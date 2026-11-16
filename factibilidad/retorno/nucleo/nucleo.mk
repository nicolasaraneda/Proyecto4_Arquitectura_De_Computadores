# nucleo.mk: cómo compilar un binario contra el núcleo del arnés de retorno.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye desde el Makefile de quien quiera agregar estrategias:
#
#   include ../retorno/nucleo/nucleo.mk          (o la ruta que corresponda)
#   build/mi_binario: $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) mi_estrategia.c
#   	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) mi_estrategia.c $(NUCLEO_LIBS)
#
# Los fuentes se compilan juntos y no como biblioteca: cada estrategia se
# registra sola al cargar el programa, y el enlazador descartaría de una
# biblioteca los archivos que nadie nombra.
#
# NUCLEO_VERSION es una huella de los fuentes de los que dependen los
# resultados (mercado, estrategias del núcleo y rivales). Los resultados
# guardados en build/resultados la llevan, y un binario solo los usa si fue
# compilado con los mismos fuentes. Si no coinciden, los recalcula.

NUCLEO_DIR := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
RETORNO_DIR := $(patsubst %/,%,$(dir $(NUCLEO_DIR)))
NUCLEO_FUENTES := $(addprefix $(NUCLEO_DIR)/,nucleo.c torneo.c e_param.c e_rivales.c main.c)
NUCLEO_CABECERAS := $(addprefix $(NUCLEO_DIR)/,nucleo.h torneo.h)
NUCLEO_VERSION := $(shell cat $(addprefix $(NUCLEO_DIR)/,nucleo.h nucleo.c e_param.c e_rivales.c) | md5sum | cut -c1-15)
NUCLEO_CC := $(CC) -O2 -Wall -Wextra -fopenmp -I$(NUCLEO_DIR) \
             -DRETORNO_DIR='"$(RETORNO_DIR)"' -DNUCLEO_VERSION=0x$(NUCLEO_VERSION)ULL
NUCLEO_LIBS := -lm
