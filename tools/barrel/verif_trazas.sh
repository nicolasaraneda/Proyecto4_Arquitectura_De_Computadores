#!/usr/bin/env bash
# verif_trazas.sh: cada hilo del barrel contra el Espino base por comparación
# de trazas en modo funcional, con programas aleatorios.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Es el método de make riesgos, con sus mismas piezas sin
# modificar: tb/core_trace_tb.v escribe la traza del Espino base (rtl/, sin
# tocar) y tb/comparar_trazas.py --modo funcional compara las secuencias de
# escrituras al banco de registros, de accesos al bus de datos y de cambios de
# las salidas, sin mirar el ciclo. La traza del barrel la escribe
# tb/barrel/tb_barrel.sv, una por hilo y con el mismo formato. El Espino base parte
# en la entrada del hilo (tb/barrel/boot_hilo.v).
#
# Se corre con Icarus, que simula con cuatro estados: además de comparar,
# tb_barrel.sv cuenta los valores desconocidos (X) que llegan al banco o al
# bus, cosa que Verilator no puede ver.
#
# Complementa a tools/barrel/verif.sh (Verilator, instrucción por instrucción): es
# otra forma de comparar, con otro simulador y otros testbenches.
#
#   1. Un hilo con un programa aleatorio de 300 instrucciones y los otros tres
#      en un lazo vacío (tools/barrel/prog_hilos.py --modo uno), para cada hilo.
#      Se comparan escrituras al banco, accesos al bus y salidas.
#   2. Los cuatro hilos a la vez, programas distintos y zonas de datos
#      separadas (--modo separado). Se comparan escrituras al banco y accesos
#      al bus de cada hilo contra el base corriendo solo.
#
# Uso: tools/barrel/verif_trazas.sh [SEMILLAS]   (o make barrel-trazas)
# Resultado en docs/mediciones/barrel/trazas.txt.
# Variables de entorno: JOBS (simulaciones en paralelo, por defecto 4) y
# CICLOS (ciclos del barrel por corrida, por defecto 24000: 6000 instrucciones
# por hilo).
set -uo pipefail
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-6}
JOBS=${JOBS:-4}
CICLOS=${CICLOS:-24000}
CICLOS_BASE=$((CICLOS * 3 / 4 + 100))    # el base gasta a lo más 3 ciclos por instrucción
O=$B/trazas
mkdir -p "$O"

# sim_barrel NOMBRE: corre tb_barrel con NOMBRE.hex y deja NOMBRE_h?.txt, NOMBRE_io.txt y NOMBRE.log
sim_barrel() {
  local n=$O/$1
  iverilog -g2012 -s tb_barrel "-DPROGRAMA=\"$n.hex\"" "-DTRAZA=\"$n\"" -DCICLOS="$CICLOS" \
    -o "$n.vvp" "$CELLS_SIM" $BARREL_SRC $TB/tb_barrel.sv && vvp -n "$n.vvp" > "$n.log" 2>&1
}
# sim_base NOMBRE HILO: Espino base con NOMBRE.hex desde la entrada del hilo, deja NOMBRE_base_hHILO.txt
sim_base() {
  local n=$O/$1 h=$2
  iverilog -g2012 -s core_trace_tb -s boot_hilo -DHILO="$h" "-DPROGRAMA=\"$n.hex\"" "-DTRAZA=\"${n}_base_h$h.txt\"" \
    -DCICLOS="$CICLOS_BASE" -o "${n}_base_h$h.vvp" "$CELLS_SIM" $BASE_SRC tb/core_trace_tb.v $TB/boot_hilo.v \
    && vvp -n "${n}_base_h$h.vvp" > "${n}_base_h$h.log" 2>&1
}
# caso MODO SEMILLA HILO: genera el programa y corre las simulaciones que hacen falta
caso() {
  local modo=$1 s=$2 t=$3 nombre=$1_s$2_h$3
  if [ "$modo" = uno ]; then
    $PYTHON $T/prog_hilos.py "$s" --modo uno --hilo-spi "$t" -n 300 -o "$O/$nombre.s"
  else
    $PYTHON $T/prog_hilos.py "$s" --modo separado -o "$O/$nombre.s"
  fi
  $PYTHON tools/pochoasm.py --allow-shifts "$O/$nombre.s" -o "$O/$nombre.hex" > /dev/null || return 0
  sim_barrel "$nombre"
  if [ "$modo" = uno ]; then sim_base "$nombre" "$t"
  else for h in 0 1 2 3; do sim_base "$nombre" "$h"; done; fi
  return 0
}
export -f sim_barrel sim_base caso
export O T TB SW FO PYTHON CICLOS CICLOS_BASE CELLS_SIM BARREL_SRC BASE_SRC

: > "$O/casos.txt"
for s in $(seq 1 "$SEMILLAS"); do
  for t in 0 1 2 3; do echo "uno $s $t" >> "$O/casos.txt"; done
  echo "separado $s x" >> "$O/casos.txt"
