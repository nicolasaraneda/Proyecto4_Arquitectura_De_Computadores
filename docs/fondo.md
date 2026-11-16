# El fondo en un chip: `sw/fondo.s`

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz. Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Documento de estudio del programa de competencia del diseño integrado (peldaño R1 de `docs/puertas.md`). Parte de lo básico y llega al detalle. Todos los números salen de un script de `tools/fondo/` y su salida está guardada en `docs/mediciones/fondo/`. La última sección dice con qué comando se obtiene cada uno.

## 1. Resumen

`sw/fondo.s` usa los cuatro hilos del Espino barrel (`docs/espino_barrel.md`) con las instrucciones `emad` y `devk` de la extensión (`docs/extension_isa.md`). El hilo 0 es el supervisor: es el único que habla con la maestra. Los hilos 1, 2 y 3 son gestores: cada uno corre la misma regla de reversión con otros umbrales y le entrega su voto al supervisor por memoria compartida. El supervisor combina los votos con pesos que se ajustan según cómo le va a cada gestor, y escribe `DECISION` una vez por tick.

Si un gestor no responde a tiempo, el supervisor decide sin él. Si no responde ninguno, decide solo, y lo que escribe es exactamente lo que escribiría `sw/trade.s`.

| Medición | Resultado | Salida |
|----------|-----------|--------|
| Hardware | Espino barrel con `emad` y `devk`: 990 de 1280 celdas, 12 de 16 BRAM, 10 de 10 semillas a 25 MHz, mínima 48,92 MHz | `timing.txt` |
| Tamaño | 193 palabras de programa, 20 de tabla y 13 de estado: 226 de 512 (44,1 %) | `tamano.txt` |
| Testbench oficial sin modificar (Icarus, 2000 ticks) | 4/4, peor caso 435 ciclos de 2262, y `decisiones.csv` idéntico byte a byte al de `ref/fondo.py` | `oficial.txt` |
| Serie de práctica, 20 000 ticks, a 0,1 ms, 1 ms y 10 ms | 4/4 y decisiones idénticas a la referencia en los tres períodos | `equiv.txt` |
| Una serie de 20 000 ticks de cada familia (15) | Bytes, estado interno, telemetría y protocolo idénticos | `equiv.txt` |
| Lote de series sintéticas por el RTL | 1 050 series de 2000 ticks (70 por familia): 2,1 millones de ticks, cero diferencias | `series.txt` |
| Respuesta, de `byte_done` a `DECISION` | 235,37 ciclos en promedio (9,41 us) | `ticks.txt` |
| Peor caso barriendo la fase (72 fases y un período de 2501 ciclos) | 480 ciclos con el programa sano: 21,2 % del presupuesto de la ronda 3 | `fases.txt` |
| Peor caso con gestores colgados (plazo agotado, 48 corridas) | 564 ciclos: 24,9 %. El límite de la puerta es 1131 | `fases.txt` |
| Degradación | 30 corridas de 20 000 ticks con un gestor colgado, un voto que no llega o un voto atrasado: decisión esperada en todas, peor caso 671 ciclos | `degradacion.txt` |
| Controles negativos | 15 errores puestos a propósito en el programa, 15 detectados | `controles.txt` |
| Instrucciones por tick | Supervisor 71,59 en promedio y 125 como máximo. Cada gestor 25, siempre | `ticks.txt` |

Criterios de la puerta de simulación que pedía el paquete: 1, 2, 4 y 6, los cuatro cumplidos. También el 3 (timing). Detalle en `docs/puertas.md`.

## 2. Qué calcula

Es la configuración `fondo_min` que midió la factibilidad, sin cambios en lo que decide (decisión T63), más la degradación (T64). Con el precio p que acaba de llegar:

**Cada gestor**, con su media exponencial S (alfa 1/32, guardada por 32) y su posición (0 afuera, 1 adentro):

| Hilo | Gestor | Entra si | Sale si |
|------|--------|----------|---------|
| 1 | `max_media` | el precio está más de 3 unidades bajo su media | vuelve a quedar sobre la media |
| 2 | `base` | más de 4 bajo su media | vuelve a quedar sobre la media |
| 3 | `activo` | más de 2 bajo su media | queda más de medio punto sobre la media |

