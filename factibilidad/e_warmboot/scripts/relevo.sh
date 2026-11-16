#!/usr/bin/env bash
# relevo.sh: simula el relevo completo y cuenta los ticks que se pierden.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Usa tb/tb_relevo.sv: el SoC principal (copia con vigilante, N = 4) corre
# sw/cuelgue.s, que responde 20 precios y se cuelga; el vigilante dispara; la
# FPGA "se reconfigura" durante TCFG (modelo: pin MISO suelto, sin reloj); y
# el SoC de respaldo (core base, sw/trade.hex) parte de cero.
#
# Parte 1. Los tres períodos de la competencia con TCFG = 53 ms, el valor
#          típico de la hoja de datos para la HX1K con el oscilador de
#          configuración en frecuencia baja, y con los otros dos valores
#          documentados (25 ms y 13 ms) en la ronda 3. Tirón del pin en 1 y en 0.
# Parte 2. Barrido del instante de vuelta: TCFG = 2 ms + j, con j entre 82 y
#          98 us en pasos de 0,5 us, a 0,1 ms. BOOT sube 13,6 us después del
#          comienzo de un tick, así que ese rango recorre toda la transacción
#          siguiente (que dura 9,5 us) con dos puntos por bit: son todas las
#          posiciones en que el respaldo puede empezar a manejar el pin
#          dentro de una transacción.
# Parte 3. Barrido del retardo entre BOOT y el momento en que el pin se
#          suelta: DBOOT = j, con el mismo rango, con un programa que tenía
#          escrito comprar 63 (0x7F) y con uno que tenía escrito mantener
#          (0x00). En las partes 2 y 3 el programa se cuelga después de 4
#          precios, para que las simulaciones sean cortas.
#
# TCFG y el nivel del pin suelto son supuestos del modelo. Lo que la
# simulación sí comprueba es la lógica: cuándo dispara el vigilante, que el
# respaldo arranca bien en medio del tráfico y qué órdenes ejecuta la maestra.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/e_warmboot/scripts/relevo.sh
# Resultado en mediciones/relevo.txt.
set -euo pipefail

E=factibilidad/e_warmboot
D=$E/build/relevo
JOBS=${JOBS:-5}
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
mkdir -p "$D" "$E/mediciones"
RTLV=$($E/scripts/armar_rtl.sh)

# Con SOLO_INFORME=1 no se simula nada: se vuelve a armar el informe con los
# registros que ya están en build/relevo/ (sirve si la corrida se interrumpió
# después de las simulaciones).
if [ "${SOLO_INFORME:-0}" != 1 ]; then
python3 tools/pochoasm.py $E/sw/cuelgue.s -D K=20 -D DEC=0x7F -o "$D/cuelgue_7f.hex" > /dev/null
python3 tools/pochoasm.py $E/sw/cuelgue.s -D K=4 -D DEC=0x7F -o "$D/corto_7f.hex" > /dev/null
python3 tools/pochoasm.py $E/sw/cuelgue.s -D K=4 -D DEC=0x00 -o "$D/corto_00.hex" > /dev/null

