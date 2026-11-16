#!/usr/bin/env bash
# icebram_prueba.sh: cambio del programa dentro del bitstream del barrel con
# icebram, sin volver a sintetizar ni a rutear.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Es la pieza del kit de contingencia que faltaba probar con este core. La
# memoria de programa del SoC queda repartida en 8 BRAM (Yosys la duplica para
# tener dos puertos de lectura), y el barrel agrega una condición propia: el
# programa nuevo tiene que traer la tabla de arranque (tools/tabla.py).
#
# Pasos:
#   1. Bitstream molde: el SoC barrel con la memoria llena de un patrón al azar
#      (icebram -g), semilla 1 de nextpnr.
#   2. icebram reemplaza el patrón por sw/trade.s con la tabla de arranque, y
#      por sw/cooperacion.s. Se mide cuánto demora de punta a punta (icebram
#      más icepack).
#   3. Los dos bitstreams cambiados se simulan desde el .asc por los pines,
#      igual que en tools/bitstream.sh: la regla base contra ref/trader.py y
#      los cuatro hilos contra LEDs y display.
#   4. Se compara el .asc cambiado con el que sale de sintetizar directamente
#      con ese programa (misma semilla).
#
# No programa la placa.
#
# Uso: factibilidad/a_barrel/tools/icebram_prueba.sh   (o make icebram)
# Resultado en factibilidad/a_barrel/mediciones/icebram.txt. Unos 2 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/icebram
rm -rf "$O"; mkdir -p "$O"
programas
NTICKS=${NTICKS:-500}
S0="7'b0111111"; S6="7'b1111101"

# completar ENTRADA.hex SALIDA.hex: deja el programa con las 512 palabras, que
# es lo que icebram exige (los dos archivos del mismo tamaño)
completar() {
  $PYTHON - "$1" "$2" <<'PY'
import sys
palabras = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("//") and not l.startswith("@")]
assert len(palabras) <= 512, len(palabras)
palabras += ["00000000"] * (512 - len(palabras))
open(sys.argv[2], "w", newline="\n").write("\n".join(palabras) + "\n")
PY
}

# construir NOMBRE HEX: síntesis y ruteo, mismos comandos que tools/bitstream.sh
construir() {
  local n=$1 hex=$2
  yosys -q -l "$O/$n.yosys.log" -p "read_verilog $BARREL_SRC; chparam -set MemFile \"$hex\" pochoco_soc; \
    synth_ice40 -top pochoco_soc -json $O/$n.json" || return 1
  nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed 1 --json "$O/$n.json" --pcf goboard.pcf \
    --asc "$O/$n.asc" -l "$O/$n.pnr.log" -q 2>/dev/null || return 1
}

icebram -g -s 1 32 512 > "$O/molde.hex"
completar "$B/sw/trade_h0.hex"    "$O/trade.hex"
completar "$B/sw/cooperacion.hex" "$O/cooperacion.hex"

t0=$(date +%s.%N)
construir molde  "$O/molde.hex" &
construir directo "$O/trade.hex" &
wait
t1=$(date +%s.%N)

# cambiar NOMBRE: reemplaza el patrón del molde por el programa NOMBRE.hex
cambiar() {
  local n=$1 a b
  a=$(date +%s.%N)
  icebram "$O/molde.hex" "$O/$n.hex" < "$O/molde.asc" > "$O/${n}_icebram.asc" || return 1
  icepack "$O/${n}_icebram.asc" "$O/${n}_icebram.bin" || return 1
  b=$(date +%s.%N)
  echo "$a $b" | awk '{printf "%.2f\n", $2 - $1}' > "$O/$n.tiempo"
  $PYTHON tools/chip_vlog.py "$O/${n}_icebram.asc" goboard.pcf -o "$O/${n}_icebram.chip.v"
}
cambiar trade
cambiar cooperacion

# Simulación desde el .asc cambiado
iverilog -g2012 -s tb_chip -DLEDS=15 "-DSEG1=$S6" "-DSEG2=$S0" -o "$O/coop.vvp" "$CELLS_SIM" "$O/cooperacion_icebram.chip.v" $A/tb/tb_chip.sv \
  && vvp -n "$O/coop.vvp" > "$O/coop.out" &
