# Makefile del estudio de retorno 4, cierre: el fondo completo contra la mejor estrategia sola.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Todo se corre desde esta carpeta. Las salidas quedan en mediciones/ y los
# productos intermedios en build/, que no se versiona. Necesita las series del
# arnés (make -C .. series, que desde este estudio incluye la semilla 3) y sus
# resultados guardados (make -C .. exploracion), que este Makefile solo lee.
#
#   make                compila build/arnes: el núcleo, los módulos de los tres estudios sin tocar,
#                       fondoc.c (copia modificada de ../r4b_fondo/fondo.c) y final.c
#   make sin-cambios    los campos nuevos de ../nucleo/torneo.c no cambian ninguna salida anterior
#   make campos         los campos nuevos contra el evaluador independiente de la auditoría
#   make prueba         identidades de las piezas nuevas y causalidad
#   make exploracion    las 19 configuraciones con la semilla 0
#   make final-0        la lista final con la semilla 0: veredicto oficial y duelos
#   make reservada      la lista final con la semilla 3. Se corre UNA vez (REPETIR=1 para reproducirla)
#   make tablas         todas las tablas en Markdown y el resumen, sin volver a evaluar
#   make todo           todo menos `reservada` y `tablas`, en orden
#
# HILOS (por defecto 5) limita los hilos del arnés.

include ../nucleo/nucleo.mk
include ../r4c_aprendizaje/r4c.mk

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

HILOS ?= 5
export HILOS
PY := python3
BIN := build/arnes
M := mediciones
AJENOS := ../r3_ejecucion/ejec.c ../r4b_fondo/fondo.c $(R4C_FUENTES)
PROPIOS := fondoc.c final.c
# Versión del repositorio con el torneo.c anterior a este estudio.
ANTES := 9b82e81

.PHONY: arnes sin-cambios campos prueba exploracion final-0 reservada tablas todo limpiar
arnes: $(BIN)

$(BIN): $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) $(AJENOS) $(R4C_CABECERAS) $(PROPIOS)
	@mkdir -p build
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) $(AJENOS) $(PROPIOS) $(NUCLEO_LIBS)

# --- Los campos nuevos no cambian nada de lo anterior ------------------------------
# Se compila el mismo binario con el torneo.c de antes (sacado del repositorio)
# y con el de ahora, se corre la misma lista de comandos con los dos y se
# comparan las salidas byte a byte. Además se repite la validación del torneo
# del arnés, que reescribe ../mediciones/validacion_torneo.txt: tiene que
# quedar idéntico al versionado.
build/antes/arnes: $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) $(AJENOS) $(R4C_CABECERAS)
	@mkdir -p build/antes
	git show $(ANTES):factibilidad/retorno/nucleo/torneo.c > build/antes/torneo.c
	$(NUCLEO_CC) -o $@ $(subst $(NUCLEO_DIR)/torneo.c,build/antes/torneo.c,$(NUCLEO_FUENTES)) $(AJENOS) $(NUCLEO_LIBS)

build/despues/arnes: $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) $(AJENOS) $(R4C_CABECERAS)
	@mkdir -p build/despues
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) $(AJENOS) $(NUCLEO_LIBS)

