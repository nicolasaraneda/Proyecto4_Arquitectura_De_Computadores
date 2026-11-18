#!/usr/bin/env bash
# degradacion.sh: pruebas de degradación de R1 y R2 (criterio 6 de la puerta de
# simulación).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Desde el 17/11 (decisión T133) la decisión la toma solo el hilo 0 y los hilos 1
# a 3 quedan en un lazo de espera. Degradación significa ahora: que esos hilos
# hagan otra cosa (cuentas sin parar, escribir y leer la RAM, leer la memoria del
# programa, o las tres a la vez) no cambia ningún byte, ni la telemetría, ni el
# tiempo de respuesta del hilo 0 más allá del límite. Cada caso es sw/fondo.s con
# instrucciones insertadas en los lazos de esos hilos (tools/fondo/variante.py);
# el hilo 0 no se toca. La referencia es la misma del programa sano.
#
# Cada caso se corre con la serie Meta completa y con una serie de reversión
# normalizada (las dos tocan 100 y 255, así que la regla opera). Se compara todo:
# bytes, estado tick a tick, telemetría y protocolo, y se exige que el peor caso
# quede bajo 1131 ciclos (50 % de holgura en la ronda 3).
#
# El hilo 0 colgado (cuelgue_sup) no se prueba aquí: deja de escribir DECISION a
# propósito, y es la falla dura que ve el vigilante de R2 (make vig-relevo y
# tools/fondo/bitstreams.sh).
#
# Uso: tools/fondo/degradacion.sh   (o make fondo-degradacion). CORTA=1, JOBS.
# Resultado en docs/mediciones/fondo/HW/degradacion.txt (HW es r1 o r2).

set -uo pipefail
source "$(dirname "$0")/comun.sh"
O=$BF/degradacion
LIMITE=1131
NT=20000
SALIDA=${SALIDA:-$MF/degradacion.txt}
[ "${CORTA:-0}" = 1 ] && NT=3000
rm -rf "$O"; mkdir -p "$O"
ensamblar_fondo || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1

# etiqueta|fallas|descripción
CASOS="ocupado_1|ocupado:1|el hilo 1 hace cuentas sin parar
ocupado_2|ocupado:2|el hilo 2 hace cuentas sin parar
ocupado_3|ocupado:3|el hilo 3 hace cuentas sin parar
ocupados|ocupado:1+ocupado:2+ocupado:3|los tres hilos hacen cuentas sin parar
escribe_1|escribe:1|el hilo 1 escribe y lee la RAM sin parar
escribe_todos|escribe:1+escribe:2+escribe:3|los tres hilos escriben y leen la RAM sin parar
programa_3|programa:3|el hilo 3 lee la memoria del programa sin parar
mezcla|ocupado:1+escribe:2+programa:3|un hilo calcula, otro escribe la RAM y otro lee el programa"

META=data/practica_meta.csv
[ "${CORTA:-0}" = 1 ] && META=$(meta_ventana 10500 $NT)
NORM=$(serie_norm reversion 1 $NT)
echo "$CASOS" | while IFS='|' read -r e fallas desc; do
  $PYTHON $TF/variante.py "$fallas" -o "$O/$e.s"
  ref=$($PYTHON $TF/variante.py "$fallas" --ref)
  echo "caso $O/${e}__meta $O/$e.s $META $NT 100000 4000 --limite $LIMITE $ref"
  echo "caso $O/${e}__norm $O/$e.s $NORM $NT 100000 4000 --limite $LIMITE $ref"
done | en_paralelo

# El programa sano con las mismas series, para comparar el tiempo de respuesta
echo "caso $O/sano__meta sw/fondo.s $META $NT 100000 4000 --limite $LIMITE" | en_paralelo

{
cabecera "Pruebas de degradacion de R1 y R2" tools/fondo/degradacion.sh "make fondo-degradacion"
echo "$NT ticks por corrida, periodo de 0,1 ms. Limite del peor caso: $LIMITE ciclos."
echo "Las fallas estan en los hilos 1 a 3; el hilo 0, que decide, no se toca. La referencia es la del programa sano."
echo
echo "--- programa sano ---"
cat "$O/sano__meta/resultado.txt"
echo "$CASOS" | while IFS='|' read -r e fallas desc; do
  echo "--- $desc ($fallas) ---"
  cat "$O/${e}__meta/resultado.txt" "$O/${e}__norm/resultado.txt"
done
echo
n=$(cat $O/*__*/resultado.txt | grep -c "^PASS"); t=$(ls $O/*__*/resultado.txt | wc -l)
peor=$(cat $O/*__*/resultado.txt | sed -n 's/.*peor caso \([0-9]*\) de.*/\1/p' | sort -n | tail -1)
sano=$(sed -n 's/.*peor caso \([0-9]*\) de.*/\1/p' "$O/sano__meta/resultado.txt")
if [ "$n" = "$t" ]; then echo "PASS: $n de $t corridas con la decision esperada y a tiempo. Peor caso $peor ciclos de $LIMITE (programa sano: $sano)"
else echo "FAIL: pasan $n de $t corridas"; fi
} | tee "$SALIDA"
cierre "$SALIDA"
