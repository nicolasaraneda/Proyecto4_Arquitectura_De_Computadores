#!/usr/bin/env bash
# cotas_rtl.sh: confirma con el RTL los ciclos por tick que tools/p7/cotas.py toma del gemelo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   1. R0 y el segmentado: tb/tb_cpi.sv con Verilator, sw/trade.hex y la serie Meta a 0,1 ms
#      (20 000 ticks). La fila por tick (TICKS_CSV) tiene que ser idéntica byte a byte a la
#      del gemelo (--ticks) con la misma serie.
#   2. R2: la medición del RTL de docs/mediciones/fondo/r2/ticks.txt (tools/fondo/ticks.sh)
#      tiene que ser del programa y la tabla actuales (sha256 en su encabezado) y dar la
#      misma respuesta y el mismo tick completo que el gemelo. No se repite: lo que mide no
#      cambió (lo comprueba el sha256).
#
# Deja docs/mediciones/p7/cotas/rtl.txt. Uso: tools/p7/cotas_rtl.sh (make p7-cotas-rtl). Unos 2 minutos.
set -euo pipefail
source "$(dirname "$0")/comun.sh"
B=build/p7/cotas
M=docs/mediciones/p7/cotas
mkdir -p "$B" "$M"
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
SRC=$(for f in rtl/*.v rtl/espino_core/*.v; do case "$f" in rtl/00_*) ;; *) printf '%s ' "$f" ;; esac; done)
make -s gemelo > /dev/null
S=data/practica_meta.csv

tb_cpi() {   # tb_cpi ETIQUETA "DEFS"
  local o=$B/rtl_$1
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_cpi -O3 $2 \
    "-DPROGRAMA=\"sw/trade.hex\"" "-DSERIE=\"$S\"" -DNTICKS=20000 -DPERIODO_NS=100000 \
    "-DTICKS_CSV=\"${o}_ticks.csv\"" --Mdir "${o}_obj" -o sim \
    "$CELLS_SIM" $SRC tb/tb_cpi.sv > "${o}_verilator.log" 2>&1
  "${o}_obj/sim" | grep -v -e '^- ' > "${o}.log"
}
tb_cpi r0 "" &
tb_cpi seg "-DESPINO_SEGMENTADO" &
wait
build/gemelo --serie $S --periodo-ns 100000 --nticks 20000 --ticks "$B/gemelo_r0_ticks.csv" --callado
build/gemelo --pipeline --serie $S --periodo-ns 100000 --nticks 20000 --ticks "$B/gemelo_seg_ticks.csv" --callado

gem_r2=$(build/gemelo --barrel --xd 3 --tabla sw/fondo_tabla.hex --hex $B/sw/fondo.hex --serie $S --periodo-ns 100000 --nticks 20000 | \
  sed -n 's/^Gemelo: .*Respuesta: \([0-9.]*\) ciclos e IC [0-9.]* en promedio, peor caso \([0-9]*\) ciclos e IC [0-9]*\. Tick completo: \([0-9.]*\) ciclos e IC [0-9.]* en promedio, peor caso \([0-9]*\) ciclos.*/\1 \2 \3 \4/p')

{
  echo "Confirmacion con el RTL de los ciclos por tick del gemelo (regla de cotas, banda 40)"
  echo "Generado por tools/p7/cotas_rtl.sh (make p7-cotas-rtl). No editar a mano."
  echo
  versiones
  echo
  echo "1. tb/tb_cpi.sv con Verilator contra build/gemelo, serie Meta a 0,1 ms (sw/trade.hex)"
  for v in r0 seg; do
    if cmp -s "$B/rtl_${v}_ticks.csv" "$B/gemelo_${v}_ticks.csv"; then
      echo "PASS $v: $(($(wc -l < "$B/rtl_${v}_ticks.csv") - 1)) filas por tick identicas byte a byte (ciclo del precio, respuesta, tick completo e IC)"
    else
      echo "FAIL $v: la fila por tick del RTL difiere de la del gemelo"
    fi
    grep -E "respuesta, (promedio|peor)|tick completo, (promedio|peor)" "$B/rtl_$v.log" | sed "s/^/    RTL $v: /"
  done
  echo
  echo "2. R2: medicion del RTL (tools/fondo/ticks.sh) contra el gemelo, ronda 3"
  echo "   gemelo: respuesta promedio y peor, tick completo promedio y peor: $gem_r2"
  f=docs/mediciones/fondo/r2/ticks.txt
  p=$(sha256sum sw/fondo.s | cut -c1-16); t=$(sha256sum sw/fondo_tabla.hex | cut -c1-16)
  if ! grep -q "sw/fondo.s (sha256 $p" "$f" || ! grep -q "sw/fondo_tabla.hex (sha256 $t" "$f"; then
    echo "FAIL r2: $f no es del programa o de la tabla actuales"
  else
    rtl=$(awk '/=== Ronda 3/ {r=1} /=== Ronda 2/ {r=0}
         r && /DECISION \(respuesta\)/ {print $(NF-5), $(NF-4)}
         r && /vuelve a sondear/ {print $(NF-5), $(NF-4)}' "$f" | tr '\n' ' ')
    # El RTL da promedios de 2 decimales (186.99) y el gemelo los redondea distinto: se compara a 1 decimal
    redondea() { echo "$1" | awk '{printf "%.1f %d %.1f %d", $1, $2, $3, $4}'; }
    if [ "$(redondea "$rtl")" = "$(redondea "$gem_r2")" ]; then
      echo "PASS r2: RTL $rtl, igual al gemelo a un decimal ($f, mismo sha256 de programa y tabla)"
    else
      echo "FAIL r2: RTL $rtl distinto del gemelo $gem_r2"
    fi
  fi
} > $M/rtl.txt
cat $M/rtl.txt
! grep -q FAIL $M/rtl.txt