Los tres usan la regla de `sw/trade.s` (`docs/trade_s.md`): `dev = 32 p - S`, y `pos = (pos | dev < entra) & (dev < sale)`, sin saltos. Son tres bandas de la misma regla, centradas en `max_media`.

**Puntaje en papel de cada gestor.** Es lo que habría ganado por acción si hubiera operado solo: suma 32 veces el cambio de precio mientras tiene la acción y resta 2 cada vez que su posición cambia. Está en treintaidosavos de unidad de precio, así que ese 2 es una comisión de 1/16. No hay productos.

**Supervisor: pesos.** Tiene un peso por gestor, en dieciseisavos, que parte en 6/5/5. Cada 512 ticks compara cuánto subió el puntaje de cada gestor en la ventana y pasa 1/16 del que menos ganó al que más ganó, siempre que la ventaja supere 1/32 del precio y ningún peso se aleje más de 4/16 de su valor inicial.

**Supervisor: voto.** Suma los pesos de los gestores que votan adentro. Con 8/16 o más escribe `0x7F` (comprar 63) y si no `0xBF` (vender 63). Las dos órdenes son idempotentes: la maestra recorta la compra a lo que alcanza y la venta a lo que se tiene, así que el programa no necesita saber cuánto tiene.

**Supervisor: `max_media` propia.** En todos los ticks el supervisor calcula además la regla de `max_media` con su propia media. No la usa mientras lleguen los tres votos. Es su respaldo.

## 3. Protocolo de memoria compartida

### 3.1 Qué palabra escribe cada hilo

| Palabra | Dirección | La escribe | Cuándo | La leen | Contenido |
|---------|-----------|------------|--------|---------|-----------|
| `PUB` | `0x7C0` | Supervisor | Una vez por tick, apenas lee el precio | Los tres gestores | Número de tick en los bits 31:8 y precio en los bits 7:0 |
| `W1`, `W2`, `W3` | `0x7C4` a `0x7CC` | Supervisor | Al arrancar y en la frontera de ventana | Supervisor | Pesos vigentes, en dieciseisavos |
| `REF1`, `REF2`, `REF3` | `0x7D0` a `0x7D8` | Supervisor | En la frontera de ventana | Supervisor | Puntaje de cada gestor al empezar la ventana |
| `DES_k` | `0x7DC`, `0x7E4`, `0x7EC` | Gestor k | Una vez por tick, antes que `EST_k` | Supervisor, solo en la frontera | Puntaje en papel del gestor |
| `EST_k` | `0x7E0`, `0x7E8`, `0x7F0` | Gestor k | Una vez por tick, lo último que publica | Supervisor | El voto: número del tick que el gestor procesó en los bits 31:8 y su posición en el bit 0 |
| Tabla de parámetros | `0x770` a `0x7BC` | Nadie | | Los cuatro hilos | Sección 5 |

Cada palabra tiene un solo hilo que la escribe. El único hilo que toca el esclavo SPI y el periférico de la placa es el supervisor. El testbench vigila las dos cosas en todas las corridas: cualquier store fuera de esta tabla, o hecho por un hilo que no es el dueño, cuenta como violación (sección 7).

### 3.2 Un tick

