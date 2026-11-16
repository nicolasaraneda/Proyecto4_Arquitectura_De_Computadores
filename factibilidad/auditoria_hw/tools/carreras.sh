#!/usr/bin/env bash
# carreras.sh: búsqueda de carreras entre los hilos del fondo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Intenta encontrar un caso en que el supervisor decida con datos mezclados de
# dos ticks. La pieza auditada probó 24 fases de llegada con los gestores de
# tiempo constante y un solo gestor atrasado una cantidad fija. Aquí:
#   - la llegada del precio se corre una cantidad al azar en cada tick
#     (período + 0 a J nanosegundos), así que recorre todas las fases de la
#     rotación de hilos y de los lazos de espera, también dentro de un ciclo;
#   - los tres gestores y el supervisor demoran una cantidad distinta y al azar
#     en cada tick, antes y después de publicar (tools/prog_carreras.py agrega
#     lazos de retardo que leen los interruptores, que el testbench mueve);
#   - se prueban períodos más cortos que el de la ronda 3, con los que un
#     gestor sigue ocupado cuando llega el precio siguiente y el fondo pierde
#     precios, y un retardo tan largo que la vuelta del gestor no cabe en el tick.
# Cada corrida se revisa de dos formas independientes:
#   monitores  tb/tb_carreras.sv vigila cada escritura en PUB, EST_k, DES_k y
#              DECISION, cada acceso al esclavo SPI y cada carga de EST_k
#              que hace el supervisor (M1 a M9, ver su encabezado). No usan
#              la referencia.
#   modelo     el estado de la memoria al terminar cada tick (13 campos) contra
#              la traza de fondo.c corrido sobre los precios que el supervisor
#              publicó. Sirve aunque se pierdan precios.
#
# Programas: "sin" es sw/fondo.s tal cual; "ret4" y "ret6" le agregan los
# retardos (después de publicar, hasta 240 y 960 vueltas); "ant4" es la
# variante que decide con lo del tick anterior (tools/variante.py de la pieza)
# con los mismos retardos, contra fondo_min_ant.
#
# Uso: factibilidad/auditoria_hw/tools/carreras.sh   (o make carreras)
# Resultado en mediciones/carreras.txt. Unos 3 minutos con 5 procesos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"
arnes || exit 1

O=$B/carreras
mkdir -p "$O/series"
NT=${NT:-20000}

# preparar NOMBRE FUENTE.s [opciones de prog_carreras.py]
preparar() {
  local n=$1 fuente=$2 d=$O/$1; shift 2
  mkdir -p "$d"
  $PYTHON $U/tools/prog_carreras.py "$fuente" -o "$d/fondo.s" "$@" || return 1
  $PYTHON tools/pochoasm.py "$d/fondo.s" -o "$d/fondo.hex" > /dev/null || return 1
  $PYTHON $F/tools/simbolos.py "$d/fondo.s" --vh "$d/simbolos.vh" || return 1
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_carreras -O3 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS "-DPROGRAMA=\"$d/fondo.hex\"" "-I$d" --Mdir "$d/obj" -o sim \
    "$CELLS_SIM" $SRC_BARREL_PROTO $U/tb/tb_carreras.sv > "$d/verilator.log" 2>&1 || { echo "FAIL $n: Verilator no compila"; return 1; }
}

serie() {   # serie FAMILIA: ruta de la serie (la de práctica o una sintética con la semilla 1)
  if [ "$1" = practica ]; then echo tb/practica.csv; return; fi
  local s=$O/series/$1.csv
  [ -s "$s" ] || $PYTHON ref/series.py "$1" --n "$NT" --semilla 1 -o "$s" > /dev/null
  echo "$s"
}

