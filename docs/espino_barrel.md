# Espino barrel: cuatro hilos por un pipeline de cuatro etapas

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Documento de estudio del tercer core del proyecto. Parte de lo básico y llega al detalle del RTL y de su verificación. Todos los números salen de un objetivo de `make` y su salida está guardada en `docs/mediciones/barrel/`. La sección 12 dice cuál.

El diseño nació como prototipo en el tramo de factibilidad (rama `factibilidad-fondo`, carpeta `factibilidad/a_barrel/`). En el paquete P1 pasó a `rtl/` sin cambios de lógica (decisión T55).

## 1. En una página

El Espino base ejecuta una instrucción cada 2 o 3 ciclos. El Espino segmentado (`docs/espino_segmentado.md`) ejecuta una por ciclo, salvo en los loads y en los saltos tomados, y para eso necesita adelantamiento de datos, una espera en los loads y anular instrucciones buscadas de más.

El Espino barrel resuelve el mismo problema de otra forma. Tiene un pipeline de cuatro etapas y **cuatro hilos de ejecución**, cada uno con su contador de programa y sus 16 registros. En cada ciclo entra al pipeline una instrucción de un hilo distinto, por turnos: hilo 0, 1, 2, 3, 0, 1... Así, en cada etapa siempre hay una instrucción de un hilo diferente, y dos instrucciones seguidas del mismo hilo nunca están juntas en el pipeline. Los problemas clásicos de un pipeline (una instrucción que necesita el resultado de la anterior, un salto que todavía no se resuelve) desaparecen, porque la instrucción anterior del mismo hilo ya terminó.

| | Espino base | Segmentado | Barrel |
|-|-------------|------------|--------|
| Hilos | 1 | 1 | 4 |
| Etapas | 2 estados | 3 | 4 |
| Ciclos por instrucción, por hilo | 2 o 3 | 1 o 2 | 4, siempre |
| Instrucciones por ciclo, todo el core | 0,43 con el mix de la clase 7 | 0,74 | 1,00 |
| Adelantamiento, burbujas, anulaciones | No hacen falta | Sí | No hacen falta |

El precio es la latencia: un hilo solo avanza una instrucción cada 4 ciclos. El barrel rinde cuando hay trabajo para los cuatro hilos. Con un solo hilo activo es el más lento de los tres cores. Por eso tiene sentido junto con el fondo de estrategias (un supervisor y tres gestores, `sw/fondo.s`, paquete P3) y no con `sw/trade.s` solo.

Sigue siendo Espino: la misma ISA (RV32E), el mismo decodificador, la misma ALU, la misma unidad de carga y almacenamiento y el mismo bus. Lo que cambia es la microarquitectura.

## 2. Lo básico: qué es un procesador barrel

Un procesador con varios hilos por hardware guarda varios estados de programa (contador de programa y registros) y reparte su camino de datos entre ellos. En un barrel el reparto es fijo: un hilo por ciclo, en ronda, sin prioridades y sin saltarse a nadie aunque no tenga nada que hacer. El nombre viene del tambor de un revólver.

En términos de la ley de hierro (Tiempo = IC × CPI × Tclk):

- **IC** no cambia: es la misma ISA.
- **Tclk** no cambia en la placa (25 MHz). La frecuencia máxima sube, porque no hay multiplexores de adelantamiento.
- **CPI** agregado baja a 1,000 exacto: el core completa una instrucción por ciclo, de cualquier clase. El CPI que ve cada hilo es 4,000 exacto.

Con la definición de la clase 7, Ppeak = f × instrucciones por ciclo × operaciones por instrucción × núcleos: 25 MHz × 0,25 × 1 × 4 = 25 MOPS con cuatro hilos y 6,25 MOPS con uno. El techo es el mismo del segmentado (25 MOPS), pero el barrel lo alcanza con cualquier mezcla de instrucciones y el segmentado solo con instrucciones de ALU.

## 3. El diseño

Archivos: `rtl/espino_core/espino_barrel_core.v` (el core) y `rtl/espino_core/espino_barrel_regfile.v` (el banco de registros). Se elige al compilar con `-DESPINO_BARREL` (`rtl/pochoco_soc.v`).

### 3.1 Las cuatro etapas

| Etapa | Qué hace |
|-------|----------|
| F, búsqueda | El contador de programa del hilo direcciona la memoria de instrucciones. |
| R, registros | La instrucción sale de la BRAM. Se decodifica y sus `rs1` y `rs2` direccionan el banco con `{hilo, registro}`. |
| X, ejecución | ALU, comparación del salto, próximo contador de programa y petición al bus de datos. |
| M, memoria y escritura | Llega el dato del load, se alinea y se escribe el registro destino en `{hilo, rd}`. |

Un contador de 2 bits (`tid_f`) dice qué hilo está en F. Los hilos de las otras etapas son ese valor menos 1, 2 y 3. El número de hilo no viaja con la instrucción. El contador de programa sí: hay un anillo de cuatro registros, uno por etapa (`pc_f_q`, `pc_r_q`, `pc_x_q` y `pc_m_q`).

### 3.2 Diagrama ciclo a ciclo

