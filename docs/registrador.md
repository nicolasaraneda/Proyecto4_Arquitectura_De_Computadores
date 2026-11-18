# Registrador de la maestra

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Herramienta para la prueba con la maestra real del 26/11. Es un bitstream aparte que escucha el SPI de la maestra y manda cada precio por la UART al computador, donde `tools/registrador.py` lo guarda como CSV. **No es parte del diseño de competencia y no guarda ninguna serie**: no tiene memoria para eso y no hay nada en el hardware de R0, R1 ni R2 que cambie. La serie queda en el computador, como cualquier otra medición.

| Archivo | Qué es |
|---------|--------|
| `rtl/registrador/registrador.v` | El núcleo (`registrador`) y el bitstream (`registrador_top`) |
| `tb/registrador/tb_registrador.sv` | Testbench: maestra SPI, receptor UART y comparación |
| `tools/registrador.sh` | Testbench, controles negativos, timing en 10 semillas, bitstream y simulación del bitstream ruteado (`make registrador`) |
| `tools/registrador.py` | Lee el puerto y escribe los CSV (con el período medido por la FPGA y la hora de llegada al computador) y los bytes crudos a medida que llegan; `--convertir` arma los CSV desde una captura en bruto; `--prueba` sin placa. Funciona en Linux, Mac y Windows con pyserial, y en Linux también sin él (sección 4b) |
| `bitstreams/registrador.bin` | El bitstream (sha256 `231a0c6d...`, también en `bitstreams/SHA256SUMS`) |
| `docs/mediciones/registrador.txt` | Resultado de `make registrador` |

## 1. Para qué sirve

1. **La puerta de maestra pide comparar el patrimonio que muestra la maestra con el que predice el gemelo "para la misma serie, si la serie es conocida"** (`docs/puertas.md` y decisión T50). Si la maestra del 26/11 usa una serie que no conocemos, el registrador la hace conocida: con el CSV, `build/gemelo --serie` y `ref/fondo.py` dan el patrimonio que R0, R1 y R2 deberían obtener, y se compara con la pantalla.
2. Mide además el período real entre precios, tick por tick, y marca las transacciones que no tuvieron 8 bits. Complementa al medidor del SPI (`docs/checklist_26nov.md`, sección 3), que da mínimos y máximos pero no la serie.

## 2. Cómo funciona

```
maestra --SCLK, MOSI, CS_n--> sincronizadores --> registro de desplazamiento --> cola de 4 --> UART 1 Mbaud --> computador
         <--MISO = 0 (mantener)--
```

- **Muestreo**, igual que el esclavo SPI del SoC (`rtl/pochoco_spi_slave.v`): tres flip-flops en cada línea, flanco de subida de SCLK con `CS_n` en bajo, el primer bit es el más significativo. La transacción termina cuando `CS_n` sube.
- **MISO** queda en 0: la maestra lee `0x00`, que es mantener. Aun así se registra lo que se leyó por MISO, para poder usar el mismo núcleo junto a un SoC.
- **Registro de 5 bytes por transacción.** El primer byte tiene el bit 7 en 1 y los otros en 0, así el computador se puede sincronizar aunque empiece a leer a mitad de un registro.

  | Byte | Contenido |
  |------|-----------|
  | b0 | `1`, secuencia de 7 bits (módulo 128) |
  | b1 | `0`, precio[7:1] |
  | b2 | `0`, MISO[7:1] |
  | b3 | `0`, precio[0], MISO[0], error (no fueron 8 bits), período[10:7] |
  | b4 | `0`, período[6:0] |

  En una captura en bruto: **precio = 2 × b1 + bit 6 de b3**; MISO = 2 × b2 + bit 5 de b3; error = bit 4 de b3; **período = 128 × (b3 & 0x0F) + b4**. El período no incluye a b2 ni a los bits 4 a 6 de b3: una fórmula como `(b2 << 14) | ((b3 & 0x3F) << 7) | b4` da el valor correcto con el registrador solo porque su MISO es siempre 0 y no hubo errores, y se equivoca en cuanto MISO tenga un 1 o una transacción venga incompleta.

  El período es el tiempo desde la bajada de `CS_n` de la transacción anterior, en unidades de 128 ciclos (5,12 µs), redondeado hacia abajo y saturado en 2047 (10,48 ms). A 10 ms da 1953.
