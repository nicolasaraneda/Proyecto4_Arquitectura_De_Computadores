# Puertas de la escalera de bitstreams

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Un bitstream sube a la escalera solo si pasa tres puertas, en orden: simulación, placa y maestra real (26/11). Este documento dice cómo se comprueba cada criterio de la puerta de simulación y deja el estado de cada peldaño. La escalera y la razón de cada peldaño están en la decisión T50.

| Peldaño | Hardware | Programa | Archivo |
|---------|----------|----------|---------|
| R0 | Espino base, sin hardware agregado | `sw/trade.s` con `max_media` | `bitstreams/r0_base_max_media.bin` |
| R1 | Espino barrel con `emad` y `devk` y la tabla, sin vigilante | `sw/fondo.s` | Pendiente (P5). El hardware sin la tabla dedicada ya pasó los criterios 1, 2, 3, 4, 5 y 6 con `sw/fondo.s` (P1 a P3) |
| R2 | R1 con vigilante y dos imágenes | `sw/fondo.s` e imagen de respaldo | Pendiente (P5) |

## Puerta de simulación

| N.º | Criterio | Cómo se comprueba |
|-----|----------|-------------------|
| 1 | Testbench oficial sin modificar: 4/4 | `make tb` |
| 2 | Decisiones idénticas a la referencia en los 20 000 ticks de práctica a los tres períodos, y en al menos 1 000 series sintéticas | `make equiv` (gemelo a los tres períodos, Verilator a 0,1 y 1 ms, 13 familias), `make equiv-r3` (Icarus a 0,1 ms), `make equiv-largo` (Verilator a 10 ms) y `make equiv-gemelo` (3810 series del protocolo a los tres períodos) |
| 3 | Timing a 25 MHz en 10 de 10 semillas, reportando la mínima | `EXIGIR=1 tools/medir_variante.sh base 10` |
| 4 | Peor caso de respuesta barriendo las 8 fases del sondeo y las 4 alineaciones de hilo, menor que la mitad del presupuesto de la ronda 3 (1131 ciclos) | `make fases` (`tools/estres.py --solo fases`). En el core base no hay alineaciones de hilo |
| 5 | Verificación del core que compite contra el core base, con el generador corregido: al menos 5 millones de instrucciones con más de 90 % distintas, y todas las mutaciones detectadas | Para el barrel, `make barrel-verif` y `make barrel-mutaciones` (decisión T57). Para R0 ver la nota |
| 6 | Degradación: un hilo gestor en lazo infinito, un voto que nunca llega, un voto atrasado | Para el fondo, P3. No aplica a R0 |
| 7 | Estrés: SCLK entre 100 kHz y 1 MHz, tiempos de `CS_n` distintos, reset con la maestra transmitiendo, rondas seguidas sin reset, serie pegada en 1 y en 255 | `make estres` (`tools/estres.py`, `tb/tb_estres.sv`) |
| 8 | Simulación del bitstream ya ruteado, 2 000 ticks idénticos a la referencia | `make sim-bitstream` |

`tb/tb_estres.sv` es una maestra con la misma transacción y la misma medición que el testbench oficial, pero con los tiempos elegidos en tiempo de ejecución (decisión T53). `tools/estres.py` compara cada byte que lee la maestra con `ref/trader.py`, exige MISO sin X y ningún precio sin leer ni sin respuesta, y modela como perdidos los precios que llegan antes de que termine el reset de encendido. Los casos con SCLK sobre 1 MHz son exploración y no cuentan para la puerta.

## R0: core base con `max_media`

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

R0 pasó la puerta de simulación. Le faltan la de placa (la corre Nicolás con la autoprueba de P6, `docs/autoprueba.md`, sección 5) y la de la maestra real el 26/11.


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

## El fondo en un chip: barrel con `emad` y `devk` y `sw/fondo.s`

