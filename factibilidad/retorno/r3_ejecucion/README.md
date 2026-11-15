# Estudio de retorno 3: ejecución que conoce su patrimonio

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Tramo de factibilidad del Proyecto 4. Esta carpeta no agrega hardware ni cambia el programa de la placa: son estrategias evaluadas con el arnés de `factibilidad/retorno` y las herramientas para medirlas. Todo se hizo con la semilla 0 (exploración). Las semillas reservadas no se miraron.

## 1. La pregunta

Cómo entrar y salir cuando hacen falta varias órdenes por el límite de 63 acciones.

La regla actual (`max_media`, igual que la regla base) repite "comprar 63" mientras la señal dice adentro y "vender 63" mientras dice afuera. Es idempotente porque la maestra recorta, pero una posición completa son 2 o 3 órdenes por lado (hasta 8 cuando el patrimonio crece o el precio es bajo), la última orden de una entrada puede comprar muy pocas acciones pagando la comisión completa, y la entrada y la salida tardan varios ticks. Una estrategia que lleva su propia contabilidad (caja y acciones, un espejo de la maestra) podría hacerlo mejor. El enunciado lo permite: "La maestra lleva la contabilidad oficial. El grupo puede llevar su propia copia si su algoritmo la necesita".

## 2. Respuesta corta

1. **La cota no es chica.** Sin límite por orden, la misma regla ganaría +1,1 % de patrimonio por ronda de 2000 ticks en el remuestreo y +1,5 % en las series interiores de la evidencia, +0,036 puntos de torneo con la lectura lineal en patrimonio (H3a) y +0,073 con la lectura por puesto (H3b). Es del mismo tamaño que pasar de la regla base a `max_media`. Con el límite en 126 ya se recupera casi todo.
2. **Pero casi toda la cota son comisiones que no se pueden evitar.** De las 55 órdenes de una ronda de 2000 ticks, 28 existen solo porque la posición no cabe en una orden, y cuestan 140 en comisiones. La demora en sí no cuesta: un tick después de la primera orden el precio está, en promedio, a menos de 0,02 del precio de esa orden en la evidencia completa, y entre -0,09 y +0,04 según cuál de las dos evidencias se mire. Entrar y salir en varios ticks no es el problema, pagar una comisión por cada tramo sí.
3. **Lo único que se puede recuperar con el límite real es no mandar las órdenes residuales chicas.** Una compra de menos de 8 acciones gana en promedio menos que los 10 de comisión que arrastra (5 al comprar y 5 al vender ese resto). Dejar de mandarlas (`ejec:m=8`) vale +15 ± 0,3 de patrimonio por ronda de 2000 ticks (+0,14 %), +0,007 puntos con H3a, y pasa el criterio de corte contra `max_media` en los dos horizontes y en las 9 combinaciones de campo y G. Mandar además el resto mediano (menos de 24 acciones) solo cuando el precio está un punto más abajo (`ejec:m=8,m2=24,e2=32`) vale +24 ± 0,8 (+0,22 %) y +0,012 puntos. Es entre un 10 y un 30 % de la cota, según cómo se mida.
4. **Todo lo demás pierde o no se distingue**: tope de la posición en 1, 2 o 3 órdenes, tope en una fracción del patrimonio, entrada escalonada, salida escalonada, salida anticipada proporcional a las órdenes que faltan, tamaño según la profundidad, no recomprar, y comprar solo en los primeros ticks de la entrada. Se probaron 61 variantes.
5. **La contabilidad propia trae un riesgo que la regla actual no tiene.** El espejo no recibe nada de la maestra: si la caja inicial real es mayor que la que supone, si la comisión real es menor, o si una ronda parte sin reiniciar la placa, el espejo cree que no queda caja, deja de comprar y nadie lo corrige. Con el doble de caja pierde 3 % en una ronda de 2000 ticks y 19 % en una de 20 000. En la dirección contraria (menos caja o más comisión) no pierde: vuelve a comportarse como `max_media`.
6. **Recomendación.** La regla de entrada y salida de la edición de competencia sigue siendo la actual: "comprar 63" en cada tick mientras la señal dice adentro y "vender 63" mientras dice afuera, sin escalones, sin topes y sin anticipar la salida. Entrar y salir lo más rápido que deja el límite es lo mejor que se encontró. Llevar contabilidad propia para suprimir las órdenes residuales pasa el criterio de corte y vale entre 0,007 y 0,012 puntos de 2 (H3a), así que por el criterio escrito es candidata a competencia. Conviene llevarla solo si el ayudante confirma que la caja inicial es 10 000 y la comisión 5, y que la placa parte de reset en cada ronda. Sin esas dos confirmaciones lo que se arriesga es mucho más que lo que se gana. No justifica `mulstep` ni `divstep`: cabe en software con holgura.

## 3. Qué se construyó

| Pieza | Dónde | Qué hace |
|-------|-------|----------|
| Cota | `cota/parche.sh`, `cota/lim.c`, `cota/validar_cota.py`, `cota/medir_cota.py` | Copia local del núcleo del arnés con dos líneas cambiadas, que acepta órdenes de más de 63 acciones, y la estrategia `lim` (la regla de `max_media` con un límite por orden hipotético). Se usa solo para la cota. |
| Descomposición | `herramientas/descomp.c` | Corre una estrategia con el lazo y la contabilidad del arnés y clasifica cada orden ejecutada: primera, continuación (existe por el límite) o recompra, por tamaño, con su comisión y su ganancia bruta. Además mide el camino del precio después de la primera orden. |
| Estrategia | `ejec.c` | `max_media` con contabilidad propia (espejo de la maestra) y una opción por cada variante del estudio. Sin opciones decide byte a byte lo mismo que `max_media`. |
| Barrido | `herramientas/barrido.py`, `herramientas/variantes.txt`, `herramientas/variantes2.txt` | El veredicto del criterio de corte (`veredicto --parada`) de cada variante contra `max_media`, en una tabla. |
| Validación | `herramientas/validar.py` | `ejec` contra `max_media`, espejo contra la cuenta oficial, control negativo y causalidad. |
| Finales | `herramientas/tabla_finales.py`, `herramientas/robustez.py` | Las candidatas bajo las cuatro hipótesis y qué pasa cuando lo que el espejo supone no es cierto. |

No se modificó ningún archivo fuera de esta carpeta. El núcleo del arnés se usa tal cual (`build/arnes` se compila con `../nucleo/nucleo.mk`). La copia de la cota vive en `build/cota/` y se regenera con `make`.

## 4. Cómo se reproduce cada número

Desde esta carpeta. Las salidas quedan en `mediciones/` y los productos intermedios en `build/`, que no se versiona. Hacen falta las series de `factibilidad/retorno/build/series` (`make -C .. series`).

