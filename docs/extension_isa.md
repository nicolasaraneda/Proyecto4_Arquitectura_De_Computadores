# Extensión de la ISA en custom-0 sobre el Espino barrel

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Especificación y documento de estudio de las tres instrucciones que agregamos al Espino barrel: `emad`, `devk` y `mulstep`. Las secciones 2 y 3 son la especificación. El resto explica cómo están construidas, cuánto cuestan y cómo se verificaron. Cada número sale de un comando de la sección 11 y su salida está guardada en `docs/mediciones/xd/`.

## 1. En una página

| | |
|-|-|
| Qué es | Tres instrucciones de formato R en el opcode custom-0, el que RISC-V reserva para extensiones propias |
| Para qué | Reemplazan los dos bloques más caros de la regla de reversión: calcular la desviación del precio respecto de la media (6 instrucciones) y actualizar la media (8 instrucciones). `mulstep` es un paso de multiplicación para la contabilidad |
| Dónde | Solo en el Espino barrel (`-DESPINO_BARREL`). Se eligen al compilar: `-DESPINO_XD` las tres, o `-DESPINO_XD_EMAD`, `-DESPINO_XD_DEVK` y `-DESPINO_XD_MULSTEP` por separado. Sin definiciones el barrel es el del paquete P1 |
| Cómo | Las tres son "un desplazamiento por una constante y una suma". Usan el sumador de la ALU con el operando A desplazado. No agregan un sumador, ni estado, ni cambian el control del pipeline |
| Costo | Las tres: 96 celdas (1034 de 1280, quedan 246) y 0 BRAM. `emad` y `devk`: 52 celdas |
| Timing | 10 de 10 semillas en los 7 subconjuntos. Con las tres, frecuencia máxima mínima de 48,33 MHz |
| Verificación | Prueba formal de cada instrucción contra su especificación sobre el core, equivalencia formal del resto del core contra el de P1, y comparación por simulación instrucción por instrucción contra el Espino base con la especificación |
| Efecto en el tiempo | La regla `max_media` escrita con `devk` y `emad` responde en 63 ciclos en el peor caso del testbench oficial, contra 83 sin ellas |
| Efecto en el patrimonio | Ninguno. Las decisiones son las mismas, bit a bit |

## 2. Especificación: convenciones

- Opcode custom-0, `0001011` (0x0B), formato R:

| Bits | 31:25 | 24:20 | 19:15 | 14:12 | 11:7 | 6:0 |
|------|-------|-------|-------|-------|------|-----|
| Campo | `funct7` | `rs2` | `rs1` | `funct3` | `rd` | `0001011` |

- Los registros son los de RV32E, `x0` a `x15`. Escribir en `x0` no tiene efecto y leerlo entrega cero. El core usa los 4 bits bajos de cada campo de registro, igual que en el resto de la ISA.
- Las tres instrucciones son de un ciclo de ejecución, sin estado oculto y sin acceso a memoria. El resultado depende solo de `rs1` y `rs2`. No modifican el contador de programa (el hilo sigue en `pc + 4`) y no generan excepciones.
- Aritmética de 32 bits que da la vuelta (módulo 2^32). `>>>` es el desplazamiento aritmético a la derecha (copia el bit de signo) y `<<` el desplazamiento a la izquierda.
- **Toda otra palabra de custom-0 es una instrucción ilegal sin efecto**, como en el Espino sin la extensión: no escribe ningún registro, no accede al bus y no salta. Eso incluye `emad` y `devk` con k distinto de 5, `mulstep` con `funct7` distinto de cero, los demás valores de `funct3`, y una instrucción que no se incluyó al compilar el core.

| Instrucción | `funct3` | `funct7` | Resultado |
|-------------|----------|----------|-----------|
| `emad rd, rs1, rs2, 5` | 100 | 0000101 | `rd = rs2 + (rs1 >>> 5)` |
| `devk rd, rs1, rs2, 5` | 101 | 0000101 | `rd = (rs1 << 5) - rs2` |
| `mulstep rd, rs1, rs2` | 010 | 0000000 | `rd = (rs1 << 1) + (rs1[31] ? rs2 : 0)` |

