# Proyecto 4: Pochoco Trader

Agente de inversión que corre en el Pochoco SoC, con el procesador Espino (RV32E), sobre la Nandland Go Board (iCE40 HX1K, 25 MHz). Una FPGA maestra envía por SPI el precio de una acción en cada tick y el programa responde si compra, vende o mantiene, y cuántas acciones.

Arquitectura de Computadores, Universidad de los Andes, semestre 2026-2. Profesor: Jorge Gómez Mir.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

El enunciado está en `docs/Proyecto_4_arq.pdf` y el informe en `informe/`. El avance se registra en `docs/estado.md`, las decisiones en `docs/decisiones.md`, y todos los objetivos de `make` están en `docs/comandos.md`.

## El diseño, en una tabla

Hay una escalera de tres bitstreams. Compite el más alto que pase las tres puertas: simulación, placa y maestra real (`docs/puertas.md`, `docs/arbol_decision.md`).

| Peldaño | Hardware | Programa | Archivo |
|---------|----------|----------|---------|
| R0 | Espino base del curso, con un reset más largo | `sw/trade.s`: regla de cotas con banda 40 (T140), sin saltos | `bitstreams/r0_banda40.bin` |
| R1 | Espino barrel de 4 hilos con las instrucciones `emad` y `devk` y una tabla de parámetros en BRAM | `sw/fondo.s`: la misma regla en el hilo 0, con los umbrales leídos de la tabla | `bitstreams/r1_banda40.bin` |
| R2 | R1 más un vigilante que, si el programa deja de responder, reconfigura la FPGA con R0 | El mismo | `bitstreams/r2_banda40_multi.bin` |

Hoy el diseño por defecto (el que ejercita el testbench oficial sin opciones) es R0. Cuando se sepa qué peldaño compite, `make peldano-fijar PELDANO=r1` lo cambia (`docs/peldano.md`).

## Origen del código

