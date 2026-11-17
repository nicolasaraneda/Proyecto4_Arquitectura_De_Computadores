#!/usr/bin/env bash
# ro_custom0.sh: tabla de solo lectura, palabras de custom-0 sin efecto y
# bordes de emad y devk sobre el hardware exacto de R1 y de R2 (revisión P10,
# docs/revision_p10.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Genera el programa con tools/p10/gen_ro_custom0.py, lo ensambla y lo corre
# con tb/p10/tb_p10_soc.sv en Icarus, una vez con las definiciones de R1 y otra
# con las de R2. Termina con error si algo falla.
#
# Uso: tools/p10/ro_custom0.sh   (o make p10-ro-custom0)
set -uo pipefail
cd "$(dirname "$0")/../.."
O=build/p10/ro_custom0
mkdir -p "$O"
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
SRC=$(for f in rtl/*.v rtl/espino_core/*.v; do case "$f" in rtl/00_*) ;; *) printf '%s ' "$f" ;; esac; done)
R1="-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA"
mal=0

python3 tools/p10/gen_ro_custom0.py "$O/prog.s" "$O/esperado.txt" || exit 1
python3 tools/pochoasm.py "$O/prog.s" -o "$O/prog.hex" || exit 1
for hw in r1 r2; do
  defs=$R1; [ $hw = r2 ] && defs="$R1 -DESPINO_VIGILANTE"
  iverilog -g2012 -s tb_p10_soc -o "$O/sim_$hw" "-DPROGRAMA=\"$O/prog.hex\"" "-DESPERADO=\"$O/esperado.txt\"" \
    $defs "$CELLS_SIM" $SRC tb/p10/tb_p10_soc.sv > "$O/iverilog_$hw.log" 2>&1 || { echo "FAIL $hw: no compila"; mal=1; continue; }
  vvp -n "$O/sim_$hw" > "$O/$hw.log" 2>&1
  echo "--- $hw ($defs)"
  grep -E "^(PASS|FAIL|Escrituras|RESUMEN)" "$O/$hw.log"
  grep -q "^RESUMEN fallas=0" "$O/$hw.log" || mal=1
done

# Controles negativos: la prueba tiene que fallar si la tabla no existe (los
# stores a 0x8002_0004 caen en los LED) o si el core sí tiene mulstep (la
# palabra de mulstep escribe rd).
control() {   # control NOMBRE DEFINICIONES
  iverilog -g2012 -s tb_p10_soc -o "$O/sim_$1" "-DPROGRAMA=\"$O/prog.hex\"" "-DESPERADO=\"$O/esperado.txt\"" \
    $2 "$CELLS_SIM" $SRC tb/p10/tb_p10_soc.sv > "$O/iverilog_$1.log" 2>&1 || { echo "FAIL control $1: no compila"; mal=1; return; }
  vvp -n "$O/sim_$1" > "$O/$1.log" 2>&1
  if grep -q "^RESUMEN fallas=0" "$O/$1.log"; then echo "FAIL control negativo $1: la prueba no lo detecta"; mal=1
  else echo "PASS control negativo $1: detectado ($(grep -c '^FAIL' "$O/$1.log") comprobaciones fallan)"; fi
}
control sin_tabla "-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK"
control con_mulstep "$R1 -DESPINO_XD_MULSTEP"

[ $mal = 0 ] && echo "PASS p10-ro-custom0" || echo "FAIL p10-ro-custom0"
exit $mal
