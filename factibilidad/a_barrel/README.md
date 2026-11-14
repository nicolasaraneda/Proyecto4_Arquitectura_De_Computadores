# Pieza A: Espino multihilo tipo barrel

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz. Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Prototipo de factibilidad. Nada de esta carpeta está integrado en `rtl/`, en el `Makefile` de la raíz ni en la integración continua. Todos los números de este documento salen de un script de esta carpeta y su salida está guardada en `mediciones/`. Al final está el comando de cada uno.

El documento tiene dos partes. La primera construyó y midió el prototipo. La segunda (sección 6) es una verificación independiente: se intentó romper el core, se repitieron las mediciones de la primera parte y se dejó escrito hasta dónde está verificado. No se encontró ningún error en el barrel y el RTL no cambió entre las dos partes. La segunda parte se hizo en dos sesiones: la primera dejó la comparación contra el Espino base y los controles negativos, y la segunda volvió a correr todo, cerró las propiedades formales, el período de 10 ms y el cambio de programa con `icebram` (secciones 6.11 y 6.12).

## 1. Resumen

Se construyó un Espino con cuatro hilos que rotan por un pipeline uniforme de cuatro etapas (búsqueda, registros, ejecución, memoria y escritura). Los cuatro contextos viven en las mismas BRAM del banco de registros. No tiene adelantamiento, ni burbujas, ni instrucciones que se anulen. El SoC completo, con el esclavo SPI y los periféricos, pasa el testbench oficial sin modificar con 4/4 y decide igual que el Espino base.

| Medición | Espino base | Pipeline de 3 etapas | Barrel de 4 hilos |
|----------|-------------|----------------------|-------------------|
| Celdas lógicas, de 1280 | 1083 | 994 | 934 |
| Celdas libres | 197 | 286 | 346 |
| LUT4 | 906 | 802 | 762 |
| BRAM, de 16 | 12 | 12 | 12 |
| Frecuencia máxima en 10 semillas: mínima, mediana, máxima (MHz) | 42,43, 43,74 y 45,08 | 51,13, 53,50 y 54,50 | 52,66, 55,52 y 57,05 |
| Semillas que cierran a 25 MHz | 10 de 10 | 10 de 10 | 10 de 10 |
| CPI con el mix de la clase 7 | 2,350 | 1,350 | 1,000 agregado, 4,000 por hilo |
| MIPS a 25 MHz con el mix | 10,64 | 18,52 | 25,00 agregado, 6,25 por hilo |
| Ppeak (definición de la clase 7) | 12,5 MOPS | 25 MOPS | 25 MOPS con 4 hilos, 6,25 con 1 |
| Regla base, respuesta: ciclos promedio y peor caso del testbench | 41,0 y 44 | 22,0 y 26 | 75,1 y 83 |
| Regla base, peor caso barriendo la fase del sondeo | 49 | 27 | 88 (3,9 % de los 2262 ciclos de la ronda 3) |
| Testbench oficial sin modificar | 4/4 | 4/4 (ya medido en el frente B) | 4/4, `decisiones.csv` idéntico al del base |
| Cada hilo contra el Espino base, instrucción por instrucción | | | 8 727 624 instrucciones de programa, 3 327 672 distintas, cero diferencias |
| Errores puestos a propósito que la comparación detecta | | | 21 de 21 |
| Propiedades formales de estructura (SymbiYosys) | | | 24 afirmaciones probadas para cualquier programa, 9 de 9 errores puestos a propósito con contraejemplo |
| Cambio de programa con `icebram` | | | Funciona: el `.bin` cambiado es idéntico al sintetizado directamente |
| Regla base en cada uno de los 4 hilos, 20 000 ticks | | | Idéntica a `ref/trader.py` en los 4 |
| Regla base en el hilo 0, 20 000 ticks a 0,1 ms, 1 ms y 10 ms | | | Idéntica a `ref/trader.py` en los tres períodos (a 0,1 ms también con Icarus) |

Veredicto según los criterios de corte: **cabe junto al SPI y cierra a 25 MHz en las 10 semillas, así que no se descarta de la edición de competencia**. Queda como candidata. La verificación a fondo, que era la primera condición, ya está hecha y no encontró errores (sección 6). Quedan dos condiciones que este tramo no resuelve: pasar por la maestra real el 26/11 y que el fondo de estrategias (piezas B y C) gane algo en los estudios de retorno. Con una sola estrategia el barrel no cambia el patrimonio y responde más lento que los otros dos cores. El detalle está en la sección 11.

## 2. Qué hay en esta carpeta

| Archivo | Qué es |
|---------|--------|
| `rtl/espino_barrel_core.v` | El core. Instancia sin modificar `espino_decoder.v`, `espino_alu.v` y `espino_load_store_unit.v` de `rtl/espino_core/`. |
| `rtl/espino_barrel_regfile.v` | El banco de registros del Espino con la dirección ampliada a `{hilo, registro}`. |
| `rtl/pochoco_soc.v` | Copia de `rtl/pochoco_soc.v` que instancia el core barrel. Mismo nombre de módulo, mismos puertos, `MemFile`, `u_spi`, `u_ram` y `u_periph`. Los cambios están listados en su encabezado. |
| `sw/hilos_distintos.s` | Cuatro hilos independientes: suma, Fibonacci, accesos a memoria de todos los tamaños, y subrutinas con comparaciones. |
| `sw/cooperacion.s` | Tres hilos publican un valor en memoria compartida y el hilo 0 los junta y escribe display y LEDs. Es la forma mínima de "un gestor por hilo". |
| `sw/mix_clase7_x4.s` | El lazo de `sw/mix_clase7.s` en los cuatro hilos, cada uno con sus datos. |
| `sw/hilo_mmio.s` | Prueba de la alternativa de arranque sin tabla (sección 3.5). |
| `tools/tabla.py` | Antepone la tabla de arranque a un programa de un hilo, sin tocarlo. Así corren `sw/trade.s`, `sw/mix_clase7.s`, `sw/hazard_test.s` y `sw/hazard_review.s` del repositorio. |
| `tb/tb_barrel.sv` | Testbench funcional: resultados, conteo de instrucciones y ciclos por hilo, trazas por hilo y monitor de valores desconocidos. |
| `tb/tb_barrel_ticks.sv` | Adaptación de `tb/tb_cpi.sv`: mediciones por tick con la maestra SPI. |
| `tb/tb_netlist.sv`, `tb/tb_chip.sv` | Simulan la netlist de Yosys y el bitstream (desde el `.asc`) por los pines. |
| `tb/boot_hilo.v` | Hace partir al Espino base en la entrada de un hilo, para comparar trazas. |
| `tools/*.sh`, `tools/informe_recursos.py`, `Makefile` | Scripts de medición. |
| `mediciones/` | Salidas guardadas de cada script. |

Agregados de la verificación (sección 6):

| Archivo | Qué es |
|---------|--------|
| `tb/tb_verif.sv` | El barrel y cuatro SoC originales con el Espino base, uno por hilo. Compara cada instrucción completada de cada hilo. |
| `tb/tb_pines.sv` | Traza de los pines con una maestra SPI, para comparar el RTL con la netlist. |
| `tools/prog_hilos.py` | Generador de programas aleatorios de cuatro hilos: zonas de datos separadas, zona compartida, un solo hilo con el SPI, o `sw/trade.s` en un hilo y los otros tres al azar. |
| `tools/verif.sh`, `tools/resumen_verif.py` | La campaña de comparación y su resumen con el conteo por hilo. |
| `tools/mutar.py`, `tools/mutaciones.sh` | Controles negativos: 18 errores en copias del RTL más los 3 que el core ya traía bajo `ifdef`. |
| `tools/verif_trazas.sh` | Trazas en modo funcional con Icarus y los testbenches del repositorio. |
| `tools/verif_spi.sh` | `sw/trade.s` en cada hilo con la maestra del testbench oficial. |
| `tools/netlist_aleatorio.sh` | Netlist contra RTL en los pines, con programas aleatorios. |
| `tools/sin_tabla.sh` | Qué pasa si se carga un programa sin la tabla de arranque. |
| `formal/propiedades.vh`, `formal/regfile_abstracto.v`, `formal/regfile_espia.v`, `tools/formal.sh` | Propiedades formales de estructura y los dos modelos del banco de registros con que se prueban. |
| `tools/icebram_prueba.sh` | Cambio del programa dentro del bitstream con `icebram`, simulado desde el `.asc`. |
| `AVANCE.md` | Bitácora de trabajo de la segunda parte. |

No se modificó ningún archivo versionado del repositorio. `rtl/pochoco_ram.v`, `rtl/pochoco_spi_slave.v`, `rtl/pochoco_periph.v`, el testbench oficial, `tb/tb_cpi.sv`, `tb/core_trace_tb.v`, `tb/comparar_trazas.py`, `tools/pochoasm.py` y `tools/medir_variante.sh` se usan tal como están.

## 3. El diseño

### 3.1 Las cuatro etapas

| Etapa | Qué hace |
|-------|----------|
| F, búsqueda | El contador de programa del hilo direcciona la memoria de instrucciones. |
| R, registros | La instrucción sale de la BRAM. Se decodifica y sus `rs1` y `rs2` direccionan el banco con `{hilo, registro}`. |
| X, ejecución | ALU, comparación del salto, próximo contador de programa y petición al bus de datos. |
| M, memoria y escritura | Llega el dato del load, se alinea y se escribe el registro destino en `{hilo, rd}`. |

En cada ciclo hay una instrucción de cada hilo en cada etapa. Un contador de 2 bits (`tid_f`) dice qué hilo está en F, y los de las otras etapas son ese valor menos 1, 2 y 3. El número de hilo no viaja con la instrucción. El contador de programa sí: hay un anillo de cuatro registros de 10 bits, uno por etapa.

