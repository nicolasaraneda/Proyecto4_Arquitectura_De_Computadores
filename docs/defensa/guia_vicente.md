# Guía de estudio: Vicente

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Según `docs/defensa/plan_estudio.md`, sección 2, Vicente es dueño de **el algoritmo, el protocolo de evaluación, `sw/trade.s` y el co-diseño** (variantes, Amdahl, roofline, PLL, ASIC). Cubre completos los puntos 3.1, 3.2 y 3.3 del informe. En la presentación de 5 minutos dice el primer bloque (`docs/defensa/guiones.md`).

## 1. Qué leer, en orden

1. `docs/defensa/algoritmo.md` y `docs/protocolo.md`: la serie revierte, cómo se mide sin engañarse (bloques, remuestreos, familias, semilla reservada).
2. `docs/zscore.md` (nuevo): su propia regla bajo el protocolo. Sección 4.5 completa: con trozos de 100 pierde, con trozos de 250 o más gana, también eligiendo en una mitad y probando en la otra. Es la pregunta más probable de la defensa.
3. `docs/trade_s.md` y `docs/defensa/espino_base.md`, sección 5: punto fijo, multiplicar por 32 con sumas, dividir leyendo un byte, sin saltos que dependan del precio.
4. `docs/codiseno.md`: la tabla de variantes, Amdahl medido contra predicho, la escalera de la clase 7 y el roofline.
5. `docs/defensa/cifras.md`, sección del algoritmo.

## 2. Lo que tiene que poder dibujar sin mirar

- La regla de `max_media` en cuatro líneas (`dev`, entra, sale, media) y por qué repetir "comprar 63" no paga comisión.
- La tabla del largo del trozo de `docs/zscore.md`, sección 4.5, y por qué los errores de los trozos largos son optimistas.
- La ley de hierro aplicada a cada variante: segmentado y barrel atacan el CPI, la extensión el IC, el PLL atacaría Tclk y no existe en el VQ100.

## 3. Cifras de memoria

| Cifra | Valor | Fuente |
|-------|-------|--------|
| Serie de práctica | VR(10) 0,77, VR(50) 0,62, VR(100) 0,53; autocorrelación -0,11 | `docs/algoritmo.md` |
| Práctica completa | `max_media` 25 973; regla base 27 062; comprar y mantener 6 497; `zscore` 40 957 | `ref/trader.py`, `ref/zscore.py` |
| Bloques | `max_media` 11 043, peor 9 620; `zscore` 11 389, peor 9 859 | `docs/mediciones/zscore/protocolo_s0.txt` |
| `zscore` contra `max_media` por largo de trozo | 50: -56; 100: +7; 250: +160; 1000: +313 | `docs/mediciones/zscore/trozos.txt` |
| Presupuestos por tick | 249 762, 24 762 y 2 262 ciclos | `docs/defensa/cifras.md` |
| `trade.s` | IC 19,5 y 21; CPI 2,10; 41 y 44 ciclos | `docs/mediciones/ticks_software.txt` |
| Fondo contra `max_media` | +0,007 puntos a 2000 ticks, -0,005 a 20 000 | decisión T50 |

## 4. Preguntas del banco que responde en profundidad

- **Avanzadas [A]**: 13, 14, 15, 19, 20, 22, 27, 28, 29, 30, 31, 33, 35, 40, 41, 43, 47, 48, 141, 142 y 146.
- **Incómodas [I] de su pieza**: 12, 18, 23, 24, 25, 26, 34, 145 y **156** (por qué no usaron la regla que da 40 957). La 156 cambia según lo que decida Nicolás sobre `zscore`: hay que repasarla después de esa decisión.
- **Básicas [B]**: las 53 del banco.

## 5. Lo que tiene que saber de las piezas de los otros

- De Nicolás: por qué el base tiene CPI 2 y qué hace el barrel (diagramas, secciones 2 y 4).
- De Santiago: qué hace el fondo con los votos y por qué no suma puntos (pregunta 3), y el árbol del 1/12.

## 6. Plan

| Fecha | Qué |
|-------|-----|
| Hasta el 18/11 | Puntos 1 a 3 de la sección 1; la tabla del largo del trozo de memoria |
| 21/11 | Prueba de práctica 1, preguntando a Santiago la parte de algoritmo |
| 24/11 | Repaso de todas las [I]; ensayar la 156 en voz alta con la decisión ya tomada |
| 27/11 | Agregar al banco lo que salga del 26/11 sobre el generador de las series |
| 30/11 | Guion de 5 minutos con cronómetro y prueba de práctica 3 |
