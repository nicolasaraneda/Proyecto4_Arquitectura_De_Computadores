# Puertas de la escalera de bitstreams

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Un bitstream sube a la escalera solo si pasa tres puertas, en orden: simulación, placa y maestra real (miércoles 25/11, por confirmar). Este documento dice cómo se comprueba cada criterio de la puerta de simulación y deja el estado de cada peldaño. La escalera y la razón de cada peldaño están en la decisión T50.

| Peldaño | Hardware | Programa | Archivo |
|---------|----------|----------|---------|
| R0 | Espino base, sin hardware agregado | `sw/trade.s` con `max_media` | `bitstreams/r0_base_max_media.bin` |
| R1 | Espino barrel con `emad` y `devk` y la tabla, sin vigilante | `sw/fondo.s` | `bitstreams/r1_fondo.bin` |
| R2 | R1 con vigilante y dos imágenes | `sw/fondo.s`, y R0 como imagen de respaldo | `bitstreams/r2_multi.bin` |
| R3 (desde el 21/11, T150 a T152) | R2 con la tabla de 512 palabras | `sw/c1.s` (C1 en los cuatro hilos), y R0 con banda 40 como imagen de respaldo | `bitstreams/r3_c1_multi.bin` |

## Puerta de simulación

| N.º | Criterio | Cómo se comprueba |
|-----|----------|-------------------|
| 1 | Testbench oficial sin modificar: 4/4 | `make tb` |
| 2 | Decisiones idénticas a la referencia en los 20 000 ticks de práctica a los tres períodos, y en al menos 1 000 series sintéticas | `make equiv` (gemelo a los tres períodos, Verilator a 0,1 y 1 ms, 13 familias), `make equiv-r3` (Icarus a 0,1 ms), `make equiv-largo` (Verilator a 10 ms) y `make equiv-gemelo` (3810 series del protocolo a los tres períodos) |
| 3 | Timing a 25 MHz en 10 de 10 semillas, informando la mínima | `EXIGIR=1 tools/medir_variante.sh base 10` |
| 4 | Peor caso de respuesta barriendo las 8 fases del sondeo y las 4 alineaciones de hilo, menor que la mitad del presupuesto de la ronda 3 (1131 ciclos) | `make fases` (`tools/estres.py --solo fases`). En el core base no hay alineaciones de hilo |
| 5 | Verificación del core que compite contra el core base, con el generador corregido: al menos 5 millones de instrucciones con más de 90 % distintas, y todas las mutaciones detectadas | Para el barrel, `make barrel-verif` y `make barrel-mutaciones` (decisión T57). Para R0 ver la nota |
| 6 | Degradación: un hilo gestor en lazo infinito, un voto que nunca llega, un voto atrasado | Para el fondo, P3. No aplica a R0 |
| 7 | Estrés: SCLK entre 100 kHz y 1 MHz, tiempos de `CS_n` distintos, reset con la maestra transmitiendo, rondas seguidas sin reset, serie pegada en 1 y en 255 | `make estres` (`tools/estres.py`, `tb/tb_estres.sv`) |
| 8 | Simulación del bitstream ya ruteado, 2 000 ticks idénticos a la referencia | `make sim-bitstream` |

`tb/tb_estres.sv` es una maestra con la misma transacción y la misma medición que el testbench oficial, pero con los tiempos elegidos en tiempo de ejecución (decisión T53). `tools/estres.py` compara cada byte que lee la maestra con `ref/trader.py`, exige MISO sin X y ningún precio sin leer ni sin respuesta, y modela como perdidos los precios que llegan antes de que termine el reset de encendido. Los casos con SCLK sobre 1 MHz son exploración y no cuentan para la puerta.

## R3: C1 en los cuatro hilos, con la tabla de 512 palabras (T150 a T152, 21/11)

Rama `c1`, creada desde `banda-40`. R3 es el hardware de R2 (barrel con `emad` y `devk`, vigilante) con la tabla de 512 palabras (`rtl/pochoco_tabla512.v`, `-DESPINO_TABLA_512`) y el programa `sw/c1.s`: la banda 40 de R2 más el desempate C1 de la exploración (`docs/c1_plan.md`). Referencia: `ref/c1/c1.py`. R0, R1 y R2 no cambian. Todo se corre con `make c1-puerta` (`tools/c1/puerta.sh`); el resumen está en `docs/mediciones/c1/puerta.txt` y los registros en `docs/mediciones/c1/`. Bitácora: `docs/bitacora/c1.md`.

El encargo pedía cuatro puertas. Las cuatro pasan con el programa del commit `5cd9b68` (`sw/c1.s` sha256 `353f6806...`, `sw/c1_tabla.hex` `9954f116...`).

