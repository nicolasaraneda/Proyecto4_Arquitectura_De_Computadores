#!/usr/bin/env bash
# variantes_demo.sh: variantes de la prueba de placa, para diagnóstico y para
# probar si la reconfiguración se puede acortar.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Las tres salen de las mismas dos imágenes de construir_demo.sh (mismo .asc,
# misma lógica). Cambia solo la cabecera del bitstream:
#
#   variantes/wb_demo_multi_sin_dormir.bin   icepack -s: la FPGA no manda la
#       flash a bajo consumo al terminar de configurarse. Es el archivo para
#       probar si el salto no funciona con el normal.
#   variantes/wb_demo_multi_frec_media.bin   oscilador de configuración en
#       frecuencia media (comando 51 01 de la cabecera)
#   variantes/wb_demo_multi_frec_alta.bin    oscilador en frecuencia alta (51 02)
#
# icepack no tiene una opción para elegir la frecuencia al empaquetar: escribe
# siempre "baja". Aquí se cambia el byte del comando 51 en el .bin. Ese
# comando va antes del que reinicia el CRC, así que el CRC no cambia. Se
# comprueba desempaquetando la imagen cambiada con icepack -u: tiene que decir
# "CRC Check OK", informar la frecuencia nueva y entregar el mismo .asc que la
# imagen original.
#
# Uso, desde la raíz del repositorio (después de construir_demo.sh):
#   factibilidad/e_warmboot/scripts/variantes_demo.sh
# Resultado en mediciones/demo_variantes.txt.
set -euo pipefail

E=factibilidad/e_warmboot
D=$E/build/variantes
V=$E/variantes
mkdir -p "$D" "$V" "$E/mediciones"

cambiar_frecuencia() {   # cambiar_frecuencia ENTRADA SALIDA VALOR
  cp "$1" "$2"
  [ "$(xxd -p -s 4 -l 6 "$2")" = "7eaa997e5100" ] || { echo "ERROR: cabecera inesperada en $1"; exit 1; }
  printf "\\x$3" | dd of="$2" bs=1 seek=9 conv=notrunc 2> /dev/null
}

ok=1
{
  echo "Variantes de la prueba de placa"
  echo "Comando: factibilidad/e_warmboot/scripts/variantes_demo.sh"
  echo

  echo "--- sin_dormir: icepack -s ---"
  for n in 0 1; do icepack -s "$E/build/demo/img$n.asc" "$D/img${n}_sd.bin"; done
  icemulti -o "$V/wb_demo_multi_sin_dormir.bin" "$D/img0_sd.bin" "$D/img1_sd.bin"
  for n in 0 1; do
    echo "imagen $n: $(icepack -u -v "$D/img${n}_sd.bin" "$D/img${n}_sd.asc" 2>&1 | grep -i "warmboot\|CRC" | paste -sd' ')"
  done
  python3 $E/scripts/ver_multi.py "$V/wb_demo_multi_sin_dormir.bin" "$D/img0_sd.bin" "$D/img1_sd.bin" | grep "tamaño\|RESULTADO" || ok=0
  echo

  for par in "media 01 medium" "alta 02 high"; do
    set -- $par
    echo "--- frec_$1: comando 51 $2 ---"
    for n in 0 1; do
      cambiar_frecuencia "$E/build/demo/img$n.bin" "$D/img${n}_$1.bin" "$2"
      icepack -u -v "$E/build/demo/img$n.bin" "$D/img${n}_orig.asc" > /dev/null 2>&1
      salida=$(icepack -u -v "$D/img${n}_$1.bin" "$D/img${n}_$1.asc" 2>&1)
      echo "imagen $n: $(echo "$salida" | grep -i "freqrange\|CRC" | paste -sd' ')"
      echo "$salida" | grep -q "freqrange to '$3'" || { echo "FALLA: la frecuencia no quedó en $3"; ok=0; }
      echo "$salida" | grep -q "CRC Check OK" || { echo "FALLA: CRC"; ok=0; }
      if cmp -s "$D/img${n}_$1.asc" "$D/img${n}_orig.asc"; then
        echo "imagen $n: al desempaquetar entrega el mismo .asc que la original"
      else
        echo "FALLA: el .asc de la imagen $n cambió"; ok=0
      fi
      echo "imagen $n: bytes distintos de la original: $(cmp -l "$E/build/demo/img$n.bin" "$D/img${n}_$1.bin" | wc -l) (posición $(cmp -l "$E/build/demo/img$n.bin" "$D/img${n}_$1.bin" | awk '{print $1}' | paste -sd,), contando desde 1)"
    done
    icemulti -o "$V/wb_demo_multi_frec_$1.bin" "$D/img0_$1.bin" "$D/img1_$1.bin"
    python3 $E/scripts/ver_multi.py "$V/wb_demo_multi_frec_$1.bin" "$D/img0_$1.bin" "$D/img1_$1.bin" | grep "tamaño\|vector 0\|RESULTADO" || ok=0
    echo
  done

  echo "SHA-256:"
  ( cd "$E" && sha256sum variantes/*.bin | sed 's/^/  /' )
  echo
  [ $ok = 1 ] && echo "RESULTADO: correcto" || echo "RESULTADO: con fallas"
} | tee $E/mediciones/demo_variantes.txt
( cd "$E" && sha256sum variantes/*.bin > variantes/SHA256SUMS.txt )
grep -q "RESULTADO: correcto" $E/mediciones/demo_variantes.txt
