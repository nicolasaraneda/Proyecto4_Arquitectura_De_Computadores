# Reglas "cotas" para series normalizadas entre 100 y 255

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio en construcción (17/11). Referencia: `ref/cotas.py`. Pruebas: `python3 ref/test_cotas.py`.

## 1. La observación

Desde el 17/11 la serie de práctica es `data/practica_meta.csv`: 20 000 precios reales de Meta, uno por minuto de mercado (febrero a mayo de 2022), normalizados de modo que el mínimo es exactamente 100 y el máximo exactamente 255. Las series de la competencia serán períodos ocultos de Meta, Apple, Netflix, AMD o Tesla entre 2022 y 2024, normalizados de la misma forma.

Como cada ronda se normaliza por separado, el precio de la ronda nunca sale de [100, 255] y toca los dos extremos. Ver 100 es ver el mínimo de la ronda: comprar ahí no puede salir peor que comprar en cualquier otro momento. Ver 255 es ver el máximo.

**Hecho confirmado (Nicolás, 21/11):** cada ronda llega normalizada por separado, así que su mínimo es 100 y su máximo 255. Antes de esa fecha esto era un supuesto; la sección 5 evaluó el caso contrario (una ronda que fuera un trozo de un período más largo, sección 5, caso d) y queda como análisis de sensibilidad, no como riesgo vigente.

**¿Es información externa a la serie?** No: es el formato de la serie que anunció el profesor, igual para todos los grupos, como que los precios son de 8 bits. La regla no guarda ninguna serie ni usa datos de fuera; decide con el precio que ve. Igual se deja como pregunta de defensa.

## 2. La regla

| Al ver | Decide |
|--------|--------|
| p = 100 | comprar 63 (repetido: la maestra compra lo que alcance) |
| p = 255 | vender 63 (repetido) |
| entre medio | mantener la posición (repite el último byte) |

Variantes: "espera" parte en caja; "compra" parte comprando con el primer precio. `ref/cotas.py` agrega márgenes (comprar desde 100 + a, vender desde 255 - b), compra parcial al inicio, decisión según el primer precio y una banda después de ver los dos extremos.

## 3. Comprobación con las cifras de Nicolás (serie Meta completa)

| Variante | Patrimonio | Órdenes | Cifra de Nicolás |
|----------|-----------|---------|------------------|
| espera | 15 894 | 2 | 15 894 con 2 |
| compra | 23 906 | 5 | 23 906 con 5 |
| compra, y después de ver los dos extremos banda de 40 (compra con p ≤ 140, vende con p ≥ 215) | 32 149 | 8 | 32 149 |

Para comparar: `max_media` da 9 722 y `zscore` 7 340 en la misma serie; no operar, 10 000.

## 4. Estructura de la serie Meta

- 20 000 ticks son 51,2 días de 390 minutos. Las aperturas caen en los ticks 40 + 390 k (52 en la serie): el salto medio absoluto en una apertura es 6,4 unidades, contra 0,44 dentro del día. El mayor es +76 en el tick 17 200 (la apertura después del informe de resultados de abril de 2022).
- El máximo (255) aparece una sola vez, en el tick 10 965, a 5 minutos de una apertura. El mínimo (100) aparece 6 veces, entre los ticks 17 084 y 17 143, en la tarde del día anterior al salto de +76.
- Por eso en esta serie "espera" ve primero el 255 sin acciones y no gana nada con él, y "compra" lo aprovecha.

## 5. Evaluación sobre la población real

### 5.1 Datos y modelo

No hay datos por minuto gratuitos de 2022 a 2024 sin cuenta (`docs/pendientes_nicolas.md`, acción 3b). Se usaron:

- **Precios diarios reales** de META, AAPL, NFLX, AMD y TSLA de diciembre de 2021 a enero de 2025 (Yahoo, sin clave; quedan en `data/externos/`, fuera del repositorio).
- **Minutos rellenados con la forma de días reales de la serie Meta** (`ref/cotas/poblacion.py`): cada día toma la forma de un día de la serie del profesor, sorteado, llevada de la apertura al cierre y estirada hacia el 89 % del exceso del máximo y del mínimo (la fracción medida en la serie Meta contra sus diarios). Los saltos de apertura, la tendencia de varios días y el día de cada extremo son reales.
- **Días de la serie Meta sorteados** y encadenados por sus retornos, como segunda población.
- **La serie del profesor ubicada en el calendario**: son los minutos de Meta del 23/2/2022 a las 15:10 al 9/5/2022, sin ajustes. Sus cierres diarios caen sobre la serie con error cuadrático medio de 0,31 unidades (el redondeo), y la normalización es lineal con los extremos de la ventana: 171,61 USD es 100 y 236,56 USD es 255.

**Validación del modelo** (`docs/mediciones/cotas/modelo.txt`, 50 réplicas de la misma ventana de la serie del profesor):

| Regla | Serie real | Modelo, mediana (p10 a p90) |
|-------|-----------|------------------------------|
| espera | 15 894 | 16 387 (15 160 a 17 217) |
| compra | 23 906 | 24 934 (22 836 a 25 849) |
| compra con banda 40 | 32 149 | 31 797 (29 070 a 32 467) |
| `max_media` | 9 722 | 9 848 (5 978 a 12 033) |
| `zscore` | 7 340 | 7 220 (5 371 a 11 054) |

Un primer modelo con puente browniano reproducía las reglas de extremos pero inflaba las de reversión (`max_media` 15 000): el puente fijado en la apertura y el cierre agrega reversión dentro del día. Se descartó para el torneo.

### 5.2 Resultados (población de las cinco empresas, 1200 ventanas por largo)

Patrimonio final desde 10 000; "> nada" y "> max_media": porcentaje de ventanas en que la estrategia termina por encima. Completo en `docs/mediciones/cotas/variantes.txt`.

| Estrategia | 2000: media | p5 | peor | > nada | 20 000: media | p5 | peor | > max_media |
|------------|------------|----|------|--------|--------------|----|------|------------|
| no operar | 10 000 | 10 000 | 10 000 | | 10 000 | 10 000 | 10 000 | 39 % |
| comprar y mantener | 11 944 | 4 600 | 3 950 | 55 % | 12 433 | 4 721 | 3 950 | 56 % |
| `max_media` | 11 848 | 5 486 | 3 076 | 55 % | 11 680 | 6 192 | 1 453 | |
| `zscore` | 10 892 | 6 613 | 3 736 | 56 % | 10 472 | 5 986 | 3 036 | 35 % |
| espera | 18 959 | 10 101 | 8 595 | 96 % | 20 112 | 10 281 | 9 324 | 91 % |
| compra | 17 888 | 10 940 | 8 311 | 99 % | 18 790 | 11 215 | 9 823 | 91 % |
| comprar 20 al inicio | 18 631 | 10 708 | 8 935 | 99 % | 19 725 | 11 158 | 9 568 | 93 % |
| espera, banda 60 | 19 863 | 10 149 | 8 796 | 96 % | 20 511 | 10 281 | 9 324 | 92 % |
| espera, banda 70 | 19 991 | 10 149 | 9 150 | 96 % | 20 630 | 10 284 | 9 324 | 91 % |
| comprar 20, banda 70 | 19 669 | 10 766 | 8 845 | 99 % | 20 266 | 11 214 | 9 568 | 93 % |
| compra, banda 40 | 18 520 | 10 948 | 7 792 | 99 % | 19 384 | 11 230 | 9 823 | 91 % |

Con 5 000 ticks y con los días de Meta sorteados el orden es el mismo.

**a. Espera contra compra.** "Espera" gana en media (de 1 000 a 1 300 más) y "compra" en el percentil 5 (unos 800 más) y en la probabilidad de terminar sobre no operar (99 % contra 96 %). Comprar una parte al inicio (20 acciones) queda entre las dos. Decidir según el primer precio no mejora a ninguna.

