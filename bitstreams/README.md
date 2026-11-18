# Bitstreams de competencia

Cada bitstream que puede llegar a la placa queda aquí con su hash, el commit del que salió y las pruebas que pasó. `SHA256SUMS` se comprueba con `sha256sum -c SHA256SUMS` desde esta carpeta.

Los dos primeros usan la regla base, que `trade.s` corrió hasta el 15/11. Desde entonces `make bin` construye el diseño de R0, pero no el mismo archivo byte por byte: los cambios de `rtl/*.v` de P5 movieron la ubicación. El archivo que vale es el guardado aquí, el que pasó las puertas; `make r0-reproducir` lo reconstruye igual desde su commit.

Regla del proyecto: el bitstream de la competencia solo puede contener hardware que haya pasado por la maestra real el 26/11.

| Archivo | Hardware | Programa | Celdas | BRAM | Frecuencia máxima | Pruebas en simulación | Maestra real |
|---------|----------|----------|--------|------|-------------------|-----------------------|--------------|
| `competencia_v1.bin` | Repositorio base más reset de 4095 ciclos. Sin hardware agregado. | Regla base, solo software (`sw/trade.s`, 40 palabras). | 1083 de 1280 (84 %) | 12 de 16 | 44,0 MHz | Testbench oficial 4/4. `make equiv`: 20 000 ticks idénticos a la referencia. `make sim-bitstream`: el bitstream simulado decide igual que la referencia en 2000 ticks. | Pendiente (26/11) |
| `r0_base_max_media.bin` | **R0, el respaldo de la escalera (T50, T54).** El mismo hardware que `competencia_v1.bin`: repositorio base más reset de 4095 ciclos. | `max_media`, solo software (`sw/trade.s`, 40 palabras). | 1083 de 1280 (84 %) | 12 de 16 | 44,6 MHz (semilla por defecto). 10 de 10 semillas cierran, mínima 42,43 MHz | Puerta de simulación completa (`docs/puertas.md`): testbench oficial 4/4, equivalencia en los tres períodos y 3810 series, 8 fases del sondeo, matriz de estrés y `make sim-bitstream` (2000 ticks del `.asc` idénticos a la referencia, patrimonio 9 661). | Pendiente (26/11) |
| `segmentado_v1.bin` | El mismo SoC con el Espino segmentado (pipeline de 3 etapas, `-DESPINO_SEGMENTADO`). No es la edición de competencia. | Regla base, el mismo `sw/trade.hex`. | 994 de 1280 (78 %) | 12 de 16 | 52,1 MHz | `make check-seg`, `make equiv-seg`, `make cosim-seg`, `make paralelo-largo` y `make mutaciones`. `make sim-bitstream-seg`: el bitstream simulado decide igual que la referencia en 2000 ticks. | Pendiente (26/11) |
| `r1_fondo.bin` | **R1.** Espino barrel con `emad`, `devk` y la tabla de parámetros (`-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA`). | `sw/fondo.s` (200 palabras) y `sw/fondo_tabla.hex`. | 1029 de 1280 (80 %) | 13 de 16 | 52,4 MHz (semilla 1). 10 de 10 semillas cierran, mínima 51,59 MHz | Puerta de simulación completa (`docs/puertas.md`). Simulado desde el `.asc`: 2000 ticks idénticos a `ref/fondo.py` en dos series. | Pendiente (26/11) |
| `r2_fondo_vigilante.bin` | **R2, una sola imagen.** R1 más el vigilante y `SB_WARMBOOT` (`-DESPINO_VIGILANTE`). Sola no sirve para competir: el relevo necesita la imagen de respaldo. | Los mismos. | 1045 de 1280 (82 %) | 13 de 16 | 52,5 MHz (semilla 1). 10 de 10, mínima 47,86 MHz | Puerta de simulación completa. Desde el `.asc`: 2000 ticks idénticos en dos series sin disparo, y disparo correcto con el supervisor colgado. | Pendiente (26/11) |
| `r2_multi.bin` | **R2 para grabar.** Imagen múltiple de `icemulti`: imagen 0 `r2_fondo_vigilante.bin`, imagen 1 `r0_base_max_media.bin`. 64 600 bytes de los 131 072 de la flash. | | | | | `tools/ver_multi.py`: vectores de arranque correctos y las dos imágenes copiadas sin cambios. | Pendiente (26/11) |
| `r2_falla_multi.bin` | **R2 con la falla inyectada, no es de competencia (P8).** Imagen 0: R2 con el programa del supervisor colgado en el tick 100 (`tools/fondo/variante.py cuelgue_sup:100`), puesto con `icebram` sobre el molde de R2; imagen 1: R0. Para ver el relevo con la maestra real el 26/11. | `sw/fondo.s` con la falla, y R0 | Las de R2 y R0 | | | `make r2-falla`: el `.asc` es byte por byte el que `make fondo-bitstreams` simuló por los pines (BOOT con `S1 S0 = 01` al terminar la transacción 105, `docs/mediciones/fondo/bitstreams.txt`, paso 5); `tools/ver_multi.py` correcto. Se graba con `iceprog -b`. | Se usa el 26/11 |
| `autoprueba_r0.bin` | **Autoprueba de R0, no es de competencia (P6, T83 a T85).** El SoC de R0 sin cambios más una maestra SPI interna, con la firma esperada adentro. Botones SW1 a SW3 eligen 10 ms, 1 ms y 0,1 ms. | `sw/trade.s` (`max_media`), el mismo de R0. | 1269 de 1280 (99 %) | 12 de 16 | 44,05 MHz | `make autoprueba-r0` (`docs/mediciones/autoprueba_r0.txt`): firma `a23c` igual en el gemelo a los tres períodos y en la referencia; RTL por los pines con los tres botones; bitstream ruteado con SW3; control negativo con LED4. Cómo usarlo: `docs/autoprueba.md`, sección 5. | No aplica: es la puerta de placa |
| `medidor_spi.bin` | **Medidor de la maestra, no es de competencia (P8, T120).** Sin el SoC: escucha `SCLK`, `MOSI` y `CS_n` y muestra en los 7 segmentos el período de SCLK, el período entre precios, la duración de `CS_n`, el tiempo libre mínimo y la cantidad de transacciones. Responde `0x00` por MISO. | No tiene. | 627 de 1280 (49 %) | 0 de 16 | 10 de 10 semillas, mínima 112,52 MHz | `make medidor` (`docs/mediciones/medidor_spi.txt`): testbench con 70 comprobaciones por los botones y los 7 segmentos, 6 de 6 errores puestos a propósito detectados, y el mismo testbench sobre el bitstream ruteado. Uso: `docs/checklist_26nov.md`, sección 3. | Se usa el 26/11 |
| `autoprueba_r1.bin` | **Autoprueba de R1, no es de competencia (P6, T87 y T88).** El SoC de R1 sin cambios (`-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA`) más la maestra SPI interna, con la caminata de semilla 0x3CA1 y la firma esperada adentro. | `sw/fondo.s` y `sw/fondo_tabla.hex`, los mismos de R1. | 1191 de 1280 (93 %) | 13 de 16 | 50,81 MHz | `make autoprueba-r1` (`docs/mediciones/autoprueba_r1.txt`): firma `15d7` igual en el gemelo a los tres períodos y en `ref/fondo.py`; RTL por los pines con los tres botones; bitstream ruteado con SW3; control negativo con otra tabla (`6f2a`, LED4). Cómo usarlo: `docs/autoprueba.md`, sección 9.2. | No aplica: es la puerta de placa |
| `autoprueba_r2_multi.bin` | **Autoprueba de R2, no es de competencia (P6, T89 y T90).** Imagen múltiple: imagen 0 la autoprueba de R2 (R1 más el vigilante) con la maestra en modo continuo, imagen 1 la testigo (cuatro LED y "--"). | Los de R1. | 1203 de 1280 (94 %) (testigo: 83) | 13 de 16 | 50,96 MHz | `make autoprueba-r2` (`docs/mediciones/autoprueba_r2.txt`): firma `15d7`; RTL con los tres botones y 2 s más en modo continuo sin disparo; bitstream ruteado con SW3 sin disparo; media hora de la caminata en el gemelo; `tools/ver_multi.py`. Cómo usarlo: `docs/autoprueba.md`, sección 9.3. Se graba con `iceprog -b`. | No aplica |
| `relevo_r2_multi.bin` | **Prueba del relevo de R2, no es de competencia (P6, T91 y T92).** Imagen múltiple: imagen 0 la autoprueba de R2 con el supervisor colgado en el tick 100, imagen 1 la testigo. Las dos hacen eco de la UART y dejan MISO del PMOD en 0, para medir el relevo. | `cuelgue_sup:100` de `tools/fondo/variante.py` sobre `sw/fondo.s`. | Las mismas de la autoprueba de R2 | 13 de 16 | | RTL y bitstream ruteado: BOOT sube con S1 S0 = 01 al terminar la transacción 103, la quinta sin respuesta. Cómo usarlo: `docs/autoprueba.md`, secciones 9.4 y 10. Se graba con `iceprog -b`. | No aplica |
| `relevo_r2_multi_sin_dormir.bin` | Lo mismo que `relevo_r2_multi.bin`, empaquetado con `icepack -s` (sin la orden de dormir la flash). Solo si con el anterior el relevo no termina (T91). | | | | | `tools/ver_multi.py` | No aplica |

