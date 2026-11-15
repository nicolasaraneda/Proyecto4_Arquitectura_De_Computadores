# Espino segmentado: pipeline de 3 etapas en la FPGA

Documento de estudio del core segmentado. Parte de cómo funciona el Espino base, explica qué se cambió y por qué, cada riesgo de datos y de control con su solución, cómo se verificó y qué se midió. Todos los números salen de scripts del repositorio y al final está el comando de cada uno.

## 1. Resumen

El Espino base demora 2 ciclos por instrucción, 3 en los loads y 3 en los saltos tomados. El segmentado demora 1, 2 y 2. Es el mismo Espino: la misma ISA, el mismo decodificador, la misma ALU, las mismas interfaces y los mismos nombres que usa el testbench oficial. Cambia el momento en que se lee el banco de registros y en que se decodifica.

| Medición | Espino base | Espino segmentado | Estimado en la clase 7 |
|----------|-------------|-------------------|------------------------|
| CPI de una instrucción de ALU, store o salto no tomado | 2 | 1 | 1 |
| CPI de un load | 3 | 2 | 2 |
| CPI de un salto tomado, `jal` o `jalr` | 3 | 2 | 3 |
| CPI con el mix de la clase 7 | 2,350 | 1,350 | 1,5 |
| MIPS con el mix, a 25 MHz | 10,64 | 18,52 | 16,7 |
| Ppeak en MOPS (25 MHz por instrucciones de ALU por ciclo) | 12,5 | 25 | 25 |
| Respuesta de `trade.s`, promedio y peor caso del testbench | 41 y 44 ciclos | 22 y 26 ciclos | |
| Celdas lógicas, de 1280 | 1083 | 994 | |
| BRAM, de 16 | 12 | 12 | |
| Frecuencia máxima en 10 semillas: mínima, mediana, máxima | 42,4, 43,7 y 45,1 MHz | 51,1, 53,5 y 54,5 MHz | |
| Semillas que cierran a 25 MHz | 10 de 10 | 10 de 10 | |

El core por defecto del repositorio sigue siendo el base. El segmentado se elige al compilar con `-DESPINO_SEGMENTADO` y todas las pruebas del base se repiten sobre él.

## 2. Punto de partida: por qué el Espino base demora 2 ciclos

La ley de hierro dice que el tiempo de un programa es IC × CPI × Tclk. En la Go Board Tclk está fijo en 40 ns: el encapsulado VQ100 no tiene PLL (`docs/mediciones/pll_nextpnr.txt`). IC depende del programa. Lo que el core puede mejorar es el CPI.

En el Espino base una instrucción vive así:

1. Flanco N. La memoria de instrucciones, que es una BRAM con salida registrada, entrega la instrucción. Recién ahora se conocen `rs1` y `rs2`.
2. Ciclo N. El banco de registros también es una BRAM con lectura registrada: se le presentan las direcciones y hay que esperar un flanco. El core no hace nada más. Esa espera es el registro `ops_valid_q` de `rtl/espino_core/espino_id_stage.v`.
3. Flanco N+1. El banco entrega los operandos.
4. Ciclo N+1. La ALU calcula y en el flanco N+2 se escribe el resultado.

Un load agrega un ciclo porque la memoria de datos también es registrada. Un salto tomado agrega un ciclo porque la instrucción que ya se había leído detrás del salto se descarta.

El ciclo de espera no hace trabajo útil. Si las direcciones `rs1` y `rs2` estuvieran disponibles antes del flanco N, el banco podría leer en ese mismo flanco y la instrucción llegaría a ejecución con sus operandos listos.

## 3. La idea, y por qué en la FPGA no es directa

En nuestro Proyecto 3 (el Espino en ASIC) la memoria de instrucciones era una ROM combinacional: la instrucción de la dirección que pide el fetch estaba disponible en el mismo ciclo, antes de registrarse. Con eso el banco de registros leía durante el fetch y desaparecía la espera. Ese core (`EarlyRead = 1`) quedó verificado y medido en ASIC: CPI 1,665 en el juego contra 2,665.

En la FPGA la memoria es BRAM y su lectura es registrada: la instrucción aparece después del flanco, no antes. Se evaluaron dos caminos para tenerla antes.

**Camino A: leer la memoria de instrucciones en el flanco de bajada.** El contador de programa cambia en el flanco de subida. La BRAM lee medio ciclo después, en el flanco de bajada, y su salida queda estable durante la segunda mitad del ciclo. En el flanco de subida siguiente el banco de registros lee con las direcciones de esa instrucción y el decodificador registra su salida. El iCE40 tiene la primitiva para esto: `SB_RAM40_4KNR`, una BRAM con reloj de lectura invertido.

