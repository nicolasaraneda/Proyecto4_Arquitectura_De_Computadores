#!/usr/bin/env bash
# memoria.sh: cuánto cuesta la RAM de datos en flip-flops según su tamaño, y
# qué macros SRAM trae el PDK instalado.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/g_asic/scripts/memoria.sh [PALABRAS ...]
# Por defecto sintetiza el macro con el Espino base y 4, 16, 64, 128, 256 y 512
# palabras de datos (solo hasta Yosys.Synthesis, con la jerarquía conservada) y escribe
# la tabla en factibilidad/g_asic/mediciones/memoria.md con
# scripts/memoria.py. Cada corrida queda en runs/base_dwN.
#
# No usa scripts/correr.sh porque ese fija DataWords = 4, que es el valor de
# todas las corridas completas.
set -uo pipefail
source factibilidad/g_asic/scripts/fuentes.sh
LIBRELANE=${LIBRELANE:-$HOME/herramientas/librelane/bin/librelane --docker-no-tty --dockerized --pdk gf180mcuD}
MAX_S=${MAX_S:-1500}

PALABRAS=${*:-4 16 64 128 256 512}
generar_rom
mkdir -p $G/build/logs
TAGS=""
for n in $PALABRAS; do
  tag=base_dw$n
  # Una síntesis que ya está hecha no se repite (REHACER=1 la fuerza)
  if [ "${REHACER:-0}" = 0 ] && ls $G/runs/$tag/*-yosys-synthesis/reports/stat.json > /dev/null 2>&1; then
    echo "$tag datawords=$n ya estaba ($(cat $G/build/logs/$tag.tiempo 2>/dev/null))"
    TAGS="$TAGS $tag"
    continue
  fi
  inicio=$(date +%s)
  timeout "$MAX_S" $LIBRELANE $G/config.yaml -c CLOCK_PERIOD=40 -c "SYNTH_PARAMETERS=Pipeline=0,DataWords=$n" \
    -c SYNTH_HIERARCHY_MODE=keep --to Yosys.Synthesis --run-tag "$tag" --overwrite > $G/build/logs/$tag.log 2>&1
  codigo=$?
  echo "$tag datawords=$n codigo=$codigo segundos=$(( $(date +%s) - inicio ))" | tee $G/build/logs/$tag.tiempo
  [ "$codigo" = 0 ] && TAGS="$TAGS $tag"
done
python3 $G/scripts/memoria.py $TAGS --md $G/mediciones/memoria.md
