# Pieza D, segunda parte, y diseño integrado: la extensión de la ISA, el vigilante y la memoria de la tabla sobre el barrel

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz. Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Estudio de factibilidad. Nada de esta carpeta está integrado en `rtl/`, en el `Makefile` de la raíz ni en la integración continua. Todos los números salen de un script de esta carpeta y su salida está guardada en `mediciones/`. La sección 3 tiene el comando de cada uno.

Este documento junta tres piezas que hasta ahora se habían medido por separado: el Espino barrel de 4 hilos (`factibilidad/a_barrel/`), la extensión de la ISA en custom-0 (`factibilidad/d_isa/`, medida solo sobre el segmentado) y el vigilante con `SB_WARMBOOT` (`factibilidad/e_warmboot/`, medido sobre el base y el segmentado). Agrega una pieza nueva, la memoria para la tabla de política del aprendizaje en vivo, y mide las configuraciones integradas candidatas.

## 1. Resultado en una página

Las cuatro configuraciones candidatas. SoC completo con el esclavo SPI y los periféricos, `nextpnr-ice40 --hx1k --package vq100 --freq 25`, semillas 1 a 10. La FPGA tiene 1280 celdas lógicas y 16 BRAM.

| Configuración | Qué lleva | Celdas | Libres | BRAM | Fmax mínima, mediana y máxima (MHz) | Cierran a 25 MHz | Testbench oficial |
|---------------|-----------|--------|--------|------|--------------------------------------|------------------|-------------------|
| I1 "fondo en un chip" | Barrel, `emad`, `devk` y `mulstep`, vigilante y tabla de 256 x 16 por MMIO | 1071 | 209 | 13 | 46,76, 48,62 y 50,48 | 10 de 10 | 4/4, decisiones idénticas |
| I1 con 16 BRAM | Lo mismo con la tabla en otras 512 palabras de datos | 1098 | 182 | 16 | 44,94, 48,07 y 51,83 | 10 de 10 | 4/4, decisiones idénticas |
| I2 "barrel mínimo" | Barrel y vigilante | 939 | 341 | 12 | 50,95, 53,59 y 56,09 | 10 de 10 | 4/4, decisiones idénticas |
| I3 "conservador" | Segmentado, `emad` y vigilante | 1046 | 234 | 12 | 48,02, 52,36 y 53,25 | 10 de 10 | 4/4, decisiones idénticas |
| I3 con tres instrucciones | Segmentado, `emad`, `devk`, `mulstep` y vigilante | 1142 | 138 | 12 | 46,59, 48,05 y 49,14 | 10 de 10 | 4/4, decisiones idénticas |
| I4 referencia | Segmentado de `rtl/`, sin tocar | 994 | 286 | 12 | 51,13, 53,50 y 54,50 | 10 de 10 | 4/4, decisiones idénticas |
| I4 referencia | Espino base de `rtl/`, sin tocar | 1083 | 197 | 12 | 42,43, 43,74 y 45,08 | 10 de 10 | 4/4 (es la referencia de las decisiones) |

Lo que se encontró:

1. **I1 cabe y cierra.** El fondo en un chip completo ocupa 1071 celdas y 13 BRAM, deja 209 celdas libres y cierra a 25 MHz en las 10 semillas con 46,8 MHz de mínima. No hubo que sacrificar nada. Ocupa 12 celdas menos que el Espino base del repositorio.
2. **La extensión cuesta menos sobre el barrel que sobre el segmentado.** `emad` agrega 26 celdas (37 en el segmentado) y el subconjunto recomendado, `emad`, `devk` y `mulstep`, agrega 90 (124 en el segmentado). La sección 4 tiene los cinco subconjuntos pedidos y sus combinaciones.
3. **Los carriles de bandas en la ALU bajan la frecuencia igual que en el segmentado.** Agregan 19 celdas y dejan la fmax mínima en 33,7 MHz (33,3 en el segmentado). Cierra a 25 MHz en las 10 semillas, pero con 10 ns de margen en vez de 19. Que la ALU esté sola en su etapa no cambió ese resultado.
4. **El vigilante cuesta 4 celdas sobre el barrel** (9 con el disparo manual), dentro del ruido del conteo, y nextpnr ubica la primitiva `SB_WARMBOOT`.
5. **Una memoria de 1024 palabras completa no cabe: necesita 20 BRAM.** El plan de este estudio suponía que usaría las 16. `pochoco_ram` guarda dos copias de cada palabra para leer la instrucción y el dato en el mismo ciclo. Lo que sí cabe en 16 BRAM son 512 palabras más que solo sirven para datos. La alternativa de una BRAM aparte de 256 x 16 por MMIO cuesta 21 celdas y deja 3 BRAM libres.
6. **Lo más grande que no cabe** es I1 con los carriles en unidad aparte y `divstep` a la vez: 1350 celdas. La sección 9 mide qué hay que soltar y en qué orden.
7. **La integración no rompió nada de lo que ya funcionaba.** Cada hilo hace lo mismo que el Espino base en 884 281 instrucciones de RV32E por configuración (6 configuraciones), las instrucciones nuevas coinciden con el modelo en los cuatro hilos (12 variantes, 240 programas cada una), las propiedades formales de estructura del barrel siguen valiendo, y 18 de 18 errores puestos a propósito se detectan.

Veredicto según los criterios de corte (detalle en la sección 14): **las cuatro configuraciones pasan los dos criterios de hardware.** Ninguna se descarta por área ni por timing. Lo que este estudio no puede decidir es si el fondo gana algo en los estudios de retorno, y eso es lo que define si I1 vale sus días de trabajo. Ningún bitstream se grabó en la placa.

## 2. Qué se construyó

RTL propio de esta carpeta (`rtl/`):

| Archivo | Qué es |
|---------|--------|
| `rtl/espino_barrel_core.v` | Copia del core del barrel con la extensión integrada en la etapa de ejecución. Las definiciones `XD_*` eligen el subconjunto, con los mismos nombres que en `factibilidad/d_isa`. Sin definiciones es el core del prototipo |
| `rtl/pochoco_soc.v` | Copia del SoC del barrel con el vigilante (`-DI_VIGILANTE`) y la memoria de la tabla (`-DI_TABLA=1` o `-DI_TABLA=2`). Sin definiciones es el SoC del prototipo |
| `rtl/espino_decoder_xd.v` | El decodificador de `factibilidad/d_isa` con otro nombre de módulo, para que conviva con el original en una misma simulación. `tools/comun.sh` avisa si deja de coincidir con el de `d_isa` |
| `rtl/tabla_mmio.v` | Memoria de la tabla, forma 1: una BRAM de 256 palabras de 16 bits por MMIO en `0x8002_0000` |
| `rtl/tabla_ram.v` | Memoria de la tabla, forma 2: otras 512 palabras de 32 bits, solo de datos, en las direcciones `0x800` a `0xFFF` |

Lo que cambió en el core respecto del prototipo del barrel (`diff factibilidad/a_barrel/rtl/espino_barrel_core.v factibilidad/i_integrado/rtl/espino_barrel_core.v`):

- Se registran entre las etapas R y X dos señales más de la decodificación: `is_xd` (el resultado sale de `xd_unit`) y `lane_op` (qué hace la ALU con los acarreos de los carriles).
- La selección 3 del multiplexor del operando A, que el barrel no usaba, entrega el operando desplazado de `xd_opa` (`emad`, `devk`, `mulstep` y `pbcast8`). En `mulstep` el operando B se anula cuando `rs1[31]` vale 0.
- `xd_opa` y `xd_unit` reciben `funct3` y `funct7` de la instrucción que está en X. La que sale de la memoria en ese ciclo es de otro hilo, y ese es el error más fácil de cometer en esta integración. Tres de las mutaciones de la sección 5 son exactamente eso.
- Con `XD_SIMDALU` se instancia `xd_alu` en vez de `espino_alu`.
- El resultado de `xd_unit` reemplaza al de la ALU en el registro entre X y M cuando `is_xd` vale 1.

