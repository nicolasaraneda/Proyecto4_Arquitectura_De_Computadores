#!/usr/bin/env bash
# repeticion.sh: vuelve a correr los objetivos de las dos piezas y compara con lo guardado.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Guarda una copia de mediciones/ de cada pieza, corre sus objetivos con make y
# compara archivo por archivo. Se ignoran las líneas que cambian por
# construcción: el commit de partida y los tiempos de corrida.
#
#   b_fondo_hilos   programa, ticks, variantes, estado, oficial y equiv. El
#                   equiv.txt guardado tiene además la fila de 10 ms (make
#                   equiv-ronda1, 34 minutos): aquí se repiten los otros 10
#                   casos con SUFIJO=_repeticion y se comparan fila por fila.
#   i_integrado     verif, tabla-vigilante, mutaciones y formal. Los tres
#                   largos (recursos, tb-xd y oficial, 17 minutos) se repiten
#                   solo con LARGOS=1. Sin eso se informa la comparación con
#                   la copia build/mediciones_antes/, si existe (es la que dejó
#                   la repetición hecha al cerrar la pieza).
#
# Uso: factibilidad/auditoria_hw/tools/repeticion.sh   (o make repeticion)
# Resultado en mediciones/repeticion.txt. Unos 20 minutos con 5 procesos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/repeticion
rm -rf "$O"; mkdir -p "$O/fondo" "$O/integrado"
cp -p $F/mediciones/*.txt "$O/fondo/"
cp -p $I/mediciones/*.txt "$O/integrado/"
FILTRO='Commit de partida|Demora:|Tiempo de las simulaciones|s de simulacion|^Simulador:'

comparar() {   # comparar ANTES AHORA ETIQUETA
  local n
  n=$(diff <(grep -vE "$FILTRO" "$1") <(grep -vE "$FILTRO" "$2") | grep -c '^[<>]')
  if [ "$n" = 0 ]; then echo "PASS $3: idéntico a lo guardado ($(grep -vcE "$FILTRO" "$2") líneas comparadas)"
  else echo "FAIL $3: $n líneas distintas"; diff <(grep -vE "$FILTRO" "$1") <(grep -vE "$FILTRO" "$2") | head -6 | sed 's/^/      /'; fi
}

T0=$(date +%s)
for t in programa ticks variantes estado oficial; do make -s -C $F $t > "$O/fondo/$t.out" 2>&1; echo "$t: salida $?" >> "$O/fondo/make.txt"; done
SUFIJO=_repeticion $F/tools/equiv.sh > "$O/fondo/equiv.out" 2>&1; echo "equiv: salida $?" >> "$O/fondo/make.txt"
mv $F/mediciones/equiv_repeticion.txt "$O/fondo/equiv_repeticion.txt"
OBJ_I="verif tabla-vigilante mutaciones formal"
[ "${LARGOS:-0}" = 1 ] && OBJ_I="recursos tb-xd oficial $OBJ_I"
for t in $OBJ_I; do make -s -C $I $t > "$O/integrado/$t.out" 2>&1; echo "$t: salida $?" >> "$O/integrado/make.txt"; done
T1=$(date +%s)

{
echo "Auditoría: repetición de los objetivos de las dos piezas contra sus salidas guardadas"
echo "Generado por factibilidad/auditoria_hw/tools/repeticion.sh (make repeticion). No editar a mano."
echo
versiones
echo "Se ignoran las líneas del commit de partida y de los tiempos de corrida. Demora: $((T1 - T0)) s."
echo
echo "1. $F"
sed 's/^/   make /' "$O/fondo/make.txt"
comparar "$O/fondo/tamano.txt"    $F/mediciones/tamano.txt    "make programa  (tamano.txt)"
comparar "$O/fondo/ticks.txt"     $F/mediciones/ticks.txt     "make ticks     (ticks.txt)"
comparar "$O/fondo/variantes.txt" $F/mediciones/variantes.txt "make variantes (variantes.txt)"
comparar "$O/fondo/estado.txt"    $F/mediciones/estado.txt    "make estado    (estado.txt)"
comparar "$O/fondo/oficial.txt"   $F/mediciones/oficial.txt   "make oficial   (oficial.txt)"
n=$(diff <(grep '^PASS' "$O/fondo/equiv.txt" | grep -v practica_10ms) <(grep '^PASS' "$O/fondo/equiv_repeticion.txt") | grep -c '^[<>]')
if [ "$n" = 0 ]; then echo "PASS make equiv     (equiv.txt): los $(grep -c '^PASS' "$O/fondo/equiv_repeticion.txt") casos repetidos dan las mismas filas que el archivo guardado; la fila de 10 ms no se repitió"
else echo "FAIL make equiv: $n filas distintas"; fi
echo "   La fila de 10 ms del archivo guardado: $(grep '^PASS practica_10ms' "$O/fondo/equiv.txt" | cut -c1-150)"
echo
echo "2. $I"
sed 's/^/   make /' "$O/integrado/make.txt"
for par in "verif:verif_rv32e.txt" "tabla-vigilante:tabla_vigilante.txt" "mutaciones:mutaciones.txt" "formal:formal.txt"; do
  comparar "$O/integrado/${par#*:}" "$I/mediciones/${par#*:}" "make ${par%%:*} (${par#*:})"
done
if [ "${LARGOS:-0}" = 1 ]; then
  for par in "recursos:recursos.txt" "tb-xd:tb_xd.txt" "oficial:oficial.txt"; do
    comparar "$O/integrado/${par#*:}" "$I/mediciones/${par#*:}" "make ${par%%:*} (${par#*:})"
  done
elif [ -d $I/build/mediciones_antes ]; then
  echo "   Los tres objetivos largos no se repitieron en esta corrida. Comparación de lo guardado con la copia anterior a la"
  echo "   repetición hecha al cerrar la pieza ($I/build/mediciones_antes/):"
  for a in recursos.txt tb_xd.txt oficial.txt; do
    comparar "$I/build/mediciones_antes/$a" "$I/mediciones/$a" "$a contra la copia anterior"
  done
fi
echo
} > "$O/informe.tmp"
{
cat "$O/informe.tmp"
if grep -q "^FAIL" "$O/informe.tmp"; then echo "RESULTADO: FAIL, alguna salida no se reproduce"
else echo "RESULTADO: PASS, todas las salidas repetidas son las guardadas"; fi
} | tee "$M/repeticion.txt"

grep -q "^RESULTADO: PASS" "$M/repeticion.txt"
