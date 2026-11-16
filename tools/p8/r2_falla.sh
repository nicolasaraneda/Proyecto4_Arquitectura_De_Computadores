#!/usr/bin/env bash
# r2_falla.sh: R2 con la falla inyectada, para ver el relevo con la maestra real
# el 26/11 (docs/checklist_26nov.md, sección 5).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# La autoprueba de P6 (relevo_r2_multi.bin) prueba el relevo con la maestra
# interna. Para verlo con la maestra del curso hace falta R2 tal cual, con el SPI
# externo, y el supervisor colgado. Este script arma esa imagen sin sintetizar:
#   1. el programa con el supervisor colgado en el tick 100
#      (tools/fondo/variante.py cuelgue_sup:100), el mismo de make fondo-bitstreams;
#   2. icebram del programa y de la tabla sobre el molde de R2;
#   3. si existe la salida de make fondo-bitstreams, exige que el .asc sea idéntico
#      byte por byte al que P5 simuló por los pines (BOOT en la transacción 105,
#      docs/mediciones/fondo/bitstreams.txt, paso 5);
#   4. icemulti con R0 de respaldo, como r2_multi.bin.
#
# Uso: tools/p8/r2_falla.sh   (o make r2-falla). Segundos.
set -euo pipefail
cd "$(dirname "$0")/../.."
O=build/p8/r2_falla
rm -rf "$O"; mkdir -p "$O"
python3 tools/fondo/variante.py cuelgue_sup:100 -o "$O/colgado.s"
python3 tools/pochoasm.py "$O/colgado.s" -o "$O/colgado_asm.hex" > /dev/null
python3 - "$O/colgado_asm.hex" "$O/colgado.hex" <<'PY'
import sys
p = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith(("//", "@"))]
open(sys.argv[2], "w", newline="\n").write("\n".join(p + ["00000000"] * (512 - len(p))) + "\n")
PY
gunzip -c bitstreams/moldes/r2_molde.asc.gz > "$O/r2_molde.asc"
icebram bitstreams/moldes/molde_prog.hex "$O/colgado.hex" < "$O/r2_molde.asc" \
  | icebram bitstreams/moldes/molde_tabla.hex sw/fondo_tabla.hex > "$O/r2_colgado.asc"
P5=build/fondo/bitstreams/r2_colgado.asc
if [ -f "$P5" ]; then
  cmp -s "$P5" "$O/r2_colgado.asc" && echo "PASS: el .asc es el que make fondo-bitstreams simulo por los pines" \
    || { echo "FAIL: el .asc no es el simulado en make fondo-bitstreams"; exit 1; }
else
  echo "Aviso: no esta $P5 (make fondo-bitstreams); no se comparo con el .asc simulado"
fi
icepack "$O/r2_colgado.asc" "$O/r2_colgado.bin"
icemulti -p0 -o bitstreams/r2_falla_multi.bin "$O/r2_colgado.bin" bitstreams/r0_base_max_media.bin
python3 tools/ver_multi.py bitstreams/r2_falla_multi.bin "$O/r2_colgado.bin" bitstreams/r0_base_max_media.bin
sha256sum bitstreams/r2_falla_multi.bin
