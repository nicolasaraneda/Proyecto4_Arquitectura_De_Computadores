# Makefile del estudio de retorno 4, parte C: aprendizaje en vivo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Todo se corre desde esta carpeta. Las salidas quedan en mediciones/ y los
# productos intermedios en build/, que no se versiona. Necesita las series
# del arnés (make -C .. series) y sus resultados guardados (make -C ..
# exploracion), que este Makefile solo lee.
#
#   make                compila build/arnes (el arnés con las estrategias de esta carpeta)
#   make equivalencia   la tabla y el filtro con el aprendizaje apagado contra max_media
#   make causal         ninguna estrategia nueva mira el futuro
#   make exactitud      exactitud del predictor de patrones por familia de series
#   make cota           cuánto se podía ganar como máximo (oráculos)
#   make barrido        barrido de variantes con la semilla 0 y su resumen por etapa
#   make finales        veredicto e hipótesis de las candidatas finales, semilla 0
#   make tamanos        memoria que pide cada variante, contra las 4 BRAM libres
#   make cuarto         las estrategias de esta carpeta como cuarto gestor del fondo (necesita ../r4b_fondo/fondo.c)
#   make todo           todo lo anterior, en orden
#
# Las semillas 2 y 3 no se usan aquí: las cifras con semilla reservada las
# corre el estudio de cierre, una vez por candidata final.

include ../nucleo/nucleo.mk
include r4c.mk

HILOS ?= 5
export HILOS
# exactitud y cota usan OpenMP sin pasar por el núcleo: se limitan con la variable estándar.
OMP_NUM_THREADS := $(HILOS)
export OMP_NUM_THREADS
SEMILLA := 0
BIN := build/arnes
PY := python3

.PHONY: todo arnes equivalencia causal exactitud cota barrido finales tamanos cuarto limpiar
arnes: $(BIN)

$(BIN): $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) $(R4C_FUENTES) $(R4C_CABECERAS)
	@mkdir -p build
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) $(R4C_FUENTES) $(NUCLEO_LIBS)

build/exactitud: exactitud.c pred.h
	@mkdir -p build
	$(CC) -O2 -Wall -Wextra -fopenmp -o $@ exactitud.c -lm

build/cota: cota.c
	@mkdir -p build
	$(CC) -O2 -Wall -Wextra -fopenmp -o $@ cota.c -lm

equivalencia: $(BIN)
	@mkdir -p mediciones
	sh equivalencia.sh $(BIN) ../build/series > mediciones/equivalencia.txt
	@tail -4 mediciones/equivalencia.txt

causal: $(BIN)
	@mkdir -p mediciones
	( for e in "tabla:ka=8" "tabla:ka=8,ter=1,filas=2" "tabla:ka=8,modo=1" "tabla:ka=8,banda=1,ter=2" \
	           "patron" "patron:tipo=1,H=12" "patron:tipo=3,sim=3,H=6" "mm_patron" "mm_patron:tipo=3,fs=2" \
	           "aprendiz" "aprendiz_rapido" "espera" "aprendiz_patron" "aprendiz_puro"; do \
	    $(BIN) causal --estrategia "$$e" || exit 1; done ) > mediciones/causal.txt
	@cat mediciones/causal.txt

exactitud: build/exactitud
	@mkdir -p mediciones
	build/exactitud --series ../build/series --semilla $(SEMILLA) --largo 2000 --max 1000 > mediciones/exactitud_s0_n2000.txt
	build/exactitud --series ../build/series --semilla $(SEMILLA) --largo 20000 --max 200 > mediciones/exactitud_s0_n20000.txt
	@grep -c . mediciones/exactitud_s0_n2000.txt mediciones/exactitud_s0_n20000.txt

cota: build/cota
	@mkdir -p mediciones
	build/cota --series ../build/series --semilla $(SEMILLA) --largo 2000 > mediciones/cota_s0_n2000.txt
	build/cota --series ../build/series --semilla $(SEMILLA) --largo 20000 --max 1000 > mediciones/cota_s0_n20000.txt
	@tail -30 mediciones/cota_s0_n2000.txt

barrido: $(BIN)
	@mkdir -p mediciones
	$(PY) barrer.py --arnes $(BIN) --semilla $(SEMILLA) --salida mediciones
	$(PY) resumir.py --mediciones mediciones > mediciones/barrido_resumen.txt
	@tail -22 mediciones/barrido_resumen.txt

finales: $(BIN)
	@mkdir -p mediciones
	$(PY) finales.py --arnes $(BIN) --semilla $(SEMILLA) --salida mediciones

tamanos: $(BIN)
	@mkdir -p mediciones
	$(PY) tamanos.py --arnes $(BIN) > mediciones/tamanos.txt
	@cat mediciones/tamanos.txt

# El fondo de estrategias es de otro estudio: su fondo.c se compila tal cual, sin modificarlo, hacia build/ de esta carpeta.
FONDO_C := ../r4b_fondo/fondo.c
build/arnes_fondo: $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) $(R4C_FUENTES) $(R4C_CABECERAS) $(FONDO_C)
	@mkdir -p build
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) $(R4C_FUENTES) $(FONDO_C) $(NUCLEO_LIBS)

cuarto: build/arnes_fondo
	@mkdir -p mediciones
	$(PY) cuarto.py --arnes build/arnes_fondo --semilla $(SEMILLA) --salida mediciones

# `cuarto` entra en `todo` solo si el estudio del fondo está en el repositorio.
todo: arnes equivalencia causal exactitud cota barrido finales tamanos $(if $(wildcard $(FONDO_C)),cuarto)

limpiar:
	rm -rf build
