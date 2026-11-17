# El fondo en un chip: `sw/fondo.s`

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz. Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Documento de estudio del programa de competencia del diseño integrado (peldaños R1 y R2 de `docs/puertas.md`). Parte de lo básico y llega al detalle. Todos los números salen de un script de `tools/fondo/` y su salida está guardada en `docs/mediciones/fondo/`. La última sección dice con qué comando se obtiene cada uno.

Las mediciones son las del peldaño R1 (paquete P5): el barrel con `emad`, `devk` y la tabla de parámetros en su BRAM (`docs/tabla_vigilante.md`). En R2, que agrega el vigilante, el programa es el mismo y los ciclos medidos son iguales; sus salidas están en `docs/mediciones/fondo/r2/`. Las del paquete P3, con la tabla todavía en la memoria de datos, quedaron en `docs/mediciones/fondo/p3/`.

## 1. Resumen

`sw/fondo.s` usa los cuatro hilos del Espino barrel (`docs/espino_barrel.md`) con las instrucciones `emad` y `devk` de la extensión (`docs/extension_isa.md`). El hilo 0 es el supervisor: es el único que habla con la maestra. Los hilos 1, 2 y 3 son gestores: cada uno corre la misma regla de reversión con otros umbrales y le entrega su voto al supervisor por memoria compartida. El supervisor combina los votos con pesos que se ajustan según cómo le va a cada gestor, y escribe `DECISION` una vez por tick.

Si un gestor no responde a tiempo, el supervisor decide sin él. Si no responde ninguno, decide solo, y lo que escribe es exactamente lo que escribiría `sw/trade.s`.

| Medición (R1) | Resultado | Salida en `docs/mediciones/fondo/r1/` |
|---------------|-----------|----------------------------------------|
| Hardware | 1029 de 1280 celdas, 13 de 16 BRAM, 10 de 10 semillas a 25 MHz, mínima 51,59 MHz | `timing.txt` |
| Tamaño | 200 palabras de programa y 13 de estado: 213 de 512 (41,6 %). La tabla está en su BRAM | `tamano.txt` |
| Testbench oficial sin modificar (Icarus, 2000 ticks) | 4/4, y `decisiones.csv` idéntico byte a byte al de `ref/fondo.py` | `oficial.txt` |
| Serie de práctica, 20 000 ticks, a 0,1 ms, 1 ms y 10 ms | 4/4 y decisiones idénticas a la referencia en los tres períodos | `equiv.txt` |
| Una serie de 20 000 ticks de cada familia (15) | Bytes, estado interno, telemetría y protocolo idénticos | `equiv.txt` |
| Lote de series sintéticas por el RTL | 1 050 series de 2000 ticks (70 por familia): 2,1 millones de ticks, cero diferencias | `series.txt` |
| Respuesta, de `byte_done` a `DECISION` | 223,01 ciclos en promedio (8,92 µs) | `ticks.txt` |
| Peor caso barriendo la fase (72 fases y un período de 2501 ciclos) | 444 ciclos con el programa sano: 19,6 % del presupuesto de la ronda 3 | `fases.txt` |
| Peor caso con gestores colgados (plazo agotado, 48 corridas) | 568 ciclos: 25,1 %. El límite de la puerta es 1131 | `fases.txt` |
| Degradación | 30 corridas de 20 000 ticks con un gestor colgado, un voto que no llega o un voto atrasado: decisión esperada en todas, peor caso 679 ciclos | `degradacion.txt` |
| Matriz de estrés | 56 de 56 casos: SCLK, tiempos de `CS_n`, reset con la maestra transmitiendo, rondas seguidas y series pegadas en 1 y en 255 | `estres.txt` |
| Controles negativos | 15 errores puestos a propósito, 15 detectados | `controles.txt` |
| Instrucciones por tick | Supervisor 68,59 en promedio y 116 como máximo. Cada gestor 25, siempre | `ticks.txt` |
| Bitstream simulado desde su `.asc` | 2000 ticks idénticos a la referencia en dos series | `../bitstreams.txt` |

R1 y R2 cumplen los ocho criterios de la puerta de simulación. Detalle en `docs/puertas.md`.

## 2. Qué calcula

Es la configuración `fondo_min` que midió la factibilidad, sin cambios en lo que decide (decisión T63), más la degradación (T64). Con el precio p que acaba de llegar:

**Cada gestor**, con su media exponencial S (alfa 1/32, guardada por 32) y su posición (0 en caja, 1 comprado):

| Hilo | Gestor | Entra si | Sale si |
|------|--------|----------|---------|
| 1 | `max_media` | el precio está más de 3 unidades bajo su media | vuelve a quedar sobre la media |
| 2 | `base` | más de 4 bajo su media | vuelve a quedar sobre la media |
| 3 | `activo` | más de 2 bajo su media | queda más de medio punto sobre la media |

Los tres usan la regla de `sw/trade.s` (`docs/trade_s.md`): `dev = 32 p - S`, y `pos = (pos | dev < entra) & (dev < sale)`, sin saltos. Son tres bandas de la misma regla, centradas en `max_media`.

**Puntaje simulado de cada gestor.** Es lo que habría ganado por acción si hubiera operado solo: suma 32 veces el cambio de precio mientras tiene la acción y resta 2 cada vez que su posición cambia. Está en treintaidosavos de unidad de precio, así que ese 2 es una comisión de 1/16. No hay productos.

**Supervisor: pesos.** Tiene un peso por gestor, en dieciseisavos, que parte en 6/5/5. Cada 512 ticks compara cuánto subió el puntaje de cada gestor en la ventana y pasa 1/16 del que menos ganó al que más ganó, siempre que la ventaja supere 1/32 del precio y ningún peso se aleje más de 4/16 de su valor inicial.

