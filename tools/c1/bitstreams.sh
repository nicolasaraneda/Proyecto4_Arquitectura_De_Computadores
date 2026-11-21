#!/usr/bin/env bash
# bitstreams.sh: construye el bitstream de R3 (C1 sobre el barrel con vigilante y la
# tabla de 512 palabras), lo simula desde su .asc por los pines y prueba de punta a
# punta el molde con icebram, el cambio de tabla, el vigilante dentro del bitstream
# y la imagen múltiple con R0.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# R3 no sale del molde de R2: la tabla de 512 palabras es hardware nuevo (una BRAM
# más), así que se sintetiza. R0, R1 y R2 y sus moldes no se tocan.
#
#   1. Dos síntesis con yosys y nextpnr (semilla 1): R3 con el programa y la tabla
#      de verdad, y el molde de R3 con las dos memorias llenas de un patrón al azar.
#      El patrón del programa es el mismo de R1 y R2 (bitstreams/moldes/molde_prog.hex);
#      el de la tabla es nuevo, de 512 palabras (icebram -g -s 3 16 512).
#   2. icebram sobre el molde: reemplaza los patrones por sw/c1.s y sw/c1_tabla.hex.
#      El .asc que resulta tiene que ser idéntico al de la síntesis directa.
#   3. Criterio 8: el .asc simulado por los pines (tb/tb_bitstream.sv sin modificar,
#      Icarus, 0,1 ms), 2000 ticks contra ref/c1/c1.py en tres series: los primeros
#      2000 ticks de la serie Meta, la serie hecha a mano que apuesta en la fase A y
#      llega al candado, y una ventana de la serie Meta que pasa por el motor.
#      SB_WARMBOOT no se dispara.
#   4. Política apagada sin sintetizar: la tabla con la palabra POLITICA en 0 puesta
#      con icebram en el molde. Simulado desde el .asc, decide como la banda 40 de
#      R2 (ref/fondo.py). Se mide el tiempo de punta a punta.
#   5. Fallas dentro del bitstream (programas puestos con icebram en el molde):
#      a. el hilo 0 colgado en el tick 100: BOOT sube con S1 S0 = 01 y CS_n en alto
#         al terminar la quinta transacción sin respuesta;
#      b. el hilo 3 colgado en el tick 700: el vigilante NO dispara (el hilo 0 sigue
#         escribiendo) y los bytes son los de la referencia con esa falla: un tick
#         sostenido y después la banda 40.
#   6. icemulti: imagen 0 R3, imagen 1 R0 con la banda 40 (bitstreams/r0_banda40.bin,
#      sin tocar). tools/ver_multi.py revisa los vectores de arranque y que quepa.
#
# Los productos quedan en build/c1/bitstreams/. Con GUARDAR=1 y sin ningún FAIL copia
# a bitstreams/ los .bin de R3 y el molde con su patrón de tabla, y agrega sus hash a
# SHA256SUMS sin tocar las líneas de los demás. No programa la placa.
#
# Uso: [GUARDAR=1] tools/c1/bitstreams.sh   (make c1-bitstreams)
# Resultado en docs/mediciones/c1/bitstreams.txt. Unos 20 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BC/bitstreams
SALIDA=${SALIDA:-$MC/bitstreams.txt}
NTICKS=${NTICKS:-2000}
R0_BIN=bitstreams/r0_banda40.bin
FLASH=131072                       # flash de la Go Board: 1 Mbit
M=bitstreams/moldes
rm -rf "$O"; mkdir -p "$O"

completar() {   # completar ENTRADA.hex SALIDA.hex: 512 palabras, como exige icebram
  $PYTHON - "$1" "$2" <<'PY'
import sys
palabras = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("//") and not l.startswith("@")]
assert len(palabras) <= 512, len(palabras)
palabras += ["00000000"] * (512 - len(palabras))
open(sys.argv[2], "w", newline="\n").write("\n".join(palabras) + "\n")
PY
}
programa() {    # programa FUENTE.s NOMBRE: deja $O/NOMBRE.hex con 512 palabras
  $PYTHON tools/pochoasm.py "$1" -o "$O/$2_asm.hex" > /dev/null && completar "$O/$2_asm.hex" "$O/$2.hex"
}

# --- Memorias ---------------------------------------------------------------------
programa sw/c1.s c1 || { echo "FAIL: no ensambla"; exit 1; }
cp "$TABLA_HEX" "$O/tabla.hex"
cp "$M/molde_prog.hex" "$O/molde_prog.hex"
icebram -g -s 3 16 512 > "$O/molde_tabla512.hex"
$PYTHON $TC/generar.py --apagada -o "$O/apagada" > /dev/null
$PYTHON $TC/variante.py cuelga:0:100 -o "$O/colgado0.s" && programa "$O/colgado0.s" colgado0
$PYTHON $TC/variante.py cuelga:3:700 -o "$O/colgado3.s" && programa "$O/colgado3.s" colgado3

