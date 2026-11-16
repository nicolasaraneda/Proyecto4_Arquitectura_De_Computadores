# Co-diseño hardware y software: las variantes de Espino medidas para el punto 3.3

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Documento de estudio del paquete P7. Parte de las definiciones de la clase 7 (Métricas de Desempeño) y llega al detalle de cada variante: cuánto cuesta en la FPGA, cuántos ciclos usa por tick, dónde se van esos ciclos, qué predice Amdahl y qué se midió, dónde queda en el roofline y por qué compite la que compite. Todas las cifras salen de un objetivo de `make` y quedan en `docs/mediciones/p7/`. La sección 13 dice cuál.

```
make p7          # todo: síntesis de las seis variantes, gemelo, RTL, PLL y duplicador (unos 25 minutos)
make p7-rapido   # tablas, figuras, CSV y cifras.tex desde las mediciones guardadas (segundos)
```

## 1. En una página

| Variante | Celdas | BRAM | Fmax mín. (MHz) | Respuesta prom. / peor (ciclos) | CPI del kernel | MOPS logrado | Speedup de la respuesta |
|---|---|---|---|---|---|---|---|
| R0: Espino base, `sw/trade.s` | 1091 | 12 | 41,93 | 41,00 / 44 | 2,125 | 3,92 | 1,00 |
| Segmentado, `sw/trade.s` | 990 | 12 | 45,34 | 22,00 / 26 | 1,125 | 7,41 | 1,86 |
| Barrel, `sw/trade.s` en un hilo | 932 | 12 | 53,45 | 75,00 / 83 | 4,000 | 2,08 | 0,55 |
| Barrel con `emad` y `devk`, `sw/xd/trade_xd.s` | 991 | 12 | 48,59 | 55,00 / 63 | 4,000 | 4,17 | 0,75 |
| R1: el fondo en un chip, `sw/fondo.s` | 1029 | 13 | 51,59 | 223,01 / 443 | 4,000 por hilo | 5,34 | 0,18 |
| R2: R1 con el vigilante | 1045 | 13 | 47,86 | 223,01 / 443 | 4,000 por hilo | 5,34 | 0,18 |
| Base con la extensión | no existe en el RTL | | | 31 (predicho) | | 7,69 (predicho) | 1,32 (predicho) |
| Segmentado con la extensión | no existe en el RTL | | | 17,25 (predicho) | | 14,29 (predicho) | 2,38 (predicho) |

Lo que hay que saber decir:

1. **La más rápida por hilo es el segmentado.** Responde en 22 ciclos, 1,86 veces antes que R0. El barrel con un solo hilo útil es la más lenta: cada instrucción de un hilo ocupa 4 ciclos.
2. **La que compite (R1) no es la más rápida, y la tabla lo muestra.** Responde 5,4 veces más lento que R0. Pero hace 56 operaciones útiles por tick y no 8: su desempeño logrado es 5,34 MOPS contra 3,92 de R0. Usa el 19,6 % del presupuesto de la ronda 3 en el peor caso.
3. **Amdahl predice casi exacto, y donde falla se sabe por qué.** En el barrel y en la extensión la predicción coincide con la medición al ciclo, porque todas las instrucciones cuestan lo mismo. En el segmentado la estimación de la clase (salto tomado de 3 ciclos) se queda 6,4 % corta; con el costo medido (2 ciclos) la diferencia baja a 1,1 %, y es la detección del sondeo.
4. **Todo está a la derecha del quiebre del roofline**: el kernel mueve entre 8 y 13 bytes por tick y hace 8 operaciones, de 0,6 a 1 Op/B contra un quiebre de 0,125. El límite es el cómputo, no la memoria.
5. **Subir la frecuencia no sirve aquí.** El VQ100 no tiene PLL (nextpnr no lo puede ubicar) y el duplicador de reloj por lógica cierra 1 de 10 semillas con un oscilador real. Y aunque funcionara, el peor caso ya usa menos del 20 % del presupuesto más corto.

## 2. Lo básico: las definiciones de la clase 7

Estas son las definiciones que usa todo el documento, las mismas del profesor.

**Ley de hierro.** El tiempo de un programa es

```
Tiempo = IC x CPI x Tclk
```

IC es la cantidad de instrucciones ejecutadas, CPI los ciclos por instrucción en promedio y Tclk el período del reloj. Toda mejora de esta tabla se explica diciendo cuál de los tres factores ataca:

- la extensión de la ISA baja el IC (14 instrucciones de la media pasan a 2);
- el pipeline baja el CPI (de 2 o 3 a 1 o 2);
- el PLL o el duplicador bajarían Tclk (de 40 a 20 ns), y no se pudo;
- el barrel sube el CPI de un hilo a 4, pero ejecuta cuatro hilos a la vez: baja el CPI de la máquina a 1.

**CPI.** En el Espino base, medido en clases: ALU 2, store 2, load 3, salto no tomado 2, salto tomado o `jal` 3. Lo comprobamos ciclo por ciclo con `make cpi`: el modelo `2 IC + loads + saltos tomados` da la cuenta exacta de ciclos en todos los programas.

**Ops/s y Ppeak.** El desempeño máximo teórico es

```
Ppeak = f x instrucciones por ciclo x operaciones por instrucción x núcleos
```

En el Espino base: 25 MHz x 0,5 x 1 x 1 = 12,5 MOPS. En el barrel los núcleos son los hilos: 25 x 0,25 x 1 x 4 = 25 MOPS. Con la extensión, `emad` y `devk` hacen 2 operaciones cada una, como el MAC de la clase: el barrel con la extensión llega a 50 MOPS.