El campo `funct7` de `emad` y `devk` es `00kkkkk`, con k en los bits 4:0. La codificación deja lugar para otros k, pero el hardware implementa solo k = 5 y el decodificador revisa los 7 bits. Los valores 000, 001, 011, 110 y 111 de `funct3` quedan reservados.

La definición ejecutable es `ref/xd.py`. Si este texto y el modelo no coinciden, manda el modelo.

## 3. Especificación: las instrucciones

Los ejemplos salen de `make xd-tabla` (`docs/mediciones/xd/codificacion.txt`).

### 3.1 `emad rd, rs1, rs2, 5`

```
rd = rs2 + (rs1 >>> 5)
```

Paso de una media exponencial con alfa = 1/32 cuando la desviación ya está en un registro: `rs1` es la desviación (muestra menos estado) y `rs2` el estado. Con `rs2 = x0` es un desplazamiento aritmético de 5 a la derecha.

```
emad x3, x6, x3, 5        # .word 0x0a33418b
# rs1 = -64 (0xffffffc0), rs2 = 3264:  3264 + (-64 >>> 5) = 3264 - 2 = 3262
# rs1 = 100,              rs2 = 3264:  3264 + (100 >>> 5) = 3264 + 3 = 3267
```

### 3.2 `devk rd, rs1, rs2, 5`

```
rd = (rs1 << 5) - rs2
```

Desviación de una muestra sin escalar (`rs1`, el precio) respecto de un estado guardado por 32 (`rs2`, la media). Con `rs2 = x0` es un desplazamiento de 5 a la izquierda, o sea multiplicar por 32.

```
devk x6, x5, x3, 5        # .word 0x0a32d30b
# rs1 = 100, rs2 = 3264:  (100 << 5) - 3264 = 3200 - 3264 = -64 (0xffffffc0)
# rs1 = 105, rs2 = 3264:  (105 << 5) - 3264 = 3360 - 3264 = 96
```

Con `devk` y `emad` el estimador completo de un tick son dos instrucciones: `devk x6, x5, x3, 5` antes de decidir y `emad x3, x6, x3, 5` después.

### 3.3 `mulstep rd, rs1, rs2`

```
rd = (rs1 << 1) + (rs1[31] ? rs2 : 0)
```

Un paso de multiplicación por suma y desplazamiento, con el bit más significativo primero. El multiplicador de n bits se carga en los n bits altos de `rs1`, con el resto en cero, y `rs2` es el multiplicando. Después de n pasos sobre el mismo registro, `rd` vale multiplicador por `rs2`, siempre que `rs2` sea menor que 2^(32 - n). Todo el estado del producto viaja en `rs1`, así que cada hilo puede tener el suyo en curso.

```
mulstep x7, x7, x8        # .word 0x0083a38b
# rs1 = 0xc0000000, rs2 = 1000:  0x80000000 + 1000 = 0x800003e8
# rs1 = 0x40000000, rs2 = 1000:  0x80000000 + 0    = 0x80000000
# ocho pasos con rs1 = 63 << 24 y rs2 = 255:  16065 = 63 * 255
```

### 3.4 Ensamblador

`tools/pochoasm.py` conoce los tres mnemónicos (`docs/ensamblador.md`, sección 10). Están apagados por defecto, porque el Espino base y el segmentado los tratarían como instrucción ilegal en silencio: se habilitan con la directiva `.extension xd` en el fuente o con la opción `--xd`. El ensamblador rechaza cualquier k distinto de 5.

## 4. Lo básico: por qué estas tres

La regla de reversión guarda la media por 32 (S) para no perder precisión, y en cada tick hace dos cosas con ella:

1. La desviación: `dev = 32 p - S`. El Espino no tiene desplazamientos (el shifter completo no cabe en la FPGA), así que 32 p se arma con cinco sumas. Con la resta son 6 instrucciones.
2. El paso de la media: `S = S + (dev >>> 5)`. Sin desplazamiento a la derecha, `sw/trade.s` lo hace multiplicando por 8 con tres sumas, guardando en memoria y leyendo el segundo byte. Son 8 instrucciones, con un store y un load.

