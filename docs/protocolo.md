# Protocolo de evaluación de algoritmos

Documento de estudio de `ref/series.py` y `ref/protocolo.py`: con qué series se evalúa un algoritmo, qué se informa, cuándo un candidato reemplaza a la regla base y qué dio la regla base.

| Archivo | Qué es |
|---------|--------|
| `ref/series.py` | Series de prueba: bloques, remuestreo y familias sintéticas. |
| `ref/protocolo.py` | Evaluación, comparación, meseta y verificación del binario. |
| `ref/trader.py`, `ref/market.py` | La estrategia de referencia y el mercado. |
| `docs/mediciones/protocolo_*.txt` | Resultados de `make protocolo`. |

## 1. El problema que resuelve

La regla base termina con 27 062 en la serie de práctica completa. Ese número no dice cuánto va a ganar el día de la competencia, por tres razones:

1. **Los parámetros se eligieron mirando esa misma serie.** En una grilla de 336 configuraciones de reversión, la mediana es 11 204 y el máximo 27 226. La regla base está casi en el máximo: parte de su resultado es haber elegido bien después de ver los datos.
2. **Es una sola trayectoria de 20 000 ticks, con interés compuesto.** Ganar en los primeros tramos agranda todo lo que viene después. El promedio por bloque de 2000 ticks es 11 069, no 27 062.
3. **Las series de la competencia son otras.** Pueden salir del mismo generador o no.

El protocolo fija, antes de probar ninguna idea nueva, cómo se va a medir. Así una mejora no se acepta porque se ve bien en un número elegido después.

## 2. Las series

Todas son de enteros entre 1 y 255, de 2000 ticks, y se regeneran iguales con la misma semilla. Son datos de prueba: nada de esto queda dentro del diseño.

### Bloques de la serie de práctica

Los 10 tramos consecutivos de 2000 ticks. Cada bloque parte con caja 10 000 y sin acciones, como una ronda. Es lo más parecido a la competencia que tenemos, pero son solo 10 muestras y son las mismas con que se eligieron los parámetros.

### Remuestreo por bloques de los incrementos

Se toman los cambios de precio de un tick al siguiente, se cortan en bloques de 100 ticks seguidos, se eligen bloques al azar con reposición y se vuelven a sumar partiendo de un precio de la serie original. Si el nivel toca 1 o 255, rebota.

- **Qué conserva:** la dependencia entre ticks vecinos dentro de cada bloque. La reversión que explota la regla base ocurre en horizontes de 10 a 50 ticks, así que queda dentro. La razón de varianza promedio de los remuestreos es 0,75 a 10 ticks y 0,62 a 50, contra 0,73 y 0,57 de los bloques originales.
- **Qué pierde:** la relación entre bloques. El nivel de largo plazo de una serie remuestreada es un paseo aleatorio, sin la reversión lenta de la original (0,53 a 100 ticks).
- **Consecuencia:** para una regla de reversión es una prueba más dura que la serie original. Un algoritmo que gana aquí no depende de la trayectoria particular de la serie de práctica.

Se usan 1000 remuestreos.

### Familias sintéticas

Sirven para la pregunta "¿y si la serie oculta es distinta?". 200 series de cada una. Todas salen del modelo ajustado a la serie de práctica (`ref/generador.py`, `ref/calibracion.py`): la volatilidad, los dos regímenes, la escala de la reversión y el tamaño de los saltos son los medidos. Lo que cambia de una familia a otra es qué pieza del modelo se quita, se exagera o se reemplaza. El detalle de la calibración está en `docs/algoritmo.md`, secciones 2 y 3.

Están separadas en dos grupos:

| Grupo | Familias | Para qué |
|-------|----------|----------|
| Plausibles (`series.PLAUSIBLES`) | `modelo`, `modelo_vecino`, `dos_componentes`, `cambio_volatilidad` | Se parecen a la serie de práctica. Si la serie oculta sale del mismo generador, debería parecerse a una de estas. |
| De estrés (`series.ESTRES`) | `paseo`, `tendencia`, `reversion`, `saltos`, `cambio_de_caracter`, `volatil`, `nivel_bajo`, `plana`, `borde_bajo`, `borde_alto` | Algo importante es distinto: no hay reversión, hay tendencia, los saltos son frecuentes, cambia la volatilidad o el nivel. Miden cuánto se pierde si la serie oculta no se parece a la de práctica. |

