# Exploración de ideas sobre la población real de minutos (18/11)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Pedido de Nicolás del 18/11 en la noche: evaluar diez ideas y sus combinaciones sobre la población real (minutos de Alpaca, `docs/cotas.md`, sección 7) y presentar qué regla conviene que compita. El corte del algoritmo es el 22/11. Este documento presenta la decisión y no la toma. La regla de los peldaños no se cambió. La decisión entre banda 40 y banda 60 quedó en pausa: las dos, y las tres bandas por hilo, son la base de comparación.

Código: `ref/cotas/ideas.py` (motor y estrategias), `ref/cotas/ideas_dp.py` (idea 1) y `ref/cotas/explorar_ideas.py` (muestra, filtros, barridos, torneo y tablas). Salidas en `docs/mediciones/exploracion/`. Bitácora: `docs/bitacora/exploracion.md`. Solo Python: no se tocó `rtl/`, `sw/`, `main` ni ningún bitstream.

## 0. Resumen

1. **Ninguna de las diez ideas ni de las combinaciones le gana a la banda 40 fuera de muestra.** Las mejores son la banda 40 con un agregado chico (ideas 8, 9, 4, 10 y 7): quedan entre 5 y 80 de patrimonio medio por debajo, y ninguna queda sobre la banda 40 en ninguna de las dos validaciones. Las finalistas corrieron después en la población completa (1 368 253 ventanas): el orden y los signos son los mismos, con diferencias de 1 a 12 respecto de la muestra. Las ideas que cambian la forma de operar en la fase D pierden más: la grilla y el torneo en sombra entre 270 y 440, la programación dinámica entre 220 y 310, los contadores más de 7 000.
2. **La banda 40 es el óptimo de su vecindad.** Se agregó una idea 12 (banda asimétrica: nivel de compra y de venta por separado, 56 combinaciones, porque en la ronda de Tesla lo que decidió fue el nivel de venta). En los dos ajustes, por años y por empresas, el mejor punto es exactamente compra con 140 o menos y venta con 215 o más, que es la banda 40.
3. **La única decisión con efecto medible es banda 40 contra banda 60.** Fuera de muestra, la banda 40 suma +256 (años) y +319 (empresas) de patrimonio medio por ronda y +0,055 puntos de torneo en las dos separaciones. Es lo mismo que mostró el paso 5 (`docs/estado.md`, tramo 17). En la población completa (sección 5) la diferencia es +257 (ee 244) y +314 (ee 194) en las dos validaciones y +205 (ee 101) en todas las ventanas.
4. **Las ideas de clase A** (las que se calibran solas con la serie recibida o salen de un modelo: 1, 3, 5 y 6) pierden todas. La estructura que explota la regla de los peldaños (los extremos 100 y 255 garantizados por la normalización) no deja otra regularidad que un modelo en vivo pueda aprovechar con estas comisiones.
5. **La ronda de Tesla del 18/11 no la habría ganado ninguna idea salvo copiar al rival.** Allí la fase D empezó en el tick 12 040 y la ronda se decidió por el nivel de venta: banda 60 vendió en 195, banda 40 en 216 y el rival en 220 o más, con cierre en 212. Ninguna variante del final de ronda (idea 8) cierra la diferencia. La más cercana de todas las elegidas fue la idea 10 con caída de 5 (21 177, contra 21 467 del rival), que en la población queda bajo la banda 40.

## 1. Método

**Motor** (`ideas.correr`). La contabilidad oficial de `ref/market.py` (caja 10 000, comisión 5, compra recortada a (caja - 5) / p, venta recortada a las acciones) con la regla de tiempo del testbench: la orden decidida tras ver p(n - 1) se ejecuta a p(n), con 63 acciones como máximo, así que un cambio completo de posición toma 2 o 3 ticks y el motor lo simula así. Cada estrategia recibe en cada tick su propia caja y sus acciones, que el programa puede llevar por su lado: conoce sus órdenes, los precios y las reglas de recorte. Validación (`explorar_ideas.py validar`): la banda 60 da 18 779 en la ronda de Tesla, lo mismo que la maestra; 0 diferencias contra la caché en C en las 3600 ventanas de la muestra (bandas 40 y 60) y contra `trader.correr` con `Cotas` en 40 ventanas. Corre a 0,18 µs por tick, así que la población completa es factible en Python.

**Fases** (las del pedido). A: no se ha visto ni 100 ni 255, en caja. B: se vio 100 y falta 255, todo invertido. C: se vio 255 y falta 100, en caja. D: se vieron los dos. Cada idea actúa en D y respeta A, B y C, salvo la idea 9, que cambia A.

**Muestra.** Estratificada por empresa y año de inicio: 240 ventanas de 20 000 minutos por cada una de las 15 combinaciones, sorteadas con la semilla 18 (3600 ventanas). Solo las finalistas corren en la población completa (1 368 253 ventanas).

**Ajuste y validación**, el mismo esquema del paso 5. Por años: ajuste con las ventanas que empiezan en 2022 o 2023 (2400), validación con las enteras en 2024 (1200). Por empresas: ajuste con META, AAPL y NFLX (2160), validación con AMD y TSLA (1440). En cada idea se elige la variante con más puntos de torneo en el ajuste y se informa en la validación. Las dos separaciones eligen por su cuenta.

**Torneo de 3 rondas.** Tres ventanas sorteadas y 9 rivales que corren las tres con el mismo programa. Uno es siempre el rival de Tesla (`unavez 100 220`); los otros 8 salen del campo de `reales_experimento.py`, dos tercios de las reglas con extremos y un tercio de las otras. Puntos lineales sobre la suma de las tres rondas: 0 al peor y 2 al mejor de los 10. "Primera sola" es terminar sobre todos los rivales, sin empate. Son 20 000 torneos por subconjunto, con los mismos sorteos para todas las estrategias. El patrimonio de los rivales sale de la caché en C de la población.

**Primera sola y la banda 40.** El campo con extremos incluye `espera_banda40`, que es la banda 40 misma. Cuando sale sorteada (en cerca de la mitad de los torneos), la banda 40 empata y no puede quedar primera sola. Por eso su porcentaje de primeros lugares es más bajo que el de bandas más angostas aunque tenga más puntos. Sección 3.1.

**Ruido.** Las ventanas vecinas comparten casi todos sus precios. Cada diferencia de patrimonio medio contra la banda 40 se informa con su error estándar por grupos de ventanas vecinas (empresa y bloque de 20 días de inicio).

**Clases.** A: se calibra sola en la placa con la serie recibida, o sale de un modelo matemático sin datos de Alpaca. B: necesita parámetros ajustados con datos de Alpaca. Las bandas 40 y 60 son B.

**Caché.** Cada resultado queda en `build/cotas/exploracion/` con una clave del código de `ideas.py` e `ideas_dp.py` y de la versión del motor: si el código no cambió, no se vuelve a correr. Cada salida anota el commit sobre el que corrió. Las de este tramo dicen `9ba804a`: el código que las generó entra en el commit siguiente, y la clave de la caché es el hash de ese código, no el del commit.

## 2. Tabla 1: filtros

Comando: `python3 ref/cotas/explorar_ideas.py filtros --semilla 18` (detalle en `docs/mediciones/exploracion/filtros.txt`).

| Idea | Filtro | Número medido | Pasa |
|------|--------|---------------|------|
| 1. Programación dinámica | Puntos de torneo de la tabla de placa (16 × 4, log exacto) contra la banda 40, en la muestra | 1,813 contra 1,860 (la mejor de las 12 variantes: 1,846) | No |
| 2. Grilla | Idas y vueltas completas por ventana en D con N = 4 (mínimo 1) | (100, 255): 0,74; (110, 245): 0,94; (120, 215): 1,41; (130, 200): 1,89 | Sí, solo en (120, 215) y (130, 200) |
| 3. Torneo en sombra | Spearman entre el orden de las cuentas a mitad de ventana y el de la segunda mitad (mínimo 0,2) | +0,322 (dentro de D: +0,055) | Sí a mitad de ventana; dentro de D, no |
| 4. Detector de régimen | Acierto en la validación por años del indicador elegido en el ajuste (mínimo 55 %) | 56,5 % con vr16 (clase mayoritaria: 61,0 %) | Sí por el umbral, pero bajo la clase mayoritaria |
| 5. Cuantiles | Variantes que superan en puntos a la banda fija del mismo ancho medio (más de la mitad) | 0 de 81 | No |
| 6. Contadores saturados | 63 × E[p(n+1) - p(n)] con el contador en 3 (mínimo 10) | +0,10 (el mejor, h = 2) | No |
| 7. Cobertura | Sin filtro en el pedido. Diagnóstico: ventanas en que la copia se activa alguna vez (m = 2 %, Tc = 20 000) | 58,2 % | Sin filtro |
| 8. Final de ronda | Sin filtro en el pedido. Diagnóstico: ventanas que terminan invertidas en D bajo el precio de entrada (banda 40) | 3,4 % | Sin filtro |
| 9. Precio inicial | Tramos de p0 en que P(255 antes que 100) real supera a (p0 - 100) / 155 por más de 0,03, con 50 ventanas o más | Uno: 170-179 (+0,033) | Sí, marginal |
| 10. Caída desde el máximo | Sin filtro en el pedido. Diagnóstico: ventanas con una subida de 20 que se devuelve bajo la entrada | 6,6 % | Sin filtro |

Notas a los filtros:

- **Idea 4.** La primera versión del filtro elegía el indicador mirando la validación (salía "ticks desde el extremo anterior", 72,5 %). Se corrigió: el indicador se elige en el ajuste (vr16, 67,8 % de acierto en el ajuste) y el número es su acierto en la validación, 56,5 %. Pasa el umbral del pedido (55 %), pero queda bajo la clase mayoritaria (61 %: predecir siempre "gana la banda" acierta más). Además, el sentido es el contrario al supuesto del pedido: una razón de varianzas **baja** antes de D anticipa que gana "vende alto y no vuelve". En 3037 de las 3600 ventanas las dos reglas terminan igual.
- **Idea 9.** En casi todos los tramos de p0, la probabilidad real de ver el 255 antes que el 100 está **bajo** la del paseo sin memoria (hasta -0,075 con p0 entre 120 y 129). Solo tres tramos quedan sobre el paseo (170-179 con +0,033, 230-239 con +0,017 y 240-249 con +0,021), con 167 a 214 ventanas cada uno. Pasa por un tramo, de forma marginal.
- **Ideas 7, 8 y 10.** El pedido no les da filtro. Su número es un diagnóstico de cuánto se presenta la situación que atacan, y pasaron directo al barrido.

## 3. Tabla 2: todas las ideas y combinaciones, ordenadas por puntos de torneo fuera de muestra

Comandos: `python3 ref/cotas/explorar_ideas.py idea N --semilla 18` (N de 1 a 12; la 11 son las combinaciones y necesita las anteriores) y `python3 ref/cotas/explorar_ideas.py tabla`. Orden: suma de los puntos de validación de las dos separaciones. Las ideas 1, 5 y 6 no pasaron su filtro: no se barrieron y se informa un representante fijo, elegido antes de ver resultados.

| # | Idea | Clase | Elegida (ajuste por años / por empresas) | Pts validación años / empresas | Pts ajuste años / empresas | 1.ª sola % (val. años / emp.) | Media | Mediana | p5 | Peor | / c. y m. | Órdenes | Comisiones | Pérdida máx. % | Δ media vs banda 40 (ee), años / empresas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 12 | Banda asimétrica (agregada: en Tesla decidió el nivel de venta) | B | banda compra<=140 vende>=215 | 1,866 / 1,849 | 1,848 / 1,861 | 18,3 / 17,3 | 22316 | 24645 | 10917 | 9864 | 1,67 | 3,9 | 20 | 22,6 | +0 (0) / +0 (0) |
| - | banda 40 | base | banda 40 | 1,866 / 1,849 | 1,848 / 1,861 | 18,3 / 17,3 | 22316 | 24645 | 10917 | 9864 | 1,67 | 3,9 | 20 | 22,6 | +0 (0) / +0 (0) |
| 8 | Final de ronda | B | final base=banda w=40 var=c Tf=3 / final base=banda w=40 var=a Tf=100 | 1,864 / 1,847 | 1,847 / 1,860 | 27,3 / 18,2 | 22311 | 24645 | 10907 | 9920 | 1,67 | 4,7 | 23 | 22,6 | -5 (1) / -13 (4) |
| 9 | Decisión según el precio inicial | B | inicio: si p(1950)-p0>=30 compra 1/3; banda 40 / inicio: si p0>=240 compra 1/3; banda 40 | 1,858 / 1,849 | 1,847 / 1,860 | 20,6 / 29,3 | 22275 | 24575 | 11115 | 9864 | 1,67 | 4,1 | 20 | 22,7 | -40 (55) / -10 (15) |
| 4 | Detector de régimen | B | regimen ind=vr64 u1=0.7 u2=1.15 sentido=-1 osc=banda w=60 | 1,860 / 1,840 | 1,845 / 1,860 | 19,3 / 16,9 | 22251 | 24582 | 10917 | 9864 | 1,66 | 3,8 | 19 | 22,5 | -65 (37) / -78 (46) |
| 10 | Salida por caída desde el máximo | B | caida w=40 dd=5 g=60 reentrada=rebote / caida w=40 dd=15 g=60 reentrada=rebote | 1,859 / 1,839 | 1,847 / 1,856 | 23,3 / 24,2 | 22292 | 24645 | 10881 | 9864 | 1,67 | 4,9 | 25 | 22,6 | -23 (24) / -55 (46) |
| 7 | Cobertura contra rivales emulados | B | cobertura base=banda w=40 m=10 Tc=500 | 1,854 / 1,841 | 1,841 / 1,853 | 24,0 / 21,8 | 22253 | 24575 | 10917 | 9864 | 1,66 | 5,5 | 27 | 22,6 | -63 (30) / -37 (28) |
| 11 (10+8) | Combinación 10+8 | B | final base=caida w=40 dd=5 g=60 reentrada=rebote var=b Tf=390 / final base=caida w=40 dd=15 g=60 reentrada=rebote var=b Tf=390 | 1,854 / 1,831 | 1,842 / 1,853 | 29,3 / 30,1 | 22287 | 24645 | 10880 | 9864 | 1,67 | 6,4 | 32 | 22,5 | -29 (25) / -82 (41) |
| 11 (2+4+8) | Combinación 2+4+8 | B | final base=regimen ind=vr64 u1=0.7 u2=1.15 sentido=-1 osc=grilla N=2 Linf=130 Lsup=200 modo=fraccion var=b Tf=390 / final base=regimen ind=vr64 u1=0.7 u2=1.15 sentido=-1 osc=grilla N=2 Linf=120 Lsup=215 modo=fraccion var=b Tf=390 | 1,851 / 1,829 | 1,837 / 1,852 | 29,7 / 30,8 | 22223 | 24582 | 10862 | 9864 | 1,66 | 5,3 | 27 | 22,5 | -93 (42) / -102 (48) |
| 11 (3 con tres cuentas) | Combinación 3 con tres cuentas | B | sombra 3c R=1000 M=1/16 lider | 1,850 / 1,821 | 1,834 / 1,853 | 19,8 / 18,7 | 22209 | 24645 | 10917 | 9864 | 1,66 | 14,3 | 71 | 22,6 | -106 (50) / -178 (71) |
| 5 | Bandas por cuantiles (no pasó el filtro; representante fijo) | A | cuantil qc=0.25 qv=0.75 origen=inicio calor=1950 | 1,843 / 1,814 | 1,808 / 1,831 | 30,6 / 31,0 | 22250 | 24645 | 10917 | 9864 | 1,66 | 4,4 | 22 | 22,6 | -65 (170) / -113 (229) |
| 11 (5+8) | Combinación 5+8 | B | final base=cuantil qc=0.25 qv=0.75 origen=inicio calor=1950 var=b Tf=390 | 1,838 / 1,807 | 1,803 / 1,827 | 36,8 / 36,8 | 22229 | 24645 | 10880 | 9864 | 1,66 | 6,5 | 32 | 22,6 | -86 (170) / -141 (229) |
| - | tres bandas por hilo | base | tres bandas por hilo | 1,820 / 1,803 | 1,807 / 1,822 | 34,6 / 36,2 | 22014 | 24656 | 10935 | 9864 | 1,65 | 4,8 | 24 | 21,3 | -302 (204) / -287 (197) |
| 1 | Política por programación dinámica (no pasó el filtro; representante fijo) | A | dp objetivo=log_exacto version=placa modo=cambios | 1,807 / 1,800 | 1,805 / 1,815 | 30,1 / 33,8 | 22010 | 24582 | 10935 | 9864 | 1,65 | 5,7 | 28 | 21,8 | -306 (171) / -220 (148) |
| - | banda 60 | base | banda 60 | 1,811 / 1,794 | 1,810 / 1,826 | 26,7 / 26,3 | 22059 | 24575 | 10917 | 9864 | 1,65 | 4,5 | 23 | 23,2 | -256 (272) / -319 (226) |
| 2 | Grilla con compensación | B | grilla N=2 Linf=130 Lsup=200 modo=fraccion / grilla N=2 Linf=120 Lsup=215 modo=fraccion | 1,806 / 1,794 | 1,813 / 1,822 | 28,6 / 27,6 | 21877 | 24582 | 10935 | 9864 | 1,64 | 4,5 | 22 | 21,7 | -438 (236) / -410 (214) |
| 3 | Torneo en sombra | A | sombra 19c R=1000 M=1/16 lider | 1,807 / 1,771 | 1,798 / 1,825 | 36,5 / 31,7 | 22045 | 24582 | 10935 | 9864 | 1,65 | 6,4 | 32 | 22,8 | -270 (343) / -442 (262) |
| 6 | Predictor de contadores saturados (no pasó el filtro; representante fijo) | A | contadores h=4 xor=False | 0,810 / 0,622 | 0,775 / 0,899 | 1,6 / 0,6 | 14895 | 15590 | 950 | 148 | 1,11 | 867,8 | 4339 | 37,1 | -7421 (839) / -8224 (748) |

Media, mediana, p5, peor, razón contra comprar y mantener, órdenes, comisiones y pérdida máxima: validación por años (ventanas enteras en 2024), con la variante elegida en el ajuste por años. Δ: diferencia de patrimonio medio contra banda 40 en cada validación, con la variante elegida en su ajuste, y su error estándar por grupos de ventanas vecinas (empresa y bloque de 20 días de inicio).

### 3.1 Primera sola sin la regla idéntica del campo

Comando: `python3 ref/cotas/explorar_ideas.py detalle --semilla 18` (`detalle.txt`). Si se saca `espera_banda40` del campo, la banda 40 queda primera sola en el 40,0 % (años) y el 37,0 % (empresas) de los torneos, contra 18,3 % y 17,3 % con el campo de siempre. Sus puntos casi no cambian (1,863 y 1,846). La banda 60 pasa a 39,4 % y 37,6 %, y las tres bandas por hilo a 48,0 % y 45,7 %.

