#!/usr/bin/env bash
# sin_tabla.sh: qué pasa si el barrel recibe un programa sin la tabla de
# arranque.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# En el barrel el hilo t parte en la dirección 4 t y todo programa tiene que
# empezar con cuatro saltos. sw/trade.hex, el programa del Espino base, no los
# tiene: los hilos 1, 2 y 3 partirían en la segunda, tercera y cuarta
# instrucción del programa. Este script lo corre así, con una copia
# parametrizada del testbench oficial, para dejar medido el modo de falla. Es
# un riesgo de operación (cambiar el programa con icebram o regenerarlo con
# tools/retune.py sin anteponer la tabla), no un error del core.
#
# Uso: factibilidad/a_barrel/tools/sin_tabla.sh   (o make sin-tabla)
# Resultado en factibilidad/a_barrel/mediciones/sin_tabla.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/sin_tabla
NTICKS=${NTICKS:-2000}
mkdir -p "$O"
programas
cp sw/trade.hex "$O/sin_tabla.hex"
cp "$B/sw/trade_h0.hex" "$O/con_tabla.hex"

sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"prog.hex\";|" \
    -e "s|SERIE      = \"[^\"]*\";|SERIE      = \"$RAIZ/tb/practica.csv\";|" \
    -e "s|NTICKS     = [0-9]*;|NTICKS     = $NTICKS;|" \
    -e "s|\"decisiones.csv\"|\"tb.csv\"|" \
    tb/tb_proyecto_4.sv > "$O/tb_p4.sv"
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_proyecto_4 \
  -DNO_ICE40_DEFAULT_ASSIGNMENTS -O3 --Mdir "$O/obj" -o sim \
  "$CELLS_SIM" $BARREL_SRC "$O/tb_p4.sv" > "$O/verilator.log" 2>&1 || { echo "FAIL sin_tabla: el testbench no compila"; exit 1; }
$PYTHON ref/trader.py tb/practica.csv --nticks "$NTICKS" --periodo-ns 100000 -o "$O/ref.csv" > "$O/ref.log"

# corre NOMBRE: deja NOMBRE/tb.log y NOMBRE/tb.csv
corre() {
  mkdir -p "$O/$1"
  cp "$O/$1.hex" "$O/$1/prog.hex"
  ( cd "$O/$1" && timeout 600 ../obj/sim > tb.log 2>&1 )
}
corre con_tabla
corre sin_tabla

{
echo "El barrel con un programa sin la tabla de arranque"
echo "Generado por factibilidad/a_barrel/tools/sin_tabla.sh (make sin-tabla). No editar a mano."
echo
versiones
echo
echo "Copia parametrizada de tb/tb_proyecto_4.sv, $NTICKS ticks, periodo 100000 ns. Referencia: ref/trader.py."
echo
for n in con_tabla sin_tabla; do
  [ $n = con_tabla ] && echo "--- sw/trade.s con la tabla (tools/tabla.py), hilo 0 ---" || echo "--- sw/trade.hex tal como esta, sin tabla ---"
  grep -E "^(PASS|FAIL)|Testbenchs aprobados|Patrimonio final|Peor caso" "$O/$n/tb.log" | sed 's/^/  /'
  if [ -s "$O/$n/tb.csv" ]; then
    dif=$(paste -d'|' "$O/$n/tb.csv" "$O/ref.csv" | awk -F'|' '$1 != $2' | wc -l)
    echo "  Filas de decisiones.csv distintas a la referencia: $dif de $(($(wc -l < "$O/ref.csv") - 1))"
  else
    echo "  No hay decisiones.csv"
  fi
  echo
done
ok_con=0; ok_sin=0
grep -q "Testbenchs aprobados: 4/4" "$O/con_tabla/tb.log" && cmp -s "$O/con_tabla/tb.csv" "$O/ref.csv" && ok_con=1
grep -q "Testbenchs aprobados: 4/4" "$O/sin_tabla/tb.log" && cmp -s "$O/sin_tabla/tb.csv" "$O/ref.csv" && ok_sin=1
if [ $ok_con = 1 ] && [ $ok_sin = 0 ]; then
  echo "RESULTADO: como se esperaba, con la tabla funciona y sin la tabla NO. El programa del Espino base no se puede cargar tal cual en el barrel."
elif [ $ok_sin = 1 ]; then
  echo "RESULTADO: INESPERADO, el programa sin tabla tambien entrega 4/4 y decide igual que la referencia"
else
  echo "RESULTADO: FAIL, el programa con tabla no funciona"
fi
} | tee "$M/sin_tabla.txt"

grep -q "^RESULTADO: como se esperaba" "$M/sin_tabla.txt"
