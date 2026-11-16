#!/usr/bin/env bash
# medir_boton.sh: costo de las variantes del vigilante que no mide
# medir_vigilante.sh.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Mide con tools/medir_variante.sh (yosys, nextpnr --hx1k --package vq100
# --freq 25) tres variantes de la copia del SoC, todas con el core base:
#
#   fact_e_base_vig_n1       Vigilante = 1, VigN = 1 (el vigilante más chico)
#   fact_e_base_vig_boton    Vigilante = 1, VigN = 4, VigBoton = 1, sw/trade.hex
#   fact_e_base_vig_cuelgue  lo mismo, con el programa de la prueba de relevo
#                            (sw/cuelgue.s, K = 500): es la imagen 0 de
#                            relevo_prueba_multi.bin
#
# Sirve para dos cosas: saber cuánto cuesta el disparo manual y explicar por
# qué la imagen de la prueba de relevo ocupa más celdas que la variante
# fact_e_base_vig de mediciones/vigilante_costo.txt.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/e_warmboot/scripts/medir_boton.sh [SEMILLAS]
# Deja el resultado en factibilidad/e_warmboot/mediciones/vigilante_boton.txt
# y los logs en build/variantes/fact_e_*/.
set -euo pipefail

SEMILLAS=${1:-10}
E=factibilidad/e_warmboot
OUT=$E/mediciones/vigilante_boton.txt
export JOBS=${JOBS:-5}
mkdir -p $E/build/vig $E/mediciones

RTLV=$($E/scripts/armar_rtl.sh)
python3 tools/pochoasm.py $E/sw/cuelgue.s -D K=500 -D DEC=0x7F -o $E/build/vig/cuelgue_k500.hex > /dev/null

{
  echo "Costo de las variantes del vigilante: N = 1 y disparo manual"
  echo "Comando: factibilidad/e_warmboot/scripts/medir_boton.sh $SEMILLAS"
  echo "Herramientas: $(yosys -V | cut -d' ' -f1-2), $(nextpnr-ice40 --version 2>&1 | head -1 | sed 's/.*(Version \(.*\))/nextpnr \1/')"
  echo "nextpnr --hx1k --package vq100 --freq 25, $SEMILLAS semillas"
  echo
  RTL=$RTLV PARAMS="Vigilante=1 VigN=1"                                     tools/medir_variante.sh fact_e_base_vig_n1      "$SEMILLAS"
  RTL=$RTLV PARAMS="Vigilante=1 VigBoton=1"                                 tools/medir_variante.sh fact_e_base_vig_boton   "$SEMILLAS"
  RTL=$RTLV PARAMS="Vigilante=1 VigBoton=1" HEX=$E/build/vig/cuelgue_k500.hex tools/medir_variante.sh fact_e_base_vig_cuelgue "$SEMILLAS"
  echo
  echo "Referencias de mediciones/vigilante_costo.txt (mismo flujo):"
  grep -E '^fact_e_base_(sin|vig) ' $E/mediciones/vigilante_costo.txt | sed 's/^/  /' || true
  echo
  echo "Frecuencia máxima por semilla (MHz), semillas 1 a $SEMILLAS:"
  for v in fact_e_base_vig_n1 fact_e_base_vig_boton fact_e_base_vig_cuelgue; do
    printf "  %-24s %s\n" "$v" "$(tr '\n' ' ' < build/variantes/$v/fmax.txt)"
  done
} | tee "$OUT"
