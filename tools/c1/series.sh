#!/usr/bin/env bash
# series.sh: R3 contra su referencia en series sintéticas (criterio 2 de la puerta
# de simulación: al menos 1000 series).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   1. RTL (tb/c1/tb_c1.sv): una serie de 20 000 ticks de cada familia sintética,
#      cruda y normalizada entre 100 y 255, a 0,1 ms. Bytes, estado tick a tick y
#      protocolo. Una serie cruda puede bajar de 100: R3 pasa a modo seguro (banda
#      40) y la referencia espera eso mismo.
#   2. RTL: 1 050 series de 2000 ticks (35 por familia, cada una cruda y
#      normalizada), a 0,1 ms.
#   3. Gemelo con la tabla de 512 palabras: las mismas 1 050 series, la serie de
#      práctica anterior (tb/practica.csv) y las 30 de 20 000 ticks, a los tres
#      períodos.
#
# Uso: [CORTA=1] [JOBS=12] tools/c1/series.sh   (make c1-series)
# Resultado en docs/mediciones/c1/series.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BC/lote
POR=${POR_FAMILIA:-35}
NT=2000
LARGO=20000
SALIDA=${SALIDA:-$MC/series.txt}
[ "${CORTA:-0}" = 1 ] && { POR=3; LARGO=3000; }
FAMILIAS="remuestreo modelo modelo_vecino paseo tendencia reversion dos_componentes saltos cambio_volatilidad cambio_de_caracter volatil nivel_bajo plana borde_bajo borde_alto"
rm -rf "$O"; mkdir -p "$O/series"
ensamblar_c1 || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1
compilar_gemelo || exit 1

NORMALIZAR=1 $PYTHON tools/fondo/lote.py "$O/series" "$POR" "$NT" 1 > "$O/lista.txt"
: > "$O/largas.txt"
for f in $FAMILIAS; do serie "$f" 1 $LARGO >> "$O/largas.txt"; serie_norm "$f" 1 $LARGO >> "$O/largas.txt"; done
{
  while read -r s; do echo "caso $O/L_$(basename "$s" .csv) --serie $s --nticks $LARGO"; done < "$O/largas.txt"
  while read -r s; do echo "caso $O/$(basename "$s" .csv) --serie $s --nticks $NT"; done < "$O/lista.txt"
} | en_paralelo
{ cat "$O/lista.txt" "$O/largas.txt"; echo tb/practica.csv; } > "$O/gemelo_lista.txt"
$PYTHON $TC/gemelo_lote.py "$O/gemelo_lista.txt" --jobs "${JOBS:-6}" --salida "$O/gemelo.txt" > /dev/null

{
cabecera "R3 contra su referencia en series sinteticas" tools/c1/series.sh "make c1-series"
echo "1. RTL: una serie de $LARGO ticks de cada familia, cruda y normalizada (-norm), a 0,1 ms"
while read -r s; do cat "$O/L_$(basename "$s" .csv)/resultado.txt"; done < "$O/largas.txt"
echo
echo "2. RTL: $POR series por familia, cada una cruda y normalizada (-norm), $NT ticks, semilla 1, periodo de 0,1 ms"
printf "%-24s %7s %7s %12s %12s %12s\n" familia series pasan "ticks" "peor caso" "modo seguro"
total=0; pasan=0; ticks=0
for fam in $(sed 's|.*/||; s|_[0-9]*\.csv$||' "$O/lista.txt" | sort -u); do
  n=0; p=0; tk=0; peor=0; seg=0
  for r in "$O/${fam}"_[0-9][0-9][0-9]/resultado.txt; do
    n=$((n + 1))
    if grep -q "^PASS" "$r"; then
      p=$((p + 1))
      tk=$((tk + $(sed -n 's/^PASS [^:]*: \([0-9]*\) bytes.*/\1/p' "$r")))
      c=$(sed -n 's/.*peor caso \([0-9]*\) de.*/\1/p' "$r"); [ "$c" -gt "$peor" ] && peor=$c
      grep -q "seguro 1" "$r" && seg=$((seg + 1))
    fi
  done
  printf "%-24s %7d %7d %12d %12d %12d\n" "$fam" "$n" "$p" "$tk" "$peor" "$seg"
  total=$((total + n)); pasan=$((pasan + p)); ticks=$((ticks + tk))
done
echo
grep -h "^FAIL" "$O"/*/resultado.txt | head -20
if [ "$pasan" = "$total" ] && [ "$total" -gt 0 ]; then
  echo "PASS: $pasan de $total series identicas a la referencia (bytes, estado y protocolo), $ticks ticks"
else
  echo "FAIL: pasan $pasan de $total series"
fi
echo
echo "3. Gemelo con la tabla de 512 palabras: las mismas series, las de $LARGO ticks y tb/practica.csv, a los tres periodos"
sed -n '3,$p' "$O/gemelo.txt"
} | tee "$SALIDA"
cierre "$SALIDA"
