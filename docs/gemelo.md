# Gemelo digital del Pochoco SoC

Documento de estudio de `ref/gemelo/gemelo.c`: qué es, qué modela, cómo se sabe que es correcto y para qué se usa.

| Archivo | Qué es |
|---------|--------|
| `ref/gemelo/gemelo.c` | El gemelo: un solo archivo en C, sin dependencias. |
| `ref/gemelo.py` | Envoltorio en Python: lo compila y lo corre sobre un lote de series. |
| `tb/tb_cpi.sv` | Testbench que escribe la traza y las mediciones del RTL. |
| `tools/cosim.sh` | La validación (`make cosim`). |
| `tools/prog_aleatorio.py` | Generador de programas aleatorios. |
| `tb/barrel/tb_gemelo.sv` | Testbench que escribe la traza y las mediciones del Espino barrel (sección 7). |
| `tools/gemelo_barrel.py` | La validación del modo barrel (`make cosim-barrel`). |

## 1. Qué es y por qué existe

Es un simulador del SoC completo que no simula compuertas. Recibe el mismo `trade.hex` que va dentro del bitstream y una serie de precios, y entrega lo mismo que el testbench oficial: el `decisiones.csv`, el patrimonio, el peor caso de respuesta en ciclos y los cuatro chequeos.

Existe por el tiempo de simulación. Los 20 000 ticks de la serie de práctica toman:

| Período | Icarus | Verilator | Gemelo |
|---------|--------|-----------|--------|
| 0,1 ms | 13 minutos | 14 segundos | 0,02 segundos |
| 1 ms | cerca de 2 horas (estimado) | 2,5 minutos | 0,02 segundos |
| 10 ms | cerca de 22 horas (estimado) | 22 minutos | 0,02 segundos |

Con eso se pueden correr millones de ticks: las 3810 series del protocolo a los tres períodos (23 millones de ticks) toman menos de 30 segundos, incluida la referencia en Python.

No reemplaza a nada. La referencia del algoritmo sigue siendo `ref/trader.py`, y lo que manda es el RTL con el testbench oficial. El gemelo es un tercer modelo, del hardware, que sirve para llegar donde la simulación del RTL no alcanza.

## 2. Qué modela

**El core.** Cada instrucción se ejecuta de una vez, pero se anota en qué ciclo ocurre cada cosa. Si la instrucción parte en el ciclo `c`:

| Instrucción | Acceso al bus | Escritura del registro | Siguiente instrucción |
|-------------|---------------|------------------------|-----------------------|
| Aritmética, `lui`, `auipc` | | `c + 1` | `c + 2` |
| Store | `c + 1` | | `c + 2` |
| Load | `c + 1` | `c + 2` | `c + 3` |
| Salto condicional no tomado | | | `c + 2` |
| Salto condicional tomado, `jal`, `jalr` | | `c + 1` (el enlace) | `c + 3` |

Es el modelo de costo de 2 ciclos por instrucción, más 1 en cada load y 1 en cada salto tomado, leído de `espino_id_stage.v`, `espino_controller.v` y `espino_load_store_unit.v`. El gemelo decodifica igual que `espino_decoder.v`, incluidos los casos que un programa normal no usa: los shifts se ejecutan como una suma, una instrucción desconocida no hace nada, un load con `funct3` inválido se comporta como `lw`, y los campos de registro tienen 4 bits.

**El core segmentado.** Con la opción `--pipeline` el gemelo usa la tabla de ciclos del pipeline de 3 etapas (`docs/espino_segmentado.md`). Las instrucciones hacen lo mismo y cambia cuándo:

| Instrucción | Acceso al bus | Escritura del registro | Siguiente instrucción |
|-------------|---------------|------------------------|-----------------------|
| Aritmética, `lui`, `auipc` | | `c` | `c + 1` |
| Store | `c` | | `c + 1` |
| Load | `c` | `c + 1` | `c + 2` |
| Salto condicional no tomado | | | `c + 1` |
| Salto condicional tomado, `jal`, `jalr` | | `c` (el enlace) | `c + 2` |

Además el contador de programa tiene 11 bits, como en el RTL, y una vuelta del lazo de sondeo dura 5 ciclos en vez de 8. `make cosim-seg` valida este modo contra el RTL del core segmentado con las mismas pruebas del base: 1 007 124 eventos de `trade.hex` en cuatro configuraciones de tiempos, 846 705 escrituras de 4 programas aleatorios, los 20 000 ticks del testbench y las mediciones por tick.