Dos lecturas. El porcentaje bajo de primeros lugares de la banda 40 en la tabla 2 viene del empate con su copia exacta, no de una debilidad. Y por la misma razón las ideas 8, 9, 10 y 7 muestran más primeros lugares que la banda 40 con casi los mismos puntos: cualquier diferencia mínima rompe el empate con la copia, hacia arriba o hacia abajo. Las tres bandas por hilo quedan primeras solas más veces que la banda 40 aun sin la copia (48 % contra 40 %), pero con menos puntos: ganan más torneos y pierden por más en los que no ganan.

### 3.2 Combinaciones

Cada separación arma sus combinaciones con los componentes elegidos en su propio ajuste, más cinco variantes del final de ronda (a con Tf 1000 y 2000, b con Tf 390 y 1000, c con Tf 390). La idea 3 con tres cuentas (banda 40, "vende con 220 o más y no vuelve" y grilla de 4) barre R, M y el modo. Ninguna combinación mejora a su mejor componente. La 2+4+8 queda en la práctica como la idea 4: la razón de varianzas casi nunca pasa de 1,15, así que el modo oscilador (la grilla) casi no se usa.

### 3.3 Idea 7 contra rivales emulados y no emulados

La cobertura copia la posición del rival de Tesla o de comprar y mantener cuando la banda queda atrás de ellos por más de m. Elegida en los dos ajustes: m = 10 % y Tc = 500. Resultado en la validación (`detalle.txt`):

| Campo | Puntos, cobertura contra banda 40 (años / empresas) | Primera sola, cobertura contra banda 40 (años / empresas) |
|-------|------------------------------------------------------|------------------------------------------------------------|
| El de siempre (rival de Tesla fijo) | 1,854 contra 1,866 (-0,011) / 1,841 contra 1,849 (-0,008) | 24,0 % contra 18,3 % (+5,7) / 21,8 % contra 17,3 % (+4,4) |
| Sin los rivales emulados (sin el rival de Tesla ni comprar y mantener) | 1,848 contra 1,860 (-0,012) / 1,835 contra 1,844 (-0,008) | 18,6 % contra 12,0 % (+6,6) / 16,8 % contra 11,4 % (+5,4) |

Pierde puntos en los dos campos. La subida en primeros lugares es casi la misma con y sin los rivales que emula. Por eso no viene de la cobertura: viene de romper el empate con `espera_banda40` (sección 3.1).

## 4. Resultados negativos

| Idea | Número que la descarta | Lectura |
|------|------------------------|---------|
| 1. Programación dinámica | Filtro: 1,813 puntos contra 1,860 de la banda 40 en la muestra; ninguna de las 12 variantes llega a 1,860. Validación del representante: -306 (ee 171) y -220 (ee 148) contra banda 40 | Con log exacto o patrimonio lineal, el modelo del paseo condicionado da una banda angosta en el centro (compra con 161 a 163, vende con 177 a 178) que solo se abre en los últimos 2500 ticks (`dp_tablas.txt`). Gana más veces sola (33 % contra 17 %) pero pierde en puntos: el paseo condicionado subestima cuánto se aleja el precio real del centro. Con la tabla entera L[x] = round(1024 log2 x), el redondeo (medio punto en diferencias de 8 a 9 por nivel) pesa más que la ganancia esperada por tick en el centro y la política sale salpicada (19 900 de 20 000 ticks restantes sin forma de umbral). Para la placa eso no importa, porque la tabla se calcula fuera, pero descarta calcular la política en el chip con esa tabla |
| 2. Grilla | Pasa el filtro solo en los rangos angostos (1,41 y 1,89 idas y vueltas por ventana en D, contra 0,74 en 100-255). Validación de la elegida (N = 2, 130-200 o 120-215): -438 (ee 236) y -410 (ee 214) contra banda 40 | El 61 % de las ventanas no completa ninguna ida y vuelta en D. Donde sí hay, los tramos angostos venden demasiado pronto: en esta población el dinero está en quedarse adentro desde 140 hasta 215 |
| 3. Torneo en sombra | Filtro: Spearman +0,32 entre el orden a mitad de ventana y la segunda mitad, pero +0,055 dentro de D. Validación de la elegida (19 cuentas, R = 1000, M = 1/16, seguir a la líder): -270 (ee 343) y -442 (ee 262) | La correlación a mitad de ventana viene de que las cuentas con fases son idénticas hasta D. Dentro de D, el orden de las cuentas no persiste: seguir a la líder es seguir ruido. Cambios de líder en la validación (`detalle.txt`): 0,58 (años) y 0,71 (empresas) por ventana, con 0,9 a 1,1 órdenes por cambio (4 a 5 de comisión). La comisión no explica la pérdida. En las ventanas sin cambio de líder la sombra opera igual que la banda 40 (0 órdenes y 0 de patrimonio de diferencia). En las que cambian (34 % y 40 % de las ventanas) hace 7 a 10 órdenes más y pierde 793 y 1100 de media. En total son -464 y -623 por cada cambio de líder, casi todo por seguir a una cuenta que después rinde menos. Con tres cuentas (combinación 3) hay 0,06 y 0,10 cambios por ventana. En las ventanas con cambio hace 150 a 160 órdenes más y pierde 1660 a 1880 |
| 5. Cuantiles | Filtro: 0 de 81 variantes superan a la banda fija del mismo ancho medio | La banda que se mueve con el histograma es una banda fija peor centrada. Con el histograma desde D y calentamiento corto pierde hasta 2 000 de media |
| 6. Contadores saturados | Filtro: 63 × E = +0,10 con el mejor contador (h = 2), contra 10 exigido. El representante (h = 4) hace 868 órdenes por ventana y termina con 14 895 de media | El signo del siguiente cambio no se puede predecir con la historia de signos a un minuto: E[p(n+1) - p(n)] con el contador en 3 está entre -0,003 y +0,002 niveles |
| 8. Final de ronda en Tesla | Ninguna variante pasa de 20 795 (banda 40) en la ronda de Tesla; el rival hizo 21 467 | Ver la sección 0, punto 5, y `docs/mediciones/exploracion/tesla.txt` |
| 12. Banda asimétrica | El óptimo de 56 combinaciones es 140/215 en los dos ajustes | No es un resultado negativo de la banda 40: confirma que no hay un nivel de venta mejor que 215 (con 225 la validación por empresas baja de 1,849 a 1,829 puntos) |

Las ideas 4, 7, 8, 9 y 10 no se descartan por su filtro, pero tampoco ganan: quedan bajo la banda 40 en las dos validaciones.

## 5. Finalistas en la población completa

Comando: `python3 ref/cotas/explorar_ideas.py completa 5 --semilla 18` (salida en `docs/mediciones/exploracion/completa.txt`). Corren las cinco ideas con más puntos de validación en la muestra: la 12, la 8, la 9, la 4 y la 10. La idea 7 quedó sexta y no entró. Cada una va con las variantes elegidas en cada separación, junto con las tres bases, en las 1 368 253 ventanas.

Cada idea se informa con la variante elegida en el ajuste de cada separación, medida en la validación de esa misma separación. En "todas las ventanas" se usa la elegida por años (incluye las ventanas de ajuste: es una referencia, no una validación). Δ es la diferencia de patrimonio medio por ronda contra la banda 40, con su error estándar por grupos de ventanas vecinas. Detalle completo, con mediana, p5, peor, razón contra comprar y mantener, comisiones y pérdida máxima, en `completa.txt`.

| Estrategia (elegida por años / por empresas) | Clase | Pts validación años / empresas | Δ validación años / empresas (ee) | 1.ª sola % val. años / emp. | Todas las ventanas: pts, media, Δ (ee) | Órdenes (val. años) |
|---|---|---|---|---|---|---|
| Banda 40 (idea 12 elige lo mismo: 140/215) | B | 1,876 / 1,848 | 0 / 0 | 18,6 / 17,0 | 1,859; 21 289; 0 | 3,9 |
| Idea 8: vende en los últimos 3 ticks sobre la entrada / no compra en los últimos 100 | B | 1,875 / 1,846 | -4 (1) / -10 (2) | 27,4 / 17,8 | 1,858; 21 285; -4 (0) | 4,6 |
| Idea 9: compra 1/3 si p(1950) - p0 ≥ 30 / si p0 ≥ 240 | B | 1,869 / 1,845 | -41 (41) / -15 (11) | 21,6 / 28,5 | 1,857; 21 281; -8 (18) | 4,1 |
| Idea 4: al entrar a D, vr64 < 0,70: no vuelve sobre 220; vr64 > 1,15: banda 60; si no, banda 40 | B | 1,870 / 1,840 | -64 (41) / -67 (36) | 20,5 / 16,7 | 1,855; 21 254; -35 (17) | 3,9 |
| Idea 10: caída de 5 / de 15 desde el máximo, reentrada por rebote | B | 1,869 / 1,837 | -35 (21) / -50 (35) | 22,9 / 23,2 | 1,855; 21 289; 0 (17) | 4,9 |
| Banda 60 | B | 1,824 / 1,790 | -257 (244) / -314 (194) | 27,3 / 25,3 | 1,817; 21 084; -205 (101) | 4,5 |
| Tres bandas por hilo | B | 1,830 / 1,798 | -328 (174) / -296 (157) | 34,0 / 34,3 | 1,815; 21 057; -232 (94) | 4,8 |

La población confirma a la muestra. El orden es el mismo y los signos también, y las diferencias contra la banda 40 cambian entre 1 y 12 de la muestra a la población (por ejemplo, banda 60: -256 y -319 en la muestra, -257 y -314 en la población). El error de muestreo es chico. El error estándar por grupos mide otra cosa: cuánto cambiaría el resultado con otros períodos y otras empresas. Ninguna idea queda sobre la banda 40 en su propia validación. Las únicas cifras positivas aparecen al cruzar separaciones, por ejemplo la elegida por años de la idea 9 medida en AMD y TSLA: +10 (22) y +8 (25) con la de la idea 10. No son validaciones limpias, porque el ajuste por años incluye ventanas de AMD y TSLA de 2022 y 2023, y quedan a menos de medio error estándar de cero.

La primera corrida tomó 6158 s (103 minutos) con 24 núcleos. Al repetir el comando se leen las evaluaciones de la caché y solo se rehacen los torneos.

## 6. Las tres mejores: opciones para decidir

Las tres ideas con más puntos fuera de muestra son la 8 (final de ronda), la 9 (precio inicial) y la 4 (detector de régimen). Las tres son la banda 40 con un agregado. Por eso las opciones se presentan sobre la banda 40, y la decisión de banda 40 contra banda 60 va como una opción más.

Números de la validación (años / empresas) en la muestra y, debajo, en la población completa (sección 5). "Δ" es la diferencia de patrimonio medio por ronda contra la banda 40, con su error estándar por grupos entre paréntesis.

| Opción | Qué cambia | Puntos de validación | Δ contra banda 40 | Δ contra banda 60 | Costo y riesgo | Hilos |
|--------|------------|----------------------|-------------------|-------------------|----------------|-------|
| **1. Banda 40 sola** | En D compra con p ≤ 140 y vende con p ≥ 215 (hoy 160 y 195) | 1,866 / 1,849; población: 1,876 / 1,848 | 0 | +256 (272) / +319 (226); población: +257 (244) / +314 (194) | Una constante en `sw/trade.s` (R0) y dos valores de la tabla en R1 y R2, cargados con `icebram` sobre los mismos moldes. El hardware no cambia. Hay que repetir la puerta de simulación de los tres peldaños (cerca de un día con R1 y R2) | Como hoy: la regla en el hilo 0, los hilos 1 a 3 en espera |
| **2. Banda 60, sin cambios** | Nada | 1,811 / 1,794; población: 1,824 / 1,790 | -256 / -319; población: -257 / -314 | 0 | Ningún trabajo; ya corrió con la maestra real el 18/11 (18 779 en Tesla, 21 895 en AMD) | Como hoy |
| **3. Banda 40 con final de ronda** (idea 8) | Además: vende en los últimos 3 ticks si el precio está sobre el de entrada (ajuste por años), o no compra en los últimos 100 ticks (ajuste por empresas) | 1,864 / 1,847; población: 1,875 / 1,846 | -5 (1) / -13 (4); población: -4 (1) / -10 (2) | +251 / +306; población: +253 / +304 | Lo de la opción 1, más unas 10 instrucciones por tick y un contador de ticks. Pierde poco pero en forma sistemática: vender al final paga comisión sin cambiar el precio de cierre | Hilo 0 |
| **4. Banda 40 con precio inicial** (idea 9) | Además, en la fase A: compra un tercio si p(1950) - p0 ≥ 30 (años) o si p0 ≥ 240 (empresas) | 1,858 / 1,849; población: 1,869 / 1,845 | -40 (55) / -10 (15); población: -41 (41) / -15 (11) | +216 / +309; población: +216 / +299 | Lo de la opción 1, más una división una sola vez. Las dos separaciones eligen reglas distintas, señal de que no hay una regla estable. Si la normalización por ronda resultara falsa, comprar en la fase A pierde (el argumento de T133) | Hilo 0 |
| **5. Banda 40 con detector de régimen** (idea 4) | Además, al entrar a D, según la razón de varianzas a 64 ticks: bajo 0,70 vende con 220 o más y no vuelve; sobre 1,15 usa la banda 60; entre las dos, la banda 40 | 1,860 / 1,840; población: 1,870 / 1,840 | -65 (37) / -78 (46); población: -64 (41) / -67 (36) | +191 / +241; población: +193 / +247 | Lo de la opción 1, más unas 60 instrucciones por tick y un anillo de 64 precios. El indicador acierta menos que la clase mayoritaria (filtro de la idea 4) | El hilo 1 calcula la razón de varianzas y publica el modo con el número de tick; el hilo 0 decide y, si el hilo 1 no responde, usa la banda 40 (la degradación de 16.3) |

**Qué se pierde con cada una.** Quedarse con la banda 60 (opción 2) deja en la mesa unas 250 a 320 unidades por ronda y 0,055 puntos por torneo, sin costo de trabajo. Las opciones 3 a 5 agregan código, instrucciones y algo que verificar, a cambio de nada medible: en las dos validaciones quedan bajo la opción 1. Ninguna de las cinco habría ganado la ronda de Tesla del 18/11 (banda 40: 20 795; rival: 21 467). Lo único que la gana es la regla del rival, que en la población promedia 18 896 (`docs/cotas.md`, sección 7.2).

**Recomendación (mía, etiquetada como tal): opción 1, la banda 40 sola.** Es la mejor en todos los cortes que se midieron hoy y en el paso 5. El cambio son dos constantes con el mismo programa y el mismo hardware. Si no alcanza el tiempo para repetir la puerta de los tres peldaños antes del 26/11, la opción 2 es la segunda mejor de las simples y no requiere nada: ninguna de las opciones 3 a 5 justifica el trabajo extra. La diferencia entre 40 y 60 es de un 1,2 % a 1,6 % por ronda y está cerca del ruido en cada separación por separado (cerca de un error estándar), pero tiene el mismo signo en casi todos los cortes medidos: las dos validaciones de hoy, la población completa, los tres años de inicio del paso 5, 4 de las 5 empresas (la excepción es NFLX) y las tres series conocidas de la clase.

## 7. Cabe en la placa

Presupuesto por hilo a 0,1 ms: 565 instrucciones por tick (2262 ciclos repartidos en los 4 hilos del barrel). Hoy el hilo 0 ejecuta entre 40 y 50 instrucciones de trabajo por tick y los hilos 1 a 3 esperan; el programa ocupa 67 de las 512 palabras de memoria y no usa RAM de datos; la tabla de parámetros en BRAM tiene 236 entradas libres de 16 bits (`docs/fondo.md`, `docs/puertas.md`). Quedan 3 BRAM y unas 235 celdas. El bitstream de competencia no tiene multiplicador ni `mulstep`, y la ALU no desplaza (`rtl/espino_core/espino_alu.v`: los desplazamientos están deshabilitados para ahorrar celdas). Por eso q por p se arma solo con sumas y comparaciones (ejemplo abajo: 64 instrucciones para q de 9 bits, sin saltos), y una división es un lazo de restas (unas 60 a 80 instrucciones para un cociente de 7 bits). Multiplicar por una constante chica son sumas (4x = (x + x) + (x + x)). Ninguna idea necesita tocar el RTL.

| Idea | Instrucciones por tick (peor caso, por hilo) | Memoria y BRAM | Multiplicación o división en el camino de decisión |
|------|---------------------------------------------|----------------|----------------------------------------------------|
| Bandas 40 y 60 (hoy) | 40 a 50 en el hilo 0 | 2 constantes en la tabla | No |
| 1. Programación dinámica | Unas 35 (q: un contador de cambios; clase: comparar 4 nc con n, 2 nc con n y 4 nc con 3 n, con sumas; tramo: un contador regresivo de 1250 ticks; dos lecturas de la tabla) | Tabla de 16 × 4 × 2 bytes en la BRAM de parámetros | No |
| 2. Grilla | 60 con N = 2 a 4, unas 150 con N = 12, más unas 40 de la cuenta propia | N palabras | Tramo fijo en acciones: no. Tramo como fracción del patrimonio: una división W / (N p) al comprar |
| 3. Torneo en sombra | 19 cuentas × unas 60 (decisión y recorte) = 1140, repartidas en los hilos 1 a 3 (unas 380 cada uno), más el orden cada R ticks (19 productos q por p de 64 instrucciones, repartidos en varios ticks); con 3 cuentas, unas 200 en un hilo | 3 palabras por cuenta | q por p en cada cuenta; con `mulstep` serían 7 instrucciones, pero no está en el bitstream |
| 4. Detector de régimen | Unas 60 (vr64: anillo de 64 precios, dos cuadrados por tick con una tabla de cuadrados o un lazo corto) | Anillo de 64 bytes (16 palabras); vr390 necesitaría 98 palabras | Cuadrados (tabla); la comparación con θ k S1 es por una constante, con sumas |
| 5. Cuantiles | Unas 50; el olvido (dividir por 2 los 156 contadores cada 4096 ticks) se reparte en varios ticks, o se reemplaza por duplicar el incremento | 78 palabras | No (la fracción k/8 se compara como 8 c contra k n, con sumas) |
| 6. Contadores | Unas 30 | h = 4: 16 palabras; h = 6: 256 palabras | No |
| 7. Cobertura | 3 cuentas × (unas 20 de decisión más 64 del producto q por p) más el patrimonio propio (64) y la comparación con margen: unas 330, en un hilo o repartidas en los hilos 1 a 3 | 10 palabras | q por p; el margen (100 + m) W es por una constante |
| 8. Final de ronda | Unas 10 (contador de ticks y comparación; la variante b baja el nivel con un acumulador, sin dividir) | 3 palabras | No |
| 9. Precio inicial | Unas 10 por tick; la compra parcial f W / p, una sola vez | 2 palabras | Una división una sola vez (o ninguna si f = 1) |
| 10. Caída desde el máximo | Unas 20 | 4 palabras | No |
| 12. Banda asimétrica | Igual que hoy | 2 constantes en la tabla | No |

