#!/usr/bin/env bash
# molde_cotas.sh: bitstreams R0, R1 y R2 con la regla de cotas (decisión T133),
# puestos con icebram sobre los moldes guardados, sin sintetizar.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El hardware de los tres peldaños no cambia: cambian el programa (y en R1 y R2
# la tabla). Los moldes de bitstreams/moldes/ son los .asc de los bitstreams que
# pasaron sus puertas, con las memorias llenas de un patrón; icebram reemplaza el
# patrón sin tocar nada más.
#
#   0. Control: los moldes con los programas anteriores (sw/trade.hex, sw/fondo.s
#      y sw/fondo_tabla.hex del commit BASE, por defecto c794834) dan byte por
#      byte los .bin de bitstreams/ (r0_base_max_media.bin, r1_fondo.bin,
#      r2_fondo_vigilante.bin y r2_multi.bin). Eso muestra que el molde es el
#      hardware que pasó las puertas.
#   1. Con los programas nuevos: r0_cotas.bin, r1_cotas.bin, r2_cotas.bin y la
#      imagen múltiple r2_cotas_multi.bin (imagen 0 R2, imagen 1 R0), revisada con
#      tools/ver_multi.py. Se mide el tiempo de icebram e icepack.
#   2. Criterio 8: los tres .asc simulados por los pines (tb/tb_bitstream.sv sin
#      modificar, Icarus, 0,1 ms) con dos series: los primeros 2000 ticks de la
#      serie Meta (lo que corre el testbench oficial por defecto) y una ventana
#      de 2000 ticks normalizada que toca 100 y 255 (meta_ventana 2775). R0 contra
#      ref/trader.py; R1 y R2 contra ref/fondo.py. En R2, SB_WARMBOOT no se dispara.
#   3. Vigilante dentro del bitstream de R2: programa con el hilo 0 colgado en el
#      tick 100 (variante cuelgue_sup:100) puesto con icebram; BOOT tiene que
#      subir con S1 S0 = 01 y CS_n en alto en la quinta transacción sin respuesta.
#
# Los productos quedan en build/fondo/molde_cotas/. No toca bitstreams/.
#
# Uso: tools/fondo/molde_cotas.sh   Resultado en docs/mediciones/fondo/molde_cotas.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"
O=build/fondo/molde_cotas
SALIDA=docs/mediciones/fondo/molde_cotas.txt
M=bitstreams/moldes
BASE=${BASE:-c794834}
NTICKS=${NTICKS:-2000}
FLASH=131072
rm -rf "$O"; mkdir -p "$O/viejo"

completar() {   # completar ENTRADA.hex SALIDA.hex: 512 palabras, como exige icebram
  $PYTHON - "$1" "$2" <<'PY'
import sys
palabras = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("//") and not l.startswith("@")]
assert len(palabras) <= 512, len(palabras)
palabras += ["00000000"] * (512 - len(palabras))
open(sys.argv[2], "w", newline="\n").write("\n".join(palabras) + "\n")
PY
}
for r in r0 r1 r2; do zcat "$M/${r}_molde.asc.gz" > "$O/${r}_molde.asc"; done

# --- 0. Control con los programas anteriores ------------------------------------------
git show "$BASE:sw/trade.hex" > "$O/viejo/trade.hex"
git show "$BASE:sw/fondo.s" > "$O/viejo/fondo.s"
git show "$BASE:sw/fondo_tabla.hex" > "$O/viejo/tabla.hex"
$PYTHON tools/pochoasm.py "$O/viejo/fondo.s" -o "$O/viejo/fondo_asm.hex" > /dev/null && completar "$O/viejo/fondo_asm.hex" "$O/viejo/fondo.hex"
icebram "$M/molde_prog_r0.hex" "$O/viejo/trade.hex" < "$O/r0_molde.asc" > "$O/viejo/r0.asc" && icepack "$O/viejo/r0.asc" "$O/viejo/r0.bin"
for r in r1 r2; do
  icebram "$M/molde_prog.hex" "$O/viejo/fondo.hex" < "$O/${r}_molde.asc" | icebram "$M/molde_tabla.hex" "$O/viejo/tabla.hex" > "$O/viejo/$r.asc" \
    && icepack "$O/viejo/$r.asc" "$O/viejo/$r.bin"
done
icemulti -v -p0 -o "$O/viejo/r2_multi.bin" "$O/viejo/r2.bin" "$O/viejo/r0.bin" > /dev/null 2>&1

