#!/usr/bin/env bash
# equiv_rtl.sh: el RTL de la edición ASIC contra el testbench oficial y la
# referencia en Python.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Hace lo mismo que tools/equiv.sh, pero con las fuentes del macro ASIC y
# escribiendo en factibilidad/g_asic/build/. Corre una copia parametrizada del
# testbench oficial (solo cambian PERIODO_NS, NTICKS y el archivo de salida)
# sobre asic_top, a través del envoltorio de simulación tb/pochoco_soc_sim.v,
# y exige 4/4 y un decisiones.csv idéntico byte a byte al de ref/trader.py.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/g_asic/scripts/equiv_rtl.sh VARIANTE PERIODO_NS NTICKS [SIM]
#     VARIANTE  base o seg
#     SIM       iverilog (por defecto) o verilator
set -euo pipefail
source factibilidad/g_asic/scripts/fuentes.sh

VAR=$1
PERIODO_NS=$2
NTICKS=$3
SIM=${4:-iverilog}
case $VAR in
  base) DEFS="" ;;
  seg)  DEFS="-DASIC_SEGMENTADO" ;;
  *) echo "variante desconocida: $VAR (base o seg)"; exit 1 ;;
esac
D=$G/build/equiv/${VAR}_${SIM}_${PERIODO_NS}_${NTICKS}
mkdir -p "$D"
generar_rom

sed -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $PERIODO_NS;|" \
    -e "s|NTICKS     = [0-9]*;|NTICKS     = $NTICKS;|" \
    -e "s|\"decisiones.csv\"|\"$D/tb.csv\"|" \
    tb/tb_proyecto_4.sv > "$D/tb_p4.sv"
if [ "$(diff tb/tb_proyecto_4.sv "$D/tb_p4.sv" | grep -c '^>')" -gt 3 ]; then
  echo "FAIL: la copia del testbench cambió más de lo esperado"; exit 1
fi

if [ "$SIM" = verilator ]; then
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_proyecto_4 \
    $DEFS -O3 --Mdir "$D/obj" -o sim $FUENTES $G/tb/pochoco_soc_sim.v "$D/tb_p4.sv" > "$D/verilator.log" 2>&1
  "$D/obj/sim" > "$D/tb.log"
else
  iverilog -g2012 $DEFS -s tb_proyecto_4 -o "$D/sim" $FUENTES $G/tb/pochoco_soc_sim.v "$D/tb_p4.sv"
  vvp -n "$D/sim" > "$D/tb.log"
fi

python3 ref/trader.py tb/practica.csv --nticks "$NTICKS" --periodo-ns "$PERIODO_NS" -o "$D/ref.csv" > "$D/ref.log"

RESUMEN="asic $VAR ($SIM): periodo $PERIODO_NS ns, $NTICKS ticks, $(grep 'Peor caso' "$D/tb.log" | sed 's/  */ /g')"
if ! grep -q "Testbenchs aprobados: 4/4" "$D/tb.log"; then
  echo "FAIL $RESUMEN: el testbench no entrega 4/4"; tail -8 "$D/tb.log"; exit 1
fi
if ! cmp "$D/tb.csv" "$D/ref.csv"; then
  echo "FAIL $RESUMEN: decisiones distintas a la referencia"; exit 1
fi
echo "PASS $RESUMEN, 4/4, $(($(wc -l < "$D/tb.csv") - 1)) filas identicas a ref/trader.py, patrimonio $(tail -1 "$D/tb.csv" | cut -d, -f6)"
