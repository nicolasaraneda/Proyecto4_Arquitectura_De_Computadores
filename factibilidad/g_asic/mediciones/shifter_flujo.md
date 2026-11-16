## Flujo completo a 40 ns sin y con el shifter completo

| corrida | variante | T (ns) | die (um2) | núcleo (um2) | celdas std (um2) | utilización | celdas | flip-flops | setup tt | setup ss | setup ff | setup r2r ss | hold peor | cierra timing | DRC Magic | DRC KLayout | LVS | antenas | cierra todo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base_t40 | base | 40.0 | 359332 | 332375 | 176975 | 0.532 | 8791 | 872 | 23.465 | 9.142 | 28.436 | 9.142 | 0.102 | sí | 0 | n/d | 0 | 0 | sí |
| base_shifter_t40 | base | 40.0 | 387034 | 359712 | 192565 | 0.535 | 9692 | 872 | 22.699 | 7.697 | 28.364 | 7.697 | 0.116 | sí | 0 | n/d | 0 | 0 | sí |
| seg_t40 | seg | 40.0 | 304298 | 280053 | 149757 | 0.535 | 7524 | 774 | 20.870 | 4.709 | 27.966 | 4.709 | 0.123 | sí | 0 | n/d | 0 | 0 | sí |
| seg_shifter_t40 | seg | 40.0 | 331966 | 305809 | 162429 | 0.531 | 8502 | 777 | 22.704 | 7.933 | 28.269 | 7.933 | 0.085 | sí | 0 | n/d | 0 | 0 | sí |

| corrida | T (ns) | período mínimo estimado ss (ns) | fmax estimada ss (MHz) | fmax estimada tt (MHz) | potencia tt (mW) | potencia ss (mW) | potencia ff (mW) | buffers de timing | buffers de reloj | cable (um) | slew | cap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base_t40 | 40.0 | 30.858 | 32.4 | 60.5 | 82.070 | 68.033 | 99.523 | 1124 | 140 | 337149 | 0 | 1 |
| base_shifter_t40 | 40.0 | 32.303 | 31.0 | 57.8 | 97.418 | 80.928 | 117.853 | 1318 | 147 | 388903 | 0 | 1 |
| seg_t40 | 40.0 | 35.291 | 28.3 | 52.3 | 56.458 | 46.741 | 68.560 | 962 | 145 | 266425 | 4 | 1 |
| seg_shifter_t40 | 40.0 | 32.067 | 31.2 | 57.8 | 66.046 | 54.811 | 79.970 | 1045 | 148 | 310340 | 2 | 1 |

Esquinas: tt = nom_tt_025C_5v00, ss = max_ss_125C_4v50, ff = min_ff_n40C_5v50. Las holguras están en ns y son la peor ruta de cada esquina, incluidas las de entrada y salida (IO_DELAY_CONSTRAINT = 20 % del período). "hold peor" es la peor de las 9 esquinas. "setup r2r ss" es la peor ruta entre registros en la esquina lenta. El período mínimo estimado es T menos la holgura de setup de esa corrida: es una estimación, no un cierre a ese período. La potencia es la que informa el flujo con la actividad por defecto de OpenSTA, al período de la corrida. La columna "antenas" suma dos métricas del flujo (antenna__violating__nets y route__antenna_violation__count): un 2 es un solo net en violación, contado por las dos.
