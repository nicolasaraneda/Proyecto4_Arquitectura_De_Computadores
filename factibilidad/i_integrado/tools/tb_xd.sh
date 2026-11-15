#!/usr/bin/env bash
# tb_xd.sh: las instrucciones nuevas ejecutadas por los cuatro hilos del
# barrel, contra el modelo en Python de factibilidad/d_isa (ref/xd.py).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Para cada variante de integración compila una vez el SoC con
# tb/tb_xd_barrel.sv (Icarus) y corre:
#   - NPROG programas con los cuatro hilos a la vez, cada hilo con un
#     programa distinto (tools/gen_prog_hilos.py);
#   - NSOLO programas por hilo con ese hilo solo y los otros tres en un lazo
#     vacío.
# En cada corrida se compara cada escritura al banco de registros de cada hilo
# con la lista que predice el modelo. Los programas traen rd = x0, rd igual a
# un operando, dos instrucciones nuevas seguidas y el uso inmediato del
# resultado.
#
# Variantes: los subconjuntos de tools/variantes.txt, la configuración I1 (con
# vigilante y tabla) y, para dejar probado el camino de xd_unit con todo lo
# que la copia del core admite, dos conjuntos completos que no caben en la
# FPGA (todas las instrucciones con todos los k).
#
# Uso: factibilidad/i_integrado/tools/tb_xd.sh [NPROG] [NSOLO] [FILTRO]
# Por defecto 50 y 5. Resultado en mediciones/tb_xd.txt (si no hay FILTRO).
# Variable JOBS: simulaciones en paralelo (5).
set -uo pipefail
source "$(dirname "$0")/comun.sh"

NPROG=${1:-50}
NSOLO=${2:-5}
FILTRO=${3:-.}
JOBS=${JOBS:-5}
O=$B/xd
mkdir -p "$O"

# una ETIQUETA SEMILLA SOLO "definiciones": genera el programa y lo corre
una() {
  local etq=$1 s=$2 solo=$3 defs=$4 n=$O/$1/p_s$2_$3 r arg="" t
  r=$($PYTHON $I/tools/gen_prog_hilos.py "--defs=$defs" --semilla "$s" --solo "$solo" --hex "$n.hex" --esperado "$n") || { echo "ERROR generador" > "$n.log"; return 0; }
  echo "$r" > "$n.gen"
  for t in 0 1 2 3; do arg="$arg +n$t=$(echo "$r" | tr ' ' '\n' | sed -n "s/^h$t=\([0-9]*\):.*/\1/p")"; done
  vvp -n "$O/$etq/sim.vvp" "+hex=$n.hex" "+esp=$n" $arg > "$n.log" 2>&1
  return 0
}
export -f una
export O I PYTHON

FALLAS=0
# variante ETIQUETA "definiciones" "descripción"
variante() {
  local etq=$1 defs=$2 desc=$3 lista s t
  [[ "$etq" =~ $FILTRO ]] || return 0
  rm -rf "${O:?}/${etq:?}"; mkdir -p "$O/$etq"
  if ! iverilog -g2012 -s tb_xd_barrel $defs -o "$O/$etq/sim.vvp" "$CELLS_SIM" $INT_SRC $I/tb/tb_xd_barrel.sv > "$O/$etq/iverilog.log" 2>&1; then
    printf "FAIL %-14s no compila (ver %s)\n" "$etq" "$O/$etq/iverilog.log"; FALLAS=$((FALLAS + 1)); return 0
  fi
  lista=$O/$etq/corridas.txt; : > "$lista"
  for s in $(seq 1 "$NPROG"); do echo "$s -1" >> "$lista"; done
  for t in 0 1 2 3; do for s in $(seq 1 "$NSOLO"); do echo "$((100000 + s)) $t" >> "$lista"; done; done
  xargs -P "$JOBS" -L 1 bash -c 'una "$0" "$1" "$2" "$3"' "$etq" < <(awk -v d="$defs" '{printf "%s %s \"%s\"\n", $1, $2, d}' "$lista" | sed "s/^/ /" | sed 's/^ //')
  $PYTHON - "$O/$etq" "$etq" "$defs" "$desc" <<'PY'
import glob, re, sys
d, etq, defs, desc = sys.argv[1:5]
corridas = sorted(glob.glob(d + "/p_s*.gen"))
ok = 0; esc = [0] * 4; nuevas = [0] * 4; malas = []
for g in corridas:
    log = open(g[:-4] + ".log", errors="replace").read()
    if re.search(r"^PASS tb_xd_barrel", log, re.M):
        ok += 1
        for t, (e, n) in enumerate(re.findall(r"h\d=(\d+):(\d+)", open(g).read())):
            esc[t] += int(e); nuevas[t] += int(n)
    else:
        malas.append(g[:-4] + ".log")
estado = "PASS" if corridas and not malas else "FAIL"
print(f"{estado} {etq:<14} {ok} de {len(corridas)} programas; instrucciones nuevas por hilo {nuevas[0]} {nuevas[1]} {nuevas[2]} {nuevas[3]} "
      f"(total {sum(nuevas)}); escrituras identicas al modelo por hilo {esc[0]} {esc[1]} {esc[2]} {esc[3]} (total {sum(esc)})")
print(f"     {desc}   [{defs}]")
for m in malas[:3]:
    print("     falla:", m)
    for l in open(m, errors="replace").read().splitlines()[:4]:
        print("       ", l)
sys.exit(0 if estado == "PASS" else 1)
PY
  [ $? = 0 ] || FALLAS=$((FALLAS + 1))
}

