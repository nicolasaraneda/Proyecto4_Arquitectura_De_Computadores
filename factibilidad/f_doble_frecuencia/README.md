# Pieza F: doble frecuencia sin PLL

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz. Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Tramo de factibilidad. Nada de esta carpeta está integrado en `main` ni en el flujo del repositorio.

## 1. Qué es y qué se construyó

El encapsulado VQ100 de la HX1K no tiene PLL (`docs/mediciones/pll_nextpnr.txt`). La pregunta es si se puede hacer el doble de trabajo por cada período de 40 ns del oscilador sin PLL, cómo se restringe eso en nextpnr y cuánto margen real queda.

Se construyó y midió:

- `rtl/duplicador_reloj.v`: duplicador por lógica. Una cadena de N LUT retrasa el reloj, un XOR compara el reloj con su copia retrasada y la salida va a un buffer global `SB_GB`. Trae un modelo de retardo para simulación.
- `rtl/pochoco_soc_x2.v`: copia de `rtl/pochoco_soc.v` con un solo cambio, el reloj interno sale del duplicador. Sirve para el Espino base y para el segmentado. El nombre del módulo, sus puertos, `MemFile` y `u_spi` no cambian.
- `scripts/sta_icestorm.py`: análisis de tiempos propio sobre el diseño ya ruteado, con la base de tiempos de icestorm. Hizo falta porque ni nextpnr ni icetime entregan el ancho del pulso, las tres esquinas de la base ni las rutas separadas por flanco. Está comparado con nextpnr y con icetime (sección 7.6).
- Mediciones de la cadena (largo, semilla y ubicación), de las formas de restringir el reloj en nextpnr, y del SoC completo con el reloj doblado en 10 semillas.
- Dos testbenches del duplicador y de la prueba de placa, y una prueba de humo del SoC doblado con el testbench oficial sin modificar.
- `rtl/placa_x2.v` y su bitstream: prueba para la Go Board, con un contador en cada reloj en los displays y un oscilador en anillo que mide el retardo real de las LUT sin osciloscopio.

## 2. Resultado en una tabla

| | Espino base, reloj doblado | Espino segmentado, reloj doblado | Espino segmentado a 25 MHz (dos flancos, lo que ya existe) |
|-|----------------------------|----------------------------------|-----------------------------------------------------------|
| Celdas lógicas y BRAM | 1085 de 1280 y 12 de 16 | 1004 de 1280 y 12 de 16 | 990 y 12 |
| Costo del duplicador | 9 celdas (8 LUT y el XOR). En el SoC se miden 15 más | 7 celdas (6 LUT y el XOR). En el SoC se miden 14 más | no usa |
| Fmax de nextpnr en 10 semillas (MHz) | 44,51, 45,70 y 47,78 | 51,66, 54,66 y 56,63 | 50,91, 53,97 y 55,41 |
| Cierran a 50 MHz según nextpnr | 0 de 10 | 10 de 10 | no aplica: cierran 10 de 10 a 25 MHz |
| Cierran con ciclo de trabajo de 50 % exacto, esquina máxima | 0 de 10 | 10 de 10, peor holgura 0,10 ns | |
| Cierran con ciclo de trabajo de 45 a 55 %, esquina máxima | 0 de 10 | 1 de 10, peor holgura -1,90 ns | 10 de 10: tolera de 6,7 a 79,4 % |
| Lo mismo en la esquina típica de la base | 0 de 10 | 10 de 10 | |
| Ganancia si funcionara | 2 veces más ciclos por tick | 2 veces sobre el segmentado | 1,74 veces más instrucciones por segundo que el base (medido, `docs/mediciones/espino_segmentado.txt`) |

Lo que sale de ahí:

1. **El duplicador funciona como circuito y cuesta poco.** Son 7 o 9 celdas y el buffer global que ya ocupaba el reloj. En el SoC completo la diferencia medida es de 14 y 15 celdas, que incluye el ruido de unas 10 celdas entre síntesis que ya conocíamos (decisión T6).
2. **El Espino base no cierra.** Su ruta crítica mide entre 20,9 y 22,9 ns y el período del reloj doblado es de 20 ns en el mejor caso.
3. **El segmentado cierra según nextpnr, pero sin margen real.** nextpnr analiza un reloj ideal de 50 MHz. El reloj doblado tiene períodos que alternan según el ciclo de trabajo del oscilador: con 45 % el período corto es de 17,73 ns, que equivale a cerrar a 56,4 MHz. Solo 1 de 10 semillas lo logra, por 0,13 ns, y eso sin descontar el skew de la red global (hasta 0,727 ns).
4. **No aporta patrimonio.** El programa usa 44 ciclos de los 2 262 de la ronda más corta. Con el reloj doblado serían 44 de 4 525.
5. **La forma que sí sirve ya está hecha.** Usar los dos flancos del reloj de 25 MHz en rutas elegidas es lo que hace el Espino segmentado: cierra en las 10 semillas, nextpnr lo analiza bien y tolera cualquier ciclo de trabajo razonable.

Veredicto: **descartada de la edición de competencia. Pasa a la edición de exhibición como resultado negativo medido.** El detalle está en la sección 15.

## 3. Cómo se reproduce

Todo se corre con `make` desde esta carpeta o con `make -C factibilidad/f_doble_frecuencia OBJETIVO` desde la raíz. Los productos intermedios quedan en `build/`, que git ignora. Cada objetivo regenera un archivo de `mediciones/`.

| Comando | Qué mide | Salida | Demora |
|---------|----------|--------|--------|
| `make sintesis` | Qué flujos de Yosys conservan la cadena | `mediciones/sintesis_cadena.txt` | 10 s |
| `make cadena` | Retardo de la cadena: 9 largos, 2 formas, 4 ubicaciones, 10 semillas (720 corridas) | `mediciones/cadena.txt` | 3 min |
| `make tb` | Testbench del duplicador en las tres esquinas y tres ciclos de trabajo, más dos controles negativos | `mediciones/tb_duplicador.txt` | 1 s |
| `make restricciones` | `--freq`, `ctx.addClock` y SDC en nextpnr, y comparación con icetime | `mediciones/restricciones.txt` | 20 s |
| `make soc` | SoC base y segmentado, con y sin duplicador, 10 semillas y dos objetivos | `mediciones/soc_x2.txt` | 2 min |
| `make validar` | El análisis propio contra nextpnr e icetime | `mediciones/validacion_sta.txt` | 10 s |
| `make opciones` | Opciones de nextpnr que cambian la ubicación o el ruteo | `mediciones/opciones_nextpnr.txt` | unos 10 min |
| `make humo` | Testbench oficial sin modificar sobre el SoC doblado, y efecto de la fase de la maestra | `mediciones/humo_soc_x2.txt`, `mediciones/humo_fase.txt` | 5 a 10 min |
| `make margen` | Margen real, comparación con los dos flancos y presupuesto de ciclos | `mediciones/margen.txt` | 1 s |
| `make placa` | Prueba para la Go Board: simulación, bitstream y valores esperados | `mediciones/placa_x2.txt`, `placa/placa_x2.bin` | 15 s |
| `make todo` | Todo lo anterior en orden | | 25 a 35 min |
| `make hoja PDF=ruta/DS1040.pdf` | Los datos de la hoja de datos que se citan (pulso mínimo y skew de la red global) | `mediciones/hoja_datos.txt` | 1 s |

