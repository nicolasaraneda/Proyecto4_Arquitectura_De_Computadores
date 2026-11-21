#!/usr/bin/env bash
# puerta_a.sh: puerta a de R3. Con la política apagada (la palabra POLITICA de la
# tabla en 0, el valor reservado) R3 da las mismas órdenes que la banda 40 de R2.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El programa es el mismo sw/c1.s: solo cambia una palabra de la tabla
# (tools/c1/generar.py --apagada). Se compara contra tres cosas:
#   - ref/c1/c1.py con esa tabla (bytes y estado: los hilos 1 a 3 siguen calculando,
#     pero el hilo 0 no los espera ni los usa);
#   - la banda 40 de R2 en Python (ref/fondo.py);
#   - el programa de R2 de verdad (sw/fondo.s con sw/fondo_tabla.hex) corrido en el
#     hardware de R2 con su testbench (tb/fondo/tb_fondo.sv): el archivo de bytes
#     que lee la maestra tiene que ser idéntico, byte a byte, al de R3.
#
#   1. RTL: Tesla, AMD y Meta completas a 0,1 ms y a 1 ms, y 40 ventanas reales a
#      0,1 ms. R3 con la tabla apagada y R2, lado a lado.
#   2. Gemelo: las 203 series de la puerta b a los tres períodos: R3 apagado contra
#      ref/c1/c1.py, contra ref/fondo.py y contra el programa de R2 en el gemelo.
#
# Uso: [JOBS=12] tools/c1/puerta_a.sh   (make c1-puerta-a)
# Resultado en docs/mediciones/c1/puerta_a.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BC/puerta_a
NV=${VENTANAS:-200}
NV_RTL=${VENTANAS_RTL:-40}
SALIDA=${SALIDA:-$MC/puerta_a.txt}
rm -rf "$O"; mkdir -p "$O/apagada"
ensamblar_c1 || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1
compilar_gemelo || exit 1
reales || { echo "FAIL: no se pudieron armar Tesla y AMD (falta P4_DATOS)"; exit 1; }
$PYTHON $TC/generar.py --apagada -o "$O/apagada" > /dev/null || { echo "FAIL: no se pudo generar la tabla apagada"; exit 1; }
TAB=$O/apagada/c1_tabla.hex
$PYTHON $TC/ventanas.py "$O/ventanas" --n "$NV" > "$O/ventanas.txt" || { echo "FAIL: no se pudieron armar las ventanas"; exit 1; }
head -"$NV_RTL" "$O/ventanas.txt" > "$O/ventanas_rtl.txt"

# lista de corridas: etiqueta serie período
{
  for s in tesla amd; do for per in 100000 1000000; do echo "${s}_$per $BC/series/$s.csv $per"; done; done
  for per in 100000 1000000; do echo "meta_$per data/practica_meta.csv $per"; done
  while read -r v; do echo "v_$(basename "$v" .csv) $v 100000"; done < "$O/ventanas_rtl.txt"
} > "$O/corridas.txt"

# R3 con la política apagada
while read -r e s per; do
  echo "caso $O/r3_$e --serie $s --nticks 20000 --periodo-ns $per --tabla $TAB"
done < "$O/corridas.txt" | en_paralelo

# R2 con su programa y su testbench (tools/fondo, sin tocar)
(
  export HW=r2
  source tools/fondo/comun.sh
  ensamblar_fondo && compilar_sim || { echo "FAIL: no se pudo preparar R2" > "$RAIZ/$O/r2_error.txt"; exit 1; }
  while read -r e s per; do
    echo "caso $O/r2_$e sw/fondo.s $s 20000 $per 4000"
  done < "$O/corridas.txt" | en_paralelo
)

{ echo data/practica_meta.csv; echo "$BC/series/tesla.csv"; echo "$BC/series/amd.csv"; cat "$O/ventanas.txt"; } > "$O/lista.txt"
$PYTHON $TC/gemelo_lote.py "$O/lista.txt" --tabla "$TAB" --banda40 --jobs "${JOBS:-6}" --salida "$O/gemelo.txt" \
  --titulo "x" > /dev/null

{
cabecera "Puerta a de R3: con la politica apagada, las ordenes de la banda 40 de R2" tools/c1/puerta_a.sh "make c1-puerta-a"
if cmp -s "$O/apagada/c1.s" sw/c1.s; then echo "PASS: el programa con la politica apagada es sw/c1.s sin cambios"; else echo "FAIL: el programa cambia"; fi
d=$(diff "$TAB" sw/c1_tabla.hex | grep -c '^<')
linea=$(diff "$TAB" sw/c1_tabla.hex | sed -n '1p')
if [ "$d" = 1 ] && [ "$linea" = "5c5" ]; then echo "PASS: la tabla cambia en una sola palabra, la 4 (POLITICA): $(sed -n 5p sw/c1_tabla.hex) pasa a $(sed -n 5p "$TAB")"
else echo "FAIL: la tabla apagada difiere en $d palabras ($linea)"; fi
[ -f "$O/r2_error.txt" ] && cat "$O/r2_error.txt"
echo
echo "1. RTL: R3 con la politica apagada (tb/c1/tb_c1.sv) y R2 (sw/fondo.s, tb/fondo/tb_fondo.sv), las mismas series"
n=0; p=0; tk=0; peor=0
while read -r e s per; do
  n=$((n + 1))
  r3=$O/r3_$e; r2=$O/r2_$e
  ok=1
  grep -q "^PASS" "$r3/resultado.txt" 2>/dev/null || ok=0
  grep -q "^PASS" "$r2/resultado.txt" 2>/dev/null || ok=0
  cmp -s "$r3/salida.csv" "$r2/salida.csv" || ok=0
  c=$(sed -n 's/.*peor caso \([0-9]*\) de.*/\1/p' "$r3/resultado.txt"); [ -n "$c" ] && [ "$c" -gt "$peor" ] && peor=$c
  if [ $ok = 1 ]; then
    p=$((p + 1)); tk=$((tk + $(($(wc -l < "$r3/salida.csv") - 1))))
    case $e in v_*) ;; *) echo "PASS $e: los $(($(wc -l < "$r3/salida.csv") - 1)) bytes de R3 apagado son los de R2 (archivos identicos), y cada uno igual a su referencia. $(sed -n 's/.*\(patrimonio [0-9]*, [0-9]* órdenes\).*/\1/p' "$r3/resultado.txt")" ;; esac
  else
    echo "FAIL $e: R3 [$(head -c 300 "$r3/resultado.txt" 2>/dev/null)] R2 [$(head -c 300 "$r2/resultado.txt" 2>/dev/null)] archivos $(cmp -s "$r3/salida.csv" "$r2/salida.csv" && echo iguales || echo distintos)"
  fi
done < "$O/corridas.txt"
if [ "$p" = "$n" ]; then echo "PASS: $p de $n corridas (6 de series completas y $NV_RTL ventanas), $tk ticks: R3 con la politica apagada escribe los mismos bytes que R2. Peor caso de R3 apagado: $peor ciclos"
else echo "FAIL: pasan $p de $n corridas"; fi
echo
echo "2. Gemelo, 203 series a los tres periodos: R3 apagado contra ref/c1/c1.py, ref/fondo.py y el programa de R2"
sed -n '3,$p' "$O/gemelo.txt"
} | tee "$SALIDA"
cierre "$SALIDA"
