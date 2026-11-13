#!/usr/bin/env bash
# medir_base.sh: mediciones del repo base del curso, tal como se importó.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Extrae el árbol de la etiqueta base-curso (copia sin cambios de
# nic0villegasc/pochoco_soc en el commit 33e8b5a) a build/base/src y mide:
#
#   1. Celdas lógicas, BRAM y frecuencia máxima (varias semillas de nextpnr).
#   2. Lo mismo con el shifter completo de la ALU habilitado.
#   3. Si el HX1K en encapsulado VQ100 acepta un PLL.
#   4. CPI en simulación y comprobación del modelo 2*IC + loads + saltos.
#
# Uso, desde cualquier carpeta del repositorio:
#   tools/medir_base.sh [numero_de_semillas]      (por defecto 10)
#
# Deja el resumen en docs/mediciones/base.txt y los logs en build/base/.

set -euo pipefail

SEMILLAS=${1:-10}
RAIZ=$(git rev-parse --show-toplevel)
cd "$RAIZ"

B=build/base
rm -rf $B
mkdir -p $B/src docs/mediciones
git archive base-curso | tar -x -C $B/src

RES=docs/mediciones/base.txt
PCF=$B/src/goboard.pcf

sintetizar() {   # $1 = carpeta con rtl/, $2 = prefijo de salida
  ( cd "$1" && yosys -q -l "$RAIZ/$2.yosys.log" \
      -p "read_verilog ./rtl/*.v ./rtl/espino_core/*.v; synth_ice40 -top pochoco_soc -json $RAIZ/$2.json; stat" )
}

pnr() {          # $1 = prefijo, $2 = semilla. Devuelve el código de salida de nextpnr.
  nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed "$2" \
    --json "$1.json" --pcf $PCF --asc "$1.s$2.asc" -l "$1.s$2.nextpnr.log" -q 2>/dev/null
}

campo() {        # $1 = log de nextpnr, $2 = ICESTORM_LC o ICESTORM_RAM
  grep "$2:" "$1" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'
}

fmax() {         # última frecuencia máxima reportada (después del ruteo)
  grep "Max frequency for clock" "$1" | tail -1 | sed -E 's/.*: ([0-9.]+) MHz.*/\1/'
}

{
  echo "Mediciones del repo base (etiqueta base-curso, nic0villegasc/pochoco_soc en 33e8b5a)"
  echo "Generado por tools/medir_base.sh. No editar a mano."
  echo
  echo "Herramientas:"
  echo "  $(yosys -V)"
  echo "  $(nextpnr-ice40 --version 2>&1)"
  echo "  $(iverilog -V 2>&1 | head -1)"
  echo
} > $RES

# --- 1. Base tal cual ---------------------------------------------------------
echo "[1/4] base: sintesis y $SEMILLAS semillas de nextpnr"
sintetizar $B/src $B/base
export -f pnr; export PCF
seq 1 "$SEMILLAS" | xargs -P "$(nproc)" -I{} bash -c "pnr $B/base {} || true"

{
  echo "1. Base sin cambios (nextpnr --hx1k --package vq100 --freq 25)"
  echo "  Celdas logicas: $(campo $B/base.s1.nextpnr.log ICESTORM_LC)"
  echo "  BRAM:           $(campo $B/base.s1.nextpnr.log ICESTORM_RAM)"
  echo "  LUT4 segun yosys: $(grep -E '^ +[0-9]+ +SB_LUT4' $B/base.yosys.log | tail -1 | awk '{print $1}')"
  echo "  Frecuencia maxima por semilla (MHz):"
  for s in $(seq 1 "$SEMILLAS"); do
    printf "    semilla %2d: %s\n" "$s" "$(fmax $B/base.s$s.nextpnr.log)"
  done
  for s in $(seq 1 "$SEMILLAS"); do fmax $B/base.s$s.nextpnr.log; done | sort -n > $B/fmax.txt
  echo "  Minima $(head -1 $B/fmax.txt), mediana $(awk '{a[NR]=$1} END {print (NR%2)? a[(NR+1)/2] : (a[NR/2]+a[NR/2+1])/2}' $B/fmax.txt), maxima $(tail -1 $B/fmax.txt) MHz"
  echo
} >> $RES

