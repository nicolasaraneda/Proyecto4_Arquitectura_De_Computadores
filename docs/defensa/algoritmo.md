# El algoritmo: de la serie al modelo y de ahí a `max_media`

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio para la defensa. Resume y ordena `docs/algoritmo.md` (el camino completo con todos los descartes) y `docs/protocolo.md` (cómo se mide). Cifras de `docs/mediciones/` (`tabla_3_1.txt`, `protocolo_*.txt`, `exploracion.txt`, `generador_*.txt`, `politica_optima.txt`, `frontera.txt`, `experimentos.txt`) y de las decisiones T20, T27, T50 y T51.

## 1. Qué problema resuelve

En cada tick la maestra manda un precio entre 1 y 255 y el programa responde comprar, vender o mantener, con una cantidad de 0 a 63. La orden que se decide con el precio n-1 se ejecuta al precio n. Cada orden ejecutada paga 5 de comisión. El patrimonio sale de dos cosas: **predecir hacia dónde va el precio** y **no pagar comisiones de más**. Todos los grupos ejecutan al mismo precio.

## 2. Lo que se ve en la serie: reversión a la media

| Medida sobre la serie de práctica | Valor | Qué significa | Fuente |
|-----------------------------------|-------|---------------|--------|
| Razón de varianza a 10, 50 y 100 ticks | 0,77, 0,62 y 0,53 | Menor que 1: los cambios largos son más chicos de lo que serían si fuera un paseo aleatorio. El precio vuelve | `docs/estado.md`, tramo 1 (`make hallazgos`) |
| Bloques de 1000 ticks con VR < 1 | 20 de 20, en los tres horizontes | No es un tramo: pasa en toda la serie | idem |
| Autocorrelación de los cambios | -0,112 en el rezago 1, ruido desde el rezago 3 | Una subida tiende a seguirse de una bajada | idem |
| Seguir tendencia, 336 configuraciones | Mediana 5 566; solo 10 de 336 terminan sobre 10 000 | La tendencia pierde | idem |
| Comprar y mantener, serie completa | 6 497 | La serie termina más abajo de donde empezó | `docs/mediciones/tabla_3_1.txt` |

**Por qué reversión y no tendencia:** la razón de varianza es menor que 1 en todos los horizontes y en todos los bloques, la autocorrelación es negativa, y seguir tendencia pierde en la práctica. Además, en las familias sintéticas, sin reversión la regla no gana y con tendencia pierde: el riesgo está medido (sección 6).

## 3. El modelo del generador

Se ajustó por máxima verosimilitud (filtro de Kalman para la verosimilitud, Nelder-Mead para maximizar, `ref/generador.py:187`):

```
precio(t)      = redondeo( nivel(t) + transitoria(t) )
nivel(t)       = nivel(t-1) + ruido                  paseo aleatorio, lento
transitoria(t) = 0,961 * transitoria(t-1) + ruido    AR(1), vida media 17,5 ticks
```

Con dos regímenes de volatilidad (86 % tranquilo, 14 % ruidoso, razón 8,9) y saltos de nivel de 8 a 14 unidades cada 4000 ticks (`docs/algoritmo.md`, sección 2.2). El modelo reproduce la varianza, la razón de varianza, la curtosis y la persistencia de la volatilidad (`docs/mediciones/generador_validacion.txt`).

Tres conclusiones que hay que saber decir:

1. **La mitad de la reversión es redondeo.** Un paseo aleatorio redondeado a enteros tiene VR(100) = 0,77. Descontando el redondeo, la práctica queda en 0,67. Esa parte no se puede explotar: el error de redondeo del precio que vio el programa ya se deshizo cuando la orden se ejecuta (`docs/mediciones/generador_redondeo.txt`).
2. **La señal es débil.** El modelo con reversión supera al paseo aleatorio en 10 unidades de log-verosimilitud en 20 000 ticks: una por ronda. Dentro de una ronda no se puede saber si la serie revierte.
3. **El techo está cerca.** La política óptima del modelo, calculada por programación dinámica con comisión, desfase de un tick y 63 acciones por orden, gana 8,4 % por ronda. La regla base gana 5,2 % en el modelo. No hay una mejora grande escondida (`docs/mediciones/politica_optima.txt`).

