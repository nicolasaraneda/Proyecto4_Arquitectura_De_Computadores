# Makefile de la pieza D: extensión de la ISA en custom-0 (estudio de factibilidad).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se usa desde esta carpeta (factibilidad/d_isa). Cada objetivo deja su
# salida en mediciones/ y los productos intermedios en build/. Las
# herramientas de OSS CAD Suite se toman del PATH o de $(OSS_CAD_SUITE).
#
#   make tb               testbench de cada módulo contra ref/xd.py, con mutaciones (3 min)
#   make tb-core          las instrucciones dentro del core, base y segmentado (2 min)
#   make tb-core-recomendado  200 programas por core para emad, devk y mulstep en la ALU (4 min)
#   make formal           pruebas formales con sby (2 min)
#   make sin-cambios      formal: la extensión no cambia las instrucciones de RV32E (10 s)
#   make costo-suelto     LUT4 de cada módulo suelto (1 min)
#   make costo-integrado  celdas y fmax en 10 semillas de cada variante (unos 15 min, 5 procesos)
#   make medir-ticks      trade.s con las instrucciones: equivalencia y ciclos por tick (10 min)
#   make equiv-combinaciones  las combinaciones que caben, por el testbench oficial (3 min)
#   make kernel           kernel de cuatro bandas, escalar contra carriles (10 s)
#   make contabilidad     anchos y contabilidad propia con mulstep y divstep (5 s)
#   make amdahl           predicho contra medido y escalera (lee las mediciones guardadas)
#   make tabla            tabla de codificaciones
#   make ejemplos         un ejemplo numérico de cada instrucción (los de ESPECIFICACION.md)
#   make rapido           tb en modo rápido, tb-core con 2 programas, formal, kernel y contabilidad
#   make todo             todo lo anterior salvo rapido

OSS_CAD_SUITE ?=
export PATH := $(if $(OSS_CAD_SUITE),$(OSS_CAD_SUITE)/bin:)$(PATH)
SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c
M := mediciones

.PHONY: tb tb-rapido tb-core tb-core-recomendado formal sin-cambios equiv-combinaciones costo-suelto costo-integrado medir-ticks kernel contabilidad \
        amdahl tabla ejemplos sw rapido todo clean

tb:
	@mkdir -p $(M)
	tools/tb_modulos.sh | tee $(M)/tb_modulos.txt

tb-rapido:
	tools/tb_modulos.sh rapido

# NPROG programas al azar por variante y por core
NPROG ?= 6
tb-core:
	@mkdir -p $(M)
	tools/tb_core.sh $(NPROG) | tee $(M)/tb_core.txt

# Más programas para el subconjunto recomendado: emad, devk y mulstep en el sumador de la ALU
NPROG_REC ?= 200
tb-core-recomendado:
	@mkdir -p $(M)
	tools/tb_core.sh $(NPROG_REC) '^(emad_k5|media_k5|media_mul)$$' | tee $(M)/tb_core_recomendado.txt

formal:
	@mkdir -p $(M)
	tools/formal.sh > $(M)/formal.txt; r=$$?; cat $(M)/formal.txt; exit $$r

sin-cambios:
	@mkdir -p $(M)
	tools/core_sin_cambios.sh > $(M)/core_sin_cambios.txt; r=$$?; cat $(M)/core_sin_cambios.txt; exit $$r

costo-suelto:
	@mkdir -p $(M)
	tools/costo_suelto.sh > $(M)/costo_suelto.txt
	@cat $(M)/costo_suelto.txt

# FILTRO: expresión regular sobre la etiqueta, para medir solo algunas variantes
# (en ese caso la salida va a la pantalla y no pisa la tabla completa)
costo-integrado:
	@mkdir -p $(M)
ifdef FILTRO
	tools/costo_integrado.sh '$(FILTRO)'
else
	tools/costo_integrado.sh > $(M)/costo_integrado.txt
	@cat $(M)/costo_integrado.txt
endif

medir-ticks:
	@mkdir -p $(M)
	tools/medir_xd.sh > $(M)/ticks_xd.txt; r=$$?; cat $(M)/ticks_xd.txt; exit $$r

equiv-combinaciones:
	@mkdir -p $(M)
	tools/equiv_combinaciones.sh > $(M)/equiv_combinaciones.txt; r=$$?; cat $(M)/equiv_combinaciones.txt; exit $$r

kernel:
	@mkdir -p $(M)
	tools/medir_kernel.sh > $(M)/kernel_bandas.txt; r=$$?; cat $(M)/kernel_bandas.txt; exit $$r

contabilidad:
	@mkdir -p $(M)
	python3 tools/contabilidad.py > $(M)/contabilidad.txt
	@cat $(M)/contabilidad.txt

amdahl:
	python3 tools/amdahl.py > $(M)/amdahl.txt
	@cat $(M)/amdahl.txt

tabla:
	@mkdir -p $(M)
	python3 ref/xd.py --tabla > $(M)/codificacion.txt
	@cat $(M)/codificacion.txt

ejemplos:
	@mkdir -p $(M)
	python3 tools/ejemplos.py > $(M)/ejemplos.txt
	@cat $(M)/ejemplos.txt

# Los programas de sw/ con las instrucciones nuevas pasadas a .word, y ensamblados
sw:
	@mkdir -p build/sw
	@for f in sw/*.s; do n=$$(basename $$f .s); \
	  python3 tools/xd_word.py --pre $$f -o build/sw/$$n.s && \
	  python3 ../../tools/pochoasm.py build/sw/$$n.s -o build/sw/$$n.hex; done

rapido:
	tools/tb_modulos.sh rapido
	tools/tb_core.sh 2
	TIEMPO=120 tools/formal.sh
	tools/medir_kernel.sh
	python3 tools/contabilidad.py | tail -12

todo: tabla ejemplos tb tb-core tb-core-recomendado formal sin-cambios costo-suelto contabilidad kernel medir-ticks equiv-combinaciones costo-integrado amdahl

clean:
	rm -rf build