# --- 1. Síntesis ---------------------------------------------------------------------
construir() {   # construir NOMBRE PROGRAMA.hex TABLA.hex
  local n=$1 prog=$2 tab=$3
  yosys -q -l "$O/$n.yosys.log" -p "read_verilog $C1_DEFS $BASE_SRC; chparam -set MemFile \"$prog\" -set TablaFile \"$tab\" pochoco_soc; \
    synth_ice40 -top pochoco_soc -json $O/$n.json" || return 1
  nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed 1 --json "$O/$n.json" --pcf goboard.pcf \
    --asc "$O/$n.asc" -l "$O/$n.pnr.log" -q 2>/dev/null || return 1
  icepack "$O/$n.asc" "$O/$n.bin"
}
construir r3       "$O/c1.hex"         "$O/tabla.hex" &
construir r3_molde "$O/molde_prog.hex" "$O/molde_tabla512.hex" &
wait
for n in r3 r3_molde; do [ -s "$O/$n.bin" ] || { echo "FAIL: no se pudo construir $n"; exit 1; }; done

# --- 2, 4 y 5. icebram sobre el molde ------------------------------------------------
molde() {   # molde PROGRAMA.hex TABLA.hex SALIDA: icebram de las dos memorias e icepack
  icebram "$O/molde_prog.hex" "$1" < "$O/r3_molde.asc" | icebram "$O/molde_tabla512.hex" "$2" > "$O/$3.asc" && icepack "$O/$3.asc" "$O/$3.bin"
}
a=$(date +%s.%N); molde "$O/c1.hex" "$O/tabla.hex" r3_icebram; b=$(date +%s.%N)
echo "$a $b" | awk '{printf "%.2f\n", $2 - $1}' > "$O/icebram.tiempo"
a=$(date +%s.%N)
$PYTHON $TC/generar.py --apagada -o "$O/apagada" > /dev/null
molde "$O/c1.hex" "$O/apagada/c1_tabla.hex" r3_apagada
b=$(date +%s.%N)
echo "$a $b" | awk '{printf "%.2f\n", $2 - $1}' > "$O/apagada.tiempo"
molde "$O/colgado0.hex" "$O/tabla.hex" r3_colgado0
molde "$O/colgado3.hex" "$O/tabla.hex" r3_colgado3
icetime -d hx1k -P vq100 -p goboard.pcf -t "$O/r3.asc" 2>/dev/null | grep 'Total path delay' > "$O/r3.icetime"

# --- Series ----------------------------------------------------------------------------
$PYTHON - "$O/mano.csv" $NTICKS <<'PY'
import sys
sys.path[:0] = ["tools/c1", "ref", "ref/cotas"]
import cosim, series
series.escribir_csv(sys.argv[1], cosim.serie_fase_a(int(sys.argv[2])))
PY
MANO=$O/mano.csv
MOT=$(meta_ventana 250 $NTICKS)
META=data/practica_meta.csv

# --- Simulaciones desde el .asc -------------------------------------------------------
sim() {   # sim NOMBRE ASC SERIE NTICKS: bytes que lee la maestra por los pines, con el monitor de SB_WARMBOOT
  local n=$1 asc=$2 ser=$3 nt=$4
  local d=$O/sim_$n
  mkdir -p "$d"
  $PYTHON tools/chip_vlog.py "$asc" goboard.pcf -o "$d/chip.v" || return 1
  iverilog -g2012 -s tb_bitstream -s mon_warmboot -DNTICKS="$nt" -DPERIODO_NS=100000 "-DSERIE=\"$ser\"" "-DSALIDA=\"$d/bytes.csv\"" \
    -o "$d/sim" "$CELLS_SIM" "$d/chip.v" tb/tb_bitstream.sv tb/fondo/mon_warmboot.sv || return 1
  vvp -n "$d/sim" > "$d/tb.log"
  $PYTHON ref/market.py contabilizar "$d/bytes.csv" -o "$d/bitstream.csv" > /dev/null
}
sim r3_meta     "$O/r3.asc"          "$META" $NTICKS &
sim r3_mano     "$O/r3.asc"          "$MANO" $NTICKS &
sim r3_motor    "$O/r3.asc"          "$MOT"  $NTICKS &
sim r3_apagada  "$O/r3_apagada.asc"  "$MOT"  $NTICKS &
sim r3_colgado0 "$O/r3_colgado0.asc" "$MANO" 300 &
sim r3_colgado3 "$O/r3_colgado3.asc" "$MANO" $NTICKS &
wait
ref() { $PYTHON ref/c1/c1.py "$1" --nticks $NTICKS --periodo-ns 100000 -o "$O/$2" "${@:3}" > /dev/null; }
ref "$META" ref_meta.csv
ref "$MANO" ref_mano.csv
ref "$MOT"  ref_motor.csv
ref "$MOT"  ref_apagada.csv --tabla "$O/apagada/c1_tabla.hex"
ref "$MANO" ref_colgado3.csv --faltas 700-$NTICKS
$PYTHON ref/fondo.py "$MOT" --nticks $NTICKS --periodo-ns 100000 -o "$O/ref_banda40.csv" > /dev/null

