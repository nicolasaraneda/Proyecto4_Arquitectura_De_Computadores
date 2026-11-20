# Bitácora: banda 40 en los tres peldaños (decisión T140)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Rama `banda-40`, desde `main` (`4da78ca`). El hardware no cambia: los programas y la tabla entran por `icebram` en los moldes guardados.

## 19/11, noche

- Leídos `docs/estado.md`, `docs/decisiones.md` y la sección 16.4 del plan. La rama `minutos-reales` y su carpeta (`~/proyectos/P4_wt_min`) son de otra sesión: solo se leyeron archivos con `git show`.
- "Recompra completa" es la opción (c) de la sección 11 de la exploración: es lo que la regla ya hace. Solo cambian los dos niveles de la banda.
- Referencia antes del cambio: `Cotas("espera", banda=60)` da 18 779 en la captura de Tesla (`~/proyectos/datos_p4/capturas/ronda_10ms_clase.csv`), igual a la maestra. La ventana de TSLA reconstruida desde los minutos de Alpaca (10/1/2022 10:20, 20 000 minutos, normalizada) es idéntica a la captura; con el mismo inicio se armó AMD (`build/banda40/amd_10ene2022.csv`): banda 60 da 21 895 (lo de la maestra), banda 40 da 26 470.
- Cambios: `ref/trader.py` (Oficial con banda 40), `ref/fondo.py` (tabla 141 y 215), `sw/trade.s` (141 y 215), `sw/fondo.s` (solo comentarios: el binario es idéntico al anterior), `sw/trade.hex` (dos palabras) y `sw/fondo_tabla.hex` (dos palabras). Pruebas en Python con las cifras nuevas (21 392 en la serie Meta).
- Controles negativos de R1 y R2: los dos de tabla ahora cargan la banda 60 (161 y 195), el de un nivel corrido en uno pasa a "vende desde 216" y se agrega "compra hasta 139". La semilla 2 ya no ejercita los bordes; la 39 de la familia de reversión tiene un 215 exacto adentro y un 140 exacto afuera.
- `tools/fondo/molde_cotas.sh` acepta `SUF=banda40` (`make fondo-molde-banda40`): mismos pasos, productos en `build/fondo/molde_banda40/`.
- **Hallazgo, decisión pendiente de Nicolás**: la autoprueba de placa no ve la banda. Su maestra interna manda una caminata de ±1 desde 128 durante 2000 ticks; con las semillas en uso (0xACE1 y 0x3CA1) nunca llega a 255, así que la regla no entra a la fase de banda y la firma sale igual con banda 40 que con banda 60. Ninguna de las 65 535 semillas toca 100 y 255 en 2000, 4000, 6000 ni 10 000 ticks; en 20 000 sí, pero el contador de ticks de la maestra es de 11 bits (`rtl/autoprueba/autoprueba_top.v:197`). Cualquier arreglo toca `rtl/autoprueba/`.
- Nicolás eligió la maestra normalizada (T141). `rtl/autoprueba/autoprueba_top.v` con `PASO` y `PISO`, `tb/autoprueba/tb_autoprueba.sv` los pasa, `tools/autoprueba.py` con `PASO`, `PISO` y `SEMILLA` como constantes y opciones `--paso`, `--piso` y `--semilla` (pedido de Nicolás: pasos más chicos para otras volatilidades). Semilla 0xE3AA elegida entre las 42 465 que tocan 100 y 255: la mayor diferencia entre banda 40 y 60 (380 bytes) con los extremos más temprano. Firma esperada `a639` en los tres peldaños en el gemelo a los tres períodos y en la referencia; con banda 60 sería `8610`.
- Puertas de R0 (`tools/puerta_r0_cotas.sh`) y R1 y R2 (`tools/fondo/puerta_cotas.sh`) en la cola global, después de un trabajo de la otra sesión.

## 20/11

- Puerta de R0 completa en verde (`docs/mediciones/r0_banda40_puerta.txt`). Único FAIL de la matriz: la exploración de 11,5 µs (50 ciclos disponibles, la regla usa 60), igual que con la banda 60.
- Moldes (`docs/mediciones/fondo/molde_banda40.txt`): el control con los programas de `c794834` reproduce los bitstreams anteriores byte por byte; `icetime` da 43,27, 52,61 y 51,66 MHz, iguales a los anteriores; los tres `.asc` por los pines idénticos a la referencia; R2 colgado pide la imagen 01 al terminar la transacción 105. Copiados a `bitstreams/` y `make r2-falla-banda40` (el `.asc` es el simulado por los pines).
- Puertas de R1 y R2: todo en verde salvo el paso de las series reales, que falló antes de simular: `tools/barrel/comun.sh` define `B=build/barrel` y pisaba la carpeta de las series de `tools/reales.sh`. Corregido (variable `SR`) y comprobado a mano el gemelo con Tesla en R1 (20 000 filas idénticas, 20 795). Se repite solo ese paso (`build/banda40/job_d.sh`, se agrega al final de cada registro), porque los demás no usan ese script.
- `make vig-relevo` y `make fondo-gemelo-series` en verde.
- Documentos: `docs/puertas.md` (secciones de banda 40), `bitstreams/README.md`, `README.md`, `docs/arbol_decision.md`, `docs/checklist_1dic.md`, `docs/cotas.md` y `docs/pendientes_nicolas.md` (decisión 6: límites del árbol con la regla de cotas).
- Repetición de las series reales (`banda40-reales`, 6 minutos en la cola): PASS en R1 y R2. Tesla 20 795 con 4 órdenes y AMD 26 470 con 8, por el RTL (0,1 y 1 ms, peor caso 127 ciclos) y por el gemelo a los tres períodos. Cada registro termina con `PASS: rX paso los criterios 1, 2, 4, 6 y 7 (con el paso de las series reales repetido)`.
- Integración continua local (`build/banda40/ci_local_b40.sh`, los 24 pasos de la corrida local, en un `git worktree` aparte): 23 en PASS en la primera corrida. El que falló, `make r0-molde check-p8`, comparaba el molde con `bitstreams/r0_cotas.bin` (banda 60). `tools/p8/r0_molde.sh` compara ahora con el R0 vigente (`R0_VIGENTE`, por defecto `r0_banda40.bin`). Repetido ese paso: PASS, y el molde sintetizado de nuevo da `r0_banda40.bin` byte por byte. Resumen en `docs/mediciones/ci_local_banda40.txt`.
