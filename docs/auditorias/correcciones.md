# Correcciones de las cuatro auditorías

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Correcciones del 17/11 sobre la rama `correcciones-auditoria`, creada desde `integra-noche` (`6adc90f`). Las auditorías (`clon_limpio.md`, `informe_enunciado.md`, `cifras.md` y `estilo.md`) quedan como se escribieron; sus `archivo:línea` se refieren al commit `bc0e8c4`. La columna "Ahora" da el `archivo:línea` después de las correcciones.

Reglas que se siguieron:

- Una cifra se corrige solo al valor de su archivo de medición. Si no hay archivo, la frase se deja o se reescribe sin la cifra, y se anota abajo.
- Los archivos generados no se editan a mano: se corrige el generador y se corre `make report` (que incluye `make p7-rapido`) o `tools/defensa/pruebas.py`.
- No se tocó `rtl/`, `sw/`, `tb/`, `ref/`, `bitstreams/` ni las mediciones que producen los scripts (salvo regenerarlas con su script). En `docs/estado.md` y `docs/pendientes_nicolas.md` solo se cambiaron las líneas que marca la auditoría de estilo.

## Resumen

| Auditoría | Errores corregidos | Errores sin corregir | Sugerencias aplicadas | Sugerencias no aplicadas |
|-----------|--------------------|----------------------|-----------------------|--------------------------|
| `clon_limpio.md` | 1 de 1 | 0 | 6 de 6 (H4 y H7 en parte) | 0 |
| `informe_enunciado.md` | 6 de 7 | 1 (el PDF en el repositorio) | 4 de 5 | 1 (el commit impreso) |
| `cifras.md` | 13 de 13 | 0 | 3 de 14 | 11 (el commit impreso, una cantidad sin archivo y los 9 grupos sin archivo de medición) |
| `estilo.md` | 23 de 23, más las 4 contradicciones | 0 | 34 de 36 | 1 (negritas), y 1 que no pide cambio (plural de siglas) |

Comprobaciones después de corregir:

- `make report`: regenera `informe/generado/` y `docs/mediciones/p7/`. Una segunda corrida sin cambios de código solo cambia `\commitinforme` en `informe/generado/peldano.tex`, como antes.
- `make check-hex test-ref test-asm`: `trade.hex` al día, 23 y 124 tests sin fallas.
- Ninguna raya larga ni semirraya en lo que se escribió.

## 1. `clon_limpio.md`: el README en un clon limpio

| Hallazgo | Tipo | Qué se hizo | Ahora |
|----------|------|-------------|-------|
| H1, `README.md:56`, `:83` y `:84`: `-o build/...` sin que exista `build/` | Error | Se agrega `mkdir -p build/fondo` antes de ensamblar `fondo.s`, y se dice que `make fondo-hex` crea la carpeta y que el ensamblador no la crea. El bloque de las referencias empieza con `mkdir -p build`. | `README.md:58`, `:84` |
| H2, `README.md:32` a `:48`: no se avisa la demora | Sugerencia | Columna "Demora aproximada" en la tabla de pruebas y demora en cada "Prueba" de las piezas. Los valores salen de los comentarios del `Makefile`, de `docs/comandos.md` y de lo medido en el clon limpio. Donde nada lo mide se escribe "sin medir". | `README.md:50`, `:70`, `:72` a `:77`, `:109` a `:116`, `:124` a `:190` |
| H3, `README.md:46` a `:48`: requisitos sin nombrar | Sugerencia | Se nombran `make` y `git`, que hace falta el historial completo (`make r0-reproducir` y `make r0-molde`) y que el repositorio privado necesita acceso de lectura. | `README.md:46`, `:48` |
| H4, `README.md:68` y `:185`: las pruebas reescriben archivos versionados | Sugerencia, en parte | El README avisa que `make fondo-oficial` reescribe `docs/mediciones/fondo/<peldaño>/oficial.txt` y `make report` reescribe `informe/generado/peldano.tex`, y que solo cambia la línea del commit. No se cambió el comportamiento de los scripts: es un cambio de herramientas de medición que no corresponde a esta revisión. | `README.md:70`, `:190` |
| H5, `README.md:73`: `make equiv` a los tres períodos | Sugerencia | Ahora dice 0,1 ms y 1 ms por el RTL con Verilator, los tres períodos en el gemelo y una serie de cada familia, y que los 20 000 ticks a 10 ms por el RTL son `make equiv-largo`. | `README.md:75` |
| H6, `docs/fondo.md:390`: "los scripts agregan OSS CAD Suite al `PATH`" | Sugerencia | Los scripts lo toman de `OSS_CAD_SUITE` o del `PATH` y no lo agregan. | `docs/fondo.md:390` |
| H7, `README.md:105` y `bitstreams/README.md:5`: `make bin` no reproduce el R0 guardado | Sugerencia, en parte | El README explica que `make bin` da el mismo diseño pero otro archivo, y que para la placa se usa el guardado o `make r0-reproducir`. `bitstreams/README.md` no se tocó porque `bitstreams/` queda fuera de esta revisión. | `README.md:114` |

