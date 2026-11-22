# Resumen para ponerse al día

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Una página, al 16/11. Para Vicente y Santiago: qué compite, por qué, qué está probado, qué falta y qué leer primero. Las cifras con su fuente están en `docs/defensa/cifras.md`.

## Qué compite y por qué

**El algoritmo** es `max_media`: reversión a la media. Una media exponencial del precio (alfa 1/32); si el precio cae más de 3 unidades bajo la media, "comprar 63"; si vuelve sobre la media, "vender 63"; si no, mantener. Siempre 63 porque la maestra recorta las órdenes y una orden en cero no paga comisión: el programa expresa una posición objetivo y no lleva contabilidad. La serie de práctica revierte (razón de varianza 0,53 a 100 ticks), seguir tendencia pierde, y `max_media` le gana a la regla base anterior 0,7 % en remuestreos y 1,4 % en series sintéticas plausibles, evaluado con una semilla reservada. En la serie completa de práctica da 25 973 (comprar y mantener: 6 497).

**El hardware** es una escalera de tres bitstreams (decisión T50: se priorizó el diseño integrado aunque agregue riesgo):

| Peldaño | Qué es | Celdas | Respuesta peor caso, barriendo fases | Para qué |
|---------|--------|--------|---------------------|----------|
| R0 | Espino base del curso con `sw/trade.s` (`max_media`) | 1091 | 49 ciclos | Respaldo de todo. No depende de nada |
| R1 | Espino **barrel** de 4 hilos con dos instrucciones propias (`emad`, `devk`) y una tabla de parámetros en BRAM, corriendo `sw/fondo.s`: un supervisor y tres gestores que votan | 1029 | 444 ciclos (19,6 % de la ronda 3) | El diseño elegido |
| R2 | R1 con un **vigilante** que, si el supervisor deja de escribir `DECISION` 5 precios seguidos, reconfigura la FPGA con R0 | 1045 | igual | Si pasa la placa y la maestra; reconfigurar está cubierto por la respuesta general del profesor (T126) |

La parte incómoda: **el fondo no suma puntos** frente a `max_media` sola (+0,007 a 2 000 ticks, -0,005 a 20 000, medido en la factibilidad). En la serie de práctica, en el testbench a 0,1 ms escribe los mismos 20 000 bytes que `max_media` (los dos terminan con 26 070); a 1 ms y 10 ms no: el fondo termina con 25 031 y `max_media` con 26 070 (`docs/mediciones/fondo/r1/equiv.txt`, `docs/mediciones/p7/gemelo.txt`). Viendo todos los precios, `ref/fondo.py` da 26 388 y `ref/trader.py` 25 973. Compite por lo que representa como co-diseño: procesador rediseñado, extensión de la ISA usada realmente, cuatro reglas en paralelo y todo medido. El riesgo lo acota la escalera: el árbol de decisión (`docs/arbol_decision.md`) dice cuándo competir con R0.

## Las piezas, en una línea cada una

- **Espino base**: CPI 2 (3 en loads y saltos tomados) porque el banco de registros es BRAM con lectura registrada.
- **Segmentado** (no compite): pipeline de 3 etapas, CPI 1,350 con el mix de la clase contra 1,5 estimado. El más rápido por hilo.
- **Barrel**: 4 hilos por 4 etapas, CPI 1 agregado y 4 por hilo, sin riesgos de datos ni de control. Más lento por hilo, pero el patrimonio no depende de la latencia mientras la decisión llegue antes del tick.
- **Extensión**: `emad` y `devk` en custom-0, un desplazamiento fijo de 5 más una suma: el estimador pasa de 14 instrucciones a 2. 52 celdas.
- **Fondo**: el supervisor (hilo 0) es el único que habla con la maestra; los gestores votan por memoria compartida con el número de tick; si un gestor se cuelga, el supervisor decide con su propia `max_media`.
- **Tabla y vigilante**: la tabla se cambia con `icebram` en 0,32 s sin volver a sintetizar; el vigilante dispara al quinto precio sin respuesta.
- **Verificación**: tres modelos separados (referencia en Python, RTL y gemelo digital en C) comparados byte a byte y ciclo a ciclo, con errores puestos a propósito para probar que las pruebas detectan.

## Qué está probado y qué falta

| Puerta | R0 | R1 | R2 |
|--------|----|----|----|
| Simulación (8 criterios) | Pasó | Pasó | Pasó |
| Placa (autoprueba con firma) | Mitad baja de la firma ("3C") a los tres períodos; falta la mitad alta ("A2") | Pendiente | Firma a 0,1 ms y media hora sin disparo; relevo medido en 35,50 ms; faltan 1 ms, 10 ms y ver la imagen testigo |
| Maestra real (miércoles 25/11, por confirmar) | Pendiente | Pendiente | Pendiente |

El 16/11 el profesor confirmó que se puede modificar lo que uno quiera y que el Espino multihilo es válido; la reconfiguración durante una ronda queda cubierta por esa respuesta general, sin confirmación específica (T126). Pendiente además: qué SCLK usa la maestra, la confirmación del relevo a la vista (el tiempo ya se midió: 35,50 ms) y la revisión del informe (`informe/informe.tex`, con las cifras que genera `make report`). **En la placa (16/11):** R2 pasó la firma a 0,1 ms y la media hora sin disparo, y el relevo se midió en 35,50 ms; faltan las firmas de R1 y de R2 a 1 y 10 ms (`docs/puertas.md`, puerta de placa).

Fechas: 22/11 corte del diseño integrado; 22/11 congelamiento del hardware y del algoritmo (etiqueta `v-maestra-25nov`); **maestra el miércoles 25/11, por confirmar**; 29/11 congelamiento total; 30/11 ensayo general; **1/12** entrega a las 10:00 y competencia y defensa a las 10:30.

## Qué leer primero

1. Este archivo y `docs/defensa/cifras.md` (media hora).
2. `docs/defensa/espino_base.md` y `docs/trade_s.md`: el punto de partida que todos tienen que dominar.
3. `docs/defensa/algoritmo.md`: por qué reversión, por qué `max_media`, cómo se evitó el sobreajuste.
4. `docs/defensa/barrel.md` y `docs/defensa/fondo.md`: lo que compite.
5. `docs/arbol_decision.md`: una página, qué se graba el 1/12.
6. Después, el documento de la pieza propia (`docs/defensa/plan_estudio.md`) y las preguntas **[B]** e **[I]** de `docs/defensa/preguntas.md`.
