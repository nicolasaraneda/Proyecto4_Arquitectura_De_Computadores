## Costo del shifter completo en el flujo completo (40 ns)

### Espino base

| | sin shifter (base_t40) | con shifter (base_shifter_t40) | diferencia | % |
|---|---|---|---|---|
| área del dado (um2) | 359332 | 387034 | +27702 | +7.7 |
| área del núcleo (um2) | 332375 | 359712 | +27337 | +8.2 |
| área de celdas estándar (um2) | 176975 | 192565 | +15590 | +8.8 |
| celdas | 8791 | 9692 | +901 | +10.2 |
| flip-flops | 872 | 872 | +0 | +0.0 |
| largo de cable (um) | 337149 | 388903 | +51754 | +15.4 |
| holgura de setup, esquina lenta (ns) | 9.142 | 7.697 | -1.445 |  |
| holgura de setup, esquina típica (ns) | 23.465 | 22.699 | -0.766 |  |
| holgura de hold, peor esquina (ns) | 0.102 | 0.116 | +0.014 |  |
| cierra timing en las 9 esquinas | sí | sí | | |
| además DRC de Magic, LVS y antenas en cero | sí | sí | | |

### Espino segmentado

| | sin shifter (seg_t40) | con shifter (seg_shifter_t40) | diferencia | % |
|---|---|---|---|---|
| área del dado (um2) | 304298 | 331966 | +27668 | +9.1 |
| área del núcleo (um2) | 280053 | 305809 | +25756 | +9.2 |
| área de celdas estándar (um2) | 149757 | 162429 | +12672 | +8.5 |
| celdas | 7524 | 8502 | +978 | +13.0 |
| flip-flops | 774 | 777 | +3 | +0.4 |
| largo de cable (um) | 266425 | 310340 | +43915 | +16.5 |
| holgura de setup, esquina lenta (ns) | 4.709 | 7.933 | +3.224 |  |
| holgura de setup, esquina típica (ns) | 20.870 | 22.704 | +1.834 |  |
| holgura de hold, peor esquina (ns) | 0.123 | 0.085 | -0.037 |  |
| cierra timing en las 9 esquinas | sí | sí | | |
| además DRC de Magic, LVS y antenas en cero | sí | sí | | |

Una corrida por caso. La holgura de una corrida no predice el período mínimo: el resizer deja de reparar cuando cumple su margen, así que la diferencia de holgura entre las dos columnas no es el costo del shifter en frecuencia. Lo que sí se demuestra es que con el shifter completo el macro cierra a 40 ns (25 MHz). No se hizo barrido de período con el shifter.
