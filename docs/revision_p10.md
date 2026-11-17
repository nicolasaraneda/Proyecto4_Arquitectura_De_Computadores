# Revisión adversarial de R1 y R2 (paquete P10)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Rama `p10-revision`, desde `main` (`a042795`), 17/11. El revisor no participó en el diseño de R1 ni de R2. Se leyó el RTL del barrel, de la extensión, de la tabla, del vigilante y de la integración en el SoC, y `sw/fondo.s` con su referencia `ref/fondo.py`, buscando fallas; para cada sospecha se escribió una prueba que la reproduce o la descarta, y se repitió desde cero la puerta de simulación de R1 y de R2. La bitácora del trabajo está en `docs/bitacora/p10.md`.

Resumen: **no se encontró ningún defecto crítico ni alto en R1 ni en R2.** El barrel, la extensión, la tabla, el vigilante y `sw/fondo.s` resistieron todas las pruebas nuevas. Hay un defecto real en el esclavo SPI del curso, que los tres peldaños heredan sin cambios (hallazgo 1): con una condición del bus que la maestra del testbench nunca produce, el esclavo inventa precios, y en R2 eso dispara el vigilante en un programa sano. El resto son observaciones; dos de ellas (rondas sin reinicio y modo SPI) tienen consecuencias para la competencia y piden una decisión o una pregunta al ayudante. La puerta repetida está en la sección 3.

## 1. Hallazgos por severidad

### Crítico

Ninguno.

### Alto

Ninguno.

### Bajo, sube a medio si la maestra real mueve SCLK con `CS_n` en alto: hallazgo 1, precios fantasma del esclavo SPI

**Qué es.** En `rtl/pochoco_spi_slave.v:74`, `byte_done = sclk_r & (bit_cnt == 4'd7)` no mira `CS_n`, y `bit_cnt` solo vuelve a 0 cuando `CS_n` baja (`:81-83`); con `CS_n` en alto conserva su valor. Si una transacción termina con `bit_cnt` en 7, desde ese momento **cada flanco de subida de SCLK con `CS_n` en alto es un precio completo**: `price_q` toma `{rx_shift[6:0], mosi}`, la bandera de precio nuevo sube y el pulso llega al vigilante. Dura hasta la próxima bajada de `CS_n`.

`bit_cnt` queda en 7 de dos maneras: una transacción de 7 flancos (un corte o un rebote), o el reset de encendido terminando a mitad de una transacción con 7 flancos por delante (`cs_sync` sale del reset en 111, ve `CS_n` en bajo, genera `cs_assert` y pone `bit_cnt` en 0 a mitad del byte). La segunda ocurre de verdad en la matriz de estrés (`reset_flanco_*`), pero ahí no pasa nada porque la maestra no mueve SCLK con `CS_n` en alto.

**Reproducción.**

- `make p10-spi-7flancos` (`tools/p10/spi_7flancos.sh`, `tb/p10/tb_p10_spi.sv`, unos 7 s con Icarus). Corre `sw/fondo.s` en el hardware de R1 y de R2 con la transacción del testbench oficial cada 100 us, y 20 flancos de SCLK a 1 MHz con `CS_n` en alto. Termina con error mientras el defecto esté.
- `make p10-formal-spi` (`tools/p10/formal_spi.sh`, `formal/p10/spi_byte.v`, menos de 1 s). Afirmación formal sobre el esclavo con todas sus entradas libres: "un precio solo se completa si `CS_n` estaba en bajo en el ciclo anterior". Con el RTL de `main` falla en el paso 18 y deja el contraejemplo en `build/p10/formal_spi/spi_prove/engine_0/trace.vcd`. El repositorio no tenía ninguna propiedad formal del esclavo SPI, aunque el frente D del plan la pedía.

| Escenario de `p10-spi-7flancos` | R1 | R2 |
|-----------|----|----|
| 0. Control: transacción normal y después 20 flancos con `CS_n` en alto | 0 precios fantasma | 0, sin disparo |
| 1. Transacción de 7 flancos y después 20 flancos con `CS_n` en alto | 20 precios fantasma (precio 120), 2 decisiones de más | 20, **el vigilante pide la reconfiguración** (ciclo 15 480) |
| 2. La primera transacción empieza 1600 ns antes del fin del reset, y después 20 flancos con `CS_n` en alto | 20 precios fantasma (precio 200; la maestra mandó 100) | 20, **el vigilante pide la reconfiguración** (ciclo 4 460) |