**Camino B: una ROM combinacional solo para `trade.s`**, como en el Proyecto 3. El ensamblador la genera con `--rom`. El programa queda en LUTs.

Hay un tercer camino, el del libro: agregar una etapa de fetch de un ciclo completo. Es el que supone la clase 7 y por eso estima 3 ciclos para el salto tomado. No se construyó porque los dos anteriores dan un salto tomado de 2 ciclos y cierran timing con holgura.

## 4. Las tres etapas

El nombre es el de la clase 7: pipeline de 3 etapas. En el camino A las dos primeras ocupan medio ciclo cada una.

| Etapa | Cuándo | Qué hace | Dónde está |
|-------|--------|----------|------------|
| IF, búsqueda | Primera mitad del ciclo: del flanco de subida al de bajada | El contador de programa `pc_q` direcciona la memoria. La BRAM lee en el flanco de bajada. | `espino_if_stage.v`, `pochoco_ram.v` (bloque `g_neg`) |
| ID, decodificación y lectura de registros | Segunda mitad del ciclo: del flanco de bajada al de subida | La instrucción (`instr_next_i`) entrega `rs1` y `rs2` al banco de registros y pasa por el decodificador. En el flanco de subida se registran los operandos y la decodificación. | `espino_id_stage.v` (bloque `g_pipe`), `espino_register_file.v` |
| EX, ejecución y escritura | Un ciclo completo | ALU, comparación del salto, acceso a memoria y escritura del resultado en el banco. Un load ocupa esta etapa dos ciclos. | `espino_id_stage.v`, `espino_alu.v`, `espino_load_store_unit.v` |

```
            flanco de subida      flanco de bajada      flanco de subida
                   |                     |                     |
 pc_q = dir(i) ----+                     |                     |
                   |--- IF de i ---------|                     |
                   |     la BRAM lee     |--- ID de i ---------|
                   |                     | rs1, rs2 al banco   |--- EX de i (un ciclo) ---
                   |                     | decodificador       | pc_q = dir(i+1), IF e ID de i+1
```

Mientras la instrucción i está en EX, la i+1 pasa por IF e ID en el mismo ciclo. Por eso sale una instrucción por ciclo.

Diagrama de bloques del camino A:

```
          +--------+   dirección    +-----------------+  instr_next   +--------------+
   +----->|  pc_q  |--------------->| BRAM del fetch  |-------------->| decodificador|--+
   |      +--------+  (sube)        | lee en bajada   |      |        +--------------+  |
   |                                +-----------------+      | rs1, rs2                 v
   |                                                         v                 +----------------+
   |  destino del salto                              +---------------+         | decodificación |
   |                                                 | banco de reg. |         | registrada     |
   |                                                 | 2 x 2 BRAM    |         +----------------+
   |                                                 +---------------+                 |
   |                                                    |         ^                    |
   |                                    operandos       v         | dato escrito       v
   |                                   +---------------------+    |            +-------------+
   |                                   | adelantamiento      |----+----------->|     ALU     |
   |                                   | (dato del flanco    |    |            +-------------+
   |                                   |  anterior o BRAM)   |    |              |    |    |
   |                                   +---------------------+    +--------------+    |    |
   +----------------------------------------------------------------------------------+    |
                                                                         memoria de datos <-+
```

Tabla de costo, leída del RTL y confirmada ciclo por ciclo en simulación (sección 9):

| Instrucción | Ciclos | Por qué |
|-------------|--------|---------|
| ALU, `lui`, `auipc`, store, salto no tomado | 1 | Llega a EX con operandos y decodificación listos. |
| load | 2 | La memoria de datos es registrada: en el primer ciclo se pide y en el segundo se recibe y se escribe el registro. El core se detiene un ciclo. |
| salto tomado, `jal`, `jalr` | 2 | La instrucción que venía detrás ya pasó por IF e ID. Entra a EX marcada como no válida y no hace nada: es la burbuja. |

## 5. Riesgos de datos y de control

En el base no existe ninguno de estos riesgos, porque cada instrucción lee el banco después de que la anterior terminó. En el segmentado la instrucción i+1 lee el banco en el mismo flanco en que la i escribe.

### 5.1 Escritura seguida de lectura del mismo registro

