# R3 (C1) el día de prueba con la maestra: pasos

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

**Día de prueba: miércoles 25/11, por confirmar.** La versión de una página, en orden, es `docs/checklist_25nov.md`. Este documento complementa `docs/checklist_26nov.md` (conexión, medidor, registrador y peldaños R0 a R2), que no cambia. Aquí está solo lo de R3: en qué orden se carga, la rutina de cada ronda, cómo se lee en la placa la cuenta que R3 emula, contra qué se compara, y la autoprueba que se puede correr antes sin la maestra (sección 9). La regla del día la fijó Nicolás (21/11): **si la caja o el patrimonio no calzan con la pantalla de la maestra, se anota la diferencia y compite la banda 40**. Este documento no decide qué peldaño compite.

## 1. Qué se lleva de R3

`cd bitstreams && sha256sum -c SHA256SUMS && cd ..` tiene que dar `OK` en todas las líneas. Los hash completos están en `bitstreams/SHA256SUMS` y en `docs/puertas.md`.

| Archivo | Para qué |
|---------|----------|
| `medidor_spi.bin` | El medidor del SPI de la maestra. **Va antes que R2 y que R3**: con su medida se decide si R3 sigue (sección 2.2). Su hash está en `docs/checklist_26nov.md`, sección 1 |
| `r2_banda40_multi.bin` | R2, la banda 40. Va primero: es el respaldo y la vara de comparación |
| `r3_c1_multi.bin` | R3: imagen 0 C1, imagen 1 R0 con la banda 40 |
| `r3_c1_apagada_multi.bin` | R3 con la política apagada en la tabla: el hardware de R3 decidiendo la banda 40. Sirve para separar un problema del hardware nuevo de un problema de la política |
| `r3_c1_falla_multi.bin` | R3 con el hilo 0 colgado en el tick 100 y R0 de respaldo: el relevo del vigilante en el ruteo de R3 |
| `autoprueba_r3_multi.bin` y `relevo_r3_multi.bin` | La autoprueba de R3, para correrla antes sin la maestra (sección 9) |

Todas son imágenes múltiples: se graban con `iceprog -b` (borra la flash entera; sin `-b` la verificación falló el 18/11).

## 2. Orden de carga

1. **El medidor antes que R2 y que R3.** `iceprog bitstreams/medidor_spi.bin`, una ronda y leer el SCLK. Con eso se decide si R3 sigue o si compite la banda 40 (sección 2.2).
2. **R2.** `iceprog -b bitstreams/r2_banda40_multi.bin`. Las rondas que dé la maestra, como en la sección 4 de `docs/checklist_26nov.md`. Anotar el patrimonio (y la caja, si la muestra) de cada ronda. Con eso la banda 40 queda probada antes de tocar nada nuevo.
3. **R3 después**, solo si el medidor lo permite. `iceprog -b bitstreams/r3_c1_multi.bin`. Las mismas rondas, leyendo la placa al final de cada una (secciones 3 y 4).
4. Si queda tiempo: `r3_c1_apagada_multi.bin` (sección 6) y `r3_c1_falla_multi.bin` (sección 7).

Decisión de Nicolás (21/11): **entre rondas se desconecta y se conecta el USB**. C1 no se rearma sola y no hace falta que lo haga. La razón:

- C1 supone una ronda de 20 000 ticks contada desde el encendido: el reloj de tramos, el modo (el candado no tiene vuelta) y las dos cuentas emuladas parten de cero solo con el reset.
- Pasado el tick 20 000 sin reset, R3 entra a modo seguro (LED1 encendido) y desde ahí decide la banda 40 sin política. No falla, pero ya no es C1.

### 2.1 Rutina por ronda

Con los cables del PMOD puestos y la maestra encendida, antes de cada partida:

| Paso | Qué se hace | Qué se tiene que ver |
|------|-------------|----------------------|
| 1 | Desconectar el USB de la Go Board. Esperar un par de segundos | Todo apagado |
| 2 | Conectar el USB | |
| 3 | Esperar la carga: contar dos segundos | Los 7 segmentos en `00` y los cuatro LED apagados |
| 4 | Revisar el LED1 | **Apagado** |
| 5 | Recién ahí, pedir la partida | Apenas llegan precios: `10` en los 7 segmentos y, mientras se mantiene SW1 apretado, `27` (los 10 000 iniciales) |

