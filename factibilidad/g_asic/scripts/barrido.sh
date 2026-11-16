#!/usr/bin/env bash
# barrido.sh: varias corridas de LibreLane, a lo más PAR a la vez.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso, desde la raíz del repositorio:
#   PAR=2 factibilidad/g_asic/scripts/barrido.sh VARIANTE:PERIODO [VARIANTE:PERIODO ...]
# Ejemplo (barrido de período de las dos variantes):
#   PAR=2 factibilidad/g_asic/scripts/barrido.sh base:30 base:25 seg:30 seg:25
# Cada corrida queda con el tag VARIANTE_tPERIODO (el punto decimal se escribe
# con p: seg_t21p5) y usa a lo más 2 hilos (config.yaml). Una corrida que no
# cierra timing igual termina: el resultado se lee con scripts/recolectar.py.
set -uo pipefail
PAR=${PAR:-2}
printf '%s\n' "$@" | xargs -P "$PAR" -I{} bash -c '
  v=${1%%:*}; t=${1##*:}
  factibilidad/g_asic/scripts/correr.sh ${v}_t${t/./p} $v $t > /dev/null 2>&1
  cat factibilidad/g_asic/build/logs/${v}_t${t/./p}.tiempo
' _ {}