### 3.2 Diagrama ciclo a ciclo

```
ciclo      1   2   3   4   5   6   7   8
hilo 0     F   R   X   M   F   R   X   M     instrucción i en los ciclos 1 a 4, la i+1 en 5 a 8
hilo 1     M   F   R   X   M   F   R   X
hilo 2     X   M   F   R   X   M   F   R
hilo 3     R   X   M   F   R   X   M   F
```

Cada hilo completa una instrucción cada 4 ciclos, sea de ALU, load, store o salto, tomado o no. El core completa una por ciclo.

### 3.3 Qué ocurre en cada flanco

Todo el diseño usa el flanco de subida. No hay BRAM con reloj invertido ni flip-flops de flanco de bajada (`mediciones/recursos.txt`, sección 5), así que no hay rutas de medio ciclo como en el pipeline de 3 etapas.

| Flanco que cierra la etapa | Qué se registra |
|----------------------------|-----------------|
| F | La BRAM de instrucciones lee la palabra del contador de programa. Su registro de salida es el registro entre F y R. El anillo de contadores avanza una posición. |
| R | La BRAM del banco lee `{hilo, rs1}` y `{hilo, rs2}`. Su registro de salida es el registro entre R y X. Se registran la decodificación y la instrucción. |
| X | Si es un store, se escribe la memoria o el periférico. Si es un load, la memoria o el periférico registran el dato. Aquí ocurren los efectos sobre el esclavo SPI: leer `PRICE` baja la bandera y escribir `DECISION` cambia el byte de salida. Se registran el resultado de la ALU o el enlace, los dos bits bajos de la dirección y el próximo contador de programa del hilo. |
| M | Se escribe el banco en `{hilo, rd}`, con el resultado o con el dato del load ya alineado. El próximo contador de programa pasa a la etapa F. |

Las tres memorias del SoC son BRAM con lectura registrada, y en este pipeline cada una cae justo en una frontera de etapa. Por eso el barrel es más chico que el pipeline de 3 etapas: no necesita el multiplexor de adelantamiento, ni la copia de la memoria para leer en el flanco de bajada, ni la lógica que detiene el core durante un load.

### 3.4 Por qué no hay riesgos de datos ni de control

Para un mismo hilo, la instrucción i ocupa los ciclos 1 a 4 y la i+1 los ciclos 5 a 8.

- **Registros.** La instrucción i escribe el banco en el flanco que cierra el ciclo 4. La i+1 lo lee en el flanco que cierra el ciclo 6. La BRAM ya tiene el dato, con un ciclo de sobra. No hace falta adelantamiento.
- **Load seguido de uso.** El dato del load se escribe en ese mismo flanco del ciclo 4. No hace falta detener nada.
- **Memoria.** El store de i se escribe al cerrar el ciclo 3 y un load de i+1 se pide al cerrar el ciclo 7.
- **Saltos.** El próximo contador de programa se calcula en el ciclo 3 y se usa para buscar en el ciclo 5. Nunca se busca una instrucción antes de que la anterior del mismo hilo haya resuelto su salto, así que ninguna instrucción buscada se descarta.
- **Efectos en el SPI.** Como no hay instrucciones especulativas, una lectura de `PRICE` o una escritura de `DECISION` que llega a la etapa X siempre es de verdad.
- **Entre hilos.** Los registros no se comparten: cada hilo tiene su contexto. Lo que se comparte es la memoria y los periféricos (sección 3.6).

Sobra un ciclo: el banco se podría escribir un flanco más tarde, y el próximo contador de programa se calcula en el ciclo 3 pero recién se necesita al terminar el ciclo 4, así que su cálculo se podría repartir entre X y M. No se usó porque la ruta crítica mide 19,0 ns de los 40 disponibles.

### 3.5 Cómo arrancan los hilos

El hilo t parte en la dirección 4 t. Todo programa empieza con una tabla de cuatro saltos:

```
    j    hilo0        # dirección 0
    j    hilo1        # dirección 4
    j    hilo2        # dirección 8
    j    hilo3        # dirección 12
```

El pipeline sale del reset como si tuviera burbujas en R y en X: instrucciones que no escriben, no piden el bus y no saltan. La primera instrucción del hilo t llega a ejecución en el ciclo 3 + t después del reset (medido por `tb/tb_barrel.sv`).

En hardware la tabla no cuesta nada, porque son los valores de reset del anillo de contadores. En software cuesta 4 palabras y una instrucción por hilo. `tools/tabla.py` la antepone a un programa de un solo hilo sin tocarlo, y los hilos que no se usan quedan en un lazo vacío.

Alternativas evaluadas:

| Alternativa | Costo en celdas | Costo en el programa | Estado |
|-------------|-----------------|----------------------|--------|
| Tabla de cuatro saltos (la elegida) | 0 | 4 palabras, 1 instrucción por hilo | Construida y medida |
| Registro `HILO` por MMIO (`0x8000_000C`, entrega el número del hilo que lo lee) y los cuatro hilos partiendo en 0 | +5 (939 contra 934, dentro del ruido) | 5 instrucciones comunes más una tabla de saltos: 6 instrucciones por hilo antes de separarse | Construida y medida (`-DBARREL_MMIO_HILO -DBARREL_BOOT_PASO=0`, `sw/hilo_mmio.s`) |
| Número de hilo en un registro de cada contexto, puesto en el contenido inicial de la BRAM del banco | 0 (estimado) | 0 (estimado) | No se construyó |

Se eligió la tabla. El registro `HILO` hace lo mismo con más instrucciones, y lo único que agrega (que un código compartido sepa en qué hilo corre) se consigue sin hardware poniendo una constante en un registro en la entrada de cada hilo. La tercera alternativa rompe la comparación con el Espino base, que parte con todos los registros en cero, y depende de que la BRAM conserve su contenido inicial.

### 3.6 Cómo comparten memoria y periféricos

- Hay un solo bus de datos y una sola instrucción en la etapa X por ciclo. Cada load y cada store es atómico.
- Leer, modificar y escribir son tres instrucciones, y entre ellas corren los otros hilos (12 ciclos). No hay instrucciones atómicas de lectura y escritura. La regla de uso que aplica `sw/cooperacion.s` es que cada palabra compartida tiene un solo hilo que la escribe.
- Una palabra se escribe completa en un flanco. Un valor y su número de tick empaquetados en una palabra se publican de forma atómica.
- Los periféricos y el esclavo SPI no saben de hilos. El que lee `PRICE` baja la bandera para todos. En el esquema del gestor por hilo, solo el hilo supervisor toca el SPI.
- El código es reentrante: cuatro hilos pueden ejecutar la misma subrutina, cada uno con sus registros (`sw/mix_clase7_x4.s`).

Nota para la pieza B: el orden relativo entre hilos está fijo ciclo a ciclo, así que el hardware es determinista. Aun así conviene que el supervisor espere a que cada estrategia publique el resultado del tick en curso (con el número de tick en la misma palabra). Así la decisión no depende de cuántas instrucciones demora cada estrategia y la referencia en Python no tiene que modelar ciclos.

### 3.7 Lecturas y escrituras simultáneas en las BRAM

| Memoria | Qué puede coincidir en un flanco | Qué pasa |
|---------|----------------------------------|----------|
| Banco de registros | La lectura del hilo que está en R y la escritura del hilo que está en M | Son hilos distintos, así que las direcciones `{hilo, registro}` nunca coinciden. No hay colisión por construcción. |
| Memoria, puerto de datos | En un store se lee y se escribe la misma palabra | El dato leído se descarta: un store no escribe el banco. |
| Memoria, puerto de instrucciones contra puerto de datos | Un hilo busca la palabra que otro hilo está escribiendo en ese mismo flanco | Solo ocurre con código que se modifica a sí mismo. El Verilog dice que se lee el dato viejo, y Yosys agrega lógica para garantizarlo en la BRAM (sección 7). |

### 3.8 Qué se reutiliza del Espino y qué cambia

Sin modificar: `espino_decoder.v`, `espino_alu.v` y `espino_load_store_unit.v`. La unidad de carga y almacenamiento se instancia dos veces: una arma la petición en X y la otra alinea el dato en M. Su máquina de espera no se usa. Los multiplexores de operandos, el destino del salto y el enlace son los de `espino_id_stage.v`, copiados. El SoC es el mismo: memoria, esclavo SPI, periféricos, mapa de memoria y multiplexor de lectura.

Diferencias de comportamiento con el Espino base:

1. Cada hilo, por separado, hace lo mismo que el Espino base partiendo en su entrada. Se comprobó con trazas en modo funcional (sección 5.6) y después instrucción por instrucción con programas aleatorios (sección 6).
2. El contador de programa tiene 11 bits, igual que en el pipeline de 3 etapas (T36). Con 32 bits el barrel ocupa 1131 celdas y sigue cabiendo.
3. El programa empieza con la tabla de arranque.
4. Los ciclos: 4 por instrucción y por hilo.

### 3.9 Las notas de diseño de partida, validadas o corregidas

| Nota | Resultado |
|------|-----------|
| La instrucción i ocupa F1 R2 X3 M4 y la i+1 busca en el ciclo 5. No hacen falta adelantamiento, burbujas ni anulación. | Validada. Las únicas burbujas son las dos del arranque. |
| Hay holgura para registrar la dirección de memoria o el dato del load. | Validada, y no hizo falta usarla. |
| El contador de programa y el número de hilo viajan con la instrucción. | El contador sí. El número de hilo no hace falta que viaje: basta un contador de 2 bits. |
| Los contextos caben en las BRAM del banco, 64 de 256 palabras. | Validada. Cero BRAM adicionales. |
| Arranque en 4 t con una tabla de saltos. | Validada y elegida. La alternativa por MMIO se midió y es peor. |
| Decidir en qué flanco se presenta cada dirección. | Todo en el flanco de subida. No hace falta el de bajada. |
| Reutilizar decodificador, ALU y unidad de carga sin cambios. | Validada. |

