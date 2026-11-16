# Estado del proyecto

Se actualiza al cerrar cada tramo de trabajo. La versión anterior queda en el historial de git.

## Tramo 10: integración en `main` y paquete P3, fondo de competencia (15/11)

Rama `p3-fondo`, desde `main`. Bitácora: `docs/bitacora/p3.md`. Documento de estudio: `docs/fondo.md`. Decisiones T62 a T68 y la decisión de Nicolás sobre T58.

### Antes del paquete: `main` y R0

- `main` tiene P0, P1 y P2, cada uno con su integración continua en verde (corridas 43742516188, 43748081263 y 43776412628).
- **R0 desde `main`.** `make check` pasa y `make sim-bitstream` da 2000 ticks idénticos a la referencia, pero `make bin` ya no entrega el archivo guardado: los archivos del barrel y de la extensión cambian los nombres internos de Yosys y la ubicación de nextpnr, y el hash es otro. Desde el commit de P0 el hash sí es el guardado. Quedó `make r0-reproducir`, que construye R0 desde las fuentes de ese commit y compara el sha256 (T62). Corre en la integración continua, que lo reprodujo en una máquina de GitHub.

### Qué quedó hecho

- **`sw/fondo.s`**: el supervisor en el hilo 0 y un gestor en cada uno de los hilos 1 a 3, con `emad` y `devk`. 193 palabras de programa, 20 de tabla y 13 de estado: 226 de 512.
- **Decisión de Nicolás sobre T58**: R1 se compila solo con `emad` y `devk`. El fondo no usa `mulstep` ni lleva contabilidad (T63).
- **Protocolo de memoria compartida** documentado (`docs/fondo.md`, sección 3): qué palabra escribe cada hilo y cuándo, y cómo se detecta un voto viejo (el voto lleva el número del tick que el gestor procesó).
- **Degradación** (T64): plazo de 8 vueltas del lazo de lectura de votos. Vencido, cada voto viejo se reemplaza por la `max_media` que el supervisor calcula por su cuenta. Sin ningún voto, los bytes son los de `sw/trade.s`.
- **Tabla de parámetros** de 20 palabras, de solo lectura (T65). El programa no tiene constantes del algoritmo en sus instrucciones. Por ahora vive en la memoria de datos.
- **Telemetría** con un store por tick (T66): 7 segmentos con la posición objetivo, tres LED con los votos y uno de latido.
- **Referencia** `ref/fondo.py`, con sus pruebas (`make test-fondo`): reproduce los números que la factibilidad midió con su módulo en C.
- **Testbench** `tb/fondo/tb_fondo.sv`: mide por tick y por hilo, vigila el protocolo y saca el estado compartido en cada decisión. Se compila una vez; el programa y la serie se cargan al ejecutar.
- **Integración continua**: trabajo nuevo `fondo` con `make check-fondo`.

### Qué se midió

Los cuatro criterios de la puerta de simulación que pedía el paquete, más el 3:

| Criterio | Resultado |
|----------|-----------|
| 1. Testbench oficial sin modificar | 4/4. Peor caso 435 ciclos de 2262. `decisiones.csv` idéntico al de la referencia |
| 2. Equivalencia | Cero diferencias. Práctica completa a 0,1 ms, 1 ms y 10 ms; una serie de 20 000 ticks de cada una de las 15 familias; 1 050 series sintéticas de 2000 ticks (2,1 millones de ticks). Se compara el byte, el estado interno en cada decisión, la telemetría y el protocolo |
| 3. Timing | 10 de 10 semillas. 990 celdas, 12 BRAM, mínima 48,92 MHz |
| 4. Peor caso barriendo la fase | 480 ciclos con el programa sano y 564 con el plazo agotado, contra el límite de 1131 |
| 6. Degradación | 30 corridas de 20 000 ticks con un gestor colgado, un voto que no llega o un voto atrasado: decisión esperada en todas, peor caso 671 ciclos |

Mediciones por tick del punto 3.2 del enunciado (`docs/mediciones/fondo/ticks.txt`, ronda 3):

| | IC promedio | IC máximo | Ciclos promedio | CPI |
|-|-------------|-----------|-----------------|-----|
| Supervisor | 71,59 | 125 | 286,37 | 4 |
| Cada gestor | 25 | 25 | 100 | 4 |
| Agregado | 146,59 | 200 | 146,59 | 1 |

Respuesta de `byte_done` a `DECISION`: 235,37 ciclos en promedio (9,41 us) y 480 en el peor caso (19,2 us), el 21,2 % del presupuesto de la ronda 3.

Controles negativos: 15 errores puestos a propósito en el programa, 15 detectados.

### Hallazgos

1. **Con un voto ausente el fondo decide como `max_media`**, no como una mezcla. Con los pesos congelados en 6/5/5 la mayoría la define la banda del medio. Lo que separa al fondo sano de `max_media` es solo el ajuste de pesos.
2. **En la serie de práctica el fondo sano escribe los mismos 20 000 bytes que `max_media`**. Es coherente con lo que midió la factibilidad (el fondo no suma puntos), y obliga a probar con otras series: las pruebas de degradación usan además una de reversión, donde difieren en 1816 bytes.
3. **Un control negativo no se detectaba**: el margen de la frontera, corrido sobre 6000 ticks de la serie de reversión, donde nunca decide. Sobre la práctica sí. La equivalencia completa lo cubría, pero el control estaba mal elegido.
4. **Un error del testbench**, no del programa: una variable con valor inicial dentro de un `always` (estática en SystemVerilog) dejaba los votos de dos gestores sin registrar en la primera corrida.
5. **La respuesta no bajó respecto de la factibilidad** (235 ciclos contra 227) aunque los gestores pasaron de 35 a 25 instrucciones: el lazo con plazo lee los tres votos en cada vuelta y la tabla cuesta 5 loads por tick.

### Qué falta

- **Criterio 5 con la máscara exacta.** La campaña de P2 corrió con las tres instrucciones. Para R1 falta repetirla con `emad` y `devk` solas y con la tabla de P5: conviene hacerlo una vez, sobre el hardware definitivo.
- **Criterio 7** (estrés: SCLK, `CS_n`, reset con la maestra transmitiendo, rondas seguidas sin reset, serie pegada en 1 y en 255) y las series sintéticas a 1 ms y 10 ms: P4, con el gemelo del barrel. El testbench del fondo ya acepta esos parámetros.
- **Criterio 8** y los bitstreams R1 y R2: P5.
- **La tabla en su BRAM**: P5. Hoy está en la memoria de datos.
- **La razón de la decisión sobre T58** quedó sin escribir: el mensaje la traía como campo por completar.
- **Borde del plazo**: atrasos de un gestor entre 200 y 600 ciclos no se probaron contra la referencia, porque el resultado depende del ciclo exacto.
- Nada se ha probado en la placa.

### Qué conviene atacar después

1. **P4, el gemelo del barrel.** Es lo que falta para el criterio 7 y para correr el protocolo completo con el binario. Las equivalencias largas hoy dependen de Verilator (35 minutos la ronda de 10 ms).
2. **P5, tabla, vigilante y bitstreams.** Con P3 cerrado ya no depende de nada más. Es el camino a R1 y R2 antes del corte del 22/11.
3. **La pregunta al ayudante** sobre si un Espino multihilo con custom-0 sigue siendo Espino. Todo lo de P1 a P5 depende de esa respuesta.

## Tramo 9: paquete P2, extensión de la ISA sobre el barrel (15/11)

Rama `p2-extension`, desde `p1-barrel`. Bitácora: `docs/bitacora/p2.md`. Especificación y documento de estudio: `docs/extension_isa.md`. Decisiones T58 a T61.

### Qué quedó hecho

