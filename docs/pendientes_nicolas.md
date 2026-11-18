# Pendientes de Nicolás

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Decisiones y acciones que dependen de Nicolás. Cada una dice las opciones, qué se pierde con cada una, la recomendación y qué se hizo mientras tanto (la alternativa que no cierra opciones).

## Decisiones

0. **Decidido (T133): (R-a) con (F-a) en los tres peldaños**, "es la que no pierde si la hipótesis de la normalización resulta falsa". Lo que sigue es el análisis que se presentó. **Regla nueva para R0, R1 y R2 con la serie Meta (17/11, `docs/cotas.md`).** Ninguna regla actual gana en la serie nueva: `max_media` da 9 722 y `zscore` 7 340, bajo los 10 000 de no operar. Si cada ronda se normaliza por separado (el mínimo es 100 y el máximo 255), la familia "cotas" casi duplica el patrimonio en la población de las cinco empresas, en los tres largos y en las dos validaciones (por años y por empresa), y supera a `max_media` en más del 90 % de las ventanas. **El hardware no cambia en ninguna opción**: solo cambian el programa y la tabla, que entran por `icebram` en los mismos bitstreams que hoy pasan por la maestra.

   **La regla.** Opciones:
   - **(R-a) "espera" con banda 60** (parte en caja; compra al ver 100, vende al ver 255; después de ver los dos, compra con p ≤ 160 y vende con p ≥ 195). Media de 19 900 a 20 500 en la población, 19 214 en la serie Meta. Si la hipótesis es falsa no pierde más que una comisión. Es la mejor en el torneo cuando otros grupos también usan los extremos (0,80 a 0,86 puntos, primera en la mitad de las rondas).
   - **(R-b) comprar 20 acciones al inicio, con banda 70.** Media de 19 700 a 20 300, mejor percentil 5 (10 800 contra 10 150 con 2000 ticks) y termina sobre no operar en el 99 % contra el 96 %. Pero si la hipótesis es falsa pierde hasta 2 100, y queda primera en menos rondas cuando otros usan los extremos (14 a 32 %). 24 671 en la serie Meta.
   - **(R-c) "compra" con banda 40**, la de 32 149 en la serie Meta: en la población queda bajo las dos anteriores (18 300 a 19 400) y pierde como comprar y mantener si la hipótesis es falsa.
   - **Recomendación: (R-a)**, y preguntar al ayudante si cada ronda se normaliza por separado.

   **El programa de cada peldaño.** Opciones:
   - **R0** (Espino base, `sw/trade.s`): la regla elegida en lugar de `max_media`. Unas 20 instrucciones, sin multiplicaciones. Toma medio día: referencia exacta, `trade.s`, equivalencia y la puerta de simulación de R0 (unas 2 horas de cómputo).
   - **R1 y R2, opción (F-a): la regla en el hilo 0 del barrel y los hilos 1 a 3 en espera.** Se pierde el fondo que vota; la extensión (`emad` y `devk`) queda en el hardware sin uso, como `mulstep` hoy. Toma de 1 a 1,5 días, porque las pruebas de la puerta de R1 (degradación, controles, protocolo de votos) están hechas para `fondo.s` y hay que adaptarlas.
   - **R1 y R2, opción (F-b): mantener el fondo**, con los tres gestores corriendo variantes de cotas (por ejemplo bandas de 40, 60 y 76) y el supervisor con la regla elegida como respaldo. Conserva el co-diseño de cuatro hilos y reutiliza las pruebas de la puerta, pero los votos de reglas tan parecidas coinciden casi siempre: no hay medición que diga que gana algo. Toma de 1,5 a 2 días.
   - **R1 y R2, opción (F-c): no cambiar `fondo.s`.** Pierde: 9 722 en la serie Meta y 0,21 a 0,27 puntos en el torneo.
   - **Recomendación: (F-a).** Con una regla de extremos, un fondo que vota no agrega decisiones distintas y sí puntos de falla.

   **Lo que hay que rehacer en cualquier opción:** las firmas de las autopruebas de placa (dependen del programa: se regeneran con el gemelo y hay que volver a correrlas en la placa, una hora tuya), los moldes de `icebram`, el gemelo con la regla nueva, y el informe, el README y la defensa (`docs/obsoleto_serie_meta.md`, unos 2 días). El banco de contingencia y `retune` quedan obsoletos (la comisión casi no pesa en una regla de 2 a 15 órdenes).

   **¿Llega al 25/11?** Sí: unos 3 días de programas y puertas, más 2 de documentos. Como el hardware no cambia, lo que se pruebe con la maestra mañana sigue valiendo, y el programa se puede cambiar hasta el 29/11 sin volver a la maestra.

1. ~~**Qué algoritmo compite: `max_media` o `zscore`.**~~ **Sin efecto** desde el 17/11: con la serie Meta las dos pierden contra no operar (decisión 0).