Todas caben. Las que más piden son la idea 3 con 19 cuentas (tiene que repartirse en tres hilos) y la 7.

**q por p sin multiplicador ni desplazador** (ideas 3 y 7, y la cuenta propia de la grilla). Es el método de Horner sobre los bits de q, de mayor a menor. En cada paso el producto se duplica con una suma. Si q es mayor o igual que 2^k, se le resta 2^k y se suma p. La comparación se convierte en máscara con `sltiu`, así que no hay saltos y el tiempo es constante, como en `sw/trade.s`. Son 7 instrucciones por bit: con q de 9 bits (hasta 511 acciones, más de las que permite la caja), 64 instrucciones, unos 64 ciclos de su hilo en el barrel. Con `mulstep` serían 9, pero esa instrucción no está en el bitstream de competencia.

```
# x10 = q (0 a 511), x11 = p (100 a 255); deja q por p en x12. Usa x13 y x14.
        li    x12, 0
        # paso del bit 8; se repite con 128, 64, 32, 16, 8, 4, 2 y 1
        add   x12, x12, x12     # producto = 2 * producto
        sltiu x13, x10, 256     # x13 = 1 si q < 256
        addi  x13, x13, -1      # máscara: 0 si q < 256, todo unos si no
        and   x14, x13, x11     # p o 0
        add   x12, x12, x14     # producto = producto + p
        andi  x14, x13, 256     # 256 o 0
        sub   x10, x10, x14     # q = q - 256 si correspondía
```

## 8. Comandos

Todos con los minutos fuera del repositorio: `export P4_DATOS=~/proyectos/datos_p4` o `--datos CARPETA`. Semilla 18 por omisión.

| Resultado | Comando | Salida |
|-----------|---------|--------|
| Motor contra la referencia | `python3 ref/cotas/explorar_ideas.py validar` | `validar.txt` |
| Tablas de la idea 1 | `python3 ref/cotas/ideas_dp.py` | `dp_tablas.txt` |
| Tabla 1 | `python3 ref/cotas/explorar_ideas.py filtros --semilla 18` | `filtros.txt` |
| Barrido de cada idea | `python3 ref/cotas/explorar_ideas.py idea 1 2 3 4 5 6 7 8 9 10 12 --semilla 18` | `ideaN.txt` e `ideaN.json` |
| Combinaciones | `python3 ref/cotas/explorar_ideas.py idea 11 --semilla 18` | `idea11.txt` |
| Tabla 2 | `python3 ref/cotas/explorar_ideas.py tabla` | `tabla2.md` |
| Ideas 3 y 7 en detalle, primera sola sin la regla idéntica | `python3 ref/cotas/explorar_ideas.py detalle --semilla 18` | `detalle.txt` |
| Idea 8 en la ronda de Tesla | `python3 ref/cotas/explorar_ideas.py tesla` | `tesla.txt` |
| Finalistas en la población completa | `python3 ref/cotas/explorar_ideas.py completa 5 --semilla 18` | `completa.txt` |

Las salidas quedan en `docs/mediciones/exploracion/`. Los `.json` no se suben al repositorio (el `.gitignore` ignora `*.json`): se regeneran con los mismos comandos, y `tabla` y `completa` los necesitan, así que van después de `idea`.

## 9. Segunda tanda (19/11): ideas 13 y 14, y primera sola sin la copia

Pedido de Nicolás del 19/11: dos ideas nuevas sobre la banda 40, cada una con su filtro primero, con el mismo protocolo, validaciones y reglas de sesión. En el pedido son la 11 y la 12; aquí son la **13** (niveles según el orden de los extremos) y la **14** (reloj de día de mercado), para no confundirlas con la 11 (combinaciones) y la 12 (banda asimétrica) de la primera tanda. Código: `ref/cotas/ideas_reloj.py` (comportamientos y detectores) y `ref/cotas/explorar_ideas2.py` (filtros, barridos y tablas). `ideas.py` no cambió, así que las cachés de la primera tanda siguen valiendo. Este documento presenta resultados; la decisión no se toma aquí.

### 9.1 Filtros

| Idea | Filtro del pedido | Número medido | Pasa |
|------|-------------------|---------------|------|
| 13. Niveles según el orden de los extremos | Por caso, el mejor par (compra, venta) contra 140/215; se descarta si en los dos casos queda a menos de un error estándar | Caso S: 130/185, +208 (ee 237). Caso B: 140/205, +157 (ee 116) | Sí, por el caso B |
| 14. Reloj de día de mercado | Algún efecto del día pasa 2 ee en el ajuste y se mantiene (mismo signo, más de 2 ee) en la validación por años y por empresas | El salto de cierre a apertura no (t del ajuste: +1,3 por años, +1,9 por empresas). 19 minutos del día sí, de 0,03 a 0,12 niveles | Sí, por los minutos; el salto no |

### 9.2 Resultados en la validación (formato de la tabla 2)

| # | Idea | Clase | Elegida (años / empresas) | Pts validación años / empresas | Pts ajuste años / empresas | 1.ª sola % | Media | Mediana | p5 | Peor | / c. y m. | Órdenes | Comisiones | Pérdida máx. % | Δ media vs banda 40 (ee), años / empresas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| - | banda 40 | base | banda 40 | 1,866 / 1,849 | 1,848 / 1,861 | 18,3 / 17,3 | 22316 | 24645 | 10917 | 9864 | 1,67 | 3,9 | 20 | 22,6 | 0 / 0 |
| 13 | Niveles según el orden de los extremos | B | S 140/215 y B 140/205 / 140/215 en los dos (la banda 40) | 1,860 / 1,849 | 1,849 / 1,861 | 20,2 / 17,3 | 22300 | 24645 | 10917 | 9864 | 1,67 | 4,0 | 20 | 22,5 | -16 (41) / 0 (0) |
| - | banda 60 | base | banda 60 | 1,811 / 1,794 | 1,810 / 1,826 | 26,7 / 26,3 | 22059 | 24575 | 10917 | 9864 | 1,65 | 4,5 | 23 | 23,2 | -256 (272) / -319 (226) |
| 14 | Reloj de día de mercado | B | detector por bloques, vende 1 tick después del salto (las dos) | 1,808 / 1,791 | 1,807 / 1,821 | 31,9 / 26,5 | 21864 | 24411 | 10917 | 9864 | 1,63 | 9,5 | 48 | 22,7 | -452 (189) / -421 (110) |

Media, mediana, p5, peor, razón contra comprar y mantener, órdenes, comisiones y pérdida máxima son de la validación por años. En el orden de la tabla 2, la idea 13 queda entre la 8 y la 9, y la 14 entre la grilla y el torneo en sombra. **Ninguna de las dos le gana a la banda 40 fuera de muestra.** Con grupos de 60 días de inicio (más que el largo de una ventana) los errores estándar de la idea 13 suben de 41 a 46 y los de las 9 variantes de la 14 cambian entre -12 % y +20 %; ninguna conclusión cambia.

### 9.3 Idea 13: niveles según el orden de los extremos

Comandos: `python3 ref/cotas/explorar_ideas2.py filtro13 --semilla 18` (`filtro13.txt`) y `python3 ref/cotas/explorar_ideas2.py idea13 --semilla 18` (`idea13.txt`, `idea13.json`).

El caso queda fijado al entrar a D: en el caso S la fase D empieza al ver el 255 y la banda vende; en el B empieza al ver el 100 y la banda compra. Como las fases A a C son iguales para todos los pares, la regla con un par por caso es, ventana por ventana, la banda del par de su caso. Así se armaron las 900 combinaciones a partir de 30 bandas (20 ya estaban en la caché de la idea 12). La regla simulada directamente (`OrdenD`) da lo mismo que la composición en las 2 combinaciones elegidas y las 3600 ventanas: 0 diferencias.

| Caso | Ventanas | Tick mediano de entrada a D | Banda 40: patrimonio medio | Tocan 215 después de entrar a D | Toques de 215 por ventana | Tocan 140 después de entrar a D | Mejor par | Δ contra 140/215 (ee; ee con grupos de 60 días) |
|------|----------|-----------------------------|----------------------------|-------------------------------|---------------------------|--------------------------------|-----------|-----------------------------------------------|
| S (100 antes que 255) | 2101 (58,4 %) | 17 695 | 25 678 | 1015 (48,3 %) | 9,45 | 295 (14,0 %) | 130/185 | +208 (237; 255) |
| B (255 antes que 100) | 1499 (41,6 %) | 16 175 | 15 325 | 294 (19,6 %) | 3,37 | 896 (59,8 %) | 140/205 | +157 (116; 124) |

Lectura del filtro. En el caso S la banda vende en el 255 al entrar a D y queda en caja, y el nivel de venta solo importa en el 14 % de las ventanas que vuelven a 140. En el caso B la banda compra en el 100, y el nivel de venta decide en el 20 % que llega a 215. El mejor par del caso B (vender en 205) es el mejor de 30 en la misma muestra, así que lleva el sesgo de elegir el máximo.

En el protocolo, el ajuste por empresas elige 140/215 en los dos casos (la banda 40 queda primera de 900 en el ajuste). El ajuste por años elige S 140/215 y B 140/205, con 1,849 puntos contra 1,848 de la banda 40. En su validación queda en 1,860 contra 1,866, con -16 (ee 41) de patrimonio medio. **La ventaja del caso B no se sostiene fuera de muestra.**

Placa: igual que la banda, con cuatro constantes en la tabla en vez de dos y un bit que guarda cuál extremo llegó primero (unas 3 instrucciones más). No necesita RTL, multiplicación ni división.

### 9.4 Idea 14: reloj de día de mercado

Comandos: `python3 ref/cotas/explorar_ideas2.py filtro14 --semilla 18` (`filtro14.txt`) y `python3 ref/cotas/explorar_ideas2.py idea14 --semilla 18` (`idea14.txt`, `idea14.json`).

**Error estándar.** En esta idea la unidad es el tick, y un mismo tick aparece en cientos de ventanas de la muestra que empiezan en bloques vecinos. Con los grupos de la tabla 2 (empresa y bloque de 20 días de inicio de la ventana), entre 146 y 198 de los 390 minutos pasaban 2 ee en cada subconjunto, cuando por azar se esperan unos 20, y el salto pasaba en los cuatro subconjuntos del protocolo (t de 2,1 a 4,3). Por eso se agrupó por empresa y bloque de 20 días de la fecha del tick mismo. Todos los números de esta sección usan esa agrupación. Para las diferencias de patrimonio por ventana de las ideas 13 y 14, la versión conservadora (grupos de 60 días de inicio, más que el largo de una ventana) cambia el error estándar entre -12 % y +20 %. No se recalculó para la primera tanda.

**Salto de cierre a apertura** (minuto 0, p(apertura) - p(cierre anterior), en niveles normalizados), por empresa y año de inicio de la ventana: media (ee).

| Empresa | 2022 | 2023 | 2024 | Todos |
|---------|------|------|------|-------|
| META | -0,75 (0,44) | +1,38 (0,45) | +0,65 (0,53) | +0,43 (0,31) |
| AAPL | -0,41 (0,38) | +0,12 (0,43) | +0,42 (0,82) | +0,04 (0,34) |
| NFLX | -0,32 (0,58) | +1,17 (0,43) | +1,03 (0,51) | +0,63 (0,32) |
| AMD | +0,01 (0,55) | +0,45 (0,40) | +0,84 (0,44) | +0,43 (0,28) |
| TSLA | +0,46 (0,34) | -0,11 (0,51) | +0,59 (0,52) | +0,32 (0,28) |
| Todas | -0,20 (0,22) | +0,60 (0,21) | +0,71 (0,26) | +0,37 (0,14) |

El salto mide 5,73 niveles en valor absoluto en promedio y su media es +0,37, con t de 2,7 en toda la muestra. El signo cambia con el año: es negativo en 2022, el año de caída. En el protocolo:

| Efecto | Ajuste años | Validación años | Ajuste empresas | Validación empresas | Se mantiene |
|--------|-------------|-----------------|-----------------|---------------------|-------------|
| Salto (minuto 0) | +0,20 (0,16) | +0,71 (0,26) | +0,37 (0,19) | +0,37 (0,20) | No: no pasa 2 ee en ningún ajuste |
| Salto + primer minuto (lo que gana por acción quien pasa el salto) | +0,11 (0,16) | +0,68 (0,26) | +0,36 (0,19) | +0,22 (0,20) | No |
| Signo del salto × 30 minutos siguientes (+ sigue, - revierte) | +0,08 (0,12) | -0,05 (0,17) | +0,16 (0,14) | -0,15 (0,12) | No |

En toda la muestra, los 30 minutos que siguen a un salto positivo se mueven -0,13 (ee 0,13), y los que siguen a uno negativo -0,22 (ee 0,15). El signo del salto no predice los 30 minutos siguientes.

**Los 390 minutos del día.** Pasan 2 ee entre 65 y 121 minutos por subconjunto, y 19 se mantienen en el ajuste y la validación de las dos separaciones: 09:43, 10:15, 10:50, 10:57, 11:14, 11:15, 11:52, 12:05, 12:52, 13:00, 13:41, 13:59, 14:38, 15:03, 15:17, 15:24, 15:35, 15:51 y 15:59. Varios están junto a horas o cuartos de hora redondos (10:15, 11:14 y 11:15, 13:00, 13:59, 15:59). Que pasen 65 a 121 minutos por subconjunto, y no 20, indica que hay estructura dentro del día o que el error estándar todavía queda corto. En cualquier caso son chicos: de 0,03 a 0,12 niveles. Una ida y vuelta de 63 acciones paga 10 de comisión, así que necesita más de 10 / 63 = 0,16 niveles por vuelta. Ninguno alcanza.

**La regla del pedido.** En la fase D, con la banda 40 en caja, compra 63 para pasar el salto (decidida tras ver p(j - 2), se ejecuta al cierre p(j - 1)) y vende h ticks después del salto. Se barrieron 9 variantes: detector oráculo (el minuto verdadero, una cota superior que la placa no tiene), por histograma y por bloques, con h de 1, 5 y 30. Diferencia de patrimonio medio contra banda 40 en la validación, con su ee:

| Variante | Años | Empresas | Vueltas por ventana (años / empresas) |
|----------|------|----------|---------------------------------------|
| Bloques, h = 1 (la elegida en los dos ajustes) | -452 (189) | -421 (110) | 2,85 / 3,23 |
| Bloques, h = 5 | -568 (209) | -496 (132) | 2,85 / 3,23 |
| Bloques, h = 30 | -818 (247) | -631 (169) | 2,85 / 3,23 |
| Histograma, h = 1 | -616 (213) | -682 (125) | 6,03 / 6,37 |
| Oráculo, h = 1 | -590 (216) | -739 (147) | 6,03 / 6,37 |
| Histograma, h = 5 | -748 (236) | -842 (151) | 6,03 / 6,37 |
| Oráculo, h = 5 | -764 (238) | -884 (165) | 6,03 / 6,37 |
| Histograma, h = 30 | -1057 (263) | -1110 (185) | 6,03 / 6,37 |
| Oráculo, h = 30 | -1061 (266) | -1156 (197) | 6,03 / 6,37 |

Pierden todas, y el oráculo pierde igual que el histograma: no es un problema de detección. El detector por bloques pierde menos solo porque opera menos. La causa está en el diagnóstico de `idea14.txt`. En la fase D de la banda 40, el salto más el primer minuto vale **-1,40 niveles (ee 0,24) cuando la banda está en caja** y +1,42 (ee 0,35) cuando está invertida. Lo mismo pasa en las dos validaciones: -1,10 y -1,56 en caja, +2,33 y +1,49 invertida. La banda queda en caja cuando el precio está alto en el rango de la ventana. Desde ahí el precio tiende a bajar también a través del salto, y esa estructura de la ventana normalizada pesa más que el +0,37 promedio del salto. Los saltos favorables ya los pasa la banda cuando está invertida.

**Detección en la placa.** Un hilo lleva un contador c que da la vuelta en 390 (sumar 1 y comparar con 390, sin dividir) y no necesita multiplicar, dividir ni desplazar.

- **Detector por histograma** (`DetectorHistograma`). En cada tick suma |p(n) - p(n - 1)| al casillero c y, con una comparación, lleva el casillero con más suma. Ese casillero es la fase del salto. El primer salto que predice llega en el tick 689 en la mediana de las 3600 ventanas (menos de 2 días de mercado), 1386 en el percentil 90 (3,6 días) y 5793 en el peor caso (15 días). Desde el primer acierto predice el 96,0 % de los saltos, y el 95,8 % de sus predicciones son saltos. Cuesta unas 20 instrucciones por tick: leer el precio anterior, valor absoluto sin saltos, cargar, sumar y guardar el casillero, comparar con el máximo y avanzar el contador. Usa 390 contadores de 16 bits, unas 195 palabras de la memoria de 512 (el programa de la regla de los peldaños usa 67).
- **Detector por bloques** (`DetectorBloque`). Guarda la posición del mayor cambio de cada bloque de 390 ticks y fija la fase cuando dos bloques seguidos coinciden. Usa 4 palabras y unas 12 instrucciones por tick. El primer acierto llega en el tick 1354 en la mediana (3008 en el percentil 90 y 7775 en el peor caso), pero después predice solo el 44,5 % de los saltos, porque suelta la fase cada vez que el mayor cambio de un día no es el salto.

Los días con menos de 390 minutos (13 en las cinco empresas, todos de 359 a 389) corren la fase. El detector por bloques la vuelve a fijar en dos días por construcción, y el histograma tarda más porque el casillero viejo tiene la suma acumulada; los porcentajes de arriba ya incluyen esos días.

### 9.5 Primera sola sin la copia `espera_banda40`

Comando: `python3 ref/cotas/explorar_ideas2.py primera --semilla 18` (`primera.txt`). Es el mismo sorteo de 20 000 torneos que la tabla 2, con `espera_banda40` fuera del campo. Los porcentajes difieren en 0,1 de los de `detalle.txt`, que usó otro sorteo.

