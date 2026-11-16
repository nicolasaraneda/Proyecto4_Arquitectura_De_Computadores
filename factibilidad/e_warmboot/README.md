# Pieza E. Respaldo por reconfiguración con SB_WARMBOOT e icemulti

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz. Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Estudio de factibilidad. Nada de esta carpeta está integrado en `main` ni en el flujo del repositorio. Ningún paso se probó en la placa: todo lo que depende de ella queda marcado como "por medir" y con el comando para medirlo.

## 1. Qué es y qué se construyó

La idea es que la flash de la Go Board guarde dos bitstreams en vez de uno. El primero (imagen principal) lleva el diseño más arriesgado. El segundo (imagen de respaldo) es el bitstream de competencia con el core base. La primitiva `SB_WARMBOOT` del iCE40 permite que el propio diseño le pida a la FPGA reconfigurarse con otra imagen de la flash, sin computador. Un vigilante dentro de la imagen principal dispara ese cambio si el programa deja de responder.

Se construyó:

| Qué | Dónde |
|-----|-------|
| Prueba de placa: dos imágenes mínimas que muestran `A` y `b` en el display izquierdo y saltan una a la otra con un interruptor, con dos modos de ping-pong para medir el tiempo de reconfiguración | `rtl/wb_demo.v`, `tb/tb_wb_demo.v`, `wb_demo_multi.bin` |
| Variantes de esa prueba: sin dormir la flash y con el oscilador de configuración más rápido | `variantes/` |
| Vigilante: módulo, testbench, prueba formal y copia del SoC que lo integra | `rtl/vigilante.v`, `tb/tb_vigilante.v`, `formal/vigilante.sby`, `soc/` |
| Simulación del relevo completo, del programa colgado al respaldo operando | `tb/tb_relevo.sv`, `sw/cuelgue.s` |
| Archivo de prueba del relevo: SoC con vigilante más `bitstreams/competencia_v1.bin`, para la placa y para la maestra real | `relevo_prueba_multi.bin`, `tb/tb_chip_relevo.sv` |
| Empaquetado de 2, 3 y 4 imágenes y del par `segmentado_v1` más `competencia_v1` | `scripts/tamanos.sh` |
| Enumeración de lo que lee la maestra si el pin MISO cambia a mitad de un byte | `scripts/corte_miso.py` |
| Medición del tiempo de reconfiguración por la UART | `scripts/medir_uart.py` |

Los `.bin` de esta carpeta no se versionan (el `.gitignore` del repositorio ignora `*.bin`). Se regeneran con `make -C factibilidad/e_warmboot demo variantes relevo-img` y sus hashes quedan en `SHA256SUMS.txt`, `variantes/SHA256SUMS.txt` y `mediciones/`.

## 2. Resultado en una página

| Pregunta | Respuesta | Estado |
|----------|-----------|--------|
| Cuántos bitstreams caben en la flash | 4, que además es el máximo de icemulti y del iCE40. Ocupan 129 040 bytes de 131 072 sin alinear y 130 524 alineados a 32 kB. Sobran 2 032 y 548 bytes | Medido con icemulti. La capacidad de 1 Mbit es la que publica Nandland; falta confirmarla en la placa |
| Tamaño de un bitstream de la HX1K | 32 220 bytes, siempre | Medido (4 bitstreams) |
| `SB_WARMBOOT` en la HX1K VQ100 con nextpnr | Se ubica: `SB_WARMBOOT: 1/1`. Hay una sola por chip | Medido en el log de nextpnr. Que funcione en la placa está por medir |
| Cuánto demora el cambio | 53 ms típico con el oscilador de configuración en frecuencia baja, que es lo que escribe icepack. 25 ms en media y 13 ms en alta | Documentado (hoja de datos, valor típico, sin máximo). Por medir en la placa |
| Qué ve la maestra en MISO | El pin queda en alta impedancia con un pull-up débil. La maestra lee `0xFF` (acción 11, se trata como mantener). Si su entrada tuviera una resistencia a tierra más fuerte, lee `0x00`, que también es mantener | Documentado para el pin. El nivel que lee la maestra solo se confirma con la maestra real |
| Ticks sin decisión nueva en un relevo | 10 a 10 ms, 58 a 1 ms y 536 a 0,1 ms, con 53 ms | Simulado con el modelo. Depende del tiempo real |
| Costo del vigilante en el SoC | 9 celdas lógicas y 0 BRAM (1076 a 1085 con el core base y 1001 a 1010 con el segmentado). Solo: 8 LUT y 4 flip-flops. Con N = 1 la cuenta integrada sube a 1095 y con el disparo manual a 1106: el ruido de síntesis pesa más que el módulo | Medido, 10 semillas |
| Cierra a 25 MHz | 10 de 10 semillas en las cuatro variantes con vigilante. Mínimo 45,09 MHz (base), 51,41 MHz (segmentado) y 42,05 MHz (base con disparo manual) | Medido |
| Falsos disparos | Ninguno en el testbench oficial (la cuenta nunca pasa de 1). Sin precios no cuenta: no dispara en el reset ni con la maestra detenida | Medido en simulación y probado formalmente |
| Ciclo de reinicios | No puede ocurrir: el respaldo no tiene `SB_WARMBOOT` | Por construcción |

## 3. Cómo se reproduce cada número

Desde la raíz del repositorio, con las herramientas en el `PATH`:

```bash
export PATH=$OSS_CAD_SUITE/bin:$PATH
make -C factibilidad/e_warmboot todo      # todo, cerca de media hora
make -C factibilidad/e_warmboot rapido    # lo que demora menos de dos minutos
```

| Objetivo de `make -C factibilidad/e_warmboot` | Script | Salida en `mediciones/` |
|-----------------------------------------------|--------|--------------------------|
| `demo` | `scripts/construir_demo.sh` | `demo_construccion.txt` |
| `sim-demo` (`sim-demo-rtl` para la parte corta) | `scripts/sim_demo.sh` | `demo_sim_rtl.txt`, `demo_sim_bitstream.txt` |
| `variantes` | `scripts/variantes_demo.sh` | `demo_variantes.txt` |
| `tamanos` | `scripts/tamanos.sh` | `icemulti_tamanos.txt` |
| `plataforma` | `scripts/plataforma.sh` | `plataforma.txt` |
| `miso` | `scripts/corte_miso.py` | `miso_corte.txt` |
| `vigilante-tb` | `scripts/probar_vigilante.sh` | `vigilante_tb.txt` |
| `vigilante-formal` | `scripts/formal_vigilante.sh` | `vigilante_formal.txt` |
| `vigilante-soc` | `scripts/probar_soc.sh` | `vigilante_soc.txt` |
| `vigilante-costo` | `scripts/medir_vigilante.sh` | `vigilante_costo.txt` |
| `vigilante-boton` | `scripts/medir_boton.sh` | `vigilante_boton.txt` |
| `relevo` | `scripts/relevo.sh` | `relevo.txt` |
| `relevo-img` | `scripts/construir_relevo.sh` | `relevo_construccion.txt` |
| `uart-autoprueba` | `scripts/medir_uart.py --autoprueba` | `medir_uart_autoprueba.txt` |

Todos los scripts corren desde la raíz y dejan sus productos intermedios en `factibilidad/e_warmboot/build/`. La excepción son `vigilante-costo` y `vigilante-boton`, que usan `tools/medir_variante.sh` y por eso escriben en `build/variantes/fact_e_*` de la raíz.

