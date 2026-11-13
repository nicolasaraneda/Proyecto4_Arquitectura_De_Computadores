#!/usr/bin/env bash
# sim_bitstream.sh: comprueba que el bitstream decide igual que la referencia.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# 1. tools/chip_vlog.py (icebox_vlog) convierte el .asc (salida del place and route, lo mismo que
#    icepack empaqueta en el .bin) en un módulo Verilog.
# 2. tb/tb_bitstream.sv lo simula por los pines, con la maestra del testbench.
# 3. ref/market.py rehace la contabilidad con los bytes leídos por la maestra.
# 4. El resultado debe ser idéntico al decisiones.csv de ref/trader.py.
#
# Uso, desde la raíz: tools/sim_bitstream.sh [ASC] [NTICKS] [PERIODO_NS]
set -euo pipefail

ASC=${1:-build/pochoco_soc.asc}
NTICKS=${2:-2000}
PERIODO_NS=${3:-100000}
SERIE=${SERIE:-tb/practica.csv}
PYTHON=${PYTHON:-python3}
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
D=build/bitstream
mkdir -p "$D"

$PYTHON tools/chip_vlog.py "$ASC" goboard.pcf -o "$D/chip.v"
iverilog -g2012 -s tb_bitstream -DNTICKS="$NTICKS" -DPERIODO_NS="$PERIODO_NS" \
  "-DSERIE=\"$SERIE\"" "-DSALIDA=\"$D/bytes.csv\"" -o "$D/sim" "$CELLS_SIM" "$D/chip.v" tb/tb_bitstream.sv
vvp -n "$D/sim" > "$D/tb.log"
grep -q "Bits de MISO con X: 0" "$D/tb.log" || { echo "FAIL: MISO con X"; cat "$D/tb.log"; exit 1; }

$PYTHON ref/market.py contabilizar "$D/bytes.csv" -o "$D/bitstream.csv" > /dev/null
$PYTHON ref/trader.py "$SERIE" --nticks "$NTICKS" --periodo-ns "$PERIODO_NS" -o "$D/ref.csv" > /dev/null
if ! cmp "$D/bitstream.csv" "$D/ref.csv"; then
  echo "FAIL: el bitstream no decide igual que la referencia"; exit 1
fi
echo "PASS bitstream $ASC: $NTICKS ticks a $PERIODO_NS ns identicos a ref/trader.py, patrimonio $(tail -1 "$D/bitstream.csv" | cut -d, -f6)"