**Supervisor: voto.** Suma los pesos de los gestores que votan comprar. Con 8/16 o más escribe `0x7F` (comprar 63) y si no `0xBF` (vender 63). Las dos órdenes son idempotentes: la maestra recorta la compra a lo que alcanza y la venta a lo que se tiene, así que el programa no necesita saber cuánto tiene.

**Supervisor: `max_media` propia.** En todos los ticks el supervisor calcula además la regla de `max_media` con su propia media. No la usa mientras lleguen los tres votos. Es su respaldo.

## 3. Protocolo de memoria compartida

### 3.1 Qué palabra escribe cada hilo

| Palabra | Dirección | La escribe | Cuándo | La leen | Contenido |
|---------|-----------|------------|--------|---------|-----------|
| `PUB` | `0x7C0` | Supervisor | Una vez por tick, apenas lee el precio | Los tres gestores | Número de tick en los bits 31:8 y precio en los bits 7:0 |
| `W1`, `W2`, `W3` | `0x7C4` a `0x7CC` | Supervisor | Al arrancar y en la frontera de ventana | Supervisor | Pesos vigentes, en dieciseisavos |
| `REF1`, `REF2`, `REF3` | `0x7D0` a `0x7D8` | Supervisor | En la frontera de ventana | Supervisor | Puntaje de cada gestor al empezar la ventana |
| `DES_k` | `0x7DC`, `0x7E4`, `0x7EC` | Gestor k | Una vez por tick, antes que `EST_k` | Supervisor, solo en la frontera | Puntaje simulado del gestor |
| `EST_k` | `0x7E0`, `0x7E8`, `0x7F0` | Gestor k | Una vez por tick, lo último que publica | Supervisor | El voto: número del tick que el gestor procesó en los bits 31:8 y su posición en el bit 0 |
| Tabla de parámetros | `0x8002_0000`, en su BRAM | Nadie: no tiene puerto de escritura | | Los cuatro hilos | Sección 5 |

Cada palabra tiene un solo hilo que la escribe. El único hilo que toca el esclavo SPI y el periférico de la placa es el supervisor. El testbench vigila las dos cosas en todas las corridas: cualquier store fuera de esta tabla, o hecho por un hilo que no es el dueño, cuenta como violación (sección 7).

### 3.2 Un tick

```
Supervisor (hilo 0)                          Gestor k (hilos 1, 2 y 3)
-------------------                          -------------------------
sondea STATUS hasta ver el precio            sondea PUB hasta que cambie
lee PRICE
PUB = tick * 256 + precio   ------------->   ve PUB distinto del último que procesó
calcula su propia max_media                  puntaje simulado y regla de reversión
lee EST_1, EST_2 y EST_3 en un lazo  <-----  DES_k = puntaje
hasta que los tres traigan este tick,        EST_k = tick * 256 + posición
o hasta que venza el plazo                   actualiza su media y vuelve a sondear PUB
(cada 512 ticks: ajusta los pesos)
voto ponderado
escribe DECISION
escribe un registro de telemetría
vuelve a sondear STATUS
```

- **Cómo se publica el precio.** El precio y el número de tick van juntos en una palabra y se escriben con un solo store. Un gestor nunca ve un precio con el número de otro tick.
- **Cómo espera un gestor.** Con un lazo de dos instrucciones (`lw` y `beq`) hasta que `PUB` sea distinta de la última que procesó. Como el número de tick cambia siempre, `PUB` cambia aunque el precio se repita.
- **Cómo vota.** Primero guarda el puntaje en `DES_k` y al final el voto en `EST_k`, que lleva su número de tick.

### 3.3 Cómo se detecta un voto viejo

El supervisor lee `EST_k` y le resta su número de tick por 256 (que ya tiene en un registro). Si el gestor ya publicó este tick, la resta da 0 o 1, que es la posición. Si el voto es de cualquier otro tick, la diferencia en los bits altos no es cero y el resultado, mirado sin signo, es 2 o más. Entonces:

```
    lw   x5, EST1(x0)
    sub  x5, x5, x3        # 0 o 1 si es de este tick; 2 o más si es viejo
```

Para saber si llegaron los tres basta un `or` de las tres restas y un `sltiu` contra 2. Si los tres son frescos, las tres restas ya son los votos y quedan en los registros.

Un gestor que nunca votó tiene `EST_k` en cero, que también da 2 o más para cualquier tick desde el 1. El número de tick tiene 24 bits (16,7 millones de ticks, 28 minutos a 0,1 ms). Al dar la vuelta, durante un solo tick un `EST_k` en cero se vería fresco: es el único caso en que un gestor que nunca votó contaría, y contaría como "en caja".

### 3.4 Degradación: el plazo

El lazo de lectura de votos tiene 12 instrucciones, 48 ciclos por vuelta. El supervisor da a lo más `PLAZO` vueltas (8 en la tabla). Si al terminar la última todavía falta algún voto:

1. Cada voto viejo se reemplaza por la posición de la `max_media` propia del supervisor.
2. No se ajustan los pesos, aunque el tick sea de frontera. La ventana vuelve a empezar.
3. El voto ponderado y la escritura de `DECISION` siguen igual.

Consecuencias:

- La decisión sale siempre. Lo más que puede tardar es el plazo completo.
- Sin ningún voto, los tres se reemplazan por la misma posición y el resultado es `max_media` sola: los mismos bytes que `sw/trade.s`.
- Con uno o dos votos ausentes, el fondo también termina decidiendo como `max_media` casi siempre. No es casualidad: los pesos quedan congelados en 6/5/5, el ausente vota como `max_media`, y con esos pesos la mayoría de 8/16 la define la banda del medio, que es `max_media`. Lo único que separa al fondo sano de `max_media` es el ajuste de pesos (sección 9).
- Un gestor atrasado no se pierde: cuando termina ve el `PUB` siguiente y sigue. Su voto vuelve a contar en cuanto llegue dentro del plazo.

