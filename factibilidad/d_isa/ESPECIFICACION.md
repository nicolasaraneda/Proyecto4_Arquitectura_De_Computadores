# Especificación de la extensión de la ISA en custom-0

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Este documento define las instrucciones propuestas: codificación, semántica exacta y un ejemplo de cada una. La definición ejecutable es `ref/xd.py`: si este texto y el modelo no coinciden, manda el modelo, porque es contra él que se compara el RTL. Los ejemplos numéricos salen de `make ejemplos` (`mediciones/ejemplos.txt`) y la tabla de palabras de `make tabla` (`mediciones/codificacion.txt`).

Es una propuesta de un estudio de factibilidad. Nada de esto está en `rtl/` ni en `tools/` del repositorio.

## 1. Convenciones

- Todas las instrucciones usan el opcode custom-0 de RISC-V, `0001011` (0x0B), y el formato R:

| Bits | 31:25 | 24:20 | 19:15 | 14:12 | 11:7 | 6:0 |
|------|-------|-------|-------|-------|------|-----|
| Campo | `funct7` | `rs2` | `rs1` | `funct3` | `rd` | `0001011` |

- Los registros son los de RV32E, `x0` a `x15`. Escribir en `x0` no tiene efecto y leerlo entrega cero, igual que en el resto de la ISA.
- Todas son de un solo ciclo de ejecución, sin estado oculto y sin acceso a memoria: el resultado depende solo de `rs1`, `rs2` y los campos de la instrucción. No modifican el contador de programa ni generan excepciones. En el Espino base cuestan 2 ciclos y en el segmentado 1, lo mismo que una instrucción de la ALU (medido, `mediciones/ticks_xd.txt`).
- `>>>` es el desplazamiento aritmético a la derecha (copia el bit de signo) y `<<` el desplazamiento a la izquierda. Las sumas y restas de 32 bits dan la vuelta (módulo 2^32).
- `funct3` elige el grupo:

| `funct3` | Grupo | `funct7` |
|----------|-------|----------|
| 000 | `ema` | `00kkkkk`: k en los bits 4:0 |
| 001 | carriles de 4 x 8 bits | operación en los bits 3:0 |
| 010 | producto y cociente | operación en los bits 1:0 |
| 011 | `srak` | `00kkkkk` |
| 100 | `emad` | `00kkkkk` |
| 101 | `devk` | `00kkkkk` |
| 110 | reservado para `kal2` (`docs/producto_2x2.md`) | |
| 111 | reservado | |

- Los bits de `funct7` que una instrucción no usa deben ir en cero. El hardware no los revisa.

### Subconjuntos y codificaciones no implementadas

La codificación es una sola, pero el hardware se sintetiza con un subconjunto (definiciones `XD_*`, sección 6). Lo que pasa con una palabra que no está en el subconjunto depende de cómo se integró su grupo:

- Si el grupo completo no está, el decodificador marca la instrucción como ilegal y no escribe `rd`, igual que con cualquier opcode desconocido. Es lo que hace el Espino sin la extensión.
- Si el grupo está pero el valor de k no (por ejemplo `emad` con k = 6 en un core sintetizado solo con k = 5), **el hardware no lo detecta**: ejecuta la instrucción con uno de los k que sí tiene. Con un solo k cableado ignora el campo; con el conjunto de 4 a 7 mira solo los bits 1:0; con el de 0 a 7, los bits 2:0.
- En los carriles con unidad aparte (`xd_simd8`), una operación que no se incluyó entrega la suma o la resta por carril, sin garantía. Con los carriles en el sumador de la ALU (`xd_alu`), una operación que no se incluyó se marca como ilegal.

Por eso el ensamblador tiene que conocer el subconjunto del core y rechazar lo que no esté (sección 9 del README).

## 2. Media exponencial

Las cuatro instrucciones llevan k en `funct7[4:0]`, con `funct7[6:5] = 00`. La codificación admite k de 0 a 31. El hardware implementa uno de cuatro conjuntos, elegido al sintetizar: solo k = 5, k de 4 a 7, k de 0 a 7, o k de 0 a 31. El costo de cada conjunto está en el README. El valor 5 es el alfa = 1/32 de la regla base, que según `docs/algoritmo.md` es también el mejor compromiso entre los que probó el frente A.

### 2.1 `ema rd, rs1, rs2, k`

```
rd = rs2 + ((rs1 - rs2) >>> k)
```

Paso completo de una media exponencial con alfa = 2^-k: `rs1` es la muestra y `rs2` el estado, los dos en la misma escala. Equivale exactamente a `sub t, rs1, rs2; srai t, t, k; add rd, rs2, t`. Con `rs2 = x0` es un desplazamiento aritmético de `rs1`.

