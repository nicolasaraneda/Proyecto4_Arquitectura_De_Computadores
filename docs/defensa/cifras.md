# Cifras para saber de memoria

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Una hoja. Cada cifra con su fuente. Si una cifra de aquí no calza con la fuente, manda la fuente. Cuando dos mediciones del mismo diseño dan números algo distintos (ruido de la síntesis, decisión T6), se dan las dos.

## Plataforma y reglas

| Cifra | Valor | Fuente |
|-------|-------|--------|
| FPGA | iCE40 HX1K VQ100: 1280 celdas lógicas, 16 BRAM, 25 MHz, sin PLL | `docs/mediciones/pll_nextpnr.txt` |
| Transacción SPI del testbench | 9,5 us (1 us, 8 bits a 1 MHz, 0,5 us) | `tb/tb_proyecto_4.sv:19` |
| Presupuesto por tick, (T - 9500 ns) / 40 ns | Ronda 1 (10 ms): 249 762. Ronda 2 (1 ms): 24 762. Ronda 3 (0,1 ms): 2 262 ciclos | `tb/tb_proyecto_4.sv:133` |
| Límite de la puerta (mitad de la ronda 3) | 1131 ciclos | `docs/puertas.md` |
| Caja y comisión | 10 000 y 5 | `tb/tb_proyecto_4.sv:17` y `:18` |

## Recursos de los peldaños

| Peldaño | Celdas de 1280 | BRAM de 16 | Fmax mínima en 10 semillas | Fuente |
|---------|----------------|------------|----------------------------|--------|
| R0, Espino base con `max_media` | 1083 (P0); 1091 en P7 | 12 | 42,43 MHz (P0); 41,93 en P7 | `docs/puertas.md`; `docs/mediciones/p7/variantes.txt` |
| R1, barrel con `emad`, `devk` y tabla | 1029 | 13 | 51,59 MHz | `docs/puertas.md` |
| R2, R1 con vigilante | 1045 | 13 | 47,86 MHz | `docs/puertas.md` |
| Segmentado (no compite) | 994 (P1); 990 en P7 | 12 | 51,13 (P1); 45,34 en P7 | `docs/mediciones/espino_segmentado.txt`; `docs/mediciones/p7/variantes.txt` |
| Shifter completo en el base | 1491: no cabe | 12 | | `docs/mediciones/base.txt` |
| Extensión: `emad` y `devk` / las tres | +52 / +96 celdas | 0 | 48,92 / 48,33 | `docs/mediciones/xd/timing.txt` |

Todas cierran 25 MHz en 10 de 10 semillas.

## Ciclos de respuesta (de `byte_done` a `DECISION`)

| | Promedio | Peor del testbench | Peor barriendo fases | Otros | Fuente |
|-|----------|--------------------|----------------------|-------|--------|
| R0 | 41,0 | 44 | 49 (primer precio) | | `docs/puertas.md`, criterio 4 |
| Segmentado | 22,0 | 26 | 27 | | `docs/mediciones/p7/variantes.txt`, `docs/espino_barrel.md` |
| Barrel, `trade.s` en un hilo | 75,0 | 83 | 88 | | idem |
| Barrel con extensión, `trade_xd.s` | 55,0 | 63 | | | `docs/mediciones/p7/variantes.txt` |
| R1 y R2 (fondo) | 223,01 (8,92 us) | 443 | 444 | 568 con plazo agotado; 679 con voto atrasado | `docs/mediciones/fondo/r1/ticks.txt`, `fases.txt`, `degradacion.txt` |

Uso del presupuesto de la ronda 3 en el peor caso: R0 2,2 % (49 ciclos); **R1 19,6 %** (444 ciclos), 80 % de holgura.

## CPI, IC y desempeño

