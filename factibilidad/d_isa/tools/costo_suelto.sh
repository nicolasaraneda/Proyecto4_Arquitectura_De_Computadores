#!/usr/bin/env bash
# costo_suelto.sh: LUT4 de cada módulo de la extensión, sintetizado solo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Sintetiza cada módulo de rtl/ por separado con synth_ice40, en cada
# configuración de sus parámetros, y cuenta SB_LUT4, SB_CARRY y flip-flops.
# Es el costo del módulo sin compartir nada con el core: sirve para comparar
# opciones entre sí. El costo real de integrarlo (que puede ser menor, si
# comparte el sumador de la ALU, o mayor, por el multiplexor de escritura)
# lo mide tools/costo_integrado.sh.
#
# Uso, desde factibilidad/d_isa:
#   tools/costo_suelto.sh > mediciones/costo_suelto.txt
set -euo pipefail
cd "$(dirname "$0")/.."
B=build/suelto
mkdir -p "$B"

# sintetizar ETIQUETA TOP "PARAM=VALOR ..." fuentes...   -> "LUT4 CARRY DFF"
sintetizar() {
  local etq=$1 top=$2 params=$3 chp=""; shift 3
  for p in $params; do chp="$chp chparam -set ${p%%=*} ${p##*=} $top;"; done
  yosys -q -l "$B/$etq.log" -p "read_verilog $*; $chp synth_ice40 -top $top; tee -o $B/$etq.stat stat" > /dev/null
  local lut carry dff
  lut=$(grep -E '^ +[0-9]+ +SB_LUT4' "$B/$etq.stat" | tail -1 | awk '{print $1}')
  carry=$(grep -E '^ +[0-9]+ +SB_CARRY' "$B/$etq.stat" | tail -1 | awk '{print $1}')
  dff=$(grep -E '^ +[0-9]+ +SB_DFF' "$B/$etq.stat" | awk '{s += $1} END {print s + 0}')
  echo "${lut:-0} ${carry:-0} ${dff:-0}"
}
fila() {   # fila "módulo y configuración" ETIQUETA TOP "PARAMS" "qué es" fuentes...
  local nombre=$1 etq=$2 top=$3 params=$4 desc=$5; shift 5
  read -r lut carry dff <<< "$(sintetizar "$etq" "$top" "$params" "$@")"
  printf "%-34s %5s %6s %4s  %s\n" "$nombre" "$lut" "$carry" "$dff" "$desc"
}

echo "Costo de cada módulo de la extensión de la ISA, sintetizado solo"
echo "Generado por factibilidad/d_isa/tools/costo_suelto.sh (make costo-suelto). No editar a mano."
echo
echo "Herramienta: $(yosys -V | cut -d' ' -f1-2), synth_ice40. Módulo suelto: sus entradas y salidas son puertos,"
echo "así que no comparte nada con el core. En el iCE40 cada celda lógica tiene una LUT4, un acarreo y un flip-flop:"
echo "las celdas que ocupa un módulo combinacional son aproximadamente sus LUT4."
echo
printf "%-34s %5s %6s %4s  %s\n" "módulo y configuración" LUT4 CARRY DFF "qué es"

echo; echo "-- Referencias"
fila "espino_alu"                 espino_alu espino_alu "" "la ALU del core (sin desplazamientos)" core/espino_core/espino_alu.v
fila "xd_srak KB=5"               srak_5 xd_srak "KB=5" "desplazador aritmético a la derecha completo, 32 bits" rtl/xd_srak.v

echo; echo "-- Paso de media exponencial autónomo: xd_ema (restador, desplazamiento y sumador)"
fila "xd_ema KB=0 (k = 5)"        ema_0 xd_ema "KB=0" "un solo k cableado" rtl/xd_ema.v
fila "xd_ema KB=2 (k de 4 a 7)"   ema_2 xd_ema "KB=2" "cuatro valores de k" rtl/xd_ema.v
fila "xd_ema KB=3 (k de 0 a 7)"   ema_3 xd_ema "KB=3" "ocho valores de k" rtl/xd_ema.v
fila "xd_ema KB=5 (k de 0 a 31)"  ema_5 xd_ema "KB=5" "todos los k" rtl/xd_ema.v

echo; echo "-- Desplazamiento suelto: xd_srak"
fila "xd_srak KB=0 (k = 5)"       srak_0 xd_srak "KB=0" "solo cables" rtl/xd_srak.v
fila "xd_srak KB=2 (k de 4 a 7)"  srak_2 xd_srak "KB=2" "" rtl/xd_srak.v
fila "xd_srak KB=3 (k de 0 a 7)"  srak_3 xd_srak "KB=3" "" rtl/xd_srak.v

echo; echo "-- Operando A desplazado para el sumador de la ALU: xd_opa (la suma la hace la ALU)"
fila "xd_opa emad k = 5"          opa_e0 xd_opa "EMAD_KB=0" "solo cables" rtl/xd_opa.v
fila "xd_opa devk k = 5"          opa_d0 xd_opa "DEVK_KB=0" "solo cables" rtl/xd_opa.v
fila "xd_opa mulstep"             opa_m xd_opa "MULSTEP=1" "solo cables y el bit que anula B" rtl/xd_opa.v
fila "xd_opa emad + devk, k = 5"  opa_ed0 xd_opa "EMAD_KB=0 DEVK_KB=0" "multiplexor de 2 entradas" rtl/xd_opa.v
fila "xd_opa emad + devk + mulstep" opa_edm xd_opa "EMAD_KB=0 DEVK_KB=0 MULSTEP=1" "multiplexor de 3 entradas" rtl/xd_opa.v
fila "xd_opa lo anterior + pbcast8" opa_edmb xd_opa "EMAD_KB=0 DEVK_KB=0 MULSTEP=1 BCAST=1" "multiplexor de 4 entradas" rtl/xd_opa.v
fila "xd_opa emad + devk, k de 4 a 7" opa_ed2 xd_opa "EMAD_KB=2 DEVK_KB=2" "" rtl/xd_opa.v
fila "xd_opa emad + devk, k de 0 a 31" opa_ed5 xd_opa "EMAD_KB=5 DEVK_KB=5" "dos desplazadores completos" rtl/xd_opa.v

