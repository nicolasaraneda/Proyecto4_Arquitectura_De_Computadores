#!/usr/bin/env bash
# equiv_rtl.sh: el RTL del macro ASIC del barrel con una copia del testbench oficial,
# contra ref/fondo.py. Con NETLIST=archivo corre la netlist (de síntesis o final) en
# vez del RTL, con los modelos de celdas del PDK.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso, desde la raíz: asic/scripts/equiv_rtl.sh XD PERIODO_NS NTICKS [iverilog|verilator]
#   XD 3 (R1: emad y devk) o 7 (agrega mulstep). El programa es sw/fondo.s en los dos.
# La copia del testbench solo cambia el período, el largo y el nombre de decisiones.csv.
# No escribe formas de onda.
set -euo pipefail
source asic/scripts/fuentes.sh
XD=$1; PERIODO_NS=$2; NTICKS=$3; SIM=${4:-iverilog}
D=$A/build/equiv/xd${XD}_${SIM}_${PERIODO_NS}_${NTICKS}${NETLIST:+_netlist}
mkdir -p "$D"
generar_rom
sed -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $PERIODO_NS;|" \
    -e "s|NTICKS     = [0-9]*;|NTICKS     = $NTICKS;|" \
    -e "s|\"decisiones.csv\"|\"$D/tb.csv\"|" \
    tb/tb_proyecto_4.sv > "$D/tb_p4.sv"
if [ "$(diff tb/tb_proyecto_4.sv "$D/tb_p4.sv" | grep -c '^>')" -gt 3 ]; then
  echo "FAIL: la copia del testbench cambió más de lo esperado"; exit 1
fi
if [ -n "${NETLIST:-}" ]; then
  CELDAS=${CELDAS:?con NETLIST hace falta CELDAS con los modelos Verilog de las celdas del PDK}
  SRC="$CELDAS $NETLIST"
else
  SRC="$FUENTES"
fi
if [ "$SIM" = verilator ]; then
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_proyecto_4 -DASIC_XD=$XD \
    -O3 --Mdir "$D/obj" -o sim $SRC $A/tb/pochoco_soc_sim_barrel.v "$D/tb_p4.sv" > "$D/verilator.log" 2>&1
  "$D/obj/sim" > "$D/tb.log"
else
  iverilog -g2012 -DASIC_XD=$XD -s tb_proyecto_4 -o "$D/sim" $SRC $A/tb/pochoco_soc_sim_barrel.v "$D/tb_p4.sv"
  vvp -n "$D/sim" > "$D/tb.log"
fi
python3 ref/fondo.py tb/practica.csv --nticks "$NTICKS" --periodo-ns "$PERIODO_NS" -o "$D/ref.csv" > "$D/ref.log"
RESUMEN="asic barrel xd=$XD ($SIM${NETLIST:+, netlist}): periodo $PERIODO_NS ns, $NTICKS ticks, $(grep 'Peor caso' "$D/tb.log" | sed 's/  */ /g')"
if ! grep -q "Testbenchs aprobados: 4/4" "$D/tb.log"; then
  echo "FAIL $RESUMEN: el testbench no entrega 4/4"; tail -8 "$D/tb.log"; exit 1
fi
if ! cmp "$D/tb.csv" "$D/ref.csv"; then
  echo "FAIL $RESUMEN: decisiones distintas a ref/fondo.py"; exit 1
fi
echo "PASS $RESUMEN, 4/4, $(($(wc -l < "$D/tb.csv") - 1)) filas identicas a ref/fondo.py, patrimonio $(tail -1 "$D/tb.csv" | cut -d, -f6)"
