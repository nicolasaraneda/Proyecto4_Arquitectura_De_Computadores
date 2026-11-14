# Pieza G: edición ASIC del Pochoco Trader (factibilidad)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

## 1. Qué es y qué se construyó

Se pasó el SoC del Proyecto 4, tal como está en `main`, por el flujo de celdas estándar de nuestro Proyecto 3: LibreLane 3.0.16 en Docker con el PDK GF180MCU (`gf180mcuD`, biblioteca de 7 pistas a 5 V). El objetivo de este tramo es tener números de partida de área, frecuencia y potencia, y saber cuánto falta para una edición ASIC completa. Esta pieza está fuera de la competencia: no toca el bitstream ni el flujo de la FPGA.

Lo que se construyó:

- Un envoltorio mínimo para el flujo: `rtl/asic_top.v`, `rtl/pochoco_soc_asic.v`, `rtl/pochoco_mem_asic.v` y una copia de `espino_register_file.v` con el banco en flip-flops. El resto del diseño (core, periféricos y esclavo SPI) son los archivos de `rtl/` del repositorio, sin copiar.
- La configuración del flujo (`config.yaml`, `pines.cfg`), derivada de `asic/rom/config.yaml` del Proyecto 3.
- Dos variantes del core, las dos con el flujo completo: Espino base (`Pipeline=0`) y Espino segmentado (`Pipeline=2`, pipeline de 3 etapas con ROM combinacional).
- Un barrido de período de cinco puntos por variante (40, 30, 25, 23,5 y 22 ns): diez corridas completas con síntesis, place and route, STA en 9 esquinas, DRC, LVS y antenas.
- Potencia con actividad real (el método de `asic/potencia/` del Proyecto 3): se simula el netlist final ejecutando `trade.s` con la maestra y OpenSTA calcula la potencia con ese VCD.
- Verificación funcional del RTL del macro, del netlist de síntesis y del netlist final contra `ref/trader.py`.
- Tres estudios de solo síntesis: área por módulo, costo de la RAM de datos según su tamaño (contra las macros SRAM del PDK) y costo del shifter completo.
- Dos corridas completas más, a 40 ns, con el shifter completo de la ALU (el que en la FPGA no cabe), una por variante.

Todo lo que se informa son cálculos de las herramientas sobre el diseño. No hay silicio: ninguna cifra es una medición física.

## 2. Decisiones del envoltorio

| Punto | Decisión | Por qué |
|---|---|---|
| Programa | ROM combinacional generada con `tools/pochoasm.py --rom` desde `sw/trade.s`. La síntesis la convierte en compuertas (167 celdas, 2 755 um2). | `pochoco_ram` usa `$readmemh` y se infiere como BRAM del iCE40. Ninguna de las dos cosas existe en celdas estándar. Es la misma estrategia del Proyecto 3. |
| Fetch del Espino base | La salida de la ROM pasa por un registro con `a_req_i`, que hace de puerto A registrado de la BRAM. | El core base ve la misma temporización que en la FPGA y no se toca. |
| Fetch del segmentado | La ROM va directo a `instr_next_i` (variante 2 de `pochoco_soc`, la de `-DESPINO_ROM`). | La variante 1 lee una BRAM en el flanco de bajada y no tiene sentido sin BRAM. |
| RAM de datos | 4 palabras de 32 bits en flip-flops (parámetro `DataWords`). | `trade.s` usa una sola palabra (`TMP`, en 0x7FC). Las 512 palabras de la FPGA en flip-flops costarían 1,98 mm2, casi 14 veces el macro entero (sección 4.6). |
| Banco de registros | 15 registros de 32 bits en flip-flops, un solo arreglo con dos puertos de lectura. x0 no se almacena. | El banco de la FPGA instancia `SB_RAM40_4K`. Es la solución del Proyecto 3. Las macros SRAM del PDK son de un puerto y 8 bits: no sirven para un banco con dos lecturas. |
| Reset | Se quitó el contador de power-on reset (depende del valor inicial de un registro). El reset entra por el puerto `rst_n`, con un sincronizador de dos flip-flops en `asic_top`. | En silicio no hay valores iniciales. El banco de registros y la RAM de datos no tienen reset, igual que en la BRAM: el programa no puede leer un registro antes de escribirlo, y `trade.s` no lo hace. |
| Core | Los dos: base y segmentado. | El flujo completo demoró entre 5 y 56 minutos por corrida, así que alcanzó para ambos. |
| Puertos | Funciones lógicas (reloj, reset, LEDs, interruptores, displays y SPI), sin pads. | Es un macro, igual que en el Proyecto 3. Un chip completo llevaría anillo de pads. |

Copias modificadas y qué cambia en cada una (el detalle está en el encabezado de cada archivo):

