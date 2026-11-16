# Makefile del estudio de factibilidad E: respaldo por reconfiguración con
# SB_WARMBOOT e icemulti.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se usa desde la raíz del repositorio:
#   make -C factibilidad/e_warmboot todo
# o un objetivo por vez (make -C factibilidad/e_warmboot demo, ...).
# Las herramientas de OSS CAD Suite tienen que estar en el PATH:
#   export PATH=$OSS_CAD_SUITE/bin:$PATH
#
# Todos los scripts corren desde la raíz, escriben sus productos intermedios
# en factibilidad/e_warmboot/build/ y dejan el resultado en mediciones/.
# Las excepciones son vigilante-costo y vigilante-boton, que usan
# tools/medir_variante.sh y por eso escriben en build/variantes/fact_e_* de
# la raíz.

RAIZ := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
S    := factibilidad/e_warmboot/scripts

.PHONY: todo rapido demo sim-demo sim-demo-rtl variantes tamanos plataforma miso \
        vigilante-tb vigilante-formal vigilante-soc vigilante-costo vigilante-boton relevo relevo-img \
        uart-autoprueba limpiar

# Todo lo que respalda un número del README. Demora cerca de media hora.
todo: demo sim-demo variantes tamanos plataforma miso vigilante-tb vigilante-formal \
      vigilante-soc vigilante-costo vigilante-boton relevo relevo-img uart-autoprueba

# Lo que corre en menos de dos minutos.
rapido: demo sim-demo-rtl variantes tamanos plataforma miso vigilante-formal uart-autoprueba

# Prueba de placa: dos imágenes con SB_WARMBOOT y wb_demo_multi.bin
demo:
	cd $(RAIZ) && $(S)/construir_demo.sh

# Simulación de las dos imágenes: RTL y desde el .asc (la segunda demora unos 8 minutos)
sim-demo: demo
	cd $(RAIZ) && $(S)/sim_demo.sh todo

sim-demo-rtl:
	cd $(RAIZ) && $(S)/sim_demo.sh rtl

# Variantes de la prueba de placa: sin dormir la flash y con el oscilador más rápido
variantes: demo
	cd $(RAIZ) && $(S)/variantes_demo.sh

# Cuántas imágenes caben y el archivo realista (segmentado_v1 + competencia_v1)
tamanos: demo
	cd $(RAIZ) && $(S)/tamanos.sh

# Hechos comprobables sin la placa
plataforma: demo
	cd $(RAIZ) && $(S)/plataforma.sh

# Qué byte lee la maestra si el pin cambia a mitad de una transacción
miso:
	cd $(RAIZ) && python3 $(S)/corte_miso.py > factibilidad/e_warmboot/mediciones/miso_corte.txt
	@tail -12 $(RAIZ)/factibilidad/e_warmboot/mediciones/miso_corte.txt

# Vigilante: testbench, prueba formal, testbench oficial sobre el SoC y costo en 10 semillas
vigilante-tb:
	cd $(RAIZ) && $(S)/probar_vigilante.sh

vigilante-formal:
	cd $(RAIZ) && $(S)/formal_vigilante.sh

vigilante-soc:
	cd $(RAIZ) && $(S)/probar_soc.sh

vigilante-costo:
	cd $(RAIZ) && $(S)/medir_vigilante.sh 10

# Variantes del vigilante integradas: N = 1 y disparo manual (10 semillas)
vigilante-boton: vigilante-costo
	cd $(RAIZ) && $(S)/medir_boton.sh 10

# Relevo completo en simulación y archivo de prueba para la placa y la maestra
relevo:
	cd $(RAIZ) && $(S)/relevo.sh

relevo-img: demo
	cd $(RAIZ) && $(S)/construir_relevo.sh

uart-autoprueba:
	cd $(RAIZ) && python3 $(S)/medir_uart.py --autoprueba > factibilidad/e_warmboot/mediciones/medir_uart_autoprueba.txt
	@tail -1 $(RAIZ)/factibilidad/e_warmboot/mediciones/medir_uart_autoprueba.txt

limpiar:
	rm -rf $(RAIZ)/factibilidad/e_warmboot/build
