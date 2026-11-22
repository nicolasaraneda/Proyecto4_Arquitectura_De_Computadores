# Plan de C1 como cuarto peldaño (R3)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Rama `c1`, creada desde `banda-40`. Escrito el 21/11. Este documento es el paso 1 del encargo: el plan, con los presupuestos medidos. Dos presupuestos quedaban fuera de lo pedido (sección 9: la memoria del programa al 94 % y el cambio de hardware) y el trabajo se detuvo ahí. **Nicolás eligió seguir con la opción A (sección 10); las puertas se construyeron y pasaron, y su estado está en `docs/puertas.md`.** Nada de esto toca R0, R1 ni R2.

## 1. Qué es C1 y qué se construye

C1 es el candidato de la exploración (rama `minutos-reales`, `docs/exploracion_ideas.md`, sección 15, y el examen de `docs/mediciones/exploracion/c1_examen.txt`). Es la banda 40 de R2 con un desempate:

| Pieza | Cuándo | Qué hace |
|-------|--------|----------|
| Fase A | Antes de ver el 100 o el 255, desde el tick 390 | Toma media posición solo si la tabla da probabilidad de 0,95 o más de que el 255 llegue antes que el 100. Sale cuando la tabla lo dice |
| Motor | Desde el primer extremo | Decide con la política óptima V2 del paseo normalizado, comprimida a 8 tramos, hasta ganarle 100 a un clon de la banda 40 |
| Candado | Cuando D (patrimonio propio menos el del clon) llega a 100 | Copia al clon hasta el final de la ronda |

Para eso el programa lleva dos cuentas exactas con la contabilidad oficial (la propia y la del clon), la clase de volatilidad con histéresis, los tramos de tiempo y una máquina de tres modos. R3 es el Espino barrel de R2 (4 hilos, vigilante) con ese programa y con una tabla más grande.

## 2. Reparto de los cuatro hilos

| Hilo | Rol | Qué calcula | Qué publica |
|------|-----|-------------|-------------|
| 0 | Corredor | Lee `PRICE`. Calcula la banda 40 por su cuenta, con la misma cuenta sin saltos de `sw/fondo.s`. Lleva el modo seguro. Espera la política del tick con plazo y escribe `DECISION` una vez. Es el único que toca el SPI | `D_PUB` (tick y precio), `D_FOFF` y `D_FASE` (fase y byte de la banda 40), `D_ORD` (el byte que escribió) |
| 1 | Régimen | S2 con diferencias topadas en 15, las siete sumas N_j (t - 1), la clase de v² con histéresis de 64 ticks, y el reloj de los tramos de 1250 y de 2500 ticks | `D_REG` (tick y tabla activa), `D_REGA` y `D_REGM` (dirección de la celda de la fase A y del motor) |
| 2 | Política | Lee la celda de la tabla: posición de la fase A (entrada con posición 0, salida con media) y posición del motor | `D_TAB` (tick, tabla activa, posición del motor, entra, posición de la fase A) |
| 3 | Emulador | Ejecuta al precio nuevo el byte propio y el del clon, D, la máquina de modos (fase A, recuperación, candado), el objetivo de la media posición y el byte de la política. Después, fuera del camino de la respuesta, el patrimonio propio y la telemetría | `D_POL` (tick y byte de la política) |

El orden de un tick:

```
hilo 0                      hilo 1                 hilo 2                  hilo 3
sondea STATUS, lee PRICE
D_PUB = tick, precio  --->  ve D_PUB               ve D_PUB                ve D_PUB
banda 40                    D_REG (casi siempre    espera D_REG            cuenta propia (D_ORD del tick anterior)
D_FOFF, D_FASE              antes de calcular)     espera D_FASE           cuenta del clon
espera D_POL del tick       S2, sumas, clase       lee la celda            D, espera D_FASE, modos
  (plazo)                   reloj                  D_TAB                   espera D_TAB, byte
DECISION                                                                   D_POL
D_ORD                                                                      patrimonio, 7 segmentos
```

