# Producto 2x2 en punto fijo: diseño y costo

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Este documento cubre solo el diseño y el costo. La instrucción no está en el SoC ni en el ensamblador. Lo que existe y se puede correr es el modelo de referencia, el generador del hardware de coeficientes fijos, la versión con multiplicadores, un testbench que compara las tres cosas y el script que mide el costo.

```
make tb-mv2x2       # las tres implementaciones contra el modelo (segundos)
make costo-mv2x2    # testbench, costo en la FPGA y costo en GF180 (un minuto y medio)
```

Los resultados quedan en `docs/mediciones/mv2x2_costo.txt`.

## 1. Para qué sirve

La regla base estima el nivel del precio con una media exponencial: un solo estado. El estimador de dos estados separa el precio en dos partes:

- un nivel lento `m`, que se mueve como un paseo aleatorio, y
- una componente transitoria `u`, que vuelve a cero con un factor `phi` por tick.

Lo que se observa es `p = m + u`, redondeado a un entero. La ganancia de una estrategia de reversión viene de `u`: si la transitoria está muy abajo, el precio debería recuperarse.

El filtro de Kalman da la mejor estimación lineal de `m` y `u` a partir de los precios. En general su ganancia cambia en cada paso, pero con parámetros constantes converge en pocos ticks a un valor fijo `(k1, k2)`. Ese es el filtro en estado estacionario, y su actualización por tick es:

```
e  = p - m - phi u        innovación: lo que el precio trae de nuevo
m' = m + k1 e
u' = phi u + k2 e
```

Si se define `d = p - m`, las dos últimas líneas son un producto de una matriz de 2x2 por un vector:

```
[ m' - m ]   [ k1    -k1 phi      ] [ d ]
[ u'     ] = [ k2    phi (1 - k2) ] [ u ]
```

Esa matriz `G` es constante. El kernel del estimador es una resta, un producto 2x2 y una suma.

En la escalera de co-diseño de la clase 7 los peldaños son extensión de la ISA, pipeline, instrucciones a medida y SIMD empaquetado. Este es el peldaño siguiente: el registro lleva un vector empaquetado y la instrucción le aplica una matriz.

## 2. Especificación

### Formato de los datos

El estado va empaquetado en un registro de 32 bits, en dos carriles de 16:

| Bits | Campo | Formato |
|------|-------|---------|
| 31:16 | `u`, componente transitoria | con signo, 8 bits de fracción (Q7.8): de -128 a 127,996 |
| 15:0 | `m`, nivel | sin signo, 8 bits de fracción (Q8.8): de 0 a 255,996 |

El precio es un entero de 8 bits. Los coeficientes de `G` son enteros con `S` bits de fracción.

### Semántica

```
d   = (p << 8) - m
dm  = (g00 d + g01 u) >> S        desplazamiento aritmético: redondea hacia abajo
un  = (g10 d + g11 u) >> S
m'  = saturar(m + dm, 0, 65535)
u'  = saturar(un, -32768, 32767)
rd  = {u', m'}
```

Los productos y las sumas se hacen con precisión completa y solo se trunca al final. La definición ejecutable es `paso()` en `ref/mv2x2.py`. Las dos versiones de hardware calculan exactamente esto.

### Codificación propuesta

Instrucción de tipo R en custom-0. El `funct3` es provisional hasta que exista la especificación completa de la extensión.

```
kal2 rd, rs1, rs2

 31      25 24  20 19  15 14 12 11   7 6       0
| 0000000 |  rs2 |  rs1 | 110 |  rd  | 0001011 |
```

- `rs1`: estado empaquetado `{u, m}`.
- `rs2`: precio en los 8 bits bajos. El resto se ignora.
- `rd`: estado nuevo.

Ejemplo: `kal2 x5, x5, x6` se codifica `0x0062E28B`.

### Cómo se usa

```
# s0 = estado {u, m}, a0 = precio recién leído, s1 = {umbral, 0}
kal2  s0, s0, a0        # un paso del estimador
slt   t0, s0, s1        # t0 = 1 si u < umbral
```

La transitoria va en el carril alto a propósito. Una comparación con signo de 32 bits entre `{u, m}` y `{umbral, 0}` la decide el carril alto, y si los carriles altos son iguales da falso porque `m` nunca es menor que cero. Entonces `slt` compara `u` con el umbral sin desempaquetar nada, que sin shifter costaría un store y un load.

## 3. Alternativas de interfaz

