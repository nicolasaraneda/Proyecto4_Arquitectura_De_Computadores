# Espino segmentado: el pipeline de 3 etapas

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio para la defensa. Resume y ordena `docs/espino_segmentado.md`, que es la fuente completa. El segmentado **no compite**: es una variante medida del punto 3.3 y la más rápida por hilo. Hay que saber explicarlo porque es la comparación natural con el barrel y con lo que estimó la clase 7. Cifras de `docs/mediciones/espino_segmentado.txt`, `docs/mediciones/paralelo_largo.txt` y `docs/mediciones/p7/variantes.txt`.

## 1. El problema: atacar el CPI

El Espino base gasta un ciclo de cada dos esperando que el banco de registros entregue los operandos (`docs/defensa/espino_base.md`, sección 2). Si las direcciones `rs1` y `rs2` estuvieran listas antes del flanco, el banco podría leer en ese mismo flanco y la espera desaparecería. Eso es un pipeline: mientras una instrucción se ejecuta, la siguiente ya se buscó y ya leyó sus operandos.

En términos de la ley de hierro, el segmentado no cambia el IC (misma ISA) ni Tclk (25 MHz fijos): baja el CPI.

| Clase | Base | Segmentado | Clase 7, estimado |
|-------|------|------------|-------------------|
| ALU, store, salto no tomado | 2 | 1 | 1 |
| load | 3 | 2 | 2 |
| salto tomado, `jal`, `jalr` | 3 | 2 | 3 |
| Mix de la clase 7 | 2,350 | 1,350 | 1,5 |
| MIPS con el mix | 10,64 | 18,52 | 16,7 |

Fuente: `docs/mediciones/espino_segmentado.txt`, secciones 2 y 3.

## 2. Por qué en la FPGA no es directo

En nuestro Proyecto 3 (ASIC) la memoria de instrucciones era combinacional: la instrucción aparecía en el mismo ciclo y el banco podía leer durante el fetch. En la FPGA la memoria es BRAM con lectura registrada: la instrucción sale **después** del flanco. Se evaluaron dos caminos:

- **Camino A, el que quedó.** La memoria de instrucciones lee en el **flanco de bajada**, medio ciclo después de que cambia el contador de programa. Su salida está estable en la segunda mitad del ciclo y en el flanco de subida siguiente el banco ya lee con las direcciones de esa instrucción. IF ocupa la primera mitad del ciclo e ID la segunda.
- **Camino B.** Una ROM combinacional solo con `trade.s`, en LUTs. Funciona (`make equiv-rom`), cuesta 61 celdas más y 4 BRAM menos.

El tercer camino, el del libro (una etapa de fetch de un ciclo completo), es el que supone la clase y por eso estima 3 ciclos para el salto tomado. No se construyó: con el camino A el salto tomado cuesta 2.

## 3. Las tres etapas

| Etapa | Cuándo | Qué hace | Dónde |
|-------|--------|----------|-------|
| IF | Del flanco de subida al de bajada | `pc_q` direcciona la memoria; la BRAM lee en la bajada | `rtl/espino_core/espino_if_stage.v`, `rtl/pochoco_ram.v:69` (bloque `g_neg`) |
| ID | Del flanco de bajada al de subida | `instr_next_i` entrega `rs1` y `rs2` al banco y pasa por el decodificador; en la subida se registra todo | `rtl/espino_core/espino_id_stage.v:128` (bloque `g_pipe`) |
| EX | Un ciclo completo | ALU, salto, acceso a memoria y escritura del banco. El load ocupa dos ciclos | `rtl/espino_core/espino_id_stage.v`, `espino_alu.v`, `espino_load_store_unit.v` |

**La copia de la memoria.** Yosys no reparte en BRAM un arreglo con un puerto de lectura en el flanco de subida y otro en el de bajada: lo convertía en 16 000 flip-flops. Con dos arreglos que reciben las mismas escrituras sí lo hace (`mem_f`, `rtl/pochoco_ram.v:71`). No cuesta BRAM adicionales: cada BRAM del iCE40 tiene un solo puerto de lectura, así que la memoria ya estaba duplicada. Son 8 bloques en los dos casos (decisión T34).

## 4. Riesgos de datos y de control

