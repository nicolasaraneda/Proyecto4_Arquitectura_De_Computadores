# Autoprueba en placa

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Documento de estudio del paquete P6: un bitstream que prueba en la Go Board, sin la maestra del curso, que el SoC de cada peldaño decide lo mismo que su referencia. Es lo que pide la puerta de placa (`docs/puertas.md`, sección "Puerta de placa"): "la firma de las decisiones que muestra la placa coincide con la calculada por el gemelo, en los tres períodos".

| Archivo | Qué es |
|---------|--------|
| `rtl/autoprueba/autoprueba_top.v` | El top: el SoC sin cambios, la maestra interna y los indicadores |
| `rtl/autoprueba/testigo_top.v` | Imagen 1 de las pruebas de R2: lo que se ve si hubo relevo (sección 8) |
| `tb/autoprueba/tb_autoprueba.sv`, `tb_testigo.sv` | Testbenches por los pines, para el RTL y para el bitstream ruteado |
| `tools/autoprueba.py` | Firma esperada, bitstream y simulaciones (`make autoprueba-r0`, `-r1`, `-r2`) |
| `tools/medir_relevo.py` | Medición del tiempo del relevo en la placa por la UART (sección 10) |
| `docs/mediciones/autoprueba_r0.txt`, `_r1.txt`, `_r2.txt`, `relevo_placa.txt` | Resultados |
| `bitstreams/autoprueba_r0.bin`, `autoprueba_r1.bin`, `autoprueba_r2_multi.bin`, `relevo_r2_multi.bin` | Los bitstreams, con su hash en `bitstreams/SHA256SUMS` |

## 1. Para qué sirve

La maestra real existe un solo día (26/11). Si ese día algo falla, hay que saber si el problema es nuestro diseño, la placa, los cables o la maestra. La autoprueba separa la primera parte antes de llegar: si la placa muestra la firma correcta a los tres períodos, el SoC, el programa y la FPGA funcionan, y lo que quede por probar el 26/11 es la conexión con la maestra.

No reemplaza a la prueba con la maestra: la autoprueba genera los precios dentro de la FPGA, con el mismo reloj, así que no prueba la sincronización con una maestra externa ni los cables del PMOD.

## 2. Qué contiene

```
            Go Board
  +--------------------------------------------------------+
  |  SW1..SW3 --> +-------------------+   SCLK, MOSI, CS_n  |
  |               | autoprueba_maestra| ------------------> |
  |               |  LFSR -> precio   |                     |  pochoco_soc
  |               |  CRC-16 <- MISO   | <------------------ |  (el que compite,
  |               +-------------------+        MISO         |   sin cambios)
  |                  |  firma, listo                        |
  |   7 segmentos <--+--> LED1..LED4                        |
  +--------------------------------------------------------+
```

- **El SoC**: `pochoco_soc` tal cual, con el programa del peldaño. Sus salidas de LED y 7 segmentos quedan sin conectar, así que la síntesis elimina los registros que las manejan: la telemetría de `sw/fondo.s` no se ve en esta versión. Sus botones se leen en 0, como en el testbench.
- **La maestra interna** manda un precio por período y lee el byte de DECISION, con una transacción SPI modo 0 como la del testbench oficial.
- **Los precios**: un paseo aleatorio. Parte en 128 y en cada tick sube o baja 1 según el bit nuevo de un LFSR de 16 bits (x^16 + x^14 + x^13 + x^11 + 1, semilla 0xACE1 en R0 y 0x3CA1 en R1 y R2, sección 8), sin salir de 1 a 255. Con 2000 ticks y la semilla de R0 va de 105 a 151 y `max_media` cambia de decisión 57 veces: se ejercita el algoritmo, no solo la comunicación.
- **La firma**: CRC-16/CCITT (polinomio 0x1021, valor inicial 0xFFFF) de los 2000 bytes leídos por MISO, bit a bit en el orden en que llegan. Un solo bit distinto en cualquier byte cambia la firma.
- **La firma esperada** va dentro del bitstream como parámetro. Al terminar, un LED dice si coinciden.

### 2.1 La transacción

La maestra se diseñó para costar lo menos posible, porque R0 ocupa el 85 % de la FPGA. Un solo contador `t` de 9 bits, que parte en 0 al inicio de cada tick, arma la transacción entera:

| t (ciclos de 40 ns) | Qué pasa |
|---------------------|----------|
| 0 | Baja CS_n |
| 32 (i + 1), i = 0 a 7 | MOSI toma el bit 7 - i (y baja SCLK, salvo en el primero) |
| 32 (i + 1) + 16 | Sube SCLK y se lee MISO |
| 288 | Última bajada de SCLK |
| 304 | Sube CS_n |

Con un medio período de 16 ciclos, `t[4]` es el nivel de SCLK y `t[8:5]` el número de bit: no hace falta contador de fase ni de bit. SCLK queda en 781 kHz, dentro del rango de 100 kHz a 1 MHz que pide la puerta. La transacción dura 12,16 µs (la del oficial, 9,5 µs).

