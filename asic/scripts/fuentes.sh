# fuentes.sh: lista de fuentes del macro ASIC del barrel. Se incluye con "source"
# desde los demás scripts de asic/scripts/, que corren desde la raíz del repositorio.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El core barrel, la extensión, el decodificador, la ALU, la LSU, el periférico y el
# esclavo SPI son los archivos de rtl/, sin copiar. Las copias modificadas están en
# asic/rtl/ (el SoC, el tope y el banco de cuatro contextos en flip-flops) y la
# memoria del programa es la de la edición ASIC del base
# (asic/rtl/pochoco_mem_asic_barrel.v). Las ROM del programa y de la tabla
# se generan desde sw/fondo.s y sw/fondo_tabla.hex.
A=asic
GEN=$A/build/gen
ROM=$GEN/pochoco_rom.v
TABLA_ROM=$GEN/pochoco_tabla_rom.v
FUENTES_REPO="rtl/pochoco_periph.v rtl/pochoco_spi_slave.v \
rtl/espino_core/espino_alu.v rtl/espino_core/espino_decoder.v \
rtl/espino_core/espino_load_store_unit.v rtl/espino_core/espino_xd.v \
rtl/espino_core/espino_barrel_core.v asic/rtl/pochoco_mem_asic_barrel.v"
FUENTES_ASIC="$A/rtl/asic_top_barrel.v $A/rtl/pochoco_soc_asic_barrel.v $A/rtl/espino_barrel_regfile.v"
FUENTES="$FUENTES_ASIC $FUENTES_REPO $ROM $TABLA_ROM"
export PATH=${OSS_CAD_SUITE:+$OSS_CAD_SUITE/bin:}$PATH
generar_rom() {
  mkdir -p $GEN
  local tmp
  tmp=$(mktemp -d $GEN/tmp.XXXXXX)
  python3 tools/pochoasm.py sw/fondo.s -o $tmp/fondo.hex --rom $tmp/pochoco_rom.v > /dev/null
  python3 $A/scripts/gen_tabla.py sw/fondo_tabla.hex $tmp/pochoco_tabla_rom.v
  cmp -s $tmp/pochoco_rom.v $ROM 2>/dev/null || mv $tmp/pochoco_rom.v $ROM
  cmp -s $tmp/pochoco_tabla_rom.v $TABLA_ROM 2>/dev/null || mv $tmp/pochoco_tabla_rom.v $TABLA_ROM
  rm -rf $tmp
}
