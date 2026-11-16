#!/usr/bin/env bash
# medir_vigilante.sh: costo del vigilante integrado en el SoC.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Mide con tools/medir_variante.sh (yosys, nextpnr --hx1k --package vq100
# --freq 25, 10 semillas) seis variantes:
#
#   fact_e_repo_base   rtl/ del repositorio, core base               (referencia)
#   fact_e_base_sin    copia de este estudio, Vigilante = 0          (control)
#   fact_e_base_vig    copia de este estudio, Vigilante = 1
#   fact_e_repo_seg    rtl/ del repositorio, core segmentado         (referencia)
#   fact_e_seg_sin     copia, core segmentado, Vigilante = 0         (control)
#   fact_e_seg_vig     copia, core segmentado, Vigilante = 1
#
# El control debería dar lo mismo que la referencia: con Vigilante = 0 la
# copia no agrega nada. En la práctica difieren en unas pocas celdas, por el
# ruido del conteo que describe la decisión T6 de docs/decisiones.md. La
# diferencia entre "vig" y "sin" es el costo del vigilante con la primitiva
# SB_WARMBOOT. Al final se sintetiza el módulo solo, para contar sus celdas
# sin ese ruido.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/e_warmboot/scripts/medir_vigilante.sh [SEMILLAS]
# Deja el resultado en factibilidad/e_warmboot/mediciones/vigilante_costo.txt
# y los logs en build/variantes/fact_e_*/.
set -euo pipefail

SEMILLAS=${1:-10}
E=factibilidad/e_warmboot
OUT=$E/mediciones/vigilante_costo.txt
export JOBS=${JOBS:-5}

RTLV=$($E/scripts/armar_rtl.sh)

{
  echo "Costo del vigilante integrado en el SoC"
  echo "Comando: factibilidad/e_warmboot/scripts/medir_vigilante.sh $SEMILLAS"
  echo "Herramientas: $(yosys -V | cut -d' ' -f1-2), $(nextpnr-ice40 --version 2>&1 | head -1 | sed 's/.*(Version \(.*\))/nextpnr \1/')"
  echo "nextpnr --hx1k --package vq100 --freq 25, $SEMILLAS semillas, programa sw/trade.hex"
  echo
  RTL=rtl                                                      tools/medir_variante.sh fact_e_repo_base "$SEMILLAS"
  RTL=$RTLV PARAMS="Vigilante=0"                               tools/medir_variante.sh fact_e_base_sin  "$SEMILLAS"
  RTL=$RTLV PARAMS="Vigilante=1"                               tools/medir_variante.sh fact_e_base_vig  "$SEMILLAS"
  RTL=rtl   DEFS=-DESPINO_SEGMENTADO                           tools/medir_variante.sh fact_e_repo_seg  "$SEMILLAS"
  RTL=$RTLV DEFS=-DESPINO_SEGMENTADO PARAMS="Vigilante=0"      tools/medir_variante.sh fact_e_seg_sin   "$SEMILLAS"
  RTL=$RTLV DEFS=-DESPINO_SEGMENTADO PARAMS="Vigilante=1"      tools/medir_variante.sh fact_e_seg_vig   "$SEMILLAS"
  echo
  echo "Primitiva SB_WARMBOOT ubicada por nextpnr (semilla 1):"
  for v in fact_e_base_vig fact_e_seg_vig; do
    printf "  %-18s %s\n" "$v" "$(grep 'SB_WARMBOOT:' build/variantes/$v/soc.s1.log | head -1 | sed 's/Info: *//' | tr -s ' \t' ' ')"
  done
  echo
  echo "Módulo vigilante sintetizado solo (yosys synth_ice40, sin place and route):"
  mkdir -p $E/build/vig
  for n in 1 4 15; do
    yosys -q -p "read_verilog $E/rtl/vigilante.v; chparam -set N $n vigilante; synth_ice40 -top vigilante; tee -o $E/build/vig/stat_n$n.txt stat" > /dev/null 2>&1
    printf "  N = %-3s %s\n" "$n" "$(grep -E 'SB_LUT4|SB_DFF|SB_CARRY' $E/build/vig/stat_n$n.txt | tr -s ' ' | sed 's/^ //' | paste -sd, | sed 's/,/, /g')"
  done
  echo
  echo "Frecuencia máxima por semilla (MHz), semillas 1 a $SEMILLAS:"
  for v in fact_e_repo_base fact_e_base_sin fact_e_base_vig fact_e_repo_seg fact_e_seg_sin fact_e_seg_vig; do
    printf "  %-18s %s\n" "$v" "$(tr '\n' ' ' < build/variantes/$v/fmax.txt)"
  done
} | tee "$OUT"