`addi x1, x0, 5` seguida de `addi x5, x1, 10`. En el flanco en que la primera escribe x1, la segunda lee x1. Una BRAM del iCE40 entrega en ese caso el valor viejo.

Solución: adelantamiento, en `espino_register_file.v` (bloque `g_bypass`). En ese flanco se guarda el dato que se escribe (`wdata_q`) y un bit por puerto que dice si la dirección leída coincide con la escrita (`fwd_a_q`, `fwd_b_q`). Un multiplexor a la salida de la BRAM elige el dato guardado cuando el bit vale 1. Una dependencia a dos instrucciones de distancia ya lee la BRAM actualizada, así que basta un solo nivel de adelantamiento.

Un detalle que importa en la placa: lo que entrega una BRAM cuando se lee y se escribe la misma dirección en el mismo flanco depende del hardware, y el modelo de simulación entrega el valor viejo. El diseño no depende de eso. Justo en ese caso el multiplexor elige el dato guardado y la salida de la BRAM se descarta.

Costo: 32 flip-flops y 64 LUT de multiplexor, que es parte de las 91 celdas que cuesta el pipeline. La clase 7 advertía que este multiplexor puede bajar la frecuencia máxima. Medido: el multiplexor queda en la ruta crítica, pero la ruta completa es más corta que la del base, porque la decodificación ya no está en ella (sección 8).

### 5.2 Carga seguida de uso

`lw x3, 0(x8)` seguida de `addi x4, x3, 1`. El dato de la carga llega en su segundo ciclo.

Solución: durante el primer ciclo de la carga el core está detenido (`stall`) y el banco no lee (`rf_rd_en_o = ~stall_i`). La lectura de operandos de la instrucción siguiente ocurre en el flanco en que la carga escribe, y el adelantamiento de 5.1 entrega el dato recién cargado. No hace falta un ciclo extra de burbuja: la carga cuesta 2 ciclos haya o no un uso inmediato.

El mismo enable resuelve otro problema: la unidad de carga alinea el byte o la media palabra con los dos bits bajos de la dirección, que salen de la ALU. Si el banco releyera durante la espera, la ALU perdería los operandos de la carga y la alineación usaría una dirección equivocada.

### 5.3 `jal` o `jalr` seguido de uso del enlace

El registro de enlace se escribe en el ciclo del salto. La instrucción destino entra a EX dos ciclos después, cuando la BRAM ya tiene el valor. No necesita adelantamiento.

### 5.4 Escrituras a x0

Una escritura a x0 no se hace y tampoco se adelanta: la señal `wr` del banco excluye la dirección 0 de las dos cosas. Leer x0 entrega siempre el contenido inicial de la BRAM, que es cero.

### 5.5 Salto tomado

La instrucción secuencial que venía detrás del salto ya fue leída y decodificada. Entra a EX con `instr_valid_i = 0` (`valid_d = ~pc_set_i` en `espino_if_stage.v`). Todo lo que tiene efecto está condicionado a esa señal: la escritura del banco, el acceso a memoria y el propio salto. Sus operandos y su decodificación se registran igual, sin consecuencias.

### 5.6 Reset y arranque

Los registros de decodificación y de adelantamiento no tienen reset. Durante el reset `valid_q` vale 0 y el contador de programa apunta a la dirección 0, así que en cada flanco se registran la primera instrucción y sus operandos. Al soltar el reset la primera instrucción ya está lista. El monitor de valores desconocidos de `tb/core_trace_tb.v` confirma que ningún X llega a usarse.

### 5.7 Programa que se modifica a sí mismo

La memoria del fetch es una copia que recibe las mismas escrituras que la de datos. En los dos cores la instrucción que sigue a un store se leyó antes de que el store escriba, y la subsiguiente ya ve el dato nuevo. La ejecución en paralelo con programas aleatorios, que a veces saltan a la zona de datos, no encontró diferencias.

## 6. Qué cambió en el RTL

