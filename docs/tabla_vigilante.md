# Tabla de parámetros, vigilante y relevo por warm boot

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz. Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Documento de estudio del hardware que el paquete P5 agregó al diseño integrado, y de los peldaños R1 y R2 que salen de él. Todos los números salen de un script y su salida está en `docs/mediciones/fondo/` y `docs/mediciones/vigilante/`. La sección 9 dice con qué comando se obtiene cada uno.

## 1. Resumen

| Peldaño | Hardware | Definiciones | Celdas | BRAM | Frecuencia mínima en 10 semillas |
|---------|----------|--------------|--------|------|-----------------------------------|
| R0 | Espino base | ninguna | 1083 | 12 | 42,43 MHz |
| R1 | Barrel, `emad`, `devk` y tabla | `-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA` | 1029 | 13 | 51,59 MHz |
| R2 | R1 más vigilante y `SB_WARMBOOT` | las de R1 y `-DESPINO_VIGILANTE` | 1045 | 13 | 47,86 MHz |

Qué agrega cada pieza:

- **Tabla** (`rtl/pochoco_tabla.v`): una BRAM de 256 valores de 16 bits que el core solo puede leer. Guarda las 20 constantes del algoritmo de `sw/fondo.s`. Se cambia dentro de un bitstream ya construido con `icebram`, sin sintetizar ni ensamblar.
- **Vigilante** (`rtl/vigilante.v`): cuenta los precios que llegan sin que el programa escriba `DECISION`. Al quinto seguido le pide a la FPGA que se reconfigure con la imagen de respaldo.
- **Imagen múltiple**: un solo archivo para la flash con dos bitstreams. La imagen 0 es R2 y la imagen 1 es R0, sin tocar.

R1 y R2 pasaron los ocho criterios de la puerta de simulación (`docs/puertas.md`). En R2 el vigilante no se disparó en ninguna corrida sana, y su cuenta nunca pasó de 1.

## 2. La tabla de parámetros

### 2.1 Qué es

Es memoria y nada más: no calcula, no mira precios y no decide. Vive en `0x8002_0000`, y el valor i está en el desplazamiento 4 i. El programa la lee con `lw`: el valor de 16 bits llega con extensión de signo a 32, así que un umbral negativo se guarda tal cual. La lectura es registrada, como la de la memoria de datos y la de los periféricos.

No tiene puerto de escritura. Un store a esa dirección no hace nada. El testbench del fondo cuenta cualquier store a la tabla como violación del protocolo.

El contenido es `sw/fondo_tabla.hex`, que genera `python3 ref/fondo.py --tabla-hex`. `make check-tabla` comprueba que el archivo guardado sea el que sale de la referencia, y `ref/test_fondo.py` que los desplazamientos que usa `sw/fondo.s` sigan el orden de `PARAMETROS`.

### 2.2 Cómo la usa el programa

Antes de este paquete la tabla estaba al final de la memoria de datos y se leía con `x0` como base. Ahora necesita un registro con `0x80020000`. El supervisor carga esa base en `x1` una vez por tick, justo después de publicar el precio, y la conserva hasta el voto: una instrucción más por tick. Cada gestor lee sus dos umbrales una sola vez, al arrancar.

Con la tabla en su propia BRAM, la memoria de datos del programa parte entera en cero: `sw/fondo.s` ya no toma ningún valor inicial de su imagen. Ocupa 200 palabras de programa y 13 de estado, 213 de 512.

### 2.3 Costo

Respecto del mismo SoC sin la tabla (990 celdas y 12 BRAM, medido en P3): 39 celdas y 1 BRAM. La mayor parte son el multiplexor de lectura de 32 bits que se agrega al bus de datos y la decodificación de la dirección.

### 2.4 Un error que la simulación del RTL no veía

La primera versión del módulo dejaba la memoria en cero con un lazo y después leía el archivo con `$readmemh`, igual que el prototipo de la factibilidad. En simulación funciona. En síntesis, Yosys se queda con los ceros y descarta el archivo: **la BRAM salía vacía en el bitstream**. Con la tabla en cero todos los umbrales valen 0, el plazo vale 0 y el programa habría decidido cualquier cosa.