# --- 6. Imagen múltiple ---------------------------------------------------------------------
multi() {   # multi IMAGEN0 SALIDA
  icemulti -v -p0 -o "$O/$2.bin" "$O/$1.bin" "$R0_BIN" > "$O/$2.icemulti.log" 2>&1
  $PYTHON tools/ver_multi.py --flash $FLASH "$O/$2.bin" "$O/$1.bin" "$R0_BIN" > "$O/$2.ver.txt" 2>&1
}
multi r3 r3_c1_multi; multi_ok=$?
multi r3_colgado0 r3_c1_falla_multi; falla_ok=$?
multi r3_apagada r3_c1_apagada_multi; apag_ok=$?

# --- Informe ---------------------------------------------------------------------------
resumen() {   # resumen NOMBRE
  local log=$O/$1.pnr.log
  echo "  $1: celdas $(grep 'ICESTORM_LC:' "$log" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'), BRAM $(grep 'ICESTORM_RAM:' "$log" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'), $(grep 'Max frequency for clock' "$log" | tail -1 | sed -E 's/.*: ([0-9.]+ MHz) \((PASS|FAIL).*/frecuencia maxima \1, \2 a 25 MHz/'), $(stat -c %s "$O/$1.bin") bytes, sha256 $(sha256sum "$O/$1.bin" | cut -d' ' -f1)"
}
comparar() {    # comparar NOMBRE REF ETIQUETA
  local d=$O/sim_$1
  if ! grep -q "Bits de MISO con X: 0" "$d/tb.log" 2>/dev/null; then echo "FAIL $3: MISO con X o la simulacion no corrio"
  elif cmp -s "$d/bitstream.csv" "$2"; then echo "PASS $3: $(($(wc -l < "$d/bitstream.csv") - 1)) ticks identicos a la referencia, patrimonio $(tail -1 "$d/bitstream.csv" | cut -d, -f6)"
  else echo "FAIL $3: el bitstream no decide igual que la referencia"; fi
}
sin_disparo() { # sin_disparo NOMBRE ETIQUETA
  if grep -q "^WARMBOOT nunca" "$O/sim_$1/tb.log"; then echo "PASS $2: SB_WARMBOOT no se dispara"
  else echo "FAIL $2: $(grep '^WARMBOOT' "$O/sim_$1/tb.log")"; fi
}

