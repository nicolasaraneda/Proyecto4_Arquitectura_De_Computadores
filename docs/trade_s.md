# `sw/trade.s`, variante solo software

Documento de estudio del programa que corre en la placa. Parte de lo básico y llega al detalle de cada bloque. Responde lo que pide el punto 3.2 del enunciado: estructura del ciclo principal, uso de registros y memoria, punto fijo, operaciones que Espino no tiene, equivalencia con la referencia y mediciones por tick.

Archivos relacionados:

| Archivo | Qué es |
|---------|--------|
| `sw/trade.s` | El programa. |
| `sw/trade.hex` | El programa ensamblado, 512 palabras. Es lo que queda dentro del bitstream. |
| `ref/trader.py` | Referencia en Python, con las mismas operaciones. |
| `ref/market.py` | Mercado de la maestra, porte del testbench. |
| `tools/equiv.sh` | Compara el `decisiones.csv` del testbench con el de la referencia. |
| `tb/tb_cpi.sv` | Mide IC, ciclos y CPI por tick. |
| `docs/mediciones/ticks_software.txt` | Resultado de `make medir-ticks`. |

## 1. Qué hace el programa

En cada tick la maestra manda un precio `p` entre 1 y 255. El programa mantiene una media exponencial del precio y compara el precio con esa media:

- si el precio está más de 4 unidades bajo la media, quiere estar adentro (con acciones);
- si el precio volvió a quedar sobre la media, quiere estar afuera (con caja);
- si no pasa ninguna de las dos cosas, se queda como estaba.

Esa es la regla base de reversión a la media. La idea es que la serie de práctica tiende a volver a su nivel reciente: razón de varianza 0,77 a 10 ticks y 0,53 a 100 ticks, en los 20 bloques de 1000 ticks (`make hallazgos`). Comprar cuando el precio cayó respecto a su media y vender cuando la recupera gana justo cuando eso se cumple.

### Cómo decide la cantidad

No decide una cantidad variable. La orden es siempre por 63 acciones, el máximo:

- adentro: `0x7F`, acción 01 (comprar) y cantidad 63;
- afuera: `0xBF`, acción 10 (vender) y cantidad 63.

La maestra recorta la compra a lo que alcanza con la caja y la venta a las acciones que se tienen, y una orden que queda en cero no se ejecuta ni paga comisión (tarea `ejecutar` de `tb/tb_proyecto_4.sv`). Por eso repetir "comprar 63" tick tras tick no cuesta nada una vez que la caja se acabó. El programa expresa una posición objetivo (todo adentro o todo afuera) y la maestra hace el resto. Esto tiene dos ventajas: el programa no necesita llevar la contabilidad, y no hay forma de que su contabilidad se desincronice de la oficial.

El límite de 63 acciones por orden hace que entrar o salir tome varios ticks. En la serie de práctica el precio va de 72 a 190 (media 128): con la caja inicial de 10 000 se compran unas 80 acciones, o sea dos órdenes en dos ticks seguidos y dos comisiones. Cuando el patrimonio crece hacen falta más: al final de la serie de práctica se llegan a tener 339 acciones, que son seis órdenes para entrar y seis para salir. En total la regla base entra 75 veces y ejecuta 388 órdenes. Este costo de entrada es un dato para el frente del algoritmo.

## 2. Punto fijo

La media se guarda multiplicada por 32:

```
S = 32 * media          (5 bits de fracción)
```

`S` ocupa 13 bits: va de 32 (media 1) a 8160 (media 255). El precio escalado `32 p` tiene el mismo rango. La desviación `dev = 32 p - S` tiene signo y queda entre -8128 y 8128, así que todo cabe holgado en los 32 bits de un registro.

La actualización de la media exponencial con alfa = 1/32 es

```
media = media + (p - media) / 32
S     = S + ((32 p - S) >> 5)        (lo mismo, multiplicado por 32)
```

El desplazamiento es aritmético: redondea hacia abajo también cuando `32 p - S` es negativo. Los umbrales se comparan en la misma escala:

| Condición | En unidades de precio | En la escala del programa |
|-----------|-----------------------|---------------------------|
| Entrar | p < media - 4 | `dev < -128` |
| Salir | p > media | `dev > 0`, o sea `dev >= 1` |

## 3. Operaciones que Espino no tiene

La ALU de Espino tiene deshabilitados los desplazamientos (`sll`, `srl`, `sra` se ejecutan como una suma) y no hay multiplicación ni división. El programa necesita tres cosas que normalmente usarían un shift.

**Multiplicar por 32.** Cinco sumas: `x6 = p + p`, y después cuatro veces `x6 = x6 + x6`.

**Desplazar a la derecha un número con signo.** Se evita con una identidad. Como `32 p` es múltiplo de 32:

```
(32 p - S) >> 5  =  p + ((-S) >> 5)  =  p - ceil(S / 32)  =  p - ((S + 31) >> 5)
```

`S + 31` nunca es negativo, así que solo queda desplazar a la derecha un número positivo.

**Desplazar a la derecha 5 bits un número positivo.** Espino sí puede leer un byte suelto de la memoria (`lbu`), y leer el segundo byte de una palabra es lo mismo que desplazarla 8 bits a la derecha y quedarse con 8 bits. Entonces:

```
x >> 5  =  (x * 8) >> 8
```

El programa multiplica `S + 31` por 8 con tres sumas, guarda la palabra en la memoria (`sw x7, TMP(x0)`) y lee su segundo byte (`lbu x7, TMP_BYTE1(x0)`). El resultado cabe en un byte porque `(8160 + 31) * 8 = 65 528`, menor que 65 536. `ref/test_ref.py` revisa la identidad para todos los valores de `S` entre 0 y 8160.

El costo de esta parte es 6 instrucciones y 13 ciclos por tick. Es el candidato natural para la extensión de la ISA (frente C).

**Decidir sin saltos.** Las dos comparaciones se hacen con `slti`, que deja 0 o 1 en un registro, y la posición se actualiza con `or` y `and`:

```
entrar   = (dev < -128)           slti x7, x6, -128
no_salir = (dev < 1)              slti x9, x6, 1
pos      = (pos | entrar) & no_salir
```

El byte de decisión se arma con aritmética: `0 - pos` vale 0 o `0xFFFFFFFF`, el `andi` con -64 deja 0 o -64, y sumar `0xBF` da `0xBF` (vender 63) o `0x7F` (comprar 63). El esclavo SPI solo toma los 8 bits bajos.

No hay ningún salto que dependa del precio. El único salto condicional del programa es el del sondeo de `STATUS`.

## 4. Estructura del ciclo principal

| Paso | Instrucciones | Qué hace |
|------|---------------|----------|
| 1. Esperar | `lw`, `andi`, `beqz` | Sondea `STATUS[0]` hasta que haya un precio nuevo. |
| 2. Leer | `lw` | Lee `PRICE`. La lectura baja la bandera de precio nuevo. |
| 3. Predecir | 5 `add`, `sub` | `dev = 32 p - S`. |
| 4. Decidir | 2 `slti`, `or`, `and`, `sub`, `andi`, `addi` | Actualiza `pos` y arma el byte. |
| 5. Escribir | `sw` | Un solo store a `DECISION`, con la decisión definitiva. |
| 6. Estado | `addi`, 3 `add`, `sw`, `lbu`, `add`, `sub`, `j` | Actualiza `S` y vuelve a esperar. |

La media se actualiza después de escribir la decisión, para que la respuesta salga lo antes posible. La decisión usa la media anterior al precio nuevo, igual que la referencia.

**Primer precio.** El bloque `primero` es una copia de los pasos 1 a 3 que además deja `S = 32 p`. Con eso `dev = 0` en el primer tick, no se opera, y la media parte en el primer precio que el programa ve, cualquiera sea. Después salta a `decidir` y sigue por el camino normal.

### Registros

