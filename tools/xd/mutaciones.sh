#!/usr/bin/env bash
# mutaciones.sh: controles negativos de la verificación por simulación de la
# extensión de la ISA.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Rompe la extensión a propósito, de una forma distinta cada vez (los `ifdef
# MUTA_XD_* de rtl/espino_core/espino_xd.v y espino_barrel_core.v), y exige que
# la comparación contra el Espino base con la especificación
# (tb/barrel/tb_verif.sv) lo note. Es el método de tools/barrel/mutaciones.sh.
# Con cada core mutado se corren seis comparaciones cortas, con programas que
# usan la extensión (tools/barrel/prog_hilos.py --xd 7):
#   U  un hilo (el 2) con el programa y los demás ociosos
#   B  cuatro hilos, zonas de datos separadas
#   C  cuatro hilos, el hilo 1 con el SPI y precios nuevos
#   D  cuatro hilos sobre la misma zona de datos
#   L  programas lineales, zonas separadas: 3 programas
#   P  programas lineales sobre la misma zona de datos: 3 programas
# Termina bien solo si el core sin mutar pasa las seis y cada mutación es
# detectada por al menos una. Las mismas mutaciones se prueban además con la
# prueba formal (tools/xd/formal.sh) y, las de espino_xd.v, con el testbench de
# los módulos (tools/xd/tb_modulos.sh).
#
# Uso: tools/xd/mutaciones.sh   (o make xd-mutaciones)
# Resultado en docs/mediciones/xd/mutaciones.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BX/mutaciones
JOBS=${JOBS:-5}
INSTR=${INSTR:-3000}
NOMBRES="MUTA_XD_K MUTA_XD_F7MUL MUTA_XD_SRL MUTA_XD_K4 MUTA_XD_BCERO MUTA_XD_WE MUTA_XD_HILO MUTA_XD_ANULA MUTA_XD_SUMA"
GRUPOS="U B C D L P"
mkdir -p "$O/prog"

G="$PYTHON $T/prog_hilos.py --xd 7"
$G 1 --modo uno --hilo-spi 2 -n 300 -o "$O/prog/U.s"
$G 1 --modo separado -o "$O/prog/B.s"
$G 1 --modo spi1 --hilo-spi 1 -o "$O/prog/C.s"
$G 1 --modo compartido -o "$O/prog/D.s"
for k in 1 2 3; do
  $G $k --modo separado --lineal -o "$O/prog/L$k.s"
  $G $((5000000 + k)) --modo compartido --lineal -o "$O/prog/P$k.s"
done
for g in U B C D L1 L2 L3 P1 P2 P3; do ensamblar "$O/prog/$g.s" "$O/prog/$g.hex" --allow-shifts || { echo "FAIL mutaciones: no ensambla $g"; exit 1; }; done

