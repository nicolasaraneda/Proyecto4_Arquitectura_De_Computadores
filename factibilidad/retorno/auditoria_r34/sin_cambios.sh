#!/bin/sh
# sin_cambios.sh: los campos nuevos de ../nucleo/torneo.c no cambian las salidas anteriores.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: sh sin_cambios.sh VERSION            (desde factibilidad/retorno/auditoria_r34)
#
# Tres comprobaciones, distintas de las que hizo el estudio de cierre:
#
#   1. El mismo binario compilado con el torneo.c de VERSION (sacado del
#      repositorio con git show, que no cambia nada) y con el actual. Se corre
#      con los dos una lista de comandos que no es la del estudio (otros
#      campos, otros G, la semilla 1, la vista de parada, estrategias de los
#      tres estudios) y se comparan las salidas byte a byte.
#   2. Las salidas versionadas del arnés que dependen del torneo
#      (../mediciones/hipotesis_s0.txt y rivales.txt) se vuelven a generar
#      con el binario actual, en build/, y se comparan con las versionadas.
#      No se reescribe ningún archivo de ../mediciones.
#   3. El cambio de torneo.c, medido: líneas agregadas y quitadas, y que
#      torneo.h, main.c y los archivos que entran en la huella del núcleo no
#      tienen cambios respecto del repositorio.
set -e
ANTES=$1
AQUI=$(cd "$(dirname "$0")" && pwd)
RET=$(dirname "$AQUI")
B="$AQUI/build/sin_cambios"
mkdir -p "$B/antes" "$B/despues" "$B/arnes"
cd "$RET"
RAIZ=$(git rev-parse --show-toplevel)
REL=factibilidad/retorno/nucleo

git show "$ANTES:$REL/torneo.c" > "$B/torneo_antes.c"
V=$(cat nucleo/nucleo.h nucleo/nucleo.c nucleo/e_param.c nucleo/e_rivales.c | md5sum | cut -c1-15)
CC_="cc -O2 -Wall -Wextra -fopenmp -Inucleo -DRETORNO_DIR=\"$RET\" -DNUCLEO_VERSION=0x${V}ULL"
MOD="r3_ejecucion/ejec.c r4b_fondo/fondo.c r4c_aprendizaje/e_tabla.c r4c_aprendizaje/e_patron.c r4c_aprendizaje/aprendiz.c r4_final/fondoc.c r4_final/final.c"
$CC_ -o "$B/antes/arnes" nucleo/nucleo.c "$B/torneo_antes.c" nucleo/e_param.c nucleo/e_rivales.c nucleo/main.c $MOD -lm
$CC_ -o "$B/despues/arnes" nucleo/nucleo.c nucleo/torneo.c nucleo/e_param.c nucleo/e_rivales.c nucleo/main.c $MOD -lm

corre() {
  BIN=$1; OUT=$2
  mkdir -p "$OUT"
  "$BIN" rivales > "$OUT/01_rivales.txt"
  "$BIN" hipotesis --largo 2000 --semilla 0 --campo ingenuo --G 15 > "$OUT/02_hipotesis_n2000_ingenuo_G15.txt"
  "$BIN" hipotesis --largo 2000 --semilla 1 --campo fuerte > "$OUT/03_hipotesis_n2000_s1_fuerte.txt"
  "$BIN" hipotesis --largo 20000 --semilla 0 --interior > "$OUT/04_hipotesis_n20000_int.txt"
  "$BIN" hipotesis --largo 20000 --semilla 0 --parada --candidatos "max_media;ejec:m=8;completo;completo_min" --ref max_media --campo fuerte > "$OUT/05_hipotesis_n20000_par_fuerte.txt"
  "$BIN" hipotesis --largo 2000 --semilla 0 --candidatos "max_media;ejec_b;rec_e;aprendiz;fondo_ancla" --ref max_media --G 5 > "$OUT/06_hipotesis_n2000_externas_G5.txt"
  "$BIN" veredicto --candidata completo --referencia max_media --semilla 0 --parada > "$OUT/07_veredicto_completo.txt"
  "$BIN" veredicto --candidata "ejec:m=8" --referencia max_media --semilla 0 --campo ingenuo --G 5 > "$OUT/08_veredicto_ejec_ingenuo_G5.txt"
  "$BIN" veredicto --candidata completo_min --referencia "ejec:m=8" --semilla 0 --largo 2000 --campo fuerte > "$OUT/09_veredicto_min_contra_ejec_fuerte.txt"
  "$BIN" veredicto --candidata activo --referencia base --semilla 1 --largo 2000 > "$OUT/10_veredicto_activo_s1.txt"
  "$BIN" frontera --largo 2000 --semilla 1 > "$OUT/11_frontera_s1.txt"
}
corre "$B/antes/arnes" "$B/antes/salidas"
corre "$B/despues/arnes" "$B/despues/salidas"

mal=0
echo "1. Salidas con el torneo.c anterior ($ANTES) y con el actual, comparadas byte a byte"
echo "   torneo.c anterior: $(md5sum < "$B/torneo_antes.c" | cut -c1-32)   actual: $(md5sum < nucleo/torneo.c | cut -c1-32)"
for f in "$B"/antes/salidas/*; do
  n=$(basename "$f")
  if cmp -s "$f" "$B/despues/salidas/$n"; then e=identica; else e=DISTINTA; mal=1; fi
  printf "   %-44s %8d bytes  %s  %s\n" "$n" "$(wc -c < "$f")" "$(md5sum < "$f" | cut -c1-16)" "$e"
done

echo
echo "2. Salidas versionadas del arnes, generadas de nuevo con el binario actual (sin reescribir ../mediciones)"
A="$B/despues/arnes"
( "$A" hipotesis --largo 2000 --semilla 0 && "$A" hipotesis --largo 20000 --semilla 0 --interior && "$A" hipotesis --largo 20000 --semilla 0 ) > "$B/arnes/hipotesis_s0.txt"
"$A" rivales > "$B/arnes/rivales.txt"
for n in hipotesis_s0.txt rivales.txt; do
  if git diff --quiet -- "mediciones/$n"; then v="igual al repositorio"; else v="con cambios locales"; fi
  if cmp -s "$B/arnes/$n" "mediciones/$n"; then e=identica; else e=DISTINTA; mal=1; fi
  printf "   %-44s %8d bytes  %s  %s (la versionada esta %s)\n" "$n" "$(wc -c < "mediciones/$n")" "$(md5sum < "mediciones/$n" | cut -c1-16)" "$e" "$v"
done

echo
echo "3. Que cambio en el nucleo respecto del repositorio ($ANTES)"
for f in nucleo.h nucleo.c e_param.c e_rivales.c torneo.h main.c nucleo.mk torneo.c; do
  n=$(git diff --numstat "$ANTES" -- "nucleo/$f" | awk '{print "+" $1 " -" $2}')
  printf "   %-12s %s\n" "$f" "${n:-sin cambios}"
done
echo "   huella del nucleo (nucleo.h, nucleo.c, e_param.c, e_rivales.c): $V"
for f in nucleo.h nucleo.c e_param.c e_rivales.c torneo.h main.c; do
  git diff --quiet "$ANTES" -- "nucleo/$f" || { echo "   CAMBIO INESPERADO en $f"; mal=1; }
done
cd "$RAIZ" > /dev/null
echo
if [ $mal = 0 ]; then echo "SIN_CAMBIOS: OK"; else echo "SIN_CAMBIOS: FALLA"; fi