No cambió nada del control del pipeline: todas las instrucciones nuevas son combinacionales, de un ciclo y sin estado.

De las otras carpetas se usan en su lugar, sin copiar ni modificar: `rtl/espino_barrel_regfile.v`, `tb/tb_verif.sv`, `formal/propiedades.vh` y los generadores de `factibilidad/a_barrel`; los módulos `rtl/xd_*.v`, el modelo `ref/xd.py`, los programas `sw/trade_*.s` y el core segmentado con la extensión de `factibilidad/d_isa`; y `rtl/vigilante.v`, la copia del esclavo SPI con las tres salidas del vigilante y el monitor `tb/mon_vigilante.sv` de `factibilidad/e_warmboot`. La configuración I3 no usa ningún archivo de esta carpeta: es el core de `d_isa` con el SoC de `e_warmboot`.

Programas y testbenches propios:

| Archivo | Para qué |
|---------|----------|
| `tb/tb_xd_barrel.sv`, `tools/gen_prog_hilos.py` | Instrucciones nuevas en los cuatro hilos contra el modelo |
| `tb/mon_mixto.sv`, `sw/kernel_media.s`, `sw/kernel_carriles.s`, `tools/modelo_kernel.py` | Regla base en el hilo 0 con el testbench oficial mientras tres hilos ejecutan instrucciones nuevas |
| `tb/tb_tabla_mod.sv`, `tb/tb_tabla.sv`, `sw/tabla_prueba.s` | Memoria de la tabla, sola y dentro del SoC con los cuatro hilos |
| `tb/tb_vig_barrel.sv`, `sw/cuelgue_supervisor.s` | Vigilante con el hilo supervisor colgado y los otros tres vivos |
| `tb/mon_boot_chip.sv` | Que BOOT no suba en la simulación del bitstream |
| `tools/mutar.py`, `tools/mutaciones.sh` | Controles negativos |
| `tools/formal.sh` | Propiedades formales de estructura sobre el core con la extensión |
| `tools/variantes.txt`, `tools/medir.sh`, `tools/informe_recursos.py` | Las 38 variantes de síntesis y su informe |

## 3. Cómo se reproduce cada número

Desde la raíz del repositorio. Hace falta OSS CAD Suite en `~/herramientas/oss-cad-suite`. Cada script usa a lo más 5 procesos.

| Comando | Qué mide | Salida | Tiempo |
|---------|----------|--------|--------|
| `make -C factibilidad/i_integrado recursos` | Celdas, BRAM y fmax en 10 semillas de las 38 variantes | `mediciones/recursos.txt` | 6 min |
| `make -C factibilidad/i_integrado tb-xd` | Instrucciones nuevas en los cuatro hilos contra el modelo, 12 variantes | `mediciones/tb_xd.txt` | 2 min |
| `make -C factibilidad/i_integrado oficial` | Testbench oficial sin modificar en 21 configuraciones | `mediciones/oficial.txt` | 11 min |
| `make -C factibilidad/i_integrado verif` | Cada hilo contra el Espino base, RV32E, 6 configuraciones | `mediciones/verif_rv32e.txt` | 1 min |
| `make -C factibilidad/i_integrado mixto` | Regla base en el hilo 0 con el testbench oficial y tres hilos con instrucciones nuevas | `mediciones/mixto.txt` | 5 min |
| `make -C factibilidad/i_integrado tabla-vigilante` | Memoria de la tabla y vigilante sobre el barrel | `mediciones/tabla_vigilante.txt` | 1 min |
| `make -C factibilidad/i_integrado mutaciones` | 18 errores puestos a propósito | `mediciones/mutaciones.txt` | 2 min |
| `make -C factibilidad/i_integrado formal` | Propiedades de estructura del barrel sobre el core con la extensión | `mediciones/formal.txt` | 20 s |
| `make -C factibilidad/i_integrado bitstreams` | Bitstream y sha256 de I1 a I4, simulados desde el `.asc` | `mediciones/bitstreams.txt` | 10 min |
| `make -C factibilidad/i_integrado todo` | Todo lo anterior | | 40 min |

Los logs de nextpnr quedan en `build/variantes/fact2_i_ETIQUETA/` de la raíz (los escribe `tools/medir_variante.sh` del repositorio). El resto de los productos intermedios queda en `build/` de esta carpeta. `tools/medir.sh '^i1'` mide solo las variantes cuya etiqueta calza con la expresión.

Ruido de la medición, igual que en los otros estudios: el conteo de celdas de un mismo circuito se mueve unas 10 celdas entre síntesis (decisión T6) y la fmax unos 5 MHz entre circuitos equivalentes. El control de esta carpeta lo muestra: el prototipo del barrel da 934 celdas y 52,7 MHz de mínima, y la copia de esta carpeta sin definiciones, que es el mismo circuito, da 935 y 51,7.

## 4. La extensión de la ISA sobre el barrel

`mediciones/recursos.txt`, sección 2. La columna "agrega" es contra la copia del barrel sin definiciones (935 celdas). Todas usan 12 BRAM.

| Subconjunto | Celdas | Agrega | Libres | Fmax mínima, mediana y máxima (MHz) | Cierran | Sobre el segmentado (`d_isa`) |
|-------------|--------|--------|--------|--------------------------------------|---------|-------------------------------|
| (a) `emad`, k = 5 | 961 | +26 | 319 | 48,58, 53,36 y 56,27 | 10 de 10 | +37, mínima 51,59 |
| `emad` y `devk`, k = 5 | 1026 | +91 | 254 | 48,56, 50,05 y 51,95 | 10 de 10 | +113, mínima 48,62 |
| (b) `emad`, `devk` y `mulstep` en el sumador de la ALU | 1025 | +90 | 255 | 48,71, 49,57 y 51,35 | 10 de 10 | +124, mínima 47,12 |
| (c) lo anterior más los carriles de bandas en la ALU | 1044 | +109 | 236 | 33,68, 35,08 y 35,66 | 10 de 10 | +166, mínima 33,31 |
| (d) lo anterior con los carriles en unidad aparte | 1198 | +263 | 82 | 46,81, 48,98 y 54,95 | 10 de 10 | +287: no cabía (1282) |
| (e) el recomendado (b) más `divstep` | 1111 | +176 | 169 | 47,52, 49,50 y 50,97 | 10 de 10 | +150 sin `emad` ni `devk` |
| (e) carriles en la ALU más `divstep` | 1136 | +201 | 144 | 34,15, 35,39 y 37,41 | 10 de 10 | +231, mínima 33,00 |
| (e) carriles en unidad aparte más `divstep` | 1312 | +377 | -32 | no termina | 0 de 10 | no se midió |

Costo marginal de cada pieza, sobre el barrel y sobre el segmentado:

| Pieza | Sobre el barrel | Sobre el segmentado |
|-------|-----------------|---------------------|
| `emad` | +26 | +37 |
| `emad`, `devk` y `mulstep` | +90 | +124 |
| Carriles en la ALU, encima de (b) | +19 | +42 |
| Carriles en unidad aparte, encima de (b) | +173 | +163 |
| `divstep`, encima de (b) | +86 | +108 (medido sin `emad` ni `devk`) |
| `divstep`, encima de (c) | +92 | +65 |

Lectura:

- **El recomendado cuesta 34 celdas menos que en el segmentado** (90 contra 124) y `emad` sola 11 menos. La diferencia es mayor que el ruido en el subconjunto recomendado. No se investigó de dónde sale. Una explicación posible es que en el segmentado el operando A pasa además por el multiplexor de adelantamiento, y el barrel no tiene adelantamiento.
- **Igual que en el segmentado, los costos no se suman.** `emad` y `devk` juntas agregan 91 y con `mulstep` son 90: el multiplexor de 32 bits del operando A aparece con la segunda instrucción y la tercera sale gratis.
- **Los carriles en la ALU casi no cuestan celdas (+19) y cuestan frecuencia.** La fmax mínima baja de 48,7 a 33,7 MHz. La ruta crítica de la peor semilla mide 29,7 ns de los 40 del período: sale de la BRAM del banco de registros, cruza el sumador con el acarreo cortado cada 8 bits y termina en la habilitación de un registro que depende de la dirección del bus. El estudio de `d_isa` había dejado abierta la posibilidad de que en el barrel fuera distinto, porque la ALU está sola en su etapa. No lo es: 33,7 MHz aquí y 33,3 en el segmentado.
- **Los carriles en unidad aparte ahora caben** junto al recomendado (1198 celdas, 82 libres), cosa que en el segmentado no pasaba (1282). Con `divstep` además, no (1312).
- **`divstep` cuesta 86 celdas** y no toca la frecuencia.

