#!/usr/bin/env bash
# medir_recursos.sh: celdas, BRAM y frecuencia máxima del SoC con el core
# barrel, contra el Espino base y el pipeline de 3 etapas medidos en la misma
# corrida y con el mismo script (tools/medir_variante.sh).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Deja tres archivos en docs/mediciones/barrel/:
#   recursos.txt       celdas, LUT4, BRAM y frecuencia máxima en 10 semillas de
#                      cada variante, celdas libres y cuánto cambia cada recorte.
#   desglose.txt       en qué módulo están las celdas.
#   ruta_critica.txt   la ruta crítica de la semilla más lenta de cada core.
#
# Variantes (nextpnr-ice40 --hx1k --package vq100 --freq 25, goboard.pcf):
#   barrel_base                Espino base (sin definiciones).
#   barrel_seg                 pipeline de 3 etapas (-DESPINO_SEGMENTADO).
#   barrel                     Espino barrel (-DESPINO_BARREL). Es la única
#                              variante a la que se le exige cerrar a 25 MHz
#                              en todas las semillas: si no, el script falla.
#   barrel_pc32                barrel con contador de programa de 32 bits en
#                              vez de 11.
#   barrel_por4                barrel con contador de reset de 4 bits en vez
#                              de 12.
#   *_ramdirecta               la memoria sin la lógica con que Yosys emula
#                              "leer el dato viejo" cuando se lee y se escribe
#                              la misma palabra en el mismo flanco. Es un
#                              atributo (* no_rw_check *) en una copia de
#                              rtl/pochoco_ram.v que se genera aquí. No está
#                              aplicado en rtl/: solo se mide.
#
# Los logs quedan en build/variantes/barrel* (ignorada por git).
#
# Uso: tools/barrel/medir_recursos.sh [SEMILLAS]   (o make barrel-recursos)
# Variables de entorno: JOBS (procesos de nextpnr en paralelo, por defecto 5).
set -euo pipefail
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-10}
export JOBS=${JOBS:-5}
O=$B/recursos
mkdir -p "$O"
rm -f "$O/barrel_no_cierra"
programas

# --- Copia del RTL con la memoria sin emulación de lectura durante escritura ----
# Tiene la forma que espera tools/medir_variante.sh (variable RTL): enlaces a
# todas las fuentes de rtl/ y, en vez de pochoco_ram.v, una copia cuya única
# diferencia es el atributo en los dos arreglos.
D=$O/rtl_ramdirecta
rm -rf "$D"; mkdir -p "$D/espino_core"
for f in rtl/*.v; do case "$f" in rtl/pochoco_ram.v|rtl/00_*) ;; *) ln -s "$RAIZ/$f" "$D/" ;; esac; done
ln -s "$RAIZ"/rtl/espino_core/*.v "$D/espino_core/"
sed -E 's|^( *)reg \[31:0\] (mem(_f)?) \[0:NumWords-1\];|\1(* no_rw_check *) reg [31:0] \2 [0:NumWords-1];|' \
  rtl/pochoco_ram.v > "$D/pochoco_ram.v"
[ "$(diff rtl/pochoco_ram.v "$D/pochoco_ram.v" | grep -c '^>')" = 2 ] || { echo "FAIL: la copia de pochoco_ram.v no quedo como se esperaba"; exit 1; }

HB=$B/sw/trade_h0.hex
BARREL=-DESPINO_BARREL
{
  tools/medir_variante.sh barrel_base "$SEMILLAS"
  DEFS=-DESPINO_SEGMENTADO tools/medir_variante.sh barrel_seg "$SEMILLAS"
  # El barrel tiene que cerrar a 25 MHz en todas las semillas. Si no, se anota
  # y el script termina con error después de escribir los informes.
  DEFS=$BARREL HEX=$HB EXIGIR=1 tools/medir_variante.sh barrel "$SEMILLAS" || touch "$O/barrel_no_cierra"
  DEFS=$BARREL HEX=$HB PARAMS="PcW=32" tools/medir_variante.sh barrel_pc32 "$SEMILLAS"
  DEFS=$BARREL HEX=$HB PARAMS="PorBits=4" tools/medir_variante.sh barrel_por4 "$SEMILLAS"
  RTL=$D DEFS=$BARREL HEX=$HB tools/medir_variante.sh barrel_ramdirecta "$SEMILLAS"
  RTL=$D tools/medir_variante.sh barrel_base_ramdirecta "$SEMILLAS"
  RTL=$D DEFS=-DESPINO_SEGMENTADO tools/medir_variante.sh barrel_seg_ramdirecta "$SEMILLAS"
} > "$O/lineas.txt"

# --- Desglose por módulo: síntesis con las fronteras del SoC conservadas ---------
# desglose NOMBRE "FUENTES" HEX [definiciones]
desglose() {
  local n=$1 src=$2 hex=$3 defs=${4:-}
  yosys -q -l "$O/desglose_$n.log" -p "read_verilog $defs $src; chparam -set MemFile \"$hex\" pochoco_soc; \
    hierarchy -top pochoco_soc; \
    setattr -set keep_hierarchy 1 pochoco_soc/u_core pochoco_soc/u_ram pochoco_soc/u_spi pochoco_soc/u_periph; \
    synth_ice40 -top pochoco_soc; tee -o $O/desglose_$n.txt stat"
}
desglose base       "$BASE_SRC"   sw/trade.hex &
desglose segmentado "$BASE_SRC"   sw/trade.hex -DESPINO_SEGMENTADO &
desglose barrel     "$BARREL_SRC" "$HB" &
# Bloques del core barrel por separado (sin aplanar nada)
yosys -q -l "$O/bloques_barrel.log" -p "read_verilog $BARREL_SRC; chparam -set MemFile \"$HB\" pochoco_soc; \
  synth_ice40 -top pochoco_soc -noflatten; tee -o $O/bloques_barrel.txt stat" &
wait

$PYTHON $T/informe_recursos.py "$O" build/variantes "$SEMILLAS" "$M"
cat "$M/recursos.txt"

if [ -e "$O/barrel_no_cierra" ]; then
  echo "FAIL: el barrel no cierra a 25 MHz en las $SEMILLAS semillas"; exit 1
fi
