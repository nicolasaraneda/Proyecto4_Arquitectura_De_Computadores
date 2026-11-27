# Proyecto 4: Pochoco Trader

Arquitectura de Computadores, Universidad de los Andes, 2026-2. Profesor: Jorge Gómez Mir.
Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

## 0. Resumen

Un agente de inversión que corre en el Pochoco SoC (procesador Espino, RV32E) sobre la Nandland Go Board (iCE40 HX1K, 25 MHz). En cada tick una FPGA maestra manda por SPI el precio de una acción y el programa responde si compra, vende o mantiene. Construimos cuatro peldaños de hardware, de R0 (el Espino del curso) a R3 (un Espino de cuatro hilos que corre C1).

**La idea de C1.** Cada ronda se normaliza entre 100 y 255, así que ver uno de los extremos asegura que el otro va a llegar: con eso, la banda 40 ya casi no deja información por usar, y un rival que la copie empata. C1 juega la banda 40 y agrega un desempate: apuesta antes de ver los extremos solo cuando un modelo de paseo aleatorio da 95 % o más de que el 255 llega primero, y cuando va 100 arriba de un clon de la banda 40 que emula en un hilo, se pone a copiarlo.

| Resultado | Cifra | Fuente |
|-----------|-------|--------|
| Torneos de 3 rondas que C1 gana sola, examen en las cinco empresas | 81,8 % (banda 40: 45,7 %) | `docs/mediciones/exploracion/c1_examen.txt` (rama `minutos-reales`) |
| Torneos en que no queda debajo del rival | 83,3 % (banda 40: 90,4 %) | El mismo |
| Diferencia media por ronda contra la banda 40 | +152 (error estándar 52) | El mismo |
| Serie de práctica Meta, 20 000 ticks | C1 22 682, banda 40 21 392, `max_media` 9 722 | `docs/mediciones/c1/series_reales.txt`, `docs/cotas.md` |
| Programa de R3 contra su referencia en Python, por el RTL | 4,14 millones de ticks, 0 diferencias | `docs/mediciones/c1/puerta_b.txt` |
| R3 con la maestra real, 25/11, a 10 ms | Meta 22 682 con 6 órdenes y Tesla 21 224 con 8: idénticos a la simulación de C1. En AMD no calza (8 315 con 1 orden) y la causa no está explicada | `docs/puertas.md`, "Puerta de maestra: el 25/11" |
| R3 en la FPGA | 1038 de 1280 celdas, 14 de 16 bloques, 48,41 MHz mínima en 10 semillas, responde en 807 de 2262 ciclos en el peor tick | `bitstreams/README.md`, `docs/puertas.md` |

El costo está a la vista: C1 queda debajo del rival en más torneos que la banda 40 (16,7 % contra 9,6 %). Y con la maestra real R3 corrió el 25/11 solo a 10 ms: coincidió con la simulación en dos de tres series, y en la tercera no, sin causa conocida. El SCLK real y los ritmos de 1 ms y 0,1 ms siguen sin verificarse (sección 11).

## 1. Cómo llegamos a la idea

| Fecha | Qué pasó | La cifra que motivó el cambio | Dónde |
|-------|----------|-------------------------------|-------|
| 15/11 | `max_media`: reversión a la media exponencial, órdenes de 63, elegida con el protocolo de bloques y remuestreos sobre la serie de práctica antigua | +0,04 puntos esperados del torneo sobre la regla base; 25 973 en esa serie | `docs/decisiones.md`, T51 |
| 17/11 | El profesor cambia la serie de práctica por minutos reales de Meta normalizados entre 100 y 255. `max_media` pierde plata | 9 722 con 249 órdenes, bajo los 10 000 de no operar | `docs/mediciones/tabla_3_1.txt`, `docs/cotas.md`, sección 3 |
| 17/11 | Observación: si la ronda se normaliza entera, el 100 y el 255 aparecen siempre. "Esperar" el 100 para comprar y el 255 para vender, y después operar una banda | "Espera" con banda 60: 19 214 en Meta; en la población modelada, de 19 900 a 20 500 de media contra 11 700 de `max_media` | `docs/decisiones.md`, T133; `docs/cotas.md`, sección 5 |
| 18/11 | Clase con la maestra real: R2 con banda 60 corre las tres rondas. En la ronda de Tesla un rival con la regla "comprar en el primer 100, vender en 220 y no volver" hace más | Tesla: banda 60 18 779, el rival 21 467 | `docs/puertas.md`, "Puerta de maestra: la clase del 18/11" |
| 19/11 | Banda 40 en vez de 60: vender más arriba, como el rival, sin renunciar a volver a comprar | +205 por ronda (error estándar 101) sobre la banda 60 en todas las ventanas reales | `docs/decisiones.md`, T140 |
| 19 a 21/11 | Exploración para superar a la banda 40 (abajo) | Ninguna variante pasa su criterio hasta C1 | `docs/exploracion_ideas.md` (rama `minutos-reales`) |
| 21/11 | C1 pasa el examen fijado de antemano y se construye como R3 | g +36,1 (2,4) y nd -7,1 (2,5) contra los umbrales +20 y -8 | `docs/decisiones.md`, T150 a T152 |
| 25/11 | Prueba con la maestra real, solo a 10 ms. En Meta y Tesla la placa da lo mismo que la simulación de C1, con su orden parcial. En AMD no | Meta 22 682 (banda 40: 21 392), Tesla 21 224 (20 795), AMD 8 315 (C1: 27 199) | `docs/puertas.md`, `docs/bitacora/c1.md` |