## 4. Mediciones de recursos y de timing

`nextpnr-ice40 --hx1k --package vq100 --freq 25`, `goboard.pcf`, semillas 1 a 10, con `tools/medir_variante.sh` del repositorio. Los tres cores se midieron en la misma corrida (`mediciones/recursos.txt`). Es el SoC completo: core, memoria, esclavo SPI, periféricos y contador de reset.

| Variante | Celdas | Libres | LUT4 | BRAM | Fmax mínima | Mediana | Máxima | Cierran a 25 MHz |
|----------|--------|--------|------|------|-------------|---------|--------|------------------|
| Espino base | 1083 | 197 | 906 | 12 | 42,43 | 43,74 | 45,08 | 10 de 10 |
| Pipeline de 3 etapas | 994 | 286 | 802 | 12 | 51,13 | 53,50 | 54,50 | 10 de 10 |
| Barrel de 4 hilos | 934 | 346 | 762 | 12 | 52,66 | 55,52 | 57,05 | 10 de 10 |

Los números del base y del segmentado coinciden con los anotados en `docs/estado.md`. El barrel ocupa 149 celdas menos que el base y 60 menos que el segmentado, con las mismas 12 BRAM. El período mínimo en la peor semilla es 19,0 ns de 40.

El conteo y la frecuencia de una semilla se mueven con detalles que no alteran la lógica. El mismo diseño con la semilla 1 dio 934 celdas y 53,59 MHz en `make recursos`, y 933 celdas y 59,18 MHz en `make bitstream`, donde lo único distinto es el orden en que se leen los fuentes. Es el ruido que describe T6, y por eso el cierre de timing se declara con las 10 semillas.

### 4.1 Dónde están las celdas

Síntesis con las fronteras del SoC conservadas (`mediciones/desglose.txt`):

| Módulo | Base: LUT4 y FF | Segmentado: LUT4 y FF | Barrel: LUT4 y FF |
|--------|-----------------|-----------------------|-------------------|
| Core | 748 y 67 | 689 y 130 | 577 y 158 |
| Memoria (`pochoco_ram`) | 89 y 117 | 47 y 81 | 89 y 117 |
| Esclavo SPI | 38 y 52 | 38 y 52 | 38 y 52 |
| Periféricos | 26 y 16 | 26 y 16 | 26 y 16 |
| `pochoco_soc`: reset, selección y multiplexor de lectura | 101 y 14 | 101 y 14 | 101 y 14 |

El core barrel tiene más flip-flops (los registros de etapa y el anillo de contadores) y menos LUT (sin ciclo de espera, sin adelantamiento, contador de 11 bits). De los bloques reutilizados, sintetizados por separado, la ALU son 255 LUT4, el decodificador 94 y cada unidad de carga 118. Lo propio del barrel (registros de etapa, anillo y multiplexores) son 159 LUT4 y 150 flip-flops.

Las 89 LUT4 y 117 flip-flops de `pochoco_ram` no son memoria: son la lógica con que Yosys emula la lectura durante la escritura (sección 7).

### 4.2 Ruta crítica

Semilla más lenta del barrel (semilla 4, 18,99 ns, `mediciones/ruta_critica.txt`): salida de la BRAM del banco de registros, multiplexor de operandos, sumador de la ALU (30 bits de acarreo, 4,76 ns), multiplexor del resultado, decodificación de la dirección (`spi_sel`, `per_sel`) y habilitación del registro de lectura de los periféricos. Son 8,31 ns de lógica y 10,68 ns de ruteo.

Es la misma ruta que limita al pipeline de 3 etapas (19,56 ns), sin el multiplexor de adelantamiento. En el base la ruta crítica (23,57 ns) parte en la memoria de instrucciones y pasa por la decodificación.

## 5. Mediciones de desempeño y pruebas

### 5.1 CPI, MIPS y Ppeak

Con el lazo de 20 instrucciones de `sw/mix_clase7.s` (20 % de loads y 15 % de saltos tomados), los tres cores en la misma corrida (`mediciones/cpi.txt`):

| | Base | Segmentado | Barrel, 4 hilos | Barrel, 1 hilo activo | Clase 7, estimado para 3 etapas |
|-|------|------------|-----------------|-----------------------|-------------------------------|
| IC en 46 000 ciclos | 19 575 | 34 077 | 46 000 | 11 500 | |
| CPI con el mix | 2,350 | 1,350 | 1,000 | 4,000 | 1,5 |
| MIPS a 25 MHz | 10,64 | 18,52 | 25,00 | 6,25 | 16,7 |
| Speedup contra el base | 1 | 1,74 | 2,35 | 0,59 | 1,57 |
| Ciclos de ALU, load y salto tomado | 2, 3 y 3 | 1, 2 y 2 | 1, 1 y 1 | 4, 4 y 4 | 1, 2 y 3 |

Por hilo, con los cuatro activos: 11 500 instrucciones en 46 000 ciclos cada uno, CPI 4,000 y 6,25 MIPS. El testbench comprueba el modelo de costo: una instrucción completada por ciclo en total y una cada 4 ciclos en cada hilo, de cualquier clase.

Ppeak con la definición de la clase 7 (f por instrucciones por ciclo por operaciones por instrucción por núcleos):

- Espino base: 25 MHz × 0,5 × 1 = 12,5 MOPS.
- Pipeline de 3 etapas: 25 MHz × 1 × 1 = 25 MOPS, solo con instrucciones de ALU. Con el mix rinde 18,52.
- Barrel con 4 hilos: 25 MHz × 0,25 × 1 × 4 = 25 MOPS, con cualquier mix. Medido: 25,00.
- Barrel con 1 hilo: 25 MHz × 0,25 × 1 × 1 = 6,25 MOPS. Medido: 6,25.

El barrel no sube el techo del segmentado. Lo alcanza con cualquier mezcla de instrucciones, siempre que los cuatro hilos tengan trabajo. En términos de la ley de hierro, IC y Tclk no cambian y el CPI agregado baja a 1. Con un solo hilo activo el CPI útil es 4 y el barrel rinde menos que el Espino base.

### 5.2 Latencia de la regla base

`sw/trade.s` sin modificar, con la tabla de arranque: la regla base corre en el hilo 0 y los otros tres hilos giran en un lazo vacío. 200 ticks de la serie de práctica con el timing del testbench oficial (`mediciones/ticks.txt`):

| Core | Respuesta: IC | Ciclos promedio | Peor caso | Tick completo: ciclos promedio | Peor caso |
|------|---------------|-----------------|-----------|--------------------------------|-----------|
| Espino base | 19,51 | 41,02 | 44 | 63,02 | 66 |
| Pipeline de 3 etapas | 19,22 | 22,03 | 26 | 34,03 | 38 |
| Barrel, hilo 0 | 19,02 | 75,06 | 83 | 115,06 | 123 |

Barriendo la fase del lazo de sondeo (12 corridas, el inicio se corre un ciclo cada vez), el peor caso es 49, 27 y 88 ciclos. El lazo de sondeo del barrel dura 12 ciclos.

| Core | Peor caso | Ronda 1 (249 762 ciclos) | Ronda 2 (24 762) | Ronda 3 (2 262) |
|------|-----------|--------------------------|------------------|-----------------|
| Espino base | 49 | 0,020 % | 0,198 % | 2,166 % |
| Pipeline de 3 etapas | 27 | 0,011 % | 0,109 % | 1,194 % |
| Barrel | 88 | 0,035 % | 0,355 % | 3,890 % |

El barrel responde 1,83 veces más lento que el base y 3,41 veces más lento que el segmentado. Sigue lejos del plazo: en la ronda 3 quedan 2174 ciclos libres por tick, unas 543 instrucciones por hilo antes de pasarse.

### 5.3 Testbench oficial sin modificar

`tb/tb_proyecto_4.sv` tal como está en el repositorio, compilado contra la copia del SoC de esta carpeta, con `vvp` corriendo dentro de la carpeta de build (`mediciones/oficial.txt`):

- Los cuatro chequeos pasan: MISO sin X, el programa escribe `DECISION`, lee todos los precios y la decisión llega antes del siguiente tick. **4/4**.
- Peor caso de precio a decisión: 83 ciclos de 2262.
- `decisiones.csv` es idéntico byte a byte al del Espino base con `sw/trade.hex` (2001 líneas, mismo sha256). Patrimonio final 9617 en los dos.

### 5.4 Equivalencia con la referencia en la serie completa

Copia parametrizada del testbench oficial con Verilator, como `tools/equiv.sh` (`mediciones/equiv_ref.txt`):

| Período | Ticks | Resultado | Peor caso | Patrimonio |
|---------|-------|-----------|-----------|------------|
| 0,1 ms | 20 000 | 4/4, 20 000 filas idénticas a `ref/trader.py` | 83 ciclos | 26 795 |
| 1 ms | 20 000 | 4/4, 20 000 filas idénticas a `ref/trader.py` | 87 ciclos | 27 306 |
| 10 ms | 20 000 | 4/4, 20 000 filas idénticas a `ref/trader.py` | 87 ciclos | 27 306 |

Son los mismos patrimonios del base y del segmentado. La fila de 10 ms se agregó en la segunda parte (`make equiv-ronda1`, 22 minutos de simulación).

La corrida de 0,1 ms se repitió además con Icarus Verilog, el simulador del encabezado del testbench oficial (`mediciones/equiv_icarus.txt`, `make equiv-icarus`, 14 minutos): 4/4, 20 000 filas idénticas a `ref/trader.py`, peor caso 83 ciclos y patrimonio 26 795. Icarus simula con cuatro estados, así que el chequeo de MISO sin valores X vale para la serie completa.

### 5.5 Netlist y bitstream