- **Tres instrucciones en custom-0 sobre el barrel**: `emad` (`rd = rs2 + (rs1 >>> 5)`), `devk` (`rd = (rs1 << 5) - rs2`) y `mulstep` (`rd = (rs1 << 1) + (rs1[31] ? rs2 : 0)`). Usan el sumador de la ALU con el operando A desplazado: sin sumador nuevo, sin estado y sin cambios en el control del pipeline. Se eligen al compilar (`-DESPINO_XD`, o una definición por instrucción). Sin definiciones el barrel es el de P1.
- **El decodificador, la ALU y la unidad de carga del Espino no se tocaron** (T59). Toda palabra de custom-0 que no sea una de las tres codificaciones exactas sigue siendo ilegal y sin efecto, incluido k distinto de 5.
- **Especificación** con codificación, semántica y ejemplo de cada instrucción, y **modelo ejecutable** `ref/xd.py`.
- **Ensamblador**: los tres mnemónicos, la directiva `.extension xd`, la opción `--xd`, rechazo de k distinto de 5, desensamblador y 37 tests nuevos (T61).
- **Prueba formal** de cada instrucción contra su especificación sobre el core, y del resto del core contra el de P1 (`make xd-formal`).
- **Verificación por simulación**: la campaña de P1 con la referencia ampliada a "Espino base más especificación" (T60), mutaciones, testbench de los dos módulos solos y un programa de punta a punta (`sw/xd/trade_xd.s`).
- **Integración continua**: trabajo nuevo `extension` con `make check-xd`. `make xd-completo` queda en la ejecución manual.

### Qué se midió

Los dos criterios del paquete:

| Criterio | Resultado |
|----------|-----------|
| Timing en 10 de 10 semillas | Los 7 subconjuntos cierran 10 de 10. Las tres instrucciones: 1034 celdas (+96), 12 BRAM, mínima 48,33 MHz, mediana 49,33, máxima 51,94. `emad` y `devk`: 990 celdas (+52), mínima 48,92 MHz |
| Equivalencia formal contra la especificación | X1 a X5 probadas por inducción en los 7 subconjuntos, para cualquier programa y cualquier operando. Core con `Xd = 0` equivalente al de P1 en 1890 puntos, y con cada subconjunto cuando custom-0 se reemplaza por nop. 9 de 9 mutaciones con contraejemplo |

Además, con las tres instrucciones:

| Prueba | Resultado |
|--------|-----------|
| Criterio 1 de la puerta | Testbench oficial sin modificar: 4/4 con `sw/trade.s` (83 ciclos) y con `sw/xd/trade_xd.s` (63 ciclos), decisiones idénticas a las del base |
| Criterio 5 de la puerta | 7 966 640 instrucciones en 20 600 programas, 93,15 % distintas en toda la campaña, cero diferencias. 1 030 081 son de la extensión. Campaña de lazos: 8 968 323, con 1 815 513 de la extensión. 9 de 9 mutaciones detectadas |
| Parte del criterio 2 | 20 000 ticks idénticos a `ref/trader.py` a 0,1 ms y a 1 ms, con los dos programas (patrimonio 26 070) |
| Módulos solos | 49 152 comprobaciones del decodificador y 1 200 000 resultados iguales al modelo, 5 de 5 mutaciones |
| Ensamblador | 124 tests (antes 87) |

### Hallazgos

1. **Un error de integración, encontrado por la primera corrida de la comparación**: las instrucciones nuevas no escribían `rd`. Corregido antes de medir nada.
2. **Un error en una propiedad formal, encontrado por una mutación**: el desplazamiento aritmético de `emad` escrito dentro de una suma se evalúa sin signo en Verilog. El RTL estaba bien. Queda como ejemplo de por qué cada prueba lleva controles negativos.
3. **Un hueco del generador, encontrado por la campaña completa**: 2 corridas de 20 600. Una palabra de custom-0 al azar resultó ser un `mulstep` que pisó la base del SPI y los stores cayeron en el código de otro hilo. Corregido y campaña repetida completa.
4. **El costo de la extensión es el multiplexor del operando A**: 16 a 28 celdas una instrucción sola, 96 las tres. Revisar la codificación completa cuesta lo que el ruido del conteo.

### Qué falta

- **Con qué subconjunto se compila R1** (T58). `emad` y `devk` entran seguro. `mulstep` solo si `sw/fondo.s` lleva la contabilidad. Es decisión de Nicolás al cerrar P3.
- **`sw/fondo.s` con las instrucciones** (P3). Regla para ese programa: empieza con `.extension xd`, y el puntaje en papel de los gestores tiene que llevarse en treintaidosavos, porque con k fijo en 5 no hay forma barata de calcular 16 p.
- **El gemelo no modela el barrel ni la extensión** (P4). `ref/xd.py` tiene las tres funciones listas para usarlas ahí.
- **La extensión solo existe en el barrel.** La tabla de variantes de P7 pide el base y el segmentado con y sin extensión: esas mediciones están en la factibilidad (rama `factibilidad-fondo`, `d_isa/`), con otra integración.
- **Criterios 4, 6, 7 y 8 de la puerta** con el programa que compite (P3 a P5).
- **Valor por defecto del SoC** para que el comando del testbench oficial compile lo que compite (T55, P5).
- **Nada probado en la placa.**

### Qué conviene atacar después y por qué

1. **P3, `sw/fondo.s`.** Es el camino crítico hacia R1 y la fecha de corte del 22/11. El hardware que necesita ya está verificado.
2. **P4 en paralelo**, el gemelo del barrel con la extensión: sin él la equivalencia larga del fondo depende de Verilator.
3. **Preguntas al ayudante**: si un Espino multihilo con instrucciones en custom-0 sigue siendo Espino. Todo lo de P1 a P5 depende de esa respuesta.

## Tramo 8: paquete P1, barrel en main (15/11)

Rama `p1-barrel`. Bitácora: `docs/bitacora/p1.md`. Documento de estudio: `docs/espino_barrel.md`. Decisiones T55 a T57.

### Qué quedó hecho

- **El Espino barrel está en `rtl/`**, elegible con `-DESPINO_BARREL` (T55). El core es el de la factibilidad sin cambios de lógica. El base y el segmentado no cambian: `make formal-base` y `make tb` pasan.
- **Suite de verificación en el repositorio**: scripts en `tools/barrel/`, testbenches en `tb/barrel/`, programas en `sw/barrel/`, propiedades en `formal/barrel/`, salidas en `docs/mediciones/barrel/`. `make check-barrel` corre en la integración continua en cada push y `make barrel-completo` queda como ejecución manual.
- **Generador de programas lineales** (`tools/barrel/prog_hilos.py --lineal`) para el criterio 5, con las instrucciones distintas contadas sobre toda la campaña (T57).
- **Pruebas de aislamiento y de memoria compartida**: `make barrel-aislamiento` y `make barrel-compartida`.
- **`docs/espino_barrel.md`**: etapas, por qué no hay riesgos, latencia por hilo, recursos, verificación, riesgos y preguntas de defensa.

### Qué se midió

Criterios 1, 3 y 5 de la puerta de simulación con `sw/trade.s` en el hilo 0:

| Criterio | Resultado |
|----------|-----------|
| 1. Testbench oficial sin modificar | 4/4, peor caso 83 ciclos de 2262, `decisiones.csv` idéntico al del base |
| 3. Timing | 10 de 10 semillas. 933 celdas, 12 BRAM. Mínima 52,62 MHz, mediana 55,65, máxima 59,18 |
| 5. Core contra el base | 7 948 558 instrucciones en 20 600 programas, 91,96 % distintas en toda la campaña, cero diferencias. 21 de 21 mutaciones detectadas, cada una por las 7 comparaciones |

Además: 8 966 903 instrucciones en la campaña de lazos de la factibilidad, repetida. 24 afirmaciones formales de estructura probadas y 9 de 9 mutaciones con contraejemplo. Los 20 000 ticks idénticos a la referencia a 0,1 ms y a 1 ms. `sw/trade.s` en cada uno de los cuatro hilos, 12 de 12 casos idénticos. CPI 1,000 agregado y 4,000 por hilo. Respuesta en 75,1 ciclos en promedio y 88 en el peor caso barriendo la fase. Netlist contra RTL, bitstream ruteado y cambio de programa con `icebram`, todos en verde.