Cómo se generó `competencia_v1.bin`:

```bash
make bin                                        # yosys, nextpnr (semilla por defecto) e icepack
make sim-bitstream                              # simula el .asc y lo compara con la referencia
make guardar-bitstream NOMBRE=competencia_v1    # copia el .bin y actualiza SHA256SUMS
```

Cómo se generó `r0_base_max_media.bin` (15/11, paquete P0):

```bash
make bin                                          # yosys, nextpnr (semilla por defecto) e icepack
make sim-bitstream                                # simula el .asc y lo compara con ref/trader.py (max_media)
make guardar-bitstream NOMBRE=r0_base_max_media   # copia el .bin y actualiza SHA256SUMS
```

Cómo se generó `segmentado_v1.bin`:

```bash
make bin-seg                 # yosys con -DESPINO_SEGMENTADO, nextpnr (semilla por defecto) e icepack
make sim-bitstream-seg       # simula el .asc y lo compara con la referencia
cp build/pochoco_soc_seg.bin bitstreams/segmentado_v1.bin
```

Herramientas: OSS CAD Suite del 2026-09-06 (Yosys 0.68+195, nextpnr 0.11.1-19-g8dbcee5c).

`competencia_v1.bin` se generó en el commit `7138393`. Desde que el core segmentado comparte archivos con el base, `make bin` produce un bitstream con la misma lógica (1083 celdas, `make formal-base`, `make cosim`) pero con otra ubicación, porque cambiaron nombres internos, y por lo tanto con otro hash. El archivo de esta carpeta es el que se construyó y se simuló entonces, y no se ha vuelto a generar. Para reproducir su hash hay que construir desde ese commit.

