# Checklist del miércoles 25/11, por confirmar: pruebas con la maestra real

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

La maestra existe un solo día. Este es el orden de las pruebas, qué se mide en cada una y qué hacer si algo falla. Lo que se anota va en la plantilla de la sección 7, que después se pasa a `docs/mediciones/maestra_26nov.md`. Con eso se decide el peldaño que compite (`docs/arbol_decision.md`).

Puerta de maestra (`docs/puertas.md` y decisión T50): cada peldaño tiene que correr las tres rondas sin perder precios ni decisiones, y su patrimonio tiene que coincidir con el que predice el gemelo si la serie es conocida. Si la serie no es conocida, R0 y R1 tienen que comportarse de forma coherente entre sí.

Desde el 19/11 los tres peldaños corren la regla de cotas con **banda 40** (decisión T140): compra con 140 o menos y vende con 215 o más, después de haber visto 100 y 255. Los bitstreams son los `*_banda40*.bin`. Los de banda 60 (`r0_cotas.bin`, `r1_cotas.bin`, `r2_cotas.bin`, `r2_cotas_multi.bin`), que corrieron con la maestra el 18/11, quedan en `bitstreams/` como anteriores y no se llevan como peldaños; tienen el mismo hardware, así que lo que se vio el 18/11 con `r2_cotas_multi.bin` vale para el hardware de los nuevos.

## 1. Antes de salir (la noche anterior)

1. `git checkout v-maestra-25nov` (la etiqueta del congelamiento del hardware y del algoritmo, T156) y `make check` en verde.
2. `cd bitstreams && sha256sum -c SHA256SUMS && cd ..`: todas las líneas en `OK`. Se llevan, en este orden de uso:

   | Archivo | Para qué | sha256 (primeros 16) |
   |---------|----------|----------------------|
   | `medidor_spi.bin` | Medir el SPI real de la maestra (sección 3) | `09bc30b5208b1abc` |
   | `r0_banda40.bin` | R0 | `390edbfad65b2e26` |
   | `r1_banda40.bin` | R1 | `a9e233b96fba7643` |
   | `r2_banda40_multi.bin` | R2 con R0 de respaldo (imagen múltiple: imagen 0 `r2_banda40.bin`, imagen 1 `r0_banda40.bin`) | `8a773121e44a4d6f` |
   | `r2_banda40_falla_multi.bin` | R2 con el supervisor colgado y R0 de respaldo: el relevo con la maestra real (sección 5) | `88d63a08082f51d2` |
   | `autoprueba_r0.bin`, `autoprueba_r1.bin`, `autoprueba_r2_multi.bin` | Si algo falla, separar placa de maestra (`docs/autoprueba.md`, sección 11). Firma esperada `a639` en los tres; con el programa de banda 60 sería `8610`. Deberían haberse probado antes del 26 | `b0a4ebcc4c30ed76`, `7478606482a119d6`, `bd5b7278a3a3eb0c` |
   | `relevo_r2_multi.bin` y `relevo_r2_multi_sin_dormir.bin` | Tiempo del relevo en la placa, sin maestra (`docs/autoprueba.md`, sección 10) | `bafb50392f8b2f83`, `91a94e4efad287dd` |
   | `registrador.bin` | Registrar la serie de la maestra en cada ronda (sección 4b) | `231a0c6d2a69a78d` |

   Las imágenes múltiples (`*_multi.bin`) se graban con `iceprog -b`.

3. Notebook con WSL, `usbipd` y OSS CAD Suite (`iceprog --help` responde). Cable USB de la Go Board, 4 cables hembra-hembra para el PMOD más uno de tierra, y el teléfono con cámara lenta (para el relevo).
4. Las preguntas para el ayudante impresas (sección 6).

## 2. Conexión

La Go Board se conecta a la maestra por el PMOD (pines del `goboard.pcf` del curso):

| Señal | Pin de la FPGA | PMOD de la Go Board |
|-------|-------------|---------------------|
| `CS_n` | 65 | 1 |
| `MOSI` | 64 | 2 |
| `MISO` | 63 | 3 |
| `SCLK` | 62 | 4 |
| Tierra | | 5 u 11 |

Verificar los números del PMOD con el ayudante antes de conectar. **La tierra se conecta primero.** No se conecta 3,3 V entre placas: cada una se alimenta por su USB.

**Con los cables puestos y la maestra encendida, desconectar y conectar el USB de la Go Board antes de la primera ronda de cada peldaño.** Los pines del SPI no tienen pull-up: con los cables desconectados pueden captar ruido y el SoC recibiría precios falsos que quedan en su media. Al reconectar, la FPGA se configura de nuevo desde la flash y parte de cero con la maestra ya fijando el nivel de las líneas (`docs/mediciones/placa_16nov.md`). Sin maestra, `r1_banda40.bin` debe mostrar "00" con los cuatro LED apagados.

