#!/usr/bin/env bash
# formal_spi.sh: propiedad formal del esclavo SPI, "un precio solo se completa
# con CS_n en bajo" (revisión P10, docs/revision_p10.md, hallazgo 1).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre SymbiYosys sobre formal/p10/spi_byte.v (envoltorio con las entradas
# libres) y el esclavo de RTL/pochoco_spi_slave.v, en dos tareas: prueba por
# inducción (prove) y alcanzabilidad de un precio normal (cover). Con el RTL de
# main la prueba falla y deja el contraejemplo en
# build/p10/formal_spi/spi_prove/engine_0/trace.vcd: es la reproducción formal
# del hallazgo. Con RTL=build/p10/wt1/rtl (rama p10-arreglo-1) pasa.
#
# Uso: tools/p10/formal_spi.sh   (o make p10-formal-spi). Variables: RTL y O
# (carpeta de trabajo, por defecto build/p10/formal_spi). Termina con error si
# la prueba no pasa.
set -uo pipefail
cd "$(dirname "$0")/../.."
RAIZ=$(pwd)
RTL=${RTL:-rtl}
case $RTL in /*) ;; *) RTL=$RAIZ/$RTL ;; esac
O=${O:-build/p10/formal_spi}
rm -rf "$O"; mkdir -p "$O"
cat > "$O/spi.sby" <<EOF
[tasks]
prove
cover

[options]
prove: mode prove
prove: depth 40
cover: mode cover
cover: depth 40

[engines]
smtbmc yices

[script]
read_verilog -formal pochoco_spi_slave.v
read_verilog -formal spi_byte.v
prep -top spi_byte

[files]
$RTL/pochoco_spi_slave.v
$RAIZ/formal/p10/spi_byte.v
EOF
( cd "$O" && sby -f spi.sby > sby.log 2>&1 )
mal=0
for t in prove cover; do
  if [ -f "$O/spi_$t/PASS" ]; then echo "PASS $t ($RTL/pochoco_spi_slave.v)"
  else
    echo "FAIL $t ($RTL/pochoco_spi_slave.v)"; mal=1
    grep -hE "Assert failed|failed assertion|Writing trace" "$O/spi_$t/logfile.txt" | head -4 | sed 's/^/    /'
  fi
done
exit $mal
