# Auditoría 3: cifras del informe, del README y del kit de defensa

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Revisión del 17/11 sobre la rama `auditorias`, creada desde `origin/main` en el commit `bc0e8c4`. Alcance: cada número de `informe/informe.tex` (con lo que entra desde `informe/generado/`), de `README.md` y de `docs/defensa/*.md`, contra los archivos que genera `make report` (`informe/generado/*.tex`, `docs/mediciones/p7/*`) y contra las demás mediciones generadas de `docs/mediciones/`.

## 1. `make report` contra lo guardado

Comando, desde la raíz de la rama: `export PATH=$HOME/herramientas/oss-cad-suite/bin:$PATH; make report`. Terminó bien en 6,4 s ("62 cifras y tablas en informe/generado/", peldaño R0 por defecto). No hay LaTeX en esta máquina, así que no compiló el PDF.

| Archivo regenerado | ¿Cambia contra lo guardado? |
|--------------------|-----------------------------|
| `docs/mediciones/p7/*` (lo rehace `make p7-rapido`, que es parte de `make report`) | No: idénticos byte a byte. |
| `informe/generado/cifras.tex`, `cifras_p7.tex`, `roofline.tex`, `t31.tex`, `t31bloques.tex`, `t32.tex`, `t32hilos.tex`, `t33*.tex` | No: idénticos byte a byte. |
| `informe/generado/peldano.tex` | **Sí, una línea**: `\commitinforme` pasa de `e4f4a8f` a `bc0e8c4`. |

La única diferencia es el commit que el informe imprime en su primer párrafo (`informe.tex:39`). Es inevitable que quede un commit atrás si el archivo generado se guarda en el mismo commit que lo usa. **Sugerencia**: imprimir el commit de las mediciones (por ejemplo el de `docs/mediciones/p7/cifras.tex`, que ya lo trae) o regenerar `peldano.tex` en la integración continua al compilar el PDF, en vez de guardarlo. El archivo se restauró después de la prueba: esta rama solo agrega los informes.

## 2. Método

1. Un script con la biblioteca estándar extrajo cada número con decimales o de tres o más cifras de los 15 archivos auditados (fechas, rutas, hashes y código entre comillas invertidas aparte) y lo buscó, exacto o redondeado, en los 152 archivos versionados de `docs/mediciones/` y en `informe/generado/`. Solo 58 números no aparecen de forma exacta; se revisaron uno por uno.
2. Como casi cualquier entero aparece en algún archivo de 1,1 MB de mediciones, la búsqueda automática no detecta una cifra que coincida con otra medición distinta. Por eso se revisaron a mano, contra su fuente: todas las cifras de las secciones "Número" del README, todas las filas de `docs/defensa/cifras.md`, todas las cifras escritas a mano en `informe.tex`, y las de los demás documentos de defensa que aparecen con valores distintos en dos lugares.
3. Se comprobó además que los archivos de medición correspondan al código actual: los 23 archivos que nombran `sw/fondo.s` llevan el sha256 del archivo actual (`19773517830a2e16...`), y `docs/mediciones/p7/gemelo.txt` el de `build/fondo/fondo.hex` actual (`d1c9990dc3303f93...`). Los 8 con otro sha256 están en `docs/mediciones/fondo/p3/`, que es historia del paquete P3 y no se cita como resultado vigente.

Los enteros chicos que no son mediciones (fechas, "3 rondas", "4 hilos", números de pregunta) no se revisaron.

## 3. Errores: cifras que no calzan con su fuente o entre sí