```
ciclo      1   2   3   4   5   6   7   8
hilo 0     F   R   X   M   F   R   X   M     instrucción i en los ciclos 1 a 4, la i+1 en 5 a 8
hilo 1     M   F   R   X   M   F   R   X
hilo 2     X   M   F   R   X   M   F   R
hilo 3     R   X   M   F   R   X   M   F
```

Leído por columnas: en cada ciclo hay un hilo en cada etapa. Leído por filas: cada hilo completa una instrucción cada 4 ciclos, sea de ALU, load, store o salto, tomado o no.

### 3.3 Qué ocurre en cada flanco

Todo el diseño usa el flanco de subida. No hay BRAM con reloj invertido ni rutas de medio ciclo, a diferencia del segmentado.

| Flanco que cierra la etapa | Qué se registra |
|----------------------------|-----------------|
| F | La BRAM de instrucciones lee la palabra del contador de programa. Su registro de salida es el registro entre F y R. El anillo de contadores avanza una posición. |
| R | La BRAM del banco lee `{hilo, rs1}` y `{hilo, rs2}`. Su registro de salida es el registro entre R y X. Se registran la decodificación y la instrucción. |
| X | Si es un store, se escribe la memoria o el periférico. Si es un load, la memoria o el periférico registran el dato. Aquí ocurren los efectos sobre el esclavo SPI: leer `PRICE` baja la bandera y escribir `DECISION` cambia el byte de salida. Se registran el resultado de la ALU o el enlace, los dos bits bajos de la dirección y el próximo contador de programa del hilo. |
| M | Se escribe el banco en `{hilo, rd}`, con el resultado o con el dato del load ya alineado. El próximo contador de programa pasa a la etapa F. |

Las tres memorias del SoC (instrucciones, datos y banco de registros) son BRAM con lectura registrada. En el Espino base esa lectura registrada cuesta un ciclo de espera. En el segmentado obligó a leer la memoria de instrucciones en el flanco de bajada. En este pipeline cada BRAM cae justo en una frontera entre etapas y su registro de salida hace de registro de pipeline. Por eso el barrel es el más chico de los tres cores.

### 3.4 Por qué no hay riesgos de datos ni de control

Para un mismo hilo, la instrucción i ocupa los ciclos 1 a 4 y la i+1 los ciclos 5 a 8.

| Riesgo en un pipeline normal | Qué pasa en el barrel |
|------------------------------|-----------------------|
| La instrucción i+1 lee un registro que i todavía no escribe | i escribe el banco en el flanco que cierra el ciclo 4. La i+1 lo lee en el flanco que cierra el ciclo 6. La BRAM ya tiene el dato, con un ciclo de sobra. No hace falta adelantamiento. |
| Load seguido de uso | El dato del load se escribe en ese mismo flanco del ciclo 4. No hace falta detener nada. |
| Store seguido de load a la misma dirección | El store de i se escribe al cerrar el ciclo 3 y el load de i+1 se pide al cerrar el ciclo 7. |
| Salto: se buscan instrucciones antes de saber si se toma | El próximo contador de programa se calcula en el ciclo 3 y se usa para buscar en el ciclo 5. Nunca se busca una instrucción antes de que la anterior del mismo hilo haya resuelto su salto. Ninguna instrucción buscada se descarta. |
| Efectos en el SPI de una instrucción que después se anula | No hay instrucciones especulativas. Una lectura de `PRICE` o una escritura de `DECISION` que llega a la etapa X siempre es de verdad. |
| Lectura y escritura del banco en el mismo flanco | La lectura es del hilo que está en R y la escritura del que está en M. Sus números de hilo difieren siempre en 2, así que las direcciones `{hilo, registro}` no pueden coincidir. |

Las únicas burbujas son las dos del arranque (sección 3.6).

### 3.5 Dónde viven los cuatro contextos

El banco de registros del Espino ya estaba en BRAM: dos copias de 32 bits (una por puerto de lectura), cada una en dos bloques de 256 palabras de 16 bits, de las que usaba 16. El barrel amplía la dirección de 4 a 6 bits, `{hilo, registro}`, y los cuatro contextos ocupan 64 de esas 256 palabras. No cuesta ninguna BRAM adicional, y no hay que guardar ni restaurar registros al cambiar de hilo.

`x0` de cada contexto vale 0 porque es el contenido inicial de la BRAM y el core nunca habilita una escritura con registro destino 0 (`espino_barrel_core.v`, registro `rf_we_m`).

### 3.6 Cómo arrancan los hilos

El hilo t parte en la dirección 4 t. Todo programa para el barrel empieza con una tabla de cuatro saltos:

```
    j    hilo0        # dirección 0
    j    hilo1        # dirección 4
    j    hilo2        # dirección 8
    j    hilo3        # dirección 12
```

En hardware la tabla no cuesta nada: son los valores de reset del anillo de contadores. El pipeline sale del reset como si tuviera burbujas en R y en X, que son instrucciones que no escriben, no piden el bus y no saltan (`valid_r` en el core). La primera instrucción del hilo t llega a ejecución en el ciclo 3 + t después del reset.

