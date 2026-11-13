# Gemelo digital del Pochoco SoC

Documento de estudio de `ref/gemelo/gemelo.c`: qué es, qué modela, cómo se sabe que es correcto y para qué se usa.

| Archivo | Qué es |
|---------|--------|
| `ref/gemelo/gemelo.c` | El gemelo: un solo archivo en C, sin dependencias. |
| `ref/gemelo.py` | Envoltorio en Python: lo compila y lo corre sobre un lote de series. |
| `tb/tb_cpi.sv` | Testbench que escribe la traza y las mediciones del RTL. |
| `tools/cosim.sh` | La validación (`make cosim`). |
| `tools/prog_aleatorio.py` | Generador de programas aleatorios. |

## 1. Qué es y por qué existe

Es un simulador del SoC completo que no simula compuertas. Recibe el mismo `trade.hex` que va dentro del bitstream y una serie de precios, y entrega lo mismo que el testbench oficial: el `decisiones.csv`, el patrimonio, el peor caso de respuesta en ciclos y los cuatro chequeos.

Existe por el tiempo de simulación. Los 20 000 ticks de la serie de práctica toman:

| Período | Icarus | Verilator | Gemelo |
|---------|--------|-----------|--------|
| 0,1 ms | 13 minutos | 14 segundos | 0,02 segundos |
| 1 ms | cerca de 2 horas (estimado) | 2,5 minutos | 0,02 segundos |
| 10 ms | cerca de 22 horas (estimado) | 22 minutos | 0,02 segundos |

Con eso se pueden correr millones de ticks: las 3010 series del protocolo a los tres períodos (18 millones de ticks) toman menos de 30 segundos, incluida la referencia en Python.

No reemplaza a nada. La referencia del algoritmo sigue siendo `ref/trader.py`, y lo que manda es el RTL con el testbench oficial. El gemelo es un tercer modelo, del hardware, que sirve para llegar donde la simulación del RTL no alcanza.

## 2. Qué modela

**El core.** Cada instrucción se ejecuta de una vez, pero se anota en qué ciclo ocurre cada cosa. Si la instrucción parte en el ciclo `c`:

| Instrucción | Acceso al bus | Escritura del registro | Siguiente instrucción |
|-------------|---------------|------------------------|-----------------------|
| Aritmética, `lui`, `auipc` | | `c + 1` | `c + 2` |
| Store | `c + 1` | | `c + 2` |
| Load | `c + 1` | `c + 2` | `c + 3` |
| Branch no tomado | | | `c + 2` |
| Branch tomado, `jal`, `jalr` | | `c + 1` (el enlace) | `c + 3` |

Es el modelo de costo de 2 ciclos por instrucción, más 1 en cada load y 1 en cada salto tomado, leído de `espino_id_stage.v`, `espino_controller.v` y `espino_load_store_unit.v`. El gemelo decodifica igual que `espino_decoder.v`, incluidos los casos que un programa normal no usa: los shifts se ejecutan como una suma, una instrucción desconocida no hace nada, un load con `funct3` inválido se comporta como `lw`, y los campos de registro tienen 4 bits.

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
| B2 | Período 400 us, SCLK de 100 kHz, reset de 63 ciclos | 225 509 eventos idénticos |
| B3 | Período 30 us, tiempos de SPI que no son múltiplos de 40 ns | 29 289 eventos idénticos |
| C | 4 programas aleatorios con tráfico SPI, 150 ticks cada uno | 555 966 eventos idénticos, 469 343 de ellos escrituras de registro o de memoria |
| D | Testbench oficial (copia), 20 000 ticks | `decisiones.csv` y resumen idénticos |
| E | Mediciones por tick, 20 000 ticks, con el atajo | 19 998 ticks idénticos: ciclo de llegada, ciclos e IC |
| F | Gemelo con y sin atajo, a 0,1 ms, 1 ms y 10 ms | Idénticos |
| G | Control negativo: `--borde 0` | La traza difiere, como debe |

