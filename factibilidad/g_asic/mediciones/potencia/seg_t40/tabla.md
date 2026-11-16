## Potencia de la corrida seg_t40 (Espino segmentado)

Reloj de 40.0 ns (25.0 MHz), el de la SDC de la corrida. Cálculo de OpenSTA con el netlist final, los parásitos extraídos y el liberty de cada esquina. La actividad sale de la simulación del netlist ejecutando trade.s con la maestra a 0,1 ms por tick, salvo en las dos primeras columnas. Valores en mW.

| esquina | flujo, sin actividad anotada | solo reloj | sondeo | ronda 3 (4 ticks) | cálculo, tick 20 | cálculo, tick 23 |
|---|---|---|---|---|---|---|
| típica (tt, 25 C, 5,0 V) | 56.458 | 19.651 | 26.183 | 26.276 | 27.331 | 27.438 |
| lenta (ss, 125 C, 4,5 V) | 46.741 | 16.164 | 21.622 | 21.696 | 22.572 | 22.660 |
| rápida (ff, -40 C, 5,5 V) | 68.560 | 24.066 | 31.954 | 32.070 | 33.345 | 33.474 |

Desglose en la esquina típica, en mW:

| grupo | flujo, sin actividad anotada | solo reloj | sondeo | ronda 3 (4 ticks) | cálculo, tick 20 | cálculo, tick 23 |
|---|---|---|---|---|---|---|
| secuencial | 14.509 | 10.138 | 10.359 | 10.364 | 10.495 | 10.493 |
| combinacional | 32.437 | 0.001 | 6.313 | 6.400 | 7.324 | 7.433 |
| reloj | 9.512 | 9.512 | 9.512 | 9.512 | 9.512 | 9.512 |
| total | 56.458 | 19.651 | 26.183 | 26.276 | 27.331 | 27.438 |

Actividad anotada desde el VCD en la ventana ronda3: 17895 pines, 0 sin anotar.

Energía por decisión y Ops/W:

| esquina | potencia de sondeo (mW) | energía por decisión, ronda 3 (nJ) | ronda 2 (nJ) | ronda 1 (nJ) | marginal del cálculo (nJ) | decisiones por joule, ronda 3 | Ppeak (MOPS) | Ppeak por watt (MOPS/W) | kernel (MOPS) | kernel por watt (MOPS/W) |
|---|---|---|---|---|---|---|---|---|---|---|
| típica (tt, 25 C, 5,0 V) | 26.183 | 2627.6 | 26192.7 | 261843.3 | 3.8437 | 3.806e+05 | 25.0 | 913 | 4.41 | 161 |
| lenta (ss, 125 C, 4,5 V) | 21.622 | 2169.6 | 21628.9 | 216222.9 | 3.1823 | 4.609e+05 | 25.0 | 1105 | 4.41 | 195 |
| rápida (ff, -40 C, 5,5 V) | 31.954 | 3207.0 | 31966.1 | 319556.6 | 4.6566 | 3.118e+05 | 25.0 | 748 | 4.41 | 132 |

Ciclos del tick completo: 34 en promedio y 38 en el peor caso (docs/mediciones/ticks_segmentado.txt, ronda 3). Operaciones útiles por tick: 6 (definición nuestra, ver el encabezado de este script). Ppeak por watt y kernel por watt usan la potencia de la ventana de cálculo (promedio de los ticks 20 y 23). La energía de la ronda 3 es medida con la ventana ronda3. Las de las rondas 2 y 1 son estimadas: la de la ronda 3 más la potencia de sondeo por 0,9 ms y 9,9 ms. El marginal del cálculo es la potencia de la ventana de cálculo menos la de sondeo, por los 3,2 us de la ventana.
