# Auditoría 4: estilo, rayas largas y huellas de autoría

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Revisión del 17/11 sobre la rama `auditorias`, creada desde `origin/main` en el commit `bc0e8c4`. La regla del grupo es "español formal pero creíble para un alumno de tercer año de ingeniería civil eléctrica, sin rayas largas". Se revisaron `informe/informe.tex` (con las tablas de `informe/generado/` que aparecen en el PDF), `README.md`, los 13 archivos de `docs/defensa/` y los 21 documentos de estudio de `docs/*.md` (todos salvo `docs/estado.md` y `docs/decisiones.md`, que son registros de trabajo y solo se miraron para buscar huellas de autoría). La búsqueda de menciones de herramientas de IA se hizo sobre todos los archivos versionados y sobre los mensajes de los 122 commits.

Criterio: **error** es algo incorrecto (gramática, término equivocado, cita a algo que no existe, huella de autoría); **sugerencia** es redacción que se puede mejorar. No se marcan los términos técnicos establecidos (pipeline, bitstream, testbench, timing, roofline, speedup, kernel, warm boot, ruteado, load y store). Tampoco "shifter", "shifts" ni "LUTs": el enunciado los usa así ("habilitar el shifter", "los shifts están deshabilitados", "cantidad de LUTs").

## 1. Rayas largas

| Búsqueda | Archivos | Resultado |
|----------|----------|-----------|
| Raya larga, U+2014 | `informe/informe.tex`, `informe/generado/*.tex`, `README.md`, `docs/*.md`, `docs/defensa/*.md` | 0 |
| Semirraya U+2013, y U+2012, U+2015 y U+2212 | los mismos | 0 |
| Guion con espacios usado como raya en prosa | los mismos | 0: todos los " - " son restas dentro de fórmulas (`dev = 32 p - S`) |
| `--` y `---` de LaTeX en el texto del informe | `informe/informe.tex` | 0 |
| `--` de LaTeX en tablas generadas | `informe/generado/t31.tex:8` y `:14`, `t31bloques.tex:6`, `t33perfil.tex`, `t33amdahl.tex:11`, `:12`, `:18` y `:19`, `t33escalera.tex` (columnas vacías) | Se compila como una semirraya (U+2013) y marca una celda sin dato. No es una raya en prosa. **Sugerencia**, solo si la regla se quiere aplicar al pie de la letra: escribir "n/a" o dejar la celda vacía. En `t31.tex` además oculta un dato que el enunciado pide (ver `docs/auditorias/informe_enunciado.md`, punto 3.1.f). |

## 2. Menciones de herramientas de IA y huellas de autoría

No aparecen en ningún archivo versionado los nombres de herramientas o empresas de IA, ni "asistente", ni "Co-Authored-By", ni "Generated with". Los 122 commits tienen autor y committer "Nicolás Araneda" y ninguno menciona herramientas. Sí hay estas huellas, todas **error** según la regla del grupo:

| Archivo:línea | Texto | Por qué | Reescritura sugerida |
|---------------|-------|---------|----------------------|
| `docs/bitacora/p1.md:56` | "los portó un subagente" | Única mención explícita de un agente automático. | "los portamos desde la factibilidad" |
| `docs/estado.md:183` | "Ningún archivo del repositorio menciona herramientas de IA" | La frase misma las menciona. | Borrar la frase; dejar solo lo de las rutas locales. |
| `docs/pendientes_nicolas.md:5` | "acumuladas mientras se trabajó sin él" | Se lee como un mensaje de otra persona o herramienta a Nicolás. | "Decisiones y acciones que dependen de Nicolás." |
| `docs/pendientes_nicolas.md:20` y `:21` | "En el archivo de inicio de tu shell"; "en tu máquina"; "(necesita `sudo`, no lo instalé)" | Tuteo dirigido a Nicolás y primera persona de alguien que no es él. | "En el archivo de inicio del shell"; "(requiere `sudo`)". Conviene sacar el archivo del repositorio o reescribirlo como lista de tareas del grupo. |
| `docs/autoprueba.md:102` | "(el plan no permite que una sesión ejecute `iceprog`)" | "Sesión" con el sentido de sesión de un asistente. | Borrar el paréntesis, o "(la grabación la hace siempre Nicolás)". |
| `docs/tabla_vigilante.md:165` | "(lo hace una persona, con la Go Board conectada" | Implica que el resto lo hace algo que no es una persona. | "(lo hace Nicolás, con la Go Board conectada" |
| `docs/bitacora/p4.md:5`; `docs/bitacora/p7.md:5`; `docs/estado.md:91` y `:248` | "otra sesión trabaja P5 en la carpeta principal"; "quedan para otra sesión"; "la otra sesión" | Sesiones de trabajo en paralelo sobre la misma carpeta; ambiguo, pero se lee como trabajo automatizado. | "otro integrante trabaja P5"; "quedan para después" |
| `docs/autoprueba.md:6`; `docs/checklist_26nov.md:7`; `docs/tabla_vigilante.md:101`; `docs/extension_isa.md:240`; `docs/bitacora/p0.md:5`; `docs/decisiones.md:376`; `docs/estado.md:515` | "la puerta de placa del plan (sección 16.4)"; "plan del proyecto, sección 16.4"; "El plan pide..."; "sección 16.0 del plan"; "sección 16.8 del plan" | Citan un "plan" con secciones numeradas que no está en el repositorio. Un lector no puede seguir la referencia. | Citar `docs/puertas.md` o la decisión T correspondiente de `docs/decisiones.md`. |