| Puerta | Qué se exige | Resultado |
|--------|--------------|-----------|
| a | Con la política apagada (una palabra de la tabla en 0), las órdenes de la banda 40 de R2 | **Pasa.** El archivo de bytes de R3 apagado es idéntico al de R2 (`sw/fondo.s` en su hardware y con su testbench) en 46 corridas por el RTL: Tesla, AMD y Meta completas a 0,1 y 1 ms y 40 ventanas reales (920 000 ticks). En el gemelo, 203 series a los tres períodos (12,18 millones de ticks): iguales a `ref/c1/c1.py`, a `ref/fondo.py` y al programa de R2. Responde en 203 ciclos |
| b | Assembly contra la referencia entera, orden por orden, en Tesla, AMD, Meta y al menos 200 ventanas más, a los tres ritmos | **Pasa.** Por el RTL, bytes y estado tick a tick: Tesla, AMD y Meta a 0,1 y 1 ms, Meta a 10 ms, y 200 ventanas reales de 20 000 ticks a 0,1 ms (4,14 millones de ticks, 1210 órdenes, 129 ventanas terminan en candado). En el gemelo con la tabla de 512 palabras, las 203 series a 0,1, 1 y 10 ms (12,18 millones de ticks). Cero diferencias. Tesla 21 224, AMD 27 199, Meta 22 682 |
| c | La misma puerta de simulación de R0, R1 y R2, y la integración local | **Pasa** (tabla siguiente) |
| d | Síntesis: celdas, bloques de memoria y temporización | **Pasa.** 1038 celdas de 1280, 14 bloques de 16, 10 de 10 semillas a 25 MHz, mínima 48,41 MHz, mediana 51,35 y máxima 53,07 |

Puerta c, criterio por criterio:

| N.º | Criterio | Resultado | Registro |
|-----|----------|-----------|----------|
| 1 | Testbench oficial sin modificar | 4/4, peor caso 759 ciclos de 2262, `decisiones.csv` idéntico al de `ref/c1/c1.py` | `oficial.txt` |
| 2 | Equivalencia | Cero diferencias. Copia del oficial con la serie Meta y con la anterior a 0,1, 1 y 10 ms (4/4 en las seis; 22 682 en la serie Meta). La puerta b. 30 series de 20 000 ticks (15 familias, crudas y normalizadas) y 1 050 de 2000 por el RTL (2,1 millones de ticks); las mismas 1 081 en el gemelo a los tres períodos | `oficial.txt`, `puerta_b.txt`, `series.txt` |
| 3 | Timing | 10 de 10 semillas, mínima 48,41 MHz. El bitstream guardado (semilla 1): 50,00 MHz, 50,20 con `icetime` | `timing.txt`, `bitstreams.txt` |
| 4 | Peor caso barriendo la fase | Programa sano: 779 ciclos (48 fases de un ciclo en dos series, 24 corridas 13 ns y el período de 2501 ciclos). Con el hilo 3 colgado, 24 fases: 916. Contra 1131 | `fases.txt` |
| 5 | Core en la configuración exacta | El core es el de R1 y R2. La campaña se repitió sobre el SoC de R3: 7 974 963 instrucciones, 92,80 % distintas, cero diferencias; 6 de 6 mutaciones de la extensión y 21 de 21 del barrel detectadas | `criterio5_*.txt` |
| 6 | Degradación | 26 de 26 casos, peor caso 907 ciclos: cada hilo (1, 2 y 3) colgado en cinco situaciones, dato viejo (un tick, dos seguidos y un atraso que se salta precios) y modo seguro (precio bajo 100, ronda larga, política apagada). Donde queda el modo seguro, los bytes son los de la banda 40 de `ref/fondo.py`. 25 de 25 controles negativos detectados y el control en blanco pasa | `degradacion.txt`, `controles.txt` |
| 7 | Estrés | 57 de 57, peor caso 779 ciclos, el vigilante no dispara en ninguno | `estres.txt` |
| 8 | Bitstream simulado desde el `.asc` | El molde con `icebram` da el mismo `.asc` que la síntesis directa. 2000 ticks por los pines idénticos a la referencia en tres series (los primeros 2000 de la serie Meta, la serie hecha a mano que apuesta en la fase A y llega al candado, y una ventana con motor), sin disparo. Con la política apagada por `icebram`: 2000 ticks iguales a la banda 40. Con el hilo 0 colgado en el tick 100, BOOT pide la imagen 01 al terminar la transacción 105. Con el hilo 3 colgado en el tick 700, sin relevo y con los bytes de la referencia | `bitstreams.txt` |
| | Integración local | 27 de 27: los 24 pasos de la rama (R0, R1 y R2 siguen pasando sus pruebas con el gemelo y el RTL de esta rama), `make check-c1`, los hash de `bitstreams/` y nada cambiado en `bitstreams/`, `sw/` ni `rtl/`. `make check-c1` pasó en la segunda corrida, después de un arreglo de `tools/c1/generar.py` para copias limpias | `docs/mediciones/ci_local_c1.txt` |

Además: el gemelo con la tabla de 512 palabras da la misma traza que el RTL de R3 en 17 configuraciones (42,4 millones de eventos, `cosim.txt`); el testbench del módulo nuevo pasa y sus tres controles se detectan (`tb_tabla.txt`); y la telemetría (el byte de los 7 segmentos con cada una de las 16 combinaciones de botones) coincide con la referencia en cada tick (`ticks.txt`).

Lo que no se repitió y por qué vale: la prueba formal del vigilante y el relevo de punta a punta con las dos imágenes en un testbench (`make check-vigilante`) son del módulo `rtl/vigilante.v` y de la imagen de respaldo, que no cambian; en R3 se comprobó el disparo dentro de su propio bitstream (criterio 8). La prueba formal de las tres mutaciones de `mulstep` que no aplican es del core.

Dos cosas que conviene saber antes de la maestra (detalle en `docs/c1_plan.md`, sección 6, y `docs/c1_dia_de_prueba.md`):