# corrida ETIQUETA PROGRAMA FAMILIA NTICKS PERIODO JITTER SW_CADA SEMILLA
corrida() {
  local e=$1 p=$2 d=$O/$2 n est=fondo_min modo="" ant=0
  [ "$p" = ant4 ] && { est=fondo_min_ant; modo=anterior; ant=1; }
  "$d/obj/sim" "+serie=$(serie "$3")" "+nticks=$4" "+periodo=$5" "+jitter=$6" "+sw_cada=$7" "+semilla=$8" "+anterior=$ant" \
    "+vistos_csv=$d/$e.vistos.csv" "+estado_csv=$d/$e.estado.csv" > "$d/$e.log" 2>&1
  n=$(($(wc -l < "$d/$e.estado.csv") - 1))
  FONDO_TRAZA=$d/$e.traza.csv HILOS=1 "$ARNES" correr --estrategia "$est" --serie "$d/$e.vistos.csv" --nticks "$n" --perdidos 0 -o "$d/$e.ref.csv" > "$d/$e.ref.log" 2>&1
  {
    printf "%-4s %-5s %-9s %6s %8s %6s %5s %3s | " "$e" "$p" "$3" "$4" "$5" "$6" "$7" "$8"
    printf "publicados %6s perdidos %5s peor %5s | " "$(grep 'Precios publicados' "$d/$e.log" | grep -o '[0-9]*' | head -1)" \
      "$(grep 'Precios publicados' "$d/$e.log" | grep -o '[0-9]*' | tail -1)" "$(grep 'Peor respuesta' "$d/$e.log" | grep -o '[0-9]*')"
    printf "esperas %5s %5s %5s | " $(grep '^Cargas de EST_k' "$d/$e.log" | sed 's/.*: *//')
    printf "%s | " "$(grep -E '^(PASS|FAIL) monitores' "$d/$e.log" | cut -d: -f1)"
    $PYTHON $U/tools/comparar_vistos.py "$d/$e.estado.csv" "$d/$e.traza.csv" $modo | sed -E 's/ identicas a la referencia sobre los precios vistos//'
  } > "$d/$e.resultado.txt"
}
export -f corrida serie
export O U ARNES PYTHON NT

$PYTHON $F/tools/variante.py $F/sw/fondo.s anterior -o "$O/fondo_anterior.s" || exit 1
preparar sin  $F/sw/fondo.s               || exit 1
preparar ret4 $F/sw/fondo.s --retardos 4  || exit 1
preparar ret6 $F/sw/fondo.s --retardos 6  || exit 1
preparar ant4 "$O/fondo_anterior.s" --retardos 4 || exit 1
for f in volatil saltos; do serie $f > /dev/null; done

LISTA="c01 sin  practica $NT 100000 4000 0 1
c02 ret4 practica $NT 100000 4000 37 1
c03 ret4 practica $NT 100000 4000 37 2
c04 ret4 practica $NT 100000 4000 37 3
c05 ret4 volatil  $NT 100000 4000 37 1
c06 ret4 volatil  $NT 100000 4000 37 2
c07 ret4 volatil  $NT 100000 4000 37 3
c08 ret4 saltos   $NT 100000 4000 5 4
c09 ret4 saltos   $NT 100000 4000 997 5
c10 ret4 practica $NT 60000 4000 37 6
c11 ret4 volatil  $NT 60000 4000 37 7
c12 ret4 practica $NT 40000 2000 37 8
c13 ret4 volatil  $NT 40000 2000 37 9
c14 ret4 volatil  3000 1000000 40000 37 10
c15 ret6 practica $NT 100000 4000 37 11
c16 ret6 volatil  $NT 100000 4000 37 12
c17 ant4 practica $NT 100000 4000 37 13
c18 ant4 volatil  $NT 100000 4000 37 14
c19 ant4 volatil  $NT 60000 4000 37 15"

T0=$(date +%s)
echo "$LISTA" | xargs -P "$JOBS" -L 1 bash -c 'corrida "$@"' _
T1=$(date +%s)