Todos los objetivos se volvieron a correr el 14/11 y entregaron las mismas salidas y los mismos hashes de los `.bin` que la corrida anterior (el detalle está en `AVANCE.md`). `make relevo` demora unos 7 minutos con 4 procesos; con `SOLO_INFORME=1 factibilidad/e_warmboot/scripts/relevo.sh` se vuelve a armar `mediciones/relevo.txt` desde los registros de `build/relevo/` sin simular de nuevo.

## 4. Hechos de la plataforma

### 4.1 Lo que está documentado

| Hecho | Valor | Fuente |
|-------|-------|--------|
| Memoria de la Go Board | "1 Mb Flash for booting up your FPGA". 1 Mbit son 131 072 bytes | Página del producto, https://nandland.com/the-go-board/ |
| Conexión de la flash | Memoria SPI de 8 pines (CS 1, SDO 2, WP 3, GND 4, SDI 5, SCK 6, HOLD 7, VCC 8), en la hoja 1 del esquemático | Esquemático `Go_Board_V1.sch`, https://www.nandland.com/goboard/images/Go_Board_V1.pdf |
| Pines de usuario durante la configuración | "Before and during configuration, the I/Os are held in tri-state". La señal GHIZ "is automatically asserted throughout the configuration process, forcing all user I/O pins into their high-impedance state" | Hoja de datos iCE40 LP/HX, DS1040 versión 3.4 (octubre de 2017), secciones "Global Hi-Z Control" y "Power On Reset" |
| Pull-up de un pin sin configurar | "tri-stated with a weak pull-up to VCCIO". Corriente del pull-up con VCCIO = 3,3 V: entre 11 y 128 uA, o sea entre unos 26 kΩ y 300 kΩ | DS1040, sección sysIO y tabla "DC Electrical Characteristics" (I_PU) |
| Tiempo de configuración de la HX1K desde la flash | 53 ms con el oscilador en frecuencia baja (por defecto), 25 ms en media y 13 ms en alta. Son valores típicos: la tabla no da máximo | DS1040, tabla "SPI Master or NVCM Configuration Time" (tCONFIG) |
| Oscilador interno de configuración | 7,5 MHz en baja (por defecto), 24 MHz en media y 40 MHz en alta | DS1040, tabla "sysCONFIG Port Timing Specifications" (fMCLK) |
| Borrado de la memoria de configuración antes de leer la flash | 800 us en la HX1K | DS1040, misma tabla (tMCLK) |
| Los pines se activan después de configurar | 49 ciclos del reloj de configuración después de CDONE | DS1040 (tDONE_IO) y nota técnica FPGA-TN-02001 versión 3.4 (diciembre de 2022), sección 5 |
| Warm boot | "A special design primitive, SB_WARMBOOT, allows an FPGA application to choose between four configuration images". Al subir BOOT la FPGA reinicia la configuración desde el vector elegido con S1 S0. El archivo con los vectores va en la dirección 0 de la flash | FPGA-TN-02001, sección 11 y figura 10.1 |

La nota técnica es la versión nueva de la TN1248 que cita la hoja de datos. Ninguno de los dos documentos dice cuánto demora un warm boot en particular: el supuesto de este estudio es que demora lo mismo que una configuración desde CRESET_B (tCONFIG), porque hace lo mismo y además lee primero un vector de 32 bytes.

### 4.2 Lo que se midió sin la placa (`mediciones/plataforma.txt`, `mediciones/icemulti_tamanos.txt`)

- **Tamaño del bitstream.** Los cuatro bitstreams que hay (`competencia_v1`, `segmentado_v1` y las dos imágenes de la prueba) miden 32 220 bytes, con 12 BRAM usadas o con ninguna. Son 257 760 bits. A la frecuencia típica del oscilador, leerlos toma 34,4 ms en baja, 10,7 ms en media y 6,4 ms en alta. La diferencia con tCONFIG es lo que la FPGA demora en borrar su memoria, despertar la flash y arrancar.
- **Cabecera.** Los bitstreams de `bitstreams/` traen el oscilador en frecuencia baja, warm boot habilitado y la orden de dormir la flash al terminar (`icepack -u -v`). icepack no tiene opción para cambiar la frecuencia.
- **Formato de icemulti.** El archivo parte con 5 vectores de 32 bytes (160 bytes): el de encendido y los cuatro que elige S1 S0. Cada vector lleva la dirección de 24 bits de su imagen. Con dos imágenes, los vectores sin imagen apuntan a la imagen 0. Acepta a lo más 4 imágenes: con 5 responde `Too many images supplied`. `scripts/ver_multi.py` decodifica los vectores y comprueba que cada imagen esté copiada sin cambios.
- **`SB_WARMBOOT` en nextpnr.** `nextpnr-ice40 --hx1k --package vq100` informa `SB_WARMBOOT: 1/1 100%` y cierra timing. Con dos primitivas en el mismo diseño falla: `Unable to place cell 'u_a', no BELs remaining to implement cell type 'SB_WARMBOOT'`.
- **iceprog.** Por defecto borra en bloques de 64 kB (`erase aligned chunks of 64kB in write mode`). `-b` borra la flash completa antes de escribir, `-t` lee el identificador de la flash y `-c` solo verifica. El texto de ayuda se leyó del binario con `strings`; iceprog no se ejecutó.

### 4.3 Lo que no se pudo confirmar y cómo se comprueba en la placa

| Dato | Por qué falta | Cómo se comprueba |
|------|---------------|-------------------|
| Modelo de la flash | En el PDF del esquemático los valores de los componentes están dibujados con trazos y no se pueden leer como texto. Lo más probable es una Micron M25P10-A, pero no hay un documento que lo respalde aquí | `iceprog -t` imprime el identificador. En las memorias SPI el tercer byte suele ser el exponente de la capacidad: `0x11` son 2^17 = 131 072 bytes |
| Capacidad real | Solo está el "1 Mb" de la página | `iceprog -R 262144 lectura.bin` y comparar las dos mitades: si son iguales, la memoria dio la vuelta a los 128 kB |
| Tamaño del sector de borrado | Depende del modelo. Si un sector es de 32 kB, el borrado por defecto de iceprog deja sin borrar la segunda mitad de un archivo de dos imágenes | Usar siempre `iceprog -b` con los archivos de varias imágenes |
| Que el warm boot funcione en esta placa | No hay placa en este tramo | Sección 6 |
| Tiempo real de reconfiguración | La hoja de datos da solo el típico | Sección 6.4 |
| Cuánto demora el pin en soltarse después de BOOT | No está documentado | Osciloscopio en el LED 4 (sección 6.4) |
| Si la flash despierta sola en un warm boot | La FPGA la deja dormida al terminar de configurarse. Lo normal es que la despierte al reconfigurar, pero no se encontró escrito | Si el salto no funciona, probar `variantes/wb_demo_multi_sin_dormir.bin` |
| Polaridad de los interruptores | Se supuso que apretado es 1, como los lee `pochoco_periph` | Paso 6 de la sección 6.3 |

## 5. Cuántas imágenes caben

Construido con icemulti (`mediciones/icemulti_tamanos.txt`), contra 131 072 bytes:

