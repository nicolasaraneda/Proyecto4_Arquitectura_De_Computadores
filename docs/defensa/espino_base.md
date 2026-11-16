# El Espino base: el core del curso y cómo se mide

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio para la defensa. Es el punto de partida de todo lo demás: R0, el respaldo de la escalera, es este core sin cambios con `sw/trade.s`. Los documentos de origen son `docs/trade_s.md`, `docs/espino_segmentado.md` (secciones 2 y 10) y `docs/gemelo.md` (sección 2). Las cifras salen de `docs/mediciones/base.txt`, `docs/mediciones/espino_segmentado.txt`, `docs/mediciones/ticks_software.txt` y `docs/mediciones/p7/variantes.txt`.

## 1. El problema, en lenguaje de la clase

La ley de hierro dice que el tiempo de un programa es IC × CPI × Tclk. En la Go Board el reloj está fijo en 25 MHz (Tclk = 40 ns) porque el encapsulado VQ100 no tiene PLL (`docs/mediciones/pll_nextpnr.txt`). El IC lo pone el programa. Lo único que el core puede mejorar es el CPI, y para eso hay que entender de dónde sale el CPI del Espino base.

La regla de costo del Espino base, medida y no supuesta:

| Clase de instrucción | Ciclos | Por qué |
|----------------------|--------|---------|
| ALU, `lui`, `auipc`, store, salto no tomado | 2 | Un ciclo de espera del banco de registros, que es BRAM con lectura registrada, y uno de ejecución |
| load | 3 | Además la memoria de datos es registrada: un ciclo más esperando el dato |
| salto tomado, `jal`, `jalr` | 3 | La instrucción que ya se buscó detrás del salto se descarta |

Con el mix de la clase 7 esto da CPI 2,35, que es lo que la clase estimó, y medido en nuestro RTL da 2,350 (`docs/mediciones/espino_segmentado.txt`, sección 3). Ppeak = 25 MHz × 0,5 instrucciones por ciclo × 1 operación × 1 núcleo = 12,5 MOPS.

## 2. Las dos fases de cada instrucción

El Espino base no es un pipeline: cada instrucción pasa por dos estados, uno detrás del otro.

1. **Flanco N.** La memoria de instrucciones (BRAM con salida registrada) entrega la instrucción. Recién ahora se conocen `rs1` y `rs2`.
2. **Ciclo N.** Se presentan `rs1` y `rs2` al banco de registros. El banco es otra BRAM con lectura registrada: hay que esperar un flanco. Esa espera es el registro `ops_valid_q`.
3. **Flanco N+1.** El banco entrega los operandos y se levanta `rf_ready`.
4. **Ciclo N+1.** La ALU calcula, el controlador avanza el contador de programa, y en el flanco siguiente se escribe el resultado.

Dónde se ve en el RTL:

| Qué | Dónde |
|-----|-------|
| El ciclo de espera del banco (`ops_valid_q`), solo en el modo base | `rtl/espino_core/espino_id_stage.v:209` a `:213` |
| `rf_ready_o` es `ops_valid_q`: sin operandos no se avanza | `rtl/espino_core/espino_id_stage.v:233` |
| El controlador: se detiene si el banco no está listo o la LSU está ocupada, y salta solo con operandos listos | `rtl/espino_core/espino_controller.v:24` a `:30` |
| El ciclo extra del load (`busy_o` sube una vez por load) | `rtl/espino_core/espino_load_store_unit.v:45` y `:53` |
| El ciclo extra del salto tomado: la instrucción siguiente entra inválida (`valid_d = ~pc_set_i`) | `rtl/espino_core/espino_if_stage.v:50` |
| El banco de registros: dos copias en BRAM, una por puerto de lectura | `rtl/espino_core/espino_register_file.v:75` y `:81` |
| Cada copia son dos `SB_RAM40_4K` de 16 bits | `rtl/espino_core/espino_register_file.v:34` y `:45` |
| Los desplazamientos están deshabilitados: `sll`, `srl` y `sra` se ejecutan como suma | `rtl/espino_core/espino_alu.v:72` |

**Por qué la BRAM y no flip-flops.** Un banco de 16 registros de 32 bits en flip-flops son 512 flip-flops más sus multiplexores de lectura; la clase lo estimó en cerca del 40 % de la FPGA. En BRAM no cuesta celdas lógicas, pero obliga a esperar un flanco para leer. Es el compromiso que fija el CPI de 2.

**Por qué no hay shifter.** El shifter completo no cabe: habilitarlo da 1491 celdas de 1280 y nextpnr no lo puede ubicar (`docs/mediciones/base.txt`, sección 2).

