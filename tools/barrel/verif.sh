#!/usr/bin/env bash
# verif.sh: verificación del Espino barrel contra el Espino base, instrucción
# por instrucción, con programas aleatorios.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Compila tb/tb_verif.sv con Verilator (una sola vez) y lo corre con muchos
# programas. En cada instrucción completada de cada hilo compara lo que hizo
# el barrel con lo que hizo un Espino base que parte en la entrada de ese hilo:
# contador de programa, instrucción, escritura al banco, acceso al bus, los 16
# registros del contexto y la palabra de memoria o el registro de periférico
# escrito. Ver el encabezado de tb/tb_verif.sv.
#
# Grupos de corridas:
#   A   Un hilo con el programa y los otros tres en un lazo vacío, para cada
#       uno de los cuatro hilos. Programas de tools/prog_aleatorio.py del
#       repositorio (300 instrucciones al azar, sin modificar) con la tabla de
#       arranque delante (tools/barrel/tabla.py). Incluye accesos al SPI y a los
#       periféricos, y cada 97 instrucciones del hilo el testbench deja un
#       precio nuevo en el esclavo SPI. En ese generador un jalr puede salir
#       con una base cualquiera y sacar al programa de la memoria: ahí termina
#       la comparación de esa corrida, porque el contador de programa del
#       barrel tiene 11 bits y el del base 32.
#   W   Los programas del grupo A con el barrel compilado con el contador de
#       programa de 32 bits (-DPCW_BARREL=32): se compara todo, también lo que
#       el programa hace fuera de la memoria.
#   U   Como A, con el generador del barrel (tools/barrel/prog_hilos.py --modo
#       uno): los programas no llegan a un punto fijo ni salen de la memoria.
#   H   sw/hazard_test.s y sw/hazard_review.s (del Proyecto 3, sin modificar)
#       en cada hilo, los otros tres en un lazo vacío.
#   B   Los cuatro hilos a la vez con programas aleatorios distintos y zonas de
#       datos separadas (tools/barrel/prog_hilos.py --modo separado). Los cuatro
#       acceden al SPI y a los periféricos, con el bus SPI quieto.
#   C   Como B, pero solo un hilo accede al SPI y el testbench le deja un
#       precio nuevo cada 29 instrucciones (--modo spi1). Se repite con cada
#       hilo en ese papel.
#   T   Un hilo corre sw/trade.s (sin modificar) y recibe un precio nuevo cada
#       61 instrucciones, mientras los otros tres corren programas aleatorios
#       (--modo trade). Se repite con cada hilo en ese papel.
#   D   Los cuatro hilos leen y escriben la misma zona de datos (--modo
#       compartido), y un jalr puede llevar a un hilo al código de otro. La
#       referencia son los cuatro Espino base ejecutando por turnos con las
#       escrituras copiadas entre ellos (+compartida=1).
#   N   Control: los programas del grupo D con la referencia del grupo B
#       (cada Espino base solo). Tiene que FALLAR: si pasara, los hilos del
#       grupo D no estarían interactuando y la prueba no probaría nada.
#   J   Informativo: programas como los del grupo B pero con el jalr libre del
#       generador del repositorio (--jalr-libre), contra la referencia de
#       hilos aislados. Algunos difieren, porque un hilo cae en el código de
#       otro. No cuenta como falla: deja medido por qué prog_hilos.py no deja
#       que un salto caiga en un jalr.
#   K   Los mismos programas del grupo J con la referencia de memoria
#       compartida. Tienen que pasar todos: la diferencia del grupo J es del
#       método de comparación y no del barrel.
#
# Campaña lineal (criterio 5 de la puerta de simulación, docs/puertas.md). Los
# grupos anteriores repiten para siempre el cuerpo de cada programa, y aunque
# los valores cambian de una vuelta a otra, más de la mitad de lo comparado es
# repetición. En estos cuatro grupos cada programa se ejecuta una sola vez
# (tools/barrel/prog_hilos.py --lineal) y la corrida termina cuando los
# cuatro hilos llegan a su lazo vacío, así que hay muchas corridas cortas con
# programas distintos:
#   L   Como B: cuatro hilos, zonas de datos separadas.
#   M   Como C: un solo hilo con el SPI y un precio nuevo cada 11 instrucciones.
#   P   Como D: cuatro hilos sobre la misma zona de datos, referencia por turnos.
#   Q   Como U: un hilo con un cuerpo de 300 instrucciones y los otros ociosos.
# Las instrucciones distintas de esta campaña se cuentan sobre toda la campaña
# y no por corrida: cada corrida deja sus claves (tb_verif.sv, +claves) y al
# final se cuentan las claves únicas.
#
# Uso: tools/barrel/verif.sh   (o make barrel-verif)
# Variables de entorno:
#   CAMPANA  lazos (los grupos A a K), lineal (L, M, P y Q) o todo (por defecto)
#   GRUPOS   si se define, solo corren esos grupos (por ejemplo "B C L M")
#   PUERTA   con 1 exige además el criterio 5: al menos 5 millones de
#            instrucciones en la campaña lineal y más de 90 % distintas
#   ESCALA   multiplica la cantidad de semillas de cada grupo (por defecto 1;
#            con 0.1 es una corrida corta de unos segundos)
#   JOBS     simulaciones en paralelo (por defecto 5)
#   SALIDA   archivo de resultado (por defecto docs/mediciones/barrel/verificacion.txt)
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/verif
JOBS=${JOBS:-5}
ESCALA=${ESCALA:-1}
SALIDA=${SALIDA:-$M/verificacion.txt}
CAMPANA=${CAMPANA:-todo}
PUERTA=${PUERTA:-0}
mkdir -p "$O"