- C1 supone una ronda de 20 000 ticks contada desde el encendido. Pasado ese tick sin reset, R3 decide la banda 40 (modo seguro, LED1). Con rondas seguidas sin reset solo la primera corre C1.
- R3 responde en hasta 807 ciclos sano y 916 con un hilo colgado: el período mínimo que soporta con holgura es de unos 50 µs (R2: 13,5 µs).

Recursos de R3:

| Recurso | Uso | Presupuesto |
|---------|-----|-------------|
| Celdas | 1038 (R2: 1015) | 1280 |
| Bloques de memoria | 14 (R2: 13) | 16 |
| Frecuencia máxima | 48,41 MHz la mínima de 10 semillas | 25 MHz |
| Memoria del programa | 482 palabras (444 de código y 38 de datos) | 512 |
| Tabla | 348 palabras usadas | 512 |
| Respuesta, programa sano | 807 ciclos en el peor tick | 1131 (la mitad de 2262) |
| Respuesta con el plazo vencido | 916 ciclos | 1131 |
| Instrucciones por hilo y por tick | 228 en el hilo 3, el mayor | 565 |
| Flash, imagen múltiple | 64 600 bytes | 131 072 |

Bitstreams (`make c1-bitstreams`, copiados a `bitstreams/` con `GUARDAR=1`):

| Archivo | sha256 |
|---------|--------|
| `r3_c1.bin` | `cd0f7f6544990ff5a32af2d64dc01b360b4bd2c569a27b41457b28d4174293a7` |
| `r3_c1_multi.bin` (imagen 0 R3, imagen 1 R0 banda 40) | `c0b8a4cc3ed7d24d7096b0102e5033f6d93f4de2eeea11afe09ff755f1dc94c0` |
| `r3_c1_apagada_multi.bin` (R3 con la política apagada, imagen 1 R0) | `a3c14f00a48da9ced7f6dd7fd7a4073ed871b52eeb92fc1c517639c8b2c97a24` |
| `r3_c1_falla_multi.bin` (R3 con el hilo 0 colgado en el tick 100, imagen 1 R0) | `ab755baa483c514663ea51beaf3d6445446e35e9998d82a91504e387d972b51f` |
| `moldes/r3_molde.asc.gz` | `709a0516e6c8598d486c62e43fcf1cf2813011cb8fcddabe5c8f9dbc21aa3dec` |
| `moldes/molde_tabla512.hex` | `b78ca6b58510199084ae274a17331a59685d54fade64cf3cc6bd88bea96685a5` |

R3 pasó la puerta de simulación. Le faltan la de placa y la de la maestra real el miércoles 25/11, por confirmar (`docs/c1_dia_de_prueba.md`). El 18/11 R2 ya había corrido con la maestra real (sección "Puerta de maestra: la clase del 18/11"), pero eso no valida los tiempos SPI de R3, porque R2 responde en 128 ciclos y R3 en hasta 916. Para la de placa tiene su autoprueba, `bitstreams/autoprueba_r3_multi.bin` (firma `984c`, 1208 celdas; `docs/autoprueba.md`, sección 12).

## R0 con banda 40 (T140, 19/11)

Rama `banda-40`. Cambian dos constantes de `sw/trade.s` (`BANDA_COMPRA` 141 y `BANDA_VENTA` 215): compra con 140 o menos y vende con 215 o más después de ver los dos extremos. El hardware no cambia y el programa entra por `icebram` en el molde de R0. La puerta la corre `tools/puerta_r0_cotas.sh` (registro en `docs/mediciones/r0_banda40_puerta.txt`, unos 50 minutos); los bitstreams salen de `make fondo-molde-banda40` (`docs/mediciones/fondo/molde_banda40.txt`).

| N.º | Resultado |
|-----|-----------|
| 1 | 4/4. Peor caso 60 ciclos de 2262 (las mismas 24 instrucciones fijas) |
| 2 | Cero diferencias. `make equiv` (20 de 20); práctica completa a 0,1 ms con Icarus y a 10 ms con Verilator; serie Meta completa por el RTL a 0,1 ms (Icarus), 1 ms y 10 ms (Verilator), patrimonio 21 392; 3810 series en el gemelo a los tres períodos (7,62 millones de ticks por período); exhaustiva: 1275 combinaciones de estado y precio a cada período; las series reales de la clase del 18/11 por el RTL a 0,1 y 1 ms y por el gemelo a los tres períodos (Tesla 20 795, AMD 26 470; `docs/mediciones/reales/r0.txt`) |
| 3 | Hardware sin cambios: vale la medición de 10 semillas de más abajo. `icetime` del `.asc` nuevo: 43,27 MHz, igual que el anterior |
| 4 | Peor caso 60 ciclos en las 8 fases, con y sin el corrimiento de 13 ns |
| 5 | Core base sin cambios |
| 7 | 72 casos pasan. El único FAIL es la exploración del período de 11,5 µs (50 ciclos disponibles, la regla usa 60), igual que con la banda 60; 13,5 µs pasa |
| 8 | El `.asc` del molde, simulado por los pines: 2000 ticks idénticos a la referencia en los primeros 2000 de la serie Meta y en una ventana normalizada que toca los dos extremos (14 697) |

Qué se reutilizó y por qué sigue valiendo: el timing en 10 semillas y el criterio 5 dependen solo del hardware, que no cambió; que el bitstream nuevo tiene el mismo hardware lo comprueban el control del molde (con el programa de `c794834` da `r0_base_max_media.bin` byte por byte) y el `icetime` del `.asc` nuevo.