| Imágenes | Sin alinear | `-a15` (32 kB, la imagen 0 después de la cabecera) | `-A15` (32 kB, todas) | `-a16` (64 kB) |
|----------|-------------|-----------------------------------------------------|------------------------|-----------------|
| 2 | 64 600 (49,3 %) | 64 988 (49,6 %) | 97 756 (74,6 %) | 97 756 (74,6 %) |
| 3 | 96 820 (73,9 %) | 97 756 (74,6 %) | 130 524 (99,6 %) | no cabe (163 292) |
| 4 | 129 040 (98,4 %) | 130 524 (99,6 %) | no cabe (163 292) | no cabe (228 828) |
| 5 | icemulti lo rechaza | | | |

Caben 4, que es el máximo. Con `-a15` cada imagen parte en un múltiplo de 32 kB: la imagen 0 comparte el primer bloque con la cabecera (termina en 0x7E7C) y las demás quedan en 0x8000, 0x10000 y 0x18000. La alineación sirve para regrabar una sola imagen sin tocar las otras, si el sector de borrado de la flash es de 32 kB. Esa regrabación parcial (`iceprog -o`) no se probó.

Para el respaldo bastan 2 imágenes. Las otras dos quedarían libres, por ejemplo para una segunda variante del principal.

## 6. Prueba para la placa

Esta sección es para quien tenga la placa en la mano (Nicolás). `iceprog` no se ejecutó en este tramo.

### 6.1 Qué hace la prueba

`wb_demo_multi.bin` tiene dos imágenes hechas del mismo módulo (`rtl/wb_demo.v`, 184 y 186 celdas, sin BRAM):

| | Imagen 0 (la de encendido) | Imagen 1 |
|-|----------------------------|----------|
| Display izquierdo | `A` | `b` |
| Display derecho | Segundos desde que la imagen arrancó, de 0 a 9 | Lo mismo |
| LED 1 | Encendido | Apagado |
| LED 2 | Encendido cuando el salto manual está armado (10 ms después de arrancar con SW1 suelto) | Lo mismo |
| LED 3 | Parpadea una vez por segundo | Lo mismo |
| LED 4 | Apagado | Encendido |
| UART | Envía `A` una vez al arrancar (115200 baudios) | Envía `b` |
| MISO | En 0 | En 0 |

Interruptores:

- **SW1**: salta a la otra imagen. Hay que soltarlo y volver a apretarlo para saltar de nuevo.
- **SW2 mantenido**: ping-pong lento. Cada imagen espera 0,671 s desde que arrancó (2^24 ciclos) y salta.
- **SW3 mantenido**: ping-pong rápido. Cada imagen espera 41,9 ms (2^20 ciclos) y salta.

Cada vez que una imagen arranca, el display derecho parte de 0. Así se nota una reconfiguración aunque la letra no cambie.

### 6.2 Simulación

- RTL (`mediciones/demo_sim_rtl.txt`): las dos imágenes, 6 escenarios cada una, 12 corridas y 58 comprobaciones, todas correctas. Se comprueba que BOOT no sube sin tocar nada, que SW1 apretado desde el arranque no dispara, que los rebotes no disparan, que cada modo dispara en el ciclo esperado, que S1 S0 apuntan a la otra imagen (01 en la imagen 0 y 00 en la imagen 1), que BOOT no vuelve a bajar y que la letra, los LED, MISO y el byte de la UART son los de la imagen.
- Desde el `.asc` (`mediciones/demo_sim_bitstream.txt`): los mismos escenarios sobre el Verilog que `icebox_vlog` reconstruye de cada imagen ya ubicada, con las esperas reales (0,671 s y 41,9 ms): 12 corridas y 58 comprobaciones, todas correctas. Demora unos 8 minutos con 5 procesos.
- BOOT sube 2 ciclos después de cumplirse la espera en el modo lento y 3 en el rápido. Están incluidos en las esperas que usa `scripts/medir_uart.py`.

La reconfiguración misma no se puede simular. Lo que queda por ver en la placa es justamente eso.

### 6.3 Pasos

Todos los comandos se corren desde la raíz del repositorio. Anota lo que veas en la hoja de la sección 6.6.

1. Preparar el entorno y regenerar los archivos (opcional si ya están):

   ```bash
   cd Proyecto4_Arquitectura_De_Computadores
   export PATH=$OSS_CAD_SUITE/bin:$PATH
   make -C factibilidad/e_warmboot demo variantes
   ```

   Construye las dos imágenes y los archivos de varias imágenes. Demora menos de un minuto.

2. Comprobar que el archivo es el que se simuló:

   ```bash
   (cd factibilidad/e_warmboot && sha256sum -c SHA256SUMS.txt)
   ```

   Tiene que decir `wb_demo_multi.bin: OK`. El hash esperado es `2f0d6efe6d26c067205086cc02588ddaeee8ef32249a68e6723efb0b26e1fa26`.

3. Leer el identificador de la flash. No escribe nada:

   ```bash
   iceprog -t
   ```

   Anota los tres bytes de la línea `flash ID`. Si el tercero es `0x11`, la memoria es de 1 Mbit.

4. Guardar lo que hay ahora en la flash, por si hiciera falta volver atrás. Tampoco escribe:

   ```bash
   mkdir -p factibilidad/e_warmboot/build
   iceprog -R 131072 factibilidad/e_warmboot/build/flash_antes.bin
   ```

5. Grabar la prueba. La opción `-b` borra la flash completa antes de escribir. Hace falta porque el archivo ocupa más de un bloque de borrado:

   ```bash
   iceprog -b factibilidad/e_warmboot/wb_demo_multi.bin
   ```

   Tiene que terminar con `VERIFY OK`. Si termina con un error de verificación, anota el mensaje y no sigas.

6. Mirar la placa sin tocar nada. Debe verse `A` a la izquierda, el display derecho contando segundos, el LED 1 y el LED 2 encendidos, el LED 3 parpadeando y el LED 4 apagado. Si las letras alternan solas, los interruptores están invertidos respecto de lo supuesto: anótalo en la hoja de resultados y no sigas con los pasos 7 a 9, porque el módulo habría que corregirlo.

7. Apretar SW1 un instante. La placa debe pasar a `b`, con el LED 4 encendido, el LED 1 apagado y el display derecho otra vez en 0. El apagón entre las dos imágenes dura unas centésimas de segundo y casi no se ve. Apretar SW1 otra vez: vuelve a `A`.

   Si al apretar SW1 los displays se apagan y no vuelven, la reconfiguración no terminó. Desconecta y vuelve a conectar el USB (debe volver `A`), y repite los pasos 5 a 7 con `variantes/wb_demo_multi_sin_dormir.bin`. Si con ese archivo sí funciona, el problema es que la flash queda dormida.

8. Mantener apretado SW2. Las letras deben alternar más o menos cada 0,7 s. Al soltarlo se queda en la imagen que esté.

9. Mantener apretado SW3. Los displays parpadean rápido y se ven las dos letras mezcladas.

10. Medir el tiempo de reconfiguración (sección 6.4).

11. Dejar la placa como estaba (sección 6.5).

### 6.4 Cómo medir el tiempo de reconfiguración

En los modos de ping-pong, el tiempo entre dos arranques seguidos es la espera, que se conoce con la exactitud del cristal, más el tiempo de reconfiguración. Hay tres formas sin osciloscopio, de la más simple a la más exacta:

**a. Cronómetro (ping-pong lento).** Mantén SW2 apretado y cronometra 100 cambios de letra. Si el total es `t` segundos:

    tiempo de reconfiguración = t / 100 - 0,671 s

