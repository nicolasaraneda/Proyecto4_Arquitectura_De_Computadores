## Comparación: macro ASIC del Proyecto 4, FPGA y ASIC del Proyecto 3

### Cierre del macro ASIC por período

| variante | T (ns) | frecuencia (MHz) | holgura de setup, esquina lenta (ns) | hold peor (ns) | cierra timing | DRC, LVS y antenas limpios |
|---|---|---|---|---|---|---|
| base | 40 | 25.0 | 9.142 | 0.102 | sí | sí |
| base | 30 | 33.3 | 4.626 | 0.103 | sí | sí |
| base | 25 | 40.0 | 1.402 | 0.100 | sí | sí |
| base | 23.5 | 42.6 | 0.245 | 0.101 | sí | sí |
| base | 22 | 45.5 | -0.479 | 0.107 | no | sí |
| seg | 40 | 25.0 | 4.709 | 0.123 | sí | sí |
| seg | 30 | 33.3 | 2.466 | 0.113 | sí | sí |
| seg | 25 | 40.0 | 1.702 | 0.118 | sí | no |
| seg | 23.5 | 42.6 | 1.435 | 0.116 | sí | sí |
| seg | 22 | 45.5 | -5.414 | 0.120 | no | no |

### Las dos variantes en las tres plataformas

| | Espino base | Espino segmentado |
|---|---|---|
| FPGA iCE40 HX1K: celdas lógicas de 1280 | 1083 | 994 (fetch en BRAM), 1055 (ROM combinacional) |
| FPGA: BRAM de 16 | 12 | 12 y 8 |
| FPGA: Fmax en 10 semillas, mínima y mediana (MHz) | 42.43 y 43.74 | 51.13 y 53.50 (BRAM), 50.04 y 53.16 (ROM) |
| ASIC GF180, corrida de 40 ns: área del dado (um2) | 359332 | 304298 |
| ASIC: área del núcleo (um2) | 332375 | 280053 |
| ASIC: área de celdas estándar (um2) | 176975 | 149757 |
| ASIC: utilización del núcleo | 0.532 | 0.535 |
| ASIC: celdas estándar y flip-flops | 8791 y 872 | 7524 y 774 |
| ASIC: frecuencia más alta del barrido que cierra timing en las 9 esquinas | 42.6 MHz (23.5 ns) | 42.6 MHz (23.5 ns) |
| ASIC: lo mismo, además sin errores de DRC, LVS ni antenas | 42.6 MHz (23.5 ns) | 42.6 MHz (23.5 ns) |
| CPI medido, mix de la clase 7 | 2.350 | 1.350 |
| CPI medido, trade.s con el sondeo | 2.652 | 1.657 |
| MIPS en la FPGA a 25 MHz, mix de la clase 7 | 10.64 | 18.52 |
| MIPS en el ASIC a la frecuencia de cierre de timing, mix de la clase 7 | 18.11 | 31.52 |
| MIPS en la FPGA a 25 MHz, trade.s | 9.43 | 15.08 |
| MIPS en el ASIC a la frecuencia de cierre de timing, trade.s | 16.05 | 25.67 |
| ASIC: potencia a 25 MHz con la actividad de la ronda 3, esquina típica (mW) | 28.03 | 26.28 |
| ASIC: energía por decisión en la ronda 3, potencia por 0,1 ms (uJ) | 2.80 | 2.63 |

### Contra el ASIC del Proyecto 3

| | Proyecto 3, corrida final | Proyecto 4, Espino base | Proyecto 4, Espino segmentado |
|---|---|---|---|
| Período de la corrida (ns) | 100 | 40 | 40 |
| Área del dado (um2) | 419131 | 359332 | 304298 |
| Área del núcleo (um2) | 389525 | 332375 | 280053 |
| Área de celdas estándar (um2) | 208439 | 176975 | 149757 |
| Celdas estándar y flip-flops | 9928 y 964 | 8791 y 872 | 7524 y 774 |
| Frecuencia máxima de cierre | 46,5 MHz (21,5 ns), documentado en asic/final.md del Proyecto 3 | 42.6 MHz (23.5 ns) | 42.6 MHz (23.5 ns) |
| MIPS con el CPI de su propio programa | 27,9 (CPI del juego 1,665), documentado | 16.0 (CPI de trade.s 2.652) | 25.7 (CPI de trade.s 1.657) |

El Proyecto 3 lleva el pipeline con lectura anticipada, antirrebote de botones y contador de ciclos; el macro del Proyecto 4 no tiene esos dos periféricos. La frecuencia del Proyecto 3 salió de un barrido fino (pasos de 0,5 ns) con su modelo de cable derivado de su propia extracción; aquí el barrido tiene 5 puntos y el modelo de cable es el copiado del Proyecto 3.
