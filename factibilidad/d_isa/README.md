# Pieza D: extensión de la ISA en custom-0 (estudio de factibilidad)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Primera parte de la pieza D: especificación, módulos sueltos, pruebas y costo. Los módulos se midieron integrados en una copia del Espino segmentado de 3 etapas (`core/`). **No se integraron ni se midieron sobre el barrel** (`factibilidad/a_barrel/`): eso queda para la segunda parte, y la sección 8 dice cómo hacerlo.

Nada de esta carpeta está en `rtl/`, `tools/` ni en el flujo del repositorio.

## 1. Resultado en una página

Se construyeron y verificaron 17 instrucciones en custom-0 y un periférico, varias con más de una forma de integrarlas, y se midió el costo de 49 variantes sobre el SoC completo.

| Pregunta del encargo | Respuesta | Medición que la respalda |
|----------------------|-----------|--------------------------|
| Cómo se codifica k | En `funct7[4:0]`: la codificación admite los 32 valores y el hardware se sintetiza con un conjunto | `ESPECIFICACION.md` |
| Qué conjunto de k cabe | Todos caben si el paso usa el sumador de la ALU (`emad`: +37 celdas con k = 5, +100 de 4 a 7, +137 de 0 a 7, +200 de 0 a 31). La versión autónoma con todos los k no cabe (1309 celdas). Se recomienda k = 5 fijo | `mediciones/costo_integrado.txt` |
| Forma del paso de media exponencial | `emad` (desde la desviación) y `devk` (la desviación) en vez de `ema`: cuestan menos y no encadenan resta, desplazamiento y suma en un ciclo | +37 y +41 celdas, +113 las dos; `ema` +60 con la resta de la ALU y +167 autónoma |
| Qué entrega la comparación por carril | Máscara 0xFF o 0x00 por carril, sin signo. La de un bit por carril ahorra 20 celdas. La con signo no cuesta (dentro del ruido) | +165 la mínima, +145 con un bit, +161 con signo |
| Mínimo y máximo por carril | No salen gratis: 96 celdas más | +261 contra +165 |
| Multiplicador | `mulstep` en el sumador de la ALU: +42 celdas. El periférico cuesta +198 y tiene estado. El combinacional de 8 x 8 cuesta +184 y el de 16 x 8 no cabe (1338 celdas) | `mediciones/costo_integrado.txt` |
| La compra recortada exige dividir | Sí, pero solo cuando hay recorte, con cociente menor que 63. Con `divstep` son 11 instrucciones y +108 celdas. Con 6 restas de prueba en RV32E son 35 instrucciones y 0 celdas (estimado) | `mediciones/contabilidad.txt` |
| Amdahl del paso de la media | Predicho 1,31 y medido 1,31 en el tick completo del segmentado (1,31 y 1,33 en el base). La respuesta que mide el testbench oficial no mejora: ese bloque va después de escribir `DECISION` | `mediciones/amdahl.txt` |
| Amdahl de los carriles | Kernel de cuatro bandas: 30 instrucciones contra 8, speedup 3,75 predicho y medido | `mediciones/kernel_bandas.txt` |

Lo que cabe y lo que no, sobre el segmentado (995 celdas la copia sin instrucciones nuevas, 1280 la FPGA, 12 de 16 BRAM en todas):

| Conjunto | Celdas | Agrega | Libres | Fmax mínima, mediana, máxima (MHz) | Cierran a 25 MHz |
|----------|--------|--------|--------|-------------------------------------|------------------|
| `emad`, k = 5 | 1032 | +37 | 248 | 51,59, 54,17 y 57,12 | 10 de 10 |
| `emad`, `devk` y `mulstep`, todo en el sumador de la ALU | 1119 | +124 | 161 | 47,12, 48,47 y 49,63 | 10 de 10 |
| Lo anterior más los carriles del kernel de bandas en la ALU | 1161 | +166 | 119 | 33,31, 34,64 y 36,93 | 10 de 10 |
| Lo anterior más `divstep` | 1226 | +231 | 54 | 33,00, 34,45 y 35,98 | 10 de 10 |
| `emad` y los carriles de bandas en una unidad aparte | 1202 | +207 | 78 | 48,18, 50,69 y 52,25 | 10 de 10 |
| `emad`, `devk`, `mulstep` y los carriles de bandas en unidad aparte | 1282 | +287 | -2 | no termina | 0 de 10 |
| Todo con k = 5 (los diez carriles y `divstep`) | 1466 | +471 | -186 | no termina | 0 de 10 |
| Todas las instrucciones, todos los k y el periférico | 2505 | +1510 | -1225 | no termina | 0 de 10 |

**Veredicto** (detalle en la sección 16): un subconjunto pasa los dos criterios de corte de hardware y el conjunto completo no cabe.

- **Candidata a la edición de competencia:** `emad` y `devk` con k = 5 y `mulstep`, en el sumador de la ALU. 1119 celdas, 12 BRAM, 10 de 10 semillas. Condiciones que este tramo no resuelve: medirla sobre el core que se elija (el barrel no se midió) y pasar por la maestra el 26/11.
- **Edición de exhibición:** los carriles y `divstep`, salvo que el fondo de estrategias (pieza B) se elija y los use. También el periférico multiplicador y `ema`, como alternativas medidas.
- **Edición ASIC:** el conjunto completo con todos los k, `mulc` de 16 x 8 y los diez carriles.

Lo que hay que tener presente al decidir: **la extensión no cambia el patrimonio.** Las cinco versiones de `trade.s` entregan las mismas decisiones bit a bit, y la respuesta sin ninguna instrucción nueva ya usa menos del 2 % del presupuesto de la ronda más rápida (26 ciclos de 2262 en el peor caso del segmentado). Lo que aporta es la pauta de co-diseño y dejar más instrucciones por tick a los hilos del barrel.

## 2. Qué se construyó

| Carpeta o archivo | Contenido |
|-------------------|-----------|
| `ESPECIFICACION.md` | Codificación, semántica exacta y un ejemplo de cada instrucción |
| `ref/xd.py` | Modelo de referencia de cada instrucción y del periférico, con autoprueba y la función `codificar` |
| `rtl/xd_ema.v`, `xd_srak.v` | Paso de media exponencial autónomo y desplazamiento aritmético, con el conjunto de k como parámetro |
| `rtl/xd_opa.v` | Operando A desplazado para el sumador de la ALU: `emad`, `devk`, `mulstep` y `pbcast8` |
| `rtl/xd_simd8.v` | Los diez carriles como unidad aparte, cada opción con su parámetro |
| `rtl/xd_alu.v` | La ALU del Espino con los carriles en su propio sumador (reemplaza a `espino_alu`) |
| `rtl/xd_mulstep.v`, `xd_divstep.v`, `xd_mulc.v` | Paso de multiplicación, paso de división y producto combinacional angosto |
| `rtl/xd_mul_mmio.v` | Periférico multiplicador serial de 24 x 8 |
| `rtl/xd_unit.v` | Unidad que junta las instrucciones que van por el multiplexor de escritura |
| `core/` | Copia del RTL del repositorio con la extensión integrada por definiciones `XD_*` (sección 13) |
| `tb/` | Un testbench por módulo, uno de las instrucciones dentro del core y uno del kernel de bandas |
| `formal/` | Propiedades y tareas de SymbiYosys |
| `sw/` | `trade.s` en cinco versiones y el kernel de cuatro bandas en tres |
| `tools/` | Scripts de cada medición, generador de vectores y de programas, y `xd_word.py` |
| `mediciones/` | La salida guardada de cada script |
| `AVANCE.md` | Bitácora del trabajo |