## 3. El SoC alrededor del core

`rtl/pochoco_soc.v` junta el core, la memoria unificada de 512 palabras (`rtl/pochoco_ram.v`), los periféricos de la placa (`rtl/pochoco_periph.v`) y el esclavo SPI (`rtl/pochoco_spi_slave.v`).

| Pieza | Dónde | Lo que hay que saber |
|-------|-------|----------------------|
| Reset de encendido de 4095 ciclos (164 us) | `rtl/pochoco_soc.v:114` | Viene del Proyecto 2: con el reset original de 15 ciclos la BRAM entregaba ceros en la placa (decisión T3). En el testbench hace que el programa no vea los primeros precios |
| Instancia del core base (sin definiciones) | `rtl/pochoco_soc.v:156` | Con `-DESPINO_BARREL` se instancia el barrel en `:140` |
| Decodificación de direcciones (`spi_sel`, `per_sel`) | `rtl/pochoco_soc.v:176` y `:177` | Está en la ruta crítica de todos los cores |
| Esclavo SPI | `rtl/pochoco_soc.v:262` | El testbench lo mira por jerarquía (`dut.u_spi.byte_done`): no se renombra |
| Precio completo: `byte_done` en el octavo flanco de subida de SCLK | `rtl/pochoco_spi_slave.v:74` | El testbench cuenta los ciclos de respuesta desde aquí |
| Leer `PRICE` baja la bandera de precio nuevo | `rtl/pochoco_spi_slave.v:106` | |
| Escribir `DECISION` deja el byte en `tx_hold` | `rtl/pochoco_spi_slave.v:113` | |
| El byte sale cuando baja `CS_n` de la transacción siguiente | `rtl/pochoco_spi_slave.v:81` y `:82` | Por eso el byte que la maestra lee en el tick n responde al precio n-1 |

Los tres sincronizadores de 3 flip-flops del esclavo (`rtl/pochoco_spi_slave.v:47`) son los que hacen que la maestra pueda ser asíncrona respecto de nuestro reloj.

## 4. Cómo se mide el CPI

No se supone: se mide con un testbench que cuenta instrucciones completadas y ciclos, y se compara con el modelo de costo.

- `tb/tb_cpi.sv` (`make cpi`) cuenta IC, ciclos, loads, stores y saltos tomados y no tomados, y comprueba que **ciclos = 2 × IC + loads + saltos tomados**, con diferencia de 0 ciclos en los tres programas del repositorio base (`docs/mediciones/base.txt`, sección 4).
- `make medir-espino` repite lo mismo con `sw/trade.s`, el mix de la clase 7 (`sw/mix_clase7.s`) y un programa aleatorio, y da la tabla de costo por clase (`docs/mediciones/espino_segmentado.txt`, sección 2).
- `make medir-ticks` mide por tick lo que pide el punto 3.2: IC, ciclos, CPI y tiempo, promedio y peor caso, en las tres rondas (`docs/mediciones/ticks_software.txt`).
- El gemelo digital (`ref/gemelo/gemelo.c`) usa la misma tabla de costo y está validado contra el RTL con trazas idénticas ciclo a ciclo (`docs/gemelo.md`, secciones 2 y 3).

## 5. `sw/trade.s` en el core base: el tick de R0

El programa está explicado bloque por bloque en `docs/trade_s.md`. Lo que conviene tener en la cabeza:

| Bloque | Dónde | Instrucciones | Ciclos |
|--------|-------|---------------|--------|
| Sondeo de `STATUS` (vuelta de 8 ciclos) | `sw/trade.s:91` | 3 | 7 la que detecta |
| Leer `PRICE` | `sw/trade.s:97` | 1 | 3 |
| `32 p` con cinco sumas y `dev = 32 p - S` | `sw/trade.s:100` a `:106` | 6 | 12 |
| Decidir sin saltos (`slti`, `or`, `and`) y armar el byte | `sw/trade.s:109` a `:115` | 7 | 14 |
| Un solo store a `DECISION` | `sw/trade.s:118` | 1 | 2 |
| Actualizar la media con la memoria como desplazador (`sw` y `lbu`) | `sw/trade.s:121` a `:128` | 8 | 17 |
| Volver al sondeo | `sw/trade.s:129` | 1 | 3 |

Mediciones por tick (`docs/mediciones/ticks_software.txt`, resumidas en `docs/trade_s.md`, sección 6):

| Ventana | IC prom. | IC peor | Ciclos prom. | Ciclos peor | CPI |
|---------|----------|---------|--------------|-------------|-----|
| Respuesta (de `byte_done` a `DECISION`) | 19,5 | 21 | 41,0 | 44 | 2,10 |
| Tick completo (hasta volver a sondear) | 28,5 | 30 | 63,0 | 66 | 2,21 |