- `rtl/pochoco_soc_asic.v`, copia de `rtl/pochoco_soc.v`: cambia el nombre del módulo, el reset y la memoria. No cambian el core, el mapa de memoria, los periféricos ni la instancia `u_spi`.
- `rtl/espino_register_file.v`, copia de `rtl/espino_core/espino_register_file.v`: flip-flops en vez de BRAM. No cambian la interfaz, la temporización ni el adelantamiento.
- `build/gen/espino_alu_shifter.v` (generado por `scripts/shifter.sh`): `espino_alu.v` con las tres líneas del shifter descomentadas, solo para medir su costo.

El testbench oficial no se modificó. Para correrlo sobre el macro existe `tb/pochoco_soc_sim.v`, un módulo de simulación que se llama `pochoco_soc`, genera el reset con el mismo contador de la FPGA y expone `u_spi` con los nombres que el testbench busca por jerarquía.

## 3. Cómo se reproduce cada número

Todo se corre desde la raíz del repositorio. Necesita Docker con la imagen `ghcr.io/librelane/librelane:3.0.16`, LibreLane en `~/herramientas/librelane`, el PDK en `~/.ciel`, OSS CAD Suite en `~/herramientas/oss-cad-suite` y, para `cierre` y `drc-klayout`, el clon del Proyecto 3 en `~/proyectos/Proyecto3_Arquitectura_De_Computadores`.

| Comando | Qué hace | Salida | Duración aproximada |
|---|---|---|---|
| `make -C factibilidad/g_asic equiv` | RTL del macro con el testbench oficial y contra `ref/trader.py`, 2 000 ticks, Icarus | `mediciones/equiv_rtl.txt` | 10 min |
| `make -C factibilidad/g_asic equiv-largo` | Lo mismo con 20 000 ticks a 0,1 ms y a 1 ms, Verilator | `mediciones/equiv_rtl_largo.txt` | 3 min |
| `make -C factibilidad/g_asic sintesis` | Síntesis con jerarquía: área por módulo | `mediciones/sintesis.md` | 1 min |
| `make -C factibilidad/g_asic memoria` | RAM de datos de 4 a 512 palabras y macros SRAM del PDK | `mediciones/memoria.md` | 5 min |
| `make -C factibilidad/g_asic shifter` | Costo del shifter completo (solo síntesis) | `mediciones/shifter.md` | 2 min |
| `make -C factibilidad/g_asic shifter-flujo` | Flujo completo a 40 ns con el shifter completo, las dos variantes. Necesita `shifter` y `flujo` | `runs/*_shifter_t40`, `mediciones/shifter_flujo.md`, `mediciones/shifter_cierre.txt`, `mediciones/shifter_delta.md` | 8 min |
| `make -C factibilidad/g_asic shifter-recolectar` | Las tablas de esas corridas, sin volver a correrlas | los mismos tres archivos | segundos |
| `make -C factibilidad/g_asic shifter-puertos` | Netlists de las corridas con shifter contra `ref/trader.py` | `mediciones/shifter_puertos.txt` | 10 min |
| `make -C factibilidad/g_asic flujo` | Flujo completo a 40 ns, las dos variantes | `runs/base_t40`, `runs/seg_t40` | 6 min |
| `make -C factibilidad/g_asic barrido` | Las diez corridas del barrido, dos a la vez | `runs/*_t*` | 2 h |
| `make -C factibilidad/g_asic recolectar` | Tabla de las corridas y copia de sus reportes | `mediciones/corridas.md`, `mediciones/TAG/` | segundos |
| `make -C factibilidad/g_asic cierre` | Criterios de cierre con el verificador del Proyecto 3 | `mediciones/cierre.txt`, `mediciones/TAG/cierre.md` | segundos |
| `make -C factibilidad/g_asic ruta` | Extremos de la ruta crítica con nombres del RTL | `mediciones/ruta_critica.md` | segundos |
| `make -C factibilidad/g_asic flipflops` | Qué registros quedaron en el netlist | `mediciones/flipflops.md` | segundos |
| `make -C factibilidad/g_asic puertos` | RTL, netlist de síntesis y netlist final contra `ref/trader.py` | `mediciones/puertos.txt` | 20 min |
| `make -C factibilidad/g_asic potencia` | Potencia con actividad real de las corridas de 40 ns | `mediciones/potencia/TAG/tabla.md` | 20 min |
| `make -C factibilidad/g_asic potencia-x` | Sensibilidad al estado inicial de los flip-flops sin reset | `mediciones/potencia/TAG/xinit.txt` | 5 min |
| `make -C factibilidad/g_asic drc-klayout` | Segundo DRC, con el deck de KLayout del Proyecto 3 | `mediciones/drc_klayout.txt` | 12 min |
| `make -C factibilidad/g_asic comparar` | Tabla contra la FPGA y contra el Proyecto 3 | `mediciones/comparacion.md` | segundos |

