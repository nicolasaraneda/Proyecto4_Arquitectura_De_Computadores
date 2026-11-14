# comun.sh: rutas y listas de fuentes que comparten los scripts del prototipo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con "source". Deja el directorio de trabajo en la raíz del
# repositorio y define:
#   A           carpeta del prototipo, relativa a la raíz
#   B           carpeta de productos intermedios (A/build, ignorada por git)
#   M           carpeta de mediciones (A/mediciones, versionada)
#   BARREL_SRC  fuentes del SoC con el core barrel. Los seis primeros son los
#               del repositorio, sin modificar. Los tres últimos son los del
#               prototipo.
#   BASE_SRC    fuentes del SoC original (rtl/), sin modificar
#   CELLS_SIM   modelos de simulación de las primitivas del iCE40
# y las funciones ensamblar, con_tabla, programas, compilar_verif y versiones.

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$RAIZ"
export PATH=$HOME/herramientas/oss-cad-suite/bin:$PATH

A=factibilidad/a_barrel
B=$A/build
M=$A/mediciones
PYTHON=${PYTHON:-python3}
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v

BARREL_SRC="rtl/pochoco_ram.v rtl/pochoco_spi_slave.v rtl/pochoco_periph.v \
rtl/espino_core/espino_decoder.v rtl/espino_core/espino_alu.v rtl/espino_core/espino_load_store_unit.v \
$A/rtl/pochoco_soc.v $A/rtl/espino_barrel_core.v $A/rtl/espino_barrel_regfile.v"
BASE_SRC=$(echo rtl/*.v rtl/espino_core/*.v)

mkdir -p "$B/sw" "$M"

# ensamblar FUENTE.s SALIDA.hex [opciones]: ensambla con tools/pochoasm.py
ensamblar() {
  local s=$1 h=$2; shift 2
  $PYTHON tools/pochoasm.py "$@" "$s" -o "$h" > /dev/null
}

# con_tabla HILO PROGRAMA.s SALIDA.hex: antepone la tabla de arranque y ensambla
con_tabla() {
  $PYTHON $A/tools/tabla.py "$1" "$2" > "${3%.hex}.s"
  ensamblar "${3%.hex}.s" "$3"
}

# programas: ensambla todos los programas del prototipo en B/sw
programas() {
  ensamblar $A/sw/hilos_distintos.s "$B/sw/hilos_distintos.hex"
  ensamblar $A/sw/cooperacion.s     "$B/sw/cooperacion.hex"
  ensamblar $A/sw/mix_clase7_x4.s   "$B/sw/mix_clase7_x4.hex"
  ensamblar $A/sw/hilo_mmio.s       "$B/sw/hilo_mmio.hex"
  ensamblar sw/mix_clase7.s         "$B/sw/mix_clase7.hex"
  con_tabla 0 sw/mix_clase7.s       "$B/sw/mix_clase7_h0.hex"
  con_tabla 0 sw/trade.s            "$B/sw/trade_h0.hex"
}

# compilar_verif DIR [CORE.v REGFILE.v SOC.v [definiciones...]]: compila
# tb/tb_verif.sv con Verilator en DIR/obj/sim. Sin más argumentos usa el RTL
# del prototipo. Con ellos usa esos tres archivos en su lugar (copias mutadas,
# tools/mutaciones.sh). El SoC barrel se compila con el nombre
# pochoco_soc_barrel para convivir con el pochoco_soc original.
compilar_verif() {
  local d=$1 core=${2:-$A/rtl/espino_barrel_core.v} rf=${3:-$A/rtl/espino_barrel_regfile.v} soc=${4:-$A/rtl/pochoco_soc.v}
  shift; shift 2>/dev/null; shift 2>/dev/null; shift 2>/dev/null
  mkdir -p "$d"
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_verif ${VERIF_OPT:--O3} \
    -DPOCHOCO_SOC_MODULE=pochoco_soc_barrel -DNO_ICE40_DEFAULT_ASSIGNMENTS "$@" --Mdir "$d/obj" -o sim \
    "$CELLS_SIM" $BASE_SRC "$soc" "$core" "$rf" $A/tb/tb_verif.sv > "$d/verilator.log" 2>&1
}

versiones() {
  echo "Herramientas:"
  echo "  $(yosys -V)"
  echo "  $(nextpnr-ice40 --version 2>&1 | head -1)"
  echo "  $(iverilog -V 2>/dev/null | head -1)"
  echo "Commit de partida: $(git rev-parse --short HEAD) (rama $(git rev-parse --abbrev-ref HEAD))"
}
