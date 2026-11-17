# La regla `zscore` de Vicente bajo el protocolo

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio de la evaluación del 16 y 17/11 (rama `zscore`, decisiones T128 y T129, bitácora `docs/bitacora/zscore.md`). Todas las cifras salen de `docs/mediciones/zscore/` y se regeneran con `make zscore` (semilla 0) y `make zscore-reservada` (semilla 4, que se corrió una sola vez).

**Resultado en una línea.** `zscore` gana en la serie de práctica completa (40 957 contra 25 973) porque es la serie con que se eligieron sus parámetros. Fuera de ella pierde contra `max_media` en el protocolo, en los puntos esperados del torneo y en el duelo cabeza a cabeza, a 2000 y a 20 000 ticks, con la semilla de exploración y con la reservada. No reemplaza a `max_media`, y un fondo de gestores `zscore` tampoco.

## 1. La regla

Es una reversión a la media como `max_media`, con dos diferencias: la banda de entrada no es fija sino proporcional a la dispersión medida, y hay un calentamiento.

| | `max_media` | `zscore` |
|-|-------------|----------|
| Media | exponencial, alfa 1/32 (`S = 32 x media`) | exponencial, alfa 1/32 (`M = 32 x media`), redondeada |
| Dispersión | no hay | `D = 64 x` desviación absoluta media del desvío `32 p - M`, alfa 1/64 |
| Entra | precio 3 unidades bajo la media | precio más de 2,5 desviaciones bajo la media: `128 |dev| > 5 D` |
| Sale | precio sobre la media | precio sobre la media |
| Calentamiento | no | 64 precios después del primero, escribiendo mantener |
| Órdenes | comprar 63 o vender 63 | igual |

La referencia está en `ref/zscore.py` (con los parámetros abiertos: memorias `km` y `kd`, umbral `num/den`, calentamiento `w` y salida `sx2`) y en C, para el arnés del torneo, en `ref/zscore/zscore.c`.

## 2. Equivalencia

| Prueba | Resultado |
|--------|-----------|
| `ref/zscore.py` contra `agente_zscore` de `tools/referencia.py` del repositorio de Vicente (commit `3173a3d`) | Mismos bytes de `DECISION` en la práctica y en 80 series sintéticas |
| Serie de práctica completa | **40 957 con 578 órdenes**, la cifra de Vicente |
| `zscore.c` contra `ref/zscore.py` | 2 955 series, cinco juegos de parámetros, patrimonio y órdenes iguales |
| Fondo con gestores por nombre (`fondo_z.c`) contra el fondo de la factibilidad | 7 511 series iguales |
| Causalidad del arnés (ninguna estrategia mira el futuro) | Pasa |

`make zscore-validar` (`ref/zscore/validar.py`).

## 3. Cómo se evaluó

Con el mismo método con que se eligió `max_media` (T46 y T128), fijado antes de medir:

- **Exploración con la semilla 0**: protocolo de `ref/protocolo.py`, grilla de 81 puntos (umbral de 1 a 3 cada 0,25, memoria de la media de 16 a 64 ticks y de la desviación de 32 a 128), fondos de gestores `zscore` y duelo.
- **Semilla 4, reservada**: nadie la había usado. Los cuatro finalistas se escribieron en la bitácora antes de correrla y se corrió una sola vez.
- **Criterio de corte** del arnés: mejorar los puntos esperados del torneo en más de dos errores estándar sin bajar el percentil 5 de la competencia de tres rondas, en el conjunto `evidencia` (remuestreos y familias plausibles), campo mixto con 10 rivales, a 2000 y a 20 000 ticks. A 20 000 ticks cuentan las series interiores y la vista de parada confirma el signo.
- **Cabeza a cabeza**: probabilidad de terminar con más patrimonio que `max_media` en una ronda, y en una competencia de tres rondas (suma del patrimonio).

## 4. Resultados

### 4.1 Protocolo (2000 ticks)