## R0 con la regla de cotas (T133, 17/11)

Rama `regla-cotas`. El hardware no cambia; el programa entra por `icebram` en el molde de R0 (`build/r0_cotas/r0_cotas.bin`, sha256 `616f799a...`). Registro completo en `docs/mediciones/r0_cotas_puerta.txt`.

| N.º | Resultado |
|-----|-----------|
| 1 | 4/4. Peor caso 60 ciclos de 2262 (24 instrucciones fijas después de leer el precio) |
| 2 | Cero diferencias. `make equiv` (20 de 20); serie Meta completa por el RTL a 0,1 ms (Icarus), 1 ms y 10 ms (Verilator), patrimonio 19 214; 3810 series en el gemelo a los tres períodos; exhaustiva: los 5 estados alcanzables por los 255 precios (`docs/mediciones/exhaustivo_r0_cotas.txt`) |
| 3 | Hardware sin cambios: vale la medición de abajo |
| 4 | Peor caso 60 ciclos en las 8 fases |
| 5 | Core base sin cambios |
| 7 | La matriz pasa. El período mínimo sube: a 11,5 µs (exploración) hay 50 ciclos y la regla usa 60 |
| 8 | El `.asc` del molde con el programa nuevo, simulado por los pines: 2000 ticks idénticos a la referencia en la serie anterior y en una ventana de la serie Meta que toca los dos extremos (25 258) |

## R0: core base con `max_media` (hasta el 17/11)

Medido el 15/11 (paquete P0). Los registros completos están en `docs/mediciones/` y en `docs/bitacora/p0.md`.

| N.º | Resultado |
|-----|-----------|
| 1 | 4/4. Peor caso 44 ciclos de 2262 |
| 2 | Cero diferencias. 20 000 ticks a 0,1 ms (gemelo, Verilator e Icarus), 1 ms (gemelo y Verilator) y 10 ms (gemelo y Verilator); 13 familias sintéticas por el RTL; 3810 series en el gemelo a los tres períodos, 7,62 millones de ticks por período. Patrimonio en el testbench con los 20 000 ticks: 26 070 |
| 3 | 10 de 10 semillas. 1083 celdas de 1280 y 12 BRAM de 16. Frecuencia máxima mínima 42,43 MHz, mediana 43,74 y máxima 45,08 |
| 4 | Peor caso 49 ciclos en las 8 fases (y en las 8 fases desplazadas 13 ns, y con un período de 2501 ciclos que las recorre todas), contra el límite de 1131 |
| 5 | El core de R0 es el base. `make formal-base` prueba que sus etapas IF e ID son las del repositorio del curso, y `make cosim` valida el gemelo contra el RTL con programas del generador corregido |
| 6 | No aplica: un solo hilo |
| 7 | 60 casos en el rango pedido, todos pasan (`docs/mediciones/estres_base.txt`). SCLK funciona hasta 4 MHz; a 5 MHz no (exploración, decisión T53). Repetido el 15/11 en P4 después de corregir `tb_estres.sv`, cuyas rondas seguidas no cambiaban de período (T81): siguen pasando los 60 |
| 8 | 2 000 ticks a 0,1 ms del `.asc` ruteado idénticos a la referencia |

R0 pasó la puerta de simulación. De la de placa (la corre Nicolás con la autoprueba de P6, `docs/autoprueba.md`, sección 5) le falta la mitad alta de la firma (sección "Puerta de placa"), y le falta la de la maestra real el miércoles 25/11, por confirmar.


## Espino barrel con un programa de un hilo

Medido el 15/11 (paquete P1). No es un peldaño de la escalera: es el core de R1 y R2, todavía sin la extensión, sin la tabla y sin `sw/fondo.s`, corriendo `sw/trade.s` en el hilo 0 con la tabla de arranque. El paquete pedía los criterios 1, 3 y 5. Detalle en `docs/espino_barrel.md` y salidas en `docs/mediciones/barrel/`.

| N.º | Resultado | Comando |
|-----|-----------|---------|
| 1 | 4/4 con `tb/tb_proyecto_4.sv` sin modificar. Peor caso 83 ciclos de 2262. `decisiones.csv` idéntico byte a byte al del Espino base | `make barrel-oficial` |
| 3 | 10 de 10 semillas. 933 celdas de 1280 y 12 BRAM de 16. Frecuencia máxima mínima 52,62 MHz, mediana 55,65 y máxima 59,18 | `make barrel-timing` |
| 5 | 7 948 558 instrucciones en 20 600 programas, 7 309 470 distintas en toda la campaña (91,96 %), cero diferencias con el Espino base. Aparte, 8 966 903 instrucciones en la campaña de lazos. 21 de 21 mutaciones detectadas, cada una por las 7 comparaciones. 24 afirmaciones formales de estructura probadas | `make barrel-verif`, `make barrel-mutaciones` y `make barrel-formal` |

Medido además, sin que el paquete lo pidiera: los 20 000 ticks idénticos a la referencia a 0,1 ms y a 1 ms con Verilator (parte del criterio 2), peor caso de 88 ciclos barriendo la fase del sondeo con el método del prototipo (criterio 4, falta repetirlo con `make fases`) y 500 ticks del bitstream ruteado idénticos a la referencia (criterio 8, que pide 2 000).

