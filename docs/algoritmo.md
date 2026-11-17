# Algoritmo: del modelo de la serie a los candidatos

Documento de estudio del frente del algoritmo. Cuenta el camino completo: qué modelo se ajustó a la serie de práctica, cuánto se puede ganar como máximo según ese modelo, qué ideas se probaron (con sus números, ganen o pierdan), cómo quedó la guardia de régimen y el tope de pérdida, y qué candidatos quedan sobre la frontera entre media y percentil 5.

**Estado.** Desde el 15/11 `sw/trade.s` y la referencia oficial (`ref/trader.py`) corren `max_media`, la regla base con el umbral de entrada en 3 unidades (decisión T51, sección 7.6). Las secciones 1 a 7.5 cuentan el camino hasta esa elección.

| Archivo | Qué es |
|---------|--------|
| `ref/generador.py`, `ref/calibracion.py` | Ajuste del modelo a la serie de práctica y sus constantes. |
| `ref/series.py` | Familias sintéticas calibradas, en dos grupos: plausibles y de estrés. |
| `ref/politica_optima.py` | Filtro de Kalman en estado estacionario y política óptima por programación dinámica. |
| `ref/candidatos.py` | Familia paramétrica de estrategias (clase `Trader`) y candidatos. |
| `ref/motor/motor.c`, `ref/motor.py` | La misma familia en C, para barrer miles de combinaciones. |
| `ref/explorar.py` | Una tabla por idea. |
| `ref/experimentos.py` | Población de traders, adaptación en vivo y perceptrón. |
| `ref/frontera.py` | Los candidatos, con la semilla de exploración y con la reservada. |
| `ref/test_candidatos.py` | Pruebas: el motor coincide con la referencia, las familias son reproducibles. |
| `docs/mediciones/` | Salida de cada script (`make algoritmo`). |

Todos los patrimonios de este documento son el patrimonio final de una serie de 2000 ticks que parte con 10 000.

## 1. Resumen

1. **La serie de práctica es un nivel que pasea más una componente transitoria pequeña, redondeado a enteros, con dos regímenes de volatilidad y saltos poco frecuentes.** El modelo ajustado reproduce la varianza, la razón de varianza a todos los horizontes, la curtosis y la persistencia de la volatilidad.
2. **Cerca de la mitad de la reversión que se ve es redondeo.** La razón de varianza a 100 ticks es 0,53. Un paseo aleatorio sin ninguna reversión, redondeado a enteros, da 0,77. Descontando el redondeo, la serie de práctica queda en 0,67.
3. **La señal es débil.** El modelo con reversión supera al paseo aleatorio en 10 unidades de log-verosimilitud sobre 20 000 ticks: una unidad por ronda. Dentro de una ronda no se puede saber si la serie revierte.
4. **El techo está cerca.** La política óptima del modelo gana 8,4 % por ronda. La regla base gana 5,2 % en el modelo y 7,5 % en los remuestreos. No hay una mejora grande escondida: lo que queda es del orden de 1 a 3 puntos.
5. **El estimador casi no importa.** Media exponencial, suma móvil y filtro de Kalman de dos estados rinden lo mismo cuando se les ajustan las bandas. El Kalman empata con la media exponencial y cuesta cinco veces más instrucciones.
6. **Lo que sí mueve el resultado es cuánto se opera.** Bandas más angostas suben la media en el modelo y bajan el percentil 5 en todos lados. Ese es el eje de la frontera.
7. **Todo corte de pérdidas cuesta media.** En una serie que revierte, vender después de una caída es vender en el peor momento. La guardia y el tope protegen cuando la serie no revierte y cuestan entre 1 y 3 % de media cuando sí.
8. **Hay cuatro candidatos sobre la frontera** (sección 7). El de mayor media supera a la regla base por 0,7 % en los remuestreos y 1,4 % en las familias plausibles, medido con la semilla reservada.

## 2. El generador

### 2.1 Qué se ve en la serie

`python3 ref/generador.py --ajustar` (`docs/mediciones/generador_ajuste.txt`).

- **Cambios de un tick.** El 56 % de los cambios es cero y el 38 % es más o menos uno. La varianza es 0,75.
- **Dos regímenes de volatilidad.** Se etiqueta cada tick mirando la desviación estándar de los cambios en una ventana de 50 ticks a cada lado. En el régimen tranquilo (86 % del tiempo) la varianza de los cambios es 0,43 y ningún cambio pasa de 2. En el ruidoso (14 %) la varianza es 2,53 y hay cambios de hasta 6. Hay cuatro tramos ruidosos, de 457 a 927 ticks, separados por tramos tranquilos de 2300 a 7300.
- **Saltos.** Cinco cambios de 8 o más en un tick: -9, +12, -14, +8 y -13. Son saltos de nivel: 20 a 60 ticks después se conserva entre el 64 y el 113 % del salto. No son caídas que se devuelven.
- **Tendencias dentro del régimen tranquilo.** Entre los ticks 18 000 y 18 800 el precio baja de 121 a 76 sin que cambie la volatilidad. El modelo lo explica como paseo del nivel, pero es el tipo de tramo que castiga a una regla de reversión.

### 2.2 El modelo

```
precio(t)      = redondeo( nivel(t) + transitoria(t) )
nivel(t)       = nivel(t-1) + ruido de varianza q_nivel            paseo aleatorio
transitoria(t) = phi * transitoria(t-1) + ruido de varianza q_trans    AR(1)
```

En el régimen ruidoso las dos varianzas se multiplican por una misma razón. El nivel además salta con una probabilidad pequeña por tick. El redondeo se trata como un ruido de observación de varianza 1/12, que es la de un error uniforme entre -0,5 y 0,5.

Los parámetros se ajustan por máxima verosimilitud. La verosimilitud se calcula con el filtro de Kalman (recorre los 20 000 ticks) y se maximiza con Nelder-Mead, partiendo de tres puntos distintos que llegan al mismo resultado:

| Parámetro | Valor | Qué significa |
|-----------|-------|---------------|
| `q_nivel` | 0,156 | El nivel se mueve 0,39 por tick en el régimen tranquilo. |
| `q_trans` | 0,107 | La innovación de la transitoria es 0,33 por tick. |
| `phi` | 0,961 | La transitoria pierde la mitad en 17,5 ticks. |
| Razón entre regímenes | 8,9 | En el régimen ruidoso todo se mueve 2,98 veces más. |
| Desviación estándar de la transitoria | 1,19 y 3,54 | Tranquilo y ruidoso. |
| Duración media de los tramos | 4300 y 700 ticks | Tranquilo y ruidoso. |
| Saltos | 1 cada 4000 ticks, de 8 a 14 unidades | |

Dos comprobaciones sobre la forma del modelo:

- **Sin transitoria** (solo paseo más redondeo) la verosimilitud empeora en 10,2 unidades. La reversión existe, pero la evidencia es poca.
- **Con parámetros separados para cada régimen** (6 en vez de 4) mejora solo 0,1. Los dos regímenes tienen la misma estructura a distinta escala.

### 2.3 El redondeo fabrica la mitad de la reversión

`python3 ref/generador.py --redondeo` (`docs/mediciones/generador_redondeo.txt`). El redondeo suma siempre lo mismo a la varianza de un cambio, sea de 1 tick o de 100. Eso baja la razón de varianza aunque el proceso de fondo no revierta.

| Horizonte | Práctica, medida | Práctica, sin redondeo | Paseo aleatorio redondeado |
|-----------|------------------|------------------------|----------------------------|
| 2 | 0,89 | 1,00 | 0,89 |
| 10 | 0,77 | 0,96 | 0,81 |
| 50 | 0,62 | 0,79 | 0,79 |
| 100 | 0,53 | 0,67 | 0,77 |
| 1000 | 0,51 | 0,65 | 0,81 |

El redondeo aporta el 22 % de la varianza del cambio de un tick. Hasta 50 ticks la serie de práctica se parece a un paseo redondeado. La reversión real aparece entre 50 y 100 ticks y deja la razón de varianza en 0,65 a 0,67.

Esa parte de la reversión no se puede explotar: como la orden se ejecuta al precio del tick siguiente, el error de redondeo del precio que vio el programa ya se deshizo cuando la orden se ejecuta.

### 2.4 Validación

`python3 ref/generador.py --validar` (`docs/mediciones/generador_validacion.txt`). Series simuladas de 20 000 ticks contra la de práctica:

| | Varianza | VR(10) | VR(50) | VR(100) | Autocorrelación | Curtosis | Persistencia de la volatilidad |
|-|----------|--------|--------|---------|-----------------|----------|-------------------------------|
| Práctica | 0,75 | 0,77 | 0,62 | 0,53 | -0,11 | 14,4 | 0,19 |
| Modelo, 5 semillas | 0,48 a 0,71 | 0,66 a 0,74 | 0,51 a 0,61 | 0,41 a 0,59 | -0,12 a -0,18 | 9 a 24 | 0,04 a 0,16 |
| Un solo régimen | 0,73 | 0,72 a 0,75 | 0,58 a 0,61 | 0,55 | -0,11 a -0,14 | 3,0 | 0,00 |

El modelo con un solo régimen acierta en la reversión y falla en la curtosis y en la persistencia: los regímenes hacen falta. La prueba que más importa es si la regla base gana en el modelo lo mismo que en la práctica:

| Conjunto | Media | Mediana | Percentil 5 |
|----------|-------|---------|-------------|
| Práctica, 10 bloques | 11 069 | 11 103 | 9 720 |
| Remuestreo (400) | 10 798 | 10 703 | 8 924 |
| Modelo (400) | 10 478 | 10 243 | 9 113 |

En el modelo la regla base gana menos (4,8 % contra 8 % en el remuestreo). Hay dos explicaciones y las dos pesan. La primera es el sesgo de selección: los parámetros de la regla base se eligieron mirando la serie de práctica y el remuestreo usa esos mismos cambios. La segunda es que el modelo es gaussiano y en la práctica las caídas grandes rebotan más: después de una caída de más de 6 unidades bajo la media, el precio sube 2,5 en 20 ticks en la práctica y 1,2 en el modelo (`python3 ref/explorar.py asimetria`). Con 10 bloques la diferencia entre 11 069 y 10 478 es de poco más de un error estándar, así que no alcanza para descartar el modelo.

Consecuencia para el método: se usan las dos evidencias. El remuestreo conserva lo que el modelo no captura y el modelo no depende de la trayectoria particular de la práctica. Una idea que gana en una y pierde en la otra no se acepta.

## 3. Familias calibradas: plausibles y de estrés

Las familias sintéticas de `ref/series.py` ahora salen todas del modelo calibrado. Lo que cambia de una a otra es qué pieza se quita, se exagera o se reemplaza.

| Grupo | Familia | Qué es |
|-------|---------|--------|
| Plausible | `modelo` | El modelo ajustado, tal cual. |
| Plausible | `modelo_vecino` | El modelo con cada parámetro movido al azar hasta la mitad o el doble. Cubre el error de la calibración. |
| Plausible | `dos_componentes` | Nivel más transitoria en un solo régimen, con la varianza promedio. |
| Plausible | `cambio_volatilidad` | Los regímenes alternan rápido: la mitad del tiempo en cada uno. |
| Estrés | `paseo` | Misma volatilidad y regímenes, sin transitoria: no hay nada que predecir. |
| Estrés | `tendencia` | El paseo con deriva de 0,02 a 0,06 por tick (40 a 120 unidades en la serie). El tramo más fuerte de la práctica tiene 0,056. |
| Estrés | `reversion` | Solo la transitoria, alrededor de una media fija. |
| Estrés | `saltos` | Saltos 20 veces más frecuentes (uno cada 200 ticks) y de hasta 30 unidades. |
| Estrés | `cambio_de_caracter` | Primera mitad como la práctica, segunda mitad con tendencia fuerte. |
| Estrés | `volatil` | Siempre en el régimen ruidoso y con el doble de varianza. |
| Estrés | `nivel_bajo` | El modelo con precios entre 15 y 40. |
| Estrés | `plana`, `borde_bajo`, `borde_alto` | Precio constante y series pegadas a 1 y a 255. Prueban la aritmética. |