- La netlist de Yosys del SoC barrel, simulada con los modelos de las primitivas del iCE40, termina `cooperacion` y `hazard_test` (en el hilo 2) con los LEDs y el display esperados. Lo mismo con la memoria sin emulación de lectura durante escritura (`mediciones/netlist.txt`, 4 de 4).
- Dos bitstreams construidos con la semilla 1 (933 celdas, 59,18 MHz) y simulados desde el `.asc` (`mediciones/bitstream.txt`): `barrel_cooperacion.bin` deja los LEDs en 1111 y el display en "60" a los 12 000 ciclos, y `barrel_trade.bin`, simulado por los pines con la maestra del testbench, decide igual que `ref/trader.py` en 500 ticks.

### 5.6 Pruebas de humo

`mediciones/humo.txt`. No es la verificación a fondo, que está en la sección 6.

| Prueba | Qué compara | Resultado |
|--------|-------------|-----------|
| `hilos_distintos` | 11 palabras de memoria contra valores esperados, y la traza de cada hilo contra la del Espino base corriendo el mismo programa desde la entrada de ese hilo (`tb/core_trace_tb.v` y `tb/comparar_trazas.py --modo funcional`, sin modificar) | Pasa. Escrituras al banco iguales por hilo: 204, 125, 20 y 141. Accesos al bus: 2, 2, 17 y 5. |
| `cooperacion` | LEDs 1111 y display "60" | Pasa |
| `mix_clase7_x4` | Modelo de costo y traza de cada hilo contra el base | Pasa. 1191 escrituras y 509 accesos iguales en cada hilo. |
| `hazard_test` y `hazard_review` del Proyecto 3, sin modificar, en cada uno de los cuatro hilos | El programa se revisa a sí mismo (LEDs 1111), su traza con las salidas contra la del base, y los hilos ociosos no hacen nada | Pasa en los 4 hilos. `hazard_test`: 348 escrituras, 63 accesos y 2 salidas. `hazard_review`: 271, 66 y 2. |
| `hilo_mmio` | La alternativa de arranque. Control: sin el registro la prueba falla. | Pasa |
| Controles negativos | Tres errores puestos a propósito bajo `ifdef`: escribir en el contexto de otro hilo, alinear el load con la dirección de otro hilo, y no anular la burbuja del arranque | Los tres detectados |

En todas las corridas el monitor no encontró ningún valor desconocido en una escritura al banco ni en un acceso al bus.

## 6. Verificación independiente

Segunda parte del trabajo. El encargo fue intentar romper el barrel y dejar medido hasta dónde está verificado. Resultado: **no se encontró ningún error en el core y el RTL no cambió**. Lo que sí apareció son dos debilidades del método de programas aleatorios, que se corrigieron en el generador del prototipo y que también afectan al generador del repositorio (sección 6.8).

| Prueba | Qué compara | Resultado | Salida |
|--------|-------------|-----------|--------|
| Cada hilo contra el Espino base, instrucción por instrucción (Verilator) | Contador de programa, instrucción, escritura al banco, acceso al bus, los 16 registros del contexto y la palabra o el registro escrito | 8 727 624 instrucciones de programa, 3 327 672 distintas, en 748 corridas. Cero diferencias | `mediciones/verificacion.txt` |
| Lo mismo con el contador de programa de 32 bits | Incluye lo que el programa hace fuera de la memoria | 1 095 021 instrucciones en 200 corridas. Cero diferencias | `mediciones/verificacion.txt` |
| Controles negativos | 21 errores puestos a propósito | 21 de 21 detectados, cada uno por las 5 comparaciones | `mediciones/mutaciones.txt` |
| Trazas en modo funcional (Icarus, testbenches del repositorio sin modificar) | Secuencias de escrituras al banco, accesos al bus y salidas de cada hilo | 417 582 escrituras y 169 663 accesos iguales en 60 corridas. Ningún valor X | `mediciones/trazas.txt` |
| `sw/trade.s` en cada hilo con la maestra del testbench oficial | `decisiones.csv` contra `ref/trader.py` | 4 hilos por 20 000 ticks, idénticos. 8 casos de 5000 ticks con los otros tres hilos ocupados, idénticos | `mediciones/spi_hilos.txt` |
| Netlist sintetizada contra RTL | Los pines, ciclo a ciclo, con programas aleatorios y tráfico SPI | 7327 eventos idénticos en 8 programas | `mediciones/netlist_aleatorio.txt` |
| Programa sin tabla de arranque | Modo de falla | Falla, como se esperaba: 2/4 y no opera | `mediciones/sin_tabla.txt` |
| Propiedades formales (SymbiYosys, inducción) | Aislamiento de contextos, x0, burbujas, rotación de hilos, contador de programa de cada hilo y arranque, para cualquier programa | 24 afirmaciones probadas. 9 de 9 errores puestos a propósito entregan contraejemplo | `mediciones/formal.txt` |
| Cambio de programa con `icebram` | El bitstream cambiado contra el sintetizado directamente, y simulado desde el `.asc` | Idéntico (mismo sha256) y decide igual que la referencia | `mediciones/icebram.txt` |

### 6.1 Repaso del razonamiento de la sección 3.4

Se leyó el RTL completo del prototipo y el del Espino base buscando casos que el razonamiento no cubriera. Para cada riesgo se anota por qué no ocurre y qué prueba lo fallaría si ocurriera.

| Riesgo | Por qué no ocurre | Qué lo detectaría |
|--------|-------------------|-------------------|
| Leer y escribir la BRAM del banco en el mismo flanco desde hilos distintos | La lectura usa `{tid_r, rs}` y la escritura `{tid_m, rd}`. `tid_r` es `tid_f - 1` y `tid_m` es `tid_f - 3`: siempre difieren en 2, así que las dos direcciones nunca coinciden | El contexto completo de 16 registros se compara después de cada instrucción. Mutaciones `ctx_escritura`, `ctx_lectura_rs1`, `ctx_lectura_rs2`, `escritura_sin_hilo` y `rd_otro_hilo` |
| Leer un registro antes de que la instrucción anterior del mismo hilo lo escriba | La escritura es al cerrar el ciclo 4 y la lectura siguiente al cerrar el ciclo 6 | Lo mismo. Los programas aleatorios usan en casi todas las instrucciones el registro que escribió la anterior |
| Contador de programa siguiente | Se calcula en X y entra a F dos flancos después, siempre del mismo hilo. El anillo tiene un registro por etapa | Contador de programa e instrucción de cada instrucción completada. Mutaciones `pc_otro_hilo`, `enlace_otro_hilo` y `jalr_no_salta` |
| Cargas | El dato se registra al cerrar X y se alinea en M con el tamaño, el signo y los dos bits bajos de la dirección que se guardaron al pedirlo. El hilo que viene detrás recién cambia esos registros en el flanco en que este escribe | Valor escrito por cada load. Mutaciones `desplazamiento_load`, `signo_load` y `tamano_store` |
| Accesos al SPI y a los periféricos intercalados entre hilos | Hay una sola instrucción en X por ciclo. El multiplexor de lectura (memoria, SPI o periféricos) lo elige un registro que se carga con el propio load. No hay instrucciones especulativas, así que una lectura de `PRICE` baja la bandera una sola vez | Grupos B, C y T de la sección 6.3 y `mediciones/spi_hilos.txt`. Mutaciones `mux_lectura` y `peticion_bus` |
| Escribir x0 | La escritura se anula si el registro destino es 0, y cada contexto parte en cero desde el contenido inicial de la BRAM | Se exige x0 igual a cero después de cada instrucción. Mutación `x0` |
| Reset y arranque | Las dos burbujas no escriben, no piden el bus y no saltan, y dejan a cada hilo en su entrada | La primera instrucción comparada de cada hilo tiene que estar en 4 t. El testbench exige que solo haya burbujas en los ciclos 1 y 2. Mutaciones `burbuja_salta`, `hilo_desfasado` y `MUTA_ARRANQUE` |
| Memoria compartida entre hilos | Cada load y cada store ocurre completo en un flanco, y los accesos de los cuatro hilos quedan en un orden fijo: uno por ciclo, por turnos | Grupo D: cuatro Espino base por turnos con las escrituras copiadas entre ellos. El control N comprueba que esos programas de verdad interactúan |

Observaciones del repaso, ninguna es un error:

1. El registro que elige el multiplexor de lectura (`rd_is_per`, `rd_is_spi` en `rtl/pochoco_soc.v`) solo se carga cuando hay un load. En el barrel esa condición sobra, porque el registro se usa en el ciclo siguiente y solo si ese ciclo es la etapa M de un load. Por lectura del RTL, quitarla no cambiaría el comportamiento. No se probó ni se midió cuántas celdas ahorra.
2. Hay dos casos en que el barrel no hace lo mismo que el Espino base, los dos conocidos y fuera de lo que usa `trade.s`. Uno es el contador de programa de 11 bits: si un programa salta fuera de las 512 palabras, `auipc` y el enlace de `jal` entregan el contador recortado (es la misma diferencia de T36 para el pipeline de 3 etapas). El otro es el código que se modifica a sí mismo: un store sobre una palabra que otro hilo está buscando se ve en un ciclo distinto que en el base.
3. Un programa sin la tabla de arranque no funciona (sección 6.6).

### 6.2 Cómo se compara cada hilo con el Espino base

`tb/tb_verif.sv` es el método de `tb/tb_paralelo.sv` del repositorio llevado a cuatro hilos. Instancia cinco SoC completos con el mismo programa: el barrel y cuatro `pochoco_soc` originales (`rtl/`, sin modificar) con el Espino base, uno por hilo, cada uno partiendo en la entrada de su hilo. La instrucción número k del hilo t del barrel se compara con la instrucción número k de su Espino base:

