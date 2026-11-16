# Prototipo de factibilidad del Espino barrel (pieza A).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Cada objetivo deja su salida en mediciones/. Los productos intermedios van a
# build/ (ignorada por git). Se puede correr desde esta carpeta o desde la
# raíz del repositorio con make -C factibilidad/a_barrel.
#
#   make humo       pruebas de humo y controles negativos        mediciones/humo.txt
#   make cpi        CPI y MIPS con el mix de la clase 7           mediciones/cpi.txt
#   make ticks      latencia de la regla base por tick            mediciones/ticks.txt
#   make oficial    testbench oficial sin modificar, 4/4          mediciones/oficial.txt
#   make equiv      regla base en el hilo 0 contra ref/trader.py, mediciones/equiv_ref.txt
#                   20 000 ticks a 0,1 ms y a 1 ms (Verilator)
#   make netlist    simulación de la netlist sintetizada          mediciones/netlist.txt
#   make recursos   celdas, BRAM y fmax en 10 semillas            mediciones/recursos.txt,
#                                                                 desglose.txt y ruta_critica.txt
#   make bitstream  dos bitstreams para la placa, simulados       mediciones/bitstream.txt
#                   desde el .asc (no programa la placa)
#   make todo       todo lo anterior (unos 20 minutos)
#
# Verificación a fondo (segunda parte):
#   make verif             cada hilo contra el Espino base, instrucción por   mediciones/verificacion.txt
#                          instrucción, con programas aleatorios (Verilator)
#   make mutaciones        controles negativos: 21 errores puestos a          mediciones/mutaciones.txt
#                          propósito que la comparación debe detectar
#   make trazas            trazas en modo funcional contra el Espino base     mediciones/trazas.txt
#                          (Icarus, testbenches del repositorio)
#   make spi               sw/trade.s en cada hilo con la maestra del         mediciones/spi_hilos.txt
#                          testbench oficial, solo y con los otros ocupados
#   make netlist-aleatorio netlist contra RTL en los pines, con programas     mediciones/netlist_aleatorio.txt
#                          aleatorios y tráfico SPI
#   make sin-tabla         qué pasa si se carga un programa sin la tabla de   mediciones/sin_tabla.txt
#                          arranque (debe fallar)
#   make formal            propiedades de estructura con SymbiYosys y 9       mediciones/formal.txt
#                          controles negativos (10 segundos)
#   make icebram           cambio del programa dentro del bitstream con       mediciones/icebram.txt
#                          icebram, simulado desde el .asc (no programa la placa)
#   make verificacion      los ocho anteriores (unos 8 minutos)
#   make equiv-ronda1      make equiv más el período de 10 ms (media hora)
#   make equiv-icarus      los 20 000 ticks a 0,1 ms con Icarus, que simula   mediciones/equiv_icarus.txt
#                          con cuatro estados (unos 15 minutos)
#
# Hace falta OSS CAD Suite en el PATH (los scripts
# agregan su carpeta bin al PATH).

.PHONY: todo humo cpi ticks oficial equiv netlist recursos bitstream limpiar \
        verif mutaciones trazas spi netlist-aleatorio sin-tabla formal icebram verificacion equiv-ronda1 equiv-icarus

todo: humo cpi ticks oficial equiv netlist recursos bitstream

humo:
	tools/humo.sh

cpi:
	tools/medir_cpi.sh

ticks:
	tools/medir_ticks.sh

oficial:
	tools/oficial.sh

equiv:
	tools/equiv_ref.sh

netlist:
	tools/netlist.sh

recursos:
	tools/medir_recursos.sh 10

bitstream:
	tools/bitstream.sh

verif:
	tools/verif.sh

mutaciones:
	tools/mutaciones.sh

trazas:
	tools/verif_trazas.sh 12

spi:
	tools/verif_spi.sh

netlist-aleatorio:
	tools/netlist_aleatorio.sh 4

sin-tabla:
	tools/sin_tabla.sh

formal:
	tools/formal.sh

icebram:
	tools/icebram_prueba.sh

verificacion: verif mutaciones trazas spi netlist-aleatorio sin-tabla formal icebram

equiv-ronda1:
	RONDA1=1 tools/equiv_ref.sh

equiv-icarus:
	tools/equiv_icarus.sh

limpiar:
	rm -rf build
