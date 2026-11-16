# Pendientes de Nicolás

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Decisiones y acciones que solo Nicolás puede tomar o hacer, acumuladas mientras se trabajó sin él. Cada una dice las opciones, qué se pierde con cada una, la recomendación y qué se hizo mientras tanto (la alternativa que no cierra opciones).

## Decisiones

Ninguna abierta. Las del 16/11 quedaron tomadas: la regla del árbol sigue en 115 kHz (T124) y las tres ramas sin integrar pasaron a etiquetas de archivo (T125).

## Acciones

1. **Usuarios de GitHub** de Santiago, del profesor y de cada ayudante, para invitarlos el 29/11 con permiso de lectura (`docs/checklist_1dic.md`, sección 1). Las invitaciones tardan en aceptarse.
2. **Números del PMOD.** `docs/checklist_26nov.md`, sección 2, asume PMOD 1 = `CS_n`, 2 = `MOSI`, 3 = `MISO`, 4 = `SCLK` (pines 65, 64, 63 y 62 del FPGA) y tierra en 5 u 11. Confirmarlo con la serigrafía de la placa o el esquemático de la Go Board antes del 26.
3. **Puerta de placa, en la placa** (`docs/autoprueba.md`, secciones 9 y 10, con lo que se debe ver en cada paso):
   - R0: con SW4 apretado deben aparecer `A2` (firma completa `a23c`).
   - `autoprueba_r1.bin`: con SW3, SW2 y SW1 (desconectando el USB entre uno y otro), LED2 y LED3 y `D7`; con SW4, `15`.
   - `autoprueba_r2_multi.bin` con `iceprog -b`: lo mismo, y dejarla 30 minutos con SW3: si aparecen los cuatro LED y `--`, el vigilante disparó y R2 no pasa.
   - `relevo_r2_multi.bin` con `iceprog -b`: con SW3, a los pocos milisegundos los cuatro LED y `--`. Medir el tiempo con `python3 tools/medir_relevo.py /dev/ttyUSB1 --segundos 20` (tres veces).
4. **OSS CAD Suite en el PATH.** Para que ningún archivo del repositorio tenga rutas locales, los scripts ya no agregan la carpeta de OSS CAD Suite al `PATH` por su cuenta: lo toman de la variable `OSS_CAD_SUITE` si existe, o del `PATH`. En el archivo de inicio de tu shell (local, no se sube): `export PATH=<carpeta de OSS CAD Suite>/bin:$PATH`, o `export OSS_CAD_SUITE=<carpeta de OSS CAD Suite>`. Sin eso, `make` no encuentra `yosys` ni `iverilog`.
5. **LaTeX para compilar el informe en tu máquina** (necesita `sudo`, no lo instalé): `sudo apt-get install -y texlive-latex-recommended texlive-latex-extra texlive-lang-spanish texlive-pictures texlive-fonts-recommended lmodern latexmk`. Después, `make report` deja `informe/informe.pdf`. Sin esto, el PDF lo compila la integración continua: trabajo `informe`, pestaña Summary de la corrida, artefacto `informe` (con el diseño por defecto y con R1).
