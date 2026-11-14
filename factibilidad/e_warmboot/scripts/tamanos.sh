#!/usr/bin/env bash
# tamanos.sh: cuántas imágenes caben en la flash de la Go Board.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Arma con icemulti archivos de 2, 3 y 4 imágenes, sin alineación y con las
# alineaciones que tienen sentido en una flash de 1 Mbit (-a15 y -A15: 32 kB,
# -a16: 64 kB), y compara el tamaño con la capacidad. También intenta 5
# imágenes, para dejar registrado el límite de icemulti.
#
# Las cuatro imágenes son bitstreams reales de la HX1K: los dos de bitstreams/
# y los dos de la prueba de placa. Todas miden lo mismo.
#
# Al final arma el archivo "realista": bitstreams/segmentado_v1.bin como
# imagen de encendido y bitstreams/competencia_v1.bin como respaldo. Es un
# ejercicio de tamaño: segmentado_v1.bin no lleva SB_WARMBOOT, así que ese
# archivo nunca saltaría al respaldo. No se graba en la placa.
#
# Uso, desde la raíz del repositorio (después de construir_demo.sh):
#   factibilidad/e_warmboot/scripts/tamanos.sh
# Resultado en mediciones/icemulti_tamanos.txt.
set -euo pipefail

E=factibilidad/e_warmboot
D=$E/build/tamanos
FLASH=${FLASH:-131072}     # 1 Mbit
mkdir -p "$D" "$E/mediciones"

I0=bitstreams/segmentado_v1.bin
I1=bitstreams/competencia_v1.bin
I2=$E/build/demo/img0.bin
I3=$E/build/demo/img1.bin

fila() {   # fila N OPCION ARCHIVOS...
  local n=$1 op=$2; shift 2
  local nombre="multi${n}${op:+_${op#-}}.bin"
  if icemulti $op -v -o "$D/$nombre" "$@" 2> "$D/$nombre.log"; then
    local t; t=$(stat -c %s "$D/$nombre")
    local ult; ult=$(grep "Place image" "$D/$nombre.log" | tail -1 | sed -E 's/.*at ([0-9a-f]+) \.\. ([0-9a-f]+).*/0x\1 a 0x\2/')
    local cabe="cabe"; [ "$t" -le "$FLASH" ] || cabe="NO CABE"
    printf "%-9s %-12s %7d bytes  %5.1f %%  sobran %6d   última imagen en %s   %s\n" \
      "$n" "${op:-sin alinear}" "$t" "$(echo "scale=3; 100*$t/$FLASH" | bc)" "$((FLASH - t))" "$ult" "$cabe"
  else
    printf "%-9s %-12s icemulti falla: %s\n" "$n" "${op:-sin alinear}" "$(tail -1 "$D/$nombre.log")"
  fi
}

{
  echo "Cuántas imágenes caben en la flash"
  echo "Comando: factibilidad/e_warmboot/scripts/tamanos.sh"
  echo "Capacidad supuesta de la flash: $FLASH bytes (1 Mbit)"
  echo
  echo "Tamaño de un bitstream de la HX1K (icepack):"
  for f in $I0 $I1 $I2 $I3; do printf "  %-48s %6d bytes\n" "$f" "$(stat -c %s "$f")"; done
  echo
  echo "Imágenes  Alineación   Tamaño del archivo"
  for op in "" -a15 -A15 -a16; do
    fila 2 "$op" $I0 $I1
    fila 3 "$op" $I0 $I1 $I2
    fila 4 "$op" $I0 $I1 $I2 $I3
  done
  fila 5 "" $I0 $I1 $I2 $I3 $I0
  echo
  echo "Cabecera de icemulti: 5 vectores de 32 bytes = 160 bytes (encendido y los 4 de S1 S0)."
  echo "Con -a<n> las imágenes 1, 2 y 3 parten en múltiplos de 2^n bytes; con -A<n>, también la 0."
  echo
  echo "--- Archivo realista: segmentado_v1.bin (encendido) + competencia_v1.bin (respaldo) ---"
  echo "icemulti -a15 -v -o build/tamanos/realista.bin $I0 $I1"
  icemulti -a15 -v -o "$D/realista.bin" $I0 $I1 2>&1 | sed 's/^/  /'
  python3 $E/scripts/ver_multi.py --flash "$FLASH" "$D/realista.bin" $I0 $I1
  echo
  echo "Los bitstreams originales, según bitstreams/SHA256SUMS:"
  sed 's/^/  /' bitstreams/SHA256SUMS
} | tee $E/mediciones/icemulti_tamanos.txt
