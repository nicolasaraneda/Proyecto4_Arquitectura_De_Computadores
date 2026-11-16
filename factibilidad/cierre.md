# Cierre del tramo de factibilidad (13/11 al 15/11)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Es la sección "Tramo 6" de `docs/estado.md` tal como quedó en la rama `factibilidad-fondo` al cerrar el tramo (commit `b556e1c`, etiqueta `archivo/factibilidad-fondo`), sin cambios salvo este encabezado y el nivel de los títulos. Se trajo a `main` el 16/11 junto con la carpeta, porque el informe, la defensa y varios documentos citan sus cifras (decisión T125). Lo que dice sobre el estado de `main`, las decisiones pendientes y lo que falta es del 15/11: lo que se decidió después está en `docs/decisiones.md` desde T50.

En el momento del cierre ninguna pieza del tramo estaba en `main`. El detalle de cada pieza está en `factibilidad/`, con el índice en `factibilidad/README.md`. El calendario se corrió una semana (T44): maestra real el 26/11, hardware congelado el 25/11 en la noche, entrega y competencia el 1/12.

Se evaluó un diseño integrado más radical que el actual: un Espino multihilo que corre varias estrategias a la vez (un fondo), aprende en vivo y se respalda por reconfiguración. Son prototipos mínimos y mediciones. **Queda una decisión de Nicolás pendiente, al final de esta sección.**

## Qué quedó hecho

- **A. Espino barrel** (`factibilidad/a_barrel/`). Cuatro hilos por un pipeline uniforme de 4 etapas, con los contextos en las BRAM del banco de registros, sin adelantamiento ni burbujas. Con su copia del SoC, que el testbench oficial compila sin modificar.
- **B. Un gestor por hilo** (`factibilidad/b_fondo_hilos/`). Programa en assembly con los cuatro hilos: un supervisor que lee el precio, lleva la contabilidad, reparte y escribe `DECISION`, y tres gestores en papel. Comparado byte a byte contra su referencia en C.
- **C. Aprendizaje en vivo.** El estudio está en `factibilidad/retorno/r4c_aprendizaje/` (tabla de política y predictor de patrones) y la memoria para la tabla en `factibilidad/i_integrado/`.
- **D. Extensión de la ISA** (`factibilidad/d_isa/` y `factibilidad/i_integrado/`). 17 instrucciones en custom-0 y un periférico multiplicador, con especificación, modelo en Python, testbench por módulo y pruebas formales. Medida sobre el segmentado y sobre el barrel.
- **E. Respaldo por reconfiguración** (`factibilidad/e_warmboot/`). Vigilante con SB_WARMBOOT, archivos de varias imágenes con icemulti y una prueba de placa con dos imágenes.
- **F. Doble frecuencia sin PLL** (`factibilidad/f_doble_frecuencia/`). Duplicador por lógica, con un análisis de timing por flanco y por esquina.
- **G. Edición ASIC** (`factibilidad/g_asic/`). El SoC de `main`, base y segmentado, por el flujo completo del Proyecto 3.
- **Configuraciones integradas** (`factibilidad/i_integrado/`). I1 a I4, con 38 variantes medidas y 7 bitstreams simulados desde el `.asc`.
- **Arnés de retorno y cuatro estudios** (`factibilidad/retorno/`). Evaluador en C a nivel de tick, validado contra `ref/market.py`, el motor, `ref/trader.py` y el binario de la placa en el gemelo. Frontera en dos largos de ronda, tres hipótesis de puntaje, ejecución con contabilidad propia, y el fondo completo contra la mejor estrategia sola.
- **Tres auditorías independientes** (`factibilidad/retorno/auditoria/`, `factibilidad/retorno/auditoria_r34/` y `factibilidad/auditoria_hw/`), con evaluadores y listas de fuentes escritos aparte.
- Decisiones T44 a T49.

## Qué se midió

Por pieza. Las frecuencias son la mínima, la mediana y la máxima de 10 semillas de nextpnr.

