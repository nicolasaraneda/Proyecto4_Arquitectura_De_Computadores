#!/usr/bin/env bash
# formal.sh: prueba formal de la extensión de la ISA en custom-0.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Tres partes:
#
#   A. Cada instrucción contra su especificación (SymbiYosys, por inducción).
#      Copia rtl/espino_core/espino_barrel_core.v, le inserta las propiedades
#      de formal/barrel/propiedades.vh (P1 a P11, las de estructura del barrel)
#      y las de formal/xd/propiedades_xd.vh (X1 a X5) y las prueba para cada
#      subconjunto Xd de 1 a 7. La instrucción que entrega la memoria, el dato
#      del bus y lo que entrega el banco quedan libres. Con el subconjunto
#      completo se repiten además las tareas de arranque y de operandos del
#      barrel. Una tarea de cobertura comprueba que las pruebas no son vacías.
#
#   B. El core con la extensión contra el core sin ella (pases equiv_* de
#      Yosys, el método de formal/base_sin_cambios). La referencia es el core
#      barrel tal como quedó verificado en el paquete P1 (commit CORE_P1).
#        B1. Con Xd = 0 el core de hoy es equivalente al de P1, registro por
#            registro y salida por salida.
#        B2. Con cada subconjunto, si las palabras de custom-0 se reemplazan
#            por un nop a la entrada de los dos, también: la extensión no
#            cambia nada de lo que hace un programa de RV32E.
#        B3. Control: sin ese reemplazo la equivalencia tiene que FALLAR.
#      El banco de registros es una caja negra con sus puertos expuestos.
#
#   C. Controles negativos: las tareas de la parte A sobre el core con cada
#      error puesto a propósito (los `ifdef MUTA_XD_* del RTL). Cada uno tiene
#      que producir un contraejemplo.
#
# Uso: tools/xd/formal.sh   (o make xd-formal)
# Resultado en docs/mediciones/xd/formal.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BX/formal
CORE_P1=0fb8ae8305fc29602847860f529a8765d2889144
MUTAS=${MUTAS:-"MUTA_XD_K MUTA_XD_F7MUL MUTA_XD_SRL MUTA_XD_K4 MUTA_XD_BCERO MUTA_XD_WE MUTA_XD_HILO MUTA_XD_ANULA MUTA_XD_SUMA"}
PROF=${PROF:-10}
JOBS=${JOBS:-4}
rm -rf "$O"; mkdir -p "$O"

$PYTHON - "$CORE_V" "$FO/propiedades.vh" "$FOX/propiedades_xd.vh" "$O/espino_barrel_core_formal.v" <<'PY'
import sys
core = open(sys.argv[1], encoding="utf-8").read()
prop = open(sys.argv[2], encoding="utf-8").read() + "\n" + open(sys.argv[3], encoding="utf-8").read()
assert core.count("endmodule") == 1
i = core.rindex("endmodule")
open(sys.argv[4], "w", encoding="utf-8", newline="\n").write(core[:i] + "`ifdef FORMAL\n" + prop + "`endif\n\n" + core[i:])
PY