`tools/barrel/tabla.py` antepone la tabla a un programa escrito para un solo hilo, sin tocarlo: el hilo elegido salta a `_start` y los otros tres quedan en un lazo vacío. Así corre `sw/trade.s` en el barrel.

**Un programa sin la tabla no funciona.** Si se carga `sw/trade.hex` tal cual, los hilos 1, 2 y 3 parten en la segunda, tercera y cuarta instrucción del programa. El testbench oficial entrega 2/4 y el trader no opera (`make barrel-sin-tabla`). En la placa esa falla es silenciosa. Todo flujo que regenere el programa del barrel tiene que anteponer la tabla.

### 3.7 Memoria compartida y periféricos

Los registros no se comparten: cada hilo tiene su contexto. La memoria y los periféricos sí.

- Hay un solo bus de datos y una sola instrucción en la etapa X por ciclo. Cada load y cada store es atómico, y los accesos de los cuatro hilos quedan en un orden fijo: uno por ciclo, por turnos.
- Leer, modificar y escribir son tres instrucciones, y entre ellas corren los otros hilos (12 ciclos). No hay instrucciones atómicas de lectura y escritura. La regla de uso es que cada palabra compartida tiene un solo hilo que la escribe (`sw/barrel/cooperacion.s`).
- Una palabra se escribe completa en un flanco. Un valor y su número de tick empaquetados en una palabra se publican de forma atómica.
- Los periféricos y el esclavo SPI no saben de hilos. El que lee `PRICE` baja la bandera para todos. En el fondo de estrategias solo el hilo supervisor toca el SPI.
- El código es reentrante: cuatro hilos pueden ejecutar la misma subrutina, cada uno con sus registros (`sw/barrel/mix_clase7_x4.s`).

El hardware es determinista: el orden relativo entre hilos está fijo ciclo a ciclo. Lo que puede tener carreras es el software, si dos hilos escriben la misma palabra.

### 3.8 Qué se reutiliza del Espino y qué cambia

Sin modificar: `espino_decoder.v`, `espino_alu.v` y `espino_load_store_unit.v`. La unidad de carga y almacenamiento se instancia dos veces: una arma la petición en X y la otra alinea el dato en M. Su máquina de espera no se usa. Los multiplexores de operandos, el destino del salto y el enlace son los de `espino_id_stage.v`, copiados. El SoC es el mismo: memoria, esclavo SPI, periféricos, mapa de memoria y multiplexor de lectura.

Diferencias de comportamiento con el Espino base:

1. Cada hilo, por separado, hace lo mismo que el Espino base partiendo en su entrada (sección 8).
2. El contador de programa tiene 11 bits, el ancho real de la memoria, igual que en el segmentado (T36). Si un programa salta fuera de las 512 palabras, `auipc` y el enlace de `jal` entregan el contador recortado.
3. El programa empieza con la tabla de arranque.
4. Los ciclos: 4 por instrucción y por hilo.
5. Código que se modifica a sí mismo: un store sobre una palabra que otro hilo está buscando se ve en un ciclo distinto que en el base. Ningún programa del proyecto lo hace.

## 4. Qué cuesta: la latencia por hilo

Cada hilo avanza una instrucción cada 4 ciclos. Con `sw/trade.s` en el hilo 0 y los otros tres en un lazo vacío, 200 ticks de la serie de práctica con el timing del testbench oficial (`make barrel-ticks`, `docs/mediciones/barrel/ticks.txt`):

| Core | Respuesta: ciclos promedio | Peor caso | Peor caso barriendo la fase del sondeo | Parte del presupuesto de la ronda 3 (2262 ciclos) |
|------|----------------------------|-----------|-----------------------------------------|---------------------------------------------------|
| Espino base | 41,0 | 44 | 49 | 2,2 % |
| Segmentado | 22,0 | 26 | 27 | 1,2 % |
| Barrel, hilo 0 | 75,1 | 83 | 88 | 3,9 % |

El barrel responde 1,8 veces más lento que el base y 3,4 veces más lento que el segmentado, con el mismo programa. El lazo de sondeo dura 12 ciclos (3 instrucciones) en vez de 6 o 7, y por eso el peor caso depende más de la fase en que llega el precio.

El peor caso sube un ciclo por hilo (83, 84, 85 y 86 en los hilos 0 a 3, `make barrel-spi`), porque el hilo t pasa por la etapa X un ciclo después que el t - 1. No cambia cuando los otros hilos están ocupados: **el tiempo de un hilo no depende de lo que hagan los demás**. Esa es la propiedad que usa el fondo de estrategias, con un hilo que atiende a la maestra mientras los otros calculan.

Lo que cabe: en la ronda 3 hay 2262 ciclos por tick, unas 565 instrucciones por hilo. La puerta de simulación pide responder en la mitad (1131 ciclos), unas 280 instrucciones del hilo que decide.

## 5. Desempeño: CPI, MIPS y Ppeak

Con el lazo de 20 instrucciones de `sw/mix_clase7.s` (20 % de loads y 15 % de saltos tomados), los tres cores en la misma corrida (`make barrel-cpi`, `docs/mediciones/barrel/cpi.txt`):