- El punto de partida es el repositorio base del curso, [nic0villegasc/pochoco_soc](https://github.com/nic0villegasc/pochoco_soc), de Nicolás Villegas, importado sin cambios desde su commit `33e8b5a`. Esa copia quedó marcada con la etiqueta `base-curso`. Los archivos del repositorio base conservan su encabezado de autor y su licencia (Solderpad Hardware License 0.51). Cuando modificamos uno de esos archivos, lo indicamos debajo del encabezado original.
- El ensamblador `tools/pochoasm.py` es el que escribió este grupo para el Proyecto 2 y amplió en el Proyecto 3, con el nombre y la interfaz que espera el testbench del Proyecto 4.
- Del Proyecto 3 del grupo vienen también el formato de la traza de `tb/tb_cpi.sv` y el método de comparar trazas ciclo a ciclo.
- El reset de encendido largo de `rtl/pochoco_soc.v` también viene de nuestro Proyecto 2.
- El core segmentado parte del diseño con lectura anticipada de nuestro Proyecto 3 (`nicolasaraneda/Proyecto3_Arquitectura_De_Computadores`). De ahí vienen también `sw/hazard_test.s` y `sw/hazard_review.s` (sin cambios), `sw/hazard_cycles.s` (adaptado), `tb/core_trace_tb.v`, `tb/comparar_trazas.py` y el método de los controles negativos por mutación.
- `tb/tb_proyecto_4.sv` y `tb/practica.csv` son el testbench y la serie de práctica entregados por el curso. No se modifican.

## Herramientas y versiones

Todo se corre con [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build), versión del 2026-09-06, sobre Ubuntu (WSL2):

| Herramienta    | Versión                    |
|----------------|----------------------------|
| Yosys          | 0.68+195                   |
| nextpnr-ice40  | 0.11.1-19-g8dbcee5c        |
| Icarus Verilog | 14.0 (devel, s20260301)    |
| Verilator      | 5.053 (devel)              |
| Compilador de C | gcc o clang, cualquiera reciente (para el gemelo digital) |
| Python         | 3.11 o superior            |
| icepack, iceprog | los de OSS CAD Suite     |

No se necesitan herramientas de compilación de RISC-V: el ensamblador es propio y está en el repositorio. Se usan además `make` y `git`.

El repositorio se obtiene con `git clone` y con su historial completo: `make r0-reproducir` y `make r0-molde` reconstruyen R0 desde el commit en que se guardó, así que no funcionan con un clon superficial (`--depth`) ni con el ZIP que descarga GitHub. Mientras el repositorio sea privado, clonarlo requiere acceso de lectura.

Todos los comandos se ejecutan desde la raíz del repositorio, con las herramientas de OSS CAD Suite en el `PATH` (`export PATH=<carpeta de OSS CAD Suite>/bin:$PATH`). La integración continua (`.github/workflows/ci.yml`) instala la misma versión y corre las pruebas en cada push. Las demoras que se indican abajo son aproximadas, medidas en la máquina del grupo o en un clon limpio (`docs/auditorias/clon_limpio.md`); varias pruebas toman minutos. El informe necesita además LaTeX (`texlive` con los paquetes en español); si no está instalado, la integración continua compila el PDF y lo deja como artefacto.

## Cómo ensamblar `trade.s`

```bash
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex
```

o `make asm`. El ensamblador es propio (`tools/pochoasm.py`); su sintaxis está en `docs/ensamblador.md` y sus tests se corren con `make test-asm`. El programa del fondo usa la extensión de la ISA, que se declara en el mismo archivo con `.extension xd`: `mkdir -p build/fondo && python3 tools/pochoasm.py sw/fondo.s -o build/fondo/fondo.hex`, o `make fondo-hex`, que crea la carpeta. El ensamblador no crea la carpeta de salida. Los programas están explicados en `docs/trade_s.md` y `docs/fondo.md`.

## Cómo correr los testbenches

Testbench oficial, con los comandos de su encabezado, sin modificar:

```bash
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex
iverilog -g2012 -s tb_proyecto_4 -o /tmp/tb_p4 $(yosys-config --datdir)/ice40/cells_sim.v rtl/*.v rtl/espino_core/*.v tb/tb_proyecto_4.sv
vvp -n /tmp/tb_p4
```

Da 4/4 y deja `decisiones.csv`; `vvp` demora de 1 a 2 minutos. Lo mismo, comprobando además que `decisiones.csv` es idéntico al de la referencia: `make peldano-oficial` (diseño por defecto, unos 2 minutos), `make tb` (R0, unos 3 minutos) y `make fondo-oficial HW=r1` (R1; `HW=r2` para R2; de 4 a 5 minutos). `make fondo-oficial` reescribe `docs/mediciones/fondo/<peldaño>/oficial.txt`, y en una corrida sin cambios solo cambia su línea "Commit de partida".

| Comando | Qué prueba | Demora aproximada |
|---------|-----------|-------------------|
| `make check` | Ensamblador, referencia, `trade.hex` al día y testbench oficial con 4/4. | Unos 3 minutos, casi todos del testbench oficial |
| `make equiv` | R0 contra la referencia, byte a byte: los 20 000 ticks a 0,1 ms y 1 ms por el RTL (Verilator) y a los tres períodos en el gemelo, más una serie de cada familia sintética. Los 20 000 ticks a 10 ms por el RTL son `make equiv-largo`. | Sin medir; `make equiv-largo`, unos 25 minutos |
| `make check-fondo HW=r1` | R1: testbench oficial, equivalencia, series, fases, degradación, controles negativos y estrés, en versión corta. | Sin medir |
| `make fondo-puerta HW=r1` | Los criterios de la puerta de simulación de R1 en versión completa. | Más de 35 minutos: incluye los 20 000 ticks a 10 ms |

La lista completa, pieza por pieza, está en `docs/comandos.md`.

## Cómo correr la versión de referencia del algoritmo

```bash
mkdir -p build                                              # carpeta de salida, si no existe
python3 ref/trader.py tb/practica.csv                       # la regla oficial contra no operar y comprar y mantener
python3 ref/trader.py tb/practica.csv -o build/ref.csv      # decisiones.csv de referencia de R0
python3 ref/fondo.py tb/practica.csv -o build/ref_fondo.csv # decisiones.csv de referencia de R1 y R2
make test-ref test-fondo                                    # pruebas de las referencias y del mercado
```

`ref/trader.py` y `ref/fondo.py` hacen las cuentas con las mismas operaciones que los programas; `ref/market.py` es el mercado de la maestra, portado del testbench. El estudio del algoritmo está en `docs/algoritmo.md` (`make algoritmo`).

## Cómo sintetizar y programar la placa

Los bitstreams ya probados están en `bitstreams/`, con su hash, el commit del que salieron y las pruebas que pasaron (`bitstreams/README.md`):

```bash
cd bitstreams && sha256sum -c SHA256SUMS && cd ..   # todos deben decir OK
iceprog bitstreams/r1_banda40.bin                   # o r0_banda40.bin
iceprog -b bitstreams/r2_banda40_multi.bin          # imagen múltiple: -b borra la flash entera
```

`iceprog` escribe la flash de la Go Board, conectada por USB, y termina con "VERIFY OK". En WSL la placa se pasa con `usbipd` (`docs/autoprueba.md`, sección 5).

Para construir desde las fuentes:

```bash
make bin                 # R0: yosys, nextpnr e icepack, deja build/pochoco_soc.bin (segundos)
make prog                # iceprog build/pochoco_soc.bin
make r0-reproducir       # R0 bit a bit igual al guardado, desde las fuentes de su commit (unos 2 minutos)
make fondo-bitstreams    # R1, R2 y la imagen múltiple, simulados desde el .asc (unos 25 minutos)
```

`make bin` produce el mismo diseño que R0, pero no el mismo archivo: con las fuentes actuales Yosys entrega otra netlist equivalente, y el `.bin` tiene otro sha256 y otra frecuencia máxima que `bitstreams/r0_base_max_media.bin` (`docs/mediciones/p7/caida_segmentado.txt`). Para la placa se usa el archivo guardado o el que deja `make r0-reproducir`, que sí coincide byte a byte.

Antes de grabar un bitstream nuevo se simula lo que se graba, reconstruido desde el `.asc`: `make sim-bitstream` (unos 8 minutos).

## Piezas

Una sección por pieza: qué es, el comando que la prueba y el número que la respalda. El detalle de cada una está en su documento de estudio.

### Algoritmo y protocolo de evaluación
Reversión a la media: la serie de práctica tiene razón de varianza 0,77 a 10 ticks. `max_media` compra cuando el precio cae más de 3 unidades bajo su media exponencial y vende al recuperarla, con órdenes de 63 acciones. Se eligió con 10 bloques de práctica, 1 000 remuestreos y 14 familias sintéticas calibradas.
Desde el 17/11 compite otra regla, la de cotas (T133): las rondas se normalizan entre 100 y 255, así que se compra al ver 100, se vende al ver 255 y, después de ver los dos, se compra con 140 o menos y se vende con 215 o más (banda 40 desde el 19/11, T140). Da 21 392 en la serie Meta normalizada, 20 795 en la ronda de Tesla de la clase del 18/11 y 26 470 con AMD (`docs/cotas.md`).
- Prueba: `make tabla-3-1` (segundos) y `make algoritmo` (unos 3 minutos; reescribe archivos de `docs/mediciones/`).
- Número: 25 973 de patrimonio en los 20 000 ticks de práctica, contra 6 497 de comprar y mantener (`docs/mediciones/tabla_3_1.txt`).
- Documento: `docs/algoritmo.md`, `docs/protocolo.md`.

### Gemelo digital
Simulador en C del SoC, exacto al ciclo, para el Espino base, el segmentado y el barrel con la extensión y la tabla. Corre el mismo `.hex` que el bitstream.
- Prueba: `make cosim` (unos 2 minutos) y `make cosim-barrel` (unos 6 minutos).
- Número: traza idéntica al RTL en 21 configuraciones del barrel, 18,3 millones de eventos; la ronda de 10 ms del fondo en 0,14 s contra 35 minutos de Verilator.
- Documento: `docs/gemelo.md`.

### Espino segmentado
Pipeline de 3 etapas con la memoria de instrucciones leída en el flanco de bajada. Se elige con `-DESPINO_SEGMENTADO`.
- Prueba: `make check-seg` y `make paralelo-largo`.
- Número: CPI 1,350 con el mix de la clase contra 2,350 del base; responde en 22 ciclos contra 41.
- Documento: `docs/espino_segmentado.md`.

### Espino barrel
Cuatro hilos que rotan por un pipeline de 4 etapas, sin riesgos de datos ni de control. Se elige con `-DESPINO_BARREL`. Es el core de R1 y R2.
- Prueba: `make check-barrel`, `make barrel-verif` (unos 6 minutos con 12 procesos) y `make barrel-mutaciones`.
- Número: CPI 1 agregado y 4 por hilo; 7,9 millones de instrucciones comparadas con el base, cero diferencias; 21 de 21 mutaciones detectadas.
- Documento: `docs/espino_barrel.md`.

### Extensión de la ISA
`emad` (`rd = rs2 + (rs1 >>> 5)`) y `devk` (`rd = (rs1 << 5) - rs2`) en custom-0, sobre el sumador de la ALU. `mulstep` existe para la edición de exhibición.
- Prueba: `make check-xd` y `make xd-formal`.
- Número: cada instrucción probada formalmente contra su especificación; la regla responde en 63 ciclos contra 83 sin ella.
- Documento: `docs/extension_isa.md`.

### Fondo en un chip
`sw/fondo.s`: un supervisor y tres gestores que votan por memoria compartida, con pesos que se ajustan y degradación si un voto no llega.
- Prueba: `make check-fondo` y `make fondo-puerta` (más de 35 minutos).
- Número: idéntico a `ref/fondo.py` en 1 050 series y en la práctica a los tres períodos; peor caso 443 ciclos de 2 262; 30 de 30 corridas con fallas puestas a propósito.
- Documento: `docs/fondo.md`.

### Tabla de parámetros, vigilante y relevo
Las 20 constantes del fondo en una BRAM de solo lectura que se cambia con `icebram`, y un vigilante que reconfigura la FPGA con R0 si llegan 5 precios sin respuesta.
- Prueba: `make check-vigilante` y `make fondo-bitstreams` (unos 25 minutos).
- Número: cambio de tabla en 0,32 s sin sintetizar; el vigilante no se dispara en ninguna corrida sana y sí en la transacción esperada con el supervisor colgado.
- Documento: `docs/tabla_vigilante.md`.

### Puertas y matriz de estrés
Ocho criterios que un bitstream debe pasar antes de la placa, más una matriz de SCLK, tiempos de `CS_n`, reset, rondas seguidas, períodos, largo de ronda, comisión y caja.
- Prueba: `make fondo-estres HW=r1`, `make estres` (unos 2 minutos con 16 núcleos) y `make p8-matriz` (10 segundos).
- Número: R0 60 de 60 casos, R1 y R2 56 de 56; R1 responde a 0,1 ms desde SCLK de 110 kHz.
- Documento: `docs/puertas.md`, `docs/contingencia.md`.

### Autoprueba en placa
El SoC de cada peldaño con una maestra SPI dentro de la FPGA y una firma CRC-16 de las decisiones en los 7 segmentos. Es la puerta de placa: prueba la placa sin la maestra del curso.
- Prueba: `make autoprueba-r0` (unos 20 minutos), `make autoprueba-r1` y `make autoprueba-r2` (unos 25 minutos cada uno).
- Número: desde el 19/11 (T141) la maestra interna manda una caminata entre 100 y 255 con pasos de 4 (semilla 0xE3AA), que toca los dos extremos y entra a la banda. Firma `a639` en los tres peldaños con banda 40, en el gemelo a los tres períodos, la referencia, el RTL y el bitstream ruteado; con la banda 60 sería `8610`, y la autoprueba la rechaza. En R2, 18 millones de precios en el gemelo (media hora a 0,1 ms) sin que el vigilante pueda dispararse, y el relevo con la falla inyectada en la transacción esperada. Las autopruebas anteriores (`a23c`, `15d7`) pasaron en la placa el 16/11 a 0,1 ms y el relevo se midió en 35,50 ms (`docs/mediciones/placa_16nov.md`); las nuevas están por correr en la placa (`docs/autoprueba.md`, sección 11).
- Documento: `docs/autoprueba.md`.

### Co-diseño: variantes, Amdahl, escalera y roofline
Las seis variantes medidas con las definiciones de la clase 7, el perfil del tick, Amdahl predicho contra medido, la escalera de la clase, el roofline, la edición ASIC y los resultados negativos del PLL y del duplicador de reloj.
- Prueba: `make p7` (unos 25 minutos) o `make p7-rapido` desde lo guardado (segundos).
- Número: el segmentado acelera la respuesta 1,86 veces (Amdahl predice 1,84); R1 hace 56 operaciones útiles por tick contra 8 de R0.
- Documento: `docs/codiseno.md`.

### Anticipación: medidor, contingencia y árbol de decisión
Un bitstream que mide el SPI real de la maestra, `tools/retune.py` para un cambio de comisión, juegos de bitstreams ya construidos y el árbol de decisión del 1/12.
- Prueba: `make medidor` (1 minuto), `make retune-control` (segundos) y `make contingencia` (45 minutos).
- Número: el medidor pasa 66 comprobaciones por los pines del bitstream; `retune` con las reglas publicadas reproduce R0, R1 y R2 byte por byte.
- Documento: `docs/contingencia.md`, `docs/checklist_26nov.md`, `docs/checklist_1dic.md`.

### Informe
Todas las cifras del informe salen de `make report`, que también compila el PDF si hay LaTeX.
- Prueba: `make report` (segundos, sin LaTeX). Reescribe `informe/generado/peldano.tex`, y en una corrida sin cambios solo cambia el commit que imprime el informe.
- Documento: `informe/informe.tex`.

## Estructura

| Carpeta    | Contenido |
|------------|-----------|
| `rtl/`     | Pochoco SoC y Espino Core. |
| `sw/`      | `trade.s`, `fondo.s` (el programa de cuatro hilos del diseño integrado), los programas de ejemplo del repositorio base, los programas de riesgos (`hazard_*.s`) y `mix_clase7.s`. |
| `tb/`      | Testbench oficial, serie de práctica y testbenches propios. |
| `ref/`     | Referencia del algoritmo en Python (`trader.py` para `trade.s` y `fondo.py` para `fondo.s`), mercado de la maestra, series de prueba, protocolo de evaluación y gemelo digital. |
| `tools/`   | Ensamblador, generador de programas aleatorios y scripts de equivalencia, co-simulación y medición. |
| `bitstreams/` | Bitstreams de competencia, con su hash. |
| `formal/`  | Verificación formal: la equivalencia del Espino base con el del repositorio del curso (`formal/base_sin_cambios/`) y las propiedades de estructura del barrel (`formal/barrel/`) y las de la extensión de la ISA contra su especificación (`formal/xd/`). |
| `docs/`    | Enunciado, estado, decisiones, documentación y mediciones. |
| `informe/` | Informe en LaTeX. `informe/generado/` lo rehace `make report`. |

## Mapa de memoria

| Dirección     | Registro | Uso |
|---------------|----------|-----|
| `0x0000_0000` | RAM unificada de 512 palabras | Instrucciones y datos. |
| `0x8000_0000` | Displays de 7 segmentos | Escritura. |
| `0x8000_0004` | LEDs | Escritura. |
| `0x8000_0008` | Interruptores | Lectura. |
| `0x8001_0000` | `STATUS` del SPI | Bit 0: hay un precio nuevo. Bit 1: `CS_n` activo. |
| `0x8001_0004` | `PRICE` | Último precio recibido. Leerlo baja la bandera de precio nuevo. |
| `0x8001_0008` | `DECISION` | Byte que la maestra lee en la transacción siguiente. |

![Arquitectura del Pochoco SoC](docs/pochoco_soc.svg)
