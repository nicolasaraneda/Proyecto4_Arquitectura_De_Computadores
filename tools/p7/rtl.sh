#!/usr/bin/env bash
# rtl.sh: confirma con el RTL los ciclos por tick que la tabla de co-diseño
# toma del gemelo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   1. R0 (Espino base) y el segmentado: tb/tb_cpi.sv con Verilator, la serie
#      de práctica completa a 0,1 ms. Su fila por tick (TICKS_CSV) tiene que
#      ser idéntica byte a byte a la del gemelo (--ticks) con la misma serie.
#   2. R1 y R2: la medición por tick del RTL de P5 (tools/fondo/ticks.sh, en
#      docs/mediciones/fondo/r1/ y r2/) tiene que ser del mismo programa y la
#      misma tabla (sha256 en su encabezado) y dar la misma respuesta y el
#      mismo tick completo que el gemelo. No se repite: son 35 minutos de
#      Verilator y lo que mide no cambió (lo comprueba el sha256).
#
# Deja docs/mediciones/p7/rtl.txt. Uso: tools/p7/rtl.sh (make p7-rtl). Unos 3 minutos.
set -euo pipefail
source "$(dirname "$0")/comun.sh"

CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
SRC=$(echo rtl/*.v rtl/espino_core/*.v)
make -s gemelo > /dev/null

tb_cpi() {   # tb_cpi ETIQUETA "DEFS"
  local o=$B/rtl_$1
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_cpi -O3 $2 \
    "-DPROGRAMA=\"sw/trade.hex\"" "-DSERIE=\"tb/practica.csv\"" -DNTICKS=20000 -DPERIODO_NS=100000 \
    "-DTICKS_CSV=\"${o}_ticks.csv\"" --Mdir "${o}_obj" -o sim \
    "$CELLS_SIM" $SRC tb/tb_cpi.sv > "${o}_verilator.log" 2>&1
  "${o}_obj/sim" | grep -v -e '^- ' > "${o}.log"
}
tb_cpi r0 "" &
tb_cpi seg "-DESPINO_SEGMENTADO" &
wait
build/gemelo --periodo-ns 100000 --ticks "$B/gemelo_r0_ticks.csv" > /dev/null
build/gemelo --pipeline --periodo-ns 100000 --ticks "$B/gemelo_seg_ticks.csv" > /dev/null

resp_fondo() {   # resp_fondo ARCHIVO: promedio y peor de la respuesta y del tick completo, ronda 3
  awk '/=== Ronda 3/ {r=1} /=== Ronda 2/ {r=0}
       r && /DECISION \(respuesta\), todos/ {print $(NF-5), $(NF-4)}
       r && /vuelve a sondear/ {print $(NF-5), $(NF-4)}' "$1" | tr '\n' ' '
}
gem_fondo=$(awk '/^r1 r3 \| Gemelo: [0-9]+ ticks/ {
  match($0, /Respuesta: [0-9.]+/); a=substr($0, RSTART+11, RLENGTH-11)
  match($0, /peor caso [0-9]+ ciclos/); b=substr($0, RSTART+10, RLENGTH-17)
  match($0, /Tick completo: [0-9.]+/); c=substr($0, RSTART+15, RLENGTH-15)
  s=substr($0, RSTART); match(s, /peor caso [0-9]+ ciclos/); d=substr(s, RSTART+10, RLENGTH-17)
  print a, b, c, d}' $M/gemelo.txt)

{
  echo "Confirmacion con el RTL de los ciclos por tick del gemelo"
  echo "Generado por tools/p7/rtl.sh (make p7-rtl). No editar a mano."
  echo
  versiones
  echo
  echo "1. tb/tb_cpi.sv con Verilator contra build/gemelo, serie de practica completa a 0,1 ms (sw/trade.hex)"
  for v in r0 seg; do
    if cmp -s "$B/rtl_${v}_ticks.csv" "$B/gemelo_${v}_ticks.csv"; then
      echo "PASS $v: $(($(wc -l < "$B/rtl_${v}_ticks.csv") - 1)) filas por tick identicas byte a byte (ciclo del precio, respuesta, tick completo e IC)"
    else
      echo "FAIL $v: la fila por tick del RTL difiere de la del gemelo"
    fi
    grep -E "respuesta, (promedio|peor)|tick completo, (promedio|peor)" "$B/rtl_$v.log" | sed "s/^/    RTL $v: /"
  done
  echo
  echo "2. R1 y R2: medicion del RTL de P5 (tools/fondo/ticks.sh) contra el gemelo, ronda 3"
  echo "   gemelo R1: respuesta promedio y peor, tick completo promedio y peor: $gem_fondo"
  for hw in r1 r2; do
    f=docs/mediciones/fondo/$hw/ticks.txt
    p=$(sha256sum sw/fondo.s | cut -c1-16); t=$(sha256sum sw/fondo_tabla.hex | cut -c1-16)
    if ! grep -q "sw/fondo.s (sha256 $p" "$f" || ! grep -q "sw/fondo_tabla.hex (sha256 $t" "$f"; then
      echo "FAIL $hw: $f no es del programa o de la tabla actuales"; continue
    fi
    rtl=$(resp_fondo "$f")
    if [ "$(echo $rtl)" = "$(echo $gem_fondo)" ]; then
      echo "PASS $hw: RTL $rtl, igual al gemelo ($f, mismo sha256 de programa y tabla)"
    else
      echo "FAIL $hw: RTL $rtl distinto del gemelo $gem_fondo"
    fi
  done
} > $M/rtl.txt
cat $M/rtl.txt
! grep -q FAIL $M/rtl.txt
