# Proyecto 4: Pochoco Trader

Agente de inversión que corre en el Pochoco SoC, con el procesador Espino (RV32E), sobre la Nandland Go Board (iCE40 HX1K, 25 MHz). Una FPGA maestra envía por SPI el precio de una acción en cada tick y el programa responde si compra, vende o mantiene, y cuántas acciones.

Arquitectura de Computadores, Universidad de los Andes, semestre 2026-2. Profesor: Jorge Gómez Mir.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

El enunciado está en `docs/Proyecto_4_arq.pdf`. El avance del trabajo se registra en `docs/estado.md` y las decisiones de diseño en `docs/decisiones.md`.

## Origen del código

- El punto de partida es el repositorio base del curso, [nic0villegasc/pochoco_soc](https://github.com/nic0villegasc/pochoco_soc), de Nicolás Villegas, importado sin cambios desde su commit `33e8b5a`. Esa copia quedó marcada con la etiqueta `base-curso`. Los archivos del repositorio base conservan su encabezado de autor y su licencia (Solderpad Hardware License 0.51). Cuando modificamos uno de esos archivos, lo indicamos debajo del encabezado original.
- El ensamblador `tools/pochoasm.py` es el que escribió este grupo para el Proyecto 2 y amplió en el Proyecto 3, con el nombre y la interfaz que espera el testbench del Proyecto 4.
- Del Proyecto 3 del grupo vienen también el formato de la traza de `tb/tb_cpi.sv` y el método de comparar trazas ciclo a ciclo.
- El power-on reset largo de `rtl/pochoco_soc.v` también viene de nuestro Proyecto 2.
- El core segmentado parte del diseño con lectura anticipada de nuestro Proyecto 3 (`nicolasaraneda/Proyecto3_Arquitectura_De_Computadores`). De ahí vienen también `sw/hazard_test.s` y `sw/hazard_review.s` (sin cambios), `sw/hazard_cycles.s` (adaptado), `tb/core_trace_tb.v`, `tb/comparar_trazas.py` y el método de los controles negativos por mutación.
- `tb/tb_proyecto_4.sv` y `tb/practica.csv` son el testbench y la serie de práctica entregados por el curso. No se modifican.

## Herramientas y versiones

Todo se corre con [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build), versión del 2026-09-06, sobre Ubuntu (WSL2):

| Herramienta    | Versión                    |
|----------------|----------------------------|
| Yosys          | 0.68+195                   |
| nextpnr-ice40  | 0.11.1-19-g8dbcee5c        |
| Icarus Verilog | 14.0 (devel, s20260301)    |
| Verilator      | 5.053 (devel)              |
| Compilador de C | gcc o clang, cualquiera reciente (para el gemelo digital) |
| Python         | 3.11 o superior            |
| icepack, iceprog | los de OSS CAD Suite     |

No se necesita un toolchain de RISC-V: el ensamblador es propio y está en el repositorio.

Todos los comandos se ejecutan desde la raíz del repositorio.

## Cómo ensamblar `trade.s`

```bash
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex
```

o `make asm`. La sintaxis que acepta el ensamblador está en `docs/ensamblador.md`, y sus 87 tests se corren con `make test-asm`. `trade.hex` queda relleno con ceros hasta las 512 palabras de la RAM.

El programa está explicado bloque por bloque en `docs/trade_s.md`.

## Cómo correr los testbenches

Testbench oficial, con los mismos comandos de su encabezado:

```bash
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex
iverilog -g2012 -s tb_proyecto_4 -o /tmp/tb_p4 $(yosys-config --datdir)/ice40/cells_sim.v rtl/*.v rtl/espino_core/*.v tb/tb_proyecto_4.sv
vvp -n /tmp/tb_p4
```

o `make tb`, que hace lo mismo y además falla si el resultado no es 4/4. La corrida por defecto (2000 ticks con período de 0,1 ms) demora cerca de un minuto y medio. El detalle por tick queda en `decisiones.csv`.

Otros objetivos:

| Comando | Qué hace |
|---------|----------|
| `make tb-param PERIODO_NS=1000000 NTICKS=500` | Corre una copia del testbench oficial con otro período y otro número de ticks, y compara el resultado con la referencia. El original no se toca. |
| `make -j4 equiv` | Equivalencia con la referencia: el `decisiones.csv` debe ser idéntico byte a byte al de `ref/trader.py`. Incluye los 20 000 ticks de práctica en el gemelo digital a los tres períodos, los mismos 20 000 ticks por el RTL con Verilator a 0,1 ms y 1 ms, y una serie de cada familia sintética. Es lo que corre la integración continua en cada push. |
| `make equiv-r3` | Los 20 000 ticks a 0,1 ms con Icarus, el simulador del testbench oficial (13 minutos). Es una ejecución manual: no corre en cada push. En GitHub se lanza con `gh workflow run CI -f icarus_completo=true`. |
| `make equiv-largo` | Lo mismo con los 20 000 ticks a 10 ms, con Verilator (unos 25 minutos). |
| `make medir-ticks` | Mediciones por tick del punto 3.2: IC, ciclos, CPI y tiempo, promedio y peor caso, en las tres rondas. Resultado en `docs/mediciones/ticks_software.txt`. |
| `make sim-bitstream` | Simula el bitstream ya ruteado (no el RTL) y comprueba que decide igual que la referencia. |
| `make cosim` | Valida el gemelo digital contra el RTL: trazas idénticas ciclo a ciclo, programas aleatorios y testbench oficial. |
| `make equiv-gemelo` | Corre `trade.hex` en el gemelo sobre las 3810 series del protocolo, a los tres períodos, y lo compara con la referencia. |
| `make test-candidatos` | Pruebas de la familia paramétrica de estrategias: el motor en C coincide con la referencia en Python, las familias calibradas son reproducibles. |
| `make algoritmo` | Todo el estudio del algoritmo: ajuste del generador, política óptima, una tabla por idea, experimentos y candidatos. Deja las salidas en `docs/mediciones/` (unos 3 minutos). |
| `make cpi` | Mide instrucciones, ciclos y CPI del core con `tb/tb_cpi.sv`, y comprueba el modelo de costo. Corrida corta, con precios de un LFSR. |
| `make check` | Tests del ensamblador y de la referencia, `trade.hex` al día y testbench oficial. |
| `make tb-mv2x2` y `make costo-mv2x2` | Producto 2x2 en punto fijo (solo diseño y costo): compara las versiones de hardware con su modelo y mide LUT en la FPGA y área en GF180. Resultado en `docs/mediciones/mv2x2_costo.txt`. |

## Cómo correr la versión de referencia del algoritmo

```bash
python3 ref/trader.py tb/practica.csv                    # tabla: algoritmo contra no operar y comprar y mantener
python3 ref/trader.py tb/practica.csv -o build/ref.csv   # decisiones.csv de referencia
make test-ref                                            # pruebas del mercado y de la referencia
```

- `ref/trader.py` es la referencia oficial del algoritmo. Hace las cuentas con las mismas operaciones que `sw/trade.s`.
- `ref/market.py` es el mercado de la maestra, portado de la tarea `ejecutar` del testbench. `python3 ref/market.py validar decisiones.csv` rehace la contabilidad de una corrida del testbench y exige que coincida fila por fila.
- `ref/p4_baseline.py` y `ref/hallazgos.py` (`make hallazgos`) son el punto de partida y el análisis estadístico de la serie de práctica.

Resultado sobre la serie de práctica completa (20 000 ticks, viendo todos los precios). Desde el 15/11 `trade.s` corre `max_media`, la regla base con el umbral de entrada en 3 unidades (decisión T51). En la serie completa de práctica rinde menos que la regla base; se eligió por los remuestreos y las familias plausibles, donde gana 0,7 % y 1,4 %, y por los puntos esperados del torneo (`docs/algoritmo.md`, sección 7, y la decisión T47). La tabla sale de `make tabla-3-1` (`docs/mediciones/tabla_3_1.txt`).

| Estrategia | Patrimonio final | Órdenes | Comisiones | Pérdida máxima |
|------------|------------------|---------|------------|----------------|
| No operar | 10 000 | 0 | 0 | 0 |
| Comprar y mantener | 6 497 | 1 | 5 | |
| Regla base (`trade.s` hasta el 15/11) | 27 062 | 388 | 1 940 | 2 929 |
| `max_media` (`trade.s`) | 25 973 | 624 | 3 120 | 6 295 |

## Piezas avanzadas

Cada una tiene su documento de estudio, su prueba y el número que la respalda.

| Pieza | Qué es | Cómo se corre su prueba | Número que la respalda | Documento |
|-------|--------|-------------------------|------------------------|-----------|
| Gemelo digital | Simulador en C del SoC con exactitud de ciclo, para el Espino base, el segmentado y el barrel con la extensión. Corre el mismo `.hex` del bitstream. | `make cosim`, `make cosim-seg` y `make cosim-barrel` | Base: traza idéntica al RTL en 8 configuraciones, 20 000 ticks a 10 ms en 0,02 s (Verilator: 22 minutos). Barrel: traza idéntica en 21 configuraciones y 18,3 millones de eventos; el fondo a 10 ms en 0,14 s (Verilator: 35 minutos). | `docs/gemelo.md` |
| Protocolo de evaluación | 10 bloques de práctica, 1000 remuestreos y 14 familias sintéticas calibradas (plausibles y de estrés), con criterio de aceptación. | `make protocolo` y `make equiv-gemelo` | Regla base: media 10 772 y percentil 5 de 8 914 en los remuestreos. El binario coincide con la referencia en 23 millones de ticks. | `docs/protocolo.md` |
| Modelo del generador y candidatos | Modelo de nivel, transitoria y redondeo ajustado a la serie de práctica; política óptima; guardia de régimen y tope de pérdida; candidatos sobre la frontera entre media y percentil 5. El algoritmo de la placa es `max_media` desde el 15/11. | `make algoritmo` y `make test-candidatos` | Techo del modelo: 8,4 % por ronda. Mejor candidato: 0,7 % sobre la regla base en remuestreos y 1,4 % en las familias plausibles, con semilla reservada. | `docs/algoritmo.md` |
| Puerta de simulación y matriz de estrés | Ocho criterios que un bitstream debe pasar antes de ir a la placa. Una maestra SPI configurable recorre las 8 fases del sondeo, SCLK de 100 kHz a 4 MHz, tiempos de `CS_n`, reset a mitad de una transacción, rondas seguidas sin reset y series pegadas en los bordes. | `make fases` y `make estres` | R0 la pasó completa: peor caso 49 ciclos en todas las fases contra un límite de 1131, y 60 de 60 casos de estrés con todos los bytes iguales a la referencia. | `docs/puertas.md` |
| Simulación del bitstream | Simula lo que se graba en la placa, reconstruido desde el `.asc`. | `make sim-bitstream` | 2000 ticks idénticos a la referencia. | `docs/decisiones.md`, T15 |
| Programas aleatorios | Generador de programas para comparar dos modelos del SoC. | `make cosim` | 469 343 escrituras de registro y de memoria comparadas con 4 semillas. | `docs/gemelo.md`, sección 3 |
| Producto 2x2 en punto fijo (diseño y costo) | Instrucción propuesta `kal2`: un paso del filtro de Kalman de dos estados como producto de matriz 2x2 por vector, con el estado empaquetado en dos carriles de 16 bits. No está en el SoC. | `make tb-mv2x2` y `make costo-mv2x2` | Tres implementaciones idénticas al modelo en 20 000 vectores por matriz. Coeficientes fijos: 251 LUT con los coeficientes calibrados, agrega 328 celdas al SoC y no cabe. Multiplicadores reales: 3094 LUT en la FPGA, 124 000 um² en GF180. | `docs/producto_2x2.md` |
| Espino segmentado | Pipeline de 3 etapas: la memoria de instrucciones se lee en el flanco de bajada y el banco de registros adelanta el dato recién escrito. Es el mismo Espino, elegido al compilar con `-DESPINO_SEGMENTADO`. El core por defecto sigue siendo el base. | `make check-seg`, `make paralelo-largo`, `make mutaciones`, `make cosim-seg` y `make equiv-seg` | CPI con el mix de la clase 7: 1,350 contra 2,350 del base (la clase estimó 1,5). Respuesta de `trade.s`: 22 ciclos en promedio contra 41. 994 celdas contra 1083. Cierra a 25 MHz en 10 de 10 semillas, con 51,1 MHz en la peor. 3,2 millones de instrucciones aleatorias comparadas una por una con el base, 628 583 distintas (corrida del 15/11 con el generador corregido, T52). | `docs/espino_segmentado.md` |
| Espino barrel | Cuatro hilos por un pipeline de 4 etapas, con los cuatro contextos en las BRAM del banco de registros. Sin adelantamiento ni burbujas. Se elige con `-DESPINO_BARREL`. Es el core del diseño que compite (decisión T50). | `make check-barrel`, `make barrel-verif` y `make barrel-mutaciones` | CPI 1,000 agregado y 4,000 por hilo. 933 celdas contra 1086 del base, 52,6 MHz en la peor de 10 semillas. 7,9 millones de instrucciones comparadas una por una con el base, 91,96 % distintas, cero diferencias. 21 de 21 errores puestos a propósito detectados. Testbench oficial 4/4, con respuesta en 83 ciclos de 2262. | `docs/espino_barrel.md` |
| Extensión de la ISA | Tres instrucciones en custom-0 sobre el barrel: `emad`, `devk` y `mulstep`. Usan el sumador de la ALU con el operando desplazado. Se eligen con `-DESPINO_XD`. | `make check-xd`, `make xd-verif` y `make xd-mutaciones` | 96 celdas, 48,3 MHz en la peor de 10 semillas. Cada instrucción probada formalmente contra su especificación. 8,0 millones de instrucciones comparadas con el base más la especificación, cero diferencias. La regla con `devk` y `emad` responde en 63 ciclos contra 83. | `docs/extension_isa.md` |
| Fondo en un chip | `sw/fondo.s`: un supervisor y tres gestores, uno por hilo del barrel. Cada gestor corre una banda de la regla de reversión y vota por memoria compartida; el supervisor combina los votos con pesos que se ajustan y escribe `DECISION`. Si un voto no llega a tiempo decide sin él, y sin ninguno decide como `sw/trade.s`. | `make check-fondo`, `make fondo-puerta` y `make fondo-bitstreams` | 213 de 512 palabras. 4/4 en el testbench oficial. Idéntico a su referencia en 1 050 series y en la práctica a los tres períodos. Peor caso 444 ciclos de 2262, y 679 con fallas puestas a propósito. 15 de 15 controles negativos detectados. | `docs/fondo.md` |
| Tabla de parámetros, vigilante y relevo | Las 20 constantes del fondo en una BRAM de solo lectura, que se cambia con `icebram` sin sintetizar. Un vigilante que, al quinto precio sin respuesta, reconfigura la FPGA con la imagen de respaldo (`SB_WARMBOOT`). Imagen múltiple con R2 y R0. | `make check-vigilante`, `make fondo-bitstreams` y `make fondo-criterio5` | R1: 1029 celdas, 51,6 MHz en la peor semilla. R2: 1045 celdas, 47,9 MHz. Cambio de tabla en 0,32 s. El vigilante no se dispara en ninguna corrida sana y dispara en la transacción esperada con el supervisor colgado. | `docs/tabla_vigilante.md` |
| Autoprueba en placa | El SoC que compite con una maestra SPI dentro de la FPGA: manda 2000 precios de una caminata aleatoria a los tres períodos y muestra una firma CRC-16 de las decisiones. Prueba la placa sin la maestra del curso. | `make autoprueba-r0` | R0: firma `a23c` igual en el gemelo a los tres períodos, en la referencia, en el RTL y en el bitstream ruteado. Cabe junto a R0 con 11 celdas libres. | `docs/autoprueba.md` |

### Espino barrel

Tercer core, elegido al compilar con `-DESPINO_BARREL`: cuatro hilos que rotan por un pipeline uniforme de cuatro etapas, con los cuatro contextos en las mismas BRAM del banco de registros. No necesita adelantamiento, burbujas ni anulaciones. Viene del tramo de factibilidad (rama `factibilidad-fondo`). Los programas para este core empiezan con una tabla de cuatro saltos, uno por hilo; `tools/barrel/tabla.py` la antepone a un programa de un hilo.

| Comando | Qué hace |
|---------|----------|
| `make check-barrel` | Lo que corre la integración continua: propiedades formales, pruebas de humo, comparación corta contra el base, testbench oficial con 4/4, los 20 000 ticks contra la referencia y timing en 10 semillas. |
| `make barrel-verif` | Cada hilo contra el Espino base, instrucción por instrucción: 20 600 programas que se ejecutan una vez y 748 que repiten su cuerpo. |
| `make barrel-mutaciones` | 21 errores puestos a propósito. La comparación anterior tiene que detectarlos todos. |
| `make barrel-aislamiento` y `make barrel-compartida` | Cuatro hilos a la vez: cada uno idéntico a su corrida solo, y cuatro hilos sobre la misma memoria contra un modelo por turnos. |
| `make barrel-recursos`, `make barrel-cpi` y `make barrel-ticks` | Celdas, frecuencia máxima, CPI y latencia por tick del base, el segmentado y el barrel en la misma corrida. |
| `make barrel-completo` | Todo lo anterior y las pruebas de netlist y de trazas. |

### Extensión de la ISA

Tres instrucciones propias en el opcode custom-0, solo en el Espino barrel: `emad rd, rs1, rs2, 5` (`rd = rs2 + (rs1 >>> 5)`), `devk rd, rs1, rs2, 5` (`rd = (rs1 << 5) - rs2`) y `mulstep rd, rs1, rs2` (`rd = (rs1 << 1) + (rs1[31] ? rs2 : 0)`). Se compilan con `-DESPINO_BARREL -DESPINO_XD`. En el ensamblador se habilitan con la directiva `.extension xd`. La especificación está en `docs/extension_isa.md`.

| Comando | Qué hace |
|---------|----------|
| `make check-xd` | Lo que corre la integración continua: módulos contra el modelo, prueba formal, comparación corta, testbench oficial con 4/4, 20 000 ticks contra la referencia y timing en 10 semillas. |
| `make xd-formal` | Cada instrucción contra su especificación sobre el core (SymbiYosys) y el core con la extensión contra el core sin ella. |
| `make xd-verif` | Cada hilo contra el Espino base más la especificación, instrucción por instrucción. |
| `make xd-mutaciones` | 9 errores puestos a propósito. La comparación anterior tiene que detectarlos todos. |
| `make xd-timing` | Celdas y frecuencia máxima de los 7 subconjuntos, en 10 semillas. |
| `make xd-oficial` | Testbench oficial y serie completa, con `sw/trade.s` y con la misma regla escrita con `devk` y `emad` (`sw/xd/trade_xd.s`). |

### Fondo en un chip

`sw/fondo.s` es el programa del diseño integrado. Corre en el barrel con `emad`, `devk` y la tabla de parámetros (`-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA`, el peldaño R1), y con el vigilante además (`-DESPINO_VIGILANTE`, el peldaño R2). Los objetivos de abajo aceptan `HW=r1` (por defecto) o `HW=r2`. El hilo 0 lee el precio, lo publica con su número de tick, recoge los votos de los hilos 1 a 3 y escribe `DECISION`. Su referencia es `ref/fondo.py`. El protocolo entre hilos, la degradación y las mediciones por tick están en `docs/fondo.md`.

| Comando | Qué hace |
|---------|----------|
| `make check-fondo` | Lo que corre la integración continua: pruebas de la referencia, testbench oficial con 4/4 y las versiones cortas de la equivalencia, el lote de series, el barrido de fases, la degradación y los controles. |
| `make fondo-oficial` | Testbench oficial sin modificar con `sw/fondo.s`. |
| `make fondo-equiv` y `make fondo-equiv-ronda1` | Serie de práctica completa a 0,1 ms y 1 ms (y a 10 ms) y una serie de cada familia: bytes, estado interno, telemetría y protocolo. |
| `make fondo-series` | 1 050 series sintéticas por el RTL. |
| `make fondo-fases` | Peor caso de la respuesta barriendo la fase de llegada del precio. |
| `make fondo-degradacion` | Un gestor colgado, un voto que no llega y un voto atrasado: la decisión sigue saliendo a tiempo y es la esperada. |
| `make fondo-controles` | 15 errores puestos a propósito en el programa. Las pruebas tienen que detectarlos todos. |
| `make fondo-estres` | Matriz de estrés: SCLK, tiempos de `CS_n`, reset con la maestra transmitiendo, rondas seguidas y series pegadas en los bordes. |
| `make fondo-ticks` y `make fondo-timing` | Instrucciones, ciclos y tiempo por tick y por hilo; celdas y frecuencia en 10 semillas. |
| `make fondo-puerta` | Los criterios 1, 2, 3, 4, 6 y 7 de la puerta de simulación del peldaño, en versión completa. |
| `make cosim-barrel` | El gemelo digital del barrel contra el RTL, ciclo a ciclo, en 21 configuraciones. |
| `make fondo-gemelo-series` | Las 1 050 series y la práctica a los tres períodos en el gemelo, contra `ref/fondo.py`. |
| `make fondo-estres-rtl60` y `make fondo-estres-gemelo` | La matriz de estrés de R0 (60 casos) con la referencia del fondo, por el RTL y por el gemelo: tienen que dar las mismas líneas. |

### Tabla de parámetros, vigilante y relevo

`rtl/pochoco_tabla.v` es una BRAM de solo lectura con las constantes del algoritmo. `rtl/vigilante.v` pide la reconfiguración de la FPGA con la imagen de respaldo si el programa deja de escribir `DECISION`. Los bitstreams R1 y R2, la imagen múltiple y los moldes para `icebram` están en `bitstreams/`. Todo está explicado en `docs/tabla_vigilante.md`.

| Comando | Qué hace |
|---------|----------|
| `make check-vigilante` | Testbench del vigilante, sus propiedades formales y el relevo de punta a punta con las dos imágenes en un mismo testbench. |
| `make fondo-bitstreams` | Construye R1 y R2, los simula desde su `.asc` contra la referencia, cambia la tabla y el programa con `icebram`, comprueba el disparo del vigilante dentro del bitstream y arma la imagen múltiple con `icemulti`. |
| `make fondo-criterio5` | La campaña del core contra el Espino base y las mutaciones, con la máscara exacta de la extensión y el SoC del peldaño. |

### Espino segmentado

El core segmentado no reemplaza al base: se compila aparte y todas las pruebas se repiten sobre él.

| Comando | Qué hace |
|---------|----------|
| `make formal-base` | Prueba formal, con Yosys, de que el Espino base no cambió al agregar el pipeline: sus etapas IF e ID son equivalentes a las del repositorio del curso. |
| `make tb-seg` | Copia del testbench oficial con el core segmentado: 4/4 y decisiones idénticas a la referencia. |
| `make cpi-seg` | CPI y modelo de costo: `ciclos = IC + loads + saltos tomados`. |
| `make riesgos` | Programas de riesgos del Proyecto 3 en el base, el segmentado y la variante con ROM. Compara trazas contra el base, entre las dos variantes y contra el gemelo. |
| `make paralelo` y `make paralelo-largo` | Dos SoC completos, uno con cada core, corriendo el mismo programa aleatorio. Compara cada instrucción completada y el banco de registros entero. |
| `make mutaciones` | Cinco errores puestos a propósito en el core segmentado. Las pruebas anteriores tienen que detectarlos. |
| `make cosim-seg` | Gemelo digital con `--pipeline` contra el RTL, ciclo a ciclo. |
| `make equiv-seg` y `make equiv-rom` | Los 20 000 ticks contra la referencia, con el core segmentado y con la variante de ROM combinacional. |
| `make timing-seg` | Las 10 semillas de nextpnr deben cerrar a 25 MHz. |
| `make medir-espino` | Recursos, frecuencia máxima, CPI, MIPS y Ops/s del base y del segmentado. Resultado en `docs/mediciones/espino_segmentado.txt`. |
| `make bin-seg` y `make sim-bitstream-seg` | Bitstream del core segmentado y su simulación desde el `.asc`. |

## Cómo sintetizar y programar la placa

```bash
make bin             # yosys, nextpnr e icepack: deja build/pochoco_soc.bin
make sim-bitstream   # opcional: simula el bitstream y lo compara con la referencia
make prog            # iceprog build/pochoco_soc.bin, con la Go Board conectada por USB
```

`make bin` ensambla `sw/trade.s` si hace falta y deja el programa dentro del bitstream. El resumen de celdas, BRAM y frecuencia máxima queda en `build/nextpnr.log`.

Los bitstreams ya probados están en `bitstreams/`, con su hash y las pruebas que pasó cada uno. `make r0-reproducir` vuelve a construir el respaldo R0 desde las fuentes de su commit y comprueba que el resultado es, bit a bit, el archivo guardado. Para grabar uno de esos: `iceprog bitstreams/competencia_v1.bin`.

## Mediciones del repositorio base

```bash
make medir-base
```

Extrae la copia sin cambios del repositorio base (etiqueta `base-curso`) y mide celdas lógicas, BRAM, frecuencia máxima con 10 semillas, el costo de habilitar el shifter completo, si el encapsulado acepta un PLL y el CPI en simulación. El resultado queda en `docs/mediciones/base.txt`.

## Estructura

| Carpeta    | Contenido |
|------------|-----------|
| `rtl/`     | Pochoco SoC y Espino Core. |
| `sw/`      | `trade.s`, `fondo.s` (el programa de cuatro hilos del diseño integrado), los programas de ejemplo del repositorio base, los programas de riesgos (`hazard_*.s`) y `mix_clase7.s`. |
| `tb/`      | Testbench oficial, serie de práctica y testbenches propios. |
| `ref/`     | Referencia del algoritmo en Python (`trader.py` para `trade.s` y `fondo.py` para `fondo.s`), mercado de la maestra, series de prueba, protocolo de evaluación y gemelo digital. |
| `tools/`   | Ensamblador, generador de programas aleatorios y scripts de equivalencia, co-simulación y medición. |
| `bitstreams/` | Bitstreams de competencia, con su hash. |
| `formal/`  | Verificación formal: la equivalencia del Espino base con el del repositorio del curso (`formal/base_sin_cambios/`) y las propiedades de estructura del barrel (`formal/barrel/`) y las de la extensión de la ISA contra su especificación (`formal/xd/`). |
| `docs/`    | Enunciado, estado, decisiones, documentación y mediciones. |
| `informe/` | Informe en LaTeX (todavía vacío). |

## Mapa de memoria

| Dirección     | Registro | Uso |
|---------------|----------|-----|
| `0x0000_0000` | RAM unificada de 512 palabras | Instrucciones y datos. |
| `0x8000_0000` | Displays de 7 segmentos | Escritura. |
| `0x8000_0004` | LEDs | Escritura. |
| `0x8000_0008` | Interruptores | Lectura. |
| `0x8001_0000` | `STATUS` del SPI | Bit 0: hay un precio nuevo. Bit 1: `CS_n` activo. |
| `0x8001_0004` | `PRICE` | Último precio recibido. Leerlo baja la bandera de precio nuevo. |
| `0x8001_0008` | `DECISION` | Byte que la maestra lee en la transacción siguiente. |

![Arquitectura del Pochoco SoC](docs/pochoco_soc.svg)
