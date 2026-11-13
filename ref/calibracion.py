#!/usr/bin/env python3
"""calibracion.py: parámetros del modelo del generador, ajustados a la serie de práctica.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Estos números los produce `python3 ref/generador.py --ajustar` (o `make
generador`), que además comprueba que el ajuste los sigue reproduciendo. Se
guardan aquí como constantes para que las series de prueba no dependan de
volver a correr el ajuste, que demora cerca de un minuto.

Son datos de prueba: sirven para fabricar series parecidas a la de práctica.
Nada de esto queda dentro del diseño ni del programa de la placa.

Modelo (docs/algoritmo.md, sección 2):

    precio = redondeo(nivel + transitoria)
    nivel       paseo aleatorio, varianza del paso Q_NIVEL (régimen tranquilo)
    transitoria AR(1) con coeficiente PHI y varianza de la innovación Q_TRANS
    régimen     tranquilo o ruidoso; en el ruidoso las dos varianzas se
                multiplican por RAZON_RUIDOSO
    saltos      el nivel salta de golpe con probabilidad P_SALTO por tick
"""

# Componentes, en el régimen tranquilo (varianzas por tick, en unidades de precio al cuadrado)
Q_NIVEL = 0.156          # desviación estándar del paso del nivel: 0,39
Q_TRANS = 0.107          # desviación estándar de la innovación transitoria: 0,33
PHI = 0.9612             # la transitoria pierde la mitad en 17,5 ticks
RAZON_RUIDOSO = 8.907    # varianzas del régimen ruidoso / tranquilo (2,98 veces en desviación estándar)

# Regímenes de volatilidad
DUR_TRANQUILO = 4300     # duración media de un tramo tranquilo, en ticks
DUR_RUIDOSO = 700        # duración media de un tramo ruidoso
UMBRAL_REGIMEN = 0.95    # un tick es ruidoso si la desviación estándar de los cambios en +-50 ticks pasa de esto

# Saltos de nivel
SALTO_MIN_ABS = 8        # un cambio de 8 o más en un tick se cuenta como salto
P_SALTO = 5 / 20000      # 5 saltos en la serie de práctica
SALTO_TAM = (8, 14)      # tamaños observados: 8, 9, 12, 13 y 14

# Nivel inicial de las series simuladas (la de práctica va de 72 a 190)
NIVEL_INICIAL = (80, 180)

# Varianza del error de redondeo a enteros (uniforme en +-0,5)
R_REDONDEO = 1.0 / 12.0