`make -C factibilidad/g_asic todo` corre todo en orden. Las corridas de LibreLane quedan en `runs/` (unos 11 GB, no se versionan) y los intermedios en `build/`.

Todo lo anterior ya se corrió y sus salidas están en `mediciones/`. No queda ninguna corrida viva. El 14/11 se repitieron `recolectar`, `cierre`, `ruta`, `flipflops`, `comparar`, `equiv-largo` y `sintesis` para comprobar que las salidas guardadas se reproducen (sección 8).

## 4. Mediciones

Estado de cada cifra: "flujo" quiere decir calculada por las herramientas del flujo sobre el layout o el netlist final. "Estimada" quiere decir derivada de lo anterior con un supuesto que se indica.

### 4.1 Verificación funcional

| Qué | Resultado | Archivo |
|---|---|---|
| RTL del macro con el testbench oficial (copia que solo cambia `PERIODO_NS`, `NTICKS` y la salida), base y segmentado, 2 000 ticks a 0,1 ms y 200 a 1 ms | 4 de 4 PASS: 4/4 chequeos y `decisiones.csv` idéntico a `ref/trader.py` | `mediciones/equiv_rtl.txt` |
| Lo mismo con los 20 000 ticks, a 0,1 ms y a 1 ms (Verilator) | 4 de 4 PASS: 20 000 filas idénticas en cada una | `mediciones/equiv_rtl_largo.txt` |
| RTL por los puertos, 2 000 ticks | 2 de 2 PASS | `mediciones/puertos.txt` |
| Netlist de síntesis (celdas del PDK, sin retardos), 300 ticks | 2 de 2 PASS | `mediciones/puertos.txt` |
| Netlist final, después del place and route, 2 000 ticks | 2 de 2 PASS | `mediciones/puertos.txt` |
| Corridas con el shifter completo: netlist de síntesis (300 ticks) y netlist final (2 000 ticks), las dos variantes | 4 de 4 PASS | `mediciones/shifter_puertos.txt` |

Peor caso entre el precio y la decisión, medido por el testbench oficial sobre el RTL del macro: 46 ciclos el base y 24 el segmentado, contra 2 262 disponibles en la ronda 3.

Las simulaciones de netlist son funcionales (`-DFUNCTIONAL`, sin SDF): comprueban que la síntesis y el place and route no cambiaron lo que el macro decide. El timing lo cubre el STA.

### 4.2 Área por módulo (síntesis con jerarquía, antes del place and route)

| | Espino base | Espino segmentado |
|---|---|---|
| Celdas y flip-flops | 4 749 y 875 | 4 729 y 927 |
| Área (um2) | 143 647 | 145 735 |
| Banco de registros | 75 605 um2 (52,6 %) | 81 132 um2 (55,7 %) |
| Memoria (ROM, 4 palabras y registros de lectura) | 23 045 um2 (16,0 %) | 19 970 um2 (13,7 %) |
| ALU | 10 153 um2 | 10 153 um2 |
| Esclavo SPI | 6 276 um2 | 6 276 um2 |
| ROM de `trade.s` sola | 2 755 um2 (167 celdas) | 2 755 um2 |

Más de la mitad del macro es el banco de registros en flip-flops. Tabla completa en `mediciones/sintesis.md`.

### 4.3 Flujo completo (cifras del flujo)

Corridas a 40 ns, el reloj de 25 MHz de la Go Board:

| | Espino base (`base_t40`) | Espino segmentado (`seg_t40`) |
|---|---|---|
| Dado | 590,55 x 608,47 um, 359 332 um2 | 542,75 x 560,67 um, 304 298 um2 |
| Núcleo | 332 375 um2 | 280 053 um2 |
| Celdas estándar (área) | 176 975 um2 | 149 757 um2 |
| Utilización del núcleo | 53,2 % (se pidió 40 % antes de reparar timing) | 53,5 % |
| Celdas (con taps y endcaps, sin relleno) | 8 791 | 7 524 |
| Flip-flops | 872 | 774 |
| Holgura de setup: típica, lenta y rápida (ns) | 23,465, 9,142 y 28,436 | 20,870, 4,709 y 27,966 |
| Holgura de hold, peor de las 9 esquinas (ns) | 0,102 | 0,123 |
| DRC de Magic | 0 | 0 |
| DRC de KLayout (deck del Proyecto 3, 684 reglas) | 0 marcadores | 0 marcadores |
| LVS | 0 errores | 0 errores |
| Antenas | 0 | 0 |
| Violaciones de slew, capacitancia y fanout máximos | 0, 1 y 16 | 4, 1 y 10 |
| Duración de la corrida | 325 s | 290 s |

Esquinas: típica `nom_tt_025C_5v00`, lenta `max_ss_125C_4v50`, rápida `min_ff_n40C_5v50`. El flujo revisa 9 (tres de proceso por tres de extracción).

Barrido de período (tabla completa en `mediciones/corridas.md` y `mediciones/cierre.txt`):