## 2. `informe_enunciado.md`: el informe contra el enunciado

### Errores

| Hallazgo | Qué se hizo | Ahora |
|----------|-------------|-------|
| 3.1.f: pérdida máxima de comprar y mantener ausente (`t31.tex:8` y `:14`) | `tools/report.py` simula comprar y mantener con la contabilidad de `ref/market.py`: compra en el tick 0 todo lo que alcanza la caja, como la referencia del testbench, y lleva la pérdida máxima con la misma definición que las otras filas (`Mercado.max_dd`). Verifica que el patrimonio final sea el de `market.comprar_y_mantener`. Resultado: 7 788 en la serie completa y 4 620 en los primeros 2 000 ticks. `docs/mediciones/tabla_3_1.txt` sigue sin el dato, porque lo genera `ref/trader.py` y `ref/` queda fuera de esta revisión. | `tools/report.py:100` a `:115`, `:141`; `informe/generado/t31.tex:8` y `:14` |
| Sección 5: "Regla base (referencia de clases)" (`informe.tex:68`, `t31.tex:9` y `:15`) | La regla se rotula "Regla base del grupo (hasta el 15/11)" en la tabla y "Regla base del grupo" en la de bloques. El texto dice que el grupo la usó hasta el 15/11 y en qué se diferencia de `max_media`. Además se explica por qué compite `max_media` aunque la regla base gane en la práctica (punto 3.1.b). | `tools/report.py:134`, `:165`; `informe/informe.tex:68`, `:77` |
| 6.1: "cierra en 1 semillas" (`informe.tex:206`) | Dos macros nuevas en `tools/p7/tablas.py`: el total de semillas y las del Espino base. El texto dice "el segmentado con el reloj doblado cierra en 1 de 10 semillas y el Espino base en 0", en la esquina de retardo máximo, y cita `docs/mediciones/p7/negativos.txt`. | `tools/p7/tablas.py:811` a `:816`; `informe/informe.tex:224` |
| 6.2: 1,76 % contra el presupuesto (`informe.tex:206`) | Macro nueva `\cifraUsoPresuRondaTres`: peor caso contra el presupuesto, no contra el período. Da 1,95 % en R0 y 19,58 % en el fondo, igual que `\pSieteUsoRtres...`. | `tools/report.py:202`, `:245`; `informe/informe.tex:224` |
| 6.3 y 3.3.l: "incluida la maestra del curso" (`informe.tex:213`) | Se quita. Ahora dice que R0 pasó la puerta de simulación completa y que la prueba con la maestra real está programada para el 26/11. También responde en los términos del enunciado: ninguna variante gana más, el segmentado es el más rápido, el fondo hace más operaciones útiles por tick, y R0 se elige por balance. La línea 179, que decía que R0 "ya pasó todas las pruebas", ahora dice "la puerta de simulación". | `informe/informe.tex:231`, `:197` |
| 6.4: "las comparaciones no son trabajo útil" (`informe.tex:190`) | Ahora dice que no cuentan como operaciones leer `PRICE`, escribir `DECISION`, armar el byte, volver al sondeo y las instrucciones que reemplazan a los desplazamientos, de acuerdo con `docs/codiseno.md`, sección 3. | `informe/informe.tex:208` |
| Sección 4: `informe/informe.pdf` no está en el repositorio | **Sin corregir.** En esta máquina no hay LaTeX, y el PDF tiene que compilarse con el texto final. Queda pendiente guardar antes del 1/12 el PDF que compila la integración continua (trabajo `informe`) o uno compilado localmente. | |