**Cuánto demora la carga.** Al conectar, la FPGA lee su configuración desde la flash. Leer la imagen demora unos 35 ms: es lo que se midió en la placa el 16/11 para una reconfiguración (35,50 ms, una sola medición; la hoja de datos da 53 ms como valor típico). En el encendido en frío se suma lo que tarda en subir la alimentación, que no está medido. Después el SoC tiene su propio reset de 0,16 ms. En total es bastante menos de un segundo: los dos segundos del paso 3 sobran, y son sobre todo para que el computador vuelva a reconocer el USB.

**Si en el paso 3 no se ve `00` con los LED apagados**, no partir:

| Se ve antes de partir | Qué pasó | Qué hacer |
|-----------------------|----------|-----------|
| Dígitos distintos de `00` | La placa no se reinició: está mostrando el último byte de la ronda anterior | Repetir los pasos 1 a 3 |
| LED1 encendido | La placa viene de una ronda anterior y ya está en modo seguro (banda 40), o recibió precios falsos por ruido con los cables sueltos | Repetir los pasos 1 a 3, con los cables puestos y la maestra encendida antes de conectar |
| Dígitos que cambian solos sin que la maestra haya partido | Llegan transacciones que nadie mandó: cables sueltos o mala tierra | Revisar la conexión (tierra primero) y repetir |

**Si la placa quedó en banda 40 durante la ronda**, se reconoce así:

| Se ve durante o al final de la ronda | Qué significa |
|--------------------------------------|---------------|
| LED1 encendido, los 7 segmentos siguen mostrando la cuenta | R3 pasó a modo seguro y desde ese tick decidió la banda 40. La cuenta emulada sigue valiendo: se anota igual. Causas: más de 20 000 ticks desde el reset, un precio bajo 100, o un hilo que no publicó a tiempo |
| LED1 encendido desde el primer precio | Se grabó `r3_c1_apagada_multi.bin` (política apagada) y no `r3_c1_multi.bin`. Comprobar el hash |
| Los 7 segmentos se quedan en `00` toda la ronda y los LED apagados, pero la maestra muestra que el grupo opera | La placa pasó a la imagen de respaldo, R0 con la banda 40, que no tiene telemetría: el vigilante se disparó. Anotar en qué ronda. Si fue al principio, también puede ser que R3 no esté recibiendo precios: mirar si la maestra registra decisiones |
| `10` y `27` todo el tiempo, con el modo en `00` | R3 recibe precios pero nunca operó: la serie no tocó ningún extremo ni cumplió la apuesta. Con una serie normalizada de 20 000 ticks no debería pasar |

En los tres primeros casos la placa decidió la banda 40 en toda la ronda o en parte: el patrimonio de la pantalla se compara con el de R2 en la misma serie, y se anota que esa ronda no prueba a C1.

### 2.2 El primer paso: el medidor del SPI y la regla de 250 y 150 kHz

Decisión de Nicolás (21/11). R3 responde más lento que R2 (hasta 807 ciclos con los cuatro hilos sanos y 916 con un hilo colgado, contra los 127 o 128 de R2), así que con un SCLK lento le queda menos tiempo libre entre transacciones. Por eso lo primero del día es medir el SCLK de la maestra con `medidor_spi.bin`, antes de grabar R2 y R3. El 18/11 R2 corrió con la maestra real (`docs/puertas.md`, sección "Puerta de maestra: la clase del 18/11"), pero eso no prueba el SPI de R3.

1. `iceprog bitstreams/medidor_spi.bin`. Al terminar ("VERIFY OK"): LED1 a LED4 apagados y `FF` en los 7 segmentos. Si la verificación falla, repetir con `-b`.
2. Pedir una ronda a la maestra. Conviene la de 0,1 ms, que es la que deja menos tiempo libre; si la maestra solo da la de 10 ms primero, medir ahí y repetir en la de 0,1 ms cuando se pueda.
3. Sin apretar SW3, leer con SW1 las medidas 0 y 1 (período mínimo y máximo de SCLK, en ciclos de 40 ns; byte bajo sin SW4 y alto con SW4 apretado). El procedimiento completo y la tabla de las ocho medidas están en `docs/checklist_26nov.md`, sección 3. **Decide la medida 1**, el período más largo, porque es el SCLK más lento que vio el esclavo. SCLK en kHz = 25 000 dividido por la medida.

