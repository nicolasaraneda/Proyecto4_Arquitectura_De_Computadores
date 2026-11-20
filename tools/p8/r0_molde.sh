#!/usr/bin/env bash
# r0_molde.sh: molde de R0 para cambiar su programa con icebram, sin sintetizar.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# R1 y R2 ya tienen sus moldes (bitstreams/moldes/, decisión T70). R0 no: su
# programa solo se podía cambiar sintetizando de nuevo, y una síntesis desde
# otro commit da otra ubicación (T62). Este script hace el molde de R0 desde
# las fuentes del commit de R0, igual que tools/reproducir_r0.sh:
#
#   1. Extrae las fuentes del commit de R0 a build/r0_molde/.
#   2. Construye ahí el bitstream con la memoria llena de un patrón al azar
#      (icebram -g) en lugar de sw/trade.hex.
#   3. Pone el programa de R0 de ese commit con icebram sobre el molde y exige que el
#      resultado sea, byte por byte, bitstreams/r0_base_max_media.bin. Exige además que
#      sw/trade.hex sobre el molde dé el R0 vigente, $R0_VIGENTE (desde el 19/11, T140,
#      bitstreams/r0_banda40.bin; del 17 al 19/11 fue r0_cotas.bin, la banda 60). Si lo es, el
#      molde sirve: cualquier otro programa puesto así queda en el mismo
#      hardware, con la misma ubicación.
#   4. Guarda el molde comprimido y su patrón en bitstreams/moldes/.
#
# Uso: tools/p8/r0_molde.sh   (o make r0-molde). Unos 2 minutos. Las
# herramientas de OSS CAD Suite tienen que estar en el PATH.
set -euo pipefail
cd "$(dirname "$0")/../.."

COMMIT_R0=1d4a82f440e5aff9761cfea75c1623243ea53561
D=build/r0_molde
SALIDA=docs/mediciones/p8/r0_molde.txt
R0_VIGENTE=${R0_VIGENTE:-bitstreams/r0_banda40.bin}   # el R0 que sale de sw/trade.hex
mkdir -p docs/mediciones/p8

git cat-file -e "$COMMIT_R0^{commit}" 2>/dev/null || { echo "FAIL: el commit de R0 no esta en este clon"; exit 1; }
rm -rf "$D"; mkdir -p "$D"
git archive "$COMMIT_R0" | tar -x -C "$D"
icebram -g -s 7 32 512 > "$D/molde_prog.hex"
( cd "$D" && make bin HEX=molde_prog.hex > construir.log 2>&1 ) || { echo "FAIL: no se pudo construir el molde"; exit 1; }

a=$(date +%s.%N)
icebram "$D/molde_prog.hex" "$D/sw/trade.hex" < "$D/build/pochoco_soc.asc" > "$D/r0_icebram.asc"
icepack "$D/r0_icebram.asc" "$D/r0_icebram.bin"
b=$(date +%s.%N)
# El programa vigente de R0 sobre el mismo molde: tiene que dar $R0_VIGENTE
icebram "$D/molde_prog.hex" sw/trade.hex < "$D/build/pochoco_soc.asc" > "$D/r0_vigente.asc"
icepack "$D/r0_vigente.asc" "$D/r0_vigente.bin"

{
echo "Molde de R0 para icebram"
echo "Generado por tools/p8/r0_molde.sh (make r0-molde). No editar a mano."
echo
echo "Herramientas: $(yosys -V); $(nextpnr-ice40 --version 2>&1 | head -n 1)"
echo "Fuentes: commit ${COMMIT_R0:0:7} (el de R0). Patron: icebram -g -s 7 32 512"
echo "Molde: $(grep -E 'ICESTORM_LC' "$D/build/nextpnr.log" | tail -n 1 | sed 's/^Info: *//')"
echo "icebram con el programa de R0 sobre el molde e icepack: $(echo "$a $b" | awk '{printf "%.2f", $2 - $1}') s"
esperado=$(sha256sum bitstreams/r0_base_max_media.bin | cut -d' ' -f1)
obtenido=$(sha256sum "$D/r0_icebram.bin" | cut -d' ' -f1)
echo "  sha256 de bitstreams/r0_base_max_media.bin  $esperado"
echo "  sha256 del molde con el programa de R0       $obtenido"
if [ "$esperado" = "$obtenido" ]; then
  mkdir -p bitstreams/moldes
  gzip -9 -n -c "$D/build/pochoco_soc.asc" > bitstreams/moldes/r0_molde.asc.gz
  cp "$D/molde_prog.hex" bitstreams/moldes/molde_prog_r0.hex
  echo "PASS: el molde con el programa de R0 da R0 byte por byte. Guardado en bitstreams/moldes/r0_molde.asc.gz"
else
  echo "FAIL: el molde con el programa de R0 no da R0"
fi
esperado_c=$(sha256sum "$R0_VIGENTE" | cut -d' ' -f1)
obtenido_c=$(sha256sum "$D/r0_vigente.bin" | cut -d' ' -f1)
echo "  sha256 de $R0_VIGENTE  $esperado_c"
echo "  sha256 del molde con sw/trade.hex      $obtenido_c"
if [ "$esperado_c" = "$obtenido_c" ]; then echo "PASS: el molde con sw/trade.hex da $R0_VIGENTE byte por byte"
else echo "FAIL: el molde con sw/trade.hex no da $R0_VIGENTE"; fi
} | tee "$SALIDA"
! grep -q '^FAIL' "$SALIDA" && grep -q '^PASS' "$SALIDA"