Las pruebas B existen porque el timing oficial es muy regular: el período son 2500 ciclos exactos y la fase del lazo de sondeo solo toma cuatro valores. Con el período de 100 010 ns la fase recorre todos los casos. Así apareció el único error del gemelo que la prueba A no veía: el conteo de instrucciones por tick fallaba por uno cuando el precio llegaba justo en el ciclo en que se completaba un load.

Los programas aleatorios cubren lo que `trade.hex` no usa: toda la ISA base, los shifts, loads y stores de los tres tamaños con cualquier desplazamiento, los seis branches, `jal`, `jalr`, palabras que el decodificador no reconoce y accesos a todos los registros del esclavo SPI y de los periféricos. Los saltos van siempre hacia adelante y el cuerpo se repite para siempre, así que cada vuelta toma caminos distintos. Más semillas: `SEMILLAS="1 2 3 4 5 6 7 8" tools/cosim.sh`.

Además, `make equiv-gemelo` corre `trade.hex` en el gemelo sobre las 3010 series del protocolo, a los tres períodos, y compara patrimonio, órdenes y pérdida máxima con `ref/trader.py`: cero diferencias en 18 millones de ticks.

### Qué no modela

- **Timing eléctrico.** No hay retardos de compuertas ni metaestabilidad. Que el diseño cierre a 25 MHz lo dice nextpnr, y que el SPI funcione con la maestra real se prueba el 19/11.
- **Valores indefinidos.** Una palabra que no está en el `.hex` vale 0 (en el RTL simulado sería X). Por eso `trade.hex` se rellena a 512 palabras, y el gemelo avisa si recibe un `.hex` más corto.
- **Solo el Espino base.** Cuando el core se segmente, la tabla de ciclos de la sección 2 cambia. El gemelo se actualiza y se vuelve a validar con `make cosim`.
- **Interruptores.** Valen 0, como en el testbench.

## 4. Qué se encontró con el gemelo

**El peor caso del testbench no es el peor caso.** El testbench oficial informa 44 ciclos. Barriendo las 8 fases posibles del lazo de sondeo (moviendo el inicio de a 40 ns), la respuesta va de 37 a 44 ciclos en régimen, y de 42 a 49 para el primer precio, que pasa por el bloque de inicialización (5 ciclos más). El peor caso real es 49 ciclos. No cambia nada frente a los 2 262 disponibles, pero es el número correcto para el informe.

**El programa responde todos los precios en todas las series.** En las 3010 series y los tres períodos no hay ningún precio sin respuesta ni perdido.

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
make equiv-gemelo                             # el binario contra la referencia en 3010 series
```

La salida normal son las mismas líneas del testbench oficial, más dos líneas propias con instrucciones, ciclos y mediciones por tick.

## 6. Preguntas que nos pueden hacer

**¿Por qué confiar en un simulador escrito por ustedes?** Porque no se confía: se compara. La traza del gemelo es idéntica a la del RTL evento por evento y ciclo por ciclo, en 8 configuraciones y más de un millón de eventos, y hay un control negativo que muestra que la comparación detecta un error de un solo ciclo.

**¿Por qué en C y no en Python?** Por velocidad. La referencia del algoritmo sí está en Python, porque ahí importa que se lea fácil. El gemelo ejecuta instrucción por instrucción y tiene que correr millones de ticks.

**¿El atajo no es hacer trampa?** Es una optimización que se verifica: con y sin atajo el resultado es idéntico, incluido el total de instrucciones y de ciclos. Y la validación contra el RTL de la prueba E se hace con el atajo activado.

**¿Qué pasa si cambian el programa?** El gemelo ejecuta cualquier `.hex`. No sabe nada del algoritmo.

**¿Y si cambian el hardware?** Hay que actualizar el modelo y volver a correr `make cosim`. Un periférico nuevo o una instrucción nueva se agregan en `bus_leer`, `bus_escribir` o el `switch` del core.
