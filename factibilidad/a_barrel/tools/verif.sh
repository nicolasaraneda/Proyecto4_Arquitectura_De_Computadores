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
#       arranque delante (tools/tabla.py). Incluye accesos al SPI y a los
#       periféricos, y cada 97 instrucciones del hilo el testbench deja un
#       precio nuevo en el esclavo SPI. En ese generador un jalr puede salir
#       con una base cualquiera y sacar al programa de la memoria: ahí termina
#       la comparación de esa corrida, porque el contador de programa del
#       barrel tiene 11 bits y el del base 32.
#   W   Los programas del grupo A con el barrel compilado con el contador de
#       programa de 32 bits (-DPCW_BARREL=32): se compara todo, también lo que
#       el programa hace fuera de la memoria.
#   U   Como A, con el generador del prototipo (tools/prog_hilos.py --modo
#       uno): los programas no llegan a un punto fijo ni salen de la memoria.
#   H   sw/hazard_test.s y sw/hazard_review.s (del Proyecto 3, sin modificar)
#       en cada hilo, los otros tres en un lazo vacío.
#   B   Los cuatro hilos a la vez con programas aleatorios distintos y zonas de
#       datos separadas (tools/prog_hilos.py --modo separado). Los cuatro
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
# Uso: factibilidad/a_barrel/tools/verif.sh   (o make verif en esa carpeta)
# Variables de entorno:
#   ESCALA   multiplica la cantidad de semillas de cada grupo (por defecto 1;
#            con 0.1 es una corrida corta de unos segundos)
#   JOBS     simulaciones en paralelo (por defecto 5)
#   SALIDA   archivo de resultado (por defecto mediciones/verificacion.txt)
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/verif
JOBS=${JOBS:-5}
ESCALA=${ESCALA:-1}
SALIDA=${SALIDA:-$M/verificacion.txt}
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

compilar_verif "$O" &
compilar_verif "$O/pc32" $A/rtl/espino_barrel_core.v $A/rtl/espino_barrel_regfile.v $A/rtl/pochoco_soc.v -DPCW_BARREL=32 &
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
    A|W) $PYTHON tools/prog_aleatorio.py "$s" -o "$n.base.s" && $PYTHON $A/tools/tabla.py "$t" "$n.base.s" > "$n.s"
       args="+instrucciones=$INSTR_A +precio_cada=97 +hilo_spi=$t"
       [ "$g" = W ] && sim=$O/pc32/obj/sim ;;
    U) $PYTHON $A/tools/prog_hilos.py "$s" --modo uno --hilo-spi "$t" -n 300 -o "$n.s"
       args="+instrucciones=$INSTR_A +precio_cada=97 +hilo_spi=$t" ;;
    H) local p=hazard_test; [ "$s" = 2 ] && p=hazard_review
       $PYTHON $A/tools/tabla.py "$t" sw/$p.s > "$n.s"
       args="+instrucciones=$INSTR_H" ;;
    B) $PYTHON $A/tools/prog_hilos.py "$s" --modo separado -o "$n.s"
       args="+instrucciones=$INSTR_B" ;;
    C) $PYTHON $A/tools/prog_hilos.py "$s" --modo spi1 --hilo-spi "$t" -o "$n.s"
       args="+instrucciones=$INSTR_C +precio_cada=29 +hilo_spi=$t" ;;
    T) $PYTHON $A/tools/prog_hilos.py "$s" --modo trade --hilo-spi "$t" --trade sw/trade.s -n 90 -o "$n.s"
       args="+instrucciones=$INSTR_T +precio_cada=61 +hilo_spi=$t" ;;
    D) $PYTHON $A/tools/prog_hilos.py "$s" --modo compartido -o "$n.s"
       args="+instrucciones=$INSTR_D +compartida=1" ;;
    N) $PYTHON $A/tools/prog_hilos.py "$s" --modo compartido -o "$n.s"
       args="+instrucciones=$INSTR_D +compartida=0" ;;
    J) $PYTHON $A/tools/prog_hilos.py "$s" --modo separado --jalr-libre -o "$n.s"
       args="+instrucciones=$INSTR_B +compartida=0" ;;
    K) $PYTHON $A/tools/prog_hilos.py "$s" --modo separado --jalr-libre -o "$n.s"
       args="+instrucciones=$INSTR_B +compartida=1" ;;
  esac
  $PYTHON tools/pochoasm.py --allow-shifts "$n.s" -o "$n.hex" > /dev/null 2> "$n.asm.log" \
    && "$sim" "+hex=$n.hex" $args > "$n.log" 2>&1
  return 0
}
export -f una
export O A PYTHON INSTR_A INSTR_B INSTR_C INSTR_T INSTR_D INSTR_H

: > "$O/corridas.txt"
lista() {   # lista GRUPO SEMILLAS HILOS...: agrega las corridas del grupo
  local g=$1 n=$2; shift 2
  for t in "$@"; do for s in $(seq 1 "$n"); do echo "$g $s $t" >> "$O/corridas.txt"; done; done
}
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

inicio=$(date +%s)
xargs -P "$JOBS" -L 1 bash -c 'una "$0" "$1" "$2"' < "$O/corridas.txt"
fin=$(date +%s)

{
echo "Verificacion del Espino barrel contra el Espino base, instruccion por instruccion"
echo "Generado por factibilidad/a_barrel/tools/verif.sh (make verif). No editar a mano."
echo
versiones
echo "  $(verilator --version)"
echo
$PYTHON $A/tools/resumen_verif.py "$O" "$O/corridas.txt"
rc=$?
echo
echo "Tiempo de las simulaciones: $((fin - inicio)) s con $JOBS procesos."
exit $rc
} | tee "$SALIDA"
exit "${PIPESTATUS[0]}"
