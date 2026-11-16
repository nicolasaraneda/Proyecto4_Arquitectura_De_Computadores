# Pieza B en la placa: un gestor por hilo sobre el Espino barrel

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz. Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Prototipo de factibilidad. Nada de esta carpeta está integrado en `rtl/`, en `sw/`, en el `Makefile` de la raíz ni en la integración continua. Todos los números de este documento salen de un script de esta carpeta y su salida está guardada en `mediciones/`. Lo que es estimado se marca como estimado. Al final está el comando de cada uno.

## 1. Resumen

Se escribió `sw/fondo.s`, un programa con los cuatro hilos del Espino barrel ocupados: el hilo 0 es el supervisor (lee el precio, lo publica, espera a los gestores, reparte, vota, escribe `DECISION` y lleva el espejo de la cuenta real) y los hilos 1, 2 y 3 son tres gestores que operan en papel. Implementa, sin simplificarla, la configuración `fondo_min` del estudio de retorno 4B (`factibilidad/retorno/r4b_fondo/`). El programa corre sobre el SoC de `factibilidad/a_barrel/` sin modificar: esta pieza no agrega hardware.

| Medición | Resultado | Salida |
|----------|-----------|--------|
| Tamaño | 227 palabras de programa y 24 de datos: 251 de 512 (49,0 %). Quedan 261 libres | `mediciones/tamano.txt` |
| Testbench oficial sin modificar (Icarus, 2000 ticks) | 4/4, y `decisiones.csv` idéntico byte a byte al de la referencia en C | `mediciones/oficial.txt` |
| Copia parametrizada del testbench oficial (Verilator) | 11 casos de 20 000 ticks (la práctica a 0,1 ms, a 1 ms y a 10 ms, y 8 series sintéticas a 0,1 ms): 4/4 y `decisiones.csv` idéntico al de la referencia en los 220 000 ticks | `mediciones/equiv.txt` |
| Estado interno tick a tick contra la traza en C | 82 991 ticks por 13 campos (espejo de la cuenta, posiciones, puntajes, pesos y byte), cero diferencias | `mediciones/estado.txt` |
| Instrucciones por tick, supervisor | 41 en el tick común, 41,99 en promedio, 72 como máximo cuando el espejo ejecuta una orden y 84 con frontera de ventana | `mediciones/ticks.txt` |
| Instrucciones por tick, cada gestor | 35, siempre (no tiene saltos que dependan del precio) | `mediciones/ticks.txt` |
| Respuesta, de `byte_done` a `DECISION` | 227,36 ciclos en promedio y 439 en el peor caso del testbench oficial | `mediciones/ticks.txt` |
| Respuesta, peor caso barriendo la fase del sondeo (24 fases) | 440 ciclos: 19,45 % de los 2262 de la ronda 3. Margen de 1822 ciclos | `mediciones/ticks.txt` |
| Las decisiones no dependen de los ciclos | Idénticas en las 24 fases, a 0,1 ms y a 1 ms, y con el gestor 3 o el gestor 2 atrasado 800 ciclos a propósito | `mediciones/ticks.txt`, `mediciones/variantes.txt` |
| Un gestor que no cabe en el tick | Con 2400 ciclos de atraso a 0,1 ms el fondo pierde 1148 de 20 000 precios y el testbench baja a 2/4. No se cuelga. A 1 ms vuelve a dar 4/4 y decisiones idénticas | `mediciones/variantes.txt` |
| Supervisor que usa lo del tick anterior (variante `anterior`) | Idéntico a `fondo_min_ant`. Responde en 131 ciclos en promedio y 343 en el peor caso | `mediciones/variantes.txt` |
| Búsqueda de carreras (auditoría, sección 15) | 19 corridas con retardos al azar en los cuatro hilos y fase de llegada al azar: 337 174 decisiones vigiladas, cero violaciones del protocolo, ningún `EST_k` cargado de otro tick al decidir y estado igual al modelo en todas | `factibilidad/auditoria_hw/mediciones/carreras.txt` |

Veredicto según los criterios de corte (sección 13): **como programa es factible** (cabe en la mitad de la memoria, usa menos de la quinta parte del plazo de la ronda más rápida y decide igual que su referencia en todos los ticks comparados), **pero el algoritmo que implementa no pasa el criterio de corte de algoritmo**: el estudio 4B midió que `fondo_min` empata con `max_media` a 2000 ticks (+0,000 ± 0,000 puntos) y pierde 0,018 ± 0,002 (H3a, series interiores) a 20 000. Por eso la pieza queda para la edición de exhibición, con estos números.

## 2. Qué hay en esta carpeta

| Archivo | Qué es |
|---------|--------|
| `sw/fondo.s` | El programa: tabla de arranque, supervisor y rutina común de los tres gestores. |
| `tb/tb_fondo.sv` | Testbench de medición. Maestra SPI, contabilidad y chequeos del testbench oficial, más conteo por tick y por hilo, hitos del protocolo y estado interno leído de la memoria. |
| `tools/comun.sh` | Rutas, lista de fuentes y funciones que comparten los scripts. |
| `tools/simbolos.py` | Direcciones de las etiquetas del programa (para el testbench) y tamaño por bloque. Usa el ensamblador del repositorio sin modificarlo. |
| `tools/variante.py` | Arma las variantes de medición desde `sw/fondo.s`, moviendo o insertando texto en las marcas `#@` del programa. |
| `tools/comparar_estado.py` | Compara el estado interno del barrel con la traza del módulo en C. |
| `tools/resumen_ticks.py` | Tablas de las mediciones por tick. |
| `tools/tamano.sh`, `oficial.sh`, `equiv.sh`, `estado.sh`, `medir_ticks.sh`, `variantes.sh`, `retorno.sh` | Un script por medición. |
| `Makefile` | Un objetivo por script. También compila la referencia (`build/arnes`). |
| `mediciones/` | Salidas guardadas de cada script. |
| `AVANCE.md` | Bitácora de trabajo. |

No se modificó ningún archivo fuera de esta carpeta. Se usan tal como están: el RTL del barrel (`factibilidad/a_barrel/rtl/`), `rtl/pochoco_ram.v`, `rtl/pochoco_spi_slave.v`, `rtl/pochoco_periph.v`, el decodificador, la ALU y la unidad de carga del Espino, el testbench oficial, `tools/pochoasm.py`, `ref/series.py`, `ref/trader.py` (solo su función `ticks_perdidos`) y el arnés de retorno con `r4b_fondo/fondo.c`. No hizo falta copiar ni cambiar ningún fuente ajeno.

## 3. Qué implementa

`fondo_min` es el fondo mínimo de demostración que definió el estudio 4B: `fondo:c=5,w0=6,w1=5,w2=5,m=2,v=9,mg=5,d=4,pp=1,vt=8`. En cada tick, con el precio p que acaba de llegar:

1. **Tres gestores en papel**, la misma regla de reversión con otras constantes. Cada uno lleva su media exponencial (alfa 1/32, guardada por 32) y su posición (0 afuera, 1 adentro):

   | Hilo | Gestor | Entra si | Sale si |
   |------|--------|----------|---------|
   | 1 | `max_media` | el precio está más de 3 bajo su media | vuelve a quedar sobre la media |
   | 2 | `base` | más de 4 bajo su media | vuelve a quedar sobre la media |
   | 3 | `activo` | más de 2 bajo su media | queda más de medio punto sobre la media |

