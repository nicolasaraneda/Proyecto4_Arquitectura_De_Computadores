# Estudio de retorno 4, parte C: aprendizaje en vivo

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Tramo de factibilidad del Proyecto 4. Esta carpeta no agrega hardware ni cambia el programa de la placa: son estrategias en C para el arnés de retorno (`../README.md`), dos herramientas de medición y sus resultados. Todo se exploró con la semilla 0. Las semillas reservadas no se usaron.

## 1. Qué se preguntó y qué salió

La idea a evaluar: que el programa aprenda de la serie en curso. Una tabla de política en las BRAM libres, que parte de la regla validada y se ajusta con sumas y desplazamientos, y un predictor de patrones como los predictores de saltos.

Respuesta corta:

1. **Ninguna variante que aprende mejora a `max_media`.** Se probaron 249 variantes, 229 de ellas con aprendizaje. De esas 229, a 2000 ticks ninguna pasa la lectura rápida del criterio: 192 empeoran los puntos esperados y 37 quedan iguales, casi todas porque con prior fuerte no alcanzan a cambiar ninguna decisión. A 20 000 ticks, de 39 preseleccionadas, tampoco pasa ninguna. El resultado empeora de forma monótona con la tasa de aprendizaje y tiende a cero cuando el aprendizaje se apaga. No hay un punto intermedio que gane.
2. **El predictor de patrones no predice.** En las familias plausibles, para el primer cambio que se puede aprovechar (h = 1), las 20 configuraciones aciertan entre 49,7 y 50,3 % del signo, contra 51,4 % de la referencia sin aprendizaje ("sube si el precio está bajo la media"). A 16 ticks, entre 48,2 y 51,0 % contra 53,5 %. Operando solo pierde entre 1 164 y 3 693 de patrimonio por ronda.
3. **El remuestreo de 20 000 ticks engaña a cualquier tabla con historia larga.** Repite tramos de la misma serie, y un predictor con 12 bits de historia los memoriza: 55,7 % ahí contra 50,7 % en la serie de práctica real y 50,0 % en las plausibles.
4. **Había algo para ganar y el aprendizaje no lo alcanza.** Un oráculo que conociera el grupo de la serie y eligiera la mejor regla fija sacaría +0,04 puntos (H3a) y +0,06 (H3b) a 2000 ticks. La información de una ronda no alcanza para saber en qué grupo se está.
5. **Subproducto: la regla fija `espera`** (no comprar en el mismo tick en que el precio baja). Pasa el criterio a 2000 ticks y no a 20 000, y gana en el remuestreo mientras pierde en las plausibles y en el estrés. No es aprendizaje y no pasa el criterio global.
6. **Hallazgo de implementación:** la forma directa `T += (obj - T) >> k` redondea siempre hacia abajo y con k grande arrastra la tabla. Costó 4 646 de patrimonio a 20 000 ticks con una tasa que debía ser inocua. Hay que guardar el acumulador.
7. **Como cuarto gestor del fondo tampoco aporta.** Las estrategias de este estudio se probaron dentro del fondo de `../r4b_fondo` en 8 configuraciones y ninguna pasa. La mejor, el voto de 3 de 4 con `espera`, queda en -0,000 ± 0,002 con H3a y +0,008 ± 0,003 con H3b a 2000 ticks, otra vez con signo opuesto en remuestreo y plausibles.

Veredicto: descartado de la edición de competencia. Queda como material de exhibición y de defensa.

## 2. Qué se construyó

| Archivo | Qué es |
|---------|--------|
| `e_tabla.c` | Estrategia `tabla`: tabla de política que parte de `max_media`. Estimación de retorno o contador saturado, tercer índice opcional, ajuste de bandas, y la regla fija de espera. |
| `pred.h` | El predictor de patrones: historia sola, gshare, solo desviación y torneo con selector. Lo comparten las estrategias y el medidor. |
| `e_patron.c` | Estrategias `patron` (el predictor solo) y `mm_patron` (`max_media` con el predictor como filtro). |
| `aprendiz.c` | Nombres estables de las estrategias entregadas (sección 9). |
| `r4c.mk` | Fuentes de esta carpeta, para que otro estudio las compile contra el núcleo. |
| `exactitud.c` | Mide la exactitud del predictor por familia de series, fuera del arnés. |
| `cota.c` | Oráculos: cuánto se podía ganar como máximo. Lleva su propia contabilidad. |
| `equivalencia.sh` | Con el aprendizaje apagado, la tabla y el filtro contra `max_media`, serie por serie y tick a tick. |
| `barrer.py` | Barrido de variantes con el comando `hipotesis` del arnés. Las listas están fijas en el archivo. |
| `resumir.py` | Resumen del barrido por etapa: rangos, conteo de juicios y signo por evidencia. No evalúa: lee las tablas de `barrer.py`. |
| `finales.py` | Veredicto con `--parada`, las 9 combinaciones de campo y G, e hipótesis de las candidatas finales. |
| `tamanos.py` | Memoria que pide cada variante (celdas, bits, palabras) contra las 4 BRAM libres y la RAM de datos. |
| `cuarto.py` | Las estrategias de esta carpeta como cuarto gestor del fondo del estudio `../r4b_fondo`, cuyo `fondo.c` se compila sin modificar. |

### La tabla de política

- **Estado.** La desviación de la regla (`dev = 32 p - S`, la misma media exponencial) cuantizada en casillas de `2^sh / 32` de precio, y la posición. La posición corre la cuantización en 1/32 de precio (`(dev - pos) >> sh`), y con eso los dos umbrales de la regla (`dev < -96` y `dev > 0`) caen justo en un borde de casilla. Con `filas=2` la posición además elige una fila propia.
- **Tercer índice** (`ter`): signo del último cambio en tres valores (1) o dos (3), o régimen de volatilidad (2).
- **Contenido.** Modo 0: estimación del retorno a `h` ticks contado desde el tick de ejecución, `R = p[t+1+h] - p[t+1]`. Modo 1: contador saturado de `bits` bits que sube si `R > g` y baja si `R < -g`.
- **Valor inicial.** El que implica la regla. En modo 0 es una recta `-c * (centro de la casilla)` con umbral de compra `c * E` y de venta `c * X`: la recta cruza el umbral en el borde de la regla. En modo 1, contador en el máximo en las casillas de compra, en cero en las de venta y en la mitad en el resto.
- **Ajuste.** Cuando el resultado ya se conoce (`h + 1` ticks después), `T[s] += (R - T[s]) >> ka`. Un anillo guarda el índice y el precio de los últimos ticks. `ka` grande es prior fuerte y `ka = 0` apaga el aprendizaje.
- **Ajuste de bandas** (`banda=1`): la tabla no decide casilla por casilla. Solo corre los dos bordes de la banda, a lo más `lim` casillas, cuando la casilla vecina cruza el umbral con margen `mg`.

