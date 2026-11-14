#!/usr/bin/env bash
# costo_integrado.sh: costo de cada instrucción nueva integrada en el core.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Para cada variante de tools/variantes.txt sintetiza el SoC completo con la
# copia del core segmentado (factibilidad/d_isa/core) y las definiciones XD_*
# de la variante, y corre nextpnr con 10 semillas. Usa el script del
# repositorio, tools/medir_variante.sh, con RTL apuntando a la copia y
# etiquetas fact_d_*: los logs quedan en build/variantes/fact_d_ETIQUETA de la
# raíz. Informa celdas lógicas, la diferencia contra la copia sin
# instrucciones nuevas, celdas libres, BRAM y la frecuencia máxima mínima,
# mediana y máxima, y cuántas semillas cierran a 25 MHz. Mide además el
# segmentado del repositorio sin tocar (rtl/), para ver cuánto se mueve el
# conteo por el solo hecho de usar la copia.
#
# Uso, desde factibilidad/d_isa:
#   tools/costo_integrado.sh [FILTRO] > mediciones/costo_integrado.txt
# FILTRO es una expresión regular sobre la etiqueta (por defecto, todas).
# Variables: SEMILLAS (10) y JOBS (5 procesos de nextpnr en paralelo).
set -euo pipefail
cd "$(dirname "$0")/.."
AQUI=factibilidad/d_isa
FILTRO=${1:-.}
SEMILLAS=${SEMILLAS:-10}
JOBS=${JOBS:-5}
VARIANTES=$PWD/tools/variantes.txt
cd ../..                                   # raíz del repositorio

EXTRA=$(echo $AQUI/rtl/xd_*.v)
medir() {   # medir ETIQUETA "definiciones" -> línea de resumen de medir_variante.sh
  RTL=$AQUI/core EXTRA="$EXTRA" DEFS="-DESPINO_SEGMENTADO $2" JOBS=$JOBS \
    tools/medir_variante.sh "fact_d_$1" "$SEMILLAS" 2>/dev/null | tail -1
}
campo() { echo "$1" | sed -E "s/.*$2 +([0-9.?]+).*/\1/"; }

echo "Costo de la extensión de la ISA integrada en el core segmentado"
echo "Generado por factibilidad/d_isa/tools/costo_integrado.sh (make costo-integrado). No editar a mano."
echo
echo "Herramientas: $(yosys -V | cut -d' ' -f1-2), $(nextpnr-ice40 --version 2>&1 | sed 's/.*(Version \(.*\))/nextpnr \1/')"
echo "Flujo: tools/medir_variante.sh, nextpnr-ice40 --hx1k --package vq100 --freq 25, goboard.pcf, semillas 1 a $SEMILLAS."
echo "SoC completo (core, memoria, esclavo SPI, periféricos y reset) con sw/trade.hex. La FPGA tiene 1280 celdas y 16 BRAM."
echo
REPO=$(DEFS=-DESPINO_SEGMENTADO JOBS=$JOBS tools/medir_variante.sh fact_d_seg_repo "$SEMILLAS" 2>/dev/null | tail -1)
REF=$(medir ref "")
LC_REPO=$(campo "$REPO" celdas); LC_REF=$(campo "$REF" celdas)
echo "Segmentado del repositorio (rtl/, sin tocar): $LC_REPO celdas, fmax mínima $(campo "$REPO" min), mediana $(campo "$REPO" mediana), máxima $(campo "$REPO" max) MHz"
echo "Copia sin instrucciones nuevas (referencia):  $LC_REF celdas, fmax mínima $(campo "$REF" min), mediana $(campo "$REF" mediana), máxima $(campo "$REF" max) MHz"
echo "Las dos son el mismo circuito: la diferencia entre ellas es ruido de la síntesis (decisión T6: unas 10 celdas)."
echo "La columna 'agrega' es la diferencia contra la copia sin instrucciones nuevas."
echo
printf "%-13s %6s %6s %6s %4s %5s  %7s %7s %7s %8s  %s\n" variante celdas agrega libres BRAM LUT4 "fmin" "fmed" "fmax" "cierran" "qué incluye"
while IFS='|' read -r etq defs desc; do
  etq=$(echo "$etq" | xargs); defs=$(echo "$defs" | xargs); desc=$(echo "$desc" | sed 's/^ *//')
  case "$etq" in
    ""|\#*) continue ;;
    =*) echo; echo "-- ${etq#= }${defs:+ | $defs}${desc:+ | $desc}"; continue ;;
  esac
  [[ "$etq" =~ $FILTRO ]] || continue
  if [ "$etq" = ref ]; then L=$REF; else L=$(medir "$etq" "$defs" || true); fi
  if ! echo "$L" | grep -q "celdas *[0-9]"; then
    printf "%-13s %s\n" "$etq" "ERROR: la síntesis o nextpnr no entregaron resultado (ver build/variantes/fact_d_$etq)"
    continue
  fi
  lc=$(campo "$L" celdas); cierran=$(echo "$L" | sed -E 's/.*cierran a 25 MHz ([0-9]+) de ([0-9]+).*/\1 de \2/')
  nota=""
  if [ "$lc" -gt 1280 ] 2>/dev/null; then nota="NO CABE. "; fi
  printf "%-13s %6s %+6d %6d %4s %5s  %7s %7s %7s %8s  %s%s\n" "$etq" "$lc" "$((lc - LC_REF))" "$((1280 - lc))" \
    "$(campo "$L" BRAM)" "$(campo "$L" LUT4)" "$(campo "$L" min)" "$(campo "$L" mediana)" "$(campo "$L" max)" "$cierran" "$nota" "$desc"
done < "$VARIANTES"
echo
echo "fmin, fmed y fmax: frecuencia máxima mínima, mediana y máxima entre las semillas, en MHz. Un 0 es una semilla"
echo "en que nextpnr no terminó: el diseño no cabe. 'cierran' cuenta las semillas que cumplen los 25 MHz."
