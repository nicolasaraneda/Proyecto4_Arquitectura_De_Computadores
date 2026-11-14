#!/usr/bin/env bash
# correr.sh: una corrida de LibreLane del macro ASIC.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/g_asic/scripts/correr.sh TAG VARIANTE PERIODO_NS [opciones de librelane]
#     TAG         nombre de la corrida: queda en factibilidad/g_asic/runs/TAG
#     VARIANTE    base (Espino base) o seg (pipeline de 3 etapas)
#     PERIODO_NS  CLOCK_PERIOD
# Ejemplos:
#   factibilidad/g_asic/scripts/correr.sh base_t40 base 40
#   factibilidad/g_asic/scripts/correr.sh seg_sint seg 40 --to Yosys.Synthesis
#   factibilidad/g_asic/scripts/correr.sh seg_jer seg 40 -c SYNTH_HIERARCHY_MODE=keep --to Yosys.Synthesis
# Con la variable CONFIG se usa otro archivo de configuración, por ejemplo el
# del shifter completo (config_shifter.yaml, que genera scripts/shifter.sh):
#   CONFIG=factibilidad/g_asic/config_shifter.yaml factibilidad/g_asic/scripts/correr.sh base_shifter_t40 base 40
#
# Usa LibreLane 3.0.16 en Docker con GF180MCU, igual que el Proyecto 3. El
# registro queda en factibilidad/g_asic/build/logs/TAG.log y la duración en
# factibilidad/g_asic/build/logs/TAG.tiempo.
set -euo pipefail
source factibilidad/g_asic/scripts/fuentes.sh
LIBRELANE=${LIBRELANE:-$HOME/herramientas/librelane/bin/librelane --docker-no-tty --dockerized --pdk gf180mcuD}

TAG=$1; VAR=$2; T=$3; shift 3
case $VAR in
  base) P=0 ;;
  seg)  P=2 ;;
  *) echo "variante desconocida: $VAR (base o seg)"; exit 1 ;;
esac
generar_rom
mkdir -p $G/build/logs
INICIO=$(date +%s)
set +e
$LIBRELANE ${CONFIG:-$G/config.yaml} -c CLOCK_PERIOD="$T" -c "SYNTH_PARAMETERS=Pipeline=$P,DataWords=4" \
  "$@" --run-tag "$TAG" --overwrite > $G/build/logs/$TAG.log 2>&1
CODIGO=$?
set -e
echo "$TAG variante=$VAR periodo=$T codigo=$CODIGO segundos=$(( $(date +%s) - INICIO ))" | tee $G/build/logs/$TAG.tiempo
exit $CODIGO