### El predictor de patrones

Predice el signo de `R = p[t+1+h] - p[t+1]`. Con `h = 1` es el primer cambio que se puede aprovechar: el cambio inmediato ya pasó cuando la orden se ejecuta. Usa un registro de desplazamiento con los últimos `H` cambios (un bit por cambio, o dos en la versión ternaria) que indexa contadores saturados de 2 o 3 bits. El contador se entrena cuando el resultado se conoce.

## 3. Cómo se reproduce cada número

Desde esta carpeta, con las series del arnés ya generadas (`make -C .. series`) y sus resultados guardados (`make -C .. exploracion`).

| Comando | Qué hace | Salida en `mediciones/` | Tiempo medido |
|---------|----------|-------------------------|---------------|
| `make` | Compila `build/arnes`. | | segundos |
| `make equivalencia` | 18 estructuras con el aprendizaje apagado contra `max_media`, y dos controles negativos. | `equivalencia.txt` | 57 s |
| `make causal` | Ninguna estrategia nueva mira el futuro. | `causal.txt` | segundos |
| `make exactitud` | Exactitud del predictor, 60 variantes, 13 familias, dos largos. | `exactitud_s0_n2000.txt`, `exactitud_s0_n20000.txt` | no se midió por separado con 5 hilos |
| `make cota` | Oráculos. | `cota_s0_n2000.txt`, `cota_s0_n20000.txt` | no se midió por separado con 5 hilos |
| `make barrido` | Barrido completo y su resumen por etapa. | `barrido_*.txt`, `barrido_cuenta.txt`, `barrido_resumen.txt` | 8 min 33 s, medido antes de agregar la etapa `tabla_umbral` |
| `make finales` | Candidatas finales. | `veredicto_*_s0.txt`, `veredictos_9_s0.txt`, `hipotesis_s0_*.txt`, `finales_s0.md` | 4 min 9 s |
| `make tamanos` | Memoria que pide cada variante. | `tamanos.txt` | menos de 1 s |
| `make cuarto` | Las estrategias de esta carpeta como cuarto gestor del fondo. Necesita `../r4b_fondo/fondo.c`, que compila sin modificar hacia `build/arnes_fondo`. | `cuarto_gestor_n2000.txt`, `cuarto_gestor_n20000_parada.txt` | 2 min 43 s |
| `make todo` | Todo, en orden. | | 22 min 53 s como un solo comando, con la máquina compartida con otros estudios |

`HILOS` vale 5 por defecto y limita también a `exactitud` y `cota`, que usan OpenMP por su cuenta (el Makefile les pasa `OMP_NUM_THREADS`).

**Reproducibilidad.** `make todo` se corrió como un solo comando con los fuentes finales (salvo lo que se indica en la sección 16). Las 30 salidas que ya existían de las corridas por separado salieron idénticas byte a byte, menos `equivalencia.txt` y `barrido_cuenta.txt`, que cambian solo por lo que se les agregó (dos estructuras y el conteo de juicios). `exactitud` y `cota` dan lo mismo con 24 hilos y con 5.

## 4. La tabla con el aprendizaje apagado es `max_media`

`mediciones/equivalencia.txt`. Cada estructura lleva por dentro a `max_media` y cuenta los ticks en que el byte de decisión es distinto.

- 18 estructuras (15 de la tabla y 3 del filtro), 32 lotes de la semilla 0 contando los bloques y la serie completa: 33 561 series y 264 240 000 ticks cada una.
- **604 098 corridas de series, 0 con resultado distinto y 0 ticks con decisión distinta.**
- Entre las 15 de la tabla están las dos con el umbral de acción corrido (`ui=48,uo=-48` y `ui=-48,uo=48`): mientras el corrimiento sea menor que media casilla (64), la tabla sigue partiendo como `max_media`. Con `ui=80` deja de serlo: 584 162 ticks distintos en el remuestreo, que es el segundo control negativo.
- `decisiones.csv` en la serie de práctica completa: idéntico byte a byte, 25 973 con 624 órdenes.
- Control negativo: con `ka=8` el mismo contador ve 1 075 465 ticks distintos en el remuestreo.

En `finales_s0.md` las filas `tabla:ka=0` y `mm_patron:apr=0` dan cero en todas las columnas de las tres vistas.

## 5. Cuánto se podía ganar: cotas

`mediciones/cota_s0_n2000.txt` y `cota_s0_n20000.txt`. La herramienta lleva su propia contabilidad y su `max_media` coincide con el arnés (10 868,4 en el remuestreo y 10 643,6 en `modelo`, iguales al comando `resumen`).

Patrimonio, diferencia contra `max_media`, conjunto evidencia:

| Oráculo | 2000 ticks | 20 000 ticks, vista de parada, 1000 series por familia |
|---------|------------|----------------------------|
| O1: la mejor banda fija de cada familia, entre 48 | +170 ± 16 | +3 024 ± 156 |
| O2: tabla de retorno de la familia, fija, con los mejores umbrales | +204 ± 28 | +3 394 ± 171 |
| O2 con el signo del último cambio | +311 ± 28 | +4 786 ± 186 |
| O3: la mejor de 3 bandas para cada serie, elegida después | +567 ± 8 | +3 472 ± 93 |
| O3 entre las 48 bandas | +1 540 ± 18 | +9 757 ± 193 |

O1 y O2 son lo que lograría un aprendizaje que identifica la familia al instante. O3 es una cota floja: elegir después el máximo de resultados con ruido infla la cifra.

De dónde sale lo de O1 y O2 (2000 ticks):

| Familia | Mejor banda | O1 | O2 | O2 con signo |
|---------|-------------|----|----|--------------|
| `remuestreo` | E=96, X=0 (`max_media`) | 0 | +35 ± 7 | +241 ± 11 |
| `modelo` | E=48, X=48 | +281 ± 28 | +266 ± 30 | +272 ± 28 |
| `modelo_vecino` | E=32, X=48 | +501 ± 113 | +595 ± 209 | +595 ± 209 |
| `dos_componentes` | E=48, X=48 | +281 ± 29 | +313 ± 34 | +313 ± 34 |
| `cambio_volatilidad` | E=48, X=48 | +299 ± 48 | +319 ± 45 | +343 ± 49 |

