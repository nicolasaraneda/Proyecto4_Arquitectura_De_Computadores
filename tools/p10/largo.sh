#!/usr/bin/env bash
# largo.sh: rondas de 200 000 ticks por el RTL de R2 (revisión P10,
# docs/revision_p10.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# La puerta corre el RTL con rondas de hasta 20 000 ticks; las de 200 000 solo
# las corrió el gemelo. Aquí se corren por el RTL de R2 (con el vigilante),
# a 0,1 ms, dos series sintéticas de 200 000 ticks, comparando todo con
# ref/fondo.py con tools/fondo/revisar.py: bytes, estado en cada decisión,
# telemetría, una escritura en DECISION por precio, y que el vigilante nunca
# cuente más de un precio sin respuesta. Unos minutos con Verilator.
#
# Uso: tools/p10/largo.sh   (o make p10-largo). Variable: NT.
set -uo pipefail
export HW=r2
source "$(dirname "$0")/../fondo/comun.sh"
BF=build/p10/largo
SIM=$BF/obj/sim
O=$BF
NT=${NT:-200000}
mkdir -p "$O/series"
compilar_sim || exit 1
mal=0
# Sin en_paralelo: ese vuelve a leer comun.sh y usaría el simulador de la
# puerta (build/fondo/r2), no el de esta carpeta.
for fam in modelo volatil; do
  s=$O/series/${fam}_7_$NT.csv
  [ -s "$s" ] || $PYTHON ref/series.py "$fam" --n "$NT" --semilla 7 -o "$s" > /dev/null
  caso "$O/$fam" sw/fondo.s "$s" "$NT" 100000 4000 &
done
wait
for fam in modelo volatil; do
  cat "$O/$fam/resultado.txt"
  grep -q "^PASS" "$O/$fam/resultado.txt" || mal=1
done
[ $mal = 0 ] && echo "PASS p10-largo" || echo "FAIL p10-largo"
exit $mal
