# Autoprueba en placa

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Documento de estudio del paquete P6: un bitstream que prueba en la Go Board, sin la maestra del curso, que el SoC de cada peldaño decide lo mismo que su referencia. Es lo que pide la puerta de placa del plan (sección 16.4): "la firma de las decisiones que muestra la placa coincide con la calculada por el gemelo, en los tres períodos".

| Archivo | Qué es |
|---------|--------|
| `rtl/autoprueba/autoprueba_top.v` | El top: el SoC sin cambios, la maestra interna y los indicadores |
| `tb/autoprueba/tb_autoprueba.sv` | Testbench por los pines, para el RTL y para el bitstream ruteado |
| `tools/autoprueba.py` | Firma esperada, bitstream y simulaciones (`make autoprueba-r0`) |
| `docs/mediciones/autoprueba_r0.txt` | Resultado de R0 |
| `bitstreams/autoprueba_r0.bin` | El bitstream de R0, con su hash en `bitstreams/SHA256SUMS` |

## 1. Para qué sirve

La maestra real existe un solo día (26/11). Si ese día algo falla, hay que saber si el problema es nuestro diseño, la placa, los cables o la maestra. La autoprueba separa la primera parte antes de llegar: si la placa muestra la firma correcta a los tres períodos, el SoC, el programa y la FPGA funcionan, y lo que quede por probar el 26/11 es la conexión con la maestra.

No reemplaza a la prueba con la maestra: la autoprueba genera los precios dentro de la FPGA, con el mismo reloj, así que no prueba la sincronización con una maestra externa ni los cables del PMOD.

## 2. Qué hay adentro

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
- **Los precios**: una caminata aleatoria. Parte en 128 y en cada tick sube o baja 1 según el bit nuevo de un LFSR de 16 bits (x^16 + x^14 + x^13 + x^11 + 1, semilla 0xACE1), sin salir de 1 a 255. Con 2000 ticks va de 105 a 151 y `max_media` cambia de decisión 57 veces: se ejercita el algoritmo, no solo la comunicación.
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

Con un medio período de 16 ciclos, `t[4]` es el nivel de SCLK y `t[8:5]` el número de bit: no hace falta contador de fase ni de bit. SCLK queda en 781 kHz, dentro del rango de 100 kHz a 1 MHz que pide la puerta. La transacción dura 12,16 us (la del oficial, 9,5 us).

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

Para R0 las cuatro dan `a23c`. Que la firma sea la misma a los tres períodos es la prueba de que el programa responde siempre antes del tick siguiente: si una decisión llegara tarde, la maestra leería el byte anterior y la firma cambiaría.

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

Estos los corre Nicolás (el plan no permite que una sesión ejecute `iceprog`). Desde la raíz del repositorio, en WSL:

1. **Comprobar el archivo.** `cd bitstreams && sha256sum -c SHA256SUMS && cd ..`. Debe decir `autoprueba_r0.bin: OK`: es el bitstream que pasó todo lo de la sección 4, y su sha256 (`901c0eac...`) está también en `docs/mediciones/autoprueba_r0.txt`. Para reconstruirlo desde las fuentes: `make autoprueba-r0` (unos 20 minutos, la mitad es la simulación de 10 ms); deja `build/autoprueba/r0/autoprueba_r0.bin` con el mismo hash.
2. **Conectar la placa a WSL**, si `iceprog` no la encuentra. En una PowerShell de Windows como administrador: `usbipd list` muestra los dispositivos USB; la Go Board aparece como un FTDI (0403:6010). `usbipd bind --busid X-Y` la comparte (una sola vez), y `usbipd attach --wsl --busid X-Y` la pasa a WSL (cada vez que se conecta). En WSL, `lsusb` debe mostrar el FTDI.
3. **Programar.** `iceprog bitstreams/autoprueba_r0.bin`. Escribe la flash de la placa y la FPGA se configura sola al terminar. Debe terminar con "VERIFY OK" y "cdone: high". Al quedar configurada: los cuatro LED apagados y los 7 segmentos en "FF" (el valor inicial de la firma).
4. **Ronda 3 (0,1 ms).** Apretar SW3. En 0,2 s LED2 y LED3 quedan encendidos y los 7 segmentos muestran "3C". Con SW4 apretado deben mostrar "A2".
5. **Ronda 2 (1 ms).** Desconectar y conectar el USB (la FPGA se vuelve a configurar desde la flash; con usbipd hay que repetir el `attach` solo si se va a programar de nuevo). Apretar SW2. En 2 s, lo mismo: LED2 y LED3, "3C", y "A2" con SW4.
6. **Ronda 1 (10 ms).** Desconectar y conectar. Apretar SW1. LED1 parpadea unos 20 s (cambia cada 0,64 s) y después LED2 y LED3, "3C" y "A2".
7. **Volver al bitstream de competencia**, cuando se termine: `iceprog bitstreams/r0_base_max_media.bin`. La flash queda con la autoprueba hasta que se grabe otra cosa.

Qué anotar: para cada período, los LED encendidos y los cuatro dígitos (sin y con SW4). Con eso basta para cerrar la puerta de placa de R0.

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
| R1 | Barrel con `emad` y `devk`, `sw/fondo.s` con la tabla en BRAM | Espera a P5: la tabla en BRAM y la versión final del programa |
| R2 | R1 con el vigilante y la imagen múltiple | Espera a P5. La autoprueba tiene que probar también que el vigilante no dispara |

Para agregar un peldaño basta una línea en `PELDANOS` de `tools/autoprueba.py`: definiciones del RTL, programa, opciones del gemelo y referencia.

## 7. Preguntas

**¿Por qué una firma y no comparar byte por byte?** Porque en la placa solo hay dos dígitos y cuatro LED. Un CRC-16 de 2000 bytes detecta cualquier error de un bit, cualquier ráfaga de hasta 16 bits y el resto con probabilidad de 1 en 65 536.

**¿Por qué no se usan los tiempos exactos del oficial?** Porque 500 ns no son un número entero de ciclos de 40 ns, y porque la versión con contadores de fase no cabía junto a R0. La autoprueba no busca reproducir la maestra: la matriz de estrés ya cubre SCLK de 100 kHz a 1 MHz en simulación.

**¿Qué prueba y qué no?** Prueba que la FPGA configurada con nuestro SoC y nuestro programa toma las mismas 2000 decisiones que la referencia, a tiempo, en los tres períodos. No prueba la entrada asíncrona desde una maestra externa ni los cables: eso es el 26/11.

**¿No es trampa que la firma esperada esté dentro del bitstream?** No es la edición de competencia: es un bitstream de prueba, que no se lleva a la competencia. Y la firma también se muestra, así que se puede comparar a mano con la que da el gemelo.