Las dos evidencias piden cosas opuestas. Las familias del modelo quieren bandas más angostas. El remuestreo quiere la banda de `max_media` y además esperar después de una baja. Lo único que un aprendizaje podría ganar es reconocer en cuál de los dos casos está.

**Cota en puntos** (2000 ticks, `barrido_cota_bandas_n2000.txt` y `barrido_espera_n2000.txt`): un oráculo que sabe si la serie es del remuestreo o de las plausibles y juega la mejor regla fija de cada grupo.

| | Mejor en remuestreo | Mejor en plausibles | Oráculo (mitad y mitad) |
|-|---------------------|---------------------|-------------------------|
| H3a | +0,046 (`tabla:ter=1,ezb=96,ezs=-32`) | +0,030 (`param:E=80,X=32`) | +0,038 |
| H3b | +0,068 (la misma) | +0,059 (`param:E=64,X=32`) | +0,064 |

Las reglas del oráculo se eligieron con las mismas series en que se miden, entre 29.

## 6. El predictor de patrones

### 6.1 Exactitud

`mediciones/exactitud_s0_n2000.txt`, 1000 series por familia. Porcentaje de aciertos del signo de `R` sobre los ticks con `R` distinto de cero. `rev` es la referencia sin aprendizaje.

| Predictor | Bits | h | Remuestreo: rev, pred | Plausibles: rev, pred | Ventaja sobre rev en plausibles |
|-----------|------|---|-----------------------|-----------------------|---------------------------------|
| Historia H=8, 2 bits | 512 | 1 | 51,59, 50,89 | 51,41, 50,01 | -1,41 ± 0,03 |
| Historia H=12, 2 bits | 8 192 | 1 | 51,59, 51,87 | 51,41, 50,04 | -1,38 ± 0,03 |
| gshare H=12, 2 bits | 8 192 | 1 | 51,59, 51,37 | 51,41, 50,12 | -1,30 ± 0,03 |
| Torneo H=8, 2 bits | 1 056 | 1 | 51,59, 50,44 | 51,41, 50,05 | -1,36 ± 0,03 |
| Solo desviación, 16 casillas, 6 bits | 96 | 16 | 54,15, 51,29 | 53,54, 50,98 | -2,56 ± 0,06 |
| Historia H=12, 2 bits | 8 192 | 16 | 54,15, 50,48 | 53,54, 50,07 | -3,48 ± 0,06 |
| Torneo H=12, 2 bits | 16 416 | 16 | 54,15, 51,04 | 53,54, 50,42 | -3,12 ± 0,07 |

- La tasa base es 50,2 %.
- **En las plausibles ningún predictor de los 60 supera a la referencia**, en ningún horizonte.
- Lo que se ganaría por acción: después de una predicción saturada de subida menos después de una saturada de baja, el mejor predictor de historia da +0,02 de precio a 16 ticks en las plausibles. La regla `max_media` da +0,80 entre su zona de compra y su zona de venta. Una ida y vuelta paga 0,13 por acción en comisiones.
- Un contador de 2 bits sirve cuando el evento se repite 9 de cada 10 veces. Aquí es 51 contra 49, y el contador hace un paseo aleatorio.

### 6.2 El remuestreo de 20 000 ticks se deja memorizar

`mediciones/exactitud_s0_n20000.txt`, 200 series por familia, h = 1:

| Predictor | Serie de práctica (una serie) | Remuestreo | Plausibles |
|-----------|-------------------------------|------------|------------|
| Referencia rev | 51,82 | 51,61 | 51,49 |
| Historia H=8, 2 bits | 49,74 | 51,53 | 49,96 |
| Historia H=12, 2 bits | 50,72 | 55,70 | 50,04 |
| Ternaria H=6, 2 bits | 50,49 | 54,00 | 50,09 |
| gshare H=12, 2 bits | 50,26 | 53,33 | 50,08 |

Un remuestreo de 20 000 ticks son 200 tramos de 100 incrementos sacados con reposición de los mismos 19 999. Los tramos se repiten dentro de la serie y una tabla con historia larga los reconoce. En la serie de práctica real, donde nada se repite, el mismo predictor queda en 50,7 %. **Cualquier estrategia con tablas indexadas por historia sale favorecida en el remuestreo largo sin mérito.** Se ve en `mm_patron` con H=12: +230 ± 18 de patrimonio en el remuestreo de 20 000 ticks y -149 ± 20 en las plausibles. A 2000 ticks el efecto es chico pero existe (51,87 contra 50,04).

### 6.3 Como estrategia

Como no hay ventaja en la exactitud, no correspondía convertirlo. Se midió igual, para dejarlo cerrado (`barrido_patron_n2000.txt`, `barrido_filtro_n2000.txt`).

- **Solo** (24 variantes): entre -1 164 ± 29 y -3 693 ± 34 de patrimonio, y entre -0,47 y -1,35 puntos.
- **Como filtro de `max_media`** (39 variantes): patrimonio entre -39 y +2. Ninguna mejora los puntos: la mejor queda en -0,000 ± 0,000.

## 7. La tabla de política

Diferencias contra `max_media` en el conjunto evidencia, campo mixto, G = 10. `max_media` saca 10 982 de patrimonio, 1,503 con H3a y 1,473 con H3b a 2000 ticks.

### 7.1 Tasa de aprendizaje y horizonte (2000 ticks)

`barrido_tabla_ka_h_n2000.txt`. Patrimonio y puntos H3a.

| ka | h = 4 | h = 8 | h = 16 | h = 32 |
|----|-------|-------|--------|--------|
| 6 | -444 ± 16, -0,190 | -746 ± 22, -0,351 | -1 061 ± 21, -0,498 | -1 229 ± 24, -0,565 |
| 8 | -107 ± 11, -0,053 | -158 ± 12, -0,077 | -281 ± 16, -0,138 | -474 ± 18, -0,236 |
| 10 | -9 ± 4, -0,003 | -25 ± 6, -0,015 | -53 ± 8, -0,030 | -102 ± 10, -0,056 |
| 12 | 0 | 0 | -2 ± 1, -0,000 | -18 ± 4, -0,006 |
| 14 | 0 | 0 | 0 | 0 |

