#!/usr/bin/env bash
# oficial.sh: el testbench oficial, sin modificar, contra el SoC con el core barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Compila tb/tb_proyecto_4.sv tal como está en el repositorio contra dos
# diseños y compara sus decisiones.csv byte a byte:
#   barrel   el SoC con el core barrel (-DESPINO_BARREL). El programa es sw/trade.s
#            sin modificar, precedido por la tabla de arranque: max_media
#            corre en el hilo 0 y los otros tres hilos quedan en un lazo vacío.
#   base     el SoC con el Espino base (sin definiciones) y sw/trade.hex.
#
# El testbench oficial lee "sw/trade.hex" y "tb/practica.csv" relativos al
# directorio actual y escribe decisiones.csv ahí mismo. Por eso cada corrida
# se hace dentro de su propia carpeta de build, con esos dos archivos puestos
# en ese lugar.
#
# Uso: tools/barrel/oficial.sh   (o make barrel-oficial)
# Resultado en docs/mediciones/barrel/oficial.txt. Demora unos 2 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/oficial
programas
for v in barrel base; do mkdir -p "$O/$v/sw" "$O/$v/tb"; ln -sf "$RAIZ/tb/practica.csv" "$O/$v/tb/practica.csv"; done
cp "$B/sw/trade_h0.hex" "$O/barrel/sw/trade.hex"
cp sw/trade.hex         "$O/base/sw/trade.hex"

iverilog -g2012 -s tb_proyecto_4 -o "$O/barrel/tb_p4" "$CELLS_SIM" $BARREL_SRC tb/tb_proyecto_4.sv || exit 1
iverilog -g2012 -s tb_proyecto_4 -o "$O/base/tb_p4"   "$CELLS_SIM" $BASE_SRC   tb/tb_proyecto_4.sv || exit 1
( cd "$O/barrel" && vvp -n tb_p4 > salida.txt ) &
( cd "$O/base"   && vvp -n tb_p4 > salida.txt ) &
wait

{
echo "Testbench oficial sin modificar contra el SoC con el core barrel"
echo "Generado por tools/barrel/oficial.sh (make barrel-oficial). No editar a mano."
echo
versiones
if git diff --quiet HEAD -- tb/tb_proyecto_4.sv; then
  echo "tb/tb_proyecto_4.sv: sin cambios respecto del repositorio (sha256 $(sha256sum tb/tb_proyecto_4.sv | cut -c1-16)...)"
else
  echo "ATENCION: tb/tb_proyecto_4.sv tiene cambios locales"
fi
echo
echo "--- Core barrel, max_media en el hilo 0 (sw/trade.s con la tabla de arranque) ---"
grep -v '\$finish' "$O/barrel/salida.txt"
echo
echo "--- Espino base, sw/trade.hex ---"
grep -v '\$finish' "$O/base/salida.txt"
echo
echo "--- Comparacion de decisiones.csv ---"
echo "barrel: $(wc -l < "$O/barrel/decisiones.csv") lineas, sha256 $(sha256sum "$O/barrel/decisiones.csv" | cut -c1-16)..."
echo "base:   $(wc -l < "$O/base/decisiones.csv") lineas, sha256 $(sha256sum "$O/base/decisiones.csv" | cut -c1-16)..."
if cmp -s "$O/barrel/decisiones.csv" "$O/base/decisiones.csv"; then
  echo "PASS decisiones.csv del barrel es identico byte a byte al del Espino base"
else
  echo "FAIL decisiones.csv difiere: $(cmp "$O/barrel/decisiones.csv" "$O/base/decisiones.csv" 2>&1 | head -1)"
fi
if grep -q "Testbenchs aprobados: 4/4" "$O/barrel/salida.txt"; then echo "PASS el barrel obtiene 4/4"
else echo "FAIL el barrel no obtiene 4/4"; fi
} | tee "$M/oficial.txt"

! grep -q "^FAIL" "$M/oficial.txt"