informe() {
echo "Instrucciones nuevas en los cuatro hilos del barrel, contra el modelo ref/xd.py de factibilidad/d_isa"
echo "Generado por factibilidad/i_integrado/tools/tb_xd.sh $NPROG $NSOLO (make tb-xd). No editar a mano."
echo
versiones
echo
echo "Por variante: $NPROG programas con los cuatro hilos a la vez (un programa distinto por hilo) y $NSOLO programas"
echo "por hilo con ese hilo solo. Cada escritura al banco de registros de cada hilo se compara con el modelo."
echo
variante emad_k5      "$(defs_de emad_k5)"      "(a) emad, k = 5"
variante media_k5     "$(defs_de media_k5)"     "emad y devk, k = 5"
variante media_mul    "$(defs_de media_mul)"    "(b) emad, devk y mulstep en el sumador de la ALU"
variante alu_todo     "$(defs_de alu_todo)"     "(c) lo anterior más los carriles de bandas en la ALU"
variante media_bandas "$(defs_de media_bandas)" "(d) lo anterior con los carriles de bandas en unidad aparte"
variante media_muldiv "$(defs_de media_muldiv)" "(e) el recomendado más divstep"
variante alu_todo_div "$(defs_de alu_todo_div)" "(e) carriles en la ALU más divstep"
variante bandas_div   "$(defs_de bandas_div)"   "(e) carriles en unidad aparte más divstep (no cabe en la FPGA)"
variante i1a          "$(defs_de media_mul) -DI_VIGILANTE -DI_TABLA=1" "I1: el recomendado con vigilante y tabla de 256 x 16"
variante i1b          "$(defs_de media_mul) -DI_VIGILANTE -DI_TABLA=2" "I1 con la tabla en otras 512 palabras de datos"
variante todo_autonomo "-DXD_EMA=5 -DXD_SRAK=5 -DXD_SIMD=31 -DXD_MULSTEP -DXD_DIVSTEP -DXD_MULC=16" "todas las instrucciones con todos los k, en unidad aparte (no cabe en la FPGA)"
variante todo_alu     "-DXD_EMA=5 -DXD_EMAALU -DXD_EMAD=5 -DXD_DEVK=5 -DXD_SRAK=5 -DXD_SIMD=31 -DXD_MULSTEPALU -DXD_DIVSTEP -DXD_MULC=16" "todas con todos los k, compartiendo la ALU donde se puede (no cabe en la FPGA)"
echo
if [ "$FALLAS" = 0 ]; then echo "RESULTADO: PASS, todas las variantes coinciden con el modelo en los cuatro hilos"
else echo "RESULTADO: FAIL, $FALLAS variantes con error"; fi
}

if [ "$FILTRO" = . ]; then informe | tee "$M/tb_xd.txt"; grep -q "^RESULTADO: PASS" "$M/tb_xd.txt"
else informe; fi
