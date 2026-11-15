#!/bin/sh
# repetir.sh: vuelve a correr objetivos baratos de los estudios auditados y compara sus salidas.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: sh repetir.sh            (desde factibilidad/retorno/auditoria_r34)
#
# Para cada carpeta auditada: guarda una copia de mediciones/, corre con su
# propio Makefile los objetivos que demoran poco y compara cada archivo de
# mediciones/ con la copia (md5). Los binarios de cada carpeta se vuelven a
# compilar contra el núcleo actual, que ya trae los campos nuevos de
# torneo.c: si una salida cambiara por eso, aquí se vería. Al final deja en
# mediciones/ los archivos de la copia, así que esta prueba no cambia nada de
# las carpetas auditadas.
cd "$(dirname "$0")/.."
B=auditoria_r34/build/repetir
rm -rf "$B"; mkdir -p "$B"
export HILOS=${HILOS:-5}
mal=0
total=0
repite() {
  carpeta=$1; shift
  cp -a "$carpeta/mediciones" "$B/$carpeta"
  echo "== $carpeta: make $*"
  for obj in "$@"; do
    if make -C "$carpeta" "$obj" > "$B/${carpeta}_$obj.log" 2>&1; then e=ok; else e=FALLA; mal=1; fi
    printf "   make %-14s %s\n" "$obj" "$e"
  done
  cambiados=0; iguales=0
  for f in "$B/$carpeta"/*; do
    n=$(basename "$f")
    if [ "$(md5sum < "$f")" = "$(md5sum < "$carpeta/mediciones/$n")" ]; then iguales=$((iguales + 1))
    else cambiados=$((cambiados + 1)); echo "   DISTINTA: $n"; diff "$f" "$carpeta/mediciones/$n" | head -6 | sed 's/^/      /'; mal=1; fi
  done
  nuevos=$(ls "$carpeta/mediciones" | wc -l)
  echo "   $iguales archivos identicos, $cambiados distintos (la carpeta tiene $nuevos)"
  total=$((total + iguales + cambiados))
  cp -a "$B/$carpeta"/. "$carpeta/mediciones/"
}
repite r3_ejecucion arnes validar cota descomposicion practica
repite r4b_fondo arnes prueba cota tablas bytes
repite r4c_aprendizaje arnes causal equivalencia tamanos
repite r4_final arnes prueba campos tablas
echo
if [ $mal = 0 ]; then echo "PASS: $total archivos de mediciones comparados despues de repetir, todos identicos"
else echo "REVISAR: alguna salida cambio o algun objetivo fallo"; fi
