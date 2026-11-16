# Anticipación: matriz de estrés, medidor del SPI y kit de contingencia

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio del paquete P8. Parte de la pregunta de fondo (qué puede ser distinto el día de la competencia) y llega al detalle de cada herramienta. Los documentos de uso son `docs/checklist_26nov.md`, `docs/checklist_1dic.md` y `docs/arbol_decision.md`.

## 1. La idea

El testbench del curso fija un SPI (SCLK de 1 MHz, 1 us antes del primer bit), una caja (10 000), una comisión (5) y tres períodos. La maestra real puede no ser exactamente así, y las reglas pueden cambiar el mismo día. Para cada cosa que puede cambiar hay que saber, antes del 1/12:

1. **Si el diseño sigue funcionando.** Es la matriz de estrés: cada celda es una combinación de parámetros y se exige lo mismo que en la puerta de simulación (bytes iguales a la referencia, ningún precio perdido, respuesta dentro del presupuesto).
2. **Cómo se sabe qué cambió.** Si la maestra usa otro SCLK, nadie lo va a anunciar. Para eso está el medidor.
3. **Qué se hace.** El árbol de decisión, y para un cambio de comisión, `tools/retune.py` con los juegos ya construidos.

## 2. La matriz de estrés

Tiene dos partes. La de la puerta de simulación corre por el RTL y ya existía: SCLK de 100 kHz a 1 MHz, tiempos de `CS_n`, reset con la maestra a mitad de un byte, rondas seguidas sin reset y series pegadas en 1 y 255 (`docs/mediciones/estres_base.txt` para R0, 60 de 60; `docs/mediciones/fondo/r1/estres.txt` y `r2/estres.txt`, 56 de 56).

La que agrega P8 (`make p8-matriz`, `docs/mediciones/p8/matriz.txt`) corre en el gemelo, que es exacto al ciclo y está validado contra el RTL de R0 (`make cosim`) y de R1 (`make cosim-barrel`). En 10 segundos cubre:

| Dimensión | Celdas | Resultado |
|-----------|--------|-----------|
| A. Período, de 10 ms a 11,5 us | 9 | R0 pasa en todas. R1 hasta 30 us; el mínimo exacto es 26,94 us (`sclk_minimo.txt`) |
| B. SCLK de 100 kHz a 1 MHz, en los tres períodos | 15 | R0 pasa en todas. R1 falla solo con 100 kHz a 0,1 ms: el límite documentado |
| C. Rondas de 500, 2 000, 20 000 y 200 000 ticks | 4 | Pasan los tres peldaños |
| D. Comisión de 0 a 50 y caja de 1 000 a 100 000 | 15 por conjunto | Ver abajo |

En A y B cuentan las celdas que dejan al menos 600 ciclos entre transacciones, igual que en la matriz de la puerta: todas pasan.

**R2 en el gemelo.** El gemelo no modela el vigilante. Pero el vigilante solo se dispara si llegan 5 precios sin ninguna escritura en `DECISION`, y en todas las celdas R1 escribe una vez por cada precio, incluso en las que responde tarde. Por eso R2 se deduce de R1. La matriz de la puerta lo confirma por el RTL: el contador del vigilante nunca pasó de 1.

**La parte económica (D).** El programa no lleva contabilidad, así que sus decisiones no dependen de la caja ni de la comisión: lo que cambia es cuánto cuesta operar. Con las referencias se mide el patrimonio final dividido por la caja inicial, en los 10 bloques de la práctica y en 280 series de las 14 familias. Algunos valores de la práctica:

| Comisión | Caja | Media | Peor bloque | Comprar y mantener | Supera a comprar y mantener |
|----------|------|-------|-------------|--------------------|-----------------------------|
| 5 | 10 000 | 1,104 | 0,962 | 0,975 | 9 de 10 bloques |
| 5 | 1 000 | 0,989 | 0,805 | 0,975 | 7 de 10 |
| 20 | 10 000 | 1,030 | 0,852 | 0,973 | 7 de 10 |
| 20 | 1 000 | 0,590 | 0,243 | 0,959 | 0 de 10 |
| 50 | 10 000 | 0,897 | 0,703 | 0,971 | 4 de 10 |

Con caja chica la comisión pesa mucho más: con 1 000 y "comprar 63" la maestra compra unas 6 acciones, y cada orden de 5 cuesta lo mismo que con 10 000. Con caja de 100 000 pasa lo contrario: "comprar 63" se repite cada tick hasta gastar la caja, porque la maestra ejecuta lo que encuentra en `DECISION` en cada tick. El diseño sigue funcionando, con más órdenes.

## 3. El medidor del SPI

`rtl/medidor/medidor_spi.v` es un bitstream aparte, sin el SoC. Escucha `SCLK`, `MOSI` y `CS_n`, los sincroniza con dos flip-flops como `pochoco_spi_slave`, y mide en ciclos de 40 ns: el período mínimo y máximo de SCLK, el período entre precios, la duración de `CS_n` en bajo, el tiempo hasta el primer flanco, el tiempo libre mínimo entre transacciones y la cantidad de transacciones. Las muestra en los 7 segmentos; los botones eligen la medida, SW3 borra y SW4 muestra el byte alto. LED4 se enciende si alguna transacción no tuvo 8 flancos.

