#!/usr/bin/env bash
# modo_spi.sh: el byte que lee una maestra SPI de modo 0 y de modo 3 con el
# hardware de R1 (revisión P10, docs/revision_p10.md, observación 4).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Exploración: corre tb/p10/tb_p10_modo.sv con sw/fondo.s en los dos modos e
# informa cuántas transacciones leyeron un byte distinto del que el esclavo
# tenía en DECISION. En modo 0 tienen que ser cero. Termina con error solo si
# el modo 0 falla.
#
# Uso: tools/p10/modo_spi.sh   (o make p10-modo-spi)
set -uo pipefail
cd "$(dirname "$0")/../.."
O=build/p10/modo_spi
mkdir -p "$O"
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
SRC=$(for f in rtl/*.v rtl/espino_core/*.v; do case "$f" in rtl/00_*) ;; *) printf '%s ' "$f" ;; esac; done)
R1="-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA"
python3 tools/pochoasm.py sw/fondo.s -o "$O/fondo.hex" > /dev/null || exit 1
mal=0
for m in 0 3; do
  iverilog -g2012 -s tb_p10_modo -o "$O/sim_$m" "-DPROGRAMA=\"$O/fondo.hex\"" -DMODO=$m $R1 "$CELLS_SIM" $SRC \
    tb/p10/tb_p10_modo.sv > "$O/iverilog_$m.log" 2>&1 || { echo "FAIL modo $m: no compila"; mal=1; continue; }
  vvp -n "$O/sim_$m" > "$O/modo_$m.log" 2>&1
  grep -E "^(RESUMEN|  transaccion)" "$O/modo_$m.log"
done
grep -q "^RESUMEN modo=0 transacciones=[0-9]* distintos=0$" "$O/modo_0.log" || mal=1
exit $mal