## 3. `informe/informe.tex` y lo que entra desde `informe/generado/`

El registro es parejo (primera persona plural, impersonal en las descripciones) y creíble para un alumno. Hallazgos:

| Archivo:línea | Tipo | Texto | Reescritura sugerida |
|---------------|------|-------|----------------------|
| `informe.tex:206` | Error (concordancia) | "cierra en 1 semillas" (macro `\pSieteDobleSemillas`) | "cierra en 1 de 10 semillas" |
| `informe/generado/t33amdahl.tex:6` y `:13` | Error (tilde, sale en el PDF) | "con el CPI que estimo la clase 7" | "que estimó la clase 7" |
| `informe/generado/t33amdahl.tex:9` a `:12` y `:16` a `:19`; `t33escalera.tex:7`, `:9`, `:11` y `:12`; `roofline.tex:19` y `:21` | Error (tilde, sale en el PDF) | "extension" (14 veces) | "extensión". Los textos vienen de las descripciones de `tools/p7/tablas.py` y de los CSV de `docs/mediciones/p7/`. |
| `informe/generado/t32.tex:4` | Sugerencia (símbolo de unidad) | "Tiempo (us)" | "Tiempo ($\mu$s)", como en `informe.tex:124` |
| `informe.tex:177`; notas de `t33amdahl.tex` y `t33variantes.tex` | Sugerencia (jerga interna) | "en P1"; "(T105)"; "(56 en el fondo, T100)" | "en la primera medición del segmentado"; quitar los códigos de decisión |
| `informe.tex:144` | Sugerencia (registro) | "Dónde se van los ciclos" | "En qué se gastan los ciclos" |
| `informe.tex:153` | Sugerencia (registro) | "actualizar la media se lleva la mayor parte del kernel" | "el estimador (desviación y actualización de la media) concentra la mayor parte del kernel" |
| `informe.tex:211` (rama del fondo) | Sugerencia (claridad) | "la elección pesa el co-diseño sobre los puntos esperados" | "la elección privilegia el co-diseño por sobre los puntos esperados" |

## 4. `README.md`

Bien escrito y en el registro pedido. Dos detalles:

| Archivo:línea | Tipo | Texto | Reescritura sugerida |
|---------------|------|-------|----------------------|
| `README.md:28` | Sugerencia (anglicismo) | "El power-on reset largo" | "El reset de encendido largo", que es el término del resto del repositorio |
| `README.md:118` | Sugerencia (precisión) | "compra cuando el precio cae 3 unidades bajo su media" | "cae más de 3 unidades" (la regla es `p < m - 3`) |

## 5. `docs/defensa/*.md`

El kit está escrito con frases cortas y directas, adecuadas para estudiar. Lo que un profesor notaría:

| Archivo:línea | Tipo | Texto | Reescritura sugerida |
|---------------|------|-------|----------------------|
| `cifras.md:12`, `:38`, `:93` y `:100`; `fondo.md:110` y `:111`; `espino_base.md:53`; `verificacion.md:128`; `preguntas.md:23`, `:263`, `:475`, `:639` y `:655` | Sugerencia (símbolo de unidad) | "9,5 us", "164 us", "2,8 uJ" | "µs", "µJ" |
| `extension.md:40`; `preguntas.md:407`; `fondo.md:11`; `verificacion.md:120` | Sugerencia (registro y propiedad de las decisiones) | "por la regla de Nicolás"; "la decisión T50 de Nicolás"; "por decisión de Nicolás (opción a)" | "por decisión del grupo". En la defensa los tres responden por todas las decisiones, y la atribución personal se lee como escrita por alguien que le reporta a Nicolás. |
| `resumen.md:11`; `fondo.md:11` | Sugerencia (registro) | la cita "opción b, tomemos riesgos" | Describir la decisión sin la cita coloquial: "se priorizó el diseño integrado aunque agregue riesgo". |
| `fondo.md:91`; `preguntas.md:9`; `plan_estudio.md:38`; `resumen.md:19` | Sugerencia (tono) | "tiene respuesta honesta"; "La respuesta es honesta"; "respuestas honestas"; "que hay que decir sin rodeos" | Quitar los adjetivos sobre la propia honestidad: la respuesta se juzga sola. |
| `fondo.md:23` y `:44`; `preguntas.md:439` | Sugerencia (calco de "paper trading") | "puntaje en papel"; "ganó en papel" | "puntaje simulado"; "ganó en la simulación" |
| `extension.md:14` y `:111`; `preguntas.md:387` y `:391` | Sugerencia (concordancia coloquial) | "Un desplazamiento por una constante ... son cables" | "se implementa solo con cableado" |
| `algoritmo.md:15`, `:62`, `:109` y `:112`; `preguntas.md:95` y `:346`; `barrel.md:43`; `extension.md:44`; `segmentado.md:69` | Sugerencia (registro coloquial) | "chico", "chica", "más chicas", "el core más chico" | "pequeño", "menor" |
| `algoritmo.md:128`; `preguntas.md:27`, `:74`, `:467` y `:519`; `fondo.md:85`; `barrel.md:54`; `tabla_vigilante.md:44`, `:100` y `:112` | Sugerencia (registro coloquial) | "de verdad" (11 veces) | "real", "realmente", "efectivamente" |
| `fondo.md:30`; `preguntas.md:83`, `:435` y `:499`; `algoritmo.md:58`; `tabla_vigilante.md:99` | Sugerencia (registro) | "votan adentro", "todo adentro o todo afuera", "contaría como afuera" | "votan comprar", "todo comprado o todo en caja" |
| `verificacion.md:13` | Sugerencia (frase de efecto) | "Una prueba que nunca falla no prueba nada." | "Si una prueba nunca falla, no hay evidencia de que detecte errores." |
| `tabla_vigilante.md:52` y `:79`; `plan_estudio.md:23` y `:39` | Sugerencia (muletilla) | "de punta a punta" | "completo" |

## 6. Documentos de estudio de `docs/*.md`

Estos 21 archivos se leyeron completos. Las tildes están bien fuera de los bloques de código. Lo que más se repite es el registro coloquial chileno, algunos anglicismos en prosa y "us" en vez de µs. Cada patrón repetido se informa una vez, con los ejemplos.

### 6.1 Errores

| Archivo:línea | Texto | Reescritura sugerida |
|---------------|-------|----------------------|
| `docs/codiseno.md:359` | "sea que el programa respondió en 22 ciclos o en 443" | "ya sea que el programa responda en 22 ciclos o en 443" |
| `docs/codiseno.md:359` | "no es la velocidad sino qué algoritmo cabe" | "no es la velocidad, sino qué algoritmo cabe" |
| `docs/tabla_vigilante.md:213` | "¿Qué habría pasado si no se simulaba el bitstream?" | "si no se hubiera simulado el bitstream" |
| `docs/tabla_vigilante.md:55` y `:214` | "la tabla de verdad" (por "la tabla real") | "la tabla definitiva". En eléctrica, "tabla de verdad" es otra cosa. |
| `docs/autoprueba.md:257` | "el vigilante gasta 5 y el reset de R0 0,164 ms" | "el vigilante gasta 5 ticks y el reset de R0, 0,164 ms" |
| `docs/espino_barrel.md:140` y `:276` | "en un ciclo distinto que en el base" | "en un ciclo distinto del del base" |
| `docs/checklist_26nov.md:33`; `docs/pendientes_nicolas.md:14` | "Pin del FPGA"; "pines 65, 64, 63 y 62 del FPGA" | "de la FPGA", como en el resto del repositorio |
| `docs/ensamblador.md:7`, `:38`, `:40`, `:87`, `:163` y `:183` | "el assembler" (6 líneas) en un documento cuyo título dice "ensamblador" | "el ensamblador" |
| `docs/gemelo.md:40`, `:41`, `:52`, `:53` y `:121`; `docs/extension_isa.md:198` | "Branch no tomado", "los seis branches", "decide un branch" | "Salto condicional no tomado", "salto condicional" |
| `docs/trade_s.md:12` | "Mercado de la maestra, porte del testbench." | "traducido del testbench a Python" |
| `docs/ensamblador.md:253` | "(1 palabras, 4 bytes)" en la salida citada de `tools/pochoasm.py` | Corregir el singular en el mensaje del ensamblador o usar otro ejemplo. |
| `docs/fondo.md:362` | Dos "dos puntos" seguidos en una misma oración ("vale lo que la serie con que se corre y lo que dura: el del tope tampoco se detecta") | Partir en dos oraciones. |

