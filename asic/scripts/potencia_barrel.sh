#!/usr/bin/env bash
# potencia_barrel.sh: potencia del macro ASIC del barrel con actividad real.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Mismo método que factibilidad/g_asic/scripts/potencia.sh (y que asic/potencia/ del
# Proyecto 3): se simula el netlist final ejecutando sw/fondo.s con la maestra, se
# vuelca la actividad de una ventana y OpenSTA calcula la potencia con esa actividad,
# los parásitos extraídos y el liberty de cada esquina. Es un cálculo sobre el
# netlist, no una medición sobre silicio.
#
# Diferencias con el del base: los VCD se escriben en /dev/shm (memoria) y se borran
# después de usarlos, para no guardar formas de onda en disco; y las ventanas son las
# del fondo, que responde en 223 ciclos en promedio y 444 en el peor caso.
#   ronda3   4 ticks completos (20 a 23), a 0,1 ms por tick
#   sondeo   60 us del tick 20 después de decidir: los cuatro hilos sondean
#   calculo  450 ciclos desde el octavo flanco de SCLK del tick 20: supervisor y
#            gestores calculan, votan y escriben DECISION
#
# Uso, desde la raíz: asic/scripts/potencia_barrel.sh TAG [todo|sim|sta]
set -euo pipefail
source asic/scripts/fuentes.sh
PDK_ROOT=${PDK_ROOT:-$HOME/.ciel/ciel/gf180mcu/versions/54435919abffb937387ec956209f9cf5fd2dfbee}
SCL=gf180mcu_fd_sc_mcu7t5v0
CELDAS_V="$PDK_ROOT/gf180mcuD/libs.ref/$SCL/verilog/primitives.v $PDK_ROOT/gf180mcuD/libs.ref/$SCL/verilog/$SCL.v"
IMG=ghcr.io/librelane/librelane:3.0.16
ESQUINAS="nom_tt_025C_5v00 max_ss_125C_4v50 min_ff_n40C_5v50"
VENTANAS=("ronda3 2004000 2404000" "sondeo 2034000 2094000" "calculo 2012500 2030500")
TAG=$1
FASE=${2:-todo}
CORRIDA=$A/runs/$TAG/final
NL=$CORRIDA/nl/asic_top_barrel.nl.v
B=$A/build/potencia/$TAG
V=/dev/shm/asic_barrel_$TAG
R=$A/mediciones/potencia/$TAG
DOCKER="docker run --rm --user $(id -u):$(id -g) -v $HOME:$HOME -v /dev/shm:/dev/shm -w $(pwd) -e HOME=$HOME -e PDK_ROOT=$PDK_ROOT"
mkdir -p "$B" "$R" "$V"
[ -f "$NL" ] || { echo "no existe $NL: la corrida $TAG no terminó"; exit 1; }
sim() {
  iverilog -g2012 -s tb_asic_barrel_puertos -DNETLIST -DFUNCTIONAL -DNTICKS=30 -DPERIODO_NS=100000 \
    "-DSALIDA=\"$B/bytes.csv\"" -o "$B/sim" "$NL" $CELDAS_V $A/tb/tb_asic_barrel_puertos.sv
  : > "$R/ventanas.txt"
  for v in "${VENTANAS[@]}"; do set -- $v
    vvp -n "$B/sim" +vcd="$V/$1.vcd" +vcd_t0=$2 +vcd_t1=$3 > "$B/sim_$1.log"
    echo "$1 t0=$2 ns t1=$3 ns ciclos=$(( ($3 - $2) / 40 )) vcd=$(stat -c %s "$V/$1.vcd") bytes" | tee -a "$R/ventanas.txt"
  done
  # Los bytes que leyó la maestra en los ticks 0 a 18, contra la referencia
  python3 ref/fondo.py tb/practica.csv --nticks 30 --periodo-ns 100000 --perdidos 0 -o "$B/ref.csv" > /dev/null
  if cmp -s <(head -20 "$B/bytes.csv" | cut -d, -f3) <(head -20 "$B/ref.csv" | cut -d, -f3); then
    echo "PASS: los 19 primeros bytes de la netlist final son los de ref/fondo.py" | tee -a "$R/ventanas.txt"
  else
    echo "AVISO: los bytes de la netlist final difieren de ref/fondo.py (ver $B/bytes.csv)" | tee -a "$R/ventanas.txt"
  fi
}
sta_una() {  # salida modo esquina [VAR=VAL ...]
  local salida=$1 modo=$2 esquina=$3; shift 3
  local extra=""; for kv in "$@"; do extra="$extra -e $kv"; done
  $DOCKER -e CORRIDA=$CORRIDA -e ESQUINA=$esquina -e MODO=$modo $extra $IMG sta -no_splash -exit $A/scripts/potencia.tcl > "$B/$salida.rpt" 2>&1 \
    || { echo "FALLO $salida (ver $B/$salida.rpt)"; return 1; }
  cp "$B/$salida.rpt" "$R/$salida.txt"
  echo "   $salida: $(grep -E '^Total' "$B/$salida.rpt" | head -1 | awk '{print $5" W"}')"
}
sta() {
  for e in $ESQUINAS; do
    sta_una defecto_$e defecto $e
    for v in "${VENTANAS[@]}"; do set -- $v
      sta_una ${1}_$e vcd $e VCD=$V/$1.vcd SCOPE=tb_asic_barrel_puertos/dut
    done
  done
  rm -rf "$V"
}
case $FASE in
  todo) sim; sta ;;
  sim)  sim ;;
  sta)  sta ;;
  *) echo "fase desconocida: $FASE"; exit 1 ;;
esac