Cada palabra tiene un solo hilo que la escribe, y lo publicado lleva el número de tick en los bits 31:8, como en el fondo de P3 (`docs/fondo.md`, sección 3). Con los cuatro hilos sanos la decisión no depende de cuánto demora cada uno, y por eso la referencia no modela ciclos.

El hilo 1 publica antes de calcular casi siempre: la clase solo puede cambiar en el tick 390 y cuando la cuenta de la histéresis está en 63. En esos ticks calcula primero y publica después.

## 3. Aritmética sin multiplicar ni desplazar

Todo son sumas, restas, comparaciones, and, or, xor y lecturas. La extensión de la ISA no se usa.

| Operación | Cómo | Costo en el peor caso (contado sobre el código) |
|-----------|------|-----------------------|
| Ejecutar una orden (compra o venta, hasta 63) | Una sola rutina voraz con los múltiplos p, 2p, ..., 32p (5 sumas por tick): resta del saldo de mayor a menor mientras quede cantidad y alcance. En la compra el saldo es caja menos comisión, y lo que queda es la caja nueva; no hace falta dividir. En la venta el saldo es el complemento de la caja: restar de él es sumar a la caja | 51 instrucciones |
| D = caja - caja del clon + (acc - acc del clon) p | Producto por los 8 bits de p, con duplicaciones. Exacto para cualquier diferencia, con signo. Si las acciones son iguales no se calcula | 35 instrucciones |
| Objetivo de la media posición, floor(W / 2p), tope 511 | División con restas de 9 pasos. Se adelanta en cada tick de la fase A sin posición, antes de esperar al hilo 2 | 64 instrucciones |
| Clase de v² | 64 S2 contra las siete sumas N_j (t - 1), que crecen N_j por tick | 63 instrucciones, fuera del camino casi siempre |
| Tramos | Dos contadores que bajan: cada 1250 y cada 2500 ticks el tramo baja uno, hasta 0 | 16 instrucciones |
| Dos niveles por celda | La palabra de 16 bits de la tabla guarda dos bytes; `lbu` en la dirección y en la dirección más 1 | 1 instrucción |

## 4. Tablas

Las genera `ref/c1/tablas.py` desde `ref/c1/paseo.py`, que es el cálculo de `paseo_optimo.py` de la exploración copiado sin cambiar ninguna operación (núcleo, probabilidades y programación dinámica). Entran v², el largo de la ronda, los niveles 100 y 255 y el costo relativo de la comisión. **No entra ningún precio.** El cálculo completo desde cero demora menos de 10 minutos con 20 procesos y da las mismas 320 celdas que la exploración tenía en caché (0 diferencias).

Formato de la tabla de la placa: 512 palabras de 16 bits en `0x8002_0000`, la palabra i en el desplazamiento 4 i (`sw/c1_tabla.hex`).

| Palabras | Contenido |
|----------|-----------|
| 0 a 3 | Los cuatro umbrales de la banda 40, en las mismas posiciones que en R2: 101, 255, 141 y 215 |
| 4 | `POLITICA`: 1 es C1; **0 apaga la política** y queda la banda 40 exacta. Es el valor reservado: la tabla de R2 tiene un 0 ahí |
| 16 a 31 | 64 d² para d de 0 a 15 |
| 32 a 38 | Los cortes de la clase, N_j: 11, 20, 28, 39, 55, 78 y 111 sesenta y cuatroavos |
| 64 a 191 | Fase A: celda clase × 16 + tramo. Byte bajo: nivel de entrada (entra si p ≥ nivel). Byte alto: nivel de salida (mantiene si p ≥ nivel) |
| 192 a 383 | Motor: celda fase × 64 + clase × 8 + tramo, con B 0, C 1 y D 2. Byte bajo: con posición 0 pasa a invertido si p ≤ nivel. Byte alto: invertido, se mantiene si p ≤ nivel |
| El resto | Libre (164 palabras) |

