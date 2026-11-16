# Factibilidad: un fondo de estrategias en un chip

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Tramo de factibilidad del Proyecto 4, hecho entre el 13/11 y el 15/11 en la rama `factibilidad-fondo`. Son prototipos mínimos y mediciones. Nada de esta carpeta está integrado en `rtl/`, `sw/`, `ref/` ni en el flujo de `make` de la raíz, y ningún archivo fuera de `factibilidad/` cambió, salvo la documentación.

La pregunta del tramo: si conviene reemplazar el diseño actual (un core, una estrategia) por un diseño integrado más radical, con un Espino multihilo que corre varias estrategias a la vez, aprende en vivo y se respalda por reconfiguración.

La respuesta corta: el hardware se puede construir, cabe y cierra, pero el fondo de estrategias no gana puntos contra la mejor estrategia sola. El detalle, la recomendación y lo que faltaba decidir al cierre están en `cierre.md`.

## Procedencia

Esta carpeta se hizo en la rama `factibilidad-fondo` y se trajo a `main` el 16/11 como archivo, porque el informe, la defensa y varios documentos citan sus cifras (decisión T125). Es la carpeta del commit `b556e1c` (etiqueta `archivo/factibilidad-fondo`) con dos cambios:

- `cierre.md`, que es la sección del tramo en el `docs/estado.md` de la rama.
- Las rutas de la máquina en que se corrió se reemplazaron por variables: `$OSS_CAD_SUITE` para OSS CAD Suite, `$PDK_CIEL` para la carpeta del PDK en los registros del flujo ASIC, y `P3` para el clon del Proyecto 3. Los scripts toman las herramientas del `PATH`. Ninguna cifra cambió.

Sigue sin estar integrada: nada de `rtl/`, `sw/`, `ref/` ni del `Makefile` de la raíz la usa, y la integración continua no la corre. Lo que se integró después (el barrel, la extensión, el vigilante, la tabla y el fondo) se trajo pieza por pieza a `rtl/` y `sw/` desde P1, con sus propias pruebas.

Los scripts de aquí se escribieron contra el repositorio del 15/11 (`rtl/`, `sw/trade.s` y `ref/` de ese día). Para reproducir una cifra tal como se midió, correrlos en una copia de la etiqueta:

```bash
git worktree add ../factibilidad archivo/factibilidad-fondo
cd ../factibilidad && make -C factibilidad/a_barrel todo
```

## Criterios de corte

Los fijó Nicolás antes de medir:

- Una pieza de hardware se descarta de la edición de competencia si no cabe junto al SPI (1280 celdas lógicas y 16 BRAM) o si no cierra a 25 MHz en las 10 semillas de nextpnr.
- Una pieza de algoritmo se descarta si no mejora los puntos esperados del torneo sin empeorar el percentil 5.
- Lo descartado se documenta con sus números y pasa a la edición de exhibición o a la ASIC.

## Piezas

Cada carpeta tiene su `README.md` con el detalle, un `Makefile` que reproduce sus números y una carpeta `mediciones/` con las salidas guardadas.

| Carpeta | Qué es | Resultado | Corte |
|---------|--------|-----------|-------|
| `a_barrel/` | Espino barrel: 4 hilos por un pipeline uniforme de 4 etapas | 934 celdas, 12 BRAM, 52,7 a 57,1 MHz, 10 de 10 semillas. CPI agregado 1,000. Verificado contra el core base con 8,7 millones de instrucciones | Pasa el de hardware |
| `b_fondo_hilos/` | Un gestor por hilo: fondo mínimo en assembly, supervisor y tres gestores en papel | 251 de 512 palabras, respuesta de 440 ciclos de 2262, decisiones idénticas a su referencia en C | Pasa el de hardware, no el de algoritmo |
| `d_isa/` | Extensión de la ISA en custom-0: 17 instrucciones y un periférico multiplicador | Sobre el segmentado: `emad` +37 celdas, `emad`, `devk` y `mulstep` +124. El conjunto completo ocupa 2505 celdas | Pasa un subconjunto |
| `e_warmboot/` | Respaldo por reconfiguración con SB_WARMBOOT e icemulti, y vigilante | Caben 4 imágenes en la flash. Vigilante: 4 a 30 celdas. Cambio de imagen: 53 ms según la hoja de datos | Pasa el de hardware, sin probar en la placa |
| `f_doble_frecuencia/` | Duplicador de reloj por lógica | Con un ciclo de trabajo de 45 a 55 % cierra 1 de 10 semillas | Descartada |
| `g_asic/` | El SoC por el flujo de LibreLane del Proyecto 3 (GF180MCU) | Base y segmentado limpios a 25 MHz. Cierran a 42,6 MHz. 28 y 26 mW | Fuera de la competencia |
| `i_integrado/` | La extensión, el vigilante y la memoria de tabla sobre el barrel, y las configuraciones integradas I1 a I4 | I1 "fondo en un chip": 1071 celdas, 13 BRAM, 46,8 a 50,5 MHz, 10 de 10 | Pasa el de hardware |
| `auditoria_hw/` | Auditoría independiente de `i_integrado/` y `b_fondo_hilos/` | Cifras reproducidas, 20 de 20 semillas, búsqueda de carreras sin hallazgos | |
| `retorno/` | Arnés de evaluación de estrategias y los cuatro estudios de retorno | Ver la sección siguiente | |

