# Protocolo de evaluación de algoritmos

Documento de estudio de `ref/series.py` y `ref/protocolo.py`: con qué series se evalúa un algoritmo, qué se informa, cuándo una candidata reemplaza a la regla base y qué dio la regla base.

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

- **Qué conserva:** la dependencia entre ticks vecinos dentro de cada bloque. La reversión que explota la regla base ocurre en horizontes de 10 a 50 ticks, así que queda adentro. La razón de varianza promedio de los remuestreos es 0,75 a 10 ticks y 0,62 a 50, contra 0,73 y 0,57 de los bloques originales.
- **Qué pierde:** la relación entre bloques. El nivel de largo plazo de una serie remuestreada es un paseo aleatorio, sin la reversión lenta de la original (0,53 a 100 ticks).
- **Consecuencia:** para una regla de reversión es una prueba más dura que la serie original. Un algoritmo que gana aquí no depende de la trayectoria particular de la serie de práctica.

Se usan 1000 remuestreos.

### Familias sintéticas

Sirven para la pregunta "¿y si la serie oculta es distinta?". 200 series de cada una.

| Familia | Qué es | Para qué está |
|---------|--------|---------------|
| `paseo` | Paseo aleatorio. | No hay nada que predecir: cualquier ganancia es suerte y las comisiones restan. |
| `tendencia` | Paseo con deriva, hacia arriba o hacia abajo. | El peor escenario para una regla de reversión. |
| `reversion` | Reversión a una media fija. | El mejor escenario. |
| `dos_componentes` | Nivel lento más componente transitoria, y redondeo. | La forma del modelo que se quiere ajustar a la serie de práctica. Los parámetros todavía no están calibrados. |
| `saltos` | Reversión con saltos de nivel. | Un salto parece una caída grande y la regla entra. |
| `cambio_volatilidad` | Tramos de volatilidad baja y alta. | Los umbrales fijos quedan chicos o grandes. |
| `cambio_de_caracter` | Primera mitad con reversión, segunda con tendencia. | La serie cambia a mitad de ronda. |
| `plana` | Precio constante. | Cualquier orden ejecutada solo paga comisión. |
| `borde_bajo`, `borde_alto` | Series pegadas a 1 y a 255. | Aritmética en los extremos del rango. |

`python3 ref/series.py listar` muestra una serie de cada familia con su rango y su razón de varianza. Dos advertencias sobre estas familias:

- **El redondeo fabrica reversión.** Un paseo aleatorio redondeado a enteros tiene razón de varianza menor que 1 a horizontes cortos (0,87 a 10 ticks, en promedio sobre las 200 series de `paseo`), porque el error de redondeo de un tick se deshace en el siguiente. Es parte de lo que el frente del algoritmo tiene que separar en la serie de práctica.
- **Con precios bajos las medias engañan.** Con precio 3, un cambio de una unidad es un 33 %. En `borde_bajo` unas pocas series multiplican el patrimonio varias veces e inflan la media. Por eso la tabla trae también la mediana y el percentil 5.

## 3. Qué se informa

Para cada conjunto: media, mediana, percentil 5, peor caso, mejor caso, fracción de series en que supera a comprar y mantener, fracción en que termina sobre 10 000, y órdenes promedio. Comprar y mantener es la referencia del testbench: comprar todo en el primer tick y no vender.

En todas las corridas el programa ve todos los precios, que es la situación de la competencia (la placa está encendida antes del primer precio).

## 4. Criterio de aceptación

`python3 ref/protocolo.py --comparar CANDIDATA` evalúa la candidata y la base sobre las mismas series, y la candidata reemplaza a la base solo si cumple las tres condiciones:

| | Conjunto | Condición |
|-|----------|-----------|
| a | 10 bloques de práctica | Media y peor bloque mayores o iguales que los de la base. |
| b | 1000 remuestreos | Media y percentil 5 mayores o iguales. |
| c | Cada familia sintética | La media no baja más de 1 %. |

La condición a es el principio del proyecto: una pieza cambia la forma de operar solo si mejora la media y el peor bloque. La b pide lo mismo donde hay 1000 muestras en vez de 10, y usa el percentil 5 porque el peor de 1000 es demasiado ruidoso. La c evita aceptar algo que gana en la serie de práctica a costa de hundirse si la serie oculta es distinta.

Una candidata que no cumple se queda como experimento documentado, con su tabla.

### Meseta