```
Supervisor (hilo 0)                          Gestor k (hilos 1, 2 y 3)
-------------------                          -------------------------
sondea STATUS hasta ver el precio            sondea PUB hasta que cambie
lee PRICE
PUB = tick * 256 + precio   ------------->   ve PUB distinto del último que procesó
calcula su propia max_media                  puntaje en papel y regla de reversión
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

Un gestor que nunca votó tiene `EST_k` en cero, que también da 2 o más para cualquier tick desde el 1. El número de tick tiene 24 bits (16,7 millones de ticks, 28 minutos a 0,1 ms). Al dar la vuelta, durante un solo tick un `EST_k` en cero se vería fresco: es el único caso en que un gestor que nunca votó contaría, y contaría como "afuera".

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

Con los tres gestores sanos, **la decisión no depende de cuántos ciclos demora cada hilo**, solo de los valores. Por eso la referencia en Python no modela ciclos y coincide byte a byte. La excepción es el borde del plazo: un voto que llega justo cuando vence puede entrar o no según el ciclo. Con los gestores sanos el lazo da a lo más 4 vueltas de las 8 (sección 8).

A diferencia de la factibilidad, el supervisor ya no espera a un gestor atrasado más de un tick. Un gestor cuya vuelta completa dure más que el período se salta precios y su media deja de ser la de la referencia. Los gestores de este programa son de tiempo constante (25 instrucciones por tick, sin saltos que dependan del precio), así que eso solo pasa con una falla.

## 4. El programa

`sw/fondo.s`, por bloque (`docs/mediciones/fondo/tamano.txt`):

| Bloque | Palabras |
|--------|----------|
| Tabla de arranque (el hilo t parte en la dirección 4 t) | 4 |
| Supervisor: inicio y primer precio | 16 |
| Supervisor: sondeo del SPI y publicación | 7 |
| Supervisor: `max_media` propia | 10 |
| Supervisor: lectura de votos con plazo | 12 |
| Supervisor: degradación (plazo vencido) | 12 |
| Supervisor: voto y `DECISION` | 15 |
| Supervisor: telemetría | 25 |
| Supervisor: frontera de ventana (pesos) | 45 |
| Entradas de los tres gestores | 12 |
| Rutina común de los gestores | 35 |
| **Programa** | **193** |
| Tabla de parámetros (solo lectura) | 20 |
| Estado compartido (parte en cero) | 13 |
| **Total** | **226 de 512 (44,1 %)** |

Entre el programa y la tabla quedan 283 palabras libres. El de la factibilidad ocupaba 251: sin el espejo de la cuenta (75 palabras) y con la extensión sobra espacio para la degradación, la telemetría y la tabla.

Cómo se resolvió lo que el Espino no tiene (la ALU no desplaza y no hay producto ni división):

- **Los tres gestores comparten la rutina.** El código es reentrante: solo usa registros (cada hilo tiene los suyos) y el bloque de memoria cuya dirección está en `x2`. Los umbrales de cada gestor se cargan de la tabla en su entrada.
- **`devk` hace 32 p y la desviación.** `devk x6, x8, x0, 5` deja 32 p (con `rs2 = x0` es un desplazamiento a la izquierda), y `devk x9, x8, x4, 5` deja `32 p - S` en una instrucción. En `sw/trade.s` eso son seis.
- **`emad` actualiza la media.** `emad x3, x6, x3, 5` hace `S = S + (dev >>> 5)`. En `sw/trade.s` son ocho instrucciones y un paso por la memoria para desplazar.
- **El puntaje no multiplica.** 32 p ya está calculado, y "tenía la acción" se aplica como máscara (`sub x7, x0, x12` y `and`).
- **El voto no multiplica.** Cada peso se suma o no con una máscara hecha del voto.
- **La frontera de ventana** elige al mejor y al peor con comparaciones y guarda el desplazamiento del peso de cada uno (0, 4 u 8), así que el ajuste es un load y un store por peso, y el tope y el piso se leen de la tabla con el mismo desplazamiento.

Un gestor ejecuta 25 instrucciones por tick: 23 hasta publicar su voto y 2 después (actualizar la media y volver al lazo). En la factibilidad, sin la extensión, eran 35.

## 5. Tabla de parámetros

El programa no trae ninguna constante del algoritmo en sus instrucciones. Todas salen de 20 palabras en `0x770`, en el mismo orden que `PARAMETROS` de `ref/fondo.py` (`python3 ref/fondo.py --tabla` las imprime):

| Dirección | Nombre | Valor | Qué es |
|-----------|--------|-------|--------|
| `0x770`, `0x774` | `S_ENTRA`, `S_SALE` | -96, 1 | `max_media` del supervisor: entra si `dev < -96`, sale si `dev >= 1` |
| `0x778`, `0x77C` | `G1_ENTRA`, `G1_SALE` | -96, 1 | Gestor 1 |
| `0x780`, `0x784` | `G2_ENTRA`, `G2_SALE` | -128, 1 | Gestor 2 |
| `0x788`, `0x78C` | `G3_ENTRA`, `G3_SALE` | -64, 17 | Gestor 3 |
| `0x790` a `0x798` | `W1_INI` a `W3_INI` | 6, 5, 5 | Pesos iniciales, en dieciseisavos |
| `0x79C` a `0x7A4` | `W1_MAX` a `W3_MAX` | 10, 9, 9 | Tope de cada peso |
| `0x7A8` a `0x7B0` | `W1_MIN` a `W3_MIN` | 2, 1, 1 | Piso de cada peso |
| `0x7B4` | `VENTANA` | 512 | Ticks entre ajustes de los pesos |
| `0x7B8` | `UMBRAL` | 8 | Compra si los pesos adentro suman esto o más |
| `0x7BC` | `PLAZO` | 8 | Vueltas del lazo de lectura de votos. Tiene que ser 1 o más |

Los umbrales están en unidades de `dev`, que es el precio por 32. La tabla es de solo lectura: el programa nunca escribe ahí, y el testbench lo vigila. Hoy vive al final de la memoria de datos. El paquete P5 la pasa a una BRAM propia para poder cambiarla con `icebram` sin tocar el programa (decisión T65).

El único estado inicial que el programa toma de la imagen de memoria es esta tabla. Los pesos vigentes los copia el supervisor al arrancar y todo lo demás parte en cero.

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

Resultados (`docs/mediciones/fondo/equiv.txt` y `series.txt`):

| Prueba | Resultado |
|--------|-----------|
| Testbench oficial sin modificar, Icarus, 2000 ticks | 4/4. `decisiones.csv` idéntico (patrimonio 9 661, 74 órdenes) |
| Copia parametrizada del oficial, práctica completa a 0,1 ms | 4/4, 20 000 filas idénticas, patrimonio 26 070 |
| Lo mismo a 1 ms y a 10 ms | 4/4, 20 000 filas idénticas, patrimonio 25 031 |
| `tb_fondo.sv`, práctica completa a los mismos períodos | Bytes, estado, telemetría y protocolo idénticos |
| `tb_fondo.sv`, una serie de 20 000 ticks de cada una de las 15 familias | Idénticos |
| `tb_fondo.sv`, 1 050 series de 2000 ticks | 1 050 de 1 050 idénticas: 2,1 millones de ticks |

El patrimonio de la práctica cambia entre 0,1 ms y 1 ms porque el programa deja de ver 2 precios o 1 durante el reset, igual que con `sw/trade.s`.

El gemelo digital todavía no modela el barrel (paquete P4), así que todo esto corre por el RTL con Verilator. Las series sintéticas no se corrieron a 1 ms ni a 10 ms (decisión T67).

## 8. Mediciones por tick

`docs/mediciones/fondo/ticks.txt`. Serie de práctica completa con el timing del testbench oficial. Una ventana va de un `byte_done` al siguiente. "Trabajo" son las instrucciones fuera de los lazos de sondeo (`STATUS` para el supervisor, `PUB` para los gestores), más la vuelta del lazo que encuentra el dato.

### 8.1 Instrucciones, ciclos y CPI por hilo (ronda 3, 19 996 ticks)

| Hilo | IC mínimo | IC promedio | IC máximo | Ciclos promedio | Ciclos máximo | CPI |
|------|-----------|-------------|-----------|-----------------|---------------|-----|
| 0, supervisor | 61 | 71,59 | 125 | 286,37 | 500 | 4,000 |
| 1, gestor `max_media` | 25 | 25,00 | 25 | 100,00 | 100 | 4,000 |
| 2, gestor `base` | 25 | 25,00 | 25 | 100,00 | 100 | 4,000 |
| 3, gestor `activo` | 25 | 25,00 | 25 | 100,00 | 100 | 4,000 |
| Los cuatro, agregado | 136 | 146,59 | 200 | 146,59 | 200 | 1,000 |

En el barrel cada hilo completa una instrucción cada 4 ciclos, sin excepciones: no hay esperas por loads ni penalización por saltos. El CPI es 4 por hilo y 1 agregado, por construcción, y los ciclos de un hilo son 4 veces su IC. En la fila agregada los ciclos son los del core entero, que ejecuta una instrucción por ciclo.

Los gestores no tienen saltos que dependan del precio: su peor caso es su promedio. El supervisor varía por dos razones: cuántas vueltas da el lazo de lectura de votos (2 o 3 en un tick común) y si el tick es de frontera (hasta 45 instrucciones más y una vuelta más del lazo).

En términos de la ley de hierro (Tiempo = IC × CPI × Tclk), contra `max_media` en un hilo del mismo barrel: el IC del camino de la respuesta sube, el CPI por hilo sigue en 4 y el reloj no cambia. Lo que el barrel aporta es que las 75 instrucciones de los tres gestores se ejecutan mientras el supervisor hace las suyas: en el camino de la respuesta cuestan lo que 23 de un solo hilo.

### 8.2 Ciclos y tiempo de la respuesta

Ciclos desde `byte_done`, que es desde donde mide el testbench oficial. Ciclo de 40 ns.

| Hito | Mínimo | Promedio | Máximo | Tiempo promedio | Tiempo máximo |
|------|--------|----------|--------|-----------------|---------------|
| El supervisor publica `PUB` | 27 | 31,00 | 35 | 1,24 us | 1,40 us |
| Llega el último voto | 118 | 123,33 | 126 | 4,93 us | 5,04 us |
| `DECISION`, todos los ticks | 215 | 235,37 | 475 | 9,41 us | 19,00 us |
| `DECISION`, ticks comunes (19 957) | 215 | 235,00 | 267 | 9,40 us | 10,68 us |
| `DECISION`, ticks con frontera (39) | 375 | 421,67 | 475 | 16,87 us | 19,00 us |
| El supervisor vuelve a sondear (tick completo) | 247 | 293,37 | 507 | 11,73 us | 20,28 us |

El programa escribe `DECISION` exactamente una vez en cada tick. A 1 ms (3000 ticks) la respuesta es 243,34 ciclos en promedio y 471 en el peor caso: el programa no mide el período y solo cambia en qué fase llega el precio.

### 8.3 Contra el período de cada ronda

Con el peor caso medido barriendo la fase (480 ciclos, sección 9):

| Ronda | Período | Presupuesto (ciclos) | Peor caso | Uso | Holgura |
|-------|---------|----------------------|-----------|-----|---------|
| 1 | 10 ms | 249 762 | 480 | 0,19 % | 99,81 % |
| 2 | 1 ms | 24 762 | 480 | 1,94 % | 98,06 % |
| 3 | 0,1 ms | 2 262 | 480 | 21,22 % | 78,78 % |

Ocupación: los cuatro hilos hacen 146,59 instrucciones de trabajo por tick. A 0,1 ms el core tiene 2500 turnos por tick, así que la ocupación es 5,86 %. A 1 ms, 0,59 %. El barrel está casi siempre sondeando.

### 8.4 Contra la factibilidad y contra `max_media` sola

| | Factibilidad (`fondo_min`, sin extensión, con espejo) | Este programa | `max_media` sola (`sw/trade.s`) en el hilo 0 del barrel |
|-|--------------------------------------------------------|---------------|-------------------------------------------|
| Instrucciones por gestor y por tick | 35 | 25 | no aplica |
| Respuesta promedio | 227,36 ciclos | 235,37 | 75,06 (`docs/mediciones/barrel/ticks.txt`) |
| Peor caso barriendo la fase | 440 | 480 | 88 |
| Memoria | 251 palabras | 226 | 40 |
| Decide si un gestor se cuelga | No | Sí | no aplica |

La respuesta no bajó respecto de la factibilidad aunque los gestores son más cortos, porque el lazo de lectura con plazo lee los tres votos en cada vuelta (48 ciclos) en vez de esperar a cada gestor con un lazo de 12, y porque el supervisor lee 5 parámetros de la tabla por tick. Es el costo de la degradación y de la tabla. El fondo responde 3 veces más lento que `max_media` sola en el mismo core en promedio (235 ciclos contra 75) y 5 veces en el peor caso (480 contra 88). Sobra plazo, pero es lo que cuesta esperar a tres hilos que avanzan una instrucción cada 4 ciclos.

## 9. Peor caso barriendo la fase

`docs/mediciones/fondo/fases.txt`. El peor caso depende de en qué punto de sus lazos está cada hilo cuando llega el precio. El lazo de sondeo del supervisor dura 12 ciclos, el de los gestores 8 y la rotación de hilos 4: el patrón se repite cada 24 ciclos. Se corrió el inicio de la serie de a un ciclo:

| Corridas | Resultado | Peor caso |
|----------|-----------|-----------|
| 48 fases de un ciclo, programa sano, 1100 ticks cada una | 48 de 48 iguales a la referencia | entre 429 y 480 ciclos |
| 24 fases corridas 13 ns (el precio no llega alineado con el reloj) | 24 de 24 | entre 429 y 480 |
| Período de 2501 ciclos, 20 000 ticks (recorre todas las fases en una corrida) | igual a la referencia | 474 |
| Gestor 3 colgado, 24 fases | 24 de 24 | entre 545 y 556 |
| Los tres gestores colgados, 24 fases | 24 de 24, y bytes iguales a `max_media` sola | entre 557 y 564 |

**Peor caso sano: 480 ciclos. Peor caso con el plazo agotado: 564 ciclos**, contra el límite de 1131 (la mitad del presupuesto de la ronda 3). El peor caso de todo lo medido son 671 ciclos, con un gestor atrasado 200 ciclos a propósito (sección 10): el supervisor lo espera casi hasta el plazo y después todavía decide.

Cota por conteo de instrucciones (hecha a mano, no sale de un script): hasta `PUB` pasan a lo más 36 ciclos; la `max_media` propia son 10 instrucciones (40 ciclos); el plazo son 8 vueltas de 48 ciclos (384); el reemplazo de votos y la frontera no ocurren en el mismo tick, y el más largo de los dos es la frontera, con 45 instrucciones más una vuelta del lazo (228); el voto son 15 instrucciones (60). La suma es 748 ciclos. Es una cota razonada, no demostrada, y queda bajo 1131.

Cuántas vueltas da el lazo de lectura con los gestores sanos, en las 1 123 corridas sanas de las secciones 7 y 9: 2 o 3 en un tick común y hasta 4 en un tick de frontera (la frontera vuelve a entrar al lazo). El plazo es 8. En ninguna corrida sana venció.

## 10. Degradación

`docs/mediciones/fondo/degradacion.txt`. Cada caso es `sw/fondo.s` con instrucciones insertadas en la rutina de los gestores (`tools/fondo/variante.py`, marcas `#@` del programa). El supervisor no se toca. La decisión esperada sale de `ref/fondo.py` con la misma falla, descrita como "el voto del gestor K no llega entre los ticks N y M" (decisión T68). Cada caso corre 20 000 ticks sobre dos series: la de práctica y una de reversión.