### 3.5 Por qué no hay carreras

El argumento se apoya en tres hechos del barrel (`docs/espino_barrel.md`):

1. **Rotación fija.** En cada ciclo hay una sola instrucción en la etapa de ejecución y los hilos pasan por ella en orden 0, 1, 2, 3. Todos los accesos a la memoria de datos quedan en un orden total, uno por ciclo.
2. **Un load y un store son atómicos.** Un store escribe la palabra completa en un flanco. No existe una palabra a medio escribir.
3. **Dentro de un hilo no hay riesgos.** Los stores de un hilo llegan a la memoria en el orden del programa.

| Propiedad | Por qué se cumple |
|-----------|-------------------|
| Un gestor nunca ve un precio con el número de tick de otro | Van en la misma palabra y se escriben con un solo store (hecho 2) |
| El supervisor nunca usa una posición de un tick anterior | La posición viaja con su número de tick en `EST_k`, y el supervisor lo compara con el suyo antes de usarla |
| Cuando el supervisor lee `DES_k`, es el puntaje de este tick | El gestor escribe `DES_k` antes que `EST_k` (hecho 3). El supervisor solo lee `DES_k` en la frontera, y solo llega a la frontera habiendo visto los tres `EST_k` con el tick en curso (hecho 1). El gestor no vuelve a escribir hasta que cambie `PUB`, y `PUB` la cambia el supervisor |
| No hay lectura, modificación y escritura repartidas entre hilos | Los pesos y los puntajes de referencia solo los usa el supervisor |
| No hay bloqueo mutuo | El supervisor no espera a nadie más que el plazo. El gestor solo espera a `PUB` |

Con los tres gestores sanos, **la decisión no depende de cuántos ciclos demora cada hilo**, solo de los valores. Por eso la referencia en Python no modela ciclos y coincide byte a byte. La excepción es el borde del plazo: un voto que llega justo cuando vence puede entrar o no según el ciclo. Con los gestores sanos el lazo da a lo más 3 vueltas de las 8 (sección 9).

A diferencia de la factibilidad, el supervisor ya no espera a un gestor atrasado más de un tick. Un gestor cuya vuelta completa dure más que el período se salta precios y su media deja de ser la de la referencia. Los gestores de este programa son de tiempo constante (25 instrucciones por tick, sin saltos que dependan del precio), así que eso solo pasa con una falla.

## 4. El programa

`sw/fondo.s`, por bloque (`docs/mediciones/fondo/r1/tamano.txt`):

| Bloque | Palabras |
|--------|----------|
| Tabla de arranque (el hilo t parte en la dirección 4 t) | 4 |
| Supervisor: inicio y primer precio | 17 |
| Supervisor: sondeo del SPI y publicación | 7 |
| Supervisor: `max_media` propia | 11 |
| Supervisor: lectura de votos con plazo | 12 |
| Supervisor: degradación (plazo vencido) | 12 |
| Supervisor: voto y `DECISION` | 15 |
| Supervisor: telemetría | 25 |
| Supervisor: frontera de ventana (pesos) | 47 |
| Entradas de los tres gestores | 15 |
| Rutina común de los gestores | 35 |
| **Programa** | **200** |
| Estado compartido (parte en cero) | 13 |
| **Total** | **213 de 512 (41,6 %)** |

Quedan 296 palabras libres. La tabla de parámetros no ocupa esta memoria. El programa de la factibilidad ocupaba 251: sin el espejo de la cuenta (75 palabras) y con la extensión sobra espacio para la degradación y la telemetría.

Cómo se resolvió lo que el Espino no tiene (la ALU no desplaza y no hay producto ni división):

- **Los tres gestores comparten la rutina.** El código es reentrante: solo usa registros (cada hilo tiene los suyos) y el bloque de memoria cuya dirección está en `x2`. Los umbrales de cada gestor se cargan de la tabla en su entrada.
- **`devk` hace 32 p y la desviación.** `devk x6, x8, x0, 5` deja 32 p (con `rs2 = x0` es un desplazamiento a la izquierda), y `devk x9, x8, x4, 5` deja `32 p - S` en una instrucción. En `sw/trade.s` eso son seis.
- **`emad` actualiza la media.** `emad x3, x6, x3, 5` hace `S = S + (dev >>> 5)`. En `sw/trade.s` son ocho instrucciones y un paso por la memoria para desplazar.
- **El puntaje no multiplica.** 32 p ya está calculado, y "tenía la acción" se aplica como máscara (`sub x7, x0, x12` y `and`).
- **El voto no multiplica.** Cada peso se suma o no con una máscara hecha del voto.
- **La frontera de ventana** elige al mejor y al peor con comparaciones y guarda el desplazamiento del peso de cada uno (0, 4 u 8), así que el ajuste es un load y un store por peso, y el tope y el piso se leen de la tabla con el mismo desplazamiento.
- **La base de la tabla va en `x1`.** El supervisor la carga una vez por tick, después de publicar el precio, y la conserva hasta el voto. Después `x1` vuelve a ser un temporal.

Un gestor ejecuta 25 instrucciones por tick: 23 hasta publicar su voto y 2 después (actualizar la media y volver al lazo). En la factibilidad, sin la extensión, eran 35.

## 5. Tabla de parámetros