Lo más grande que cabe sobre el barrel solo es (e) con los carriles en la ALU: 1136 celdas, 144 libres, fmax mínima 34,2 MHz.

## 5. Verificación de la integración

| Prueba | Qué compara | Resultado | Salida |
|--------|-------------|-----------|--------|
| Instrucciones nuevas en los cuatro hilos | Cada escritura al banco de registros de cada hilo contra la lista que predice `ref/xd.py` de `d_isa`. Por variante: 200 programas con los cuatro hilos a la vez, cada uno con un programa distinto, y 10 por hilo con ese hilo solo | 12 variantes, 240 de 240 programas en cada una. Unas 25 200 instrucciones nuevas y 84 600 escrituras por variante, repartidas parejo entre los hilos | `mediciones/tb_xd.txt` |
| Cada hilo contra el Espino base (RV32E) | `tb/tb_verif.sv` de `a_barrel`, sin modificar, con el SoC de esta carpeta: contador de programa, escritura al banco, acceso al bus, los 16 registros y la memoria en cada instrucción completada | 6 configuraciones, 884 281 instrucciones de programa en cada una (348 466 distintas), cero diferencias. La meta era unas 200 000 | `mediciones/verif_rv32e.txt` |
| Testbench oficial sin modificar | 4/4 y `decisiones.csv` idéntico byte a byte al del Espino base, 2000 ticks a 0,1 ms. En las configuraciones con vigilante, que BOOT no suba | 21 configuraciones, todas 4/4 con decisiones idénticas (patrimonio 9617). La cuenta del vigilante nunca pasa de 1 | `mediciones/oficial.txt` |
| Prueba mixta | El testbench oficial con la regla base en el hilo 0 mientras los hilos 1 a 3 ejecutan instrucciones nuevas sin parar. Un monitor compara cada resultado que publican contra el modelo | Ver abajo | `mediciones/mixto.txt` |
| Propiedades formales de estructura | Las 24 afirmaciones de `a_barrel/formal/propiedades.vh`, sin modificar, sobre el core con cada subconjunto de la extensión | PASS en 4 configuraciones (sin definiciones, (b), (c) con `divstep` y (d) con `divstep`). 4 de 4 errores de estructura puestos a propósito dan contraejemplo | `mediciones/formal.txt` |
| Controles negativos | 18 errores puestos a propósito en lo que este estudio agregó, contra seis pruebas cortas | 18 de 18 detectados. El RTL sin mutar pasa las seis | `mediciones/mutaciones.txt` |
| Controles negativos de la auditoría | Otros 12 errores, elegidos sin mirar los 18 anteriores: 6 en la integración de la extensión y 6 en el vigilante | 12 de 12 detectados después de corregir `tb/tb_vig_barrel.sv`. Antes de la corrección, 10 de 12 (sección 16) | `factibilidad/auditoria_hw/mediciones/mutaciones.txt` |

Las variantes de la primera prueba son los ocho subconjuntos de la sección 4 (incluido el que no cabe), las dos formas de I1 y dos conjuntos completos que tampoco caben en la FPGA (todas las instrucciones con todos los k), que se corrieron para dejar probado el camino de `xd_unit` entero.

**Prueba mixta.** Es la forma de uso del fondo: un hilo supervisor que atiende a la maestra y tres hilos que calculan. Mira las dos direcciones: que las instrucciones nuevas de los otros hilos no alteren las decisiones del hilo 0, y que el tráfico del hilo 0 no altere los resultados de las instrucciones nuevas.

| Corrida | Testbench oficial | Decisiones | Hilos 1 a 3 contra el modelo | Vigilante |
|---------|-------------------|------------|------------------------------|-----------|
| I1. Hilo 0 con `sw/trade.s`. Hilos 1 a 3 con `mulstep`, `emad` y `devk` (`sw/kernel_media.s`) | 4/4, peor caso 83 ciclos | Idénticas a las del Espino base | 155 648, 155 647 y 155 647 vueltas, cero diferencias | No dispara |
| I1. Hilo 0 con la regla base escrita con `devk` y `emad`. Hilos 1 a 3 igual | 4/4, peor caso 63 ciclos | Idénticas | 155 648, 155 647 y 155 647 vueltas, cero diferencias | No dispara |
| I1 más carriles en la ALU. Hilo 0 con `sw/trade.s`. Hilos 1 a 3 con seis operaciones de carril y `emad` (`sw/kernel_carriles.s`) | 4/4, peor caso 83 ciclos | Idénticas | 95 232, 95 231 y 95 231 vueltas, cero diferencias | No dispara |

Son 2000 ticks a 0,1 ms. Cada vuelta de `kernel_media.s` tiene 3 instrucciones nuevas y cada vuelta de `kernel_carriles.s` tiene 7, así que entre los tres hilos son 1,4 y 2,0 millones de instrucciones nuevas comparadas. La tercera corrida es el caso más delicado de la integración: la ALU corta el acarreo cada 8 bits cuando la instrucción que está en X es de carriles, y en el ciclo siguiente la usa una instrucción de RV32E de otro hilo.

**Peor caso de la respuesta.** En el barrel la regla base de `sw/trade.s` responde en 83 ciclos en el peor caso del testbench (2262 disponibles). Escrita con `devk` y `emad` (`sw/trade_media.s` de `d_isa`) responde en 63. En el segmentado son 26 y 21. Las decisiones son las mismas en todos los casos.

**Los 18 controles negativos.** Ocho son de la integración de la extensión (por ejemplo: `xd_opa` recibe el `funct3` de la instrucción de otro hilo, `mulstep` no anula el operando B, la ALU corta los acarreos según la instrucción de otro hilo), tres del vigilante (no ve las escrituras en `DECISION`, toma cualquier escritura de cualquier hilo como respuesta, no espera a que CS_n suba) y siete de la memoria de la tabla (selección, multiplexor de lectura, alias con la memoria de programa, índice, bytes). Cada una la detecta la prueba que corresponde: las de la extensión las ve la comparación contra el modelo, y las dos que rompen instrucciones de RV32E (`anula_sin_seleccion` y `enlace_sin_pc4`) las ve la comparación contra el Espino base.

**Dos cosas que aparecieron en el camino y no eran errores del RTL:**

- Los generadores de programas aleatorios del repositorio y del barrel incluyen palabras con el opcode custom-0 entre las codificaciones que el Espino no reconoce. En el Espino base no hacen nada y con la extensión son instrucciones. Para comparar contra el base se reemplazan por `nop` (`tools/sin_custom0.py`: 161 palabras de código y 24 de datos en 68 programas). Si la extensión entra al repositorio hay que hacer lo mismo en `make paralelo`.
- `tb/tb_tabla_mod.sv` tenía un defecto propio: el último acceso al azar se cancelaba antes del flanco y el modelo ya lo había contado. Aparecía con una de tres semillas. Se corrigió el testbench.

## 6. Vigilante con SB_WARMBOOT sobre el barrel

`mediciones/recursos.txt`, sección 3, y `mediciones/tabla_vigilante.txt`, sección 3.

| Variante | Celdas | Agrega | BRAM | Fmax mínima, mediana y máxima (MHz) | Cierran | `SB_WARMBOOT` |
|----------|--------|--------|------|--------------------------------------|---------|---------------|
| Barrel sin vigilante (referencia) | 935 | | 12 | 51,67, 58,27 y 60,13 | 10 de 10 | |
| Barrel con vigilante, N = 4 (es I2) | 939 | +4 | 12 | 50,95, 53,59 y 56,09 | 10 de 10 | 1 de 1 |
| Lo mismo con el disparo manual en el interruptor 4 | 944 | +9 | 12 | 55,22, 57,00 y 58,91 | 10 de 10 | 1 de 1 |
| Segmentado con vigilante (control de I3) | 1009 | +15 | 12 | 49,47, 51,86 y 54,00 | 10 de 10 | 1 de 1 |