echo; echo "-- Carriles de 4 x 8 bits, unidad aparte: xd_simd8"
fila "xd_simd8 mínimo"            simd_0 xd_simd8 "CON_SIGNO=0 MINMAX=0 SATURA=0 BCAST=0 MOVMSK=0 CMP_BIT=0" "padd8, psub8, pcmpltu8 (máscara por carril)" rtl/xd_simd8.v
fila "xd_simd8 comparación de 1 bit" simd_32 xd_simd8 "CON_SIGNO=0 MINMAX=0 SATURA=0 BCAST=0 MOVMSK=0 CMP_BIT=1" "lo mismo, un bit por carril" rtl/xd_simd8.v
fila "xd_simd8 + pcmplt8"         simd_1 xd_simd8 "CON_SIGNO=1 MINMAX=0 SATURA=0 BCAST=0 MOVMSK=0 CMP_BIT=0" "comparación con signo" rtl/xd_simd8.v
fila "xd_simd8 + pminu8, pmaxu8"  simd_2 xd_simd8 "CON_SIGNO=0 MINMAX=1 SATURA=0 BCAST=0 MOVMSK=0 CMP_BIT=0" "mínimo y máximo" rtl/xd_simd8.v
fila "xd_simd8 + paddus8, psubus8" simd_4 xd_simd8 "CON_SIGNO=0 MINMAX=0 SATURA=1 BCAST=0 MOVMSK=0 CMP_BIT=0" "saturadas" rtl/xd_simd8.v
fila "xd_simd8 + pbcast8"         simd_8 xd_simd8 "CON_SIGNO=0 MINMAX=0 SATURA=0 BCAST=1 MOVMSK=0 CMP_BIT=0" "" rtl/xd_simd8.v
fila "xd_simd8 + pmovmsk8"        simd_16 xd_simd8 "CON_SIGNO=0 MINMAX=0 SATURA=0 BCAST=0 MOVMSK=1 CMP_BIT=0" "" rtl/xd_simd8.v
fila "xd_simd8 kernel de bandas"  simd_28 xd_simd8 "CON_SIGNO=0 MINMAX=0 SATURA=1 BCAST=1 MOVMSK=1 CMP_BIT=0" "saturadas, pbcast8 y pmovmsk8" rtl/xd_simd8.v
fila "xd_simd8 las diez operaciones" simd_31 xd_simd8 "CON_SIGNO=1 MINMAX=1 SATURA=1 BCAST=1 MOVMSK=1 CMP_BIT=0" "" rtl/xd_simd8.v

echo; echo "-- Carriles en el sumador de la ALU: xd_alu (reemplaza a espino_alu)"
fila "xd_alu"                     xd_alu xd_alu "" "la ALU completa con padd8, psub8, pcmpltu8, paddus8 y psubus8" rtl/xd_alu.v

echo; echo "-- Producto y cociente"
fila "xd_mulstep"                 mulstep xd_mulstep "" "un paso de multiplicación (sumador propio)" rtl/xd_mulstep.v
fila "xd_divstep"                 divstep xd_divstep "" "un paso de división (restador propio de 26 bits)" rtl/xd_divstep.v
fila "xd_mulc AW=8"               mulc_8 xd_mulc "AW=8" "producto combinacional de 8 x 8" rtl/xd_mulc.v
fila "xd_mulc AW=16"              mulc_16 xd_mulc "AW=16" "producto combinacional de 16 x 8" rtl/xd_mulc.v
fila "xd_mulc AW=24"              mulc_24 xd_mulc "AW=24" "producto combinacional de 24 x 8" rtl/xd_mulc.v
fila "xd_mul_mmio"                mmio xd_mul_mmio "" "periférico serial de 24 x 8 (registro, contador y lectura)" rtl/xd_mul_mmio.v rtl/xd_mulstep.v

echo; echo "-- Unidad completa"
fila "xd_unit, todo con todos los k" unit_todo xd_unit "EMA_KB=5 SIMD=31 MULSTEP=1 DIVSTEP=1 MULC_AW=16 SRAK_KB=5" "ema, carriles, mulstep, divstep, mulc y srak" rtl/xd_unit.v rtl/xd_ema.v rtl/xd_srak.v rtl/xd_simd8.v rtl/xd_mulstep.v rtl/xd_divstep.v rtl/xd_mulc.v
fila "xd_unit, kernel de bandas k = 5" unit_bandas xd_unit "EMA_KB=0 SIMD=28 MULSTEP=1" "ema, carriles de bandas y mulstep" rtl/xd_unit.v rtl/xd_ema.v rtl/xd_srak.v rtl/xd_simd8.v rtl/xd_mulstep.v rtl/xd_divstep.v rtl/xd_mulc.v
echo
echo "La diferencia entre xd_alu y espino_alu es el costo de los carriles cuando comparten el sumador."
