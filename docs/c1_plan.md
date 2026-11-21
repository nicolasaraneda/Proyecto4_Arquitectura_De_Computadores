# Plan de C1 como cuarto peldaño (R3)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Rama `c1`, creada desde `banda-40`. Escrito el 21/11. Este documento es el paso 1 del encargo: el plan, con los presupuestos medidos sobre un borrador que ya ensambla y corre. **Dos presupuestos quedan fuera de lo pedido (sección 9) y por eso el trabajo se detiene aquí, con opciones para decidir (sección 10).** Nada de esto toca R0, R1 ni R2.

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

Periféricos: `0x8001_0000` SPI (solo el hilo 0), `0x8000_0000` periférico de la placa (el hilo 0 escribe los LED; el hilo 3 lee los interruptores y escribe los 7 segmentos), `0x8002_0000` tabla de solo lectura.

## 6. Degradación

Las mismas reglas de R2, con el hilo 0 decidiendo siempre:

1. El hilo 0 calcula la banda 40 en cada tick, antes de mirar lo que publican los demás.
2. Usa la política solo si `D_POL` trae el tick actual. La espera con un plazo de 28 vueltas de 6 instrucciones (24 ciclos cada una).
3. Vencido el plazo, si `D_POL` es del tick anterior, sostiene esa orden si era completa (comprar 63 o vender 63, que son idempotentes) y si era parcial mantiene, porque repetir una parcial compra de más. Es un tick: el hilo atrasado se pone al día en el siguiente.
4. Vencido el plazo, si `D_POL` es más vieja o nunca llegó, pasa a **modo seguro**: banda 40 sin política y sin espera, hasta el final. Un hilo que se saltó un tick ya no tiene una cuenta exacta, así que no se vuelve a confiar en él.
5. También pasa a modo seguro si llega un precio menor que 100 (la serie no está normalizada como supone el modelo) o si la ronda pasa de 20 000 ticks (el reloj del modelo ya no vale). Con rondas seguidas sin reset, la segunda ronda corre en modo seguro, que es lo que hace R2.
6. Con `POLITICA` en 0 parte en modo seguro: la banda 40 exacta de R2, byte por byte.

El hilo 0 publica siempre el byte que escribió de verdad, venga de la política o del respaldo, y el hilo 3 ejecuta ese. Así la cuenta propia sigue exacta aunque se use el respaldo. Un hilo 1 o 2 colgado deja al hilo 3 esperando y el hilo 0 termina en modo seguro por la regla 4. El vigilante de R2 no cambia: el hilo 0 escribe `DECISION` en todos los ticks.

## 7. Telemetría: el patrimonio propio en la placa

Propuesta para el día de prueba, ya incluida en el borrador. **No cuesta ninguna celda: es solo programa** (13 palabras y unas 45 instrucciones por tick fuera del camino de la respuesta).

- El hilo 3 calcula en cada tick el patrimonio propio emulado, caja más acciones por el precio, y lo deja en una palabra de datos.
- Los dos dígitos de 7 segmentos muestran un byte de esa palabra en hexadecimal. Los interruptores 1 y 2 eligen cuál: ninguno apretado, el byte bajo; el 1, el segundo byte; el 2, el tercero (patrimonio sobre 65 535); los dos, el modo (00 fase A, 01 recuperación, 02 candado).
- Al terminar la ronda no llegan más precios y el valor queda fijo: se lee el byte bajo, se aprieta el interruptor 1 y se lee el segundo. Por ejemplo, 22 682 es `0x589A`: se ve `9A` y, con el interruptor 1, `58`. Se compara con el patrimonio que muestra la maestra.
- LED 0: modo seguro (encendido si la política quedó fuera).

En la simulación el patrimonio emulado coincide con el de la contabilidad oficial en todas las ventanas comparadas (sección 8).

## 8. Qué está hecho y medido del borrador

