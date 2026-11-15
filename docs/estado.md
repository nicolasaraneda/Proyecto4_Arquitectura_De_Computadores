# Estado del proyecto

Se actualiza al cerrar cada tramo de trabajo. La versión anterior queda en el historial de git.

## Tramo 6: factibilidad del fondo de estrategias en un chip (13/11 al 15/11)

Rama `factibilidad-fondo`. **Nada de este tramo está en `main`.** El detalle de cada pieza está en `factibilidad/`, con el índice en `factibilidad/README.md`. El calendario se corrió una semana (T44): maestra real el 26/11, hardware congelado el 25/11 en la noche, entrega y competencia el 1/12.

Se evaluó un diseño integrado más radical que el actual: un Espino multihilo que corre varias estrategias a la vez (un fondo), aprende en vivo y se respalda por reconfiguración. Son prototipos mínimos y mediciones. **Queda una decisión de Nicolás pendiente, al final de esta sección.**

### Qué quedó hecho

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

### Qué se midió

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

### Hallazgos

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

### Tabla comparativa de diseños integrados

Los puntos son esperados y relativos a `max_media` sola, con el campo mixto. Los días son de una persona y son estimaciones. Hasta el congelamiento del hardware el 25/11 quedan unos 33 días de persona para todo el proyecto.

| Diseño | Hardware | Programa | Puntos esperados | Días | Piezas sin probar en la placa | Qué se pierde |
|--------|----------|----------|------------------|------|-------------------------------|---------------|
| 0. Dejar todo como está | Base | Regla base | -0,04 | 0 | Ninguna | 0,04 puntos y el co-diseño en la competencia |
| 1. Mínimo | Base o segmentado | `max_media` | 0 | 1 | El segmentado | El co-diseño de la extensión queda solo en el informe |
| **2. Recomendación** | **Segmentado con `emad`. Barrel y fondo en la edición de exhibición** | **`max_media`, y `ejec:m=8` si se confirman caja, comisión y reset** | **0 a +0,007** | **4 a 8,5** | **El segmentado y una instrucción** | **El barrel y el fondo no compiten en vivo** |
| 3. Barrel mínimo (I2) | Barrel y vigilante | `max_media` en un hilo | 0 | 9 | Barrel y vigilante | 9 días por un core que con una estrategia responde más lento. No gana nada |
| 4. Fondo en un chip (I1) | Barrel, extensión, vigilante y tabla | Fondo mínimo con tabla y ejecución | +0,007 a 2 000 ticks y -0,005 a 20 000. Contra la opción 2 con `ejec:m=8`: 0,000 y -0,011 | 16,5 a 18,5 | Barrel, extensión y vigilante, juntas | La mitad de los días que quedan, y el margen para una falla de placa |
| 5. Fondo completo sobre I1 | Lo mismo, con más memoria | Fondo completo | -0,007 a -0,034 contra la opción 2 | Más de 20 | Las mismas | Lo anterior, puntos, y no cabe en las 512 palabras sin rediseñar la memoria |

### Recomendación

**Dos ediciones, como dice el principio 2 del proyecto.**

- **Edición de competencia.** Espino segmentado, que ya está en `main`, con `max_media`. Encima, en este orden y solo si cada paso pasa su prueba: la instrucción `emad` como co-diseño visible en el bitstream final (1032 celdas sin vigilante), después de pasar por la maestra el 26/11, y `ejec:m=8` solo si el ayudante confirma caja 10 000, comisión 5 y reset por ronda. El vigilante queda fuera mientras no funcione en la placa y el ayudante no acepte reconfigurar durante una ronda.
- **Edición de exhibición.** I1 "fondo en un chip" con el fondo mínimo, tal como quedó medido, más el duplicador de reloj como resultado negativo y la edición ASIC. Es material para el punto 3.3 del informe y para la defensa, y se puede llevar a la maestra el 26/11 como un bitstream más sin comprometer la competencia.

Razones:

1. El criterio de corte que se fijó antes de medir descarta al fondo, y descarta al barrel con él: con una estrategia el barrel no aporta.
2. El hardware no cambia el patrimonio. Todas las configuraciones deciden igual con el mismo programa, así que el hardware de competencia se elige por riesgo y por lo que muestra.
3. La recomendación usa entre 4 y 8,5 de los 33 días de persona. Deja tiempo para lo que hoy está en cero: verificación formal, matriz de estrés, kit de contingencia, informe y defensa.
4. No hace falta decidir hoy qué corre el 1/12. El 26/11 se puede llevar una escalera de bitstreams, del más seguro al más ambicioso, y competir con el más ambicioso que haya pasado.

### Decisión pendiente de Nicolás

1. **Qué diseño integrado se construye**: la recomendación (opción 2) o alguna de las otras de la tabla.
2. **Si `max_media` reemplaza a la regla base** en `sw/trade.s` y `ref/trader.py`. Es independiente de lo anterior y es el único cambio con retorno medido.
3. **Si el commit del calendario (T44) pasa a `main`** por separado.

### Qué falta

- **Nada se probó en la placa.** Hay tres pruebas listas, con los pasos en el README de cada carpeta: `factibilidad/e_warmboot/wb_demo_multi.bin` (dos imágenes, "A" y "b", y medición del tiempo de reconfiguración), `factibilidad/a_barrel/build/bitstream/barrel_cooperacion.bin` (debe mostrar 60 y los cuatro LED) y `factibilidad/f_doble_frecuencia/placa/placa_x2.bin` (opcional).
- **Preguntas al ayudante**, en orden de impacto: cómo se calcula el puntaje (lineal en patrimonio o en el puesto, por ronda o sobre las tres), cuántos ticks dura cada ronda, si caja 10 000 y comisión 5 son definitivas y si la placa se reinicia antes de cada ronda, si un Espino multihilo con instrucciones en custom-0 sigue siendo Espino, si se puede reconfigurar durante una ronda y qué lee la maestra con MISO suelto, y cuántos grupos compiten.
- **El gemelo digital no modela el barrel ni la extensión.** El protocolo de series no puede correr esos binarios.
- **Seis módulos de I1 no tienen un testbench que los instancie solos.** Se prueban a nivel del SoC.
- **Las cifras de las estrategias sin assembly son estimaciones**: instrucciones por tick, palabras y días.
- **Toda la evidencia de retorno sale de la serie de práctica** o del modelo ajustado a ella. A 20 000 ticks las cifras son de orden de magnitud.
- **`make paralelo-largo` del segmentado** hay que repetirlo con el generador corregido (T49).
- **Consumo real de la Go Board**, para comparar con los 28 y 26 mW del ASIC, si se consigue un medidor.

