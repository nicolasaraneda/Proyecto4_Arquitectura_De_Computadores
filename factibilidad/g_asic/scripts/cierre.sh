#!/usr/bin/env bash
# cierre.sh: criterios de cierre de cada corrida, con el verificador de
# nuestro Proyecto 3.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/g_asic/scripts/cierre.sh TAG [TAG ...]
# Corre asic/verificar_cierre.py del clon del Proyecto 3 (variable P3) sobre
# factibilidad/g_asic/runs/TAG, sin copiarlo: para la edición ASIC habría que
# traerlo a este repositorio. Es una segunda lectura de las métricas,
# independiente de scripts/recolectar.py. Criterios: flujo completo, DRC de
# Magic, LVS, antenas, y setup y hold (WNS >= 0 y TNS = 0) en las 9 esquinas.
# Deja la tabla de cada corrida en mediciones/TAG/cierre.md e imprime una
# línea por corrida.
set -uo pipefail
G=factibilidad/g_asic
P3=${P3:?defina P3 con la ruta de un clon del Proyecto 3}
[ -f "$P3/asic/verificar_cierre.py" ] || { echo "no está $P3/asic/verificar_cierre.py"; exit 1; }
for tag in "$@"; do
  if [ ! -f "$G/runs/$tag/final/metrics.json" ]; then
    echo "$tag: incompleta (sin final/metrics.json)"; continue
  fi
  mkdir -p "$G/mediciones/$tag"
  python3 "$P3/asic/verificar_cierre.py" "$G/runs/$tag" --md "$G/mediciones/$tag/cierre.md" > /dev/null
  falla=$(grep -E '\| NO \|$' "$G/mediciones/$tag/cierre.md" | grep -v "^|  " | sed -E 's/^\| ([^|]*) \|.*/\1/' | sed 's/ *$//' | paste -sd ';' -)
  echo "$tag: $(grep -o 'Resultado: [A-Z ]*' "$G/mediciones/$tag/cierre.md")${falla:+ (falla: $falla)}"
done
