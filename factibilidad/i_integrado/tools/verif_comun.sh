# verif_comun.sh: compilación de tb/tb_verif.sv del estudio del barrel con el
# SoC integrado. Lo comparten tools/verif_rv32e.sh y tools/mutaciones.sh.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con "source" después de tools/comun.sh.
#
# El testbench instancia en una misma simulación el barrel y cuatro SoC
# originales con el Espino base. Para que convivan, el SoC de esta carpeta se
# compila con el nombre pochoco_soc_barrel y su esclavo SPI (la copia de
# e_warmboot con las tres salidas del vigilante) con el nombre
# pochoco_spi_slave_vig. El decodificador de la extensión ya tiene su propio
# nombre (espino_decoder_xd). Los Espino base usan rtl/ sin tocar: las
# definiciones XD_*, I_VIGILANTE e I_TABLA no aparecen en esos archivos.

# preparar_spi DIR: deja en DIR/pochoco_spi_slave_vig.v la copia renombrada
preparar_spi() {
  local d=$1
  mkdir -p "$d"
  sed 's/^module pochoco_spi_slave\b/module pochoco_spi_slave_vig/' $E/soc/pochoco_spi_slave.v > "$d/pochoco_spi_slave_vig.v"
  grep -q "^module pochoco_spi_slave_vig" "$d/pochoco_spi_slave_vig.v" || { echo "FAIL: no se pudo renombrar el esclavo SPI"; return 1; }
  VERIF_SPI=$d/pochoco_spi_slave_vig.v
  export VERIF_SPI
}

# compilar_verif DIR "definiciones" [CARPETA_RTL]: compila con Verilator en
# DIR/obj/sim. Con CARPETA_RTL toma de ahí espino_barrel_core.v, pochoco_soc.v,
# tabla_mmio.v y tabla_ram.v (copias mutadas de tools/mutar.py) en vez de los
# de rtl/ de esta carpeta.
compilar_verif() {
  local d=$1 defs=$2 r=${3:-$I/rtl}
  mkdir -p "$d"
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_verif ${VERIF_OPT:--O3} \
    -DPOCHOCO_SOC_MODULE=pochoco_soc_barrel -DPOCHOCO_SPI_MODULE=pochoco_spi_slave_vig -DNO_ICE40_DEFAULT_ASSIGNMENTS $defs \
    --Mdir "$d/obj" -o sim "$CELLS_SIM" $BASE_SRC "$VERIF_SPI" "$r/pochoco_soc.v" "$r/espino_barrel_core.v" $A/rtl/espino_barrel_regfile.v \
    $I/rtl/espino_decoder_xd.v $E/rtl/vigilante.v "$r/tabla_mmio.v" "$r/tabla_ram.v" $XD_SRC $A/tb/tb_verif.sv > "$d/verilator.log" 2>&1
}
export -f compilar_verif
export CELLS_SIM BASE_SRC XD_SRC A I E