| Alternativa | Qué es | Por qué no es la principal |
|-------------|--------|----------------------------|
| `kal2`, instrucción con el paso completo | La de la sección 2. La resta `p - m` y la suma `m + dm` van dentro. | Es la elegida. |
| `mv2x2`, producto 2x2 genérico | `rd = M x`, con el vector en `rs1` y la matriz en `rs2` como cuatro coeficientes de 8 bits. | Más general, pero el programa tendría que armar `{u, d}` y separar `{u', dm}`. Sin shifter eso es un store y un load por carril, y se pierde casi todo lo que la instrucción ahorra. Los coeficientes de 8 bits además limitan la precisión de `k1`. |
| Periférico MMIO | El estado vive en el periférico y se actualiza al llegar cada precio. El core lee `m` y `u`. | Sirve y es la forma barata en la FPGA (sección 6), pero cada lectura es un load de 3 ciclos y hay que preguntar al ayudante si cumple la regla de no reemplazar al procesador. |

## 4. Las dos versiones de hardware

### Coeficientes fijos, para la FPGA

`tools/gen_mv2x2.py` recibe los parámetros del modelo, calcula `k1` y `k2`, cuantiza y escribe un módulo combinacional. Multiplicar por una constante es sumar copias desplazadas de la entrada, y un desplazamiento fijo es solo cableado. Se usan dígitos con signo canónicos, que permiten restar: 7 se escribe 8 - 1 y cuesta un sumador en vez de dos.

Hay dos formas, y dan el mismo resultado bit a bit:

- **Directa.** Cuatro productos por constante, uno por coeficiente.
- **Factorizada.** `G` es una matriz de rango 1 más una diagonal: `G = [k1; k2] [1, -phi] + diag(0, phi)`. La innovación `e = d - phi u` se calcula una vez y se usa en las dos filas. Son tres productos por constante en vez de cuatro, y cada constante (`phi`, `k1`, `k2`) tiene la mitad de los bits que los coeficientes de `G`.

Las ganancias quedan fijas al sintetizar. Cambiarlas exige un bitstream nuevo.

### Multiplicadores reales, para la edición ASIC

`rtl/exhibicion/mv2x2_mult.v` recibe los cuatro coeficientes como entradas y usa cuatro multiplicadores de 17 bits por el ancho del coeficiente. Con cuatro registros de coeficientes el programa puede cambiar la matriz mientras corre. Eso permite cosas que la versión fija no:

- que la guardia de régimen cambie las ganancias cuando detecta que la serie dejó de revertir,
- usar la ganancia variable de los primeros ticks, antes de que el filtro llegue al estado estacionario,
- reajustar los parámetros el día de la competencia escribiendo cuatro constantes, sin sintetizar.

## 5. Verificación

`tb/tb_mv2x2.sv` aplica 20 000 vectores por matriz: las combinaciones de valores extremos de `m`, `u` y el precio, estados al azar y una trayectoria con el estado realimentado. Compara la versión factorizada, la directa y la de multiplicadores (con los mismos coeficientes en sus entradas) contra `ref/mv2x2.py`.

```
PASS tb_mv2x2: 20000 vectores por matriz, las tres implementaciones coinciden con ref/mv2x2.py
```

Falta la equivalencia formal entre las dos versiones y contra la especificación. Corresponde hacerla con SymbiYosys cuando la instrucción entre al diseño.

## 6. Costo medido

La fila "calibrada" usa los coeficientes del estimador ajustado a la serie de práctica (`docs/algoritmo.md`, sección 4.1): `phi = 1 - 1/32 - 1/128`, `K1 = 1/2 + 1/8` y `K2 = 1/8 + 1/16`. Con 7 bits de fracción son exactos: 123, 80 y 24. Las demás filas usan coeficientes de ejemplo, de un modelo con parámetros puestos a mano, y sirven para ver cómo cambia el costo con la precisión y con la cantidad de términos de las constantes.

Hay una diferencia con la referencia del algoritmo: `candidatos.Trader` con `est=1` trunca después de cada desplazamiento, porque así lo haría el programa en assembly, y `kal2` hace las sumas con precisión completa y trunca una sola vez. Los resultados pueden diferir en el último bit. Si la instrucción se construye hay que elegir una de las dos definiciones y dejarla en la referencia.

### FPGA, módulo suelto

Síntesis con `synth_ice40`. `C` es la cantidad de bits de fracción de `phi`, `k1` y `k2`, y `S` la de los coeficientes de `G` en la forma directa.

