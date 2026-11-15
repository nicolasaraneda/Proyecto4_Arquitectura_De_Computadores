#!/usr/bin/env bash
# formal.sh: las propiedades formales de estructura del barrel, probadas sobre
# el core con la extensión de la ISA integrada.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El estudio del barrel probó con SymbiYosys once propiedades de estructura
# (factibilidad/a_barrel/formal/propiedades.vh): los hilos rotan, no se pisan
# en el banco de registros, x0 no se escribe, cada hilo sigue su propio
# contador de programa y el arranque deja a cada uno en su entrada. Este
# script usa ese mismo archivo, sin copiarlo ni modificarlo, y lo prueba sobre
# rtl/espino_barrel_core.v de esta carpeta con cada subconjunto de la
# extensión, para comprobar que integrar las instrucciones nuevas en la etapa
# X no cambió nada del control del pipeline. El método es el de
# factibilidad/a_barrel/tools/formal.sh: las propiedades se insertan en una
# copia del core (rtl/ no se toca) y quedan libres la instrucción que entrega
# la memoria, el dato del bus y el contenido del banco de registros.
#
# Tareas, por configuración:
#   invariantes   P1 a P8 por inducción
#   arranque      P9 con profundidad acotada desde el reset (12 ciclos)
#   operandos     P10 y P11 por inducción, con el banco que devuelve las
#                 direcciones que vio
#
# Configuraciones: sin definiciones (control), (b) emad, devk y mulstep,
# (c) y (e) con xd_alu y divstep, y (d) y (e) con los carriles en unidad
# aparte y divstep.
#
# Controles negativos: cuatro errores de estructura puestos a propósito en el
# core con la configuración (b). Son reemplazos de texto tomados de
# factibilidad/a_barrel/tools/mutar.py, que se lee sin modificar. Cada uno
# tiene que hacer fallar alguna tarea con un contraejemplo.
#
# No prueba que las instrucciones nuevas calculen lo que deben: eso lo hacen
# tools/tb_xd.sh (contra el modelo) y las pruebas formales de cada módulo en
# factibilidad/d_isa.
#
# Uso: factibilidad/i_integrado/tools/formal.sh   (o make formal)
# Resultado en mediciones/formal.txt. Unos 2 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/formal
PROF=${PROF:-10}
CONFIGS="ref media_mul alu_todo_div bandas_div"
MUTAS="ctx_escritura ctx_lectura_rs1 x0 rd_otro_hilo"
rm -rf "$O"; mkdir -p "$O"

# probar NOMBRE CORE.v "definiciones": inserta las propiedades en una copia de
# CORE.v y corre las tres tareas
probar() {
  local n=$1 core=$2 defs=$3 d=$O/$1 f xd_files="" xd_lista=""
  mkdir -p "$d"
  $PYTHON - "$core" "$A/formal/propiedades.vh" "$d/espino_barrel_core_formal.v" <<'PY'
import sys
core = open(sys.argv[1], encoding="utf-8").read()
prop = open(sys.argv[2], encoding="utf-8").read()
assert core.count("endmodule") == 1
i = core.rindex("endmodule")
open(sys.argv[3], "w", encoding="utf-8", newline="\n").write(core[:i] + "`ifdef FORMAL\n" + prop + "`endif\n\n" + core[i:])
PY
  for f in $XD_SRC; do
    [ "$(basename "$f")" = xd_mul_mmio.v ] && continue
    xd_files="$xd_files $(basename "$f")"
    xd_lista="$xd_lista$RAIZ/$f"$'\n'
  done
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
invariantes: read_verilog -formal -sv -DFORMAL $defs espino_barrel_core_formal.v
arranque: read_verilog -formal -sv -DFORMAL -DFORMAL_ARRANQUE $defs espino_barrel_core_formal.v
operandos: read_verilog -formal -sv -DFORMAL -DFORMAL_ESPIA $defs espino_barrel_core_formal.v
read_verilog -formal -sv espino_decoder_xd.v espino_alu.v espino_load_store_unit.v$xd_files
invariantes: read_verilog -formal -sv regfile_abstracto.v
arranque: read_verilog -formal -sv regfile_abstracto.v
operandos: read_verilog -formal -sv regfile_espia.v
prep -top espino_barrel_core
async2sync

[files]
$RAIZ/$d/espino_barrel_core_formal.v
$RAIZ/$I/rtl/espino_decoder_xd.v
$RAIZ/rtl/espino_core/espino_alu.v
$RAIZ/rtl/espino_core/espino_load_store_unit.v
$RAIZ/$A/formal/regfile_abstracto.v
$RAIZ/$A/formal/regfile_espia.v
$xd_lista
SBY
  ( cd "$d" && sby -f barrel.sby > sby.log 2>&1 )
  return 0
}
estado() { head -1 "$O/$1/barrel_$2/status" 2>/dev/null | cut -d' ' -f1; }