| | Base | Segmentado | Barrel, 4 hilos | Barrel, 1 hilo activo | Clase 7, estimado para 3 etapas |
|-|------|------------|-----------------|-----------------------|-------------------------------|
| CPI con el mix | 2,350 | 1,350 | 1,000 | 4,000 | 1,5 |
| MIPS a 25 MHz | 10,64 | 18,52 | 25,00 | 6,25 | 16,7 |
| Speedup contra el base | 1 | 1,74 | 2,35 | 0,59 | 1,57 |
| Ciclos de ALU, load y salto tomado | 2, 3 y 3 | 1, 2 y 2 | 1, 1 y 1 | 4, 4 y 4 | 1, 2 y 3 |

El testbench comprueba el modelo de costo: una instrucción completada por ciclo en total y una cada 4 ciclos en cada hilo, de cualquier clase.

## 6. Recursos y timing

`nextpnr-ice40 --hx1k --package vq100 --freq 25`, semillas 1 a 10, los tres cores en la misma corrida y con el mismo programa (`make barrel-recursos`, `docs/mediciones/barrel/recursos.txt`). Es el SoC completo.

| Variante | Celdas, de 1280 | BRAM, de 16 | Fmax mínima | Mediana | Máxima | Cierran a 25 MHz |
|----------|-----------------|-------------|-------------|---------|--------|------------------|
| Espino base | 1086 | 12 | 42,75 | 44,48 | 47,64 | 10 de 10 |
| Segmentado | 993 | 12 | 51,59 | 53,48 | 54,95 | 10 de 10 |
| Barrel | 933 | 12 | 52,62 | 55,65 | 59,18 | 10 de 10 |

El barrel deja 347 celdas y 4 BRAM libres, que es donde van la extensión de la ISA, la tabla de parámetros y el vigilante (paquetes P2 y P5). El criterio 3 de la puerta de simulación se comprueba con `make barrel-timing`, que falla si alguna de las 10 semillas no cierra.

Las cifras del base se mueven unas pocas celdas respecto de las de P0 (1083 celdas, 42,43 MHz). El RTL del base no cambió (`make formal-base`); cambia el conjunto de archivos que lee Yosys, y diferencias menores que unas 10 celdas son ruido de la síntesis (T6).

Otras variantes medidas en la misma corrida:

| Cambio sobre el barrel | Celdas | Diferencia |
|------------------------|--------|------------|
| Contador de programa de 32 bits en vez de 11 | 1143 | +210 |
| Contador de reset de 4 bits en vez de 12 | 921 | -12 |
| Memoria sin emulación de lectura durante escritura (`no_rw_check`) | 796 | -137 |

Ninguna está aplicada. La última toca `rtl/pochoco_ram.v`, que comparten los tres cores, y cambia lo que pasa en la placa si un hilo busca la palabra que otro está escribiendo en ese mismo flanco.

**Ruta crítica** (`docs/mediciones/barrel/ruta_critica.txt`): salida de la BRAM del banco de registros, multiplexor de operandos, sumador de la ALU, multiplexor del resultado, decodificación de la dirección (`spi_sel`, `per_sel`) y habilitación del registro de lectura de los periféricos. Es la misma ruta que limita al segmentado, sin el multiplexor de adelantamiento. En la peor semilla ocupa 19,0 ns de los 40 disponibles.

**Dónde están las celdas** (`docs/mediciones/barrel/desglose.txt`): el core barrel tiene más flip-flops que el base (los registros de etapa y el anillo de contadores) y menos LUT (sin ciclo de espera, sin adelantamiento, contador de 11 bits).

## 7. El SoC completo con la maestra

| Prueba | Resultado | Comando y salida |
|--------|-----------|------------------|
| Testbench oficial sin modificar, `sw/trade.s` con la tabla de arranque en el hilo 0 | 4/4. Peor caso 83 ciclos de 2262. `decisiones.csv` idéntico byte a byte al del Espino base, patrimonio 9 661 | `make barrel-oficial`, `oficial.txt` |
| Los 20 000 ticks de práctica contra `ref/trader.py`, con Verilator | Idénticos a 0,1 ms (peor caso 83) y a 1 ms (peor caso 87). Patrimonio 26 070 | `make barrel-equiv`, `equiv_ref.txt` |
| `sw/trade.s` en cada uno de los cuatro hilos, solo y con los otros tres corriendo programas al azar | 12 de 12 casos con 4/4 e idénticos a la referencia | `make barrel-spi`, `spi_hilos.txt` |
| Trazas en modo funcional contra el Espino base, con Icarus (cuatro estados) | 417 582 escrituras al banco y 169 663 accesos al bus iguales en 60 corridas. Ningún valor X | `make barrel-trazas`, `trazas.txt` |
| Netlist de Yosys contra el RTL, en los pines, con programas aleatorios y tráfico SPI | 7 327 eventos idénticos en 8 programas | `make barrel-netlist-aleatorio`, `netlist_aleatorio.txt` |
| Bitstream ruteado, simulado desde el `.asc` | 500 ticks idénticos a la referencia | `make barrel-bitstream`, `bitstream.txt` |
| Cambio de programa con `icebram`, sin volver a sintetizar | El `.bin` cambiado tiene el mismo sha256 que el sintetizado directamente | `make barrel-icebram`, `icebram.txt` |
| Programa sin tabla de arranque | Falla, como se esperaba | `make barrel-sin-tabla`, `sin_tabla.txt` |