| SCLK medido | Medida 1 | Qué se hace |
|-------------|----------|-------------|
| 250 kHz o más | 100 (`0x0064`) o menos | **R3 sigue.** Se continúa con R2 y R3 como en la sección 2 |
| Entre 150 y 250 kHz | 101 a 166 (`0x0065` a `0x00A6`) | **R3 sigue y se anota el margen**: el SCLK, la medida 6 (tiempo libre mínimo entre transacciones, en ciclos) y cuánto le sobra a R3, que es la medida 6 menos 916 |
| Menos de 150 kHz | 167 (`0x00A7`) o más | **Compite la banda 40** (R2 o R0 según el árbol, `docs/arbol_decision.md`). R3 no se prueba como candidato |

Qué hay medido detrás de estos números, para saber hasta dónde llega: en la matriz de estrés de R3 (`docs/mediciones/c1/estres.txt`) la respuesta sale a tiempo con SCLK de 200 kHz a 0,1 ms (peor caso 725 ciclos de 1362 disponibles, línea 13), de 500 kHz y de 1 MHz, y no sale con 100 kHz (la maestra de ese caso deja 237 ciclos libres, línea 72, exploración). Los casos de 150 y de 250 kHz no se simularon: caen entre un caso que falla y uno que pasa (150 kHz) o sobre uno que pasa (250 kHz). Además, en esa matriz el tiempo de `CS_n` crece con el período de SCLK; el de la maestra real es otro y lo dicen las medidas 4 y 5 del medidor.

Al terminar el medidor se sigue con R2 (sección 2, paso 2). Si el medidor enciende LED4 (transacciones con otro número de flancos, flancos con `CS_n` en alto o modo 2 o 3), se anota y se aplica lo que dice `docs/checklist_26nov.md`, sección 3.

## 3. Qué muestra la placa

R3 lleva dentro una copia de la contabilidad oficial (caja 10 000, comisión 5): la cuenta propia y la de un clon que opera la banda 40. Los 7 segmentos muestran **un byte en hexadecimal** de esas cuentas, y los cuatro botones eligen cuál.

**Importante: el display solo se actualiza cuando llega un precio.** El programa lee los botones y escribe los 7 segmentos una vez por tick. Mientras la maestra manda precios, el display sigue a los botones. Cuando la ronda termina, el display queda congelado en el byte que elegían los botones **en el último precio**, y apretar botones después ya no cambia nada. Por eso:

- Sin tocar nada, al terminar la ronda queda a la vista el **byte bajo del patrimonio**.
- Para dejar congelado otro byte hay que mantener apretada su combinación desde antes de que termine la ronda y soltar después del último precio.
- Los demás bytes se leen **en vivo**, con la ronda corriendo. En la ronda de 10 ms (200 segundos) hay tiempo de sobra; en la de 1 ms (20 segundos) alcanza para uno o dos; en la de 0,1 ms (2 segundos) solo queda el byte congelado.

| Botones apretados | Qué se ve |
|-------------------|-----------|
| Ninguno | Patrimonio propio emulado, byte bajo |
| SW1 | Patrimonio, segundo byte |
| SW2 | Patrimonio, tercer byte (distinto de `00` solo sobre 65 535) |
| SW1 + SW2 | Modo: `00` fase A (todavía no vio 100 ni 255), `01` motor, `02` candado |
| SW3 | Caja propia, byte bajo |
| SW3 + SW1 | Caja, segundo byte |
| SW3 + SW2 | Caja, tercer byte |
| SW4 | Acciones propias, byte bajo |
| SW4 + SW1 | Acciones, segundo byte |
| SW4 + SW3 | Caja del clon de la banda 40, byte bajo |
| SW4 + SW3 + SW1 | Caja del clon, segundo byte |
| SW4 + SW3 + SW2 | Caja del clon, tercer byte |

- **LED1**: modo seguro. Apagado es lo normal. Encendido significa que R3 dejó la política y decide la banda 40. El LED también se escribe una vez por tick y queda como estaba en el último precio.
- LED2 a LED4 no se usan: apagados.
- El patrimonio emulado es caja más acciones por el último precio recibido. Con acciones en la mano cambia en cada tick; en caja queda quieto. La caja y las acciones solo cambian cuando se ejecuta una orden, así que se leen bien en vivo.
- Para pasar a decimal: patrimonio = tercer byte x 65 536 + segundo x 256 + byte bajo. Por ejemplo `58` y `9A` son 0x589A = 22 682 (`python3 -c "print(0x589A)"`).