# --- 1. Programas nuevos ------------------------------------------------------------
$PYTHON tools/pochoasm.py sw/fondo.s -o "$O/fondo_asm.hex" > /dev/null || { echo "FAIL: no ensambla"; exit 1; }
completar "$O/fondo_asm.hex" "$O/fondo.hex"
cp "$TABLA_HEX" "$O/tabla.hex"
a=$(date +%s.%N)
icebram "$M/molde_prog_r0.hex" sw/trade.hex < "$O/r0_molde.asc" > "$O/r0_cotas.asc" && icepack "$O/r0_cotas.asc" "$O/r0_cotas.bin"
for r in r1 r2; do
  icebram "$M/molde_prog.hex" "$O/fondo.hex" < "$O/${r}_molde.asc" | icebram "$M/molde_tabla.hex" "$O/tabla.hex" > "$O/${r}_cotas.asc" \
    && icepack "$O/${r}_cotas.asc" "$O/${r}_cotas.bin"
done
b=$(date +%s.%N)
icemulti -v -p0 -o "$O/r2_cotas_multi.bin" "$O/r2_cotas.bin" "$O/r0_cotas.bin" > "$O/icemulti.log" 2>&1
$PYTHON tools/ver_multi.py --flash $FLASH "$O/r2_cotas_multi.bin" "$O/r2_cotas.bin" "$O/r0_cotas.bin" > "$O/ver_multi.txt" 2>&1; multi_ok=$?
$PYTHON tools/fondo/variante.py cuelgue_sup:100 -o "$O/colgado.s"
$PYTHON tools/pochoasm.py "$O/colgado.s" -o "$O/colgado_asm.hex" > /dev/null && completar "$O/colgado_asm.hex" "$O/colgado.hex"
icebram "$M/molde_prog.hex" "$O/colgado.hex" < "$O/r2_molde.asc" | icebram "$M/molde_tabla.hex" "$O/tabla.hex" > "$O/r2_colgado.asc"