`make tb` necesita antes `make cadena`. `make validar`, `make opciones` y `make margen` necesitan antes `make soc`. `make margen` usa además el resultado de `make humo` si existe. `make hoja` no entra en `make todo` porque la hoja de datos no está en el repositorio: hay que bajarla y pasar su ruta.

El 14/11 se volvió a correr todo desde cero, objetivo por objetivo, incluidas las 720 corridas de `make cadena`, las 80 de `make soc` y las 70 de `make opciones`. Los doce archivos de `mediciones/` y el bitstream de la prueba de placa salieron idénticos byte a byte a los guardados. La única salida que cambió respecto de la primera corrida del 13/11 es `restricciones.txt`, en dos cifras (la frecuencia máxima de `clk2x` y la ruta de pin a pin), porque la prueba de placa se editó después. Lo único que depende de la carga de la máquina son las corridas con tiempo límite: las que nextpnr no termina de rutear en 60 s en `make cadena` y en 300 s en `make opciones`. En la repetición se cortaron las mismas.

Herramientas: OSS CAD Suite del 2026-09-06 (Yosys 0.68+195, nextpnr-0.11.1-19-g8dbcee5c, Icarus Verilog 14.0 de desarrollo, icetime e icepack de icestorm). Python solo con la biblioteca estándar.

## 4. Dos formas de hacer el doble de trabajo por período

### 4.1. Duplicador por lógica

```
            +-- cadena de N LUT --+
  i_Clk ----+                     +--> XOR --> SB_GB --> clk (reloj doblado)
            +---------------------+
```

Cada flanco de `i_Clk`, de subida o de bajada, produce un pulso que dura lo que demora la cadena. La salida tiene dos flancos de subida por período de 40 ns. Tres cosas quedan fijadas por construcción y son las que deciden el margen:

- **Los períodos alternan.** Un flanco de subida del reloj doblado nace del flanco de subida del oscilador y el siguiente nace del de bajada. Si el oscilador pasa 18 ns en alto y 22 ns en bajo (ciclo de trabajo de 45 %), el reloj doblado tiene períodos de 18 y 22 ns. Toda la lógica tiene que caber en el corto.
- **El tiempo en alto es el retardo de la cadena**, no medio período. Con 8 LUT son unos 7 ns de cada 20.
- **El retardo de la cadena no afecta al período.** Los flancos de subida salen por el camino directo al XOR. La cadena solo define cuándo baja el pulso. Por eso el Espino base, que usa solo flancos de subida, es insensible al largo de la cadena mientras el pulso no sea demasiado angosto ni demasiado ancho. El segmentado sí depende, porque usa también el flanco de bajada.

Qué gana: el RTL del SoC no se toca. El mismo core, el mismo esclavo SPI y las mismas memorias corren con el doble de flancos.

### 4.2. Los dos flancos del reloj de 25 MHz en rutas elegidas

Es lo que hace el Espino segmentado (`docs/espino_segmentado.md`, decisiones T33 y T39): la memoria de instrucciones se lee en el flanco de bajada, así la instrucción está lista antes del siguiente flanco de subida y una instrucción de ALU cuesta 1 ciclo en vez de 2. Es literalmente hacer el doble de trabajo en 40 ns, pero solo donde hacía falta.

Qué gana: no hay reloj nuevo ni cadena. nextpnr conoce el reloj, analiza las rutas de medio ciclo con medio período (T39) y el diseño cierra en las 10 semillas con el doble de la frecuencia pedida.

### 4.3. Comparación

Medido en `mediciones/margen.txt` (punto 3) y `mediciones/soc_x2.txt`. La columna de los dos flancos es el SoC segmentado sin duplicador (`seg_x1`).

| | Duplicador por lógica | Dos flancos a 25 MHz |
|-|-----------------------|----------------------|
| Qué hay que rediseñar | Nada del SoC | El core (ya está hecho y verificado) |
| Ganancia medida o nominal | 2,00 veces más ciclos, nominal | 1,74 veces más instrucciones por segundo con el mix de la clase, medido |
| Ruta de un período | Tiene que caber en 17,73 ns con 45 % | Dispone de 40 ns. Usa 18,05 a 19,30 ns: sobran 20,7 ns o más |
| Rutas de medio ciclo | De subida a bajada disponen solo del ancho del pulso (4 a 5,9 ns) | De subida a bajada usan hasta 2,45 ns de 20. De bajada a subida, hasta 8,00 ns de 20 |
| Ciclo de trabajo del oscilador que tolera, esquina máxima | Base: ninguno. Segmentado: entre 44,7 a 56,6 % la mejor semilla y 49,8 a 51,5 % la peor | De 6,7 a 79,4 % en las 10 semillas |
| Lo que ve nextpnr | Un reloj ideal de 50 MHz. No ve los períodos alternados ni el ancho del pulso | Lo que hay |
| Variación con proceso, voltaje y temperatura | El pulso cambia con el chip. Las holguras son de décimas de ns | Las holguras son de 12 ns o más |

Las dos se pueden combinar (segmentado con reloj doblado, `seg_x2`). Es la única variante con duplicador que cierra según nextpnr, y es la que se analiza en la sección 7.

Otras formas que se descartaron sin construir: un oscilador en anillo como reloj rápido (su frecuencia cambia cerca de 25 % entre esquinas y no guarda relación con el reloj de 25 MHz), y flip-flops de doble flanco armados con dos flip-flops y un multiplexor (duplican los registros y no hay celdas para eso).

## 5. La cadena de retardo

### 5.1. Cómo evitar que las herramientas se la lleven

`mediciones/sintesis_cadena.txt`, con una cadena de 8 LUT:

| Forma de escribirla | Qué queda después de `synth_ice40` |
|---------------------|------------------------------------|
| Primitivas `SB_LUT4` instanciadas, con o sin `keep`, flujo por defecto, `-relut` o `-abc9` | Las 8 LUT y el XOR |
| Asignaciones comunes (`assign d[i+1] = d[i]`) | 0 de 8. La entrada del buffer global queda en la constante 0: el reloj doblado desaparece |

Instanciar primitivas basta para que Yosys no optimice la cadena. El atributo `keep` se deja como seguro. En nextpnr hay dos cosas más:

- **Ubicación.** nextpnr mueve las LUT si no se fijan. `scripts/fijar_cadena.py` se pasa con `--pre-pack` y pone el atributo `BEL` en cada LUT, 8 por bloque lógico. Después de empaquetar quedan 9 celdas lógicas en fila (comprobado en el mismo archivo).
- **Entrada física de la LUT.** nextpnr elige por cuál de las cuatro entradas entra la señal, y cada entrada tiene un retardo distinto (de 0,32 a 0,45 ns en la esquina máxima, tabla al final de `mediciones/cadena.txt`). Eso no se puede fijar. Se probó una segunda forma de la cadena (`Modo = 1`), con las cuatro entradas conectadas a la misma señal y compuertas AND y OR alternadas, para que el retardo no dependa de esa elección.

### 5.2. Cuánto retarda y cuánto varía

`mediciones/cadena.txt`. Ancho del pulso en ns, mínimo y máximo entre 10 semillas, con la cadena de una entrada por LUT (`Modo = 0`):

| N | Ubicación | Según nextpnr | icestorm, esquina máxima | icestorm, esquina mínima |
|---|-----------|---------------|--------------------------|--------------------------|
| 2 | libre | 2,02 a 3,09 | 1,40 a 2,86 | 1,12 a 2,30 |
| 8 | libre | 8,24 a 8,98 | 6,55 a 8,37 | 5,27 a 6,73 |
| 8 | fija en X1/Y8 | 8,24 a 8,24 | 6,57 a 8,02 | 5,28 a 6,44 |
| 8 | fija en X6/Y9 | 8,24 a 8,61 | 6,89 a 8,28 | 5,54 a 6,66 |
| 8 | fija en X12/Y2 | 8,24 a 8,24 | 6,82 a 7,95 | 5,49 a 6,39 |
| 16 | fija en X1/Y8 | 15,83 a 15,83 | 12,67 a 15,13 | 10,19 a 12,17 |

Los rangos de icestorm incluyen el pulso que nace del flanco de subida y el que nace del de bajada, que es cerca de 10 % más angosto.

- **Retardo por LUT:** entre 0,95 y 1,01 ns en la esquina máxima, contando la LUT y su tramo de interconexión.
- **Lo que estima nextpnr:** 1,04 ns por LUT (8,24 ns con 8). Es un solo número por arco, el máximo de la base y con la entrada más lenta de la LUT. Con la cadena fija no cambia entre semillas (0,00 ns en X1/Y8).
- **Entre semillas, con la cadena fija:** el ancho real cambia hasta 1,0 ns aunque nextpnr informe lo mismo, por la entrada física que elige el ruteo. Con la cadena de cuatro entradas (`Modo = 1`) esa dispersión baja a entre 0,2 y 0,8 ns según la posición (0,23 ns en X1/Y8).
- **Entre ubicaciones:** con N = 8 el pulso va de 6,57 a 8,28 ns entre las tres posiciones fijas, en la esquina máxima.
- **Sin fijar:** hasta 1,7 ns de diferencia entre semillas. Además con la cadena de cuatro entradas sin fijar nextpnr no termina de rutear en 60 s algunas corridas (1 de 10 con N = 12, 3 de 10 con N = 16 y 1 de 10 con N = 20).

### 5.3. Cuántas LUT hacen falta

La red global exige un pulso de 0,88 ns como mínimo (tW_GBUF, hoja de datos DS1040 versión 3.4, tabla de características externas de los iCE40HX; la fila está copiada en `mediciones/hoja_datos.txt`). La hoja de datos no distingue entre el tiempo en alto y en bajo, y aquí se exige para los dos. El resumen al final de `mediciones/cadena.txt`:

| N | Pulso más angosto (esquina mínima) | Pulso más ancho (esquina máxima) | Utilizable |
|---|------------------------------------|----------------------------------|------------|
| 1 | 0,43 ns | 1,05 ns | No: bajo el mínimo |
| 2 | 1,12 ns | 2,86 ns | Sí, pero sin margen si el chip es más rápido que la base |
| 4 a 16 | 2,52 a 10,19 ns | 4,49 a 16,78 ns | Sí |
| 20 | 13,30 ns | 20,47 ns | No: con 45 % no deja hueco entre pulsos |

Para el Espino base sirve cualquier largo entre 4 y 16, y se usó 8 para quedar lejos de los dos límites. Para el segmentado la ventana es más angosta: el pulso tiene que cubrir la ruta de subida a bajada (2,45 ns) y dejar tiempo a la de bajada a subida (8,86 ns de un período corto de 17,73 ns). Se usó 6, que da entre 4,0 y 5,9 ns.

## 6. Cómo se restringe en nextpnr y qué no ve

`mediciones/restricciones.txt`, sobre la prueba de placa sin el anillo, que tiene el reloj del pin y el doblado.

### 6.1. Las tres formas

| Forma | Qué hace |
|-------|----------|
| Sin restricción | Los dos relojes quedan con el objetivo por defecto, 12 MHz |
| `--freq 50` | Los dos relojes a 50 MHz. Sobrerrestringe el de 25 MHz |
| `--freq 25 --pre-pack restricciones/reloj_x2.py` (`ctx.addClock("clk", 50)`) | Cada red con su objetivo. Es la que se usó en el SoC |
| `--sdc restricciones/relojes.sdc` (`create_clock -period 20 [get_nets clk2x]`) | Lo mismo que la anterior |

El reloj doblado no entra por un pin, así que se restringe por el nombre de la red que sale del `SB_GB`. Con cualquiera de las dos últimas nextpnr informa `PASS at 50.00 MHz` para la red doblada y `PASS at 25.00 MHz` para la del pin.

SDC en nextpnr 0.11: acepta `create_clock` con `-period` y `-name`, y `set_false_path` entre puertos. Rechaza `-waveform` (el ciclo de trabajo), `create_generated_clock`, `set_clock_groups`, `set_clock_uncertainty`, `set_clock_latency`, `set_max_delay`, `set_input_delay`, `set_multicycle_path` y `get_clocks`. No hay forma de decirle que el reloj tiene 7 ns en alto de cada 20, ni que los períodos alternan.

**El objetivo no cambia el resultado.** Con 50 y con 56,4 MHz nextpnr entrega el mismo diseño ruteado en las 40 corridas comparadas (mismo checksum, `mediciones/soc_x2.txt`, punto 5). El objetivo solo mueve el umbral de PASS o FAIL. Pedir más frecuencia no hace que se esfuerce más.

### 6.2. Qué analiza y qué no