una() {
  local m=$1 d=$O/$1 def=""
  mkdir -p "$d"
  [ "$m" != referencia ] && def="-D$m"
  VERIF_OPT="-O1 -CFLAGS -O0" compilar_verif "$d" "$CORE_V" "$RF_V" "$SOC_V" -DESPINO_XD $def
  if [ $? -ne 0 ] || [ ! -x "$d/obj/sim" ]; then echo "NO_COMPILA" > "$d/estado.txt"; return 0; fi
  "$d/obj/sim" "+hex=$O/prog/U.hex" "+instrucciones=$INSTR" +precio_cada=97 +hilo_spi=2 > "$d/U.log" 2>&1
  "$d/obj/sim" "+hex=$O/prog/B.hex" "+instrucciones=$INSTR"                              > "$d/B.log" 2>&1
  "$d/obj/sim" "+hex=$O/prog/C.hex" "+instrucciones=$INSTR" +precio_cada=29 +hilo_spi=1 > "$d/C.log" 2>&1
  "$d/obj/sim" "+hex=$O/prog/D.hex" "+instrucciones=$INSTR" +compartida=1 +limite_codigo=1984 > "$d/D.log" 2>&1
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

rm -f "$O"/*/estado.txt "$O"/*/?.log
echo "referencia $NOMBRES" | tr ' ' '\n' | xargs -P "$JOBS" -I{} bash -c 'una {}'

desc() {
  case $1 in
    MUTA_XD_K)     echo "espino_xd_dec no revisa k: emad y devk con cualquier k se ejecutan con k = 5" ;;
    MUTA_XD_F7MUL) echo "espino_xd_dec no revisa funct7 en mulstep" ;;
    MUTA_XD_SRL)   echo "espino_xd_opa: el desplazamiento a la derecha de emad es logico" ;;
    MUTA_XD_K4)    echo "espino_xd_opa: devk desplaza 4 en vez de 5" ;;
    MUTA_XD_BCERO) echo "espino_xd_opa: mulstep suma rs2 siempre" ;;
    MUTA_XD_WE)    echo "core: las instrucciones nuevas no escriben rd" ;;
    MUTA_XD_HILO)  echo "core: espino_xd_opa recibe el funct3 de la instruccion que sale de la memoria (de otro hilo)" ;;
    MUTA_XD_ANULA) echo "core: el operando B se anula con rs1[31] = 0 en cualquier instruccion, no solo en mulstep" ;;
    MUTA_XD_SUMA)  echo "core: devk suma en vez de restar" ;;
  esac
}

{
echo "Controles negativos de la verificacion por simulacion de la extension de la ISA"
echo "Generado por tools/xd/mutaciones.sh (make xd-mutaciones). No editar a mano."
echo
versiones
echo "  $(verilator --version)"
echo
fallas=0
echo "Sin mutacion: las seis comparaciones deben pasar"
if [ "$(cat "$O/referencia/estado.txt" 2>/dev/null)" != OK ]; then
  echo "FAIL el core sin mutar no compila"; fallas=$((fallas + 1))
else
  for g in $GRUPOS; do
    if grep -q "^PASS verif" "$O/referencia/$g.log"; then
      echo "   PASS $g: $(grep '^PASS verif' "$O/referencia/$g.log" | sed -E 's/^PASS verif: //; s/;.*//')"
    else
      echo "   FAIL $g: $(grep -m1 '^FAIL' "$O/referencia/$g.log")"; fallas=$((fallas + 1))
    fi
  done
fi
echo
total=0; detectadas=0
for m in $NOMBRES; do
  total=$((total + 1))
  if [ "$(cat "$O/$m/estado.txt" 2>/dev/null)" != OK ]; then
    echo "FAIL $m: no compila (ver $O/$m/verilator.log)"; fallas=$((fallas + 1)); continue
  fi
  n=0; det=""
  for g in $GRUPOS; do
    if grep -q "^PASS verif" "$O/$m/$g.log" 2>/dev/null; then det="$det      $g: no la detecta"$'\n'
    else n=$((n + 1)); det="$det      $g: $(grep -m1 '^FAIL' "$O/$m/$g.log" | sed -E 's/^FAIL verif: //; s/el hilo ([0-9]) difiere del Espino base en su instruccion ([0-9]+) \((.*)\)/hilo \1, instruccion \2: \3/' | cut -c1-140)"$'\n'; fi
  done
  if [ $n -gt 0 ]; then detectadas=$((detectadas + 1)); echo "PASS $m: detectada por $n de las 6 comparaciones"
  else fallas=$((fallas + 1)); echo "FAIL $m: NO detectada"; fi
  echo "      $(desc $m)"
  printf '%s' "$det"
done
echo
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, $detectadas de $total mutaciones detectadas y el core sin mutar pasa"
else echo "RESULTADO: FAIL ($detectadas de $total mutaciones detectadas, $fallas problemas)"; fi
} | tee "$MX/mutaciones.txt"

grep -q "^RESULTADO: PASS" "$MX/mutaciones.txt"