{
echo "Auditoría: búsqueda de carreras entre los hilos del fondo (sw/fondo.s en el Espino barrel)"
echo "Generado por factibilidad/auditoria_hw/tools/carreras.sh (make carreras). No editar a mano."
echo
versiones
echo "Programas: sin = sw/fondo.s tal cual ($(sha256sum "$O/sin/fondo.hex" | cut -c1-12)...); ret4 y ret6 = con retardos según los interruptores"
echo "  (después de publicar, hasta 240 y 960 vueltas de dos instrucciones); ant4 = variante que decide con el tick anterior, con retardos."
echo "  Palabras distintas de cero en la imagen: sin $(grep -vc '^00000000' "$O/sin/fondo.hex"), ret4 $(grep -vc '^00000000' "$O/ret4/fondo.hex"), ret6 $(grep -vc '^00000000' "$O/ret6/fondo.hex"), ant4 $(grep -vc '^00000000' "$O/ant4/fondo.hex")."
echo "Columnas: corrida, programa, serie, ticks, período (ns), corrimiento máximo de la llegada (ns), ciclos entre cambios de los"
echo "  interruptores, semilla | precios publicados, precios perdidos por atraso, peor respuesta (ciclos) | veces que el supervisor"
echo "  cargó EST_1, EST_2 y EST_3 cuando todavía eran de otro tick y tuvo que volver a leer | monitores | modelo"
echo "Demora: $((T1 - T0)) s con $JOBS procesos."
echo
for e in $(echo "$LISTA" | cut -d' ' -f1); do
  p=$(echo "$LISTA" | grep "^$e " | awk '{print $2}')
  cat "$O/$p/$e.resultado.txt" 2>/dev/null || echo "$e FAIL sin resultado"
done
echo
tot=$(echo "$LISTA" | wc -l)
okm=0; okr=0; dec=0; viol=0
for e in $(echo "$LISTA" | cut -d' ' -f1); do
  p=$(echo "$LISTA" | grep "^$e " | awk '{print $2}')
  grep -q "^PASS monitores" "$O/$p/$e.log" 2>/dev/null && okm=$((okm + 1))
  grep -q "PASS modelo" "$O/$p/$e.resultado.txt" 2>/dev/null && okr=$((okr + 1))
  dec=$((dec + $(grep '^Decisiones' "$O/$p/$e.log" | grep -o '[0-9]*')))
  viol=$((viol + $(grep '^Violaciones' "$O/$p/$e.log" | sed 's/.*: *//' | tr ' ' '\n' | awk '{s += $1} END {print s + 0}')))
done
echo "Corridas: $tot. Monitores sin violaciones: $okm. Iguales al modelo: $okr. Decisiones vigiladas: $dec. Violaciones: $viol."
echo "Violaciones por monitor (M1 a M7), sumadas: $(for e in $(echo "$LISTA" | cut -d' ' -f1); do p=$(echo "$LISTA" | grep "^$e " | awk '{print $2}'); grep '^Violaciones M1' "$O/$p/$e.log" | sed 's/.*: *//'; done | awk '{for (i = 1; i <= 7; i++) s[i] += $i} END {for (i = 1; i <= 7; i++) printf "%d ", s[i]}'). M8 (accesos al SPI que no son load o store del hilo 0): $(for e in $(echo "$LISTA" | cut -d' ' -f1); do p=$(echo "$LISTA" | grep "^$e " | awk '{print $2}'); grep '^Violaciones M8' "$O/$p/$e.log" | sed 's/.*: *//'; done | awk '{s += $1} END {print s + 0}')."
echo "M9 (decisiones con un EST_k que el supervisor cargó de otro tick): $(for e in $(echo "$LISTA" | cut -d' ' -f1); do p=$(echo "$LISTA" | grep "^$e " | awk '{print $2}'); grep '^Violaciones M9' "$O/$p/$e.log" | sed 's/.*: *//'; done | awk '{s += $1} END {print s + 0}'). Cargas en que el supervisor encontró EST_1, EST_2 y EST_3 de otro tick y esperó, sumadas: $(for e in $(echo "$LISTA" | cut -d' ' -f1); do p=$(echo "$LISTA" | grep "^$e " | awk '{print $2}'); grep '^Cargas de EST_k' "$O/$p/$e.log" | sed 's/.*: *//'; done | awk '{for (i = 1; i <= 3; i++) s[i] += $i} END {for (i = 1; i <= 3; i++) printf "%d ", s[i]}')."
if [ "$okm" = "$tot" ] && [ "$okr" = "$tot" ]; then
  echo "RESULTADO: PASS, no se encontró ningún caso en que el supervisor decida con datos de dos ticks"
else
  echo "RESULTADO: FAIL, hay corridas con violaciones o distintas del modelo"
fi
} | tee "$M/carreras.txt"

grep -q "^RESULTADO: PASS" "$M/carreras.txt"