**Es una relación de dosis y respuesta: mientras más aprende, más pierde.** Con ka = 14 la tabla no alcanza a cambiar ninguna decisión en 2000 ticks. El signo es el mismo en el remuestreo y en las plausibles en todas las celdas.

La razón es de ruido. El retorno a 16 ticks tiene una desviación cercana a 4 unidades de precio y la señal que separa una casilla de compra de su vecina es de 0,1 a 0,3. Con ka = 8 el ruido de la estimación es mayor que esa señal y las casillas del borde cambian de lado al azar: 82 órdenes por ronda contra 55.

### 7.2 Lo demás del barrido (2000 ticks)

Diferencia de patrimonio contra `max_media` en evidencia, de la peor variante a la mejor (`mediciones/barrido_resumen.txt`). En ninguna etapa hay una variante que aprenda y mejore H3a y H3b en más de dos errores.

| Etapa | Variantes | Resultado |
|-------|-----------|-----------|
| Pendiente del valor inicial `c` de 8 a 128 (`tabla_c`) | 15 | De -1 194 a 0. Con `c` chico el prior es débil y pierde más. |
| Umbral de acción corrido en 48/1024 de precio, en la compra, en la venta o en los dos (`tabla_umbral`) | 18 | De -384 a +2 ± 3. Las 18 empeoran los puntos (H3a de -0,187 a -0,004). Con el umbral corrido, una casilla del borde queda a 16/1024 de cambiar de lado en vez de a 64/1024, y hasta ka = 12 se aparta de la regla dentro de una ronda: -0,004 a -0,023 con H3a. Exigir más para comprar (`ui=48`) pierde lo mismo que exigir menos. |
| Forma: 8 a 64 casillas, filas por posición, tercer índice (`tabla_forma`) | 26 | De -195 a +1 ± 1. Ninguna mejora. |
| Contador saturado de 3 a 10 bits (`tabla_contador`) | 29 | De -2 115 a 0. Con 3 o 4 bits hace 230 a 317 órdenes por ronda. |
| Ajuste de bandas (`tabla_banda`) | 41 | De -297 a +1. |
| Tabla con el signo del último cambio, partiendo de `max_media` (`signo`) | 6 | De -255 a 0. No descubre la regla de espera. |

Tamaños probados: de 8 a 192 celdas (32 casillas, 3 valores del tercer índice y 2 filas). El prototipo admite hasta 384 (64 casillas), que no se barrió. En bits, de 96 a 5 376, o sea de 0,6 a 32,8 % de los 16 384 bits de las 4 BRAM libres (`mediciones/tamanos.txt`).

### 7.3 Rondas de 20 000 ticks

`barrido_largas_n20000_parada.txt` (vista de parada) y `barrido_largas_n20000_interiores.txt`. Patrimonio, H3a y H3b en evidencia, vista de parada:

| Variante | Patrimonio | H3a | H3b |
|----------|------------|-----|-----|
| `tabla:ka=10,h=16` | -1 229 ± 81 | -0,084 ± 0,003 | -0,032 ± 0,003 |
| `tabla:ka=12,h=16` (`aprendiz`) | -135 ± 34 | -0,016 ± 0,001 | -0,002 ± 0,001 |
| `tabla:ka=14,h=16` | 0 | 0 | 0 |
| `tabla:ka=12,h=32` | -293 ± 50 | -0,034 ± 0,002 | -0,007 ± 0,002 |
| `tabla:banda=1,ka=10,h=16,lim=1` | -977 ± 67 | -0,066 ± 0,003 | -0,024 ± 0,003 |
| `tabla:banda=1,ka=12,h=16,lim=1` | -133 ± 34 | -0,015 ± 0,001 | -0,001 ± 0,001 |
| `tabla:modo=1,bits=10,h=16` | -82 ± 13 | -0,010 ± 0,001 | -0,008 ± 0,001 |
| `tabla:modo=1,bits=8,h=16` | -2 331 ± 117 | -0,241 ± 0,005 | -0,132 ± 0,004 |
| `tabla:ter=3,ka=12,h=8` | -10 ± 14 | -0,004 ± 0,001 | +0,000 ± 0,001 |

Diez veces más ticks no cambian el resultado: la misma relación, corrida dos pasos de `ka`. En las 42 variantes de la preselección ninguna que aprende mejora H3a.

### 7.4 Lo único que el aprendizaje sí hace: proteger en el estrés

En el conjunto de estrés la tabla gana puntos, porque deja de comprar donde la reversión no existe:

| Variante | 2000 ticks: evidencia H3a, H3b | 2000: estrés H3a, H3b | 20 000 parada: evidencia | 20 000 parada: estrés |
|----------|-------------------------------|-----------------------|--------------------------|------------------------|
| `aprendiz` (ka=12) | -0,000, +0,000 | +0,003 ± 0,001, +0,003 ± 0,001 | -0,016, -0,002 | +0,039 ± 0,003, +0,042 ± 0,003 |
| `aprendiz_rapido` (ka=10) | -0,030, -0,020 | +0,018 ± 0,003, +0,030 ± 0,003 | -0,084, -0,032 | +0,076 ± 0,007, +0,083 ± 0,006 |

Es el mismo intercambio de la guardia de régimen, a mejor precio: `guardia` cuesta 0,065 puntos en evidencia a 2000 ticks. Con el criterio de corte, que mira la evidencia, no pasa. Si la serie oculta fuera de estrés con probabilidad mayor que 29 % (H3a) o 5 % (H3b), `aprendiz` convendría en rondas de 20 000 ticks (estimado con las cifras de la tabla). En rondas de 2000 ticks no hace nada.

### 7.5 Sesgo de redondeo

`barrido_redondeo_n2000.txt` y `barrido_redondeo_n20000_parada.txt`. `dir=1` es la forma directa, con la estimación en la tabla. Por defecto se guarda el acumulador `A = T * 2^ka` y se actualiza `A += R - (A >> ka)`.

| Variante | 2000 ticks | 20 000 ticks, parada |
|----------|------------|----------------------|
| `tabla:ka=14,h=16` | 0 | 0 |
| `tabla:ka=14,h=16,dir=1` | -107 ± 7 | -4 646 ± 123 |
| `tabla:ka=16,h=16,dir=1` | -106 ± 7 | -4 645 ± 123 |

El desplazamiento aritmético redondea hacia menos infinito. Una diferencia positiva chica suma 0 y una negativa chica resta 1, así que cada actualización empuja la casilla hacia abajo aunque no haya nada que aprender. Con ka = 14, que no debía hacer nada, cuesta 0,243 puntos de H3a a 20 000 ticks. La primera versión de este estudio tenía ese defecto y se detectó porque ka = 14 no daba cero. Todas las cifras de este documento son con el acumulador.