| Registro | Uso |
|----------|-----|
| `x2` | Base del esclavo SPI, `0x8001_0000`. |
| `x3` | `S`, la media por 32. |
| `x4` | `pos`: 0 afuera, 1 adentro. |
| `x5` | `p`, el último precio. |
| `x6` | `32 p`, y después `dev`. |
| `x7`, `x9` | Temporales. |
| `x8` | Byte de decisión. |

### Memoria

El programa ocupa 40 palabras. El único dato en memoria es `TMP`, la última palabra de la RAM (`0x7FC`), que se usa para el desplazamiento. El `.org 0x800` del final rellena `trade.hex` con ceros hasta las 512 palabras (ver `docs/ensamblador.md`, sección 5).

## 5. Equivalencia con la referencia

`make equiv` corre una copia del testbench oficial en la que solo cambian `PERIODO_NS`, `NTICKS` y el nombre del archivo de salida, y compara su `decisiones.csv` con el que genera `ref/trader.py`, byte a byte (`cmp`). El archivo trae, por tick, el precio, el byte de decisión, la caja, las acciones y el patrimonio.

| Corrida | Simulador | Ticks | Resultado |
|---------|-----------|-------|-----------|
| Ronda 3, 0,1 ms (`make equiv-r3`, ejecución manual) | Icarus | 20 000 | Idénticos. Patrimonio 26 795. |
| Rondas 3, 2 y 1 (`make equiv-gemelo-20k`) | Gemelo digital | 20 000 cada una | Idénticos. Patrimonio 26 795, 27 306 y 27 306. |
| Ronda 2, 1 ms | Icarus | 200 | Idénticos. |
| Ronda 1, 10 ms | Icarus | 20 | Idénticos. |
| Ronda 3, 0,1 ms | Verilator | 20 000 | Idénticos. Patrimonio 26 795. |
| Ronda 2, 1 ms | Verilator | 20 000 | Idénticos. Patrimonio 27 306. |
| Ronda 1, 10 ms (`make equiv-largo`) | Verilator | 20 000 | Idénticos. Patrimonio 27 306. |
| Una serie de cada familia sintética y un remuestreo (`make equiv-series`) | Verilator | 13 series de 2000 | Idénticos. |

Control negativo: si la referencia no modela los precios que se pierden en el reset, los archivos difieren desde la línea 3.

### Por qué el patrimonio no es 27 062

La regla base da 27 062 sobre la serie completa cuando el programa ve todos los precios (`python3 ref/trader.py tb/practica.csv`). En el testbench da 26 795 a 0,1 ms y 27 306 a 1 ms. La diferencia es el reset largo de la placa (decisión T3): dura 4095 ciclos, 164 us, y el testbench manda el primer precio a los 4 us. A 0,1 ms el programa no ve los precios de los ticks 0 y 1, y a 1 ms y 10 ms no ve el del tick 0. La media parte entonces en otro precio y las primeras operaciones cambian.

`ref/trader.py` modela esto con `ticks_perdidos(periodo_ns)`: los primeros precios no se entregan a la estrategia, y la maestra sigue leyendo `0x00` (mantener) hasta que el programa responde al primer precio que sí ve. En la competencia la placa está encendida antes del primer precio y no se pierde ninguno.

## 6. Mediciones por tick

`make medir-ticks` corre `tb/tb_cpi.sv` con la serie de práctica al período de cada ronda. Mide dos ventanas que parten cuando llega el precio (`byte_done` del esclavo SPI):

- **Respuesta:** hasta la escritura de `DECISION`. Es lo que mide el testbench oficial y lo que se compara con el presupuesto.
- **Tick completo:** hasta que el programa vuelve a sondear `STATUS`. Incluye la actualización de la media.

| Ventana | IC promedio | IC peor caso | Ciclos promedio | Ciclos peor caso | CPI | Tiempo promedio | Tiempo peor caso |
|---------|-------------|--------------|-----------------|------------------|-----|-----------------|------------------|
| Respuesta | 19,5 | 21 | 41,0 | 44 | 2,10 | 1,64 us | 1,76 us |
| Tick completo | 28,5 | 30 | 63,0 | 66 | 2,21 | 2,52 us | 2,64 us |