esc() { $PYTHON -c "import sys; print(max(1, round(float(sys.argv[1]) * float(sys.argv[2]))))" "$1" "$ESCALA"; }
SEM_A=$(esc 50);  INSTR_A=6000      # por hilo: 4 x SEM_A corridas
SEM_B=$(esc 100); INSTR_B=5000
SEM_C=$(esc 25);  INSTR_C=5000      # por hilo con el SPI: 4 x SEM_C corridas
SEM_T=$(esc 10);  INSTR_T=5000      # por hilo con trade.s: 4 x SEM_T corridas
SEM_D=$(esc 100); INSTR_D=5000
SEM_N=$(esc 10)
SEM_J=$(esc 100)
INSTR_H=1500
SEM_L=$(esc 6500)
SEM_M=$(esc 1300)                   # por hilo con el SPI: 4 x SEM_M corridas
SEM_P=$(esc 4500)
SEM_Q=$(esc 1100)                   # por hilo: 4 x SEM_Q corridas
INSTR_L=3000                        # tope por hilo, por si un programa no llega a su lazo vacío
INSTR_P=400                         # en el grupo P un jalr libre puede dejar a un hilo dando vueltas

compilar_verif "$O" &
compilar_verif "$O/pc32" rtl/espino_core/espino_barrel_core.v rtl/espino_core/espino_barrel_regfile.v rtl/pochoco_soc.v -DPCW_BARREL=32 &
wait
for d in "$O" "$O/pc32"; do
  if [ ! -x "$d/obj/sim" ] || grep -q "^%Error" "$d/verilator.log"; then
    echo "FAIL verif: tb_verif no compila (ver $d/verilator.log)"; tail -5 "$d/verilator.log"; exit 1
  fi
done

# una GRUPO SEMILLA HILO: genera el programa, lo ensambla y corre la comparación
una() {
  local g=$1 s=$2 t=$3 d=$O/$1 n=$O/$1/$1_s$2_h$3 args sim=$O/obj/sim
  mkdir -p "$d"
  case $g in
    A|W) $PYTHON tools/prog_aleatorio.py "$s" -o "$n.base.s" && $PYTHON $T/tabla.py "$t" "$n.base.s" > "$n.s"
       args="+instrucciones=$INSTR_A +precio_cada=97 +hilo_spi=$t"
       [ "$g" = W ] && sim=$O/pc32/obj/sim ;;
    U) $PYTHON $T/prog_hilos.py "$s" --modo uno --hilo-spi "$t" -n 300 -o "$n.s"
       args="+instrucciones=$INSTR_A +precio_cada=97 +hilo_spi=$t" ;;
    H) local p=hazard_test; [ "$s" = 2 ] && p=hazard_review
       $PYTHON $T/tabla.py "$t" sw/$p.s > "$n.s"
       args="+instrucciones=$INSTR_H" ;;
    B) $PYTHON $T/prog_hilos.py "$s" --modo separado -o "$n.s"
       args="+instrucciones=$INSTR_B" ;;
    C) $PYTHON $T/prog_hilos.py "$s" --modo spi1 --hilo-spi "$t" -o "$n.s"
       args="+instrucciones=$INSTR_C +precio_cada=29 +hilo_spi=$t" ;;
    T) $PYTHON $T/prog_hilos.py "$s" --modo trade --hilo-spi "$t" --trade sw/trade.s -n 90 -o "$n.s"
       args="+instrucciones=$INSTR_T +precio_cada=61 +hilo_spi=$t" ;;
    D) $PYTHON $T/prog_hilos.py "$s" --modo compartido -o "$n.s"
       args="+instrucciones=$INSTR_D +compartida=1" ;;
    N) $PYTHON $T/prog_hilos.py "$s" --modo compartido -o "$n.s"
       args="+instrucciones=$INSTR_D +compartida=0" ;;
    J) $PYTHON $T/prog_hilos.py "$s" --modo separado --jalr-libre -o "$n.s"
       args="+instrucciones=$INSTR_B +compartida=0" ;;
    K) $PYTHON $T/prog_hilos.py "$s" --modo separado --jalr-libre -o "$n.s"
       args="+instrucciones=$INSTR_B +compartida=1" ;;
    # En la campaña lineal cada corrida usa una semilla del generador que no
    # se repite en otro grupo ni con otro hilo: con la misma semilla dos
    # programas empiezan igual y esas instrucciones no contarían como distintas
    L) $PYTHON $T/prog_hilos.py "$s" --modo separado --lineal -o "$n.s"
       args="+instrucciones=$INSTR_L +fin_lazo=1 +claves=$n.claves" ;;
    M) $PYTHON $T/prog_hilos.py "$((1000000 * (t + 1) + s))" --modo spi1 --hilo-spi "$t" --lineal -o "$n.s"
       args="+instrucciones=$INSTR_L +fin_lazo=1 +precio_cada=11 +hilo_spi=$t +claves=$n.claves" ;;
    P) $PYTHON $T/prog_hilos.py "$((5000000 + s))" --modo compartido --lineal -o "$n.s"
       args="+instrucciones=$INSTR_P +fin_lazo=1 +compartida=1 +claves=$n.claves" ;;
    Q) $PYTHON $T/prog_hilos.py "$((1000000 * (t + 6) + s))" --modo uno --hilo-spi "$t" -n 300 --lineal -o "$n.s"
       args="+instrucciones=$INSTR_L +fin_lazo=1 +precio_cada=31 +hilo_spi=$t +claves=$n.claves" ;;
  esac
  $PYTHON tools/pochoasm.py --allow-shifts "$n.s" -o "$n.hex" > /dev/null 2> "$n.asm.log" \
    && "$sim" "+hex=$n.hex" $args > "$n.log" 2>&1
  # Los programas lineales son muchos y se regeneran con su semilla: si la
  # corrida pasó no se guardan
  case $g in L|M|P|Q) grep -q "^PASS verif" "$n.log" 2>/dev/null && rm -f "$n.s" "$n.hex" "$n.asm.log" ;; esac
  return 0
}
export -f una
export O T TB SW FO PYTHON INSTR_A INSTR_B INSTR_C INSTR_T INSTR_D INSTR_H INSTR_L INSTR_P