**La exploración, paso a paso.** Todas las variantes se ajustaron en las 100 acciones ajenas (12 000 ventanas de 20 000 minutos normalizadas) y se examinaron una sola vez en Meta, Apple, Netflix, AMD y Tesla, con el criterio escrito antes de mirar. Las secciones que se citan aquí y más abajo son de `docs/exploracion_ideas.md`, que está en la rama `minutos-reales` junto con su bitácora y el examen (`docs/mediciones/exploracion/`); esa rama no está integrada en esta.

- **Diez ideas sobre la banda 40** (sección 0): finales de ronda, decisión por el precio inicial, detectores de régimen, contadores. Ninguna le gana fuera de muestra; las mejores quedan entre 5 y 80 abajo. La banda 40 resultó el óptimo de su vecindad en 56 combinaciones de compra y venta.
- **Módulo A** (sección 12): usar la volatilidad de la ronda para apostar en la fase A. +60 por ronda (error estándar 30) en el examen, pero +11 (76) en la validación por años: no cumple el criterio.
- **V1, V2 y V3** (sección 13): la política óptima del paseo normalizado (sección 4 de este README). V1 optimiza solo la fase A, V2 las cuatro fases y V3 es V1 con media posición. V2 gana +880 por ronda a la banda 40 en las ajenas, pero pierde 38,2 % de los torneos contra ella. V3 con la guarda de media posición da +124 (77) en el examen y empata con la banda 40 en la validación por años: tampoco cumple.
- **V4 y V4b** (sección 14 y `docs/bitacora/exploracion.md` de esa rama): V3 más un candado contra un clon de la banda 40. En V4 ninguna combinación queda sobre la banda 40 en media (la mejor, -67 con error estándar 29). V4b gana 75,8 % de los torneos, pero no queda debajo solo en 77,2 % contra 87,9 % de la banda 40.
- **V5 y C1** (sección 15): dos cambios sobre V4b. Apostar en la fase A solo con probabilidad de 0,95 o más, y correr el motor desde el primer extremo aunque no haya nada que recuperar. C1 domina a V4b en las dos cifras por unos 7 errores estándar (83,0 y 81,9 contra 77,2 y 75,8).

**Lo que probamos y no funcionó** (diferencias en puntos de "no queda debajo", nd, y de "gana", g, salvo que se diga otra cosa):

| Idea | Resultado | Dónde |
|------|-----------|-------|
| Cambiar la forma de operar en la fase D | Bajo la banda 40 por ronda: grilla y torneo en sombra de 270 a 440, programación dinámica de 220 a 310, contadores más de 7 000. Los modelos que se calibran solos con la serie en curso pierden todos | `docs/exploracion_ideas.md`, sección 0 |
| Tres bandas, una por hilo | Contra el rival de Tesla en el caso B, -82 por ronda (137) contra +322 (148) de la banda 40 sola | Sección 10 |
| Audacia al final: con D negativa, jugar lo contrario del clon | De -0,6 a -7,1 de nd; la posición contraria tiene deriva en contra | Sección 15.7 |
| Frenos por pérdida y pisos en D | De -2,2 a -4,2 de nd; cortan la cola a costa de las dos cifras | Sección 15.7 |
| Comprar cerca del piso en la fase C | nd 72,1 a 73,1, bajo V4b: el 100 está garantizado y comprar antes regala niveles | Sección 15.7 |

Un error de diseño que se corrigió en el camino: el primer candado igualaba las acciones del clon. Con eso perdía de 664 a 1 240 por ronda en las rondas que llegaban al candado, porque la estrategia propia ya tenía más caja que el clon y al igualar acciones la dejaba sin usar. El candado de C1 copia las órdenes del clon ("comprar 63" o "vender 63") con la cuenta propia, y así compra más acciones con lo ganado (`docs/bitacora/exploracion.md`, sección 14, puntos 6 y 7, rama `minutos-reales`).

## 2. La información que deja la normalización

Cada ronda es un trozo de 20 000 minutos de una acción real llevado linealmente a la escala de 100 a 255, con su mínimo exactamente en 100 y su máximo exactamente en 255. Las tres series de la maestra que conocemos lo cumplen (Meta de práctica, Tesla y AMD de la clase del 18/11).

Eso tiene una consecuencia que ningún precio individual muestra: **al ver el 100, el 255 está garantizado antes del final de la ronda, y al ver el 255, el 100 también**. Lo que la estrategia sabe en cada tick depende solo de qué extremos ya vio:

| Fase | Qué se vio | Qué se sabe del futuro |
|------|------------|------------------------|
| A | Ninguno | Los dos extremos van a llegar, sin saber cuál primero |
| B | Solo el 255 | El 100 va a llegar |
| C | Solo el 100 | El 255 va a llegar |
| D | Los dos | Nada más de los extremos: queda la reversión dentro de la banda |

Llamamos caso S a las rondas en que el 100 llega antes que el 255 (pasan de A a C) y caso B a las otras (de A a B). En las cinco empresas, 58 % de las ventanas son del caso S.

**Por qué es legítimo bajo la regla 4 del enunciado** (el procesador decide, no se usa información externa a la serie, no se guardan series):

