# Bitácora: material de estudio adicional (punto 7 del trabajo autónomo, 17/11)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Encargo: diagramas de la arquitectura de cada core y del recorrido de un tick por los 4 hilos; guion de 5 minutos y de 1 minuto; tres pruebas de práctica de 15 preguntas del banco con su pauta; una guía por integrante según el plan de estudio. Rama `integra-noche`.

- `docs/defensa/diagramas.md`: el SoC, el Espino base (dos fases), el segmentado (tres etapas en dos ciclos), el barrel (tabla de cuatro hilos por cuatro etapas y camino de datos), un tick por los cuatro hilos del fondo con los ciclos medidos, y el relevo de R2 con el tiempo medido en la placa. En texto, para copiarlos en la pizarra. Cada número tiene su fuente.
- `docs/defensa/guiones.md`: 1 minuto y 5 minutos (un bloque por integrante en el orden de la pauta, más el cierre). Las frases que cambian si cambia el peldaño o el algoritmo están marcadas con (*).
- `tools/defensa/pruebas.py` genera `docs/defensa/pruebas_practica.md`: tres pruebas de 15 preguntas sin repetir (7 [B], 5 [A] y 3 [I] cada una, repartidas por secciones), con la pauta copiada del banco. Semilla fija: si el banco cambia, se regeneran.
- `docs/defensa/guia_nicolas.md`, `guia_vicente.md` y `guia_santiago.md`: qué leer, qué dibujar, cifras de memoria, preguntas [A] e [I] de su pieza (listas sacadas del banco) y fechas.
- Banco: pregunta 156 ("¿Por qué no usaron la regla que da 40 957 en la práctica?"), pedida por Nicolás el 17/11. El README de la carpeta dice 156.
- Pendiente: repasar la 156 y los guiones marcados con (*) después de la decisión sobre `zscore`; agregar al banco lo del 26/11.
