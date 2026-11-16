#!/usr/bin/env bash
# no_aplican.sh: prueba formal de que tres mutaciones de la extensión de la ISA
# no cambian nada en el core cuando la extensión no tiene mulstep (máscara 3,
# la de R1 y R2). Es parte del criterio 5 en la configuración exacta
# (tools/fondo/criterio5.sh).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# MUTA_XD_F7MUL, MUTA_XD_BCERO y MUTA_XD_ANULA cambian solo lógica de mulstep.
# La campaña de simulación no las puede detectar en R1, y no hace falta: lo que
# hay que mostrar es que con la máscara 3 el core mutado es el mismo core. Se
# hace con los pases equiv_make, equiv_simple y equiv_induct de Yosys, con el
# mismo envoltorio y el mismo banco de registros en caja negra que usa la
# equivalencia del paquete P2 (tools/xd/formal.sh, formal/xd/). Como control,
# la misma prueba con MUTA_XD_K4, que sí toca lógica presente, tiene que fallar.
#
# No depende del SoC: el resultado vale igual para R1 y para R2.
#
# Uso: tools/fondo/no_aplican.sh   (lo llama make fondo-criterio5)
# Resultado en docs/mediciones/fondo/HW/criterio5_no_aplican.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BF/criterio5/no_aplican
FOX=formal/xd
XD_V=rtl/espino_core/espino_xd.v
FUENTES_EQ="rtl/espino_core/espino_decoder.v rtl/espino_core/espino_alu.v rtl/espino_core/espino_load_store_unit.v $FOX/regfile_caja.v $FOX/envoltorio_core.v"
NO_APLICAN="MUTA_XD_F7MUL MUTA_XD_BCERO MUTA_XD_ANULA"
mkdir -p "$O"

# equivalencia MUTACION: el core con la máscara 3 contra el mismo core mutado
equivalencia() {
  local m=$1
  yosys -q -l "$O/$m.log" -p "
    read_verilog -DLADO_XD=3 $CORE_V $XD_V $FUENTES_EQ
    hierarchy -top w_core; proc; flatten; async2sync; expose -evert t:espino_barrel_regfile; opt_clean; rename w_core gold; design -stash gold
    read_verilog -DLADO_XD=3 -D$m $CORE_V $XD_V $FUENTES_EQ
    hierarchy -top w_core; proc; flatten; async2sync; expose -evert t:espino_barrel_regfile; opt_clean; rename w_core gate; design -stash gate
    design -copy-from gold -as gold gold
    design -copy-from gate -as gate gate
    equiv_make gold gate equiv
    hierarchy -top equiv
    equiv_simple
    equiv_induct
    equiv_status -assert
  " > /dev/null 2>&1
  echo $? > "$O/$m.rc"
}
for m in $NO_APLICAN MUTA_XD_K4; do equivalencia $m & done
wait
puntos() { grep -oE 'Found [0-9]+ \$equiv cells' "$O/$1.log" | tail -1 | grep -oE '[0-9]+'; }

{
cabecera "Criterio 5: mutaciones de la extension que no aplican a la mascara 3 (emad y devk)" tools/fondo/no_aplican.sh "make fondo-criterio5 HW=$HW"
echo "El core con Xd = 3 contra el mismo core con cada mutacion, con equiv_make, equiv_simple y equiv_induct."
for m in $NO_APLICAN; do
  if [ "$(cat "$O/$m.rc")" = 0 ]; then echo "PASS $m: el core mutado es equivalente al core sin mutar ($(puntos $m) puntos de comparacion, todos probados). La logica que cambia no existe sin mulstep"
  else echo "FAIL $m: el core mutado no es equivalente; la mutacion si aplica y habria que detectarla (ver $O/$m.log)"; fi
done
if [ "$(cat "$O/MUTA_XD_K4.rc")" != 0 ]; then echo "PASS control: con MUTA_XD_K4, que si toca logica presente, la equivalencia falla"
else echo "FAIL control: la equivalencia pasa con una mutacion que si aplica"; fi
} | tee "$MF/criterio5_no_aplican.txt"
cierre "$MF/criterio5_no_aplican.txt"