- **La cadena no existe para el análisis del reloj.** Para nextpnr el reloj doblado nace en la salida del buffer global. La cadena aparece solo en la ruta combinacional de pin a pin de la prueba de placa (`i_Clk` hasta el pin de prueba), que informa como un retardo sin compararlo con nada. En el SoC no aparece en ninguna parte.
- **Relación entre el reloj original y el doblado.** Los trata como relacionados y con los flancos alineados: informa un "clock to clock delay" de 0,45 ns que es el mismo con cadenas de 4, 8 y 16 LUT, y compara los cruces contra un período de 40 ns. En el chip el flanco del reloj doblado llega unos 2 ns después que el del reloj original y hay otro a mitad de período, así que un cruce directo entre los dos dominios dispondría de unos 18 a 22 ns, no de 40. En el SoC no hay cruces porque todo queda en el reloj doblado. En la prueba de placa los cruces pasan por sincronizadores.
- **Períodos alternados y ciclo de trabajo.** No los ve. Analiza un período único de 20 ns.
- **Flanco de bajada.** Supone que está a medio período. Para el segmentado con reloj doblado eso está mal en los dos sentidos: a las rutas de subida a bajada les da 10 ns cuando disponen de 4,0 a 5,9 ns (el ancho del pulso), y a las de bajada a subida les da 10 ns cuando disponen de 11,8 ns o más.
- **Skew de la red global.** No lo descuenta. La hoja de datos da hasta 727 ps en la HX1K.
- **Entradas del esclavo SPI.** SCLK, MOSI y CS_n aparecen como rutas `<async> -> posedge clk` con su retardo (2,07 ns hasta el primer flip-flop del sincronizador) y sin restricción. No analiza metaestabilidad, y no tiene por qué.

### 6.3. icetime

icetime entrega un solo número para todo el diseño. No distingue relojes ni flancos (T39) ni conoce restricciones por red. En la prueba de placa informa como ruta crítica la combinacional de pin a pin que pasa por la cadena (16,10 ns) y la da por aprobada contra 50 MHz, que no significa nada. En el SoC informa la ruta de un período (22,26 ns contra 22,11 ns de nextpnr en la misma corrida). Sirve como segunda opinión para esa ruta y para nada más. Lo útil de icetime aquí fue su netlist del diseño ruteado, que es la entrada de `scripts/sta_icestorm.py`.

## 7. Margen real del SoC con el reloj doblado

`mediciones/soc_x2.txt` y `mediciones/margen.txt`. Cadena fija en X1/Y8, 8 LUT en el base y 6 en el segmentado, 10 semillas.

### 7.1. Según nextpnr

| Variante | Celdas | BRAM | Fmax mínima, mediana y máxima (MHz) | Cierran a 50 MHz | Cierran a 56,4 MHz |
|----------|--------|------|-------------------------------------|------------------|--------------------|
| Base sin duplicador (control) | 1070 | 12 | 43,42, 44,95 y 47,16 | 0 de 10 | 0 de 10 |
| Base con reloj doblado | 1085 | 12 | 44,51, 45,70 y 47,78 | 0 de 10 | 0 de 10 |
| Segmentado sin duplicador (control) | 990 | 12 | 50,91, 53,97 y 55,41 | 10 de 10 | 0 de 10 |
| Segmentado con reloj doblado | 1004 | 12 | 51,66, 54,66 y 56,63 | 10 de 10 | 1 de 10 |

El control muestra que el duplicador no cambia la frecuencia máxima: la lógica es la misma y la diferencia entre con y sin duplicador es del tamaño de la que hay entre semillas.

### 7.2. A qué período hay que cerrar

El período corto del reloj doblado es 40 ns por el ciclo de trabajo, menos 0,27 ns. Esos 0,27 ns salen de la base de tiempos: el flanco de bajada del oscilador cruza el pin y el XOR más rápido que el de subida.

| Ciclo de trabajo del oscilador | Período corto | Equivale a cerrar a | Base | Segmentado |
|--------------------------------|---------------|---------------------|------|------------|
| 50 % exacto | 19,73 ns | 50,7 MHz | 0 de 10 | 10 de 10 |
| 48 a 52 % | 18,93 ns | 52,8 MHz | 0 de 10 | 9 de 10 |
| 45 a 55 % | 17,73 ns | 56,4 MHz | 0 de 10 | 1 de 10 |
| 40 a 60 % | 15,73 ns | 63,6 MHz | 0 de 10 | 0 de 10 |

Sumando el skew de la red global (0,727 ns), con 45 a 55 % habría que cerrar a 17,0 ns, que son 58,8 MHz. Ninguna semilla llega.

### 7.3. Con todas las clases de ruta y las tres esquinas

`scripts/sta_icestorm.py` calcula la peor ruta de cada clase (subida a subida, subida a bajada y bajada a subida) y el pulso del duplicador, cada cosa en la misma esquina de la base de tiempos. Semillas con holgura no negativa:

| Variante | Esquina | 45 a 55 % | 48 a 52 % | 50 % exacto |
|----------|---------|-----------|-----------|-------------|
| Base | máxima | 0 de 10 | 0 de 10 | 0 de 10 |
| Base | típica | 0 de 10 | 1 de 10 | 5 de 10 |
| Base | mínima | 5 de 10 | 10 de 10 | 10 de 10 |
| Segmentado | máxima | 1 de 10 | 8 de 10 | 10 de 10 |
| Segmentado | típica | 10 de 10 | 10 de 10 | 10 de 10 |
| Segmentado | mínima | 10 de 10 | 10 de 10 | 10 de 10 |

Peor holgura en la esquina máxima: con 50 % exacto, -3,17 ns el base y +0,10 ns el segmentado. Con 45 a 55 %, -5,17 ns y -1,90 ns. La semilla 1 del segmentado es la única que tolera el rango completo (de 44,7 a 56,6 %).

En el segmentado las rutas de medio ciclo no son el problema con la cadena de 6 LUT: la de subida a bajada usa hasta 2,45 ns de un pulso de 4,97 ns o más, y la de bajada a subida hasta 8,86 ns de los 11,8 ns o más que quedan entre el fin del pulso y el flanco siguiente. Lo que no cabe es la ruta de un período.

### 7.4. Variación con proceso, voltaje y temperatura

Base de la estimación, y sus límites:

- La base de tiempos de icestorm (`share/icebox/timings_hx1k.txt`) trae tres valores por arco: mínimo, típico y máximo. La razón entre ellos es la misma en 407 de los 417 valores no nulos (mínimo = 0,804 por máximo y típico = 0,889 por máximo) y los otros 10 tienen los tres iguales (`mediciones/cadena.txt`). Es un factor de escala fijo, no una caracterización de cada celda. No sabemos a qué voltaje y temperatura corresponde cada esquina.
- La hoja de datos (DS1040, "Derating Logic Timing", copiado en `mediciones/hoja_datos.txt`) dice que los tiempos de las herramientas son el peor caso dentro del rango de operación y que los retardos reales pueden ser mucho menores. No da una tabla de factores.
- No tenemos una medición del chip. El oscilador en anillo de la prueba de placa (sección 10) es justamente para eso.

