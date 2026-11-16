#!/usr/bin/env bash
# construir_demo.sh: construye las dos imágenes de la prueba de placa y el
# archivo de varias imágenes que se graba en la flash.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Pasos, por cada imagen (0 y 1):
#   yosys     sintetiza rtl/wb_demo.v con Img = N y Destino = la otra imagen
#   nextpnr   --hx1k --package vq100 --freq 25, semilla 1, con goboard.pcf
#   icepack   .asc a .bin
# y al final:
#   icemulti  empaqueta img0.bin e img1.bin en wb_demo_multi.bin (la imagen 0
#             es la de encendido)
#   ver_multi.py comprueba los vectores y que las imágenes estén copiadas sin
#             cambios
#
# El archivo final queda en factibilidad/e_warmboot/wb_demo_multi.bin. El
# .gitignore del repositorio ignora los .bin, así que no se versiona: este
# script lo regenera. Su SHA-256 queda en mediciones/demo_construccion.txt.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/e_warmboot/scripts/construir_demo.sh
set -euo pipefail

E=factibilidad/e_warmboot
D=$E/build/demo
OUT=$E/mediciones/demo_construccion.txt
SEMILLA=${SEMILLA:-1}
mkdir -p "$D" "$E/mediciones"

construir() {   # construir IMG DESTINO
  local n=$1 dest=$2
  yosys -q -l "$D/yosys_img$n.log" \
    -p "read_verilog $E/rtl/wb_demo.v; chparam -set Img $n -set Destino 2'd$dest wb_demo; synth_ice40 -top wb_demo -json $D/img$n.json"
  nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed "$SEMILLA" --json "$D/img$n.json" \
    --pcf goboard.pcf --asc "$D/img$n.asc" -l "$D/nextpnr_img$n.log" -q 2>/dev/null
  icepack "$D/img$n.asc" "$D/img$n.bin"
}

construir 0 1
construir 1 0
icemulti -v -o "$E/wb_demo_multi.bin" "$D/img0.bin" "$D/img1.bin" 2> "$D/icemulti.log"

campo() { grep "$2:" "$1" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'; }
fmax()  { grep "Max frequency for clock" "$1" | tail -1 | sed -E 's/.*: ([0-9.]+) MHz \((.*)\)/\1 MHz (\2)/'; }

{
  echo "Prueba de placa: dos imágenes con SB_WARMBOOT"
  echo "Comando: factibilidad/e_warmboot/scripts/construir_demo.sh"
  echo "Herramientas: $(yosys -V | cut -d' ' -f1-2), $(nextpnr-ice40 --version 2>&1 | head -1 | sed 's/.*(Version \(.*\))/nextpnr \1/')"
  echo "nextpnr --hx1k --package vq100 --freq 25 --seed $SEMILLA, goboard.pcf"
  echo
  for n in 0 1; do
    echo "imagen $n (rtl/wb_demo.v, Img = $n):"
    echo "  celdas lógicas   $(campo "$D/nextpnr_img$n.log" ICESTORM_LC)"
    echo "  BRAM             $(campo "$D/nextpnr_img$n.log" ICESTORM_RAM)"
    echo "  SB_WARMBOOT      $(campo "$D/nextpnr_img$n.log" SB_WARMBOOT)"
    echo "  frecuencia máx.  $(fmax "$D/nextpnr_img$n.log")"
    echo "  tamaño           $(stat -c %s "$D/img$n.bin") bytes"
    echo "  sha256           $(sha256sum "$D/img$n.bin" | cut -d' ' -f1)"
  done
  echo
  echo "icemulti -v -o wb_demo_multi.bin img0.bin img1.bin:"
  sed 's/^/  /' "$D/icemulti.log"
  echo
  python3 $E/scripts/ver_multi.py "$E/wb_demo_multi.bin" "$D/img0.bin" "$D/img1.bin"
} | tee "$OUT"

# Hash en el formato de sha256sum, para comprobarlo antes de grabar
( cd "$E" && sha256sum $(ls wb_demo_multi.bin relevo_prueba_multi.bin 2> /dev/null) > SHA256SUMS.txt )
