#!/usr/bin/env bash
# contingencia.sh: juegos de bitstreams preconstruidos para un cambio de
# comisión anunciado el día de la competencia (docs/arbol_decision.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# tools/retune.py deja los umbrales actuales con comisión de 0 a 10 y con
# cualquier caja de 1 000 a 100 000. Con comisión de 20 o más elige otros. Este
# script construye, con icebram sobre los moldes y simulando cada .asc por los
# pines, los juegos que aparecen en la tabla del árbol de decisión, y los deja
# en bitstreams/contingencia/<umbrales>/ con su SHA256SUMS. Así el 1/12 no hay
# que esperar los 40 minutos de la simulación.
#
# Uso: tools/p8/contingencia.sh   (o make contingencia). Unos 45 minutos.
set -euo pipefail
cd "$(dirname "$0")/../.."
O=bitstreams/contingencia
mkdir -p "$O"
# comisión caja -> carpeta (los umbrales que elige retune; se comprueba abajo)
JUEGOS="20:10000:e7_s4 50:10000:e16_s4 50:100000:e16_s3"
make -s build/gemelo fondo-hex > /dev/null
pids=""
for j in $JUEGOS; do
  IFS=: read -r c k n <<< "$j"
  python3 tools/retune.py --comision "$c" --caja "$k" --simular > "build/contingencia_$n.log" 2>&1 &
  pids="$pids $!"
done
fallas=0
for p in $pids; do wait "$p" || fallas=$((fallas + 1)); done
for j in $JUEGOS; do
  IFS=: read -r c k n <<< "$j"
  d=build/retune/c${c}_k${k}_n2000
  e=$(echo "$n" | sed 's/e\([0-9]*\)_s\([0-9]*\)/entra \1, sale \2/')
  grep -q "Umbrales elegidos: $e" "$d/RESUMEN.txt" || { echo "FAIL: retune ya no elige $e con comision $c y caja $k"; fallas=$((fallas + 1)); continue; }
  tail -n 1 "$d/RESUMEN.txt" | grep -q PASS || { echo "FAIL: $d no paso"; fallas=$((fallas + 1)); continue; }
  rm -rf "${O:?}/$n"; mkdir -p "$O/$n"
  cp "$d"/r0.bin "$d"/r1.bin "$d"/r2_multi.bin "$d"/tabla.hex "$d"/trade.hex "$d"/RESUMEN.txt "$O/$n/"
  ( cd "$O/$n" && sha256sum r0.bin r1.bin r2_multi.bin tabla.hex trade.hex > SHA256SUMS )
  echo "PASS $n: comision $c, caja $k, $(grep -c '^  PASS' "$d/RESUMEN.txt") comprobaciones (gemelo y .asc por los pines)"
done
[ "$fallas" -eq 0 ] && echo "PASS: juegos de contingencia en $O"
exit "$fallas"
