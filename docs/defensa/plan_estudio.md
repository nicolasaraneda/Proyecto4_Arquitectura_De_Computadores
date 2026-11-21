# Plan de estudio para la defensa (16/11 al 1/12)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

El enunciado dice que en la defensa "se harán preguntas sobre cualquier parte del informe, del algoritmo, del assembly y del RTL" y que **todos los integrantes deben poder responder**. La defensa vale 1,0 de 6,0. Este plan reparte quién es dueño de cada pieza, fija lo que los tres tienen que dominar, y deja sesiones de repaso cruzado con el banco de preguntas (`docs/defensa/preguntas.md`) y un ensayo con preguntas al azar.

## 1. Hitos

| Fecha | Hito | Consecuencia para el estudio |
|-------|------|------------------------------|
| Lun 16/11 | Kit de defensa listo | Empieza la lectura individual |
| Dom 22/11 | Fecha de corte del diseño integrado | Si R1 no tiene la puerta de simulación, R0 es el titular: el foco de la defensa cambia (sección 6) |
| Mié 25/11 | Congelamiento del hardware, etiqueta `v-maestra-26nov` | Las cifras de hardware ya no cambian |
| **Jue 26/11** | **Maestra real** | Se suman a la defensa los resultados de la placa y las respuestas del ayudante |
| Dom 29/11 | Congelamiento total | Se regenera `cifras.md` si cambió algo; el banco queda fijo |
| Lun 30/11 | Ensayo general de las rondas y de la defensa | Ensayo con preguntas al azar (sección 5) |
| **Mar 1/12** | Entrega 10:00, competencia y defensa 10:30 | |

## 2. Quién domina qué

La propuesta del encargo (Nicolás el RTL y la verificación, Vicente el algoritmo y el co-diseño, Santiago el fondo, el vigilante y la operación del día) se mantiene, con dos ajustes:

1. **`sw/trade.s` pasa a Vicente.** El punto 3.2 del enunciado (assembly y mediciones por tick) está pegado al algoritmo: punto fijo, cómo se hace la división sin shifter, por qué no hay saltos que dependan del precio, y qué parte consume más ciclos, que es la entrada del perfil y de Amdahl del punto 3.3. Así Vicente cubre completos los puntos 3.1, 3.2 y 3.3 del informe.
2. **`sw/fondo.s` es de Santiago entero**, incluido el assembly y no solo el protocolo. Y Santiago acompaña a Nicolás el 26/11: es el dueño de la operación del día y del árbol de decisión, y lo que se vea con la maestra es lo que va a tener que defender.

| Persona | Dueño de | Documentos de estudio | Preguntas del banco que responde en profundidad |
|---------|----------|-----------------------|--------------------------------------------------|
| Nicolás | Espino base, segmentado, barrel, extensión de la ISA, verificación (formal, mutaciones, gemelo, puertas) | `espino_base.md`, `segmentado.md`, `barrel.md`, `extension.md`, `verificacion.md`; fuentes `docs/espino_*.md`, `docs/extension_isa.md`, `docs/gemelo.md`, `docs/puertas.md` | Secciones 4, 5, 6, 7 y 10 (50 a 96 y 126 a 137), y de la 14 la 176, 177 y 179 |
| Vicente | Algoritmo, protocolo de evaluación, `sw/trade.s`, co-diseño (variantes, Amdahl, roofline, PLL, ASIC) | `algoritmo.md`, `espino_base.md` (sección 5); fuentes `docs/algoritmo.md`, `docs/protocolo.md`, `docs/trade_s.md`, `docs/codiseno.md` | Secciones 2, 3 y 11 (11 a 49 y 138 a 146), y de la 14 la 159, 163, 165 a 169, 173 a 175 y 183 |
| Santiago | `sw/fondo.s` (supervisor, gestores, memoria compartida, degradación), tabla, `icebram` y moldes, vigilante y relevo, operación del 26/11 y del 1/12 (medidor, árbol, checklists, `retune`) | `fondo.md`, `tabla_vigilante.md`; fuentes `docs/fondo.md`, `docs/tabla_vigilante.md`, `docs/contingencia.md`, `docs/arbol_decision.md`, `docs/checklist_26nov.md`, `docs/checklist_1dic.md` | Secciones 1, 8, 9 y 12 (1 a 10, 97 a 125 y 147 a 155), y de la 14 la 161, 162, 164, 171, 172, 178 y 180 a 182 |

"Dueño" quiere decir: responde cualquier pregunta [A] de su pieza con el `archivo:línea` en la mano, y es quien contesta primero si la pregunta va dirigida al grupo.

## 3. Lo que los tres tienen que poder explicar

Sin mirar nada, cada uno de los tres:

1. **Las preguntas [B] y [I] de todo el banco.** Son 91 de las 183: 57 [B] y 34 [I]. Las [I] tienen respuestas ya escritas: hay que decirlas así, sin esconder lo que se aceptó a sabiendas.
2. **El recorrido completo de un tick**: la maestra baja `CS_n` y manda el precio; `byte_done`; el programa sale del sondeo, lee `PRICE`, calcula `dev`, decide sin saltos, escribe `DECISION` una vez; el byte sale en la transacción siguiente y la maestra lo ejecuta al precio de ese tick. En R0 (`sw/trade.s:91` a `:129`) y en R1 (supervisor, gestores y votos, `docs/defensa/fondo.md`, sección 3).
3. **La escalera R0, R1 y R2**, qué hardware tiene cada peldaño y el árbol de decisión del 1/12 (`docs/arbol_decision.md`).
4. **La ley de hierro aplicada a cada pieza**: segmentado y barrel atacan el CPI, la extensión el IC, el PLL atacaría Tclk y no existe en el VQ100.
5. **Las cifras de `docs/defensa/cifras.md`** que están en negrita o que aparecen en las preguntas [B]: celdas y frecuencia de R0, R1 y R2; 41/44/49 y 223/443/444 ciclos; presupuestos 249 762, 24 762 y 2 262; 19,6 %; CPI 2, 1,350, 1 y 4; 25 973, 27 062, 6 497 y 10 000; +0,007 y -0,005; 0,7 % y 1,4 %; 35,50 ms medidos (53 de la hoja de datos) y 361 ticks; 110 y 115 kHz.
6. **Qué está probado y qué no** (`docs/defensa/resumen.md`): la puerta de simulación completa en los tres peldaños; en la placa, R2 a 0,1 ms y media hora sin disparo, el relevo medido en 35,50 ms y la mitad baja de la firma de R0 (`docs/mediciones/placa_16nov.md`); la maestra real, el 26/11.

## 4. Calendario de estudio

Cada sesión de repaso cruzado dura una hora: cada uno pregunta al otro sobre **la pieza que no es suya**, con el banco abierto. El que pregunta lee la pregunta, el otro responde en voz alta en unos 20 segundos, y el que pregunta compara con la respuesta escrita y anota si faltó el dato o el archivo.

| Fecha | Qué |
|-------|-----|
| Lun 16 a mié 18/11 | Lectura individual: `resumen.md`, `cifras.md`, `espino_base.md` y el documento de la propia pieza. Vicente y Santiago leen además `algoritmo.md` y `barrel.md` respectivamente |
| Mié 18/11 | **Repaso 1** (presencial o por llamada): sección 1 del banco y las [B] de las secciones 2 a 4. Objetivo: los tres responden el recorrido del tick y la escalera |
| Jue 19 a sáb 21/11 | Cada uno lee los documentos de las otras dos piezas: Nicolás `algoritmo.md` y `fondo.md`; Vicente `barrel.md`, `extension.md` y `fondo.md`; Santiago `segmentado.md`, `extension.md` y `algoritmo.md` |
| Sáb 21/11 | **Repaso 2**: secciones 2, 6 y 8 del banco, preguntadas cruzado (Nicolás pregunta algoritmo a Santiago, Santiago pregunta barrel a Vicente, Vicente pregunta fondo a Nicolás) |
| Mar 24/11 | **Repaso 3**: secciones 5, 7, 9 y 10, cruzado. Todas las [I] del banco, una vez cada una, con los tres presentes |
| Jue 26/11 | Maestra (Nicolás y Santiago). En la noche, Santiago anota en la plantilla del checklist lo visto y lo que respondió el ayudante |
| Vie 27/11 | Se agregan al banco las preguntas que salgan del 26/11 (resultado de cada peldaño, SCLK medido, lo que diga el ayudante sobre el warm boot, si dice algo). Se ajusta la sección 6 de este plan si compite R0 |
| Sáb 28/11 | **Repaso 4**: secciones 3, 11 y 12, cruzado. Repaso de `cifras.md` con tarjetas: uno dice la cifra, otro dice de dónde sale |
| Dom 29/11 | Congelamiento. Cada uno relee las preguntas que anotó como falladas en los repasos |
| **Lun 30/11** | **Ensayo general** (sección 5) |

## 5. Ensayo con preguntas al azar (30/11)

Simula la defensa. Unos 45 minutos.

1. Se sortean 30 números entre 1 y 183 (por ejemplo, `python3 -c "import random; print(sorted(random.sample(range(1, 184), 30)))"`). Se fuerza que entren al menos 8 de las [I].
2. Para cada número, se sortea quién responde entre los tres, **excluyendo al dueño de la pieza** en dos de cada tres preguntas. El enunciado exige que cualquiera responda cualquier parte.
3. 20 segundos para responder, con el dato y, si se puede, el archivo. Sin mirar.
4. Los otros dos anotan: bien, incompleta (faltó el dato o la fuente), mal.
5. Al final, cada pregunta incompleta o mal se vuelve a leer en voz alta con su respuesta escrita, y el dueño de la pieza explica lo que faltó.
6. Segunda vuelta de 10 preguntas al azar solo entre las que fallaron.

Criterio para dar el ensayo por bueno: ninguna [I] mal respondida, y a lo más 3 incompletas en total. Si no se cumple, se repite la segunda vuelta el 1/12 temprano, antes de la entrega.

Durante la defensa: tener abiertos `README.md`, `docs/puertas.md`, `docs/arbol_decision.md`, `docs/defensa/cifras.md` y el informe (`docs/checklist_1dic.md`, sección 5). Si preguntan por un número, el comando que lo produce está en el README (una sección por pieza) y en `docs/comandos.md`.

## 6. Si cambia lo que compite

| Si... | Cambia en la defensa |
|-------|----------------------|
| Compite R0 (corte del 22/11, R1 falla con la maestra o SCLK bajo 115 kHz) | El barrel, la extensión, el fondo y el vigilante pasan a ser la edición de exhibición, con todo lo medido. Las preguntas de las secciones 6 a 9 siguen valiendo para el punto 3.3 del informe. Santiago pasa a ser dueño también de `sw/trade.s` en la operación del día |
| Compite R1 (no se permite reconfigurar) | Las preguntas del vigilante pasan a ser de exhibición; la [I] 125 es la respuesta |
| Compite R2 | Sin cambios. Agregar el resultado del relevo en la placa |

En cualquier caso, la pregunta 3 del banco ("¿por qué compiten con un diseño que no suma puntos?") sigue siendo la más probable y la tienen que responder los tres igual.