: > "$O/corridas.txt"
lista() {   # lista GRUPO SEMILLAS HILOS...: agrega las corridas del grupo
  local g=$1 n=$2; shift 2
  if [ -n "${GRUPOS:-}" ] && ! echo " $GRUPOS " | grep -q " $g "; then return 0; fi
  for t in "$@"; do for s in $(seq 1 "$n"); do echo "$g $s $t" >> "$O/corridas.txt"; done; done
}
if [ "$CAMPANA" != lineal ]; then
  lista A "$SEM_A" 0 1 2 3
  lista W "$SEM_A" 0 1 2 3
  lista U "$SEM_A" 0 1 2 3
  lista H 2 0 1 2 3
  lista B "$SEM_B" x
  lista C "$SEM_C" 0 1 2 3
  lista T "$SEM_T" 0 1 2 3
  lista D "$SEM_D" x
  lista N "$SEM_N" x
  lista J "$SEM_J" x
  lista K "$SEM_J" x
fi
if [ "$CAMPANA" != lazos ]; then
  rm -rf "$O/L" "$O/M" "$O/P" "$O/Q"
  lista L "$SEM_L" x
  lista M "$SEM_M" 0 1 2 3
  lista P "$SEM_P" x
  lista Q "$SEM_Q" 0 1 2 3
fi

inicio=$(date +%s)
xargs -P "$JOBS" -L 1 bash -c 'una "$0" "$1" "$2"' < "$O/corridas.txt"
fin=$(date +%s)

# Claves únicas de la campaña lineal (instrucciones distintas en toda la campaña)
UNICAS=0
if [ "$CAMPANA" != lazos ]; then
  mkdir -p "$O/L" "$O/M" "$O/P" "$O/Q"
  UNICAS=$(find "$O/L" "$O/M" "$O/P" "$O/Q" -name '*.claves' -print0 | xargs -0 -r cat | LC_ALL=C sort -u -S 1G | wc -l)
  find "$O/L" "$O/M" "$O/P" "$O/Q" -name '*.claves' -delete
fi

{
echo "Verificacion del Espino barrel contra el Espino base, instruccion por instruccion"
echo "Generado por tools/barrel/verif.sh (make barrel-verif). No editar a mano."
echo
versiones
echo "  $(verilator --version)"
echo
$PYTHON $T/resumen_verif.py "$O" "$O/corridas.txt" "$UNICAS" "$PUERTA"
rc=$?
echo
echo "Tiempo de las simulaciones: $((fin - inicio)) s con $JOBS procesos."
exit $rc
} | tee "$SALIDA"
exit "${PIPESTATUS[0]}"