## 8. La regla fija `espera`

Salió del oráculo O2 con signo. `max_media` casi siempre compra en un tick en que el precio acaba de bajar, porque la desviación solo cruza el umbral hacia abajo en una baja. `espera` (`tabla:ter=1,ezb=64,ezs=-32`) no compra en ese tick salvo que la desviación pase de 5 unidades, y mantiene la compra pendiente si el precio rebota una unidad. No aprende nada: es otra regla fija, con dos constantes más.

`mediciones/veredicto_espera_s0.txt` y `finales_s0.md`:

| | 2000 ticks | 20 000 ticks, interiores | 20 000 ticks, parada |
|-|------------|--------------------------|----------------------|
| H1, evidencia | +37 ± 7 | +215 ± 82 | +380 ± 49 |
| H2 (razón W/B&H), evidencia | +0,008 ± 0,005 | +0,059 ± 0,012 | +0,237 ± 0,015 |
| H3a, evidencia | +0,005 ± 0,002 | -0,021 ± 0,002 | -0,000 ± 0,002 |
| H3b, evidencia | +0,017 ± 0,003 | +0,009 ± 0,002 | +0,025 ± 0,002 |
| p5 de tres rondas, H3a y H3b | +0,019 ± 0,013, -0,006 ± 0,026 | -0,016 ± 0,018, -0,056 ± 0,027 | +0,020 ± 0,013, +0,028 ± 0,028 |
| H3a: remuestreo, plausibles | +0,042, -0,033 | +0,029, -0,067 | +0,050, -0,050 |
| H3b: remuestreo, plausibles | +0,062, -0,026 | +0,064, -0,039 | +0,081, -0,029 |
| H3a y H3b, estrés | -0,020 ± 0,002, -0,014 ± 0,003 | -0,110 ± 0,007, -0,045 ± 0,007 | -0,027 ± 0,004, -0,005 ± 0,004 |
| Veredicto | PASA | NO_PASA | (informativa) |

- **Veredicto global: NO_PASA.** A 20 000 ticks empeora H3a y baja el percentil 5 de H3b. La fila de parada no confirma una mejora de H3a. El veredicto literal también es "no pasa".
- En las 9 combinaciones de campo y G pasa a 2000 ticks en 5 y a 20 000 en ninguna (`veredictos_9_s0.txt`).
- **El signo no se repite entre las dos evidencias.** Gana en el remuestreo y pierde en las plausibles y en el estrés, en las 12 variantes de la meseta (`barrido_espera_n2000.txt`). Es el caso inverso de `activo`. Su ventaja depende de que la serie oculta se parezca a la de práctica en un detalle que el modelo ajustado no tiene.
- La tabla que aprende, partiendo de `max_media` con el signo como tercer índice, no la descubre. Partiendo de `espera`, aprender la empeora (`barrido_signo_n2000.txt`).

## 9. Candidatas finales y módulo para el fondo

Alias registrados por `aprendiz.c`. Se usan incluyendo `r4c.mk` (el archivo explica cómo) y con `instancia_crear("cand:aprendiz", ...)`.

| Nombre | Especificación | Veredicto, semilla 0 (2000, 20 000, global) | Instrucciones por tick (estimado) |
|--------|----------------|---------------------------------------------|-----------------------------------|
| `espera` | `tabla:ter=1,ezb=64,ezs=-32` | PASA, NO_PASA, **NO_PASA** | 34 |
| `aprendiz` | `tabla:ka=12,h=16` | NO_PASA, NO_PASA, **NO_PASA** | 70 |
| `aprendiz_patron` | `mm_patron:tipo=1,H=12,sim=2,bits=2,h=1,fe=2,fs=0,maxp=4` | NO_PASA, NO_PASA, **NO_PASA** | 72 |
| `aprendiz_rapido` (informativa) | `tabla:ka=10,h=16` | NO_PASA, NO_PASA, **NO_PASA** | 70 |
| `aprendiz_puro` (informativa) | `patron:tipo=1,H=12,sim=2,bits=3,h=1` | NO_PASA, NO_PASA, **NO_PASA** | 55 |

Las tres primeras son la lista corta para el estudio de cierre. Las tablas completas en los dos largos, con H1, H2, H3a y H3b en evidencia, remuestreo, plausibles y estrés, están en `mediciones/finales_s0.md`.

Para el fondo de estrategias:

- **`espera` es el gestor que más aporta como cuarto en papel.** Es el único que le gana a `max_media` por un margen claro en uno de los dos grupos de evidencia (+158 ± 8 de patrimonio en el remuestreo a 2000 ticks), y lo hace donde `activo` pierde.
- `aprendiz` decide igual que `max_media` en rondas de 2000 ticks. Como gestor en papel solo se distingue en rondas largas.
- `aprendiz_rapido` es el que se aparta de la regla dentro de una ronda corta. Pierde en evidencia y gana en estrés.
- **Aviso:** a 20 000 ticks, `aprendiz_patron` y cualquier gestor con historia larga salen favorecidos en el remuestreo por la repetición de tramos (sección 6.2). Hay que mirar las plausibles.

Los alias cambiaron durante el estudio. Quien haya compilado antes de la versión final tiene en `aprendiz` otra especificación (`tabla:ka=10,h=16,c=32,banda=1,lim=1`).

### 9.1 Como cuarto gestor del fondo

`make cuarto` (`mediciones/cuarto_gestor_n2000.txt` y `cuarto_gestor_n20000_parada.txt`). El estudio del fondo dejó el cuarto gestor probado solo como mecanismo (parámetro `x` de su estrategia `fondo`) y no usó estas estrategias. Aquí se compila su `fondo.c`, sin tocarlo, junto con `r4c.mk`, y se mide una lista corta fijada antes de mirar resultados: su fondo recomendado (`max_media`, `kalman` y `activo`, banda de 4/16) con pesos 6/3/3/4, el voto entre `max_media`, `base`, `activo` y el cuarto gestor, y el fondo mínimo con pesos aprendidos.

Controles: el fondo recomendado sin cuarto gestor da -0,004 ± 0,001 y +0,006 ± 0,002, las cifras del estudio del fondo. El fondo con todo el peso en el cuarto gestor da exactamente lo mismo que ese gestor solo, en los dos largos (`IDENTIDAD: OK`): el módulo se puede usar desde otra carpeta.