Sobre el base y el segmentado había costado entre 9 y 30 celdas. Sobre el barrel cuesta 4, o 9 con el disparo manual. Las dos cifras están dentro del ruido del conteo: lo que se puede afirmar es que cuesta menos de unas 15 celdas y que no mueve la frecuencia.

El vigilante es el módulo de `e_warmboot` sin cambios y mira solo las escrituras en `DECISION`. En un core multihilo eso tiene una consecuencia que se probó aparte (`sw/cuelgue_supervisor.s`, `tb/tb_vig_barrel.sv`): si el hilo supervisor se cuelga, el vigilante dispara aunque los otros tres hilos sigan vivos y escribiendo en la memoria.

| Caso | Resultado |
|------|-----------|
| N = 4, período 0,1 ms | El supervisor responde 20 precios, BOOT sube con el precio 25 (K + N + 1) con CS_n en alto, destino 01. Los tres hilos de estrategia siguen contando antes y después |
| N = 1, período 0,1 ms | BOOT sube con el precio 22 |
| N = 4, período 1 ms | BOOT sube con el precio 25 |
| N = 4 dentro de I1, con cada forma de la tabla | Igual que el primer caso |

Con el programa sano el vigilante no dispara: en las 10 configuraciones con vigilante del testbench oficial la cuenta de precios sin respuesta nunca pasa de 1 y BOOT nunca sube.

Qué pasa si se cuelga un hilo de estrategia depende del programa, y la primera versión de este documento lo decía mal. Con un supervisor que no espera a los otros hilos (el de `sw/cuelgue_supervisor.s`, o cualquiera que tome lo último que encuentre publicado), el vigilante no lo ve: el supervisor sigue respondiendo con datos viejos de ese hilo. Con el programa del fondo (`sw/fondo.s` de `factibilidad/b_fondo_hilos`) pasa lo contrario: el supervisor espera a los tres gestores sin plazo, así que deja de escribir `DECISION` y el vigilante dispara. La auditoría lo midió sobre I1 con el gestor del hilo 3 colgado desde el tick 100: la última decisión es la del precio 99 y BOOT sube con el precio 104, que es T + N (`factibilidad/auditoria_hw/mediciones/cuelgue.txt`).

El testbench mira BOOT, S1 y S0 en las entradas de la primitiva `SB_WARMBOOT`. Hasta la auditoría miraba los cables que salen del vigilante, y por eso no habría notado una primitiva mal conectada (sección 16).

## 7. Memoria para la tabla de política

`mediciones/recursos.txt`, sección 4, y `mediciones/tabla_vigilante.txt`, secciones 1 y 2.

| Forma | Celdas | Agrega | BRAM | Fmax mínima, mediana y máxima (MHz) | Cierran |
|-------|--------|--------|------|--------------------------------------|---------|
| Barrel sin tabla (referencia) | 935 | | 12 | 51,67, 58,27 y 60,13 | 10 de 10 |
| Forma 1: BRAM aparte de 256 x 16 por MMIO (`rtl/tabla_mmio.v`) | 956 | +21 | 13 | 53,55, 54,80 y 56,32 | 10 de 10 |
| Forma 2: otras 512 palabras de 32 bits, solo de datos (`rtl/tabla_ram.v`) | 991 | +56 | 16 | 54,04, 56,21 y 59,20 | 10 de 10 |
| Memoria de 1024 palabras completa (`NumWords = 1024`) | 949 | +14 | 20 | no termina | 0 de 10 |

**La memoria de 1024 palabras completa no cabe.** nextpnr se detiene con "Unable to place cell 'u_ram.mem.1.1_RAM', no BELs remaining to implement cell type 'ICESTORM_RAM'". `pochoco_ram` lee la instrucción y el dato en el mismo ciclo, y para eso Yosys guarda dos copias de cada palabra: 512 palabras son 8 BRAM y 1024 serían 16, más las 4 del banco de registros. La forma 2 evita la segunda copia porque las palabras nuevas no se pueden ejecutar: el contador de programa sigue teniendo 11 bits. Con eso son 4 BRAM más y se llega justo a las 16.

Diferencias entre las dos formas:

| | Forma 1 | Forma 2 |
|-|---------|---------|
| Tamaño | 256 entradas de 16 bits (4 096 bits) | 512 palabras de 32 bits (16 384 bits) |
| Dirección | `0x8002_0000` + 4 i | `0x800` + 4 i, a continuación de la memoria de datos |
| Accesos | `lw`, `lh`, `lhu`, `lb`, `sw`, `sh` y `sb` sobre los 16 bits de la entrada | Los de la memoria de datos |
| BRAM que quedan libres | 3 | 0 |
| Celdas | +21 | +56 |

Las dos son memoria y nada más: no calculan, no miran precios y no deciden. Un acceso es una lectura o una escritura, nunca las dos, así que no necesitan la emulación de lectura durante escritura que sí lleva `pochoco_ram`.

Pruebas: los dos módulos solos con 200 000 accesos al azar contra un modelo, con tres semillas y con el contenido inicial cargado de un archivo. Y `sw/tabla_prueba.s` en el SoC, donde cada hilo inicializa, recorre y ajusta su cuarto de la tabla, con accesos por palabra y por byte. El testbench compara la tabla entera, las sumas de los cuatro hilos y que nada fuera de la tabla haya cambiado. Pasa en las dos formas, solas y dentro de I1.

Recomendación: la forma 1. Cuesta 35 celdas menos, deja 3 BRAM libres y 256 entradas alcanzan para una tabla indexada por 8 bits de historia o de estado. La forma 2 solo se justifica si el aprendizaje en vivo necesita más de 256 entradas o entradas de 32 bits, y deja el diseño sin ninguna BRAM de reserva.

En todas las mediciones la tabla parte en cero (`TablaFile` vacío). Qué contenido inicial lleva es asunto del programa del fondo y de la regla sobre tablas derivadas de la serie de práctica (sección 11).

## 8. Configuraciones integradas

La tabla de la sección 1 tiene los recursos y el timing. Aquí está lo demás.

**Testbench oficial** (`mediciones/oficial.txt`): las 21 configuraciones entregan 4/4 y el mismo `decisiones.csv` que el Espino base. Peor caso de la respuesta: 44 ciclos el base, 26 el segmentado y 83 el barrel, de 2262 disponibles.

**Ruta crítica de la peor semilla** (`mediciones/recursos.txt`):

| Configuración | Semilla | Ruta (ns) | Lógica y ruteo (ns) | Sale de |
|---------------|---------|-----------|---------------------|---------|
| I1, 13 BRAM | 4 | 21,39 | 8,97 y 12,41 | BRAM del banco de registros |
| I1, 16 BRAM | 2 | 22,25 | 8,85 y 13,41 | BRAM del banco de registros |
| I2 | 10 | 19,63 | 6,95 y 12,68 | Registro de selección del operando A |
| I3, `emad` | 6 | 20,82 | 6,70 y 14,12 | BRAM del banco de registros |
| I3, tres instrucciones | 8 | 21,46 | 7,36 y 14,11 | Registro de instrucción |
| I4 segmentado | 7 | 19,56 | 8,53 y 11,03 | BRAM del banco de registros |
| I4 base | 7 | 23,57 | 7,41 y 16,16 | BRAM de la memoria |

En las configuraciones del barrel la ruta cruza el sumador de la ALU (más de 60 tramos de acarreo) y termina en la habilitación de un registro que depende de la dirección del bus. En I3 con `emad` termina en el registro del destino del salto. El informe trae el nombre de cada extremo tal como lo escribe nextpnr.

Todas son de flanco de subida a flanco de subida. El barrel no tiene rutas de medio ciclo.

