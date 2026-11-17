# Revisión adversarial de R1 y R2 (paquete P10)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Rama `p10-revision`, desde `main` (`a042795`), 17/11. El revisor no participó en el diseño de R1 ni de R2. Se leyó el RTL del barrel, de la extensión, de la tabla, del vigilante y de la integración en el SoC, y `sw/fondo.s` con su referencia `ref/fondo.py`, buscando fallas; para cada sospecha se escribió una prueba que la reproduce o la descarta, y se repitió desde cero la puerta de simulación de R1 y de R2. La bitácora del trabajo está en `docs/bitacora/p10.md`.

Resumen: **no se encontró ningún defecto crítico ni alto.** Hay un defecto real en el esclavo SPI del curso, que el diseño hereda sin cambios (hallazgo 1): con una condición del bus que la maestra del testbench nunca produce, el esclavo inventa precios, y en R2 eso dispara el vigilante. El resto son observaciones. La puerta repetida da los mismos resultados que los registrados en `docs/puertas.md` (sección 3).

## 1. Hallazgos por severidad

### Crítico

Ninguno.

### Alto

Ninguno.

### Medio (condicional): hallazgo 1, precios fantasma del esclavo SPI con el contador de bits en 7

**Qué es.** En `rtl/pochoco_spi_slave.v:74`, `byte_done = sclk_r & (bit_cnt == 4'd7)` no mira `CS_n`, y `bit_cnt` solo vuelve a 0 cuando `CS_n` baja (`:81-83`); con `CS_n` en alto no cambia. Si una transacción termina con `bit_cnt` en 7, desde ese momento **cada flanco de subida de SCLK con `CS_n` en alto es un precio completo**: `price_q` toma `{rx_shift[6:0], mosi}`, la bandera de precio nuevo sube y el pulso llega al vigilante. Dura hasta la próxima bajada de `CS_n`.

`bit_cnt` queda en 7 de dos maneras: una transacción de 7 flancos (un corte o un rebote), o el reset de encendido terminando a mitad de una transacción con 7 flancos por delante (`cs_sync` sale del reset en 111, ve `CS_n` en bajo, genera `cs_assert` y pone `bit_cnt` en 0 a mitad del byte). La segunda ocurre de verdad en la matriz de estrés (`reset_flanco_*`), pero ahí no pasa nada porque la maestra no mueve SCLK con `CS_n` en alto.

**Reproducción.** `make p10-spi-7flancos` (`tools/p10/spi_7flancos.sh`, `tb/p10/tb_p10_spi.sv`, unos 7 s con Icarus). Corre `sw/fondo.s` en el hardware de R1 y de R2 con la transacción del testbench oficial cada 100 us, y 20 flancos de SCLK a 1 MHz con `CS_n` en alto:

| Escenario | R1 | R2 |
|-----------|----|----|
| 0. Control: transacción normal y después 20 flancos con `CS_n` en alto | 0 precios fantasma | 0, sin disparo |
| 1. Transacción de 7 flancos y después 20 flancos con `CS_n` en alto | 20 precios fantasma (precio 120), 2 decisiones de más | 20, **el vigilante pide la reconfiguración** (ciclo 15 480) |
| 2. La primera transacción empieza 1600 ns antes del fin del reset, y después 20 flancos con `CS_n` en alto | 20 precios fantasma (precio 200; la maestra mandó 100) | 20, **el vigilante pide la reconfiguración** (ciclo 4 460) |

Observado: `byte_done` con `CS_n` en alto, y en R2 `BOOT` en 1. Esperado de un esclavo correcto: ningún precio fuera de una transacción y ningún disparo. El comentario de `rtl/vigilante.v:24-26` ("si el ruido llegara a completar uno, el programa lo lee como un precio y responde, y la cuenta vuelve a cero") no se cumple en este caso: llegan 5 precios en 5 us, mucho antes de que el supervisor responda uno.

**Consecuencia para la competencia.** Necesita, además del contador en 7, flancos de SCLK con `CS_n` en alto, que el testbench oficial no tiene. En la placa eso pasa si la maestra comparte SCLK con otro esclavo (por ejemplo, varias placas en el mismo bus con un `CS_n` cada una), si su SCLK reposa en alto, o con ruido en el PMOD mientras está desconectado (`goboard.pcf` no pone pull-up en ninguna entrada del SPI). No sabemos cómo es la maestra real.