La primera versión copiaba los tiempos del oficial (SCLK de 1 MHz con medio período de 12,5 ciclos, redondeado a 13) con contadores de fase y bit y un CRC byte a byte: 233 LUT solo la maestra, y el total con R0 llegaba a 1340 celdas de 1280. La versión actual cuesta unas 186 celdas sobre R0 (sección 4).

### 2.2 Uso en la placa

| Control | Qué hace |
|---------|----------|
| SW1 | Parte con período de 10 ms (ronda 1). Dura 20 s |
| SW2 | Parte con período de 1 ms (ronda 2). Dura 2 s |
| SW3 | Parte con período de 0,1 ms (ronda 3). Dura 0,2 s |
| SW4 | Mientras se mantiene apretado, los 7 segmentos muestran el byte alto de la firma |
| LED1 | Parpadea mientras corre (cambia cada 64 precios) |
| LED2 | Terminó |
| LED3 | Terminó y la firma coincide con la esperada |
| LED4 | Terminó y la firma no coincide |
| 7 segmentos | Byte bajo de la firma en hexadecimal: parcial mientras corre, final al terminar |

Después de una corrida los botones de período no hacen nada. Para probar otro período hay que reiniciar la FPGA (desconectar y conectar el USB): el SoC solo se reinicia al configurarse, y la firma supone que el programa parte de cero.

## 3. De dónde sale la firma esperada

`tools/autoprueba.py firma` la calcula de dos formas independientes y exige que den lo mismo:

1. **Con el gemelo digital** (`docs/gemelo.md`), corriendo el mismo `.hex` con la misma serie y los tiempos de la maestra interna (`--cs-setup-ns 1280 --sclk-medio-ns 640 --cs-hold-ns 640`), a los tres períodos. El gemelo está validado ciclo a ciclo contra el RTL.
2. **Con la referencia del algoritmo** (`ref/trader.py` para R0, `ref/fondo.py` para R1 y R2), sin modelo de hardware.

Para R0 las cuatro dan `a23c`; para R1 y R2, con su paseo, `15d7` (sección 8). Que la firma sea la misma a los tres períodos es la prueba de que el programa responde siempre antes del tick siguiente: si una decisión llegara tarde, la maestra leería el byte anterior y la firma cambiaría.

## 4. Verificación y recursos

`make autoprueba-r0` (`docs/mediciones/autoprueba_r0.txt`):

| Prueba | Resultado |
|--------|-----------|
| Firma esperada | `a23c` en el gemelo a 10 ms, 1 ms y 0,1 ms y en `ref/trader.py`, bytes idénticos |
| RTL con SW3, SW2 y SW1 (Verilator, por los pines) | Firma `a23c` y LED2 y LED3 encendidos en los tres: 197 ms, 1 997 ms y 19 988 ms simulados |
| Bitstream ruteado con SW3 (icebox_vlog y Verilator) | Firma `a23c`, LED2 y LED3 |
| Control negativo | `sw/trade.s` con el umbral de la regla base (`-D UMBRAL_COMPRA=-128`): el gemelo predice `f8cf`, la autoprueba muestra `f8cf` y enciende LED4 |
| Recursos | 1269 de 1280 celdas (R0 solo: 1083), 12 de 16 BRAM, frecuencia máxima 44,05 MHz. Quedan 11 celdas |

El testbench hace lo que haría una persona: espera medio milisegundo, aprieta el botón 2 ms, espera a que se encienda LED2, lee los dos dígitos, aprieta SW4 y lee los otros dos. Solo mira pines, por eso sirve igual para el RTL y para el bitstream ruteado.

## 5. Comandos para la placa

Estos los corre Nicolás (la grabación de la placa la hace siempre él). Desde la raíz del repositorio, en WSL:

1. **Comprobar el archivo.** `cd bitstreams && sha256sum -c SHA256SUMS && cd ..`. Debe decir `autoprueba_r0.bin: OK`: es el bitstream que pasó todo lo de la sección 4, y su sha256 (`901c0eac...`) está también en `docs/mediciones/autoprueba_r0.txt`. `make autoprueba-r0` lo reconstruye desde las fuentes (unos 20 minutos), pero desde que P5 cambió `rtl/*.v` sale con la misma lógica en otra ubicación y otro hash, como le pasó a R0 de competencia (T62). Vale el archivo guardado.
2. **Conectar la placa a WSL**, si `iceprog` no la encuentra. En una PowerShell de Windows como administrador: `usbipd list` muestra los dispositivos USB; la Go Board aparece como un FTDI (0403:6010). `usbipd bind --busid X-Y` la comparte (una sola vez), y `usbipd attach --wsl --busid X-Y` la pasa a WSL (cada vez que se conecta). En WSL, `lsusb` debe mostrar el FTDI.
3. **Programar.** `iceprog bitstreams/autoprueba_r0.bin`. Escribe la flash de la placa y la FPGA se configura sola al terminar. Debe terminar con "VERIFY OK" y "cdone: high". Al quedar configurada: los cuatro LED apagados y los 7 segmentos en "FF" (el valor inicial de la firma).
4. **Ronda 3 (0,1 ms).** Apretar SW3. En 0,2 s LED2 y LED3 quedan encendidos y los 7 segmentos muestran "3C". Con SW4 apretado deben mostrar "A2".
5. **Ronda 2 (1 ms).** Desconectar y conectar el USB (la FPGA se vuelve a configurar desde la flash; con usbipd hay que repetir el `attach` solo si se va a programar de nuevo). Apretar SW2. En 2 s, lo mismo: LED2 y LED3, "3C", y "A2" con SW4.
6. **Ronda 1 (10 ms).** Desconectar y conectar. Apretar SW1. LED1 parpadea unos 20 s (cambia cada 0,64 s) y después LED2 y LED3, "3C" y "A2".
7. **Volver al bitstream de competencia**, cuando se termine: `iceprog bitstreams/r0_base_max_media.bin`. La flash queda con la autoprueba hasta que se grabe otra cosa.

Qué anotar: para cada período, los LED encendidos y los cuatro dígitos (sin y con SW4). Con eso basta para cerrar la puerta de placa de R0.

**Lo que falta de R0 (16/11).** Nicolás vio "3C" con LED2 y LED3 en los tres períodos, pero no apretó SW4. Falta eso: en cualquiera de los tres períodos, después de que se encienden LED2 y LED3, mantener SW4 apretado. **Los 7 segmentos deben mostrar "A2"** (la firma completa es `a23c`: "A2" es el byte alto y "3C" el bajo). Al soltar SW4 vuelve "3C". Si con SW4 se ve otra cosa, anotarla: el byte bajo coincidió, así que lo más probable es que SW4 no se lea o que los dígitos estén en otro orden, no que el SoC haya decidido distinto (LED3 ya dice que los 16 bits coinciden).

Si algo no sale así:

| Se ve | Qué significa | Qué hacer |
|-------|---------------|-----------|
| LED4 en vez de LED3 | La firma no coincide: alguna decisión fue distinta o llegó tarde | Anotar los cuatro dígitos y el período. Si falla solo a 0,1 ms es un problema de tiempo; si falla a los tres, de lógica o de la memoria del programa |
| Apenas se configura ya corre, sin apretar nada | Los botones se leen al revés de lo supuesto (apretado = 1) | Avisar: se invierte la lectura y se reconstruye |
| Nada se enciende al apretar | El botón no llega, o la FPGA no se configuró | Revisar que `iceprog` haya terminado con "cdone: high" y probar otro botón |
| Los dígitos no son hexadecimales | Los segmentos están en otro orden | Avisar con una foto |

## 6. Peldaños

| Peldaño | Hardware y programa | Estado |
|---------|---------------------|--------|
| R0 | Core base con `sw/trade.s` (`max_media`) | Construido y simulado (sección 4) |
| R1 | Barrel con `emad` y `devk`, `sw/fondo.s` con la tabla en BRAM | Construido y simulado (sección 8). Comandos en la sección 9 |
| R2 | R1 con el vigilante y la imagen múltiple | Construido y simulado, con la prueba de media hora y el relevo con una falla inyectada (secciones 8 y 9) |

Para agregar un peldaño basta una entrada en `PELDANOS` de `tools/autoprueba.py`: definiciones del RTL, programa, opciones del gemelo, referencia, tabla, semilla y modo continuo.

## 7. Preguntas

**¿Por qué una firma y no comparar byte por byte?** Porque en la placa solo hay dos dígitos y cuatro LED. Un CRC-16 de 2000 bytes detecta cualquier error de un bit, cualquier ráfaga de hasta 16 bits y el resto con probabilidad de 1 en 65 536.

**¿Por qué no se usan los tiempos exactos del oficial?** Porque 500 ns no son un número entero de ciclos de 40 ns, y porque la versión con contadores de fase no cabía junto a R0. La autoprueba no busca reproducir la maestra: la matriz de estrés ya cubre SCLK de 100 kHz a 1 MHz en simulación.

**¿Qué prueba y qué no?** Prueba que la FPGA configurada con nuestro SoC y nuestro programa toma las mismas 2000 decisiones que la referencia, a tiempo, en los tres períodos. No prueba la entrada asíncrona desde una maestra externa ni los cables: eso es el 26/11.

**¿No es trampa que la firma esperada esté dentro del bitstream?** No es la edición de competencia: es un bitstream de prueba, que no se lleva a la competencia. Y la firma también se muestra, así que se puede comparar a mano con la que da el gemelo.