Con 53 ms el total sería 72,4 s. Un error de 0,3 s en el cronómetro son 3 ms en el resultado.

**b. Video en cámara lenta (ping-pong rápido).** Con SW3 apretado, graba los displays a 240 cuadros por segundo. Durante la reconfiguración los displays están apagados. Cuenta, en unos 20 ciclos seguidos, los cuadros con el display encendido (`e`) y los cuadros con el display apagado (`a`):

    tiempo de reconfiguración = 41,9 ms × a / e

Con 53 ms serían unos 10 cuadros encendidos y 13 apagados por ciclo. No necesita cronómetro: usa la espera de 41,9 ms como patrón.

**c. UART (ping-pong rápido).** Es la más exacta. Cada imagen envía un byte al arrancar y el computador anota la hora de llegada. El puerto serie de la placa tiene que estar visible desde donde corras el script (es el segundo de los dos puertos de la Go Board, por ejemplo `/dev/ttyUSB1`):

```bash
python3 factibilidad/e_warmboot/scripts/medir_uart.py /dev/ttyUSB1 --modo rapido --segundos 30
```

Mantén SW3 apretado los 30 segundos. La última línea dice `RESULTADO: tiempo de reconfiguración = ... ms`. Cópiala tal cual. El conversor USB entrega los bytes con hasta 16 ms de atraso, pero el promedio de 300 intervalos queda con menos de 0,1 ms de error (`mediciones/medir_uart_autoprueba.txt`). Con `--modo lento` y SW2 sirve igual. Si el sistema no deja abrir el puerto es un tema de permisos de tu usuario sobre el dispositivo.

Lo que miden a, b y c es el tiempo desde que sube BOOT hasta que la imagen nueva empieza a correr. Para el SoC hay que sumarle el reset de 4095 ciclos (0,164 ms).

**Con osciloscopio o analizador lógico**, si se consigue uno, hay dos puntos que dicen más:

- **Pin MISO del PMOD** (pin 63 de la FPGA). La prueba lo mantiene en 0. Durante la reconfiguración queda suelto y el pull-up interno lo sube a 3,3 V. El ancho de ese pulso es el tiempo que la maestra vería el pin sin dueño. Con una resistencia de 10 kΩ entre el pin y tierra se puede además estimar el pull-up: si el pulso llega a `V` volts, el pull-up vale 10 kΩ × (3,3 − V) / V.
- **Pin del LED 4** (pin 60). Cambia de nivel en el mismo ciclo en que sube BOOT, después queda a un voltaje intermedio mientras el pin está suelto (el pull-up a través del LED) y al final toma el nivel de la imagen nueva. Se ven los tres tramos: de BOOT a que se sueltan los pines, que es el dato que no está documentado, y de ahí a que arranca la imagen nueva.

Con el disparo del osciloscopio en modo único y SW1 se captura un solo cambio. Con SW3 se repite sola cada 95 ms, más cómodo para medir con cursores.

**Variantes para acortar el cambio (opcional).** `variantes/wb_demo_multi_frec_media.bin` y `variantes/wb_demo_multi_frec_alta.bin` son la misma prueba con el oscilador de configuración en frecuencia media y alta (un byte de la cabecera de cada imagen; el CRC no cambia y `icepack -u` las acepta, `mediciones/demo_variantes.txt`). Según la hoja de datos el cambio bajaría a 25 ms y 13 ms. Se graban y se miden igual que la principal (pasos 5 a 10). Si con alguna la placa no arranca (displays apagados después de grabar), la flash no alcanza esa frecuencia: se anota y se graba otra cosa encima, porque iceprog siempre puede escribir la flash.

### 6.5 Volver a dejar la placa con el bitstream de competencia

```bash
iceprog -b bitstreams/competencia_v1.bin
```

Borra toda la flash y graba el bitstream de competencia. Tiene que terminar con `VERIFY OK`.

```bash
iceprog -c bitstreams/competencia_v1.bin
(cd bitstreams && sha256sum -c SHA256SUMS)
```

El primero vuelve a comparar la flash con el archivo sin escribir nada. El segundo comprueba que el archivo es el del repositorio. Con `competencia_v1.bin` la placa queda con los dos displays en `0` y los LED apagados, porque `trade.s` no los usa: eso es lo normal.

### 6.6 Hoja de resultados

| Dato | Valor |
|------|-------|
| `flash ID` (paso 3) | |
| `VERIFY OK` al grabar `wb_demo_multi.bin` (paso 5) | sí / no |
| Sin tocar nada se ve `A` y cuenta segundos (paso 6) | sí / no |
| SW1 cambia entre `A` y `b` (paso 7) | sí / no |
| Hizo falta el archivo `sin_dormir` | sí / no |
| Segundos para 100 cambios con SW2 (método a) | |
| Cuadros encendidos y apagados (método b) | |
| Línea `RESULTADO` de `medir_uart.py`, modo rápido | |
| Lo mismo con `frec_media` y con `frec_alta` | |
| Con osciloscopio: ancho del pulso en MISO, voltaje del pulso, tiempo de BOOT a pin suelto | |
| `VERIFY OK` al restaurar `competencia_v1.bin` | sí / no |

## 7. Qué ve la maestra en MISO durante el cambio

### 7.1 El byte

Mientras la FPGA se reconfigura, sus pines de usuario están en alta impedancia con un pull-up débil (sección 4.1). El pin MISO (pin 63, banco 1, 3,3 V) deja de estar manejado. Cada grupo tiene su propia línea MISO, así que nadie más la maneja. La maestra lee entonces:

- `0xFF` si su entrada no tiene resistencia a tierra, o tiene una más débil que el pull-up del iCE40 (entre 26 kΩ y 300 kΩ). Los bits [7:6] valen 11, que según el enunciado es "reservado (se trata como mantener)". En el testbench oficial cae en el `default` y no ejecuta nada.
- `0x00` si la maestra tiene una resistencia a tierra más fuerte. También es mantener.

En los dos casos la maestra no ejecuta órdenes durante el corte y la posición queda congelada. Lo que cambia es que ya no se repite la decisión anterior, que es lo que el enunciado describe para un programa que no alcanza a responder: se lee mantener.

Las líneas compartidas SCLK, MOSI y CS_n son entradas de nuestra placa. Durante la reconfiguración reciben el mismo pull-up débil, igual que cuando la placa se enciende. La maestra las maneja con una salida y no debería notarlo.

### 7.2 Si el cambio cae a mitad de un byte

`scripts/corte_miso.py` recorre todos los casos (`mediciones/miso_corte.txt`) y `scripts/relevo.sh` los repite en simulación con el SoC (partes 2 y 3 de `mediciones/relevo.txt`). Coinciden.

