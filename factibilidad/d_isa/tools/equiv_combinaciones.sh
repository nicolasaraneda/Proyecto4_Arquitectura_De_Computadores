#!/usr/bin/env bash
# equiv_combinaciones.sh: el testbench oficial con las combinaciones que caben en la FPGA.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# tools/medir_xd.sh mide cada versión de trade.s con el hardware mínimo que
# necesita. Este script corre las combinaciones de instrucciones que son
# candidatas a un bitstream (las de la tabla del README), que tienen más
# hardware que el que el programa usa: comprueba que con ese hardware agregado
# el programa sigue entregando 4/4 en una copia parametrizada del testbench
# oficial y decisiones.csv idéntico byte a byte al de ref/trader.py. Es el
# mismo procedimiento de tools/medir_xd.sh y de tools/equiv.sh del
# repositorio. Serie de práctica, período de la ronda 3, Verilator.
#
# Uso, desde factibilidad/d_isa:
#   tools/equiv_combinaciones.sh > mediciones/equiv_combinaciones.txt
# Variables: NTICKS (20000).
set -uo pipefail
cd "$(dirname "$0")/.."
AQUI=factibilidad/d_isa
NTICKS=${NTICKS:-20000}
PERIODO=100000
cd ../..                                   # raíz: el testbench usa rutas relativas a ella
B=$AQUI/build/comb
mkdir -p "$B" $AQUI/build/sw
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
SRC="$(echo $AQUI/core/*.v $AQUI/core/espino_core/*.v $AQUI/rtl/xd_*.v)"
VFLAGS="--binary --timing -Wno-fatal -Wno-lint -Wno-style -O3 --build-jobs 2"

python3 ref/trader.py tb/practica.csv --nticks "$NTICKS" --periodo-ns "$PERIODO" -o "$B/ref.csv" > "$B/ref.log"

FALLAS=0
echo "Las combinaciones que caben, por el testbench oficial"
echo "Generado por factibilidad/d_isa/tools/equiv_combinaciones.sh (make equiv-combinaciones). No editar a mano."
echo
echo "Serie tb/practica.csv, $NTICKS ticks, período de la ronda 3 ($PERIODO ns). Verilator."
echo "Copia parametrizada de tb/tb_proyecto_4.sv (cambian PROGRAMA, PERIODO_NS, NTICKS y el archivo de salida)."
echo "'igual' significa decisiones.csv idéntico byte a byte al de ref/trader.py."
echo
printf "%-11s %-13s %-12s %-10s %8s  %s\n" core combinación programa resultado "peor caso" "definiciones"

correr() {   # correr CORE ETIQUETA PROGRAMA "definiciones"
  local core=$1 etq=$2 prog=$3 defs=$4 cdef="" o res peor
  [ "$core" = segmentado ] && cdef="-DESPINO_SEGMENTADO"
  o="$B/${core}_$etq"
  python3 $AQUI/tools/xd_word.py --pre "$AQUI/sw/$prog.s" -o "$AQUI/build/sw/$prog.s" > /dev/null
  python3 tools/pochoasm.py "$AQUI/build/sw/$prog.s" -o "$AQUI/build/sw/$prog.hex" > /dev/null
  sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"$AQUI/build/sw/$prog.hex\";|" \
      -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $PERIODO;|" \
      -e "s|NTICKS     = [0-9]*;|NTICKS     = $NTICKS;|" \
      -e "s|\"decisiones.csv\"|\"${o}_tb.csv\"|" \
      tb/tb_proyecto_4.sv > "${o}_tb_p4.sv"
  if [ "$(diff tb/tb_proyecto_4.sv "${o}_tb_p4.sv" | grep -c '^>')" -gt 4 ]; then
    echo "FAIL: la copia del testbench cambió más de lo esperado"; exit 1
  fi
  res=FAIL
  if verilator $VFLAGS --top-module tb_proyecto_4 -DNO_ICE40_DEFAULT_ASSIGNMENTS $cdef $defs \
       --Mdir "${o}_obj" -o sim "$CELLS_SIM" $SRC "${o}_tb_p4.sv" > "${o}_verilator.log" 2>&1 \
     && "${o}_obj/sim" > "${o}_tb.log" 2>&1 \
     && grep -q "Testbenchs aprobados: 4/4" "${o}_tb.log" && cmp -s "${o}_tb.csv" "$B/ref.csv"; then
    res="4/4,igual"
  else
    FALLAS=$((FALLAS + 1))
  fi
  # peor caso de la respuesta que informa el propio testbench oficial, en ciclos
  peor=$(grep -iE "peor" "${o}_tb.log" | grep -oE "[0-9]+ ciclos" | head -1 | cut -d' ' -f1)
  printf "%-11s %-13s %-12s %-10s %8s  %s\n" "$core" "$etq" "$prog" "$res" "${peor:--}" "$defs"
}

for core in base segmentado; do
  correr $core media_mul    trade_media "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU"
  correr $core alu_todo     trade_media "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DXD_SIMDALU=12"
  correr $core alu_todo_div trade_media "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DXD_SIMDALU=12 -DXD_DIVSTEP"
  correr $core min_bandas   trade_emad  "-DXD_EMAD=0 -DXD_SIMD=28"
  echo
done

echo "'peor caso' es el de la respuesta (byte_done a DECISION) que informa el testbench oficial, en ciclos."
if [ "$FALLAS" != 0 ]; then echo "FAIL: $FALLAS corridas con error"; exit 1; fi
echo "PASS: las cuatro combinaciones entregan 4/4 y las mismas decisiones que ref/trader.py en los dos cores"