2. **Puntaje en papel por acción**, sin productos: el gestor suma 16 veces el cambio de precio mientras tiene la acción y resta 1 cada vez que su posición cambia (la comisión, en dieciseisavos de unidad de precio).
3. **Supervisor: reparto.** Tiene un peso por gestor, en dieciseisavos, que parte en 6/5/5 (el prior). Cada 512 ticks compara cuánto ganó cada gestor en la ventana y pasa 1/16 del peor al mejor, si la ventaja supera 1/32 del precio y ningún peso se aleja más de 4/16 de su prior.
4. **Supervisor: voto y `DECISION`.** Suma los pesos de los gestores que están adentro. Con 8/16 o más escribe `0x7F` (comprar 63) y si no `0xBF` (vender 63). Una sola escritura por tick.
5. **Supervisor: espejo de la cuenta real.** Ejecuta sobre su copia de la caja y de las acciones, al precio que acaba de llegar, el byte que dejó en el tick anterior, con las reglas de `tb/tb_proyecto_4.sv` (compra recortada a lo que alcanza, venta recortada a lo que se tiene, comisión de 5).

`fondo_min` no usa el espejo para decidir: su voto es todo o nada. Se incluyó igual porque el diseño pide que el supervisor lleve la contabilidad, porque es el bloque que las configuraciones con posiciones parciales (`fondo_rec`) sí necesitan, y porque así queda medido lo que cuesta (75 palabras y entre 5 y 39 instrucciones por tick). Se calcula después de escribir `DECISION`, así que no alarga la respuesta. Se comprobó contra la traza del módulo en C en todos los ticks (sección 6.3).

Como la configuración no se simplificó, su resultado de retorno es el que ya midió el estudio 4B y no hizo falta agregar una configuración al módulo en C. `make retorno` deja constancia de que la referencia usada aquí es ese mismo módulo y repite el patrimonio medio con el arnés compilado en esta carpeta (`mediciones/retorno.txt`): +1,4 ± 0,7 de patrimonio contra `max_media` a 2000 ticks (10 000 series) y +602 ± 86 a 20 000 ticks en las series interiores (4021 series). En puntos de torneo, que es lo que cuenta para el criterio de corte, el estudio 4B midió +0,000 ± 0,000 a 2000 ticks y -0,018 ± 0,002 (H3a) a 20 000.

## 4. Protocolo entre hilos

### 4.1 Palabras compartidas y quién las escribe

| Palabra | La escribe | La leen | Contenido |
|---------|------------|---------|-----------|
| `PUB` | Supervisor | Los tres gestores | Número de tick en los bits 31:8 y precio en los bits 7:0 |
| `DES_k` | Gestor k | Supervisor (solo en la frontera de ventana) | Puntaje en papel del gestor |
| `EST_k` | Gestor k | Supervisor | Número del tick que el gestor acaba de procesar en los bits 31:8 y su posición en el bit 0 |
| `TMP_k` | Gestor k | Gestor k | Palabra de trabajo del desplazamiento a la derecha |
| `CAJA`, `ACC`, `W1` a `W3`, `REF1` a `REF3` | Supervisor | Supervisor | Espejo de la cuenta, pesos vigentes y puntajes al empezar la ventana |

Cada palabra tiene un solo hilo que la escribe. El único hilo que toca el esclavo SPI es el supervisor.

### 4.2 Un tick

```
Supervisor (hilo 0)                          Gestor k (hilos 1, 2 y 3)
-------------------                          -------------------------
sondea STATUS hasta ver el precio            sondea PUB hasta que cambie
lee PRICE
PUB = tick * 256 + precio   ------------->   ve PUB distinto del último que procesó
                                             puntaje en papel y regla de reversión
espera EST_1, EST_2 y EST_3 con    <------   DES_k = puntaje
el número de este tick                       EST_k = tick * 256 + posición
(cada 512 ticks: ajusta los pesos)           actualiza su media y vuelve a sondear PUB
voto ponderado
escribe DECISION
espejo de la cuenta real
vuelve a sondear STATUS
```

Respuestas a las preguntas del protocolo:

- **Cómo publica el supervisor el precio y el número de tick.** Juntos, en una sola palabra y con un solo store (`sw x9, PUB(x0)`).
- **Cómo espera cada gestor.** Sondea `PUB` con un lazo de dos instrucciones (`lw` y `beq`) hasta que su valor sea distinto del último que procesó. Como el número de tick cambia en cada tick, `PUB` cambia siempre, aunque el precio se repita.
- **Cómo publica su objetivo.** Primero el puntaje en `DES_k` y al final `EST_k`, que lleva el número de tick y la posición en una sola palabra.
- **Cómo sabe el supervisor que los tres terminaron.** Lee `EST_k` y le resta su número de tick por 256. Si el gestor ya publicó este tick, la resta da 0 o 1 (la posición). Si todavía tiene el tick anterior da -256 o -255, que sin signo es mayor que 2, y el supervisor vuelve a leer. Son tres instrucciones por gestor (`lw`, `sub` y `bgeu`) y de paso dejan la posición en un registro.

### 4.3 Por qué no hay carreras

El argumento se apoya en tres hechos del barrel (`factibilidad/a_barrel/README.md`, secciones 3.2, 3.4 y 3.6):

1. **Rotación de 4 ciclos.** En cada ciclo hay una sola instrucción en la etapa de ejecución, y los hilos pasan por ella en orden fijo: 0, 1, 2, 3, 0, 1... Todos los accesos al bus de datos quedan entonces en un orden total, uno por ciclo.
2. **Un load y un store son atómicos.** El store escribe la palabra completa en el flanco que cierra su ciclo. Un load de cualquier hilo en un ciclo posterior ve la palabra nueva completa, y uno anterior ve la vieja completa. No existe una palabra a medio escribir.
3. **Dentro de un hilo no hay riesgos.** La instrucción i+1 de un hilo entra a búsqueda cuando la i ya escribió, así que los stores de un hilo llegan a la memoria en el orden del programa.

Con eso, cada propiedad del protocolo se sigue de cómo está escrito el programa:

| Propiedad | Por qué se cumple |
|-----------|-------------------|
| Un gestor nunca ve un precio con el número de tick de otro | Van en la misma palabra y se escriben con un solo store (hecho 2) |
| El supervisor nunca toma una posición de un tick anterior | La posición viaja con su número de tick en `EST_k`, y el supervisor compara ese número con el suyo antes de usarla |
| Cuando el supervisor lee `DES_k` en la frontera, ya es el puntaje de este tick | El gestor escribe `DES_k` antes que `EST_k` (hecho 3), y el supervisor lee `DES_k` solo después de haber visto `EST_k` con el número de este tick (hecho 1). El gestor no vuelve a escribir `DES_k` hasta que `PUB` cambie, y `PUB` lo cambia el propio supervisor |
| Ningún gestor se salta un precio ni procesa dos veces el mismo | El supervisor no publica el tick n+1 hasta haber visto los tres `EST_k` del tick n. Entre dos publicaciones de un gestor, `PUB` cambia exactamente una vez |
| No hay lectura, modificación y escritura repartidas entre hilos | Las secuencias de leer, sumar y guardar (caja, acciones, pesos, puntajes al empezar la ventana) son todas sobre palabras que solo usa el supervisor |
| No hay bloqueo mutuo | El supervisor espera a un gestor solo después de haber publicado `PUB`, y el gestor no espera nada más que `PUB` |
| El contador de ticks puede dar la vuelta | Tiene 24 bits (16,7 millones de ticks, 28 minutos a 0,1 ms). Solo se usa para comparar por igualdad y restar módulo 2^32, así que la vuelta no cambia nada. Se ejercitó haciendo partir el contador 16 ticks antes de la vuelta (variante `vuelta`, sección 4.6) |

La auditoría puso a prueba este argumento con mutaciones del protocolo y con tiempos al azar (sección 15). No encontró ninguna carrera, y precisó dos filas de la tabla: la segunda solo se puede comprobar completa atrasando a cada gestor (sin retardos, los gestores 2 y 3 siempre publican antes de que el supervisor llegue a leerlos), y la tercera no se puede comprobar en este programa.

La consecuencia práctica es que **la decisión no depende de cuántos ciclos demora cada hilo**, solo de los valores. Por eso la referencia en C no modela ciclos y aun así coincide byte a byte. Se comprobó de cuatro formas: con dos períodos (0,1 ms y 1 ms), corriendo la llegada del primer precio de a un ciclo en 24 fases distintas (sección 7.3), atrasando a propósito a un gestor (sección 4.4) y moviendo el espejo de lugar (sección 4.5). En todas las corridas el flujo de bytes es el mismo.

