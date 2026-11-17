# Makefile de la tarea B (docs/generador_b.md): el arnés de factibilidad/retorno con el
# campo "variados" (ref/torneo_b/torneo_b.c) y las estrategias de ref/zscore/.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
include ../../factibilidad/retorno/nucleo/nucleo.mk
SALIDA := ../../build/torneo_b
BIN := $(SALIDA)/arnes
FUENTES := $(filter-out $(NUCLEO_DIR)/torneo.c,$(NUCLEO_FUENTES)) torneo_b.c ../zscore/zscore.c ../zscore/fondo_z.c
.PHONY: todo
todo: $(BIN)
$(BIN): $(FUENTES) $(NUCLEO_CABECERAS)
	@mkdir -p $(SALIDA)
	$(NUCLEO_CC) -o $@ $(FUENTES) $(NUCLEO_LIBS)
