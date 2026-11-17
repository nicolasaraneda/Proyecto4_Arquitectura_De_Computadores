#!/usr/bin/env bash
# reservada.sh: los tres finalistas de la tarea B contra max_media con la semilla 5, que
# nadie había usado (docs/bitacora/generador_b.md, sección 3). Se corre una sola vez.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: ref/torneo_b/reservada.sh   (necesita make -C ref/torneo_b y las series de la semilla 5)
set -uo pipefail
cd "$(dirname "$0")/../.."
export RETORNO_SERIES=${RETORNO_SERIES:?falta RETORNO_SERIES con las series de la semilla 5}
export HILOS=${HILOS:-8}
M=docs/mediciones/generador_b
mkdir -p "$M"
A=build/torneo_b/arnes
F1="param:k=5,E=80,X=16"; F2="param:k=5,E=80,X=0"; F3="param:k=5,E=96,X=16"
{
  echo "Tarea B, semilla reservada (5): los tres finalistas contra max_media. Generado por ref/torneo_b/reservada.sh."
  echo "  1. $F1 (entra 2,5, sale +0,5)"; echo "  2. $F2 (entra 2,5, sale 0)"; echo "  3. $F3 (entra 3, sale +0,5)"
  echo
  for c in "$F1" "$F2" "$F3"; do
    for campo in variados mixto; do
      echo "=== Criterio de corte: $c contra max_media, campo $campo, semilla 5, con la vista de parada ==="
      RETORNO_CAMPO=$campo $A veredicto --candidata "$c" --referencia max_media --semilla 5 --campo "$campo" --parada
      echo
    done
  done
  echo "=== Protocolo de ref/protocolo.py, semilla 5 ==="
  for e in "E=80,X=16" "E=80,X=0" "E=96,X=16"; do
    python3 ref/protocolo.py --semilla 5 --estrategia oficial --comparar "trader:$e"
    echo
  done
} > "$M/reservada_s5.txt" 2>&1
python3 ref/zscore/duelo.py --largo 2000 --semilla 5 --candidatas "$F1;$F2;$F3" --salida "$M/duelo_n2000_s5.txt" > /dev/null
python3 ref/zscore/duelo.py --largo 20000 --semilla 5 --candidatas "$F1;$F2;$F3" --salida "$M/duelo_n20000_s5.txt" > /dev/null
echo FIN
