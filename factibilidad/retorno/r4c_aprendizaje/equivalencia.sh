#!/bin/sh
# equivalencia.sh: con el aprendizaje apagado, la tabla y el filtro deciden igual que max_media.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: sh equivalencia.sh build/arnes ../build/series
#
# Para cada estructura con el aprendizaje apagado y cada lote de series de la
# semilla 0 (más los bloques y la serie de práctica) compara, serie por serie:
#   1. patrimonio final, órdenes, mayor caída y comprar y mantener contra los
#      de max_media (columnas 1, 2, 3 y 8 de `detalle`);
#   2. el byte de decisión de cada tick: la estrategia corre con cmp=1, lleva
#      a max_media por dentro y cuenta los ticks distintos (columna 7).
# Además compara decisiones.csv en la serie de práctica completa.
# Termina con error si hay alguna diferencia.

ARNES=$1
SERIES=$2
AQUI=$(cd "$(dirname "$0")" && pwd)
TMP=$AQUI/build/equivalencia
mkdir -p "$TMP"
rm -f "$TMP/suma.txt"

ESTRUCTURAS="tabla:cmp=1
tabla:cmp=1,sh=4,nb=64
tabla:cmp=1,sh=3,nb=64
tabla:cmp=1,nb=16
tabla:cmp=1,ter=1
tabla:cmp=1,ter=2
tabla:cmp=1,ter=3,filas=2
tabla:cmp=1,filas=2,c=8
tabla:cmp=1,c=64,h=64
tabla:cmp=1,ui=48,uo=-48
tabla:cmp=1,ui=-48,uo=48
tabla:cmp=1,modo=1,bits=4
tabla:cmp=1,modo=1,bits=8,filas=2,ter=1
tabla:cmp=1,banda=1,lim=2
tabla:cmp=1,banda=1,ter=2,sh=4,nb=64
mm_patron:cmp=1,apr=0
mm_patron:cmp=1,apr=0,fe=2,fs=2,tipo=3,sim=3,H=6
mm_patron:cmp=1,apr=0,fe=2,fs=2,tipo=1,H=12,bits=3"

LOTES="$SERIES/bloques_n2000.bin $SERIES/practica_n20000.bin $(ls "$SERIES"/*_s0_n2000.bin "$SERIES"/*_s0_n20000.bin)"

echo "Equivalencia con el aprendizaje apagado: cada estructura contra max_media, serie por serie."
echo "Columnas: estructura, lotes, series, ticks, series con resultado distinto, ticks con decision distinta."
total_dif=0
total_series=0
for lote in $LOTES; do
  nombre=$(basename "$lote" .bin)
  "$ARNES" detalle --estrategia max_media --lote "$lote" | cut -d' ' -f1-3,8 > "$TMP/ref_$nombre.txt"
done
echo "$ESTRUCTURAS" | while IFS= read -r e; do
  lotes=0; series=0; ticks=0; dif_res=0; dif_tick=0
  for lote in $LOTES; do
    nombre=$(basename "$lote" .bin)
    "$ARNES" detalle --estrategia "$e" --lote "$lote" > "$TMP/cand.txt"
    cut -d' ' -f1-3,8 "$TMP/cand.txt" > "$TMP/cand_res.txt"
    n=$(wc -l < "$TMP/cand.txt")
    largo=${nombre##*_n}
    d=$(paste -d'|' "$TMP/ref_$nombre.txt" "$TMP/cand_res.txt" | awk -F'|' '$1 != $2 {c++} END {print c+0}')
    t=$(awk '{s += $7} END {print s+0}' "$TMP/cand.txt")
    lotes=$((lotes + 1)); series=$((series + n)); ticks=$((ticks + n * largo))
    dif_res=$((dif_res + d)); dif_tick=$((dif_tick + t))
  done
  echo "$e | $lotes | $series | $ticks | $dif_res | $dif_tick"
  echo "$dif_res $dif_tick $series" >> "$TMP/suma.txt"
done
# Control negativo: con el aprendizaje encendido el mismo contador tiene que ver diferencias.
"$ARNES" detalle --estrategia "tabla:cmp=1,ka=8" --lote "$SERIES/remuestreo_s0_n2000.bin" > "$TMP/cand.txt"
neg=$(awk '{s += $7} END {print s+0}' "$TMP/cand.txt")
echo
echo "Control negativo (tabla:cmp=1,ka=8 en remuestreo_s0_n2000): $neg ticks con decision distinta (debe ser mayor que cero)"
if [ "$neg" -le 0 ]; then echo "1 0 0" >> "$TMP/suma.txt"; fi
# Segundo control negativo: un umbral de accion corrido mas de media casilla (64) ya no es max_media.
"$ARNES" detalle --estrategia "tabla:cmp=1,ui=80" --lote "$SERIES/remuestreo_s0_n2000.bin" > "$TMP/cand.txt"
neg2=$(awk '{s += $7} END {print s+0}' "$TMP/cand.txt")
echo "Control negativo (tabla:cmp=1,ui=80 en remuestreo_s0_n2000): $neg2 ticks con decision distinta (debe ser mayor que cero)"
if [ "$neg2" -le 0 ]; then echo "1 0 0" >> "$TMP/suma.txt"; fi
"$ARNES" correr --estrategia max_media --serie "$AQUI/../../../tb/practica.csv" -o "$TMP/dec_ref.csv" > "$TMP/correr_ref.txt"
"$ARNES" correr --estrategia "tabla" --serie "$AQUI/../../../tb/practica.csv" -o "$TMP/dec_tabla.csv" > "$TMP/correr_tabla.txt"
"$ARNES" correr --estrategia "mm_patron:apr=0" --serie "$AQUI/../../../tb/practica.csv" -o "$TMP/dec_filtro.csv" > "$TMP/correr_filtro.txt"
echo
echo "decisiones.csv en la serie de practica completa (20000 filas):"
for x in tabla filtro; do
  if cmp -s "$TMP/dec_ref.csv" "$TMP/dec_$x.csv"; then echo "  $x: identico byte a byte a max_media"; else echo "  $x: DISTINTO"; echo "1 0 0" >> "$TMP/suma.txt"; fi
done
echo "  max_media: $(tail -1 "$TMP/correr_ref.txt")"
echo "  tabla:     $(tail -1 "$TMP/correr_tabla.txt")"
echo
awk '{a += $1; b += $2; s += $3} END {printf "TOTAL: %d corridas de series, %d con resultado distinto, %d ticks con decision distinta\n", s, a, b; if (a + b > 0) {print "EQUIVALENCIA: FALLA"; exit 1} else print "EQUIVALENCIA: OK"}' "$TMP/suma.txt"
estado=$?
rm -f "$TMP/suma.txt"
exit $estado