- contador de programa e instrucción;
- escritura al banco de registros: registro y valor;
- acceso al bus de datos: lectura o escritura, dirección, bytes habilitados y dato;
- los 16 registros del contexto después de la instrucción, leídos de las BRAM del banco (las dos copias);
- en un store a memoria, la palabra recién escrita, leída de la memoria;
- en un store al SPI o a los periféricos, el registro escrito (`DECISION`, display o LEDs).

Al final se compara la memoria completa. El número de hilo de cada etapa lo calcula el testbench con el número de ciclo, y se exige que coincida con el del core.

Hay dos referencias. Si lo que hace un hilo no depende de los otros (un hilo con los demás ociosos, o cuatro hilos con zonas de datos separadas), cada Espino base corre solo: es la comparación "cada hilo idéntico a su corrida en el core base". Si los hilos comparten memoria, los cuatro Espino base ejecutan por turnos, una instrucción cada uno, y cada store de uno se copia a la memoria de los otros tres. En el barrel los accesos al bus ocurren en ese mismo orden.

El bus SPI queda quieto, porque un precio que llega por los pines cae en ciclos distintos en cada SoC. Para ejercitar igual el esclavo, el testbench deja un precio nuevo en `PRICE` y levanta la bandera de `STATUS` entre la misma pareja de instrucciones en el barrel y en el Espino base. El tráfico SPI real por los pines se prueba aparte (sección 6.5).

### 6.3 Resultados por grupo de corridas

`mediciones/verificacion.txt`. Se cuentan solo instrucciones de programa: las de un hilo que gira en un lazo vacío (un `jal` a sí mismo) también se comparan, pero se informan aparte. "Distintas" cuenta una sola vez las instrucciones de una corrida que tienen el mismo contador de programa, el mismo valor escrito y el mismo acceso al bus: mide cuánto de lo comparado no es repetición de la misma vuelta del programa.

| Grupo | Qué corre | Corridas | Hilo 0 | Hilo 1 | Hilo 2 | Hilo 3 | Total | Distintas |
|-------|-----------|----------|--------|--------|--------|--------|-------|-----------|
| A | Un hilo con un programa de `tools/prog_aleatorio.py` (el generador del repositorio, 300 instrucciones) y los otros tres ociosos. Con SPI, periféricos y precios nuevos | 200 | 235 762 | 235 762 | 247 623 | 241 574 | 960 721 | 130 771 |
| U | Lo mismo con el generador del prototipo (`tools/prog_hilos.py --modo uno`) | 200 | 300 000 | 300 000 | 300 000 | 300 000 | 1 200 000 | 599 696 |
| H | `sw/hazard_test.s` y `sw/hazard_review.s` en cada hilo | 8 | 834 | 834 | 834 | 834 | 3 336 | 3 336 |
| B | Los cuatro hilos a la vez, programas distintos, zonas de datos separadas, los cuatro con accesos al SPI y a los periféricos | 100 | 500 000 | 500 000 | 500 000 | 500 000 | 2 000 000 | 758 051 |
| C | Los cuatro a la vez, uno solo con el SPI y con un precio nuevo cada 29 instrucciones | 100 | 500 000 | 500 000 | 500 000 | 500 000 | 2 000 000 | 782 019 |
| T | `sw/trade.s` en un hilo, con un precio nuevo cada 61 instrucciones, y los otros tres con programas al azar | 40 | 200 000 | 200 000 | 200 000 | 200 000 | 800 000 | 270 834 |
| D | Los cuatro a la vez sobre la misma zona de datos, con saltos que pueden caer en el código de otro hilo | 100 | 440 897 | 440 892 | 440 889 | 440 889 | 1 763 567 | 782 965 |
| **Total** | | **748** | **2 177 493** | **2 177 488** | **2 189 346** | **2 183 297** | **8 727 624** | **3 327 672** |
| W | Los programas de A con el barrel compilado con contador de 32 bits | 200 | 276 588 | 265 007 | 276 868 | 276 558 | 1 095 021 | 138 066 |

Del total, 6 320 734 instrucciones escriben un registro, 1 336 290 son loads, 1 098 908 son stores, 1 327 280 son saltos y 680 876 acceden al SPI o a los periféricos (463 220 al SPI). Aparte se compararon 7 297 683 instrucciones de lazo vacío.

- Grupo A: 32 de las 200 corridas terminan antes, porque el programa sale de la memoria (un `jalr` con una base cualquiera) y ahí el contador de 11 bits del barrel deja de coincidir con el de 32 del base. El grupo W corre los mismos programas con el contador de 32 bits y compara también lo que pasa fuera.
- Grupo D: 12 de las 100 corridas terminan antes por la misma razón.
- Grupo N, el control: 10 programas del grupo D comparados con la referencia de hilos aislados. Fallan los 10, como debe ser. Si pasaran, los hilos del grupo D no estarían interactuando.
- En los grupos A, U, C y T el testbench puso 44 840 precios nuevos y los hilos leyeron `STATUS` con la bandera arriba 12 900 veces.

Las simulaciones de toda la campaña demoran 39 segundos con 5 procesos. A eso se suma compilar el testbench con Verilator.

### 6.4 Trazas en modo funcional

`mediciones/trazas.txt`. Es el método de `make riesgos` del repositorio con sus piezas sin modificar: `tb/core_trace_tb.v` escribe la traza del Espino base y `tb/comparar_trazas.py --modo funcional` compara las secuencias de eventos sin mirar el ciclo. La traza del barrel, una por hilo, la escribe `tb/tb_barrel.sv`. Corre con Icarus, que simula con cuatro estados, así que además se cuentan los valores desconocidos que llegan al banco o al bus, cosa que Verilator no ve.

Con 12 semillas (48 corridas de un hilo activo y 12 con los cuatro a la vez, 6000 instrucciones por hilo en cada una):

| Hilo | Escrituras al banco iguales | Accesos al bus iguales |
|------|-----------------------------|------------------------|
| 0 | 103 945 | 42 938 |
| 1 | 105 248 | 43 163 |
| 2 | 103 230 | 41 045 |
| 3 | 105 159 | 42 517 |
| Total | 417 582 | 169 663 |

Además, 1760 cambios de LEDs y display iguales, ningún valor X usado, y en las 60 corridas se cumple el modelo de costo (una instrucción por ciclo en total y una cada 4 ciclos por hilo).

### 6.5 La regla base en cada hilo, con precios por los pines

`mediciones/spi_hilos.txt`. Copia parametrizada del testbench oficial (como `tools/equiv.sh`), con Verilator, período de la ronda 3.

| Caso | Ticks | Resultado | Peor caso |
|------|-------|-----------|-----------|
| `sw/trade.s` en el hilo 0, los otros tres ociosos | 20 000 | 4/4, idéntico a `ref/trader.py`, patrimonio 26 795 | 83 ciclos |
| En el hilo 1 | 20 000 | 4/4, idéntico, 26 795 | 84 |
| En el hilo 2 | 20 000 | 4/4, idéntico, 26 795 | 85 |
| En el hilo 3 | 20 000 | 4/4, idéntico, 26 795 | 86 |
| `sw/trade.s` en cada hilo, con los otros tres corriendo programas al azar que leen y escriben memoria y periféricos (2 programas por hilo, 8 casos) | 5 000 | 4/4 e idéntico a la referencia en los 8 | 83 a 86, el mismo de cada hilo |

El peor caso sube un ciclo por hilo porque el hilo t pasa por la etapa X un ciclo después que el t - 1. No cambia cuando los otros hilos están ocupados: el tiempo de un hilo no depende de lo que hagan los demás. Es el caso de uso del fondo de estrategias, con un hilo que atiende a la maestra mientras los otros calculan.

### 6.6 Netlist contra RTL y programa sin tabla

**Netlist** (`mediciones/netlist_aleatorio.txt`). `tb/tb_pines.sv` anota con su número de ciclo cada cambio de LEDs y display y cada byte que una maestra SPI recibe, y se exige que la traza de la netlist de Yosys sea idéntica byte a byte a la del RTL. Con 8 programas aleatorios de cuatro hilos (4 con zonas separadas y 4 con zona compartida), 34 000 ciclos cada uno y un byte por SPI cada 287 a 350 ciclos: 7327 eventos idénticos y ningún X en los pines. Complementa a `make netlist`, que corre dos programas que se revisan a sí mismos.

**Programa sin tabla** (`mediciones/sin_tabla.txt`). `sw/trade.hex`, el programa del Espino base, cargado tal cual en el barrel: los hilos 1, 2 y 3 parten en la segunda, tercera y cuarta instrucción. El testbench entrega 2/4, el programa no escribe `DECISION` y el patrimonio queda en 10 000. No es un error del core, pero es un riesgo de operación: `tools/retune.py`, `icebram` y cualquier flujo que regenere el programa tienen que anteponer la tabla, y en la placa la falla es silenciosa.

### 6.7 Controles negativos

`mediciones/mutaciones.txt`. Cada mutación es un reemplazo de texto en una copia de los tres archivos del prototipo (`tools/mutar.py`; el RTL no se toca), más las tres que el core ya traía bajo `ifdef`. Con cada barrel mutado se corren cinco comparaciones cortas, una por grupo (A, H, B, C y D). Sin mutación pasan las cinco.

