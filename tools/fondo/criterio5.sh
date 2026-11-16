#!/usr/bin/env bash
# criterio5.sh: criterio 5 de la puerta de simulación en la configuración
# exacta que compite: el barrel con emad y devk (máscara 3 de la extensión,
# sin mulstep) dentro del SoC de R1 (con la tabla de parámetros) o de R2 (con
# la tabla y el vigilante).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Repite, sin cambiar nada de las pruebas, lo que los paquetes P1 y P2
# corrieron con otras configuraciones:
#
#   1. La campaña de tools/barrel/verif.sh: cada hilo contra el Espino base más
#      la especificación de la extensión, instrucción por instrucción. La puerta
#      pide al menos 5 millones de instrucciones con más de 90 % distintas. Los
#      programas se generan con la máscara 3: usan emad y devk, y las palabras
#      de mulstep aparecen como custom-0 sin efecto, que es lo que este hardware
#      tiene que hacer con ellas.
#   2. Las mutaciones de la extensión (tools/xd/mutaciones.sh) que tocan lógica
#      que existe con la máscara 3: 6 de las 9.
#   3. Las otras 3 (MUTA_XD_F7MUL, MUTA_XD_BCERO y MUTA_XD_ANULA) cambian solo
#      lógica de mulstep. Con la máscara 3 esa lógica no está, así que no hay
#      nada que detectar: tools/fondo/no_aplican.sh prueba formalmente que el
#      core mutado es equivalente al core sin mutar.
#   4. Las 21 mutaciones del barrel (tools/barrel/mutaciones.sh) sobre este
#      hardware.
#
# Las definiciones de la tabla y del vigilante se agregan a los dos SoC de la
# comparación (el barrel y el base de referencia), porque son del SoC y no del
# core.
#
# Uso: HW=r1 tools/fondo/criterio5.sh   (o make fondo-criterio5 HW=r1)
# Resultado en docs/mediciones/fondo/HW/criterio5_*.txt. Unos 40 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BF/criterio5
mkdir -p "$O"
case $HW in
  r1) SOC_DEFS="-DESPINO_TABLA" ;;
  r2) SOC_DEFS="-DESPINO_TABLA -DESPINO_VIGILANTE" ;;
esac
XD_DEFS_R="-DESPINO_XD_EMAD -DESPINO_XD_DEVK"
APLICAN="MUTA_XD_K MUTA_XD_SRL MUTA_XD_K4 MUTA_XD_WE MUTA_XD_HILO MUTA_XD_SUMA"
mal=0

# 1. Campaña
VERIF_DEFS="$SOC_DEFS" XD=3 PUERTA=1 JOBS=${JOBS:-12} DIR_VERIF="$O/verif" SALIDA="$MF/criterio5_verificacion.txt" \
  tools/barrel/verif.sh > "$O/verif.out" 2>&1 || mal=1
tail -25 "$MF/criterio5_verificacion.txt"

# 2. Mutaciones de la extensión que aplican
VERIF_DEFS="$SOC_DEFS" XD=3 NOMBRES="$APLICAN" JOBS=${JOBS:-12} DIR_MUT="$O/mut_xd" SALIDA="$MF/criterio5_mutaciones_xd.txt" \
  tools/xd/mutaciones.sh > "$O/mut_xd.out" 2>&1 || mal=1
grep -E "^(PASS|FAIL)" "$MF/criterio5_mutaciones_xd.txt"

# 3. Las que no aplican: prueba formal de que el core no cambia
$TF/no_aplican.sh > "$O/no_aplican.out" 2>&1 || mal=1
grep -E "^(PASS|FAIL)" "$MF/criterio5_no_aplican.txt"

# 4. Mutaciones del barrel
VERIF_DEFS="$XD_DEFS_R $SOC_DEFS" JOBS=${JOBS:-12} DIR_MUT="$O/mut_barrel" SALIDA="$MF/criterio5_mutaciones_barrel.txt" \
  tools/barrel/mutaciones.sh > "$O/mut_barrel.out" 2>&1 || mal=1
tail -3 "$MF/criterio5_mutaciones_barrel.txt"

exit $mal