| Paso | Resultado | Dónde |
|------|-----------|-------|
| Tablas desde el modelo | Calculadas desde cero; 0 celdas distintas contra las de la exploración | `ref/c1/tablas.py`, `sw/c1_tabla.hex` |
| Referencia entera contra el C1 de la exploración (paso 2 del encargo) | 2400 ventanas de las cinco empresas, 48 millones de bytes: **0 bytes distintos** contra `v5.V5Ref`, 0 diferencias de órdenes y de patrimonio contra `v5.fase_a` más `v5.post` (la del examen), 0 en D final. Con la política apagada, 0 diferencias contra la banda 40 de `ref/fondo.py` | `docs/mediciones/c1/contra_exploracion.txt` |
| Borrador del programa contra la referencia, por el RTL | Serie Meta completa a 0,1 ms: 20 000 bytes y el estado de los 20 000 ticks idénticos; patrimonio 22 682 contra 21 392 de la banda 40. 40 ventanas reales de 20 000 ticks a 0,1 ms: 40 de 40 idénticas en bytes y estado | `tools/c1/caso.py`, `tb/c1/tb_c1.sv` |
| Degradación, primera prueba | Hilo 3 colgado en el tick 5000: sostiene un tick, pasa a modo seguro y sigue con la banda 40, con los mismos bytes que la referencia; respuesta de 907 ciclos en los dos ticks con el plazo vencido y de unos 200 después | misma herramienta, con `--faltas` |
| Síntesis del hardware de R3 | 1038 celdas, 14 bloques, 10 de 10 semillas a 25 MHz, mínima 48,41 MHz | `build/variantes/c1_r3` |
| R0 y R2 después del cambio de RTL | El `.asc` de cada uno es idéntico al de antes del cambio, con la misma semilla | `build/variantes/c1_ctl_*` |

No está hecho: las puertas (paso 5), el barrido de fases y alineaciones, el estrés, el gemelo con la tabla de 512, los bitstreams y la integración local.

## 9. Presupuestos

Umbral pedido: 85 % de cada presupuesto.

| Recurso | Presupuesto | Uso medido | % | Estado |
|---------|-------------|------------|---|--------|
| Operaciones por hilo y por tick a 0,1 ms | 565 | Hilo 0: 202. Hilo 1: 135. Hilo 2: 158. Hilo 3: 228 (máximos de las series medidas, contando las vueltas de espera entre hilos) | 40 % | Dentro |
| Camino de la respuesta, caso sano | 1131 ciclos (la mitad de 2262) | 799 en el peor tick de 41 series; promedio 497 a 516 | 71 % | Dentro |
| Camino de la respuesta con el plazo vencido | 1131 ciclos | 907 con el plazo de 28 vueltas (955 con 30) | 80 % | Dentro, con poco margen |
| Bytes de tabla nuevos | 3 bloques de 512 bytes | 1 bloque. La tabla usa 348 de sus 512 palabras | 33 % de los bloques, 68 % de la tabla | Dentro |
| Celdas | Unas 235 libres (265 medidas en R2: 1015 de 1280) | 23 más que R2 | 9 % a 10 % | Dentro |
| Temporización | 25 MHz en 10 de 10 semillas | 48,41 MHz la mínima | | Dentro |
| **Memoria del programa** | **512 palabras** | **482** | **94,1 %** | **Pasa del 85 %** |
| **Hardware** | El de R2 | Tabla de 512 palabras: un módulo nuevo y una síntesis nueva | | **Exige cambiar hardware** |

**Memoria del programa.** No estaba medida en la exploración (15.10 lo advertía). Con todo lo pedido el programa ocupa 482 palabras y quedan 30. Es un recurso estático: el programa cabe o no cabe al ensamblar, y cabe. Lo que se pierde es margen para cambios. Revisé qué se puede recortar sin cambiar lo que decide:

| Recorte | Palabras | Costo |
|---------|----------|-------|
| `producto` como lazo en vez de 8 pasos escritos | 24 | Estimado, no medido: 17 instrucciones más en el camino de la respuesta. El peor caso sano subiría a unos 870 ciclos (77 %) y con plazo vencido a unos 980 (87 %) |
| Sin telemetría (7 segmentos y LED) | 13 | Se pierde lo del paso 6 |
| Sin el chequeo de tick saltado del hilo 3 y sin guardar D | 4 | Menos red de seguridad y menos estado para comparar |

Con los tres recortes queda en 441 palabras (86,1 %): ni así baja del 85 %, y cada uno cuesta algo. No hay cómo agrandar la memoria del programa: 512 palabras más son 8 bloques y quedan 2.

**Hardware.** C1 no cabe en el hardware de R2 sin tocarlo. Las celdas de las tablas son 640 bytes; la tabla de R2 tiene 252 palabras libres (504 bytes) y la memoria del programa ya está al 94 %. El cambio mínimo es duplicar la tabla: `rtl/pochoco_tabla512.v` (el mismo módulo con 512 palabras) y un `ifdef` en `rtl/pochoco_soc.v`. Sin la definición `ESPINO_TABLA_512` el SoC es texto idéntico al de antes y R0, R1 y R2 no cambian (comprobado con la síntesis). Lo que el cambio implica:

- R3 no es "el molde de R2 más `icebram`". Es una síntesis nueva, con su propio molde, su temporización (ya medida), su bitstream simulado y su imagen múltiple.
- El hardware de R3 no es el que ya pasó por la maestra el 18/11. Para competir tendría que pasar la prueba del 26/11 por su cuenta, igual que R1 y R2 con banda 40. El core, el SPI y el vigilante son los mismos; cambia una memoria de solo lectura.
- La verificación del core (criterio 5) y la equivalencia formal de la extensión no dependen de la tabla. El gemelo del barrel hay que ampliarlo a la tabla de 512 para las corridas largas.

## 10. Opciones, sin decidir

| Opción | Qué es | Qué se gana | Qué se pierde o arriesga |
|--------|--------|-------------|--------------------------|
| **A. Seguir con el borrador tal como está** | Tabla de 512 palabras (1 bloque y 23 celdas más), programa de 482 palabras | Es lo que ya decide igual que la referencia en 41 series. Camino de la respuesta en 71 %. Telemetría incluida | Memoria del programa al 94 %: 30 palabras para cualquier arreglo que pidan las puertas. Hardware nuevo, con su propia prueba el 26/11 |
| **B. Seguir con el programa recortado** | Lo mismo con `producto` en lazo (458 palabras, 89 %) | 54 palabras libres en vez de 30 | Peor caso sano en unos 77 % y con plazo vencido en unos 87 % (estimados): se cambia margen de memoria por margen de tiempo. Sigue sobre el 85 % en memoria |
| **C. No construir R3** | C1 queda como referencia entera verificada y borrador medido, en la rama `c1` | No se gasta más tiempo antes del corte del 22/11 y del congelamiento del 25/11. La banda 40 queda intacta, como respaldo y como titular | C1 no llega a la placa |

No hay una opción sin cambio de hardware: el programa y las tablas juntos no caben en la memoria de R2.

Mi recomendación, etiquetada como mía: **la opción A**. El 94 % es de un recurso que no falla en vivo, y el recorte de B gasta el margen que sí importa en vivo, que es el tiempo. Si en las puertas aparece un arreglo que no quepa en 30 palabras, el primer recorte sería la telemetría de los LED y después `producto` en lazo. Lo que decide entre A y C no es técnico: es si vale la pena llevar a la maestra un hardware que cambió, a cinco días de la prueba, por un desempate cuyo efecto en la nota la exploración midió en menos de una centésima y media.

Decisiones que necesito para seguir:

1. A, B o C.
2. Si es A o B: confirmar que la tabla de 512 palabras es un cambio de hardware aceptado para R3.

## 11. Si se sigue: lo que falta, en orden

1. Herramienta de variantes con fallas y referencia de la degradación para todas las pruebas del criterio 6.
2. Gemelo del barrel con la tabla de 512 palabras y `lbu` sobre la tabla, validado contra el RTL.
3. Puertas del paso 5: (a) política apagada contra la banda 40 de R2; (b) assembly contra la referencia en Tesla, AMD, Meta y al menos 200 ventanas a los tres ritmos; (c) la puerta de simulación de R1 y R2 (oficial, equivalencia, fases y alineaciones, degradación, controles negativos, estrés, bitstream por los pines, relevo) y la integración local; (d) síntesis.
4. Molde, bitstreams de R3 con y sin vigilante, imagen múltiple con R0 de respaldo, y sus hash.
5. Documento de estudio, `docs/puertas.md`, `docs/estado.md` y la bitácora.

## 12. Cómo reproducir lo de este documento

| Qué | Comando |
|-----|---------|
| Tablas desde el modelo (menos de 10 minutos la primera vez) | `python3 ref/c1/tablas.py --calcular` |
| Programa y tabla de la placa | `python3 tools/c1/generar.py` y `python3 tools/c1/generar.py --check` |
| Referencia sobre una serie | `python3 ref/c1/c1.py data/practica_meta.csv` |
| Referencia contra la exploración (necesita la carpeta de `minutos-reales` y los minutos reales) | `python3 tools/c1/contra_exploracion.py --ventanas 2400 --salida docs/mediciones/c1/contra_exploracion.txt` |
| Un caso por el RTL, con mediciones | `python3 tools/c1/caso.py build/c1/casos/meta --nticks 20000 --inicio-ns 200000 --medir` (antes, compilar `tb/c1/tb_c1.sv` con Verilator y las definiciones de R3) |
| Recursos y temporización de R3 | `DEFS="-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA -DESPINO_TABLA_512 -DESPINO_VIGILANTE" HEX=build/c1/c1.hex tools/medir_variante.sh c1_r3 10` |