### Hallazgos

1. **La primera campaña completa falló en 2 programas de 4 500 del grupo de memoria compartida.** Un `jalr` con base cualquiera llevaba a un hilo a ejecutar la zona de datos que los otros escriben. Son dos diferencias conocidas con el base (código que se modifica y contador de 11 bits en la última palabra), no un error del core. Se cerró el hueco en el testbench y la campaña se repitió completa. Queda como regla para `sw/fondo.s`: ningún `jalr` con una base que venga de datos.
2. **El margen del criterio 5 es chico**: 91,96 % contra 90 %. Lo que se repite son las instrucciones fijas del comienzo de cada hilo.
3. **Las cifras del base se movieron 3 celdas** (1086 contra 1083 de P0) al agregar archivos a `rtl/espino_core/`. Es ruido de la síntesis (T6); el RTL del base es equivalente al del curso.

### Qué falta

- **Corridas largas del barrel no repetidas en este paquete**: los 20 000 ticks con Icarus (`make barrel-equiv-icarus`) y a 10 ms (`make barrel-equiv-ronda1`). Pasaron en la factibilidad con el mismo RTL y la regla anterior.
- **`make fases` y `make estres` sobre el barrel** (criterios 4 y 7): `tools/estres.py` necesita el programa con tabla. El 88 de peor caso sale del barrido del prototipo, no de `make fases`.
- **El gemelo no modela el barrel** (P4).
- **Qué compila el comando del testbench oficial.** Sin definiciones sigue dando el base con `sw/trade.hex`. Si R1 o R2 compiten habrá que cambiar los valores por defecto (T55). Es decisión de Nicolás, en P5.
- **Tabla de arranque dentro de `sw/trade.s`** (T56): propuesta, sin decidir.

### Qué conviene atacar después y por qué

1. **P2, extensión sobre el barrel.** Sigue en el camino crítico hacia R1. La suite de P1 ya sirve para verificarla: la comparación contra el base necesita que el base no ejecute las instrucciones nuevas, así que P2 tiene que definir contra qué se comparan (su especificación, con formal).
2. **P4 en paralelo**: el gemelo del barrel desbloquea `make equiv-gemelo` y la matriz de estrés para el fondo.
3. **Preguntas al ayudante**, sobre todo si un Espino multihilo sigue siendo Espino. Todo lo de P1 a P5 depende de esa respuesta.

## Tramo 7: paquete P0, orden y respaldo (15/11)

Rama `p0-respaldo`. Primer paquete del plan vigente desde el 15/11 (decisión T50: compite el fondo en un chip, con una escalera de bitstreams R0, R1 y R2). El tramo 6, la factibilidad, está en la rama `factibilidad-fondo` y no se integra a `main`: los paquetes siguientes traen de ahí lo que necesiten. Bitácora: `docs/bitacora/p0.md`.

### Qué quedó hecho

- **Calendario en `main`** (T44): el commit pasó tal cual.
- **`max_media` en `sw/trade.s` y `ref/trader.py`** (T51). Cambia una constante, de -128 a -96. `ReglaBase` queda en la referencia como comparador del protocolo; `MaxMedia` es la oficial.
- **Tabla del punto 3.1** (`make tabla-3-1`, `docs/mediciones/tabla_3_1.txt`), revisada en la integración continua.
- **R0, `bitstreams/r0_base_max_media.bin`**, con su hash en `SHA256SUMS` (T54).
- **Puerta de simulación escrita como procedimiento** (`docs/puertas.md`): un comando por criterio. Para los criterios 4 y 7 se hizo una maestra configurable, `tb/tb_estres.sv` con `tools/estres.py` (`make fases`, `make estres`, T53). `make fases` corre en la integración continua.
- **Generador de programas aleatorios corregido** (T52) y verificación larga del segmentado repetida. `tb/tb_paralelo.sv` cuenta las instrucciones distintas. `--original` reproduce los programas viejos para medir la diferencia.

### Qué se midió

R0 pasó la puerta de simulación completa:

| Criterio | Resultado |
|----------|-----------|
| 1. Testbench oficial | 4/4, peor caso 44 ciclos de 2262 |
| 2. Equivalencia | Cero diferencias: 20 000 ticks a 0,1 ms (gemelo, Verilator e Icarus), 1 ms y 10 ms (gemelo y Verilator), 13 familias por el RTL, 3810 series en el gemelo a los tres períodos |
| 3. Timing | 10 de 10 semillas. 1083 celdas, 12 BRAM. Mínima 42,43 MHz, mediana 43,74, máxima 45,08 |
| 4. Fases | Peor caso 49 ciclos en las 8 fases, límite 1131 |
| 5. Core | Es el core base: `make formal-base` y `make cosim` |
| 6. Degradación | No aplica, un hilo |
| 7. Estrés | 60 casos en el rango pedido, todos pasan. SCLK funciona hasta 4 MHz |
| 8. Bitstream ruteado | 2 000 ticks idénticos a la referencia, patrimonio 9 661 |

Algoritmo, sobre la serie de práctica: `max_media` da 25 973 en la serie completa (regla base 27 062) y 9 661 en los primeros 2 000 ticks a 0,1 ms (regla base 9 617). En el testbench con los 20 000 ticks, 26 070 a los tres períodos.

Generador: la verificación larga del 13/11 comparaba 1 300 756 instrucciones, pero solo 4 644 eran distintas (0,4 %). La de hoy compara 1 600 000 por configuración, 628 583 distintas (39,3 %), con cero diferencias. Las 5 mutaciones del segmentado las detectan los programas de riesgos y 4 de 4 programas aleatorios cada una.

### Qué falta

- **Puertas de placa y de maestra para R0.** La de placa necesita la autoprueba de P6. La de maestra es el 26/11.
- **R0 no tiene telemetría** en los 7 segmentos ni en los LED: el programa no los toca.
- **El criterio 5 de la puerta para el barrel pide más de 90 % de instrucciones distintas.** Con la definición actual el techo práctico ronda 40 a 50 %: las comparaciones dan 0 o 1 y las constantes se repiten. P1 tiene que elegir otra definición (por ejemplo, el estado de los operandos) o un generador distinto, y decirlo antes de medir.
- **`docs/estado.md` de `main` no tiene el tramo 6**, que vive en la rama de la factibilidad.

### Qué conviene atacar después y por qué

1. **P1, barrel en `main`.** Es el camino crítico hacia R1 y la fecha de corte del 22/11. Lo primero es resolver la definición de "instrucción distinta" del criterio 5.
2. **P9 en paralelo.** La defensa necesita la respuesta a por qué la tabla del punto 3.1 baja de 27 062 a 25 973 con el algoritmo nuevo (T51).
3. **Preguntas al ayudante** (sección 16.8 del plan): sobre todo si un Espino multihilo con custom-0 sigue siendo Espino. Si la respuesta es no, R0 compite y P1 a P5 pasan a la edición de exhibición.

## Tramos 4 y 5: integración continua y frente C, producto 2x2 (13/11)

Los frentes A (algoritmo) y B (Espino segmentado) se trabajan en paralelo, cada uno en su rama. Esta sección cubre lo que se hizo aparte de ellos.

### Qué quedó hecho

- **Integración continua más corta** (T22). Los 20 000 ticks con Icarus salieron del push. Los reemplazan el gemelo digital a los tres períodos (`make equiv-gemelo-20k`, `tools/equiv_gemelo.sh`) y Verilator sobre el RTL. La corrida con Icarus queda como ejecución manual: `make equiv-r3`, o `gh workflow run CI -f icarus_completo=true`.
- **Producto 2x2 en punto fijo, solo diseño y costo** (`docs/producto_2x2.md`, T23 y T24). Especificación de la instrucción propuesta `kal2`, modelo de referencia (`ref/mv2x2.py`), generador de la versión de coeficientes fijos (`tools/gen_mv2x2.py`), versión con multiplicadores reales (`rtl/exhibicion/mv2x2_mult.v`), testbench (`tb/tb_mv2x2.sv`) y script de costo (`tools/costo_mv2x2.py`). No está en el SoC ni en el ensamblador.