### 4.4 Qué pasa si un gestor se atrasa

Se midió con variantes del programa en que el gestor del hilo 3 da vueltas en un lazo vacío, y una en que lo hace el del hilo 2 (`tools/variante.py`, `mediciones/variantes.txt`, serie de práctica completa a 0,1 ms):

| Variante | Chequeos | Precios perdidos | Decisiones | Respuesta: promedio y peor caso (ciclos) |
|----------|----------|------------------|------------|-------------------------------------------|
| `base` | 4/4 | 0 | idénticas a `fondo_min` | 227,36 y 439 |
| `atraso_800`: 800 ciclos más antes de publicar | 4/4 | 0 | idénticas, y el estado interno también | 1019,36 y 1231 |
| `atraso_800_g2`: lo mismo con el gestor del hilo 2 | 4/4 | 0 | idénticas, y el estado interno también | 1031,36 y 1243 |
| `despues_2000`: 2000 ciclos después de publicar | 4/4 | 0 | idénticas, y el estado interno también | 227,36 y 439 |
| `despues_2400`: 2400 ciclos después de publicar | 2/4 | 406 de 20 000 | distintas desde el tick 56 | 1224,54 y 2499 |
| `atraso_2400`: 2400 ciclos más antes de publicar | 2/4 | 1148 de 20 000 | distintas desde el tick 3 | 1178,57 y 2499 |
| `atraso_2400` con período de 1 ms (3000 ticks) | 4/4 | 0 | idénticas | 2615,31 y 2827 |

Lectura:

- **Si el atraso cabe en el tick, no cambia ninguna decisión.** El supervisor espera y la respuesta crece exactamente lo que se atrasó el gestor (792 ciclos más en `atraso_800`, y 804 en `atraso_800_g2`, porque después de esperar al gestor 2 todavía le falta leer al 3).
- **Cada espera necesita su variante.** Sin retardos el supervisor solo espera de verdad al gestor 1: cuando termina, los gestores 2 y 3 ya publicaron (lo midió la auditoría, sección 15). `atraso_800` ejercita la espera del gestor 3 y `atraso_800_g2`, que se agregó en la auditoría, la del gestor 2.
- **Lo que un gestor haga después de publicar es gratis para la respuesta**, mientras su vuelta completa quepa en el tick. Con 2000 ciclos de trabajo extra después de `EST_k` la respuesta es la misma, ciclo por ciclo. Un gestor más pesado conviene escribirlo así: decidir y publicar primero, y dejar para después lo que solo prepara el tick siguiente. `fondo.s` ya lo hace con la actualización de la media.
- **Si la vuelta completa de un gestor dura más que el tick, el fondo se atrasa un poco más en cada tick y termina perdiendo precios.** El supervisor sigue esperando cuando llega el precio siguiente, no alcanza a leer `PRICE` antes de que lo pise el que viene, y la maestra relee el byte anterior. En `despues_2400` la vuelta del gestor dura unos 2550 ciclos (por conteo de instrucciones) contra 2500 del tick, y se pierde el 2,0 % de los precios. En `atraso_2400`, el 5,7 %. El testbench lo detecta con dos de sus cuatro chequeos (lee todos los precios, y la decisión llega antes del tick siguiente).
- **No hay bloqueo ni estado corrupto.** El fondo sigue operando sobre los precios que alcanza a ver (terminó con patrimonio 26 703 y 25 568, contra 26 070 de la referencia), pero ya no es equivalente a ella, y el espejo de la cuenta deja de coincidir con la cuenta real, porque la maestra ejecutó órdenes a precios que el supervisor no vio.
- **No hay nada que acote el tiempo de un gestor.** El protocolo no tiene plazo. La protección que tiene este programa es que el gestor es de tiempo constante: 35 instrucciones por tick, sin saltos que dependan del precio. Una versión de competencia con gestores de tiempo variable necesitaría un plazo en el supervisor (decidir con lo del tick anterior si `EST_k` no llegó a tiempo). No se construyó.

### 4.5 El supervisor trabaja mientras espera

En `fondo.s` el espejo de la cuenta se calcula después de escribir `DECISION`. La variante `espejo_antes` lo mueve a antes de la espera, o sea que el supervisor hace su contabilidad mientras los gestores calculan. Es lo que haría falta si el reparto necesitara el patrimonio (posiciones parciales). Resultado, con las mismas decisiones y el mismo estado interno:

| Variante | Respuesta: promedio y peor caso | Supervisor termina el tick: promedio y peor caso | Instrucciones del supervisor esperando a los gestores |
|----------|----------------------------------|---------------------------------------------------|--------------------------------------------------------|
| `base` | 227,36 y 439 | 267,01 y 475 | 33,02 |
| `espejo_antes` | 232,87 y 447 | 236,87 y 451 | 25,48 |

Hacer el espejo antes de decidir cuesta 5,5 ciclos de respuesta en promedio. En un core de un solo hilo las mismas instrucciones costarían su duración completa. Es la medición directa de lo que aporta el barrel a este programa: los gestores tardan unos 105 ciclos entre que ven `PUB` y publican, y en ese rato el supervisor tiene 26 instrucciones propias que no alargan la respuesta.

### 4.6 Si el supervisor usa la respuesta del tick anterior

La variante `anterior` no espera el resultado del tick en curso. Al llegar el precio n, el supervisor comprueba que los tres `EST_k` sean del tick n-1 (si alguno no lo fuera, lo espera), ajusta los pesos si toca, y recién entonces publica el precio n y decide con las posiciones del tick n-1. Sigue sin carreras, porque toma la foto antes de publicar: desde que ve `EST_k` del tick n-1 hasta que publica `PUB`, ningún gestor escribe `DES_k` ni `EST_k`.

| Variante | Referencia | Decisiones | Respuesta: promedio y peor caso |
|----------|------------|------------|----------------------------------|
| `base` | `fondo_min` | idénticas (20 000 ticks) | 227,36 y 439 |
| `anterior` | `fondo_min_ant` | idénticas (20 000 ticks) | 131,37 y 343 |
| `vuelta` (el contador de ticks da la vuelta en el tick 16) | `fondo_min` | idénticas (20 000 ticks), y el estado interno también | 227,36 y 439 |

La fila `vuelta` no es de este tema: está en la misma corrida y es la prueba de la vuelta del contador de ticks que cita la sección 4.3.

Se ganan 96 ciclos de respuesta que no hacen falta (el plazo es 2262) y se pierde retorno: el estudio 4B midió que el desfase de un tick cuesta 0,021 ± 0,002 puntos (H3a) a 2000 ticks, y `make retorno` da -30,4 ± 5,9 de patrimonio contra `max_media`. La versión que espera es la que conviene. La variante queda como respaldo si algún día los gestores no cupieran en el tick.

## 5. El programa

`sw/fondo.s`, 227 palabras (`mediciones/tamano.txt`):

| Bloque | Palabras |
|--------|----------|
| Tabla de arranque (el hilo t parte en la dirección 4 t) | 4 |
| Supervisor: inicio, sondeo del SPI y publicación | 17 |
| Supervisor: espera a los tres gestores | 9 |
| Supervisor: voto y `DECISION` | 14 |
| Supervisor: espejo de la cuenta real | 75 |
| Supervisor: vuelta al sondeo | 1 |
| Supervisor: frontera de ventana (pesos) | 46 |
| Entradas de los tres gestores (base de su bloque y sus dos umbrales) | 12 |
| Rutina común de los gestores | 49 |
| **Programa** | **227** |
| Datos: 9 del supervisor, 9 de los gestores y 6 constantes (topes y pisos de los pesos) | 24 |
| **Total** | **251 de 512 (49,0 %)** |

Por tipo: 140 instrucciones de ALU, 32 saltos condicionales, 28 loads, 14 stores, 12 `jal` y 1 `lui`.

