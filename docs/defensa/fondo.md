# El fondo en un chip: supervisor, gestores, memoria compartida y degradación

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio para la defensa. Resume y ordena `docs/fondo.md`, que es la fuente completa (con el protocolo de memoria compartida en su sección 3). Es el programa que compite en R1 y R2: `sw/fondo.s`, con su referencia `ref/fondo.py`. Cifras de `docs/mediciones/fondo/r1/` (R2 da lo mismo; sus salidas están en `fondo/r2/`).

## 1. Qué problema resuelve, y qué no

El barrel tiene cuatro hilos. Con un solo programa (`sw/trade.s`) tres hilos quedan ociosos y el core es el más lento de los tres (`docs/defensa/barrel.md`, sección 6). El fondo les da trabajo: **un supervisor y tres gestores**, como un fondo de inversión con tres analistas y un jefe que vota.

Lo que **no** resuelve: no gana más patrimonio. Según la factibilidad, contra `max_media` sola suma +0,007 puntos esperados a 2 000 ticks y -0,005 a 20 000, y agrega riesgo de falla en vivo. Compite por la decisión T50 de Nicolás ("opción b, tomemos riesgos"), tomada a sabiendas, por lo que representa como co-diseño (`docs/decisiones.md`, T50). Hay que decirlo así en la defensa.

## 2. Qué calcula

**Cada gestor** (hilos 1, 2 y 3) corre la regla de `sw/trade.s` con su media exponencial (alfa 1/32) y su posición, con otros umbrales:

| Hilo | Gestor | Entra si el precio está bajo su media más de | Sale si |
|------|--------|----------------------------------------------|---------|
| 1 | `max_media` | 3 unidades | vuelve a la media |
| 2 | `base` | 4 unidades | vuelve a la media |
| 3 | `activo` | 2 unidades | queda medio punto sobre la media |

Son tres bandas de la misma regla, centradas en `max_media`. Cada gestor lleva además un **puntaje en papel**: lo que habría ganado por acción operando solo (32 veces el cambio de precio mientras tiene la acción, menos 2 por cada cambio de posición).

**El supervisor** (hilo 0):

- Es **el único que toca el SPI**: lee `PRICE` y escribe `DECISION`.
- Publica el precio con el número de tick en una sola palabra.
- **Calcula su propia `max_media`** en todos los ticks: es su respaldo.
- Recoge los tres votos y suma los pesos de los gestores que votan adentro. Con 8/16 o más escribe `0x7F` (comprar 63); si no, `0xBF` (vender 63). Pesos iniciales 6/5/5.
- Cada 512 ticks pasa 1/16 de peso del gestor que menos ganó al que más ganó, con tope y piso alrededor del peso inicial.

Las órdenes son idempotentes: la maestra recorta la compra a lo que alcanza y la venta a lo que se tiene. El programa no lleva contabilidad.

## 3. El tick, paso a paso, en el código

| Paso | Hilo | Dónde |
|------|------|-------|
| Tabla de arranque: el hilo t salta a su rutina | todos | `sw/fondo.s:157` a `:160` |
| Sondea `STATUS` y lee `PRICE` | 0 | `sw/fondo.s:188` a `:192` |
| `PUB = tick * 256 + precio`, en un solo store | 0 | `sw/fondo.s:197` a `:199` |
| `max_media` propia: `devk`, dos comparaciones, `or`, `and`, `emad` | 0 | `sw/fondo.s:202` a `:209` |
| Espera que `PUB` cambie | 1 a 3 | `sw/fondo.s:401` a `:403` |
| Puntaje en papel y regla de reversión, sin saltos | 1 a 3 | `sw/fondo.s:410` a `:426` |
| Publica el puntaje (`DES_k`) y después el voto con su tick (`EST_k`) | 1 a 3 | `sw/fondo.s:430` y `:434` |
| Actualiza su media con `emad` | 1 a 3 | `sw/fondo.s:438` |
| Lee los tres votos, con plazo | 0 | `sw/fondo.s:216` a `:228` |
| Si vence el plazo, reemplaza cada voto viejo por su `max_media` | 0 | `sw/fondo.s:230` a `:245` |
| Voto ponderado y **una sola** escritura en `DECISION` | 0 | `sw/fondo.s:252` a `:266` |
| Un store de telemetría (7 segmentos o LED) | 0 | `sw/fondo.s:268` a `:297` |
| Cada 512 ticks: ajuste de pesos | 0 | `sw/fondo.s:308` |

La rutina de los gestores es una sola (`sw/fondo.s:385`), reentrante: cada hilo tiene sus registros y su bloque de memoria con la base en `x2`.

## 4. Protocolo de memoria compartida

**Regla: cada palabra tiene un solo hilo que la escribe.** El testbench lo vigila en todas las corridas.