Ninguna prueba del RTL lo podía ver, porque el testbench carga la tabla por su cuenta y el simulador sí respeta el `$readmemh`. Lo delató `icebram`, que no encontró el patrón del molde en ninguna BRAM, y lo habría delatado igual la simulación del bitstream (criterio 8). El módulo quedó solo con el `$readmemh`, como `pochoco_ram`, y el archivo trae las 256 líneas.

Es el argumento más concreto que tenemos de por qué el criterio 8 existe: lo que se simula tiene que ser lo que se graba.

## 3. Cambiar la tabla o el programa con `icebram`

### 3.1 El molde

`icebram` reemplaza el contenido de una memoria dentro de un `.asc` ya ruteado. Para ubicarla necesita saber qué había: busca el contenido anterior en las BRAM. Si el contenido anterior es la tabla definitiva, no puede: tiene 236 valores en cero y muchos bits iguales en todas las palabras, y `icebram` se niega con "Conflicting from pattern". Con el programa definitivo pasaría algo parecido en las zonas en cero.

La solución es la de siempre: se sintetiza un **molde**, el mismo diseño con las dos memorias llenas de un patrón al azar (`icebram -g`), y los cambios se hacen siempre desde el molde. `tools/fondo/bitstreams.sh` construye los dos, el molde y la síntesis directa con el contenido definitivo, y comprueba que el molde con `icebram` da **el mismo `.asc`, byte por byte**, que la síntesis directa, en R1 y en R2. El reemplazo de las dos memorias más `icepack` demora 0,26 s.

Por eso en `bitstreams/moldes/` quedan guardados los moldes de R1 y de R2 (el `.asc` comprimido) y los dos patrones. Sin ellos, cambiar algo obligaría a sintetizar de nuevo, y una síntesis nueva puede dar otra ubicación (le pasó a R0, decisión T62).

### 3.2 Cambio de tabla de punta a punta

Prueba hecha (`docs/mediciones/fondo/bitstreams.txt`, paso 4): una tabla con 9 valores distintos (otro umbral del gestor 3, otros pesos iniciales con sus topes y pisos, ventana de 256 ticks y plazo de 6 vueltas) puesta con `icebram` en el molde de R1.

- Cambian 2 líneas del `.asc` respecto de R1.
- El bitstream cambiado, simulado desde su `.asc` por los pines, decide igual que `ref/fondo.py` con esos parámetros en 2000 ticks de la serie de reversión. Con la tabla original la referencia da 53 bytes distintos en esa serie, así que la prueba distingue una tabla de la otra.
- **Tiempo de punta a punta: 0,32 s** (generar la tabla, `icebram` e `icepack`).

Comandos, desde la raíz, para una tabla nueva el día de la competencia (ejemplo con dos parámetros):

```bash
gunzip -c bitstreams/moldes/r1_molde.asc.gz > build/r1_molde.asc
python3 ref/fondo.py --param G3_ENTRA=-80 --param PLAZO=6 --tabla-hex build/tabla_nueva.hex
python3 tools/pochoasm.py sw/fondo.s -o build/fondo.hex        # y completarlo a 512 palabras, como hace tools/fondo/bitstreams.sh
icebram bitstreams/moldes/molde_prog.hex build/fondo_512.hex < build/r1_molde.asc \
  | icebram bitstreams/moldes/molde_tabla.hex build/tabla_nueva.hex > build/r1_nuevo.asc
icepack build/r1_nuevo.asc build/r1_nuevo.bin
```

Antes de grabar un bitstream así hay que simularlo desde su `.asc` contra `ref/fondo.py` con los mismos `--param`, que es lo que hace el paso 4 de `tools/fondo/bitstreams.sh`. Eso demora unos 40 minutos con Icarus para 2000 ticks. El paquete P8 arma con esto el kit de contingencia.

## 4. El vigilante

### 4.1 La regla

El módulo cuenta los precios recibidos (`byte_done` del esclavo SPI) desde la última escritura en `DECISION`. En un programa sano la cuenta va de 0 a 1 y vuelve a 0 en cada tick. Si llega a `VigN + 1 = 5`, es decir, cuatro precios quedaron sin respuesta y ya llegó un quinto, sube `BOOT` de la primitiva `SB_WARMBOOT` con `S1 S0 = 01` y la FPGA se reconfigura con la imagen 1.

