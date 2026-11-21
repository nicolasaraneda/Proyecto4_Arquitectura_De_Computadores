# comun.sh: rutas y funciones que comparten los scripts de la puerta de R3 (C1 en
# los cuatro hilos del barrel, sw/c1.s, docs/c1_plan.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con "source". Parte de tools/barrel/comun.sh (deja el directorio de
# trabajo en la raíz y define BASE_SRC, CELLS_SIM, PYTHON y versiones) y agrega:
#   TC, BC, MC     carpetas de los scripts, de los productos intermedios
#                  (build/c1, ignorada por git) y de las mediciones
#   C1_DEFS        el hardware de R3: el de R2 con la tabla de 512 palabras
#   C1_SRC         fuentes del SoC con esas definiciones delante
#   C1_HEX         sw/c1.s ensamblado
#   SIM            tb/c1/tb_c1.sv compilado con Verilator
#   TABLA_HEX      sw/c1_tabla.hex
#   LIMITE         1131 ciclos: la mitad del presupuesto de la ronda 3

source "$(dirname "${BASH_SOURCE[0]}")/../barrel/comun.sh"

TC=tools/c1
BC=build/c1
MC=docs/mediciones/c1
R2_DEFS="-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA -DESPINO_VIGILANTE"
C1_DEFS="$R2_DEFS -DESPINO_TABLA_512"
C1_SIN_VIG="-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA -DESPINO_TABLA_512"
C1_SRC="$C1_DEFS $BASE_SRC"
C1_HEX=$BC/c1.hex
TABLA_HEX=sw/c1_tabla.hex
SIM=$BC/r3/obj/sim
LIMITE=1131
GEMELO_C1="build/gemelo --barrel --xd 3"

mkdir -p "$BC/series" "$MC"

# ensamblar_c1 [FUENTE.s] [SALIDA.hex]: por defecto sw/c1.s
ensamblar_c1() {
  $PYTHON tools/pochoasm.py "${1:-sw/c1.s}" -o "${2:-$C1_HEX}" > /dev/null
}

# compilar_sim: compila tb_c1.sv una vez. No depende del programa ni de la tabla.
compilar_sim() {
  if [ -x "$SIM" ] && [ -z "$(find rtl tb/c1/tb_c1.sv -newer "$SIM" \( -name '*.v' -o -name '*.sv' \) 2>/dev/null)" ]; then return 0; fi
  mkdir -p "$BC/r3"
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_c1 -O3 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS --Mdir "$BC/r3/obj" -o sim \
    "$CELLS_SIM" $C1_SRC tb/c1/tb_c1.sv > "$BC/r3/verilator.log" 2>&1 || { echo "FAIL: Verilator no compila (ver $BC/r3/verilator.log)"; return 1; }
}

# compilar_gemelo: el gemelo digital (ref/gemelo/gemelo.c)
compilar_gemelo() {
  cc -O2 -Wall -Wextra -Werror -o build/gemelo ref/gemelo/gemelo.c || { echo "FAIL: el gemelo no compila"; return 1; }
}

# serie_norm FAMILIA SEMILLA N: serie sintética normalizada entre 100 y 255. Imprime su ruta
serie_norm() {
  local f=$BC/series/$1-norm_$2_$3.csv
  [ -s "$f" ] || $PYTHON - "$1" "$2" "$3" "$f" <<'PY'
import sys
sys.path.insert(0, "ref"); sys.path.insert(0, "ref/cotas")
import comun, series
fam, sem, n, ruta = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
series.escribir_csv(ruta, comun.normalizar(series.lote(fam, 1, n, sem)[0]))
PY
  echo "$f"
}

# serie FAMILIA SEMILLA N: la serie cruda (sin normalizar). Imprime su ruta
serie() {
  local f=$BC/series/$1_$2_$3.csv
  [ -s "$f" ] || $PYTHON ref/series.py "$1" --n "$3" --semilla "$2" -o "$f" > /dev/null
  echo "$f"
}

# meta_ventana INICIO N: N ticks de la serie Meta desde INICIO, normalizados de nuevo
meta_ventana() {
  local f=$BC/series/meta_$1_$2.csv
  [ -s "$f" ] || $PYTHON - "$1" "$2" "$f" <<'PY'
import sys
sys.path.insert(0, "ref"); sys.path.insert(0, "ref/cotas")
import comun, market, series
ini, n, ruta = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
p = market.leer_serie("data/practica_meta.csv")
series.escribir_csv(ruta, comun.normalizar(p[ini:ini + n]))
PY
  echo "$f"
}

# reales: arma en build/c1/series las series de la clase del 18/11 (tesla.csv y amd.csv,
# como tools/reales.sh) desde $P4_DATOS. Falla si no hay datos.
reales() {
  local datos=${P4_DATOS:-$HOME/proyectos/datos_p4}
  [ -s "$BC/series/tesla.csv" ] && [ -s "$BC/series/amd.csv" ] && return 0
  $PYTHON - "${datos/#\~/$HOME}" "$BC/series" <<'PY'
import os, sys
sys.path.insert(0, "ref"); sys.path.insert(0, "ref/cotas")
import comun
datos, b = sys.argv[1], sys.argv[2]
def ventana(emp, fecha="2022-01-10", minuto=50, largo=20000):
    filas = [l.split(",") for l in open(os.path.join(datos, "minuto", emp + ".csv")).read().splitlines()[1:]]
    i = next(k for k, r in enumerate(filas) if r[0] == fecha and int(r[1]) == minuto)
    return comun.normalizar([float(r[2]) for r in filas[i:i + largo]])
def escribir(ruta, p):
    open(ruta, "w", newline="\n").write("tick,price\n" + "".join(f"{i},{x}\n" for i, x in enumerate(p)))
cap = [int(l.split(",")[1]) for l in open(os.path.join(datos, "capturas", "ronda_10ms_clase.csv")).read().splitlines()[1:]]
if ventana("TSLA") != cap:
    raise SystemExit("la ventana de TSLA no es la captura")
escribir(os.path.join(b, "tesla.csv"), cap)
escribir(os.path.join(b, "amd.csv"), ventana("AMD"))
PY
}

# caso CARPETA [argumentos de tools/c1/caso.py]: corre un caso por el RTL y deja la
# línea PASS o FAIL en CARPETA/resultado.txt
caso() {
  local d=$1; shift
  mkdir -p "$d"
  $PYTHON $TC/caso.py "$d" --sim "$SIM" "$@" > "$d/resultado.txt" 2>&1
}

# en_paralelo: lee comandos por la entrada estándar y los corre con JOBS procesos
en_paralelo() { xargs -P "${JOBS:-6}" -I{} bash -c "source $TC/comun.sh; {}"; }

# cabecera TITULO SCRIPT OBJETIVO
cabecera() {
  echo "$1"
  echo "Generado por $2 ($3). No editar a mano."
  echo
  versiones
  echo "  $(verilator --version)"
  echo "Hardware (R3): pochoco_soc con $C1_DEFS"
  echo "Programa: sw/c1.s (sha256 $(sha256sum sw/c1.s | cut -c1-16)...), tabla $TABLA_HEX (sha256 $(sha256sum $TABLA_HEX | cut -c1-16)...), referencia ref/c1/c1.py"
  echo
}

# cierre ARCHIVO: termina con error si el informe tiene algún FAIL
cierre() { ! grep -q "^FAIL" "$1"; }
