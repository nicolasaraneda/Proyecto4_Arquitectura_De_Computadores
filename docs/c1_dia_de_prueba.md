# R3 (C1) el día de prueba con la maestra: pasos

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Complementa `docs/checklist_26nov.md` (conexión, medidor, registrador y peldaños R0 a R2), que no cambia. Aquí está solo lo de R3: en qué orden se carga, cómo se lee en la placa la cuenta que R3 emula y contra qué se compara. La regla del día la fijó Nicolás (21/11): **si la caja o el patrimonio no calzan con la pantalla de la maestra, se anota la diferencia y compite la banda 40**. Este documento no decide qué peldaño compite.

## 1. Qué se lleva de R3

`cd bitstreams && sha256sum -c SHA256SUMS && cd ..` tiene que dar `OK` en todas las líneas. Los hash completos están en `bitstreams/SHA256SUMS` y en `docs/puertas.md`.

| Archivo | Para qué |
|---------|----------|
| `r2_banda40_multi.bin` | R2, la banda 40. Va primero: es el respaldo y la vara de comparación |
| `r3_c1_multi.bin` | R3: imagen 0 C1, imagen 1 R0 con la banda 40 |
| `r3_c1_apagada_multi.bin` | R3 con la política apagada en la tabla: el hardware de R3 decidiendo la banda 40. Sirve para separar un problema del hardware nuevo de un problema de la política |
| `r3_c1_falla_multi.bin` | R3 con el hilo 0 colgado en el tick 100 y R0 de respaldo: el relevo del vigilante en el ruteo de R3 |

Las cuatro son imágenes múltiples: se graban con `iceprog -b` (borra la flash entera; sin `-b` la verificación falló el 18/11).

## 2. Orden de carga

1. **R2 primero.** `iceprog -b bitstreams/r2_banda40_multi.bin`. Las rondas que dé la maestra, como en la sección 4 de `docs/checklist_26nov.md`. Anotar el patrimonio (y la caja, si la muestra) de cada ronda. Con eso la banda 40 queda probada antes de tocar nada nuevo.
2. **R3 después.** `iceprog -b bitstreams/r3_c1_multi.bin`. Las mismas rondas, leyendo la placa al final de cada una (secciones 3 y 4).
3. Si queda tiempo: `r3_c1_apagada_multi.bin` (sección 6) y `r3_c1_falla_multi.bin` (sección 7).

**Antes de cada ronda de R3, desconectar y conectar el USB de la Go Board**, con los cables del PMOD puestos y la maestra encendida. Para R2 basta hacerlo antes de la primera ronda; para R3 hace falta en todas, por dos razones:

- C1 supone una ronda de 20 000 ticks contada desde el encendido: el reloj de tramos, el modo (el candado no tiene vuelta) y las dos cuentas emuladas parten de cero solo con el reset.
- Pasado el tick 20 000 sin reset, R3 entra a modo seguro (LED1 encendido) y desde ahí decide la banda 40 sin política. No falla, pero ya no es C1 lo que se está probando.

Si la maestra no deja reiniciar entre rondas, se anota: en la primera ronda corre C1 y en las siguientes la banda 40.

## 3. Qué muestra la placa

R3 lleva dentro una copia de la contabilidad oficial (caja 10 000, comisión 5): la cuenta propia y la de un clon que opera la banda 40. Los 7 segmentos muestran **un byte en hexadecimal** de esas cuentas, y los cuatro botones eligen cuál. Hay que mantenerlos apretados mientras se lee.

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

- **LED1**: modo seguro. Apagado es lo normal. Encendido significa que R3 dejó la política y decide la banda 40: precio bajo 100, más de 20 000 ticks sin reset, o un hilo que no publicó a tiempo dos ticks seguidos.
- LED2 a LED4 no se usan: apagados.
- El patrimonio emulado es caja más acciones por el último precio recibido. Cambia en cada tick durante la ronda; cuando la maestra deja de mandar precios queda fijo y se puede leer con calma.
- Para pasar a decimal: patrimonio = tercer byte x 65 536 + segundo x 256 + byte bajo. Por ejemplo `58` y `9A` son 0x589A = 22 682 (`python3 -c "print(0x589A)"`).

