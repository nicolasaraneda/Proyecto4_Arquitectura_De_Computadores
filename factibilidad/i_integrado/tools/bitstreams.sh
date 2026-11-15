#!/usr/bin/env bash
# bitstreams.sh: bitstream de cada configuración integrada, con su sha256, y
# su simulación desde el .asc. No programa la placa.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Para I1 (en sus dos formas de tabla), I2, I3 (en sus dos subconjuntos) e I4
# (base y segmentado de rtl/):
#   1. toma el .asc de la semilla 1 que dejó tools/medir.sh en
#      build/variantes/fact2_i_ETIQUETA (si no está, lo mide);
#   2. lo empaqueta con icepack en build/bitstreams/NOMBRE.bin y anota tamaño
#      y sha256;
#   3. reconstruye un módulo Verilog desde el .asc (tools/chip_vlog.py del
#      repositorio, o scripts/chip_vlog_wb.py de e_warmboot si tiene
#      SB_WARMBOOT) y lo simula por los pines con la maestra de
#      tb/tb_bitstream.sv del repositorio: los bytes que lee la maestra se
#      contabilizan con ref/market.py y se comparan con ref/trader.py, igual
#      que tools/sim_bitstream.sh. En las configuraciones con vigilante,
#      tb/mon_boot_chip.sv comprueba que BOOT no suba.
#
# Programa dentro de cada bitstream: la regla base. En el barrel es sw/trade.s
# con la tabla de arranque (hilo 0) y en los demás sw/trade.hex. El programa
# del fondo de estrategias no existe todavía.
#
# Los .bin quedan en build/bitstreams/ de esta carpeta (ignorada por git: se
# regeneran con este script). nextpnr es determinista para una misma semilla y
# una misma versión de las herramientas, así que el sha256 se reproduce.
#
# Uso: factibilidad/i_integrado/tools/bitstreams.sh   (o make bitstreams)
# Resultado en mediciones/bitstreams.txt. Unos 10 minutos.
# Variables: NTICKS (500) y JOBS (5).
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/bitstreams
JOBS=${JOBS:-5}
NTICKS=${NTICKS:-500}
mkdir -p "$O"

# nombre | etiqueta de tools/medir.sh | SB_WARMBOOT | descripción
LISTA=$(cat <<FIN
i1a|i1a|1|I1 fondo en un chip: barrel, emad, devk, mulstep, vigilante y tabla de 256 x 16 (13 BRAM)
i1b|i1b|1|I1 con la tabla en otras 512 palabras de datos (16 BRAM)
i2|i2|1|I2 barrel mínimo: barrel y vigilante
i3a|i3a|1|I3 conservador: segmentado, emad y vigilante
i3b|i3b|1|I3 con emad, devk y mulstep
i4_base|base|0|I4: Espino base de rtl/
i4_segmentado|segmentado|0|I4: pipeline de 3 etapas de rtl/
FIN
)

# Los .asc de la semilla 1
faltan=""
while IFS='|' read -r n etq wb desc; do
  [ -f "build/variantes/fact2_i_$etq/soc.s1.asc" ] || faltan="$faltan|$etq"
done <<< "$LISTA"
if [ -n "$faltan" ]; then
  $I/tools/medir.sh "^(${faltan#|})\$" > /dev/null 2>&1
fi

$PYTHON ref/trader.py tb/practica.csv --nticks "$NTICKS" --periodo-ns 100000 -o "$O/ref.csv" > /dev/null

# una NOMBRE: empaqueta y simula
una() {
  local n=$1 etq wb desc asc
  IFS='|' read -r _ etq wb desc <<< "$(echo "$LISTA" | grep "^$n|")"
  asc=build/variantes/fact2_i_$etq/soc.s1.asc
  [ -f "$asc" ] || { echo "sin .asc" > "$O/$n.estado"; return 0; }
  cp "$asc" "$O/$n.asc"
  icepack "$O/$n.asc" "$O/$n.bin" || { echo "icepack falla" > "$O/$n.estado"; return 0; }
  if [ "$wb" = 1 ]; then
    $PYTHON $E/scripts/chip_vlog_wb.py "$O/$n.asc" goboard.pcf -o "$O/$n.chip.v" > "$O/$n.chip.log" 2>&1 || { echo "chip_vlog falla" > "$O/$n.estado"; return 0; }
    iverilog -g2012 -s tb_bitstream -s mon_boot_chip -DNTICKS="$NTICKS" -DPERIODO_NS=100000 '-DSERIE="tb/practica.csv"' \
      "-DSALIDA=\"$O/$n.bytes.csv\"" "-DSALIDA_BOOT=\"$O/$n.boot.txt\"" \
      -o "$O/$n.vvp" "$CELLS_SIM" "$O/$n.chip.v" tb/tb_bitstream.sv $I/tb/mon_boot_chip.sv > "$O/$n.iverilog.log" 2>&1 || { echo "no compila" > "$O/$n.estado"; return 0; }
  else
    $PYTHON tools/chip_vlog.py "$O/$n.asc" goboard.pcf -o "$O/$n.chip.v" > "$O/$n.chip.log" 2>&1 || { echo "chip_vlog falla" > "$O/$n.estado"; return 0; }
    iverilog -g2012 -s tb_bitstream -DNTICKS="$NTICKS" -DPERIODO_NS=100000 '-DSERIE="tb/practica.csv"' "-DSALIDA=\"$O/$n.bytes.csv\"" \
      -o "$O/$n.vvp" "$CELLS_SIM" "$O/$n.chip.v" tb/tb_bitstream.sv > "$O/$n.iverilog.log" 2>&1 || { echo "no compila" > "$O/$n.estado"; return 0; }
  fi
  vvp -n "$O/$n.vvp" > "$O/$n.sim.out" 2>&1
  $PYTHON ref/market.py contabilizar "$O/$n.bytes.csv" -o "$O/$n.bitstream.csv" > /dev/null 2>&1
  echo "OK" > "$O/$n.estado"
}
export -f una
export O LISTA NTICKS CELLS_SIM PYTHON E I