Es la fórmula del encargo, `rd = rs1 + ((rs2 - rs1) >>> k)`, con los nombres de los operandos cambiados: el estado va en `rs2` y la muestra en `rs1`, para que la resta sea `rs1 - rs2`, que es la que la ALU del core ya hace. Así la integración barata no necesita un restador propio.

Ejemplo: precio 100 y media 102, con el estado escalado por 32 (S = 3264) y la muestra también (32 p = 3200 en `x10`).

```
ema x3, x10, x3, 5        # .word 0x0a35018b
# rs1 = 3200, rs2 = 3264:  3264 + ((3200 - 3264) >>> 5) = 3264 - 2 = 3262
```

### 2.2 `emad rd, rs1, rs2, k`

```
rd = rs2 + (rs1 >>> k)
```

El mismo paso cuando la desviación (muestra menos estado) ya está en un registro: `rs1` es la desviación y `rs2` el estado. `ema(a, b, k)` es igual a `emad(a - b, b, k)`. Con `rs2 = x0` es `srak`. Se propone porque `trade.s` ya calcula la desviación para decidir, y porque es un desplazamiento cableado más una suma: usa el sumador de la ALU y no encadena resta, desplazamiento y suma en el mismo ciclo.

```
emad x3, x6, x3, 5        # .word 0x0a33418b
# rs1 = -64 (0xffffffc0), rs2 = 3264:  3264 + (-64 >>> 5) = 3262
```

### 2.3 `devk rd, rs1, rs2, k`

```
rd = (rs1 << k) - rs2
```

La desviación de una muestra sin escalar (`rs1`, el precio) respecto de un estado con k bits de fracción (`rs2`). Con `rs2 = x0` es un desplazamiento a la izquierda por k. Reemplaza las cinco sumas con que `trade.s` calcula 32 p, y la resta.

```
devk x6, x5, x3, 5        # .word 0x0a32d30b
# rs1 = 100, rs2 = 3264:  (100 << 5) - 3264 = -64 (0xffffffc0)
```

Con `devk` y `emad` el tick completo del estimador son dos instrucciones: `devk x6, x5, x3, 5` antes de decidir y `emad x3, x6, x3, 5` después (`sw/trade_media.s`).

### 2.4 `srak rd, rs1, k`

```
rd = rs1 >>> k
```

Desplazamiento aritmético a la derecha por una constante. `rs2` debe ser `x0`. Es la alternativa mínima: el paso de la media se escribe `srak t, dev, k; add S, S, t`. Queda en la especificación como referencia de costo. `emad` con `rs2 = x0` hace lo mismo.

```
srak x7, x6, 5            # .word 0x0a03338b
# rs1 = -64:  -64 >>> 5 = -2 (0xfffffffe)
```

## 3. Carriles de 4 x 8 bits

Un registro de 32 bits lleva cuatro carriles de 8 bits. El carril i ocupa los bits 8i+7 a 8i. Ningún acarreo pasa de un carril al siguiente. La operación va en `funct7[3:0]` y `funct7[6:4] = 000`. En la tabla, a y b son el carril de `rs1` y el de `rs2`, entre 0 y 255.

| `funct7[3:0]` | Instrucción | Resultado por carril |
|---------------|-------------|----------------------|
| 0 | `padd8 rd, rs1, rs2` | (a + b) mod 256 |
| 1 | `psub8 rd, rs1, rs2` | (a - b) mod 256 |
| 2 | `pcmpltu8 rd, rs1, rs2` | 0xFF si a < b sin signo, 0x00 si no |
| 3 | `pcmplt8 rd, rs1, rs2` | 0xFF si a < b con signo (complemento a dos de 8 bits), 0x00 si no |
| 4 | `pminu8 rd, rs1, rs2` | el menor de a y b, sin signo |
| 5 | `pmaxu8 rd, rs1, rs2` | el mayor de a y b, sin signo |
| 6 | `paddus8 rd, rs1, rs2` | min(a + b, 255): suma saturada sin signo |
| 7 | `psubus8 rd, rs1, rs2` | max(a - b, 0): resta saturada sin signo |
| 8 | `pbcast8 rd, rs1` | `rs1[7:0]` en los cuatro carriles. `rs2` debe ser `x0` |
| 9 | `pmovmsk8 rd, rs1` | `rd[i]` = bit 7 del carril i de `rs1`, para i de 0 a 3. `rd[31:4]` = 0. `rs2` debe ser `x0` |
| 10 a 15 | reservadas | |