El peor caso de respuesta barriendo las 8 fases del sondeo es 49 ciclos, con el primer precio (`docs/puertas.md`, criterio 4 de R0). Contra los 2262 ciclos de la ronda 3 es el 2,2 %.

**Por qué hay peor caso si no hay saltos que dependan del precio.** El algoritmo tarda siempre lo mismo. Lo que varía es en qué punto de la vuelta de sondeo (8 ciclos) llega el precio. El testbench tiene un período de 2500 ciclos, que no es múltiplo de 8, así que recorre solo 4 fases: 38, 40, 42 y 44 ciclos.

## 6. Recursos de R0

| | Valor | Fuente |
|-|-------|--------|
| Celdas lógicas | 1083 de 1280 (P0) y 1091 (P7, mismo RTL, ruido de síntesis T6) | `docs/puertas.md`, `docs/mediciones/p7/variantes.txt` |
| BRAM | 12 de 16: 8 de la memoria (dos copias, una por puerto) y 4 del banco | `docs/espino_segmentado.md`, sección 6 |
| Frecuencia máxima en 10 semillas | Mínima 42,43 MHz (P0) o 41,93 (P7) | las mismas |
| Repositorio del curso sin cambios | 1065 celdas, 12 BRAM, mínima 42,66 MHz | `docs/mediciones/base.txt`, sección 1 |

La ruta crítica pasa por el banco de registros, la ALU y la decodificación de la dirección del bus. Con 42 MHz de mínima hay holgura de sobra a 25 MHz, pero la holgura no se puede convertir en velocidad porque no hay PLL.

`make formal-base` prueba con los pases `equiv_*` de Yosys que las etapas IF e ID del core de R0 son equivalentes a las del repositorio del curso: lo que agregamos para el segmentado no cambia el base (`docs/espino_segmentado.md`, sección 6).

## 7. Preguntas típicas

1. **¿Por qué el Espino base tiene CPI 2 si no hay riesgos?** Porque el banco de registros es BRAM con lectura registrada: cada instrucción espera un ciclo a sus operandos (`ops_valid_q`, `rtl/espino_core/espino_id_stage.v:209`). No es un riesgo, es una espera estructural.
2. **¿Por qué el load cuesta 3?** La memoria de datos también es registrada: la LSU levanta `busy_o` un ciclo (`rtl/espino_core/espino_load_store_unit.v:53`) y el controlador detiene el core (`rtl/espino_core/espino_controller.v:26`).
3. **¿Y el salto tomado?** La instrucción buscada detrás del salto se marca inválida (`rtl/espino_core/espino_if_stage.v:50`) y se pierde un ciclo.
4. **¿Cómo saben que el CPI es ese?** `make cpi` y `make medir-espino` cuentan IC y ciclos en simulación y comprueban `ciclos = 2 × IC + loads + tomados` con diferencia 0 en todos los programas (`docs/mediciones/base.txt`, sección 4).
5. **¿Cuál es el CPI de `trade.s`?** 2,10 en la respuesta y 2,21 en el tick completo (`docs/mediciones/ticks_software.txt`). Medido con el sondeo, 2,652 (`docs/mediciones/espino_segmentado.txt`), porque el lazo de espera tiene un load y un salto tomado por vuelta.
6. **¿Qué parte del tick consume más ciclos?** Actualizar la media: 17 de 58 ciclos sin la espera, por el desplazamiento hecho con `sw` y `lbu` (`sw/trade.s:125` y `:126`). En el tick completo a 0,1 ms, esperar: 98 % (`docs/codiseno.md`, sección 1).
7. **¿Cómo desplazan a la derecha sin shifter?** Multiplicando por 8 con tres sumas, guardando la palabra y leyendo su segundo byte con `lbu`: `x >> 5 = (8 x) >> 8` (`sw/trade.s:121` a `:126`). Para el número con signo usan la identidad `(32 p - S) >> 5 = p - ((S + 31) >> 5)`.
8. **¿Por qué el testbench dice 44 y ustedes 49?** El testbench solo recorre 4 de las 8 fases del sondeo. Barriendo todas, el primer precio, que pasa por el bloque `primero` (`sw/trade.s:77`), llega a 49 (`docs/gemelo.md`, sección 4).
9. **¿Qué cambiaron del core del curso?** Para R0, nada en la lógica: `make formal-base` lo prueba. El SoC tiene el reset de encendido largo (`rtl/pochoco_soc.v:114`) y tres salidas nuevas del esclavo SPI que solo usa el vigilante.