Dos cosas que el formato aprovecha y que el generador comprueba cada vez:

- En las 192 celdas del motor los umbrales `alto` y `salida` de la exploración valen 256 (nunca). No se guardan: la celda baja de 4 bytes a 2 y la tabla del motor de 768 a 384 bytes.
- En la fase A la condición "umbral de V3 y probabilidad de 0,95 o más" es un solo umbral en las 128 celdas (la probabilidad es monótona en el precio). Un nivel 256 se guarda como 255: en la fase A el precio está entre 101 y 254.

Total: 640 bytes de celdas, no los 1024 que estimaba la exploración.

Los parámetros de la contabilidad no van en la tabla sino en palabras de datos del programa, para no gastar instrucciones en copiarlos al arrancar: caja inicial 10 000, comisión 5, M 100, largo de la ronda 20 000, precio mínimo válido 100, plazo 28 y el tick 390. Los fija `tools/c1/generar.py` y se cambian generando el programa de nuevo; entra por `icebram` igual que la tabla.

## 5. Mapa de memoria

Memoria del programa: 512 palabras de 32 bits, código y datos juntos (medido sobre `sw/c1.s`).

| Bloque | Palabras |
|--------|----------|
| Tabla de arranque | 4 |
| Hilo 0, corredor (58 hasta el lazo de espera de la política, 22 del plazo y la escritura) | 80 |
| Lazo de un hilo que se saltó un tick | 1 |
| Hilo 1, régimen y reloj | 99 |
| Hilo 2, política | 51 |
| Hilo 3, emulador (sin las rutinas) | 114 |
| Rutina `ejecutar` (compartida por las dos cuentas) | 62 |
| Rutina `producto` | 33 |
| **Código** | **444** |
| Datos (`0x768` a `0x7FC`): 7 del hilo 0, 17 del hilo 1, 1 del hilo 2 y 13 del hilo 3 | 38 |
| **Total** | **482 de 512 (94,1 %)** |
| Libres | 30 |

Periféricos: `0x8001_0000` SPI (solo el hilo 0), `0x8000_0000` periférico de la placa (el hilo 0 escribe los LED; el hilo 3 lee los botones y escribe los 7 segmentos), `0x8002_0000` tabla de solo lectura.

## 6. Degradación

Las mismas reglas de R2, con el hilo 0 decidiendo siempre:

1. El hilo 0 calcula la banda 40 en cada tick, antes de mirar lo que publican los demás.
2. Usa la política solo si `D_POL` trae el tick actual. La espera con un plazo de 28 vueltas de 6 instrucciones (24 ciclos cada una).
3. Vencido el plazo, si `D_POL` es del tick anterior, sostiene esa orden si era completa (comprar 63 o vender 63, que son idempotentes) y si era parcial mantiene, porque repetir una parcial compra de más. Es un tick: el hilo atrasado se pone al día en el siguiente.
4. Vencido el plazo, si `D_POL` es más vieja o nunca llegó, pasa a **modo seguro**: banda 40 sin política y sin espera, hasta el final. Un hilo que se saltó un tick ya no tiene una cuenta exacta, así que no se vuelve a confiar en él.
5. También pasa a modo seguro si llega un precio menor que 100 (la serie no está normalizada como supone el modelo) o si la ronda pasa de 20 000 ticks (el reloj del modelo ya no vale). Con rondas seguidas sin reset, la segunda ronda corre en modo seguro, que es lo que hace R2.
6. Con `POLITICA` en 0 parte en modo seguro: la banda 40 exacta de R2, byte por byte.

El hilo 0 publica siempre el byte que escribió de verdad, venga de la política o del respaldo, y el hilo 3 ejecuta ese. Así la cuenta propia sigue exacta aunque se use el respaldo. Un hilo 1 o 2 colgado deja al hilo 3 esperando y el hilo 0 termina en modo seguro por la regla 4. El vigilante de R2 no cambia: el hilo 0 escribe `DECISION` en todos los ticks.