| Comando | Qué hace | Salida | Tiempo medido |
|---------|----------|--------|---------------|
| `make arnes` | Compila `build/arnes`: el núcleo sin tocar más `ejec.c`. | | segundos |
| `make validar` | Comprobaciones de `ejec` (sección 9). | `mediciones/validacion.txt` | 15 s |
| `make validar-cota` | La copia del núcleo contra el arnés con límite 63. | `mediciones/cota_parche.txt`, `mediciones/cota_validacion.txt` | 1 min 35 s |
| `make cota` | Paso 1: la cota. | `mediciones/cota.txt` | 45 s |
| `make descomposicion` | Paso 2: de qué está hecho el costo. | `mediciones/descomposicion.txt` | 10 s |
| `make variantes` | Paso 3: las 61 variantes y el control, cada una con su veredicto. | `mediciones/variantes_1.txt`, `mediciones/variantes_2.txt` | 14 min |
| `make finales` | Paso 4: veredictos completos, sensibilidad al campo y a G, control del desempate, hipótesis, robustez y costo de las candidatas finales. | `mediciones/finales_*` | 8 min |
| `make practica` | Las candidatas finales en los 10 bloques reales y en la serie de práctica completa (informativo). | `mediciones/finales_practica.txt` | 1 s |
| `make todo` | Todo lo anterior. | | 26 min 25 s como un solo comando (sin `practica`, que se agregó después) |

`HILOS` (por defecto 5) limita los hilos del arnés. `barrido.py` corre hasta 5 veredictos a la vez con un hilo cada uno. Los tiempos de `variantes`, `finales` y `todo` son de la última corrida completa (14/11), con la máquina compartida con otros trabajos; los demás se midieron por separado. Todas las salidas de `mediciones/` son de esa corrida.

## 5. Paso 1: cuánto se gana como máximo arreglando la ejecución

### Cómo se midió

El núcleo fija el límite de 63, igual que la maestra: la cantidad son los 6 bits bajos del byte. Para la cota hace falta una maestra que no existe. `cota/parche.sh` copia el núcleo a `build/cota/nucleo/` y cambia dos líneas de `nucleo.c` (`mediciones/cota_parche.txt`): la cuenta acepta además la cantidad que venga sobre el bit 8 de la decisión, y la instancia deja pasar esos bits. Una estrategia que devuelve un byte (todas las del núcleo y todos los rivales) se ejecuta exactamente igual. Solo `lim` usa los bits altos, así que en el torneo los rivales siguen con el límite real.

Validación de la copia (`mediciones/cota_validacion.txt`): 6 candidatos y 16 rivales de las seis clases en 12 lotes de los dos largos, 391 842 corridas, 0 distintas. `lim:L=63` de la copia contra `max_media` del arnés, 17 811 series, 0 distintas. Control negativo: `lim:L=126` difiere de `lim:L=63` en 4830 de 5000 series. El comando `veredicto` completo de `max_media` contra `base` da el mismo texto en los dos binarios, a los dos largos.

### Resultado

Diferencia pareada contra `max_media` con el límite real, semilla 0, campo mixto, G = 10 (`mediciones/cota.txt`). Los puntos son del conjunto evidencia.

Rondas de 2000 ticks:

| Límite por orden | Órdenes por ronda | Patrimonio, remuestreo | Patrimonio, evidencia interior | Media geométrica, evidencia | H3a: puntos, p5 de tres rondas | H3b: puntos, p5 de tres rondas |
|------------------|-------------------|------------------------|--------------------------------|-----------------------------|--------------------------------|--------------------------------|
| 63 (real) | 55,2 | 0 | 0 | 0 | 0 | 0 |
| 126 | 31,8 | +103 ± 5 (+0,95 %) | +132 ± 3 (+1,21 %) | +1,21 % | +0,033 ± 0,001, +0,040 ± 0,008 | +0,069 ± 0,001, +0,067 ± 0,022 |
| 252 | 27,9 | +117 ± 6 (+1,07 %) | +156 ± 5 (+1,42 %) | +1,46 % | +0,035 ± 0,001, +0,042 ± 0,008 | +0,072 ± 0,001, +0,083 ± 0,021 |
| Sin límite | 27,2 | +120 ± 8 (+1,10 %) | +160 ± 6 (+1,46 %) | +1,84 % | +0,036 ± 0,001, +0,042 ± 0,008 | +0,073 ± 0,001, +0,083 ± 0,021 |

Rondas de 20 000 ticks, conjunto evidencia:

| Límite por orden | Interiores: órdenes, patrimonio, geométrica | Interiores: H3a, H3b | Parada: órdenes, patrimonio, geométrica | Parada: H3a, H3b |
|------------------|---------------------------------------------|----------------------|------------------------------------------|------------------|
| 63 (real) | 723, 26 534, 0 | 0 | 597, 21 556, 0 | 0 |
| 126 | 444, +3 887 ± 151, +10,9 % | +0,044 ± 0,001, +0,083 ± 0,002 | 367, +2 897 ± 84, +9,3 % | +0,042 ± 0,001, +0,079 ± 0,001 |
| 252 | 314, +5 869 ± 312, +14,5 % | +0,049 ± 0,002, +0,087 ± 0,002 | 258, +4 382 ± 170, +12,5 % | +0,045 ± 0,001, +0,084 ± 0,002 |
| Sin límite | 252, +9 697 ± 2 194, +15,5 % | +0,048 ± 0,002, +0,086 ± 0,002 | 200, +6 590 ± 1 111, +13,2 % | +0,042 ± 0,002, +0,081 ± 0,002 |

- **La cota está muy por encima del ruido.** A 2000 ticks, +120 ± 8 en el remuestreo y +0,036 ± 0,001 puntos con H3a. Pasar de la regla base a `max_media` vale +0,038 (H3a) y +0,036 (H3b) con esta misma semilla: el límite de 63 cuesta lo mismo que esa mejora con H3a y el doble con H3b. En el estrés la cota es +0,030 ± 0,002 (H3a) y +0,063 ± 0,002 (H3b).
- **Con 126 se recupera casi todo**: +0,033 de los +0,036 puntos. La mayoría de las posiciones necesita 2 órdenes (sección 6).
- **A 20 000 ticks es la misma tasa compuesta.** +15,5 % de media geométrica en 10 tramos es +1,45 % por cada 2000 ticks (calculado a partir de la cifra medida). La vista de parada confirma el signo y el tamaño en puntos.
- **Sin límite, la media de patrimonio con todas las series no sirve.** En las pocas series que bajan a precios de 1 a 5, una orden sin límite compra miles de acciones, el patrimonio se multiplica por miles y llega a desbordar los 32 bits (en el estrés a 20 000 ticks el percentil 5 sale negativo). Por eso la tabla usa el remuestreo, las series interiores (precio siempre entre 21 y 249), la media geométrica y los puntos, que no tienen ese problema. `mediciones/cota.txt` trae todas las vistas.
- La cota es de la ejecución de esta señal. No dice nada de cambiar la señal.

## 6. Paso 2: de qué está hecho el costo de la ejecución actual

`herramientas/descomp.c` corre `max_media` con la contabilidad del arnés y anota cada orden ejecutada (`mediciones/descomposicion.txt`). Comprueba que el patrimonio y las órdenes de cada serie son los de `correr_serie`: 0 series distintas en todos los conjuntos.

Clases de orden: **primera** (la primera compra de una posición o la primera venta de una salida), **continuación** (la orden del tick anterior ejecutó exactamente 63: esta orden existe porque la posición no cabía en una) y **recompra** (compra con la posición ya completa, porque el precio bajó y la caja que sobraba alcanza para alguna acción más).