Cómo se resolvió lo que el Espino no tiene (la ALU no desplaza y no hay producto ni división):

- **Los tres gestores comparten la rutina.** El código es reentrante: solo usa registros (cada hilo tiene los suyos) y el bloque de memoria cuya dirección está en `x2`. Los umbrales de cada gestor quedan en `x10` y `x11` en su entrada, así que cambiar un gestor por otro de la misma familia es cambiar dos constantes.
- **La regla de reversión es la de `sw/trade.s`** (`docs/trade_s.md`): 32 p con cinco sumas, comparaciones con `slt` en vez de saltos, y la posición con `or` y `and`. El desplazamiento a la derecha de la media usa la memoria (`sw` de la palabra y `lbu` de su segundo byte), con una palabra `TMP_k` propia de cada gestor para que no se pisen.
- **El puntaje en papel no multiplica:** 16 p sale de camino a 32 p, y "tenía la acción" se aplica como máscara (`sub x7, x0, x12` y `and`).
- **El voto no multiplica:** cada peso se suma o no con una máscara hecha de la posición.
- **El espejo de la cuenta** hace el cociente de la compra, `min(63, (caja - 5) / p)`, con 6 restas de prueba contra 32 p, 16 p, ..., p (el resto es la caja que queda), y el producto de la venta con 6 sumas condicionadas a los bits de la cantidad. Es el único bloque con saltos que dependen de los datos.
- **La frontera de ventana** elige al mejor y al peor con comparaciones y guarda la dirección del peso de cada uno, así que el ajuste es un load y un store por peso. El margen de 1/32 del precio se compara como `2 * ventaja > p`.

El único estado inicial que el programa toma de la imagen de memoria son las 24 palabras de datos (caja 10 000, pesos, topes y pisos). El SoC solo tiene el reset de encendido, que ocurre junto con la carga de las BRAM, así que la imagen y el reset no se pueden separar.

## 6. Equivalencia con la referencia

La referencia es `factibilidad/retorno/r4b_fondo/fondo.c` sin modificar, compilado con el núcleo del arnés en `build/arnes` (`make arnes`). El flujo de bytes sale de `build/arnes correr --estrategia fondo_min --serie S --nticks N --perdidos K -o ref.csv`, que escribe el mismo formato que el `decisiones.csv` del testbench. K son los precios que el programa no ve porque llegan durante el reset de encendido de 4095 ciclos: 2 a 0,1 ms y 1 a 1 ms y 10 ms. Es el mismo modelo de `ref/trader.py` (decisión T13), y K se calcula con su función `ticks_perdidos`.

### 6.1 Testbench oficial sin modificar

`mediciones/oficial.txt`. `tb/tb_proyecto_4.sv` tal como está en el repositorio, con Icarus Verilog, contra el SoC barrel y `fondo.hex` puesto en el lugar de `sw/trade.hex`:

- Los cuatro chequeos pasan: **4/4**. Peor caso de precio a decisión: 439 ciclos de 2262.
- `decisiones.csv` es idéntico byte a byte al de la referencia (2001 líneas, mismo sha256). Patrimonio final 9661 con 74 órdenes en los dos.

### 6.2 Copia parametrizada, 20 000 ticks

`mediciones/equiv.txt`. La copia del testbench solo cambia `PROGRAMA`, `SERIE`, `PERIODO_NS`, `NTICKS` y el nombre del archivo de salida (el script comprueba que no cambie nada más). Verilator. Cada caso exige 4/4 y `cmp` contra la referencia.

| Serie | Período | Precios | Peor caso (ciclos) | Órdenes | Patrimonio final | Resultado |
|-------|---------|---------|--------------------|---------|------------------|-----------|
| Práctica | 0,1 ms | 72 a 190 | 439 | 630 | 26 070 | 4/4, 20 000 filas idénticas |
| Práctica | 1 ms | 72 a 190 | 439 | 594 | 25 031 | 4/4, 20 000 filas idénticas |
| Práctica | 10 ms | 72 a 190 | 439 | 594 | 25 031 | 4/4, 20 000 filas idénticas |
| `modelo` | 0,1 ms | 76 a 163 | 439 | 325 | 11 208 | 4/4, 20 000 filas idénticas |
| `remuestreo` | 0,1 ms | 71 a 198 | 439 | 655 | 24 926 | 4/4, 20 000 filas idénticas |
| `tendencia` | 0,1 ms | 17 a 255 | 439 | 185 | 13 079 | 4/4, 20 000 filas idénticas |
| `saltos` | 0,1 ms | 1 a 220 | 439 | 5 069 | 312 660 | 4/4, 20 000 filas idénticas |
| `cambio_de_caracter` | 0,1 ms | 72 a 255 | 439 | 521 | 13 255 | 4/4, 20 000 filas idénticas |
| `volatil` | 0,1 ms | 1 a 255 | 439 | 6 521 | 374 864 | 4/4, 20 000 filas idénticas |
| `borde_alto` | 0,1 ms | 240 a 255 | 439 | 6 681 | 614 131 | 4/4, 20 000 filas idénticas |
| `plana` | 0,1 ms | 10 a 10 | 383 | 0 | 10 000 | 4/4, 20 000 filas idénticas |

El patrimonio de la práctica cambia entre 0,1 ms y 1 ms porque el programa deja de ver 2 precios o 1 durante el reset, igual que con la regla base. Los patrimonios de las series de estrés son los de una serie inventada y no dicen nada del retorno esperado: están para mostrar que el espejo y los puntajes se ejercitaron con miles de órdenes y con cajas grandes.

Las series sintéticas salen de `ref/series.py FAMILIA --n 20000 --semilla 1`. Dos son plausibles (`modelo`, `remuestreo`) y seis de estrés, entre ellas las que tocan los bordes 1 y 255. Con 20 000 ticks cada serie pasa por 39 fronteras de ventana.

**Cero diferencias en los 220 000 ticks.** La fila de 10 ms no sale de `make equiv`: se corrió una vez con `make equiv-ronda1` (34 minutos), que es el comando que dejó el `mediciones/equiv.txt` guardado. `make equiv` solo, sin esa fila, lo vuelve a escribir con 10 casos y 200 000 ticks.

### 6.3 Estado interno

`mediciones/estado.txt`. El flujo de bytes de `fondo_min` solo toma los valores `7F` y `BF` (más `00` antes del primer precio), así que un error en un puntaje o en el espejo podría no verse en los bytes hasta muchos ticks después, o nunca. Por eso `tb/tb_fondo.sv` lee además la memoria del SoC al cerrar cada tick y `tools/comparar_estado.py` la compara con la traza que `fondo.c` escribe con `FONDO_TRAZA`: precio, espejo de la caja y de las acciones, posición y puntaje de cada gestor, los tres pesos y el byte.

| Serie | Ticks | Órdenes que ejecuta el espejo | Cambios de pesos | Resultado |
|-------|-------|-------------------------------|------------------|-----------|
| Práctica, 0,1 ms | 19 998 | 630 | 20 (terminan en 7/6/3) | 13 campos idénticos en todos los ticks |
| Práctica, 1 ms | 2 999 | 92 | 3 | idénticos |
| `modelo` | 19 998 | 325 | 15 (terminan en 3/4/9) | idénticos |
| `tendencia` | 19 998 | 185 | 6 (terminan en 6/2/8) | idénticos |
| `volatil` (precio entre 1 y 255, patrimonio final sobre 300 000) | 19 998 | 6 521 | 31 (terminan en 8/5/3) | idénticos |

Son 82 991 ticks. Las variantes `espejo_antes`, `atraso_800`, `atraso_800_g2`, `despues_2000` y `vuelta` pasan la misma comparación en la serie de práctica (`mediciones/variantes.txt`).

## 7. Mediciones