Lo que mostraron las pruebas de degradación (`make c1-degradacion`, `docs/mediciones/c1/degradacion.txt`), además de lo anterior:

- **En el candado los hilos 1 y 2 ya no hacen falta.** El hilo 3 copia al clon con lo que publica el hilo 0 y no espera a nadie más. Si el hilo 1 o el 2 se cuelga después del candado, la política sigue llegando a tiempo y es la banda 40: no hay plazo vencido ni modo seguro, y los bytes son los mismos.
- **Dos atrasos seguidos.** Si la política del tick n llega después del plazo, queda como "la del tick anterior" para el tick n + 1. La referencia distingue los dos casos: `faltas` (no llega nunca) y `tardias` (llega tarde).
- **Límite conocido, sin corregir.** El hilo 3 lee `D_ORD` (el byte que el hilo 0 escribió en el tick anterior) apenas ve el precio, unos 90 ciclos después de `byte_done`, y no mira su número de tick. El hilo 0 la reescribe a los 200 ciclos en modo seguro y a los 500 a 907 en modo normal. Para leer la del tick equivocado el hilo 3 tendría que partir más de 100 ciclos tarde, y no tiene de quién esperar antes de ese punto: en el programa sano no pasa, y un hilo 3 que se salta un precio se detiene solo (lazo `muerto`). Cerrarlo del todo cuesta 4 palabras y 16 ciclos en el camino de la respuesta; queda anotado y no se aplicó.

## 7. Telemetría: la cuenta emulada en la placa

**No cuesta ninguna celda: es solo programa** (13 palabras y unas 45 instrucciones por tick fuera del camino de la respuesta). Los pasos del día de prueba están en `docs/c1_dia_de_prueba.md`.

- El hilo 3 calcula en cada tick el patrimonio propio emulado, caja más acciones por el precio, y lo deja en una palabra de datos (`D_W`), con el modo en su byte alto. Las tres palabras que siguen son la caja propia, las acciones propias y la caja del clon.
- Los dos dígitos de 7 segmentos muestran en hexadecimal un byte de esas cuatro palabras. Los cuatro botones eligen cuál (0 a 15, SW1 es el bit 0): bytes 0 a 2, el patrimonio; byte 3, el modo (00 fase A, 01 motor, 02 candado); 4 a 7, la caja; 8 a 11, las acciones; 12 a 15, la caja del clon.
- Por ejemplo, 22 682 es `0x589A`: se ve `9A` y, con SW1 apretado, `58`. Se compara con el patrimonio que muestra la maestra.
- **Límite: el display solo se actualiza cuando llega un precio.** Los botones se leen y los 7 segmentos se escriben una vez por tick, fuera del camino de la respuesta. Al terminar la ronda el display queda congelado en el byte que elegían los botones en el último precio, y apretar botones después no cambia nada. Sin tocar nada queda el byte bajo del patrimonio; los demás bytes se leen en vivo (cómodo a 10 ms) o manteniendo la combinación apretada hasta el final. Corregirlo es mover esas cuatro instrucciones al lazo de espera del hilo 3: cero palabras, y hasta 16 ciclos más en el camino de la respuesta porque el lazo pasa de 2 a 6 instrucciones. Cambia el binario y obliga a repetir las puertas; no se aplicó porque el bitstream de R3 está congelado.
- LED1: modo seguro (encendido si la política quedó fuera).
- `python3 ref/c1/c1.py SERIE.csv --placa` imprime lo que debe verse con cada combinación de botones.

El borrador mostraba solo el patrimonio y el modo (botones 1 y 2). Mostrar la caja y las acciones no costó palabras: cambió la máscara de los botones (de 3 a 15) y el orden de cuatro datos. `make c1-ticks` corre una ventana con cada una de las 16 combinaciones y compara el byte mostrado con la referencia en cada tick.

## 8. Qué está hecho y medido

El detalle de cada puerta, con sus registros, está en `docs/puertas.md` (sección de R3). Resumen:

| Paso | Resultado | Dónde |
|------|-----------|-------|
| Tablas desde el modelo | Calculadas desde cero; 0 celdas distintas contra las de la exploración | `ref/c1/tablas.py`, `sw/c1_tabla.hex` |
| Referencia entera contra el C1 de la exploración (paso 2 del encargo) | 2400 ventanas de las cinco empresas, 48 millones de bytes: **0 bytes distintos** contra `v5.V5Ref`, 0 diferencias de órdenes y de patrimonio contra `v5.fase_a` más `v5.post` (la del examen), 0 en D final | `docs/mediciones/c1/contra_exploracion.txt` |
| Gemelo con la tabla de 512 palabras contra el RTL de R3 | 17 configuraciones, 42 millones de eventos idénticos ciclo a ciclo | `docs/mediciones/c1/cosim.txt` |
| Puerta a: política apagada | R3 escribe los mismos bytes que R2 en 46 corridas por el RTL (archivos idénticos) y en 203 series a los tres períodos en el gemelo | `docs/mediciones/c1/puerta_a.txt` |
| Puerta b: assembly contra referencia | Tesla, AMD y Meta por el RTL a 0,1 y 1 ms, Meta a 10 ms, 200 ventanas a 0,1 ms y las 203 series en el gemelo a los tres períodos: todo idéntico, en bytes y en estado | `docs/mediciones/c1/puerta_b.txt` |
| Puerta c: la puerta de simulación de R0 a R2 | Los criterios 1 a 8 pasan | `docs/mediciones/c1/puerta.txt` |
| Puerta d: síntesis | 1038 celdas, 14 bloques, 10 de 10 semillas a 25 MHz, mínima 48,41 MHz | `docs/mediciones/c1/timing.txt` |
| R0 y R2 después del cambio de RTL | El `.asc` de cada uno es idéntico al de antes del cambio, con la misma semilla. Sin `-DESPINO_TABLA_512` el SoC no instancia el módulo nuevo | `build/variantes/c1_ctl_*`, `docs/mediciones/c1/tb_tabla.txt` |

## 9. Presupuestos

Umbral pedido: 85 % de cada presupuesto.

| Recurso | Presupuesto | Uso medido | % | Estado |
|---------|-------------|------------|---|--------|
| Operaciones por hilo y por tick a 0,1 ms | 565 | Hilo 0: 202. Hilo 1: 135. Hilo 2: 158. Hilo 3: 228 (máximos de las series medidas, contando las vueltas de espera entre hilos; en la serie Meta, 196, 133, 156 y 218) | 40 % | Dentro |
| Camino de la respuesta, caso sano | 1131 ciclos (la mitad de 2262) | 807 en el peor tick de las puertas (203 series reales, 1081 sintéticas y el barrido de fases); promedio 500 a 530 | 71 % | Dentro |
| Camino de la respuesta con el plazo vencido | 1131 ciclos | 916 barriendo 24 fases con el hilo 3 colgado (907 en la fase del testbench oficial), con el plazo de 28 vueltas | 81 % | Dentro, con poco margen |
| Bytes de tabla nuevos | 3 bloques de 512 bytes | 1 bloque. La tabla usa 348 de sus 512 palabras | 33 % de los bloques, 68 % de la tabla | Dentro |
| Celdas | Unas 235 libres (265 medidas en R2: 1015 de 1280) | 23 más que R2 | 9 % a 10 % | Dentro |
| Temporización | 25 MHz en 10 de 10 semillas | 48,41 MHz la mínima | | Dentro |
| **Memoria del programa** | **512 palabras** | **482** | **94,1 %** | **Pasa del 85 %. Aceptado por Nicolás (opción A)** |
| **Hardware** | El de R2 | Tabla de 512 palabras: un módulo nuevo y una síntesis nueva | | **Exige cambiar hardware. Aceptado por Nicolás (opción A)** |