Las dos cosas son un desplazamiento por una constante seguido de una suma o una resta. En hardware, un desplazamiento por una constante no necesita compuertas: se implementa solo con cableado. Basta con que el operando A del sumador de la ALU pueda venir desplazado, y eso es lo único que agrega la extensión.

`mulstep` tiene la misma forma (desplazar uno a la izquierda y sumar) y cuesta muy poco una vez que existe el multiplexor. Sirve para la contabilidad (acciones por precio). En la sección 9 está la discusión de si llega o no al bitstream de competencia.

Por qué no un `ema` de una sola instrucción (`rd = rs2 + ((rs1 - rs2) >>> k)`): encadena una resta, un desplazamiento y una suma en un ciclo y necesita un segundo sumador. La factibilidad lo midió sobre el segmentado: 60 a 167 celdas contra 37 de `emad`. Además el programa necesita la desviación de todas formas, para decidir.

Por qué k fijo en 5: con un solo k el desplazamiento se implementa solo con cableado. Con k de 0 a 31 hace falta un desplazador delante del sumador, que cuesta unas 160 celdas más y baja la frecuencia máxima (medido en la factibilidad sobre el segmentado: de 51,6 a 39,2 MHz). El alfa de `max_media` y de las tres bandas del fondo es 1/32.

## 5. Cómo está construida

Dos módulos pequeños en `rtl/espino_core/espino_xd.v` y cuatro puntos de contacto en `rtl/espino_core/espino_barrel_core.v`. El decodificador, la ALU y la unidad de carga del Espino no se tocaron.

```
        etapa R                                etapa X
  instrucción ──► espino_decoder ─┐
        │                         ├─► registros ──► sel A = 3 ──┐
        └───────► espino_xd_dec ──┘   R → X                     ▼
                  (emad, devk,                  rs1 ─► espino_xd_opa ─► operando A ─┐
                   mulstep)                            (rs1>>>5, rs1<<5, rs1<<1)    ├─► sumador de la ALU ─► rd
                                                rs2 ─► (cero si mulstep y          ─┘
                                                        rs1[31] = 0)   operando B
```

1. **Etapa R, `espino_xd_dec`.** Mira la palabra que sale de la memoria y dice si es `emad`, `devk` o `mulstep`: compara el opcode, `funct3` y los 7 bits de `funct7`. Para el decodificador del Espino esas palabras son ilegales (no escriben, no piden el bus, no saltan).
2. **Etapa R, el core.** Si es una de las tres, lo que se registra hacia X cambia en cuatro señales: selección 3 del operando A (que el Espino no usa), `rs2` como operando B, suma (resta en `devk`) y escritura de `rd`. Para cualquier otra palabra se registra lo que dice el decodificador, sin cambios.
3. **Etapa X, `espino_xd_opa`.** Entrega el operando A desplazado: `rs1 >>> 5`, `rs1 << 5` o `rs1 << 1`. Elige con el `funct3` de la instrucción que está en X. Además avisa cuando `mulstep` necesita el operando B en cero (`rs1[31] = 0`).
4. **Etapa X, el core.** El multiplexor del operando A tiene una entrada más y el operando B se anula con ese aviso. El resultado sale del sumador de la ALU por el mismo camino que un `add`.

Lo que no cambió: el avance del pipeline, el banco de registros, el bus de datos y el próximo contador de programa. No hay registros nuevos.

**El error más fácil de cometer.** En el barrel, en cada ciclo hay una instrucción de un hilo distinto en cada etapa. La palabra que sale de la memoria mientras una instrucción está en X es de otro hilo. `espino_xd_opa` tiene que mirar el `funct3` registrado (`instr_x`) y no el que sale de la memoria. Es la mutación `MUTA_XD_HILO` de la sección 8.

**Subconjuntos.** El parámetro `Xd` del core es una máscara: bit 0 `emad`, bit 1 `devk`, bit 2 `mulstep`. Con `Xd = 0` los dos módulos no se instancian. Si una instrucción no está, su palabra es ilegal y su rama del multiplexor desaparece.