sin-cambios: build/antes/arnes build/despues/arnes
	@mkdir -p $(M)
	sh salidas_torneo.sh build/antes/arnes build/antes/salidas > /dev/null
	sh salidas_torneo.sh build/despues/arnes build/despues/salidas > /dev/null
	( echo "Salidas del arnes con el torneo.c anterior ($(ANTES)) y con el actual, comparadas byte a byte."; \
	  echo "torneo.c anterior: $$(md5sum < build/antes/torneo.c | cut -c1-32)   actual: $$(md5sum < $(NUCLEO_DIR)/torneo.c | cut -c1-32)"; \
	  mal=0; for f in build/antes/salidas/*; do n=$$(basename $$f); \
	    if cmp -s $$f build/despues/salidas/$$n; then e=identica; else e=DISTINTA; mal=1; fi; \
	    printf "%-36s %8d bytes  %s  %s\n" $$n $$(wc -c < $$f) $$(md5sum < $$f | cut -c1-16) $$e; done; \
	  cp ../mediciones/validacion_torneo.txt build/antes/validacion_torneo.txt; \
	  $(MAKE) --no-print-directory -C .. validar-torneo > build/despues/validar_torneo.log 2>&1 || mal=1; \
	  if cmp -s build/antes/validacion_torneo.txt ../mediciones/validacion_torneo.txt; then e=identica; else e=DISTINTA; mal=1; fi; \
	  printf "%-36s %8d bytes  %s  %s (make -C .. validar-torneo)\n" validacion_torneo.txt $$(wc -c < ../mediciones/validacion_torneo.txt) \
	    $$(md5sum < ../mediciones/validacion_torneo.txt | cut -c1-16) $$e; \
	  tail -2 ../mediciones/validacion_torneo.txt; \
	  if [ $$mal = 0 ]; then echo "SIN_CAMBIOS: OK"; else echo "SIN_CAMBIOS: FALLA"; fi ) | tee $(M)/sin_cambios.txt
	@grep -q "SIN_CAMBIOS: OK" $(M)/sin_cambios.txt

# --- Los campos nuevos dan lo mismo que el evaluador independiente ---------------
campos: $(BIN)
	@mkdir -p $(M)
	$(PY) comparar_campos.py --arnes $(BIN) > $(M)/campos_contra_independiente.txt
	@tail -3 $(M)/campos_contra_independiente.txt
	( for c in racional reversores fijos2; do echo "== RETORNO_CAMPO=$$c: el campo ocupa la columna del mixto =="; \
	    RETORNO_CAMPO=$$c $(BIN) rivales | awk -F'|' 'NR <= 4 || $$2 !~ /^ *[0-9.]+% +0.00% +[0-9.]+% *$$/'; echo; done ) > $(M)/campos_pesos.txt

# --- Piezas propias -------------------------------------------------------------------
prueba: $(BIN)
	@mkdir -p $(M)
	sh pruebas.sh $(BIN) ../../../tb/practica.csv > $(M)/prueba.txt 2>&1; tail -1 $(M)/prueba.txt
	@grep -q "^PASS" $(M)/prueba.txt

# --- Estudio ---------------------------------------------------------------------------
# exploracion: las 19 configuraciones con la semilla 0, en las tres vistas y los cinco campos.
exploracion: $(BIN)
	$(PY) correr.py --semilla 0 --lista exploracion
	$(PY) tablas.py --semilla 0 --etiqueta exploracion > $(M)/tablas_exploracion_s0.md

# final-0: la lista final (lista_final.txt) con la semilla 0, con el veredicto oficial y los duelos.
final-0: $(BIN)
	$(PY) correr.py --semilla 0 --lista final
	$(PY) tablas.py --semilla 0 --etiqueta final > $(M)/tablas_final_s0.md
	$(PY) tablas.py --semilla 0 --etiqueta duelo_ejec_a --ref ejec_a > $(M)/tablas_duelo_ejec_a_s0.md

# reservada: la lista final con la semilla 3. correr.py se niega a repetirla sin REPETIR=1.
reservada: $(BIN)
	$(PY) correr.py --semilla 3 --lista final $(if $(REPETIR),--repetir)
	$(PY) tablas.py --semilla 3 --etiqueta final > $(M)/tablas_final_s3.md
	$(PY) tablas.py --semilla 3 --etiqueta duelo_ejec_a --ref ejec_a > $(M)/tablas_duelo_ejec_a_s3.md
	$(PY) resumen.py > $(M)/resumen.md

tablas:
	$(PY) tablas.py --semilla 0 --etiqueta exploracion > $(M)/tablas_exploracion_s0.md
	$(PY) tablas.py --semilla 0 --etiqueta final > $(M)/tablas_final_s0.md
	$(PY) tablas.py --semilla 3 --etiqueta final > $(M)/tablas_final_s3.md
	$(PY) tablas.py --semilla 0 --etiqueta duelo_ejec_a --ref ejec_a > $(M)/tablas_duelo_ejec_a_s0.md
	$(PY) tablas.py --semilla 3 --etiqueta duelo_ejec_a --ref ejec_a > $(M)/tablas_duelo_ejec_a_s3.md
	$(PY) resumen.py > $(M)/resumen.md

todo: arnes sin-cambios campos prueba exploracion final-0

limpiar:
	rm -rf build