### Qué conviene atacar después y por qué

Suponiendo la recomendación. Si la decisión es otra, cambia el punto 4.

1. **`max_media` en `sw/trade.s` y en `ref/trader.py`, con equivalencia y bitstream nuevo.** Es una constante, 0,7 días, y es lo único medido que suma puntos: +0,04.
2. **Repetir la verificación del segmentado con el generador corregido.** Medio día. Es el core recomendado para la competencia y hoy su cobertura es menor que la informada.
3. **Preguntar al ayudante esta semana.** Las respuestas sobre caja, comisión y reset deciden si entra `ejec:m=8`, y las del puntaje y el largo de la ronda dicen cuánto vale cada cosa.
4. **Integrar `emad` en `rtl/` sobre el segmentado**: ensamblador, gemelo, equivalencia y verificación. 3 a 4 días. Tiene que estar antes del 25/11 para ir a la maestra.
5. **Frente E.** Checklist del 26/11 con la escalera de bitstreams, matriz de estrés y cambio de programa con `icebram`. No se ha empezado y es lo que protege el día de la competencia.
6. **Frentes D y F.** Propiedades formales del esclavo SPI, informe y kit de defensa. La factibilidad ya dejó material: los resultados negativos del fondo, del aprendizaje y del duplicador de reloj responden varias de las preguntas incómodas.

## Tramos 4 y 5: integración continua y frente C, producto 2x2 (13/11)

Los frentes A (algoritmo) y B (Espino segmentado) se trabajan en paralelo, cada uno en su rama. Esta sección cubre lo que se hizo aparte de ellos.

### Qué quedó hecho

- **Integración continua más corta** (T22). Los 20 000 ticks con Icarus salieron del push. Los reemplazan el gemelo digital a los tres períodos (`make equiv-gemelo-20k`, `tools/equiv_gemelo.sh`) y Verilator sobre el RTL. La corrida con Icarus queda como ejecución manual: `make equiv-r3`, o `gh workflow run CI -f icarus_completo=true`.
- **Producto 2x2 en punto fijo, solo diseño y costo** (`docs/producto_2x2.md`, T23 y T24). Especificación de la instrucción propuesta `kal2`, modelo de referencia (`ref/mv2x2.py`), generador de la versión de coeficientes fijos (`tools/gen_mv2x2.py`), versión con multiplicadores reales (`rtl/exhibicion/mv2x2_mult.v`), testbench (`tb/tb_mv2x2.sv`) y script de costo (`tools/costo_mv2x2.py`). No está en el SoC ni en el ensamblador.

### Qué se midió

- La integración continua pasó de 32 a 14 minutos. La equivalencia por push demora 2 minutos 19 segundos en local.
- Producto 2x2 (`make costo-mv2x2`, salida en `docs/mediciones/mv2x2_costo.txt`), con coeficientes de ejemplo:

| Versión | FPGA, módulo suelto | FPGA, integrada en el SoC base | GF180, solo síntesis |
|---------|---------------------|--------------------------------|----------------------|
| Coeficientes fijos, forma factorizada | 160 a 396 LUT según la precisión | agrega 217 a 368 celdas: no cabe (1291 de 1280 la más barata) | 8 000 a 20 000 um² |
| Coeficientes fijos, con los coeficientes calibrados del frente A | 251 LUT | agrega 328 celdas: no cabe (1402 de 1280) | 14 776 um² |
| Coeficientes fijos, forma directa | 324 a 427 LUT | | 30 000 um² |
| Multiplicadores reales | 1645 LUT (8 bits) y 3094 LUT (14 bits): más que la FPGA | | 67 000 a 130 000 um² |

- Las tres implementaciones coinciden con el modelo en 20 000 vectores por matriz.

### Qué falta

- **Medir las formas de achicarlo** (carriles más angostos, sin saturación, versión secuencial o periférico). Son estimaciones.
- **Equivalencia formal** entre las dos versiones y contra la especificación.
- **La integración en el core se hizo solo para contar celdas.** No está verificada como instrucción y el ensamblador no la conoce.
- **Correr `make equiv-r3` a mano** antes de cada etiqueta y cada vez que cambie el RTL del core o del esclavo SPI.

### Qué conviene atacar después y por qué

1. **El producto 2x2 queda en la edición de exhibición.** El estimador de dos estados no gana bajo el protocolo (T30) y el hardware no cabe en la FPGA: agrega 328 celdas y el pipeline deja 286 libres. Si se construye, es para la edición ASIC o como periférico secuencial, y para medir el peldaño de la escalera.
2. **El resto del frente C** (especificación de la extensión en custom-0, soporte en el ensamblador, periférico estimador y la escalera de la clase 7 medida) necesita el kernel definitivo del frente A.

## Tramo 4: frente A, algoritmo (13/11)

Rama `frente-a`. El detalle está en `docs/algoritmo.md`. **`ref/trader.py` y `sw/trade.s` no cambiaron: la regla base sigue siendo el algoritmo de la placa hasta que se elija un candidato.**

### Qué quedó hecho

