# Verificación: el flujo completo, de la referencia en Python a la maestra real

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio para la defensa. Junta en un solo recorrido lo que está repartido en `docs/puertas.md`, `docs/gemelo.md`, `docs/espino_barrel.md` (sección 8), `docs/extension_isa.md` (sección 7), `docs/fondo.md` (secciones 7 a 11), `docs/tabla_vigilante.md`, `docs/autoprueba.md` y `docs/contingencia.md`. Cifras de esos documentos y de `docs/mediciones/`.

## 1. La idea: tres modelos escritos por separado

Un número de verificación vale si compara contra algo **escrito por separado** y si se demuestra que la comparación detecta errores. Por eso cada pieza tiene:

1. **Una referencia independiente**: la referencia del algoritmo en Python, el Espino base del curso, o la especificación escrita aparte.
2. **Una comparación byte a byte o ciclo a ciclo**, no "se ve bien".
3. **Controles negativos**: errores puestos a propósito que la comparación tiene que detectar. Si una prueba nunca falla, no hay evidencia de que detecte errores.
4. **Una medida de cobertura**: cuántas instrucciones distintas, cuántas series, cuántas fases.

Hay tres modelos del mismo sistema, y cada par se compara:

| Modelo | Qué es | Dónde |
|--------|--------|-------|
| Referencia del algoritmo | Python, modela **valores**: qué byte deja el programa en `DECISION` por cada precio. Con las mismas operaciones enteras que el assembly | `ref/trader.py` (R0), `ref/fondo.py` (R1 y R2), `ref/market.py` (la contabilidad de la maestra) |
| RTL | Lo que se sintetiza. Simulado con Icarus (el simulador del testbench oficial) o Verilator (corridas largas) | `rtl/` |
| Gemelo digital | C, modela **ciclos**: el SoC completo, exacto al ciclo, sin simular compuertas. Corre el mismo `.hex` del bitstream | `ref/gemelo/gemelo.c` |

## 2. Referencia en Python

`ref/trader.py:74` es la regla con las mismas operaciones que `sw/trade.s` (incluido el desplazamiento por la identidad `p - ((S + 31) >> 5)`). Modela además los precios que el programa no ve durante el reset de encendido (`ref/trader.py:101`), porque en el testbench el reset largo hace que se pierdan 2 precios a 0,1 ms y 1 a 1 ms y 10 ms. `ref/market.py` es la tarea `ejecutar` del testbench portada a Python: `python3 ref/market.py validar decisiones.csv` rehace la contabilidad fila por fila.

`ref/fondo.py` modela el fondo completo: los tres gestores, la `max_media` del supervisor, los puntajes, la frontera de ventana, el voto y las fallas ("el voto del gestor k no llega entre los ticks N y M"). No modela ciclos: con los gestores sanos la decisión no depende de ellos (`docs/fondo.md`, sección 3.5). Está respaldada por 7 pruebas (`make test-fondo`), entre ellas una segunda escritura independiente con la aritmética de la factibilidad.

## 3. Equivalencia: RTL contra referencia

`make equiv` corre una copia del testbench oficial en la que solo cambian `PERIODO_NS`, `NTICKS` y el archivo de salida, y compara su `decisiones.csv` con el de la referencia **con `cmp`** (`tools/equiv.sh:69`). El testbench oficial no se toca nunca.

| Peldaño | Qué se comparó | Resultado | Fuente |
|---------|----------------|-----------|--------|
| R0 | 20 000 ticks de práctica a 0,1 ms (gemelo, Verilator e Icarus), 1 ms y 10 ms; 13 familias por el RTL; 3810 series en el gemelo a los tres períodos (7,62 millones de ticks por período) | Cero diferencias | `docs/puertas.md`, criterio 2 |
| R1 y R2 | Práctica a los tres períodos; una serie de 20 000 ticks de cada una de las 15 familias; 1 050 series sintéticas por el RTL (2,1 millones de ticks); 1 051 series a los tres períodos en el gemelo (6,36 millones de ticks) | Cero diferencias, comparando bytes, estado interno, telemetría y protocolo | `docs/puertas.md`, criterio 2 y notas |

