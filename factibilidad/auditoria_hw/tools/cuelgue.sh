#!/usr/bin/env bash
# cuelgue.sh: qué pasa en el fondo en un chip si un hilo de estrategia se cuelga.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El README de factibilidad/i_integrado decía que el vigilante no ve un hilo
# de estrategia colgado, porque "el supervisor seguiría respondiendo con datos
# viejos de ese hilo". Eso se escribió antes de que existiera el programa del
# fondo. Con sw/fondo.s el supervisor espera a los tres gestores sin plazo,
# así que la predicción es otra: el supervisor se queda esperando, deja de
# escribir DECISION y el vigilante dispara. Aquí se mide.
#
# Programa: sw/fondo.s con el gestor del hilo 3 colgado desde el tick T = 100
# (tools/prog_carreras.py --cuelgue 100). 300 ticks de la serie de práctica a
# 0,1 ms con tb/tb_carreras.sv.
#   barrel  SoC del prototipo del barrel, sin vigilante
#   i1a     hardware I1 (vigilante con N = 4 y tabla de 256 x 16)
#   sano    hardware I1 con el programa sin colgar (control: BOOT no debe subir)
#   lento   hardware I1 con el programa sano y los retardos más largos de la
#           prueba de carreras (tools/prog_carreras.py --retardos 6: la vuelta
#           de un gestor puede durar hasta 3 ticks), 20 000 ticks. El fondo
#           pierde precios. Se mide si eso alcanza para un relevo en falso.
# Lo esperado: la última decisión es la del precio T - 1 = 99 y, en I1, BOOT
# sube en la primitiva SB_WARMBOOT con el precio T + N = 104.
#
# Uso: factibilidad/auditoria_hw/tools/cuelgue.sh   (o make cuelgue)
# Resultado en mediciones/cuelgue.txt. Menos de un minuto.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/cuelgue
T=100
mkdir -p "$O/colgado" "$O/sano" "$O/lento"
$PYTHON $U/tools/prog_carreras.py $F/sw/fondo.s -o "$O/colgado/fondo.s" --cuelgue $T || exit 1
cp $F/sw/fondo.s "$O/sano/fondo.s"
$PYTHON $U/tools/prog_carreras.py $F/sw/fondo.s -o "$O/lento/fondo.s" --retardos 6 || exit 1
for p in colgado sano lento; do
  $PYTHON tools/pochoasm.py "$O/$p/fondo.s" -o "$O/$p/fondo.hex" > /dev/null || exit 1
  $PYTHON $F/tools/simbolos.py "$O/$p/fondo.s" --vh "$O/$p/simbolos.vh" || exit 1
done

compilar() {   # compilar SALIDA PROGRAMA "definiciones" FUENTES...
  local d=$O/$1 p=$O/$2 defs=$3; shift 3
  mkdir -p "$d"
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_carreras -O3 $defs \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS "-DPROGRAMA=\"$p/fondo.hex\"" "-I$p" --Mdir "$d/obj" -o sim \
    "$CELLS_SIM" "$@" $U/tb/tb_carreras.sv > "$d/verilator.log" 2>&1
}
compilar barrel colgado "" $SRC_BARREL_PROTO &
compilar i1a colgado "-DAUD_I1 $DEFS_I1A" $SRC_I &
compilar i1a_sano sano "-DAUD_I1 $DEFS_I1A" $SRC_I &
compilar i1a_lento lento "-DAUD_I1 $DEFS_I1A" $SRC_I &
wait
for c in barrel i1a i1a_sano; do
  [ -x "$O/$c/obj/sim" ] || { echo "FAIL Verilator no compila $c"; exit 1; }
  "$O/$c/obj/sim" +serie=tb/practica.csv +nticks=300 +periodo=100000 > "$O/$c/run.log" 2>&1
done
[ -x "$O/i1a_lento/obj/sim" ] || { echo "FAIL Verilator no compila i1a_lento"; exit 1; }
"$O/i1a_lento/obj/sim" +serie=tb/practica.csv +nticks=20000 +periodo=100000 +jitter=4000 +sw_cada=37 +semilla=11 > "$O/i1a_lento/run.log" 2>&1

campo() { grep "^$2" "$O/$1/run.log" | sed 's/.*: *//'; }
{
echo "Auditoría: un hilo de estrategia colgado en el fondo en un chip"
echo "Generado por factibilidad/auditoria_hw/tools/cuelgue.sh (make cuelgue). No editar a mano."
echo
versiones
echo "Programa: sw/fondo.s con el gestor del hilo 3 colgado desde el tick $T. 300 ticks de la práctica a 0,1 ms."
echo
fallas=0
for c in barrel i1a i1a_sano i1a_lento; do
  case $c in barrel) desc="barrel prototipo, sin vigilante, gestor 3 colgado" ;; i1a) desc="hardware I1 (vigilante N = 4), gestor 3 colgado" ;;
    i1a_sano) desc="hardware I1, programa sano (control)" ;; *) desc="hardware I1, programa sano con retardos largos al azar, 20 000 ticks" ;; esac
  echo "-- $c: $desc"
  grep -E "^(Precios publicados|Decisiones|Ultima decision|Escrituras EST|Peor respuesta|Ciclos con BOOT|BOOT sube|Cuenta maxima)" "$O/$c/run.log" | sed 's/^/   /'
done
echo
ud=$(campo barrel "Ultima decision" | awk '{print $1}')
if [ "$ud" = $((T - 1)) ]; then echo "PASS barrel: la última decisión es la del precio $ud. Desde el tick $T el supervisor espera al gestor 3 y no vuelve a escribir DECISION"
else echo "FAIL barrel: la última decisión es la del precio $ud, se esperaba $((T - 1))"; fallas=1; fi
ud=$(campo i1a "Ultima decision" | awk '{print $1}')
pb=$(campo i1a "BOOT sube")
if [ "$ud" = $((T - 1)) ] && [ "$pb" = $((T + 4)) ]; then echo "PASS i1a: última decisión con el precio $ud y BOOT sube en la primitiva con el precio $pb = T + N. El vigilante sí releva al fondo cuando un gestor se cuelga"
else echo "FAIL i1a: última decisión con el precio $ud y BOOT con el precio $pb (se esperaban $((T - 1)) y $((T + 4)))"; fallas=1; fi
if [ "$(campo i1a_sano "Ciclos con BOOT")" = 0 ] && grep -q "^PASS monitores" "$O/i1a_sano/run.log"; then echo "PASS i1a_sano: con el programa sano BOOT no sube en los 300 ticks"
else echo "FAIL i1a_sano: BOOT sube con el programa sano o los monitores fallan"; fallas=1; fi
cm=$(campo i1a_lento "Cuenta maxima")
if [ "$(campo i1a_lento "Ciclos con BOOT")" = 0 ] && grep -q "^PASS monitores" "$O/i1a_lento/run.log"; then
  echo "PASS i1a_lento: con $(grep '^Precios publicados' "$O/i1a_lento/run.log" | grep -o 'atraso: [0-9]*' | grep -o '[0-9]*') precios perdidos de 20000 la cuenta del vigilante llega a $cm de las 5 que hacen falta: no hay relevo en falso"
else echo "AVISO i1a_lento: el vigilante dispara con el fondo atrasado (cuenta máxima $cm, BOOT con el precio $(campo i1a_lento "BOOT sube"))"; fi
echo
[ $fallas = 0 ] && echo "RESULTADO: PASS" || echo "RESULTADO: FAIL"
} | tee "$M/cuelgue.txt"

grep -q "^RESULTADO: PASS" "$M/cuelgue.txt"
