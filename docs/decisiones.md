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
