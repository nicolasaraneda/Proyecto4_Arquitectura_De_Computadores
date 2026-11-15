#!/usr/bin/env bash
# medir_ticks.sh: mediciones por tick del fondo de cuatro hilos.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   1. Serie de práctica completa (20 000 ticks) con el timing del testbench
#      oficial y el período de la ronda 3: respuesta (de byte_done a la
#      escritura de DECISION), hitos del protocolo, instrucciones por tick de
#      cada hilo y tick completo.
#   2. Lo mismo con el período de la ronda 2 (1 ms), 3000 ticks.
#   3. Barrido de la fase: el peor caso depende de en qué punto de sus lazos
#      de espera está cada hilo cuando llega el precio. El lazo de sondeo del
#      supervisor dura 12 ciclos y el de los gestores 8, así que el patrón se
#      repite cada 24 ciclos. Se corre el inicio de la serie de a un ciclo, 24
#      veces, con 1100 ticks cada vez (dos fronteras de ventana por corrida).
#
# En todas las corridas se exige además que las decisiones sean las de la
# referencia en C, o sea que la fase y el período no cambian ningún byte.
#
# Uso: factibilidad/b_fondo_hilos/tools/medir_ticks.sh   (o make ticks)
# Resultado en mediciones/ticks.txt. Demora unos 3 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

armar base || exit 1
compilar_fondo base || { echo "FAIL Verilator no compila tb_fondo"; exit 1; }
D=$B/sim/base
NFASES=24
TICKS_FASE=1100

# corrida ETIQUETA NTICKS PERIODO_NS INICIO_NS: corre y compara con la referencia
corrida() {
  local e=$1 k
  k=$(perdidos "$3")
  correr_fondo base "$e" tb/practica.csv "$2" "$3" "$4"
  referencia fondo_min tb/practica.csv "$2" "$k" "$D/$e.ref.csv" > "$D/$e.ref.log"
  if cmp -s "$D/$e.dec.csv" "$D/$e.ref.csv" && grep -q "Chequeos aprobados: 4/4" "$D/$e.log"; then
    echo "PASS $e: $2 ticks, periodo $3 ns, inicio $4 ns: 4/4 y decisiones identicas a la referencia" > "$D/$e.resultado.txt"
  else
    echo "FAIL $e: $2 ticks, periodo $3 ns, inicio $4 ns: $(grep 'Chequeos' "$D/$e.log"), $(cmp "$D/$e.dec.csv" "$D/$e.ref.csv" 2>&1 | head -1)" > "$D/$e.resultado.txt"
  fi
}
export -f corrida correr_fondo referencia perdidos
export B D ARNES PYTHON

{
  echo "ticks_r3 20000 100000 4000"
  echo "ticks_r2 3000 1000000 4000"
  for f in $(seq 0 $((NFASES - 1))); do echo "ticks_fase$f $TICKS_FASE 100000 $((4000 + 40 * f))"; done
} | xargs -P "$JOBS" -L 1 bash -c 'corrida "$@"' _

{
echo "Mediciones por tick del fondo de cuatro hilos (sw/fondo.s) en el Espino barrel"
echo "Generado por factibilidad/b_fondo_hilos/tools/medir_ticks.sh (make ticks). No editar a mano."
echo
versiones
echo
echo "=== A. Serie de practica completa, periodo de la ronda 3 (0,1 ms) ==="
echo
cat "$D/ticks_r3.resultado.txt"
$PYTHON $F/tools/resumen_ticks.py completo "$D/ticks_r3.ticks.csv" 100000
echo
echo "=== B. Periodo de la ronda 2 (1 ms), 3000 ticks ==="
echo
cat "$D/ticks_r2.resultado.txt"
$PYTHON $F/tools/resumen_ticks.py completo "$D/ticks_r2.ticks.csv" 1000000
echo
echo "=== C. Barrido de la fase: $NFASES corridas de $TICKS_FASE ticks, el inicio se corre un ciclo cada vez ==="
echo
for f in $(seq 0 $((NFASES - 1))); do cat "$D/ticks_fase$f.resultado.txt"; done | grep -c "^PASS" | sed "s/$/ de $NFASES fases con 4\/4 y decisiones identicas a la referencia/; s/^/  /"
for f in $(seq 0 $((NFASES - 1))); do grep "^FAIL" "$D/ticks_fase$f.resultado.txt"; done
$PYTHON $F/tools/resumen_ticks.py fases $(for f in $(seq 0 $((NFASES - 1))); do echo "$D/ticks_fase$f.ticks.csv"; done)
} | tee "$M/ticks.txt"

! grep -q "^FAIL" "$M/ticks.txt"