| Conjunto | `zscore` | `max_media` | Diferencia | Gana en |
|----------|----------|-------------|------------|---------|
| 10 bloques de práctica | 11 389 (peor 9 859) | 11 043 (peor 9 620) | +346 +- 321 | 7 de 10 |
| 1000 remuestreos, semilla 0 | 10 747 | 10 857 | -110 +- 37 | 44 % |
| 1000 remuestreos, semilla 4 | 10 772 | 10 808 | -36 +- 30 | 48 % |
| Las cuatro familias plausibles, semilla 0 | | | -166 a -852 | 32 a 46 % |
| `tendencia` y `cambio_de_caracter`, semilla 0 | | | +327 y +463 | 57 % |
| `volatil`, `nivel_bajo` y `borde_bajo`, semilla 0 | | | -8 833, -5 923 y -23 485 | 0 a 40 % |

Cumple la condición de los bloques y no cumple las otras dos: **no reemplaza** a `max_media` (`protocolo_s0.txt`, `reservada_s4.txt`). La diferencia en los bloques es del tamaño de su error.

### 4.2 Torneo y duelo, semilla reservada

| | 2000 ticks | 20 000 ticks, interiores | 20 000 ticks, parada |
|-|------------|--------------------------|----------------------|
| H3a (lineal en patrimonio), diferencia | -0,094 +- 0,005 | -0,222 +- 0,006 | -0,167 +- 0,005 |
| H3b (lineal en el puesto), diferencia | -0,051 +- 0,005 | -0,085 +- 0,004 | -0,061 +- 0,004 |
| Percentil 5 de H3a en tres rondas | -0,080 +- 0,018 | -0,353 +- 0,024 | |
| Gana una ronda, remuestreos | 46,2 % | 37,6 % | |
| Gana una ronda, plausibles | 40,7 % | 25,6 % | |
| Gana la competencia (tres rondas), remuestreos | 46,0 % | 33,4 % | |
| Gana la competencia (tres rondas), plausibles | 34,8 % | 16,3 % | |

Veredicto del criterio de corte: **NO PASA** a los dos largos (`reservada_s4.txt`, `duelo_n2000_s4.txt`, `duelo_n20000_s4.txt`). En las rondas largas pierde más que en las cortas.

### 4.3 Meseta (punto b)

`meseta_n2000_s0.txt` y `meseta_n20000_s0_*.txt`. Diferencia de puntos H3a contra `max_media` en la evidencia:

| Umbral | 1,5 | 1,75 | 2,0 | 2,25 | 2,5 | 2,75 | 3,0 |
|--------|-----|------|-----|------|-----|------|-----|
| Memorias 32 y 64 (las de Vicente), 2000 ticks | -0,068 | -0,063 | -0,062 | -0,071 | **-0,095** | -0,128 | -0,162 |
| Memorias 32 y 128, 2000 ticks | **-0,058** | -0,060 | -0,071 | -0,080 | -0,096 | -0,115 | -0,143 |
| Memorias 32 y 128, 20 000 ticks, interiores | **-0,047** | -0,062 | -0,098 | -0,148 | -0,222 | -0,303 | -0,385 |

- **Ninguno de los 81 puntos le gana a `max_media`** en H3a, a ninguno de los dos largos.
- **El centro de la meseta está en z = 1,5 a 1,75 con la desviación de memoria 128**, no en 2,5. Sobre 2,5 la regla pierde cada vez más, que es lo que Nicolás vio en su prueba rápida.
- **La memoria de la media importa más que el umbral**: con 16 ticks (km = 4) pierde entre 0,12 y 0,25 puntos; con 64 (km = 6), entre 0,09 y 0,24. La de 32 es la mejor, igual que en `max_media`.

### 4.4 Fondo de tres gestores `zscore` (punto c)

`tabla_n2000_s0.txt` y `tabla_n2000_s4.txt`, `tabla_n20000_s4_*.txt`. Diferencia H3a en la evidencia a 2000 ticks, semilla 4:

| Candidata | dH3a | dH3b |
|-----------|------|------|
| Mejor `zscore` solo (z 1,5, memorias 32 y 128) | -0,055 +- 0,005 | -0,024 +- 0,005 |
| Fondo `zscore` 2,0/2,25/2,5, pesos aprendidos como en R1 | -0,072 +- 0,005 | -0,034 +- 0,005 |
| Fondo `zscore` 1,25/1,5/1,75, mayoría | -0,055 +- 0,005 | -0,024 +- 0,005 |
| Fondo `max_media` + `zscore` 2,0 + `zscore` 1,5, mayoría | -0,040 +- 0,004 | -0,012 +- 0,004 |

