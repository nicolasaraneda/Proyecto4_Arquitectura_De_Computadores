# Makefile del ejemplo: una estrategia propia compilada contra el núcleo del arnés.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Para usarlo en otra carpeta: copiar este archivo y mi_estrategia.c, cambiar
# la ruta del include y el directorio de salida, y agregar los .c propios.
#
#   make -C factibilidad/retorno/ejemplo          compila ../build/ejemplo/arnes
#   make -C factibilidad/retorno/ejemplo probar   lista, causalidad, bloques y veredicto

include ../nucleo/nucleo.mk

SALIDA := ../build/ejemplo
BIN := $(SALIDA)/arnes
MIS_FUENTES := mi_estrategia.c
HILOS ?= 6
export HILOS

.PHONY: todo probar
todo: $(BIN)

$(BIN): $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) $(MIS_FUENTES)
	@mkdir -p $(SALIDA)
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) $(MIS_FUENTES) $(NUCLEO_LIBS)

probar: $(BIN)
	$(BIN) listar | grep -E "^  (ejemplo|seguidor) "
	$(BIN) causal --estrategia ejemplo
	$(BIN) causal --estrategia seguidor
	$(BIN) correr --estrategia ejemplo --serie ../../../tb/practica.csv
	$(BIN) correr --estrategia "ejemplo:k=5,entra=3,sale=0" --serie ../../../tb/practica.csv
	$(BIN) resumen --conjunto bloques --largo 2000 --estrategia "base;max_media;ejemplo;seguidor"
	$(BIN) veredicto --candidata seguidor --referencia base --largo 2000 --semilla 0
	$(MAKE) -C minimo probar