| Subconjunto | Estrategia | Pts, campo de siempre | 1.ª sola %, campo de siempre | Pts sin la copia | 1.ª sola % sin la copia |
|-------------|------------|-----------------------|------------------------------|------------------|-------------------------|
| Validación años (muestra) | banda 40 | 1,866 | 18,3 | 1,862 | 39,9 |
| | banda 60 | 1,811 | 26,7 | 1,824 | 39,2 |
| | tres bandas por hilo | 1,820 | 34,6 | 1,834 | 47,2 |
| Validación empresas (muestra) | banda 40 | 1,849 | 17,3 | 1,845 | 37,0 |
| | banda 60 | 1,794 | 26,3 | 1,816 | 38,0 |
| | tres bandas por hilo | 1,803 | 36,2 | 1,820 | 46,0 |
| Población completa, todas | banda 40 | 1,859 | 16,7 | 1,852 | 35,9 |
| | banda 60 | 1,817 | 25,7 | 1,825 | 37,9 |
| | tres bandas por hilo | 1,815 | 32,0 | 1,823 | 42,9 |
| Población, validación años | banda 40 | 1,876 | 18,6 | 1,874 | 40,1 |
| | banda 60 | 1,824 | 27,3 | 1,838 | 40,0 |
| | tres bandas por hilo | 1,830 | 34,0 | 1,846 | 47,6 |
| Población, validación empresas | banda 40 | 1,848 | 17,0 | 1,843 | 35,3 |
| | banda 60 | 1,790 | 25,3 | 1,806 | 35,6 |
| | tres bandas por hilo | 1,798 | 34,3 | 1,811 | 43,1 |

Sin la copia, la banda 40 y la banda 60 quedan primeras solas con la misma frecuencia (35 % a 40 %, con diferencias de -2,0 a +0,7 puntos porcentuales entre ellas), y la banda 40 sigue con más puntos (+0,025 a +0,038). Las tres bandas por hilo quedan primeras solas más veces (43 % a 48 %) y con menos puntos que la banda 40. La pregunta de cuál conviene depende de qué cuente más en la nota, ganar la ronda o el puntaje lineal. La pauta del enunciado reparte la nota de competencia en forma lineal entre el peor grupo y el mejor, y eso es lo que miden los puntos.

### 9.6 Qué cambia para la decisión

Nada de esta tanda agrega una opción a la sección 6. La idea 13 en su mejor versión es la banda 40 (ajuste por empresas) o queda 16 bajo ella (ajuste por años). La idea 14 pierde de 420 a 1160 por ronda en todas sus variantes. La recomendación de la sección 6 (mía, etiquetada como tal) no cambia, y la decisión sigue siendo de Nicolás.

### 9.7 Comandos

| Resultado | Comando | Salida |
|-----------|---------|--------|
| Filtro de la idea 13 | `python3 ref/cotas/explorar_ideas2.py filtro13 --semilla 18` | `filtro13.txt` |
| Idea 13 | `python3 ref/cotas/explorar_ideas2.py idea13 --semilla 18` | `idea13.txt`, `idea13.json` |
| Filtro de la idea 14 y detectores | `python3 ref/cotas/explorar_ideas2.py filtro14 --semilla 18` | `filtro14.txt` |
| Regla de la idea 14 y salto según la posición de la banda | `python3 ref/cotas/explorar_ideas2.py idea14 --semilla 18` | `idea14.txt`, `idea14.json` |
| Primera sola sin la copia | `python3 ref/cotas/explorar_ideas2.py primera --semilla 18` | `primera.txt` |

## 10. Mano a mano contra el rival de Tesla (19/11)

Comando: `python3 ref/cotas/explorar_rival.py mano --semilla 18` (`mano.txt`). El rival de Tesla compra 63 repetido desde el primer 100, vende al ver 220 o más y no vuelve; su patrimonio sale de la caché en C de la población. Los subconjuntos son de la población completa: todas las ventanas y las de validación por años y por empresas. Aquí no se ajusta nada, así que "validación" solo nombra el subconjunto. El caso de cada ventana (S: 100 antes que 255; B: 255 antes que 100) lo informa la corrida de la sección 11. Δ es la diferencia media de patrimonio por ronda (nosotros menos el rival), con su error estándar por grupos de ventanas vecinas. Los torneos de 3 rondas son 20 000 sorteos de tres ventanas del mismo subconjunto y caso, los mismos para las tres estrategias, y comparan la suma de las tres rondas. La diferencia media de esa suma es 3 veces la de la tabla, con 3 veces su error estándar.

| Subconjunto | Caso | Ventanas | Estrategia | Gana % | Empata % | Pierde % | Δ media (ee) | 3 rondas: gana % | empata % | pierde % |
|---|---|---|---|---|---|---|---|---|---|---|
| Población completa | todas | 1 368 253 | banda 40 | 60,6 | 34,0 | 5,4 | +2393 (174) | 93,3 | 4,0 | 2,7 |
| Población completa | todas | 1 368 253 | banda 60 | 62,1 | 28,6 | 9,3 | +2188 (164) | 91,4 | 2,3 | 6,3 |
| Población completa | todas | 1 368 253 | tres bandas por hilo | 66,9 | 19,3 | 13,8 | +2161 (168) | 91,4 | 0,7 | 7,9 |
| Población completa | S | 790 173 | banda 40 | 98,5 | 0,0 | 1,5 | +3908 (198) | 100,0 | 0,0 | 0,0 |
| Población completa | S | 790 173 | banda 60 | 96,8 | 0,0 | 3,1 | +3692 (170) | 99,6 | 0,0 | 0,4 |
| Población completa | S | 790 173 | tres bandas por hilo | 98,2 | 0,0 | 1,8 | +3802 (169) | 100,0 | 0,0 | 0,1 |
| Población completa | B | 578 080 | banda 40 | 8,8 | 80,5 | 10,7 | +322 (148) | 22,8 | 51,4 | 25,8 |
| Población completa | B | 578 080 | banda 60 | 14,6 | 67,6 | 17,8 | +134 (143) | 32,5 | 30,3 | 37,3 |
| Población completa | B | 578 080 | tres bandas por hilo | 24,1 | 45,6 | 30,3 | -82 (137) | 38,9 | 9,2 | 51,9 |
| Validación años | todas | 391 320 | banda 40 | 68,0 | 25,7 | 6,2 | +2790 (357) | 96,7 | 1,7 | 1,6 |
| Validación años | todas | 391 320 | banda 60 | 68,0 | 22,9 | 9,1 | +2533 (322) | 95,0 | 1,3 | 3,8 |
| Validación años | todas | 391 320 | tres bandas por hilo | 75,3 | 11,9 | 12,7 | +2462 (261) | 95,8 | 0,2 | 4,0 |
| Validación años | S | 262 490 | banda 40 | 98,4 | 0,1 | 1,4 | +3902 (369) | 100,0 | 0,0 | 0,0 |
| Validación años | S | 262 490 | banda 60 | 96,4 | 0,1 | 3,5 | +3705 (352) | 99,6 | 0,0 | 0,4 |
| Validación años | S | 262 490 | tres bandas por hilo | 98,1 | 0,1 | 1,8 | +3654 (227) | 99,9 | 0,0 | 0,1 |
| Validación años | B | 128 830 | banda 40 | 6,0 | 78,0 | 16,0 | +524 (519) | 16,0 | 47,2 | 36,8 |
| Validación años | B | 128 830 | banda 60 | 10,2 | 69,4 | 20,5 | +145 (286) | 25,5 | 33,5 | 41,1 |
| Validación años | B | 128 830 | tres bandas por hilo | 29,0 | 36,0 | 35,0 | +33 (301) | 42,8 | 4,6 | 52,5 |
| Validación empresas | todas | 547 338 | banda 40 | 53,7 | 41,2 | 5,1 | +2144 (293) | 89,5 | 7,1 | 3,5 |
| Validación empresas | todas | 547 338 | banda 60 | 53,5 | 36,5 | 9,9 | +1830 (232) | 86,8 | 4,9 | 8,3 |
| Validación empresas | todas | 547 338 | tres bandas por hilo | 61,0 | 24,9 | 14,1 | +1848 (242) | 88,2 | 1,5 | 10,2 |
| Validación empresas | S | 284 347 | banda 40 | 97,0 | 0,0 | 3,0 | +3994 (384) | 99,9 | 0,0 | 0,1 |
| Validación empresas | S | 284 347 | banda 60 | 94,1 | 0,0 | 5,9 | +3457 (252) | 99,0 | 0,0 | 1,0 |
| Validación empresas | S | 284 347 | tres bandas por hilo | 96,1 | 0,0 | 3,9 | +3716 (250) | 99,8 | 0,0 | 0,2 |
| Validación empresas | B | 262 991 | banda 40 | 6,9 | 85,7 | 7,4 | +145 (102) | 17,8 | 63,3 | 18,9 |
| Validación empresas | B | 262 991 | banda 60 | 9,7 | 76,0 | 14,3 | +71 (126) | 24,0 | 44,2 | 31,9 |
| Validación empresas | B | 262 991 | tres bandas por hilo | 22,9 | 51,9 | 25,2 | -171 (141) | 37,6 | 14,0 | 48,4 |

Lectura:

- **Caso S (58 % de la población): le ganamos casi siempre** (94 % a 98,5 % de las ventanas según estrategia y subconjunto, 99 % o más de los torneos de 3 rondas). El rival vende en 220 y no vuelve, y la regla de los peldaños vende en el 255. Las pocas ventanas S que perdemos son de recompras que terminan mal: con la variante (a) de la sección 11 no se pierde ninguna.
- **Caso B (42 %): el rival es casi la misma regla.** Los dos compran en el 100 y venden cerca de 215 a 220, así que la banda 40 empata en el 80 % de las ventanas, gana en el 9 % y pierde en el 11 %, con +322 (ee 148) de media. La banda 60 empata menos (68 %) y queda en +134 (143). Las tres bandas pierden más ventanas de las que ganan (30 % contra 24 %), con -82 (137). En torneos de 3 rondas solo con ventanas B, la banda 40 gana el 23 %, empata el 51 % y pierde el 26 %. La ronda de Tesla del 18/11 fue de este caso.
- **En toda la población** la banda 40 es la que menos pierde contra el rival: 5,4 % de las ventanas y 2,7 % de los torneos de 3 rondas, contra 9,3 % y 6,3 % de la banda 60 y 13,8 % y 7,9 % de las tres bandas. Las tres bandas ganan más ventanas (66,9 %) porque empatan menos.

## 11. Ronda de AMD y variante del caso S (19/11)

### 11.1 Traza de la ronda de AMD

Comando: `python3 ref/cotas/explorar_rival.py amd` (`amd.txt`). Es AMD desde el 10/1/2022 a las 10:20, la ronda que la maestra mostró con 21 895. **Es del caso B**: el primer 255 llega en el tick 1124 y el primer 100 en el 5051, y ahí empieza la fase D. El precio final es 173.

Banda 60 (la regla que corrió el 18/11). Cada fila es una orden ejecutada:

| Tick | Precio | Orden | Caja | Acciones | Patrimonio |
|------|--------|-------|------|----------|------------|
| 5052 | 100 | compra 63 | 3695 | 63 | 9995 |
| 5053 | 101 | compra 36 | 54 | 99 | 10 053 |
| 6191 | 208 | vende 63 | 13 153 | 36 | 20 641 |
| 6192 | 203 | vende 36 | 20 456 | 0 | 20 456 |
| 9170 | 161 | compra 63 | 10 308 | 63 | 20 451 |
| 9171 | 162 | compra 63 | 97 | 126 | 20 509 |

Patrimonio máximo: **24 541 en el tick 12 955**, con precio 194. Termina en 21 895.

**¿La caída desde el máximo vino de una recompra? Sí.** La caída de 2646 es la de las 126 acciones recompradas en 161 y 162 (ticks 9170 y 9171), que la regla mantuvo mientras el precio bajaba de 194 a 173. Después del máximo no hubo ninguna orden: la banda 60 vende con 195 o más y el precio llegó a 194, a un nivel de la venta. Aun así la recompra sumó: sin ella la ronda habría cerrado con 20 456 en caja, y con ella cerró con 21 895. Esta recompra es del caso B, así que la variante de la sección 11.2 no la toca.

Como referencia, la banda 40 vende en 216 (ticks 8230 y 8231), recompra 152 acciones en 140 (ticks 10 964 a 10 966) y llega a un máximo de 29 683 en el mismo tick 12 955. Termina con 26 470. El rival de Tesla vende en 220 (ticks 8371 y 8372), no vuelve a comprar y termina con 21 824.

### 11.2 Variante del caso S

Comando: `python3 ref/cotas/explorar_rival.py casos --semilla 18` (`caso_s.txt`). Código: `ref/cotas/ideas_caso_s.py`. La variante actúa solo en el caso S, después de vender en el 255:

- **(a)** no vuelve a comprar;
- **(b)** vuelve a comprar con un tercio del patrimonio, fijado al momento de la recompra y sin reajustes tick a tick (en las tres bandas, la posición total queda en ese tercio);
- **(c)** recompra todo, que es lo actual.

En el caso B nada cambia. Se probó sobre la banda 40 y las tres bandas, sin ajustar parámetros, en la población completa: 4 corridas nuevas, 49 minutos con 24 núcleos. Comprobación: en la muestra, el modo (c) da lo mismo que la base, con 0 diferencias en 3600 ventanas.

Media, p5 y peor son de las ventanas del caso S; el resto, de todas las ventanas del subconjunto. "Recompra en S" es el porcentaje de ventanas S en que la base vuelve a comprar después del 255. Los puntos y la primera sola son del torneo de 3 rondas de la tabla 2 sin `espera_banda40` (mismo sorteo que `primera.txt`). "Contra el rival" es el mano a mano de la sección 10.

| Subconjunto | Estrategia | Caso S: media | p5 | Peor | Δ contra (c) (ee) | Recompra en S % | Pts sin copia | 1.ª sola % sin copia | Contra el rival: gana / empata / pierde % | Δ contra el rival (ee) | 3 rondas: gana % | Caso S contra el rival: gana / pierde % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Población completa | banda 40, (c) recompra todo | 25668 | 24198 | 14746 | +0 (0) | 12,7 | 1,852 | 35,9 | 60,6 / 34,0 / 5,4 | +2393 (174) | 93,3 | 98,5 / 1,5 |
| Población completa | banda 40, (a) no recompra | 24961 | 24314 | 14746 | -707 (196) | 12,7 | 1,836 | 27,3 | 61,4 / 34,0 / 4,5 | +1985 (118) | 93,8 | 100,0 / 0,0 |
| Población completa | banda 40, (b) recompra 1/3 | 25194 | 24198 | 14746 | -474 (132) | 12,7 | 1,845 | 33,3 | 61,4 / 34,0 / 4,5 | +2119 (129) | 93,9 | 99,9 / 0,0 |
| Población completa | tres bandas por hilo, (c) recompra todo | 25562 | 23709 | 14746 | +0 (0) | 26,6 | 1,823 | 42,9 | 66,9 / 19,3 / 13,8 | +2161 (168) | 91,4 | 98,2 / 1,8 |
| Población completa | tres bandas, (a) no recompra | 24961 | 24314 | 14746 | -601 (167) | 26,6 | 1,811 | 31,8 | 67,9 / 19,3 / 12,8 | +1814 (121) | 91,8 | 100,0 / 0,0 |
| Población completa | tres bandas, (b) recompra 1/3 | 25067 | 23401 | 14746 | -495 (141) | 26,6 | 1,810 | 38,8 | 67,7 / 19,3 / 13,0 | +1875 (129) | 91,7 | 99,5 / 0,4 |
| Validación años | banda 40, (c) recompra todo | 25556 | 23684 | 14746 | +0 (0) | 15,3 | 1,874 | 40,1 | 68,0 / 25,7 / 6,2 | +2790 (357) | 96,7 | 98,4 / 1,4 |
| Validación años | banda 40, (a) no recompra | 24812 | 24218 | 14746 | -743 (359) | 15,3 | 1,854 | 27,8 | 69,0 / 25,7 / 5,3 | +2292 (237) | 97,1 | 99,9 / 0,0 |
| Validación años | banda 40, (b) recompra 1/3 | 25081 | 23772 | 14746 | -474 (230) | 15,3 | 1,865 | 37,2 | 68,9 / 25,7 / 5,3 | +2472 (260) | 97,0 | 99,8 / 0,1 |
| Validación años | tres bandas por hilo, (c) recompra todo | 25308 | 23167 | 14746 | +0 (0) | 29,6 | 1,846 | 47,6 | 75,3 / 11,9 / 12,7 | +2462 (261) | 95,8 | 98,1 / 1,8 |
| Validación años | tres bandas, (a) no recompra | 24812 | 24218 | 14746 | -495 (219) | 29,6 | 1,835 | 33,1 | 76,5 / 11,9 / 11,5 | +2130 (198) | 96,2 | 99,9 / 0,0 |
| Validación años | tres bandas, (b) recompra 1/3 | 25048 | 23628 | 14746 | -260 (138) | 29,6 | 1,837 | 44,8 | 76,4 / 11,9 / 11,6 | +2288 (221) | 96,2 | 99,7 / 0,2 |
| Validación empresas | banda 40, (c) recompra todo | 25745 | 23714 | 17301 | +0 (0) | 17,1 | 1,843 | 35,3 | 53,7 / 41,2 / 5,1 | +2144 (293) | 89,5 | 97,0 / 3,0 |
| Validación empresas | banda 40, (a) no recompra | 24946 | 24198 | 18644 | -799 (382) | 17,1 | 1,828 | 26,5 | 55,3 / 41,2 / 3,6 | +1729 (170) | 90,7 | 100,0 / 0,0 |
| Validación empresas | banda 40, (b) recompra 1/3 | 25205 | 23952 | 18893 | -541 (259) | 17,1 | 1,838 | 32,7 | 55,2 / 41,2 / 3,6 | +1863 (197) | 90,7 | 100,0 / 0,0 |
| Validación empresas | tres bandas por hilo, (c) recompra todo | 25468 | 22808 | 16853 | +0 (0) | 42,1 | 1,811 | 43,1 | 61,0 / 24,9 / 14,1 | +1848 (242) | 88,2 | 96,1 / 3,9 |
| Validación empresas | tres bandas, (a) no recompra | 24946 | 24198 | 18644 | -522 (246) | 42,1 | 1,804 | 30,7 | 63,0 / 24,9 / 12,1 | +1577 (181) | 89,4 | 100,0 / 0,0 |
| Validación empresas | tres bandas, (b) recompra 1/3 | 25057 | 23004 | 19082 | -411 (194) | 42,1 | 1,799 | 39,3 | 62,6 / 24,9 / 12,5 | +1635 (198) | 89,1 | 99,2 / 0,8 |

Lectura:

- **(a) y (b) bajan la media del caso S en todos los subconjuntos.** Con la banda 40, (a) pierde -707 (ee 196) en la población, y -743 (359) y -799 (382) en las dos validaciones; (b) pierde -474 (132), -474 (230) y -541 (259). Con las tres bandas, (a) pierde de -495 a -601 y (b) de -260 a -495.
- **La recompra pasa poco y vale mucho.** La banda 40 recompra en el 12,7 % a 17,1 % de las ventanas S. Dividiendo la diferencia entre (c) y (a) por esa fracción, cada recompra vale en promedio entre +4700 y +5600 por ronda.
- **Lo que ganan (a) y (b).** Con (a) el percentil 5 del caso S sube un poco (24 314 contra 24 198 en la población; 24 218 contra 23 684 en la validación por años), y en la validación por empresas el peor caso pasa de 17 301 a 18 644. Además nunca perdemos contra el rival en el caso S (100 % contra 98,5 %), las ventanas perdidas contra el rival bajan de 5,4 % a 4,5 %, y los torneos de 3 rondas ganados contra el rival suben de 93,3 % a 93,8 %. El peor caso de la población (14 746) es el mismo en las tres versiones.
- **Lo que pierden.** Puntos de torneo: banda 40 (c) 1,852, (b) 1,845, (a) 1,836 en la población, con el mismo orden en las dos validaciones. Primera sola: 35,9 %, 33,3 % y 27,3 %. Parte de la caída de (a) en primeros lugares es otro empate: la regla `espera` del campo (sin banda en la fase D) hace en el caso S exactamente lo mismo que (a).
- En la ronda de AMD, que es del caso B, las tres versiones dan lo mismo.

Placa: (a) es un bit que recuerda que el 100 llegó primero y bloquea la compra en D, unas 3 instrucciones. (b) calcula una sola vez, al recomprar, el patrimonio dividido por 3p (una división por restas, de 60 a 80 instrucciones) y después va hacia ese número de acciones con órdenes de hasta 63. Ninguna necesita RTL.

**Opciones, sin decidir:** (c) es lo actual y tiene la mejor media, los mejores puntos y la mayor primera sola. (a) sacrifica de 700 a 800 de media en el caso S (de 400 a 500 por ronda sobre todas las ventanas) a cambio de no perder nunca contra el rival en el caso S y de un percentil 5 algo más alto. (b) queda entre las dos. **Recomendación (mía, etiquetada como tal): mantener (c).** Las ventajas de (a) son chicas y la pérdida en media y en puntos aparece en los tres subconjuntos. La decisión es de Nicolás.

### 11.3 Comandos

| Resultado | Comando | Salida |
|-----------|---------|--------|
| Mano a mano contra el rival de Tesla | `python3 ref/cotas/explorar_rival.py mano --semilla 18` (corre la población si falta, unos 50 minutos) | `mano.txt` |
| Traza de la ronda de AMD | `python3 ref/cotas/explorar_rival.py amd` | `amd.txt` |
| Variante del caso S | `python3 ref/cotas/explorar_rival.py casos --semilla 18` | `caso_s.txt` |


## 12. Política por régimen filtrado (19/11)

Diseño de Nicolás ("Último intento: política por régimen filtrado"), encargo de su sección 11. La tesis: como la maestra normaliza con el mínimo y el máximo de toda la ronda, la volatilidad en niveles por tick, v = 155 s / R, medida en los primeros ticks revela cuántas volatilidades de un minuto mide el rango que la ventana va a recorrer. Con v bajo la ventana tendría que ser de tendencia; con v alto, de vaivén. La política es la banda 40 más tres módulos: D (bandas según caso, clase y tramo en la fase D), A (entrada temprana por ruptura en la fase A) y E (orden condicionada a los bits del precio que llega). Solo Python; no se tocó `rtl/`, `sw/`, `main` ni los bitstreams. Decisiones de Nicolás del 19/11: lista de acciones aprobada, módulo D con c2 y k compartidos entre casos (10 parámetros, 14 con el A), ajuste desde la banda 40 moviendo un parámetro a la vez, N en {33, 63}, el módulo A como principal y el D descartado si F1 pasa solo en las fases A a C.

### 12.0 Resumen

- **F1 pasa en las fases A a C y no en la D**, en las otras acciones, en las cinco empresas y en paseos aleatorios normalizados. El efecto sale de la normalización (los paseos lo muestran sin ningún mercado detrás), así que estaría igual en las series de la competencia. En la fase D el precio revierte en todas las clases y la clase no distingue nada: **el módulo D se descarta**.
- **F2 pasa con holgura.** Partiendo del primer máximo nuevo de 220 o más en la fase A, con clase 0 el 255 llega antes de caer 16 niveles en el 85,7 % de las ventanas de las otras acciones, 29,6 puntos sobre lo que daría un paseo sin memoria (ee 1,5).
- **F3 no pasa.** Decidir con el precio completo valdría +242 por ronda en las cinco y +291 en las otras, pero con la restricción de bits la orden condicional pierde. **El módulo E no se construye.**
- **Con los módulos apagados, la política decide igual que la banda 40** en toda la población de las cinco (27 365 millones de decisiones por regla) y en la muestra de las otras: 0 diferencias.
- **Módulo A ajustado en las otras acciones:** kA 1, θA 220, d 24, N 63. Validación interna: +92 (ee 27) por años y +107 (ee 26) por grupos contra la banda 40.
- **Examen final en las cinco (una sola vez):** +60 (ee 30) en la población, +146 (ee 49) en la validación por empresas y +11 (ee 76) en la de años. Gana en el caso B (+246, ee 56) y pierde en el S (-76, ee 26).
- **El criterio de la sección 9 del diseño no se cumple en ninguno de sus tres puntos** (por poco en el 1 y el 3). Según esa misma sección, compite la banda 40.

### 12.1 Datos: las otras acciones

- **Lista** (`tools/datos/otras_acciones.txt`, `tools/datos/candidatas.py`): 198 candidatas grandes que cotizaron todo 2020 a 2024 sin cambio de símbolo, fusión ni escisión conocida; en cada uno de cinco grupos de sectores (tecnología y comunicaciones, financiero, salud, consumo, e industria con energía, materiales, servicios básicos e inmobiliario; asignación propia cercana a GICS) las 20 de mayor monto transado mediano en enero de 2020, más dos suplentes.
- **Descarga** (`tools/datos/alpaca.py`): 110 acciones (las 100 y las suplentes), 2 de enero de 2020 a 31 de diciembre de 2024, feed SIP, ajuste por splits, 4 hilos con tope común de 190 llamadas por minuto (el límite de la cuenta es 200), unos 45 minutos, 1,9 GB fuera del repositorio. Sin fallas.
- **Suplentes.** La receta de sesión (un precio por minuto de 9:30 a 15:59, sin los días con menos de 200 minutos con operaciones) le deja a BKNG 848 de 1258 días: por su precio alto tiene minutos sin operaciones, y los días descartados empalman días no consecutivos (avisó un salto falso de +29 %). REGN queda con 1206 y BLK con 1219; las demás, con 1245 o más. Regla aplicada: una elegida falla si le quedan menos del 98 % de los días, y entra la primera suplente de su grupo. BKNG por EL, REGN por HCA, BLK por ICE. La receta no se cambió.
- **Saltos entre días sobre 25 %** (todos reales): ROKU, INTC, BIIB, SNAP (resultados o noticias) y el desplome del petróleo del 9/3/2020 (OXY, SLB, COP, EOG).
- **Muestra:** 24 ventanas por acción y año de inicio (12 000), con inicios en múltiplos de 97 minutos para sacar los rivales de la caché en C con ese paso. Validación interna por años (ajuste: inicio en 2020 a 2022; validación: inicio en 2023 o 2024) y por grupos (ajuste: financiero, salud e industria; validación: tecnología y consumo, los sectores de las cinco).
- **Error estándar** por grupos de ventanas: bloques de 20 y 60 días hábiles de la fecha de inicio, con todas las empresas juntas porque comparten fechas, y en las otras acciones también en dos sentidos (fecha y empresa); se usa el mayor.
- **Sesgo de supervivencia:** todas las acciones existen hoy, igual que las cinco. Por eso F2 se informa también por año de inicio (2022 fue año de caída).

### 12.2 Filtros

Reglas fijadas en la bitácora antes de correrlos. F1 pasa en un grupo de fases si en los tres K (1000, 2000 y 4000) y los dos h (390 y 1950) la persistencia de la clase 0 supera a la de la clase 3 por más de 2 ee; en D y en "todas" además deben crecer los cruces (b). Decide el conjunto de las otras acciones. Clases con los umbrales del diseño (v² < 1/4, 1/2, 1): en las otras, clase 0 de 4,7 % a 6,9 % y clase 3 de 20 % a 21 %; en las cinco, 7,5 % a 9,9 % y 10,5 % a 12,7 %.

**F1 (c): persistencia de la clase 0 menos la de la clase 3** (entre paréntesis, t). Cada celda da K = 1000 / 2000 / 4000.

| Conjunto | Fases | h = 390 | h = 1950 | Veredicto |
|---|---|---|---|---|
| Otras acciones | A a C | +0,092 (5,0) / +0,095 (4,7) / +0,106 (5,2) | +0,326 (18,5) / +0,363 (17,8) / +0,395 (19,8) | pasa |
| Otras acciones | D | +0,010 (0,5) / +0,007 (0,3) / -0,001 (0,0) | -0,057 (-1,5) / -0,074 (-2,0) / -0,104 (-1,9) | no pasa |
| Cinco empresas | A a C | +0,066 (3,2) / +0,061 (2,4) / +0,064 (2,1) | +0,237 (5,4) / +0,231 (4,6) / +0,278 (4,7) | pasa |
| Cinco empresas | D | -0,071 (-1,4) / -0,051 (-0,9) / -0,107 (-2,3) | +0,001 (0,0) / +0,001 (0,0) / +0,048 (0,5) | no pasa |
| Paseos normalizados | A a C | +0,221 (9,8) / +0,272 (28,4) / +0,193 (2,6) | +0,502 (4,8) / +0,651 (63,5) / +0,762 (6,8) | pasa |

- **(a)** La correlación de v² de los ticks 1 a K con v² del resto de la ventana va de 0,64 a 0,69 en las otras y de 0,70 a 0,77 en las cinco (0,99 en los paseos, que tienen volatilidad constante).
- **(b)** Los cruces de 140/215 en D crecen con la clase en las otras (K = 2000: 0,05, 0,08, 0,23 y 0,56 por ventana). En las cinco no crecen estrictamente con K = 4000 (0,06 en la clase 0 y 0,05 en la 1), así que allí "todas las fases" no pasa.
- **En la fase D la persistencia es negativa en todas las clases** (de -0,02 a -0,29): el precio revierte, como en toda la exploración, y la clase no separa nada.
- **Por caso:** en las otras, S y B pasan en A a C (S: +0,065 a +0,074 con h = 390, t 4,3 a 5,6; B: +0,120 a +0,140, t 6,3 a 9,3) y ninguno en D. En las cinco, B pasa en A a C y S no (h = 390: +0,024 a +0,043, t 0,6 a 1,5).

**F2: primer máximo nuevo de 220 o más en la fase A desde t = 390, d = 16.** Tasa de ver 255 antes de caer d, y exceso sobre la base d / (255 - p0 + d) en puntos porcentuales (ee).

| Conjunto | Clase 0 | Clases 0 y 1 | Clase 3 | Celdas sobre 2 ee (de 16) |
|---|---|---|---|---|
| Otras acciones | 85,7 %, +29,6 (1,5), 377 ventanas | 69,2 %, +21,5 (1,8), 1690 | 34,2 %, -5,4 (1,9) | 16 y 16 |
| Otras, inicio en 2022 | 82,4 %, +28,4 (5,0), 34 | 66,6 %, +17,9 (4,1), 362 | 37,6 %, -2,8 (5,3) | |
| Cinco empresas | 83,7 %, +18,2 (7,6), 43 | 65,7 %, +19,8 (5,0), 490 | 34,7 %, -8,7 (6,4) | |
| Cinco, inicio en 2022 | 83,3 %, +18,3 (7,8), 42 | 78,2 %, +24,8 (6,3), 238 | 38,6 %, -3,4 (9,9) | |
| Paseos normalizados | (1 ventana) | 75,3 %, +21,7 (2,5), 328 | 31,0 %, -6,0 (2,2) | |

En las otras el exceso de las clases 0 y 1 está entre +17,9 y +26,6 en cada uno de los cinco años de inicio. F2 no se separa por caso S y B como se pidió: ver el 255 antes de caer d hace que la ventana sea del caso B, así que en el caso S la tasa es 0 por construcción. Por eso, para revisar el sesgo de supervivencia, se separa por año de inicio.

**F3: techo del módulo E** (diferencia de patrimonio medio con la banda 40, ee).

| Variante | Cinco empresas (3600 ventanas) | Otras acciones (12 000) |
|---|---|---|
| Decide con p(n) completo (techo) | +242 (55) | +291 (15) |
| Orden condicional armada a 1 nivel del umbral | -90 (35) | -14 (18) |
| Orden condicional armada a 2 niveles | -283 (40) | -140 (31) |

La regla de bits reproduce los casos del diseño (con umbral 100 compra 56 acciones a 104 y 48 a 116, y mantiene a 128; con umbral 255 vende 63 a 254 y 0 a 191, y mantiene a 127). Con o sin comisión por cantidad 0 da lo mismo: en estas ventanas no salió ninguna orden de cantidad 0. No separé de dónde sale la pérdida. La explicación más probable es que la condición por bits deja pasar órdenes antes del umbral (con umbral 140, compra completa a 141 y 62 acciones a 142), y que eso cuesta más de lo que se gana al ver el precio un tick antes.

### 12.3 Política y equivalencia

`ref/cotas/regimen.py` implementa las variables de la sección 3 (S2 con la diferencia acotada a 15 y una tabla de 16 cuadrados; la clase comparando t con 4 S2, 2 S2 y S2 armados con sumas; histéresis de 64 ticks; tramo) y la política de la sección 4, con enteros, sumas, comparaciones y tablas. Al entrar a la fase D se vende en el caso S y se compra en el B, como la banda 40 (son certezas que ningún módulo toca). Equivalencia (`regimen_equivalencia_cinco.txt`, `regimen_equivalencia_otras.txt`): la banda 40, la política con los módulos apagados y la política con el módulo D en su punto neutro (140/215 en toda la tabla) deciden lo mismo en los 20 000 ticks de las 1 368 253 ventanas de las cinco y de las 12 000 de las otras. 0 diferencias.

### 12.4 Ajuste del módulo A y validación interna

Grilla de 64 (kA en {0, 1}, θA en {180, 200, 220, 235}, d en {8, 12, 16, 24}, N en {33, 63}), elección por puntos de torneo de 3 rondas en la parte de ajuste. Las dos separaciones y el ajuste con todas las otras eligen kA 1, θA 200 o 220, d 24, N 63, y las cinco mejores de cada ajuste están en kA 1, θA 200 a 220, d 16 a 24: una meseta. Parámetros finales (ajuste con todas las otras): **kA 1, θA 220, d 24, N 63**. Comprobaciones: la banda 40 en Python y `espera_banda40` en C dan lo mismo en las 12 000 ventanas.

| Parte | Estrategia | Ventanas | Pts sin copia | 1.ª sola % | Media | p5 | Peor | Órdenes | Δ con banda 40 (ee) | A dispara / tope % | Contra el rival: gana / empata / pierde % | Δ con el rival (ee) | 3 rondas: gana / pierde % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Ajuste años | banda 40 | 7200 | 1,851 | 38,9 | 21433 | 10813 | 9405 | 3,8 | +0 (0) | 0,0 / 0,0 | 57,5 / 35,2 / 7,3 | +2413 (153) | 91,9 / 3,9 |
| Ajuste años | banda 40 + A(kA 1, theta 200, d 24, N 63) | 7200 | 1,859 | 47,5 | 21536 | 10970 | 8317 | 4,2 | +103 (37) | 16,9 / 4,5 | 68,5 / 21,5 / 10,0 | +2516 (127) | 95,2 / 3,8 |
| Validación años | banda 40 | 4800 | 1,829 | 35,8 | 21109 | 10680 | 8490 | 3,7 | +0 (0) | 0,0 / 0,0 | 57,7 / 36,0 / 6,2 | +2288 (114) | 92,1 / 3,1 |
| Validación años | banda 40 + A(kA 1, theta 200, d 24, N 63) | 4800 | 1,837 | 44,5 | 21201 | 10791 | 7714 | 4,1 | +92 (27) | 17,7 / 5,2 | 69,0 / 21,7 / 9,3 | +2380 (114) | 95,3 / 3,7 |
| Ajuste grupos | banda 40 | 7200 | 1,840 | 38,0 | 21328 | 10795 | 8490 | 3,8 | +0 (0) | 0,0 / 0,0 | 57,7 / 35,3 / 7,1 | +2365 (113) | 91,8 / 3,7 |
| Ajuste grupos | banda 40 + A(kA 1, theta 220, d 24, N 63) | 7200 | 1,846 | 45,8 | 21399 | 10935 | 8490 | 4,1 | +72 (18) | 14,4 / 3,3 | 67,8 / 23,0 / 9,2 | +2436 (103) | 95,2 / 3,6 |
| Validación grupos | banda 40 | 4800 | 1,840 | 37,6 | 21267 | 10677 | 9465 | 3,8 | +0 (0) | 0,0 / 0,0 | 57,5 / 35,9 / 6,7 | +2361 (141) | 91,7 / 3,7 |
| Validación grupos | banda 40 + A(kA 1, theta 220, d 24, N 63) | 4800 | 1,849 | 47,0 | 21374 | 10888 | 7714 | 4,1 | +107 (26) | 16,8 / 3,1 | 70,1 / 21,5 / 8,4 | +2468 (131) | 95,8 / 3,3 |

### 12.5 Examen final en las cinco empresas

Una sola corrida con los parámetros fijos, en la población completa (`regimen_examen.txt`). El error estándar es por grupos de ventanas vecinas (empresa y bloque de 20 días de inicio), como en las secciones 10 y 11. Los torneos de 3 rondas contra el rival usan los mismos sorteos para las dos estrategias y que la sección 10. La primera versión del reporte usaba sorteos distintos por estrategia; se corrigió y se rehízo el reporte desde la caché, sin volver a evaluar ni tocar los parámetros. Con sorteos distintos la banda 40 perdía 2,8 % de los torneos contra el rival y el módulo A 2,9 %; con los mismos sorteos, 2,7 % y 2,8 %.