**Un fondo de tres bandas de la misma regla, con la misma salida, decide igual que su banda del medio.** Con umbrales anidados, si entra la banda más exigente entran las tres, y la mayoría de dos de tres se forma exactamente cuando entra la del medio; las tres salen juntas al cruzar la media. Por eso el fondo 1,25/1,5/1,75 da los mismos números que `zscore` 1,5 solo, y los pesos aprendidos casi no lo mueven. El fondo no puede ser mejor que la mejor de sus bandas, y ninguna de las bandas le gana a `max_media`. El fondo mixto pierde menos porque una de sus bandas es `max_media`, pero tampoco pasa (`reservada_s4.txt`).

## 5. Por qué gana 40 957 en la práctica

1. **Es la serie con que se eligieron sus parámetros.** En la grilla de 81 puntos sobre la serie de práctica completa, la regla de Vicente es el máximo (`practica.txt`). Sus vecinos inmediatos dan 22 421 (z = 2,75), 37 004 (z = 2,25), 32 873 (memoria de la media 16) y 23 152 (memoria 64). Una cima aislada en la serie de elección, que no se repite fuera de ella, es la firma del sobreajuste (`docs/protocolo.md`, sección 1). `max_media` también se eligió mirando la práctica, pero su vecindario es plano (`docs/protocolo.md`, meseta).
2. **Veinte mil ticks son una sola trayectoria con interés compuesto.** En los 10 bloques de 2000, la ventaja es +346 +- 321 por bloque: menos de dos errores. Compuesta diez veces sobre la misma trayectoria se convierte en 40 957 contra 25 973.
3. **Lo que gana en la práctica no aparece en series con la misma estadística.** En las familias plausibles, que salen del modelo ajustado a la práctica, gana el 41 % de las rondas de 2000 ticks y el 26 % de las de 20 000.

## 6. Bandas escaladas con la volatilidad: por qué se descartaron y qué tiene de distinto `zscore` (punto d)

El frente A probó en `ref/explorar.py volatilidad` (`docs/algoritmo.md`, sección 5.3) bandas de la forma `E = E0 + ev V / 4`, con `V` la media exponencial del valor absoluto del **cambio de precio de un tick al siguiente**: 368 combinaciones. La mejor dio 11 028 de promedio contra 11 029 de la mejor banda fija. Se descartó porque no agregaba nada: la banda fija de 3 a 4 unidades ya queda ancha en el régimen tranquilo y justa en el ruidoso.

`zscore` es otra cosa en tres puntos:

| | Bandas del frente A | `zscore` |
|-|---------------------|----------|
| Qué mide | El cambio de un tick al siguiente (`|p - p anterior|`) | El desvío del precio respecto de su media (`|32 p - M|`) |
| Forma de la banda | Un piso fijo más un término proporcional | Proporcional pura, sin piso |
| Arranque | Desde el primer precio | 64 precios sin operar |

La diferencia que importa es la primera. El cambio de un tick mide el ruido. El desvío respecto de la media mide el ruido **más** cuánto se aleja el nivel: cuando la serie entra en tendencia, el precio se separa de una media que lo sigue con retraso, `D` crece y la banda se ensancha sola. Por eso `zscore` protege en `tendencia` (+327 y +501 sobre `max_media` en las semillas 0 y 4) y en `cambio_de_caracter` (+463 y +831): funciona como una guardia de régimen sin pedirla. En la serie de práctica su banda de entrada va de 2,1 unidades (percentil 5) a 11,5 (percentil 95), con mediana 3,85: el 68 % del tiempo es más ancha que la de `max_media`.

Lo que paga por eso:

- **Opera menos en las series que más rinden.** La comisión es fija (5 por orden) y la ganancia de una reversión es proporcional al tamaño del movimiento. Una banda en unidades de precio entra cuando el movimiento esperado paga la comisión; una banda en desviaciones no mira la comisión. En `volatil`, `nivel_bajo` y `borde_bajo`, donde los mismos movimientos valen más frente a la comisión, `max_media` gana 8 800, 5 900 y 23 500 más.
- **Se ensancha también cuando no hay tendencia.** En los tramos ruidosos de una serie que revierte, `D` sube y la regla deja pasar las caídas que `max_media` sí aprovecha. Es el mismo diagnóstico del frente A con otra medida: ensanchar la banda con la volatilidad no mejora la media.
- **El umbral de 2,5 es demasiado alto.** Con la banda más ancha que la de `max_media` casi siempre, opera la mitad (31 órdenes por ronda contra 55). Bajando el umbral a 1,5 se recupera parte, pero no alcanza (sección 4.3).

## 7. Lo único que queda abierto

A 20 000 ticks y solo en las familias plausibles, la variante de la meseta (z = 1,5, memorias 32 y 128) sí le gana a `max_media` en el puesto: +0,050 +- 0,006 puntos H3b con las series interiores y +0,044 +- 0,005 con la vista de parada, y gana el 65 % de las rondas y el 74 % de las competencias. En patrimonio (H3a) empata (+0,006 +- 0,006). En los remuestreos del mismo largo pierde (-0,036 en H3b, gana el 44 % de las rondas), y a 2000 ticks pierde en todo.

No cambia el veredicto: el criterio se fijó sobre la evidencia completa antes de medir, y elegir después el subconjunto donde una variante gana es justamente lo que el protocolo evita. Pero es un dato que depende de dos respuestas del 26/11 (cuántos ticks dura cada ronda y si las series salen del mismo generador), y por eso queda anotado en `docs/pendientes_nicolas.md` con las opciones.

## 8. Qué cambiaría si se adoptara (punto e)

No aplica, porque no gana. Para la defensa, el costo estimado de cambiar el algoritmo de los tres peldaños: el programa de R0 (sin shifter, `>> 6` y el valor absoluto cuestan unas 15 instrucciones más; Vicente ya tiene una versión en assembly verificada en su RTL), los cuatro hilos de `sw/fondo.s` y la tabla de parámetros, la referencia `ref/fondo.py`, la equivalencia de los tres peldaños, las firmas de las tres autopruebas y las puertas de simulación de R0, R1 y R2. Unos 3 días para R0 y 4 a 5 más para R1 y R2. El hardware no cambia, así que entraría antes del congelamiento total del 29/11, pero no del 25/11 con R1 y R2 completos.

## 9. Cómo se reproduce

```bash
make zscore-validar        # equivalencia con la referencia de Vicente y entre C y Python
make zscore                # exploración con la semilla 0 (unos 6 minutos)
make zscore-reservada      # la semilla reservada (ya corrida: no repetir para elegir nada)
python3 ref/zscore.py tb/practica.csv            # 40 957 con 578 órdenes
python3 ref/zscore.py tb/practica.csv --num 3 --den 2 --kd 7
```

Las series de la semilla 4 no se versionan: `make zscore-series` las genera en `build/zscore/series/` con el generador del estudio de retorno.

## 10. Preguntas que nos pueden hacer

**El algoritmo de Vicente gana 40 957 y el de ustedes 25 973. ¿Por qué compiten con el peor?** Porque 40 957 es el resultado en la serie con que se eligieron sus parámetros. Su vecino a 2,75 desviaciones da 22 421. En series que no se usaron para elegir pierde: gana el 41 % de las rondas de 2000 ticks en las familias que imitan la práctica, y en el torneo pierde 0,09 puntos por ronda.

**¿Y si la serie oculta es la misma de práctica?** Entonces gana `zscore`. Pero el enunciado prohíbe guardar la serie en el diseño, y elegir los parámetros por su resultado en una serie que después se repite es lo mismo por otro camino.

**¿No es lo mismo con `max_media`?** También se eligió mirando la práctica, y por eso no informamos su 25 973 como lo esperado. La diferencia es que su vecindario es plano y que gana fuera de la práctica.

**¿Por qué un fondo de tres `zscore` no mejora?** Porque tres bandas anidadas de la misma regla con la misma salida votan igual que la del medio (sección 4.4).

**¿Qué aprendieron de `zscore`?** Que medir la dispersión del desvío respecto de la media, y no la del cambio de un tick, protege en tendencia sin una guardia aparte. Cuesta ganancia en series volátiles porque ignora la comisión fija.
