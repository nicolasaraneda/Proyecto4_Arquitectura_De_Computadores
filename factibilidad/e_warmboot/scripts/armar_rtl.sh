#!/usr/bin/env bash
# armar_rtl.sh: arma la carpeta de RTL del SoC con vigilante.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Copia rtl/ y rtl/espino_core/ del repositorio a
# factibilidad/e_warmboot/build/rtl_vig/ y pone encima los tres archivos de
# este estudio:
#
#   soc/pochoco_soc.v         copia modificada (parámetros Vigilante, VigN, VigDestino)
#   soc/pochoco_spi_slave.v   copia modificada (tres salidas nuevas)
#   rtl/vigilante.v           módulo nuevo
#
# El resto del RTL se usa tal como está en el repositorio, sin copias
# versionadas. La carpeta resultante tiene la misma forma que rtl/, así que
# sirve para tools/medir_variante.sh (RTL=...) y para el comando del
# testbench oficial.
#
# Las copias se hicieron sobre las versiones de rtl/ con los hashes de abajo.
# Si esos archivos cambian en el repositorio, el script avisa: hay que
# rehacer las copias antes de confiar en una medición.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/e_warmboot/scripts/armar_rtl.sh
set -euo pipefail

E=factibilidad/e_warmboot
D=$E/build/rtl_vig
SOC_BASE=0c8951456a37faa5052b2438bc74b107b466e6f9f452e69d3f94139bb07d22ad
SPI_BASE=dab33af8b2cb654590bc708afd3f68f46a6121705cee21f7bc33bb6b61e7e443

[ "$(sha256sum rtl/pochoco_soc.v | cut -d' ' -f1)" = "$SOC_BASE" ] ||
  echo "AVISO: rtl/pochoco_soc.v cambió desde que se hizo la copia de $E/soc" >&2
[ "$(sha256sum rtl/pochoco_spi_slave.v | cut -d' ' -f1)" = "$SPI_BASE" ] ||
  echo "AVISO: rtl/pochoco_spi_slave.v cambió desde que se hizo la copia de $E/soc" >&2

# Se arma en una carpeta temporal y solo se reemplaza la anterior si algo
# cambió: así otra corrida que la esté leyendo no la ve a medio copiar.
T=$D.tmp.$$
rm -rf "$T"
mkdir -p "$T/espino_core"
cp rtl/*.v "$T/"
cp rtl/espino_core/*.v "$T/espino_core/"
cp "$E/soc/pochoco_soc.v" "$E/soc/pochoco_spi_slave.v" "$E/rtl/vigilante.v" "$T/"
if [ -d "$D" ] && diff -rq "$T" "$D" > /dev/null; then
  rm -rf "$T"
else
  rm -rf "$D"
  mv "$T" "$D"
fi
echo "$D"