| Subconjunto | Caso | Estrategia | Ventanas | Pts sin copia | 1.ª sola % | Media | p5 | Peor | Órdenes | Δ con banda 40 (ee) | A dispara / tope % | Contra el rival: gana / empata / pierde % | Δ con el rival (ee) | 3 rondas: gana / pierde % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Población | todas | banda 40 | 1368253 | 1,852 | 35,6 | 21289 | 10578 | 8948 | 3,8 | +0 (0) | 0,0 / 0,0 | 60,6 / 34,0 / 5,4 | +2393 (174) | 93,3 / 2,7 |
| Población | todas | banda 40 + módulo A | 1368253 | 1,856 | 43,6 | 21349 | 10699 | 8622 | 4,1 | +60 (30) | 15,6 / 4,0 | 70,6 / 21,7 / 7,7 | +2453 (168) | 96,2 / 2,8 |
| Población | S | banda 40 | 790173 | 1,992 | 53,1 | 25668 | 24198 | 14746 | 4,6 | +0 (0) | 0,0 / 0,0 | 98,5 / 0,0 / 1,5 | +3908 (198) | 100,0 / 0,0 |
| Población | S | banda 40 + módulo A | 790173 | 1,986 | 52,5 | 25592 | 22480 | 14746 | 4,6 | -76 (26) | 2,7 / 2,7 | 97,9 / 0,0 / 2,1 | +3832 (201) | 99,9 / 0,1 |
| Población | B | banda 40 | 578080 | 1,297 | 1,2 | 15303 | 10152 | 8948 | 2,7 | +0 (0) | 0,0 / 0,0 | 8,8 / 80,5 / 10,7 | +322 (148) | 22,8 / 25,8 |
| Población | B | banda 40 + módulo A | 578080 | 1,350 | 2,7 | 15548 | 10236 | 8622 | 3,3 | +246 (56) | 33,1 / 5,8 | 33,3 / 51,4 / 15,3 | +567 (157) | 62,3 / 24,2 |
| Validación años | todas | banda 40 | 391320 | 1,870 | 40,2 | 22422 | 11214 | 9472 | 3,9 | +0 (0) | 0,0 / 0,0 | 68,0 / 25,7 / 6,2 | +2790 (357) | 96,7 / 1,6 |
| Validación años | todas | banda 40 + módulo A | 391320 | 1,867 | 45,1 | 22433 | 11460 | 8622 | 4,3 | +11 (76) | 14,8 / 5,9 | 75,3 / 15,9 / 8,9 | +2802 (337) | 97,8 / 1,9 |
| Validación años | S | banda 40 | 262490 | 1,993 | 56,4 | 25556 | 23684 | 14746 | 4,6 | +0 (0) | 0,0 / 0,0 | 98,4 / 0,1 / 1,4 | +3902 (369) | 100,0 / 0,0 |
| Validación años | S | banda 40 + módulo A | 262490 | 1,981 | 55,3 | 25401 | 21835 | 14746 | 4,7 | -155 (69) | 5,3 / 5,3 | 96,7 / 0,1 / 3,2 | +3747 (382) | 99,9 / 0,1 |
| Validación años | B | banda 40 | 128830 | 1,165 | 0,5 | 16036 | 10323 | 9472 | 2,7 | +0 (0) | 0,0 / 0,0 | 6,0 / 78,0 / 16,0 | +524 (519) | 16,0 / 36,8 |
| Validación años | B | banda 40 + módulo A | 128830 | 1,231 | 1,9 | 16386 | 10484 | 8622 | 3,4 | +350 (158) | 34,2 / 7,0 | 31,6 / 48,0 / 20,4 | +874 (535) | 61,6 / 27,1 |
| Validación empresas | todas | banda 40 | 547338 | 1,845 | 35,6 | 20372 | 10422 | 9372 | 3,7 | +0 (0) | 0,0 / 0,0 | 53,7 / 41,2 / 5,1 | +2144 (293) | 89,5 / 3,5 |
| Validación empresas | todas | banda 40 + módulo A | 547338 | 1,860 | 45,1 | 20519 | 10620 | 8622 | 4,0 | +146 (49) | 17,9 / 3,1 | 67,2 / 25,6 / 7,2 | +2291 (283) | 95,2 / 3,3 |
| Validación empresas | S | banda 40 | 284347 | 1,986 | 55,5 | 25745 | 23714 | 17301 | 4,8 | +0 (0) | 0,0 / 0,0 | 97,0 / 0,0 / 3,0 | +3994 (384) | 99,9 / 0,1 |
| Validación empresas | S | banda 40 + módulo A | 284347 | 1,983 | 55,2 | 25705 | 22723 | 17301 | 4,8 | -40 (27) | 1,6 / 1,6 | 97,0 / 0,0 / 3,0 | +3954 (386) | 99,9 / 0,1 |
| Validación empresas | B | banda 40 | 262991 | 1,341 | 0,9 | 14563 | 10150 | 9372 | 2,4 | +0 (0) | 0,0 / 0,0 | 6,9 / 85,7 / 7,4 | +145 (102) | 17,8 / 18,9 |
| Validación empresas | B | banda 40 + módulo A | 262991 | 1,419 | 2,5 | 14911 | 10214 | 8622 | 3,2 | +348 (90) | 35,6 / 4,8 | 34,9 / 53,3 / 11,8 | +493 (136) | 66,7 / 18,4 |

Lectura:

- **Dónde gana y dónde pierde.** En el caso B (el 255 antes que el 100) el módulo A compra en la fase A en un tercio de las ventanas y sube la media +246 (ee 56) en la población. En el caso S dispara en 1,6 % a 5,3 % de las ventanas y siempre termina en el tope (el 100 llega antes que el 255, así que la ruptura falla por construcción): -76 (ee 26) en la población. El percentil 5 del caso S baja de 24 198 a 22 480 y el peor caso general, de 8948 a 8622.
- **Contra el rival de Tesla.** En el caso B pasa de ganar 22,8 % de los torneos de 3 rondas a 62,3 %, porque el rival y la banda 40 hacen casi lo mismo en la fase A (esperar) y el módulo los separa. En toda la población gana más torneos (96,2 % contra 93,3 %) y pierde un poco más (2,8 % contra 2,7 %).
- **Primera sola** sube de 35,6 % a 43,6 % en la población y de 5 a 10 puntos en las dos validaciones.
- **La validación por años** (ventanas enteras en 2024) es la débil: +11 (ee 76) y 1,867 puntos contra 1,870. En 2024 el módulo disparó en 14,8 % de las ventanas y cortó por tope en 5,9 %, el doble que en la validación por empresas (3,1 %).
- **Comparado con lo esperado.** En las otras acciones el módulo daba +72 a +107 por ventana, y en las cinco +60 en la población. Es menos que lo que el diseño estimaba (1 % a 3 % por ronda, unos 200 a 600) y el error estándar es de la mitad del efecto.

### 12.6 Criterio de la sección 9 del diseño

| Punto | Banda 40 + módulo A | Se cumple |
|---|---|---|
| 1. Más puntos de torneo que la banda 40, sin la copia `espera_banda40`, en las dos validaciones | Años: 1,867 contra 1,870. Empresas: 1,860 contra 1,845 | no (falla en años) |
| 2. Diferencia de patrimonio medio con la banda 40 mayor que 1 ee | Años: +11 (ee 76). Empresas: +146 (ee 49). Población: +60 (ee 30) | no (falla en años) |
| 3. No pierde contra el rival de Tesla en más torneos de 3 rondas que la banda 40 (población) | 2,8 % contra 2,7 % | no (por 0,1 puntos) |

Los módulos D y E quedaron fuera en sus filtros y no tienen examen.

### 12.7 Instrucciones por tick de cada hilo

Estimación contando instrucciones de RV32E sin desplazamientos ni multiplicación (la ALU de competencia no desplaza), para la política que quedó en pie: la banda 40 más el módulo A. No está escrita en `sw/`: es un conteo a mano.

| Hilo | Rol | Trabajo por tick | Instrucciones, peor caso |
|---|---|---|---|
| 0 | Corredor | Lee `PRICE` y publica precio y número de tick (4); fases A a D, caso y pmáx (unas 12); banda 40 en D (6); módulo A: espera la clase del tick, compara clase, p con pmáx y con θA, guarda la entrada y arma la orden, o compara con el tope (unas 15); escribe `DECISION` (1) | unas 40 |
| 1 | Régimen | Diferencia, valor absoluto y tope en 15 (6); dirección en la tabla de cuadrados con dos sumas, carga y suma a S2 (5); t y precio anterior (2); clase cruda con 2 S2 y 4 S2 por sumas y tres comparaciones (hasta 9); histéresis (hasta 6); publica clase y tick (2) | unas 33 |
| 2 | Política | Sin el módulo D no tiene tabla que leer. Puede quedar libre o recalcular la banda 40 como control | 0 a 20 |
| 3 | Reloj y centinela | t, precio entre 100 y 255, no más de 20 000 ticks, modo seguro (unas 10); el histograma del día (20) ya no lo usa ningún módulo | 10 a 30 |

Todo cabe: el tope es de unas 565 instrucciones por hilo a 0,1 ms. El camino de la respuesta es el del hilo 0 esperando la clase del hilo 1 del mismo tick: unas 3 + 33 + 15 instrucciones de cada hilo, unos 200 a 250 ciclos en el barrel de 4 hilos, contra 1131 ciclos que pide la puerta (la mitad de 2262). Memoria: 16 palabras de cuadrados y 4 parámetros (kA, θA, d, N) en la tabla de BRAM, que se pueden cambiar con `icebram`. S2 llega a lo más a 20 000 × 225 = 4,5 millones: cabe en 32 bits. Sin hardware nuevo.

Dos advertencias para cuando se escriba:

- **Para que `make equiv` dé igual que `regimen.py`, el hilo 0 tiene que usar la clase del mismo tick**, porque la referencia actualiza la clase con p(n) antes de decidir. Con la clase del tick anterior, las decisiones cambiarían en los ticks en que la clase cambia. La forma simple es esperar la clase con el número de tick actual y, si no llega a tiempo, decidir con la banda 40 (la regla de degradación).
- **Toda la política cabe en un solo hilo** (unas 75 instrucciones) y decidiría lo mismo. Los hilos no suman ganancia, como ya dice la sección 5 del diseño.

### 12.8 Opciones, sin decidir

| Opción | Qué se gana | Qué se pierde |
|---|---|---|
| **Banda 40** (lo que manda la sección 9 del diseño, porque el criterio no se cumple) | La regla ya probada, sin código nuevo antes del corte del 22/11; mejor percentil 5 en el caso S y mejor peor caso; 0,1 puntos menos de torneos perdidos contra el rival | El efecto del módulo A: +60 (ee 30) por ronda en la población y de 5 a 10 puntos de primera sola. En el caso B, la ventaja contra el rival de Tesla (62 % contra 23 % de torneos ganados) |
| **Banda 40 + módulo A** (kA 1, θA 220, d 24, N 63) | +60 (ee 30) en la población, +146 (ee 49) en la validación por empresas, +92 y +107 en la validación interna de las otras acciones; más primeros lugares; el caso B mucho mejor contra el rival | No cumple el criterio que fijó el propio diseño: en la validación por años no gana (+11, ee 76; 1,867 contra 1,870 puntos). Cuesta en el caso S (-76) y en el peor caso (8622 contra 8948). Hay que escribir los hilos 0 y 1, la referencia exacta y pasar las puertas de R1 y R2 antes del corte |

**Recomendación (mía, etiquetada como tal): competir con la banda 40**, como dice la sección 9 del diseño. El módulo A tiene una base sólida: el filtro F2 es fuerte, sale igual en paseos aleatorios y la elección del ajuste es estable. Pero lo que vale en patrimonio es chico frente a su error (+60 ± 30), no aparece en las ventanas de 2024 y obliga a escribir y verificar código nuevo a tres días del corte. Si se quiere guardar como material de defensa, la conclusión del intento es: la normalización sí filtra el régimen, pero solo en las fases A a C, donde la regla ya está en caja esperando, y lo que se puede sacar de ahí es del orden del ruido de una ronda. La decisión es de Nicolás.

### 12.9 Comandos

| Resultado | Comando | Salida |
|-----------|---------|--------|
| Liquidez y cobertura de las candidatas | `python3 tools/datos/candidatas.py` (pide 4 barras diarias por grupo de 60) | pantalla |
| Descarga de las otras acciones | `python3 tools/datos/alpaca.py --lista tools/datos/otras_acciones.txt --desde 2020-01-01 --hasta 2024-12-31 --salida $P4_DATOS/otras --procesos 4 --gzip` (unos 45 minutos) | `$P4_DATOS/otras` |
| F1 y F2 | `python3 ref/cotas/explorar_regimen.py filtros --conjunto otras` (y `cinco`, `paseo`) | `filtros_otras.txt`, `filtros_cinco.txt`, `filtros_paseo.txt` |
| F3 | `python3 ref/cotas/explorar_regimen.py f3 --conjunto otras` (y `cinco`) | `f3_otras.txt`, `f3_cinco.txt` |
| Equivalencia con la banda 40 | `python3 ref/cotas/explorar_regimen.py equivalencia --conjunto cinco` (unos 32 minutos) y `--conjunto otras` | `regimen_equivalencia_cinco.txt`, `regimen_equivalencia_otras.txt` |
| Ajuste del módulo A | `python3 ref/cotas/explorar_regimen.py ajuste --sin-d` (unos 14 minutos) | `regimen_ajuste.txt` |
| Examen final | `python3 ref/cotas/explorar_regimen.py examen` (unos 21 minutos) | `regimen_examen.txt` |


## 13. La política óptima del paseo normalizado (19 y 20/11)

Diseño de Nicolás ("Última idea: la política óptima del paseo normalizado"), que reemplaza al módulo A como candidato. Como el efecto de la sección 12 aparece igual en paseos aleatorios normalizados, el juego tiene un modelo exacto: un paseo con volatilidad v por tick condicionado a que su mínimo sea 100 y su máximo 255. Para ese modelo se calcula la política óptima en vez de adivinarla. Solo Python; no se tocó `rtl/`, `sw/`, `main` ni los bitstreams.

Decisiones de Nicolás durante el trabajo: visto bueno a G1; S2/t como estimador base contra la ventana de 2000; ver G2 antes del examen; seguir con V3 log; el punto 3 del criterio pasa a ser "pierde a lo más 10 % de los torneos de 3 rondas contra el rival de Tesla" (decidido antes del examen); guardas en la fase A con una regla de elección fijada por él; un reparto de hilos obligatorio para la factibilidad.

### 13.0 Resumen

- **El modelo calibra.** G1 pasa con S2/t en paseos (2,0 puntos de mayor distancia con el v verdadero, 5,4 con S2/t), en las otras acciones (4,5) y en las cinco (4,0). No hizo falta el factor sobre v.
- **La política óptima en la fase A tiene dos intervalos**: un bloque alto que no llega al 255 y, con v² alto y mucho tiempo por delante, uno bajo. Comprimida cabe en 512 bytes.
- **G2 y G3 pasan en las otras acciones:** V3 log con S2/t gana +299 (ee 73) a la banda 40; la tabla comprimida conserva 98,9 %.
- **La pérdida contra el rival de Tesla sale de las compras de la fase A** con v² de 1/2 a 2. Por la regla de Nicolás se eligió **V3 log con la guarda (b)** (nunca más de media posición en la fase A): en las otras, 1,857 puntos contra 1,842, pierde 3,4 % de los torneos de 3 rondas contra el rival (la banda 40, 3,7 %) y +146 (ee 43); también gana en las dos validaciones internas.
- **Examen en las cinco (una sola vez, segunda mirada):** en la población es la mejor de las tres estrategias: 1,869 puntos contra 1,852 de la banda 40 y 1,856 del módulo A, +124 (ee 77), primera sola 50,8 % contra 35,6 %, y pierde 2,2 % de los torneos contra el rival (banda 40, 2,7 %).
- **El criterio no se cumple en los puntos 1 y 2.** En la validación por años empata con la banda 40 (1,869 contra 1,870 puntos; -7 con ee 179). En la de empresas gana en puntos (1,863 contra 1,845), pero +82 queda bajo su ee de 102. El punto 3 nuevo se cumple (2,2 % contra el tope de 10 %).
- **Por qué:** la ganancia depende de la proporción de casos S. Con la guarda (b), V3 pierde unos 500 por ronda en el caso S y gana unos 1000 en el B, tanto en las otras acciones como en las cinco. El equilibrio está cerca de 66 % de casos S. Las ventanas de las cinco que empiezan en 2023 o 2024 tienen 67 % de casos S; las de las otras acciones en esos mismos años, 56 %.
- **Factibilidad:** cabe con el reparto de hilos pedido (unos 700 ciclos de 1131, tabla de 512 bytes, unos 800 bytes en total). La equivalencia con la referencia es exacta solo con la contabilidad oficial (caja 10 000, comisión 5). Queda preparada la alternativa V1 log con a16 y c, sin contabilidad y de unos 330 ciclos, que no pasó por el examen.
- **Según el criterio no compite.** Opciones y recomendación en 13.10.

### 13.1 El modelo y su verificación

`ref/cotas/paseo_optimo.py`. Paso: gaussiana discretizada en los enteros con varianza exacta v² (con v² = 1/8, discretizar con s = v daría 0,035). Para cada v² en {1/8, 1/4, 3/8, 1/2, 3/4, 1, 3/2, 2} y r de 0 a 19 999, por recurrencia hacia atrás: g_D (no salir de [100, 255]), g_B (tocar 255 sin salir), g_C (tocar 100 sin salir), g_A (tocar los dos sin salir) y h_A (los dos, con el 255 primero). P(255 antes que 100 | fase A) = h_A / g_A. Unos 10 segundos por v² en un núcleo.

- g_D contra paseos de la red simulados en la banda completa: 0,1179 contra 0,1177 (v² = 2, x = 177, r = 6000), 0,3454 contra 0,3435 (v² = 1/2, r = 12 000), con 24 000 paseos.
- Tocar exactamente los dos bordes sin salir es raro en 156 niveles, así que g_A y h_A se probaron con el mismo código en una banda de 100 a 130: g_A 0,0011 contra 0,0011 (ee 0,0002) y del mismo orden en los otros tres casos; h_A / g_A dentro del ruido.
- La prueba completa del cálculo es G1 en paseos con el v verdadero (tabla de 13.2): mayor distancia 2,0 puntos.

Observación hecha antes de ejecutar: el modelo usa la varianza de largo plazo por tick, y S2/t en series redondeadas la sobrestima, porque el redondeo agrega ruido a cada diferencia de un tick y no al largo plazo. En paseos, S2/t da una mediana de 0,75 contra 0,58 verdadera.

### 13.2 G1: calibración

Observaciones en t = 500, 1000, 2000, 4000 y 8000 de cada ventana que sigue en la fase A, con r = 19 999 - t; probabilidad del modelo interpolada en v² entre las tablas vecinas; deciles de la predicha. Pasa si ningún decil cae respecto del anterior en más de 2 ee y ninguno se aleja más de 10 puntos (`optimo_g1.txt`).