**Bitstreams** (`mediciones/bitstreams.txt`). Semilla 1, empaquetados con `icepack`. Quedan en `build/bitstreams/` de esta carpeta, que git ignora: se regeneran con `make bitstreams` y el sha256 se reproduce con las mismas versiones de las herramientas. Ninguno se grabó en la placa. Cada uno se simuló desde su `.asc` por los pines, con la maestra de `tb/tb_bitstream.sv` del repositorio, contra `ref/trader.py`.

| Bitstream | Configuración | Fmax con la semilla 1 (MHz) | sha256 | Simulado desde el `.asc`, 500 ticks |
|-----------|---------------|-----------------------------|--------|-------------------------------------|
| `i1a.bin` | I1, tabla de 256 x 16 (13 BRAM) | 48,77 | `c7de9de4858d7a7286fbd094550f6a722f9ee785eb31ff23bbe4adbdd154e419` | Idéntico a la referencia, BOOT no sube |
| `i1b.bin` | I1, tabla de 512 palabras (16 BRAM) | 48,27 | `89ae68f15ddbf7c720497fd1617bd225c5e73bbddaa10c3fc6457658df8b4927` | Idéntico a la referencia, BOOT no sube |
| `i2.bin` | I2, barrel y vigilante | 53,34 | `c879f9e8f7a1e87175bef3566e0b2d147e20f37bd20b6e1655007191593597c5` | Idéntico a la referencia, BOOT no sube |
| `i3a.bin` | I3, segmentado, `emad` y vigilante | 51,99 | `832d807da79b8a03cf9d3e6f45d18447b27aa18453a94d23c7ba3997a4eb6e83` | Idéntico a la referencia, BOOT no sube |
| `i3b.bin` | I3 con `emad`, `devk` y `mulstep` | 48,07 | `c83bb1fff9c6127a2874a89a325f3940183fe44cd278b9864f68ac7267ed048f` | Idéntico a la referencia, BOOT no sube |
| `i4_base.bin` | I4, Espino base de `rtl/` | 43,30 | `3c85d2f98af5c89fe9ee50e6feb08e08cdbe32ad003697e8f8f422dbc69e2e49` | Idéntico a la referencia |
| `i4_segmentado.bin` | I4, segmentado de `rtl/` | 54,50 | `7cbc3a814c6b3f69cd272d7b2eaaeece3d5049fe6ea25d6f612c635a5633da9e` | Idéntico a la referencia |

Los siete miden 32 220 bytes. Los dos de I4 no tienen el hash de `bitstreams/competencia_v1.bin` ni de `bitstreams/segmentado_v1.bin`: son la misma lógica colocada de nuevo (decisión T32). Para la competencia valen los versionados en `bitstreams/`.

El programa dentro de cada bitstream es la regla base: `sw/trade.s` con la tabla de arranque en el hilo 0 en el barrel, y `sw/trade.hex` en los demás. El programa del fondo de estrategias es de otra pieza y no está en estos bitstreams.

**Cuánto más cabe en I1** (`mediciones/recursos.txt`, sección 6):

| I1 más... | Celdas | Libres | BRAM | Fmax mínima (MHz) | Cierran |
|-----------|--------|--------|------|-------------------|---------|
| nada (I1) | 1071 | 209 | 13 | 46,76 | 10 de 10 |
| carriles de bandas en la ALU | 1078 | 202 | 13 | 33,72 | 10 de 10 |
| `divstep` | 1147 | 133 | 13 | 47,97 | 10 de 10 |
| carriles en la ALU y `divstep` | 1176 | 104 | 13 | 34,05 | 10 de 10 |
| carriles en unidad aparte | 1234 | 46 | 13 | 46,11 | 10 de 10 |
| carriles en unidad aparte y `divstep` ("I1 máximo") | 1350 | -70 | 13 | no termina | 0 de 10 |
| I1 de 16 BRAM más carriles en la ALU | 1095 | 185 | 16 | 33,15 | 10 de 10 |
| I1 de 16 BRAM más carriles en unidad aparte | 1270 | 10 | 16 | 44,15 | 10 de 10 |
| I1 de 16 BRAM máximo | 1388 | -108 | 16 | no termina | 0 de 10 |

## 9. Qué habría que sacrificar para que quepa

I1 cabe sin sacrificar nada. Para dejar medido el orden de los sacrificios se tomó el caso que no cabe, el "I1 máximo": I1 más los carriles de bandas en unidad aparte más `divstep`, 1350 celdas, 70 sobre el límite (`mediciones/recursos.txt`, sección 7).

| Paso | Celdas | Recupera (acumulado) | Libres | Fmax mínima (MHz) | Cierran |
|------|--------|----------------------|--------|-------------------|---------|
| I1 máximo | 1350 | | -70 | no termina | 0 de 10 |
| 1. Memoria sin emulación de lectura durante escritura | 1207 | 143 | 73 | 46,80 | 10 de 10 |
| 2. Además sin periféricos (LEDs, display e interruptores) | 1164 | 186 | 116 | 47,48 | 10 de 10 |
| 3. Además reset corto (15 ciclos) | 1167 | 183 | 113 | 48,00 | 10 de 10 |
| Sin tocar la memoria: solo sin periféricos | 1302 | 48 | -22 | no termina | 0 de 10 |
| Sin tocar la memoria: sin periféricos y con reset corto | 1298 | 52 | -18 | no termina | 0 de 10 |
| I1 máximo de 16 BRAM, memoria sin emulación | 1218 | 170 | 62 | 48,36 | 10 de 10 |

Lectura:

- **La memoria sin emulación es el único recorte que alcanza por sí solo.** Recupera 143 celdas aquí y 146 sobre I1 (de 1071 a 925), en línea con las 140 que midió el estudio del barrel.
- **Los periféricos recuperan 43 más** (39 en el estudio del barrel).
- **El reset corto no recupera nada medible**: 3 celdas más, dentro del ruido. Las 14 que midió el estudio del barrel también lo estaban. No conviene, porque además el reset largo existe por una falla que se vio en la placa (decisión T3).
- **Sin tocar la memoria, el I1 máximo no cabe** aunque se saquen los periféricos y se acorte el reset.

Orden recomendado si algún día hiciera falta espacio, de lo que menos se pierde a lo que más:

1. **Sacar `divstep`** (recupera 116: de 1350 a 1234). Solo sirve en el tick de una compra recortada. Con eso el I1 con carriles en unidad aparte cabe, con 46 libres.
2. **Pasar los carriles de la unidad aparte a la ALU** (recupera 156: de 1234 a 1078). Se pierden unos 12 MHz de fmax mínima (de 46,1 a 33,7) y las operaciones `pcmplt8`, `pminu8`, `pmaxu8` y `pmovmsk8`. Sigue cerrando en las 10 semillas.
3. **Memoria sin emulación de lectura durante escritura** (recupera unas 145). Toca `rtl/pochoco_ram.v`, que comparten los tres cores, y cambia lo que pasa en el silicio si el programa busca la palabra que está escribiendo en ese mismo flanco. La simulación no puede probar ese caso.
4. **Periféricos** (recupera unas 40). Se pierde la telemetría en LEDs y display.
5. **Reset corto.** No recupera nada y agrega un riesgo de placa.

## 10. Días de trabajo para calidad de competencia

Todo lo de esta sección es estimado. Suma las estimaciones de cada pieza (barrel 7 días, extensión 4, vigilante 3,5) y agrega dos cifras propias: la memoria de la tabla y el programa del fondo. El programa del fondo es de la pieza B y su estudio dará su propia cifra, que reemplaza a la de aquí.

