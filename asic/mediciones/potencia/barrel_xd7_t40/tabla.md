## Potencia de la corrida barrel_xd7_t40 (Espino barrel, sw/fondo.s)

Reloj de 40 ns (25 MHz). Cálculo de OpenSTA con el netlist final, los parásitos extraídos y el liberty de cada esquina. La actividad sale de la simulación del netlist final ejecutando sw/fondo.s con la maestra a 0,1 ms por tick (asic/scripts/potencia_barrel.sh), salvo en la primera columna. Valores en mW.

| esquina | flujo, sin actividad anotada | sondeo | ronda 3 (4 ticks) | cálculo (450 ciclos) |
|---|---|---|---|---|
| típica (tt, 25 C, 5,0 V) | 74.545 | 95.773 | 96.488 | 97.259 |
| lenta (ss, 125 C, 4,5 V) | 61.334 | 79.041 | 79.643 | 80.287 |
| rápida (ff, -40 C, 5,5 V) | 91.487 | 117.034 | 117.882 | 118.812 |

Desglose en la esquina típica, en mW:

| grupo | flujo, sin actividad anotada | sondeo | ronda 3 (4 ticks) | cálculo (450 ciclos) |
|---|---|---|---|---|
| secuencial | 38.162 | 38.411 | 38.461 | 38.535 |
| combinacional | 0.259 | 21.237 | 21.902 | 22.599 |
| reloj | 36.125 | 36.125 | 36.125 | 36.125 |
| total | 74.545 | 95.773 | 96.488 | 97.259 |

Pines sin actividad anotada en las ventanas con VCD: 0 en todas.

Energía por decisión:

| esquina | potencia de sondeo (mW) | energía por decisión, ronda 3 (nJ) | ronda 2 (nJ) | ronda 1 (nJ) | marginal del cálculo (nJ) |
|---|---|---|---|---|---|
| típica (tt, 25 C, 5,0 V) | 95.773 | 9648.8 | 95844.9 | 957806.3 | 26.7307 |
| lenta (ss, 125 C, 4,5 V) | 79.041 | 7964.3 | 79101.7 | 790475.2 | 22.4150 |
| rápida (ff, -40 C, 5,5 V) | 117.034 | 11788.2 | 117119.0 | 1170427.7 | 31.9914 |

La energía de la ronda 3 es la de la ventana ronda 3 por 100 us. Las de las rondas 2 y 1 son estimadas: la de la ronda 3 más la potencia de sondeo por 0,9 ms y 9,9 ms. El marginal del cálculo es la potencia de la ventana de cálculo menos la de sondeo, por los 18 us de la ventana. En el barrel los cuatro hilos ejecutan una instrucción por ciclo también mientras sondean, así que calcular cuesta casi lo mismo que esperar.
