#!/usr/bin/env bash
# ticks.sh: mediciones por tick del fondo en un chip (punto 3.2 del enunciado):
# IC, ciclos, CPI y tiempo, promedio y peor caso, por hilo y agregado.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Serie de práctica completa con el timing del testbench oficial, a los
# períodos de la ronda 3 (20 000 ticks) y de la ronda 2 (3000 ticks), medida
# con tb/fondo/tb_fondo.sv y Verilator. También deja el tamaño del programa
# por bloque.
#
# Uso: tools/fondo/ticks.sh   (o make fondo-ticks)
# Resultado en docs/mediciones/fondo/HW/ticks.txt (HW es r1 o r2) y tamano.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BF/ticks
mkdir -p "$O"
ensamblar_fondo || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1

{
cabecera "Tamano de sw/fondo.s por bloque, en palabras de 32 bits" tools/fondo/ticks.sh "make fondo-ticks"
$PYTHON $TF/simbolos.py sw/fondo.s --tamano
} | tee "$MF/tamano.txt"
echo

caso "$O/ronda3" sw/fondo.s tb/practica.csv 20000 100000 4000 --medir &
caso "$O/ronda2" sw/fondo.s tb/practica.csv 3000 1000000 4000 --medir &
wait

{
cabecera "Mediciones por tick del fondo en un chip" tools/fondo/ticks.sh "make fondo-ticks"
echo "=== Ronda 3: periodo de 0,1 ms, 20 000 ticks de la serie de practica ==="
cat "$O/ronda3/resultado.txt"
echo
echo "=== Ronda 2: periodo de 1 ms, 3000 ticks de la serie de practica ==="
cat "$O/ronda2/resultado.txt"
} | tee "$MF/ticks.txt"
cierre "$MF/ticks.txt"
