# Reglas "cotas" para series normalizadas entre 100 y 255

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio en construcción (17/11). Referencia: `ref/cotas.py`. Pruebas: `python3 ref/test_cotas.py`.

## 1. La observación

Desde el 17/11 la serie de práctica es `data/practica_meta.csv`: 20 000 precios reales de Meta, uno por minuto de mercado (febrero a mayo de 2022), normalizados de modo que el mínimo es exactamente 100 y el máximo exactamente 255. Las series de la competencia serán períodos ocultos de Meta, Apple, Netflix, AMD o Tesla entre 2022 y 2024, normalizados de la misma forma.

Si cada ronda se normaliza por separado, el precio de la ronda nunca sale de [100, 255] y toca los dos extremos. Ver 100 es ver el mínimo de la ronda: comprar ahí no puede salir peor que comprar en cualquier otro momento. Ver 255 es ver el máximo.

**Supuesto clave, sin confirmar:** que la normalización es por ronda. Si la ronda fuera un trozo de un período normalizado más largo, puede no tocar ningún extremo (sección 5, caso d). Es la primera pregunta para el ayudante (`docs/clase_18nov.md`, sección 3).

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

Pendiente (paso 5 del 17/11): ventanas de las cinco empresas normalizadas entre 100 y 255, con largos de 2 000, 5 000 y 20 000 ticks, separando empresas o años para ajustar y validar; "espera" contra "compra" y versiones intermedias; qué hacer después de los dos extremos; márgenes; el caso en que la hipótesis es falsa; torneo.
