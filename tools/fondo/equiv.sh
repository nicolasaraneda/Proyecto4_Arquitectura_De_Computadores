#!/usr/bin/env bash
# equiv.sh: equivalencia del fondo en un chip con ref/fondo.py (criterio 2 de
# la puerta de simulación).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   1. Copia parametrizada del testbench oficial (solo cambian el programa, el
#      período, la cantidad de ticks y el archivo de salida) con Verilator: los
#      20 000 ticks de la serie de práctica a 0,1 ms y a 1 ms (y a 10 ms con
#      RONDA1=1, unos 35 minutos). Exige 4/4 y decisiones.csv idéntico.
#   2. tb/fondo/tb_fondo.sv con las mismas series y una serie de 20 000 ticks de
#      cada familia sintética: bytes, estado interno en cada decisión (votos,
#      puntajes, pesos y PUB), telemetría y protocolo.
#
# Uso: tools/fondo/equiv.sh   (o make fondo-equiv; make fondo-equiv-ronda1)
# Variables: NTICKS (20000), CORTA=1 (2000 ticks y sin la copia del oficial a
# 1 ms, para la integración continua), RONDA1=1, JOBS.
# Resultado en docs/mediciones/fondo/equiv.txt.
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

# copia PERIODO_NS: la copia parametrizada del testbench oficial
copia() {
  local per=$1 d=$O/oficial_$1
  mkdir -p "$d"
  sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"$FONDO_HEX\";|" \
      -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $per;|" \
      -e "s|NTICKS     = [0-9]*;|NTICKS     = $NT;|" \
      -e "s|\"decisiones.csv\"|\"$d/tb.csv\"|" \
      tb/tb_proyecto_4.sv > "$d/tb_p4.sv"
  if [ "$(diff tb/tb_proyecto_4.sv "$d/tb_p4.sv" | grep -c '^>')" -gt 4 ]; then
    echo "FAIL copia del oficial a $per ns: la copia cambio mas de lo esperado" > "$d/resultado.txt"; return
  fi
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_proyecto_4 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS -O3 --Mdir "$d/obj" -o sim \
    "$CELLS_SIM" $FONDO_SRC "$d/tb_p4.sv" > "$d/verilator.log" 2>&1 || { echo "FAIL copia del oficial a $per ns: Verilator no compila" > "$d/resultado.txt"; return; }
  "$d/obj/sim" > "$d/tb.log"
  $PYTHON ref/fondo.py tb/practica.csv --nticks "$NT" --periodo-ns "$per" -o "$d/ref.csv" > "$d/ref.log"
  local r="copia del oficial, practica, periodo $per ns, $NT ticks, $(grep 'Peor caso' "$d/tb.log" | sed 's/  */ /g')"
  if ! grep -q "Testbenchs aprobados: 4/4" "$d/tb.log"; then echo "FAIL $r: no entrega 4/4" > "$d/resultado.txt"; return; fi
  if ! cmp -s "$d/tb.csv" "$d/ref.csv"; then echo "FAIL $r: decisiones distintas a la referencia" > "$d/resultado.txt"; return; fi
  echo "PASS $r, 4/4, $(($(wc -l < "$d/tb.csv") - 1)) filas identicas, patrimonio $(tail -1 "$d/tb.csv" | cut -d, -f6)" > "$d/resultado.txt"
}
export -f copia; export O NT

{
  for per in $PERIODOS; do echo "copia $per"; done
  for per in $PERIODOS; do echo "caso $O/practica_$per sw/fondo.s tb/practica.csv $NT $per 4000"; done
  for f in $FAMILIAS; do echo "caso $O/$f sw/fondo.s \$(serie $f 1 $NT) $NT 100000 4000"; done
} | en_paralelo

{
cabecera "Equivalencia del fondo en un chip con su referencia" tools/fondo/equiv.sh "make fondo-equiv"
echo "1. Copia parametrizada del testbench oficial (Verilator)"
for per in $PERIODOS; do cat "$O/oficial_$per/resultado.txt"; done
echo
echo "2. Bytes, estado interno, telemetria y protocolo (tb/fondo/tb_fondo.sv)"
for per in $PERIODOS; do cat "$O/practica_$per/resultado.txt"; done
for f in $FAMILIAS; do cat "$O/$f/resultado.txt"; done
echo
t=$(cat "$O"/practica_*/resultado.txt $(for f in $FAMILIAS; do echo "$O/$f/resultado.txt"; done) | sed -n 's/^PASS [^:]*: \([0-9]*\) bytes.*/\1/p' | paste -sd+ | bc)
echo "Ticks comparados con tb_fondo.sv en los casos que pasan: $t"
} | tee "$SALIDA"
cierre "$SALIDA"