| Pieza | Celdas y BRAM | Fmax (MHz) y semillas que cierran a 25 MHz | Qué habría que sacrificar para que quepa | Días de trabajo | Reglas del enunciado | Corte |
|-------|---------------|--------------------------------------------|------------------------------------------|-----------------|----------------------|-------|
| A. Barrel de 4 hilos, SoC completo | 934 y 12. Libres 346 y 4 | 52,7, 55,5 y 57,1. 10 de 10 | Nada | 7 | Cumple, con una duda: si un Espino multihilo sigue siendo Espino | Pasa |
| B. Un gestor por hilo, `fondo.s` | No agrega hardware. 251 de 512 palabras | La del barrel | Nada para el fondo mínimo. El fondo completo no cabe en las 512 palabras (unas 620, estimado) | 4,5 el mínimo, 7 el completo | Cumple, con una duda: tres hilos calculan y uno decide | Pasa hardware, no pasa algoritmo |
| C. Tabla de política, 256 x 16 por MMIO | +21 celdas y +1 BRAM sobre el barrel | 53,6, 54,8 y 56,3. 10 de 10 | Nada. Una memoria de 1024 palabras completa no cabe (20 BRAM) | Dentro de I1 | Cumple: la tabla parte de la regla y no de la serie | Pasa hardware, no pasa algoritmo |
| D. Extensión de la ISA sobre el barrel | `emad` +26. `emad`, `devk` y `mulstep` +90: 1025 celdas y 12 BRAM | 48,7, 49,6 y 51,4. 10 de 10 | El conjunto completo ocupa 2505 celdas. Cabe con k fijo en 5, sin multiplicador combinacional ni periférico, y con los carriles dentro de la ALU, donde la mínima baja a 33,7 MHz | 4 | Cumple: aritmética sin estado, la decisión la escribe el programa | Pasa un subconjunto |
| E. Vigilante y warmboot | +4 a +30 celdas y 0 BRAM. Caben 4 imágenes en la flash | 10 de 10 sobre base, segmentado y barrel | Nada en área. Un relevo deja 536 ticks sin decisión a 0,1 ms (53 ms según la hoja de datos) y liquida la posición | 3,5 | En duda: reconfigurar durante una ronda, y la regla del mismo programa | Pasa hardware. Sin probar en la placa |
| F. Doble frecuencia sin PLL | +7 a +9 celdas | A 50 MHz: base 0 de 10. Segmentado 10 de 10 con reloj ideal y 1 de 10 con ciclo de trabajo de 45 a 55 % | No es un problema de área: falta margen de timing | 6 a 7, no se recomienda | Cumple | Descartada |
| G. ASIC, GF180MCU | Dado de 0,359 mm² (base) y 0,304 mm² (segmentado) | Cierra a 42,6 MHz en la esquina lenta. DRC, LVS y antenas en 0 a 25 MHz | No aplica | 4,5 a 5 | Fuera de la competencia | Base lista |

Configuraciones integradas (`make -C factibilidad/i_integrado recursos`). Todas dan 4/4 en el testbench oficial sin modificar, con decisiones idénticas al Espino base.

| Configuración | Qué lleva | Celdas | Libres | BRAM | Fmax mínima, mediana y máxima (MHz) | Cierran | Respuesta, peor caso | Días de persona |
|---------------|-----------|--------|--------|------|-------------------------------------|---------|----------------------|-----------------|
| I4 base | Lo que corre hoy (`competencia_v1.bin`) | 1083 | 197 | 12 | 42,4, 43,7 y 45,1 | 10 de 10 | 44 ciclos | 0,25 |
| I4 segmentado | Pipeline de 3 etapas, ya en `main` | 994 | 286 | 12 | 51,1, 53,5 y 54,5 | 10 de 10 | 26 | 0,25 |
| I3 conservador | Segmentado, `emad` y vigilante | 1046 | 234 | 12 | 48,0, 52,4 y 53,3 | 10 de 10 | 26 | 7,5 |
| I2 barrel mínimo | Barrel y vigilante, una estrategia en un hilo | 939 | 341 | 12 | 51,0, 53,6 y 56,1 | 10 de 10 | 83 | 9 |
| I1 fondo en un chip | Barrel, `emad`, `devk`, `mulstep`, vigilante y tabla | 1071 | 209 | 13 | 46,8, 48,6 y 50,5 | 10 de 10, y 20 de 20 en la auditoría | 439 con el fondo mínimo | 16,5 a 18,5 |

Otras mediciones de hardware:

