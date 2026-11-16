#!/usr/bin/env bash
# estres.sh: matriz de estrés del fondo en un chip (criterio 7 de la puerta de
# simulación). Los casos y lo que se exige están en tools/fondo/estres.py.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: HW=r1 tools/fondo/estres.sh   (o make fondo-estres HW=r1)
# Resultado en docs/mediciones/fondo/HW/estres.txt. Unos 3 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

SALIDA=${SALIDA:-$MF/estres.txt}
ensamblar_fondo || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1
rm -rf "$BF/estres"
{
cabecera "Matriz de estres del fondo en un chip" tools/fondo/estres.sh "make fondo-estres HW=$HW"
$PYTHON $TF/estres.py "$SIM" "$FONDO_HEX" "$TABLA_HEX" "$(simbolos)" "$BF/estres"
} | tee "$SALIDA"
cierre "$SALIDA"