El programa no trae ninguna constante del algoritmo en sus instrucciones. Todas salen de 20 valores de 16 bits en la BRAM de la tabla (`rtl/pochoco_tabla.v`, `0x8002_0000`), en el mismo orden que `PARAMETROS` de `ref/fondo.py` (`python3 ref/fondo.py --tabla` los imprime). El contenido es `sw/fondo_tabla.hex`.

| Desplazamiento | Nombre | Valor | Qué es |
|----------------|--------|-------|--------|
| 0, 4 | `S_ENTRA`, `S_SALE` | -96, 1 | `max_media` del supervisor: entra si `dev < -96`, sale si `dev >= 1` |
| 8, 12 | `G1_ENTRA`, `G1_SALE` | -96, 1 | Gestor 1 |
| 16, 20 | `G2_ENTRA`, `G2_SALE` | -128, 1 | Gestor 2 |
| 24, 28 | `G3_ENTRA`, `G3_SALE` | -64, 17 | Gestor 3 |
| 32 a 40 | `W1_INI` a `W3_INI` | 6, 5, 5 | Pesos iniciales, en dieciseisavos |
| 44 a 52 | `W1_MAX` a `W3_MAX` | 10, 9, 9 | Tope de cada peso |
| 56 a 64 | `W1_MIN` a `W3_MIN` | 2, 1, 1 | Piso de cada peso |
| 68 | `VENTANA` | 512 | Ticks entre ajustes de los pesos |
| 72 | `UMBRAL` | 8 | Compra si los pesos de los votos de compra suman esto o más |
| 76 | `PLAZO` | 8 | Vueltas del lazo de lectura de votos. Tiene que ser 1 o más |

Los umbrales están en unidades de `dev`, que es el precio por 32. Cada valor tiene que caber en 16 bits con signo: `ref/fondo.py` se niega a generar una tabla que no cumpla, o con `PLAZO` en cero.

La tabla es de solo lectura: el módulo no tiene puerto de escritura, y el testbench cuenta cualquier store a esa dirección como violación. Se cambia dentro de un bitstream ya construido con `icebram`, sin sintetizar ni ensamblar (`docs/tabla_vigilante.md`, sección 3).

El programa no toma ningún valor inicial de su imagen de memoria. Los pesos vigentes los copia el supervisor de la tabla al arrancar y todo lo demás parte en cero.

## 6. Telemetría

Un store por tick, siempre después de escribir `DECISION`, así que no alarga la respuesta (decisión T66):

| Tick | Registro | Qué muestra |
|------|----------|-------------|
| Par | 7 segmentos | `63` si la orden es comprar, `00` si es vender: la posición objetivo |
| Impar | LED | LED 0: latido, el bit 10 del número de tick. LED 1, 2 y 3: los votos de los gestores 1, 2 y 3 tal como entraron a la suma |

El latido cambia cada 1024 ticks: 0,1 s en la ronda 3, 1 s en la ronda 2 y 10 s en la ronda 1. Si un voto fue reemplazado por el plazo, su LED muestra el reemplazo. Un LED de voto queda apagado si el peso de ese gestor es cero, cosa que con los pisos de la tabla no ocurre.

El testbench comprueba en cada tick que haya a lo más un store al periférico y que los LED y los segmentos valgan lo que predice la referencia.

## 7. Referencia y equivalencia

La referencia es `ref/fondo.py`. Modela los valores, no los ciclos: por cada precio que el programa ve calcula los tres gestores, la `max_media` del supervisor, la frontera y el voto, y entrega el byte que queda en `DECISION`. Los precios que llegan durante el reset de encendido no se ven (2 a 0,1 ms y 1 a 1 ms y a 10 ms), igual que en `ref/trader.py`.

Qué respalda a la referencia (`make test-fondo`, 7 pruebas):

- Da los números que la factibilidad midió con su módulo en C para `fondo_min`: 26 070 de patrimonio con 630 órdenes y pesos finales 7/6/3 tras 20 cambios en la práctica a 0,1 ms, y lo mismo en otras cuatro corridas.
- Una segunda escritura del fondo, hecha aparte y con la aritmética de la factibilidad (puntaje en dieciseisavos, media con `(S + 31) >> 5`), da los mismos bytes, pesos, puntajes y medias en 19 series.
- Sin ningún voto, los bytes son los de `ref/trader.py`.
- La tabla del programa es la de la referencia, palabra por palabra.

Cómo se compara el RTL con ella. `tb/fondo/tb_fondo.sv` es la maestra SPI de `tb/tb_estres.sv` (misma transacción y misma medición que el testbench oficial) más la observación del barrel. `tools/fondo/revisar.py` comprueba en cada corrida:

1. **Bytes.** Cada byte que leyó la maestra es el de la referencia.
2. **Estado en el momento de decidir, tick a tick.** El byte escrito, la palabra `PUB`, los tres pesos y, de cada gestor cuyo voto llega, el voto y el puntaje. También que el plazo venció exactamente en los ticks en que la referencia dice que faltó un voto. El flujo de bytes solo toma dos valores, así que un error en un puntaje podría no verse en los bytes por miles de ticks: por eso se compara el estado.
3. **Telemetría.** A lo más un store al periférico por tick, y los LED y los segmentos con el valor esperado.
4. **Protocolo.** Llegaron todos los precios, cada uno tuvo una sola escritura en `DECISION`, MISO sin X, ninguna palabra escrita por un hilo que no es su dueño, y peor caso bajo el límite.

Resultados (`docs/mediciones/fondo/r1/equiv.txt` y `series.txt`; los de R2 son iguales):

