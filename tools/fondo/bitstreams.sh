#!/usr/bin/env bash
# bitstreams.sh: construye los bitstreams R1 y R2 del fondo en un chip, los
# simula desde su .asc y prueba de punta a punta el cambio de la tabla y del
# programa con icebram, el vigilante dentro del bitstream y la imagen múltiple.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   R1  barrel con emad y devk y la tabla de parámetros, con sw/fondo.s
#   R2  R1 más el vigilante y SB_WARMBOOT. Con icemulti se junta con la imagen
#       de respaldo, que es R0 (bitstreams/r0_base_max_media.bin, sin tocar)
#
# Pasos:
#   1. Cuatro síntesis con yosys y nextpnr (semilla 1): R1 y R2 con el programa
#      y la tabla de verdad, y un molde de cada uno con las dos memorias llenas
#      de un patrón al azar (icebram -g).
#   2. icebram sobre el molde: reemplaza el patrón por el programa y por la
#      tabla. El .asc que resulta tiene que ser idéntico al de la síntesis
#      directa. Se mide cuánto demora.
#   3. Criterio 8 de la puerta: R1 y R2 simulados desde su .asc por los pines,
#      con la maestra de tb/tb_bitstream.sv sin modificar, 2000 ticks contra
#      ref/fondo.py. En R2 se mira además que SB_WARMBOOT no se dispare.
#   4. Cambio de la tabla sin sintetizar: una tabla con otros parámetros se pone
#      con icebram en el molde de R1 (junto con el programa). El bitstream que
#      resulta, simulado desde su .asc, tiene que decidir como ref/fondo.py con
#      esos parámetros. Se mide el tiempo de punta a punta: generar la tabla,
#      icebram e icepack. Se deja constancia además de lo que pasa si se intenta
#      sobre el .asc ya construido con la tabla de verdad: icebram se niega,
#      porque esa tabla tiene muchos bits iguales en todas sus palabras y no
#      puede ubicarla. Por eso el molde se guarda junto al bitstream.
#   5. Vigilante dentro del bitstream: en R2 se cambia el programa con icebram
#      por uno en que el supervisor se cuelga en el tick 100. Simulado desde el
#      .asc, BOOT tiene que subir con S1 S0 = 01 y CS_n en alto, después del
#      quinto precio sin respuesta.
#   6. icemulti: imagen 0 R2, imagen 1 R0. tools/ver_multi.py revisa los
#      vectores de arranque, que las dos imágenes estén copiadas sin cambios y
#      que quepan en la flash de la Go Board.
#
# Los productos quedan en build/fondo/bitstreams/. Con GUARDAR=1 copia a
# bitstreams/ los .bin de R1 y R2, la imagen múltiple y los dos moldes (el
# .asc comprimido y sus patrones, que son lo que icebram necesita para cambiar
# la tabla o el programa más adelante), y actualiza SHA256SUMS. No programa la
# placa.
#
# Uso: tools/fondo/bitstreams.sh   (o make fondo-bitstreams)
# Resultado en docs/mediciones/fondo/bitstreams.txt. Unos 25 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=build/fondo/bitstreams
SALIDA=docs/mediciones/fondo/bitstreams.txt
NTICKS=${NTICKS:-2000}
R0_BIN=bitstreams/r0_base_max_media.bin
FLASH=131072                       # flash de la Go Board: 1 Mbit
OTRA="G3_ENTRA=-80 W1_INI=5 W3_INI=6 W1_MAX=9 W3_MAX=10 W1_MIN=1 W3_MIN=2 VENTANA=256 PLAZO=6"
rm -rf "$O"; mkdir -p "$O"

# completar ENTRADA.hex SALIDA.hex: deja el programa con las 512 palabras, que
# es lo que icebram exige (los dos archivos del mismo tamaño)
completar() {
  $PYTHON - "$1" "$2" <<'PY'
import sys
palabras = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("//") and not l.startswith("@")]
assert len(palabras) <= 512, len(palabras)
palabras += ["00000000"] * (512 - len(palabras))
open(sys.argv[2], "w", newline="\n").write("\n".join(palabras) + "\n")
PY
}

