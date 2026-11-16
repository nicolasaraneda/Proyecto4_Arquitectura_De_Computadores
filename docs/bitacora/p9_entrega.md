# Bitácora del paquete P9: README e informe

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Rama `p8-anticipacion` (los puntos 6 y 7 del 16/11 se hicieron sobre ella, con P7 ya integrado).

## 16/11

- **Informe** (`informe/informe.tex`): responde 3.1, 3.2 y 3.3 en el orden del enunciado, con las tablas y la figura que se piden. Ninguna cifra está escrita a mano: `tools/report.py` (más `tools/report_33.py`) rehace `informe/generado/` con 58 macros y 11 tablas desde las referencias y `docs/mediciones/`, y copia las macros, las tablas en CSV y el roofline en TikZ que deja P7.
- El peldaño del informe se elige como el del comando oficial (`docs/peldano.md`): `rtl/00_peldano.v` si existe; si no, `PELDANO_INFORME` y por defecto R0. El texto que depende del peldaño va en `\ifpeldanofondo`. Así, al fijar el peldaño, `make report` regenera el informe solo.
- La ronda 1 de R1 no tenía mediciones por tick por el RTL (35 minutos de Verilator). Para la tabla del 3.2 los ciclos de esa ronda salen del gemelo y la tabla lo dice.
- La equivalencia que cita el informe la corre `make report` en el gemelo: la práctica a los tres períodos y 700 series sintéticas, 1,46 millones de ticks, cero diferencias.
- No hay LaTeX en la máquina y no se puede instalar sin `sudo`: el PDF lo compila un trabajo nuevo de la integración continua (`informe`), que instala `texlive` y deja dos PDF como artefacto, con el diseño por defecto y con R1. El comando para instalarlo localmente quedó en `docs/pendientes_nicolas.md`.
- Las mediciones en CSV estaban ignoradas por una regla `*.csv` del `.gitignore`: los de P7 no habían quedado en el repositorio. Se agregó la excepción `!docs/mediciones/**/*.csv`.
- **README** reescrito según la regla del enunciado: cómo ensamblar, correr los testbenches y la referencia, sintetizar y programar, versiones de herramientas, y una sección corta por pieza con el comando que la prueba y el número que la respalda. Las tablas largas de comandos pasaron a `docs/comandos.md`.
- **Rutas locales**: los scripts que agregaban la carpeta de OSS CAD Suite al `PATH` ahora la toman de `OSS_CAD_SUITE` o del `PATH`; se quitó la mención del plan local en `tb/tb_estres.sv` y la de la carpeta de trabajo en `docs/estado.md`.
