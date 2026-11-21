#!/usr/bin/env bash
# oficial.sh: el testbench oficial sin modificar con R3 (criterio 1 de la puerta de
# simulación), y la copia parametrizada del oficial a los tres períodos (parte del
# criterio 2).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   1. tb/tb_proyecto_4.sv tal como está en el repositorio, con Icarus y el comando
#      de su encabezado, más las definiciones de R3. El programa se pone en el lugar
#      de sw/trade.hex dentro de una carpeta de trabajo, porque el testbench tiene
#      ese nombre fijo; la tabla va en sw/c1_tabla.hex de esa carpeta. Exige 4/4 y
#      que decisiones.csv sea idéntico, byte a byte, al de ref/c1/c1.py. La serie de
#      ese testbench (tb/practica.csv) no está normalizada: baja de 100 y R3 pasa a
#      modo seguro, que es lo que la referencia espera.
#   2. Copia parametrizada del oficial (cambian el programa, el período, la cantidad
#      de ticks, la serie y el archivo de salida) con Verilator: los 20 000 ticks de
#      la serie Meta y de tb/practica.csv a 0,1 ms y a 1 ms (y a 10 ms con RONDA1=1).
#      Exige 4/4 y decisiones.csv idéntico.
#
# Uso: [RONDA1=1] [CORTA=1] tools/c1/oficial.sh   (make c1-oficial)
# Resultado en docs/mediciones/c1/oficial.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

d=$BC/oficial
SALIDA=${SALIDA:-$MC/oficial.txt}
NT=20000
PERIODOS="100000 1000000"
[ "${RONDA1:-0}" = 1 ] && PERIODOS="$PERIODOS 10000000"
[ "${CORTA:-0}" = 1 ] && { NT=2000; PERIODOS="100000"; }
rm -rf "$d"; mkdir -p "$d/sw" "$d/tb"
ensamblar_c1 || { echo "FAIL: no ensambla"; exit 1; }
cp "$C1_HEX" "$d/sw/trade.hex"
cp "$TABLA_HEX" "$d/sw/c1_tabla.hex"
ln -sf "$RAIZ/tb/practica.csv" "$d/tb/practica.csv"
iverilog -g2012 -s tb_proyecto_4 -o "$d/tb_p4" "$CELLS_SIM" $C1_SRC tb/tb_proyecto_4.sv || { echo "FAIL: Icarus no compila"; exit 1; }
( cd "$d" && vvp -n tb_p4 > salida.txt ) &
$PYTHON ref/c1/c1.py tb/practica.csv --nticks 2000 --periodo-ns 100000 -o "$d/ref.csv" > "$d/ref.log"

# copia PERIODO_NS SERIE ETIQUETA: la copia parametrizada del testbench oficial
copia() {
  local per=$1 ser=$2 c=$d/copia_$3_$1
  mkdir -p "$c"
  sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"$C1_HEX\";|" \
      -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $per;|" \
      -e "s|NTICKS     = [0-9]*;|NTICKS     = $NT;|" \
      -e "s|SERIE      = \"[^\"]*\";|SERIE      = \"$ser\";|" \
      -e "s|\"decisiones.csv\"|\"$c/tb.csv\"|" \
      tb/tb_proyecto_4.sv > "$c/tb_p4.sv"
  if [ "$(diff tb/tb_proyecto_4.sv "$c/tb_p4.sv" | grep -c '^>')" -gt 5 ]; then
    echo "FAIL copia del oficial, $ser a $per ns: la copia cambio mas de lo esperado" > "$c/resultado.txt"; return
  fi
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_proyecto_4 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS -O3 --Mdir "$c/obj" -o sim \
    "$CELLS_SIM" $C1_SRC "$c/tb_p4.sv" > "$c/verilator.log" 2>&1 || { echo "FAIL copia del oficial, $ser a $per ns: Verilator no compila" > "$c/resultado.txt"; return; }
  "$c/obj/sim" > "$c/tb.log"
  $PYTHON ref/c1/c1.py "$ser" --nticks "$NT" --periodo-ns "$per" -o "$c/ref.csv" > "$c/ref.log"
  local r="copia del oficial, $ser, periodo $per ns, $NT ticks, $(grep 'Peor caso' "$c/tb.log" | sed 's/  */ /g')"
  if ! grep -q "Testbenchs aprobados: 4/4" "$c/tb.log"; then echo "FAIL $r: no entrega 4/4" > "$c/resultado.txt"; return; fi
  if ! cmp -s "$c/tb.csv" "$c/ref.csv"; then echo "FAIL $r: decisiones distintas a la referencia" > "$c/resultado.txt"; return; fi
  echo "PASS $r, 4/4, $(($(wc -l < "$c/tb.csv") - 1)) filas identicas, patrimonio $(tail -1 "$c/tb.csv" | cut -d, -f6)" > "$c/resultado.txt"
}
export -f copia; export d NT

for per in $PERIODOS; do echo "copia $per data/practica_meta.csv meta"; echo "copia $per tb/practica.csv practica"; done | en_paralelo
wait

{
cabecera "Testbench oficial sin modificar con R3 (sw/c1.s)" tools/c1/oficial.sh "make c1-oficial"
if git diff --quiet HEAD -- tb/tb_proyecto_4.sv; then
  echo "tb/tb_proyecto_4.sv: sin cambios respecto del repositorio (sha256 $(sha256sum tb/tb_proyecto_4.sv | cut -c1-16)...)"
else
  echo "FAIL: tb/tb_proyecto_4.sv tiene cambios locales"
fi
echo
echo "1. Testbench oficial sin modificar (Icarus)"
grep -E 'Peor caso|Patrimonio|rdenes|aprobados' "$d/salida.txt" | sed 's/^/  /'
if grep -q "Testbenchs aprobados: 4/4" "$d/salida.txt"; then echo "PASS: 4/4"; else echo "FAIL: no obtiene 4/4"; fi
if cmp -s "$d/decisiones.csv" "$d/ref.csv"; then
  echo "PASS: decisiones.csv identico byte a byte al de ref/c1/c1.py ($(wc -l < "$d/decisiones.csv") lineas, sha256 $(sha256sum "$d/decisiones.csv" | cut -c1-16)...)"
else echo "FAIL: decisiones.csv difiere de ref/c1/c1.py"; fi
echo
echo "2. Copia parametrizada del testbench oficial (Verilator)"
for per in $PERIODOS; do cat "$d/copia_meta_$per/resultado.txt" "$d/copia_practica_$per/resultado.txt"; done
} | tee "$SALIDA"
cierre "$SALIDA"
