# comun.sh: rutas y listas de fuentes de la auditoría de hardware.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con "source". Deja el directorio de trabajo en la raíz del
# repositorio. Las listas de fuentes están escritas aquí archivo por archivo,
# a propósito: la auditoría no usa las listas de los scripts que revisa.
#
#   U    carpeta de la auditoría        B    productos intermedios (U/build)
#   M    mediciones (U/mediciones)      I, F carpetas de las dos piezas auditadas
#   A, D, E   barrel, extensión de la ISA y respaldo por reconfiguración
#   SRC_BARREL_PROTO  SoC del prototipo del barrel (el que usa el fondo)
#   SRC_I             SoC integrado sobre el barrel (I1 e I2, según definiciones)
#   SRC_SEG           SoC "conservador" (I3): segmentado con la extensión y vigilante
#   SRC_BASE          SoC del repositorio, sin tocar

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$RAIZ"
export PATH=${OSS_CAD_SUITE:+$OSS_CAD_SUITE/bin:}$PATH
export PYTHONDONTWRITEBYTECODE=1

U=factibilidad/auditoria_hw
I=factibilidad/i_integrado
F=factibilidad/b_fondo_hilos
A=factibilidad/a_barrel
D=factibilidad/d_isa
E=factibilidad/e_warmboot
B=$U/build
M=$U/mediciones
PYTHON=${PYTHON:-python3}
JOBS=${JOBS:-5}
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
mkdir -p "$B" "$M"

XD="$D/rtl/xd_alu.v $D/rtl/xd_divstep.v $D/rtl/xd_ema.v $D/rtl/xd_mulc.v $D/rtl/xd_mulstep.v \
$D/rtl/xd_opa.v $D/rtl/xd_simd8.v $D/rtl/xd_srak.v $D/rtl/xd_unit.v $D/rtl/xd_mul_mmio.v"

SRC_BARREL_PROTO="rtl/pochoco_ram.v rtl/pochoco_spi_slave.v rtl/pochoco_periph.v \
rtl/espino_core/espino_decoder.v rtl/espino_core/espino_alu.v rtl/espino_core/espino_load_store_unit.v \
$A/rtl/pochoco_soc.v $A/rtl/espino_barrel_core.v $A/rtl/espino_barrel_regfile.v"

# src_i [CARPETA]: los cuatro archivos propios del diseño integrado salen de
# CARPETA (por defecto, rtl/ de la pieza). Las mutaciones pasan una copia.
src_i() {
  local r=${1:-$I/rtl} v=${2:-$E/rtl/vigilante.v} x=${3:-$XD}
  echo "rtl/pochoco_ram.v rtl/pochoco_periph.v $E/soc/pochoco_spi_slave.v \
rtl/espino_core/espino_alu.v rtl/espino_core/espino_load_store_unit.v $I/rtl/espino_decoder_xd.v \
$r/pochoco_soc.v $r/espino_barrel_core.v $A/rtl/espino_barrel_regfile.v $v $r/tabla_mmio.v $r/tabla_ram.v $x"
}
SRC_I=$(src_i)

SRC_SEG="rtl/pochoco_ram.v rtl/pochoco_periph.v $E/soc/pochoco_spi_slave.v $E/soc/pochoco_soc.v \
$D/core/espino_core/espino_alu.v $D/core/espino_core/espino_controller.v $D/core/espino_core/espino_core.v \
$D/core/espino_core/espino_decoder.v $D/core/espino_core/espino_id_stage.v $D/core/espino_core/espino_if_stage.v \
$D/core/espino_core/espino_load_store_unit.v $D/core/espino_core/espino_register_file.v $E/rtl/vigilante.v $XD"

SRC_BASE="rtl/pochoco_periph.v rtl/pochoco_ram.v rtl/pochoco_soc.v rtl/pochoco_spi_slave.v \
rtl/espino_core/espino_alu.v rtl/espino_core/espino_controller.v rtl/espino_core/espino_core.v \
rtl/espino_core/espino_decoder.v rtl/espino_core/espino_id_stage.v rtl/espino_core/espino_if_stage.v \
rtl/espino_core/espino_load_store_unit.v rtl/espino_core/espino_register_file.v"

# Definiciones de cada configuración, copiadas de la tabla del README de la
# pieza (sección 1), no de sus scripts.
DEFS_I1A="-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DI_VIGILANTE -DI_TABLA=1"
DEFS_I1B="-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DI_VIGILANTE -DI_TABLA=2"
DEFS_I2="-DI_VIGILANTE"
DEFS_I3A="-DESPINO_SEGMENTADO -DXD_EMAD=0"
DEFS_I3B="-DESPINO_SEGMENTADO -DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU"

# enlazar DESTINO FUENTES...: carpeta con la forma que espera
# tools/medir_variante.sh (*.v y espino_core/*.v), con enlaces
enlazar() {
  local d=$1 f; shift
  rm -rf "${d:?}"; mkdir -p "$d/espino_core"
  for f in "$@"; do
    case "$(basename "$f")" in
      espino_*) ln -s "$RAIZ/$f" "$d/espino_core/" ;;
      *)        ln -s "$RAIZ/$f" "$d/" ;;
    esac
  done
}

# regla_base_h0 SALIDA.hex: sw/trade.s con la tabla de arranque del barrel
regla_base_h0() {
  $PYTHON $A/tools/tabla.py 0 sw/trade.s > "${1%.hex}.s"
  $PYTHON tools/pochoasm.py "${1%.hex}.s" -o "$1" > /dev/null
}

# arnes: la referencia en C (núcleo del arnés de retorno con el módulo del
# fondo, sin modificar), compilada dentro de esta carpeta
arnes() {
  ARNES=$B/arnes
  if [ ! -x "$ARNES" ] || [ factibilidad/retorno/r4b_fondo/fondo.c -nt "$ARNES" ]; then
    make -s -C "$U" build/arnes > /dev/null || { echo "FAIL no compila la referencia en C"; return 1; }
  fi
}

perdidos() {
  $PYTHON -c "import sys; sys.path.insert(0, 'ref'); import trader; print(trader.ticks_perdidos($1))"
}

versiones() {
  echo "Herramientas:"
  echo "  $(yosys -V)"
  echo "  $(nextpnr-ice40 --version 2>&1 | head -1)"
  echo "  $(iverilog -V 2>/dev/null | head -1)"
  echo "  $(verilator --version)"
  echo "Commit de partida: $(git rev-parse --short HEAD) (rama $(git rev-parse --abbrev-ref HEAD))"
}