Las instrucciones, por grupo (`mediciones/codificacion.txt`):

- Media exponencial: `ema rd, rs1, rs2, k` (`rd = rs2 + ((rs1 - rs2) >>> k)`), `emad` (`rd = rs2 + (rs1 >>> k)`), `devk` (`rd = (rs1 << k) - rs2`) y `srak` (`rd = rs1 >>> k`).
- Carriles de 4 x 8 bits: `padd8`, `psub8`, `pcmpltu8`, `pcmplt8`, `pminu8`, `pmaxu8`, `paddus8`, `psubus8`, `pbcast8` y `pmovmsk8`.
- Producto y cociente: `mulstep`, `divstep` y `mulc`.

En `ema` el estado va en `rs2` y la muestra en `rs1`. Es la fórmula del encargo con los nombres de los operandos cambiados, para que la resta sea `rs1 - rs2`, que es la que la ALU ya hace.

## 3. Cómo se reproduce cada número

Todo se corre desde `factibilidad/d_isa/`. El Makefile toma las herramientas de `~/herramientas/oss-cad-suite/bin`.

| Comando | Qué hace | Salida | Tiempo |
|---------|----------|--------|--------|
| `make tabla` | Tabla de codificaciones | `mediciones/codificacion.txt` | 1 s |
| `make ejemplos` | Un ejemplo numérico de cada instrucción | `mediciones/ejemplos.txt` | 1 s |
| `make tb` | Cada módulo contra `ref/xd.py`, y mutaciones | `mediciones/tb_modulos.txt` | 3 min |
| `make tb-core` | Las instrucciones dentro del core, base y segmentado | `mediciones/tb_core.txt` | 2 min |
| `make tb-core-recomendado` | 200 programas por core para `emad`, `devk` y `mulstep` en la ALU | `mediciones/tb_core_recomendado.txt` | 3 min |
| `make formal` | Pruebas formales con sby | `mediciones/formal.txt` | 2 min |
| `make sin-cambios` | Formal: la extensión no cambia las instrucciones de RV32E | `mediciones/core_sin_cambios.txt` | 10 s |
| `make costo-suelto` | LUT4 de cada módulo suelto | `mediciones/costo_suelto.txt` | 1 min |
| `make costo-integrado` | Celdas, BRAM y fmax en 10 semillas de las 49 variantes y del segmentado del repositorio | `mediciones/costo_integrado.txt` | 15 min con 5 procesos |
| `make medir-ticks` | `trade.s` con las instrucciones: equivalencia y ciclos por tick | `mediciones/ticks_xd.txt` | 10 min |
| `make equiv-combinaciones` | Las combinaciones que caben, por la copia del testbench oficial | `mediciones/equiv_combinaciones.txt` | 3 min |
| `make kernel` | Kernel de cuatro bandas, escalar contra carriles | `mediciones/kernel_bandas.txt` | 10 s |
| `make contabilidad` | Anchos y contabilidad propia con `mulstep` y `divstep` | `mediciones/contabilidad.txt` | 5 s |
| `make amdahl` | Predicho contra medido y escalera de la clase 7 | `mediciones/amdahl.txt` | 1 s |
| `make rapido` | Versión corta de las pruebas, sin escribir en `mediciones/` | pantalla | 3 min |
| `make todo` | Todo lo anterior salvo `rapido` | | 40 min |

`make costo-integrado` usa `tools/medir_variante.sh` del repositorio con `RTL` apuntando a `core/` y deja los logs en `build/variantes/fact_d_*` de la raíz. Con `make costo-integrado FILTRO='^(emad_k5|media_mul)$'` se miden solo algunas variantes y la salida va a la pantalla. `make amdahl` no mide: lee las salidas guardadas de `medir-ticks`, `costo-integrado` y `kernel`.

Al retomar el trabajo el 14/11 se repitieron `make rapido`, `make tb`, `make amdahl`, `make costo-suelto` y cuatro variantes de `make costo-integrado` (`ref`, `emad_k5`, `media_mul` y `alu_todo`): todo dio lo mismo que lo guardado.

## 4. Costo

### 4.1 Módulos sueltos

`mediciones/costo_suelto.txt`, Yosys `synth_ice40`, cada módulo con sus entradas y salidas como puertos. Sirve para comparar opciones entre sí, no para saber cuánto agrega al SoC.

| Módulo | LUT4 | Acarreos | Flip-flops |
|--------|------|----------|------------|
| `espino_alu` (referencia) | 255 | 63 | 0 |
| `xd_ema`, k = 5, de 4 a 7, de 0 a 7 y de 0 a 31 | 90, 145, 213 y 253 | 62 | 0 |
| `xd_srak`, k = 5, de 4 a 7, de 0 a 7 y de 0 a 31 | 0, 54, 93 y 163 | 0 | 0 |
| `xd_opa`: `emad` o `devk` solos, k = 5 | 0 | 0 | 0 |
| `xd_opa`: `emad` y `devk`, k = 5 | 84 | 0 | 0 |
| `xd_opa`: `emad`, `devk` y `mulstep` | 85 | 0 | 0 |
| `xd_opa`: `emad` y `devk`, k de 0 a 31 | 373 | 0 | 0 |
| `xd_simd8` mínimo (`padd8`, `psub8`, `pcmpltu8`) | 99 | 32 | 0 |
| `xd_simd8` con comparación de un bit por carril | 71 | 32 | 0 |
| `xd_simd8` más `pcmplt8` | 111 | 32 | 0 |
| `xd_simd8` más `pminu8` y `pmaxu8` | 204 | 32 | 0 |
| `xd_simd8` kernel de bandas | 147 | 32 | 0 |
| `xd_simd8` con las diez operaciones | 260 | 32 | 0 |
| `xd_alu` (la ALU completa con cinco operaciones de carril) | 219 | 32 | 0 |
| `xd_mulstep` | 62 | 30 | 0 |
| `xd_divstep` | 48 | 25 | 0 |
| `xd_mulc` de 8 x 8, 16 x 8 y 24 x 8 | 158, 300 y 444 | 12, 20 y 28 | 0 |
| `xd_mul_mmio` | 104 | 32 | 92 |
| `xd_unit` con todo y todos los k | 1010 | 169 | 0 |

