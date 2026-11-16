#!/usr/bin/env bash
# cosim.sh: valida el gemelo digital (ref/gemelo/gemelo.c) contra el RTL.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El RTL se simula con tb/tb_cpi.sv, que escribe una traza con el número de
# ciclo de cada evento (escrituras al banco de registros, accesos al bus,
# llegada de cada precio, byte que sale por MISO) y una fila de mediciones por
# tick. El gemelo escribe los mismos archivos. Deben ser idénticos (cmp).
#
#   A. trade.hex con el timing del testbench oficial.
#   B. trade.hex con otros tiempos de SPI, otro período y otro reset.
#   C. Programas aleatorios (tools/prog_aleatorio.py) con tráfico SPI.
#   D. Testbench oficial (copia parametrizada, 20 000 ticks): decisiones.csv
#      y las líneas del resumen.
#   E. Mediciones por tick de los 20 000 ticks, con el atajo del sondeo.
#   F. El gemelo con y sin el atajo del sondeo da lo mismo.
#   G. Control negativo: si se cambia cómo se resuelve la coincidencia entre
#      SCLK y el reloj, la traza debe ser distinta.
#
# Uso, desde la raíz: tools/cosim.sh
# Variables: SEMILLAS (por defecto "1 2 3 4"), TICKS_ALEATORIO (150),
#            SIM_ALEATORIO (iverilog o verilator),
#            VARIANTE (base, por defecto, o segmentado: el pipeline de 3
#            etapas contra el gemelo con --pipeline).
set -euo pipefail

