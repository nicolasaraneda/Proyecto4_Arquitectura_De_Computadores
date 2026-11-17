# Bitácora: evaluación de la regla `zscore` (17/11)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Encargo de Nicolás del 16/11 en la noche, con prioridad sobre el resto de la lista. Rama `zscore`. Decisión de método: T128. Nada de esto toca R0, R1 ni R2.

## 1. Implementación y equivalencia

- `ref/zscore.py`: la regla con la interfaz del protocolo, parámetros km, kd, num/den, w y sx2. Con los valores de Vicente da **40 957 con 578 órdenes** en la serie de práctica completa, la cifra pedida.
- Clon del repositorio de Vicente fuera de esta carpeta (`../Vicente_Proyecto4`, commit `3173a3d`): `tools/referencia.py`, función `agente_zscore`. Su regla y la nuestra dan los mismos bytes de `DECISION` en la práctica y en 80 series sintéticas.
- `ref/zscore/zscore.c` y `ref/zscore/fondo_z.c` (copia del fondo de la factibilidad con gestores por nombre), compilados contra el arnés de `factibilidad/retorno` en `build/zscore/arnes` (`make -C ref/zscore`).
- `ref/zscore/validar.py`: C contra Python en 2 955 series con cinco juegos de parámetros, y `fondoz_min` contra el `fondo_min` original en 7 511 series. Todo igual. La causalidad del arnés pasa para las dos estrategias nuevas.

## 2. Exploración con la semilla 0

- Protocolo (`ref/protocolo.py --estrategia oficial --comparar zscore`): no reemplaza. Gana en los 10 bloques (+346 +- 321, ruido), pierde en los remuestreos (-110 +- 37) y en las cuatro familias plausibles.
- Meseta a 2000 ticks (81 puntos: z de 1 a 3, km 4 a 6, kd 5 a 7): ningún punto le gana a `max_media` en puntos. El mejor es km 5, kd 7, z 1,5: -0,058 +- 0,005 en H3a. La regla de Vicente: -0,095.
- Meseta a 20 000 ticks: interiores, mejor punto -0,047 en H3a y +0,014 +- 0,004 en H3b; la vista de parada no confirma el signo (-0,089 y -0,023). La regla de Vicente pierde -0,21 en H3a.
- Fondos de tres gestores zscore (2,0/2,25/2,5 y 1,25/1,5/1,75, mayoría y pesos aprendidos) y uno mixto con `max_media`: entre -0,046 y -0,071 en H3a a 2000 ticks. No superan al mejor zscore solo por más que el ruido.
- En la serie de práctica completa la regla de Vicente es el máximo de las 81 combinaciones y su vecino z = 2,75 da 22 421: una cima aislada en la serie de elección.

## 3. Finalistas para la semilla reservada (fijados antes de correrla)

1. `zscore` tal como lo entregó Vicente: km 5, kd 6, z 2,5.
2. El centro de la meseta a 2000 ticks: km 5, kd 7, z 1,5 (`zscore:km=5,kd=7,num=6,den=4`).
3. El mejor fondo: `max_media`, zscore 2,0 y zscore 1,5 con mayoría de dos de tres.
4. El fondo del ejemplo de Nicolás: tres gestores zscore de 2,0, 2,25 y 2,5 con los pesos aprendidos de R1.

Se corren una vez con la semilla 4, a 2000 y 20 000 ticks: protocolo, criterio de corte del arnés con la vista de parada, duelo cabeza a cabeza y tabla de puntos.

## 4. Semilla reservada (corrida una vez, 17/11)

`ref/zscore/reservada.sh`, salida en `docs/mediciones/zscore/reservada_s4.txt`, `tabla_n*_s4*.txt` y `duelo_n*_s4.txt`.

- Los cuatro finalistas: **NO PASA** el criterio de corte a 2000 y a 20 000 ticks. El protocolo tampoco los acepta (finalistas 1 y 2).
- `zscore` de Vicente: -0,094 (2000) y -0,222 (20 000, interiores) en H3a; -0,167 con la vista de parada.
- Centro de la meseta: -0,055 y -0,060 en H3a; en H3b -0,024 y +0,007 (igual).
- Fondo mixto: -0,040 y -0,052. Fondo `zscore` 2,0/2,25/2,5 aprendido: -0,072 y -0,134.
- Hallazgo que no estaba previsto: en las plausibles a 20 000 ticks el centro de la meseta gana en H3b (+0,050 interiores, +0,044 parada) y el 65 % de las rondas. En los remuestreos del mismo largo pierde. No cambia el veredicto (criterio fijado sobre la evidencia completa) y queda como decisión de Nicolás.
- Cierre: T129, `docs/zscore.md`.