- **Modelo del generador** (`ref/generador.py`, `ref/calibracion.py`). Nivel que pasea más transitoria AR(1) más redondeo, con dos regímenes de volatilidad y saltos. Ajustado por máxima verosimilitud con el filtro de Kalman y validado contra la serie de práctica.
- **Familias sintéticas calibradas en dos grupos** (`ref/series.py`). 4 plausibles y 10 de estrés, todas derivadas del modelo. Se agregaron `modelo`, `modelo_vecino`, `volatil` y `nivel_bajo`.
- **Protocolo** (`ref/protocolo.py`). Grupos, diferencia pareada con error estándar, candidatos por nombre (`cand:...`, `trader:...`) y semilla reservada.
- **Filtro de Kalman y política óptima** (`ref/politica_optima.py`). Ganancias en estado estacionario, matriz 2x2 en punto fijo y programación dinámica con comisión, desfase de un tick y 63 acciones por orden.
- **Familia paramétrica de estrategias** (`ref/candidatos.py`) y **motor en C** (`ref/motor/motor.c`, `ref/motor.py`), con pruebas de que coinciden (`make test-candidatos`, en la integración continua).
- **Exploración por ideas** (`ref/explorar.py`): bandas, estimadores, bandas escaladas con la volatilidad, saltos, cortes, guardia, tope, tamaño de órdenes, asimetría y potencia de una guardia estadística.
- **Ideas que aprenden en vivo** (`ref/experimentos.py`): población de traders, adaptación con prior fuerte y perceptrón, con control de rotación.
- **Guardia de régimen y tope de pérdida**, sin multiplicaciones.
- **Candidatos sobre la frontera** (`ref/frontera.py`), evaluados con una semilla que no se usó para elegir nada.
- Decisiones T25 a T31 en `docs/decisiones.md`.

### Qué se midió

Generador (`make generador`):

| Medición | Valor |
|----------|-------|
| Paso del nivel y de la transitoria, régimen tranquilo | 0,39 y 0,33 por tick |
| Vida media de la transitoria | 17,5 ticks |
| Régimen ruidoso | 14 % del tiempo, 2,98 veces más volatilidad |
| Saltos | 5 en 20 000 ticks, permanentes |
| Mejora de la verosimilitud por incluir la reversión | 10,2 en 20 000 ticks, 1 por ronda |
| Razón de varianza a 100 ticks: medida, sin redondeo, paseo redondeado | 0,53, 0,67 y 0,77 |

Regla base con las familias calibradas (`make protocolo`): plausibles 10 955 de media y 8 553 de percentil 5. Estrés: `tendencia` 9 410 y 5 777, `cambio_de_caracter` 9 043 y 2 592, `paseo` 9 927 y 7 866.

Política óptima (`make politica`): 8,4 % por ronda como techo del modelo. La regla base saca 5,2 % en el modelo. Las bandas óptimas del modelo, probadas en el remuestreo, dan 10 119 contra 10 813 de la regla base.

Candidatos con la semilla reservada (`make frontera`), diferencia contra la regla base con su error estándar:

| Candidato | Bloques: media, peor | Remuestreo: media, dif., p5 | Plausibles: media, dif., p5 | Estrés: p5 |
|-----------|----------------------|-----------------------------|------------------------------|------------|
| `prudente` (E=192, X=-32) | 10 712, 10 000 | 10 639, -115 ± 14, 9 308 | 10 619, -334 ± 19, 9 048 | 6 986 |
| `base` (E=128, X=0) | 11 069, 9 720 | 10 754, 8 958 | 10 954, 8 741 | 5 615 |
| `max_media` (E=96, X=0) | 11 043, 9 620 | 10 833, +79 ± 11, 8 788 | 11 103, +150 ± 15, 8 622 | 5 071 |
| `guardia` (E=96 con saltos y guardia) | 11 018, 9 024 | 10 735, -20 ± 14, 8 881 | 10 893, -60 ± 15, 8 434 | 6 658 |
| `guardia_tope` (además tope de pérdida) | 11 018, 9 024 | 10 716, -38 ± 15, 8 833 | 10 714, -239 ± 32, 8 052 | 6 828 |

Guardia y tope: en los 10 bloques de práctica no se activan nunca. En los remuestreos la guardia pausa en el 2,3 % de las series y el tope salta en el 1,7 %. La guardia sube el percentil 5 de `tendencia` de 4 631 a 6 375 y el de `cambio_de_caracter` de 2 136 a 5 692. El tope deja el peor caso de esas familias sobre 5 200.

El binario contra la referencia con las series nuevas (`make equiv-gemelo`): 3810 series a los tres períodos, 22 860 000 ticks, cero diferencias.

### Hallazgos

1. **La mitad de la reversión aparente es redondeo** y no se puede operar, porque la orden se ejecuta un tick después.
2. **La señal es débil y el techo está cerca.** No hay una mejora grande escondida: lo que queda sobre la regla base es del orden de 1 a 3 puntos de media.
3. **El estimador casi no importa.** Media exponencial, suma móvil y Kalman de dos estados rinden lo mismo con bandas equivalentes. El filtro óptimo baja la incertidumbre de la transitoria de 1,19 a 1,11.
4. **Lo que mueve el resultado es cuánto se opera.** Bandas más angostas suben la media en el modelo y bajan el percentil 5 en todos lados.
5. **Todo corte de pérdidas cuesta media**, porque en una serie que revierte se vende en el fondo.
6. **No se puede detectar en vivo si la serie revierte.** La guardia mide si las entradas vuelven a la media.
7. **Población, adaptación en vivo y perceptrón no ganan** aun con control de rotación.
8. **Ningún candidato reemplaza formalmente a la regla base** con las tres condiciones del protocolo. `max_media` falla por 26 puntos en la media de los bloques (el error es 238) y por las familias de estrés.

### Qué falta

- **Elegir el candidato.** Es decisión de Nicolás. La recomendación con el perfil de máximo patrimonio esperado es `max_media`, y `guardia` si se le da más de 20 % de probabilidad a una serie con tendencia.
- **Escribir el candidato elegido en `sw/trade.s`** con su equivalencia. `max_media` es cambiar una constante. `guardia` son unas 70 instrucciones (estimado).
- **Niveles por presupuesto.** No se hizo: ningún modelo más pesado ganó, así que no hay nada que correr con el tiempo que sobra en las rondas 1 y 2.
- **Rondas largas.** La guardia pausa 1000 ticks y el tope apaga hasta el final. Si una ronda dura mucho más que 2000 ticks hay que rearmar el tope.
- **Tabla del punto 3.1 con el algoritmo final**, cuando se elija.

