#!/usr/bin/env bash
# medir_cpi.sh: CPI y MIPS del Espino barrel con el mix de la clase 7, contra
# el Espino base y el pipeline de 3 etapas medidos en la misma corrida.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Mide cuatro casos, todos con el lazo de 20 instrucciones de sw/mix_clase7.s
# (20 % de loads y 15 % de saltos tomados):
#   base          SoC original, tb/tb_cpi.sv del repositorio, sin modificar.
#   segmentado    lo mismo con -DESPINO_SEGMENTADO.
#   barrel x4     el lazo en los cuatro hilos (sw/mix_clase7_x4.s), con
#                 tb/tb_barrel.sv de esta carpeta.
#   barrel x1     el lazo en el hilo 0 y los otros tres en un lazo vacío
#                 (sw/mix_clase7.s sin modificar, con la tabla de arranque).
#                 Es el caso en que el barrel pierde: solo cuenta como trabajo
#                 útil lo que hace el hilo 0.
#
# Uso: factibilidad/a_barrel/tools/medir_cpi.sh   (o make cpi)
# Resultado en factibilidad/a_barrel/mediciones/cpi.txt.
set -euo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/cpi
mkdir -p "$O"
programas
CICLOS=${CICLOS:-46004}

# Base y segmentado, con el testbench y el programa del repositorio
ref() {   # ref VARIANTE [definiciones]
  local v=$1; shift
  iverilog -g2012 -s tb_cpi "$@" "-DPROGRAMA=\"$B/sw/mix_clase7.hex\"" -DNTICKS=20 -o "$O/$v.vvp" "$CELLS_SIM" $BASE_SRC tb/tb_cpi.sv
  vvp -n "$O/$v.vvp" > "$O/$v.log"
  grep -q "^PASS el modelo de costo" "$O/$v.log" || { echo "FAIL: el modelo de costo no coincide ($v)"; exit 1; }
}
bar() {   # bar NOMBRE HEX
  iverilog -g2012 -s tb_barrel "-DPROGRAMA=\"$2\"" -DCICLOS="$CICLOS" -o "$O/$1.vvp" "$CELLS_SIM" $BARREL_SRC $A/tb/tb_barrel.sv
  vvp -n "$O/$1.vvp" > "$O/$1.log"
  grep -q "^RESULTADO: PASS" "$O/$1.log" || { echo "FAIL: tb_barrel ($1)"; exit 1; }
}
ref base &
ref segmentado -DESPINO_SEGMENTADO &
bar barrel_x4 "$B/sw/mix_clase7_x4.hex" &
bar barrel_x1 "$B/sw/mix_clase7_h0.hex" &
wait

