#!/usr/bin/env bash
# mutaciones.sh: controles negativos de la verificación del Espino barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Una prueba que siempre pasa no prueba nada. Este script rompe el barrel a
# propósito, de una forma distinta cada vez, y exige que la comparación contra
# el Espino base (tb/tb_verif.sv) lo note. El método viene del
# tb/revision_a_mutaciones.sh de nuestro Proyecto 3 y de tools/mutaciones.sh
# del repositorio.
#
# Las mutaciones son de dos clases:
#   - las de tools/barrel/mutar.py: un reemplazo de texto en una COPIA de los
#     tres archivos del barrel (los de rtl/ no se tocan);
#   - las tres que el core ya traía bajo `ifdef (MUTA_CONTEXTO, MUTA_BOFF y
#     MUTA_ARRANQUE), que usa tools/humo.sh.
#
# Con cada barrel mutado se corren siete comparaciones cortas, una por grupo
# de tools/barrel/verif.sh:
#   A  un hilo (el 2) con un programa aleatorio y los demás ociosos
#   H  sw/hazard_test.s en el hilo 3
#   B  cuatro hilos, zonas de datos separadas
#   C  cuatro hilos, el hilo 1 con el SPI y precios nuevos
#   D  cuatro hilos sobre la misma zona de datos
#   L  programas lineales (se ejecutan una vez), zonas separadas: 3 programas
#   P  programas lineales sobre la misma zona de datos: 3 programas
# L y P son los generadores de la campaña del criterio 5 de la puerta: una
# corrida es mucho más corta que las otras, y por eso llevan tres programas.
# El script termina bien solo si el barrel sin mutar pasa las siete y cada
# mutación es detectada por al menos una. Informa además cuáles la detectan y
# en qué instrucción.
#
# Uso: tools/barrel/mutaciones.sh   (o make barrel-mutaciones)
# Resultado en docs/mediciones/barrel/mutaciones.txt.
# Con SOLO_INFORME=1 no compila ni simula: vuelve a escribir el informe con
# los logs de la corrida anterior.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/mutaciones
JOBS=${JOBS:-5}
INSTR=${INSTR:-3000}
mkdir -p "$O/prog"

# Programas de las comparaciones (los mismos para todas las mutaciones)
$PYTHON tools/prog_aleatorio.py 1 -o "$O/prog/a.base.s" && $PYTHON $T/tabla.py 2 "$O/prog/a.base.s" > "$O/prog/A.s"
$PYTHON $T/tabla.py 3 sw/hazard_test.s > "$O/prog/H.s"
$PYTHON $T/prog_hilos.py 1 --modo separado -o "$O/prog/B.s"
$PYTHON $T/prog_hilos.py 1 --modo spi1 --hilo-spi 1 -o "$O/prog/C.s"
$PYTHON $T/prog_hilos.py 1 --modo compartido -o "$O/prog/D.s"
for k in 1 2 3; do
  $PYTHON $T/prog_hilos.py $k --modo separado --lineal -o "$O/prog/L$k.s"
  $PYTHON $T/prog_hilos.py $((5000000 + k)) --modo compartido --lineal -o "$O/prog/P$k.s"
done
for g in A H B C D L1 L2 L3 P1 P2 P3; do ensamblar "$O/prog/$g.s" "$O/prog/$g.hex" --allow-shifts || { echo "FAIL mutaciones: no ensambla $g"; exit 1; }; done

# una NOMBRE: compila el barrel con esa mutación y corre las siete comparaciones
una() {
  local m=$1 d=$O/$1
  mkdir -p "$d"
  case $m in
    referencia) VERIF_OPT="-O1 -CFLAGS -O0" compilar_verif "$d" ;;
    MUTA_*)     VERIF_OPT="-O1 -CFLAGS -O0" compilar_verif "$d" rtl/espino_core/espino_barrel_core.v rtl/espino_core/espino_barrel_regfile.v rtl/pochoco_soc.v "-D$m" ;;
    *)          $PYTHON $T/mutar.py "$m" "$d/rtl" > "$d/mutar.log" \
                  && VERIF_OPT="-O1 -CFLAGS -O0" compilar_verif "$d" "$d/rtl/espino_barrel_core.v" "$d/rtl/espino_barrel_regfile.v" "$d/rtl/pochoco_soc.v" ;;
  esac
  if [ $? -ne 0 ] || [ ! -x "$d/obj/sim" ]; then echo "NO_COMPILA" > "$d/estado.txt"; return 0; fi
  "$d/obj/sim" "+hex=$O/prog/A.hex" "+instrucciones=$INSTR" +precio_cada=97 +hilo_spi=2 > "$d/A.log" 2>&1
  "$d/obj/sim" "+hex=$O/prog/H.hex" +instrucciones=1500                                 > "$d/H.log" 2>&1
  "$d/obj/sim" "+hex=$O/prog/B.hex" "+instrucciones=$INSTR"                              > "$d/B.log" 2>&1
  "$d/obj/sim" "+hex=$O/prog/C.hex" "+instrucciones=$INSTR" +precio_cada=29 +hilo_spi=1 > "$d/C.log" 2>&1
  "$d/obj/sim" "+hex=$O/prog/D.hex" "+instrucciones=$INSTR" +compartida=1 +limite_codigo=1984 > "$d/D.log" 2>&1
  # L y P: tres programas lineales cada una. Queda el log del primero que falla,
  # o el del último si pasan los tres.
  local g k
  for g in L P; do
    for k in 1 2 3; do
      if [ $g = L ]; then "$d/obj/sim" "+hex=$O/prog/L$k.hex" +instrucciones=3000 +fin_lazo=1 > "$d/$g.log" 2>&1
      else "$d/obj/sim" "+hex=$O/prog/P$k.hex" +instrucciones=400 +fin_lazo=1 +compartida=1 +limite_codigo=1984 > "$d/$g.log" 2>&1; fi
      grep -q "^PASS verif" "$d/$g.log" || break
    done
  done
  echo "OK" > "$d/estado.txt"
}
export -f una compilar_verif soc_barrel
export O T TB SW FO B PYTHON INSTR CELLS_SIM BASE_SRC SRC_SIN_BARREL CORE_V RF_V SOC_V

