# Registro de decisiones

Cada decisión lleva su razón, las alternativas que se consideraron y lo que se perdió al elegir. Las decisiones técnicas se numeran en orden y no se borran: si una cambia, se agrega otra que la reemplaza.

## Decisiones de alcance (Nicolás Araneda)

Estas cuatro decisiones fijan el alcance del proyecto. La razón es la misma para todas y se copia textual:

> "lo más ambicioso posible, sin tener en consideración ninguna limitación. Si es más difícil en funcionamiento, eso forma parte tanto del README como de una defensa para elaborar y estudiar y dejar en el repo"

| N.º | Decisión |
|-----|----------|
| A1 | Pieza de autor: todas. Espino segmentado, extensión de la ISA, acelerador, verificación formal, verificación exhaustiva y guardia de régimen en vivo. |
| A2 | Perfil de riesgo: maximizar el patrimonio esperado. Ganar por diferencia pesa más que asegurar un lugar intermedio. |
| A3 | Algoritmo: la investigación más profunda que alcance, sin techo de complejidad, mientras lo que opere en la competencia sea lo que gana fuera de muestra. |
| A4 | La dificultad no es motivo para descartar nada. Lo difícil se documenta y se convierte en material de estudio para la defensa. |

Hay tres hechos que estas decisiones no cambian y con los que se planifica:

1. Las reglas del enunciado. La decisión la calcula Espino.
2. La FPGA tiene 1280 celdas lógicas y 16 BRAM.
3. La maestra real está disponible un solo día, el 26/11 (hasta el 13/11 la fecha era el 19/11: ver T44). El bitstream de competencia solo puede contener hardware que haya pasado esa prueba.

## Decisiones técnicas

### T1. El repositorio base se importa como una copia, sin su historial (12/11)

- **Decisión.** El primer commit contiene los archivos de `nic0villegasc/pochoco_soc` en su commit `33e8b5a`, sin ningún cambio. Se comprobó que el árbol de archivos es idéntico al del commit original. Ese commit quedó con la etiqueta `base-curso`.
- **Razón.** El historial de este repositorio debe mostrar solo el trabajo del grupo. El crédito al autor original va en el README y en los encabezados de cada archivo, que se conservan intactos.
- **Alternativas.** Hacer un fork o conservar los cinco commits originales.
- **Qué se pierde.** El historial del repositorio base ya no se ve desde aquí. Queda el enlace y el identificador del commit para consultarlo.

### T2. El ensamblador es el del Proyecto 2, con el nombre `tools/pochoasm.py` (12/11)

- **Decisión.** El testbench oficial pide `python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex`, y el repositorio base no trae ese archivo. Se trajo el ensamblador que el grupo escribió en el Proyecto 2, con sus 73 tests. La interfaz ya coincidía. Los módulos quedaron en `tools/asm/`.
- **Razón.** Ya está probado contra los `.hex` del repositorio base, rechaza los shifts que la ALU no implementa y lo conocemos entero, que es lo que hace falta para agregarle las instrucciones de la extensión de la ISA.
- **Alternativas.** Esperar un `pochoasm.py` del curso, o usar el toolchain GNU con el `sw/Makefile` del repositorio base.
- **Qué se pierde.** Si el curso publica su propio `pochoasm.py`, habrá que comprobar que el nuestro genera lo mismo. Queda como pregunta para el ayudante.
- **Consecuencia.** Se eliminó `sw/Makefile`, para que exista una sola forma de generar los `.hex`. El toolchain GNU no podría ensamblar las instrucciones propias.

### T3. Power-on reset de 4095 ciclos, parametrizado (12/11)

- **Decisión.** El contador de reset de `pochoco_soc` pasa de 4 a 12 bits. El ancho queda en el parámetro `PorBits`.
- **Razón.** Lo medimos en la placa en el Proyecto 2: con el reset de 15 ciclos las BRAM del iCE40 todavía no entregan datos válidos después de configurar, el core lee ceros y el programa parte por la mitad. En este proyecto eso significaría saltarse la inicialización del algoritmo.
- **Alternativas.** Mantener los 15 ciclos del repositorio base, o buscar en la placa el reset más corto que funciona.
- **Qué se pierde.** Cerca de 10 a 20 celdas (ver T6 sobre el ruido de esa cifra). Además, en el testbench oficial la primera transacción empieza a los 4 us y el reset termina a los 164 us. Con período de 0,1 ms los precios de los ticks 0 y 1 llegan durante el reset y el programa no los ve. Con 1 ms y con 10 ms se pierde solo el tick 0. El testbench igual entrega 4/4, porque el esclavo SPI en reset no levanta `byte_done`. En la competencia la placa está encendida mucho antes del primer precio, así que no se pierde ninguno.
- **Consecuencia.** La referencia en Python tendrá que modelar esos ticks iniciales para que la equivalencia sea exacta. El algoritmo debe partir bien desde cualquier precio inicial, que es algo que ya se exige por otros motivos.
- **Pendiente.** Se puede medir en nuestra propia placa, sin la maestra, cuál es el reset más corto que arranca bien. Con 63 ciclos (`PorBits = 6`) el testbench no perdería ningún precio.

### T4. `sw/trade.hex` es el programa por defecto y se elige con `chparam` (12/11)

- **Decisión.** El valor por defecto de `MemFile` pasa de `"../sw/blink.hex"` a `"sw/trade.hex"`, relativo a la raíz del repositorio. El `Makefile` además fija el programa al sintetizar con `chparam -set MemFile`.
- **Razón.** Cualquier forma de sintetizar el diseño debe producir un bitstream con el programa de competencia. Con `chparam` se pueden generar bitstreams con otros programas sin tocar el RTL. Se comprobó que el contenido de las BRAM cambia con el programa elegido.
- **Alternativas.** Dejar el valor original, que solo funcionaba porque Yosys busca el archivo también en la carpeta del fuente.
- **Qué se pierde.** Nada. El testbench oficial siempre pasa `MemFile` de forma explícita.

### T5. `sw/trade.hex` queda versionado (12/11)

- **Decisión.** El `.hex` se sube al repositorio y `make check-hex` comprueba que corresponde a `sw/trade.s`.
- **Razón.** Es lo que queda dentro del bitstream. Quien revise el repositorio puede ver el programa exacto sin ensamblar nada, y la integración continua detecta si alguien cambió el `.s` sin regenerarlo.
- **Alternativas.** Tratarlo como un archivo generado y no subirlo.
- **Qué se pierde.** Hay que acordarse de regenerarlo en cada cambio. La comprobación automática lo recuerda.

### T6. El conteo de celdas tiene un ruido de unas 10 celdas (12/11)

- **Observación, no decisión.** El mismo diseño, sintetizado con cambios que no alteran la lógica (por ejemplo fijar un parámetro con `chparam` en vez de dejar su valor por defecto), dio entre 1063 y 1075 celdas. Con el reset de 12 bits dio 1083 y 1086.
- **Consecuencia.** Cuando se reporte cuántas celdas ahorra o cuesta un cambio, una diferencia menor que unas 10 celdas no se puede atribuir al cambio con una sola síntesis. Para los recortes del Espino segmentado habrá que medir cada uno con varias variantes del flujo o acumularlos.

### T7. Qué mejoras del Proyecto 2 se trajeron y cuáles no (12/11)

- **Se trajo.** El ensamblador con sus tests y su documento (T2), el reset largo (T3) y la idea de que el `.hex` sea prerrequisito de la síntesis.
- **No se trajo, por ahora.** El contador libre de ciclos de 32 bits (`CYCLES`, lectura en `0x8000_000C`) y el antirrebote de los interruptores. El contador sirve para que el programa mida el período entre precios y para la telemetría, pero cuesta del orden de 40 a 60 celdas y esa decisión corresponde al frente del co-diseño, cuando se sepa cuánto espacio queda. El antirrebote no hace falta mientras los interruptores sean solo de diagnóstico.
- **No aplica.** En el Proyecto 2 se había sacado el esclavo SPI para ganar espacio. Aquí es el periférico principal.

### T8. `trade.s` del primer tramo: comprar y mantener (12/11)

- **Decisión.** El primer `trade.s` espera el precio, lo lee y escribe siempre "comprar 63".
- **Razón.** Es lo mínimo que ejercita el camino completo: bandera de precio nuevo, lectura de `PRICE`, escritura de `DECISION`, salida por MISO y contabilidad del testbench. Como la maestra recorta la compra a lo que alcanza con la caja, repetir la orden no paga comisiones de más.
- **Resultado.** 4/4 en el testbench oficial. El `decisiones.csv` del testbench coincide fila por fila con el mercado de `ref/p4_baseline.py`.
- **Qué sigue.** Reemplazarlo por la regla base con equivalencia exacta.

### T9. La serie de práctica se versiona (12/11)

- **Decisión.** `tb/practica.csv` se sube al repositorio, aunque el `.gitignore` del repositorio base ignora todos los `.csv`.
- **Razón.** El testbench oficial la lee desde `tb/practica.csv` y todos los números del algoritmo salen de ella.
- **Aclaración.** La regla del enunciado prohíbe guardar series de precios dentro del diseño. La serie está en el repositorio solo como dato de prueba: ni el RTL ni `trade.s` la contienen.

### T10. El ensamblador pasa a ser el del Proyecto 3, con la directiva `.org` (13/11)

- **Decisión.** Se trajeron del ensamblador del Proyecto 3 las salidas en Verilog (`--vh` y `--rom`) con sus tests, y se agregó la directiva `.org dirección`, que rellena con ceros. `sw/trade.s` termina con `.org 0x800`, así que `trade.hex` tiene siempre 512 palabras. Reemplaza en parte a T2.
- **Razón.** En simulación una palabra que no está en el `.hex` queda indefinida y en la placa queda en cero: con el relleno las dos parten igual. Además `icebram` necesita un `.hex` del tamaño completo de la memoria. Las salidas en Verilog se van a usar en el frente del Espino segmentado, si se evalúa la ROM combinacional.
- **Alternativas.** Una opción `--pad` en la línea de comandos, o rellenar siempre. La primera no sirve porque el comando del testbench oficial no lleva opciones. La segunda rompe la comparación con los `.hex` del repositorio base.
- **Qué se pierde.** Nada. La suite pasa de 73 a 87 tests.

### T11. El desplazamiento a la derecha se hace con la memoria (13/11)

- **Decisión.** La regla base necesita `(32 p - S) >> 5`. En `trade.s` se calcula como `p - ((S + 31) >> 5)`, y el desplazamiento de `S + 31`, que es positivo, se hace multiplicando por 8 con tres sumas, guardando la palabra en memoria y leyendo su segundo byte con `lbu`. Cuesta 6 instrucciones y 13 ciclos.
- **Razón.** La ALU no tiene shifter y el shifter completo no cabe (116 % de la FPGA). Leer un byte de una palabra es un desplazamiento de 8 bits que el hardware ya tiene en la unidad de carga. El costo es fijo y no depende del dato.
- **Alternativas.** Un lazo que arma el resultado bit a bit (unas 24 instrucciones). Llevar la parte entera y la fracción de la media en registros separados y normalizar con restas sucesivas (pocas instrucciones en el caso normal, pero hasta 9 vueltas en el peor caso). Cambiar la regla por la suma móvil de 64, que no necesita desplazar pero rinde menos (24 143 contra 27 062 en la serie completa) y ocupa 64 palabras de memoria.
- **Qué se pierde.** Una palabra de RAM (`TMP`) y un store y un load por tick. Queda como el candidato natural para la extensión de la ISA: una instrucción de paso de media exponencial reemplaza las 8 instrucciones del bloque.

### T12. `trade.s` no tiene saltos que dependan del precio (13/11)

- **Decisión.** Las comparaciones se hacen con `slti` y la posición se actualiza con `or` y `and`. El byte de decisión se arma con aritmética. El único salto condicional es el del sondeo de `STATUS`.
- **Razón.** El trabajo por tick es constante: 27 instrucciones y 58 ciclos, sin contar la espera. El peor caso se puede enunciar sin buscar la peor entrada. También simplifica la verificación exhaustiva y el modelo de costo.
- **Alternativas.** Saltos condicionales, que ahorran 1 o 2 instrucciones en algunos caminos y agregan variación.
- **Qué se pierde.** Nada medible. La respuesta varía entre 38 y 44 ciclos solo por la fase del lazo de sondeo, que dura 8 ciclos. Eso no se puede eliminar sin interrupciones.
- **Detalle.** Si las dos condiciones se cumplieran a la vez, la forma sin saltos saldría y la forma con saltos entraría. Con umbrales en que entrar exige estar bajo la media y salir exige estar sobre ella, nunca se cumplen juntas. `ref/trader.py` rechaza parámetros en que podrían coincidir.

### T13. La referencia modela los precios que se pierden en el reset (13/11)

- **Decisión.** `ref/trader.py` recibe el período del testbench y calcula cuántos precios iniciales llegan durante el power-on reset (`ticks_perdidos`): 2 a 0,1 ms y 1 a 1 ms y a 10 ms. Esos precios no se entregan a la estrategia.
- **Razón.** La equivalencia debe ser byte a byte con el testbench oficial sin modificar, y el reset largo (T3) es parte del diseño.
- **Alternativas.** Acortar el reset para que el testbench no pierda precios (pendiente de T3, hay que medirlo en la placa), o comparar a partir del tick 3.
- **Qué se pierde.** El patrimonio del testbench en la serie completa (26 795 a 0,1 ms, 27 306 a 1 ms) no es el de la regla base viendo todos los precios (27 062). Los tres números salen de la misma referencia con distinto parámetro. Para evaluar el algoritmo se usa el caso sin pérdidas, que es el de la competencia.

### T14. Icarus es el simulador oficial y Verilator se usa para las corridas largas (13/11)

- **Decisión.** `make tb` y `make equiv-r3` usan Icarus, con los comandos del encabezado del testbench. Las corridas de 20 000 ticks a 1 ms y a 10 ms y las mediciones por tick usan Verilator, con la misma copia del testbench.
- **Razón.** Icarus demora 13 minutos en 20 000 ticks a 0,1 ms. A 10 ms serían unas 22 horas. Verilator es unas 50 veces más rápido y acepta el testbench oficial tal cual (`--binary --timing`).
- **Validación.** Las dos herramientas dan la misma traza ciclo a ciclo y el mismo `decisiones.csv`. Eso incluye el caso delicado: el testbench cambia `SCLK` en el mismo instante en que sube el reloj, y las dos resuelven esa coincidencia igual.
- **Qué se pierde.** Nada. Verilator viene en OSS CAD Suite.

### T15. Antes de programar la placa se simula el bitstream (13/11)

- **Decisión.** `make sim-bitstream` convierte el `.asc` del place and route en Verilog con `icebox_vlog` y lo simula por los pines con la maestra del testbench (`tb/tb_bitstream.sv`). Los bytes que lee la maestra se pasan por `ref/market.py` y el resultado debe ser idéntico al de la referencia.
- **Razón.** El testbench oficial simula el RTL, no lo que se graba en la placa. Esta prueba cubre la síntesis, el place and route y sobre todo el contenido inicial de las BRAM, que es donde va el programa. En el Proyecto 2 el problema que tuvimos en la placa fue justamente de arranque con las BRAM.
- **Alternativas.** Simular la netlist de Yosys (no cubre el place and route) o confiar en el flujo.
- **Qué se pierde.** Ocho minutos por bitstream con Icarus. No cubre el timing ni el comportamiento eléctrico: eso se prueba el 19/11.
- **Detalle.** `icebox_vlog` declara los puertos dos veces e Icarus lo rechaza. `tools/chip_vlog.py` reescribe solo el encabezado del módulo.

### T16. Los bitstreams de competencia se versionan con su hash (13/11)

- **Decisión.** Cada bitstream candidato queda en `bitstreams/` con su SHA-256 y una tabla con el commit, los recursos y las pruebas que pasó.
- **Razón.** El día de la competencia hay que grabar un archivo que ya se probó, no uno recién sintetizado. Con el hash se puede comprobar que el archivo de la placa es el que pasó por la maestra real.
- **Alternativas.** Regenerarlo cada vez con `make bin`. Con las mismas versiones el resultado es el mismo, pero depende de tener el entorno intacto ese día.
- **Qué se pierde.** 32 kB por bitstream en el repositorio.

### T17. El gemelo digital se escribe en C y se valida por trazas (13/11)

- **Decisión.** `ref/gemelo/gemelo.c` simula el SoC con exactitud de ciclo: el core por instrucción, con el ciclo exacto de cada acceso al bus y de cada escritura de registro, y el esclavo SPI flanco por flanco con la misma lógica del Verilog. Se valida con `make cosim`, que exige trazas idénticas a las del RTL.
- **Razón.** La simulación del RTL no alcanza para las rondas de 10 ms ni para miles de series: Icarus demoraría unas 22 horas en 20 000 ticks a 10 ms y Verilator 22 minutos. El gemelo demora 0,02 segundos. Python puro habría sido unas 100 veces más lento, y no hay numpy en el entorno.
- **Alternativas.** Usar solo Verilator (sirve para una corrida, no para la matriz de estrés ni para correr el binario en el protocolo). Un modelo por tick sin ciclos (no sirve para medir la respuesta ni para probar otros tiempos de SPI).
- **Qué se pierde.** Hay un segundo modelo del hardware que mantener. Cuando el core se segmente, hay que actualizar su tabla de ciclos y volver a validarlo. Hace falta un compilador de C para las pruebas.
- **Método.** La traza por eventos y la comparación con `cmp` vienen del `tb/core_trace_tb.v` y el `tb/comparar_trazas.py` del Proyecto 3.

