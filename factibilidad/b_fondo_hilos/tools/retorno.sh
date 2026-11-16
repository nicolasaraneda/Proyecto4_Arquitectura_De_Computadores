#!/usr/bin/env bash
# retorno.sh: cuánto rinde la configuración que corre en la placa contra max_media.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El programa de esta pieza implementa fondo_min sin simplificarlo, así que su
# resultado de retorno es el que midió el estudio 4B
# (factibilidad/retorno/r4b_fondo/mediciones/veredicto_fondo_min.txt). Este
# script no repite ese veredicto. Deja constancia de que la referencia contra
# la que se compara el programa es ese mismo módulo (misma huella del fuente)
# y vuelve a medir, con el arnés compilado aquí, el patrimonio medio de
# fondo_min, de fondo_min_ant (la variante "anterior") y de max_media en las
# series de evidencia de la semilla 0.
#
# Lee las series de factibilidad/retorno/build/series (las genera el Makefile
# de esa carpeta) y no escribe nada fuera de esta: corre sin caché de resultados.
#
# Uso: factibilidad/b_fondo_hilos/tools/retorno.sh   (o make retorno)
# Resultado en mediciones/retorno.txt. Demora unos 20 segundos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

R=factibilidad/retorno
export RETORNO_SIN_CACHE=1 RETORNO_RESULTADOS=$RAIZ/$B/resultados HILOS=${HILOS:-4}

{
echo "Retorno de la configuracion que corre en la placa (fondo_min) contra max_media"
echo "Generado por factibilidad/b_fondo_hilos/tools/retorno.sh (make retorno). No editar a mano."
echo
echo "Modulo de referencia: $R/r4b_fondo/fondo.c, md5 $(md5sum < $R/r4b_fondo/fondo.c | cut -d' ' -f1)"
echo "Nucleo del arnes: md5 de nucleo.c $(md5sum < $R/nucleo/nucleo.c | cut -c1-12), de e_param.c $(md5sum < $R/nucleo/e_param.c | cut -c1-12)"
echo "Alias: $("$ARNES" listar | grep 'cand:fondo_min ' | sed 's/  */ /g')"
echo "       $("$ARNES" listar | grep 'cand:fondo_min_ant ' | sed 's/  */ /g')"
echo
echo "Patrimonio final (H1), series de evidencia, semilla 0. dif y ee: diferencia pareada contra max_media y su error estandar."
echo
for caso in "2000:" "20000:--interior"; do
  largo=${caso%%:*}; extra=${caso#*:}
  echo "--- $largo ticks ${extra:+(solo series interiores: precio siempre entre 21 y 249)} ---"
  "$ARNES" resumen --estrategia "max_media;fondo_min;fondo_min_ant" --conjunto evidencia --largo "$largo" --semilla 0 $extra 2>&1 \
    | awk '/^#/ {print "  " $0; next} {printf "  %-14s series %6d  media %9.1f  dif %+8.1f  ee %6.1f  p5 %6d  ordenes %6.1f\n", $1, $2, $3, $4, $5, $7, $11}'
  echo
done
echo "Puntos del torneo (H3a, H3b) y veredicto del criterio de corte: no se repiten aqui. Estan en"
echo "$R/r4b_fondo/mediciones/veredicto_fondo_min.txt y veredicto_fondo_min_ant.txt:"
grep -E "^(2000 +todas +evidencia +H3[ab]|20000 +interiores +evidencia +H3[ab]|20000 +parada +evidencia +H3[ab])" $R/r4b_fondo/mediciones/veredicto_fondo_min.txt | sed 's/^/  fondo_min      /'
grep -E "^(2000 +todas +evidencia +H3[ab]|20000 +interiores +evidencia +H3[ab]|20000 +parada +evidencia +H3[ab])" $R/r4b_fondo/mediciones/veredicto_fondo_min_ant.txt | sed 's/^/  fondo_min_ant  /'
} | tee "$M/retorno.txt"
