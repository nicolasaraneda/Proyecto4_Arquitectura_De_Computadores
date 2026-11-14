#!/usr/bin/env bash
# bitstream.sh: bitstreams del SoC barrel para probar en la Go Board.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Construye dos bitstreams (yosys, nextpnr con la semilla 1 e icepack) y
# simula cada uno desde su .asc antes de que alguien lo grabe:
#
#   barrel_cooperacion.bin   sw/cooperacion.s: los cuatro hilos. No necesita la
#                            maestra. En la placa se debe ver "60" en el
#                            display y los cuatro LEDs encendidos.
#   barrel_trade.bin         sw/trade.s sin modificar, con la tabla de arranque:
#                            la regla base en el hilo 0. Es el que se probaría
#                            con la maestra real. Se simula por los pines con
#                            la maestra del testbench (tb/tb_bitstream.sv del
#                            repositorio) y los bytes que lee la maestra se
#                            comparan con ref/trader.py, como hace
#                            tools/sim_bitstream.sh.
#
# Los .bin quedan en build/bitstream/ (ignorada por git: se regeneran con este
# script). Este script NO programa la placa. Los comandos para hacerlo están
# en el README.
#
# Uso: factibilidad/a_barrel/tools/bitstream.sh   (o make bitstream)
# Resultado en factibilidad/a_barrel/mediciones/bitstream.txt. Unos 4 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/bitstream
mkdir -p "$O"
programas
NTICKS=${NTICKS:-500}
S0="7'b0111111"; S6="7'b1111101"

# construir NOMBRE HEX
construir() {
  local n=$1 hex=$2
  yosys -q -l "$O/$n.yosys.log" -p "read_verilog $BARREL_SRC; chparam -set MemFile \"$hex\" pochoco_soc; \
    synth_ice40 -top pochoco_soc -json $O/$n.json" || return 1
  nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed 1 --json "$O/$n.json" --pcf goboard.pcf \
    --asc "$O/$n.asc" -l "$O/$n.pnr.log" -q 2>/dev/null || return 1
  icepack "$O/$n.asc" "$O/$n.bin" || return 1
  $PYTHON tools/chip_vlog.py "$O/$n.asc" goboard.pcf -o "$O/$n.chip.v"
}
resumen() {   # resumen NOMBRE
  local n=$1 log=$O/$1.pnr.log
  echo "  celdas $(grep 'ICESTORM_LC:' "$log" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'), BRAM $(grep 'ICESTORM_RAM:' "$log" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'), $(grep 'Max frequency for clock' "$log" | tail -1 | sed -E 's/.*: ([0-9.]+ MHz) \((PASS|FAIL).*/frecuencia maxima \1, \2 a 25 MHz/')"
  echo "  $(stat -c %s "$O/$n.bin") bytes, sha256 $(sha256sum "$O/$n.bin" | cut -d' ' -f1)"
}

construir barrel_cooperacion "$B/sw/cooperacion.hex" &
construir barrel_trade       "$B/sw/trade_h0.hex" &
wait

# Simulación del bitstream de los cuatro hilos: LEDs y display en los pines
iverilog -g2012 -s tb_chip -DLEDS=15 "-DSEG1=$S6" "-DSEG2=$S0" -o "$O/coop.vvp" "$CELLS_SIM" "$O/barrel_cooperacion.chip.v" $A/tb/tb_chip.sv \
  && vvp -n "$O/coop.vvp" > "$O/coop.out" &

# Simulación del bitstream de la regla base, con la maestra del testbench
( iverilog -g2012 -s tb_bitstream -DNTICKS="$NTICKS" -DPERIODO_NS=100000 '-DSERIE="tb/practica.csv"' "-DSALIDA=\"$O/bytes.csv\"" \
    -o "$O/trade.vvp" "$CELLS_SIM" "$O/barrel_trade.chip.v" tb/tb_bitstream.sv \
  && vvp -n "$O/trade.vvp" > "$O/trade.out" \
  && $PYTHON ref/market.py contabilizar "$O/bytes.csv" -o "$O/bitstream.csv" > /dev/null \
  && $PYTHON ref/trader.py tb/practica.csv --nticks "$NTICKS" --periodo-ns 100000 -o "$O/ref.csv" > /dev/null ) &
wait

{
echo "Bitstreams del SoC barrel para la Go Board, simulados desde el .asc"
echo "Generado por factibilidad/a_barrel/tools/bitstream.sh (make bitstream). No editar a mano."
echo
versiones
echo "nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed 1, goboard.pcf. Los .bin quedan en $O/."
echo
echo "1. barrel_cooperacion.bin: los cuatro hilos, sin la maestra"
resumen barrel_cooperacion
if grep -q "^RESULTADO: PASS" "$O/coop.out" 2>/dev/null; then
  echo "  PASS simulado desde el .asc, 12000 ciclos: $(grep '^LEDs' "$O/coop.out") (segmentos {G,F,E,D,C,B,A} encendidos: se lee \"60\")"
else
  echo "  FAIL simulacion del .asc: $(grep -E '^LEDs|^FAIL' "$O/coop.out" 2>/dev/null | tr '\n' ' ')"
fi
echo
echo "2. barrel_trade.bin: la regla base en el hilo 0 (sw/trade.s con la tabla de arranque)"
resumen barrel_trade
if ! grep -q "Bits de MISO con X: 0" "$O/trade.out" 2>/dev/null; then
  echo "  FAIL simulacion del .asc: MISO con X o la simulacion no corrio"
elif cmp -s "$O/bitstream.csv" "$O/ref.csv"; then
  echo "  PASS simulado desde el .asc por los pines: $NTICKS ticks a 0,1 ms identicos a ref/trader.py, patrimonio $(tail -1 "$O/bitstream.csv" | cut -d, -f6)"
else
  echo "  FAIL el bitstream no decide igual que la referencia"
fi
} | tee "$M/bitstream.txt"

! grep -q "FAIL" "$M/bitstream.txt"