Conjunto evidencia, rondas de 2000 ticks, promedio por ronda:

| | Órdenes | Acciones | Comisión | Ganancia bruta por orden |
|-|---------|----------|----------|--------------------------|
| Compras, primera | 13,46 | 839 | 67 | 57,2 |
| Compras, continuación | 14,16 | 443 | 71 | 33,5 |
| Compras, recompra | 0,29 | 10 | 1,4 | 49,1 |
| Ventas, primera | 13,44 | 837 | 67 | |
| Ventas, continuación | 13,86 | 434 | 69 | |
| Total | 55,2 | | 276 | |

- 13,5 posiciones por ronda, de 96 acciones en promedio. Ganancia bruta de 0,97 de precio por acción comprada, 93 por posición.
- Según las órdenes de compra de la entrada: 1 orden el 14,8 % de las posiciones, 2 órdenes el 72,1 %, 3 el 10,6 % y 4 o más el 2,5 %. A 20 000 ticks (vista de parada) son 162 acciones por posición y 3,06 órdenes por entrada: 2 órdenes el 50 %, 3 el 20 %, 4 o más el 21 %.
- **Las continuaciones son 28 de las 55 órdenes y cuestan 140 en comisiones por ronda de 2000 ticks**, el 1,28 % del patrimonio final. A 20 000 ticks son 1 982 por ronda en la vista de parada y 2 358 en las interiores.
- Las recompras casi no existen: 0,29 órdenes y 1,4 de comisión por ronda.

### Órdenes residuales: cuántas ejecutan menos de m acciones y cuánto cuestan

Compras de continuación según las acciones que ejecutan (evidencia, 2000 ticks, por ronda). Cada una paga 5 al comprar y arrastra otra continuación de 5 al vender ese resto: 10 en total.

| Acciones | Órdenes por ronda | Ganancia bruta por orden | Contra 10 de comisión |
|----------|-------------------|--------------------------|------------------------|
| 1 | 0,33 | 0,9 | pierde 9,1 |
| 2 a 3 | 0,62 | 2,2 | pierde 7,8 |
| 4 a 7 | 1,20 | 5,1 | pierde 4,9 |
| 8 a 15 | 2,27 | 10,6 | empata |
| 16 a 31 | 3,55 | 21,7 | gana 11,7 |
| 32 a 62 | 3,44 | 44,0 | gana 34,0 |
| 63 | 2,76 | 77,4 | gana 67,4 |

Todas las órdenes (compras y ventas) que ejecutan menos de m acciones:

| m | Órdenes por ronda | Comisión por ronda | Porcentaje de las órdenes |
|---|-------------------|--------------------|---------------------------|
| 2 | 0,76 | 3,8 | 1,4 % |
| 4 | 1,97 | 9,9 | 3,6 % |
| 8 | 4,34 | 21,7 | 7,9 % |
| 16 | 8,85 | 44,2 | 16,0 % |
| 32 | 15,89 | 79,5 | 28,8 % |

El punto de equilibrio sale de la tabla y también de la cuenta directa: 10 de comisión dividido por 0,97 de ganancia por acción son 10 acciones. Bajo 8 acciones la orden residual pierde; sobre 16 gana. Lo que se puede ahorrar suprimiendo las de menos de 8 es 0,33 x 9,1 + 0,62 x 7,8 + 1,20 x 4,9 = 13,7 por ronda (calculado a partir de la tabla). La variante `ejec:m=8` midió +14,8.

### La demora

Camino del precio después de la primera orden, sin condicionar a lo que la estrategia haga después (media ± error entre órdenes, en unidades de precio):

| Conjunto, 2000 ticks | Primera compra: precio 1, 2 y 4 ticks después, menos el de la primera compra | Primera venta: precio 1, 2 y 4 ticks después, menos el de la primera venta |
|----------------------|-------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| Evidencia | -0,014 ± 0,004, +0,006 ± 0,005, +0,018 ± 0,007 | -0,013 ± 0,003, -0,071 ± 0,004, -0,060 ± 0,006 |
| Remuestreo | -0,088 ± 0,006, -0,086 ± 0,008, -0,137 ± 0,010 | -0,020 ± 0,004, -0,148 ± 0,006, -0,122 ± 0,009 |
| Plausibles | +0,039 ± 0,003, +0,072 ± 0,004, +0,137 ± 0,006 | +0,000 ± 0,003, +0,002 ± 0,004, -0,004 ± 0,006 |
| Los 10 bloques reales | -0,267 ± 0,158, -0,117 ± 0,178, -0,175 ± 0,226 | -0,041 ± 0,097, -0,213 ± 0,133, -0,230 ± 0,218 |

- **Comprar el segundo tramo un tick después cuesta entre -0,09 y +0,04 de precio por acción según la evidencia que se mire**, y las dos evidencias tienen signo contrario: en el material de la serie de práctica el precio sigue bajando un poco después de la entrada, y en el modelo sube. En los 10 bloques reales son 120 entradas y el error (0,16) no deja afirmar nada. Con 33 acciones demoradas por posición son entre -3 y +1,3 por posición, contra 10 de comisión.
- Vender el segundo tramo un tick después cuesta 0,01 a 0,02 por acción.
- Lo que sí se ve en todas las evidencias es el desfase de un tick de la maestra: la primera compra se ejecuta 0,14 más cara que el precio que disparó la señal y la primera venta 0,14 más barata (`mediciones/descomposicion.txt`). Eso no depende del límite y no se arregla con contabilidad.
- **Comprobación con la cota.** En el remuestreo a 2000 ticks, quitar el límite ahorra 25,6 órdenes, que son 128 de comisión, y la cota medida es +120 ± 8. La diferencia, -8 ± 8, es todo lo que queda para la demora y para las posiciones que no alcanzan a completarse.

Un aviso sobre una medida que se descartó. La herramienta también informa la diferencia de precio entre cada continuación y la primera orden de su racha. Sale favorable a las continuaciones (por ejemplo -0,13 por acción en las compras de la evidencia), pero no es el costo de la demora: una continuación solo existe si la señal no cambió antes, o sea si el precio no se devolvió, y además pesa por acciones, así que dominan las series con mucho patrimonio o precio bajo. Queda en la salida con ese aviso y no se usa en ninguna conclusión.

## 7. Paso 3: variantes con contabilidad propia

`ejec.c` lleva un espejo de la maestra: en cada tick ejecuta su decisión anterior al precio que acaba de llegar, con la misma aritmética, y queda con su caja y sus acciones. Con eso decide. Cada variante es una opción. El detalle de cada una está en el encabezado de `ejec.c`.

Cada variante contra `max_media` con el criterio de corte (`veredicto --parada`, campo mixto, G = 10, semilla 0). dW es la diferencia pareada de patrimonio y dH3a la de puntos esperados. La tabla completa, con H3b, los percentiles 5 y los errores, está en `mediciones/variantes_1.txt` y `mediciones/variantes_2.txt`.

