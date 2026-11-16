# Makefile de la pieza G de la factibilidad: edición ASIC del Pochoco Trader.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se corre desde la raíz del repositorio:
#   make -C factibilidad/g_asic OBJETIVO
# Todos los scripts corren desde la raíz, por eso cada regla empieza con cd.
# Las salidas quedan en factibilidad/g_asic/mediciones/. Las corridas de
# LibreLane quedan en factibilidad/g_asic/runs/ y no se versionan.
#
# Necesita Docker con la imagen ghcr.io/librelane/librelane:3.0.16, LibreLane
# en el PATH, el PDK GF180MCU instalado con ciel (PDK_ROOT) y OSS CAD Suite en
# el PATH (iverilog y verilator).
#
# Ojo: no editar un script de scripts/ mientras una corrida lo está usando.
# bash lee el archivo a medida que avanza y seguiría en otra línea.

RAIZ := ../..
G    := factibilidad/g_asic
M    := $(G)/mediciones
S    := $(G)/scripts
SHELL := /bin/bash

# Barrido de período de cada variante. El punto decimal se escribe con p en
# el nombre de la corrida (23.5 queda como base_t23p5).
BASE_T := 40 30 25 23.5 22
SEG_T  := 40 30 25 23.5 22
TAGS_BASE := $(foreach t,$(BASE_T),base_t$(subst .,p,$(t)))
TAGS_SEG  := $(foreach t,$(SEG_T),seg_t$(subst .,p,$(t)))
TAGS ?= $(TAGS_BASE) $(TAGS_SEG)
PAR ?= 2

.PHONY: ayuda equiv equiv-largo sintesis memoria shifter shifter-flujo shifter-recolectar shifter-puertos flujo barrido recolectar cierre ruta flipflops puertos potencia potencia-x drc-klayout comparar todo

ayuda:
	@echo "equiv        RTL del macro contra el testbench oficial y ref/trader.py (2000 ticks, Icarus)"
	@echo "equiv-largo  lo mismo con los 20 000 ticks (Verilator)"
	@echo "sintesis     síntesis jerárquica de las dos variantes: área por módulo"
	@echo "memoria      RAM de datos en flip-flops contra las macros SRAM del PDK"
	@echo "shifter      costo del shifter completo de la ALU, que en la FPGA no cabe"
	@echo "shifter-flujo flujo completo a 40 ns con el shifter completo, las dos variantes"
	@echo "shifter-recolectar tablas de ese flujo, sin volver a correrlo"
	@echo "shifter-puertos netlists de ese flujo contra ref/trader.py"
	@echo "flujo        flujo completo a 40 ns (25 MHz), Espino base y segmentado"
	@echo "barrido      barrido de período de las dos variantes (PAR corridas a la vez)"
	@echo "recolectar   tablas de todas las corridas del barrido que existan"
	@echo "cierre       criterios de cierre de cada corrida con el verificador del Proyecto 3"
	@echo "ruta         de qué registro a qué registro va la ruta crítica de cada corrida"
	@echo "flipflops    qué registros del RTL quedan en el netlist de las corridas de 40 ns"
	@echo "puertos      RTL, netlist de síntesis y netlist final contra ref/trader.py"
	@echo "potencia     potencia con actividad real de las corridas de 40 ns"
	@echo "potencia-x   sensibilidad de esa potencia al estado inicial de los flip-flops sin reset"
	@echo "drc-klayout  segundo DRC con el deck de KLayout del Proyecto 3"
	@echo "comparar     tabla comparativa con la FPGA y con el Proyecto 3"

# El RTL de la edición ASIC decide igual que la referencia y entrega 4/4 con
# el testbench oficial (copia que solo cambia PERIODO_NS, NTICKS y la salida).
equiv:
	cd $(RAIZ) && { $(S)/equiv_rtl.sh base 100000 2000 && $(S)/equiv_rtl.sh seg 100000 2000 \
	  && $(S)/equiv_rtl.sh base 1000000 200 && $(S)/equiv_rtl.sh seg 1000000 200; } | tee $(M)/equiv_rtl.txt

equiv-largo:
	cd $(RAIZ) && { $(S)/equiv_rtl.sh base 100000 20000 verilator && $(S)/equiv_rtl.sh seg 100000 20000 verilator \
	  && $(S)/equiv_rtl.sh base 1000000 20000 verilator && $(S)/equiv_rtl.sh seg 1000000 20000 verilator; } | tee $(M)/equiv_rtl_largo.txt

# Síntesis con la jerarquía conservada, solo hasta Yosys: área por módulo.
sintesis:
	cd $(RAIZ) && $(S)/correr.sh base_jer base 40 -c SYNTH_HIERARCHY_MODE=keep --to Yosys.Synthesis
	cd $(RAIZ) && $(S)/correr.sh seg_jer seg 40 -c SYNTH_HIERARCHY_MODE=keep --to Yosys.Synthesis
	cd $(RAIZ) && python3 $(S)/sintesis.py base_jer seg_jer --md $(M)/sintesis.md

