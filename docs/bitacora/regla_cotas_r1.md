# Bitácora: la regla de cotas en R1 y R2 (opción F-a, decisión T133)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Rama `regla-cotas-r1`, desde `0acda61` (R0 ya con la regla nueva). El hardware de R1 y R2 no cambia: el programa y la tabla entran por `icebram` en los moldes guardados.

## 17/11, noche

- Plan: `sw/fondo.s` nuevo (hilo 0 con la regla y los umbrales leídos de la tabla en cada tick, hilos 1 a 3 en un lazo de espera), `ref/fondo.py` como modelo exacto, y adaptar el testbench del fondo y las pruebas de la puerta, que estaban hechas para el fondo que vota.
- `sw/fondo.s` nuevo: 67 palabras (el fondo anterior tenía 251). Hilo 0: sondeo, cuatro umbrales leídos de la tabla en cada tick (`T_LO_MAS_1` = 101, `T_HI` = 255, `T_BANDA_COMPRA` = 161, `T_BANDA_VENTA` = 195), decisión sin saltos como `sw/trade.s`, un store a DECISION y uno de telemetría. Hilos 1 a 3: un salto a sí mismos, con una marca `#@HILOk` para inyectar fallas.
- `ref/fondo.py` modela el programa exacto (bytes, telemetría, tabla, traza). Con la tabla por defecto decide igual que `ref/trader.py` (Oficial) en la serie Meta, en la anterior y en familias crudas y normalizadas (`ref/test_fondo.py`, 8 pruebas). En la serie Meta: 19 214 con 4 órdenes.
- Gemelo del barrel con la serie Meta completa a 0,1, 1 y 10 ms: 4/4, bytes idénticos a la referencia, peor caso 127 ciclos (el fondo anterior llegaba a 444).
- RTL de R1 con `tb/fondo/tb_fondo.sv` y la serie Meta completa: PASS (bytes, estado, LED y 7 segmentos, protocolo, ningún store a la RAM), 18 s de Verilator.
- Herramientas adaptadas: testbench del fondo (sin el estado del protocolo de votos; cuenta stores a la RAM), `revisar.py`, `simbolos.py`, `variante.py` (fallas de los hilos 1 a 3: `ocupado`, `escribe`, `programa`; `cuelgue_sup` para el vigilante), `controles.py` (13 controles de la regla nueva), `degradacion.sh`, `fases.sh`, `equiv.sh`, `series.sh` y `lote.py` (series normalizadas entre 100 y 255), `ticks.sh`, `estres.py` (serie de ventanas normalizadas de la serie Meta) y la prueba del relevo.
- `tools/fondo/molde_cotas.sh`: control previo superado a mano: los moldes con los programas del commit `c794834` dan byte por byte `r0_base_max_media.bin`, `r1_fondo.bin`, `r2_fondo_vigilante.bin` y `r2_multi.bin`.
- Queda: verificación corta, puertas completas de R1 y R2 por la cola, bitstreams nuevos con su simulación, relevo del vigilante y `docs/puertas.md`.
- Herramientas fuera de la puerta que usan nombres del fondo anterior y ya no corren: `tools/retune.py` (parámetros `S_ENTRA`, etc.; está en `make check-p8` de la integración continua), `tools/autoprueba.py` (control con `G1_ENTRA`) y `tools/exhaustivo/r1.py` (usa los gestores). Se informan; no se adaptan en esta rama.

## 18/11, madrugada

- Verificación corta (`make check-fondo HW=r1`): la primera corrida encontró dos errores de las herramientas, ninguno del programa: `lote.py` no importaba la normalización (el lote quedó en 1 serie) y el control del umbral de venta con 196 no lo ejercitaba ninguna serie. Corregidos (el control quedó en dos: 200 con una serie de reversión normalizada, y 196 con la semilla 2, la única que tiene un 195 exacto estando adentro). Segunda corrida: todo PASS.
- Con la regla de cotas el hilo 0 responde en 128 ciclos: el caso de SCLK de 100 kHz a 0,1 ms (237 ciclos entre transacciones) pasa a la puerta; el límite de exploración baja de 600 a 200 ciclos.
- Puertas completas por la cola: R1 (46 min) y R2 (46 min), todos los criterios PASS. Bitstreams sobre los moldes con el control y `icetime` iguales. Relevo del vigilante: PASS. Gemelo con 1 051 series a los tres períodos: PASS. Resultados en `docs/puertas.md`, sección "R1 y R2 con la regla de cotas".
- Observación: la síntesis nueva de `make fondo-timing` (el programa y la tabla cargados al sintetizar) da 1001 celdas en R1 y 1015 en R2, contra 1029 y 1045 con el programa anterior. Es otra netlist del mismo RTL (como la caída del segmentado, T127); los bitstreams de competencia no salen de esa síntesis sino del molde, que es el hardware que pasó las puertas.
- Pendiente para la promoción (lo decide quien integre): copiar los cuatro `.bin` de `build/fondo/molde_cotas/` a `bitstreams/` con sus hashes, rehacer las autopruebas de placa (`tools/autoprueba.py` usa `G1_ENTRA`), y adaptar o retirar `tools/retune.py` (en `make check-p8`) y `tools/exhaustivo/r1.py`.