### Qué se midió

- La integración continua pasó de 32 a 14 minutos. La equivalencia por push demora 2 minutos 19 segundos en local.
- Producto 2x2 (`make costo-mv2x2`, salida en `docs/mediciones/mv2x2_costo.txt`), con coeficientes de ejemplo:

| Versión | FPGA, módulo suelto | FPGA, integrada en el SoC base | GF180, solo síntesis |
|---------|---------------------|--------------------------------|----------------------|
| Coeficientes fijos, forma factorizada | 160 a 396 LUT según la precisión | agrega 217 a 368 celdas: no cabe (1291 de 1280 la más barata) | 8 000 a 20 000 um² |
| Coeficientes fijos, con los coeficientes calibrados del frente A | 251 LUT | agrega 328 celdas: no cabe (1402 de 1280) | 14 776 um² |
| Coeficientes fijos, forma directa | 324 a 427 LUT | | 30 000 um² |
| Multiplicadores reales | 1645 LUT (8 bits) y 3094 LUT (14 bits): más que la FPGA | | 67 000 a 130 000 um² |

- Las tres implementaciones coinciden con el modelo en 20 000 vectores por matriz.

### Qué falta

- **Medir las formas de achicarlo** (carriles más angostos, sin saturación, versión secuencial o periférico). Son estimaciones.
- **Equivalencia formal** entre las dos versiones y contra la especificación.
- **La integración en el core se hizo solo para contar celdas.** No está verificada como instrucción y el ensamblador no la conoce.
- **Correr `make equiv-r3` a mano** antes de cada etiqueta y cada vez que cambie el RTL del core o del esclavo SPI.

### Qué conviene atacar después y por qué

1. **El producto 2x2 queda en la edición de exhibición.** El estimador de dos estados no gana bajo el protocolo (T30) y el hardware no cabe en la FPGA: agrega 328 celdas y el pipeline deja 286 libres. Si se construye, es para la edición ASIC o como periférico secuencial, y para medir el peldaño de la escalera.
2. **El resto del frente C** (especificación de la extensión en custom-0, soporte en el ensamblador, periférico estimador y la escalera de la clase 7 medida) necesita el kernel definitivo del frente A.

## Tramo 4: frente A, algoritmo (13/11)

Rama `frente-a`. El detalle está en `docs/algoritmo.md`. **`ref/trader.py` y `sw/trade.s` no cambiaron: la regla base sigue siendo el algoritmo de la placa hasta que se elija un candidato.**

### Qué quedó hecho

- **Modelo del generador** (`ref/generador.py`, `ref/calibracion.py`). Nivel que pasea más transitoria AR(1) más redondeo, con dos regímenes de volatilidad y saltos. Ajustado por máxima verosimilitud con el filtro de Kalman y validado contra la serie de práctica.
- **Familias sintéticas calibradas en dos grupos** (`ref/series.py`). 4 plausibles y 10 de estrés, todas derivadas del modelo. Se agregaron `modelo`, `modelo_vecino`, `volatil` y `nivel_bajo`.
- **Protocolo** (`ref/protocolo.py`). Grupos, diferencia pareada con error estándar, candidatos por nombre (`cand:...`, `trader:...`) y semilla reservada.
- **Filtro de Kalman y política óptima** (`ref/politica_optima.py`). Ganancias en estado estacionario, matriz 2x2 en punto fijo y programación dinámica con comisión, desfase de un tick y 63 acciones por orden.
- **Familia paramétrica de estrategias** (`ref/candidatos.py`) y **motor en C** (`ref/motor/motor.c`, `ref/motor.py`), con pruebas de que coinciden (`make test-candidatos`, en la integración continua).
- **Exploración por ideas** (`ref/explorar.py`): bandas, estimadores, bandas escaladas con la volatilidad, saltos, cortes, guardia, tope, tamaño de órdenes, asimetría y potencia de una guardia estadística.
- **Ideas que aprenden en vivo** (`ref/experimentos.py`): población de traders, adaptación con prior fuerte y perceptrón, con control de rotación.
- **Guardia de régimen y tope de pérdida**, sin multiplicaciones.
- **Candidatos sobre la frontera** (`ref/frontera.py`), evaluados con una semilla que no se usó para elegir nada.
- Decisiones T25 a T31 en `docs/decisiones.md`.

### Qué se midió

Generador (`make generador`):

| Medición | Valor |
|----------|-------|
| Paso del nivel y de la transitoria, régimen tranquilo | 0,39 y 0,33 por tick |
| Vida media de la transitoria | 17,5 ticks |
| Régimen ruidoso | 14 % del tiempo, 2,98 veces más volatilidad |
| Saltos | 5 en 20 000 ticks, permanentes |
| Mejora de la verosimilitud por incluir la reversión | 10,2 en 20 000 ticks, 1 por ronda |
| Razón de varianza a 100 ticks: medida, sin redondeo, paseo redondeado | 0,53, 0,67 y 0,77 |

Regla base con las familias calibradas (`make protocolo`): plausibles 10 955 de media y 8 553 de percentil 5. Estrés: `tendencia` 9 410 y 5 777, `cambio_de_caracter` 9 043 y 2 592, `paseo` 9 927 y 7 866.

Política óptima (`make politica`): 8,4 % por ronda como techo del modelo. La regla base saca 5,2 % en el modelo. Las bandas óptimas del modelo, probadas en el remuestreo, dan 10 119 contra 10 813 de la regla base.

Candidatos con la semilla reservada (`make frontera`), diferencia contra la regla base con su error estándar:

| Candidato | Bloques: media, peor | Remuestreo: media, dif., p5 | Plausibles: media, dif., p5 | Estrés: p5 |
|-----------|----------------------|-----------------------------|------------------------------|------------|
| `prudente` (E=192, X=-32) | 10 712, 10 000 | 10 639, -115 ± 14, 9 308 | 10 619, -334 ± 19, 9 048 | 6 986 |
| `base` (E=128, X=0) | 11 069, 9 720 | 10 754, 8 958 | 10 954, 8 741 | 5 615 |
| `max_media` (E=96, X=0) | 11 043, 9 620 | 10 833, +79 ± 11, 8 788 | 11 103, +150 ± 15, 8 622 | 5 071 |
| `guardia` (E=96 con saltos y guardia) | 11 018, 9 024 | 10 735, -20 ± 14, 8 881 | 10 893, -60 ± 15, 8 434 | 6 658 |
| `guardia_tope` (además tope de pérdida) | 11 018, 9 024 | 10 716, -38 ± 15, 8 833 | 10 714, -239 ± 32, 8 052 | 6 828 |

Guardia y tope: en los 10 bloques de práctica no se activan nunca. En los remuestreos la guardia pausa en el 2,3 % de las series y el tope salta en el 1,7 %. La guardia sube el percentil 5 de `tendencia` de 4 631 a 6 375 y el de `cambio_de_caracter` de 2 136 a 5 692. El tope deja el peor caso de esas familias sobre 5 200.

El binario contra la referencia con las series nuevas (`make equiv-gemelo`): 3810 series a los tres períodos, 22 860 000 ticks, cero diferencias.

### Hallazgos

