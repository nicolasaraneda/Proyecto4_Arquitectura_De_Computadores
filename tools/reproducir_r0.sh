#!/usr/bin/env bash
# reproducir_r0.sh: vuelve a construir el bitstream R0 y comprueba que es,
# bit a bit, el que está guardado en bitstreams/.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# R0 (bitstreams/r0_base_max_media.bin) se construyó en el commit de abajo.
# Desde entonces el repositorio tiene más archivos en rtl/ (el barrel y la
# extensión de la ISA). No cambian la lógica del Espino base, pero sí los
# nombres internos que Yosys genera, y con ellos la ubicación que elige
# nextpnr: "make bin" en un commit posterior entrega un bitstream con la misma
# lógica y otro hash. Para obtener el mismo archivo hay que sintetizar las
# fuentes de ese commit, y eso es lo que hace este script, desde cualquier
# commit posterior:
#
#   1. Extrae las fuentes del commit de R0 a build/r0/ con "git archive".
#   2. Corre ahí "make bin" (yosys, nextpnr con la semilla por defecto, icepack).
#   3. Compara el sha256 del resultado con el de bitstreams/SHA256SUMS y con el
#      archivo guardado.
#   4. Lista, como información, las líneas de código que cambiaron desde ese
#      commit en las fuentes del Espino base sin ninguna variante definida.
#      Que el base de hoy decide igual lo comprueban make equiv, make
#      formal-base y make sim-bitstream, no este script.
#
# Necesita el historial de git (en la integración continua, fetch-depth: 0) y
# la misma versión de OSS CAD Suite con que se construyó (2026-09-06).
#
# Uso: tools/reproducir_r0.sh   (o make r0-reproducir). Demora unos 2 minutos.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -n "${OSS_CAD_SUITE:-}" ] && export PATH="$OSS_CAD_SUITE/bin:$PATH"   # si no, las herramientas tienen que estar en el PATH

COMMIT_R0=1d4a82f440e5aff9761cfea75c1623243ea53561
NOMBRE=r0_base_max_media.bin
D=build/r0

git cat-file -e "$COMMIT_R0^{commit}" 2>/dev/null || { echo "FAIL: el commit de R0 ($COMMIT_R0) no esta en este clon. Hace falta el historial completo"; exit 1; }
rm -rf "$D"; mkdir -p "$D"
git archive "$COMMIT_R0" | tar -x -C "$D"
( cd "$D" && make bin > construir.log 2>&1 ) || { echo "FAIL: no se pudo construir R0. Ver $D/construir.log"; tail -5 "$D/construir.log"; exit 1; }

esperado=$(grep " $NOMBRE$" bitstreams/SHA256SUMS | cut -d' ' -f1)
guardado=$(sha256sum "bitstreams/$NOMBRE" | cut -d' ' -f1)
obtenido=$(sha256sum "$D/build/pochoco_soc.bin" | cut -d' ' -f1)
echo "R0 construido desde el commit ${COMMIT_R0:0:7}:"
grep -E "ICESTORM_LC|ICESTORM_RAM|Max frequency" "$D/build/nextpnr.log" | tail -3 | sed 's/^Info: */  /'
echo "  sha256 en bitstreams/SHA256SUMS  $esperado"
echo "  sha256 del archivo guardado      $guardado"
echo "  sha256 del recien construido     $obtenido"
mal=0
[ "$esperado" = "$guardado" ] || { echo "FAIL: el archivo guardado no corresponde a SHA256SUMS"; mal=1; }
[ "$esperado" = "$obtenido" ] || { echo "FAIL: el bitstream reconstruido no es el guardado"; mal=1; }
python3 tools/pochoasm.py sw/historico/trade_max_media.s -o "$D/historico.hex" > /dev/null
cmp -s "$D/sw/trade.hex" "$D/historico.hex" || { echo "FAIL: sw/historico/trade_max_media.s ya no es el programa de R0"; mal=1; }

# 4. Informativo: qué cambió desde entonces en las fuentes que usa el base,
#    pasadas por el preprocesador sin definir ninguna variante y sin comentarios
pre() { iverilog -g2012 -E -o - "$1" 2>/dev/null | grep -v '^`line' | sed -e 's|//.*$||' -e 's/[[:space:]]*$//' | grep -v '^$'; }
echo "  lineas de codigo del Espino base que cambiaron desde ese commit (sin variantes definidas):"
n=0
for f in $(cd "$D" && ls rtl/*.v rtl/espino_core/*.v); do
  d=$(diff <(pre "$D/$f") <(pre "$f") | grep '^[<>]' || true)
  [ -n "$d" ] && { echo "$d" | sed "s|^|    $f: |"; n=$((n + 1)); }
done
[ $n = 0 ] && echo "    ninguna"

[ $mal = 0 ] && echo "PASS: R0 se reproduce bit a bit desde este repositorio"
exit $mal