2. **Usar la serie que se registre el 26/11 para aceptar algoritmos (tarea B).** El registrador solo escucha, y la serie no entra al diseño. Pero si la maestra del 26/11 usa la misma serie que la competencia, aceptar o rechazar un algoritmo por su resultado en ella es elegir con la serie oculta, que choca con el espíritu de la regla de no usar información externa a la serie. Opciones: (a) usarla solo como control de que el gemelo predice el patrimonio de la maestra (puerta de maestra, criterio 2) y no para elegir algoritmos; (b) usarla para aceptar candidatos solo si el ayudante confirma que la serie del 26/11 no es la de la competencia. **Recomendación: preguntar al ayudante el 26/11 y, mientras tanto, (a).**

3. **Salida de `max_media` a +0,5 unidades (tarea B, T131, `docs/generador_b.md`).** Pasa el criterio de corte con la semilla reservada si los otros grupos operan todos reversión; si el campo es variado, pierde (H3a -0,011 a 2000 ticks). En la práctica pierde 173 +- 137 por bloque. Cambiarla es una constante: el umbral de salida de 1 a 17 (`sw/trade.s` en R0, `S_SALE` y `G1_SALE` en la tabla de R1 y R2), cargable con `icebram` sin sintetizar.
   - **(a) No cambiar.** Es lo robusto si no se sabe qué hacen los otros grupos.
   - **(b) Cambiar después del 26/11** si se ve que los otros grupos operan reversión y la candidata gana en la serie registrada (si el ayudante dice que no es la de la competencia).
   - **Recomendación: (a)**, y mirar el 26/11 qué hacen los otros grupos. Si se adopta `zscore` (decisión 1), esta candidata deja de aplicar: habría que repetir la tarea B contra `zscore`.

4. **Precios fantasma del esclavo SPI del curso (revisión P10, hallazgo 1, `docs/revision_p10.md`).** Si el contador de bits del esclavo queda en 7 (una transacción de 7 flancos, o el reset de encendido terminando a mitad de una transacción) y después hay flancos de SCLK con `CS_n` en alto (bus compartido o ruido), cada flanco es un precio. En R2 dispara el vigilante con el programa sano; en R0 y R1 mete precios falsos en la media. Reproducción: `make p10-spi-7flancos` y `make p10-formal-spi`. El testbench oficial nunca lo produce.
   - **(a) Adoptar el arreglo** de la rama `p10-arreglo-1` (un parámetro en el esclavo, activo solo con el barrel; R0 no cambia). Pasa sus pruebas y el testbench oficial da 4/4 con los tres peldaños, pero cambia el hardware de R1 y R2: hay que repetir su puerta completa, los bitstreams, las autopruebas y los moldes antes del 25/11 (unas 4 horas de cola).
   - **(b) No cambiar el hardware y medir el 26/11** con el medidor nuevo (ya integrado: LED4 avisa flancos de SCLK con `CS_n` en alto). Si aparecen, competir con R1 en vez de R2 (el vigilante es el único que convierte el problema en un relevo).
   - **Recomendación: (b)**, porque la condición necesita un bus que la maestra del enunciado no tiene y (a) cambia hardware que ya pasó su puerta; si el 26/11 el medidor la ve, R1.
5. **Reiniciar la placa entre rondas (revisión P10, observación 2).** Si la maestra reinicia la caja entre rondas y la placa no, la ronda nueva parte con la última orden y la media de la serie anterior: cuesta en promedio 63 por ronda con series del mismo generador y 1 922 si la serie nueva tiene otro nivel (peor caso -57 552). Hoy `docs/checklist_1dic.md` dice no reprogramar entre rondas.
   - **Recomendación:** preguntar el 26/11 si la caja se reinicia y si las series son independientes; si las dos respuestas son sí, desconectar y conectar el USB entre rondas (un minuto, sin reprogramar).

## Acciones

