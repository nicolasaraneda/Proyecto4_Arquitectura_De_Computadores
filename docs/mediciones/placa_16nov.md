# Pruebas en la placa del 16/11

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Las corrió Nicolás en la Go Board, siguiendo `docs/autoprueba.md`, secciones 9 y 10. Este archivo copia lo que informó, sin interpretar. La interpretación y lo que falta están en `docs/puertas.md` (sección "Puerta de placa") y en `docs/pendientes_nicolas.md`.

## Lo que se vio

| Prueba | Bitstream | Lo esperado (`docs/autoprueba.md`) | Lo que se vio | Resultado |
|--------|-----------|------------------------------------|---------------|-----------|
| R1, firma a 0,1 ms, 1 ms y 10 ms | `autoprueba_r1.bin` | LED2 y LED3, "D7"; "15" con SW4 | No se corrió | Pendiente |
| R2, firma a 0,1 ms (SW3) | `autoprueba_r2_multi.bin` | LED2 y LED3, LED1 a media luz (la maestra sigue), "D7" | "D7" con LED 1 a 3 encendidos y LED4 apagado | **PASS** |
| R2, firma a 1 ms (SW2) y 10 ms (SW1) | `autoprueba_r2_multi.bin` | Lo mismo | No se corrieron | Pendiente |
| R2, media hora sin tocar (SW3) | `autoprueba_r2_multi.bin` | Al final lo mismo que al comienzo; los cuatro LED y "--" significarían disparo | Al final seguía igual: "D7" con LED 1 a 3, y "15" con SW4. Sin disparo del vigilante | **PASS** |
| R2, relevo con la falla inyectada, a la vista | `relevo_r2_multi.bin` | Los cuatro LED y "--" (la imagen testigo) | No se anotó: solo se hizo la medición por la UART | Pendiente |
| R2, tiempo del relevo por la UART | `relevo_r2_multi.bin` | Entre 35,2 ms (cota inferior) y 53 ms (típico de la hoja de datos) | **35,50 ms** (entre 35,42 y 35,59). Una sola medición | Medido |
| R1 de competencia sin maestra | `r1_fondo.bin` | "00" y los cuatro LED apagados (ver abajo) | "00". Los LED no se anotaron | Pendiente |
| R0, mitad alta de la firma (SW4) | `autoprueba_r0.bin` | "A2" | No se informó (antes se vio "3C" con LED2 y LED3 a los tres períodos, sin SW4) | Pendiente |

## El tiempo del relevo

`python3 tools/medir_relevo.py /dev/ttyUSB1 --segundos 20`, una corrida. El intervalo de 35,42 a 35,59 ms es la resolución del método: un byte de eco a 115 200 baudios son 0,087 ms.

Traducción a ticks con el modelo de la simulación del relevo (`python3 tools/medir_relevo.py --traducir 35.50`):

| Ronda | Ticks sin decisión nueva | De ellos leyendo 0xFF (mantener) | Con los 53 ms de la hoja de datos |
|-------|--------------------------|----------------------------------|-----------------------------------|
| 1 (10 ms) | 8 | 3 | 10 |
| 2 (1 ms) | 40 | 35 | 58 |
| 3 (0,1 ms) | 361 | 355 | 536 |

Con los extremos del intervalo, la ronda 3 da 360 y 362; las rondas 1 y 2 no cambian.

El valor medido queda a 0,3 ms de la cota inferior calculada en `docs/mediciones/relevo_placa.txt` (leer los 257 760 bits del bitstream a 7,5 MHz más el borrado, 35,17 ms). Es coherente: la hoja de datos da 53 ms como valor típico y sin máximo, y la placa lee la flash más rápido que eso.

## Lo que debe mostrar `r1_fondo.bin` sin maestra

Sin maestra no llega ningún precio, así que el programa queda esperando el primero y nunca hace el store de telemetría. Lo que se ve son los valores de reset del periférico (`rtl/pochoco_periph.v`, líneas 33 a 36): `digit_q = 0`, que se muestra como "00", y `led_q = 0`, **los cuatro LED apagados**.

"00" es lo esperado. Si algún LED estaba encendido o parpadeaba, el SoC recibió transacciones que nadie mandó: los pines del SPI no tienen pull-up (`goboard.pcf` y `rtl/pochoco_soc.v` no lo piden) y, con los cables sueltos, pueden captar ruido. No sería una falla del diseño, pero el programa partiría la ronda con una media formada por precios falsos. La regla que lo evita está en `docs/checklist_26nov.md` y `docs/checklist_1dic.md`: conectar la maestra y después desconectar y conectar el USB, para que la FPGA parta de cero con las líneas ya conducidas.
