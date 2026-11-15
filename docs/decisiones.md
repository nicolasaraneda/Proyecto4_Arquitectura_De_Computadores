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

### T50. Compite el fondo en un chip: opción b (15/11)

- **Decisión de Nicolás, con su razón textual.** "opción b, tomemos riesgos".
- **Qué significa.** Compite el diseño integrado: Espino barrel de 4 hilos con el fondo mínimo, la extensión de la ISA, la tabla de parámetros en BRAM y el vigilante. Es la opción 4 de la tabla comparativa de la factibilidad (`docs/estado.md`, tramo 6): 1071 celdas, 13 BRAM y 46,8 MHz de frecuencia mínima medidos. El algoritmo base pasa a ser `max_media` (T51). Se construye una escalera de bitstreams para la maestra del 26/11: R0 (core base con `max_media`, el respaldo), R1 (fondo en un chip sin vigilante) y R2 (con vigilante). Compite el peldaño más alto que pase las tres puertas: simulación, placa y maestra.
- **Riesgo aceptado a sabiendas.** Según lo medido, este diseño no suma puntos esperados contra `max_media` sola (+0,007 a 2 000 ticks y -0,005 a 20 000) y agrega riesgo de falla en vivo. Se elige por lo que representa como co-diseño.
- **Alternativa descartada.** La recomendación del tramo de factibilidad (opción 2): segmentado con `emad` y `max_media`, con el barrel y el fondo en la edición de exhibición.
- **Qué se pierde.** Entre 16,5 y 18,5 días de persona de los 33 que quedaban hasta el 25/11, y margen para reaccionar a una falla de placa. Quedan fuera de la competencia, con sus números: compras residuales (`ejec:m=8`), guardia, tope de pérdida, ancla en comprar y mantener, aprendizaje en vivo, predictor de patrones y doble frecuencia.
- **Fecha de corte.** Si el 22/11 a medianoche R1 no pasó completa la puerta de simulación, R0 pasa a ser el titular y el fondo va a la edición de exhibición.

### T51. `max_media` reemplaza a la regla base en `trade.s` y en la referencia (15/11)

- **Decisión.** `sw/trade.s` entra cuando `dev < -96` (3 unidades bajo la media) en vez de `dev < -128`. Es la única línea de código que cambia. En `ref/trader.py`, `MaxMedia` es la estrategia oficial (`trader.Oficial`) y la que usan `correr`, la línea de comandos, `tools/equiv.sh`, `tools/equiv_gemelo.sh`, `tools/sim_bitstream.sh` y `ref/protocolo.py --binario`. `ReglaBase` se conserva sin cambios, con la entrada a 4 unidades, porque el protocolo compara a los candidatos contra ella (`--comparar`, `--meseta`).
- **Razón.** Decisión de Nicolás (sección 16.0 del plan). Es el único cambio con retorno medido: +0,04 puntos esperados del torneo sobre la regla base a 2 000 ticks, +0,7 % de patrimonio en los remuestreos y +1,4 % en las familias plausibles, con semilla reservada.
- **Conflicto con el principio 4, que se avisa.** El principio pide mejorar la media y el peor bloque fuera de muestra. `max_media` no lo cumple en los 10 bloques de práctica: media 11 043 contra 11 069 y peor bloque 9 620 contra 9 720. En la serie completa de práctica da 25 973 contra 27 062. La sección 16 del plan manda sobre la 5, y las diferencias en los bloques están dentro del error (238), pero en la defensa hay que poder explicar por qué la tabla del punto 3.1 muestra un número menor que el de la versión anterior.
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
