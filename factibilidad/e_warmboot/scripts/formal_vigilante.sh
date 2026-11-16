#!/usr/bin/env bash
# formal_vigilante.sh: corre las pruebas formales del vigilante.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# 1. formal/vigilante.sby: prueba por inducción y alcanzabilidad, con N = 1,
#    4 y 7. Todas las tareas deben terminar en PASS.
# 2. Controles negativos: la misma prueba (N = 4) sobre dos copias del módulo
#    con un error puesto a propósito. Las dos deben terminar en FAIL; si
#    alguna pasa, las propiedades no están comprobando nada.
#      mutación A  BOOT sube sin esperar a que CS_n esté en alto
#      mutación B  el disparo ocurre con un precio menos (cuenta N en vez de N + 1)
#
# Uso, desde la raíz del repositorio:
#   factibilidad/e_warmboot/scripts/formal_vigilante.sh
# Resultado en mediciones/vigilante_formal.txt. Los directorios de trabajo de
# sby quedan en build/formal/.
set -euo pipefail

E=factibilidad/e_warmboot
D=$E/build/formal
rm -rf "$D"
mkdir -p "$D" "$E/mediciones"
sed 's|\.\./rtl/vigilante.v|../../rtl/vigilante.v|' $E/formal/vigilante.sby > "$D/vigilante.sby"
( cd "$D" && sby -f vigilante.sby > sby.log 2>&1 ) || true

# Controles negativos
sed 's/if ((lleno | forzar_i) & ~cs_activo_i) boot_q/if (lleno | forzar_i) boot_q/' $E/rtl/vigilante.v > "$D/mut_a.v"
sed 's/wire lleno = (sin_resp == N + 1);/wire lleno = (sin_resp == N);/' $E/rtl/vigilante.v > "$D/mut_b.v"
for m in a b; do
  if cmp -s "$D/mut_$m.v" $E/rtl/vigilante.v; then echo "ERROR: la mutación $m no cambió el archivo"; exit 1; fi
  mkdir -p "$D/mut_$m"
  cp "$D/mut_$m.v" "$D/mut_$m/vigilante.v"
  cat > "$D/mut_$m/mut.sby" <<FIN
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
  ( cd "$D/mut_$m" && sby -f mut.sby > sby.log 2>&1 ) || true
done

estado() { head -1 "$1" 2>/dev/null | cut -d' ' -f1 || true; }

{
  echo "Verificación formal del vigilante (formal/vigilante.sby)"
  echo "Comando: factibilidad/e_warmboot/scripts/formal_vigilante.sh"
  echo "Herramientas: $(sby --version 2>&1 | head -1), $(yices-smt2 --version 2>&1 | head -1)"
  echo "Propiedades en rtl/vigilante.v: $(grep -c 'assert (' $E/rtl/vigilante.v) sentencias assert y $(grep -c 'cover (' $E/rtl/vigilante.v) cover"
  echo
  echo "Tarea       Resultado   Detalle"
  for t in prove_n1 prove_n4 prove_n7; do
    printf "%-11s %-11s %s\n" "$t" "$(estado "$D/vigilante_$t/status")" \
      "$(grep "\[vigilante_$t\] summary: successful" "$D/sby.log" | sed 's/.*summary: //' | head -1)"
  done
  for t in cover_n1 cover_n4 cover_n7; do
    printf "%-11s %-11s %s\n" "$t" "$(estado "$D/vigilante_$t/status")" \
      "$(grep "\[vigilante_$t\] summary:   reached cover" "$D/sby.log" | sed -E 's/.*at vigilante.v:([0-9]+).* step ([0-9]+)/línea \1 en el paso \2/' | paste -sd, | sed 's/,/, /g')"
  done
  echo
  echo "Línea 152: cover (boot_q && !f_forzado), el disparo por cuenta, sin disparo manual."
  echo "Línea 153: cover (f_respuestas == 8 && !boot_q), ocho precios respondidos sin que BOOT suba."
  echo
  echo "Controles negativos (deben dar FAIL):"
  printf "%-11s %-11s %s\n" "mutación A" "$(estado "$D/mut_a/mut/status")" \
    "$(grep -m1 "Assert failed" "$D/mut_a/sby.log" | sed -E 's/.*(Assert failed in vigilante: [^ ]+).*/\1/')"
  printf "%-11s %-11s %s\n" "mutación B" "$(estado "$D/mut_b/mut/status")" \
    "$(grep -m1 "Assert failed" "$D/mut_b/sby.log" | sed -E 's/.*(Assert failed in vigilante: [^ ]+).*/\1/')"
} | tee $E/mediciones/vigilante_formal.txt

ok=1
for t in prove_n1 prove_n4 prove_n7 cover_n1 cover_n4 cover_n7; do
  [ "$(estado "$D/vigilante_$t/status")" = PASS ] || ok=0
done
[ "$(estado "$D/mut_a/mut/status")" = FAIL ] || ok=0
[ "$(estado "$D/mut_b/mut/status")" = FAIL ] || ok=0
if [ $ok = 1 ]; then echo "RESULTADO: correcto" | tee -a $E/mediciones/vigilante_formal.txt
else echo "RESULTADO: con fallas" | tee -a $E/mediciones/vigilante_formal.txt; exit 1; fi
