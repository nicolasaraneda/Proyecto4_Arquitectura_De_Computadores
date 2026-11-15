#!/usr/bin/env bash
# variantes.sh: variantes del protocolo entre hilos, medidas contra la referencia.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Cada variante sale de sw/fondo.s con tools/variante.py (solo mueve o agrega
# las líneas que dice su nombre) y corre la serie de práctica completa con
# tb/tb_fondo.sv y Verilator.
#
#   base              el programa tal cual
#   espejo_antes      el espejo de la cuenta se calcula mientras los gestores
#                     trabajan, antes de decidir. Mismas decisiones.
#   atraso_800        el gestor 3 demora 800 ciclos más antes de publicar.
#                     Mismas decisiones: el supervisor lo espera.
#   atraso_800_g2     lo mismo con el gestor 2. Sin retardos el supervisor
#                     siempre encuentra publicados a los gestores 2 y 3, así
#                     que cada espera necesita su propia variante (la agregó
#                     la auditoría, README sección 15).
#   despues_2000      el gestor 3 gasta 2000 ciclos después de publicar. Su
#                     vuelta completa (unos 2150 ciclos) cabe en el tick de
#                     2500, así que no debe cambiar ni la respuesta.
#   despues_2400      lo mismo con 2400 ciclos: su vuelta completa (unos 2550
#                     ciclos) ya no cabe en el tick de 0,1 ms. Se mide cómo falla.
#   atraso_2400       el gestor 3 demora 2400 ciclos más antes de publicar: la
#                     respuesta ya no cabe en el tick de 0,1 ms. Se mide cómo
#                     falla. Con el período de 1 ms vuelve a caber.
#   anterior          el supervisor decide con lo publicado en el tick
#                     anterior. Referencia: fondo_min_ant.
#   vuelta            el contador de ticks (24 bits) da la vuelta en el tick 16.
#                     Mismas decisiones.
#
# Uso: factibilidad/b_fondo_hilos/tools/variantes.sh   (o make variantes)
# Resultado en mediciones/variantes.txt. Demora unos 3 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

NTICKS=${NTICKS:-20000}

armar base                                || exit 1
armar espejo_antes espejo_antes           || exit 1
armar atraso_800 retardo_antes:100:3      || exit 1
armar atraso_800_g2 retardo_antes:100:2   || exit 1
armar despues_2000 retardo_despues:250:3  || exit 1
armar despues_2400 retardo_despues:300:3  || exit 1
armar atraso_2400 retardo_antes:300:3     || exit 1
armar anterior anterior                   || exit 1
armar vuelta vuelta                       || exit 1

# variante NOMBRE ESTRATEGIA ETIQUETA NTICKS PERIODO_NS: compila (si hace falta), corre y compara
variante() {
  local n=$1 est=$2 e=$3 d=$B/sim/$1 k
  if [ ! -x "$d/obj/sim" ] || [ "$B/prog/$n/fondo.hex" -nt "$d/obj/sim" ] || [ "$F/tb/tb_fondo.sv" -nt "$d/obj/sim" ]; then
    compilar_fondo "$n" || { echo "FAIL $n: Verilator no compila" > "$d/$e.resultado.txt"; return; }
  fi
  k=$(perdidos "$5")
  correr_fondo "$n" "$e" tb/practica.csv "$4" "$5" 4000
  referencia "$est" tb/practica.csv "$4" "$k" "$d/$e.ref.csv" "$d/$e.traza.csv" > "$d/$e.ref.log"
  local chequeos perdidos_tb iguales
  chequeos=$(grep -o "Chequeos aprobados: [0-9]/4" "$d/$e.log" | grep -o "[0-9]/4")
  perdidos_tb=$(grep "Precios perdidos" "$d/$e.log" | grep -o "[0-9]*$")
  if cmp -s "$d/$e.dec.csv" "$d/$e.ref.csv"; then iguales="identicas a $est"
  else iguales="DISTINTAS a $est desde la fila $(cmp "$d/$e.dec.csv" "$d/$e.ref.csv" | grep -o 'line [0-9]*' | grep -o '[0-9]*')"; fi
  echo "$n ($e): $4 ticks, periodo $5 ns: $chequeos, precios perdidos $perdidos_tb, respuestas $(grep 'Respuestas' "$d/$e.log" | grep -o '[0-9]*$'), decisiones $iguales, patrimonio $(grep 'Patrimonio' "$d/$e.log" | grep -o '[0-9]*$'), peor caso $(grep 'Peor caso' "$d/$e.log" | grep -o ': [0-9]* ciclos' | grep -o '[0-9]*') ciclos" > "$d/$e.resultado.txt"
}
export -f variante compilar_fondo correr_fondo referencia perdidos
export B F ARNES PYTHON CELLS_SIM BARREL_SRC

