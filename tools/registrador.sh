#!/usr/bin/env bash
# registrador.sh: testbench, controles negativos, timing, bitstream y simulación del
# bitstream ruteado del registrador de la maestra (rtl/registrador/registrador.v,
# docs/registrador.md), más la prueba sin placa de tools/registrador.py.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# 1. tb/registrador/tb_registrador.sv con el módulo tal cual: ningún precio perdido a
#    0,1 ms, 1 ms, 10 ms y 60 us; el control a 30 us tiene que perder y delatarlo.
# 2. Controles negativos: errores puestos a propósito en una copia del módulo.
# 3. Síntesis y nextpnr en 10 semillas a 25 MHz. Celdas, BRAM y frecuencia.
# 4. Bitstream con la semilla 1 en build/registrador/registrador.bin.
# 5. El bitstream ruteado (construido con REBOTE = 8) simulado por los pines con el
#    mismo testbench, en su versión corta.
# 6. tools/registrador.py --prueba: los bytes del paso 1 y un pseudoterminal a 1 Mbaud.
#
# Uso: tools/registrador.sh   (o make registrador). Las herramientas de OSS CAD Suite
# tienen que estar en el PATH. Resultado en docs/mediciones/registrador.txt.
set -uo pipefail
RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$RAIZ"
B=build/registrador
SALIDA=docs/mediciones/registrador.txt
FUENTE=rtl/registrador/registrador.v
mkdir -p "$B"
fallas=0
simular() {   # simular FUENTE ETIQUETA [plusargs]
  iverilog -g2012 -o "$B/sim_$2" "$1" tb/registrador/tb_registrador.sv && vvp -n "$B/sim_$2" ${3:-} > "$B/tb_$2.log"
  grep -q '^PASS: registrador' "$B/tb_$2.log"
}
{
echo "Registrador de la maestra SPI: testbench, controles negativos, timing, bitstream y herramienta"
echo "Generado por tools/registrador.sh (make registrador). No editar a mano."
echo
echo "Herramientas:"
echo "  $(yosys -V)"
echo "  $(nextpnr-ice40 --version 2>&1 | head -n 1)"
echo "  $(iverilog -V 2>&1 | head -n 1)"
echo "Commit de partida: $(git rev-parse --short HEAD)"
echo
echo "== 1. Testbench"
if simular "$FUENTE" sano "+BYTES=$B/bytes_r3.bin"; then
  grep -E '^(PASS|FAIL|RESUMEN)' "$B/tb_sano.log" | grep -v '^PASS: registrador'
  echo "PASS: $(grep -c '^PASS ' "$B/tb_sano.log") comprobaciones, cero fallas"
else
  grep -E '^(FAIL|RESUMEN)' "$B/tb_sano.log"; echo "FAIL: el testbench no pasa con el modulo sano"; fallas=$((fallas + 1))
fi
echo

echo "== 2. Controles negativos"
while IFS='|' read -r nombre orig mut; do
  [ -z "$nombre" ] && continue
  sed "s/$orig/$mut/" "$FUENTE" > "$B/mut_$nombre.v"
  if cmp -s "$FUENTE" "$B/mut_$nombre.v"; then
    echo "FAIL $nombre: la mutacion no cambio el archivo"; fallas=$((fallas + 1)); continue
  fi
  if simular "$B/mut_$nombre.v" "$nombre"; then
    echo "FAIL $nombre: el testbench no lo detecto"; fallas=$((fallas + 1))
  else
    echo "PASS $nombre: detectado ($(grep -c '^FAIL' "$B/tb_$nombre.log") comprobaciones fallan)"
  fi
done <<'MUT'
flanco_de_bajada|wire sclk_sube = sclk_s\[1\] \& ~sclk_s\[2\];|wire sclk_sube = ~sclk_s[1] \& sclk_s[2];
primero_el_bit_menor|rx   <= {rx\[6:0\], mosi_s\[1\]};|rx   <= {mosi_s[1], rx[7:1]};
sin_marca_de_error|if (bits != 4'd8) alarma_err_o <= 1'b1;|if (bits == 4'd15) alarma_err_o <= 1'b1;
secuencia_no_avanza_si_se_pierde|      sec <= sec + 7'd1;   |      if (!llena) sec <= sec + 7'd1;
baudios_mal|div == CICLOS_BIT - 1|div == CICLOS_BIT + 2
periodo_sin_escala|hubo ? t_per\[17:7\]|hubo ? t_per[16:6]
cola_llena_en_32_bits|wire llena = ocupados\[PROF_LOG2\];|wire llena = (esc - lec) == (1 << PROF_LOG2);
MUT
echo

echo "== 3. Timing en 10 semillas (nextpnr --hx1k --package vq100 --freq 25)"
yosys -q -l "$B/yosys.log" -p "read_verilog $FUENTE; synth_ice40 -top registrador_top -json $B/registrador.json"
for s in $(seq 1 10); do
  nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed "$s" --json "$B/registrador.json" --pcf goboard.pcf \
    --asc "$B/registrador_s$s.asc" -l "$B/pnr_s$s.log" -q 2>/dev/null &
done
wait
frecs=""
cierran=0
for s in $(seq 1 10); do
  f=$(grep -o "Max frequency for clock '[^']*': [0-9.]* MHz" "$B/pnr_s$s.log" | tail -n 1 | grep -o '[0-9.]* MHz' | cut -d' ' -f1)
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
icepack "$B/registrador_s1.asc" "$B/registrador.bin"
echo "build/registrador/registrador.bin: $(stat -c %s "$B/registrador.bin") bytes, sha256 $(sha256sum "$B/registrador.bin" | cut -d' ' -f1)"
echo

echo "== 5. Bitstream ruteado simulado por los pines (testbench corto, construido con REBOTE = 8)"
yosys -q -p "read_verilog $FUENTE; chparam -set REBOTE 8 registrador_top; synth_ice40 -top registrador_top -json $B/registrador_r8.json"
nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed 1 --json "$B/registrador_r8.json" --pcf goboard.pcf \
  --asc "$B/registrador_r8.asc" -l "$B/pnr_r8.log" -q 2>/dev/null
python3 tools/chip_vlog.py "$B/registrador_r8.asc" goboard.pcf -o "$B/chip.v"
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
if iverilog -g2012 -DCHIP -o "$B/sim_chip" "$CELLS_SIM" "$B/chip.v" tb/registrador/tb_registrador.sv && \
   vvp -n "$B/sim_chip" +RAPIDO > "$B/tb_chip.log" && grep -q '^PASS: registrador' "$B/tb_chip.log"; then
  echo "PASS: $(grep -c '^PASS ' "$B/tb_chip.log") comprobaciones por los pines del bitstream, cero fallas"
else
  grep -E '^(FAIL|RESUMEN)' "$B/tb_chip.log"; echo "FAIL: el bitstream no registra lo esperado"; fallas=$((fallas + 1))
fi
echo

echo "== 6. Herramienta (tools/registrador.py --prueba)"
if python3 tools/registrador.py --prueba > "$B/prueba.log" 2>&1; then cat "$B/prueba.log"
else cat "$B/prueba.log"; fallas=$((fallas + 1)); fi
echo
if [ "$fallas" -eq 0 ]; then echo "PASS: registrador listo"; else echo "FAIL: $fallas pasos fallaron"; fi
} | tee "$SALIDA"
grep -q '^PASS: registrador listo' "$SALIDA"