| N.º | Archivo:línea | Lo escrito | Lo que dice la fuente | Fuente |
|-----|---------------|------------|-----------------------|--------|
| E1 | `informe/informe.tex:206` | "el diseño que compite usa el 1,76 % del actual [presupuesto]" | Contra el presupuesto de 2 262 ciclos, 44 ciclos son 1,945 %. El 1,76 % es contra el período completo (2 500 ciclos). | `docs/mediciones/p7/variantes.txt:37`; `informe/generado/cifras_p7.tex` (`\pSieteUsoRtresRcero` = 1,95) |
| E2 | `informe/informe.tex:206` | "cierra en 1 semillas" (`\pSieteDobleSemillas`) | "1 de 10" semillas, y en el segmentado en la esquina máxima | `docs/mediciones/p7/negativos.txt:19` y `:22` |
| E3 | `informe/generado/t33variantes.tex:7` (tabla de variantes del informe) | Speedup de la respuesta del barrel con extensión: 0,74 | 41 / 55 = 0,7454, que se redondea a 0,75. La fuente guarda 0.745 y `tools/report_33.py` vuelve a redondear el número ya redondeado (en coma flotante 0.745 queda en 0,74). `cifras_p7.tex` y `docs/defensa/cifras.md:58` dicen 0,75: el informe y la defensa no coinciden. | `docs/mediciones/p7/variantes.csv:5`, `variantes.txt:31` |
| E4 | `informe/generado/t33escalera.tex:13` | Speedup del paso 4: 24,23 | 24.22 en la fuente (95 × 51 / 200 = 24,225, el mismo doble redondeo) | `docs/mediciones/p7/escalera.txt:18`; `\pSieteEscSpeedupCuatro` = 24,22 |
| E5 | `README.md:168` | R0: firma `a23c` "vista en la placa a los tres períodos" | En la placa solo se vio la mitad baja ("3C") a los tres períodos; la mitad alta ("A2") está pendiente | `docs/mediciones/placa_16nov.md`, tabla "Lo que se vio", fila R0; `docs/puertas.md:121` |
| E6 | `docs/defensa/resumen.md:19`, `docs/defensa/fondo.md:93` y `:137`, `docs/defensa/cifras.md:75`, `docs/defensa/preguntas.md:459` y `:471` | "En la serie de práctica [el fondo] escribe los mismos [20 000] bytes que `max_media`" | Solo vale en el testbench a 0,1 ms (fondo y `max_media` dan 26 070). A 1 ms y 10 ms el fondo da 25 031 y `max_media` 26 070; viendo todos los precios, `ref/fondo.py` da 26 388 y `ref/trader.py` 25 973. Los bytes no son los mismos. | `docs/mediciones/fondo/r1/equiv.txt:19` a `:21`; `docs/mediciones/p7/gemelo.txt` (r0 r2 y r0 r3: 26070); salida de `python3 ref/fondo.py tb/practica.csv` (26 388) y `docs/mediciones/tabla_3_1.txt:7` (25 973) |
| E7 | `docs/defensa/espino_base.md:118` | "Actualizar la media: 17 de 58 ciclos sin la espera" | El kernel medido es de 51 ciclos (17 de 51 = 33,3 %). Y `docs/defensa/preguntas.md:607` responde la misma pregunta con "29 de 51 ciclos del kernel" (desviación más actualización). Dos respuestas distintas a la misma pregunta en el mismo kit. | `docs/mediciones/p7/perfil.txt`; `informe/generado/t33perfil.tex` |
| E8 | `docs/defensa/tabla_vigilante.md:73` | "gasta solo 5 ticks de los 536 del relevo" | Con el tiempo medido en la placa son 361 (536 era con los 53 ms de la hoja de datos). El mismo documento dice 361 en las líneas 91 y 116, y `preguntas.md:527` también. | `docs/mediciones/placa_16nov.md`, tabla del relevo |
| E9 | `docs/defensa/preguntas.md:39` | "Nada se ha probado todavía en la placa" | El 16/11 R2 pasó la firma a 0,1 ms y la media hora sin disparo, y el relevo se midió en 35,50 ms | `docs/mediciones/placa_16nov.md` |
| E10 | `docs/defensa/preguntas.md:599` | "Nada se ha probado en la placa todavía. Falta ... el tiempo real de reconfiguración" | Igual que E9; además la pregunta 122 (`preguntas.md:535`) ya da los 35,50 ms medidos | `docs/mediciones/placa_16nov.md` |
| E11 | `docs/defensa/resumen.md:36` | Tabla de puertas: R0 "Bitstream listo, falta grabarlo"; R2 "Pendiente" | R0 ya se grabó (se vio "3C" a los tres períodos) y R2 pasó dos de sus pruebas. El párrafo de la línea 39 del mismo archivo lo dice. | `docs/mediciones/placa_16nov.md` |
| E12 | `docs/defensa/verificacion.md:139`, `:140` y `:158` | "Falta programarla en la placa" (R0); relevo y media hora de R2 "Pendiente"; "Todo lo demás es simulación" | Igual que E9 y E11 | `docs/mediciones/placa_16nov.md` |
| E13 | `docs/defensa/barrel.md:121` y `docs/defensa/plan_estudio.md:43` | "nada se ha probado en la placa"; "todo es simulación hasta el 26/11" | Igual que E9 | `docs/mediciones/placa_16nov.md` |