### Qué conviene atacar después y por qué

1. **Decidir entre `max_media` y `guardia`** y llevarlo a `trade.s` antes del 18/11, para que llegue a la maestra.
2. **Preguntar al ayudante si las series ocultas salen del mismo generador y cuánto dura una ronda.** Las dos respuestas cambian la elección: con el mismo generador gana `max_media`, con rondas largas hay que rearmar el tope.
3. **Frente C.** El producto de matriz 2x2 ya tiene sus coeficientes (`docs/algoritmo.md`, sección 4.1). Va a la edición de exhibición.
4. **Frente E.** La matriz de estrés puede usar el motor y las familias calibradas tal como están.

## Tramo 5: frente B, Espino segmentado (13/11)

### Qué quedó hecho

- **Pipeline de 3 etapas en la FPGA** (`docs/espino_segmentado.md`). Es el core con lectura anticipada del Proyecto 3, portado a BRAM: la memoria de instrucciones se lee en el flanco de bajada (`SB_RAM40_4KNR`), el banco de registros lee durante el fetch y adelanta el dato recién escrito. Se elige al compilar con `-DESPINO_SEGMENTADO`. **El core por defecto sigue siendo el Espino base** y `bitstreams/competencia_v1.bin` no se tocó.
- **Los dos caminos de fetch de la sección 15**, construidos y medidos: flanco de bajada sobre BRAM y ROM combinacional de `trade.s` (`-DESPINO_ROM`). Se eligió el primero (T33).
- **Recorte de celdas** medido uno por uno. El único que rinde es el contador de programa de 11 bits.
- **Verificación**: prueba formal de que el base no cambió (`make formal-base`), programas de riesgos del Proyecto 3 (`make riesgos`), ejecución en paralelo de dos SoC con programas aleatorios (`make paralelo`, `make paralelo-largo`), controles negativos por mutación (`make mutaciones`), gemelo ciclo a ciclo (`make cosim-seg`) y equivalencia con la referencia (`make equiv-seg`, `make equiv-rom`).
- **Gemelo digital** con la tabla de ciclos del segmentado (`--pipeline`), validado contra el RTL.
- **`tb/tb_cpi.sv`** mide las dos variantes: ya no depende de señales que solo existen en el base.
- **Mediciones** en `docs/mediciones/`: `espino_segmentado.txt`, `ticks_segmentado.txt`, `paralelo_largo.txt` y `mutaciones.txt`.
- **Bitstream** `bitstreams/segmentado_v1.bin`, con hash, simulado desde el `.asc`.
- **Integración continua**: `make check-seg` en cada push (cerca de un minuto en local: prueba formal, modelo de costo, riesgos, paralelo, 20 000 ticks y timing en 10 semillas). Lo largo queda como ejecución manual (`segmentado-completo`).
- Decisiones T32 a T43 en `docs/decisiones.md`.

### Qué se midió

Recursos y timing, `nextpnr --hx1k --package vq100 --freq 25`, 10 semillas (`make medir-espino`):

| Variante | Celdas | BRAM | Fmax mínima | Mediana | Máxima | Cierran a 25 MHz |
|----------|--------|------|-------------|---------|--------|------------------|
| Espino base | 1083 | 12 | 42,43 | 43,74 | 45,08 | 10 de 10 |
| Segmentado, fetch en flanco de bajada | 994 | 12 | 51,13 | 53,50 | 54,50 | 10 de 10 |
| Segmentado, ROM combinacional | 1055 | 8 | 50,04 | 53,16 | 55,05 | 10 de 10 |

- **Recortes.** Contador de programa de 32 a 11 bits: recupera 133 celdas en el base (1083 a 950) y 180 en el segmentado (1174 a 994). Decodificación sin uso: dentro del ruido (entre 17 menos y 12 más). Registros de lectura de periféricos: 0, la síntesis ya los recorta.
- **Costo del pipeline.** 91 celdas con el mismo ancho de contador. Con el recorte queda 89 celdas bajo el base y deja 286 libres.
- **Rutas de medio ciclo.** nextpnr las analiza con medio período (comprobado con un diseño de prueba; `icetime` no). Ninguna pasa de 9,8 ns de los 20 disponibles. La ruta crítica es de ciclo completo: 19,6 ns en la peor semilla.

CPI, con los mismos programas (`tb/tb_cpi.sv`, modelo de costo con diferencia de 0 ciclos en todos):

| | Base | Segmentado | Clase 7, estimado |
|-|------|------------|-------------------|
| ALU, store, salto no tomado | 2 | 1 | 1 |
| Load | 3 | 2 | 2 |
| Salto tomado, `jal`, `jalr` | 3 | 2 | 3 |
| CPI con el mix de la clase (`sw/mix_clase7.s`) | 2,350 | 1,350 | 1,5 |
| MIPS con el mix | 10,64 | 18,52 | 16,7 |
| Ppeak | 12,5 MOPS | 25 MOPS | 25 MOPS |
| `trade.s`, respuesta: ciclos promedio y peor caso | 41 y 44 | 22 y 26 | |
| `trade.s`, tick completo: ciclos promedio y peor caso | 63 y 66 | 34 y 38 | |
| `trade.s`, peor caso real barriendo la fase del sondeo | 49 | 27 | |

Verificación:

| Prueba | Resultado |
|--------|-----------|
| `make formal-base` | Etapas IF e ID en modo base equivalentes a las del repositorio del curso: 1376 puntos probados |
| `make riesgos` | `hazard_test` (56 comprobaciones), `hazard_review` (48) y `hazard_cycles` (5): mismas secuencias que el base, trazas idénticas entre BRAM y ROM, e idénticas al gemelo |
| `make paralelo-largo` | 1 300 756 instrucciones comparadas una por una con el contador de 11 bits y 1 600 000 con el de 32, con el banco de registros completo en cada una. Cero diferencias |
| `make mutaciones` | 5 de 5 detectadas, por los programas de riesgos y por la ejecución en paralelo |
| `make cosim-seg` | Gemelo contra RTL: 1 007 124 eventos de `trade.hex`, 846 705 escrituras de programas aleatorios, 20 000 ticks |
| `make equiv-seg`, `make equiv-rom` | 20 000 ticks idénticos a `ref/trader.py` (Verilator a 0,1 ms y 1 ms, Icarus corto, gemelo a los tres períodos) |
| `make equiv-r3` y `make equiv-seg-icarus` | La corrida manual de T22, que toca repetir porque cambió el RTL del core: 20 000 ticks con Icarus, base y segmentado, idénticos a la referencia (patrimonio 26 795) |
| `make sim-bitstream-seg` | El bitstream simulado decide igual que la referencia en 2000 ticks |

