# Auditoría 2: el informe contra el enunciado

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Revisión del 17/11 sobre la rama `auditorias`, creada desde `origin/main` en el commit `bc0e8c4`. Se compara `informe/informe.tex` (con las tablas y cifras de `informe/generado/` tal como las deja `make report`) contra los puntos 3.1, 3.2 y 3.3 de `docs/Proyecto_4_arq.pdf` y contra las reglas generales del enunciado sobre lo que se entrega. El texto del PDF se extrajo con un script propio de la biblioteca estándar de Python (descompresión de los flujos con `zlib` y lectura de los operadores `Tj` y `TJ`).

El informe se escribe con dos ramas de texto según el peldaño que compite (`\ifpeldanofondo`). Hoy `make report` lo genera para R0, porque no existe `rtl/00_peldano.v`. Esta auditoría revisa el texto que se compila hoy (rama R0) y comenta la rama del fondo solo cuando cambia la respuesta. No hay LaTeX en esta máquina; la integración continua compila el PDF sin errores (trabajo `informe`, corrida 43983074133 del 16/11, éxito).

Escala usada en la columna "Cobertura": **completa**, **parcial** (responde, pero falta algo que el punto pide) y **no responde**.

## 1. Punto 3.1: algoritmo de predicción y decisión

| N.º | Lo que pide el enunciado | Dónde lo responde el informe | Cobertura | Observación |
|-----|--------------------------|------------------------------|-----------|-------------|
| 3.1.a | Diseñar y validar el algoritmo fuera de la placa (Python o C) con la serie de práctica | Sección 1.1, líneas 46 a 54; tabla `tab:31b` (líneas 75 a 80) | Completa | Nombra `ref/trader.py`, los bloques de 2 000 ticks y las familias sintéticas. |
| 3.1.b | Explicar la idea detrás de la elección del algoritmo | Sección 1.1, línea 46 | Parcial | Explica bien por qué reversión a la media (razón de varianza y autocorrelación). No explica por qué `max_media` y no la regla base, que en la propia tabla `tab:31` gana en la serie completa (27 062 contra 25 973), en la media de los bloques (11 069 contra 11 043) y en el peor bloque (9 720 contra 9 620). El lector ve una tabla donde la referencia agregada por el grupo le gana al algoritmo elegido y el texto no lo comenta. La respuesta existe en `docs/defensa/algoritmo.md`, sección 6 (sesgo de selección, semilla reservada, +0,7 % y +1,4 %); bastan dos frases. Tampoco se justifica el umbral de 3 unidades ni alfa 1/32. |
| 3.1.c | El algoritmo debe implementarse con los recursos de la FPGA (aritmética entera o de punto fijo, memoria del SoC, LUTs) dentro del presupuesto de ciclos de cada ronda | Sección 1.2, línea 62 | Completa | Aritmética entera, 40 palabras, remite a la sección de ticks para el presupuesto. |
| 3.1.d | Explicar cómo decide la cantidad q | Sección 1.2, línea 64 | Completa | Posición objetivo con órdenes de 63, recorte de la maestra e idempotencia. |
| 3.1.e | Comparar con no operar y con comprar al inicio y mantener | Sección 1.3, líneas 68 a 75, tabla `tab:31` | Completa | |
| 3.1.f | Reportar patrimonio final, número de órdenes, comisiones pagadas y pérdida máxima desde un peak | Tabla `tab:31` (`informe/generado/t31.tex`) | Parcial | La pérdida máxima de comprar y mantener aparece como "--" en las dos mitades de la tabla (líneas 8 y 14 de `t31.tex`), y la fuente (`docs/mediciones/tabla_3_1.txt`) también la deja en blanco. Comprar y mantener sí tiene pérdida máxima (termina en 6 497 partiendo de 10 000), y el enunciado la pide para la comparación. **Error.** |

## 2. Punto 3.2: implementación en assembly

