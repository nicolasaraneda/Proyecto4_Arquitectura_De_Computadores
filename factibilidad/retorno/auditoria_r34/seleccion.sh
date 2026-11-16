#!/bin/sh
# seleccion.sh: indicios sobre el sesgo de selección de los estudios 3 y 4.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: sh seleccion.sh            (desde factibilidad/retorno/auditoria_r34)
#
# Junta en un solo texto lo que se puede comprobar con archivos: fechas de
# modificación, huellas, bitácoras, usos de la semilla 3 y cantidad de
# variantes. Las fechas de archivo son un indicio y no una prueba: se pueden
# cambiar. No modifica nada.
cd "$(dirname "$0")/.."
F="--time-style=+%d/%m_%H:%M:%S"
fecha() { ls -l "$F" "$1" 2>/dev/null | awk '{print $6}'; }

echo "1. Fuentes que fijan las candidatas (ultima modificacion)"
for f in r3_ejecucion/ejec.c r4b_fondo/fondo.c r4c_aprendizaje/e_tabla.c r4c_aprendizaje/e_patron.c r4c_aprendizaje/pred.h \
         r4c_aprendizaje/aprendiz.c nucleo/e_param.c nucleo/e_rivales.c nucleo/nucleo.c nucleo/torneo.c r4_final/fondoc.c r4_final/final.c; do
  printf "   %-34s %s\n" "$f" "$(fecha $f)"
done

echo
echo "2. Semilla 3: series, lista y corrida"
printf "   %-58s %s\n" "primera serie generada (remuestreo_s3_n2000.bin)" "$(fecha build/series/remuestreo_s3_n2000.bin)"
printf "   %-58s %s\n" "ultima serie generada (borde_alto_s3_n20000.bin)" "$(fecha build/series/borde_alto_s3_n20000.bin)"
printf "   %-58s %s\n" "tablas de la exploracion con la semilla 0 (bitacora)" "$(grep -m1 'Exploración con la semilla 0 terminada' r4_final/AVANCE.md | cut -c3-7)"
printf "   %-58s %s\n" "expectativa escrita (titulo en AVANCE.md)" "$(grep -m1 'Expectativa para la semilla 3' r4_final/AVANCE.md | sed 's/.*(\(.*\))/\1/')"
printf "   %-58s %s\n" "inicio de la corrida (reservada_usada.txt)" "$(grep 'inicio de la corrida' r4_final/mediciones/reservada_usada.txt | sed 's/.*: //')"
printf "   %-58s %s\n" "primera salida con la semilla 3 (hipotesis_final_s3_n2000)" "$(fecha r4_final/mediciones/hipotesis_final_s3_n2000.txt)"
printf "   %-58s %s\n" "ultima salida de evaluacion con la semilla 3" "$(fecha r4_final/mediciones/hipotesis_duelo_ejec_a_s3_n20000_par.txt)"
printf "   %-58s %s\n" "registro de la corrida (build/final_s3.log)" "$(fecha r4_final/build/final_s3.log)"
echo "   Fuentes modificados DESPUES del inicio de la corrida con la semilla 3 (21:38):"
for f in r3_ejecucion/ejec.c r4b_fondo/fondo.c r4c_aprendizaje/e_tabla.c r4c_aprendizaje/e_patron.c r4c_aprendizaje/pred.h r4c_aprendizaje/aprendiz.c \
         nucleo/*.c nucleo/*.h r4_final/fondoc.c r4_final/final.c r4_final/correr.py r4_final/resumen.py r4_final/tablas.py r4_final/lista_final.txt; do
  if [ "$f" -nt r4_final/mediciones/hipotesis_final_s3_n2000.txt ]; then printf "     %-34s %s\n" "$f" "$(fecha $f)"; fi
done

echo
echo "3. La lista final: huella de la original contra la anotada antes de la corrida"
if [ -f r4_final/build/lista_final_original.txt ]; then
  echo "   md5 de build/lista_final_original.txt: $(md5sum < r4_final/build/lista_final_original.txt | cut -c1-32)"
  echo "   md5 anotado en reservada_usada.txt:    $(grep '^md5 de lista_final.txt' r4_final/mediciones/reservada_usada.txt | sed 's/.*: //')"
  cambian=$(diff r4_final/build/lista_final_original.txt r4_final/lista_final.txt | grep -c '^>')
  nocom=$(diff r4_final/build/lista_final_original.txt r4_final/lista_final.txt | grep '^[<>]' | grep -vc '^[<>] #')
  echo "   lineas que cambian entre la original y la actual: $cambian; de ellas, lineas que no son comentario: $nocom"
  echo "   candidatas y duelos de la original, sin comentarios:"
  grep -v '^#' r4_final/build/lista_final_original.txt | sed 's/ *#.*//' | grep . | tr '\n' ';' | sed 's/^/     /'; echo
