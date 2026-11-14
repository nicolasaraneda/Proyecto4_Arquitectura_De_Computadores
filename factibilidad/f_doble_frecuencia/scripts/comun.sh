#!/usr/bin/env bash
# comun.sh: rutas y funciones compartidas por los scripts de la pieza F.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con `source`. Deja el directorio de trabajo en la raíz del
# repositorio (los $readmemh del SoC son relativos a ella) y define:
#   F      carpeta de la pieza, relativa a la raíz
#   B      carpeta de productos intermedios (F/build, ignorada por git)
#   M      carpeta de mediciones (F/mediciones, versionada)
#   SOC_X2 fuentes del SoC con el reloj doblado
set -euo pipefail

export PATH="$HOME/herramientas/oss-cad-suite/bin:$PATH"

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$RAIZ"

F=factibilidad/f_doble_frecuencia
B=$F/build
M=$F/mediciones
mkdir -p "$B" "$M"

# El SoC con reloj doblado: la copia modificada de pochoco_soc.v, el
# duplicador y el resto del RTL del repositorio sin tocar.
SOC_X2="$F/rtl/pochoco_soc_x2.v $F/rtl/duplicador_reloj.v rtl/pochoco_periph.v rtl/pochoco_ram.v rtl/pochoco_spi_slave.v $(echo rtl/espino_core/*.v)"

JOBS=${JOBS:-5}

# Frecuencia máxima que informa nextpnr para un reloj, después de rutear
fmax_de() {   # fmax_de LOG RELOJ
  grep "Max frequency for clock '$2'" "$1" | tail -1 | sed -E 's/.*: ([0-9.]+) MHz.*/\1/'
}

# Mínimo, mediana y máximo de una lista de números, uno por línea
min_med_max() {
  sort -n | awk '{a[NR]=$1} END {if (NR==0) {print "- - -"} else
    printf "%.2f %.2f %.2f", a[1], (NR%2)? a[(NR+1)/2] : (a[NR/2]+a[NR/2+1])/2, a[NR]}'
}
