# Guiones para presentar el diseño

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Dos guiones para decir en voz alta: uno de 1 minuto (si piden "cuéntennos qué hicieron") y uno de 5 minutos (si hay tiempo para presentar). Los dos están escritos para decirse, no para leerse: frases cortas, un número por idea. Cada número sale de `docs/defensa/cifras.md`. Si el 26/11 cambia el peldaño que compite o el 29/11 cambia el algoritmo, se ajustan las frases marcadas con (*).

## Guion de 1 minuto

> Hicimos un trader en el Pochoco SoC, sobre el Espino, en la Go Board. El algoritmo es una reversión a la media: compra 63 acciones cuando el precio cae 3 unidades bajo su media exponencial y vende cuando la recupera. Lo elegimos con un protocolo que separa la exploración de la confirmación, con una semilla reservada (*).
>
> En hardware construimos tres procesadores Espino que ejecutan la misma ISA: el base, uno segmentado y uno barrel de cuatro hilos, más una extensión propia en custom-0. Compite una escalera de tres bitstreams (*): R0, el Espino base, que es el respaldo; R1, el barrel con un fondo de cuatro hilos que vota la decisión; y R2, que agrega un vigilante que cambia a R0 si R1 deja de responder.
>
> Todo está verificado bit a bit contra la referencia en Python: más de 50 millones de instrucciones del barrel contra el Espino base, y las 4 144 770 combinaciones de estado y precio de la regla de R0 por el RTL. El peor caso del fondo es 444 ciclos de 2262 en la ronda 3.

## Guion de 5 minutos

Un bloque por persona, en el orden de la pauta. Cada uno dice su parte en unos 90 segundos y el siguiente retoma.

### Vicente: el algoritmo y el assembly (puntos 3.1 y 3.2)

> La serie de práctica revierte a la media: la razón de varianza baja de 1 a 0,53 a 100 ticks, y la autocorrelación de los cambios es -0,11 en el primer rezago. Por eso operamos reversión y no tendencia: de 336 reglas de tendencia, la mediana termina en 3 853 desde 10 000.
>
> La regla es `max_media` (*): media exponencial con alfa 1/32, entra 3 unidades bajo la media, sale al cruzarla. Siempre pide 63 acciones; la maestra recorta a lo que alcanza, así que repetir la orden no cuesta comisión y no necesitamos contabilidad propia.
>
> No la elegimos por su resultado en la serie completa, que es una sola trayectoria. Usamos 10 bloques, 1000 remuestreos y familias sintéticas de un modelo ajustado a la práctica, y confirmamos con una semilla que no se usó para elegir. La regla de Vicente, `zscore`, da 40 957 en la práctica; con ese criterio pierde, aunque con trozos de remuestreo largos gana: lo explicamos en `docs/zscore.md` (*).
>
> En assembly, `sw/trade.s` no tiene shifter: multiplica por 32 con cinco sumas y divide por 32 leyendo el segundo byte de una palabra. No tiene saltos que dependan del precio: el peor caso es el promedio. Responde en 41 ciclos en promedio y 44 en el peor caso, contra 2262 disponibles en la ronda 3.

### Nicolás: los procesadores y la verificación (punto 3.3 y verificación)

> El Espino base tiene CPI 2 porque el banco de registros es una BRAM con lectura registrada: cada instrucción espera un flanco por sus operandos. Atacamos el CPI de dos formas. El segmentado lee la memoria en el flanco de bajada y hace IF, ID y EX en dos ciclos: CPI 1,35 con `trade.s`. El barrel tiene cuatro hilos en un pipeline de cuatro etapas: cada BRAM cae justo en una frontera entre etapas, no hay riesgos ni adelantamiento, y por eso es el core más chico, 932 celdas.
>
> La extensión agrega dos instrucciones en custom-0: `devk` calcula el desvío `32 p - S` y `emad` el paso de la media, `S + (dev >>> 5)`, cada una en una instrucción en vez de cinco sumas. Ataca el IC, no el CPI.
>
> La verificación: cada core contra el Espino base instrucción por instrucción, más de 50 millones de instrucciones con la máscara exacta de R1; 21 de 21 mutaciones detectadas; propiedades formales de la estructura del barrel y de cada instrucción nueva; y la regla de R0 aplicada en sus 4 144 770 combinaciones de estado y precio, por el gemelo y por el RTL.

### Santiago: el fondo, el vigilante y el día de la competencia

> R1 corre `sw/fondo.s`: el hilo 0 es el supervisor, el único que toca el SPI; publica el precio con su número de tick en un solo store, y los hilos 1 a 3 corren la misma regla con umbrales distintos y votan. Un voto viejo se detecta restando el número de tick. Si un gestor no vota a tiempo, el supervisor usa su propia `max_media`: la decisión nunca depende de que otro hilo esté vivo. Responde en 223 ciclos en promedio y 444 en el peor caso.
>
> R2 agrega un vigilante: si llegan cinco precios sin escritura en DECISION, pide un warm boot a la imagen de R0. En la placa medimos el relevo: 35,5 ms, 361 ticks sin decisión nueva a 0,1 ms. Pasó media hora sin disparar.
>
> El día de la competencia seguimos un árbol de una página: medimos el SCLK real con un bitstream aparte y elegimos el peldaño. Si cambian la comisión, tenemos juegos de parámetros ya simulados que se cargan con `icebram` sin sintetizar.

### Cierre (cualquiera)

> Lo que aceptamos a sabiendas: el fondo no suma puntos esperados sobre `max_media` sola; lo elegimos por lo que representa como co-diseño, con R0 de respaldo probado. Todo número que dijimos sale de un comando del repositorio.

## Cómo se ensaya

- El 30/11, cada uno dice su bloque con cronómetro. Si pasa de 100 segundos, se saca una frase, no se habla más rápido.
- Después del guion de 5 minutos viene una pregunta del banco al azar (`docs/defensa/pruebas_practica.md`) para quien no habló de ese tema.