### T18. El gemelo se salta las vueltas del sondeo que no cambian nada (13/11)

- **Decisión.** Cuando el contador de programa está en el lazo `lw`, `andi`, `beqz` sobre `STATUS` y no hay precio nuevo, el gemelo calcula en qué vuelta va a llegar y se salta las anteriores.
- **Razón.** El programa pasa más del 97 % del tiempo en ese lazo. Sin el atajo los 20 000 ticks a 10 ms toman 21 segundos y con el atajo 0,02.
- **Alternativas.** No optimizar, o reconocer el lazo por dirección. Se reconoce por el contenido de las tres instrucciones, para que siga funcionando si el programa cambia de lugar.
- **Qué se pierde.** Código más delicado. Se cubre comparando el resultado con y sin atajo en cada `make cosim`, incluidos los totales de instrucciones y de ciclos. Con `--traza` el atajo se desactiva.

### T19. El gemelo resuelve la coincidencia entre SCLK y el reloj igual que los simuladores (13/11)

- **Observación.** El testbench oficial sube `SCLK` exactamente en un flanco de subida del reloj de 25 MHz (5500 ns = 20 + 40 × 137). Qué ve el sincronizador depende del orden de los eventos en el simulador. Icarus y Verilator coinciden: el flanco ya ve el valor nuevo.
- **Decisión.** El gemelo usa esa resolución por defecto (`--borde 1`) y permite la contraria (`--borde 0`).
- **Consecuencia.** El peor caso que informa el testbench (44 ciclos) depende de esa coincidencia y de la fase del lazo de sondeo. Barriendo todas las fases, el peor caso real es 49 ciclos, en el primer precio. Las decisiones no cambian con ninguna de las dos resoluciones. En la placa la maestra es asíncrona y se dan los dos casos.

### T20. Protocolo de evaluación y criterio de aceptación (13/11)

- **Decisión.** Un algoritmo se evalúa con `ref/protocolo.py` sobre series de 2000 ticks: los 10 bloques de práctica, 1000 remuestreos por bloques de 100 incrementos y 200 series de cada una de 10 familias sintéticas. Una candidata reemplaza a la regla base solo si (a) en los bloques la media y el peor bloque son mayores o iguales, (b) en los remuestreos la media y el percentil 5 son mayores o iguales, y (c) en ninguna familia sintética la media baja más de 1 %.
- **Razón.** Fijar la vara antes de probar ideas. La regla base está casi en el máximo de su grilla sobre la serie completa, así que ese número ya tiene sesgo de selección.
- **Alternativas.** Mitad de la serie para ajustar y mitad para validar (quedan 5 bloques por lado, muy pocos). Pedir significancia estadística en vez de mayor o igual (queda como mejora: con 1000 remuestreos se puede calcular el error de la diferencia).
- **Qué se pierde.** El remuestreo por bloques conserva la dependencia dentro de 100 ticks y pierde la de más largo plazo: es más duro que la serie original para una regla de reversión. La tolerancia de 1 % y el largo del bloque son elecciones nuestras. Las familias sintéticas no están calibradas contra la serie de práctica: eso es parte del frente del algoritmo.
- **Primer resultado.** La suma móvil de 64 no reemplaza a la regla base: pierde en bloques y en remuestreos, aunque gana en las familias sintéticas (`docs/protocolo.md`).

### T21. Todo en Python estándar, sin numpy (13/11)

- **Decisión.** `ref/` usa solo la biblioteca estándar de Python. Lo que necesita velocidad va en C (el gemelo) o se reparte entre procesos con `multiprocessing`.
- **Razón.** El entorno no tiene numpy y no instalamos nada en el sistema. Además quien revise el repositorio lo puede correr sin preparar nada, y la integración continua tampoco instala paquetes.
- **Qué se pierde.** Los barridos grandes de parámetros serán más lentos que con vectores. La evaluación completa de una estrategia toma unos 5 segundos, que por ahora alcanza.

### T22. Los 20 000 ticks con Icarus salen del push y quedan como ejecución manual (13/11)

- **Decisión.** En cada push la equivalencia de los 20 000 ticks se comprueba con el gemelo digital (`make equiv-gemelo-20k`, a los tres períodos) y con Verilator sobre el RTL (`make equiv-verilator`, a 0,1 ms y 1 ms). La corrida con Icarus (`make equiv-r3`) queda como ejecución manual: en local, o en GitHub con `gh workflow run CI -f icarus_completo=true`.
- **Razón.** La integración continua demoraba 32 minutos y la mayor parte era esa corrida. Con dos frentes trabajando en paralelo, cada rama tiene que esperar la integración continua antes de entrar a `main`, y media hora por intento es demasiado.
- **Por qué no se pierde cobertura.** Verilator simula el mismo RTL con la misma copia del testbench y ya se comprobó que da la misma traza que Icarus (T14). El gemelo se valida contra el RTL en cada push con `make cosim`. El testbench oficial sin modificar sigue corriendo con Icarus en cada push (`make tb`, 2000 ticks), igual que las corridas cortas a 1 ms y 10 ms.
- **Alternativas.** Dejar todo como estaba, o correr Icarus solo en `main`. La segunda deja pasar a `main` un cambio que después falla ahí.
- **Qué se pierde.** Una diferencia entre Icarus y Verilator que solo aparezca después del tick 2000 no se vería en el push. Por eso la corrida manual se repite antes de cada etiqueta (`v-maestra-19nov` y `v-competencia`) y cada vez que cambie el RTL del core o del esclavo SPI.

### T23. El producto 2x2 se diseña como una instrucción con el paso completo del estimador (13/11)

- **Decisión.** La propuesta es `kal2 rd, rs1, rs2` en custom-0: `rs1` lleva el estado empaquetado `{u, m}` en dos carriles de 16 bits, `rs2` el precio, y la instrucción hace la resta `d = p - m`, el producto de la matriz 2x2 por `[d, u]` y la suma `m + dm`, con saturación. La especificación está en `docs/producto_2x2.md` y la definición ejecutable en `ref/mv2x2.py`. Por ahora es solo diseño y costo: no está en el SoC ni en el ensamblador.
- **Razón.** El filtro de Kalman de dos estados en estado estacionario es exactamente ese producto. Con la resta y la suma adentro el programa no tiene que armar ni separar carriles, que sin shifter cuesta un store y un load cada vez. La transitoria va en el carril alto para que un `slt` contra `{umbral, 0}` la compare sin desempaquetar.
- **Alternativas.** Un producto 2x2 genérico con la matriz en `rs2` (más general, pero pierde lo que ahorra en empaquetar y desempaquetar, y los coeficientes de 8 bits limitan la precisión). Un periférico MMIO que actualiza el estado al llegar el precio (es la forma barata en la FPGA, pero cada lectura es un load y hay que preguntar si cumple la regla de no reemplazar al procesador).
- **Qué se pierde.** La instrucción sirve para este estimador y no para un producto 2x2 cualquiera. El formato de los carriles (8 bits de fracción) lo fijamos antes de tener el estimador calibrado: si el frente del algoritmo usa otro, hay que regenerar.

### T24. Dos versiones del producto 2x2 y ninguna entra hoy a la edición de competencia (13/11)

- **Decisión.** Se diseñaron y midieron dos versiones que calculan lo mismo bit a bit: coeficientes fijos con sumas y desplazamientos cableados (generada por `tools/gen_mv2x2.py`, en forma factorizada) y multiplicadores reales con coeficientes programables (`rtl/exhibicion/mv2x2_mult.v`). Las dos quedan en la edición de exhibición. La primera apunta a la FPGA y la segunda a la edición ASIC.
- **Medición** (`make costo-mv2x2`). Coeficientes fijos: entre 160 y 396 LUT como módulo suelto según la precisión, y entre 217 y 368 celdas más en el SoC una vez integrada. El SoC base tiene 206 celdas libres, así que ni la más barata cabe (1291 de 1280). Multiplicadores reales: 1645 LUT con coeficientes de 8 bits y 3094 con 14 bits, más que toda la FPGA. En GF180 la versión fija ocupa entre 8 000 y 30 000 um² y la de multiplicadores entre 67 000 y 130 000 um².
- **Razón de la forma factorizada.** La matriz es de rango 1 más una diagonal, y calcular la innovación una sola vez deja tres productos por constante en vez de cuatro. Cuesta entre 26 % y 44 % menos LUT que la forma directa con la misma precisión.
- **Condición para entrar a la competencia.** Que el estimador de dos estados gane bajo el protocolo y que el hardware quepa junto al pipeline. La segunda hoy no se cumple. Para cumplirla habría que angostar los carriles, quitar la saturación o hacer una versión secuencial, y ninguna de esas está medida.
- **Qué se pierde.** Nada en la competencia: en la FPGA sobra tiempo (44 ciclos usados de 2262) y falta área, así que el estimador de dos estados puede correr en software. Se pierde mostrar este peldaño funcionando en la placa.
- **Actualización con el frente del algoritmo.** Con los coeficientes calibrados (`phi = 123/128`, `K1 = 5/8`, `K2 = 3/16`) la versión fija cuesta 251 LUT suelta, agrega 328 celdas integrada (1402 de 1280) y ocupa 14 776 um² en GF180. El estimador de dos estados no gana bajo el protocolo (T30). Las dos condiciones quedan en contra y el producto 2x2 se queda en la edición de exhibición.

### T25. El generador se modela como nivel más transitoria más redondeo, con dos regímenes (13/11)

- **Decisión.** El modelo de la serie de práctica es un nivel que pasea, una componente transitoria AR(1) y redondeo a enteros, con dos regímenes de volatilidad que escalan las dos varianzas por la misma razón y saltos de nivel poco frecuentes. Se ajusta por máxima verosimilitud con el filtro de Kalman (`ref/generador.py`) y las constantes quedan en `ref/calibracion.py`.
- **Razón.** Es el modelo más chico que reproduce a la vez la razón de varianza, la curtosis y la persistencia de la volatilidad. Con un solo régimen la curtosis sale 3 en vez de 14. Con parámetros separados por régimen la verosimilitud mejora 0,1: no se justifican.
- **Alternativas.** Reversión a una media fija (no explica que la razón de varianza se estabilice en 0,5), volatilidad estocástica continua o un modelo oculto de Markov ajustado por EM (más parámetros de los que 20 000 ticks pueden fijar).
- **Qué se pierde.** El modelo es gaussiano dentro de cada régimen. En la práctica las caídas grandes rebotan el doble que en el modelo, y la regla base gana 5 % en el modelo contra 8 % en el remuestreo. Por eso el modelo no se usa solo.

### T26. Las familias sintéticas se calibran con el modelo y se separan en plausibles y de estrés (13/11)

- **Decisión.** Todas las familias de `ref/series.py` salen del modelo calibrado, quitando, exagerando o reemplazando una pieza. Cuatro son plausibles y diez de estrés. Se agregaron `modelo`, `modelo_vecino`, `volatil` y `nivel_bajo`. Reemplaza la parte de T20 que decía que las familias no estaban calibradas.
- **Razón.** Con los parámetros puestos a mano, `reversion` daba 40 086 y `dos_componentes` 25 138 con la regla base: no decían nada sobre la competencia. Calibradas dan 11 513 y 10 772.
- **Alternativas.** Mantener las familias antiguas junto a las nuevas. Se descartó para no tener dos tablas con el mismo nombre de familia.
- **Qué se pierde.** Los números del protocolo del tramo 3 para las familias sintéticas ya no se reproducen (los bloques y los remuestreos sí). La verificación del binario pasa de 3010 a 3810 series.

### T27. Dos evidencias y una semilla reservada (13/11)

- **Decisión.** Una idea se acepta solo si mejora a la vez en el remuestreo de la serie real y en el modelo calibrado. Los parámetros se eligen con la semilla 0. Los finalistas se evalúan con la semilla 1, que no se miró para decidir nada. La comparación entrega la diferencia pareada con su error estándar.
- **Razón.** Se probaron unas 3000 combinaciones. El máximo de 3000 números con ruido es optimista aunque ninguna combinación sea mejor que otra. Además el remuestreo y el modelo se equivocan hacia lados distintos: el remuestreo hereda la suerte de la serie de práctica y el modelo no captura las caídas grandes.
- **Alternativas.** Partir la serie de práctica en mitad de ajuste y mitad de validación: quedan 5 bloques por lado y un solo tramo ruidoso por lado.
- **Qué se pierde.** Los 10 bloques de práctica no tienen reserva posible: se usaron para elegir la regla base original.

### T28. Para explorar se usa un motor en C validado contra la referencia en Python (13/11)

- **Decisión.** La familia paramétrica de estrategias está escrita dos veces: `candidatos.Trader` en Python, que es la referencia, y `ref/motor/motor.c`, que corre unas cien veces más rápido. `ref/test_candidatos.py` exige que coincidan serie por serie en los candidatos y en 60 combinaciones de parámetros al azar.
- **Razón.** Sin numpy, evaluar una configuración sobre 15 000 series toma decenas de segundos en Python y 0,3 segundos en C. La exploración completa son unas 1800 configuraciones.
- **Alternativas.** Solo Python con menos series (el ruido tapa diferencias de 1 %), o solo C (se pierde la referencia legible).
- **Qué se pierde.** Hay dos versiones que mantener iguales. La prueba lo vigila en cada push.

### T29. La guardia de régimen mide el resultado de las entradas, no un estadístico del precio (13/11)

- **Decisión.** La guardia es: tope de tiempo de 48 ticks por posición y, si tres posiciones seguidas terminan por ese tope, 1000 ticks sin operar. El tope de pérdida apaga la estrategia si la caída acumulada en unidades de precio, desde el mejor momento, pasa de la mitad del precio. El manejo de saltos corre la media cuando el precio cambia 8 o más en un tick.
- **Razón.** Un estadístico que detecte en vivo si la serie revierte no tiene potencia: en 2000 ticks la razón de varianza de una serie que revierte y la de un paseo aleatorio se traslapan casi enteras, y la evidencia a favor de la reversión es de una unidad de log-verosimilitud por ronda. Lo que sí se observa es si las entradas vuelven a la media.
- **Alternativas.** Guardia por tendencia con una media lenta de la desviación (para proteger tiene que activarse en más de la mitad de los remuestreos), tope de precio por posición (cuesta 5 % de media con 6 unidades), tope de pérdida de 25 % (salta en el 9 % de los remuestreos).
- **Qué se pierde.** La guardia cuesta 1 % de media en el remuestreo y 2 % en las familias plausibles. El tope cuesta otro 0,2 y 1,6 %, y casi toda la ganancia si la serie es mucho más volátil que la de práctica. Ninguno cubre un salto grande con la posición abierta.

### T30. El estimador de dos estados queda en la edición de exhibición (13/11)

- **Decisión.** El filtro de Kalman de dos estados en punto fijo (`est=1` en `candidatos.Trader`) no entra a la edición de competencia.
- **Razón.** Bajo el protocolo no reemplaza a la regla base: cumple en bloques y remuestreos por 0,3 % y baja más de 1 % en tres familias. Con la semilla reservada gana 30 ± 5 en el remuestreo y pierde 8 ± 8 en las familias plausibles. En software cuesta unas 140 instrucciones por tick contra 27.
- **Alternativas.** Aceptarlo por la ventaja en el remuestreo. Es del tamaño de lo que se gana o se pierde por elegir una banda vecina.
- **Qué se pierde.** Nada medible en patrimonio. Queda como el caso de uso del producto de matriz 2x2 en hardware, con su matriz en `docs/algoritmo.md`, sección 4.1.

### T31. `ref/trader.py` no cambia hasta que se elija un candidato (13/11)

- **Decisión.** La regla base sigue siendo la referencia oficial y el programa de la placa. Los candidatos viven en `ref/candidatos.py` y se presentan sobre la frontera entre media y percentil 5 (`docs/algoritmo.md`, sección 7).
- **Razón.** Ningún candidato cumple las tres condiciones del protocolo contra la regla base: los que suben la media bajan el peor bloque o una familia de estrés, y los que protegen bajan la media. La elección depende del perfil de riesgo y es de Nicolás.
- **Alternativas.** Fijar `max_media` por ser el de mayor media con significancia.
- **Qué se pierde.** Mientras no se elija, la equivalencia del RTL y el bitstream siguen siendo los de la regla base.


### T32. El core segmentado convive con el base y se elige al compilar (13/11)

