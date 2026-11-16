# comun.sh: rutas y funciones que comparten los scripts del fondo en un chip
# (sw/fondo.s, docs/fondo.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con "source". Parte de tools/barrel/comun.sh (deja el directorio
# de trabajo en la raíz y define BASE_SRC, CELLS_SIM, PYTHON y versiones) y
# agrega:
#   TF, BF, MF     carpetas de los scripts, de los productos intermedios
#                  (build/fondo, ignorada por git) y de las mediciones
#   FONDO_DEFS     definiciones del hardware en que corre el fondo: el barrel
#                  con emad y devk, sin mulstep (decisión T58)
#   FONDO_SRC      fuentes del SoC con esas definiciones delante
#   FONDO_HEX      el programa ensamblado
#   SIM            el testbench tb/fondo/tb_fondo.sv compilado con Verilator

source "$(dirname "${BASH_SOURCE[0]}")/../barrel/comun.sh"

TF=tools/fondo
BF=build/fondo
MF=docs/mediciones/fondo
FONDO_DEFS="-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK"
FONDO_SRC="$FONDO_DEFS $BASE_SRC"
FONDO_HEX=$BF/fondo.hex
SIM=$BF/obj/sim

mkdir -p "$BF/series" "$MF"

# ensamblar_fondo [FUENTE.s] [SALIDA.hex]: por defecto sw/fondo.s
ensamblar_fondo() {
  $PYTHON tools/pochoasm.py "${1:-sw/fondo.s}" -o "${2:-$FONDO_HEX}" > /dev/null
}

# compilar_sim: compila tb_fondo.sv una vez. No depende del programa.
compilar_sim() {
  if [ -x "$SIM" ] && [ -z "$(find rtl tb/fondo/tb_fondo.sv -newer "$SIM" -name '*.v' -o -newer "$SIM" -name '*.sv' 2>/dev/null)" ]; then return 0; fi
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_fondo -O3 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS --Mdir "$BF/obj" -o sim \
    "$CELLS_SIM" $FONDO_SRC tb/fondo/tb_fondo.sv > "$BF/verilator.log" 2>&1 || { echo "FAIL: Verilator no compila (ver $BF/verilator.log)"; return 1; }
}

# simbolos FUENTE.s: plusargs con las direcciones de las etiquetas
simbolos() { $PYTHON $TF/simbolos.py "${1:-sw/fondo.s}" --plusargs; }

# serie FAMILIA SEMILLA N: genera la serie si no existe e imprime su ruta
serie() {
  local f=$BF/series/$1_$2_$3.csv
  [ -s "$f" ] || $PYTHON ref/series.py "$1" --n "$3" --semilla "$2" -o "$f" > /dev/null
  echo "$f"
}

# caso CARPETA FUENTE.s SERIE NTICKS PERIODO_NS INICIO_NS [argumentos de revisar.py]
# Ensambla el programa si hace falta, corre el testbench y compara con la
# referencia. Deja la línea PASS o FAIL en CARPETA/resultado.txt.
caso() {
  local d=$1 fuente=$2 ser=$3 nt=$4 per=$5 ini=$6; shift 6
  mkdir -p "$d"
  local hex=$d/programa.hex
  $PYTHON tools/pochoasm.py "$fuente" -o "$hex" > /dev/null || { echo "FAIL $(basename "$d"): no ensambla" > "$d/resultado.txt"; return 1; }
  "$SIM" +PROGRAMA="$hex" $(simbolos "$fuente") +SERIE="$ser" +NTICKS="$nt" +PERIODO_NS="$per" +INICIO_NS="$ini" \
    +SALIDA="$d/salida.csv" +ESTADO="$d/estado.csv" ${PLUS:-} > "$d/tb.log" 2>&1
  $PYTHON $TF/revisar.py "$d" --serie "$ser" --nticks "$nt" --periodo-ns "$per" --inicio-ns "$ini" "$@" > "$d/resultado.txt" 2>&1
}

# en_paralelo: lee comandos por la entrada estándar y los corre con JOBS procesos
en_paralelo() { xargs -P "${JOBS:-6}" -I{} bash -c "source $TF/comun.sh; {}"; }

# cabecera TITULO SCRIPT OBJETIVO
cabecera() {
  echo "$1"
  echo "Generado por $2 ($3). No editar a mano."
  echo
  versiones
  echo "  $(verilator --version)"
  echo "Hardware: pochoco_soc con $FONDO_DEFS"
  echo "Programa: sw/fondo.s (sha256 $(sha256sum sw/fondo.s | cut -c1-16)...), referencia ref/fondo.py"
  echo
}

# cierre ARCHIVO: termina con error si el informe tiene algún FAIL
cierre() { ! grep -q "^FAIL" "$1"; }
