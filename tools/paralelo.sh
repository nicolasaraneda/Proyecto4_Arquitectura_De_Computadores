#!/usr/bin/env bash
# paralelo.sh: ejecución en paralelo del Espino base y del segmentado con
# programas aleatorios.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Compila tb/tb_paralelo.sv con Verilator (una sola vez) y lo corre con un
# programa de tools/prog_aleatorio.py por semilla. En cada instrucción
# completada compara lo que hizo cada core y el contenido real del banco de
# registros y de la memoria. Ver el encabezado de tb/tb_paralelo.sv.
#
# Uso, desde la raíz del repositorio:
#   tools/paralelo.sh [SEMILLAS] [INSTRUCCIONES_POR_SEMILLA]
# Por defecto 4 semillas de 25 000 instrucciones (lo que corre la integración
# continua). make paralelo-largo corre 16 semillas de 100 000: 1,6 millones.
# Variables de entorno:
#   PCW    bits del contador de programa del segmentado: 11 (el que se
#          sintetiza) o 32. Por defecto se corren las dos configuraciones.
#   MUTA   definiciones extra (mutaciones, tools/mutaciones.sh)
#   ETQ    sufijo de la carpeta de salida
#   JOBS   simulaciones en paralelo (por defecto 8)
#   PRIMERA  primera semilla (por defecto 1)
set -uo pipefail

SEMILLAS=${1:-4}
INSTR=${2:-25000}
MUTA=${MUTA:-}
ETQ=${ETQ:-}
JOBS=${JOBS:-8}
PRIMERA=${PRIMERA:-1}
PYTHON=${PYTHON:-python3}
if [ -z "${PCW:-}" ]; then
  PCW=11 "$0" "$@" || exit 1
  PCW=32 "$0" "$@" || exit 1
  exit 0
fi
SRC=$(echo rtl/*.v rtl/espino_core/*.v)
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
D=build/paralelo${ETQ:+_$ETQ}_pc$PCW
mkdir -p "$D"

if ! verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_paralelo -O3 $MUTA -DPCW_B=$PCW \
     -DNO_ICE40_DEFAULT_ASSIGNMENTS --Mdir "$D/obj" -o sim "$CELLS_SIM" $SRC tb/tb_paralelo.sv > "$D/verilator.log" 2>&1; then
  echo "FAIL paralelo: no compila (ver $D/verilator.log)"; tail -5 "$D/verilator.log"; exit 1
fi

una() {   # una SEMILLA
  local s=$1
  $PYTHON tools/prog_aleatorio.py "$s" -o "$D/prog_$s.s" \
    && $PYTHON tools/pochoasm.py --allow-shifts "$D/prog_$s.s" -o "$D/prog_$s.hex" > /dev/null \
    && "$D/obj/sim" "+hex=$D/prog_$s.hex" "+instrucciones=$INSTR" > "$D/sim_$s.log" 2>&1
}
export -f una; export D INSTR PYTHON
seq "$PRIMERA" $((PRIMERA + SEMILLAS - 1)) | xargs -P "$JOBS" -I{} bash -c "una {}"

total=0; rf=0; st=0; ld=0; sal=0; fallas=0; fuera=0
for s in $(seq "$PRIMERA" $((PRIMERA + SEMILLAS - 1))); do
  if grep -q "^PASS paralelo" "$D/sim_$s.log"; then
    set -- $(grep "^PASS paralelo" "$D/sim_$s.log" | sed -E 's/[^0-9 ]//g')
    total=$((total + $1)); rf=$((rf + $2)); st=$((st + $3)); ld=$((ld + $4)); sal=$((sal + $5))
    if grep -q "FUERA" "$D/sim_$s.log"; then fuera=$((fuera + 1)); fi
  else
    fallas=$((fallas + 1))
    echo "FAIL paralelo, semilla $s: $(grep -m1 -A2 FAIL "$D/sim_$s.log" | tr '\n' ' ')"
  fi
done

if [ "$fallas" -ne 0 ]; then
  echo "FAIL paralelo: $fallas de $SEMILLAS programas difieren"; exit 1
fi
echo "PASS paralelo (contador de programa de $PCW bits): $SEMILLAS programas aleatorios, $total instrucciones comparadas una por una entre el Espino base y el segmentado ($rf escrituras de registro, $st stores, $ld loads, $sal saltos), con el banco de registros completo en cada una. Programas que salieron de la memoria: $fuera"