| Cifra | Valor | Fuente |
|-------|-------|--------|
| Costo por clase en el base | ALU 2, store 2, load 3, salto no tomado 2, tomado 3 | `docs/mediciones/espino_segmentado.txt`, sección 2 |
| Costo por clase en el segmentado | 1, 1, 2, 1, 2 | idem |
| CPI con el mix de la clase 7 | Base 2,350; segmentado 1,350 (la clase estimó 1,5); barrel 1,000 agregado | `docs/mediciones/espino_segmentado.txt`, `docs/mediciones/barrel/cpi.txt` |
| CPI por hilo en el barrel | 4,000, cualquier mezcla | `docs/mediciones/barrel/cpi.txt` |
| `trade.s` en R0, respuesta | IC 19,5 prom. y 21 peor; CPI 2,10 | `docs/mediciones/ticks_software.txt` |
| `trade.s` en R0, tick completo | IC 28,5 y 30; ciclos 63 y 66; CPI 2,21 | idem |
| Fondo, supervisor | IC 68,59 prom. y 116 máx.; 274,37 ciclos | `docs/mediciones/fondo/r1/ticks.txt` |
| Fondo, cada gestor | IC 25 siempre; 100 ciclos | idem |
| Fondo, los cuatro hilos | IC 143,59 por tick; CPI agregado 1,000 | idem |
| Operaciones útiles por tick | `max_media` 8; fondo 56 | decisión T100 |
| MOPS logrado del kernel | R0 3,92; segmentado 7,41; barrel un hilo 2,08; barrel con extensión 4,17; R1 5,34 | `docs/mediciones/p7/variantes.txt` |
| Ppeak | Base 12,5 MOPS; segmentado 25; barrel 25 con 4 hilos y 6,25 con uno | `docs/mediciones/barrel/cpi.txt` |
| Speedup de la respuesta contra R0 | Segmentado 1,86; barrel un hilo 0,55; con extensión 0,75; R1 0,18 | `docs/mediciones/p7/variantes.txt` |
| Speedup en MOPS contra R0 | Segmentado 1,89; R1 1,36 | idem |
| Amdahl en el segmentado | Predicho 1,843, medido 1,864 (con la estimación de la clase, 1,745) | `docs/estado.md`, P7 |
| Roofline | Quiebre 0,125 Op/B; el kernel está entre 0,6 y 1 Op/B: limitado por cómputo | `docs/codiseno.md`, sección 1 |
| Parte del tick a 0,1 ms que es sondeo | 98 % | `docs/codiseno.md`, sección 1 |

## Patrimonio

| Cifra | Valor | Fuente |
|-------|-------|--------|
| Serie completa de práctica, viendo todos los precios | No operar 10 000; comprar y mantener 6 497; regla base 27 062 (388 órdenes); `max_media` 25 973 (624 órdenes, 3 120 de comisiones) | `docs/mediciones/tabla_3_1.txt` |
| Testbench oficial por defecto (2000 ticks, 0,1 ms) | `max_media` 9 661 (74 órdenes); comprar y mantener 6 695; regla base 9 617 | `docs/mediciones/tabla_3_1.txt` |
| Testbench con los 20 000 ticks, `max_media` | 26 070 (R0, a los tres períodos) | decisión T51 |
| Fondo en el testbench con los 20 000 ticks | 26 070 a 0,1 ms; 25 031 a 1 ms y 10 ms | `docs/fondo.md`, sección 7 |
| `max_media` contra la regla base, semilla reservada | +0,7 % en remuestreos (10 833 contra 10 754); +1,4 % en plausibles (11 103 contra 10 954) | `docs/algoritmo.md`, sección 7.2 |
| `max_media` supera a comprar y mantener | 71 % de los remuestreos, 64 % de las plausibles | idem |
| Fondo contra `max_media`, puntos esperados del torneo (factibilidad) | +0,007 a 2 000 ticks; -0,005 a 20 000 | decisión T50 |
| Fondo contra `max_media` en bytes | Práctica: los mismos 20 000. Una serie de reversión: 1816 bytes distintos | `docs/estado.md`, tramo 10; `docs/fondo.md`, sección 10 |
| Techo del modelo (política óptima) | 8,4 % por ronda; la regla base saca 5,2 % en el modelo | `docs/algoritmo.md`, sección 4 |
| Dispersión con la misma regla, remuestreos | 6 520 a 15 637 | `docs/protocolo.md`, sección 8 |

