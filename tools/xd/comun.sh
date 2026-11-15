# comun.sh: rutas que comparten los scripts de la extensión de la ISA en
# custom-0 sobre el Espino barrel (docs/extension_isa.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con "source". Parte de tools/barrel/comun.sh (deja el directorio
# de trabajo en la raíz y define BASE_SRC, BARREL_SRC, CELLS_SIM, compilar_verif
# y las demás) y agrega:
#   TX, TBX, SWX, FOX  carpetas de los scripts, testbenches, programas y
#                      archivos formales de la extensión
#   BX                 productos intermedios (build/xd, ignorada por git)
#   MX                 mediciones (docs/mediciones/xd, versionada)
#   XD_DEFS            definiciones del barrel con las tres instrucciones
#   XD_SRC             fuentes del SoC con esas definiciones delante
#   XD_V               el archivo con los dos módulos de la extensión
#   XD_SUBCONJUNTOS    los subconjuntos que se prueban, como "etiqueta:defs"

source "$(dirname "${BASH_SOURCE[0]}")/../barrel/comun.sh"

TX=tools/xd
TBX=tb/xd
SWX=sw/xd
FOX=formal/xd
BX=build/xd
MX=docs/mediciones/xd
XD_V=rtl/espino_core/espino_xd.v
XD_DEFS="-DESPINO_BARREL -DESPINO_XD"
XD_SRC="$XD_DEFS $BASE_SRC"
# máscara Xd, etiqueta y definiciones de cada subconjunto
XD_SUBCONJUNTOS="1:emad:-DESPINO_XD_EMAD
2:devk:-DESPINO_XD_DEVK
3:emad_devk:-DESPINO_XD_EMAD,-DESPINO_XD_DEVK
4:mulstep:-DESPINO_XD_MULSTEP
5:emad_mulstep:-DESPINO_XD_EMAD,-DESPINO_XD_MULSTEP
6:devk_mulstep:-DESPINO_XD_DEVK,-DESPINO_XD_MULSTEP
7:todo:-DESPINO_XD"

mkdir -p "$BX/sw" "$MX"

# ensamblar_xd FUENTE.s SALIDA.hex [opciones]: ensambla con la extensión
ensamblar_xd() {
  local s=$1 h=$2; shift 2
  $PYTHON tools/pochoasm.py --xd "$@" "$s" -o "$h" > /dev/null
}
