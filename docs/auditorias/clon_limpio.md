# Auditoría 1: el README seguido al pie de la letra en un clon limpio

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Prueba del 17/11: clonar el repositorio desde GitHub en una carpeta temporal fuera del árbol de trabajo y seguir `README.md` en orden, comando por comando, como lo haría un alumno nuevo. Se anota para cada comando qué se corrió, si funcionó, cuánto demoró y qué mostró. Cuenta como hallazgo todo comando que falle o que funcione gracias a algo que el README no dice (una variable de entorno, una herramienta en el `PATH`, un archivo que deja otro paso, otro repositorio, acceso a la red o una demora larga que no se avisa).

## 1. Entorno

| Qué | Valor |
|-----|-------|
| Commit clonado | `bc0e8c4` (`main` en GitHub) |
| Clon | `git clone https://github.com/nicolasaraneda/Proyecto4_Arquitectura_De_Computadores.git` en `/tmp/auditoria_clon_*/` |
| Máquina | WSL2 Ubuntu, 24 núcleos, 534 GB libres en `/home` |
| `PATH` | Uno limpio (`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`, sin OSS CAD Suite ni `OSS_CAD_SUITE`), más exactamente lo que pide `README.md:48`: `export PATH=$HOME/herramientas/oss-cad-suite/bin:$PATH` |
| Versiones vistas | Yosys 0.68+195, nextpnr-ice40 0.11.1-19-g8dbcee5c, Icarus Verilog 14.0 (s20260301), Verilator 5.053, Python 3.14.4 (`/usr/bin/python3`), gcc 15. Coinciden con la tabla de `README.md:36` a `:44`. |
| Carga | La máquina compartía la CPU con otros trabajos (carga promedio de 25 a 30 en la primera corrida). Los tiempos son de reloj de pared y sirven como orden de magnitud. |

La prueba se hizo dos veces. La primera corrida (madrugada del 17/11) llegó hasta el paso 12 y se perdió cuando la máquina se cayó: se borró `/tmp` con el clon y los registros, pero los resultados quedaron anotados y se informan abajo marcados con "1.ª". La segunda corrida (mañana del 17/11) se hizo en un clon nuevo del mismo commit, con la regla de correr los comandos pesados de a uno por la cola de la máquina; se marca "2.ª".

## 2. Comandos, en el orden del README