## 4. La regla: `max_media`

```
S   = 32 × media exponencial del precio, alfa = 1/32
dev = 32 p - S
pos = (pos | dev < -96) & (dev < 1)     entra 3 unidades bajo la media, sale al recuperarla
DECISION = "comprar 63" si pos = 1, "vender 63" si pos = 0
S   = S + (dev >>> 5)
```

| Dónde | Qué |
|-------|-----|
| `ref/trader.py:74` | `decidir`, la referencia oficial con las mismas operaciones que el assembly |
| `ref/trader.py:90` y `:98` | `MaxMedia` y `Oficial = MaxMedia` |
| `sw/trade.s:64` | `UMBRAL_COMPRA = -96`: la única línea que cambia respecto de la regla base (-128) |
| `sw/trade.s:109` a `:115` | La decisión sin saltos |

**Cómo decide la cantidad.** No la decide: siempre 63, el máximo. La maestra recorta la compra a lo que alcanza con la caja y la venta a las acciones que se tienen, y una orden que queda en cero no paga comisión (`tb/tb_proyecto_4.sv:73` y `:78`). Entonces "comprar 63" repetido no cuesta nada una vez gastada la caja. El programa expresa una **posición objetivo** (todo adentro o todo afuera) y no lleva contabilidad, que así no se puede desincronizar de la oficial.

**Por qué los parámetros son esos.**

- **Alfa 1/32.** Con alfa más grande la media sigue al precio y no queda desviación que operar; con más chico mejora el modelo y empeora el remuestreo (`docs/algoritmo.md`, sección 5.2). Además 1/32 son cables en la extensión (k = 5).
- **Entrar a 3 unidades (E = 96).** Bandas más angostas suben la media en el modelo y bajan el percentil 5 en todas partes. El remuestreo tiene su máximo en E entre 96 y 128; el modelo en E = 48. Donde coinciden las dos evidencias es E = 96 (`docs/algoritmo.md`, sección 5.1).
- **Salir al recuperar la media (X = 0).** Es la forma que da la política óptima: entrar bajo un umbral, salir sobre otro, no hacer nada entre los dos. La comisión es la que abre la banda.

## 5. El protocolo de evaluación: cómo se evita engañarse

El 27 062 de la regla base en la serie completa **no** es lo esperado: los parámetros se eligieron mirando esa serie, es una sola trayectoria con interés compuesto, y las series de la competencia son otras (`docs/protocolo.md`, sección 1). El protocolo se fijó **antes** de probar ideas (decisión T20):

| Evidencia | Qué es | Fuente en el código |
|-----------|--------|---------------------|
| 10 bloques de práctica | Tramos de 2000 ticks, cada uno con caja 10 000 | `ref/series.py:56` |
| 1000 remuestreos | Cambios de precio cortados en bloques de 100 ticks, elegidos al azar con reposición. Conserva la dependencia de 10 a 50 ticks, donde está la ganancia | `ref/series.py:75` |
| 14 familias sintéticas calibradas | 4 plausibles (el modelo, el modelo con parámetros vecinos, dos componentes, cambio de volatilidad) y 10 de estrés (paseo, tendencia, saltos, cambio de carácter a mitad de la serie, volátil, nivel bajo, plana, bordes 1 y 255, reversión) | `ref/series.py:267` y `:270` |
| Semilla reservada | Con la semilla 0 se exploró y se eligió todo; la semilla 1 solo evalúa a los finalistas | decisión T27 |

**Criterio de aceptación** (`ref/protocolo.py:36` a `:40`): una candidata reemplaza a la base solo si (a) en los 10 bloques sube la media y el peor bloque, (b) en los remuestreos sube la media y el percentil 5, y (c) en ninguna familia la media baja más de 1 %. Además se informa la diferencia pareada con su error estándar.

