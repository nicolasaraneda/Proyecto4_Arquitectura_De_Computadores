#!/usr/bin/env bash
# medidor.sh: testbench, controles negativos, timing y bitstream del medidor
# de la maestra SPI (rtl/medidor/medidor_spi.v, docs/checklist_26nov.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# 1. tb/medidor/tb_medidor.sv con el módulo tal cual: todas las medidas iguales
#    a las que corresponden a los tiempos de la maestra del testbench.
# 2. Controles negativos: cinco errores puestos a propósito en una copia del
#    módulo. El testbench tiene que fallar con cada uno.
# 3. Síntesis y nextpnr en 10 semillas a 25 MHz. Celdas, BRAM y frecuencia.
# 4. Bitstream con la semilla 1 en build/medidor/medidor_spi.bin.
#
# Uso: tools/medidor.sh   (o make medidor). Las herramientas de OSS CAD Suite
# tienen que estar en el PATH. Resultado en docs/mediciones/medidor_spi.txt.
set -uo pipefail
RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$RAIZ"
B=build/medidor
SALIDA=docs/mediciones/medidor_spi.txt
mkdir -p "$B"
fallas=0

simular() {   # simular FUENTE ETIQUETA
  iverilog -g2012 -o "$B/sim_$2" "$1" tb/medidor/tb_medidor.sv && vvp -n "$B/sim_$2" > "$B/tb_$2.log"
  grep -q '^PASS: medidor_spi' "$B/tb_$2.log"
}