## 8. R1 y R2

### 8.1 Qué cambia respecto de R0

El top y la maestra son los mismos. Todo lo nuevo son parámetros, con el valor de R0 por defecto:

| Parámetro o pieza | R0 | R1 | R2 | Para qué |
|-------------------|----|----|----|----------|
| Definiciones del SoC | ninguna | `-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA` | las de R1 y `-DESPINO_VIGILANTE` | El hardware del peldaño, como en `docs/tabla_vigilante.md` |
| Programa y tabla | `sw/trade.s` | `sw/fondo.s` y `sw/fondo_tabla.hex` | igual que R1 | `TablaFile` llega a la BRAM de la tabla |
| `SEMILLA` del LFSR | 0xACE1 | 0x3CA1 | 0x3CA1 | Con el paseo de R0 el fondo decide igual que `max_media` y no se vería un gestor colgado (T87) |
| `CONTINUO` | 0 | 0 | 1 | En R2 la maestra sigue mandando precios después de la firma, para la prueba de media hora (T90) |
| Eco de la UART y MISO del PMOD en 0 | sí | sí | sí | Para medir el relevo (sección 10). No usa lógica |

El paseo de 0x3CA1 va de 87 a 152. En ella el fondo cambia de decisión 44 veces y difiere de `max_media` en 51 ticks. Por eso la firma dice algo de los gestores:

| Lo que corre en la FPGA | Firma |
|-------------------------|-------|
| El fondo completo (lo esperado) | `15d7` |
| `max_media` sola, o el fondo con cualquiera de los tres gestores colgado | `7d4f` |
| El fondo con `G1_ENTRA` en -64 en la tabla (control negativo, T88) | `6f2a` |

Para R2 se arman además dos imágenes múltiples con `icemulti -p0`, revisadas con `tools/ver_multi.py`. En las dos la imagen 1 es la **testigo** (`rtl/autoprueba/testigo_top.v`, T89): los cuatro LED encendidos, "--" en los 7 segmentos y, con SW4 apretado, los minutos desde que arrancó (en decimal, hasta 99). No tiene SoC ni vigilante, así que no hay un segundo relevo.

| Archivo | Imagen 0 | Imagen 1 | Para qué |
|---------|----------|----------|----------|
| `autoprueba_r2_multi.bin` | Autoprueba de R2, `sw/fondo.s` sano, modo continuo | testigo | Puerta de placa (a) y (b): la firma y la media hora sin relevo |
| `relevo_r2_multi.bin` | Autoprueba de R2 con el supervisor colgado en el tick 100 (`cuelgue_sup:100` de `tools/fondo/variante.py`) | testigo | Puerta de placa (c): el relevo ocurre. Y la medición de su tiempo |
| `relevo_r2_multi_sin_dormir.bin` | Las mismas dos, empaquetadas con `icepack -s` | | Solo si el relevo no termina con el anterior (T91) |

La imagen con el supervisor colgado sale de la misma síntesis que la autoprueba de R2 con otro programa: el `.asc` es idéntico salvo el contenido de las BRAM.

### 8.2 Verificación

`make autoprueba-r1` y `make autoprueba-r2` (`docs/mediciones/autoprueba_r1.txt` y `autoprueba_r2.txt`):

| Prueba | R1 | R2 |
|--------|----|----|
| Firma esperada | `15d7` en el gemelo a 10 ms, 1 ms y 0,1 ms y en `ref/fondo.py`, bytes idénticos. Peor caso de respuesta 438 ciclos | Igual (el gemelo modela R1; el vigilante no cambia las decisiones) |
| RTL con SW3, SW2 y SW1 (Verilator, por los pines) | Firma `15d7` con LED2 y LED3 en los tres: 197, 1 997 y 19 988 ms simulados | Lo mismo, y después 2 s más en modo continuo: la firma no cambia, LED1 sigue cambiando (312, 31 y 3 veces) y `SB_WARMBOOT` no sube en ninguna de las tres corridas |
| Control negativo (otra tabla, T88) | `G1_ENTRA` en -64: el gemelo y `ref/fondo.py` dan `6f2a`, la autoprueba muestra `6f2a` y enciende LED4 | Igual |
| Supervisor colgado en el tick 100 | | Con SW3, SW2 y SW1, BOOT sube con S1 S0 = 01 al terminar la transacción 103 (la quinta sin respuesta, 99 + 4), 12 320 ns después del comienzo del tick: con CS_n ya en alto y lejos de la transacción siguiente. Es lo que predice `tools/vigilante/relevo_ref.py` |
| Bitstream ruteado (icebox_vlog y Verilator) | SW3: firma `15d7`, LED2 y LED3 | SW3: firma `15d7`, 2 s en modo continuo sin disparo. La imagen con la falla: BOOT en el mismo instante que el RTL. La testigo: LED, "--", "00" con SW4, eco y MISO |
| Testigo en RTL (minuto de 1000 ciclos) | | LED, "--", y con SW4 "00", "01", "02" y "99" al pasar 122 minutos (se detiene) |
| Media hora en el gemelo (T90) | | El paseo de la media hora completa: 180 000, 1 800 000 y 18 000 000 precios, entre 1 y 255 (toca los dos topes). Peor caso de respuesta 442 ciclos, con 2 196 disponibles a 0,1 ms: todo precio se responde antes del siguiente, así que la cuenta del vigilante no pasa de 1 |
| Imágenes múltiples | | `tools/ver_multi.py`: encendido y S1 S0 = 00, 10 y 11 apuntan a la imagen 0, 01 a la testigo; las dos copiadas sin cambios; 64 600 de 131 072 bytes |