| Archivo | Cambio |
|---------|--------|
| `rtl/pochoco_soc.v` | Parámetro `Pipeline` (0 base, 1 segmentado con fetch en flanco de bajada, 2 segmentado con ROM), cuyo valor por defecto sale de las definiciones `ESPINO_SEGMENTADO` y `ESPINO_ROM`. Parámetro `PcW`. Cable `instr_next` de la memoria al core. |
| `rtl/pochoco_ram.v` | Parámetro `FetchMode`. Con 1, el puerto de instrucciones lee en el flanco de bajada desde una copia propia de la memoria (`mem_f`) y entrega `a_next_o`. Con 2 no hay puerto de instrucciones. |
| `rtl/espino_core/espino_core.v` | Pasa `Pipeline` y `PcW`, puerto `instr_next_i`, señal `instr_ex` para los testbenches. |
| `rtl/espino_core/espino_if_stage.v` | Contador de programa de `PcW` bits. |
| `rtl/espino_core/espino_id_stage.v` | Bloque `g_pipe`: decodificación registrada, sin ciclo de espera, enable de lectura del banco. Bloque `g_base`: el código original. Destino del salto y enlace con `PcW` bits. |
| `rtl/espino_core/espino_register_file.v` | Entrada `rd_en_i` y adelantamiento (`Bypass`). |

No cambiaron `espino_decoder.v`, `espino_alu.v`, `espino_load_store_unit.v`, `espino_controller.v`, `pochoco_periph.v` ni `pochoco_spi_slave.v`. Con `Pipeline = 0` cada módulo genera la lógica original.

Eso último está probado formalmente con `make formal-base`. Con los pases `equiv_*` de Yosys (el método de la equivalencia entre RTL y netlist del Proyecto 3) compara las etapas IF e ID del repositorio base con las actuales en modo base, registro por registro y salida por salida: 266 y 1110 puntos de comparación, todos probados equivalentes. La etapa ID lleva dentro el decodificador y la ALU. Como control negativo, con el contador de programa de 11 bits la misma prueba deja 42 puntos sin probar.

Por qué la copia de la memoria: Yosys no reparte en BRAM un arreglo que tiene un puerto de lectura en el flanco de subida y otro en el de bajada, y lo convierte en 16 000 flip-flops. Con dos arreglos que reciben las mismas escrituras sí lo hace. No cuesta BRAM adicionales: la memoria original también se duplica, porque cada BRAM del iCE40 tiene un solo puerto de lectura. Son 8 bloques en los dos casos.

Única diferencia de comportamiento con el base: el contador de programa tiene 11 bits. Un programa que salte fuera de las 512 palabras lee en los dos cores la misma instrucción, porque la memoria solo mira 9 bits de la dirección, pero `auipc` y el enlace de `jal` entregan el valor recortado. `trade.s` nunca sale de la memoria.

## 7. Recorte de celdas

Antes de agregar el pipeline se buscó dónde recuperar celdas. Cada recorte se midió sintetizando con y sin él (`make medir-espino`).

| Recorte | Espino base | Segmentado | Comentario |
|---------|-------------|------------|------------|
| Contador de programa y sus sumadores, de 32 a 11 bits | 1083 a 950: recupera 133 | 1174 a 994: recupera 180 | El contador, su copia para la etapa de ejecución, el sumador de +4, el sumador del destino del salto, el del enlace y el multiplexor del próximo PC. En el segmentado además se acorta el registro del inmediato del salto. |
| Decodificación que no se usa (`illegal_insn_o`, códigos de los shifts) | entre 14 y 40 menos | entre 17 menos y 12 más | La síntesis ya elimina la lógica que nadie lee. Reescribir el decodificador de tres formas equivalentes movió el conteo en esos rangos y en el segmentado ni siquiera con el mismo signo: es el ruido de la herramienta (T6). No se aplicó. |
| Registros de lectura de los periféricos, de 32 bits | 0 | 0 | Yosys ya detecta que 28 y 24 de esos bits son siempre cero y los quita. |

El recorte del contador de programa se aplica solo al segmentado. El base conserva sus 32 bits para que el bitstream de competencia no cambie.

Resultado: el pipeline cuesta 91 celdas sobre el base cuando los dos tienen el contador de 32 bits (1174 contra 1083). Con el recorte el segmentado termina en 994 celdas, 89 menos que el base, y deja 286 libres.

## 8. Los dos caminos de fetch, medidos

`nextpnr-ice40 --hx1k --package vq100 --freq 25`, semillas 1 a 10 (`make medir-espino`).

| Variante | Celdas | BRAM | Fmax mínima | Mediana | Máxima | Cierran a 25 MHz | CPI |
|----------|--------|------|-------------|---------|--------|------------------|-----|
| Espino base | 1083 | 12 | 42,43 | 43,74 | 45,08 | 10 de 10 | 2, 3 y 3 |
| A: fetch en flanco de bajada (BRAM) | 994 | 12 | 51,13 | 53,50 | 54,50 | 10 de 10 | 1, 2 y 2 |
| B: ROM combinacional de `trade.s` | 1055 | 8 | 50,04 | 53,16 | 55,05 | 10 de 10 | 1, 2 y 2 |