{
echo "CPI y MIPS con el mix de la clase 7: Espino base, pipeline de 3 etapas y barrel"
echo "Generado por factibilidad/a_barrel/tools/medir_cpi.sh (make cpi). No editar a mano."
echo
versiones
echo
$PYTHON - "$O" <<'PYEOF'
import re, sys
D = sys.argv[1]
F = 25.0   # MHz

def ref(nombre):
    t = open(f"{D}/{nombre}.log").read()
    g = lambda pat: int(re.search(pat + r"\s+(\d+)", t).group(1))
    return dict(ic=g(r"Instrucciones \(IC\):"), ciclos=g(r"Ciclos:"), loads=g(r"loads:"),
                tomados=g(r"branches tomados:") + g(r"jal y jalr:"))

def barrel(nombre):
    t = open(f"{D}/{nombre}.log").read()
    hilos = []
    for m in re.finditer(r"^\s+([0-3])\s+(\d+)\s+(\d+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", t, re.M):
        h, ic, cic, cpi, ld, st, bt, bn, jp, ot = m.groups()
        hilos.append(dict(ic=int(ic), ciclos=int(cic), loads=int(ld), tomados=int(bt) + int(jp)))
    return hilos

b, s = ref("base"), ref("segmentado")
x4, x1 = barrel("barrel_x4"), barrel("barrel_x1")

def fila(nombre, ic, ciclos, loads, tomados, nota=""):
    cpi = ciclos / ic
    print(f"  {nombre:<44} {ic:>7} {ciclos:>7} {cpi:>6.3f} {F / cpi:>6.2f}  {100 * loads / ic:>5.1f} % {100 * tomados / ic:>5.1f} %  {nota}")
    return cpi

print("1. CPI medido con el lazo de sw/mix_clase7.s")
print()
print(f"  {'Caso':<44} {'IC':>7} {'Ciclos':>7} {'CPI':>6} {'MIPS':>6}  {'loads':>7} {'tomados':>7}")
cb = fila("Espino base (tb/tb_cpi.sv)", b["ic"], b["ciclos"], b["loads"], b["tomados"])
cs = fila("Pipeline de 3 etapas (tb/tb_cpi.sv)", s["ic"], s["ciclos"], s["loads"], s["tomados"])
ic4 = sum(h["ic"] for h in x4)
c4 = fila("Barrel, mix en los 4 hilos: agregado", ic4, x4[0]["ciclos"], sum(h["loads"] for h in x4), sum(h["tomados"] for h in x4))
for t, h in enumerate(x4):
    fila(f"    hilo {t}", h["ic"], h["ciclos"], h["loads"], h["tomados"])
c1 = fila("Barrel, mix solo en el hilo 0: trabajo util", x1[0]["ic"], x1[0]["ciclos"], x1[0]["loads"], x1[0]["tomados"],
          "(los otros 3 hilos giran en un lazo vacio)")
print()
print("  MIPS = 25 MHz / CPI. En el barrel de un hilo solo se cuentan las instrucciones del hilo 0.")
print()
print("2. Comparacion")
print()
print(f"  {'':<34} {'Base':>8} {'Segmentado':>11} {'Barrel x4':>10} {'Barrel x1':>10} {'Clase 7 (3 etapas, estimado)':>30}")
print(f"  {'CPI con el mix':<34} {cb:>8.3f} {cs:>11.3f} {c4:>10.3f} {c1:>10.3f} {1.5:>30.1f}")
print(f"  {'MIPS a 25 MHz':<34} {F / cb:>8.2f} {F / cs:>11.2f} {F / c4:>10.2f} {F / c1:>10.2f} {16.7:>30.1f}")
print(f"  {'Speedup contra el base':<34} {1.0:>8.2f} {cb / cs:>11.2f} {cb / c4:>10.2f} {cb / c1:>10.2f} {2.35 / 1.5:>30.2f}")
print(f"  {'Speedup contra el segmentado':<34} {cs / cb:>8.2f} {1.0:>11.2f} {cs / c4:>10.2f} {cs / c1:>10.2f}")
print(f"  {'Ciclos de ALU, load, salto tomado':<34} {'2, 3, 3':>8} {'1, 2, 2':>11} {'1, 1, 1':>10} {'4, 4, 4':>10} {'1, 2, 3':>30}")
print()
print("3. Ppeak con la definicion de la clase 7 (f x instrucciones por ciclo x operaciones por instruccion x nucleos)")
print()
print(f"  Espino base:           25 MHz x 0,5  x 1 x 1          = 12,5  MOPS")
print(f"  Pipeline de 3 etapas:  25 MHz x 1    x 1 x 1          = 25    MOPS (solo con instrucciones de ALU; con el mix {F / cs:.2f})")
print(f"  Barrel, 4 hilos:       25 MHz x 0,25 x 1 x 4 hilos    = 25    MOPS (con cualquier mix: medido {F / c4:.2f})")
print(f"  Barrel, 1 hilo:        25 MHz x 0,25 x 1 x 1 hilo     =  6,25 MOPS (medido {F / c1:.2f})")
print()
print("  El barrel no sube el techo del segmentado. Lo alcanza con cualquier mezcla de")
print("  instrucciones, siempre que los cuatro hilos tengan trabajo. Con un solo hilo")
print("  activo rinde la cuarta parte.")
PYEOF
echo
echo "4. Salida de tb_barrel con el mix en los cuatro hilos"
echo
sed -n '1,/^RESULTADO/p' "$O/barrel_x4.log" | sed 's/^/  /'
} | tee "$M/cpi.txt"
