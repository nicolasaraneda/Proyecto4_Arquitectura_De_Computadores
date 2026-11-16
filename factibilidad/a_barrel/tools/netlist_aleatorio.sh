#!/usr/bin/env bash
# netlist_aleatorio.sh: la netlist sintetizada del SoC barrel contra su RTL,
# ciclo a ciclo en los pines, con programas aleatorios de cuatro hilos y
# tráfico SPI.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# tools/netlist.sh corre en la netlist dos programas que se revisan a sí
# mismos. Aquí se corren programas aleatorios (tools/prog_hilos.py, con más
# accesos al SPI y a los periféricos que en tools/verif.sh, para que salga más
# por los pines) y no hay valor esperado: la referencia es el RTL. tb/tb_pines.sv anota con su número
# de ciclo cada cambio de LEDs y display y cada byte que la maestra SPI recibe,
# y las trazas del RTL y de la netlist (Yosys synth_ice40, modelos de
# cells_sim.v) tienen que ser idénticas byte a byte.
#
# Comprueba que la síntesis conserva el comportamiento con los cuatro
# contextos del banco en uso, memoria compartida entre hilos y los cuatro
# hilos leyendo y escribiendo el esclavo SPI mientras llegan precios.
#
# Uso: factibilidad/a_barrel/tools/netlist_aleatorio.sh [SEMILLAS]
#      (o make netlist-aleatorio). Por defecto 3 semillas en cada modo.
# Resultado en factibilidad/a_barrel/mediciones/netlist_aleatorio.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-3}
JOBS=${JOBS:-4}
CICLOS=${CICLOS:-34000}
O=$B/netlist_aleatorio
mkdir -p "$O"

# caso MODO SEMILLA: sintetiza el SoC con el programa y simula RTL y netlist
caso() {
  local modo=$1 s=$2 n=$O/$1_s$2
  $PYTHON $A/tools/prog_hilos.py "$s" --modo "$modo" --peso-spi 12 --peso-periph 10 -o "$n.s" \
    && $PYTHON tools/pochoasm.py --allow-shifts "$n.s" -o "$n.hex" > /dev/null || return 0
  yosys -q -l "$n.yosys.log" -p "read_verilog $BARREL_SRC; chparam -set MemFile \"$n.hex\" pochoco_soc; \
    synth_ice40 -top pochoco_soc; write_verilog -noattr $n.v" || return 0
  iverilog -g2012 -s tb_pines -DNETLIST -DCICLOS="$CICLOS" "-DTRAZA=\"$n.netlist.txt\"" -o "$n.netlist.vvp" \
    "$CELLS_SIM" "$n.v" $A/tb/tb_pines.sv && vvp -n "$n.netlist.vvp" > "$n.netlist.log" 2>&1
  iverilog -g2012 -s tb_pines "-DPROGRAMA=\"$n.hex\"" -DCICLOS="$CICLOS" "-DTRAZA=\"$n.rtl.txt\"" -o "$n.rtl.vvp" \
    "$CELLS_SIM" $BARREL_SRC $A/tb/tb_pines.sv && vvp -n "$n.rtl.vvp" > "$n.rtl.log" 2>&1
  return 0
}
export -f caso
export O A PYTHON CICLOS CELLS_SIM BARREL_SRC

: > "$O/casos.txt"
for s in $(seq 1 "$SEMILLAS"); do echo "separado $s" >> "$O/casos.txt"; echo "compartido $s" >> "$O/casos.txt"; done
rm -f "$O"/*.rtl.txt "$O"/*.netlist.txt
xargs -P "$JOBS" -L 1 bash -c 'caso "$0" "$1"' < "$O/casos.txt"

{
echo "Netlist sintetizada del SoC barrel contra su RTL: traza de los pines con programas aleatorios de cuatro hilos"
echo "Generado por factibilidad/a_barrel/tools/netlist_aleatorio.sh (make netlist-aleatorio). No editar a mano."
echo
versiones
echo
echo "Ciclos por corrida: $CICLOS (los primeros 4095 son el reset de encendido). Simulador: Icarus."
echo
fallas=0; lineas=0
while read -r modo s; do
  n=$O/${modo}_s$s
  if [ ! -s "$n.rtl.txt" ] || [ ! -s "$n.netlist.txt" ]; then
    echo "FAIL $modo, semilla $s: falta una de las trazas"; fallas=$((fallas + 1)); continue
  fi
  x=$(sed -nE 's/.* ([0-9]+) ciclos con X en los pines/\1/p' "$n.rtl.log" "$n.netlist.log" | paste -sd+ | bc)
  if cmp -s "$n.rtl.txt" "$n.netlist.txt" && [ "$x" = 0 ]; then
    lineas=$((lineas + $(wc -l < "$n.rtl.txt")))
    echo "PASS $modo, semilla $s: trazas identicas, $(grep -c ' spi ' "$n.rtl.txt") bytes recibidos por SPI ($(grep ' spi ' "$n.rtl.txt" | sed 's/.*rx=//' | sort -u | wc -l) valores distintos) y $(grep -c ' io ' "$n.rtl.txt") cambios de LEDs o display, sin X en los pines"
  else
    fallas=$((fallas + 1))
    echo "FAIL $modo, semilla $s: $(diff "$n.rtl.txt" "$n.netlist.txt" | sed -n 2,3p | tr '\n' ' ') (ciclos con X: $x)"
  fi
done < "$O/casos.txt"
echo
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, $lineas eventos de pines identicos entre el RTL y la netlist"
else echo "RESULTADO: FAIL ($fallas casos)"; fi
} | tee "$M/netlist_aleatorio.txt"

grep -q "^RESULTADO: PASS" "$M/netlist_aleatorio.txt"