### Hallazgos

1. **El pipeline medido supera la estimación de la clase 7.** El salto tomado cuesta 2 ciclos y no 3, porque la instrucción se lee medio ciclo después de que cambia el contador de programa y hay una sola instrucción que anular.
2. **El pipeline sube la frecuencia máxima en vez de bajarla**, de 43,7 a 53,5 MHz de mediana. El multiplexor de adelantamiento entra a la ruta crítica, pero la decodificación sale de ella.
3. **El prototipo anotado (24,4 a 25,6 MHz con el core sin rediseñar) no se reprodujo**: con la decodificación registrada el flanco de bajada cierra con más del doble de margen.
4. **Yosys no reparte en BRAM una memoria con puertos de lectura en flancos distintos.** Con un solo arreglo el diseño ocupaba 47 551 celdas. Hace falta una copia explícita para el fetch (T34).
5. **El gemelo tenía un caso que el base no ejercita**: la instrucción que sigue a un store al esclavo SPI se completa en el ciclo inmediato. Lo encontraron los programas aleatorios (T40).
6. **`make bin` ya no reproduce el hash de `competencia_v1.bin`.** La lógica del base es la misma, pero cambiaron nombres internos y nextpnr ubica distinto (T32).

### Qué falta del frente B

- **Decidir si el segmentado va a la maestra el 19/11** como candidato a la edición de competencia. No cambia el patrimonio con la regla base. Libera 89 celdas y baja la respuesta de 44 a 26 ciclos.
- **Probar `segmentado_v1.bin` en la placa.** Lo hace Nicolás con `iceprog`. El riesgo propio de este diseño es el ciclo de trabajo del reloj: las rutas de medio ciclo toleran entre 25 % y 75 %.
- **riscv-formal.** Evaluado y sin hacer. `docs/espino_segmentado.md` lista lo que falta, cerca de un día (T42).
- **`icebram` con dos copias de la memoria.** El programa está en la memoria de datos y en la del fetch: hay que comprobar que `icebram` reemplaza las dos.
- **Equivalencia formal de `pochoco_ram.v` y `espino_register_file.v` en modo base.** `make formal-base` cubre IF e ID. Esos dos tienen memorias y hoy se cubren con simulación.

### Qué conviene atacar después y por qué

1. **Frente C sobre el segmentado.** Quedan 286 celdas libres y 4 BRAM. La instrucción de paso de media exponencial reemplaza el bloque más caro de `trade.s`, y el producto 2x2 cabe o no según su versión de coeficientes fijos.
2. **Checklist del 19/11 con los dos bitstreams.** Si el segmentado va a competir tiene que pasar ese día. Conviene llevar `competencia_v1.bin` y `segmentado_v1.bin` y probar los dos.
3. **`icebram`** antes del 18/11, porque condiciona el kit de contingencia y ahora hay dos memorias que actualizar.

## Tramo 3: gemelo digital, series de prueba y protocolo de evaluación (13/11)

### Qué quedó hecho

- **Gemelo digital** (`ref/gemelo/gemelo.c`, `ref/gemelo.py`, `docs/gemelo.md`). Simulador en C del SoC con exactitud de ciclo: core por instrucción, esclavo SPI flanco por flanco, reset, maestra y contabilidad. Ejecuta el mismo `trade.hex` del bitstream.
- **Validación contra el RTL** (`make cosim`, `tools/cosim.sh`). `tb/tb_cpi.sv` escribe una traza con el ciclo de cada evento y el gemelo escribe la misma. Se comparan con `cmp`.
- **Generador de programas aleatorios** (`tools/prog_aleatorio.py`). Toda la ISA base, shifts, codificaciones inválidas y accesos a los periféricos. Sirve también para comparar el Espino original con el segmentado.
- **Series de prueba** (`ref/series.py`). Bloques de práctica, remuestreo por bloques de incrementos y 10 familias sintéticas, reproducibles con semilla.
- **Protocolo** (`ref/protocolo.py`, `docs/protocolo.md`). Evaluación, comparación con criterio de aceptación, meseta de parámetros y verificación del binario contra la referencia.
- **Integración continua.** Se agregaron la equivalencia de 20 000 ticks, las pruebas de la referencia, `make cosim` y `make equiv-gemelo`.
- Decisiones T17 a T21 en `docs/decisiones.md`.

### Qué se midió

Gemelo contra RTL (`make cosim`):

| Prueba | Resultado |
|--------|-----------|
| `trade.hex`, timing oficial, 300 ticks | 282 210 eventos idénticos |
| `trade.hex` con otros tres timings de SPI, período y reset | 347 867 eventos idénticos |
| 4 programas aleatorios | 555 966 eventos idénticos |
| Testbench oficial, 20 000 ticks | `decisiones.csv` y resumen idénticos |
| Mediciones por tick, 20 000 ticks | 19 998 ticks idénticos |
| Con y sin atajo del sondeo, a los tres períodos | Idénticos |
| Control negativo (`--borde 0`) | La traza difiere |

Velocidad, 20 000 ticks a 10 ms: Icarus unas 22 horas (estimado), Verilator 22 minutos, gemelo 0,02 segundos.

Regla base bajo el protocolo (`make protocolo`, resultados en `docs/mediciones/protocolo_*.txt`):

