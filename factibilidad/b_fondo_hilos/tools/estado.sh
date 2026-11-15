#!/usr/bin/env bash
# estado.sh: estado interno del fondo, tick a tick, contra la traza del módulo en C.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Los bytes de DECISION de fondo_min solo toman los valores 7F y BF, así que
# la equivalencia byte a byte deja sin mirar casi todo lo que el programa
# calcula. Aquí se compara además, al cerrar cada tick, lo que quedó en la
# memoria del SoC: espejo de la caja y de las acciones, posición y puntaje en
# papel de cada gestor y los tres pesos (13 campos por tick, con el precio y
# el byte de DECISION). La traza de referencia la escribe fondo.c con
# FONDO_TRAZA. El testbench es tb/tb_fondo.sv, con Verilator.
#
# Casos: la serie de práctica completa a 0,1 ms, 3000 ticks de la práctica a
# 1 ms y tres series sintéticas de 20 000 ticks a 0,1 ms.
#
# Uso: factibilidad/b_fondo_hilos/tools/estado.sh   (o make estado)
# Resultado en mediciones/estado.txt. Demora unos 2 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

armar base || exit 1
compilar_fondo base || { echo "FAIL Verilator no compila tb_fondo"; exit 1; }
D=$B/sim/base

# caso ETIQUETA SERIE NTICKS PERIODO_NS
caso() {
  local e=estado_$1 k
  k=$(perdidos "$4")
  correr_fondo base "$e" "$2" "$3" "$4" 4000
  referencia fondo_min "$2" "$3" "$k" "$D/$e.ref.csv" "$D/$e.traza.csv" > "$D/$e.ref.log"
  {
    echo "--- $1: $2, $3 ticks, periodo $4 ns, $k precios sin ver por el reset ---"
    grep -E "Peor caso|Chequeos aprobados|Ordenes" "$D/$e.log" | sed 's/  */ /g; s/^/  /'
    if cmp -s "$D/$e.dec.csv" "$D/$e.ref.csv"; then echo "PASS $1: decisiones.csv identico al de la referencia ($(($(wc -l < "$D/$e.dec.csv") - 1)) filas)"
    else echo "FAIL $1: decisiones distintas: $(diff "$D/$e.dec.csv" "$D/$e.ref.csv" | sed -n 2,4p | tr '\n' ' ')"; fi
    $PYTHON $F/tools/comparar_estado.py "$D/$e.ticks.csv" "$D/$e.traza.csv" | sed "s/^PASS /PASS $1: /; s/^FAIL /FAIL $1: /"
    echo
  } > "$D/$e.resultado.txt"
}
export -f caso correr_fondo referencia perdidos
export B D F ARNES PYTHON

S1=$(serie_sintetica modelo 1 20000)
S2=$(serie_sintetica tendencia 1 20000)
S3=$(serie_sintetica volatil 1 20000)
printf '%s\n' "practica_0p1ms tb/practica.csv 20000 100000" "practica_1ms tb/practica.csv 3000 1000000" \
  "modelo $S1 20000 100000" "tendencia $S2 20000 100000" "volatil $S3 20000 100000" \
  | xargs -P "$JOBS" -L 1 bash -c 'caso "$@"' _

{
echo "Estado interno del fondo en el barrel contra la traza del modulo en C, tick a tick"
echo "Generado por factibilidad/b_fondo_hilos/tools/estado.sh (make estado). No editar a mano."
echo
versiones
echo
for e in practica_0p1ms practica_1ms modelo tendencia volatil; do cat "$D/estado_$e.resultado.txt"; done
echo "Filas comparadas en total: $(cat "$D"/estado_*.resultado.txt | grep -o 'PASS [a-z_0-9]*: [0-9]* filas por' | awk '{s += $3} END {print s}') por 13 campos."
} | tee "$M/estado.txt"

! grep -q "^FAIL" "$M/estado.txt"
