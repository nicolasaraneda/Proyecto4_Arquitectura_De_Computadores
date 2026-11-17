# Edición ASIC del barrel (exhibición)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

El SoC de R1 (Espino barrel de cuatro hilos, la extensión `emad` y `devk`, la tabla de parámetros y `sw/fondo.s`) llevado por el flujo de LibreLane del Proyecto 3 a GF180MCU. No compite: la competencia es en la FPGA. Sirve para responder lo que la FPGA no puede (área real sin el límite de 1280 celdas, frecuencia en esquinas de proceso, potencia, Ops/W y energía por decisión) y para comparar con la edición ASIC del Espino base y el segmentado que hizo la factibilidad (`factibilidad/g_asic/`, `docs/codiseno.md`, sección 10).

Todo lo que dice este documento sale de los archivos de `asic/mediciones/` y se regenera con los comandos de la sección 7.

## 1. Qué cambia respecto de la FPGA

El core, el decodificador, la ALU, la extensión, la unidad de carga y el esclavo SPI son los mismos archivos de `rtl/`. Cambia lo que en la FPGA es BRAM o depende de ella (`asic/rtl/`):

| Archivo | En la FPGA | En el ASIC |
|---------|-----------|------------|
| `pochoco_soc_asic_barrel.v` | `pochoco_soc` con el barrel | Mismo mapa de memoria y periféricos. Sin el contador de reset de encendido (dependía del valor inicial de un registro); el reset entra ya sincronizado |
| `espino_barrel_regfile.v` | Banco de registros en dos BRAM, 64 palabras (4 hilos por 16 registros) | 64 por 32 flip-flops con lectura registrada; x0 de cada hilo lee 0 |
| `pochoco_mem_asic_barrel.v` | BRAM de 512 palabras con el programa y los datos | Programa en una ROM combinacional generada desde `sw/fondo.s`; 16 palabras de datos en flip-flops (las que usa el fondo, 0x7C0 a 0x7FC), que **vuelven a 0 con el reset** (sección 5) |
| `asic_top_barrel.v` | `goboard_top` | Sincronizador del reset y los puertos de la placa |
| Tabla de parámetros | BRAM de 256 por 16 bits, cambiable con `icebram` | ROM combinacional con los mismos valores (`asic/scripts/gen_tabla.py`) |

Se construyen dos variantes: `xd=3` (`emad` y `devk`, el hardware de R1) y `xd=7` (agrega `mulstep`, que `fondo.s` no usa y por eso no está en la FPGA de competencia, decisión T58).

## 2. Verificación

| Prueba | xd=3 | xd=7 | Archivo |
|--------|------|------|---------|
| RTL del macro con una copia del testbench oficial, 2000 ticks a 0,1 ms, contra `ref/fondo.py` | 4/4, 2000 filas idénticas, peor caso 433 ciclos | Igual | `make asic-barrel-equiv` |
| Netlist final por sus puertos, 500 ticks, contra `ref/fondo.py` | 500 bytes idénticos | Igual | `asic/mediciones/barrel_xd*_t40/puertos.txt` |
| Netlist final con los flip-flops sin reset partiendo en 0 y en 1 | Los dos idénticos a la referencia | Igual | `arranque.txt` |
| Cierre con el verificador del Proyecto 3: setup y hold en 9 esquinas, DRC de Magic, LVS, antenas | Cierra | Cierra | `cierre.md` |
| Segundo DRC con el deck de KLayout del Proyecto 3 (684 reglas) | 0 marcadores | 0 marcadores | `drc_klayout.md` |

## 3. Resultados (25 MHz, esquina típica salvo que se diga otra cosa)

| | Espino base (`trade.s`) | Segmentado (`trade.s`) | Barrel xd=3, R1 (`fondo.s`) | Barrel xd=7 |
|---|---|---|---|---|
| Dado | 0,359 mm² | 0,304 mm² | 1,072 mm² | 1,077 mm² |
| Celdas estándar | 176 975 um² | 149 757 um² | 565 604 um² | 575 241 um² |
| Flip-flops | | | 2929 | 2930 |
| Holgura de setup a 40 ns, esquina lenta | | | 8,01 ns | 8,21 ns |
| Frecuencia con cierre demostrado (esquina lenta) | 42,6 MHz | 42,6 MHz | FMAX_XD3 | (no se barrió) |
| Potencia esperando / calculando | 27,97 / 28,79 mW | 26,18 / 27,38 mW | 94,68 / 96,03 mW | 95,77 / 97,26 mW |
| Kernel a 25 MHz | 3,92 MOPS (8 op. por tick) | 7,41 MOPS | 5,34 MOPS (56 op. por tick) | |
| Ops/W del kernel | 136 MOPS/W | 271 MOPS/W | 55,6 MOPS/W | |
| Ppeak por watt | 434 MOPS/W | 913 MOPS/W | 521 MOPS/W | |
| Energía por decisión, ronda 3 | 2,80 uJ | 2,63 uJ | 9,54 uJ | 9,65 uJ |
| Rondas 2 y 1 (estimadas) | 28,0 y 280 uJ | 26,2 y 262 uJ | 94,8 y 947 uJ | |
| Costo marginal de decidir | 2,62 nJ | 3,84 nJ | 24,4 nJ | |

Las columnas del base y el segmentado son las de `docs/codiseno.md`, sección 10; las del barrel salen de `asic/mediciones/` y de `docs/mediciones/p7/asic.txt` (`make p7-rapido`), con las mismas definiciones de la sección 3 de ese documento.

**Cómo se lee.**

