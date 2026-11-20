#!/usr/bin/env bash
# puerta_cotas.sh: puerta de simulación de R1 o R2 con la regla de cotas vigente
# (sw/fondo.s y la tabla de sw/fondo_tabla.hex), en el orden de docs/puertas.md.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre los mismos objetivos que la puerta de la banda 60 (docs/bitacora/regla_cotas_r1.md),
# salvo el timing y el criterio 5, que dependen solo del hardware:
#   referencia y tabla      make test-fondo, make check-tabla
#   1. oficial              make fondo-oficial
#   2. equivalencia         make fondo-equiv-ronda1 (serie Meta y la anterior a 0,1, 1 y
#                           10 ms, 15 familias crudas y normalizadas), make fondo-series
#                           (1050 series), y las series reales del 18/11 si hay
#                           $P4_DATOS (tools/reales.sh)
#   4. fases                make fondo-fases
#   6. degradación          make fondo-degradacion
#      controles negativos  make fondo-controles
#   7. estrés               make fondo-estres
#   3.2 del enunciado       make fondo-ticks
# El criterio 8 (bitstream por los pines) lo hace tools/fondo/molde_cotas.sh.
#
# Uso: HW=r1|r2 tools/fondo/puerta_cotas.sh   (unos 45 minutos por peldaño)
# Resultado en docs/mediciones/fondo/HW/puerta_banda40.txt (SALIDA para otro nombre).
set -uo pipefail
RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$RAIZ"
HW=${HW:-r1}
case $HW in r1|r2) ;; *) echo "HW debe ser r1 o r2"; exit 1 ;; esac
SALIDA=${SALIDA:-docs/mediciones/fondo/$HW/puerta_banda40.txt}
B=build/fondo/$HW/puerta
mkdir -p "$B"
f=0
paso() {
  local e=$1; shift
  echo "== $*"
  if "$@" > "$B/$e.log" 2>&1; then echo "PASS: $*"; else echo "FAIL: $*"; f=$((f + 1)); fi
  grep -E '^(PASS|FAIL|DETECTADO)|Ticks comparados|Peor caso|series' "$B/$e.log" | grep -v '^PASS: ' | cut -c1-200 | head -60
}
{
echo "Puerta de simulacion de $HW con la regla de cotas, tabla: $(python3 ref/fondo.py --tabla | awk '{printf "%s=%s ", $3, $4}')"
echo "Generado por tools/fondo/puerta_cotas.sh, commit $(git rev-parse --short HEAD). Hardware sin cambios: programa y tabla entran por icebram en el molde."
echo "sw/fondo.s sha256 $(sha256sum sw/fondo.s | cut -c1-16)..., sw/fondo_tabla.hex sha256 $(sha256sum sw/fondo_tabla.hex | cut -c1-16)..."
echo
echo "Referencia y tabla"
paso test_fondo make test-fondo
paso check_tabla make check-tabla
echo
echo "1. Testbench oficial sin modificar"
paso oficial make fondo-oficial HW=$HW
echo
echo "2. Equivalencia"
paso equiv make fondo-equiv-ronda1 HW=$HW
paso series make fondo-series HW=$HW
if [ -n "${P4_DATOS:-}" ]; then paso reales tools/reales.sh $HW
else echo "(sin P4_DATOS: las series reales del 18/11 no se corren)"; fi
echo
echo "3. Timing: hardware sin cambios (docs/puertas.md); icetime del .asc nuevo en tools/fondo/molde_cotas.sh."
echo
echo "4. Fases"
paso fases make fondo-fases HW=$HW
echo
echo "5. Core: hardware sin cambios y el binario de sw/fondo.s es el mismo (la mascara de la extension no cambia)."
echo
echo "6. Degradacion y controles negativos"
paso degradacion make fondo-degradacion HW=$HW
paso controles make fondo-controles HW=$HW
echo
echo "7. Estres"
paso estres make fondo-estres HW=$HW
echo
echo "Mediciones por tick (punto 3.2)"
paso ticks make fondo-ticks HW=$HW
echo
if [ "$f" -eq 0 ]; then echo "PASS: $HW paso los criterios 1, 2, 4, 6 y 7"; else echo "FAIL: $f pasos fallaron"; fi
} 2>&1 | tee "$SALIDA"
grep -q "^PASS: $HW paso" "$SALIDA"
