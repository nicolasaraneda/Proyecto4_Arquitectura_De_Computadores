#!/usr/bin/env bash
# medir_ticks.sh: mediciones por tick del punto 3.2 del enunciado.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre tb/tb_cpi.sv con la serie de práctica al período de cada ronda y deja
# el resultado en docs/mediciones/ticks_<variante>.txt: IC, ciclos, CPI y
# tiempo por tick, promedio y peor caso, contra el T de la ronda. Deja además
# una fila por tick en build/med/<variante>_<ronda>_ticks.csv.
#
# Usa Verilator porque Icarus demoraría horas en la ronda de 10 ms. Las dos
# herramientas dan la misma traza ciclo a ciclo (make cosim lo comprueba).
#
# Uso, desde la raíz: tools/medir_ticks.sh [VARIANTE]
# Variables de entorno: HEX, SRC, NT_R1, NT_R2, NT_R3 (ticks por ronda).
set -euo pipefail

VARIANTE=${1:-software}
HEX=${HEX:-sw/trade.hex}
SRC=${SRC:-$(echo rtl/*.v rtl/espino_core/*.v)}
SERIE=${SERIE:-tb/practica.csv}
NT_R1=${NT_R1:-2000}
NT_R2=${NT_R2:-20000}
NT_R3=${NT_R3:-20000}
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
D=build/med
mkdir -p "$D" docs/mediciones

correr() {   # ronda periodo_ns nticks
  local r=$1 periodo=$2 nticks=$3 o="$D/${VARIANTE}_$1"
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_cpi -O3 \
    "-DPROGRAMA=\"$HEX\"" "-DSERIE=\"$SERIE\"" -DNTICKS="$nticks" -DPERIODO_NS="$periodo" \
    "-DTICKS_CSV=\"${o}_ticks.csv\"" --Mdir "${o}_obj" -o sim \
    "$CELLS_SIM" $SRC tb/tb_cpi.sv > "${o}_verilator.log" 2>&1
  "${o}_obj/sim" | grep -v -e '^- ' > "${o}.log"
}

correr r1 10000000 "$NT_R1" &
correr r2 1000000  "$NT_R2" &
correr r3 100000   "$NT_R3" &
wait

SALIDA=docs/mediciones/ticks_$VARIANTE.txt
{
  echo "Mediciones por tick, variante: $VARIANTE"
  echo "Programa $HEX, serie $SERIE. Generado por tools/medir_ticks.sh (make medir-ticks)."
  echo "Reloj de 25 MHz: un ciclo son 40 ns."
  for r in r1 r2 r3; do
    echo
    echo "== Ronda ${r#r} =="
    cat "$D/${VARIANTE}_$r.log"
  done
} > "$SALIDA"
grep -q "FAIL" "$SALIDA" && { echo "FAIL: ver $SALIDA"; exit 1; }
cat "$SALIDA"