| Mutación | Qué rompe | Detectada por | Instrucción del hilo en que aparece la diferencia |
|----------|-----------|---------------|---------------------------------------------------|
| `ctx_escritura` | El resultado se escribe en el contexto del hilo que está en X | 5 de 5 | 2 |
| `ctx_lectura_rs1` | rs1 se lee del contexto del hilo que está en F | 5 de 5 | 6 a 8 |
| `ctx_lectura_rs2` | rs2 se lee del contexto del hilo que está en X | 5 de 5 | 10 a 24 |
| `escritura_sin_hilo` | La escritura al banco ignora el número de hilo | 5 de 5 | 2 |
| `pc_otro_hilo` | El hilo que entra a F busca con el contador de otro hilo | 5 de 5 | 1 |
| `enlace_otro_hilo` | El enlace de `jal` y `jalr` guarda el contador de otro hilo | 5 de 5 | 27 a 223 |
| `x0` | Se permite escribir x0 | 5 de 5 | 1 |
| `rd_otro_hilo` | El registro destino sale de la instrucción de otro hilo | 5 de 5 | 2 |
| `be_ram` | Los bytes habilitados llegan rotados a la memoria | 5 de 5 | 23 a 239 |
| `tamano_store` | El tamaño del store sale de la instrucción de otro hilo | 5 de 5 | 20 a 101 |
| `desplazamiento_load` | El load se alinea con la dirección de otro hilo | 5 de 5 | 24 a 107 |
| `signo_load` | El signo del load sale de la instrucción de otro hilo | 5 de 5 | 36 a 136 |
| `mux_lectura` | El multiplexor de lectura elige con la dirección de otro hilo | 5 de 5 | 22 a 191 |
| `peticion_bus` | La petición al bus sale un ciclo antes, con otro hilo | 5 de 5 | 20 a 78 |
| `burbuja_salta` | La burbuja del arranque ejecuta un salto | 5 de 5 | 1 |
| `hilo_desfasado` | El contador de hilos sale del reset en 1 | 5 de 5 | Ciclo 1 |
| `jalr_no_salta` | `jalr` no salta | 5 de 5 | 43 a 224 |
| `dato_store` | El dato del store sale de rs1 | 5 de 5 | 23 a 78 |
| `MUTA_CONTEXTO` | El resultado se escribe en el contexto de otro hilo (`ifdef` de la primera parte) | 5 de 5 | 2 |
| `MUTA_BOFF` | El load se alinea con la dirección de otro hilo (`ifdef`) | 5 de 5 | 24 a 107 |
| `MUTA_ARRANQUE` | Las burbujas del arranque no se anulan (`ifdef`) | 5 de 5 | 1 |

**21 de 21 detectadas**, cada una por las cinco comparaciones. La última columna es la menor y la mayor instrucción en que aparece la diferencia entre las cinco comparaciones. La más tardía aparece en la instrucción 239.

### 6.8 Lo que se encontró en el método

Ninguno de los dos hallazgos es un error del barrel. Los dos afectan también a `tools/prog_aleatorio.py`, el generador con que se verificó el pipeline de 3 etapas.

1. **Los programas aleatorios se quedan quietos.** El cuerpo se repite para siempre, y después de un par de vueltas los registros llegan a un punto fijo: las vueltas siguientes escriben los mismos valores. En el grupo A, que usa el generador del repositorio, de 960 721 instrucciones comparadas solo 130 771 son distintas. En `tools/prog_hilos.py` se reservaron dos registros (x11 y x12) que avanzan con una recurrencia de sumas al comienzo de cada vuelta y se mezclan en los demás. Con eso las distintas pasaron a ser entre un tercio y la mitad (599 696 de 1 200 000 en el grupo U). Para el frente B, la consecuencia es que las 1 300 756 instrucciones de `make paralelo-largo` valen bastante menos de lo que dice el número, y conviene llevar este cambio al generador del repositorio.
2. **Un `jalr` puede salir con una base cualquiera.** En el generador del repositorio un salto puede caer justo en un `jalr` sin pasar por el `auipc` que le prepara la base. Con un hilo no importa. Con cuatro, el hilo cae en el código de otro, lee su zona de datos o el SPI, y ya no se puede comparar con un Espino base que corre solo. Quedó medido en dos grupos aparte de `mediciones/verificacion.txt`: con el `jalr` libre (grupo J), 4 de 100 programas de cuatro hilos difieren de la referencia de hilos aislados, y esos mismos 100 programas pasan todos con la referencia de memoria compartida (grupo K, 1 763 563 instrucciones más, que no se sumaron al total). O sea que la diferencia es del método de comparación y no del barrel. En `tools/prog_hilos.py` ningún salto cae en un `jalr`, salvo en el modo compartido, donde se deja a propósito.

Además, el testbench tenía un defecto propio: con memoria compartida se quedaba esperando si un hilo salía de la memoria. Se corrigió (la corrida termina ahí).

### 6.9 Lo que no está cubierto

- **La placa y la maestra real.** Todo lo anterior es simulación.
- **Prueba formal de lo que calcula cada instrucción.** Las propiedades de la sección 6.11 son de estructura: prueban que los hilos no se pisan y que el arranque es el correcto, no que un `add` sume. Eso sigue apoyado en la simulación contra el Espino base. No se corrió riscv-formal ni una equivalencia formal contra el Espino base.
- **El gemelo digital** no modela el barrel, así que no hay cosimulación ciclo a ciclo contra él.
- **Cuatro hilos accediendo al SPI mientras llegan precios por los pines**, comparados contra el base. Ahí lo que ve cada hilo depende de cuál leyó `PRICE` primero y no hay un Espino base de referencia. Se cubre de otras tres formas: con el bus quieto (grupo B), con un solo hilo en el SPI (grupos C y T, y la sección 6.5) y en la comparación de netlist contra RTL, donde los cuatro hilos sí leen el SPI con tráfico.
- **Código que se modifica a sí mismo** y programas que escriben sobre el código de otro hilo. Ningún programa de prueba lo hace.
- **Fuera de la memoria con el contador de 11 bits.** Se compara solo con el de 32 (grupo W).
- **La alternativa de arranque con el registro `HILO`** solo tiene la prueba de humo.
- **El bitstream.** La comparación con programas aleatorios llega hasta la netlist de Yosys. Después de nextpnr solo están las dos simulaciones de `make bitstream` y las dos de `make icebram`.
- **Instrucciones ilegales.** Los programas de prueba solo traen instrucciones válidas. El decodificador es el mismo módulo en los dos cores y ninguno usa su salida `illegal_insn_o`, pero no hay una corrida que lo compruebe.
- **El kit de contingencia contra el barrel.** `tools/retune.py` todavía no existe en el repositorio. Cuando se escriba tiene que anteponer la tabla de arranque y correr su equivalencia rápida contra este core. El cambio de programa con `icebram` sí quedó probado (sección 6.12).
- **Versión de 2 hilos:** no se hizo.

### 6.10 Mediciones de la primera parte, repetidas

Se volvieron a correr `make recursos`, `make humo`, `make cpi`, `make ticks`, `make oficial` y `make netlist`, y la corrida de 20 000 ticks a 0,1 ms y a 1 ms de `make equiv`. Las salidas nuevas son idénticas línea a línea a las del informe anterior (las copias quedaron en `build/previas/` para compararlas). Coinciden entonces todos los números clave:

| Número | Informe anterior | Repetido |
|--------|------------------|----------|
| Celdas, LUT4 y BRAM del SoC barrel | 934, 762 y 12 | 934, 762 y 12 |
| Frecuencia máxima en 10 semillas: mínima, mediana y máxima | 52,66, 55,52 y 57,05 MHz, 10 de 10 | 52,66, 55,52 y 57,05 MHz, 10 de 10 |
| Base y segmentado en la misma corrida | 1083 y 994 celdas | 1083 y 994 celdas |
| CPI con el mix de la clase 7 | 1,000 agregado y 4,000 por hilo | 1,000 y 4,000 |
| Respuesta de la regla base en el hilo 0 | 75,06 ciclos promedio, 83 peor caso, 88 barriendo la fase | 75,06, 83 y 88 |
| Testbench oficial sin modificar | 4/4, `decisiones.csv` idéntico al del base | 4/4, idéntico (mismo sha256) |
| 20 000 ticks contra `ref/trader.py` | Idénticos a 0,1 ms y a 1 ms | Idénticos a 0,1 ms, a 1 ms y, nuevo, a 10 ms |
| Pruebas de humo | 34 PASS y 0 FAIL, 3 de 3 mutaciones | 34 PASS y 0 FAIL, 3 de 3 |

Como el RTL no cambió, las mediciones de recursos y de frecuencia de la sección 4 siguen vigentes.

En la segunda sesión se volvió a correr todo otra vez, incluida la campaña de la sección 6 (`make verif`, `make mutaciones`, `make trazas`, `make spi`, `make netlist-aleatorio`, `make sin-tabla`) y `make recursos` con sus 10 semillas por variante, y cada salida se comparó con la guardada: cero líneas distintas en todas, sin contar la línea del tiempo de simulación.

### 6.11 Propiedades formales

`mediciones/formal.txt`, con SymbiYosys y boolector. `tools/formal.sh` inserta las propiedades de `formal/propiedades.vh` en una copia del core (el RTL del prototipo no se toca) y las prueba con el decodificador, la ALU y la unidad de carga del repositorio. Quedan libres la instrucción que entrega la memoria, el dato del bus y el contenido del banco de registros, así que lo probado vale para cualquier programa y cualquier contenido de memoria.

| Propiedad | Qué afirma | Cómo se prueba |
|-----------|------------|----------------|
| P1 | El hilo que lee el banco (etapa R) nunca es el que lo escribe (etapa M): no hay lectura y escritura de la misma dirección en un flanco | Inducción |
| P2 | x0 no se escribe nunca | Inducción |
| P3 | Una burbuja no pide el bus, no salta y no escribe el banco | Inducción |
| P4 | No hay escritura al bus sin petición | Inducción |
| P5 | Los hilos rotan: en la etapa X hay un hilo distinto en cada ciclo, en orden | Inducción |
| P6 | La instrucción que escribe el banco es la que estuvo en X en el ciclo anterior, y escribe en el contexto de ese hilo | Inducción |
| P7 | Después de las dos burbujas del arranque no vuelve a haber burbujas | Inducción |
| P8 | El contador de programa que entra a F es el que calculó ese mismo hilo dos ciclos antes, en X | Inducción |
| P9 | Arranque: el hilo t busca su primera instrucción en 4 t en el ciclo t + 1 y la ejecuta en el ciclo t + 3. Antes de eso en X solo hay burbujas | Acotada, 12 ciclos desde el reset |
| P10 | Los operandos que llegan a X se leyeron del contexto del hilo que está en X y de los registros rs1 y rs2 de su instrucción | Inducción, con un banco que devuelve las direcciones que vio |
| P11 | Lo que el banco escribió es el registro destino de la instrucción que estuvo en X dos ciclos antes, en el contexto de ese hilo, y solo si esa instrucción escribía y su destino no era x0 | Inducción, con el mismo banco |

