# Pendientes de Nicolás

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Decisiones y acciones que dependen de Nicolás. Cada una dice las opciones, qué se pierde con cada una, la recomendación y qué se hizo mientras tanto (la alternativa que no cierra opciones).

## Decisiones

1. **Qué algoritmo compite: `max_media` o `zscore` (T129, T130, `docs/zscore.md`, secciones 4.5 y 7).** Con el criterio fijado antes de medir (remuestreos de trozos de 100 y el modelo calibrado), `zscore` pierde. Con trozos de 250 o más, en tramos reales contiguos y eligiendo parámetros en una mitad de la práctica para probarlos en la otra, gana (+313 +- 43 con trozos de 1000; +0,107 puntos H3b). En el modelo no gana, y las muestras independientes de verdad (10 bloques) dan +346 +- 321.
   - **(a) `max_media` en todo.** No supone nada sobre la serie oculta. Se pierde la ventaja si la serie oculta se parece a la práctica en escalas de cientos de ticks.
   - **(b) `zscore` en R0 (y en el supervisor y los gestores de R1 y R2).** Gana si la serie oculta se parece a la práctica; pierde más que `max_media` en series volátiles o de precio bajo (sección 4.1). Cuesta unos 3 días para R0 y 4 a 5 más para R1 y R2 (programa, tabla, referencias, equivalencias, autopruebas y puertas), sin tocar el hardware: alcanza antes del congelamiento total del 29/11 pero aprieta el informe y la defensa.
   - **(c) Decidir el 26/11 con dos datos**: si el ayudante confirma que las series ocultas salen del mismo generador que la práctica, y la serie que registre el registrador (si el ayudante dice que no es la de la competencia). Mientras tanto, preparar `zscore` para R0 en una rama sin integrar, para que el cambio quede listo.
   - **Recomendación: (c)**, con la rama de (b) para R0 preparada desde ahora. La ventaja de `zscore` depende de una sola pregunta que se puede hacer el 26/11, y R0 se cambia con `icebram` sin resintetizar.
   - Tu decisión anunciada en el próximo mensaje manda sobre esta recomendación.
2. **Usar la serie que se registre el 26/11 para aceptar algoritmos (tarea B).** El registrador solo escucha, y la serie no entra al diseño. Pero si la maestra del 26/11 usa la misma serie que la competencia, aceptar o rechazar un algoritmo por su resultado en ella es elegir con la serie oculta, que choca con el espíritu de la regla de no usar información externa a la serie. Opciones: (a) usarla solo como control de que el gemelo predice el patrimonio de la maestra (puerta de maestra, criterio 2) y no para elegir algoritmos; (b) usarla para aceptar candidatos solo si el ayudante confirma que la serie del 26/11 no es la de la competencia. **Recomendación: preguntar al ayudante el 26/11 y, mientras tanto, (a).**

3. **Salida de `max_media` a +0,5 unidades (tarea B, T131, `docs/generador_b.md`).** Pasa el criterio de corte con la semilla reservada si los otros grupos operan todos reversión; si el campo es variado, pierde (H3a -0,011 a 2000 ticks). En la práctica pierde 173 +- 137 por bloque. Cambiarla es una constante: el umbral de salida de 1 a 17 (`sw/trade.s` en R0, `S_SALE` y `G1_SALE` en la tabla de R1 y R2), cargable con `icebram` sin sintetizar.
   - **(a) No cambiar.** Es lo robusto si no se sabe qué hacen los otros grupos.
   - **(b) Cambiar después del 26/11** si se ve que los otros grupos operan reversión y la candidata gana en la serie registrada (si el ayudante dice que no es la de la competencia).
   - **Recomendación: (a)**, y mirar el 26/11 qué hacen los otros grupos. Si se adopta `zscore` (decisión 1), esta candidata deja de aplicar: habría que repetir la tarea B contra `zscore`.

## Acciones

1. **Usuarios de GitHub** de Santiago, del profesor y de cada ayudante, para invitarlos el 29/11 con permiso de lectura (`docs/checklist_1dic.md`, sección 1). Las invitaciones tardan en aceptarse.
2. **Números del PMOD.** `docs/checklist_26nov.md`, sección 2, asume PMOD 1 = `CS_n`, 2 = `MOSI`, 3 = `MISO`, 4 = `SCLK` (pines 65, 64, 63 y 62 de la FPGA) y tierra en 5 u 11. Confirmarlo con la serigrafía de la placa o el esquemático de la Go Board antes del 26.
3. **Puerta de placa, en la placa** (`docs/autoprueba.md`, secciones 9 y 10, con lo que se debe ver en cada paso):
   - R0: con SW4 apretado deben aparecer `A2` (firma completa `a23c`).
   - `autoprueba_r1.bin`: con SW3, SW2 y SW1 (desconectando el USB entre uno y otro), LED2 y LED3 y `D7`; con SW4, `15`.
   - `autoprueba_r2_multi.bin` con `iceprog -b`: lo mismo, y dejarla 30 minutos con SW3: si aparecen los cuatro LED y `--`, el vigilante disparó y R2 no pasa.
   - `relevo_r2_multi.bin` con `iceprog -b`: con SW3, a los pocos milisegundos los cuatro LED y `--`. Medir el tiempo con `python3 tools/medir_relevo.py /dev/ttyUSB1 --segundos 20` (tres veces).
4. **OSS CAD Suite en el PATH.** Para que ningún archivo del repositorio tenga rutas locales, los scripts ya no agregan la carpeta de OSS CAD Suite al `PATH` por su cuenta: lo toman de la variable `OSS_CAD_SUITE` si existe, o del `PATH`. En el archivo de inicio del shell (local, no se sube): `export PATH=<carpeta de OSS CAD Suite>/bin:$PATH`, o `export OSS_CAD_SUITE=<carpeta de OSS CAD Suite>`. Sin eso, `make` no encuentra `yosys` ni `iverilog`.
5. **LaTeX para compilar el informe localmente** (requiere `sudo`): `sudo apt-get install -y texlive-latex-recommended texlive-latex-extra texlive-lang-spanish texlive-pictures texlive-fonts-recommended lmodern latexmk`. Después, `make report` deja `informe/informe.pdf`. Sin esto, el PDF lo compila la integración continua: trabajo `informe`, pestaña Summary de la corrida, artefacto `informe` (con el diseño por defecto y con R1).