El testbench oficial lee `sw/trade.hex` del directorio actual. Contra el barrel se corre dentro de una carpeta de `build/` donde ese nombre es el programa con la tabla de arranque. El archivo `tb/tb_proyecto_4.sv` no se modifica (T56).

Faltan para el barrel las corridas largas que quedaron como ejecución manual: los 20 000 ticks con Icarus (`make barrel-equiv-icarus`, unos 15 minutos) y a 10 ms (`make barrel-equiv-ronda1`, unos 25 minutos). En la factibilidad las dos pasaron con el mismo RTL y la regla anterior.


## 8. Verificación

El core se verifica de cuatro formas que se complementan. Ninguna encontró un error en el barrel, ni en la factibilidad ni al traerlo a `rtl/`.

| Prueba | Qué compara | Qué no ve | Comando |
|--------|-------------|-----------|---------|
| Cada hilo contra el Espino base, instrucción por instrucción | Contador de programa, instrucción, escritura al banco, acceso al bus, los 16 registros del contexto y la palabra o el registro escrito | Lo que el base y el barrel hicieran mal los dos | `make barrel-verif` |
| Controles negativos | 21 errores puestos a propósito tienen que ser detectados por la comparación anterior | | `make barrel-mutaciones` |
| Propiedades formales de estructura | Aislamiento de contextos, x0, burbujas, rotación de hilos, contador de programa de cada hilo y arranque, para cualquier programa | Que cada instrucción calcule lo que debe | `make barrel-formal` |
| El SoC completo con la maestra SPI | `decisiones.csv` del testbench oficial contra `ref/trader.py` | Programas distintos de `sw/trade.s` | `make barrel-oficial`, `make barrel-equiv`, `make barrel-spi` |

### 8.1 Cómo se compara cada hilo con el Espino base

`tb/barrel/tb_verif.sv` instancia cinco SoC completos con el mismo programa: el barrel y cuatro `pochoco_soc` con el Espino base, uno por hilo, cada uno partiendo en la entrada de su hilo. La instrucción número k del hilo t del barrel se compara con la instrucción número k de su Espino base:

- contador de programa e instrucción;
- escritura al banco de registros: registro y valor;
- acceso al bus de datos: lectura o escritura, dirección, bytes habilitados y dato;
- los 16 registros del contexto después de la instrucción, leídos de las BRAM del banco (las dos copias);
- en un store a memoria, la palabra recién escrita;
- en un store al SPI o a los periféricos, el registro escrito (`DECISION`, display o LEDs).

Al final se compara la memoria completa. El número de hilo de cada etapa lo calcula el testbench con el número de ciclo, y se exige que coincida con el del core.

Hay dos referencias, y son las dos pruebas que pide el paquete:

- **Aislamiento entre hilos.** Si lo que hace un hilo no depende de los otros (zonas de datos separadas), cada Espino base corre solo. Que el barrel coincida quiere decir que cada hilo se comporta como si fuera el único, aunque los otros tres estén ejecutando programas distintos sobre el mismo camino de datos. Grupos B, C, T, L y M. `make barrel-aislamiento` los corre junto con las propiedades formales.
- **Memoria compartida.** Si los hilos leen y escriben la misma zona, los cuatro Espino base ejecutan por turnos, una instrucción cada uno, y cada store de uno se copia a la memoria de los otros tres. En el barrel los accesos al bus ocurren en ese mismo orden. Grupos D y P. El grupo N es el control: los mismos programas contra la referencia de hilos aislados tienen que fallar, y fallan todos. Si pasaran, los hilos no estarían interactuando y la prueba no probaría nada. `make barrel-compartida`.

El bus SPI queda quieto en esta prueba, porque un precio que llega por los pines cae en ciclos distintos en cada SoC. Para ejercitar igual el esclavo, el testbench deja un precio nuevo en `PRICE` y levanta la bandera de `STATUS` entre la misma pareja de instrucciones en el barrel y en el Espino base. El tráfico SPI real por los pines se prueba con el testbench oficial.

### 8.2 Dos campañas de programas aleatorios

`tools/barrel/prog_hilos.py` genera programas de cuatro hilos con la misma mezcla de instrucciones del generador del repositorio (`tools/prog_aleatorio.py`).

**Campaña de lazos** (grupos A, U, H, B, C, T y D). El cuerpo de cada hilo se repite para siempre y dos registros avanzan en cada vuelta para que los valores cambien. Corre pocas corridas largas. Sirve para estados que tardan en aparecer, pero una parte grande de lo comparado es repetición: las comparaciones dan 0 o 1 y las constantes son las mismas en cada vuelta.

**Campaña lineal** (grupos L, M, P y Q, opción `--lineal`). Es la que responde al criterio 5 de la puerta de simulación, que pide al menos 5 millones de instrucciones con más de 90 % distintas (decisión T57). Cada cuerpo se ejecuta una sola vez y termina en un lazo vacío. Son muchas corridas cortas, cada una con un programa distinto. Los saltos hacia atrás se ejercitan con lazos cortos de 2 a 4 vueltas.