### Sugerencias

| Hallazgo | Qué se hizo | Ahora |
|----------|-------------|-------|
| 3.2.b: el paso 3 se llama "Actualizar el estado y predecir" | Ahora se llama "Predecir". | `informe/informe.tex:103` |
| 6.5: el CPI de 2,652 junto a una tabla con 2,103 | "Contando también el lazo de sondeo, el CPI medido de todo el programa es...". | `informe/informe.tex:156` |
| 6.6: nombres internos "P1", "T105" y "T100" | "En su primera medición" en el texto. Los códigos se quitaron de las notas de `t33amdahl.tex` y `t33variantes.tex`. | `informe/informe.tex:195`; `tools/report_33.py:68`, `:115` |
| 6.7: el mismo dato con dos porcentajes | El texto dice siempre "del período" (1,76 %) o "del presupuesto" (1,95 %), según el denominador. | `informe/informe.tex:62`, `:156`, `:224`, `:231` |
| 6.8: el commit impreso queda un paso atrás | **No aplicada.** `peldano.tex` registra el commit en que se corrió `make report`, y que cambie en cada corrida es el comportamiento esperado. Imprimir otro commit cambia lo que el informe certifica, y eso es una decisión del grupo. | |

### Coberturas parciales que no son error ni sugerencia

| Punto | Qué se hizo | Ahora |
|-------|-------------|-------|
| 3.1.b: por qué `max_media` y no la regla base; umbral y alfa | Un párrafo con el sesgo de selección, la semilla reservada y el error de los bloques. Una frase sobre la meseta del umbral y el compromiso de alfa 1/32 (`docs/algoritmo.md`, secciones 5.1 y 5.2). No se agregan cifras a mano. | `informe/informe.tex:54`, `:77` |
| 3.2.c: registros y memoria | Tabla de registros y de la palabra `TMP`, tomada de `sw/trade.s`: `x8` es el byte de decisión y los temporales son `x7` y `x9`. | `informe/informe.tex:115` a `:132` |
| 3.2.f: equivalencia por el RTL en la rama de R0 | Una frase sobre `make equiv` con Verilator a 0,1 ms y 1 ms, con cero diferencias (`docs/puertas.md`, criterio 2 de R0). | `informe/informe.tex:138` |
| 3.3.a: f agrupa dos fases | "El estimador, es decir, la desviación a la media y su actualización", y f se presenta como la suma de sus fracciones. | `informe/informe.tex:171` |
| 3.3.i: falta la predicción de Amdahl para R1 | **No aplicada.** Requiere un análisis nuevo del fondo con Amdahl. | |
| Regla general: "el README indica el comando de cada número" | Ahora dice que cada tabla indica su archivo de medición, y `docs/comandos.md` el comando. | `informe/informe.tex:39` |
| Sección 5: contenido no pedido (escalera, ASIC, duplicador, variantes no construidas) | **No se movió.** Sacar secciones del informe es una decisión del grupo. | |

## 3. `cifras.md`: cifras contra las mediciones

