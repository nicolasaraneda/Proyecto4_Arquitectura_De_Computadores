#!/usr/bin/env bash
# humo.sh: pruebas de humo del Espino barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# No es la verificación a fondo (esa queda para el tramo siguiente). Comprueba
# que el prototipo ejecuta bien, con cuatro pruebas:
#
#   1. hilos_distintos   Cuatro hilos independientes con cálculos distintos.
#                        Resultados en memoria contra valores esperados, y la
#                        traza de cada hilo contra la del Espino base corriendo
#                        el mismo programa desde la entrada de ese hilo
#                        (tb/core_trace_tb.v y tb/comparar_trazas.py del
#                        repositorio, sin modificar, en modo funcional).
#   2. cooperacion       Tres hilos publican un valor en memoria compartida y
#                        el hilo 0 los suma y escribe display y LEDs.
#   3. mix_clase7_x4     El mix de la clase 7 en los cuatro hilos: traza de
#                        cada hilo contra el Espino base.
#   4. hazard_test y     Los programas de riesgos del Proyecto 3 (sw/, sin
#      hazard_review     modificar) en cada uno de los cuatro hilos, con los
#                        otros tres en un lazo vacío. Cada uno se revisa a sí
#                        mismo (LEDs en 1111) y su traza, incluidas las
#                        salidas, se compara con la del Espino base.
#   5. hilo_mmio         La alternativa de arranque sin tabla: el SoC con el
#                        registro HILO y los cuatro hilos partiendo en 0.
#   6. Controles         Tres errores puestos a propósito en el core.
#      negativos
#
# Uso: factibilidad/a_barrel/tools/humo.sh   (o make humo en esa carpeta)
# Deja el resultado en factibilidad/a_barrel/mediciones/humo.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/humo
mkdir -p "$O"
programas
fallas=0
falla() { echo "FAIL $1"; fallas=$((fallas + 1)); }

# barrel NOMBRE HEX CICLOS [definiciones...]: corre tb_barrel, deja NOMBRE.log y trazas NOMBRE_h?.txt
barrel() {
  local n=$1 hex=$2 c=$3; shift 3
  iverilog -g2012 -s tb_barrel "-DPROGRAMA=\"$hex\"" "-DTRAZA=\"$O/$n\"" -DCICLOS="$c" "$@" \
    -o "$O/$n.vvp" "$CELLS_SIM" $BARREL_SRC $A/tb/tb_barrel.sv && vvp -n "$O/$n.vvp" > "$O/$n.log"
}
# base NOMBRE HEX CICLOS HILO: Espino base desde la entrada del hilo, deja NOMBRE.txt
base() {
  local n=$1 hex=$2 c=$3 h=$4
  iverilog -g2012 -s core_trace_tb -s boot_hilo -DHILO="$h" "-DPROGRAMA=\"$hex\"" "-DTRAZA=\"$O/$n.txt\"" \
    -DCICLOS="$c" -o "$O/$n.vvp" "$CELLS_SIM" $BASE_SRC tb/core_trace_tb.v $A/tb/boot_hilo.v \
    && vvp -n "$O/$n.vvp" > "$O/$n.log"
}
# comparar TEXTO TIPOS REF ACT
comparar() {
  local texto=$1 tipos=$2 ref=$3 act=$4
  if $PYTHON tb/comparar_trazas.py --modo funcional --tipos "$tipos" "$ref" "$act" > "$O/cmp.txt"; then
    echo "PASS $texto: $(grep 'eventos iguales' "$O/cmp.txt" | sed 's/ (ref.*//' | tr '\n' ',' | sed 's/,$//; s/,/, /g')"
  else
    falla "$texto: $(grep DIFIEREN "$O/cmp.txt" | head -1)"
  fi
}
resultado() {   # resultado NOMBRE TEXTO: exige RESULTADO: PASS en el log de tb_barrel
  if grep -q "^RESULTADO: PASS" "$O/$1.log"; then
    echo "PASS $2: $(grep -c '^PASS' "$O/$1.log") comprobaciones del testbench"
  else
    falla "$2: $(grep '^FAIL' "$O/$1.log" | head -1)"
  fi
}

