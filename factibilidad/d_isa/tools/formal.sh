#!/usr/bin/env bash
# formal.sh: corre las pruebas formales de formal/xd.sby y resume el resultado.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso, desde factibilidad/d_isa:   tools/formal.sh > mediciones/formal.txt
# Variable: TIEMPO, segundos que se le dan a cada tarea (por defecto 600).
# Las carpetas de trabajo de sby quedan en build/formal/.
set -uo pipefail
cd "$(dirname "$0")/.."
TIEMPO=${TIEMPO:-600}
mkdir -p build/formal

declare -A QUE=(
  [ema_k5]="xd_ema, k = 5: rd = rs2 + ((rs1 - rs2) >>> 5) para todo rs1 y rs2"
  [ema_k4a7]="xd_ema, k de 4 a 7, contra la misma fórmula"
  [ema_k0a7]="xd_ema, k de 0 a 7"
  [ema_todos]="xd_ema, k de 0 a 31"
  [caminos_k5]="ema autónoma = ema con la resta de la ALU = sub y emad; devk, mulstep y pbcast8 por el sumador de espino_alu (k = 5)"
  [caminos_todos]="lo mismo con k de 0 a 31"
  [alu_base]="xd_alu con lane_op = 0 entrega lo mismo que espino_alu (resultado y comparación)"
  [alu_carriles]="padd8, psub8, pcmpltu8, paddus8 y psubus8 de xd_alu contra la especificación por carril"
  [simd]="las diez operaciones de xd_simd8 contra la especificación por carril"
  [mul8]="8 pasos de mulstep = producto, para todo multiplicador de 8 bits y multiplicando de 12 bits"
  [div8]="8 pasos de divstep = cociente y resto, para todo N < 256 D con D de 8 bits (el precio)"
  [divpaso]="un paso de divstep con D de 24 bits: 2 R + bit = q D + R nuevo, con R nuevo < D"
  [mut_ema]="control negativo: xd_ema con desplazamiento lógico"
  [mut_caminos]="control negativo: xd_opa con desplazamiento lógico"
  [mut_alu]="control negativo: xd_alu sin cortar el acarreo entre dos carriles"
  [mut_simd]="control negativo: xd_simd8 con acarreo entre carriles"
  [mut_mul8]="control negativo: mulstep mira el bit 30"
  [mut_div8]="control negativo: divstep compara con mayor estricto"
  [mut_divpaso]="control negativo: lo mismo, en el lema de un paso"
)
ORDEN="ema_k5 ema_k4a7 ema_k0a7 ema_todos caminos_k5 caminos_todos alu_base alu_carriles simd mul8 div8 divpaso mut_ema mut_caminos mut_alu mut_simd mut_mul8 mut_div8 mut_divpaso"

echo "Pruebas formales de la extensión de la ISA"
echo "Generado por factibilidad/d_isa/tools/formal.sh (make formal). No editar a mano."
echo
echo "SymbiYosys ($(sby --version 2>&1 | head -1)), modo bmc de un paso con boolector: son circuitos combinacionales,"
echo "así que un paso cubre todas las entradas. Propiedades en formal/xd_formal.sv. Tiempo máximo por tarea: $TIEMPO s."
echo
printf "%-14s %-22s %8s  %s\n" tarea resultado segundos "qué prueba"
FALLAS=0; SIN_TERMINAR=0
for t in $ORDEN; do
  ini=$(date +%s)
  timeout "$TIEMPO" sby -f --prefix build/formal/xd formal/xd.sby "$t" > "build/formal/$t.log" 2>&1
  rc=$?
  seg=$(( $(date +%s) - ini ))
  if [ $rc = 124 ]; then
    res="SIN TERMINAR"; SIN_TERMINAR=$((SIN_TERMINAR + 1))
  elif [[ "$t" == mut_* ]] && grep -q "DONE (FAIL, rc=0)" "build/formal/$t.log"; then
    res="PASS (falla detectada)"
  elif [[ "$t" != mut_* ]] && grep -q "DONE (PASS, rc=0)" "build/formal/$t.log"; then
    res="PASS"
  else
    res="FAIL"; FALLAS=$((FALLAS + 1))
  fi
  printf "%-14s %-22s %8s  %s\n" "$t" "$res" "$seg" "${QUE[$t]}"
done
echo
echo "En las tareas mut_* la propiedad debe fallar: PASS significa que sby encontró el contraejemplo esperado."
echo "No quedaron probados de punta a punta el producto con multiplicando de 16 o 24 bits ni el cociente con divisor"
echo "de 24 bits (tareas mul8_16, mul8_24 y div8_24 de formal/xd.sby): ni boolector ni yices terminaron en 200 a 300 s."
echo "Los cubren la propiedad de un paso (mulstep en caminos_*, divstep en divpaso) y la simulación de tb_xd_mulstep y"
echo "tb_xd_divstep (8 x 8 exhaustivo y 24 bits al azar)."
echo "Tareas con error: $FALLAS. Tareas que no terminaron en el tiempo dado: $SIN_TERMINAR."
[ "$FALLAS" = 0 ]