**Desempeño logrado por un kernel.** Solo cuenta el trabajo útil:

```
P = operaciones útiles x 25 MHz / ciclos del kernel
```

En la suma de vectores de la clase cuenta 1 de las 8 instrucciones del lazo. Advertencia de la clase: nunca se comparan instrucciones por segundo entre ISAs distintas, se compara tiempo o trabajo útil por segundo. Por eso la tabla compara MOPS de operaciones útiles y no MIPS: `sw/trade.s` y `sw/xd/trade_xd.s` ejecutan 24 y 12 instrucciones para el mismo trabajo.

**Roofline.** El desempeño alcanzable de un kernel es

```
P = min(Ppeak, I x Bs)
```

donde I es la intensidad operacional (operaciones útiles por byte movido) y Bs el ancho de banda de la memoria. En Pochoco el bus mueve 4 bytes por ciclo: Bs = 4 B x 25 MHz = 100 MB/s. Con Ppeak de 12,5 MOPS el quiebre está en I = 12,5 / 100 = 0,125 Op/B. Un kernel a la izquierda del quiebre está limitado por la memoria; a la derecha, por el cómputo. Cada variante tiene su propio techo Ppeak. Ejes logarítmicos: intensidad en Op/B contra MOPS.

**Amdahl generalizado.** Si una fracción f del tiempo se acelera en un factor F,

```
S = 1 / ((1 - f) + f / F)
```

y si el programa tiene varias partes, cada una con su fracción f_i y su factor F_i, S = 1 / Σ (f_i / F_i). Es lo que usa la sección 7, con una fracción por fase del tick.

**Ops/W.** MOPS divididos por la potencia. La clase supuso 10 mW para Pochoco. En la FPGA no medimos consumo (no hay medidor); la sección 10 usa la potencia que calcula el flujo ASIC.

## 3. Nuestro kernel y qué es una operación útil

El kernel es la regla `max_media` (decisión T50) por cada precio: actualizar la media y decidir. En su forma matemática (`ref/trader.py`, `ReglaBase.decidir`):

```
dev = 32 p - S                       desviación del precio respecto de la media
pos = (pos | dev < -96) & (dev < 1)  entrar 3 unidades bajo la media, salir al recuperarla
S   = S + (dev >>> 5)                media exponencial con alfa 1/32, en treintaidosavos
```

**Operaciones útiles por tick: 8.**

| Parte | Operaciones | Cuenta |
|---|---|---|
| Actualizar la media | 32 p, dev = 32 p - S, dev >>> 5, S + (dev >>> 5) | 4 |
| Decidir | dev < umbral de entrada, dev < umbral de salida, pos \| entrar, (...) & no_salir | 4 |

No cuentan: el sondeo de STATUS, la lectura de PRICE, el store a DECISION, armar el byte (0x7F o 0xBF, que es codificar la salida), el salto de vuelta y las instrucciones que Espino necesita para hacer lo que su ALU no tiene. En `sw/trade.s`, `32 p` son cinco sumas y `dev >>> 5` son siete instrucciones con la memoria como desplazador (`docs/trade_s.md`): 14 instrucciones para 4 operaciones. Con `devk` y `emad` (`docs/extension_isa.md`) son 2 instrucciones para las mismas 4: cada una hace 2 operaciones, como el MAC.

**Operaciones útiles del fondo por tick: 56.** `sw/fondo.s` corre la misma regla cuatro veces (el supervisor y tres gestores con umbrales distintos), lleva el puntaje de cada gestor y combina los votos (`ref/fondo.py`):

| Parte | Operaciones | Cuenta |
|---|---|---|
| 4 reglas | 4 x 8 | 32 |
| 3 puntajes | 32 (p - p anterior), por la posición ejecutada (0 o 1), suma al puntaje, xor de posiciones, por 2, resta de la comisión: 6 cada uno | 18 |
| Combinación | 3 productos peso por voto, 2 sumas, comparación con el umbral | 6 |

El ajuste de pesos cada 512 ticks no se cuenta.

**Ciclos del kernel.** Los de las instrucciones que van desde la lectura de PRICE hasta el salto de vuelta al sondeo, medidos con el perfil del gemelo (sección 6). No incluyen la espera del precio: esperar no es trabajo del kernel. En el fondo son los ciclos del supervisor, que además espera los votos de los gestores: es el camino crítico del tick.

**Bytes movidos por tick.** Los de los loads y stores del kernel, con su tamaño (4 un `lw` o `sw`, 1 un `lbu`). El sondeo de STATUS no cuenta. Si un lazo espera un dato (el voto de un gestor, el precio publicado), cuenta solo la lectura que lo trae. En `sw/trade.s`: PRICE (4), DECISION (4), la palabra de trabajo del desplazador (4) y su byte (1), 13 bytes. Con la extensión el desplazador desaparece: 8 bytes.

## 4. Las variantes

Todas son el mismo `pochoco_soc` con su programa dentro, elegidas al compilar (`docs/espino_segmentado.md`, `docs/espino_barrel.md`, `docs/extension_isa.md`, `docs/tabla_vigilante.md`).

