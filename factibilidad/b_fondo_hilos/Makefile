# Pieza B del tramo de factibilidad: un gestor por hilo sobre el Espino barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Cada objetivo deja su salida en mediciones/. Los productos intermedios van a
# build/ (ignorada por git). Se puede correr desde esta carpeta o desde la
# raíz del repositorio con make -C factibilidad/b_fondo_hilos.
#
#   make arnes       compila la referencia en C: el arnés de retorno con el     build/arnes
#                    módulo del fondo (factibilidad/retorno, sin modificar)
#   make programa    ensambla sw/fondo.s y cuenta sus palabras por bloque       mediciones/tamano.txt
#   make oficial     testbench oficial sin modificar (Icarus, 2000 ticks):      mediciones/oficial.txt
#                    4/4 y decisiones.csv idéntico al de la referencia
#   make equiv       copia parametrizada del testbench oficial (Verilator):     mediciones/equiv.txt
#                    20 000 ticks de la práctica a 0,1 ms y a 1 ms, y 8 series
#                    sintéticas de familias distintas
#   make estado      estado interno tick a tick contra la traza del módulo en   mediciones/estado.txt
#                    C: espejo de la cuenta, posiciones, puntajes y pesos
#   make ticks       instrucciones por tick de cada hilo, ciclos de respuesta   mediciones/ticks.txt
#                    y barrido de la fase del sondeo
#   make variantes   espejo antes de decidir, un gestor atrasado a propósito    mediciones/variantes.txt
#                    y supervisor que usa lo del tick anterior
#   make retorno     patrimonio de fondo_min contra max_media con el arnés      mediciones/retorno.txt
#                    compilado aquí, y el veredicto que midió el estudio 4B
#   make todo        todo lo anterior (unos 15 minutos)
#   make equiv-ronda1  make equiv más el período de 10 ms (media hora)
#
# Hace falta OSS CAD Suite en ~/herramientas/oss-cad-suite (los scripts
# agregan su carpeta bin al PATH) y gcc.

include ../retorno/nucleo/nucleo.mk

FONDO_C := ../retorno/r4b_fondo/fondo.c

.PHONY: todo arnes programa oficial equiv equiv-ronda1 estado ticks variantes retorno limpiar

todo: arnes programa oficial equiv estado ticks variantes retorno

arnes: build/arnes

build/arnes: $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) $(FONDO_C)
	@mkdir -p build
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) $(FONDO_C) $(NUCLEO_LIBS)

programa:
	tools/tamano.sh

oficial: arnes
	tools/oficial.sh

equiv: arnes
	tools/equiv.sh

equiv-ronda1: arnes
	RONDA1=1 tools/equiv.sh

estado: arnes
	tools/estado.sh

ticks: arnes
	tools/medir_ticks.sh

variantes: arnes
	tools/variantes.sh

retorno: arnes
	tools/retorno.sh

limpiar:
	rm -rf build
