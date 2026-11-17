#!/usr/bin/env bash
# sclk_degradado.sh: SCLK lento a 0,1 ms con el fondo degradado (revisión P10,
# docs/revision_p10.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El árbol de decisión (docs/arbol_decision.md) deja competir a R1 desde SCLK
# de 115 kHz en la ronda 3, con el margen calculado para el programa sano
# (peor caso 444 ciclos). Con un gestor colgado o atrasado el supervisor
# demora más (hasta 559 y 679 ciclos en make fondo-degradacion). Esta prueba
# corre por el RTL de R1, con la forma de transacción de la matriz de estrés
# (CS_SETUP = máx(1500, 3 medio período), CS_HOLD = 500), los 2000 primeros
# ticks de la práctica con el programa sano, con el gestor 3 colgado desde el
# arranque y con el gestor 3 atrasado 200 ciclos, a varios SCLK. Cada caso se
# compara con ref/fondo.py (bytes que lee la maestra, estado, conteos); el
# límite del peor caso se deja abierto para que mande lo que lee la maestra.
#
# Es una exploración: informa la tabla y no termina con error.
#
# Uso: tools/p10/sclk_degradado.sh   (o make p10-sclk-degradado)
set -uo pipefail
export HW=r1
source "$(dirname "$0")/../fondo/comun.sh"
BF=build/p10/sclk_degradado
SIM=$BF/obj/sim
O=$BF
mkdir -p "$O"
compilar_sim || exit 1
$PYTHON $TF/variante.py cuelgue:3:1 -o "$O/colgado.s"
$PYTHON $TF/variante.py atraso:3:200 -o "$O/atrasado.s"
NT=2000
correr() {   # correr KHZ ETIQUETA FUENTE [args de revisar]
  local khz=$1 e=$2 f=$3; shift 3
  local medio=$(( (500000000 / khz + 500) / 1000 ))
  local setup=$(( 3 * medio > 1500 ? 3 * medio : 1500 ))
  PLUS="+SCLK_MEDIO_NS=$medio +CS_SETUP_NS=$setup +CS_HOLD_NS=500" \
    caso "$O/${e}_$khz" "$f" tb/practica.csv $NT 100000 4000 --limite 99999 "$@"
}
for khz in 105 110 115 120 125 130; do
  correr $khz sano sw/fondo.s &
  correr $khz colgado "$O/colgado.s" --falla 3:1: &
  correr $khz atrasado "$O/atrasado.s" &
  wait
done
echo "SCLK minimo a 0,1 ms con el fondo degradado, por el RTL de R1 (exploracion)"
echo "Generado por tools/p10/sclk_degradado.sh. Bytes: lo que lee la maestra contra ref/fondo.py."
echo
printf "%-8s %-10s %-6s %s\n" "SCLK" "programa" "estado" "peor caso y bytes"
for khz in 105 110 115 120 125 130; do
  for e in sano colgado atrasado; do
    r=$O/${e}_$khz/resultado.txt
    est=$(cut -d' ' -f1 "$r")
    peor=$(sed -n 's/.*peor caso \([0-9]*\) de.*/\1/p' "$r")
    difs=$(sed -n 's/.*; \?\([0-9]* bytes distintos[^;]*\).*/\1/p; s/.*\. \([0-9]* bytes distintos[^;]*\).*/\1/p' "$r" | head -1)
    printf "%-8s %-10s %-6s peor caso %s ciclos%s\n" "${khz} kHz" "$e" "$est" "$peor" "${difs:+, $difs}"
  done
done