( iverilog -g2012 -s tb_bitstream -DNTICKS="$NTICKS" -DPERIODO_NS=100000 '-DSERIE="tb/practica.csv"' "-DSALIDA=\"$O/bytes.csv\"" \
    -o "$O/trade.vvp" "$CELLS_SIM" "$O/trade_icebram.chip.v" tb/tb_bitstream.sv \
  && vvp -n "$O/trade.vvp" > "$O/trade.out" \
  && $PYTHON ref/market.py contabilizar "$O/bytes.csv" -o "$O/bitstream.csv" > /dev/null \
  && $PYTHON ref/trader.py tb/practica.csv --nticks "$NTICKS" --periodo-ns 100000 -o "$O/ref.csv" > /dev/null ) &
wait

{
echo "Cambio de programa en el bitstream del barrel con icebram, sin volver a sintetizar"
echo "Generado por factibilidad/a_barrel/tools/icebram_prueba.sh (make icebram). No editar a mano."
echo
versiones
echo
echo "Molde: SoC barrel con la memoria llena de un patron al azar (icebram -g -s 1 32 512), nextpnr --seed 1."
echo "  celdas $(grep 'ICESTORM_LC:' "$O/molde.pnr.log" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'), BRAM $(grep 'ICESTORM_RAM:' "$O/molde.pnr.log" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'), $(grep 'Max frequency for clock' "$O/molde.pnr.log" | tail -1 | sed -E 's/.*: ([0-9.]+ MHz) \((PASS|FAIL).*/frecuencia maxima \1, \2 a 25 MHz/')"
echo "  Sintesis y ruteo del molde y del bitstream directo, en paralelo: $(echo "$t0 $t1" | awk '{printf "%.0f", $2 - $1}') s (es lo que el cambio con icebram evita)."
echo
echo "1. Regla base (sw/trade.s con la tabla de arranque) puesta con icebram"
if [ -s "$O/trade_icebram.bin" ]; then
  echo "  icebram mas icepack: $(cat "$O/trade.tiempo") s. $(stat -c %s "$O/trade_icebram.bin") bytes, sha256 $(sha256sum "$O/trade_icebram.bin" | cut -d' ' -f1)"
  if ! grep -q "Bits de MISO con X: 0" "$O/trade.out" 2>/dev/null; then
    echo "  FAIL simulacion del .asc: MISO con X o la simulacion no corrio"
  elif cmp -s "$O/bitstream.csv" "$O/ref.csv"; then
    echo "  PASS simulado desde el .asc por los pines: $NTICKS ticks a 0,1 ms identicos a ref/trader.py, patrimonio $(tail -1 "$O/bitstream.csv" | cut -d, -f6)"
  else
    echo "  FAIL el bitstream cambiado no decide igual que la referencia"
  fi
  dif=$(diff <(grep -v '^\.comment' "$O/trade_icebram.asc") <(grep -v '^\.comment' "$O/directo.asc") | grep -c '^[<>]')
  if [ "$dif" = 0 ]; then
    echo "  PASS el .asc cambiado es identico al que sale de sintetizar directamente con ese programa (misma semilla)"
  else
    echo "  NOTA el .asc cambiado difiere en $dif lineas del sintetizado directamente (la colocacion puede cambiar con el contenido; vale la simulacion)"
  fi
else
  echo "  FAIL icebram o icepack no terminaron"
fi
echo
echo "2. Los cuatro hilos (sw/cooperacion.s) puestos con icebram sobre el mismo molde"
if [ -s "$O/cooperacion_icebram.bin" ]; then
  echo "  icebram mas icepack: $(cat "$O/cooperacion.tiempo") s. sha256 $(sha256sum "$O/cooperacion_icebram.bin" | cut -d' ' -f1)"
  if grep -q "^RESULTADO: PASS" "$O/coop.out" 2>/dev/null; then
    echo "  PASS simulado desde el .asc, 12000 ciclos: $(grep '^LEDs' "$O/coop.out") (se lee \"60\")"
  else
    echo "  FAIL simulacion del .asc: $(grep -E '^LEDs|^FAIL' "$O/coop.out" 2>/dev/null | tr '\n' ' ')"
  fi
else
  echo "  FAIL icebram o icepack no terminaron"
fi
} | tee "$M/icebram.txt"

if grep -q "FAIL" "$M/icebram.txt"; then echo "RESULTADO: FAIL" | tee -a "$M/icebram.txt"; exit 1; fi
echo "RESULTADO: PASS, el programa del barrel se cambia con icebram sin volver a sintetizar" | tee -a "$M/icebram.txt"