printf '%s\n' "base fondo_min var $NTICKS 100000" "espejo_antes fondo_min var $NTICKS 100000" \
  "atraso_800 fondo_min var $NTICKS 100000" "atraso_800_g2 fondo_min var $NTICKS 100000" \
  "despues_2000 fondo_min var $NTICKS 100000" \
  "despues_2400 fondo_min var $NTICKS 100000" \
  "atraso_2400 fondo_min var $NTICKS 100000" "anterior fondo_min_ant var $NTICKS 100000" \
  | xargs -P "$JOBS" -L 1 bash -c 'variante "$@"' _
# El atraso que no cabe a 0,1 ms, con el período de la ronda 2, y la vuelta del contador
printf '%s\n' "atraso_2400 fondo_min var_1ms 3000 1000000" "vuelta fondo_min var $NTICKS 100000" \
  | xargs -P "$JOBS" -L 1 bash -c 'variante "$@"' _

{
echo "Variantes del protocolo entre hilos, serie de practica, $NTICKS ticks"
echo "Generado por factibilidad/b_fondo_hilos/tools/variantes.sh (make variantes). No editar a mano."
echo
versiones
echo
echo "1. Resultado de cada corrida"
echo
for n in base espejo_antes atraso_800 atraso_800_g2 despues_2000 despues_2400 atraso_2400 anterior; do sed 's/^/  /' "$B/sim/$n/var.resultado.txt"; done
sed 's/^/  /' "$B/sim/atraso_2400/var_1ms.resultado.txt"
sed 's/^/  /' "$B/sim/vuelta/var.resultado.txt"
echo
echo "2. Estado interno contra la traza en C (las variantes que deben decidir igual que fondo_min)"
echo
for n in base espejo_antes atraso_800 atraso_800_g2 despues_2000 vuelta; do
  echo "  $n:"
  $PYTHON $F/tools/comparar_estado.py "$B/sim/$n/var.ticks.csv" "$B/sim/$n/var.traza.csv" | sed 's/^/  /'
done
echo
echo "3. Ciclos e instrucciones por tick"
echo
$PYTHON $F/tools/resumen_ticks.py cabecera
for n in base espejo_antes atraso_800 atraso_800_g2 despues_2000 despues_2400 atraso_2400 anterior; do
  $PYTHON $F/tools/resumen_ticks.py linea "$n" "$B/sim/$n/var.ticks.csv"
done
$PYTHON $F/tools/resumen_ticks.py linea "atraso_2400 a 1 ms" "$B/sim/atraso_2400/var_1ms.ticks.csv"
$PYTHON $F/tools/resumen_ticks.py linea "vuelta" "$B/sim/vuelta/var.ticks.csv"
echo
echo "  Columnas: respuesta en ciclos desde byte_done hasta DECISION (promedio de todos los ticks, promedio de los"
echo "  ticks sin frontera de ventana y peor caso); ultimo ciclo con trabajo del supervisor (promedio y peor);"
echo "  instrucciones de trabajo del supervisor por tick; instrucciones del supervisor esperando a los gestores."
echo
echo "4. Programas"
echo
for n in base espejo_antes atraso_800 atraso_800_g2 despues_2000 despues_2400 atraso_2400 anterior vuelta; do
  echo "  $n: $(diff "$B/prog/base/fondo.s" "$B/prog/$n/fondo.s" | grep -c '^[<>]') lineas distintas de sw/fondo.s, sha256 de la imagen $(sha256sum "$B/prog/$n/fondo.hex" | cut -c1-12)..."
done
echo
echo "5. Que se espera de cada una"
echo
echo "  base, espejo_antes, atraso_800, atraso_800_g2, despues_2000 y vuelta deben dar 4/4 y decisiones identicas a fondo_min."
echo "  anterior debe dar 4/4 y decisiones identicas a fondo_min_ant."
echo "  despues_2400 y atraso_2400 a 0,1 ms deben fallar: la vuelta del gestor 3 no cabe en el tick."
echo "  atraso_2400 a 1 ms debe dar 4/4 y decisiones identicas a fondo_min."
ok=1
for n in base espejo_antes atraso_800 atraso_800_g2 despues_2000 vuelta; do
  grep -q ": 4/4, precios perdidos 0, respuestas [0-9]*, decisiones identicas a fondo_min," "$B/sim/$n/var.resultado.txt" || { ok=0; echo "FAIL $n no cumple lo esperado"; }
done
grep -q ": 4/4, precios perdidos 0, respuestas [0-9]*, decisiones identicas a fondo_min_ant," "$B/sim/anterior/var.resultado.txt" || { ok=0; echo "FAIL anterior no cumple lo esperado"; }
grep -q ": 4/4, precios perdidos 0, respuestas [0-9]*, decisiones identicas a fondo_min," "$B/sim/atraso_2400/var_1ms.resultado.txt" || { ok=0; echo "FAIL atraso_2400 a 1 ms no cumple lo esperado"; }
for n in despues_2400 atraso_2400; do
  grep -q ": 4/4," "$B/sim/$n/var.resultado.txt" && { ok=0; echo "FAIL $n a 0,1 ms no deberia dar 4/4"; }
done
[ $ok = 1 ] && echo "PASS las diez corridas dan lo esperado"
} | tee "$M/variantes.txt"

! grep -q "^FAIL" "$M/variantes.txt"