SEMILLAS=${SEMILLAS:-"1 2 3 4"}
TICKS_ALEATORIO=${TICKS_ALEATORIO:-150}
SIM_ALEATORIO=${SIM_ALEATORIO:-iverilog}
PYTHON=${PYTHON:-python3}
SRC=$(ls rtl/*.v rtl/espino_core/*.v | grep -v '^rtl/00_')
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
SERIE=tb/practica.csv
G=build/gemelo
VARIANTE=${VARIANTE:-base}
case "$VARIANTE" in
  base)       DEFS="";                    GEM_OPTS="";           D=build/cosim ;;
  segmentado) DEFS="-DESPINO_SEGMENTADO"; GEM_OPTS="--pipeline"; D=build/cosim_segmentado ;;
  *) echo "VARIANTE debe ser base o segmentado"; exit 1 ;;
esac
export DEFS
echo "== Variante del core: $VARIANTE =="
mkdir -p "$D"
[ -x "$G" ] || { echo "falta $G: correr make gemelo"; exit 1; }

# rtl ETIQUETA SIM PROGRAMA NTICKS [defines extra...]: deja $D/ETIQUETA_rtl_{traza.txt,ticks.csv}
rtl() {
  local et=$1 sim=$2 hex=$3 nt=$4; shift 4
  local defs=("-DPROGRAMA=\"$hex\"" "-DSERIE=\"$SERIE\"" "-DNTICKS=$nt" "-DTICKS_CSV=\"$D/${et}_rtl_ticks.csv\"")
  [ "${SIN_TRAZA:-0}" = 1 ] || defs+=("-DTRAZA=\"$D/${et}_rtl_traza.txt\"")
  if [ "$sim" = verilator ]; then
    verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_cpi -O3 $DEFS "${defs[@]}" "$@" \
      --Mdir "$D/${et}_obj" -o sim "$CELLS_SIM" $SRC tb/tb_cpi.sv > "$D/${et}_verilator.log" 2>&1
    "$D/${et}_obj/sim" > "$D/${et}_rtl.log"
  else
    iverilog -g2012 -s tb_cpi $DEFS "${defs[@]}" "$@" -o "$D/${et}_sim" "$CELLS_SIM" $SRC tb/tb_cpi.sv
    vvp -n "$D/${et}_sim" > "$D/${et}_rtl.log"
  fi
}

# comparar ETIQUETA: traza y ticks del RTL contra los del gemelo
comparar() {
  local et=$1
  cmp "$D/${et}_rtl_traza.txt" "$D/${et}_gem_traza.txt" || { echo "FAIL $et: traza distinta"; exit 1; }
  cmp "$D/${et}_rtl_ticks.csv" "$D/${et}_gem_ticks.csv" || { echo "FAIL $et: mediciones por tick distintas"; exit 1; }
  echo "PASS $et: $(wc -l < "$D/${et}_rtl_traza.txt") eventos y $(($(wc -l < "$D/${et}_rtl_ticks.csv") - 1)) ticks identicos"
}

gem() {   # gem ETIQUETA HEX NTICKS [opciones...]
  local et=$1 hex=$2 nt=$3; shift 3
  "$G" $GEM_OPTS --hex "$hex" --serie "$SERIE" --nticks "$nt" --traza "$D/${et}_gem_traza.txt" \
       --ticks "$D/${et}_gem_ticks.csv" --callado "$@"
}

echo "== A y B: trade.hex, traza ciclo a ciclo =="
rtl A iverilog sw/trade.hex 300 &
rtl B1 iverilog sw/trade.hex 100 -DPERIODO_NS=100010 -DINICIO_NS=3999 -DCS_SETUP_NS=2010 -DSCLK_MEDIO_NS=1000 -DCS_HOLD_NS=990 &
rtl B2 iverilog sw/trade.hex 60 -DPERIODO_NS=400000 -DSCLK_MEDIO_NS=5000 -DPOR_BITS=6 &
rtl B3 iverilog sw/trade.hex 100 -DPERIODO_NS=30000 -DINICIO_NS=200007 -DCS_SETUP_NS=130 -DSCLK_MEDIO_NS=490 -DCS_HOLD_NS=70 &
wait
gem A sw/trade.hex 300
gem B1 sw/trade.hex 100 --periodo-ns 100010 --inicio-ns 3999 --cs-setup-ns 2010 --sclk-medio-ns 1000 --cs-hold-ns 990
gem B2 sw/trade.hex 60 --periodo-ns 400000 --sclk-medio-ns 5000 --por-bits 6
gem B3 sw/trade.hex 100 --periodo-ns 30000 --inicio-ns 200007 --cs-setup-ns 130 --sclk-medio-ns 490 --cs-hold-ns 70
for et in A B1 B2 B3; do comparar $et; done

echo "== C: programas aleatorios =="
for s in $SEMILLAS; do
  $PYTHON tools/prog_aleatorio.py "$s" -o "$D/prog_$s.s"
  $PYTHON tools/pochoasm.py --allow-shifts "$D/prog_$s.s" -o "$D/prog_$s.hex" > /dev/null
  rtl "C$s" "$SIM_ALEATORIO" "$D/prog_$s.hex" "$TICKS_ALEATORIO" &
done
wait
total=0
for s in $SEMILLAS; do
  gem "C$s" "$D/prog_$s.hex" "$TICKS_ALEATORIO"
  comparar "C$s"
  total=$((total + $(grep -c ' R \| W ' "$D/C${s}_rtl_traza.txt")))
  rm -f "$D/C${s}_rtl_traza.txt" "$D/C${s}_gem_traza.txt"
done
echo "     programas aleatorios: $total escrituras de registro y de memoria comparadas"

echo "== D: testbench oficial, 20 000 ticks =="
SIM=verilator tools/equiv.sh cosim_r3_$VARIANTE 100000 20000 > "$D/D_equiv.log"
"$G" $GEM_OPTS --csv "$D/D_gem.csv" > "$D/D_gem.log" || true
cmp build/equiv/cosim_r3_$VARIANTE/tb.csv "$D/D_gem.csv" || { echo "FAIL D: decisiones.csv distinto"; exit 1; }
diff <(grep -v -e '^- ' -e 'finish' build/equiv/cosim_r3_$VARIANTE/tb.log) <(grep -v '^Gemelo' "$D/D_gem.log") \
  || { echo "FAIL D: resumen distinto"; exit 1; }
echo "PASS D: decisiones.csv (20 000 filas) y resumen identicos al testbench: $(grep 'Peor caso' "$D/D_gem.log")"

echo "== E: mediciones por tick, 20 000 ticks =="
SIN_TRAZA=1 rtl E verilator sw/trade.hex 20000
"$G" $GEM_OPTS --ticks "$D/E_gem_ticks.csv" --callado
cmp "$D/E_rtl_ticks.csv" "$D/E_gem_ticks.csv" || { echo "FAIL E: mediciones por tick distintas"; exit 1; }
echo "PASS E: $(($(wc -l < "$D/E_rtl_ticks.csv") - 1)) ticks con las mismas mediciones (ciclo de llegada, ciclos e IC)"

echo "== F: atajo del sondeo =="
for r in "100000 20000" "1000000 20000" "10000000 2000"; do
  set -- $r
  "$G" $GEM_OPTS --periodo-ns "$1" --nticks "$2" --csv "$D/F_con.csv" --ticks "$D/F_con_ticks.csv" > "$D/F_con.log"
  "$G" $GEM_OPTS --periodo-ns "$1" --nticks "$2" --csv "$D/F_sin.csv" --ticks "$D/F_sin_ticks.csv" --sin-atajo > "$D/F_sin.log"
  cmp "$D/F_con.csv" "$D/F_sin.csv" && cmp "$D/F_con_ticks.csv" "$D/F_sin_ticks.csv" \
    && diff <(sed 's/, [0-9]* vueltas.*//' "$D/F_con.log") <(sed 's/, [0-9]* vueltas.*//' "$D/F_sin.log") \
    || { echo "FAIL F: el atajo cambia el resultado (periodo $1)"; exit 1; }
done
echo "PASS F: con y sin atajo dan lo mismo a 0,1 ms, 1 ms y 10 ms (decisiones, mediciones, IC y ciclos totales)"

echo "== G: control negativo =="
"$G" $GEM_OPTS --nticks 300 --borde 0 --traza "$D/G_gem_traza.txt" --callado
if cmp -s "$D/A_rtl_traza.txt" "$D/G_gem_traza.txt"; then
  echo "FAIL G: la comparacion no detecta un cambio de un ciclo en el esclavo SPI"; exit 1
fi
echo "PASS G: con --borde 0 la traza difiere de la del RTL en $(cmp -l "$D/A_rtl_traza.txt" "$D/G_gem_traza.txt" 2>/dev/null | wc -l) bytes"
echo "PASS cosim ($VARIANTE): el gemelo coincide con el RTL"
