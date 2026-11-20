#!/usr/bin/env bash
# controles.sh: controles negativos de las pruebas de R1 y R2. Cada uno es
# sw/fondo.s con un error puesto a propósito (tools/fondo/controles.py), corrido
# con la misma comparación que usan las demás pruebas. Todos tienen que fallar.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Desde el 17/11 el programa es la regla de cotas (decisión T133): los controles
# corren con series normalizadas que tocan 100 y 255. La revisión es la estricta
# de siempre (sin --permitir-ram), también en el control del hilo que escribe la
# RAM.
#
# Uso: tools/fondo/controles.sh   (o make fondo-controles). Variables: NTICKS, JOBS.
# Resultado en docs/mediciones/fondo/HW/controles.txt (HW es r1 o r2).
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BF/controles
NT=${NTICKS:-6000}
SALIDA=${SALIDA:-$MF/controles.txt}
rm -rf "$O"; mkdir -p "$O"
ensamblar_fondo || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1
NORM=$(serie_norm reversion 1 $NT)
NORM2=$(serie_norm reversion 39 $NT)
META=$(meta_ventana 10500 $NT)
$PYTHON $TF/controles.py --lista > "$O/lista.txt"
while IFS='|' read -r n falla ser param desc; do
  $PYTHON $TF/controles.py "$n" -o "$O/$n.s" || { echo "FAIL: no se pudo armar el control $n"; exit 1; }
  tab=""
  if [ -n "$param" ]; then
    $PYTHON ref/fondo.py --param "$param" --tabla-hex "$O/$n.tabla.hex"
    tab="TABLA=$O/$n.tabla.hex "
  fi
  if [ -n "$falla" ]; then
    $PYTHON $TF/variante.py "$falla" -i "$O/$n.s" -o "$O/${n}_f.s" && mv "$O/${n}_f.s" "$O/$n.s"
  fi
  s=$META; [ "$ser" = norm ] && s=$NORM; [ "$ser" = norm2 ] && s=$NORM2
  echo "${tab}caso $O/$n $O/$n.s $s $NT 100000 4000 --limite 1131"
done < "$O/lista.txt" | en_paralelo

{
cabecera "Controles negativos de las pruebas del fondo" tools/fondo/controles.sh "make fondo-controles"
echo "$NT ticks por control. Un control esta bien cuando la comparacion FALLA."
echo
total=0; detectados=0
while IFS='|' read -r n falla ser param desc; do
  total=$((total + 1))
  r=$(cat "$O/$n/resultado.txt")
  if echo "$r" | grep -q "^FAIL"; then
    detectados=$((detectados + 1))
    echo "DETECTADO $n: $desc${falla:+ (con $falla)}"
    echo "    $(echo "$r" | sed 's/^FAIL [^.]*\. //' | cut -c1-200)"
  else
    echo "FAIL $n: no se detecto. $desc"
  fi
done < "$O/lista.txt"
echo
if [ "$detectados" = "$total" ]; then echo "PASS: $detectados de $total controles detectados"; else echo "FAIL: $detectados de $total controles detectados"; fi
} | tee "$SALIDA"
cierre "$SALIDA"