## 3. Medir el SPI real con el medidor (primera prueba, unos 10 minutos)

Es lo primero porque decide entre R0 y R1 (regla 3 del árbol). `medidor_spi.bin` no tiene el SoC: escucha la maestra, responde siempre `0x00` (mantener) y muestra lo que mide en los 7 segmentos (`rtl/medidor/medidor_spi.v`).

1. `iceprog bitstreams/medidor_spi.bin`. Al terminar ("VERIFY OK"): LED1 a LED4 apagados, 7 segmentos en `FF`.
2. Pedir a la maestra la ronda 1 (10 ms). Al terminar, sin apretar SW3, leer las medidas apretando SW1 para avanzar. Los LED1 a LED3 dicen el número de la medida en binario (LED1 es el bit 0). Para cada medida anotar el byte bajo (sin SW4) y el alto (con SW4 apretado):

   | Medida | Qué es | Testbench del curso | Cómo se lee |
   |--------|--------|---------------------|-------------|
   | 0 | Período mínimo de SCLK, en ciclos de 40 ns | `0x0019` (25) | SCLK en kHz = 25 000 / valor |
   | 1 | Período máximo de SCLK | `0x0019` | Si es muy distinto de la medida 0, el SCLK no es estable |
   | 2 | Período entre precios, último, en unidades de 0,64 µs | `0x3D09` en la ronda 1, `0x061A` en la 2, `0x009C` en la 3 | T en µs = valor x 0,64 |
   | 3 | Período mínimo entre precios | Igual | |
   | 4 | Duración de `CS_n` en bajo, en ciclos | `0x00ED` (9,5 µs) | |
   | 5 | De la bajada de `CS_n` al primer flanco de SCLK, en ciclos | `0x0025` (1,5 µs) | |
   | 6 | Tiempo libre mínimo entre transacciones, en ciclos | `0xFFFF` en las rondas 1 y 2, `0x08D6` (2262) en la 3 | Es el presupuesto de la respuesta. Con la regla de cotas R1 necesita 128 y R0 60 (con el fondo que votaba eran 444 y 44) |
   | 7 | Transacciones contadas | Las de la ronda | Número de precios por ronda (pregunta 1 al ayudante) |

   LED4 encendido significa que alguna transacción no tuvo 8 flancos de SCLK, que hubo flancos de SCLK con `CS_n` en alto (bus compartido con otro esclavo), o que SCLK estaba en alto al bajar `CS_n` (maestra de modo 2 o 3). Anotarlo: en el primer caso el esclavo del SoC perdería ese precio; en el segundo puede tomar cada flanco como un precio si su contador de bits quedó en 7, lo que en R2 dispara el vigilante (`docs/revision_p10.md`, hallazgo 1); en el tercero la maestra lee la decisión corrida un bit y "vender 63" llega como "comprar 62" (observación 4), y ningún peldaño debe competir sin hablarlo con el ayudante. Para saber cuál de los dos casos es, mirar el PMOD con el osciloscopio o el analizador lógico.
3. Apretar SW3 (borra), pedir la ronda 2 y repetir. Lo mismo con la ronda 3.
4. **Decisión inmediata.** Si en la ronda 3 la medida 0 es mayor que 217 (`0x00D9`, es decir, SCLK menor que 115 kHz), o la medida 6 es menor que 600, R1 no tiene margen: se prueba igual, pero el titular es R0 (árbol, reglas 3 y 4). Estos límites se fijaron con el fondo que votaba (444 ciclos); con la regla de cotas R1 responde en 128 y pasa la matriz de estrés con SCLK de 100 kHz a 0,1 ms. Se mantienen mientras Nicolás no decida otra cosa (`docs/pendientes_nicolas.md`).

Si no se puede usar el medidor (por ejemplo, la maestra solo corre con un grupo a la vez y no hay tiempo), lo mismo se mide con un osciloscopio o un analizador lógico en el PMOD: período de SCLK, duración de `CS_n` y período entre bajadas de `CS_n`, en las tres rondas.

## 4. Peldaños con la maestra, del más seguro al más alto

Para cada peldaño, las tres rondas. Antes de cada peldaño se anota el sha256 que imprime `sha256sum` del archivo que se va a grabar.

