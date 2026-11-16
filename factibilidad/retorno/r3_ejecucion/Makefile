# Makefile del estudio de retorno 3: ejecución que conoce su patrimonio.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se corre desde esta carpeta o con make -C factibilidad/retorno/r3_ejecucion.
# Los productos intermedios quedan en build/ (no se versiona) y las salidas en
# mediciones/. Solo se usa la semilla 0 (exploración).
#
#   make arnes          compila build/arnes: el núcleo del arnés, sin tocar, más ejec.c
#   make validar        ejec sin opciones es max_media serie por serie, espejo de la cuenta y causalidad
#   make validar-cota   la copia del núcleo de la cota da lo mismo que el arnés con límite 63
#   make cota           paso 1: max_media con límite 63, 126, 252 y sin límite
#   make descomposicion paso 2: de qué está hecho el costo de la ejecución actual
#   make variantes      paso 3: barrido de las variantes con contabilidad propia
#   make finales        paso 4: veredictos, hipótesis, meseta, estrés y robustez de las candidatas finales
#   make practica       las candidatas finales en los 10 bloques reales y en la serie de práctica completa (informativo)
#   make todo           todo lo anterior, en orden
#
# HILOS (por defecto 5) limita los hilos del arnés.

include ../nucleo/nucleo.mk

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

PYTHON ?= python3
HILOS ?= 5
export HILOS
B := build
M := mediciones
BIN := $(B)/arnes
SERIES := $(RETORNO_DIR)/build/series

.PHONY: arnes validar validar-cota cota descomposicion variantes finales practica todo limpiar

arnes: $(BIN)

$(BIN): $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) ejec.c
	@mkdir -p $(B)
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) ejec.c $(NUCLEO_LIBS)

# --- Paso 1: cota con una copia local del núcleo ------------------------------------------
# La copia se arma con cota/parche.sh (dos líneas de nucleo.c). Lleva su propia
# huella y guarda sus resultados en build/cota/resultados, nunca en los del arnés.

CN := $(B)/cota/nucleo
COTA := $(B)/cota/arnes
COTA_FUENTES := $(addprefix $(CN)/,nucleo.c torneo.c e_param.c e_rivales.c main.c)
COTA_ENT := RETORNO_RESULTADOS=$(abspath $(B)/cota/resultados) RETORNO_GUARDAR=1

$(CN)/.listo: $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) cota/parche.sh
	@mkdir -p $(B)/cota $(M)
	sh cota/parche.sh $(NUCLEO_DIR) $(CN) > $(M)/cota_parche.txt
	@touch $@

$(COTA): $(CN)/.listo cota/lim.c
	$(CC) -O2 -Wall -Wextra -fopenmp -I$(CN) -DRETORNO_DIR='"$(RETORNO_DIR)"' \
	  -DNUCLEO_VERSION=0x$$(cat $(CN)/nucleo.h $(CN)/nucleo.c $(CN)/e_param.c $(CN)/e_rivales.c | md5sum | cut -c1-15)ULL \
	  -o $@ $(COTA_FUENTES) cota/lim.c -lm

validar-cota: $(COTA) $(BIN)
	$(COTA_ENT) $(PYTHON) cota/validar_cota.py --arnes $(BIN) --cota $(COTA) --series $(SERIES) | tee $(M)/cota_validacion.txt

cota: $(COTA) $(BIN)
	$(COTA_ENT) $(PYTHON) cota/medir_cota.py --cota $(COTA) | tee $(M)/cota.txt

# --- Paso 2: descomposición del costo de la ejecución ---------------------------------------

DESC := $(B)/descomp

$(DESC): herramientas/descomp.c ejec.c $(NUCLEO_DIR)/nucleo.c $(NUCLEO_DIR)/e_param.c $(NUCLEO_CABECERAS)
	@mkdir -p $(B)
	$(NUCLEO_CC) -o $@ herramientas/descomp.c ejec.c $(NUCLEO_DIR)/nucleo.c $(NUCLEO_DIR)/e_param.c $(NUCLEO_LIBS)

descomposicion: $(DESC)
	@mkdir -p $(M)
	( for c in evidencia remuestreo plausibles estres; do $(DESC) --estrategia max_media --conjunto $$c --largo 2000 --semilla 0; echo; done; \
	  $(DESC) --estrategia base --conjunto evidencia --largo 2000 --semilla 0; echo; \
	  $(DESC) --estrategia max_media --conjunto bloques --largo 2000; echo; \
	  $(DESC) --estrategia max_media --conjunto practica --largo 20000; echo; \
	  for c in evidencia remuestreo plausibles; do $(DESC) --estrategia max_media --conjunto $$c --largo 20000 --semilla 0 --parada; echo; done; \
	  $(DESC) --estrategia max_media --conjunto evidencia --largo 20000 --semilla 0 --interior ) | tee $(M)/descomposicion.txt