**El esclavo SPI.** Aquí no hay atajo: `spi_paso` es la misma lógica de `pochoco_spi_slave.v`, flanco por flanco, con los tres sincronizadores de 3 etapas, el contador de bits, los registros de desplazamiento y la bandera de precio nuevo. Lo único que se ahorra es el tiempo en que las tres líneas están quietas: si los sincronizadores ya tienen el valor del pin, el estado no puede cambiar hasta el próximo evento de la maestra, y se salta hasta ahí.

**La maestra.** Los instantes en nanosegundos de `tb_proyecto_4.sv`: baja `CS_n`, espera 1000 ns, 8 bits con `SCLK` de 1 MHz, espera 500 ns y sube. Todos esos tiempos son parámetros, igual que el período, el instante de la primera transacción, la caja y la comisión.

**El reset.** El contador de encendido de `pochoco_soc.v`: mientras dura, el esclavo SPI está en reset y responde 0.

**La contabilidad.** La tarea `ejecutar` del testbench, con enteros de 32 bits y la división que trunca hacia cero.

### Numeración de ciclos

El ciclo `k` es el intervalo que termina en el flanco de subida número `k` del reloj. El flanco 0 ocurre a los 20 ns y hay uno cada 40 ns. Un evento "del ciclo `k`" es lo que se ve al muestrear en ese flanco. `tb/tb_cpi.sv` usa la misma convención, y por eso las trazas se pueden comparar con `cmp`.

### La coincidencia entre SCLK y el reloj

El testbench oficial sube `SCLK` a los 5500 ns de cada transacción, y 5500 = 20 + 40 × 137: justo en un flanco del reloj de 25 MHz. Qué ve el sincronizador en ese flanco depende del orden en que el simulador procesa los dos eventos. Icarus y Verilator lo resuelven igual: el flanco ya ve el valor nuevo. El gemelo lo modela con la opción `--borde` (1 por defecto).

En la placa esto no existe como problema: la maestra es asíncrona respecto a nuestro reloj y el sincronizador de 3 etapas está para eso. Con `--borde 0` la respuesta se mueve un ciclo y las decisiones no cambian. Sirve además como control negativo de la validación.

### El atajo del sondeo

El programa pasa más del 97 % del tiempo en el lazo de espera:

```
esperar:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, esperar
```

Cada vuelta dura 8 ciclos y 3 instrucciones, y mientras no llegue un precio no cambia nada. Cuando el gemelo reconoce este patrón en el contador de programa (compara las tres palabras de la memoria, no depende de direcciones fijas), adelanta el esclavo SPI hasta que se levanta la bandera, calcula cuál es la primera vuelta cuya lectura la ve y se salta las anteriores sumando 8 ciclos y 3 instrucciones por cada una.

A 10 ms son 31 000 vueltas por tick. Sin el atajo los 20 000 ticks toman 21 segundos y con el atajo 0,02. El resultado es el mismo: `make cosim` compara las dos formas en decisiones, mediciones por tick y totales de instrucciones y ciclos. Si el programa no tiene ese lazo, el gemelo no se salta nada y sigue siendo correcto, solo más lento. Con `--traza` el atajo se desactiva, porque la traza debe traer todos los eventos.

## 3. Cómo se sabe que es correcto

`make cosim` corre el RTL con `tb/tb_cpi.sv` y el gemelo con las mismas entradas, y exige archivos idénticos. La traza trae una línea por evento, con su número de ciclo:

```
4097 R 2 80010000     escritura al banco de registros: x2 = 0x80010000
5102 C 00             baja CS_n: el byte que va a salir por MISO es 0x00
5314 B 95             llegó un precio: 0x95 (149)
5324 L 80010004       lectura por el bus de datos: PRICE
5325 R 5 00000095     x5 = 149
5327 R 6 0000012a     x6 = 298, la primera de las cinco sumas
```

Las escrituras por el bus aparecen como `W dirección máscara dato`.

Si las dos trazas son iguales, el gemelo hizo lo mismo que el RTL en el mismo ciclo: cada registro escrito, cada acceso a memoria y a periféricos, cada precio recibido y cada byte transmitido. El formato y el método vienen del `tb/core_trace_tb.v` del Proyecto 3.