## 4. Qué se anota y qué se compara, por ronda

Lo que se puede leer depende del período:

| Ronda | Cómo se lee |
|-------|-------------|
| 10 ms | En los últimos 30 segundos, con la ronda corriendo: SW1 (segundo byte del patrimonio), SW1 + SW2 (modo), SW3 y SW3 + SW1 (caja), SW4 (acciones). Soltar todo antes del final: queda congelado el byte bajo del patrimonio |
| 1 ms | Mantener SW1 apretado durante toda la ronda y soltar al terminar: queda congelado el segundo byte. O no tocar nada y queda el byte bajo. Uno de los dos por partida |
| 0,1 ms | Igual que a 1 ms: un byte por partida |

Qué se compara:

| Dato de la placa | Contra qué | Qué prueba |
|------------------|------------|------------|
| Byte bajo del patrimonio (sin botones, congelado al final) | El patrimonio de la pantalla de la maestra, módulo 256: `python3 -c "print(hex(PATRIMONIO % 256))"` | Detecta cualquier diferencia chica, por ejemplo una comisión distinta de 5: con dos cuentas distintas el byte bajo coincide por azar una vez de cada 256 |
| Segundo byte del patrimonio (SW1) | El patrimonio de la pantalla dividido por 256, sin decimales: `python3 -c "print(hex(PATRIMONIO // 256))"` | Detecta diferencias grandes |
| Caja y acciones (ronda de 10 ms, en vivo) | La caja y las acciones que muestre la maestra, si las muestra | Lo mismo, por separado |
| Modo (SW1 + SW2) | Se anota. `02` es candado: desde ahí R3 copia a la banda 40 | |
| LED1 | Tiene que estar apagado | |
| Patrimonio de R3 en la pantalla | El de R2 en la misma ronda. Se anota la diferencia, a favor o en contra | Lo que C1 ganó o perdió contra la banda 40 |

Con las tres rondas se juntan los dos bytes: en la de 10 ms se leen todos, y en las otras dos conviene dejar una vez el byte bajo y otra el segundo.

Qué dice cada resultado:

- **Los bytes calzan con la pantalla**: la copia de la contabilidad que lleva R3 es la de la maestra. Es la condición para que C1 funcione como se midió, porque el candado se decide con esa cuenta.
- **No calzan**: se anota la diferencia, la ronda, el modo y los bytes leídos. Según la regla de Nicolás, compite la banda 40. Causas posibles, para revisar esa noche con la serie registrada: comisión o caja inicial distintas de 5 y 10 000, una regla de recorte distinta a la del testbench, o un precio que la placa no vio.
- **LED1 encendido** sin haber pasado de 20 000 ticks ni haber visto un precio bajo 100: un hilo se atrasó o se colgó. Se anota en qué ronda. La decisión siguió saliendo (banda 40), pero es un hallazgo.

Si la serie quedó registrada, esa noche se compara todo de una vez: `python3 ref/c1/c1.py SERIE.csv --placa` imprime el patrimonio, la caja, las acciones, el modo y el byte de cada combinación de botones, y el patrimonio tiene que ser el de la pantalla.

## 5. Valores esperados si la serie es conocida

Con las series que ya se conocen, 20 000 ticks y la placa encendida antes del primer precio:

| Serie | Patrimonio de R3 | En la placa (sin botones, SW1) | Modo final | Caja y acciones | Banda 40 (R2) |
|-------|------------------|--------------------------------|------------|-----------------|---------------|
| Meta de práctica (`data/practica_meta.csv`) | 22 682 | `9A`, `58` | `02` | 22 682 y 0 | 21 392 |
| Tesla de la clase del 18/11 | 21 224 | `E8`, `52` | `02` | 21 224 y 0 | 20 795 |
| AMD de la clase del 18/11 | 27 199 | `3F`, `6A` | `02` | 38 y 157 | 26 470 |

Para cualquier otra serie que quede registrada (`docs/checklist_26nov.md`, sección 4b):

```
python3 ref/c1/c1.py build/maestra/ronda3_serie.csv --placa
```

imprime el patrimonio, el modo, la caja, las acciones y el byte que debe verse con cada combinación de botones. El gemelo da lo mismo ciclo a ciclo, con el período de la ronda:

```
python3 tools/pochoasm.py sw/c1.s -o build/c1/c1.hex
build/gemelo --barrel --xd 3 --tabla sw/c1_tabla.hex --hex build/c1/c1.hex \
             --serie build/maestra/ronda3_serie.csv --periodo-ns 100000 --inicio-ns 200000 --nticks N
```

(`N` es la cantidad de precios de la ronda; sin `--nticks` el gemelo corre 2000.)

Si la maestra parte con la placa recién reiniciada y manda precios antes de 164 µs, la placa no ve los primeros (está en su reset): quitar `--inicio-ns 200000` y usar `--periodo-ns` en `ref/c1/c1.py`.

## 6. R3 con la política apagada (si algo no calza, o si sobra tiempo)

`iceprog -b bitstreams/r3_c1_apagada_multi.bin`. Es el mismo hardware y el mismo programa de R3 con una palabra de la tabla en 0: decide exactamente la banda 40.

- LED1 queda encendido desde el primer precio (modo seguro: es lo que apaga la política).
- En la misma serie, el patrimonio de la pantalla tiene que ser **el mismo de R2**.
- Los 7 segmentos siguen mostrando la cuenta emulada, con las mismas reglas de lectura de las secciones 3 y 4: tiene que calzar con la pantalla.

Si R3 apagado calza con R2 y R3 con la política no calza con su cuenta, el problema está en la política o en la contabilidad emulada y no en el hardware nuevo. Si R3 apagado tampoco calza con R2, el problema es del hardware o del ruteo de R3.

## 7. Relevo de R3 con la falla inyectada (optativo)

`iceprog -b bitstreams/r3_c1_falla_multi.bin` y una ronda de 0,1 ms. El hilo 0 se cuelga a propósito en el tick 100, el vigilante dispara al quinto precio sin respuesta y la placa pasa a R0 con la banda 40. Es la misma prueba de la sección 5 de `docs/checklist_26nov.md` y se espera lo mismo que en R2 (unos 361 ticks sin decisión nueva a 0,1 ms). El vigilante de R3 es el mismo módulo de R2; lo que cambia es el ruteo, por eso vale repetirla si hay tiempo.

Se reconoce el relevo porque la telemetría desaparece: R0 no escribe los 7 segmentos, que quedan en `00`.

## 8. Plantilla

| Ronda | Período | Ticks | Patrimonio en pantalla | Byte bajo en la placa | Segundo byte (SW1) | Caja en la placa | Acciones | Modo | LED1 | Patrimonio de R2 en la misma ronda | ¿Calza? |
|-------|---------|-------|------------------------|-----------------------|--------------------|------------------|----------|------|------|------------------------------------|---------|
| 1 | 10 ms | | | | | | | | | | |
| 2 | 1 ms | | | | | | | | | | |
| 3 | 0,1 ms | | | | | | | | | | |

SCLK medido por el medidor (medida 1, ciclos de 40 ns y kHz): ________ y ________. Margen anotado si cae entre 150 y 250 kHz (medida 6 menos 916): ________

Hash grabado (lo que imprime `sha256sum bitstreams/r3_c1_multi.bin`): ________

## 9. Autoprueba de R3 en la placa (antes del día de prueba, sin maestra)

### 9.1 Qué es y qué prueba

`bitstreams/autoprueba_r3_multi.bin` es un bitstream aparte: **el de competencia (`r3_c1_multi.bin`) no se toca**. Adentro va el mismo SoC de R3 (mismo RTL, mismo `sw/c1.s`, misma tabla) con una maestra SPI interna que le manda 2000 precios y junta en una firma de 16 bits todos los bytes de decisión que lee. La firma esperada va dentro del bitstream y un LED dice si coincide.

Se reutilizó todo lo que existía para R0 a R2 (`docs/autoprueba.md`): el mismo top, la misma maestra, la misma caminata de precios (pasos de 4 entre 100 y 255) y el mismo testbench. Lo único nuevo es la configuración del peldaño en `tools/autoprueba.py`: la referencia es `ref/c1/c1.py`, el control negativo es la tabla con la política apagada y la falla es el hilo 0 colgado.