| Falla | Casos | Qué se comprobó |
|-------|-------|-----------------|
| Un gestor en lazo infinito | Cada gestor colgado desde el arranque, cada gestor colgado desde el tick 1500, dos colgados en distintos momentos y los tres colgados | Decisión esperada en todos los ticks. El plazo vence en todos los ticks desde la falla y en ninguno antes. Con los tres colgados los bytes son los de `max_media` sola |
| Un voto que no llega | El gestor 1 en un tick, el gestor 2 en un tick de frontera, el gestor 3 durante 1601 ticks | El plazo vence solo en esos ticks. En la frontera sin voto no se tocan los pesos. Al volver el voto, el fondo sigue como la referencia |
| Un voto atrasado | 160 y 200 ciclos (cabe en el plazo), 1000 ciclos siempre y 1200 ciclos durante 1401 ticks (no cabe) | Si cabe, ninguna decisión cambia y la respuesta crece lo que se atrasó el gestor. Si no cabe, se decide sin ese voto |

Las 30 corridas pasan: bytes, estado, ticks con plazo vencido, telemetría y protocolo iguales a lo esperado, y **peor caso 671 ciclos**.

Por qué dos series. En la serie de práctica el fondo sano, el fondo con fallas y `max_media` sola escriben los mismos 20 000 bytes, así que ahí la prueba solo distingue los casos por el estado interno. En la de reversión el fondo sano y `max_media` difieren en 1816 bytes, y los casos con fallas parciales difieren de los dos (por ejemplo 276 del sano y 1540 de `max_media` con el gestor 3 sin voto entre los ticks 1000 y 2600). La última columna de cada línea de `degradacion.txt` lo informa.

