#!/usr/bin/env bash
# equiv.sh: equivalencia de R1 y R2 con ref/fondo.py (criterio 2 de la puerta
# de simulación).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   1. Copia parametrizada del testbench oficial (cambian el programa, el
#      período, la cantidad de ticks, el archivo de salida y, en la de la serie
#      Meta, la serie) con Verilator: los 20 000 ticks de la serie Meta y de la
#      serie de práctica anterior a 0,1 ms y a 1 ms (y a 10 ms con RONDA1=1).
#      Exige 4/4 y decisiones.csv idéntico.
#   2. tb/fondo/tb_fondo.sv con la serie Meta a esos períodos, la serie anterior,
#      y una serie de 20 000 ticks de cada familia sintética, cruda y normalizada
#      entre 100 y 255 (desde el 17/11 la regla de R1 y R2 solo opera cuando la
#      serie toca esos extremos): bytes, estado tick a tick, telemetría y
#      protocolo.
#
# Uso: tools/fondo/equiv.sh   (o make fondo-equiv; make fondo-equiv-ronda1)
# Variables: NTICKS (20000), CORTA=1 (2000 ticks y sin la copia del oficial a
# 1 ms, para la integración continua), RONDA1=1, JOBS.
# Resultado en docs/mediciones/fondo/HW/equiv.txt (HW es r1 o r2).

set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BF/equiv
NT=${NTICKS:-20000}
[ "${CORTA:-0}" = 1 ] && NT=2000
SALIDA=${SALIDA:-$MF/equiv.txt}
PERIODOS="100000 1000000"
[ "${RONDA1:-0}" = 1 ] && PERIODOS="$PERIODOS 10000000"
[ "${CORTA:-0}" = 1 ] && PERIODOS="100000"
FAMILIAS="remuestreo modelo modelo_vecino paseo tendencia reversion dos_componentes saltos cambio_volatilidad cambio_de_caracter volatil nivel_bajo plana borde_bajo borde_alto"
mkdir -p "$O"
ensamblar_fondo || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1

# copia PERIODO_NS [SERIE]: la copia parametrizada del testbench oficial
copia() {
  local per=$1 ser=${2:-tb/practica.csv} d=$O/oficial_$1${2:+_meta} cambios=4
  mkdir -p "$d"
  [ -n "${2:-}" ] && cambios=5
  sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"$FONDO_HEX\";|" \
      -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $per;|" \
      -e "s|NTICKS     = [0-9]*;|NTICKS     = $NT;|" \
      -e "s|SERIE      = \"[^\"]*\";|SERIE      = \"$ser\";|" \
      -e "s|\"decisiones.csv\"|\"$d/tb.csv\"|" \
      tb/tb_proyecto_4.sv > "$d/tb_p4.sv"
  if [ "$(diff tb/tb_proyecto_4.sv "$d/tb_p4.sv" | grep -c '^>')" -gt $cambios ]; then
    echo "FAIL copia del oficial a $per ns: la copia cambio mas de lo esperado" > "$d/resultado.txt"; return
  fi
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_proyecto_4 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS -O3 --Mdir "$d/obj" -o sim \
    "$CELLS_SIM" $FONDO_SRC "$d/tb_p4.sv" > "$d/verilator.log" 2>&1 || { echo "FAIL copia del oficial a $per ns: Verilator no compila" > "$d/resultado.txt"; return; }
  "$d/obj/sim" > "$d/tb.log"
  $PYTHON ref/fondo.py "$ser" --nticks "$NT" --periodo-ns "$per" -o "$d/ref.csv" > "$d/ref.log"
  local r="copia del oficial, $ser, periodo $per ns, $NT ticks, $(grep 'Peor caso' "$d/tb.log" | sed 's/  */ /g')"
  if ! grep -q "Testbenchs aprobados: 4/4" "$d/tb.log"; then echo "FAIL $r: no entrega 4/4" > "$d/resultado.txt"; return; fi
  if ! cmp -s "$d/tb.csv" "$d/ref.csv"; then echo "FAIL $r: decisiones distintas a la referencia" > "$d/resultado.txt"; return; fi
  echo "PASS $r, 4/4, $(($(wc -l < "$d/tb.csv") - 1)) filas identicas, patrimonio $(tail -1 "$d/tb.csv" | cut -d, -f6)" > "$d/resultado.txt"
}
export -f copia; export O NT

{
  for per in $PERIODOS; do echo "copia $per"; echo "copia $per data/practica_meta.csv"; done
  for per in $PERIODOS; do echo "caso $O/meta_$per sw/fondo.s data/practica_meta.csv $NT $per 4000"; done
  echo "caso $O/practica_anterior sw/fondo.s tb/practica.csv $NT 100000 4000"
  for f in $FAMILIAS; do
    echo "caso $O/$f sw/fondo.s \$(serie $f 1 $NT) $NT 100000 4000"
    echo "caso $O/$f-norm sw/fondo.s \$(serie_norm $f 1 $NT) $NT 100000 4000"
  done
} | en_paralelo

{
cabecera "Equivalencia del fondo en un chip con su referencia" tools/fondo/equiv.sh "make fondo-equiv"
echo "1. Copia parametrizada del testbench oficial (Verilator)"
for per in $PERIODOS; do cat "$O/oficial_$per/resultado.txt" "$O/oficial_${per}_meta/resultado.txt"; done
echo
echo "2. Bytes, estado tick a tick, telemetria y protocolo (tb/fondo/tb_fondo.sv)"
for per in $PERIODOS; do cat "$O/meta_$per/resultado.txt"; done
cat "$O/practica_anterior/resultado.txt"
for f in $FAMILIAS; do cat "$O/$f/resultado.txt" "$O/$f-norm/resultado.txt"; done
echo
t=$(cat "$O"/meta_*/resultado.txt "$O/practica_anterior/resultado.txt" $(for f in $FAMILIAS; do echo "$O/$f/resultado.txt $O/$f-norm/resultado.txt"; done) | sed -n 's/^PASS [^:]*: \([0-9]*\) bytes.*/\1/p' | paste -sd+ | bc)
echo "Ticks comparados con tb_fondo.sv en los casos que pasan: $t"
} | tee "$SALIDA"
cierre "$SALIDA"