| Tarea | I1 | I2 | I3 | I4 |
|-------|----|----|----|----|
| Barrel a `rtl/`: verificación y formal a `main`, gemelo con cuatro contextos, integración y mediciones por tick, documento, bitstream y prueba de placa | 5 | 5 | | |
| Regla base en un hilo con equivalencia (ya pasa) | | 0,5 | | |
| Extensión: ensamblador, gemelo, verificación larga, equivalencia y documentos | 4 | | 4 | |
| Vigilante: a `rtl/`, archivo de dos imágenes, gemelo del relevo, equivalencia, pruebas de placa y con la maestra, documentos | 3,5 | 3,5 | 3,5 | |
| Memoria de la tabla: a `rtl/` con su testbench, mapa de memoria en el gemelo, contenido inicial con su generador y prueba con `icebram`, documento | 1 | | | |
| Programa del fondo: supervisor con contabilidad, tres estrategias en papel, reparto de capital, tabla con prior, referencia y equivalencia bit a bit | 5 | | | |
| Prueba de placa del bitstream ya existente | | | | 0,25 |
| **Suma** | **18,5** | **9** | **7,5** | **0,25** |
| Descontando lo que se hace una sola vez cuando las piezas van juntas (integración continua, flujo de bitstream, estructura de los documentos) | 16,5 | 8,5 | 7 | 0,25 |

Notas:

- Los 7 días del barrel incluían 2 de `trade.s` multihilo. En la columna I1 esos 2 días están dentro de los 5 del programa del fondo.
- En I3 la integración de la extensión en el segmentado ya existe en `factibilidad/d_isa`. Con solo `emad` el trabajo es casi el mismo que con las tres instrucciones.
- Lo que ya se gastó en este tramo no está contado: la integración de la extensión en el barrel, su verificación y las mediciones de esta carpeta.

**Reparto entre tres personas.** Del 15/11 al 25/11 hay 11 días de calendario, o sea 33 días de persona, que se comparten con el resto del proyecto (elección del algoritmo, matriz de estrés, kit de contingencia, informe y defensa).

| Persona | Días 1 a 4 | Días 5 a 8 |
|---------|------------|------------|
| A | Barrel a `rtl/` y gemelo con cuatro contextos | Programa del fondo: supervisor, contabilidad y equivalencia |
| B | Extensión: ensamblador, gemelo y verificación larga. Memoria de la tabla | Programa del fondo: estrategias en papel y tabla. Documentos de la extensión |
| C | Vigilante a `rtl/`, archivo de dos imágenes, pruebas de placa (necesita la placa) | Equivalencia del conjunto, bitstream con hash, checklist del 26/11, documentos |

Qué se puede hacer en paralelo y qué no:

- **En paralelo desde el primer día:** barrel, extensión y vigilante tocan archivos distintos. La integración entre los tres ya está resuelta en esta carpeta y sirve de guía.
- **En serie:** el programa del fondo necesita el gemelo del barrel para correr el protocolo, y la equivalencia del conjunto necesita el programa. Ese es el camino crítico: gemelo (1,5 días), programa (3 a 5) y equivalencia (1).
- **El hardware se puede congelar antes que el programa.** Lo que tiene que pasar por la maestra el 26/11 es el bitstream. El programa se puede cambiar después con `icebram` sin tocar el hardware, y eso está probado sobre el prototipo del barrel pero no sobre I1 ni sobre un archivo de dos imágenes.

Con las tres personas dedicadas solo a esto desde el 15/11, I1 toma unos 7 a 8 días de calendario: termina entre el 22 y el 23/11 y deja 2 o 3 días antes del congelamiento del 25/11. Es la cota optimista. Supone que nadie hace otra cosa en esos días, que las tres piezas pasan su prueba de placa al primer intento y que el camino crítico (gemelo, programa y equivalencia) no se atrasa. Los 16,5 días de persona son la mitad de los 33 que hay hasta el congelamiento, y el resto del proyecto (elegir el algoritmo y llevarlo a `trade.s`, matriz de estrés, kit de contingencia, checklist del 26/11, informe y defensa) tiene que salir de la otra mitad. Con una sola persona no llega. I2 e I3 toman unos 4 días de calendario con dos personas.

## 11. Reglas del enunciado

| Regla | Cumple | Comentario |
|-------|--------|------------|
| "La decisión se debe calcular en el Espino Core en la placa. El core debe leer el precio y escribir la decisión; el hardware agregado puede acelerar partes del algoritmo, pero no reemplazar al procesador en el ciclo de decisión." | Sí | Las instrucciones nuevas son aritmética sin estado. El vigilante no calcula nada. La tabla es memoria que el programa lee y escribe con `lw` y `sw`: no recibe precios ni entrega decisiones. En todas las configuraciones un hilo lee `PRICE` y escribe `DECISION` con instrucciones de la ISA |
| "No se puede usar información externa a la serie recibida por SPI ni almacenar series de precios en el diseño distintas de la que se está stremeando." | Sí en el hardware, a cuidar en el programa | El hardware no trae ninguna tabla: en todas las mediciones parte en cero. El riesgo está en el contenido inicial que le ponga el programa del fondo. Ver abajo |
| "Todo hardware agregado debe estar en el repositorio con su testbench." | Sí a nivel del SoC, con una salvedad | `tabla_mmio` y `tabla_ram`: `tb/tb_tabla_mod.sv` y `tb/tb_tabla.sv`. Integración de la extensión: `tb/tb_xd_barrel.sv`. Vigilante sobre el barrel: `tb/tb_vig_barrel.sv`. La salvedad la midió la auditoría: de los 19 módulos agregados de I1, 13 tienen un testbench que los instancia solos y 6 no (el core barrel con la extensión, los dos módulos del banco de registros, el decodificador, la copia del esclavo SPI y `xd_unit`), que se prueban dentro del SoC (sección 16). Para entrar al repositorio tendrían que pasar a `rtl/` y `tb/`, y esta carpeta todavía no está en ningún commit |
| "Deben usar el mismo programa para todas las series de tiempo." | Sí, con la duda del vigilante | Un solo programa y un solo bitstream. La duda es la del estudio del respaldo: después de un relevo la placa opera con la imagen de respaldo |
| "Pueden modificar libremente el RTL, siempre que el procesador siga siendo Espino." | Sí, con dos dudas ya planteadas | Las instrucciones de RV32E no cambian: cada hilo hace lo mismo que el Espino base en 884 281 instrucciones por configuración. Las dudas son si un Espino de cuatro hilos y si un Espino con instrucciones en custom-0 siguen contando como Espino |
| El testbench oficial no se modifica y entra por jerarquía a `dut.u_spi.*` | Sí | Compila y entrega 4/4 sin tocarlo en las 21 configuraciones. No se renombró `pochoco_soc`, sus puertos, `MemFile`, `u_spi` ni sus señales. El esclavo SPI es la copia de `e_warmboot`, que solo agrega tres salidas. El mapa de registros del SPI y el de los periféricos no cambian: la tabla por MMIO usa una dirección nueva (`0x8002_0000`) |

**La tabla y la regla de no guardar tablas derivadas de la serie de práctica.** Es la regla propia del proyecto y es donde esta pieza puede chocar. La memoria es hardware genérico y no la viola. La violaría un contenido inicial ajustado punto a punto con la serie de práctica. Una tabla inicializada con la regla validada es aceptable solo si se genera desde los parámetros de la regla (los umbrales de entrada y salida) con un script del repositorio, y no desde un entrenamiento sobre la serie. Lo que el programa escriba en la tabla durante la ronda sale de la serie que se está recibiendo, y eso el enunciado lo permite. Quien construya la pieza C tiene que dejar el generador del contenido inicial a la vista.

Preguntas para el ayudante que agrega esta pieza (las de las otras tres piezas siguen en sus documentos):

1. Si una memoria que el programa usa como tabla de política, inicializada con los umbrales de la regla y ajustada durante la ronda con la serie que llega, cumple la regla de no usar información externa a la serie.
2. Si el hardware agregado que es solo memoria (una BRAM más) necesita algo más que su testbench para cumplir la regla del hardware agregado.

## 12. Riesgos