| N.º | Lo que pide el enunciado | Dónde lo responde el informe | Cobertura | Observación |
|-----|--------------------------|------------------------------|-----------|-------------|
| 3.2.a | Implementar el algoritmo en `trade.s` para Espino (RV32E) | Sección 2, líneas 97 a 105 | Completa | |
| 3.2.b | Describir la estructura del ciclo principal: esperar precio, actualizar estado, predecir, decidir y escribir `DECISION` | Sección 2.1, líneas 98 a 104 | Completa | El orden real del programa es esperar, leer, predecir, decidir, escribir y después actualizar la media; el informe lo dice en el paso 5. Está bien, aunque el paso 3 se llama "Actualizar el estado y predecir" y solo calcula `dev`: conviene llamarlo "Predecir" para que no parezca que la media se actualiza dos veces. |
| 3.2.c | Documentar el uso de registros y memoria | Sección 2.2, línea 113 | Parcial | Solo dice "usa 8 registros y una palabra de trabajo" y remite a `docs/trade_s.md`. El enunciado pide documentarlo en el informe: falta una tabla corta con qué guarda cada registro (`x2` base del SPI, `x3` la media S, `x4` la posición, `x5` el precio, `x6` 32p y `dev`, `x7` a `x9` temporales) y la palabra `TMP` en `0x7FC`. |
| 3.2.d | Documentar la representación de punto fijo | Sección 2.2, línea 109 | Completa | S = 32 m, 13 bits, umbrales en la misma escala. |
| 3.2.e | Explicar cómo se resolvieron las operaciones que Espino no tiene (shifts, multiplicación, división) | Sección 2.2, línea 116 | Completa | Cinco sumas para multiplicar por 32, la identidad para el desplazamiento con signo y el truco del `lbu`. |
| 3.2.f | Mostrar que `trade.s` toma exactamente las mismas decisiones que la referencia para toda la serie de práctica | Sección 2.3, línea 120 | Parcial | Con el testbench sin modificar solo se muestran los primeros 2 000 ticks. La serie completa (20 000 ticks) se muestra con el gemelo digital, no con el RTL. `make equiv` sí corre los 20 000 ticks por el RTL con Verilator a 0,1 ms y 1 ms, y la rama del fondo lo cita (línea 120), pero la rama de R0 no. Agregar una frase con ese resultado deja el punto completo con evidencia del RTL. |
| 3.2.g | Reportar por tick IC, ciclos, CPI y tiempo, en el caso promedio y en el peor caso | Tabla `tab:32` (`informe/generado/t32.tex`) | Completa | |
| 3.2.h | Comparar esas mediciones con el período T de cada ronda | Tabla `tab:32`, columnas "% de T" y "Presupuesto" | Completa | Ver el hallazgo 6 sobre los dos porcentajes distintos para la misma cantidad. |

## 3. Punto 3.3: co-diseño hardware/software

| N.º | Lo que pide el enunciado | Dónde lo responde el informe | Cobertura | Observación |
|-----|--------------------------|------------------------------|-----------|-------------|
| 3.3.a | Identificar, midiendo, qué parte del algoritmo consume más ciclos | Sección 3.1, línea 146 y tabla `tab:perfil` | Parcial | La tabla está bien. El texto (línea 153) dice que "actualizar la media se lleva la mayor parte del kernel" y usa f = 0,569, pero en la tabla la fila "Actualizar la media" es el 33,3 % del kernel; el 0,569 resulta de sumar "Desviación a la media" (23,5 %) y "Actualizar la media" (33,3 %). Hay que decir que f agrupa las dos fases del estimador. |
| 3.3.b | Usar la ley de Amdahl para estimar cuánto se ganaría acelerando esa parte | Sección 3.1, línea 153 | Completa | f, F, S y el límite con F infinito. |
| 3.3.c | Proponer e implementar al menos dos alternativas de hardware y compararlas con la versión solo software | Sección 3.2, líneas 164 a 175 | Completa | Cuatro alternativas construidas y medidas. |
| 3.3.d | Para cada variante: LUTs y BRAM | Tabla `tab:variantes` | Completa | Celdas, LUT4 y BRAM. |
| 3.3.e | Para cada variante: frecuencia máxima | Tabla `tab:variantes`; línea 177 | Completa | Mínima y mediana en 10 semillas, con la advertencia sobre el ruido de la síntesis. |
| 3.3.f | Para cada variante: ciclos por tick | Tabla `tab:variantes` | Completa | |
| 3.3.g | Para cada variante: CPI medido | Tabla `tab:variantes`, columna "CPI kernel" | Completa | |
| 3.3.h | Para cada variante: Ops/s, definiendo qué cuenta como operación útil | Línea 146 y tabla `tab:variantes` | Completa | |
| 3.3.i | Para cada variante: speedup medido contra el predicho por Amdahl | Tabla `tab:amdahl` | Parcial | Están el segmentado, el barrel en un hilo y el barrel con la extensión. Falta R1 (y R2), que es justamente el diseño integrado que el grupo eligió: la tabla de variantes trae su speedup medido (0,18 en la respuesta, 1,36 en MOPS) pero no hay predicción de Amdahl con la que compararlo. |
| 3.3.j | Para cada variante: ubicación del kernel en el roofline de su Espino | Figura `fig:roofline`, línea 190 | Completa | |
| 3.3.k | Si se sube la frecuencia con el PLL: mostrar que nextpnr cierra timing y recalcular el presupuesto | Sección 3.4, línea 206 | Completa | No aplica (no hay PLL en el VQ100), pero se muestra el error de nextpnr y se recalcula el presupuesto hipotético. |
| 3.3.l | Elegir la variante final y justificar: la que más gana, la más rápida o la que mejor balancea LUTs, ciclos y calidad de predicción | Sección 3.5, líneas 210 a 214 | Parcial | La rama R0 (la que se compila hoy) dice que R0 "es el que pasó todas las pruebas, incluida la maestra del curso" (línea 213). Al 17/11 eso no es cierto: la maestra real se prueba el 26/11 y la puerta de placa de R0 no está completa (`docs/puertas.md:121`). Además no responde la pregunta en los términos del enunciado (ganancia, rapidez o balance); la rama del fondo (línea 211) sí lo hace. **Error** mientras no se haya probado con la maestra. |

