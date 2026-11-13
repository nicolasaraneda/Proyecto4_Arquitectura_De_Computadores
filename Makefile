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
SERIE      ?= tb/practica.csv

# Productos de síntesis
JSON := $(BUILD)/$(TOP).json
ASC  := $(BUILD)/$(TOP).asc
BIN  := $(BUILD)/$(TOP).bin
FREQ ?= 25

.PHONY: all asm test-asm test-ref tb tb-param cpi check check-hex synth pnr bin prog \
        equiv equiv-r3 equiv-r2 equiv-r1 equiv-verilator equiv-largo medir-ticks \
        sim-bitstream guardar-bitstream medir-base hallazgos clean

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
tb: $(HEX) | $(BUILD)
	$(IVERILOG) -g2012 -s tb_proyecto_4 -o $(BUILD)/tb_p4 $(CELLS_SIM) $(SRC) $(TB_OFICIAL)
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
#   equiv-r3: los 20 000 ticks de práctica al período de la ronda 3, con Icarus
#             (unos 13 minutos).
#   equiv-r2 y equiv-r1: pocos ticks a 1 ms y 10 ms con Icarus, para validar el
#             modelo de los precios que se pierden durante el reset.
#   equiv-verilator: los 20 000 ticks a 0,1 ms y a 1 ms con Verilator.
#   equiv-largo: los 20 000 ticks a 10 ms con Verilator (unos 25 minutos). No
#             corre en la integración continua.
equiv: equiv-r3 equiv-r2 equiv-r1 equiv-verilator

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

# Mercado y referencia: pruebas en Python (ref/test_ref.py)
test-ref:
	$(PYTHON) ref/test_ref.py

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

# Lo que corre la integración continua en cada push
check: test-asm test-ref check-hex tb

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