| T (ns) | Frecuencia (MHz) | Base: holgura de setup en la esquina lenta (ns) | Base: cierra | Segmentado: holgura (ns) | Segmentado: cierra |
|---|---|---|---|---|---|
| 40 | 25,0 | 9,142 | sí | 4,709 | sí |
| 30 | 33,3 | 4,626 | sí | 2,466 | sí |
| 25 | 40,0 | 1,402 | sí | 1,702 | timing sí, pero queda 1 net con violación de antena |
| 23,5 | 42,6 | 0,245 | sí | 1,435 | sí |
| 22 | 45,5 | -0,479 | no | -5,414 | no (además 1 net con antena) |

"Cierra" es el criterio del Proyecto 3: flujo completo, setup y hold con holgura no negativa y TNS 0 en las 9 esquinas, DRC de Magic, LVS y antenas en cero. En `mediciones/corridas.md` la columna "antenas" suma dos métricas del flujo, así que el net en violación de `seg_t25` y de `seg_t22` aparece ahí como 2.

- **Frecuencia máxima con cierre demostrado: 42,6 MHz (23,5 ns) en las dos variantes.** A 22 ns ninguna cierra. El punto exacto queda entre 42,6 y 45,5 MHz: el barrido tiene pasos de 1,5 ns y una sola corrida por punto.
- En la esquina típica la holgura a 23,5 ns es de 10,96 ns (base) y 11,53 ns (segmentado). Estimado como T menos holgura, eso da cerca de 80 MHz, pero no es un cierre: el flujo optimiza para la esquina lenta.
- La holgura del segmentado no baja en forma pareja con el período (4,7 ns a 40, 1,4 a 23,5 y -5,4 a 22). El resizer deja de reparar cuando cumple el margen, así que la holgura de una corrida no predice bien el período mínimo. Por eso se informa el cierre demostrado y no una extrapolación.
- Las corridas de 23,5 ns terminaron dentro de su contenedor después de que se cortó el script que las lanzó. No tienen archivo `.tiempo`, pero su `flow.log` dice "Flow complete" con los 78 pasos y `make cierre` las da por cerradas.

Ruta crítica en la esquina lenta (`mediciones/ruta_critica.md`): en el base sale del registro de instrucción, pasa por la decodificación y la ALU y llega al banco de registros (45 celdas a 23,5 ns). En el segmentado sale del registro del adelantamiento (`fwd_b_q`), pasa por la ALU y llega al banco (39 celdas a 23,5 ns).

**Advertencia sobre el área del segmentado.** Las corridas completas se sintetizan aplanadas. En el segmentado la ROM entra directo a la decodificación, el sintetizador ve el contenido del programa y elimina lo que `trade.s` no usa: 4 de los 15 registros del banco (x10, x11, x12 y x14, 128 flip-flops) y bits de otros registros (`mediciones/flipflops.md`). El macro del segmentado queda especializado para `trade.s` y por eso sale 15 % más chico que el base. Con la jerarquía conservada, donde eso no ocurre, el segmentado es 1,5 % más grande (sección 4.2). Con otro programa el área cambia.

### 4.4 Potencia, energía por decisión y Ops/W

Método: simulación del netlist final ejecutando `trade.s` con la maestra a 0,1 ms por tick, VCD de todos los pines y cálculo de OpenSTA con los parásitos extraídos y el liberty de cada esquina. Los 21 034 pines del base y los 17 895 del segmentado quedan anotados desde el VCD (0 sin anotar). Reloj de 25 MHz, alimentación de 5 V.

| Potencia a 25 MHz, esquina típica (mW) | Espino base | Espino segmentado | Estado |
|---|---|---|---|
| La que informa el flujo, sin actividad anotada | 82,07 | 56,46 | flujo, actividad por defecto de OpenSTA |
| Solo el reloj | 21,71 | 19,65 | flujo, actividad cero |
| Sondeo (el programa espera el precio) | 27,97 | 26,18 | flujo, con VCD |
| Ronda 3, cuatro ticks completos | 28,03 | 26,28 | flujo, con VCD |
| Ventana de cálculo, 80 ciclos (promedio de dos ticks) | 28,79 | 27,38 | flujo, con VCD |
| Esquina lenta y rápida, ronda 3 | 23,18 y 34,18 | 21,70 y 32,07 | flujo, con VCD |

- La cifra por defecto del flujo sobreestima casi 3 veces en el base y 2 veces en el segmentado. La que vale es la del VCD.
- El 77 % de la potencia con actividad real es reloj y flip-flops (21,6 de 28,0 mW en el base). El chip gasta casi lo mismo esperando que calculando: el sondeo ocupa más del 97 % del tiempo en la ronda 3.
- Sensibilidad al estado inicial de los flip-flops sin reset (`mediciones/potencia/TAG/xinit.txt`): con todo en 0 o todo en 1, la ronda 3 da 26,92 y 29,15 mW en el base y 25,40 y 27,24 mW en el segmentado. La cifra informada tiene una incertidumbre de más o menos 4 % por esa causa. Las decisiones son las mismas en los tres casos.

