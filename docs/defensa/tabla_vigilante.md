# Tabla de parámetros, `icebram`, vigilante, warm boot e imagen múltiple

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio para la defensa. Resume y ordena `docs/tabla_vigilante.md` (la fuente completa) y la parte de moldes de `docs/contingencia.md`. Es el hardware que separa R0, R1 y R2. Cifras de `docs/mediciones/fondo/bitstreams.txt`, `docs/mediciones/vigilante/` y `docs/puertas.md`.

## 1. Qué problema resuelve cada pieza

| Pieza | Problema | Peldaño |
|-------|----------|---------|
| Tabla de parámetros en BRAM | Cambiar umbrales, pesos o plazo el día de la competencia **sin volver a sintetizar**, porque una síntesis nueva ya no es el hardware probado con la maestra | R1 y R2 |
| `icebram` con moldes | Reemplazar el contenido de una BRAM dentro de un bitstream ya ruteado | R0, R1 y R2 |
| Vigilante con `SB_WARMBOOT` | Que una falla dura del programa (el supervisor deja de escribir `DECISION`) no deje al grupo sin operar el resto de la ronda | R2 |
| Imagen múltiple | Tener en la flash el diseño que compite y un respaldo que la FPGA pueda cargar sola | R2 |

| Peldaño | Hardware | Celdas | BRAM | Fmax mín. (10 semillas) |
|---------|----------|--------|------|-------------------------|
| R0 | Espino base | 1083 | 12 | 42,43 MHz |
| R1 | Barrel, `emad`, `devk` y tabla | 1029 | 13 | 51,59 MHz |
| R2 | R1 más vigilante y `SB_WARMBOOT` | 1045 | 13 | 47,86 MHz |

Fuente: `docs/puertas.md`, criterio 3 de cada peldaño.

## 2. La tabla de parámetros

**Qué es.** Una BRAM de 256 valores de 16 bits en `0x8002_0000`, de **solo lectura**. Es memoria y nada más: no calcula, no mira precios y no decide. Guarda las 20 constantes de `sw/fondo.s` (umbrales de las cuatro reglas, pesos iniciales, topes, pisos, ventana, umbral del voto y plazo).

| Qué | Dónde |
|-----|-------|
| El módulo: solo `$readmemh`, lectura registrada, sin puerto de escritura | `rtl/pochoco_tabla.v:39` a `:45` |
| Extensión de signo de 16 a 32 bits: un umbral negativo se guarda tal cual | `rtl/pochoco_tabla.v:47` |
| Instancia en el SoC con `-DESPINO_TABLA` | `rtl/pochoco_soc.v:205` |
| El programa carga la base en `x1` una vez por tick | `sw/fondo.s:201` |
| Desplazamientos de cada constante, en el orden de `PARAMETROS` de la referencia | `sw/fondo.s:118` a `:134`, `ref/fondo.py:71` |

Contenido: `sw/fondo_tabla.hex`, que genera `python3 ref/fondo.py --tabla-hex`; `make check-tabla` comprueba que el archivo guardado sea el de la referencia.

**Por qué una BRAM aparte y no la memoria de datos.** Así se cambia con `icebram` sin tocar el programa, y el programa no puede escribirla ni por error (decisión T69). Costo: 39 celdas y 1 BRAM, y una instrucción más por tick en el supervisor.

**El error que la simulación del RTL no veía.** La primera versión llenaba la memoria con ceros en un lazo y después hacía `$readmemh`. En simulación funcionaba. En síntesis Yosys se quedó con los ceros y descartó el archivo: **la BRAM salía vacía en el bitstream**, con todos los umbrales y el plazo en cero. Lo delató `icebram` (no encontró el patrón del molde) y lo habría delatado la simulación del bitstream (criterio 8). Es el argumento más concreto de por qué se simula lo que se graba y no solo el RTL (`docs/tabla_vigilante.md`, sección 2.4). El comentario de `rtl/pochoco_tabla.v:36` a `:38` lo deja escrito.

## 3. Cambiar la tabla o el programa con `icebram`