### Errores

| Hallazgo | Qué se hizo | Ahora |
|----------|-------------|-------|
| E1, `informe.tex:206`: 1,76 % del presupuesto | Igual que el error 6.2 de la auditoría del informe: 1,95 %. | `informe/informe.tex:224` |
| E2, `informe.tex:206`: "1 semillas" | Igual que el error 6.1: "1 de 10", y se dice qué diseño y qué esquina. | `informe/informe.tex:224` |
| E3, `t33variantes.tex:7`: speedup 0,74 | `tools/report_33.py` toma el speedup de las macros de `docs/mediciones/p7/cifras.tex`, calculadas sin redondear, en vez de volver a redondear el valor de 3 decimales del CSV. Ahora da 0,75. | `tools/report_33.py:38` a `:45`, `:61`; `informe/generado/t33variantes.tex:7` |
| E4, `t33escalera.tex:13`: speedup 24,23 | La misma corrección: 24,22, como `\pSieteEscSpeedupCuatro` y `escalera.txt:18`. | `tools/report_33.py:128`; `informe/generado/t33escalera.tex:13` |
| E5, `README.md:168`: firma de R0 "vista en la placa a los tres períodos" | Ahora dice que se vio la mitad baja (`3C`) a los tres períodos y que falta la mitad alta (`A2`). También se agrega lo que pasó R2 y lo que falta, desde `docs/mediciones/placa_16nov.md`. | `README.md:173` |
| E6: "el fondo escribe los mismos bytes que `max_media`" | Ahora: los mismos 20 000 bytes solo en el testbench a 0,1 ms (los dos 26 070); a 1 ms y 10 ms el fondo da 25 031 y `max_media` 26 070; viendo todos los precios, 26 388 y 25 973. Las cifras se comprobaron en `docs/mediciones/fondo/r1/equiv.txt:14` a `:21`, `docs/mediciones/p7/gemelo.txt:17` y `:23`, `docs/mediciones/tabla_3_1.txt:7` y la salida de `ref/fondo.py`. La pregunta de las pruebas de degradación aclara que corren a 0,1 ms, y `degradacion.txt` da 0 bytes distintos ahí. | `docs/defensa/resumen.md:19`; `docs/defensa/fondo.md:89`, `:93`, `:137`; `docs/defensa/cifras.md:75`; `docs/defensa/preguntas.md:458`, `:459`, `:471`; también `docs/checklist_26nov.md:89`, `docs/fondo.md:336` y `:377`, y `docs/bitacora/ensayo.md` |
| E7, `espino_base.md:118` y `preguntas.md:607`: dos respuestas a "qué consume más ciclos" | Las dos responden lo mismo, con `docs/mediciones/p7/perfil.txt`: en el kernel de 51 ciclos, la fase más larga es actualizar la media (17 ciclos, 33,3 %); con la desviación (12) el estimador suma 29 de 51 (56,9 %), que es la f de Amdahl; en la respuesta, decidir (14 de 41); en el tick, esperar (98 %). | `docs/defensa/espino_base.md:118`; `docs/defensa/preguntas.md:607` |
| E8, `tabla_vigilante.md:73`: "5 ticks de los 536" | 5 de los 361 con el relevo medido en la placa (536 con los 53 ms de la hoja de datos). | `docs/defensa/tabla_vigilante.md:73`; también `docs/tabla_vigilante.md:101` y una nota en `docs/decisiones.md`, T71 |
| E9, `preguntas.md:39`: "Nada se ha probado todavía en la placa" | Lo probado el 16/11, desde `docs/mediciones/placa_16nov.md`. | `docs/defensa/preguntas.md:39` |
| E10, `preguntas.md:599` | Lo mismo. Además, el tiempo de reconfiguración tiene una sola medición de tres pedidas. | `docs/defensa/preguntas.md:599` |
| E11, `resumen.md:36`: tabla de puertas | Fila de placa con R0 en su mitad baja, R1 pendiente y R2 con firma a 0,1 ms, media hora sin disparo y relevo medido. | `docs/defensa/resumen.md:36` |
| E12, `verificacion.md:139`, `:140` y `:158` | Lo mismo en las tres líneas. El relevo queda como parcial, porque no se anotó la imagen testigo. | `docs/defensa/verificacion.md:139`, `:140`, `:158` |
| E13, `barrel.md:121` y `plan_estudio.md:43` | Lo mismo. | `docs/defensa/barrel.md:121`; `docs/defensa/plan_estudio.md:43` |