## Serie de práctica

| Cifra | Valor | Fuente |
|-------|-------|--------|
| Razón de varianza a 10, 50 y 100 ticks | 0,77, 0,62 y 0,53; menor que 1 en los 20 bloques | `docs/estado.md`, tramo 1 |
| Autocorrelación de los cambios, rezago 1 | -0,112 | idem |
| VR(100) de un paseo aleatorio redondeado | 0,77: la mitad de la reversión es redondeo | `docs/mediciones/generador_redondeo.txt` |
| Vida media de la transitoria | 17,5 ticks (phi = 0,961) | `docs/algoritmo.md`, sección 2.2 |

## Operación y contingencia

| Cifra | Valor | Fuente |
|-------|-------|--------|
| SCLK mínimo a 0,1 ms | R0 100 kHz; R1 110 kHz; el árbol usa 115 kHz | `docs/mediciones/fondo/r1/sclk_minimo.txt`, T124 |
| Período mínimo con SCLK de 1 MHz | R0 11,34 us (8,82 veces la ronda 3); R1 26,94 us (3,71 veces) | `docs/mediciones/fondo/r1/sclk_minimo.txt` |
| SCLK máximo que funciona | 4 MHz; a 5 MHz el esclavo pierde bits en todos los diseños | decisión T53 |
| Vigilante | Dispara al 5.º precio seguido sin escritura (K = 4); cuenta máxima en corridas sanas: 1 | `docs/tabla_vigilante.md`, secciones 4 y 7 |
| Reconfiguración por warm boot | 53 ms de la hoja de datos, **sin medir**: 536 ticks sin decisión nueva a 0,1 ms, 58 a 1 ms, 10 a 10 ms | `docs/mediciones/vigilante/relevo.txt` |
| Cambio de tabla con `icebram` | 0,32 s; R0 desde su molde 0,10 s; simular el `.asc` nuevo unos 40 minutos | `docs/tabla_vigilante.md`, sección 3; `docs/mediciones/p8/r0_molde.txt` |
| Imagen múltiple | 64 600 de 131 072 bytes de la flash | `docs/tabla_vigilante.md`, sección 6 |
| Tamaño de `sw/fondo.s` | 213 de 512 palabras; `sw/trade.s` 40 | `docs/mediciones/fondo/r1/tamano.txt`, `docs/trade_s.md` |
| Reset de encendido | 4095 ciclos, 164 us | `rtl/pochoco_soc.v:114` |

## Verificación

| Cifra | Valor | Fuente |
|-------|-------|--------|
| Core de R1 y R2 contra el Espino base | 7 974 963 instrucciones, 92,80 % distintas, cero diferencias | `docs/puertas.md`, criterio 5 |
| Mutaciones detectadas | Barrel 21/21; extensión 9/9; segmentado 5/5; fondo 15/15; vigilante 4/4 | `docs/defensa/verificacion.md`, sección 7 |
| Series del fondo idénticas a la referencia | 1 050 por el RTL; 1 051 a los tres períodos en el gemelo (6,36 millones de ticks) | `docs/puertas.md` |
| Gemelo contra RTL | Base: 8 configuraciones; barrel: 21 configuraciones y 18,3 millones de eventos | `docs/gemelo.md` |
| Gemelo contra Verilator, 20 000 ticks a 10 ms | R0: 0,02 s contra 22 min; fondo: 0,14 s contra 35 min | `docs/gemelo.md:25` y `:197` |
| Degradación | 30 de 30 corridas, peor caso 679 ciclos | `docs/mediciones/fondo/r1/degradacion.txt` |
| Matriz de estrés de la puerta | R0 60 de 60; R1 y R2 56 de 56 | `docs/puertas.md` |
