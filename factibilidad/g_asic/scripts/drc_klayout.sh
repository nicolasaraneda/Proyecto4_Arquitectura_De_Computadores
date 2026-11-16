#!/usr/bin/env bash
# drc_klayout.sh: segundo DRC, independiente del de Magic, sobre el GDS final
# de una corrida.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# LibreLane salta el paso KLayout.DRC con gf180mcuD, porque el deck que trae
# el PDK instalado es una plantilla sin reglas. Nuestro Proyecto 3 resolvió
# eso con el deck monolítico de GF180MCU (asic/drc/gf180mcu.drc, su origen
# está en asic/drc/ORIGEN.md de ese repositorio). Este script usa ese deck y
# su resumen tal como están en el clon del Proyecto 3, sin copiarlos: para la
# edición ASIC habría que traerlos a este repositorio.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/g_asic/scripts/drc_klayout.sh TAG
# Variables: P3 (clon del Proyecto 3) e HILOS (2 por defecto).
# Deja el log y la base de marcadores en build/drc_klayout/TAG/ y el resumen
# por regla en mediciones/TAG/drc_klayout.md.
set -euo pipefail
G=factibilidad/g_asic
TAG=$1
P3=${P3:?defina P3 con la ruta de un clon del Proyecto 3}
HILOS=${HILOS:-2}
IMAGEN=ghcr.io/librelane/librelane:3.0.16
GDS=$(pwd)/$G/runs/$TAG/final/gds/asic_top.gds
OUT=$(pwd)/$G/build/drc_klayout/$TAG
[ -f "$GDS" ] || { echo "no existe $GDS: la corrida $TAG no terminó"; exit 1; }
[ -f "$P3/asic/drc/gf180mcu.drc" ] || { echo "no está el deck en $P3/asic/drc/gf180mcu.drc"; exit 1; }
mkdir -p "$OUT" "$G/mediciones/$TAG"
INICIO=$(date +%s)
docker run --rm --user "$(id -u):$(id -g)" -v "$HOME:$HOME" -w "$(pwd)" -e HOME="$HOME" "$IMAGEN" \
  klayout -b -zz -r "$P3/asic/drc/gf180mcu.drc" \
    -rd "input=$GDS" -rd topcell=asic_top -rd "report=$OUT/drc.lyrdb" \
    -rd feol=true -rd beol=true -rd offgrid=true -rd conn_drc=false \
    -rd metal_top=11K -rd mim_option=B -rd metal_level=5LM \
    -rd run_mode=flat -rd "thr=$HILOS" > "$OUT/drc.log" 2>&1 || { echo "klayout terminó con error; ver $OUT/drc.log"; tail -5 "$OUT/drc.log"; exit 1; }
python3 "$P3/asic/drc/resumir.py" "$OUT/drc.lyrdb" --md "$G/mediciones/$TAG/drc_klayout.md" --gds "$G/runs/$TAG/final/gds/asic_top.gds" > /dev/null
echo "DRC de KLayout de $TAG: $(sed -n 3p "$G/mediciones/$TAG/drc_klayout.md") ($(( $(date +%s) - INICIO )) s)"