| Variante | 2000 ticks: dW evidencia, remuestreo, plausibles | 2000 ticks: dH3a | 20 000 ticks, parada: dW, dH3a | Veredicto 2000 / 20 000 |
|----------|--------------------------------------------------|------------------|---------------------------------|--------------------------|
| **(a) No mandar compras de menos de m acciones** | | | | |
| `m=2` | +3, +3, +4 | +0,001 | +29, +0,001 | pasa / pasa |
| `m=4` | +8, +7, +9 | +0,004 | +71, +0,004 | pasa / pasa |
| `m=6` | +12, +10, +14 | +0,006 | +104, +0,005 | pasa / pasa |
| `m=8` | +15, +12, +17 | +0,007 | +128, +0,007 | pasa / pasa |
| `m=10` | +16, +13, +19 | +0,008 | +143, +0,007 | pasa / pasa |
| `m=12` | +17, +14, +20 | +0,009 | +149, +0,008 | pasa / pasa |
| `m=16` | +16, +11, +20 | +0,010 | +143, +0,008 | pasa / pasa |
| `m=24` | +4, 0, +7 | +0,007 | +11, +0,002 | pasa / no pasa |
| `m=32` | -18, -29, -8 | +0,001 | -238, -0,009 | no pasa |
| **(a) No vender si quedan menos de mv acciones** | | | | |
| `mv=8` | +3, -1, +6 | +0,003 | +13, +0,002 | no pasa |
| `mv=16` | -15, -25, -6 | 0,000 | -200, -0,008 | no pasa |
| **(b) Tope de la posición en K órdenes** | | | | |
| `K=1` | -333, -278, -378 | -0,055 | -6 875, -0,231 | no pasa |
| `K=2` | -107, -52, -151 | -0,007 | -3 941, -0,088 | no pasa |
| `K=3` | -69, -22, -104 | -0,003 | -2 571, -0,046 | no pasa |
| **(b) Tope en F/16 del patrimonio** | | | | |
| `F=8` (la mitad) | -138, -161, -131 | -0,029 | -3 829, -0,110 | no pasa |
| `F=12` | +7, -9, +15 | +0,007 | -883, -0,008 | pasa / no pasa |
| `F=14` | +20, +12, +24 | +0,008 | -47, +0,007 | pasa / no pasa |
| **(c) Entrada escalonada que empieza antes** (última orden en E, las anteriores eo antes) | | | | |
| `eo=16` | +31, -22, +79 | -0,008 | +290, -0,066 | no pasa |
| `eo=32` | -5, -92, +85 | -0,021 | -618, -0,131 | no pasa |
| **(c) Entrada anticipada completa, proporcional a las órdenes que hacen falta** | | | | |
| `ec=1,eo=8` | +29, -32, +77 | -0,018 | +448, -0,071 | no pasa |
| `ec=1,eo=16` | +20, -66, +97 | -0,028 | -248, -0,135 | no pasa |
| `ec=1,eo=32` | -51, -180, +77 | -0,058 | -1 697, -0,228 | no pasa |
| **(c)(e) Completar más abajo: tamaño según la profundidad** (primera orden en E, las siguientes eo más abajo) | | | | |
| `ea=0,eo=16` | -29, -9, -38 | 0,000 | -853, -0,015 | no pasa |
| `ea=0,eo=32` | -49, -18, -69 | +0,001 | -1 769, -0,032 | no pasa |
| `ea=0,eo=64` | -83, -33, -126 | -0,005 | -3 067, -0,068 | no pasa |
| **(c) Salida escalonada que empieza antes** (última orden en X, las anteriores xo antes) | | | | |
| `xo=16` | -31, -19, -47 | -0,008 | -836, -0,028 | no pasa |
| `xo=32` | -78, -71, -88 | -0,024 | -1 696, -0,064 | no pasa |
| **(c) Salida escalonada hacia arriba** (primera orden en X, las siguientes xo después) | | | | |
| `xa=0,xo=16` | -7, -61, +53 | -0,011 | +81, -0,052 | no pasa |
| `xa=0,xo=32` | -37, -160, +93 | -0,026 | -1 102, -0,148 | no pasa |
| **(d) Salida anticipada completa, proporcional a las órdenes que hacen falta** | | | | |
| `xc=1,xo=8` | -18, +6, -48 | -0,012 | -719, -0,037 | no pasa |
| `xc=1,xo=16` | -64, -43, -90 | -0,027 | -1 864, -0,082 | no pasa |
| `xc=1,xo=32` | -174, -170, -186 | -0,073 | -3 245, -0,160 | no pasa |
| **(f) No recomprar con la posición completa** | | | | |
| `nr=1` | 0, 0, +1 | 0,000 | +4, 0,000 | pasa / pasa en la letra, literal no pasa: no se distingue |
| **(f) Sin contabilidad: comprar solo en los primeros nt ticks de la entrada** | | | | |
| `nt=2` | -106, -50, -150 | -0,007 | -3 913, -0,087 | no pasa |
| `nt=3` | -68, -22, -103 | -0,003 | -2 527, -0,045 | no pasa |
| `nt=4` | -55, -13, -84 | -0,002 | -1 634, -0,025 | no pasa |
| `nt=6` | -44, -8, -65 | -0,001 | -758, -0,012 | no pasa |
| **(f) Resto mediano solo más abajo** (menos de m: nunca; menos de m2: solo con dev < -(E + e2)) | | | | |
| `m=8,m2=16,e2=32` | +21, +18, +23 | +0,010 | +186, +0,009 | pasa / pasa |
| `m=8,m2=24,e2=16` | +22, +19, +24 | +0,011 | +201, +0,010 | pasa / pasa |
| `m=8,m2=24,e2=32` | +24, +22, +26 | +0,012 | +220, +0,011 | pasa / pasa |
| `m=8,m2=24,e2=64` | +25, +24, +25 | +0,013 | +228, +0,011 | pasa / pasa |
| `m=8,m2=32,e2=32` | +26, +23, +27 | +0,012 | +235, +0,011 | pasa / pasa |
| `m=8,m2=48,e2=64` | +14, +18, +10 | +0,010 | +82, +0,004 | pasa / no pasa |
| `m=8,m2=63,e2=64` | -19, -3, -33 | -0,009 | -205, -0,023 | no pasa |

Lectura por familia:

- **(a) Suprimir las compras residuales chicas es lo único que gana, y lo hace en todas partes**: remuestreo, plausibles y estrés, los dos horizontes, las tres vistas a 20 000 ticks. Hay meseta de m = 6 a m = 16 y el óptimo medido (m entre 10 y 12) coincide con el punto de equilibrio de la sección 6. Con m = 24 o más empieza a suprimir órdenes que ganan.
- **No vender los restos chicos (mv) no sirve**: se queda con acciones fuera de la señal.
- **(b) Los topes pierden mucho.** `K=1` (una sola orden por lado, sin continuaciones) ahorra todas las comisiones de continuación y pierde 333 por ronda, porque deja fuera un tercio de la posición. A 20 000 ticks pierde 6 875. La fracción del patrimonio gana algo a 2000 ticks con 14/16 y pierde a 20 000: no pasa.
- **(c) Empezar antes con parte de la posición** tiene el patrón que ya se vio con el candidato `activo`: gana en el modelo y pierde en el remuestreo. El signo no se repite entre las dos evidencias, así que no es evidencia.
- **(c)(e) Completar más abajo** pierde: demora justo las órdenes residuales grandes, que son las que más ganan.
- **(c)(d) Salir antes o por tramos pierde en todas las vistas.** La salida anticipada proporcional a las órdenes que faltan, que era la idea más natural para posiciones de 3 a 6 órdenes, cuesta 0,04 a 0,16 puntos a 20 000 ticks.
- **(f) No recomprar** no cambia nada, porque las recompras casi no existen: gana menos de 1 de patrimonio por ronda de 2000 ticks y 4 por ronda de 20 000. El veredicto del arnés la marca como que pasa, porque esa diferencia es positiva en casi todas las series y su error es casi cero, y porque con H3b unos pocos pesos bastan para desempatar con el rival idéntico (sección 8.3). El veredicto literal no pasa y no vale nada en la práctica: no se cuenta como candidata. **Comprar solo en los primeros ticks** (la aproximación sin contabilidad) pierde: corta posiciones que necesitan más órdenes.
- **(f) El resto mediano solo más abajo** salió de la tabla de la sección 6: un resto de 8 a 24 acciones empata con su comisión si entra con la señal, pero gana si se manda solo cuando el precio llega un punto más abajo, donde cada acción rinde más. Mejora a `m=8` en +9 de patrimonio a 2000 ticks y +92 a 20 000 (parada). La meseta es ancha: m2 entre 16 y 32 con e2 entre 16 y 96 pasa en las 12 combinaciones, con dW entre +19 y +26.

## 8. Paso 4: las candidatas finales

| | Candidata A | Candidata B |
|-|-------------|-------------|
| Nombre en el arnés | `ejec:m=8` | `ejec:m=8,m2=24,e2=32` |
| Señal | La de `max_media`: E = 96, X = 0, k = 5 | La misma |
| Entrada | "Comprar 63" en cada tick con la señal adentro, salvo que la caja alcance para menos de 8 acciones (caja - 5 < 8 p): ahí mantiene | Igual, y además, si la caja alcanza para menos de 24 acciones, compra solo cuando dev < -128 (4 puntos bajo la media, uno más que la entrada) |
| Salida | "Vender 63" en cada tick con la señal afuera | Igual |
| Parámetros nuevos | 1 | 3 |
| Estado nuevo | Caja y acciones del espejo | Lo mismo |

A es la versión mínima: suprime solo órdenes que pierden en promedio (sección 6) y 8 p son tres sumas. B agrega el resto mediano solo más abajo; se eligió en el centro de su meseta y no en el máximo.

### 8.1 Criterio de corte

`mediciones/finales_veredictos.txt` (salida completa de `veredicto --parada`) y `mediciones/finales_sensibilidad.txt`. Conjunto evidencia, campo mixto, G = 10, semilla 0.

| Candidata | 2000 ticks: dH3a, p5 de tres rondas | 2000 ticks: dH3b, p5 | 20 000 interiores: dH3a, p5 | 20 000 interiores: dH3b, p5 | 20 000 parada: dH3a, dH3b | Veredicto | Literal | Pasa en |
|-----------|-------------------------------------|----------------------|------------------------------|------------------------------|----------------------------|-----------|---------|---------|
| `ejec:m=8` | +0,007 ± 0,000, +0,009 ± 0,004 | +0,027 ± 0,001, +0,022 ± 0,020 | +0,007 ± 0,000, +0,021 ± 0,007 | +0,050 ± 0,001, +0,078 ± 0,019 | +0,007, +0,048 | PASA | pasa | 9 de 9 |
| `ejec:m=8,m2=24,e2=32` | +0,012 ± 0,000, +0,019 ± 0,006 | +0,031 ± 0,001, +0,022 ± 0,022 | +0,010 ± 0,000, +0,026 ± 0,008 | +0,041 ± 0,001, +0,067 ± 0,023 | +0,011, +0,041 | PASA | pasa | 9 de 9 |

Las dos pasan las cuatro filas, el veredicto literal también pasa, y la fila de parada tiene el mismo signo que la de interiores. El percentil 5 no baja en ninguna fila (sube en todas, y el error que da el arnés es 2,8 veces el real).

### 8.2 Las cuatro hipótesis, evidencia y estrés, los dos horizontes

Diferencia pareada contra `max_media`, con su error. H2 en diferencia es la misma cifra de H1, porque comprar y mantener es igual para las dos; se informa además la diferencia de la razón W/B&H. Tablas completas, con remuestreo y plausibles por separado y con todas las series a 20 000 ticks, en `mediciones/finales_tablas.md`.

| Vista | Conjunto | Candidata | H1 y H2: patrimonio | H1: percentil 5 | H2: razón W/B&H | H3a: puntos | H3b: puntos |
|-------|----------|-----------|---------------------|-----------------|-----------------|-------------|-------------|
| 2000 ticks | evidencia | A | +14,8 ± 0,3 | +27 | +0,0019 ± 0,0001 | +0,0075 ± 0,0002 | +0,0268 ± 0,0007 |
| 2000 ticks | evidencia | B | +24,1 ± 0,8 | +61 | +0,0034 ± 0,0001 | +0,0119 ± 0,0004 | +0,0307 ± 0,0010 |
| 2000 ticks | estrés | A | +22,6 ± 1,4 | +65 | +0,0071 ± 0,0014 | +0,0061 ± 0,0002 | +0,0250 ± 0,0008 |
| 2000 ticks | estrés | B | +37,9 ± 3,9 | +70 | +0,0153 ± 0,0048 | +0,0098 ± 0,0004 | +0,0258 ± 0,0010 |
| 20 000, interiores | evidencia | A | +176 ± 3 | +140 | +0,0235 ± 0,0006 | +0,0066 ± 0,0002 | +0,0502 ± 0,0009 |
| 20 000, interiores | evidencia | B | +290 ± 7 | +218 | +0,0396 ± 0,0012 | +0,0103 ± 0,0004 | +0,0410 ± 0,0012 |
| 20 000, interiores | estrés (602 series) | A | +60 ± 7 | +178 | +0,0063 ± 0,0008 | +0,0087 ± 0,0009 | +0,0340 ± 0,0031 |
| 20 000, interiores | estrés (602 series) | B | **-113 ± 21** | +256 | -0,0106 ± 0,0023 | +0,0092 ± 0,0015 | +0,0099 ± 0,0040 |
| 20 000, parada | evidencia | A | +128 ± 2 | +67 | +0,0282 ± 0,0006 | +0,0067 ± 0,0001 | +0,0476 ± 0,0006 |
| 20 000, parada | evidencia | B | +220 ± 5 | +116 | +0,0548 ± 0,0014 | +0,0107 ± 0,0003 | +0,0413 ± 0,0008 |
| 20 000, parada | estrés | A | +54 ± 5 | +57 | +0,0182 ± 0,0024 | +0,0064 ± 0,0003 | +0,0330 ± 0,0013 |
| 20 000, parada | estrés | B | +41 ± 9 | +53 | +0,0276 ± 0,0035 | +0,0091 ± 0,0005 | +0,0276 ± 0,0016 |