# mutar NOMBRE DESTINO.v: aplica al core de esta carpeta el reemplazo de texto
# que define factibilidad/a_barrel/tools/mutar.py para esa mutación
mutar() {
  $PYTHON - "$1" "$I/rtl/espino_barrel_core.v" "$2" "$A/tools" <<'PY'
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[4])
import mutar
archivo, desc, original, mutado = mutar.MUTACIONES[sys.argv[1]]
assert archivo == mutar.CORE, "la mutacion no es del core"
texto = open(sys.argv[2], encoding="utf-8").read()
assert texto.count(original) == 1, "el texto original no aparece exactamente una vez"
open(sys.argv[3], "w", encoding="utf-8", newline="\n").write(texto.replace(original, mutado))
print(desc)
PY
}

for c in $CONFIGS; do
  probar "$c" $I/rtl/espino_barrel_core.v "$(defs_de "$c")"
done
# Cobertura: que la tarea de arranque no sea vacía (con la configuración (b))
sed -e 's/^arranque: mode bmc/arranque: mode cover/' "$O/media_mul/barrel.sby" > "$O/media_mul/cobertura.sby"
( cd "$O/media_mul" && sby -f cobertura.sby arranque > cover.log 2>&1 )
for m in $MUTAS; do
  mkdir -p "$O/muta_$m"
  mutar "$m" "$O/muta_$m/core.v" > "$O/muta_$m/descripcion.txt" 2> "$O/muta_$m/mutar.err" \
    && probar "muta_$m" "$O/muta_$m/core.v" "$(defs_de media_mul)"
done

{
echo "Propiedades formales de estructura del barrel sobre el core con la extensión (SymbiYosys)"
echo "Generado por factibilidad/i_integrado/tools/formal.sh (make formal). No editar a mano."
echo
versiones
echo "  $(sby --version 2>&1 | head -1)"
echo
echo "Propiedades: $A/formal/propiedades.vh, sin modificar (sha256 $(sha256sum $A/formal/propiedades.vh | cut -c1-16)...),"
echo "insertadas en una copia de $I/rtl/espino_barrel_core.v. Afirmaciones (assert) en el archivo: $(grep -c 'assert (' $A/formal/propiedades.vh)."
echo "Entradas libres: la instrucción que entrega la memoria, el dato del bus y lo que entrega el banco de registros."
echo
fallas=0
for c in $CONFIGS; do
  case $c in
    ref)          desc="sin definiciones (control: es el prototipo del barrel)" ;;
    media_mul)    desc="(b) emad, devk y mulstep en el sumador de la ALU" ;;
    alu_todo_div) desc="(c) y (e): xd_alu en vez de espino_alu, más divstep por xd_unit" ;;
    bandas_div)   desc="(d) y (e): carriles en unidad aparte más divstep (no cabe en la FPGA)" ;;
  esac
  echo "Configuración $c: $desc   [$(defs_de "$c")]"
  for t in invariantes arranque operandos; do
    case $t in
      invariantes) que="invariantes P1 a P8, por inducción (profundidad $PROF), banco con cualquier valor" ;;
      arranque)    que="P1 a P9 desde el reset, 12 ciclos, para cualquier contenido de la memoria" ;;
      operandos)   que="P1 a P8 más P10 y P11, por inducción (profundidad $PROF), banco que devuelve sus direcciones" ;;
    esac
    if [ "$(estado "$c" $t)" = PASS ]; then echo "   PASS $que"
    else echo "   FAIL $que: $(estado "$c" $t) (ver $O/$c/barrel_$t/logfile.txt)"; fallas=$((fallas + 1)); fi
  done
done
echo
if [ "$(head -1 "$O/media_mul/cobertura_arranque/status" 2>/dev/null | cut -d' ' -f1)" = PASS ]; then
  echo "PASS cobertura (configuración media_mul): existe una ejecución que llega al ciclo 6 con una escritura al banco"
else echo "FAIL cobertura"; fallas=$((fallas + 1)); fi
echo
echo "Controles negativos: las mismas tareas sobre el core (configuración media_mul) con un error de estructura puesto a propósito"
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
  if echo "$det" | grep -q "sin-resultado"; then echo "FAIL $m: alguna tarea no terminó:$det"; fallas=$((fallas + 1))
  elif [ -n "$det" ]; then detectadas=$((detectadas + 1)); echo "PASS $m: hace fallar:$det"; echo "      $(cat "$O/muta_$m/descripcion.txt")"
  elif [ -n "$nodem" ]; then echo "FAIL $m: sin contraejemplo desde el reset; solo deja de cerrar la inducción en:$nodem"; fallas=$((fallas + 1))
  else echo "FAIL $m: las tres tareas pasan con el error puesto"; fallas=$((fallas + 1)); fi
done
echo
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, las propiedades valen en las $(echo $CONFIGS | wc -w) configuraciones y $detectadas de $total errores puestos a propósito las hacen fallar"
else echo "RESULTADO: FAIL ($fallas problemas, $detectadas de $total errores detectados)"; fi
} | tee "$M/formal.txt"

grep -q "^RESULTADO: PASS" "$M/formal.txt"