Antes de calibrar, `reversion` y `dos_componentes` tenían una transitoria tres veces más fuerte que la de la práctica y la regla base ganaba 40 086 y 25 138 en ellas. Esos números no decían nada sobre la competencia.

### La regla base en los dos grupos

`make protocolo` (`docs/mediciones/protocolo_base.txt`), semilla 0:

| Conjunto | n | Media | Mediana | Percentil 5 | Peor | Supera a comprar y mantener |
|----------|---|-------|---------|-------------|------|-----------------------------|
| Práctica, 10 bloques | 10 | 11 069 | 11 103 | 9 720 | 9 720 | 90 % |
| Remuestreo | 1000 | 10 772 | 10 703 | 8 914 | 6 520 | 72 % |
| **Plausibles** | | | | | | |
| `modelo` | 200 | 10 406 | 10 181 | 8 930 | 3 263 | 50 % |
| `modelo_vecino` | 200 | 11 381 | 10 316 | 8 543 | 4 445 | 60 % |
| `dos_componentes` | 200 | 10 772 | 10 749 | 9 138 | 7 276 | 60 % |
| `cambio_volatilidad` | 200 | 11 261 | 10 961 | 7 484 | 2 766 | 66 % |
| Plausibles, todas | 800 | 10 955 | 10 478 | 8 553 | 2 766 | 59 % |
| **Estrés** | | | | | | |
| `paseo` | 200 | 9 927 | 10 054 | 7 866 | 2 271 | 53 % |
| `tendencia` | 200 | 9 410 | 9 990 | 5 777 | 636 | 46 % |
| `reversion` | 200 | 11 513 | 10 253 | 10 000 | 9 764 | 85 % |
| `saltos` | 200 | 12 584 | 10 478 | 4 567 | 1 094 | 50 % |
| `cambio_de_caracter` | 200 | 9 043 | 9 862 | 2 592 | 256 | 46 % |
| `volatil` | 200 | 20 952 | 15 284 | 8 047 | 2 238 | 80 % |
| `nivel_bajo` | 200 | 18 042 | 11 751 | 7 278 | 1 855 | 61 % |
| `plana` | 200 | 10 000 | 10 000 | 10 000 | 10 000 | |
| `borde_bajo` | 200 | 18 496 | 16 854 | 10 046 | 8 851 | 70 % |
| `borde_alto` | 200 | 14 966 | 14 921 | 13 363 | 12 731 | 100 % |

Qué se lee:

1. **En lo plausible la regla base gana entre 4 y 14 % de media**, y en una de cada veinte series pierde más de 14 %.
2. **Los peores casos están en el modelo mismo.** El nivel pasea 18 unidades de desviación estándar en 2000 ticks en el régimen tranquilo y mucho más en el ruidoso. Una serie del modelo que parte en 85 puede terminar en 25, y ahí pierde cualquiera que esté comprado.
3. **Con más volatilidad o precios más bajos gana mucho más** (`volatil`, `nivel_bajo`), porque los mismos movimientos pesan más frente a la comisión. Las medias de esas familias están infladas por pocas series muy buenas: hay que mirar la mediana.
4. **Sin reversión no gana y con tendencia pierde.** En `cambio_de_caracter` el percentil 5 es 2 592.

## 4. Cuánto se puede ganar: filtro de Kalman y política óptima

`python3 ref/politica_optima.py` (`docs/mediciones/politica_optima.txt`).

### 4.1 El mejor estimador del modelo

Si el modelo fuera exacto, el mejor estimador de la transitoria sería el filtro de Kalman de dos estados. En estado estacionario sus ganancias son constantes y la actualización es un producto de matriz de 2x2 por vector:

```
[nivel']   [ 1-K1      -K1*phi  ] [nivel]   [K1]
[trans'] = [ -K2    (1-K2)*phi  ] [trans] + [K2] * precio
```

| | K1 | K2 | Error de la transitoria | Desviación estándar de la transitoria |
|-|----|----|-------------------------|----------------------------------------|
| Régimen tranquilo | 0,614 | 0,184 | 1,11 | 1,19 |
| Régimen ruidoso | 0,742 | 0,225 | 3,29 | 3,54 |

La última comparación es la que explica todo lo demás: después de filtrar, la incertidumbre sobre la transitoria casi no baja (1,11 contra 1,19). El nivel y la transitoria se mueven a escalas parecidas y con un solo precio por tick no se pueden separar bien.

En punto fijo los coeficientes se aproximan por sumas de potencias de dos: `phi = 1 - 1/32 - 1/128 = 0,9609`, `K1 = 1/2 + 1/8 = 0,625` y `K2 = 1/8 + 1/16 = 0,1875`. La matriz queda

```
A = [[ 0,375 , -0,6006 ], [ -0,1875 , 0,7808 ]]      K = [ 0,625 , 0,1875 ]
En Q8 (por 256):  A = [[ 96, -154 ], [ -48, 200 ]]    K = [ 160, 48 ]
```

y la forma que usa `candidatos.Trader` con `est=1`, con el estado en Q8, es

```
Tp = T - (T >> 5) - (T >> 7)      phi * T
e  = (p << 8) - L - Tp            innovación
L  = L + (e >> 1) + (e >> 3)      K1 * e
T  = Tp + (e >> 3) + (e >> 4)     K2 * e
```

`ref/test_candidatos.py` comprueba que esta versión sigue a la de punto flotante con menos de 0,25 unidades de diferencia en 2000 ticks.

### 4.2 La política óptima

