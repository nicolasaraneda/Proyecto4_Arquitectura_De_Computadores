#!/usr/bin/env bash
# series.sh: el fondo en un chip contra ref/fondo.py en un lote de series
# sintéticas (criterio 2 de la puerta: al menos 1 000 series).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Genera POR_FAMILIA series de cada una de las 15 familias de ref/series.py
# (14 sintéticas y el remuestreo de la práctica), de NTICKS ticks, y corre cada
# una por el RTL con tb/fondo/tb_fondo.sv al período de la ronda 3. En cada
# serie compara los bytes, el estado interno en cada decisión, la telemetría y
# el protocolo. El gemelo digital todavía no modela el barrel (paquete P4), así
# que esto corre con Verilator.
#
# Uso: tools/fondo/series.sh   (o make fondo-series)
# Variables: POR_FAMILIA (70, o sea 1 050 series), NTICKS (2000), SEMILLA (1), JOBS.
# Resultado en docs/mediciones/fondo/HW/series.txt (HW es r1 o r2). Unos 10 minutos con 6 procesos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BF/lote
POR=${POR_FAMILIA:-70}
NT=${NTICKS:-2000}
SEM=${SEMILLA:-1}
SALIDA=${SALIDA:-$MF/series.txt}
rm -rf "$O"; mkdir -p "$O/series"
ensamblar_fondo || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1

$PYTHON $TF/lote.py "$O/series" "$POR" "$NT" "$SEM" > "$O/lista.txt"
while read -r s; do
  e=$(basename "$s" .csv)
  echo "caso $O/$e sw/fondo.s $s $NT 100000 4000"
done < "$O/lista.txt" | en_paralelo

{
cabecera "El fondo en un chip contra su referencia en un lote de series sinteticas" tools/fondo/series.sh "make fondo-series"
echo "$POR series por familia, $NT ticks cada una, semilla $SEM, periodo de 0,1 ms."
echo
printf "%-20s %7s %7s %12s %12s %10s\n" familia series pasan "ticks" "peor caso" "por plazo"
total=0; pasan=0; ticks=0
for fam in $(sed 's|.*/||; s|_[0-9]*\.csv$||' "$O/lista.txt" | sort -u); do
  n=0; p=0; tk=0; peor=0; plazo=0
  for r in "$O/${fam}"_[0-9][0-9][0-9]/resultado.txt; do
    n=$((n + 1))
    if grep -q "^PASS" "$r"; then
      p=$((p + 1))
      tk=$((tk + $(sed -n 's/^PASS [^:]*: \([0-9]*\) bytes.*/\1/p' "$r")))
      c=$(sed -n 's/.*peor caso \([0-9]*\) de.*/\1/p' "$r"); [ "$c" -gt "$peor" ] && peor=$c
      plazo=$((plazo + $(sed -n 's/.* \([0-9]*\) ticks por plazo.*/\1/p' "$r")))
    fi
  done
  printf "%-20s %7d %7d %12d %12d %10d\n" "$fam" "$n" "$p" "$tk" "$peor" "$plazo"
  total=$((total + n)); pasan=$((pasan + p)); ticks=$((ticks + tk))
done
echo
grep -h "^FAIL" "$O"/*/resultado.txt | head -20
if [ "$pasan" = "$total" ] && [ "$total" -gt 0 ]; then
  echo "PASS: $pasan de $total series identicas a la referencia (bytes, estado, telemetria y protocolo), $ticks ticks"
else
  echo "FAIL: pasan $pasan de $total series"
fi
} | tee "$SALIDA"
cierre "$SALIDA"
