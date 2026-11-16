#!/usr/bin/env bash
# probar_vigilante.sh: testbench del módulo vigilante, para varios valores de N.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre tb/tb_vigilante.v (casos dirigidos y estímulo aleatorio contra un
# modelo de referencia) con N = 1, 2, 4, 7 y 15.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/e_warmboot/scripts/probar_vigilante.sh
# Resultado en mediciones/vigilante_tb.txt.
set -euo pipefail

E=factibilidad/e_warmboot
D=$E/build/vig
mkdir -p "$D" "$E/mediciones"

{
  echo "Testbench del vigilante (tb/tb_vigilante.v)"
  echo "Comando: factibilidad/e_warmboot/scripts/probar_vigilante.sh"
  echo
  for n in 1 2 4 7 15; do
    iverilog -g2012 -DN_VIG=$n -s tb_vigilante -o "$D/tb_n$n" $E/rtl/vigilante.v $E/tb/tb_vigilante.v
    vvp -n "$D/tb_n$n" | grep -v "finish called" | tee "$D/tb_n$n.log"
    echo
  done
  pass=$(cat "$D"/tb_n*.log | grep -c '^PASS' || true)
  fail=$(cat "$D"/tb_n*.log | grep -c '^FAIL' || true)
  ok=$(cat "$D"/tb_n*.log | grep -c '^  ok' || true)
  falla=$(cat "$D"/tb_n*.log | grep -c '^  FALLA' || true)
  echo "RESUMEN: $pass valores de N con PASS, $fail con FAIL; $ok comprobaciones correctas, $falla con falla"
} | tee $E/mediciones/vigilante_tb.txt
# Falla si alguna corrida terminó en FAIL o alguna comprobación en FALLA. Se
# miran solo los comienzos de línea: el resumen también contiene esas palabras.
! grep -q "^FAIL\|^  FALLA" $E/mediciones/vigilante_tb.txt
