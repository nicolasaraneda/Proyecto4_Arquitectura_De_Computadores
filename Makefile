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
SRC := $(wildcard rtl/*.v rtl/espino_core/*.v)

# Programa. $readmemh lo deja dentro del bitstream al sintetizar, así que el
# .hex es prerrequisito de la síntesis.
PYTHON ?= python3
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

# Productos de síntesis
JSON := $(BUILD)/$(TOP).json
ASC  := $(BUILD)/$(TOP).asc
BIN  := $(BUILD)/$(TOP).bin
FREQ ?= 25

.PHONY: all asm test-asm tb tb-param cpi check check-hex synth pnr bin prog \
        medir-base hallazgos clean

# Objetivo por defecto: todo lo verificable sin la placa
all: check

$(BUILD):
	mkdir -p $(BUILD)

# --- Ensamblado -------------------------------------------------------------
sw/%.hex: sw/%.s $(ASMDEP)
	$(PYTHON) $(ASM) $< -o $@

asm: $(HEX)

# Tests del ensamblador (73 tests, incluye la comparación con los .hex del repo base)
test-asm:
	cd tools/asm && $(PYTHON) -m unittest discover -s tests -t .

# sw/trade.hex está versionado: se comprueba que corresponde a sw/trade.s
check-hex: | $(BUILD)
	$(PYTHON) $(ASM) sw/trade.s -o $(BUILD)/trade_check.hex >/dev/null
	cmp $(BUILD)/trade_check.hex $(HEX)

# --- Testbench oficial, sin modificar ---------------------------------------
# Mismos comandos que el encabezado de tb/tb_proyecto_4.sv. Falla si no es 4/4.
tb: $(HEX) | $(BUILD)
	$(IVERILOG) -g2012 -s tb_proyecto_4 -o $(BUILD)/tb_p4 $(CELLS_SIM) $(SRC) $(TB_OFICIAL)
	$(VVP) -n $(BUILD)/tb_p4 | tee $(BUILD)/tb_p4.log
	@grep -q "Testbenchs aprobados: 4/4" $(BUILD)/tb_p4.log

# Copia del testbench con otro período o número de ticks, por ejemplo:
#   make tb-param PERIODO_NS=1000000 NTICKS=500
tb-param: $(HEX) | $(BUILD)
	sed -e 's/PERIODO_NS = [0-9]*;/PERIODO_NS = $(PERIODO_NS);/' \
	    -e 's/NTICKS     = [0-9]*;/NTICKS     = $(NTICKS);/' \
	    $(TB_OFICIAL) > $(BUILD)/tb_p4_param.sv
	$(IVERILOG) -g2012 -s tb_proyecto_4 -o $(BUILD)/tb_p4_param $(CELLS_SIM) $(SRC) $(BUILD)/tb_p4_param.sv
	$(VVP) -n $(BUILD)/tb_p4_param | tee $(BUILD)/tb_p4_param.log
	@grep -q "Testbenchs aprobados: 4/4" $(BUILD)/tb_p4_param.log

# CPI medido en simulación (instrucciones completadas y ciclos, por clase)
cpi: $(HEX) | $(BUILD)
	$(IVERILOG) -g2012 -s tb_cpi -o $(BUILD)/tb_cpi $(CELLS_SIM) $(SRC) tb/tb_cpi.sv
	$(VVP) -n $(BUILD)/tb_cpi

# Lo que corre la integración continua en cada push
check: test-asm check-hex tb

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

# Programar la placa (lo ejecuta una persona, con la Go Board conectada)
prog: $(BIN)
	iceprog $(BIN)

# --- Mediciones reproducibles -----------------------------------------------
# Recursos, frecuencia máxima, shifter, PLL y CPI del repo base (etiqueta base-curso)
medir-base:
	tools/medir_base.sh

# Hallazgos sobre la serie de práctica
hallazgos:
	$(PYTHON) ref/p4_baseline.py tb/practica.csv
	$(PYTHON) ref/hallazgos.py tb/practica.csv

clean:
	rm -rf $(BUILD) decisiones.csv
