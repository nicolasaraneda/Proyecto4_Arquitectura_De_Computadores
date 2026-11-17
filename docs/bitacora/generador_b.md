# Bitácora: tarea B, último intento con el generador (17/11)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Objetivo, acordado el 16/11 como último intento de identificar el generador, acotado a esa noche: la probabilidad de ganarle cabeza a cabeza a `max_media` y los puntos esperados contra un campo de rivales que también operan reversión con parámetros variados, con el mismo protocolo contra el sobreajuste. Un candidato solo se acepta si además gana sobre la serie que se registre el 26/11; si nada gana, se documenta y se cierra el tema. Con la corrección del 16/11: el rival a vencer es el mejor entre `max_media` y `zscore`; como `zscore` no le gana a `max_media` (T129), el rival es `max_media`. Rama `generador`.

## 1. Herramienta

- `ref/torneo_b/torneo_b.c`: copia de `factibilidad/retorno/nucleo/torneo.c` con un campo más, **`variados`**: los 10 rivales de cada ronda se sortean entre las 25 parametrizaciones de la clase de reversión, todas con la misma probabilidad (umbral de entrada de 2 a 6, salida 0 o 1, media exponencial o suma móvil, momentum invertido). Incluye a `max_media` y a la regla base como dos rivales más. Sin pedir ese campo, la salida es la del original.
- `ref/torneo_b/busqueda.py`: grilla de la regla de reversión (memoria 16, 32 o 64; entrada de 2 a 5 unidades; salida de -1 a +0,5) y de `zscore`, 78 candidatas, contra `max_media`.

## 2. Exploración con la semilla 0

| Vista | Mejor candidata | dH3a | dH3b | En el campo mixto |
|-------|-----------------|------|------|-------------------|
| 2000 ticks, `variados` | entra 2,5, sale +0,5 | +0,019 +- 0,006 | +0,012 +- 0,006 | -0,020 en H3a |
| 20 000 ticks interiores, `variados` | entra 2,5, sale +0,5 | +0,075 +- 0,007 | +0,077 +- 0,007 | (no corrido) |

Lo que se lee: contra rivales que hacen todos reversión, conviene entrar un poco antes (2,5 unidades bajo la media en vez de 3) y salir un poco después (media unidad sobre la media). Contra el campo mixto, `max_media` sigue siendo la mejor. Es el máximo de 78 candidatas: sin confirmar con otra semilla no vale nada.

## 3. Finalistas para la semilla 5 (fijados antes de correrla)

Regla de elección escrita antes de mirar la vista de parada: las tres mejores por dH3a + dH3b a 20 000 ticks (interiores, campo `variados`) que no pierden en ninguna de las dos lecturas a 2000 ticks en el mismo campo.

1. Entra 2,5, sale +0,5 (`param:k=5,E=80,X=16`).
2. Entra 2,5, sale 0 (`param:k=5,E=80,X=0`).
3. Entra 3, sale +0,5 (`param:k=5,E=96,X=16`): `max_media` con la salida media unidad más arriba.

(Entra 2, sale +0,5 quedó fuera: pierde en H3b a 2000 ticks.)

La semilla 5 no se había usado. Se corre una vez: criterio de corte en el campo `variados` y en el mixto, a los dos largos con la vista de parada, duelo cabeza a cabeza y el protocolo de `ref/protocolo.py`.

## 4. Semilla 5 (corrida una vez, 17/11, por la cola de trabajos pesados)

`docs/mediciones/generador_b/reservada_s5.txt`, `duelo_n2000_s5.txt`, `duelo_n20000_s5.txt`. La primera corrida murió con la caída de WSL después de la primera de seis filas; se repitió entera (es determinista: la fila que se alcanzó a ver es igual).

- Entra 2,5, sale +0,5: no pasa en `variados` (a 2000 ticks el percentil 5 de H3b baja), no pasa en el mixto.
- Entra 2,5, sale 0: no pasa en ninguno.
- **Entra 3, sale +0,5: pasa en `variados`** (las cuatro filas), no pasa en el mixto (H3a -0,011 y -0,019).
- Protocolo: las tres pierden en los bloques y en los remuestreos y ganan en las familias plausibles.
- Cierre: T131, `docs/generador_b.md`.
