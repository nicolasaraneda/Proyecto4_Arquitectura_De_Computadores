#!/usr/bin/env bash
# medir_soc.sh: el SoC con el reloj doblado, 10 semillas, a 50 MHz y a la frecuencia que exige el ciclo de trabajo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Variantes:
#   base_x2   Espino base con el reloj doblado (rtl/pochoco_soc_x2.v)
#   seg_x2    Espino segmentado (-DESPINO_SEGMENTADO) con el reloj doblado
#   base_x1, seg_x1   los mismos SoC sin duplicador (Doblar = 0), como control:
#             misma lógica, mismo objetivo de frecuencia, reloj por el pin
# Cada variante se rutea con cada frecuencia objetivo de FRECS y cada semilla.
# El reloj doblado se restringe con restricciones/reloj_x2.py (ctx.addClock),
# que es la forma que deja el objetivo atado al nombre de la red y no a
# --freq. De cada corrida se guarda el log de nextpnr, lo que dice icetime y
# el análisis de scripts/sta_icestorm.py (clases de ruta, pulso del
# duplicador y holguras para ciclo de trabajo de 45, 50 y 55 %).
#
# Uso: scripts/medir_soc.sh [SEMILLAS]        (por defecto 10)
# Variables: VARIANTES, FRECS, NRET_BASE, NRET_SEG, MODO_RET
# Resultado: mediciones/soc_x2.txt
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-10}
VARIANTES=${VARIANTES:-"base_x2 seg_x2 base_x1 seg_x1"}
FRECS=${FRECS:-"50 56.4"}
NRET_BASE=${NRET_BASE:-8}
NRET_SEG=${NRET_SEG:-6}
MODO_RET=${MODO_RET:-0}
D=$B/soc
mkdir -p "$D"

for v in $VARIANTES; do
  case $v in
    base_x2) DEFS="";                    PAR="chparam -set NRet $NRET_BASE -set ModoRet $MODO_RET pochoco_soc;" ;;
    seg_x2)  DEFS="-DESPINO_SEGMENTADO"; PAR="chparam -set NRet $NRET_SEG -set ModoRet $MODO_RET pochoco_soc;" ;;
    base_x1) DEFS="";                    PAR="chparam -set Doblar 0 pochoco_soc;" ;;
    seg_x1)  DEFS="-DESPINO_SEGMENTADO"; PAR="chparam -set Doblar 0 pochoco_soc;" ;;
    *) echo "variante desconocida: $v"; exit 1 ;;
  esac
  yosys -q -l "$D/$v.yosys.log" -p "read_verilog $DEFS $SOC_X2; \
    chparam -set MemFile \"sw/trade.hex\" pochoco_soc; $PAR synth_ice40 -top pochoco_soc -json $D/$v.json" &
done
wait

una() {   # una VARIANTE FRECUENCIA SEMILLA
  local v=$1 f=$2 s=$3
  local base=$D/${v}_f${f}_s${s}
  local extra="--freq $f"
  if [ "${v##*_}" = x2 ]; then
    export CADENA_X=1 CADENA_Y=8 RELOJ_X2_MHZ=$f
    extra="--freq 25 --pre-pack $F/scripts/fijar_cadena.py --pre-pack $F/restricciones/reloj_x2.py"
  fi
  nextpnr-ice40 --hx1k --package vq100 $extra --seed "$s" --json "$D/$v.json" --pcf goboard.pcf \
    --timing-allow-fail --asc "$base.asc" --write "$base.pnr.json" -l "$base.log" -q 2>/dev/null \
    || { echo "FALLA nextpnr $base"; return 0; }
  icetime -d hx1k -P vq100 -p goboard.pcf -c "$f" -o "$base.ice.v" -r "$base.icetime.txt" "$base.asc" > /dev/null 2>&1 || true
  python3 "$F/scripts/sta_icestorm.py" "$base.ice.v" --pnr-json "$base.pnr.json" \
    --json "$base.sta.json" > "$base.sta.txt"
  rm -f "$base.asc" "$base.ice.v" "$base.pnr.json"
}
export -f una; export D F

for v in $VARIANTES; do for f in $FRECS; do for s in $(seq 1 "$SEMILLAS"); do
  echo "$v $f $s"
done; done; done | xargs -P "$JOBS" -L1 bash -c 'una "$0" "$1" "$2"'

python3 "$F/scripts/resumen_soc.py" "$D" | tee "$M/soc_x2.txt"