Dispara solo por falla dura. No mira nada del algoritmo: ni precios, ni votos, ni el plazo del supervisor. Un gestor colgado no lo dispara, porque el supervisor sigue decidiendo (sección 10 de `docs/fondo.md`).

Propiedades que salen de contar precios y no tiempo:

- Con la maestra detenida no pasa nada. Sin precios no hay cuenta.
- Durante el reset del SoC no pasa nada.
- Funciona igual con cualquier período.
- El disparo espera a que `CS_n` esté en alto, para que la maestra nunca vea soltarse el pin MISO a mitad de un byte.
- `BOOT` no vuelve a bajar.
- La imagen de respaldo no tiene vigilante: no puede haber un ciclo de reinicios.

### 4.2 Por qué K = 4

El criterio es un K que no dispare en ninguna simulación sana, incluida la matriz de estrés. En todas las corridas sanas de R2 (sección 7) la cuenta máxima fue 1: el programa responde cada precio antes de que llegue el siguiente. Cualquier K de 2 o más cumple. Se dejó 4, el de la factibilidad, que da margen de sobra sin alargar mucho el relevo: a 0,1 ms el vigilante gasta 5 ticks de los 361 que dura el relevo completo con los 35,50 ms medidos en la placa (536 con los 53 ms de la hoja de datos).

### 4.3 Qué se tocó del esclavo SPI

`rtl/pochoco_spi_slave.v` tiene tres salidas nuevas (`byte_done_o`, `decision_wr_o` y `cs_active_o`) que sacan señales que ya existían. No cambia la lógica, el mapa de registros ni los nombres que el testbench oficial mira por jerarquía. `make formal-base` y el testbench oficial pasan igual en el core base.

### 4.4 Costo

16 celdas sobre R1 (1045 contra 1029). La frecuencia mínima baja de 51,59 a 47,86 MHz, lejos de los 25 MHz.

### 4.5 Pruebas del módulo

| Prueba | Resultado | Comando |
|--------|-----------|---------|
| Testbench del módulo, con N = 1, 2, 4, 7 y 15 | 90 comprobaciones. Programa sano, N precios sin respuesta (no dispara) y N + 1 (dispara), espera de `CS_n`, escritura en el mismo ciclo que un precio, maestra detenida, `BOOT` que no baja. 400 223 ciclos al azar por cada N contra un modelo | `make vig-tb` |
| Formal con SymbiYosys, N = 1, 4 y 7 | Cinco propiedades por inducción: `BOOT` solo sube con `CS_n` en alto, solo por la cuenta completa, no baja, exige N + 1 precios seguidos sin escritura, y el destino es constante. El disparo es alcanzable. 4 mutaciones con contraejemplo | `make vig-formal` |

## 5. El relevo, de punta a punta

`make vig-relevo` pone las dos imágenes en un mismo testbench (`tb/vigilante/tb_relevo.sv`): R2 con un programa en que el supervisor se cuelga en un tick elegido, y el Espino base con `sw/trade.hex`. Cuando `BOOT` sube, MISO queda en 1 durante el tiempo de reconfiguración y después la imagen 1 sale de su reset. El byte esperado en cada transacción lo calcula `tools/vigilante/relevo_ref.py`.

Qué lee la maestra, en orden:

1. Los bytes del fondo, hasta la falla.
2. El último byte escrito, repetido, mientras el vigilante cuenta: 5 transacciones.
3. `0xFF` durante la reconfiguración. Tiene la acción 11, que la maestra trata como mantener.
4. `0x00` (mantener) mientras la imagen 1 está en su reset de encendido.
5. Las decisiones de `max_media`, arrancada desde cero con los precios que alcanza a ver.

