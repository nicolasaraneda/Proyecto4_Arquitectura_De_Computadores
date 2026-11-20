#!/usr/bin/env bash
# puerta_r0_cotas.sh: puerta de simulación de R0 con la regla de cotas vigente
# (sw/trade.s, ref/trader.py Oficial), en el orden de docs/puertas.md.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Con banda 60 (17/11) esta puerta se armó a mano (docs/mediciones/r0_cotas_puerta.txt);
# desde la banda 40 (T140) la corre este script:
#   1. testbench oficial sin modificar (make tb)
#   2. equivalencia: make equiv; los 20 000 ticks de práctica a 0,1 ms con Icarus
#      (make equiv-r3) y a 10 ms con Verilator (make equiv-largo); la serie Meta por
#      el RTL a 0,1 ms (Icarus), 1 ms y 10 ms (Verilator); 3810 series en el gemelo a
#      los tres períodos (make equiv-gemelo); la verificación exhaustiva de la regla
#      (tools/exhaustivo/r0_cotas.py); y las series reales del 18/11 si hay
#      $P4_DATOS (tools/reales.sh r0)
#   3. timing: el hardware no cambia (se informa; lo comprueba icetime en
#      tools/fondo/molde_cotas.sh)
#   4. fases del sondeo (make fases)
#   5. core: el base, sin cambios
#   7. matriz de estrés (make estres)
#   8. el .asc del molde por los pines: tools/fondo/molde_cotas.sh (aparte, porque
#      construye R0, R1 y R2 juntos)
#
# Uso: tools/puerta_r0_cotas.sh   (unos 50 minutos)
# Resultado en docs/mediciones/r0_banda40_puerta.txt (SALIDA para otro nombre).
set -uo pipefail
RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$RAIZ"
SALIDA=${SALIDA:-docs/mediciones/r0_banda40_puerta.txt}
B=build/puerta_r0
mkdir -p "$B"
f=0
paso() {   # paso ETIQUETA comando...: corre, guarda el registro y muestra las líneas de resultado
  local e=$1; shift
  echo "== $*"
  if "$@" > "$B/$e.log" 2>&1; then echo "PASS: $*"; else echo "FAIL: $*"; f=$((f + 1)); fi
  grep -E '^(PASS|FAIL)|periodo .*series|Distintas|combinaciones|Testbenchs aprobados|Peor caso' "$B/$e.log" | grep -v '^PASS: ' | cut -c1-200
}
{
echo "Puerta de simulacion de R0 con la regla de cotas: $(python3 -c 'import sys; sys.path.insert(0,"ref"); import trader; o=trader.Oficial(); print(f"Cotas(\"{o.inicio}\", banda={o.banda})")')"
echo "Generado por tools/puerta_r0_cotas.sh, commit $(git rev-parse --short HEAD). Hardware sin cambios: el programa entra por icebram en el molde de R0."
echo "sw/trade.s sha256 $(sha256sum sw/trade.s | cut -c1-16)..., sw/trade.hex sha256 $(sha256sum sw/trade.hex | cut -c1-16)..."
echo
echo "1. Testbench oficial sin modificar (tb/practica.csv, 2000 ticks a 0,1 ms)"
paso tb make tb
echo
echo "2. Equivalencia"
paso equiv make -j4 equiv
paso equiv_r3 make equiv-r3
paso equiv_largo make equiv-largo
paso meta_100000 tools/equiv.sh meta_100000 100000 20000 data/practica_meta.csv
paso vmeta_1000000 env SIM=verilator tools/equiv.sh vmeta_1000000 1000000 20000 data/practica_meta.csv
paso vmeta_10000000 env SIM=verilator tools/equiv.sh vmeta_10000000 10000000 20000 data/practica_meta.csv
paso equiv_gemelo make equiv-gemelo
paso exhaustiva python3 tools/exhaustivo/r0_cotas.py
if [ -n "${P4_DATOS:-}" ]; then paso reales tools/reales.sh r0
else echo "(sin P4_DATOS: las series reales del 18/11 no se corren)"; fi
echo
echo "3. Timing: hardware sin cambios (10 de 10 semillas, minima 42,43 MHz; docs/puertas.md). icetime del .asc nuevo en tools/fondo/molde_cotas.sh."
echo
echo "4. Fases del sondeo"
paso fases make fases
echo
echo "5. Core base sin cambios."
echo
echo "7. Matriz de estres"
make estres > "$B/estres.log" 2>&1
grep -E '^(PASS|FAIL|pasa|no pasa)' "$B/estres.log" | cut -c1-200
# Los casos periodo_* exploran el período mínimo, fuera de lo que pide el criterio 7
# (con la regla de cotas R0 responde en 60 ciclos y a 11,5 us hay 50, igual que con banda 60)
otros=$(grep '^FAIL ' "$B/estres.log" | grep -v -E '^FAIL (periodo_[0-9]+ns|[0-9]+ casos fallidos)' | wc -l)
if [ "$otros" -eq 0 ] && grep -q '^PASS sclk_100k' "$B/estres.log"; then
  echo "PASS: matriz de estres (los FAIL de periodo_*ns son exploracion del periodo minimo, fuera del criterio 7)"
else echo "FAIL: matriz de estres, $otros casos del criterio 7 fallaron"; f=$((f + 1)); fi
echo
echo "8. Bitstream: tools/fondo/molde_cotas.sh (R0, R1 y R2 desde los moldes, por los pines)."
echo
if [ "$f" -eq 0 ]; then echo "PASS: R0 paso los criterios 1, 2, 4 y 7"; else echo "FAIL: $f pasos fallaron"; fi
} 2>&1 | tee "$SALIDA"
grep -q '^PASS: R0 paso' "$SALIDA"
