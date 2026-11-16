#!/usr/bin/env bash
# core_sin_cambios.sh: prueba formal de que la extensión no cambia las instrucciones de RV32E.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Compara la etapa ID del repositorio (rtl/espino_core: decodificador, ALU y
# multiplexores) con la de la copia que lleva la extensión (core/espino_core),
# con los pases equiv_* de Yosys. Es el método de formal/base_sin_cambios del
# repositorio: empareja registros y salidas por nombre y exige que todos los
# puntos de comparación queden probados.
#
# Dos tipos de caso:
#   - Sin definiciones XD_*: la copia tiene que ser el core original.
#   - Con la extensión encendida: en los dos lados una instrucción de custom-0
#     se reemplaza por un nop antes de entrar a la etapa (formal/envoltorio_id.v).
#     Lo que se prueba es que ninguna otra instrucción cambia.
# Y un control negativo: con la extensión encendida y sin ese reemplazo la
# prueba tiene que fallar.
#
# Uso, desde factibilidad/d_isa:
#   tools/core_sin_cambios.sh > mediciones/core_sin_cambios.txt
set -uo pipefail
cd "$(dirname "$0")/.."
B=build/sin_cambios
mkdir -p "$B"
ORO="../../rtl/espino_core/espino_id_stage.v ../../rtl/espino_core/espino_decoder.v ../../rtl/espino_core/espino_alu.v"
COPIA="core/espino_core/espino_id_stage.v core/espino_core/espino_decoder.v core/espino_core/espino_alu.v \
rtl/xd_alu.v rtl/xd_opa.v rtl/xd_unit.v rtl/xd_ema.v rtl/xd_srak.v rtl/xd_simd8.v rtl/xd_mulstep.v rtl/xd_divstep.v rtl/xd_mulc.v"
W=formal/envoltorio_id.v
FALLAS=0

# probar ETIQUETA PIPE PCW SANEAR "definiciones" ESPERADO "descripción"
# ESPERADO: pasa (tiene que probarse), falla (control negativo) o informa (se informa lo que salga)
probar() {
  local etq=$1 pipe=$2 pcw=$3 san=$4 defs=$5 esperado=$6 desc=$7
  local d="-DPIPE=$pipe -DPCW=$pcw -DSANEAR=$san" rc puntos sin res donde
  timeout 600 yosys -q -l "$B/$etq.log" -p "
    read_verilog $d $ORO $W
    hierarchy -top w_id; proc; flatten; async2sync; opt_clean; rename w_id gold; design -stash gold
    read_verilog $d $defs $COPIA $W
    hierarchy -top w_id; proc; flatten; async2sync; opt_clean; rename w_id gate; design -stash gate
    design -copy-from gold -as gold gold
    design -copy-from gate -as gate gate
    equiv_make gold gate equiv
    hierarchy -top equiv
    equiv_simple
    equiv_induct
    equiv_status -assert
  " > "$B/$etq.out" 2>&1
  rc=$?
  puntos=$(grep -E 'Found [0-9]+ \$equiv cells' "$B/$etq.log" | tail -1 | sed -E 's/.*Found ([0-9]+) .*/\1/')
  sin=$(grep -c "Unproven" "$B/$etq.log")
  # señales en las que quedaron los puntos sin probar
  donde=$(grep "Unproven" "$B/$etq.log" | sed -E 's/.*find_same_wires\$[0-9]+: //' | awk '{print $1}' \
          | sed -E 's/\[[0-9]+\]//; s/^\\//; s/_gold$//' | sort -u | tr '\n' ' ')
  if [ $rc = 0 ]; then res="PROBADO"; else res="NO PROBADO"; fi
  case "$esperado" in
    pasa)  [ $rc = 0 ] || FALLAS=$((FALLAS + 1)) ;;
    falla) if [ $rc = 0 ]; then res="NO DETECTADO"; FALLAS=$((FALLAS + 1)); else res="FALLA DETECTADA"; fi ;;
  esac
  printf "%-22s %-15s %6s %6s  %s\n" "$etq" "$res" "${puntos:-?}" "$sin" "$desc"
  [ -n "$donde" ] && [ "$esperado" != falla ] && printf "%-22s   sin probar en: %s\n" "" "$donde"
  return 0
}

