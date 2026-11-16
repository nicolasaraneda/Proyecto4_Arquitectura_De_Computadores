#!/usr/bin/env bash
# humo_fase.sh: lo que ve el testbench oficial del SoC doblado depende de la fase de la maestra.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El testbench oficial muestrea byte_done y la escritura de DECISION con su
# reloj de 25 MHz. Con el reloj interno doblado esos pulsos duran un ciclo
# interno, o sea medio ciclo del testbench: que los vea o no depende de en
# qué mitad caigan, y eso lo decide el instante en que la maestra mueve SCLK.
# El testbench oficial sube SCLK justo en un flanco de subida del reloj.
#
# Este script corre dos copias parametrizadas del testbench, de 200 ticks:
# una con el timing oficial y otra con toda la transacción SPI corrida
# 20 ns (la primera transacción parte a los 4020 ns en vez de 4000). El
# testbench oficial no se toca: las copias quedan en build/humo_fase/.
# En las dos se compara el decisiones.csv con ref/trader.py.
#
# Uso: scripts/humo_fase.sh
# Resultado: mediciones/humo_fase.txt
source "$(dirname "$0")/comun.sh"

CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
D=$B/humo_fase
mkdir -p "$D"
NT=200

correr() {   # correr NOMBRE INICIO_NS
  local n=$1 ini=$2
  mkdir -p "$D/$n"
  ln -sfn "$RAIZ/sw" "$D/$n/sw"
  ln -sfn "$RAIZ/tb" "$D/$n/tb"
  sed -e "s/localparam int    NTICKS     = 2000;/localparam int    NTICKS     = $NT;/" \
      -e "s/#4000;/#$ini;/" tb/tb_proyecto_4.sv > "$D/$n/tb_copia.sv"
  iverilog -g2012 -DSIM_RETARDO -s tb_proyecto_4 -s monitor_x2 -o "$D/$n/sim" \
    "$CELLS_SIM" $SOC_X2 "$D/$n/tb_copia.sv" "$F/tb/monitor_x2.sv"
  (cd "$D/$n" && vvp -n sim > tb.log)
  python3 ref/trader.py tb/practica.csv --nticks $NT --periodo-ns 100000 --por-bits 11 -o "$D/$n/ref.csv" > "$D/$n/ref.log"
  echo "== primera transacción a los $ini ns"
  grep -E "PASS|FAIL|Peor caso|Testbenchs aprobados|MONITOR byte_done|MONITOR escrituras|MONITOR respuesta" "$D/$n/tb.log" | sed 's/^/  /'
  if cmp -s "$D/$n/decisiones.csv" "$D/$n/ref.csv"; then
    echo "  decisiones.csv idéntico a ref/trader.py ($NT filas): el SoC decide bien en los dos casos"
  else
    echo "  decisiones.csv DISTINTO de ref/trader.py"
  fi
  echo
}

correr oficial 4000 > "$D/oficial.txt" &
correr corrido 4020 > "$D/corrido.txt" &
wait
{
  echo "El testbench oficial frente al reloj interno doblado: efecto de la fase (Espino base, $NT ticks)"
  echo "Copias parametrizadas de tb/tb_proyecto_4.sv. Cambian solo NTICKS y el instante de la primera transacción."
  echo
  cat "$D/oficial.txt" "$D/corrido.txt"
} | tee "$M/humo_fase.txt"
