#!/usr/bin/env bash
# interfaz.sh: el ejemplo de estrategia, compilado y corrido desde una carpeta ajena al repositorio.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Copia ejemplo/minimo/mia.c a una carpeta fuera del repositorio (AJENA),
# escribe ahí el Makefile del README con la ruta del núcleo, compila y corre
# los comandos del arnés. Antes y después calcula la huella de nucleo/ para
# mostrar que no se tocó ningún archivo del núcleo.
#
#   bash auditoria/interfaz.sh            (desde factibilidad/retorno)
set -euo pipefail

RETORNO="$(cd "$(dirname "$0")/.." && pwd)"
RAIZ="$(cd "$RETORNO/../.." && pwd)"
AJENA="${AJENA:-${TMPDIR:-/tmp}/auditoria_interfaz_$(id -u)}"
export HILOS="${HILOS:-6}"

huella() { cat "$RETORNO"/nucleo/* | sha256sum | cut -c1-16; }

antes="$(huella)"
rm -rf "$AJENA"
mkdir -p "$AJENA"
cp "$RETORNO/ejemplo/minimo/mia.c" "$AJENA/mia.c"
# El Makefile del README, con la ruta absoluta del núcleo. Las recetas llevan tabulador.
printf 'include %s/nucleo/nucleo.mk\nbuild/arnes: $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) mia.c\n\t@mkdir -p build\n\t$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) mia.c $(NUCLEO_LIBS)\n' "$RETORNO" > "$AJENA/Makefile"

echo "Interfaz: estrategia propia desde una carpeta ajena al repositorio"
case "$AJENA" in "$RAIZ"/*) echo "Carpeta fuera del repositorio: NO" ;; *) echo "Carpeta fuera del repositorio: si" ;; esac
echo "Archivos: $(cd "$AJENA" && ls | tr '\n' ' ')"
make -s -C "$AJENA" build/arnes
cd "$AJENA"
echo "--- listar"
build/arnes listar | grep -E "^  (mia|param) "
echo "--- causal"
build/arnes causal --estrategia mia | tail -1
echo "--- correr (con entra=4 es la regla base: 27062 con 388 ordenes)"
build/arnes correr --estrategia "mia:k=5,entra=4" --serie "$RAIZ/tb/practica.csv" | tail -1
echo "--- resumen (mia sin parametros es max_media: las dos filas tienen que ser iguales)"
build/arnes resumen --conjunto remuestreo --largo 2000 --semilla 0 --estrategia "max_media;mia" | cut -d' ' -f1-9
echo "--- veredicto de mia:entra=4 contra max_media, 2000 ticks, semilla 0"
build/arnes veredicto --candidata "mia:entra=4" --referencia max_media --largo 2000 --semilla 0 | tail -3
despues="$(huella)"
echo "--- huella de nucleo/ antes $antes y despues $despues"
r1="$(build/arnes resumen --conjunto remuestreo --largo 2000 --semilla 0 --estrategia "max_media;mia" | sed -n 2p | cut -d' ' -f2-)"
r2="$(build/arnes resumen --conjunto remuestreo --largo 2000 --semilla 0 --estrategia "max_media;mia" | sed -n 3p | cut -d' ' -f2-)"
w="$(build/arnes correr --estrategia "mia:k=5,entra=4" --serie "$RAIZ/tb/practica.csv" | tail -1 | cut -d' ' -f2,4)"
if [ "$antes" = "$despues" ] && [ "$r1" = "$r2" ] && [ "$w" = "27062 388" ]; then
  echo "PASS: compila y corre fuera del repositorio sin editar nada del nucleo"
else
  echo "FAIL"; exit 1
fi
