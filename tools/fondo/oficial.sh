#!/usr/bin/env bash
# oficial.sh: el testbench oficial sin modificar con el fondo en un chip
# (criterio 1 de la puerta de simulación).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre tb/tb_proyecto_4.sv tal como está en el repositorio, con Icarus y el
# comando de su encabezado, más las definiciones del barrel con emad y devk.
# El programa se pone en el lugar de sw/trade.hex dentro de una carpeta de
# trabajo, porque el testbench tiene ese nombre fijo. Exige 4/4 y que
# decisiones.csv sea idéntico, byte a byte, al de ref/fondo.py.
#
# Uso: tools/fondo/oficial.sh   (o make fondo-oficial). Demora unos 5 minutos.
# Resultado en docs/mediciones/fondo/HW/oficial.txt (HW es r1 o r2).
set -uo pipefail
source "$(dirname "$0")/comun.sh"

d=$BF/oficial
mkdir -p "$d/sw" "$d/tb"
ensamblar_fondo sw/fondo.s "$d/sw/trade.hex" || { echo "FAIL: no ensambla"; exit 1; }
cp "$TABLA_HEX" "$d/sw/fondo_tabla.hex"
ln -sf "$RAIZ/tb/practica.csv" "$d/tb/practica.csv"
iverilog -g2012 -s tb_proyecto_4 -o "$d/tb_p4" "$CELLS_SIM" $FONDO_SRC tb/tb_proyecto_4.sv || { echo "FAIL: Icarus no compila"; exit 1; }
( cd "$d" && vvp -n tb_p4 > salida.txt )
$PYTHON ref/fondo.py tb/practica.csv --nticks 2000 --periodo-ns 100000 -o "$d/ref.csv" > "$d/ref.log"

{
cabecera "Testbench oficial sin modificar con el fondo en un chip" tools/fondo/oficial.sh "make fondo-oficial"
if git diff --quiet HEAD -- tb/tb_proyecto_4.sv; then
  echo "tb/tb_proyecto_4.sv: sin cambios respecto del repositorio (sha256 $(sha256sum tb/tb_proyecto_4.sv | cut -c1-16)...)"
else
  echo "FAIL: tb/tb_proyecto_4.sv tiene cambios locales"
fi
echo
grep -E 'Peor caso|Patrimonio|rdenes|aprobados' "$d/salida.txt" | sed 's/^/  /'
if grep -q "Testbenchs aprobados: 4/4" "$d/salida.txt"; then echo "PASS: 4/4"; else echo "FAIL: no obtiene 4/4"; fi
if cmp -s "$d/decisiones.csv" "$d/ref.csv"; then
  echo "PASS: decisiones.csv identico byte a byte al de ref/fondo.py ($(wc -l < "$d/decisiones.csv") lineas, sha256 $(sha256sum "$d/decisiones.csv" | cut -c1-16)...)"
else echo "FAIL: decisiones.csv difiere de ref/fondo.py"; fi
} | tee "$MF/oficial.txt"
cierre "$MF/oficial.txt"
