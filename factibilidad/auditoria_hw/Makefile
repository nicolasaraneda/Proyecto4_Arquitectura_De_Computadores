# Auditoría de hardware: diseño integrado (factibilidad/i_integrado) y fondo
# de cuatro hilos (factibilidad/b_fondo_hilos).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Cada objetivo deja su salida en mediciones/. Los productos intermedios van a
# build/ de esta carpeta (ignorada por git), salvo los logs de nextpnr, que
# tools/medir_variante.sh del repositorio deja en
# build/variantes/fact2_auditoria_hw_* de la raíz. Se puede correr desde esta
# carpeta o desde la raíz con make -C factibilidad/auditoria_hw.
#
#   make recursos     celdas, BRAM y fmax de I1, I2 e I3 en 20 semillas,     mediciones/recursos.txt
#                     con nextpnr y con icetime (6 minutos)
#   make oficial      testbench oficial sin modificar con I1, I2 e I3 y      mediciones/oficial.txt
#                     con el fondo cargado en el hardware I1 (6 minutos)
#   make equiv        el fondo contra la referencia en C con series y        mediciones/equiv.txt
#                     semillas nuevas, sobre el barrel y sobre I1 (4 minutos)
#   make mutaciones   errores nuevos puestos a propósito en la integración   mediciones/mutaciones.txt
#                     de la extensión, en el vigilante y en el protocolo
#   make carreras     retardos y fase de llegada al azar, monitores del      mediciones/carreras.txt
#                     protocolo y referencia sobre los precios vistos
#   make cuelgue      un gestor colgado: el supervisor deja de responder     mediciones/cuelgue.txt
#                     y el vigilante de I1 dispara
#   make integridad   git status y git diff: nada versionado cambió fuera    mediciones/integridad.txt
#                     de factibilidad/ y el testbench oficial está intacto
#   make reglas       reglas del enunciado para el fondo en un chip          mediciones/reglas.txt
#   make todo         todo lo anterior (unos 20 minutos)
#   make repeticion   vuelve a correr los objetivos de las dos piezas y      mediciones/repeticion.txt
#                     compara con sus salidas guardadas (20 minutos; no
#                     está en make todo)
#
# Hace falta OSS CAD Suite en ~/herramientas/oss-cad-suite (los scripts
# agregan su carpeta bin al PATH) y gcc. Cada script usa a lo más 5 procesos.

include ../retorno/nucleo/nucleo.mk

FONDO_C := ../retorno/r4b_fondo/fondo.c

.PHONY: todo recursos oficial equiv mutaciones carreras cuelgue integridad reglas repeticion limpiar

todo: recursos oficial equiv mutaciones carreras cuelgue integridad reglas

build/arnes: $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) $(FONDO_C)
	@mkdir -p build
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) $(FONDO_C) $(NUCLEO_LIBS)

recursos:
	tools/recursos.sh

oficial: build/arnes
	tools/oficial.sh

equiv: build/arnes
	tools/equiv.sh

mutaciones: build/arnes
	tools/mutaciones.sh

carreras: build/arnes
	tools/carreras.sh

cuelgue:
	tools/cuelgue.sh

integridad:
	tools/integridad.sh

reglas:
	tools/reglas.sh

repeticion:
	tools/repeticion.sh

limpiar:
	rm -rf build