Medido el 15/11 (paquete P3). Es el hardware de R1 sin la tabla en BRAM (`-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK`, decisión de Nicolás sobre T58) con el programa de competencia. La tabla de parámetros va por ahora en la memoria de datos (T65). El paquete pedía los criterios 1, 2, 4 y 6. Detalle en `docs/fondo.md` y salidas en `docs/mediciones/fondo/`.

| N.º | Resultado | Comando |
|-----|-----------|---------|
| 1 | 4/4 con `tb/tb_proyecto_4.sv` sin modificar. Peor caso 435 ciclos de 2262. `decisiones.csv` idéntico byte a byte al de `ref/fondo.py` | `make fondo-oficial` |
| 2 | Cero diferencias con `ref/fondo.py`. Serie de práctica completa a 0,1 ms, 1 ms y 10 ms con la copia parametrizada del oficial (4/4 en las tres) y con `tb/fondo/tb_fondo.sv`. Una serie de 20 000 ticks de cada una de las 15 familias. 1 050 series sintéticas de 2000 ticks a 0,1 ms (2,1 millones de ticks). Con `tb_fondo.sv` se compara además el estado interno en cada decisión, la telemetría y el protocolo. En P4, con el gemelo: las mismas 1 050 series más la práctica a los tres períodos, 6,36 millones de ticks | `make fondo-equiv-ronda1`, `make fondo-series` y `make fondo-gemelo-series` |
| 3 | 10 de 10 semillas. 990 celdas de 1280 y 12 BRAM de 16. Frecuencia máxima mínima 48,92 MHz, mediana 51,08 y máxima 54,05 | `make fondo-timing` |
| 4 | Peor caso 480 ciclos con el programa sano (72 fases de un ciclo y un período de 2501 ciclos que las recorre todas) y 564 con gestores colgados y el plazo agotado, contra el límite de 1131 | `make fondo-fases` |
| 5 | El core es el de P2: `make xd-verif` y `make xd-mutaciones` cubren el subconjunto `emad` y `devk` dentro de sus 7 966 640 instrucciones. No se repitió con la máscara exacta: ver la nota | |
| 6 | 30 corridas de 20 000 ticks: cada gestor en lazo infinito desde el arranque y desde el tick 1500, dos y tres colgados, un voto que no llega (en un tick, en una frontera y en un tramo), y un voto atrasado dentro y fuera del plazo. La decisión es la esperada en todas y el peor caso son 671 ciclos de 1131. 15 de 15 controles negativos detectados | `make fondo-degradacion` y `make fondo-controles` |
| 7 | 59 de 60 casos, por el RTL y por el gemelo con resultados idénticos caso por caso. Falla SCLK de 100 kHz con período de 0,1 ms: la transacción dura 90,5 us, el presupuesto es de 237 ciclos y el fondo responde en hasta 474 (bytes iguales a la referencia en esa serie, pero sin la garantía de tiempo). Desde 115 kHz responde a tiempo. Pendiente de decisión de Nicolás (P4) | `make fondo-estres`, `make fondo-estres-gemelo` y `make fondo-sclk-minimo` |
| 8 | Pendiente (P5, con el bitstream de R1) | |

Nota sobre el criterio 5. Pide la verificación del core "en la configuración exacta que compite". La campaña de P2 se corrió con las tres instrucciones (`-DESPINO_XD`), y la prueba formal y el timing con los 7 subconjuntos. Para R1 falta repetir la campaña de simulación con la máscara de `emad` y `devk` (`XD=3`) y con la tabla de P5 puesta: conviene hacerlo una sola vez, al cerrar P5, sobre el hardware definitivo.

Cómo se comprueba el criterio 6. Cada caso es `sw/fondo.s` con instrucciones insertadas en la rutina de los gestores (`tools/fondo/variante.py`); el supervisor no se toca. La decisión esperada sale de `ref/fondo.py` con la falla descrita como "el voto del gestor K no llega entre los ticks N y M" (decisión T68).
