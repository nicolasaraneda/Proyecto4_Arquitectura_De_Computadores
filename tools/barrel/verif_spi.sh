#!/usr/bin/env bash
# verif_spi.sh: max_media en cada hilo del barrel, con precios que llegan
# por los pines del SPI, contra la referencia en Python.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# tools/barrel/verif.sh deja el bus SPI quieto. Aquí la maestra es la del testbench
# oficial: una copia parametrizada de tb/tb_proyecto_4.sv (solo cambian
# PROGRAMA, SERIE, NTICKS y el nombre del archivo de salida, igual que en
# tools/equiv.sh) corre con Verilator contra el SoC barrel.
# Se exige 4/4 y que decisiones.csv sea idéntico byte a byte al de
# ref/trader.py, que es la referencia que el Espino base cumple.
#
#   1. sw/trade.s (sin modificar) en el hilo T, para T = 0, 1, 2 y 3, con los
#      otros tres hilos en un lazo vacío. Serie de práctica completa.
#   2. sw/trade.s en el hilo T mientras los otros tres corren programas
#      aleatorios que leen y escriben memoria y periféricos (tools/barrel/prog_hilos.py
#      --modo trade). Es el caso del fondo de estrategias: un hilo atiende a la
#      maestra y los demás calculan.
#
# El testbench se compila una sola vez: lee el programa de "prog.hex" y cada
# caso corre en su propia carpeta.
#
# Uso: tools/barrel/verif_spi.sh   (o make barrel-spi)
# Resultado en docs/mediciones/barrel/spi_hilos.txt.
# Variables de entorno: JOBS (por defecto 4), NTICKS (por defecto 20000),
# NTICKS_FONDO (por defecto 5000) y SEMILLAS (programas aleatorios por hilo,
# por defecto 2).
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/spi
JOBS=${JOBS:-4}
NTICKS=${NTICKS:-20000}
NTICKS_FONDO=${NTICKS_FONDO:-5000}
SEMILLAS=${SEMILLAS:-2}
PERIODO_NS=100000
mkdir -p "$O"

# compilar ETIQUETA NTICKS: copia parametrizada del testbench oficial
compilar() {
  local d=$O/$1 n=$2
  mkdir -p "$d"
  sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"prog.hex\";|" \
      -e "s|SERIE      = \"[^\"]*\";|SERIE      = \"$RAIZ/tb/practica.csv\";|" \
      -e "s|NTICKS     = [0-9]*;|NTICKS     = $n;|" \
      -e "s|\"decisiones.csv\"|\"tb.csv\"|" \
      tb/tb_proyecto_4.sv > "$d/tb_p4.sv"
  [ "$(diff tb/tb_proyecto_4.sv "$d/tb_p4.sv" | grep -c '^>')" -le 4 ] || { echo "FAIL: la copia del testbench cambio mas de lo esperado"; return 1; }
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_proyecto_4 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS -O3 --Mdir "$d/obj" -o sim \
    "$CELLS_SIM" $BARREL_SRC "$d/tb_p4.sv" > "$d/verilator.log" 2>&1
}
compilar tb_largo "$NTICKS" &
compilar tb_fondo "$NTICKS_FONDO" &
wait
for e in tb_largo tb_fondo; do
  [ -x "$O/$e/obj/sim" ] || { echo "FAIL spi: el testbench no compila (ver $O/$e/verilator.log)"; exit 1; }
done
$PYTHON ref/trader.py tb/practica.csv --nticks "$NTICKS" --periodo-ns $PERIODO_NS -o "$O/ref_largo.csv" > "$O/ref_largo.log"
$PYTHON ref/trader.py tb/practica.csv --nticks "$NTICKS_FONDO" --periodo-ns $PERIODO_NS -o "$O/ref_fondo.csv" > "$O/ref_fondo.log"

# caso TIPO HILO SEMILLA: arma el programa y corre el testbench en su carpeta
caso() {
  local tipo=$1 t=$2 s=$3 d=$O/$1_h$2_s$3
  mkdir -p "$d"
  if [ "$tipo" = solo ]; then
    $PYTHON $T/tabla.py "$t" sw/trade.s > "$d/prog.s"
    $PYTHON tools/pochoasm.py "$d/prog.s" -o "$d/prog.hex" > /dev/null || return 0
    ( cd "$d" && "$O/tb_largo/obj/sim" > tb.log 2>&1 )
  else
    $PYTHON $T/prog_hilos.py "$s" --modo trade --hilo-spi "$t" --trade sw/trade.s -n 90 -o "$d/prog.s"
    $PYTHON tools/pochoasm.py --allow-shifts "$d/prog.s" -o "$d/prog.hex" > /dev/null || return 0
    ( cd "$d" && "$O/tb_fondo/obj/sim" > tb.log 2>&1 )
  fi
  return 0
}
export -f caso
export O T TB SW FO PYTHON

: > "$O/casos.txt"
for t in 0 1 2 3; do echo "solo $t 0" >> "$O/casos.txt"; done
for t in 0 1 2 3; do for s in $(seq 1 "$SEMILLAS"); do echo "fondo $t $s" >> "$O/casos.txt"; done; done
O=$(cd "$O" && pwd) xargs -P "$JOBS" -L 1 bash -c 'caso "$0" "$1" "$2"' < "$O/casos.txt"

{
echo "max_media (sw/trade.s) en cada hilo del barrel, con la maestra SPI del testbench oficial"
echo "Generado por tools/barrel/verif_spi.sh (make barrel-spi). No editar a mano."
echo
versiones
echo "  $(verilator --version)"
echo
echo "Testbench: copia parametrizada de tb/tb_proyecto_4.sv, periodo $PERIODO_NS ns (ronda 3), serie tb/practica.csv."
echo "Referencia: ref/trader.py con los mismos ticks. Se exige 4/4 y decisiones.csv identico byte a byte."
echo
fallas=0
while read -r tipo t s; do
  d=$O/${tipo}_h${t}_s${s}
  if [ "$tipo" = solo ]; then ref=$O/ref_largo.csv; que="trade.s en el hilo $t, los otros tres en un lazo vacio"
  else ref=$O/ref_fondo.csv; que="trade.s en el hilo $t, los otros tres con programas aleatorios (semilla $s)"; fi
  if ! grep -q "Testbenchs aprobados: 4/4" "$d/tb.log" 2>/dev/null; then
    echo "FAIL $que: el testbench no entrega 4/4"; fallas=$((fallas + 1)); continue
  fi
  if ! cmp -s "$d/tb.csv" "$ref"; then
    echo "FAIL $que: decisiones distintas a la referencia"; fallas=$((fallas + 1)); continue
  fi
  echo "PASS $que: 4/4, $(($(wc -l < "$d/tb.csv") - 1)) filas identicas a ref/trader.py, patrimonio $(tail -1 "$d/tb.csv" | cut -d, -f6), $(grep 'Peor caso' "$d/tb.log" | sed 's/  */ /g; s/Peor caso precio->decision: /peor caso /')"
done < "$O/casos.txt"
echo
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, cada hilo decide igual que la referencia, solo o con los otros tres ocupados"
else echo "RESULTADO: FAIL ($fallas casos)"; fi
} | tee "$M/spi_hilos.txt"

grep -q "^RESULTADO: PASS" "$M/spi_hilos.txt"
