# Makefile del estudio de retorno (factibilidad/retorno).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se corre desde esta carpeta o con make -C factibilidad/retorno. Todo lo que
# genera queda en build/ (no se versiona) y las salidas en mediciones/.
#
#   make arnes        compila build/retorno (el arnés con las estrategias del núcleo)
#   make series       genera las series que falten en build/series (unos 2 minutos la primera vez)
#   make validar      mercado, familia paramétrica, números conocidos, frontera anterior y causalidad (5 minutos)
#   make comprobar-series  las series guardadas son las de ref/series.py (medio minuto)
#   make gemelo       sw/trade.hex en el gemelo digital contra la regla base del arnés, en las series nuevas (5 minutos)
#   make ejemplo      compila y prueba la estrategia de ejemplo (ejemplo/)
#   make exploracion  frontera, hipótesis, veredictos, duelos y tablas con la semilla 0
#   make final        lo mismo con la semilla reservada (2). Se corre una sola vez, al final
#   make comparar     las dos semillas lado a lado (mediciones/semillas_0_y_2.md)
#   make validar-torneo  puntajes H3a y H3b recalculados por otro camino (después de make exploracion)
#   make todo         todo lo anterior, en orden (7 minutos con las series ya generadas)
#   make auditoria    la auditoría independiente del arnés (auditoria/Makefile, 6 minutos)
#
# HILOS (por defecto 6) limita los hilos del arnés y PROCESOS los de Python.

include nucleo/nucleo.mk

# con tuberías (| tee) el objetivo falla si falla el primer comando
SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

PYTHON ?= python3
HILOS ?= 6
export HILOS
PROCESOS ?= 6
export PROCESOS
RAIZ := $(abspath ../..)
B := build
M := mediciones
R := $(B)/retorno
GUARDA := RETORNO_GUARDAR=1

.PHONY: arnes series comprobar-series validar validar-torneo causal gemelo ejemplo precalcular exploracion final comparar todo limpiar auditoria

arnes: $(R)

$(R): $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) nucleo/nucleo.mk
	@mkdir -p $(B)
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) $(NUCLEO_LIBS)

$(B)/motor: $(RAIZ)/ref/motor/motor.c
	@mkdir -p $(B)
	$(CC) -O2 -Wall -Wextra -o $@ $<

$(B)/gemelo: $(RAIZ)/ref/gemelo/gemelo.c
	@mkdir -p $(B)
	$(CC) -O2 -o $@ $<

series:
	$(PYTHON) generar_series.py

# --- Validación del arnés ---------------------------------------------------------
validar: $(R) $(B)/motor series
	$(PYTHON) pruebas/validar.py | tee $(M)/validacion.txt
	$(R) causal | tee $(M)/causal.txt

comprobar-series: series
	$(PYTHON) pruebas/validar_series.py | tee $(M)/series_comprobacion.txt

causal: $(R)
	$(R) causal | tee $(M)/causal.txt

gemelo: $(R) $(B)/gemelo series
	$(PYTHON) pruebas/validar_gemelo.py | tee $(M)/gemelo.txt

# Primero compila en silencio y después prueba, para que la salida guardada
# traiga solo los comandos y sus resultados (sin la línea de compilación ni la
# ruta local de la carpeta).
ejemplo: $(R)
	@$(MAKE) -s -C ejemplo todo
	@$(MAKE) -s -C ejemplo/minimo todo
	$(MAKE) --no-print-directory -C ejemplo probar | tee $(M)/ejemplo.txt

# --- Estudios ----------------------------------------------------------------------
# Los resultados de candidatos y rivales quedan en build/resultados para que
# otros binarios compilados contra el mismo núcleo no los recalculen.
# A 20 000 ticks cada tabla sale dos veces: con las series interiores (precio
# siempre entre 21 y 249) y con todas. Ver README.md, límites 1 y 255.
precalcular-%: $(R) series
	$(GUARDA) $(R) precalcular --largo 2000 --semilla $*
	$(GUARDA) $(R) precalcular --largo 20000 --semilla $*

estudio-%: precalcular-%
	@mkdir -p $(B)/tsv
	cp $(B)/series/MANIFIESTO.txt $(M)/series_manifiesto.txt
	$(R) rivales > $(M)/rivales.txt
	( $(R) bordes --largo 2000 --semilla $* && $(R) bordes --largo 20000 --semilla $* ) > $(M)/bordes_s$*.txt
	( $(R) frontera --largo 2000 --semilla $* && $(R) frontera --largo 20000 --semilla $* --interior \
	  && $(R) frontera --largo 20000 --semilla $* ) > $(M)/frontera_s$*.txt
	( $(R) hipotesis --largo 2000 --semilla $* --tsv $(B)/tsv/hipotesis_n2000_todas_s$*.tsv \
	  && $(R) hipotesis --largo 20000 --semilla $* --interior --tsv $(B)/tsv/hipotesis_n20000_interiores_s$*.tsv \
	  && $(R) hipotesis --largo 20000 --semilla $* --tsv $(B)/tsv/hipotesis_n20000_todas_s$*.tsv ) > $(M)/hipotesis_s$*.txt
	$(PYTHON) pruebas/veredictos.py --semilla $* > $(M)/veredictos_s$*.txt
	$(PYTHON) pruebas/tablas.py --semilla $* > $(M)/tablas_s$*.md
	@wc -l $(M)/frontera_s$*.txt $(M)/bordes_s$*.txt $(M)/hipotesis_s$*.txt $(M)/veredictos_s$*.txt $(M)/tablas_s$*.md

# Duelos: los candidatos que quedan arriba con la semilla 0, comparados entre
# sí con el mismo criterio de corte y max_media como referencia.
DUELOS := kalman;activo;guardia
duelos-%: precalcular-%
	$(PYTHON) pruebas/veredictos.py --semilla $* --referencia max_media --candidatas "$(DUELOS)" > $(M)/duelos_s$*.txt
	@wc -l $(M)/duelos_s$*.txt

validar-torneo: $(R)
	$(PYTHON) pruebas/validar_torneo.py | tee $(M)/validacion_torneo.txt

comparar:
	$(PYTHON) pruebas/comparar_semillas.py > $(M)/semillas_0_y_2.md
	@wc -l $(M)/semillas_0_y_2.md

exploracion: estudio-0 duelos-0
final: estudio-2 duelos-2 comparar

todo: arnes series comprobar-series validar gemelo ejemplo exploracion validar-torneo final

auditoria: $(R) series
	$(MAKE) -C auditoria todo

limpiar:
	rm -rf $(B)/retorno $(B)/motor $(B)/gemelo $(B)/resultados $(B)/ejemplo $(B)/tsv
