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
GEMELO := $(BUILD)/gemelo
BIN  := $(BUILD)/$(TOP).bin
FREQ ?= 25

.PHONY: all asm test-asm test-ref tb tb-param cpi check check-hex synth pnr bin prog \
        equiv equiv-r3 equiv-r2 equiv-r1 equiv-verilator equiv-largo medir-ticks \
        equiv-icarus equiv-completo equiv-gemelo-20k \
        equiv-series equiv-gemelo gemelo cosim protocolo \
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
FAMILIAS := remuestreo paseo tendencia reversion dos_componentes saltos \
            cambio_volatilidad cambio_de_caracter plana borde_bajo borde_alto
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

# El binario sw/trade.hex, corrido en el gemelo sobre las 3010 series del
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

# === Espino segmentado: pipeline de 3 etapas (docs/espino_segmentado.md) =======
# El core por defecto sigue siendo el Espino base. Estos objetivos compilan la
# variante segmentada (-DESPINO_SEGMENTADO) o la de ROM combinacional
# (-DESPINO_ROM) y repiten sobre ellas las pruebas del core base.
.PHONY: tb-seg equiv-seg equiv-gemelo-seg cosim-seg cpi-seg riesgos paralelo paralelo-largo \
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

clean:
	rm -rf $(BUILD) decisiones.csv