- **UART a 1 Mbaud** (25 ciclos por bit, sin error de reloj). Un registro tarda 50 µs. A 0,1 ms la UART está ocupada la mitad del tiempo; la cola de 4 registros absorbe cualquier irregularidad.
- **Si la cola se llena** (precios cada menos de 50 µs, sostenidos), el registro nuevo se descarta, LED4 queda encendido y la secuencia salta: la pérdida siempre se ve en el CSV.
- **En la placa**: los 7 segmentos muestran la cuenta de registros (byte bajo; con SW4, el alto). SW3 borra la cuenta y la secuencia. LED1 cambia con cada registro, LED2 se enciende si la UART está transmitiendo, LED3 si hubo una transacción con error y LED4 si se perdió un registro.

## 3. Verificación

`make registrador` (`docs/mediciones/registrador.txt`):

| Prueba | Resultado |
|--------|-----------|
| Ronda 3: 0,1 ms, SCLK 1 MHz, 2000 precios de la práctica (34 comprobaciones en total en el testbench) | 2000 registros, ninguno perdido, precio, secuencia y período (19 unidades) exactos |
| Ronda 2: 1 ms con SCLK de 100 kHz, 200 precios | Igual, período 195 |
| Ronda 1: 10 ms, 12 precios | Igual, período 1953 |
| Una transacción de 7 bits | Ese registro con la marca de error, LED3 encendido, los demás intactos |
| 60 µs entre precios, 1000 precios | Ninguno perdido |
| Control: 30 µs entre precios | Se pierden registros, la secuencia lo muestra, los que llegan están intactos y LED4 se enciende |
| Controles negativos (errores puestos a propósito) | 7 de 7 detectados |
| Timing | 10 de 10 semillas a 25 MHz: 478 celdas, ninguna BRAM, mínima 118,40 MHz |
| Ronda 3 entera con la serie Meta (`data/practica_meta.csv`): 20 000 precios a 0,1 ms | 20 000 registros, ninguno perdido; la herramienta arma con esos bytes un CSV idéntico byte a byte al archivo |
| Bitstream ruteado, simulado por los pines | Los mismos casos en versión corta: 28 comprobaciones sin fallas |
| Variante de 926 kbaud, bitstream ruteado por los pines | 28 comprobaciones sin fallas |
| `tools/registrador.py --prueba` | Los bytes del testbench dan la serie de práctica exacta; pérdida, basura, byte dañado y borrado con SW3 se detectan; de punta a punta por un pseudoterminal a 1 Mbaud |

**Un error encontrado por los controles negativos.** La primera versión comparaba `esc - lec` (punteros de 3 bits) con un entero: Verilog hace esa resta en 32 bits y, cuando los punteros dan la vuelta, la cola llena no se veía y un registro nuevo sobrescribía al que se estaba transmitiendo. A 0,1 ms no ocurre (la cola nunca pasa de un registro), pero a 30 µs aparecían registros con la secuencia de uno y el precio de otro. El control negativo que debía demostrar que la secuencia delata las pérdidas no falló, y eso llevó al error. Se corrigió guardando la resta en 3 bits, se agregó al testbench la comprobación de que cada registro que llega tiene el precio de su transacción, y la versión antigua quedó como control negativo (`cola_llena_en_32_bits`).

## 4. Uso el 26/11

Paso a paso, con usbipd, en `docs/clase_18nov.md` (la clase con la maestra) y en `docs/checklist_26nov.md`, sección 4b. En resumen:

1. `iceprog bitstreams/registrador.bin`. Los 7 segmentos muestran `00` y los LED quedan apagados.
2. Conectar la maestra (PMOD, como en la sección 2 del checklist) y el USB. Desconectar y conectar el USB para que parta de cero.
3. `ls /dev/ttyUSB*` y, antes de que la maestra empiece la ronda, `python3 tools/registrador.py /dev/ttyUSB1 -o build/maestra/ronda3`.
4. Correr la ronda. Al terminar, Ctrl+C. El programa imprime registros, perdidos, errores y el período. Comprobar que los 7 segmentos muestran la cuenta que el programa dice.
5. Apretar SW3 antes de la ronda siguiente y repetir con otro prefijo.