Para el fondo se compara **el estado interno en cada decisión**, no solo los bytes: el flujo de bytes toma solo dos valores, y un error en un puntaje podría no verse en los bytes por miles de ticks (`docs/fondo.md`, sección 7).

## 4. El gemelo digital y la cosimulación

**Por qué existe.** Los 20 000 ticks a 10 ms toman unas 22 horas en Icarus (estimado), 22 minutos en Verilator y 0,02 s en el gemelo (`docs/gemelo.md`, sección 1). Con él se corren millones de ticks: el protocolo completo, la matriz de estrés y la firma de la autoprueba.

**Cómo se sabe que es correcto.** `make cosim` corre el RTL con `tb/tb_cpi.sv` y el gemelo con las mismas entradas y exige **trazas idénticas**: una línea por escritura de registro, acceso al bus, precio recibido y byte transmitido, con su número de ciclo.

| Core | Validación | Resultado | Fuente |
|------|------------|-----------|--------|
| Base | 8 configuraciones: timing oficial, fases que se recorren solas, SCLK de 500 y 100 kHz, tiempos que no son múltiplos de 40 ns, 4 programas aleatorios, testbench completo, mediciones por tick | Idénticas | `docs/gemelo.md`, sección 3 |
| Segmentado | `make cosim-seg` | Idénticas | `docs/gemelo.md`, sección 2 |
| Barrel y extensión | 21 configuraciones, 18,3 millones de eventos: el fondo, programas aleatorios de cuatro hilos, gestores colgados, rondas seguidas, reset con la maestra transmitiendo, series en los bordes | Idénticas | `docs/gemelo.md`, sección 7.4 |

Controles negativos: con `--borde 0` (otra forma de resolver la coincidencia de SCLK con el reloj) y con la máscara de la extensión equivocada, la traza difiere, como debe.

**El atajo.** El gemelo se salta las vueltas del lazo de sondeo que no cambian nada. En el barrel saca una foto del estado de los cuatro hilos y, si se repite, salta por períodos completos. Con y sin atajo los resultados son idénticos a los tres períodos, y la validación contra el RTL se hace sin atajo (pedir la traza lo desactiva).

**Lo que encontró tener dos modelos.** La validación del gemelo del barrel dio 20 de 21: en las rondas seguidas el RTL nunca cambiaba de período. El error estaba en tres testbenches, no en el gemelo: una variable declarada con valor inicial dentro de un bloque `initial` es estática en SystemVerilog (decisión T81). Cuando dos modelos escritos por separado no coinciden, alguno está mal, y no siempre es el nuevo.

## 5. El core contra el Espino base

Para un core nuevo la referencia es el Espino del curso, instrucción por instrucción.

| Core | Comparación | Cobertura | Controles negativos | Fuente |
|------|-------------|-----------|---------------------|--------|
| Segmentado | Dos SoC completos con el mismo programa aleatorio; se compara contador de programa, instrucción, escritura al banco, memoria y los 16 registros en cada instrucción | 1 600 000 instrucciones por configuración, 628 583 distintas (39 %) | 5 de 5 mutaciones | `docs/mediciones/paralelo_largo.txt` |
| Barrel | Cada hilo contra su propio Espino base | 7 948 558 instrucciones en 20 600 programas, 91,96 % distintas en toda la campaña | 21 de 21 mutaciones | `docs/mediciones/barrel/verificacion.txt` |
| Barrel con extensión | Contra el Espino base más la especificación escrita en el testbench (T60) | 7 966 640 instrucciones, 93,15 % distintas | 9 de 9 | `docs/mediciones/xd/verificacion.txt` |
| R1 y R2 exactos | La misma campaña con `emad`, `devk`, tabla y vigilante | 7 974 963 instrucciones, 92,80 % distintas | 6 de 6 de la extensión que aplican, 21 de 21 del barrel | `docs/puertas.md`, criterio 5 |