La comparación entrega una máscara por carril (0xFF o 0x00) y no un bit por carril. La máscara se combina directamente con `and`, `or` y `xori` de RV32E, que ya operan bit a bit y por lo tanto por carril, y sirve para elegir entre dos valores por carril. `pmovmsk8` la pasa a un bit por carril cuando hace falta. La variante de un bit por carril se construyó y se midió (`CMP_BIT` en `xd_simd8`): ahorra 20 celdas, el doble del ruido del conteo, y obliga a otra instrucción para volver a la máscara. Los precios y las medias son valores sin signo de 8 bits, así que la comparación principal es la sin signo. La comparación con signo es opcional.

Ejemplos, todos con `rs1 = 0x10ff8001` y `rs2 = 0x20017f02` (carriles 3 a 0: 0x10, 0xff, 0x80, 0x01 contra 0x20, 0x01, 0x7f, 0x02):

| Instrucción | Palabra | `rd` |
|-------------|---------|------|
| `padd8 x7, x8, x9` | 0x0094138b | 0x3000ff03 |
| `psub8 x7, x8, x9` | 0x0294138b | 0xf0fe01ff |
| `pcmpltu8 x7, x8, x9` | 0x0494138b | 0xff0000ff |
| `pcmplt8 x7, x8, x9` | 0x0694138b | 0xffffffff |
| `pminu8 x7, x8, x9` | 0x0894138b | 0x10017f01 |
| `pmaxu8 x7, x8, x9` | 0x0a94138b | 0x20ff8002 |
| `paddus8 x7, x8, x9` | 0x0c94138b | 0x30ffff03 |
| `psubus8 x7, x8, x9` | 0x0e94138b | 0x00fe0100 |
| `pbcast8 x7, x8` con `rs1 = 0x12345664` | 0x1004138b | 0x64646464 |
| `pmovmsk8 x7, x8` con `rs1 = 0xff0000ff` | 0x1204138b | 0x00000009 |

Uso previsto: evaluar cuatro bandas con el mismo precio. Con las cuatro medias en `x10`, las cuatro bandas en `x11` y las cuatro posiciones como máscaras en `x4` (`sw/bandas_carriles.s`):

```
pbcast8  x6, x5            # el precio en los cuatro carriles
psubus8  x7, x10, x11      # umbral = media - banda, con piso en 0
pcmpltu8 x7, x6, x7        # entrar = precio < umbral
pcmpltu8 x9, x10, x6       # salir = media < precio
or       x4, x4, x7
xori     x9, x9, -1
and      x4, x4, x9        # pos = (pos | entrar) & ~salir
pmovmsk8 x8, x4            # un bit por estrategia
```

## 4. Producto y cociente

La operación va en `funct7[1:0]` y `funct7[6:2] = 00000`. En un pipeline sin detenciones no puede haber una instrucción de varios ciclos, así que el producto y el cociente se hacen con una instrucción de un paso que el programa repite. Todo el estado del cálculo viaja en `rs1`: no hay registros ocultos, y por eso cada hilo del barrel puede tener un producto en curso sin estorbar a los demás.

### 4.1 `mulstep rd, rs1, rs2` (`funct7[1:0] = 00`)

```
rd = (rs1 << 1) + (rs1[31] ? rs2 : 0)
```

Un paso de multiplicación por suma y desplazamiento, con el bit más significativo primero. El multiplicador de n bits se carga en los n bits altos de `rs1`, con el resto en cero. `rs2` es el multiplicando. Después de n pasos, `rd` = multiplicador x `rs2`, siempre que `rs2 < 2^(32 - n)`.

Para la contabilidad el multiplicador es el precio (8 bits, 8 pasos) y el multiplicando las acciones, que pueden tener hasta 24 bits.

```
mulstep x7, x7, x8        # .word 0x0083a38b
# un paso con rs1 = 0xc0000000 y rs2 = 1000:  0x80000000 + 1000 = 0x800003e8
# ocho pasos con rs1 = 63 << 24 y rs2 = 255:  63 * 255 = 16065
```

### 4.2 `divstep rd, rs1, rs2` (`funct7[1:0] = 01`)

```
{R, Q} = rs1          R = bits 31:8 (24 bits), Q = bits 7:0
D      = rs2[23:0]
T      = {R, Q[7]}    25 bits: el resto parcial desplazado
si T >= D:  rd = {(T - D)[23:0], Q[6:0], 1}
si no:      rd = {T[23:0],       Q[6:0], 0}
```