{
echo "Pruebas de humo del Espino barrel"
echo "Generado por factibilidad/a_barrel/tools/humo.sh (make humo). No editar a mano."
echo
versiones
echo

# --- 1. Cuatro hilos distintos ------------------------------------------------
echo "1. hilos_distintos.s: cuatro hilos independientes"
barrel hd "$B/sw/hilos_distintos.hex" 4000 "-DESPERADO=\"$A/sw/hilos_distintos.esperado.txt\"" || falla "hilos_distintos: no corre"
resultado hd "hilos_distintos, resultados en memoria y modelo de costo"
grep -E "^PASS [0-9]+ de" "$O/hd.log" | sed 's/^/     /'
for t in 0 1 2 3; do base hd_base_h$t "$B/sw/hilos_distintos.hex" 4000 $t & done; wait
for t in 0 1 2 3; do
  comparar "hilos_distintos, hilo $t contra el Espino base desde la direccion $((4 * t))" rf,bus "$O/hd_base_h$t.txt" "$O/hd_h$t.txt"
done
echo

# --- 2. Cooperación por memoria compartida ------------------------------------
echo "2. cooperacion.s: tres hilos publican y el hilo 0 junta"
barrel coop "$B/sw/cooperacion.hex" 4000 -DLEDS=15 "-DDISP=8'h60" || falla "cooperacion: no corre"
resultado coop "cooperacion, LEDs 1111 y display 60"
echo

# --- 3. Mix de la clase 7 en los cuatro hilos -----------------------------------
echo "3. mix_clase7_x4.s: el mismo lazo en los cuatro hilos, cada uno con sus datos"
barrel mix "$B/sw/mix_clase7_x4.hex" 8000 || falla "mix_clase7_x4: no corre"
resultado mix "mix_clase7_x4, modelo de costo"
for t in 0 1 2 3; do base mix_base_h$t "$B/sw/mix_clase7_x4.hex" 4000 $t & done; wait
for t in 0 1 2 3; do
  comparar "mix_clase7_x4, hilo $t contra el Espino base" rf,bus "$O/mix_base_h$t.txt" "$O/mix_h$t.txt"
done
echo

# --- 4. Programas de riesgos del Proyecto 3, en cada hilo -----------------------
echo "4. hazard_test.s y hazard_review.s (sin modificar) en cada hilo, los otros tres en un lazo vacio"
for p in hazard_test hazard_review; do
  for t in 0 1 2 3; do
    con_tabla $t sw/$p.s "$O/${p}_h$t.hex" || { falla "$p hilo $t: no ensambla"; continue; }
    ( barrel ${p}_h$t "$O/${p}_h$t.hex" 16000 -DLEDS=15 ) &
    ( base ${p}_base_h$t "$O/${p}_h$t.hex" 8000 $t ) &
  done
  wait
  for t in 0 1 2 3; do
    resultado ${p}_h$t "$p en el hilo $t, LEDs 1111"
    cat "$O/${p}_h${t}_h$t.txt" "$O/${p}_h${t}_io.txt" > "$O/${p}_h${t}_todo.txt"
    comparar "$p en el hilo $t contra el Espino base" rf,bus,io "$O/${p}_base_h$t.txt" "$O/${p}_h${t}_todo.txt"
    # Los hilos ociosos no deben escribir registros ni tocar el bus
    for o in 0 1 2 3; do
      [ $o = $t ] && continue
      [ -s "$O/${p}_h${t}_h$o.txt" ] && falla "$p en el hilo $t: el hilo ocioso $o hizo algo"
    done
  done
done
echo

# --- 5. Alternativa de arranque: registro HILO y los cuatro hilos desde 0 ----------
echo "5. hilo_mmio.s: arranque sin tabla, con el registro HILO (-DBARREL_MMIO_HILO -DBARREL_BOOT_PASO=0)"
barrel mmio "$B/sw/hilo_mmio.hex" 400 "-DESPERADO=\"$A/sw/hilo_mmio.esperado.txt\"" -DBARREL_MMIO_HILO -DBARREL_BOOT_PASO=0 || falla "hilo_mmio: no corre"
resultado mmio "hilo_mmio, cada hilo lee su numero y deja su resultado"
grep -E "^PASS [0-9]+ de" "$O/mmio.log" | sed 's/^/     /'
echo "     $(grep '^Primera instruccion' "$O/mmio.log")"
# Control: sin el registro los cuatro hilos leen 0 y la prueba tiene que fallar
barrel mmio_neg "$B/sw/hilo_mmio.hex" 400 "-DESPERADO=\"$A/sw/hilo_mmio.esperado.txt\"" -DBARREL_BOOT_PASO=0 > /dev/null 2>&1
if grep -q "^RESULTADO: PASS" "$O/mmio_neg.log"; then falla "hilo_mmio pasa sin el registro HILO"
else echo "PASS hilo_mmio falla si el SoC no tiene el registro HILO (control)"; fi
echo

# --- 6. Controles negativos ---------------------------------------------------------
echo "6. Controles negativos: tres errores puestos a proposito en el core deben hacer fallar las pruebas"
for m in MUTA_CONTEXTO MUTA_BOFF MUTA_ARRANQUE; do
  det=""
  barrel neg_hd "$B/sw/hilos_distintos.hex" 4000 "-DESPERADO=\"$A/sw/hilos_distintos.esperado.txt\"" -D$m > /dev/null 2>&1
  grep -q "^RESULTADO: PASS" "$O/neg_hd.log" || det="$det hilos_distintos"
  barrel neg_hz "$O/hazard_test_h2.hex" 16000 -DLEDS=15 -D$m > /dev/null 2>&1
  cat "$O/neg_hz_h2.txt" "$O/neg_hz_io.txt" > "$O/neg_hz_todo.txt"
  if ! grep -q "^RESULTADO: PASS" "$O/neg_hz.log" || \
     ! $PYTHON tb/comparar_trazas.py --modo funcional --tipos rf,bus,io "$O/hazard_test_base_h2.txt" "$O/neg_hz_todo.txt" > /dev/null; then
    det="$det hazard_test"
  fi
  if [ -n "$det" ]; then echo "PASS $m detectada por:$det"
  else falla "$m no fue detectada"; fi
done
echo

if [ $fallas = 0 ]; then echo "RESULTADO: todas las pruebas de humo pasan"
else echo "RESULTADO: $fallas pruebas de humo FALLAN"; fi
} | tee "$M/humo.txt"

grep -q "^RESULTADO: todas" "$M/humo.txt"
