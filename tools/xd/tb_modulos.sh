#!/usr/bin/env bash
# tb_modulos.sh: testbench de los dos módulos de la extensión, solos, contra
# el modelo ref/xd.py, y controles negativos.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre la autoprueba del modelo, genera los vectores con él y simula
# tb/xd/tb_xd_mod.sv con Icarus. Después repite el testbench con cada error
# puesto a propósito en rtl/espino_core/espino_xd.v (`ifdef MUTA_XD_*): los
# cinco que están dentro de esos módulos tienen que hacerlo fallar.
#
# Uso: tools/xd/tb_modulos.sh   (o make xd-tb)
# Resultado en docs/mediciones/xd/tb_modulos.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BX/tb_modulos
N=${N:-300000}
MUTAS="MUTA_XD_K MUTA_XD_F7MUL MUTA_XD_SRL MUTA_XD_K4 MUTA_XD_BCERO"
mkdir -p "$O"
$PYTHON ref/xd.py > "$O/modelo.log" 2>&1; rc_modelo=$?
$PYTHON ref/xd.py --vectores "$N" 1 > "$O/vectores.hex"

correr() {   # correr NOMBRE [definición]
  iverilog -g2012 -s tb_xd_mod ${2:-} -o "$O/$1.vvp" "$XD_V" rtl/espino_core/espino_alu.v $TBX/tb_xd_mod.sv > "$O/$1.iverilog.log" 2>&1 \
    && vvp -n "$O/$1.vvp" "+vectores=$O/vectores.hex" "+n=$N" > "$O/$1.log" 2>&1
}
correr referencia
for m in $MUTAS; do correr "$m" "-D$m" & done; wait

{
echo "Testbench de los modulos de la extension de la ISA (espino_xd_dec y espino_xd_opa) contra ref/xd.py"
echo "Generado por tools/xd/tb_modulos.sh (make xd-tb). No editar a mano."
echo
versiones
echo
fallas=0
if [ $rc_modelo = 0 ]; then cat "$O/modelo.log"; else echo "FAIL autoprueba de ref/xd.py"; fallas=1; fi
if grep -q "^PASS tb_xd_mod" "$O/referencia.log"; then grep "^PASS tb_xd_mod" "$O/referencia.log"
else echo "FAIL tb_xd_mod sin mutar:"; grep -m3 FAIL "$O/referencia.log" "$O/referencia.iverilog.log"; fallas=$((fallas + 1)); fi
echo
echo "Controles negativos (errores puestos a proposito en espino_xd.v):"
det=0; total=0
for m in $MUTAS; do
  total=$((total + 1))
  if grep -q "^FAIL tb_xd_mod" "$O/$m.log" 2>/dev/null; then det=$((det + 1)); echo "  PASS $m: detectada ($(grep '^FAIL tb_xd_mod' "$O/$m.log" | sed 's/FAIL tb_xd_mod: //'))"
  else echo "  FAIL $m: el testbench pasa con el error puesto"; fallas=$((fallas + 1)); fi
done
echo
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, los modulos coinciden con el modelo y $det de $total mutaciones se detectan"
else echo "RESULTADO: FAIL ($fallas problemas)"; fi
} | tee "$MX/tb_modulos.txt"
grep -q "^RESULTADO: PASS" "$MX/tb_modulos.txt"
