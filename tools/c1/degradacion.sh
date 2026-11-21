#!/usr/bin/env bash
# degradacion.sh: pruebas de degradación de R3 (criterio 6 de la puerta de
# simulación). Los casos los arma tools/c1/degradacion.py; las fallas las pone
# tools/c1/variante.py sin tocar una línea del programa.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Reglas que se comprueban (las de R2, docs/c1_plan.md): el hilo 0 calcula siempre
# la banda 40 por su cuenta; usa la política solo si trae el tick actual; vencido
# el plazo, si es del tick anterior sostiene una orden completa (o mantiene) y si
# es más vieja pasa a modo seguro, que es la banda 40 sin política para siempre.
#
#   - Un hilo colgado por vez (1, 2 y 3), en cinco situaciones: antes de que la
#     tabla esté activa, justo después de la orden parcial de entrada, con la media
#     posición tomada, en el motor y en el candado.
#   - Dato viejo: la política llega después del plazo (un tick, dos seguidos, y un
#     atraso que se salta precios).
#   - Modo seguro: precio bajo el mínimo válido, ronda más larga que la supuesta y
#     política apagada.
#
# En cada caso se compara cada byte con la referencia (que modela la falla), el LED
# de modo seguro, una sola escritura en DECISION por tick, el protocolo y el estado
# de los hilos hasta la falla. Donde queda el modo seguro se exige además que desde
# ese tick los bytes sean los de la banda 40 de R2 (ref/fondo.py). El peor caso de
# la respuesta tiene que quedar bajo 1131 ciclos.
#
# Uso: [CORTA=1] [JOBS=12] tools/c1/degradacion.sh   (make c1-degradacion)
# Resultado en docs/mediciones/c1/degradacion.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BC/degradacion
SALIDA=${SALIDA:-$MC/degradacion.txt}
rm -rf "$O"; mkdir -p "$O"
ensamblar_c1 || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1
[ "${CORTA:-0}" = 1 ] && CORTA_ARG=--corta || CORTA_ARG=
$PYTHON $TC/degradacion.py "$O" $CORTA_ARG > "$O/casos.txt" || { echo "FAIL: no se pudieron armar los casos"; exit 1; }
{
  while IFS='|' read -r e args desc; do echo "caso $O/$e $args"; done < "$O/casos.txt"
  echo "caso $O/sano_mano --serie $O/mano.csv --nticks 2600 --inicio-ns 200000"
  echo "caso $O/sano_motor --serie $O/motor.csv --nticks 2600 --inicio-ns 200000"
} | en_paralelo

{
cabecera "Pruebas de degradacion de R3" tools/c1/degradacion.sh "make c1-degradacion"
echo "2600 ticks por corrida. Limite del peor caso: $LIMITE ciclos. La referencia modela cada falla (ref/c1/c1.py, faltas y tardias)."
echo
echo "--- programa sano, las mismas series ---"
cat "$O/sano_mano/resultado.txt" "$O/sano_motor/resultado.txt"
echo
n=0; p=0; peor=0
while IFS='|' read -r e args desc; do
  echo "--- $desc ---"
  cat "$O/$e/resultado.txt"
  n=$((n + 1)); grep -q "^PASS" "$O/$e/resultado.txt" && p=$((p + 1))
  c=$(sed -n 's/.*peor caso \([0-9]*\) de.*/\1/p' "$O/$e/resultado.txt"); [ -n "$c" ] && [ "$c" -gt "$peor" ] && peor=$c
done < "$O/casos.txt"
echo
sano=$(cat "$O"/sano_*/resultado.txt | sed -n 's/.*peor caso \([0-9]*\) de.*/\1/p' | sort -n | tail -1)
if [ "$p" = "$n" ] && [ "$n" -gt 0 ] && ! grep -q "^FAIL" "$O"/sano_*/resultado.txt; then
  echo "PASS: $p de $n casos con la decision esperada y a tiempo. Peor caso $peor ciclos de $LIMITE (programa sano en las mismas series: $sano)"
else echo "FAIL: pasan $p de $n casos"; fi
} | tee "$SALIDA"
cierre "$SALIDA"