Con un solo k, `emad`, `devk` y `srak` son cables. Lo que cuestan integrados es el multiplexor: el de la entrada A de la ALU, o una entrada más en el de escritura.

### 4.2 Integrado en el segmentado

`mediciones/costo_integrado.txt`. SoC completo con `sw/trade.hex`, `nextpnr-ice40 --hx1k --package vq100 --freq 25`, semillas 1 a 10. La columna "agrega" es contra la copia sin instrucciones nuevas (995 celdas). Las 49 variantes usan 12 de 16 BRAM.

Ruido de la medición:

- **Celdas.** El segmentado del repositorio da 994 y la copia sin instrucciones 995, y son el mismo circuito. La decisión T6 pone el ruido en unas 10 celdas. Las diferencias de menos de 10 celdas de este documento no son significativas.
- **Frecuencia.** Esos mismos dos circuitos dan 51,13 y 45,55 MHz de mínima (53,50 y 48,61 de mediana). Una diferencia de fmax de menos de unos 5 MHz entre dos variantes tampoco es significativa. Lo que sí se puede afirmar es cuántas semillas cierran a 25 MHz, y el grupo de variantes "en la ALU con carriles", que queda claramente más abajo (33 a 39 MHz).

Paso de media exponencial, por conjunto de k (celdas que agrega y fmax mínima en MHz):

| Forma | k = 5 | k de 4 a 7 | k de 0 a 7 | k de 0 a 31 |
|-------|-------|------------|------------|-------------|
| `ema` autónoma (restador y sumador propios) | +167, 49,06 | +216, 46,99 | +282, 46,16 | +314: no cabe (1309) |
| `ema` con la resta de la ALU | +60, 45,42 | +117, 42,34 | +185, 38,65 | +221, 34,28 |
| `emad` (sumador de la ALU) | +37, 51,59 | +100, 45,12 | +137, 43,55 | +200, 39,24 |
| `emad` y `devk` | +113, 48,62 | +231, 42,85 | | |
| `srak` (por el multiplexor de escritura) | +57, 44,09 | | +154, 48,92 | +217, 48,71 |

`devk` solo con k = 5 agrega 41 celdas. Todas las variantes de la tabla que caben cierran 10 de 10.

Lectura: el desplazador de 32 valores cuesta entre 147 y 163 celdas más que el cableado, según la forma, y baja la frecuencia cuando queda delante del sumador de la ALU (de 51,6 a 39,2 MHz en `emad`). El shifter completo de RV32I no cabe (1491 celdas según `docs/estado.md`; no se repitió aquí). Un desplazamiento restringido a k = 5 sí, y es lo único que usa la regla base (alfa = 1/32). También le basta al candidato `max_media`, que solo cambia un umbral. Los candidatos con guardia, volatilidad o Kalman de `ref/candidatos.py` desplazan por otras constantes (`kg`, `kv`, `ka` y otras): si se elige uno de esos hay que revisar el conjunto de k antes de congelar el hardware. `emad` con k de 0 a 7 cuesta +137 y con todos +200, y las dos caben.

Carriles:

| Variante | Agrega | Fmax mínima | Cierran |
|----------|--------|-------------|---------|
| Unidad aparte, mínimo (`padd8`, `psub8`, `pcmpltu8` con máscara) | +165 | 50,02 | 10 de 10 |
| Lo mismo con la comparación de un bit por carril | +145 | 47,35 | 10 de 10 |
| Más `pcmplt8` | +161 | 46,04 | 10 de 10 |
| Más `pminu8` y `pmaxu8` | +261 | 49,21 | 10 de 10 |
| Más `paddus8` y `psubus8` | +172 | 49,65 | 10 de 10 |
| Más `pbcast8` | +167 | 46,33 | 10 de 10 |
| Más `pmovmsk8` | +168 | 44,04 | 10 de 10 |
| Kernel de bandas (saturadas, `pbcast8`, `pmovmsk8`) | +186 | 50,68 | 10 de 10 |
| Las diez operaciones | +278 | 47,81 | 10 de 10 |
| En el sumador de la ALU, mínimo | -8 | 36,14 | 10 de 10 |
| En el sumador de la ALU, más saturadas | -11 | 36,08 | 10 de 10 |
| En el sumador de la ALU, más `pbcast8` | +29 | 36,49 | 10 de 10 |

Lectura: como unidad aparte, la mayor parte del costo es fijo (unas 165 celdas: cuatro sumadores de 9 bits y una entrada de 32 bits en el multiplexor de escritura). La comparación con signo, las saturadas, `pbcast8` y `pmovmsk8` cuestan menos que el ruido cada una. El mínimo y el máximo cuestan 96 celdas. Compartiendo el sumador de la ALU los carriles salen gratis en celdas (-8 y -11 están dentro del ruido), pero cortar el acarreo cada 8 bits baja la frecuencia máxima de unos 46 a 51 MHz a unos 36 MHz. Sigue cerrando a 25 MHz en las 10 semillas, con el período mínimo en 27,7 ns de 40. Esa integración no tiene `pcmplt8`, `pminu8`, `pmaxu8` ni `pmovmsk8`.

Producto y cociente:

| Variante | Agrega | Fmax mínima | Cierran |
|----------|--------|-------------|---------|
| `mulstep` con sumador propio | +136 | 45,22 | 10 de 10 |
| `mulstep` en el sumador de la ALU | +42 | 47,59 | 10 de 10 |
| `divstep` (restador propio de 26 bits) | +108 | 50,67 | 10 de 10 |
| `mulstep` en la ALU y `divstep` | +150 | 45,84 | 10 de 10 |
| `mulc` de 8 x 8 | +184 | 48,84 | 10 de 10 |
| `mulc` de 16 x 8 | +343: no cabe (1338) | | 0 de 10 |
| Periférico multiplicador serial de 24 x 8 | +198 | 44,12 | 10 de 10 |

Los costos no se suman: `emad` (+37) y `devk` (+41) juntas agregan 113, porque recién con dos instrucciones aparece el multiplexor de 32 bits del operando A. Con ese multiplexor ya puesto, `mulstep` agrega 11 más (124 las tres). Por eso se midieron las combinaciones (tabla de la sección 1).

## 5. Tiempo: `trade.s` con las instrucciones

`mediciones/ticks_xd.txt`. Serie de práctica, 20 000 ticks, período de la ronda 3, Verilator. Cada versión pasa por una copia parametrizada del testbench oficial (4/4 y `decisiones.csv` idéntico al de `ref/trader.py`) y por `tb/tb_cpi.sv` del repositorio sin modificar. Las instrucciones nuevas van como `.word`.

