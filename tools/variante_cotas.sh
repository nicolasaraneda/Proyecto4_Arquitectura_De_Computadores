#!/usr/bin/env bash
# variante_cotas.sh: puerta de simulación de R0 con una variante de la regla de cotas.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Las variantes de contingencia (docs/cotas.md) no reemplazan al programa oficial. Para
# verificarlas con las mismas pruebas que R0, este script arma una copia de trabajo del
# commit actual en build/variante_NOMBRE/, pone ahí el programa de la variante como
# sw/trade.s y la regla de la variante como trader.Oficial, y corre:
#   testbench oficial, make equiv, make equiv-gemelo, make fases, make estres, la
#   verificación exhaustiva, el bitstream desde el molde de R0 (icebram) y su simulación
#   por los pines con la serie anterior y con una ventana de la serie Meta.
# El bitstream queda en bitstreams/variantes/r0_NOMBRE.bin y el registro en
# docs/mediciones/variantes/r0_NOMBRE.txt.
#
# Uso: tools/variante_cotas.sh NOMBRE PROGRAMA.s 'ARGUMENTOS DE Cotas'
#   tools/variante_cotas.sh p20b70 sw/variantes/trade_p20b70.s '"parte", k=20, banda=70'
set -uo pipefail
RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$RAIZ"
NOMBRE=$1; PROG=$2; ARGS=$3
W=build/variante_$NOMBRE
SALIDA=docs/mediciones/variantes/r0_$NOMBRE.txt
mkdir -p docs/mediciones/variantes bitstreams/variantes
rm -rf "$W"
git worktree prune
git worktree add -q --detach "$W" HEAD
cp "$PROG" "$W/sw/trade.s"
sed -i "s|super().__init__(\"espera\", banda=60)|super().__init__($ARGS)|" "$W/ref/trader.py"
grep -q "super().__init__($ARGS)" "$W/ref/trader.py" || { echo "FAIL: no se pudo poner la variante en ref/trader.py"; exit 1; }
cd "$W"
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex > /dev/null
# Ventana de la serie Meta que toca los dos extremos (ticks 15 600 a 17 599, normalizada)
mkdir -p build/cotas
python3 - <<'PY'
import sys; sys.path.insert(0, "ref"); sys.path.insert(0, "ref/cotas")
import comun, cotas
v = comun.normalizar(cotas.leer("data/practica_meta.csv")[15600:17600])
open("build/cotas/meta_ventana.csv", "w").write("tick,price\n" + "".join(f"{i},{x}\n" for i, x in enumerate(v)))
PY
f=0
paso() { echo "== $*"; if "$@" > build/paso.log 2>&1; then echo "PASS: $*"; else echo "FAIL: $*"; f=$((f+1)); fi;
         grep -E '^(PASS|FAIL)|Peor caso|Patrimonio|Testbenchs|Distintas|periodo .*series' build/paso.log | grep -v '^PASS: ' | cut -c1-200; }
{
echo "Puerta de simulacion de R0 con la variante $NOMBRE de la regla de cotas: Cotas($ARGS)"
echo "Generado por tools/variante_cotas.sh sobre $(git -C "$RAIZ" rev-parse --short HEAD). Programa: $PROG."
echo
paso make tb
paso make equiv
paso make equiv-gemelo
paso make fases
paso make estres
paso python3 tools/exhaustivo/r0_cotas.py
B=build/r0_variante; mkdir -p $B
zcat bitstreams/moldes/r0_molde.asc.gz > $B/r0_molde.asc
icebram bitstreams/moldes/molde_prog_r0.hex sw/trade.hex < $B/r0_molde.asc > $B/r0.asc
icepack $B/r0.asc $B/r0.bin
paso tools/sim_bitstream.sh $B/r0.asc 2000
paso env SERIE=build/cotas/meta_ventana.csv tools/sim_bitstream.sh $B/r0.asc 2000
cp $B/r0.bin "$RAIZ/bitstreams/variantes/r0_$NOMBRE.bin"
echo "bitstreams/variantes/r0_$NOMBRE.bin: sha256 $(sha256sum $B/r0.bin | cut -d' ' -f1)"
echo
if [ "$f" -eq 0 ]; then echo "PASS: la variante $NOMBRE paso la puerta de R0"; else echo "FAIL: $f pasos fallaron"; fi
} 2>&1 | tee "$RAIZ/$SALIDA"
cd "$RAIZ" && git worktree remove --force "$W"
grep -q '^PASS: la variante' "$SALIDA"
