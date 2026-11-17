# Ensamblador del Espino Core (`tools/pochoasm.py`)

Este documento describe el ensamblador del proyecto, que traduce programas en assembly RV32E, como `sw/trade.s`, a archivos `.hex` que el RTL carga con `$readmemh`. Es el contrato entre el código del ensamblador, sus tests y los programas de `sw/`.

## 1. Origen y alcance

El testbench oficial del Proyecto 4 espera el comando `python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex`, pero el repositorio base del curso no trae ese archivo. Usamos el ensamblador que el grupo escribió para el Proyecto 2 y amplió en el Proyecto 3 (ahí se llamaba `assembler/asm.py`), con el nombre y la interfaz que pide el testbench. Del Proyecto 3 vienen las salidas en Verilog (`--vh` y `--rom`). En este proyecto se agregó la directiva `.org`. El punto de entrada es `tools/pochoasm.py` y los módulos están en `tools/asm/`.

Está escrito en Python 3 sin dependencias y no invoca ninguna herramienta externa, así que no hace falta instalar las herramientas de compilación de RISC-V. Por eso se eliminó `sw/Makefile` del repositorio base, que llamaba a `riscv64-unknown-elf-as`: ahora existe una sola regla para generar los `.hex`, en el `Makefile` de la raíz.

Para comprobar que el ensamblador es correcto, el repositorio base trae tres programas de ejemplo con su `.hex` ya generado (`blink`, `7seg` y `buttons_leds`). `tools/asm/tests/test_golden.py` los ensambla y verifica que salen idénticos, palabra por palabra, a los originales.

Las instrucciones propias de la extensión de la ISA (`emad`, `devk` y `mulstep`, en el espacio custom-0) también se ensamblan aquí. Están apagadas por defecto y se describen en la sección 10.

## 2. Uso

```
python3 tools/pochoasm.py ENTRADA.s [-o SALIDA.hex] [-D NOMBRE=VALOR ...] [--allow-shifts] [--xd] [--vh SALIDA.vh] [--rom SALIDA.v]
```

| Opción                  | Efecto                                                                                     |
|-------------------------|--------------------------------------------------------------------------------------------|
| `ENTRADA.s`             | Archivo de entrada (obligatorio).                                                          |
| `-o`, `--output`        | Archivo `.hex` de salida. Por defecto, la entrada con extensión `.hex`.                    |
| `-D`, `--define`        | `NOMBRE=VALOR`: fija una constante y pisa el `.equ` del mismo nombre. Se puede repetir.    |
| `--allow-shifts`        | Acepta `sll`, `srl`, `sra`, `slli`, `srli` y `srai`.                                       |
| `--xd`                  | Habilita la extensión xd (`emad`, `devk`, `mulstep`), igual que la directiva `.extension xd`. Ver la sección 10. |
| `--vh SALIDA.vh`        | Escribe además el programa como include de Verilog: `PROG_WORDS` y la función `prog_word(idx)`. |
| `--rom SALIDA.v`        | Escribe además el módulo `pochoco_rom`, una ROM combinacional con el programa (un `case` por dirección). |

Ejemplos:

```bash
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex
python3 tools/pochoasm.py sw/trade.s -o build/trade_prueba.hex -D COMPRAR_63=0x41
```

El valor de `-D` acepta los mismos literales que el ensamblador: decimal, `0x` y `0b`. Si el nombre no existe como `.equ` en el archivo, `-D` lo define de todos modos, de modo que se puede usar para pasar constantes que el programa solo lee. Un `-D` mal formado (sin `=`, o con valor no numérico) termina con error y código de salida 1. Al terminar, el ensamblador imprime cuántas palabras generó.

**Por qué los shifts se rechazan por defecto.** La ALU del Espino Core, para ahorrar LUTs, ejecuta `sll`, `srl` y `sra` (y sus variantes con inmediato) como una suma. El decodificador los reconoce bien, pero el resultado es el de un `add`. Si el ensamblador los emitiera sin avisar, se obtendría un binario que ensambla sin errores y corre mal, que es el peor tipo de falla porque no deja pistas. Por eso el ensamblador los rechaza con un mensaje explicativo, y `--allow-shifts` existe solo para quien sepa lo que hace, por ejemplo con una ALU propia. Mientras el core no tenga shifter, un desplazamiento a la izquierda se hace sumando un registro consigo mismo (`add x7, x7, x7`).

## 3. Sintaxis aceptada

