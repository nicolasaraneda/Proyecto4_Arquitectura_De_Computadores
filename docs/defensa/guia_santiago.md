# Guía de estudio: Santiago

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Según `docs/defensa/plan_estudio.md`, sección 2, Santiago es dueño de **`sw/fondo.s` entero, la tabla y `icebram`, el vigilante y el relevo, y la operación del 26/11 y del 1/12** (medidor, registrador, árbol, checklists, `retune`). Acompaña a Nicolás el 26/11. En la presentación de 5 minutos dice el tercer bloque (`docs/defensa/guiones.md`).

## 1. Qué leer, en orden

1. `docs/defensa/fondo.md` y `docs/defensa/diagramas.md`, sección 5: el recorrido de un tick por los cuatro hilos.
2. `docs/fondo.md`, secciones 3 (protocolo de memoria compartida y voto viejo), 9 (peor caso por fase) y 10 (degradación).
3. `docs/defensa/tabla_vigilante.md` y diagramas, sección 6: el relevo, con el tiempo medido en la placa (35,50 ms, 361 ticks a 0,1 ms).
4. `docs/arbol_decision.md`, `docs/checklist_26nov.md` (con el registrador, sección 4b) y `docs/checklist_1dic.md`.
5. `docs/registrador.md` (nuevo) y `docs/contingencia.md`.
6. `docs/mediciones/placa_16nov.md`: qué pasó la placa y qué falta.
7. `docs/defensa/c1.md`, secciones 3, 4, 7 y 9, y `docs/c1_dia_de_prueba.md` entero: los cuatro hilos de `sw/c1.s`, la degradación, la rutina por ronda con reset por USB, la telemetría y su límite, y la autoprueba de R3 (sección 9 del día de prueba).

## 2. Lo que tiene que poder dibujar sin mirar

- El tick por los cuatro hilos (diagramas, sección 5), con `PUB`, `DES_k` y `EST_k`, y la resta que detecta un voto viejo.
- La escalera R0, R1 y R2 y el árbol del 1/12, regla por regla.
- El relevo de R2: cinco precios sin escritura, BOOT con `CS_n` en alto, 35,5 ms con MISO en 1 (la maestra lee `0xFF`, mantener), R0 desde cero.

## 3. Cifras de memoria

| Cifra | Valor | Fuente |
|-------|-------|--------|
| Respuesta del fondo | 223,01 ciclos promedio; 444 peor; 568 con el plazo agotado; 679 con un gestor atrasado; límite 1131 | `docs/fondo.md`, sección 1 |
| Votos | Pesos iniciales 6, 5 y 5 dieciseisavos; umbral 8; ventana de 512 ticks; plazo 8 vueltas de 48 ciclos | `ref/fondo.py`, `docs/fondo.md` |
| Vigilante | Dispara al quinto precio sin escritura; nunca pasó de 1 en una corrida sana | `docs/tabla_vigilante.md` |
| Relevo | 35,50 ms medidos; 361, 40 y 8 ticks sin decisión nueva | `docs/mediciones/placa_16nov.md` |
| SCLK | R1 responde desde 110 kHz; el árbol usa 115 | `docs/arbol_decision.md` |
| Placa (16/11) | R2: firma a 0,1 ms y media hora sin disparo; faltan R1 y R2 a 1 y 10 ms | `docs/puertas.md`, puerta de placa |

## 4. Preguntas del banco que responde en profundidad

- **Avanzadas [A]**: 8, 99, 100, 101, 102, 105, 106, 107, 109, 110, 111, 112, 113, 114, 117, 118, 120, 121, 123, 124, 148, 149, 150, 151, 153 y 155; de R3 (sección 14 del banco): 161 (datos entre hilos), 162 (máquina de modos), 171 (hilo colgado), 172 (hilo 0 colgado y relevo), 178 (rondas seguidas), 180 (autoprueba) y 181 (telemetría y su límite).
- **Incómodas [I] de su pieza**: 3, 4, 9, 103, 104, 122, 125, 147 y 154. De R3: 164 (comisión o caja distintas) y 182 (hardware sin maestra, quién decide).
- **Básicas [B]**: las 57 del banco (las 4 de R3 son la 157, 158, 160 y 170).

## 5. Lo que tiene que saber de las piezas de los otros

- De Nicolás: por qué el barrel no tiene riesgos y qué es una campaña de verificación (diagramas, sección 4; `docs/defensa/verificacion.md`).
- De Vicente: el protocolo con semilla reservada y la pregunta 156.

## 6. Plan

| Fecha | Qué |
|-------|-----|
| Hasta el 18/11 | Puntos 1 a 3 de la sección 1 |
| 21/11 | Prueba de práctica 1, respondida por Santiago |
| 24/11 | Repaso de todas las [I]; ensayar el checklist del 26/11 paso por paso con la placa |
| 26/11 | Maestra real: medidor, peldaños, registrador, relevo; anotar en la plantilla |
| 27/11 | Agregar al banco lo que salga del 26/11 |
| 30/11 | Guion de 5 minutos con cronómetro y prueba de práctica 2 |