Lo que no se probó: atrasos entre 200 y 600 ciclos, donde el voto llega cerca del plazo y el resultado depende del ciclo exacto. El programa decide bien en cualquiera de los dos casos (con el voto o con el reemplazo), pero la referencia no modela cuál de los dos toca.

## 11. Controles negativos

`docs/mediciones/fondo/controles.txt`. Para saber que las comparaciones de las secciones 7 a 10 ven lo que dicen ver, `tools/fondo/controles.py` arma 15 versiones del programa con un error puesto a propósito y `make fondo-controles` exige que la comparación falle en todas:

| Error | Lo detecta |
|-------|-----------|
| Otro umbral en la tabla para el gestor 3 | Voto, puntaje, LED y bytes |
| El puntaje descuenta la mitad de la comisión | Puntaje, en el tick 3 |
| La frontera no exige el margen | Pesos |
| La frontera no respeta el tope de un peso | Pesos |
| El voto exige un dieciseisavo más | Byte |
| Plazo de una sola vuelta | Vence con los gestores sanos |
| Vencido el plazo, un voto viejo no se reemplaza | Byte y LED |
| Vencido el plazo, el voto viejo se cuenta como afuera | LED |
| El supervisor no actualiza su propia media | Bytes, con los tres gestores colgados |
| Con un voto ausente en la frontera igual se ajustan los pesos | Byte y escrituras en `DECISION` |
| El supervisor acepta un voto sin mirar de qué tick es | Plazo y byte, con un gestor atrasado |
| Dos stores de telemetría en un tick | Conteo de stores |
| El latido usa otro bit | LED |
| Un gestor escribe en `PUB` | Vigilancia del protocolo |
| Dos escrituras en `DECISION` | Conteo de escrituras |