### 8.3 Recursos

| Bitstream | Celdas | BRAM | Frecuencia máxima (semilla por defecto) |
|-----------|--------|------|------------------------------------------|
| Autoprueba de R0 (el guardado) | 1269 de 1280 | 12 | 44,05 MHz |
| Autoprueba de R1 | 1191 de 1280 | 13 | 50,81 MHz |
| Autoprueba de R2 (y la imagen con la falla, que tiene la misma ubicación) | 1203 de 1280 | 13 | 50,96 MHz |
| Testigo | 83 de 1280 | 0 | 141,92 MHz |

Cabe todo: no hubo que sacar nada de la autoprueba. R1 sin la autoprueba ocupa 1029 celdas y R2 1045 (`docs/tabla_vigilante.md`); la maestra, el CRC y los indicadores agregan 162 y 158. La regresión de R0 con el top nuevo da 1250 celdas y 47,12 MHz, con la firma `a23c` por el RTL y por el bitstream ruteado.

## 9. Comandos para la placa: R1 y R2

Los corre Nicolás. Desde la raíz del repositorio, en WSL, con la placa conectada como en la sección 5 (paso 2, `usbipd`). Cada vez que se desconecta y se conecta el USB, la FPGA se vuelve a configurar desde la flash con la imagen 0, y hay que repetir `usbipd attach` solo si se va a usar `iceprog` o la UART.

### 9.1 Comprobar los archivos

```bash
cd bitstreams && sha256sum -c SHA256SUMS && cd ..
```

Todas las líneas deben decir `OK`, en particular `autoprueba_r1.bin`, `autoprueba_r2_multi.bin`, `relevo_r2_multi.bin` y `relevo_r2_multi_sin_dormir.bin`. Los hashes están también en `docs/mediciones/autoprueba_r1.txt` y `autoprueba_r2.txt`.

### 9.2 R1: la firma a los tres períodos

1. **Programar.** `iceprog bitstreams/autoprueba_r1.bin`. Debe terminar con "VERIFY OK" y "cdone: high". Al quedar configurada: los cuatro LED apagados y "FF" en los 7 segmentos.
2. **Ronda 3 (0,1 ms).** Apretar SW3 un instante. En 0,2 s se encienden LED2 y LED3, y los 7 segmentos muestran **"D7"**. Mantener SW4 apretado: deben mostrar **"15"**. Al soltar vuelve "D7".
3. **Ronda 2 (1 ms).** Desconectar y conectar el USB. Apretar SW2. En 2 s, lo mismo: LED2 y LED3, "D7", y "15" con SW4.
4. **Ronda 1 (10 ms).** Desconectar y conectar. Apretar SW1. LED1 parpadea unos 20 s (cambia cada 0,64 s) y después LED2 y LED3, "D7" y "15".

Anotar en cada período los LED encendidos y los cuatro dígitos. Si los tres dan `15d7` con LED3, R1 pasa la puerta de placa.

### 9.3 R2: la firma y la media hora sin relevo

1. **Programar.** `iceprog -b bitstreams/autoprueba_r2_multi.bin`. El `-b` borra la flash entera antes de escribir: el archivo tiene dos imágenes y ocupa más de 32 kB, y si la flash borra en sectores de 32 kB el borrado por bloques de `iceprog` dejaría parte sin borrar (`docs/tabla_vigilante.md`, sección 6). Debe terminar con "VERIFY OK" y "cdone: high". Al quedar configurada: los cuatro LED apagados y "FF", igual que R1. Si en cambio se ven los cuatro LED encendidos y "--", arrancó la imagen 1: anotarlo y no seguir.
2. **(a) La firma.** Repetir los pasos 2 a 4 de R1 (SW3, SW2 y SW1, desconectando entre uno y otro). Se debe ver lo mismo: LED2 y LED3, "D7", y "15" con SW4. La diferencia es que LED1 no se apaga al terminar, porque la maestra sigue mandando precios: con SW3 parece encendido a media luz (cambia cada 6,4 ms) y con SW1 sigue parpadeando cada 0,64 s.
3. **(b) Media hora.** Desconectar y conectar. Anotar la hora. Apretar SW3. Comprobar que a los 0,2 s se ven LED2 y LED3 y "D7" (LED1 a media luz). Dejar la placa así 30 minutos sin tocarla. A la media hora debe verse exactamente lo mismo: LED2 y LED3 encendidos, LED1 a media luz, "D7", y "15" con SW4. En ese tiempo la maestra mandó 18 millones de precios y el vigilante los contó todos.
   - Si en algún momento se ven los cuatro LED encendidos y "--", el vigilante disparó en funcionamiento normal y **R2 no pasa la puerta**. Mantener SW4 apretado: muestra los minutos que lleva la testigo. El disparo ocurrió esa cantidad de minutos antes de mirar. Anotar los dos datos.

