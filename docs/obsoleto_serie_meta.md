# Qué queda obsoleto con la serie Meta (17/11)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Relevamiento de solo lectura del informe, el README y el kit de defensa después del cambio de la serie de práctica a `data/practica_meta.csv`. **No se reescribió nada todavía**: se reescribe cuando esté elegida la regla nueva (`docs/pendientes_nicolas.md`).

Categorías: **A** cifra medida en la serie anterior; **B** afirmación sobre el carácter de la serie (reversión a la media, modelo del generador, familias calibradas); **C** justificación de la elección del algoritmo (`max_media`, el fondo que vota, el protocolo y las semillas reservadas); **D** hardware, ciclos, área y verificación de los cores, que no dependen de la serie y siguen valiendo; **E** pregunta del banco cuya respuesta cambia.

## 0. Antes que nada

`make report` sigue leyendo la serie anterior: `tools/report.py:124`, `:270` y `:336`, `Makefile:42` (`SERIE ?=`) y `Makefile:186-187` (`tabla-3-1`) tienen `tb/practica.csv`. Mientras no apunten a la serie nueva, cada macro del informe se regenera con las cifras viejas. `tb/practica.csv` sigue siendo la serie sintética anterior (el testbench oficial la lee de ahí: para correrlo con la serie Meta hay que copiarla a esa ruta, como se hizo en `docs/mediciones/meta/oficial.txt`).

## 1. Informe (`informe/informe.tex`)

- **3.1, casi entero.** Líneas 46 (B: "la serie revierte", VR y autocorrelación en macros; "seguir la tendencia pierde"), 48-54 (C: definición y justificación de `max_media`, familias calibradas), 57 (C: el fondo), 62 y 64 (C), 68 (C: comparación con la regla base), 72 y tabla `t31` (A, generada), 75 (A, macros: 25 973, 6 497, bloques), 77 (A en prosa y C: semilla reservada, remuestreos, familias), 81 y tabla `t31bloques` (A, generada).
- **3.2.** Solo la línea 138 depende de la serie (equivalencia "en la serie de práctica completa"; sigue valiendo como verificación y hay que agregar la Meta). El resto es C solo si cambia `trade.s` (líneas 94-134).
- **3.3.** Las cifras no dependen de la serie, pero el kernel es `max_media` (C: líneas 164, 171, 204). La línea 231 es prosa falsa con la serie nueva: dice que el fondo "empata a 0,1 ms y pierde a 1 ms y 10 ms", y en la Meta los dos dan 9 722 a los tres períodos. Las líneas 6-8 dicen que ninguna cifra se escribe a mano, pero 64, 77 y 231 son prosa.
- **D, siguen valiendo:** `t32` (41 y 44 ciclos; la Meta da los mismos 44 y 443), `t32hilos`, las tablas de 3.3 (perfil, Amdahl, variantes, escalera, roofline, ASIC), celdas, MHz, PLL, duplicador.

## 2. README

- `:17` y `:18` (C): R0 descrito como `max_media` de reversión y R1 como tres gestores que votan.
- `:30` (B): llama serie de práctica a `tb/practica.csv`.
- `:85-87` (A): los comandos de la referencia usan `tb/practica.csv`.
- `:123` (B y C): reversión, razón de varianza 0,77, protocolo con familias calibradas. `:125` (A): 25 973 contra 6 497. `:126` (C).
- `:153-159`, `:179`, `:185` (C): el fondo, sus constantes, 56 operaciones contra 8, `retune` con el protocolo viejo.
- **D:** líneas 75, 131, 137, 143, 149, 161, 167 y 173.

## 3. Kit de defensa (`docs/defensa/`)

- **`preguntas.md`, respuestas que cambian (E):** 3, 4, 5, 11, 12, 14, 15, 18 a 32, 34, 97, 98, 99, 104, 105, 107, 145, 154 y 156. La 26 ("¿y si la serie oculta sale de otro generador?") ya tiene respuesta: son acciones reales. La 104 (26 070, 25 031 y 26 388) y la 156 (`zscore` con 40 957; en la Meta da 7 340) tienen cifras falsas ahora. Siguen valiendo la 2, 6 a 10, 33, 35 a 96, 136, 138 a 144 y 146 a 155 (las de hardware y verificación; C solo si cambia `trade.s`).
- **`pruebas_practica.md`:** las preguntas 22, 23, 145, 156, 15, 18, 11, 14 y 104 aparecen en las tres pruebas; hay que reemplazarlas.
- **`guiones.md`:** `:9`, `:11`, `:21`, `:23`, `:25`, `:39` y `:47` (B y C). `:21` además contradice a `algoritmo.md:18` (3 853 contra 5 566).
- **`cifras.md`:** las tablas "Patrimonio" (`:68-77`) y "Serie de práctica" (`:79-86`) enteras (A y B); `:55-56` y `:99` (C).
- **Documentos de estudio:** `algoritmo.md` casi entero; `fondo.md` (`:11`, `:13-31`, `:93`, `:95`, `:137-139`); `resumen.md` (`:9`, `:15`, `:19`, `:27`, `:47`); `guia_vicente.md` (`:9-10`, `:17-18`, `:25-36`, `:51`); `guia_nicolas.md:42`; `guia_santiago.md:42`; `plan_estudio.md` (`:29`, `:42`, cifras para memorizar); `diagramas.md` (`:96-118`, `:130`); `extension.md:66` (k = 5 justificado por alfa = 1/32).
- **D:** la verificación de los cores (`verificacion.md`, `barrel.md`, `espino_base.md`) se hizo con la serie anterior y sus familias: sigue valiendo; conviene agregar la corrida con la Meta.

## 4. Documentos fuente también obsoletos (sin detalle por línea)

`docs/algoritmo.md` (unas 53 menciones), `docs/protocolo.md` (29), `docs/zscore.md` (28), `docs/fondo.md` (secciones 6, 7 y 10), `docs/decisiones.md` (T20, T27, T50, T51, T129 en adelante), `docs/trade_s.md` (`:25`, `:36` con el rango de precios 72 a 190, `:148-150`, `:214`), `docs/generador_b.md`, `docs/codiseno.md:160`, `docs/contingencia.md` y `docs/arbol_decision.md` (umbrales de `retune`), las mediciones del algoritmo en `docs/mediciones/` (`tabla_3_1.txt`, `protocolo_*`, `generador_*`, `zscore/*`, `fondo/r1/equiv.txt`) y el código calibrado a la serie anterior (`ref/series.py`, `ref/generador.py`, `ref/hallazgos.py`, `tools/retune.py`).

## 5. Orden sugerido para reescribir

1. Que `make report` lea la serie nueva (sección 0) y regenerar `cifras.tex`, `t31` y `t31bloques`.
2. La prosa de 3.1 en el informe (líneas 46, 54 y 77) y la línea 231.
3. `preguntas.md`, sección 2 (11 a 34), y las 3, 4, 26, 104, 107, 154 y 156; después las pruebas de práctica, las guías y las cifras para memorizar.
4. Lo que se dice en voz alta: `guiones.md`, `cifras.md`, `resumen.md`, el README (`:17`, `:30`, `:123-126`) y `docs/defensa/algoritmo.md`.

Cuenta aproximada: unas 45 cifras de la serie anterior, 22 afirmaciones sobre su carácter, 40 justificaciones del algoritmo y 32 preguntas del banco.