- **Barrel.** CPI agregado 1,000 y 25,0 MIPS con el mix de la clase 7, contra 1,350 y 18,5 del segmentado y 2,350 y 10,6 del base. Por hilo son 4,000 y 6,25 MIPS: con un solo hilo con trabajo rinde 0,59 veces el base. Verificación: 8 727 624 instrucciones comparadas una por una contra el Espino base, 21 de 21 mutaciones detectadas, 24 propiedades formales de estructura, y 20 000 ticks idénticos a `ref/trader.py` a los tres períodos.
- **Fondo en assembly.** El supervisor ejecuta 42 instrucciones por tick en promedio y cada gestor 35. Decisiones y estado interno idénticos a la referencia en C en 866 000 ticks. La búsqueda de carreras no encontró ninguna en 337 174 decisiones con retardos y fase al azar.
- **Extensión de la ISA.** Con `devk` y `emad` el tick completo de `trade.s` baja de 34 a 21 ciclos en el segmentado. Amdahl predicho y medido coinciden: 1,308 con `emad` y 1,619 con las dos. La extensión no cambia ninguna decisión.
- **ASIC.** 28,0 mW el base y 26,3 mW el segmentado con actividad real, y 2,80 y 2,63 uJ por decisión en la ronda 3. El shifter completo, que no cabe en la FPGA, agrega 7,7 % y 9,1 % de dado.
- **Warmboot.** Durante el cambio de imagen el pin MISO queda en alta impedancia con pull-up débil: la maestra leería 0xFF, que es mantener. Es lo documentado, no lo medido.

Retorno. Diferencia de puntos esperados contra `max_media`, de un máximo de 2, con la semilla reservada 3, el campo de rivales mixto y 10 grupos. H3a es el torneo lineal en patrimonio y H3b lineal en el puesto.

| Estrategia | 2 000 ticks: H3a y H3b | 20 000 ticks, vista de parada: H3a y H3b | Criterio de corte | Costo |
|------------|------------------------|-------------------------------------------|-------------------|-------|
| Regla base, lo que corre hoy | -0,042 y -0,036 | -0,078 y -0,053 | | 27 instrucciones por tick |
| `max_media` (E = 96) | referencia: 1,50 y 1,46 puntos | 1,72 y 1,70 | Pasa contra la base | Una constante. 0,7 días |
| `ejec:m=8`: `max_media` sin compras residuales | +0,007 y +0,027 | +0,006 y +0,048 | Pasa, en 5 campos y 2 semillas | 38 a 90 instrucciones. 3 días. Condicionada (T48) |
| Fondo completo | +0,000 y +0,011 | -0,001 y +0,014 | No pasa | Unas 540 instrucciones y 620 palabras, estimado. Más de 11,5 días |
| Fondo mínimo con tabla y ejecución (`completo_min`) | +0,007 y +0,027 | -0,005 y +0,020 | No pasa | Unas 350 instrucciones y 395 palabras, estimado |
| Fondo mínimo (`fondo_min`), el que está en assembly | 0,000 y 0,000 | -0,020 y -0,006 | No pasa | Medido: 251 palabras y 440 ciclos |
| Fondo con ancla en comprar y mantener | -0,031 y -0,018 | -0,164 y -0,094 | No pasa | |
| Tabla que aprende, sola | 0,000 y 0,000 | -0,014 y -0,002 | No pasa | |

El fondo completo contra la mejor estrategia sola (`ejec:m=8`): -0,007 y -0,016 a 2 000 ticks, y -0,008 y -0,034 a 20 000. En patrimonio empata a 2 000 ticks (-1 ± 3) y gana cerca de 1 % a 20 000 (+249 ± 26), todo en las familias del modelo (+500) y nada en el remuestreo (-1).

## Hallazgos

