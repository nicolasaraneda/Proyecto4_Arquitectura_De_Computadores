# Árbol de decisión: qué se graba el 1/12

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Una página. Se recorre de arriba abajo, y la primera regla que se cumple decide. Cada cifra sale de un archivo del repositorio, citado al final.

## 1. Qué peldaño compite

| # | Si... | Entonces | Por qué |
|---|-------|----------|---------|
| 1 | (Resuelta el 16/11.) El profesor confirmó que se puede modificar lo que uno quiera y que el Espino multihilo es válido (T126) | No lleva a R0 | El barrel puede competir. Antes, un no del ayudante llevaba a R0 |
| 2 | R1 no pasó la puerta de maestra el 26/11 (perdió precios o decisiones, o el patrimonio no coincide con el gemelo) | **R0** | Solo compite hardware probado con la maestra real |
| 3 | En la ronda 3 el SCLK real es **menor que 115 kHz** (medidor, medida 0: valor mayor que 217, `0x00D9`) | **R0** | Con 100 kHz quedan 237 ciclos y R1 necesita hasta 444. R1 responde a tiempo desde 110 kHz; 115 deja margen. R0 responde en 44 ciclos |
| 4 | El período real de la ronda 3 es menor que 27 us | **R0** | Período mínimo con SCLK de 1 MHz: R1 26,94 us, R0 11,34 us |
| 5 | R2 pasó la puerta de placa (relevo al inyectar la falla, ninguno en media hora) y la de maestra, y nadie del curso prohibió de forma explícita reconfigurar la FPGA durante una ronda | **R2** (`r2_multi.bin`) | El vigilante cambia a R0 si R2 deja de responder 5 precios seguidos. Reconfigurar está cubierto por la respuesta general del profesor, sin confirmación específica (T126) |
| 6 | En cualquier otro caso | **R1** (`r1_fondo.bin`) | Es el diseño elegido (decisión T50) |

R0 es el respaldo de toda la escalera y no depende de ninguna respuesta del curso. Ninguna regla depende ya de una respuesta pendiente: la regla 1 la resolvió el profesor y la 5 solo cambia ante una prohibición explícita.

## 2. Si cambian las reglas el mismo día

| Si cambia... | Hacer | Tiempo |
|--------------|-------|--------|
| Nada, o el largo de las rondas, o la caja con comisión de 10 o menos | Nada. Las decisiones no dependen de la caja ni del largo, y `retune` deja los umbrales actuales en todas esas combinaciones | 0 |
| Comisión de 20 o más | Usar el juego ya construido de `bitstreams/contingencia/` que corresponda (tabla de abajo). Si la combinación no está, `python3 tools/retune.py --comision C --caja K --simular` | 0, o 45 min |
| SCLK mayor que 1 MHz | Hasta 4 MHz los tres peldaños responden igual. A 5 MHz el esclavo SPI del curso pierde bits en todos los diseños: avisar al ayudante | 0 |
| Período entre 27 us y 0,1 ms | Ninguno: R1 cabe | 0 |

Juegos de contingencia (umbrales de `max_media` que elige `retune`; los gestores 2 y 3 se corren igual):

| Comisión | Caja 1 000 | Caja 10 000 | Caja 100 000 |
|----------|------------|-------------|--------------|
| 0 a 10 | actuales (3, 0) | actuales (3, 0) | actuales (3, 0) |
| 20 | (16, 4) | (7, 4) | actuales (3, 0) |
| 50 | (16, 4) | (16, 4) | (16, 3) |

(16, 4) casi no opera: con comisión alta lo que más rinde es no pagarla.

## 3. Durante la ronda

| Se ve | Hacer |
|-------|-------|
| El LED de latido (R1 y R2) no cambia o los 7 segmentos quedan fijos varios segundos con precios llegando | Si es R2, esperar 0,1 s: el vigilante cambia solo a R0. Si es R1, no tocar durante la ronda; entre rondas, grabar R0 |
| La maestra muestra a nuestro grupo sin operar desde el comienzo | Revisar tierra común y el cable de MISO (PMOD 3). Grabar de nuevo el mismo bitstream |
| `iceprog` no encuentra la placa | `usbipd attach --wsl --busid X-Y` en PowerShell (`docs/autoprueba.md`, sección 5) |

## Fuentes

- SCLK mínimo y período mínimo: `docs/mediciones/fondo/r1/sclk_minimo.txt` (`make fondo-sclk-minimo`).
- Celdas por SCLK y período: `docs/mediciones/p8/matriz.txt` (`make p8-matriz`), `docs/mediciones/fondo/r1/estres.txt` y `docs/mediciones/estres_base.txt`.
- Juegos de contingencia: `tools/retune.py`, `bitstreams/contingencia/LEEME.md`.
- Medidor del SCLK: `docs/mediciones/medidor_spi.txt` (`make medidor`) y `docs/checklist_26nov.md`.
- Decisión sobre SCLK de 100 kHz a 0,1 ms: opción (a) de Nicolás, límite documentado de R1 (`docs/estado.md`, tramo 13).
