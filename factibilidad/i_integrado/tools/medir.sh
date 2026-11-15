#!/usr/bin/env bash
# medir.sh: celdas, BRAM y frecuencia máxima en 10 semillas de cada variante
# de tools/variantes.txt (y de las del archivo que se pase en VARIANTES).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Usa tools/medir_variante.sh del repositorio (yosys synth_ice40 y
# nextpnr-ice40 --hx1k --package vq100 --freq 25, goboard.pcf), con etiquetas
# fact2_i_*: los logs quedan en build/variantes/fact2_i_ETIQUETA de la raíz.
# La línea de resumen de cada variante se guarda en build/medir/ETIQUETA.txt
# de esta carpeta, y tools/informe_recursos.py arma con todas ellas
# mediciones/recursos.txt.
#
# Uso: factibilidad/i_integrado/tools/medir.sh [FILTRO]   (o make recursos)
# FILTRO es una expresión regular sobre la etiqueta. Sin filtro mide todo.
# Variables: SEMILLAS (10), JOBS (5 procesos de nextpnr en paralelo),
# VARIANTES (archivo de variantes) y SOLO_INFORME=1 (no mide: vuelve a
# escribir el informe con lo que ya está medido).
set -uo pipefail
source "$(dirname "$0")/comun.sh"

FILTRO=${1:-.}
SEMILLAS=${SEMILLAS:-10}
export JOBS=${JOBS:-5}
VARIANTES=${VARIANTES:-$I/tools/variantes.txt}
O=$B/medir
mkdir -p "$O"

if [ "${SOLO_INFORME:-0}" != 1 ]; then
  programas
  armar_rtl "$O/rtl_barrel"     barrel
  armar_rtl "$O/rtl_barrel_dir" barrel directa
  armar_rtl "$O/rtl_seg"        segmentado
  # Prototipo del barrel, sin tocar
  rm -rf "${O:?}/rtl_proto"; mkdir -p "$O/rtl_proto/espino_core"
  ln -s "$RAIZ/rtl/pochoco_ram.v" "$RAIZ/rtl/pochoco_spi_slave.v" "$RAIZ/rtl/pochoco_periph.v" "$RAIZ/$A/rtl/pochoco_soc.v" "$O/rtl_proto/"
  ln -s "$RAIZ/rtl/espino_core/espino_decoder.v" "$RAIZ/rtl/espino_core/espino_alu.v" "$RAIZ/rtl/espino_core/espino_load_store_unit.v" \
        "$RAIZ/$A/rtl/espino_barrel_core.v" "$RAIZ/$A/rtl/espino_barrel_regfile.v" "$O/rtl_proto/espino_core/"

  while IFS='|' read -r etq fuentes defs params ref desc; do
    etq=$(echo "$etq" | xargs); fuentes=$(echo "$fuentes" | xargs); defs=$(echo "$defs" | xargs); params=$(echo "$params" | xargs)
    case "$etq" in ""|\#*|=*) continue ;; esac
    [[ "$etq" =~ $FILTRO ]] || continue
    case "$fuentes" in
      repo)       rtl=rtl;                 hex=sw/trade.hex ;;
      proto)      rtl=$O/rtl_proto;        hex=$B/sw/trade_h0.hex ;;
      barrel)     rtl=$O/rtl_barrel;       hex=$B/sw/trade_h0.hex ;;
      barrel_dir) rtl=$O/rtl_barrel_dir;   hex=$B/sw/trade_h0.hex ;;
      seg)        rtl=$O/rtl_seg;          hex=sw/trade.hex ;;
      *) echo "medir.sh: fuentes desconocidas '$fuentes' en $etq" >&2; continue ;;
    esac
    inicio=$(date +%s)
    RTL=$rtl HEX=$hex DEFS="$defs" PARAMS="$params" tools/medir_variante.sh "fact2_i_$etq" "$SEMILLAS" > "$O/$etq.tmp" 2> "$O/$etq.err"
    tail -1 "$O/$etq.tmp" > "$O/$etq.txt"; rm -f "$O/$etq.tmp"
    echo "$(cat "$O/$etq.txt")   [$(( $(date +%s) - inicio )) s]" >&2
  done < "$VARIANTES"
fi

$PYTHON $I/tools/informe_recursos.py "$O" build/variantes "$SEMILLAS" "$M" $I/tools/variantes.txt ${VARIANTES_EXTRA:-}