| Prueba | Qué compara | Resultado |
|--------|-------------|-----------|
| A | `trade.hex`, timing oficial, 300 ticks | 282 210 eventos idénticos |
| B1 | Período 100 010 ns, SCLK de 500 kHz, otros tiempos de CS, inicio en 3999 ns | 93 069 eventos idénticos |
| B2 | Período 400 µs, SCLK de 100 kHz, reset de 63 ciclos | 225 509 eventos idénticos |
| B3 | Período 30 µs, tiempos de SPI que no son múltiplos de 40 ns | 29 289 eventos idénticos |
| C | 4 programas aleatorios con tráfico SPI, 150 ticks cada uno | 555 966 eventos idénticos, 469 343 de ellos escrituras de registro o de memoria |
| D | Testbench oficial (copia), 20 000 ticks | `decisiones.csv` y resumen idénticos |
| E | Mediciones por tick, 20 000 ticks, con el atajo | 19 998 ticks idénticos: ciclo de llegada, ciclos e IC |
| F | Gemelo con y sin atajo, a 0,1 ms, 1 ms y 10 ms | Idénticos |
| G | Control negativo: `--borde 0` | La traza difiere, como debe |

Las pruebas B existen porque el timing oficial es muy regular: el período son 2500 ciclos exactos y la fase del lazo de sondeo solo toma cuatro valores. Con el período de 100 010 ns la fase recorre todos los casos. Así apareció el único error del gemelo que la prueba A no veía: el conteo de instrucciones por tick fallaba por uno cuando el precio llegaba justo en el ciclo en que se completaba un load.

Los programas aleatorios cubren lo que `trade.hex` no usa: toda la ISA base, los shifts, loads y stores de los tres tamaños con cualquier desplazamiento, los seis saltos condicionales, `jal`, `jalr`, palabras que el decodificador no reconoce y accesos a todos los registros del esclavo SPI y de los periféricos. Los saltos van siempre hacia adelante y el cuerpo se repite para siempre, así que cada vuelta toma caminos distintos. Más semillas: `SEMILLAS="1 2 3 4 5 6 7 8" tools/cosim.sh`.

Además, `make equiv-gemelo` corre `trade.hex` en el gemelo sobre las 3810 series del protocolo, a los tres períodos, y compara patrimonio, órdenes y pérdida máxima con `ref/trader.py`: cero diferencias en 23 millones de ticks.

### Qué no modela

- **Timing eléctrico.** No hay retardos de compuertas ni metaestabilidad. Que el diseño cierre a 25 MHz lo dice nextpnr, y que el SPI funcione con la maestra real se prueba el 26/11.
- **Valores indefinidos.** Una palabra que no está en el `.hex` vale 0 (en el RTL simulado sería X). Por eso `trade.hex` se rellena a 512 palabras, y el gemelo avisa si recibe un `.hex` más corto.
- **Tres cores, validados por separado.** El Espino base (`make cosim`), el segmentado (`--pipeline`, `make cosim-seg`) y el barrel con o sin la extensión (`--barrel --xd`, `make cosim-barrel`, sección 7). Un cambio en el RTL de cualquiera obliga a repetir su validación.
- **Interruptores.** Valen 0, como en el testbench.

## 4. Qué se encontró con el gemelo

**El peor caso del testbench no es el peor caso.** El testbench oficial informa 44 ciclos. Barriendo las 8 fases posibles del lazo de sondeo (moviendo el inicio en pasos de 40 ns), la respuesta va de 37 a 44 ciclos en régimen, y de 42 a 49 para el primer precio, que pasa por el bloque de inicialización (5 ciclos más). El peor caso real es 49 ciclos. No cambia nada frente a los 2 262 disponibles, pero es el número correcto para el informe.

**El programa responde todos los precios en todas las series.** En las 3810 series y los tres períodos no hay ningún precio sin respuesta ni perdido.

## 5. Uso

```bash
make gemelo                                   # compila build/gemelo
build/gemelo                                  # serie de práctica, timing del testbench oficial
build/gemelo --periodo-ns 10000000            # ronda 1
build/gemelo --nticks 2000 --csv build/g.csv --ticks build/g_ticks.csv
build/gemelo --inicio-ns 200000               # placa encendida antes del primer precio
build/gemelo --lote series.txt                # una serie por línea, un resultado por línea
build/gemelo --ayuda
make cosim                                    # validación contra el RTL (unos 2 minutos)
make equiv-gemelo                             # el binario contra la referencia en 3810 series
```

La salida normal son las mismas líneas del testbench oficial, más dos líneas propias con instrucciones, ciclos y mediciones por tick.

## 6. Preguntas que nos pueden hacer

**¿Por qué confiar en un simulador escrito por ustedes?** Porque sus resultados no se aceptan sin compararlos con el RTL. La traza del gemelo es idéntica a la del RTL evento por evento y ciclo por ciclo, en 8 configuraciones y más de un millón de eventos, y hay un control negativo que muestra que la comparación detecta un error de un solo ciclo.