| N.º | README | Comando | Corrida | Resultado | Tiempo | Lo que mostró |
|-----|--------|---------|---------|-----------|--------|---------------|
| 1 | `:53` | `python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex` | 1.ª y 2.ª | Funciona | 0,1 s | "sw/trade.s -> sw/trade.hex (512 palabras, 2048 bytes)". `git status` limpio: el `.hex` versionado es idéntico. |
| 2 | `:56` | `make asm` | 1.ª y 2.ª | Funciona | < 0,1 s | "Nothing to be done" (el `.hex` ya está al día). |
| 3 | `:56` | `make test-asm` | 1.ª y 2.ª | Funciona | 0,2 a 0,3 s | 124 tests, OK. |
| 4 | `:56` | `python3 tools/pochoasm.py sw/fondo.s -o build/fondo/fondo.hex` | 1.ª y 2.ª | **Falla** | 0,1 s | `error: [Errno 2] No such file or directory: 'build/fondo/fondo.hex'`. En un clon limpio no existe `build/`. Ver hallazgo H1. |
| 5 | `:56` | `make fondo-hex` | 1.ª y 2.ª | Funciona | 0,1 s | Crea `build/fondo` y ensambla. Después de esto el comando 4 sí funciona. |
| 6 | `:63` | `python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex` | 1.ª y 2.ª | Funciona | 0,1 s | |
| 7 | `:64` | `iverilog -g2012 -s tb_proyecto_4 -o /tmp/tb_p4 $(yosys-config --datdir)/ice40/cells_sim.v rtl/*.v rtl/espino_core/*.v tb/tb_proyecto_4.sv` | 1.ª y 2.ª | Funciona | 0,1 s | Sin advertencias. |
| 8 | `:65` | `vvp -n /tmp/tb_p4` | 1.ª y 2.ª | Funciona | 115 s y 74 s | "Testbenchs aprobados: 4/4"; patrimonio 9 661, 74 órdenes, pérdida máxima 1 846, comprar y mantener 6 695, peor caso 44 de 2 262 ciclos. |
| 9 | `:68` | `make peldano-oficial` | 1.ª | Funciona | 125 s | "PASS: el comando oficial da 4/4 con el diseno por defecto"; `decisiones.csv` idéntico al de `ref/trader.py`. |
| 10 | `:68` | `make tb` | 1.ª | Funciona | 155 s | 4/4. |
| 11 | `:68` | `make fondo-oficial HW=r1` | 1.ª | Funciona | 268 s | "PASS: 4/4", `decisiones.csv` idéntico al de `ref/fondo.py` (2001 líneas), peor caso 443 de 2 262. **Reescribe un archivo versionado**: `docs/mediciones/fondo/r1/oficial.txt` (solo cambia la línea "Commit de partida"). Ver H4. |
| 12 | `:68` | `make fondo-oficial HW=r2` | 1.ª | Funciona | 312 s | Código de salida 0. El registro detallado se perdió con la caída. |
| 13 | `:72` | `make check` | | No corrido | | Ver sección 4. |
| 14 | `:73` | `make equiv` | | No corrido | | Ver sección 4. |
| 15 | `:74` | `make check-fondo HW=r1` | | No corrido | | Ver sección 4. |
| 16 | `:75` | `make fondo-puerta HW=r1` | | No corrido | | Ver sección 4. |
| 17 | `:82` | `python3 ref/trader.py tb/practica.csv` | 2.ª | Funciona | 0,1 s | No operar 10 000; comprar y mantener 6 497; regla base 27 062; `max_media` 25 973 con 624 órdenes. |
| 18 | `:83` | `python3 ref/trader.py tb/practica.csv -o build/ref.csv` | 2.ª | Funciona | 0,1 s | Funciona porque `build/` ya existe (lo creó el paso 5). En un clon donde se corra antes del paso 5, fallaría igual que el 4. |
| 19 | `:84` | `python3 ref/fondo.py tb/practica.csv -o build/ref_fondo.csv` | 2.ª | Funciona | 0,1 s | Patrimonio 26 388, 614 órdenes, pesos finales 6/6/4. Misma observación que el 18 sobre `build/`. |
| 20 | `:85` | `make test-ref test-fondo` | 2.ª | Funciona | 2,6 s | Compila `build/gemelo` con `cc`; 23 y 8 tests, OK. |
| 21 | `:88` | `make algoritmo` | | No corrido | | Documentado en unos 3 minutos (`docs/comandos.md:20`); reescribe 13 archivos de `docs/mediciones/`. Ver sección 4. |
| 22 | `:95` | `cd bitstreams && sha256sum -c SHA256SUMS && cd ..` | 2.ª | Funciona | < 0,1 s | Los 17 archivos de `SHA256SUMS` dicen OK. |
| 23 | `:96` y `:97` | `iceprog bitstreams/r1_fondo.bin`; `iceprog -b bitstreams/r2_multi.bin` | | No ejecutable en este entorno | | Necesita la placa conectada por USB (y `usbipd` en WSL). |
| 24 | `:105` | `make bin` | 2.ª | Funciona | 5,5 s | Yosys, nextpnr e icepack; 42,49 MHz con la semilla por defecto (pasa a 25 MHz); 2 advertencias por las restricciones `i_UART_RX` y `o_UART_TX` de `goboard.pcf` sin uso. El `.bin` (sha256 `4c1d845f...`) **no es** el `bitstreams/r0_base_max_media.bin` guardado (`67f6f1c4...`, 44,6 MHz). Ver H7. |
| 25 | `:106` | `make prog` | | No ejecutable en este entorno | | Llama a `iceprog`. |
| 26 | `:107` | `make r0-reproducir` | | No corrido | | Ver sección 4. |
| 27 | `:108` | `make fondo-bitstreams` | | No corrido | | Documentado en unos 25 minutos en el `Makefile`; el README no lo dice. Lanza 4 síntesis y después 6 simulaciones en paralelo (`tools/fondo/bitstreams.sh:90` a `:93` y `:132` a `:137`), más que el límite de 4 procesos de esta auditoría. Ver sección 4 y H2. |
| 28 | `:111` | `make sim-bitstream` | | (en la cola) | | Documentado en unos 8 minutos en el `Makefile`. Es el comando largo representativo de esta corrida. |
| 29 | `:119` | `make tabla-3-1` | 2.ª | Funciona | 0,1 s | Reescribe `docs/mediciones/tabla_3_1.txt` idéntico (sin diferencias en `git status`). |
| 30 | `:179` | `make retune-control` | 2.ª | Funciona | 1,2 s | "PASS control: con las reglas publicadas no cambia nada"; arma R0, R1, R2 y la imagen múltiple con `icebram` y los cuatro `.bin` tienen el mismo sha256 que los de `bitstreams/` (confirma `README.md:180`). Avisa que los `.asc` no se simularon por los pines (eso es `--simular`). |
| 31 | `:173` | `make p7-rapido` | 2.ª | Funciona | 0,2 s | "282 macros en docs/mediciones/p7/cifras.tex"; todos los archivos de `docs/mediciones/p7/` quedan idénticos. |
| 32 | `:185` | `make report` | 2.ª | Funciona | 3,3 s | "62 cifras y tablas en informe/generado/"; sin LaTeX no compila el PDF y lo avisa. Solo cambia `informe/generado/peldano.tex` (el commit impreso). Ver H4. |