| Prueba | Resultado |
|--------|-----------|
| Testbench oficial sin modificar, Icarus, 2000 ticks | 4/4. `decisiones.csv` idéntico (patrimonio 9 661, 74 órdenes) |
| Copia parametrizada del oficial, práctica completa a 0,1 ms | 4/4, 20 000 filas idénticas, patrimonio 26 070 |
| Lo mismo a 1 ms y a 10 ms | 4/4, 20 000 filas idénticas, patrimonio 25 031 |
| `tb_fondo.sv`, práctica completa a los mismos períodos | Bytes, estado, telemetría y protocolo idénticos |
| `tb_fondo.sv`, una serie de 20 000 ticks de cada una de las 15 familias | Idénticos |
| `tb_fondo.sv`, 1 050 series de 2000 ticks | 1 050 de 1 050 idénticas: 2,1 millones de ticks |

El patrimonio de la práctica cambia entre 0,1 ms y 1 ms porque el programa deja de ver 2 precios o 1 durante el reset, igual que con `sw/trade.s`.

Cuando se midió esto (P3) el gemelo digital todavía no modelaba el barrel, así que todo corre por el RTL con Verilator. Desde P4 el gemelo sí lo modela y repitió las series a 1 ms y 10 ms (`docs/gemelo.md`, sección 7). Las series sintéticas no se corrieron a 1 ms ni a 10 ms (decisión T67). El criterio 8, el bitstream simulado desde su `.asc`, está en `docs/tabla_vigilante.md`, sección 6.

## 8. Mediciones por tick

`docs/mediciones/fondo/r1/ticks.txt`. Serie de práctica completa con el timing del testbench oficial. Una ventana va de un `byte_done` al siguiente. "Trabajo" son las instrucciones fuera de los lazos de sondeo (`STATUS` para el supervisor, `PUB` para los gestores), más la vuelta del lazo que encuentra el dato.

### 8.1 Instrucciones, ciclos y CPI por hilo (ronda 3, 19 996 ticks)

| Hilo | IC mínimo | IC promedio | IC máximo | Ciclos promedio | Ciclos máximo | CPI |
|------|-----------|-------------|-----------|-----------------|---------------|-----|
| 0, supervisor | 62 | 68,59 | 116 | 274,37 | 464 | 4,000 |
| 1, gestor `max_media` | 25 | 25,00 | 25 | 100,00 | 100 | 4,000 |
| 2, gestor `base` | 25 | 25,00 | 25 | 100,00 | 100 | 4,000 |
| 3, gestor `activo` | 25 | 25,00 | 25 | 100,00 | 100 | 4,000 |
| Los cuatro, agregado | 137 | 143,59 | 191 | 143,59 | 191 | 1,000 |

En el barrel cada hilo completa una instrucción cada 4 ciclos, sin excepciones: no hay esperas por loads ni penalización por saltos. El CPI es 4 por hilo y 1 agregado, por construcción, y los ciclos de un hilo son 4 veces su IC. En la fila agregada los ciclos son los del core entero, que ejecuta una instrucción por ciclo.

Los gestores no tienen saltos que dependan del precio: su peor caso es su promedio. El supervisor varía por dos razones: cuántas vueltas da el lazo de lectura de votos (2 o 3) y si el tick es de frontera (hasta 47 instrucciones más).

En términos de la ley de hierro (Tiempo = IC × CPI × Tclk), contra `max_media` en un hilo del mismo barrel: el IC del camino de la respuesta sube, el CPI por hilo sigue en 4 y el reloj no cambia. Lo que el barrel aporta es que las 75 instrucciones de los tres gestores se ejecutan mientras el supervisor hace las suyas: en el camino de la respuesta cuestan lo que 23 de un solo hilo.

### 8.2 Ciclos y tiempo de la respuesta

Ciclos desde `byte_done`, que es desde donde mide el testbench oficial. Ciclo de 40 ns.

| Hito | Mínimo | Promedio | Máximo | Tiempo promedio | Tiempo máximo |
|------|--------|----------|--------|-----------------|---------------|
| El supervisor publica `PUB` | 27 | 30,64 | 35 | 1,23 µs | 1,40 µs |
| Llega el último voto | 122 | 124,36 | 130 | 4,97 µs | 5,20 µs |
| `DECISION`, todos los ticks | 219 | 223,01 | 443 | 8,92 µs | 17,72 µs |
| `DECISION`, ticks comunes | 219 | 222,64 | 227 | 8,91 µs | 9,08 µs |
| `DECISION`, ticks con frontera (39) | 379 | 413,36 | 443 | 16,53 µs | 17,72 µs |

El programa escribe `DECISION` exactamente una vez en cada tick. A 1 ms (3000 ticks) la respuesta es 221,91 ciclos en promedio y 435 en el peor caso: el programa no mide el período y solo cambia en qué fase llega el precio.

### 8.3 Contra el período de cada ronda

Con el peor caso medido barriendo la fase (444 ciclos, sección 9):

| Ronda | Período | Presupuesto (ciclos) | Peor caso | Uso | Holgura |
|-------|---------|----------------------|-----------|-----|---------|
| 1 | 10 ms | 249 762 | 444 | 0,18 % | 99,82 % |
| 2 | 1 ms | 24 762 | 444 | 1,79 % | 98,21 % |
| 3 | 0,1 ms | 2 262 | 444 | 19,63 % | 80,37 % |

Ocupación: los cuatro hilos hacen 143,59 instrucciones de trabajo por tick. A 0,1 ms el core tiene 2500 turnos por tick, así que la ocupación es 5,74 %. El barrel está casi siempre sondeando.

### 8.4 Contra la factibilidad y contra `max_media` sola