La orden se ejecuta un tick después de decidir. Por eso lo único que sirve para predecir es la transitoria estimada `z`: el cambio esperado del precio entre el tick de ejecución y el siguiente es `-phi (1 - phi) z`. Con `z` como estado (es un AR(1)), la política que maximiza la ganancia esperada se calcula por programación dinámica, con comisión de 5 por orden, 63 acciones por orden como máximo y ejecución al tick siguiente.

| Régimen | Primera orden si | Segunda orden si | Vende si | Ganancia óptima por ronda |
|---------|------------------|------------------|----------|---------------------------|
| Tranquilo (z tiene desviación 0,43) | z < -0,34 | z < -0,69 | z > +0,34 | 595 |
| Ruidoso (z tiene desviación 1,29) | z < -0,65 | z < -1,29 | z > +0,65 | 2 371 |
| Mezcla, 86 % tranquilo | | | | 844 (8,4 %) |

Tres cosas salen de aquí:

- **La política óptima es de bandas**, igual que la regla base: entrar bajo un umbral, salir sobre otro, y no hacer nada entre los dos. La comisión es la que abre la banda: sin comisión el umbral de compra es cero.
- **La segunda orden pide el doble de desviación.** Con caja 10 000 y precio 128 se compran 78 acciones: 63 en la primera orden y 15 en la segunda. La segunda paga la misma comisión por una cuarta parte de las acciones.
- **El techo es 8,4 % por ronda** conociendo el modelo y el régimen. La regla base saca 5,2 % en el modelo (10 515 de media en 5000 series).

### 4.3 La política óptima no se traslada bien a la práctica

Las bandas de la política óptima se probaron con el filtro de Kalman en punto fijo (`est=1 E=100 X=120` en `docs/mediciones/exploracion.txt`):

| | Modelo | Vecino | Remuestreo | Bloques |
|-|--------|--------|------------|---------|
| Regla base | 10 515 | 10 996 | 10 813 | 11 069 |
| Bandas óptimas del modelo | 10 943 | 11 824 | 10 119 | 10 308 |

En el modelo gana 4 puntos más que la regla base, que es lo que predice la programación dinámica. En el remuestreo pierde 7 puntos. Las bandas óptimas entran con caídas pequeñas y salen tarde, y eso depende de que la transitoria sea gaussiana y simétrica. En la práctica las caídas pequeñas no rebotan lo suficiente. Por eso la política óptima se usa como cota y como guía de la forma, y los umbrales se eligen donde las dos evidencias coinciden.

## 5. Ideas probadas, una por una

`make exploracion` (`docs/mediciones/exploracion.txt`). Cada tabla cambia una sola pieza. Las columnas son la media y el peor bloque de práctica, la media y el percentil 5 de 5000 remuestreos, de 5000 series del modelo y de 5000 del vecino, y el percentil 5 y el peor caso de las familias de estrés. Todo con la semilla 0.

Con 5000 series el error estándar de una diferencia pareada entre dos configuraciones parecidas es de 10 a 30. Una diferencia menor que 50 no se distingue del ruido.

### 5.1 Bandas

| E, X (en 1/32 de precio) | Bloques: media, peor | Remuestreo: media, p5 | Modelo: media, p5 | Vecino: media, p5 |
|--------------------------|----------------------|-----------------------|-------------------|-------------------|
| 192, -32 (entra a 6, sale 1 antes) | 10 712, 10 000 | 10 652, 9 337 | 10 332, 9 260 | 10 647, 9 130 |
| 128, 0 (regla base) | 11 069, 9 720 | 10 813, 9 017 | 10 515, 8 960 | 10 996, 8 837 |
| 96, 0 | 11 043, 9 620 | 10 868, 8 866 | 10 640, 8 872 | 11 190, 8 695 |
| 64, 16 | 10 826, 8 728 | 10 740, 8 443 | 10 783, 8 656 | 11 475, 8 501 |
| 48, 32 | 10 705, 8 414 | 10 563, 7 892 | 10 885, 8 435 | 11 640, 8 250 |

- **Entre 77 combinaciones, el promedio de las tres medias va de 10 309 a 11 029.** Es una meseta ancha, no un pico.
- **Bandas más angostas suben la media en el modelo y en el vecino, y bajan el percentil 5 en todas partes.** Operar más es estar más tiempo comprado, y estar comprado es llevar el riesgo del nivel.
- **El remuestreo tiene su máximo en E entre 96 y 128 con X en 0.** El modelo lo tiene en E = 48 con X = 32. Donde coinciden las dos evidencias es en E = 96: mejora a la regla base en las tres medias.

### 5.2 Estimador del nivel

| Estimador | Bandas | Bloques: media, peor | Remuestreo: media, p5 | Modelo | Vecino |
|-----------|--------|----------------------|-----------------------|--------|--------|
| Media exponencial, alfa 1/8 | entra 4 | 10 173, 8 843 | 10 185, 8 945 | 10 177 | 10 398 |
| Media exponencial, alfa 1/16 | entra 4 | 10 446, 8 503 | 10 561, 9 094 | 10 306 | 10 672 |
| Media exponencial, alfa 1/32 | entra 4 (regla base) | 11 069, 9 720 | 10 813, 9 017 | 10 515 | 10 996 |
| Media exponencial, alfa 1/64 | entra 3 | 10 618, 8 662 | 10 682, 8 281 | 10 752 | 11 484 |
| Media exponencial, alfa 1/128 | entra 3 | 10 365, 8 125 | 10 521, 7 698 | 10 697 | 11 412 |
| Suma móvil de 32 | entra 4 | 10 645, 9 279 | 10 658, 8 967 | 10 424 | 10 881 |
| Suma móvil de 64 | entra 4 | 11 031, 9 285 | 10 786, 8 666 | 10 669 | 11 178 |
| Kalman de dos estados | E=250, X=-40 | 11 102, 10 000 | 10 840, 9 034 | 10 503 | 10 980 |
| Kalman de dos estados | E=190, X=-40 | 11 002, 9 678 | 10 908, 8 869 | 10 635 | 11 202 |

