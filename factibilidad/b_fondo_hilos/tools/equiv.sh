#!/usr/bin/env bash
# equiv.sh: el fondo de cuatro hilos contra la referencia en C, byte a byte,
# con una copia parametrizada del testbench oficial.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Hace lo mismo que tools/equiv.sh del repositorio, con los fuentes del SoC
# barrel y dentro de la carpeta de build de esta pieza: la copia del testbench
# solo cambia PROGRAMA, SERIE, PERIODO_NS, NTICKS y el nombre del archivo de
# salida (se comprueba que no cambie nada más), se genera el decisiones.csv de
# referencia con el módulo en C (fondo_min) y se exige que los dos archivos
# sean idénticos byte a byte y que el testbench entregue 4/4.
#
# Casos:
#   - la serie de práctica completa, 20 000 ticks, a 0,1 ms y a 1 ms
#   - 8 series sintéticas de familias distintas (ref/series.py, semilla 1),
#     20 000 ticks cada una a 0,1 ms. Con 20 000 ticks hay 39 fronteras de
#     ventana por serie, que es donde se ajustan los pesos.
#   - con RONDA1=1, además la práctica a 10 ms (unos 25 minutos)
#
# Simulador: Verilator (decisión T14). Los casos corren de a JOBS (5).
#
# Uso: factibilidad/b_fondo_hilos/tools/equiv.sh   (o make equiv)
# Resultado en mediciones/equiv.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/equiv
mkdir -p "$O"
armar base || exit 1
HEX=$B/prog/base/fondo.hex
NTICKS=${NTICKS:-20000}
FAMILIAS=${FAMILIAS:-"modelo remuestreo tendencia saltos cambio_de_caracter volatil borde_alto plana"}

# caso ETIQUETA SERIE PERIODO_NS: deja una línea PASS o FAIL en O/ETIQUETA/resultado.txt
caso() {
  local e=$1 serie=$2 per=$3 d=$O/$1 k
  mkdir -p "$d"
  sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"$HEX\";|" \
      -e "s|SERIE      = \"[^\"]*\";|SERIE      = \"$serie\";|" \
      -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $per;|" \
      -e "s|NTICKS     = [0-9]*;|NTICKS     = $NTICKS;|" \
      -e "s|\"decisiones.csv\"|\"$d/tb.csv\"|" \
      tb/tb_proyecto_4.sv > "$d/tb_p4.sv"
  if [ "$(diff tb/tb_proyecto_4.sv "$d/tb_p4.sv" | grep -c '^>')" -gt 5 ]; then
    echo "FAIL $e: la copia del testbench cambio mas de lo esperado" > "$d/resultado.txt"; return
  fi
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_proyecto_4 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS -O3 --Mdir "$d/obj" -o sim \
    "$CELLS_SIM" $BARREL_SRC "$d/tb_p4.sv" > "$d/verilator.log" 2>&1 || { echo "FAIL $e: Verilator no compila" > "$d/resultado.txt"; return; }
  "$d/obj/sim" > "$d/tb.log"
  k=$(perdidos "$per")
  referencia fondo_min "$serie" "$NTICKS" "$k" "$d/ref.csv" > "$d/ref.log"
  local resumen="periodo $per ns, $NTICKS ticks, precios $(tail -n +2 "$serie" | head -"$NTICKS" | cut -d, -f2 | sort -n | sed -n '1p;$p' | tr '\n' ' ' | sed 's/ $//; s/ / a /'), $(grep 'Peor caso' "$d/tb.log" | sed 's/  */ /g')"
  if ! grep -q "Testbenchs aprobados: 4/4" "$d/tb.log"; then echo "FAIL $e: $resumen: el testbench no entrega 4/4" > "$d/resultado.txt"; return; fi
  if ! cmp -s "$d/tb.csv" "$d/ref.csv"; then
    echo "FAIL $e: $resumen: decisiones distintas a la referencia. Primera fila distinta: $(diff "$d/tb.csv" "$d/ref.csv" | sed -n 2,4p | tr '\n' ' ')" > "$d/resultado.txt"; return
  fi
  echo "PASS $e: $resumen, 4/4, $(($(wc -l < "$d/tb.csv") - 1)) filas identicas a la referencia, $(tail -n +2 "$d/tb.csv" | cut -d, -f3 | sort | uniq -c | awk '{printf "%s x %d ", $2, $1}'), ordenes $(grep 'Ordenes' "$d/tb.log" | grep -o '[0-9]*$'), patrimonio $(tail -1 "$d/tb.csv" | cut -d, -f6)" > "$d/resultado.txt"
}
export -f caso perdidos referencia
export O B HEX NTICKS CELLS_SIM BARREL_SRC ARNES PYTHON

CASOS="practica_0p1ms tb/practica.csv 100000
practica_1ms tb/practica.csv 1000000"
ORDEN="practica_0p1ms practica_1ms"
for f in $FAMILIAS; do
  s=$(serie_sintetica "$f" 1 "$NTICKS")
  CASOS="$CASOS
sintetica_$f $s 100000"
  ORDEN="$ORDEN sintetica_$f"
done
if [ "${RONDA1:-0}" = 1 ]; then
  CASOS="$CASOS
practica_10ms tb/practica.csv 10000000"
  ORDEN="$ORDEN practica_10ms"
fi
T0=$(date +%s)
echo "$CASOS" | xargs -P "$JOBS" -L 1 bash -c 'caso "$@"' _
T1=$(date +%s)

{
echo "Fondo de cuatro hilos (sw/fondo.s) en el barrel contra la referencia en C (fondo_min), byte a byte"
echo "Generado por factibilidad/b_fondo_hilos/tools/equiv.sh (make equiv). No editar a mano."
echo
versiones
echo "Referencia: $ARNES correr --estrategia fondo_min (factibilidad/retorno/r4b_fondo/fondo.c, sin modificar)"
echo "Testbench: copia de tb/tb_proyecto_4.sv con PROGRAMA, SERIE, PERIODO_NS, NTICKS y el archivo de salida cambiados"
echo "Series sinteticas: ref/series.py FAMILIA --n $NTICKS --semilla 1"
echo "Demora: $((T1 - T0)) s con $JOBS procesos"
echo
for e in $ORDEN; do cat "$O/$e/resultado.txt" 2>/dev/null || echo "FAIL $e: sin resultado"; done
echo
if [ "${RONDA1:-0}" != 1 ]; then
  echo "No se corrio el periodo de la ronda 1 (10 ms): con Verilator son unos 25 minutos. Se agrega con RONDA1=1 (make equiv-ronda1)."
fi
echo "Casos: $(echo $ORDEN | wc -w). PASS: $(for e in $ORDEN; do cat "$O/$e/resultado.txt"; done | grep -c '^PASS'). Ticks comparados: $(( $(echo $ORDEN | wc -w) * NTICKS ))."
} | tee "$M/equiv${SUFIJO:-}.txt"

! grep -q "^FAIL" "$M/equiv${SUFIJO:-}.txt"