Energía por decisión (potencia por el período del tick), esquina típica:

| | Espino base | Espino segmentado | Estado |
|---|---|---|---|
| Ronda 3 (0,1 ms) | 2,80 uJ | 2,63 uJ | flujo: potencia de la ventana de 4 ticks por 100 us |
| Ronda 2 (1 ms) | 28,0 uJ | 26,2 uJ | estimada: la de la ronda 3 más la potencia de sondeo por 0,9 ms |
| Ronda 1 (10 ms) | 279,7 uJ | 261,8 uJ | estimada: igual, con 9,9 ms de sondeo |
| Costo marginal de decidir, sobre el de esperar | 2,6 nJ | 3,8 nJ | flujo: diferencia entre la ventana de cálculo y el sondeo, por 3,2 us |

La energía por decisión es mil veces el costo marginal de calcular: casi toda se va en esperar el precio con el reloj corriendo. En una edición ASIC completa, detener el reloj mientras no hay precio nuevo es la mejora de energía más grande disponible.

Ops/W con las definiciones de la clase 7, a 25 MHz, esquina típica, con la potencia de la ventana de cálculo:

| | Espino base | Espino segmentado | Estado |
|---|---|---|---|
| Ppeak (f por instrucciones por ciclo) | 12,5 MOPS | 25,0 MOPS | definición de la clase |
| Ppeak por watt | 434 MOPS/W | 913 MOPS/W | flujo |
| Kernel: operaciones útiles por 25 MHz sobre ciclos del tick | 2,38 MOPS (6 operaciones en 63 ciclos) | 4,41 MOPS (6 en 34 ciclos) | ciclos medidos (`docs/mediciones/ticks_*.txt`); las 6 operaciones útiles son una definición nuestra, pendiente de fijar en el frente C |
| Kernel por watt | 83 MOPS/W | 161 MOPS/W | flujo, con ese supuesto |

La clase supuso 10 mW para Pochoco, que da 1 250 MOPS/W de Ppeak. El macro en GF180 a 5 V consume 2,8 veces eso. Tablas completas, con las tres esquinas, en `mediciones/potencia/base_t40/tabla.md` y `mediciones/potencia/seg_t40/tabla.md`.

### 4.5 Shifter completo

Solo síntesis, con la jerarquía conservada (`mediciones/shifter.md`):

| | Sin shifter | Con shifter completo | Diferencia |
|---|---|---|---|
| ALU | 589 celdas, 10 153 um2 | 1 119 celdas, 18 896 um2 | +530 celdas, +8 743 um2 |
| Macro con el Espino base | 143 647 um2 | 152 318 um2 | +6,0 % |
| Macro con el segmentado | 145 735 um2 | 154 382 um2 | +5,9 % |

Flujo completo a 40 ns (`mediciones/shifter_flujo.md`, `mediciones/shifter_delta.md` y `mediciones/shifter_cierre.txt`), cifras del flujo:

| | Base sin shifter | Base con shifter | Segmentado sin shifter | Segmentado con shifter |
|---|---|---|---|---|
| Dado (um2) | 359 332 | 387 034 (+7,7 %) | 304 298 | 331 966 (+9,1 %) |
| Celdas estándar (um2) | 176 975 | 192 565 (+8,8 %) | 149 757 | 162 429 (+8,5 %) |
| Celdas | 8 791 | 9 692 | 7 524 | 8 502 |
| Holgura de setup en la esquina lenta (ns) | 9,142 | 7,697 | 4,709 | 7,933 |
| Holgura de hold, peor esquina (ns) | 0,102 | 0,116 | 0,123 | 0,085 |
| DRC de Magic, LVS y antenas | 0, 0 y 0 | 0, 0 y 0 | 0, 0 y 0 | 0, 0 y 0 |
| Cierra a 25 MHz | sí | sí | sí | sí |
| Duración de la corrida | 325 s | 483 s | 290 s | 329 s |

En la FPGA el shifter completo no cabe (1 491 de 1 280 celdas, 116 %, `docs/mediciones/base.txt`). En el ASIC cuesta entre 8 y 9 % del área después del place and route y el macro sigue cerrando a 25 MHz, limpio de DRC, LVS y antenas. Lo que no se sabe es cuánto baja la frecuencia máxima: no se hizo barrido de período con el shifter, y la holgura de una sola corrida no sirve para estimarlo (en el segmentado la holgura con shifter salió mayor que sin él, lo que solo muestra cuánto varía el resizer de una corrida a otra).

