#!/usr/bin/env bash
# vuelta_tick.sh: el número de tick de sw/fondo.s da la vuelta (revisión P10,
# docs/revision_p10.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El supervisor lleva tick * 256 en x3 (32 bits): el número de tick tiene 24
# bits y vuelve a 0 después de 16 777 216 ticks (28 minutos a 0,1 ms). Para
# probar esa vuelta sin simular 16 millones de ticks, se arma una copia de
# sw/fondo.s cuya única diferencia es el valor inicial de x3: 0xFFFC0000 en
# vez de 0, de modo que x3 vale 0 en el tick 1024 (que además es frontera de
# ventana). Los bits 8 y 18 de x3, que usa la telemetría, quedan iguales a los
# del programa original. Se corre con el hardware de R1 y tb/fondo/tb_fondo.sv
# y se compara con ref/fondo.py (bytes, conteos, peor caso; el estado interno
# no se compara porque PUB y los votos llevan otro número de tick).
#
#   1. Programa sano: tiene que ser idéntico a la referencia.
#   2. Gestor 3 colgado desde el arranque (su voto queda en 0): observación.
#      En el tick en que x3 vuelve a 0, EST3 - x3 = 0 y el supervisor toma el
#      voto viejo como si fuera de este tick. Con x3 partiendo en 0, eso pasa
#      en el tick 16 777 216 de una corrida sin reset con un gestor colgado.
#
# Uso: tools/p10/vuelta_tick.sh   (o make p10-vuelta-tick)
set -uo pipefail
export HW=r1
source "$(dirname "$0")/../fondo/comun.sh"
BF=build/p10/vuelta_tick
SIM=$BF/obj/sim
O=$BF
mkdir -p "$O"
compilar_sim || exit 1

ORIG='    li   x3, 0                 # todavía no hay ningún tick'
grep -qF "$ORIG" sw/fondo.s || { echo "FAIL: sw/fondo.s ya no tiene la línea que inicia x3"; exit 1; }
sed "s|^$ORIG\$|    li   x3, 0xFFFC0000        # P10: x3 vuelve a 0 en el tick 1024|" sw/fondo.s > "$O/vuelta.s"
cmp -s sw/fondo.s "$O/vuelta.s" && { echo "FAIL: no se pudo armar la variante"; exit 1; }
$PYTHON $TF/variante.py cuelgue:3:1 -i "$O/vuelta.s" -o "$O/vuelta_colgado.s"
$PYTHON $TF/variante.py cuelgue:3:1 -o "$O/colgado.s"

NT=2000
caso "$O/sano" "$O/vuelta.s" tb/practica.csv $NT 100000 4000 --sin-estado
REV=$(serie reversion 1 $NT)
caso "$O/sano_rev" "$O/vuelta.s" "$REV" $NT 100000 4000 --sin-estado
caso "$O/colgado_ref" "$O/colgado.s" "$REV" $NT 100000 4000 --falla 3:1: --sin-estado
caso "$O/colgado_vuelta" "$O/vuelta_colgado.s" "$REV" $NT 100000 4000 --falla 3:1: --sin-estado

mal=0
for c in sano sano_rev colgado_ref; do
  cat "$O/$c/resultado.txt"
  grep -q "^PASS" "$O/$c/resultado.txt" || mal=1
done
echo "Observacion (gestor 3 colgado y vuelta del tick; se espera una diferencia con la referencia):"
sed 's/^/  /' "$O/colgado_vuelta/resultado.txt"
[ $mal = 0 ] && echo "PASS p10-vuelta-tick" || echo "FAIL p10-vuelta-tick"
exit $mal
