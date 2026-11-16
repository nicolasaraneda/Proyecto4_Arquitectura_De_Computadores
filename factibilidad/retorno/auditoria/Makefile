# Makefile de la auditoría independiente del arnés de retorno.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se corre desde esta carpeta o con make -C factibilidad/retorno/auditoria.
# Lo que compila queda en ../build/auditoria (no se versiona) y las salidas en
# ../mediciones/auditoria_*.
#
#   make contabilidad   cuatro contabilidades con los mismos flujos de órdenes (4 s)
#   make desfase        testbench oficial sin modificar contra el arnés y contra una regla propia (1 min 20 s)
#   make futuro         ninguna estrategia ni rival ve el precio de ejecución (5 s)
#   make series         las series guardadas, por otro camino que la validación original (10 s)
#   make rivales        segunda implementación de los rivales contra el arnés, serie por serie (30 s)
#   make estudio        el evaluador independiente con las semillas 0 y 2 (1 min 15 s)
#   make informe        cifras informadas contra las obtenidas, y tablas de la auditoría
#   make interfaz       el ejemplo mínimo copiado a una carpeta fuera del repositorio, compilado y corrido (5 s)
#   make parada         la vista de parada del arnés contra el evaluador independiente (2 min 40 s)
#   make todo           todo, en orden (5 min 57 s medidos)
#
# contabilidad y desfase necesitan iverilog, vvp y yosys-config en el PATH:
#   export PATH=$$OSS_CAD_SUITE/bin:$$PATH
# Hace falta haber corrido antes `make -C .. series` (las series de build/series).

include ../nucleo/nucleo.mk

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

PYTHON ?= python3
HILOS ?= 6
export HILOS
B := ../build/auditoria
M := ../mediciones
NUCLEO_SIN_MAIN := $(filter-out %/main.c,$(NUCLEO_FUENTES))
EJEMPLOS := ../ejemplo/mi_estrategia.c ../ejemplo/minimo/mia.c
AJENA ?= $(or $(TMPDIR),/tmp)/auditoria_interfaz_$(shell id -u)

.PHONY: todo arnes contabilidad desfase futuro series rivales externos estudio informe interfaz parada

todo: contabilidad desfase futuro series rivales estudio informe interfaz parada

arnes:
	$(MAKE) -C .. arnes

contabilidad: arnes
	cd .. && $(PYTHON) auditoria/contabilidad.py | tee mediciones/auditoria_contabilidad.txt

desfase: arnes
	cd .. && $(PYTHON) auditoria/desfase.py | tee mediciones/auditoria_desfase.txt

# El binario de la prueba es un programa ajeno al núcleo: usa sus fuentes sin
# tocarlos, deja fuera el main.c del arnés y agrega las estrategias de ejemplo.
$(B)/futuro: futuro.c $(NUCLEO_SIN_MAIN) $(NUCLEO_CABECERAS) $(EJEMPLOS)
	@mkdir -p $(B)
	$(NUCLEO_CC) -o $@ futuro.c $(NUCLEO_SIN_MAIN) $(EJEMPLOS) $(NUCLEO_LIBS)

futuro: $(B)/futuro
	$(B)/futuro | tee $(M)/auditoria_futuro.txt

series:
	cd .. && $(PYTHON) auditoria/series_indep.py | tee mediciones/auditoria_series.txt

# El evaluador independiente no usa ningún fuente del núcleo.
$(B)/indep: indep.c
	@mkdir -p $(B)
	$(CC) -O2 -Wall -Wextra -fopenmp -o $@ indep.c -lm

rivales: arnes $(B)/indep
	cd .. && $(PYTHON) auditoria/rivales_indep.py > mediciones/auditoria_rivales.txt
	@head -12 $(M)/auditoria_rivales.txt; tail -1 $(M)/auditoria_rivales.txt

externos: arnes
	cd .. && $(PYTHON) auditoria/externos.py

estudio: $(B)/indep externos
	cd .. && build/auditoria/indep estudio --semilla 0 > build/auditoria/estudio_s0.txt
	cd .. && build/auditoria/indep estudio --semilla 2 > build/auditoria/estudio_s2.txt
	@wc -l $(B)/estudio_s0.txt $(B)/estudio_s2.txt

informe:
	cd .. && $(PYTHON) auditoria/informe.py | tee mediciones/auditoria_informe.txt

# La interfaz, desde una carpeta que no está en el repositorio: se copia solo
# el archivo de la estrategia y se escribe un Makefile de cuatro líneas.
interfaz: arnes
	cd .. && AJENA="$(AJENA)" bash auditoria/interfaz.sh 2>&1 | tee mediciones/auditoria_interfaz.txt

parada: arnes
	cd .. && $(PYTHON) auditoria/parada.py | tee mediciones/auditoria_parada.txt