Lo que se puede decir con esa base (`mediciones/margen.txt`, punto 4, escalando todos los retardos por un factor k respecto de la esquina máxima):

| k | Pulso más angosto (ns): base, segmentado | Peor holgura con 45 a 55 % (ns): base, segmentado |
|---|------------------------------------------|---------------------------------------------------|
| 1,00 (esquina máxima) | 6,63 y 4,97 | -5,17 y -1,90 |
| 0,89 (típica) | 5,90 y 4,43 | -2,62 y +0,29 |
| 0,80 (mínima) | 5,31 y 3,98 | -0,53 y +2,04 |
| 0,65 | 4,31 y 3,23 | +2,94 y +1,66 |
| 0,50 | 3,32 y 2,49 | +6,42 y +1,28 |

- El pulso cambia cerca de 25 % entre la esquina mínima y la máxima de la base. Con 8 LUT va de 5,3 ns (el más angosto en la esquina mínima) a 8,0 ns (el más ancho en la máxima), y se angosta más si el chip real es más rápido que la base. En ningún caso de la tabla baja de 0,88 ns.
- El Espino base cerraría con 45 a 55 % solo si el chip fuera entre 15 % (mejor semilla) y 23 % (peor semilla) más rápido que la esquina máxima.
- El segmentado cierra desde la esquina típica hacia abajo. O sea: es probable que funcione sobre la mesa a temperatura ambiente, y no hay cómo garantizarlo en el peor caso. Un diseño de competencia tiene que cerrar en el peor caso.

### 7.5. Si las opciones de nextpnr alcanzan

`mediciones/opciones_nextpnr.txt`: como el objetivo no cambia nada, se probaron las opciones que sí cambian la ubicación o el ruteo, con la red `clk` restringida a 56,4 MHz y 10 semillas. Frecuencia máxima según nextpnr en MHz (mínima, mediana y máxima):

| Variante | Opciones | Terminan | Fmax | Llegan a 50 | Llegan a 56,4 | Llegan a 58,8 |
|----------|----------|----------|------|-------------|---------------|---------------|
| Segmentado | por defecto | 10 de 10 | 51,66, 54,66 y 56,63 | 10 | 1 | 0 |
| Segmentado | `--opt-timing` | 10 de 10 | 48,48, 51,88 y 54,72 | 8 | 0 | 0 |
| Segmentado | `--tmg-ripup` | 10 de 10 | 50,69, 54,66 y 56,63 | 10 | 1 | 0 |
| Segmentado | `--opt-timing --tmg-ripup` | 8 de 10 | 48,48, 51,80 y 54,72 | 6 de 8 | 0 | 0 |
| Segmentado | `--placer-heap-timingweight 30` | 10 de 10 | 51,64, 53,21 y 55,82 | 10 | 0 | 0 |
| Base | por defecto | 10 de 10 | 44,51, 45,70 y 47,78 | 0 | 0 | 0 |
| Base | `--opt-timing` | 10 de 10 | 37,47, 39,80 y 42,39 | 0 | 0 | 0 |

- **Ninguna opción lleva las 10 semillas a 56,4 MHz**, y ninguna corrida llega a 58,8 MHz, que es lo que haría falta descontando el skew.
- **`--opt-timing` empeora.** Con el segmentado baja la mediana de 54,66 a 51,88 MHz y dos semillas dejan de cerrar incluso a 50 MHz. Con el base baja de 45,70 a 39,80 MHz. Es una pasada experimental de nextpnr y aquí resta.
- **`--tmg-ripup` casi no cambia nada**: 8 de 10 semillas dan el mismo número que por defecto, una sube 0,26 MHz y otra baja 0,97 MHz.
- **Las dos juntas no convergen siempre**: 2 de 10 corridas seguían ruteando a los 300 s y se cortaron. Como referencia, una corrida por defecto demora unos 3 s y una con `--opt-timing` sola unos 6 s.
- Las corridas por defecto de este barrido repiten semilla por semilla las de `mediciones/soc_x2.txt`, que es una comprobación independiente de que el resultado de nextpnr se reproduce.

O sea, no hay un interruptor de la herramienta que entregue el margen que falta. Habría que rediseñar la ruta crítica del core (sección 12).

### 7.6. Cuánto se le puede creer al análisis propio

Las secciones 7.3 y 7.4 salen de `scripts/sta_icestorm.py` y no de nextpnr, así que se comparó con las dos herramientas donde hay con qué (`mediciones/validacion_sta.txt`, `make validar`):

- **Clase de la ruta.** `rtl/top_clases.v` es un diseño de control con una ruta larga de clase conocida, de bajada a subida o de subida a bajada según un parámetro. En 10 corridas (2 casos por 5 semillas) el script clasifica la ruta igual que nextpnr en las 10, y su retardo difiere entre -0,01 y +0,21 ns (4,1 % como máximo).
- **Ruta de un período del SoC.** En las 40 corridas de `make soc` con objetivo de 50 MHz, el script queda entre 0,03 y 0,10 ns bajo icetime, que usa la misma base de tiempos. Contra nextpnr la diferencia va de -0,76 a +0,75 ns: nextpnr usa un solo valor por arco y, en el segmentado, a veces informa como crítica una ruta de medio ciclo contada dos veces.
- **Pulso del duplicador.** No hay otra herramienta que lo calcule. Lo más cercano es el retardo de la cadena en el SDF de nextpnr: 8,24 ns con 8 LUT contra 7,33 a 8,02 ns del script en la esquina máxima (`mediciones/cadena.txt`). Coinciden en el orden de magnitud y nextpnr queda por arriba, como corresponde a quien toma la entrada más lenta de cada LUT.

Lo que no está validado: las esquinas mínima y típica (son la misma base escalada), el skew de la red global (se toma de la hoja de datos, no se calcula) y, sobre todo, nada de esto contra el chip.

## 8. Presupuesto de ciclos y el esclavo SPI

### 8.1. Presupuesto

`mediciones/margen.txt`, punto 5. El enunciado pide recalcularlo si se sube la frecuencia. Con la fórmula del testbench, (período - 9 500 ns) dividido por el período del reloj:

| Ronda | Período | Ciclos a 25 MHz | Ciclos con el reloj doblado |
|-------|---------|-----------------|-----------------------------|
| 1 | 10 ms | 249 762 | 499 525 |
| 2 | 1 ms | 24 762 | 49 525 |
| 3 | 0,1 ms | 2 262 | 4 525 |

