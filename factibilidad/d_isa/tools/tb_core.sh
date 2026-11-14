#!/usr/bin/env bash
# tb_core.sh: las instrucciones nuevas ejecutadas por el core, en cada variante.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Para cada variante de integración (definiciones XD_*) y para los dos cores
# (Espino base y segmentado) genera programas al azar con tools/gen_prog.py,
# los corre en la copia del SoC con tb/tb_xd_core.sv y compara cada escritura
# al banco de registros con el modelo. Imprime una línea por variante y core.
#
# Uso, desde factibilidad/d_isa:   tools/tb_core.sh [PROGRAMAS_POR_VARIANTE] [FILTRO]
# Con FILTRO (una expresión regular) solo corre las variantes cuyo nombre calza.
set -euo pipefail
cd "$(dirname "$0")/.."

NPROG=${1:-6}
FILTRO=${2:-.}
B=build/core
mkdir -p "$B"
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
SRC="$(echo core/*.v core/espino_core/*.v rtl/*.v)"
FALLAS=0

# variante ETIQUETA "definiciones"
variante() {
  local etq=$1 defs=$2 core cdef total nuevas n resumen
  [[ "$etq" =~ $FILTRO ]] || return 0
  for core in base segmentado; do
    cdef=""; [ "$core" = segmentado ] && cdef="-DESPINO_SEGMENTADO"
    total=0; nuevas=0; ok=1; resumen=""
    for s in $(seq 1 "$NPROG"); do
      resumen=$(python3 tools/gen_prog.py "--defs=$defs" --semilla "$s" --hex "$B/$etq.$s.hex" --esperado "$B/$etq.$s.esp")
      n=${resumen%% *}
      # instrucciones de custom-0 (y productos por el periférico) del programa
      nuevas=$((nuevas + $(echo "$resumen" | tr ' ' '\n' | grep '=' | cut -d= -f2 | paste -sd+ | bc)))
      iverilog -g2012 -s tb_xd_core $cdef $defs "-DPROGRAMA=\"$B/$etq.$s.hex\"" "-DESPERADO=\"$B/$etq.$s.esp\"" \
        -DN_ESP="$n" -o "$B/$etq.$core.vvp" "$CELLS_SIM" $SRC tb/tb_xd_core.sv
      if vvp -n "$B/$etq.$core.vvp" > "$B/$etq.$core.$s.log" 2>&1 && grep -q "^PASS" "$B/$etq.$core.$s.log"; then
        total=$((total + n))
      else
        ok=0; grep -E "diferencia|FAIL|rror" "$B/$etq.$core.$s.log" | head -5
      fi
    done
    if [ "$ok" = 1 ]; then
      printf "PASS %-14s %-11s %d programas, %5d instrucciones nuevas, %6d escrituras identicas al modelo   [%s]\n" "$etq" "$core" "$NPROG" "$nuevas" "$total" "$defs"
    else
      printf "FAIL %-14s %-11s [%s]\n" "$etq" "$core" "$defs"; FALLAS=$((FALLAS + 1))
    fi
  done
}

echo "== Instrucciones nuevas dentro del core, contra ref/xd.py =="
variante ema_k5        "-DXD_EMA=0"
variante ema_k4a7      "-DXD_EMA=2"
variante ema_k0a7      "-DXD_EMA=3"
variante ema_todos     "-DXD_EMA=5"
variante emaalu_k5     "-DXD_EMA=0 -DXD_EMAALU"
variante emaalu_todos  "-DXD_EMA=5 -DXD_EMAALU"
variante emad_k5       "-DXD_EMAD=0"
variante emad_k4a7     "-DXD_EMAD=2"
variante emad_todos    "-DXD_EMAD=5"
variante devk_k5       "-DXD_DEVK=0"
variante devk_todos    "-DXD_DEVK=5"
variante media_k5      "-DXD_EMAD=0 -DXD_DEVK=0"
variante media_mul     "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU"
variante srak_k5       "-DXD_SRAK=0"
variante srak_todos    "-DXD_SRAK=5"
variante simd_min      "-DXD_SIMD=0"
variante simd_bandas   "-DXD_SIMD=28"
variante simd_todo     "-DXD_SIMD=31"
variante simd_bit      "-DXD_SIMD=32"
variante simdalu_min   "-DXD_SIMDALU=0"
variante simdalu_sat   "-DXD_SIMDALU=4"
variante simdalu_bandas "-DXD_SIMDALU=12"
variante mulstep       "-DXD_MULSTEP"
variante mulstepalu    "-DXD_MULSTEPALU"
variante divstep       "-DXD_DIVSTEP"
variante mulc8         "-DXD_MULC=8"
variante mulc16        "-DXD_MULC=16"
variante mulmmio       "-DXD_MULMMIO"
variante todo_autonomo "-DXD_EMA=5 -DXD_SRAK=5 -DXD_SIMD=31 -DXD_MULSTEP -DXD_DIVSTEP -DXD_MULC=16 -DXD_MULMMIO"
variante todo_alu      "-DXD_EMA=5 -DXD_EMAALU -DXD_SRAK=5 -DXD_SIMD=31 -DXD_MULSTEPALU -DXD_DIVSTEP -DXD_MULC=16 -DXD_MULMMIO"
variante todo_bandas   "-DXD_EMA=0 -DXD_EMAALU -DXD_SIMD=28 -DXD_MULSTEPALU"
variante alu_todo      "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DXD_SIMDALU=12"
variante alu_todo_div  "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DXD_SIMDALU=12 -DXD_DIVSTEP"

if [ "$FALLAS" != 0 ]; then echo "FAIL: $FALLAS variantes con error"; exit 1; fi
echo "PASS: todas las variantes coinciden con el modelo en los dos cores"
