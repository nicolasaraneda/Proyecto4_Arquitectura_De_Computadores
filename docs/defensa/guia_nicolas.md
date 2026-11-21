# Guía de estudio: Nicolás

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Según `docs/defensa/plan_estudio.md`, sección 2, Nicolás es dueño de **los procesadores y la verificación**: Espino base, segmentado, barrel, extensión de la ISA, y la verificación formal, por mutaciones, con el gemelo y las puertas. En la presentación de 5 minutos dice el segundo bloque (`docs/defensa/guiones.md`).

## 1. Qué leer, en orden

1. `docs/defensa/espino_base.md` y `docs/defensa/diagramas.md`, secciones 1 y 2: por qué CPI 2 (la espera del banco en BRAM).
2. `docs/defensa/segmentado.md` y diagramas, sección 3: IF con la BRAM en el flanco de bajada, escritura adelantada.
3. `docs/defensa/barrel.md` y diagramas, sección 4: por qué no hay riesgos y por qué es el core más pequeño.
4. `docs/defensa/extension.md`: `emad` y `devk`, la codificación, y por qué toda otra palabra de custom-0 no hace nada.
5. `docs/defensa/verificacion.md`, `docs/verificacion_exhaustiva.md` (nuevo) y `docs/puertas.md`.
6. `docs/revision_p10.md` cuando esté integrado: lo que encontró el revisor adversarial, en particular el hallazgo del esclavo SPI con el contador de bits en 7.
7. `docs/defensa/c1.md`, secciones 3, 5, 7 y 9: R3 vista como hardware y verificación. Qué cambia respecto de R2 (tabla de 512 palabras, `rtl/pochoco_tabla512.v`), por qué el core no se verificó de nuevo salvo la campaña sobre el SoC de R3, y qué prueban las puertas de `docs/puertas.md`, sección "R3".

## 2. Lo que tiene que poder dibujar sin mirar

- Las dos fases del Espino base (diagramas, sección 2) y la tabla de ciclos por tipo de instrucción.
- La tabla de cuatro hilos por cuatro etapas del barrel (diagramas, sección 4).
- La campaña de verificación: qué se compara en cada instrucción completada (contador de programa, instrucción, escritura al banco, bus, los 16 registros del contexto, palabra de memoria).

## 3. Cifras de memoria

| Cifra | Valor | Fuente |
|-------|-------|--------|
| CPI | Base 2 (ALU), 3 (load, salto tomado); segmentado 1,350 con `trade.s`; barrel 4 por hilo y 1 agregado | `docs/defensa/cifras.md` |
| Celdas | R0 1091; segmentado 990; barrel solo 932; R1 1029; R2 1045 | `docs/puertas.md`, `docs/mediciones/p7/variantes.txt` |
| Frecuencia mínima en 10 semillas | R0 41,93; R1 51,59; R2 47,86 MHz | `docs/mediciones/p7/variantes.txt` (R0 da 42,43 en la medición de la puerta, `docs/puertas.md`) |
| Respuesta de `trade.s` | 41 ciclos promedio, 44 peor; segmentado 22 y 26 | `docs/defensa/cifras.md` |
| Verificación del barrel con la máscara de R1 | 50,8 millones de instrucciones, cero diferencias (17/11); 7,97 millones en la puerta | `docs/mediciones/noche/barrel_r1_50m.txt` |
| Exhaustivo de R0 | 16 254 estados alcanzables por 255 precios = 4 144 770 combinaciones | `docs/verificacion_exhaustiva.md` |
| Mutaciones | 21 de 21 del barrel; 6 de 6 de la extensión que aplican | `docs/puertas.md`, criterio 5 |

## 4. Preguntas del banco que responde en profundidad

- **Avanzadas [A]**: 56, 58, 59, 60, 61, 63, 64, 65, 66, 67, 73, 74, 75, 77, 78, 79, 80, 81, 83, 87, 89, 90, 91, 93, 94, 95, 128, 129, 131, 134 y 136; de R3 (sección 14 del banco): 176 (por qué cuatro hilos y no uno) y 179 (cómo se verificó el programa).
- **Incómodas [I] de su pieza**: 55, 68, 76, 88, 92, 132 y 137. Se responden tal como están escritas, sin esconder lo que se aceptó. De R3: 177 (memoria al 94 % y plazo en 81 % del límite).
- **Básicas [B]**: las 57 del banco (las 4 de R3 son la 157, 158, 160 y 170), igual que los otros dos.

## 5. Lo que tiene que saber de las piezas de los otros

- De Vicente: por qué reversión y no tendencia (pregunta 12), qué es `max_media` y por qué no se informa el 25 973 como lo esperado, y la pregunta 156 sobre `zscore`.
- De Santiago: el recorrido de un tick por los cuatro hilos (diagramas, sección 5), cómo se detecta un voto viejo, y qué pasa en el relevo de R2.

## 6. Plan

| Fecha | Qué |
|-------|-----|
| Hasta el 18/11 | Puntos 1 a 4 de la sección 1 y la sección 3 de memoria |
| 21/11 | Prueba de práctica 1 (`docs/defensa/pruebas_practica.md`), respondida por Santiago con Nicolás preguntando |
| 24/11 | Repaso de todas las [I] del banco con los tres |
| 26/11 | Maestra real con Santiago: anotar todo lo que se vea en la plantilla del checklist |
| 30/11 | Guion de 5 minutos con cronómetro y prueba de práctica 3 |
