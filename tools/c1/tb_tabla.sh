#!/usr/bin/env bash
# tb_tabla.sh: testbench del hardware que R3 agrega, la tabla de 512 palabras
# (rtl/pochoco_tabla512.v, tb/c1/tb_tabla512.sv), con sus controles negativos.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   1. El módulo con sw/c1_tabla.hex y con un patrón propio: las 512 palabras, la
#      extensión de signo y la salida quieta sin rd_i.
#   2. Tres copias con un error puesto a propósito tienen que fallar: el índice
#      recortado a 8 bits, la extensión con ceros y la lectura sin mirar rd_i.
#   3. R0 y R2 no cambian: sin -DESPINO_TABLA_512 el SoC no instancia el módulo
#      nuevo (se busca en el netlist de yosys de cada uno).
#
# Uso: tools/c1/tb_tabla.sh   (make c1-tb-tabla). Resultado en docs/mediciones/c1/tb_tabla.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BC/tb_tabla
SALIDA=${SALIDA:-$MC/tb_tabla.txt}
rm -rf "$O"; mkdir -p "$O"
correr() {   # correr NOMBRE FUENTE.v [plusargs]
  local n=$1 v=$2; shift 2
  iverilog -g2012 -s tb_tabla512 -o "$O/$n" "$v" tb/c1/tb_tabla512.sv 2> "$O/$n.err" || { echo "FAIL: no compila"; return; }
  vvp -n "$O/$n" "$@" | grep -E "^(PASS|FAIL)" | tail -1
}
mutar() {    # mutar NOMBRE EXPRESION_SED
  sed -e "$2" rtl/pochoco_tabla512.v > "$O/$1.v"
  cmp -s rtl/pochoco_tabla512.v "$O/$1.v" && echo "(la mutacion $1 no cambio nada)"
}
{
cabecera "Testbench de la tabla de 512 palabras de R3 (rtl/pochoco_tabla512.v)" tools/c1/tb_tabla.sh "make c1-tb-tabla"
echo "1. El modulo sin cambios"
echo "$(correr sano rtl/pochoco_tabla512.v) (contenido de sw/c1_tabla.hex)"
echo "$(correr patron rtl/pochoco_tabla512.v +PATRON=1) (patron propio, todas las palabras distintas)"
echo
echo "2. Controles negativos: cada copia con un error tiene que fallar"
mutar indice 's/q <= mem\[idx_i\]/q <= mem[{1'"'"'b0, idx_i[7:0]}]/'
mutar signo 's/assign rdata_o = {{16{q\[15\]}}, q}/assign rdata_o = {16'"'"'b0, q}/'
mutar sin_rd 's/if (rd_i) q <= mem\[idx_i\]/q <= mem[idx_i]/'
for m in indice signo sin_rd; do
  r=$(correr $m "$O/$m.v" +PATRON=1)
  if echo "$r" | grep -q "^FAIL"; then echo "DETECTADO $m: $r"; else echo "FAIL $m: no se detecto ($r)"; fi
done
echo
echo "3. Sin -DESPINO_TABLA_512 el SoC no usa el modulo nuevo"
for par in "r0:" "r2:$R2_DEFS" "r3:$C1_DEFS"; do
  n=${par%%:*}; defs=${par#*:}
  yosys -p "read_verilog $defs $BASE_SRC; hierarchy -top pochoco_soc; stat" 2>/dev/null | grep -c "^=== .*pochoco_tabla512" > "$O/$n.cuenta" || true
  c=$(cat "$O/$n.cuenta")
  if [ "$n" = r3 ]; then [ "$c" -ge 1 ] && echo "PASS r3: instancia pochoco_tabla512" || echo "FAIL r3: no instancia pochoco_tabla512"
  else [ "$c" = 0 ] && echo "PASS $n: no instancia pochoco_tabla512" || echo "FAIL $n: instancia pochoco_tabla512"; fi
done
} | tee "$SALIDA"
cierre "$SALIDA"