| Versión | Matriz entera | Términos | LUT4 |
|---------|---------------|----------|------|
| Fija, factorizada, C = 3 | [24, -21] [40, 21] / 2^6 | 6 | 217 |
| Fija, factorizada, C = 4 | [96, -84] [160, 84] / 2^8 | 6 | 218 |
| Fija, factorizada, C = 5 | [352, -319] [640, 348] / 2^10 | 8 | 264 |
| Fija, factorizada, C = 6 | [1472, -1334] [2496, 1450] / 2^12 | 9 | 314 |
| Fija, factorizada, C = 8 | [23296, -20930] [40192, 22770] / 2^16 | 12 | 396 |
| Fija, directa, S = 6 | [23, -21] [39, 22] / 2^6 | 12 | 324 |
| Fija, directa, S = 8 | [91, -82] [157, 89] / 2^8 | 15 | 387 |
| Fija, directa, S = 12 | [1462, -1316] [2513, 1424] / 2^12 | 18 | 427 |
| Fija, factorizada, C = 6, sin saturar | la misma de C = 6 | 9 | 280 |
| Fija, k1 = 1/32, k2 = 1/2, phi = 7/8 | [32, -28] [512, 448] / 2^10 | 4 | 160 |
| **Fija, calibrada** | [10240, -9840] [3072, 12792] / 2^14 | 7 | **251** |
| Multiplicadores, coeficientes de 8 bits | programable | | 1645 |
| Multiplicadores, coeficientes de 14 bits | programable | | 3094 |

- La forma factorizada cuesta entre 26 % y 44 % menos que la directa con los mismos bits de fracción en la matriz (217 contra 324, 218 contra 387 y 314 contra 427).
- La saturación cuesta 34 LUT.
- El caso más barato usa ganancias que son potencias de 2 o casi: 160 LUT. Los coeficientes calibrados tienen 7 términos y cuestan 251.
- La versión de multiplicadores pide más LUT que las 1280 de la FPGA completa. La HX1K no tiene bloques multiplicadores. Esa versión solo existe en ASIC.

### FPGA, integrado en el core base

El módulo suelto no cuenta el multiplexor de 32 bits en la escritura del banco de registros ni la decodificación. Para medirlo, el script conecta el módulo como instrucción en una copia del core base y corre el place and route con 5 semillas. La copia es solo para medir y no está verificada como instrucción.

| Variante | Celdas | De 1280 | Agrega | Resultado |
|----------|--------|---------|--------|-----------|
| SoC base, sin la instrucción | 1074 | 84 % | | Cierra en 5 de 5 semillas, mediana 44,6 MHz |
| Con `kal2`, k1 = 1/32, k2 = 1/2, phi = 7/8 | 1291 | 101 % | +217 | No cabe |
| **Con `kal2`, calibrada** | 1402 | 110 % | +328 | No cabe |
| Con `kal2`, factorizada, C = 4 | 1345 | 105 % | +271 | No cabe |
| Con `kal2`, factorizada, C = 6 | 1442 | 113 % | +368 | No cabe |

Integrar cuesta entre 55 y 77 celdas más que el módulo suelto. La versión más barata se pasa por 11 celdas incluso junto al core base, que deja 206 libres, y la calibrada se pasa por 122. Como no cabe, no hay frecuencia máxima que informar.

### ASIC, GF180MCU

Síntesis con Yosys y abc contra el liberty típico de la biblioteca de 7 pistas. Es solo síntesis: sin place and route, sin reparación de timing y sin relleno.

| Versión | Celdas | Área (um²) | Respecto del SoC del Proyecto 3 |
|---------|--------|------------|---------------------------------|
| Fija, k1 = 1/32, k2 = 1/2, phi = 7/8 | 402 | 7 971 | 4 % |
| **Fija, calibrada** | 742 | 14 776 | 7 % |
| Fija, factorizada, C = 6 | 993 | 20 325 | 10 % |
| Fija, directa, S = 12 | 1 473 | 30 331 | 15 % |
| Multiplicadores de 17 x 8 | 3 407 | 66 897 | 32 % |
| Multiplicadores de 17 x 14 | 6 373 | 123 978 | 59 % |
| Multiplicadores de 17 x 14 y 4 registros | 6 599 | 129 804 | 62 % |

El SoC completo del Proyecto 3 ocupó 208 439 um² de celdas en este mismo proceso. La versión programable con coeficientes de 14 bits cuesta más de la mitad de un SoC. La fija con la misma precisión cuesta la sexta parte de eso.

## 7. Qué significa para la edición de competencia

La condición para entrar a la edición de competencia tiene dos partes: que el estimador de dos estados gane bajo el protocolo y que el hardware quepa junto al pipeline.

