#!/usr/bin/env bash
# medir_variante.sh: recursos y frecuencia máxima de una variante del SoC.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Sintetiza pochoco_soc con las definiciones que se le pasen, corre nextpnr
# con varias semillas (--hx1k --package vq100 --freq 25) e informa celdas
# lógicas, BRAM y la frecuencia máxima mínima, mediana y máxima. Cuenta
# cuántas semillas cierran a 25 MHz.
#
# Uso, desde la raíz del repositorio:
#   tools/medir_variante.sh ETIQUETA [SEMILLAS]
# Variables de entorno:
#   DEFS    definiciones para read_verilog, por ejemplo "-DESPINO_SEGMENTADO"
#   PARAMS  parámetros de pochoco_soc, por ejemplo "PcW=11 Pipeline=1"
#   EXTRA   fuentes adicionales (la ROM combinacional de la variante 2)
#   HEX     programa (por defecto sw/trade.hex)
#   RTL     carpeta con el RTL (por defecto rtl)
#   JOBS    procesos de nextpnr en paralelo (por defecto 10)
# Ejemplos:
#   tools/medir_variante.sh base 10
#   DEFS=-DESPINO_SEGMENTADO tools/medir_variante.sh segmentado 10
#
# Deja los logs en build/variantes/ETIQUETA/ y una línea de resumen por la
# salida estándar. Termina con error si alguna semilla no cierra a 25 MHz y
# se pidió EXIGIR=1.
set -euo pipefail

ETIQUETA=$1
SEMILLAS=${2:-10}
DEFS=${DEFS:-}
PARAMS=${PARAMS:-}
EXTRA=${EXTRA:-}
HEX=${HEX:-sw/trade.hex}
JOBS=${JOBS:-10}
EXIGIR=${EXIGIR:-0}
RTL=${RTL:-rtl}
SRC="$(echo $RTL/*.v $RTL/espino_core/*.v) $EXTRA"

D=build/variantes/$ETIQUETA
mkdir -p "$D"

CHP="chparam -set MemFile \"$HEX\" pochoco_soc;"
for p in $PARAMS; do CHP="$CHP chparam -set ${p%%=*} ${p##*=} pochoco_soc;"; done

yosys -q -l "$D/yosys.log" \
  -p "read_verilog $DEFS $SRC; $CHP synth_ice40 -top pochoco_soc -json $D/soc.json"

pnr() {   # pnr SEMILLA
  nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed "$1" --json "$D/soc.json" \
    --pcf goboard.pcf --asc "$D/soc.s$1.asc" -l "$D/soc.s$1.log" -q 2>/dev/null || true
}
export -f pnr; export D
seq 1 "$SEMILLAS" | xargs -P "$JOBS" -I{} bash -c "pnr {}"

fmax() { grep "Max frequency for clock" "$1" | tail -1 | sed -E 's/.*: ([0-9.]+) MHz.*/\1/'; }
campo() { grep "$2:" "$1" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1/'; }

: > "$D/fmax.txt"
cierran=0
for s in $(seq 1 "$SEMILLAS"); do
  f=$(fmax "$D/soc.s$s.log" || true)
  if [ -z "$f" ]; then f=0; fi
  echo "$f" >> "$D/fmax.txt"
  if grep "Max frequency for clock" "$D/soc.s$s.log" | tail -1 | grep -q "PASS"; then cierran=$((cierran + 1)); fi
done
sort -n "$D/fmax.txt" > "$D/fmax_orden.txt"
MIN=$(head -1 "$D/fmax_orden.txt")
MAX=$(tail -1 "$D/fmax_orden.txt")
MED=$(awk '{a[NR]=$1} END {printf "%.2f", (NR%2)? a[(NR+1)/2] : (a[NR/2]+a[NR/2+1])/2}' "$D/fmax_orden.txt")
LC=$(campo "$D/soc.s1.log" ICESTORM_LC || echo "?")
RAM=$(campo "$D/soc.s1.log" ICESTORM_RAM || echo "?")
LUT=$(grep -E '^ +[0-9]+ +SB_LUT4' "$D/yosys.log" | tail -1 | awk '{print $1}')

printf "%-22s celdas %4s de 1280, BRAM %2s de 16, LUT4 %4s, fmax min %6s mediana %6s max %6s MHz, cierran a 25 MHz %s de %s\n" \
  "$ETIQUETA" "$LC" "$RAM" "$LUT" "$MIN" "$MED" "$MAX" "$cierran" "$SEMILLAS"

if [ "$EXIGIR" = 1 ] && [ "$cierran" != "$SEMILLAS" ]; then
  echo "FAIL $ETIQUETA: no todas las semillas cierran a 25 MHz"; exit 1
fi
