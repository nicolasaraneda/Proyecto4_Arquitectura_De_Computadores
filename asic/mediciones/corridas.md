# Corridas de LibreLane del macro ASIC del barrel

Generado por `asic/scripts/resumen_barrel.py`. GF180MCU (`gf180mcuD`), LibreLane 3.0.16. Áreas en um2, holguras en ns. "Cierra" con el verificador del Proyecto 3 (setup y hold en 9 esquinas, DRC de Magic, LVS y antenas). Slew y capacitancia son informativos, como en el Proyecto 3.

| corrida | xd | período (ns) | dado | celdas estándar | celdas | flip-flops | setup WNS lenta | setup WNS típica | hold WNS | DRC Magic | DRC KLayout | LVS | antenas | slew | cap | cierra |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| barrel_xd3_t22 | 3 | 22 | 1071890 | 588281 | 25533 | 2929 | 0.175 | 10.046 | 0.046 | 0 | n/c | 0 | 0 | 9 | 5 | sí |
| barrel_xd3_t23.5 | 3 | 23.5 | 1071890 | 578914 | 25467 | 2929 | 0.925 | 11.124 | 0.046 | 0 | n/c | 0 | 0 | 3 | 5 | sí |
| barrel_xd3_t25 | 3 | 25 | 1071890 | 577441 | 25462 | 2929 | 1.385 | 12.062 | 0.056 | 0 | n/c | 0 | 0 | 3 | 5 | sí |
| barrel_xd3_t27 | 3 | 27 | 1071890 | 576958 | 25466 | 2929 | 2.085 | 13.363 | 0.043 | 0 | n/c | 0 | 0 | 7 | 5 | sí |
| barrel_xd3_t30 | 3 | 30 | 1071890 | 577002 | 25465 | 2929 | 4.931 | 16.275 | 0.055 | 0 | n/c | 0 | 0 | 3 | 5 | sí |
| barrel_xd3_t31 | 3 | 31 | 1071890 | 577570 | 25474 | 2929 | 6.177 | 17.387 | 0.058 | 0 | n/c | 0 | 0 | 0 | 5 | sí |
| barrel_xd3_t40 | 3 | 40 | 1071890 | 565604 | 25453 | 2929 | 8.007 | 22.895 | 0.058 | 0 | 0 | 0 | 0 | 4 | 5 | sí |
| barrel_xd7_t40 | 7 | 40 | 1076920 | 575241 | 25697 | 2930 | 8.207 | 22.994 | 0.094 | 0 | 0 | 0 | 0 | 30 | 7 | sí |

Con xd=3 (el hardware de R1) cierra hasta 22 ns (45.5 MHz); ningún período probado falla.