Una instrucción comparada cuenta como **distinta** si no hay otra, en ninguna corrida de la campaña, con el mismo hilo, contador de programa, instrucción, valor escrito al banco, acceso al bus y palabra de memoria escrita.

Resultado de `make barrel-verif` (`docs/mediciones/barrel/verificacion.txt`), con el barrel tal como se sintetiza:

| Grupo | Qué corre | Corridas | Instrucciones de programa | Distintas dentro de la corrida |
|-------|-----------|----------|---------------------------|--------------------------------|
| L | Cuatro hilos, zonas de datos separadas, los cuatro con SPI (bus quieto) y periféricos | 6 500 | 2 686 320 | 2 635 214 |
| M | Cuatro hilos, uno solo con el SPI y un precio nuevo cada 11 instrucciones | 5 200 | 2 147 955 | 2 106 825 |
| P | Cuatro hilos sobre la misma zona de datos, referencia por turnos | 4 500 | 1 627 178 | 1 580 645 |
| Q | Un hilo con 300 instrucciones y los otros tres ociosos | 4 400 | 1 487 105 | 1 448 278 |
| **Campaña lineal** | | **20 600** | **7 948 558** | **7 770 962 (97,77 %)** |
| Campaña de lazos | Grupos A, U, H, B, C, T y D | 748 | 8 966 903 | 3 859 705 (43,0 %) |
| W | Programas de A con el contador de programa de 32 bits | 200 | 1 200 000 | |

**Distintas en toda la campaña lineal: 7 309 470 de 7 948 558, el 91,96 %. Cero diferencias con el Espino base.** El criterio 5 pide 5 millones y más de 90 %.

Lo que se repite de una corrida a otra (el 5,8 % que separa las dos cifras) son las instrucciones fijas de cada hilo: el salto de la tabla de arranque y la carga de las tres direcciones base. Dentro de una corrida se repiten los saltos de los lazos cortos.

De las instrucciones de la campaña lineal, 6,19 millones escriben un registro, 891 mil son loads, 754 mil son stores, 998 mil son saltos y 406 mil acceden al SPI o a los periféricos. El testbench puso 98 mil precios nuevos. Las simulaciones demoran 190 segundos con 14 procesos.

**Un hallazgo del método.** La primera corrida completa terminó con 2 programas del grupo P, de 4 500, distintos al modelo de turnos. En los dos, un `jalr` con una base cualquiera (permitido a propósito en ese grupo) llevó a un hilo a ejecutar la zona de datos compartida. En uno, los otros hilos estaban escribiendo la palabra que ese hilo buscaba, y el barrel la busca en un ciclo distinto que el modelo. En el otro, el hilo ejecutó un `jalr` en la última palabra de la memoria y el enlace vale 0x800 en el base y 0 en el barrel. Son las diferencias 2 y 5 de la sección 3.8, no un error del core. La comparación terminaba cuando un hilo salía de la memoria, pero no cuando entraba a la zona de datos. Ahora termina ahí (`+limite_codigo` en `tb/barrel/tb_verif.sv`) y la campaña se repitió completa. La campaña de lazos de la factibilidad no lo había visto con 100 programas.

### 8.3 Controles negativos

`tools/barrel/mutar.py` hace un reemplazo de texto en una copia de los tres archivos del barrel (los de `rtl/` no se tocan). Hay 18 mutaciones, más las tres que el core trae bajo `ifdef` (`MUTA_CONTEXTO`, `MUTA_BOFF` y `MUTA_ARRANQUE`). Con cada barrel mutado se corren siete comparaciones cortas: las cinco de la campaña de lazos (grupos A, H, B, C y D) y dos con programas lineales (L y P).

**21 de 21 detectadas, cada una por las siete comparaciones** (`docs/mediciones/barrel/mutaciones.txt`). La más tardía aparece en la instrucción 239 de un hilo.

| Qué rompen | Mutaciones |
|------------|------------|
| El contexto: se lee o se escribe el registro de otro hilo | `ctx_escritura`, `ctx_lectura_rs1`, `ctx_lectura_rs2`, `escritura_sin_hilo`, `rd_otro_hilo`, `MUTA_CONTEXTO` |
| El contador de programa de cada hilo | `pc_otro_hilo`, `enlace_otro_hilo`, `jalr_no_salta` |
| x0 | `x0` |
| Cargas y almacenamientos | `be_ram`, `tamano_store`, `dato_store`, `desplazamiento_load`, `signo_load`, `MUTA_BOFF` |
| El bus y el multiplexor de lectura | `mux_lectura`, `peticion_bus` |
| El arranque | `burbuja_salta`, `hilo_desfasado`, `MUTA_ARRANQUE` |

### 8.4 Propiedades formales

`tools/barrel/formal.sh` inserta las propiedades de `formal/barrel/propiedades.vh` en una copia del core y las prueba con SymbiYosys y boolector, con el decodificador, la ALU y la unidad de carga del repositorio. Quedan libres la instrucción que entrega la memoria, el dato del bus y el contenido del banco de registros, así que lo probado vale para cualquier programa y cualquier contenido de memoria.