15 de 15 detectados. El de "se cuenta como afuera" solo lo delata la telemetría: con los pesos 6/5/5 ese voto no alcanza a cambiar el byte. Y el del margen no se detectaba en la primera versión, que lo corría sobre 6000 ticks de la serie de reversión, donde el margen nunca decide. Sobre la serie de práctica sí. Queda como advertencia: una prueba del ajuste de pesos vale lo que la serie con que se corre y lo que dura: el del tope tampoco se detecta con 3000 ticks, porque ningún peso llega a su tope antes del tick 3072.

## 12. Reglas del enunciado

| Regla | Cumple | Comentario |
|-------|--------|------------|
| "La decisión se debe calcular en el Espino Core en la placa. El core debe leer el precio y escribir la decisión." | Sí, con una duda | Todo el cálculo son instrucciones ejecutadas por el core: un hilo lee `PRICE` y escribe `DECISION`, y los otros tres calculan y le entregan su voto por memoria. No hay hardware que decida. La duda es si un Espino multihilo con dos instrucciones propias sigue siendo Espino: es una pregunta pendiente para el ayudante |
| No usar información externa a la serie ni guardar series de precios | Sí | El programa guarda una media por gestor y una del supervisor, tres puntajes, tres pesos y el último precio por 32. No guarda precios pasados |
| Mismo programa para todas las series | Sí | No mide el período ni cambia de modo |
| Todo hardware agregado con su testbench | Sí | El hardware es el de los paquetes P1 y P2, con sus pruebas. Este paquete no agrega hardware |
| El testbench oficial no se modifica | Sí | Entrega 4/4 sin tocarlo |
| Regla propia: nada derivado punto a punto de la serie de práctica | Sí | La tabla tiene 20 constantes: umbrales de tres candidatos del frente del algoritmo, pesos iniciales, ventana, margen implícito de 1/32 y plazo |