Respuesta medida en la prueba de humo, en ciclos del reloj interno desde `byte_done` hasta la escritura de `DECISION`: el Espino base 41,0 de promedio y 44 de peor caso (0,88 us en vez de 1,76 us), y el segmentado 22,0 y 24 (0,48 us en vez de 0,96 us). El programa pasa de usar el 1,9 % del presupuesto de la ronda 3 al 1,0 %. No hay nada en el algoritmo actual que necesite esos ciclos: ningún modelo más pesado ganó bajo el protocolo (`docs/estado.md`, tramo 4).

### 8.2. Qué cambia en el esclavo SPI

El esclavo sincroniza SCLK, MOSI y CS_n con tres flip-flops en el reloj del sistema y detecta los flancos de SCLK comparando dos muestras. Si su reloj se duplica:

- **Muestrea cada 20 ns en vez de 40.** La advertencia del enunciado (no usar un SCLK cercano a la frecuencia del sistema) se relaja. Con SCLK de 1 MHz hay 25 muestras por semiperíodo en vez de 12. No hacía falta.
- **Reacciona en la mitad del tiempo.** Entre un flanco de SCLK y su efecto pasan 2 a 3 ciclos: 40 a 60 ns en vez de 80 a 120 ns. MISO cambia antes después del flanco de bajada, y la maestra lo lee 500 ns después de todas formas.
- **El sincronizador tiene menos tiempo para resolver.** Un período de 20 ns (18 con ciclo de trabajo de 45 %) en vez de 40. Sigue sobrando, pero es margen que se entrega.
- **El reset dura la mitad.** El contador de 4095 ciclos pasa de 164 us a 82 us. Ese reset existe porque las BRAM demoran en entregar datos válidos (decisión T3), así que habría que subir `PorBits` a 13 para conservar el tiempo. En la prueba de humo se nota: el programa pierde un precio inicial y no dos, y por eso la referencia se corre con `--por-bits 11`.
- **Comparte el reloj con todo lo demás.** Si el reloj doblado entrega un período demasiado corto, el core calcula mal o salta a cualquier parte y `DECISION` queda con basura o pegada en el último valor. Si entrega un pulso deformado, el contador de bits y el registro de salida del esclavo se corrompen y la maestra lee un byte cualquiera, que puede ser una orden de compra o de venta. Con el reloj del pin ninguna de las dos cosas puede pasar.
- **Lo que nextpnr analiza de ese cruce** es lo mismo que antes: nada, porque son entradas asíncronas que pasan por un sincronizador.

### 8.3. El testbench oficial frente al reloj doblado

El testbench mide con su propio reloj de 25 MHz. Con el reloj interno doblado:

- Informa la respuesta en ciclos de 40 ns (22 en vez de 44 el base) y la compara contra el presupuesto de 25 MHz.
- `byte_done` y la escritura de `DECISION` son pulsos de un ciclo interno, o sea de medio ciclo del testbench. Que los vea depende de en qué mitad caen. Con el segmentado ve 1 200 de las 1 999 escrituras de `DECISION` (`mediciones/humo_soc_x2.txt`).
- El 4/4 depende de una coincidencia: el testbench sube SCLK justo en un flanco de su reloj (decisión T19). Con una copia del testbench que corre la transacción 20 ns, el mismo SoC decide igual de bien (decisiones idénticas a la referencia) y el testbench ve 0 de 199 `byte_done`, informa peor caso de 0 ciclos y entrega 3/4 (`mediciones/humo_fase.txt`).

O sea, el testbench oficial no sirve para certificar un diseño con reloj interno doblado. Es una razón más, aparte del timing.

## 9. Testbenches: qué demuestran y qué no

| Testbench | Comando | Qué demuestra | Qué no demuestra |
|-----------|---------|---------------|------------------|
| `tb/tb_duplicador.v` | `make tb` | Dos flancos de subida por período, ancho del pulso igual al retardo de la cadena, períodos que alternan con el ciclo de trabajo y contador al doble. 9 casos (3 esquinas por 3 ciclos de trabajo) con los retardos del diseño ruteado, y 2 controles negativos que fallan como deben | Que esos retardos sean los del chip. No ve jitter ni el pulso mínimo real de la red global |
| `tb/tb_proyecto_4.sv` sin modificar, más `tb/monitor_x2.sv` | `make humo` | Que el SoC con el reloj interno al doble sigue funcionando en lo funcional: 4/4, y `decisiones.csv` idéntico a `ref/trader.py` en 2000 ticks, con el base y con el segmentado. Que el esclavo SPI opera bien muestreando al doble | Nada sobre timing. Es simulación RTL: la lógica no tiene retardos y cualquier período sirve. No dice si el diseño cierra |
| Copias del testbench con otra fase | `make humo` | Que el 4/4 del testbench oficial depende de la fase cuando el reloj interno va al doble | |
| `tb/tb_placa_x2.v` | `make placa` | Que la lógica de la prueba de placa hace lo que dice: 13 comprobaciones, incluidos el reloj detenido, el error retenido y la medición del anillo, más un control negativo | Los retardos reales. Ahí son parámetros |

Resultados guardados: `mediciones/tb_duplicador.txt` (todos los casos como se esperaba), `mediciones/humo_soc_x2.txt` (HUMO: PASS), `mediciones/humo_fase.txt` y `mediciones/placa_x2.txt` (RESULTADO: PASS en los dos).

No se hizo simulación a nivel de compuertas con retardos del SoC completo. La información de tiempos sale del análisis estático.

## 10. Prueba para la placa

`rtl/placa_x2.v`, con los pines de `goboard.pcf` (`restricciones/placa_x2.pcf`). Ocupa 207 celdas y no usa BRAM. El bitstream está en `placa/placa_x2.bin` y su SHA-256 en `placa/placa_x2.sha256`. Los valores esperados están en `mediciones/placa_x2.txt`.

### 10.1. Qué muestra

| Elemento | Qué muestra |
|----------|-------------|
| Display izquierdo | Bits altos de un contador en el reloj de 25 MHz. Cambia cada 0,67 s |
| Display derecho | Los mismos bits de un contador en el reloj doblado. Cambia cada 0,34 s si el duplicador funciona |
| LED1 | Encendido: en la última ventana de 0,17 s el reloj doblado dio exactamente el doble de ciclos (con tolerancia de uno) |
| LED2 | Error retenido: alguna ventana no dio el doble, o el reloj doblado está detenido |
| LED3 y LED4 | Parpadeo de cada reloj. LED4 va al doble que LED3 |
| SW1, SW2, SW3 (mantener presionado) | Acortan la cadena: sin LUT, 1 LUT y 2 LUT. Sin botones son 8 |
| SW4 | Borra el error, enciende el oscilador en anillo y muestra su medición en los dos displays |
| Pin 63 (el MISO del PMOD) | Reloj doblado dividido por 2. Con SW4, el pulso crudo. Solo si hay osciloscopio |

