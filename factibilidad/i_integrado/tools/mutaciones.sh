#!/usr/bin/env bash
# mutaciones.sh: controles negativos de las pruebas del diseño integrado.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Una prueba que siempre pasa no prueba nada. Este script rompe a propósito
# lo que este estudio agregó (la integración de la extensión en la etapa X,
# la conexión del vigilante y la memoria de la tabla), de una forma distinta
# cada vez, y exige que alguna prueba lo note. Las mutaciones son reemplazos
# de texto en copias del RTL (tools/mutar.py): rtl/ no se toca.
#
# Con cada copia mutada se corren seis pruebas cortas sobre una configuración
# "ancha", que tiene todos los caminos de integración a la vez (emad, devk,
# mulstep y los carriles en el sumador de la ALU con xd_alu, divstep por
# xd_unit, el vigilante y la tabla):
#   XD   6 programas de custom-0 con los cuatro hilos, contra el modelo de d_isa
#   RV   cada hilo contra el Espino base con tb/tb_verif.sv de a_barrel:
#        un programa de un hilo, uno de cuatro hilos con zonas separadas, uno
#        con el SPI en un hilo y uno con memoria compartida (RV32E)
#   T1   sw/tabla_prueba.s con la tabla de 256 x 16 por MMIO
#   T2   sw/tabla_prueba.s con las otras 512 palabras de datos
#   TM   los dos módulos de memoria solos, con accesos al azar
#   VIG  sw/cuelgue_supervisor.s: el supervisor se cuelga y los otros hilos siguen
# El script termina bien solo si el RTL sin mutar pasa las seis y cada
# mutación es detectada por al menos una.
#
# Uso: factibilidad/i_integrado/tools/mutaciones.sh   (o make mutaciones)
# Resultado en mediciones/mutaciones.txt. Unos 6 minutos (casi todo es
# compilar tb_verif con Verilator, una vez por mutación).
# Con SOLO_INFORME=1 vuelve a escribir el informe con la corrida anterior.
# Variable JOBS: mutaciones en paralelo (5).
set -uo pipefail
source "$(dirname "$0")/comun.sh"
source "$I/tools/verif_comun.sh"
source "$I/tools/pruebas_comun.sh"

O=$B/mutaciones
JOBS=${JOBS:-5}
INSTR=${INSTR:-3000}
ANCHA_XD="$(defs_de alu_todo_div)"
PRUEBAS="XD RV T1 T2 TM VIG"
mkdir -p "$O/prog"

# una NOMBRE: aplica la mutación y corre las seis pruebas. Deja una línea por
# prueba en O/NOMBRE/resultado.txt: "PRUEBA PASS|FAIL detalle".
una() {
  local m=$1 d=$O/$1 r=$O/$1/rtl g
  mkdir -p "$d"
  find "$d" -maxdepth 1 -name 'resultado.txt' -delete
  $PYTHON $I/tools/mutar.py "$m" "$r" > "$d/mutar.log" 2>&1 || { echo "NO_APLICA" > "$d/estado.txt"; return 0; }
  VERIF_SPI=$O/pochoco_spi_slave_vig.v
  {
    echo "XD $(correr_xd "$d/xd" "$ANCHA_XD -DI_VIGILANTE -DI_TABLA=1" 6 "$r" | tail -1)"
    if VERIF_OPT="-O1 -CFLAGS -O0" compilar_verif "$d/rv" "$ANCHA_XD -DI_VIGILANTE -DI_TABLA=1" "$r" && [ -x "$d/rv/obj/sim" ]; then
      "$d/rv/obj/sim" "+hex=$O/prog/U.hex" "+instrucciones=$INSTR" +precio_cada=97 +hilo_spi=2 > "$d/rv/U.log" 2>&1
      "$d/rv/obj/sim" "+hex=$O/prog/B.hex" "+instrucciones=$INSTR"                              > "$d/rv/B.log" 2>&1
      "$d/rv/obj/sim" "+hex=$O/prog/C.hex" "+instrucciones=$INSTR" +precio_cada=29 +hilo_spi=1 > "$d/rv/C.log" 2>&1
      "$d/rv/obj/sim" "+hex=$O/prog/D.hex" "+instrucciones=$INSTR" +compartida=1               > "$d/rv/D.log" 2>&1
      local malas="" primera=""
      for g in U B C D; do
        if ! grep -q "^PASS verif" "$d/rv/$g.log"; then
          malas="$malas$g "
          [ -z "$primera" ] && primera=$(grep -m1 '^FAIL' "$d/rv/$g.log" | sed -E 's/^FAIL verif: //' | cut -c1-110)
        fi
      done
      if [ -z "$malas" ]; then echo "RV PASS tb_verif: los 4 programas iguales al Espino base"
      else echo "RV FAIL tb_verif: difieren $malas($primera)"; fi
    else
      echo "RV FAIL tb_verif: no compila"
    fi
    echo "T1 $(DEFS_PRUEBA="$ANCHA_XD -DI_VIGILANTE" correr_tabla "$d/t" 1 "$r" | tail -1)"
    echo "T2 $(DEFS_PRUEBA="$ANCHA_XD -DI_VIGILANTE" correr_tabla "$d/t" 2 "$r" | tail -1)"
    echo "TM $(CICLOS_TABLA=20000 correr_tabla_mod "$d/tm" "$r" | tail -1)"
    echo "VIG $(DEFS_PRUEBA="$ANCHA_XD -DI_TABLA=1" correr_vig "$d/v" 4 "$r" | tail -1)"
  } > "$d/resultado.txt"
  echo "OK" > "$d/estado.txt"
}