Son 24 afirmaciones en tres tareas, y las tres pasan. Una cuarta tarea de cobertura comprueba que la prueba no es vacía: existe una ejecución que llega al ciclo 6 con una escritura al banco. Toda la corrida demora 10 segundos.

Controles negativos: las mismas tareas sobre 9 de las mutaciones de `tools/mutar.py`. Las 9 hacen fallar alguna tarea con un contraejemplo desde el reset. `ctx_lectura_rs1`, `ctx_lectura_rs2` y `ctx_escritura` solo las detecta la tarea del banco que devuelve direcciones, que es la razón de tener P10 y P11: las otras propiedades miran señales del core y no lo que de verdad llega a los puertos del banco.

Un detalle del método que conviene recordar para el formal del resto del proyecto. Con profundidad de inducción 6 el control `ctx_escritura` no entregaba contraejemplo: el caso base no alcanzaba a llegar a la primera escritura al banco (ciclo 5 desde el reset), solo fallaba el paso inductivo, y SymbiYosys responde UNKNOWN en vez de FAIL. Con profundidad 10 sí hay contraejemplo. El script ahora distingue los dos casos y no cuenta un UNKNOWN como detección.

Qué no prueba: que cada instrucción calcule lo que debe, que la BRAM del banco devuelva lo último que se escribió en cada dirección (el banco está abstraído), ni nada del SoC (multiplexor de lectura, memoria, esclavo SPI). Todo eso se apoya en la comparación contra el Espino base de las secciones 6.2 a 6.5.

### 6.12 Cambio de programa con icebram

`mediciones/icebram.txt`. Se construyó un bitstream molde con la memoria llena de un patrón al azar (`icebram -g`) y después se reemplazó el patrón por el programa, sin volver a sintetizar ni a rutear:

| Programa puesto con `icebram` | Demora de `icebram` más `icepack` | Resultado |
|-------------------------------|-----------------------------------|-----------|
| `sw/trade.s` con la tabla de arranque | 0,07 s | El `.asc` es idéntico al que sale de sintetizar con ese programa, y el `.bin` tiene el mismo sha256 que `barrel_trade.bin` de `make bitstream`. Simulado desde el `.asc` por los pines: 500 ticks idénticos a `ref/trader.py` |
| `sw/cooperacion.s` | 0,07 s | Mismo sha256 que `barrel_cooperacion.bin`. Simulado desde el `.asc`: LEDs 1111 y display "60" |

Funciona, y el contenido de la memoria no cambia la colocación: el molde da las mismas 933 celdas y 59,18 MHz que los bitstreams de la sección 5.5. Dos condiciones: el programa nuevo tiene que traer las 512 palabras (el script lo completa con ceros) y la tabla de arranque. El molde se construye una sola vez y hay que guardarlo junto con su archivo de patrón.

## 7. Qué habría que sacrificar para que quepa

Nada: cabe con 346 celdas y 4 BRAM libres. Como encima van la extensión de la ISA y el vigilante, se midió igual cuánto se puede recuperar o cuánto cuesta cada cosa, siempre con las 10 semillas cerrando a 25 MHz (`mediciones/recursos.txt`, secciones 2 y 3):

| Cambio sobre el barrel | Celdas | Diferencia | Libres |
|------------------------|--------|------------|--------|
| Barrel (referencia) | 934 | | 346 |
| Memoria sin emulación de lectura durante escritura | 794 | -140 | 486 |
| Sin `pochoco_periph` (LEDs, display e interruptores) | 895 | -39 | 385 |
| Contador de reset de 4 bits en vez de 12 | 920 | -14 | 360 |
| Registro `HILO` y arranque común | 939 | +5 | 341 |
| Contador de programa de 32 bits en vez de 11 | 1131 | +197 | 149 |

No se midió una versión de 2 hilos, porque la de 4 cabe.

**La emulación de lectura durante escritura.** `pochoco_ram` lee y escribe el mismo arreglo en el mismo flanco. El Verilog dice que la lectura entrega el dato viejo, la BRAM del iCE40 no lo garantiza, y Yosys agrega registros y multiplexores para emularlo. Con el atributo `(* no_rw_check *)` en el arreglo no los agrega. Es el mayor recorte disponible y sirve para los tres cores:

| Core | Celdas | Sin emulación | Recupera | Fmax mínima sin emulación |
|------|--------|---------------|----------|---------------------------|
| Espino base | 1083 | 916 | 167 | 45,41 |
| Pipeline de 3 etapas | 994 | 884 | 110 | 51,52 |
| Barrel | 934 | 794 | 140 | 54,02 |

No está aplicado en el prototipo. Cambia lo que pasa en la placa en un solo caso: buscar la palabra de memoria que se está escribiendo en ese mismo flanco, o sea código que se modifica a sí mismo. En un store el puerto de datos también lee la palabra que escribe, pero ese dato se descarta. `trade.s` no modifica su código. La netlist sin emulación pasa `cooperacion` y `hazard_test`, pero el modelo de simulación de la BRAM no reproduce lo que hace el silicio en una colisión, así que la simulación no prueba ese caso. Aplicarlo es una decisión aparte, porque toca `rtl/pochoco_ram.v`, que comparten los tres cores.

## 8. Días de trabajo para calidad de competencia

Estimación, para una persona, contando solo el core y no las piezas B, C y D.

| Tarea | Días |
|-------|------|
| Verificación a fondo: hecha en este tramo (sección 6). Falta llevarla a `main`: objetivos en el `Makefile` de la raíz, una corrida corta en la integración continua y el generador nuevo en `tools/` | 0,5 |
| Gemelo digital: cuatro contextos y tabla de ciclos del barrel en `ref/gemelo/gemelo.c`, rehacer el atajo del sondeo, cosimulación ciclo a ciclo contra el RTL | 1,5 |
| Formal: las propiedades de estructura ya están (sección 6.11). Falta llevarlas a `formal/` y a la integración continua. riscv-formal o una equivalencia contra el Espino base quedan fuera de esta cuenta | 0,5 |
| Integración: variante del core elegible al compilar en `rtl/`, adaptar `tb/tb_cpi.sv`, mediciones por tick, equivalencia, simulación del bitstream e integración continua | 1 |
| `trade.s` multihilo con su referencia y equivalencia bit a bit (si solo corre la regla base en un hilo son 0,5 días: ya pasa) | 2 |
| Documento de estudio, diagramas y preguntas de defensa | 1 |
| Bitstream con hash, prueba en la placa y entrada en el checklist del 26/11. Incluye que el kit de contingencia (`tools/retune.py`, cuando exista) anteponga la tabla de arranque | 0,5 |
| **Total** | **7** (5,5 con la regla base en un solo hilo) |

La primera parte estimó 9 días, 2 de ellos de verificación. Esos 2 se gastaron en este tramo, junto con la mitad del día de formal, y queda 1 día para llevar las dos cosas a `main`. Del 14/11 al 25/11 hay 12 días de calendario, que se reparten con las demás piezas.

## 9. Reglas del enunciado

| Regla | Cumple | Comentario |
|-------|--------|------------|
| "La decisión se debe calcularla en el Espino Core en la placa. El core debe leer el precio y escribir la decisión; el hardware agregado puede acelerar partes del algoritmo, pero no reemplazar al procesador en el ciclo de decisión." | Sí | El barrel es el procesador, no un acelerador. Un hilo lee `PRICE` y escribe `DECISION` con instrucciones de la ISA. No hay lógica fuera del core que decida. |
| "Pueden modificar libremente el RTL, siempre que el procesador siga siendo Espino." | Sí, con una duda | La ISA, el decodificador, la ALU, la unidad de carga y el bus son los del Espino, sin modificar. Cambia la microarquitectura, igual que en el pipeline de 3 etapas. La duda es si un Espino con cuatro contextos sigue contando como Espino para quien evalúa. |
| "Todo hardware agregado debe estar en el repositorio con su testbench." | Sí | `tb/tb_barrel.sv`, `tb/tb_barrel_ticks.sv`, `tb/tb_netlist.sv` y `tb/tb_chip.sv`. |
| "Deben usar el mismo programa para todas las series de tiempo." | Sí | Un solo programa y un solo bitstream para las tres rondas. |
| "No se puede usar información externa a la serie recibida por SPI ni almacenar series de precios en el diseño distintas de la que se está stremeando." | Sí | El core no guarda nada de la serie. |
| El testbench oficial no se modifica y entra por jerarquía a `dut.u_spi.*` | Sí | Compila y entrega 4/4 sin tocarlo. |

Preguntas para el ayudante:

1. Si un Espino multihilo (cuatro contextos sobre el mismo decodificador y la misma ALU, misma ISA) cumple "siempre que el procesador siga siendo Espino".
2. Si varias estrategias corriendo en hilos del mismo core, con un hilo que lee el precio y escribe la decisión, cumple "el core debe leer el precio y escribir la decisión".
3. Cómo se informan el CPI y las mediciones por tick del punto 3.2 en un core multihilo: por hilo (4,0) o agregado (1,0).

## 10. Riesgos

