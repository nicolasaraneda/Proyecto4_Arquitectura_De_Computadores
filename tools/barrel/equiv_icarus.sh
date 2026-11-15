#!/usr/bin/env bash
# equiv_icarus.sh: max_media en el hilo 0 del barrel contra la referencia
# en Python, en los 20 000 ticks de la serie de práctica, con Icarus Verilog.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Es la misma corrida de tools/barrel/equiv_ref.sh (ronda 3, 0,1 ms) con el simulador
# del encabezado del testbench oficial en vez de Verilator. Icarus simula con
# cuatro estados, así que el chequeo "MISO sin X" del testbench vale para la
# serie completa, cosa que Verilator no puede mostrar. Demora unos 15 minutos.
#
# Uso: tools/barrel/equiv_icarus.sh   (o make barrel-equiv-icarus)
# Resultado en docs/mediciones/barrel/equiv_icarus.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/equiv_icarus
mkdir -p "$O"
programas
NTICKS=${NTICKS:-20000}
PER=${PER:-100000}
HEX=$B/sw/trade_h0.hex

{
echo "max_media en el hilo 0 del barrel contra ref/trader.py, serie de practica completa, con Icarus Verilog"
echo "Generado por tools/barrel/equiv_icarus.sh (make barrel-equiv-icarus). No editar a mano."
echo
versiones
echo
sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"$HEX\";|" \
    -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $PER;|" \
    -e "s|NTICKS     = [0-9]*;|NTICKS     = $NTICKS;|" \
    -e "s|\"decisiones.csv\"|\"$O/tb.csv\"|" \
    tb/tb_proyecto_4.sv > "$O/tb_p4.sv"
if [ "$(diff tb/tb_proyecto_4.sv "$O/tb_p4.sv" | grep -c '^>')" -gt 4 ]; then
  echo "FAIL la copia del testbench cambio mas de lo esperado"
elif ! iverilog -g2012 -s tb_proyecto_4 -o "$O/sim.vvp" "$CELLS_SIM" $BARREL_SRC "$O/tb_p4.sv" > "$O/iverilog.log" 2>&1; then
  echo "FAIL Icarus no compila (ver $O/iverilog.log)"
else
  s=$(date +%s)
  vvp -n "$O/sim.vvp" > "$O/tb.log" 2>&1
  $PYTHON ref/trader.py tb/practica.csv --nticks "$NTICKS" --periodo-ns "$PER" -o "$O/ref.csv" > "$O/ref.log"
  resumen="periodo $PER ns, $NTICKS ticks, $(grep 'Peor caso' "$O/tb.log" | sed 's/  */ /g')"
  grep -E "^ *(PASS|FAIL) " "$O/tb.log" | sed 's/^ */  /'
  if ! grep -q "Testbenchs aprobados: 4/4" "$O/tb.log"; then echo "FAIL $resumen: el testbench no entrega 4/4"
  elif ! cmp -s "$O/tb.csv" "$O/ref.csv"; then echo "FAIL $resumen: decisiones distintas a la referencia"
  else echo "PASS $resumen, 4/4, $(($(wc -l < "$O/tb.csv") - 1)) filas identicas a ref/trader.py, patrimonio $(tail -1 "$O/tb.csv" | cut -d, -f6)"; fi
  echo "Tiempo de simulacion: $(( $(date +%s) - s )) s."
fi
} | tee "$M/equiv_icarus.txt"

! grep -q "^FAIL" "$M/equiv_icarus.txt"