Ancho del pulso con cada botón según la base de tiempos, esquinas mínima y máxima: sin botones 7,98 a 10,63 ns, SW3 3,64 a 4,61 ns, SW2 2,26 a 2,86 ns, SW1 1,00 a 1,31 ns. SW1 queda a propósito cerca del mínimo de 0,88 ns de la hoja de datos.

### 10.2. Comandos, uno por uno

Los corre Nicolás, con la Go Board conectada por USB y **desconectada de la maestra**.

1. `make -C factibilidad/f_doble_frecuencia placa`
   Opcional. Vuelve a simular la prueba, sintetiza, rutea 10 semillas y deja el bitstream de la semilla 1. No toca la placa. Sirve para comprobar que el bitstream que se va a grabar es el que se midió.
2. `cd factibilidad/f_doble_frecuencia/placa && sha256sum -c placa_x2.sha256 && cd -`
   Comprueba que el archivo `placa_x2.bin` corresponde al hash guardado. Debe responder `placa_x2.bin: OK`.
3. `iceprog factibilidad/f_doble_frecuencia/placa/placa_x2.bin`
   Graba el bitstream en la memoria flash de la Go Board y lo verifica. **Reemplaza lo que la placa tenía grabado.** La placa arranca sola con la prueba.
4. Hacer las observaciones de la tabla de abajo y anotarlas.
5. `iceprog bitstreams/competencia_v1.bin`
   Deja la placa otra vez con el bitstream de competencia. No saltarse este paso.

### 10.3. Qué anotar

| Paso | Qué hacer | Qué anotar | Qué se espera |
|------|-----------|------------|---------------|
| a | Nada, mirar 10 s | ¿El display derecho avanza al doble? LED1 y LED2 | Sí. LED1 encendido, LED2 apagado |
| b | Mantener SW3, tocar SW4 una vez, esperar 2 s | LED1 y LED2 | Igual que en a |
| c | Mantener SW2, tocar SW4, esperar 2 s | LED1 y LED2 | Igual que en a |
| d | Mantener SW1, tocar SW4, esperar 2 s | LED1 y LED2, y si el display derecho avanza | No se sabe: es el caso límite. Si LED2 se enciende, el pulso de 1,0 a 1,3 ns ya no pasa por la red global |
| e | Soltar todo, tocar SW4 | LED1 y LED2 | Vuelve a quedar como en a |
| f | Mantener SW4 | Los dos dígitos hexadecimales de los displays, D | 60 en la esquina mínima, 56 en la típica, 4D en la máxima. Un número mayor que 60 dice que el chip es más rápido que toda la base |
| g | Repetir f con la placa recién encendida y después de 10 minutos, y si se puede calentando el chip con un secador de pelo | D en cada condición | D baja al calentar |
| h | Con osciloscopio, sin botones: pin 63 | Tiempo en alto y tiempo en bajo de la onda de 25 MHz | Los dos períodos del reloj doblado. Su diferencia es el ciclo de trabajo del oscilador: 20 y 20 ns es 50 %, 18 y 22 ns es 45 % |

Con D se calcula el período real del anillo, 1280 / D ns (D en decimal), y el factor k de la sección 7.4: k = (1280 / D) / 16,58. El 16,58 es el período del anillo en la esquina máxima para este bitstream (`mediciones/placa_x2.txt`, punto 5). Con k se lee directamente en esa tabla si el segmentado doblado cerraría en esta placa.

Dos advertencias sobre la prueba. Cambiar de toma con el reloj andando produce pulsos irregulares, y por eso se borra el error con SW4 después de cada cambio. Y el multiplexor de tomas es lógica en el camino del reloj que el SoC no tendría: si la prueba falla sin botones, hay que mirar primero eso.

## 11. Qué habría que sacrificar para que quepa

En área no hay nada que sacrificar. El duplicador son 7 o 9 celdas (14 y 15 de diferencia medida en el SoC) y ningún buffer global adicional: usa el que ocupaba el reloj del pin, 3 de 8 con y sin duplicador. El SoC queda en 1085 de 1280 celdas con el Espino base y 1004 con el segmentado.

Lo que se sacrifica es margen de timing:

| Para que cierre | Se entrega |
|-----------------|------------|
| Usar el segmentado y no el base | El base queda fuera: le falta entre 15 y 23 % de velocidad |
| Elegir la semilla 1 | La única que tolera 45 a 55 %, por 0,13 ns. Cualquier cambio en el RTL (una instrucción nueva, un periférico) la desordena |
| Aceptar solo 48 a 52 % de ciclo de trabajo | Cierran 8 de 10 semillas, sin haber medido el oscilador de la placa |
| Aceptar la esquina típica en vez de la máxima | Cierran 10 de 10, y deja de haber garantía con calor o con voltaje bajo |
| No descontar el skew de la red global | Hasta 0,727 ns sobre holguras de décimas de ns |
| Todo lo anterior | De 20,7 ns de holgura a 25 MHz se pasa a una holgura que no se puede demostrar positiva |

## 12. Días de trabajo para llevarla a calidad de competencia

Estimado, no medido.

| Tarea | Días |
|-------|------|
| Bajar la ruta crítica del segmentado de 19,6 ns a menos de 17,0 ns en las 10 semillas (reordenar el adelantamiento y la ALU). Resultado incierto | 2 a 3 |
| Caracterizar la placa: ciclo de trabajo del oscilador con osciloscopio, anillo en frío y en caliente, y repetir en las tres Go Board del grupo | 1 |
| Simulación a nivel de compuertas con retardos del SoC doblado, o al menos el análisis estático corriendo en la integración continua | 1 |
| Gemelo digital con el reloj doblado (período de 20 ns y reset de la mitad) y equivalencia a los tres períodos | 0,5 |
| Copias del testbench que midan con el reloj interno, y acordar con el ayudante cómo se revisa | 0,5 |
| Prueba con la maestra real el 26/11, con el bitstream doblado además de los dos que ya van | el mismo día |
| Documento de estudio y preguntas de defensa | 1 |
| **Total** | **6 a 7** |

A cambio de eso el patrimonio no cambia. No se recomienda gastarlos.

## 13. Reglas del enunciado y preguntas para el ayudante

