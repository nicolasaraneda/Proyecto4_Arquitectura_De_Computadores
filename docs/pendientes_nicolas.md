# Pendientes de Nicolás

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Decisiones y acciones que solo Nicolás puede tomar o hacer, acumuladas mientras se trabajó sin él. Cada una dice las opciones, qué se pierde con cada una, la recomendación y qué se hizo mientras tanto (la alternativa que no cierra opciones).

## Decisiones

### 1. Umbral de SCLK del árbol: 115 kHz o 110 kHz

Con el programa de P5, R1 responde a tiempo a 0,1 ms desde SCLK de 110 kHz (antes, con el de P3, desde 115 kHz). La regla que fijaste es "con SCLK bajo 115 kHz en la ronda 3 compite R0".

- **(a) Mantener 115 kHz** (recomendada). Deja 5 kHz de margen para el error del medidor y para un SCLK inestable. Se pierde R1 solo si la maestra usa entre 110 y 115 kHz.
- (b) Bajar a 110 kHz. Gana ese rango, sin margen.

Mientras tanto: el árbol usa 115 kHz (decisión T124).

## Acciones

1. **Usuarios de GitHub** de Santiago, del profesor y de cada ayudante, para invitarlos el 29/11 con permiso de lectura (`docs/checklist_1dic.md`, sección 1). Las invitaciones tardan en aceptarse.
2. **Números del PMOD.** `docs/checklist_26nov.md`, sección 2, asume PMOD 1 = `CS_n`, 2 = `MOSI`, 3 = `MISO`, 4 = `SCLK` (pines 65, 64, 63 y 62 del FPGA) y tierra en 5 u 11. Confirmarlo con la serigrafía de la placa o el esquemático de la Go Board antes del 26.
3. **SW4 en la autoprueba de R0.** Falta ver la mitad alta de la firma: con SW4 apretado deben aparecer `A2` (firma completa `a23c`). Comandos en `docs/autoprueba.md`, sección 5.
4. **OSS CAD Suite en el PATH.** Para que ningún archivo del repositorio tenga rutas locales, los scripts ya no agregan la carpeta de OSS CAD Suite al `PATH` por su cuenta: lo toman de la variable `OSS_CAD_SUITE` si existe, o del `PATH`. En el archivo de inicio de tu shell (local, no se sube): `export PATH=<carpeta de OSS CAD Suite>/bin:$PATH`, o `export OSS_CAD_SUITE=<carpeta de OSS CAD Suite>`. Sin eso, `make` no encuentra `yosys` ni `iverilog`.
5. **LaTeX para compilar el informe en tu máquina** (necesita `sudo`, no lo instalé): `sudo apt-get install -y texlive-latex-recommended texlive-latex-extra texlive-lang-spanish texlive-pictures texlive-fonts-recommended lmodern latexmk`. Después, `make report` deja `informe/informe.pdf`. Sin esto, el PDF lo compila la integración continua: trabajo `informe`, pestaña Summary de la corrida, artefacto `informe` (con el diseño por defecto y con R1).
