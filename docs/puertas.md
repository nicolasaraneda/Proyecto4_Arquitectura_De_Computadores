# Puertas de la escalera de bitstreams

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Un bitstream sube a la escalera solo si pasa tres puertas, en orden: simulación, placa y maestra real (26/11). Este documento dice cómo se comprueba cada criterio de la puerta de simulación y deja el estado de cada peldaño. La escalera y la razón de cada peldaño están en la decisión T50.

| Peldaño | Hardware | Programa | Archivo |
|---------|----------|----------|---------|
| R0 | Espino base, sin hardware agregado | `sw/trade.s` con `max_media` | `bitstreams/r0_base_max_media.bin` |
| R1 | Espino barrel con la extensión y la tabla, sin vigilante | `sw/fondo.s` | Pendiente (P2 a P5). El core solo ya pasó los criterios 1, 3 y 5 (P1) |
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
| 7 | 60 casos en el rango pedido, todos pasan (`docs/mediciones/estres_base.txt`). SCLK funciona hasta 4 MHz; a 5 MHz no (exploración, decisión T53) |
| 8 | 2 000 ticks a 0,1 ms del `.asc` ruteado idénticos a la referencia |

R0 pasó la puerta de simulación. Le faltan la de placa (la corre Nicolás con la autoprueba de P6) y la de la maestra real el 26/11.


## Espino barrel con un programa de un hilo

Medido el 15/11 (paquete P1). No es un peldaño de la escalera: es el core de R1 y R2, todavía sin la extensión, sin la tabla y sin `sw/fondo.s`, corriendo `sw/trade.s` en el hilo 0 con la tabla de arranque. El paquete pedía los criterios 1, 3 y 5. Detalle en `docs/espino_barrel.md` y salidas en `docs/mediciones/barrel/`.

| N.º | Resultado | Comando |
|-----|-----------|---------|
| 1 | 4/4 con `tb/tb_proyecto_4.sv` sin modificar. Peor caso 83 ciclos de 2262. `decisiones.csv` idéntico byte a byte al del Espino base | `make barrel-oficial` |
| 3 | 10 de 10 semillas. 933 celdas de 1280 y 12 BRAM de 16. Frecuencia máxima mínima 52,62 MHz, mediana 55,65 y máxima 59,18 | `make barrel-timing` |
| 5 | 7 948 558 instrucciones en 20 600 programas, 7 309 470 distintas en toda la campaña (91,96 %), cero diferencias con el Espino base. Aparte, 8 966 903 instrucciones en la campaña de lazos. 21 de 21 mutaciones detectadas, cada una por las 7 comparaciones. 24 afirmaciones formales de estructura probadas | `make barrel-verif`, `make barrel-mutaciones` y `make barrel-formal` |

Medido además, sin que el paquete lo pidiera: los 20 000 ticks idénticos a la referencia a 0,1 ms y a 1 ms con Verilator (parte del criterio 2), peor caso de 88 ciclos barriendo la fase del sondeo con el método del prototipo (criterio 4, falta repetirlo con `make fases`) y 500 ticks del bitstream ruteado idénticos a la referencia (criterio 8, que pide 2 000).

Los criterios 2, 4, 6, 7 y 8 se cierran con el programa que compite, en P3 a P5.