Los valores son los mismos en las tres rondas, porque el trabajo por tick no depende del período. Contra el T de cada ronda:

| Ronda | T | Presupuesto (ciclos) | Peor caso de respuesta | Uso del presupuesto | Tick completo, peor caso, como fracción de T |
|-------|---|----------------------|------------------------|---------------------|----------------------------------------------|
| 1 | 10 ms | 249 762 | 44 | 0,018 % | 0,026 % |
| 2 | 1 ms | 24 762 | 44 | 0,18 % | 0,26 % |
| 3 | 0,1 ms | 2 262 | 44 | 1,9 % | 2,6 % |

### De dónde sale cada ciclo

Costo por instrucción en el Espino base: 2 ciclos, más 1 en cada load y 1 en cada salto tomado (`make cpi` comprueba que este modelo coincide con lo medido, con diferencia de 0 ciclos).

| Bloque | Instrucciones | Ciclos | Parte del tick completo |
|--------|---------------|--------|-------------------------|
| Sondeo que detecta el precio (`lw`, `andi`, `beqz` no tomado) | 3 | 7 | 12 % |
| Leer `PRICE` | 1 | 3 | 5 % |
| `32 p` y `dev` | 6 | 12 | 20 % |
| Decidir y armar el byte | 7 | 14 | 24 % |
| Escribir `DECISION` | 1 | 2 | 3 % |
| Actualizar la media | 8 | 17 | 29 % |
| Volver al sondeo (`j`) | 1 | 3 | 5 % |
| Total sin la espera | 27 | 58 | |

El mínimo de la respuesta son 38 ciclos (los primeros cinco bloques). Lo que falta para los 38 a 44 medidos es la espera del sondeo.

### Por qué hay peor caso si el programa no tiene saltos

El algoritmo tarda siempre lo mismo. Lo que varía es en qué punto del lazo de sondeo está el programa cuando llega el precio. Una vuelta del lazo dura 8 ciclos (`lw` 3, `andi` 2, `beqz` tomado 3), y la bandera puede levantarse en cualquiera de ellos. En el testbench el período son 2500 ciclos, que no es múltiplo de 8 (sobran 4), así que la fase va rotando y la respuesta toma exactamente cuatro valores con la misma frecuencia: 38, 40, 42 y 44 ciclos. El promedio es 41 y el peor caso 44.

Además el testbench cambia `SCLK` justo en un flanco del reloj de 25 MHz, y el simulador resuelve esa coincidencia siempre igual. En la placa la maestra es asíncrona respecto a nuestro reloj, así que la respuesta real puede variar un ciclo más o menos.

### El peor caso sobre todas las fases

El testbench oficial solo recorre cuatro de las ocho fases del lazo. Con el gemelo digital (`docs/gemelo.md`) se barrieron las ocho, moviendo el inicio de la primera transacción de a 40 ns, con las dos formas de resolver la coincidencia de `SCLK`:

| Caso | Respuesta (ciclos) | Tick completo (ciclos) |
|------|--------------------|------------------------|
| Régimen, todas las fases | 37 a 44 | 59 a 66 |
| Primer precio (pasa por `primero`: un `mv` y un `j` más, 5 ciclos) | 42 a 49 | 64 a 71 |

El peor caso real de respuesta es **49 ciclos**, y ocurre una sola vez, con el primer precio. En el testbench oficial ese tick cae en una fase favorable y por eso informa 44. Frente a los 2 262 ciclos disponibles en la ronda más rápida es el 2,2 %.

## 7. Cómo reproducir

```bash
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex   # ensamblar
make tb                # testbench oficial sin modificar: 4/4
make test-ref          # pruebas del mercado y de la referencia
python3 ref/trader.py tb/practica.csv                   # tabla del punto 3.1
make -j4 equiv         # equivalencia con la referencia: gemelo y Verilator
make equiv-r3          # los 20 000 ticks con Icarus, ejecución manual (unos 13 minutos)
make cpi               # CPI y modelo de costo (rápido)
make medir-ticks       # mediciones por tick en las tres rondas
```