1. **No se ha probado en la placa ni con la maestra real.** Solo puede ir en el bitstream de competencia si pasa el 26/11.
2. **Que cada instrucción calcula lo que debe está comprobado solo por simulación.** Son 8,7 millones de instrucciones comparadas contra el Espino base y 21 controles negativos. La prueba formal cubre la estructura (que los hilos no se pisan y el arranque), no la función, y no hay cosimulación con el gemelo. Lo que no está cubierto está listado en la sección 6.9.
3. **El gemelo digital no modela el barrel.** Mientras no lo haga, el protocolo no puede correr el binario y las equivalencias largas dependen de Verilator.
4. **El software concurrente es más difícil que el hardware.** El core no tiene riesgos entre instrucciones, pero un programa con cuatro hilos sí puede tener carreras sobre la memoria compartida. No hay instrucciones atómicas de lectura y escritura.
5. **Un hilo ocioso desperdicia su turno.** Con menos de cuatro hilos con trabajo el barrel rinde menos que el segmentado, y con uno solo, menos que el base.
6. **La latencia por hilo se multiplica por 4.** La regla base responde en 88 ciclos en el peor caso. Un algoritmo de más de unas 540 instrucciones por tick en un hilo no cabe en la ronda 3.
7. **Las herramientas del repositorio suponen un solo hilo** (`tb/tb_cpi.sv`, mediciones por tick, ejecución en paralelo, mutaciones). Hay que adaptarlas. La ejecución en paralelo y las mutaciones para cuatro hilos ya existen en esta carpeta.
8. **La pregunta 1 al ayudante.** Si la respuesta es no, la pieza pasa a exhibición.
9. **Un programa sin la tabla de arranque no funciona y en la placa falla en silencio** (sección 6.6): el trader no opera y el patrimonio queda en 10 000. Afecta al kit de contingencia: `tools/retune.py` y el cambio de programa con `icebram` tienen que anteponer la tabla (`tools/icebram_prueba.sh` lo hace), y conviene que la equivalencia rápida de ese kit corra contra el barrel.

A favor: un solo flanco de reloj y ninguna ruta de medio ciclo, 19,0 ns de 40 en la peor semilla, el mismo reset de encendido del base y el programa en una sola copia de la memoria, como en el base (el segmentado tiene dos, T34). El cambio de programa con `icebram` funciona en el barrel (sección 6.12).

## 11. Veredicto

**Hardware: pasa los dos criterios de corte.** Cabe junto al SPI (934 de 1280 celdas y 12 de 16 BRAM) y cierra a 25 MHz en 10 de 10 semillas. No se descarta de la edición de competencia. Las dos mediciones se repitieron en la segunda parte y dieron lo mismo.

**Verificación: no se encontró ningún error.** Cada hilo hace lo mismo que el Espino base en 8 727 624 instrucciones de programas aleatorios (2,18 millones por hilo), con cuatro hilos a la vez, con memoria compartida y con accesos al SPI y a los periféricos. Los 21 errores puestos a propósito se detectan. La regla base decide igual que la referencia en los cuatro hilos. Además están probadas con SymbiYosys, para cualquier programa, las propiedades de estructura: los hilos no se pisan en el banco, x0 no se escribe, cada hilo sigue su propio contador de programa y el arranque deja a cada uno en su entrada. Lo que falta para llamarlo verificado como el pipeline de 3 etapas es el gemelo.

Lo que este tramo no puede decidir:

- **Si conviene.** El barrel solo no mejora el patrimonio: con la regla base decide igual que los otros dos cores y responde más lento. Vale la pena si el fondo de estrategias (piezas B y C) pasa su propio criterio de corte en los estudios de retorno. Si el fondo no gana, el core que conviene para un solo hilo es el pipeline de 3 etapas, y el barrel pasa a la edición de exhibición con estos números.
- **Si llega.** Son 7 días de trabajo estimados antes del 25/11 (5,5 si solo corre la regla base en un hilo), más la prueba con la maestra.

Qué aporta al diseño integrado si se elige: 346 celdas y 4 BRAM libres para la extensión de la ISA y el vigilante (486 celdas si además se quita la emulación de la memoria), cuatro juegos de 16 registros sin guardar ni restaurar contexto, y tiempo constante por instrucción.

## 12. Para probar en la placa

Lo ejecuta Nicolás. Ningún script de esta carpeta programa la placa.

```bash
# 1. Construye los dos bitstreams y los simula desde el .asc. No toca la placa. Unos 4 minutos.
make -C factibilidad/a_barrel bitstream

# 2. Comprueba que el archivo es el que se simuló: el hash debe ser el de mediciones/bitstream.txt.
sha256sum factibilidad/a_barrel/build/bitstream/barrel_cooperacion.bin

# 3. Graba la flash de la Go Board con el programa de los cuatro hilos. Reemplaza lo que haya.
iceprog factibilidad/a_barrel/build/bitstream/barrel_cooperacion.bin

# 4. Para volver al bitstream de competencia.
iceprog bitstreams/competencia_v1.bin
```

Qué se debe ver después del paso 3, sin la maestra conectada: el display muestra "60" y los cuatro LEDs quedan encendidos. Eso dice que los cuatro hilos corrieron, que los tres trabajadores publicaron sus valores y que el supervisor los sumó (55 + 42 + 255 = 352 = 0x160, y el display muestra los 8 bits bajos). Si el display muestra otro número y hay un solo LED encendido, el supervisor terminó pero la suma salió mal: algún hilo publicó un valor equivocado. Si el display queda en "00" con los LEDs apagados, el supervisor sigue esperando a algún hilo o el programa no arrancó, y lo primero a mirar es el arranque de las BRAM, como en el Proyecto 2.

`barrel_trade.bin` es el que se probaría con la maestra el 26/11: la regla base en el hilo 0.

## 13. Cómo reproducir

Desde la raíz del repositorio o desde esta carpeta. Los scripts agregan OSS CAD Suite al `PATH`.

| Comando | Qué mide | Salida | Demora aproximada |
|---------|----------|--------|--------|
| `make -C factibilidad/a_barrel humo` | Pruebas de humo y controles negativos | `mediciones/humo.txt` | 10 s |
| `make -C factibilidad/a_barrel cpi` | CPI, MIPS y Ppeak con el mix de la clase 7 | `mediciones/cpi.txt` | 15 s |
| `make -C factibilidad/a_barrel ticks` | Latencia de la regla base y barrido de la fase | `mediciones/ticks.txt` | 1 min |
| `make -C factibilidad/a_barrel oficial` | Testbench oficial sin modificar, barrel y base | `mediciones/oficial.txt` | 2 min |
| `make -C factibilidad/a_barrel equiv` | 20 000 ticks contra `ref/trader.py`, a 0,1 ms y 1 ms | `mediciones/equiv_ref.txt` | 6 min |
| `make -C factibilidad/a_barrel netlist` | Simulación de la netlist sintetizada | `mediciones/netlist.txt` | 1 min |
| `make -C factibilidad/a_barrel recursos` | Celdas, BRAM y frecuencia en 10 semillas de 10 variantes, desglose y ruta crítica | `mediciones/recursos.txt`, `desglose.txt` y `ruta_critica.txt` | 5 min |
| `make -C factibilidad/a_barrel bitstream` | Dos bitstreams simulados desde el `.asc` | `mediciones/bitstream.txt` | 4 min |
| `make -C factibilidad/a_barrel todo` | Todo lo anterior | | 20 min |
| `make -C factibilidad/a_barrel verif` | Cada hilo contra el Espino base, instrucción por instrucción, 1158 corridas | `mediciones/verificacion.txt` | 1 min |
| `make -C factibilidad/a_barrel mutaciones` | Los 21 controles negativos | `mediciones/mutaciones.txt` | 2 min |
| `make -C factibilidad/a_barrel trazas` | Trazas en modo funcional con Icarus, 12 semillas | `mediciones/trazas.txt` | 1 min |
| `make -C factibilidad/a_barrel spi` | `sw/trade.s` en cada hilo con la maestra del testbench oficial | `mediciones/spi_hilos.txt` | 1 min |
| `make -C factibilidad/a_barrel netlist-aleatorio` | Netlist contra RTL en los pines, 8 programas | `mediciones/netlist_aleatorio.txt` | 1 min |
| `make -C factibilidad/a_barrel sin-tabla` | El barrel con un programa sin tabla de arranque | `mediciones/sin_tabla.txt` | 15 s |
| `make -C factibilidad/a_barrel formal` | Propiedades formales de estructura y 9 controles negativos | `mediciones/formal.txt` | 10 s |
| `make -C factibilidad/a_barrel icebram` | Cambio de programa en el bitstream con `icebram`, simulado desde el `.asc` | `mediciones/icebram.txt` | 2 min |
| `make -C factibilidad/a_barrel verificacion` | Los ocho anteriores | | 8 min |
| `make -C factibilidad/a_barrel equiv-ronda1` | `make equiv` más el período de 10 ms | `mediciones/equiv_ref.txt` | 25 min |
| `make -C factibilidad/a_barrel equiv-icarus` | Los 20 000 ticks a 0,1 ms con Icarus | `mediciones/equiv_icarus.txt` | 15 min |

`make recursos` deja los logs de nextpnr en `build/variantes/fact_a_*` de la raíz, que es donde escribe `tools/medir_variante.sh`. Todo lo demás queda en `factibilidad/a_barrel/build/`.

`tools/verif.sh` acepta `ESCALA` para cambiar la cantidad de semillas (con `ESCALA=0.1` es una corrida de pocos segundos, pensada para la integración continua) y `tools/mutaciones.sh` acepta `SOLO_INFORME=1` para volver a escribir el informe sin simular.

Herramientas: OSS CAD Suite del 2026-09-06 (Yosys 0.68+195, nextpnr 0.11.1-19-g8dbcee5c, Icarus Verilog 14.0, Verilator 5.053, SymbiYosys 0.68).