done
rm -f "$O"/*.txt.cmp
xargs -P "$JOBS" -L 1 bash -c 'caso "$0" "$1" "$2"' < "$O/casos.txt"

{
echo "Cada hilo del barrel contra el Espino base por trazas en modo funcional (Icarus, programas aleatorios)"
echo "Generado por tools/barrel/verif_trazas.sh (make barrel-trazas). No editar a mano."
echo
versiones
echo
echo "Ciclos por corrida: $CICLOS en el barrel ($((CICLOS / 4)) instrucciones por hilo) y $CICLOS_BASE en el Espino base."
echo "Trazas del base: tb/core_trace_tb.v. Comparacion: tb/comparar_trazas.py --modo funcional. Los dos sin modificar."
echo
fallas=0
declare -A ev_rf ev_bus
for h in 0 1 2 3; do ev_rf[$h]=0; ev_bus[$h]=0; done
ev_io=0; corridas=0; xtotal=0
# comparar NOMBRE HILO TIPOS ACT: compara contra NOMBRE_base_hHILO.txt y acumula
comparar() {
  local nombre=$1 h=$2 tipos=$3 act=$4 salida
  salida=$($PYTHON tb/comparar_trazas.py --modo funcional --tipos "$tipos" "$O/${nombre}_base_h$h.txt" "$act" 2>&1)
  if [ $? -ne 0 ]; then
    echo "FAIL $nombre, hilo $h: $(echo "$salida" | grep -m1 DIFIEREN)"; fallas=$((fallas + 1)); return
  fi
  local r b i
  r=$(echo "$salida" | sed -nE 's/^rf: ([0-9]+) eventos iguales.*/\1/p')
  b=$(echo "$salida" | sed -nE 's/^bus: ([0-9]+) eventos iguales.*/\1/p')
  i=$(echo "$salida" | sed -nE 's/^io: ([0-9]+) eventos iguales.*/\1/p')
  ev_rf[$h]=$((${ev_rf[$h]} + ${r:-0})); ev_bus[$h]=$((${ev_bus[$h]} + ${b:-0})); ev_io=$((ev_io + ${i:-0}))
}
while read -r modo s t; do
  nombre=${modo}_s${s}_h${t}
  corridas=$((corridas + 1))
  if ! grep -q "^RESULTADO: PASS" "$O/$nombre.log" 2>/dev/null; then
    echo "FAIL $nombre: $(grep -m1 '^FAIL' "$O/$nombre.log" 2>/dev/null || echo 'tb_barrel no termino')"; fallas=$((fallas + 1)); continue
  fi
  x=$(sed -nE 's/^Monitor de X: +([0-9]+) valores.*/\1/p' "$O/$nombre.log"); xtotal=$((xtotal + ${x:-0}))
  if [ "$modo" = uno ]; then
    cat "$O/${nombre}_h$t.txt" "$O/${nombre}_io.txt" > "$O/${nombre}_todo.txt"
    comparar "$nombre" "$t" rf,bus,io "$O/${nombre}_todo.txt"
    for o in 0 1 2 3; do
      [ "$o" = "$t" ] && continue
      [ -s "$O/${nombre}_h$o.txt" ] && { echo "FAIL $nombre: el hilo ocioso $o escribio un registro o toco el bus"; fallas=$((fallas + 1)); }
    done
  else
    for h in 0 1 2 3; do comparar "$nombre" "$h" rf,bus "$O/${nombre}_h$h.txt"; done
  fi
done < "$O/casos.txt"

echo "Corridas del barrel: $corridas ($SEMILLAS semillas: 4 con un hilo activo y 1 con los cuatro, por semilla)."
echo "Eventos iguales entre cada hilo del barrel y el Espino base, sumados sobre las corridas:"
echo "   hilo   escrituras al banco   accesos al bus"
trf=0; tbus=0
for h in 0 1 2 3; do
  printf "   %s      %17s   %14s\n" "$h" "${ev_rf[$h]}" "${ev_bus[$h]}"
  trf=$((trf + ${ev_rf[$h]})); tbus=$((tbus + ${ev_bus[$h]}))
done
printf "   total  %17s   %14s\n" "$trf" "$tbus"
echo "Cambios de LEDs y display iguales (corridas de un hilo): $ev_io."
echo "Valores desconocidos (X) que llegaron al banco o al bus en el barrel: $xtotal."
echo "Ademas, en cada corrida tb_barrel.sv comprueba el modelo de costo: una instruccion por ciclo en total y una cada 4 ciclos por hilo."
echo
if [ $fallas = 0 ] && [ "$xtotal" = 0 ]; then echo "RESULTADO: PASS, las trazas de cada hilo son equivalentes a las del Espino base"
else echo "RESULTADO: FAIL ($fallas comparaciones con problemas, $xtotal valores X)"; fi
} | tee "$M/trazas.txt"

grep -q "^RESULTADO: PASS" "$M/trazas.txt"
