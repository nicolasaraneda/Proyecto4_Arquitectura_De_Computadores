# Checklist del 26/11: pruebas con la maestra real

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

La maestra existe un solo día. Este es el orden de las pruebas, qué se mide en cada una y qué hacer si algo falla. Lo que se anota va en la plantilla de la sección 7, que después se pasa a `docs/mediciones/maestra_26nov.md`. Con eso se decide el peldaño que compite (`docs/arbol_decision.md`).

Puerta de maestra (plan del proyecto, sección 16.4): cada peldaño tiene que correr las tres rondas sin perder precios ni decisiones, y su patrimonio tiene que coincidir con el que predice el gemelo si la serie es conocida. Si la serie no es conocida, R0 y R1 tienen que comportarse de forma coherente entre sí.

## 1. Antes de salir (25/11 en la noche)

1. `git checkout v-maestra-26nov` (la etiqueta del congelamiento del hardware) y `make check` en verde.
2. `cd bitstreams && sha256sum -c SHA256SUMS && cd ..`: todas las líneas en `OK`. Se llevan, en este orden de uso:

   | Archivo | Para qué |
   |---------|----------|
   | `medidor_spi.bin` | Medir el SPI real de la maestra (sección 3) |
   | `r0_base_max_media.bin` | R0 |
   | `r1_fondo.bin` | R1 |
   | `r2_multi.bin` | R2 con R0 de respaldo (imagen múltiple) |
   | `r2_falla_multi.bin` | R2 con el supervisor colgado y R0 de respaldo: el relevo con la maestra real (sección 5) |
   | `autoprueba_r0.bin`, `autoprueba_r1.bin`, `autoprueba_r2_multi.bin` | Si algo falla, separar placa de maestra (`docs/autoprueba.md`, sección 9). Deberían haberse probado antes del 26 |
   | `relevo_r2_multi.bin` y `relevo_r2_multi_sin_dormir.bin` | Tiempo del relevo en la placa, sin maestra (`docs/autoprueba.md`, sección 10) |

   Las imágenes múltiples (`*_multi.bin`) se graban con `iceprog -b`.

3. Notebook con WSL, `usbipd` y OSS CAD Suite (`iceprog --help` responde). Cable USB de la Go Board, 4 cables hembra-hembra para el PMOD más uno de tierra, y el teléfono con cámara lenta (para el relevo).
4. Las preguntas para el ayudante impresas (sección 6).

## 2. Conexión

La Go Board se conecta a la maestra por el PMOD (pines del `goboard.pcf` del curso):

| Señal | Pin del FPGA | PMOD de la Go Board |
|-------|-------------|---------------------|
| `CS_n` | 65 | 1 |
| `MOSI` | 64 | 2 |
| `MISO` | 63 | 3 |
| `SCLK` | 62 | 4 |
| Tierra | | 5 u 11 |

Verificar los números del PMOD con el ayudante antes de conectar. **La tierra se conecta primero.** No se conecta 3,3 V entre placas: cada una se alimenta por su USB.

## 3. Medir el SPI real con el medidor (primera prueba, unos 10 minutos)

Es lo primero porque decide entre R0 y R1 (regla 3 del árbol). `medidor_spi.bin` no tiene el SoC: escucha la maestra, responde siempre `0x00` (mantener) y muestra lo que mide en los 7 segmentos (`rtl/medidor/medidor_spi.v`).

1. `iceprog bitstreams/medidor_spi.bin`. Al terminar ("VERIFY OK"): LED1 a LED4 apagados, 7 segmentos en `FF`.
2. Pedir a la maestra la ronda 1 (10 ms). Al terminar, sin apretar SW3, leer las medidas apretando SW1 para avanzar. Los LED1 a LED3 dicen el número de la medida en binario (LED1 es el bit 0). Para cada medida anotar el byte bajo (sin SW4) y el alto (con SW4 apretado):

   | Medida | Qué es | Testbench del curso | Cómo se lee |
   |--------|--------|---------------------|-------------|
   | 0 | Período mínimo de SCLK, en ciclos de 40 ns | `0x0019` (25) | SCLK en kHz = 25 000 / valor |
   | 1 | Período máximo de SCLK | `0x0019` | Si es muy distinto de la medida 0, el SCLK no es estable |
   | 2 | Período entre precios, último, en unidades de 0,64 us | `0x3D09` en la ronda 1, `0x061A` en la 2, `0x009C` en la 3 | T en us = valor x 0,64 |
   | 3 | Período mínimo entre precios | Igual | |
   | 4 | Duración de `CS_n` en bajo, en ciclos | `0x00ED` (9,5 us) | |
   | 5 | De la bajada de `CS_n` al primer flanco de SCLK, en ciclos | `0x0025` (1,5 us) | |
   | 6 | Tiempo libre mínimo entre transacciones, en ciclos | `0xFFFF` en las rondas 1 y 2, `0x08D6` (2262) en la 3 | Es el presupuesto de la respuesta. R1 necesita 444 y R0 44 |
   | 7 | Transacciones contadas | Las de la ronda | Número de precios por ronda (pregunta 1 al ayudante) |

   LED4 encendido significa que alguna transacción no tuvo 8 flancos de SCLK: anotarlo, porque el esclavo del SoC perdería ese precio.
3. Apretar SW3 (borra), pedir la ronda 2 y repetir. Lo mismo con la ronda 3.
4. **Decisión inmediata.** Si en la ronda 3 la medida 0 es mayor que 217 (`0x00D9`, es decir, SCLK menor que 115 kHz), o la medida 6 es menor que 600, R1 no tiene margen: se prueba igual, pero el titular es R0 (árbol, reglas 3 y 4).