`mediciones/ticks.txt`. Serie de práctica completa con el timing del testbench oficial y el período de la ronda 3, medido con `tb/tb_fondo.sv` y Verilator. Una ventana va de un `byte_done` al siguiente (2500 ciclos). Cada hilo ejecuta 625 instrucciones por ventana, una cada 4 ciclos. "Trabajo" son las instrucciones fuera de los lazos de espera más una vuelta de cada lazo (la que encuentra lo que esperaba).

### 7.1 Instrucciones por tick de cada hilo

| Hilo | Mínimo | Promedio | Máximo |
|------|--------|----------|--------|
| 0, supervisor | 38 | 41,99 | 84 |
| 1, gestor `max_media` | 29 | 35,00 | 35 |
| 2, gestor `base` | 29 | 35,00 | 35 |
| 3, gestor `activo` | 29 | 35,00 | 35 |

Los gestores ejecutan 35 instrucciones en todos los ticks menos el primero (29, porque ahí solo inician su media). No tienen saltos que dependan del precio, así que su peor caso es su promedio. De esas 35, 26 van antes de publicar `EST_k` y 9 después.

El supervisor, por tipo de tick:

| Tick | Ticks | Instrucciones: mínimo, promedio y máximo |
|------|-------|-------------------------------------------|
| Común, sin orden que ejecutar en el espejo | 19 327 | 41, 41,00 y 41 |
| El espejo ejecuta una orden (316 compras y 314 ventas) | 630 | 61, 69,97 y 72 |
| Con frontera de ventana | 39 | 72, 78,62 y 84 |

De las instrucciones del supervisor, el espejo de la cuenta usa entre 5 y 39 (8,91 en promedio) y la frontera entre 30 y 42 cuando la hay. En el tick común son 12 de sondeo y espera que encuentran lo que buscan, 21 de publicar, votar y escribir, y 8 del espejo.

El resto del turno se va en los lazos de espera: el supervisor sondea el SPI durante 562 instrucciones por tick en promedio y espera a los gestores durante 33, y cada gestor sondea `PUB` durante 592.

Contra lo que estimó el estudio 4B sin tener el programa:

| | Estimado (4B) | Medido |
|-|---------------|--------|
| Instrucciones por gestor | 38 | 35 |
| Supervisor, tick común | 35, sin espejo | 41 con espejo (33 sin él) |
| Supervisor, frontera de ventana | 80, sin espejo | 84 como máximo, con espejo |
| Respuesta | 320 ciclos | 227,36 en promedio y 440 en el peor caso |
| Memoria | unas 185 palabras, sin espejo | 251 con espejo (176 sin él) |

### 7.2 Ciclos de respuesta

Ciclos desde `byte_done` hasta la escritura de `DECISION`, que es lo que mide el testbench oficial:

| Ticks | Cuántos | Mínimo | Promedio | Máximo |
|-------|---------|--------|----------|--------|
| Todos | 19 997 | 203 | 227,36 | 439 |
| Comunes | 19 957 | 223 | 227,00 | 231 |
| Con frontera de ventana | 39 | 387 | 415,00 | 439 |

En tiempo, a 40 ns por ciclo: 9,09 us en promedio y 17,56 us en el peor caso. El programa escribe `DECISION` exactamente una vez en cada uno de los 19 997 ticks.

Dónde se va la respuesta en un tick común:

| Tramo | Mínimo | Promedio | Máximo |
|-------|--------|----------|--------|
| Llega el precio y el supervisor publica `PUB` (sondeo del SPI, leer y publicar) | 27 | 31,00 | 35 |
| De `PUB` al último `EST_k` (los tres gestores en paralelo, 26 instrucciones cada uno) | 103 | 105,66 | 107 |
| Del último `EST_k` a `DECISION` (terminar la espera, voto y store) | 89 | 90,34 | 93 |

Los tres gestores publican con un ciclo de diferencia entre uno y otro (134,66, 135,66 y 136,66 en promedio), que es justo el desfase de la rotación: el tercero termina 2 ciclos después que el primero. Lo que sí agrega cada gestor son las 3 instrucciones con que el supervisor revisa su `EST_k` y las 2 de su peso en el voto. En la frontera de ventana el tercer tramo crece hasta 301 ciclos, porque el ajuste de pesos (hasta 42 instrucciones) va antes del voto.

Tick completo: el supervisor hace su última instrucción de trabajo en el ciclo 267,01 en promedio y 475 en el peor tick, y los gestores en el 172,66 y 178. En el peor tick quedan 2025 de los 2500 ciclos sin nada que hacer.

Con el período de la ronda 2 (1 ms, 3000 ticks) la respuesta es la misma: 227,31 en promedio y 439 en el peor caso. Solo crece la espera.

### 7.3 Barrido de la fase y presupuesto de cada ronda

El peor caso depende de en qué punto de sus lazos de espera está cada hilo cuando llega el precio. El lazo de sondeo del supervisor dura 12 ciclos y el de los gestores 8, así que el patrón se repite cada 24 ciclos. Se corrió el inicio de la serie de a un ciclo, 24 veces, con 1100 ticks cada vez (dos fronteras de ventana por corrida):

- Las 24 fases dan 4/4 y decisiones idénticas a la referencia.
- El peor caso por fase va de 433 a 440 ciclos. **Peor caso: 440 ciclos.** El promedio de la respuesta va de 225,35 a 228,37.
- Tomando el máximo de cada tramo por separado, en todos los ticks de las 24 fases: 36 ciclos hasta `PUB`, 107 hasta el último `EST_k` y 301 hasta `DECISION`. La suma es 444.
- Por conteo de instrucciones (hecho a mano, no sale de un script): hasta `PUB` pasan a lo más 36 ciclos (6 instrucciones después del sondeo, cuyo lazo dura 12), cada gestor publica a lo más 107 ciclos después de `PUB` (26 instrucciones más a lo sumo 7 ciclos de su lazo de sondeo), y de ahí a `DECISION` hay a lo más 98 ciclos en un tick común y 306 con la frontera más larga (42 instrucciones más repetir la espera). La suma es 449 ciclos, siempre que los gestores ya estén sondeando cuando se publica el precio. Es una cota razonada, no demostrada.

| Ronda | Presupuesto (ciclos) | Peor caso | Uso | Margen en ciclos | Margen en instrucciones por hilo |
|-------|----------------------|-----------|-----|------------------|----------------------------------|
| 1 (10 ms) | 249 762 | 440 | 0,176 % | 249 322 | 62 330 |
| 2 (1 ms) | 24 762 | 440 | 1,777 % | 24 322 | 6 080 |
| 3 (0,1 ms) | 2 262 | 440 | 19,45 % | 1 822 | 455 |

Comparado con la regla base de `sw/trade.s` (peor caso barriendo la fase: 49 ciclos en el Espino base, 27 en el segmentado y 88 en el hilo 0 del barrel), el fondo responde 5 veces más lento que la regla base en el mismo barrel (440 contra 88). En la ronda 3 queda margen para que cada gestor ejecute unas 455 instrucciones más antes de publicar.

### 7.4 Ocupación

Los cuatro hilos juntos hacen 146,98 instrucciones de trabajo por tick. A 0,1 ms el core tiene 2500 turnos por tick, así que la ocupación es 5,88 %. A 1 ms es 0,59 %. El CPI es 4,000 por hilo y 1,000 agregado por construcción (una instrucción por ciclo, por turnos). Contando solo el trabajo, son 17,0 ciclos por instrucción útil en la ronda 3.

En términos de la ley de hierro, el fondo multiplica el IC por tick por 5 respecto de la regla base (147 instrucciones contra 28,5), el barrel deja el CPI agregado en 1 y el período de reloj no cambia. El techo del barrel son 25 MIPS con los cuatro hilos ocupados, y este programa usa 1,47 MIPS en la ronda más rápida: el barrel está casi siempre esperando. El paralelismo sí se nota en la respuesta: las 105 instrucciones de los tres gestores (3 por 35) cuestan en el camino crítico lo que 26 de un solo hilo.