# probar NOMBRE MASCARA [-DMUTA...]: las tareas de la parte A
probar() {
  local n=$1 m=$2 def=${3:-} d=$O/$1
  mkdir -p "$d"
  cat > "$d/xd.sby" <<SBY
[tasks]
instrucciones
cobertura
arranque
operandos

[options]
instrucciones: mode prove
instrucciones: depth $PROF
cobertura: mode cover
cobertura: depth 12
arranque: mode bmc
arranque: depth 12
operandos: mode prove
operandos: depth $PROF

[engines]
smtbmc boolector

[script]
instrucciones: read_verilog -formal -sv -DFORMAL $def espino_barrel_core_formal.v
cobertura: read_verilog -formal -sv -DFORMAL -DFORMAL_XD_COBERTURA $def espino_barrel_core_formal.v
arranque: read_verilog -formal -sv -DFORMAL -DFORMAL_ARRANQUE $def espino_barrel_core_formal.v
operandos: read_verilog -formal -sv -DFORMAL -DFORMAL_ESPIA $def espino_barrel_core_formal.v
read_verilog -formal -sv $def espino_xd.v
read_verilog -formal -sv espino_decoder.v espino_alu.v espino_load_store_unit.v
operandos: read_verilog -formal -sv regfile_espia.v
instrucciones: read_verilog -formal -sv regfile_abstracto.v
cobertura: read_verilog -formal -sv regfile_abstracto.v
arranque: read_verilog -formal -sv regfile_abstracto.v
chparam -set Xd 3'd$m espino_barrel_core
prep -top espino_barrel_core
async2sync

[files]
$RAIZ/$O/espino_barrel_core_formal.v
$RAIZ/$XD_V
$RAIZ/rtl/espino_core/espino_decoder.v
$RAIZ/rtl/espino_core/espino_alu.v
$RAIZ/rtl/espino_core/espino_load_store_unit.v
$RAIZ/$FO/regfile_abstracto.v
$RAIZ/$FO/regfile_espia.v
SBY
  local tareas="instrucciones"
  [ -z "$def" ] && tareas="instrucciones cobertura"
  [ -z "$def" ] && [ "$m" = 7 ] && tareas="instrucciones cobertura arranque operandos"
  ( cd "$d" && sby -f xd.sby $tareas > sby.log 2>&1 )
  return 0
}
estado() { head -1 "$O/$1/xd_$2/status" 2>/dev/null | cut -d' ' -f1; }
export -f probar estado
export O PROF RAIZ XD_V FO

# equivalencia NOMBRE "DEFS_REFERENCIA" "DEFS_NUEVO": pases equiv_* de Yosys
FUENTES_EQ="rtl/espino_core/espino_decoder.v rtl/espino_core/espino_alu.v rtl/espino_core/espino_load_store_unit.v $FOX/regfile_caja.v $FOX/envoltorio_core.v"
equivalencia() {
  local n=$1 dg=$2 dn=$3
  yosys -q -l "$O/eq_$n.log" -p "
    read_verilog -DCORE_P1 $dg $O/core_p1.v $FUENTES_EQ
    hierarchy -top w_core; proc; flatten; async2sync; expose -evert t:espino_barrel_regfile; opt_clean; rename w_core gold; design -stash gold
    read_verilog $dn $CORE_V $XD_V $FUENTES_EQ
    hierarchy -top w_core; proc; flatten; async2sync; expose -evert t:espino_barrel_regfile; opt_clean; rename w_core gate; design -stash gate
    design -copy-from gold -as gold gold
    design -copy-from gate -as gate gate
    equiv_make gold gate equiv
    hierarchy -top equiv
    equiv_simple
    equiv_induct
    equiv_status -assert
  " > /dev/null 2>&1
}
puntos() { grep -E 'Found [0-9]+ \$equiv cells in equiv' "$O/eq_$1.log" | tail -1 | sed -E 's/.*Found ([0-9]+) .*/\1/'; }

# --- Parte A y parte C, en paralelo --------------------------------------------
{ for m in 1 2 3 4 5 6 7; do echo "xd_$m $m"; done
  for x in $MUTAS; do echo "muta_$x 7 -D$x"; done; } > "$O/tareas.txt"
xargs -P "$JOBS" -L 1 bash -c 'probar "$0" "$1" "${2:-}"' < "$O/tareas.txt"

# --- Parte B --------------------------------------------------------------------
if ! git cat-file -e "$CORE_P1^{commit}" 2> /dev/null; then
  git fetch -q --depth 1 origin "$CORE_P1"       # la integración continua clona sin historia
fi
git show "$CORE_P1:rtl/espino_core/espino_barrel_core.v" > "$O/core_p1.v"
equivalencia xd0 "" "-DLADO_XD=0"; rc_b1=$?
for m in 1 2 3 4 5 6 7; do equivalencia "nop_$m" "-DSIN_CUSTOM0" "-DSIN_CUSTOM0 -DLADO_XD=$m"; echo $? > "$O/eq_nop_$m.rc"; done
equivalencia control "" "-DLADO_XD=7"; rc_b3=$?