| Propiedad | Qué afirma | Cómo se prueba |
|-----------|------------|----------------|
| P1 | El hilo que lee el banco (etapa R) nunca es el que lo escribe (etapa M) | Inducción |
| P2 | x0 no se escribe nunca | Inducción |
| P3 | Una burbuja no pide el bus, no salta y no escribe el banco | Inducción |
| P4 | No hay escritura al bus sin petición | Inducción |
| P5 | Los hilos rotan: en la etapa X hay un hilo distinto en cada ciclo, en orden | Inducción |
| P6 | La instrucción que escribe el banco es la que estuvo en X en el ciclo anterior, y escribe en el contexto de ese hilo | Inducción |
| P7 | Después de las dos burbujas del arranque no vuelve a haber burbujas | Inducción |
| P8 | El contador de programa que entra a F es el que calculó ese mismo hilo dos ciclos antes, en X | Inducción |
| P9 | Arranque: el hilo t busca su primera instrucción en 4 t en el ciclo t + 1 y la ejecuta en el ciclo t + 3 | Acotada, 12 ciclos desde el reset |
| P10 | Los operandos que llegan a X se leyeron del contexto del hilo que está en X y de los registros rs1 y rs2 de su instrucción | Inducción, con un banco que devuelve las direcciones que vio |
| P11 | Lo que el banco escribió es el registro destino de la instrucción que estuvo en X dos ciclos antes, en el contexto de ese hilo, y solo si esa instrucción escribía y su destino no era x0 | Inducción, con el mismo banco |

Son 24 afirmaciones en tres tareas y las tres pasan. Una cuarta tarea de cobertura comprueba que la prueba no es vacía. Como controles negativos, las mismas tareas se corren sobre 9 mutaciones, y las 9 entregan un contraejemplo desde el reset. Toda la corrida demora unos 10 segundos (`docs/mediciones/barrel/formal.txt`).

P1, P6, P10 y P11 son la prueba formal del aislamiento: para cualquier programa, un hilo solo lee y escribe su propio contexto.

Un detalle del método. Con profundidad de inducción 6 la mutación `ctx_escritura` no entregaba contraejemplo: el caso base no alcanzaba a llegar a la primera escritura al banco (ciclo 5 desde el reset), solo fallaba el paso inductivo, y SymbiYosys responde UNKNOWN en vez de FAIL. Con profundidad 10 sí hay contraejemplo. El script distingue los dos casos y no cuenta un UNKNOWN como detección.

### 8.5 Lo que no está cubierto

- **La placa y la maestra real.** Todo lo anterior es simulación. Falta la puerta de placa (P6) y la del 26/11.
- **Prueba formal de lo que calcula cada instrucción.** Las propiedades son de estructura. Que un `add` sume se apoya en la comparación contra el Espino base. No se corrió riscv-formal ni una equivalencia formal contra el base.
- **El gemelo digital** modela el barrel desde P4 (`docs/gemelo.md`, sección 7).
- **Cuatro hilos accediendo al SPI mientras llegan precios por los pines**, comparados contra el base. Ahí lo que ve cada hilo depende de cuál leyó `PRICE` primero y no hay un Espino base de referencia. Se cubre con el bus quieto, con un solo hilo en el SPI y en la comparación de netlist contra RTL.
- **Código que se modifica a sí mismo** y programas que escriben sobre el código de otro hilo.
- **Fuera de la memoria con el contador de 11 bits.** Se compara solo con el de 32 (grupo W).
- **Instrucciones ilegales.** El decodificador es el mismo módulo en los dos cores y ninguno usa su salida `illegal_insn_o`. Los programas aleatorios traen algunas codificaciones raras (custom-0, `ecall`, loads y saltos con `funct3` inválido) y los dos cores hacen lo mismo con ellas.


## 9. Reglas del enunciado

| Regla | Cumple | Comentario |
|-------|--------|------------|
| La decisión la calcula el Espino. El core lee el precio y escribe la decisión | Sí | El barrel es el procesador, no un acelerador. Un hilo lee `PRICE` y escribe `DECISION` con instrucciones de la ISA |
| El RTL se puede modificar mientras el procesador siga siendo Espino | Sí | ISA, decodificador, ALU, unidad de carga y bus son los del Espino, sin modificar. Cambia la microarquitectura. El profesor lo confirmó en persona el 16/11: se puede modificar lo que uno quiera, y el Espino multihilo está bien (T126) |
| Todo hardware agregado va con su testbench | Sí | `tb/barrel/` |
| El mismo programa en las tres rondas | Sí | |
| No se guarda la serie | Sí | El core no guarda nada de la serie |
| El testbench oficial no se modifica | Sí | 4/4 sin tocarlo |

## 10. Riesgos