Diferencia contra `max_media` en evidencia, campo mixto, G = 10. Entre paréntesis, remuestreo y plausibles por separado.

| Fondo | 2000 ticks: H3a | 2000 ticks: H3b | 20 000 ticks, parada: H3a | 20 000 ticks, parada: H3b |
|-------|-----------------|-----------------|---------------------------|---------------------------|
| Recomendado, sin cuarto gestor (control) | -0,004 ± 0,001 (-0,010, +0,003) | +0,006 ± 0,002 (-0,003, +0,013) | -0,008 ± 0,001 | +0,006 ± 0,001 |
| Recomendado con `espera`, 6/3/3/4 | -0,004 ± 0,001 (+0,001, -0,011) | +0,003 ± 0,002 (+0,011, -0,008) | -0,006 ± 0,001 | +0,006 ± 0,001 |
| Recomendado con `aprendiz`, 6/3/3/4 | -0,003 ± 0,001 (-0,009, +0,002) | +0,005 ± 0,001 (-0,002, +0,012) | -0,007 ± 0,001 | +0,007 ± 0,001 |
| Recomendado con `aprendiz_rapido`, 6/3/3/4 | -0,006 ± 0,001 (-0,014, +0,001) | +0,001 ± 0,002 (-0,009, +0,009) | -0,012 ± 0,001 | +0,004 ± 0,002 |
| Voto de 2 de 4 con `espera` | 0 | 0 | 0 | 0 |
| Voto de 3 de 4 con `espera` | -0,000 ± 0,002 (+0,023, -0,026) | +0,008 ± 0,003 (+0,039, -0,023) | -0,003 ± 0,002 | +0,018 ± 0,002 |
| Voto de 2 de 4 con `aprendiz_rapido` | -0,004 ± 0,001 | +0,001 ± 0,001 | -0,013 ± 0,001 | +0,001 ± 0,002 |
| Voto de 3 de 4 con `aprendiz_rapido` | -0,013 ± 0,001 | -0,015 ± 0,002 | -0,042 ± 0,002 | -0,027 ± 0,002 |
| Pesos aprendidos con `espera`, 4/4/4/4 | +0,001 ± 0,001 (+0,006, -0,006) | -0,001 ± 0,001 (+0,007, -0,008) | -0,005 ± 0,001 | +0,008 ± 0,002 |

- **Ninguna de las 8 configuraciones con cuarto gestor pasa**, en ninguno de los dos largos. Ninguna mejora H3a.
- El voto de 2 de 4 con `espera` decide exactamente como `max_media` (cero en las 18 000 series de los dos largos): `espera` solo está adentro cuando `max_media` ya lo está, así que no cambia ninguna mayoría.
- El voto de 3 de 4 con `espera` es media dosis de `espera`: la mitad de su ganancia en el remuestreo y la mitad de su pérdida en las plausibles.
- `aprendiz_rapido` como gestor le lleva al fondo la protección en el estrés (+0,020 a +0,033 a 20 000 ticks) y la pérdida en evidencia, en proporción a su peso.
- No es un barrido del reparto de capital. Los pesos y las reglas de voto se fijaron de una vez, sobre las configuraciones que el estudio del fondo ya recomendaba.

## 10. Costo y hardware

Las instrucciones por tick son estimaciones: se contaron las operaciones de la versión en C y se sumó lo que cuesta cada desplazamiento sin desplazador (el mismo truco de memoria que usa hoy el `>> 5` de la media). No se escribió en assembly ni se midió en el gemelo. La regla base usa 27 instrucciones por tick y el presupuesto de la ronda 3 es de 2 262 ciclos (unas 540 instrucciones por hilo en el barrel). La memoria sí sale de un comando: `make tamanos` (`mediciones/tamanos.txt`), que hace la cuenta con los parámetros de cada variante.

| Pieza | Instrucciones por tick (estimado) | Celdas y bits | En las 4 BRAM libres (16 384 bits) | En la RAM de datos (512 palabras, 472 libres) | Hardware que pediría |
|-------|-----------------------------------|---------------|-------------------------------------|-----------------------------------------------|----------------------|
| `espera` | 34 | Sin tabla: dos umbrales | 0 | 1 palabra más | Ninguno |
| `aprendiz` (`tabla`, 32 casillas, ka = 12, h = 16) | 70 a 80 | 32 celdas de 28 bits: 896 bits | 5,5 % | 32 de tabla y 18 de anillo: 50 palabras, 9,8 % | Ninguno |
| La tabla más grande del barrido (32 casillas, tres signos, dos filas) | 80 | 192 celdas de 28 bits: 5 376 bits | 32,8 % | 210 palabras, 41,0 % | Ninguno |
| `aprendiz_patron` (gshare H = 12, 2 bits) | 72 | 4 096 contadores de 2 bits: 8 192 bits | 50,0 %: 2 BRAM | 1 027 palabras a un byte por contador: no cabe | 2 BRAM por MMIO |
| Predictor H = 8, 2 bits | 72 | 256 contadores: 512 bits | 3,1 % | 67 palabras a un byte por contador | Ninguno |
| Torneo H = 12, 2 bits | sin estimar | 16 416 bits | 100,2 %: no cabe por 32 bits | No cabe | Más de las 4 BRAM libres |

- **Las 4 BRAM libres no son la restricción de la tabla.** Ninguna de las 166 variantes de la tabla que aprenden pasa del 33 % de los 16 kbit libres, y todas caben en la RAM de datos que ya existe: la RAM del SoC tiene 512 palabras y el programa actual usa 40. Cada celda necesita 16 + ka bits con signo para el acumulador (la estimación recortada a ±31 de precio por 2^10, por 2^ka), o sea una palabra.
- **El predictor de historia larga sí necesita memoria aparte.** Con 12 bits de historia son 8 192 bits: 2 BRAM en modo 2048 x 2. En la RAM de datos no cabe, porque sin desplazamientos variables cada contador ocupa un byte. De las 63 variantes del predictor que aprenden, 24 no caben en la RAM de datos y 7 tampoco en las 4 BRAM libres. El periférico (dirección, dato de 2 bits, lectura y escritura) no se construyó ni se midió en celdas.
- Los desplazamientos son por constantes, pero el core base no tiene desplazador completo: cada `>> ka` y cada `>> sh` cuesta lo que cuesta hoy el `>> 5` de la media. Con la extensión de la ISA (`emad`, `devk`) baja.
- No hay multiplicaciones en `decidir`. Las del valor inicial son constantes que irían en el `.hex`.