| | Factibilidad (`fondo_min`, sin extensión, con espejo) | Este programa en R1 | `max_media` sola (`sw/trade.s`) en el hilo 0 del barrel |
|-|--------------------------------------------------------|---------------------|-------------------------------------------|
| Instrucciones por gestor y por tick | 35 | 25 | no aplica |
| Respuesta promedio | 227,36 ciclos | 223,01 | 75,06 (`docs/mediciones/barrel/ticks.txt`) |
| Peor caso barriendo la fase | 440 | 444 | 88 |
| Memoria | 251 palabras | 213 | 40 |
| Decide si un gestor se cuelga | No | Sí | no aplica |

La respuesta quedó donde estaba en la factibilidad aunque los gestores son más cortos: lo que se ganó con la extensión se gasta en el lazo de lectura con plazo, que lee los tres votos en cada vuelta (48 ciclos), y en leer los parámetros de la tabla. Es el costo de la degradación y de la tabla. En el mismo core, el fondo tarda en responder 3 veces lo que tarda `max_media` sola en promedio (223 ciclos contra 75) y 5 veces en el peor caso (444 contra 88). Sobra plazo, pero es lo que cuesta esperar a tres hilos que avanzan una instrucción cada 4 ciclos.

Un detalle que muestra cuánto pesa la fase: respecto de P3, el supervisor ejecuta una instrucción más antes de leer los votos (cargar la base de la tabla), y la respuesta promedio bajó de 235 a 223 ciclos. Esos 4 ciclos corren la primera lectura lo justo para que los tres votos estén casi siempre en la segunda o tercera vuelta, y ya nunca en la cuarta.

## 9. Peor caso barriendo la fase

`docs/mediciones/fondo/r1/fases.txt`. El peor caso depende de en qué punto de sus lazos está cada hilo cuando llega el precio. El lazo de sondeo del supervisor dura 12 ciclos, el de los gestores 8 y la rotación de hilos 4: el patrón se repite cada 24 ciclos. Se desplazó el inicio de la serie un ciclo a la vez:

| Corridas | Resultado | Peor caso |
|----------|-----------|-----------|
| 48 fases de un ciclo, programa sano, 1100 ticks cada una | 48 de 48 iguales a la referencia | entre 433 y 444 ciclos |
| 24 fases corridas 13 ns (el precio no llega alineado con el reloj) | 24 de 24 | entre 433 y 444 |
| Período de 2501 ciclos, 20 000 ticks (recorre todas las fases en una corrida) | igual a la referencia | 442 |
| Gestor 3 colgado, 24 fases | 24 de 24 | entre 553 y 560 |
| Los tres gestores colgados, 24 fases | 24 de 24, y bytes iguales a `max_media` sola | entre 557 y 568 |

**Peor caso sano: 444 ciclos. Peor caso con el plazo agotado: 568 ciclos**, contra el límite de 1131 (la mitad del presupuesto de la ronda 3). El peor caso de todo lo medido son 679 ciclos, con un gestor atrasado 200 ciclos a propósito (sección 10): el supervisor lo espera casi hasta el plazo y después todavía decide.

Cota por conteo de instrucciones (hecha a mano, no sale de un script): hasta `PUB` pasan a lo más 36 ciclos; la `max_media` propia son 11 instrucciones (44 ciclos); el plazo son 8 vueltas de 48 ciclos (384); el reemplazo de votos y la frontera no ocurren en el mismo tick, y el más largo de los dos es la frontera, con 47 instrucciones más una vuelta del lazo (236); el voto son 15 instrucciones (60). La suma es 760 ciclos. Es una cota razonada, no demostrada, y queda bajo 1131.

Cuántas vueltas da el lazo de lectura con los gestores sanos, en las 1 122 corridas sanas del lote de series y de este barrido: nunca más de 3. El plazo es 8. En ninguna corrida sana venció.

## 10. Degradación

`docs/mediciones/fondo/r1/degradacion.txt`. Cada caso es `sw/fondo.s` con instrucciones insertadas en la rutina de los gestores (`tools/fondo/variante.py`, marcas `#@` del programa). El supervisor no se toca. La decisión esperada sale de `ref/fondo.py` con la misma falla, descrita como "el voto del gestor K no llega entre los ticks N y M" (decisión T68). Cada caso corre 20 000 ticks sobre dos series: la de práctica y una de reversión.

| Falla | Casos | Qué se comprobó |
|-------|-------|-----------------|
| Un gestor en lazo infinito | Cada gestor colgado desde el arranque, cada gestor colgado desde el tick 1500, dos colgados en distintos momentos y los tres colgados | Decisión esperada en todos los ticks. El plazo vence en todos los ticks desde la falla y en ninguno antes. Con los tres colgados los bytes son los de `max_media` sola |
| Un voto que no llega | El gestor 1 en un tick, el gestor 2 en un tick de frontera, el gestor 3 durante 1601 ticks | El plazo vence solo en esos ticks. En la frontera sin voto no se tocan los pesos. Al volver el voto, el fondo sigue como la referencia |
| Un voto atrasado | 160 y 200 ciclos (cabe en el plazo), 1000 ciclos siempre y 1200 ciclos durante 1401 ticks (no cabe) | Si cabe, ninguna decisión cambia y la respuesta crece lo que se atrasó el gestor. Si no cabe, se decide sin ese voto |

Las 30 corridas pasan: bytes, estado, ticks con plazo vencido, telemetría y protocolo iguales a lo esperado, y **peor caso 679 ciclos**.

Por qué dos series. En la serie de práctica el fondo sano, el fondo con fallas y `max_media` sola escriben los mismos 20 000 bytes, así que ahí la prueba solo distingue los casos por el estado interno. En la de reversión el fondo sano y `max_media` difieren en 1816 bytes, y los casos con fallas parciales difieren de los dos (por ejemplo 276 del sano y 1540 de `max_media` con el gestor 3 sin voto entre los ticks 1000 y 2600). La última columna de cada línea de `degradacion.txt` lo informa.

