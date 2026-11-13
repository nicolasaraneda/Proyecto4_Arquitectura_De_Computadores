# Estado del proyecto

Se actualiza al cerrar cada tramo de trabajo. La versión anterior queda en el historial de git.

## Tramo 1: repositorio, flujo completo y mediciones de partida (12/11 y 13/11)

### Qué quedó hecho

- Repositorio privado `nicolasaraneda/Proyecto4_Arquitectura_De_Computadores`, con el repositorio base del curso importado sin cambios (etiqueta `base-curso`) y la estructura `rtl/`, `sw/`, `tb/`, `ref/`, `tools/`, `formal/`, `docs/`, `informe/`.
- Los cuatro archivos entregados quedaron en su lugar: `docs/Proyecto_4_arq.pdf`, `tb/tb_proyecto_4.sv`, `tb/practica.csv` y `ref/p4_baseline.py`. Ninguno se modificó.
- Ensamblador `tools/pochoasm.py`: es el del Proyecto 2 con el nombre que pide el testbench. 73 tests pasan.
- `sw/trade.s` trivial (comprar y mantener) y `Makefile` con todo el flujo: ensamblar, testbench oficial, copias parametrizadas del testbench, CPI, síntesis, place and route y bitstream.
- Power-on reset largo traído del Proyecto 2 (`PorBits = 12`).
- Scripts de medición: `tools/medir_base.sh` y `ref/hallazgos.py`.
- Integración continua en GitHub Actions: tests del ensamblador, `trade.hex` al día, testbench oficial, CPI y síntesis hasta el bitstream. La primera corrida en GitHub terminó en verde.
- `main` protegido en GitHub: exige que el chequeo `verificar` de la integración continua haya pasado, y no admite `push --force` ni borrar la rama. El dueño del repositorio puede empujar directo. Los demás integrantes entran por pull request desde una rama.
- `Vcalderone` invitado como colaborador con permiso de escritura.
- `README.md`, `docs/decisiones.md` y `docs/ensamblador.md`.

### Qué se midió

Testbench oficial sin modificar, con el `trade.s` trivial:

| Período | Ticks | Resultado | Peor caso | Presupuesto |
|---------|-------|-----------|-----------|-------------|
| 0,1 ms (por defecto) | 2000 | 4/4 | 18 ciclos | 2 262 |
| 1 ms (copia parametrizada) | 20 | 4/4 | 18 ciclos | 24 762 |
| 10 ms (copia parametrizada) | 5 | 4/4 | 18 ciclos | 249 762 |

Con 2000 ticks a 0,1 ms el patrimonio final es 6 845 con 2 órdenes (comprar y mantener según el testbench: 6 695). El `decisiones.csv` se comparó fila por fila con el mercado de `ref/p4_baseline.py`: cero diferencias en 2000 filas (hecho con el reset original; con el reset largo cambia solo el tick en que aparece la primera orden).

Repositorio base (`make medir-base`, resultado en `docs/mediciones/base.txt`):

| Medición | Valor medido | Valor que teníamos anotado |
|----------|--------------|----------------------------|
| Celdas lógicas | 1065 de 1280 (83 %) | 1080 (84 %) |
| BRAM | 12 de 16 | 12 de 16 |
| Frecuencia máxima, 10 semillas | 42,7 a 47,1 MHz, mediana 44,1 | cerca de 43 MHz |
| Shifter completo | 1491 celdas (116 %), no cabe | 1479 (115 %) |
| PLL en el VQ100 | nextpnr falla: "PLL 'u_pll' couldn't be placed anywhere, no suitable BEL found" | el mismo error |
| CPI | 2 ciclos por instrucción, más 1 por load y 1 por salto tomado. Medido en simulación con tres programas: el modelo coincide con diferencia de 0 ciclos | el mismo modelo, por lectura del RTL |

Diseño actual (repositorio base más reset largo): 1083 celdas, 12 BRAM, 44,0 MHz con la semilla por defecto.

Serie de práctica (`make hallazgos`):

| Hallazgo | Valor medido | Coincide |
|----------|--------------|----------|
| VR(10), VR(50), VR(100) | 0,77, 0,62 y 0,53 | sí |
| Reversión en los 20 bloques de 1000 ticks | VR menor que 1 en 20 de 20, para los tres horizontes | sí |
| Autocorrelación de los cambios | -0,112 en el rezago 1, dentro del ruido desde el rezago 3 | sí |
| Regla base (media exponencial, alfa 1/32, entra 4, sale 0) | 27 062 con 388 órdenes. Bloques: media 11 069, peor 9 720, supera a comprar y mantener en 9 de 10 | sí |
| Suma móvil de 64, entra 4, sale 1 | 24 143. Bloques: media 10 951, peor 10 148 | sí |
| Comprar y mantener | 6 497. Media por bloque 9 746 | sí |
| Seguir tendencia, 336 configuraciones | mediana 5 566, solo 10 de 336 terminan sobre 10 000 | no: teníamos 3 853 |