## Estudios de retorno

Todos usan el arnés de `retorno/nucleo/`, que evalúa estrategias a nivel de tick con la contabilidad del testbench oficial. No es el gemelo digital: el gemelo simula el SoC ciclo a ciclo y se usó solo para confirmar que `sw/trade.hex` decide igual que la regla base del arnés.

| Carpeta | Estudio | Resultado |
|---------|---------|-----------|
| `retorno/` | 1. Frontera con rondas de 2 000 y de 20 000 ticks | `max_media` (la regla base con E = 96) supera a la base en los dos largos |
| `retorno/` | 2. Tres hipótesis de puntaje y torneo contra rivales | La hipótesis no cambia la elección. El nivel de puntos depende de los rivales: entre 0,87 y 1,67 de 2 |
| `retorno/r3_ejecucion/` | 3. Ejecución que conoce su patrimonio | La regla de entrada y salida actual se mantiene. Suprimir compras residuales vale +0,007 puntos |
| `retorno/r4b_fondo/` | 4. El fondo y el reparto de capital | Ninguna de 90 variantes mejora a `max_media` |
| `retorno/r4c_aprendizaje/` | 4. Tabla de política y predictor de patrones | Ninguna de 249 variantes mejora a `max_media`. El predictor acierta entre 49,7 y 50,3 % |
| `retorno/r4_final/` | 4. El fondo completo contra la mejor estrategia sola, con semilla reservada | El fondo completo pierde entre 0,007 y 0,034 puntos |
| `retorno/auditoria/` y `retorno/auditoria_r34/` | Auditorías independientes del arnés y de los estudios 3 y 4 | Cifras reproducidas con evaluadores escritos aparte. Sin errores de cálculo ni información del futuro |

## Cómo se reproduce

Las herramientas de OSS CAD Suite tienen que estar en el `PATH`. Todo se corre desde la raíz del repositorio.

```bash
make -C factibilidad/a_barrel todo            # barrel: recursos, CPI, oficial, equivalencia
make -C factibilidad/i_integrado todo         # configuraciones integradas, unos 40 minutos
make -C factibilidad/i_integrado rapido       # versión corta, 1 minuto
make -C factibilidad/b_fondo_hilos todo       # fondo en assembly contra su referencia
make -C factibilidad/e_warmboot todo          # vigilante, imágenes y prueba de placa
make -C factibilidad/f_doble_frecuencia todo  # duplicador de reloj
make -C factibilidad/g_asic ayuda             # flujo ASIC (necesita Docker y el PDK)
make -C factibilidad/retorno series todo      # arnés y estudios 1 y 2
make -C factibilidad/retorno/r3_ejecucion todo
make -C factibilidad/retorno/r4b_fondo todo
make -C factibilidad/retorno/r4c_aprendizaje todo
make -C factibilidad/retorno/r4_final todo
make -C factibilidad/retorno/auditoria_r34 todo
make -C factibilidad/auditoria_hw todo
```

`d_isa/` no tiene un objetivo único: sus objetivos están listados en su README (`tb`, `formal`, `costo-suelto`, `costo-integrado`, `medir-ticks`).

Las series de prueba (548 MB), los bitstreams, las corridas del flujo ASIC (11 GB) y los productos de síntesis no se versionan. Cada carpeta dice cómo regenerarlos.

## Qué no cubre este tramo

- Nada se probó en la placa ni con la maestra real.
- Las instrucciones por tick y los días de trabajo de las estrategias que no existen en assembly son estimaciones.
- El gemelo digital no modela el barrel ni la extensión de la ISA.
- Toda la evidencia de retorno sale de la serie de práctica o del modelo ajustado a ella. Las semillas reservadas protegen de elegir por azar, no de que la serie oculta sea distinta.
- A 20 000 ticks las series de prueba chocan con los límites 1 y 255 en el 20 a 40 % de los casos. Las cifras de ese largo son de orden de magnitud.
