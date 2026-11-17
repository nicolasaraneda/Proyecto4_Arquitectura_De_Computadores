# Makefile de la evaluación de la regla zscore (ref/zscore/).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Compila el arnés de factibilidad/retorno con dos estrategias más: zscore
# (zscore.c) y el fondo con gestores por nombre (fondo_z.c). Se corre desde la
# raíz con make zscore-arnes, o make -C ref/zscore.

include ../../factibilidad/retorno/nucleo/nucleo.mk

SALIDA := ../../build/zscore
BIN := $(SALIDA)/arnes

.PHONY: todo
todo: $(BIN)

$(BIN): $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) zscore.c fondo_z.c
	@mkdir -p $(SALIDA)
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) zscore.c fondo_z.c $(NUCLEO_LIBS)