inicio=$(date +%s)
echo "$LISTA" | cut -d'|' -f1 | xargs -P "$JOBS" -I{} bash -c 'una {}'
fin=$(date +%s)

{
echo "Bitstreams de las configuraciones integradas, con su sha256 y simulados desde el .asc"
echo "Generado por factibilidad/i_integrado/tools/bitstreams.sh (make bitstreams). No editar a mano."
echo
versiones
echo "nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed 1, goboard.pcf (los .asc son los de tools/medir.sh)."
echo "Los .bin quedan en $O/. Ninguno se grabó en la placa."
echo "Simulación: $NTICKS ticks a 0,1 ms por los pines, con tb/tb_bitstream.sv del repositorio, contra ref/trader.py."
echo
fallas=0
while IFS='|' read -r n etq wb desc; do
  log=build/variantes/fact2_i_$etq/soc.s1.log
  echo "$n: $desc"
  if [ "$(cat "$O/$n.estado" 2>/dev/null)" != OK ]; then echo "   FAIL $(cat "$O/$n.estado" 2>/dev/null)"; fallas=$((fallas + 1)); continue; fi
  echo "   celdas $(grep 'ICESTORM_LC:' "$log" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'), BRAM $(grep 'ICESTORM_RAM:' "$log" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'), SB_WARMBOOT $(grep 'SB_WARMBOOT:' "$log" | head -1 | sed -E 's/.*: *([0-9]+)\/ *([0-9]+).*/\1 de \2/'), $(grep 'Max frequency for clock' "$log" | tail -1 | sed -E 's/.*: ([0-9.]+ MHz) \((PASS|FAIL).*/frecuencia maxima \1 con la semilla 1, \2 a 25 MHz/')"
  echo "   $(stat -c %s "$O/$n.bin") bytes, sha256 $(sha256sum "$O/$n.bin" | cut -d' ' -f1)"
  if ! grep -q "Bits de MISO con X: 0" "$O/$n.sim.out" 2>/dev/null; then
    echo "   FAIL simulacion del .asc: MISO con X o la simulacion no corrio"; fallas=$((fallas + 1))
  elif cmp -s "$O/$n.bitstream.csv" "$O/ref.csv"; then
    echo "   PASS simulado desde el .asc por los pines: $NTICKS ticks idénticos a ref/trader.py, patrimonio $(tail -1 "$O/$n.bitstream.csv" | cut -d, -f6)"
  else
    echo "   FAIL el bitstream no decide igual que la referencia"; fallas=$((fallas + 1))
  fi
  if [ "$wb" = 1 ]; then
    if grep -q "^boot_en_alto=0" "$O/$n.boot.txt" 2>/dev/null; then echo "   PASS BOOT de SB_WARMBOOT nunca sube ($(cat "$O/$n.boot.txt"))"
    else echo "   FAIL BOOT: $(cat "$O/$n.boot.txt" 2>/dev/null)"; fallas=$((fallas + 1)); fi
  fi
done <<< "$LISTA"
echo
echo "Bitstreams versionados en bitstreams/ (referencia, no se regeneran aquí):"
sed 's/^/   /' bitstreams/SHA256SUMS
echo "   Los de I4 de este informe no tienen el mismo hash: son la misma lógica colocada de nuevo (decisión T32)."
echo
echo "Tiempo de las simulaciones: $((fin - inicio)) s con $JOBS procesos."
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, $(echo "$LISTA" | wc -l) bitstreams generados y simulados"
else echo "RESULTADO: FAIL, $fallas problemas"; fi
} | tee "$M/bitstreams.txt"

grep -q "^RESULTADO: PASS" "$M/bitstreams.txt"