| Variante | Definiciones | Programa | Qué cambia respecto de R0 |
|---|---|---|---|
| R0 | ninguna | `sw/trade.s` | Es la referencia: solo software, sin hardware agregado |
| Segmentado | `-DESPINO_SEGMENTADO` | `sw/trade.s` | Pipeline de 3 etapas: baja el CPI |
| Barrel | `-DESPINO_BARREL` | `sw/trade.s` en el hilo 0, con la tabla de arranque | Cuatro hilos por turnos; los otros tres giran en `j .` |
| Barrel con extensión | `+ -DESPINO_XD_EMAD -DESPINO_XD_DEVK` | `sw/xd/trade_xd.s` | `devk` y `emad` reemplazan 14 instrucciones por 2: baja el IC |
| R1 | barrel, extensión y `-DESPINO_TABLA` | `sw/fondo.s` | El fondo: cuatro reglas en cuatro hilos y la tabla de parámetros en una BRAM |
| R2 | R1 y `-DESPINO_VIGILANTE` | `sw/fondo.s` | El vigilante con `SB_WARMBOOT` |

**Las dos que no existen.** El Espino base y el segmentado con la extensión no están en el RTL: `emad` y `devk` viven en `espino_xd.v`, que solo se conecta al core barrel. Construirlas exigía tocar `espino_core.v`, que es el RTL de R0 y ya pasó la puerta (decisión T101). Quedan como predicción con Amdahl, que en las variantes medidas acierta al ciclo (sección 7), y así aparecen en la tabla.

## 5. La tabla de variantes

`make p7-variantes` (salida en `docs/mediciones/p7/variantes.txt` y `variantes.csv`).

**Recursos y frecuencia.** `tools/p7/recursos.sh` sintetiza las seis variantes en la misma corrida, cada una con su programa, y corre nextpnr con las semillas 1 a 10 (`--hx1k --package vq100 --freq 25`):

| Variante | Celdas de 1280 | LUT4 | BRAM de 16 | Fmax mínima | Mediana | Cierran a 25 MHz |
|---|---|---|---|---|---|---|
| R0 | 1091 | 921 | 12 | 41,93 | 44,09 | 10 de 10 |
| Segmentado | 990 | 798 | 12 | 45,34 | 47,20 | 10 de 10 |
| Barrel | 932 | 761 | 12 | 53,45 | 56,32 | 10 de 10 |
| Barrel con extensión | 991 | 817 | 12 | 48,59 | 51,61 | 10 de 10 |
| R1 | 1029 | 854 | 13 | 51,59 | 52,57 | 10 de 10 |
| R2 | 1045 | 868 | 13 | 47,86 | 50,33 | 10 de 10 |

La extensión (`emad` y `devk`) cuesta 59 celdas sobre el barrel y baja la frecuencia mínima de 53,45 a 48,59 MHz: su sumador y su desplazador quedan en la ruta crítica de la ALU. La tabla cuesta una BRAM.

Un hallazgo de esta corrida: el segmentado mide 45,34 MHz de mínima, y en P1 (`docs/mediciones/barrel/recursos.txt`) había medido 51,59. Su RTL no cambió; sí cambió `pochoco_soc.v` (P2 y P5 agregaron la extensión, la tabla y el vigilante detrás de definiciones que el segmentado no usa). Con otra síntesis cambia la ubicación y la ruta del medio ciclo del fetch. Sigue cerrando 10 de 10 a 25 MHz y no compite, así que no se investigó más.

**Ciclos por tick.** Con el gemelo (`tools/p7/medir.py`), la serie de práctica completa, timing del testbench oficial. La respuesta va de `byte_done` a la escritura en DECISION, como la mide el oficial. El tick completo, hasta que el programa vuelve a sondear.

| Variante | Respuesta prom. | Peor | Tick prom. | Peor | IC de la respuesta | CPI de la respuesta |
|---|---|---|---|---|---|---|
| R0 | 41,00 | 44 | 63,00 | 66 | 19,50 | 2,103 |
| Segmentado | 22,00 | 26 | 34,00 | 38 | 19,20 | 1,146 |
| Barrel | 75,00 | 83 | 115,00 | 123 | 19,00 | 3,947 |
| Barrel con extensión | 55,00 | 63 | 67,00 | 75 | 14,00 | 3,929 |
| R1 y R2 | 223,01 | 443 | 281,01 | 475 | 56,00 (supervisor) | 3,982 |

El IC de la respuesta incluye las vueltas del sondeo que caen después de `byte_done`, por eso el CPI de la respuesta no es el del kernel.

**Confirmación con el RTL** (`make p7-rtl`, `docs/mediciones/p7/rtl.txt`). Para R0 y el segmentado se corrió `tb/tb_cpi.sv` con Verilator sobre la serie completa: las 19 998 filas por tick (ciclo del precio, respuesta, tick completo e IC) son idénticas byte a byte a las del gemelo. Para R1 y R2 la medición del RTL de P5 (`docs/mediciones/fondo/r1/ticks.txt` y `r2/ticks.txt`, con el mismo sha256 del programa y de la tabla) da 223,01 y 443 de respuesta y 281,01 y 475 de tick completo, lo mismo que el gemelo. Por eso R2 lleva los ciclos de R1: el vigilante solo observa.

**Kernel, desempeño y speedup.** Con el perfil (sección 6):