# --- 2. Shifter completo habilitado -------------------------------------------
echo "[2/4] shifter completo"
cp -r $B/src $B/src_shifter
sed -i -E 's|// (ALU_S[LR][LA]: +result_o)|\1|' $B/src_shifter/rtl/espino_core/espino_alu.v
if [ "$(grep -cE '^ +ALU_S[LR][LA]: +result_o' $B/src_shifter/rtl/espino_core/espino_alu.v)" != 3 ]; then
  echo "error: no se pudieron habilitar las tres lineas del shifter" >&2; exit 1
fi
sintetizar $B/src_shifter $B/shifter
cabe=si; pnr $B/shifter 1 || cabe=no
{
  echo "2. Shifter completo habilitado (sll, srl y sra descomentados en espino_alu.v)"
  echo "  Celdas logicas: $(campo $B/shifter.s1.nextpnr.log ICESTORM_LC)"
  echo "  BRAM:           $(campo $B/shifter.s1.nextpnr.log ICESTORM_RAM)"
  echo "  LUT4 segun yosys: $(grep -E '^ +[0-9]+ +SB_LUT4' $B/shifter.yosys.log | tail -1 | awk '{print $1}')"
  echo "  Cabe en el HX1K: $cabe"
  if [ $cabe = si ]; then echo "  Frecuencia maxima (semilla 1): $(fmax $B/shifter.s1.nextpnr.log) MHz"
  else echo "  nextpnr: $(grep -m1 -E '^ERROR' $B/shifter.s1.nextpnr.log)"; fi
  echo
} >> $RES

# --- 3. PLL ---------------------------------------------------------------------
echo "[3/4] PLL"
cp -r $B/src $B/src_pll
python3 - "$B/src_pll/rtl/pochoco_soc.v" <<'EOF'
import sys
ruta = sys.argv[1]
texto = open(ruta, encoding="utf-8").read()
original = "  assign clk = i_Clk;\n"
assert original in texto
# 25 MHz * (DIVF + 1) / 2^DIVQ = 25 * 32 / 16 = 50 MHz (parametros de icepll -i 25 -o 50)
pll = """  SB_PLL40_CORE #(
    .FEEDBACK_PATH("SIMPLE"), .DIVR(4'd0), .DIVF(7'd31), .DIVQ(3'd4), .FILTER_RANGE(3'd2)
  ) u_pll (
    .REFERENCECLK(i_Clk), .PLLOUTGLOBAL(clk), .RESETB(1'b1), .BYPASS(1'b0)
  );
"""
open(ruta, "w", encoding="utf-8").write(texto.replace(original, pll))
EOF
sintetizar $B/src_pll $B/pll
pll_ok=si; pnr $B/pll 1 || pll_ok=no
cp $B/pll.s1.nextpnr.log docs/mediciones/pll_nextpnr.log
{
  echo "3. PLL (SB_PLL40_CORE de 25 a 50 MHz en pochoco_soc.v)"
  echo "  nextpnr termina bien: $pll_ok"
  grep -E '^ERROR' $B/pll.s1.nextpnr.log | sed 's/^/  nextpnr: /' || true
  echo "  Log completo en docs/mediciones/pll_nextpnr.log"
  echo
} >> $RES

# --- 4. CPI en simulacion -------------------------------------------------------
echo "[4/4] CPI en simulacion"
CELLS=$(yosys-config --datdir)/ice40/cells_sim.v
{
  echo "4. CPI del Espino base en simulacion (tb/tb_cpi.sv)"
  for prog in sw/blink.hex sw/7seg.hex sw/buttons_leds.hex; do
    iverilog -g2012 -s tb_cpi -DPROGRAMA=\"$B/src/$prog\" -DNTICKS=20 -o $B/tb_cpi \
      "$CELLS" $B/src/rtl/*.v $B/src/rtl/espino_core/*.v tb/tb_cpi.sv
    vvp -n $B/tb_cpi | grep -vE '^WARNING|finish called' | sed 's/^/  /'
    echo
  done
} >> $RES

cat $RES
