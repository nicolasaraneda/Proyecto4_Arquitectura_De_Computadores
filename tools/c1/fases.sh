#!/usr/bin/env bash
# fases.sh: peor caso de la respuesta de R3 barriendo la fase de llegada del precio
# (criterio 4 de la puerta de simulación).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# La respuesta depende de en qué punto de su lazo de sondeo está el hilo 0 cuando
# llega el precio (el lazo dura 12 ciclos y la rotación de hilos 4) y de en qué punto
# de sus lazos de espera están los hilos 1 a 3 (8 ciclos cada uno). Se corre el
# inicio de la serie de a un ciclo:
#
#   1. 48 fases con el programa sano, 2600 ticks cada una de una ventana real que
#      entra a media posición, pasa por el motor y llega al candado.
#   2. Las 24 primeras fases corridas 13 ns, para que el precio no llegue alineado
#      con el reloj.
#   3. Un período de 2501 ciclos, que recorre todas las fases dentro de una misma
#      corrida, con la serie Meta completa y con una ventana real completa.
#   4. 24 fases con el hilo 3 colgado: es el camino más largo del hilo 0 (espera el
#      plazo entero y decide solo). Con el plazo vencido y en modo seguro.
#
# En todas se exige lo de siempre: bytes, estado y protocolo iguales a la
# referencia. El límite es la mitad del presupuesto de la ronda 3: 1131 ciclos.
#
# Uso: [CORTA=1] [JOBS=12] tools/c1/fases.sh   (make c1-fases)
# Resultado en docs/mediciones/c1/fases.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BC/fases
NT=2600
SALIDA=${SALIDA:-$MC/fases.txt}
F1=47; F2=23; LARGO=20000
[ "${CORTA:-0}" = 1 ] && { F1=11; F2=3; LARGO=3000; }
rm -rf "$O"; mkdir -p "$O"
ensamblar_c1 || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1
# La ventana: la serie hecha a mano de la validación del gemelo (apuesta en la fase A
# y candado), seguida de una ventana de la serie Meta que pasa por el motor
$PYTHON - "$O/ventana.csv" $NT <<'PY'
import sys
sys.path[:0] = ["tools/c1", "ref", "ref/cotas"]
import cosim, comun, market, series
ruta, n = sys.argv[1], int(sys.argv[2])
series.escribir_csv(ruta, cosim.serie_fase_a(n))
PY
VEN=$O/ventana.csv
MOT=$(meta_ventana 250 $NT)
K=700
$PYTHON $TC/variante.py cuelga:3:$K -o "$O/colgado.s"
FALTAS=$($PYTHON $TC/variante.py cuelga:3:$K --faltas $NT)
{
  for f in $(seq 0 $F1); do
    echo "caso $O/sano_$f --serie $VEN --nticks $NT --inicio-ns $((4000 + 40 * f))"
    echo "caso $O/motor_$f --serie $MOT --nticks $NT --inicio-ns $((4000 + 40 * f))"
  done
  for f in $(seq 0 $F2); do echo "caso $O/corrido_$f --serie $VEN --nticks $NT --inicio-ns $((4013 + 40 * f))"; done
  echo "caso $O/periodo_2501_meta --serie data/practica_meta.csv --nticks $LARGO --periodo-ns 100040"
  echo "caso $O/periodo_2501_mano --serie $VEN --nticks $NT --periodo-ns 100040"
  for f in $(seq 0 $F2); do
    echo "caso $O/colgado_$f --asm $O/colgado.s --serie $VEN --nticks $NT --inicio-ns $((4000 + 40 * f)) $FALTAS"
  done
} | en_paralelo

# grupo NOMBRE PATRON: resumen de un grupo de corridas
grupo() {
  local n=0 p=0 lo=999999 hi=0 c
  for r in $O/$2/resultado.txt; do
    n=$((n + 1))
    grep -q "^PASS" "$r" && p=$((p + 1))
    c=$(sed -n 's/.*peor caso \([0-9]*\) de.*/\1/p' "$r")
    [ -n "$c" ] && { [ "$c" -gt "$hi" ] && hi=$c; [ "$c" -lt "$lo" ] && lo=$c; }
  done
  local e=PASS; [ "$p" = "$n" ] || e=FAIL
  echo "$e $1: $p de $n corridas iguales a la referencia, peor caso por corrida entre $lo y $hi ciclos (limite $LIMITE)"
  [ "$hi" -gt "$PEOR" ] && PEOR=$hi
  return 0
}

{
cabecera "Peor caso de la respuesta de R3 barriendo la fase de llegada del precio" tools/c1/fases.sh "make c1-fases"
PEOR=0
grupo "programa sano, serie con apuesta en la fase A y candado, $((F1 + 1)) fases de un ciclo, $NT ticks" "sano_*"
grupo "programa sano, ventana de la serie Meta con motor, $((F1 + 1)) fases de un ciclo, $NT ticks" "motor_*"
grupo "programa sano, $((F2 + 1)) fases corridas 13 ns" "corrido_*"
grupo "programa sano, periodo de 2501 ciclos" "periodo_2501_*"
SANO=$PEOR
grupo "hilo 3 colgado desde el tick $K (plazo vencido y modo seguro), $((F2 + 1)) fases" "colgado_[0-9]*"
echo
grep -h "^FAIL" $O/*/resultado.txt | head -10
echo "Peor caso con el programa sano: $SANO ciclos ($(echo "scale=2; 100 * $SANO / 2262" | bc) % del presupuesto de la ronda 3, 2262 ciclos)"
echo "Peor caso con el hilo 3 colgado: $PEOR ciclos ($(echo "scale=2; 100 * $PEOR / 2262" | bc) %)"
if [ "$PEOR" -lt "$LIMITE" ]; then echo "PASS: el peor caso, $PEOR ciclos, es menor que $LIMITE (holgura de $(echo "scale=2; 100 * (2262 - $PEOR) / 2262" | bc) % del presupuesto)"
else echo "FAIL: el peor caso, $PEOR ciclos, no es menor que $LIMITE"; fi
} | tee "$SALIDA"
cierre "$SALIDA"