Observado: `byte_done` con `CS_n` en alto y, en R2, `BOOT` en 1. Esperado de un esclavo correcto: ningún precio fuera de una transacción y ningún disparo. El comentario de `rtl/vigilante.v:24-26` ("si el ruido llegara a completar uno, el programa lo lee como un precio y responde, y la cuenta vuelve a cero") no se cumple en este caso: llegan 5 precios en 5 us, mucho antes de que el supervisor responda uno.

**Consecuencia para la competencia.** Necesita, además del contador en 7, flancos de SCLK con `CS_n` en alto, que el testbench oficial no tiene. En la placa eso pasa si la maestra comparte SCLK con otro esclavo (por ejemplo, varias placas en el mismo bus con un `CS_n` cada una), o con ruido en el PMOD mientras está desconectado (`goboard.pcf:39-42` no pone pull-up en ninguna entrada del SPI). No sabemos cómo es la maestra real.

- **R2**: el vigilante dispara con un programa sano. Relevo a R0: unos 536 ticks sin decisión nueva a 0,1 ms (53 ms de la hoja de datos, sin medir) y el resto de la ronda con R0. La pérdida esperada es acotada, porque R0 decide igual que el fondo en la serie de práctica, pero es justamente el disparo que la puerta exige que nunca ocurra.
- **R1 y R0**: precios inventados entran a las medias, y el supervisor de R1 decide sobre ellos. Si pasa antes del primer precio, la media parte en un valor falso y tarda unos 100 ticks en olvidarlo.

Hoy el medidor del 26/11 no puede ver esa condición (hallazgo 2).

**Arreglo propuesto: rama `p10-arreglo-1`, commit `b99205d`.** Parámetro `CsLimpia` en el esclavo: con 1, `bit_cnt` vuelve a 0 desde el segundo ciclo con `CS_n` en alto (un octavo flanco que se ve en el mismo ciclo en que sube `CS_n` sigue completando el byte, como antes). `pochoco_soc.v` lo pone en 1 solo con el barrel (`Pipeline == 3`), así que R1 y R2 cambian y R0 y el segmentado conservan el esclavo del curso; el bitstream de R0 no se toca. Una primera versión que exigía `CS_n` en bajo en `byte_done` se descartó porque perdía el precio si el octavo flanco y la subida de `CS_n` se ven en el mismo ciclo. Lo comprobado y lo que falta está en la sección 3.2. Cambia el hardware de R1 y R2: exige repetir sus puertas, regenerar sus bitstreams, moldes y autopruebas, y pasar por la placa antes del 25/11. Decisión de Nicolás.

**Mitigación sin cambiar el hardware.** Conectar el PMOD (tierra primero) antes de grabar la placa, que ya es el orden de `docs/checklist_26nov.md`; preguntar al ayudante si el bus de la maestra es compartido; y medir el 26/11 si hay flancos de SCLK con `CS_n` en alto, con el medidor de la rama `p10-arreglo-2` o con un analizador lógico. Si los hay y no se adopta el arreglo, competir con R1 y no con R2.

### Bajo: hallazgo 2, el medidor del 26/11 no detecta flancos de SCLK con `CS_n` en alto

**Qué es.** `rtl/medidor/medidor_spi.v:133-149` cuenta flancos solo con `CS_n` en bajo; LED4 se enciende si una transacción no tuvo 8. La condición que activa el hallazgo 1 pasa inadvertida, y el modo SPI de la maestra tampoco se ve (observación 4).

**Reproducción.** Lectura del código. En la rama `p10-arreglo-2` el testbench del medidor tiene el caso nuevo; con el módulo de `main` ese caso falla (es el control negativo `sin_alarma_cs_alto` de `tools/medidor.sh`).