### 9.4 R2: el relevo con la falla inyectada

1. **Programar.** `iceprog -b bitstreams/relevo_r2_multi.bin`. "VERIFY OK", "cdone: high", y la placa queda con los LED apagados y "FF".
2. **(c) Inyectar la falla.** Apretar SW3. El supervisor se cuelga con el precio 100, el vigilante cuenta cinco precios sin respuesta y pide el relevo 10,3 ms después de apretar. Los 7 segmentos se apagan un instante (35,50 ms medidos el 16/11, casi no se nota) y aparece la testigo: **los cuatro LED encendidos y "--"**. Con SW4, "00" (cero minutos).
3. Desconectar y conectar, y repetir con SW1: ahora LED1 se enciende y alrededor de 1 s después (el precio 100 llega al segundo) aparece la testigo.

Si aparece la testigo, el relevo funciona en la placa: el vigilante dentro del bitstream disparó, `SB_WARMBOOT` cargó la imagen del vector 01 y esa imagen arrancó.

### 9.5 Si algo no sale así

| Se ve | Qué significa | Qué hacer |
|-------|---------------|-----------|
| R1 o R2: LED4 en vez de LED3, con "4F" ("7D" con SW4) | La firma es `7d4f`: la FPGA decidió como `max_media` sola. Los votos de los gestores no cuentan: algún gestor no vota, o la tabla no es la esperada | Anotar el período. Si pasa a los tres, avisar: es una falla del fondo en la FPGA que la simulación no vio |
| R1 o R2: LED4 con otros dígitos | Alguna decisión fue distinta o llegó tarde | Anotar los cuatro dígitos y el período. Si falla solo a 0,1 ms es de tiempo; si a los tres, de lógica o de memoria |
| R2 (9.3): la testigo (cuatro LED, "--") sin haber inyectado nada | El vigilante disparó con el programa sano | Anotar los minutos con SW4 y la hora. R2 no pasa la puerta; R1 sigue siendo candidato |
| R2 (9.3 o 9.4): al configurar ya aparece la testigo | La imagen 0 no cargó o el vector de encendido apunta mal | Volver a programar con `-b`; si se repite, avisar |
| 9.4: a los 0,2 s se encienden LED2 y LED4 y no aparece la testigo | El vigilante no disparó, o `SB_WARMBOOT` no hizo nada | Avisar. El vigilante dentro del bitstream sí disparó en la simulación desde el `.asc` |
| 9.4: los 7 segmentos se apagan y no vuelven | El relevo empezó pero la imagen 1 no terminó de cargar. Lo más probable es que la flash haya quedado dormida | Desconectar y conectar (vuelve "FF"), programar `iceprog -b bitstreams/relevo_r2_multi_sin_dormir.bin` y repetir 9.4. Si así funciona, avisar: `r2_multi.bin` de competencia hay que empaquetarlo con `icepack -s` |
| 9.4: los 7 segmentos se apagan y vuelve "FF" con los LED apagados | El relevo cargó la imagen 0 en vez de la 1 | Avisar: el vector 01 no es el que se usa |

### 9.6 Volver al bitstream de competencia

`iceprog bitstreams/r1_fondo.bin` para R1, o `iceprog -b bitstreams/r2_multi.bin` para R2 con R0 de respaldo. La flash queda con la autoprueba hasta que se grabe otra cosa.

## 10. Medir el tiempo del relevo

La hoja de datos da 53 ms típicos para configurar la HX1K desde la flash, sin máximo. **El 16/11 se midió por la UART: 35,50 ms** (35,42 a 35,59, una medición; `docs/mediciones/placa_16nov.md`). Faltan las otras dos mediciones del paso 4 de 10.1. Es lo que más pesa en cuántos ticks pierde R2 si dispara: el vigilante gasta 5 ticks y el reset de R0, 0,164 ms. La FPGA pierde todo su estado al reconfigurarse, así que la medición tiene que ser externa. `relevo_r2_multi.bin` está preparado para tres formas, de la más exacta a la más simple. Las tres miden lo mismo: el tiempo en que los pines quedan flotantes (en alta impedancia), desde que sube BOOT hasta que arranca la testigo (T92).