| Variante | Ciclos del kernel | IC del kernel | CPI | Operaciones útiles | MOPS logrado | Ppeak | S (respuesta) | S (MOPS) |
|---|---|---|---|---|---|---|---|---|
| R0 | 51,00 | 24 | 2,125 | 8 | 3,922 | 12,5 | 1,000 | 1,000 |
| Segmentado | 27,00 | 24 | 1,125 | 8 | 7,408 | 25 | 1,864 | 1,889 |
| Barrel | 96,00 | 24 | 4,000 | 8 | 2,083 | 6,25 | 0,547 | 0,531 |
| Barrel con extensión | 48,00 | 12 | 4,000 | 8 | 4,167 | 12,5 | 0,745 | 1,062 |
| R1 y R2 | 262,37 | 65,59 en el supervisor, 125,59 en los 4 hilos | 4,000 por hilo | 56 | 5,336 | 50 | 0,184 | 1,361 |

El Ppeak del barrel con un solo hilo útil es la cuarta parte del de la máquina (6,25 contra 25 MOPS): los otros tres hilos giran sin hacer nada.

**Presupuesto usado en cada ronda** (peor caso de la respuesta, con el período de la ronda):

| Variante | Ronda 1 (249 762 ciclos) | Ronda 2 (24 762) | Ronda 3 (2 262) |
|---|---|---|---|
| R0 | 44, 0,018 % | 44, 0,178 % | 44, 1,95 % |
| Segmentado | 26, 0,010 % | 26, 0,105 % | 26, 1,15 % |
| Barrel | 87, 0,035 % | 87, 0,351 % | 83, 3,67 % |
| Barrel con extensión | 67, 0,027 % | 67, 0,271 % | 63, 2,79 % |
| R1 y R2 | 435, 0,174 % | 443, 1,79 % | 443, 19,58 % |

El peor caso de R1 (443) es un tick de frontera de ventana, cada 512 ticks, en que el supervisor ajusta los pesos. En un tick común responde entre 219 y 227 ciclos (`docs/mediciones/fondo/r1/ticks.txt`).

## 6. Perfilado: dónde se van los ciclos

El enunciado pide medir qué parte del tick consume más ciclos, no estimarlo. Para eso el gemelo tiene la opción `--perfil` (`ref/gemelo/gemelo.c`): cuenta, por hilo y por dirección del programa, cuántas veces se ejecutó cada instrucción y cuántos ciclos ocupó. No cambia nada de la simulación (`make cosim` y `make cosim-barrel-corta` siguen en verde). `tools/p7/fuentes.py` ensambla el programa con el mismo `tools/pochoasm.py` y asigna cada dirección a una fase leyendo el programa: en `sw/trade.s` recorre el lazo principal (sondeo, lectura, cálculo de dev, decisión, store, media), en `sw/fondo.s` usa las secciones numeradas de sus comentarios.

La detección (cuánto demora el sondeo en ver el precio) no la cuenta el perfil: es la respuesta medida menos las fases que van antes de la escritura.

R0 (`docs/mediciones/p7/perfil.txt`), ciclos por tick:

| Fase | Ciclos | Instrucciones | % de la respuesta | % del kernel |
|---|---|---|---|---|
| Esperar el precio: detección por el sondeo | 10,00 | | 24,4 | |
| Leer PRICE | 3,00 | 1 | 7,3 | 5,9 |
| Media: dev = 32 p - S | 12,00 | 6 | 29,3 | 23,5 |
| Decidir y armar el byte | 14,00 | 7 | 34,1 | 27,5 |
| Escribir DECISION | 2,00 | 1 | 4,9 | 3,9 |
| Media: S = S + (dev >>> 5) | 17,00 | 8 | | 33,3 |
| Volver al sondeo | 3,00 | 1 | | 5,9 |

- **En el kernel, lo que más pesa es actualizar la media: 29 de 51 ciclos (56,9 %).** Son 14 instrucciones porque Espino no tiene desplazador. Es exactamente lo que ataca la extensión.
- **En la respuesta pesa más decidir (14 ciclos)**, porque la media S se actualiza después del store, fuera de la respuesta. El programa se escribió así para que la decisión salga lo antes posible.
- **En el tick completo a 0,1 ms, el 98 % del tiempo es sondeo**: 2 449 de 2 500 ciclos. El procesador espera.

En el segmentado las proporciones son casi las mismas (la media es el 55,6 % del kernel). En el barrel con la extensión la media baja a 8 de 48 ciclos y lo que domina pasa a ser decidir (28 ciclos, 58 % del kernel).

En R1 la respuesta del supervisor se reparte así: detección 14,6 ciclos, lectura 4, publicar el precio 12, su propia regla 44, **esperar los votos de los gestores 88,1 (39,5 %)**, voto ponderado 52 y el store 4. La espera de los votos es la fase más larga: cada gestor ejecuta 20 instrucciones por tick (puntaje 9, regla 7, publicar 4), a 4 ciclos cada una.

## 7. Amdahl: predicho contra medido

`make p7-amdahl` (`docs/mediciones/p7/amdahl.txt`). Método:

1. La fracción f_i de cada fase sale del perfil medido de la variante de partida.
2. El factor F_i predicho sale de aplicar el modelo de costo de la variante nueva a las instrucciones de esa fase, contadas en el perfil por clase (ALU, load, store, salto). La detección se predice escalando la de R0 por la duración de una vuelta del lazo de sondeo (`lw`, `andi`, `beqz` tomado) en cada modelo: 8 ciclos en el base, 6 con la estimación de la clase, 5 en el segmentado medido y 12 en el barrel.
3. S predicho = 1 / Σ (f_i / F_i), contra S medido = ciclos de R0 / ciclos de la variante.

Modelos de costo (ciclos por instrucción):