| Core | Programa | Instr. por tick | Respuesta: promedio y peor caso | Tick: mínimo, promedio y peor caso | CPI |
|------|----------|-----------------|---------------------------------|------------------------------------|-----|
| Base | solo software | 28,50 | 41,00 y 44 | 60, 63,00 y 66 | 2,211 |
| Base | `srak` y `add` | 22,12 | 40,50 y 44 | 46, 49,50 y 53 | 2,237 |
| Base | `emad` | 21,13 | 40,50 y 44 | 44, 47,50 y 51 | 2,249 |
| Base | `ema` | 21,13 | 40,50 y 44 | 44, 47,50 y 51 | 2,249 |
| Base | `devk` y `emad` | 16,12 | 30,50 y 34 | 34, 37,50 y 41 | 2,326 |
| Segmentado | solo software | 28,20 | 22,00 y 26 | 32, 34,00 y 38 | 1,206 |
| Segmentado | `srak` y `add` | 22,20 | 22,00 y 26 | 25, 27,00 y 31 | 1,216 |
| Segmentado | `emad` | 21,20 | 22,00 y 26 | 24, 26,00 y 30 | 1,226 |
| Segmentado | `ema` | 21,20 | 22,00 y 26 | 24, 26,00 y 30 | 1,226 |
| Segmentado | `devk` y `emad` | 16,20 | 17,00 y 21 | 19, 21,00 y 25 | 1,296 |

"Respuesta" es de `byte_done` a la escritura de `DECISION`, que es lo que mide el testbench oficial. "Tick" llega hasta que el programa vuelve a sondear. Los dos incluyen la espera del sondeo. Las instrucciones nuevas cuestan lo mismo que una de la ALU, 2 ciclos en el base y 1 en el segmentado: el modelo de costo de `tb_cpi.sv` coincide con el RTL en las diez corridas.

El bloque de la media pasa de 8 instrucciones a 1 con `emad` o con `ema`, y a 2 con `srak`. Con `devk` además el bloque "predecir" pasa de 6 a 1, y ese sí está antes de `DECISION`.

## 6. Amdahl y la escalera de la clase 7

`mediciones/amdahl.txt`. El perfil sale de contar las instrucciones de `sw/trade.s` por bloque con el modelo de costo que `tb_cpi.sv` comprueba: el tick sin la espera son 27 instrucciones, 58 ciclos en el base y 31 en el segmentado. La actualización de la media son 8 instrucciones, 17 ciclos en el base (29,3 %) y 9 en el segmentado (29,0 %).

Predicho contra medido. f es la fracción del tiempo medido que ocupan los bloques reemplazados y F cuánto se aceleran:

| Core | Versión | Ventana | f | F | S predicho | S medido |
|------|---------|---------|---|---|------------|----------|
| Base | `emad` o `ema` | tick | 0,270 | 8,50 | 1,312 | 1,326 |
| Base | `emad` o `ema` | respuesta | 0 | | 1,000 | 1,012 |
| Base | `devk` y `emad` | tick | 0,460 | 7,25 | 1,658 | 1,680 |
| Base | `devk` y `emad` | respuesta | 0,293 | 6,00 | 1,323 | 1,344 |
| Segmentado | `emad` o `ema` | tick | 0,265 | 9,00 | 1,308 | 1,308 |
| Segmentado | `emad` o `ema` | respuesta | 0 | | 1,000 | 1,000 |
| Segmentado | `devk` y `emad` | tick | 0,441 | 7,50 | 1,619 | 1,619 |
| Segmentado | `devk` y `emad` | respuesta | 0,273 | 6,00 | 1,294 | 1,294 |

En el segmentado lo predicho y lo medido coinciden. En el base difieren en medio ciclo de 63 por la espera del sondeo, cuya fase cambia con el largo del tick.

La escalera de la clase 7 sobre el kernel "actualizar el estimador y decidir". Una operación útil es una decisión, y MOPS = 25 MHz / ciclos por decisión. Todas las filas están medidas:

| Peldaño | Instr. por decisión | Ciclos por decisión | CPI | MOPS | Speedup | Costo |
|---------|---------------------|---------------------|-----|------|---------|-------|
| 0. Espino base, solo software | 28,50 | 63,00 | 2,211 | 0,397 | 1,00 | referencia |
| 1. Extensión de la ISA: `emad` | 21,13 | 47,50 | 2,249 | 0,526 | 1,33 | no medido en el base |
| 1. Extensión de la ISA: `devk` y `emad` | 16,12 | 37,50 | 2,326 | 0,667 | 1,68 | no medido en el base |
| 2. Pipeline de 3 etapas, solo software | 28,20 | 34,00 | 1,206 | 0,735 | 1,85 | 995 celdas |
| 2 + 1. Pipeline y `emad` | 21,20 | 26,00 | 1,226 | 0,962 | 2,42 | +37 celdas |
| 2 + 1. Pipeline, `devk` y `emad` | 16,20 | 21,00 | 1,296 | 1,190 | 3,00 | +113 celdas |

El peldaño del SIMD empaquetado se midió sobre otro kernel, el de cuatro bandas (`mediciones/kernel_bandas.txt`). Una operación útil es evaluar una banda: entrar, salir y actualizar la posición de una estrategia.

| Core | Versión | Instr. del kernel | Ciclos | Ciclos por banda | MOPS | Speedup |
|------|---------|-------------------|--------|------------------|------|---------|
| Base | escalar | 30 | 60 | 15,00 | 1,67 | 1,00 |
| Base | carriles | 8 | 16 | 4,00 | 6,25 | 3,75 |
| Segmentado | escalar | 30 | 30 | 7,50 | 3,33 | 1,00 |
| Segmentado | carriles | 8 | 8 | 2,00 | 12,50 | 3,75 |

Predicho por conteo de instrucciones: 30 / 8 = 3,75, igual a lo medido, porque el kernel no tiene loads ni saltos. Con el lazo de prueba completo (6 instrucciones más por vuelta) el speedup medido es 2,63 en el base y 2,57 en el segmentado. Se midió con la unidad aparte (`-DXD_SIMD=28`, +186 celdas). Con los carriles en la ALU el kernel no tiene `pmovmsk8` y habría que entregar las posiciones como máscaras: no se midió.

Lo que queda como predicción: un tick completo de `trade.s` que evalúe cuatro bandas no existe como programa. Armado con el perfil, serían 60 ciclos con el kernel escalar y 38 con carriles en el segmentado (S = 1,58), y 25 con `devk` y `emad` además (S = 2,40). Está marcado como estimado en `mediciones/amdahl.txt`.

## 7. Contabilidad propia: producto y división

`mediciones/contabilidad.txt` (`tools/contabilidad.py`).

Anchos, con caja inicial entre 1 000 y 100 000 y precio entre 1 y 255:

| Cantidad | Máximo | Bits |
|----------|--------|------|
| Precio | 255 | 8 |
| Acciones por orden | 63 | 6 |
| Costo de una orden | 16 065 | 14 |
| Caja inicial | 100 000 | 17 |
| Acciones con la caja inicial más grande y precio 1 | 99 995 | 17 |
| Acciones si el patrimonio se multiplica por 100, con precio 1 | 10 000 000 | 24 |
| Multiplicando que acepta `mulstep` con 8 pasos | 16 777 215 | 24 |

El multiplicador es siempre el precio (8 bits, 8 pasos) y el multiplicando las acciones o la cantidad de la orden. El producto cabe en 32 bits. Un multiplicador combinacional de 8 x 8 no alcanza para valorizar la posición (las acciones pasan de 8 bits) y el de 16 x 8 no cabe en la FPGA.

La división aparece en un solo lugar: la compra recortada, `(caja - comisión) div p`, cuando la caja no alcanza para las 63 acciones. Ahí el cociente es menor que 63, la condición de `divstep` (`N < 256 D`) se cumple siempre y el resto de la división es la caja que queda. La venta se recorta con una comparación.

Comprobación: una contabilidad escrita con las funciones `mulstep` y `divstep` del modelo da caja, acciones y patrimonio idénticos a `ref/market.py` en 780 000 ticks de 309 corridas (la serie de práctica con caja 1 000, 10 000 y 100 000 y comisión 0, 5 y 50, y 300 series al azar con órdenes al azar). Peor caso por tick: 2 productos y 1 cociente. **Es una comprobación del modelo en Python. No hay un programa en assembly de la contabilidad ni se corrió en el RTL.**

Formas de multiplicar y dividir (instrucciones contadas a mano: estimado):

| Forma | Instrucciones | Celdas que agrega | Nota |
|-------|---------------|-------------------|------|
| Producto solo con RV32E (sumar y duplicar) | 48 | 0 | sin saltos |
| Producto con `mulstep` | 10 | +42 | 8 pasos, más dejar el precio en los 8 bits altos con `sb` y `lw` |
| Producto con el periférico | 3 + 2 | +198 | `sw`, `sw`, dos instrucciones cualesquiera y `lw`. Tiene estado: un solo hilo |
| Producto con `mulc` | 1 | +184 con 8 x 8 | 16 x 8 no cabe |
| Cociente con 6 restas de prueba en RV32E | 35 | 0 | |
| Cociente y resto con `divstep` | 11 | +108 | 8 pasos |
| Cociente buscando con el multiplicador | 60 | 0 con `mulstep` | 6 pasos de búsqueda binaria |

Contabilidad completa de un tick en el peor caso (estimado): 43 instrucciones con `mulstep` y `divstep`, 67 con `mulstep` y sin `divstep`, 143 solo con RV32E. En el barrel, a 4 ciclos por instrucción de un hilo, son 172, 268 y 572 ciclos de los 2262 de la ronda más rápida. Las tres caben. `divstep` ahorra 96 ciclos por tick en el peor caso y cuesta 108 celdas: no se justifica en la FPGA.

El periférico necesita que la lectura se pida 9 ciclos o más después de escribir `MULB`. En el barrel eso son dos instrucciones del hilo entre el `sw` y el `lw` (12 ciclos). En el segmentado son 8 ciclos de espera.

No se construyó un divisor que comparta el sumador de la ALU. `divstep` necesita elegir entre el resto restado y el resto sin restar según el signo de esa misma resta, o sea un multiplexor después del sumador, que es justo el camino crítico. Queda sin medir.

## 8. Guía para integrar en el barrel

Todas las instrucciones son combinacionales, de un ciclo y sin estado: caben en la etapa de ejecución de un pipeline sin detenciones sin tocar el control. El resultado sale en el mismo punto que el de la ALU, así que lo que el core haga con el resultado de una instrucción de la ALU sirve igual. El único bloque con estado es el periférico.

Interfaces:

| Módulo | Entradas | Salida | Parámetros |
|--------|----------|--------|------------|
| `xd_opa` | `rs1_i`, `funct3_i`, `funct7_i` | `a_o` (operando A de la ALU), `b_cero_o` (anular el operando B) | `MULSTEP`, `EMAD_KB`, `DEVK_KB`, `BCAST`, `K0` |
| `xd_alu` | las de `espino_alu` más `lane_op_i[2:0]` | las de `espino_alu` | ninguno |
| `xd_unit` | `rs1_i`, `rs2_i`, `alu_i`, `funct3_i`, `funct7_i` | `result_o` | `EMA_KB`, `EMA_ALU`, `SIMD`, `MULSTEP`, `DIVSTEP`, `MULC_AW`, `SRAK_KB` |
| `xd_ema`, `xd_srak` | `a_i`, `b_i`, `k_i[4:0]` | `r_o` | `KB` (0, 2, 3 o 5), `K0` |
| `xd_simd8` | `a_i`, `b_i`, `op_i[3:0]` | `r_o` | `CON_SIGNO`, `MINMAX`, `SATURA`, `BCAST`, `MOVMSK`, `CMP_BIT` |
| `xd_mulstep`, `xd_divstep`, `xd_mulc` | `a_i`, `b_i` | `r_o` | `AW`, `BW` en `xd_mulc` |
| `xd_mul_mmio` | `clk_i`, `rst_ni`, `req_i`, `we_i`, `off_i[1:0]`, `wdata_i` | `rdata_o` (registrada) | ninguno |

Pasos para el subconjunto recomendado (`emad`, `devk` y `mulstep` en el sumador de la ALU), tomando como ejemplo lo que se hizo en `core/espino_core/espino_id_stage.v`:

1. **Decodificador.** Usar `core/espino_core/espino_decoder.v` en lugar del original, con `XdEmad = 1`, `XdDevk = 1` y `XdMulAlu = 1`. Para esas tres instrucciones entrega `alu_op_a_sel_o = 3`, `alu_op_b_sel_o` en registro, `alu_operator_o` en suma (resta en `devk`) y `rf_we_o = 1`. Con los parámetros en cero es el decodificador original.
2. **Operando A.** La selección 3 del multiplexor del operando A está libre en el Espino y también en `espino_barrel_core.v` (usa 0, 1 y 2). Ahí va `a_o` de `xd_opa`, que recibe `rs1` y los campos `funct3` y `funct7` de la instrucción que está en ejecución. En el barrel hay que llevar esos campos a la etapa X: con k fijo bastan los 3 bits de `funct3`.
3. **Operando B.** Cuando la selección de A es 3 y `b_cero_o` vale 1, el operando B es cero (`mulstep` con el bit que sale en 0).
4. **Nada más.** No hay camino nuevo hacia el banco de registros: el resultado es el de la ALU.

Para los carriles en la ALU se agrega `XdLanes` al decodificador, se registra `lane_op_o` hasta la etapa X y se instancia `xd_alu` en vez de `espino_alu`. Para lo que va por `xd_unit` (carriles en unidad aparte, `divstep`, `mulc`, `srak`, `ema`) el decodificador entrega `is_xd_o`, que también se registra hasta X y elige `result_o` de `xd_unit` en vez del resultado de la ALU.