**Memoria del programa.** No estaba medida en la exploración (15.10 lo advertía). Con todo lo pedido el programa ocupa 482 palabras y quedan 30. Es un recurso estático: el programa cabe o no cabe al ensamblar, y cabe. Lo que se pierde es margen para cambios. Las puertas no pidieron ningún arreglo del programa, así que las 30 palabras siguen libres. Los recortes posibles, que ni juntos bajan del 85 % (441 palabras, 86,1 %), están en la sección 10 como reserva. No hay cómo agrandar la memoria del programa: 512 palabras más son 8 bloques y quedan 2.

**Hardware.** C1 no cabe en el hardware de R2 sin tocarlo. Las celdas de las tablas son 640 bytes; la tabla de R2 tiene 252 palabras libres (504 bytes) y la memoria del programa ya está al 94 %. El cambio mínimo es duplicar la tabla: `rtl/pochoco_tabla512.v` (el mismo módulo con 512 palabras) y un `ifdef` en `rtl/pochoco_soc.v`. Sin la definición `ESPINO_TABLA_512` el SoC es texto idéntico al de antes y R0, R1 y R2 no cambian (comprobado con la síntesis). Lo que el cambio implica:

- R3 no es "el molde de R2 más `icebram`". Es una síntesis nueva, con su propio molde (`bitstreams/moldes/r3_molde.asc.gz`), su temporización, su bitstream simulado por los pines y su imagen múltiple.
- El hardware de R3 no es el que ya pasó por la maestra el 18/11. Para competir tiene que pasar la prueba del miércoles 25/11, por confirmar por su cuenta. El core, el SPI y el vigilante son los mismos; cambia una memoria de solo lectura.
- La verificación del core (criterio 5) se repitió igual sobre el SoC de R3, y el gemelo del barrel se amplió a la tabla de 512 palabras y se validó contra el RTL.

## 10. Decisión y reserva de recortes

**Decisión de Nicolás (21/11): opción A.** Se sigue con el borrador tal como está: tabla de 512 palabras (hardware nuevo para R3, un bloque de memoria y 23 celdas más que R2) y programa de 482 palabras. Las opciones que se presentaron fueron A (seguir así), B (seguir con el programa recortado) y C (no construir R3); quedan en la decisión T151.

No hay una versión de C1 sin cambio de hardware: el programa y las tablas juntos no caben en la memoria de R2.

### Reserva: los recortes de la opción B (no aplicados)

Quedan 30 palabras libres entre el código y los datos. Si un arreglo necesita más, estos son los recortes, en el orden en que conviene aplicarlos. **Ninguno está aplicado.** Cada uno cambia el binario, así que después de aplicarlo hay que repetir todas las puertas (`make c1-puerta`).

| N.º | Recorte | Palabras que libera | Costo en el camino de la respuesta | Qué se pierde | Dónde se hace |
|-----|---------|---------------------|-------------------------------------|---------------|---------------|
| 1 | Sacar la telemetría de la cuenta (el bloque del hilo 3 después de publicar `D_POL`: producto de las acciones por el precio, `D_W`, lectura de botones y escritura de los 7 segmentos) | 13 | Ninguno: está fuera del camino | Leer en la placa el patrimonio, la caja y el modo. Queda el LED1 de modo seguro. `tools/c1/caso.py` compara `D_W` y los 7 segmentos: hay que sacar esas dos comparaciones | `tools/c1/generar.py`, plantilla, entre "fuera del camino de la respuesta" y `j h3_espera` |
| 2 | Sacar el chequeo de tick saltado del hilo 3 (`addi x15`, `bne ... muerto`) y la palabra `D_DIF` con su store | 4 | 2 instrucciones menos (8 ciclos a favor) | Que un hilo 3 que se salta un precio se detenga solo. Seguiría publicando con la cuenta corrida en un tick. `D_DIF` solo la miran las pruebas | Plantilla, inicio del hilo 3 y cálculo de D |
| 3 | `producto` en lazo en vez de desenrollado: 8 vueltas que duplican el resultado, miran el bit 7 de una copia del precio y la duplican | 22 a 24 (la rutina baja de 33 palabras a unas 10) | Unas 17 a 26 instrucciones más (70 a 100 ciclos) en los ticks en que las acciones propias y las del clon difieren. Hay que subir el plazo de 28 a unas 31 vueltas | Margen de tiempo: peor caso sano de unos 870 ciclos (77 % de 1131) y con el plazo vencido de unos 980 (87 %). Estimados, sin medir | Función `producto()` de `tools/c1/generar.py` y `--plazo` |

