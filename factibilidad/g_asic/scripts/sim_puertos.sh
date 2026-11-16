#!/usr/bin/env bash
# sim_puertos.sh: el macro ASIC, simulado solo por sus puertos, contra la
# referencia en Python. Sirve para el RTL y para los netlists de una corrida.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/g_asic/scripts/sim_puertos.sh QUE VARIANTE_O_TAG [NTICKS] [PERIODO_NS]
#     QUE   rtl   el RTL de asic_top; el segundo argumento es base o seg
#           sint  el netlist que sale de la síntesis de la corrida TAG
#           pnr   el netlist final de la corrida TAG, después del place and
#                 route (con buffers, árbol de reloj y celdas de relleno)
# Los netlists se simulan con los modelos de celdas del PDK, sin retardos
# (-DFUNCTIONAL): es una comprobación funcional, no de timing.
#
# tb/tb_asic_puertos.sv escribe el byte que la maestra lee en cada tick,
# ref/market.py rehace la contabilidad oficial y el resultado debe ser
# idéntico byte a byte al decisiones.csv de ref/trader.py. El reset se suelta
# antes del primer precio, así que la referencia se corre con --perdidos 0.
#
# Por defecto son 300 ticks con período de 15000 ns: la transacción SPI dura
# 9500 ns y el tick completo del programa menos de 3000, así que alcanza, y la
# simulación del netlist demora pocos minutos.
set -euo pipefail
source factibilidad/g_asic/scripts/fuentes.sh
PDK_ROOT=${PDK_ROOT:-$HOME/.ciel/ciel/gf180mcu/versions/54435919abffb937387ec956209f9cf5fd2dfbee}
SCL=gf180mcu_fd_sc_mcu7t5v0
CELDAS_V="$PDK_ROOT/gf180mcuD/libs.ref/$SCL/verilog/primitives.v $PDK_ROOT/gf180mcuD/libs.ref/$SCL/verilog/$SCL.v"

QUE=$1
ARG=$2
NTICKS=${3:-300}
PERIODO_NS=${4:-15000}
D=$G/build/puertos/${QUE}_${ARG}_${PERIODO_NS}_${NTICKS}
mkdir -p "$D"
DEFS="-DNTICKS=$NTICKS -DPERIODO_NS=$PERIODO_NS -DSALIDA=\"$D/bytes.csv\""

case $QUE in
  rtl)
    generar_rom
    case $ARG in base) P=0 ;; seg) P=2 ;; *) echo "variante desconocida: $ARG"; exit 1 ;; esac
    iverilog -g2012 -s tb_asic_puertos $DEFS -Ptb_asic_puertos.PIPELINE=$P -o "$D/sim" $FUENTES $G/tb/tb_asic_puertos.sv ;;
  sint)
    NL=$(ls $G/runs/$ARG/*-yosys-synthesis/asic_top.nl.v | tail -1)
    iverilog -g2012 -s tb_asic_puertos $DEFS -DNETLIST -DFUNCTIONAL -o "$D/sim" "$NL" $CELDAS_V $G/tb/tb_asic_puertos.sv ;;
  pnr)
    NL=$G/runs/$ARG/final/nl/asic_top.nl.v
    iverilog -g2012 -s tb_asic_puertos $DEFS -DNETLIST -DFUNCTIONAL -o "$D/sim" "$NL" $CELDAS_V $G/tb/tb_asic_puertos.sv ;;
  *) echo "QUE desconocido: $QUE (rtl, sint o pnr)"; exit 1 ;;
esac
INICIO=$(date +%s)
vvp -n "$D/sim" > "$D/tb.log"
SEG=$(( $(date +%s) - INICIO ))
grep -q "Bits de MISO con X: 0" "$D/tb.log" || { echo "FAIL $QUE $ARG: MISO con X"; cat "$D/tb.log"; exit 1; }

python3 ref/market.py contabilizar "$D/bytes.csv" -o "$D/dut.csv" > /dev/null
python3 ref/trader.py tb/practica.csv --nticks "$NTICKS" --perdidos 0 -o "$D/ref.csv" > /dev/null
if ! cmp "$D/dut.csv" "$D/ref.csv"; then
  echo "FAIL $QUE $ARG: no decide igual que la referencia"; exit 1
fi
ORDENES=$(awk -F, 'NR > 1 && $3 != "00" && $3 != p { n++ } { p = $3 } END { print n + 0 }' "$D/bytes.csv")
echo "PASS $QUE $ARG: $NTICKS ticks a $PERIODO_NS ns identicos a ref/trader.py, MISO sin X, patrimonio $(tail -1 "$D/dut.csv" | cut -d, -f6), cambios del byte de decision $ORDENES, simulacion ${SEG} s"
