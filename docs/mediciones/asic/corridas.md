## Corridas de LibreLane del macro ASIC

| corrida | variante | T (ns) | die (um2) | núcleo (um2) | celdas std (um2) | utilización | celdas | flip-flops | setup tt | setup ss | setup ff | setup r2r ss | hold peor | cierra timing | DRC Magic | DRC KLayout | LVS | antenas | cierra todo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base_t40 | base | 40.0 | 359332 | 332375 | 176975 | 0.532 | 8791 | 872 | 23.465 | 9.142 | 28.436 | 9.142 | 0.102 | sí | 0 | n/d | 0 | 0 | sí |
| base_t30 | base | 30.0 | 359332 | 332375 | 187053 | 0.563 | 8785 | 872 | 16.209 | 4.626 | 20.434 | 4.626 | 0.103 | sí | 0 | n/d | 0 | 0 | sí |
| base_t25 | base | 25.0 | 359332 | 332375 | 188638 | 0.568 | 8780 | 872 | 12.269 | 1.402 | 16.448 | 1.402 | 0.100 | sí | 0 | n/d | 0 | 0 | sí |
| base_t23p5 | base | 23.5 | 359332 | 332375 | 191823 | 0.577 | 8781 | 872 | 10.958 | 0.245 | 15.231 | 0.245 | 0.101 | sí | 0 | n/d | 0 | 0 | sí |
| base_t22 | base | 22.0 | 359332 | 332375 | 195654 | 0.589 | 8777 | 872 | 9.864 | -0.479 | 14.019 | -0.479 | 0.107 | no | 0 | n/d | 0 | 0 | no |
| seg_t40 | seg | 40.0 | 304298 | 280053 | 149757 | 0.535 | 7524 | 774 | 20.870 | 4.709 | 27.966 | 4.709 | 0.123 | sí | 0 | n/d | 0 | 0 | sí |
| seg_t30 | seg | 30.0 | 304298 | 280053 | 160924 | 0.575 | 7538 | 774 | 14.949 | 2.466 | 20.318 | 2.466 | 0.113 | sí | 0 | n/d | 0 | 0 | sí |
| seg_t25 | seg | 25.0 | 304298 | 280053 | 161571 | 0.577 | 7528 | 774 | 12.333 | 1.702 | 16.294 | 1.702 | 0.118 | sí | 0 | n/d | 0 | 2 | no |
| seg_t23p5 | seg | 23.5 | 304298 | 280053 | 163391 | 0.583 | 7527 | 774 | 11.530 | 1.435 | 15.101 | 1.435 | 0.116 | sí | 0 | n/d | 0 | 0 | sí |
| seg_t22 | seg | 22.0 | 304298 | 280053 | 164258 | 0.587 | 7551 | 774 | 7.041 | -5.414 | 12.500 | -5.414 | 0.120 | no | 0 | n/d | 0 | 2 | no |

| corrida | T (ns) | período mínimo estimado ss (ns) | fmax estimada ss (MHz) | fmax estimada tt (MHz) | potencia tt (mW) | potencia ss (mW) | potencia ff (mW) | buffers de timing | buffers de reloj | cable (um) | slew | cap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base_t40 | 40.0 | 30.858 | 32.4 | 60.5 | 82.070 | 68.033 | 99.523 | 1124 | 140 | 337149 | 0 | 1 |
| base_t30 | 30.0 | 25.374 | 39.4 | 72.5 | 120.529 | 99.781 | 146.364 | 1118 | 140 | 343349 | 0 | 1 |
| base_t25 | 25.0 | 23.598 | 42.4 | 78.5 | 146.041 | 120.859 | 177.399 | 1113 | 140 | 343741 | 0 | 1 |
| base_t23p5 | 23.5 | 23.255 | 43.0 | 79.7 | 159.880 | 132.278 | 194.276 | 1114 | 140 | 347182 | 0 | 1 |
| base_t22 | 22.0 | 22.479 | 44.5 | 82.4 | 177.084 | 146.369 | 215.385 | 1110 | 140 | 348621 | 0 | 1 |
| seg_t40 | 40.0 | 35.291 | 28.3 | 52.3 | 56.458 | 46.741 | 68.560 | 962 | 145 | 266425 | 4 | 1 |
| seg_t30 | 30.0 | 27.534 | 36.3 | 66.4 | 85.571 | 70.717 | 104.107 | 976 | 145 | 271310 | 10 | 1 |
| seg_t25 | 25.0 | 23.298 | 42.9 | 78.9 | 103.426 | 85.464 | 125.841 | 965 | 145 | 271174 | 4 | 1 |
| seg_t23p5 | 23.5 | 22.065 | 45.3 | 83.5 | 111.470 | 92.085 | 135.663 | 965 | 145 | 273048 | 16 | 1 |
| seg_t22 | 22.0 | 27.414 | 36.5 | 66.9 | 119.771 | 98.917 | 145.808 | 988 | 145 | 272887 | 7 | 1 |

Esquinas: tt = nom_tt_025C_5v00, ss = max_ss_125C_4v50, ff = min_ff_n40C_5v50. Las holguras están en ns y son la peor ruta de cada esquina, incluidas las de entrada y salida (IO_DELAY_CONSTRAINT = 20 % del período). "hold peor" es la peor de las 9 esquinas. "setup r2r ss" es la peor ruta entre registros en la esquina lenta. El período mínimo estimado es T menos la holgura de setup de esa corrida: es una estimación, no un cierre a ese período. La potencia es la que informa el flujo con la actividad por defecto de OpenSTA, al período de la corrida. La columna "antenas" suma dos métricas del flujo (antenna__violating__nets y route__antenna_violation__count): un 2 es un solo net en violación, contado por las dos.