| Decil | Otras acciones: predicha / observada (ee) | Cinco empresas: predicha / observada (ee) | Paseos con S2/t: predicha / observada | Paseos con el v verdadero: predicha / observada |
|---|---|---|---|---|
| 1 | 0,018 / 0,022 (0,005) | 0,004 / 0,000 (0,000) | 0,053 / 0,026 | 0,019 / 0,017 |
| 2 | 0,096 / 0,092 (0,011) | 0,042 / 0,041 (0,025) | 0,175 / 0,121 | 0,114 / 0,116 |
| 3 | 0,212 / 0,189 (0,018) | 0,133 / 0,158 (0,053) | 0,290 / 0,252 | 0,241 / 0,261 |
| 4 | 0,328 / 0,292 (0,023) | 0,261 / 0,285 (0,080) | 0,386 / 0,359 | 0,358 / 0,363 |
| 5 | 0,426 / 0,381 (0,025) | 0,386 / 0,363 (0,081) | 0,470 / 0,468 | 0,462 / 0,471 |
| 6 | 0,513 / 0,510 (0,026) | 0,490 / 0,471 (0,079) | 0,548 / 0,570 | 0,559 / 0,571 |
| 7 | 0,608 / 0,622 (0,025) | 0,593 / 0,589 (0,072) | 0,634 / 0,659 | 0,668 / 0,655 |
| 8 | 0,722 / 0,717 (0,021) | 0,714 / 0,707 (0,058) | 0,733 / 0,768 | 0,787 / 0,770 |
| 9 | 0,861 / 0,848 (0,021) | 0,836 / 0,797 (0,066) | 0,847 / 0,901 | 0,909 / 0,897 |
| 10 | 0,976 / 0,953 (0,011) | 0,958 / 0,920 (0,034) | 0,953 / 0,970 | 0,986 / 0,975 |
| Mayor distancia | 4,5 puntos: pasa | 4,0: pasa | 5,4: pasa | 2,0: pasa |

Con S2/t no hizo falta el factor sobre v que permitía el diseño. Las diferencias de 10 ticks (estimador agregado, solo informativo) corrigen el redondeo en los paseos (1,6 puntos), pero en datos reales dejan al modelo demasiado seguro en los deciles altos (otras: 0,927 predicha, 0,842 observada; en las cinco no pasa). La ventana de 2000 da casi lo mismo que S2/t.

### 13.3 Programación dinámica, variantes y forma de la política