| Palabra | Dirección | La escribe | La leen |
|---------|-----------|------------|---------|
| `PUB` (tick y precio) | `0x7C0` | Supervisor | Los tres gestores |
| `W1` a `W3` (pesos), `REF1` a `REF3` (puntaje al empezar la ventana) | `0x7C4` a `0x7D8` | Supervisor | Supervisor |
| `DES_k` (puntaje) | `0x7DC`, `0x7E4`, `0x7EC` | Gestor k | Supervisor, solo en la frontera |
| `EST_k` (voto: tick en los bits 31:8 y posición en el bit 0) | `0x7E0`, `0x7E8`, `0x7F0` | Gestor k | Supervisor |
| Tabla de parámetros | `0x8002_0000` | Nadie (sin puerto de escritura) | Los cuatro |

Definidas en `sw/fondo.s:137` a `:154`.

**Cómo se detecta un voto viejo, sin bit de "listo".** El supervisor resta a `EST_k` su número de tick por 256. Si el gestor ya publicó este tick, la resta da 0 o 1, que es la posición. Si es de otro tick, mirada sin signo da 2 o más. Con un `or` de las tres restas y un `sltiu` contra 2 sabe si llegaron los tres (`sw/fondo.s:216` a `:225`). Un bit de "listo" habría que borrarlo, y entonces dos hilos escribirían la misma palabra.

**Por qué no hay carreras.** Tres hechos del barrel: (1) rotación fija, un acceso a memoria por ciclo en orden total; (2) un store escribe la palabra completa en un flanco; (3) dentro de un hilo los stores llegan en orden de programa. De ahí: un gestor nunca ve un precio con el tick de otro (van en la misma palabra); el supervisor nunca usa un voto viejo (lo compara con su tick); cuando lee `DES_k` es el de este tick (el gestor lo escribe antes que `EST_k`, y el supervisor solo lo lee después de ver los tres `EST_k` frescos). No hay bloqueo mutuo: el supervisor solo espera el plazo y el gestor solo espera `PUB`.

Con los gestores sanos, **la decisión no depende de cuántos ciclos demora cada hilo**, solo de los valores. Por eso la referencia en Python no modela ciclos y coincide byte a byte.

## 5. Degradación: qué pasa si un hilo se cuelga

**Un gestor colgado.** El lazo de lectura de votos tiene 12 instrucciones (48 ciclos) y da a lo más `PLAZO` vueltas (8, leído de la tabla). Si al final falta un voto:

1. El voto viejo se reemplaza por la `max_media` propia del supervisor (`sw/fondo.s:230` a `:241`).
2. No se ajustan los pesos, aunque sea tick de frontera.
3. El voto y `DECISION` siguen igual.

La decisión **nunca depende de que otro hilo esté vivo**. Sin ningún voto, los bytes son exactamente los de `sw/trade.s`. Con los gestores sanos el lazo da a lo más 3 vueltas de 8 (en 1 122 corridas sanas el plazo no venció nunca).

Probado (`make fondo-degradacion`, `docs/mediciones/fondo/r1/degradacion.txt`): 30 corridas de 20 000 ticks con un gestor en lazo infinito, un voto que nunca llega y un voto atrasado. Decisión esperada en todas, peor caso 679 ciclos, contra el límite de 1131. Las fallas se ponen **en el programa** (`tools/fondo/variante.py`), no forzando señales en el simulador: un gestor colgado de verdad sigue ocupando su turno, como pasaría en la placa (decisión T68).

**El supervisor colgado.** Es la falla que el programa no puede cubrir: nadie escribe `DECISION` y la maestra repite el último byte. En R1 no hay defensa. En R2 la cubre el **vigilante**: al quinto precio seguido sin escritura en `DECISION` reconfigura la FPGA con R0 (`docs/defensa/tabla_vigilante.md`).

## 6. Qué aportan los otros tres hilos si deciden igual que `max_media`

La pregunta incómoda tiene respuesta honesta:

- **En la serie de práctica, nada en los bytes.** El fondo sano escribe los mismos 20 000 bytes que `max_media` (`docs/estado.md`, tramo 10, hallazgo 2).
- **Por qué.** Con los pesos en 6/5/5 la mayoría de 8/16 la define la banda del medio, que es `max_media`. Lo único que separa al fondo de `max_media` es el **ajuste de pesos**: cuando los pesos se alejan de 6/5/5 otra banda puede inclinar el voto.
- **En otras series sí difieren.** En una serie de la familia de reversión el fondo sano y `max_media` difieren en 1816 bytes; con fallas parciales difieren de los dos (`docs/fondo.md`, sección 10). Por eso las pruebas de degradación corren sobre dos series.
- **Lo que sí aportan:** usan los cuatro hilos del barrel y las instrucciones de dos operaciones. El fondo hace 56 operaciones útiles por tick contra 8 de `max_media`: 5,34 MOPS contra 3,92 de R0 (`docs/mediciones/p7/variantes.txt`). Es co-diseño medido, no más patrimonio.

## 7. Mediciones por tick (punto 3.2)

