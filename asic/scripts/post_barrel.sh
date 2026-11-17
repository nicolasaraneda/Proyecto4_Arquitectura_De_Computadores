#!/usr/bin/env bash
# post_barrel.sh: lo que se mide sobre una corrida terminada del macro ASIC del barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso, desde la raíz: asic/scripts/post_barrel.sh TAG [NTICKS]
#   1. cierre    criterios del Proyecto 3 (asic/verificar_cierre.py del clon en P3):
#                flujo completo, DRC de Magic, LVS, antenas, setup y hold en 9 esquinas
#   2. drc       segundo DRC con el deck de KLayout del Proyecto 3 (684 reglas)
#   3. puertos   el netlist final por sus puertos, con la maestra del testbench
#                oficial, NTICKS ticks (2000 por defecto) a 0,1 ms contra ref/fondo.py
#   4. potencia  asic/scripts/potencia_barrel.sh (actividad real, VCD en /dev/shm)
# Mismos pasos que factibilidad/g_asic para el base (cierre, drc-klayout, puertos y
# potencia). Las salidas quedan en asic/mediciones/TAG/.
set -uo pipefail
source asic/scripts/fuentes.sh
TAG=$1; NT=${2:-2000}
P3=${P3:-$HOME/proyectos/Proyecto3_Arquitectura_De_Computadores}
PDK_ROOT=${PDK_ROOT:-$HOME/.ciel/ciel/gf180mcu/versions/54435919abffb937387ec956209f9cf5fd2dfbee}
SCL=gf180mcu_fd_sc_mcu7t5v0
CELDAS_V="$PDK_ROOT/gf180mcuD/libs.ref/$SCL/verilog/primitives.v $PDK_ROOT/gf180mcuD/libs.ref/$SCL/verilog/$SCL.v"
IMG=ghcr.io/librelane/librelane:3.0.16
RUN=$A/runs/$TAG
M=$A/mediciones/$TAG
B=$A/build/post/$TAG
mkdir -p "$M" "$B"
[ -f "$RUN/final/metrics.json" ] || { echo "FAIL: $RUN no terminó"; exit 1; }
fallas=0

echo "== 1. cierre"
python3 "$P3/asic/verificar_cierre.py" "$RUN" --md "$M/cierre.md" > /dev/null
r=$(grep -o 'Resultado: [A-Z ]*' "$M/cierre.md"); echo "$TAG: $r"
[ "$r" = "Resultado: CIERRA" ] || fallas=$((fallas+1))

echo "== 2. drc de KLayout"
GDS=$(pwd)/$RUN/final/gds/asic_top_barrel.gds
INICIO=$(date +%s)
if docker run --rm --user "$(id -u):$(id -g)" -v "$HOME:$HOME" -w "$(pwd)" -e HOME="$HOME" "$IMG" \
     klayout -b -zz -r "$P3/asic/drc/gf180mcu.drc" \
       -rd "input=$GDS" -rd topcell=asic_top_barrel -rd "report=$(pwd)/$B/drc.lyrdb" \
       -rd feol=true -rd beol=true -rd offgrid=true -rd conn_drc=false \
       -rd metal_top=11K -rd mim_option=B -rd metal_level=5LM \
       -rd run_mode=flat -rd thr=4 > "$B/drc.log" 2>&1; then
  python3 "$P3/asic/drc/resumir.py" "$B/drc.lyrdb" --md "$M/drc_klayout.md" --gds "$RUN/final/gds/asic_top_barrel.gds" > /dev/null
  echo "DRC de KLayout de $TAG: $(sed -n 3p "$M/drc_klayout.md") ($(( $(date +%s) - INICIO )) s)"
else
  echo "FAIL: klayout terminó con error (ver $B/drc.log)"; tail -5 "$B/drc.log"; fallas=$((fallas+1))
fi

echo "== 3. netlist final por los puertos, $NT ticks"
NL=$RUN/final/nl/asic_top_barrel.nl.v
iverilog -g2012 -s tb_asic_barrel_puertos -DNETLIST -DFUNCTIONAL -DNTICKS=$NT -DPERIODO_NS=100000 \
  "-DSALIDA=\"$B/bytes.csv\"" -o "$B/sim_puertos" "$NL" $CELDAS_V $A/tb/tb_asic_barrel_puertos.sv
INICIO=$(date +%s)
vvp -n "$B/sim_puertos" > "$B/puertos.log"
python3 ref/fondo.py tb/practica.csv --nticks $NT --periodo-ns 100000 --perdidos 0 -o "$B/ref.csv" > /dev/null
# El tick n de la maestra lee la decisión del tick n-1: se comparan las filas 1 a NT-1
if cmp -s <(head -$NT "$B/bytes.csv" | cut -d, -f3) <(head -$NT "$B/ref.csv" | cut -d, -f3); then
  echo "PASS: $NT bytes del netlist final de $TAG identicos a ref/fondo.py ($(( $(date +%s) - INICIO )) s)" | tee "$M/puertos.txt"
else
  echo "FAIL: el netlist final de $TAG difiere de ref/fondo.py (ver $B/bytes.csv)" | tee "$M/puertos.txt"; fallas=$((fallas+1))
fi

echo "== 4. potencia"
asic/scripts/potencia_barrel.sh "$TAG" todo || fallas=$((fallas+1))

echo "RESULTADO $TAG: $fallas pasos con falla"
exit $fallas