Si no se puede usar el medidor (por ejemplo, la maestra solo corre con un grupo a la vez y no hay tiempo), lo mismo se mide con un osciloscopio o un analizador lógico en el PMOD: período de SCLK, duración de `CS_n` y período entre bajadas de `CS_n`, en las tres rondas.

## 4. Peldaños con la maestra, del más seguro al más alto

Para cada peldaño, las tres rondas. Antes de cada peldaño se anota el sha256 que imprime `sha256sum` del archivo que se va a grabar.

1. **R0.** `iceprog bitstreams/r0_base_max_media.bin`. Rondas 1, 2 y 3. Anotar el patrimonio final que muestra la maestra en cada ronda y si en algún tick nuestro grupo quedó sin operar cuando los demás operaban.
2. **R1.** `iceprog bitstreams/r1_fondo.bin`. Lo mismo. Mirar además la telemetría: el LED de latido cambia con cada precio, los otros tres LED son los votos de los gestores y los 7 segmentos muestran la posición objetivo.
3. **R2.** `iceprog -b bitstreams/r2_multi.bin` (con `-b`: la imagen múltiple ocupa más de 32 kB y hay que borrar la flash entera, T91 y `docs/tabla_vigilante.md`). Lo mismo. En funcionamiento normal **no debe cambiar a R0**: si la telemetría de R1 desaparece a mitad de una ronda, el vigilante se disparó; anotar en qué ronda y en qué momento.

Si la serie de la maestra es conocida (por ejemplo, la de práctica), el patrimonio de cada ronda se compara con el del gemelo:

```
make fondo-hex
build/gemelo --hex sw/trade.hex --serie SERIE.csv --periodo-ns 100000 --nticks N           # R0
build/gemelo --barrel --xd 3 --tabla sw/fondo_tabla.hex --hex build/fondo/fondo.hex \
             --serie SERIE.csv --periodo-ns 100000 --nticks N                               # R1 y R2
```

con el período de cada ronda (10 000 000, 1 000 000 y 100 000 ns) y el SCLK medido (`--sclk-medio-ns`, la mitad del período de SCLK en ns). Si la maestra parte con la placa ya encendida, los precios perdidos en el reset son 0: usar `--inicio-ns 200000`.

Si la serie no es conocida: en las series de práctica R0 y R1 escriben los mismos bytes, así que en una serie parecida sus patrimonios deben ser parecidos. Una diferencia grande entre R0 y R1 en la misma ronda se anota y se revisa con el gemelo esa noche.

## 5. Relevo de R2 con la falla inyectada (solo si el ayudante permite reconfigurar)

`bitstreams/r2_falla_multi.bin` es R2 con el supervisor colgado a propósito en el tick 100 y R0 de respaldo: a los 100 precios deja de escribir `DECISION`, el vigilante dispara al quinto precio sin respuesta y la placa pasa a R0. Su `.asc` es el mismo que la puerta de simulación de R2 probó por los pines (`make r2-falla`).

1. `iceprog -b bitstreams/r2_falla_multi.bin` y correr la ronda 3.
2. Anotar cuántos ticks quedó nuestro grupo sin decisión nueva según la maestra, y filmar la placa en cámara lenta. La predicción, con los 53 ms de la hoja de datos, es de unos 536 ticks a 0,1 ms (5 sin respuesta que esperan al vigilante y 531 de reconfiguración), unos 58 a 1 ms y unos 10 a 10 ms. Si antes se midió el tiempo del relevo en la placa (`docs/autoprueba.md`, sección 10), `python3 tools/medir_relevo.py --traducir MS` da la predicción con ese tiempo.
3. Anotar qué hace la maestra mientras la FPGA se reconfigura (MISO queda con pull-up: se espera que lea `0xFF`, que es mantener) y que, después, R0 opere normalmente.

Si el ayudante no permite reconfigurar, R2 no compite (árbol, regla 5) y esta prueba se salta.

## 6. Preguntas para el ayudante

Se hacen ese día, con la maestra delante. Cada respuesta va a la plantilla.

1. Cuántos precios manda la maestra en cada ronda.
2. Si la maestra usa el timing del testbench (SCLK de 1 MHz, 1 us antes del primer bit). Ya medido con el medidor: confirmarlo.
3. Si caja 10 000 y comisión 5 son definitivas.
4. Si la placa se reinicia entre rondas.
5. Si un Espino multihilo con instrucciones en custom-0 sigue siendo Espino (si no, compite R0).
6. Si se puede reconfigurar la FPGA durante una ronda (si no, R2 no compite).
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
| La maestra muestra a nuestro grupo sin operar en todos los ticks, con cualquier peldaño | No llega MISO o no hay tierra común | Revisar tierra y PMOD 3. Grabar la autoprueba del peldaño: si la autoprueba pasa en la placa, el problema es la conexión |
| R0 opera y R1 no | R1 no responde a tiempo con ese SPI | Mirar la medida 6 del medidor. Si es menor que 600, es la regla 3 o 4 del árbol: compite R0 |
| R1 y R0 operan distinto en la misma ronda | Puede ser normal en una serie que no es la de práctica | Anotar la serie si se puede y comparar con el gemelo esa noche |
| R2 cambia a R0 sin falla inyectada | El vigilante se disparó en funcionamiento normal | R2 no compite. Anotar la ronda y el momento |
| `iceprog` falla | La placa no está conectada a WSL | `usbipd attach --wsl --busid X-Y` en PowerShell, y repetir |
| LED4 del medidor encendido | Alguna transacción con un número de flancos distinto de 8 | Anotar en qué ronda. Repetir con SW3 para ver si se repite |