Los netlists de estas dos corridas se simularon contra `ref/trader.py` (`mediciones/shifter_puertos.txt`, sección 4.1). `trade.s` no usa ningún desplazamiento (la ALU de la FPGA no los tiene), así que esa simulación comprueba que agregar el shifter no cambió lo que el macro decide, y no que el shifter desplace bien. Eso último no está verificado: en `tb/` no hay un programa de prueba de `sll`, `srl` y `sra`, y habría que escribirlo.

### 4.6 RAM de datos: flip-flops contra macros SRAM (solo síntesis)

El PDK instalado trae cuatro macros SRAM (`gf180mcu_fd_ip_sram`), de 64 a 512 palabras de 8 bits, un puerto y lectura sincrónica. Una memoria de 32 bits usa cuatro.

| Palabras de 32 bits | En flip-flops (um2) | Cuatro macros SRAM (um2) | Más chico |
|---|---|---|---|
| 4 (lo que tiene el macro) | 20 290 | no hay macro tan chica | flip-flops |
| 64 | 236 118 | 402 286 | flip-flops |
| 128 | 467 971 | 464 474 | empate |
| 256 | 1 003 072 | 588 850 | macros SRAM |
| 512 (la RAM de la FPGA) | 1 979 429 | 837 601 | macros SRAM |

El área en flip-flops es de síntesis. La de las macros es el tamaño de su LEF, sin el espacio que piden alrededor ni la red de alimentación. No se integró ninguna macro en el flujo. Detalle en `mediciones/memoria.md`.

### 4.7 Comparación con la FPGA y con el ASIC del Proyecto 3

| | Espino base | Espino segmentado |
|---|---|---|
| FPGA iCE40 HX1K: celdas lógicas de 1 280 | 1 083 | 994 (fetch en BRAM), 1 055 (ROM combinacional) |
| FPGA: BRAM de 16 | 12 | 12 y 8 |
| FPGA: Fmax en 10 semillas, mínima y mediana | 42,43 y 43,74 MHz | 51,13 y 53,50 MHz |
| ASIC: área de celdas estándar a 25 MHz | 176 975 um2 | 149 757 um2 (especializado, ver 4.3) |
| ASIC: frecuencia máxima con cierre demostrado, esquina lenta | 42,6 MHz | 42,6 MHz |
| CPI medido, `trade.s` con el sondeo | 2,652 | 1,657 |
| CPI medido, mix de la clase 7 | 2,350 | 1,350 |
| MIPS en la FPGA a 25 MHz, `trade.s` | 9,43 | 15,08 |
| MIPS en el ASIC a 42,6 MHz, `trade.s` | 16,05 | 25,67 |
| MIPS en el ASIC a 42,6 MHz, mix de la clase 7 | 18,11 | 31,52 |

El CPI es el medido en simulación con el RTL de la FPGA (`docs/mediciones/espino_segmentado.txt`). El core del macro son los mismos archivos, pero el CPI no se volvió a medir sobre el macro.

| | Proyecto 3, corrida final | Proyecto 4, base | Proyecto 4, segmentado |
|---|---|---|---|
| Área de celdas estándar (um2) | 208 439 (a 100 ns) | 176 975 (a 40 ns) | 149 757 (a 40 ns) |
| Celdas y flip-flops | 9 928 y 964 | 8 791 y 872 | 7 524 y 774 |
| Frecuencia máxima de cierre | 46,5 MHz (21,5 ns), documentado en `asic/final.md` del Proyecto 3 | 42,6 MHz | 42,6 MHz |
| MIPS con el CPI de su programa | 27,9 (CPI 1,665), documentado | 16,0 | 25,7 |

Lectura:

- En la FPGA el segmentado es 22 % más rápido que el base. En el ASIC, con este barrido, los dos cierran en el mismo punto y no se ve esa ventaja.
- El segmentado del Proyecto 4 queda 8 % bajo la frecuencia del Proyecto 3 (42,6 contra 46,5 MHz). Parte de la diferencia es de método: el Proyecto 3 hizo un barrido fino con pasos de 0,5 ns y derivó su modelo de cable de su propia extracción. Aquí el barrido es grueso y el modelo de cable es el copiado.
- La ganancia del pipeline en el ASIC viene entera del CPI: 60 % más de MIPS en `trade.s` a la misma frecuencia.

Tabla generada: `mediciones/comparacion.md`.

## 5. Qué habría que sacrificar para que quepa

No aplica el corte de las 1 280 celdas: esta pieza no va en la FPGA. En el ASIC lo que se sacrificó para tener un macro razonable fue la RAM de datos, que bajó de 512 a 4 palabras. El programa actual usa una. Si el algoritmo definitivo necesita más memoria (por ejemplo una tabla de política o una ventana de precios), cada palabra extra cuesta entre 3 700 y 4 200 um2 en flip-flops, y sobre 128 palabras conviene integrar macros SRAM.

## 6. Días de trabajo para la edición ASIC completa