`python3 ref/protocolo.py --meseta` evalúa la regla base con parámetros vecinos (k entre 4 y 6, umbral de entrada entre 2 y 6, umbral de salida entre 0 y 2). Un buen parámetro tiene vecinos que rinden parecido. Un máximo aislado es señal de sobreajuste.

## 5. Resultados de la regla base

Salida de `make protocolo` (`docs/mediciones/protocolo_base.txt`):

| Conjunto | n | Media | Mediana | Percentil 5 | Peor | Supera a comprar y mantener | Órdenes |
|----------|---|-------|---------|-------------|------|-----------------------------|---------|
| Práctica, 10 bloques | 10 | 11 069 | 11 103 | 9 720 | 9 720 | 90 % | 29,9 |
| Remuestreo | 1000 | 10 772 | 10 703 | 8 914 | 6 520 | 72 % | 30,2 |
| `paseo` | 200 | 9 873 | 9 947 | 7 126 | 2 918 | 42 % | 56,2 |
| `tendencia` | 200 | 9 543 | 10 015 | 4 530 | 969 | 46 % | 59,8 |
| `reversion` | 200 | 40 086 | 32 441 | 19 832 | 14 305 | 100 % | 290,8 |
| `dos_componentes` | 200 | 25 138 | 23 137 | 16 399 | 13 134 | 100 % | 193,8 |
| `saltos` | 200 | 37 679 | 29 912 | 15 827 | 7 761 | 99 % | 274,2 |
| `cambio_volatilidad` | 200 | 63 697 | 53 886 | 25 722 | 17 099 | 100 % | 293,6 |
| `cambio_de_caracter` | 200 | 13 225 | 13 800 | 3 507 | 389 | 76 % | 124,5 |
| `plana` | 200 | 10 000 | 10 000 | 10 000 | 10 000 | 100 % | 0,0 |
| `borde_bajo` | 200 | 18 496 | 16 854 | 10 046 | 8 851 | 70 % | 134,8 |
| `borde_alto` | 200 | 14 966 | 14 921 | 13 363 | 12 731 | 100 % | 53,5 |

Qué se lee de la tabla:

1. **La ganancia esperada por ronda es del orden de 8 % sobre la caja inicial.** En los remuestreos la media es 10 772, contra 9 583 de comprar y mantener sobre las mismas series. El 27 062 de la serie completa es ese rendimiento compuesto diez veces sobre una trayectoria favorable.
2. **En uno de cada cinco remuestreos termina bajo 10 000**, y el percentil 5 es 8 914. La regla base sola no asegura no perder.
3. **Sin reversión no gana.** En el paseo aleatorio la mediana es 9 947: queda en la caja inicial menos comisiones.
4. **En tendencia puede perderlo casi todo.** Peor caso 969 en `tendencia` y 389 en `cambio_de_caracter`. Es una tendencia a la baja: la regla compra porque el precio cayó bajo su media, el precio sigue cayendo, y no vende hasta que recupere la media, cosa que no ocurre. No hay tope de pérdida. Este es el caso que debe cubrir la guardia de régimen.
5. **En serie plana no opera.** Ni una orden en las 200 series.
6. **Donde hay reversión fuerte opera mucho más.** Casi 300 órdenes en 2000 ticks, contra 30 en la serie de práctica.

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
| Familias sintéticas | Gana o empata en todas | | c cumple |

Es un resultado negativo útil: la suma móvil gana en las familias sintéticas con reversión (entre 2 y 12 % más de media) y tiene mejor peor bloque, pero pierde en lo que se parece a la serie de práctica. Sugiere que la forma de la media importa menos que los umbrales y el control de pérdidas.

## 6. El binario contra la referencia

`make equiv-gemelo` (`python3 ref/protocolo.py --binario`) corre `sw/trade.hex` en el gemelo digital sobre las 3010 series, a 0,1 ms, 1 ms y 10 ms, y compara patrimonio, órdenes y pérdida máxima con la referencia:

- 18 060 000 ticks, cero diferencias;
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
python3 ref/protocolo.py --comparar sma64       # candidata contra la base, con veredicto
python3 ref/protocolo.py --comparar candidatas:MiClase   # una clase de ref/candidatas.py
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

**¿Cuánto del resultado es suerte?** En los remuestreos el patrimonio final va de 6 520 a 15 637 con la misma regla. La diferencia entre la media (10 772) y la caja inicial es chica frente a esa dispersión: en una sola ronda la suerte pesa más que la regla. En tres rondas pesa menos, pero sigue pesando.