La maestra ve a nuestro grupo manteniendo durante toda la ronda (`0x00`). Si la maestra solo admite un bitstream por ronda, esta prueba va después de las de los peldaños.

## 4b. En Mac o Windows, y captura en bruto

- **Puerto serie.** Con pyserial (`python3 -m pip install pyserial`) la herramienta abre el puerto en Linux, Mac y Windows; sin pyserial usa `termios` de la biblioteca estándar, que solo sirve en Linux y WSL. La versión del 17/11 no partía en Mac: el `termios` de Mac no trae las constantes de 921 600 ni de 1 000 000 baudios y el programa las pedía al cargarse. `--puerto-con pyserial` o `termios` fuerza una de las dos; si se pide `termios` en un sistema sin esas constantes, dice que instale pyserial.
- **Nombre del puerto.** `python3 tools/registrador.py --listar` (con pyserial). La Go Board tiene dos interfaces y la UART es la segunda: `/dev/ttyUSB1` en Linux, la terminada en 1 en Mac (por ejemplo `/dev/cu.usbserial-1201`), un `COM` en Windows.
- **Captura en bruto.** Si los bytes se guardaron con otro programa (por ejemplo `captura.py` del kit del 18/11), `python3 tools/registrador.py --convertir captura.bin` escribe `captura_serie.csv` y `captura_detalle.csv` junto a la captura (o con `-o PREFIJO`) e imprime el mismo resumen: registros, perdidos, errores y período. No necesita pyserial ni la placa. Con la captura de la ronda de Tesla del 18/11 da 20 000 registros sin pérdidas y un CSV idéntico al decodificado a mano (`docs/mediciones/clase_18nov.md`).
- **Prueba sin placa.** `--prueba` agrega la conversión de una captura en bruto y prueba el puerto con pyserial si está instalado (si no, con `termios`). En WSL no hay pyserial: el camino de pyserial se probó con un módulo `serial` de imitación sobre un pseudoterminal y con un `termios` sin las constantes de Mac (`docs/bitacora/minutos_reales.md`), no con pyserial real. En el Mac, correr `--prueba` una vez antes de usarlo.

## 5. Límites

- **128 registros perdidos seguidos no se ven en la secuencia** (es módulo 128). Para eso está la cuenta de los 7 segmentos, que tiene que coincidir con las filas del CSV.
- **El período se redondea hacia abajo** a múltiplos de 5,12 µs: a 0,1 ms se informa 97,3 µs. Para el período exacto está el medidor del SPI.
- **1 Mbaud tiene que funcionar en el computador.** El conversor de la Go Board lo admite, y `tools/registrador.py --prueba` lo prueba con un pseudoterminal, no con el conversor. Si `/dev/ttyUSB1` no acepta 1 Mbaud, se graba `bitstreams/registrador_921k.bin` (926 kbaud, `CICLOS_BIT = 27`) y se lee con `--baudios 921600`: el error de 0,5 % está dentro de lo que tolera una UART. Está construido y su bitstream ruteado pasa las mismas pruebas (`make registrador`, paso 5b).
- **No se usa la serie para elegir nada mientras el ayudante no diga que no es la de la competencia** (`docs/pendientes_nicolas.md`, decisión 2).

## 6. Preguntas que nos pueden hacer

**¿Esto no es guardar la serie en el diseño?** No. El bitstream no tiene dónde guardarla: escucha y retransmite cada precio en 50 µs. La serie queda en el computador. Ninguno de los peldaños que compiten lleva el registrador.

**¿Para qué lo necesitan?** Para la puerta de maestra: comparar el patrimonio que muestra la maestra con el que predice el gemelo para la misma serie. Sin la serie, solo se puede comparar R0 con R1.

**¿Cómo saben que no se pierde ningún precio?** Por tres caminos independientes: la secuencia de cada registro, la cuenta en los 7 segmentos y LED4. En simulación, a 0,1 ms la cola nunca pasa de un registro.
