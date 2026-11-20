# Árbol de decisión: qué se graba el 1/12

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Una página. Se recorre de arriba abajo, y la primera regla que se cumple decide. Cada cifra sale de un archivo del repositorio, citado al final.

Desde el 19/11 los tres peldaños corren la regla de cotas con banda 40 (T140): `r0_banda40.bin`, `r1_banda40.bin` y `r2_banda40_multi.bin`. Los límites de las reglas 3 y 4 (115 kHz y 27 µs) se fijaron con el fondo que votaba, cuando R1 respondía en hasta 444 ciclos; con la regla de cotas R1 responde en 128 y R0 en 60, así que esos límites quedan conservadores. Se mantienen mientras Nicolás no decida otros (`docs/pendientes_nicolas.md`). La tabla de la sección 2 se calculó para `max_media` y no se ha rehecho para la regla de cotas: también queda pendiente.

## 1. Qué peldaño compite

| # | Si... | Entonces | Por qué |
|---|-------|----------|---------|
| 1 | (Resuelta el 16/11.) El profesor confirmó que se puede modificar lo que uno quiera y que el Espino multihilo es válido (T126) | No lleva a R0 | El barrel puede competir. Antes, un no del ayudante llevaba a R0 |
| 2 | R1 no pasó la puerta de maestra el 26/11 (perdió precios o decisiones, o el patrimonio no coincide con el gemelo) | **R0** | Solo compite hardware probado con la maestra real |
| 3 | En la ronda 3 el SCLK real es **menor que 115 kHz** (medidor, medida 0: valor mayor que 217, `0x00D9`) | **R0** | Con 100 kHz quedan 237 ciclos y R1 necesita hasta 444. R1 responde a tiempo desde 110 kHz; 115 deja margen. R0 responde en 44 ciclos |
| 4 | El período real de la ronda 3 es menor que 27 µs | **R0** | Período mínimo con SCLK de 1 MHz: R1 26,94 µs, R0 11,34 µs |
| 5 | R2 pasó la puerta de placa (relevo al inyectar la falla, ninguno en media hora) y la de maestra, y nadie del curso prohibió de forma explícita reconfigurar la FPGA durante una ronda | **R2** (`r2_banda40_multi.bin`, con `iceprog -b`) | El vigilante cambia a R0 si R2 deja de responder 5 precios seguidos: 361 ticks sin decisión nueva a 0,1 ms con los 35,50 ms de reconfiguración medidos el 16/11. Reconfigurar está cubierto por la respuesta general del profesor, sin confirmación específica (T126). Estado al 16/11: media hora sin disparo y firma a 0,1 ms en la placa; faltan la firma a 1 y 10 ms y ver la testigo después del relevo (`docs/puertas.md`, puerta de placa) |
| 6 | En cualquier otro caso | **R1** (`r1_banda40.bin`) | Es el diseño elegido (decisión T50) |

R0 es el respaldo de toda la escalera y no depende de ninguna respuesta del curso. Ninguna regla depende ya de una respuesta pendiente: la regla 1 la resolvió el profesor y la 5 solo cambia ante una prohibición explícita.

## 2. Si cambian las reglas el mismo día

| Si cambia... | Hacer | Tiempo |
|--------------|-------|--------|
| Nada, o el largo de las rondas, o la comisión con 8 o menos | Nada. Las decisiones no dependen del largo, y `retune` deja los umbrales actuales con cualquier caja | 0 |
| La comisión (más de 8) o la caja | Buscar la celda en la tabla de abajo y usar ese juego de `bitstreams/contingencia/` ("actuales": no cambiar nada). Si la combinación no está en la tabla, `python3 tools/retune.py --comision C --caja K --simular` | 0, o 45 min |
| SCLK mayor que 1 MHz | Hasta 4 MHz los tres peldaños responden igual. A 5 MHz el esclavo SPI del curso pierde bits en todos los diseños: avisar al ayudante | 0 |
| Período entre 27 µs y 0,1 ms | Ninguno: R1 cabe | 0 |

Juego que corresponde a cada comisión y caja (umbrales de `max_media` que elige `retune`, "entra" y "sale"; los gestores 2 y 3 se corren igual). Cada juego trae R0, R1 y R2 simulados por los pines y su `SHA256SUMS` (`bitstreams/contingencia/LEEME.md`). Si la comisión o la caja no están en la tabla, correr `retune --simular` con los valores exactos y, mientras termina, usar la celda más cercana.