Comprobación rápida al partir: antes del primer precio los 7 segmentos muestran `00`. Apenas llega el primero muestran `10`, y con SW1 `27`: 0x2710 son los 10 000 iniciales. Si no se ve eso, R3 no está recibiendo precios.

## 4. Qué se anota y qué se compara, por ronda

Al terminar cada ronda de R3, con la placa quieta:

| Dato | Cómo se lee | Contra qué se compara |
|------|-------------|-----------------------|
| Patrimonio emulado | Sin botones, SW1 y SW2 | **El patrimonio de nuestro grupo en la pantalla de la maestra. Tiene que ser igual, peso por peso** |
| Caja emulada | SW3, SW3 + SW1, SW3 + SW2 | La caja que muestre la maestra, si la muestra. Si solo muestra patrimonio, sirve igual para saber si quedó con acciones |
| Acciones | SW4, SW4 + SW1 | Las acciones que muestre la maestra, si las muestra |
| Modo | SW1 + SW2 | Se anota. `02` es candado: desde ahí R3 copia a la banda 40 |
| LED1 | A la vista | Tiene que estar apagado |
| Caja del clon | SW4 + SW3 y sus bytes | El patrimonio que la maestra le dio a R2 en la misma ronda, si la serie es la misma y el clon terminó sin acciones |
| Patrimonio de R3 en la pantalla | Pantalla | El de R2 en la misma ronda. Se anota la diferencia, a favor o en contra |

Qué dice cada resultado:

- **Patrimonio emulado igual al de la pantalla**: la copia de la contabilidad que lleva R3 es la de la maestra. Es la condición para que C1 funcione como se midió, porque el candado se decide con esa cuenta.
- **Distinto**: se anota la diferencia exacta, la ronda, el modo y la caja. Según la regla de Nicolás, compite la banda 40. Causas posibles, para revisar esa noche con la serie registrada: comisión o caja inicial distintas de 5 y 10 000, una regla de recorte distinta a la del testbench, o un precio que la placa no vio.
- **LED1 encendido** sin haber pasado de 20 000 ticks ni haber visto un precio bajo 100: un hilo se atrasó o se colgó. Se anota en qué ronda. La decisión siguió saliendo (banda 40), pero es un hallazgo.

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
- Los 7 segmentos siguen mostrando la cuenta emulada: tiene que calzar con la pantalla igual que en la sección 4.

Si R3 apagado calza con R2 y R3 con la política no calza con su cuenta, el problema está en la política o en la contabilidad emulada y no en el hardware nuevo. Si R3 apagado tampoco calza con R2, el problema es del hardware o del ruteo de R3.

## 7. Relevo de R3 con la falla inyectada (optativo)

`iceprog -b bitstreams/r3_c1_falla_multi.bin` y una ronda de 0,1 ms. El hilo 0 se cuelga a propósito en el tick 100, el vigilante dispara al quinto precio sin respuesta y la placa pasa a R0 con la banda 40. Es la misma prueba de la sección 5 de `docs/checklist_26nov.md` y se espera lo mismo que en R2 (unos 361 ticks sin decisión nueva a 0,1 ms). El vigilante de R3 es el mismo módulo de R2; lo que cambia es el ruteo, por eso vale repetirla si hay tiempo.

Se reconoce el relevo porque la telemetría desaparece: R0 no escribe los 7 segmentos, que quedan en `00`.

## 8. Plantilla

| Ronda | Período | Ticks | Patrimonio en pantalla | Patrimonio en la placa (hex y decimal) | Caja en la placa | Acciones | Modo | LED1 | Patrimonio de R2 en la misma ronda | ¿Calza? |
|-------|---------|-------|------------------------|-----------------------------------------|------------------|----------|------|------|------------------------------------|---------|
| 1 | 10 ms | | | | | | | | | |
| 2 | 1 ms | | | | | | | | | |
| 3 | 0,1 ms | | | | | | | | | |

Hash grabado (lo que imprime `sha256sum bitstreams/r3_c1_multi.bin`): ________