- **Alfa 1/32 es el mejor compromiso.** Con alfa más grande la media sigue al precio y no queda desviación que operar. Con un alfa menor mejora el modelo y empeora el remuestreo y el percentil 5.
- **La suma móvil no mejora a la media exponencial** y ocupa 32 o 64 palabras de memoria.
- **El Kalman de dos estados empata.** Con las bandas E=250, X=-40 se parece a la regla base y con E=190, X=-40 se parece a E=96. La comparación formal está en la sección 7.3.

Es lo que anticipa la sección 4.1: si el filtro óptimo casi no reduce la incertidumbre, cambiar de filtro no puede cambiar mucho el resultado.

### 5.3 Bandas escaladas con la volatilidad

La política óptima usa bandas distintas en cada régimen. Se probó hacer las bandas proporcionales a la volatilidad medida (media exponencial del valor absoluto del cambio): 368 combinaciones. La mejor da 11 028 de promedio de las tres medias, contra 11 029 de la mejor banda fija, así que la banda escalada no mejora el resultado. La banda fija de 3 a 4 unidades ya queda ancha para el régimen tranquilo y justa para el ruidoso, que es lo que haría la banda escalada.

### 5.4 Asimetría entre caídas y subidas

`python3 ref/explorar.py asimetria`. Cambio medio del precio 20 ticks después de la ejecución, según la desviación al decidir:

| Desviación | Práctica | Modelo |
|------------|----------|--------|
| Bajo -6 | +2,52 | +1,15 |
| -4 a -3 | +0,50 | +0,55 |
| -2 a -1 | +0,12 | +0,26 |
| +1 a +2 | -0,33 | -0,13 |
| +3 a +4 | -0,23 | -0,41 |

- **Para desviaciones moderadas la respuesta es simétrica** y parecida a la del modelo.
- **Las caídas grandes rebotan el doble que en el modelo.** Son 287 ticks que vienen de pocos episodios, así que la evidencia es poca, pero es la razón por la que el remuestreo prefiere umbrales de entrada más altos que el modelo.
- **No hay una asimetría que se pueda explotar más allá de eso.** El mercado no permite vender lo que no se tiene, así que cuando el precio está sobre la media lo único que se puede hacer es estar en caja, y eso ya lo hace la regla.

### 5.5 Saltos

Con `J = 8`, un cambio de 8 o más en un tick se trata como salto de nivel: la media se corre con el precio y no se opera por él.

| | Bloques: media, peor | Remuestreo | Modelo | Vecino | `saltos`: percentil 5 |
|-|----------------------|------------|--------|--------|------------------------|
| Regla base | 11 069, 9 720 | 10 813 | 10 515 | 10 996 | 4 758 |
| Con J = 8 | 10 873, 9 227 | 10 744 | 10 519 | 11 009 | 7 126 |

En el modelo, donde los saltos son permanentes, no cuesta nada. En los bloques cuesta 196 porque dos de los cinco saltos de la práctica fueron hacia abajo y el precio subió después: la regla base los compró y ganó. Con cinco saltos eso es suerte, no evidencia. Donde los saltos son frecuentes el percentil 5 sube de 4 758 a 7 126.

### 5.6 Cortes de una posición

| | Bloques: media, peor | Remuestreo: media, p5 | Modelo | Vecino | `tendencia`: p5 | `cambio_de_caracter`: p5 |
|-|----------------------|-----------------------|--------|--------|-----------------|---------------------------|
| Regla base | 11 069, 9 720 | 10 813, 9 017 | 10 515 | 10 996 | 5 751 | 2 592 |
| Tope de tiempo, 48 ticks | 11 039, 10 000 | 10 773, 9 138 | 10 426 | 10 815 | 6 856 | 5 538 |
| Tope de tiempo, 24 ticks | 10 729, 10 000 | 10 550, 9 081 | 10 281 | 10 549 | 7 434 | 6 858 |
| Tope de precio, 12 unidades | 11 051, 10 000 | 10 629, 8 709 | 10 373 | 10 675 | 6 529 | 4 749 |
| Tope de precio, 6 unidades | 10 725, 9 984 | 10 317, 8 690 | 10 225 | 10 437 | 7 142 | 6 189 |

- **El tope de tiempo es el corte más barato.** Salir si la posición lleva más de 48 ticks (casi tres vidas medias de la transitoria) cuesta 40 en el remuestreo y sube el percentil 5. En la práctica casi todas las posiciones que ganan se cierran antes de 45 ticks, y las pérdidas grandes vienen de posiciones de 50 a 110 ticks.
- **El tope de precio es caro.** Vender porque el precio cayó es lo contrario de la regla: con 6 unidades cuesta 500 en el remuestreo.

### 5.7 Tamaño de las órdenes y entrada escalonada

| | Remuestreo: media, p5 | Modelo: media, p5 | `tendencia`: p5 |
|-|-----------------------|-------------------|-----------------|
| Siempre "comprar 63" (regla base) | 10 813, 9 017 | 10 515, 8 960 | 5 751 |
| Una sola orden por entrada | 10 531, 9 320 | 10 353, 9 293 | 6 634 |
| Segunda orden solo si el precio es 110 o menos | 10 786, 9 134 | 10 510, 9 087 | 5 835 |
| 40 acciones al entrar y el resto a 6 unidades | 10 726, 9 241 | 10 414, 9 146 | 6 690 |
| 20 acciones al entrar y el resto a 8 unidades | 10 596, 9 366 | 10 303, 9 265 | 7 430 |

Ninguna variante sube la media. Todas bajan la exposición: menos media y mejor percentil 5. Ahorrar la comisión de la segunda orden no compensa lo que deja de ganar esa parte de la posición. Operar con menos que todo el patrimonio es otra forma de moverse por la misma frontera, y la que da más media por punto de percentil 5 es la de las bandas.

### 5.8 Ideas que aprenden en vivo

`make experimentos` (`docs/mediciones/experimentos.txt`). Diferencia pareada contra la regla base, con su error estándar:

| Idea | Remuestreo (400) | Modelo (400) | Órdenes por ronda |
|------|------------------|--------------|-------------------|
| Población de 15 traders virtuales, se sigue al líder con margen | -57 ± 45 | +157 ± 49 | 51 contra 30 |
| Adaptación con prior fuerte (3 traders vecinos, margen grande) | -16 ± 9 | +19 ± 10 | 31 contra 30 |
| Perceptrón en línea con histéresis | -199 ± 57 | -49 ± 57 | 53 contra 30 |

- **La población** termina comportándose como una banda más angosta: gana en el modelo y pierde en el remuestreo, igual que E = 64. No aprende nada que una banda fija no tenga.
- **La adaptación con prior fuerte** casi nunca deja la regla base, y cuando la deja no gana.
- **El perceptrón** pierde aunque ya no opera 2000 veces: con histéresis hace 53 órdenes. Pierde porque aprende de muy pocos casos por ronda.

La razón de fondo es la del punto 3 del resumen: hay una unidad de log-verosimilitud de evidencia por ronda. Adaptarse a la serie en curso es ajustar parámetros con casi nada de información.

## 6. Guardia de régimen y tope de pérdida

### 6.1 Qué no se puede hacer

La primera idea de guardia era estadística: medir en vivo si la serie revierte y dejar de operar si no. `python3 ref/explorar.py potencia`:

| Razón de varianza a 50 ticks, en una serie de 2000 | Percentil 5 | Mediana | Percentil 95 |
|-----------------------------------------------------|-------------|---------|--------------|
| `modelo` (revierte) | 0,37 | 0,53 | 0,84 |
| `paseo` (no revierte) | 0,46 | 0,66 | 1,08 |
| `tendencia` | 0,47 | 0,65 | 1,02 |

Las distribuciones se traslapan casi enteras. Una guardia que saltara cuando la razón pasa de 0,84 se activaría en el 5 % de las series que sí revierten y solo en el 20 % de los paseos aleatorios. No existe un estadístico que separe los dos casos dentro de una ronda, porque la información no está.

También se probó una guardia por tendencia (una media lenta de la desviación). Para que proteja tiene que activarse en más de la mitad de los remuestreos, y calibrada para activarse en el 1 % no hace nada (`docs/mediciones/exploracion.txt`).

### 6.2 Qué sí funciona: medir si las entradas están volviendo

La guardia que quedó no mira el precio sino el resultado de la propia regla:

- **Tope de tiempo** (`tmax = 48`). Si una posición lleva más de 48 ticks sin que el precio recupere la media, se sale. No se vuelve a entrar hasta que el precio haya recuperado la media.
- **Guardia de régimen** (`nfal = 3`, `gapag = 1000`). Si tres posiciones seguidas terminan por el tope de tiempo, la serie no está revirtiendo: se deja de operar por 1000 ticks. Una salida normal borra la cuenta.
- **Manejo de saltos** (`J = 8`), el de la sección 5.5.
- **Tope de pérdida** (`capsh = 1`). Se lleva la suma de `precio de salida - precio de entrada` de las posiciones, medida desde su mejor momento y contando la posición abierta. Si la caída pasa de la mitad del precio actual, se sale y no se opera más en la ronda.

Todo son contadores, sumas y comparaciones. No hay multiplicaciones: la mitad del precio se compara como `2 * caída + precio <= 0`.

### 6.3 Cuánto se activa y cuánto cuesta

Sobre el candidato de E = 96 (sección 7), con la semilla reservada:

| | Solo bandas | Con saltos y guardia | Con saltos, guardia y tope |
|-|-------------|----------------------|----------------------------|
| **Activación** | | | |
| Bloques de práctica: pausas de la guardia y topes | | 0 y 0 | 0 y 0 |
| Remuestreos en que la guardia llegó a pausar | | 2,3 % | 2,3 % |
| Remuestreos en que saltó el tope | | | 1,7 % |
| Ticks sin poder operar, en los remuestreos | | 0,7 % | 1,2 % |
| **Costo en media** | | | |
| Bloques | 11 043 | 11 018 | 11 018 |
| Remuestreo | 10 833 | 10 735 (-98) | 10 716 (-117) |
| Plausibles | 11 103 | 10 893 (-210) | 10 714 (-389) |
| **Peor caso en estrés** | | | |
| `tendencia`: percentil 5 y peor | 4 631 y 518 | 6 375 y 1 712 | 7 052 y 5 845 |
| `cambio_de_caracter`: percentil 5 y peor | 2 136 y 224 | 5 692 y 744 | 7 017 y 5 213 |
| `paseo`: percentil 5 y peor | 7 143 y 1 223 | 7 451 y 1 421 | 7 299 y 6 009 |
| `saltos`: percentil 5 y peor | 4 631 y 180 | 6 769 y 190 | 6 603 y 1 164 |
| `volatil`: media | 20 790 | 18 336 | 12 225 |
| `nivel_bajo`: media | 19 051 | 17 000 | 11 008 |

- **En los 10 bloques de práctica la guardia no pausa nunca y el tope no salta nunca.** El tope de tiempo sí corta 13 posiciones en los 10 bloques, que es su trabajo normal.
- **La guardia cuesta 1 % en el remuestreo y 2 % en las plausibles**, y sube el percentil 5 de `tendencia` de 4 631 a 6 375 y el de `cambio_de_caracter` de 2 136 a 5 692. No pone piso al peor caso.
- **El tope sí pone piso**: el peor caso de `tendencia`, `paseo` y `cambio_de_caracter` queda sobre 5 200. Cuesta otro 0,2 % en el remuestreo y 1,6 % en las plausibles.
- **El tope se paga caro si la serie es más volátil que la de práctica.** En `volatil` y `nivel_bajo` la regla sin tope gana 20 790 y 19 051 de media, y con tope 12 225 y 11 008. En esas series las caídas de medio precio son parte del camino normal y después se recuperan. Si la serie oculta tuviera el doble de volatilidad, el tope haría perder la mayor parte de la ganancia.
- **Los saltos grandes no los cubre nada.** Un salto de -30 con la posición abierta se pierde completo: el peor caso de `saltos` sigue cerca de 1 000 con todas las protecciones.