- "Pueden modificar libremente el RTL, siempre que el procesador siga siendo Espino": cumple. El core no se toca.
- "El core debe leer el precio y escribir la decisión": cumple. El duplicador no participa en la decisión.
- "Todo hardware agregado debe estar en el repositorio con su testbench": cumple, con `tb/tb_duplicador.v`, la prueba de humo y `tb/tb_placa_x2.v`.
- "Deben usar el mismo programa para todas las series de tiempo": cumple. `trade.hex` es el mismo.
- Punto 3.3: "Si sube la frecuencia con el PLL, muestre que nextpnr cierra timing a la nueva frecuencia y recalcule el presupuesto de ciclos de cada ronda". El presupuesto está recalculado (sección 8.1). El cierre **no se puede mostrar con honestidad**: nextpnr informa PASS a 50 MHz para el segmentado en las 10 semillas, pero ese análisis no conoce los períodos alternados, y con ellos cierra 1 de 10.
- Punto 2.1: "El esclavo de Pochoco sincroniza SCLK con el reloj de 25 MHz". Con el duplicador lo sincroniza con el reloj doblado. Funciona, pero el diseño ya no es el que describe el enunciado.
- El testbench oficial entra por jerarquía a `dut.u_spi.*` y muestrea con su reloj: con el reloj interno doblado su resultado depende de la fase (sección 8.3). No se renombró nada.

Preguntas para el ayudante, solo si se quisiera insistir con esta pieza:

1. ¿Se acepta un reloj interno distinto de 25 MHz generado sin PLL? El enunciado solo menciona el PLL.
2. ¿El testbench oficial se va a correr contra el repositorio? Con reloj interno doblado mide en ciclos de 25 MHz y puede no ver los pulsos.
3. ¿Qué oscilador trae la Go Board y con qué ciclo de trabajo? No encontramos su hoja de datos.
4. ¿La maestra real usa el timing del testbench? Ya estaba en la lista y aquí pesa más.

## 14. Riesgos

- **El ciclo de trabajo del oscilador no está medido.** Todo el margen depende de él. El rango de 45 a 55 % es un supuesto.
- **El pulso depende del chip.** Cambia 25 % dentro de la base de tiempos y no sabemos cuánto más en el silicio.
- **La holgura depende de la semilla.** Entre la mejor y la peor del segmentado hay 2 ns, y hace falta la mejor.
- **Falla en silencio.** Una violación de setup no enciende ningún LED: el core calcula mal o el esclavo SPI entrega un byte cualquiera, y eso es una orden.
- **Un solo día con la maestra.** El 26/11 habría que probar tres bitstreams en vez de dos, y un reloj marginal puede pasar ese día y fallar el 1/12 con otra temperatura.
- **El testbench oficial deja de ser confiable** para este diseño.
- **El análisis propio no está validado contra el chip.** `scripts/sta_icestorm.py` coincide con icetime en la ruta de un período (a 0,10 ns o menos en 40 corridas) y con nextpnr en la clase de las rutas por flanco (10 de 10, sección 7.6), pero el pulso del duplicador no tiene contra qué compararse hasta medir en la placa.
- **El reset más corto** puede reabrir el problema de arranque de las BRAM del Proyecto 2 si no se sube `PorBits`.

## 15. Veredicto

Con los criterios de corte:

- **Cabe junto al SPI:** sí. 1085 celdas con el base y 1004 con el segmentado, 12 BRAM.
- **Cierra en las 10 semillas:** no. El base no cierra a 50 MHz en ninguna (0 de 10). El segmentado cierra a 50 MHz en las 10 según nextpnr, pero el reloj doblado no es un reloj de 50 MHz: con el ciclo de trabajo entre 45 y 55 % cierra 1 de 10 en la esquina máxima, y ninguna si se descuenta el skew.
- **Aporte a la competencia:** ninguno. Sobra presupuesto de ciclos por un factor 50.

**Descartada de la edición de competencia. Va a la edición de exhibición como resultado negativo medido**, junto al del PLL: el VQ100 no tiene PLL, y doblar el reloj con lógica se puede pero no se puede garantizar. No aplica a la edición ASIC: ahí la frecuencia se sube en el flujo, no con un duplicador.

Lo que sí queda para el resto del proyecto:

- La tolerancia del segmentado al ciclo de trabajo, medida: de 6,7 a 79,4 % en las 10 semillas. Reemplaza al "entre 25 y 75 %" que teníamos anotado como cota.
- `scripts/sta_icestorm.py`, que entrega rutas por flanco y por esquina. Sirve para cualquier pieza que use el flanco de bajada.
- El oscilador en anillo de la prueba de placa, que dice dónde cae nuestro chip respecto de la base de tiempos. Vale para estimar el margen real de todo el SoC, no solo de esta pieza.
- Dos hechos sobre nextpnr: el objetivo de frecuencia no cambia la ubicación ni el ruteo, y el SDC no admite ciclo de trabajo ni relojes generados.

## 16. Archivos

| Archivo | Qué es |
|---------|--------|
| `rtl/duplicador_reloj.v` | Duplicador: cadena, XOR y buffer global. Modelo de retardo con `SIM_RETARDO` |
| `rtl/pochoco_soc_x2.v` | Copia de `rtl/pochoco_soc.v`. Cambia solo el origen de `clk` y agrega los parámetros `Doblar`, `NRet`, `ModoRet` y los del modelo de retardo. Con `Doblar = 0` es el SoC original. Conserva el encabezado de licencia y de autor |
| `rtl/top_cadena.v` | Duplicador más un contador, para medir la cadena |
| `rtl/placa_x2.v` | Prueba para la Go Board |
| `restricciones/reloj_x2.py` | `ctx.addClock` por nombre de red, para `--pre-pack` |
| `restricciones/relojes.sdc` | Los dos relojes en el SDC que acepta nextpnr |
| `restricciones/placa_x2.pcf` | Pines de la prueba de placa |
| `scripts/fijar_cadena.py` | Fija la cadena y el anillo con el atributo `BEL`, para `--pre-pack` |
| `scripts/sta_icestorm.py` | Análisis de tiempos sobre la netlist de icetime: rutas por flanco y por esquina, pulso del duplicador, holguras y período de un lazo |
| `scripts/validar_sta.sh`, `rtl/top_clases.v` | Comparación de ese análisis con nextpnr y con icetime, y su diseño de control |
| `scripts/hoja_datos.py` | Extrae de la hoja de datos DS1040 el pulso mínimo y el skew de la red global |
| `scripts/medir_sintesis.sh`, `medir_cadena.sh`, `medir_restricciones.sh`, `medir_soc.sh`, `medir_opciones.sh` | Las mediciones de síntesis y de place and route |
| `scripts/resumen_cadena.py`, `resumen_soc.py`, `margen.py`, `casos_tb.py` | Arman las tablas a partir de las corridas |
| `scripts/tb_duplicador.sh`, `humo_soc.sh`, `humo_fase.sh`, `placa.sh` | Simulaciones y construcción del bitstream de prueba |
| `tb/tb_duplicador.v`, `tb/monitor_x2.sv`, `tb/tb_placa_x2.v` | Testbenches |
| `mediciones/` | Las salidas guardadas de cada comando |
| `placa/placa_x2.bin`, `placa/placa_x2.sha256` | Bitstream de la prueba de placa y su hash |
| `AVANCE.md` | Bitácora de trabajo: qué se hizo, qué se rehízo y qué quedó pendiente |