Con los tres el programa queda en unas 441 palabras (86 %): 71 libres en vez de 30. El orden importa: los dos primeros no gastan tiempo de respuesta, que es el margen que sí importa en vivo; el tercero cambia memoria por tiempo y por eso va al final.

Lo que no se puede recortar sin cambiar lo que C1 decide: la rutina `ejecutar` (la contabilidad oficial exacta, 62 palabras), las siete sumas de la clase de v² y la división de la media posición.

## 11. Estado y pendientes

Las puertas están construidas y su estado, con los números, está en `docs/puertas.md` (sección de R3). Las herramientas:

| Paso del encargo | Dónde | Comando |
|------------------|-------|---------|
| Gemelo con la tabla de 512 palabras, validado contra el RTL | `ref/gemelo/gemelo.c`, `tools/c1/cosim.py` | `make c1-cosim` |
| Herramienta de fallas y referencia de la degradación | `tools/c1/variante.py`, `ref/c1/c1.py` (`faltas` y `tardias`) | `make c1-degradacion` |
| Puerta a: política apagada igual a la banda 40 de R2 | `tools/c1/puerta_a.sh` | `make c1-puerta-a` |
| Puerta b: assembly contra referencia en Tesla, AMD, Meta y 200 ventanas a los tres ritmos | `tools/c1/puerta_b.sh` | `make c1-puerta-b` |
| Puerta c: oficial, equivalencia, fases, core, degradación, controles, estrés y bitstream | `tools/c1/oficial.sh`, `series.sh`, `fases.sh`, `criterio5.sh`, `degradacion.sh`, `controles.sh`, `estres.sh`, `bitstreams.sh` | `make c1-oficial`, `c1-series`, `c1-fases`, `c1-criterio5`, `c1-degradacion`, `c1-controles`, `c1-estres`, `c1-bitstreams` |
| Puerta d: síntesis | `tools/medir_variante.sh`, `tools/c1/bitstreams.sh` | `make c1-timing`, `make c1-bitstreams` |
| Todo en orden, con resumen | `tools/c1/puerta.sh` | `make c1-puerta` |
| Pasos del día de prueba | `docs/c1_dia_de_prueba.md` | |

Pendiente, fuera de este encargo: la puerta de placa y la de maestra (las corre Nicolás), el documento de estudio de R3 para la defensa, y la decisión de qué peldaño compite.

## 12. Cómo reproducir lo de este documento

| Qué | Comando |
|-----|---------|
| Tablas desde el modelo (menos de 10 minutos la primera vez) | `python3 ref/c1/tablas.py --calcular` |
| Programa y tabla de la placa | `python3 tools/c1/generar.py` y `python3 tools/c1/generar.py --check` |
| Referencia sobre una serie | `python3 ref/c1/c1.py data/practica_meta.csv` |
| Referencia contra la exploración (necesita la carpeta de `minutos-reales` y los minutos reales) | `python3 tools/c1/contra_exploracion.py --ventanas 2400 --salida docs/mediciones/c1/contra_exploracion.txt` |
| Un caso por el RTL, con mediciones | `python3 tools/c1/caso.py build/c1/casos/meta --nticks 20000 --inicio-ns 200000 --medir` (antes, compilar `tb/c1/tb_c1.sv` con Verilator y las definiciones de R3) |
| Recursos y temporización de R3 | `DEFS="-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA -DESPINO_TABLA_512 -DESPINO_VIGILANTE" HEX=build/c1/c1.hex tools/medir_variante.sh c1_r3 10` |
