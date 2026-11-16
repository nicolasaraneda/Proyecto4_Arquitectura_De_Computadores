# comun.sh: rutas y listas de fuentes que comparten los scripts del Espino barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con "source". Deja el directorio de trabajo en la raíz del
# repositorio y define:
#   T, TB, SW, FO  carpetas de los scripts, testbenches, programas y archivos
#               formales del barrel (tools/barrel, tb/barrel, sw/barrel y
#               formal/barrel)
#   B           carpeta de productos intermedios (build/barrel, ignorada por git)
#   M           carpeta de mediciones (docs/mediciones/barrel, versionada)
#   BASE_SRC    fuentes del SoC, las mismas del comando del testbench oficial
#               (rtl/*.v rtl/espino_core/*.v). Sin definiciones dan el Espino base.
#   BARREL_SRC  las mismas fuentes con -DESPINO_BARREL delante: el SoC con el
#               core barrel. Sirve tal cual en una línea de iverilog, de
#               Verilator o de read_verilog de Yosys.
#   CELLS_SIM   modelos de simulación de las primitivas del iCE40
# y las funciones ensamblar, con_tabla, programas, soc_barrel, compilar_verif
# y versiones.

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$RAIZ"
[ -n "${OSS_CAD_SUITE:-}" ] && export PATH="$OSS_CAD_SUITE/bin:$PATH"   # si no, las herramientas tienen que estar en el PATH

T=tools/barrel
TB=tb/barrel
SW=sw/barrel
FO=formal/barrel
B=build/barrel
M=docs/mediciones/barrel
PYTHON=${PYTHON:-python3}
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v

CORE_V=rtl/espino_core/espino_barrel_core.v
RF_V=rtl/espino_core/espino_barrel_regfile.v
SOC_V=rtl/pochoco_soc.v
BASE_SRC=$(ls rtl/*.v rtl/espino_core/*.v | grep -v '^rtl/00_')
BARREL_SRC="-DESPINO_BARREL $BASE_SRC"
# Las fuentes sin los dos archivos del core barrel, para compilar en su lugar
# copias con un error puesto a propósito
SRC_SIN_BARREL=$(echo $BASE_SRC | tr ' ' '\n' | grep -v espino_barrel_ | tr '\n' ' ')

mkdir -p "$B/sw" "$M"

# ensamblar FUENTE.s SALIDA.hex [opciones]: ensambla con tools/pochoasm.py
ensamblar() {
  local s=$1 h=$2; shift 2
  $PYTHON tools/pochoasm.py "$@" "$s" -o "$h" > /dev/null
}

# con_tabla HILO PROGRAMA.s SALIDA.hex: antepone la tabla de arranque y ensambla
con_tabla() {
  $PYTHON $T/tabla.py "$1" "$2" > "${3%.hex}.s"
  ensamblar "${3%.hex}.s" "$3"
}

# programas: ensambla todos los programas de prueba del barrel en B/sw
programas() {
  ensamblar $SW/hilos_distintos.s "$B/sw/hilos_distintos.hex"
  ensamblar $SW/cooperacion.s     "$B/sw/cooperacion.hex"
  ensamblar $SW/mix_clase7_x4.s   "$B/sw/mix_clase7_x4.hex"
  ensamblar sw/mix_clase7.s       "$B/sw/mix_clase7.hex"
  con_tabla 0 sw/mix_clase7.s     "$B/sw/mix_clase7_h0.hex"
  con_tabla 0 sw/trade.s          "$B/sw/trade_h0.hex"
}

# soc_barrel SOC.v SALIDA.v: copia de pochoco_soc.v con el core barrel y con el
# módulo llamado pochoco_soc_barrel, para instanciarlo en un mismo testbench
# junto al pochoco_soc con el Espino base. La copia solo difiere del original
# en el nombre del módulo y en que ESPINO_BARREL queda definido dentro de ella.
soc_barrel() {
  { echo '`define ESPINO_BARREL'
    sed -e 's/^module pochoco_soc #(/module pochoco_soc_barrel #(/' "$1"
    echo; echo '`undef ESPINO_BARREL'; } > "$2"
  grep -q '^module pochoco_soc_barrel #(' "$2" || { echo "soc_barrel: no se pudo renombrar el modulo de $1" >&2; return 1; }
  [ "$(sed -e '$a\\' "$1" | diff - "$2" | grep -c '^[<>]')" = 5 ] || { echo "soc_barrel: la copia de $1 cambio mas de lo esperado" >&2; return 1; }
}

# compilar_verif DIR [CORE.v REGFILE.v SOC.v [definiciones...]]: compila
# tb/barrel/tb_verif.sv con Verilator en DIR/obj/sim. Sin más argumentos usa
# el RTL del repositorio. Con ellos usa esos tres archivos para el barrel
# (copias con un error puesto a propósito, tools/barrel/mutaciones.sh); los
# cuatro SoC de referencia con el Espino base salen siempre de rtl/.
# VERIF_DEFS (variable de entorno, opcional): definiciones que se agregan a los
# dos SoC de la comparación, el barrel y el base de referencia. Se usa para
# repetir la campaña sobre el hardware de R1 y de R2 (-DESPINO_TABLA y
# -DESPINO_VIGILANTE son del SoC, no del core: tools/fondo/criterio5.sh).
compilar_verif() {
  local d=$1 core=${2:-$CORE_V} rf=${3:-$RF_V} soc=${4:-$SOC_V}
  shift; shift 2>/dev/null; shift 2>/dev/null; shift 2>/dev/null
  mkdir -p "$d"
  soc_barrel "$soc" "$d/pochoco_soc_barrel.v" || return 1
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_verif ${VERIF_OPT:--O3} \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS ${VERIF_DEFS:-} "$@" --Mdir "$d/obj" -o sim \
    "$CELLS_SIM" $SRC_SIN_BARREL "$d/pochoco_soc_barrel.v" "$core" "$rf" $TB/tb_verif.sv > "$d/verilator.log" 2>&1
}

versiones() {
  echo "Herramientas:"
  echo "  $(yosys -V)"
  echo "  $(nextpnr-ice40 --version 2>&1 | head -1)"
  echo "  $(iverilog -V 2>/dev/null | head -1)"
  echo "Commit de partida: $(git rev-parse --short HEAD) (rama $(git rev-parse --abbrev-ref HEAD))"
}