## 13. Límites y lo que falta

- **El algoritmo no suma puntos.** Es la decisión T50, tomada a sabiendas: según la factibilidad el fondo empata con `max_media` a 2000 ticks y pierde 0,005 puntos a 20 000. En la serie de práctica escribe los mismos bytes que `max_media`.
- **Placa y maestra real.** Todo es simulación. No se construyó un bitstream con este programa: R1 y R2 son del paquete P5.
- **Gemelo digital.** No modela el barrel (paquete P4). Las series sintéticas a 1 ms y a 10 ms, la matriz de estrés (criterio 7) y la simulación del bitstream ruteado (criterio 8) quedan para P4 y P5.
- **Rondas seguidas sin reset.** El programa no se reinicia entre rondas: medias, puntajes y pesos siguen desde donde quedaron. La referencia evalúa cada ronda desde cero. No se midió: es parte del criterio 7.
- **Borde del plazo.** Cerca del plazo la decisión depende del ciclo en que llega el voto (sección 10).
- **Vuelta del contador de ticks.** A los 16,7 millones de ticks un gestor que nunca votó contaría como "afuera" durante un tick (sección 3.3). No se ejercitó.
- **Un gestor más lento que el período se salta precios.** El supervisor ya no lo espera. No pasa con gestores sanos (25 instrucciones de 625 turnos por tick a 0,1 ms).
- **Peor caso por análisis.** El de la sección 9 es el máximo observado más una cota razonada, no una demostración.
- **Valores X en la memoria.** Verilator simula con dos estados. La corrida con Icarus, de cuatro estados, cubre 2000 ticks.