# --- Memorias ---------------------------------------------------------------------
$PYTHON tools/pochoasm.py sw/fondo.s -o "$O/fondo_asm.hex" > /dev/null || { echo "FAIL: no ensambla"; exit 1; }
completar "$O/fondo_asm.hex" "$O/fondo.hex"
cp "$TABLA_HEX" "$O/tabla.hex"
icebram -g -s 1 32 512 > "$O/molde_prog.hex"
icebram -g -s 2 16 256 > "$O/molde_tabla.hex"
$PYTHON $TF/variante.py cuelgue_sup:100 -o "$O/colgado.s"
$PYTHON tools/pochoasm.py "$O/colgado.s" -o "$O/colgado_asm.hex" > /dev/null && completar "$O/colgado_asm.hex" "$O/colgado.hex"
PARAMS=$(for q in $OTRA; do echo -n "--param $q "; done)

# --- 1. Síntesis ---------------------------------------------------------------------
# construir NOMBRE DEFS PROGRAMA.hex TABLA.hex
construir() {
  local n=$1 defs=$2 prog=$3 tab=$4
  yosys -q -l "$O/$n.yosys.log" -p "read_verilog $defs $BASE_SRC; chparam -set MemFile \"$prog\" -set TablaFile \"$tab\" pochoco_soc; \
    synth_ice40 -top pochoco_soc -json $O/$n.json" || return 1
  nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed 1 --json "$O/$n.json" --pcf goboard.pcf \
    --asc "$O/$n.asc" -l "$O/$n.pnr.log" -q 2>/dev/null || return 1
  icepack "$O/$n.asc" "$O/$n.bin"
}
construir r1       "$R1_DEFS" "$O/fondo.hex"      "$O/tabla.hex" &
construir r2       "$R2_DEFS" "$O/fondo.hex"      "$O/tabla.hex" &
construir r1_molde "$R1_DEFS" "$O/molde_prog.hex" "$O/molde_tabla.hex" &
construir r2_molde "$R2_DEFS" "$O/molde_prog.hex" "$O/molde_tabla.hex" &
wait
for n in r1 r2 r1_molde r2_molde; do [ -s "$O/$n.bin" ] || { echo "FAIL: no se pudo construir $n"; exit 1; }; done

# --- 2. icebram sobre el molde -----------------------------------------------------
for r in r1 r2; do
  a=$(date +%s.%N)
  icebram "$O/molde_prog.hex" "$O/fondo.hex" < "$O/${r}_molde.asc" | icebram "$O/molde_tabla.hex" "$O/tabla.hex" > "$O/${r}_icebram.asc" \
    && icepack "$O/${r}_icebram.asc" "$O/${r}_icebram.bin"
  b=$(date +%s.%N)
  echo "$a $b" | awk '{printf "%.2f\n", $2 - $1}' > "$O/${r}_icebram.tiempo"
done

# --- 4. Otra tabla, sin sintetizar ----------------------------------------------------
a=$(date +%s.%N)
$PYTHON ref/fondo.py $PARAMS --tabla-hex "$O/otra_tabla.hex"
icebram "$O/molde_prog.hex" "$O/fondo.hex" < "$O/r1_molde.asc" | icebram "$O/molde_tabla.hex" "$O/otra_tabla.hex" > "$O/r1_otra.asc" \
  && icepack "$O/r1_otra.asc" "$O/r1_otra.bin"
b=$(date +%s.%N)
echo "$a $b" | awk '{printf "%.2f\n", $2 - $1}' > "$O/otra.tiempo"
icebram "$O/tabla.hex" "$O/otra_tabla.hex" < "$O/r1.asc" > "$O/r1_otra_directo.asc" 2> "$O/directo.err"; echo $? > "$O/directo.rc"