- Por separado, a 2000 ticks: remuestreo A +12,0 ± 0,4 y B +22,0 ± 1,1; plausibles A +17,4 ± 0,4 y B +26,0 ± 0,8. El signo se repite en las dos evidencias y en el estrés.
- **Una celda negativa**: B pierde 113 ± 21 de patrimonio medio en el estrés interior a 20 000 ticks. Son 602 series, 400 de ellas de la familia `reversion`, que es donde el resto mediano más rinde. En puntos sigue positiva, y con la vista de parada (+41 ± 9) y con todas las series (+615 ± 60) el patrimonio también. A no tiene ninguna celda negativa.
- En patrimonio vale +0,14 % (A) y +0,22 % (B) por ronda de 2000 ticks, y +0,6 % y +1,0 % por ronda de 20 000 (parada).
- **En la serie de práctica** (`mediciones/finales_practica.txt`; informativo: son 10 bloques y una sola serie completa, no una muestra, y no se eligió nada con estas cifras). En los 10 bloques de 2000 ticks A da 11 070 de media contra 11 043 de `max_media` (+27 ± 18) con peor bloque 9 797 contra 9 620, y B da 11 045 (+2 ± 24) con peor bloque 9 810. En la serie completa de 20 000 ticks A termina en 26 567 y B en 26 683, contra 25 973 de `max_media`, con 606 y 596 órdenes en vez de 624. La regla base sigue arriba en esa serie (27 062), igual que en el estudio 1.

### 8.3 Cuánto de H3b es desempate

H3b sale 3 a 7 veces más grande que H3a y eso hay que leerlo con cuidado. Uno de los 61 rivales del arnés es exactamente `max_media` (`reversion:k=5,a=3,b=0`), con peso 0,67 % por rival en el campo ingenuo, 5,56 % en el mixto y 20 % en el fuerte. Con la lectura por puesto un empate vale medio puesto. Una candidata que es `max_media` más unos pocos pesos deja de empatar con ese rival y le gana, y cada vez que pasa suma 0,1 puntos con G = 10, aunque la ventaja sea de 3 pesos.

| Candidata | dH3b a 2000 ticks: campo ingenuo, mixto, fuerte | dH3a a 2000 ticks: ingenuo, mixto, fuerte |
|-----------|--------------------------------------------------|-------------------------------------------|
| `ejec:m=2` (gana 3 de patrimonio) | +0,003, +0,015, +0,052 | +0,001, +0,001, +0,002 |
| `ejec:m=8` | +0,010, +0,027, +0,081 | +0,004, +0,007, +0,010 |
| `ejec:m=8,m2=24,e2=32` | +0,015, +0,031, +0,081 | +0,008, +0,012, +0,016 |

Control (`mediciones/finales_desempate.txt`): la misma mejora puesta sobre una regla que no es idéntica a ningún rival (E = 112 en vez de 96), contra esa regla sin la mejora. Campo mixto, G = 10, conjunto evidencia.

| Mejora | Sobre `max_media`, que tiene un rival idéntico: dH3a y dH3b a 2000 ticks; a 20 000 interiores | Sobre E = 112, sin rival idéntico: dH3a y dH3b a 2000 ticks; a 20 000 interiores |
|--------|------------------------------|------------------------------|
| `m=2` | +0,001 y +0,015; +0,001 y +0,046 | +0,001 y +0,001; +0,002 y +0,001 |
| `m=8` | +0,007 y +0,027; +0,007 y +0,050 | +0,006 y +0,007; +0,008 y +0,007 |
| `m=8,m2=24,e2=32` | +0,012 y +0,031; +0,010 y +0,041 | +0,010 y +0,012; +0,012 y +0,011 |

Sin un rival idéntico la diferencia de H3b es la misma de H3a, y H3a casi no cambia. `m=2`, que gana 3 de patrimonio, vale +0,015 puntos con H3b contra `max_media` y +0,001 sobre E = 112: esos 0,014 son desempate. Con el campo fuerte, donde el rival idéntico pesa 20 %, llegan a +0,052 a 2000 ticks y +0,167 a 20 000.

El exceso de H3b sobre H3a es real solo si algún grupo llega exactamente a la misma regla que nosotros; en ese caso ganarle por poco vale medio puesto, y eso sí es un argumento a favor. Para decidir se usa H3a: **+0,007 puntos (A) y +0,012 (B) de un máximo de 2**, entre +0,004 y +0,023 según el campo, G y el largo de la ronda (`mediciones/finales_sensibilidad.txt`).

### 8.4 Meseta

- A: m de 6 a 16 da entre +12 y +17 de patrimonio a 2000 ticks y entre +104 y +149 a 20 000 (parada), siempre con veredicto PASA (sección 7). m = 8 queda del lado prudente de la meseta.
- B: las 12 combinaciones de m2 en {16, 24, 32} con e2 en {16, 32, 64, 96} pasan, con dW entre +19 y +26 a 2000 ticks y entre +172 y +235 a 20 000 (parada). Con el piso m en 4 o en 12 en vez de 8 da +21 a +24 (`mediciones/variantes_2.txt`).

### 8.5 Robustez: qué pasa si lo que el espejo supone no es cierto

`mediciones/finales_robustez.txt`. Diferencia de patrimonio contra `max_media`, conjunto evidencia. La estrategia supone caja 10 000 y comisión 5.

| Caso | 2000 ticks: A, B | 20 000 ticks, parada: A, B |
|------|------------------|-----------------------------|
| Caja real 5 000 | +0,4, +0,4 | +5, +5 |
| Caja real 9 000 | +0,7, +12,9 | +6, +100 |
| Caja real 10 000 (lo supuesto) | +14,8, +24,1 | +128, +220 |
| Caja real 11 000 | +9,5, +13,4 | -67, -37 |
| Caja real 12 000 | -21, -22 | -640, -657 (-2,5 %) |
| Caja real 15 000 | -203, -219 (-1,3 %) | -3 142, -3 237 (-10 %) |
| Caja real 20 000 | -657, -678 (-3,0 %) | -7 723, -7 840 (-19 %) |
| Caja real 100 000 | -6 065, -6 085 (-5,7 %) | -47 639, -47 756 (-30 %) |
| Comisión real 0 | -13, -22 | -986, -1 088 (-4 %) |
| Comisión real 2 | 0, -2 | -341, -374 (-1,5 %) |
| Comisión real 10 | +31, +59 | +117, +314 |
| Comisión real 50 | +44, +170 | +27, +108 |
| Espejo parte en 5 000, maestra en 10 000 | -209, -214 (-1,9 %) | -3 674, -3 730 (-17 %) |
| Espejo parte en 8 000 | -20, -24 | -664, -692 (-3,1 %) |
| Espejo parte en 9 500 | +16,5, +23,2 | +106, +159 |
| Espejo parte en 12 000 | +0,6, +7,5 | +6, +46 |
| Espejo parte en 20 000 | +0,6, +0,6 | +5, +4 |