## 4. Reglas generales del enunciado sobre la entrega

| Regla | Dónde está en el enunciado | Situación | Observación |
|-------|----------------------------|-----------|-------------|
| Justificar cada decisión con ciclos, CPI, Ops/s, LUTs y frecuencia máxima | Sección 1 | Cumple | |
| Se evalúa la calidad del proceso y de la evidencia | Sección 1 | Cumple | Cada tabla trae su fuente y su comando. |
| Los ítems 1 a 3 se entregan como "código + PDF" | Sección 6, tabla de puntaje | Parcial | El repositorio no tiene `informe/informe.pdf`: el PDF solo existe como artefacto de la integración continua, que expira y no queda en la entrega. Hay que guardar el PDF compilado en el repositorio antes del 1/12. |
| Todo hardware agregado debe estar en el repositorio con su testbench | Sección 4 | Cumple (fuera del alcance del informe) | |
| El README debe indicar cómo sintetizar y programar, cómo ensamblar, cómo correr los testbenches y la referencia, y las versiones de las herramientas | Sección 4 | Cumple | Revisado en `docs/auditorias/clon_limpio.md`. |
| El informe dice que el README indica el comando de cada número (línea 39) | Afirmación propia | Parcial | El README solo dice que todas las cifras salen de `make report`. La correspondencia cifra a cifra está en `informe/generado/` y en `docs/comandos.md`, no en el README. Corregir la frase o apuntar a `docs/comandos.md`. |

## 5. Lo que el informe trae y el enunciado no pide

La regla del grupo es "mínimo viable: cada punto de 3.1, 3.2 y 3.3 en orden, con las tablas y figuras pedidas y nada más".

| Contenido | Dónde | Juicio |
|-----------|-------|--------|
| Fila "Regla base (referencia de clases)" en la tabla `tab:31` y mención en la línea 68 | `informe.tex:68`, `t31.tex:9` y `:15` | No la pide el enunciado (pide dos referencias). Además el nombre parece inexacto: el repositorio la define como la regla del propio grupo (`ref/p4_baseline.py`, y en `docs/mediciones/tabla_3_1.txt` aparece como "regla base (trade.s hasta el 15/11)"), no como una referencia entregada en clases. Si se mantiene, hay que llamarla "regla base del grupo" y explicar por qué el algoritmo elegido queda bajo ella (hallazgo 3.1.b). **Error de denominación** si no viene de clases. |
| Tabla de los 10 bloques (`tab:31b`) | Líneas 75 a 80 | Sirve como validación (3.1.a). Se puede mantener. |
| Párrafo sobre el ruido de la síntesis del segmentado | Línea 177 | Sostiene la columna de frecuencia máxima; es aceptable, pero usa "P1" (un nombre interno de paquete de trabajo que el lector no conoce). |
| Escalera de la clase 7 (tabla `tab:escalera`) | Líneas 181 a 188 | No la pide el enunciado. Es material de la clase y del plan del grupo. Candidata a moverse a `docs/codiseno.md`. |
| Edición ASIC: Ops/W y energía por decisión (tabla `tab:asic`) | Líneas 197 a 202 | No la pide el enunciado. Candidata a moverse a `docs/`. |
| Duplicador de reloj por lógica | Línea 206 | El enunciado solo pide el PLL y de forma condicional. Una frase basta; hoy el resultado se entrega sin decir qué diseño se probó ni de cuántas semillas (ver el punto 1 de la sección 6). |
| Variantes construidas sin el Espino base con extensión (línea 179) y filas "no construida" de `tab:amdahl` | Línea 179, `t33amdahl.tex:11`, `:12`, `:18` y `:19` | Predicciones sin medición; aportan poco al punto 3.3 y alargan la tabla. Opcional. |

