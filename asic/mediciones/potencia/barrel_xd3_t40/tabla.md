## Potencia de la corrida barrel_xd3_t40 (Espino barrel, sw/fondo.s)

Reloj de 40 ns (25 MHz). Cálculo de OpenSTA con el netlist final, los parásitos extraídos y el liberty de cada esquina. La actividad sale de la simulación del netlist final ejecutando sw/fondo.s con la maestra a 0,1 ms por tick (asic/scripts/potencia_barrel.sh), salvo en la primera columna. Valores en mW.

| esquina | flujo, sin actividad anotada | sondeo | ronda 3 (4 ticks) | cálculo (450 ciclos) |
|---|---|---|---|---|
| típica (tt, 25 C, 5,0 V) | 73.404 | 94.681 | 95.385 | 96.034 |
| lenta (ss, 125 C, 4,5 V) | 60.440 | 78.202 | 78.794 | 79.338 |
| rápida (ff, -40 C, 5,5 V) | 90.007 | 115.590 | 116.428 | 117.208 |

Desglose en la esquina típica, en mW:

| grupo | flujo, sin actividad anotada | sondeo | ronda 3 (4 ticks) | cálculo (450 ciclos) |
|---|---|---|---|---|
| secuencial | 38.144 | 38.347 | 38.405 | 38.479 |
| combinacional | 0.268 | 21.343 | 21.989 | 22.563 |
| reloj | 34.992 | 34.992 | 34.992 | 34.992 |
| total | 73.404 | 94.681 | 95.385 | 96.034 |

Pines sin actividad anotada en las ventanas con VCD: 0 en todas.

Energía por decisión:

| esquina | potencia de sondeo (mW) | energía por decisión, ronda 3 (nJ) | ronda 2 (nJ) | ronda 1 (nJ) | marginal del cálculo (nJ) |
|---|---|---|---|---|---|
| típica (tt, 25 C, 5,0 V) | 94.681 | 9538.5 | 94751.2 | 946877.8 | 24.3594 |
| lenta (ss, 125 C, 4,5 V) | 78.202 | 7879.4 | 78261.6 | 782083.4 | 20.4327 |
| rápida (ff, -40 C, 5,5 V) | 115.590 | 11642.8 | 115673.9 | 1155984.8 | 29.1312 |

La energía de la ronda 3 es la de la ventana ronda 3 por 100 us. Las de las rondas 2 y 1 son estimadas: la de la ronda 3 más la potencia de sondeo por 0,9 ms y 9,9 ms. El marginal del cálculo es la potencia de la ventana de cálculo menos la de sondeo, por los 18 us de la ventana. En el barrel los cuatro hilos ejecutan una instrucción por ciclo también mientras sondean, así que calcular cuesta casi lo mismo que esperar.