Los criterios 2, 4, 6, 7 y 8 se cierran con el programa que compite, en P3 a P5.

## Espino barrel con la extensión de la ISA

Medido el 15/11 (paquete P2). Tampoco es un peldaño: es el core de R1 y R2 con `emad`, `devk` y `mulstep` (`-DESPINO_BARREL -DESPINO_XD`), todavía sin la tabla y sin `sw/fondo.s`. El paquete pedía el timing y la equivalencia formal de cada instrucción contra su especificación. Detalle en `docs/extension_isa.md` y salidas en `docs/mediciones/xd/`.

| N.º | Resultado | Comando |
|-----|-----------|---------|
| 1 | 4/4 con `tb/tb_proyecto_4.sv` sin modificar, con `sw/trade.s` (83 ciclos) y con `sw/xd/trade_xd.s`, que usa `devk` y `emad` (63 ciclos). `decisiones.csv` idéntico al del Espino base | `make xd-oficial` |
| 3 | 10 de 10 semillas en los 7 subconjuntos. Las tres instrucciones: 1034 celdas de 1280 y 12 BRAM de 16. Frecuencia máxima mínima 48,33 MHz, mediana 49,33 y máxima 51,94 | `make xd-timing` |
| 5 | 7 966 640 instrucciones en 20 600 programas, 93,15 % distintas en toda la campaña, cero diferencias con el Espino base más la especificación. 1 030 081 son de la extensión. 9 de 9 mutaciones detectadas | `make xd-verif` y `make xd-mutaciones` |
| Formal | Cada instrucción contra su especificación en los 7 subconjuntos, y el core con la extensión equivalente al de P1 para programas sin custom-0. 9 de 9 mutaciones con contraejemplo | `make xd-formal` |

Para el criterio 5, la referencia de las instrucciones nuevas es la fórmula de la especificación escrita en el testbench (decisión T60).

## R1 y R2 con banda 40 (T140, 19/11)

Rama `banda-40`. El hardware y el binario de `sw/fondo.s` no cambian (solo sus comentarios; `cmp` del `.hex` contra el anterior). Cambian dos palabras de la tabla: `BANDA_COMPRA` 0x8d (141) y `BANDA_VENTA` 0xd7 (215). La puerta la corre `HW=r1|r2 tools/fondo/puerta_cotas.sh` (registros en `docs/mediciones/fondo/r1/puerta_banda40.txt` y `r2/puerta_banda40.txt`).

| N.º | Criterio | R1 | R2 |
|-----|----------|----|----|
| 1 | Testbench oficial sin modificar | 4/4, peor caso 127 ciclos de 2262, `decisiones.csv` idéntico al de `ref/fondo.py` | Igual |
| 2 | Equivalencia | Cero diferencias: copia del oficial con la serie anterior y con la serie Meta a 0,1, 1 y 10 ms (21 392 en la serie Meta); `tb_fondo.sv` con la serie Meta a los tres períodos y las 15 familias crudas y normalizadas; 1 050 series por el RTL (2,1 millones de ticks); el gemelo con 1 051 series a los tres períodos (6,36 millones de ticks); las series reales de la clase del 18/11 por el RTL a 0,1 y 1 ms y por el gemelo a los tres períodos (`docs/mediciones/reales/r1.txt`) | Igual (`reales/r2.txt`) |
| 3 | Timing | Hardware sin cambios. `icetime` del `.asc` nuevo: 52,61 MHz, igual que antes | 51,66 MHz, igual que antes |
| 4 | Peor caso barriendo la fase | 128 ciclos contra 1131 (holgura de 94,3 %) | Igual |
| 5 | Core | Hardware y binario sin cambios: vale la campaña de P1 a P5 | Igual |
| 6 | Degradación | 17 de 17 corridas, peor caso 127 ciclos. 15 de 15 controles negativos detectados, entre ellos la tabla con la banda 60 (161 y 195), un nivel corrido en uno de cada lado (vende desde 216, compra hasta 139) | Igual |
| 7 | Estrés | 57 de 57, peor caso 128 ciclos | 57 de 57, el vigilante no dispara en ninguno |
| 8 | Bitstream simulado desde el `.asc` | Molde con `icebram`: 2000 ticks idénticos en los primeros 2000 de la serie Meta y en una ventana normalizada (14 697) | Igual, sin disparo; con el supervisor colgado en el tick 100, BOOT pide la imagen 01 al terminar la transacción 105. `make vig-relevo`: todas las comprobaciones pasan |

El paso de las series reales falló en la primera corrida por un error del script, no del diseño (`tools/barrel/comun.sh` define `B` y pisaba la carpeta de las series); se corrigió y se repitió solo ese paso, como consta al final de cada registro. En la repetición pasó en los dos peldaños: Tesla 20 795 y AMD 26 470 por el RTL a 0,1 y 1 ms y por el gemelo a los tres períodos, iguales a `ref/fondo.py` y a R0.

Bitstreams (`make fondo-molde-banda40`, copiados a `bitstreams/`):

