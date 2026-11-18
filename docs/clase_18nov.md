# Clase del 18/11: registrar la serie de la maestra

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

**Estado de los bitstreams para hoy (se actualiza en la madrugada del 18/11):**

| Archivo | Qué es | Estado |
|---------|--------|--------|
| `registrador.bin` | Registra la serie de la maestra por la UART | Listo |
| `r0_cotas.bin` | R0 con la regla nueva ("espera", banda 60) | Listo: pasó su puerta de simulación |
| `r1_cotas.bin`, `r2_cotas_multi.bin` | R1 y R2 con la regla nueva (barrel, la regla en el hilo 0) | Listos: pasaron su puerta de simulación |
| `r1_fondo.bin`, `r2_multi.bin` | R1 y R2 anteriores (el fondo con `max_media`) | Alternativa: **mismo hardware** que los nuevos, así que probarlos con la maestra valida el hardware igual |
| `r0_base_max_media.bin` | R0 anterior | Alternativa de `r0_cotas.bin`, mismo hardware |

El profesor lleva la FPGA maestra a clases. Objetivo principal: grabar la serie que manda la maestra con el registrador (`docs/registrador.md`). Después, pasar por la maestra los peldaños con la regla nueva (sección 4).

Todo se corre en WSL desde la carpeta del proyecto, `~/proyectos/Proyecto4_Arquitectura_De_Computadores` (`main` tiene el registrador y su herramienta desde el 17/11 en la noche). Antes de salir, en WSL:

```
cd ~/proyectos/Proyecto4_Arquitectura_De_Computadores
git log --oneline -1                                  # anotar el commit
cd bitstreams && sha256sum -c SHA256SUMS --ignore-missing | grep -E 'registrador|medidor|r0_|r1_|r2_' ; cd ..
python3 tools/registrador.py --prueba                 # sin placa: tiene que terminar en "RESULTADO prueba PASS"
```

## 1. Esta noche: la Go Board dentro de WSL con usbipd

WSL no ve los USB de Windows por su cuenta. `usbipd-win` los pasa. Si el 16/11 ya funcionó `tools/medir_relevo.py /dev/ttyUSB1`, esto ya está instalado y basta con los pasos 3, 5 y 6.

1. **Instalar usbipd-win** (una sola vez). En PowerShell como administrador:
   ```
   winget install --interactive --exact dorssel.usbipd-win
   ```
   Cerrar y abrir PowerShell. `usbipd --version` tiene que responder.
2. **Conectar la Go Board** por USB al computador.
3. **Buscar su identificador.** En PowerShell (como administrador la primera vez):
   ```
   usbipd list
   ```
   La Go Board aparece como `0403:6010` ("USB Serial Converter A, USB Serial Converter B"). Anotar su `BUSID`, por ejemplo `2-3`.
4. **Compartirla** (una sola vez por placa, como administrador):
   ```
   usbipd bind --busid 2-3
   ```
5. **Pasarla a WSL** (cada vez que se conecta la placa; con WSL abierto):
   ```
   usbipd attach --wsl --busid 2-3
   ```
   Con `--auto-attach` al final, la vuelve a pasar sola cada vez que se desconecta y se conecta el USB; la ventana de PowerShell queda ocupada mientras tanto. Conviene en clases, porque la sección 3 pide desconectar y conectar el USB.
6. **Comprobar en WSL**:
   ```
   ls -l /dev/ttyUSB*
   ```
   Tienen que aparecer `/dev/ttyUSB0` (la interfaz que usa `iceprog`) y `/dev/ttyUSB1` (la UART). Si dice "Permission denied" al usarlos: `sudo usermod -aG dialout $USER` y, en PowerShell, `wsl --shutdown` y abrir WSL de nuevo (una sola vez). Para salir del paso en clases: `sudo chmod a+rw /dev/ttyUSB1`.