## 6. Resultados: `max_media` contra la regla base

Semilla reservada (`docs/algoritmo.md`, sección 7.2, y `docs/mediciones/frontera.txt`):

| | Bloques: media, peor | Remuestreo: media, dif., p5 | Plausibles: media, dif., p5 | Estrés: p5, peor |
|-|----------------------|-----------------------------|------------------------------|------------------|
| Regla base | 11 069, 9 720 | 10 754, 8 958 | 10 954, 8 741 | 5 615, 156 |
| `max_media` | 11 043, 9 620 | 10 833, +79 ± 11, 8 788 | 11 103, +150 ± 15, 8 622 | 5 071, 180 |

- **Gana 0,7 % en el remuestreo y 1,4 % en las plausibles**, con diferencias de 7 y 10 errores estándar. Es el único candidato que sube la media en las dos evidencias independientes, y no agrega una instrucción.
- **No cumple formalmente el criterio**: en los 10 bloques queda 26 abajo, con un error de 238 (ruido), y baja más de 1 % en familias de estrés. Se eligió por el perfil de riesgo del grupo (maximizar el patrimonio esperado) y por los puntos esperados del torneo: +0,04 sobre la regla base a 2 000 ticks (decisión T51).
- **En la serie completa de práctica rinde menos**: 25 973 contra 27 062 (`docs/mediciones/tabla_3_1.txt`). Es la pregunta obligada sobre la tabla del punto 3.1. Respuesta: el 27 062 está sesgado por haber elegido los parámetros mirando esa serie, y la diferencia en los bloques está dentro del error.

Tabla del punto 3.1, serie completa viendo todos los precios (`docs/mediciones/tabla_3_1.txt`):

| Estrategia | Patrimonio | Órdenes | Comisiones | Pérdida máxima |
|------------|------------|---------|------------|----------------|
| No operar | 10 000 | 0 | 0 | 0 |
| Comprar y mantener | 6 497 | 1 | 5 | |
| Regla base | 27 062 | 388 | 1 940 | 2 929 |
| `max_media` | 25 973 | 624 | 3 120 | 6 295 |

## 7. Por qué no otras ideas

Cada idea se midió cambiando una sola pieza (`make exploracion`, `docs/mediciones/exploracion.txt`). Ninguna sube la media en las dos evidencias:

| Idea | Resultado | Por qué |
|------|-----------|---------|
| Filtro de Kalman de dos estados (el estimador óptimo del modelo) | Empata, cuesta unas 140 instrucciones contra 27 | Después de filtrar, la incertidumbre de la transitoria baja de 1,19 a 1,11: no hay señal que sacar |
| Suma móvil de 32 o 64 | No mejora a la media exponencial y ocupa 32 o 64 palabras | |
| Política óptima del modelo | +4 puntos en el modelo, -7 en el remuestreo | Es óptima para el modelo gaussiano, no para la serie: en la práctica las caídas chicas no rebotan lo suficiente |
| Bandas escaladas con la volatilidad | 11 028 contra 11 029 de la banda fija | La banda fija de 3 a 4 unidades ya es ancha para el régimen tranquilo y justa para el ruidoso |
| Tope de tiempo y de precio | Suben el peor caso en tendencia y cuestan media | En una serie que revierte, vender después de una caída es vender en el peor momento |
| Entrada escalonada, órdenes más chicas | Bajan media y suben percentil 5 | Es moverse por la misma frontera, con peor relación que las bandas |
| Población de traders, adaptación en vivo, perceptrón | -57, -16 y -199 en el remuestreo | Hay una unidad de log-verosimilitud de evidencia por ronda: adaptarse en vivo es ajustar con casi nada de información |
| Guardia de régimen | Cuesta 1 % en el remuestreo y 2 % en las plausibles; protege en tendencia | Quedó fuera de la competencia (T50) con sus números |

