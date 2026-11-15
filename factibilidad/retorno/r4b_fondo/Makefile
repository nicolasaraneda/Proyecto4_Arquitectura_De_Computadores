# Makefile del estudio de retorno 4, parte B: el fondo de estrategias y el reparto de capital.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Todo se corre desde esta carpeta. Las salidas quedan en mediciones/ y los
# productos intermedios en build/, que no se versiona. Solo usa la semilla 0.
#
#   make arnes          compila build/arnes (el arnés con la estrategia fondo) y build/cota
#   make prueba         causalidad, identidades y espejo de la cuenta        mediciones/prueba.txt
#   make cota           oráculo, mezclas fijas, correlaciones y persistencia  mediciones/cota_*.txt
#   make exploracion    todas las variantes a 2000 ticks                      mediciones/exploracion_n2000_*, finales_n2000_*
#   make largo          la lista corta a 20 000 ticks, tres vistas            mediciones/largo_n20000_*
#   make veredictos     criterio de corte oficial de las candidatas           mediciones/veredicto_*.txt
#   make bytes          flujo de bytes de DECISION del fondo recomendado      mediciones/bytes_*.txt
#   make tablas         tablas en Markdown a partir de lo anterior            mediciones/tablas.md
#   make todo           todo lo anterior, en orden

include ../nucleo/nucleo.mk

BIN := build/arnes
COTA := build/cota
HILOS ?= 5
export HILOS
SEMILLA := 0
SERIE ?= ../../../tb/practica.csv
NUCLEO_SIN_MAIN := $(filter-out %/main.c,$(NUCLEO_FUENTES))

.PHONY: arnes prueba cota exploracion largo veredictos bytes tablas todo
arnes: $(BIN) $(COTA)

$(BIN): $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) fondo.c
	@mkdir -p build
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) fondo.c $(NUCLEO_LIBS)

$(COTA): $(NUCLEO_SIN_MAIN) $(NUCLEO_CABECERAS) cota.c
	@mkdir -p build
	$(NUCLEO_CC) -o $@ $(NUCLEO_SIN_MAIN) cota.c $(NUCLEO_LIBS)

prueba: $(BIN)
	@mkdir -p mediciones
	sh pruebas.sh $(BIN) $(SERIE) > mediciones/prueba.txt 2>&1; tail -3 mediciones/prueba.txt

cota: $(COTA)
	@mkdir -p mediciones
	$(COTA) --largo 2000 --semilla $(SEMILLA) --conjunto evidencia > mediciones/cota_n2000_evidencia.txt
	$(COTA) --largo 2000 --semilla $(SEMILLA) --conjunto estres > mediciones/cota_n2000_estres.txt
	$(COTA) --largo 20000 --semilla $(SEMILLA) --conjunto evidencia --interior > mediciones/cota_n20000_evidencia_interiores.txt

exploracion: $(BIN)
	python3 explorar.py --fase exploracion --forzar
	python3 explorar.py --fase finales --forzar

largo: $(BIN)
	python3 explorar.py --fase largo --forzar

veredictos: $(BIN)
	python3 explorar.py --fase veredictos

tablas:
	python3 explorar.py --fase tablas

bytes: $(BIN)
	sh bytes.sh $(BIN) fondo_rec $(SERIE) mediciones/bytes_fondo_rec_practica.txt
	sh bytes.sh $(BIN) fondo_min $(SERIE) mediciones/bytes_fondo_min_practica.txt

todo: arnes prueba cota exploracion largo veredictos bytes tablas
