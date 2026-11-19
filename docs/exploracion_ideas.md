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