`r0_base_max_media.bin` se generó en el commit `1d4a82f` y le pasa lo mismo desde que entraron el barrel y la extensión de la ISA: `make bin` en un commit posterior da la misma lógica con otra ubicación y otro hash. Para no depender de volver a ese commit a mano, `make r0-reproducir` extrae sus fuentes con `git archive`, las construye en `build/r0/` y compara el resultado con el archivo guardado y con `SHA256SUMS`. Corre en la integración continua, así que el hash también se comprueba en una máquina que no es la nuestra.

Cómo se generaron `r1_fondo.bin`, `r2_fondo_vigilante.bin`, `r2_multi.bin` y `moldes/` (15/11, paquete P5):

```bash
GUARDAR=1 tools/fondo/bitstreams.sh   # yosys, nextpnr (semilla 1), icepack, simulación desde el .asc, icebram e icemulti
```

`moldes/` tiene lo que `icebram` necesita para cambiar la tabla de parámetros o el programa de R1 o de R2 sin sintetizar: el `.asc` de cada peldaño con las dos memorias llenas de un patrón al azar (comprimido con gzip) y los dos patrones. El molde con `icebram` da el mismo `.asc`, byte por byte, que la síntesis directa. Sobre un bitstream con la tabla de verdad `icebram` no puede trabajar, porque no logra ubicarla. El procedimiento está en `docs/tabla_vigilante.md`, sección 3.

Estos tres bitstreams se construyeron en el commit de cierre de P5. Como le pasó a R0, un commit posterior que agregue archivos a `rtl/` puede dar otra ubicación y otro hash: lo que vale es el archivo guardado y sus moldes.

Cómo se generaron `autoprueba_r1.bin`, `autoprueba_r2_multi.bin`, `relevo_r2_multi.bin` y `relevo_r2_multi_sin_dormir.bin` (16/11, paquete P6 para R1 y R2):

```bash
make autoprueba-r1    # build/autoprueba/r1/autoprueba_r1.bin
make autoprueba-r2    # build/autoprueba/r2/: autoprueba_r2_multi.bin, relevo_r2_multi.bin y relevo_r2_multi_sin_dormir.bin
```

Se copiaron a esta carpeta con su nombre y `SHA256SUMS` se rehízo con `sha256sum *.bin moldes/*`. Los tres archivos de R2 tienen dos imágenes y ocupan 64 600 bytes: se graban con `iceprog -b`, igual que `r2_multi.bin`.

`registrador.bin` (17/11) no es un peldaño: escucha el SPI de la maestra, responde siempre mantener y manda cada precio por la UART, para registrar la serie del 26/11 (`docs/registrador.md`). 478 celdas, ninguna BRAM, 10 de 10 semillas (`make registrador`).

`registrador_921k.bin` (17/11) es el mismo registrador a 926 kbaud (`CICLOS_BIT = 27`), por si el conversor USB del computador no acepta 1 Mbaud. Se lee con `python3 tools/registrador.py /dev/ttyUSB1 --baudios 921600 -o ...` (0,47 % de diferencia, dentro de lo que tolera una UART). Su bitstream ruteado pasa las mismas pruebas por los pines (`make registrador`, paso 5b).
