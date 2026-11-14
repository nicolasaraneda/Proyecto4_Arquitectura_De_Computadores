#!/usr/bin/env bash
# medir_cadena.sh: retardo de la cadena del duplicador según largo, semilla y ubicación.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Sintetiza rtl/top_cadena.v (duplicador más un contador) para cada largo N y
# cada modo de la cadena, y corre nextpnr con varias semillas en cuatro
# ubicaciones: libre (nextpnr decide) y fija en tres lugares del chip
# (scripts/fijar_cadena.py). De cada corrida se guardan:
#   - el SDF de nextpnr, de donde sale el retardo que nextpnr le asigna a la
#     cadena (un solo valor por arco, por el pin lógico);
#   - la netlist de icetime, de donde scripts/sta_icestorm.py saca el ancho
#     del pulso con el pin físico, subida y bajada, en las tres esquinas.
# El resumen lo arma scripts/resumen_cadena.py.
#
# Uso: scripts/medir_cadena.sh [SEMILLAS]      (por defecto 10)
# Variables: LARGOS, MODOS, UBICACIONES, LIMITE (segundos por corrida de nextpnr)
# Resultado: mediciones/cadena.txt
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-10}
LARGOS=${LARGOS:-"1 2 4 6 8 10 12 16 20"}
MODOS=${MODOS:-"0 1"}
# nombre:X:Y  (libre no fija nada)
UBICACIONES=${UBICACIONES:-"libre fijo_1_8:1:8 fijo_6_9:6:9 fijo_12_2:12:2"}
D=$B/cadena
mkdir -p "$D"

for m in $MODOS; do
  for n in $LARGOS; do
    yosys -q -l "$D/m${m}_n${n}.yosys.log" -p "read_verilog $F/rtl/duplicador_reloj.v $F/rtl/top_cadena.v; \
      chparam -set N $n -set Modo $m top_cadena; synth_ice40 -top top_cadena -json $D/m${m}_n${n}.json"
  done
done

una() {   # una MODO N UBICACION SEMILLA
  local m=$1 n=$2 u=$3 s=$4
  local nombre=${u%%:*}
  local base=$D/m${m}_n${n}_${nombre}_s${s}
  local extra=""
  if [ "$nombre" != libre ]; then
    local resto=${u#*:}
    export CADENA_X=${resto%%:*} CADENA_Y=${resto##*:}
    extra="--pre-pack $F/scripts/fijar_cadena.py"
  fi
  # El ruteador de nextpnr no siempre termina con la cadena de 4 entradas en
  # ubicación libre: se corta a los LIMITE segundos y la corrida se cuenta
  # como no ruteada.
  rm -f "$base.sta.json" "$base.nortea"
  timeout "$LIMITE" nextpnr-ice40 --hx1k --package vq100 --freq 50 --seed "$s" --json "$D/m${m}_n${n}.json" \
    --pcf goboard.pcf --pcf-allow-unconstrained $extra \
    --asc "$base.asc" --sdf "$base.sdf" -l "$base.log" -q > /dev/null 2>&1 || { touch "$base.nortea"; return 0; }
  icetime -d hx1k -P vq100 -p goboard.pcf -o "$base.ice.v" "$base.asc" > /dev/null 2>&1
  python3 "$F/scripts/sta_icestorm.py" "$base.ice.v" --json "$base.sta.json" > "$base.sta.txt"
  rm -f "$base.asc" "$base.ice.v"
}
LIMITE=${LIMITE:-60}
export -f una; export D F LIMITE

for m in $MODOS; do for n in $LARGOS; do for u in $UBICACIONES; do for s in $(seq 1 "$SEMILLAS"); do
  echo "$m $n $u $s"
done; done; done; done | xargs -P "$JOBS" -L1 bash -c 'una "$0" "$1" "$2" "$3"'

python3 "$F/scripts/resumen_cadena.py" "$D" | tee "$M/cadena.txt"