**b. Después de ver los dos extremos.** Una banda (comprar con p ≤ 100 + w, vender con p ≥ 255 - w) mejora a "espera" en 400 a 1 000 de media. La meseta va de w = 40 a w = 76 (todas a menos del 2 % de la mejor en cada corte); el centro es 60. La banda de 40 que da 32 149 en la serie del profesor es la mejor allí con "compra", pero en la población "compra con banda" queda bajo "espera con banda".

**c. Márgenes.** Comprar desde 100 + a o vender desde 255 - b no ayuda: con a = 2 la media baja y el peor caso empeora (la orden se ejecuta al precio siguiente y el extremo exacto ya es el mejor punto).

**Ajuste y validación** (`docs/mediciones/cotas/seleccion.txt`): eligiendo en 2022 y 2023 y probando en 2024, o eligiendo con META, AAPL y NFLX y probando con AMD y TSLA, la mejor variante del ajuste es siempre "espera con banda" de 50 a 76, y en la validación da de 19 200 a 22 100 de media según el largo, contra 9 600 a 13 400 de `max_media`.

### 5.3 Si la hipótesis es falsa (caso d)

Rondas que son trozos de una ventana de 20 000 normalizada, sin normalizar de nuevo (`docs/mediciones/cotas/hipotesis_falsa.txt`). Con trozos de 2000 solo el 20 % toca algún extremo:

| Estrategia | media | p5 | peor |
|------------|-------|----|------|
| no operar | 10 000 | 10 000 | 10 000 |
| `max_media` | 10 078 | 8 444 | 5 094 |
| espera (con o sin banda) | 10 297 | 10 000 | 9 990 |
| comprar 20 al inicio (con o sin banda) | 10 293 | 9 055 | 7 915 |
| compra | 10 360 | 7 241 | 5 400 |

"Espera" no pierde más que una comisión cuando la hipótesis falla: si no ve un extremo, no opera. "Compra" pierde como comprar y mantener.

### 5.4 Torneo (caso e)

En cada ronda, 9 rivales sorteados; puntos lineales entre el peor y el mejor de la ronda (`docs/mediciones/cotas/torneo.txt`). Largo 5000:

| Estrategia | rivales sin extremos | un tercio con extremos | dos tercios con extremos |
|------------|---------------------|------------------------|--------------------------|
| `max_media` | 0,455 | 0,262 | 0,206 |
| espera | 0,946 | 0,852 | 0,809 |
| espera, banda 60 | 0,950 | 0,859 | 0,820 |
| comprar 20, banda 70 | 0,958 | 0,856 | 0,813 |
| compra | 0,932 | 0,809 | 0,752 |

Con rivales que también usan los extremos, "espera con banda" queda primera en el 48 a 57 % de las rondas; "comprar 20 con banda", en el 14 a 32 %.

### 5.5 Conclusión

- **Como cada ronda se normaliza por separado, las reglas de extremos dominan**: casi duplican el patrimonio y superan a `max_media` en más del 90 % de las ventanas, en las cinco empresas, en los tres largos y en las dos validaciones.
- **Recomendada el 17/11: "espera" con banda 60** (centro de la meseta). **Desde el 19/11 compite la banda 40 (T140)**, elegida con los minutos reales de Alpaca: +205 por ronda con error estándar 101 sobre todas las ventanas reales, y la que menos pierde contra el rival de Tesla de la clase del 18/11 (`docs/decisiones.md`, T140). En la ronda de Tesla da 20 795 contra 18 779 de la banda 60, en AMD 26 470 contra 21 895 y en la serie Meta 21 392 contra 19 214. Es la de mayor media y mayor puntaje cuando otros grupos usan los extremos, y la única que no pierde si la hipótesis es falsa.
- **Alternativa: comprar 20 al inicio con banda 70.** Mejor percentil 5 y más puntaje si nadie más usa los extremos, pero pierde hasta 2 100 si la hipótesis es falsa.
- **Lo que no se sabe**: cómo es la forma por minuto de las otras cuatro empresas (el modelo usa la de Meta; con los minutos reales de Alpaca se puede repetir todo con `python3 ref/cotas/experimento.py`).