**¿Por qué en C y no en Python?** Por velocidad. La referencia del algoritmo sí está en Python, porque ahí importa que se lea fácil. El gemelo ejecuta instrucción por instrucción y tiene que correr millones de ticks.

**¿El atajo no es hacer trampa?** Es una optimización que se verifica: con y sin atajo el resultado es idéntico, incluido el total de instrucciones y de ciclos. Y la validación contra el RTL de la prueba E se hace con el atajo activado.

**¿Qué pasa si cambian el programa?** El gemelo ejecuta cualquier `.hex`. No sabe nada del algoritmo.

**¿Y si cambian el hardware?** Hay que actualizar el modelo y volver a correr `make cosim`. Un periférico nuevo o una instrucción nueva se agregan en `bus_leer`, `bus_escribir` o el `switch` del core.

## 7. El Espino barrel y la extensión (paquete P4)

Con `--barrel` el gemelo modela el Espino barrel de `docs/espino_barrel.md`, y con `--xd MASCARA` la extensión de `docs/extension_isa.md` (1 `emad`, 2 `devk`, 4 `mulstep`; el fondo corre con `--xd 3`). Es lo que corre `sw/fondo.s`.

### 7.1 Por qué el barrel es más fácil de modelar que el base

En el barrel la rotación de hilos es fija y no depende de las instrucciones: no hay burbujas, ni esperas, ni instrucciones anuladas. Con R el último ciclo del reset y x0 = R + 2:

| Etapa | Ciclo del hilo t, instrucción n | Qué hace el gemelo |
|-------|----------------------------------|--------------------|
| F | x0 + t + 4n - 2 | Lee la palabra de su contador de programa, con la memoria de antes de las escrituras de ese flanco |
| X | x0 + t + 4n | Ejecuta la instrucción completa: ALU, salto y acceso al bus |
| M | x0 + t + 4n + 1 | La escritura al banco aparece en la traza |

Como cada hilo tiene su banco y su instrucción anterior ya terminó (sección 3.4 de `docs/espino_barrel.md`), ejecutar cada instrucción entera en su ciclo X da exactamente lo mismo que el RTL. Lo único que hay que respetar es el orden entre hilos: un ciclo, un hilo en X. Al salir del reset el hilo 0 busca en el ciclo R, el 1 en R + 1, el 2 en R + 2 y el 3 en R + 3: son las burbujas del arranque, que el gemelo no ejecuta.

El IC que informa por tick es el del hilo 0, el que decide. Sale de una fórmula: el hilo 0 completa una instrucción cada 4 ciclos desde x0.

### 7.2 El atajo, ahora con cuatro hilos

El atajo del core base reconoce el lazo de sondeo y salta vueltas. En el barrel no basta: mientras el supervisor sondea STATUS, los gestores sondean PUB, y un hilo de prueba puede estar en cualquier lazo. El gemelo usa una regla general:

1. Cada vez que el hilo 0 está por leer STATUS en el lazo `lw / andi 1 / beqz` y no hay precio nuevo, toma una instantánea del estado: registros y contadores de programa de los cuatro hilos, palabras ya buscadas, LED y dígitos, y cuántas escrituras cambiaron la memoria.
2. Si la instantánea es igual a una anterior, y entre las dos el único acceso al SPI o a los periféricos fue esa lectura de STATUS (que el `andi` reduce a la bandera, que valió 0), todo el sistema es periódico: cada P ciclos vuelve al mismo estado. Con `sw/fondo.s` P = 24 ciclos (el lazo del supervisor dura 12 y el de los gestores 8).
3. Se adelanta el esclavo SPI hasta que se levante la bandera, se calcula la primera lectura de STATUS que la ve, y se salta a ella reponiendo la instantánea de esa fase del período. Los conteos de instrucciones por clase se suman por períodos completos.

Si un programa nunca llega a un estado periódico (un contador que siempre avanza, como el gestor colgado de las pruebas de degradación) no se salta nada y el resultado sigue siendo exacto, solo más lento.

| Fondo, 20 000 ticks de práctica | Verilator | Gemelo sin atajo | Gemelo con atajo |
|---------------------------------|-----------|------------------|------------------|
| 0,1 ms | 58 s (`tb/barrel/tb_gemelo.sv` sin traza) | 0,74 s | 0,14 s |
| 10 ms | 35 minutos (medido en P3) | 76 s | 0,14 s |

Con y sin atajo las decisiones, las mediciones por tick y los conteos por clase de instrucción son idénticos a los tres períodos (`make cosim-barrel`, última parte).