## 6. Costo y timing

`make xd-timing` (`docs/mediciones/xd/timing.txt`). SoC completo, `nextpnr-ice40 --hx1k --package vq100 --freq 25`, semillas 1 a 10. La FPGA tiene 1280 celdas y 16 BRAM.

| Subconjunto | Celdas | Agrega | Libres | BRAM | Fmax mínima, mediana y máxima (MHz) | Cierran a 25 MHz |
|-------------|--------|--------|--------|------|--------------------------------------|------------------|
| Barrel sin extensión (control) | 938 | | 342 | 12 | 52,11, 55,94 y 59,82 | 10 de 10 |
| `emad` | 966 | +28 | 314 | 12 | 50,68, 54,05 y 55,74 | 10 de 10 |
| `devk` | 961 | +23 | 319 | 12 | 51,08, 54,60 y 56,01 | 10 de 10 |
| `emad` y `devk` | 990 | +52 | 290 | 12 | 48,92, 51,08 y 54,05 | 10 de 10 |
| `mulstep` | 954 | +16 | 326 | 12 | 50,89, 54,22 y 56,10 | 10 de 10 |
| `emad` y `mulstep` | 990 | +52 | 290 | 12 | 48,23, 49,80 y 51,91 | 10 de 10 |
| `devk` y `mulstep` | 1002 | +64 | 278 | 12 | 50,73, 52,49 y 55,44 | 10 de 10 |
| Las tres | 1034 | +96 | 246 | 12 | 48,33, 49,33 y 51,94 | 10 de 10 |

Lectura:

- **El costo es el multiplexor.** Una instrucción sola cuesta 16 a 28 celdas: una entrada más en el operando A de 32 bits. Cada instrucción que se agrega suma otro camino de 32 bits a ese multiplexor.
- **La frecuencia baja unos 4 MHz con las tres** (de 52,1 a 48,3 de mínima), porque el operando A tiene un nivel más de lógica delante del sumador. Sigue cerrando con el doble de lo que se necesita: la ruta más lenta mide 20,7 ns de los 40 del período.
- **El ruido del conteo** es de unas 10 celdas entre síntesis del mismo circuito (decisión T6). El control de esta tabla da 938 y `make barrel-timing` de P1 dio 933, con la misma lógica: la prueba formal B1 de la sección 7 demuestra que con `Xd = 0` el core es equivalente al de P1.
- **Contra la factibilidad.** El prototipo midió +90 celdas y 48,7 MHz de mínima para las tres, sin revisar `funct7`. Aquí son +96 y 48,3 revisándolo: el decodificador completo cuesta lo que el ruido.

## 7. Verificación

Tres métodos independientes, cada uno con sus controles negativos.

| Prueba | Qué demuestra | Resultado | Comando |
|--------|---------------|-----------|---------|
| Modelo | `ref/xd.py` contra las mismas fórmulas escritas de otra forma, la regla de `trade.s`, productos de 8 pasos y la codificación | 720 304 comprobaciones | `python3 ref/xd.py` |
| Módulos solos | `espino_xd_dec` con todas las combinaciones de `funct3` y `funct7`, y `espino_xd_opa` con la ALU contra el modelo, en los 8 valores de `Xd` | 49 152 comprobaciones del decodificador y 1 200 000 resultados iguales al modelo. 5 de 5 mutaciones detectadas | `make xd-tb` |
| Formal A | Cada instrucción contra su especificación, sobre el core, para cualquier programa y cualquier valor de los operandos | X1 a X5 probadas por inducción en los 7 subconjuntos | `make xd-formal` |
| Formal B | El resto del core no cambió | Equivalente al core de P1 en 1890 puntos de comparación, con `Xd = 0` y con cada subconjunto si custom-0 se reemplaza por nop | `make xd-formal` |
| Formal C | Que la prueba A sirve | 9 de 9 mutaciones dan contraejemplo | `make xd-formal` |
| Simulación | Cada hilo contra el Espino base más la especificación, instrucción por instrucción | 7 966 640 instrucciones en 20 600 programas, 93,15 % distintas en toda la campaña, cero diferencias. De ellas 1 030 081 son de la extensión. Aparte, 8 968 323 en la campaña de lazos, con 1 815 513 de la extensión | `make xd-verif` |
| Mutaciones por simulación | Que la comparación sirve | 9 de 9 detectadas, 8 de ellas por las 6 comparaciones | `make xd-mutaciones` |
| De punta a punta | Ensamblador, hardware y programa: `max_media` con `devk` y `emad` contra `ref/trader.py` | 4/4 en el testbench oficial sin modificar y 20 000 ticks idénticos a 0,1 ms y a 1 ms | `make xd-oficial` |