- **Decisión.** El pipeline de 3 etapas vive en los mismos módulos del Espino, bajo el parámetro `Pipeline` de `pochoco_soc` (0 base, 1 segmentado con fetch en flanco de bajada, 2 segmentado con ROM combinacional). Su valor por defecto sale de las definiciones `ESPINO_SEGMENTADO` y `ESPINO_ROM`, y sin ninguna es 0: el core por defecto sigue siendo el base.
- **Razón.** El testbench oficial instancia `pochoco_soc` sin parámetros de variante y no se puede modificar, así que la variante se elige con una definición en la línea de comandos. Así el mismo testbench, las mismas copias parametrizadas y el mismo flujo de síntesis sirven para las dos variantes. Que sea el mismo módulo con un parámetro, como `EarlyRead` en el Proyecto 3, deja a la vista que sigue siendo Espino.
- **Alternativas.** Archivos separados para el core segmentado (duplica el decodificador y la ALU o los comparte igual). Cambiar el valor por defecto al segmentado (cambia lo que prueba el testbench oficial y el bitstream de competencia antes de pasar por la maestra).
- **Qué se pierde.** Los archivos del core base cambiaron de texto aunque no de lógica: con `Pipeline = 0` se genera el circuito original (1083 celdas, las mismas trazas ciclo a ciclo contra el gemelo, las mismas decisiones en 20 000 ticks), pero los nombres internos cambiaron y `make bin` ya no reproduce el hash de `bitstreams/competencia_v1.bin`, porque nextpnr ubica distinto. El archivo guardado no se tocó.
- **Cómo se cubre.** `make formal-base` prueba con los pases `equiv_*` de Yosys que, con `Pipeline = 0`, las etapas IF e ID (que incluyen el decodificador y la ALU) son lógicamente equivalentes a las del repositorio base: 266 y 1110 puntos de comparación, todos probados. Como control, con el contador de programa de 11 bits la misma prueba deja 42 puntos sin probar. No cubre `pochoco_ram.v` ni `espino_register_file.v`, que tienen memorias y cuyo cambio en el modo base es de cableado, ni el cableado de `espino_core.v` y `pochoco_soc.v`: eso lo cubren `make cosim` y `make equiv`.

### T33. La instrucción se lee en el flanco de bajada, desde BRAM (13/11)

- **Decisión.** De los dos caminos evaluados para tener la instrucción antes del flanco, se eligió leer la memoria de instrucciones en el flanco de bajada (`SB_RAM40_4KNR`). La ROM combinacional queda disponible y verificada con `-DESPINO_ROM`.
- **Razón.** Medido en 10 semillas: el flanco de bajada ocupa 994 celdas y 12 BRAM con 51,1 a 54,5 MHz, y la ROM 1055 celdas y 8 BRAM con 50,0 a 55,1 MHz. La BRAM cuesta 61 celdas menos y conserva el cambio de programa con `icebram` sin sintetizar de nuevo, que es parte del plan de contingencia.
- **Alternativas.** La ROM combinacional. Una etapa de fetch de un ciclo completo, que es el pipeline que estima la clase 7: no tiene rutas de medio ciclo, pero el salto tomado cuesta 3 ciclos en vez de 2.
- **Qué se pierde.** Hay rutas que disponen de medio ciclo. nextpnr las analiza con medio período (se comprobó con un diseño de prueba) y ninguna pasa de 9,8 ns de los 20 disponibles, pero el análisis supone un reloj con ciclo de trabajo de 50 %. Es lo primero que hay que revisar con la maestra real.

### T34. La memoria del fetch es una copia explícita (13/11)

- **Decisión.** `pochoco_ram` tiene un segundo arreglo, `mem_f`, que recibe las mismas escrituras y se lee en el flanco de bajada.
- **Razón.** Con un solo arreglo y puertos de lectura en flancos distintos, Yosys no usa BRAM y genera 16 384 flip-flops (47 551 celdas). Con dos arreglos mapea a 8 BRAM, las mismas que usa la memoria original, que también se duplica porque cada BRAM tiene un solo puerto de lectura.
- **Qué se pierde.** Nada en recursos. Hay dos `$readmemh` del mismo archivo, y `icebram` tendrá que reemplazar el programa en las dos copias: hay que verificarlo cuando se pruebe `icebram`.

### T35. Adelantamiento a la salida de la BRAM y lectura detenida durante la carga (13/11)

- **Decisión.** El banco de registros sigue en BRAM. Un registro guarda el dato que se escribe y un multiplexor a la salida lo elige cuando la dirección leída coincide con la escrita. Mientras una carga espera su dato el banco no lee.
- **Razón.** Es el diseño del Proyecto 3, adaptado: allá el banco era de flip-flops y el adelantamiento iba antes del registro de salida. En una BRAM el registro de salida está dentro del bloque, así que el multiplexor va después.
- **Alternativas.** Banco en flip-flops (480 flip-flops y dos multiplexores de 16 entradas: no cabe). Insertar una burbuja cuando hay dependencia (sube el CPI justo en el patrón más común de `trade.s`, calcular y usar). Fundir el adelantamiento con el multiplexor de operandos para sacar un nivel de lógica (no hizo falta: la ruta crítica mide 19,6 ns de 40).
- **Qué se pierde.** 32 flip-flops y 64 LUT, y un multiplexor más en la ruta de ejecución.

### T36. El contador de programa de 11 bits se aplica solo al segmentado (13/11)

- **Decisión.** El parámetro `PcW` vale 11 en el segmentado y 32 en el base.
- **Razón.** El recorte recupera 133 celdas en el base y 180 en el segmentado, pero cambia el circuito del base, y el bitstream de competencia no debe cambiar hasta pasar por la maestra.
- **Qué se pierde.** Fuera de las 512 palabras los dos cores ya no son idénticos: leen la misma instrucción, pero `auipc` y el enlace de `jal` entregan el contador recortado. `trade.s` no sale de la memoria. La ejecución en paralelo se corre también con el contador de 32 bits para comparar el resto del pipeline sin esa diferencia.

### T37. Recortes que se midieron y no se aplicaron (13/11)

- **Observación.** Quitar la decodificación que nadie usa movió el conteo entre 17 celdas menos y 12 más en el segmentado, según cómo se escribiera, y los registros de lectura de los periféricos ya los recorta la síntesis (0 celdas).
- **Decisión.** No se tocó el decodificador ni los periféricos. Es el ruido que describe T6, y el decodificador es compartido con el base.

### T38. Verificación del pipeline: tres comparaciones independientes y controles negativos (13/11)

- **Decisión.** El segmentado se compara contra el Espino base (trazas funcionales de los programas de riesgos del Proyecto 3, y ejecución en paralelo de dos SoC con programas aleatorios), contra el gemelo digital con su tabla de ciclos (ciclo a ciclo) y contra la referencia en Python (decisiones). Cinco mutaciones bajo `ifdef` comprueban que las pruebas detectan errores.
- **Razón.** Cada comparación cubre algo distinto: el base dice si el resultado es correcto, el gemelo dice si los ciclos son los esperados y la referencia dice si el trader decide igual.
- **Alternativas.** Mutar copias del RTL en vez de dejar `ifdef` en el código (como la revisión del Proyecto 3). Se prefirió el `ifdef` para que las mutaciones queden versionadas y corran con `make`.
- **Qué se pierde.** El RTL tiene cinco bloques `ifdef MUTA_*` que no se sintetizan nunca. La ejecución en paralelo deja el bus SPI quieto, porque con tráfico los dos cores leerían valores distintos al ir a distinta velocidad: el tráfico SPI se cubre con el gemelo.

### T39. Las cifras de timing son de nextpnr, no de icetime (13/11)

- **Observación.** Con una ruta de prueba entre una BRAM de flanco de bajada y un registro de flanco de subida, nextpnr informa `negedge -> posedge` y calcula la frecuencia como 1 / (2 × retardo). `icetime` informa el doble.
- **Decisión.** El cierre de timing se declara con nextpnr en 10 semillas (`make timing-seg`).

### T40. El gemelo lleva la tabla de ciclos de cada core (13/11)

- **Decisión.** `ref/gemelo/gemelo.c` acepta `--pipeline`: 1 ciclo por instrucción, 2 los loads y 2 los saltos tomados, contador de programa de 11 bits y lazo de sondeo de 5 ciclos. Sin la opción es el base. `make cosim-seg` lo valida contra el RTL.
- **Detalle.** Apareció un caso que el base no tiene: después de un store al esclavo SPI, la instrucción siguiente se completa en el ciclo inmediato, y el conteo de instrucciones por tick tenía que anticiparla. Lo encontró la comparación con programas aleatorios.

### T41. `hazard_cycles.s` lee los interruptores (13/11)

- **Decisión.** En el Proyecto 3 este programa leía el contador `CYCLES`, que este SoC no tiene (T7). Aquí lee `BTN` y el testbench cambia los interruptores en cada ciclo. Cada comprobación compara el valor usado en la instrucción inmediata con el mismo valor usado una instrucción después.
- **Qué se pierde.** El gemelo no modela interruptores que cambian, así que este programa no se compara ciclo a ciclo contra él.

### T42. riscv-formal queda documentado y sin hacer (13/11)

- **Decisión.** No se integró riscv-formal en este tramo. `docs/espino_segmentado.md` lista lo que falta: interfaz RVFI, envoltorio con el banco en flip-flops, excluir shifts y excepciones, y limitar los registros a 16.
- **Razón.** Es cerca de un día de trabajo y el plazo para el hardware que va a la maestra es el 18/11. Se priorizó la comparación contra el Espino base con 2,9 millones de instrucciones aleatorias y los controles negativos.

### T43. El bitstream del segmentado se guarda aparte (13/11)

- **Decisión.** `bitstreams/segmentado_v1.bin` es el SoC con el core segmentado y el mismo `trade.hex`. `competencia_v1.bin` no se tocó.
- **Pendiente.** Decidir si el segmentado va a la maestra real el 19/11 como candidato a la edición de competencia. Con la regla base no cambia el patrimonio. Sí libera 89 celdas y deja la respuesta en 26 ciclos en vez de 44.

### T44. El calendario se corre una semana (13/11)

- **Decisión.** Todas las fechas del proyecto se mueven una semana. La maestra real está disponible el 26/11, y la entrega y la competencia son el 1/12 (10:00 y 10:30). El plan interno se corre igual: el hardware que quiera llegar a la competencia se etiqueta el 25/11 en la noche (`v-maestra-26nov`), del 27 al 29/11 solo se aceptan cambios que no tocan el hardware probado, el 29/11 se congela y el 30/11 es el ensayo general.
- **Razón.** Cambio de fechas del curso, informado por Nicolás el 13/11. El enunciado en PDF (`docs/Proyecto_4_arq.pdf`) todavía muestra las fechas anteriores, 19/11 y 24/11.
- **Consecuencia.** Donde las decisiones anteriores dicen 18/11, 19/11 o 24/11 debe leerse 25/11, 26/11 y 1/12, y la etiqueta `v-maestra-19nov` pasa a llamarse `v-maestra-26nov`. Las decisiones anteriores no se reescriben. Se corrigió la fecha en `bitstreams/README.md`, `docs/gemelo.md` y `docs/espino_segmentado.md`.
- **Qué se gana.** Siete días más antes de la prueba con la maestra real.

### T45. Tramo de factibilidad del fondo de estrategias en un chip, en rama aparte (13/11)

- **Encargo de Nicolás, textual.** "Quiero un diseño integrado y mucho más radical, aceptando el riesgo de área. Este tramo es de factibilidad: prototipos mínimos y mediciones, sin integrar nada en main."
- **Decisión.** Todo el tramo vive en la rama `factibilidad-fondo` y en la carpeta `factibilidad/`, una subcarpeta por pieza con su README, su Makefile y sus mediciones. Los prototipos copian los fuentes que necesitan cambiar. Ningún archivo de `rtl/`, `sw/`, `ref/`, `tb/` ni `tools/` se modificó, y el flujo de `make` de la raíz y la integración continua no conocen la carpeta.
- **Criterios de corte, fijados por Nicolás antes de medir.** Una pieza de hardware se descarta de la edición de competencia si no cabe junto al SPI o no cierra a 25 MHz en 10 semillas. Una pieza de algoritmo se descarta si no mejora los puntos esperados del torneo sin empeorar el percentil 5. Lo descartado se documenta con sus números y pasa a la edición de exhibición o a la ASIC.
- **Alternativas.** Construir el diseño integrado directamente sobre `main`, con una bandera de compilación como se hizo con el segmentado.
- **Qué se pierde.** Los prototipos no pasan por la integración continua, y lo que se decida llevar a `main` hay que integrarlo aparte: mover a `rtl/` y `tb/`, enseñarle las instrucciones al ensamblador y al gemelo, y rehacer la equivalencia.

### T46. El retorno se mide en puntos de torneo, con tres vistas y semillas reservadas (14/11)

- **Decisión.** Las estrategias se comparan con el arnés de `factibilidad/retorno/`, bajo tres hipótesis de puntaje: patrimonio, exceso sobre comprar y mantener, y torneo contra un campo de rivales sorteado. El enunciado dice que el resto de los grupos "se repartirá de forma lineal según su posición relativa": es ambiguo, así que el torneo se evalúa lineal en patrimonio (H3a) y lineal en el puesto (H3b). La referencia a superar es `max_media` y no la regla base.
- **Rondas largas.** A 20 000 ticks las series de prueba tocan los límites 1 y 255 y las medias se inflan. Un resultado a ese largo vale solo si tiene el mismo signo con las series interiores y con la vista de parada, que corta cada serie cuando el precio sale de 21 a 249.
- **Semillas.** La 0 es de exploración. La 2 se usó una vez para los candidatos del estudio 1 y 2, y la 3 una vez para la lista final del estudio 4, fijada antes. Las auditorías las volvieron a correr sin elegir nada con ellas: una confirmación nueva pide otra semilla.
- **Rivales.** Nadie sabe qué van a programar los otros grupos. Se usaron siete campos, desde uno ingenuo hasta uno en que todos traen una reversión ajustada. El nivel de puntos cambia mucho con el campo (0,87 a 1,67 de 2 para la regla base) y el signo de las diferencias entre candidatos no.
- **Qué se pierde.** El criterio es más exigente que el protocolo de T20 y deja fuera piezas que protegen el patrimonio en series con tendencia. Toda la evidencia sigue saliendo de la serie de práctica o del modelo ajustado a ella.

### T47. Veredictos del tramo de factibilidad (15/11)

Resultado de aplicar los criterios de T45. No cambia nada en `main`: qué se construye lo decide Nicolás con `docs/estado.md`.

- **Pasan el criterio de hardware.** El Espino barrel de 4 hilos (934 celdas), la extensión de la ISA en sus subconjuntos (`emad`, y `emad` con `devk` y `mulstep`), el vigilante con SB_WARMBOOT y las cuatro configuraciones integradas, incluida I1 "fondo en un chip" (1071 celdas, 13 BRAM, 46,8 MHz de mínima).
- **No pasan el criterio de hardware.** El duplicador de reloj (con un ciclo de trabajo real cierra 1 de 10 semillas), el conjunto completo de la extensión (2505 celdas), los carriles en unidad aparte con `divstep` sobre el barrel (1312) y una memoria de 1024 palabras completa (20 BRAM).
- **Pasa el criterio de algoritmo.** `max_media` contra la regla base, y `max_media` con supresión de compras residuales (`ejec:m=8`) contra `max_media`, confirmada con la semilla reservada en cinco campos de rivales.
- **No pasan el criterio de algoritmo.** El fondo de estrategias en todas sus formas (90 variantes y el fondo completo), el reparto de capital según desempeño en papel, la tabla de política que aprende, el predictor de patrones, el ancla en comprar y mantener, la guardia, el tope de pérdida y las bandas anchas.
- **Consecuencia.** El hardware no es lo que limita al fondo en un chip. Lo descarta de la competencia el criterio de algoritmo: con una sola estrategia el barrel decide igual que los otros cores y responde más lento.

### T48. `ejec:m=8` queda condicionada a tres confirmaciones (15/11)

- **Observación.** La supresión de compras residuales lleva un espejo de la contabilidad de la maestra, con caja inicial 10 000 y comisión 5. Vale +0,007 puntos esperados. Si la caja real fuera 12 000 perdería 21 de patrimonio por ronda de 2000 ticks y 640 por ronda de 20 000. Con caja 20 000 pierde 3 % y 19 %. Con comisión 0 pierde 13 y 986.
- **Decisión.** No se recomienda para la edición de competencia mientras el ayudante no confirme caja 10 000, comisión 5 y reset de la placa antes de cada ronda. Sin eso la estrategia recomendada es `max_media` sola, que no supone nada.
- **Qué se pierde.** 0,007 puntos esperados si las condiciones eran las del testbench y no se preguntó a tiempo.

### T49. El generador de programas aleatorios cae en un punto fijo (14/11)

- **Observación.** Al verificar el barrel se vio que los programas de `tools/prog_aleatorio.py` llegan pronto a un lazo corto: de 960 721 instrucciones ejecutadas, solo 130 771 eran distintas. La verificación del barrel usó un generador corregido (`factibilidad/a_barrel/tools/prog_hilos.py`: registros que avanzan en cada vuelta y saltos que no caen en un `jalr`).
- **Consecuencia.** Las 1 300 756 instrucciones de `make paralelo-largo` del Espino segmentado (T38) valen menos de lo que dice el conteo. No se encontró ningún error, pero la cobertura real es menor.
- **Pendiente.** Llevar la corrección al generador del repositorio y repetir `make paralelo-largo`. Importa más si el segmentado termina siendo el core de la competencia.

### T50. Compite el fondo en un chip: opción b (15/11)