## 6. Otros hallazgos del texto del informe

1. **Error.** `informe.tex:206`: "cierra en \pSieteDobleSemillas{} semillas" se compila como "cierra en 1 semillas". Falta la concordancia y el total: la fuente (`docs/mediciones/p7/negativos.txt` y la salida de `make p7-rapido`) dice "1 de 10 semillas". Tampoco dice qué diseño se probó (según `docs/defensa/preguntas.md:251`, el segmentado). Reescritura sugerida: "con un oscilador real de 45 a 55 % de ciclo de trabajo, el segmentado cierra en 1 de 10 semillas, sin margen".
2. **Error.** `informe.tex:206`: "el diseño que compite usa el \cifraUsoRondaTres\,\% del actual" usa 1,76 %, que es la respuesta peor (44 ciclos) contra el período completo de 2 500 ciclos. La frase habla del presupuesto (2 262 ciclos), contra el que el uso es 1,95 % (`\pSieteUsoRtresRcero`). Ver también el punto 7.
3. **Error.** `informe.tex:213`: "Es el que pasó todas las pruebas, incluida la maestra del curso". Al 17/11 la maestra no se ha probado y a R0 le falta la mitad alta de su firma en la puerta de placa (`docs/puertas.md:121`). Si el texto se escribe por adelantado, hay que dejarlo condicional o completarlo después del 26/11.
4. **Error.** `informe.tex:190`: "ninguno llega a su techo porque el sondeo y las comparaciones no son trabajo útil" contradice la definición de la línea 146, donde una operación útil es una de las 8 "aritméticas o de comparación" de `max_media` (4 de ellas son para decidir, es decir, comparaciones). Reescritura sugerida: "ninguno llega a su techo porque el sondeo, las cargas y los saltos del kernel no cuentan como trabajo útil".
5. **Sugerencia.** `informe.tex:138`: "El CPI medido del programa es 2,652" aparece justo después de una tabla cuyo CPI es 2,103 (promedio) y 2,095 (peor). Son ventanas distintas: 2,652 incluye el lazo de sondeo. Decirlo en la misma frase ("contando el sondeo, el CPI de todo el programa es 2,652").
6. **Sugerencia.** `informe.tex:177` y notas de `t33amdahl.tex` y `t33variantes.tex`: nombres internos ("P1", "T105", "T100") que el profesor no puede interpretar. Reemplazarlos por la descripción ("en la primera medición del segmentado") o quitarlos.
7. **Sugerencia.** El mismo dato aparece con dos porcentajes: `informe.tex:138` dice que 44 ciclos son "el 1,76 % del período de la ronda 3" y `informe.tex:213` dice que son "el 1,95 % de la ronda 3". Las dos cuentas son correctas con denominadores distintos (2 500 y 2 262 ciclos), pero el texto no lo aclara. Usar uno solo, o decir siempre "del período" o "del presupuesto".
8. **Sugerencia.** `informe.tex:39`: el párrafo inicial cita el commit del informe (`\commitinforme`). Cada vez que se guarda `informe/generado/peldano.tex` el commit queda un paso atrás (hoy dice `e4f4a8f` y la rama está en `bc0e8c4`). Ver `docs/auditorias/cifras.md`.

## 7. Resumen

- Puntos del enunciado revisados: 26 (6 de 3.1, 8 de 3.2 y 12 de 3.3; el 3.4 es la competencia y no va en el informe). Completos: 19. Parciales: 7 (3.1.b, 3.1.f, 3.2.c, 3.2.f, 3.3.a, 3.3.i y 3.3.l). Sin respuesta: ninguno.
- Reglas generales revisadas: 6. Se cumplen 4; quedan parciales 2 (el PDF no está en el repositorio y la afirmación de la línea 39 sobre el README).
- Errores: 7 (pérdida máxima de comprar y mantener ausente; "referencia de clases"; "1 semillas"; 1,76 % contra el presupuesto; "incluida la maestra del curso"; las comparaciones como trabajo no útil en la línea 190, contra la definición de la línea 146; el PDF no está en el repositorio).
- Sugerencias: 5 (sección 6, puntos 5 a 8, y el nombre del paso 3 en 3.2.b). Las de redacción están en `docs/auditorias/estilo.md`.
- Contenido no pedido: escalera de la clase 7, edición ASIC, duplicador de reloj, fila de la regla base y predicciones de variantes sin construir.