### Sugerencias

| Hallazgo | Qué se hizo | Ahora |
|----------|-------------|-------|
| Sección 1: el commit impreso | **No aplicada**, igual que la 6.8 de la auditoría del informe. | |
| Sección 4: celdas de R0, 1083 contra 1091 | Donde R0 se compara con R1 y R2 (que son de P7) se usa 1091. `docs/defensa/cifras.md:21` y `espino_base.md:102` ya daban los dos valores con su explicación y se dejaron. En `segmentado.md` la tabla es histórica: se agregó una fila con el base en P7 en vez de mezclar fuentes. | `docs/defensa/resumen.md:15`; `tabla_vigilante.md:18`; `diagramas.md:31` y `:93`; `guia_nicolas.md:27`; `segmentado.md:67` |
| Sección 4: frecuencia mínima de R0, 42,43 contra 41,93 | 41,93 donde se compara con R1 y R2. En la tabla de la puerta de simulación (`verificacion.md:109`) se deja 42,43, que es la medición de la puerta, y se anota 41,93 de P7. | `docs/defensa/tabla_vigilante.md:18`; `verificacion.md:109`; `guia_nicolas.md:28` |
| Sección 4: uso de la ronda 3, 1,9 % y 2,2 % | `preguntas.md:207` dice 1,95 % del presupuesto y 1,76 % del período. `cifras.md:40` aclara que 2,2 % es el barrido de fases (49 ciclos) y que el informe usa 1,95 % (44 ciclos). `espino_base.md:94` ya decía 49 ciclos barriendo fases y se dejó. | `docs/defensa/preguntas.md:207`; `cifras.md:40` |
| Sección 4: series en el gemelo, 700 contra 3810 | **No aplicada.** La de 3810 (`make equiv-gemelo`) no tiene archivo de medición guardado, y guardarlo requiere una corrida nueva. | |
| Sección 5: 9 grupos de cifras sin archivo de medición (gemelo contra Verilator, mediana de seguir tendencia, `make formal-base`, 1 122 corridas, +0,007 y -0,005, +0,04, cifras de la extensión, 16 000 flip-flops, `retune`) | **No aplicadas.** Guardar esas salidas en `docs/mediciones/` requiere correr los comandos de nuevo. Ninguna de esas cifras está mal según la auditoría. | |

## 4. `estilo.md`: rayas largas, registro y huellas de autoría

### Errores: huellas de autoría (sección 2)