Cosas que cambian en el barrel y que esta parte no midió:

- El costo marginal. El barrel deja 346 celdas libres según `factibilidad/a_barrel/mediciones/recursos.txt`. Si las instrucciones costaran lo mismo que en el segmentado, `emad`, `devk` y `mulstep` dejarían unas 222. Es una resta, no una medición.
- La frecuencia. Los carriles en la ALU bajaron la fmax mínima del segmentado a unos 36 MHz. En el barrel la ALU está sola en su etapa y el efecto puede ser distinto.
- `mulstep` y `divstep` llevan todo su estado en `rs1`, así que cada hilo puede tener un producto en curso. El periférico no: tiene un solo producto en curso para todo el SoC.

## 9. Ensamblador

`tools/` no se modificó. Las instrucciones se entregan como `.word`:

```
python3 tools/xd_word.py emad x3, x6, x3, 5          # imprime: .word 0x0a33418b   # emad x3, x6, x3, 5
python3 tools/xd_word.py --pre sw/trade_media.s -o build/sw/trade_media.s
python3 ../../tools/pochoasm.py build/sw/trade_media.s -o build/sw/trade_media.hex
make sw                                              # lo anterior para todos los programas de sw/
```

`--pre` reemplaza cada línea que usa un mnemónico nuevo por su `.word`, con la instrucción original de comentario, y entiende constantes definidas con `.equ` en el campo k. La codificación sale de `ref/xd.py`, la misma función que usan los testbenches.

Trabajo estimado para agregarlas a `tools/asm/` (medio día):

- `isa.py`: una tabla de custom-0 con `funct3` y `funct7` por mnemónico. El codificador de formato R ya existe.
- `core.py`: una rama en `_encode_instruction` (todas ocupan una palabra) y la validación de k entre 0 y 31.
- Una opción con el subconjunto del core, para rechazar un k o una operación que el hardware no tiene. Hace falta porque el hardware no lo detecta (`ESPECIFICACION.md`, sección 1).
- `disasm.py`: decodificar las palabras nuevas.
- Pruebas de ida y vuelta y de rechazo, en el estilo de las 80 que ya tiene, y la sección correspondiente de `docs/ensamblador.md`.

## 10. Verificación

Qué se corrió, con los conteos de las salidas guardadas:

| Prueba | Alcance | Resultado |
|--------|---------|-----------|
| Autoprueba del modelo (`ref/xd.py`) | 2 725 001 casos: identidades entre instrucciones, la regla de `trade.s`, productos y cocientes contra Python | PASS |
| Testbench por módulo (`make tb`) | 25 corridas, 13 968 223 vectores o ciclos. Carriles exhaustivos: cada carril recorre los 65 536 pares de cada operación, con una permutación distinta por carril. `ema`, `emad` y `devk` con k = 5 en todo el dominio de la regla base (S de 32 a 8160 por precio de 1 a 255). `mulstep` y `mulc` de 8 x 8 exhaustivos. El resto, esquinas cruzadas y al azar | PASS |
| Mutaciones en simulación | Un error puesto a propósito en cada módulo | 9 de 9 detectadas |
| Instrucciones dentro del core (`make tb-core`) | 33 variantes por 2 cores (base y segmentado): 396 programas al azar, 73 116 instrucciones nuevas, 181 110 escrituras al banco comparadas con el modelo. Incluye `rd = x0`, `rd` igual a un operando y uso del resultado en la instrucción siguiente | PASS |
| Subconjunto recomendado dentro del core (`make tb-core-recomendado`) | `emad`, `emad` con `devk`, y las dos con `mulstep`, por 2 cores: 1 200 programas, 228 232 instrucciones nuevas, 573 420 escrituras al banco comparadas | PASS |
| Formal (`make formal`) | 12 propiedades con sby, para todas las entradas: `ema` en los cuatro conjuntos de k contra la fórmula; equivalencia entre `ema` autónoma, `ema` con la resta de la ALU y `sub` más `emad`; `devk`, `mulstep` y `pbcast8` por el sumador de `espino_alu`; `xd_alu` con `lane_op = 0` igual a `espino_alu`; los carriles de `xd_alu` y los diez de `xd_simd8` contra la especificación; 8 pasos de `mulstep` con multiplicando de 12 bits; 8 pasos de `divstep` con divisor de 8 bits; un paso de `divstep` con divisor de 24 bits | PASS |
| Controles negativos formales | 7 mutaciones: sby encuentra el contraejemplo | 7 de 7 |
| La extensión no cambia RV32E (`make sin-cambios`) | Etapa ID del repositorio contra la de la copia, con los pases `equiv_*` de Yosys, en el Espino base: sin definiciones (1278 puntos de comparación) y con la extensión encendida y custom-0 reemplazada por un nop (1214 puntos) en cuatro subconjuntos, incluido el recomendado y el de todas las instrucciones | 5 casos probados, y el control negativo falla como debe |
| Equivalencia de `trade.s` (`make medir-ticks`) | 5 versiones por 2 cores, 20 000 ticks al período de la ronda 3: 4/4 en la copia del testbench oficial y `decisiones.csv` idéntico al de `ref/trader.py` | PASS |
| Combinaciones candidatas por el testbench oficial (`make equiv-combinaciones`) | Las cuatro combinaciones que caben (recomendada, todo en la ALU, todo en la ALU con `divstep`, y `emad` con carriles en unidad aparte) por 2 cores, 20 000 ticks: 4/4 y `decisiones.csv` idéntico al de `ref/trader.py`. Peor caso de la respuesta según el testbench: 34 ciclos en el base y 21 en el segmentado con `devk` y `emad` | PASS |
| Kernel de bandas (`make kernel`) | 3 programas por 2 cores, 256 vueltas: resultados iguales al modelo | PASS |
| Contabilidad (`make contabilidad`) | 780 000 ticks contra `ref/market.py`, solo en Python | PASS |

Errores encontrados: las pruebas guardadas no muestran ninguna diferencia entre el RTL y el modelo. Al revisar el periférico multiplicador se corrigió una imprecisión de un ciclo en la descripción de sus tiempos: el comentario decía que bastaba pedir la lectura 8 ciclos después de escribir `MULB` y el modelo y el RTL exigen 9. Era el texto, no el circuito: el testbench ya comprobaba el valor correcto. La estimación de instrucciones del periférico pasó de "3 + 1" a "3 + 2".

Lo que no quedó probado:

- Formal de punta a punta del producto con multiplicando de 16 o 24 bits y del cociente con divisor de 24 bits: ni boolector ni yices terminaron en 200 a 300 s. Los cubren la propiedad de un paso y la simulación.
- Que la extensión no cambie las instrucciones de RV32E **en el segmentado**. En el Espino base quedó probado formalmente (`make sin-cambios`). En el segmentado el mismo método no alcanza: la copia tiene un registro que el original no tiene (`is_xd_q`) y la inducción parte de estados que después del reset no se alcanzan. Ahí la evidencia es por simulación.
- Que los carriles en el sumador de la ALU no cambien nada visible. `xd_alu` deja la resta donde `espino_alu` deja la suma durante un branch, y ese valor sale por el bus de direcciones sin petición de acceso. La prueba formal de `xd_alu` lo excluye a propósito y `make sin-cambios` lo muestra como 93 puntos sin probar, todos en `alu_result` y `lsu_addr_o`. Que nadie use ese valor está respaldado solo por simulación.
- La ejecución en paralelo con un millón de instrucciones que exige el frente B. Dentro del core, el subconjunto recomendado se probó con unas 38 000 instrucciones nuevas por variante y por core, y el resto de las variantes con unas 1 100.
- Nada se probó sobre el barrel ni en la placa.

## 11. Qué habría que sacrificar para que quepa

El conjunto completo ocupa 2505 celdas, casi el doble de la FPGA. Lo que hay que soltar, con lo que recupera cada cosa:

| Sacrificio | Celdas que recupera | Qué se pierde |
|------------|---------------------|---------------|
| k fijo en 5 en vez de 0 a 31 | 163 en `emad` (200 a 37) | Cambiar alfa exige volver a sintetizar. Si alfa cambia después del 26/11, el hardware ya no sirve |
| `emad` y `devk` en vez de `ema` autónoma | 54 (167 a 113), y además reemplazan un bloque más | Nada: hacen lo mismo en dos instrucciones |
| `mulstep` en la ALU en vez del periférico | 156 (198 a 42) | El producto ocupa 10 instrucciones del hilo en vez de 5 (estimado) |
| Sin `mulc` de 16 x 8 | 343 | El producto en una instrucción |
| Sin `divstep` | 108 | 24 instrucciones más en el tick de una compra recortada |
| Carriles en la ALU en vez de unidad aparte | 157 (186 a 29) | Unos 14 MHz de fmax mínima (de 50,7 a 36,5), y `pcmplt8`, `pminu8`, `pmaxu8` y `pmovmsk8` |
| Sin mínimo y máximo por carril | 96 | Dos operaciones que el kernel de bandas no usa |

Lo más grande que cabe es `emad`, `devk`, `mulstep`, los carriles de bandas en la ALU y `divstep`: 1226 celdas, 54 libres y fmax mínima de 33,0 MHz. Con los carriles en unidad aparte la combinación con `emad`, `devk` y `mulstep` queda en 1282 celdas, 2 sobre el límite. Dos celdas están dentro del ruido del conteo, pero un diseño que cabe o no según la síntesis no sirve para la competencia.

Fuera de esta pieza, el estudio del barrel midió que quitar la emulación de lectura durante escritura de la memoria recupera entre 110 y 167 celdas según el core. Eso daría espacio para los carriles en unidad aparte. No es una medición de esta carpeta.

## 12. Días de trabajo que faltan

Estimado, para llevar el subconjunto recomendado (`emad`, `devk` y `mulstep`) a calidad de competencia:

| Tarea | Días |
|-------|------|
| Integrar en el core elegido (el barrel, si se elige) y medir celdas y fmax en 10 semillas | 0,5 |
| Ensamblador: `tools/asm/`, desensamblador, opción de subconjunto, pruebas y documento | 0,5 |
| Gemelo digital: instrucciones nuevas y validación ciclo a ciclo contra el RTL | 0,5 |
| Verificación: generador aleatorio del repositorio con las instrucciones nuevas, ejecución en paralelo de al menos un millón de instrucciones, mutaciones sobre el core integrado y equivalencia formal del core sin la extensión | 1 |
| Equivalencia: `trade.s` definitivo con las instrucciones, `make equiv` en todas las variantes a los tres períodos, testbench oficial 4/4 e integración continua | 0,5 |
| Documentación: especificación en `docs/`, documento de estudio, preguntas de la defensa y la escalera en el informe | 1 |
| **Total** | **4** |

Aparte, si se eligen:

- Carriles en el programa de competencia: 1 día más (el kernel real dentro del programa del fondo y su equivalencia). Depende de la pieza B.
- Contabilidad propia en assembly con `mulstep`: 1,5 días (programa, referencia y equivalencia contra `ref/market.py` en el RTL). También es de la pieza B.
- La prueba con la maestra del 26/11 la hace Nicolás.

## 13. Archivos copiados y qué se les cambió

`core/` es una copia de `rtl/` del repositorio (commit 849a755). Conservan su encabezado de licencia y de autor. Nueve archivos son idénticos al original (`diff` sin salida): `pochoco_periph.v`, `pochoco_ram.v`, `pochoco_spi_slave.v`, `espino_alu.v`, `espino_controller.v`, `espino_core.v`, `espino_if_stage.v`, `espino_load_store_unit.v` y `espino_register_file.v`. Cambian tres:

| Archivo | Cambio | Por qué |
|---------|--------|---------|
| `core/espino_core/espino_decoder.v` | Parámetros `XdF3`, `XdEmaAlu`, `XdMulAlu`, `XdEmad`, `XdDevk` y `XdLanes`, salidas `is_xd_o` y `lane_op_o`, y la rama del opcode custom-0 | Decodificar las instrucciones nuevas. Con los parámetros por defecto es el original |
| `core/espino_core/espino_id_stage.v` | Definiciones `XD_*`, `xd_opa` en la selección 3 del operando A, anulación del operando B, `xd_alu` o `espino_alu`, `xd_unit` y su entrada al multiplexor de escritura | Integrar cada instrucción de la forma elegida, en el base y en el segmentado |
| `core/pochoco_soc.v` | Con `-DXD_MULMMIO`, el periférico `xd_mul_mmio` en `0x8002_0000` | Medir la alternativa del periférico. El mapa del esclavo SPI y el de `pochoco_periph` no cambian |

No se renombró nada de lo que el testbench oficial usa por jerarquía. `sw/trade_sw.s` es `sw/trade.s` con los comentarios resumidos, para medir la versión de solo software con el mismo flujo. Las otras cuatro versiones cambian solo los bloques marcados con "XD".

## 14. Reglas del enunciado