- **Vuelta.** El respaldo arranca en reset con MISO en 0 y con `DECISION = 0x00`. Si empieza a manejar el pin dentro de una transacción, la maestra lee unos cuantos unos y después ceros: `0x80`, `0xC0`, `0xE0` hasta `0xFE`. `0x80` es vender 0, que no se ejecuta, y el resto es acción 11. Ningún caso ejecuta una orden. Simulado en 66 puntos, con dos por bit: cero órdenes. Además el esclavo SPI descarta el byte que quedó a medias, porque su contador de bits parte de cero en la bajada siguiente de CS_n.
- **Salida.** El vigilante sube BOOT solo cuando CS_n está en alto (100 ns después de que sube, medido en la simulación del bitstream). Hasta la transacción siguiente quedan 90 us en la ronda 3. La salida cae dentro de una transacción solo si la FPGA demora más que eso en soltar el pin, y ese retardo no está documentado. Si ocurriera:
  - Con `comprar 63` o `vender 63` escrito, que es lo único que escribe la regla base, la maestra lee la misma orden, una de menor cantidad o mantener. Nunca una orden distinta.
  - Con un mantener escrito como `0x00` y pull-up, un corte justo después del primer bit se lee `0x7F`, comprar 63. Es el caso con una orden que el programa no pidió: 77 de 2304 combinaciones, que son los 64 mantener con el bit 7 en 0 (`0x00` a `0x3F`, corte después del primer bit) y las órdenes de cantidad 0 (`0x40` y `0x80`). En la simulación ocurre en 2 de 33 puntos (retardos de 92,0 y 92,5 us): la maestra compra todo lo que alcanza en un tick que nadie eligió y el respaldo lo liquida al arrancar; en esa corrida costó 766 de patrimonio. Un programa que escriba mantener como `0xC0` no tiene ningún caso.

### 7.3 Ticks que se pierden

Simulado con `tb/tb_relevo.sv` (`mediciones/relevo.txt`, parte 1): el SoC principal con vigilante corre un programa que responde 20 precios y se cuelga; el modelo deja el pin suelto durante el tiempo de configuración; y el SoC de respaldo parte de cero. Maestra y contabilidad son las del testbench oficial.

| Ronda | T | Tiempo de configuración supuesto | Ticks con el pin suelto | Ticks sin decisión nueva | De una ronda de 2000 ticks |
|-------|---|----------------------------------|--------------------------|---------------------------|-----------------------------|
| 1 | 10 ms | 53 ms | 5 | 10 | 0,5 % |
| 2 | 1 ms | 53 ms | 53 | 58 | 2,9 % |
| 3 | 0,1 ms | 53 ms | 530 | 536 | 26,8 % |
| 3 | 0,1 ms | 25 ms (frecuencia media) | 250 | 256 | 12,8 % |
| 3 | 0,1 ms | 13 ms (frecuencia alta) | 130 | 136 | 6,8 % |

"Sin decisión nueva" cuenta desde el último precio que respondió el principal hasta la primera escritura del respaldo: los 5 precios que el vigilante espera (N + 1 con N = 4), el tiempo de configuración, el reset de 4095 ciclos (0,164 ms, 1,6 ticks en la ronda 3) y la espera al primer precio completo. Con otro tiempo `Tc` en milisegundos la cuenta es 5 + parte entera de (Tc + 0,178) / T.

El dato que más pesa: una ronda de 2000 ticks a 0,1 ms dura 0,2 s. Un relevo en la ronda 3 se lleva la cuarta parte de la ronda con el oscilador por defecto. En las rondas 1 y 2 casi no se nota.

### 7.4 El estado del algoritmo al volver

El respaldo parte de cero: no hereda nada del principal.

- **Posición.** La contabilidad la lleva la maestra, así que las acciones siguen ahí. El respaldo arranca creyendo que está afuera y escribe `vender 63` desde su primer precio. Como la orden es idempotente, eso liquida lo que hubiera: en la simulación, 67 acciones en dos ticks y dos comisiones. La regla base parte entonces sin posición, que es su estado inicial normal.
- **Media.** Se inicializa con el primer precio que recibe el respaldo. Tarda del orden de 100 ticks en converger (alfa = 1/32), y mientras tanto la regla opera poco: con la media igual al precio no hay desviación.
- **Antes de la primera escritura** la maestra lee `0x00` (el valor de reset de `DECISION`): mantener.
- **Reset largo.** `PorBits = 12` son 4095 ciclos, 0,164 ms. Frente a los 53 ms de la configuración no pesa. Si el respaldo necesita ese reset después de un warm boot igual que después de encender (por las BRAM) no se sabe: se ve en la prueba de relevo de la sección 10.

Un programa colgado no es el peor caso para la contabilidad. Su última orden (`comprar 63` o `vender 63`) se sigue repitiendo y es idempotente: el grupo queda comprado o en caja hasta el final de la ronda. Lo que el respaldo recupera es seguir operando, y lo que cuesta es el corte y liquidar la posición en un momento que no eligió el algoritmo.

### 7.5 Qué solo se confirma con la maestra real el 26/11

1. Qué byte lee la maestra con el pin suelto y qué hace con él (si lo grafica, si lo cuenta como mantener, si marca al grupo como desconectado).
2. Que el respaldo retoma en medio del tráfico real, que es asíncrono.
3. Que la reconfiguración de nuestra placa no molesta a las líneas compartidas.

Cómo probarlo ese día: con `relevo_prueba_multi.bin` (sección 10). El programa de la imagen principal se cuelga solo después de 500 precios, el vigilante dispara y el respaldo, que es `competencia_v1.bin`, sigue operando. En la pantalla de la maestra se debería ver el patrimonio quieto durante el corte y después la regla base. Los displays de la placa dicen en qué imagen está.

## 8. Vigilante

### 8.1 Diseño (`rtl/vigilante.v`)

Cuenta los precios recibidos desde la última escritura en `DECISION`. En un programa sano esa cuenta va de 0 a 1 y vuelve a 0 en cada tick. Si llega a N + 1 (N precios quedaron sin respuesta y llegó otro más), sube BOOT con el destino S1 S0 = 01, la imagen de respaldo. Por defecto N = 4.

Decisiones de diseño:

- **Cuenta precios, no tiempo.** Funciona igual con cualquier período y no depende de saber cuánto dura un tick. La escritura en `DECISION` hace de latido: el programa no necesita ninguna instrucción adicional.
- **Espera a que CS_n esté en alto** para subir BOOT, de modo que el pin no se suelte a mitad de un byte.
- **BOOT no se baja.** Queda en alto hasta que la FPGA se reconfigura.
- **Disparo manual opcional** (`forzar_i`), que en el SoC solo se conecta al interruptor 4 con el parámetro `VigBoton = 1`. Es para la prueba de placa. En la edición de competencia quedaría desconectado (sección 11).

Para integrarlo se usó una copia del SoC (`soc/pochoco_soc.v`, parámetros `Vigilante`, `VigN`, `VigDestino` y `VigBoton`) y una copia del esclavo SPI (`soc/pochoco_spi_slave.v`) con tres salidas nuevas que sacan señales que ya existían: `byte_done`, la escritura en `DECISION` y `cs_active`. No cambia el mapa de registros ni ningún nombre de los que el testbench oficial usa por jerarquía.

### 8.2 Costo (`mediciones/vigilante_costo.txt`)

`tools/medir_variante.sh`, `nextpnr --hx1k --package vq100 --freq 25`, 10 semillas, `sw/trade.hex`:

| Variante | Celdas lógicas | BRAM | LUT4 | Frecuencia máxima: mínima, mediana, máxima (MHz) | Cierran a 25 MHz |
|----------|----------------|------|------|---------------------------------------------------|------------------|
| `rtl/` del repositorio, core base (referencia) | 1083 de 1280 | 12 de 16 | 906 | 42,43 / 43,74 / 45,08 | 10 de 10 |
| Copia del SoC, core base, `Vigilante = 0` (control) | 1076 | 12 | 899 | 42,74 / 44,75 / 46,13 | 10 de 10 |
| Copia del SoC, core base, `Vigilante = 1` | **1085** | 12 | 906 | 45,09 / 45,61 / 47,63 | 10 de 10 |
| `rtl/` del repositorio, core segmentado (referencia) | 994 | 12 | 802 | 51,13 / 53,50 / 54,50 | 10 de 10 |
| Copia del SoC, core segmentado, `Vigilante = 0` (control) | 1001 | 12 | 810 | 51,83 / 53,77 / 55,44 | 10 de 10 |
| Copia del SoC, core segmentado, `Vigilante = 1` | **1010** | 12 | 817 | 51,41 / 53,56 / 54,39 | 10 de 10 |