# RAM de datos de 4 a 512 palabras en flip-flops (solo síntesis) y macros SRAM
memoria:
	cd $(RAIZ) && $(S)/memoria.sh 4 16 64 128 256 512 | tee $(G)/build/logs/memoria.txt

# Shifter completo de la ALU (solo síntesis). Necesita make sintesis.
shifter:
	cd $(RAIZ) && $(S)/shifter.sh

# Flujo completo a 40 ns con el shifter completo de la ALU. Necesita make
# shifter (genera config_shifter.yaml) y las corridas base_t40 y seg_t40.
shifter-flujo:
	cd $(RAIZ) && printf '%s\n' base seg | xargs -P $(PAR) -I{} env CONFIG=$(G)/config_shifter.yaml $(S)/correr.sh {}_shifter_t40 {} 40
	$(MAKE) shifter-recolectar

# Tablas del flujo con el shifter, sin volver a correrlo
shifter-recolectar:
	cd $(RAIZ) && python3 $(S)/recolectar.py base_t40 base_shifter_t40 seg_t40 seg_shifter_t40 --md $(M)/shifter_flujo.md --titulo "Flujo completo a 40 ns sin y con el shifter completo"
	cd $(RAIZ) && $(S)/cierre.sh base_shifter_t40 seg_shifter_t40 | tee $(M)/shifter_cierre.txt
	cd $(RAIZ) && python3 $(S)/shifter_delta.py --md $(M)/shifter_delta.md

# Netlists de las corridas con el shifter contra ref/trader.py (las dos
# variantes a la vez). trade.s no usa los desplazamientos variables: esto
# comprueba que agregar el shifter no cambió lo que el macro decide, no que el
# shifter desplace bien.
shifter-puertos:
	cd $(RAIZ) && printf '%s\n' base seg | xargs -P 2 -I{} sh -c '$(S)/sim_puertos.sh sint {}_shifter_t40 && $(S)/sim_puertos.sh pnr {}_shifter_t40 2000' | sort | tee $(M)/shifter_puertos.txt

# Flujo completo (síntesis, place and route, STA en 9 esquinas, DRC, LVS)
flujo:
	cd $(RAIZ) && PAR=$(PAR) $(S)/barrido.sh base:40 seg:40

barrido:
	cd $(RAIZ) && PAR=$(PAR) $(S)/barrido.sh $(foreach t,$(BASE_T),base:$(t)) $(foreach t,$(SEG_T),seg:$(t))

# Tablas de las corridas. Con TAGS="..." se eligen otras.
recolectar:
	cd $(RAIZ) && python3 $(S)/recolectar.py $(TAGS) --md $(M)/corridas.md --titulo "Corridas de LibreLane del macro ASIC"

# Criterios de cierre con el verificador del Proyecto 3 (segunda lectura)
cierre:
	cd $(RAIZ) && $(S)/cierre.sh $(TAGS) | tee $(M)/cierre.txt

# Extremos de la ruta crítica de cada corrida, con los nombres del RTL.
# Necesita make recolectar.
ruta:
	cd $(RAIZ) && python3 $(S)/extremos.py $(TAGS) --md $(M)/ruta_critica.md

# Qué registros quedaron como flip-flops después de la síntesis aplanada
flipflops:
	cd $(RAIZ) && python3 $(S)/flipflops.py base_t40 seg_t40 base_jer seg_jer --md $(M)/flipflops.md

# Simulación por los puertos: RTL, netlist de síntesis y netlist final
puertos:
	cd $(RAIZ) && { $(S)/sim_puertos.sh rtl base 2000 && $(S)/sim_puertos.sh rtl seg 2000 \
	  && $(S)/sim_puertos.sh sint base_t40 && $(S)/sim_puertos.sh sint seg_t40 \
	  && $(S)/sim_puertos.sh pnr base_t40 2000 && $(S)/sim_puertos.sh pnr seg_t40 2000; } | tee $(M)/puertos.txt

potencia:
	cd $(RAIZ) && $(S)/potencia.sh base_t40 && $(S)/potencia.sh seg_t40

potencia-x:
	cd $(RAIZ) && $(S)/potencia.sh base_t40 xinit && $(S)/potencia.sh seg_t40 xinit

drc-klayout:
	cd $(RAIZ) && { $(S)/drc_klayout.sh base_t40 && $(S)/drc_klayout.sh seg_t40; } | tee $(M)/drc_klayout.txt

comparar:
	cd $(RAIZ) && python3 $(S)/comparar.py --md $(M)/comparacion.md

todo: equiv equiv-largo sintesis memoria shifter barrido shifter-flujo shifter-puertos recolectar cierre ruta flipflops puertos potencia potencia-x drc-klayout comparar