- **El riesgo va en una sola dirección.** Si el espejo cree tener más caja que la real (menos caja real, más comisión real, espejo que parte alto), la candidata manda órdenes que la maestra recorta y se comporta como `max_media`: pierde la mejora y nada más. Si el espejo cree tener menos caja que la real, deja de comprar con caja disponible y nadie lo corrige: la maestra no devuelve nada.
- **Un error de 10 % en la caja borra la mejora; uno de 20 % cuesta 2,5 % en una ronda larga.**
- **Probabilidad de equilibrio** (calculado a partir de la tabla, no medido). A gana 0,14 % si todo es como se supone y pierde 3,0 % si la caja real es el doble, en rondas de 2000 ticks: la esperanza es cero si ese caso tiene una probabilidad de 0,14 / (0,14 + 3,0) = 4,5 %. En rondas de 20 000 ticks, 0,59 / (0,59 + 18,5) = 3,1 %. Para B, 6,7 % y 5,1 %. Si no se puede descartar con esa seguridad que la caja, la comisión o el reset sean distintos, la contabilidad propia resta en vez de sumar.
- **La comisión se acumula**: con comisión real 0 el espejo descuenta 5 de más en cada orden y después de cientos de órdenes cree tener miles menos.
- **La tercera parte de la tabla es la ronda que parte sin reiniciar la placa.** El enunciado dice que cada ronda parte con 10 000 y sin acciones. Si la placa no pasa por reset, el espejo sigue con la caja de la ronda anterior. Si esa ronda terminó con ganancia, el espejo parte alto y no pasa nada. Si terminó con pérdida o con la posición abierta, parte bajo.
- Los precios que se pierden en el reset del testbench no afectan: mientras el programa no arranca, `DECISION` vale 0 y la maestra no ejecuta nada.

### 8.6 Costo en instrucciones y memoria

No existe en assembly. Las cifras de esta sección son un conteo a mano sobre la aritmética de `ejec.c` y el estilo de `sw/trade.s` (Espino no tiene desplazamientos: 8 p son tres sumas y 63 p + 5 sale de 32 p, que la regla ya calcula). **Estimado.** Lo medido es la frecuencia de cada camino (`mediciones/finales_robustez.txt`, parte 4).

| Camino del tick | Instrucciones que agrega (estimado) | Total con las 27 de la regla | Frecuencia medida |
|-----------------|--------------------------------------|------------------------------|-------------------|
| Sin orden ejecutada: despacho y filtro | 11 | 38 | casi todos los ticks |
| Compra de 63 completa | 18 | 45 | unas 14 por ronda de 2000 ticks |
| Venta de 63 | 20 | 47 | unas 14 por ronda |
| Compra recortada: cociente (caja - 5) / p, menor que 63, con 6 restas de prueba | 51 | 78 | 9 a 10 por ronda (A), 8 (B) |
| Venta de un resto: producto de 6 por 8 bits, sin saltos | 62 | 89 | 9 a 10 por ronda (A), 8 (B) |
| B: comparación de dev con -(E + e2) | 5 más en todos | 94 en el peor | |

- **Peor tick: unas 90 instrucciones** contra 27. El conteo de `factibilidad/d_isa` para una contabilidad completa, con valorización del patrimonio, es 143 solo con RV32E. Las dos caben: en el core base son 200 a 340 ciclos de los 2 262 de la ronda más rápida (con el CPI de 2,15 a 2,35 medido en `trade.s`), y en el barrel 90 a 143 de las 540 instrucciones que tiene cada hilo por tick.
- **El cociente y el producto aparecen en el 1 % de los ticks** (0,8 a 1,0 %). El tick promedio queda en unas 40 instrucciones.
- **No justifica `mulstep` (+42 celdas) ni `divstep` (+108 celdas).** Bajarían el peor tick a unas 55 instrucciones, pero ese tick ocurre 20 veces por ronda y ya cabe con un margen de 7 veces. No hay nada que comprar con esas celdas.
- **Memoria** (estimado): 2 palabras de estado (caja y acciones; caben en registros, RV32E tiene 7 libres en `trade.s`) y entre 60 y 75 palabras de programa más, sobre las 40 que usa hoy, de 512.
- El programa actual no tiene saltos que dependan del precio (decisión T12). Con contabilidad el camino del tick depende de si hubo orden y de si fue recortada. Se puede hacer sin saltos, pagando siempre el peor caso (unas 90 instrucciones por tick).

## 9. Validación

`mediciones/validacion.txt` (`make validar`), todo en PASS:

| Prueba | Resultado |
|--------|-----------|
| `ejec` sin opciones contra `max_media`: patrimonio, órdenes y pérdida máxima de cada serie | 17 lotes de los dos largos, 25 011 series, 0 distintas |
| Espejo de la contabilidad contra la cuenta oficial del arnés, tick a tick, para 15 variantes (las dos finales y una de cada familia) | 165 240 000 ticks por variante, 0 ticks distintos |
| Control negativo: con otra caja real el espejo debe fallar | 5000 de 5000 series con el espejo distinto |
| Causalidad (comando `causal` del arnés) para 16 variantes | 78 comparaciones cada una, 0 fallas |
| Copia del núcleo de la cota contra el arnés (`make validar-cota`) | 391 842 corridas, 0 distintas (sección 5) |
| `descomp` contra `correr_serie` | 0 series distintas en todos los conjuntos |

## 10. Variantes probadas y sobreajuste

- **61 variantes** de `ejec`, todas en `herramientas/variantes.txt` (37, más el control sin opciones, que da cero en todo) y `herramientas/variantes2.txt` (24), más las 4 de la cota, que no son candidatas. Fuera de esas listas solo se corrieron las 3 del control del desempate (la misma mejora sobre E = 112, sección 8.3) y las de robustez (el espejo con otra caja inicial, sección 8.5): se corrieron después de fijar las candidatas y no se eligió nada con ellas.
- De las 37 de la primera lista pasan 8 el veredicto del arnés: las 7 de la misma familia (m entre 2 y 16), con el mismo signo en remuestreo, plausibles y estrés, y `nr=1`, que gana menos de 1 de patrimonio por ronda y no pasa el veredicto literal. No es una variante que sale buena entre veinte: es una familia entera con meseta, y el tamaño que se midió (+14,8) es el que predice la descomposición hecha antes sobre `max_media` (+13,7).
- La segunda lista se armó después de mirar la tabla de órdenes por tamaño, o sea con información de la semilla 0. Tiene 2 parámetros más. Pasan 18 de 24 y las 6 que no pasan están en el borde donde el resto "mediano" ya es una orden grande (m2 de 48 con e2 de 64 o 96, y m2 de 63).
- B tiene más grados de libertad que A y una celda negativa (sección 8.2). Si la semilla reservada no confirma la ventaja de B sobre A, la candidata es A.
- Todo se eligió con la semilla 0. Las candidatas van al estudio de cierre con los parámetros fijados.

## 11. Respuestas

**¿Conviene llevar contabilidad propia en la edición de competencia?** Con el criterio de corte escrito, sí pasa: mejora los puntos esperados sin empeorar el percentil 5, en los dos horizontes y en las 9 combinaciones de campo y G (semilla 0; falta la reservada). Pero vale poco y abre un modo de falla nuevo. Conviene solo con dos confirmaciones del ayudante: caja inicial 10 000 y comisión 5 definitivas, y reset de la placa antes de cada ronda. Si alguna no se puede confirmar, no conviene: la mejora es de +0,14 a +0,22 % de patrimonio y el error en la dirección mala cuesta de 3 a 30 %.

