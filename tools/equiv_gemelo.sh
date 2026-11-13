#!/usr/bin/env bash
# equiv_gemelo.sh: los 20 000 ticks de práctica en el gemelo digital contra la
# referencia en Python.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre sw/trade.hex en el gemelo (ref/gemelo/gemelo.c) con el timing del
# testbench oficial, a los períodos de las tres rondas, y exige que el
# decisiones.csv sea idéntico byte a byte al de ref/trader.py y que los cuatro
# chequeos del testbench pasen. Reemplaza en la integración continua a la
# corrida de 20 000 ticks con Icarus (make equiv-r3), que queda como ejecución
# manual. El gemelo se valida contra el RTL en make cosim.
#
# Uso, desde la raíz del repositorio: tools/equiv_gemelo.sh [NTICKS]
# Variables de entorno: HEX (por defecto sw/trade.hex), SERIE (tb/practica.csv),
# GEM_OPTS (opciones para el gemelo, por ejemplo --pipeline para el core
# segmentado) y ETQ (sufijo de la carpeta de salida).
set -euo pipefail

NTICKS=${1:-20000}
HEX=${HEX:-sw/trade.hex}
SERIE=${SERIE:-tb/practica.csv}
PYTHON=${PYTHON:-python3}
G=build/gemelo
GEM_OPTS=${GEM_OPTS:-}
ETQ=${ETQ:-}
D=build/equiv/gemelo${ETQ:+_$ETQ}
mkdir -p "$D"
[ -x "$G" ] || { echo "falta $G: correr make gemelo"; exit 1; }

for PERIODO_NS in 100000 1000000 10000000; do
  "$G" $GEM_OPTS --hex "$HEX" --serie "$SERIE" --periodo-ns "$PERIODO_NS" --nticks "$NTICKS" \
       --csv "$D/gem_$PERIODO_NS.csv" > "$D/gem_$PERIODO_NS.log"
  $PYTHON ref/trader.py "$SERIE" --nticks "$NTICKS" --periodo-ns "$PERIODO_NS" \
       -o "$D/ref_$PERIODO_NS.csv" > "$D/ref_$PERIODO_NS.log"

  RESUMEN="gemelo${ETQ:+ ($ETQ)}: periodo $PERIODO_NS ns, $NTICKS ticks, $SERIE, $(grep 'Peor caso' "$D/gem_$PERIODO_NS.log" | sed 's/  */ /g')"
  if ! grep -q "Testbenchs aprobados: 4/4" "$D/gem_$PERIODO_NS.log"; then
    echo "FAIL $RESUMEN: no entrega 4/4"; exit 1
  fi
  if ! cmp "$D/gem_$PERIODO_NS.csv" "$D/ref_$PERIODO_NS.csv"; then
    echo "FAIL $RESUMEN: decisiones distintas a la referencia"; exit 1
  fi
  echo "PASS $RESUMEN, 4/4, $(($(wc -l < "$D/gem_$PERIODO_NS.csv") - 1)) filas identicas a ref/trader.py, patrimonio $(tail -1 "$D/gem_$PERIODO_NS.csv" | cut -d, -f6)"
done