## 8. Estimado: qué cambiaría con las instrucciones nuevas y con la tabla en BRAM

Nada de esta sección está construido ni medido. Son conteos de instrucciones a mano sobre el programa medido, con las definiciones de `factibilidad/d_isa/ESPECIFICACION.md`. Las instrucciones nuevas no están en el barrel de `factibilidad/a_barrel/`, y su costo en celdas se midió sobre el segmentado, no sobre el barrel.

| Cambio | Dónde actúa | Efecto estimado |
|--------|-------------|-----------------|
| `devk` y `emad` con k = 5 (+113 celdas las dos, medido en el segmentado) | Gestor: `devk` reemplaza las cinco sumas de 32 p y la resta, y `emad` las 8 instrucciones de la media | El gestor baja de 35 a unas 24 instrucciones por tick. Antes de publicar baja de 26 a unas 22: unos 16 ciclos menos de respuesta, de 227. El puntaje tendría que llevarse en treintaidosavos (con k fijo en 5 no hay forma barata de hacer 16 p), lo que no cambia ninguna decisión pero sí la traza |
| `mulstep` (+42 celdas en el sumador de la ALU, medido en el segmentado) | Supervisor, producto de la venta en el espejo: 25 instrucciones pasan a unas 9 (dejar la cantidad en los bits altos y 6 pasos) | En `fondo_min` no cambia la respuesta, porque el espejo va después de `DECISION`. Ahorra unas 16 instrucciones en los ticks con venta (314 de los 20 000 de la serie de práctica) |
| `mulstep` en un fondo con posiciones parciales (`fondo_rec`) | El supervisor tendría que valorizar la posición en cada tick (acciones por precio, 24 por 8 bits) y calcular la orden parcial. El estudio 4B estimó 200 instrucciones en el peor caso con 2 productos y una división | Cada producto baja de unas 48 instrucciones a unas 10: unos 300 ciclos menos en el peor caso, de los cerca de 1200 estimados. Además la valorización no depende de los gestores, así que se puede hacer mientras ellos calculan (sección 4.5) |
| `divstep` (+108 celdas) | Cociente de la compra: 23 instrucciones pasan a unas 11 | No se justifica: va después de `DECISION` y cuesta más celdas que todo lo anterior |
| Tabla de política en BRAM (pieza C) | El gestor reemplaza sus dos comparaciones por una lectura: acotar la desviación a un índice (unas 6 instrucciones sin saltos), sumar la base de su tabla y leer un byte | Unas 6 instrucciones más antes de publicar (24 ciclos de respuesta). El ajuste de la tabla (leer, sumar o desplazar y guardar, unas 8 instrucciones) va después de publicar y no alarga la respuesta. Tres tablas de 256 entradas de un byte ocupan 192 palabras: caben en las 261 libres de la memoria actual, sin tocar las 4 BRAM libres. Llevarlas a las BRAM libres exige un bloque de memoria nuevo en el mapa del SoC, que no está construido ni medido. Cada gestor tendría que ser el único que escribe su tabla |

Lo que no cambia con nada de esto es el piso de la respuesta: unos 31 ciclos para que el supervisor vea el precio y lo publique, y unos 90 entre el último `EST_k` y `DECISION`.

## 9. Qué falta

- **La placa y la maestra real.** Todo es simulación. No se construyó un bitstream con `fondo.hex`. Con el molde de `factibilidad/a_barrel/` y `icebram` el cambio de programa es directo (la tabla de arranque ya viene en el programa), pero no se hizo aquí.
- **El período de 10 ms, más allá de una corrida.** Se corrió una sola vez, con la serie de práctica y la copia del testbench oficial (20 000 ticks, 34 minutos con Verilator): 4/4 y decisiones idénticas. Las series sintéticas, el estado interno y las mediciones por tick no se corrieron a 10 ms. Como el programa no mide el período y la respuesta es la misma a 0,1 ms y a 1 ms, no se espera nada distinto, pero no está medido.
- **El fondo completo.** `fondo_min` no tiene gestor Kalman ni posiciones parciales. `fondo_rec` y `fondo_ancla` no están escritos en assembly: sus costos siguen siendo las estimaciones del estudio 4B.
- **Plazo en el supervisor.** No hay nada que acote el tiempo de un gestor (sección 4.4). Si un gestor se cuelga, el supervisor se queda esperando y no vuelve a escribir `DECISION`. La auditoría lo midió con el gestor del hilo 3 colgado desde el tick 100: la última decisión es la del precio 99. En el hardware I1, que tiene vigilante, la FPGA pide el relevo con el precio 104 (`factibilidad/auditoria_hw/mediciones/cuelgue.txt`). En el barrel solo, la maestra sigue leyendo el último byte hasta el final de la ronda.
- **Rondas seguidas sin reconfigurar.** El programa no se reinicia entre rondas: pesos, puntajes y medias siguen desde donde quedaron, y el espejo de la cuenta deja de coincidir, porque la maestra parte de nuevo con 10 000. La referencia evalúa cada ronda desde cero. En `fondo_min` el espejo no entra en la decisión, pero los pesos aprendidos sí. No se midió.
- **Gemelo digital.** `ref/gemelo/gemelo.c` no modela el barrel. Las equivalencias largas dependen de Verilator: 20 000 ticks a 0,1 ms demoran unos 15 segundos por serie con la copia del testbench oficial, y a 10 ms unos 25 minutos. Las 3810 series del protocolo a los tres períodos no son alcanzables sin el gemelo.
- **Peor caso por análisis.** El peor caso de la sección 7.3 es el máximo observado en 24 fases, no una cota demostrada. Los gestores son de tiempo constante y la frontera de ventana tiene un camino máximo de 42 instrucciones por lectura del código, pero la combinación de fases de los tres lazos de espera no se enumeró.
- **Telemetría.** El programa no usa LEDs ni displays.
- **Verificación con valores X en la memoria.** Verilator simula con dos estados. La corrida con Icarus (cuatro estados) cubre 2000 ticks.

## 10. Días de trabajo para la versión de competencia del programa

Estimación para una persona. Supone que el barrel ya está integrado en `rtl/` (eso está contado en la pieza A).

| Tarea | Días |
|-------|------|
| Fondo completo en assembly: gestor Kalman en punto fijo (7 desplazamientos por tick sin shifter) y supervisor con posiciones parciales (valorización, banda y cociente de 6 pasos), con su traza de referencia | 2,5 |
| Robustez: plazo en el supervisor, inicio de los datos por código y comportamiento definido entre rondas | 0,5 |
| Gemelo digital multihilo: cuatro contextos, rotación de 4 ciclos y memoria compartida en `ref/gemelo/gemelo.c`, validado ciclo a ciclo contra el RTL con las trazas de `tb/tb_fondo.sv` | 1,5 |
| Equivalencia en todas las series del protocolo (3810 series a los tres períodos) con el gemelo, estado interno incluido, y su objetivo en el `Makefile` de la raíz y en la integración continua | 1 |
| Mediciones por tick del punto 3.2 por hilo, barrido de fase y peor caso por análisis | 0,5 |
| Documento de estudio (protocolo, cada bloque de `fondo.s`, preguntas de defensa) | 1 |
| **Total** | **7** |

Si el programa de competencia fuera `fondo_min` tal como está, sobran los 2,5 días de la primera fila y quedan 4,5. El gemelo y el documento de estudio ya están contados en la estimación de la pieza A (1,5 y 1 día), así que no se suman dos veces: sobre los 7 días de la pieza A, el fondo completo agrega unos 4,5 y `fondo_min` unos 2.

## 11. Reglas del enunciado