### 7.1 Prueba formal contra la especificación

`formal/xd/propiedades_xd.vh` se inserta en una copia del core y se prueba con SymbiYosys por inducción. La instrucción que entrega la memoria, el dato del bus y lo que entrega el banco de registros quedan libres. La especificación está escrita de nuevo dentro de las propiedades, sobre la instrucción registrada en X y con los operadores de Verilog, sin usar ninguna señal de `espino_xd.v`.

| Propiedad | Qué dice |
|-----------|----------|
| X1 | Una instrucción presente deja en el puerto de escritura del banco exactamente el valor de la fórmula, con los `rs1` y `rs2` que el banco entregó para ella |
| X2 | Escribe `rd`, y solo si `rd` no es `x0`. El registro escrito es el `rd` de esa instrucción |
| X3 | No pide el bus de datos, no salta y el hilo sigue en `pc + 4` |
| X4 | Una palabra de custom-0 que no es una instrucción presente no escribe, no pide el bus y no salta |
| X5 | Una instrucción que no es de custom-0 no usa nada de la extensión: se registra lo que dice el decodificador del Espino, la selección 3 del operando A no aparece y el operando B no se anula |

Que el resultado no dependa de las instrucciones de los otros hilos no necesita una propiedad aparte: en el ciclo en que se comprueba X1, lo que sale de la memoria es una entrada libre. Con las propiedades P6, P10 y P11 del barrel (`formal/barrel/propiedades.vh`, que se prueban en la misma corrida) queda cerrado que el valor se escribe en el contexto del hilo correcto y que los operandos son los de ese hilo.

La parte B usa los pases `equiv_make`, `equiv_simple` y `equiv_induct` de Yosys, el método de `formal/base_sin_cambios`. Compara el core de hoy con el core del commit de P1 (`0fb8ae8`), registro por registro y salida por salida, con el banco de registros como caja negra. Como control, sin reemplazar custom-0 la equivalencia falla, que es lo que tiene que pasar.

**Lo que encontró la prueba formal.** La primera versión de la propiedad X1 falló para `emad` y, a la vez, la mutación que vuelve lógico el desplazamiento pasó. El error estaba en la propiedad y no en el RTL: `rs2 + (rs1s >>> 5)` escrito en una sola expresión se evalúa sin signo en Verilog, porque un operando sin signo vuelve sin signo toda la expresión, y el desplazamiento aritmético pasa a ser lógico. Se corrigió dejando el desplazamiento en un cable propio con signo. Sirve como ejemplo de por qué una prueba se acompaña de mutaciones: sin el control negativo, "arreglar" el RTL para que pasara la propiedad habría metido el error.

### 7.2 Comparación por simulación

Es la campaña del barrel de P1 (`tb/barrel/tb_verif.sv`: cada hilo contra un Espino base, comparando contador de programa, escritura al banco, acceso al bus, los 16 registros y la memoria en cada instrucción), con un cambio: la referencia pasa a ser el Espino base más la especificación. El Espino base no hace nada con una palabra de custom-0. Cuando completa una que la especificación reconoce, el testbench calcula el resultado con la fórmula, usando los valores de `rs1` y `rs2` del banco del propio Espino base, y lo escribe en `rd` directamente en las BRAM de ese banco. La instrucción siguiente ya lee el valor nuevo.