- **R2**: el vigilante dispara en un programa sano. Relevo a R0: unos 536 ticks sin decisión nueva a 0,1 ms (53 ms de la hoja de datos, sin medir) y el resto de la ronda con R0. La pérdida esperada es acotada (R0 decide igual que el fondo en la práctica), pero es justamente el disparo que la puerta exige que nunca ocurra.
- **R1 y R0**: precios inventados entran a las medias, y el supervisor de R1 decide sobre ellos. Si pasa antes del primer precio, la media parte en un valor falso y tarda unos 100 ticks en olvidarlo.

Severidad media para R2 si el 26/11 se ven flancos de SCLK con `CS_n` en alto; baja si no. Hoy el medidor del 26/11 no puede verlo (hallazgo 4).

**Arreglo propuesto (rama `p10-arreglo-1`).** Una línea en el esclavo. Con el arreglo, `make p10-spi-7flancos` pasa en los 6 casos, y el testbench oficial da 4/4 con R0, R1 y R2 (resultados en la sección 4). Cambia el hardware de los tres peldaños, así que exige repetir sus puertas y regenerar los bitstreams antes del 25/11. Decisión de Nicolás.

**Mitigación sin cambiar el hardware.** Conectar el PMOD (tierra primero) antes de grabar la placa, que ya es el orden de `docs/checklist_26nov.md`; preguntar al ayudante si el bus de la maestra es compartido; y medir el 26/11 si hay flancos de SCLK con `CS_n` en alto con el medidor de la rama `p10-arreglo-2` o con un analizador lógico.

### Bajo: hallazgo 4, el medidor del 26/11 no detecta flancos de SCLK con `CS_n` en alto

**Qué es.** `rtl/medidor/medidor_spi.v:133-149` cuenta flancos solo con `CS_n` en bajo; LED4 se enciende si una transacción no tuvo 8. La condición que activa el hallazgo 1 pasa inadvertida.

**Reproducción.** Lectura del código. En la rama `p10-arreglo-2` el testbench del medidor tiene el caso nuevo; con el módulo de `main` ese caso falla (es el control negativo `sin_alarma_cs_alto` de `tools/medidor.sh`).

**Arreglo propuesto (rama `p10-arreglo-2`).** LED4 se enciende también con un flanco de subida de SCLK con `CS_n` en alto. `make medidor` en la rama: 68 comprobaciones sin fallas, 5 de 5 controles negativos detectados, 10 de 10 semillas (mínima 110,01 MHz, 610 celdas), el mismo testbench sobre el bitstream ruteado, y `bitstreams/medidor_spi.bin` nuevo con su hash. `docs/checklist_26nov.md` explica la nueva lectura de LED4. El medidor no es hardware de competencia, así que este arreglo no toca ningún peldaño.

### Observaciones

**Observación 1: el número de tick da la vuelta a los 16 777 216 ticks.** `sw/fondo.s:197` lleva tick por 256 en `x3`. El programa sano pasa la vuelta sin diferencias (`make p10-vuelta-tick`: variante de `sw/fondo.s` que solo cambia el valor inicial de `x3` para que vuelva a 0 en el tick 1024; 2 000 ticks en dos series idénticos a la referencia). Con un gestor colgado desde el arranque, su `EST` queda en 0, y en el tick en que `x3` vuelve a 0 la resta de `sw/fondo.s:217-225` da 0 y el voto viejo cuenta como de este tick: la prueba lo muestra (1 997 ticks por plazo en vez de 1 998). Como 2^24 es múltiplo de 512, ese tick además es frontera, y los pesos se ajustarían con el puntaje 0 del gestor colgado. Solo pasa después de 28 minutos seguidos a 0,1 ms con un gestor colgado: no afecta la competencia. No se propone arreglo.

**Observación 2: la primera transacción de una ronda sin reset lee la última decisión de la ronda anterior.** `tx_hold` y el estado del programa (medias, posición, pesos) siguen de una ronda a la otra. Ya está anotado en `docs/fondo.md:381`, la referencia lo modela igual y la matriz de estrés lo prueba; vale también para R0. Lo que no está medido es cuánto cuesta: si la maestra reinicia la caja entre rondas pero la placa no, la ronda nueva parte ejecutando la última orden de la anterior y con la media de otra serie. Conviene medirlo con `ref/fondo.py` (dos series de niveles distintos de corrido, contra la segunda sola) para decidir si se reprograma entre rondas.

