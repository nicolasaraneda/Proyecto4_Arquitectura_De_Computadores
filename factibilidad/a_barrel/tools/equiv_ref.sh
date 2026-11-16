#!/usr/bin/env bash
# equiv_ref.sh: la regla base en el hilo 0 del barrel contra la referencia en
# Python, en los 20 000 ticks de la serie de práctica.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Hace lo mismo que tools/equiv.sh del repositorio, pero con los fuentes del
# SoC barrel y dentro de la carpeta de build del prototipo: corre una copia
# parametrizada del testbench oficial (solo cambian PROGRAMA, PERIODO_NS,
# NTICKS y el nombre del archivo de salida), genera el decisiones.csv de
# referencia con ref/trader.py y exige que los dos sean idénticos byte a byte
# y que el testbench entregue 4/4.
#
# El programa es sw/trade.s sin modificar, con la tabla de arranque delante.
# Simulador: Verilator (decisión T14: Icarus demora 13 minutos por corrida).
#
# Uso: factibilidad/a_barrel/tools/equiv_ref.sh   (o make equiv)
# Con RONDA1=1 (make equiv-ronda1) corre además el período de la ronda 1,
# 10 ms, que demora bastante más.
# Resultado en factibilidad/a_barrel/mediciones/equiv_ref.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/equiv
mkdir -p "$O"
programas
NTICKS=${NTICKS:-20000}
SERIE=tb/practica.csv
HEX=$B/sw/trade_h0.hex

# caso ETIQUETA PERIODO_NS
caso() {
  local e=$1 per=$2 d=$O/$1
  mkdir -p "$d"
  sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"$HEX\";|" \
      -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $per;|" \
      -e "s|NTICKS     = [0-9]*;|NTICKS     = $NTICKS;|" \
      -e "s|\"decisiones.csv\"|\"$d/tb.csv\"|" \
      tb/tb_proyecto_4.sv > "$d/tb_p4.sv"
  if [ "$(diff tb/tb_proyecto_4.sv "$d/tb_p4.sv" | grep -c '^>')" -gt 4 ]; then
    echo "FAIL $e: la copia del testbench cambio mas de lo esperado"; return
  fi
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_proyecto_4 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS -O3 --Mdir "$d/obj" -o sim \
    "$CELLS_SIM" $BARREL_SRC "$d/tb_p4.sv" > "$d/verilator.log" 2>&1 || { echo "FAIL $e: Verilator no compila"; return; }
  "$d/obj/sim" > "$d/tb.log"
  $PYTHON ref/trader.py "$SERIE" --nticks "$NTICKS" --periodo-ns "$per" -o "$d/ref.csv" > "$d/ref.log"
  local resumen="periodo $per ns, $NTICKS ticks, $(grep 'Peor caso' "$d/tb.log" | sed 's/  */ /g')"
  if ! grep -q "Testbenchs aprobados: 4/4" "$d/tb.log"; then echo "FAIL $e: $resumen: el testbench no entrega 4/4"; return; fi
  if ! cmp -s "$d/tb.csv" "$d/ref.csv"; then echo "FAIL $e: $resumen: decisiones distintas a la referencia"; return; fi
  echo "PASS $e: $resumen, 4/4, $(($(wc -l < "$d/tb.csv") - 1)) filas identicas a ref/trader.py, patrimonio $(tail -1 "$d/tb.csv" | cut -d, -f6)"
}

{
echo "Regla base en el hilo 0 del barrel contra ref/trader.py, serie de practica completa"
echo "Generado por factibilidad/a_barrel/tools/equiv_ref.sh (make equiv). No editar a mano."
echo
versiones
echo "  $(verilator --version)"
echo
caso ronda3_0p1ms 100000
caso ronda2_1ms   1000000
if [ "${RONDA1:-0}" = 1 ]; then
  caso ronda1_10ms 10000000
else
  echo
  echo "No se corrio el periodo de la ronda 1 (10 ms): con Verilator son unos 25 minutos. Se agrega con RONDA1=1 (make equiv-ronda1)."
fi
} | tee "$M/equiv_ref.txt"

! grep -q "^FAIL" "$M/equiv_ref.txt"
