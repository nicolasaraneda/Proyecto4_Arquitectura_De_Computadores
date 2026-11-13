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
3. La maestra real está disponible un solo día, el 19/11. El bitstream de competencia solo puede contener hardware que haya pasado esa prueba.

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