Los dos caminos ejecutan igual, ciclo a ciclo: sus trazas son idénticas (sección 9).

Se eligió el camino A:

- Cuesta 61 celdas menos. La ROM de `trade.s` son 40 instrucciones, y un programa más largo costaría más.
- El programa sigue en BRAM. Se puede cambiar dentro del bitstream con `icebram` sin volver a sintetizar, que es parte del plan de contingencia para el día de la evaluación. Con el camino B el programa queda en LUTs y cada cambio obliga a sintetizar y a rutear de nuevo.
- La frecuencia máxima es la misma.

El camino B libera 4 BRAM. Queda disponible (`-DESPINO_ROM`) y verificado, por si un periférico futuro necesitara esos bloques.

### El camino de medio ciclo

El riesgo del camino A es que hay rutas que disponen de medio ciclo y no de uno entero: del contador de programa a la BRAM (subida a bajada), y de la BRAM al banco de registros y a los registros de decodificación (bajada a subida).

nextpnr sí analiza esas rutas con medio período. Se comprobó con un diseño de prueba que tiene una ruta larga entre una BRAM de flanco de bajada y un registro de flanco de subida: nextpnr informa la ruta como `negedge -> posedge` y calcula la frecuencia máxima como 1 / (2 × retardo). `icetime` no lo hace: para el mismo diseño informa el doble de frecuencia. Por eso todas las cifras de este documento son de nextpnr.

En el segmentado la ruta crítica no es de medio ciclo. Es de un ciclo completo, de 18,4 a 19,6 ns según la semilla. En la semilla más lenta es: salida del banco de registros, multiplexor de adelantamiento, sumador de la ALU (dirección de memoria), decodificación de la dirección y habilitación del registro que recuerda de qué periférico se lee. Como nextpnr cuenta doble las rutas de medio ciclo y la frecuencia mínima es 51,1 MHz, ninguna ruta de medio ciclo pasa de 9,8 ns, y dispone de 20.

En el base la ruta crítica mide 22 a 23,6 ns porque incluye la decodificación: la instrucción sale de la BRAM, pasa por el decodificador y recién entonces llega a la ALU. En el segmentado la decodificación está registrada y queda fuera. Por eso el pipeline, que agrega un multiplexor, igual sube la frecuencia máxima.

Qué no cubre este análisis: nextpnr supone un reloj con ciclo de trabajo de 50 %. Con los 9,8 ns medidos el diseño tolera un ciclo de trabajo entre 25 % y 75 %. El oscilador de la Go Board está muy lejos de eso, pero es lo primero que hay que mirar el 26/11 si el segmentado falla en la placa y el base no.

## 9. Verificación

Toda la verificación corre con `make` y compara contra algo independiente: el Espino base, el gemelo digital o la referencia en Python.

| Prueba | Qué compara | Resultado |
|--------|-------------|-----------|
| `make formal-base` | Etapas IF e ID en modo base contra las del repositorio del curso, con Yosys | 1376 puntos de comparación probados equivalentes: el Espino base no cambió |
| `make tb-seg` | Copia del testbench oficial, con el core segmentado | 4/4, peor caso 26 ciclos, `decisiones.csv` idéntico a la referencia |
| `make equiv-seg` | Los 20 000 ticks de práctica por el RTL (Verilator, 0,1 ms y 1 ms), pocos ticks con Icarus a 1 ms y 10 ms, y el gemelo a los tres períodos, contra `ref/trader.py` | Idénticos byte a byte. Patrimonio 26 795 y 27 306, los mismos del base |
| `make equiv-seg-icarus` y `make equiv-r3` | Los 20 000 ticks con Icarus, el simulador del testbench oficial, con el segmentado y con el base (ejecución manual, 13 minutos cada una) | Idénticos a la referencia, 4/4, patrimonio 26 795 |
| `make equiv-rom` | Lo mismo con la ROM combinacional, 20 000 ticks | Idénticos |
| `make riesgos` | `hazard_test.s`, `hazard_review.s` y `hazard_cycles.s` del Proyecto 3 en el base, el segmentado y el de ROM | Ver abajo |
| `make paralelo-largo` | Base y segmentado corriendo a la vez 16 programas aleatorios | 1 600 000 instrucciones comparadas una por una con cada contador (11 y 32 bits), 628 583 distintas (39,3 %), cero diferencias. Corrida del 15/11 con el generador corregido (T52). La del 13/11 informaba 1 300 756 y 1 600 000, pero solo 4 644 y 5 306 eran distintas (0,4 %): el generador anterior caía en un punto fijo |
| `make cosim-seg` | RTL del segmentado contra el gemelo digital con `--pipeline`, ciclo a ciclo | 1 007 124 eventos de `trade.hex` idénticos, 846 705 escrituras de 4 programas aleatorios, 20 000 ticks del testbench y 19 998 mediciones por tick |
| `make mutaciones` | Cinco errores puestos a propósito | Los cinco detectados por `riesgos` y por `paralelo` |
| `make timing-seg` | Cierre de timing en 10 semillas | 10 de 10 a 25 MHz |
| `make sim-bitstream-seg` | El bitstream del segmentado, simulado desde el `.asc` | Ver `bitstreams/README.md` |