7. **Probar el puerto sin maestra** (5 segundos, con el registrador grabado):
   ```
   iceprog bitstreams/registrador.bin
   python3 tools/registrador.py /dev/ttyUSB1 -o build/maestra/prueba_casa --segundos 5
   ```
   Debe decir "Registros: 0" sin errores. Si el puerto no acepta 1 Mbaud, avisar: hay que construir el bitstream a 921 600 baudios (`docs/registrador.md`, sección 5).

Si después de `iceprog` desaparece `/dev/ttyUSB1`, en PowerShell: `usbipd detach --busid 2-3` y `usbipd attach --wsl --busid 2-3`.

## 2. En clases: registrar la serie, uno por uno

1. **Conectar a la maestra** según `docs/checklist_26nov.md`, sección 2: la tierra primero, después `CS_n` al PMOD 1, `MOSI` al 2, `MISO` al 3 y `SCLK` al 4. Confirmar los números con el ayudante antes de conectar. No unir los 3,3 V.
2. **Grabar el registrador**:
   ```
   cd ~/proyectos/Proyecto4_Arquitectura_De_Computadores
   sha256sum bitstreams/registrador.bin        # anotar; tiene que coincidir con bitstreams/SHA256SUMS
   iceprog bitstreams/registrador.bin
   ```
   Al terminar ("VERIFY OK"): `00` en los 7 segmentos y los LED apagados.
3. **Desconectar y conectar el USB** con la maestra encendida (las entradas del SPI no tienen pull-up), y si no se usó `--auto-attach`, repetir `usbipd attach --wsl --busid 2-3`. `ls /dev/ttyUSB*`.
4. **Empezar a leer antes de que la maestra empiece la ronda**:
   ```
   mkdir -p build/maestra
   python3 tools/registrador.py /dev/ttyUSB1 -o build/maestra/clase_ronda1
   ```
   Cada 2 segundos imprime cuántos registros lleva. Los bytes se guardan en disco a medida que llegan (`build/maestra/clase_ronda1_crudo.bin`).
5. **Pedir la ronda.** Mirar que la cuenta avance. LED1 cambia con cada precio.
6. **Al terminar la ronda, Ctrl+C.** Anotar lo que imprime:
   - Registros (la cantidad de precios de la ronda).
   - **Perdidos: tiene que ser 0.**
   - Transacciones con error y bytes fuera de un registro.
   - Período mínimo, medio y máximo entre precios.
   - Comprobar que los 7 segmentos muestran la cuenta que dice el programa (con SW4, el byte alto).
7. **Apretar SW3** (borra la cuenta) y repetir los pasos 4 a 6 para cada ronda que corra la maestra, con otro nombre: `clase_ronda2`, `clase_ronda3`, etc.
8. **Al final, copiar todo fuera de WSL** por si acaso:
   ```
   mkdir -p /mnt/d/Descargas/maestra_18nov && cp build/maestra/clase_* /mnt/d/Descargas/maestra_18nov/
   ```

Qué deja cada ronda:

| Archivo | Contenido |
|---------|-----------|
| `clase_rondaN_serie.csv` | `tick,price`, el mismo formato de `data/practica_meta.csv`: sirve tal cual para el testbench, el gemelo y `ref/` |
| `clase_rondaN_detalle.csv` | Por precio: secuencia, precio, la decisión que leyó la maestra, error, período medido por la FPGA (resolución de 5,12 µs, hasta 10 480 µs) y hora de llegada al computador (resolución de USB, unos ms; sirve si la maestra va más lento que 10 ms por precio) |
| `clase_rondaN_crudo.bin` | Los bytes tal como llegaron. Si el programa se cae: `python3 tools/registrador.py --archivo build/maestra/clase_rondaN_crudo.bin -o build/maestra/clase_rondaN` |

La maestra ve a nuestro grupo manteniendo durante toda la ronda (el registrador responde `0x00`).

## 3. Si no se alcanza a conectar la UART

Sin la UART la serie no se puede reconstruir: el registrador no guarda nada en la placa. Lo que sí se puede anotar:

1. **Con el registrador grabado igual**, al final de cada ronda: el número de los 7 segmentos (byte bajo) y, con SW4 apretado, el byte alto. Es la cantidad de precios de la ronda. LED3 encendido: hubo transacciones con un número de bits distinto de 8.
2. **Mejor, con el medidor** (no necesita la UART): `iceprog bitstreams/medidor_spi.bin` y seguir `docs/checklist_26nov.md`, sección 3. Anotar las ocho medidas de cada ronda (byte bajo y byte alto): período de SCLK, período entre precios, duración de `CS_n`, tiempo libre mínimo y cantidad de transacciones. Y si LED4 se encendió.
3. **De la pantalla de la maestra**: el patrimonio final de cada grupo, el número de ticks de cada ronda y cualquier dato de la serie que muestre (primer y último precio, mínimo y máximo). Una foto de la pantalla por ronda.
4. **Preguntas al ayudante** (las respuestas cambian la regla que compite, `docs/cotas.md`):
   - ¿Cada ronda se normaliza por separado, de modo que su mínimo es exactamente 100 y su máximo exactamente 255? ¿O se normaliza un período más largo y la ronda es un trozo?
   - ¿Cuántos ticks tiene cada ronda? ¿Las tres rondas usan la misma serie o series distintas?
   - ¿Caja 10 000 y comisión 5 en la competencia?
   - ¿La serie de clases es `practica_meta.csv` u otra?
   - ¿Se puede repetir la prueba con la maestra antes del 1/12?

## 4. Orden para grabar con la maestra y qué se ve en cada uno

En este orden, cada uno con las rondas que permita la maestra. Antes de cada uno: `sha256sum bitstreams/ARCHIVO` y anotarlo. Después de grabar, desconectar y conectar el USB con la maestra conectada (sección 2, paso 3).

1. **`registrador.bin`** (sección 2). 7 segmentos: la cuenta de precios (con SW4, el byte alto). LED1 cambia con cada precio, LED2 encendido mientras la UART transmite, LED3 si hubo una transacción con error, LED4 si se perdió un registro. La maestra ve a nuestro grupo manteniendo.
2. **`r0_cotas.bin`** (`iceprog bitstreams/r0_cotas.bin`). R0 no escribe telemetría: **los 7 segmentos quedan en `00` y los LED apagados todo el tiempo**. Lo que importa está en la pantalla de la maestra:
   - Si la ronda toca el 100, el grupo compra en ese momento; si después toca el 255, vende. Con la banda, después de ver los dos, compra bajo 160 y vende sobre 195.
   - **Si la ronda termina con exactamente 10 000 y ninguna orden, la ronda no tocó el 100.** Eso responde en parte la pregunta de la normalización: si pasa en todas las rondas, lo más probable es que las rondas sean trozos de una serie normalizada más larga (`docs/cotas.md`, sección 5.3). Anotarlo con el número de ticks de la ronda.
   - Anotar el patrimonio final de cada ronda.
3. **`r1_cotas.bin`** (`iceprog bitstreams/r1_cotas.bin`; si algo falla, `r1_fondo.bin`, que tiene el mismo hardware). Telemetría: en los ticks pares los 7 segmentos muestran `63` si el byte es "comprar 63" y `00` si no; en los impares, **LED1** es el latido (cambia cada 1024 precios: unas 10 veces por segundo a 0,1 ms, cada segundo a 1 ms, cada 10 segundos a 10 ms), **LED2** se enciende al ver el 100, **LED3** al ver el 255 y **LED4** mientras está adentro. Con `r1_fondo.bin` (el anterior) los LED son los votos de los gestores y el latido.
4. **`r2_cotas_multi.bin`** con `iceprog -b bitstreams/r2_cotas_multi.bin` (si algo falla, `r2_multi.bin`). Lo mismo que R1. **Si la telemetría desaparece a mitad de una ronda** (LED1 deja de cambiar y queda todo en `00` y apagado), el vigilante cambió a la imagen de R0: anotar en qué ronda y en qué momento.

Para comparar con lo que muestra la maestra, si la serie quedó registrada: `python3 ref/trader.py build/maestra/clase_rondaN_serie.csv --periodo-ns PERIODO` da el patrimonio que debe obtener R0 (y R1 y R2, que deciden igual).