compilar() {   # compilar NOMBRE PERIODO_NS NTICKS TIRON PROGRAMA
  iverilog -g2012 -s tb_relevo -DPERIODO_NS=$2 -DNTICKS=$3 "-DTIRON=1'b$4" \
    "-DPROG_PRINCIPAL=\"$5\"" -o "$D/$1.vvp" "$CELLS_SIM" $RTLV/*.v $RTLV/espino_core/*.v $E/tb/tb_relevo.sv
}
correr() {     # correr NOMBRE ETIQUETA TCFG_NS DBOOT_NS
  vvp -n "$D/$1.vvp" +tcfg=$3 +dboot=$4 "+salida=$D/$2.csv" > "$D/$2.log" 2>&1 || true
}
export -f correr; export D

compilar r3_t1  100000   700 1 "$D/cuelgue_7f.hex"
compilar r3_t0  100000   700 0 "$D/cuelgue_7f.hex"
compilar r2_t1  1000000  140 1 "$D/cuelgue_7f.hex"
compilar r1_t1  10000000  60 1 "$D/cuelgue_7f.hex"
compilar b_t1   100000    50 1 "$D/corto_7f.hex"
compilar b_t0   100000    50 0 "$D/corto_7f.hex"
compilar h_t1   100000    50 1 "$D/corto_00.hex"
compilar h_t0   100000    50 0 "$D/corto_00.hex"

{
  echo "r3_t1 p1_r3_53_t1 53000000 0"
  echo "r3_t0 p1_r3_53_t0 53000000 0"
  echo "r3_t1 p1_r3_25_t1 25000000 0"
  echo "r3_t1 p1_r3_13_t1 13000000 0"
  echo "r2_t1 p1_r2_53_t1 53000000 0"
  echo "r1_t1 p1_r1_53_t1 53000000 0"
  for j in $(seq 82000 500 98000); do
    echo "b_t1 p2_t1_$j $((2000000 + j)) 0"
    echo "b_t0 p2_t0_$j $((2000000 + j)) 0"
    echo "b_t1 p3_7f_t1_$j 2000000 $j"
    echo "b_t0 p3_7f_t0_$j 2000000 $j"
    echo "h_t1 p3_00_t1_$j 2000000 $j"
    echo "h_t0 p3_00_t0_$j 2000000 $j"
  done
} > "$D/lista.txt"
rm -f "$D"/p?_*.log
xargs -P "$JOBS" -L1 bash -c 'correr $0 $1 $2 $3' < "$D/lista.txt"
fi

campo() { grep "^$2" "$D/$1.log" | head -1 | sed "s/^$2[: ]*//"; }

{
  echo "Simulación del relevo: del programa colgado a la imagen de respaldo"
  echo "Comando: factibilidad/e_warmboot/scripts/relevo.sh"
  echo "Principal: copia del SoC con vigilante (N = 4) y sw/cuelgue.s (20 precios y se cuelga)."
  echo "Respaldo: core base con sw/trade.hex. Maestra y contabilidad del testbench oficial."
  echo "TCFG y el nivel del pin suelto son supuestos del modelo, no mediciones."
  echo
  echo "=== Parte 1. Los tres períodos ==="
  for c in p1_r1_53_t1 p1_r2_53_t1 p1_r3_53_t1 p1_r3_53_t0 p1_r3_25_t1 p1_r3_13_t1; do
    echo "--- $c ---"
    grep -v "finish called" "$D/$c.log" | sed 's/^/  /'
  done
  echo
  echo "Resumen de la parte 1 (ticks sin decisión nueva = desde el último precio respondido"
  echo "por el principal hasta la primera escritura del respaldo, sin contar los extremos):"
  printf "  %-13s %-10s %-6s %-22s %-16s %-10s\n" "caso" "TCFG" "tirón" "ticks sin decisión" "ticks pin suelto" "resultado"
  for c in p1_r1_53_t1 p1_r2_53_t1 p1_r3_53_t1 p1_r3_53_t0 p1_r3_25_t1 p1_r3_13_t1; do
    printf "  %-13s %-10s %-6s %-22s %-16s %-10s\n" "$c" \
      "$(grep '^RELEVO' "$D/$c.log" | sed -E 's/.*tcfg_ns=([0-9]+).*/\1/' | awk '{printf "%d ms", $1/1000000}')" \
      "$(grep '^RELEVO' "$D/$c.log" | sed -E 's/.*tiron=([0-9]).*/\1/')" \
      "$(campo $c ticks_sin_decision_nueva | cut -d' ' -f1)" \
      "$(campo $c ticks_con_el_pin_suelto | cut -d' ' -f1)" \
      "$(grep -o '^PASS relevo\|^FAIL relevo' "$D/$c.log")"
  done
  echo
  echo "=== Parte 2. Barrido del instante de vuelta (66 simulaciones) ==="
  for t in t1 t0; do
    n=$(ls "$D"/p2_${t}_*.log | wc -l)
    pass=$(grep -l '^PASS relevo' "$D"/p2_${t}_*.log | wc -l)
    cort=$(grep -h '^transacciones_cortadas' "$D"/p2_${t}_*.log | grep -c 'fase 1 a 2' || true)
    bytes=$(grep -h '^transacciones_cortadas' "$D"/p2_${t}_*.log | { grep -o 'fase 1 a 2, byte [0-9a-f]*' || true; } | awk '{print $NF}' | sort -u | paste -sd' ')
    ord=$(grep -h '^ordenes_ejecutadas_durante_el_corte' "$D"/p2_${t}_*.log | awk '{s+=$NF} END {print s+0}')
    echo "tirón = ${t#t}: $n simulaciones, $pass PASS. En $cort la vuelta cae dentro de una transacción."
    echo "  bytes leídos en esas transacciones: ${bytes:-ninguno}"
    echo "  órdenes ejecutadas durante el corte, sumando todas: $ord"
  done
  echo
  echo "=== Parte 3. Barrido del retardo entre BOOT y la salida del pin (132 simulaciones) ==="
  for p in 7f 00; do
    for t in t1 t0; do
      n=$(ls "$D"/p3_${p}_${t}_*.log | wc -l)
      cort=$(grep -h '^transacciones_cortadas' "$D"/p3_${p}_${t}_*.log | grep -c 'fase 0 a 1' || true)
      bytes=$(grep -h '^transacciones_cortadas' "$D"/p3_${p}_${t}_*.log | { grep -o 'fase 0 a 1, byte [0-9a-f]*' || true; } | awk '{print $NF}' | sort -u | paste -sd' ')
      conord=$({ grep -l '^ordenes_ejecutadas_durante_el_corte: [1-9]' "$D"/p3_${p}_${t}_*.log 2>/dev/null || true; } | wc -l)
      cuales=$({ grep -l '^ordenes_ejecutadas_durante_el_corte: [1-9]' "$D"/p3_${p}_${t}_*.log 2>/dev/null || true; } | sed -E 's/.*_([0-9]+)\.log/\1 ns/' | paste -sd',' | sed 's/,/, /g')
      echo "DECISION = 0x$p, tirón = ${t#t}: $n simulaciones. En $cort la salida cae dentro de una transacción."
      echo "  bytes leídos en esas transacciones: ${bytes:-ninguno}"
      echo "  simulaciones en que la maestra ejecuta una orden durante el corte: $conord${cuales:+ (retardo de $cuales)}"
    done
  done
} | tee $E/mediciones/relevo.txt
