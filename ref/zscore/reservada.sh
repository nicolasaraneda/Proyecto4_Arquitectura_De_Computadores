#!/usr/bin/env bash
# reservada.sh: los cuatro finalistas de zscore contra max_media con la semilla 4,
# la reservada (T128). Se corre una sola vez, con la lista de
# docs/bitacora/zscore.md, sección 3. Deja todo en docs/mediciones/zscore/.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: ref/zscore/reservada.sh   (necesita make -C ref/zscore y ref/zscore/series_reservadas.py)
set -uo pipefail
cd "$(dirname "$0")/../.."
export RETORNO_SERIES=${RETORNO_SERIES:-$PWD/build/zscore/series}
export HILOS=${HILOS:-20}
M=docs/mediciones/zscore
mkdir -p "$M"
PY=${PYTHON:-python3}
G="km~5/kd~6/den~4"; H="km~5/kd~7/den~4"
F="fondoz:c=5,w0=6,w1=5,w2=5"; L="m=2,v=9,mg=5,d=4,pp=1,vt=8"
F1="zscore"
F2="zscore:km=5,kd=7,num=6,den=4"
F3="$F,vt=8,g0=cand:max_media,g1=zscore:$G/num~8,g2=zscore:$H/num~6"
F4="$F,$L,g0=zscore:$G/num~9,g1=zscore:$G/num~8,g2=zscore:$G/num~10"

{
  echo "Semilla reservada (4): los finalistas de zscore contra max_media. Generado por ref/zscore/reservada.sh."
  echo "Finalistas (docs/bitacora/zscore.md, seccion 3):"
  echo "  1. $F1"; echo "  2. $F2"; echo "  3. $F3"; echo "  4. $F4"
  echo
  echo "=== Protocolo (ref/protocolo.py, semilla 4): finalistas 1 y 2 ==="
  $PY ref/protocolo.py --semilla 4 --estrategia oficial --comparar "$F1"
  echo
  $PY ref/protocolo.py --semilla 4 --estrategia oficial --comparar "zscore:km=5,kd=7,num=6,den=4"
  echo
  for c in "$F1" "$F2" "$F3" "$F4"; do
    echo "=== Criterio de corte del arnes: $c contra max_media, semilla 4, con la vista de parada ==="
    build/zscore/arnes veredicto --candidata "$c" --referencia max_media --semilla 4 --parada
    echo
  done
} > "$M/reservada_s4.txt" 2>&1

$PY ref/zscore/tabla.py --largo 2000 --semilla 4 --salida "$M/tabla_n2000_s4.txt" > /dev/null
$PY ref/zscore/tabla.py --largo 20000 --semilla 4 --interior --salida "$M/tabla_n20000_s4_interior.txt" > /dev/null
$PY ref/zscore/tabla.py --largo 20000 --semilla 4 --parada --salida "$M/tabla_n20000_s4_parada.txt" > /dev/null
$PY ref/zscore/duelo.py --largo 2000 --semilla 4 --candidatas "$F1;$F2;$F3;$F4" --salida "$M/duelo_n2000_s4.txt" > /dev/null
$PY ref/zscore/duelo.py --largo 20000 --semilla 4 --candidatas "$F1;$F2;$F3;$F4" --salida "$M/duelo_n20000_s4.txt" > /dev/null
echo FIN
