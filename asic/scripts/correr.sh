#!/usr/bin/env bash
# correr.sh: una corrida de LibreLane del macro ASIC del barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso, desde la raíz del repositorio:
#   asic/scripts/correr.sh TAG XD PERIODO_NS [opciones de librelane]
#     TAG         nombre de la corrida: queda en asic/runs/TAG
#     XD          3 (emad y devk, el hardware de R1) o 7 (agrega mulstep)
#     PERIODO_NS  CLOCK_PERIOD
# Ejemplos:
#   asic/scripts/correr.sh barrel_t40 3 40
#   asic/scripts/correr.sh barrel_sint 3 40 --to Yosys.Synthesis
#
# LibreLane 3.0.16 en Docker con GF180MCU, igual que la edición ASIC del base
# (factibilidad/g_asic) y el Proyecto 3. LibreLane se toma del entorno virtual
# LIBRELANE_VENV (por defecto ~/herramientas/librelane). El registro queda en
# asic/build/logs/TAG.log y la duración en asic/build/logs/TAG.tiempo.
set -euo pipefail
source asic/scripts/fuentes.sh
VENV=${LIBRELANE_VENV:-$HOME/herramientas/librelane}
# shellcheck disable=SC1091
[ -f "$VENV/bin/activate" ] && source "$VENV/bin/activate"
LIBRELANE=${LIBRELANE:-librelane --docker-no-tty --dockerized --pdk gf180mcuD}
TAG=$1; XD=$2; T=$3; shift 3
case $XD in 3|7) ;; *) echo "XD tiene que ser 3 o 7"; exit 1 ;; esac
generar_rom
mkdir -p $A/build/logs
INICIO=$(date +%s)
set +e
$LIBRELANE $A/config_barrel.yaml -c CLOCK_PERIOD="$T" -c "SYNTH_PARAMETERS=Xd=$XD,DataWords=16" \
  "$@" --run-tag "$TAG" --overwrite > $A/build/logs/$TAG.log 2>&1
CODIGO=$?
set -e
echo "$TAG xd=$XD periodo=$T codigo=$CODIGO segundos=$(( $(date +%s) - INICIO ))" | tee $A/build/logs/$TAG.tiempo
exit $CODIGO