- **Una instrucción por línea.**
- **Comentarios** con `#`, hasta el fin de la línea. Una línea que solo tiene comentario, o que está en blanco, se ignora.
- **Etiquetas** con la forma `nombre:`. Pueden ir solas en su línea, y entonces apuntan a la instrucción siguiente, o delante de una instrucción en la misma línea. Un nombre es una letra o `_` seguida de letras, dígitos o `_`.
- **Mayúsculas y minúsculas.** Los mnemónicos, los registros y las directivas no distinguen mayúsculas (`ADDI X1, X2, 5` equivale a `addi x1, x2, 5`). Las etiquetas y los nombres de `.equ` sí las distinguen.
- **Operandos** separados por comas.
- **Acceso a memoria** con el formato `desplazamiento(registro)`, por ejemplo `lw x9, 8(x2)` o `sw x9, OFF_LEDS(x2)`. El desplazamiento puede ser un literal o una constante `.equ`, y si se omite vale 0: `jalr x0, (x1)`.
- **Literales numéricos:** decimal (`75`, `-585`), hexadecimal con prefijo `0x` (`0x04C11DB7`) y binario con prefijo `0b` (`0b1010`). Aceptan signo `+` o `-`.

## 4. Registros

El core implementa RV32E, que tiene 16 registros, de `x0` a `x15`. Se aceptan además los nombres ABI:

| ABI          | Registro | ABI  | Registro |
|--------------|----------|------|----------|
| `zero`       | x0       | `s1` | x9       |
| `ra`         | x1       | `a0` | x10      |
| `sp`         | x2       | `a1` | x11      |
| `gp`         | x3       | `a2` | x12      |
| `tp`         | x4       | `a3` | x13      |
| `t0`         | x5       | `a4` | x14      |
| `t1`         | x6       | `a5` | x15      |
| `t2`         | x7       | `s0`, `fp` | x8 |

Pedir `x16` o superior es un **error** ("x16 no existe: RV32E solo tiene x0-x15"), no un truncamiento silencioso. Los campos de registro de la instrucción tienen 5 bits, así que `x16` cabría en la codificación, y un programa con ese error ensamblaría sin quejas pero no significaría lo que el autor pensó. Un nombre que no es ni `xN` ni ABI también es error.

## 5. Directivas

| Directiva                    | Efecto                                                                                          |
|------------------------------|-------------------------------------------------------------------------------------------------|
| `.equ NOMBRE, valor`         | Define una constante. El valor es un literal u otra constante ya definida. No ocupa memoria.    |
| `.word v1, v2, ...`          | Emite una o más palabras de 32 bits literales. El valor puede ser un literal, una constante o una etiqueta. |
| `.org dirección`             | Avanza hasta esa dirección de byte rellenando con palabras en cero. La dirección debe ser múltiplo de 4, no puede ser menor que la actual ni pasar de 0x800. |
| `.extension xd`              | Habilita las instrucciones de la extensión xd desde esa línea en adelante. No ocupa memoria. Cualquier otro nombre es error. Ver la sección 10. |
| `.section`, `.text`, `.global` | Se aceptan e ignoran. Existen para que el mismo archivo se lea bien con otras herramientas.   |

Cualquier otra directiva es un error. Un `.equ` con un nombre repetido también es error, salvo que el nombre venga fijado por `-D`, caso en que el `.equ` del archivo se ignora. Las constantes deben definirse antes de usarse.

`sw/trade.s` termina con `.org 0x800`, así que `trade.hex` tiene siempre las 512 palabras de la RAM. Hay dos razones. La primera es que en simulación una palabra que no aparece en el `.hex` queda indefinida, mientras que en la placa queda en cero: con el relleno las dos parten con la misma memoria. La segunda es que `icebram`, la herramienta que cambia el programa dentro de un bitstream sin volver a sintetizar, necesita un `.hex` del tamaño completo de la memoria. Se eligió una directiva dentro del archivo, y no una opción de la línea de comandos, porque el comando del testbench oficial (`python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex`) no lleva opciones.

## 6. Etiquetas, inmediatos y pseudo-instrucciones

### Dos pasadas

El ensamblador recorre el archivo dos veces.