## 14. Cómo reproducir

Desde la raíz del repositorio. Los scripts agregan OSS CAD Suite al `PATH`.

| Comando | Qué hace | Salida en `docs/mediciones/fondo/` | Demora |
|---------|----------|-------------------------------------|--------|
| `make test-fondo` | Pruebas de la referencia | | 3 s |
| `make fondo-oficial` | Testbench oficial sin modificar, Icarus | `oficial.txt` | 5 min |
| `make fondo-equiv` | Práctica a 0,1 ms y 1 ms y una serie por familia | `equiv.txt` | 3 min |
| `make fondo-equiv-ronda1` | Lo mismo más el período de 10 ms | `equiv.txt` | 35 min |
| `make fondo-series` | 1 050 series sintéticas | `series.txt` | 15 min |
| `make fondo-timing` | Celdas y frecuencia en 10 semillas | `timing.txt` | 3 min |
| `make fondo-fases` | Peor caso barriendo la fase | `fases.txt` | 2 min |
| `make fondo-degradacion` | 30 corridas con fallas | `degradacion.txt` | 3 min |
| `make fondo-controles` | 15 controles negativos | `controles.txt` | 1 min |
| `make fondo-ticks` | Mediciones por tick y tamaño | `ticks.txt`, `tamano.txt` | 1 min |
| `make check-fondo` | Versiones cortas de todo lo anterior. Corre en la integración continua | `build/fondo/` | 10 min |
| `make fondo-completo` | Todo, en versión completa | | |

Para correr un caso a mano: `source tools/fondo/comun.sh; ensamblar_fondo; compilar_sim; caso build/fondo/prueba sw/fondo.s tb/practica.csv 2000 100000 4000 --medir; cat build/fondo/prueba/resultado.txt`.

## 15. Preguntas para estudiar

1. **¿Por qué el supervisor calcula `max_media` si el gestor 1 ya la calcula?** Porque la del gestor 1 llega por memoria y puede no llegar. La del supervisor está en sus registros: es la única que no depende de otro hilo. `sw/fondo.s`, bloque 3 del supervisor.
2. **¿Qué pasa si un gestor se cuelga?** Su voto queda con un número de tick viejo. El supervisor lo nota porque la resta contra su tick no da 0 ni 1, espera 8 vueltas, y usa su propia `max_media` en ese lugar. La decisión sale 564 ciclos después del precio en el peor caso medido, y es la de `max_media`. Sección 10.
3. **¿Cómo sabe el supervisor que un voto es viejo sin un bit de "listo"?** El voto lleva el número del tick que el gestor procesó. Un bit de "listo" habría que borrarlo, y eso serían dos hilos escribiendo la misma palabra. Sección 3.3.
4. **¿Por qué no hay carreras si cuatro hilos comparten la memoria?** Porque cada palabra la escribe un solo hilo, un store es atómico y el barrel ejecuta una instrucción por ciclo en orden fijo. Sección 3.5.
5. **¿Por qué el fondo responde más lento que `max_media` sola si usa cuatro hilos?** Porque cada hilo avanza una instrucción cada 4 ciclos y el supervisor tiene que esperar a los otros tres. El barrel reparte el trabajo, no lo acelera para un hilo. Sección 8.4.
6. **¿Qué gana el fondo con las instrucciones nuevas?** Cada gestor baja de 35 a 25 instrucciones por tick, y el supervisor calcula su `max_media` en 8. Sección 4.
7. **¿Por qué el puntaje está en treintaidosavos?** Porque `devk` entrega 32 p y la diferencia de dos de esos valores ya es 32 veces el cambio de precio. Es el doble exacto del puntaje de la factibilidad. Sección 2 y `ref/test_fondo.py`.
8. **¿Cuánto del resultado es del fondo y cuánto de `max_media`?** En la serie de práctica, todo es de `max_media`: los bytes son los mismos. La diferencia aparece cuando los pesos se alejan de 6/5/5. Secciones 3.4 y 10.
9. **¿Qué se puede cambiar sin volver a ensamblar?** Las 20 palabras de la tabla. Sección 5.
10. **¿Cómo se sabe que las pruebas detectarían un error?** Por los 15 controles negativos, y porque uno de ellos mostró que una prueba mal elegida no detectaba nada. Sección 11.