Lo que no se probó: atrasos entre 200 y 600 ciclos, donde el voto llega cerca del plazo y el resultado depende del ciclo exacto. El programa decide bien en cualquiera de los dos casos (con el voto o con el reemplazo), pero la referencia no modela cuál de los dos toca.

## 11. Controles negativos

`docs/mediciones/fondo/r1/controles.txt`. Para saber que las comparaciones de las secciones 7 a 10 ven lo que dicen ver, `tools/fondo/controles.py` arma 15 casos con un error puesto a propósito (13 en el programa y 2 en la tabla, que se carga cambiada) y `make fondo-controles` exige que la comparación falle en todas:

| Error | Lo detecta |
|-------|-----------|
| Otro umbral en la tabla para el gestor 3 | Voto, puntaje, LED y bytes |
| El puntaje descuenta la mitad de la comisión | Puntaje, en el tick 3 |
| La frontera no exige el margen | Pesos |
| La frontera no respeta el tope de un peso | Pesos |
| El voto exige un dieciseisavo más | Byte |
| Plazo de una sola vuelta | Vence con los gestores sanos |
| Vencido el plazo, un voto viejo no se reemplaza | Byte y LED |
| Vencido el plazo, el voto viejo se cuenta como en caja | LED |
| El supervisor no actualiza su propia media | Bytes, con los tres gestores colgados |
| Con un voto ausente en la frontera los pesos se ajustan aun así | Byte y escrituras en `DECISION` |
| El supervisor acepta un voto sin mirar de qué tick es | Plazo y byte, con un gestor atrasado |
| Dos stores de telemetría en un tick | Conteo de stores |
| El latido usa otro bit | LED |
| Un gestor escribe en `PUB` | Vigilancia del protocolo |
| Dos escrituras en `DECISION` | Conteo de escrituras |

15 de 15 detectados. El de "se cuenta como en caja" solo lo delata la telemetría: con los pesos 6/5/5 ese voto no alcanza a cambiar el byte. Y el del margen no se detectaba en la primera versión, que lo corría sobre 6000 ticks de la serie de reversión, donde el margen nunca decide. Sobre la serie de práctica sí. Queda como advertencia: una prueba del ajuste de pesos vale lo que la serie con que se corre y lo que dura. El del tope tampoco se detecta con 3000 ticks, porque ningún peso llega a su tope antes del tick 3072.

## 12. Reglas del enunciado

| Regla | Cumple | Comentario |
|-------|--------|------------|
| "La decisión se debe calcular en el Espino Core en la placa. El core debe leer el precio y escribir la decisión." | Sí | Todo el cálculo son instrucciones ejecutadas por el core: un hilo lee `PRICE` y escribe `DECISION`, y los otros tres calculan y le entregan su voto por memoria. No hay hardware que decida. El profesor confirmó el 16/11 que el Espino multihilo es válido (T126) |
| No usar información externa a la serie ni guardar series de precios | Sí | El programa guarda una media por gestor y una del supervisor, tres puntajes, tres pesos y el último precio por 32. No guarda precios pasados |
| Mismo programa para todas las series | Sí | No mide el período ni cambia de modo |
| Todo hardware agregado con su testbench | Sí | El barrel, la extensión, la tabla y el vigilante tienen cada uno sus pruebas (`docs/espino_barrel.md`, `docs/extension_isa.md` y `docs/tabla_vigilante.md`) |
| El testbench oficial no se modifica | Sí | Entrega 4/4 sin tocarlo |
| Regla propia: nada derivado punto a punto de la serie de práctica | Sí | La tabla tiene 20 constantes: umbrales de tres candidatos del frente del algoritmo, pesos iniciales, ventana, margen implícito de 1/32 y plazo |

## 13. Límites y lo que falta

- **El algoritmo no suma puntos.** Es la decisión T50, tomada a sabiendas: según la factibilidad el fondo empata con `max_media` a 2000 ticks y pierde 0,005 puntos a 20 000. En la serie de práctica, en el testbench a 0,1 ms, escribe los mismos bytes que `max_media` (los dos terminan con 26 070); a 1 ms y 10 ms no: el fondo termina con 25 031 y `max_media` con 26 070 (`docs/mediciones/fondo/r1/equiv.txt` y `docs/mediciones/p7/gemelo.txt`). Viendo todos los precios, `ref/fondo.py` da 26 388 y `ref/trader.py` 25 973.
- **Placa y maestra real.** El 16/11 R2 pasó en la placa la firma a 0,1 ms y la media hora sin disparo, y el relevo se midió en 35,50 ms por la UART (`docs/mediciones/placa_16nov.md`). Faltan la firma de R2 a 1 ms y 10 ms, las tres firmas de R1, ver la imagen testigo después del relevo y la puerta de la maestra (26/11).
- **Gemelo digital.** Desde P4 modela el barrel, la extensión y la tabla; con él se corrieron las series a 1 ms y 10 ms (`docs/mediciones/fondo/r1/gemelo_series.txt`).
- **SCLK lento con el período más corto.** Con SCLK de 100 kHz y período de 0,1 ms quedan 237 ciclos entre transacciones y el fondo necesita hasta 444. A 1 ms funciona (`docs/tabla_vigilante.md`, sección 8).
- **Rondas seguidas sin reset.** El programa no se reinicia entre rondas: medias, puntajes y pesos siguen desde donde quedaron. La matriz de estrés lo ejercita con tres rondas seguidas a períodos distintos y la referencia corrida de corrido: coincide. Lo que no se sabe es si la maestra real reinicia su cuenta entre rondas, que es una pregunta pendiente.
- **Borde del plazo.** Cerca del plazo la decisión depende del ciclo en que llega el voto (sección 10).
- **Vuelta del contador de ticks.** A los 16,7 millones de ticks un gestor que nunca votó contaría como "en caja" durante un tick (sección 3.3). No se ejercitó.
- **Un gestor más lento que el período se salta precios.** El supervisor ya no lo espera. No pasa con gestores sanos (25 instrucciones de 625 turnos por tick a 0,1 ms).
- **Peor caso por análisis.** El de la sección 9 es el máximo observado más una cota razonada, no una demostración.
- **Valores X en la memoria.** Verilator simula con dos estados. La corrida con Icarus, de cuatro estados, cubre 2000 ticks.

