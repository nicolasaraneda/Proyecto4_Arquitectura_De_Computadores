# Copyright 2026 Universidad de los Andes.
# Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
# you may not use this file except in compliance with the License.
# SPDX-License-Identifier: SHL-0.51
#
# Course: Arquitectura de Computadores (2026)
#
# Authors:
# - Nicolás Villegas <navillegas@miuandes.cl>
#
# Modificado para el Proyecto 4 por el grupo de Nicolás Araneda, Vicente
# Calderón y Santiago Muñoz: ensamblado de sw/trade.s, testbench oficial,
# mediciones y verificaciones. Todo se corre desde la raíz del repositorio.

# Configuración
TOP   := pochoco_soc
PCF   := goboard.pcf
BUILD := build

# Fuentes RTL: la misma lista que usa el comando del testbench oficial
SRC := $(filter-out rtl/00_%,$(wildcard rtl/*.v rtl/espino_core/*.v))

# Programa. $readmemh lo deja dentro del bitstream al sintetizar, así que el
# .hex es prerrequisito de la síntesis.
PYTHON ?= python3
# Herramientas de OSS CAD Suite: tienen que estar en el PATH, o en la carpeta
# OSS_CAD_SUITE (make ... OSS_CAD_SUITE=/ruta/a/oss-cad-suite)
export PATH := $(if $(OSS_CAD_SUITE),$(OSS_CAD_SUITE)/bin:)$(PATH)
ASM    := tools/pochoasm.py
ASMDEP := $(ASM) $(wildcard tools/asm/*.py)
HEX    := sw/trade.hex

# Simulación
IVERILOG  ?= iverilog
VVP       ?= vvp
CELLS_SIM ?= $(shell yosys-config --datdir 2>/dev/null)/ice40/cells_sim.v
TB_OFICIAL := tb/tb_proyecto_4.sv

# Copias parametrizadas del testbench oficial (el original no se modifica)
PERIODO_NS ?= 100000
NTICKS     ?= 2000
SERIE      ?= tb/practica.csv

# Productos de síntesis
JSON := $(BUILD)/$(TOP).json
ASC  := $(BUILD)/$(TOP).asc
GEMELO := $(BUILD)/gemelo
BIN  := $(BUILD)/$(TOP).bin
FREQ ?= 25

.PHONY: all asm test-asm test-ref tb tb-param cpi check check-hex synth pnr bin prog \
        equiv equiv-r3 equiv-r2 equiv-r1 equiv-verilator equiv-largo medir-ticks \
        equiv-icarus equiv-completo equiv-gemelo-20k \
        equiv-series equiv-gemelo gemelo cosim protocolo \
        tb-mv2x2 costo-mv2x2 \
        sim-bitstream guardar-bitstream medir-base hallazgos clean tabla-3-1 fases estres

# Objetivo por defecto: todo lo verificable sin la placa
all: check

$(BUILD):
	mkdir -p $(BUILD)

# --- Ensamblado -------------------------------------------------------------
sw/%.hex: sw/%.s $(ASMDEP)
	$(PYTHON) $(ASM) $< -o $@

asm: $(HEX)

# Tests del ensamblador (87 tests, incluye la comparación con los .hex del repo base)
test-asm:
	cd tools/asm && $(PYTHON) -m unittest discover -s tests -t .

# sw/trade.hex está versionado: se comprueba que corresponde a sw/trade.s
check-hex: | $(BUILD)
	$(PYTHON) $(ASM) sw/trade.s -o $(BUILD)/trade_check.hex >/dev/null
	cmp $(BUILD)/trade_check.hex $(HEX)

# --- Testbench oficial, sin modificar ---------------------------------------
# Mismos comandos que el encabezado de tb/tb_proyecto_4.sv. Falla si no es 4/4.
# Ejercita el diseño por defecto, igual que el comando del encabezado: con las
# fuentes tal como las ve ese comando (incluido rtl/00_peldano.v si existe,
# docs/peldano.md) y el programa que ensambla (PROG_OFICIAL, escrito sin la
# extensión para que tools/peldano.py fijar no lo cambie por el de R0).
PROG_OFICIAL := sw/trade
SRC_OFICIAL := $(wildcard rtl/*.v rtl/espino_core/*.v)
tb: | $(BUILD)
	$(PYTHON) $(ASM) $(PROG_OFICIAL).s -o $(PROG_OFICIAL).hex
	$(IVERILOG) -g2012 -s tb_proyecto_4 -o $(BUILD)/tb_p4 $(CELLS_SIM) $(SRC_OFICIAL) $(TB_OFICIAL)
	$(VVP) -n $(BUILD)/tb_p4 | tee $(BUILD)/tb_p4.log
	@grep -q "Testbenchs aprobados: 4/4" $(BUILD)/tb_p4.log

# Copia del testbench con otro período, número de ticks o serie, por ejemplo:
#   make tb-param PERIODO_NS=1000000 NTICKS=500
# Compara además el decisiones.csv con la referencia (es tools/equiv.sh).
tb-param: $(HEX)
	tools/equiv.sh param $(PERIODO_NS) $(NTICKS) $(SERIE)

# --- Equivalencia entre el RTL y la referencia en Python --------------------
# El decisiones.csv del testbench (copia parametrizada, el oficial no se toca)
# debe ser idéntico byte a byte al de ref/trader.py. Conviene `make -j4 equiv`.
# `make equiv` es lo que corre la integración continua en cada push:
#   equiv-gemelo-20k: los 20 000 ticks de práctica en el gemelo digital, con
#             el timing del testbench oficial, a 0,1 ms, 1 ms y 10 ms.
#   equiv-verilator: los 20 000 ticks por el RTL a 0,1 ms y a 1 ms, con
#             Verilator.
#   equiv-r2 y equiv-r1: pocos ticks a 1 ms y 10 ms con Icarus, para validar el
#             modelo de los precios que se pierden durante el reset.
#   equiv-series: una serie de cada familia sintética, con Verilator.
# Corridas manuales, fuera del push:
#   equiv-r3 (o equiv-icarus): los 20 000 ticks al período de la ronda 3 con
#             Icarus, el simulador del testbench oficial (unos 13 minutos).
#   equiv-largo: los 20 000 ticks a 10 ms con Verilator (unos 25 minutos).
#   equiv-completo: todo lo anterior.
equiv: equiv-gemelo-20k equiv-r2 equiv-r1 equiv-verilator equiv-series
equiv-icarus: equiv-r3
equiv-completo: equiv equiv-r3 equiv-largo

equiv-gemelo-20k: $(GEMELO) $(HEX)
	tools/equiv_gemelo.sh

equiv-r3: $(HEX)
	tools/equiv.sh r3 100000 20000
equiv-r2: $(HEX)
	tools/equiv.sh r2 1000000 200
equiv-r1: $(HEX)
	tools/equiv.sh r1 10000000 20
equiv-verilator: $(HEX)
	SIM=verilator tools/equiv.sh v_r3 100000 20000
	SIM=verilator tools/equiv.sh v_r2 1000000 20000
equiv-largo: $(HEX)
	SIM=verilator tools/equiv.sh v_r1 10000000 20000

# Lotes de series de prueba por el RTL: una serie de cada familia sintética y
# un remuestreo, 2000 ticks cada una, con Verilator. Conviene make -j4.
FAMILIAS := remuestreo modelo paseo tendencia reversion dos_componentes saltos \
            cambio_volatilidad cambio_de_caracter nivel_bajo plana borde_bajo borde_alto
equiv-series: $(addprefix equiv-serie-,$(FAMILIAS))
equiv-serie-%: $(HEX)
	$(PYTHON) ref/series.py $* --n 2000 --semilla 1 -o $(BUILD)/series/$*.csv > /dev/null
	SIM=verilator tools/equiv.sh serie_$* 100000 2000 $(BUILD)/series/$*.csv

# Mercado, referencia, series y protocolo: pruebas en Python (ref/test_ref.py)
test-ref: $(GEMELO)
	$(PYTHON) ref/test_ref.py

# --- Gemelo digital ------------------------------------------------------------
# Simulador en C con exactitud de ciclo (docs/gemelo.md).
gemelo: $(GEMELO)
$(GEMELO): ref/gemelo/gemelo.c | $(BUILD)
	$(CC) -O2 -Wall -Wextra -o $@ $<

# Valida el gemelo contra el RTL: trazas ciclo a ciclo, programas aleatorios,
# testbench oficial y control negativo. Unos 2 minutos.
cosim: $(GEMELO) $(HEX)
	tools/cosim.sh

# El binario sw/trade.hex, corrido en el gemelo sobre las 3810 series del
# protocolo y a los tres períodos, debe dar lo mismo que ref/trader.py.
equiv-gemelo: $(GEMELO) $(HEX)
	$(PYTHON) ref/protocolo.py --binario

# --- Protocolo de evaluación de algoritmos (docs/protocolo.md) ----------------
# Deja los resultados de la regla base en docs/mediciones/.
protocolo: $(GEMELO)
	$(PYTHON) ref/protocolo.py | tee docs/mediciones/protocolo_base.txt
	$(PYTHON) ref/protocolo.py --meseta | tee docs/mediciones/protocolo_meseta.txt
	$(PYTHON) ref/protocolo.py --comparar sma64 | tee docs/mediciones/protocolo_sma64.txt

# CPI medido en simulación (instrucciones completadas y ciclos, por clase) y
# mediciones por tick con precios de un LFSR. Es rápido: 200 ticks con Icarus.
cpi: $(HEX) | $(BUILD)
	$(IVERILOG) -g2012 -s tb_cpi -o $(BUILD)/tb_cpi $(CELLS_SIM) $(SRC) tb/tb_cpi.sv
	$(VVP) -n $(BUILD)/tb_cpi

# Mediciones por tick del punto 3.2 (IC, ciclos, CPI y tiempo, promedio y peor
# caso) con la serie de práctica al período de cada ronda. Usa Verilator.
# Resultado en docs/mediciones/ticks_software.txt.
medir-ticks: $(HEX)
	tools/medir_ticks.sh software

# Tabla del punto 3.1 del enunciado: la estrategia de trade.s (max_media)
# contra la regla base, no operar y comprar y mantener, en la serie completa y
# en los primeros 2000 ticks con el período de la ronda 3.
tabla-3-1:
	{ $(PYTHON) ref/trader.py tb/practica.csv; echo; \
	  $(PYTHON) ref/trader.py tb/practica.csv --nticks 2000 --periodo-ns 100000; } | tee docs/mediciones/tabla_3_1.txt

# Puerta de simulación, criterios 4 y 7 (docs/puertas.md): barrido de las 8
# fases del sondeo y matriz de estrés de la maestra SPI, con tb/tb_estres.sv y
# Verilator. Unos 2 minutos con 16 núcleos. Con DEFS=-DESPINO_SEGMENTADO
# ETQ=seg se corre sobre el segmentado.
ETQ ?= base
fases: $(HEX)
	$(PYTHON) tools/estres.py --solo fases --etiqueta $(ETQ)
estres: $(HEX)
	$(PYTHON) tools/estres.py --etiqueta $(ETQ) | tee docs/mediciones/estres_$(ETQ).txt

# Lo que corre la integración continua en cada push
check: test-asm test-ref test-candidatos check-hex tb

# --- Síntesis, place and route y bitstream ----------------------------------
synth: $(JSON)
$(JSON): $(SRC) $(HEX) | $(BUILD)
	yosys -q -l $(BUILD)/yosys.log \
	  -p "read_verilog $(SRC); chparam -set MemFile \"$(HEX)\" $(TOP); synth_ice40 -top $(TOP) -json $(JSON)"

pnr: $(ASC)
$(ASC): $(JSON) $(PCF)
	nextpnr-ice40 --hx1k --package vq100 --freq $(FREQ) --json $(JSON) --pcf $(PCF) \
	  --asc $(ASC) -l $(BUILD)/nextpnr.log -q
	@grep -E "ICESTORM_LC|ICESTORM_RAM|Max frequency" $(BUILD)/nextpnr.log | tail -3

bin: $(BIN)
$(BIN): $(ASC)
	icepack $(ASC) $(BIN)

# Simula el bitstream (no el RTL): icebox_vlog reconstruye un Verilog desde el
# .asc y se comprueba que decide igual que la referencia. Unos 8 minutos.
sim-bitstream: $(ASC)
	tools/sim_bitstream.sh $(ASC) 2000

# Copia el bitstream recién construido a bitstreams/ con su hash
# (make guardar-bitstream NOMBRE=competencia_v1)
NOMBRE ?= competencia
guardar-bitstream: $(BIN)
	cp $(BIN) bitstreams/$(NOMBRE).bin
	cd bitstreams && sha256sum *.bin > SHA256SUMS && cat SHA256SUMS

# Reconstruye R0 desde las fuentes de su commit y comprueba que es, bit a bit,
# el de bitstreams/ (tools/reproducir_r0.sh). Unos 2 minutos.
r0-reproducir:
	tools/reproducir_r0.sh

# Programar la placa (lo ejecuta una persona, con la Go Board conectada)
prog: $(BIN)
	iceprog $(BIN)

# --- Producto 2x2 en punto fijo: diseño y costo (docs/producto_2x2.md) -------
# No toca el SoC: todo se arma en build/mv2x2/.
#   tb-mv2x2:    las versiones de coeficientes fijos y la de multiplicadores
#                contra ref/mv2x2.py. Corre en la integración continua.
#   costo-mv2x2: además mide LUT en la FPGA (suelto e integrado en una copia
#                del core base) y celdas y área en GF180. Resultado en
#                docs/mediciones/mv2x2_costo.txt.
tb-mv2x2:
	$(PYTHON) tools/costo_mv2x2.py --solo-tb
costo-mv2x2:
	$(PYTHON) tools/costo_mv2x2.py | tee docs/mediciones/mv2x2_costo.txt

# === Frente A: algoritmo (docs/algoritmo.md) ==================================
# Todo lo de este bloque deja su salida en docs/mediciones/.
#   test-candidatos: la familia paramétrica, el motor en C y las familias
#             calibradas (5 segundos). Corre en la integración continua.
#   generador: ajuste del modelo a la serie de práctica, validación y efecto
#             del redondeo.
#   politica: filtro de Kalman en estado estacionario y política óptima.
#   exploracion: una tabla por idea (bandas, estimadores, saltos, cortes,
#             guardia, tope, órdenes, asimetría). Poco más de un minuto.
#   experimentos: población de traders, adaptación y perceptrón.
#   frontera: los candidatos con la semilla de exploración y con la reservada.
#   protocolo-candidatos: cada candidato contra la regla base con la
#             referencia en Python y el criterio de aceptación.
#   algoritmo: todo lo anterior.
MOTOR := $(BUILD)/motor
MED   := docs/mediciones
CANDIDATOS_A := max_media guardia guardia_tope prudente kalman

.PHONY: motor test-candidatos generador politica exploracion experimentos frontera \
        protocolo-candidatos algoritmo

motor: $(MOTOR)
$(MOTOR): ref/motor/motor.c | $(BUILD)
	$(CC) -O2 -Wall -Wextra -o $@ $<

test-candidatos: $(MOTOR)
	$(PYTHON) ref/test_candidatos.py

generador:
	$(PYTHON) ref/generador.py --ajustar | tee $(MED)/generador_ajuste.txt
	$(PYTHON) ref/generador.py --validar | tee $(MED)/generador_validacion.txt
	$(PYTHON) ref/generador.py --redondeo | tee $(MED)/generador_redondeo.txt

politica:
	$(PYTHON) ref/politica_optima.py | tee $(MED)/politica_optima.txt

exploracion: $(MOTOR)
	$(PYTHON) ref/explorar.py > $(MED)/exploracion.txt
	@grep -c "^==" $(MED)/exploracion.txt | xargs echo "tablas en $(MED)/exploracion.txt:"

experimentos:
	$(PYTHON) ref/experimentos.py | tee $(MED)/experimentos.txt

frontera: $(MOTOR)
	$(PYTHON) ref/frontera.py --detalle > $(MED)/frontera.txt
	@grep -c "" $(MED)/frontera.txt | xargs echo "lineas en $(MED)/frontera.txt:"

protocolo-candidatos:
	for c in $(CANDIDATOS_A); do \
	  $(PYTHON) ref/protocolo.py --estrategia cand:$$c > $(MED)/protocolo_$$c.txt || exit 1; \
	  $(PYTHON) ref/protocolo.py --comparar cand:$$c >> $(MED)/protocolo_$$c.txt; \
	  tail -4 $(MED)/protocolo_$$c.txt; \
	done
	$(PYTHON) ref/protocolo.py --comparar trader:est=1,E=250,X=-40 | tee $(MED)/protocolo_kalman_base.txt | tail -4

algoritmo: generador politica exploracion experimentos frontera protocolo-candidatos
# === Fin del bloque del frente A ==============================================

# --- Mediciones reproducibles -----------------------------------------------
# Recursos, frecuencia máxima, shifter, PLL y CPI del repo base (etiqueta base-curso)
medir-base:
	tools/medir_base.sh

# Hallazgos sobre la serie de práctica
hallazgos:
	$(PYTHON) ref/p4_baseline.py tb/practica.csv
	$(PYTHON) ref/hallazgos.py tb/practica.csv

# === Espino segmentado: pipeline de 3 etapas (docs/espino_segmentado.md) =======
# El core por defecto sigue siendo el Espino base. Estos objetivos compilan la
# variante segmentada (-DESPINO_SEGMENTADO) o la de ROM combinacional
# (-DESPINO_ROM) y repiten sobre ellas las pruebas del core base.
.PHONY: tb-seg equiv-seg equiv-gemelo-seg cosim-seg cpi-seg riesgos paralelo paralelo-largo paralelo-largo-original \
        mutaciones timing-seg synth-seg pnr-seg bin-seg sim-bitstream-seg medir-espino \
        check-seg equiv-rom medir-ticks-seg formal-base equiv-seg-icarus

SEG_DEFS := -DESPINO_SEGMENTADO
JSON_SEG := $(BUILD)/$(TOP)_seg.json
ASC_SEG  := $(BUILD)/$(TOP)_seg.asc
BIN_SEG  := $(BUILD)/$(TOP)_seg.bin

# Copia del testbench oficial (solo cambia el nombre del archivo de salida)
# con el core segmentado: 4/4 y decisiones idénticas a la referencia.
tb-seg: $(HEX)
	DEFS="$(SEG_DEFS)" tools/equiv.sh seg_tb 100000 2000

# Equivalencia con la referencia, como make equiv, con el core segmentado
equiv-seg: $(HEX) equiv-gemelo-seg
	DEFS="$(SEG_DEFS)" SIM=verilator tools/equiv.sh seg_v_r3 100000 20000
	DEFS="$(SEG_DEFS)" SIM=verilator tools/equiv.sh seg_v_r2 1000000 20000
	DEFS="$(SEG_DEFS)" tools/equiv.sh seg_r2 1000000 200
	DEFS="$(SEG_DEFS)" tools/equiv.sh seg_r1 10000000 20
# Ejecución manual: los 20 000 ticks con Icarus (unos 13 minutos)
equiv-seg-icarus: $(HEX)
	DEFS="$(SEG_DEFS)" tools/equiv.sh seg_r3 100000 20000
equiv-gemelo-seg: $(GEMELO) $(HEX)
	GEM_OPTS=--pipeline ETQ=seg tools/equiv_gemelo.sh

# Lo mismo con el programa en una ROM combinacional (variante 2)
equiv-rom: $(HEX) | $(BUILD)
	mkdir -p $(BUILD)/rom
	$(PYTHON) $(ASM) sw/trade.s -o $(BUILD)/rom/trade.hex --rom $(BUILD)/rom/pochoco_rom.v > /dev/null
	DEFS="-DESPINO_ROM" SRC="$(SRC) $(BUILD)/rom/pochoco_rom.v" SIM=verilator tools/equiv.sh rom_v_r3 100000 20000

# Gemelo digital (con --pipeline) contra el RTL del core segmentado
cosim-seg: $(GEMELO) $(HEX)
	VARIANTE=segmentado tools/cosim.sh

# CPI y modelo de costo del core segmentado: ciclos = IC + loads + saltos tomados
cpi-seg: $(HEX) | $(BUILD)
	$(IVERILOG) -g2012 $(SEG_DEFS) -s tb_cpi -o $(BUILD)/tb_cpi_seg $(CELLS_SIM) $(SRC) tb/tb_cpi.sv
	$(VVP) -n $(BUILD)/tb_cpi_seg

# Riesgos de datos y de control: los programas de riesgos del Proyecto 3 en el
# base, en el segmentado y en el de ROM, comparando trazas (tools/riesgos.sh)
riesgos: $(GEMELO)
	tools/riesgos.sh

# Ejecución en paralelo del base y del segmentado con programas aleatorios,
# comparando registros y memoria en cada instrucción (tb/tb_paralelo.sv).
# paralelo: 4 programas de 25 000 instrucciones por configuración (en la
# integración continua). paralelo-largo: 16 de 100 000, más de un millón.
paralelo:
	tools/paralelo.sh 4 25000
paralelo-largo:
	ETQ=largo tools/paralelo.sh 16 100000 | tee docs/mediciones/paralelo_largo.txt
# Lo mismo con el generador anterior al 15/11, para medir cuánto cubría (T52)
paralelo-largo-original:
	ORIGINAL=1 ETQ=largo_original tools/paralelo.sh 16 100000 | tee docs/mediciones/paralelo_largo_original.txt

# Controles negativos: cinco errores puestos a propósito en el core segmentado
# deben ser detectados por riesgos y por paralelo (unos 2 minutos)
mutaciones: $(GEMELO)
	tools/mutaciones.sh | tee docs/mediciones/mutaciones.txt

# Cierre de timing: las 10 semillas de nextpnr deben cerrar a 25 MHz
timing-seg: $(HEX)
	DEFS="$(SEG_DEFS)" EXIGIR=1 tools/medir_variante.sh segmentado 10

# Síntesis, place and route y bitstream del core segmentado
synth-seg: $(JSON_SEG)
$(JSON_SEG): $(SRC) $(HEX) | $(BUILD)
	yosys -q -l $(BUILD)/yosys_seg.log \
	  -p "read_verilog $(SEG_DEFS) $(SRC); chparam -set MemFile \"$(HEX)\" $(TOP); synth_ice40 -top $(TOP) -json $(JSON_SEG)"
pnr-seg: $(ASC_SEG)
$(ASC_SEG): $(JSON_SEG) $(PCF)
	nextpnr-ice40 --hx1k --package vq100 --freq $(FREQ) --json $(JSON_SEG) --pcf $(PCF) \
	  --asc $(ASC_SEG) -l $(BUILD)/nextpnr_seg.log -q
	@grep -E "ICESTORM_LC|ICESTORM_RAM|Max frequency" $(BUILD)/nextpnr_seg.log | tail -3
bin-seg: $(BIN_SEG)
$(BIN_SEG): $(ASC_SEG)
	icepack $(ASC_SEG) $(BIN_SEG)
sim-bitstream-seg: $(ASC_SEG)
	tools/sim_bitstream.sh $(ASC_SEG) 2000

# Recursos, frecuencia máxima, recortes de celdas, CPI, MIPS y Ops/s del base
# y del segmentado, con los mismos programas. Deja docs/mediciones/espino_segmentado.txt
medir-espino: $(GEMELO) $(HEX)
	tools/medir_espino.sh

# Mediciones por tick del punto 3.2 con el core segmentado
# (docs/mediciones/ticks_segmentado.txt)
medir-ticks-seg: $(HEX)
	DEFS="$(SEG_DEFS)" tools/medir_ticks.sh segmentado

# Prueba formal de que el Espino base no cambió: con Pipeline = 0 las etapas
# IF e ID (con el decodificador y la ALU) son equivalentes a las del
# repositorio base, con los pases equiv_* de Yosys. Unos segundos.
formal-base:
	formal/base_sin_cambios/equiv.sh

# Lo que corre la integración continua para el core segmentado en cada push:
# modelo de costo, riesgos, ejecución en paralelo, los 20 000 ticks contra la
# referencia (Verilator y gemelo) y cierre de timing en 10 semillas.
# Quedan como ejecución manual: tb-seg y equiv-seg (Icarus), cosim-seg,
# mutaciones y paralelo-largo.
check-seg: formal-base cpi-seg riesgos paralelo equiv-gemelo-seg timing-seg
	DEFS="$(SEG_DEFS)" SIM=verilator tools/equiv.sh seg_v_r3 100000 20000

# === Espino barrel: 4 hilos por un pipeline de 4 etapas (docs/espino_barrel.md) ===
# El core por defecto sigue siendo el Espino base. Estos objetivos compilan la
# variante barrel (-DESPINO_BARREL). Sus programas empiezan con la tabla de
# arranque (el hilo t parte en la dirección 4 t); tools/barrel/tabla.py la
# antepone a un programa de un hilo, como sw/trade.s. Los scripts están en
# tools/barrel/, los testbenches en tb/barrel/, los programas de prueba en
# sw/barrel/ y las salidas quedan en docs/mediciones/barrel/.
#
# Puerta de simulación con un programa de un hilo (docs/puertas.md):
#   barrel-oficial       criterio 1: testbench oficial sin modificar, 4/4
#   barrel-timing        criterio 3: 25 MHz en 10 de 10 semillas
#   barrel-verif         criterio 5: cada hilo contra el Espino base, instrucción
#                        por instrucción. Campaña lineal (más de 5 millones de
#                        instrucciones, más de 90 % distintas) y campaña de
#                        lazos. Unos 6 minutos con 12 procesos.
#   barrel-mutaciones    criterio 5: 21 errores puestos a propósito, todos detectados
# Aislamiento entre hilos y memoria compartida:
#   barrel-formal        propiedades de estructura con SymbiYosys (10 segundos)
#   barrel-aislamiento   cuatro hilos a la vez, cada uno idéntico a su corrida
#                        solo en el Espino base, y las propiedades formales
#   barrel-compartida    cuatro hilos sobre la misma zona de memoria contra el
#                        modelo de turnos, con su control negativo
# Mediciones y pruebas complementarias:
#   barrel-humo, barrel-cpi, barrel-ticks, barrel-equiv, barrel-equiv-icarus,
#   barrel-spi, barrel-trazas, barrel-netlist, barrel-netlist-aleatorio,
#   barrel-sin-tabla, barrel-recursos, barrel-bitstream, barrel-icebram
# check-barrel es lo que corre la integración continua en cada push.
# barrel-completo es la ejecución manual con todo lo demás.
.PHONY: barrel-oficial barrel-timing barrel-verif barrel-verif-corta barrel-mutaciones barrel-formal \
        barrel-aislamiento barrel-compartida barrel-humo barrel-cpi barrel-ticks barrel-equiv \
        barrel-equiv-icarus barrel-equiv-ronda1 barrel-spi barrel-trazas barrel-netlist \
        barrel-netlist-aleatorio barrel-sin-tabla barrel-recursos barrel-bitstream barrel-icebram \
        check-barrel barrel-completo

BARREL_JOBS ?= 12
HEX_BARREL  := $(BUILD)/barrel/sw/trade_h0.hex

# sw/trade.s en el hilo 0, con la tabla de arranque delante
$(HEX_BARREL): sw/trade.s tools/barrel/tabla.py $(ASMDEP)
	mkdir -p $(dir $@)
	$(PYTHON) tools/barrel/tabla.py 0 sw/trade.s > $(basename $@).s
	$(PYTHON) $(ASM) $(basename $@).s -o $@ > /dev/null

barrel-oficial:
	tools/barrel/oficial.sh
barrel-timing: $(HEX_BARREL)
	DEFS=-DESPINO_BARREL HEX=$(HEX_BARREL) EXIGIR=1 tools/medir_variante.sh barrel 10 > docs/mediciones/barrel/timing.txt; \
	  r=$$?; cat docs/mediciones/barrel/timing.txt; exit $$r
barrel-verif:
	PUERTA=1 JOBS=$(BARREL_JOBS) tools/barrel/verif.sh
barrel-verif-corta:
	ESCALA=0.03 JOBS=4 SALIDA=$(BUILD)/barrel/verif_corta.txt tools/barrel/verif.sh
barrel-mutaciones:
	JOBS=$(BARREL_JOBS) tools/barrel/mutaciones.sh
barrel-formal:
	tools/barrel/formal.sh
barrel-aislamiento: barrel-formal
	GRUPOS="B C T L M" ESCALA=0.25 JOBS=$(BARREL_JOBS) SALIDA=docs/mediciones/barrel/aislamiento.txt tools/barrel/verif.sh
barrel-compartida:
	GRUPOS="D N K J P" ESCALA=0.25 JOBS=$(BARREL_JOBS) SALIDA=docs/mediciones/barrel/compartida.txt tools/barrel/verif.sh

barrel-humo:
	tools/barrel/humo.sh
barrel-cpi:
	tools/barrel/medir_cpi.sh
barrel-ticks:
	tools/barrel/medir_ticks.sh
barrel-equiv:
	tools/barrel/equiv_ref.sh
barrel-equiv-ronda1:
	RONDA1=1 tools/barrel/equiv_ref.sh
barrel-equiv-icarus:
	tools/barrel/equiv_icarus.sh
barrel-spi:
	tools/barrel/verif_spi.sh
barrel-trazas:
	tools/barrel/verif_trazas.sh 12
barrel-netlist:
	tools/barrel/netlist.sh
barrel-netlist-aleatorio:
	tools/barrel/netlist_aleatorio.sh 4
barrel-sin-tabla:
	tools/barrel/sin_tabla.sh
barrel-recursos:
	tools/barrel/medir_recursos.sh 10
barrel-bitstream:
	tools/barrel/bitstream.sh
barrel-icebram:
	tools/barrel/icebram_prueba.sh

check-barrel: barrel-formal barrel-humo barrel-verif-corta barrel-oficial barrel-equiv barrel-timing
barrel-completo: barrel-verif barrel-mutaciones barrel-aislamiento barrel-compartida barrel-trazas barrel-spi \
                 barrel-cpi barrel-ticks barrel-netlist barrel-netlist-aleatorio barrel-sin-tabla

clean:
	rm -rf $(BUILD) decisiones.csv

# ---------------------------------------------------------------------------
# Extensión de la ISA en custom-0 sobre el Espino barrel (docs/extension_isa.md)
# ---------------------------------------------------------------------------
# Tres instrucciones (emad, devk y mulstep), elegibles al compilar con
# -DESPINO_XD o con -DESPINO_XD_EMAD, -DESPINO_XD_DEVK y -DESPINO_XD_MULSTEP.
# Scripts en tools/xd, testbenches en tb/xd, propiedades en formal/xd, programa
# de prueba en sw/xd y salidas en docs/mediciones/xd.
#   xd-tabla         codificación y ejemplos, desde el modelo ref/xd.py
#   xd-tb            los dos módulos solos contra el modelo, con mutaciones
#   xd-formal        cada instrucción contra su especificación (SymbiYosys), el
#                    core con la extensión contra el de P1 (equiv_*) y mutaciones
#   xd-timing        25 MHz en 10 de 10 semillas, los 7 subconjuntos
#   xd-verif         cada hilo contra el Espino base más la especificación,
#                    instrucción por instrucción: campaña completa, con el
#                    criterio 5 de la puerta
#   xd-verif-corta   lo mismo con la décima parte de los programas
#   xd-mutaciones    controles negativos de esa comparación
#   xd-oficial       testbench oficial sin modificar (4/4) y 20 000 ticks contra
#                    la referencia, con sw/trade.s y con sw/xd/trade_xd.s
# check-xd es lo que corre la integración continua en cada push.
# xd-completo es la ejecución manual con lo demás.
.PHONY: xd-tabla xd-tb xd-formal xd-timing xd-verif xd-verif-corta xd-mutaciones xd-oficial xd-timing-todo check-xd xd-completo

xd-tabla:
	@mkdir -p docs/mediciones/xd
	python3 ref/xd.py --tabla | tee docs/mediciones/xd/codificacion.txt
xd-tb:
	tools/xd/tb_modulos.sh
xd-formal:
	tools/xd/formal.sh
xd-timing:
	tools/xd/timing.sh 10
xd-verif:
	PUERTA=1 JOBS=$(BARREL_JOBS) tools/xd/verif.sh
xd-verif-corta:
	ESCALA=0.1 JOBS=$(BARREL_JOBS) SALIDA=build/xd/verificacion_corta.txt tools/xd/verif.sh
xd-mutaciones:
	JOBS=$(BARREL_JOBS) tools/xd/mutaciones.sh
xd-oficial:
	tools/xd/oficial.sh

# En la integración continua el timing se mide solo con las tres instrucciones
# (la tabla de los 7 subconjuntos es make xd-timing, 6 minutos)
xd-timing-todo:
	MASCARAS=7 SALIDA=build/xd/timing_todo.txt tools/xd/timing.sh 10

check-xd: xd-tb xd-formal xd-verif-corta xd-oficial xd-timing-todo
xd-completo: xd-verif xd-mutaciones

# --- Fondo en un chip: sw/fondo.s en los peldaños R1 y R2 (docs/fondo.md) -------
# R1 es el barrel con emad y devk y la tabla de parámetros en su BRAM. R2 es R1
# con el vigilante y SB_WARMBOOT (docs/tabla_vigilante.md). El peldaño se elige
# con HW=r1 (por defecto) o HW=r2. Cada objetivo deja su salida en
# docs/mediciones/fondo/$(HW)/. Los de check-fondo son las versiones cortas, que
# corren en la integración continua y dejan su salida en build/fondo/$(HW)/.
.PHONY: test-fondo check-tabla fondo-hex fondo-oficial fondo-equiv fondo-equiv-ronda1 fondo-series fondo-fases \
        fondo-degradacion fondo-controles fondo-estres fondo-ticks fondo-timing fondo-bitstreams fondo-criterio5 \
        check-fondo fondo-puerta fondo-completo vig-tb vig-formal vig-relevo check-vigilante
HW ?= r1
export HW
R1_DEFS := -DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA
R2_DEFS := $(R1_DEFS) -DESPINO_VIGILANTE
FONDO_DEFS := $(if $(filter r2,$(HW)),$(R2_DEFS),$(R1_DEFS))
FONDO_JOBS ?= 6

test-fondo:
	$(PYTHON) ref/test_fondo.py
# sw/fondo_tabla.hex es el contenido de la BRAM de la tabla: sale de ref/fondo.py
check-tabla:
	@mkdir -p $(BUILD) && $(PYTHON) ref/fondo.py --tabla-hex $(BUILD)/fondo_tabla.hex && cmp $(BUILD)/fondo_tabla.hex sw/fondo_tabla.hex \
	  && echo "PASS sw/fondo_tabla.hex corresponde a ref/fondo.py"
fondo-hex:
	mkdir -p $(BUILD)/fondo
	$(PYTHON) $(ASM) sw/fondo.s -o $(BUILD)/fondo/fondo.hex
# Criterio 1: testbench oficial sin modificar (Icarus, unos 5 minutos)
fondo-oficial:
	tools/fondo/oficial.sh
# Criterio 2: 20 000 ticks a 0,1 ms y 1 ms y una serie de cada familia; 10 ms aparte (35 minutos)
fondo-equiv:
	JOBS=$(FONDO_JOBS) tools/fondo/equiv.sh
fondo-equiv-ronda1:
	RONDA1=1 JOBS=$(FONDO_JOBS) tools/fondo/equiv.sh
# Criterio 2: 1 050 series sintéticas de 2000 ticks por el RTL
fondo-series:
	JOBS=$(FONDO_JOBS) tools/fondo/series.sh
# Criterio 3: timing en 10 semillas del hardware exacto, con el programa cargado
fondo-timing: fondo-hex
	mkdir -p docs/mediciones/fondo/$(HW)
	DEFS="$(FONDO_DEFS)" HEX=$(BUILD)/fondo/fondo.hex EXIGIR=1 tools/medir_variante.sh fondo_$(HW) 10 > docs/mediciones/fondo/$(HW)/timing.txt; \
	  r=$$?; cat docs/mediciones/fondo/$(HW)/timing.txt; exit $$r
# Criterio 4: peor caso barriendo la fase
fondo-fases:
	JOBS=$(FONDO_JOBS) tools/fondo/fases.sh
# Criterio 6: degradación
fondo-degradacion:
	JOBS=$(FONDO_JOBS) tools/fondo/degradacion.sh
# Controles negativos: errores puestos a propósito que las pruebas deben detectar
fondo-controles:
	JOBS=$(FONDO_JOBS) tools/fondo/controles.sh
# Criterio 7: matriz de estrés
fondo-estres:
	JOBS=$(FONDO_JOBS) tools/fondo/estres.sh
# Punto 3.2 del enunciado: mediciones por tick
fondo-ticks:
	tools/fondo/ticks.sh
# Criterio 8 y kit de icebram: bitstreams R1 y R2 simulados desde el .asc, cambio
# de tabla y de programa con icebram, vigilante dentro del bitstream e imagen
# múltiple. Construye los dos peldaños (no usa HW). Unos 25 minutos.
fondo-bitstreams:
	tools/fondo/bitstreams.sh

# Criterio 5 en la configuración exacta: campaña del core y mutaciones con la
# máscara de emad y devk sobre el SoC del peldaño. Unos 40 minutos.
fondo-criterio5:
	JOBS=$(BARREL_JOBS) tools/fondo/criterio5.sh

# Vigilante (docs/tabla_vigilante.md): testbench del módulo, propiedades formales
# con SymbiYosys y relevo de punta a punta con las dos imágenes en el mismo
# testbench (R2 con el supervisor colgado y la imagen de respaldo).
vig-tb:
	tools/vigilante/tb.sh
vig-formal:
	tools/vigilante/formal.sh
vig-relevo:
	tools/vigilante/relevo.sh
check-vigilante: vig-tb vig-formal vig-relevo

check-fondo: test-fondo check-tabla fondo-oficial
	CORTA=1 JOBS=$(FONDO_JOBS) SALIDA=$(BUILD)/fondo/$(HW)/equiv_corta.txt tools/fondo/equiv.sh
	POR_FAMILIA=4 JOBS=$(FONDO_JOBS) SALIDA=$(BUILD)/fondo/$(HW)/series_corta.txt tools/fondo/series.sh
	CORTA=1 JOBS=$(FONDO_JOBS) SALIDA=$(BUILD)/fondo/$(HW)/fases_corta.txt tools/fondo/fases.sh
	CORTA=1 JOBS=$(FONDO_JOBS) SALIDA=$(BUILD)/fondo/$(HW)/degradacion_corta.txt tools/fondo/degradacion.sh
	JOBS=$(FONDO_JOBS) SALIDA=$(BUILD)/fondo/$(HW)/controles_corta.txt tools/fondo/controles.sh
	JOBS=$(FONDO_JOBS) SALIDA=$(BUILD)/fondo/$(HW)/estres_corta.txt tools/fondo/estres.sh
# La puerta de simulación completa de un peldaño, salvo los criterios 5 (make
# fondo-criterio5) y 8 (make fondo-bitstreams)
fondo-puerta: test-fondo check-tabla fondo-oficial fondo-equiv-ronda1 fondo-series fondo-timing fondo-fases \
              fondo-degradacion fondo-controles fondo-estres fondo-ticks
fondo-completo:
	$(MAKE) fondo-puerta HW=r1
	$(MAKE) fondo-puerta HW=r2
	$(MAKE) fondo-bitstreams
	$(MAKE) fondo-criterio5 HW=r1
	$(MAKE) fondo-criterio5 HW=r2

# --- Gemelo del barrel (paquete P4, docs/gemelo.md sección 7) -----------------
# cosim-barrel: traza, ticks y decisiones del RTL (tb/barrel/tb_gemelo.sv)
#   contra el gemelo en 21 configuraciones, controles negativos y gemelo con y
#   sin atajo. Unos 6 minutos. La versión corta corre en la integración continua.
#   El hardware del fondo es el de R1 (con la tabla en su BRAM).
# fondo-gemelo-series: 1 051 series a los tres períodos contra ref/fondo.py.
# fondo-estres-rtl60 / fondo-estres-gemelo: la matriz de estrés de R0 (60 casos,
#   tools/estres.py) con la referencia del fondo, por el RTL y por el gemelo. Es
#   la validación cruzada del gemelo; la matriz de la puerta es make fondo-estres.
#   Como en esa, los casos con menos de 600 ciclos entre transacciones (SCLK de
#   100 kHz a 0,1 ms) son exploración: es el límite documentado de R1 (T86).
# El gemelo modela R1: el vigilante de R2 no existe en el gemelo, así que estas
# salidas van a docs/mediciones/fondo/r1/.
.PHONY: cosim-barrel cosim-barrel-corta fondo-gemelo-series fondo-estres-rtl60 fondo-estres-gemelo fondo-sclk-minimo
FONDO_MINIMOS := 33500,38300
GEMELO_R1 := --barrel --xd 3 --tabla sw/fondo_tabla.hex
cosim-barrel: $(GEMELO)
	$(PYTHON) tools/gemelo_barrel.py --jobs $(FONDO_JOBS)
cosim-barrel-corta: $(GEMELO)
	$(PYTHON) tools/gemelo_barrel.py --corta --jobs $(FONDO_JOBS)
fondo-gemelo-series: $(GEMELO) fondo-hex
	$(PYTHON) tools/fondo/gemelo_series.py --practica
fondo-estres-rtl60: fondo-hex
	mkdir -p docs/mediciones/fondo/r1
	DEFS="$(R1_DEFS)" $(PYTHON) tools/estres.py --ref fondo --hex $(BUILD)/fondo/fondo.hex --etiqueta fondo_r1 \
	  --solo estres --periodos-minimos $(FONDO_MINIMOS) --presupuesto-minimo 600 > docs/mediciones/fondo/r1/estres_rtl60.txt; \
	  r=$$?; cat docs/mediciones/fondo/r1/estres_rtl60.txt; exit $$r
fondo-estres-gemelo: fondo-hex
	mkdir -p docs/mediciones/fondo/r1
	$(PYTHON) tools/estres.py --ref fondo --motor gemelo --gemelo-opts "$(GEMELO_R1)" --hex $(BUILD)/fondo/fondo.hex \
	  --etiqueta fondo_gemelo --solo estres --periodos-minimos $(FONDO_MINIMOS) --presupuesto-minimo 600 > docs/mediciones/fondo/r1/estres_gemelo.txt; \
	  r=$$?; cat docs/mediciones/fondo/r1/estres_gemelo.txt; exit $$r
# Exploración: SCLK mínimo a 0,1 ms y período mínimo a 1 MHz, R0 y R1, con el gemelo
fondo-sclk-minimo: fondo-hex
	$(PYTHON) tools/fondo/sclk_minimo.py

# --- Autoprueba en placa (paquete P6, docs/autoprueba.md) ---------------------
# autoprueba-r0: firma esperada (gemelo y referencia), bitstream, simulación del
#   RTL con los tres botones y del bitstream ruteado con SW3. Unos 20 minutos.
#   Deja build/autoprueba/r0/autoprueba_r0.bin y docs/mediciones/autoprueba_r0.txt.
.PHONY: autoprueba-r0 autoprueba-r0-firma
autoprueba-r0:
	$(PYTHON) tools/autoprueba.py todo r0
autoprueba-r0-firma:
	$(PYTHON) tools/autoprueba.py firma r0

# --- Anticipación (paquete P8, docs/contingencia.md) ---------------------------
# medidor: testbench, controles negativos, 10 semillas, bitstream y su
#   simulación por los pines del medidor de la maestra SPI (1 minuto).
# r0-molde: molde de R0 para icebram, desde el commit de R0 (necesita el
#   historial completo).
# p8-matriz: período, SCLK, largo de ronda, comisión y caja en R0, R1 y R2,
#   con el gemelo (10 s). p8-matriz-rapida deja la salida en build/p8/.
# retune-control: con las reglas publicadas, retune no cambia nada y los .bin
#   que arma son los de bitstreams/, byte por byte.
# contingencia: juegos preconstruidos para comisión de 20 y 50, simulados por
#   los pines (45 minutos).
.PHONY: medidor r0-molde p8-matriz p8-matriz-rapida retune-control contingencia check-p8
medidor:
	tools/medidor.sh
r0-molde:
	tools/p8/r0_molde.sh
p8-matriz: $(GEMELO) fondo-hex
	$(PYTHON) tools/p8/matriz.py
p8-matriz-rapida: $(GEMELO) fondo-hex
	$(PYTHON) tools/p8/matriz.py --rapida --salida $(BUILD)/p8
retune-control: $(GEMELO) fondo-hex
	$(PYTHON) tools/retune.py --comision 5 --caja 10000 --control
contingencia: $(GEMELO) fondo-hex
	tools/p8/contingencia.sh
check-p8: medidor p8-matriz-rapida retune-control

# --- Diseño por defecto (docs/peldano.md) ---------------------------------------
# peldano-oficial: el comando del encabezado de tb/tb_proyecto_4.sv tal cual, sin
#   definiciones, con el diseño que hoy es el de por defecto: 4/4 y decisiones.csv
#   igual a su referencia. Corre en la integración continua.
# peldano-probar: el cambio a R1 (o R2) hecho en una copia, con el comando
#   oficial y otras pruebas después del cambio. No toca este árbol.
# peldano-fijar: el cambio de verdad, en este árbol, sin commit. Después del 26/11.
.PHONY: peldano-oficial peldano-probar peldano-fijar
PELDANO ?= r1
peldano-oficial:
	$(PYTHON) tools/peldano.py oficial
peldano-probar:
	$(PYTHON) tools/peldano.py probar $(PELDANO) > docs/mediciones/peldano_probar_$(PELDANO).txt; \
	  r=$$?; cat docs/mediciones/peldano_probar_$(PELDANO).txt; exit $$r
peldano-fijar:
	$(PYTHON) tools/peldano.py fijar $(PELDANO)

# --- Co-diseño para la pauta (paquete P7, docs/codiseno.md) --------------------
# Tabla de variantes del punto 3.3, perfilado con Amdahl, escalera de la clase 7,
# roofline, edición ASIC y resultados negativos. Todo queda en docs/mediciones/p7/.
#   p7-recursos   celdas, LUT4, BRAM y fmax de las seis variantes, 10 semillas
#                 (unos 4 minutos; no se repite si la huella de las fuentes no cambió)
#   p7-medir      ciclos por tick a los tres períodos y perfil por dirección, con el gemelo
#   p7-rtl        confirmación con el RTL: R0 y segmentado tick por tick (Verilator), R1 y R2
#                 contra la medición del RTL de P5 (unos 3 minutos)
#   p7-pll        el PLL en el VQ100 y en un TQ144 hipotético (unos 2 minutos)
#   p7-doble      el duplicador de reloj de la factibilidad, reproducido (unos 15 minutos)
#   p7-rapido     tablas, figuras, CSV y cifras.tex desde las mediciones guardadas, sin sintetizar
#   p7-variantes  la tabla de variantes con sus mediciones
#   p7-amdahl     el perfil y Amdahl con sus mediciones
#   p7            todo lo anterior
#   p7-caida-seg  por qué la fmax mínima del segmentado bajó de 51,59 (P1) a 45,34 MHz (P7):
#                 el mismo comando en cuatro commits, 40 semillas, órdenes de lectura y
#                 equivalencia formal (unos 3 minutos; no es parte de p7)
.PHONY: p7 p7-rapido p7-variantes p7-amdahl p7-recursos p7-medir p7-rtl p7-pll p7-doble p7-caida-seg
p7-caida-seg:
	tools/p7/caida_segmentado.sh 40
p7-recursos:
	tools/p7/recursos.sh 10
p7-medir: $(GEMELO)
	$(PYTHON) tools/p7/medir.py
p7-rtl: p7-medir
	tools/p7/rtl.sh
p7-pll:
	tools/p7/pll.sh 10
p7-doble:
	tools/p7/doble_frecuencia.sh
p7-rapido:
	$(PYTHON) tools/p7/tablas.py
p7-variantes: p7-recursos p7-medir p7-rtl
	$(PYTHON) tools/p7/tablas.py > /dev/null && cat docs/mediciones/p7/variantes.txt
p7-amdahl: p7-medir
	$(PYTHON) tools/p7/tablas.py > /dev/null && cat docs/mediciones/p7/perfil.txt docs/mediciones/p7/amdahl.txt
p7: p7-recursos p7-medir p7-rtl p7-pll p7-doble
	$(PYTHON) tools/p7/tablas.py

# --- Informe (informe/informe.tex) -------------------------------------------------
# report: rehace informe/generado/ (cifras y tablas) desde las referencias y
#   docs/mediciones/, y compila el PDF si hay LaTeX (latexmk). El peldaño sale de
#   rtl/00_peldano.v; sin él, de PELDANO (por defecto r0, como el comando oficial).
.PHONY: report informe
report: p7-rapido informe
informe: $(GEMELO) fondo-hex
	$(PYTHON) tools/report.py $(if $(PELDANO_INFORME),--peldano $(PELDANO_INFORME))
	@if command -v latexmk > /dev/null; then \
	  cd informe && latexmk -pdf -interaction=nonstopmode -halt-on-error informe.tex > /dev/null && echo "informe/informe.pdf listo"; \
	else echo "No hay LaTeX en esta maquina: el PDF lo compila la integracion continua (trabajo informe)"; fi

# autoprueba-r1 / autoprueba-r2: lo mismo para R1 y R2 (docs/autoprueba.md,
#   sección 8), con el control negativo de otra tabla. R2 además: modo continuo
#   sin disparo del vigilante, supervisor colgado con disparo, imagen testigo,
#   las dos imágenes múltiples y media hora de la caminata en el gemelo. Unos
#   25 minutos. Deja docs/mediciones/autoprueba_r1.txt y autoprueba_r2.txt.
# relevo-placa: tiempo esperado del relevo y prueba sin placa de
#   tools/medir_relevo.py (docs/mediciones/relevo_placa.txt).
.PHONY: autoprueba-r1 autoprueba-r1-firma autoprueba-r2 autoprueba-r2-firma relevo-placa
autoprueba-r1:
	$(PYTHON) tools/autoprueba.py todo r1
autoprueba-r1-firma:
	$(PYTHON) tools/autoprueba.py firma r1
autoprueba-r2:
	$(PYTHON) tools/autoprueba.py todo r2
autoprueba-r2-firma:
	$(PYTHON) tools/autoprueba.py firma r2
relevo-placa:
	$(PYTHON) tools/medir_relevo.py --esperado > docs/mediciones/relevo_placa.txt; \
	  $(PYTHON) tools/medir_relevo.py --prueba >> docs/mediciones/relevo_placa.txt; r=$$?; \
	  cat docs/mediciones/relevo_placa.txt; exit $$r
# r2-falla: R2 con el supervisor colgado y R0 de respaldo, para ver el relevo con
#   la maestra real (bitstreams/r2_falla_multi.bin).
.PHONY: r2-falla
r2-falla:
	tools/p8/r2_falla.sh

# Edición de exhibición con las tres instrucciones (docs/mediciones/p9/exhibicion.txt)
.PHONY: exhibicion
exhibicion:
	tools/p9/exhibicion.sh

# --- Evaluación de la regla zscore de Vicente (docs/zscore.md) -------------------
# zscore-arnes      compila build/zscore/arnes (el arnés de factibilidad/retorno con zscore y el fondo por nombre)
# zscore-series     series de la semilla 4, la reservada (T128), en build/zscore/series (unos 3 minutos)
# zscore-validar    zscore.c contra ref/zscore.py, contra la referencia de Vicente (si está su repositorio) y
#                   el fondo por nombre contra el de la factibilidad
# zscore            exploración con la semilla 0: protocolo, meseta a 2000 y 20 000 ticks, fondos, duelo y
#                   la grilla en la serie de práctica (unos 6 minutos)
# zscore-reservada  los cuatro finalistas con la semilla 4. Se corrió una vez (docs/bitacora/zscore.md)
.PHONY: zscore zscore-arnes zscore-series zscore-validar zscore-reservada
ZSCORE_ENV = RETORNO_SERIES=$(CURDIR)/build/zscore/series HILOS=20
ZSCORE_M = docs/mediciones/zscore
zscore-arnes:
	$(MAKE) -C ref/zscore
zscore-series:
	$(PYTHON) ref/zscore/series_reservadas.py
zscore-validar: zscore-arnes
	$(PYTHON) ref/zscore/validar.py
zscore: zscore-arnes zscore-series zscore-validar
	mkdir -p $(ZSCORE_M)
	$(PYTHON) ref/protocolo.py --estrategia oficial --comparar zscore > $(ZSCORE_M)/protocolo_s0.txt
	$(ZSCORE_ENV) $(PYTHON) ref/zscore/meseta.py --largo 2000 --semilla 0 > /dev/null
	$(ZSCORE_ENV) $(PYTHON) ref/zscore/meseta.py --largo 20000 --semilla 0 --interior > /dev/null
	$(ZSCORE_ENV) $(PYTHON) ref/zscore/meseta.py --largo 20000 --semilla 0 --parada > /dev/null
	$(ZSCORE_ENV) $(PYTHON) ref/zscore/tabla.py --largo 2000 --semilla 0 --salida $(ZSCORE_M)/tabla_n2000_s0.txt > /dev/null
	$(ZSCORE_ENV) $(PYTHON) ref/zscore/duelo.py --largo 2000 --semilla 0 --salida $(ZSCORE_M)/duelo_n2000_s0.txt \
	  --candidatas "zscore;zscore:km=5,kd=7,num=6,den=4;zscore:km=5,kd=6,num=7,den=4;zscore:km=5,kd=6,num=8,den=4" > /dev/null
	$(ZSCORE_ENV) $(PYTHON) ref/zscore/practica.py > /dev/null
	$(ZSCORE_ENV) $(PYTHON) ref/zscore/trozos.py --puntos > /dev/null
	@echo "Resultados en $(ZSCORE_M)/"
zscore-reservada: zscore-arnes zscore-series
	ref/zscore/reservada.sh

# Ensayo general (docs/checklist_1dic.md): las tres rondas para cada peldaño con series
# nuevas, por el RTL, mostrando lo que vería la maestra (docs/mediciones/ensayo.txt).
# Unos 5 minutos con 5 procesos.
.PHONY: ensayo
ensayo:
	$(PYTHON) tools/ensayo.py --jobs 5

# Registrador de la maestra para el 26/11 (docs/registrador.md): testbench, controles
# negativos, 10 semillas, bitstream, simulación del bitstream ruteado y prueba de
# tools/registrador.py (unos 6 minutos). Resultado en docs/mediciones/registrador.txt.
.PHONY: registrador
registrador:
	tools/registrador.sh