# --- Validación de la estrategia ---------------------------------------------------------------

validar: $(BIN)
	@mkdir -p $(M)
	$(PYTHON) herramientas/validar.py --arnes $(BIN) --series $(SERIES) | tee $(M)/validacion.txt

# --- Paso 3: barrido de variantes (cada una con el veredicto completo contra max_media) -----

variantes: $(BIN)
	@mkdir -p $(M)
	$(PYTHON) herramientas/barrido.py --arnes $(BIN) --lista herramientas/variantes.txt | tee $(M)/variantes_1.txt
	$(PYTHON) herramientas/barrido.py --arnes $(BIN) --lista herramientas/variantes2.txt | tee $(M)/variantes_2.txt

# --- Paso 4: candidatas finales ------------------------------------------------------------------

FINALES := ejec:m=8;ejec:m=8,m2=24,e2=32
HIP := --semilla 0 --candidatos "max_media;$(FINALES);base" --ref max_media

finales: $(BIN) $(DESC)
	@mkdir -p $(M)
	$(PYTHON) herramientas/barrido.py --arnes $(BIN) --variantes "$(FINALES)" --completo > $(M)/finales_veredictos.txt
	HILOS_VEREDICTO=1 PROCESOS=5 $(PYTHON) $(RETORNO_DIR)/pruebas/veredictos.py --arnes $(BIN) --candidatas "$(FINALES);ejec:m=2" \
	  --referencia max_media --semilla 0 > $(M)/finales_sensibilidad.txt
	( echo "Control del desempate de H3b: la misma mejora sobre una regla que no es identica a ningun rival (E = 112)."; \
	  echo "Si la diferencia de H3b baja al nivel de la de H3a, lo que H3b mide contra max_media es el desempate con el rival identico."; echo; \
	  $(PYTHON) herramientas/barrido.py --arnes $(BIN) --referencia "param:E=112,X=0" \
	    --variantes "ejec:E=112,m=8;ejec:E=112,m=8,m2=24,e2=32;ejec:E=112,m=2" ) > $(M)/finales_desempate.txt
	$(BIN) hipotesis --largo 2000 $(HIP) --tsv $(B)/h_2000.tsv > $(M)/finales_hipotesis_2000.txt
	$(BIN) hipotesis --largo 20000 --interior $(HIP) --tsv $(B)/h_20000_interiores.tsv > $(M)/finales_hipotesis_20000_interiores.txt
	$(BIN) hipotesis --largo 20000 --parada $(HIP) --tsv $(B)/h_20000_parada.tsv > $(M)/finales_hipotesis_20000_parada.txt
	$(BIN) hipotesis --largo 20000 $(HIP) --tsv $(B)/h_20000_todas.tsv > $(M)/finales_hipotesis_20000_todas.txt
	$(PYTHON) herramientas/tabla_finales.py --finales "$(FINALES);base" \
	  --vista "Rondas de 2000 ticks=$(B)/h_2000.tsv" \
	  --vista "Rondas de 20 000 ticks, series interiores=$(B)/h_20000_interiores.tsv" \
	  --vista "Rondas de 20 000 ticks, vista de parada=$(B)/h_20000_parada.tsv" \
	  --vista "Rondas de 20 000 ticks, todas las series (medias infladas por el rebote en el precio 1)=$(B)/h_20000_todas.tsv" > $(M)/finales_tablas.md
	$(PYTHON) herramientas/robustez.py --arnes $(BIN) --series $(SERIES) --finales "$(FINALES)" > $(M)/finales_robustez.txt
	( $(DESC) --estrategia "ejec:m=8" --conjunto evidencia --largo 2000 --semilla 0; echo; \
	  $(DESC) --estrategia "ejec:m=8,m2=24,e2=32" --conjunto evidencia --largo 2000 --semilla 0 ) > $(M)/finales_descomposicion.txt
	@sed -n 1,9p $(M)/finales_veredictos.txt

# Informativo: los 10 bloques reales son 10 series y la serie completa es una sola. No es una muestra
# y no se eligió nada con estas cifras.
practica: $(BIN)
	@mkdir -p $(M)
	( $(BIN) resumen --conjunto bloques --largo 2000 --semilla 0 --estrategia "max_media;$(FINALES);base"; \
	  $(BIN) resumen --conjunto practica --largo 20000 --semilla 0 --estrategia "max_media;$(FINALES);base" ) | tee $(M)/finales_practica.txt

todo: validar-cota cota descomposicion validar variantes finales practica

limpiar:
	rm -rf $(B)