# --- 2 y 3. Simulaciones desde el .asc --------------------------------------------
sim() {   # sim NOMBRE ASC SERIE NTICKS [mon]
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
VEN=$(meta_ventana 2775 $NTICKS)
META=data/practica_meta.csv
sim r0_meta "$O/r0_cotas.asc" "$META" $NTICKS &
sim r0_ven  "$O/r0_cotas.asc" "$VEN"  $NTICKS &
sim r1_meta "$O/r1_cotas.asc" "$META" $NTICKS &
sim r1_ven  "$O/r1_cotas.asc" "$VEN"  $NTICKS &
wait
sim r2_meta "$O/r2_cotas.asc" "$META" $NTICKS mon &
sim r2_ven  "$O/r2_cotas.asc" "$VEN"  $NTICKS mon &
sim r2_colgado "$O/r2_colgado.asc" "$VEN" 300 mon &
wait
$PYTHON ref/trader.py "$META" --nticks $NTICKS --periodo-ns 100000 -o "$O/ref_r0_meta.csv" > /dev/null
$PYTHON ref/trader.py "$VEN" --nticks $NTICKS --periodo-ns 100000 -o "$O/ref_r0_ven.csv" > /dev/null
$PYTHON ref/fondo.py "$META" --nticks $NTICKS --periodo-ns 100000 -o "$O/ref_meta.csv" > /dev/null
$PYTHON ref/fondo.py "$VEN" --nticks $NTICKS --periodo-ns 100000 -o "$O/ref_ven.csv" > /dev/null

comparar() {   # comparar NOMBRE REF ETIQUETA
  local d=$O/sim_$1
  if ! grep -q "Bits de MISO con X: 0" "$d/tb.log" 2>/dev/null; then echo "FAIL $3: MISO con X o la simulacion no corrio"
  elif cmp -s "$d/bitstream.csv" "$2"; then echo "PASS $3: $(($(wc -l < "$d/bitstream.csv") - 1)) ticks identicos a la referencia, patrimonio $(tail -1 "$d/bitstream.csv" | cut -d, -f6)"
  else echo "FAIL $3: el bitstream no decide igual que la referencia"; fi
}
sin_disparo() {
  if grep -q "^WARMBOOT nunca" "$O/sim_$1/tb.log"; then echo "PASS $2: SB_WARMBOOT no se dispara"
  else echo "FAIL $2: $(grep '^WARMBOOT' "$O/sim_$1/tb.log")"; fi
}
igual() {   # igual A B ETIQUETA
  if cmp -s "$1" "$2"; then echo "PASS $3: identico byte a byte ($(sha256sum "$1" | cut -c1-16)...)"; else echo "FAIL $3: distinto"; fi
}
{
echo "Bitstreams R0, R1 y R2 con la regla de cotas, puestos con icebram sobre los moldes"
echo "Generado por tools/fondo/molde_cotas.sh. No editar a mano."
echo
versiones
echo "Commit: $(git rev-parse --short HEAD). Programas: sw/trade.s y sw/fondo.s (sha256 $(sha256sum sw/fondo.s | cut -c1-16)...), tabla $TABLA_HEX."
echo
echo "0. Control: los moldes con los programas del commit $BASE dan los bitstreams guardados"
igual "$O/viejo/r0.bin" bitstreams/r0_base_max_media.bin "R0 (sw/trade.hex anterior) contra bitstreams/r0_base_max_media.bin"
igual "$O/viejo/r1.bin" bitstreams/r1_fondo.bin "R1 (fondo anterior) contra bitstreams/r1_fondo.bin"
igual "$O/viejo/r2.bin" bitstreams/r2_fondo_vigilante.bin "R2 (fondo anterior) contra bitstreams/r2_fondo_vigilante.bin"
igual "$O/viejo/r2_multi.bin" bitstreams/r2_multi.bin "imagen multiple anterior contra bitstreams/r2_multi.bin"
echo
echo "1. Bitstreams nuevos (icebram e icepack de los tres: $(echo "$a $b" | awk '{printf "%.2f", $2 - $1}') s)"
for f in r0_cotas r1_cotas r2_cotas r2_cotas_multi; do echo "  $f.bin: $(stat -c %s "$O/$f.bin") bytes, sha256 $(sha256sum "$O/$f.bin" | cut -d' ' -f1)"; done
for r in r0 r1 r2; do echo "  lineas del .asc que cambian respecto del anterior en $r: $(diff "$O/viejo/$r.asc" "$O/${r}_cotas.asc" | grep -c '^>')"; done
sed 's/^/  /' "$O/ver_multi.txt"
if [ $multi_ok = 0 ]; then echo "PASS imagen multiple correcta (imagen 0 R2, imagen 1 R0) y cabe en la flash de $FLASH bytes"; else echo "FAIL imagen multiple"; fi
echo
echo "2. Criterio 8: bitstream simulado desde el .asc por los pines (Icarus, tb/tb_bitstream.sv), periodo de 0,1 ms"
comparar r0_meta "$O/ref_r0_meta.csv" "R0, primeros $NTICKS ticks de la serie Meta, contra ref/trader.py"
comparar r0_ven  "$O/ref_r0_ven.csv"  "R0, ventana normalizada de la serie Meta (toca 100 y 255), contra ref/trader.py"
comparar r1_meta "$O/ref_meta.csv"    "R1, primeros $NTICKS ticks de la serie Meta"
comparar r1_ven  "$O/ref_ven.csv"     "R1, ventana normalizada"
comparar r2_meta "$O/ref_meta.csv"    "R2, primeros $NTICKS ticks de la serie Meta"
comparar r2_ven  "$O/ref_ven.csv"     "R2, ventana normalizada"
sin_disparo r2_meta "R2, serie Meta"
sin_disparo r2_ven  "R2, ventana normalizada"
if cmp -s <(cut -d, -f3 "$O/ref_r0_ven.csv") <(cut -d, -f3 "$O/ref_ven.csv"); then echo "PASS R0 y R1 deciden los mismos bytes en la ventana normalizada"; else echo "FAIL R0 y R1 deciden distinto"; fi
echo
echo "3. Vigilante dentro del bitstream de R2: hilo 0 colgado en el tick 100"
linea=$(grep '^WARMBOOT' "$O/sim_r2_colgado/tb.log")
echo "  $linea"
t=$(echo "$linea" | sed -n 's/.*t_ns=\([0-9]*\).*/\1/p')
if [ -n "$t" ]; then
  tx=$(( (t - 4000) / 100000 ))
  if echo "$linea" | grep -q "s1s0=01 cs_n=1" && [ "$tx" = 105 ]; then
    echo "PASS el vigilante pide la imagen 01 con CS_n en alto al terminar la transaccion 105: la quinta sin respuesta (101 a 105)"
  else echo "FAIL el disparo no es el esperado (transaccion $tx)"; fi
else echo "FAIL el vigilante no se disparo"; fi
} | tee "$SALIDA"
cierre "$SALIDA"