{
echo "Prueba formal de la extension de la ISA en custom-0 (SymbiYosys y Yosys)"
echo "Generado por tools/xd/formal.sh (make xd-formal). No editar a mano."
echo
versiones
echo "  $(sby --version 2>&1 | head -1)"
echo
fallas=0
echo "A. Cada instruccion contra su especificacion, sobre el core barrel"
echo "   Propiedades: formal/xd/propiedades_xd.vh (X1 a X5, $(grep -c 'assert (' $FOX/propiedades_xd.vh) afirmaciones) y formal/barrel/propiedades.vh"
echo "   (P1 a P11, $(grep -c 'assert (' $FO/propiedades.vh) afirmaciones). Entradas libres: la instruccion que entrega la memoria, el dato del"
echo "   bus y lo que entrega el banco de registros. Induccion de profundidad $PROF."
for m in 1 2 3 4 5 6 7; do
  nombre=$(echo "$XD_SUBCONJUNTOS" | grep "^$m:" | cut -d: -f2 | tr '_' ' ')
  e=$(estado "xd_$m" instrucciones); c=$(estado "xd_$m" cobertura)
  if [ "$e" = PASS ] && [ "$c" = PASS ]; then echo "   PASS Xd = $m ($nombre): X1 a X5 y P1 a P8 probadas para cualquier programa; cobertura alcanzada"
  else echo "   FAIL Xd = $m ($nombre): instrucciones $e, cobertura $c (ver $O/xd_$m)"; fallas=$((fallas + 1)); fi
done
for t in arranque operandos; do
  if [ "$(estado xd_7 $t)" = PASS ]; then echo "   PASS Xd = 7: tarea de $t del barrel (make barrel-formal) con la extension"
  else echo "   FAIL Xd = 7: tarea de $t: $(estado xd_7 $t)"; fallas=$((fallas + 1)); fi
done
echo
echo "B. El core con la extension contra el core del paquete P1 (commit ${CORE_P1:0:7}), con equiv_make, equiv_simple y equiv_induct"
if [ $rc_b1 = 0 ]; then echo "   PASS B1. Xd = 0: equivalente al core de P1, $(puntos xd0) puntos de comparacion, todos probados"
else echo "   FAIL B1. Xd = 0 (ver $O/eq_xd0.log)"; fallas=$((fallas + 1)); fi
for m in 1 2 3 4 5 6 7; do
  if [ "$(cat "$O/eq_nop_$m.rc")" = 0 ]; then echo "   PASS B2. Xd = $m con custom-0 reemplazado por nop en los dos lados: equivalente, $(puntos nop_$m) puntos, todos probados"
  else echo "   FAIL B2. Xd = $m (ver $O/eq_nop_$m.log)"; fallas=$((fallas + 1)); fi
done
if [ $rc_b3 != 0 ] && grep -q 'unproven' "$O/eq_control.log"; then
  echo "   PASS B3. Control: Xd = 7 sin el reemplazo NO es equivalente al core de P1 ($(grep -E 'Found a total of [0-9]+ unproven' "$O/eq_control.log" | sed -E 's/.*total of ([0-9]+) .*/\1/') puntos sin probar), como debe ser"
else echo "   FAIL B3. El control de la equivalencia pasa: la prueba B2 no estaria comparando nada"; fallas=$((fallas + 1)); fi
echo
echo "C. Controles negativos: la parte A (Xd = 7) con un error puesto a proposito en el RTL"
total=0; det=0
for x in $MUTAS; do
  total=$((total + 1))
  e=$(estado "muta_$x" instrucciones)
  if [ "$e" = FAIL ]; then det=$((det + 1)); echo "   PASS $x: contraejemplo ($(grep -m1 -oE 'Assert failed in [a-z_]+: [^ ]+' "$O/muta_$x/xd_instrucciones/logfile.txt" | sed -E 's/.*: //; s/.*formal\.v://' ))"
  else echo "   FAIL $x: la prueba responde ${e:-nada} con el error puesto"; fallas=$((fallas + 1)); fi
done
echo
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, las tres instrucciones cumplen su especificacion en los 7 subconjuntos, el resto del core no cambia y $det de $total mutaciones dan contraejemplo"
else echo "RESULTADO: FAIL ($fallas problemas)"; fi
} | tee "$MX/formal.txt"

grep -q "^RESULTADO: PASS" "$MX/formal.txt"
