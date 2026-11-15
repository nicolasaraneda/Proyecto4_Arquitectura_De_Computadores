#!/usr/bin/env bash
# verif.sh: el barrel con la extensión de la ISA contra el Espino base más la
# especificación de la extensión, instrucción por instrucción.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Es la campaña de tools/barrel/verif.sh (los mismos grupos, el mismo
# testbench) con el barrel compilado con la extensión y programas que la usan.
# Qué cambia, en una línea: cuando el Espino base de referencia completa una
# palabra que la especificación reconoce, el testbench calcula el resultado con
# la fórmula de la especificación y lo escribe en el banco de registros de la
# referencia (encabezado de tb/barrel/tb_verif.sv).
#
# Uso: tools/xd/verif.sh   (o make xd-verif)
# Variables de entorno: las de tools/barrel/verif.sh (CAMPANA, GRUPOS, PUERTA,
# ESCALA, JOBS), más
#   XD      máscara del subconjunto (por defecto 7: emad, devk y mulstep)
#   SALIDA  por defecto docs/mediciones/xd/verificacion.txt
set -uo pipefail
source "$(dirname "$0")/comun.sh"
export XD=${XD:-7}
export DIR_VERIF=${DIR_VERIF:-$BX/verif_$XD}
export SALIDA=${SALIDA:-$MX/verificacion.txt}
exec $T/verif.sh