`docs/mediciones/fondo/r1/ticks.txt`, serie de práctica a 0,1 ms:

| Hilo | IC prom. | IC máx. | Ciclos prom. | CPI |
|------|----------|---------|--------------|-----|
| 0, supervisor | 68,59 | 116 | 274,37 | 4,000 |
| Cada gestor | 25 | 25 | 100 | 4,000 |
| Los cuatro, agregado | 143,59 | 191 | 143,59 | 1,000 |

| Respuesta (de `byte_done` a `DECISION`) | Ciclos | Tiempo |
|------------------------------------------|--------|--------|
| Promedio | 223,01 | 8,92 us |
| Peor caso del testbench oficial | 443 | 17,72 us |
| Peor caso barriendo la fase | 444 | 19,6 % de la ronda 3 |
| Peor caso con el plazo agotado | 568 | 25,1 % |
| Peor caso de todo lo medido (voto atrasado 200 ciclos) | 679 | 30,0 % |

El supervisor varía por las vueltas del lazo de votos (2 o 3) y por los ticks de frontera (hasta 47 instrucciones más, 39 ticks de 20 000). Los gestores son de tiempo constante. A 0,1 ms la ocupación del core es 5,74 %: el barrel está casi siempre sondeando.

El fondo responde 3 veces más lento que `max_media` sola en el mismo barrel (223 contra 75 ciclos en promedio). Lo que se ganó con la extensión se gasta en el lazo de votos con plazo y en leer la tabla: es el costo de la degradación.

## 8. Tamaño y reglas

200 palabras de programa y 13 de estado: 213 de 512 (`docs/mediciones/fondo/r1/tamano.txt`). Ninguna constante del algoritmo está en las instrucciones: las 20 salen de la tabla en BRAM (`docs/defensa/tabla_vigilante.md`).

| Regla del enunciado | Cómo se cumple |
|---------------------|----------------|
| El core lee el precio y escribe la decisión | Un hilo lee `PRICE` y escribe `DECISION`; los otros calculan con instrucciones. No hay hardware que decida |
| No guardar series de precios | Guarda cuatro medias, tres puntajes, tres pesos y el último precio por 32 |
| Mismo programa para todas las series | No mide el período ni cambia de modo |

## 9. Preguntas típicas

1. **¿Por qué el supervisor calcula `max_media` si el gestor 1 ya la calcula?** Porque la del gestor 1 llega por memoria y puede no llegar. La del supervisor está en sus registros (`sw/fondo.s:202` a `:209`): es la única que no depende de otro hilo.
2. **¿Qué pasa si un gestor se cuelga?** Su voto queda con un tick viejo; el supervisor lo nota con la resta, espera 8 vueltas y usa su `max_media` en ese lugar (`sw/fondo.s:230`). 30 de 30 corridas de degradación correctas, peor caso 679 ciclos.
3. **¿Y si se cuelga el supervisor?** Nadie escribe `DECISION` y la maestra repite el último byte. En R1 no hay defensa; en R2 el vigilante reconfigura con R0 al quinto precio sin respuesta.
4. **¿Cómo sabe el supervisor que un voto es viejo sin un bit de listo?** El voto lleva el número de tick que el gestor procesó; la resta contra el tick del supervisor da 0 o 1 solo si es fresco (`sw/fondo.s:217` y `:225`).
5. **¿Por qué no hay carreras?** Una palabra, un escritor; un store es atómico; el barrel ejecuta un acceso por ciclo en orden fijo (`docs/fondo.md`, sección 3.5).
6. **¿Qué aportan los otros tres hilos si deciden igual que `max_media`?** En la práctica escriben los mismos bytes. Difieren en otras series (1816 bytes en una de reversión). Lo que los separa es el ajuste de pesos. Aportan co-diseño: 56 operaciones útiles por tick en vez de 8.
7. **¿Por qué el fondo responde más lento si usa cuatro hilos?** Cada hilo avanza una instrucción cada 4 ciclos y el supervisor espera a los otros tres. El barrel reparte el trabajo, no lo acelera para un hilo.
8. **¿Por qué compiten con algo que no suma puntos?** Decisión T50, tomada a sabiendas: +0,007 a 2 000 ticks y -0,005 a 20 000 según la factibilidad. El riesgo está acotado por la escalera: R0 es el respaldo y el árbol de decisión dice cuándo competir con él.
9. **¿Cómo se sabe que las pruebas detectan errores?** 15 controles negativos (13 en el programa, 2 en la tabla), 15 detectados. Uno mostró que una prueba mal elegida no detectaba nada: el margen de la frontera corrido sobre una serie donde el margen nunca decide (`docs/fondo.md`, sección 11).
10. **¿Por qué el puntaje está en treintaidosavos?** Porque `devk` entrega 32 p y la diferencia de dos de esos valores ya es 32 veces el cambio de precio. Es el doble exacto del puntaje de la factibilidad y no cambia ninguna decisión (decisión T63).