# --- 5. Programa con el supervisor colgado, en R2 ---------------------------------------
icebram "$O/molde_prog.hex" "$O/colgado.hex" < "$O/r2_molde.asc" | icebram "$O/molde_tabla.hex" "$O/tabla.hex" > "$O/r2_colgado.asc"

# --- Simulaciones desde el .asc -------------------------------------------------------
# sim NOMBRE ASC SERIE NTICKS [mon]: bytes que lee la maestra por los pines
sim() {
  local n=$1 asc=$2 ser=$3 nt=$4 mon=${5:-}
  local d=$O/sim_$n tops="-s tb_bitstream" fuentes="tb/tb_bitstream.sv"
  mkdir -p "$d"
  $PYTHON tools/chip_vlog.py "$asc" goboard.pcf -o "$d/chip.v" || return 1
  [ -n "$mon" ] && { tops="$tops -s mon_warmboot"; fuentes="$fuentes tb/fondo/mon_warmboot.sv"; }
  iverilog -g2012 $tops -DNTICKS="$nt" -DPERIODO_NS=100000 "-DSERIE=\"$ser\"" "-DSALIDA=\"$d/bytes.csv\"" \
    -o "$d/sim" "$CELLS_SIM" "$d/chip.v" $fuentes || return 1
  vvp -n "$d/sim" > "$d/tb.log"
  $PYTHON ref/market.py contabilizar "$d/bytes.csv" -o "$d/bitstream.csv" > /dev/null
}
REV=$(serie reversion 1 $NTICKS)
sim r1         "$O/r1.asc"         tb/practica.csv $NTICKS &
sim r2         "$O/r2.asc"         tb/practica.csv $NTICKS mon &
sim r1_rev     "$O/r1.asc"         "$REV"          $NTICKS &
sim r2_rev     "$O/r2.asc"         "$REV"          $NTICKS mon &
sim r1_otra    "$O/r1_otra.asc"    "$REV"          $NTICKS &
sim r2_colgado "$O/r2_colgado.asc" tb/practica.csv 300 mon &
wait
$PYTHON ref/fondo.py tb/practica.csv --nticks $NTICKS --periodo-ns 100000 -o "$O/ref_practica.csv" > /dev/null
$PYTHON ref/fondo.py "$REV" --nticks $NTICKS --periodo-ns 100000 -o "$O/ref_rev.csv" > /dev/null
$PYTHON ref/fondo.py "$REV" --nticks $NTICKS --periodo-ns 100000 $PARAMS -o "$O/ref_otra.csv" > /dev/null

# --- 6. Imagen múltiple ---------------------------------------------------------------------
icemulti -v -p0 -o "$O/r2_multi.bin" "$O/r2.bin" "$R0_BIN" > "$O/icemulti.log" 2>&1
$PYTHON tools/ver_multi.py --flash $FLASH "$O/r2_multi.bin" "$O/r2.bin" "$R0_BIN" > "$O/ver_multi.txt" 2>&1; multi_ok=$?

# --- Informe ---------------------------------------------------------------------------
resumen() {   # resumen NOMBRE
  local log=$O/$1.pnr.log
  echo "  $1: celdas $(grep 'ICESTORM_LC:' "$log" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'), BRAM $(grep 'ICESTORM_RAM:' "$log" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'), $(grep 'Max frequency for clock' "$log" | tail -1 | sed -E 's/.*: ([0-9.]+ MHz) \((PASS|FAIL).*/frecuencia maxima \1, \2 a 25 MHz/'), $(stat -c %s "$O/$1.bin") bytes, sha256 $(sha256sum "$O/$1.bin" | cut -d' ' -f1)"
}
# comparar NOMBRE REF ETIQUETA
comparar() {
  local d=$O/sim_$1
  if ! grep -q "Bits de MISO con X: 0" "$d/tb.log" 2>/dev/null; then echo "FAIL $3: MISO con X o la simulacion no corrio"
  elif cmp -s "$d/bitstream.csv" "$2"; then echo "PASS $3: $(($(wc -l < "$d/bitstream.csv") - 1)) ticks identicos a la referencia, patrimonio $(tail -1 "$d/bitstream.csv" | cut -d, -f6)"
  else echo "FAIL $3: el bitstream no decide igual que la referencia"; fi
}
sin_disparo() {   # sin_disparo NOMBRE ETIQUETA
  if grep -q "^WARMBOOT nunca" "$O/sim_$1/tb.log"; then echo "PASS $2: SB_WARMBOOT no se dispara"
  else echo "FAIL $2: $(grep '^WARMBOOT' "$O/sim_$1/tb.log")"; fi
}

