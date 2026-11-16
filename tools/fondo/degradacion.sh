#!/usr/bin/env bash
# degradacion.sh: pruebas de degradación del fondo (criterio 6 de la puerta de
# simulación): un gestor en lazo infinito, un voto que nunca llega y un voto
# atrasado. La decisión tiene que seguir saliendo a tiempo y ser la esperada.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Cada caso es sw/fondo.s con instrucciones insertadas en la rutina de los
# gestores (tools/fondo/variante.py). El supervisor no se toca. La decisión
# esperada sale de ref/fondo.py con la misma falla descrita como "el voto del
# gestor K no llega entre los ticks N y M". Se compara todo: bytes, estado en
# cada decisión, en qué ticks venció el plazo, telemetría y protocolo, y se
# exige que el peor caso quede bajo 1131 ciclos (50 % de holgura en la ronda 3).
#
# Cada caso se corre con dos series de 20 000 ticks: la de práctica y una
# sintética de reversión en la que el fondo sano y max_media sola deciden
# distinto, para que la prueba distinga una respuesta de la otra. La última
# columna de cada línea dice en cuántos bytes difiere lo esperado del fondo
# sano y de max_media sola.
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
CASOS="lazo_g1_inicio|cuelgue:1:1|gestor 1 en lazo infinito desde el arranque
lazo_g2_inicio|cuelgue:2:1|gestor 2 en lazo infinito desde el arranque
lazo_g3_inicio|cuelgue:3:1|gestor 3 en lazo infinito desde el arranque
lazo_g1_t1500|cuelgue:1:1500|gestor 1 en lazo infinito desde el tick 1500
lazo_g2_t1500|cuelgue:2:1500|gestor 2 en lazo infinito desde el tick 1500
lazo_g3_t1500|cuelgue:3:1500|gestor 3 en lazo infinito desde el tick 1500
lazo_dos|cuelgue:1:900+cuelgue:3:1700|gestor 1 colgado desde el tick 900 y gestor 3 desde el 1700
lazo_tres|cuelgue:1:1+cuelgue:2:1+cuelgue:3:1|los tres gestores colgados: el supervisor decide solo
sin_voto_g1|sin_voto:1:1200:1200|el voto del gestor 1 no llega en el tick 1200
sin_voto_g2_frontera|sin_voto:2:1024:1024|el voto del gestor 2 no llega en un tick de frontera de ventana (1024)
sin_voto_g3_tramo|sin_voto:3:1000:2600|el voto del gestor 3 no llega entre los ticks 1000 y 2600 y despues vuelve
atraso_g1_corto|atraso:1:160|gestor 1 atrasado 160 ciclos en todos los ticks (cabe en el plazo)
atraso_g3_corto|atraso:3:200|gestor 3 atrasado 200 ciclos en todos los ticks (cabe en el plazo)
atraso_g2_largo|atraso:2:1000|gestor 2 atrasado 1000 ciclos en todos los ticks (llega despues del plazo)
atraso_g3_tramo|atraso:3:1200:1100:2500|gestor 3 atrasado 1200 ciclos entre los ticks 1100 y 2500"

REV=$(serie reversion 1 $NT)
echo "$CASOS" | while IFS='|' read -r e fallas desc; do
  $PYTHON $TF/variante.py "$fallas" -o "$O/$e.s"
  ref=$($PYTHON $TF/variante.py "$fallas" --ref)
  extra=""; [ "$e" = lazo_tres ] && extra="--solo-max-media"
  echo "caso $O/${e}__practica $O/$e.s tb/practica.csv $NT 100000 4000 --limite $LIMITE $ref $extra"
  echo "caso $O/${e}__reversion $O/$e.s $REV $NT 100000 4000 --limite $LIMITE $ref $extra"
done | en_paralelo

{
cabecera "Pruebas de degradacion del fondo en un chip" tools/fondo/degradacion.sh "make fondo-degradacion"
echo "$NT ticks por corrida, periodo de 0,1 ms. Limite del peor caso: $LIMITE ciclos."
echo
echo "$CASOS" | while IFS='|' read -r e fallas desc; do
  echo "--- $desc ($fallas) ---"
  cat "$O/${e}__practica/resultado.txt" "$O/${e}__reversion/resultado.txt"
done
echo
n=$(cat $O/*/resultado.txt | grep -c "^PASS"); t=$(ls $O/*/resultado.txt | wc -l)
peor=$(cat $O/*/resultado.txt | sed -n 's/.*peor caso \([0-9]*\) de.*/\1/p' | sort -n | tail -1)
if [ "$n" = "$t" ]; then echo "PASS: $n de $t corridas con la decision esperada y a tiempo. Peor caso $peor ciclos de $LIMITE"
else echo "FAIL: pasan $n de $t corridas"; fi
} | tee "$SALIDA"
cierre "$SALIDA"