| Conjunto | Media | Mediana | Percentil 5 | Peor | Supera a comprar y mantener |
|----------|-------|---------|-------------|------|-----------------------------|
| 10 bloques de práctica | 11 069 | 11 103 | 9 720 | 9 720 | 90 % |
| 1000 remuestreos | 10 772 | 10 703 | 8 914 | 6 520 | 72 % |
| Paseo aleatorio (200) | 9 873 | 9 947 | 7 126 | 2 918 | 42 % |
| Tendencia (200) | 9 543 | 10 015 | 4 530 | 969 | 46 % |
| Cambio de carácter (200) | 13 225 | 13 800 | 3 507 | 389 | 76 % |
| Dos componentes (200) | 25 138 | 23 137 | 16 399 | 13 134 | 100 % |

- **Meseta.** (k, entra, sale) = (5, 4, 0) es el máximo de 45 combinaciones en los bloques (11 069; sus vecinos dan entre 10 446 y 11 043). En 300 remuestreos da 10 816 y el vecino con entra 3 da 10 921. No es un máximo aislado y la diferencia es del tamaño del ruido.
- **Suma móvil de 64 contra la base.** No la reemplaza: pierde en la media de los bloques (10 951 contra 11 069) y en los remuestreos (10 624 contra 10 772), aunque gana en todas las familias sintéticas.
- **El binario contra la referencia** (`make equiv-gemelo`). 3010 series a 0,1 ms, 1 ms y 10 ms: 18 060 000 ticks, cero diferencias, ningún precio sin respuesta.

### Hallazgos

1. **El peor caso del testbench no es el peor caso.** El testbench informa 44 ciclos. Barriendo las 8 fases del lazo de sondeo con el gemelo, la respuesta va de 37 a 44 ciclos en régimen y de 42 a 49 con el primer precio. El peor caso real es 49 ciclos.
2. **El testbench sube SCLK justo en un flanco del reloj.** Icarus y Verilator lo resuelven igual. En la placa la maestra es asíncrona. Las decisiones no dependen de eso (T19).
3. **La regla base no tiene tope de pérdida.** En tendencia a la baja compra y no vende hasta que el precio recupere la media. Peor caso 969 en `tendencia` y 389 en `cambio_de_caracter`.
4. **La ganancia esperada por ronda es del orden de 8 %, con mucha dispersión.** En los remuestreos el patrimonio final va de 6 520 a 15 637 y uno de cada cinco termina bajo 10 000.
5. **El redondeo a enteros fabrica reversión aparente.** Un paseo aleatorio redondeado tiene razón de varianza 0,87 a 10 ticks. Hay que separarlo de la reversión real al identificar el generador.

### Qué falta del tramo 3

- **Las familias sintéticas no estaban calibradas.** Resuelto en el tramo 4: salen del modelo ajustado. Los números de las familias sintéticas de la tabla de arriba son los de antes de calibrar.
- **El criterio de aceptación no tenía error estadístico.** Resuelto en el tramo 4: la comparación entrega la diferencia pareada con su error estándar.
- **El gemelo modela solo el Espino base.** Cuando el core cambie hay que actualizar su tabla de ciclos y repetir `make cosim`.

## Tramo 2: regla base de punta a punta (13/11)

### Qué quedó hecho

- **Ensamblador.** Directiva `.org` y salidas `--vh` y `--rom` del Proyecto 3. 87 tests. `trade.hex` queda relleno a 512 palabras.
- **Referencia.** `ref/market.py` (porte del mercado del testbench) y `ref/trader.py` (regla base con la aritmética de `trade.s`, y modelo de los precios que se pierden en el reset). `make test-ref`: 22 pruebas.
- **`sw/trade.s`, variante solo software.** Regla base sin saltos que dependan del precio. Explicado bloque por bloque en `docs/trade_s.md`.
- **`make equiv`** (`tools/equiv.sh`). Copia parametrizada del testbench contra la referencia, con `cmp`.
- **Mediciones por tick** (`make medir-ticks`, `tb/tb_cpi.sv`).
- **Primer bitstream de competencia** en `bitstreams/competencia_v1.bin`, con hash, y `make sim-bitstream`.
- Decisiones T10 a T16.

### Qué se midió

Testbench oficial sin modificar: **4/4**, peor caso 44 ciclos de 2 262 disponibles, patrimonio 9 617 en los 2000 ticks por defecto.

Equivalencia con la referencia (`decisiones.csv` idéntico byte a byte):

| Corrida | Simulador | Ticks | Patrimonio |
|---------|-----------|-------|------------|
| 0,1 ms | Icarus | 20 000 | 26 795 |
| 0,1 ms | Verilator | 20 000 | 26 795 |
| 1 ms | Verilator | 20 000 | 27 306 |
| 10 ms (`make equiv-largo`) | Verilator | 20 000 | 27 306 |
| 1 ms y 10 ms | Icarus | 200 y 20 | |
| Una serie de cada familia sintética | Verilator | 11 de 2000 | |

El patrimonio no es 27 062 porque en el testbench el programa no ve los primeros precios, que llegan durante el reset (2 a 0,1 ms, 1 a 1 ms y 10 ms). La referencia lo modela (T13).

Tabla del punto 3.1, serie completa viendo todos los precios (`python3 ref/trader.py tb/practica.csv`):

| Estrategia | Patrimonio | Órdenes | Comisiones | Pérdida máxima |
|------------|------------|---------|------------|----------------|
| No operar | 10 000 | 0 | 0 | 0 |
| Comprar y mantener | 6 497 | 1 | 5 | |
| Regla base | 27 062 | 388 | 1 940 | 2 929 |

Mediciones por tick del punto 3.2, iguales en las tres rondas (`docs/mediciones/ticks_software.txt`):

| Ventana | IC promedio | IC peor | Ciclos promedio | Ciclos peor | CPI | Tiempo peor caso |
|---------|-------------|---------|-----------------|-------------|-----|------------------|
| Respuesta (hasta `DECISION`) | 19,5 | 21 | 41 | 44 | 2,10 | 1,76 us |
| Tick completo | 28,5 | 30 | 63 | 66 | 2,21 | 2,64 us |

El trabajo sin la espera son 27 instrucciones y 58 ciclos. La actualización de la media es el bloque más caro: 8 instrucciones y 17 ciclos, el 29 %.