| Regla | Cumple | Comentario |
|-------|--------|------------|
| "La decisión se debe calcular en el Espino Core en la placa. El core debe leer el precio y escribir la decisión; el hardware agregado puede acelerar partes del algoritmo, pero no reemplazar al procesador en el ciclo de decisión." | Sí, con una duda | Todo el cálculo son instrucciones de la ISA ejecutadas por el core: un hilo lee `PRICE` y escribe `DECISION`, y los otros tres calculan y le entregan su resultado por memoria. Esta pieza no agrega hardware. La duda es la misma de la pieza A: si varias estrategias en hilos del mismo core cuentan como "el core" |
| "No se puede usar información externa a la serie recibida por SPI ni almacenar series de precios en el diseño distintas de la que se está stremeando." | Sí | El programa guarda una media por gestor, tres puntajes, tres pesos y la cuenta. No guarda precios pasados |
| "Todo hardware agregado debe estar en el repositorio con su testbench." | No aplica | No hay hardware nuevo. El programa tiene su testbench (`tb/tb_fondo.sv`) y pasa el oficial |
| "Deben usar el mismo programa para todas las series de tiempo." | Sí | Un solo programa. No mide el período ni cambia de modo: las mismas decisiones a 0,1 ms y a 1 ms |
| "Pueden modificar libremente el RTL, siempre que el procesador siga siendo Espino." | Depende de la pieza A | El RTL es el de `factibilidad/a_barrel/`, sin cambios |
| El testbench oficial no se modifica y entra por jerarquía a `dut.u_spi.*` | Sí | Compila y entrega 4/4 sin tocarlo |
| Regla propia: nada derivado punto a punto de la serie de práctica | Sí | Las constantes son los umbrales de tres candidatos del frente del algoritmo (3, 4 y 2 bajo la media), el prior 6/5/5, la ventana de 512 ticks y el margen de 1/32. No hay tablas |

Preguntas para el ayudante, además de las tres de la pieza A: si un programa en que tres hilos calculan estrategias y un cuarto decide cumple "el core debe leer el precio y escribir la decisión", y si las mediciones por tick del punto 3.2 se informan por hilo o sumadas.

## 12. Riesgos

1. **El algoritmo no gana.** Es el riesgo que decide: el fondo no mejora los puntos contra `max_media` en ninguna de las configuraciones que midió el estudio 4B.
2. **Un gestor que no cabe en el tick hace perder precios, y en la placa eso no se ve.** Quedó medido (sección 4.4). El programa actual está lejos de ese límite (35 instrucciones por gestor de las 625 del turno), pero un gestor más pesado o de tiempo variable lo acerca, y no hay plazo que lo proteja.
3. **El software concurrente depende de una regla que nadie hace cumplir.** "Un solo hilo escritor por palabra" es una convención del programa. El ensamblador no la revisa. Un cambio que la rompa puede pasar las pruebas cortas y fallar con otra fase. La auditoría lo mostró con dos casos concretos. Un supervisor que deja de esperar al gestor 3 pasa la equivalencia nominal sin una sola diferencia, y solo lo detectan `make variantes` y la prueba de carreras. Uno que deja de esperar al gestor 2 pasaba además la variante `atraso_800`: hasta que se agregó `atraso_800_g2`, ninguna prueba de esta carpeta lo veía. Cualquier cambio al protocolo debería pasar por `make -C factibilidad/auditoria_hw carreras` (2 minutos).
4. **La respuesta es más lenta que la de la regla base:** 3 veces en promedio (227 ciclos contra 75) y 5 en el peor caso (440 contra 88) en el mismo barrel, y 10 veces en promedio contra el segmentado (22). Sobra plazo, pero es el costo de esperar a tres hilos que avanzan una instrucción cada 4 ciclos.
5. **No hay gemelo digital del barrel.** Sin él no se puede correr el protocolo completo con el binario.
6. **Todo depende de la pieza A:** de que el barrel pase por la maestra el 26/11 y de la respuesta del ayudante sobre si un Espino multihilo sigue siendo Espino.
7. **Entre rondas el estado no se reinicia** (sección 9).

A favor: los gestores son de tiempo constante, el protocolo no depende de los ciclos (el mismo flujo de bytes en 24 fases, dos períodos y con atrasos puestos a propósito), el estado interno completo coincide con la referencia y no solo los bytes, y queda la mitad de la memoria libre.

## 13. Veredicto

**Hardware (cabe junto al SPI y cierra a 25 MHz en 10 semillas).** Esta pieza no agrega ni cambia hardware: usa el SoC barrel de la pieza A, que mide 934 de 1280 celdas y 12 de 16 BRAM y cierra en 10 de 10 semillas (`factibilidad/a_barrel/mediciones/recursos.txt`; no se volvió a medir aquí, porque el contenido de la memoria no cambia la síntesis). El programa ocupa 251 de las 512 palabras. Pasa.

**Tiempo.** Peor caso de 440 ciclos de 2262 en la ronda 3 (19,45 %), 4/4 en el testbench oficial. Pasa con margen.

**Equivalencia.** Cero diferencias con la referencia en C en 220 000 ticks con períodos de 0,1 ms, 1 ms y 10 ms, más el estado interno en 82 991 ticks. Pasa.

**Algoritmo (mejorar los puntos esperados sin empeorar el percentil 5).** No pasa. Lo midió el estudio 4B con la semilla 0: `fondo_min` da +0,000 ± 0,000 puntos contra `max_media` a 2000 ticks (H3a y H3b) y -0,018 ± 0,002 (H3a) y -0,003 ± 0,002 (H3b) a 20 000 ticks en las series interiores, con veredicto `NO_PASA` en los dos largos. Ninguna otra configuración del fondo pasa.

**Conclusión: el fondo de cuatro hilos se descarta de la edición de competencia por el criterio de algoritmo, no por el de hardware ni por el tiempo, y pasa a la edición de exhibición.** Como exhibición está completo en lo que importa para defenderlo: corre en el barrel, pasa el testbench oficial con 4/4, decide byte a byte como su modelo, y a 2000 ticks no cuesta puntos. Lo que deja medido para el resto del proyecto:

- un protocolo entre hilos sin carreras y que no depende de los ciclos, reutilizable si el barrel se usa para otra cosa;
- que el trabajo que un hilo hace mientras los otros calculan no alarga la respuesta (5,5 ciclos por mover el espejo), y que lo que un gestor hace después de publicar tampoco;
- el modo de falla cuando un hilo no cabe en el tick;
- el costo real de un gestor de reversión (35 instrucciones) y del espejo de la cuenta (75 palabras, hasta 39 instrucciones), que reemplazan las estimaciones del estudio 4B (38 por gestor, 35 y 80 para el supervisor).

## 14. Cómo reproducir

Desde la raíz del repositorio o desde esta carpeta. Los scripts agregan OSS CAD Suite al `PATH`. `make retorno` necesita las series del arnés ya generadas (`make -C factibilidad/retorno series`).

| Comando | Qué mide | Salida | Demora medida |
|---------|----------|--------|---------------|
| `make -C factibilidad/b_fondo_hilos arnes` | Compila la referencia en C | `build/arnes` | segundos |
| `make -C factibilidad/b_fondo_hilos programa` | Tamaño del programa por bloque | `mediciones/tamano.txt` | 1 s |
| `make -C factibilidad/b_fondo_hilos oficial` | Testbench oficial sin modificar, Icarus | `mediciones/oficial.txt` | 5 min |
| `make -C factibilidad/b_fondo_hilos equiv` | Copia parametrizada, 10 casos de 20 000 ticks | `mediciones/equiv.txt` | 5 min |
| `make -C factibilidad/b_fondo_hilos estado` | Estado interno contra la traza en C | `mediciones/estado.txt` | 1 min |
| `make -C factibilidad/b_fondo_hilos ticks` | Instrucciones y ciclos por tick, barrido de fase | `mediciones/ticks.txt` | 1 min |
| `make -C factibilidad/b_fondo_hilos variantes` | Variantes del protocolo | `mediciones/variantes.txt` | 3 min |
| `make -C factibilidad/b_fondo_hilos retorno` | Patrimonio de `fondo_min` contra `max_media` | `mediciones/retorno.txt` | 20 s |
| `make -C factibilidad/b_fondo_hilos todo` | Todo lo anterior | | unos 15 min |
| `make -C factibilidad/b_fondo_hilos equiv-ronda1` | `make equiv` más el período de 10 ms | `mediciones/equiv.txt` | 34 min |