NOMBRES="$($PYTHON $T/mutar.py --lista) MUTA_CONTEXTO MUTA_BOFF MUTA_ARRANQUE"
if [ "${SOLO_INFORME:-0}" != 1 ]; then
  rm -f "$O"/*/estado.txt "$O"/*/?.log
  echo "referencia $NOMBRES" | tr ' ' '\n' | xargs -P "$JOBS" -I{} bash -c 'una {}'
fi

# detalle NOMBRE: escribe qué comparaciones detectan la mutación; devuelve cuántas
detalle() {
  local m=$1 d=$O/$1 n=0 g
  for g in A H B C D L P; do
    if grep -q "^PASS verif" "$d/$g.log" 2>/dev/null; then
      echo "      $g: no la detecta"
    else
      n=$((n + 1))
      echo "      $g: $(grep -m1 '^FAIL' "$d/$g.log" | sed -E 's/^FAIL verif: //; s/el hilo ([0-9]) difiere del Espino base en su instruccion ([0-9]+) \((.*)\)/hilo \1, instruccion \2: \3/' | cut -c1-140)"
    fi
  done
  return $n
}

{
echo "Controles negativos de la verificacion del Espino barrel"
echo "Generado por tools/barrel/mutaciones.sh (make barrel-mutaciones). No editar a mano."
echo
versiones
echo "  $(verilator --version)"
echo
fallas=0
echo "Sin mutacion: las siete comparaciones deben pasar"
if [ "$(cat "$O/referencia/estado.txt" 2>/dev/null)" != OK ]; then
  echo "FAIL el barrel sin mutar no compila"; fallas=$((fallas + 1))
else
  for g in A H B C D L P; do
    if grep -q "^PASS verif" "$O/referencia/$g.log"; then
      echo "   PASS $g: $(grep '^PASS verif' "$O/referencia/$g.log" | sed -E 's/^PASS verif: //; s/;.*//')"
    else
      echo "   FAIL $g: $(grep -m1 '^FAIL' "$O/referencia/$g.log")"; fallas=$((fallas + 1))
    fi
  done
fi
echo
total=0; detectadas=0; resumen=""
tabla=$($PYTHON $T/mutar.py --tabla)
for m in $NOMBRES; do
  total=$((total + 1))
  case $m in
    MUTA_CONTEXTO) desc="(ifdef del core) El resultado se escribe en el contexto del hilo que esta en X" ;;
    MUTA_BOFF)     desc="(ifdef del core) El dato del load se alinea con la direccion de la instruccion que esta en X" ;;
    MUTA_ARRANQUE) desc="(ifdef del core) Las burbujas del arranque no se anulan" ;;
    *)             desc="$(echo "$tabla" | grep "^$m|" | cut -d'|' -f3) ($(echo "$tabla" | grep "^$m|" | cut -d'|' -f2))" ;;
  esac
  if [ "$(cat "$O/$m/estado.txt" 2>/dev/null)" != OK ]; then
    echo "FAIL $m: la copia mutada no compila (ver $O/$m/verilator.log)"; fallas=$((fallas + 1)); continue
  fi
  det=$(detalle "$m"); n=$?
  if [ $n -gt 0 ]; then
    detectadas=$((detectadas + 1))
    echo "PASS $m: detectada por $n de las 7 comparaciones"
  else
    fallas=$((fallas + 1))
    echo "FAIL $m: NO detectada"
  fi
  echo "      $desc"
  echo "$det"
  # Para el resumen: primera y última instrucción en que difiere, entre las comparaciones
  ins=$(echo "$det" | sed -nE 's/.*instruccion ([0-9]+):.*/\1/p' | sort -n)
  if [ -n "$ins" ]; then rango="$(echo "$ins" | head -1) a $(echo "$ins" | tail -1)"; else rango="en el ciclo 1"; fi
  resumen="$resumen$(printf '   %-22s %d de 7   %s' "$m" "$n" "$rango")"$'\n'
done
echo
echo "Resumen: mutacion, comparaciones que la detectan e instruccion del hilo en que aparece la primera diferencia"
echo "(la menor y la mayor entre las comparaciones que la detectan)"
printf '%s' "$resumen"
echo
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, $detectadas de $total mutaciones detectadas y el barrel sin mutar pasa"
else echo "RESULTADO: FAIL ($detectadas de $total mutaciones detectadas, $fallas problemas)"; fi
} | tee "$M/mutaciones.txt"

grep -q "^RESULTADO: PASS" "$M/mutaciones.txt"
