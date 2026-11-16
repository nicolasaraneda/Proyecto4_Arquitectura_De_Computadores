# Makefile del ejemplo mínimo: un archivo propio compilado contra el núcleo del arnés.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# En otra carpeta solo cambia la ruta del include (por ejemplo
# ../retorno/nucleo/nucleo.mk desde factibilidad/otro_estudio/) y el
# directorio de salida.
#
#   make -C factibilidad/retorno/ejemplo/minimo probar

include ../../nucleo/nucleo.mk

SALIDA := ../../build/ejemplo
BIN := $(SALIDA)/minimo
HILOS ?= 6
export HILOS

.PHONY: todo probar
todo: $(BIN)

$(BIN): $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) mia.c
	@mkdir -p $(SALIDA)
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) mia.c $(NUCLEO_LIBS)

probar: $(BIN)
	$(BIN) listar | grep -E "^  mia "
	$(BIN) causal --estrategia mia
	$(BIN) correr --estrategia "mia:k=5,entra=4" --serie ../../../../tb/practica.csv
	$(BIN) resumen --conjunto remuestreo --largo 2000 --semilla 0 --estrategia "base;max_media;mia"
	$(BIN) veredicto --candidata mia --referencia base --largo 2000 --semilla 0 | tail -4
