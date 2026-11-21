#!/usr/bin/env bash
# puerta.sh: las puertas de R3 (C1 sobre el barrel con vigilante y la tabla de 512
# palabras), en orden. Encadena los scripts de tools/c1 y deja un resumen.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   referencia y tablas   make c1-generar (sw/c1.s y sw/c1_tabla.hex son los generados
#                         desde el modelo), tools/c1/tb_tabla.sh (hardware nuevo)
#   gemelo                tools/c1/cosim.py (el gemelo con la tabla de 512 palabras
#                         contra el RTL de R3)
#   puerta a              tools/c1/puerta_a.sh (política apagada = banda 40 de R2)
#   puerta b              tools/c1/puerta_b.sh (assembly contra referencia: Tesla, AMD,
#                         Meta y 200 ventanas, a los tres ritmos)
#   puerta c              la puerta de simulación de docs/puertas.md:
#     1. oficial          tools/c1/oficial.sh
#     2. equivalencia     la puerta b, las copias del oficial (oficial.sh) y
#                         tools/c1/series.sh (1 050 series sintéticas)
#     4. fases            tools/c1/fases.sh
#     5. core             tools/c1/criterio5.sh
#     6. degradación      tools/c1/degradacion.sh y tools/c1/controles.sh
#     7. estrés           tools/c1/estres.sh
#     8. bitstream        tools/c1/bitstreams.sh
#     3.2 del enunciado   tools/c1/ticks.sh
#   puerta d              make c1-timing (síntesis en 10 semillas: celdas, bloques de
#                         memoria y temporización) y el criterio 8
#
# Variables: SOLO="a b oficial ..." corre solo esos pasos; SALTAR="b criterio5" los
# salta (para no repetir una corrida larga cuyo código no cambió: el resumen cita el
# registro que ya existe). GUARDAR=1 copia los bitstreams a bitstreams/ si todo pasa.
#
# Uso: [JOBS=12] [SALTAR="..."] [GUARDAR=1] tools/c1/puerta.sh   (make c1-puerta)
# Resultado en docs/mediciones/c1/puerta.txt. Unas 3 horas completa.
set -uo pipefail
RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$RAIZ"
[ -n "${OSS_CAD_SUITE:-}" ] && export PATH="$OSS_CAD_SUITE/bin:$PATH"
export JOBS=${JOBS:-12}
M=docs/mediciones/c1
B=build/c1/puerta
SALIDA=${SALIDA:-$M/puerta.txt}
mkdir -p "$B" "$M"
f=0
quiere() { case " ${SALTAR:-} " in *" $1 "*) return 1 ;; esac; [ -z "${SOLO:-}" ] && return 0; case " $SOLO " in *" $1 "*) return 0 ;; esac; return 1; }
# paso ETIQUETA REGISTRO comando...: corre el paso, o cita su registro si se salta
paso() {
  local e=$1 reg=$2; shift 2
  if quiere "$e"; then
    echo "== $e: $*"
    local t0=$(date +%s)
    "$@" > "$B/$e.log" 2>&1; local r=$?
    if [ $r = 0 ]; then echo "PASS $e ($(( ($(date +%s) - t0) / 60 )) min)"; else echo "FAIL $e (codigo $r, ver $B/$e.log)"; f=$((f + 1)); fi
  else
    echo "== $e: no se corre ahora; vale el registro $reg"
    if [ -f "$reg" ] && ! grep -q "^FAIL" "$reg" && tail -5 "$reg" | grep -q "^PASS"; then echo "PASS $e (registro $reg)"; else echo "FAIL $e: el registro $reg no existe o no termina en PASS"; f=$((f + 1)); fi
  fi
  [ -f "$reg" ] && grep -E "^(PASS|FAIL):? " "$reg" | grep -E "^(PASS|FAIL):|peor caso|Peor caso" | tail -4 | cut -c1-230 | sed 's/^/     /'
  return 0
}
{
echo "Puertas de R3: C1 en los cuatro hilos del Espino barrel con vigilante y la tabla de 512 palabras"
echo "Generado por tools/c1/puerta.sh, commit $(git rev-parse --short HEAD)$([ -n "$(git status --porcelain rtl sw tools/c1 ref/c1 ref/gemelo tb/c1)" ] && echo ' con cambios sin commit')."
echo "sw/c1.s sha256 $(sha256sum sw/c1.s | cut -c1-16)..., sw/c1_tabla.hex sha256 $(sha256sum sw/c1_tabla.hex | cut -c1-16)..."
echo
echo "Referencia, tablas y hardware nuevo"
paso generar "$B/generar.log" make -s c1-generar
paso tb_tabla $M/tb_tabla.txt tools/c1/tb_tabla.sh
paso cosim $M/cosim.txt python3 tools/c1/cosim.py --jobs "$JOBS"
echo
echo "Puerta a: con la politica apagada, las ordenes de la banda 40 de R2"
paso a $M/puerta_a.txt tools/c1/puerta_a.sh
echo
echo "Puerta b: assembly contra la referencia entera, orden por orden"
paso b $M/puerta_b.txt env RONDA1=1 tools/c1/puerta_b.sh
echo
echo "Puerta c: la puerta de simulacion de R0, R1 y R2 (docs/puertas.md)"
echo "1. Testbench oficial sin modificar, y 2. copias del oficial a los tres periodos"
paso oficial $M/oficial.txt env RONDA1=1 tools/c1/oficial.sh
echo "2. Equivalencia en series sinteticas (la de series reales es la puerta b)"
paso series $M/series.txt tools/c1/series.sh
echo "4. Fases"
paso fases $M/fases.txt tools/c1/fases.sh
echo "5. Core en la configuracion exacta"
paso criterio5 $M/criterio5_verificacion.txt tools/c1/criterio5.sh
echo "6. Degradacion y controles negativos"
paso degradacion $M/degradacion.txt tools/c1/degradacion.sh
paso controles $M/controles.txt tools/c1/controles.sh
echo "7. Estres"
paso estres $M/estres.txt tools/c1/estres.sh
echo "Mediciones por tick (punto 3.2)"
paso ticks $M/ticks.txt tools/c1/ticks.sh
echo
echo "Puerta d: sintesis"
echo "3. Timing en 10 semillas, celdas y bloques de memoria"
paso timing $M/timing.txt make -s c1-timing
[ -f $M/timing.txt ] && sed 's/^/     /' $M/timing.txt | cut -c1-200
echo "8. Bitstream: molde con icebram, simulacion desde el .asc, vigilante e imagen multiple"
G=0; [ "${GUARDAR:-0}" = 1 ] && [ "$f" = 0 ] && G=1
paso bitstreams $M/bitstreams.txt env GUARDAR=$G tools/c1/bitstreams.sh
echo
if [ "$f" -eq 0 ]; then echo "PASS: R3 paso todos los pasos"; else echo "FAIL: $f pasos fallaron"; fi
} 2>&1 | tee "$SALIDA"
grep -q "^PASS: R3 paso" "$SALIDA"