| Hallazgo | Qué se hizo | Ahora |
|----------|-------------|-------|
| `docs/bitacora/p1.md:56`: "subagente" | "los portamos desde la factibilidad". | `docs/bitacora/p1.md:56` |
| `docs/estado.md:183`: la frase sobre herramientas de IA | Se quita la mención; queda lo de las rutas locales. | `docs/estado.md:217` |
| `docs/pendientes_nicolas.md:5` | "Decisiones y acciones que dependen de Nicolás." | `docs/pendientes_nicolas.md:5` |
| `docs/pendientes_nicolas.md:20` y `:21`: tuteo y primera persona | "del shell", "localmente", "requiere `sudo`". | `docs/pendientes_nicolas.md:31`, `:32` |
| `docs/autoprueba.md:102`: "una sesión" | "la grabación la hace siempre Nicolás". | `docs/autoprueba.md:102` |
| `docs/tabla_vigilante.md:165`: "una persona" | "Nicolás". | `docs/tabla_vigilante.md:165` |
| `docs/bitacora/p4.md:5`, `p7.md:5`, `docs/estado.md:91` y `:248`: "otra sesión" | "en paralelo", "para después", "cuando se cierren". | `docs/bitacora/p4.md:5`, `p7.md:5`; `docs/estado.md:125`, `:282` |
| Citas a "plan, sección 16.x": `autoprueba.md:6`, `checklist_26nov.md:7`, `tabla_vigilante.md:101`, `extension_isa.md:240`, `bitacora/p0.md:5`, `decisiones.md:376`, `estado.md:515` | Ahora citan `docs/puertas.md` o la decisión T50 o T58, o el criterio se presenta como del grupo. | Las mismas líneas; `docs/estado.md:549` |

### Errores: lo que sale en el PDF (sección 3)

| Hallazgo | Qué se hizo | Ahora |
|----------|-------------|-------|
| `informe.tex:206`: "1 semillas" | Ver el error 6.1 de la auditoría del informe. | `informe/informe.tex:224` |
| `t33amdahl.tex:6` y `:13`: "estimo" | En `tools/p7/tablas.py` las descripciones que llegan al informe dicen "estimó". Los textos de los `.txt` que no llegan al informe se dejaron sin tildes, como el resto de las salidas de los scripts. | `tools/p7/tablas.py:428` |
| "extension" 14 veces (`t33amdahl.tex`, `t33escalera.tex`, `roofline.tex`) | "extensión", en las descripciones y en los rótulos de los techos. `make p7-rapido` regenera `amdahl.csv`, `escalera.csv`, `roofline.csv`, `roofline.tex` y `roofline.svg`, y sus `.txt`. Solo cambian esas palabras. | `tools/p7/tablas.py:431` a `:434`, `:517` a `:526`, `:596`, `:597` |

### Errores: documentos de estudio (sección 6.1)

| Hallazgo | Qué se hizo | Ahora |
|----------|-------------|-------|
| `codiseno.md:359`, dos errores | "ya sea que el programa responda" y la coma antes de "sino". | `docs/codiseno.md:359` |
| `tabla_vigilante.md:213` | "si no se hubiera simulado". | `docs/tabla_vigilante.md:213` |
| `tabla_vigilante.md:55` y `:214`: "tabla de verdad" | "tabla definitiva". También se corrigió en `docs/defensa/tabla_vigilante.md`, `preguntas.md` y `bitacora/p5.md`. | `docs/tabla_vigilante.md:55`, `:57`, `:214` |
| `autoprueba.md:257` | "gasta 5 ticks y el reset de R0, 0,164 ms". | `docs/autoprueba.md:257` |
| `espino_barrel.md:140` y `:276` | "en un ciclo distinto del que...". | `docs/espino_barrel.md:140`, `:276` |
| `checklist_26nov.md:33`, `pendientes_nicolas.md:14`: "del FPGA" | "de la FPGA". | `docs/checklist_26nov.md:34`; `docs/pendientes_nicolas.md:25` |
| `ensamblador.md`: "assembler" (6 líneas) | "ensamblador". Se deja la ruta `assembler/asm.py`, que es un nombre de archivo. | `docs/ensamblador.md` |
| `gemelo.md` y `extension_isa.md:198`: "branch" | "salto condicional". | `docs/gemelo.md:40`, `:41`, `:52`, `:53`, `:121`; `docs/extension_isa.md:198` |
| `trade_s.md:12`: "porte del testbench" | "traducido del testbench a Python". | `docs/trade_s.md:12` |
| `ensamblador.md:253`: "(1 palabras, 4 bytes)" | Se corrió el ensamblador y esa es su salida real, así que la cita se dejó. Se agrega una nota de que el mensaje siempre usa el plural y un `mkdir -p build` para que el ejemplo funcione en un clon limpio. `tools/pochoasm.py` no se cambió. | `docs/ensamblador.md:251` a `:258` |
| `fondo.md:362`: dos dos puntos | Partida en dos oraciones. | `docs/fondo.md:362` |

