#!/usr/bin/env bash
# netlist.sh: simula la netlist sintetizada del SoC barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Sintetiza el SoC con un programa de prueba dentro de las BRAM, escribe la
# netlist en Verilog y la simula con los modelos de las primitivas del iCE40.
# Dos programas que se revisan a sí mismos:
#   cooperacion     los cuatro hilos y la memoria compartida. LEDs 1111 y
#                   display "60".
#   hazard_test     el programa de riesgos del Proyecto 3 en el hilo 2. LEDs
#                   1111 y display "38" (las 56 comprobaciones).
# Se repite con la memoria sin emulación de lectura durante escritura (el
# recorte de tools/barrel/medir_recursos.sh), para comprobar que esa netlist también
# funciona en simulación. Lo que esta prueba no cubre de ese recorte se
# explica en docs/espino_barrel.md.
#
# Uso: tools/barrel/netlist.sh   (o make barrel-netlist)
# Resultado en docs/mediciones/barrel/netlist.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/netlist
mkdir -p "$O"
programas
con_tabla 2 sw/hazard_test.s "$O/hazard_test_h2.hex"
sed -E 's|^( *)reg \[31:0\] (mem(_f)?) \[0:NumWords-1\];|\1(* no_rw_check *) reg [31:0] \2 [0:NumWords-1];|' \
  rtl/pochoco_ram.v > "$O/pochoco_ram_directa.v"
[ "$(diff rtl/pochoco_ram.v "$O/pochoco_ram_directa.v" | grep -c '^>')" = 2 ] || { echo "FAIL: la copia de pochoco_ram.v no quedo como se esperaba"; exit 1; }
# Las mismas fuentes del barrel, con la copia en el lugar de rtl/pochoco_ram.v
SRC_DIRECTA="-DESPINO_BARREL $O/pochoco_ram_directa.v $(echo $BASE_SRC | tr ' ' '\n' | grep -vx rtl/pochoco_ram.v | tr '\n' ' ')"

# Segmentos en lógica positiva: {G, F, E, D, C, B, A}
S0="7'b0111111"; S3="7'b1001111"; S6="7'b1111101"; S8="7'b1111111"

# caso NOMBRE "FUENTES" HEX LEDS SEG1 SEG2
caso() {
  local n=$1 src=$2 hex=$3 leds=$4 s1=$5 s2=$6
  yosys -q -l "$O/$n.log" -p "read_verilog $src; chparam -set MemFile \"$hex\" pochoco_soc; \
    synth_ice40 -top pochoco_soc; write_verilog -noattr $O/$n.v" || { echo "FAIL $n: no sintetiza"; return; }
  iverilog -g2012 -s tb_netlist -DLEDS="$leds" "-DSEG1=$s1" "-DSEG2=$s2" -o "$O/$n.vvp" "$CELLS_SIM" "$O/$n.v" $TB/tb_netlist.sv \
    && vvp -n "$O/$n.vvp" > "$O/$n.out"
  if grep -q "^RESULTADO: PASS" "$O/$n.out"; then echo "PASS $n: $(grep '^LEDs' "$O/$n.out")"
  else echo "FAIL $n: $(grep -E '^LEDs|^FAIL' "$O/$n.out" | tr '\n' ' ')"; fi
}

{
echo "Simulacion de la netlist sintetizada del SoC barrel (Yosys synth_ice40, modelos de cells_sim.v)"
echo "Generado por tools/barrel/netlist.sh (make barrel-netlist). No editar a mano."
echo
versiones
echo
caso cooperacion              "$BARREL_SRC"  "$B/sw/cooperacion.hex"   15 "$S6" "$S0" &
caso hazard_test_hilo2        "$BARREL_SRC"  "$O/hazard_test_h2.hex"   15 "$S3" "$S8" &
caso cooperacion_ramdirecta   "$SRC_DIRECTA" "$B/sw/cooperacion.hex"   15 "$S6" "$S0" &
caso hazard_test_h2_ramdirecta "$SRC_DIRECTA" "$O/hazard_test_h2.hex"  15 "$S3" "$S8" &
wait
} | tee "$M/netlist.txt"

! grep -q "^FAIL" "$M/netlist.txt"