{
cabecera "Bitstreams R1 y R2 del fondo en un chip" tools/fondo/bitstreams.sh "make fondo-bitstreams" | sed "s|^Hardware (.*|R1: $R1_DEFS\nR2: $R2_DEFS|"
echo "nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed 1, goboard.pcf."
echo
echo "1. Sintesis"
for n in r1 r2 r1_molde r2_molde; do resumen $n; done
for n in r1 r2; do
  if grep -q "PASS at 25.00 MHz" "$O/$n.pnr.log"; then echo "PASS $n: cierra a 25 MHz"; else echo "FAIL $n: no cierra a 25 MHz"; fi
done
echo
echo "2. icebram sobre el molde (programa y tabla), contra la sintesis directa"
for r in r1 r2; do
  if cmp -s "$O/$r.asc" "$O/${r}_icebram.asc"; then echo "PASS $r: el .asc del molde con icebram es identico al de la sintesis directa ($(cat "$O/${r}_icebram.tiempo") s con icepack)"
  elif cmp -s "$O/$r.bin" "$O/${r}_icebram.bin"; then echo "PASS $r: el .bin del molde con icebram es identico al de la sintesis directa ($(cat "$O/${r}_icebram.tiempo") s con icepack)"
  else echo "FAIL $r: el molde con icebram no da el bitstream de la sintesis directa"; fi
done
echo
echo "3. Criterio 8: bitstream simulado desde el .asc por los pines (Icarus, tb/tb_bitstream.sv), periodo de 0,1 ms"
comparar r1     "$O/ref_practica.csv" "R1, serie de practica"
comparar r1_rev "$O/ref_rev.csv"      "R1, serie de reversion"
comparar r2     "$O/ref_practica.csv" "R2, serie de practica"
comparar r2_rev "$O/ref_rev.csv"      "R2, serie de reversion"
sin_disparo r2     "R2, serie de practica"
sin_disparo r2_rev "R2, serie de reversion"
echo
echo "4. Cambio de la tabla con icebram, sin sintetizar"
echo "  Parametros cambiados: $OTRA"
echo "  Valores de 16 bits distintos entre las dos tablas: $(paste "$O/tabla.hex" "$O/otra_tabla.hex" | awk '$1 != $2' | wc -l)"
if [ "$(cat "$O/directo.rc")" != 0 ] || [ ! -s "$O/r1_otra_directo.asc" ]; then
  echo "  Sobre el .asc ya construido con la tabla de verdad icebram se niega: $(head -1 "$O/directo.err")"
  echo "  (la tabla de verdad repite bits entre palabras; el cambio se hace siempre desde el molde)"
elif cmp -s "$O/r1_otra.asc" "$O/r1_otra_directo.asc"; then echo "  Sobre el .asc ya construido el resultado es el mismo que desde el molde"
else echo "FAIL sobre el .asc ya construido icebram entrega otro resultado que desde el molde"; fi
echo "  Lineas del .asc que cambian respecto de R1: $(diff "$O/r1.asc" "$O/r1_otra.asc" | grep -c '^>')"
comparar r1_otra "$O/ref_otra.csv" "R1 con la otra tabla, serie de reversion, contra ref/fondo.py con esos parametros"
echo "  Bytes en que la referencia con la otra tabla difiere de la referencia con la tabla original: $(paste -d, "$O/ref_rev.csv" "$O/ref_otra.csv" | awk -F, 'NR > 1 && $3 != $9' | wc -l) de $NTICKS"
echo "  Tiempo de punta a punta (generar la tabla, icebram e icepack): $(cat "$O/otra.tiempo") s"
echo "  sha256 de r1_otra.bin: $(sha256sum "$O/r1_otra.bin" | cut -d' ' -f1)"
echo
echo "5. Vigilante dentro del bitstream de R2: supervisor colgado en el tick 100 (programa puesto con icebram en el molde de R2)"
linea=$(grep '^WARMBOOT' "$O/sim_r2_colgado/tb.log")
echo "  $linea"
t=$(echo "$linea" | sed -n 's/.*t_ns=\([0-9]*\).*/\1/p')
if [ -n "$t" ]; then
  tx=$(( (t - 4000) / 100000 ))
  echo "  BOOT sube durante el periodo de la transaccion $tx (la primera es la 0). El programa no ve las 2 primeras: su tick 100 es la transaccion 101."
  if echo "$linea" | grep -q "s1s0=01 cs_n=1" && [ "$tx" = 105 ]; then
    echo "PASS el vigilante pide la imagen 01 con CS_n en alto, al terminar la transaccion 105: la quinta sin respuesta (101 a 105)"
  else echo "FAIL el disparo no es el esperado"; fi
else echo "FAIL el vigilante no se disparo"; fi
$PYTHON - "$O/sim_r2_colgado/bytes.csv" "$O/ref_practica.csv" <<'PY'
import csv, sys
tb = list(csv.reader(open(sys.argv[1])))[1:]
ref = list(csv.reader(open(sys.argv[2])))[1:]
# la maestra lee en la transacción n lo decidido con el precio n-1: hasta la 101 inclusive son bytes del fondo sano
iguales = all(int(a[2], 16) == int(b[2], 16) for a, b in zip(tb[:102], ref[:102]))
quieto = len({a[2] for a in tb[101:]}) == 1
print(("PASS" if iguales and quieto else "FAIL") + " bytes: iguales a la referencia hasta la transaccion 101, y despues se repite el ultimo "
      f"({tb[101][2]}); en el bitstream simulado no hay reconfiguracion, asi que el byte no cambia")
PY
echo
echo "6. Imagen multiple: icemulti -p0, imagen 0 R2 e imagen 1 R0 ($R0_BIN)"
sed 's/^/  /' "$O/ver_multi.txt"
if [ $multi_ok = 0 ]; then echo "PASS imagen multiple correcta y cabe en la flash de $FLASH bytes"; else echo "FAIL imagen multiple"; fi
} | tee "$SALIDA"

if [ "${GUARDAR:-0}" = 1 ] && ! grep -q "^FAIL" "$SALIDA"; then
  cp "$O/r1.bin" bitstreams/r1_fondo.bin
  cp "$O/r2.bin" bitstreams/r2_fondo_vigilante.bin
  cp "$O/r2_multi.bin" bitstreams/r2_multi.bin
  mkdir -p bitstreams/moldes
  gzip -9 -n -c "$O/r1_molde.asc" > bitstreams/moldes/r1_molde.asc.gz
  gzip -9 -n -c "$O/r2_molde.asc" > bitstreams/moldes/r2_molde.asc.gz
  cp "$O/molde_prog.hex" "$O/molde_tabla.hex" bitstreams/moldes/
  ( cd bitstreams && sha256sum *.bin moldes/* > SHA256SUMS )
  echo "Guardados en bitstreams/: r1_fondo.bin, r2_fondo_vigilante.bin, r2_multi.bin y los moldes en bitstreams/moldes/"
fi
cierre "$SALIDA"