A estos se suman las huellas de autoría y las citas al "plan" de la sección 2.

### 6.2 Contradicciones dentro de un mismo documento o entre documentos

No son de estilo, pero se notan al leer:

- `docs/codiseno.md:369` dice que la caída de frecuencia del segmentado está "medida, no investigada", y la sección 5 del mismo documento (`:152` en adelante) la investiga.
- `docs/tabla_vigilante.md:190` y `:191` dicen "Nada se ha probado en la placa" y que el tiempo de reconfiguración no está medido; la línea 140 del mismo documento da los 35,50 ms medidos el 16/11.
- `docs/espino_barrel.md:319` y `:341`, `docs/extension_isa.md:220` y `:263`: "nada se probó en la placa", desactualizado desde el 16/11 (`docs/mediciones/placa_16nov.md`). Lo mismo en el kit de defensa: ver `docs/auditorias/cifras.md`, E9 a E13.
- `docs/fondo.md:390` dice "Los scripts agregan OSS CAD Suite al `PATH`"; desde el 16/11 no lo hacen (`docs/pendientes_nicolas.md:20`, y el `Makefile` lo toma de `OSS_CAD_SUITE` o del `PATH`).

### 6.3 Sugerencias, por patrón

| Patrón | Dónde (ejemplos) | Reescritura sugerida |
|--------|------------------|----------------------|
| "us", "um²", "uJ" en vez de µs, µm², µJ (unas 50 veces en 11 archivos) | `docs/fondo.md:23` y `:272` a `:276`; `docs/codiseno.md:338` y `:344`; `docs/checklist_26nov.md:56` a `:59`; `docs/arbol_decision.md:14` y `:27`; `docs/trade_s.md:150` y `:163`; `docs/producto_2x2.md:183` | µs, µm², µJ |
| "chico/chica" (9), "de verdad" (15), "igual" por "aun así" (6), "de a" (5) | `docs/algoritmo.md:24` y `:226`; `docs/espino_barrel.md:78` y `:90`; `docs/extension_isa.md:115` y `:286`; `docs/espino_segmentado.md:208` y `:250`; `docs/tabla_vigilante.md:47` y `:57` | "pequeño", "real", "aun así", "uno a la vez" |
| "adentro/afuera" para la posición (21) | `docs/fondo.md:38`, `:52` y `:105`; `docs/trade_s.md:21` y `:22` | "comprado / en caja" |
| Calco "N veces más lento" (unas 8) | `docs/codiseno.md:29`; `docs/espino_barrel.md:152`; `docs/fondo.md:302` | "tarda N veces más en responder" |
| Calco "puntaje en papel" | `docs/fondo.md:48`, `:65` y `:79` | "puntaje simulado" |
| Calco "conducidas" (de *driven*) | `docs/arbol_decision.md:43`; `docs/checklist_1dic.md:61`; `docs/checklist_26nov.md:43` | "con la maestra ya fijando el nivel de las líneas" |
| Calco "empujar" (de *push*) | `docs/checklist_1dic.md:20`; `docs/peldano.md:44` | "subir los cambios (push)" |
| "foto del estado" | `docs/gemelo.md:188`, `:190` y `:236` | "instantánea del estado" |
| Frases de efecto o fórmula "no es X: es Y" (unas 20, sobre todo en `algoritmo.md` y `codiseno.md`) | `docs/gemelo.md:156` ("Porque no se confía: se compara."); `docs/extension_isa.md:105` ("no es lógica: son cables ... Eso es toda la extensión."); `docs/algoritmo.md:270` ("**No agrega nada.**") | Decirlo de forma descriptiva, una vez. |
| Negrita al comienzo de casi cada viñeta | `docs/algoritmo.md` (72 líneas), `docs/codiseno.md` (65), `docs/fondo.md` (47) | Dejar la negrita para términos que se definen. Usada en todas partes, el texto parece generado. |
| Tono autocomplaciente | `docs/codiseno.md:354` ("La tabla muestra con honestidad lo que eso significa") | "La tabla muestra lo que eso implica" |
| Anglicismos menores | `docs/espino_segmentado.md:125` y `:155` ("enable"); `docs/ensamblador.md:9` ("toolchain"); `docs/puertas.md:19` ("reportando"); `docs/puertas.md:115` y `:117` ("**PASS**" en una tabla en español) | "habilitación", "herramientas de compilación", "informando", "Pasa" |
| Terminología distinta para lo mismo | `docs/autoprueba.md:41`, `docs/comandos.md:42` ("caminata aleatoria") frente a "paseo aleatorio" en `algoritmo.md` y `protocolo.md`; `docs/protocolo.md` ("una candidata" y "cada candidato") | Unificar en "paseo aleatorio" y "candidato". |
| "pines sueltos" | `docs/autoprueba.md:257` y `:276`; `docs/tabla_vigilante.md:145` | "pines flotantes (en alta impedancia)" |
| Otros de registro, de a uno | `docs/algoritmo.md:393` ("dejaría sobre la mesa"); `docs/algoritmo.md:424` ("queda 26 abajo"); `docs/codiseno.md:6` y `:410` ("dónde se van los ciclos", "¿Dónde se va la energía?"); `docs/codiseno.md:30` y `:258` ("predice casi exacto"); `docs/extension_isa.md:107` ("sale casi gratis"); `docs/producto_2x2.md:177` ("se pasa por 11 celdas"); `docs/contingencia.md:42` ("caja chica") | "haría perder"; "queda 26 por debajo"; "en qué se gastan"; "casi con exactitud"; "cuesta muy poco"; "excede en 11 celdas"; "caja inicial pequeña" |
| Plural de siglas | `docs/espino_segmentado.md:48`, `docs/espino_barrel.md:237` ("LEDs", "LUTs") | El enunciado usa "LUTs"; es aceptable. Solo conviene ser consistente dentro de cada documento. |
| `docs/ensamblador.md:157` | "✓" | Quitar el símbolo. |