## 14. Cómo reproducir

Desde la raíz del repositorio, con OSS CAD Suite en el `PATH` (los scripts lo toman de la variable `OSS_CAD_SUITE` o del `PATH`; no lo agregan por su cuenta).

Todos los objetivos aceptan `HW=r1` (por defecto) o `HW=r2`.

| Comando | Qué hace | Salida en `docs/mediciones/fondo/r1/` | Demora |
|---------|----------|----------------------------------------|--------|
| `make test-fondo` y `make check-tabla` | Pruebas de la referencia y de que la tabla guardada es la de la referencia | | 3 s |
| `make fondo-oficial` | Testbench oficial sin modificar, Icarus | `oficial.txt` | 5 min |
| `make fondo-equiv` | Práctica a 0,1 ms y 1 ms y una serie por familia | `equiv.txt` | 3 min |
| `make fondo-equiv-ronda1` | Lo mismo más el período de 10 ms | `equiv.txt` | 35 min |
| `make fondo-series` | 1 050 series sintéticas | `series.txt` | 15 min |
| `make fondo-timing` | Celdas y frecuencia en 10 semillas | `timing.txt` | 3 min |
| `make fondo-fases` | Peor caso barriendo la fase | `fases.txt` | 2 min |
| `make fondo-degradacion` | 30 corridas con fallas | `degradacion.txt` | 3 min |
| `make fondo-controles` | 15 controles negativos | `controles.txt` | 1 min |
| `make fondo-estres` | Matriz de estrés | `estres.txt` | 3 min |
| `make fondo-ticks` | Mediciones por tick y tamaño | `ticks.txt`, `tamano.txt` | 1 min |
| `make fondo-puerta` | Todo lo anterior, en versión completa | | 50 min |
| `make fondo-bitstreams` y `make fondo-criterio5` | Criterios 8 y 5 (`docs/tabla_vigilante.md`) | | |
| `make check-fondo` | Versiones cortas. Corre en la integración continua, una vez por peldaño | `build/fondo/r1/` | 10 min |

Para correr un caso a mano: `source tools/fondo/comun.sh; ensamblar_fondo; compilar_sim; caso build/fondo/r1/prueba sw/fondo.s tb/practica.csv 2000 100000 4000 --medir; cat build/fondo/r1/prueba/resultado.txt`.

## 15. Preguntas para estudiar

1. **¿Por qué el supervisor calcula `max_media` si el gestor 1 ya la calcula?** Porque la del gestor 1 llega por memoria y puede no llegar. La del supervisor está en sus registros: es la única que no depende de otro hilo. `sw/fondo.s`, bloque 3 del supervisor.
2. **¿Qué pasa si un gestor se cuelga?** Su voto queda con un número de tick viejo. El supervisor lo nota porque la resta contra su tick no da 0 ni 1, espera 8 vueltas, y usa su propia `max_media` en ese lugar. La decisión sale 568 ciclos después del precio en el peor caso medido (564 con el programa de P3), y es la de `max_media`. Sección 10.
3. **¿Cómo sabe el supervisor que un voto es viejo sin un bit de "listo"?** El voto lleva el número del tick que el gestor procesó. Un bit de "listo" habría que borrarlo, y eso serían dos hilos escribiendo la misma palabra. Sección 3.3.
4. **¿Por qué no hay carreras si cuatro hilos comparten la memoria?** Porque cada palabra la escribe un solo hilo, un store es atómico y el barrel ejecuta una instrucción por ciclo en orden fijo. Sección 3.5.
5. **¿Por qué el fondo responde más lento que `max_media` sola si usa cuatro hilos?** Porque cada hilo avanza una instrucción cada 4 ciclos y el supervisor tiene que esperar a los otros tres. El barrel reparte el trabajo, no lo acelera para un hilo. Sección 8.4.
6. **¿Qué gana el fondo con las instrucciones nuevas?** Cada gestor baja de 35 a 25 instrucciones por tick, y el supervisor calcula su `max_media` en 8. Sección 4.
7. **¿Por qué el puntaje está en treintaidosavos?** Porque `devk` entrega 32 p y la diferencia de dos de esos valores ya es 32 veces el cambio de precio. Es el doble exacto del puntaje de la factibilidad. Sección 2 y `ref/test_fondo.py`.
8. **¿Cuánto del resultado es del fondo y cuánto de `max_media`?** En la serie de práctica, todo es de `max_media`: los bytes son los mismos. La diferencia aparece cuando los pesos se alejan de 6/5/5. Secciones 3.4 y 10.
9. **¿Qué se puede cambiar sin volver a ensamblar?** Las 20 palabras de la tabla. Sección 5.
10. **¿Cómo se sabe que las pruebas detectarían un error?** Por los 15 controles negativos, y porque uno de ellos mostró que una prueba mal elegida no detectaba nada. Sección 11.