**Arreglo propuesto: rama `p10-arreglo-2`, commit `ff61971`.** LED4 se enciende también con un flanco de subida de SCLK con `CS_n` en alto. `make medidor` en la rama: 68 comprobaciones sin fallas, 5 de 5 controles negativos detectados, 10 de 10 semillas a 25 MHz (mínima 110,01 MHz, 610 celdas), el mismo testbench sobre el bitstream ruteado, y `bitstreams/medidor_spi.bin` nuevo con su hash. `docs/checklist_26nov.md` explica la nueva lectura de LED4. El medidor no es hardware de competencia: este arreglo no toca ningún peldaño. La alarma por modo 3 (observación 4) se agregó después y su resultado está en la sección 3.2.

### Observaciones

**Observación 1: el número de tick da la vuelta a los 16 777 216 ticks.** `sw/fondo.s:197` lleva tick por 256 en `x3`. El programa sano pasa la vuelta sin diferencias: `make p10-vuelta-tick` arma una variante de `sw/fondo.s` que solo cambia el valor inicial de `x3` para que vuelva a 0 en el tick 1024, y da 2 000 ticks en dos series idénticos a la referencia. Con un gestor colgado desde el arranque, su `EST` queda en 0, y en el tick en que `x3` vuelve a 0 la resta de `sw/fondo.s:217-225` da 0 y el voto viejo cuenta como de este tick: la prueba lo muestra (1 997 ticks por plazo en vez de 1 998). Como 2^24 es múltiplo de 512, ese tick además es frontera, y los pesos se ajustarían con el puntaje 0 del gestor colgado. Solo pasa después de 28 minutos seguidos a 0,1 ms con un gestor colgado: no afecta la competencia. No se propone arreglo.

**Observación 2: no reiniciar la placa entre rondas cuesta patrimonio si la maestra reinicia la caja.** `tx_hold` y el estado del programa (medias, posición, pesos) siguen de una ronda a la otra. Ya está anotado en `docs/fondo.md:381`, la referencia lo modela igual y la matriz de estrés lo prueba; vale también para R0. Lo nuevo es cuánto cuesta. `make p10-rondas-sin-reset` (`tools/p10/rondas_sin_reset.py`, 12 s, referencias exactas) compara la ronda B fresca con la ronda B corrida después de la A sin reinicio, con la caja reiniciada, en 40 pares de series de 2000 ticks (`docs/mediciones/p10/rondas_sin_reset.txt`):

| Ronda A, luego ronda B | R1 y R2: diferencia media | peor par | R0: diferencia media | peor par |
|---|---|---|---|---|
| modelo, luego modelo | -63 | -4 582 | -88 | -4 582 |
| modelo, luego nivel_bajo (otro nivel) | -1 922 | -57 552 | -1 998 | -57 552 |
| nivel_bajo, luego modelo | +25 | -1 536 | -52 | -1 536 |
| modelo, luego saltos | +196 | -2 020 | +141 | -2 020 |

Con series del mismo generador la pérdida media es chica (menos de 1 %), pero la cola es larga, y si la ronda nueva tiene otro nivel de precios la media vieja hace comprar 63 por tick durante unos 100 ticks. Recomendación: preguntar al ayudante si la caja se reinicia entre rondas y si las series son independientes; si las dos respuestas son sí, reiniciar la placa entre rondas (volver a grabar o desenchufar el USB) en vez de lo que dice hoy `docs/checklist_1dic.md:63`. Si la caja no se reinicia, conviene lo contrario: la placa reiniciada partiría vendiendo lo que tiene.

**Observación 3: entradas del SPI sin pull-up.** `goboard.pcf:39-42` no pone `-pullup yes` en `CS_n`, SCLK ni MOSI. Con el PMOD desconectado las entradas flotan y pueden fabricar precios o dejar el contador del hallazgo 1 en 7. El orden del checklist (conectar y después grabar) lo evita. Un pull-up en `CS_n` lo resolvería, pero cambia los tres bitstreams; no se propone para la competencia.