Así los programas mezclan RV32E y la extensión, con resultados de unas que alimentan a las otras (un `devk` cuyo resultado decide un salto condicional, un producto de 8 pasos que termina como dirección de un load), y todo lo demás de la comparación sigue igual. `tools/barrel/prog_hilos.py --xd 7` genera instrucciones sueltas, con el destino igual a un operando, el par `devk` y `emad`, productos completos de 8 pasos, y palabras que casi son una instrucción (otro `funct7`, otro `funct3`) que no deben hacer nada. Las codifica el generador por su cuenta, sin pasar por el ensamblador.

Resultado de `make xd-verif` con las tres instrucciones (`docs/mediciones/xd/verificacion.txt`):

| Campaña | Programas | Instrucciones comparadas | `emad` | `devk` | `mulstep` | Custom-0 sin efecto | Diferencias |
|---------|-----------|--------------------------|--------|--------|-----------|---------------------|-------------|
| Lineal (cada programa se ejecuta una vez) | 20 600 | 7 966 640, 93,15 % distintas en toda la campaña | 216 211 | 208 315 | 605 555 | 137 816 | 0 |
| Lazos (grupos de P1, con memoria compartida, SPI y `trade.s`) | 748 | 8 968 323 | 383 623 | 383 124 | 1 048 766 | 258 105 | 0 |

Cumple el criterio 5 de la puerta de simulación (al menos 5 millones de instrucciones y más de 90 % distintas) en la configuración con la extensión. Las "custom-0 sin efecto" son palabras que casi son una instrucción y que no hicieron nada en ninguno de los dos lados.

**Lo que encontró la campaña.** Dos cosas, ninguna en el RTL de la extensión:

1. En la primera corrida todas las instrucciones nuevas fallaban: el core no escribía `rd`. La señal de escritura corregida (`rf_we_r`) estaba calculada pero el registro hacia X seguía tomando la del decodificador. Era un error de la integración, la comparación lo mostró en la primera instrucción nueva de cada programa y se corrigió antes de cualquier medición.
2. En la primera campaña completa fallaron 2 corridas de 20 600. El generador incluye palabras de custom-0 al azar entre sus "instrucciones raras", y con la extensión una de cada 340 resulta ser una instrucción válida. En esos dos programas era un `mulstep` con destino `x14`, la dirección base del SPI. Los stores siguientes de ese hilo cayeron en la tabla de arranque de otro hilo. Los dos lados hicieron lo mismo con el hilo que escribía. La diferencia apareció en el hilo cuyo código se pisó, porque en ese grupo cada Espino base de referencia corre con su propia memoria. Es un hueco del generador, del mismo tipo que el que encontró P1. Se corrigió limitando el destino de esas palabras a `x1` a `x10` y la campaña se repitió completa.

### 7.3 Qué no cubre

- **El gemelo digital modela el barrel y la extensión desde P4** (`docs/gemelo.md`, sección 7).
- **La equivalencia B compara contra el core de P1 con el banco de registros como caja negra.** El banco no cambió (no se tocó su archivo).
- **La prueba A deja libre lo que entrega el banco.** Que el banco entregue el valor que se escribió antes es del barrel y lo cubren la campaña de simulación y las propiedades P10 y P11.
- **No hay prueba formal de un producto completo de 8 pasos.** Está probado un paso, que es lo que hace el hardware. El producto se comprueba en el modelo (exhaustivo con 8 por 8 bits) y en la campaña.
- **La placa, en parte.** El 16/11 R2, que usa `emad` y `devk`, pasó en la placa la firma a 0,1 ms y la media hora sin disparo (`docs/mediciones/placa_16nov.md`). Faltan la firma de R2 a 1 ms y 10 ms y las tres firmas de R1.

## 8. Controles negativos

Nueve errores puestos a propósito, como bloques `ifdef MUTA_XD_*` que solo se activan desde la línea de comandos. Cada uno se prueba contra la prueba formal, contra la simulación y, los de `espino_xd.v`, contra el testbench de los módulos.