| Comisión | Caja 1 000 | Caja 2 000 | Caja 5 000 | Caja 10 000 | Caja 20 000 | Caja 50 000 | Caja 100 000 |
|---|---|---|---|---|---|---|---|
| 0 | actuales | actuales | actuales | actuales | actuales | actuales | actuales |
| 2 | actuales | actuales | actuales | actuales | actuales | actuales | actuales |
| 5 | actuales | actuales | actuales | actuales | actuales | actuales | actuales |
| 8 | actuales | actuales | actuales | actuales | actuales | actuales | actuales |
| 10 | actuales | `e3_s1` | actuales | actuales | actuales | actuales | actuales |
| 12 | `e16_s4` | `e3_s1` | actuales | actuales | actuales | actuales | actuales |
| 15 | `e16_s4` | `e3_s2` | actuales | `e4_s1` | actuales | actuales | actuales |
| 20 | `e16_s4` | `e16_s4` | `e7_s3` | `e7_s4` | `e10_s4` | `e7_s3` | actuales |
| 25 | `e16_s4` | `e16_s4` | `e3_s1` | `e7_s4` | `e7_s4` | `e7_s3` | `e7_s3` |
| 30 | `e16_s4` | `e16_s4` | `e10_s4` | `e7_s4` | `e7_s4` | `e7_s3` | `e7_s3` |
| 40 | `e16_s4` | `e16_s4` | `e16_s4` | `e16_s4` | `e16_s3` | `e7_s3` | `e7_s3` |
| 50 | `e16_s4` | `e16_s4` | `e16_s4` | `e16_s4` | `e16_s3` | `e16_s3` | `e16_s3` |
| 75 | `e16_s4` | `e16_s4` | `e16_s4` | `e16_s4` | `e16_s4` | `e16_s3` | `e16_s3` |
| 100 | `e63_s-1` (no construido) | `e16_s4` | `e16_s4` | `e16_s4` | `e16_s4` | `e16_s3` | `e16_s3` |

- `e16_s4` y `e16_s3` casi no operan: con comisión alta lo que más rinde es no pagarla.
- Comisión 100 con caja 1 000: `retune` elige no operar nunca (63, -1). No se construyó: con esa caja una sola compra cuesta el 10 % y el resultado es mantener la caja. Si pasa, competir con `e16_s4`, que opera casi nunca.
- La tabla sale de `make contingencia-grilla` (`docs/mediciones/p8/retune_grilla.txt`).

## 3. Durante la ronda

| Se ve | Hacer |
|-------|-------|
| Antes de la primera ronda, con la maestra recién conectada | Desconectar y conectar el USB de la Go Board: los pines del SPI no tienen pull-up y la FPGA debe partir de cero con la maestra ya fijando el nivel de las líneas |
| El LED de latido (R1 y R2) no cambia o los 7 segmentos quedan fijos varios segundos con precios llegando | Si es R2, esperar 0,1 s: el vigilante cambia solo a R0. Si es R1, no tocar durante la ronda; entre rondas, grabar R0 |
| La maestra muestra a nuestro grupo sin operar desde el comienzo | Revisar tierra común y el cable de MISO (PMOD 3). Grabar de nuevo el mismo bitstream |
| `iceprog` no encuentra la placa | `usbipd attach --wsl --busid X-Y` en PowerShell (`docs/autoprueba.md`, sección 5) |

## Fuentes

- SCLK mínimo y período mínimo: `docs/mediciones/fondo/r1/sclk_minimo.txt` (`make fondo-sclk-minimo`).
- Celdas por SCLK y período: `docs/mediciones/p8/matriz.txt` (`make p8-matriz`), `docs/mediciones/fondo/r1/estres.txt` y `docs/mediciones/estres_base.txt`.
- Juegos de contingencia: `tools/retune.py`, `bitstreams/contingencia/LEEME.md`.
- Relevo medido en la placa (35,50 ms) y puerta de placa: `docs/mediciones/placa_16nov.md`, `docs/puertas.md`.
- Medidor del SCLK: `docs/mediciones/medidor_spi.txt` (`make medidor`) y `docs/checklist_26nov.md`.
- Decisión sobre SCLK de 100 kHz a 0,1 ms: opción (a) de Nicolás, límite documentado de R1 (`docs/estado.md`, tramo 13).