0. **La integración continua de GitHub dejó de correr el 17/11 en la tarde.** Todos los trabajos fallan en segundos con "The job was not started because recent account payments have failed or your spending limit needs to be increased" (corridas 44109393726 en adelante). Se arregla en GitHub, Settings, Billing and plans: revisar el medio de pago o subir el límite de gasto de Actions. Mientras tanto, `~/proyectos/cola/ci_local.sh` corre en la máquina los mismos pasos de los trabajos `verificar`, `extension` y `fondo` (sin el PDF del informe, que necesita LaTeX).
0b. **Avanzar `main` a `integra-noche`** (permiso de Nicolás del 17/11: cuando la integración continua esté en verde). La corrida local de los mismos pasos de la integración continua pasó 24 de 24 sobre `e9fd653` (`docs/mediciones/ci_local_17nov.txt`); lo que vino después en `integra-noche` es solo documentación. Comando: `git push origin <sha de integra-noche>:refs/heads/main`. No se hizo porque requiere tu permiso.
1. **Usuarios de GitHub** de Santiago, del profesor y de cada ayudante, para invitarlos el 29/11 con permiso de lectura (`docs/checklist_1dic.md`, sección 1). Las invitaciones tardan en aceptarse.
2. **Números del PMOD.** `docs/checklist_26nov.md`, sección 2, asume PMOD 1 = `CS_n`, 2 = `MOSI`, 3 = `MISO`, 4 = `SCLK` (pines 65, 64, 63 y 62 de la FPGA) y tierra en 5 u 11. Confirmarlo con la serigrafía de la placa o el esquemático de la Go Board antes del 26.
3. **Pruebas de placa pendientes** (lo que no se corrió o no se anotó el 16/11, `docs/mediciones/placa_16nov.md`; qué se debe ver en cada paso en `docs/autoprueba.md`, secciones 9 y 10):
   - `autoprueba_r1.bin`, firma a los tres períodos: SW3, SW2 y SW1, desconectando el USB entre uno y otro. Se debe ver LED2 y LED3 y `D7`; con SW4, `15`. No se corrió ninguno.
   - `autoprueba_r2_multi.bin` (con `iceprog -b`) a 1 ms (SW2) y 10 ms (SW1): lo mismo que a 0,1 ms. Solo se corrió SW3.
   - `relevo_r2_multi.bin` (con `iceprog -b`), a la vista: con SW3, a los pocos milisegundos los cuatro LED y `--`. El 16/11 solo se midió por la UART.
   - Dos mediciones más del relevo: `python3 tools/medir_relevo.py /dev/ttyUSB1 --segundos 20`, para tener tres. La del 16/11 dio 35,50 ms.
   - `r1_fondo.bin` sin maestra: se vio `00`; falta anotar los LED (se esperan los cuatro apagados).
   - `autoprueba_r0.bin` con SW4: la mitad alta de la firma, se espera `A2` (firma completa `a23c`). El 16/11 solo se vio la mitad baja, `3C`.
3b. **Datos por minuto de 2022 a 2024 (paso 4 del 17/11).** No hay una fuente gratuita sin cuenta que los cubra: Yahoo da el minuto solo de los últimos 30 días, Stooq ahora pide resolver una prueba antibots (no se elude) y HF Data Library (barras de IEX desde el 7/3/2022, licencia CC BY 4.0, uso académico) pide una cuenta con correo verificado para descargar. Mientras tanto se usan los precios diarios de Yahoo (sin clave) y los días de la serie Meta (`docs/cotas.md`, sección 5). Para tener los minutos reales, la opción recomendada es **Alpaca**: histórico consolidado (SIP, el 100 % del volumen, no solo IEX), desde 2016, gratis, con una cuenta de papel sin depositar dinero:
   1. Crear la cuenta en https://app.alpaca.markets/signup con tu correo y confirmar el correo.
   2. Entrar al panel de **Paper Trading** (no hace falta abrir la cuenta real ni dar datos bancarios).
   3. En la página principal del panel de papel, sección "API Keys", **Generate New Keys**. Copiar el "Key ID" y el "Secret Key" (el secreto se muestra una sola vez).
   4. En WSL, en esa terminal (no en un archivo del repositorio): `export APCA_API_KEY_ID=<Key ID>` y `export APCA_API_SECRET_KEY=<Secret Key>`.
   5. `cd ~/proyectos/P4_wt_int && python3 tools/datos/alpaca.py`. Baja META, AAPL, NFLX, AMD y TSLA de 2022 a 2024 (unos 1,5 millones de minutos; del orden de 15 minutos por el límite de llamadas) a `data/externos/minuto/`, que no se versiona.
   Alternativa: HF Data Library (https://hfdatalibrary.com, crear cuenta, verificar el correo, descargar el CSV "clean" de 1 minuto de cada ticker y dejarlo en `data/externos/hf/`). Tiene solo los precios de IEX y empieza el 7/3/2022.
4. **OSS CAD Suite en el PATH.** Para que ningún archivo del repositorio tenga rutas locales, los scripts ya no agregan la carpeta de OSS CAD Suite al `PATH` por su cuenta: lo toman de la variable `OSS_CAD_SUITE` si existe, o del `PATH`. En el archivo de inicio del shell (local, no se sube): `export PATH=<carpeta de OSS CAD Suite>/bin:$PATH`, o `export OSS_CAD_SUITE=<carpeta de OSS CAD Suite>`. Sin eso, `make` no encuentra `yosys` ni `iverilog`.
5. **LaTeX para compilar el informe localmente** (requiere `sudo`): `sudo apt-get install -y texlive-latex-recommended texlive-latex-extra texlive-lang-spanish texlive-pictures texlive-fonts-recommended lmodern latexmk`. Después, `make report` deja `informe/informe.pdf`. Sin esto, el PDF lo compila la integración continua (trabajo `informe`, artefacto `informe`), que hoy no corre (acción 0). El PDF tiene que quedar en el repositorio antes del 1/12.
