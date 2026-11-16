# Bitácora del kit de defensa

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Rama `defensa`, desde `p8-anticipacion` (`9ad1c40`, con P1 a P5, P7 y P8). Todo el trabajo queda en `docs/defensa/`. No se cambia código.

## Encargo

1. Un documento de estudio por pieza: `espino_base.md`, `segmentado.md`, `barrel.md`, `extension.md`, `fondo.md`, `tabla_vigilante.md`, `algoritmo.md` y `verificacion.md`. Cada uno parte de lo básico, llega al detalle con `archivo:línea` y cierra con 5 a 10 preguntas.
2. `preguntas.md`: banco de al menos 100 preguntas con respuesta corta y `archivo:línea`, agrupadas por pieza, con las incómodas.
3. `cifras.md`: las cifras de memoria, cada una con su fuente.
4. `resumen.md`: una página para ponerse al día.
5. `plan_estudio.md`: plan para tres personas hasta el 1/12.
6. `README.md` de la carpeta.

Reglas: cada cifra con su fuente en `docs/mediciones/` o en un documento del repo; cada `archivo:línea` comprobado en esta rama; contradicciones entre documentos ajenos se anotan aquí y en el informe final, sin corregirlas.

## 16/11

- Rama creada desde `origin/p8-anticipacion` (`9ad1c40`).
- Leídos: `README.md`, `docs/estado.md` (P7, tramos 7 a 13), `docs/decisiones.md` (T50 a T124), `docs/puertas.md`, los documentos de estudio de cada pieza, el RTL del core base, del barrel, de la extensión, de la tabla y del vigilante, `sw/trade.s`, `sw/fondo.s` y las mediciones de `p7/`, `fondo/r1/`, `tabla_3_1.txt`, `base.txt` y `espino_segmentado.txt`.

### Contradicciones encontradas entre documentos (no corregidas)

Se anotan con los dos lugares. Ninguna cambia una conclusión.

1. Celdas y frecuencia de R0: 1083 celdas y 42,43 MHz en `docs/puertas.md` (criterio 3 de R0) y `docs/tabla_vigilante.md` (sección 1), contra 1091 y 41,93 MHz en `docs/mediciones/p7/variantes.txt` y `docs/codiseno.md` (sección 1), y 1086 en `docs/espino_barrel.md` (sección 6). Es el mismo RTL; la diferencia es el ruido de la síntesis de T6, pero los documentos no lo dicen igual.
2. Frecuencia mínima del segmentado: 51,1 MHz en `docs/espino_segmentado.md` (sección 1) y 51,59 en `docs/espino_barrel.md` (sección 6), contra 45,34 en `docs/mediciones/p7/variantes.txt` (hallazgo 1 de P7, no investigado).
3. Patrimonio de la equivalencia de `sw/trade.s` en el testbench con 20 000 ticks: `docs/trade_s.md` (sección 5) dice 26 795 a 0,1 ms y 27 306 a 1 ms, que son de la regla base; `docs/decisiones.md` (T51) y `docs/puertas.md` dicen 26 070 a los tres períodos con `max_media`.
4. Estado del algoritmo: `docs/algoritmo.md`, párrafo "Estado" del comienzo, dice que la regla base sigue siendo el algoritmo de `sw/trade.s`; la sección 7.6 del mismo documento y T51 dicen que desde el 15/11 es `max_media`.
5. Gemelo y barrel: `docs/fondo.md` (secciones 7 y 13), `docs/tabla_vigilante.md` (sección 8), `docs/espino_barrel.md` (sección 8.5) y `docs/extension_isa.md` (sección 7.3) dicen que el gemelo no modela el barrel; `docs/gemelo.md` (sección 7) y el tramo 12 de `docs/estado.md` dicen que sí desde P4.
6. Peor caso con los gestores colgados: `docs/fondo.md`, pregunta 2 de la sección 15, dice 564 ciclos (cifra de P3); la tabla de la sección 1 y la sección 9 del mismo documento dicen 568 (R1).
7. SCLK mínimo y período mínimo de R1: 115 kHz y 26,66 us en el tramo 12 de `docs/estado.md` (programa de P3), contra 110 kHz y 26,94 us en el tramo 13 y en `docs/mediciones/fondo/r1/sclk_minimo.txt`. El árbol usa 115 a propósito (T124).
8. `docs/gemelo.md`, sección 7.4, atribuye el arreglo de la variable estática de los testbenches a la "decisión T70"; en `docs/decisiones.md` es T81 (T70 es la de los moldes).
9. `docs/peldano.md` cita `docs/mediciones/peldano_probar_r1.txt`, que no existe en esta rama. `docs/gemelo.md`, sección 7.5, cita `docs/mediciones/fondo/gemelo_series.txt`; el archivo está en `docs/mediciones/fondo/r1/gemelo_series.txt`.