**Observación 4: el esclavo supone una maestra de modo 0.** El esclavo del curso carga DECISION al bajar `CS_n` y la corre en cada bajada de SCLK (`rtl/pochoco_spi_slave.v:81-91`), que es el modo 0 del testbench oficial. `make p10-modo-spi` (`tools/p10/modo_spi.sh`, `tb/p10/tb_p10_modo.sv`, 2 min) corre R1 con una maestra de modo 0 (397 de 397 bytes iguales a los de DECISION) y de modo 3, con SCLK en reposo alto (397 de 397 distintos): la maestra lee el byte corrido un bit, `0xBF` (vender 63) como `0x7E` (comprar 62) y `0x7F` como `0xFE` (11, mantener). Con una maestra de modo 3 el fondo nunca vendería. No es un defecto (el enunciado define la maestra del testbench), pero vale para los tres peldaños y hoy nada lo detectaría el 26/11 salvo un patrimonio absurdo. Por eso la rama `p10-arreglo-2` enciende LED4 también si SCLK está en alto cuando baja `CS_n`.

### Verificado sin hallazgo

| Sospecha | Cómo se revisó | Resultado |
|----------|----------------|-----------|
| Precio que llega con el supervisor a mitad del cálculo; carrera al limpiar la bandera de precio nuevo | Lectura de `pochoco_spi_slave.v:99-108` y `sw/fondo.s:188-266` | Si `byte_done` y la lectura de PRICE caen en el mismo ciclo, la bandera queda arriba y el core recibe el precio anterior, que es el suyo: no se pierde ni se duplica nada. Todos los caminos del supervisor terminan en una sola escritura de DECISION. La puerta lo mide en cada corrida (`dec_distinto_de_1`) |
| Tabla de solo lectura, también con desplazamientos que coinciden con DECISION, LED y 7 segmentos | `make p10-ro-custom0` (R1 y R2) | 31 de 31 palabras esperadas; sw, sh y sb a `0x8002_xxxx`, `0x8003_xxxx` y `0x8007_0008` no cambian la tabla ni escriben DECISION, LED o 7 segmentos. Controles negativos: sin la tabla (11 comprobaciones fallan) y con `mulstep` (4) |
| Palabras de custom-0 que no son `emad` ni `devk` | La misma prueba: 182 palabras (8 `funct3` por 10 `funct7`, más custom-1, 2 y 3) | No escriben rd (tres centinelas, incluido x2), no tocan la memoria y no saltan |
| `emad` y `devk` en los bordes | La misma prueba, contra la fórmula de `docs/extension_isa.md` calculada en Python | 17 casos iguales: signo, redondeo hacia menos infinito (-31, -32, -33), desborde, rd igual a rs1 y rs2, rd = x0 |
| Voto viejo, ventana cada 512 ticks y topes de los pesos | Lectura contra `ref/fondo.py:186-232`; topes alcanzados en `fondo-degradacion` (pesos 6/1/9) | Mismo orden de comparaciones; la frontera solo corre con los tres votos al día y ningún gestor escribe hasta que cambie PUB |
| Rondas de 200 000 ticks por el RTL (la puerta llega a 20 000; las de 200 000 solo las corrió el gemelo) | `make p10-largo` (R2, 0,1 ms, familias `modelo` y `volatil`) | Todo idéntico a la referencia: bytes, estado en cada decisión, telemetría, una escritura por precio; 196 y 314 cambios de pesos; vigilante nunca sobre 1; peor caso 443 ciclos |
| SCLK lento con el fondo degradado | `make p10-sclk-degradado` (exploración, RTL de R1) | Con un gestor colgado o atrasado decide igual que la referencia desde 110 kHz; a 105 kHz el colgado da 40 bytes distintos. La regla de 115 kHz del árbol también cubre la degradación. El presupuesto del testbench, (período menos transacción) / 40, es más estricto que el plazo real (de `byte_done` a la bajada siguiente de `CS_n`) |
| `PLAZO = 0` en la tabla colgaría al supervisor si un gestor muere | Lectura | `ref/fondo.py:252` rechaza esa tabla |
| MISO con X o Z | Lectura de `pochoco_spi_slave.v:95`; afirmación 2 de `formal/p10/spi_byte.v` | MISO sale de un flip-flop con reset y vale 0 con `CS_n` en alto |
| PC de 11 bits | Criterio 5 repetido, que compara también con PC de 32 bits (grupo W) | Sin diferencias |
| Vigilante con escritura y precio en el mismo ciclo, o disparo en una corrida sana | Lectura de `rtl/vigilante.v:67-83`; `make p10-largo` y la puerta repetida | La cuenta queda en 1; BOOT espera `CS_n` en alto; ninguna corrida sana pasó de 1 |