**¿Cuántos puntos esperados vale?** +0,007 (A) y +0,012 (B) de 2 con H3a, a los dos horizontes. Con H3b, +0,027 y +0,031 a 2000 ticks y +0,05 y +0,04 a 20 000, pero la mayor parte es desempate contra un rival idéntico (sección 8.3). En patrimonio, +15 y +24 por ronda de 2000 ticks y +128 y +220 por ronda de 20 000 (parada). La cota era +0,036 y +0,073 puntos.

**¿Qué regla de entrada y salida se recomienda?**

1. Entrada: "comprar 63" en cada tick mientras la señal diga adentro. Sin escalones, sin empezar antes y sin tope. La maestra recorta la última orden.
2. Salida: "vender 63" en cada tick mientras la señal diga afuera. Sin anticipar y sin tramos.
3. Opcional, con contabilidad propia: no mandar la compra cuando la caja alcanza para menos de 8 acciones al precio actual (A). Y si se confirma con la semilla reservada, mandar el resto de menos de 24 acciones solo con el precio 4 puntos bajo la media (B).

Es la regla que ya está en `sw/trade.s`, con una condición más. El resultado del estudio es que la forma actual de entrar y salir ya es la buena, y que lo que cuesta el límite de 63 son comisiones que no dependen de nosotros.

## 12. Cumplimiento de las reglas

- "La decisión se debe calcular en el Espino Core": se cumple. Nada de esta carpeta corre en la placa. Las candidatas son el mismo programa con dos palabras de estado y más instrucciones, sin hardware nuevo.
- "No se puede usar información externa a la serie recibida por SPI ni almacenar series de precios en el diseño": se cumple. El espejo se calcula con los precios recibidos y las decisiones propias. La caja inicial y la comisión son reglas del enunciado, no datos de la serie. Los umbrales m, m2 y e2 son hiperparámetros elegidos con la semilla 0, igual que E y X. No hay tablas.
- "Todo hardware agregado debe estar en el repositorio con su testbench": no se agrega hardware.
- "Deben usar el mismo programa para todas las series de tiempo": se cumple.
- El enunciado permite expresamente la contabilidad propia (sección 2.4).
- Aritmética: enteros, sumas, restas, comparaciones y desplazamientos por constantes. Un producto de precio por acciones (6 por 8 bits) al vender un resto y un cociente de 6 bits al recortar una compra, contados aparte (sección 8.6). Sin punto flotante.
- La copia del núcleo de la cota y la estrategia `lim` no son candidatas: evalúan una maestra que no existe.

## 13. Riesgos

1. **Caja inicial o comisión distintas de las supuestas** (sección 8.5). El enunciado dice que los valores publicados son referenciales y que los definitivos se publican con la serie de práctica; el testbench trae 10 000 y 5. Es la pregunta 10 para el ayudante. Si el día de la competencia anuncian otros valores hay que regenerar el programa con las constantes nuevas.
2. **Ronda sin reset.** Si las tres rondas se corren seguidas sin reiniciar la placa, el espejo arrastra la caja de la ronda anterior. No se diseñó ni se probó un detector de ronda nueva.
3. **Un tick perdido a mitad de ronda** desincroniza el espejo para el resto de la ronda. La regla actual no tiene ese problema. No se midió.
4. **H3b está inflado por el desempate** contra un rival idéntico. La cifra para decidir es la de H3a.
5. **Toda la evidencia sale de una serie de práctica** y del modelo ajustado a ella, igual que en los estudios 1 y 2. La ganancia por acción (0,97) fija el punto de equilibrio de m; con otra volatilidad sería otro. En el estrés la mejora se mantiene.
6. **El conteo de instrucciones es a mano.** No hay assembly de la contabilidad en el repositorio.

## 14. Qué falta y qué no se verificó

- Las semillas reservadas no se usaron. El veredicto es de la semilla 0.
- No existe el programa en assembly ni la referencia en `ref/trader.py`. No se corrió en el gemelo digital ni en el RTL.
- No se midió qué pasa si se pierde un tick a mitad de ronda ni si una ronda parte con el espejo en posición abierta (se midió el espejo con otra caja, que es el efecto principal).
- No se probó un detector de ronda nueva ni un espejo que se proteja solo.
- No se probaron valores de m entre los de la lista (14, 20) ni una función continua de la profundidad para el resto.
- La vista de parada se corrió para todas las variantes solo con el conjunto evidencia, que es lo que entrega el arnés.
- La cifra de 143 instrucciones es de `factibilidad/d_isa` y no se volvió a contar.

## 15. Días de trabajo para calidad de competencia

Estimado, para la candidata A o la B (la diferencia entre las dos es una comparación):

| Tarea | Días |
|-------|------|
| `ref/trader.py` con el espejo y el filtro, y sus pruebas contra `ref/market.py` | 0,5 |
| `sw/trade.s`: espejo, cociente de 6 restas, producto de 6 por 8 bits, filtro | 1,0 |
| Equivalencia: `make equiv`, gemelo a los tres períodos, testbench oficial con 4/4, core segmentado | 0,5 |
| Matriz de estrés: caja, comisión, ronda sin reset, tick perdido. Decidir qué hacer con la ronda sin reset | 0,5 |
| Bitstream, documento de estudio y preguntas de defensa | 0,5 |
| Total | 3,0 |

Tiene que estar en el bitstream que se pruebe con la maestra real el 26/11.

## 16. Veredicto según los criterios de corte

| Pieza | Veredicto | Razón |
|-------|-----------|-------|
| Regla actual de entrada y salida (repetir "comprar 63" y "vender 63") | **Competencia**, se mantiene | Ninguna forma de escalonar, limitar o anticipar la supera |
| `ejec:m=8` (no mandar compras de menos de 8 acciones) | **Pasa el criterio de algoritmo** con la semilla 0, pendiente de la reservada. Competencia solo si se confirman caja, comisión y reset por ronda; si no, exhibición | +0,007 puntos (H3a), percentil 5 no baja, 9 de 9 combinaciones, parada confirma. No agrega hardware. Riesgo de 3 a 30 % si el espejo parte bajo |
| `ejec:m=8,m2=24,e2=32` (además, el resto mediano solo más abajo) | **Pasa el criterio de algoritmo** con la semilla 0, pendiente de la reservada. Mismas condiciones | +0,012 puntos (H3a). Dos parámetros más y una celda negativa en el estrés interior a 20 000 ticks |
| Tope en K órdenes o en una fracción del patrimonio | Descartada | Baja los puntos esperados |
| Entrada escalonada o anticipada | Descartada | El signo no se repite entre remuestreo y plausibles |
| Tamaño según la profundidad (completar más abajo) | Descartada | Baja el patrimonio y los puntos |
| Salida escalonada y salida anticipada proporcional | Descartada | Baja los puntos en todas las vistas |
| No recomprar; comprar solo en los primeros ticks | Descartada | No cambia nada; pierde |
| `mulstep` y `divstep` para la contabilidad | No se justifican | El peor tick cabe en software con margen de 7 veces y ocurre en el 1 % de los ticks |

Elegir es decisión de Nicolás. Este estudio no tocó `ref/trader.py`, `sw/trade.s` ni ningún archivo fuera de esta carpeta.