| | |
|---|---|
| Firma esperada | **`984c`**: "4C" en los 7 segmentos y "98" con SW4. Calculada con el gemelo a los tres períodos y con `ref/c1/c1.py`: los mismos 2000 bytes |
| Qué recorre C1 en esos 2000 precios | Ve el primer extremo en el tick 12, la tabla se activa en el 390, opera con el motor y llega al candado en el 578. Difiere de la banda 40 en 9 bytes |
| Si la placa decidiera la banda 40 | La firma sería `a639`, la de las autopruebas de R0, R1 y R2: LED4 con "39" |
| Costo | 1208 de 1280 celdas (R3 solo: 1038), 14 de 16 bloques de memoria, 50,55 MHz |
| Verificación | Por el RTL y por el bitstream ya ruteado, apretando los botones por los pines: `984c` a los tres períodos. Con la política apagada: `a639` y LED4. Media hora en el gemelo sin que el vigilante llegue a contar 5 (`docs/mediciones/autoprueba_r3.txt`) |

Qué **no** prueba:

- La apuesta de la fase A (la media posición). La caminata se mueve en todos los ticks, la volatilidad sale alta y la tabla nunca apuesta. Eso queda cubierto por la simulación y por la maestra.
- La conexión con una maestra externa ni los cables: los precios se generan dentro de la FPGA.
- La ubicación exacta del bitstream de competencia: es el mismo circuito, ruteado de nuevo junto con la maestra interna. Además aquí la telemetría de R3 no se ve (los 7 segmentos y los LED muestran la firma).

### 9.2 Comandos, uno por uno

Desde la raíz del repositorio, en WSL.

1. **Comprobar los archivos.**

   ```bash
   cd bitstreams && sha256sum -c SHA256SUMS && cd ..
   ```

   Calcula el hash de cada bitstream guardado y lo compara con el anotado. Todas las líneas tienen que decir `OK`, en particular `autoprueba_r3_multi.bin` (`062167ba...`) y `relevo_r3_multi.bin` (`beb964d4...`). No escribe nada.

2. **Pasar la placa a WSL**, si `iceprog` no la encuentra. En una PowerShell de Windows como administrador:

   ```
   usbipd list
   usbipd attach --wsl --busid X-Y
   ```

   El primero muestra los dispositivos USB: la Go Board aparece como un FTDI (0403:6010) con un número de bus `X-Y`. El segundo la entrega a WSL; hay que repetirlo cada vez que se reconecta el USB y se va a programar. En WSL, `lsusb` tiene que mostrar el FTDI.

3. **Grabar la autoprueba.**

   ```bash
   iceprog -b bitstreams/autoprueba_r3_multi.bin
   ```

   Escribe el archivo en la flash de la placa. El `-b` borra la flash entera antes: el archivo trae dos imágenes y ocupa más de 32 kB (sin `-b` la verificación falló el 18/11). Tiene que terminar con "VERIFY OK" y "cdone: high". La FPGA se configura sola al terminar: **los cuatro LED apagados y "FF"** en los 7 segmentos. Si aparecen los cuatro LED encendidos y "--", arrancó la imagen 1 (la testigo): volver a grabar.

4. **Ronda 3 (0,1 ms).** Apretar SW3 un instante. En 0,2 segundos: **LED2 y LED3 encendidos y "4C"**. Mantener SW4 apretado: **"98"**. Al soltar vuelve "4C". LED1 queda a media luz, porque la maestra sigue mandando precios.

5. **Ronda 2 (1 ms).** Desconectar y conectar el USB (la firma supone que el programa parte de cero). Apretar SW2. En 2 segundos, lo mismo: LED2, LED3, "4C", y "98" con SW4.

6. **Ronda 1 (10 ms).** Desconectar y conectar. Apretar SW1. LED1 parpadea unos 20 segundos (cambia cada 0,64 s) y después LED2, LED3, "4C" y "98".

7. **Media hora sin relevo (optativo).** Desconectar y conectar, anotar la hora, apretar SW3 y dejar la placa 30 minutos. Al final tiene que verse lo mismo: LED2 y LED3, LED1 a media luz, "4C". En ese tiempo la maestra mandó 18 millones de precios. A los 2 segundos R3 pasó los 20 000 ticks y entró a modo seguro: no cambia la firma, que quedó fija en el precio 2000, y es justamente el caso de una placa que sigue recibiendo precios sin reset. Si aparecen los cuatro LED encendidos y "--", el vigilante disparó sin falla: anotar los minutos que muestra con SW4.