## 2. Lo que no se verificó

- Nada en la placa: ni el hallazgo 1 ni la observación 4 con una maestra real, ni el tiempo del relevo.
- El arreglo 1 no pasó la puerta completa de R1 y R2 (sección 3.2).
- Qué hace la maestra real entre rondas (observación 2): es una pregunta al ayudante.

## 3. Puerta de simulación repetida desde cero

### 3.1 R1 y R2, sin cambios en el diseño

Se repitió entera, el 17/11, con el RTL, el programa y la tabla de `main` (`sw/fondo.s` sha256 `19773517830a2e16...`, `sw/fondo_tabla.hex` sha256 `f792588c9cc823cb...`), con 4 procesos por corrida. La máquina se cayó dos veces durante la primera noche y se perdieron las corridas en curso; las de esta tabla se hicieron después, una a la vez por la cola de la máquina. Comandos: `make fondo-puerta HW=r1` (53 min), `make fondo-puerta HW=r2` (60 min), `make fondo-criterio5 HW=r1` (13 min) y `HW=r2` (25 min), y `make fondo-bitstreams` (10 min).

**Cada archivo que escriben esos objetivos en `docs/mediciones/fondo/r1/` y `r2/` quedó idéntico al versionado, salvo la línea "Commit de partida" y, en el criterio 5, el tiempo de simulación.** Los dos `timing.txt` no tienen esa línea y quedaron byte por byte iguales. En `docs/mediciones/fondo/bitstreams.txt` cambian además los tiempos de `icebram` (0,09 s en vez de 0,26 s). Por eso cada resultado de abajo coincide con el registrado en `docs/puertas.md`. Además, **los bitstreams reconstruidos son byte por byte los guardados**: `r1.bin`, `r2.bin` y `r2_multi.bin` de `build/fondo/bitstreams/` tienen el sha256 de `bitstreams/r1_fondo.bin` (`b61c8dc0...`), `r2_fondo_vigilante.bin` (`a9c107a1...`) y `r2_multi.bin` (`29365357...`).

| N.º | Criterio | R1 ahora | R2 ahora | Registrado en `docs/puertas.md` |
|-----|----------|----------|----------|------|
| 1 | Testbench oficial sin modificar | 4/4, peor caso 443 de 2262, `decisiones.csv` idéntico a `ref/fondo.py` | Igual | Igual en los dos |
| 2 | Equivalencia con la referencia | 21 de 21 casos: práctica a 0,1, 1 y 10 ms por la copia del oficial (4/4 en las tres) y por `tb_fondo`, más una serie de 20 000 ticks de cada una de las 15 familias; 1 050 de 1 050 series sintéticas (2,1 millones de ticks) | Igual | Igual en los dos |
| 3 | Timing en 10 semillas | 10 de 10; 1029 celdas, 13 BRAM, mínima 51,59 MHz, mediana 52,57 | 10 de 10; 1045 celdas, 13 BRAM, mínima 47,86 MHz, mediana 50,33 | Igual en los dos |
| 4 | Peor caso barriendo la fase | 444 sano y 568 con el plazo agotado, contra 1131 | Igual | Igual en los dos |
| 5 | Core en la configuración exacta | 7 974 963 instrucciones en 20 600 programas, 92,80 % distintas, cero diferencias; 6 de 6 mutaciones de la extensión, 21 de 21 del barrel, prueba formal de las 3 de `mulstep` | Igual | Igual en los dos |
| 6 | Degradación | 30 de 30, peor caso 679; 15 de 15 controles negativos | Igual | Igual en los dos |
| 7 | Estrés | 56 de 56 | 56 de 56, sin disparo del vigilante | Igual en los dos |
| 8 | Bitstream simulado desde el `.asc` | 2000 ticks idénticos en las dos series (práctica y reversión); otra tabla puesta con `icebram` también idéntica | 2000 ticks idénticos en las dos series, sin disparo; con el supervisor colgado, BOOT con S1 S0 = 01 al terminar la transacción 105 (quinta sin respuesta); imagen múltiple correcta | 2000 ticks idénticos en dos series; en R2 sin disparo, y disparo correcto con el supervisor colgado |