1. **La mitad de la reversión aparente es redondeo** y no se puede operar, porque la orden se ejecuta un tick después.
2. **La señal es débil y el techo está cerca.** No hay una mejora grande escondida: lo que queda sobre la regla base es del orden de 1 a 3 puntos de media.
3. **El estimador casi no importa.** Media exponencial, suma móvil y Kalman de dos estados rinden lo mismo con bandas equivalentes. El filtro óptimo baja la incertidumbre de la transitoria de 1,19 a 1,11.
4. **Lo que mueve el resultado es cuánto se opera.** Bandas más angostas suben la media en el modelo y bajan el percentil 5 en todos lados.
5. **Todo corte de pérdidas cuesta media**, porque en una serie que revierte se vende en el fondo.
6. **No se puede detectar en vivo si la serie revierte.** La guardia mide si las entradas vuelven a la media.
7. **Población, adaptación en vivo y perceptrón no ganan** aun con control de rotación.
8. **Ningún candidato reemplaza formalmente a la regla base** con las tres condiciones del protocolo. `max_media` falla por 26 puntos en la media de los bloques (el error es 238) y por las familias de estrés.

### Qué falta

- **Elegir el candidato.** Es decisión de Nicolás. La recomendación con el perfil de máximo patrimonio esperado es `max_media`, y `guardia` si se le da más de 20 % de probabilidad a una serie con tendencia.
- **Escribir el candidato elegido en `sw/trade.s`** con su equivalencia. `max_media` es cambiar una constante. `guardia` son unas 70 instrucciones (estimado).
- **Niveles por presupuesto.** No se hizo: ningún modelo más pesado ganó, así que no hay nada que correr con el tiempo que sobra en las rondas 1 y 2.
- **Rondas largas.** La guardia pausa 1000 ticks y el tope apaga hasta el final. Si una ronda dura mucho más que 2000 ticks hay que rearmar el tope.
- **Tabla del punto 3.1 con el algoritmo final**, cuando se elija.

### Qué conviene atacar después y por qué

1. **Decidir entre `max_media` y `guardia`** y llevarlo a `trade.s` antes del 18/11, para que llegue a la maestra.
2. **Preguntar al ayudante si las series ocultas salen del mismo generador y cuánto dura una ronda.** Las dos respuestas cambian la elección: con el mismo generador gana `max_media`, con rondas largas hay que rearmar el tope.
3. **Frente C.** El producto de matriz 2x2 ya tiene sus coeficientes (`docs/algoritmo.md`, sección 4.1). Va a la edición de exhibición.
4. **Frente E.** La matriz de estrés puede usar el motor y las familias calibradas tal como están.

## Tramo 5: frente B, Espino segmentado (13/11)

### Qué quedó hecho

- **Pipeline de 3 etapas en la FPGA** (`docs/espino_segmentado.md`). Es el core con lectura anticipada del Proyecto 3, portado a BRAM: la memoria de instrucciones se lee en el flanco de bajada (`SB_RAM40_4KNR`), el banco de registros lee durante el fetch y adelanta el dato recién escrito. Se elige al compilar con `-DESPINO_SEGMENTADO`. **El core por defecto sigue siendo el Espino base** y `bitstreams/competencia_v1.bin` no se tocó.
- **Los dos caminos de fetch de la sección 15**, construidos y medidos: flanco de bajada sobre BRAM y ROM combinacional de `trade.s` (`-DESPINO_ROM`). Se eligió el primero (T33).
- **Recorte de celdas** medido uno por uno. El único que rinde es el contador de programa de 11 bits.
- **Verificación**: prueba formal de que el base no cambió (`make formal-base`), programas de riesgos del Proyecto 3 (`make riesgos`), ejecución en paralelo de dos SoC con programas aleatorios (`make paralelo`, `make paralelo-largo`), controles negativos por mutación (`make mutaciones`), gemelo ciclo a ciclo (`make cosim-seg`) y equivalencia con la referencia (`make equiv-seg`, `make equiv-rom`).
- **Gemelo digital** con la tabla de ciclos del segmentado (`--pipeline`), validado contra el RTL.
- **`tb/tb_cpi.sv`** mide las dos variantes: ya no depende de señales que solo existen en el base.
- **Mediciones** en `docs/mediciones/`: `espino_segmentado.txt`, `ticks_segmentado.txt`, `paralelo_largo.txt` y `mutaciones.txt`.
- **Bitstream** `bitstreams/segmentado_v1.bin`, con hash, simulado desde el `.asc`.
- **Integración continua**: `make check-seg` en cada push (cerca de un minuto en local: prueba formal, modelo de costo, riesgos, paralelo, 20 000 ticks y timing en 10 semillas). Lo largo queda como ejecución manual (`segmentado-completo`).
- Decisiones T32 a T43 en `docs/decisiones.md`.

### Qué se midió

Recursos y timing, `nextpnr --hx1k --package vq100 --freq 25`, 10 semillas (`make medir-espino`):

| Variante | Celdas | BRAM | Fmax mínima | Mediana | Máxima | Cierran a 25 MHz |
|----------|--------|------|-------------|---------|--------|------------------|
| Espino base | 1083 | 12 | 42,43 | 43,74 | 45,08 | 10 de 10 |
| Segmentado, fetch en flanco de bajada | 994 | 12 | 51,13 | 53,50 | 54,50 | 10 de 10 |
| Segmentado, ROM combinacional | 1055 | 8 | 50,04 | 53,16 | 55,05 | 10 de 10 |

- **Recortes.** Contador de programa de 32 a 11 bits: recupera 133 celdas en el base (1083 a 950) y 180 en el segmentado (1174 a 994). Decodificación sin uso: dentro del ruido (entre 17 menos y 12 más). Registros de lectura de periféricos: 0, la síntesis ya los recorta.
- **Costo del pipeline.** 91 celdas con el mismo ancho de contador. Con el recorte queda 89 celdas bajo el base y deja 286 libres.
- **Rutas de medio ciclo.** nextpnr las analiza con medio período (comprobado con un diseño de prueba; `icetime` no). Ninguna pasa de 9,8 ns de los 20 disponibles. La ruta crítica es de ciclo completo: 19,6 ns en la peor semilla.

CPI, con los mismos programas (`tb/tb_cpi.sv`, modelo de costo con diferencia de 0 ciclos en todos):

| | Base | Segmentado | Clase 7, estimado |
|-|------|------------|-------------------|
| ALU, store, salto no tomado | 2 | 1 | 1 |
| Load | 3 | 2 | 2 |
| Salto tomado, `jal`, `jalr` | 3 | 2 | 3 |
| CPI con el mix de la clase (`sw/mix_clase7.s`) | 2,350 | 1,350 | 1,5 |
| MIPS con el mix | 10,64 | 18,52 | 16,7 |
| Ppeak | 12,5 MOPS | 25 MOPS | 25 MOPS |
| `trade.s`, respuesta: ciclos promedio y peor caso | 41 y 44 | 22 y 26 | |
| `trade.s`, tick completo: ciclos promedio y peor caso | 63 y 66 | 34 y 38 | |
| `trade.s`, peor caso real barriendo la fase del sondeo | 49 | 27 | |

Verificación:

| Prueba | Resultado |
|--------|-----------|
| `make formal-base` | Etapas IF e ID en modo base equivalentes a las del repositorio del curso: 1376 puntos probados |
| `make riesgos` | `hazard_test` (56 comprobaciones), `hazard_review` (48) y `hazard_cycles` (5): mismas secuencias que el base, trazas idénticas entre BRAM y ROM, e idénticas al gemelo |
| `make paralelo-largo` | 1 300 756 instrucciones comparadas una por una con el contador de 11 bits y 1 600 000 con el de 32, con el banco de registros completo en cada una. Cero diferencias |
| `make mutaciones` | 5 de 5 detectadas, por los programas de riesgos y por la ejecución en paralelo |
| `make cosim-seg` | Gemelo contra RTL: 1 007 124 eventos de `trade.hex`, 846 705 escrituras de programas aleatorios, 20 000 ticks |
| `make equiv-seg`, `make equiv-rom` | 20 000 ticks idénticos a `ref/trader.py` (Verilator a 0,1 ms y 1 ms, Icarus corto, gemelo a los tres períodos) |
| `make equiv-r3` y `make equiv-seg-icarus` | La corrida manual de T22, que toca repetir porque cambió el RTL del core: 20 000 ticks con Icarus, base y segmentado, idénticos a la referencia (patrimonio 26 795) |
| `make sim-bitstream-seg` | El bitstream simulado decide igual que la referencia en 2000 ticks |