- **"La decisión se debe calcular en el Espino Core en la placa. El core debe leer el precio y escribir la decisión; el hardware agregado puede acelerar partes del algoritmo, pero no reemplazar al procesador en el ciclo de decisión."** Se cumple. Las instrucciones son operaciones aritméticas sin estado: un desplazamiento con suma, operaciones por carril, un paso de multiplicación. El programa sigue leyendo `PRICE` con un `lw`, compara contra los umbrales con `slti`, arma el byte y lo escribe con un `sw`. Ninguna instrucción recibe un precio y entrega una decisión o una posición, y ninguna guarda nada entre un tick y el siguiente: la media, la posición y las bandas viven en registros del programa. El límite estaría en un bloque que entregue la decisión ya calculada o que lleve él mismo el estado del algoritmo, por ejemplo un periférico que reciba el precio y devuelva "comprar" o "vender", o una instrucción que reciba precio y estado y devuelva el byte de decisión. Un periférico estimador que mantenga la media por su cuenta al llegar cada precio está más cerca de ese límite que cualquier cosa de esta pieza, y es una pregunta que ya está pendiente con el ayudante.
- **"No se puede usar información externa a la serie recibida por SPI ni almacenar series de precios en el diseño."** Se cumple. No hay tablas ni memoria. El único estado es el del periférico multiplicador: un producto en curso.
- **"Todo hardware agregado debe estar en el repositorio con su testbench."** Cada módulo tiene su testbench en `tb/` y su prueba formal. Para entrar al repositorio tendrían que pasar de esta carpeta a `rtl/` y `tb/`.
- **"Deben usar el mismo programa para todas las series de tiempo."** No cambia: la extensión no depende de la ronda.
- **"Pueden modificar libremente el RTL, siempre que el procesador siga siendo Espino."** Las instrucciones de RV32E no cambian: con los carriles apagados `xd_alu` entrega lo mismo que `espino_alu` (probado formalmente) y sin definiciones el decodificador es el original. Se usa custom-0, el opcode que RISC-V reserva para extensiones propias.
- **Testbench oficial.** No se modificó. Las mediciones usan una copia parametrizada, igual que `tools/equiv.sh`. No se renombró `pochoco_soc`, sus puertos, `MemFile`, `u_spi` ni sus señales, y el mapa de registros del SPI no cambió.

Preguntas para el ayudante:

1. Si agregar instrucciones propias en custom-0 mantiene al procesador como "Espino" para efectos de la regla.
2. Si `tools/pochoasm.py` se puede extender con mnemónicos nuevos, o si el programa entregado debe ensamblarse con el ensamblador sin cambios (en ese caso van como `.word`).
3. Si una instrucción que hace el paso completo del estimador (`emad`) cuenta como "acelerar partes del algoritmo". Entendemos que sí, porque la decisión la sigue calculando el programa.
4. Si el testbench oficial se va a correr contra nuestro repositorio con nuestro RTL: un core sin la extensión marca estas instrucciones como ilegales.

## 15. Riesgos

1. **No cambia el resultado de la competencia.** Las decisiones son las mismas y el tiempo sobra. Meter hardware nuevo en el bitstream de competencia arriesga los 2,0 puntos de la competencia a cambio de nada en patrimonio. Los puntos de co-diseño se pueden defender igual desde la edición de exhibición, con estas mismas mediciones.
2. **El costo sobre el barrel no está medido.** Todo el costo marginal es sobre el segmentado de 3 etapas.
3. **Compartir la ALU mueve el camino crítico y cambia un valor que no se usa.** Los carriles en la ALU dejan la fmax mínima en 33 a 36 MHz: cierra a 25 MHz, pero el margen baja de unos 20 ns a unos 10 ns de los 40 del período. Además `xd_alu` entrega otro resultado que `espino_alu` durante un branch, que sale por el bus de direcciones sin petición de acceso (sección 10). Las simulaciones no muestran efecto, pero no está probado formalmente.
4. **k cableado.** Con k = 5 fijo, un programa ensamblado con otro k se ejecuta con k = 5 sin aviso. Hasta que el ensamblador lo rechace, es un error silencioso posible. Además amarra el hardware al alfa de la regla base: si el algoritmo final necesita otros desplazamientos (los candidatos con guardia los usan), el conjunto de k tiene que decidirse antes del 26/11, porque después el hardware no se toca.
5. **Operaciones de carril no incluidas.** En la unidad aparte, una operación que no se sintetizó entrega otra cosa sin marcar la instrucción como ilegal.
6. **El ruido de la medición.** Diez celdas y unos 5 MHz entre síntesis del mismo circuito. Las conclusiones de este documento se apoyan en diferencias mayores, salvo donde se dice lo contrario.
7. **La contabilidad propia solo existe en Python.** Los conteos de instrucciones del producto y del cociente son estimaciones a mano.
8. **Dependencia de otras piezas.** Los carriles y la contabilidad solo sirven si se elige el fondo de estrategias. Sin la pieza B no tienen uso en el programa de competencia.
9. **Ensamblador y gemelo.** Mientras no conozcan las instrucciones, el flujo de equivalencia del repositorio no las cubre.

## 16. Veredicto según los criterios de corte

Criterio de hardware: se descarta de la edición de competencia lo que no cabe junto al SPI (1280 celdas y 16 BRAM) o no cierra a 25 MHz en las 10 semillas.

| Parte | Cabe | Cierra 10 de 10 | Veredicto |
|-------|------|-----------------|-----------|
| `emad` y `devk` con k = 5, y `mulstep`, en el sumador de la ALU (1119 celdas, 12 BRAM, fmax mínima 47,1 MHz) | Sí, 161 libres | Sí | **Competencia**, como candidata: falta medirla sobre el core elegido y pasar por la maestra |
| Solo `emad` con k = 5 (1032 celdas, fmax mínima 51,6 MHz) | Sí, 248 libres | Sí | **Competencia**, es la opción de menor riesgo si se quiere una sola instrucción |
| Carriles del kernel de bandas (unidad aparte: +186; en la ALU: +29 y fmax mínima 36,5 MHz) | Sí | Sí | **Competencia solo si se elige el fondo de estrategias** y el programa los usa. Si no, exhibición |
| `divstep` (+108) | Sí | Sí | **Exhibición**: 108 celdas por 24 instrucciones en un tick poco frecuente |
| Periférico multiplicador (+198) | Sí | Sí | **Exhibición**: `mulstep` hace lo mismo con 42 celdas y sin estado |
| `ema` en una instrucción (+60 con la resta de la ALU) | Sí | Sí | **Exhibición**: `emad` hace lo mismo con 37 |
| `mulc` de 16 x 8, todos los k en la versión autónoma, los diez carriles con todo lo demás | No (1338, 1309 y 1466 celdas) | No | **ASIC** |
| Conjunto completo (2505 celdas) | No | No | **ASIC** |

Recomendación: si el core de competencia es el segmentado o el barrel con una sola estrategia, la extensión va completa a la edición de exhibición y a la ASIC, porque no mueve el patrimonio y agrega riesgo al bitstream. Si se elige el fondo de estrategias sobre el barrel, entran `emad`, `devk` y `mulstep` (124 celdas en el segmentado), y los carriles solo después de medirlos sobre el barrel. La decisión de qué queda en el bitstream de competencia es de Nicolás.
