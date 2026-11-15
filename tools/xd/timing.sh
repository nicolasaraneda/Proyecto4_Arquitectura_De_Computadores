#!/usr/bin/env bash
# timing.sh: celdas, BRAM y frecuencia máxima del barrel con la extensión de
# la ISA, en 10 semillas de nextpnr (criterio 3 de la puerta de simulación).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Mide con tools/medir_variante.sh (nextpnr-ice40 --hx1k --package vq100
# --freq 25, goboard.pcf), todas con el mismo programa en la memoria:
#   xd_ref   el barrel sin la extensión (control: es el de make barrel-timing)
#   xd_M     el barrel con el subconjunto de máscara M (1 a 7; bit 0 emad,
#            bit 1 devk, bit 2 mulstep). xd_7 es el que lleva las tres.
# Todas las variantes con extensión tienen que cerrar a 25 MHz en todas las
# semillas: si alguna no cierra, el script termina con error.
#
# Uso: tools/xd/timing.sh [SEMILLAS]   (o make xd-timing)
# Variables de entorno:
#   MASCARAS  subconjuntos que se miden (por defecto "1 2 3 4 5 6 7")
#   JOBS      procesos de nextpnr en paralelo (por defecto 5)
#   SALIDA    archivo de resultado (por defecto docs/mediciones/xd/timing.txt)
set -uo pipefail
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-10}
MASCARAS=${MASCARAS:-1 2 3 4 5 6 7}
export JOBS=${JOBS:-5}
SALIDA=${SALIDA:-$MX/timing.txt}
programas
HB=$B/sw/trade_h0.hex
O=$BX/timing
mkdir -p "$O"
rm -f "$O/no_cierra"

{
  DEFS=-DESPINO_BARREL HEX=$HB tools/medir_variante.sh xd_ref "$SEMILLAS"
  for m in $MASCARAS; do
    linea=$(echo "$XD_SUBCONJUNTOS" | grep "^$m:")
    defs=$(echo "$linea" | cut -d: -f3 | tr ',' ' ')
    DEFS="-DESPINO_BARREL $defs" HEX=$HB EXIGIR=1 tools/medir_variante.sh "xd_$m" "$SEMILLAS" || touch "$O/no_cierra"
  done
} > "$O/lineas.txt"

{
echo "Barrel con la extension de la ISA en custom-0: celdas, BRAM y frecuencia maxima"
echo "Generado por tools/xd/timing.sh (make xd-timing). No editar a mano."
echo
versiones
echo
echo "nextpnr-ice40 --hx1k --package vq100 --freq 25, $SEMILLAS semillas. La FPGA tiene 1280 celdas y 16 BRAM."
echo "xd_ref es el barrel sin la extension. xd_M lleva el subconjunto de mascara M:"
echo "$XD_SUBCONJUNTOS" | sed -E 's/^([0-9]):([a-z_]+):(.*)$/  xd_\1  \2 (\3)/'
echo
cat "$O/lineas.txt"
echo
$PYTHON $TX/resumen_timing.py "$O/lineas.txt"
} | tee "$SALIDA"

if [ -e "$O/no_cierra" ]; then
  echo "FAIL: alguna variante con la extension no cierra a 25 MHz en las $SEMILLAS semillas"; exit 1
fi
echo "PASS timing: todas las variantes con la extension cierran a 25 MHz en las $SEMILLAS semillas"