- **Decisión de Nicolás, con su razón textual.** "opción b, tomemos riesgos".
- **Qué significa.** Compite el diseño integrado: Espino barrel de 4 hilos con el fondo mínimo, la extensión de la ISA, la tabla de parámetros en BRAM y el vigilante. Es la opción 4 de la tabla comparativa de la factibilidad (`docs/estado.md`, tramo 6): 1071 celdas, 13 BRAM y 46,8 MHz de frecuencia mínima medidos. El algoritmo base pasa a ser `max_media` (T51). Se construye una escalera de bitstreams para la maestra del 26/11: R0 (core base con `max_media`, el respaldo), R1 (fondo en un chip sin vigilante) y R2 (con vigilante). Compite el peldaño más alto que pase las tres puertas: simulación, placa y maestra.
- **Riesgo aceptado a sabiendas.** Según lo medido, este diseño no suma puntos esperados contra `max_media` sola (+0,007 a 2 000 ticks y -0,005 a 20 000) y agrega riesgo de falla en vivo. Se elige por lo que representa como co-diseño.
- **Alternativa descartada.** La recomendación del tramo de factibilidad (opción 2): segmentado con `emad` y `max_media`, con el barrel y el fondo en la edición de exhibición.
- **Qué se pierde.** Entre 16,5 y 18,5 días de persona de los 33 que quedaban hasta el 25/11, y margen para reaccionar a una falla de placa. Quedan fuera de la competencia, con sus números: compras residuales (`ejec:m=8`), guardia, tope de pérdida, ancla en comprar y mantener, aprendizaje en vivo, predictor de patrones y doble frecuencia.
- **Fecha de corte.** Si el 22/11 a medianoche R1 no pasó completa la puerta de simulación, R0 pasa a ser el titular y el fondo va a la edición de exhibición.

### T51. `max_media` reemplaza a la regla base en `trade.s` y en la referencia (15/11)

- **Decisión.** `sw/trade.s` entra cuando `dev < -96` (3 unidades bajo la media) en vez de `dev < -128`. Es la única línea de código que cambia. En `ref/trader.py`, `MaxMedia` es la estrategia oficial (`trader.Oficial`) y la que usan `correr`, la línea de comandos, `tools/equiv.sh`, `tools/equiv_gemelo.sh`, `tools/sim_bitstream.sh` y `ref/protocolo.py --binario`. `ReglaBase` se conserva sin cambios, con la entrada a 4 unidades, porque el protocolo compara a los candidatos contra ella (`--comparar`, `--meseta`).
- **Razón.** Decisión de Nicolás, del mismo día que T50. Es el único cambio con retorno medido: +0,04 puntos esperados del torneo sobre la regla base a 2 000 ticks, +0,7 % de patrimonio en los remuestreos y +1,4 % en las familias plausibles, con semilla reservada.
- **Conflicto con el principio 4, que se avisa.** El principio pide mejorar la media y el peor bloque fuera de muestra. `max_media` no lo cumple en los 10 bloques de práctica: media 11 043 contra 11 069 y peor bloque 9 620 contra 9 720. En la serie completa de práctica da 25 973 contra 27 062. La decisión del 15/11 (T50 y esta) manda sobre los principios anteriores, y las diferencias en los bloques están dentro del error (238), pero en la defensa hay que poder explicar por qué la tabla del punto 3.1 muestra un número menor que el de la versión anterior.
- **Equivalencia.** `make equiv` (gemelo a los tres períodos, Verilator a 0,1 y 1 ms, 13 series de familias), `make equiv-gemelo` (3810 series a los tres períodos, 7,62 millones de ticks por período) y `make equiv-r3` (Icarus) con cero diferencias. Patrimonio en el testbench con los 20 000 ticks: 26 070 a los tres períodos.

### T52. El generador de programas aleatorios se corrige y se mide su cobertura (15/11)

- **Decisión.** `tools/prog_aleatorio.py` lleva las dos correcciones de `factibilidad/a_barrel/tools/prog_hilos.py` (T49): x11 y x12 avanzan con una recurrencia de sumas al comienzo de cada vuelta y ningún salto cae en un `jalr` sin pasar por su `auipc`. Además, al comienzo de cada vuelta los diez registros x1 a x10 reciben x11 o x12 con un `xor`, las bases x13 a x15 pesan la cuarta parte como operandos, y un tipo de instrucción nuevo escribe x0 y lo lee en la instrucción siguiente. Este último hizo falta porque, con x0 también rebajado como operando, la mutación `MUTA_X0` dejó de ser detectada por la ejecución en paralelo; con el par explícito la detectan 4 de 4 programas, igual que a las otras cuatro. `tb/tb_paralelo.sv` cuenta las instrucciones distintas con la misma definición que la factibilidad: mismo contador de programa con otro valor escrito, otro store u otra palabra de memoria.
- **Medición.** `make paralelo-largo` con el generador anterior (`ORIGINAL=1`, que reproduce los programas viejos byte a byte): las mismas 1 300 756 instrucciones publicadas en T38, de las cuales solo 4 644 eran distintas (0,4 %). Con el de 32 bits, 5 306 de 1 600 000. Con el generador corregido: 1 600 000 instrucciones en cada configuración, 628 583 distintas (39,3 %), ningún programa sale de la memoria y cero diferencias entre el base y el segmentado.
- **Por qué no más.** Con cinco registros mezclados la cobertura fue 34 %, con diez 39 %, y con un 35 % de operaciones de mezcla 47 %. El techo lo ponen las comparaciones (`slt`, `sltu`, `slti`, `sltiu`), que solo dan 0 o 1, y las constantes (`lui`, `auipc`, enlaces de `jal`). Subir la mezcla más allá de lo elegido reduce la variedad de operaciones (todas pasan a ser `x = x op x11`). Para el criterio 5 de la puerta del barrel (más de 90 % distintas) hará falta otra definición de "distinta" o un generador distinto: queda anotado para P1.
- **Qué cambia en las cifras.** La cifra de "2,9 millones de instrucciones" del segmentado (T38, T42, README y `docs/espino_segmentado.md`) se corrige a la nueva. `tools/medir_espino.sh` sigue usando el generador anterior (`--original`) para que las cifras de CPI publicadas se puedan reproducir.

### T53. Barrido de fases y matriz de estrés con una maestra configurable (15/11)

- **Decisión.** `tb/tb_estres.sv` es una maestra SPI con la misma transacción y la misma medición que el testbench oficial, pero con período, inicio, SCLK, tiempos de `CS_n`, rondas y pausas elegidos con plusargs, para compilar una sola vez con Verilator. `tools/estres.py` arma los casos y compara cada byte que lee la maestra con `ref/trader.py`. `make fases` (criterio 4 de la puerta) y `make estres` (criterio 7).
- **Alternativas.** Copias del testbench oficial con `sed`, como `tools/equiv.sh`: no alcanzan, porque los tiempos de la transacción están escritos como números dentro de la tarea `spi`. Hacer la matriz en el gemelo: el gemelo ya acepta SCLK y tiempos de `CS_n`, pero no modela el barrel (P4), y la puerta tiene que correr igual sobre R1.
- **Resultados en el core base con `max_media`** (`docs/mediciones/estres_base.txt`). Peor caso de respuesta en las 8 fases del sondeo: 49 ciclos, contra un límite de 1131 (la mitad del presupuesto de la ronda 3). El testbench oficial informa 44 porque con su período siempre cae en las mismas dos fases. SCLK de 100 kHz a 1 MHz, 20 combinaciones de tiempos de `CS_n`, reset que termina a mitad de una transacción en 17 posiciones distintas, tres rondas seguidas sin reset con períodos distintos, series pegadas en 1 y en 255 y seis familias: todos los bytes idénticos a la referencia, MISO sin X y ningún precio sin respuesta.
- **Límites encontrados.** SCLK funciona hasta 4 MHz. A 5 MHz el medio período (100 ns) es menor que la latencia de MISO, que pasa por dos flip-flops de sincronización y cambia un ciclo después (unos 120 ns): la maestra lee el bit anterior. Está fuera del rango que se pide. Un reset que termina a mitad de una transacción pierde ese precio y no deja un byte falso: el contador de bits se reinicia con la siguiente bajada de `CS_n`. El período mínimo probado es 11,5 us, 8,7 veces más rápido que la ronda 3.

### T54. R0 es un bitstream nuevo; `competencia_v1.bin` queda como antecedente (15/11)

- **Decisión.** `bitstreams/r0_base_max_media.bin` es el core base, sin hardware agregado, con el `trade.hex` de `max_media`. `competencia_v1.bin` (regla base) y `segmentado_v1.bin` no se tocan ni se borran.
- **Criterios 5 y 6 de la puerta para R0.** El 5 pide comparar cada hilo del core que compite contra el core base: en R0 el core que compite es el base, así que se cubre con `make formal-base` (las etapas IF e ID son equivalentes a las del repositorio del curso) y con `make cosim` (el gemelo, validado contra el RTL con programas del generador corregido). El 6 (degradación con hilos que se cuelgan) no aplica: R0 tiene un solo hilo.

### T55. El barrel entra a `rtl/` como una variante más del mismo SoC (15/11)

- **Decisión.** El core de la factibilidad pasa a `rtl/espino_core/espino_barrel_core.v` y `rtl/espino_core/espino_barrel_regfile.v` sin cambios de lógica (el `diff` contra el prototipo son comentarios). `rtl/pochoco_soc.v` lo instancia cuando se compila con `-DESPINO_BARREL`. Sin definiciones el SoC sigue siendo el Espino base, y `-DESPINO_SEGMENTADO` y `-DESPINO_ROM` siguen eligiendo el segmentado. Scripts en `tools/barrel/`, testbenches en `tb/barrel/`, programas de prueba en `sw/barrel/`, propiedades en `formal/barrel/` y salidas en `docs/mediciones/barrel/`.
- **Alternativas.** (a) Mantener una copia aparte de `pochoco_soc.v` para el barrel, como en el prototipo: dos archivos con el mismo módulo no pueden estar en `rtl/` (el comando del testbench oficial compila `rtl/*.v`), y dos copias del mapa de memoria terminan divergiendo. (b) Elegir con el parámetro `Pipeline = 3` y un `generate`: la instancia del core dejaría de llamarse `dut.u_core` y habría que tocar los testbenches del base y del segmentado. Se eligió el `ifdef`, que es lo que ya hace la variante de ROM.
- **Qué se quitó.** Las opciones que el prototipo tenía solo para medir alternativas: el registro `HILO` por MMIO con arranque común, el SoC sin periféricos y el nombre de módulo configurable. Sus números quedan en `factibilidad/a_barrel/README.md` (rama `factibilidad-fondo`). Para instanciar el barrel junto al base en un mismo testbench, `tools/barrel/comun.sh` genera una copia de `pochoco_soc.v` con el módulo renombrado y comprueba que difiera en 5 líneas exactas.
- **Comprobación de que el base no cambió.** `make formal-base` (IF e ID equivalentes a las del repositorio del curso), `make tb` con 4/4 y la medición de recursos del base en la misma corrida que la del barrel.
- **Pendiente que se avisa.** El comando del encabezado del testbench oficial no lleva definiciones, así que compila el Espino base con `sw/trade.hex`. Si R1 o R2 pasan a ser titulares, el valor por defecto del SoC y el programa por defecto tendrán que cambiar para que ese comando ejercite el diseño que compite. Es una decisión de P5, cuando exista `sw/fondo.s`, y se presenta antes de tomarla.

### T56. La tabla de arranque la pone el programa; `sw/trade.s` no cambia (15/11)

- **Decisión.** `sw/trade.s` y `sw/trade.hex` quedan como están: son el programa de R0, que ya pasó su puerta de simulación. Para correrlo en el barrel, `tools/barrel/tabla.py` le antepone la tabla de cuatro saltos (`build/barrel/sw/trade_h0.hex`). El testbench oficial sin modificar lee `sw/trade.hex` del directorio actual, así que contra el barrel se corre dentro de una carpeta de `build/` donde ese nombre apunta al programa con tabla (`tools/barrel/oficial.sh`). El archivo del testbench no se toca.
- **Alternativa que queda propuesta.** Poner la tabla dentro de `sw/trade.s`. En el base y en el segmentado la primera instrucción sería un salto a `_start` y las otras tres entradas no se ejecutarían nunca: 4 palabras y 3 ciclos una sola vez al arrancar. El mismo `.hex` serviría en los tres cores y desaparecería el modo de falla del programa sin tabla (`make barrel-sin-tabla`). No se hizo en P1 porque cambia el programa y el hash de R0 y obliga a repetir su puerta. Conviene decidirlo en P3, junto con `sw/fondo.s`.

### T57. Criterio 5 de la puerta: programas lineales y distintas contadas en toda la campaña (15/11)

- **El problema.** El criterio pide comparar al menos 5 millones de instrucciones con más de 90 % distintas. Con programas que repiten su cuerpo el techo ronda 40 % (T52): las comparaciones dan 0 o 1 y las constantes se repiten en cada vuelta.
- **Decisión.** No se cambia la definición para que el número suba. Se cambia el generador: `tools/barrel/prog_hilos.py --lineal` hace programas que se ejecutan una sola vez y terminan en un lazo vacío, y la campaña son 20 600 corridas cortas con programas distintos. La definición se hace más exigente: una instrucción es distinta si no hay otra con el mismo hilo, contador de programa, instrucción, valor escrito, acceso al bus y palabra de memoria **en toda la campaña**, no solo dentro de su corrida.
- **Alternativas descartadas.** (a) Definir "distinta" por el estado de los operandos, como proponía el cierre de P0: sube el porcentaje de los programas con lazos sin que se pruebe nada nuevo. (b) Mezclar más los registros en cada vuelta: en P0 llegó a 47 % y deja todas las operaciones de la forma `x = x op x11`.
- **Resultado.** 7 948 558 instrucciones, 7 309 470 distintas (91,96 %), cero diferencias. La campaña de lazos de la factibilidad se conserva como complemento: 8 966 903 instrucciones, 43 % distintas dentro de su corrida. Las 21 mutaciones se detectan también con los programas lineales.
- **Qué se pierde.** Un programa lineal dura unas 100 instrucciones por hilo, así que no ejercita estados que tardan miles de instrucciones en aparecer. Para eso queda la campaña de lazos. El margen sobre el 90 % es chico (1,96 puntos): lo que se repite son las instrucciones fijas del comienzo de cada hilo.
- **Lo que encontró.** Dos programas de 4 500 en que un hilo terminaba ejecutando la zona de datos compartida. Era un hueco del método y no un error del core (detalle en `docs/espino_barrel.md`, sección 8.2).

### T58. La extensión lleva tres instrucciones elegibles por separado; cuáles compiten se fija con `sw/fondo.s` (15/11)

- **Decisión.** El paquete P2 deja en `rtl/` `emad`, `devk` y `mulstep`, cada una con su definición (`-DESPINO_XD_EMAD`, `-DESPINO_XD_DEVK`, `-DESPINO_XD_MULSTEP`; `-DESPINO_XD` las tres), y mide y verifica los 7 subconjuntos. No se trajo ninguna otra instrucción de la factibilidad.
- **Razón.** El criterio del grupo es que al bitstream entren solo las instrucciones que `sw/fondo.s` usa realmente, y ese programa es del paquete P3. `emad` y `devk` las usan los cuatro hilos. `mulstep` solo tiene uso si el supervisor lleva la contabilidad de la cuenta, que el fondo mínimo no necesita para decidir. Con los 7 subconjuntos ya probados, sacar `mulstep` es quitar una definición y no repetir el paquete.
- **Alternativas.** (a) Solo `emad` y `devk`: si P3 necesitara el producto habría que reabrir P2. (b) Las tres siempre: deja en el bitstream una instrucción que puede quedar sin uso, contra ese criterio.
- **Qué se pierde.** Nada medible: las tres juntas cuestan 96 celdas y `emad` con `devk` 52.
- **Decidido por Nicolás (15/11).** "R1 se compila solo con emad y devk. mulstep queda para la edición de exhibición y el ASIC." Razón, textual: "no quiero piezas sin uso en el chip que compite". El fondo de P3 se escribió con esa restricción (T63).

### T59. La extensión va fuera del decodificador del Espino y las codificaciones que no existen son ilegales (15/11)

- **Decisión.** `rtl/espino_core/espino_decoder.v`, `espino_alu.v` y `espino_load_store_unit.v` no se tocan. Un módulo aparte (`espino_xd_dec`) reconoce las tres codificaciones y el core barrel corrige cuatro señales de lo que se registra hacia la etapa X. El módulo revisa los 7 bits de `funct7`: `emad` y `devk` con k distinto de 5, y `mulstep` con `funct7` distinto de cero, son instrucciones ilegales sin efecto.
- **Razón.** El decodificador lo comparten el base y el segmentado, y R0 ya pasó su puerta con ese archivo. Y una especificación que dice "con otro k el resultado es el de k = 5" no se puede defender: en el prototipo el hardware ignoraba el campo k.
- **Alternativas.** La integración del prototipo, con parámetros nuevos dentro del decodificador y k sin revisar.
- **Qué se pierde.** Unas 6 celdas contra el prototipo (+96 contra +90, dentro del ruido del conteo) y 0,4 MHz de mínima (48,3 contra 48,7).
- **Comprobación.** Con `Xd = 0` el core es formalmente equivalente al del commit de P1 (`make xd-formal`, parte B1).

### T60. La referencia de la extensión es el Espino base más la especificación escrita en el testbench (15/11)

- **Decisión.** `tb/barrel/tb_verif.sv` sigue comparando cada hilo contra un Espino base. Cuando el base completa una palabra que la especificación reconoce, el testbench calcula el resultado con la fórmula y lo escribe en el banco de registros de la referencia. `tools/barrel/prog_hilos.py --xd` genera las instrucciones, codificadas por el generador y no por el ensamblador.
- **Razón.** El cierre de P1 dejó planteado contra qué comparar instrucciones que el base no ejecuta. Así se reutiliza toda la campaña de P1 (los mismos grupos, la memoria compartida, los precios por el SPI) con programas que mezclan RV32E y la extensión, y la configuración que compite vuelve a pasar el criterio 5.
- **Alternativas.** (a) El método del prototipo: una lista de escrituras predicha por el modelo en Python, que solo sirve para programas sin saltos. (b) Reemplazar custom-0 por nop y comparar solo RV32E: no prueba las instrucciones.
- **Qué se pierde.** La referencia ya no es RTL del curso sin tocar para esas instrucciones: es una fórmula de tres líneas en el testbench. Por eso la misma especificación se prueba además formalmente (`make xd-formal`) y contra el modelo en Python (`make xd-tb`), escrita por separado en los tres lugares.
- **Lo que encontró.** El generador podía producir por azar un `mulstep` que pisaba la dirección base del SPI (2 corridas de 20 600). Detalle en `docs/extension_isa.md`, sección 7.2.

