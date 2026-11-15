#!/usr/bin/env bash
# oficial.sh: el testbench oficial, sin modificar, con el fondo de cuatro hilos.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Compila tb/tb_proyecto_4.sv tal como está en el repositorio contra el SoC
# con el core barrel (factibilidad/a_barrel/rtl, sin modificar) y el programa
# sw/fondo.s, con Icarus Verilog, que es el simulador del encabezado del
# testbench. Compara su decisiones.csv byte a byte con el de la referencia en
# C (fondo_min de factibilidad/retorno/r4b_fondo/fondo.c).
#
# El testbench oficial lee "sw/trade.hex" y "tb/practica.csv" relativos al
# directorio actual y escribe decisiones.csv ahí mismo. Por eso la corrida se
# hace dentro de su propia carpeta de build, con esos dos archivos puestos en
# ese lugar.
#
# Uso: factibilidad/b_fondo_hilos/tools/oficial.sh   (o make oficial)
# Resultado en mediciones/oficial.txt. Demora unos 4 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/oficial
mkdir -p "$O/sw" "$O/tb"
armar base || exit 1
cp "$B/prog/base/fondo.hex" "$O/sw/trade.hex"
ln -sf "$RAIZ/tb/practica.csv" "$O/tb/practica.csv"

iverilog -g2012 -s tb_proyecto_4 -o "$O/tb_p4" "$CELLS_SIM" $BARREL_SRC tb/tb_proyecto_4.sv || exit 1
T0=$(date +%s)
( cd "$O" && vvp -n tb_p4 > salida.txt )
T1=$(date +%s)
K=$(perdidos 100000)
referencia fondo_min tb/practica.csv 2000 "$K" "$O/ref.csv" > "$O/ref.txt"

{
echo "Testbench oficial sin modificar con el fondo de cuatro hilos (sw/fondo.s) en el Espino barrel"
echo "Generado por factibilidad/b_fondo_hilos/tools/oficial.sh (make oficial). No editar a mano."
echo
versiones
if git diff --quiet HEAD -- tb/tb_proyecto_4.sv; then
  echo "tb/tb_proyecto_4.sv: sin cambios respecto del repositorio (sha256 $(sha256sum tb/tb_proyecto_4.sv | cut -c1-16)...)"
else
  echo "ATENCION: tb/tb_proyecto_4.sv tiene cambios locales"
fi
echo "Simulador: Icarus Verilog, $((T1 - T0)) s de simulacion"
echo
echo "--- Salida del testbench oficial ---"
grep -v '\$finish' "$O/salida.txt"
echo
echo "--- Referencia en C: fondo_min, $K precios iniciales sin ver (llegan durante el reset de encendido) ---"
cat "$O/ref.txt"
echo
echo "--- Comparacion de decisiones.csv ---"
echo "barrel:     $(wc -l < "$O/decisiones.csv") lineas, sha256 $(sha256sum "$O/decisiones.csv" | cut -c1-16)..."
echo "referencia: $(wc -l < "$O/ref.csv") lineas, sha256 $(sha256sum "$O/ref.csv" | cut -c1-16)..."
if cmp -s "$O/decisiones.csv" "$O/ref.csv"; then
  echo "PASS decisiones.csv del testbench oficial es identico byte a byte al de la referencia en C (2000 ticks)"
else
  echo "FAIL decisiones.csv difiere: $(cmp "$O/decisiones.csv" "$O/ref.csv" 2>&1 | head -1)"
  echo "  primera fila distinta: $(diff "$O/decisiones.csv" "$O/ref.csv" | sed -n 2,4p | tr '\n' ' ')"
fi
echo "Bytes distintos en el flujo: $(tail -n +2 "$O/decisiones.csv" | cut -d, -f3 | sort | uniq -c | awk '{printf "%s x %d  ", $2, $1}')"
if grep -q "Testbenchs aprobados: 4/4" "$O/salida.txt"; then echo "PASS el testbench oficial entrega 4/4"
else echo "FAIL el testbench oficial no entrega 4/4"; fi
} | tee "$M/oficial.txt"

! grep -q "^FAIL" "$M/oficial.txt"