### Pruebas de riesgos

Los tres programas vienen del Proyecto 3. `hazard_test.s` tiene 56 comprobaciones y `hazard_review.s` 48: cada riesgo de la sección 5, uno por uno y encadenados, con cada tipo de load, cada salto condicional tomado y no tomado, y saltos encadenados. Cada programa se revisa a sí mismo y termina con los LEDs en 1111. `hazard_cycles.s` se adaptó: en el Proyecto 3 leía el contador de ciclos, que este SoC no tiene, y aquí lee los interruptores, que el testbench cambia en cada ciclo.

`tools/riesgos.sh` exige cinco cosas:

1. **Funcional.** El segmentado hace las mismas escrituras al banco, los mismos accesos al bus y los mismos cambios de salidas que el base, en el mismo orden. `hazard_test`: 348 escrituras, 63 accesos y 2 salidas iguales. `hazard_review`: 271, 66 y 2.
2. **Ciclo a ciclo entre los dos caminos de fetch.** Trazas idénticas: 3153, 3137 y 3017 eventos.
3. **Ciclo a ciclo contra el modelo de ciclos esperado.** La traza del RTL es idéntica a la del gemelo con `--pipeline`: 413 y 339 eventos.
4. Los tres programas terminan con los LEDs en 1111 en las tres variantes.
5. Ningún valor desconocido llega a una escritura, al bus, a la ALU ni a una salida.

### Ejecución en paralelo

`tb/tb_paralelo.sv` instancia dos SoC completos, uno con cada core, con el mismo programa de `tools/prog_aleatorio.py` (toda la ISA, shifts, codificaciones inválidas y accesos a periféricos). La instrucción número k del base se compara con la número k del segmentado: contador de programa, instrucción, escritura al banco, escritura a memoria, el contenido real de los 16 registros leído de las BRAM y la palabra de memoria escrita. Al final se compara la RAM completa. Como el segmentado va más rápido, su reloj se detiene cuando se adelanta.

Se corre en dos configuraciones. Con el contador de programa de 11 bits, que es el que se sintetiza, la comparación de un programa termina sin error cuando el base ejecuta una instrucción fuera de la memoria: pasó en 3 de los 16 programas, por un `jalr` con una base cualquiera. Con el contador de 32 bits se compara todo, también lo que pasa fuera de la memoria.

### Controles negativos

Una prueba que siempre pasa no prueba nada. `tools/mutaciones.sh` activa, de a una, cinco mutaciones que están en el RTL bajo `ifdef`:

| Mutación | Qué rompe | Quién la detecta |
|----------|-----------|------------------|
| `MUTA_FWD` | Sin adelantamiento | Los tres programas de riesgos y los 4 programas aleatorios |
| `MUTA_LOADUSE` | La instrucción que sigue a una carga lee antes de que la carga escriba | Los tres programas y los 4 aleatorios |
| `MUTA_RDEN` | El banco relee durante la espera de una carga | `hazard_test`, `hazard_review` y los 4 aleatorios |
| `MUTA_X0` | El adelantamiento no excluye a x0 | `hazard_test`, `hazard_review` y 3 de los 4 aleatorios |
| `MUTA_SQUASH` | No se anula la instrucción que sigue a un salto tomado | `hazard_test`, `hazard_review` y los 4 aleatorios |

### riscv-formal

Se evaluó y no se hizo en este tramo. Qué faltaría:

- Agregar al core la interfaz RVFI: por cada instrucción completada, su código, el contador de programa antes y después, los registros leídos con su valor, el registro escrito y el acceso a memoria. Las señales ya existen dentro de `espino_id_stage.v`. Lo delicado es entregar el valor de `rs1` y `rs2` que la instrucción usó de verdad, después del adelantamiento.
- Un envoltorio para SymbiYosys con el banco de registros en flip-flops, porque las BRAM con contenido inicial hacen muy lenta la prueba.
- Excluir los chequeos de los shifts: la ALU de Espino no los implementa y los ejecuta como una suma, así que fallarían por diseño. También los de excepciones, que Espino no tiene.
- Restringir los índices de registro a 16: riscv-formal está pensado para 32 registros y Espino es RV32E.

Estimamos un día de trabajo. Lo que se hizo cubre lo mismo por otro camino: 3,2 millones de instrucciones aleatorias (628 583 distintas) comparadas contra el Espino base con el estado completo del banco, y controles negativos. Hasta el 15/11 esta cifra decía 2,9 millones, pero con el generador anterior solo unas 10 000 eran distintas (T52). Una prueba formal acotada agregaría la garantía para todas las secuencias de pocas instrucciones.

## 10. Mediciones

### CPI por clase de instrucción

`tb/tb_cpi.sv` cuenta instrucciones y ciclos por clase y comprueba un modelo de costo: `ciclos = 2 × IC + loads + saltos tomados` en el base y `ciclos = IC + loads + saltos tomados` en el segmentado. La diferencia entre el modelo y lo medido es de 0 ciclos en `trade.s`, en el programa con el mix de la clase y en un programa aleatorio.

| Programa | Core | IC | Ciclos | CPI | Loads | Saltos tomados |
|----------|------|----|--------|-----|-------|----------------|
| `trade.s`, 200 ticks | base | 187 040 | 496 000 | 2,652 | 32,7 % | 32,5 % |
| `trade.s`, 200 ticks | segmentado | 299 264 | 496 000 | 1,657 | 32,9 % | 32,8 % |
| `mix_clase7.s` | base | 19 575 | 46 000 | 2,350 | 20,0 % | 15,0 % |
| `mix_clase7.s` | segmentado | 34 077 | 46 003 | 1,350 | 20,0 % | 15,0 % |
| aleatorio | base | 19 968 | 46 002 | 2,304 | 18,4 % | 12,0 % |
| aleatorio | segmentado | 35 280 | 46 002 | 1,304 | 18,4 % | 12,0 % |

El CPI global de `trade.s` es alto porque el programa pasa casi todo el tiempo en el lazo de sondeo, que es un load, una instrucción de ALU y un salto tomado. En los mismos ciclos el segmentado da 60 % más vueltas a ese lazo.

### `trade.s` por tick

Las mismas ventanas del punto 3.2 del enunciado (`docs/mediciones/ticks_segmentado.txt` y `ticks_software.txt`), con la serie de práctica. Son iguales en las tres rondas.

| Ventana | Core | IC promedio | Ciclos promedio | Ciclos peor caso | CPI | Tiempo peor caso |
|---------|------|-------------|-----------------|------------------|-----|------------------|
| Respuesta (hasta `DECISION`) | base | 19,5 | 41,0 | 44 | 2,10 | 1,76 us |
| Respuesta (hasta `DECISION`) | segmentado | 19,2 | 22,0 | 26 | 1,15 | 1,04 us |
| Tick completo | base | 28,5 | 63,0 | 66 | 2,21 | 2,64 us |
| Tick completo | segmentado | 28,2 | 34,0 | 38 | 1,21 | 1,52 us |

El peor caso del testbench depende de en qué punto del lazo de sondeo llega el precio. Barriendo todas las fases con el gemelo, el peor caso real es 49 ciclos en el base y 27 en el segmentado. El lazo de sondeo baja de 8 a 5 ciclos, así que la incertidumbre por la fase también baja.

El speedup de la respuesta es 41,0 / 22,0 = 1,86. Es más que el 1,74 del mix porque la respuesta de `trade.s` casi no tiene saltos tomados: se escribió sin saltos que dependan del precio (T12).

### Comparación con la clase 7

La clase 7 midió el Espino base (2, 2, 3, 2 y 3 ciclos, CPI 2,35 con su mix) y dejó estimado, sin simular, un pipeline de 3 etapas: ALU 1, load 2, salto tomado 3, CPI 1,5 y 16,7 MIPS. Las dos cifras de CPI fijan el mix: 20 % de loads y 15 % de saltos tomados. `sw/mix_clase7.s` es un lazo de 20 instrucciones con ese mix exacto.

