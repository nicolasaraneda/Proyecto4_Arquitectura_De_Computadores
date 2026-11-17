# Juegos de contingencia: otra comisión anunciada el día de la competencia

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Bitstreams ya construidos y simulados para el caso en que el 1/12 anuncien una comisión distinta de 5 (`docs/arbol_decision.md`, sección 2). Los hace `make contingencia` (`tools/p8/contingencia.sh`), que llama a `tools/retune.py --simular` para cada combinación: los umbrales de `max_media` se eligen con el protocolo, los bitstreams salen de `icebram` sobre los moldes de `bitstreams/moldes/` (sin sintetizar, el mismo hardware que pasó las puertas), y cada `.asc` se simula por los pines contra la referencia con los parámetros nuevos. `RESUMEN.txt` de cada carpeta tiene la búsqueda, las comprobaciones y los hashes.

| Carpeta | Umbrales (entra, sale) | Para | Comprobaciones |
|---------|------------------------|------|----------------|
| `e7_s4/` | (7, 4) | Comisión 20, caja 10 000 | 10 en el gemelo y 3 `.asc` por los pines |
| `e16_s4/` | (16, 4) | Comisión 20 con caja 1 000; comisión 50 con caja 1 000 o 10 000 | Igual |
| `e16_s3/` | (16, 3) | Comisión 50, caja 100 000 | Igual |
| `e7_s3/` | (7, 3) | Comisión 20 con caja 5 000 o 50 000; comisión 25 a 40 con caja de 50 000 o más | Igual (17/11) |
| `e10_s4/` | (10, 4) | Comisión 20 con caja 20 000; comisión 30 con caja 5 000 | Igual (17/11) |
| `e4_s1/` | (4, 1) | Comisión 15, caja 10 000 | Igual (17/11) |
| `e3_s1/` | (3, 1) | Comisión 10 o 12 con caja 2 000; comisión 25 con caja 5 000 | Igual (17/11) |
| `e3_s2/` | (3, 2) | Comisión 15, caja 2 000 | Igual (17/11) |

La tabla completa de comisión y caja, con el juego que corresponde a cada caso, está en `docs/mediciones/p8/retune_grilla.txt` (`make contingencia-grilla`) y en el árbol de decisión. Con comisión de 0 a 8, y con casi todas las cajas hasta 12, no hay que cambiar nada. Los juegos del 17/11 se construyeron con `JUEGOS=... PARALELO=1 tools/p8/contingencia.sh`, uno a la vez.

Cada carpeta trae `r0.bin` (R0), `r1.bin` (R1) y `r2_multi.bin` (R2 con su R0 de respaldo), más la tabla y el programa que se pusieron con `icebram`. Antes de grabar: `cd bitstreams/contingencia/e7_s4 && sha256sum -c SHA256SUMS`. Se graba igual que los de `bitstreams/`, por ejemplo `iceprog bitstreams/contingencia/e7_s4/r1.bin`; `r2_multi.bin` con `iceprog -b`.

Estos bitstreams no pasaron por la maestra real. Su hardware sí (es el de R0, R1 y R2); lo que cambia es el contenido de dos BRAM.