Un tope más ajustado (25 % del precio) salta en el 9 % de los remuestreos y cuesta 1 % de media en el remuestreo y 5 % en el vecino (`docs/mediciones/exploracion.txt`). El motivo es que vende en el fondo de caídas que después se recuperan: es el mismo efecto del tope de precio de la sección 5.6.

## 7. Candidatos

### 7.1 Cómo se eligieron y con qué se miden

Se probaron unas 3000 combinaciones de parámetros con la semilla 0. Para que la tabla final no tenga el sesgo de haber elegido lo mejor entre muchas, toda la evidencia sintética se regeneró con otra semilla (5000 remuestreos, 10 000 series plausibles y 7000 de estrés) y ahí se evaluaron solo los finalistas. **Ningún parámetro se eligió ni se retocó mirando la semilla 1.** Los 10 bloques de práctica son los mismos en las dos: son la única evidencia sin reserva posible.

`make frontera` (`docs/mediciones/frontera.txt`). Los números de las dos semillas coinciden dentro de 1 %, que es lo esperable si no hubo sobreajuste a la semilla 0.

### 7.2 La tabla

Semilla reservada. La diferencia es contra la regla base, serie por serie, con su error estándar.

| Candidato | Parámetros | Bloques: media, peor | Remuestreo: media, dif., p5 | Plausibles: media, dif., p5 | Estrés: p5, peor | Costo estimado |
|-----------|------------|----------------------|-----------------------------|------------------------------|------------------|----------------|
| `prudente` | E=192, X=-32 | 10 712, 10 000 | 10 639, -115 ± 14, 9 308 | 10 619, -334 ± 19, 9 048 | 6 986, 197 | 27 instr., 58 ciclos |
| `base` | E=128, X=0 | 11 069, 9 720 | 10 754, 8 958 | 10 954, 8 741 | 5 615, 156 | 27 instr., 58 ciclos |
| `max_media` | E=96, X=0 | 11 043, 9 620 | 10 833, +79 ± 11, 8 788 | 11 103, +150 ± 15, 8 622 | 5 071, 180 | 27 instr., 58 ciclos |
| `guardia` | E=96, X=0, saltos y guardia | 11 018, 9 024 | 10 735, -20 ± 14, 8 881 | 10 893, -60 ± 15, 8 434 | 6 658, 190 | unas 70 instr., 150 ciclos |
| `guardia_tope` | E=96, X=0, saltos, guardia y tope | 11 018, 9 024 | 10 716, -38 ± 15, 8 833 | 10 714, -239 ± 32, 8 052 | 6 828, 1 164 | unas 85 instr., 183 ciclos |

Probabilidad de superar a comprar y mantener, en remuestreo y en plausibles: `prudente` 66 y 57 %, `base` 69 y 61 %, `max_media` 71 y 64 %, `guardia` 70 y 62 %, `guardia_tope` 69 y 61 %.

El costo es una estimación con el modelo de `docs/trade_s.md` hasta que el candidato esté escrito en `trade.s`. El presupuesto de la ronda 3 es de 2 262 ciclos: todos caben con holgura.

### 7.3 Qué se pierde con cada uno

- **`max_media`.** Es la regla base con el umbral de entrada en 3 unidades en vez de 4: en `trade.s` cambia una constante. Gana 0,7 % en el remuestreo y 1,4 % en las plausibles, con diferencias de 7 y 10 errores estándar. Se pierde 170 en el percentil 5 del remuestreo y 120 en el de las plausibles, y queda sin ninguna defensa si la serie no revierte: en `tendencia` el percentil 5 es 4 631 y en `cambio_de_caracter` 2 136. En los 10 bloques queda 26 por debajo de la regla base, con un error de 238: no se distinguen.
- **`guardia`.** Lo mismo con manejo de saltos y guardia de régimen. Entrega casi toda la ventaja de `max_media` sobre la regla base (queda 20 por debajo en el remuestreo y 60 en las plausibles) a cambio de subir el percentil 5 del estrés de 5 071 a 6 658. No pone piso al peor caso. El peor bloque de práctica baja a 9 024.
- **`guardia_tope`.** Agrega el tope de pérdida. El peor caso de las familias con tendencia queda sobre 5 200. Se pierde 2,2 % en las plausibles frente a la regla base y casi toda la ganancia si la serie resulta más volátil que la de práctica.
- **`prudente`.** Entra solo con caídas de 6 unidades y sale antes de recuperar la media. Es el mejor percentil 5 en remuestreo y plausibles (350 y 300 más que la regla base) y el único que no pierde en ningún bloque de práctica. Se pierde 1,1 % de media en el remuestreo y 3,1 % en las plausibles.

Bajo el criterio de aceptación del protocolo (media y peor bloque mayores o iguales, media y percentil 5 de los remuestreos mayores o iguales, ninguna familia baja más de 1 %), **ningún candidato reemplaza formalmente a la regla base** (`docs/mediciones/protocolo_*.txt`). `max_media` falla por 26 puntos en la media de los bloques, que es ruido, y por las familias de estrés. Los demás cambian media por protección o al revés. Por eso la decisión es de perfil de riesgo y no sale sola del protocolo.

### 7.4 El estimador de dos estados

El filtro de Kalman en punto fijo de la sección 4.1 contra la media exponencial, con bandas equivalentes, semilla reservada:

| | Bloques: media, peor | Remuestreo: media, p5 | Plausibles: media, p5 | Estrés: media |
|-|----------------------|-----------------------|-----------------------|---------------|
| Regla base | 11 069, 9 720 | 10 754, 8 958 | 10 954, 8 741 | 12 656 |
| Kalman, E=250, X=-40 | 11 102, 10 000 | 10 785 (+30 ± 5), 9 004 | 10 946 (-8 ± 8), 8 741 | 12 604 (-51 ± 27) |
| `max_media` | 11 043, 9 620 | 10 833, 8 788 | 11 103, 8 622 | 13 112 |
| Kalman, E=190, X=-40 | 11 002, 9 678 | 10 863 (+30), 8 825 | 11 086 (-17), 8 596 | 13 080 |