**La medida de cobertura importa.** El 13/11 la verificación del segmentado informaba 1,3 millones de instrucciones, pero solo el 0,4 % eran distintas: el generador caía en un punto fijo. Se corrigió (T52). Para el barrel, con programas con lazos el techo práctico era 40 %; en vez de cambiar la definición de "distinta" para que el número subiera, se cambió el generador a programas lineales y se hizo la definición más exigente: distinta en **toda la campaña**, no solo en su corrida (T57).

## 6. Verificación formal

| Qué | Método | Resultado | Fuente |
|-----|--------|-----------|--------|
| El Espino base no cambió | Equivalencia con los pases `equiv_*` de Yosys entre las etapas IF e ID actuales (modo base) y las del curso | 1376 puntos equivalentes | `formal/base_sin_cambios/`, `make formal-base` |
| Estructura del barrel | SymbiYosys, inducción: aislamiento de contextos, x0, burbujas, rotación, contador de cada hilo, arranque | 24 afirmaciones; 9 de 9 mutaciones con contraejemplo | `formal/barrel/propiedades.vh:53` (P1), `:91` (P10) |
| Cada instrucción de la extensión contra su especificación | SymbiYosys, inducción, para cualquier programa y operando | X1 a X5 en los 7 subconjuntos; 9 de 9 mutaciones | `formal/xd/propiedades_xd.vh:78` (X1) |
| El core con extensión no cambió RV32E | Equivalencia con el core de P1 | 1890 puntos | `make xd-formal` |
| El vigilante | SymbiYosys, inducción con N = 1, 4 y 7: `BOOT` solo sube con `CS_n` en alto, solo con la cuenta completa, no baja | 5 propiedades; 4 mutaciones con contraejemplo | `rtl/vigilante.v:136` a `:142`, `formal/vigilante/vigilante.sby` |

Lo que no se probó formalmente: que cada instrucción de RV32E calcule lo que debe en el barrel (se apoya en la comparación contra el base) y riscv-formal (evaluado, no hecho, T42).

**Un detalle de método.** Con profundidad de inducción 6 una mutación del barrel daba UNKNOWN en vez de FAIL; con 10 da contraejemplo. El script no cuenta un UNKNOWN como detección (`docs/espino_barrel.md`, sección 8.4).

## 7. Mutaciones y controles negativos

| Pieza | Errores puestos a propósito | Detectados |
|-------|-----------------------------|------------|
| Segmentado | 5 (`MUTA_FWD`, `MUTA_LOADUSE`, `MUTA_RDEN`, `MUTA_X0`, `MUTA_SQUASH`) | 5 |
| Barrel | 21 (contexto, contador de programa, x0, cargas, bus, arranque) | 21, cada una por las 7 comparaciones |
| Extensión | 9 (k, `funct7`, signo, desplazamiento, escritura, hilo equivocado, ...) | 9 por formal, 9 por simulación |
| Fondo | 15 (13 en el programa, 2 en la tabla) | 15 |
| Vigilante | 4 | 4 |
| Medidor del SPI | 4 | 4 |

Fuentes: `docs/espino_segmentado.md`, sección 9; `docs/mediciones/barrel/mutaciones.txt`; `docs/extension_isa.md`, sección 8; `docs/mediciones/fondo/r1/controles.txt`; `docs/tabla_vigilante.md`, sección 4.5; `docs/contingencia.md`, sección 3.

Las mutaciones encontraron errores **en las pruebas**, no solo en el diseño: una propiedad formal de `emad` que se evaluaba sin signo (`docs/extension_isa.md`, sección 7.1) y un control del fondo corrido sobre una serie donde el margen nunca decide (`docs/fondo.md`, sección 11).

## 8. La puerta de simulación: ocho criterios

Un bitstream sube a la escalera solo si pasa tres puertas en orden: simulación, placa y maestra (`docs/puertas.md`).

