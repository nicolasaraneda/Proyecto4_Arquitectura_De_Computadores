# comun.sh: rutas, fuentes y funciones que comparten los scripts de la pieza B.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con "source". Deja el directorio de trabajo en la raíz del
# repositorio y define:
#   F           carpeta de esta pieza, relativa a la raíz
#   A           carpeta del barrel (factibilidad/a_barrel), que solo se lee
#   B           productos intermedios (F/build, ignorada por git)
#   M           mediciones (F/mediciones, versionada)
#   BARREL_SRC  fuentes del SoC con el core barrel: los seis primeros son del
#               repositorio y los tres últimos de factibilidad/a_barrel, todos
#               sin modificar
#   ARNES       el arnés de retorno compilado con el módulo del fondo
# y las funciones armar, compilar_fondo, correr_fondo, referencia, perdidos,
# serie_sintetica y versiones.

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$RAIZ"
export PATH=${OSS_CAD_SUITE:+$OSS_CAD_SUITE/bin:}$PATH

F=factibilidad/b_fondo_hilos
A=factibilidad/a_barrel
B=$F/build
M=$F/mediciones
PYTHON=${PYTHON:-python3}
JOBS=${JOBS:-5}
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
ARNES=$B/arnes

BARREL_SRC="rtl/pochoco_ram.v rtl/pochoco_spi_slave.v rtl/pochoco_periph.v \
rtl/espino_core/espino_decoder.v rtl/espino_core/espino_alu.v rtl/espino_core/espino_load_store_unit.v \
$A/rtl/pochoco_soc.v $A/rtl/espino_barrel_core.v $A/rtl/espino_barrel_regfile.v"

mkdir -p "$B" "$M"

# armar NOMBRE [VARIANTE...]: deja en B/prog/NOMBRE el programa (fondo.s),
# su imagen (fondo.hex, 512 palabras) y las direcciones de sus etiquetas
# (simbolos.vh). Sin variantes es sw/fondo.s tal cual.
armar() {
  local n=$1; shift
  local d=$B/prog/$n t f
  mkdir -p "$d"
  t=$(mktemp -d "$B/prog/.armar.XXXXXX")
  if [ $# -eq 0 ]; then cp $F/sw/fondo.s "$t/fondo.s"
  else $PYTHON $F/tools/variante.py $F/sw/fondo.s "$@" -o "$t/fondo.s" || return 1; fi
  $PYTHON tools/pochoasm.py "$t/fondo.s" -o "$t/fondo.hex" > /dev/null || return 1
  $PYTHON $F/tools/simbolos.py "$t/fondo.s" --vh "$t/simbolos.vh" || return 1
  # Solo se reemplaza lo que cambió: otra corrida puede estar leyendo estos archivos
  for f in fondo.s fondo.hex simbolos.vh; do cmp -s "$t/$f" "$d/$f" || mv "$t/$f" "$d/$f"; done
  rm -rf "$t"
}

# compilar_fondo NOMBRE: compila tb/tb_fondo.sv con Verilator para el programa
# B/prog/NOMBRE. El binario queda en B/sim/NOMBRE/obj/sim.
compilar_fondo() {
  local n=$1 d=$B/sim/$1
  mkdir -p "$d"
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_fondo -O3 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS "-DPROGRAMA=\"$B/prog/$n/fondo.hex\"" "-I$B/prog/$n" \
    --Mdir "$d/obj" -o sim "$CELLS_SIM" $BARREL_SRC $F/tb/tb_fondo.sv > "$d/verilator.log" 2>&1
}

# correr_fondo NOMBRE ETIQUETA SERIE NTICKS PERIODO_NS INICIO_NS: corre el
# binario de compilar_fondo. Deja ETIQUETA.log, ETIQUETA.ticks.csv y
# ETIQUETA.dec.csv en B/sim/NOMBRE.
correr_fondo() {
  local d=$B/sim/$1
  "$d/obj/sim" "+serie=$3" "+nticks=$4" "+periodo=$5" "+inicio=${6:-4000}" \
    "+ticks_csv=$d/$2.ticks.csv" "+dec_csv=$d/$2.dec.csv" > "$d/$2.log" 2>&1
}

# perdidos PERIODO_NS: precios que el programa no ve porque llegan durante el
# reset de encendido (ref/trader.py, ticks_perdidos): 2 a 0,1 ms, 1 a 1 ms y 10 ms.
perdidos() {
  $PYTHON -c "import sys; sys.path.insert(0, 'ref'); import trader; print(trader.ticks_perdidos($1))"
}

# referencia ESTRATEGIA SERIE NTICKS PERDIDOS SALIDA.csv [TRAZA.csv]: flujo de
# bytes de la referencia en C, en el formato del decisiones.csv del testbench.
referencia() {
  FONDO_TRAZA=${6:-} HILOS=1 "$ARNES" correr --estrategia "$1" --serie "$2" --nticks "$3" --perdidos "$4" -o "$5"
}

# serie_sintetica FAMILIA SEMILLA NTICKS: genera B/series/FAMILIA_SEMILLA_NTICKS.csv
# con ref/series.py y escribe su ruta. La serie depende solo de esos tres
# valores, así que si el archivo ya está completo no se vuelve a escribir.
serie_sintetica() {
  local s=$B/series/$1_$2_$3.csv
  mkdir -p "$B/series"
  if [ ! -f "$s" ] || [ "$(wc -l < "$s")" -ne $(($3 + 1)) ]; then
    $PYTHON ref/series.py "$1" --n "$3" --semilla "$2" -o "$s.tmp" > /dev/null && mv "$s.tmp" "$s"
  fi
  echo "$s"
}

versiones() {
  echo "Herramientas:"
  echo "  $(yosys -V)"
  echo "  $(iverilog -V 2>/dev/null | head -1)"
  echo "  $(verilator --version)"
  echo "Commit de partida: $(git rev-parse --short HEAD) (rama $(git rev-parse --abbrev-ref HEAD))"
}