| Modelo | ALU | load | store | salto tomado | De dónde sale |
|---|---|---|---|---|---|
| Espino base | 2 | 3 | 2 | 3 | Medido, `make cpi` |
| Pipeline, estimado en la clase 7 | 1 | 2 | 1 | 3 | La clase |
| Pipeline, medido | 1 | 2 | 1 | 2 | Medido, `make cpi-seg` |
| Barrel | 4 | 4 | 4 | 4 | Un hilo, por construcción |

Resultado sobre la respuesta:

| Cambio | S predicho | S medido | Diferencia |
|---|---|---|---|
| R0 a segmentado, con el CPI que estimó la clase | 1,745 | 1,864 | -6,4 % |
| R0 a segmentado, con el costo medido | 1,843 | 1,864 | -1,1 % |
| R0 a barrel, un hilo | 0,547 | 0,547 | 0 |
| Barrel a barrel con la extensión (la extensión sola) | 1,364 | 1,364 | 0 |
| R0 a barrel con la extensión | 0,745 | 0,745 | 0 |
| R0 a Espino base con la extensión | 1,323 (31 ciclos) | no existe | |
| R0 a segmentado con la extensión | 2,377 (17,25 ciclos) | no existe | |

Y sobre el kernel (los MOPS): segmentado 1,889 predicho y medido con el costo medido (1,821 con el de la clase); la extensión sola 2,000 y 2,000; base con extensión 1,962 y segmentado con extensión 3,643, predichos.

**Por qué la diferencia.**

- **Con la estimación de la clase** el salto tomado del pipeline cuesta 3 ciclos. En nuestro segmentado cuesta 2: la instrucción se lee en el flanco de bajada, medio ciclo después de que cambia el contador de programa, y no hay que anular una etapa de fetch completa (`docs/espino_segmentado.md`). El kernel tiene un solo salto (`j esperar`), pero el lazo de sondeo tiene uno por vuelta: la detección predicha (7,5 ciclos) se pasa de la medida (6).
- **Con el costo medido** lo único que no se predice exacto es la detección: 6,25 predichos contra 6,00 medidos. La detección depende de en qué punto de la vuelta del lazo cae el precio, y eso no escala en proporción exacta con la duración de la vuelta: el primer ciclo en que STATUS se ve en 1 depende de la sincronización del esclavo SPI.
- **En el barrel y en la extensión** la predicción es exacta, porque cada instrucción de un hilo cuesta 4 ciclos, sin excepción: no hay riesgos, ni burbujas, ni diferencias entre clases. La extensión sola acelera la fase de dev 6 veces (6 instrucciones a 1) y la de la media S 8 veces, y no toca las demás.

**Amdahl clásico sobre la fase más pesada.** La media es f = 29 / 51 = 0,569 del kernel de R0. Con la extensión en el Espino base esas 14 instrucciones pasan a 2 (`devk` y `emad`, 4 ciclos en vez de 29): F = 7,25 y S = 1 / ((1 - 0,569) + 0,569 / 7,25) = 1,96. Aunque la media costara cero, el kernel no iría más de 1 / (1 - 0,569) = 2,32 veces más rápido: el resto (decidir, leer, escribir) queda igual.

**El fondo no es un speedup del mismo kernel.** R1 hace 7 veces más trabajo útil por tick que R0. Su respuesta la domina la espera de los votos; el piso de esa espera son las 20 instrucciones de un gestor a 4 ciclos.

## 8. La escalera de la clase 7 y el roofline

La clase aplicó a un kernel una escalera de cuatro pasos: extensión de la ISA, pipeline, instrucciones a medida estilo Xpulp (post-incremento, MAC, lazo por hardware) y SIMD empaquetado, con los pasos 2 a 4 estimados con CPI ideal. Aquí está la misma escalera sobre nuestro kernel, con cada paso construido y medido donde existe (`docs/mediciones/p7/escalera.txt`):

| Paso | Qué | Estado | Instr. por op. | Ciclos por op. | MOPS | Speedup | Celdas |
|---|---|---|---|---|---|---|---|
| 0 | Espino base, solo software (R0) | medido | 3,000 | 6,375 | 3,92 | 1,00 | 1091 |
| 1 | Extensión de la ISA en el Espino base | estimado con el costo medido del base | 1,500 | 3,250 | 7,69 | 1,96 | no existe |
| 2 | Pipeline de 3 etapas, solo software | medido | 3,000 | 3,375 | 7,41 | 1,89 | 990 |
| 1+2 | Pipeline con la extensión | estimado con el costo medido del segmentado | 1,500 | 1,750 | 14,29 | 3,64 | no existe |
| 2b | Barrel, un hilo, solo software | medido | 3,000 | 12,000 | 2,08 | 0,53 | 932 |
| 1+2b | Barrel, un hilo, con la extensión | medido | 1,500 | 6,000 | 4,17 | 1,06 | 991 |
| 2c | Barrel, 4 hilos, con la extensión: el fondo (R1) | medido | 2,243 | 4,685 | 5,34 | 1,36 | 1029 |
| 3 | Instrucciones a medida sobre el pipeline | estimado, CPI ideal 1 | 0,875 | 0,875 | 28,57 | 7,29 | no construido |
| 4 | SIMD de 2 carriles de 16 bits | estimado, CPI ideal 1 | 0,263 | 0,263 | 95,00 | 24,22 | no construido |