| N.º | Criterio | R0 | R1 | R2 |
|-----|----------|----|----|----|
| 1 | Testbench oficial sin modificar: 4/4 | 44 ciclos | 443 ciclos | 443 |
| 2 | Equivalencia con la referencia (sección 3) | Pasa | Pasa | Pasa |
| 3 | 25 MHz en 10 de 10 semillas | 42,43 MHz mín. (41,93 en la medición de P7, la del informe) | 51,59 | 47,86 |
| 4 | Peor caso barriendo las fases del sondeo, bajo la mitad del presupuesto de la ronda 3 (1131 ciclos) | 49 | 444 (568 con plazo agotado) | igual |
| 5 | Core en la configuración exacta contra el base (sección 5) | Formal y gemelo | Pasa | Pasa |
| 6 | Degradación: gestor colgado, voto ausente, voto atrasado | No aplica | 30 de 30, peor 679 | igual |
| 7 | Estrés: SCLK de 100 kHz a 1 MHz, tiempos de `CS_n`, reset con la maestra transmitiendo, rondas seguidas, series pegadas en 1 y 255 | 60 de 60 | 56 de 56 | 56 de 56, sin disparo |
| 8 | Bitstream ruteado simulado desde su `.asc`, 2000 ticks idénticos | Pasa | Pasa, dos series | Pasa, sin disparo |

**Por qué el criterio 4 barre fases.** El testbench oficial tiene un período de 2500 ciclos y solo recorre 4 de las 8 fases del sondeo del base. `tb/tb_estres.sv` es una maestra con la misma transacción y la misma medición, pero con los tiempos elegidos al ejecutar (T53).

**Por qué el criterio 8.** La tabla de R1 salía en cero en el bitstream aunque el RTL funcionaba (Yosys descartó el `$readmemh`). Ninguna prueba del RTL lo podía ver. Lo que se simula tiene que ser lo que se graba (`docs/tabla_vigilante.md`, sección 2.4). `make sim-bitstream` reconstruye el diseño desde el `.asc` ruteado y lo corre con `tb/tb_bitstream.sv`.

**Límite documentado de R1.** SCLK de 100 kHz con período de 0,1 ms deja 237 ciclos entre transacciones y el fondo necesita hasta 444. Queda fuera de la puerta por decisión del grupo (opción a); R1 responde a tiempo desde 110 kHz y el árbol usa 115 kHz (T124).

## 9. Matriz de estrés de P8

`make p8-matriz` corre en el gemelo, en 10 segundos, lo que la puerta no cubría (`docs/mediciones/p8/matriz.txt`, `docs/contingencia.md`, sección 2):

| Dimensión | Resultado |
|-----------|-----------|
| Período de 10 ms a 11,5 µs | R0 pasa en todas. R1 hasta 30 µs; período mínimo 26,94 µs (3,71 veces más rápido que la ronda 3); R0 11,34 µs (8,82 veces) |
| SCLK de 100 kHz a 1 MHz en los tres períodos | R0 pasa en todas; R1 falla solo con 100 kHz a 0,1 ms |
| Rondas de 500 a 200 000 ticks | Pasan los tres peldaños |
| Comisión de 0 a 50 y caja de 1 000 a 100 000 | Las decisiones no cambian; cambia cuánto cuesta operar. Con comisión de 20 o más conviene otro umbral (`tools/retune.py`) |

R2 no tiene columna propia en el gemelo, que no modela el vigilante: el vigilante solo dispara con 5 precios sin escritura, y en todas las celdas R1 escribe una vez por precio (T123).

## 10. Placa y maestra: lo que falta

| Puerta | Qué se prueba | Estado al 16/11 |
|--------|---------------|-----------------|
| Placa | **Autoprueba** (`docs/autoprueba.md`): el SoC del peldaño con una maestra SPI dentro de la FPGA que manda 2000 precios de un paseo aleatorio a los tres períodos y muestra una firma CRC-16 de las decisiones. La firma esperada sale del gemelo y de la referencia | R0: firma `a23c` igual en gemelo, referencia, RTL y bitstream ruteado, en simulación; en la placa (16/11) se vio la mitad baja ("3C") a los tres períodos y falta la mitad alta ("A2"). R2: firma a 0,1 ms en la placa; faltan 1 ms y 10 ms. R1: pendiente (`docs/mediciones/placa_16nov.md`) |
| Placa, R2 | El relevo ocurre al inyectar la falla y no ocurre en media hora de funcionamiento normal | Media hora sin disparo: pasa. Relevo: la UART midió 35,50 ms de reconfiguración, pero no se anotó si apareció la imagen testigo (`docs/mediciones/placa_16nov.md`) |
| Maestra (miércoles 25/11, por confirmar) | Las tres rondas sin perder precios ni decisiones; patrimonio igual al que predice el gemelo si la serie es conocida | Pendiente: `docs/checklist_26nov.md` |

