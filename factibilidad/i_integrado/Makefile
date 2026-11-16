# Diseño integrado: la extensión de la ISA, el vigilante y la memoria para la
# tabla de política sobre el Espino barrel, y las configuraciones candidatas.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Cada objetivo deja su salida en mediciones/. Los productos intermedios van a
# build/ de esta carpeta (ignorada por git), salvo los logs de nextpnr, que
# tools/medir_variante.sh del repositorio deja en build/variantes/fact2_i_* de
# la raíz. Se puede correr desde esta carpeta o desde la raíz con
# make -C factibilidad/i_integrado.
#
#   make recursos         celdas, BRAM y fmax en 10 semillas de     mediciones/recursos.txt
#                         las 38 variantes (6 minutos)
#   make tb-xd            instrucciones nuevas en los cuatro hilos  mediciones/tb_xd.txt
#                         contra el modelo de d_isa (2 minutos)
#   make oficial          testbench oficial sin modificar en 21     mediciones/oficial.txt
#                         configuraciones (11 minutos)
#   make verif            cada hilo contra el Espino base, RV32E,   mediciones/verif_rv32e.txt
#                         en 6 configuraciones (1 minuto)
#   make mixto            regla base en el hilo 0 con el testbench  mediciones/mixto.txt
#                         oficial y tres hilos con instrucciones
#                         nuevas (5 minutos)
#   make tabla-vigilante  memoria de la tabla y vigilante sobre el  mediciones/tabla_vigilante.txt
#                         barrel (menos de un minuto)
#   make mutaciones       18 errores puestos a propósito que las    mediciones/mutaciones.txt
#                         pruebas deben detectar (2 minutos)
#   make formal           propiedades de estructura del barrel      mediciones/formal.txt
#                         sobre el core con la extensión, con
#                         SymbiYosys (menos de un minuto)
#   make bitstreams       bitstream y sha256 de I1 a I4, simulados  mediciones/bitstreams.txt
#                         desde el .asc (10 minutos). Necesita
#                         make recursos. No programa la placa.
#   make todo             todo lo anterior, en ese orden (unos 40 minutos)
#   make rapido           versión corta de las pruebas, sin escribir en mediciones/
#
# Hace falta OSS CAD Suite en el PATH (los scripts
# agregan su carpeta bin al PATH). Cada script usa a lo más 5 procesos.

.PHONY: todo recursos tb-xd oficial verif mixto tabla-vigilante mutaciones formal bitstreams rapido limpiar

todo: recursos tb-xd oficial verif mixto tabla-vigilante mutaciones formal bitstreams

recursos:
	tools/medir.sh

tb-xd:
	tools/tb_xd.sh 200 10

oficial:
	tools/oficial.sh

verif:
	tools/verif_rv32e.sh

mixto:
	tools/mixto.sh

tabla-vigilante:
	tools/tabla_vigilante.sh

mutaciones:
	tools/mutaciones.sh

formal:
	tools/formal.sh

bitstreams:
	tools/bitstreams.sh

rapido:
	tools/tb_xd.sh 5 1 'media_mul|alu_todo_div|i1a'
	ESCALA=0.2 tools/verif_rv32e.sh 'media_mul|i1a'

limpiar:
	rm -rf build
