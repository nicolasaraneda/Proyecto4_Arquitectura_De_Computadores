# Makefile de la auditoría de los estudios de retorno 3 y 4.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se corre desde esta carpeta. Las salidas quedan en mediciones/ y lo que se
# compila en build/, que no se versiona. Necesita las series del arnés
# (make -C .. series) y sus resultados guardados (make -C .. exploracion).
#
#   make                compila build/arnes (núcleo y módulos de los cuatro estudios, sin tocar),
#                       build/perturba y build/indep34
#   make causal         comando `causal` del arnés para todas las configuraciones (1 s)
#   make perturba       perturbación propia de los precios futuros y martingala (33 s)
#   make sin-cambios    los campos nuevos de ../nucleo/torneo.c no cambian las salidas anteriores (4 min)
#   make equivalencia   las estrategias reescritas aquí contra las del arnés, serie por serie (1 min)
#   make reproducir     la tabla final con el evaluador independiente, semillas 0 y 3 (2 min)
#   make cotas          la cota de ejecución, el oráculo del fondo y la robustez del espejo, recalculados (35 s)
#   make aritmetica     operaciones de cada candidata final, contadas en el código y en corrida
#   make seleccion      fechas, huellas y cantidad de variantes
#   make veredictos     el veredicto por campo de las tablas del estudio contra el comando oficial (6 min)
#   make repetir        objetivos baratos de las cuatro carpetas auditadas, repetidos y comparados (3 min)
#   make informe        cifras informadas contra las obtenidas (mediciones/cifras.txt)
#   make todo           todo, en orden (16 min 20 s medidos)
#
# HILOS (por defecto 5) limita los hilos.

include ../nucleo/nucleo.mk
include ../r4c_aprendizaje/r4c.mk

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

HILOS ?= 5
export HILOS
PY := python3
M := mediciones
B := build
NUCLEO_SIN_MAIN := $(filter-out %/main.c,$(NUCLEO_FUENTES))
MODULOS := ../r3_ejecucion/ejec.c ../r4b_fondo/fondo.c $(R4C_FUENTES) ../r4_final/fondoc.c ../r4_final/final.c
ANTES := 9b82e81

.PHONY: arnes causal perturba sin-cambios equivalencia reproducir cotas aritmetica seleccion veredictos repetir informe todo limpiar
arnes: $(B)/arnes $(B)/perturba $(B)/indep34

$(B)/arnes: $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) $(MODULOS) $(R4C_CABECERAS)
	@mkdir -p $(B)
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) $(MODULOS) $(NUCLEO_LIBS)

$(B)/perturba: perturba.c $(NUCLEO_SIN_MAIN) $(NUCLEO_CABECERAS) $(MODULOS) $(R4C_CABECERAS)
	@mkdir -p $(B)
	$(NUCLEO_CC) -o $@ perturba.c $(NUCLEO_SIN_MAIN) $(MODULOS) $(NUCLEO_LIBS)

# El evaluador independiente no usa ningún fuente del núcleo: incluye el de la
# auditoría del arnés (../auditoria/indep.c, sin modificar) y agrega lo propio.
$(B)/indep34: indep34.c ../auditoria/indep.c
	@mkdir -p $(B)
	$(CC) -O2 -Wall -Wextra -fopenmp -o $@ indep34.c -lm

causal: $(B)/arnes
	@mkdir -p $(M)
	sh causal.sh $(B)/arnes > $(M)/causal.txt 2>&1; tail -1 $(M)/causal.txt
	@grep -q "^PASS" $(M)/causal.txt

perturba: $(B)/perturba
	@mkdir -p $(M)
	$(B)/perturba > $(M)/perturbacion.txt; tail -1 $(M)/perturbacion.txt
	@grep -q "^PASS" $(M)/perturbacion.txt

sin-cambios: $(B)/arnes
	@mkdir -p $(M)
	sh sin_cambios.sh $(ANTES) > $(M)/sin_cambios.txt 2>&1; tail -1 $(M)/sin_cambios.txt
	@grep -q "^SIN_CAMBIOS: OK" $(M)/sin_cambios.txt

equivalencia: $(B)/arnes $(B)/indep34
	@mkdir -p $(M)
	$(PY) equivalencia.py > $(M)/equivalencia.txt; tail -1 $(M)/equivalencia.txt
	@grep -q "^PASS" $(M)/equivalencia.txt

reproducir: $(B)/indep34
	@mkdir -p $(M)
	cd .. && auditoria_r34/$(B)/indep34 tabla --semilla 0 > auditoria_r34/$(B)/tabla_s0.txt
	cd .. && auditoria_r34/$(B)/indep34 tabla --semilla 3 > auditoria_r34/$(B)/tabla_s3.txt
	cp $(B)/tabla_s0.txt $(M)/independiente_s0.txt
	cp $(B)/tabla_s3.txt $(M)/independiente_s3.txt

cotas: $(B)/indep34
	@mkdir -p $(M)
	cd .. && auditoria_r34/$(B)/indep34 cotas --semilla 0 > auditoria_r34/$(M)/cotas.txt
	@tail -3 $(M)/cotas.txt

aritmetica: $(B)/arnes
	@mkdir -p $(M)
	$(PY) aritmetica.py > $(M)/aritmetica.txt; tail -3 $(M)/aritmetica.txt

seleccion:
	@mkdir -p $(M)
	sh seleccion.sh > $(M)/seleccion.txt 2>&1; tail -3 $(M)/seleccion.txt

veredictos: $(B)/arnes
	@mkdir -p $(M)
	sh veredictos_campos.sh $(B)/arnes > $(M)/veredictos_campos.txt 2>&1; tail -1 $(M)/veredictos_campos.txt
	@grep -q "^PASS" $(M)/veredictos_campos.txt

repetir:
	@mkdir -p $(M)
	sh repetir.sh > $(M)/repeticion.txt 2>&1; tail -1 $(M)/repeticion.txt
	@grep -q "^PASS" $(M)/repeticion.txt

informe:
	@mkdir -p $(M)
	$(PY) informe.py > $(M)/cifras.txt; tail -4 $(M)/cifras.txt

todo: arnes causal perturba sin-cambios equivalencia reproducir cotas aritmetica seleccion veredictos repetir informe

limpiar:
	rm -rf $(B)
