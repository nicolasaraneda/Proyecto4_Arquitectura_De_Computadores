#!/usr/bin/env bash
# equiv.sh: equivalencia entre el RTL y la referencia en Python.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre una copia parametrizada del testbench oficial (el original no se
# toca: solo cambian PERIODO_NS, NTICKS, SERIE y el nombre del archivo de
# salida), genera el decisiones.csv de referencia con ref/trader.py y exige
# que los dos archivos sean idénticos byte a byte y que el testbench entregue
# 4/4.
#
# Uso, desde la raíz del repositorio:
#   tools/equiv.sh ETIQUETA PERIODO_NS NTICKS [SERIE]
# Ejemplo:
#   tools/equiv.sh r3 100000 20000 tb/practica.csv
#
# Variables de entorno:
#   HEX   programa (por defecto sw/trade.hex)
#   SRC   fuentes RTL (por defecto rtl/*.v rtl/espino_core/*.v)
#   SIM   iverilog (por defecto) o verilator
#   DEFS  definiciones para elegir la variante del core: vacío para el Espino
#         base, -DESPINO_SEGMENTADO para el pipeline de 3 etapas, o
#         -DESPINO_ROM (y la ROM del programa agregada a SRC)
set -euo pipefail

ETIQUETA=$1
PERIODO_NS=$2
NTICKS=$3
SERIE=${4:-tb/practica.csv}
HEX=${HEX:-sw/trade.hex}
SRC=${SRC:-$(echo rtl/*.v rtl/espino_core/*.v)}
SIM=${SIM:-iverilog}
DEFS=${DEFS:-}
PYTHON=${PYTHON:-python3}
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v

D=build/equiv/$ETIQUETA
mkdir -p "$D"

sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"$HEX\";|" \
    -e "s|SERIE      = \"[^\"]*\";|SERIE      = \"$SERIE\";|" \
    -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $PERIODO_NS;|" \
    -e "s|NTICKS     = [0-9]*;|NTICKS     = $NTICKS;|" \
    -e "s|\"decisiones.csv\"|\"$D/tb.csv\"|" \
    tb/tb_proyecto_4.sv > "$D/tb_p4.sv"

# La copia solo puede diferir del oficial en esas cinco líneas
if [ "$(diff tb/tb_proyecto_4.sv "$D/tb_p4.sv" | grep -c '^>')" -gt 5 ]; then
  echo "FAIL $ETIQUETA: la copia del testbench cambió más de lo esperado"; exit 1
fi

if [ "$SIM" = verilator ]; then
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_proyecto_4 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS $DEFS -O3 --Mdir "$D/obj" -o sim \
    "$CELLS_SIM" $SRC "$D/tb_p4.sv" > "$D/verilator.log" 2>&1
  "$D/obj/sim" > "$D/tb.log"
else
  iverilog -g2012 $DEFS -s tb_proyecto_4 -o "$D/sim" "$CELLS_SIM" $SRC "$D/tb_p4.sv"
  vvp -n "$D/sim" > "$D/tb.log"
fi

$PYTHON ref/trader.py "$SERIE" --nticks "$NTICKS" --periodo-ns "$PERIODO_NS" -o "$D/ref.csv" > "$D/ref.log"

RESUMEN="$ETIQUETA: periodo $PERIODO_NS ns, $NTICKS ticks, $SERIE, $(grep 'Peor caso' "$D/tb.log" | sed 's/  */ /g')"
if ! grep -q "Testbenchs aprobados: 4/4" "$D/tb.log"; then
  echo "FAIL $RESUMEN: el testbench no entrega 4/4"; tail -8 "$D/tb.log"; exit 1
fi
if ! cmp "$D/tb.csv" "$D/ref.csv"; then
  echo "FAIL $RESUMEN: decisiones distintas a la referencia"; exit 1
fi
echo "PASS $RESUMEN, 4/4, $(($(wc -l < "$D/tb.csv") - 1)) filas identicas a ref/trader.py, patrimonio $(tail -1 "$D/tb.csv" | cut -d, -f6)"
