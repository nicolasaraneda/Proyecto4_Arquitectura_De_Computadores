#!/usr/bin/env bash
# shifter.sh: cuánto cuesta en el ASIC el shifter completo de la ALU, que en
# la FPGA no cabe (116 % de las celdas, docs/mediciones/base.txt).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/g_asic/scripts/shifter.sh
# Hace lo mismo que tools/medir_base.sh en la FPGA: copia espino_alu.v con las
# tres líneas de sll, srl y sra descomentadas (build/gen/espino_alu_shifter.v,
# el archivo de rtl/ no se toca), genera config_shifter.yaml a partir de
# config.yaml cambiando solo ese archivo, y sintetiza las dos variantes con la
# jerarquía conservada, solo hasta Yosys.Synthesis. La tabla queda en
# mediciones/shifter.md. Necesita las corridas base_jer y seg_jer
# (make sintesis).
set -euo pipefail
source factibilidad/g_asic/scripts/fuentes.sh
LIBRELANE=${LIBRELANE:-librelane --docker-no-tty --dockerized --pdk gf180mcuD}

generar_rom
ALU=$G/build/gen/espino_alu_shifter.v
sed -E 's|// (ALU_S[LR][LA]: +result_o)|\1|' rtl/espino_core/espino_alu.v > $ALU
if [ "$(grep -cE '^ +ALU_S[LR][LA]: +result_o' $ALU)" != 3 ]; then
  echo "FAIL: no se pudieron habilitar las tres lineas del shifter"; exit 1
fi
{
  echo "# GENERADO por scripts/shifter.sh a partir de config.yaml. No editar."
  echo "# Única diferencia: la ALU es build/gen/espino_alu_shifter.v (shifter completo)."
  sed -e 's|dir::../../rtl/espino_core/espino_alu.v|dir::build/gen/espino_alu_shifter.v|' $G/config.yaml
} > $G/config_shifter.yaml
grep -q "espino_alu_shifter.v" $G/config_shifter.yaml || { echo "FAIL: no se pudo generar config_shifter.yaml"; exit 1; }

mkdir -p $G/build/logs
for v in base:0 seg:2; do
  tag=${v%%:*}_shifter_jer
  inicio=$(date +%s)
  $LIBRELANE $G/config_shifter.yaml -c CLOCK_PERIOD=40 -c "SYNTH_PARAMETERS=Pipeline=${v##*:},DataWords=4" \
    -c SYNTH_HIERARCHY_MODE=keep --to Yosys.Synthesis --run-tag "$tag" --overwrite > $G/build/logs/$tag.log 2>&1
  echo "$tag codigo=$? segundos=$(( $(date +%s) - inicio ))" | tee $G/build/logs/$tag.tiempo
done
python3 $G/scripts/sintesis.py base_jer base_shifter_jer seg_jer seg_shifter_jer --resumen espino_alu --md $G/mediciones/shifter.md