1. **No se ha probado en la placa ni con la maestra real.**
2. **Que cada instrucción calcula lo que debe está comprobado por simulación**, no por una prueba formal.
3. **El software concurrente es más difícil que el hardware.** El core no tiene riesgos entre instrucciones, pero un programa con cuatro hilos sí puede tener carreras sobre la memoria compartida.
4. **Un hilo ocioso desperdicia su turno.** Con un solo hilo con trabajo el barrel rinde menos que el base.
5. **La latencia por hilo se multiplica por 4.**
6. **Un programa sin la tabla de arranque falla en silencio en la placa.**
7. **Un hilo que salta a ejecutar datos que otros escriben** no se comporta como el modelo de referencia (sección 8.2, hallazgo de la campaña lineal). Ningún programa del proyecto lo hace, y `sw/fondo.s` no usa `jalr` con bases calculadas a partir de datos.

A favor: un solo flanco de reloj y ninguna ruta de medio ciclo, 19 ns de 40 en la peor semilla, el mismo reset de encendido del base y el programa en una sola copia de la memoria.

## 11. Preguntas para la defensa

| Pregunta | Respuesta corta | Dónde se ve |
|----------|-----------------|-------------|
| ¿Por qué no hay adelantamiento? | Entre dos instrucciones del mismo hilo pasan 4 ciclos. La anterior ya escribió el banco cuando la siguiente lo lee | `rtl/espino_core/espino_barrel_core.v`, encabezado y sección "Avance del pipeline" |
| ¿Cómo sabe el core de qué hilo es cada instrucción? | Un contador de 2 bits, `tid_f`. Las otras etapas son ese valor menos 1, 2 y 3 | `espino_barrel_core.v`, `tid_f`, `tid_r`, `tid_x`, `tid_m` |
| ¿Dónde están los registros de los cuatro hilos? | En las mismas BRAM del banco, con dirección `{hilo, registro}`. 64 de 256 palabras | `rtl/espino_core/espino_barrel_regfile.v` |
| ¿Puede un hilo leer o escribir un registro de otro? | No. Está probado formalmente para cualquier programa (P1, P6, P10 y P11) y comparado en cada instrucción de la campaña | `formal/barrel/propiedades.vh`, `docs/mediciones/barrel/formal.txt` |
| ¿Qué pasa si dos hilos escriben la misma palabra de memoria? | Las dos escrituras ocurren, en ciclos distintos y en orden fijo. El hardware es determinista. Evitar la carrera es tarea del programa: una palabra, un escritor | Sección 3.7, `sw/barrel/cooperacion.s` |
| ¿Por qué un barrel si responde más lento? | Porque el diseño que compite corre cuatro estrategias a la vez. Para una sola, el segmentado es mejor y está medido | Sección 4 |
| ¿Sigue siendo Espino? | Misma ISA, mismo decodificador, misma ALU, misma unidad de carga, mismo bus. Cambia cuántos contextos hay y cómo se reparten los ciclos | Sección 3.8 |
| ¿Cómo saben que funciona? | Cada hilo comparado instrucción por instrucción con el Espino base, 21 errores puestos a propósito detectados, propiedades formales y el testbench oficial con 4/4 | Sección 8 |
| ¿Encontraron algún error? | En el core, ninguno. En el método, tres: programas que llegaban a un punto fijo, un `jalr` que sacaba a un hilo de su código, y un hilo que terminaba ejecutando datos | Sección 8.2, `docs/bitacora/p1.md` |
| ¿Cuál es el CPI? | 1,000 agregado y 4,000 por hilo, exactos, para cualquier mezcla | Sección 5 |

## 12. Cómo reproducir

Las herramientas de OSS CAD Suite tienen que estar en el `PATH`. Todo se corre desde la raíz del repositorio.

```bash
make check-barrel         # lo que corre la integración continua: formal, humo, comparación corta,
                          # testbench oficial, equivalencia de 20 000 ticks y timing en 10 semillas
make barrel-verif         # criterio 5: campaña lineal y campaña de lazos (unos 5 minutos con 12 procesos)
make barrel-mutaciones    # 21 controles negativos (1 minuto)
make barrel-aislamiento   # hilos aislados, más las propiedades formales
make barrel-compartida    # memoria compartida y su control negativo
make barrel-completo      # todo lo anterior y las mediciones (ejecución manual en la integración continua)
```

| Salida en `docs/mediciones/barrel/` | Objetivo |
|-------------------------------------|----------|
| `verificacion.txt` | `barrel-verif` |
| `mutaciones.txt` | `barrel-mutaciones` |
| `formal.txt` | `barrel-formal` |
| `aislamiento.txt`, `compartida.txt` | `barrel-aislamiento`, `barrel-compartida` |
| `timing.txt` | `barrel-timing` |
| `recursos.txt`, `desglose.txt`, `ruta_critica.txt` | `barrel-recursos` |
| `oficial.txt`, `equiv_ref.txt`, `spi_hilos.txt` | `barrel-oficial`, `barrel-equiv`, `barrel-spi` |
| `cpi.txt`, `ticks.txt` | `barrel-cpi`, `barrel-ticks` |
| `humo.txt`, `trazas.txt` | `barrel-humo`, `barrel-trazas` |
| `netlist.txt`, `netlist_aleatorio.txt`, `bitstream.txt`, `icebram.txt`, `sin_tabla.txt` | `barrel-netlist`, `barrel-netlist-aleatorio`, `barrel-bitstream`, `barrel-icebram`, `barrel-sin-tabla` |

Cada salida anota las versiones de las herramientas y el commit con que se corrió.