| Caso | `BOOT` sube al terminar la transacción | Ticks con `0xFF` | Ticks sin decisión nueva |
|------|-----------------------------------------|------------------|--------------------------|
| Falla en el tick 100, 0,1 ms | 105 | 530 | 536 |
| Falla en el tick 100, 1 ms | 104 | 53 | 58 |
| Falla en el tick 100, 10 ms | 104 | 5 | 10 |
| Falla en el tick 3, 0,1 ms | 8 | 530 | 536 |
| Falla en el tick 100, 0,1 ms, con los 35,50 ms medidos | 105 | 355 | 361 |
| Falla en el tick 100, 1 ms, medido | 104 | 35 | 40 |
| Falla en el tick 100, 10 ms, medido | 104 | 3 | 8 |

Las cuatro primeras filas usan los 53 ms típicos de la hoja de datos. El 16/11 se midió en la placa, por el eco de la UART, **35,50 ms** (una medición; `docs/mediciones/placa_16nov.md`), y las tres últimas filas son la misma simulación con ese tiempo (sección 2b de `docs/mediciones/vigilante/relevo.txt`). El testbench lo toma como parámetro. Todos los bytes coinciden con el esperado en las 130 simulaciones de `docs/mediciones/vigilante/relevo.txt`, y en todas `BOOT` sube con `CS_n` en alto y sin transacción en curso, 80 ns después de que `CS_n` sube.

Tres cosas que conviene saber para la defensa:

- **El relevo cuesta posición.** `max_media` parte sin posición y su primera decisión suele ser vender. Si el fondo estaba comprado, la imagen de respaldo liquida.
- **Una transacción puede quedar cortada** por el fin de la reconfiguración. Se barrió ese instante en 40 corridas: la maestra lee `80`, `c0`, `e0`, `f0`, `f8`, `fc` o `fe`, y ninguno es una orden (acción 11, o vender 0). Eso vale si el pin flotante (en alta impedancia) se lee como 1 y la imagen 1 mantiene MISO en 0 durante su reset.
- **Qué no demuestra la simulación**: cuánto dura realmente la reconfiguración (se midió en la placa el 16/11: 35,50 ms), qué nivel tiene el pin mientras tanto, y que `SB_WARMBOOT` cargue la imagen correcta. El modelo de simulación de esa primitiva está vacío: aquí se comprueba que `BOOT` suba cuando debe y con `S1 S0 = 01`. Lo demás es de la puerta de placa.

## 6. Bitstreams e imagen múltiple

`docs/mediciones/fondo/bitstreams.txt`. Los cuatro `.asc` (R1, R2 y sus moldes) salen de yosys y nextpnr con la semilla 1.

| Archivo en `bitstreams/` | Qué es | Celdas | Frecuencia con la semilla 1 |
|--------------------------|--------|--------|-----------------------------|
| `r1_fondo.bin` | R1 con `sw/fondo.s` y la tabla | 1029 | 52,44 MHz |
| `r2_fondo_vigilante.bin` | R2, una sola imagen | 1045 | 52,53 MHz |
| `r2_multi.bin` | Imagen múltiple: R2 en la imagen 0 y R0 en la imagen 1 | | |
| `moldes/` | Moldes de R1 y R2 y sus patrones, para `icebram` | | |

Lo que se comprobó sobre los bitstreams, no sobre el RTL:

- **Criterio 8.** R1 y R2 simulados desde su `.asc` por los pines, con la maestra de `tb/tb_bitstream.sv` sin modificar: 2000 ticks idénticos a `ref/fondo.py` con la serie de práctica y con una de reversión. En R2, `SB_WARMBOOT` no se dispara en ninguna de las dos.
- **El vigilante dentro del bitstream.** Con el programa del supervisor colgado en el tick 100 puesto con `icebram` en el molde de R2, `BOOT` sube con `S1 S0 = 01` y `CS_n` en alto al terminar la transacción 105, la quinta sin respuesta. Es el mismo instante que en el RTL (sección 5).
- **La imagen múltiple.** `icemulti -p0` con R2 y `bitstreams/r0_base_max_media.bin`. `tools/ver_multi.py` decodifica los cinco vectores de arranque: el de encendido y los de `S1 S0` = 00, 10 y 11 apuntan a R2, y el de 01 apunta a R0. Las dos imágenes están copiadas sin un bit de diferencia (R0 conserva su sha256). Ocupa 64 600 bytes de los 131 072 de la flash de la Go Board.