Responde `0x00` por MISO, que es mantener: la maestra ve un grupo que no opera.

Por qué hace falta: R1 necesita hasta 444 ciclos entre el fin de una transacción y la siguiente. Con SCLK de 100 kHz y período de 0,1 ms quedan 237. El testbench del curso usa 1 MHz, pero nada garantiza que la maestra real también. El medidor lo dice en un minuto y sin instrumentos.

Pruebas (`make medidor`, `docs/mediciones/medidor_spi.txt`): un testbench con las tres rondas del curso, SCLK de 100 kHz y 115 kHz y tiempos de `CS_n` cortos y largos, que lee las medidas por los 7 segmentos apretando los botones como en la placa (66 comprobaciones); cuatro errores puestos a propósito, los cuatro detectados; 611 de 1280 celdas, 10 de 10 semillas a 25 MHz con mínima de 112,5 MHz; y el mismo testbench sobre el bitstream ruteado, simulado por los pines.

## 4. El kit de contingencia

### 4.1 Moldes

`icebram` cambia el contenido de una BRAM en un bitstream ya ruteado, sin sintetizar. Para ubicar la memoria busca lo que había, y con el contenido de verdad no siempre puede (muchos ceros). Por eso se sintetiza un **molde**: el mismo diseño con la memoria llena de un patrón al azar (`docs/tabla_vigilante.md`, sección 3.1). R1 y R2 tenían sus moldes desde P5. P8 agrega el de R0 (`make r0-molde`): se construye desde el commit de R0, como `make r0-reproducir`, y se comprueba que el molde con `sw/trade.hex` puesto con `icebram` es R0 byte por byte (0,10 s).

### 4.2 `tools/retune.py`

Recibe la comisión, la caja y el largo de las rondas.

1. **Busca umbrales.** Evalúa 77 pares (entra, sale) de `max_media` en los bloques de la práctica y en 80 series de las cuatro familias plausibles, con las reglas nuevas. Acepta otros umbrales solo si suben la media en más de 0,2 % sin bajar el percentil 5 ni el peor bloque de la práctica: es el principio 4 del proyecto (una pieza cambia la forma de operar solo si mejora la media y el peor caso). Sin esa condición, con las reglas publicadas habría elegido entrar a 1 unidad y salir a 2: más media, pero peor percentil 5.
2. **Arma los bitstreams** con `icebram` sobre los tres moldes: R0 con `sw/trade.s` ensamblado con `-D UMBRAL_COMPRA` y `-D UMBRAL_VENTA`, R1 y R2 con otra tabla, y la imagen múltiple de R2 con el R0 nuevo de respaldo. Tarda 0,3 s.
3. **Equivalencia rápida** en el gemelo: la práctica y una serie de cada familia plausible contra las referencias con los parámetros nuevos.
4. Con `--simular`, **simula los `.asc` por los pines** (unos 40 minutos, en paralelo).

Control (`make retune-control`, en la integración continua): con comisión 5 y caja 10 000 deja los umbrales actuales, y los cuatro `.bin` que arma son los de `bitstreams/`, byte por byte.

Qué elige (`docs/arbol_decision.md`, sección 2): con comisión de 0 a 10, los actuales para cualquier caja. Con 20, (7, 4) para caja 10 000 y (16, 4) para 1 000. Con 50, (16, 4) o (16, 3): casi no operar.

### 4.3 Juegos preconstruidos

`make contingencia` construye y simula los juegos de la tabla del árbol y los deja en `bitstreams/contingencia/<umbrales>/` con su `SHA256SUMS`. El 1/12, si anuncian comisión de 20 o 50, se graba uno de esos sin esperar la simulación.

## 5. Preguntas de defensa

1. **¿Qué pasa si la maestra usa un SCLK más lento?** Hasta 110 kHz en la ronda 3, R1 responde a tiempo; bajo eso compite R0, que responde en 44 ciclos. El árbol usa 115 kHz para dejar margen. Se mide con el medidor el 26/11.
2. **¿Y si cambian la comisión?** Las decisiones no cambian solas, porque el programa no lleva contabilidad. `retune` busca umbrales nuevos con el mismo protocolo, y para comisión de 20 y 50 los bitstreams ya están construidos y simulados.
3. **¿Por qué no se ajusta solo, en el chip?** Porque el programa no sabe la comisión: no la recibe por SPI. Ajustarla en vivo exigiría inferirla del patrimonio, que el chip no ve.
4. **¿Cómo saben que un bitstream hecho con `icebram` es correcto?** Por el control: con los parámetros de siempre, `icebram` sobre el molde da los bitstreams guardados byte por byte. Y cada juego nuevo se simula por los pines antes de guardarse.
5. **¿Qué cubre el gemelo que no cubra el RTL?** Lo mismo, más rápido: 10 segundos para las 28 celdas de cada peldaño, incluida una ronda de 200 000 ticks que por el RTL tomaría horas. Su exactitud está probada contra el RTL en 21 configuraciones.
