#!/usr/bin/env bash
# formal.sh: pruebas formales del vigilante con SymbiYosys.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# 1. formal/vigilante/vigilante.sby: prueba por inducción y alcanzabilidad de
#    las propiedades que rtl/vigilante.v trae bajo `ifdef FORMAL, con N = 1, 4
#    y 7. Todas las tareas deben terminar en PASS.
# 2. Controles negativos: la misma prueba por inducción (N = 4) sobre copias
#    del módulo con un error puesto a propósito con sed. rtl/vigilante.v no se
#    toca: las copias quedan en build/vigilante/formal/. Todas deben terminar
#    en FAIL en sby. Si alguna pasa, las propiedades no están comprobando nada.
#      mutación A  BOOT sube sin esperar a que CS_n esté en alto
#      mutación B  el disparo ocurre con un precio menos (cuenta N, no N + 1)
#      mutación C  BOOT vuelve a bajar cuando la condición de disparo se va
#      mutación D  la escritura simultánea con un precio deja la cuenta en 0
#
# Uso, desde cualquier carpeta del repositorio:
#   tools/vigilante/formal.sh      (make vig-formal)
# Resultado en docs/mediciones/vigilante/formal.txt. Termina con error si
# alguna línea da FAIL.
set -uo pipefail
export HW=r2
source "$(dirname "${BASH_SOURCE[0]}")/../fondo/comun.sh"

D=build/vigilante/formal
MV=docs/mediciones/vigilante
INF=$MV/formal.txt
V=rtl/vigilante.v
rm -rf "$D"
mkdir -p "$D" "$MV"

cp formal/vigilante/vigilante.sby "$D/vigilante.sby"
( cd "$D" && sby -f vigilante.sby > sby.log 2>&1 ) || true

# Controles negativos: cada mutación es una sustitución de una sola línea
mutar() {   # mutar LETRA EXPRESION_SED
  mkdir -p "$D/mut_$1"
  sed "$2" $V > "$D/mut_$1/vigilante.v"
  [ "$(diff $V "$D/mut_$1/vigilante.v" | grep -c '^>')" = 1 ] || { echo "la mutacion $1 no cambio exactamente una linea" > "$D/mut_$1/error.txt"; return; }
  cat > "$D/mut_$1/mut.sby" <<FIN
[options]
mode prove
depth 24
[engines]
smtbmc yices
[script]
read_verilog -formal vigilante.v
chparam -set N 4 vigilante
prep -top vigilante
[files]
vigilante.v
FIN
  ( cd "$D/mut_$1" && sby -f mut.sby > sby.log 2>&1 ) || true
}
mutar a 's/if ((lleno | forzar_i) & ~cs_activo_i) boot_q <= 1.b1;/if (lleno | forzar_i) boot_q <= 1'"'"'b1;/'
mutar b 's/wire lleno = (sin_resp == N + 1);/wire lleno = (sin_resp == N);/'
mutar c 's/if ((lleno | forzar_i) & ~cs_activo_i) boot_q <= 1.b1;/boot_q <= (lleno | forzar_i) \& ~cs_activo_i;/'
mutar d 's/if (decision_wr_i) sin_resp <= {{(W-1){1.b0}}, 1.b1};/if (decision_wr_i) sin_resp <= {W{1'"'"'b0}};/'

estado() { head -1 "$1" 2>/dev/null | cut -d' ' -f1; }
linea() { grep -n -F "$1" $V | head -1 | cut -d: -f1; }
L_DISPARO=$(linea 'cover (boot_q && !f_forzado);')
L_SANO=$(linea "cover (f_respuestas == 4'd8 && !boot_q);")

{
  echo "Verificacion formal del vigilante (formal/vigilante/vigilante.sby)"
  echo "Generado por tools/vigilante/formal.sh (make vig-formal). No editar a mano."
  echo
  versiones
  echo "  $(sby --version 2>&1 | head -1)"
  echo "  $(yices-smt2 --version 2>&1 | head -1)"
  echo "Modulo: $V (sha256 $(sha256sum $V | cut -c1-16)...), con $(grep -c 'assert (' $V) sentencias assert y $(grep -c 'cover (' $V) cover."
  echo
  echo "Pruebas por induccion (modo prove, profundidad 24):"
  for t in prove_n1 prove_n4 prove_n7; do
    e=$(estado "$D/vigilante_$t/status")
    det=$(grep "\[vigilante_$t\] summary: successful" "$D/sby.log" | sed 's/.*summary: //' | head -1)
    if [ "$e" = PASS ]; then echo "PASS $t: ${det:-sin detalle}"
    else echo "FAIL $t: sby termino en '${e:-sin estado}' (ver $D/sby.log)"; fi
  done
  echo
  echo "Alcanzabilidad (modo cover, profundidad 80). Linea $L_DISPARO: el disparo por cuenta,"
  echo "sin disparo manual. Linea $L_SANO: ocho precios respondidos sin que BOOT suba."
  for t in cover_n1 cover_n4 cover_n7; do
    e=$(estado "$D/vigilante_$t/status")
    det=$(grep "\[vigilante_$t\] summary:   reached cover" "$D/sby.log" | sed -E 's/.*at vigilante.v:([0-9]+).* step ([0-9]+)/linea \1 en el paso \2/' | paste -sd, | sed 's/,/, /g')
    n=$(grep -c "\[vigilante_$t\] summary:   reached cover" "$D/sby.log")
    if [ "$e" = PASS ] && [ "$n" = 2 ]; then echo "PASS $t: $det"
    else echo "FAIL $t: sby termino en '${e:-sin estado}' con $n de 2 cover alcanzados (ver $D/sby.log)"; fi
  done
  echo
  echo "Controles negativos (N = 4). PASS significa que sby rechazo la copia con el error:"
  nombre_a="BOOT sube sin esperar a CS_n"
  nombre_b="dispara con N precios en vez de N + 1"
  nombre_c="BOOT vuelve a bajar"
  nombre_d="la escritura simultanea deja la cuenta en 0"
  for m in a b c d; do
    n=nombre_$m
    if [ -f "$D/mut_$m/error.txt" ]; then echo "FAIL mutacion $m (${!n}): $(cat "$D/mut_$m/error.txt")"; continue; fi
    e=$(estado "$D/mut_$m/mut/status")
    det=$(grep -m1 "Assert failed" "$D/mut_$m/sby.log" | sed -E 's/.*(Assert failed in vigilante: [^ ]+).*/\1/')
    if [ "$e" = FAIL ]; then echo "PASS mutacion $m (${!n}): sby da FAIL, $det"
    else echo "FAIL mutacion $m (${!n}): sby termino en '${e:-sin estado}', la mutacion no se detecto"; fi
  done
  echo
} > "$INF" 2>&1
echo "Total: $(grep -c '^PASS' "$INF") lineas con PASS y $(grep -c '^FAIL' "$INF") con FAIL." >> "$INF"
cat "$INF"
cierre "$INF"