1. **Primera pasada.** Va con un contador de dirección que parte en 0. Cada instrucción real ocupa 4 bytes. Cada etiqueta se anota en la tabla de símbolos con la dirección actual y cada `.equ` con su valor. Para saber cuánto ocupa cada línea, se calcula el largo de cada pseudo-instrucción (`li` puede ocupar 4 u 8 bytes, según el valor).
2. **Segunda pasada.** Con la tabla completa, codifica cada línea. En este punto una etiqueta ya tiene dirección aunque esté más adelante en el archivo, y así se resuelven las **referencias hacia adelante**: un `beq x9, x0, fin` puede aparecer antes de `fin:` porque en la primera pasada `fin` ya quedó registrada. Para un salto o bifurcación, el desplazamiento codificado es `dirección de la etiqueta - dirección de la instrucción`.

`li` comparte una sola función entre ambas pasadas, así que el tamaño que se reserva y el que se genera no pueden discrepar.

### Rangos de inmediato por formato

| Uso                                     | Rango permitido                     |
|-----------------------------------------|-------------------------------------|
| Formato I (`addi`, `andi`, ..., `lw`, `jalr`) y formato S (`sw`) | -2048 a 2047   |
| `shamt` de shifts (con `--allow-shifts`) | 0 a 31                             |
| Bifurcaciones (`beq`, `bne`, ...)       | desplazamiento par, de -4096 a 4094 bytes |
| `jal`, `j`                              | desplazamiento par, de -1.048.576 a 1.048.574 bytes |
| `lui`, `auipc`                          | 0 a 0xFFFFF (20 bits)               |
| `li`                                    | -2^31 a 2^32 - 1 (cabe en 32 bits)  |

Un valor fuera de rango produce un error con el número de línea, en vez de truncarse.

### Pseudo-instrucciones

Se traducen a instrucciones reales:

| Pseudo            | Expansión                       |
|-------------------|---------------------------------|
| `nop`             | `addi x0, x0, 0`                |
| `mv rd, rs`       | `addi rd, rs, 0`                |
| `not rd, rs`      | `xori rd, rs, -1`               |
| `neg rd, rs`      | `sub rd, x0, rs`                |
| `j etiqueta`      | `jal x0, etiqueta`              |
| `jr rs`           | `jalr x0, 0(rs)`                |
| `ret`             | `jalr x0, 0(x1)`                |
| `beqz rs, etiq`   | `beq rs, x0, etiq`              |
| `bnez rs, etiq`   | `bne rs, x0, etiq`              |
| `bltz rs, etiq`   | `blt rs, x0, etiq`              |
| `la rd, etiqueta` | `addi rd, x0, dirección`, y la dirección debe caber en -2048..2047 |
| `li rd, valor`    | una o dos instrucciones, ver abajo |

### Expansión de `li` y corrección de signo

`li rd, valor` carga una constante de 32 bits. Según el valor, se expande así:

1. Si el valor cabe en 12 bits con signo (-2048 a 2047): `addi rd, x0, valor`.
2. Si los 12 bits bajos son cero: `lui rd, valor >> 12`.
3. En el caso general, dos instrucciones: `lui rd, hi` y `addi rd, rd, lo`.

El caso general tiene una sutileza. `lui` deja los 20 bits altos en su lugar y los 12 bajos en cero, y `addi` suma un inmediato de 12 bits **con signo**. Si el bit 11 del valor deseado es 1, el inmediato de `addi` se interpreta como negativo, o sea resta 4096 de más. Para compensar hay que sumar 1 a la parte alta:

```
hi = (valor + 0x800) >> 12
lo = valor - (hi << 12)          # queda entre -2048 y 2047
```

Sumar `0x800` antes de desplazar equivale a redondear al múltiplo de 4096 más cercano, y así `lo` siempre cabe con signo en 12 bits.

**Ejemplo completo: `li x4, 0x04C11DB7`.**

1. El valor no cabe en 12 bits y sus 12 bits bajos (`0xDB7`) no son cero, así que se usa el caso general.
2. El bit 11 de `0xDB7` es 1 (`0xDB7 = 1101 1011 0111`), así que hace falta la corrección.
3. `valor + 0x800 = 0x04C11DB7 + 0x00000800 = 0x04C125B7`.
4. `hi = 0x04C125B7 >> 12 = 0x04C12`. Sin la corrección habría sido `0x04C11`.
5. `lo = 0x04C11DB7 - 0x04C12000 = -0x249 = -585`.
6. Resultado:

```
lui  x4, 0x04C12
addi x4, x4, -585
```

7. Verificación: `lui` deja `0x04C12000`, y `addi` le suma -585 (`-0x249`): `0x04C12000 - 0x249 = 0x04C11DB7`, que es el valor pedido.