1. **Nada se probó en la placa.** Ningún bitstream de esta carpeta se grabó. Todo lo que quiera ir a la competencia tiene que pasar por la maestra el 26/11.
2. **El programa del fondo no está en esta carpeta.** El hardware se midió con la regla base en el hilo 0 y con núcleos sintéticos en los otros tres hilos. Lo que faltaba lo midieron la pieza B y la auditoría: `sw/fondo.s` usa 41 instrucciones por tick en el supervisor (84 como máximo) y 35 en cada gestor, de las 540 disponibles, y cargado en el hardware I1 entrega 4/4 en el testbench oficial con decisiones idénticas a su referencia. Con ese programa en la memoria las celdas y el timing de I1 son los mismos (1071 celdas, mínima 46,76 MHz).
3. **I1 junta tres piezas que no han pasado por la placa** (barrel, extensión y vigilante). Si una falla el 26/11, el bitstream entero queda fuera de la competencia. I2 e I3 juntan dos.
4. **Los carriles en la ALU dejan 10 ns de margen.** Cierran en las 10 semillas con 33,7 MHz de mínima, contra 46,8 de I1. Si se eligen, conviene la unidad aparte mientras quepa (1234 celdas con I1, 46 libres), y eso deja poco espacio para cualquier otra cosa.
5. **I1 con 16 BRAM no deja ninguna BRAM de reserva.**
6. **El vigilante solo ve al supervisor.** Un hilo de estrategia colgado dispara el relevo solo si el supervisor lo espera, como hace `sw/fondo.s` (sección 6). Con un supervisor que no espera, no dispara nada. Y si el supervisor dejara de escribir `DECISION` en algún tick, dispararía en falso: es la misma condición que el vigilante le impone a cualquier programa. Lo mismo vale para un fondo con un gestor muy lento: medido sobre I1 con retardos al azar de hasta unos 3 ticks por vuelta, el fondo pierde el 42 % de los precios y la cuenta del vigilante llega a 4 de las 5 que disparan. Con un gestor que tardara 4 ticks o más habría un relevo con el programa sano.
7. **La memoria compartida no tiene instrucciones atómicas.** La tabla la pueden leer y escribir los cuatro hilos. La disciplina de un solo hilo escritor por palabra es del programa, no del hardware.
8. **k cableado en 5.** Un programa ensamblado con otro k se ejecuta con k = 5 sin aviso. Si el algoritmo final usa otros desplazamientos hay que decidir el conjunto de k antes del 26/11.
9. **El gemelo digital no modela el barrel, la extensión ni la tabla.** Hasta que lo haga, el protocolo no puede correr el binario y las equivalencias largas dependen de Verilator.
10. **El ruido de la medición.** Diez celdas y unos 5 MHz entre síntesis del mismo circuito. Las conclusiones se apoyan en diferencias mayores, salvo el costo del vigilante (4 a 9 celdas), que se informa como "menos de 15".
11. **El costo en la competencia no cambia.** Ni la extensión ni el vigilante ni la tabla mueven el patrimonio por sí solos: con la regla base las siete configuraciones deciden igual. Lo único que puede mover el patrimonio es el programa del fondo.

## 13. Lo que no se verificó

- Nada en la placa ni con la maestra real.
- Las configuraciones integradas con el testbench oficial a 1 ms y 10 ms, ni en los 20 000 ticks de la serie completa. Se corrieron los 2000 ticks a 0,1 ms que el testbench trae por defecto. El prototipo del barrel sí tiene la serie completa a los tres períodos, en su estudio.
- La simulación de los bitstreams desde el `.asc` es de 500 ticks y solo con la semilla 1.
- El cambio de programa con `icebram` sobre I1 (13 o 16 BRAM) y la carga del contenido inicial de la tabla dentro del bitstream. El contenido inicial se probó en simulación con el módulo solo.
- La equivalencia formal entre el core de esta carpeta sin definiciones y el del prototipo. Se apoya en el `diff`, en que la síntesis da lo mismo (935 y 934 celdas) y en que las propiedades de estructura pasan.
- Que cada instrucción nueva calcule lo que debe está probado formalmente por módulo en `d_isa`, y aquí por simulación contra el modelo. No hay una prueba formal de la integración en la etapa X más allá de las propiedades de estructura.
- El relevo completo (reconfiguración y arranque del respaldo) con el barrel como imagen principal. Se probó, en simulación del RTL, que BOOT sube cuando corresponde en la entrada de la primitiva y que S1 S0 vale 01. En la simulación de los bitstreams solo se comprueba el caso sano: que BOOT no sube y que S1 S0 vale 01 en la primitiva.
- Un testbench que instancie solos el core barrel con la extensión, el decodificador y la copia del esclavo SPI. Se prueban dentro del SoC (sección 16).
- El consumo.
- El programa del fondo y el aprendizaje en vivo: son de las piezas B y C.

## 14. Veredicto según los criterios de corte

Criterio de hardware: se descarta de la edición de competencia lo que no cabe junto al SPI (1280 celdas y 16 BRAM) o no cierra a 25 MHz en las 10 semillas.

| Pieza o configuración | Cabe | Cierra 10 de 10 | Veredicto |
|-----------------------|------|-----------------|-----------|
| I1: barrel, `emad`, `devk`, `mulstep`, vigilante y tabla de 256 x 16 (1071 celdas, 13 BRAM, mínima 46,8 MHz) | Sí, 209 libres | Sí | **No se descarta.** Candidata si el fondo gana en los estudios de retorno |
| I1 con la tabla de 512 palabras (1098 celdas, 16 BRAM, mínima 44,9 MHz) | Sí, 182 libres y 0 BRAM | Sí | No se descarta. Solo si la tabla necesita más de 256 entradas |
| I2: barrel y vigilante (939 celdas, 12 BRAM, mínima 51,0 MHz) | Sí, 341 libres | Sí | No se descarta |
| I3: segmentado, `emad` y vigilante (1046 celdas, mínima 48,0 MHz) | Sí, 234 libres | Sí | No se descarta |
| I3 con `emad`, `devk` y `mulstep` (1142 celdas, mínima 46,6 MHz) | Sí, 138 libres | Sí | No se descarta |
| I4: segmentado y base de `rtl/` | Sí | Sí | Ya están en `main` |
| Extensión (a), (b), (c), (d) y (e) sobre el barrel, salvo la última fila | Sí | Sí | No se descartan. (c) cierra con 33,7 MHz de mínima |
| Carriles en unidad aparte más `divstep` sobre el barrel (1312 celdas) | No | No | **Descartada**: exhibición o ASIC |
| I1 máximo (1350 celdas) | No | No | **Descartada** como está. Cabe con la memoria sin emulación (1207), que es una decisión aparte |
| Memoria de 1024 palabras completa (20 BRAM) | No | No | **Descartada** |
| Vigilante sobre el barrel (+4 celdas) | Sí | Sí | No se descarta. Sus condiciones son las del estudio del respaldo |
| Tabla de 256 x 16 por MMIO (+21 celdas, 1 BRAM) | Sí | Sí | No se descarta |

El hardware no es lo que limita al fondo en un chip. Lo que decide entre las configuraciones queda fuera de este estudio:

- **I1** solo vale la pena si el fondo de estrategias mejora los puntos esperados sin empeorar el percentil 5 en los estudios de retorno. Si no, sus 16 a 18 días de trabajo y sus tres piezas sin probar en la placa no compran nada en la competencia, y pasa a la edición de exhibición con estos números.
- **I2** es el barrel con una red de seguridad. Con una sola estrategia decide igual que el segmentado y responde más lento (83 ciclos contra 26).
- **I3** es la opción de menor riesgo que todavía muestra co-diseño en el bitstream de competencia: el segmentado ya está verificado en `main` y `emad` agrega 52 celdas con el vigilante.
- **I4** es lo que hay hoy.

## 15. Fuentes copiadas y qué cambió

| Copia | Original | Cambio | Por qué |
|-------|----------|--------|---------|
| `rtl/espino_barrel_core.v` | `factibilidad/a_barrel/rtl/espino_barrel_core.v` | La extensión en la etapa X (sección 2) | Integrar las instrucciones sin tocar el prototipo |
| `rtl/pochoco_soc.v` | `factibilidad/a_barrel/rtl/pochoco_soc.v` | Vigilante, memoria de la tabla y nombre del módulo del esclavo SPI elegible. Se quitaron el registro `HILO` y el arranque común, que el estudio del barrel midió y descartó | Integrar las dos piezas y poder instanciar este SoC junto al original en un testbench |
| `rtl/espino_decoder_xd.v` | `factibilidad/d_isa/core/espino_core/espino_decoder.v` | Solo el nombre del módulo | Que conviva con el decodificador original en `tb/tb_verif.sv`, que instancia el barrel y cuatro Espino base |

