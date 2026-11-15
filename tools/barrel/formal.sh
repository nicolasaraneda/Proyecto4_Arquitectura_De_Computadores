#!/usr/bin/env bash
# formal.sh: propiedades formales de estructura del Espino barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Copia rtl/espino_core/espino_barrel_core.v, le inserta las propiedades de
# formal/barrel/propiedades.vh antes del endmodule y las prueba con SymbiYosys, en
# tres tareas:
#   invariantes   P1 a P8 por inducción: valen en cualquier ciclo y para
#                 cualquier programa.
#   arranque      P9 con profundidad acotada desde el reset: cada hilo parte
#                 en su entrada, para cualquier contenido de la memoria.
#   operandos     P10 y P11 por inducción: qué contexto y qué registro llegan
#                 al banco en cada lectura y en cada escritura.
# El decodificador, la ALU y la unidad de carga son los del repositorio. El
# banco de registros se reemplaza por formal/barrel/regfile_abstracto.v o por
# formal/barrel/regfile_espia.v.
#
# Controles negativos: las mismas tres tareas sobre copias mutadas del core
# (tools/barrel/mutar.py). Cada mutación de la lista tiene que hacer fallar alguna.
#
# No prueba que cada instrucción calcule lo que debe: eso se comprueba por
# simulación contra el Espino base (tools/barrel/verif.sh). Ver docs/espino_barrel.md.
#
# Uso: tools/barrel/formal.sh   (o make barrel-formal)
# Resultado en docs/mediciones/barrel/formal.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/formal
MUTAS=${MUTAS:-"ctx_escritura ctx_lectura_rs1 ctx_lectura_rs2 rd_otro_hilo x0 pc_otro_hilo peticion_bus burbuja_salta hilo_desfasado"}
# Profundidad de la inducción. Tiene que alcanzar para que el caso base llegue
# a la primera escritura al banco y a lo que el banco espía devuelve después
# (ciclo 5 desde el reset): con menos, un error en la dirección de escritura
# solo hace fallar el paso inductivo y SymbiYosys responde UNKNOWN en vez de
# entregar un contraejemplo desde el reset.
PROF=${PROF:-10}
rm -rf "$O"; mkdir -p "$O"

# probar NOMBRE CORE.v: inserta las propiedades en una copia de CORE.v y corre las tres tareas
probar() {
  local n=$1 core=$2 d=$O/$1
  mkdir -p "$d"
  $PYTHON - "$core" "$FO/propiedades.vh" "$d/espino_barrel_core_formal.v" <<'PY'
import sys
core = open(sys.argv[1], encoding="utf-8").read()
prop = open(sys.argv[2], encoding="utf-8").read()
assert core.count("endmodule") == 1
i = core.rindex("endmodule")
open(sys.argv[3], "w", encoding="utf-8", newline="\n").write(core[:i] + "`ifdef FORMAL\n" + prop + "`endif\n\n" + core[i:])
PY
  cat > "$d/barrel.sby" <<SBY
[tasks]
invariantes
arranque
operandos

[options]
invariantes: mode prove
invariantes: depth $PROF
arranque: mode bmc
arranque: depth 12
operandos: mode prove
operandos: depth $PROF

[engines]
smtbmc boolector

[script]
invariantes: read_verilog -formal -sv -DFORMAL espino_barrel_core_formal.v
arranque: read_verilog -formal -sv -DFORMAL -DFORMAL_ARRANQUE espino_barrel_core_formal.v
operandos: read_verilog -formal -sv -DFORMAL -DFORMAL_ESPIA espino_barrel_core_formal.v
read_verilog -formal -sv espino_decoder.v espino_alu.v espino_load_store_unit.v
invariantes: read_verilog -formal -sv regfile_abstracto.v
arranque: read_verilog -formal -sv regfile_abstracto.v
operandos: read_verilog -formal -sv regfile_espia.v
prep -top espino_barrel_core
async2sync

[files]
$RAIZ/$d/espino_barrel_core_formal.v
$RAIZ/rtl/espino_core/espino_decoder.v
$RAIZ/rtl/espino_core/espino_alu.v
$RAIZ/rtl/espino_core/espino_load_store_unit.v
$RAIZ/$FO/regfile_abstracto.v
$RAIZ/$FO/regfile_espia.v
SBY
  ( cd "$d" && sby -f barrel.sby > sby.log 2>&1 )
  return 0
}
estado() { head -1 "$O/$1/barrel_$2/status" 2>/dev/null | cut -d' ' -f1; }

