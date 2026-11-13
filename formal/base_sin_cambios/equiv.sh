#!/usr/bin/env bash
# equiv.sh: prueba formal de que el Espino base no cambió.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Para agregar el pipeline se editaron las etapas IF e ID del core, que el
# Espino base comparte con el segmentado. Con Pipeline = 0 deben generar la
# lógica original. Este script lo demuestra con los pases equiv_* de Yosys
# (el método de asic/eqy del Proyecto 3): compara cada etapa del repositorio
# base (etiqueta base-curso) con la actual, registro por registro y salida por
# salida, y exige que todas las celdas $equiv queden probadas.
#
# El decodificador y la ALU van dentro de la etapa ID, así que quedan
# cubiertos. No cubre pochoco_ram.v ni espino_register_file.v, cuyos cambios
# con Pipeline = 0 son de cableado (se leen en el diff) y que tienen memorias,
# ni el cableado de espino_core.v y pochoco_soc.v. Eso lo cubren make cosim y
# make equiv.
#
# Uso, desde la raíz del repositorio: formal/base_sin_cambios/equiv.sh
set -euo pipefail

D=build/formal_base
mkdir -p "$D/gold"
# En la integración continua el repositorio se clona sin etiquetas
if ! git rev-parse -q --verify refs/tags/base-curso > /dev/null; then
  git fetch -q --depth 1 origin tag base-curso
fi
git archive base-curso rtl | tar -x -C "$D/gold"
W=formal/base_sin_cambios/envoltorios.v

probar() {   # probar MODULO_ENVOLTORIO  [renombres del lado nuevo...]
  local top=$1; shift
  local ren="cd $top;"
  for r in "$@"; do ren="$ren rename \\${r%%=*} \\${r##*=};"; done
  yosys -q -l "$D/$top.log" -p "
    read_verilog -DORIGINAL $D/gold/rtl/espino_core/*.v $W
    hierarchy -top $top; proc; flatten; async2sync; opt_clean; rename $top gold; design -stash gold
    read_verilog rtl/espino_core/*.v $W
    hierarchy -top $top; proc; flatten; async2sync; opt_clean; $ren cd ..; rename $top gate; design -stash gate
    design -copy-from gold -as gold gold
    design -copy-from gate -as gate gate
    equiv_make gold gate equiv
    hierarchy -top equiv
    equiv_simple
    equiv_induct
    equiv_status -assert
  "
  echo "PASS $top: $(grep -E 'Found [0-9]+ \$equiv cells' "$D/$top.log" | tail -1 | sed -E 's/.*Found ([0-9]+) .*/\1/') puntos de comparacion, todos probados equivalentes"
}

probar w_if
probar w_id 'u.g_base.ops_valid_q=u.ops_valid_q'
echo "PASS: con Pipeline = 0 las etapas IF e ID son equivalentes a las del repositorio base"