Las dos instrucciones se codifican como `04c12237` y `db720213`. `tools/asm/tests/test_pseudo.py` verifica este caso.

## 7. Instrucciones soportadas

Las instrucciones base de RV32I que el ensamblador codifica, listadas abajo. No hay `ecall`, `ebreak`, `fence` ni instrucciones de CSR. Los mnemónicos están en `tools/asm/isa.py`.

| Formato | Instrucciones                                                        |
|---------|----------------------------------------------------------------------|
| R       | `add`, `sub`, `slt`, `sltu`, `xor`, `or`, `and`                      |
| R (shift, requiere `--allow-shifts`) | `sll`, `srl`, `sra`                     |
| I (aritméticas) | `addi`, `slti`, `sltiu`, `xori`, `ori`, `andi`               |
| I (shift, requiere `--allow-shifts`) | `slli`, `srli`, `srai`                  |
| I (carga)       | `lb`, `lh`, `lw`, `lbu`, `lhu`                               |
| I (salto)       | `jalr`                                                       |
| S       | `sb`, `sh`, `sw`                                                     |
| B       | `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu`                           |
| U       | `lui`, `auipc`                                                       |
| J       | `jal`                                                                |
| R en custom-0 (requiere `.extension xd` o `--xd`) | `emad`, `devk`, `mulstep`  |

Más las pseudo-instrucciones de la sección 6.

## 8. Validaciones y suite de tests

El ensamblador rechaza con un mensaje de error, indicando el número de línea, los casos siguientes: registro fuera de x0 a x15 o desconocido, shift sin `--allow-shifts`, instrucción de la extensión sin habilitar o con `k` distinto de 5, extensión desconocida, mnemónico o directiva desconocidos, etiqueta o constante repetida o no definida, inmediato fuera de rango, número incorrecto de operandos, operando de memoria mal formado, salto a dirección impar o fuera de alcance, y programa de más de 512 palabras.

La suite se corre con `make test-asm` y tiene **124 tests**, repartidos así:

| Archivo                          | Tests | Qué verifica                                                                                                  |
|----------------------------------|-------|---------------------------------------------------------------------------------------------------------------|
| `tests/test_golden.py`           | 3     | Ensambla `blink.s`, `7seg.s` y `buttons_leds.s` y compara palabra por palabra con los `.hex` originales.      |
| `tests/test_formats.py`          | 8     | Codificaciones calculadas a mano que los `.hex` de referencia no cubren: `sub`, `slt`, `blt`, `bge`, `bltu`, `bgeu`, `jalr`, `auipc`. |
| `tests/test_pseudo.py`           | 16    | Las once pseudo-instrucciones simples y cinco casos de `li`, incluida la corrección de signo (con el ejemplo de la sección 6). |
| `tests/test_directives.py`       | 10    | `.equ` (hex, binario, sensibilidad a mayúsculas), `.word` (incluida una etiqueta hacia adelante), directivas ignoradas y mayúsculas. |
| `tests/test_defines.py`          | 3     | `-D` pisa el `.equ`, `-D` sin `.equ` en el archivo, y valor no numérico es error.                              |
| `tests/test_validation.py`       | 28    | Todas las validaciones del párrafo anterior, con casos límite en los rangos.                                   |
| `tests/test_roundtrip.py`        | 5     | Ensamblar, desensamblar con `tools/asm/disasm.py` y volver a ensamblar da lo mismo, para todas las instrucciones y para los tres ejemplos. Detecta errores de codificación que la comparación con archivos de referencia no ve. |
| `tests/test_org.py`              | 9     | `.org`: relleno con ceros, relleno hasta las 512 palabras, etiquetas después del relleno y los cuatro errores (retroceder, dirección impar, fuera de la RAM, código después de llenar la RAM). |
| `tests/test_image.py`            | 5     | Las salidas `--vh` y `--rom` contienen las mismas palabras que el `.hex`, en el mismo orden, con el desensamblado como comentario. |
| `tests/test_xd.py`               | 37    | La extensión xd: las tres palabras de referencia, las 16 x 16 x 16 combinaciones de registros de cada instrucción con ida y vuelta por el desensamblador, rechazo de `k` distinto de 5, `k` por `.equ` y por `-D`, las dos formas de habilitarla, los errores de la directiva, las salidas `--vh` y `--rom`, y que `sw/trade.s` sigue dando `sw/trade.hex` byte a byte. |
| **Total**                        | **124**|                                                                                                               |