`icebram` reemplaza el contenido de una BRAM dentro de un `.asc` ya ruteado. Para ubicarla busca el contenido anterior. Con la tabla de verdad (236 valores en cero) no puede distinguirla y se niega. La solución es un **molde**: el mismo diseño sintetizado con las memorias llenas de un patrón al azar (`icebram -g`). Los cambios se hacen siempre desde el molde (decisión T70).

- `tools/fondo/bitstreams.sh` construye el molde y la síntesis directa, y comprueba que el molde con `icebram` da **el mismo `.asc` byte por byte** que la síntesis directa, en R1 y en R2.
- Los moldes quedan guardados en `bitstreams/moldes/` (`r0_molde.asc.gz`, `r1_molde.asc.gz`, `r2_molde.asc.gz` y los patrones).
- El molde de R0 se construye desde el commit de R0 (decisión T121): una síntesis desde otro commit da otra ubicación (T62).

| Medido | Valor | Fuente |
|--------|-------|--------|
| Cambio de tabla de punta a punta (generar, `icebram`, `icepack`) | 0,32 s | `docs/tabla_vigilante.md`, sección 3.2 |
| `icebram` con `sw/trade.hex` sobre el molde de R0, igual a R0 byte por byte | 0,10 s | `docs/mediciones/p8/r0_molde.txt` |
| Simular el bitstream nuevo desde su `.asc` antes de grabarlo | unos 40 minutos | `docs/tabla_vigilante.md`, sección 3.2 |

Un bitstream cambiado con `icebram` **no hereda la puerta**: hay que simularlo desde su `.asc`. Por eso los juegos de contingencia para comisión de 20 y 50 ya están construidos y simulados (`docs/contingencia.md`, sección 4.3).

## 4. El vigilante

**La regla.** Cuenta los precios recibidos (`byte_done` del esclavo SPI) desde la última escritura en `DECISION`. En un programa sano la cuenta va de 0 a 1 y vuelve a 0 en cada tick. Si llega a 5 (cuatro precios sin respuesta y llegó un quinto), sube `BOOT` de `SB_WARMBOOT` con `S1 S0 = 01` y la FPGA se reconfigura con la imagen 1.

| Qué | Dónde |
|-----|-------|
| `lleno` cuando la cuenta llega a N + 1 | `rtl/vigilante.v:65` |
| La cuenta: sube con cada precio, vuelve a 0 con cada escritura en `DECISION` | `rtl/vigilante.v:67` a `:79` |
| `BOOT` sube solo con `CS_n` en alto, y no vuelve a bajar | `rtl/vigilante.v:81` |
| Instancia con `VigN = 4` y la primitiva `SB_WARMBOOT` | `rtl/pochoco_soc.v:285` y `:295` |
| Tres salidas nuevas del esclavo SPI (sin cambiar su lógica) | `rtl/pochoco_spi_slave.v:32` a `:34` |
| Propiedades formales dentro del módulo | `rtl/vigilante.v:136` a `:142` |

**Dispara solo por falla dura.** No mira precios, votos ni el plazo del supervisor. Un gestor colgado no lo dispara, porque el supervisor sigue decidiendo. Por contar precios y no tiempo: con la maestra detenida no pasa nada, durante el reset no pasa nada y funciona igual con cualquier período.

**Por qué K = 4 (dispara al quinto).** El plan pide un K que no dispare en ninguna simulación sana. En todas las corridas sanas de R2, incluida la matriz de estrés, **la cuenta nunca pasó de 1**. Cualquier K de 2 o más cumple; 4 da margen y gasta solo 5 ticks de los 536 del relevo (decisión T71).

**Por qué espera `CS_n` en alto.** Para que la maestra nunca vea soltarse MISO a mitad de un byte.

**Por qué la imagen de respaldo no tiene vigilante.** Es R0 tal cual, el mismo archivo que pasó su puerta (decisión T72). Sin vigilante no puede haber un ciclo de reinicios.

## 5. El relevo de punta a punta

`make vig-relevo` pone las dos imágenes en un mismo testbench: R2 con el supervisor colgado a propósito y R0 con `sw/trade.hex` (`docs/mediciones/vigilante/relevo.txt`). Lo que lee la maestra, en orden:

1. Los bytes del fondo hasta la falla.
2. El último byte, repetido 5 transacciones mientras el vigilante cuenta.
3. `0xFF` durante la reconfiguración: acción 11, que la maestra trata como mantener.
4. `0x00` (mantener) mientras R0 está en su reset de encendido.
5. Las decisiones de `max_media`, partiendo desde cero.

| Período | Ticks sin decisión nueva |
|---------|--------------------------|
| 0,1 ms | 361 (355 con `0xFF`) |
| 1 ms | 40 |
| 10 ms | 8 |

Con los **35,50 ms de reconfiguración medidos en la placa** el 16/11 por el eco de la UART (una medición). Con los 53 ms de la hoja de datos eran 536, 58 y 10. Todas las simulaciones del relevo dan los bytes esperados.

Lo que hay que saber decir:

- **El relevo cuesta posición.** `max_media` parte sin media y sin posición, y su primera decisión suele ser vender: si el fondo estaba adentro, R0 liquida.
- **Lo que la simulación no demuestra:** cuánto dura de verdad la reconfiguración, qué nivel tiene MISO mientras tanto, y que `SB_WARMBOOT` cargue la imagen correcta (su modelo de simulación está vacío). Eso es de la puerta de placa: el relevo tiene que ocurrir al inyectar la falla y no ocurrir en media hora de funcionamiento normal.
- **Reconfigurar durante una ronda está cubierto por la respuesta general del profesor** del 16/11, sin confirmación específica (T126). Solo si el ayudante lo prohíbe de forma explícita, R2 no compite y compite R1 (`docs/arbol_decision.md`, regla 5).

## 6. La imagen múltiple

`bitstreams/r2_multi.bin` es `icemulti -p0` con R2 en la imagen 0 y `bitstreams/r0_base_max_media.bin` en la imagen 1, copiado sin cambios. `tools/ver_multi.py` decodifica los vectores de arranque: el de encendido y los de `S1 S0` = 00, 10 y 11 apuntan a R2, y el de 01 a R0. R0 conserva su sha256 dentro del archivo. Ocupa 64 600 bytes de los 131 072 de la flash (`docs/tabla_vigilante.md`, sección 6).

## 7. Preguntas típicas

1. **¿La tabla decide algo?** No. Es memoria de solo lectura (`rtl/pochoco_tabla.v:43` a `:45`). El que lee, compara y decide es el programa en el core.
2. **¿Por qué una BRAM aparte?** Para cambiarla con `icebram` sin tocar el programa, y para que el programa no pueda escribirla (T69).
3. **¿Qué habría pasado si no se simulaba el bitstream?** La tabla habría salido en cero y el diseño habría fallado en la placa después de pasar todas las pruebas del RTL (`rtl/pochoco_tabla.v:36`).
4. **¿Por qué no se cambia la tabla directamente en el bitstream final?** Porque `icebram` ubica la memoria por su contenido y la tabla de verdad no es distinguible. Por eso los moldes (T70).
5. **¿Cuándo dispara el vigilante?** Al quinto precio seguido sin escritura en `DECISION`, y espera a que `CS_n` suba (`rtl/vigilante.v:65` y `:81`).
6. **¿Puede disparar con el programa sano?** En ninguna corrida sana la cuenta pasó de 1; el disparo necesita 5 (`docs/puertas.md`, lo propio de R2).
7. **¿Qué pasa si se cuelga un gestor y no el supervisor?** Nada que vea el vigilante: el supervisor decide sin ese voto.
8. **¿Qué pierde el fondo si dispara?** 361 ticks sin decisión nueva a 0,1 ms con el tiempo medido en la placa (536 con el de la hoja de datos), y probablemente la posición.
9. **¿Por qué la imagen de respaldo no tiene vigilante?** Para que no exista un ciclo de reinicios, y porque es R0, que ya pasó su puerta tal como está (T72).
10. **¿Cuánto demora cambiar un parámetro el día de la competencia?** 0,32 s en armar el bitstream, más unos 40 minutos de simulación desde el `.asc`. Para comisión de 20 y 50 los juegos ya están hechos.