1. Es información de la propia serie: sale de cómo se construye la ronda, igual que el nivel o la volatilidad que mide cualquier estimador.
2. La decide el procesador en la placa. Espino compara cada precio con 100 y 255, lleva la fase y calcula la orden. La tabla de R3 es una memoria de solo lectura sin lógica; con su palabra `POLITICA` en 0 la política se apaga y la placa decide exactamente la banda 40.
3. No hay series almacenadas. Las tablas las calcula `ref/c1/tablas.py` desde un modelo cuyas entradas son la varianza por tick, el largo de la ronda, los niveles 100 y 255 y la comisión. No entra ningún precio (`docs/defensa/c1.md`, sección 6).

Si una ronda no cumpliera la normalización (un precio bajo 100), R3 lo detecta y pasa a la banda 40 hasta el final (sección 6).

## 3. Banda 40

La regla, que corre en R0, R1 y R2 (`sw/trade.s`, `sw/fondo.s`, `ref/trader.py`):

1. Parte en caja.
2. Al ver el 100 manda "comprar 63"; al ver el 255 manda "vender 63". Las dos órdenes se repiten: la maestra recorta la compra a lo que alcanza y la venta a lo que hay.
3. Después de haber visto los dos extremos, compra con precio 140 o menos y vende con 215 o más.
4. Entre medio mantiene.

Es la respuesta natural a la sección 2: en la fase C estar invertido es una ganancia segura hasta el 255, en la fase B estar en caja espera un 100 seguro, y en la fase D solo queda la reversión, que la banda captura con dos órdenes por vuelta y sin pagar comisiones de más.

| Serie | Banda 40 | Banda 60 | Fuente |
|-------|----------|----------|--------|
| Meta, práctica | 21 392 | 19 214 | `docs/mediciones/c1/series_reales.txt` |
| Tesla, clase del 18/11 | 20 795 | 18 779 | El mismo |
| AMD, clase del 18/11 | 26 470 | 21 895 | El mismo |

En todas las ventanas reales la banda 40 suma +205 por ronda (error estándar 101) sobre la banda 60 (`docs/decisiones.md`, T140), y en 56 combinaciones de nivel de compra y de venta el mejor punto es exactamente 140 y 215 (`docs/exploracion_ideas.md`, sección 0).

**Su límite.** La banda 40 deja poco por usar, y eso también la hace fácil de copiar. Un rival que corra la misma regla termina con el mismo patrimonio en todas las rondas, y contra la regla de extremos puros la banda 40 empata 55,7 % de los torneos, porque en la mayoría de las rondas las dos hacen lo mismo (`docs/exploracion_ideas.md`, sección 15.3). Con un puntaje por posición, empatar con el mejor no es ganarle.

## 4. El modelo matemático

Fuentes: `ref/c1/paseo.py` (el modelo), `ref/c1/tablas.py` (la compresión), `docs/c1_plan.md` (secciones 3 y 4), `docs/defensa/c1.md` (secciones 5 y 6) y `docs/exploracion_ideas.md`, sección 13 (la calibración).

**El paseo entre dos barreras.** El precio normalizado se modela como un paseo en los enteros de 100 a 255:

$$x_{t+1} = x_t + \xi_t, \qquad \xi_t \sim \text{gaussiana discretizada en los enteros}, \quad \operatorname{Var}(\xi_t) = v^2,$$

**condicionado** a que en los 20 000 ticks de la ronda su mínimo sea 100 y su máximo 255, que es lo que hace la normalización con cualquier serie. Se calcula para ocho valores de v², de 1/8 a 2.

**Qué extremo llega primero.** Sea g_A(x, r) la probabilidad de que, desde el precio x con r ticks por delante, el paseo toque los dos extremos sin salirse de [100, 255], y h_A(x, r) la de que lo haga con el 255 primero. Las dos se calculan hacia atrás, de r = 0 a r = 19 999, sumando sobre el paso siguiente:

$$g_A(x, r) = \sum_k K(k)\, g_A(x+k, r-1), \qquad P(\text{255 antes que 100} \mid A, x, r) = \frac{h_A(x, r)}{g_A(x, r)},$$

con K(k) la probabilidad de un paso k, y con las condiciones de borde que cambian de fase al tocar 100 o 255. En la fase A, C1 toma media posición solo si esa probabilidad es **0,95 o más**, desde el tick 390. El modelo calibra en datos reales: con v² estimado como S2/t (la suma de las diferencias al cuadrado sobre los ticks transcurridos), ningún decil de la probabilidad predicha se aleja más de 4,5 puntos de lo observado en las acciones ajenas, ni más de 4,0 en las cinco empresas.

**La política V2.** Con las mismas probabilidades, el paso condicionado de una fase a otra es

