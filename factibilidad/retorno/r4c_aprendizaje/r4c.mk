# r4c.mk: fuentes de las estrategias del estudio de aprendizaje en vivo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Para usar estas estrategias desde otra carpeta (por ejemplo el estudio del
# fondo, como cuarto gestor en papel) basta con incluir este archivo después
# de nucleo.mk y agregar $(R4C_FUENTES) a la línea de compilación:
#
#   include ../nucleo/nucleo.mk
#   include ../r4c_aprendizaje/r4c.mk
#   build/arnes: $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) $(R4C_FUENTES) $(R4C_CABECERAS) lo_mio.c
#   	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) $(R4C_FUENTES) lo_mio.c $(NUCLEO_LIBS)
#
# Estrategias que quedan registradas: `tabla`, `patron` y `mm_patron`, y los
# alias estables de aprendiz.c: `aprendiz` (la tabla que aprende),
# `aprendiz_rapido`, `espera` (regla fija), `aprendiz_patron` y
# `aprendiz_puro`. Se crean con instancia_crear("cand:aprendiz", ...).

R4C_DIR := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
R4C_FUENTES := $(addprefix $(R4C_DIR)/,e_tabla.c e_patron.c aprendiz.c)
R4C_CABECERAS := $(addprefix $(R4C_DIR)/,pred.h)
