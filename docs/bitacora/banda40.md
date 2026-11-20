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