### Hallazgos

1. **El pipeline medido supera la estimación de la clase 7.** El salto tomado cuesta 2 ciclos y no 3, porque la instrucción se lee medio ciclo después de que cambia el contador de programa y hay una sola instrucción que anular.
2. **El pipeline sube la frecuencia máxima en vez de bajarla**, de 43,7 a 53,5 MHz de mediana. El multiplexor de adelantamiento entra a la ruta crítica, pero la decodificación sale de ella.
3. **El prototipo anotado (24,4 a 25,6 MHz con el core sin rediseñar) no se reprodujo**: con la decodificación registrada el flanco de bajada cierra con más del doble de margen.
4. **Yosys no reparte en BRAM una memoria con puertos de lectura en flancos distintos.** Con un solo arreglo el diseño ocupaba 47 551 celdas. Hace falta una copia explícita para el fetch (T34).
5. **El gemelo tenía un caso que el base no ejercita**: la instrucción que sigue a un store al esclavo SPI se completa en el ciclo inmediato. Lo encontraron los programas aleatorios (T40).
6. **`make bin` ya no reproduce el hash de `competencia_v1.bin`.** La lógica del base es la misma, pero cambiaron nombres internos y nextpnr ubica distinto (T32).

### Qué falta del frente B

- **Decidir si el segmentado va a la maestra el 19/11** como candidato a la edición de competencia. No cambia el patrimonio con la regla base. Libera 89 celdas y baja la respuesta de 44 a 26 ciclos.
- **Probar `segmentado_v1.bin` en la placa.** Lo hace Nicolás con `iceprog`. El riesgo propio de este diseño es el ciclo de trabajo del reloj: las rutas de medio ciclo toleran entre 25 % y 75 %.
- **riscv-formal.** Evaluado y sin hacer. `docs/espino_segmentado.md` lista lo que falta, cerca de un día (T42).
- **`icebram` con dos copias de la memoria.** El programa está en la memoria de datos y en la del fetch: hay que comprobar que `icebram` reemplaza las dos.
- **Equivalencia formal de `pochoco_ram.v` y `espino_register_file.v` en modo base.** `make formal-base` cubre IF e ID. Esos dos tienen memorias y hoy se cubren con simulación.

### Qué conviene atacar después y por qué

1. **Frente C sobre el segmentado.** Quedan 286 celdas libres y 4 BRAM. La instrucción de paso de media exponencial reemplaza el bloque más caro de `trade.s`, y el producto 2x2 cabe o no según su versión de coeficientes fijos.
2. **Checklist del 19/11 con los dos bitstreams.** Si el segmentado va a competir tiene que pasar ese día. Conviene llevar `competencia_v1.bin` y `segmentado_v1.bin` y probar los dos.
3. **`icebram`** antes del 18/11, porque condiciona el kit de contingencia y ahora hay dos memorias que actualizar.

## Tramo 3: gemelo digital, series de prueba y protocolo de evaluación (13/11)

### Qué quedó hecho

- **Gemelo digital** (`ref/gemelo/gemelo.c`, `ref/gemelo.py`, `docs/gemelo.md`). Simulador en C del SoC con exactitud de ciclo: core por instrucción, esclavo SPI flanco por flanco, reset, maestra y contabilidad. Ejecuta el mismo `trade.hex` del bitstream.
- **Validación contra el RTL** (`make cosim`, `tools/cosim.sh`). `tb/tb_cpi.sv` escribe una traza con el ciclo de cada evento y el gemelo escribe la misma. Se comparan con `cmp`.
- **Generador de programas aleatorios** (`tools/prog_aleatorio.py`). Toda la ISA base, shifts, codificaciones inválidas y accesos a los periféricos. Sirve también para comparar el Espino original con el segmentado.
- **Series de prueba** (`ref/series.py`). Bloques de práctica, remuestreo por bloques de incrementos y 10 familias sintéticas, reproducibles con semilla.
- **Protocolo** (`ref/protocolo.py`, `docs/protocolo.md`). Evaluación, comparación con criterio de aceptación, meseta de parámetros y verificación del binario contra la referencia.
- **Integración continua.** Se agregaron la equivalencia de 20 000 ticks, las pruebas de la referencia, `make cosim` y `make equiv-gemelo`.
- Decisiones T17 a T21 en `docs/decisiones.md`.

### Qué se midió

Gemelo contra RTL (`make cosim`):

| Prueba | Resultado |
|--------|-----------|
| `trade.hex`, timing oficial, 300 ticks | 282 210 eventos idénticos |
| `trade.hex` con otros tres timings de SPI, período y reset | 347 867 eventos idénticos |
| 4 programas aleatorios | 555 966 eventos idénticos |
| Testbench oficial, 20 000 ticks | `decisiones.csv` y resumen idénticos |
| Mediciones por tick, 20 000 ticks | 19 998 ticks idénticos |
| Con y sin atajo del sondeo, a los tres períodos | Idénticos |
| Control negativo (`--borde 0`) | La traza difiere |

Velocidad, 20 000 ticks a 10 ms: Icarus unas 22 horas (estimado), Verilator 22 minutos, gemelo 0,02 segundos.

Regla base bajo el protocolo (`make protocolo`, resultados en `docs/mediciones/protocolo_*.txt`):

| Conjunto | Media | Mediana | Percentil 5 | Peor | Supera a comprar y mantener |
|----------|-------|---------|-------------|------|-----------------------------|
| 10 bloques de práctica | 11 069 | 11 103 | 9 720 | 9 720 | 90 % |
| 1000 remuestreos | 10 772 | 10 703 | 8 914 | 6 520 | 72 % |
| Paseo aleatorio (200) | 9 873 | 9 947 | 7 126 | 2 918 | 42 % |
| Tendencia (200) | 9 543 | 10 015 | 4 530 | 969 | 46 % |
| Cambio de carácter (200) | 13 225 | 13 800 | 3 507 | 389 | 76 % |
| Dos componentes (200) | 25 138 | 23 137 | 16 399 | 13 134 | 100 % |

- **Meseta.** (k, entra, sale) = (5, 4, 0) es el máximo de 45 combinaciones en los bloques (11 069; sus vecinos dan entre 10 446 y 11 043). En 300 remuestreos da 10 816 y el vecino con entra 3 da 10 921. No es un máximo aislado y la diferencia es del tamaño del ruido.
- **Suma móvil de 64 contra la base.** No la reemplaza: pierde en la media de los bloques (10 951 contra 11 069) y en los remuestreos (10 624 contra 10 772), aunque gana en todas las familias sintéticas.
- **El binario contra la referencia** (`make equiv-gemelo`). 3010 series a 0,1 ms, 1 ms y 10 ms: 18 060 000 ticks, cero diferencias, ningún precio sin respuesta.

### Hallazgos

1. **El peor caso del testbench no es el peor caso.** El testbench informa 44 ciclos. Barriendo las 8 fases del lazo de sondeo con el gemelo, la respuesta va de 37 a 44 ciclos en régimen y de 42 a 49 con el primer precio. El peor caso real es 49 ciclos.
2. **El testbench sube SCLK justo en un flanco del reloj.** Icarus y Verilator lo resuelven igual. En la placa la maestra es asíncrona. Las decisiones no dependen de eso (T19).
3. **La regla base no tiene tope de pérdida.** En tendencia a la baja compra y no vende hasta que el precio recupere la media. Peor caso 969 en `tendencia` y 389 en `cambio_de_caracter`.
4. **La ganancia esperada por ronda es del orden de 8 %, con mucha dispersión.** En los remuestreos el patrimonio final va de 6 520 a 15 637 y uno de cada cinco termina bajo 10 000.
5. **El redondeo a enteros fabrica reversión aparente.** Un paseo aleatorio redondeado tiene razón de varianza 0,87 a 10 ticks. Hay que separarlo de la reversión real al identificar el generador.