8. **El relevo con la falla inyectada (optativo).**

   ```bash
   iceprog -b bitstreams/relevo_r3_multi.bin
   ```

   Es la misma autoprueba con el hilo 0 colgado a propósito en el precio 100. Al quedar configurada: LED apagados y "FF". Apretar SW3: a los 10 ms el vigilante pide el relevo y aparece la testigo, **los cuatro LED encendidos y "--"**. Si los 7 segmentos se apagan y no vuelven, grabar `relevo_r3_multi_sin_dormir.bin` y repetir (`docs/autoprueba.md`, sección 9.5).

9. **Volver al bitstream de competencia.**

   ```bash
   iceprog -b bitstreams/r3_c1_multi.bin
   ```

   La flash queda con la autoprueba hasta que se grabe otra cosa. Para R2, `iceprog -b bitstreams/r2_banda40_multi.bin`.

### 9.3 Qué anotar y cómo leerlo

Para cada período: los LED encendidos y los cuatro dígitos (sin y con SW4).

| Se ve | Qué significa | Qué hacer |
|-------|---------------|-----------|
| LED2 y LED3, "4C" y "98", en los tres períodos | Los 2000 bytes son los de la referencia: R3 pasa la autoprueba | Seguir |
| LED4 con "39" ("A6" con SW4) | Firma `a639`: la placa decidió la banda 40. La política no actuó: la tabla no se lee bien o un hilo no publica | Anotar el período. Si pasa en los tres, es una falla de R3 en la FPGA que la simulación no vio |
| LED4 con otros dígitos | Alguna decisión fue distinta o llegó tarde | Anotar los cuatro dígitos y el período. Si falla solo a 0,1 ms es de tiempo; si en los tres, de lógica o de memoria |
| Los cuatro LED encendidos y "--" sin haber grabado la falla | El vigilante disparó con el programa sano | Anotar la hora y los minutos con SW4 |
| Al configurar ya corre, o no pasa nada al apretar | Botones o configuración | Revisar "cdone: high" y probar otro botón |

## 10. Verificación con la serie de práctica Meta a 10 ms (si la maestra la permite)

Si la maestra deja correr la serie de práctica de Meta (`data/practica_meta.csv`) a 10 ms, es la mejor prueba de la apuesta de la fase A, que la autoprueba no ejercita (sección 9.1). La serie es la misma del testbench y R3 hace lo mismo en ella cada vez. Lo que tiene que pasar, calculado con `ref/c1/c1.py` (`make c1-series-reales`, `docs/mediciones/c1/series_reales.txt`, script `tools/c1/series_reales.py`):

| Orden | Tick | Precio | Qué hace R3 | Después, en la placa |
|-------|------|--------|-------------|----------------------|
| 1 | **8234** | **222** | **Compra 22 acciones en la fase A** (byte `0x56`): la media posición, caja 10 000 a 5 111 | SW4: `16` (22 acciones). SW3: `F7` y SW3 + SW1: `13` (5 111) |
| 2 | **10966** | 250 | Vende 63, recortada a las 22 que hay (modo candado) | SW4: `00`. SW3: `6E` y SW3 + SW1: `29` (10 606) |
| 3 y 4 | 17085 y 17086 | 100 y 101 | Compra 63, recortada a la caja | |
| 5 y 6 | 19084 y 19085 | 216 y 215 | Vende 63 | |
| Final | | | **Patrimonio 22 682**, 6 órdenes | Caja 22 682, acciones 0, modo `02`: byte bajo `9A`, SW1 `58` |

- El tick es la posición del precio en la serie contando desde 0 (el precio del tick 8234 es la fila 8234 del archivo sin el encabezado). A 10 ms cada tick dura 10 ms: la orden 1 cae unos 82,3 s después del primer precio y la orden 2 unos 109,7 s.
- La orden que ejecuta la maestra en el tick n es la que R3 decidió al ver el precio n-1.
- **Si la primera compra no ocurre en el tick 8234 al precio 222**, anotar el tick, el precio, las acciones y la caja: o la serie que corrió la maestra no es la de práctica (normalizada de otra forma, o con otro largo) o la apuesta de la fase A hace otra cosa en la placa que en la simulación. En los dos casos se anota y, por la regla de Nicolás, compite la banda 40.
- Esta prueba es solo para el ritmo de 10 ms: es el único donde da tiempo de leer la placa con la ronda corriendo (sección 4).
