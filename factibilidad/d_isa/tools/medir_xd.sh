#!/usr/bin/env bash
# medir_xd.sh: trade.s con las instrucciones nuevas, medido y comparado con la referencia.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Para cada versión de trade.s de sw/ (solo software, srak, emad, ema y
# devk + emad) y para los dos cores (Espino base y segmentado) de la copia
# core/:
#   1. Pasa las instrucciones nuevas a .word (tools/xd_word.py) y ensambla con
#      el ensamblador del repositorio, sin modificarlo.
#   2. Equivalencia: corre una copia parametrizada del testbench oficial (solo
#      cambian PROGRAMA, PERIODO_NS, NTICKS y el nombre del archivo de salida),
#      exige 4/4 y que decisiones.csv sea idéntico byte a byte al de
#      ref/trader.py. Es el mismo procedimiento de tools/equiv.sh, con las
#      salidas dentro de esta carpeta.
#   3. Mediciones por tick con tb/tb_cpi.sv del repositorio (sin modificar):
#      IC y ciclos de la respuesta y del tick completo, promedio y peor caso.
# Todo al período de la ronda 3 (0,1 ms), con Verilator.
#
# Uso, desde factibilidad/d_isa:
#   tools/medir_xd.sh > mediciones/ticks_xd.txt
# Variables: NTICKS (20000). Deja un resumen para tools/amdahl.py en
# build/med/resumen.tsv.
set -euo pipefail
cd "$(dirname "$0")/.."
AQUI=factibilidad/d_isa
NTICKS=${NTICKS:-20000}
PERIODO=100000
cd ../..                                   # raíz: el testbench usa rutas relativas a ella
B=$AQUI/build/med
mkdir -p "$B" $AQUI/build/sw
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
SRC="$(echo $AQUI/core/*.v $AQUI/core/espino_core/*.v $AQUI/rtl/xd_*.v)"
VFLAGS="--binary --timing -Wno-fatal -Wno-lint -Wno-style -O3 --build-jobs 2"

python3 ref/trader.py tb/practica.csv --nticks "$NTICKS" --periodo-ns "$PERIODO" -o "$B/ref.csv" > "$B/ref.log"

# El testbench oficial con cinco líneas cambiadas, igual que en tools/equiv.sh
tb_oficial() {   # tb_oficial HEX SALIDA.sv SALIDA.csv
  sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"$1\";|" \
      -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $PERIODO;|" \
      -e "s|NTICKS     = [0-9]*;|NTICKS     = $NTICKS;|" \
      -e "s|\"decisiones.csv\"|\"$3\"|" \
      tb/tb_proyecto_4.sv > "$2"
  if [ "$(diff tb/tb_proyecto_4.sv "$2" | grep -c '^>')" -gt 4 ]; then
    echo "FAIL: la copia del testbench cambió más de lo esperado"; exit 1
  fi
}

: > "$B/resumen.tsv"
FALLAS=0
echo "trade.s con la extensión de la ISA: equivalencia y mediciones por tick"
echo "Generado por factibilidad/d_isa/tools/medir_xd.sh (make medir-ticks). No editar a mano."
echo
echo "Serie tb/practica.csv, $NTICKS ticks, período de la ronda 3 ($PERIODO ns, presupuesto 2262 ciclos). Verilator."
echo "RTL: la copia factibilidad/d_isa/core con las definiciones de cada fila. Reloj de 25 MHz."
echo "Equivalencia: copia parametrizada del testbench oficial, 4/4 y decisiones.csv idéntico a ref/trader.py."
echo "Ciclos e IC: tb/tb_cpi.sv. 'resp' es la respuesta (byte_done a DECISION) y 'tick' el tick completo"
echo "(hasta que el programa vuelve a sondear STATUS). Incluyen la espera del sondeo, que depende de la fase."
echo
printf "%-11s %-12s %-26s %-9s %7s %7s %7s %7s %7s %7s %7s %7s  %s\n" core programa definiciones equiv \
  "IC_resp" "resp" "resp_pc" "IC_tick" "tick_mn" "tick" "tick_pc" "CPI" "modelo de costo"