Los comandos de las secciones "Piezas" del README (`:119` a `:185`) que no aparecen en la tabla se listan en la sección 4.

## 3. Hallazgos

| N.º | Tipo | Archivo:línea | Hallazgo | Corrección sugerida |
|-----|------|---------------|----------|---------------------|
| H1 | **Error** | `README.md:56` | `python3 tools/pochoasm.py sw/fondo.s -o build/fondo/fondo.hex` falla en un clon limpio porque `build/fondo/` no existe; el ensamblador no crea la carpeta de salida. Los comandos de `README.md:83` y `:84` (`-o build/ref.csv` y `-o build/ref_fondo.csv`) dependen de lo mismo y solo funcionaron porque un paso anterior ya había creado `build/`. | Que `tools/pochoasm.py`, `ref/trader.py` y `ref/fondo.py` creen la carpeta de salida (`os.makedirs(os.path.dirname(out), exist_ok=True)`), o escribir en el README `mkdir -p build/fondo` antes, o dejar solo `make fondo-hex`. |
| H2 | Sugerencia | `README.md:32` a `:48` | El README no avisa cuánto demora ningún comando. Varios toman minutos (`make fondo-oficial`, 4 a 5 minutos; `make fondo-bitstreams`, unos 25; `make autoprueba-r1` y `-r2`, unos 25 cada uno; `make p7`, unos 25) y `make fondo-puerta HW=r1`, que la tabla de `:75` presenta junto a los cortos, incluye la ronda de 10 ms que el `Makefile` documenta en 35 minutos. Las demoras están en comentarios del `Makefile` y en parte en `docs/comandos.md`, no en el README. | Agregar una columna "Demora aproximada" a la tabla de `README.md:70` y a cada "Prueba" de la sección "Piezas". |
| H3 | Sugerencia | `README.md:46` a `:48` | Requisitos que se usan y no se nombran: `make`, `git` con el historial completo (`make r0-reproducir` reconstruye R0 desde su commit y falla con un clon superficial o con el ZIP de GitHub; `tools/reproducir_r0.sh:38`) y acceso de lectura al repositorio, que es privado. | Nombrarlos en "Herramientas y versiones" y decir "clonar con `git clone`, no descargar el ZIP". |
| H4 | Sugerencia | `README.md:68`, `:185` | Correr las pruebas deja el árbol modificado: `make fondo-oficial HW=r1` reescribe `docs/mediciones/fondo/r1/oficial.txt` (cambia solo la línea del commit) y `make report` reescribe `informe/generado/peldano.tex` (cambia solo el commit impreso). Un alumno que siga el README termina con archivos versionados cambiados sin haber tocado nada. | Escribir esas salidas en `build/` y copiarlas a `docs/` solo con un objetivo explícito, o no registrar el commit en archivos versionados. |
| H5 | Sugerencia | `README.md:73` | "`make equiv`: R0 contra la referencia, byte a byte, en los 20 000 ticks a los tres períodos". Según el `Makefile` (objetivos `equiv-gemelo-20k`, `equiv-verilator`, `equiv-r1`), los 20 000 ticks a 10 ms solo se corren en el gemelo digital; por el RTL son 20 ticks a 10 ms con Icarus. | "a 0,1 ms y 1 ms por el RTL, y a los tres períodos en el gemelo". |
| H6 | Sugerencia | `README.md:48` frente a `docs/fondo.md:390` | El README dice bien que OSS CAD Suite tiene que estar en el `PATH` (y con eso todo funcionó con un `PATH` limpio), pero `docs/fondo.md:390` dice que "los scripts agregan OSS CAD Suite al `PATH`", lo que ya no es cierto. Un lector que llegue por ese documento no lo exportaría. | Corregir `docs/fondo.md:390`. |
| H7 | Sugerencia | `README.md:105` y `bitstreams/README.md:5` | "`make bin` # R0 ... deja build/pochoco_soc.bin" y "Desde entonces `make bin` produce R0". Con las fuentes actuales `make bin` da el mismo diseño, pero no el mismo archivo: otro sha256 y otra frecuencia (42,49 contra 44,6 MHz), porque desde el commit `c293cf4` Yosys recibe más archivos y entrega otra netlist equivalente (`docs/mediciones/p7/caida_segmentado.txt`). Un alumno que compare con `SHA256SUMS` creerá que algo salió mal. El README sí dice que la copia exacta sale de `make r0-reproducir` (`:107`). | Decir en `:105` que el `.bin` no coincide byte a byte con el guardado y que para la placa se usa `bitstreams/r0_base_max_media.bin` o `make r0-reproducir`. |