E3 y E4 son diferencias de una centésima por un redondeo doble en `tools/report_33.py` (lee del CSV valores con tres decimales y los vuelve a redondear); conviene redondear desde el valor sin redondear o con `Decimal`. E9 a E13 son estados que quedaron atrás con las pruebas en placa del 16/11; son "cifras" en el sentido de que afirman un resultado que la medición contradice.

## 4. Cifras con fuente, pero distinta según el documento

No son errores, porque cada valor sale de una medición real, pero un profesor que lea el informe y la defensa ve dos números para lo mismo. **Sugerencia**: usar en todo el kit los valores de P7, que son los del informe, y dejar los antiguos solo en `docs/defensa/cifras.md` con su explicación.

| Cantidad | Valor en el informe | Otro valor | Dónde aparece el otro | Fuente de cada uno |
|----------|---------------------|------------|-----------------------|--------------------|
| Celdas de R0 | 1091 | 1083 | `docs/defensa/resumen.md:15`, `tabla_vigilante.md:18`, `espino_base.md:102`, `segmentado.md:64`, `cifras.md:21` | `docs/mediciones/p7/variantes.txt:10`; `docs/mediciones/espino_segmentado.txt` |
| Frecuencia mínima de R0 | 41,93 MHz | 42,43 MHz | `docs/defensa/tabla_vigilante.md:18`, `verificacion.md:109`, `espino_base.md:104`, `segmentado.md:64` | las mismas |
| Uso de la ronda 3 por R0 en el peor caso | 1,76 % (`informe.tex:62` y `:138`) y 1,95 % (`informe.tex:213`) | 1,9 % y 2,2 % | `docs/defensa/preguntas.md:207` (1,9 %), `espino_base.md:94` (2,2 %, con 49 ciclos) | 1,76 % contra el período; 1,95 % contra el presupuesto; 2,2 % es el barrido de fases (`docs/mediciones/barrel/ticks.txt:30`) |
| Series comparadas en el gemelo para R0 | 700 (`informe.tex:120`) | 3810 | `docs/defensa/preguntas.md:203`, `verificacion.md:36` y `:151` | 700 lo cuenta `tools/report.py`; 3810 es `make equiv-gemelo`, sin archivo de medición guardado |

## 5. Cifras sin una fuente generada que las respalde

Estas cifras solo están escritas en documentos de texto (`docs/*.md`, `docs/estado.md`, `docs/decisiones.md` o `factibilidad/*.md`), no en un archivo que produzca un comando. No se encontró que estén mal; la observación es que no se pueden regenerar. **Sugerencia** en todos los casos: guardar la salida del comando en `docs/mediciones/` o citar el texto como estimación.