medir() {   # medir CORE PROGRAMA "definiciones"
  local core=$1 prog=$2 defs=$3 cdef="" o
  [ "$core" = segmentado ] && cdef="-DESPINO_SEGMENTADO"
  o="$B/${core}_$prog"
  python3 $AQUI/tools/xd_word.py --pre "$AQUI/sw/$prog.s" -o "$AQUI/build/sw/$prog.s" > /dev/null
  python3 tools/pochoasm.py "$AQUI/build/sw/$prog.s" -o "$AQUI/build/sw/$prog.hex" > /dev/null

  # Equivalencia con la referencia, por el testbench oficial
  tb_oficial "$AQUI/build/sw/$prog.hex" "${o}_tb_p4.sv" "${o}_tb.csv"
  local equiv=FAIL
  if verilator $VFLAGS --top-module tb_proyecto_4 -DNO_ICE40_DEFAULT_ASSIGNMENTS $cdef $defs \
       --Mdir "${o}_obj_eq" -o sim "$CELLS_SIM" $SRC "${o}_tb_p4.sv" > "${o}_eq_verilator.log" 2>&1 \
     && "${o}_obj_eq/sim" > "${o}_tb.log" 2>&1 \
     && grep -q "Testbenchs aprobados: 4/4" "${o}_tb.log" && cmp -s "${o}_tb.csv" "$B/ref.csv"; then
    equiv="4/4,igual"
  else
    FALLAS=$((FALLAS + 1))
  fi

  # Mediciones por tick
  verilator $VFLAGS --top-module tb_cpi $cdef $defs \
    "-DPROGRAMA=\"$AQUI/build/sw/$prog.hex\"" "-DSERIE=\"tb/practica.csv\"" -DNTICKS="$NTICKS" -DPERIODO_NS="$PERIODO" \
    "-DTICKS_CSV=\"${o}_ticks.csv\"" --Mdir "${o}_obj_cpi" -o sim \
    "$CELLS_SIM" $SRC tb/tb_cpi.sv > "${o}_cpi_verilator.log" 2>&1
  "${o}_obj_cpi/sim" | grep -v -e '^- ' > "${o}_cpi.log"
  local ic_r c_r c_rp ic_t c_t c_tp cpi modelo c_tmin
  ic_r=$(awk '/respuesta, promedio/ {print $4}' "${o}_cpi.log")
  c_r=$(awk '/respuesta, promedio/ {print $6}' "${o}_cpi.log")
  c_rp=$(awk '/respuesta, peor caso/ {print $7}' "${o}_cpi.log")
  ic_t=$(awk '/tick completo, promedio/ {print $5}' "${o}_cpi.log")
  c_t=$(awk '/tick completo, promedio/ {print $7}' "${o}_cpi.log")
  c_tp=$(awk '/tick completo, peor caso/ {print $8}' "${o}_cpi.log")
  cpi=$(awk '/tick completo, promedio/ {print $9}' "${o}_cpi.log")
  # mínimo del tick completo en régimen (sin el primer precio): la espera más corta
  c_tmin=$(awk -F, 'NR > 3 && $7 > 0 { if (m == "" || $7 < m) m = $7 } END { print m }' "${o}_ticks.csv")
  modelo=$(grep -c "^PASS el modelo de costo" "${o}_cpi.log" || true)
  [ "$modelo" = 1 ] && modelo="coincide" || { modelo="NO COINCIDE"; FALLAS=$((FALLAS + 1)); }
  printf "%-11s %-12s %-26s %-9s %7s %7s %7s %7s %7s %7s %7s %7s  %s\n" "$core" "$prog" "${defs:--}" "$equiv" \
    "$ic_r" "$c_r" "$c_rp" "$ic_t" "$c_tmin" "$c_t" "$c_tp" "$cpi" "$modelo"
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$core" "$prog" "$equiv" "$ic_r" "$c_r" "$c_rp" "$ic_t" "$c_tmin" "$c_t" "$c_tp" >> "$B/resumen.tsv"
}

for core in base segmentado; do
  medir $core trade_sw    ""
  medir $core trade_srak  "-DXD_SRAK=0"
  medir $core trade_emad  "-DXD_EMAD=0"
  medir $core trade_ema   "-DXD_EMA=0 -DXD_EMAALU"
  medir $core trade_media "-DXD_EMAD=0 -DXD_DEVK=0"
  echo
done

echo "Columnas: IC_resp y resp, instrucciones y ciclos promedio de la respuesta; resp_pc, peor caso de la respuesta;"
echo "IC_tick, instrucciones promedio del tick completo; tick_mn, tick y tick_pc, ciclos mínimo, promedio y peor caso"
echo "del tick completo; CPI del tick completo. 'modelo de costo' es la comprobación de tb_cpi.sv:"
echo "ciclos = IC + loads + saltos tomados en el segmentado, y 2 IC + loads + saltos tomados en el base."
echo "Las instrucciones nuevas cuestan lo mismo que una de la ALU: 1 ciclo en el segmentado y 2 en el base."
if [ "$FALLAS" != 0 ]; then echo "FAIL: $FALLAS comprobaciones con error"; exit 1; fi
echo "PASS: las cinco versiones entregan las mismas decisiones que ref/trader.py en los dos cores"