**Pasos 3 y 4, cómo se estimaron.** Paso 3: dos instrucciones a medida que fusionan operaciones que siempre van juntas, como hace Xpulp: `mmpos` hace las dos comparaciones con los umbrales y actualiza la posición (4 operaciones), y `mmbyte` pasa de la posición al byte. El kernel queda en `lw`, `devk`, `mmpos`, `mmbyte`, `sw`, `emad` y `j`. Nuestro kernel no tiene lazos ni arreglos, así que el post-incremento y el lazo por hardware de Xpulp no tienen dónde aplicarse. Paso 4: los precios son de 8 bits, pero S necesita 13 bits y dev 14 con signo: no caben cuatro carriles de 8 bits, sí dos de 16. Las cuatro reglas del fondo (mismo precio, umbrales distintos) caben en dos registros, y el voto ponderado es una instrucción más: 38 operaciones en 10 instrucciones. Los dos pasos son estimaciones con CPI ideal, como hizo la clase, y en la FPGA no caben: el barrel con la extensión ya ocupa 991 de 1280 celdas, y una ALU de dos carriles duplica los sumadores.

**Contra lo que estimó la clase.** Con el método de la clase (IC por 2,35 en el base, IC por 1,5 en el pipeline):

- paso 0: la clase estima 56,4 ciclos y se miden 51 (+10,6 %). El kernel tiene menos loads y saltos que el mix de la clase: su CPI es 2,125 y no 2,35.
- paso 2: la clase estima 36 ciclos y se miden 27 (+33 %). El CPI del kernel en el pipeline es 1,125 y no 1,5: el salto tomado cuesta 2 y no 3, y casi todo el kernel son instrucciones de ALU.
- Con el mix de la clase (`sw/mix_clase7.s`, `docs/mediciones/espino_segmentado.txt`) el pipeline mide CPI 1,35 contra el 1,5 estimado.

**Roofline.** Figura en `docs/mediciones/p7/roofline.svg` (y `roofline.tex`, la misma figura en TikZ para el informe; datos en `roofline.csv`). Ejes logarítmicos, intensidad en Op/B contra MOPS, el techo de memoria de 100 MB/s y un techo Ppeak por variante: 6,25 (barrel con un hilo), 12,5 (Espino base, y barrel con un hilo y la extensión), 25 (segmentado, barrel con 4 hilos) y 50 MOPS (barrel con 4 hilos y la extensión: R1 y R2).

| Punto | I (Op/B) | MOPS | Techo de su variante | Fracción del techo |
|---|---|---|---|---|
| R0 | 0,615 | 3,92 | 12,5 | 31 % |
| Segmentado | 0,615 | 7,41 | 25 | 30 % |
| Barrel, un hilo | 0,615 | 2,08 | 6,25 | 33 % |
| Barrel con extensión, un hilo | 1,000 | 4,17 | 12,5 | 33 % |
| R1 y R2 | 0,699 | 5,34 | 50 | 11 % |

Lectura:

- **Todos los puntos están a la derecha del quiebre** (0,125 Op/B en el base, 0,5 en R1): ningún kernel está limitado por la memoria. Con 100 MB/s y 0,6 Op/B el techo de memoria estaría en 60 MOPS, lejos de cualquier punto.
- **Todos quedan a un tercio o menos de su techo de cómputo.** La distancia es el trabajo que no es útil: en `sw/trade.s` 24 instrucciones para 8 operaciones (la lectura, el store, armar el byte, el salto, y el desplazamiento por memoria). La extensión sube el punto y además lo corre a la derecha, porque elimina el store y el load del desplazador.
- **R1 es el que más lejos queda de su techo (11 %)**: tiene 4 hilos y las instrucciones de 2 operaciones, pero el supervisor pasa el 40 % de la respuesta esperando votos y gasta instrucciones en publicar, combinar y la telemetría.

## 9. Frecuencia: PLL y doble frecuencia, resultados negativos

El enunciado pide, si se sube la frecuencia con un PLL, mostrar que nextpnr cierra y recalcular el presupuesto. Los dos caminos para subirla se midieron y no sirven en la Go Board (`docs/mediciones/p7/negativos.txt`).

**PLL** (`make p7-pll`, `docs/mediciones/p7/pll.txt`, log completo en `pll_vq100_r1.log`). Una copia de `pochoco_soc.v` en `build/p7/` con el reloj interno saliendo de un `SB_PLL40_CORE` de 25 a 50 MHz (parámetros de `icepll -i 25 -o 50`), con R0 y con R1:

```
nextpnr-ice40 --hx1k --package vq100 --freq 50 --pcf goboard.pcf ...
ERROR: PLL 'u_pll' couldn't be placed anywhere, no suitable BEL found.
ERROR: Packing design failed.
```

El HX1K en encapsulado VQ100 no tiene PLL. Para saber qué habría pasado si existiera, el mismo diseño se ubicó en el HX1K en TQ144, que sí lo tiene, sin restricciones de pines: R1 cierra a 50 MHz en 10 de 10 semillas (mínima 50,44 MHz) y R0 en 0 de 10 (mínima 42,68).

**Duplicador de reloj por lógica** (`make p7-doble`, `docs/mediciones/p7/doble_frecuencia/`). El experimento de la factibilidad (una cadena de LUT y un XOR que generan un pulso en cada flanco del oscilador) se reprodujo desde la rama `factibilidad-fondo`: las cuatro salidas salieron idénticas byte a byte a las guardadas. nextpnr analiza un reloj ideal de 50 MHz, pero el reloj doblado alterna períodos según el ciclo de trabajo del oscilador: con 45 % el período corto es de 17,73 ns, que equivale a cerrar a 56,4 MHz. El Espino base no cierra en ninguna semilla; el segmentado cierra en 1 de 10 con un ciclo de trabajo de 45 a 55 % en la esquina lenta.