1. **R0.** `iceprog bitstreams/r0_banda40.bin`. Rondas 1, 2 y 3. Anotar el patrimonio final que muestra la maestra en cada ronda y si en algún tick nuestro grupo quedó sin operar cuando los demás operaban. R0 no tiene telemetría.
2. **R1.** `iceprog bitstreams/r1_banda40.bin`. Lo mismo. Mirar además la telemetría (un store por tick, `sw/fondo.s`): LED1 es el latido (cambia cada 1024 precios), LED2 se enciende al ver el 100, LED3 al ver el 255, LED4 mientras la posición es comprar 63; los 7 segmentos muestran "63" mientras está adentro y "00" afuera.
3. **R2.** `iceprog -b bitstreams/r2_banda40_multi.bin` (con `-b`: la imagen múltiple ocupa más de 32 kB y hay que borrar la flash entera; el 18/11 sin `-b` la verificación falló, `docs/clase_18nov.md`). Lo mismo. En funcionamiento normal **no debe cambiar a R0**: si la telemetría de R1 desaparece a mitad de una ronda (R0 no tiene telemetría), el vigilante se disparó; anotar en qué ronda y en qué momento.

Si la serie de la maestra es conocida (por ejemplo, la de práctica), el patrimonio de cada ronda se compara con el del gemelo:

```
make fondo-hex
build/gemelo --hex sw/trade.hex --serie SERIE.csv --periodo-ns 100000 --nticks N           # R0
build/gemelo --barrel --xd 3 --tabla sw/fondo_tabla.hex --hex build/fondo/fondo.hex \
             --serie SERIE.csv --periodo-ns 100000 --nticks N                               # R1 y R2
```

con el período de cada ronda (10 000 000, 1 000 000 y 100 000 ns) y el SCLK medido (`--sclk-medio-ns`, la mitad del período de SCLK en ns). Si la maestra parte con la placa ya encendida, los precios perdidos en el reset son 0: usar `--inicio-ns 200000`.

Si la serie no es conocida: con la regla de cotas R0, R1 y R2 escriben los mismos bytes en cualquier serie y a cualquier período (las puertas lo comprueban: `ref/fondo.py` decide igual que `ref/trader.py`), así que **en la misma ronda los tres tienen que mostrar exactamente el mismo patrimonio**. En la serie de práctica Meta dan 21 392; en las rondas del 18/11, Tesla 20 795 y AMD 26 470 (con banda 60 la maestra mostró 18 779 y 21 895, lo mismo que la referencia). Una diferencia entre peldaños en la misma ronda se anota y se revisa con el gemelo esa noche.

## 4b. Registrar la serie de la maestra (registrador, unos 10 minutos por ronda)

Para la puerta de maestra hace falta la serie que mandó la maestra: con ella el gemelo predice el patrimonio de cada peldaño y se compara con la pantalla. `bitstreams/registrador.bin` escucha el SPI, responde siempre mantener y manda cada precio por la UART (`docs/registrador.md`). No guarda nada en la placa.

1. `iceprog bitstreams/registrador.bin`. Al terminar: `00` en los 7 segmentos y los LED apagados.
2. Con los cables del PMOD puestos, desconectar y conectar el USB; repetir `usbipd attach` si hace falta. `ls /dev/ttyUSB*`: el segundo puerto (normalmente `/dev/ttyUSB1`) es la UART.
3. Antes de que la maestra empiece: `python3 tools/registrador.py /dev/ttyUSB1 -o build/maestra/ronda3`. Pedir la ronda 3.
4. Al terminar la ronda, Ctrl+C. Anotar lo que imprime: registros, **perdidos (tiene que ser 0)**, transacciones con error, período mínimo y máximo. Comprobar que los 7 segmentos muestran la cuenta que dice el programa (con SW4, el byte alto). LED4 encendido significa que se perdió algún registro.
5. SW3 (borra la cuenta y la secuencia) y repetir con las rondas 2 y 1 (`-o build/maestra/ronda2`, `ronda1`).
6. Esa noche, con cada serie: `build/gemelo --hex sw/trade.hex --serie build/maestra/ronda3_serie.csv --periodo-ns 100000 --inicio-ns 200000` para R0, y con `--barrel --xd 3 --tabla sw/fondo_tabla.hex --hex build/fondo/fondo.hex` para R1 y R2. El patrimonio tiene que ser el que mostró la maestra en la sección 4.

Si dice "Permission denied", falta el grupo `dialout`. Si el puerto no acepta 1 Mbaud, ver `docs/registrador.md`, sección 5. Las series quedan en el computador: no se usan para elegir algoritmos mientras el ayudante no confirme que no son las de la competencia (`docs/pendientes_nicolas.md`).

## 5. Relevo de R2 con la falla inyectada

`bitstreams/r2_banda40_falla_multi.bin` es R2 con el supervisor colgado a propósito en el tick 100 y R0 de banda 40 de respaldo: a los 100 precios deja de escribir `DECISION`, el vigilante dispara al quinto precio sin respuesta y la placa pasa a R0. Su `.asc` es el mismo que la puerta de simulación de R2 probó por los pines (`make r2-falla-banda40`, paso 3 de `make fondo-molde-banda40`).