| | Base medido | Segmentado medido | Clase 7, estimado |
|-|-------------|-------------------|-------------------|
| CPI con el mix | 2,350 | 1,350 | 1,5 |
| MIPS a 25 MHz | 10,64 | 18,52 | 16,7 |
| Speedup | 1 | 1,74 | 1,57 |
| Ppeak (25 MHz × instrucciones de ALU por ciclo × 1 operación) | 12,5 MOPS | 25 MOPS | 25 MOPS |

El base medido coincide con la clase. El segmentado mejora la estimación porque el salto tomado cuesta 2 ciclos y no 3: la instrucción se lee medio ciclo después de que cambia el contador de programa, así que hay una sola instrucción que anular y no dos.

Las dos advertencias de la clase, medidas:

- "El multiplexor de adelantamiento puede bajar la frecuencia máxima." El multiplexor está en la ruta crítica, pero la frecuencia máxima sube de 43,7 a 53,5 MHz de mediana, porque la decodificación salió de esa ruta. A 25 MHz fijos esa holgura no se convierte en velocidad: es margen.
- "Un banco de registros en flip-flops costaría cerca del 40 % de la FPGA." No hizo falta. El banco sigue en BRAM y el adelantamiento cuesta 32 flip-flops y 64 LUT.

En términos de la ley de hierro: IC no cambia, Tclk no cambia, y el CPI baja de 2,35 a 1,35 con el mix de la clase.

## 11. Cómo reproducir

```bash
export PATH=$HOME/herramientas/oss-cad-suite/bin:$PATH
make formal-base       # prueba formal de que el Espino base no cambió
make tb-seg            # copia del testbench oficial con el core segmentado
make cpi-seg           # CPI y modelo de costo
make riesgos           # programas de riesgos del Proyecto 3, tres variantes
make paralelo          # base y segmentado en paralelo, corrida corta
make paralelo-largo    # 16 programas de 100 000 instrucciones
make mutaciones        # controles negativos
make cosim-seg         # gemelo con --pipeline contra el RTL
make equiv-seg         # 20 000 ticks contra la referencia
make equiv-rom         # lo mismo con la ROM combinacional
make timing-seg        # 10 semillas, todas deben cerrar a 25 MHz
make medir-espino      # tabla completa: docs/mediciones/espino_segmentado.txt
make bin-seg           # bitstream del segmentado
make sim-bitstream-seg # simula el bitstream y lo compara con la referencia
```

Para compilar a mano cualquier testbench con el segmentado basta agregar `-DESPINO_SEGMENTADO` al comando de `iverilog` o de `verilator`, y a `read_verilog` en Yosys.

## 12. Preguntas que conviene saber responder

- **¿Sigue siendo Espino?** Sí. La ISA, el decodificador, la ALU, la unidad de carga y las interfaces son las mismas. Cambia cuándo se lee el banco y cuándo se decodifica. Con `Pipeline = 0` es el core original.
- **¿Por qué 3 etapas si una instrucción de ALU demora 1 ciclo?** Etapas y ciclos por instrucción son cosas distintas. Hay tres etapas trabajando a la vez sobre instrucciones distintas, y por eso sale una por ciclo. IF e ID ocupan medio ciclo cada una.
- **¿Por qué el salto tomado cuesta 2 y la clase dice 3?** La clase supone una etapa de fetch de un ciclo completo, con dos instrucciones detrás del salto. Aquí hay una sola.
- **¿Qué pasa si la ruta de medio ciclo no alcanza?** Fallaría la lectura del banco o la decodificación. Mide a lo más 9,8 ns de 20 disponibles en las 10 semillas.
- **¿Por qué no un banco de registros en flip-flops, que no necesita adelantamiento?** Son 480 flip-flops más dos multiplexores de 16 entradas y 32 bits: no cabe.
- **¿Por qué no se adelanta desde más atrás?** No hay más atrás. La instrucción escribe al final de EX y la siguiente lee en ese mismo flanco: solo existe la distancia 1.
- **¿Cómo sabemos que las pruebas detectan errores?** Por las cinco mutaciones.
- **¿El pipeline cambia las decisiones del trader?** No. `decisiones.csv` es idéntico byte a byte en los 20 000 ticks. Cambia cuántos ciclos demora cada una.
- **¿Sirve para la competencia?** Con la regla base la respuesta ya ocupaba 44 de 2262 ciclos, así que no cambia el resultado. Sirve si el algoritmo final es más pesado, y libera 89 celdas para la extensión de la ISA. Solo puede ir en el bitstream de competencia si pasa por la maestra real el 26/11.
