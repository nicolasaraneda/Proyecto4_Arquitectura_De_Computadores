#!/usr/bin/env bash
# humo_soc.sh: prueba de humo del SoC con el reloj doblado, con el testbench oficial sin modificar.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Compila tb/tb_proyecto_4.sv tal como está en el repositorio contra
# rtl/pochoco_soc_x2.v (el duplicador con su modelo de retardo, SIM_RETARDO)
# y agrega tb/monitor_x2.sv como segundo módulo raíz. Corre los 2000 ticks
# por defecto a 0,1 ms con el Espino base y con el segmentado, y compara el
# decisiones.csv con ref/trader.py. Con el reloj doblado el reset dura la
# mitad (4095 ciclos de 20 ns), así que se pierde un precio inicial y no
# dos: la referencia se corre con --por-bits 11, que dura lo mismo.
#
# El testbench escribe decisiones.csv en el directorio de trabajo. Para no
# tocar la raíz del repositorio, la simulación corre en build/humo/VARIANTE
# con enlaces a sw/ y tb/. Las variantes corren en paralelo (unos 5 minutos
# cada una con la máquina libre).
#
# Qué mira además del testbench: tb/monitor_x2.sv cuenta los pulsos de
# byte_done y las escrituras de DECISION con el reloj interno y con el de
# 25 MHz, que es con el que muestrea el testbench oficial. Si el testbench
# no los ve todos, su 4/4 y su peor caso salen de una parte de los ticks.
#
# Uso: scripts/humo_soc.sh [VARIANTES]      (por defecto "base seg")
# Resultado: mediciones/humo_soc_x2.txt
source "$(dirname "$0")/comun.sh"

VARIANTES=${1:-"base seg"}
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v

correr() {   # correr VARIANTE: deja su bloque en build/humo/VARIANTE/bloque.txt
  local v=$1
  local D=$B/humo/$v
  mkdir -p "$D"
  ln -sfn "$RAIZ/sw" "$D/sw"
  ln -sfn "$RAIZ/tb" "$D/tb"
  local DEFS=""; [ "$v" = seg ] && DEFS="-DESPINO_SEGMENTADO"
  iverilog -g2012 -DSIM_RETARDO $DEFS -s tb_proyecto_4 -s monitor_x2 -o "$D/sim" \
    "$CELLS_SIM" $SOC_X2 tb/tb_proyecto_4.sv "$F/tb/monitor_x2.sv"
  (cd "$D" && vvp -n sim > tb.log)
  python3 ref/trader.py tb/practica.csv --nticks 2000 --periodo-ns 100000 --por-bits 11 -o "$D/ref.csv" > "$D/ref.log"
  {
    echo "== $v"
    grep -E "PASS|FAIL|Peor caso|Patrimonio final|Testbenchs aprobados|MONITOR" "$D/tb.log" | sed 's/^/  /'
    if cmp -s "$D/decisiones.csv" "$D/ref.csv"; then
      echo "  decisiones.csv idéntico a ref/trader.py ($(($(wc -l < "$D/decisiones.csv") - 1)) filas)"
    else
      echo "  decisiones.csv DISTINTO de ref/trader.py"
    fi
    echo
  } > "$D/bloque.txt"
}

for v in $VARIANTES; do correr "$v" & done
wait

{
  echo "Prueba de humo del SoC con el reloj doblado (simulación RTL con Icarus, retardo del duplicador modelado)"
  if git diff --quiet HEAD -- tb/tb_proyecto_4.sv; then
    echo "Testbench: tb/tb_proyecto_4.sv sin modificar (igual al del último commit)"
  else
    echo "AVISO: tb/tb_proyecto_4.sv difiere del último commit"
  fi
  echo
  mal=0
  for v in $VARIANTES; do
    cat "$B/humo/$v/bloque.txt"
    grep -q "DISTINTO" "$B/humo/$v/bloque.txt" && mal=1
    grep -q "Testbenchs aprobados: 4/4" "$B/humo/$v/bloque.txt" || mal=1
  done
  if [ "$mal" = 0 ]; then echo "HUMO: PASS"; else echo "HUMO: FAIL"; fi
} | tee "$M/humo_soc_x2.txt"
grep -q "HUMO: PASS" "$M/humo_soc_x2.txt"