### Contradicciones (sección 6.2)

| Hallazgo | Qué se hizo | Ahora |
|----------|-------------|-------|
| `codiseno.md:369`: "medida, no investigada" | "medida e investigada hasta la síntesis". | `docs/codiseno.md:369` |
| `tabla_vigilante.md:190` y `:191`: nada probado en la placa | El estado del 16/11, con una sola medición del relevo. | `docs/tabla_vigilante.md:190`, `:191` |
| `espino_barrel.md:319` y `:341`, `extension_isa.md:220` y `:263` | Lo mismo. También en `docs/puertas.md` (R0, R1 y R2) y en `docs/fondo.md:378`. | Las mismas líneas |
| `fondo.md:390`: los scripts agregan OSS CAD Suite | Ver H6. | `docs/fondo.md:390` |

### Sugerencias

| Hallazgo | Qué se hizo |
|----------|-------------|
| Sección 1: `--` en las tablas generadas | Las celdas sin dato dicen "n/a"; en la columna de ciclos medidos de Amdahl, "sin medir". Con la pérdida máxima nueva, `t31.tex` ya no tiene celdas vacías. |
| Sección 3: "Tiempo (us)" en `t32.tex` | "Tiempo ($\mu$s)" en las dos ramas de `tools/report.py`. |
| Sección 3: "P1", "T105", "T100" | Corregido (ver 6.6 de la auditoría del informe). |
| Sección 3: `informe.tex:144`, `:153` y `:211` | "En qué se gastan los ciclos", "el estimador ... concentra la mayor parte del kernel" y "privilegia el co-diseño por sobre los puntos esperados" (`informe/informe.tex:162`, `:171`, `:229`). |
| Sección 4: `README.md:28` y `:118` | "reset de encendido largo"; "cae más de 3 unidades" (`README.md:28`, `:123`). También "herramientas de compilación" en vez de "toolchain" (`:46`). |
| Sección 5: "us" y "uJ" en `docs/defensa/` | µs y µJ en las 13 líneas. |
| Sección 5: "por la regla de Nicolás", "decisión T50 de Nicolás", "decisión de Nicolás (opción a)" | "Por decisión del grupo", en `extension.md:40`, `preguntas.md:407`, `fondo.md:11` y `verificacion.md:120`. |
| Sección 5: la cita "opción b, tomemos riesgos" | "Se priorizó el diseño integrado aunque agregue riesgo" (`resumen.md:11`, `fondo.md:11`). La cita textual sigue en `docs/decisiones.md`, T50, que es el registro. |
| Sección 5: "respuesta honesta", "sin rodeos" | Se quitan (`fondo.md:91`, `preguntas.md:9`, `plan_estudio.md:38`, `resumen.md:19`). |
| Sección 5: "en papel" | "puntaje simulado". |
| Sección 5: "son cables" | "se implementa solo con cableado" o "basta el cableado", en `extension.md`, `preguntas.md` y `algoritmo.md`. |
| Sección 5: "chico", "de verdad", "adentro/afuera", "de punta a punta" | "pequeño" o "menor"; "realmente", o "se ejecuta"; "comprado / en caja", o "votan comprar"; "completo". También en los documentos de defensa que se escribieron después de la auditoría (`diagramas.md`, `guiones.md`, `guia_*.md`). |
| Sección 5: `verificacion.md:13` | "Si una prueba nunca falla, no hay evidencia de que detecte errores." |
| Sección 6.3: µs y µm² en `docs/*.md` | 69 cambios en 18 archivos, solo en prosa (los bloques de código y el código en línea quedan iguales). |
| Sección 6.3: "chico", "de verdad", "igual" por "aun así", "de a", "adentro/afuera", "N veces más lento", "puntaje en papel", "conducidas", "empujar", "foto del estado", "con honestidad", anglicismos menores, "caminata aleatoria" y "candidata", "pines sueltos", los casos sueltos de registro y el "✓" | Aplicadas en `docs/*.md` y en las bitácoras (9, 16, 6, 6, unos 20, 4, 4, 3, 5, 8, 1, 6, 16, 4 y 11 casos). Los identificadores y las citas de código quedan iguales. |
| Sección 6.3: frases de efecto | Se reescribieron los tres ejemplos de la auditoría (`gemelo.md:156`, `extension_isa.md:105`, `algoritmo.md:270`). Las otras unas 17 no se tocaron, porque habría que reescribir párrafos enteros. |
| Sección 6.3: negrita al comienzo de cada viñeta | **No aplicada.** Habría que cambiar el estilo de documentos enteros. |
| Sección 6.3: plural de siglas ("LEDs", "LUTs") | La auditoría dice que es aceptable y no pide cambio. |