En el base no hay riesgos porque cada instrucción lee el banco después de que la anterior terminó. En el segmentado la instrucción i+1 lee el banco **en el mismo flanco** en que la i escribe.

| Riesgo | Solución | Dónde |
|--------|----------|-------|
| Escritura seguida de lectura del mismo registro: la BRAM entrega el valor viejo | Adelantamiento de un nivel: en ese flanco se guarda el dato escrito (`wdata_q`) y un bit por puerto (`fwd_a_q`, `fwd_b_q`); un multiplexor a la salida de la BRAM lo elige | `rtl/espino_core/espino_register_file.v:88` a `:113` |
| Carga seguida de uso | Durante el primer ciclo de la carga el core se detiene y el banco no lee (`rf_rd_en_o = advance`). La lectura ocurre en el flanco en que la carga escribe, y el adelantamiento entrega el dato | `rtl/espino_core/espino_id_stage.v:205` |
| `jal` o `jalr` seguido de uso del enlace | El enlace se escribe en el ciclo del salto; el destino entra a EX dos ciclos después. No hace falta nada | |
| Escritura a x0 | `wr` excluye la dirección 0 de la escritura y del adelantamiento | `rtl/espino_core/espino_register_file.v:71` |
| Salto tomado | La instrucción que venía detrás entra a EX inválida (`valid_d = ~pc_set_i`): es la burbuja | `rtl/espino_core/espino_if_stage.v:50` |
| Programa que se modifica a sí mismo | La copia del fetch recibe las mismas escrituras; mismo comportamiento que el base | `rtl/pochoco_ram.v:69` |

Dos detalles que suelen preguntar:

- **El mismo enable del banco resuelve dos problemas.** Si el banco releyera durante la espera de la carga, la ALU perdería los operandos de la carga y la LSU alinearía el byte con una dirección equivocada. Es la mutación `MUTA_RDEN` (`rtl/espino_core/espino_id_stage.v:199`).
- **Lectura y escritura en el mismo flanco.** Lo que entrega la BRAM en ese caso depende del hardware. El diseño no depende de eso: justo en ese caso el multiplexor elige el dato guardado.

## 5. Costo y recortes

| | Celdas | Fmax mín. | Fuente |
|-|--------|-----------|--------|
| Base | 1083 | 42,43 | `docs/mediciones/espino_segmentado.txt`, sección 1 |
| Segmentado con contador de 32 bits | 1174 | 48,43 | idem |
| Segmentado final, contador de 11 bits | 994 | 51,13 | idem |
| Base en P7 (mismo core, SoC con más variantes) | 1091 | 41,93 | `docs/mediciones/p7/variantes.txt` |
| Segmentado en P7 (mismo core, SoC con más variantes) | 990 | 45,34 | `docs/mediciones/p7/variantes.txt` |

El pipeline cuesta 91 celdas (adelantamiento: 32 flip-flops y 64 LUT). Recortar el contador de programa al ancho real de la memoria (11 bits para 512 palabras) recupera 180. El resultado es más pequeño que el base y más rápido: la decodificación salió de la ruta crítica. La clase advertía que el multiplexor de adelantamiento podía bajar la frecuencia; medido, queda en la ruta crítica pero la ruta completa es más corta.

La caída a 45,34 MHz de mínima (51,59 en P1, `docs/mediciones/barrel/recursos.txt`) no es de diseño. Se investigó (T127, `docs/mediciones/p7/caida_segmentado.txt`): la lógica es la misma (equivalencia formal), pero desde el commit `c293cf4` Yosys entrega otra netlist equivalente que nextpnr rutea peor. Con el mismo RTL leído en otro orden la mediana va de 47,88 a 53,59 MHz. Sigue cerrando 40 de 40 semillas a 25 MHz.

## 6. Qué mide en `trade.s` y por qué no compite

| | Base | Segmentado |
|-|------|------------|
| Respuesta promedio / peor (ciclos) | 41 / 44 | 22 / 26 |
| Speedup de la respuesta | 1,00 | 1,86 |
| MOPS logrado del kernel (8 operaciones útiles) | 3,92 | 7,41 |

Fuente: `docs/mediciones/p7/variantes.txt`.