### Qué falta del tramo 3

- **Las familias sintéticas no estaban calibradas.** Resuelto en el tramo 4: salen del modelo ajustado. Los números de las familias sintéticas de la tabla de arriba son los de antes de calibrar.
- **El criterio de aceptación no tenía error estadístico.** Resuelto en el tramo 4: la comparación entrega la diferencia pareada con su error estándar.
- **El gemelo modela solo el Espino base.** Cuando el core cambie hay que actualizar su tabla de ciclos y repetir `make cosim`.

## Tramo 2: regla base de punta a punta (13/11)

### Qué quedó hecho

- **Ensamblador.** Directiva `.org` y salidas `--vh` y `--rom` del Proyecto 3. 87 tests. `trade.hex` queda relleno a 512 palabras.
- **Referencia.** `ref/market.py` (porte del mercado del testbench) y `ref/trader.py` (regla base con la aritmética de `trade.s`, y modelo de los precios que se pierden en el reset). `make test-ref`: 22 pruebas.
- **`sw/trade.s`, variante solo software.** Regla base sin saltos que dependan del precio. Explicado bloque por bloque en `docs/trade_s.md`.
- **`make equiv`** (`tools/equiv.sh`). Copia parametrizada del testbench contra la referencia, con `cmp`.
- **Mediciones por tick** (`make medir-ticks`, `tb/tb_cpi.sv`).
- **Primer bitstream de competencia** en `bitstreams/competencia_v1.bin`, con hash, y `make sim-bitstream`.
- Decisiones T10 a T16.

### Qué se midió

Testbench oficial sin modificar: **4/4**, peor caso 44 ciclos de 2 262 disponibles, patrimonio 9 617 en los 2000 ticks por defecto.

Equivalencia con la referencia (`decisiones.csv` idéntico byte a byte):

| Corrida | Simulador | Ticks | Patrimonio |
|---------|-----------|-------|------------|
| 0,1 ms | Icarus | 20 000 | 26 795 |
| 0,1 ms | Verilator | 20 000 | 26 795 |
| 1 ms | Verilator | 20 000 | 27 306 |
| 10 ms (`make equiv-largo`) | Verilator | 20 000 | 27 306 |
| 1 ms y 10 ms | Icarus | 200 y 20 | |
| Una serie de cada familia sintética | Verilator | 11 de 2000 | |

El patrimonio no es 27 062 porque en el testbench el programa no ve los primeros precios, que llegan durante el reset (2 a 0,1 ms, 1 a 1 ms y 10 ms). La referencia lo modela (T13).

Tabla del punto 3.1, serie completa viendo todos los precios (`python3 ref/trader.py tb/practica.csv`):

| Estrategia | Patrimonio | Órdenes | Comisiones | Pérdida máxima |
|------------|------------|---------|------------|----------------|
| No operar | 10 000 | 0 | 0 | 0 |
| Comprar y mantener | 6 497 | 1 | 5 | |
| Regla base | 27 062 | 388 | 1 940 | 2 929 |

Mediciones por tick del punto 3.2, iguales en las tres rondas (`docs/mediciones/ticks_software.txt`):

| Ventana | IC promedio | IC peor | Ciclos promedio | Ciclos peor | CPI | Tiempo peor caso |
|---------|-------------|---------|-----------------|-------------|-----|------------------|
| Respuesta (hasta `DECISION`) | 19,5 | 21 | 41 | 44 | 2,10 | 1,76 us |
| Tick completo | 28,5 | 30 | 63 | 66 | 2,21 | 2,64 us |

El trabajo sin la espera son 27 instrucciones y 58 ciclos. La actualización de la media es el bloque más caro: 8 instrucciones y 17 ciclos, el 29 %.

Bitstream `competencia_v1.bin`: 1083 celdas de 1280 (84 %), 12 BRAM, 44,0 MHz. Simulado desde el `.asc`: 2000 ticks idénticos a la referencia.

### Diferencias con lo que teníamos anotado

1. **Costo de la regla base.** Estimábamos unas 30 instrucciones y 70 ciclos por tick. Medido: 28,5 instrucciones y 63 ciclos con la espera, 27 y 58 sin ella.
2. **Entrar no es una sola orden.** Por el límite de 63 acciones, entrar toma 2 órdenes con la caja inicial y hasta 6 cuando el patrimonio crece. La regla base entra 75 veces y ejecuta 388 órdenes.
3. **No hay numpy en el entorno.** Todo `ref/` usa la biblioteca estándar (T21).

Nada de lo encontrado contradice al enunciado ni al testbench.

### Qué falta del tramo 2

- **Probar el bitstream en la placa.** Lo hace Nicolás con `iceprog`. Sin la maestra no hay nada que observar: el programa no usa LEDs ni displays.
- **Reset más corto.** Sigue pendiente medir en la placa el reset mínimo que arranca bien (T3).
- **`icebram`.** `trade.hex` ya tiene el tamaño que necesita, pero no se ha probado el cambio de programa dentro del bitstream.

## Pendientes generales

- **Colaboradores.** Falta el usuario de GitHub de Santiago Muñoz y el de quien deba revisar la entrega.
- **Preguntas al ayudante.** Siguen abiertas las diez. Las que más pesan ahora: si las series ocultas salen del mismo generador, cuántos ticks dura cada ronda, si la maestra usa el timing del testbench y si la placa parte encendida antes del primer precio (define si se pierde alguno).
- **Verificación formal.** `formal/` sigue vacía.

## Qué conviene atacar después y por qué

1. **Frente A, guardia de régimen y tope de pérdida.** Es el hallazgo más caro: sin reversión la regla base puede perder casi todo. El protocolo ya mide exactamente eso, y la guardia tiene que mejorar `tendencia` y `cambio_de_caracter` sin tocar los bloques ni los remuestreos.
2. **Frente A, identificar el generador.** Calibrar `dos_componentes` contra la serie de práctica y separar el efecto del redondeo. Con el modelo se puede calcular la política óptima y se obtienen series fuera de muestra que sí se parecen a la real.
3. **Frente A, límite de 63 acciones.** Entrar en 6 ticks cuesta comisiones y precio. Conviene evaluar entradas escalonadas y si vale la pena operar con menos que todo el patrimonio.
4. **Frente B, Espino segmentado.** La traza de `tb/tb_cpi.sv`, el generador de programas aleatorios y el gemelo ya están listos para la ejecución en paralelo contra el original. Tiene que estar antes del 18/11 para llegar a la maestra.
5. **Frente E, `icebram` y matriz de estrés.** Con el gemelo la matriz de períodos, tiempos de SPI, comisión y caja es cuestión de minutos.

## Tramo 1: repositorio, flujo completo y mediciones de partida (12/11 y 13/11)

### Qué quedó hecho

- Repositorio privado `nicolasaraneda/Proyecto4_Arquitectura_De_Computadores`, con el repositorio base del curso importado sin cambios (etiqueta `base-curso`) y la estructura `rtl/`, `sw/`, `tb/`, `ref/`, `tools/`, `formal/`, `docs/`, `informe/`.
- Los cuatro archivos entregados quedaron en su lugar: `docs/Proyecto_4_arq.pdf`, `tb/tb_proyecto_4.sv`, `tb/practica.csv` y `ref/p4_baseline.py`. Ninguno se modificó.
- Ensamblador `tools/pochoasm.py`: es el del Proyecto 2 con el nombre que pide el testbench. 73 tests pasan.
- `sw/trade.s` trivial (comprar y mantener) y `Makefile` con todo el flujo: ensamblar, testbench oficial, copias parametrizadas del testbench, CPI, síntesis, place and route y bitstream.
- Power-on reset largo traído del Proyecto 2 (`PorBits = 12`).
- Scripts de medición: `tools/medir_base.sh` y `ref/hallazgos.py`.
- Integración continua en GitHub Actions: tests del ensamblador, `trade.hex` al día, testbench oficial, CPI y síntesis hasta el bitstream. La primera corrida en GitHub terminó en verde.
- `main` protegido en GitHub: exige que el chequeo `verificar` de la integración continua haya pasado, y no admite `push --force` ni borrar la rama. El dueño del repositorio puede empujar directo. Los demás integrantes entran por pull request desde una rama.
- `Vcalderone` invitado como colaborador con permiso de escritura.
- `README.md`, `docs/decisiones.md` y `docs/ensamblador.md`.