Antes de los peldaños, el miércoles 25/11, por confirmar se graba el **medidor del SPI** (`rtl/medidor/medidor_spi.v`, T120): un bitstream aparte que escucha a la maestra y muestra en los 7 segmentos el período de SCLK, el período entre precios y los tiempos de `CS_n`. El SCLK real decide entre R0 y R1 (`docs/arbol_decision.md`, regla 3).

## 11. Integración continua

`.github/workflows/ci.yml` corre en cada push: ensamblador, referencia, testbench oficial, `make equiv`, `make fases`, `make cosim`, `make equiv-gemelo`, los chequeos del segmentado, del barrel, de la extensión, del fondo en R1 y en R2, del vigilante, la reproducción de R0 desde su commit (`make r0-reproducir`) y el molde de R0. Las corridas largas (Icarus completo, campañas completas) quedan como ejecución manual.

## 12. Preguntas típicas

1. **¿Cómo saben que `trade.s` decide igual que la referencia?** `make equiv` compara `decisiones.csv` con `cmp` (`tools/equiv.sh:69`) en los 20 000 ticks a los tres períodos y en las 3810 series del protocolo: cero diferencias.
2. **¿Qué es el gemelo digital y por qué confiar en él?** Un simulador en C del SoC exacto al ciclo. Se confía porque sus trazas son idénticas a las del RTL, evento por evento, en 8 configuraciones del base y 21 del barrel (`docs/gemelo.md`, secciones 3 y 7.4).
3. **¿Contra qué comparan un core nuevo?** Contra el Espino del curso, instrucción por instrucción, con los 16 registros y la memoria (`tb/tb_paralelo.sv`, `tb/barrel/tb_verif.sv`).
4. **¿Qué es una mutación y para qué sirve?** Un error puesto a propósito bajo `ifdef` (por ejemplo `rtl/espino_core/espino_if_stage.v:45`). Si la prueba no lo detecta, la prueba no sirve.
5. **¿Qué probaron formalmente?** Que el base no cambió, la estructura del barrel (aislamiento de hilos), cada instrucción de la extensión contra su especificación y el vigilante. No: el cálculo de cada instrucción RV32E en el barrel.
6. **¿Por qué simulan el bitstream si ya simularon el RTL?** Porque la tabla de R1 salió en cero en el bitstream con el RTL funcionando (`rtl/pochoco_tabla.v:36`). Lo que se graba tiene que ser lo que se simula.
7. **¿Por qué no basta el testbench oficial?** Recorre solo 4 de las 8 fases del sondeo, usa un solo SCLK y tiempos fijos. El peor caso real de R0 es 49 y no 44.
8. **¿Qué falta?** Completar la puerta de placa (las tres firmas de R1, R2 a 1 ms y 10 ms, la imagen testigo del relevo y la mitad alta de la firma de R0) y la puerta de la maestra del miércoles 25/11, por confirmar. Lo demás es simulación, salvo lo que se probó en la placa el 16/11 (`docs/mediciones/placa_16nov.md`).
9. **¿Qué encontró la verificación?** En los cores, ningún error. En los métodos varios: generador en punto fijo, variable estática en tres testbenches, propiedad formal sin signo, control mal elegido, tabla vacía en el bitstream.
10. **¿Cómo se reproduce todo?** Un objetivo de `make` por número; la integración continua corre las versiones cortas en cada push (`.github/workflows/ci.yml`).