| Archivo:línea | Cifra | Dónde está escrita | Comentario |
|---------------|-------|--------------------|------------|
| `README.md:126`; `docs/defensa/cifras.md:110`; `preguntas.md:559`; `verificacion.md:43` | Fondo a 10 ms: 0,14 s en el gemelo contra 35 minutos en Verilator; R0: 0,02 s contra 22 minutos; "unas 22 horas en Icarus (estimado)" | `docs/gemelo.md:196` y `:197` ("medido en P3") | Tiempos de reloj de pared; ningún archivo de medición los guarda. |
| `docs/defensa/algoritmo.md:18` y `:127`; `preguntas.md:67` | Seguir tendencia: mediana 5 566, 10 de 336 sobre 10 000 | `docs/estado.md:888` | `make hallazgos` no guarda su salida. |
| `docs/defensa/preguntas.md:267`; `segmentado.md:89`; `verificacion.md:76` | `make formal-base`: 1376 puntos | `docs/espino_segmentado.md:218`, `docs/estado.md:673` | La salida de `make formal-base` no se guarda en `docs/mediciones/`. La de `make xd-formal` (1890 puntos) sí está en `docs/mediciones/xd/formal.txt`. |
| `docs/defensa/fondo.md:83`; `preguntas.md:487` | 1 122 corridas sanas sin que venza el plazo | `docs/fondo.md:322` | Es una suma de corridas de varios archivos; no está escrita en ninguno de ellos. |
| `docs/defensa/cifras.md:74`; `resumen.md:19`; `fondo.md:11` y `:139`; `preguntas.md:27`; `plan_estudio.md:42` | +0,007 y -0,005 puntos esperados | `factibilidad/cierre.md:65` (texto) | En `factibilidad/` no hay un archivo de mediciones con esas dos cifras; vienen de una tabla escrita a mano. |
| `docs/defensa/algoritmo.md:89` | +0,04 puntos sobre la regla base a 2 000 ticks | `docs/decisiones.md`, T51 | Sin archivo de medición. |
| `docs/defensa/extension.md:62` a `:64`, `:83`; `preguntas.md:391` y `:399` | k variable: 51,6 a 39,2 MHz y unas 160 celdas; `ema` de 60 a 167 celdas contra 37; multiplicador de 1338 celdas; 35 instrucciones por gestor | `docs/extension_isa.md`, secciones 4 y 12 (medido en la factibilidad) | Hay cifras parecidas en `factibilidad/d_isa/mediciones/`, pero no se encontró cada una de forma exacta. |
| `docs/defensa/segmentado.md:40` | "16 000 flip-flops" | `docs/decisiones.md`, T34 | Aproximación (512 × 32 = 16 384). |
| `README.md:180` | `retune` con las reglas publicadas reproduce R0, R1 y R2 byte por byte | Solo la salida de `make retune-control` | No hay archivo en `docs/mediciones/p8/`. El comando se corrió en esta auditoría y la afirmación se cumple: los cuatro `.bin` tienen el sha256 de `bitstreams/` (`docs/auditorias/clon_limpio.md`, paso 30). |

## 6. Lo que sí se comprobó y calza

Para que se vea el alcance, sin repetir cada línea: todas las cifras de la tabla "El diseño, en una tabla" y de las secciones "Número" del README (patrimonio 25 973 y 6 497, 21 configuraciones y 18,3 millones de eventos, CPI 1,350 y 2,350, 22 y 41 ciclos, 7,9 millones de instrucciones y 21 de 21 mutaciones, 63 y 83 ciclos, 1 050 series, 443 de 2 262 ciclos, 30 de 30 corridas, 0,32 s, 60 de 60 y 56 de 56 casos, 110 kHz, 18 millones de precios, 1,86 y 1,84, 56 y 8 operaciones, 66 comprobaciones); todas las macros y tablas que usa `informe.tex` (son las de `informe/generado/`, idénticas a lo regenerado); y todas las filas de `docs/defensa/cifras.md` salvo las de las secciones 3 a 5 de este documento.

## 7. Resumen

- `make report` regenera todo igual, salvo el commit impreso en `informe/generado/peldano.tex` (sugerencia).
- Errores: 13 (E1 a E13). Los más importantes: E6 (el fondo no escribe los mismos bytes que `max_media` en la práctica, salvo a 0,1 ms), E5 (la firma de R0 en la placa se vio solo a medias), E1 y E2 (dos cifras mal escritas en la sección del PLL del informe), E7 (dos respuestas distintas a "qué consume más ciclos") y E9 a E13 (estado de la placa desactualizado en cinco documentos de defensa).
- Sugerencias: 4 cantidades con dos valores según el documento (sección 4) y 9 grupos de cifras sin archivo de medición (sección 5).