Estados (fase, x, r, s), con s la posición que viaja al precio siguiente y s' la que se ejecuta en él; esperanza bajo P(x → y | condición) = K(y - x) g_F'(y, r - 1) / g_F(x, r). Log: E[log(1 - s + s y/x)] más el costo de cambiar (10 / 15 000 por un cambio completo, la mitad por media posición) más E[V(y, r - 1, s')]; lineal: el producto. V1: óptima en la fase A, banda 40 en la D, B invertido y C en caja. V2: óptima en las cuatro fases. V3: V1 con media posición. Para medir la ganancia dentro del modelo se evaluó también la banda 40 en el mismo modelo. 56 tablas en 5 minutos.

Ganancia dentro del modelo, empezando en caja en la fase A con r = 19 999 (diferencia de E[log patrimonio] con la banda 40, en %, para x0 = 140 / 177 / 215):

| v² | V1 | V2 | V3 |
|---|---|---|---|
| 1/8 | 0,04 / 14,20 / 16,82 | 0,04 / 14,22 / 16,88 | 0,04 / 14,20 / 16,82 |
| 1/4 | 1,08 / 11,61 / 15,00 | 1,14 / 11,77 / 15,34 | 1,08 / 11,62 / 15,00 |
| 3/8 | 2,49 / 8,89 / 10,96 | 2,71 / 9,27 / 11,67 | 2,49 / 8,91 / 10,96 |
| 1/2 | 2,98 / 6,21 / 6,52 | 3,59 / 6,91 / 7,70 | 2,99 / 6,25 / 6,54 |
| 3/4 | 2,16 / 2,51 / 1,87 | 4,63 / 4,52 / 4,50 | 2,39 / 2,58 / 1,92 |
| 1 | 5,37 / 2,84 / 1,57 | 11,07 / 7,40 / 6,91 | 5,73 / 3,18 / 1,76 |
| 3/2 | 16,83 / 10,78 / 6,93 | 31,51 / 23,53 / 20,81 | 17,21 / 11,20 / 7,24 |
| 2 | 28,78 / 21,14 / 15,64 | 54,39 / 44,48 / 40,38 | 29,19 / 21,60 / 16,01 |

**Forma de la política en la fase A (paso 8 del encargo): dos intervalos.** Con s = 0 compra en un bloque alto que no llega al 255 (con v² = 1/4 y r = 19 000, de 184 a 250: cerca del 255 queda poco por ganar) y, a veces, en 101, justo antes del 100. Con v² alto y mucho tiempo por delante compra abajo (con v² = 1 y r = 19 000, de 101 a 146) y no arriba: el paseo tiene que ir al 100 y después al 255. Con s = 1 mantiene en bloques algo más anchos (histéresis). En V3 la media posición aparece en los bordes de esos bloques. Compresión por celda (clase de v², tramo de 1250 ticks), del r del medio del tramo: con dos posiciones, 4 bytes (compra si x ≥ alto o x ≤ bajo con s = 0; mantiene si x ≥ salida o x ≤ bajo1 con s = 1; se ignora el corte superior del bloque alto), 512 bytes en la fase A; con tres posiciones, 12 bytes (1536). Con la guarda (b) elegida, en la fase A la posición es solo caja o media y bastan los dos umbrales de "media o más" de cada s: vuelve a 512 bytes, y decide igual que la de 1536 en los 39 424 casos (128 celdas, 2 posiciones, 154 precios).

### 13.4 G2 y G3 en las otras acciones

Reglas fijadas antes de evaluar: variante y objetivo por puntos de torneo en todas las otras acciones con S2/t; la ventana de 2000 reemplaza a S2/t solo si tiene más puntos y gana por más de 1 ee; G2: la elegida completa gana a la banda 40 por más de 2 ee; G3: la comprimida conserva al menos 80 %. Antes de G2, la política apagada decide igual que la banda 40 en la muestra de las otras (0 diferencias en 240 millones de decisiones) y en la población completa de las cinco (0 en 27 365 millones).

| Estrategia (otras acciones, 12 000 ventanas) | Pts sin copia | 1.ª sola % | Media | p5 | Peor | Órdenes | Δ con banda 40 (ee) | Torneos de 3 rondas perdidos contra el rival % |
|---|---|---|---|---|---|---|---|---|
| banda 40 | 1,842 | 37,9 | 21 303 | 10 746 | 8490 | 3,8 | 0 | 3,7 |
| V1 log | 1,852 | 52,9 | 21 643 | 11 579 | 5649 | 7,2 | +339 (72) | 8,7 |
| V1 lineal | 1,852 | 53,0 | 21 648 | 11 502 | 5879 | 7,0 | +345 (71) | 8,3 |
| V2 log | 1,847 | 59,2 | 22 176 | 12 020 | 5639 | 14,0 | +872 (109) | 11,2 |
| V2 lineal | 1,849 | 59,7 | 22 262 | 11 746 | 5886 | 12,6 | +958 (104) | 10,6 |
| **V3 log** | **1,855** | 52,7 | 21 603 | 11 636 | 6122 | 7,9 | **+299 (73)** | 8,2 |
| V3 lineal | 1,852 | 53,0 | 21 651 | 11 508 | 5879 | 7,0 | +348 (71) | 8,3 |
| V3 log, ventana de 2000 | 1,854 | 52,3 | 21 577 | 11 652 | 6202 | 8,6 | +273 (75) | 8,9 |
| V3 log, comprimida | 1,855 | 52,9 | 21 600 | 11 646 | 6156 | 7,9 | +296 (73) | 8,3 |

Elegida V3 log con S2/t (la ventana de 2000 da -26, ee 28). **G2 pasa: +299 (ee 73). G3 pasa: la comprimida conserva 98,9 %.** La de V1 (512 bytes) conserva 96 %. V2 gana tres veces más en media pero tiene menos puntos y pierde más torneos contra el rival.

### 13.5 Diagnóstico, guardas y elección

Todo con la tabla comprimida y la clase de placa. El reparto de hilos pedido calcula la clase con histéresis en el hilo 1, y los cortes geométricos de la grilla son irracionales; antes de evaluar se alineó la referencia con lo que la placa puede hacer: 64 S2 ≥ N_j (t - 1) con N_j = 11, 20, 28, 39, 55, 78 y 111 (cortes redondeados a 1/64, comparados con sumas corridas) e histéresis de 64 ticks. V3 sin guarda se volvió a evaluar así: +312 (ee 75), 1,856 puntos, pierde 8,1 % de los torneos contra el rival (`optimo_guardas.txt`).

**Diagnóstico de V3 sin guarda (otras acciones).** La diferencia de patrimonio se reparte según la fase y la clase de v² del tick en que ocurrió cada cambio (porcentaje del total neto; negativo es pérdida).

| En los 1611 torneos que pierde contra el rival (de 20 000) | antes de 390 | 1/8 | 1/4 | 3/8 | 1/2 | 3/4 | 1 | 3/2 | 2 | total |
|---|---|---|---|---|---|---|---|---|---|---|
| Fase A | 0 | +1 | -1 | -6 | -26 | -16 | -25 | -21 | -13 | **-107** |
| Fase B | 0 | 0 | +3 | +9 | +22 | +10 | +6 | -12 | -9 | +30 |
| Fase C | 0 | 0 | 0 | 0 | -2 | 0 | 0 | 0 | 0 | -2 |
| Fase D | 0 | 0 | 0 | 0 | -2 | -6 | -9 | -3 | +1 | -21 |

| En el 1 % de peores ventanas (120, patrimonio de 5828 a 10 243), resultado propio | antes de 390 | 1/8 | 1/4 | 3/8 | 1/2 | 3/4 | 1 | 3/2 | 2 | total |
|---|---|---|---|---|---|---|---|---|---|---|
| Fase A | 0 | +2 | -15 | -43 | -102 | -28 | +5 | +2 | 0 | **-178** |
| Fase B | 0 | 0 | 0 | 0 | 0 | +29 | +17 | -1 | 0 | +46 |
| Fase C | 0 | -1 | 0 | -1 | -48 | -2 | -1 | 0 | 0 | -52 |
| Fase D | 0 | 0 | +1 | +4 | +21 | +49 | +8 | +2 | 0 | +85 |

La pérdida contra el rival se origina en las compras de la fase A, con v² de 1/2 a 2; la fase B la compensa en parte. Las peores ventanas pierden sobre todo en la fase A con v² de 1/4 a 1/2, y después en la C con v² 1/2 (lo que se pierde entre ver el 255 y vender una posición comprada en A).

**Guardas sobre las compras de la fase A** (solas y combinadas): (a) tope de d niveles bajo la entrada, sin volver a entrar en esa ronda; (b) nunca más de media posición en la fase A; (c) no aumentar la posición con v² en las dos clases más altas.

| V3 log (otras acciones) | Pts sin copia | 1.ª sola % | Media | p5 | Peor | Órdenes | Δ con banda 40 (ee) | 3 rondas perdidas contra el rival % |
|---|---|---|---|---|---|---|---|---|
| banda 40 | 1,842 | 37,9 | 21 303 | 10 746 | 8490 | 3,8 | 0 | 3,7 |
| sin guarda | 1,856 | 53,0 | 21 615 | 11 659 | 5828 | 7,4 | +312 (75) | 8,1 |
| a16 | 1,845 | 49,6 | 21 423 | 10 937 | 8000 | 6,3 | +120 (40) | 5,6 |
| a24 | 1,847 | 50,7 | 21 462 | 11 122 | 7373 | 6,8 | +158 (47) | 6,6 |
| a32 | 1,848 | 51,4 | 21 496 | 11 320 | 5828 | 7,0 | +192 (58) | 7,3 |
| **b** | **1,857** | 51,3 | 21 449 | 11 359 | 7642 | 6,0 | **+146 (43)** | **3,4** |
| c | 1,854 | 52,8 | 21 509 | 11 561 | 5828 | 6,7 | +205 (54) | 6,7 |
| a16+b | 1,845 | 48,6 | 21 358 | 10 938 | 9181 | 5,6 | +55 (22) | 3,8 |
| a24+b | 1,847 | 49,3 | 21 375 | 11 079 | 8651 | 5,8 | +71 (28) | 3,5 |
| a32+b | 1,849 | 49,8 | 21 391 | 11 170 | 7642 | 5,9 | +87 (34) | 3,6 |
| a16+c | 1,846 | 50,0 | 21 406 | 10 937 | 8000 | 6,0 | +103 (33) | 5,3 |
| a24+c | 1,848 | 51,0 | 21 429 | 11 122 | 7373 | 6,3 | +125 (42) | 5,9 |
| a32+c | 1,849 | 51,6 | 21 458 | 11 304 | 5828 | 6,5 | +154 (48) | 6,4 |
| b+c | 1,852 | 51,1 | 21 397 | 11 327 | 7642 | 5,7 | +94 (33) | 3,3 |
| a16+b+c | 1,845 | 48,8 | 21 352 | 10 935 | 8490 | 5,4 | +49 (20) | 3,8 |
| a24+b+c | 1,847 | 49,5 | 21 357 | 11 079 | 8490 | 5,5 | +53 (25) | 3,5 |
| a32+b+c | 1,848 | 50,1 | 21 370 | 11 166 | 7642 | 5,6 | +66 (29) | 3,5 |

**Elegida (regla 1 de Nicolás: más puntos entre las que pierden a lo más 5 %): V3 log con (b)**, 1,857 puntos, pierde 3,4 % de los torneos contra el rival (menos que la banda 40), +146 (ee 43). Validación interna, informativa: +207 (ee 60) en años y +144 (ee 50) en grupos, con 2,6 % y 3,4 % de torneos perdidos contra el rival. Los topes (a) cortan compras que después llegan al 255: bajan puntos y no bajan las pérdidas contra el rival tanto como (b).

### 13.6 Factibilidad en la placa con el reparto de hilos pedido

Reparto obligatorio: hilo 0 corredor (fases, lectura de lo publicado, decisión, única escritura en `DECISION`, banda 40 de respaldo), hilo 1 régimen (S2 y clase con histéresis), hilo 2 política (lee la celda y publica la posición objetivo), hilo 3 reloj y contabilidad (ticks, tramo, caja y acciones propias, cantidad de la próxima orden, supuestos y modo seguro). Es un conteo sobre la referencia, no un programa escrito; la aritmética del hilo 3 está escrita y probada en `ref/cotas/optimo_placa.py`.

**Cantidad de la media posición sin dividir ni multiplicar.** La referencia fija, al pasar a media posición, el objetivo en acciones floor((caja + acc p) / (2 p)), y después va hacia él con órdenes de hasta 63. En la placa: acc p por Horner con duplicaciones (r = r + r por cada bit de acc, y r = r + p si el bit está; los bits se sacan comparando con una tabla de potencias de dos, sin desplazar), y el cociente por restas: se arman 2p, 4p, ..., 2p·2^8 por sumas y se restan de mayor a menor. Con la guarda (b) la media posición solo aparece en la fase A, entrando desde caja, así que en la práctica acc = 0 y queda floor(caja / (2 p)); se deja el cálculo general para que sea exacto en cualquier caso. Prueba exhaustiva contra la aritmética de Python: 0 diferencias en 2 079 480 casos; peor caso, 91 operaciones.

**Contabilidad después de salidas y reentradas.** El hilo 3 repite en cada tick la contabilidad oficial con el byte que la maestra leyó (el que el hilo 0 escribió después del precio anterior y publicó con su número de tick) y el precio que acaba de llegar, que es al que se ejecutó: compra q = min(cantidad, floor((caja - 5) / p)) (el cociente con 6 bits da 63 si es 64 o más), caja -= q p + 5, acc += q; venta q = min(cantidad, acc), caja += q p - 5, acc -= q; una orden que queda en cero no hace nada. Como cada orden se repite así, las salidas y reentradas no necesitan nada especial: la caja y las acciones de la placa son las de la maestra mientras la contabilidad sea la oficial (caja inicial 10 000, comisión 5, el recorte del testbench). Recorte y q p: 37 y 30 operaciones en el peor caso, 0 diferencias en pruebas exhaustivas.

**Instrucciones por tick, peor caso** (variante elegida, V3 log con (b)):

| Hilo | Trabajo | Instrucciones |
|---|---|---|
| 0, corredor | Lee `PRICE` y publica precio y tick (4); fases, caso y pmáx (12); banda 40 de respaldo (6); espera la cantidad del hilo 3 con el tick actual (sondeo); arma el byte: completa "comprar 63", caja "vender 63", media la cantidad del hilo 3 (6); escribe `DECISION` y publica el byte con su tick (3) | unas 35 más el sondeo |
| 1, régimen | Diferencia, valor absoluto y tope en 15 (6); 64 d² desde una tabla de 16 palabras y suma a 64 S2 (4); siete sumas corridas N_j (t - 1) (7); comparaciones de la clase (hasta 14); histéresis (6); publica clase y tick (2) | unas 40 |
| 2, política | Espera clase y fase del tick; dirección de la celda: base de la clase (tabla de 8 punteros), desplazamiento del tramo (lo lleva el hilo 3 restando 4 cada 1250 ticks) y s (sumas) (6); dos cargas (a1, b1) y dos comparaciones (6); fases B, C y D sin tabla (4); guarda (b) (2); publica objetivo y tick (2) | unas 25 |
| 3, reloj y contabilidad | Tick y tramo (5); precio entre 100 y 255 y tick hasta 20 000 (5); repite la orden ejecutada: compra 37 + 30 + 4, venta 30 + 4 (hasta 71); cantidad: media posición nueva 91, si no la diferencia con el objetivo topada en 63 (6); publica cantidad y tick (2) | unas 180 |

Camino de la respuesta: el hilo 3 repite la orden ejecutada mientras los hilos 1 y 2 calculan (en paralelo); en serie quedan la publicación del precio (4), la clase (40), la celda (25), la cantidad (hasta 97) y el byte (9): unas 175 instrucciones de cada hilo, unos 700 ciclos en el barrel de 4 hilos (una instrucción de cada hilo cada 4 ciclos), contra 1131 de la puerta (la mitad de 2262). Cabe, pero sin la holgura de la banda 40 sola (83 a 88 ciclos). El tope por hilo, unas 565 instrucciones a 0,1 ms, no se acerca.

**Memoria.** Tabla de la fase A: 128 celdas (8 clases por 16 tramos) por 2 posiciones por 2 umbrales = 512 bytes, una BRAM, cambiable con `icebram`. Además: 16 palabras de 64 d², 7 constantes N_j y 7 sumas corridas, 8 punteros de clase, 9 potencias de dos, unas 14 palabras de buzones (valor y tick de precio, fase, clase, tramo, objetivo, cantidad y byte), 5 de contabilidad (caja, acc, objetivo de acciones, entrada, estado). Unas 70 palabras más la tabla: cerca de 800 bytes. Hay que confirmar contra el mapa de memoria de R1 que la tabla cabe en la BRAM libre.

**Protocolo de memoria compartida para que las decisiones sean idénticas a la referencia.**
1. Un solo escritor por palabra. Cada dato publicado lleva el número de tick: el escritor guarda primero el valor y después el tick; el lector espera a ver el tick actual y recién entonces lee el valor. Necesita que los stores de un hilo se vean en orden en los otros, lo que el barrel cumple si tiene un solo puerto de memoria y ejecuta en orden (hay que confirmarlo en su prueba de memoria compartida, P1).
2. Orden de cada tick: hilo 0 publica precio y tick; hilos 1 y 3 arrancan con él (clase; repetición de la orden ejecutada); hilo 2 espera clase y fase del tick; hilo 3 espera el objetivo; hilo 0 espera la cantidad y escribe. Nadie usa un dato de otro tick, así que el resultado no depende de la velocidad relativa de los hilos.
3. El hilo 0 publica siempre el byte que escribió, venga de la tabla o del respaldo, y el hilo 3 repite ese. Así la contabilidad sigue bien aunque se use el respaldo.
4. Respaldo: si la cantidad no llega antes de un plazo fijo, o el hilo 3 publicó modo seguro, el hilo 0 escribe el byte de la banda 40. En operación normal no ocurre, y entonces la placa decide igual que `optimo_estrategia.Optima` (tabla comprimida, clase de placa, guarda (b)), cuya contabilidad es la del motor, que es la oficial.
5. Para que la referencia sea exacta hay que fijar en ella lo mismo que la placa: los cortes N_j, la histéresis de 64, los umbrales de 512 bytes, la fórmula de la media posición y el orden de las órdenes de hasta 63. Ya están así en `optimo_estrategia.py` con `placa=True, comprimida=True`.

**¿Cabe y permite equivalencia exacta?** Sí, con dos condiciones. La primera es de presupuesto: unos 700 ciclos de 1131 en el peor caso, con poca holgura para el sondeo; habría que medirlo. La segunda es de supuestos: la media posición sale de la contabilidad propia, que es exacta solo si la maestra usa la contabilidad del testbench (caja inicial 10 000, comisión 5). Si el día de la competencia cambian, la placa sigue funcionando, pero la media posición queda mal dimensionada y deja de coincidir con la referencia calculada con los valores supuestos. Por eso se deja preparada la alternativa.

### 13.7 Alternativa preparada: V1 log con el mismo reparto

Dos posiciones (caja o invertido), 512 bytes, sin contabilidad: las órdenes son "comprar 63" y "vender 63", idempotentes, así que no dependen de la caja ni de la comisión. Con la misma regla de elección sobre sus guardas ((b) no aplica), ninguna pierde a lo más 5 % de los torneos contra el rival, y por la regla 2 queda **V1 log con a16 y c**: 1,843 puntos (banda 40 1,842), pierde 6,3 % de los torneos contra el rival, +115 (ee 33) en las otras acciones; +146 (ee 47) en la validación por años y +119 (ee 49) en la de grupos.

| V1 log (otras acciones) | Pts sin copia | Media | Peor | Δ con banda 40 (ee) | 3 rondas perdidas contra el rival % |
|---|---|---|---|---|---|
| sin guarda | 1,853 | 21 650 | 5648 | +347 (73) | 8,7 |
| a16 | 1,840 | 21 436 | 6957 | +132 (38) | 6,8 |
| a24 | 1,845 | 21 509 | 6957 | +206 (50) | 7,7 |
| a32 | 1,846 | 21 533 | 5648 | +230 (60) | 8,3 |
| c | 1,851 | 21 530 | 5648 | +227 (52) | 7,3 |
| **a16+c** | 1,843 | 21 418 | 7762 | +115 (33) | 6,3 |
| a24+c | 1,846 | 21 469 | 7363 | +166 (43) | 6,9 |
| a32+c | 1,847 | 21 497 | 5648 | +194 (47) | 7,2 |

En la placa: hilo 3 sin contabilidad (ticks, tramo, supuestos: unas 12 instrucciones); hilo 2 con la celda de 4 bytes, el tope (a) (la entrada se guarda al comprar y se compara con p + 16) y la guarda (c) (unas 30); hilos 0 y 1 iguales. Camino de la respuesta: unas 4 + 40 + 30 + 9 = 83 instrucciones, unos 330 ciclos. Memoria: 512 bytes de tabla y unas 50 palabras. No fue al examen: si se quiere, sería otra mirada a las cinco empresas.

### 13.8 Examen en las cinco empresas

Una sola corrida (`optimo_examen.txt`, 52 minutos), con la población completa: 1 368 253 ventanas. Compara la variante elegida en las otras acciones con la banda 40 y con la banda 40 más el módulo A de la sección 12. Es la segunda mirada a las cinco empresas, después del examen del módulo A. Con ellas no se ajustó ni se eligió nada. Error estándar por empresa y bloque de 20 días de inicio, como en las secciones 10 a 12. Los torneos usan los mismos sorteos para las tres estrategias. "Contra el rival" es el mano a mano de una ronda; "3 rondas" es la suma de tres ventanas sorteadas.

| Subconjunto | Estrategia | Pts sin copia | 1.ª sola % | Media | p5 | Peor | Órdenes | Δ con banda 40 (ee) | Contra el rival: gana / empata / pierde % | 3 rondas: gana / pierde % |
|---|---|---|---|---|---|---|---|---|---|---|
| Población (1 368 253) | banda 40 | 1,852 | 35,6 | 21 289 | 10 578 | 8948 | 3,8 | 0 | 60,6 / 34,0 / 5,4 | 93,3 / 2,7 |
| Población (1 368 253) | banda 40 + módulo A | 1,856 | 43,6 | 21 349 | 10 699 | 8622 | 4,1 | +60 (30) | 70,6 / 21,7 / 7,7 | 96,2 / 2,8 |
| Población (1 368 253) | **V3 log con (b)** | 1,869 | 50,8 | 21 413 | 10 970 | 8122 | 5,7 | +124 (77) | 81,2 / 10,4 / 8,4 | 97,7 / 2,2 |
| Validación por años (391 320) | banda 40 | 1,870 | 40,2 | 22 422 | 11 214 | 9472 | 3,9 | 0 | 68,0 / 25,7 / 6,2 | 96,7 / 1,6 |
| Validación por años (391 320) | banda 40 + módulo A | 1,867 | 45,1 | 22 433 | 11 460 | 8622 | 4,3 | +11 (76) | 75,3 / 15,9 / 8,9 | 97,8 / 1,9 |
| Validación por años (391 320) | **V3 log con (b)** | 1,869 | 50,6 | 22 415 | 11 934 | 8122 | 6,2 | -7 (179) | 81,6 / 6,7 / 11,7 | 97,0 / 3,0 |
| Validación por empresas (547 338) | banda 40 | 1,845 | 35,6 | 20 372 | 10 422 | 9372 | 3,7 | 0 | 53,7 / 41,2 / 5,1 | 89,5 / 3,5 |
| Validación por empresas (547 338) | banda 40 + módulo A | 1,860 | 45,1 | 20 519 | 10 620 | 8622 | 4,0 | +146 (49) | 67,2 / 25,6 / 7,2 | 95,2 / 3,3 |
| Validación por empresas (547 338) | **V3 log con (b)** | 1,863 | 49,0 | 20 454 | 10 865 | 8122 | 5,5 | +82 (102) | 78,4 / 12,7 / 8,9 | 96,7 / 3,1 |

Por caso. Caso S: el 100 llega antes que el 255. Caso B: el 255 llega primero.

| Subconjunto | Caso (ventanas, % del subconjunto) | Estrategia | Pts sin copia | Media | p5 | Δ con banda 40 (ee) | 3 rondas: gana / pierde % |
|---|---|---|---|---|---|---|---|
| Población | S (790 173, 57,8) | banda 40 | 1,992 | 25 668 | 24 198 | 0 | 100,0 / 0,0 |
| Población | S (790 173, 57,8) | banda 40 + módulo A | 1,986 | 25 592 | 22 480 | -76 (26) | 99,9 / 0,1 |
| Población | S (790 173, 57,8) | **V3 log con (b)** | 1,953 | 25 187 | 20 930 | -481 (93) | 99,1 / 0,9 |
| Población | B (578 080, 42,2) | banda 40 | 1,297 | 15 303 | 10 152 | 0 | 22,8 / 25,8 |
| Población | B (578 080, 42,2) | banda 40 + módulo A | 1,350 | 15 548 | 10 236 | +246 (56) | 62,3 / 24,2 |
| Población | B (578 080, 42,2) | **V3 log con (b)** | 1,466 | 16 254 | 10 413 | +951 (99) | 91,6 / 6,9 |
| Validación por años | S (262 490, 67,1) | banda 40 | 1,993 | 25 556 | 23 684 | 0 | 100,0 / 0,0 |
| Validación por años | S (262 490, 67,1) | banda 40 + módulo A | 1,981 | 25 401 | 21 835 | -155 (69) | 99,9 / 0,1 |
| Validación por años | S (262 490, 67,1) | **V3 log con (b)** | 1,937 | 24 909 | 20 232 | -647 (218) | 97,7 / 2,3 |
| Validación por años | B (128 830, 32,9) | banda 40 | 1,165 | 16 036 | 10 323 | 0 | 16,0 / 36,8 |
| Validación por años | B (128 830, 32,9) | banda 40 + módulo A | 1,231 | 16 386 | 10 484 | +350 (158) | 61,6 / 27,1 |
| Validación por años | B (128 830, 32,9) | **V3 log con (b)** | 1,375 | 17 334 | 10 667 | +1298 (235) | 95,7 / 3,4 |
| Validación por empresas | S (284 347, 52,0) | banda 40 | 1,986 | 25 745 | 23 714 | 0 | 99,9 / 0,1 |
| Validación por empresas | S (284 347, 52,0) | banda 40 + módulo A | 1,983 | 25 705 | 22 723 | -40 (27) | 99,9 / 0,1 |
| Validación por empresas | S (284 347, 52,0) | **V3 log con (b)** | 1,950 | 25 228 | 20 573 | -518 (137) | 99,0 / 1,0 |
| Validación por empresas | B (262 991, 48,0) | banda 40 | 1,341 | 14 563 | 10 150 | 0 | 17,8 / 18,9 |
| Validación por empresas | B (262 991, 48,0) | banda 40 + módulo A | 1,419 | 14 911 | 10 214 | +348 (90) | 66,7 / 18,4 |
| Validación por empresas | B (262 991, 48,0) | **V3 log con (b)** | 1,496 | 15 293 | 10 400 | +730 (94) | 91,7 / 6,5 |

**Lectura.** El patrón por caso es el mismo de las otras acciones (`optimo_casos_otras.txt`: -527 con ee 49 en el caso S y +1016 con ee 48 en el B). En el caso S, V3 compra en la fase A, el precio baja hasta el 100 y desde ahí la regla sigue igual que la banda 40. Pierde unos 500 por ronda y el percentil 5 baja de 24 198 a 20 930. En el caso B, la banda 40 queda en caja hasta ver el 100, que llega después del 255: V3 gana unos 1000 por ronda y pasa de 22,8 % a 91,6 % de torneos de 3 rondas ganados contra el rival. La diferencia en un subconjunto es casi exactamente la mezcla de los dos casos. El equilibrio está en d_B / (d_B - d_S):

| Conjunto | Casos S | Equilibrio | Δ con banda 40 (ee) |
|---|---|---|---|
| Cinco, población | 57,8 % | 66,4 % | +124 (77) |
| Cinco, validación por años | 67,1 % | 66,7 % | -7 (179) |
| Cinco, validación por empresas | 52,0 % | 58,5 % | +82 (102) |
| Otras, todas | 56,4 % | 65,8 % | +146 (43) |
| Otras, validación por años | 56,5 % | 70,6 % | +207 (60) |
| Otras, validación por grupos | 56,2 % | 65,7 % | +144 (50) |

La validación por años de las cinco (2023 y 2024) es el único subconjunto con más casos S que el equilibrio, y ahí la ventaja desaparece. En las otras acciones, en esos mismos años, la proporción fue la de siempre. El error estándar en las cinco es alto porque son solo cinco empresas y las ventanas vecinas se traslapan: aun sin el efecto de los años, +82 en la validación por empresas no alcanza a separarse del ruido.

### 13.9 Criterio de la sección 7 del diseño, punto por punto

Puntos 1 y 2 como en la sección 12. El punto 3 lo cambió Nicolás antes del examen: "no pierde contra el rival de Tesla en más de 10 % de los torneos de 3 rondas". El criterio se evaluó con los valores sin redondear.

| Punto | V3 log con (b) | Se cumple | Banda 40 + módulo A (mismo examen) | Se cumple |
|---|---|---|---|---|
| 1. Más puntos que la banda 40, sin la copia `espera_banda40`, en las dos validaciones | Años: 1,869 contra 1,870. Empresas: 1,863 contra 1,845 | no (falla en años) | Años: 1,867. Empresas: 1,860 | no (falla en años) |
| 2. Diferencia de patrimonio medio con la banda 40 mayor que 1 ee, en las dos validaciones | Años: -7 (ee 179). Empresas: +82 (ee 102). Población: +124 (ee 77) | no (falla en las dos) | Años: +11 (ee 76). Empresas: +146 (ee 49) | no (falla en años) |
| 3. Pierde a lo más 10 % de los torneos de 3 rondas contra el rival (población) | 2,2 % | sí | 2,8 % | sí |

Con el punto 3 original del diseño (no perder más torneos que la banda 40, que pierde 2,7 %), V3 con (b) también lo cumpliría y el módulo A no. **V3 con (b) no cumple el criterio.** Según la regla de la sección 12, compite la banda 40.

### 13.10 Opciones, sin decidir

| Opción | Qué se gana | Qué se pierde |
|---|---|---|
| **Banda 40** (lo que sigue del criterio, como en la sección 12) | Es la regla de los bitstreams R0, R1 y R2 que ya están pasando las puertas, sin código nuevo antes del corte del 22/11. Responde en 83 a 88 ciclos. No depende de la caja ni de la comisión. Es mejor en el caso S (percentil 5: 24 198 contra 20 930) y en el peor caso (8948 contra 8122) | La ventaja de V3 en la población: +124 (ee 77) por ronda, +0,017 puntos, 15 puntos más de primera sola y 0,5 puntos menos de torneos perdidos contra el rival. Sobre todo pierde el caso B, donde gana solo 22,8 % de los torneos de 3 rondas contra el rival (V3, 91,6 %) |
| **V3 log con (b)**, con el reparto de 4 hilos de 13.6 | Lo anterior. Es la mejor de las tres en puntos y en primera sola en la población y en la validación por empresas. En las otras acciones gana a la banda 40 en las dos validaciones internas | No cumple el criterio fijado antes del examen. Su ganancia media es una apuesta a que los casos S sean menos de dos tercios. Pierde unos 500 por ronda en cada caso S. Hay que escribir un `fondo.s` nuevo con contabilidad y protocolo, más su referencia exacta, y pasar las puertas antes del corte del 22/11 y de la maestra del 26/11. Sube a unos 700 de 1131 ciclos. Si el 1/12 cambian la caja o la comisión, la media posición queda mal dimensionada y deja de coincidir con la referencia |
| **V1 log con a16 y c** (alternativa preparada en 13.7) | Sin contabilidad: las órdenes son idempotentes. Unos 330 ciclos, 512 bytes de tabla | No pasó por el examen; examinarla sería la tercera mirada a las cinco. En las otras gana menos (+115, ee 33) y pierde más torneos contra el rival que la banda 40 (6,3 % contra 3,7 %). Exige el mismo trabajo de programa y puertas |
| **Banda 40 + módulo A** (sección 12) | +60 (ee 30) en la población, +146 (ee 49) en la validación por empresas, programa más simple que V3 | Con el punto 3 nuevo cumple ese punto, pero sigue sin cumplir el 1 y el 2. En todo lo que mide el examen queda por debajo de V3 con (b) |

**Recomendación (mía, etiquetada como tal): competir con la banda 40.** Tengo tres razones:

1. El criterio se fijó antes del examen y no se cumple. Adoptar V3 después de ver el examen convertiría a las cinco empresas en datos de ajuste.
2. El examen sí explica lo que pasa, y la explicación es la misma en las otras acciones y en las cinco. Por eso la decisión se reduce a una apuesta sobre cuántas series ocultas suben y cuántas bajan. Con menos de dos tercios de casos S, V3 gana en promedio. Las cinco empresas en 2023 y 2024 estuvieron justo sobre ese límite, y nada de la serie dice de antemano en qué lado va a caer la competencia.
3. Implementarla obliga a escribir y verificar un programa de 4 hilos con contabilidad propia a dos días del corte, y su equivalencia exacta depende de que la caja y la comisión no cambien.

Lo que podría inclinar la decisión hacia V3 es el perfil de riesgo registrado en `docs/decisiones.md` (A2): maximizar el patrimonio esperado y ganar por diferencia. En esa medida V3 con (b) es la mejor estimación que hay, con +124 (ee 77) en las cinco y +146 (ee 43) en las otras, y además pierde menos torneos contra el rival que la banda 40. Si se elige así, la elección va contra el criterio y debe quedar registrada de esa forma.

Como material de defensa, la conclusión del intento es esta: el juego tiene un modelo exacto que calibra en datos reales, y su política óptima sí gana en promedio. Pero gana apostando en la fase A a qué extremo llega primero, y esa apuesta tiene un resultado de unos 1500 de diferencia entre un caso y otro, demasiado grande para demostrarla con cinco empresas.

La decisión es de Nicolás.

### 13.11 Comandos

Todos con `export P4_DATOS=$HOME/proyectos/datos_p4`, desde la raíz de la rama. Salidas en `docs/mediciones/exploracion/` salvo que se diga otra cosa.

| Resultado | Comando | Salida |
|-----------|---------|--------|
| Recurrencia contra paseos simulados | `python3 ref/cotas/paseo_optimo.py prueba` | pantalla |
| Tablas de la programación dinámica (56, unos 5 minutos) | `cd ref/cotas && python3 -c "import paseo_optimo as P; P.politicas()"` | `build/cotas/optimo/` |
| G1 | `python3 ref/cotas/explorar_optimo.py g1` (unos 8 minutos) | `optimo_g1.txt` |
| Equivalencia con la banda 40 | `python3 ref/cotas/explorar_optimo.py equivalencia --conjunto otras` y `--conjunto cinco` (unos 29 minutos) | `optimo_equivalencia_otras.txt`, `optimo_equivalencia_cinco.txt` |
| G2 | `python3 ref/cotas/explorar_optimo.py g2` | `optimo_g2.txt` |
| G3 | `python3 ref/cotas/explorar_optimo.py g3` | `optimo_g3.txt` |
| Diagnóstico, guardas y elección | `python3 ref/cotas/explorar_optimo.py guardas` (unos 12 minutos) | `optimo_guardas.txt` |
| Elegida por caso en las otras | `python3 ref/cotas/explorar_optimo.py casos` (desde la caché) | `optimo_casos_otras.txt` |
| Examen | `python3 ref/cotas/explorar_optimo.py examen` (unos 52 minutos) | `optimo_examen.txt` |
| Aritmética de placa | `python3 ref/cotas/optimo_placa.py` | pantalla |
