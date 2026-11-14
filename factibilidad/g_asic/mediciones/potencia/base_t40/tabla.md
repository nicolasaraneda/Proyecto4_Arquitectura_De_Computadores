## Potencia de la corrida base_t40 (Espino base)

Reloj de 40.0 ns (25.0 MHz), el de la SDC de la corrida. Cálculo de OpenSTA con el netlist final, los parásitos extraídos y el liberty de cada esquina. La actividad sale de la simulación del netlist ejecutando trade.s con la maestra a 0,1 ms por tick, salvo en las dos primeras columnas. Valores en mW.

| esquina | flujo, sin actividad anotada | solo reloj | sondeo | ronda 3 (4 ticks) | cálculo, tick 20 | cálculo, tick 23 |
|---|---|---|---|---|---|---|
| típica (tt, 25 C, 5,0 V) | 82.070 | 21.714 | 27.973 | 28.029 | 28.700 | 28.881 |
| lenta (ss, 125 C, 4,5 V) | 68.033 | 17.896 | 23.129 | 23.175 | 23.734 | 23.884 |
| rápida (ff, -40 C, 5,5 V) | 99.523 | 26.544 | 34.110 | 34.178 | 34.983 | 35.201 |

Desglose en la esquina típica, en mW:

| grupo | flujo, sin actividad anotada | solo reloj | sondeo | ronda 3 (4 ticks) | cálculo, tick 20 | cálculo, tick 23 |
|---|---|---|---|---|---|---|
| secuencial | 18.948 | 11.534 | 11.438 | 11.441 | 11.519 | 11.520 |
| combinacional | 52.942 | 0.001 | 6.356 | 6.409 | 7.002 | 7.181 |
| reloj | 10.179 | 10.179 | 10.179 | 10.179 | 10.179 | 10.179 |
| total | 82.070 | 21.714 | 27.973 | 28.029 | 28.700 | 28.881 |

Actividad anotada desde el VCD en la ventana ronda3: 21034 pines, 0 sin anotar.

Energía por decisión y Ops/W:

| esquina | potencia de sondeo (mW) | energía por decisión, ronda 3 (nJ) | ronda 2 (nJ) | ronda 1 (nJ) | marginal del cálculo (nJ) | decisiones por joule, ronda 3 | Ppeak (MOPS) | Ppeak por watt (MOPS/W) | kernel (MOPS) | kernel por watt (MOPS/W) |
|---|---|---|---|---|---|---|---|---|---|---|
| típica (tt, 25 C, 5,0 V) | 27.973 | 2802.9 | 27978.9 | 279738.2 | 2.6153 | 3.568e+05 | 12.5 | 434 | 2.38 | 83 |
| lenta (ss, 125 C, 4,5 V) | 23.129 | 2317.5 | 23133.4 | 231292.9 | 2.1765 | 4.315e+05 | 12.5 | 525 | 2.38 | 100 |
| rápida (ff, -40 C, 5,5 V) | 34.110 | 3417.8 | 34116.5 | 341103.5 | 3.1439 | 2.926e+05 | 12.5 | 356 | 2.38 | 68 |

Ciclos del tick completo: 63 en promedio y 66 en el peor caso (docs/mediciones/ticks_software.txt, ronda 3). Operaciones útiles por tick: 6 (definición nuestra, ver el encabezado de este script). Ppeak por watt y kernel por watt usan la potencia de la ventana de cálculo (promedio de los ticks 20 y 23). La energía de la ronda 3 es medida con la ventana ronda3. Las de las rondas 2 y 1 son estimadas: la de la ronda 3 más la potencia de sondeo por 0,9 ms y 9,9 ms. El marginal del cálculo es la potencia de la ventana de cálculo menos la de sondeo, por los 3,2 us de la ventana.