La guardia como test estadístico no se puede hacer: con 2000 ticks la razón de varianza de una serie que revierte y la de un paseo aleatorio se traslapan casi enteras (`docs/algoritmo.md`, sección 6.1).

## 8. Cuánto es suerte, y qué pasa si la serie oculta es distinta

- **En una ronda la suerte pesa más que la regla.** En los remuestreos el patrimonio final va de 6 520 a 15 637 con la misma regla (`docs/protocolo.md`, sección 8). Con la misma regla, una de cada veinte rondas termina con más de 10 % de pérdida (`docs/algoritmo.md`, sección 9). `max_media` supera a comprar y mantener en el 71 % de los remuestreos y el 64 % de las plausibles (sección 7.2): cerca de una ronda de cada tres termina bajo esa referencia.
- **La serie oculta puede ser distinta**, y está medido: sin reversión (`paseo`) no se gana; con tendencia a la baja se pierde (percentil 5 de 4 631 en `tendencia`); con más volatilidad o precio más bajo se gana más.
- **Sobreajuste.** Tres defensas: la semilla reservada (los números de las dos semillas coinciden dentro de 1 %), la meseta (E entre 80 y 128 da medias dentro de 60 puntos) y el modelo, que no usa los cambios de la práctica uno por uno y coincide en el signo de la mejora.
- **Si cambian la comisión o la caja.** El programa no las conoce: no llegan por SPI. `tools/retune.py` busca umbrales nuevos con el mismo protocolo (cambia solo si la media sube más de 0,2 % sin bajar el percentil 5 ni el peor bloque, `tools/retune.py:195`). Con las reglas publicadas devuelve los umbrales actuales; cambia solo con comisión de 20 o más (decisión T122, `docs/arbol_decision.md`, sección 2).

## 9. Preguntas típicas

1. **¿Por qué reversión y no tendencia?** VR menor que 1 en todos los horizontes y en los 20 bloques de 1000 ticks, autocorrelación de -0,11, y seguir tendencia termina con mediana 5 566 en 336 configuraciones (`docs/estado.md:767` a `:773`).
2. **¿Cuánta reversión hay de verdad?** Menos de la que parece: la mitad de la caída de VR es redondeo. La otra mitad es una transitoria de 1,2 unidades de desviación estándar con vida media de 17,5 ticks.
3. **¿Cómo decide la cantidad?** Siempre 63: la maestra recorta, y una orden en cero no paga. El programa expresa una posición objetivo (`sw/trade.s:113` a `:115`).
4. **¿Por qué la tabla del 3.1 muestra menos con `max_media` que con la regla base?** Porque 27 062 está sesgado por haber elegido los parámetros mirando esa serie. Fuera de muestra `max_media` gana 0,7 % y 1,4 % (T51).
5. **¿Cómo saben que no es sobreajuste?** Semilla reservada, meseta de parámetros y el modelo independiente de la trayectoria (`docs/algoritmo.md`, sección 9).
6. **¿Cuánto del resultado es suerte?** La mayor parte en una ronda: de 6 520 a 15 637 con la misma regla en los remuestreos. En tres rondas pesa menos, pero pesa.
7. **¿Por qué no usar el filtro de Kalman si es el óptimo?** El problema está mal condicionado: la incertidumbre baja de 1,19 a 1,11. Empata y cuesta cinco veces más instrucciones.
8. **¿Qué pasa si la serie oculta no revierte?** No se gana (paseo) o se pierde (tendencia). La guardia protegía en tendencia y costaba 1 a 2 % de media; quedó fuera por la decisión T50.
9. **¿Qué pasa si cambian la comisión?** `retune` busca umbrales con el mismo protocolo; para comisión de 20 y 50 los bitstreams están construidos y simulados (`docs/contingencia.md`, sección 4).
10. **¿Por qué no aprender en vivo?** Hay una unidad de log-verosimilitud de evidencia por ronda. Los tres intentos (población, adaptación con prior fuerte, perceptrón) pierden en el remuestreo (`docs/mediciones/experimentos.txt`).