1. **El fondo en un chip se puede construir.** Cabe con 209 celdas libres, cierra en 20 de 20 semillas, y el programa de cuatro hilos decide igual que su referencia. El área no era el riesgo.
2. **El fondo no gana puntos.** Tres causas medidas. El desempeño en papel no persiste: el líder de la primera mitad de una ronda es el mejor de la segunda en 35 a 39 % de las series, lo mismo que al azar. Los gestores de reversión están correlacionados entre 0,76 y 0,98 con `max_media`, y el único que diversifica, comprar y mantener, rinde 1 209 menos. Y la comisión fija castiga las órdenes parciales: las órdenes suben de 55 a 76 por ronda.
3. **El aprendizaje en vivo no alcanza.** Ninguna de 229 variantes que aprenden mejora a `max_media`, y el resultado empeora de forma monótona con la tasa de aprendizaje. El predictor de patrones acierta entre 49,7 y 50,3 % del signo. Una ronda no trae información suficiente para saber en qué tipo de serie se está.
4. **La hipótesis de puntaje no cambia la elección.** Con patrimonio, exceso sobre comprar y mantener y torneo en sus dos lecturas conviene `max_media`. Vale +0,04 puntos sobre la regla base a 2 000 ticks y entre +0,05 y +0,07 a 20 000.
5. **Proteger el patrimonio no protege el puntaje.** Guardia, tope de pérdida, bandas anchas y ancla bajan los puntos esperados y también su percentil 5 en las tres rondas, salvo el ancla en rondas cortas (+0,06 de percentil 5 a cambio de 0,03 de media).
6. **Lo que más mueve el puntaje no depende de nosotros.** Según qué traigan los otros grupos, la regla base saca entre 0,87 y 1,67 puntos de 2. Tener una reversión bien hecha vale 0,29 a 0,51 puntos sobre no operar. Afinarla vale 0,04 a 0,10.
7. **Una ronda sola es casi una lotería.** El percentil 5 de los puntos de una ronda de 2 000 ticks es 0,16 a 0,30. Con las tres rondas sube a 0,83 y 0,87.
8. **El límite de 63 acciones cuesta, y casi nada se recupera.** Sin el límite se ganarían 0,036 a 0,073 puntos por ronda, pero casi todo son comisiones de las órdenes de continuación. La demora de entrar en varios ticks no cuesta. Escalones, topes y salidas anticipadas pierden.
9. **Con una sola estrategia el barrel no aporta.** Decide igual que los otros cores y responde en 88 ciclos contra 27 del segmentado.
10. **La extensión de la ISA cuesta menos sobre el barrel que sobre el segmentado** (+90 contra +124 celdas), y no cambia el patrimonio: su valor es la pauta de co-diseño.
11. **El duplicador de reloj es un resultado negativo medido.** nextpnr cierra el segmentado a 50 MHz con un reloj ideal, pero no puede describir el ciclo de trabajo. Con 45 a 55 % el período corto es de 17,7 ns y cierra 1 de 10 semillas.
12. **El generador de programas aleatorios del repositorio cae en un punto fijo** (T49). La verificación del segmentado en `main` cubre menos de lo que dice su conteo.

## Tabla comparativa de diseños integrados

Los puntos son esperados y relativos a `max_media` sola, con el campo mixto. Los días son de una persona y son estimaciones. Hasta el congelamiento del hardware el 25/11 quedan unos 33 días de persona para todo el proyecto.

| Diseño | Hardware | Programa | Puntos esperados | Días | Piezas sin probar en la placa | Qué se pierde |
|--------|----------|----------|------------------|------|-------------------------------|---------------|
| 0. Dejar todo como está | Base | Regla base | -0,04 | 0 | Ninguna | 0,04 puntos y el co-diseño en la competencia |
| 1. Mínimo | Base o segmentado | `max_media` | 0 | 1 | El segmentado | El co-diseño de la extensión queda solo en el informe |
| **2. Recomendación** | **Segmentado con `emad`. Barrel y fondo en la edición de exhibición** | **`max_media`, y `ejec:m=8` si se confirman caja, comisión y reset** | **0 a +0,007** | **4 a 8,5** | **El segmentado y una instrucción** | **El barrel y el fondo no compiten en vivo** |
| 3. Barrel mínimo (I2) | Barrel y vigilante | `max_media` en un hilo | 0 | 9 | Barrel y vigilante | 9 días por un core que con una estrategia responde más lento. No gana nada |
| 4. Fondo en un chip (I1) | Barrel, extensión, vigilante y tabla | Fondo mínimo con tabla y ejecución | +0,007 a 2 000 ticks y -0,005 a 20 000. Contra la opción 2 con `ejec:m=8`: 0,000 y -0,011 | 16,5 a 18,5 | Barrel, extensión y vigilante, juntas | La mitad de los días que quedan, y el margen para una falla de placa |
| 5. Fondo completo sobre I1 | Lo mismo, con más memoria | Fondo completo | -0,007 a -0,034 contra la opción 2 | Más de 20 | Las mismas | Lo anterior, puntos, y no cabe en las 512 palabras sin rediseñar la memoria |

## Recomendación

**Dos ediciones, como dice el principio 2 del proyecto.**

- **Edición de competencia.** Espino segmentado, que ya está en `main`, con `max_media`. Encima, en este orden y solo si cada paso pasa su prueba: la instrucción `emad` como co-diseño visible en el bitstream final (1032 celdas sin vigilante), después de pasar por la maestra el 26/11, y `ejec:m=8` solo si el ayudante confirma caja 10 000, comisión 5 y reset por ronda. El vigilante queda fuera mientras no funcione en la placa y el ayudante no acepte reconfigurar durante una ronda.
- **Edición de exhibición.** I1 "fondo en un chip" con el fondo mínimo, tal como quedó medido, más el duplicador de reloj como resultado negativo y la edición ASIC. Es material para el punto 3.3 del informe y para la defensa, y se puede llevar a la maestra el 26/11 como un bitstream más sin comprometer la competencia.