Un detalle que no cambia nada: en la matriz de R2 la cuenta del vigilante llega a 2 en dos casos de exploración (períodos de 11,5 y 13,5 us, fuera de la puerta). En todos los casos de la puerta queda en 1 o menos, como dice `docs/puertas.md`.

### 3.2 Arreglo 1 (rama `p10-arreglo-1`)

No se repitió la puerta completa con el arreglo: cambia el hardware de R1 y R2, y la puerta completa de los dos cuesta unas 4 horas de máquina. Se corrió lo que muestra que el arreglo hace lo que dice y no rompe el comando oficial:

| Prueba | Resultado |
|--------|-----------|
| `make p10-spi-7flancos` | 6 de 6 casos: cero precios fantasma y ningún disparo del vigilante |
| `make p10-formal-spi` (`CSLIMPIA=1`) | Prueba por inducción y cover alcanzable. Con `CsLimpia = 0` la misma prueba falla, como en `main` |
| `make tb` (R0, comando oficial sin definiciones) | 4/4, peor caso 44 ciclos |
| `tools/fondo/oficial.sh` con R1 y con R2 | ARREGLO_OFICIAL |

Falta, si se adopta: `make fondo-puerta` y `make fondo-criterio5` con `HW=r1` y `HW=r2`, `make fondo-bitstreams` con `GUARDAR=1`, las autopruebas de R1 y R2, los moldes y el kit de contingencia de R1 y R2, y la puerta de placa. R0 no cambia.

### 3.3 Arreglo 2 (rama `p10-arreglo-2`)

ARREGLO2

## 4. Pruebas agregadas

Todas tienen su objetivo en el `Makefile` (sección "Revisión adversarial P10") y ninguna es parte de `check` ni de la integración continua. Las que reproducen el hallazgo 1 terminan con error a propósito en esta rama.

| Objetivo | Archivos | Qué prueba | Resultado en `p10-revision` |
|----------|----------|------------|------------------------------|
| `make p10-ro-custom0` | `tools/p10/gen_ro_custom0.py`, `tools/p10/ro_custom0.sh`, `tb/p10/tb_p10_soc.sv` | Tabla de solo lectura, 182 palabras de custom-0 a 3 sin efecto y 17 bordes de `emad` y `devk`, en el SoC de R1 y R2, con dos controles negativos | PASS |
| `make p10-spi-7flancos` | `tools/p10/spi_7flancos.sh`, `tb/p10/tb_p10_spi.sv` | Hallazgo 1 por simulación, 3 escenarios en R1 y R2 | FAIL a propósito (4 de 6 casos); PASS en `p10-arreglo-1` |
| `make p10-formal-spi` | `tools/p10/formal_spi.sh`, `formal/p10/spi_byte.v` | Hallazgo 1 por prueba formal | FAIL a propósito (contraejemplo de 18 pasos); PASS en `p10-arreglo-1` |
| `make p10-vuelta-tick` | `tools/p10/vuelta_tick.sh` | Observación 1: vuelta del número de tick, sano y con un gestor colgado | PASS (y la diferencia esperada con el gestor colgado) |
| `make p10-largo` | `tools/p10/largo.sh` | Dos rondas de 200 000 ticks por el RTL de R2 | PASS |
| `make p10-sclk-degradado` | `tools/p10/sclk_degradado.sh` | Exploración: SCLK de 105 a 130 kHz a 0,1 ms con un gestor colgado o atrasado | Tabla en la sección 1 |
| `make p10-rondas-sin-reset` | `tools/p10/rondas_sin_reset.py` | Observación 2 | `docs/mediciones/p10/rondas_sin_reset.txt` |
| `make p10-modo-spi` | `tools/p10/modo_spi.sh`, `tb/p10/tb_p10_modo.sv` | Observación 4: maestra de modo 0 y de modo 3 | Modo 0 sin diferencias; modo 3 con 397 de 397 bytes distintos |
| `make p10` | | Todas las anteriores | |
