#!/bin/bash
# v5_todo.sh: repite todas las etapas de la sección 15 (docs/exploracion_ideas.md) con el código actual.
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz. Arquitectura de Computadores, Universidad de los Andes, 2026-2.
# Uso, desde la raíz de la rama: export P4_DATOS=~/proyectos/datos_p4; ref/cotas/v5_todo.sh
# Cada etapa deja su registro en build/clon/v5_<etapa>.log y una línea de inicio y fin en build/clon/v5_todo.log.
mkdir -p build/clon
for e in finalistas compuestas varas base30 regimen fino ambicion motor faseA faseD; do
  echo "$(date +%H:%M:%S) inicio $e" >> build/clon/v5_todo.log
  python3 ref/cotas/explorar_v5.py $e > build/clon/v5_$e.out 2>&1
  echo "$(date +%H:%M:%S) fin $e (código $?)" >> build/clon/v5_todo.log
done
for g in v5_causal.py v5_mezclas.py v5_diag.py v5_puntaje.py; do
  echo "$(date +%H:%M:%S) inicio $g" >> build/clon/v5_todo.log
  python3 ref/cotas/$g > build/clon/${g%.py}.out 2>&1
  echo "$(date +%H:%M:%S) fin $g (código $?)" >> build/clon/v5_todo.log
done
