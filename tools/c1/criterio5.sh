#!/usr/bin/env bash
# criterio5.sh: criterio 5 de la puerta de simulación en la configuración exacta de
# R3: el barrel con emad y devk (máscara 3 de la extensión, sin mulstep) dentro del
# SoC con la tabla de 512 palabras y el vigilante.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El core de R3 es el de R1 y R2, sin cambiar una línea: lo nuevo es del SoC (la
# tabla más grande). Igual se repite la campaña sobre este SoC, sin cambiar nada de
# las pruebas (es tools/fondo/criterio5.sh con las definiciones de R3):
#
#   1. La campaña de tools/barrel/verif.sh: cada hilo contra el Espino base más la
#      especificación de la extensión, instrucción por instrucción. La puerta pide al
#      menos 5 millones de instrucciones con más de 90 % distintas.
#   2. Las mutaciones de la extensión que tocan lógica que existe con la máscara 3
#      (6 de las 9; las otras 3 son solo de mulstep y tools/fondo/no_aplican.sh ya
#      probó formalmente que con esta máscara el core mutado es el mismo: es una
#      prueba del core, que no depende del SoC, y vale la de R2).
#   3. Las 21 mutaciones del barrel sobre este hardware.
#
# Las definiciones de la tabla y del vigilante se agregan a los dos SoC de la
# comparación (el barrel y el base de referencia), porque son del SoC y no del core.
#
# sw/c1.s no usa la extensión (ni emad ni devk): se deja en el hardware para que el
# core sea byte a byte el que ya pasó las puertas de R1 y R2.
#
# Uso: [JOBS=12] tools/c1/criterio5.sh   (make c1-criterio5). Unos 40 minutos.
# Resultado en docs/mediciones/c1/criterio5_*.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BC/criterio5
mkdir -p "$O"
SOC_DEFS="-DESPINO_TABLA -DESPINO_TABLA_512 -DESPINO_VIGILANTE"
XD_DEFS_R="-DESPINO_XD_EMAD -DESPINO_XD_DEVK"
APLICAN="MUTA_XD_K MUTA_XD_SRL MUTA_XD_K4 MUTA_XD_WE MUTA_XD_HILO MUTA_XD_SUMA"
mal=0

VERIF_DEFS="$SOC_DEFS" XD=3 PUERTA=1 JOBS=${JOBS:-12} DIR_VERIF="$O/verif" SALIDA="$MC/criterio5_verificacion.txt" \
  tools/barrel/verif.sh > "$O/verif.out" 2>&1 || mal=1
tail -25 "$MC/criterio5_verificacion.txt"

VERIF_DEFS="$SOC_DEFS" XD=3 NOMBRES="$APLICAN" JOBS=${JOBS:-12} DIR_MUT="$O/mut_xd" SALIDA="$MC/criterio5_mutaciones_xd.txt" \
  tools/xd/mutaciones.sh > "$O/mut_xd.out" 2>&1 || mal=1
grep -E "^(PASS|FAIL)" "$MC/criterio5_mutaciones_xd.txt"

VERIF_DEFS="$XD_DEFS_R $SOC_DEFS" JOBS=${JOBS:-12} DIR_MUT="$O/mut_barrel" SALIDA="$MC/criterio5_mutaciones_barrel.txt" \
  tools/barrel/mutaciones.sh > "$O/mut_barrel.out" 2>&1 || mal=1
tail -3 "$MC/criterio5_mutaciones_barrel.txt"

if [ $mal = 0 ]; then echo "PASS: criterio 5 en el hardware de R3"; else echo "FAIL: criterio 5 en el hardware de R3"; fi
exit $mal
