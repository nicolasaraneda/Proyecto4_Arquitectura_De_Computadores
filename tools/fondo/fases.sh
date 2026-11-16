#!/usr/bin/env bash
# fases.sh: peor caso de la respuesta del fondo barriendo la fase de llegada del
# precio (criterio 4 de la puerta de simulación).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# La respuesta depende de en qué punto de sus lazos está cada hilo cuando llega
# el precio: el lazo de sondeo del supervisor dura 12 ciclos, el de los
# gestores 8 y la rotación de hilos 4, así que el patrón se repite cada 24
# ciclos. Se corre el inicio de la serie de a un ciclo:
#
#   1. 48 fases (dos vueltas completas del patrón) con el programa sano, 1100
#      ticks cada una (dos fronteras de ventana por corrida).
#   2. Las mismas 24 primeras fases corridas 13 ns, para que el precio no llegue
#      alineado con el reloj.
#   3. Un período de 2501 ciclos, que recorre todas las fases dentro de una
#      misma corrida de 20 000 ticks, con todas sus fronteras.
#   4. 24 fases con un gestor colgado y 24 con los tres colgados, que es cuando
#      el supervisor agota el plazo: el peor caso degradado.
#
# En todas se exige además lo de siempre: bytes, estado, telemetría y protocolo
# iguales a la referencia. El límite es el presupuesto de la ronda 3 con 50 %
# de holgura: 1131 ciclos.
#
# Uso: tools/fondo/fases.sh   (o make fondo-fases). Variables: CORTA=1, JOBS.
# Resultado en docs/mediciones/fondo/HW/fases.txt (HW es r1 o r2).
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BF/fases
LIMITE=1131
NT=1100
SALIDA=${SALIDA:-$MF/fases.txt}
F1=47; F2=23; LARGO=20000
[ "${CORTA:-0}" = 1 ] && { F1=23; F2=7; LARGO=3000; }
rm -rf "$O"; mkdir -p "$O"
ensamblar_fondo || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1
$PYTHON $TF/variante.py cuelgue:3:1 -o "$O/colgado.s"
$PYTHON $TF/variante.py cuelgue:1:1+cuelgue:2:1+cuelgue:3:1 -o "$O/colgados.s"

{
  for f in $(seq 0 $F1); do echo "caso $O/sano_$f sw/fondo.s tb/practica.csv $NT 100000 $((4000 + 40 * f)) --limite $LIMITE"; done
  for f in $(seq 0 $F2); do echo "caso $O/corrido_$f sw/fondo.s tb/practica.csv $NT 100000 $((4013 + 40 * f)) --limite $LIMITE"; done
  echo "caso $O/periodo_2501 sw/fondo.s tb/practica.csv $LARGO 100040 4000 --limite $LIMITE"
  for f in $(seq 0 $F2); do
    echo "caso $O/colgado_$f $O/colgado.s tb/practica.csv $NT 100000 $((4000 + 40 * f)) --limite $LIMITE --falla 3:1:"
    echo "caso $O/colgados_$f $O/colgados.s tb/practica.csv $NT 100000 $((4000 + 40 * f)) --limite $LIMITE --falla 1:1: --falla 2:1: --falla 3:1: --solo-max-media"
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
cabecera "Peor caso de la respuesta del fondo barriendo la fase de llegada del precio" tools/fondo/fases.sh "make fondo-fases"
PEOR=0
grupo "programa sano, $((F1 + 1)) fases de un ciclo, $NT ticks" "sano_*"
grupo "programa sano, $((F2 + 1)) fases corridas 13 ns" "corrido_*"
grupo "programa sano, periodo de 2501 ciclos, $LARGO ticks" "periodo_2501"
SANO=$PEOR
grupo "gestor 3 colgado, $((F2 + 1)) fases" "colgado_[0-9]*"
grupo "los tres gestores colgados, $((F2 + 1)) fases" "colgados_[0-9]*"
echo
grep -h "^FAIL" $O/*/resultado.txt | head -10
echo "Peor caso con el programa sano: $SANO ciclos ($(echo "scale=2; 100 * $SANO / 2262" | bc) % del presupuesto de la ronda 3, 2262 ciclos)"
echo "Peor caso con gestores colgados (plazo agotado): $PEOR ciclos ($(echo "scale=2; 100 * $PEOR / 2262" | bc) %)"
if [ "$PEOR" -lt "$LIMITE" ]; then echo "PASS: el peor caso, $PEOR ciclos, es menor que $LIMITE (holgura de $(echo "scale=2; 100 * (2262 - $PEOR) / 2262" | bc) %)"
else echo "FAIL: el peor caso, $PEOR ciclos, no es menor que $LIMITE"; fi
} | tee "$SALIDA"
cierre "$SALIDA"
