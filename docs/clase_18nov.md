# Clase del 18/11: registrar la serie de la maestra

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

El profesor lleva la FPGA maestra a clases. Objetivo principal: grabar la serie que manda la maestra con el registrador (`docs/registrador.md`) para tener precios reales del formato de la competencia. Objetivo secundario, si hay tiempo: medir el SPI real y pasar R0, R1 y R2 por la maestra (`docs/checklist_26nov.md`, secciones 3 y 4).

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

## 4. Si sobra tiempo: el hardware de la competencia con la maestra

La regla del proyecto es que el bitstream de la competencia solo puede tener hardware que pasó por la maestra real. El algoritmo va a cambiar con la serie nueva, pero el hardware no: probar hoy R0, R1 y R2 con la maestra valida el hardware aunque el programa que corran sea `max_media`. En orden, cada uno con las rondas que permita la maestra:

1. `iceprog bitstreams/r0_base_max_media.bin`
2. `iceprog bitstreams/r1_fondo.bin`
3. `iceprog -b bitstreams/r2_multi.bin`

Para cada uno: sha256 del archivo, patrimonio que muestra la maestra en cada ronda, y si nuestro grupo dejó de operar en algún momento. Detalle en `docs/checklist_26nov.md`, sección 4.
