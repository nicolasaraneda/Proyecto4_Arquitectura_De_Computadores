#!/usr/bin/env bash
# potencia.sh: potencia del macro ASIC con actividad real.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Es el método de asic/potencia/ de nuestro Proyecto 3: se simula el netlist
# final de una corrida (después del place and route) ejecutando trade.s con la
# maestra del testbench, se vuelca la actividad de todos los nodos en un VCD y
# OpenSTA calcula la potencia con esa actividad, los parásitos extraídos y el
# liberty de cada esquina. Es un cálculo sobre el netlist: no es una medición
# sobre silicio.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/g_asic/scripts/potencia.sh TAG [todo|sim|contar_x|sta|tabla|xinit]
#     TAG  corrida completa, por ejemplo base_t40 o seg_t40
#
# Ventanas, con la maestra a 0,1 ms por tick (ronda 3). El tick n empieza en
# 4000 + n * 100000 ns. Las ubica la sonda de tb/tb_asic_puertos.sv (-DSONDA):
# el precio llega a los 8580 ns del tick y el programa vuelve al lazo de sondeo
# antes de los 11100 ns en el Espino base y de los 9980 ns en el segmentado.
#   ronda3     4 ticks completos (20 a 23): transacción SPI, cálculo y sondeo
#   sondeo     70 us dentro del tick 20, con el bus SPI quieto: el programa
#              solo sondea STATUS. Es lo que el chip hace más del 97 % del
#              tiempo, y casi todo el tiempo en las rondas 1 y 2
#   calculo    80 ciclos desde el octavo flanco de SCLK del tick 20: llega el
#              precio, el programa decide, escribe DECISION y actualiza la media
#   calculo_b  lo mismo en el tick 23, para ver la dispersión entre ticks
#
# Modos sin VCD: defecto (lo que informa el flujo) y cero (solo el reloj).
# Esquinas: típica, lenta y rápida. Reportes en build/potencia/TAG/ y copia
# de los que respaldan la tabla en mediciones/potencia/TAG/.
set -euo pipefail
source factibilidad/g_asic/scripts/fuentes.sh
PDK_ROOT=${PDK_ROOT:-$HOME/.ciel/ciel/gf180mcu/versions/54435919abffb937387ec956209f9cf5fd2dfbee}
SCL=gf180mcu_fd_sc_mcu7t5v0
CELDAS_V="$PDK_ROOT/gf180mcuD/libs.ref/$SCL/verilog/primitives.v $PDK_ROOT/gf180mcuD/libs.ref/$SCL/verilog/$SCL.v"
IMG=ghcr.io/librelane/librelane:3.0.16
DOCKER="docker run --rm --user $(id -u):$(id -g) -v $HOME:$HOME -w $(pwd) -e HOME=$HOME -e PDK_ROOT=$PDK_ROOT"
ESQUINAS="nom_tt_025C_5v00 max_ss_125C_4v50 min_ff_n40C_5v50"
VENTANAS=("ronda3 2004000 2404000" "sondeo 2024000 2094000" "calculo 2012500 2015700" "calculo_b 2312500 2315700")

TAG=$1
FASE=${2:-todo}
CORRIDA=$G/runs/$TAG/final
NL=$CORRIDA/nl/asic_top.nl.v
B=$G/build/potencia/$TAG
R=$G/mediciones/potencia/$TAG
mkdir -p "$B" "$R"
[ -f "$NL" ] || { echo "no existe $NL: la corrida $TAG no terminó"; exit 1; }

sim() {
  iverilog -g2012 -s tb_asic_puertos -DNETLIST -DFUNCTIONAL -DNTICKS=30 -DPERIODO_NS=100000 \
    "-DSALIDA=\"$B/bytes.csv\"" -o "$B/sim" "$NL" $CELDAS_V $G/tb/tb_asic_puertos.sv
  : > "$R/ventanas.txt"
  for v in "${VENTANAS[@]}"; do set -- $v
    vvp -n "$B/sim" +vcd="$B/$1.vcd" +vcd_t0=$2 +vcd_t1=$3 > "$B/sim_$1.log"
    echo "$1 t0=$2 ns t1=$3 ns ciclos=$(( ($3 - $2) / 40 )) vcd=$(stat -c %s "$B/$1.vcd") bytes senales=$(grep -c '^\$var' "$B/$1.vcd")" | tee -a "$R/ventanas.txt"
  done
}

sta_una() {  # salida modo esquina [VAR=VAL ...]
  local salida=$1 modo=$2 esquina=$3; shift 3
  local extra=""; for kv in "$@"; do extra="$extra -e $kv"; done
  $DOCKER -e CORRIDA=$CORRIDA -e ESQUINA=$esquina -e MODO=$modo $extra $IMG sta -no_splash -exit $G/scripts/potencia.tcl > "$B/$salida.rpt" 2>&1 \
    || { echo "FALLO $salida (ver $B/$salida.rpt)"; return 1; }
  cp "$B/$salida.rpt" "$R/$salida.txt"
  echo "   $salida: $(grep -E '^Total' "$B/$salida.rpt" | head -1 | awk '{print $5" W"}') $(grep -E '^Annotated' "$B/$salida.rpt" | tr '\n' ' ' || true)"
  # Con un VCD, todos los pines deben quedar anotados. Si no, OpenSTA propaga
  # una actividad inventada y el número no vale (ver tb/tb_asic_puertos.sv).
  if [ "$modo" = vcd ]; then
    local sin
    sin=$(awk '$1 == "unannotated" { print $2; exit }' "$B/$salida.rpt")
    if [ "${sin:-1}" != 0 ]; then
      echo "FALLO $salida: quedaron ${sin:-?} pines sin anotar desde el VCD"; return 1
    fi
  fi
}

