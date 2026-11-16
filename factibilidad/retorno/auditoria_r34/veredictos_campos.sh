#!/bin/sh
# veredictos_campos.sh: el veredicto por campo de las tablas del estudio de cierre contra el comando oficial.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: sh veredictos_campos.sh BINARIO        (desde factibilidad/retorno/auditoria_r34)
#
# El estudio de cierre corrió el comando oficial `veredicto` solo con el campo
# mixto. Con los demás campos calculó el veredicto en tablas.py, con la misma
# regla. Aquí se corre el comando oficial con los campos duros para las
# candidatas principales, con la semilla 0, y se muestra al lado lo que dice
# la tabla del estudio (r4_final/mediciones/tablas_final_s0.md, columna del
# veredicto del arnés: 2000 / 20 000 / global).
BIN=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
cd "$(dirname "$0")/.."
T=r4_final/mediciones/tablas_final_s0.md
mal=0
echo "Veredicto del comando oficial (veredicto --parada, semilla 0, G = 10) y veredicto global de la tabla del estudio"
printf "%-14s %-11s %-34s %s\n" candidata campo "comando oficial (2000 / 20000 / global)" "tabla del estudio"
for c in ejec_a completo completo_min rec_e fondo_rec; do
  for f in ingenuo fuerte racional reversores; do
    s=$c; [ "$c" = ejec_a ] && s="ejec:m=8"
    o=$("$BIN" veredicto --candidata "$s" --referencia max_media --semilla 0 --campo $f --parada | grep '^VEREDICTO' | sed 's/VEREDICTO[ 0-9]*: //; s/ (4 filas.*//' | tr '\n' '/' | sed 's|/$||; s|/| / |g')
    t=$(awk -v campo="### Campo $f" -v cand="\`$c\`" '$0 == campo {en = 1; next} /^### / {en = 0} en && index($0, "| " cand " |") == 1 {n = split($0, a, "|"); print a[n - 4]}' "$T" | sed 's/^ *//; s/ *$//')
    g=$(echo "$o" | awk -F' / ' '{print $3}')
    gt=$(echo "$t" | awk -F' / ' '{print $3}')
    if [ "$g" = "$gt" ]; then e=igual; else e=DISTINTO; mal=1; fi
    printf "%-14s %-11s %-34s %-34s %s\n" "$c" "$f" "$o" "$t" "$e"
  done
done
if [ $mal = 0 ]; then echo "PASS: los 20 veredictos por campo de la tabla coinciden con el comando oficial"
else echo "FAIL: algun veredicto de la tabla no coincide con el comando oficial"; fi