| Archivo | sha256 |
|---------|--------|
| `r0_banda40.bin` | `390edbfad65b2e269c059e646259f7c3e117398a5ececb1d64816fe8fdd4fd5f` |
| `r1_banda40.bin` | `a9e233b96fba7643c8faa5cabcd3f54b1b9cd5e291850bb8ee295570b0a7ba61` |
| `r2_banda40.bin` | `3fb31a04674a1fcd67d7cf97cb57fcf44eea23243de262a1994284ff96c57bd3` |
| `r2_banda40_multi.bin` (imagen 0 R2, imagen 1 R0 banda 40) | `8a773121e44a4d6f93f319afe8145620e65bcab285dec1e9b0440f8763d9d691` |
| `r2_banda40_falla_multi.bin` (R2 colgado en el tick 100, imagen 1 R0; `make r2-falla-banda40`) | `88d63a08082f51d279e7e3a9e4c3ac7030443905ea92561a27e29fd7800b345d` |

Qué se reutilizó y por qué sigue valiendo: el timing en 10 semillas, la verificación del core (criterio 5) y la equivalencia formal dependen solo del hardware, que no cambió; el control del molde (con los programas anteriores da `r1_fondo.bin`, `r2_fondo_vigilante.bin` y `r2_multi.bin` byte por byte) y el `icetime` de cada `.asc` nuevo lo comprueban. La máscara de la extensión que vigila el criterio 5 depende del binario de `sw/fondo.s`, que es el mismo.

## R1 y R2 con la regla de cotas (desde el 17/11, decisión T133)

Medido el 18/11 en la rama `regla-cotas-r1`. El hardware no cambia: el mismo barrel con `emad`, `devk` y la tabla, y en R2 el vigilante. Cambian el programa y la tabla: `sw/fondo.s` corre en el hilo 0 la regla de R0 ("espera" con banda 60, `docs/cotas.md`) con sus cuatro umbrales leídos de la tabla en cada tick, y deja los hilos 1 a 3 en un lazo de espera. Referencia: `ref/fondo.py`, que con la tabla por defecto decide igual que `ref/trader.py`. Bitácora: `docs/bitacora/regla_cotas_r1.md`.

| N.º | Criterio | R1 | R2 |
|-----|----------|----|----|
| 1 | Testbench oficial sin modificar | 4/4, peor caso 127 ciclos de 2262, `decisiones.csv` idéntico al de `ref/fondo.py` | Igual |
| 2 | Equivalencia con la referencia | Cero diferencias: copia del oficial con la serie Meta y con la anterior a 0,1, 1 y 10 ms (4/4 en las seis; 19 214 en la serie Meta); `tb_fondo.sv` con la serie Meta a los tres períodos, la anterior y una serie de cada una de las 15 familias, cruda y normalizada (680 000 ticks); 1 050 series (2,1 millones de ticks, la mitad normalizadas entre 100 y 255); el gemelo con 1 051 series a los tres períodos | Igual |
| 3 | Timing en 10 semillas | Hardware sin cambios: el bitstream sale del molde de `r1_fondo.bin` (control: el molde con el programa anterior da ese `.bin` byte por byte) e `icetime` da los mismos 52,61 MHz. Síntesis nueva con el programa cargado: 10 de 10, 1001 celdas, mínima 49,40 MHz | Molde de `r2_fondo_vigilante.bin`, `icetime` 51,66 MHz igual que antes. Síntesis nueva: 10 de 10, 1015 celdas, mínima 49,64 MHz |
| 4 | Peor caso barriendo la fase | 128 ciclos (48 fases, 24 corridas 13 ns, período de 2501 ciclos, y 24 fases con los hilos 1 a 3 haciendo cuentas), contra 1131 | Igual |
| 5 | Core en la configuración exacta | Sin cambios: es hardware (la campaña y las mutaciones no dependen del programa) | Igual |
| 6 | Degradación | 17 de 17 corridas: los hilos 1 a 3 haciendo cuentas, escribiendo y leyendo la RAM o leyendo el programa, de a uno y todos a la vez, no cambian ningún byte ni el peor caso (127 ciclos). 14 de 14 controles negativos detectados | Igual |
| 7 | Estrés | 57 de 57 casos (se suma SCLK de 100 kHz a 0,1 ms, que ahora cabe: 126 ciclos de 237) | 57 de 57, sin disparo del vigilante |
| 8 | Bitstream simulado desde el `.asc` | Molde con icebram: 2000 ticks idénticos con la serie Meta y con una ventana normalizada | Igual, sin disparo; con el hilo 0 colgado en el tick 100, BOOT sube en la quinta transacción sin respuesta |

Mediciones por tick (`docs/mediciones/fondo/r1/ticks.txt`, serie Meta a 0,1 ms): el hilo 0 ejecuta entre 40 y 50 instrucciones de trabajo por tick (CPI 4 por hilo), responde en 119 a 127 ciclos (5,6 % del presupuesto de la ronda 3) y vuelve a sondear a los 163 a 211 ciclos. El programa ocupa 67 de 512 palabras (`tamano.txt`) y no usa la RAM de datos.

Bitstreams nuevos (`make fondo-molde-cotas`, `docs/mediciones/fondo/molde_cotas.txt`; quedan en `build/fondo/molde_cotas/` y no reemplazan todavía a los de `bitstreams/`):

| Archivo | sha256 |
|---------|--------|
| `r0_cotas.bin` | `616f799a816d5bdd4ba29f0713f769e35beb980d7f5a1f8734ddd5a763ec64a1` |
| `r1_cotas.bin` | `309a443512f28e3e44d24219116e099c496e56e42a7f99ab27147d9e4e0d0854` |
| `r2_cotas.bin` | `aa7d1fb5027986a059f8a1b06aa94ab8f7df0f5359f996a3d21e0837267d94be` |
| `r2_cotas_multi.bin` (imagen 0 R2, imagen 1 R0) | `12b93bb0009c9eb24ff44bda023bb63c7696ad3aa655c3a5f5e0a4ddfe73f9ff` |