echo "La extensión no cambia las instrucciones de RV32E: etapa ID del repositorio contra la de la copia"
echo "Generado por factibilidad/d_isa/tools/core_sin_cambios.sh (make sin-cambios). No editar a mano."
echo
echo "Yosys $(yosys -V | cut -d' ' -f2), pases equiv_make, equiv_simple, equiv_induct y equiv_status -assert."
echo "'puntos' son los puntos de comparación (bits de registros, cables con el mismo nombre y salidas) y"
echo "'sin' los que no quedaron probados."
echo
printf "%-22s %-15s %6s %6s  %s\n" caso resultado puntos sin "qué compara"
echo
echo "-- Espino base (Pipeline = 0, contador de programa de 32 bits)"
probar base_sin        0 32 0 "" pasa "la copia sin ninguna definición XD_*: es el core original"
probar base_emad       0 32 1 "-DXD_EMAD=0" pasa "con emad, todas las instrucciones menos las de custom-0"
probar base_media_mul  0 32 1 "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU" pasa "con emad, devk y mulstep en la ALU (subconjunto recomendado)"
probar base_bandas     0 32 1 "-DXD_EMAD=0 -DXD_SIMD=28" pasa "con emad y los carriles de bandas en unidad aparte"
probar base_todo       0 32 1 "-DXD_EMA=5 -DXD_EMAALU -DXD_EMAD=5 -DXD_DEVK=5 -DXD_SRAK=5 -DXD_SIMD=31 -DXD_MULSTEPALU -DXD_DIVSTEP -DXD_MULC=16" pasa "con todas las instrucciones y todos los k (carriles en unidad aparte)"
probar base_alu_todo   0 32 1 "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DXD_SIMDALU=12" informa "con los carriles en el sumador de la ALU (xd_alu en vez de espino_alu)"
probar control_negativo 0 32 0 "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU" falla "control: extensión encendida sin reemplazar custom-0, tiene que fallar"
echo
echo "-- Espino segmentado (Pipeline = 1, contador de programa de 11 bits)"
probar seg_sin         1 11 0 "" informa "la copia sin ninguna definición XD_*"
probar seg_media_mul   1 11 1 "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU" informa "con emad, devk y mulstep en la ALU"
echo
echo "Lectura:"
echo "- Base: sin definiciones la copia es el core original, y con la extensión encendida ninguna instrucción"
echo "  de RV32E cambia, salvo en el caso de los carriles en la ALU. Ahí lo único que difiere es el resultado"
echo "  de la ALU durante un branch (xd_alu deja la resta donde espino_alu deja la suma), que sale por"
echo "  lsu_addr_o sin petición de acceso. El encabezado de rtl/xd_alu.v lo describe. Que ese valor no se use"
echo "  no quedó probado formalmente: lo respaldan las simulaciones de make tb-core con XD_SIMDALU."
echo "- Segmentado: este método no alcanza. La copia tiene un registro que el original no tiene (is_xd_q, la"
echo "  marca de instrucción nueva) y los registros de decodificación pueden partir en un valor que solo"
echo "  custom-0 produce. La inducción parte de un estado cualquiera y no sabe que esos estados no se"
echo "  alcanzan después del reset. Para el segmentado la evidencia es por simulación (make tb-core,"
echo "  make tb-core-recomendado y make medir-ticks)."
if [ "$FALLAS" != 0 ]; then echo "FAIL: $FALLAS casos no dieron lo esperado"; exit 1; fi
echo "PASS: los casos del Espino base que debían probarse quedaron probados y el control negativo falla"