$$P(x \to y \mid F) = K(y - x)\,\frac{g_{F'}(y, r-1)}{g_F(x, r)},$$

y la programación dinámica elige, para cada fase, precio, tiempo restante y posición, la posición siguiente que maximiza el logaritmo esperado del patrimonio, restando el costo relativo de la comisión (10 / 15 000 por un cambio completo). V2 es esa política en las cuatro fases. Es lo que C1 usa como motor después del primer extremo.

**Cómo cabe en 512 palabras.** La política completa no cabe en la placa. Se comprime a un umbral de precio por celda:

| Tabla | Celdas | Qué guarda cada celda | Palabras |
|-------|--------|-----------------------|----------|
| Fase A | 8 clases de v² × 16 tramos de 1250 ticks | Nivel de entrada (entra si p ≥ nivel) y de salida | 64 a 191 |
| Motor | 3 fases (B, C, D) × 8 clases × 8 tramos de 2500 ticks | Nivel bajo el cual pasa a invertido y nivel bajo el cual se mantiene | 192 a 383 |

Son 320 celdas de dos bytes, 640 bytes, en `rtl/pochoco_tabla512.v`. La compresión es posible porque en la fase A "umbral de V3 y probabilidad de 0,95 o más" resulta un solo umbral en las 128 celdas (la probabilidad crece con el precio), y porque en las 192 celdas del motor dos de los cuatro umbrales originales nunca se usan. La clase de v² se obtiene sin dividir: se compara 64 · S2 con siete sumas N_j (t − 1), con N_j = 11, 20, 28, 39, 55, 78 y 111, y se aplica una histéresis de 64 ticks.

**El clon y la diferencia D.** La placa lleva dos cuentas con la contabilidad oficial (caja 10 000, comisión 5, compra recortada a (caja − 5) / p): la propia, con las órdenes que escribió de verdad, y la de un clon que juega la banda 40 pura con los mismos precios. La diferencia es

$$D = (C - C') + (a - a')\,p,$$

con C y a la caja y las acciones propias, C' y a' las del clon, y p el precio actual. El producto se hace con sumas sobre los 8 bits de p, porque el Espino de competencia no multiplica.

**El candado.** Cuando D llega a 100, la placa copia las órdenes del clon hasta el final de la ronda. Desde ahí las dos cuentas hacen las mismas órdenes y D casi no se mueve: la ventaja ganada se conserva contra cualquier rival que juegue la banda 40.

## 5. C1

| Pieza | Cuándo | Qué hace |
|-------|--------|----------|
| Apuesta en la fase A | Antes de ver un extremo, desde el tick 390 | Toma media posición, floor(W / 2p) acciones, solo si la tabla da 0,95 o más de que el 255 llegue antes que el 100. Sale cuando la tabla lo dice |
| Motor | Desde el primer extremo | Decide con la política V2 comprimida, haya apostado o no, mientras D sea menor que 100 |
| Candado | Cuando D llega a 100 | Copia las órdenes del clon de la banda 40 hasta el final de la ronda |

Con la política apagada (palabra `POLITICA` en 0, o el modo seguro), R3 decide exactamente la banda 40: los mismos bytes que R2 en 46 corridas por el RTL y en 203 series a los tres períodos en el gemelo (`docs/mediciones/c1/puerta_a.txt`).

**Por qué el candado copia órdenes y no iguala acciones.** Al cerrar el candado la estrategia propia suele tener más patrimonio que el clon. Igualar acciones la dejaba con caja sin usar y con dos o tres órdenes extra a precios peores; en la exploración eso costó de 664 a 1 240 por ronda en las rondas que llegaban al candado (sección 1). Copiar las órdenes con la cuenta propia hace que, después de la primera, las dos cuentas estén siempre en la misma posición, cada una con su caja.

**El examen.** Una sola corrida, con el código congelado y el criterio de Nicolás fijado antes de mirar: g de C1 al menos 20 puntos sobre la banda 40 y nd a lo más 8 puntos debajo. 3 600 ventanas de las cinco empresas, torneos de 3 rondas mano a mano contra un rival sorteado (extremos puros 30 %, la regla del rival de Tesla 30 %, bandas 30, 50 y 60 con 10 % cada una, banda 40 exacta 10 %), errores estándar agrupados por fecha y empresa (`docs/mediciones/exploracion/c1_examen.txt`, rama `minutos-reales`).

| Cifra | Banda 40 sola | C1 | Diferencia (error estándar) | Criterio | Resultado |
|-------|---------------|----|-----------------------------|----------|-----------|
| g: gana el torneo | 45,7 % | 81,8 % | +36,1 (2,4) | Al menos +20 | Se cumple con holgura |
| nd: no queda debajo | 90,4 % | 83,3 % | -7,1 (2,5) | A lo más -8 | Se cumple por 0,9 puntos, menos que su error estándar |
| Patrimonio por ronda | | | +152 (52) | | |
| Lo que queda debajo, en promedio | 89 | 117 | +28 (22) | | |

**Dónde está el costo: todo en el caso S.** En las rondas en que el 100 llega primero, C1 cae 18,1 puntos de nd (error estándar 3,1) y queda en -44 por ronda (55): el motor cierra el candado en la mitad de esas rondas y en la otra mitad queda unos 316 abajo. En el caso B gana en las dos cifras (+6,3 de nd, +60,7 de g) y +431 por ronda (62). Netflix, con 71 % de casos S, es el peor subconjunto. Contra un clon exacto de la banda 40, C1 queda debajo en 16,6 % de los torneos.

**Sin señal de sobreajuste.** C1 se armó en las 100 acciones ajenas y se examinó en las cinco empresas. El intercambio se repite: g +36,4 (1,0) en las ajenas contra +36,1 (2,4) en el examen, y +151 (20) por ronda contra +152 (52). La caída de nd es algo mayor en el examen (-7,1 contra -5,0), porque ahí la banda 40 sola sube, no porque C1 baje (83,3 contra 83,0). El punto 1 del criterio se cumple en los diez subconjuntos (caso, año y empresa). Hay que decir también que fue la tercera mirada a las cinco empresas: las dos anteriores fueron los exámenes del módulo A y de V3, que no cumplieron su criterio y no se adoptaron.

**Lo que C1 no hace.** No sube la nota esperada: con un campo supuesto de tres grupos, la diferencia con la banda 40 es de menos de una centésima de los 2 puntos, y a favor de la banda 40 (`docs/exploracion_ideas.md`, sección 15.5). Lo que cambia es con qué frecuencia se gana el mano a mano.

## 6. Los hilos

El Espino barrel de R1 a R3 tiene cuatro hilos que rotan por un pipeline de 4 etapas: cada hilo ejecuta una instrucción cada 4 ciclos, sin riesgos de datos ni de control (`docs/espino_barrel.md`). En R3 cada hilo tiene un rol (`sw/c1.s`, `docs/c1_plan.md`, sección 2):

| Hilo | Rol | Qué hace | Qué publica |
|------|-----|----------|-------------|
| 0 | Corredor | Sondea `STATUS`, lee `PRICE`, calcula la banda 40 por su cuenta, espera la política con un plazo de 28 vueltas y escribe `DECISION` una vez por tick. Es el único que toca el SPI | `D_PUB` (tick y precio), `D_FASE` (byte de la banda 40), `D_ORD` (el byte que escribió) |
| 1 | Régimen | S2 con diferencias topadas en 15, la clase de v² con histéresis y el reloj de los tramos | `D_REG` y la dirección de la celda de cada tabla |
| 2 | Política | Lee la celda y compara el precio con sus niveles | `D_TAB` (posición de la fase A y del motor) |
| 3 | Emulador | Ejecuta la orden propia y la del clon con la contabilidad oficial, calcula D, lleva los modos (fase A, motor, candado) y arma el byte de la política; después, fuera del camino de la respuesta, el patrimonio y los 7 segmentos | `D_POL` (tick y byte de la política) |

```
byte_done
   |
hilo 0: lee PRICE --> D_PUB (tick, precio)
   |                     |               |                  |
   |               hilo 1: S2,      hilo 2: espera     hilo 3: cuenta propia
   |               clase, reloj     D_REG, lee la      (D_ORD) y del clon,
   |               --> D_REG        celda --> D_TAB    D, modos; espera D_TAB
   |                                                   --> D_POL
hilo 0: banda 40 --> D_FASE                               |
hilo 0: espera D_POL del tick (plazo) <-------------------+
hilo 0: escribe DECISION, publica D_ORD
```

**Memoria compartida.** Cada palabra tiene un solo hilo que la escribe, y lo publicado lleva el número de tick en los bits 31:8. Un hilo que espera un dato lo relee hasta que trae el tick actual; una escritura de palabra es atómica, así que no hacen falta candados de memoria. En la serie Meta a 0,1 ms el hilo 0 publica el precio a los 35 ciclos, el hilo 3 la política a los 496 en promedio y `DECISION` sale a los 530 en promedio, 783 en el peor tick (`docs/mediciones/c1/ticks.txt`).

**Degradación.** El hilo 0 decide siempre. Si `D_POL` no llega a tiempo y es del tick anterior, sostiene la orden si era completa y mantiene si era parcial; si es más vieja, pasa a modo seguro: la banda 40 sin política hasta el final de la ronda. También entra a modo seguro con un precio bajo 100 o pasado el tick 20 000. Probado con 26 fallas puestas a propósito, todas con la decisión esperada y a tiempo, peor caso 907 de 1131 ciclos (`docs/mediciones/c1/degradacion.txt`).

**Vigilante y relevo.** Si el hilo 0 deja de escribir `DECISION` durante 5 precios seguidos, el vigilante reconfigura la FPGA con `SB_WARMBOOT` y arranca la imagen 1 de la flash, que es R0 con la banda 40. En R3 con el hilo 0 colgado en el tick 100 el relevo se pide al terminar la transacción 105 (`bitstreams/README.md`). El relevo de R2 se midió en la placa en 35,50 ms (`docs/mediciones/placa_16nov.md`).

**Por qué R2 usa un hilo y R3 cuatro.** La banda 40 son unas 42 instrucciones por tick: en el hilo 0 responde en 127 ciclos y los otros tres hilos quedan en espera. El trabajo de C1 en un solo hilo serían del orden de 470 instrucciones por tick en promedio y 700 en el peor caso, a 4 ciclos cada una: entre 1 900 y 2 800 ciclos, contra 2 262 de la ronda 3. Repartido en cuatro hilos que avanzan en paralelo, el peor tick queda en 807 (`docs/defensa/c1.md`, pregunta 9).

## 7. Hardware de R0 a R3

| Peldaño | Qué agrega | Programa | Celdas | Bloques de memoria | Frecuencia máxima, mínima en 10 semillas | Ciclos por tick, promedio y peor |
|---------|------------|----------|--------|--------------------|------------------------------------------|----------------------------------|
| R0 | Espino base del curso con un reset más largo | `sw/trade.s`, banda 40 | 1083 | 12 | 42,43 MHz | 56,5 y 60 |
| R1 | Espino barrel de 4 hilos, instrucciones `emad` y `devk`, tabla de parámetros en BRAM | `sw/fondo.s`, banda 40 en el hilo 0 | 1029 | 13 | 51,59 MHz | 123 y 127 |
| R2 | R1 más el vigilante y la imagen múltiple con R0 de respaldo | El de R1 | 1045 | 13 | 47,86 MHz | 123 y 127 |
| R3 | R2 con la tabla de 512 palabras | `sw/c1.s`, C1 en los 4 hilos | 1038 | 14 | 48,41 MHz | 529,9 y 783 (807 en todas las puertas, 916 con un hilo colgado) |

De 1280 celdas y 16 bloques. Los ciclos van desde que llega el precio hasta la escritura de `DECISION`, en la serie Meta a 0,1 ms; el presupuesto a 0,1 ms es 2 262 ciclos, y la puerta de simulación exige la mitad (1 131). Fuentes: `bitstreams/README.md` (celdas, bloques y frecuencia de cada bitstream guardado), `docs/mediciones/p7/cotas/variantes.txt` (R0 y R2), `docs/mediciones/fondo/r1/ticks.txt` (R1) y `docs/mediciones/c1/perfil_hilos.txt` (R3). Las celdas cambian algunas decenas según el programa con que se sintetiza: con el mismo flujo y el programa de la banda 40, R2 da 1015 (`docs/mediciones/fondo/r2/timing.txt`) y R3 le suma 23. El detalle de la escalera y las métricas del punto 3.3 están en `docs/codiseno.md`.

## 8. Cómo se verificó C1

| Prueba | Resultado | Archivo |
|--------|-----------|---------|
| Referencia `ref/c1/c1.py` contra el C1 de la exploración | 2 400 ventanas, 48 millones de bytes, 0 diferencias | `docs/mediciones/c1/contra_exploracion.txt` |
| Assembly contra referencia | Tesla, AMD y Meta por el RTL a 0,1 y 1 ms, Meta a 10 ms y 200 ventanas reales: 4,14 millones de ticks, 0 diferencias en bytes y en estado; 203 series reales y 1 081 sintéticas en el gemelo a los tres períodos | `docs/mediciones/c1/puerta_b.txt`, `series.txt` |
| Contabilidad emulada contra la del testbench oficial | 6,95 millones de vectores sin diferencias en el dominio de la competencia; tick a tick, 3 052 series, 0 diferencias, con 858 órdenes parciales | `docs/mediciones/c1/contabilidad.txt` |
| RTL de R3 contra la maestra emulada del testbench oficial | 28 de 28 corridas (13 series a 0,1 y 1 ms), `decisiones.csv` idéntico y monitor de la cuenta sin diferencias; los controles negativos sí dan diferencias | `docs/mediciones/c1/contabilidad_rtl.txt` |
| Testbench oficial sin modificar | 4/4, peor caso 759 ciclos de 2 262 | `docs/mediciones/c1/oficial.txt` |
| Core en la configuración de R3 | 7,97 millones de instrucciones contra el Espino base, 0 diferencias; 21 de 21 mutaciones detectadas | `docs/puertas.md`, `docs/mediciones/c1/criterio5_*.txt` |
| Degradación, controles negativos y estrés | 26 de 26, 25 de 25 y 57 de 57 | `docs/mediciones/c1/degradacion.txt`, `controles.txt`, `estres.txt` |
| Autoprueba en la placa | Pasa en los tres ritmos el 21/11 (firma `984c`, se ve `4C` y `98`) | `docs/bitacora/c1.md`, quinta parte; `docs/mediciones/autoprueba_r3.txt` |
| Integración local | 27 de 27 pasos, con R0, R1 y R2 intactos | `docs/mediciones/ci_local_c1.txt` |

Todas las puertas de R3 están en `docs/puertas.md`; las de R0 a R2, en el mismo archivo.

## 9. Series reales

| Serie | C1 | Banda 40 | Banda 60 | Rival observado el 18/11 (compra en el primer 100, vende en 220) |
|-------|----|----------|----------|------------------------------------------------------------------|
| Meta, práctica | 22 682 | 21 392 | 19 214 | 21 752 |
| Tesla, clase del 18/11 | 21 224 | 20 795 | 18 779 | 21 467 |
| AMD, clase del 18/11 | 27 199 | 26 470 | 21 895 | 21 824 |

**Lo que dio la maestra real el 25/11** (a 10 ms, solo estas rondas; resultados informados por quien corrió la prueba, sin registro de terminal en el repositorio):

| Serie | Placa | C1 en simulación | Banda 40 en simulación | ¿Calza con C1? |
|-------|-------|------------------|------------------------|----------------|
| Meta, práctica | 22 682 con 6 órdenes | 22 682 con 6 | 21 392 con 4 | Sí, idéntico |
| Tesla | 21 224 con 8 órdenes | 21 224 con 8 | 20 795 | Sí, idéntico |
| AMD | 8 315 con 1 orden | 27 199 con 11 | 26 470 con 8 | No |

En Meta y Tesla el resultado es el de C1 y no el de la banda 40, incluida la compra de 22 acciones de la fase A en Meta (una orden parcial), que antes solo estaba probada en simulación. En AMD la placa hizo una sola compra de 48 acciones a unos 208, no vendió nunca y terminó con la decisión 0x7F; no es ni C1 ni la banda 40. Las hipótesis son una mala conexión en el puerto usado en esa ronda (distinto del de las otras dos) o un bitstream distinto, y ninguna está comprobada: no se anotó el hash grabado ni se leyó la placa. En esas mismas rondas, dos rivales hicieron 23 215 en Meta y 21 659 en Tesla, sobre nuestros 22 682 y 21 224; es una ronda por serie y no dice nada del torneo de tres rondas.

Salen de `make c1-series-reales` (`tools/c1/series_reales.py`, `docs/mediciones/c1/series_reales.txt`). Son tres series: ilustran cómo opera cada regla, no prueban nada. La prueba es el examen de la sección 5. Tesla y AMD se arman desde los datos registrados en la clase (`tools/reales.sh`, carpeta `$P4_DATOS`), que no están en el repositorio.

## 10. Cómo reproducir todo

Todo se corre desde la raíz, con OSS CAD Suite en el `PATH` (`export PATH=<carpeta de OSS CAD Suite>/bin:$PATH`). El repositorio se clona con su historial completo: `make r0-reproducir` reconstruye R0 desde su commit. La lista completa de objetivos está en `docs/comandos.md`.

**Versiones de las herramientas** (`docs/mediciones/p7/recursos.txt`, `docs/mediciones/fondo/r1/ticks.txt`, `.github/workflows/ci.yml`):

| Herramienta | Versión |
|-------------|---------|
| OSS CAD Suite | 2026-09-06 (la misma en la integración continua) |
| Yosys | 0.68+195 |
| nextpnr-ice40 | 0.11.1-19-g8dbcee5c |
| Icarus Verilog | 14.0 (devel, s20260301-403-g5ab23063f) |
| Verilator | 5.053 (devel, v5.052-22-g7cf8c5cca) |
| icepack, icebram, icemulti, iceprog | Los de OSS CAD Suite |
| Compilador de C (gemelo digital) | gcc 15.2.0 |
| Python | 3.11.6 en la máquina del grupo |

No se necesitan herramientas de RISC-V: el ensamblador es propio. El informe necesita LaTeX; si no está, la integración continua compila el PDF.

**Ensamblar.**

```bash
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex      # R0, o make asm
make fondo-hex                                            # R1 y R2
python3 tools/c1/generar.py --check                       # R3: sw/c1.s y sw/c1_tabla.hex al día
```

La sintaxis del ensamblador y sus extensiones están en `docs/ensamblador.md`; sus tests, en `make test-asm`.

**Testbenches.** El oficial, sin modificar, con los comandos de su encabezado (diseño por defecto, R0):

```bash
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex
iverilog -g2012 -s tb_proyecto_4 -o /tmp/tb_p4 $(yosys-config --datdir)/ice40/cells_sim.v rtl/*.v rtl/espino_core/*.v tb/tb_proyecto_4.sv
vvp -n /tmp/tb_p4
```

| Comando | Qué prueba |
|---------|-----------|
| `make check` | Ensamblador, referencia y testbench oficial de R0 |
| `make equiv` | R0 contra la referencia, byte a byte |
| `make check-fondo HW=r2` | R1 o R2, versión corta de la puerta |
| `make c1-oficial` | El testbench oficial con R3 |
| `make check-c1` | R3, versión corta (la de la integración continua) |
| `make c1-puerta` | Las cuatro puertas de R3 completas; necesita los datos de `$P4_DATOS` |

**Referencia en Python.**

```bash
python3 ref/trader.py data/practica_meta.csv              # banda 40 (R0) contra no operar y comprar y mantener
python3 ref/fondo.py data/practica_meta.csv -o build/ref_fondo.csv   # R1 y R2
python3 ref/c1/c1.py data/practica_meta.csv               # C1 (R3); con --placa, lo que muestran los 7 segmentos
make c1-generar                                           # recalcula las tablas desde el modelo (unos 10 minutos)
```

**Sintetizar y programar la placa.**

```bash
cd bitstreams && sha256sum -c SHA256SUMS && cd ..   # en Mac: shasum -a 256 -c SHA256SUMS
iceprog bitstreams/r0_banda40.bin                   # R0, una imagen
iceprog -b bitstreams/r2_banda40_multi.bin          # R2 con R0 de respaldo
iceprog -b bitstreams/r3_c1_multi.bin               # R3 con R0 de respaldo
```

Los archivos `_multi` llevan dos imágenes y se graban con `iceprog -b`, que borra la flash entera. `iceprog` termina con "VERIFY OK". En Mac, `iceprog` de OSS CAD Suite ve la placa directo por USB. En WSL hay que pasarla primero desde una PowerShell de Windows como administrador: `usbipd list` (la Go Board es un FTDI 0403:6010), `usbipd bind --busid X-Y` una vez y `usbipd attach --wsl --busid X-Y` cada vez que se conecta (`docs/autoprueba.md`, sección 5).

Para construir desde las fuentes: `make bin` (R0), `make r0-reproducir` (R0 byte por byte igual al guardado), `make fondo-bitstreams` (R1 y R2) y `make c1-bitstreams` (R3 desde su molde con `icebram`). Antes de grabar algo nuevo se simula lo que se graba: `make sim-bitstream`.

**Cifras del informe.** `make report` rehace `informe/generado/` desde las referencias y `docs/mediciones/`, y compila el PDF si hay LaTeX. El examen de C1 y la exploración se reproducen en la rama `minutos-reales` (`docs/exploracion_ideas.md`, sección 15.13) y necesitan los minutos reales de `$P4_DATOS`, que no están en el repositorio.

## 11. Estado y límites

- **R3 corrió con la maestra real el 25/11, solo a 10 ms.** En Meta y Tesla dio exactamente lo que da la simulación de C1 (22 682 y 21 224). En AMD dio 8 315 con una sola orden, lejos de los 27 199 de C1 y de los 26 470 de la banda 40, y la causa no está explicada (mala conexión o un bitstream distinto, sin comprobar). La prueba la hizo uno de nosotros sin el medidor del SPI, sin hash anotado y sin leer la placa en esa ronda, así que no hay con qué separar las hipótesis. R2 había corrido con la maestra real el 18/11, con la banda 60. Pasos y regla de decisión: `docs/checklist_25nov.md` y `docs/c1_dia_de_prueba.md`.
- **Qué peldaño compite no está decidido.** La regla del 21/11 pide que la caja y el patrimonio de la placa calcen con la pantalla de la maestra en las rondas leídas, y si no, compite la banda 40. La ronda de AMD no calzó.
- **Siguen sin verificar el SCLK ni los ritmos de 1 ms y 0,1 ms.** Son los que más exigen a R3, que responde en hasta 916 ciclos y se queda sin tiempo antes que R2 si el SCLK es lento: en simulación a 0,1 ms funciona con 200 kHz y falla con 100 kHz; entre esos dos no hay casos simulados. El medidor del SPI es el primer paso del día de prueba y el 25/11 no se usó; con menos de 150 kHz compite la banda 40 (`docs/c1_dia_de_prueba.md`, sección 2.2).
- **La banda 40 en R2 queda como respaldo.** Si la cuenta emulada que muestran los 7 segmentos no calza con la pantalla de la maestra, compite la banda 40.
- **C1 supone caja 10 000, comisión 5 y una ronda de 20 000 ticks desde el encendido.** Si cambian, el candado se decide con una cuenta equivocada. Se reconecta el USB antes de cada ronda; sin eso, desde la segunda ronda R3 decide la banda 40.
- **La memoria del programa está al 94 %** (482 de 512 palabras). Los recortes posibles están documentados sin aplicar (`docs/c1_plan.md`, sección 10).
- **La autoprueba de la placa no ejercita la apuesta de la fase A:** su caminata tiene volatilidad alta y la tabla nunca apuesta. Lo cubren la simulación y, desde el 25/11, la maestra real en Meta.
- **La telemetría solo se actualiza cuando llega un precio** (decisión T153, resuelta: se deja así).
- Con la serie de práctica antigua (`tb/practica.csv`, de 72 a 190, sin normalizar), que es la que usa el testbench oficial por defecto, R3 pasa a modo seguro al primer precio bajo 100 y termina en 9 729 (`docs/mediciones/c1/oficial.txt`).
- Las fuentes del examen de C1 están en la rama `minutos-reales`, que no está integrada en esta.

## 12. Mapa del repositorio

| Carpeta | Contenido |
|---------|-----------|
| `rtl/` | Pochoco SoC, Espino base, segmentado y barrel, extensión de la ISA, tablas, vigilante, medidor y autopruebas |
| `sw/` | `trade.s` (R0), `fondo.s` (R1 y R2), `c1.s` y `c1_tabla.hex` (R3, generados por `tools/c1/generar.py`) y programas de prueba |
| `tb/` | Testbench oficial y serie de práctica del curso (sin modificar) y testbenches propios |
| `ref/` | Referencias en Python (`trader.py`, `fondo.py`, `c1/`), mercado de la maestra, series sintéticas y gemelo digital en C |
| `tools/` | Ensamblador, generadores, equivalencia, co-simulación y mediciones |
| `bitstreams/` | Bitstreams de cada peldaño con su hash, moldes para `icebram` y su `README.md` |
| `formal/` | Verificación formal del Espino base, del barrel y de la extensión |
| `asic/` | Edición ASIC del barrel (GF180MCU) |
| `docs/` | Enunciado, estado, decisiones, documentos de estudio y mediciones |
| `informe/` | Informe en LaTeX; `informe/generado/` lo rehace `make report` |

**Documentos clave.** `docs/defensa/c1.md` (C1 de punta a punta), `docs/c1_plan.md` (diseño de R3), `docs/puertas.md` (las pruebas de cada peldaño), `docs/cotas.md` y `docs/algoritmo.md` (algoritmos), `docs/espino_barrel.md`, `docs/espino_segmentado.md` y `docs/extension_isa.md` (hardware), `docs/codiseno.md` (punto 3.3), `docs/decisiones.md` (todas las decisiones con sus alternativas), `docs/estado.md` (avance) y `docs/defensa/` (banco de preguntas y plan de estudio).

**Mapa de memoria del SoC.**

| Dirección | Registro | Uso |
|-----------|----------|-----|
| `0x0000_0000` | RAM unificada de 512 palabras | Instrucciones y datos |
| `0x8000_0000` | Displays de 7 segmentos | Escritura |
| `0x8000_0004` | LEDs | Escritura |
| `0x8000_0008` | Interruptores | Lectura |
| `0x8001_0000` | `STATUS` del SPI | Bit 0: hay un precio nuevo. Bit 1: `CS_n` activo |
| `0x8001_0004` | `PRICE` | Último precio; leerlo baja la bandera |
| `0x8001_0008` | `DECISION` | Byte que la maestra lee en la transacción siguiente |
| `0x8002_0000` | Tabla de solo lectura (R1 a R3) | Parámetros y, en R3, las tablas de C1 |

![Arquitectura del Pochoco SoC](docs/pochoco_soc.svg)

**Autores.** Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

**Crédito.** El punto de partida es el repositorio base del curso, [nic0villegasc/pochoco_soc](https://github.com/nic0villegasc/pochoco_soc), de Nicolás Villegas, importado sin cambios desde su commit `33e8b5a` (etiqueta `base-curso`). Sus archivos conservan su encabezado de autor y su licencia (Solderpad Hardware License 0.51); cuando modificamos uno, lo indicamos bajo el encabezado original. `tb/tb_proyecto_4.sv` y `tb/practica.csv` son del curso y no se modifican. El ensamblador `tools/pochoasm.py`, el reset largo y el método de comparar trazas vienen de nuestros Proyectos 2 y 3.