if [ "${1:-}" = --una ]; then una "$2"; exit 0; fi

NOMBRES=$($PYTHON $I/tools/mutar.py --lista)
if [ "${SOLO_INFORME:-0}" != 1 ]; then
  programas_prueba
  preparar_spi "$O" || exit 1
  # Programas de la comparación contra el Espino base (los mismos para todas)
  $PYTHON $A/tools/prog_hilos.py 1 --modo uno --hilo-spi 2 -n 300 -o "$O/prog/U.orig.s"
  $PYTHON $A/tools/prog_hilos.py 1 --modo separado -o "$O/prog/B.orig.s"
  $PYTHON $A/tools/prog_hilos.py 1 --modo spi1 --hilo-spi 1 -o "$O/prog/C.orig.s"
  $PYTHON $A/tools/prog_hilos.py 1 --modo compartido -o "$O/prog/D.orig.s"
  for g in U B C D; do
    $PYTHON $I/tools/sin_custom0.py "$O/prog/$g.orig.s" > "$O/prog/$g.s" 2> /dev/null
    ensamblar "$O/prog/$g.s" "$O/prog/$g.hex" --allow-shifts || { echo "FAIL mutaciones: no ensambla $g"; exit 1; }
  done
  echo "referencia $NOMBRES" | tr ' ' '\n' | xargs -P "$JOBS" -I{} "$RAIZ/$I/tools/mutaciones.sh" --una {}
fi

{
echo "Controles negativos de las pruebas del diseño integrado"
echo "Generado por factibilidad/i_integrado/tools/mutaciones.sh (make mutaciones). No editar a mano."
echo
versiones
echo "  $(verilator --version)"
echo "Configuración de las pruebas: $ANCHA_XD -DI_VIGILANTE -DI_TABLA=1 (T2 con -DI_TABLA=2)"
echo "Pruebas: XD custom-0 en los cuatro hilos contra el modelo; RV cada hilo contra el Espino base (RV32E);"
echo "T1 y T2 la tabla en sus dos formas dentro del SoC; TM los módulos de memoria solos; VIG el vigilante con el supervisor colgado."
echo
fallas=0
echo "Sin mutación: las seis pruebas deben pasar"
if [ "$(cat "$O/referencia/estado.txt" 2>/dev/null)" != OK ]; then
  echo "   FAIL la referencia no corrió"; fallas=$((fallas + 1))
else
  while read -r p estado resto; do
    echo "   $estado $p: $resto"
    [ "$estado" = PASS ] || fallas=$((fallas + 1))
  done < "$O/referencia/resultado.txt"
fi
echo
total=0; detectadas=0; resumen=""
tabla=$($PYTHON $I/tools/mutar.py --tabla)
for m in $NOMBRES; do
  total=$((total + 1))
  desc="$(echo "$tabla" | grep "^$m|" | cut -d'|' -f3) ($(echo "$tabla" | grep "^$m|" | cut -d'|' -f2))"
  if [ "$(cat "$O/$m/estado.txt" 2>/dev/null)" != OK ]; then
    echo "FAIL $m: la mutación no se pudo aplicar o correr (ver $O/$m)"; fallas=$((fallas + 1)); continue
  fi
  quien=$(grep " FAIL " "$O/$m/resultado.txt" | cut -d' ' -f1 | tr '\n' ' ' | sed 's/ $//')
  n=$(grep -c " FAIL " "$O/$m/resultado.txt")
  if [ "$n" -gt 0 ]; then detectadas=$((detectadas + 1)); echo "PASS $m: detectada por $n de las 6 pruebas ($quien)"
  else fallas=$((fallas + 1)); echo "FAIL $m: NO detectada"; fi
  echo "      $desc"
  grep " FAIL " "$O/$m/resultado.txt" | sed -E 's/^([A-Z0-9]+) FAIL /      \1: /' | cut -c1-200
  resumen="$resumen$(printf '   %-22s %d de 6   %s' "$m" "$n" "$quien")"$'\n'
done
echo
echo "Resumen: mutación, cuántas pruebas la detectan y cuáles"
printf '%s' "$resumen"
echo
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, $detectadas de $total mutaciones detectadas y el RTL sin mutar pasa las seis pruebas"
else echo "RESULTADO: FAIL ($detectadas de $total mutaciones detectadas, $fallas problemas)"; fi
} | tee "$M/mutaciones.txt"

grep -q "^RESULTADO: PASS" "$M/mutaciones.txt"