### T61. El ensamblador exige declarar la extensión y rechaza k distinto de 5 (15/11)

- **Decisión.** `emad`, `devk` y `mulstep` solo se aceptan con la directiva `.extension xd` en el fuente o con la opción `--xd`. Un k distinto de 5 es un error.
- **Razón.** El comando del encabezado del testbench oficial ensambla sin opciones, así que la habilitación tiene que poder ir dentro del fuente. Y un programa con estas instrucciones cargado en el base o en el segmentado no falla: simplemente no las ejecuta. El error tiene que aparecer al ensamblar.
- **Qué se pierde.** Una línea más en cada programa que use la extensión.

### T62. R0 se reproduce desde su commit, no desde el último (15/11)

- **Decisión.** `make r0-reproducir` extrae las fuentes del commit `1d4a82f` con `git archive`, construye el bitstream ahí y compara su sha256 con el de `bitstreams/SHA256SUMS`. Corre en la integración continua.
- **Razón.** Al integrar P1 y P2 en `main`, `make bin` siguió dando un R0 correcto (`make check` y `make sim-bitstream` pasan) pero con otro hash: los archivos nuevos de `rtl/` cambian los nombres internos de Yosys y con ellos la ubicación que elige nextpnr. El bitstream que va a la maestra el 26/11 tiene que ser un archivo con hash conocido que cualquiera pueda volver a obtener.
- **Alternativas.** (a) Sintetizar R0 solo con los archivos que existían entonces: se probó y da un tercer hash, porque `pochoco_soc.v` también cambió de líneas. (b) Volver a generar R0 en cada paquete y repetirle la puerta: gasta tiempo y cambia el archivo que ya pasó las pruebas.
- **Qué se pierde.** El script depende del historial de git y de la versión de las herramientas (OSS CAD Suite del 2026-09-06).

### T63. El fondo de competencia es `fondo_min` sin el espejo de la cuenta (15/11)

- **Decisión.** `sw/fondo.s` implementa la configuración `fondo_min` de la factibilidad (tres gestores de la regla de reversión con entradas a 3, 4 y 2 unidades bajo la media, pesos 6/5/5 que se ajustan cada 512 ticks y mayoría de 8/16) y no lleva la contabilidad de la cuenta. El puntaje en papel se guarda en treintaidosavos de unidad de precio en vez de dieciseisavos.
- **Razón.** La especificación del fondo pide la combinación medida en la factibilidad y órdenes idempotentes. El espejo no entraba en ninguna decisión, ocupaba 75 de las 227 palabras y era el único uso de `mulstep`, que quedó fuera de R1 (T58). El puntaje en treintaidosavos sale de `devk` sin instrucciones adicionales: es el doble exacto y el margen de la frontera se escala igual, así que no cambia ninguna decisión. `ref/test_fondo.py` lo comprueba contra una segunda escritura con la aritmética de la factibilidad y contra los números que midió su módulo en C.
- **Alternativas.** Conservar el espejo para la telemetría (mostrar el patrimonio): exige `mulstep` o 25 instrucciones por venta, y un espejo que nadie compara con la maestra puede mostrar un número falso sin que se note.
- **Qué se pierde.** El programa no sabe cuánto tiene. La telemetría muestra la posición objetivo, no el patrimonio.

### T64. Degradación: plazo en el supervisor y `max_media` propia en el lugar del voto ausente (15/11)

- **Decisión.** El supervisor lee los tres votos en un lazo de 12 instrucciones (48 ciclos) y sale cuando los tres traen el tick en curso o después de `PLAZO` vueltas (8 en la tabla). Vencido el plazo, cada voto viejo se reemplaza por la posición de la `max_media` que el supervisor calcula en todos los ticks con su propia media. Con algún voto ausente no se ajustan los pesos, y si el tick era de frontera la ventana vuelve a empezar.
- **Razón.** La especificación pide que la decisión nunca dependa de que otro hilo esté vivo, y que sin ningún voto el supervisor decida solo. Con esta regla, sin votos el byte es exactamente el de `sw/trade.s` (probado en 20 000 ticks y en `ref/test_fondo.py`). No ajustar los pesos mantiene la única propiedad en que se apoya la lectura de los puntajes: `DES_k` solo se lee después de ver `EST_k` con el tick en curso.
- **Alternativas.** (a) Repartir el peso del ausente entre los presentes: necesita comparar contra la mitad de un total que cambia, y con dos ausentes deja la decisión en un solo gestor que no es `max_media`. (b) Contar al ausente como afuera: sesga hacia vender. (c) Esperar siempre, como en la factibilidad: un gestor colgado deja al fondo sin escribir `DECISION`.
- **Qué se pierde.** Cerca del plazo la decisión sí depende de los ciclos: un voto que llega justo cuando vence puede entrar o no. Con los gestores sanos el lazo da a lo más 3 vueltas en un tick común (4 con frontera), contra las 8 del plazo. La respuesta promedio sube de 227 a 235 ciclos respecto de la factibilidad, porque el lazo lee los tres votos en cada vuelta.
- **Lo que mostró.** Con un voto ausente el fondo decide igual que `max_media`: con los pesos en 6/5/5 la mayoría la define la banda del medio. Lo que separa al fondo sano de `max_media` es solo el ajuste de pesos.

### T65. Las constantes del algoritmo viven en una tabla de 20 palabras (15/11)

- **Decisión.** Umbrales, pesos iniciales, topes, pisos, ventana, umbral del voto y plazo se leen de una tabla en `0x770`, en el mismo orden que `PARAMETROS` de `ref/fondo.py`. Los pesos vigentes son estado y el supervisor los copia de la tabla al arrancar. El resto de la memoria de datos parte en cero.
- **Razón.** La especificación pide los parámetros en una tabla de solo lectura que se pueda cambiar con `icebram` sin sintetizar. La BRAM dedicada es hardware del paquete P5; hasta entonces la tabla va al final de la memoria de datos, y P5 solo tiene que cambiar su dirección. `ref/test_fondo.py` compara la tabla del programa con la de la referencia palabra por palabra.
- **Qué se pierde.** 5 loads por tick en el supervisor (20 ciclos de respuesta) frente a tener las constantes como inmediatos.

### T66. Telemetría con un store por tick, alternando registro (15/11)

- **Decisión.** En los ticks pares el supervisor escribe los 7 segmentos (63 si la orden es comprar, 00 si es vender) y en los impares los LED (LED 0 el bit 10 del número de tick, LED 1 a 3 los votos tal como entraron a la suma). Siempre después de escribir `DECISION`.
- **Razón.** El periférico de la placa tiene los dígitos y los LED en registros distintos y la especificación admite un store de telemetría por tick. Cambiar el periférico para juntarlos sería hardware nuevo sin otra función.
- **Qué se pierde.** Cada indicador se actualiza tick por medio. El latido cambia cada 1024 ticks: 0,1 s en la ronda 3, 1 s en la ronda 2 y 10 s en la ronda 1.

### T67. Criterio 2 de la puerta por el RTL con Verilator (15/11)

- **Decisión.** Las 1 000 series sintéticas del criterio 2 se corren por el RTL con `tb/fondo/tb_fondo.sv`: 70 series de 2000 ticks de cada una de las 15 familias, a 0,1 ms. Los tres períodos se cubren con los 20 000 ticks de la serie de práctica.
- **Razón.** El gemelo digital no modela el barrel (es el paquete P4) y el criterio es de este paquete. El testbench carga el programa y la serie al ejecutarse, así que se compila una vez y cada serie demora unos 2 segundos.
- **Qué se pierde.** Las series sintéticas no se corren a 1 ms ni a 10 ms: eso queda para el gemelo de P4.

### T68. Las fallas de la degradación se ponen en el programa, no en el simulador (15/11)

- **Decisión.** Los casos del criterio 6 son `sw/fondo.s` con instrucciones insertadas en la rutina de los gestores (`tools/fondo/variante.py`): un lazo infinito, un salto que omite el store del voto o un lazo de retardo. El supervisor no se toca. La decisión esperada sale de `ref/fondo.py` con la falla descrita como "el voto del gestor K no llega entre los ticks N y M".
- **Razón.** Un gestor colgado de verdad sigue ocupando su turno en el barrel y sigue leyendo la memoria: es lo que pasaría en la placa. Forzar señales en el simulador prueba otra cosa.
- **Qué se pierde.** No se prueban atrasos cercanos al plazo (entre 200 y 600 ciclos), donde el resultado depende del ciclo exacto y la referencia no lo modela.

### T69. La tabla de parámetros es una BRAM de solo lectura, sin puerto de escritura (15/11)

- **Decisión.** `rtl/pochoco_tabla.v` es una BRAM de 256 valores de 16 bits en `0x8002_0000` que el core solo lee. `lw` entrega el valor con extensión de signo. Un store a esa dirección no hace nada. El programa lee de ahí en todos los ticks, con la base en un registro.
- **Razón.** La especificación pide los parámetros en una tabla de solo lectura en competencia. El prototipo de la factibilidad era de lectura y escritura. Sin puerto de escritura el programa no puede corromperla ni por error, y el módulo es más chico. Leerla en cada tick, y no copiarla a la memoria de datos al arrancar, mantiene una sola copia de cada constante.
- **Alternativas.** (a) Copiar la tabla a la memoria de datos al arrancar: el programa no cambia, pero la copia sí se puede pisar, y hay una carrera en el arranque entre el supervisor que copia y los gestores que leen. (b) Dejarla en la memoria de datos, como en P3: cambiarla con `icebram` obliga a tocar la memoria del programa.
- **Qué se pierde.** 39 celdas y 1 BRAM, y una instrucción más por tick en el supervisor.
- **Lo que encontró.** La primera versión salía con la BRAM en cero en el bitstream: Yosys descarta el `$readmemh` si antes hay un lazo que deja la memoria en cero. Ninguna prueba del RTL lo veía. Detalle en `docs/tabla_vigilante.md`, sección 2.4.

### T70. Los cambios con `icebram` se hacen siempre desde un molde, que se guarda (15/11)

- **Decisión.** Junto a R1 y R2 se guardan sus moldes en `bitstreams/moldes/`: el `.asc` de cada uno con el programa y la tabla reemplazados por un patrón al azar, y los patrones. Los bitstreams de R1 y R2 son la síntesis directa, y se comprobó que el molde con `icebram` da el mismo `.asc`.
- **Razón.** `icebram` ubica una memoria por su contenido, y la tabla de verdad (236 valores en cero) no es distinguible: se niega a trabajar sobre el bitstream final. Y volver a sintetizar el día de la competencia puede dar otra ubicación, que ya no sería el hardware probado con la maestra.
- **Qué se pierde.** 190 KB más en el repositorio. Un bitstream cambiado hay que simularlo desde su `.asc` antes de grabarlo, unos 40 minutos.

### T71. Vigilante con K = 4 y tres salidas nuevas en el esclavo SPI (15/11)

- **Decisión.** `rtl/vigilante.v` es el de la factibilidad, sin cambios en la lógica, con `VigN = 4`: dispara al quinto precio seguido sin escritura en `DECISION`. `rtl/pochoco_spi_slave.v` saca `byte_done`, la escritura en `DECISION` y `CS_n` sincronizado por tres salidas nuevas. No se conectó el disparo manual por interruptor.
- **Razón.** En todas las corridas sanas de R2, incluida la matriz de estrés, la cuenta del vigilante nunca pasó de 1, así que cualquier K de 2 o más cumple el criterio de no disparar en ninguna simulación sana. 4 deja margen y gasta 5 ticks de los 536 del relevo (361 con el tiempo medido después en la placa, `docs/mediciones/placa_16nov.md`). Las salidas del esclavo son la forma más chica de darle al vigilante las señales que necesita: no cambian su lógica ni los nombres que mira el testbench oficial. El disparo manual quedó fuera porque el uso de los interruptores durante la competencia es una pregunta pendiente para el ayudante.
- **Alternativas.** Derivar `byte_done` fuera del esclavo: habría que duplicar su sincronizador y su contador de bits.
- **Qué se pierde.** 16 celdas y unos 4 MHz de frecuencia mínima respecto de R1.

### T72. La imagen de respaldo de R2 es R0, el mismo archivo (15/11)

- **Decisión.** `bitstreams/r2_multi.bin` es `icemulti -p0` con R2 en la imagen 0 y `bitstreams/r0_base_max_media.bin` en la imagen 1, copiado sin cambios (se comprueba su sha256 dentro del archivo múltiple).
- **Razón.** R0 ya pasó su puerta de simulación completa y es el respaldo de toda la escalera. Usar el mismo archivo evita tener un segundo bitstream del core base que probar. No tiene vigilante, así que no puede haber un ciclo de reinicios.
- **Qué se pierde.** Después de un relevo, `max_media` parte de cero: sin media previa y sin posición.

### T73. Criterio 7 con el RTL y con casos propios del fondo (15/11)

- **Decisión.** La matriz de estrés de R1 y R2 usa los casos de R0 (`tools/estres.py`) con el testbench del fondo y Verilator. Los casos que dejan menos de 600 ciclos entre transacciones se informan como exploración, y se agregaron SCLK de 100 y 200 kHz con período de 1 ms.
- **Razón.** El gemelo del barrel (P4) no existe todavía y la puerta de R1 y R2 es de este paquete. El fondo responde en 220 a 444 ciclos y R0 en menos de 50: SCLK de 100 kHz con período de 0,1 ms deja 237 ciclos, donde R0 cabe y el fondo no.
- **Qué se pierde.** Una combinación que R0 soporta y el fondo no. Si la maestra real usara SCLK de 100 kHz en la ronda de 0,1 ms, R1 respondería con un tick de atraso según la medición del testbench (en la simulación los bytes igual coinciden). Es un dato para la prueba del 26/11.

### T74. Criterio 5 repetido con la máscara exacta sobre el SoC de cada peldaño (15/11)

- **Decisión.** `make fondo-criterio5` repite la campaña del core y las mutaciones con la máscara 3 (`emad` y `devk`), agregando las definiciones de la tabla y del vigilante a los dos SoC de la comparación. De las 9 mutaciones de la extensión se corren las 6 que tocan lógica presente; para las 3 de `mulstep` se comprueba que el netlist sintetizado no cambia.
- **Razón.** El criterio pide la configuración exacta que compite. Una mutación sobre lógica que no existe no se puede detectar ni hace falta: lo que hay que mostrar es que de verdad no existe.
- **Qué se pierde.** Nada: las pruebas son las de P1 y P2 sin cambios.

Las decisiones T80 a T85 son de los paquetes P4 y P6, trabajados en paralelo con P5 en otra rama. Los números T75 a T79 quedaron sin usar.

### T80. El gemelo modela el barrel por calendario de etapas, con un atajo por estado periódico (15/11)

- **Decisión.** En modo `--barrel` el gemelo no simula el pipeline: ejecuta cada instrucción entera en el ciclo en que su hilo está en la etapa X (x0 + t + 4n), busca la siguiente dos ciclos después con la memoria de antes de las escrituras de ese flanco, y anota la escritura al banco un ciclo después. El atajo del sondeo saca una foto del estado de los cuatro hilos cada vez que el hilo 0 va a leer STATUS en su lazo; si se repite sin otros accesos al SPI, salta por períodos completos hasta la lectura que ve el precio.
- **Razón.** La rotación del barrel es fija y no hay riesgos entre hilos, así que el calendario es exacto. La foto no depende de `sw/fondo.s`: sirve para cualquier programa que quede en un ciclo mientras espera, y si no queda, no salta.
- **Alternativas.** (a) Simular las cuatro etapas registro por registro: más código, el mismo resultado. (b) Reconocer el lazo de los gestores como el del supervisor: ata el gemelo al programa y no sirve para los programas aleatorios ni para el gestor colgado.
- **Qué se pierde.** Nada medible: con y sin atajo los resultados son idénticos a los tres períodos, y la ronda de 10 ms del fondo pasa de 76 s (sin atajo) a 0,14 s.

### T81. Las variables de ronda de los testbenches se asignan aparte (15/11)

- **Decisión.** En `tb/tb_estres.sv`, `tb/fondo/tb_fondo.sv` y `tb/barrel/tb_gemelo.sv`, `int r = (ronda_ticks > 0) ? n / ronda_ticks : 0;` dentro del `for` pasa a ser `int r;` y una asignación. Se repitió la matriz de estrés de R0 y se corrió la del fondo con el arreglo.
- **Razón.** Una variable declarada con valor inicial dentro de un bloque `initial` es estática en SystemVerilog: el valor inicial se asigna una sola vez. `r` quedaba en 0 y todas las rondas usaban el período de la primera. Lo encontró la validación del gemelo, que tenía la semántica correcta y no coincidía con el RTL en las rondas seguidas. Es el mismo error que P3 encontró en `tb_fondo.sv` con otra variable.
- **Qué cambió.** Los casos `rondas_*` de R0 vuelven a pasar, ahora con los períodos que dicen (`docs/mediciones/estres_base.txt`): las cifras no se mueven porque la respuesta de R0 no depende del período. Lo que antes estaba afirmado sin probar era que el programa sigue funcionando cuando el período cambia sin reset.

