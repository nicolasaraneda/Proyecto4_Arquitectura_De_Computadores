#!/usr/bin/env bash
# construir_relevo.sh: arma el archivo de la prueba de relevo y simula su
# imagen principal desde el .asc.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El archivo tiene dos imágenes:
#
#   imagen 0 (encendido)  copia del SoC con vigilante (N = 4) y disparo manual
#                         con el interruptor 4, corriendo sw/cuelgue.s: responde
#                         K = 500 precios con "comprar 63" y se cuelga
#   imagen 1 (respaldo)   bitstreams/competencia_v1.bin, sin ningún cambio
#
# Es una imagen de prueba, no la edición de competencia: sirve para ver en la
# placa (con el interruptor) y con la maestra real (dejando que el programa
# se cuelgue) el relevo hacia el bitstream de competencia verdadero.
#
# Queda en factibilidad/e_warmboot/relevo_prueba_multi.bin (el .gitignore lo
# ignora; este script lo regenera) y su hash en mediciones/relevo_construccion.txt.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/e_warmboot/scripts/construir_relevo.sh [sin-simular]
set -euo pipefail

E=factibilidad/e_warmboot
D=$E/build/relevo_img
K=${K:-500}
SEMILLA=${SEMILLA:-1}
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
mkdir -p "$D" "$E/mediciones"
RTLV=$($E/scripts/armar_rtl.sh)

python3 tools/pochoasm.py $E/sw/cuelgue.s -D K=$K -D DEC=0x7F -o "$D/cuelgue.hex" > /dev/null

yosys -q -l "$D/yosys.log" \
  -p "read_verilog $(echo $RTLV/*.v $RTLV/espino_core/*.v); chparam -set MemFile \"$D/cuelgue.hex\" -set Vigilante 1 -set VigN 4 -set VigBoton 1 pochoco_soc; synth_ice40 -top pochoco_soc -json $D/principal.json"
nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed "$SEMILLA" --json "$D/principal.json" \
  --pcf goboard.pcf --asc "$D/principal.asc" -l "$D/nextpnr.log" -q 2>/dev/null
icepack "$D/principal.asc" "$D/principal.bin"
icemulti -a15 -v -o "$E/relevo_prueba_multi.bin" "$D/principal.bin" bitstreams/competencia_v1.bin 2> "$D/icemulti.log"

if [ "${1:-}" != sin-simular ]; then
  python3 $E/scripts/chip_vlog_wb.py "$D/principal.asc" goboard.pcf -o "$D/chip.v"
  iverilog -g2012 -s tb_chip_relevo -DK=$K -o "$D/tb_chip" "$CELLS_SIM" "$D/chip.v" $E/tb/tb_chip_relevo.sv
  vvp -n "$D/tb_chip" +modo=0 > "$D/sim_modo0.log" 2>&1 &
  vvp -n "$D/tb_chip" +modo=1 > "$D/sim_modo1.log" 2>&1 &
  wait
fi

campo() { grep "$2:" "$1" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'; }
{
  echo "Archivo de la prueba de relevo: SoC con vigilante + bitstream de competencia"
  echo "Comando: factibilidad/e_warmboot/scripts/construir_relevo.sh"
  echo "Herramientas: $(yosys -V | cut -d' ' -f1-2), $(nextpnr-ice40 --version 2>&1 | head -1 | sed 's/.*(Version \(.*\))/nextpnr \1/')"
  echo
  echo "imagen 0: copia del SoC, Vigilante = 1, VigN = 4, VigBoton = 1, programa sw/cuelgue.s con K = $K"
  echo "  celdas lógicas   $(campo "$D/nextpnr.log" ICESTORM_LC)"
  echo "  BRAM             $(campo "$D/nextpnr.log" ICESTORM_RAM)"
  echo "  SB_WARMBOOT      $(campo "$D/nextpnr.log" SB_WARMBOOT)"
  echo "  frecuencia máx.  $(grep "Max frequency for clock" "$D/nextpnr.log" | tail -1 | sed -E 's/.*: ([0-9.]+) MHz \((.*)\)/\1 MHz (\2)/') (semilla $SEMILLA)"
  echo "  sha256           $(sha256sum "$D/principal.bin" | cut -d' ' -f1)"
  echo "imagen 1: bitstreams/competencia_v1.bin"
  echo "  sha256           $(sha256sum bitstreams/competencia_v1.bin | cut -d' ' -f1)"
  echo
  echo "icemulti -a15 -v -o relevo_prueba_multi.bin principal.bin bitstreams/competencia_v1.bin:"
  sed 's/^/  /' "$D/icemulti.log"
  echo
  python3 $E/scripts/ver_multi.py "$E/relevo_prueba_multi.bin" "$D/principal.bin" bitstreams/competencia_v1.bin
  echo
  if [ -f "$D/sim_modo0.log" ]; then
    echo "Simulación de la imagen 0 desde el .asc (tb/tb_chip_relevo.sv):"
    grep -v "finish called" "$D/sim_modo0.log" "$D/sim_modo1.log" | sed -E 's/^[^:]*sim_modo[01].log://'
  fi
} | tee $E/mediciones/relevo_construccion.txt

( cd "$E" && sha256sum $(ls wb_demo_multi.bin relevo_prueba_multi.bin 2> /dev/null) > SHA256SUMS.txt )
! grep -q "FAIL\|FALLA\|con fallas" $E/mediciones/relevo_construccion.txt
