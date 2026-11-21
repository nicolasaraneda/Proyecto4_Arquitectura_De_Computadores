#!/usr/bin/env bash
# ticks.sh: mediciones por tick de R3 (punto 3.2 del enunciado): IC, ciclos, CPI y
# tiempo, promedio y peor caso, por hilo, y los hitos del tick.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Serie Meta (data/practica_meta.csv) con el timing del testbench oficial, a los
# períodos de la ronda 3 (20 000 ticks) y de la ronda 2 (3000 ticks), medida con
# tb/c1/tb_c1.sv y Verilator. También deja el tamaño del programa por bloque.
#
# Telemetría: los 7 segmentos muestran, en hexadecimal, un byte de la cuenta que
# emula el hilo 3, elegido con los cuatro botones (0 a 15): patrimonio propio (bytes
# 0 a 2) y modo (byte 3), caja (4 a 7), acciones (8 a 11) y caja del clon (12 a 15).
# Se corre una ventana con cada una de las 16 combinaciones y se compara el byte
# mostrado al cerrar cada tick con el de la referencia. El LED 1 es el modo seguro
# (se compara en todas las corridas de todas las pruebas).
#
# Uso: tools/c1/ticks.sh   (make c1-ticks)
# Resultado en docs/mediciones/c1/ticks.txt y tamano.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BC/ticks
mkdir -p "$O"
ensamblar_c1 || { echo "FAIL: no ensambla"; exit 1; }
compilar_sim || exit 1
{
cabecera "Tamano de sw/c1.s por bloque, en palabras de 32 bits" tools/c1/ticks.sh "make c1-ticks"
$PYTHON - <<'PY'
import sys
sys.path[:0] = ["tools/fondo"]
import simbolos
e, palabras = simbolos.ensamblar("sw/c1.s")
s = e.simbolos
datos = s["D_PUB"] // 4
codigo = max(i for i in range(datos) if palabras[i]) + 1
bloques = [("tabla de arranque", 0), ("hilo 0: corredor", s["hilo0"]), ("lazo de un hilo muerto", s["muerto"]),
           ("hilo 1: regimen y reloj", s["hilo1"]), ("hilo 2: politica (tablas)", s["hilo2"]),
           ("hilo 3: cuentas, D, modos y telemetria", s["hilo3"]), ("rutina ejecutar (contabilidad oficial)", s["ejecutar"]),
           ("rutina producto", s["producto"]), ("(fin del codigo)", 4 * codigo)]
for (nombre, ini), (_, fin) in zip(bloques, bloques[1:]):
    print(f"  {nombre:42s} {(fin - ini) // 4:4d}")
print(f"  {'datos (desde 0x%03x)' % (4 * datos):42s} {512 - datos:4d}")
print()
print(f"Codigo: {codigo} palabras. Datos: {512 - datos} palabras. Total {codigo + 512 - datos} de 512 "
      f"({100 * (codigo + 512 - datos) / 512:.1f} %). Libres entre el codigo y los datos: {datos - codigo}.")
PY
} | tee "$MC/tamano.txt"
caso "$O/ronda3" --serie data/practica_meta.csv --nticks 20000 --medir &
caso "$O/ronda2" --serie data/practica_meta.csv --nticks 3000 --periodo-ns 1000000 --medir &
wait
MOT=$(meta_ventana 250 2600)
for b in $(seq 0 15); do echo "caso $O/botones_$b --serie $MOT --nticks 2600 --inicio-ns 200000 --botones $b"; done | en_paralelo
{
cabecera "Mediciones por tick de R3 (C1 en los cuatro hilos)" tools/c1/ticks.sh "make c1-ticks"
echo "=== Ronda 3: periodo de 0,1 ms, 20 000 ticks de la serie Meta (data/practica_meta.csv) ==="
cat "$O/ronda3/resultado.txt"
echo
echo "=== Ronda 2: periodo de 1 ms, 3000 ticks de la serie Meta ==="
cat "$O/ronda2/resultado.txt"
echo
echo "=== Telemetria: el byte de los 7 segmentos con cada combinacion de botones, 2600 ticks de una ventana con motor y candado ==="
n=0; for b in $(seq 0 15); do grep -q "^PASS" "$O/botones_$b/resultado.txt" && n=$((n + 1)) || cat "$O/botones_$b/resultado.txt"; done
if [ $n = 16 ]; then echo "PASS: con las 16 combinaciones de botones el byte mostrado es el de la referencia en cada tick (patrimonio y modo, caja, acciones, caja del clon)"
else echo "FAIL: pasan $n de 16 combinaciones de botones"; fi
} | tee "$MC/ticks.txt"
cierre "$MC/ticks.txt"