probar barrel rtl/espino_core/espino_barrel_core.v
# Cobertura: que la tarea de arranque no sea vacía
sed -e 's/^arranque: mode bmc/arranque: mode cover/' "$O/barrel/barrel.sby" > "$O/barrel/cobertura.sby"
( cd "$O/barrel" && sby -f cobertura.sby arranque > cover.log 2>&1 )
for m in $MUTAS; do
  $PYTHON $T/mutar.py "$m" "$O/muta_$m/rtl" > /dev/null && probar "muta_$m" "$O/muta_$m/rtl/espino_barrel_core.v"
done

{
echo "Propiedades formales de estructura del Espino barrel (SymbiYosys)"
echo "Generado por tools/barrel/formal.sh (make barrel-formal). No editar a mano."
echo
versiones
echo "  $(sby --version 2>&1 | head -1)"
echo
echo "Propiedades: formal/barrel/propiedades.vh, insertadas en una copia de rtl/espino_core/espino_barrel_core.v."
echo "Entradas libres: la instruccion que entrega la memoria, el dato del bus y lo que entrega el banco de registros."
echo "Afirmaciones (assert) en el archivo: $(grep -c 'assert (' $FO/propiedades.vh)."
echo
fallas=0
for t in invariantes arranque operandos; do
  case $t in
    invariantes) que="invariantes P1 a P8, por induccion (profundidad $PROF), banco con cualquier valor" ;;
    arranque)    que="P1 a P9 desde el reset, 12 ciclos, para cualquier contenido de la memoria" ;;
    operandos)   que="P1 a P8 mas P10 y P11, por induccion (profundidad $PROF), banco que devuelve sus direcciones" ;;
  esac
  if [ "$(estado barrel $t)" = PASS ]; then echo "PASS $que"
  else echo "FAIL $que: $(estado barrel $t) (ver $O/barrel/barrel_$t/logfile.txt)"; fallas=$((fallas + 1)); fi
done
if [ "$(head -1 "$O/barrel/cobertura_arranque/status" 2>/dev/null | cut -d' ' -f1)" = PASS ]; then
  echo "PASS cobertura: existe una ejecucion que llega al ciclo 6 con una escritura al banco"
else echo "FAIL cobertura"; fallas=$((fallas + 1)); fi
echo
echo "Controles negativos: las mismas tareas sobre el core con un error puesto a proposito (tools/barrel/mutar.py)"
total=0; detectadas=0
for m in $MUTAS; do
  total=$((total + 1))
  det=""; nodem=""
  for t in invariantes arranque operandos; do
    e=$(estado "muta_$m" $t)
    [ "$e" = FAIL ] && det="$det $t"
    [ "$e" = UNKNOWN ] && nodem="$nodem $t"
    [ -z "$e" ] && det="$det ($t-sin-resultado)"
  done
  if echo "$det" | grep -q "sin-resultado"; then echo "FAIL $m: alguna tarea no termino:$det"; fallas=$((fallas + 1))
  elif [ -n "$det" ]; then detectadas=$((detectadas + 1)); echo "PASS $m: hace fallar:$det"
  elif [ -n "$nodem" ]; then echo "FAIL $m: sin contraejemplo desde el reset; solo deja de cerrar la induccion en:$nodem"; fallas=$((fallas + 1))
  else echo "FAIL $m: las tres tareas pasan con el error puesto"; fallas=$((fallas + 1)); fi
done
echo
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, las propiedades valen para cualquier programa y $detectadas de $total mutaciones las hacen fallar"
else echo "RESULTADO: FAIL ($fallas problemas, $detectadas de $total mutaciones detectadas)"; fi
} | tee "$M/formal.txt"

grep -q "^RESULTADO: PASS" "$M/formal.txt"