Los tres conservan el encabezado de licencia y de autor del repositorio base. Para medir la memoria sin emulación de lectura durante escritura, `tools/comun.sh` genera en `build/` una copia de `rtl/pochoco_ram.v` con el atributo `(* no_rw_check *)` en sus dos arreglos. `rtl/` no se toca.

## 16. Auditoría

Esta pieza se revisó junto con la del fondo de cuatro hilos. Los scripts, las salidas y el detalle están en `factibilidad/auditoria_hw/` (su README, secciones 4 a 10). Aquí va lo que toca a esta carpeta.

**Lo que se confirmó.**

| Qué | Cómo | Resultado |
|-----|------|-----------|
| Celdas, BRAM y fmax de I1 (las dos formas), I2 e I3 (las dos formas) | Síntesis y place and route de nuevo, con listas de fuentes y definiciones escritas desde la tabla de la sección 1 y no desde los scripts de esta carpeta. Lectura directa de los logs de nextpnr | Las mismas cifras, exactas, con las semillas 1 a 10 |
| "Cierran 10 de 10" | Diez semillas más (11 a 20), que no se habían usado | 20 de 20 en las cinco. La peor es 44,68 MHz (I1 con 16 BRAM) |
| El timing, con otro analizador | `icetime` sobre el `.asc` de cada semilla | Mínimas de 46,44 (I1), 45,29 (I1 con 16 BRAM), 50,92 (I2), 48,58 y 45,28 MHz (I3). En I3 vale solo como referencia, porque `icetime` no entiende las rutas de medio ciclo |
| Testbench oficial | Sin modificar, con Icarus: I1, I2 e I3 | 4/4 y decisiones idénticas a las del Espino base. El vigilante no dispara |
| El hardware I1 con el programa del fondo | `sw/fondo.s` de `factibilidad/b_fondo_hilos` cargado en I1: testbench oficial, 20 000 ticks de la práctica a 0,1 ms, 3000 a 1 ms y dos series sintéticas | 4/4, decisiones y estado interno idénticos a la referencia en C, 439 ciclos de peor caso. Las celdas y el timing de I1 no cambian con ese programa en la memoria |
| Las salidas guardadas | `make recursos`, `make tb-xd` y `make oficial` repetidos al cerrar la pieza; `make verif`, `make tabla-vigilante`, `make mutaciones` y `make formal` repetidos por la auditoría | Idénticas, salvo la línea del commit y los tiempos |
| Las cifras de este documento | Cada tabla contra el archivo de `mediciones/` que cita | Coinciden. No hubo que corregir ningún número |
| Que nada cambió fuera de `factibilidad/` | `git status` y `git diff` | Ningún archivo versionado fuera de `factibilidad/` tiene cambios, y `tb/tb_proyecto_4.sv` es el entregado |

**Lo que se refutó y se corrigió.**

1. **El testbench del vigilante no probaba la conexión de la primitiva.** `tb/tb_vig_barrel.sv` miraba `dut.g_vig.boot` y `dut.g_vig.sel`, los cables que salen del módulo `vigilante`, y no las entradas de `SB_WARMBOOT`. La auditoría puso dos errores en una copia del SoC: la entrada BOOT de la primitiva en 0, y S1 y S0 cruzados. Las dos copias pasaban la prueba. En la placa el primero significa que el respaldo no entra nunca y el segundo que la FPGA carga la imagen 2, que no existe. El RTL de esta carpeta estaba bien conectado (la simulación de los bitstreams informa `S1S0=01` leído en la primitiva), así que ningún resultado cambia. Lo que cambió es el testbench: ahora mira BOOT, S1 y S0 en la primitiva, y las dos mutaciones se detectan. `make tabla-vigilante` y `make mutaciones` se repitieron con el testbench corregido: PASS, 12 pruebas y 18 de 18.
2. **La frase sobre un hilo de estrategia colgado estaba equivocada para el programa real.** La sección 6 decía que el vigilante no lo ve porque el supervisor seguiría respondiendo con datos viejos. Con `sw/fondo.s` el supervisor espera a los gestores sin plazo, deja de responder y el vigilante dispara con el precio T + N. Medido sobre I1. Se corrigieron la sección 6 y el riesgo 6.
3. **La holgura frente al calendario estaba contada en el mejor caso.** Se reescribió el último párrafo de la sección 10 con sus supuestos.

**Mutaciones nuevas.** 12 errores distintos de los 18 de esta carpeta, contra `tb_xd_barrel.sv`, `tb_vig_barrel.sv` y la prueba formal del vigilante.

| Grupo | Mutaciones | Detectadas | Comentario |
|-------|------------|------------|------------|
| Integración de la extensión | 6 | 6 | Cuatro las detecta la configuración I1. `carriles_pegados` solo se ve con carriles y `k_de_otro_hilo` solo con k variable: en I1 el k está cableado y el funct7 no se usa, así que ahí esa mutación no cambia nada. Es el riesgo 8 visto desde el otro lado |
| Vigilante | 6 | 6 después de la corrección, 4 antes | `vig_mismo_ciclo` (el precio que llega en el mismo ciclo que una escritura en `DECISION`) no la detecta ninguna simulación del barrel: la detecta la prueba por inducción de `factibilidad/e_warmboot` |

**Lo que sigue sin testbench propio.** El core barrel con la extensión, los dos módulos del banco de registros, el decodificador y la copia del esclavo SPI no tienen un testbench que los instancie solos. Se prueban dentro del SoC (tres testbenches de esta carpeta, `tb_verif.sv` del barrel y el testbench oficial) y con las propiedades formales. Si la regla "todo hardware agregado con su testbench" se lee módulo por módulo, falta escribirlos. Es una pregunta para el ayudante.

**Días de trabajo frente al calendario.** Las estimaciones de la sección 10 son coherentes con las de la pieza del fondo (medio día de diferencia en el programa). El juicio de la auditoría es que I1 no se sostiene para la competencia: pide entre 16 y 18,5 de los 33 días de persona que quedan hasta el congelamiento del 25/11, junta tres piezas que no han pasado por la placa, y lo único que podría mover el patrimonio, el fondo, no pasa el criterio de corte de algoritmo. I3 (7 días) e I2 (8,5) sí caben en el plazo.

**Segunda pasada (15/11).** La auditoría se repitió completa al día siguiente. Las cifras de esta carpeta volvieron a salir exactas: celdas, BRAM y las 20 frecuencias de I1 (las dos formas), I2 e I3 (las dos formas), el testbench oficial con 4/4 y decisiones idénticas, las 12 mutaciones de RTL y la prueba del gestor colgado sobre I1. Las copias de `recursos.txt`, `tb_xd.txt` y `oficial.txt` anteriores a la repetición del cierre (`build/mediciones_antes/`) se compararon otra vez con las guardadas: las dos primeras son idénticas y la tercera cambia solo en la línea del commit y en el tiempo. Además, los bitstreams de la semilla 1 hechos desde la síntesis de la auditoría tienen el mismo sha256 que la tabla de la sección 8 para `i1a.bin`, `i1b.bin`, `i2.bin`, `i3a.bin` e `i3b.bin`: la frase "el sha256 se reproduce" queda comprobada para esos cinco. En esta carpeta no cambió ningún otro archivo. Lo nuevo de la segunda pasada está en la pieza del fondo: un monitor más en la búsqueda de carreras y una variante que faltaba (README de `factibilidad/auditoria_hw`, sección 13).

**Cómo se reproduce.** `make -C factibilidad/auditoria_hw todo` (unos 17 minutos) y `make -C factibilidad/auditoria_hw repeticion` (8 minutos, unos 27 con `LARGOS=1`).