Un paso de división con restauración. Partiendo de `rs1 = N`, con `N < 256 D`, después de 8 pasos los 8 bits bajos son el cociente `N div D` y los 24 altos el resto `N mod D`. Si `N >= 256 D` el cociente no cabe en 8 bits y el resultado no es válido. Con `D = 0` el resultado tampoco tiene sentido (el precio nunca es 0).

En la contabilidad se usa para la compra recortada, `(caja - comisión) div p`: el cociente es menor que 63 cuando hay recorte, y el resto es la caja que queda.

```
divstep x7, x7, x8        # .word 0x0283a38b
# ocho pasos con rs1 = 9995 (caja 10000 menos comisión 5) y rs2 = 180:
#   rd = 0x00005f37: cociente 55 (0x37) y resto 95 (0x5f)
```

### 4.3 `mulc rd, rs1, rs2` (`funct7[1:0] = 10`)

```
rd = rs1[AW-1:0] * rs2[7:0]        sin signo, extendido con ceros
```

Producto combinacional angosto en un solo ciclo. `AW` es el ancho del multiplicando y se fija al sintetizar: se evaluaron 8 y 16. Queda en la especificación como alternativa medida: con `AW = 16` no cabe en la FPGA.

```
mulc x7, x7, x8           # .word 0x0483a38b
# rs1 = 63, rs2 = 255:  16065
```

## 5. Periférico multiplicador serial (alternativa a `mulstep`)

No es una instrucción. Es un periférico mapeado en memoria, evaluado como alternativa. En la copia del SoC queda en `0x8002_0000` (bit 17 de la dirección), sin tocar el mapa del esclavo SPI ni el de `pochoco_periph`.

| Dirección | Registro | Acceso | Contenido |
|-----------|----------|--------|-----------|
| 0x8002_0000 | `MULA` | escritura | multiplicando, bits 23:0 |
| 0x8002_0004 | `MULB` | escritura | multiplicador, bits 7:0. La escritura parte el producto |
| 0x8002_0008 | `MULP` | lectura | producto de 32 bits |
| 0x8002_000C | `MULS` | lectura | bit 0 = ocupado |

Hace un paso de `mulstep` por ciclo. El producto queda en el registro 8 flancos después del flanco en que se escribe `MULB`. La lectura es registrada: una lectura de `MULP` cuya petición llega al bus 9 ciclos o más después de la de esa escritura entrega el producto, y una pedida antes entrega un valor parcial. Escribir `MULB` con un producto en curso parte de nuevo. Tiene estado (un producto en curso): si varios hilos lo comparten, solo uno puede usarlo a la vez.

## 6. Subconjuntos y definiciones de síntesis

Cada instrucción se incluye con una definición que se pasa a la síntesis o a la simulación de la copia del core (`core/`). Sin ninguna, el core es el original.

| Definición | Incluye | Cómo se integra |
|------------|---------|-----------------|
| `XD_EMA=c` | `ema` | unidad aparte (`xd_ema`), con restador y sumador propios |
| `XD_EMA=c` y `XD_EMAALU` | `ema` | usa la resta de la ALU y agrega un sumador |
| `XD_EMAD=c` | `emad` | sumador de la ALU, con el operando A desplazado (`xd_opa`) |
| `XD_DEVK=c` | `devk` | sumador de la ALU, con el operando A desplazado |
| `XD_SRAK=c` | `srak` | unidad aparte (`xd_srak`), por el multiplexor de escritura |
| `XD_SIMD=m` | carriles | unidad aparte (`xd_simd8`) |
| `XD_SIMDALU=m` | carriles | en el sumador de la ALU (`xd_alu` reemplaza a `espino_alu`) |
| `XD_MULSTEP` | `mulstep` | unidad aparte, con sumador propio |
| `XD_MULSTEPALU` | `mulstep` | sumador de la ALU |
| `XD_DIVSTEP` | `divstep` | unidad aparte, con restador propio de 26 bits |
| `XD_MULC=AW` | `mulc` | unidad aparte |
| `XD_MULMMIO` | periférico | `xd_mul_mmio` en `pochoco_soc` |

- `c` es el conjunto de k: 0 solo k = 5, 2 k de 4 a 7, 3 k de 0 a 7, 5 k de 0 a 31.
- `m` es una máscara. En `XD_SIMD`: 1 `pcmplt8`, 2 `pminu8` y `pmaxu8`, 4 `paddus8` y `psubus8`, 8 `pbcast8`, 16 `pmovmsk8`, 32 comparación de un bit por carril (variante evaluada y no elegida). Con 0 quedan `padd8`, `psub8` y `pcmpltu8`. En `XD_SIMDALU` solo existen los bits 4 y 8: esa integración no tiene `pcmplt8`, `pminu8`, `pmaxu8` ni `pmovmsk8`.