Para grabar (lo hace Nicolás, con la Go Board conectada; el detalle está en `docs/autoprueba.md`, sección 9): `iceprog bitstreams/r1_fondo.bin` para R1, o `iceprog -b bitstreams/r2_multi.bin` para R2 con su respaldo. El `-b` borra la flash entera antes de escribir: el archivo de dos imágenes ocupa más de 32 kB y, si la flash de la placa borra en sectores de 32 kB, el borrado por bloques de `iceprog` dejaría la segunda mitad sin borrar (lo advirtió la factibilidad del warm boot).

## 7. La puerta de simulación de R1 y R2

Detalle en `docs/puertas.md`. Las dos columnas se corrieron por separado, cada una con su hardware.

| N.º | Criterio | R1 | R2 |
|-----|----------|----|----|
| 1 | Testbench oficial sin modificar | 4/4, peor caso 443 ciclos de 2262, `decisiones.csv` idéntico al de `ref/fondo.py` | Igual |
| 2 | Equivalencia con la referencia | Cero diferencias: práctica completa a 0,1 ms, 1 ms y 10 ms (4/4 en las tres), una serie de 20 000 ticks de cada una de las 15 familias y 1 050 series sintéticas (2,1 millones de ticks) | Igual |
| 3 | Timing en 10 semillas | 10 de 10. 1029 celdas, 13 BRAM, mínima 51,59 MHz, mediana 52,57 | 10 de 10. 1045 celdas, 13 BRAM, mínima 47,86 MHz, mediana 50,33 |
| 4 | Peor caso barriendo la fase | 444 ciclos sano y 568 con el plazo agotado, contra 1131 | Igual |
| 5 | Core en la configuración exacta | 7 974 963 instrucciones en 20 600 programas, 92,80 % distintas, cero diferencias con el Espino base más la especificación. 6 de 6 mutaciones de la extensión que aplican, 21 de 21 del barrel, y prueba formal de que las 3 de `mulstep` no cambian el core | Igual |
| 6 | Degradación | 30 de 30 corridas, peor caso 679 ciclos. 15 de 15 controles negativos | Igual |
| 7 | Estrés | 56 de 56 casos | 56 de 56, sin disparo del vigilante |
| 8 | Bitstream simulado desde el `.asc` | 2000 ticks idénticos en dos series | 2000 ticks idénticos en dos series, sin disparo |

**El vigilante en las corridas sanas de R2.** En las 1 201 corridas sanas del lote de series, del barrido de fases y de la degradación (que tiene gestores colgados, pero el supervisor sano), en la equivalencia de 20 000 ticks a los tres períodos y en los 56 casos de la matriz de estrés, `BOOT` no subió nunca y la cuenta del vigilante nunca pasó de 1. El disparo necesita 5.

Fuera de la puerta, en dos casos de exploración con períodos de 11,5 y 13,5 µs (ocho veces más rápido que la ronda 3, donde el fondo ya no alcanza a responder cada precio), la cuenta llegó a 2. Tampoco disparó.

**Criterio 5.** La campaña de P2 había corrido con las tres instrucciones. Se repitió con la máscara de `emad` y `devk` y con la tabla (R1) y la tabla y el vigilante (R2) puestos en los dos SoC de la comparación. Las palabras de `mulstep` que genera el banco de pruebas aparecen ahora como custom-0 sin efecto: 268 689 en la campaña de lazos, todas tratadas como ilegales, que es lo que este hardware tiene que hacer.

## 8. Límites y lo que falta

