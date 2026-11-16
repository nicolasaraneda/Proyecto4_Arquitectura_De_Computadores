#!/usr/bin/env bash
# medir_espino.sh: mediciones del Espino base y del segmentado con los mismos
# programas.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Deja en docs/mediciones/espino_segmentado.txt:
#   1. Celdas, BRAM y frecuencia máxima en 10 semillas de nextpnr de cada
#      variante, y cuánto recupera el recorte del contador de programa.
#   2. CPI medido en simulación (tb/tb_cpi.sv) con tres programas: sw/trade.s,
#      sw/mix_clase7.s (el mix de la clase 7) y un programa aleatorio. En cada
#      uno se comprueba el modelo de costo por clase de instrucción.
#   3. MIPS y Ops/s con las definiciones de la clase 7, y la comparación con
#      lo que la clase estimó para un pipeline de 3 etapas.
#
# Uso, desde la raíz del repositorio: tools/medir_espino.sh [SEMILLAS]
set -euo pipefail

SEMILLAS=${1:-10}
PYTHON=${PYTHON:-python3}
SRC=$(ls rtl/*.v rtl/espino_core/*.v | grep -v '^rtl/00_')
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
D=build/medir_espino
SALIDA=docs/mediciones/espino_segmentado.txt
mkdir -p "$D" docs/mediciones

# --- Programas ------------------------------------------------------------------
$PYTHON tools/pochoasm.py sw/mix_clase7.s -o "$D/mix_clase7.hex" > /dev/null
$PYTHON tools/prog_aleatorio.py --original 1 -o "$D/aleatorio.s"   # el de las cifras publicadas (T49)
$PYTHON tools/pochoasm.py --allow-shifts "$D/aleatorio.s" -o "$D/aleatorio.hex" > /dev/null
mkdir -p build/rom
$PYTHON tools/pochoasm.py sw/trade.s -o build/rom/trade.hex --rom build/rom/pochoco_rom.v > /dev/null

# --- 1. Recursos y frecuencia máxima ---------------------------------------------
{
  tools/medir_variante.sh base "$SEMILLAS"
  PARAMS="PcW=11" tools/medir_variante.sh base_pc11 "$SEMILLAS"
  DEFS=-DESPINO_SEGMENTADO PARAMS="PcW=32" tools/medir_variante.sh segmentado_pc32 "$SEMILLAS"
  DEFS=-DESPINO_SEGMENTADO tools/medir_variante.sh segmentado "$SEMILLAS"
  DEFS=-DESPINO_ROM EXTRA=build/rom/pochoco_rom.v tools/medir_variante.sh rom "$SEMILLAS"
} > "$D/recursos.txt"

# --- 2. CPI ------------------------------------------------------------------------
cpi() {   # cpi VARIANTE PROGRAMA HEX NTICKS [defs]
  local v=$1 p=$2 hex=$3 nt=$4; shift 4
  iverilog -g2012 -s tb_cpi "$@" "-DPROGRAMA=\"$hex\"" -DNTICKS="$nt" -o "$D/${v}_$p.vvp" "$CELLS_SIM" $SRC tb/tb_cpi.sv
  vvp -n "$D/${v}_$p.vvp" > "$D/${v}_$p.log"
  grep -q "^PASS el modelo de costo" "$D/${v}_$p.log" || { echo "FAIL: el modelo de costo no coincide ($v, $p)"; exit 1; }
}
for v in base segmentado; do
  defs=""; [ $v = segmentado ] && defs="-DESPINO_SEGMENTADO"
  cpi $v trade sw/trade.hex 200 $defs &
  cpi $v mix_clase7 "$D/mix_clase7.hex" 20 $defs &
  cpi $v aleatorio "$D/aleatorio.hex" 20 $defs &
done
wait

dato() { grep "^$2" "$D/$1.log" | head -1 | sed -E 's/.*: *//; s/ ciclos.*//'; }

# --- Informe --------------------------------------------------------------------------
$PYTHON - "$D" > "$SALIDA" <<'PYEOF'
import re, subprocess, sys
D = sys.argv[1]

def leer(nombre):
    t = open(f"{D}/{nombre}.log").read()
    g = lambda pat: int(re.search(pat + r"\s+(\d+)", t).group(1))
    r = dict(ic=g(r"Instrucciones \(IC\):"), ciclos=g(r"Ciclos:"), loads=g(r"loads:"), stores=g(r"stores:"),
             br_t=g(r"branches tomados:"), br_nt=g(r"branches no tomados:"), jump=g(r"jal y jalr:"), otras=g(r"otras:"))
    r["dif"] = int(re.search(r"diferencia con lo medido: (-?\d+)", t).group(1))
    return r

def ver(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip().splitlines()[0]

print("Espino base contra Espino segmentado (pipeline de 3 etapas)")
print("Generado por tools/medir_espino.sh (make medir-espino). No editar a mano.")
print()
print("Herramientas:")
print("  " + ver(["yosys", "-V"]))
print("  " + ver(["nextpnr-ice40", "--version"]))
print("  " + ver(["iverilog", "-V"]))
print()
print("1. Recursos y frecuencia maxima (nextpnr --hx1k --package vq100 --freq 25, 10 semillas)")
print()
filas = {}
for linea in open(f"{D}/recursos.txt"):
    m = re.match(r"(\S+)\s+celdas\s+(\d+) de 1280, BRAM\s+(\d+) de 16, LUT4\s+(\d+), fmax min\s+([\d.]+) mediana\s+([\d.]+) max\s+([\d.]+) MHz, cierran a 25 MHz (\d+) de (\d+)", linea)
    if m:
        filas[m.group(1)] = m.groups()
nombres = [("base", "Espino base (el del bitstream de competencia)"),
           ("base_pc11", "Espino base con contador de programa de 11 bits"),
           ("segmentado_pc32", "Segmentado con contador de programa de 32 bits"),
           ("segmentado", "Segmentado, fetch en flanco de bajada (BRAM)"),
           ("rom", "Segmentado, programa en ROM combinacional")]
print(f"  {'Variante':<50} {'Celdas':>6} {'BRAM':>4} {'Fmax min':>9} {'mediana':>8} {'max':>7}  Cierran")
for k, texto in nombres:
    f = filas[k]
    print(f"  {texto:<50} {f[1]:>6} {f[2]:>4} {f[4]:>9} {f[5]:>8} {f[6]:>7}  {f[7]} de {f[8]}")
c = lambda k: int(filas[k][1])
print()
print(f"  Recorte del contador de programa y sus sumadores (32 a 11 bits):")
print(f"    en el base:       {c('base')} a {c('base_pc11')} celdas, recupera {c('base') - c('base_pc11')}")
print(f"    en el segmentado: {c('segmentado_pc32')} a {c('segmentado')} celdas, recupera {c('segmentado_pc32') - c('segmentado')}")
print(f"  Costo del pipeline sin el recorte: {c('segmentado_pc32') - c('base'):+d} celdas sobre el base")
print(f"  Segmentado final contra el base:   {c('segmentado') - c('base'):+d} celdas. Quedan libres {1280 - c('segmentado')} de 1280")
print(f"  ROM combinacional contra BRAM:     {c('rom') - c('segmentado'):+d} celdas y {int(filas['rom'][2]) - int(filas['segmentado'][2]):+d} BRAM")
print()
print("2. CPI medido en simulacion (tb/tb_cpi.sv), con los mismos programas")
print()
print(f"  {'Programa':<12} {'Core':<11} {'IC':>8} {'Ciclos':>8} {'CPI':>7}  {'loads':>6} {'tomados':>8}  Modelo de costo")
res = {}
for p in ("trade", "mix_clase7", "aleatorio"):
    for v in ("base", "segmentado"):
        r = leer(f"{v}_{p}")
        res[(v, p)] = r
        k = 2 if v == "base" else 1
        tom = r["br_t"] + r["jump"]
        print(f"  {p:<12} {v:<11} {r['ic']:>8} {r['ciclos']:>8} {r['ciclos'] / r['ic']:>7.4f}  {100 * r['loads'] / r['ic']:>5.1f}% {100 * tom / r['ic']:>7.1f}%  "
              f"{k}*IC + loads + tomados, diferencia {r['dif']} ciclos")
print()
print("  El modelo de costo coincide ciclo por ciclo en los tres programas, asi que el costo por clase es:")
print("    Clase de instruccion          Base   Segmentado   Estimado en la clase 7 (pipeline de 3 etapas)")
print("    ALU (registro o inmediato)       2            1   1")
print("    store                            2            1   1")
print("    load                             3            2   2")
print("    salto no tomado                  2            1   1")
print("    salto tomado, jal, jalr          3            2   3")
print()
mb, ms = res[("base", "mix_clase7")], res[("segmentado", "mix_clase7")]
cb, cs = mb["ciclos"] / mb["ic"], ms["ciclos"] / ms["ic"]
tb_, ts = res[("base", "trade")], res[("segmentado", "trade")]
print("3. Comparacion con la clase 7 (reloj de 25 MHz)")
print()
print(f"  {'':<34} {'Base':>8} {'Segmentado':>11} {'Clase 7, estimado':>18}")
print(f"  {'CPI con el mix de la clase':<34} {cb:>8.3f} {cs:>11.3f} {'1,5 (base 2,35)':>18}")
print(f"  {'MIPS con el mix (25 / CPI)':<34} {25 / cb:>8.2f} {25 / cs:>11.2f} {'16,7':>18}")
print(f"  {'Ppeak en MOPS (25 x 1/CPI de ALU)':<34} {25 / 2:>8.2f} {25 / 1:>11.2f} {'25 (CPI ideal 1)':>18}")
print(f"  {'Speedup en el mix':<34} {1.0:>8.2f} {cb / cs:>11.2f} {2.35 / 1.5:>18.2f}")
print(f"  {'CPI de trade.s (con el sondeo)':<34} {tb_['ciclos'] / tb_['ic']:>8.3f} {ts['ciclos'] / ts['ic']:>11.3f}")
print()
print("  Ppeak = f x instrucciones por ciclo x operaciones por instruccion x nucleos, con una")
print("  operacion por instruccion y un nucleo. El pipeline medido supera la estimacion de la")
print("  clase porque el salto tomado cuesta 2 ciclos y no 3: la instruccion se lee en el flanco")
print("  de bajada, medio ciclo despues de que cambia el contador de programa, y no hay una")
print("  etapa de fetch de un ciclo completo que anular.")
PYEOF
grep -q "FAIL" "$SALIDA" && { echo "FAIL: ver $SALIDA"; exit 1; }
cat "$SALIDA"