## 11. Variantes probadas y sobreajuste

`mediciones/barrido_cuenta.txt`.

- **266 variantes distintas a 2000 ticks**: 249 de este estudio (229 que aprenden y 20 fijas o con el aprendizaje apagado) y 17 bandas fijas para la cota. 42 más 6 a 20 000 ticks, todas ya contadas a 2000 salvo una (`tabla:banda=1,ka=14,h=16,lim=1`). Además 60 configuraciones del predictor en la medición de exactitud y 8 configuraciones del fondo con cuarto gestor.
- Las listas se escribieron antes de correr cada etapa, salvo tres cosas que se agregaron después de mirar resultados: la etapa `espera` (meseta de la regla fija), las formas con 8 casillas y la etapa `redondeo`. La etapa `tabla_umbral` y la lista del cuarto gestor se agregaron en la revisión de cierre, con sus listas fijadas antes de correrlas.
- Juicio rápido de las 229 que aprenden a 2000 ticks: 0 pasan, 0 mejoran los puntos bajando el percentil 5, 37 quedan iguales y 192 empeoran. A 20 000 ticks, de 39: 0 pasan, 3 iguales y 36 empeoran con las interiores, y 0, 4 y 35 con la vista de parada.
- **De las 249, una sola pasa la lectura rápida del criterio a 2000 ticks: `tabla:ter=1,ezb=64,ezs=-32`.** No aprende, tiene signo opuesto en las dos evidencias y no pasa a 20 000 ticks. Su vecina `ezb=96` mejora H3a y H3b igual y queda en "igual" por el percentil 5.
- Para las variantes que aprenden no hay nada que corregir por selección: ninguna mejora H3a y H3b a la vez. La que más se acerca por H3b es `tabla:ter=3,ezb=64,ka=12,h=8` (+0,006 ± 0,003), que es la regla de espera con un aprendizaje que casi no actúa, y repite su firma: +0,043 en el remuestreo y -0,030 en las plausibles.
- La meseta de `espera` existe en `ezb` (64, 96 y 128 dan +0,003 a +0,005 con H3a) y es angosta en `ezs`: solo -32. Con 0 o -64, H3a queda en -0,010 a -0,013.

## 12. Reglas del enunciado

- **La decisión se calcula en Espino.** Todo es software: tablas en la RAM de datos, sumas, restas, comparaciones y desplazamientos. El predictor de 12 bits pediría 2 BRAM como memoria por MMIO, sin lógica de decisión.
- **No usar información externa ni guardar series.** La tabla parte de la regla y no de la serie de práctica. El anillo guarda los últimos 18 a 34 precios de la serie que se está recibiendo, igual que la suma móvil. Los hiperparámetros se eligieron con la semilla 0. Las tablas de los oráculos de `cota.c` sí salen de las series: son herramientas de medición en el computador y no entran al diseño.
- **Hardware con testbench.** No se agrega hardware.
- **El mismo programa en todas las series.** Sí. La tabla se reinicia sola al comienzo de cada ronda solo si el programa parte de nuevo. En rondas seguidas sin reset seguiría aprendiendo de la ronda anterior, y eso no se evaluó.
- `espera` son dos constantes derivadas de un análisis de la serie de práctica. Es del mismo tipo que el umbral E = 96, pero conviene decirlo en la defensa.

## 13. Días de trabajo para calidad de competencia (estimado)

No se recomienda llevar nada de esto a la competencia. Si se quisiera:

| Pieza | Tareas | Días |
|-------|--------|------|
| `espera` | Dos umbrales en `sw/trade.s` sin saltos que dependan del precio, parámetro en `ref/trader.py`, equivalencia y gemelo | 1 |
| `tabla` (`aprendiz`) | Assembly con anillo y acumulador, equivalencia bit a bit con una referencia en Python, verificación del arranque y de rondas seguidas, documento de estudio | 4 |
| Predictor con 2 BRAM | Periférico con testbench y prueba formal, assembly, equivalencia, documento | 5 |

Para la edición de exhibición bastan la tabla en la RAM actual y este documento: 2 días.

## 14. Riesgos y límites

- **Los rivales y las series son los del arnés.** Vale todo lo dicho en `../README.md`, secciones 14 y 17: el nivel de puntos depende del campo y el error del percentil 5 es 2,8 veces el real.
- **Solo semilla 0.** Ninguna cifra de aquí está confirmada con una semilla reservada.
- **Las cotas O1 y O2 se eligen y se miden con las mismas series.** Con 2 500 a 5 000 series por familia el sesgo es chico frente al tamaño de las cifras, pero no se midió.
- **La cota en puntos usa 29 reglas.** Otra regla fija podría subirla.
- **No se probaron otras formas de aprender**: mínimos cuadrados en línea de una sola pendiente, actualización con el resultado de la operación en vez del retorno a h ticks, o tasas que bajan con el tiempo. El argumento de ruido de la sección 7.1 aplica a todas, pero no se midieron. La forma agrupada (elegir entre reglas completas según su desempeño en papel, que junta todos los ticks en una cifra por regla) es la del estudio del fondo, y tampoco gana: el desempeño en papel no persiste dentro de la ronda (`../r4b_fondo/README.md`).
- **El reparto de capital según desempeño en papel no es de este estudio.** Lo ve el estudio del fondo.
- **Las instrucciones por tick son estimaciones.**
- El efecto de memorización del remuestreo (sección 6.2) afecta a las cifras de `aprendiz_patron` a 20 000 ticks en el remuestreo. Las de la tabla no dependen de la historia.

## 15. Veredicto según los criterios de corte

| Pieza | Veredicto | Razón |
|-------|-----------|-------|
| Tabla de política que aprende (`tabla`, `aprendiz`, `aprendiz_rapido`) | **Descartada de la competencia. Exhibición** | No mejora los puntos esperados en ningún largo ni en ninguna de las 125 variantes que aprenden casilla por casilla. Con prior fuerte es `max_media`, con prior débil pierde hasta 0,9 puntos |
| Tabla como ajuste lento de las bandas | Descartada | Lo mismo, 41 variantes |
| Las estrategias de este estudio como cuarto gestor del fondo | Descartada | 8 configuraciones, ninguna pasa (sección 9.1) |
| Predictor de patrones solo (`patron`) | Descartada | No predice (50,0 a 50,4 %) y pierde 0,5 a 1,4 puntos |
| Predictor como filtro (`mm_patron`, `aprendiz_patron`) | Descartada | No mejora en 39 variantes. Su hardware (2 BRAM) no compra nada |
| Regla fija `espera` | **Descartada con el criterio.** Queda como gestor para el estudio del fondo | Pasa a 2000 ticks y no a 20 000, con signo opuesto en remuestreo y plausibles |
| Acumulador en vez de la forma directa | Se adopta si alguna vez se implementa una media con k grande | El sesgo de redondeo costó 0,243 puntos |