La base (envoltorio, flujo, verificación funcional, potencia y tablas) está hecha y corre con un comando. Lo que falta, en días de una persona:

| Tarea | Días |
|---|---|
| Traer la pieza a su lugar en el repositorio (`asic/`), con objetivos en el Makefile raíz, y copiar del Proyecto 3 el verificador de cierre, el deck de KLayout y su resumen, que hoy se usan desde ese clon | 0,5 |
| SDC propio (hoy se usa el genérico del flujo: entradas SPI asíncronas tratadas como sincrónicas) y modelo de cable derivado de la extracción de este diseño | 0,5 |
| Barrido fino de período (pasos de 0,5 ns) de la variante elegida. Casi todo es tiempo de máquina: 30 a 60 minutos por corrida cerca del límite | 0,5 |
| Equivalencia formal entre el RTL y el netlist, portando `asic/eqy/` del Proyecto 3 | 0,5 |
| Shifter completo: programa de prueba de los desplazamientos, barrido de período y equivalencia. El RTL ya existe (tres líneas comentadas de la ALU) y el flujo completo a 40 ns ya cierra (sección 4.5) | 0,5 |
| Extensión de la ISA y periférico estimador: agregarlos al flujo, repetir corridas, verificación y potencia. No incluye diseñarlos, que es trabajo del frente C | 0,5 a 1 |
| Potencia y Ops/W de la versión final, con la definición de operaciones útiles del frente C, y energía por decisión por ronda | 0,5 |
| Documento de estudio (`docs/asic.md`), sección del README, preguntas de defensa y figuras del layout | 1 |
| **Total sin barrel ni macros SRAM** | **4,5 a 5** |
| Barrel de 4 hilos, si se construye: cuatro bancos de registros en flip-flops (estimado: unos 300 000 um2 solo en bancos, a 75 600 um2 cada uno, con lo que el macro pasa a más del doble), flujo, verificación y potencia | +1 |
| Macros SRAM para una RAM de datos grande: ubicación de las macros, alimentación, LVS con macros y modelos de simulación | +1,5 |

Es trabajo que se puede hacer después de etiquetar `v-maestra` sin tocar la edición de competencia.

Qué hay que decidir:

1. Qué core lleva la edición ASIC principal: el segmentado (lo que compite y lo que muestra la ganancia de CPI) o los dos, como ahora.
2. Si se acepta que el macro quede especializado para `trade.s`, o si se sintetiza con la jerarquía del banco de registros conservada para informar el costo de un Espino completo.
3. Tamaño de la RAM de datos: lo que use el `trade.s` definitivo en flip-flops, o macros SRAM.
4. A qué frecuencia se informa el punto principal: 25 MHz (comparable con la placa) y además la máxima de cierre.
5. La definición de operaciones útiles por tick para Ops/W. Hoy son 6 y es una definición nuestra.
6. Si se agrega la detención del reloj durante la espera, que es donde está casi toda la energía.

## 7. Reglas del enunciado y preguntas para el ayudante

Esta pieza no participa en la competencia, así que no puede incumplir las reglas del ciclo de decisión. Aun así:

- "La decisión se debe calcular en el Espino Core en la placa": la placa lleva la FPGA. El macro ASIC es material de exhibición y no reemplaza nada.
- "Pueden modificar libremente el RTL, siempre que el procesador siga siendo Espino": el core del macro son los archivos de `rtl/espino_core/` sin copiar, salvo el banco de registros, que cambia la BRAM por flip-flops con la misma interfaz y temporización.
- "No se puede [...] almacenar series de precios en el diseño": la ROM contiene solo el programa `trade.s`.
- "Todo hardware agregado debe estar en el repositorio con su testbench": el envoltorio tiene `tb/tb_asic_puertos.sv` y además pasa el testbench oficial a través de `tb/pochoco_soc_sim.v`.
- "Deben usar el mismo programa para todas las series": la ROM se genera desde el mismo `sw/trade.s`, y el script falla si `sw/trade.hex` no corresponde.

Preguntas para el ayudante:

1. Si una edición ASIC del mismo SoC, fuera de la competencia, se considera en el punto de co-diseño o en la defensa, o si es solo material adicional.
2. Si Ops/W y energía por decisión calculados sobre el ASIC sirven para la parte de métricas, dado que la clase pidió medir el consumo en la Go Board.
3. Qué cuenta como operación útil en el kernel del trader para Ops/s y el roofline.

## 8. Riesgos y lo que no está verificado