- **La primera no se cumple.** Bajo el protocolo el estimador de dos estados empata con la regla base: con la semilla reservada gana 30 ± 5 en el remuestreo, pierde 8 ± 8 en las familias plausibles y baja más de 1 % en tres familias de estrés (`docs/algoritmo.md`, sección 7.4, y decisión T30). La razón está en el modelo: el nivel y la transitoria se mueven a escalas parecidas, y el filtro óptimo apenas baja la incertidumbre de la transitoria de 1,19 a 1,11.
- **La segunda tampoco.** Con los coeficientes calibrados agrega 328 celdas. El pipeline de 3 etapas ocupa 994 celdas y deja 286 libres (`docs/espino_segmentado.md`), así que faltan unas 40. La cifra de 328 se midió sobre el core base: en el pipeline el multiplexor de escritura es otro y habría que repetirla. La versión de ganancias baratas (217 celdas) cabría en el papel, pero no son las ganancias calibradas.

Con las dos condiciones en contra, el producto 2x2 queda en la edición de exhibición.

Formas de achicarlo, ninguna medida todavía:

1. **Carriles más angostos.** La regla base guarda la media con 5 bits de fracción. Con 5 en vez de 8 y un rango menor para `u`, cada sumador pierde 3 o 4 bits. Estimamos entre 30 y 40 celdas menos.
2. **Sin saturación.** 34 celdas menos. Hay que demostrar que con los coeficientes elegidos los carriles no se desbordan con ningún precio.
3. **Versión secuencial.** Un solo sumador que hace las sumas una por ciclo, con un contador. Estimamos entre 80 y 100 celdas y unos 8 ciclos por paso. Como instrucción obliga a detener el core esos ciclos. Como periférico es natural: el estado se actualiza al llegar el precio y sobran más de 2000 ciclos por tick.

En la FPGA lo que falta es área y lo que sobra es tiempo: la regla base responde en 44 ciclos de 2262 disponibles. Un estimador de dos estados en software entra en ese presupuesto sin hardware nuevo. Por eso esta pieza apunta a la edición de exhibición y a la edición ASIC, donde el área no tiene ese límite, y su valor para el informe está en el co-diseño: el speedup medido contra el predicho y el punto en el roofline.

## 8. Lugar en la escalera de la clase 7

Predicción, con las definiciones de la clase. No hay nada medido todavía.

- **Trabajo útil por paso:** 8 operaciones (4 productos y 4 sumas).
- **Solo software, sin multiplicador ni shifter:** cada producto por constante son sumas, y cada desplazamiento a la derecha cuesta 6 instrucciones con el método de la memoria. El estimador calibrado tiene seis desplazamientos de números con signo, y el frente del algoritmo estima el tick completo en unas 140 instrucciones contra las 27 de la regla base. Descontando las 19 que no son del estimador quedan unas 120 instrucciones, cerca de 260 ciclos en el Espino base. Eso da 0,8 MOPS.
- **Con `kal2`:** una instrucción. 2 ciclos en el Espino base (100 MOPS) y 1 ciclo en el pipeline de 3 etapas (200 MOPS).
- **Amdahl.** El resto del tick (leer el precio, decidir y escribir) cuesta unos 41 ciclos. Con el estimador en 260 ciclos, la fracción acelerada es f = 260 / 301 = 0,864 y el factor F = 260 / 2 = 130. S = 1 / ((1 - 0,864) + 0,864 / 130) = 7,0 para el tick completo.
- **Roofline.** El paso mueve un byte (el precio) y hace 8 operaciones: intensidad de 8 Op/B, muy a la derecha del quiebre de 0,125 Op/B. Está limitado por cómputo, no por memoria.

Las 140 instrucciones son una estimación: el estimador de dos estados no está escrito en assembly. Estos números se reemplazan por mediciones si la instrucción se construye para la edición de exhibición.

## 9. Archivos

| Archivo | Qué es |
|---------|--------|
| `ref/mv2x2.py` | Modelo de referencia, ganancia en estado estacionario, cuantización y vectores de prueba |
| `tools/gen_mv2x2.py` | Generador de la versión de coeficientes fijos |
| `rtl/exhibicion/mv2x2_mult.v` | Versión con multiplicadores reales |
| `tb/tb_mv2x2.sv` | Testbench de las tres implementaciones |
| `tools/costo_mv2x2.py` | Corre el testbench y mide el costo |
| `docs/mediciones/mv2x2_costo.txt` | Salida de la última medición |

`rtl/exhibicion/` no está en la lista de fuentes del testbench oficial ni de la síntesis del SoC.
