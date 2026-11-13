# Bitstreams de competencia

Cada bitstream que puede llegar a la placa queda aquí con su hash, el commit del que salió y las pruebas que pasó. `SHA256SUMS` se comprueba con `sha256sum -c SHA256SUMS` desde esta carpeta.

Regla del proyecto: el bitstream de la competencia solo puede contener hardware que haya pasado por la maestra real el 19/11.

| Archivo | Hardware | Programa | Celdas | BRAM | Frecuencia máxima | Pruebas en simulación | Maestra real |
|---------|----------|----------|--------|------|-------------------|-----------------------|--------------|
| `competencia_v1.bin` | Repositorio base más reset de 4095 ciclos. Sin hardware agregado. | Regla base, solo software (`sw/trade.s`, 40 palabras). | 1083 de 1280 (84 %) | 12 de 16 | 44,0 MHz | Testbench oficial 4/4. `make equiv`: 20 000 ticks idénticos a la referencia. `make sim-bitstream`: el bitstream simulado decide igual que la referencia en 2000 ticks. | Pendiente (19/11) |

Cómo se generó `competencia_v1.bin`:

```bash
make bin                                        # yosys, nextpnr (semilla por defecto) e icepack
make sim-bitstream                              # simula el .asc y lo compara con la referencia
make guardar-bitstream NOMBRE=competencia_v1    # copia el .bin y actualiza SHA256SUMS
```

Herramientas: OSS CAD Suite del 2026-09-06 (Yosys 0.68+195, nextpnr 0.11.1-19-g8dbcee5c). Con las mismas versiones `make bin` vuelve a producir un archivo con el mismo hash.