**Observación 3: entradas del SPI sin pull-up.** `goboard.pcf:39-42` no pone `-pullup yes` en `CS_n`, SCLK ni MOSI. Con el PMOD desconectado las entradas flotan y pueden fabricar precios o dejar el contador del hallazgo 1 en 7. El orden del checklist (conectar y después grabar) lo evita. Un pull-up en `CS_n` lo resolvería del todo, pero cambia los tres bitstreams; no se propone para competencia.

### Verificado sin hallazgo

Cada punto de la lista del paquete se revisó; lo que sigue no mostró defectos.

| Sospecha | Cómo se revisó | Resultado |
|----------|----------------|-----------|
| Precio que llega con el supervisor a mitad del cálculo; carrera al limpiar la bandera de precio nuevo | Lectura de `pochoco_spi_slave.v:99-108` y `sw/fondo.s:188-266` | Si `byte_done` y la lectura de PRICE caen en el mismo ciclo, la bandera queda arriba y el core recibe el precio anterior, que es el suyo: no se pierde ni se duplica nada. Todos los caminos del supervisor terminan en una sola escritura de DECISION |
| Tabla de solo lectura, también con desplazamientos que coinciden con DECISION, LED y 7 segmentos | `make p10-ro-custom0` (R1 y R2) | 31 de 31 palabras esperadas; sw, sh y sb a `0x8002_xxxx`, `0x8003_xxxx` y `0x8007_0008` no cambian la tabla ni escriben DECISION, LED o 7 segmentos. Controles negativos: sin la tabla (11 comprobaciones fallan) y con `mulstep` (4) |
| Palabras de custom-0 que no son `emad` ni `devk` | La misma prueba: 182 palabras (8 `funct3` por 10 `funct7`, más custom-1, 2 y 3) | No escriben rd (tres centinelas, incluido x2), no tocan la memoria y no saltan |
| `emad` y `devk` en los bordes | La misma prueba, contra la fórmula de `docs/extension_isa.md` calculada en Python | 17 casos iguales: signo, redondeo hacia menos infinito (-31, -32, -33), desborde, rd igual a rs1 y rs2, rd = x0 |
| Voto viejo, ventana cada 512 ticks y topes de los pesos | Lectura contra `ref/fondo.py:186-232` | Mismo orden de comparaciones; la frontera solo corre con los tres votos al día y ningún gestor escribe hasta que cambie PUB |
| Rondas de 200 000 ticks por el RTL (la puerta llega a 20 000; las de 200 000 solo las corrió el gemelo) | `make p10-largo` (R2, 0,1 ms, familias `modelo` y `volatil`) | Todo idéntico a la referencia: bytes, estado en cada decisión, telemetría, una escritura por precio; 314 cambios de pesos en una de ellas; vigilante nunca sobre 1; peor caso 443 |
| SCLK lento con el fondo degradado | `make p10-sclk-degradado` (exploración, RTL de R1) | Con un gestor colgado o atrasado, decide igual que la referencia desde 110 kHz; a 105 kHz el colgado da 40 bytes distintos. La regla de 115 kHz del árbol cubre también la degradación |
| `PLAZO = 0` en la tabla colgaría al supervisor si un gestor muere | Lectura | `ref/fondo.py:252` rechaza la tabla |
| MISO con X o Z | Lectura de `pochoco_spi_slave.v:95` y del reset | MISO sale de un flip-flop con reset y nunca queda en Z; la puerta lo exige en cada corrida |
| PC de 11 bits | Lectura; criterio 5 compara también con PC de 32 bits (grupo W) | Sin diferencias en la campaña repetida |
| Vigilante con escritura y precio en el mismo ciclo, o disparo en una corrida sana | Lectura de `rtl/vigilante.v:67-83`; `make p10-largo` y la puerta repetida | La cuenta queda en 1; BOOT espera `CS_n` en alto; ninguna corrida sana pasó de 1 |

## 2. Lo que no se verificó

- Nada en la placa: ni el hallazgo 1 con una maestra real, ni el tiempo del relevo.
- El arreglo 1 no pasó la puerta completa: solo las pruebas de la sección 4.

## 3. Puerta de simulación repetida desde cero

PENDIENTE

## 4. Pruebas agregadas

PENDIENTE
