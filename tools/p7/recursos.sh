#!/usr/bin/env bash
# recursos.sh: celdas, LUT4, BRAM y frecuencia máxima de cada variante de la
# tabla de co-diseño (punto 3.3 del enunciado), medidas en la misma corrida.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Cada variante es el SoC completo con su programa dentro (la síntesis lleva
# el .hex), por tools/medir_variante.sh: yosys synth_ice40 y nextpnr-ice40
# --hx1k --package vq100 --freq 25 con las semillas 1 a 10.
#
# Deja docs/mediciones/p7/recursos.txt con una línea por variante y la
# frecuencia de cada semilla. El encabezado lleva la huella de las fuentes
# (sha256 del RTL, de los programas y de las definiciones): si no cambió, el
# script no vuelve a correr nextpnr (FORZAR=1 lo obliga).
#
# Uso: tools/p7/recursos.sh [SEMILLAS]   (o make p7-recursos)
# Variables: JOBS (procesos de nextpnr por variante, por defecto 4).
set -euo pipefail
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-10}
export JOBS=${JOBS:-4}
SAL=$M/recursos.txt
programas

huella() {
  { for v in "${VARIANTES[@]}"; do echo "$v"; done
    cat rtl/*.v rtl/espino_core/*.v sw/fondo_tabla.hex "$B"/sw/*.hex goboard.pcf tools/medir_variante.sh
    echo "$SEMILLAS"; } | sha256sum | cut -c1-16
}
H=$(huella)
if [ "${FORZAR:-0}" != 1 ] && [ -f "$SAL" ] && grep -q "^Huella de las fuentes: $H" "$SAL"; then
  echo "$SAL ya corresponde a las fuentes actuales (huella $H): no se repite"
  exit 0
fi

for v in "${VARIANTES[@]}"; do
  IFS='|' read -r etq defs hex <<< "$v"
  ( DEFS="$defs" HEX="$hex" tools/medir_variante.sh "p7_$etq" "$SEMILLAS" > "$B/recursos_$etq.txt" 2>&1 || true ) &
done
wait

{
  echo "Recursos y frecuencia maxima de las variantes de co-diseno"
  echo "Generado por tools/p7/recursos.sh (make p7-recursos). No editar a mano."
  echo
  versiones
  echo "Huella de las fuentes: $H"
  echo
  echo "Flujo: tools/medir_variante.sh, yosys synth_ice40 y nextpnr-ice40 --hx1k --package vq100 --freq 25,"
  echo "goboard.pcf, semillas 1 a $SEMILLAS. SoC completo con el programa de cada variante dentro."
  echo
  for v in "${VARIANTES[@]}"; do
    IFS='|' read -r etq defs hex <<< "$v"
    printf "variante %-10s definiciones [%s] programa %s\n" "$etq" "$defs" "$hex"
  done
  echo
  for v in "${VARIANTES[@]}"; do
    IFS='|' read -r etq defs hex <<< "$v"
    grep -E "^p7_$etq " "$B/recursos_$etq.txt" || echo "p7_$etq FALLO: ver $B/recursos_$etq.txt"
  done
  echo
  echo "Frecuencia maxima por semilla (MHz), semillas 1 a $SEMILLAS:"
  for v in "${VARIANTES[@]}"; do
    IFS='|' read -r etq defs hex <<< "$v"
    printf "  %-10s %s\n" "$etq" "$(tr '\n' ' ' < build/variantes/p7_$etq/fmax.txt)"
  done
} > "$SAL"
cat "$SAL"