Positivo: con un `PATH` limpio y solo la línea `export` del README, todas las herramientas se encontraron; no hizo falta ninguna variable de entorno adicional, ningún repositorio hermano ni acceso a la red fuera del `git clone`. Los resultados coinciden con lo que el README y las mediciones guardadas dicen (4/4, 9 661, 25 973, 443 ciclos, 62 cifras).

## 4. No corridos

Por la regla de esta auditoría (los comandos pesados se corren de a uno por la cola común de la máquina, y de los largos solo uno o dos representativos), estos comandos del README no se corrieron:

| Comando | README | Demora documentada | Por qué no |
|---------|--------|--------------------|------------|
| `make check` | `:72` | Unos 3 minutos (incluye el testbench oficial) | Pesado; el testbench oficial ya se corrió (pasos 8 a 10). Lo corre la integración continua en cada push. |
| `make equiv` | `:73` | No documentada (Verilator sobre 20 000 ticks dos veces y 13 series) | Pesado. |
| `make check-fondo HW=r1` | `:74` | No documentada | Pesado. |
| `make fondo-puerta HW=r1` | `:75` | No documentada en el README; incluye `fondo-equiv-ronda1` (35 minutos según el `Makefile`) | Largo. Se intentó en la primera corrida como comando representativo y la caída de la máquina lo interrumpió. |
| `make algoritmo` | `:88`, `:119` | Unos 3 minutos | Pesado y reescribe 13 archivos de `docs/mediciones/`. |
| `make r0-reproducir` | `:107` | Unos 2 minutos | Pesado (síntesis). |
| `make fondo-bitstreams` | `:108` | Unos 25 minutos | Largo y con 6 simulaciones en paralelo, sin opción para limitarlas (el script no lee `JOBS`). |
| `make cosim`, `make cosim-barrel` | `:125` | 2 y 6 minutos | Pesados. |
| `make check-seg`, `make paralelo-largo` | `:131` | No documentadas | Pesados. |
| `make check-barrel`, `make barrel-verif`, `make barrel-mutaciones` | `:137` | `barrel-verif` unos 6 minutos con 12 procesos | Pesados. |
| `make check-xd`, `make xd-formal` | `:143` | No documentadas | Pesados. |
| `make check-fondo` | `:149` | No documentada | Igual al paso 15. |
| `make check-vigilante` | `:155` | No documentada | Pesado. |
| `make fondo-estres HW=r1`, `make estres`, `make p8-matriz` | `:161` | `estres` unos 2 minutos con 16 núcleos; `p8-matriz` 10 s | Pesados (el de 10 s usa el gemelo, pero se dejó fuera para no saturar la cola). |
| `make autoprueba-r0`, `make autoprueba-r1`, `make autoprueba-r2` | `:167` | 20 y 25 minutos | Largos. |
| `make p7` | `:173` | Unos 25 minutos | Largo. Se corrió `make p7-rapido`. |
| `make medidor` | `:179` | 1 minuto | Pesado (síntesis y simulación). |
| `make contingencia` | `:179` | 45 minutos | Largo. |
| `iceprog ...`, `make prog` | `:96`, `:97`, `:106` | | No ejecutables en este entorno (sin placa; además la regla del grupo es que solo Nicolás graba la placa). |

## 5. Resumen

- Comandos distintos corridos: 22 (12 en la primera corrida y 18 en la segunda, 8 de ellos repetidos). Funcionaron todos menos uno.
- Comando que falló: `python3 tools/pochoasm.py sw/fondo.s -o build/fondo/fondo.hex` (`README.md:56`), en las dos corridas.
- Hallazgos: 1 error (H1) y 6 sugerencias (H2 a H7).
- No corridos: 26 comandos del README, por la regla de la cola; 3 no ejecutables en este entorno.
