#!/usr/bin/env bash
# spi_7flancos.sh: precios fantasma del esclavo SPI cuando bit_cnt queda en 7
# con CS_n en alto, y su efecto en R1 y en R2 (revisión P10,
# docs/revision_p10.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre tb/p10/tb_p10_spi.sv con sw/fondo.s en tres escenarios (control,
# transacción de 7 flancos, reset que termina a mitad de una transacción),
# con el hardware de R1 y el de R2. Es una prueba de reproducción: informa lo
# que pasa y termina con error si el comportamiento no es el que se espera de
# un esclavo correcto (ningún byte_done con CS_n en alto y ningún disparo del
# vigilante). Con RTL=carpeta se corre sobre otra copia del RTL (la del arreglo
# propuesto).
#
# Uso: tools/p10/spi_7flancos.sh   (o make p10-spi-7flancos)
set -uo pipefail
cd "$(dirname "$0")/../.."
O=build/p10/spi_7flancos
RTL=${RTL:-rtl}
mkdir -p "$O"
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
SRC=$(for f in $RTL/*.v $RTL/espino_core/*.v; do case "$f" in $RTL/00_*) ;; *) printf '%s ' "$f" ;; esac; done)
R1="-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA"
python3 tools/pochoasm.py sw/fondo.s -o "$O/fondo.hex" > /dev/null || exit 1
mal=0
for hw in r1 r2; do
  defs=$R1; [ $hw = r2 ] && defs="$R1 -DESPINO_VIGILANTE"
  for e in 0 1 2; do
    iverilog -g2012 -s tb_p10_spi -o "$O/sim_${hw}_$e" "-DPROGRAMA=\"$O/fondo.hex\"" -DESCENARIO=$e \
      $defs "$CELLS_SIM" $SRC tb/p10/tb_p10_spi.sv > "$O/iverilog_${hw}_$e.log" 2>&1 || { echo "FAIL $hw/$e: no compila"; mal=1; continue; }
    vvp -n "$O/sim_${hw}_$e" > "$O/${hw}_$e.log" 2>&1
    r=$(grep "^RESUMEN" "$O/${hw}_$e.log")
    f=$(echo "$r" | sed -n 's/.*fantasmas=\([0-9]*\).*/\1/p')
    b=$(echo "$r" | sed -n 's/.*boot=\([0-9]*\).*/\1/p')
    if [ "$f" = 0 ] && [ "$b" = 0 ]; then echo "PASS $hw escenario $e: $r"
    else echo "FAIL $hw escenario $e: $r"; mal=1; fi
    grep -E "^(Escenario|El vigilante)" "$O/${hw}_$e.log" | sed 's/^/    /'
  done
done
exit $mal