`python3 ref/series.py listar` muestra una serie de cada familia con su grupo, su rango y su razón de varianza. Dos advertencias:

- **El redondeo fabrica reversión.** Un paseo aleatorio redondeado a enteros tiene razón de varianza cercana a 0,8 a cualquier horizonte largo, sin que haya nada que predecir. Cerca de la mitad de la reversión aparente de la serie de práctica viene de ahí (`python3 ref/generador.py --redondeo`).
- **Con precios bajos o mucha volatilidad las medias engañan.** En `nivel_bajo`, `volatil` y `borde_bajo` unas pocas series multiplican el patrimonio varias veces e inflan la media. Por eso la tabla trae también la mediana y el percentil 5.

### Semilla de exploración y semilla reservada

Todo lo anterior se regenera igual con la misma semilla. La semilla 0 es la de exploración: con ella se probaron las ideas y se eligieron los parámetros. La semilla 1 queda reservada: se usa solo para evaluar a los finalistas (`python3 ref/protocolo.py --semilla 1`, `make frontera`). Así la tabla final no tiene el sesgo de haber elegido lo mejor entre miles de combinaciones. Los 10 bloques de práctica son los mismos con cualquier semilla.

## 3. Qué se informa

Para cada conjunto: media, mediana, percentil 5, peor caso, mejor caso, fracción de series en que supera a comprar y mantener, fracción en que termina sobre 10 000, y órdenes promedio. Comprar y mantener es la referencia del testbench: comprar todo en el primer tick y no vender.

En todas las corridas el programa ve todos los precios, que es la situación de la competencia (la placa está encendida antes del primer precio).

## 4. Criterio de aceptación

`python3 ref/protocolo.py --comparar CANDIDATA` evalúa el candidato y la base sobre las mismas series, y el candidato reemplaza a la base solo si cumple las tres condiciones:

| | Conjunto | Condición |
|-|----------|-----------|
| a | 10 bloques de práctica | Media y peor bloque mayores o iguales que los de la base. |
| b | 1000 remuestreos | Media y percentil 5 mayores o iguales. |
| c | Cada familia sintética | La media no baja más de 1 %. |

La condición a es el principio del proyecto: una pieza cambia la forma de operar solo si mejora la media y el peor bloque. La b pide lo mismo donde hay 1000 muestras en vez de 10, y usa el percentil 5 porque el peor de 1000 es demasiado ruidoso. La c evita aceptar algo que gana en la serie de práctica a costa de hundirse si la serie oculta es distinta.

Un candidato que no cumple se queda como experimento documentado, con su tabla.

### Error de la diferencia

La comparación informa además la diferencia pareada: para cada serie se resta el patrimonio de la base al del candidato, y se entrega la media de esas diferencias con su error estándar (columnas `dif` y `+-ee`). Comparar serie por serie quita casi toda la dispersión que viene de la serie y deja la que viene del algoritmo. Una diferencia menor que dos errores estándar no se distingue del ruido. En los 10 bloques el error es grande (cerca de 240 entre dos reglas parecidas), así que la condición a decide poco por sí sola: sirve para descartar lo que empeora claramente.

### Meseta

`python3 ref/protocolo.py --meseta` evalúa la regla base con parámetros vecinos (k entre 4 y 6, umbral de entrada entre 2 y 6, umbral de salida entre 0 y 2). Un buen parámetro tiene vecinos que rinden parecido. Un máximo aislado es señal de sobreajuste.

## 5. Resultados de la regla base

Salida de `make protocolo` (`docs/mediciones/protocolo_base.txt`), semilla 0:

| Conjunto | n | Media | Mediana | Percentil 5 | Peor | Supera a comprar y mantener | Órdenes |
|----------|---|-------|---------|-------------|------|-----------------------------|---------|
| Práctica, 10 bloques | 10 | 11 069 | 11 103 | 9 720 | 9 720 | 90 % | 29,9 |
| Remuestreo | 1000 | 10 772 | 10 703 | 8 914 | 6 520 | 72 % | 30,2 |
| **Plausibles** | | | | | | | |
| `modelo` | 200 | 10 406 | 10 181 | 8 930 | 3 263 | 50 % | 22,0 |
| `modelo_vecino` | 200 | 11 381 | 10 316 | 8 543 | 4 445 | 60 % | 36,0 |
| `dos_componentes` | 200 | 10 772 | 10 749 | 9 138 | 7 276 | 60 % | 36,6 |
| `cambio_volatilidad` | 200 | 11 261 | 10 961 | 7 484 | 2 766 | 66 % | 60,6 |
| Plausibles, todas | 800 | 10 955 | 10 478 | 8 553 | 2 766 | 59 % | 38,8 |
| **Estrés** | | | | | | | |
| `paseo` | 200 | 9 927 | 10 054 | 7 866 | 2 271 | 53 % | 25,1 |
| `tendencia` | 200 | 9 410 | 9 990 | 5 777 | 636 | 46 % | 30,1 |
| `reversion` | 200 | 11 513 | 10 253 | 10 000 | 9 764 | 85 % | 22,6 |
| `saltos` | 200 | 12 584 | 10 478 | 4 567 | 1 094 | 50 % | 49,6 |
| `cambio_de_caracter` | 200 | 9 043 | 9 862 | 2 592 | 256 | 46 % | 31,6 |
| `volatil` | 200 | 20 952 | 15 284 | 8 047 | 2 238 | 80 % | 196,7 |
| `nivel_bajo` | 200 | 18 042 | 11 751 | 7 278 | 1 855 | 61 % | 149,2 |
| `plana` | 200 | 10 000 | 10 000 | 10 000 | 10 000 | | 0,0 |
| `borde_bajo` | 200 | 18 496 | 16 854 | 10 046 | 8 851 | 70 % | 134,8 |
| `borde_alto` | 200 | 14 966 | 14 921 | 13 363 | 12 731 | 100 % | 53,5 |
| Estrés, todas | 2000 | 13 493 | 10 474 | 6 980 | 256 | 69 % | 69,3 |

Qué se lee de la tabla:

1. **La ganancia esperada por ronda es de 4 a 14 % en lo que se parece a la práctica.** En los remuestreos la media es 10 772, contra 9 583 de comprar y mantener sobre las mismas series. El 27 062 de la serie completa es ese rendimiento compuesto diez veces sobre una trayectoria favorable.
2. **En una de cada cinco series plausibles termina bajo 10 000**, y el percentil 5 está entre 7 500 y 9 100. La regla base sola no asegura no perder.
3. **Sin reversión no gana.** En el paseo aleatorio la mediana es 10 054: queda en la caja inicial.
4. **En tendencia puede perderlo casi todo.** Peor caso 636 en `tendencia` y 256 en `cambio_de_caracter`. La regla compra porque el precio cayó bajo su media, el precio sigue cayendo, y no vende hasta que recupere la media. Es el caso que cubren la guardia de régimen y el tope de pérdida (`docs/algoritmo.md`, sección 6).
5. **En serie plana no opera.** Ni una orden en las 200 series.
6. **Con más volatilidad o precios más bajos opera y gana mucho más**, porque los mismos movimientos pesan más frente a la comisión. En esas familias hay que mirar la mediana y no la media.

Con las familias sin calibrar, `reversion` y `dos_componentes` daban 40 086 y 25 138 porque su componente transitoria era tres veces más fuerte que la de la práctica. Calibradas dan 11 513 y 10 772.

### Meseta de la regla base

`docs/mediciones/protocolo_meseta.txt`, 45 combinaciones:

| | Bloques, media | Remuestreos (300), media |
|-|----------------|--------------------------|
| Regla base (k = 5, entra 4, sale 0) | 11 069 | 10 816 |
| Sus 5 vecinos a distancia 1 | 10 446 a 11 043 | 10 602 a 10 921 |
| Mejor de las 45 | 11 069, la regla base | 10 921, con entra 3 |

En los bloques la regla base es el máximo de las 45, que es lo esperable si se eligió mirándolos. En los remuestreos queda dentro del grupo de arriba y un vecino la supera por un 1 %. No es un máximo aislado: todas las combinaciones con k = 5 y salida en 0 dan entre 10 712 y 10 921. La diferencia entre vecinos es del tamaño del ruido de 300 remuestreos, así que no hay base para cambiar los parámetros con esta evidencia.

### Primera comparación: suma móvil de 64

`docs/mediciones/protocolo_sma64.txt`. La versión con suma móvil de 64 precios (entra 4, sale 1) no reemplaza a la regla base:

| Conjunto | Suma móvil | Regla base | Condición |
|----------|------------|------------|-----------|
| Bloques: media y peor | 10 951 y 10 148 | 11 069 y 9 720 | a no cumple (la media es menor) |
| Remuestreos: media y percentil 5 | 10 624 y 8 275 | 10 772 y 8 914 | b no cumple |
| Familias sintéticas | Baja 1,5 % en `cambio_de_caracter` (8 907 contra 9 043) y gana en casi todas las demás | | c no cumple |

Es un resultado negativo útil: la suma móvil tiene mejor peor bloque y gana en varias familias sintéticas, pero pierde en lo que se parece a la serie de práctica. La comparación completa entre estimadores (media exponencial con otras constantes, suma móvil y filtro de Kalman de dos estados) está en `docs/algoritmo.md`, sección 5.2: la forma del estimador importa poco y lo que mueve el resultado son las bandas.

### Candidatos

El resultado de cada candidato bajo este protocolo está en `docs/mediciones/protocolo_*.txt` (`make protocolo-candidatos`) y se discute en `docs/algoritmo.md`, sección 7. Ninguno reemplaza formalmente a la regla base con las tres condiciones: los que suben la media bajan el peor bloque o alguna familia de estrés, y los que protegen bajan la media.

## 6. El binario contra la referencia

`make equiv-gemelo` (`python3 ref/protocolo.py --binario`) corre `sw/trade.hex` en el gemelo digital sobre las 3810 series, a 0,1 ms, 1 ms y 10 ms, y compara patrimonio, órdenes y pérdida máxima con la referencia:

- 22 860 000 ticks, cero diferencias;
- ningún precio sin respuesta ni perdido;
- peor caso de respuesta 48 ciclos (ver `docs/trade_s.md`, sección 6).

Con eso los números del protocolo, que se calculan con la referencia en Python, valen también para el programa que corre en la placa.

## 7. Uso

```bash
python3 ref/series.py listar                    # una serie de cada familia
python3 ref/series.py saltos --n 2000 --semilla 3 -o build/series/saltos_3.csv
python3 ref/protocolo.py                        # regla base
python3 ref/protocolo.py --estrategia sma64
python3 ref/protocolo.py --estrategia base:k=5,entra=3,sale=0
python3 ref/protocolo.py --comparar sma64       # candidato contra la base, con veredicto
python3 ref/protocolo.py --comparar cand:max_media        # un candidato de ref/candidatos.py
python3 ref/protocolo.py --estrategia trader:E=96,X=0,J=8 # la familia paramétrica con esos parámetros
python3 ref/protocolo.py --semilla 1                      # con la semilla reservada
python3 ref/protocolo.py --meseta
make protocolo                                  # deja todo en docs/mediciones/
make equiv-gemelo
make equiv-series                               # una serie de cada familia por el RTL
```

Una estrategia nueva es una clase con un método `decidir(precio)` que devuelve el byte de `DECISION`. La evaluación completa de una estrategia toma unos 5 segundos.

## 8. Preguntas que nos pueden hacer

**¿Cómo saben que no es sobreajuste?** No lo damos por descontado. Los parámetros de la regla base sí se eligieron mirando la serie de práctica, y por eso no informamos el 27 062 como lo esperado. Lo esperado es la media de los remuestreos, 10 772, con un vecindario de parámetros que rinde parecido.

**¿Qué pasa si la serie oculta es distinta?** Está en la tabla: en un paseo aleatorio queda en la caja inicial menos comisiones, y en una tendencia a la baja puede perder casi todo. Por eso la regla base no es el algoritmo final.

**¿Por qué remuestrear incrementos y no precios?** Remuestrear precios sueltos destruye la continuidad de la serie. Remuestrear incrementos en bloques conserva los movimientos locales, que es donde está la reversión.

**¿Por qué bloques de 100?** Porque la ganancia está en horizontes de 10 a 50 ticks, y el bloque tiene que contenerlos. Con bloques mucho más largos quedan muy pocos bloques distintos.

**¿Cuánto del resultado es suerte?** En los remuestreos el patrimonio final va de 6 520 a 15 637 con la misma regla. La diferencia entre la media (10 772) y la caja inicial es pequeña frente a esa dispersión: en una sola ronda la suerte pesa más que la regla. En tres rondas pesa menos, pero sigue pesando.