## 16. Lo que no se hizo o no se verificó

- Nada con las semillas 2 ni 3 en este estudio. El estudio de cierre (`../r4_final`) evaluó después `aprendiz` y `espera` una vez con la semilla reservada 3, con el mismo resultado que aquí (sección 17).
- No se escribió assembly ni se corrió nada en el gemelo digital o en el RTL.
- No se construyó ni se sintetizó el periférico de 2 BRAM.
- `make todo` se corrió como un solo comando (22 min 53 s) antes de agregar `make cuarto` y el segundo control negativo de la equivalencia. Esos dos se corrieron aparte, después, con `make cuarto` y `make equivalencia`.
- Los tiempos de `make exactitud` y `make cota` con el límite de 5 hilos no se midieron por separado. Los 19 s y 46 s de la primera versión eran con 24 hilos, porque esas dos herramientas no respetaban `HILOS`. Se corrigió.
- El cuarto gestor del fondo se midió con 8 configuraciones elegidas aquí sobre las que recomienda el estudio del fondo. No es un barrido del reparto de capital, y el estudio del fondo no usó estas estrategias.
- No se evaluaron rondas seguidas sin reset, ni otras cajas y comisiones.
- La cota a 20 000 ticks usa 1000 series por familia y la exactitud a 20 000 ticks usa 200.
- El control de la contabilidad de `cota.c` contra el arnés se hizo a 2000 ticks en dos familias. A 20 000 ticks no se comparó.
- La serie de práctica aparece en `exactitud` como una sola serie de 20 000 ticks (y 10 bloques a 2000): sus cifras no tienen error.

## 17. Auditoría

Revisión independiente hecha el 15/11 junto con la de los estudios de ejecución, del fondo y de cierre. Todo está en `../auditoria_r34/` y se corre con `make todo` desde ahí. Aquí va lo que toca a este estudio.

### 17.1 Qué se revisó y qué dio

| Punto | Cómo | Resultado |
|-------|------|-----------|
| El ajuste de la tabla usa solo precios ya recibidos | Lectura de `e_tabla.c`: en el tick n se ajusta la casilla usada en el tick n - 1 - h con `R = p[n] - p[n - h]`, el precio que acaba de llegar menos el precio al que se ejecutó esa decisión. El anillo tiene 128 lugares y `h` llega a 126 | Correcto |
| El predictor | Lectura de `pred.h`: la misma estructura, entrena el contador del tick n - 1 - h con el signo de `p[n] - p[n - h]` | Correcto |
| Prueba | El comando `causal` y una perturbación propia de los precios futuros más una prueba de martingala. El comando `causal` solo no alcanza para `aprendiz`: usa 3000 ticks y con prior fuerte la tabla casi no cambia decisiones en ese largo, así que una fuga en el ajuste no se vería. La prueba propia usa 8192 ticks, 63 cortes por serie y variantes que aprenden rápido por el mismo código (`ka=6` y `ka=8` con h de 4, 16, 32 y 126, contador de 4 bits, bandas, tercer índice, dos filas, forma directa y tres configuraciones del predictor) | 0 fallas en 18 estrategias de este estudio. Un control negativo con la forma de la tabla y la fuga puesta en el ajuste (tasa 2^-12, retorno futuro a 16 ticks) sí falla |
| La tabla | Escrita de nuevo a partir de la sección 2, sin usar el núcleo | `aprendiz` y `aprendiz_rapido`: 46 061 series de 36 archivos cada una, 0 distintas. En la práctica completa `aprendiz` da 27 567 con 663 órdenes |
| Cifras | Torneo con el valor esperado exacto, semillas 0 y 3 | `aprendiz` contra `max_media`, campo mixto, semilla 0 / semilla 3: -0,0001 ± 0,0002 / -0,0002 ± 0,0003 con H3a a 2000 ticks, -0,0283 / -0,0273 a 20 000 con interiores y -0,0160 / -0,0139 con parada. En el estrés con parada, +0,039 / +0,047. Son las cifras de este documento |
| Como cuarto gestor | El fondo completo del estudio de cierre, con la tabla de cuarto gestor, reescrito entero | `completo`, `completo_s` y `completo_min`: 46 061 series cada uno, 0 distintas |
| Aritmética | Lectura de `decidir` | Los productos y cocientes son entre constantes de la configuración. Con datos solo hay sumas, comparaciones y desplazamientos por 5, 10 y 12 |
| Reglas | Lectura | La tabla parte de una recta calculada con E, X y la pendiente: no sale de la serie de práctica. Las tablas de `cota.c` sí salen de las series y no están en ninguna estrategia |
| Repetición | `make causal`, `make equivalencia` y `make tamanos` de esta carpeta, con el binario recompilado contra el núcleo actual | Los 37 archivos de `mediciones/` quedan idénticos |

### 17.2 Precisiones

1. **Sección 5, cota en puntos.** Los +0,038 y +0,064 son el promedio de dos cifras del arnés, (0,046 + 0,030) / 2 y (0,068 + 0,059) / 2. La cuenta está bien. Las dos cifras de entrada no se recalcularon, y el texto ya dice que las reglas se eligieron con las mismas series: es una cota optimista y no algo alcanzable.
2. **Sección 16, semilla reservada.** El estudio de cierre evaluó `aprendiz` y `espera` una vez con la semilla 3, con el mismo resultado que aquí.

Ninguna cifra de las tablas cambió y ninguna medición se volvió a generar.

### 17.3 Lo que no se cubrió

- Las 249 variantes del barrido no se volvieron a correr. Se reescribió solo la tabla en su forma básica (32 casillas, modo 0, sin tercer índice). `espera`, el predictor y las demás formas pasan las pruebas de causalidad y sus cifras son las del arnés.
- La exactitud del predictor (sección 6) y los oráculos O1 a O3 no se recalcularon.
- El efecto de memorización del remuestreo largo (sección 6.2) no se volvió a medir.