- **La puerta de placa está incompleta.** El 16/11 R2 pasó la firma a 0,1 ms y la media hora sin disparo, y el relevo se midió en 35,50 ms por la UART; faltan la firma de R2 a 1 ms y 10 ms, ver la imagen testigo después del relevo y las tres firmas de R1 (`docs/mediciones/placa_16nov.md`). La maestra real se prueba el miércoles 25/11, por confirmar.
- **El tiempo de reconfiguración tiene una sola medición (35,50 ms) y el nivel de MISO durante el relevo no está medido.** De eso depende cuántos ticks se pierden y si la maestra realmente lee mantener.
- **Reconfigurar durante una ronda está cubierto por la respuesta general del profesor** (16/11: cualquier decisión de diseño es válida), sin confirmación específica (T126). Si el ayudante lo prohibiera de forma explícita, R2 no compite y el titular es R1.
- **El vigilante no cubre un programa que escribe basura.** Solo ve que se escribió `DECISION`, no qué se escribió. Es lo que pide la especificación: disparar por falla dura y nunca por una condición del algoritmo.
- **SCLK de 100 kHz con período de 0,1 ms.** Esa combinación deja 237 ciclos entre transacciones y el fondo necesita hasta 444 para responder. En la simulación los bytes coinciden aun así, porque el esclavo toma el byte al empezar la transacción siguiente, pero el caso queda fuera de la puerta. R0 sí cabe ahí (49 ciclos). A 1 ms el fondo funciona con SCLK de 100 kHz.
- **Cambiar la tabla exige simular el bitstream nuevo**, unos 40 minutos. No es un cambio de último minuto.
- **Esta puerta corrió por el RTL con Verilator y por el `.asc` con Icarus**: el gemelo digital todavía no modelaba el barrel. Desde P4 lo modela, con la tabla (`--tabla`), aunque no el vigilante.

## 9. Cómo reproducir

| Comando | Qué hace | Salida | Demora |
|---------|----------|--------|--------|
| `make fondo-puerta HW=r1` (o `HW=r2`) | Criterios 1, 2, 3, 4, 6 y 7 del peldaño | `docs/mediciones/fondo/r1/` | 50 min |
| `make fondo-bitstreams` | Criterio 8 de los dos peldaños, `icebram`, vigilante dentro del bitstream e imagen múltiple | `docs/mediciones/fondo/bitstreams.txt` | 50 min |
| `make fondo-criterio5 HW=r1` (o `HW=r2`) | Criterio 5 con la máscara de `emad` y `devk` sobre el SoC del peldaño | `docs/mediciones/fondo/r1/criterio5_*.txt` | 40 min |
| `make check-vigilante` | Testbench, formal y relevo del vigilante | `docs/mediciones/vigilante/` | 3 min |
| `make check-fondo HW=r1` (o `HW=r2`) | Versiones cortas. Corre en la integración continua | `build/fondo/r1/` | 10 min |
| `GUARDAR=1 tools/fondo/bitstreams.sh` | Lo de `make fondo-bitstreams`, y copia los resultados a `bitstreams/` | `bitstreams/` | 50 min |

## 10. Preguntas para estudiar

1. **¿La tabla decide algo?** No. Es una memoria de solo lectura. El que lee, compara y decide es el programa en el core.
2. **¿Por qué una BRAM aparte y no la memoria de datos?** Porque así se cambia con `icebram` sin tocar el programa, y porque el programa no puede escribirla ni por error.
3. **¿Qué habría pasado si no se hubiera simulado el bitstream?** La tabla habría salido en cero y el diseño habría fallado en la placa habiendo pasado todas las pruebas del RTL. Sección 2.4.
4. **¿Por qué no se puede cambiar la tabla directamente en el bitstream final?** Porque `icebram` ubica la memoria por su contenido y la tabla definitiva no es distinguible. Sección 3.1.
5. **¿Cuándo dispara el vigilante?** Al quinto precio seguido sin escritura en `DECISION`, y espera a que `CS_n` suba.
6. **¿Puede disparar con el programa sano?** En ninguna corrida sana la cuenta pasó de 1, y el disparo necesita 5. Sección 7.
7. **¿Qué pierde el fondo si dispara?** 361 ticks sin decisión nueva a 0,1 ms con los 35,50 ms medidos en la placa (536 con los 53 ms de la hoja de datos), y probablemente la posición. Sección 5.
8. **¿Qué pasa si se cuelga un gestor y no el supervisor?** Nada que vea el vigilante: el supervisor decide sin ese voto. `docs/fondo.md`, sección 10.
9. **¿Por qué la imagen de respaldo no tiene vigilante?** Para que no exista un ciclo de reinicios, y porque es R0, que ya pasó su puerta tal como está.
