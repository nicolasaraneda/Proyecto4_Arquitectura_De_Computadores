# Pendientes de Nicolás

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Decisiones y acciones que solo Nicolás puede tomar o hacer, acumuladas mientras se trabajó sin él. Cada una dice las opciones, qué se pierde con cada una, la recomendación y qué se hizo mientras tanto (la alternativa que no cierra opciones).

## Decisiones

1. **`zscore` a 20 000 ticks (T129, `docs/zscore.md`, sección 7).** La regla de Vicente no gana bajo el protocolo y `max_media` sigue en todo. Queda un solo resultado a favor de una variante (z = 1,5 con la desviación de memoria 128): en las familias plausibles a 20 000 ticks gana el 65 % de las rondas y +0,044 a +0,050 puntos H3b, con empate en H3a; en los remuestreos del mismo largo y a 2000 ticks pierde.
   - **(a) Cerrar el tema.** `max_media` en los tres peldaños. No se pierde nada medido: el criterio fijado antes de medir dice que no pasa.
   - **(b) Reabrir solo si el 26/11 el ayudante confirma rondas de 20 000 ticks o más y series del mismo generador.** Se fijaría antes un criterio restringido a las plausibles a 20 000 ticks, con una semilla nueva (5), y la serie registrada el 26/11 como prueba adicional. Si pasa, se cambia el programa (sin tocar hardware): unos 3 días para R0 y 4 a 5 más para R1 y R2, dentro del congelamiento del 29/11 pero con poco margen para el informe y la defensa. Se pierde ese tiempo, y el riesgo de elegir un subconjunto después de mirar.
   - **Recomendación: (a).** La ventaja aparece solo en H3b (el puesto) y no en el patrimonio, se da vuelta en los remuestreos, y opera 40 % más (1 017 órdenes por ronda contra 736: más expuesta si cambia la comisión).
   - Mientras tanto: nada cambió en R0, R1 ni R2.
2. **Usar la serie que se registre el 26/11 para aceptar algoritmos (tarea B).** El registrador solo escucha, y la serie no entra al diseño. Pero si la maestra del 26/11 usa la misma serie que la competencia, aceptar o rechazar un algoritmo por su resultado en ella es elegir con la serie oculta, que choca con el espíritu de la regla de no usar información externa a la serie. Opciones: (a) usarla solo como control de que el gemelo predice el patrimonio de la maestra (puerta de maestra, criterio 2) y no para elegir algoritmos; (b) usarla para aceptar candidatos solo si el ayudante confirma que la serie del 26/11 no es la de la competencia. **Recomendación: preguntar al ayudante el 26/11 y, mientras tanto, (a).**

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
