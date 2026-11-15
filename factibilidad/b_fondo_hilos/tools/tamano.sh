#!/usr/bin/env bash
# tamano.sh: ensambla sw/fondo.s y cuenta sus palabras por bloque.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: factibilidad/b_fondo_hilos/tools/tamano.sh   (o make programa)
# Resultado en mediciones/tamano.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

armar base || exit 1
{
echo "Tamano de sw/fondo.s en la memoria del SoC (512 palabras de 32 bits)"
echo "Generado por factibilidad/b_fondo_hilos/tools/tamano.sh (make programa). No editar a mano."
echo
$PYTHON $F/tools/simbolos.py $F/sw/fondo.s --tamano
echo
echo "Imagen: $B/prog/base/fondo.hex, $(wc -l < "$B/prog/base/fondo.hex") palabras, sha256 $(sha256sum "$B/prog/base/fondo.hex" | cut -c1-16)..."
echo "Instrucciones por tipo (palabras de programa):"
$PYTHON - "$B/prog/base/fondo.hex" <<'PYEOF'
import sys
pal = [int(x, 16) for x in open(sys.argv[1]).read().split()]
codigo = pal[:0x7A0 // 4]
ultimo = max(i for i, w in enumerate(codigo) if w) + 1
nombres = {0x33: "ALU registro-registro", 0x13: "ALU con inmediato", 0x03: "load", 0x23: "store",
           0x63: "salto condicional", 0x6F: "jal", 0x67: "jalr", 0x37: "lui", 0x17: "auipc"}
cuenta = {}
for w in codigo[:ultimo]:
    n = nombres.get(w & 0x7F, "otro")
    cuenta[n] = cuenta.get(n, 0) + 1
for n, c in sorted(cuenta.items(), key=lambda kv: -kv[1]):
    print(f"  {n:<24} {c:>4}")
print(f"  {'total':<24} {ultimo:>4}")
PYEOF
} | tee "$M/tamano.txt"

! grep -q "^FAIL" "$M/tamano.txt"