## Avance

- Se integró `origin/p8-anticipacion` (informe, README nuevo, `docs/comandos.md`) en la rama: las referencias se volvieron a comprobar; cambió `tools/autoprueba.py:60` a `:61` y la cita del README en `cifras.md` pasó a `docs/gemelo.md`, porque el README nuevo ya no trae esa tabla.

- `espino_base.md`, `segmentado.md`, `barrel.md`: hechos y empujados.
- `extension.md`, `fondo.md`, `tabla_vigilante.md`: hechos y empujados.
- `algoritmo.md`, `verificacion.md`: hechos y empujados.
- `cifras.md`: hecho. Cuando dos mediciones del mismo diseño difieren por ruido de síntesis (R0 1083 y 1091 celdas; segmentado 51,13 y 45,34 MHz) se dan las dos con su fuente.
- `preguntas.md`: 155 preguntas (53 [B], 78 [A], 24 [I]) en 12 secciones, cada una con `archivo:línea`.
- `resumen.md`, `plan_estudio.md` y `README.md`: hechos.

### Comprobación de las referencias

Un script en el área temporal (no versionado) extrae cada `` `archivo:línea` `` y cada rango `` `:N` `` de `docs/defensa/*.md`, comprueba que el archivo exista y que la línea no esté vacía, e imprime la línea para revisarla a mano. Última corrida: 0 errores. Se corrigieron en el camino: `rtl/pochoco_soc.v:125` (vacía, pasó a `:124`), `tools/asm/isa.py:90` (era la llave, pasó a `:91`), `sw/fondo.s:191` (era el `beqz`, pasó a `:192`, el `lw` de `PRICE`), y dos citas de `docs/contingencia.md` y `docs/tabla_vigilante.md` que apuntaban a la línea vecina.

Ninguna referencia apunta a una línea de `docs/estado.md`: ese archivo crece por arriba en cada tramo y las líneas se corren (pasó al agregar el párrafo de este kit). Se citan sus secciones, o el script o la medición de donde sale la cifra.

### Decisiones propias del kit

- **Ajuste al reparto propuesto**: `sw/trade.s` pasa a Vicente (cierra los puntos 3.1, 3.2 y 3.3 en una persona) y `sw/fondo.s` entero a Santiago, que además acompaña a Nicolás el 26/11 (`plan_estudio.md`, sección 2).
- **Las [I] se responden con lo aceptado a sabiendas**, citando la decisión (T50, T51, T58, T124) en vez de defender que no hubo costo.

### Lo que no se hizo

- Diagramas nuevos de la arquitectura y del flujo de un tick: se usan los de `docs/espino_barrel.md` (sección 3.2), `docs/espino_segmentado.md` (sección 4), `docs/fondo.md` (sección 3.2) y `docs/pochoco_soc.svg`.
- Un documento por bloque de `sw/trade.s`: lo cubre `docs/trade_s.md`, al que apuntan `espino_base.md` (sección 5) y la sección 3 del banco.