### 10.1 Por la UART (eco)

Las dos imágenes conectan el pin de recepción de la UART con el de transmisión. El script manda bytes sin pausa y cuenta los que no vuelven; a 115 200 baudios cada uno es 86,8 µs.

1. Programar `relevo_r2_multi.bin` (9.4, paso 1), o desconectar y conectar para partir de la imagen 0 si ya está programado.
2. `ls /dev/ttyUSB*`. La Go Board aparece como dos puertos: el segundo (normalmente `/dev/ttyUSB1`) es la UART. Si no aparece ninguno, falta `usbipd attach`.
3. `python3 tools/medir_relevo.py /dev/ttyUSB1 --segundos 20`. Cuando diga "Apriete SW3 una vez ahora", apretar SW3 una vez. A los 20 s imprime los huecos, la línea `RESULTADO: tiempo de reconfiguracion = ... ms` y la traducción a ticks de cada ronda. Copiar todo.
4. Repetir dos veces más desde el paso 1. Las tres deben dar casi lo mismo.

Si dice "Permission denied", el usuario no tiene permiso sobre el puerto (en Ubuntu se agrega al grupo `dialout`). Si la línea "Envio" da menos de 99 %, el computador dejó pausas y el resultado es un mínimo. Si no hay hueco, el relevo ocurrió antes de que partiera el script o no ocurrió.

### 10.2 Con la cámara

Filmar la placa en cámara lenta (240 cuadros por segundo) y apretar SW3. En el video: los 7 segmentos muestran dígitos (la firma parcial cambia muy rápido y se ve casi todo encendido), después **todo apagado** y después "--". Contar los cuadros completamente apagados: `tiempo ≈ cuadros × 4,17 ms`, con una resolución de unos 4 ms. Los LED pueden quedar con un brillo débil durante el relevo por el pull-up del pin; conviene mirar los 7 segmentos, que son activos en bajo y se apagan del todo.

### 10.3 Con un analizador lógico u osciloscopio

El pin de MISO del PMOD (pin 63 de la FPGA, el mismo que usa la maestra real) está en 0 en las dos imágenes. Durante el relevo queda flotante (en alta impedancia) y el pull-up interno lo sube: el ancho del pulso en alto es el tiempo buscado. Disparar con el flanco de subida y apretar SW3.

### 10.4 Qué hacer con el número

`python3 tools/medir_relevo.py --traducir 53` (con el valor medido en ms) lo traduce a ticks sin decisión nueva en cada ronda, con el mismo modelo que la simulación del relevo (`tools/vigilante/relevo_ref.py`). Con la hoja de datos (`docs/mediciones/relevo_placa.txt`):

| Tiempo de reconfiguración | Ronda 1 (10 ms) | Ronda 2 (1 ms) | Ronda 3 (0,1 ms) |
|---------------------------|-----------------|----------------|------------------|
| 35,2 ms (cota inferior: leer el bitstream a 7,5 MHz) | 8 | 40 | 358 |
| **35,50 ms (medido en la placa el 16/11)** | **8** | **40** | **361** |
| 53 ms (típico de la hoja de datos) | 10 | 58 | 536 |
| 106 ms (el doble) | 15 | 111 | 1066 |

La cuenta es: 5 ticks del vigilante, más el tiempo de reconfiguración y los 0,164 ms del reset de R0 divididos por el período, más el primer precio que R0 alcanza a responder. Durante la reconfiguración la maestra lee 0xFF, que es mantener. El número medido ya está en `tools/vigilante/relevo.sh` (`T_MEDIDO`, sección 2b de `docs/mediciones/vigilante/relevo.txt`: 361, 40 y 8 ticks, iguales a la traducción) y en el árbol de decisión del 1/12. Los casos con 53 ms se conservan como el escenario de la hoja de datos.

## 11. Banda 40 y la caminata entre 100 y 255 (19/11, T140 y T141)

### 11.1 Qué cambió

Con la regla de cotas la decisión depende de haber visto 100 y 255, y después de una banda junto a cada extremo. La caminata anterior (pasos de 1 desde 128) nunca llegaba a 255 en 2000 precios, así que la firma salía igual con cualquier banda y la autoprueba no distinguía el programa. Nicolás eligió la maestra normalizada (T141): la caminata sube o baja `PASO` por tick, sin pasar de 255 ni bajar de `PISO`, desde 128. El hardware de la maestra se cambió solo en eso (`rtl/autoprueba/autoprueba_top.v`, parámetros `PASO` y `PISO`); el SoC de cada peldaño es el mismo que compite.

| Constante (`tools/autoprueba.py`) | Valor | Para cambiarla |
|-----------------------------------|-------|----------------|
| `PASO` | 4 | Editar la constante, o `--paso N` |
| `PISO` | 100 | Editar la constante, o `--piso N` |
| `SEMILLA` | 0xE3AA | Editar la constante, o `--semilla S` |