Bitstream `competencia_v1.bin`: 1083 celdas de 1280 (84 %), 12 BRAM, 44,0 MHz. Simulado desde el `.asc`: 2000 ticks idénticos a la referencia.

### Diferencias con lo que teníamos anotado

1. **Costo de la regla base.** Estimábamos unas 30 instrucciones y 70 ciclos por tick. Medido: 28,5 instrucciones y 63 ciclos con la espera, 27 y 58 sin ella.
2. **Entrar no es una sola orden.** Por el límite de 63 acciones, entrar toma 2 órdenes con la caja inicial y hasta 6 cuando el patrimonio crece. La regla base entra 75 veces y ejecuta 388 órdenes.
3. **No hay numpy en el entorno.** Todo `ref/` usa la biblioteca estándar (T21).

Nada de lo encontrado contradice al enunciado ni al testbench.

### Qué falta del tramo 2

- **Probar el bitstream en la placa.** Lo hace Nicolás con `iceprog`. Sin la maestra no hay nada que observar: el programa no usa LEDs ni displays.
- **Reset más corto.** Sigue pendiente medir en la placa el reset mínimo que arranca bien (T3).
- **`icebram`.** `trade.hex` ya tiene el tamaño que necesita, pero no se ha probado el cambio de programa dentro del bitstream.

## Pendientes generales

- **Colaboradores.** Falta el usuario de GitHub de Santiago Muñoz y el de quien deba revisar la entrega.
- **Preguntas al ayudante.** Siguen abiertas las diez. Las que más pesan ahora: si las series ocultas salen del mismo generador, cuántos ticks dura cada ronda, si la maestra usa el timing del testbench y si la placa parte encendida antes del primer precio (define si se pierde alguno).
- **Verificación formal.** `formal/` sigue vacía.

## Qué conviene atacar después y por qué

1. **Frente A, guardia de régimen y tope de pérdida.** Es el hallazgo más caro: sin reversión la regla base puede perder casi todo. El protocolo ya mide exactamente eso, y la guardia tiene que mejorar `tendencia` y `cambio_de_caracter` sin tocar los bloques ni los remuestreos.
2. **Frente A, identificar el generador.** Calibrar `dos_componentes` contra la serie de práctica y separar el efecto del redondeo. Con el modelo se puede calcular la política óptima y se obtienen series fuera de muestra que sí se parecen a la real.
3. **Frente A, límite de 63 acciones.** Entrar en 6 ticks cuesta comisiones y precio. Conviene evaluar entradas escalonadas y si vale la pena operar con menos que todo el patrimonio.
4. **Frente B, Espino segmentado.** La traza de `tb/tb_cpi.sv`, el generador de programas aleatorios y el gemelo ya están listos para la ejecución en paralelo contra el original. Tiene que estar antes del 18/11 para llegar a la maestra.
5. **Frente E, `icebram` y matriz de estrés.** Con el gemelo la matriz de períodos, tiempos de SPI, comisión y caja es cuestión de minutos.

## Tramo 1: repositorio, flujo completo y mediciones de partida (12/11 y 13/11)

### Qué quedó hecho

- Repositorio privado `nicolasaraneda/Proyecto4_Arquitectura_De_Computadores`, con el repositorio base del curso importado sin cambios (etiqueta `base-curso`) y la estructura `rtl/`, `sw/`, `tb/`, `ref/`, `tools/`, `formal/`, `docs/`, `informe/`.
- Los cuatro archivos entregados quedaron en su lugar: `docs/Proyecto_4_arq.pdf`, `tb/tb_proyecto_4.sv`, `tb/practica.csv` y `ref/p4_baseline.py`. Ninguno se modificó.
- Ensamblador `tools/pochoasm.py`: es el del Proyecto 2 con el nombre que pide el testbench. 73 tests pasan.
- `sw/trade.s` trivial (comprar y mantener) y `Makefile` con todo el flujo: ensamblar, testbench oficial, copias parametrizadas del testbench, CPI, síntesis, place and route y bitstream.
- Power-on reset largo traído del Proyecto 2 (`PorBits = 12`).
- Scripts de medición: `tools/medir_base.sh` y `ref/hallazgos.py`.
- Integración continua en GitHub Actions: tests del ensamblador, `trade.hex` al día, testbench oficial, CPI y síntesis hasta el bitstream. La primera corrida en GitHub terminó en verde.
- `main` protegido en GitHub: exige que el chequeo `verificar` de la integración continua haya pasado, y no admite `push --force` ni borrar la rama. El dueño del repositorio puede empujar directo. Los demás integrantes entran por pull request desde una rama.
- `Vcalderone` invitado como colaborador con permiso de escritura.
- `README.md`, `docs/decisiones.md` y `docs/ensamblador.md`.

### Qué se midió

Testbench oficial sin modificar, con el `trade.s` trivial:

| Período | Ticks | Resultado | Peor caso | Presupuesto |
|---------|-------|-----------|-----------|-------------|
| 0,1 ms (por defecto) | 2000 | 4/4 | 18 ciclos | 2 262 |
| 1 ms (copia parametrizada) | 20 | 4/4 | 18 ciclos | 24 762 |
| 10 ms (copia parametrizada) | 5 | 4/4 | 18 ciclos | 249 762 |

Con 2000 ticks a 0,1 ms el patrimonio final es 6 845 con 2 órdenes (comprar y mantener según el testbench: 6 695). El `decisiones.csv` se comparó fila por fila con el mercado de `ref/p4_baseline.py`: cero diferencias en 2000 filas (hecho con el reset original; con el reset largo cambia solo el tick en que aparece la primera orden).

Repositorio base (`make medir-base`, resultado en `docs/mediciones/base.txt`):