Se reproduce con `python3 ref/cotas/validar.py` (el evaluador en C contra las referencias en Python), `python3 ref/cotas/validar_modelo.py` y `python3 ref/cotas/experimento.py` (20 segundos).

## 6. Plan B: si las rondas son trozos de una serie normalizada más larga

Pedido de Nicolás del 18/11: la mejor regla si la respuesta es que cada ronda es un trozo de una serie normalizada más larga y no toca los extremos. Es justo lo que hace el testbench oficial con la serie de práctica: corre los primeros 2000 ticks de una serie de 20 000 normalizada entera. `ref/cotas/planb_experimento.py`, salidas en `docs/mediciones/cotas/planb.txt` (madre de 20 000) y `planb_madre50000.txt` (madre de 50 000).

**Familias probadas** (145 variantes, validadas contra sus referencias en Python con `ref/cotas/validar.py`):

- **Posición en el rango sin tocar los extremos** ("rango"): compra bajo L, vende sobre H, de L = 110 a 180 y H hasta 250; con y sin compra al inicio si el primer precio es bajo.
- **Saltos de apertura** ("salto"): a favor o en contra de saltos de 3, 5 u 8 unidades, saliendo 30, 60, 120 o 390 precios después.
- **Tendencia**: cruce de medias de 8 a 1024 precios.
- **Reversión**: `max_media` y otros umbrales, `zscore`.
- **Cotas con márgenes**: comprar desde 100 + a y vender desde 255 - a, sin esperar el extremo exacto.

**Resultado (primer trozo de cada ventana, validación):**

| Separación | Largo | Elegida en el ajuste | Media en la validación | Termina bajo 10 000 | Peor |
|------------|-------|----------------------|------------------------|---------------------|------|
| Por años, madre 20 000 | 2000 | espera con banda 60 | 10 885 | 1,1 % | 9 892 |
| Por años, madre 20 000 | 5000 | espera con banda 60 | 12 227 | 0 % | 10 000 |
| Por empresa, madre 20 000 | 2000 | espera con banda 60 | 10 483 | 0 % | 10 000 |
| Por empresa, madre 20 000 | 5000 | espera con banda 60 | 11 432 | 0,4 % | 9 830 |

Con una madre de 50 000 el ajuste elige la misma regla en los cuatro cortes (media de 10 330 a 10 900 en la población).

**Por qué la misma regla sigue ganando.** Aunque la ronda sea un trozo, el primer trozo de una serie normalizada toca algún extremo mucho más que su proporción del largo: el 44 % de las veces con 2000 ticks de 20 000 (el 10 % del largo). Es la ley del arcoseno: el máximo y el mínimo de un camino al azar tienden a caer cerca de sus bordes. Cuando la ronda toca un extremo, la regla lo aprovecha; cuando no, no opera y no pierde.

**Si la ronda fuera un trozo cualquiera** (no el primero), los extremos aparecen en el 8 a 21 % de las rondas y "espera con banda 60" queda apenas sobre no operar (10 070 a 10 280). Ahí las de mayor media son "comprar al inicio si el primer precio es 190 o menos, y operar un rango" (de 10 200 a 11 300), pero con pérdidas de hasta 50 % en el peor caso y bajo 10 000 en una de cada cuatro rondas.

**Conclusión del plan B.** Ninguna de las familias nuevas le gana a la regla elegida cuando la ronda es el primer trozo, que es lo que hace el testbench oficial. **La opción de bajo riesgo para el plan B es la misma regla ya elegida**: no hay que cambiar nada. Si se confirmara que las rondas son trozos tomados al azar en medio de la serie, la regla queda como "casi no operar" (no pierde), y la alternativa de más media (comprar al inicio con precio bajo, más un rango) cambia esa seguridad por un riesgo grande.
