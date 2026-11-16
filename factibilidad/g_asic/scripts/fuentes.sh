# fuentes.sh: lista de fuentes del macro ASIC. Se incluye con "source" desde
# los demás scripts, que corren desde la raíz del repositorio.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El core, los periféricos y el esclavo SPI son los archivos de rtl/, sin
# copiar. De rtl/ quedan fuera tres archivos, reemplazados por las copias de
# factibilidad/g_asic/rtl/: pochoco_soc.v, pochoco_ram.v y
# espino_core/espino_register_file.v.
G=factibilidad/g_asic
ROM=$G/build/gen/pochoco_rom.v
FUENTES_REPO="rtl/pochoco_periph.v rtl/pochoco_spi_slave.v \
rtl/espino_core/espino_alu.v rtl/espino_core/espino_controller.v \
rtl/espino_core/espino_core.v rtl/espino_core/espino_decoder.v \
rtl/espino_core/espino_id_stage.v rtl/espino_core/espino_if_stage.v \
rtl/espino_core/espino_load_store_unit.v"
FUENTES_ASIC="$G/rtl/asic_top.v $G/rtl/pochoco_soc_asic.v $G/rtl/pochoco_mem_asic.v $G/rtl/espino_register_file.v"
FUENTES="$FUENTES_ASIC $FUENTES_REPO $ROM"
export PATH=${OSS_CAD_SUITE:+$OSS_CAD_SUITE/bin:}$PATH

# ROM del programa, generada desde sw/trade.s con el ensamblador del repo.
# Se genera en un archivo temporal y solo se reemplaza si cambió, para que dos
# corridas simultáneas no se pisen el archivo mientras lo leen.
generar_rom() {
  mkdir -p $G/build/gen
  local tmp
  tmp=$(mktemp -d $G/build/gen/tmp.XXXXXX)
  python3 tools/pochoasm.py sw/trade.s -o $tmp/trade.hex --rom $tmp/pochoco_rom.v > /dev/null
  cmp -s $tmp/trade.hex sw/trade.hex || { echo "FAIL: sw/trade.hex no corresponde a sw/trade.s"; rm -rf $tmp; exit 1; }
  cmp -s $tmp/pochoco_rom.v $ROM 2>/dev/null || mv $tmp/pochoco_rom.v $ROM
  rm -rf $tmp
}