### T82. La matriz de estrés del fondo es la de R0 con la referencia del fondo, por el RTL y por el gemelo (15/11)

- **Decisión.** `tools/estres.py` acepta `--ref fondo` (bytes esperados de `ref/fondo.py`) y `--motor gemelo`. El criterio 7 del fondo se corre con los mismos 60 casos que R0, por el RTL (`make fondo-estres`) y por el gemelo (`make fondo-estres-gemelo`). Los dos casos de período cercano al mínimo se fijan por programa: para el fondo, 33,5 us y 38,3 us (presupuesto de 600 y 720 ciclos) en vez de 11,5 us y 13,5 us (50 y 100 ciclos, que solo tienen sentido para R0).
- **Razón.** Una sola matriz para todos los peldaños hace comparables los resultados. Correrla por los dos motores es otra validación del gemelo: dan las mismas 60 líneas, con los mismos promedios y peores casos.
- **Qué se pierde.** Nada. La matriz por el RTL demora unos minutos; por el gemelo, 3 segundos.

### T83. La autoprueba vive fuera de `rtl/*.v` y deja sin conectar la telemetría del SoC (15/11)

- **Decisión.** El top de la autoprueba está en `rtl/autoprueba/`, instancia `pochoco_soc` sin cambios y deja sus LED y 7 segmentos sin conectar. Los botones del SoC van a 0.
- **Razón.** `rtl/*.v` es la lista de fuentes del comando del testbench oficial y de la síntesis de R0: un archivo más ahí cambia los nombres internos de Yosys y el hash del bitstream (T62). Los LED y los 7 segmentos de la placa los necesita la autoprueba para mostrar la firma. La especificación de la autoprueba permite sacar la telemetría de esta versión si no cabe; aquí además se necesitan los pines.
- **Qué se pierde.** La autoprueba no muestra la telemetría de `sw/fondo.s`. El SoC de la autoprueba no es el mismo bitstream que compite: es el mismo RTL, sintetizado junto a otra lógica.

### T84. Maestra interna mínima: SCLK de 781 kHz, caminata de a 1 y CRC bit a bit (15/11)

- **Decisión.** La maestra interna arma la transacción con un contador de 9 bits (medio período de SCLK de 16 ciclos, así que el nivel y el número de bit son bits del contador), genera los precios con una caminata de +1 o -1 según un LFSR de 16 bits, calcula la firma CRC-16 bit a bit al leer MISO, y lleva el período con un contador descendente que se carga con una de tres constantes.
- **Razón.** R0 ocupa 1083 celdas. La primera versión, con los tiempos del oficial (SCLK de 1 MHz, medio período de 12,5 ciclos redondeado a 13), contadores de fase y de bit, CRC byte a byte y pasos de -2 a +2, costaba 233 LUT y el total llegaba a 1340 de 1280 celdas. La versión actual entra: 1269 celdas, 44,05 MHz.
- **Alternativas.** (a) Sacar los 7 segmentos y mostrar solo un LED de coincide: pierde la firma, que es lo que permite comparar a mano. (b) Una maestra más lenta todavía: no ahorra celdas, el costo está en los contadores y la firma.
- **Qué se pierde.** La transacción no es la del oficial: 781 kHz y 12,16 us en vez de 1 MHz y 9,5 us. Para lo que prueba la autoprueba (que la FPGA toma las mismas decisiones a tiempo) no importa, y los tiempos del oficial ya están en la matriz de estrés. Quedan 11 celdas libres: cualquier cambio en R0 o en la maestra puede dejar de caber.

### T85. La firma esperada va dentro del bitstream, y se calcula de dos formas (15/11)

- **Decisión.** `tools/autoprueba.py` calcula la firma con el gemelo a los tres períodos y con la referencia del algoritmo, exige que las cuatro coincidan y la fija como parámetro del top. Al terminar, LED3 indica que coincide y LED4 que no. Los 7 segmentos muestran la firma de todos modos.
- **Razón.** Con un LED la prueba en la placa no depende de leer bien cuatro dígitos. Que la firma sea la misma a los tres períodos prueba que el programa responde siempre antes del tick siguiente.
- **Qué se pierde.** Hay que reconstruir el bitstream si cambia el programa o la serie. Un bitstream de autoprueba no es de competencia y nunca se lleva el 1/12.

### T86. Al integrar P4 con P5, la matriz de la puerta es la de P5 y la de P4 queda como validación del gemelo (16/11)

- **Decisión.** `make fondo-estres` es la matriz de P5 (`tools/fondo/estres.py`, con `tb/fondo/tb_fondo.sv`, T73), que es la del criterio 7 de R1 y R2. La de P4 (T82, los 60 casos de R0 con la referencia del fondo) pasa a llamarse `make fondo-estres-rtl60` por el RTL y `make fondo-estres-gemelo` por el gemelo, siempre con el hardware de R1. El gemelo aprende la tabla de parámetros (`--tabla sw/fondo_tabla.hex`) y las herramientas de P4 corren con el programa de P5. Las salidas de P4 hechas con el programa de P3 se movieron a `docs/mediciones/fondo/p3/`.
- **Razón.** Las dos matrices miden casi lo mismo. La de P5 compara además el estado interno, la telemetría y el protocolo, y es la que ya está en `docs/puertas.md`. La de P4 sigue sirviendo para lo que la hizo valiosa: dos motores que tienen que dar las mismas líneas.
- **Qué se pierde.** Nada. El gemelo no modela el vigilante, así que todo lo que corre en el gemelo es R1; en R2 el vigilante no se dispara en ninguna corrida sana (T71, T73).

### T87. La autoprueba de R1 y R2 usa otra caminata, con semilla 0x3CA1 (16/11)

- **Decisión.** La maestra interna de R1 y R2 parte el LFSR en 0x3CA1. R0 sigue con 0xACE1. La semilla es un parámetro del top (`SEMILLA`) y no cuesta celdas.
- **Razón.** Con la caminata de 0xACE1 el fondo decide exactamente igual que `max_media` en los 2000 ticks, así que su firma habría sido `a23c`, la de R0. Con un gestor colgado el supervisor decide solo, que también es `max_media`: la autoprueba no lo habría visto. De 677 semillas probadas, solo 10 dan alguna diferencia entre el fondo y `max_media` en 2000 ticks de pasos de a 1. Con 0x3CA1 hay 51 ticks distintos, y cualquiera de los tres gestores colgado cambia 51 bytes y la firma (`7d4f` en vez de `15d7`).
- **Alternativas.** (a) Más ticks: las diferencias aparecen después del primer ajuste de pesos, y la ronda de 10 ms ya dura 20 s. (b) Pasos más grandes en la caminata: cuesta celdas en la maestra y R0 ya está grabado con la de ahora.
- **Qué se pierde.** La firma de R1 no se compara con la de R0: son series distintas. La serie sigue siendo poco exigente para el fondo; lo que prueba la autoprueba es que la FPGA hace lo mismo que el gemelo, no que el fondo gane.

### T88. El control negativo de R1 y R2 cambia la tabla, no el programa (16/11)

- **Decisión.** El control negativo de R1 y R2 es la misma autoprueba con otra tabla de parámetros: `G1_ENTRA` en -64 en vez de -96, con el mismo programa. El gemelo (con esa tabla) y `ref/fondo.py` (con ese parámetro) predicen `6f2a`, y la autoprueba tiene que terminar con LED4 y mostrar `6f2a`.
- **Razón.** Muestra que el SoC lee sus umbrales de la BRAM de la tabla, que es lo nuevo de R1. Se probó primero `G3_ENTRA` en -80, pero esa tabla da `7d4f`, la misma firma que `max_media` sola o un gestor colgado: en la placa no se podría distinguir un control de una falla. `G1_ENTRA` en -64 cambia 93 bytes y da una firma que no se confunde con nada.
- **Qué se pierde.** Nada.

### T89. La imagen 1 de las pruebas de R2 en la placa es una imagen testigo, no R0 (16/11)

- **Decisión.** Las dos imágenes múltiples de la puerta de placa de R2 (`autoprueba_r2_multi.bin` y `relevo_r2_multi.bin`) llevan como imagen 1 un diseño de 83 celdas (`rtl/autoprueba/testigo_top.v`): los cuatro LED encendidos, "--" en los 7 segmentos, los minutos desde que arrancó con SW4, eco de la UART y MISO del PMOD en 0. El bitstream de competencia (`r2_multi.bin`) sigue con R0 como imagen 1.
- **Razón.** Lo que hay que ver en la placa es si hubo relevo. La testigo no se parece a nada que muestre la autoprueba (que siempre muestra dos dígitos hexadecimales), dice cuántos minutos lleva corriendo y permite medir el tiempo del relevo por la UART. `sw/trade.s` no escribe en los LED ni en los 7 segmentos: R0 mostraría el estado de reposo de los periféricos, LED apagados y dos dígitos, que se confunde con una autoprueba recién configurada.
- **Qué se pierde.** Estas pruebas no muestran que R0 arranque después de un warm boot. El mecanismo es el mismo (los vectores de `icemulti` son iguales y todos los bitstreams de la HX1K miden 32 220 bytes, así que demoran lo mismo en cargarse), y R0 es el archivo guardado que ya pasó su puerta. Si se quiere ver con R0, `r2_multi.bin` con la maestra real el 26/11.

### T90. La media hora sin disparo se prueba con la maestra interna en modo continuo (16/11)

- **Decisión.** En la autoprueba de R2 la maestra no se detiene al terminar los 2000 precios de la firma: sigue con la misma caminata y el mismo período, y la firma queda fija (`CONTINUO = 1`). La prueba de media hora es dejar la placa corriendo después de la firma y comprobar que no aparece la testigo. En simulación, el RTL sigue 2 s más después de la firma en cada período sin disparo, y el gemelo corre la caminata de la media hora completa (18 millones de precios a 0,1 ms) y mide el peor caso de respuesta.
- **Razón.** El vigilante cuenta precios. Sin precios no hay nada que probar, y la maestra real no está disponible. A 0,1 ms la media hora son 18 millones de precios, unas 9 000 veces la ronda 3.
- **Qué se pierde.** Después de los 2000 precios la placa no compara las decisiones con nada: solo el relevo diría que algo falló. La caminata es la de la autoprueba, no una serie de mercado.

### T91. La falla se inyecta con una imagen 0 aparte, con el supervisor colgado, y se entrega también sin la orden de dormir la flash (16/11)

- **Decisión.** `relevo_r2_multi.bin` tiene como imagen 0 la autoprueba de R2 con el programa `cuelgue_sup:100` de `tools/fondo/variante.py` (el mismo de las pruebas de P5) y como imagen 1 la testigo. Se arma igual que la autoprueba de R2: sale con la misma ubicación y el mismo ruteo, solo cambia el contenido de las BRAM. Se entrega además `relevo_r2_multi_sin_dormir.bin`, las mismas dos imágenes empaquetadas con `icepack -s`.
- **Razón.** No hay que tocar el SoC ni `sw/fondo.s`. El supervisor colgado es la falla dura para la que existe el vigilante. La variante sin dormir es para diagnosticar en el momento: por defecto `icepack` deja la flash en reposo profundo al terminar de configurar, y la hoja de datos no dice explícitamente que un warm boot la despierte (lo anotó la factibilidad). Si el relevo no ocurre con el archivo normal y sí con el otro, el bitstream de competencia hay que empaquetarlo con `-s`.
- **Qué se pierde.** Nada: son bitstreams de prueba.

### T92. El tiempo del relevo se mide por el eco de la UART, con la cámara y el PMOD como alternativas (16/11)

- **Decisión.** Las dos imágenes de `relevo_r2_multi.bin` conectan el pin de recepción de la UART con el de transmisión, sin lógica. `tools/medir_relevo.py` manda bytes sin pausa a 115 200 baudios y cuenta cuáles no vuelven: son el tiempo en que la FPGA tuvo los pines sueltos. Como alternativas: filmar los 7 segmentos (apagados durante la reconfiguración) a 240 cuadros por segundo, o mirar el pin de MISO del PMOD con un analizador lógico (las dos imágenes lo mantienen en 0; suelto, el pull-up lo sube). El eco y MISO en 0 quedaron en el top de la autoprueba de todos los peldaños.
- **Razón.** El eco no necesita un transmisor en la FPGA y no depende de cuándo el conversor USB entrega los bytes al computador: lo que se cuenta es cuáles faltan. La resolución es un byte, 86,8 us, menos de un tick de la ronda 3. La propuesta de factibilidad (ping-pong de dos imágenes que se alternan solas y promedio de muchas mediciones con la hora de llegada de un byte) necesita un transmisor y no usa el SoC de R2.
- **Alternativas.** (a) La imagen 0 manda bytes hasta el disparo y la imagen 1 desde que arranca: necesita dos transmisores y la hora de llegada al computador tiene el atraso del conversor (hasta 16 ms). (b) Solo la cámara: 4 ms de resolución.
- **Qué se pierde.** Una medición por encendido: para repetirla hay que desconectar y conectar la placa. Si el computador no manda sin pausas, el hueco medido es un mínimo; el script lo comprueba con la duración del envío.

### T100. Operación útil del kernel: 8 por tick en `max_media` y 56 en el fondo (16/11)

- **Decisión.** Para Ops/s, el roofline y Ops/W se cuentan las operaciones de la regla escrita en su forma matemática (`ref/trader.py`): 4 para actualizar la media (32 p, dev = 32 p - S, dev >>> 5 y la suma) y 4 para decidir (dos comparaciones, el or y el and de la posición). En el fondo, 4 reglas de 8, 3 puntajes de 6 y 6 de la combinación: 56. `emad` y `devk` valen 2 cada una, como el MAC de la clase. Los ciclos del kernel van de la lectura de PRICE al salto de vuelta al sondeo, sin la espera. Los bytes son los de los loads y stores del kernel, contando una vez por tick cada lectura de un lazo que espera un dato.
- **Razón.** Es la regla de la clase (solo cuenta el trabajo útil) aplicada a nuestro kernel, y no depende de cómo lo escriba cada variante: `sw/trade.s` y `sw/xd/trade_xd.s` hacen las mismas 8 operaciones con 24 y 12 instrucciones. La factibilidad usaba 6 de forma provisoria (sin la suma de la media ni el and).
- **Alternativas.** (a) Contar instrucciones (MIPS): la clase lo prohíbe entre ISAs distintas, y la extensión es otra ISA. (b) Incluir la espera en los ciclos del kernel: todas las variantes darían casi lo mismo a 0,1 ms, porque el 98 % del tick es sondeo.
- **Qué se pierde.** La cuenta es nuestra. Si el ayudante usa otra, las tablas se regeneran cambiando dos constantes de `tools/p7/tablas.py`.

### T101. El Espino base y el segmentado con la extensión no se construyen: van predichos con Amdahl (16/11)

- **Decisión.** La tabla de variantes los lista como "no existe en el RTL" y da su respuesta y su kernel predichos con el perfil de `sw/xd/trade_xd.s` y el modelo de costo medido de cada core.
- **Razón.** `emad` y `devk` están en `espino_xd.v`, conectado solo al core barrel. Llevarlas al base o al segmentado obliga a tocar `espino_core.v`, que es el RTL de R0 y pasó la puerta de simulación. En las variantes medidas del mismo tipo (barrel con y sin extensión) la predicción acierta al ciclo.
- **Qué se pierde.** Dos filas sin medición. No se sabe cuántas celdas costaría la extensión en el base, donde la ALU es otra.

### T102. El perfil sale de una opción del gemelo, y las fases se leen del programa (16/11)

- **Decisión.** `build/gemelo --perfil` cuenta instrucciones y ciclos por hilo y por dirección; con esa opción el atajo del sondeo se apaga. `tools/p7/fuentes.py` ensambla el programa con `tools/pochoasm.py` y asigna cada dirección a una fase recorriendo el lazo principal de `sw/trade.s` o las secciones numeradas de `sw/fondo.s`. La detección del sondeo es la respuesta medida menos las fases anteriores a la escritura.
- **Razón.** El enunciado pide medir qué parte consume más ciclos. La traza del gemelo y la de `tb/tb_cpi.sv` no traen el contador de programa, y agregarlo al testbench cambia un archivo que usan otras pruebas. La opción solo cuenta: `make cosim` y `make cosim-barrel-corta` siguen en verde.
- **Qué se pierde.** El perfil no sale del RTL. Los ciclos totales que lo validan sí (T103).

### T103. Los ciclos de la tabla salen del gemelo y el RTL confirma R0, el segmentado, R1 y R2 (16/11)

- **Decisión.** `make p7-rtl` corre `tb/tb_cpi.sv` con Verilator para R0 y el segmentado y exige la fila por tick idéntica byte a byte a la del gemelo. Para R1 y R2 compara con la medición del RTL de P5, si su encabezado trae el sha256 del programa y de la tabla actuales. R2 lleva los ciclos de R1.
- **Razón.** El gemelo está validado contra el RTL en todas estas variantes y corre en segundos. La medición de P5 son 35 minutos de Verilator por peldaño y lo que mide no cambió. El vigilante de R2 solo observa: su medición del RTL da los mismos ciclos que R1.
- **Qué se pierde.** El barrel de un hilo y el barrel con la extensión no se repiten por el RTL en P7; los cubre `make cosim-barrel` (21 configuraciones, entre ellas `sw/trade.s` en un hilo y programas con la extensión).