### Qué se midió

Testbench oficial sin modificar, con el `trade.s` trivial:

| Período | Ticks | Resultado | Peor caso | Presupuesto |
|---------|-------|-----------|-----------|-------------|
| 0,1 ms (por defecto) | 2000 | 4/4 | 18 ciclos | 2 262 |
| 1 ms (copia parametrizada) | 20 | 4/4 | 18 ciclos | 24 762 |
| 10 ms (copia parametrizada) | 5 | 4/4 | 18 ciclos | 249 762 |

Con 2000 ticks a 0,1 ms el patrimonio final es 6 845 con 2 órdenes (comprar y mantener según el testbench: 6 695). El `decisiones.csv` se comparó fila por fila con el mercado de `ref/p4_baseline.py`: cero diferencias en 2000 filas (hecho con el reset original; con el reset largo cambia solo el tick en que aparece la primera orden).

Repositorio base (`make medir-base`, resultado en `docs/mediciones/base.txt`):

| Medición | Valor medido | Valor que teníamos anotado |
|----------|--------------|----------------------------|
| Celdas lógicas | 1065 de 1280 (83 %) | 1080 (84 %) |
| BRAM | 12 de 16 | 12 de 16 |
| Frecuencia máxima, 10 semillas | 42,7 a 47,1 MHz, mediana 44,1 | cerca de 43 MHz |
| Shifter completo | 1491 celdas (116 %), no cabe | 1479 (115 %) |
| PLL en el VQ100 | nextpnr falla: "PLL 'u_pll' couldn't be placed anywhere, no suitable BEL found" | el mismo error |
| CPI | 2 ciclos por instrucción, más 1 por load y 1 por salto tomado. Medido en simulación con tres programas: el modelo coincide con diferencia de 0 ciclos | el mismo modelo, por lectura del RTL |

Diseño actual (repositorio base más reset largo): 1083 celdas, 12 BRAM, 44,0 MHz con la semilla por defecto.

Serie de práctica (`make hallazgos`):

| Hallazgo | Valor medido | Coincide |
|----------|--------------|----------|
| VR(10), VR(50), VR(100) | 0,77, 0,62 y 0,53 | sí |
| Reversión en los 20 bloques de 1000 ticks | VR menor que 1 en 20 de 20, para los tres horizontes | sí |
| Autocorrelación de los cambios | -0,112 en el rezago 1, dentro del ruido desde el rezago 3 | sí |
| Regla base (media exponencial, alfa 1/32, entra 4, sale 0) | 27 062 con 388 órdenes. Bloques: media 11 069, peor 9 720, supera a comprar y mantener en 9 de 10 | sí |
| Suma móvil de 64, entra 4, sale 1 | 24 143. Bloques: media 10 951, peor 10 148 | sí |
| Comprar y mantener | 6 497. Media por bloque 9 746 | sí |
| Seguir tendencia, 336 configuraciones | mediana 5 566, solo 10 de 336 terminan sobre 10 000 | no: teníamos 3 853 |

### Diferencias con lo que teníamos anotado

1. **Versión de Yosys.** La instalada es 0.68+195 (OSS CAD Suite del 2026-09-06), no 0.70. Con ella el repositorio base da 1065 celdas en vez de 1080 y el shifter 1491 en vez de 1479. Las conclusiones no cambian: quedan unas 200 celdas libres y el shifter completo no cabe.
2. **El conteo de celdas tiene ruido.** El mismo diseño dio entre 1063 y 1075 celdas según detalles del flujo que no cambian la lógica. Una diferencia menor que unas 10 celdas no se puede atribuir a un cambio con una sola síntesis (decisión T6).
3. **Barrido de seguir tendencia.** La grilla de 336 configuraciones original no estaba en ningún script. Con la grilla que definimos en `ref/hallazgos.py` la mediana es 5 566 y no 3 853. La conclusión es la misma: seguir tendencia pierde.
4. **Intentos anteriores sin código.** Perceptrón en línea, población de 120 traders y comité por votación no se pudieron reproducir porque su código no está en el repositorio. Hay que rehacerlos en el frente del algoritmo.
5. **Costo de la regla base (unas 30 instrucciones, 70 ciclos).** Sin medir todavía, porque `trade.s` es el trivial.
6. **CPI del enunciado.** La tabla del enunciado supone CPI = 2,35. Los programas medidos dan entre 2,50 y 2,67, porque tienen muchos saltos tomados y loads.
7. **Reset largo y primeros precios.** Con el reset del Proyecto 2, en el testbench el programa no ve los precios de los ticks 0 y 1 a 0,1 ms, ni el del tick 0 a 1 ms y 10 ms (medido). El testbench entrega 4/4 de todas formas. En la competencia no pasa, porque la placa está encendida antes del primer precio (decisión T3).
8. **Puntaje de la competencia.** El enunciado dice que depende del patrimonio final respecto a comprar y mantener y de la posición relativa entre los grupos. Lo teníamos resumido solo como lineal entre el peor y el mejor grupo.

Nada de lo encontrado contradice al enunciado ni al testbench.

### Observaciones para lo que viene

- **La simulación con Icarus es lenta.** 2000 ticks a 0,1 ms demoran 76 segundos. Una ronda de 2000 ticks a 10 ms demoraría cerca de dos horas. Para las rondas 1 y 2 completas hace falta Verilator o el gemelo digital.
- **`trade.hex` no rellena las 512 palabras.** Las palabras que no están en el archivo quedan indefinidas en simulación y en cero en la placa. Un programa que lea memoria sin haberla escrito se comportaría distinto en los dos lados. Conviene que el ensamblador rellene hasta 512 palabras, que además es lo que necesita `icebram`.
- **Posible sobreajuste de la regla base.** En la grilla de 336 configuraciones de reversión, la mediana es 11 204 y el máximo 27 226. La regla base (27 062) está casi en el máximo de la grilla, así que sus parámetros ya están elegidos mirando la serie completa. El protocolo por bloques y con remuestreo tiene que partir de ahí.
- **`tb/tb_cpi.sv` mira señales internas del Espino base.** Cuando el core se segmente hay que actualizar esas rutas o sacar una señal de instrucción completada.

### Qué falta del tramo 1

- **Equivalencia y verificación formal en la integración continua.** Todavía no existen. Se agregan al flujo cuando estén `make equiv` y las pruebas de `formal/`.
- **Colaboradores.** Falta el usuario de GitHub de Santiago Muñoz y el de quien deba revisar la entrega.
- **Definición de Ops/s y roofline vista en clases.** No está en el repositorio. Hace falta la diapositiva para el frente del co-diseño.

### Qué conviene atacar después y por qué

1. **Regla base en `trade.s` con equivalencia exacta (`make equiv`).** Es el entregable del día 2 y la base de todo lo demás: fija la referencia `ref/trader.py`, obliga a resolver el desplazamiento sin shifter y entrega el primer bitstream de competencia.
2. **Gemelo digital o Verilator.** Sin simulación rápida no se pueden correr las rondas de 10 ms ni la matriz de estrés. Destraba los frentes A, D y E.
3. **Relleno de `trade.hex` a 512 palabras y prueba de `icebram`.** Es barato y elimina una diferencia entre simulación y placa.
4. **Preguntas al ayudante.** Sobre todo las que cambian el diseño: si el periférico estimador cumple las reglas, si las series ocultas salen del mismo generador, cuántos ticks dura cada ronda y si la maestra usa el timing del testbench.