Con estos valores la caminata toca 100 en el tick 11 y 255 en el 174, y la regla compra y vende 7 veces (patrimonio 26 395). Con otro paso o semilla, los productos quedan en `build/autoprueba/PELDANO_pasoN_sSEMILLA/` y en `docs/mediciones/autoprueba_PELDANO_pasoN_sSEMILLA.txt`, sin pisar los de competencia. Con pasos más chicos la caminata puede no llegar a los dos extremos (con paso 2 y esta semilla llega solo a 198): el informe de la firma lo avisa con un AVISO, y en ese caso hay que buscar otra semilla.

### 11.2 Firma esperada y verificación

| | R0 | R1 | R2 |
|---|----|----|----|
| Firma esperada (gemelo a los tres períodos y referencia) | `a639` | `a639` | `a639` |
| Con la banda 60 (control negativo) | `8610`, rechazada con LED4 | `8610` (tabla con 161 y 195), rechazada | Igual que R1 |
| RTL por los pines, SW3, SW2 y SW1 | `a639`, LED2 y LED3 | Igual | Igual, más 2 s en modo continuo sin disparo |
| Bitstream ruteado, SW3 | `a639` | `a639` | `a639`; la imagen con el supervisor colgado pide el relevo en la transacción 103 |
| Peor caso de respuesta | 60 ciclos | 126 | 126; media hora en el gemelo a los tres períodos sin que el vigilante llegue a 5 |
| Celdas | 1267 de 1280 | 1188 | 1199 (testigo: 83) |
| Frecuencia máxima | 45,14 MHz | 52,00 MHz | 52,00 MHz |

La autoprueba de R0 sigue cabiendo con la telemetría: quedan 13 celdas. Resultados completos en `docs/mediciones/autoprueba_r0.txt`, `_r1.txt` y `_r2.txt` (`make autoprueba-r0`, `-r1`, `-r2`).

| Archivo | sha256 |
|---------|--------|
| `autoprueba_r0.bin` | `b0a4ebcc4c30ed76a46eb61d0857e22fdcaf7c7b305ea22e7665e17cdcf90070` |
| `autoprueba_r1.bin` | `7478606482a119d69f3f3317604d109716509a0e43a454b55f608e5e1a88d73d` |
| `autoprueba_r2_multi.bin` | `bd5b7278a3a3eb0ca7bd6d7471d95261e01fb164b81ea2bf09b9e3bde8656b98` |
| `relevo_r2_multi.bin` | `bafb50392f8b2f83a70be80e06b917d95287a3690ecee8cf4c5a7e760a08cd36` |
| `relevo_r2_multi_sin_dormir.bin` | `91a94e4efad287dd605bdbfcaf41821ebbbfc489e9b6a572ab5821ce5fd6677d` |

### 11.3 Comandos para la placa

Los mismos pasos de las secciones 5 y 9, con otros dígitos. En los tres peldaños, al terminar cada corrida: **LED2 y LED3 encendidos, "39" en los 7 segmentos y "A6" con SW4 apretado**. Al configurarse, antes de apretar nada: los cuatro LED apagados y "FF".

1. `cd bitstreams && sha256sum -c SHA256SUMS && cd ..`: todas las líneas en `OK`.
2. R0: `iceprog bitstreams/autoprueba_r0.bin`; SW3 (0,2 s), desconectar y conectar el USB, SW2 (2 s), desconectar y conectar, SW1 (20 s, LED1 parpadea cada 0,64 s). En los tres, LED2, LED3, "39" y "A6".
3. R1: `iceprog bitstreams/autoprueba_r1.bin` y lo mismo.
4. R2: `iceprog -b bitstreams/autoprueba_r2_multi.bin` y lo mismo; LED1 no se apaga al terminar, porque la maestra sigue mandando precios. Después, media hora con SW3 como en 9.3: a la media hora, lo mismo y sin la testigo.
5. Relevo: `iceprog -b bitstreams/relevo_r2_multi.bin` y SW3: a los pocos milisegundos, los cuatro LED encendidos y "--" (9.4).
6. Volver a competencia: `iceprog bitstreams/r1_banda40.bin`, o `iceprog -b bitstreams/r2_banda40_multi.bin`, o `iceprog bitstreams/r0_banda40.bin`.

| Se ve | Qué significa |
|-------|---------------|
| LED4 con "10" ("86" con SW4) | Firma `8610`: la placa corre un programa con la banda 60 (161 y 195) en vez de la banda 40 |
| LED4 con otros dígitos | Alguna decisión fue distinta o llegó tarde: anotar los cuatro dígitos y el período, y seguir la tabla de 9.5 |
| LED2 y LED3 con "D7" o "3C" | Se grabó una autoprueba anterior al 19/11 (firmas `15d7` y `a23c` con la caminata vieja); comprobar el `sha256sum` |