### Diferencias con lo que teníamos anotado

1. **Versión de Yosys.** La instalada es 0.68+195 (OSS CAD Suite del 2026-09-06), no 0.70. Con ella el repositorio base da 1065 celdas en vez de 1080 y el shifter 1491 en vez de 1479. Las conclusiones no cambian: quedan unas 200 celdas libres y el shifter completo no cabe.
2. **El conteo de celdas tiene ruido.** El mismo diseño dio entre 1063 y 1075 celdas según detalles del flujo que no cambian la lógica. Una diferencia menor que unas 10 celdas no se puede atribuir a un cambio con una sola síntesis (decisión T6).
3. **Barrido de seguir tendencia.** La grilla de 336 configuraciones original no estaba en ningún script. Con la grilla que definimos en `ref/hallazgos.py` la mediana es 5 566 y no 3 853. La conclusión es la misma: seguir tendencia pierde.
4. **Intentos anteriores sin código.** Perceptrón en línea, población de 120 traders y comité por votación no se pudieron reproducir porque su código no está en el repositorio. Hay que rehacerlos en el frente del algoritmo.
5. **Costo de la regla base (unas 30 instrucciones, 70 ciclos).** Sin medir todavía, porque `trade.s` es el trivial.
6. **CPI del enunciado.** La tabla del enunciado supone CPI = 2,35. Los programas medidos dan entre 2,50 y 2,67, porque tienen muchos saltos tomados y loads.
7. **Reset largo y primeros precios.** Con el reset del Proyecto 2, en el testbench el programa no ve los precios de los ticks 0 y 1 a 0,1 ms, ni el del tick 0 a 1 ms y 10 ms (medido). El testbench entrega 4/4 de todas formas. En la competencia no pasa, porque la placa está encendida antes del primer precio (decisión T3).
8. **Puntaje de la competencia.** El enunciado dice que depende del patrimonio final respecto a comprar y mantener y de la posición relativa entre los grupos. Lo teníamos resumido solo como lineal entre el peor y el mejor grupo.

Nada de lo encontrado contradice al enunciado ni al testbench.

### Observaciones para lo que viene

- **La simulación con Icarus es lenta.** 2000 ticks a 0,1 ms demoran 76 segundos. Una ronda de 2000 ticks a 10 ms demoraría cerca de dos horas. Para las rondas 1 y 2 completas hace falta Verilator o el gemelo digital.
- **`trade.hex` no rellena las 512 palabras.** Las palabras que no están en el archivo quedan indefinidas en simulación y en cero en la placa. Un programa que lea memoria sin haberla escrito se comportaría distinto en los dos lados. Conviene que el ensamblador rellene hasta 512 palabras, que además es lo que necesita `icebram`.
- **Posible sobreajuste de la regla base.** En la grilla de 336 configuraciones de reversión, la mediana es 11 204 y el máximo 27 226. La regla base (27 062) está casi en el máximo de la grilla, así que sus parámetros ya están elegidos mirando la serie completa. El protocolo por bloques y con remuestreo tiene que partir de ahí.
- **`tb/tb_cpi.sv` mira señales internas del Espino base.** Cuando el core se segmente hay que actualizar esas rutas o sacar una señal de instrucción completada.

### Qué falta del tramo 1

- **Equivalencia y verificación formal en la integración continua.** Todavía no existen. Se agregan al flujo cuando estén `make equiv` y las pruebas de `formal/`.
- **Colaboradores.** Falta el usuario de GitHub de Santiago Muñoz y el de quien deba revisar la entrega.
- **Definición de Ops/s y roofline vista en clases.** No está en el repositorio. Hace falta la diapositiva para el frente del co-diseño.

### Qué conviene atacar después y por qué

1. **Regla base en `trade.s` con equivalencia exacta (`make equiv`).** Es el entregable del día 2 y la base de todo lo demás: fija la referencia `ref/trader.py`, obliga a resolver el desplazamiento sin shifter y entrega el primer bitstream de competencia.
2. **Gemelo digital o Verilator.** Sin simulación rápida no se pueden correr las rondas de 10 ms ni la matriz de estrés. Destraba los frentes A, D y E.
3. **Relleno de `trade.hex` a 512 palabras y prueba de `icebram`.** Es barato y elimina una diferencia entre simulación y placa.
4. **Preguntas al ayudante.** Sobre todo las que cambian el diseño: si el periférico estimador cumple las reglas, si las series ocultas salen del mismo generador, cuántos ticks dura cada ronda y si la maestra usa el timing del testbench.