### T104. El PLL se prueba también en un encapsulado que lo tiene, y el duplicador se reproduce desde su rama (16/11)

- **Decisión.** `make p7-pll` repite el intento del PLL sobre R0 y R1 en el VQ100 (falla) y además en un HX1K TQ144 hipotético, sin pines, para saber si el diseño cerraría a 50 MHz. `make p7-doble` extrae la rama `factibilidad-fondo` en `build/p7/` y corre ahí el experimento del duplicador, comparando sus salidas con las guardadas.
- **Razón.** El enunciado pide, si se sube la frecuencia, mostrar que nextpnr cierra y recalcular el presupuesto. En el VQ100 no se puede ni ubicar el PLL; el TQ144 responde la pregunta que queda (R1 sí cerraría, R0 no). El duplicador tiene su propio RTL, que no compite: traerlo a `rtl/` cambiaría la lista de fuentes del oficial.
- **Qué se pierde.** El TQ144 no es la placa. `make p7-doble` necesita que la rama exista en el clon.

### T105. Amdahl se aplica por fase del tick, en dos ventanas: la respuesta y el kernel (16/11)

- **Decisión.** S = 1 / Σ (f_i / F_i) con una fracción por fase. F_i predicho sale de aplicar el modelo de costo de la variante nueva a las instrucciones de la fase; la detección se escala con la vuelta del sondeo. Se informa sobre la respuesta (lo que mide el testbench oficial) y sobre el kernel (lo que dan los MOPS), con la estimación de la clase 7 y con el costo medido.
- **Razón.** Con una sola fracción (f de la media) no se puede predecir el segmentado ni el barrel, que cambian el costo de todas las instrucciones. Por fase, la diferencia entre predicho y medido queda localizada: es la detección del sondeo y el costo del salto tomado.
- **Qué se pierde.** La predicción usa los conteos medidos del programa: no predice cambios de programa, salvo los de la extensión, cuyo programa sí se midió.

### T106. Ops/W y energía de la edición ASIC con la potencia del flujo de la factibilidad (16/11)

- **Decisión.** Se copian a `docs/mediciones/asic/` las tablas de potencia y de corridas de la pieza G, sin cambios y con su procedencia, y `tools/p7/tablas.py` calcula Ops/s, Ops/W y energía con la definición de T100. Ops/W usa la potencia de la ventana de cálculo; la energía por decisión, la de la ronda 3 (calculada) y las de las rondas 1 y 2 (estimadas sumando sondeo).
- **Razón.** El encargo pide los números del ASIC sin correr LibreLane. La placa no tiene medidor.
- **Qué se pierde.** Solo hay base y segmentado. El barrel, la extensión y el fondo no tienen Ops/W.

Las decisiones T87 a T99 son del paquete P6 de R1 y R2 y las T100 a T119 del paquete P7, trabajados en paralelo el 16/11 en otras ramas. Las del paquete P8 parten en T120.

### T120. El SCLK real se mide con un bitstream aparte, sin el SoC (16/11)

- **Decisión.** `rtl/medidor/medidor_spi.v` es un diseño propio que solo escucha la maestra y muestra en los 7 segmentos el período de SCLK, el período entre precios, la duración de `CS_n`, el tiempo libre mínimo y la cantidad de transacciones. Responde `0x00` por MISO. Se graba el 26/11 antes que los peldaños.
- **Razón.** El SCLK real decide entre R0 y R1 (árbol, regla 3) y no hay garantía de tener un osciloscopio ese día. Ponerlo dentro del SoC cambiaría el hardware de R0, R1 y R2, que ya pasaron la puerta; además, junto a R0 no cabe (quedan 197 celdas y el medidor usa 611).
- **Qué se pierde.** Unos minutos de maestra: mientras está grabado el medidor, el grupo no opera.

### T121. El molde de R0 se construye desde el commit de R0 (16/11)

- **Decisión.** `make r0-molde` extrae las fuentes del commit de R0, sintetiza con la memoria llena de un patrón al azar y guarda el molde solo si `icebram` con `sw/trade.hex` sobre él da R0 byte por byte.
- **Razón.** Una síntesis desde otro commit da otra ubicación (T62), y el molde tiene que ser del mismo hardware que el bitstream que pasó las puertas. Con la comparación byte por byte no hay que confiar en que el molde es el correcto: se comprueba.
- **Qué se pierde.** Nada. La comparación corre en la integración continua.

### T122. `retune` cambia los umbrales solo si mejora la media sin empeorar el percentil 5 ni el peor bloque (16/11)

- **Decisión.** `tools/retune.py` evalúa 77 pares (entra, sale) de `max_media` con las reglas nuevas en los bloques de la práctica y en 80 series de las familias plausibles. Elige otro par solo si sube la media en más de 0,2 % sin bajar el percentil 5 ni el peor bloque de la práctica. Los gestores 2 y 3 del fondo quedan una unidad más abajo y más arriba que el supervisor, como en la tabla actual.
- **Razón.** Es el principio 4 del proyecto. Con la media sola, la herramienta habría cambiado los umbrales incluso con las reglas publicadas (entrar a 1, salir a 2), con peor percentil 5: habría sido sobreajuste a la práctica. Con el criterio completo, las reglas publicadas devuelven los umbrales actuales y los bitstreams guardados byte por byte, y eso es el control.
- **Qué se pierde.** Con comisión de 10 y caja de 1 000 el fondo pierde contra comprar y mantener en la práctica y `retune` no lo cambia, porque ningún par mejora la media sin bajar el percentil 5. Es conservador a propósito.

### T123. La matriz de P8 corre en el gemelo y la columna de R2 se deduce de la de R1 (16/11)

- **Decisión.** Período, SCLK por período, largo de ronda y comisión con caja se corren en el gemelo (`tools/p8/matriz.py`). R2 no tiene columna propia: el vigilante solo se dispara con 5 precios sin escritura en `DECISION`, y en todas las celdas R1 escribe una vez por precio.
- **Razón.** El gemelo está validado contra el RTL de R0 y de R1 y corre las 56 celdas en 10 segundos, incluida una ronda de 200 000 ticks. La matriz de la puerta ya probó el vigilante por el RTL en sus 56 casos.
- **Qué se pierde.** Una prueba directa del vigilante en esas celdas. El argumento cubre el disparo; no cubre una falla del vigilante mismo, que tiene su testbench y su prueba formal (P5).

### T124. El árbol usa 115 kHz aunque R1 responda desde 110 kHz (16/11)

- **Decisión.** Regla 3 del árbol: con SCLK bajo 115 kHz en la ronda 3, compite R0. Es la cifra que fijó Nicolás con el programa de P3. Con el programa de P5, R1 responde a tiempo desde 110 kHz.
- **Razón.** Deja 5 kHz de margen para el error del medidor (un ciclo en 217) y para un SCLK que no sea estable. La combinación es improbable: el testbench del curso usa 1 MHz.
- **Qué se pierde.** Si la maestra usara entre 110 y 115 kHz, competiría R0 cuando R1 habría podido.
- **Confirmada por Nicolás (16/11).** "Prefiero dejar margen sobre el límite medido."

### T125. La factibilidad pasa a `main` como archivo y las tres ramas sin integrar se borran con una etiqueta (16/11)

- **Encargo de Nicolás.** Revisar qué tiene cada rama que no esté en `main`, traer a `main` la evidencia que citen el informe, el README o la defensa, dejar una etiqueta de archivo por rama y borrarlas.
- **Qué tenía cada una.** `frente-a` y `frente-b`: nada que falte. Cada archivo que cambiaron está en `main` con el mismo contenido en algún commit; las diferencias en el `Makefile`, el README, la integración continua y los documentos de estado y decisiones son de las integraciones (`integra-a` e `integra-b`), que renumeraron sus decisiones TA1 a TA7 y TB1 a TB12 como T25 a T43. `factibilidad-fondo`: la carpeta `factibilidad/` (825 archivos, unos 9,5 MB), las decisiones T45 a T49 y la sección del tramo en `docs/estado.md`, ninguna en `main`.
- **Qué se cita.** La defensa (`docs/defensa/fondo.md`, `resumen.md`, `cifras.md`, `extension.md` y `preguntas.md`), `docs/fondo.md`, `docs/extension_isa.md`, `docs/codiseno.md` y `docs/decisiones.md` usan cifras que solo estaban en esa rama: +0,007 y -0,005 puntos del fondo contra `max_media`, el `ema` de 60 a 167 celdas, el k variable que baja la mínima a 39,2 MHz, el multiplicador de 1 338 celdas, las 35 instrucciones por gestor, entre otras. `tools/p7/doble_frecuencia.sh` extraía la rama para correr.
- **Decisión.** La carpeta `factibilidad/` entra a `main` completa y sin integrar (nada de la raíz la usa), con `factibilidad/cierre.md` (la sección del estado de la rama) y T45 a T49 en este archivo. Las rutas de la máquina en que se corrió se reemplazan por variables (`factibilidad/README.md`, "Procedencia"); ninguna cifra cambia. Cada rama queda en una etiqueta anotada, `archivo/factibilidad-fondo`, `archivo/frente-a` y `archivo/frente-b`, y después se borra. `make p7-doble` extrae la etiqueta en vez de la rama.
- **Alternativa descartada.** Traer solo las mediciones. Se pierden los scripts que las producen, y la regla del proyecto es que cada cifra salga de un script del repositorio.
- **Qué se pierde.** Nada: los commits siguen en las etiquetas. La carpeta suma 9,5 MB al repositorio.

### T126. El profesor confirma que cualquier decisión de diseño es válida, y el Espino multihilo con ella (16/11)

- **Qué se supo.** El profesor Jorge Gómez le confirmó en persona a Nicolás, el 16/11, que se puede modificar lo que uno quiera y que cualquier decisión de diseño es válida. Nicolás le habló del Espino multihilo y respondió que está perfecto.
- **Decisión.** El barrel puede competir y ya no depende de una respuesta pendiente. La regla 1 del árbol (`docs/arbol_decision.md`), que llevaba a R0 si el ayudante decía que el Espino multihilo no es Espino, queda resuelta, y la pregunta 5 del checklist del 26/11 ya no se hace.
- **Reconfiguración durante una ronda.** No se le mencionó en particular. Se considera cubierta por la respuesta general, **sin confirmación específica**. R2 compite si pasa sus puertas (árbol, regla 5); solo una prohibición explícita del curso lo deja fuera. La pregunta 6 del checklist del 26/11 queda como confirmación opcional.
- **Qué cambia.** El árbol, el checklist del 26/11, el banco de preguntas (9, 125 y 154) y los documentos que planteaban la duda (`docs/espino_barrel.md`, `docs/extension_isa.md`, `docs/fondo.md`, `docs/tabla_vigilante.md`, `docs/codiseno.md` y `docs/defensa/`). Las secciones antiguas de `docs/estado.md` y la carpeta `factibilidad/` conservan la duda tal como estaba en su fecha.

### T127. La caída de frecuencia del segmentado es de la síntesis, y la tabla de co-diseño usa el valor actual (16/11)

- **Encargo de Nicolás.** Investigar por qué la frecuencia mínima del segmentado bajó de 51,6 a 45,3 MHz desde P1, y asegurar que la tabla de co-diseño y el informe usen el valor actual.
- **Resultado** (`make p7-caida-seg`, `docs/mediciones/p7/caida_segmentado.txt`, `docs/bitacora/caida_segmentado.md`). Con el mismo script se reproducen los dos valores. El salto está en `c293cf4` (tabla y vigilante en `pochoco_soc.v`): la netlist pasa de 802 a 798 LUT4 con los mismos acarreos, flip-flops y BRAM, y la equivalencia formal entre el SoC de P1 y el actual pasa, con control negativo. En 40 semillas las distribuciones no se solapan (mediana 53,45 antes y 47,88 después), así que no es ruido de una semilla. El mismo RTL leído en diez órdenes da cuatro netlists con medianas de 47,88 a 53,59 MHz.
- **Decisión.** La tabla de co-diseño y el informe siguen con el valor actual, 45,34 de mínima y 47,20 de mediana, medido en la misma corrida que las otras variantes. `docs/codiseno.md` y el informe dicen que una síntesis tiene unos 6 MHz de incertidumbre en la mediana y que diferencias de ese tamaño entre variantes no se atribuyen al diseño; el informe toma esas cifras de `make report`.
- **Alternativa descartada.** Elegir el orden de lectura que da la mejor frecuencia. Mejora el número sin cambiar el diseño, y obligaría a hacer lo mismo con cada variante para que la tabla siga siendo comparable.
- **Qué se pierde.** Nada: el segmentado no compite y cierra a 25 MHz en 40 de 40 semillas.

### T128. Evaluación de `zscore`: semilla 4 reservada y criterios fijados antes de medir (16/11)

- **Encargo de Nicolás.** Evaluar con el protocolo completo la regla `zscore` de Vicente Calderón (40 957 contra 25 973 de `max_media` en los 20 000 ticks de práctica), en `ref/` y en una rama aparte, sin tocar R0, R1 ni R2.
- **Semillas.** La exploración (meseta, umbral, memorias y fondo de gestores `zscore`) se hace solo con la semilla 0. La semilla 4, que nadie había usado, queda reservada y se corre una sola vez, con la lista de finalistas escrita antes en `docs/bitacora/zscore.md`. Las semillas 1, 2 y 3 ya se usaron para elegir o confirmar otras cosas (T46), así que no sirven como confirmación nueva.
- **Criterios, los mismos de antes.** (1) El protocolo de `ref/protocolo.py` contra `max_media`: media y peor bloque de la práctica, media y percentil 5 de los remuestreos, y ninguna familia baja más de 1 %. (2) El criterio de corte del arnés (T45 y T46): mejora los puntos esperados del torneo en más de dos errores estándar sin empeorar el percentil 5 de la competencia de tres rondas, a 2000 y a 20 000 ticks (interiores, con la vista de parada como confirmación), en el campo mixto con 10 rivales y con la sensibilidad a los otros campos. Se informa además la probabilidad de ganarle cabeza a cabeza a `max_media` en una ronda y en una competencia de tres rondas.
- **Qué se acepta.** `zscore` (o una variante) gana si cumple el criterio (2) con la semilla reservada. El criterio (1) se informa completo; si falla en alguna familia de estrés se dice cuál y cuánto. Ganar en la serie de práctica completa no cuenta: es la serie con la que Vicente eligió los parámetros.

### T129. `zscore` no reemplaza a `max_media`, ni sola ni en un fondo (17/11)

- **Resultado** (`docs/zscore.md`, `docs/mediciones/zscore/`). Con la semilla reservada, los cuatro finalistas no pasan el criterio de corte a 2000 ni a 20 000 ticks. La regla de Vicente pierde 0,094 puntos H3a por ronda a 2000 ticks y 0,222 a 20 000; gana el 41 % de las rondas de 2000 ticks en las familias plausibles. En el protocolo gana en los 10 bloques de práctica (+346 +- 321) y pierde en los remuestreos y en las cuatro familias plausibles. Ninguno de los 81 puntos de la grilla gana; el centro de la meseta está en z = 1,5 con la desviación de memoria 128, no en 2,5.
- **Por qué 40 957 en la práctica.** Es el máximo de la grilla en la serie con que se eligió (sus vecinos dan entre 22 421 y 37 004), y la ventaja por bloque, compuesta diez veces sobre la misma trayectoria, se convierte en un 58 % más.
- **Fondo de gestores `zscore`.** Tres bandas anidadas de la misma regla con la misma salida votan igual que la del medio: el fondo no puede superar a su mejor banda.
- **Decisión.** `max_media` sigue en R0, R1 y R2. `zscore` queda como experimento documentado. El único resultado a favor (z = 1,5 en las familias plausibles a 20 000 ticks: +0,044 a +0,050 puntos H3b, empate en H3a) aparece en un subconjunto elegido después de mirar y depende de dos respuestas del 26/11; queda como decisión de Nicolás en `docs/pendientes_nicolas.md`.
- **Qué se pierde.** Si la serie oculta fuera la de práctica, `zscore` habría ganado. Elegir por eso sería ajustarse a una serie que el enunciado no deja guardar.

### T130. El largo del trozo del remuestreo cambia el signo de `zscore` contra `max_media` (17/11)

- **Origen.** Prueba de Nicolás: con trozos de 10 a 100 ticks hay empate; con trozos de 250 o más y en tramos reales contiguos, `zscore` (z = 2,5) gana entre +150 y +430 a 2000 ticks.
- **Medición** (`ref/zscore/trozos.py --puntos`, `docs/mediciones/zscore/trozos.txt`, `docs/zscore.md`, sección 4.5). El remuestreo del protocolo usa trozos de 100 (`ref/series.py:75`). Se reproduce: trozo 50, -56 +- 32; 100, +7 +- 37; 250, +160 +- 36; 1000, +313 +- 43, y en puntos con trozos de 1000, +0,019 en H3a y +0,107 en H3b. Con parámetros elegidos en una mitad de la práctica y probados en la otra, `zscore` gana con trozos largos en las dos direcciones (+424 y +567 con trozos de 1000; +137 y +307 con 250) y empata con 50. En series del modelo calibrado los trozos largos no favorecen a `zscore`: el efecto es propio de la práctica, que tiene algo a escalas de cientos de ticks que el modelo no reproduce. La evidencia con muestras independientes sigue siendo un error (+346 +- 321 en los 10 bloques).
- **Qué cambia.** La explicación de los 40 957 de `docs/zscore.md` se corrige: no es solo sobreajuste. T129 sigue vigente como resultado del criterio fijado antes de medir; la decisión de qué algoritmo compite es de Nicolás (`docs/pendientes_nicolas.md`, decisión 1). Nada cambió en R0, R1 ni R2.
- **Pregunta al banco.** La 156: "¿Por qué no usaron la regla que da 40 957 en la práctica?"