En las dos variantes con vigilante nextpnr informa `SB_WARMBOOT: 1/ 1 100%`.

El costo es la diferencia entre la copia con vigilante y la misma copia sin él: 9 celdas en los dos cores, y ninguna BRAM. La copia sin vigilante no da exactamente lo mismo que `rtl/` (7 celdas menos en el base y 7 más en el segmentado), aunque la lógica es la misma: es el ruido del conteo que describe la decisión T6. El módulo sintetizado solo ocupa 8 LUT, 4 flip-flops y 1 acarreo con N = 4, 5 LUT y 3 flip-flops con N = 1, y 13 LUT y 6 flip-flops con N = 15. La frecuencia máxima no cambia más que el ruido entre semillas. Cabe junto al SPI y cierra a 25 MHz en las 10 semillas.

Dos variantes más, también con 10 semillas y el core base (`mediciones/vigilante_boton.txt`):

| Variante | Celdas lógicas | LUT4 | Frecuencia máxima: mínima, mediana, máxima (MHz) | Cierran a 25 MHz |
|----------|----------------|------|---------------------------------------------------|------------------|
| `Vigilante = 1`, `VigN = 1` | 1095 de 1280 | 917 | 43,98 / 45,30 / 47,04 | 10 de 10 |
| `Vigilante = 1`, `VigN = 4`, `VigBoton = 1` (disparo manual) | 1106 de 1280 | 925 | 42,05 / 44,14 / 46,55 | 10 de 10 |

Dos resultados que no eran los esperados. Achicar el vigilante a N = 1 no ahorra celdas una vez integrado: da 1095, diez más que con N = 4, aunque el módulo solo sea más chico. Y el disparo manual, que son dos flip-flops, sube la cuenta en 21 celdas. Ninguna de las dos diferencias se explica por el tamaño del módulo. Son del orden del ruido de síntesis del SoC completo que describe T6 (unas 10 celdas), y en el caso del disparo manual, el doble; no se investigó de dónde sale. Para decidir conviene tomar el costo como "entre 9 y 30 celdas" y no como 9 exactas. Con cualquiera de las variantes el SoC queda bajo 1110 celdas.

### 8.3 Verificación

| Prueba | Resultado | Archivo |
|--------|-----------|---------|
| Testbench del módulo, N = 1, 2, 4, 7 y 15: 17 comprobaciones dirigidas por valor de N y 400 000 ciclos de estímulo aleatorio contra un modelo, con resets | 85 comprobaciones correctas, cero diferencias con el modelo, entre 24 y 214 disparos por corrida | `mediciones/vigilante_tb.txt` |
| Prueba formal por inducción con SymbiYosys, N = 1, 4 y 7: BOOT solo sube con CS_n en alto, solo por la cuenta completa o el disparo manual, no vuelve a bajar, y solo después de N + 1 precios seguidos sin escritura (contra un monitor con otra codificación) | PASS las 3. Alcanzabilidad: PASS las 3 (el disparo por cuenta y ocho precios respondidos sin disparo) | `mediciones/vigilante_formal.txt` |
| Controles negativos de la prueba formal: dos errores puestos a propósito | Los dos dan FAIL, como corresponde | el mismo |
| Testbench oficial sin modificar sobre la copia del SoC con vigilante, core base y segmentado | 4/4 en los dos. `decisiones.csv` idéntico byte a byte al del SoC de `rtl/`. La cuenta del vigilante nunca pasa de 1 y BOOT nunca sube | `mediciones/vigilante_soc.txt` |
| Relevo completo en simulación (sección 7.3) | El vigilante dispara en el tick esperado, con CS_n en alto, y el respaldo retoma | `mediciones/relevo.txt` |
| Imagen principal de la prueba de relevo simulada desde el `.asc` | BOOT sube exactamente después de N + 1 precios sin respuesta y con el interruptor 4 | `mediciones/relevo_construccion.txt` |

### 8.4 Falsos disparos

- **Durante el reset inicial.** No puede: el vigilante está en reset y el esclavo SPI en reset no entrega precios. En el testbench oficial los dos primeros precios llegan durante el reset y la cuenta máxima es 1.
- **Con la maestra detenida, o antes de que parta.** No cuenta: sin precios completos no hay nada que contar. Probado con CS_n moviéndose sin completar bytes, y formalmente.
- **Entre rondas.** Igual que el caso anterior.
- **Un programa sano que no escribe `DECISION` en todos los ticks.** Dispararía. Hoy `trade.s` escribe siempre. Si el programa final dejara de escribir cuando mantiene, o demorara más de N ticks en responder (un modelo pesado en la ronda 3, o una inicialización larga al arrancar), hay que subir N o armar el vigilante solo después de la primera escritura. Es una condición que el vigilante le impone al programa y hay que revisarla cada vez que el programa cambie.
- **Ruido en CS_n o SCLK al conectar el cable.** Un rebote que no completa un byte no cuenta. Si el ruido completa uno, el programa lo responde y la cuenta vuelve a cero.

Lo que el vigilante no detecta: un programa que sigue escribiendo `DECISION` pero con decisiones equivocadas. Solo ve el silencio.

### 8.5 Ciclo de reinicios

No puede ocurrir. La imagen de respaldo no instancia `SB_WARMBOOT`, así que no puede pedir otra reconfiguración: el cambio es de una sola vía. La cabecera de `competencia_v1.bin` trae el bit de warm boot habilitado, como todos los bitstreams de icepack, pero sin la primitiva nadie maneja BOOT. Después de un relevo la placa se queda en el respaldo hasta que se le corte la alimentación. Al volver a encender parte otra vez con la principal: si la causa del cuelgue se repite habrá otro relevo, pero uno por encendido.

## 9. Archivo realista y qué habría que reconstruir

`scripts/tamanos.sh` arma con `icemulti -a15` un archivo con `bitstreams/segmentado_v1.bin` como imagen de encendido y `bitstreams/competencia_v1.bin` como respaldo: 64 988 bytes, el 49,6 % de la flash, con el respaldo en 0x8000. Las dos imágenes quedan copiadas sin ningún cambio, con sus hashes de `bitstreams/SHA256SUMS`. Es solo un ejercicio de tamaño: `segmentado_v1.bin` no tiene `SB_WARMBOOT`, así que ese archivo nunca saltaría. No se graba.

Para una versión real:

1. **La imagen principal se reconstruye.** Hay que llevar a `rtl/` las tres salidas del esclavo SPI, el vigilante y la primitiva (apagados por defecto con un parámetro, para no cambiar el bitstream del core base), sintetizar con `Vigilante = 1` y volver a correr toda la verificación del principal. Es hardware nuevo: tiene que pasar por la maestra el 26/11.
2. **La imagen de respaldo no se toca.** `competencia_v1.bin` entra tal cual, con su hash. Lo que sí es nuevo es que arranque por un warm boot en vez de por el encendido, y eso también hay que verlo en la placa.
3. **El archivo de la flash pasa a ser el de dos imágenes.** Es lo que se graba y lo que hay que etiquetar con su hash. Se graba con `iceprog -b`.
4. **Cambio de programa sin sintetizar.** Con dos imágenes, `icebram` tiene que aplicarse a cada una y después hay que empaquetar de nuevo. Sigue pendiente probar `icebram` en este diseño, también con las dos copias de la memoria del segmentado.
5. **Elegir N** con el programa final, por lo dicho en 8.4.
6. **Oscilador de configuración**, si la prueba de placa muestra que la frecuencia media o alta funcionan. Cambia un byte de cada imagen, y por lo tanto su hash: habría que hacerlo antes del 26/11.

## 10. Prueba de relevo con el bitstream de competencia

`relevo_prueba_multi.bin` (`scripts/construir_relevo.sh`, `mediciones/relevo_construccion.txt`) es un archivo de dos imágenes para ver el relevo de verdad:

- **Imagen 0**: la copia del SoC con vigilante (N = 4) y disparo manual en el interruptor 4, con `sw/cuelgue.s`: responde 500 precios con `comprar 63` y se cuelga. Enciende el LED 1 y muestra en los displays, en hexadecimal, el byte bajo de los precios que le faltan. Ocupa 1106 celdas de 1280 y 12 BRAM, con `SB_WARMBOOT: 1 de 1`, y cierra a 45,39 MHz con la semilla 1. Son 21 celdas más que la variante con vigilante de la sección 8.2 (1085). La diferencia viene del disparo manual y no del programa: con `sw/trade.hex` en vez de `sw/cuelgue.s` la cuenta es la misma, 1106 (`mediciones/vigilante_boton.txt`).
- **Imagen 1**: `bitstreams/competencia_v1.bin`, sin cambios (mismo hash).

No es la edición de competencia. Es una imagen de prueba.

La imagen 0 se simuló desde su `.asc` (`tb/tb_chip_relevo.sv`): con la maestra del testbench, BOOT sube en el tick 506, que es exactamente N + 1 precios después del último respondido, 100 ns después de que sube CS_n, con S1 S0 = 01; sin maestra, el interruptor 4 sube BOOT y los otros tres no.

**En la casa, sin la maestra:**

```bash
(cd factibilidad/e_warmboot && sha256sum -c SHA256SUMS.txt)
iceprog -b factibilidad/e_warmboot/relevo_prueba_multi.bin
```

Debe verse el LED 1 encendido y `F4` en los displays (500 en hexadecimal es 0x1F4). Al apretar el interruptor 4 la placa debe pasar al respaldo: LED apagados y `00` en los displays. Si los displays quedan apagados, el respaldo no arrancó. Para volver a la imagen principal hay que desconectar y conectar el USB. Con esto se comprueba, sin la maestra, que `competencia_v1.bin` arranca por warm boot.

**El 26/11, con la maestra:** se graba el mismo archivo y se conecta la placa. Mientras la maestra envía precios los displays cuentan hacia abajo. Al llegar a `00` el programa se cuelga, 5 precios después el vigilante dispara y el LED 1 se apaga. Hay que anotar qué muestra la pantalla de la maestra durante el corte (el patrimonio debería quedar quieto en lo que valga la posición) y si después se ve operar a la regla base. Si la maestra permite ver el byte recibido, anotar si es `FF` o `00`. Conviene repetirlo con cada período que la maestra ofrezca. Después se restaura la placa como en la sección 6.5.

## 11. Reglas del enunciado y preguntas para el ayudante

| Regla | Cumple | Comentario |
|-------|--------|------------|
| "La decisión se debe calcularla en el Espino Core en la placa. El core debe leer el precio y escribir la decisión; el hardware agregado puede acelerar partes del algoritmo, pero no reemplazar al procesador en el ciclo de decisión" | Sí | El vigilante no calcula nada: mira si llegan precios y si se escribe `DECISION`. En las dos imágenes decide Espino. Duda: durante el corte la maestra no lee una decisión de Espino sino el pin suelto, que se interpreta como mantener |
| "No se puede usar información externa a la serie recibida por SPI ni almacenar series de precios en el diseño" | Sí | La flash guarda dos bitstreams con sus programas. Nada pasa de una imagen a la otra |
| "Todo hardware agregado debe estar en el repositorio con su testbench" | Sí | `rtl/vigilante.v` con `tb/tb_vigilante.v` y `formal/vigilante.sby`; `rtl/wb_demo.v` con `tb/tb_wb_demo.v`. `SB_WARMBOOT` es una primitiva del chip |
| "Pueden modificar libremente el RTL, siempre que el procesador siga siendo Espino" | Sí | Las dos imágenes son Espino |
| "Deben usar el mismo programa para todas las series de tiempo" | En duda | Si las dos imágenes llevan el mismo `trade.s`, el programa es el mismo y lo que cambia en un relevo es el core. Si el principal llevara un programa que el core base no puede correr, después de un relevo la placa operaría con otro programa, quizás en rondas distintas. Hay que preguntarlo |
| Reconfigurar durante una ronda | En duda | El enunciado no lo prohíbe ni lo contempla. Dice que no es necesario dejar MISO en alta impedancia, no que esté prohibido, pero durante el corte la placa no responde |
| Regla del proyecto: el bitstream de competencia solo puede contener hardware que pasó por la maestra real | Se puede cumplir | Lo que se graba es el archivo de dos imágenes, y es ese archivo completo el que tiene que probarse el 26/11, incluido un relevo. Tiene que estar listo el 25/11 en la noche |
| Interruptores | No se usan en competencia | El disparo manual existe solo en la imagen de prueba. Usarlo entre rondas es cambiar de estrategia con un interruptor, que es la pregunta 9 pendiente |

Preguntas para el ayudante:

1. ¿Se permite que la placa se reconfigure sola durante una ronda, pasando a un segundo bitstream guardado en su misma flash, si el programa deja de responder? Durante unos 50 ms no contesta.
2. ¿Qué lee la maestra si la línea MISO de un grupo queda en alta impedancia? ¿Su entrada tiene pull-up, pull-down o nada? ¿Qué hace con un byte `0xFF` (acción 11) y con `0x00`?
3. ¿La maestra penaliza o marca como desconectado a un grupo que no responde por un rato?
4. "Mismo programa para todas las series": ¿se cumple si la flash trae dos bitstreams con el mismo `trade.s` y distinto core, y el segundo solo entra si el primero falla? ¿Y si el segundo trae un `trade.s` más simple?
5. ¿Entre rondas se corta la alimentación de las placas o se pueden reiniciar? Después de un relevo la placa queda en el respaldo hasta que se apague.
6. ¿La maestra envía precios de prueba antes de que parta una ronda? El vigilante los contaría.
7. ¿Cuántos ticks dura cada ronda? Con 2000 ticks la ronda 3 dura 0,2 s y un relevo se lleva la cuarta parte. (Es la pregunta 1 de la lista general.)
8. ¿Se puede apretar un interruptor de la placa entre rondas? (Es la pregunta 9 de la lista general.)

## 12. Qué habría que sacrificar para que quepa

Nada, sobre el core base o el segmentado. El vigilante con la primitiva agrega 9 celdas y ninguna BRAM: el SoC con core base queda en 1085 de 1280 y con el segmentado en 1010. En la flash, dos imágenes ocupan la mitad.