Razones:

1. El criterio de corte que se fijó antes de medir descarta al fondo, y descarta al barrel con él: con una estrategia el barrel no aporta.
2. El hardware no cambia el patrimonio. Todas las configuraciones deciden igual con el mismo programa, así que el hardware de competencia se elige por riesgo y por lo que muestra.
3. La recomendación usa entre 4 y 8,5 de los 33 días de persona. Deja tiempo para lo que hoy está en cero: verificación formal, matriz de estrés, kit de contingencia, informe y defensa.
4. No hace falta decidir hoy qué corre el 1/12. El 26/11 se puede llevar una escalera de bitstreams, del más seguro al más ambicioso, y competir con el más ambicioso que haya pasado.

## Decisión pendiente de Nicolás

1. **Qué diseño integrado se construye**: la recomendación (opción 2) o alguna de las otras de la tabla.
2. **Si `max_media` reemplaza a la regla base** en `sw/trade.s` y `ref/trader.py`. Es independiente de lo anterior y es el único cambio con retorno medido.
3. **Si el commit del calendario (T44) pasa a `main`** por separado.

## Qué falta

- **Nada se probó en la placa.** Hay tres pruebas listas, con los pasos en el README de cada carpeta: `factibilidad/e_warmboot/wb_demo_multi.bin` (dos imágenes, "A" y "b", y medición del tiempo de reconfiguración), `factibilidad/a_barrel/build/bitstream/barrel_cooperacion.bin` (debe mostrar 60 y los cuatro LED) y `factibilidad/f_doble_frecuencia/placa/placa_x2.bin` (opcional).
- **Preguntas al ayudante**, en orden de impacto: cómo se calcula el puntaje (lineal en patrimonio o en el puesto, por ronda o sobre las tres), cuántos ticks dura cada ronda, si caja 10 000 y comisión 5 son definitivas y si la placa se reinicia antes de cada ronda, si un Espino multihilo con instrucciones en custom-0 sigue siendo Espino, si se puede reconfigurar durante una ronda y qué lee la maestra con MISO suelto, y cuántos grupos compiten.
- **El gemelo digital no modela el barrel ni la extensión.** El protocolo de series no puede correr esos binarios.
- **Seis módulos de I1 no tienen un testbench que los instancie solos.** Se prueban a nivel del SoC.
- **Las cifras de las estrategias sin assembly son estimaciones**: instrucciones por tick, palabras y días.
- **Toda la evidencia de retorno sale de la serie de práctica** o del modelo ajustado a ella. A 20 000 ticks las cifras son de orden de magnitud.
- **`make paralelo-largo` del segmentado** hay que repetirlo con el generador corregido (T49).
- **Consumo real de la Go Board**, para comparar con los 28 y 26 mW del ASIC, si se consigue un medidor.

## Qué conviene atacar después y por qué

Suponiendo la recomendación. Si la decisión es otra, cambia el punto 4.

1. **`max_media` en `sw/trade.s` y en `ref/trader.py`, con equivalencia y bitstream nuevo.** Es una constante, 0,7 días, y es lo único medido que suma puntos: +0,04.
2. **Repetir la verificación del segmentado con el generador corregido.** Medio día. Es el core recomendado para la competencia y hoy su cobertura es menor que la informada.
3. **Preguntar al ayudante esta semana.** Las respuestas sobre caja, comisión y reset deciden si entra `ejec:m=8`, y las del puntaje y el largo de la ronda dicen cuánto vale cada cosa.
4. **Integrar `emad` en `rtl/` sobre el segmentado**: ensamblador, gemelo, equivalencia y verificación. 3 a 4 días. Tiene que estar antes del 25/11 para ir a la maestra.
5. **Frente E.** Checklist del 26/11 con la escalera de bitstreams, matriz de estrés y cambio de programa con `icebram`. No se ha empezado y es lo que protege el día de la competencia.
6. **Frentes D y F.** Propiedades formales del esclavo SPI, informe y kit de defensa. La factibilidad ya dejó material: los resultados negativos del fondo, del aprendizaje y del duplicador de reloj responden varias de las preguntas incómodas.

