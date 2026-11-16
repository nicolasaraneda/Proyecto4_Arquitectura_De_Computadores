# Juegos de contingencia: otra comisión anunciada el día de la competencia

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Bitstreams ya construidos y simulados para el caso en que el 1/12 anuncien una comisión distinta de 5 (`docs/arbol_decision.md`, sección 2). Los hace `make contingencia` (`tools/p8/contingencia.sh`), que llama a `tools/retune.py --simular` para cada combinación: los umbrales de `max_media` se eligen con el protocolo, los bitstreams salen de `icebram` sobre los moldes de `bitstreams/moldes/` (sin sintetizar, el mismo hardware que pasó las puertas), y cada `.asc` se simula por los pines contra la referencia con los parámetros nuevos. `RESUMEN.txt` de cada carpeta tiene la búsqueda, las comprobaciones y los hashes.

| Carpeta | Umbrales (entra, sale) | Para | Comprobaciones |
|---------|------------------------|------|----------------|
| `e7_s4/` | (7, 4) | Comisión 20, caja 10 000 | 10 en el gemelo y 3 `.asc` por los pines |
| `e16_s4/` | (16, 4) | Comisión 20 con caja 1 000; comisión 50 con caja 1 000 o 10 000 | Igual |
| `e16_s3/` | (16, 3) | Comisión 50, caja 100 000 | Igual |

Con comisión de 0 a 10 (y con 20 y caja de 100 000) no hay que cambiar nada: `retune` deja los umbrales actuales.

Cada carpeta trae `r0.bin` (R0), `r1.bin` (R1) y `r2_multi.bin` (R2 con su R0 de respaldo), más la tabla y el programa que se pusieron con `icebram`. Antes de grabar: `cd bitstreams/contingencia/e7_s4 && sha256sum -c SHA256SUMS`. Se graba igual que los de `bitstreams/`, por ejemplo `iceprog bitstreams/contingencia/e7_s4/r1.bin`; `r2_multi.bin` con `iceprog -b`.

Estos bitstreams no pasaron por la maestra real. Su hardware sí (es el de R0, R1 y R2); lo que cambia es el contenido de dos BRAM.