| Medición | Valor medido | Valor que teníamos anotado |
|----------|--------------|----------------------------|
| Celdas lógicas | 1065 de 1280 (83 %) | 1080 (84 %) |
| BRAM | 12 de 16 | 12 de 16 |
| Frecuencia máxima, 10 semillas | 42,7 a 47,1 MHz, mediana 44,1 | cerca de 43 MHz |
| Shifter completo | 1491 celdas (116 %), no cabe | 1479 (115 %) |
| PLL en el VQ100 | nextpnr falla: "PLL 'u_pll' couldn't be placed anywhere, no suitable BEL found" | el mismo error |
| CPI | 2 ciclos por instrucción, más 1 por load y 1 por salto tomado. Medido en simulación con tres programas: el modelo coincide con diferencia de 0 ciclos | el mismo modelo, por lectura del RTL |

Diseño actual (repositorio base más reset largo): 1083 celdas, 12 BRAM, 44,0 MHz con la semilla por defecto.

Serie de práctica (`make hallazgos`):

| Hallazgo | Valor medido | Coincide |
|----------|--------------|----------|
| VR(10), VR(50), VR(100) | 0,77, 0,62 y 0,53 | sí |
| Reversión en los 20 bloques de 1000 ticks | VR menor que 1 en 20 de 20, para los tres horizontes | sí |
| Autocorrelación de los cambios | -0,112 en el rezago 1, dentro del ruido desde el rezago 3 | sí |
| Regla base (media exponencial, alfa 1/32, entra 4, sale 0) | 27 062 con 388 órdenes. Bloques: media 11 069, peor 9 720, supera a comprar y mantener en 9 de 10 | sí |
| Suma móvil de 64, entra 4, sale 1 | 24 143. Bloques: media 10 951, peor 10 148 | sí |
| Comprar y mantener | 6 497. Media por bloque 9 746 | sí |
| Seguir tendencia, 336 configuraciones | mediana 5 566, solo 10 de 336 terminan sobre 10 000 | no: teníamos 3 853 |

### Diferencias con lo que teníamos anotado

1. **Versión de Yosys.** La instalada es 0.68+195 (OSS CAD Suite del 2026-09-06), no 0.70. Con ella el repositorio base da 1065 celdas en vez de 1080 y el shifter 1491 en vez de 1479. Las conclusiones no cambian: quedan unas 200 celdas libres y el shifter completo no cabe.
2. **El conteo de celdas tiene ruido.** El mismo diseño dio entre 1063 y 1075 celdas según detalles del flujo que no cambian la lógica. Una diferencia menor que unas 10 celdas no se puede atribuir a un cambio con una sola síntesis (decisión T6).
3. **Barrido de seguir tendencia.** La grilla de 336 configuraciones original no estaba en ningún script. Con la grilla que definimos en `ref/hallazgos.py` la mediana es 5 566 y no 3 853. La conclusión es la misma: seguir tendencia pierde.
4. **Intentos anteriores sin código.** Perceptrón en línea, población de 120 traders y comité por votación no se pudieron reproducir porque su código no está en el repositorio. Hay que rehacerlos en el frente del algoritmo.
5. **Costo de la regla base (unas 30 instrucciones, 70 ciclos).** Sin medir todavía, porque `trade.s` es el trivial.
6. **CPI del enunciado.** La tabla del enunciado supone CPI = 2,35. Los programas medidos dan entre 2,50 y 2,67, porque tienen muchos saltos tomados y loads.
7. **Reset largo y primeros precios.** Con el reset del Proyecto 2, en el testbench el programa no ve los precios de los ticks 0 y 1 a 0,1 ms, ni el del tick 0 a 1 ms y 10 ms (medido). El testbench entrega 4/4 de todas formas. En la competencia no pasa, porque la placa está encendida antes del primer precio (decisión T3).
8. **Puntaje de la competencia.** El enunciado dice que depende del patrimonio final respecto a comprar y mantener y de la posición relativa entre los grupos. Lo teníamos resumido solo como lineal entre el peor y el mejor grupo.

Nada de lo encontrado contradice al enunciado ni al testbench.

### Observaciones para lo que viene

- **La simulación con Icarus es lenta.** 2000 ticks a 0,1 ms demoran 76 segundos. Una ronda de 2000 ticks a 10 ms demoraría cerca de dos horas. Para las rondas 1 y 2 completas hace falta Verilator o el gemelo digital.
- **`trade.hex` no rellena las 512 palabras.** Las palabras que no están en el archivo quedan indefinidas en simulación y en cero en la placa. Un programa que lea memoria sin haberla escrito se comportaría distinto en los dos lados. Conviene que el ensamblador rellene hasta 512 palabras, que además es lo que necesita `icebram`.
- **Posible sobreajuste de la regla base.** En la grilla de 336 configuraciones de reversión, la mediana es 11 204 y el máximo 27 226. La regla base (27 062) está casi en el máximo de la grilla, así que sus parámetros ya están elegidos mirando la serie completa. El protocolo por bloques y con remuestreo tiene que partir de ahí.
- **`tb/tb_cpi.sv` mira señales internas del Espino base.** Cuando el core se segmente hay que actualizar esas rutas o sacar una señal de instrucción completada.

### Qué falta del tramo 1

- **Equivalencia y verificación formal en la integración continua.** Todavía no existen. Se agregan al flujo cuando estén `make equiv` y las pruebas de `formal/`.
- **Colaboradores.** Falta el usuario de GitHub de Santiago Muñoz y el de quien deba revisar la entrega.
- **Definición de Ops/s y roofline vista en clases.** No está en el repositorio. Hace falta la diapositiva para el frente del co-diseño.

### Qué conviene atacar después y por qué

1. **Regla base en `trade.s` con equivalencia exacta (`make equiv`).** Es el entregable del día 2 y la base de todo lo demás: fija la referencia `ref/trader.py`, obliga a resolver el desplazamiento sin shifter y entrega el primer bitstream de competencia.
2. **Gemelo digital o Verilator.** Sin simulación rápida no se pueden correr las rondas de 10 ms ni la matriz de estrés. Destraba los frentes A, D y E.
3. **Relleno de `trade.hex` a 512 palabras y prueba de `icebram`.** Es barato y elimina una diferencia entre simulación y placa.
4. **Preguntas al ayudante.** Sobre todo las que cambian el diseño: si el periférico estimador cumple las reglas, si las series ocultas salen del mismo generador, cuántos ticks dura cada ronda y si la maestra usa el timing del testbench.