1. `iceprog -b bitstreams/r2_banda40_falla_multi.bin` y correr la ronda 3.
2. Anotar cuántos ticks quedó nuestro grupo sin decisión nueva según la maestra, y filmar la placa en cámara lenta. La predicción, con los 35,50 ms medidos en la placa el 16/11 (`docs/mediciones/placa_16nov.md`), es de 361 ticks a 0,1 ms (5 sin respuesta que esperan al vigilante y 356 de reconfiguración y reset), 40 a 1 ms y 8 a 10 ms. Con los 53 ms de la hoja de datos eran 536, 58 y 10. Si se repite la medición, `python3 tools/medir_relevo.py --traducir MS` da la predicción con el nuevo tiempo.
3. Anotar qué hace la maestra mientras la FPGA se reconfigura (MISO queda con pull-up: se espera que lea `0xFF`, que es mantener) y que, después, R0 opere normalmente.

Reconfigurar durante una ronda está cubierto por la respuesta general del profesor del 16/11 (cualquier decisión de diseño es válida), sin una confirmación específica (T126). Solo si el ayudante lo prohíbe de forma explícita, R2 no compite (árbol, regla 5) y esta prueba se salta.

## 6. Preguntas para el ayudante

Se hacen ese día, con la maestra delante. Cada respuesta va a la plantilla.

1. Cuántos precios manda la maestra en cada ronda.
2. Si la maestra usa el timing del testbench (SCLK de 1 MHz, 1 µs antes del primer bit). Ya medido con el medidor: confirmarlo.
3. Si caja 10 000 y comisión 5 son definitivas.
4. Si la placa se reinicia entre rondas.
5. Ya no se pregunta: el profesor confirmó el 16/11 que el Espino multihilo es válido (T126).
6. Opcional: que el ayudante confirme que se puede reconfigurar la FPGA durante una ronda. Ya está cubierto por la respuesta general del profesor (T126); solo un no explícito deja fuera a R2.
7. Si las series ocultas salen del mismo generador que la de práctica.
8. Si se pueden usar los botones de la placa durante la competencia (nuestros diseños no los usan).
9. Cómo se calcula el puntaje.

## 7. Plantilla para anotar

| Prueba | Ronda 1 (10 ms) | Ronda 2 (1 ms) | Ronda 3 (0,1 ms) |
|--------|-----------------|----------------|------------------|
| Medidor: medida 0 (SCLK) / kHz | | | |
| Medidor: medida 2 (período) | | | |
| Medidor: medida 4 / 5 (CS_n) | | | |
| Medidor: medida 6 (tiempo libre) | | | |
| Medidor: medida 7 (precios) y LED4 | | | |
| R0: patrimonio, ticks sin operar | | | |
| R1: patrimonio, ticks sin operar, latido | | | |
| R2: patrimonio, ¿cambió a R0? | | | |
| Relevo: ticks sin decisión | | | |

Respuestas del ayudante: 1 ___ 2 ___ 3 ___ 4 ___ 5 ___ 6 ___ 7 ___ 8 ___ 9 ___

## 8. Si algo falla

| Se ve | Qué significa | Qué hacer |
|-------|---------------|-----------|
| La maestra muestra a nuestro grupo sin operar en todos los ticks, con cualquier peldaño | No llega MISO o no hay tierra común. Ojo: con la regla de cotas es normal no operar hasta que la serie toca 100 o 255 | Revisar tierra y PMOD 3. Grabar la autoprueba del peldaño: si la autoprueba pasa en la placa, el problema es la conexión |
| R0, R1 o R2 dan patrimonios distintos en la misma ronda | Con la regla de cotas no debería pasar: los tres deciden los mismos bytes | Anotar la ronda y los tres patrimonios. Si se registró la serie, correrla esa noche en el gemelo con los tres |
| R0 opera y R1 no | R1 no responde a tiempo con ese SPI | Mirar la medida 6 del medidor. Si es menor que 600, es la regla 3 o 4 del árbol: compite R0 |
| R2 cambia a R0 sin falla inyectada | El vigilante se disparó en funcionamiento normal | R2 no compite. Anotar la ronda y el momento |
| `iceprog` falla | La placa no está conectada a WSL | `usbipd attach --wsl --busid X-Y` en PowerShell, y repetir |
| LED4 del medidor encendido | Alguna transacción con un número de flancos distinto de 8, flancos de SCLK con `CS_n` en alto, o SCLK en alto al bajar `CS_n` | Anotar en qué ronda. Repetir con SW3 para ver si se repite. Si hay flancos con `CS_n` en alto, preguntar al ayudante si el bus es compartido y no competir con R2 sin el arreglo de la rama `p10-arreglo-1` |