{
cabecera "Bitstream de R3 (C1 sobre el barrel con vigilante y la tabla de 512 palabras)" tools/c1/bitstreams.sh "make c1-bitstreams"
echo "nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed 1, goboard.pcf."
echo
echo "1. Sintesis"
for n in r3 r3_molde; do resumen $n; done
if grep -q "PASS at 25.00 MHz" "$O/r3.pnr.log"; then echo "PASS r3: cierra a 25 MHz (icetime: $(cat "$O/r3.icetime"))"; else echo "FAIL r3: no cierra a 25 MHz"; fi
echo
echo "2. icebram sobre el molde (programa y tabla), contra la sintesis directa"
if cmp -s "$O/r3.asc" "$O/r3_icebram.asc"; then echo "PASS r3: el .asc del molde con icebram es identico al de la sintesis directa ($(cat "$O/icebram.tiempo") s con icepack)"
elif cmp -s "$O/r3.bin" "$O/r3_icebram.bin"; then echo "PASS r3: el .bin del molde con icebram es identico al de la sintesis directa ($(cat "$O/icebram.tiempo") s con icepack)"
else echo "FAIL r3: el molde con icebram no da el bitstream de la sintesis directa"; fi
echo
echo "3. Criterio 8: bitstream simulado desde el .asc por los pines (Icarus, tb/tb_bitstream.sv), periodo de 0,1 ms"
comparar r3_meta  "$O/ref_meta.csv"  "R3, primeros $NTICKS ticks de la serie Meta"
comparar r3_mano  "$O/ref_mano.csv"  "R3, serie hecha a mano (apuesta en la fase A y candado)"
comparar r3_motor "$O/ref_motor.csv" "R3, ventana de la serie Meta con motor"
for s in meta mano motor; do sin_disparo r3_$s "R3, $s"; done
echo
echo "4. Politica apagada con icebram, sin sintetizar"
echo "  Palabras de la tabla que cambian: $(paste "$O/tabla.hex" "$O/apagada/c1_tabla.hex" | awk '$1 != $2' | wc -l)"
comparar r3_apagada "$O/ref_apagada.csv" "R3 con la politica apagada, ventana con motor, contra ref/c1/c1.py con esa tabla"
comparar r3_apagada "$O/ref_banda40.csv" "R3 con la politica apagada contra la banda 40 de R2 (ref/fondo.py)"
sin_disparo r3_apagada "R3 con la politica apagada"
echo "  Bytes en que C1 difiere de la banda 40 en esa ventana: $(paste -d, "$O/ref_motor.csv" "$O/ref_banda40.csv" | awk -F, 'NR > 1 && $3 != $9' | wc -l) de $NTICKS"
echo "  Tiempo de punta a punta (generar la tabla, icebram e icepack): $(cat "$O/apagada.tiempo") s"
echo
echo "5a. Vigilante dentro del bitstream: hilo 0 colgado en el tick 100 (programa puesto con icebram en el molde)"
linea=$(grep '^WARMBOOT' "$O/sim_r3_colgado0/tb.log")
echo "  $linea"
t=$(echo "$linea" | sed -n 's/.*t_ns=\([0-9]*\).*/\1/p')
if [ -n "$t" ]; then
  tx=$(( (t - 4000) / 100000 ))
  echo "  BOOT sube durante el periodo de la transaccion $tx (la primera es la 0). El programa no ve las 2 primeras: su tick 100 es la transaccion 101."
  if echo "$linea" | grep -q "s1s0=01 cs_n=1" && [ "$tx" = 105 ]; then
    echo "PASS el vigilante pide la imagen 01 con CS_n en alto, al terminar la transaccion 105: la quinta sin respuesta (101 a 105)"
  else echo "FAIL el disparo no es el esperado"; fi
else echo "FAIL el vigilante no se disparo"; fi
echo
echo "5b. Hilo 3 colgado en el tick 700: el hilo 0 sigue decidiendo, sin relevo"
comparar r3_colgado3 "$O/ref_colgado3.csv" "R3 con el hilo 3 colgado, contra la referencia con esa falla (un tick sostenido y despues la banda 40)"
sin_disparo r3_colgado3 "R3 con el hilo 3 colgado"
echo
echo "6. Imagen multiple: icemulti -p0, imagen 0 R3 e imagen 1 R0 ($R0_BIN)"
sed 's/^/  /' "$O/r3_c1_multi.ver.txt"
if [ $multi_ok = 0 ]; then echo "PASS imagen multiple correcta y cabe en la flash de $FLASH bytes"; else echo "FAIL imagen multiple"; fi
if [ $falla_ok = 0 ] && [ $apag_ok = 0 ]; then echo "PASS las imagenes multiples de la falla (hilo 0 colgado en el tick 100) y de la politica apagada tambien"; else echo "FAIL imagenes multiples de la falla o de la politica apagada"; fi
echo
echo "Archivos:"
for f in r3 r3_c1_multi r3_c1_falla_multi r3_apagada r3_c1_apagada_multi r3_molde; do echo "  $f.bin: $(stat -c %s "$O/$f.bin") bytes, sha256 $(sha256sum "$O/$f.bin" | cut -d' ' -f1)"; done
} | tee "$SALIDA"

if [ "${GUARDAR:-0}" = 1 ] && ! grep -q "^FAIL" "$SALIDA"; then
  cp "$O/r3.bin" bitstreams/r3_c1.bin
  cp "$O/r3_c1_multi.bin" bitstreams/r3_c1_multi.bin
  cp "$O/r3_c1_falla_multi.bin" bitstreams/r3_c1_falla_multi.bin
  cp "$O/r3_c1_apagada_multi.bin" bitstreams/r3_c1_apagada_multi.bin
  gzip -9 -n -c "$O/r3_molde.asc" > $M/r3_molde.asc.gz
  cp "$O/molde_tabla512.hex" $M/
  ( cd bitstreams
    grep -v -E '  (r3_c1.*\.bin|moldes/r3_molde\.asc\.gz|moldes/molde_tabla512\.hex)$' SHA256SUMS > SHA256SUMS.nuevo
    sha256sum r3_c1.bin r3_c1_multi.bin r3_c1_falla_multi.bin r3_c1_apagada_multi.bin moldes/r3_molde.asc.gz moldes/molde_tabla512.hex >> SHA256SUMS.nuevo
    mv SHA256SUMS.nuevo SHA256SUMS )
  echo "Guardados en bitstreams/: r3_c1.bin, r3_c1_multi.bin, r3_c1_falla_multi.bin, r3_c1_apagada_multi.bin y el molde en bitstreams/moldes/"
fi
cierre "$SALIDA"