## 9. Ejemplo completo de traducción: `sw x9, OFF_LEDS(x2)`

Con una constante `.equ OFF_LEDS, 4`, la línea

```
sw   x9, OFF_LEDS(x2)
```

guarda el registro `x9` en la dirección `x2 + 4`. Como `x2` vale `0x8000_0000` (la base de periféricos), la **dirección efectiva es `0x8000_0004`**, que es el registro LEDS.

`sw` es de formato **S**. Su codificación, de izquierda a derecha, es:

```
 31        25 24  20 19  15 14  12 11       7 6      0
+------------+------+------+------+----------+--------+
| imm[11:5]  | rs2  | rs1  |funct3| imm[4:0] | opcode |
+------------+------+------+------+----------+--------+
```

El inmediato de 12 bits va partido en dos trozos, de modo que `rs1`, `rs2` y `funct3` quedan en la misma posición que en otros formatos.

Campo por campo:

| Campo       | Bits    | Valor                    | Binario   |
|-------------|---------|--------------------------|-----------|
| `imm[11:5]` | 31 a 25 | `4 = 0b000000000100`, bits 11 a 5 | `0000000` |
| `rs2`       | 24 a 20 | `x9`, el dato a guardar  | `01001`   |
| `rs1`       | 19 a 15 | `x2`, la base            | `00010`   |
| `funct3`    | 14 a 12 | `sw` (palabra)           | `010`     |
| `imm[4:0]`  | 11 a 7  | `4`, bits 4 a 0          | `00100`   |
| `opcode`    | 6 a 0   | store                    | `0100011` |

Concatenando de izquierda a derecha:

```
0000000 01001 00010 010 00100 0100011
```

En grupos de 4 bits:

```
0000 0000 1001 0001 0010 0010 0010 0011
 0    0    9    1    2    2    2    3
```

El resultado es **`0x00912223`**.

Se puede verificar con el propio ensamblador:

```
$ mkdir -p build
$ printf '.equ OFF_LEDS, 4\nsw x9, OFF_LEDS(x2)\n' > build/ejemplo.s
$ python3 tools/pochoasm.py build/ejemplo.s -o build/ejemplo.hex && cat build/ejemplo.hex
build/ejemplo.s -> build/ejemplo.hex (1 palabras, 4 bytes)
00912223
```

El mensaje se copia tal como lo imprime el ensamblador, que escribe siempre "palabras" en plural; el archivo generado no cambia por eso.

## 10. Extensión xd: instrucciones propias en custom-0

El grupo agregó tres instrucciones al Espino barrel, en el opcode custom-0 de RISC-V (`0001011`, 0x0B), que el estándar reserva para extensiones propias. La especificación completa, con la semántica exacta y el hardware que las ejecuta, está en `docs/extension_isa.md`. Esta sección cubre solo lo que hace el ensamblador con ellas.

### Sintaxis y codificación

Las tres usan el formato R, con los mismos campos y las mismas posiciones que `add`. Los registros son los de RV32E (`x0` a `x15` o sus nombres ABI).

| Sintaxis                | funct3 | funct7    | Semántica                                |
|-------------------------|--------|-----------|------------------------------------------|
| `emad rd, rs1, rs2, k`  | `100`  | `00kkkkk` | `rd = rs2 + (rs1 >>> k)`                 |
| `devk rd, rs1, rs2, k`  | `101`  | `00kkkkk` | `rd = (rs1 << k) - rs2`                  |
| `mulstep rd, rs1, rs2`  | `010`  | `0000000` | `rd = (rs1 << 1) + (rs1[31] ? rs2 : 0)`  |

```
 31        25 24  20 19  15 14  12 11   7 6      0
+------------+------+------+------+------+--------+
|   funct7   | rs2  | rs1  |funct3|  rd  | opcode |
+------------+------+------+------+------+--------+
```

En `emad` y `devk` el cuarto operando, `k`, va en los bits 4 a 0 del funct7 (bits 29 a 25 de la palabra), y los bits 6 y 5 del funct7 son cero. `k` puede ser un literal o una constante de `.equ` o de `-D`, y se resuelve igual que cualquier inmediato.

Ejemplo, `emad x3, x6, x3, 5`:

| Campo    | Bits    | Valor          | Binario   |
|----------|---------|----------------|-----------|
| `funct7` | 31 a 25 | `k = 5`        | `0000101` |
| `rs2`    | 24 a 20 | `x3`           | `00011`   |
| `rs1`    | 19 a 15 | `x6`           | `00110`   |
| `funct3` | 14 a 12 | `emad`         | `100`     |
| `rd`     | 11 a 7  | `x3`           | `00011`   |
| `opcode` | 6 a 0   | custom-0       | `0001011` |

El resultado es `0x0a33418b`. Las tres palabras de referencia, que `tests/test_xd.py` verifica, son:

| Instrucción            | Palabra      |
|------------------------|--------------|
| `emad x3, x6, x3, 5`   | `0x0a33418b` |
| `devk x6, x5, x3, 5`   | `0x0a32d30b` |
| `mulstep x7, x7, x8`   | `0x0083a38b` |

### Solo k = 5

El hardware no tiene un desplazador variable: `k` está cableado en 5, y una palabra con otro valor en ese campo es una instrucción ilegal para el core. Por eso el ensamblador rechaza cualquier `k` distinto de 5 en `emad` y `devk`, en vez de emitir una palabra que el core no ejecutaría. El operando se escribe igual, y no se deja implícito, para que el fuente diga qué desplazamiento se está usando y para que la codificación no cambie si algún día el hardware admite otros valores.

### Cómo se habilita

Las tres instrucciones están apagadas por defecto. La razón es la misma que con los shifts: el Espino base y el segmentado tratan una palabra custom-0 como instrucción ilegal y no hacen nada con ella, sin avisar. Un programa que las usara y se cargara en uno de esos cores ensamblaría sin errores y correría mal. Solo el Espino barrel compilado con la extensión las ejecuta.

Hay dos formas equivalentes de habilitarlas:

- La directiva `.extension xd` en el fuente. Debe aparecer antes del primer uso, rige desde esa línea en adelante y no ocupa memoria. Es la forma preferida, porque deja escrito en el propio programa que necesita la extensión, y el comando para ensamblarlo no cambia.
- La opción `--xd` en la línea de comandos, que equivale a tener la directiva en la primera línea.

Usar ambas a la vez, o repetir la directiva, no es error. Habilitar la extensión no cambia la codificación de ninguna otra instrucción: `sw/trade.s` produce el mismo `sw/trade.hex` con y sin `--xd`.

```bash
python3 tools/pochoasm.py sw/fondo.s -o sw/fondo.hex          # con .extension xd en el fuente
python3 tools/pochoasm.py build/prueba.s -o build/prueba.hex --xd
```

### Errores

Todos llevan el número de línea, como el resto.

| Caso                                              | Mensaje                                                                 |
|---------------------------------------------------|-------------------------------------------------------------------------|
| Uso sin habilitar, o directiva después del uso    | `'emad': instrucción de la extensión xd (custom-0) sin habilitar: agrega '.extension xd' antes del primer uso o usa --xd. Solo el Espino barrel compilado con la extensión la ejecuta; el base y el segmentado la tratan como instrucción ilegal` |
| `k` distinto de 5 en `emad` o `devk`              | `'emad': k = 4 no está permitido: el core tiene k cableado en 5`         |
| `.extension` con otro nombre                      | `extensión desconocida: 'otra' (la única disponible es 'xd')`            |
| `.extension` sin nombre o con más de uno          | `.extension requiere un nombre de extensión`                             |
| Número incorrecto de operandos                    | `'emad' espera 4 operando(s), recibió 3` (3 operandos en `mulstep`)      |
| Registro `x16` o superior                         | `x16 no existe: RV32E solo tiene x0-x15`                                 |

### Desensamblador y salidas en Verilog

`tools/asm/disasm.py` reconoce las tres instrucciones y entrega el mismo texto que se escribió (`emad x3, x6, x3, 5`), así que la prueba de ida y vuelta de la sección 8 también las cubre. Como el texto desensamblado no trae la directiva, para volver a ensamblarlo hay que usar `--xd`.

Una palabra con opcode custom-0 que no sea exactamente una de las tres formas válidas (otro funct3, `k` distinto de 5 o bits 6 y 5 del funct7 distintos de cero en `emad` y `devk`, funct7 distinto de cero en `mulstep`) se trata como cualquier otra palabra desconocida, porque para el core es una instrucción ilegal. En las salidas `--vh` y `--rom` eso significa que el comentario de esa dirección muestra `.word 0x...` en lugar de un mnemónico. Esas dos salidas no vuelven a ensamblar nada: solo usan el desensamblador para los comentarios, y funcionan igual con programas que usan la extensión.
