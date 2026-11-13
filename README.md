# Proyecto 4: Pochoco Trader

Agente de inversión que corre en el Pochoco SoC, con el procesador Espino (RV32E), sobre la Nandland Go Board (iCE40 HX1K, 25 MHz). Una FPGA maestra envía por SPI el precio de una acción en cada tick y el programa responde si compra, vende o mantiene, y cuántas acciones.

Arquitectura de Computadores, Universidad de los Andes, semestre 2026-2. Profesor: Jorge Gómez Mir.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

El enunciado está en `docs/Proyecto_4_arq.pdf`. El avance del trabajo se registra en `docs/estado.md` y las decisiones de diseño en `docs/decisiones.md`.

## Origen del código

- El punto de partida es el repositorio base del curso, [nic0villegasc/pochoco_soc](https://github.com/nic0villegasc/pochoco_soc), de Nicolás Villegas, importado sin cambios desde su commit `33e8b5a`. Esa copia quedó marcada con la etiqueta `base-curso`. Los archivos del repositorio base conservan su encabezado de autor y su licencia (Solderpad Hardware License 0.51). Cuando modificamos uno de esos archivos, lo indicamos debajo del encabezado original.
- El ensamblador `tools/pochoasm.py` es el que escribió este grupo para el Proyecto 2, con el nombre y la interfaz que espera el testbench del Proyecto 4.
- El power-on reset largo de `rtl/pochoco_soc.v` también viene de nuestro Proyecto 2.
- `tb/tb_proyecto_4.sv` y `tb/practica.csv` son el testbench y la serie de práctica entregados por el curso. No se modifican.

## Herramientas y versiones

Todo se corre con [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build), versión del 2026-09-06, sobre Ubuntu (WSL2):

| Herramienta    | Versión                    |
|----------------|----------------------------|
| Yosys          | 0.68+195                   |
| nextpnr-ice40  | 0.11.1-19-g8dbcee5c        |
| Icarus Verilog | 14.0 (devel, s20260301)    |
| Python         | 3.11 o superior            |
| icepack, iceprog | los de OSS CAD Suite     |

No se necesita un toolchain de RISC-V: el ensamblador es propio y está en el repositorio.

Todos los comandos se ejecutan desde la raíz del repositorio.

## Cómo ensamblar `trade.s`

```bash
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex
```

o `make asm`. La sintaxis que acepta el ensamblador está en `docs/ensamblador.md`, y sus 73 tests se corren con `make test-asm`.

## Cómo correr los testbenches

Testbench oficial, con los mismos comandos de su encabezado:

```bash
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex
iverilog -g2012 -s tb_proyecto_4 -o /tmp/tb_p4 $(yosys-config --datdir)/ice40/cells_sim.v rtl/*.v rtl/espino_core/*.v tb/tb_proyecto_4.sv
vvp -n /tmp/tb_p4
```

o `make tb`, que hace lo mismo y además falla si el resultado no es 4/4. La corrida por defecto (2000 ticks con período de 0,1 ms) demora cerca de un minuto y medio. El detalle por tick queda en `decisiones.csv`.

Otros objetivos:

| Comando | Qué hace |
|---------|----------|
| `make tb-param PERIODO_NS=1000000 NTICKS=500` | Corre una copia del testbench oficial con otro período y otro número de ticks. El original no se toca. |
| `make cpi` | Mide instrucciones, ciclos y CPI del core con `tb/tb_cpi.sv`, y comprueba el modelo de costo. |
| `make check` | Tests del ensamblador, `trade.hex` al día y testbench oficial. Es lo que corre la integración continua. |

## Cómo correr la versión de referencia del algoritmo

```bash
python3 ref/p4_baseline.py tb/practica.csv
python3 ref/hallazgos.py tb/practica.csv
```

o `make hallazgos`. El primero simula el mercado con las mismas reglas del testbench y compara las estrategias de partida. El segundo agrega el análisis estadístico de la serie de práctica.

## Cómo sintetizar y programar la placa

```bash
make bin      # yosys, nextpnr e icepack: deja build/pochoco_soc.bin
make prog     # iceprog build/pochoco_soc.bin, con la Go Board conectada por USB
```

`make bin` ensambla `sw/trade.s` si hace falta y deja el programa dentro del bitstream. El resumen de celdas, BRAM y frecuencia máxima queda en `build/nextpnr.log`.

## Mediciones del repositorio base

```bash
make medir-base
```

Extrae la copia sin cambios del repositorio base (etiqueta `base-curso`) y mide celdas lógicas, BRAM, frecuencia máxima con 10 semillas, el costo de habilitar el shifter completo, si el encapsulado acepta un PLL y el CPI en simulación. El resultado queda en `docs/mediciones/base.txt`.

## Estructura

| Carpeta    | Contenido |
|------------|-----------|
| `rtl/`     | Pochoco SoC y Espino Core. |
| `sw/`      | `trade.s` y los programas de ejemplo del repositorio base. |
| `tb/`      | Testbench oficial, serie de práctica y testbenches propios. |
| `ref/`     | Referencia del algoritmo en Python y análisis de la serie. |
| `tools/`   | Ensamblador y scripts de medición. |
| `formal/`  | Verificación formal (todavía vacía). |
| `docs/`    | Enunciado, estado, decisiones, documentación y mediciones. |
| `informe/` | Informe en LaTeX (todavía vacío). |

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
