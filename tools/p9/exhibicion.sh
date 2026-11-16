#!/usr/bin/env bash
# exhibicion.sh: la edición de exhibición con las tres instrucciones de la
# extensión, medida para la tabla de variantes (punto 9 del 16/11).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# R1 y R2 llevan solo emad y devk, las que usa sw/fondo.s (T58 y T63). La
# edición de exhibición lleva además mulstep (-DESPINO_XD): es R2 con la
# extensión completa. Este script mide su costo con el mismo programa:
#   1. celdas, BRAM y frecuencia en 10 semillas (tools/medir_variante.sh), junto
#      con R2 en la misma corrida para que la diferencia sea solo mulstep;
#   2. el testbench oficial sin modificar con esas definiciones: 4/4 y
#      decisiones.csv idéntico al de ref/fondo.py.
#
# Uso: tools/p9/exhibicion.sh   (o make exhibicion). Unos 5 minutos.
set -uo pipefail
cd "$(dirname "$0")/../.."
SALIDA=docs/mediciones/p9/exhibicion.txt
O=build/p9/exhibicion
mkdir -p "$O/sw" "$O/tb" docs/mediciones/p9
R2="-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA -DESPINO_VIGILANTE"
EX="-DESPINO_BARREL -DESPINO_XD -DESPINO_TABLA -DESPINO_VIGILANTE"
python3 tools/pochoasm.py sw/fondo.s -o "$O/sw/trade.hex" > /dev/null || { echo "FAIL: no ensambla"; exit 1; }
cp sw/fondo_tabla.hex "$O/sw/fondo_tabla.hex"
ln -sf "$PWD/tb/practica.csv" "$O/tb/practica.csv"
FUENTES=$(for f in rtl/*.v rtl/espino_core/*.v; do case "$f" in rtl/00_*) ;; *) printf '%s ' "$PWD/$f" ;; esac; done)
CELLS=$(yosys-config --datdir)/ice40/cells_sim.v
{
echo "Edicion de exhibicion: R2 con las tres instrucciones de la extension (emad, devk y mulstep)"
echo "Generado por tools/p9/exhibicion.sh (make exhibicion). No editar a mano."
echo
echo "Herramientas: $(yosys -V); $(nextpnr-ice40 --version 2>&1 | head -n 1)"
echo "Commit de partida: $(git rev-parse --short HEAD). Programa: sw/fondo.s (sha256 $(sha256sum sw/fondo.s | cut -c1-16)...)"
echo
echo "== 1. Recursos y frecuencia, 10 semillas, el mismo programa"
DEFS="$R2" HEX="$O/sw/trade.hex" tools/medir_variante.sh exhib_r2 10
DEFS="$EX" HEX="$O/sw/trade.hex" EXIGIR=1 tools/medir_variante.sh exhib_xd3 10 || echo "FAIL: alguna semilla no cierra a 25 MHz"
echo
echo "== 2. Testbench oficial sin modificar, con $EX"
iverilog -g2012 -s tb_proyecto_4 -o "$O/tb_p4" $EX "$CELLS" $FUENTES "$PWD/tb/tb_proyecto_4.sv" || echo "FAIL: Icarus no compila"
( cd "$O" && vvp -n tb_p4 > salida.txt )
grep -E 'Peor caso|Patrimonio|aprobados' "$O/salida.txt" | sed 's/^/  /'
python3 ref/fondo.py tb/practica.csv --nticks 2000 --periodo-ns 100000 -o "$O/ref.csv" > /dev/null
grep -q "Testbenchs aprobados: 4/4" "$O/salida.txt" && echo "PASS: 4/4" || echo "FAIL: no obtiene 4/4"
cmp -s "$O/decisiones.csv" "$O/ref.csv" && echo "PASS: decisiones.csv identico a ref/fondo.py" || echo "FAIL: decisiones.csv distinto"
echo
echo "Los ciclos por tick son los de R2: el programa no usa mulstep y el core es el mismo (la prueba formal de P2"
echo "muestra que mulstep no cambia las otras instrucciones, make xd-formal)."
} 2>&1 | tee "$SALIDA"
! grep -q '^FAIL' "$SALIDA"
