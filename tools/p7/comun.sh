# comun.sh: rutas, programas y variantes que comparten los scripts de P7
# (co-diseño, docs/codiseno.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con "source". Deja el directorio de trabajo en la raíz del
# repositorio y define:
#   B         productos intermedios (build/p7, ignorada por git)
#   M         mediciones (docs/mediciones/p7, versionada)
#   VARIANTES etiqueta|definiciones|programa de cada variante del SoC
# y las funciones programas (ensambla los cuatro programas) y versiones.

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$RAIZ"
export PATH=$HOME/herramientas/oss-cad-suite/bin:$PATH
PYTHON=${PYTHON:-python3}
B=build/p7
M=docs/mediciones/p7
mkdir -p "$B/sw" "$M"

R1_DEFS="-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA"
VARIANTES=(
  "r0||sw/trade.hex"
  "seg|-DESPINO_SEGMENTADO|sw/trade.hex"
  "barrel|-DESPINO_BARREL|$B/sw/trade_h0.hex"
  "barrel_xd|-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK|$B/sw/trade_xd_h0.hex"
  "r1|$R1_DEFS|$B/sw/fondo.hex"
  "r2|$R1_DEFS -DESPINO_VIGILANTE|$B/sw/fondo.hex"
)

# programas: los cuatro programas que se miden, ensamblados en B/sw
programas() {
  $PYTHON tools/pochoasm.py sw/trade.s -o "$B/sw/trade.hex" > /dev/null
  cmp -s "$B/sw/trade.hex" sw/trade.hex || { echo "FAIL: sw/trade.hex no corresponde a sw/trade.s"; exit 1; }
  $PYTHON tools/barrel/tabla.py 0 sw/trade.s > "$B/sw/trade_h0.s"
  $PYTHON tools/pochoasm.py "$B/sw/trade_h0.s" -o "$B/sw/trade_h0.hex" > /dev/null
  $PYTHON tools/barrel/tabla.py 0 sw/xd/trade_xd.s > "$B/sw/trade_xd_h0.s"
  $PYTHON tools/pochoasm.py "$B/sw/trade_xd_h0.s" -o "$B/sw/trade_xd_h0.hex" > /dev/null
  $PYTHON tools/pochoasm.py sw/fondo.s -o "$B/sw/fondo.hex" > /dev/null
}

versiones() {
  echo "Herramientas:"
  echo "  $(yosys -V)"
  echo "  $(nextpnr-ice40 --version 2>&1 | head -1)"
  echo "  $(verilator --version 2>/dev/null | head -1)"
  echo "  $(cc --version | head -1)"
  echo "Commit de partida: $(git rev-parse --short HEAD) (rama $(git rev-parse --abbrev-ref HEAD))"
}