## 7. Resumen

| Alcance | Errores | Sugerencias |
|---------|---------|-------------|
| Rayas largas (todos los archivos) | 0 | 1 (`--` de las tablas generadas) |
| Menciones de IA y huellas de autoría (todo el repositorio) | 8 filas (14 lugares) | 0 |
| `informe/informe.tex` y `informe/generado/` | 3 (con 16 apariciones de tildes faltantes) | 5 |
| `README.md` | 0 | 2 |
| `docs/defensa/*.md` | 0 | 11 |
| `docs/*.md`, documentos de estudio | 12, más 4 contradicciones | 17 patrones |

Lo más importante:

1. Las huellas de autoría: `docs/bitacora/p1.md:56` ("subagente"), `docs/estado.md:183`, `docs/pendientes_nicolas.md` completo, `docs/autoprueba.md:102`, `docs/tabla_vigilante.md:165` y las citas a un "plan" con secciones 16.x que no está en el repositorio.
2. Lo que se ve en el PDF del informe: "1 semillas" (`informe.tex:206`) y las 16 palabras sin tilde de las tablas generadas ("estimo", "extension").
3. "tabla de verdad" con el sentido de "tabla real" en `docs/tabla_vigilante.md`, que un profesor de eléctrica lee de otra forma.
4. Los dos errores gramaticales de `docs/codiseno.md:359` y `docs/tabla_vigilante.md:213`.
5. Uniformar µs y bajar el registro coloquial ("chico", "de verdad", "adentro/afuera") en el kit de defensa, que es lo que los tres van a leer en voz alta.