- **No hay silicio.** Todas las cifras son del flujo. La potencia es un cálculo sobre el netlist con actividad simulada.
- **Barrido grueso y una corrida por punto.** La frecuencia máxima real está entre 42,6 y 45,5 MHz. No se probaron semillas ni otras densidades.
- **Modelo de cable copiado del Proyecto 3** (`LAYERS_RC` de `config.yaml`), sin volver a derivarlo con la extracción de este diseño.
- **SDC genérico del flujo**: retardos de entrada y salida del 20 % del período y entradas SPI tratadas como sincrónicas.
- **Violaciones que el criterio de cierre no mira** (`mediciones/TAG/max_ss_125C_4v50_violaciones.txt`): 1 de capacitancia máxima en todas las corridas, que es la raíz del árbol de reloj (`clkbuf_0_clk/Z`, 0,39 a 0,42 pF contra un límite de 0,2), igual que en el Proyecto 3. De 10 a 16 de fanout, todas en buffers del árbol de reloj. Entre 4 y 16 de slew en el segmentado: en `seg_t40` es un solo net que pasa el límite de 3 ns por 0,035 ns.
- **Antenas**: las corridas `seg_t25` y `seg_t22` quedan con 1 net en violación. A 25 MHz y a 42,6 MHz no hay.
- **Flip-flops sin reset**: el banco de registros y la RAM de datos arrancan indefinidos. La simulación de netlist pasa porque `trade.s` escribe antes de leer. Un programa que no lo haga se comportaría distinto que en la FPGA, donde parten en cero.
- **Macro especializado para el programa** en la variante segmentada (sección 4.3).
- **DRC de KLayout**: solo sobre `base_t40` y `seg_t40`. No se corrió sobre las de 23,5 ns ni sobre las del shifter. En esas el DRC es el de Magic.
- **Shifter completo**: una corrida por variante, a 40 ns. Sin barrido de período, sin potencia con actividad real y sin un programa que ejercite los desplazamientos.
- **No se hizo**: equivalencia formal entre RTL y netlist, simulación con retardos (SDF), integración de macros SRAM, extensión de la ISA, periférico ni barrel. El CPI no se midió sobre el macro.
- **Reproducción de control (14/11)**: `recolectar`, `cierre`, `ruta`, `flipflops` y `comparar` se volvieron a correr y sus salidas coinciden con las guardadas. En `flipflops.md` cambiaba el orden de las filas de una corrida a otra (mismo contenido) y se dejó un orden fijo. `equiv-largo` y `sintesis` también se repitieron. El barrido, la potencia, `puertos` y el DRC de KLayout no se repitieron: se informa su salida guardada.
- **Dependencia del clon del Proyecto 3** para `make cierre` y `make drc-klayout`.
- **Reproducibilidad por el profesor**: necesita Docker, la imagen de LibreLane y el PDK (varios GB). Conviene dejar versionados los reportes, como se hizo en `mediciones/`.

## 9. Veredicto

**Edición ASIC, fuera de la competencia. La base queda lista.** El SoC actual pasa el flujo completo en las dos variantes del core, limpio de DRC (Magic y KLayout), LVS y antenas a 25 MHz, cierra timing hasta 42,6 MHz en la esquina lenta, y el netlist final decide igual que `ref/trader.py`. Hay cifras de partida de área (0,36 mm2 de dado el base y 0,30 mm2 el segmentado), frecuencia, potencia (28,0 y 26,3 mW a 25 MHz) y energía por decisión (2,80 y 2,63 uJ en la ronda 3). El shifter completo, que en la FPGA no cabe, cuesta entre 8 y 9 % de área y el macro sigue cerrando a 25 MHz.

No compite con nada de la FPGA por celdas ni por la maestra. Faltan entre 4,5 y 5 días de una persona para la edición completa sin barrel, y se puede hacer después de `v-maestra`.

## 10. Archivos

| Ruta | Qué es |
|---|---|
| `rtl/asic_top.v` | Módulo superior del macro: sincronizador de reset y puertos |
| `rtl/pochoco_soc_asic.v` | Copia de `pochoco_soc.v` con reset externo y memoria ASIC |
| `rtl/pochoco_mem_asic.v` | ROM del programa y RAM de datos en flip-flops |
| `rtl/espino_register_file.v` | Banco de registros en flip-flops |
| `config.yaml`, `pines.cfg` | Configuración de LibreLane y orden de los terminales |
| `config_shifter.yaml` | Generado por `scripts/shifter.sh`: igual, con la ALU del shifter completo |
| `tb/pochoco_soc_sim.v` | Puente de simulación para correr el testbench oficial sobre el macro |
| `tb/tb_asic_puertos.sv` | Testbench por los puertos: sirve para el RTL y para los netlists, y vuelca el VCD de potencia |
| `tb/dffq_func_init.v` | Modelo del flip-flop sin reset con estado inicial definido, para la sensibilidad de la potencia |
| `scripts/` | Un script por objetivo del Makefile (`shifter_delta.py` es la tabla sin y con shifter) |
| `Makefile` | Punto de entrada: `make -C factibilidad/g_asic ayuda` |
| `mediciones/` | Salidas guardadas: tablas y reportes de cada corrida |
| `runs/` | Corridas de LibreLane (no se versionan) |
| `AVANCE.md` | Estado del trabajo |