| Mutación | Qué rompe | Formal | Simulación | Módulos |
|----------|-----------|--------|------------|---------|
| `MUTA_XD_K` | No se revisa k: cualquier k se ejecuta con k = 5 | Contraejemplo | 5 de 6 | Detectada |
| `MUTA_XD_F7MUL` | `mulstep` no revisa `funct7` | Contraejemplo | 6 de 6 | Detectada |
| `MUTA_XD_SRL` | El desplazamiento de `emad` es lógico | Contraejemplo | 6 de 6 | Detectada |
| `MUTA_XD_K4` | `devk` desplaza 4 | Contraejemplo | 6 de 6 | Detectada |
| `MUTA_XD_BCERO` | `mulstep` suma `rs2` siempre | Contraejemplo | 6 de 6 | Detectada |
| `MUTA_XD_WE` | Las instrucciones nuevas no escriben `rd` | Contraejemplo | 6 de 6 | No aplica |
| `MUTA_XD_HILO` | El operando se elige con el `funct3` de otro hilo | Contraejemplo | 6 de 6 | No aplica |
| `MUTA_XD_ANULA` | El operando B se anula en instrucciones de RV32E | Contraejemplo | 6 de 6 | No aplica |
| `MUTA_XD_SUMA` | `devk` suma en vez de restar | Contraejemplo | 6 de 6 | No aplica |

## 9. Qué entra al bitstream de competencia

El criterio del grupo es que al bitstream entren solo las instrucciones que `sw/fondo.s` usa realmente. Ese programa se escribe en el paquete P3, así que este paquete deja las tres construidas y verificadas, cada una elegible por separado, y los 7 subconjuntos medidos y probados (decisión T58).

- `emad` y `devk` las usan los cuatro hilos: el supervisor calcula `max_media` por su cuenta y cada gestor corre una banda de la misma regla. Entran seguro.
- `mulstep` solo tiene uso si el supervisor lleva la contabilidad de la cuenta (el "espejo" del prototipo). El fondo mínimo no la necesita para decidir: su voto es todo o nada y las órdenes son idempotentes. Si P3 no la lleva, el bitstream se compila con `-DESPINO_XD_EMAD -DESPINO_XD_DEVK` (990 celdas, 48,92 MHz de mínima) y `mulstep` queda para la edición de exhibición y el ASIC.

Las demás instrucciones que estudió la factibilidad (`ema`, `srak`, los carriles de 4 por 8 bits, `divstep`, `mulc` y el periférico multiplicador) no están en `rtl/`. Sus números están en `factibilidad/d_isa/` y `factibilidad/i_integrado/` (T125).

## 10. Reglas del enunciado y riesgos

| Regla | Cumple | Comentario |
|-------|--------|------------|
| La decisión la calcula el Espino. El hardware agregado acelera partes del algoritmo | Sí | Son tres operaciones aritméticas sin estado. El programa sigue leyendo `PRICE` con `lw`, comparando con `slti` y escribiendo `DECISION` con `sw`. Ninguna recibe un precio y entrega una decisión, y ninguna guarda nada entre ticks |
| Nada de información externa ni series guardadas | Sí | No hay tablas ni memoria |
| Hardware agregado con su testbench | Sí | `tb/xd/tb_xd_mod.sv` instancia los dos módulos solos. Además formal y la campaña sobre el SoC |
| El procesador sigue siendo Espino | Sí | Las instrucciones de RV32E no cambian (formal B). Custom-0 es el opcode reservado para esto. El profesor confirmó el 16/11 que se puede modificar lo que uno quiera y que cualquier decisión de diseño es válida (T126) |
| El testbench oficial no se modifica | Sí | 4/4 sin tocarlo |

Riesgos:

1. **No cambia el patrimonio.** Las decisiones son las mismas con y sin la extensión. Lo que aporta es co-diseño medido y ciclos libres para los hilos.
2. **k cableado en 5.** Si después del 25/11 el algoritmo necesitara otro alfa, el hardware no sirve y hay que volver a las sumas. El ensamblador rechaza cualquier otro k y el core lo trata como ilegal, así que no hay forma de ejecutar otro k en silencio.
3. **Un programa con la extensión no corre en el base ni en el segmentado.** Ahí las instrucciones no hacen nada. Por eso el ensamblador exige `.extension xd`. R0 no usa la extensión.
4. **El comando del encabezado del testbench oficial no lleva definiciones.** Compila el Espino base. Si R1 compite, el valor por defecto del SoC tiene que pasar a ser el barrel con la extensión (pendiente de P5, decisión T55).
5. **La placa, en parte.** En la placa solo se comprobó R2 a 0,1 ms y la media hora sin disparo (16/11, `docs/mediciones/placa_16nov.md`). Todo lo que quiera competir pasa por la maestra el 26/11.

## 11. Cómo reproducir

Desde la raíz, con OSS CAD Suite en el `PATH`.

| Comando | Qué hace | Salida | Tiempo |
|---------|----------|--------|--------|
| `python3 ref/xd.py` | Autoprueba del modelo | pantalla | 5 s |
| `make xd-tabla` | Codificación y ejemplos | `docs/mediciones/xd/codificacion.txt` | 1 s |
| `make xd-tb` | Módulos solos contra el modelo, con mutaciones | `tb_modulos.txt` | 25 s |
| `make xd-formal` | Formal A, B y C | `formal.txt` | 15 s |
| `make xd-timing` | Celdas y timing de los 7 subconjuntos, 10 semillas | `timing.txt` | 6 min |
| `make xd-verif` | Campaña completa contra el base con la especificación | `verificacion.txt` | 8 min con 5 procesos |
| `make xd-mutaciones` | Controles negativos por simulación | `mutaciones.txt` | 1 min |
| `make xd-oficial` | Testbench oficial y 20 000 ticks, con y sin las instrucciones | `oficial.txt` | 4 min |
| `make check-xd` | Lo que corre la integración continua | | 8 min |
| `make test-asm` | Tests del ensamblador, con los de la extensión | pantalla | 1 s |

## 12. Preguntas para la defensa

1. **¿Por qué custom-0?** Es uno de los opcodes que RISC-V reserva para extensiones propias: ninguna extensión estándar lo va a ocupar. `espino_xd.v`, línea del `OPCODE_CUSTOM0`.
2. **¿Por qué no agregaron el shifter?** El completo no cabe: 1491 celdas en el base. Un desplazamiento por una constante se implementa solo con cableado. La extensión cuesta 96 celdas.
3. **¿Por qué `emad` y `devk` y no un `ema` de una instrucción?** Sección 4: un solo sumador en vez de dos, y el programa necesita la desviación igual.
4. **¿Qué pasa si el programa usa k = 4?** El ensamblador lo rechaza. Si la palabra llega igual a la memoria, el core la trata como ilegal: no hace nada. Probado formalmente (X4) y por la mutación `MUTA_XD_K`.
5. **¿Cómo saben que no rompieron RV32E?** Formal B: el core con la extensión es equivalente al de P1 en 1890 puntos cuando no hay palabras de custom-0. Y la campaña compara cada instrucción contra el Espino base.
6. **¿Contra qué se compara una instrucción que el Espino base no tiene?** Contra la fórmula de la especificación, escrita tres veces por separado: en el modelo de Python, en el testbench y en las propiedades formales. Sección 7.
7. **¿Dónde está el riesgo propio del barrel?** En mirar la instrucción de otro hilo. Sección 5 y mutación `MUTA_XD_HILO`.
8. **¿Cuánto acelera?** La respuesta de `max_media` baja de 83 a 63 ciclos en el barrel. En instrucciones, el estimador pasa de 14 a 2.
9. **¿Cambia el resultado de la competencia?** No. Sección 10, riesgo 1.
10. **¿Por qué `mulstep` y no un multiplicador?** Uno combinacional de 16 por 8 no cabe (medido en la factibilidad: 1338 celdas en el segmentado). Un paso por instrucción reutiliza el sumador, cuesta 16 celdas y no tiene estado oculto, así que cada hilo puede multiplicar sin estorbar a los otros.
