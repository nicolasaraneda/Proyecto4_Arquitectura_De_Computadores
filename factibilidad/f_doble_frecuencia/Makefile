# Makefile de la pieza F: doble frecuencia sin PLL (experimento de factibilidad).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Cada objetivo regenera un archivo de mediciones/. Se puede correr desde
# cualquier carpeta: make -C factibilidad/f_doble_frecuencia todo
# Los productos intermedios quedan en build/, que git ignora.
#
#   make sintesis       qué flujos de Yosys conservan la cadena      mediciones/sintesis_cadena.txt
#   make cadena         retardo de la cadena: largo, semilla, lugar  mediciones/cadena.txt
#   make tb             testbench del duplicador, con retardos       mediciones/tb_duplicador.txt
#   make restricciones  --freq, ctx.addClock y SDC en nextpnr        mediciones/restricciones.txt
#   make soc            SoC base y segmentado con el reloj doblado   mediciones/soc_x2.txt
#   make validar        el análisis propio contra nextpnr e icetime  mediciones/validacion_sta.txt
#   make opciones       opciones de nextpnr que cambian el ruteo     mediciones/opciones_nextpnr.txt
#   make humo           testbench oficial sobre el SoC doblado       mediciones/humo_soc_x2.txt
#                       y efecto de la fase de la maestra            mediciones/humo_fase.txt
#   make margen         margen real, dos flancos y presupuesto       mediciones/margen.txt
#   make placa          prueba para la Go Board: bitstream y tb      mediciones/placa_x2.txt
#   make todo           todo lo anterior, en orden
#   make hoja PDF=...   datos citados de la hoja de datos DS1040     mediciones/hoja_datos.txt
#                       (no está en el repositorio: se baja y se pasa su ruta)
#   make limpiar        borra build/
#
# SEMILLAS (por defecto 10) y JOBS (por defecto 5) se pueden cambiar:
#   make soc SEMILLAS=3 JOBS=2

SEMILLAS ?= 10
JOBS     ?= 5
export JOBS

.PHONY: todo sintesis cadena tb restricciones soc validar opciones humo margen placa hoja limpiar

todo: sintesis cadena tb restricciones soc validar opciones humo margen placa

sintesis:
	scripts/medir_sintesis.sh

cadena:
	scripts/medir_cadena.sh $(SEMILLAS)

tb:
	scripts/tb_duplicador.sh

restricciones:
	scripts/medir_restricciones.sh

soc:
	scripts/medir_soc.sh $(SEMILLAS)

validar:
	scripts/validar_sta.sh

opciones:
	scripts/medir_opciones.sh $(SEMILLAS)

humo:
	scripts/humo_soc.sh
	scripts/humo_fase.sh

margen:
	python3 scripts/margen.py build/soc mediciones/humo_soc_x2.txt | tee mediciones/margen.txt

placa:
	scripts/placa.sh $(SEMILLAS)

hoja:
	@test -n "$(PDF)" || { echo "Uso: make hoja PDF=ruta/a/la/hoja_de_datos.pdf"; exit 1; }
	python3 scripts/hoja_datos.py "$(PDF)" | tee mediciones/hoja_datos.txt

limpiar:
	rm -rf build