**Presupuesto que habría dado cada uno.** Los dos duplican la frecuencia: el presupuesto pasa a (T - 9 500 ns) / 20 ns.

| Ronda | A 25 MHz | A 50 MHz |
|---|---|---|
| 1 (10 ms) | 249 762 | 499 525 |
| 2 (1 ms) | 24 762 | 49 525 |
| 3 (0,1 ms) | 2 262 | 4 525 |

R1 usaría el 9,8 % del presupuesto de la ronda 3 en vez del 19,6 %; R0, el 0,97 % en vez del 1,95 %. El programa haría el mismo trabajo en la mitad del tiempo, pero ya cabía con holgura: el patrimonio no cambia. La forma de hacer más trabajo por período que sí funciona en esta placa es la del segmentado, que usa los dos flancos del reloj de 25 MHz solo donde hace falta.

## 10. Edición ASIC: Ops/W y energía por decisión

La edición ASIC (pieza G de la factibilidad, LibreLane con GF180MCU) existe para el Espino base y el segmentado. Sus mediciones están en `docs/mediciones/asic/` con su procedencia (`LEEME.md`). P7 no corre el flujo; calcula Ops/s, Ops/W y energía con la definición de la sección 3 (`docs/mediciones/p7/asic.txt`). Esquina típica, 25 MHz:

| | Espino base | Segmentado |
|---|---|---|
| Dado | 0,359 mm² | 0,304 mm² |
| Celdas estándar | 176 975 um² | 149 757 um² |
| Frecuencia máxima con cierre (esquina lenta) | 42,6 MHz | 42,6 MHz |
| Potencia esperando / calculando | 27,97 / 28,79 mW | 26,18 / 27,38 mW |
| Kernel a 25 MHz / a 42,6 MHz | 3,92 / 6,68 MOPS | 7,41 / 12,61 MOPS |
| Ops/W del kernel | 136 MOPS/W | 271 MOPS/W |
| Ppeak por watt | 434 MOPS/W | 913 MOPS/W |
| Energía por decisión, ronda 3 (calculada) | 2,80 uJ | 2,63 uJ |
| Energía por decisión, rondas 2 y 1 (estimadas) | 28,0 y 280 uJ | 26,2 y 262 uJ |
| Costo marginal de decidir | 2,62 nJ, 0,33 nJ por operación | 3,84 nJ, 0,48 nJ por operación |

- La clase supuso 10 mW para Pochoco, que dan 1 250 MOPS/W de Ppeak. El macro a 5 V consume casi 3 veces eso.
- **La energía por decisión la pone la espera, no el cálculo.** Decidir cuesta unos nJ por sobre los 2,6 a 2,8 uJ que se gastan esperando 0,1 ms con el reloj corriendo. Ningún peldaño de la escalera cambia eso; detener el reloj entre precios sí.
- El barrel, la extensión y el fondo no pasaron por el flujo: su Ops/W no se informa (sección 12).

## 11. La variante elegida y por qué

**Compite R1** (y R2 si el ayudante permite reconfigurar durante una ronda), por la decisión T50 de Nicolás: "opción b, tomemos riesgos". La tabla muestra con honestidad lo que eso significa:

- **No es la más rápida por hilo.** El segmentado responde en 22 ciclos y R1 en 223 en promedio. Si la métrica fuera la latencia del kernel de una regla, ganaría el segmentado, y con la extensión ganaría todavía más (17 ciclos predichos).
- **Hace más trabajo útil por segundo.** 56 operaciones por tick contra 8, 5,34 MOPS contra 3,92 de R0 y 7,41 del segmentado con una sola regla. Es la única variante que usa los cuatro hilos del barrel y las instrucciones de dos operaciones.
- **Cabe y tiene margen.** 1029 de 1280 celdas, 13 de 16 BRAM, 51,59 MHz de mínima en 10 semillas (más del doble de los 25 MHz del oscilador), y usa el 19,6 % del presupuesto de la ronda 3 en el peor caso: 80 % de holgura, por encima del 50 % que pide la puerta.
- **La latencia no da patrimonio.** El byte que la maestra lee en el tick n se ejecuta al precio n, sea que el programa respondió en 22 ciclos o en 443: mientras la respuesta llegue antes del tick siguiente, la misma estrategia da los mismos bytes en cualquier core (R0, el segmentado, el barrel y el barrel con la extensión dan con `max_media` los mismos 20 000 bytes que `ref/trader.py`). Por eso el criterio para elegir no es la velocidad sino qué algoritmo cabe y cuánto riesgo agrega.
- **Lo que se acepta a sabiendas.** Según el protocolo, el fondo no suma puntos esperados contra `max_media` sola (+0,007 a 2 000 ticks, -0,005 a 20 000; decisión T50) y agrega riesgo de falla en vivo. El respaldo es R0, que decide `max_media` en 44 ciclos con el core base. La elección es por lo que el diseño representa como co-diseño: un procesador rediseñado, una extensión propia de la ISA usada de verdad y cuatro reglas en paralelo, todo medido.

## 12. Lo que no se midió y por qué