Relevo del vigilante de punta a punta con los programas nuevos (`make vig-relevo`, `docs/mediciones/vigilante/relevo.txt`): todas las comprobaciones pasan, incluidas las de los 35,50 ms medidos en la placa (355 ticks leyendo 0xFF a 0,1 ms).

Lo que no cambió y sigue valiendo de la sección siguiente: el criterio 5, el timing del hardware y la puerta de placa del hardware. La puerta de placa con los programas nuevos (firmas de las autopruebas) está por rehacer: `tools/autoprueba.py` todavía usa los parámetros del fondo anterior.

## R1 y R2: el fondo en un chip (hasta el 17/11)

Medido el 15/11 (paquete P5). R1 es el barrel con `emad`, `devk` y la tabla de parámetros en su BRAM (`-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA`). R2 agrega el vigilante y `SB_WARMBOOT` (`-DESPINO_VIGILANTE`) y se graba como imagen múltiple con R0 de respaldo. El programa de los dos es `sw/fondo.s`. Detalle en `docs/fondo.md` y `docs/tabla_vigilante.md`; salidas en `docs/mediciones/fondo/r1/`, `r2/` y `bitstreams.txt`, y en `docs/mediciones/vigilante/`.

| N.º | Criterio | R1 | R2 |
|-----|----------|----|----|
| 1 | Testbench oficial sin modificar | 4/4, peor caso 443 ciclos de 2262, `decisiones.csv` idéntico al de `ref/fondo.py` | Igual |
| 2 | Equivalencia con la referencia | Cero diferencias: práctica completa a 0,1 ms, 1 ms y 10 ms (4/4 en las tres), una serie de 20 000 ticks de cada una de las 15 familias y 1 050 series sintéticas (2,1 millones de ticks) | Igual |
| 3 | Timing en 10 semillas | 10 de 10. 1029 celdas, 13 BRAM, mínima 51,59 MHz, mediana 52,57 | 10 de 10. 1045 celdas, 13 BRAM, mínima 47,86 MHz, mediana 50,33 |
| 4 | Peor caso barriendo la fase | 444 ciclos sano y 568 con el plazo agotado, contra 1131 | Igual |
| 5 | Core en la configuración exacta | 7 974 963 instrucciones en 20 600 programas, 92,80 % distintas, cero diferencias con el Espino base más la especificación. 6 de 6 mutaciones de la extensión que aplican, 21 de 21 del barrel, y prueba formal de que las 3 de `mulstep` no cambian el core | Igual |
| 6 | Degradación | 30 de 30 corridas, peor caso 679 ciclos. 15 de 15 controles negativos | Igual |
| 7 | Estrés | 56 de 56 casos | 56 de 56, sin disparo del vigilante |
| 8 | Bitstream simulado desde el `.asc` | 2000 ticks idénticos en dos series | 2000 ticks idénticos en dos series, sin disparo |

Comandos: `make fondo-puerta HW=r1` (criterios 1, 2, 3, 4, 6 y 7), `make fondo-criterio5 HW=r1` y `make fondo-bitstreams` (criterio 8 de los dos peldaños). Con `HW=r2` para R2.

**R1 y R2 pasaron la puerta de simulación.** La de placa (autoprueba de P6) está incompleta: R2 pasó el 16/11 la firma a 0,1 ms y la media hora sin disparo, y R1 no se ha corrido (sección "Puerta de placa"). Les falta la de la maestra real el miércoles 25/11, por confirmar.

Lo propio de R2:

- El vigilante no se disparó en ninguna corrida sana, y su cuenta nunca pasó de 1 (el disparo necesita 5).
- Con el supervisor colgado a propósito, `BOOT` sube al terminar la quinta transacción sin respuesta, con `CS_n` en alto y `S1 S0 = 01`, en el RTL y dentro del bitstream simulado desde su `.asc`.
- El relevo completo (R2, reconfiguración y R0) coincide byte por byte con lo esperado en las simulaciones de `make vig-relevo`. Con los 35,50 ms de reconfiguración medidos en la placa el 16/11 son 361 ticks sin decisión nueva a 0,1 ms, 40 a 1 ms y 8 a 10 ms (con los 53 ms de la hoja de datos eran 536, 58 y 10).
- La imagen múltiple tiene los vectores de arranque correctos y las dos imágenes copiadas sin cambios (`tools/ver_multi.py`).

Notas:

- **Criterio 7.** La matriz de la puerta corre por el RTL con `tb/fondo/tb_fondo.sv` (T73), repetida el 16/11 con el arreglo de T81 en el testbench: los casos de rondas seguidas ahora sí cambian de período y siguen pasando, 56 de 56 en R1 y en R2. SCLK de 100 kHz con período de 0,1 ms queda fuera de la puerta como **límite documentado de R1** (decisión de Nicolás del 16/11, opción a): deja 237 ciclos entre transacciones y el fondo necesita hasta 444. R1 responde a tiempo a 0,1 ms desde SCLK de 110 kHz (`docs/mediciones/fondo/r1/sclk_minimo.txt`); el árbol de decisión usa 115 kHz para dejar margen. R0 sí cabe en esa combinación.
- **Validación cruzada con el gemelo (P4, T86).** La matriz de R0 con la referencia del fondo (60 casos) da las mismas 60 líneas por el RTL y por el gemelo: 57 pasan y 3 son exploración (`make fondo-estres-rtl60` y `make fondo-estres-gemelo`). El gemelo, con la tabla, coincide con el RTL de R1 en 21 configuraciones y 18,3 millones de eventos (`make cosim-barrel`).
- **Criterio 5.** De las 9 mutaciones de la extensión, 3 tocan solo lógica de `mulstep`, que R1 y R2 no tienen. En vez de correrlas se probó formalmente que no cambian el core (decisión T74).
- **Criterio 2.** Las 1 050 series sintéticas se corrieron a 0,1 ms por el RTL, y a 0,1, 1 y 10 ms por el gemelo con el hardware de R1, junto con la práctica: 6,36 millones de ticks idénticos a `ref/fondo.py` (`make fondo-gemelo-series`, `docs/mediciones/fondo/r1/gemelo_series.txt`).
- **Un bitstream cambiado con `icebram`** (otra tabla u otro programa) no hereda esta puerta: hay que simularlo desde su `.asc` antes de grabarlo.

Las mediciones del paquete P3, con la tabla todavía en la memoria de datos, quedaron en `docs/mediciones/fondo/p3/`.

## Puerta de placa

La corre Nicolás con las autopruebas de P6 (`docs/autoprueba.md`, secciones 5, 9 y 10). Lo que informó del 16/11 está copiado en `docs/mediciones/placa_16nov.md`.

| Criterio | R0 | R1 | R2 |
|----------|----|----|----|
| 1. Firma a 0,1 ms | "3C" con LED2 y LED3 (mitad baja, vista antes); falta la mitad alta, "A2" con SW4 | **Pendiente** | **Pasa**: "D7" con LED1 a LED3, LED4 apagado |
| 1. Firma a 1 ms y 10 ms | "3C" con LED2 y LED3 en los dos; falta "A2" | **Pendiente** | **Pendiente** |
| 2. Sin relevo en media hora | No aplica | No aplica | **Pasa**: al final "D7" con LED1 a LED3 y "15" con SW4, sin disparo |
| 2. Relevo al inyectar la falla | No aplica | No aplica | **Parcial**: la UART midió un hueco de 35,50 ms, así que hubo reconfiguración, pero no se anotó si apareció la imagen testigo (cuatro LED y "--"). El eco vuelve con cualquiera de las dos imágenes: solo la testigo prueba que cargó la imagen 1 |
| Tiempo del relevo | No aplica | No aplica | 35,50 ms (35,42 a 35,59), una medición de tres pedidas |

Ningún peldaño pasó todavía la puerta de placa completa. A R2 le falta la firma a 1 ms y 10 ms y ver la testigo después del relevo; a R1 las tres firmas; a R0 la mitad alta de su firma. La lista con los comandos está en `docs/pendientes_nicolas.md`.

## Puerta de maestra: la clase del 18/11 (R2 con la regla de cotas)

El 18/11, en la clase, `bitstreams/r2_cotas_multi.bin` (R2 con la regla de cotas de banda 60, hardware de R2) corrió con la maestra real en las tres rondas. Nicolás lo grabó desde su Mac con `iceprog -b` y terminó en "VERIFY OK". Resultados, como los informó Nicolás (fuente: su registro de terminal y los resultados anotados en la clase; las sesiones de trabajo no vieron ese registro):

| Ronda | Período | Serie | Patrimonio | Lugar |
|-------|---------|-------|------------|-------|
| 3 | 0,1 ms | No registrada | Cerca de 25 000 (cifra aproximada) | Primeros |
| 2 | 1 ms | No registrada | 18 870 | Primeros |
| 1 | 10 ms | AMD | 21 895 | No anotado |
| 1 | 10 ms | Tesla | 18 779 | No anotado |

- **Qué respalda.** Los 21 895 de AMD y los 18 779 de Tesla son exactamente lo que da la referencia con banda 60 (`ref/trader.py`, `docs/decisiones.md:770`, `docs/bitacora/banda40.md:11`): con órdenes de 63, la maestra real usa caja 10 000 y comisión 5, ejecuta al precio del mismo tick en que lee el byte, recorta la compra a `(caja - 5) / p` y no cobra una orden que queda en cero. Las series de 0,1 ms y 1 ms no se registraron, así que esas dos cifras no tienen referencia con qué compararlas.
- **Qué prueba del hardware.** El de R2 (barrel con la tabla, el vigilante y la imagen múltiple) recibió precios de la maestra real a los tres ritmos y operó en las tres rondas, con el primer lugar en las de 0,1 y 1 ms. Lo que informó Nicolás no dice si el vigilante hizo un relevo en alguna ronda.
- **Qué no prueba.** No valida los tiempos SPI de R3: R2 responde en 128 ciclos (127 en el testbench oficial) y R3 en hasta 807 ciclos con los cuatro hilos sanos y 916 con un hilo colgado, así que con un SCLK lento R3 se queda sin tiempo antes que R2 (de ahí la regla de SCLK de `docs/c1_dia_de_prueba.md`, sección 2.2). Tampoco prueba la tabla de 512 palabras, que es hardware nuevo, ni las órdenes parciales (menos de 63) de la media posición de C1.
