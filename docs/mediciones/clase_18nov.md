# Clase del 18/11 con la maestra real

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

La primera parte copia lo que informó Nicolás, sin interpretar. La segunda es lo que se comprobó después con las referencias y con los minutos reales (`docs/cotas.md`, sección 7).

## 1. Lo que se vio

- **R2 (`r2_cotas_multi.bin`) corrió las tres velocidades "sin atrasos".**
- **La ronda dura 20 000 ticks.** El mismo programa debe usarse en las tres rondas.
- **`r2_cotas_multi.bin` solo graba bien con `iceprog -b`.** Sin borrado completo, la verificación de `iceprog` falla.
- **Resultados** (nuestro patrimonio contra el del otro grupo que se nombra):

| Ronda | Serie | Lugar | Nuestro patrimonio | Rival |
|-------|-------|-------|--------------------|-------|
| 0,1 ms | sin identificar | primeros | cerca de 25 000 | |
| 1 ms | sin identificar | primeros | 18 870 | 18 735 |
| | AMD, enero de 2022 | primeros | 21 895 | 10 385 |
| 10 ms | Tesla, enero de 2022 | segundos | 18 779 | 21 467 |

- **El rival que ganó en Tesla** compra al ver el 100, vende con precio de 220 o más y no vuelve a entrar.
- **Captura de la ronda de Tesla** con el registrador: `ronda_10ms_clase.csv` (ya decodificada) y `captura_tesla_ene2022_10ms.bin` (en bruto, registros de 5 bytes). Quedan fuera del repositorio, con los minutos de Alpaca.

## 2. Lo que se comprobó

| Comprobación | Resultado | Cómo se reproduce |
|--------------|-----------|-------------------|
| La captura en bruto | 20 000 registros, ninguno perdido, ninguna transacción con error, ningún byte suelto; período de 1953 unidades (9 999,4 µs) en todos menos el primero y uno a la mitad (registro 6648, más de 10,48 ms) | `python3 tools/registrador.py --convertir captura_tesla_ene2022_10ms.bin` |
| El CSV que arma la herramienta | Idéntico byte a byte a `ronda_10ms_clase.csv` | `cmp` de los dos archivos |
| El formato de 5 bytes | Precio = 2 × byte 1 + bit 6 del byte 3, confirmado en el RTL (`rtl/registrador/registrador.v:24-28` y `:136-141`) | `docs/registrador.md`, sección 2 |
| MISO durante la captura | 0x00 en los 20 000 registros: la placa tenía el registrador, que manda mantener. La captura es de una corrida aparte, no de la de R2 | Columna `decision` del detalle |
| La serie de Tesla | Es TSLA del 10/1/2022 a las 10:20 al 24/3/2022 a las 12:09 (hora de Nueva York), normalizada con su mínimo y su máximo: 20 000 de 20 000 precios iguales | `python3 ref/cotas/reales.py comprobar --captura ronda_10ms_clase.csv` |
| Nuestra referencia en Tesla | `Cotas("espera", banda=60)` da **18 779**, lo que mostró la maestra | `python3 ref/cotas.py ronda_10ms_clase.csv --inicio espera --banda 60` |
| El rival de Tesla | "Comprar 63 (repetido) desde el primer 100 hasta ver 220 o más, después vender 63 y no volver a entrar" da **21 467**, lo que mostró la maestra. Comprando solo en los ticks con 100 da 21 500, y comprando y vendiendo una sola vez, 17 550: la versión repetida es la que coincide | `planb.UnaVez(100, 220)`, `ref/cotas/validar.py` |
| La ronda de AMD | AMD con el mismo inicio que Tesla (10/1/2022 a las 10:20) da **21 895** con nuestra regla, lo que mostró la maestra. Hay 119 inicios de enero de 2022 que dan esa misma cifra, así que el inicio común es la explicación más simple, no una prueba | `ref/cotas/reales.py` |
| La serie de práctica | Es META del 23/2/2022 a las **15:20** (no 15:10) al 9/5/2022 a las 10:39: 20 000 de 20 000 precios iguales con los minutos de Alpaca | `python3 ref/cotas/reales.py comprobar` |

**Normalización por ronda.** La ronda de Tesla tiene 20 000 precios, toca 100 y 255, y es una ventana de 20 000 minutos normalizada con sus propios extremos. Con la ronda de 20 000 ticks, cada ronda se normaliza por separado: la hipótesis de la familia "cotas" (`docs/cotas.md`, sección 1) quedó confirmada para esta ronda.

## 3. La grabación con `iceprog -b` y la placa del 16/11

**Por qué falla sin `-b`.** `r2_cotas_multi.bin` ocupa 64 600 bytes y su segunda imagen empieza en 0x7E7C (`python3 tools/ver_multi.py bitstreams/r2_cotas_multi.bin`). Sin `-b`, `iceprog` borra en bloques de 64 kB alineados: como el archivo cabe en 64 kB, manda un solo borrado en la dirección 0. Si la flash de la placa borra 32 kB con esa orden, todo lo que está desde 0x8000 (casi toda la segunda imagen) se escribe sobre lo que había, sin borrar, y la verificación encuentra diferencias. Es lo que la factibilidad del warm boot había anticipado (`factibilidad/e_warmboot/README.md`, riesgo del tamaño del sector). `iceprog -t` muestra el identificador de la flash, si se quiere confirmar el modelo.

**¿Quedó mal grabado R2 el 16/11 sin que lo notáramos? No.**

1. `iceprog` verifica cada byte después de escribir y, si encuentra una diferencia, se detiene con "Found difference between flash and file!" y código de salida 3. Una grabación que terminó en "VERIFY OK" es idéntica al archivo, con o sin `-b`. Lo que no pasa es que quede mal grabada en silencio.
2. El 16/11 no se grabó el R2 de competencia (`r2_multi.bin`): se grabaron `autoprueba_r2_multi.bin` y `relevo_r2_multi.bin` (`docs/mediciones/placa_16nov.md`), y las instrucciones de ese día ya decían `iceprog -b` para los dos (`docs/autoprueba.md`, secciones 9.3 y 9.4, desde el commit `144456e`, anterior a las pruebas).
3. Lo que se vio en la placa lo confirma: la FPGA comprueba el CRC de cada imagen al configurarse y no arranca con una imagen dañada. La imagen 0 de la autoprueba dio la firma esperada ("D7" y "15") y media hora sin disparo; la imagen 1 de `relevo_r2_multi.bin` arrancó y respondió el eco de la UART, con el relevo medido en 35,50 ms.
4. Lo único que el 16/11 no ejercitó es la imagen 1 (la testigo) de `autoprueba_r2_multi.bin`, que no se mostró a la vista. Como se grabó con `-b` y la verificación de `iceprog` cubre el archivo entero, no hay motivo para pensar que quedó mal.

Hoy, el 18/11, R2 se grabó con `-b`, corrió las tres velocidades y dio en Tesla y AMD exactamente lo que da su referencia: la imagen 0 está bien grabada. La imagen 1 (R0 de respaldo) no se ejercitó, pero pasó la misma verificación.
