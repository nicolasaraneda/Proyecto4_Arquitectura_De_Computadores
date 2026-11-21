#!/usr/bin/env bash
# puerta_b.sh: puerta b de R3. El assembly de los cuatro hilos (sw/c1.s) contra la
# referencia entera (ref/c1/c1.py), orden por orden, en las series reales de práctica
# (Tesla, AMD y Meta) y en 200 ventanas reales más, a los tres ritmos de tick.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   1. RTL (tb/c1/tb_c1.sv, Verilator): Tesla, AMD y Meta completas (20 000 ticks) a
#      0,1 ms y a 1 ms, y Meta a 10 ms (con RONDA1=1; unos 30 minutos). Se compara
#      cada byte que lee la maestra y, tick a tick, el estado de los cuatro hilos (las
#      dos cuentas, D, el modo, la clase, las posiciones y el patrimonio emulado),
#      más el protocolo de memoria compartida y la respuesta bajo 1131 ciclos.
#   2. RTL: las 200 ventanas (20 000 ticks cada una) a 0,1 ms, con lo mismo.
#   3. Gemelo digital con la tabla de 512 palabras (validado contra el RTL de R3 con
#      make c1-cosim): las 203 series a 0,1 ms, 1 ms y 10 ms. Bytes, precios sin leer,
#      respuestas y peor caso.
#
# Tesla y AMD son las series de la clase del 18/11 (tools/reales.sh) y las ventanas
# salen de $P4_DATOS/minuto (tools/c1/ventanas.py, semilla 21): no están en el
# repositorio.
#
# Uso: [RONDA1=1] [JOBS=12] [VENTANAS=200] tools/c1/puerta_b.sh   (make c1-puerta-b)
# Resultado en docs/mediciones/c1/puerta_b.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BC/puerta_b
NV=${VENTANAS:-200}
SALIDA=${SALIDA:-$MC/puerta_b.txt}
rm -rf "$O"; mkdir -p "$O"
ensamblar_c1 || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1
compilar_gemelo || exit 1
reales || { echo "FAIL: no se pudieron armar Tesla y AMD (falta P4_DATOS)"; exit 1; }
$PYTHON $TC/ventanas.py "$O/ventanas" --n "$NV" > "$O/ventanas.txt" || { echo "FAIL: no se pudieron armar las ventanas"; exit 1; }
PERIODOS="100000 1000000"
[ "${RONDA1:-0}" = 1 ] && LARGO=10000000 || LARGO=""

{
  for s in tesla amd; do for per in $PERIODOS; do
    echo "caso $O/${s}_$per --serie $BC/series/$s.csv --nticks 20000 --periodo-ns $per"
  done; done
  for per in $PERIODOS $LARGO; do echo "caso $O/meta_$per --serie data/practica_meta.csv --nticks 20000 --periodo-ns $per"; done
  while read -r v; do echo "caso $O/v_$(basename "$v" .csv) --serie $v --nticks 20000"; done < "$O/ventanas.txt"
} | en_paralelo

{ echo data/practica_meta.csv; echo "$BC/series/tesla.csv"; echo "$BC/series/amd.csv"; cat "$O/ventanas.txt"; } > "$O/lista.txt"
$PYTHON $TC/gemelo_lote.py "$O/lista.txt" --jobs "${JOBS:-6}" --salida "$O/gemelo.txt" > /dev/null

{
cabecera "Puerta b de R3: sw/c1.s contra la referencia entera, orden por orden" tools/c1/puerta_b.sh "make c1-puerta-b"
echo "1. RTL (tb/c1/tb_c1.sv): series reales de practica completas, bytes y estado tick a tick"
for s in tesla amd meta; do for per in $PERIODOS $LARGO; do [ -f "$O/${s}_$per/resultado.txt" ] && cat "$O/${s}_$per/resultado.txt"; done; done
[ -z "$LARGO" ] && echo "(la serie Meta a 10 ms por el RTL se corre con RONDA1=1)"
echo
echo "2. RTL: $NV ventanas reales de 20 000 ticks a 0,1 ms (tools/c1/ventanas.py, semilla 21)"
n=0; p=0; peor=0; tk=0; ord=0; cand=0
for v in $(cat "$O/ventanas.txt"); do
  r=$O/v_$(basename "$v" .csv)/resultado.txt
  n=$((n + 1))
  if grep -q "^PASS" "$r"; then
    p=$((p + 1)); tk=$((tk + $(sed -n 's/^PASS [^:]*: \([0-9]*\) bytes.*/\1/p' "$r")))
    c=$(sed -n 's/.*peor caso \([0-9]*\) de.*/\1/p' "$r"); [ "$c" -gt "$peor" ] && peor=$c
    ord=$((ord + $(sed -n 's/.*, \([0-9]*\) órdenes.*/\1/p' "$r")))
    grep -q "modo final 2" "$r" && cand=$((cand + 1))
  else cat "$r"; fi
done
if [ "$p" = "$n" ] && [ "$n" -gt 0 ]; then echo "PASS: $p de $n ventanas identicas a la referencia en bytes y estado, $tk ticks, $ord ordenes, $cand terminan en candado, peor caso $peor ciclos de $LIMITE"
else echo "FAIL: pasan $p de $n ventanas"; fi
echo
echo "3. Gemelo digital con la tabla de 512 palabras, a los tres periodos"
sed -n '3,$p' "$O/gemelo.txt"
echo
t=$(cat "$O"/*/resultado.txt | sed -n 's/^PASS [^:]*: \([0-9]*\) bytes.*/\1/p' | paste -sd+ | bc)
echo "Ticks comparados por el RTL en los casos que pasan: $t"
} | tee "$SALIDA"
cierre "$SALIDA"
