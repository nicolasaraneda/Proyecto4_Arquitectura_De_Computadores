#!/usr/bin/env bash
# plataforma.sh: hechos de la plataforma que se pueden comprobar sin la placa.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Reúne en un archivo: versiones de las herramientas, tamaño y cabecera de los
# bitstreams de bitstreams/, ayuda de icemulti y su límite de imágenes, que
# nextpnr ubica la primitiva SB_WARMBOOT en la HX1K VQ100 (y que rechaza una
# segunda), las opciones de iceprog que importan (leídas del binario, sin
# ejecutarlo) y la cuenta de ticks que se pierden con los tiempos de
# configuración de la hoja de datos.
#
# Uso, desde la raíz del repositorio (después de construir_demo.sh):
#   factibilidad/e_warmboot/scripts/plataforma.sh
# Resultado en mediciones/plataforma.txt.
set -euo pipefail

E=factibilidad/e_warmboot
D=$E/build/plataforma
mkdir -p "$D" "$E/mediciones"
LIBEXEC=$(dirname "$(readlink -f "$(command -v yosys)")")/../libexec

{
  echo "Hechos de la plataforma comprobados sin la placa"
  echo "Comando: factibilidad/e_warmboot/scripts/plataforma.sh"
  echo
  echo "=== Herramientas ==="
  echo "$(yosys -V)"
  echo "$(nextpnr-ice40 --version 2>&1 | head -1)"
  echo "icepack, icemulti, iceprog: los de OSS CAD Suite ($(dirname "$(command -v icepack)"))"
  echo
  echo "=== Bitstreams de la HX1K ==="
  for f in bitstreams/competencia_v1.bin bitstreams/segmentado_v1.bin $E/build/demo/img0.bin $E/build/demo/img1.bin; do
    printf "%-46s %6d bytes (%d bits)\n" "$f" "$(stat -c %s "$f")" "$(( $(stat -c %s "$f") * 8 ))"
  done
  echo "Cabecera, según icepack -u -v:"
  for f in bitstreams/competencia_v1.bin bitstreams/segmentado_v1.bin $E/build/demo/img0.bin; do
    printf "  %-44s %s\n" "$f" "$(icepack -u -v "$f" "$D/tmp.asc" 2>&1 | grep -i "freqrange\|warmboot\|CRC" | paste -sd' ')"
  done
  echo "Primeros 16 bytes de bitstreams/competencia_v1.bin: $(xxd -p -l 16 bitstreams/competencia_v1.bin)"
  echo "  7eaa997e sincronía, 51 00 oscilador de configuración en frecuencia baja, 01 05 reinicio del CRC,"
  echo "  92 00 20 warm boot habilitado y flash a bajo consumo al terminar"
  echo
  echo "=== icemulti ==="
  icemulti -h 2>&1 | sed '1,2d; s/^/  /' || true
  echo "Con 5 imágenes: $(icemulti -o "$D/cinco.bin" bitstreams/competencia_v1.bin bitstreams/competencia_v1.bin bitstreams/competencia_v1.bin bitstreams/competencia_v1.bin bitstreams/competencia_v1.bin 2>&1 | tail -1 || true)"
  echo
  echo "=== SB_WARMBOOT en la HX1K VQ100 con nextpnr ==="
  echo "Imagen 0 de la prueba de placa (build/demo/nextpnr_img0.log):"
  grep -E "(ICESTORM_LC|ICESTORM_RAM|SB_IO|SB_GB|SB_WARMBOOT|ICESTORM_PLL): +[0-9]+\/" $E/build/demo/nextpnr_img0.log | sed 's/^Info: */  /' | tr -s '\t' ' '
  echo "Dos primitivas en el mismo diseño:"
  cat > "$D/dos.v" <<'FIN'
module dos (input i_Clk, input [3:0] i_Switch, output [3:0] o_LED);
  reg [1:0] q = 0;
  always @(posedge i_Clk) q <= i_Switch[1:0];
  SB_WARMBOOT u_a (.BOOT(q[0]), .S1(1'b0), .S0(1'b1));
  SB_WARMBOOT u_b (.BOOT(q[1]), .S1(1'b1), .S0(1'b0));
  assign o_LED = {2'b00, q};
endmodule
FIN
  yosys -q -p "read_verilog $D/dos.v; synth_ice40 -top dos -json $D/dos.json" > "$D/dos_yosys.log" 2>&1
  nextpnr-ice40 --hx1k --package vq100 --json "$D/dos.json" --pcf goboard.pcf --asc "$D/dos.asc" > "$D/dos_pnr.log" 2>&1 || true
  echo "  $(grep -m1 "^ERROR" "$D/dos_pnr.log" || echo "nextpnr no dio error")"
  echo
  echo "=== iceprog: opciones que importan (texto de ayuda leído del binario, sin ejecutarlo) ==="
  strings "$LIBEXEC/iceprog" | grep -E "^  (\[default\] +(erase|write)|-b |-n |-c |-t |-o |-e |-R |-r |-i )" | sed 's/^/  /'
  echo
  echo "=== Ticks que se pierden, con los tiempos de la hoja de datos (estimado, no medido) ==="
  echo "tCONFIG típico de la iCE40HX1K (DS1040, tabla SPI Master or NVCM Configuration Time):"
  echo "53 ms con el oscilador en frecuencia baja, 25 ms en media y 13 ms en alta."
  echo "Cuenta: N + 1 = 5 precios para que el vigilante dispare. BOOT sube 13,6 us después del"
  echo "comienzo del quinto (al terminar su transacción). Desde ahí pasan tCONFIG y el reset de"
  echo "4095 ciclos (0,164 ms), y el respaldo responde al primer precio que recibe completo."
  echo "La misma cuenta sale de la simulación del relevo (mediciones/relevo.txt)."
  python3 - <<'FIN'
import math
print("  %-8s %-10s %-22s %-28s %-24s" % ("T", "tCONFIG", "ticks sin el chip", "ticks sin decisión nueva", "de una ronda de 2000"))
for T, nombre in ((10.0, "10 ms"), (1.0, "1 ms"), (0.1, "0,1 ms")):
    for tc in (53.0, 25.0, 13.0):
        fuera = (tc + 0.164 + 0.0136) / T
        total = 5 + math.floor(fuera)
        print("  %-8s %-10s %-22s %-28s %-24s" % (nombre, "%d ms" % tc, "%.1f" % fuera, "%d" % total, "%.1f %%" % (100.0 * total / 2000)))
FIN
  echo "Una ronda de 2000 ticks dura 20 s a 10 ms, 2 s a 1 ms y 0,2 s a 0,1 ms."
  echo
  echo "Lectura del bitstream a la frecuencia típica del oscilador (DS1040, fMCLK): $(( 32220 * 8 )) bits"
  python3 -c "
for n, f in (('baja', 7.5), ('media', 24.0), ('alta', 40.0)):
    print('  %-6s %4.1f MHz: %5.1f ms' % (n, f, 32220 * 8 / f / 1000))"
  echo "La diferencia con tCONFIG es lo que la FPGA demora en borrar su memoria de configuración,"
  echo "despertar la flash y arrancar. No está desglosado en la hoja de datos."
} | tee $E/mediciones/plataforma.txt