### T131. Tarea B: ninguna candidata mejora a `max_media` en todo; la salida a +0,5 queda condicionada (17/11)

- **Encargo de Nicolás.** Último intento con el generador, acotado a la noche: probabilidad de ganarle cabeza a cabeza a la mejor regla y puntos esperados contra un campo de rivales que también operan reversión; mismo protocolo; aceptar solo si además gana en la serie registrada el 26/11; si nada gana, documentar y cerrar.
- **Método** (`docs/generador_b.md`). Campo nuevo `variados` (todos los rivales son reversiones). Exploración con la semilla 0 (78 candidatas), tres finalistas fijados antes, semilla 5 (nueva) una sola vez.
- **Resultado.** `max_media` con salida a +0,5 unidades pasa el criterio de corte en `variados` a 2000 y 20 000 ticks y no pasa en el campo mixto; pierde en los bloques de la práctica (-173 +- 137) y en los remuestreos (-22 +- 16). Las otras dos finalistas no pasan.
- **Decisión.** No cambia nada. La candidata queda condicionada a dos datos del 26/11 (que los rivales operen reversión y que gane en la serie registrada, si se puede usar) y es decisión de Nicolás (`docs/pendientes_nicolas.md`, decisión 3). El intento de identificar mejor el generador no dio un modelo nuevo: el tema se cierra.

### T132. Revisión adversarial P10: sin hallazgos críticos ni altos; el arreglo del esclavo SPI queda sin integrar (17/11)

- **Resultado** (`docs/revision_p10.md`, `docs/bitacora/p10.md`). Un revisor que no participó en el diseño leyó el barrel, la extensión, la tabla, el vigilante y `sw/fondo.s`, agregó pruebas (`make p10-*`, fuera de la integración continua) y repitió la puerta de simulación de R1 y R2 desde cero: todas las mediciones y los sha256 de los bitstreams son los registrados.
- **Hallazgo 1 (bajo, medio si la maestra mueve SCLK con `CS_n` en alto).** El esclavo SPI del curso puede contar precios fuera de una transacción. Arreglo en `p10-arreglo-1`, sin integrar: cambia hardware que ya pasó su puerta. Decisión de Nicolás (`docs/pendientes_nicolas.md`, decisión 4).
- **Hallazgo 2.** El medidor del 26/11 no veía esa condición. El arreglo (`p10-arreglo-2`) se integró: el medidor no es parte de ningún peldaño, y pasó `make medidor` (70 comprobaciones, 6 de 6 controles negativos, 10 de 10 semillas, bitstream ruteado).
- **Observaciones.** Vuelta del número de tick a los 16,7 millones de ticks (no afecta la competencia), costo de no reiniciar la placa entre rondas (decisión 5), entradas del SPI sin pull-up y supuesto de maestra de modo 0.

### T133. Regla nueva: "espera" con banda 60 en R0, R1 y R2; en R1 y R2, la regla en el hilo 0 del barrel (17/11)

- **Decisión de Nicolás, con su razón textual:** "Opción R-a con F-a, en los tres peldaños. Razón: es la que no pierde si la hipótesis de la normalización resulta falsa."
- **La regla** (`ref/cotas.py`, `docs/cotas.md`): parte en caja; al ver 100 compra 63 (repetido), al ver 255 vende 63 (repetido); después de haber visto los dos extremos, compra con p ≤ 160 y vende con p ≥ 195; entre medio mantiene la posición.
- **R0**: `sw/trade.s` corre la regla en el Espino base. **R1 y R2**: el hilo 0 del barrel corre la misma regla y los hilos 1 a 3 quedan en espera; los umbrales salen de la tabla en BRAM. El hardware de los tres peldaños no cambia: el programa y la tabla entran por `icebram`.
- **Alternativas y lo que se pierde** (`docs/pendientes_nicolas.md`, decisión 0): comprar 20 al inicio con banda 70 (mejor percentil 5, pierde hasta 2 100 si la hipótesis es falsa); compra con banda 40 (32 149 en la serie Meta, peor en la población); mantener el fondo que vota (sin ganancia medida, más puntos de falla); no cambiar (9 722 en la serie Meta).
- **Pendiente**: preguntar el 18/11 si cada ronda se normaliza por separado; con los minutos reales de Alpaca, repetir el paso 5 antes del 22/11 y ver si cambia la banda.
- `make report` y `make tabla-3-1` leen la serie nueva (`data/practica_meta.csv`). El informe, el README y la defensa no se reescriben hasta que la regla esté fija en los peldaños y se sepa cómo se normaliza (`docs/obsoleto_serie_meta.md`).

### T134. Población real: todas las ventanas de 20 000 minutos, con los datos fuera del repositorio (18/11)

- **Pedido de Nicolás:** bajar los minutos de 2022 a 2024 con Alpaca, armar todas las ventanas de 20 000 ticks normalizadas con sus extremos y repetir el paso 5.
- **Datos.** `tools/datos/alpaca.py` lee la clave de `~/.alpaca.env` (o del entorno) y escribe en `$P4_DATOS/minuto`, fuera de cualquier repositorio; en el repositorio solo quedan el descargador, los programas y las cifras agregadas. Serie de cada empresa: un precio por minuto de la sesión regular (9:30 a 15:59 de Nueva York), cierre del minuto, ajustado por splits, y los minutos sin operaciones repiten el último precio. Es la construcción que reproduce `data/practica_meta.csv` y la captura de Tesla del 18/11 byte a byte (`docs/mediciones/clase_18nov.md`).
- **Ventanas.** Todas las posiciones de inicio (paso 1): 1 368 253 ventanas en las cinco empresas. Solo largo 20 000, porque la clase confirmó que cada ronda dura 20 000 ticks; los largos 2 000 y 5 000 del 17/11 dejan de ser el caso.
- **Alternativas y lo que se pierde.** Una ventana por día o cada 39 minutos: 10 a 400 veces menos cálculo, sin cambiar las medias (ventanas vecinas son casi iguales). Se eligió paso 1 porque el evaluador en C con OpenMP lo corre en unos 12 minutos y así no hay que elegir un inicio. Lo que no cambia con ninguna opción: con 20 000 minutos, cada empresa tiene unas 15 ventanas que no se solapan, así que las conclusiones se informan también por empresa, por año y sin solapar.
- **El caso d (la ronda como trozo de una ventana más larga) no se repite**: la ronda de Tesla tiene 20 000 precios y toca 100 y 255.

### T135. El rival de la ronda de Tesla entra al campo del torneo como `unavez 100 220` (18/11)

- **Pedido de Nicolás:** agregar al campo de rivales al grupo que ganó la ronda de Tesla ("compra al ver el 100, vende con precio de 220 o más y no vuelve a entrar").
- **Cuál de las lecturas.** Comprar 63 repetido desde el primer 100 hasta ver 220 o más, y desde ahí vender 63 repetido, da 21 467 en la serie de Tesla: la cifra exacta de la maestra. Comprar solo en los ticks con precio 100 da 21 500, y comprar y vender una sola vez da 17 550. Se usa la primera (`planb.UnaVez`, tipo `unavez` de `evaluar.c`, validada contra Python).
- **Dónde entra.** En el campo "con extremos" del torneo de `ref/cotas/reales_experimento.py`, y en un campo nuevo donde uno de los 9 rivales es siempre él. `ref/cotas/experimento.py` (la población modelada del 17/11) no se cambia, para que sus mediciones sigan reproduciéndose tal como están.

### T136. Exploración de diez ideas sobre la población real: método, y la decisión queda para Nicolás (18/11)

- **Pedido de Nicolás:** evaluar diez ideas (programación dinámica, grilla, torneo en sombra, detector de régimen, cuantiles, contadores saturados, cobertura contra rivales, final de ronda, precio inicial, salida por caída) y tres combinaciones sobre la población real, con un filtro previo por idea, ajuste y validación por años y por empresas, y torneo de 3 rondas; presentar qué regla compite sin decidir. Corte del algoritmo: 22/11. Documento: `docs/exploracion_ideas.md`.
- **Motor en Python** (`ref/cotas/ideas.py`) y no en C: el pedido dice "solo Python", y a 0,18 µs por tick la población completa con una estrategia toma unos 4 minutos con 24 núcleos. Se validó contra la referencia (18 779 en Tesla) y contra la caché en C (0 diferencias en 3600 ventanas). Lo que se pierde: las finalistas en la población completa tomaron 103 minutos en vez de minutos.
- **Muestra estratificada** de 240 ventanas por empresa y año de inicio (3600), semilla 18; las finalistas, en las 1 368 253 ventanas. **Torneo de 3 rondas** con el mismo programa en las tres, el rival de Tesla siempre presente y 8 rivales del campo de `reales_experimento.py`; puntos lineales de 0 a 2 sobre la suma de las tres rondas. Alternativa descartada: el torneo de una ronda del paso 5, que no refleja que la competencia suma tres rondas con el mismo programa.
- **Filtros.** Se aplicaron los del pedido. Las ideas 7, 8 y 10 no traen filtro: se informa un diagnóstico y pasan al barrido. Las ideas que no pasan (1, 5 y 6) no se barren; para la tabla se informa un representante elegido antes de ver resultados. El filtro de la idea 4 se corrigió durante el trabajo: la primera versión elegía el indicador mirando la validación.
- **Idea 12 agregada:** banda asimétrica (compra y venta por separado), porque en la ronda de Tesla decidió el nivel de venta. Su óptimo es 140/215 en los dos ajustes, la banda 40.
- **Resultado:** ninguna idea ni combinación le gana a la banda 40 fuera de muestra, ni en la muestra ni en la población completa (las cinco finalistas quedan entre -4 y -67 de patrimonio medio en su propia validación). La regla de los peldaños no se cambió; la decisión (banda 40 sola, banda 60 sin cambios, o banda 40 con un agregado) queda en `docs/exploracion_ideas.md`, sección 6.

### T137. Ideas 13 y 14 sobre la banda 40: resultados negativos, la decisión sigue en la sección 6 (19/11)

- **Pedido de Nicolás:** niveles de la banda según el orden de los extremos y reloj de día de mercado, cada una con su filtro, con el protocolo de T136; la primera sola sin `espera_banda40`. En el documento son las ideas 13 y 14 (en el pedido, 11 y 12), para no chocar con la numeración de la primera tanda.
- **Idea 13 por composición:** como el caso queda fijado al entrar a D y las fases A a C son iguales para todos los pares, la regla con un par por caso se arma ventana por ventana con las bandas de cada par (30 bandas en vez de 900 simulaciones). Se comprobó contra la simulación directa: 0 diferencias.
- **Error estándar de la idea 14 por la fecha del tick:** con los grupos por inicio de ventana de la tabla 2, la mitad de los minutos del día salía significativa. Alternativa descartada: dejar la agrupación del protocolo, que habría dado por bueno el salto. Lo que se pierde: la comparación directa con los ee de la tabla 2.
- **La regla de la idea 14 se probó** aunque el salto no pasó por sí solo, porque el criterio del pedido ("algún efecto") se cumplió por los minutos del día. Perdió en las 9 variantes.
- **Resultado:** ninguna de las dos le gana a la banda 40 fuera de muestra. La regla de los peldaños no se cambió.

### T138. Mano a mano contra el rival de Tesla y variante del caso S: se presentan, no se deciden (19/11)

- **Subconjuntos de la población completa** para las dos validaciones, en vez de la muestra: aquí no se ajusta ningún parámetro, y la población ya estaba evaluada para las bases. Lo que se pierde: nada del protocolo, porque no hay elección en el ajuste.
- **El caso de cada ventana** sale de la corrida de la variante (a), que lo informa, en vez de una pasada aparte por las 1 368 253 ventanas.
- **Variante (b) en las tres bandas:** la posición total queda en un tercio del patrimonio, fijado al recomprar, sin reajustes tick a tick (reajustar cada tick haría órdenes de una acción). Alternativa descartada: escalar cada banda a un tercio (un noveno por banda), que no es lo que dice el pedido.
- **Resultado:** (a) y (b) bajan la media del caso S y los puntos en los tres subconjuntos. La regla de los peldaños no se cambió.

### T139. Política por régimen filtrado: se presenta, no se decide (19/11)

- **Otras acciones:** 20 por grupo de sectores, las de mayor monto transado en enero de 2020 (dato del inicio del período), en vez de las de mayor capitalización hoy. Lo que se pierde: nada en cantidad; el sesgo de supervivencia sigue, porque todas existen hoy.
- **Suplentes por días faltantes:** una elegida falla si la receta de sesión le deja menos del 98 % de los días (BKNG, REGN, BLK). Alternativa descartada: cambiar la receta para aceptar días con menos de 200 minutos con operaciones; el pedido decía usar la receta calibrada.
- **Reglas de paso fijadas antes de correr los filtros**, con el error estándar mayor entre grupos por fecha (20 y 60 días) y en dos sentidos (fecha y empresa). F1 por grupo de fases, porque el módulo D actúa solo en la fase D. F2 por año de inicio en vez de por caso S y B, porque ver el 255 antes de caer d hace que la ventana sea del caso B.
- **Módulos D y E descartados en sus filtros** (F1 no pasa en la fase D; F3 no pasa). Regla de Nicolás: con F1 solo en A a C, se sigue con el módulo A.
- **Torneos de 3 rondas contra el rival con los mismos sorteos para las dos estrategias**, como en la sección 10. La primera versión del reporte del examen sorteaba distinto por estrategia; se rehízo desde la caché, sin volver a evaluar.
- **Resultado:** el módulo A no cumple el criterio de la sección 9 del diseño. La regla de los peldaños no se cambió.


### T140. Política óptima del paseo normalizado: se presenta, no se decide (19 y 20/11)

- **Estimador de v²:** S2/t acumulado, por decisión de Nicolás después de G1; la ventana de 2000 se comparó en G2 y no la mejora (-26, ee 28). Las diferencias de 10 ticks calibran mejor en paseos y peor en datos reales, así que quedaron solo como información.
- **Variante V3 log**, elegida en G2 por puntos de torneo en las otras acciones y confirmada por Nicolás. V2 gana más en patrimonio medio pero tiene menos puntos y pierde más torneos contra el rival.
- **Referencia alineada con la placa antes de las guardas y el examen:** clase de v² con cortes en 1/64 (64 S2 ≥ N_j (t - 1)), histéresis de 64 ticks y tabla comprimida. Lo que se pierde: nada medible (en las otras, +312 con la clase de placa contra +296 con la clase exacta, las dos con la tabla comprimida). La alternativa, evaluar con la clase exacta, dejaba a la referencia sin equivalencia posible con el reparto de hilos pedido.
- **Criterio, punto 3 cambiado por Nicolás antes del examen:** pierde a lo más 10 % de los torneos de 3 rondas contra el rival de Tesla. Regla de elección de guardas fijada por él, también antes del examen: más puntos entre las que pierden a lo más 5 %; si ninguna, la que menos pierde entre las que superan en puntos a la banda 40. Resultado: V3 log con (b) (nunca más de media posición en la fase A), que además cabe en 512 bytes.
- **Alternativa V1 log con a16 y c preparada sin examen**, para no hacer una tercera mirada a las cinco empresas sin pedirlo.
- **Resultado:** V3 log con (b) no cumple el criterio (puntos 1 y 2; cumple el 3). En la población de las cinco es la mejor de las tres, +124 (ee 77). Su ganancia depende de la proporción de casos S, con el equilibrio cerca de dos tercios. La regla de los peldaños no se cambió.

### T141. V5 contra el campo esperado: se presenta, no se decide (20 y 21/11)

- **Lectura del criterio fijada antes de correr:** el índice son dos cifras (no queda debajo y gana) y el punto 1 exige superar a las dos varas en las dos por más de 2 ee pareados. Alternativa: promediarlas en una sola, que daría el punto 1 por cumplido; se informa, pero no es la que se fijó.
- **Reparto del 60 % de "extremos o Fila 5" en mitades** (30 % extremos puros, 30 % Fila 5). El pedido no lo separa; como el índice es lineal en los pesos, las tablas por rival permiten rehacerlo.
- **Extremos puros como "una vez"** (compra desde el primer 100, vende al ver 255 y no vuelve), como dice el pedido, y no como `espera` de la caché, que vuelve a comprar en un segundo 100. Difieren en 21 de 6 768 ventanas del caso S.
- **Finalistas en forma de placa:** fase A en 2 bytes por celda y motor V2 comprimido de 8 tramos con clase de histéresis, para que lo medido sea lo que cabría. Lo que se pierde frente a las tablas completas: 0,4 de nd y 0,5 de g.
- **Margen por deslizamiento fuera de C1:** suma +0,5 / +0,9 pero sube el déficit contra la banda 40 de 111 a 148; queda como ajuste opcional.
- **Programación dinámica relativa no corrida:** costo alto en Python puro y ganancia acotada (a lo más 4,9 de nd y 6 de g sobre C1, sin pasar a la banda 40). Quedó formulada.
- **Resultado:** ningún candidato cumple el criterio. C1 domina a V4b. La banda 40 sola es la mejor en déficit ponderado y en nota esperada; la banda 30 sola, en "no queda debajo". La regla de los peldaños no se cambió.
