#!/usr/bin/env bash
# mutaciones.sh: controles negativos de la verificación del core segmentado.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Una prueba que siempre pasa no prueba nada. Este script rompe el core
# segmentado a propósito, de una forma distinta cada vez, y exige que las
# pruebas lo noten. El método viene del tb/revision_a_mutaciones.sh de nuestro
# Proyecto 3. Las mutaciones están en el RTL bajo `ifdef y solo se activan
# desde la línea de comandos:
#
#   MUTA_FWD      el banco de registros no adelanta el dato que se escribe en
#                 el mismo flanco en que se lee (riesgo de datos).
#   MUTA_LOADUSE  la instrucción que sigue a una carga lee sus operandos antes
#                 de que la carga escriba (riesgo de carga seguida de uso).
#   MUTA_RDEN     el banco relee durante la espera de una carga y pierde los
#                 operandos de la carga.
#   MUTA_X0       el adelantamiento no excluye a x0.
#   MUTA_SQUASH   la instrucción que sigue a un salto tomado no se anula
#                 (riesgo de control).
#
# Para cada una corre las pruebas de riesgos (tools/riesgos.sh) y la ejecución
# en paralelo con programas aleatorios (tools/paralelo.sh). Termina bien solo
# si las pruebas pasan sin mutación y cada mutación es detectada por las
# pruebas de riesgos y por la ejecución en paralelo.
#
# Uso, desde la raíz del repositorio: tools/mutaciones.sh
set -uo pipefail

MUTACIONES=${MUTACIONES:-"MUTA_FWD MUTA_LOADUSE MUTA_RDEN MUTA_X0 MUTA_SQUASH"}
D=build/mutaciones
mkdir -p "$D"

echo "== Sin mutacion: todo debe pasar =="
if ! ETQ=muta_ref tools/riesgos.sh > "$D/ref_riesgos.log" 2>&1; then
  echo "FAIL mutaciones: las pruebas de riesgos fallan sin mutacion"; tail -5 "$D/ref_riesgos.log"; exit 1
fi
if ! ETQ=muta_ref PCW=32 tools/paralelo.sh 4 5000 > "$D/ref_paralelo.log" 2>&1; then
  echo "FAIL mutaciones: la ejecucion en paralelo falla sin mutacion"; tail -5 "$D/ref_paralelo.log"; exit 1
fi
echo "PASS sin mutacion: riesgos y ejecucion en paralelo pasan"

fallas=0
for m in $MUTACIONES; do
  echo "== $m =="
  det_r=0; det_p=0
  if ! MUTA=-D$m ETQ=$m tools/riesgos.sh > "$D/${m}_riesgos.log" 2>&1; then det_r=1; fi
  if ! MUTA=-D$m ETQ=$m PCW=32 tools/paralelo.sh 4 5000 > "$D/${m}_paralelo.log" 2>&1; then det_p=1; fi
  if [ $det_r = 1 ]; then
    echo "  detectada por las pruebas de riesgos: $(grep -c '^FAIL .*hazard' "$D/${m}_riesgos.log") comprobaciones fallan"
    for p in hazard_test hazard_review hazard_cycles; do
      n=$(grep -c "^FAIL $p" "$D/${m}_riesgos.log")
      if [ "$n" -gt 0 ]; then echo "    $p: $(grep -m1 "^FAIL $p" "$D/${m}_riesgos.log" | sed "s/^FAIL $p[ ,(]*//" | cut -c1-150)"; fi
    done
  else
    echo "  NO detectada por las pruebas de riesgos"
  fi
  if [ $det_p = 1 ]; then
    echo "  detectada por la ejecucion en paralelo: $(grep -c '^FAIL paralelo, semilla' "$D/${m}_paralelo.log") de 4 programas aleatorios difieren"
  else
    echo "  NO detectada por la ejecucion en paralelo"
  fi
  if [ $det_r = 0 ] || [ $det_p = 0 ]; then fallas=$((fallas + 1)); fi
done

if [ "$fallas" -ne 0 ]; then
  echo "FAIL mutaciones: $fallas mutaciones no fueron detectadas por alguna de las dos pruebas"; exit 1
fi
echo "PASS mutaciones: las $(echo $MUTACIONES | wc -w) mutaciones son detectadas por las pruebas de riesgos y por la ejecucion en paralelo"