- **El área la pone el banco de registros.** Los cuatro contextos son 2048 flip-flops: el 24,4 % del área de lógica solo en los flip-flops, más los multiplexores de lectura (`asic/mediciones/barrel_xd3_t40/layout_bloques.txt`). En la FPGA ese banco cabe gratis en dos BRAM; en un ASIC sin SRAM es lo más caro del diseño. Por eso el barrel, que es el core más chico en la FPGA (932 celdas contra 1091 del base), es tres veces más grande que el base en silicio.
- **La potencia es casi toda reloj y flip-flops.** En la esquina típica, de 95,4 mW en la ronda 3, 35,0 son el árbol de reloj, 38,4 los flip-flops y 22,0 la lógica combinacional (`asic/mediciones/potencia/barrel_xd3_t40/tabla.md`). Los 2929 flip-flops conmutan el reloj en cada ciclo aunque el dato no cambie.
- **Esperar cuesta lo mismo que calcular.** En el base, decidir cuesta 2,6 nJ sobre 2,8 uJ de espera. En el barrel la diferencia entre sondear y calcular es de 1,4 mW: los cuatro hilos ejecutan una instrucción por ciclo también mientras sondean. La energía por decisión es 3,4 veces la del base por el área, no por el cálculo.
- **Ops/W.** El fondo hace 56 operaciones útiles por tick contra 8 de `max_media`, pero gasta 3,3 veces la potencia: 55,6 MOPS/W contra 136. Por Ppeak por watt el barrel (521) queda entre el base (434) y el segmentado (913).
- **`mulstep` cuesta 9 637 um² de celdas estándar** (1,7 %) y no cambia la frecuencia de forma apreciable.

## 4. Imagen del layout

`asic/mediciones/barrel_xd3_t40/layout.png` (`make asic-barrel-imagen`). Cada celda se colorea según el bloque de la red que maneja su salida: el netlist sale aplanado y las celdas tienen nombres genéricos, así que solo se ven por bloque los flip-flops y la lógica que los alimenta directamente; el resto (las ROM, la decodificación, la ALU) queda en gris. Se ven el banco de registros ocupando la mitad superior, la RAM de datos abajo y el core al centro.

## 5. Dos errores encontrados al hacer esta edición

1. **La configuración de LibreLane había perdido las perillas del flujo.** `config_barrel.yaml` se copió de la del base pero quedó sin `CLOCK_PORT`, el pin de terminales ni las opciones del resizer. La primera corrida terminó sin reloj: DRC y LVS limpios, pero sin árbol de reloj ni análisis de timing. Se detectó porque el STA no informaba caminos de registro a registro. Corrida descartada (`asic/runs/descartadas/`).
2. **El macro dependía del estado de encendido de sus flip-flops.** `sw/fondo.s` supone que la memoria compartida parte en cero ("estado compartido, parte en cero", línea 136): en la FPGA es cierto, porque la BRAM parte con la imagen de `MemFile`. La RAM de datos del ASIC eran flip-flops sin reset. La simulación del RTL no lo mostró: un `if` con una X toma la rama falsa, que resultó ser la correcta. La del netlist sí: MISO salía con X en todos los bits. Con el modelo de flip-flop con estado inicial del Proyecto 3, partiendo en 0 decidía como la referencia y partiendo en 1 compraba desde el tick 1. Se agregó el reset a las 16 palabras de datos (sus flip-flops pasan de 32 594 a 38 214 um², porque los que tienen reset son más grandes) y la prueba de arranque en 0 y en 1 quedó como paso fijo de `post_barrel.sh`. En silicio el estado de encendido es arbitrario: sin el arreglo, el chip habría decidido distinto según el encendido.

## 6. Límites

- **No es una medición de silicio.** La potencia es un cálculo de OpenSTA con los parásitos extraídos y la actividad de la simulación del netlist final.
- **El netlist se probó en 500 ticks**, no en los 20 000: es una simulación por compuertas de 25 000 celdas (35 minutos los 500 ticks). La equivalencia larga es la del RTL, que es el mismo de la FPGA salvo las sustituciones de la sección 1.
- **La biblioteca es de 5 V** (la de 7 pistas de GF180MCU, la misma del Proyecto 3 y de la edición del base): la potencia absoluta es alta para un proceso de 180 nm a 3,3 V. Lo comparable es la razón entre variantes.
- **Las rondas 2 y 1 son estimadas** sumando potencia de sondeo, como en la edición del base.

## 7. Cómo se reproduce

Necesita Docker con la imagen `ghcr.io/librelane/librelane:3.0.16`, LibreLane en el entorno de `LIBRELANE_VENV`, el PDK GF180MCU instalado con ciel y, para el cierre y el DRC de KLayout, un clon del Proyecto 3 en la variable `P3`. Desde la raíz:

| Comando | Qué hace | Tiempo |
|---------|----------|--------|
| `make asic-barrel-equiv` | RTL del macro con el testbench oficial, xd=3 y xd=7 | 3 min |
| `make asic-barrel-flujo` | Las dos corridas de 40 ns | 30 min |
| `make asic-barrel-post` | Cierre, DRC de KLayout, netlist final (500 ticks), arranque y potencia, de cada corrida | 2 h |
| `make asic-barrel-imagen` | La imagen del layout | 1 min |
| `asic/scripts/correr.sh barrel_xd3_tT 3 T` | Una corrida a otro período (el barrido de la sección 3) | 15 a 20 min |
| `python3 asic/scripts/resumen_barrel.py` | `asic/mediciones/corridas.md` y `resumen.txt` (los lee `make p7-rapido`) | segundos |

Las corridas quedan en `asic/runs/` (unos 2 GB cada una, no se versionan).