Herramientas: OSS CAD Suite del 2026-09-06 (Yosys 0.68+195, Icarus Verilog 14.0, Verilator 5.053) y gcc.

## 15. Auditoría

Esta pieza se revisó junto con el diseño integrado. Los scripts, las salidas y el detalle están en `factibilidad/auditoria_hw/` (su README, secciones 4 a 10). Aquí va lo que toca a esta carpeta.

**Lo que se confirmó.**

| Qué | Cómo | Resultado |
|-----|------|-----------|
| Equivalencia con la referencia en C | `tb/tb_fondo.sv` con las 14 familias de `ref/series.py` y las semillas 2 y 3 (28 series de 20 000 ticks que este estudio no había corrido), más la práctica a 0,1 ms y a 1 ms | 30 casos sobre el barrel: 4/4, decisiones idénticas y 13 campos de estado idénticos en todos los ticks |
| El mismo programa en el hardware I1 | Barrel con extensión, vigilante y tabla, de `factibilidad/i_integrado`: la práctica a 0,1 ms y a 1 ms y dos series sintéticas | 4 casos idénticos. En total 646 000 ticks y 645 934 filas de estado sin una diferencia |
| Testbench oficial | Sin modificar, con Icarus, sobre el barrel y sobre I1 | 4/4, 439 ciclos, `decisiones.csv` idéntico al de la referencia en los dos. En I1 el vigilante no dispara |
| Peor caso de la respuesta | 20 000 ticks con la fase de llegada al azar, sin retardos | 440 ciclos, el mismo del barrido de 24 fases |
| Las salidas guardadas | `make programa`, `ticks`, `variantes`, `estado`, `oficial` y `equiv` repetidos | Ver `factibilidad/auditoria_hw/mediciones/repeticion.txt` |
| Las cifras de este documento | Cada tabla contra el archivo de `mediciones/` que cita | Coinciden. No hubo que corregir ningún número |
| Reglas del enunciado, sobre I1 | Quién accede al esclavo SPI y con qué instrucción, y qué palabras de memoria cambian en 20 000 ticks | Solo el hilo 0, con `lw` y `sw`. Cambian 17 palabras, todas del estado del programa |

**Lo que se corrigió.**

1. Este documento tenía seis marcas sin reemplazar (el resumen de la equivalencia, la fila de 10 ms, el total de ticks y la demora). Los números estaban medidos y guardados en `mediciones/equiv.txt`: faltaba pasarlos al texto. `AVANCE.md` decía que faltaban `make ticks`, `make variantes` y `make programa`, que ya estaban corridos.
2. **Ninguna prueba de esta carpeta ejercitaba la espera del gestor 2.** La prueba de carreras cuenta cuántas veces el supervisor carga un `EST_k` que todavía es de otro tick y tiene que volver a leer. Sin retardos, en 20 000 ticks: 159 982 veces con `EST_1`, y ninguna con `EST_2` ni con `EST_3`. La variante `atraso_800` cubría al gestor 3. Al gestor 2 no lo cubría nada: un supervisor que no comprueba el número de tick de `EST_2` pasaba la equivalencia nominal y `atraso_800`. Se agregó la variante `atraso_800_g2` a `tools/variantes.sh` (el gestor 2 atrasado 800 ciclos). El programa sano la pasa con 4/4 y decisiones y estado idénticos, y ese error se detecta desde la fila 58. `make variantes` tiene ahora diez corridas, y las nueve anteriores dan lo mismo que antes.

**Carreras entre hilos.** Se buscó un caso en que el supervisor decida con datos mezclados de dos ticks.

- Por lectura de `sw/fondo.s` y del core no se encontró ninguno. El argumento de la sección 4.3 se sostiene.
- Con una prueba hecha para eso (`factibilidad/auditoria_hw/tb/tb_carreras.sv`): la llegada del precio se corre una cantidad al azar en cada tick, y los tres gestores y el supervisor demoran una cantidad distinta y al azar en cada tick, antes y después de publicar, leyendo los interruptores de la placa. Se probaron además períodos de 0,06 y 0,04 ms, en que el fondo pierde precios, y un retardo con el que la vuelta de un gestor no cabe en el tick. Nueve monitores miran cada escritura en `PUB`, `EST_k`, `DES_k` y `DECISION` y cada carga de `EST_k` que hace el supervisor, y el estado se compara con la referencia corrida sobre los precios que el supervisor vio.
- Resultado: 19 corridas, 337 174 decisiones, cero violaciones, y los 13 campos del estado iguales al modelo en todas. También cuando se pierde el 42 % de los precios, y también en la variante `anterior`. En ninguna decisión el supervisor había cargado un `EST_k` de otro tick. Con los retardos, las tres esperas se ejercitan: sumando las 19 corridas, el supervisor tuvo que volver a leer `EST_1` 9,3 millones de veces, `EST_2` 2,2 millones y `EST_3` 1,5 millones.

**Mutaciones del protocolo.** Seis errores puestos en copias de `sw/fondo.s`.

| Mutación | `make equiv` y `make estado` | Variante `atraso_800` | Variante `atraso_800_g2` | Prueba de carreras |
|----------|------------------------------|-----------------------|--------------------------|--------------------|
| `PUB` en dos stores (tick y precio por separado) | la detectan, desde la fila 6 | la detecta | la detecta | la detecta |
| El supervisor no mira el número de tick de `EST_1` | la detectan, desde la fila 58 | la detecta | la detecta | la detecta |
| El gestor sella `EST_k` con el tick anterior | la detectan: el supervisor se queda esperando, 2/4 | la detecta | la detecta | la detecta |
| El supervisor no espera al gestor 3 | **no la detectan**: 20 000 filas idénticas | la detecta, desde la fila 419 | no | la detecta: 224 decisiones tomadas con un `EST_3` cargado del tick anterior |
| El supervisor no espera al gestor 2 | **no la detectan**: 20 000 filas idénticas | **no** | la detecta, desde la fila 58 | la detecta: 300 decisiones tomadas con un `EST_2` cargado del tick anterior |
| El gestor publica `EST_k` antes que `DES_k` | no | no | no | solo el monitor del orden. Ninguna decisión ni peso cambia |

Dos lecturas:

1. **La equivalencia nominal no alcanza para afirmar que el supervisor espera a los tres gestores.** Con los gestores de tiempo constante, los gestores 2 y 3 siempre publican antes de que el supervisor llegue a leerlos. Lo que sostiene la segunda fila de la tabla de la sección 4.3 es `make variantes`, no `make equiv`, y para eso hace falta una variante por gestor: `atraso_800` para el 3 y `atraso_800_g2` para el 2. La espera del gestor 1 se ejercita sola.
2. **El orden "primero `DES_k`, después `EST_k`" no se ejercita.** Invertirlo no cambia nada, porque el supervisor tarda al menos tres instrucciones entre leer `EST_k` y leer `DES_k`, y el gestor escribe las dos palabras en instrucciones seguidas. El orden importaría con un gestor que hiciera trabajo entre los dos stores, y ahí ninguna prueba de equivalencia lo avisaría.

**Un gestor colgado.** Medido: el supervisor deja de responder desde ese tick (sección 9). En el hardware I1 el vigilante lo convierte en un relevo.

**Días de trabajo.** Los 7 días de la sección 10 (4,5 sobre los del barrel) son coherentes con los 5 que supone el diseño integrado. No cambian la conclusión: el fondo se descarta de la competencia por el criterio de algoritmo, que la auditoría no revisó. Lo que se comprobó aquí es que el programa hace lo que hace su referencia, no que la referencia gane.

**Cómo se reproduce.** `make -C factibilidad/auditoria_hw todo` (unos 17 minutos) y `make -C factibilidad/auditoria_hw repeticion` (8 minutos).