Con el criterio del protocolo (`docs/mediciones/protocolo_kalman_base.txt`) cumple en los bloques y en los remuestreos y no cumple en las familias: baja más de 1 % en `saltos`, `borde_bajo` y `borde_alto`. **No reemplaza a la regla base.** La ventaja en el remuestreo es de 0,3 % y en el modelo, que es para lo que el filtro es óptimo, no hay ninguna. Cuesta unas 140 instrucciones por tick en software, porque necesita seis desplazamientos de números con signo, contra 27 de la media exponencial.

Queda como pieza de la edición de exhibición: es el caso natural para el producto de matriz 2x2 en hardware.

### 7.5 Recomendación

Con el perfil de riesgo que fijó el grupo (maximizar el patrimonio esperado), el candidato es **`max_media`**: es el único que sube la media en las dos evidencias independientes, con significancia, y no agrega una sola instrucción.

La alternativa razonable es **`guardia`**. Cuesta 1 % de media frente a `max_media` y conviene si se le da más de un 20 % de probabilidad a que alguna serie oculta tenga una tendencia sostenida: en `tendencia` gana 490 de media sobre `max_media` y en `cambio_de_caracter` 965, y en las plausibles pierde 210.

`guardia_tope` no se recomienda con este perfil. El piso que pone solo importa en escenarios en que comprar y mantener también se hunde, y cuesta mucho si la serie oculta es más volátil.

### 7.6 Lo que se eligió

Desde el 15/11 `sw/trade.s` y `ref/trader.py` corren `max_media` (decisiones T50 y T51). La regla base se conserva en `ref/trader.py` como `ReglaBase`, porque es la referencia contra la que el protocolo compara a los candidatos. Al cambiar, `max_media` sigue sin cumplir formalmente el criterio de aceptación del protocolo (falla por 26 puntos en la media de los 10 bloques, dentro del ruido, y por las familias de estrés) y en la serie completa de práctica queda en 25 973 contra 27 062. Lo que la respalda son los remuestreos, las familias plausibles y los puntos esperados del torneo medidos en `factibilidad/retorno/` (+0,04 sobre la regla base a 2 000 ticks). La tabla del punto 3.1 sale de `make tabla-3-1`.

## 8. Lo que no se sabe

- **Si las series ocultas salen del mismo generador.** Toda la tabla supone que sí, o algo parecido. Sigue siendo la pregunta más importante para el ayudante.
- **Cuántos ticks dura cada ronda.** La guardia pausa 1000 ticks y el tope apaga hasta el final. En una ronda de 200 000 ticks habría que rearmar el tope.
- **El costo exacto en instrucciones** de `guardia` y `guardia_tope`, hasta escribirlos en `trade.s`.
- **Diez bloques son pocos.** La media de los bloques tiene un error estándar cercano a 240. Diferencias de 26 o 51 entre candidatos en los bloques no dicen nada.

## 9. Preguntas que nos pueden hacer

**¿Por qué reversión y no tendencia?** Porque la razón de varianza es menor que 1 en todos los horizontes y en los 20 bloques de 1000 ticks, y porque el modelo ajustado tiene una componente transitoria con vida media de 17,5 ticks. Seguir tendencia pierde en la serie de práctica (`make hallazgos`).

**¿Cuánta reversión hay realmente?** Menos de la que parece. La mitad de la caída de la razón de varianza es redondeo y no se puede operar. La otra mitad es una transitoria de 1,2 unidades de desviación estándar, contra un nivel que se mueve 0,4 por tick.

**¿Cómo saben que no es sobreajuste?** Por tres cosas. Los candidatos se evaluaron con una semilla que no se usó para elegir nada. Los parámetros están en una meseta: E entre 80 y 128 da medias dentro de 60 puntos. Y el modelo, que no usa los cambios de la práctica uno por uno, coincide en el signo de la mejora.

**¿Por qué no usar la política óptima?** Porque es óptima para el modelo, no para la serie. En el remuestreo de la serie real pierde 7 puntos contra la regla base.

**¿Por qué el Kalman no gana si es el estimador óptimo?** Porque el problema está mal condicionado: después de filtrar, la incertidumbre de la transitoria baja de 1,19 a 1,11. Ningún estimador puede sacar una señal que el precio no trae.

**¿Qué pasa si la serie oculta es distinta?** Está medido en las familias de estrés. Sin reversión no se gana, con tendencia a la baja se pierde, y con más volatilidad se gana más. La guardia sube el percentil 5 en tendencia de 4 631 a 6 375.

**¿Por qué la guardia no es un test estadístico?** Porque no tiene potencia. Con 2000 ticks la razón de varianza de una serie que revierte y la de un paseo aleatorio se traslapan casi enteras. La guardia mide otra cosa: si las últimas tres entradas volvieron o no.

**¿Cuánto del resultado es suerte?** La mayor parte. La ganancia esperada es de 5 a 11 % según el conjunto, y con la misma regla una de cada veinte rondas termina con más de 10 % de pérdida. En una ronda, una de cada tres veces se termina bajo comprar y mantener.

## 10. Cómo reproducir

```bash
make test-candidatos        # el motor coincide con la referencia (5 segundos)
make generador              # ajuste, validación y redondeo
make politica               # Kalman y política óptima
make exploracion            # una tabla por idea (poco más de un minuto)
make experimentos           # población, adaptación y perceptrón
make frontera               # candidatos con las dos semillas
make protocolo-candidatos   # cada candidato contra la base con la referencia en Python
make algoritmo              # todo lo anterior (unos 3 minutos)

python3 ref/candidatos.py                             # lista de candidatos
python3 ref/protocolo.py --comparar cand:max_media    # una comparación
python3 ref/protocolo.py --estrategia trader:E=96,X=0,J=8 --semilla 1
python3 ref/explorar.py bandas saltos                 # solo algunas secciones
```