else
  echo "   no esta build/lista_final_original.txt (build/ no se versiona)"
fi
echo "   candidatas que de verdad se corrieron con la semilla 3 (build/final_s3.log):"
grep '^veredictos s3' r4_final/build/final_s3.log 2>/dev/null | awk '{print $3}' | tr '\n' ' ' | sed 's/^/     /'; echo

echo
echo "4. Otros usos de la semilla 3 en los estudios de retorno"
echo "   archivos con _s3 fuera de build/series y de r4_final:"
find . -path ./build/series -prune -o -path ./r4_final -prune -o -path ./auditoria_r34 -prune -o -name '*_s3*' -print | sed 's/^/     /'
echo "   (fin de la lista)"
echo "   resultados guardados del arnes con la semilla 3 (build/resultados):"
ls build/resultados 2>/dev/null | grep -c '_s3_' | sed 's/^/     /'
echo "   scripts de los estudios 3, 4B y 4C que nombran la semilla 3:"
grep -ln -- '--semilla", *"3"\|--semilla 3\|semilla=3' r3_ejecucion/herramientas/*.py r3_ejecucion/cota/*.py r3_ejecucion/Makefile r4b_fondo/*.py r4b_fondo/Makefile \
  r4c_aprendizaje/*.py r4c_aprendizaje/Makefile 2>/dev/null | sed 's/^/     /'
echo "   (fin de la lista)"
echo "   scripts que se niegan a usar semillas reservadas:"
grep -n 'reservad\|(2, 3)\|in (2, 3)\|repetir' r4b_fondo/explorar.py r4_final/correr.py 2>/dev/null | cut -c1-160 | sed 's/^/     /'

echo
echo "5. Cuantas variantes se probaron"
echo "   estudio 3 (ejecucion): $(grep -cv '^ *#\|^ *$' r3_ejecucion/herramientas/variantes.txt) en variantes.txt (una es el control) y $(grep -cv '^ *#\|^ *$' r3_ejecucion/herramientas/variantes2.txt) en variantes2.txt"
echo "   estudio 4B (fondo): variantes fondo:... distintas en mediciones/exploracion_n2000_*: $(cat r4b_fondo/mediciones/exploracion_n2000_t*_parte*.txt | awk -F'\t' '$4 == "evidencia" && $5 ~ /^fondo:/ {print $5}' | sort -u | wc -l); configuraciones con nombre en finales_n2000: $(awk -F'\t' '$4 == "evidencia" && $5 ~ /^fondo_/ {print $5}' r4b_fondo/mediciones/finales_n2000_parte1.txt | sort -u | wc -l); a 20 000 ticks: $(awk -F'\t' '$4 == "evidencia" && $5 ~ /^fondo/ {print $5}' r4b_fondo/mediciones/largo_n20000_parada_parte1.txt | sort -u | wc -l)"
echo "   estudio 4C (aprendizaje), de mediciones/barrido_cuenta.txt:"
head -12 r4c_aprendizaje/mediciones/barrido_cuenta.txt | sed 's/^/     /'
echo "   estudio de cierre: $(grep -c 'nucleo_alias' r4_final/final.c) alias propios en final.c; configuraciones de la exploracion:"
grep -n 'EXPLORACION\|exploracion' r4_final/correr.py | head -5 | cut -c1-200 | sed 's/^/     /'

echo
echo "6. Las candidatas finales ya estaban fijadas por sus estudios antes de que existiera la semilla 3"
printf "   %-66s %s\n" "r3: mediciones/finales_veredictos.txt (ejec:m=8 y la B)" "$(fecha r3_ejecucion/mediciones/finales_veredictos.txt)"
printf "   %-66s %s\n" "r4b: mediciones/veredicto_fondo_rec.txt" "$(fecha r4b_fondo/mediciones/veredicto_fondo_rec.txt)"
printf "   %-66s %s\n" "r4c: mediciones/cuarto_gestor_n2000.txt (pesos 6/3/3/4)" "$(fecha r4c_aprendizaje/mediciones/cuarto_gestor_n2000.txt)"
echo "   especificaciones en esas salidas:"
grep -ho 'ejec:m=8[^ ]*' r3_ejecucion/mediciones/finales_veredictos.txt | sort -u | sed 's/^/     /'
grep -ho 'fondo:c=3[^ ;]*' r4c_aprendizaje/cuarto.py | sort -u | head -4 | sed 's/^/     /'
