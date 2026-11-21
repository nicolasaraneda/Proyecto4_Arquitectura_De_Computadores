#!/usr/bin/env bash
# controles.sh: controles negativos de las pruebas de R3. Cada uno es sw/c1.s o su
# tabla con un error puesto a propósito (tools/c1/controles.py), corrido con la
# misma comparación que usan las demás pruebas. Todos tienen que fallar, salvo el
# control en blanco (un cambio que no cambia el binario), que tiene que pasar.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: [JOBS=12] tools/c1/controles.sh   (make c1-controles)
# Resultado en docs/mediciones/c1/controles.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BC/controles
SALIDA=${SALIDA:-$MC/controles.txt}
rm -rf "$O"; mkdir -p "$O/deg"
ensamblar_c1 || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1
$PYTHON $TC/degradacion.py "$O/deg" > "$O/deg/casos.txt" || { echo "FAIL: no se pudieron armar las series"; exit 1; }
$PYTHON $TC/controles.py "$O" > "$O/lista.txt" || { echo "FAIL: no se pudieron armar los controles"; exit 1; }
while IFS='|' read -r n ser args desc; do echo "caso $O/${n}__$ser $args"; done < "$O/lista.txt" | en_paralelo

{
cabecera "Controles negativos de las pruebas de R3" tools/c1/controles.sh "make c1-controles"
echo "2600 ticks por corrida, tres series por control. Un control esta bien cuando la comparacion FALLA en alguna."
echo
total=0; detectados=0; blanco=FAIL
for n in $(cut -d'|' -f1 "$O/lista.txt" | awk '!v[$0]++'); do
  desc=$(grep "^$n|" "$O/lista.txt" | head -1 | cut -d'|' -f4)
  r=$(cat "$O/${n}__mano/resultado.txt" "$O/${n}__motor/resultado.txt" "$O/${n}__triangulo/resultado.txt")
  if [ "$n" = prog_histeresis ]; then
    if ! echo "$r" | grep -q "^FAIL" && [ "$(echo "$r" | grep -c "^PASS")" = 3 ]; then blanco=PASS; fi
    echo "$blanco control en blanco: una linea agregada que no cambia el binario pasa en las tres series"
    continue
  fi
  total=$((total + 1))
  if echo "$r" | grep -q "^FAIL"; then
    detectados=$((detectados + 1))
    echo "DETECTADO $n: $desc"
    echo "    $(echo "$r" | grep "^FAIL" | head -1 | sed 's/^FAIL [^.]*\. //' | cut -c1-220)"
  else
    echo "FAIL $n: no se detecto. $desc"
  fi
done
echo
if [ "$detectados" = "$total" ] && [ "$blanco" = PASS ]; then echo "PASS: $detectados de $total controles detectados, y el control en blanco pasa"; else echo "FAIL: $detectados de $total controles detectados (control en blanco: $blanco)"; fi
} | tee "$SALIDA"
cierre "$SALIDA"
