#!/usr/bin/env bash
# medir_recursos.sh: celdas, BRAM y frecuencia máxima del SoC con el core
# barrel, contra el Espino base y el pipeline de 3 etapas medidos en la misma
# corrida y con el mismo script (tools/medir_variante.sh del repositorio).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Deja tres archivos en factibilidad/a_barrel/mediciones/:
#   recursos.txt       celdas, LUT4, BRAM y frecuencia máxima en 10 semillas de
#                      cada variante, celdas libres y cuánto cambia cada recorte.
#   desglose.txt       en qué módulo están las celdas.
#   ruta_critica.txt   la ruta crítica de la semilla más lenta de cada core.
#
# Variantes (nextpnr-ice40 --hx1k --package vq100 --freq 25, goboard.pcf):
#   base, segmentado           los del repositorio, sin tocar.
#   barrel                     el prototipo.
#   barrel_pc32                contador de programa de 32 bits en vez de 11.
#   barrel_sinperiph           sin LEDs, display ni interruptores.
#   barrel_por4                contador de reset de 4 bits en vez de 12.
#   barrel_mmio                con el registro HILO y los cuatro hilos
#                              partiendo en 0 (la alternativa de arranque).
#   *_ramdirecta               la memoria sin la lógica con que Yosys emula
#                              "leer el dato viejo" cuando se lee y se escribe
#                              la misma palabra en el mismo flanco. Es un
#                              atributo (* no_rw_check *) en una copia de
#                              rtl/pochoco_ram.v que se genera aquí.
#
# Los logs quedan en build/variantes/fact_a_* (carpeta compartida del
# repositorio, ignorada por git).
#
# Uso: factibilidad/a_barrel/tools/medir_recursos.sh [SEMILLAS]   (o make recursos)
set -euo pipefail
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-10}
export JOBS=${JOBS:-5}
O=$B/recursos
mkdir -p "$O"
programas

# --- Carpetas de fuentes con la forma que espera tools/medir_variante.sh --------
# armar DESTINO core(base|barrel) ram(original|directa)
armar() {
  local d=$1 core=$2 ram=$3
  rm -rf "$d"; mkdir -p "$d/espino_core"
  ln -s "$RAIZ/rtl/pochoco_spi_slave.v" "$RAIZ/rtl/pochoco_periph.v" "$d/"
  if [ "$core" = barrel ]; then
    ln -s "$RAIZ/$A/rtl/pochoco_soc.v" "$d/"
    ln -s "$RAIZ/rtl/espino_core/espino_decoder.v" "$RAIZ/rtl/espino_core/espino_alu.v" \
          "$RAIZ/rtl/espino_core/espino_load_store_unit.v" \
          "$RAIZ/$A/rtl/espino_barrel_core.v" "$RAIZ/$A/rtl/espino_barrel_regfile.v" "$d/espino_core/"
  else
    ln -s "$RAIZ/rtl/pochoco_soc.v" "$d/"
    ln -s "$RAIZ"/rtl/espino_core/*.v "$d/espino_core/"
  fi
  if [ "$ram" = directa ]; then
    # Única diferencia con rtl/pochoco_ram.v: el atributo en los dos arreglos
    sed -E 's|^( *)reg \[31:0\] (mem(_f)?) \[0:NumWords-1\];|\1(* no_rw_check *) reg [31:0] \2 [0:NumWords-1];|' \
      rtl/pochoco_ram.v > "$d/pochoco_ram.v"
    [ "$(diff rtl/pochoco_ram.v "$d/pochoco_ram.v" | grep -c '^>')" = 2 ] || { echo "FAIL: la copia de pochoco_ram.v no quedo como se esperaba"; exit 1; }
  else
    ln -s "$RAIZ/rtl/pochoco_ram.v" "$d/"
  fi
}
armar "$O/rtl_barrel"            barrel original
armar "$O/rtl_barrel_ramdirecta" barrel directa
armar "$O/rtl_base_ramdirecta"   base   directa

HB=$B/sw/trade_h0.hex
{
  tools/medir_variante.sh fact_a_base "$SEMILLAS"
  DEFS=-DESPINO_SEGMENTADO tools/medir_variante.sh fact_a_segmentado "$SEMILLAS"
  RTL=$O/rtl_barrel HEX=$HB tools/medir_variante.sh fact_a_barrel "$SEMILLAS"
  RTL=$O/rtl_barrel HEX=$HB PARAMS="PcW=32" tools/medir_variante.sh fact_a_barrel_pc32 "$SEMILLAS"
  RTL=$O/rtl_barrel HEX=$HB DEFS=-DBARREL_SIN_PERIPH tools/medir_variante.sh fact_a_barrel_sinperiph "$SEMILLAS"
  RTL=$O/rtl_barrel HEX=$HB PARAMS="PorBits=4" tools/medir_variante.sh fact_a_barrel_por4 "$SEMILLAS"
  RTL=$O/rtl_barrel HEX=$B/sw/hilo_mmio.hex DEFS="-DBARREL_MMIO_HILO -DBARREL_BOOT_PASO=0" tools/medir_variante.sh fact_a_barrel_mmio "$SEMILLAS"
  RTL=$O/rtl_barrel_ramdirecta HEX=$HB tools/medir_variante.sh fact_a_barrel_ramdirecta "$SEMILLAS"
  RTL=$O/rtl_base_ramdirecta tools/medir_variante.sh fact_a_base_ramdirecta "$SEMILLAS"
  RTL=$O/rtl_base_ramdirecta DEFS=-DESPINO_SEGMENTADO tools/medir_variante.sh fact_a_segmentado_ramdirecta "$SEMILLAS"
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

$PYTHON $A/tools/informe_recursos.py "$O" build/variantes "$SEMILLAS" "$M"
cat "$M/recursos.txt"
