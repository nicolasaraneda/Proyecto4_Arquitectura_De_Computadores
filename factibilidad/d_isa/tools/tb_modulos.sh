#!/usr/bin/env bash
# tb_modulos.sh: los testbenches de cada módulo de la pieza D contra el modelo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Para cada módulo y cada configuración genera los vectores con
# tools/gen_vectores.py (los valores esperados salen de ref/xd.py), compila el
# testbench con Icarus y lo corre. Imprime una línea PASS o FAIL por corrida y
# termina con error si alguna falla.
#
# Uso, desde factibilidad/d_isa:   tools/tb_modulos.sh [rapido]
# Con "rapido" se salta el dominio completo de la regla base (2 millones de
# vectores) y usa menos vectores al azar.
set -euo pipefail
cd "$(dirname "$0")/.."

MODO=${1:-completo}
N=20000
[ "$MODO" = rapido ] && N=2000
B=build/tb
mkdir -p "$B"
FALLAS=0

# correr ETIQUETA TB GENERADOR "opciones del generador" "definiciones" fuentes...
correr() {
  local etq=$1 tb=$2 gen=$3 opts=$4 defs=$5; shift 5
  python3 tools/gen_vectores.py "$gen" "$B/$etq.vec" --n "$N" $opts > /dev/null
  iverilog -g2012 -I tb -s "$tb" "-DVEC=\"$B/$etq.vec\"" "-DNOMBRE=\"$etq\"" $defs \
    -o "$B/$etq.vvp" "$@" "tb/$tb.sv"
  vvp -n "$B/$etq.vvp" > "$B/$etq.log" 2>&1 || true
  grep -E "^(PASS|FAIL|  diferencia|ERROR)" "$B/$etq.log" || echo "FAIL $etq: el testbench no terminó"
  grep -q "^PASS" "$B/$etq.log" || FALLAS=$((FALLAS + 1))
  rm -f "$B/$etq.vec"
}

echo "== Testbenches por módulo contra ref/xd.py ($MODO) =="
python3 ref/xd.py

for kb in 0 2 3 5; do
  correr "xd_ema_kb$kb"  tb_xd_ema  ema  "--kb $kb" "-DKB=$kb" rtl/xd_ema.v
  correr "xd_srak_kb$kb" tb_xd_srak srak "--kb $kb" "-DKB=$kb" rtl/xd_srak.v
  correr "xd_opa_kb$kb"  tb_xd_opa  opa  "--kb $kb" "-DKB=$kb" rtl/xd_opa.v
done
if [ "$MODO" != rapido ]; then
  correr xd_ema_dominio tb_xd_ema ema_dominio "" "-DKB=0" rtl/xd_ema.v
  correr xd_opa_dominio tb_xd_opa opa_dominio "" "-DKB=0" rtl/xd_opa.v
fi
for m in 0 28 31 32 63; do
  correr "xd_simd8_m$m" tb_xd_simd8 simd "--mascara $m" "-DMASCARA=$m" rtl/xd_simd8.v
done
correr xd_alu_carriles tb_xd_alu simd "--mascara 4" "" rtl/xd_alu.v
correr xd_mulstep tb_xd_mulstep mulstep "" "" rtl/xd_mulstep.v
correr xd_divstep tb_xd_divstep divstep "" "" rtl/xd_divstep.v
for aw in 8 16; do
  correr "xd_mulc_aw$aw" tb_xd_mulc mulc "--aw $aw" "-DAW=$aw" rtl/xd_mulc.v
done
correr xd_mul_mmio tb_xd_mul_mmio mmio "" "" rtl/xd_mul_mmio.v rtl/xd_mulstep.v

if [ "$FALLAS" != 0 ]; then echo "FAIL: $FALLAS corridas con error"; exit 1; fi
echo "PASS: todos los módulos coinciden con el modelo"

# Controles negativos: un error puesto a propósito en cada módulo (bloques
# `ifdef MUTA_XD_*` del RTL) tiene que hacer fallar a su testbench.
echo
echo "== Controles negativos por mutación =="
DETECTADAS=0; MUTACIONES=0
# mutar ETIQUETA TB GENERADOR "opciones" "definiciones" fuentes...
mutar() {
  local etq=$1 tb=$2 gen=$3 opts=$4 defs=$5; shift 5
  MUTACIONES=$((MUTACIONES + 1))
  python3 tools/gen_vectores.py "$gen" "$B/$etq.vec" --n 2000 $opts > /dev/null
  iverilog -g2012 -I tb -s "$tb" "-DVEC=\"$B/$etq.vec\"" "-DNOMBRE=\"$etq\"" $defs \
    -o "$B/$etq.vvp" "$@" "tb/$tb.sv"
  vvp -n "$B/$etq.vvp" > "$B/$etq.log" 2>&1 || true
  rm -f "$B/$etq.vec"
  if grep -q "^FAIL" "$B/$etq.log"; then
    DETECTADAS=$((DETECTADAS + 1))
    echo "detectada     $etq: $(grep '^FAIL' "$B/$etq.log" | head -1 | sed 's/^FAIL [^:]*: //')"
  else
    echo "NO DETECTADA  $etq"
  fi
}
mutar muta_ema     tb_xd_ema      ema     "--kb 0" "-DKB=0 -DMUTA_XD_EMA"     rtl/xd_ema.v
mutar muta_srak    tb_xd_srak     srak    "--kb 3" "-DKB=3 -DMUTA_XD_SRAK"    rtl/xd_srak.v
mutar muta_opa     tb_xd_opa      opa     "--kb 0" "-DKB=0 -DMUTA_XD_OPA"     rtl/xd_opa.v
mutar muta_simd    tb_xd_simd8    simd    "--mascara 0" "-DMASCARA=0 -DMUTA_XD_SIMD" rtl/xd_simd8.v
mutar muta_alu     tb_xd_alu      simd    "--mascara 4" "-DMUTA_XD_ALU"      rtl/xd_alu.v
mutar muta_mulstep tb_xd_mulstep  mulstep ""       "-DMUTA_XD_MULSTEP"        rtl/xd_mulstep.v
mutar muta_divstep tb_xd_divstep  divstep ""       "-DMUTA_XD_DIVSTEP"        rtl/xd_divstep.v
mutar muta_mulc    tb_xd_mulc     mulc    "--aw 8" "-DAW=8 -DMUTA_XD_MULC"    rtl/xd_mulc.v
mutar muta_mmio    tb_xd_mul_mmio mmio    ""       "-DMUTA_XD_MMIO"           rtl/xd_mul_mmio.v rtl/xd_mulstep.v
echo "Mutaciones detectadas: $DETECTADAS de $MUTACIONES"
[ "$DETECTADAS" = "$MUTACIONES" ] || exit 1