No compite por la decisión T50: compite el fondo en el barrel. Si la métrica fuera la latencia de una sola regla, ganaría el segmentado, y con la extensión todavía más (17,25 ciclos predichos, `docs/codiseno.md`, sección 1). Pero la latencia no cambia el patrimonio mientras la respuesta llegue antes del tick siguiente.

## 7. Verificación

| Prueba | Resultado | Fuente |
|--------|-----------|--------|
| `make formal-base` | Las etapas IF e ID en modo base son equivalentes a las del curso: 1376 puntos | `docs/espino_segmentado.md`, sección 9 |
| `make paralelo-largo` | 1 600 000 instrucciones aleatorias comparadas una por una contra el base, en cada contador (11 y 32 bits), 628 583 distintas (39 %), cero diferencias | `docs/mediciones/paralelo_largo.txt` |
| `make riesgos` | Programas de riesgos del Proyecto 3 (`sw/hazard_test.s` con 56 comprobaciones, `sw/hazard_review.s` con 48) en base, segmentado y ROM | `docs/espino_segmentado.md`, sección 9 |
| `make mutaciones` | 5 de 5 errores puestos a propósito detectados (`MUTA_FWD`, `MUTA_LOADUSE`, `MUTA_RDEN`, `MUTA_X0`, `MUTA_SQUASH`) | idem |
| `make cosim-seg` | RTL contra el gemelo con `--pipeline`, trazas idénticas ciclo a ciclo | `docs/gemelo.md`, sección 2 |
| `make equiv-seg` | 20 000 ticks idénticos a `ref/trader.py` | `docs/espino_segmentado.md`, sección 9 |

Un hallazgo que conviene contar: la verificación del 13/11 informaba 1,3 millones de instrucciones comparadas, pero solo 4 644 eran distintas (0,4 %), porque el generador de programas aleatorios caía en un punto fijo. Se corrigió el generador (decisión T52) y se repitió. Es un ejemplo de por qué una cifra de verificación se acompaña de una medida de cobertura.

riscv-formal se evaluó y no se hizo (decisión T42): falta la interfaz RVFI y excluir los chequeos de shifts, que Espino no implementa.

## 8. Preguntas típicas

1. **¿Por qué 3 etapas si una instrucción de ALU demora 1 ciclo?** Etapas y ciclos por instrucción son cosas distintas: hay tres etapas trabajando a la vez sobre instrucciones distintas. IF e ID ocupan medio ciclo cada una (`docs/espino_segmentado.md`, sección 4).
2. **¿Por qué el salto tomado cuesta 2 y la clase dice 3?** La clase supone una etapa de fetch de un ciclo completo con dos instrucciones detrás del salto. Aquí hay una sola, que se anula (`rtl/espino_core/espino_if_stage.v:50`).
3. **¿Qué es el adelantamiento y dónde está?** Un registro con el dato que se escribe y un bit de coincidencia por puerto; un multiplexor lo elige a la salida de la BRAM (`rtl/espino_core/espino_register_file.v:99` a `:113`).
4. **¿Por qué basta un nivel?** La instrucción escribe al final de EX y la siguiente lee en ese mismo flanco. Una dependencia a distancia 2 ya lee la BRAM actualizada.
5. **¿Qué riesgo tiene el medio ciclo?** Que la BRAM y la decodificación no alcancen en 20 ns. Mide a lo más 9,8 ns en las 10 semillas (`docs/espino_segmentado.md`, sección 8).
6. **¿Cómo saben que las pruebas detectan errores?** Por las cinco mutaciones bajo `ifdef` en el RTL, por ejemplo `MUTA_SQUASH` (`rtl/espino_core/espino_if_stage.v:45`) y `MUTA_LOADUSE` (`rtl/espino_core/espino_id_stage.v:189`).
7. **¿Sigue siendo Espino?** Misma ISA, decodificador, ALU, LSU e interfaces. Con `Pipeline = 0` cada módulo genera la lógica original, y `make formal-base` lo prueba.
8. **¿Por qué no compite si es el más rápido?** Porque compite el fondo (T50) y la latencia no da patrimonio. Con `max_media` responde en 22 ciclos de 2262: el resultado sería el mismo que con R0.