sta() {
  for e in $ESQUINAS; do
    sta_una defecto_$e defecto $e
    sta_una cero_$e cero $e
    for v in "${VENTANAS[@]}"; do set -- $v
      sta_una ${1}_$e vcd $e VCD=$B/$1.vcd SCOPE=tb_asic_puertos/dut
    done
  done
}

# Cambios de valor a 0 o 1 y a x en cada VCD, fuera del volcado inicial.
# OpenSTA no cuenta las transiciones desde o hacia x. Los flip-flops sin reset
# (banco de registros y palabras de datos que trade.s nunca escribe) quedan en
# x durante toda la simulación, y los nodos que los leen pasan por x. Este
# conteo dimensiona cuánta actividad queda fuera del cálculo.
contar_x() {
  : > "$R/conteo_x.txt"
  for v in "${VENTANAS[@]}"; do set -- $v
    [ -s "$B/$1.vcd" ] || continue
    awk -v nombre="$1" 'BEGIN{defs=1} /^\$enddefinitions/{defs=0; next} defs{next}
         /^#/{t=substr($0,2); if(t0=="")t0=t; next}
         { if(t==t0) next; ch=substr($0,1,1); if(ch=="0"||ch=="1") v01++;
           else if(ch=="x"){ vx++; c=substr($0,2); if(!(c in seen)){seen[c]=1; nc++} } }
         END{printf "%s cambios_a_0_o_1=%d cambios_a_x=%d porcentaje_x=%.2f senales_que_pasan_por_x=%d\n", nombre, v01, vx, (v01 ? 100*vx/v01 : 0), nc}' \
      "$B/$1.vcd" | tee -a "$R/conteo_x.txt"
  done
}

# Sensibilidad al estado inicial de los flip-flops sin reset (método del
# Proyecto 3). Repite las ventanas ronda3 y calculo con tb/dffq_func_init.v,
# con estado inicial 0 y 1, y calcula la potencia en la esquina típica. Las
# decisiones de cada simulación deben ser las mismas de la simulación normal.
xinit() {
  local I v e=nom_tt_025C_5v00
  : > "$R/xinit.txt"
  for I in 0 1; do
    iverilog -g2012 -s tb_asic_puertos -DNETLIST -DFUNCTIONAL -DNTICKS=30 -DPERIODO_NS=100000 \
      -DINIT_FF=$I -DGF180MCU_FD_SC_MCU7T5V0__DFFQ_FUNC_V \
      "-DSALIDA=\"$B/bytes_init$I.csv\"" -o "$B/sim_init$I" $G/tb/dffq_func_init.v "$NL" $CELDAS_V $G/tb/tb_asic_puertos.sv
    for v in "ronda3 2004000 2404000" "calculo 2012500 2015700"; do set -- $v
      vvp -n "$B/sim_init$I" +vcd="$B/$1_init$I.vcd" +vcd_t0=$2 +vcd_t1=$3 > "$B/sim_$1_init$I.log"
      local nx
      nx=$(awk 'BEGIN{defs=1} /^\$enddefinitions/{defs=0; next} defs{next} /^#/{t=substr($0,2); if(t0=="")t0=t; next}
                { if(t!=t0 && substr($0,1,1)=="x") n++ } END{print n+0}' "$B/$1_init$I.vcd")
      sta_una ${1}_init${I}_$e vcd $e VCD=$B/$1_init$I.vcd SCOPE=tb_asic_puertos/dut
      echo "$1 init=$I cambios_a_x=$nx total_W=$(grep -E '^Total' "$B/${1}_init${I}_$e.rpt" | head -1 | awk '{print $5}') combinacional_W=$(grep -E '^Combinational' "$B/${1}_init${I}_$e.rpt" | head -1 | awk '{print $5}')" | tee -a "$R/xinit.txt"
    done
    # Los bytes que leyó la maestra en los ticks 0 a 18 (la última simulación
    # de cada juego termina en el tick 20)
    if cmp -s <(head -20 "$B/bytes_init$I.csv") <(head -20 "$B/bytes.csv"); then
      echo "init=$I: los 19 primeros bytes de decision son los mismos de la simulacion normal" | tee -a "$R/xinit.txt"
    else
      echo "init=$I: AVISO: los bytes de decision difieren de la simulacion normal" | tee -a "$R/xinit.txt"
    fi
  done
  echo "normal ronda3 total_W=$(grep -E '^Total' "$B/ronda3_$e.rpt" | head -1 | awk '{print $5}') combinacional_W=$(grep -E '^Combinational' "$B/ronda3_$e.rpt" | head -1 | awk '{print $5}')" | tee -a "$R/xinit.txt"
  echo "normal calculo total_W=$(grep -E '^Total' "$B/calculo_$e.rpt" | head -1 | awk '{print $5}') combinacional_W=$(grep -E '^Combinational' "$B/calculo_$e.rpt" | head -1 | awk '{print $5}')" | tee -a "$R/xinit.txt"
}

tabla() {
  python3 $G/scripts/tabla_potencia.py "$TAG"
}

case $FASE in
  todo)  sim; contar_x; sta; tabla ;;
  sim)   sim ;;
  contar_x) contar_x ;;
  xinit) xinit ;;
  sta)   sta ;;
  tabla) tabla ;;
  *) echo "fase desconocida: $FASE (todo, sim, contar_x, sta, tabla o xinit)"; exit 1 ;;
esac
