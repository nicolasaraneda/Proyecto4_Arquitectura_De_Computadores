#!/usr/bin/env bash
# estres.sh: matriz de estrés de R3 (criterio 7 de la puerta de simulación). Los
# casos y lo que se exige están en tools/c1/estres.py.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: [JOBS=12] tools/c1/estres.sh   (make c1-estres)
# Resultado en docs/mediciones/c1/estres.txt. Unos 5 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

SALIDA=${SALIDA:-$MC/estres.txt}
ensamblar_c1 || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1
rm -rf "$BC/estres"
{
cabecera "Matriz de estres de R3" tools/c1/estres.sh "make c1-estres"
$PYTHON $TC/estres.py "$SIM" "$BC/estres"
} | tee "$SALIDA"
cierre "$SALIDA"
