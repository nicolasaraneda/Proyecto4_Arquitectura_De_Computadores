#!/usr/bin/env bash
# pll.sh: resultado negativo del PLL, con su evidencia, sobre el SoC actual.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Repite sobre R0 (Espino base con sw/trade.s) y R1 (el fondo en un chip) lo
# que tools/medir_base.sh hizo sobre el repositorio base: una copia de
# rtl/pochoco_soc.v en la que el reloj interno sale de un SB_PLL40_CORE de
# 25 a 50 MHz (parámetros de icepll -i 25 -o 50). La copia vive en build/p7/;
# rtl/ no se toca.
#
#   1. Go Board (HX1K, VQ100, goboard.pcf): nextpnr no encuentra dónde poner
#      el PLL. Se guarda el log de R1 en docs/mediciones/p7/pll_vq100_r1.log.
#   2. Hipotético: el mismo diseño en el HX1K en encapsulado TQ144, que sí
#      tiene PLL, sin restricciones de pines y con --freq 50, en 10 semillas.
#      Sirve para saber si el diseño cerraría a 50 MHz si el PLL existiera.
#
# Deja docs/mediciones/p7/pll.txt. Uso: tools/p7/pll.sh [SEMILLAS] (make p7-pll)
set -euo pipefail
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-10}
programas
D=$B/pll
rm -rf "$D"; mkdir -p "$D/rtl/espino_core"
cp rtl/*.v "$D/rtl/"; cp rtl/espino_core/*.v "$D/rtl/espino_core/"
$PYTHON - "$D/rtl/pochoco_soc.v" <<'PY'
import sys
ruta = sys.argv[1]
texto = open(ruta, encoding="utf-8").read()
original = "  assign clk = i_Clk;\n"
assert texto.count(original) == 1, "no se encontró la asignación del reloj"
pll = """  SB_PLL40_CORE #(
    .FEEDBACK_PATH("SIMPLE"), .DIVR(4'd0), .DIVF(7'd31), .DIVQ(3'd4), .FILTER_RANGE(3'd2)
  ) u_pll (
    .REFERENCECLK(i_Clk), .PLLOUTGLOBAL(clk), .RESETB(1'b1), .BYPASS(1'b0)
  );
"""
open(ruta, "w", encoding="utf-8").write(texto.replace(original, pll))
PY
[ "$(diff rtl/pochoco_soc.v "$D/rtl/pochoco_soc.v" | grep -c '^>')" = 5 ] || { echo "FAIL: la copia con PLL no quedó como se esperaba"; exit 1; }

sintetizar() {   # sintetizar ETIQUETA "DEFS" HEX
  yosys -q -l "$D/$1.yosys.log" -p "read_verilog $2 $(echo $D/rtl/*.v $D/rtl/espino_core/*.v); \
    chparam -set MemFile \"$3\" pochoco_soc; synth_ice40 -top pochoco_soc -json $D/$1.json"
}
sintetizar r0 "" sw/trade.hex
sintetizar r1 "$R1_DEFS" "$B/sw/fondo.hex"

vq100() {   # vq100 ETIQUETA: 0 si nextpnr termina
  nextpnr-ice40 --hx1k --package vq100 --freq 50 --json "$D/$1.json" --pcf goboard.pcf \
    --asc "$D/$1.vq100.asc" -l "$D/$1.vq100.log" -q > /dev/null 2>&1
}
tq144() {   # tq144 ETIQUETA SEMILLA
  nextpnr-ice40 --hx1k --package tq144 --freq 50 --seed "$2" --json "$D/$1.json" --pcf-allow-unconstrained \
    --asc "$D/$1.tq144.s$2.asc" -l "$D/$1.tq144.s$2.log" -q > /dev/null 2>&1 || true
}
export -f tq144; export D
r0_vq=si; vq100 r0 || r0_vq=no
r1_vq=si; vq100 r1 || r1_vq=no
cp "$D/r1.vq100.log" "$M/pll_vq100_r1.log"
for e in r0 r1; do seq 1 "$SEMILLAS" | xargs -P 10 -I{} bash -c "tq144 $e {}"; done

fmax() { grep "Max frequency for clock" "$1" | tail -1 | sed -E 's/.*: ([0-9.]+) MHz.*/\1/'; }
resumen() {   # resumen ETIQUETA
  local n=0 c=0 l=""
  for s in $(seq 1 "$SEMILLAS"); do
    f=$(fmax "$D/$1.tq144.s$s.log" || true); [ -z "$f" ] && f=0
    l="$l $f"; n=$((n + 1))
    grep "Max frequency for clock" "$D/$1.tq144.s$s.log" | tail -1 | grep -q PASS && c=$((c + 1))
  done
  m=$(echo $l | tr ' ' '\n' | sort -n | awk '{a[NR]=$1} END {printf "minima %.2f mediana %.2f", a[1], (NR%2)? a[(NR+1)/2] : (a[NR/2]+a[NR/2+1])/2}')
  echo "  $1: cierran a 50 MHz $c de $SEMILLAS semillas, fmax $m MHz"
  echo "      por semilla:$l"
  echo "      PLL ubicado en: $(grep -m1 -oE "constrained PLL '.*' to .*|PLL '.*' .* placed .*" "$D/$1.tq144.s1.log" || grep -m1 -oE 'SB_PLL40_CORE.*' "$D/$1.tq144.s1.log" || echo 've el log')"
}

{
  echo "PLL de 25 a 50 MHz en el SoC actual: resultado negativo en la Go Board"
  echo "Generado por tools/p7/pll.sh (make p7-pll). No editar a mano."
  echo
  versiones
  echo
  echo "Copia de rtl/pochoco_soc.v en $D/rtl/ con 'assign clk = i_Clk' reemplazado por un SB_PLL40_CORE"
  echo "(DIVR 0, DIVF 31, DIVQ 4, FILTER_RANGE 2: 25 MHz x 32 / 16 = 50 MHz, de icepll -i 25 -o 50)."
  echo
  echo "1. Go Board: nextpnr-ice40 --hx1k --package vq100 --freq 50 --pcf goboard.pcf"
  echo "  R0 (Espino base, sw/trade.s): nextpnr termina bien: $r0_vq"
  grep -E '^ERROR' "$D/r0.vq100.log" | sed 's/^/    /' || true
  echo "  R1 (fondo en un chip, sw/fondo.s): nextpnr termina bien: $r1_vq"
  grep -E '^ERROR' "$D/r1.vq100.log" | sed 's/^/    /' || true
  echo "  Log completo de R1 en $M/pll_vq100_r1.log"
  echo
  echo "2. Hipotético: HX1K en TQ144 (tiene PLL), --freq 50, sin restricciones de pines"
  resumen r0
  resumen r1
  echo
  echo "3. Presupuesto por ronda si el PLL existiera: (período - 9500 ns) / período del reloj"
  for p in 10000000 1000000 100000; do
    awk -v p=$p 'BEGIN {printf "  T = %8d ns: a 25 MHz %6d ciclos, a 50 MHz %6d ciclos\n", p, (p-9500)/40, (p-9500)/20}'
  done
} > "$M/pll.txt"
cat "$M/pll.txt"