### 7.3 Lo que se agregó a la maestra

- `--ronda-ticks`, `--pausa-ns`, `--periodo2-ns` y `--periodo3-ns`: rondas seguidas sin reset de la placa, como `tb/tb_estres.sv`.
- `--cs-sclk-ns`: tiempo de la bajada de CS_n al primer flanco de SCLK, con la convención de `tb_estres.sv` (en el gemelo `--cs-setup-ns` cuenta hasta el primer bit).
- `--bytes`, con `--lote`: agrega a cada línea la suma de los ciclos de respuesta y los bytes leídos, para comparar series enteras con la referencia.

### 7.4 Validación contra el RTL

`tools/gemelo_barrel.py` corre cada configuración en `tb/barrel/tb_gemelo.sv` (Verilator, compilado una vez por hardware) y en el gemelo, y exige traza, mediciones por tick y `decisiones.csv` idénticos byte a byte. La traza es la de `tb_cpi.sv`, con el hilo en cada escritura al banco: `<ciclo> R <hilo> <registro> <valor>`. Resultado en `docs/mediciones/gemelo_barrel.txt`.

| Grupo | Configuraciones |
|-------|-----------------|
| A | `sw/fondo.s`, timing oficial, 300 ticks |
| B | Fases que se recorren solas (período de 100 010 ns), SCLK de 500 kHz y de 100 kHz, reset de 63 ciclos, tiempos de SPI que no son múltiplos de 40 ns |
| C | 8 programas aleatorios de cuatro hilos (`tools/barrel/prog_hilos.py`): zonas separadas, memoria compartida, un solo hilo en el SPI, un hilo con `sw/trade.s`; con la extensión de 2 y de 3 instrucciones, y palabras de la extensión en un core sin ella |
| D | `sw/trade.s` en el hilo 0 (tabla de arranque) |
| E | El fondo con un gestor colgado, un voto atrasado y un voto ausente |
| F | Tres rondas seguidas sin reset, a 10 ms, 1 ms y 0,1 ms |
| G | Reset con la maestra transmitiendo: desde t = 0 y con el reset terminando a mitad de una transacción |
| H | Series pegadas en 1 y en 255 |

Son 21 configuraciones y 18,3 millones de eventos, todos iguales. Dos controles negativos: con `--borde 0` y con la máscara de la extensión equivocada la traza difiere, como debe.

**Lo que encontró la validación.** La primera corrida dio 20 de 21: en las rondas seguidas el RTL nunca cambiaba de período. El error estaba en el testbench, no en el gemelo: `int r = ...;` dentro del `for` de un bloque `initial` es una variable estática en SystemVerilog, se inicializa una sola vez y queda en 0. La misma línea estaba en `tb/tb_estres.sv` y `tb/fondo/tb_fondo.sv`, así que los casos de rondas seguidas de R0 y del fondo habían corrido todas las rondas con el período de la primera (decisión T81). Es el valor de tener dos modelos escritos por separado: cuando no coinciden, alguno está mal, y no siempre es el nuevo.

### 7.5 Para qué se usó

- `make fondo-gemelo-series`: 1 051 series (70 de cada familia más la práctica) a los tres períodos, 6,36 millones de ticks idénticos a `ref/fondo.py`, en un minuto (`docs/mediciones/fondo/r1/gemelo_series.txt`, con el programa de P5 y la tabla en su BRAM).
- `make fondo-estres-gemelo`: la matriz de estrés del criterio 7 con el fondo (`docs/mediciones/fondo/estres_gemelo.txt`), que también se corre por el RTL con `make fondo-estres`.
- La firma esperada de la autoprueba en placa (`docs/autoprueba.md`).

### 7.6 Preguntas

**¿Cómo sabemos que el atajo no tapa un error?** La validación contra el RTL de los grupos A a H se hace sin atajo, porque pedir la traza lo desactiva. Y el gemelo con atajo da lo mismo que sin atajo en la práctica completa a los tres períodos: decisiones, mediciones por tick y conteos de instrucciones.

**¿Por qué una instantánea del estado completo y no reconocer el lazo de los gestores, como en el base?** Porque así el atajo no depende de `sw/fondo.s`. Sirve para cualquier programa que, mientras espera el precio, quede en un ciclo; y si no queda, no salta.

**¿El gemelo modela el código que se modifica a sí mismo?** Sí: cada hilo busca su instrucción en el ciclo que corresponde y con la memoria de antes de las escrituras de ese flanco, que es lo que hace la BRAM. Los programas aleatorios con memoria compartida, que pueden ejecutar datos, dan la misma traza que el RTL.