Si la imagen principal fuera un diseño que deja menos de unas 30 celdas libres, no hay un recorte que lo arregle: el vigilante con N = 1 es más chico como módulo (5 LUT y 3 flip-flops contra 8 y 4), pero integrado en el SoC no ahorra nada (1095 celdas contra 1085, sección 8.2). En ese caso el vigilante compite por las mismas celdas que la pieza principal y habría que medirlo sobre ese diseño, con sus 10 semillas, antes de contar con él.

Lo que sí se sacrifica no es área: es tiempo de ronda si hay un relevo (sección 7.3) y la libertad de que el programa no escriba `DECISION` en todos los ticks (sección 8.4).

## 13. Días de trabajo para llevarlo a calidad de competencia

| Tarea | Días |
|-------|------|
| Prueba de placa y medición del tiempo de reconfiguración (Nicolás, secciones 6 y 10) | 0,25 |
| Llevar el vigilante a `rtl/` apagado por defecto, con sus decisiones, su testbench y la prueba formal en la integración continua | 0,5 |
| Flujo de construcción del archivo de dos imágenes: Makefile, hashes, simulación de cada imagen desde su `.asc`, `icebram` sobre las dos | 0,75 |
| Gemelo digital: modelar el corte y el arranque del respaldo, y medir cuánto patrimonio cuesta un relevo en cada ronda | 0,5 |
| Equivalencia: principal con vigilante contra la referencia (20 000 ticks a los tres períodos) y relevo contra una referencia en Python | 0,5 |
| Prueba con la maestra el 26/11 y análisis de lo que se vea | 0,5 |
| Documento de estudio, preguntas de defensa y pasos en los checklist del 26/11 y del 1/12 | 0,5 |
| **Total** | **3,5** |

Es una estimación. No incluye lo que cueste la imagen principal misma.

## 14. Riesgos

1. **Nada se probó en la placa.** Que nextpnr ubique la primitiva no demuestra que el warm boot funcione en esta placa, con esta flash y con la flash dormida.
2. **El tiempo de reconfiguración es un valor típico, sin máximo.** En la ronda 3 cada milisegundo son 10 ticks.
3. **El nivel del pin suelto lo decide la maestra**, y también qué hace con `0xFF`. Si no tratara la acción 11 como mantener, el corte ejecutaría órdenes.
4. **Retardo entre BOOT y la salida del pin**, sin documentar. Importa solo si el programa escribe mantener como `0x00` (sección 7.2).
5. **Interpretación de las reglas** (sección 11). Si el ayudante dice que no, la pieza no puede ir a la competencia.
6. **Falso disparo** si el programa final no responde todos los ticks. Un falso disparo cuesta lo mismo que uno verdadero.
7. **Relevo en la ronda 3**: aun funcionando bien se pierde hasta la cuarta parte de la ronda, y además el respaldo liquida la posición. Puede salir peor que dejar el programa colgado con su última orden.
8. **Borrado de la flash.** Con el borrado por defecto de iceprog un archivo de dos imágenes puede quedar mal grabado si el sector es de 32 kB. La verificación de iceprog lo detecta. Se evita con `-b`.
9. **Cambio de programa de último minuto.** Con dos imágenes el camino de `icebram` es más largo y no está probado.
10. **El día de la competencia la placa queda en el respaldo después de un relevo.** Si entre rondas no se corta la alimentación, las rondas siguientes las juega el respaldo.

## 15. Veredicto

Según los criterios de corte de hardware, **pasa**: cabe junto al SPI (entre 9 y 30 celdas según la variante, ninguna BRAM; el SoC queda en 1085 de 1280 con el core base y en 1010 con el segmentado) y cierra a 25 MHz en las 10 semillas, con el core base y con el segmentado.

Recomendación: **edición de exhibición por ahora, y candidata a la edición de competencia con tres condiciones**, en este orden:

1. que la prueba de placa funcione y el tiempo medido sea del orden del documentado;
2. que el ayudante acepte la reconfiguración durante una ronda y aclare la regla del mismo programa;
3. que la imagen principal sea un diseño con algún riesgo de colgarse que el core base no tiene. Si la edición de competencia termina siendo el core base o el segmentado ya verificado, el vigilante protege de muy poco y agrega un modo de falla (el falso disparo).

Aunque no llegue a la competencia, la prueba de dos imágenes y el relevo son una pieza de exhibición barata y se pueden mostrar en la defensa con la placa en la mano.

Lo que se pierde si se descarta: la única red de seguridad que actúa sola dentro de una ronda. Sin ella el respaldo es grabar otro bitstream con el computador entre rondas.

## 16. Fuentes copiadas del repositorio y qué cambió

| Copia | Original | Cambio | Por qué |
|-------|----------|--------|---------|
| `soc/pochoco_soc.v` | `rtl/pochoco_soc.v` | Parámetros `Vigilante`, `VigN`, `VigDestino` y `VigBoton`; conexión de las tres salidas nuevas del esclavo SPI; instancia del vigilante y de `SB_WARMBOOT` dentro de un `generate` | Integrar el vigilante sin tocar `rtl/` |
| `soc/pochoco_spi_slave.v` | `rtl/pochoco_spi_slave.v` | Tres salidas: `byte_done_o`, `decision_wr_o` y `cs_active_o` | El vigilante necesita esas señales, que ya existían adentro |

Las dos copias conservan el encabezado de licencia y de autor del repositorio base. El resto del RTL se usa sin copiar: `scripts/armar_rtl.sh` arma en `build/rtl_vig/` una carpeta con `rtl/` y `rtl/espino_core/` del repositorio más estos archivos, y avisa si los originales cambiaron desde que se hicieron las copias. En la copia del SoC `Vigilante` vale 1 por defecto, para que el testbench oficial, que no pasa parámetros, pruebe el SoC con el vigilante.

`tb/tb_proyecto_4.sv` no se modificó. `scripts/chip_vlog_wb.py` llama a `tools/chip_vlog.py` y corrige además la forma en que `icebox_vlog` escribe la primitiva de warm boot.

## 17. Lo que no se verificó

- Nada en la placa: ni el salto, ni el tiempo, ni el nivel del pin, ni la flash.
- El modelo de la flash, su capacidad real y su sector de borrado.
- Que el respaldo arranque bien después de un warm boot con el reset de 4095 ciclos.
- La regrabación de una sola imagen con `iceprog -o` y el cambio de programa con `icebram` en un archivo de dos imágenes.
- `scripts/medir_uart.py` contra un puerto real: solo su cálculo, con marcas de tiempo sintéticas.
- El vigilante con un programa distinto de `trade.s` y de `cuelgue.s`.
- El costo en patrimonio de un relevo bajo el protocolo. La simulación del relevo usa un solo tramo de la serie de práctica y no sirve para eso.
- El vigilante integrado en un diseño distinto del SoC base y del segmentado (por ejemplo el barrel). El costo medido, entre 9 y 30 celdas según la variante, vale para estos dos.
- El vigilante reducido al disparo manual solo, sin la cuenta de precios.
- El arranque en frío con selección por pines (`icemulti -c`, pines CBSEL0 y CBSEL1): permitiría elegir la imagen al encender, sin vigilante y sin reconfigurar durante una ronda. No se revisó si esos pines están accesibles en la Go Board.
- Las variantes de frecuencia media y alta: se comprobó que icepack las acepta, no que la FPGA y la flash las soporten.