- **Espino base y segmentado con la extensión**: no existen en el RTL y construirlos toca el RTL de R0 (T101). Están predichos con Amdahl, que acierta al ciclo en las variantes medidas del mismo tipo.
- **Pasos 3 y 4 de la escalera**: no construidos, no caben en la FPGA. Estimados con CPI ideal, como en la clase.
- **Consumo de la Go Board**: no hay medidor. La potencia es la del flujo ASIC, y solo del base y del segmentado.
- **Edición ASIC del barrel, la extensión y el fondo**: no se pasaron por LibreLane. Es un punto posterior (la factibilidad estima más del doble de área por los cuatro bancos de registros).
- **R2 con el gemelo**: el gemelo no modela el vigilante. Sus ciclos son los de R1, confirmados contra la medición del RTL de P5 con el mismo programa y la misma tabla.
- **La caída de frecuencia del segmentado** desde P1 (sección 5): medida, no investigada.

## 13. Cómo se reproduce cada número

| Comando | Qué hace | Salida | Demora |
|---|---|---|---|
| `make p7-recursos` | Síntesis y 10 semillas de nextpnr de las seis variantes. No repite si la huella de las fuentes no cambió | `recursos.txt` | 4 min |
| `make p7-medir` | Gemelo a los tres períodos y perfil a 0,1 ms | `gemelo.txt`, `perfil/*.txt` | 10 s |
| `make p7-rtl` | R0 y segmentado por el RTL con Verilator, R1 y R2 contra la medición de P5 | `rtl.txt` | 3 min |
| `make p7-pll` | PLL en el VQ100 y en un TQ144 hipotético | `pll.txt`, `pll_vq100_r1.log` | 2 min |
| `make p7-doble` | Duplicador de reloj, reproducido desde la rama de la factibilidad | `doble_frecuencia/reproduccion.txt` | 15 min |
| `make p7-rapido` | Tablas, figuras, CSV y macros, sin sintetizar | `variantes`, `perfil`, `amdahl`, `escalera`, `asic`, `negativos` (`.txt` y `.csv`), `roofline.svg`, `roofline.tex`, `cifras.tex` | segundos |
| `make p7-variantes` | Recursos, gemelo y RTL, y la tabla | `variantes.txt` | 7 min |
| `make p7-amdahl` | Gemelo y perfil, y Amdahl | `perfil.txt`, `amdahl.txt` | 10 s |
| `make p7` | Todo | | 25 min |

Todo queda en `docs/mediciones/p7/`, cada archivo con el commit y las versiones de las herramientas en su encabezado. `cifras.tex` tiene una macro por cifra que cita el informe (por ejemplo `\pSieteCeldasRcero`, `\pSieteMopsRuno`, `\pSieteAmdahlPredRespSeg`), con coma decimal.

Archivos de P7:

| Archivo | Qué es |
|---|---|
| `tools/p7/comun.sh` | Variantes, programas y versiones que comparten los scripts |
| `tools/p7/recursos.sh` | Recursos y frecuencia máxima |
| `tools/p7/medir.py` | Gemelo y perfil |
| `tools/p7/rtl.sh` | Confirmación con el RTL |
| `tools/p7/pll.sh` | PLL |
| `tools/p7/doble_frecuencia.sh` | Duplicador de reloj |
| `tools/p7/fuentes.py` | De cada dirección del programa a su línea y su fase |
| `tools/p7/tablas.py` | Tablas, Amdahl, escalera, roofline, ASIC, negativos y macros |
| `ref/gemelo/gemelo.c` | Opción `--perfil` |

## 14. Preguntas para la defensa

1. **¿Por qué compiten con una variante más lenta?** Porque la latencia no da patrimonio mientras la respuesta llegue antes del tick siguiente, y R1 usa el 19,6 % del plazo. Lo que se elige es el algoritmo y el riesgo. La tabla lo muestra: el segmentado es 1,86 veces más rápido que R0, R1 es 5,4 veces más lento, y hace 7 veces más trabajo útil por tick.
2. **¿Qué es una operación útil en su kernel?** Las 8 operaciones de la regla escrita en su forma matemática: 4 para la media, 4 para decidir. Sección 3.
3. **¿Qué parte del tick consume más ciclos?** En R0, actualizar la media: 29 de 51 ciclos del kernel. En la respuesta, decidir (14 de 41). En el tick completo, esperar: 98 %. Sección 6.
4. **¿Por qué Amdahl acierta exacto en el barrel y no en el segmentado?** En el barrel toda instrucción cuesta 4 ciclos. En el segmentado el salto tomado cuesta 2 y no 3 como estimó la clase, y la detección del sondeo no escala exacto con la vuelta del lazo. Sección 7.
5. **¿Por qué el kernel está a la derecha del quiebre del roofline?** Porque mueve 8 a 13 bytes por tick y hace 8 operaciones: 0,6 a 1 Op/B contra 0,125. Está limitado por el cómputo. Sección 8.
6. **¿Por qué no usaron el PLL?** El VQ100 no lo tiene: nextpnr no lo puede ubicar. En un TQ144 R1 cerraría a 50 MHz, pero no ganaría patrimonio. Sección 9.
7. **¿Por qué no hay base con la extensión?** Porque `emad` y `devk` están en el core barrel y llevarlas al base toca el RTL de R0, que ya pasó la puerta. Está predicho: 31 ciclos de respuesta, 1,32 veces R0. Sección 4.
8. **¿Dónde se va la energía?** En esperar. Decidir cuesta 2,6 nJ sobre 2,8 uJ por tick en el ASIC. Sección 10.