{
echo "Medidor de la maestra SPI: testbench, controles negativos, timing y bitstream"
echo "Generado por tools/medidor.sh (make medidor). No editar a mano."
echo
echo "Herramientas:"
echo "  $(yosys -V)"
echo "  $(nextpnr-ice40 --version 2>&1 | head -n 1)"
echo "  $(iverilog -V 2>&1 | head -n 1)"
echo "Commit de partida: $(git rev-parse --short HEAD)"
echo

echo "== 1. Testbench"
if simular rtl/medidor/medidor_spi.v sano; then
  grep -E '^(FAIL|RESUMEN)' "$B/tb_sano.log"
  echo "PASS: $(grep -c '^PASS ' "$B/tb_sano.log") comprobaciones, cero fallas"
else
  grep -E '^(FAIL|RESUMEN)' "$B/tb_sano.log"; echo "FAIL: el testbench no pasa con el modulo sano"; fallas=$((fallas + 1))
fi
echo

echo "== 2. Controles negativos"
# nombre|texto original|texto mutado
while IFS='|' read -r nombre orig mut; do
  [ -z "$nombre" ] && continue
  sed "s/$orig/$mut/" rtl/medidor/medidor_spi.v > "$B/mut_$nombre.v"
  if cmp -s rtl/medidor/medidor_spi.v "$B/mut_$nombre.v"; then
    echo "FAIL $nombre: la mutacion no cambio el archivo"; fallas=$((fallas + 1)); continue
  fi
  if simular "$B/mut_$nombre.v" "$nombre"; then
    echo "FAIL $nombre: el testbench no lo detecto"; fallas=$((fallas + 1))
  else
    echo "PASS $nombre: detectado ($(grep -c '^FAIL' "$B/tb_$nombre.log") comprobaciones fallan)"
  fi
done <<'EOF'
flanco_de_bajada|wire sclk_sube = (sclk_s\[2:1\] == 2'b01);|wire sclk_sube = (sclk_s[2:1] == 2'b10);
periodo_sin_escala|t_per\[19:4\];|t_per[15:0];
sin_primera_subida|if (primera) begin|if (1'b0) begin
sin_alarma|if (bits != 4'd8) alarma <= 1'b1;|if (bits == 4'd15) alarma <= 1'b1;
sin_alarma_cs_alto|if (sclk_sube .. !cs_activo) alarma|if (1'b0) alarma
EOF
echo

echo "== 3. Timing en 10 semillas (nextpnr --hx1k --package vq100 --freq 25)"
yosys -q -l "$B/yosys.log" -p "read_verilog rtl/medidor/medidor_spi.v; synth_ice40 -top medidor_spi -json $B/medidor.json"
for s in $(seq 1 10); do
  nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed "$s" --json "$B/medidor.json" --pcf goboard.pcf \
    --asc "$B/medidor_s$s.asc" -l "$B/pnr_s$s.log" -q 2>/dev/null &
done
wait
frecs=""
cierran=0
for s in $(seq 1 10); do
  f=$(grep -o "Max frequency for clock 'i_Clk\$SB_IO_IN_\$glb_clk': [0-9.]* MHz" "$B/pnr_s$s.log" | tail -n 1 | grep -o '[0-9.]* MHz' | cut -d' ' -f1)
  [ -z "$f" ] && f=$(grep -o "Max frequency for clock '[^']*': [0-9.]* MHz" "$B/pnr_s$s.log" | tail -n 1 | grep -o '[0-9.]* MHz' | cut -d' ' -f1)
  frecs="$frecs $f"
  awk -v f="$f" 'BEGIN { exit !(f >= 25) }' && cierran=$((cierran + 1))
done
celdas=$(grep -o 'ICESTORM_LC: *[0-9]*/ *[0-9]*' "$B/pnr_s1.log" | tail -n 1 | tr -s ' ')
bram=$(grep -o 'ICESTORM_RAM: *[0-9]*/ *[0-9]*' "$B/pnr_s1.log" | tail -n 1 | tr -s ' ')
echo "Celdas: $celdas. BRAM: $bram"
echo "Frecuencia maxima por semilla (MHz):$frecs"
echo "$frecs" | tr ' ' '\n' | grep . | sort -n | awk '{v[NR]=$1} END {printf "Minima %.2f MHz, mediana %.2f MHz, maxima %.2f MHz\n", v[1], (v[int((NR+1)/2)]+v[int(NR/2)+1])/2, v[NR]}'
if [ "$cierran" -eq 10 ]; then echo "PASS: 10 de 10 semillas cierran a 25 MHz"; else echo "FAIL: $cierran de 10 semillas cierran"; fallas=$((fallas + 1)); fi
echo

echo "== 4. Bitstream (semilla 1)"
icepack "$B/medidor_s1.asc" "$B/medidor_spi.bin"
echo "build/medidor/medidor_spi.bin: $(stat -c %s "$B/medidor_spi.bin") bytes, sha256 $(sha256sum "$B/medidor_spi.bin" | cut -d' ' -f1)"
echo

echo "== 5. Bitstream ruteado simulado por los pines (el mismo testbench, construido con REBOTE = 8)"
yosys -q -p "read_verilog rtl/medidor/medidor_spi.v; chparam -set REBOTE 8 medidor_spi; synth_ice40 -top medidor_spi -json $B/medidor_r8.json"
nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed 1 --json "$B/medidor_r8.json" --pcf goboard.pcf \
  --asc "$B/medidor_r8.asc" -l "$B/pnr_r8.log" -q 2>/dev/null
python3 tools/chip_vlog.py "$B/medidor_r8.asc" goboard.pcf -o "$B/chip.v"
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
if iverilog -g2012 -DCHIP -o "$B/sim_chip" "$CELLS_SIM" "$B/chip.v" tb/medidor/tb_medidor.sv && vvp -n "$B/sim_chip" > "$B/tb_chip.log" \
   && grep -q '^PASS: medidor_spi' "$B/tb_chip.log"; then
  echo "PASS: $(grep -c '^PASS ' "$B/tb_chip.log") comprobaciones por los pines del bitstream, cero fallas"
else
  grep -E '^(FAIL|RESUMEN)' "$B/tb_chip.log"; echo "FAIL: el bitstream no mide lo esperado"; fallas=$((fallas + 1))
fi
echo
if [ "$fallas" -eq 0 ]; then echo "PASS: medidor listo"; else echo "FAIL: $fallas pasos fallaron"; fi
} | tee "$SALIDA"
grep -q '^PASS: medidor listo' "$SALIDA"
