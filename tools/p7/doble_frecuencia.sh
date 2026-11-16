#!/usr/bin/env bash
# doble_frecuencia.sh: reproduce el resultado negativo del duplicador de reloj
# por lógica (pieza F de la factibilidad) y lo compara con lo guardado.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El experimento es del tramo de factibilidad (factibilidad/
# f_doble_frecuencia, etiqueta archivo/factibilidad-fondo), con su propio RTL: una copia de pochoco_soc.v con el
# reloj interno saliendo del duplicador. No se trae a rtl/ porque no compite
# y el RTL compartido no se toca. Este script extrae la etiqueta completa en
# build/p7/factibilidad-fondo/ con git archive, corre ahí sus objetivos
#   soc     SoC base y segmentado con y sin duplicador, 10 semillas
#   humo    testbench oficial sin modificar sobre el SoC doblado
#   margen  margen real con el ciclo de trabajo del oscilador y presupuesto
# y compara las salidas con las copias guardadas en docs/mediciones/p7/
# doble_frecuencia/ (que son las de la rama, sin cambios).
#
# Uso: tools/p7/doble_frecuencia.sh   (make p7-doble). Unos 15 minutos.
# Variable RAMA (por defecto la etiqueta archivo/factibilidad-fondo).
set -euo pipefail
source "$(dirname "$0")/comun.sh"

RAMA=${RAMA:-archivo/factibilidad-fondo}
D=$B/factibilidad-fondo
G=$M/doble_frecuencia
rm -rf "$D"; mkdir -p "$D" "$G"
git archive "$RAMA" | tar -x -C "$D"
F=$D/factibilidad/f_doble_frecuencia
make -C "$F" soc humo margen SEMILLAS=10 JOBS=10 > "$B/doble_frecuencia.log" 2>&1

{
  echo "Duplicador de reloj por lógica: reproducción desde $RAMA ($(git rev-parse --short "$RAMA^{commit}"))"
  echo "Generado por tools/p7/doble_frecuencia.sh (make p7-doble). No editar a mano."
  echo
  versiones
  echo
  for f in soc_x2.txt humo_soc_x2.txt humo_fase.txt margen.txt; do
    if cmp -s "$F/mediciones/$f" "$G/$f"; then
      echo "IGUAL  $f: la corrida de hoy es idéntica byte a byte a la guardada"
    else
      echo "DISTINTO $f: diferencias con la guardada:"
      diff "$G/$f" "$F/mediciones/$f" | head -20 | sed 's/^/    /'
    fi
  done
} > "$G/reproduccion.txt"
cat "$G/reproduccion.txt"
