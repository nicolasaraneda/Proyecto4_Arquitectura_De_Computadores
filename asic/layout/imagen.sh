#!/usr/bin/env bash
# imagen.sh: lanza asic/layout/imagen.py con KLayout en modo batch dentro de la imagen
# de Docker de LibreLane. Uso, desde la raíz: asic/layout/imagen.sh asic/runs/<tag>
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
set -eu
RUN=$1; shift
IMAGEN=${IMAGEN:-ghcr.io/librelane/librelane:3.0.16}
PDK_ROOT=${PDK_ROOT:-$HOME/.ciel/ciel/gf180mcu/versions/54435919abffb937387ec956209f9cf5fd2dfbee}
docker run --rm --user "$(id -u):$(id -g)" -v "$HOME:$HOME" -w "$(pwd)" -e HOME="$HOME" -e PDK_ROOT="$PDK_ROOT" \
  "$IMAGEN" klayout -b -r asic/layout/imagen.py -rd "run=$RUN" "$@" 2>&1 | grep -v "^Warning: No mapping"