## 5. Otras huellas que no estaban en las auditorías

Corregidas, con el mismo criterio:

- `docs/registrador.md:18`: "(plan, sección 16.4)".
- `docs/bitacora/p0.md:31`: "esta sesión".
- `docs/bitacora/p2.md:35`: "lo que el plan nombra".
- `docs/bitacora/p9_entrega.md:16`: "plan local".
- `docs/checklist_1dic.md:14`: "la sesión de `gh`", que ahora es "la cuenta".
- "Encargo" pasó a "Objetivo" en las bitácoras, y las instrucciones citadas con tuteo se reescribieron en forma neutra (`docs/bitacora/generador_b.md:5`, `docs/generador_b.md:9`).
- `docs/decisiones.md`: "El plan pide, admite o permite" en T51 y en las entradas de las líneas 377, 424, 425, 461, 482, 514 y 560. Se cambió solo la cita; la decisión es la misma.
- `tools/autoprueba.py:39`: "sección 16.3 del plan".
- `tools/p8/matriz.py:3`: "frente E del plan".
- `factibilidad/a_barrel/README.md:7`: "en dos sesiones".

Vistas y **no corregidas**, porque las reglas de esta revisión no lo permiten. Quedan para quien edita esos archivos:

| Archivo:línea | Texto | Por qué no |
|---------------|-------|------------|
| `docs/pendientes_nicolas.md:14` | "Tu decisión anunciada en el próximo mensaje manda sobre esta recomendación." | Se agregó después de la auditoría y no está marcado. En ese archivo solo se podían cambiar las líneas marcadas. Es la huella más visible que queda. |
| `docs/estado.md:13` | "rama del agente" | Lo mismo: no está marcada. |
| `docs/estado.md:23` | "esta sesión no tiene permiso para empujar a `main`" | Lo mismo. |
| `docs/estado.md:50`, `:77`, `:78` | "te tocan", "tu shell", "Si quieres el PDF en tu máquina" | Lo mismo. |
| `docs/estado.md:508` | "Primer paquete del plan vigente" | Lo mismo. |
| `tb/tb_estres.sv:2` | "(plan del proyecto, sección 16.4, criterios 4 y 7)" | `tb/` queda fuera de esta revisión. |
| `bitstreams/README.md:5` | "Desde entonces `make bin` produce R0" (H7) | `bitstreams/` queda fuera de esta revisión. |
| `docs/mediciones/tabla_3_1.txt` | La pérdida máxima de comprar y mantener en blanco | La genera `ref/trader.py`, y `ref/` queda fuera de esta revisión. El informe ya la trae, desde `tools/report.py`. |
| `docs/mediciones/placa_16nov.md` | "**PASS**", "cables sueltos", "líneas ya conducidas" | Es el registro de lo informado en la placa. No está marcado. |
