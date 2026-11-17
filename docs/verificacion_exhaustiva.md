# Verificación exhaustiva de la regla de decisión

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio de `tools/exhaustivo/` (17/11). Responde a "verificación exhaustiva de punta a punta: todas las combinaciones de estado del algoritmo y precio de entrada, o la mayor cobertura alcanzable, con el conteo de casos reportado" (plan, frente D).

## 1. Qué se verifica

La regla de R0 (`sw/trade.s`, `max_media`) guarda dos cosas entre un precio y el siguiente: **S**, 32 veces la media exponencial (un entero de 32 a 8160), y **pos**, si quiere estar adentro (0 o 1). Con cada precio p de 1 a 255:

```
dev = 32 p - S
pos = (pos | dev < -96) & (dev < 1)
S   = S + p - ceil(S / 32)
decisión: comprar 63 si pos = 1, vender 63 si no
```

Todo lo que el programa puede hacer con un precio depende solo de (S, pos, p). Si cada combinación posible se le aplica al programa real y la decisión sale igual a la de la referencia, la regla queda verificada entera, no por muestreo.

Las pruebas que ya existían (`ref/test_ref.py`) recorren todas las combinaciones, pero sobre el modelo en Python. Lo nuevo es aplicarlas al **programa ensamblado corriendo en el procesador**: en el gemelo y en el RTL.

## 2. Cuántas combinaciones hay

No todos los pares (S, pos) se pueden dar. Una búsqueda por anchura desde los 255 primeros precios posibles (S = 32 p0, pos = 0) da:

| | Cantidad |
|-|----------|
| Estados alcanzables con pos = 0 | 8 129 (todos los S de 32 a 8160) |
| Estados alcanzables con pos = 1 | 8 125 |
| **Combinaciones (estado, precio)** | **16 254 x 255 = 4 144 770** |

Los cuatro estados que faltan con pos = 1 son los de S de 8157 a 8160: para estar adentro hay que haber entrado, con un precio más de 3 unidades bajo la media, y ese paso deja S en 8156 o menos (desde S = 8160, el precio más alto que todavía entra es 251).

## 3. Cómo se llega a cada combinación sin tocar el procesador

No se fuerza ningún registro: el programa recibe precios por el SPI, como en la competencia. El problema es llevarlo a cada estado. `tools/exhaustivo/r0_cubrir.c` arma series de precios que lo hacen:

1. Divide los estados en 24 franjas de S con la misma cantidad de combinaciones, una serie por franja.
2. En el estado actual, si quedan precios por probar, aplica uno (de preferencia uno que lleve a otro estado con pendientes).
3. Si no, busca el estado pendiente más cercano y lo alcanza con un controlador directo. La regla de llegada sale de la aritmética: **para llegar con pos = 0 hay que subir hacia S** (un paso con el precio sobre la media sale); **para llegar con pos = 1 hay que bajar 4 unidades de S o más** desde arriba (entra) o bajar conservando pos = 1 (cada paso con el precio bajo la media).
4. Cada serie empieza con 24 precios iguales: el programa pierde los que llegan durante el reset y su primer precio queda bien definido.

**La esquina.** Los estados con S de 8129 a 8160 (media sobre 254) solo se alcanzan si el primer precio es 255: desde abajo la media nunca vuelve a subir tanto, porque con S = 8128 el mayor paso posible es +1. Esas combinaciones van en 15 810 series cortas aparte, cada una desde el reset con el primer precio que la alcanza.

Resultado: 24 series largas con 19 116 872 precios y 15 810 cortas con 417 690. Cada combinación se aplica en promedio 4,7 veces.

**El conteo no se confía al generador.** `tools/exhaustivo/r0.py` lo rehace con `ref/trader.py`: corre la referencia sobre todas las series, con los precios que el programa pierde en el reset, y marca cada (S, pos, p) que pasa. Recalcula además el conjunto alcanzable por su cuenta.

## 4. Resultados

`docs/mediciones/noche/exhaustivo_r0.txt` y `exhaustivo_r1.txt`.

| Prueba | Resultado |
|--------|-----------|
| Cobertura, contada con la referencia | 4 144 770 de 4 144 770 combinaciones; ninguna fuera del conjunto alcanzable |
| Gemelo (Espino base con `sw/trade.hex`), 12 us por precio | Las 24 series y las 15 810 cortas: todos los bytes de decisión iguales a `ref/trader.py` |
| RTL con Verilator, copia del testbench oficial a 12 us | Las 24 series largas (19 116 872 ticks): 4/4 en cada una, peor caso 44 ciclos de 62, todos los bytes de decisión iguales a `ref/trader.py` |
| RTL, esquina (300 de las 15 810 series cortas, al azar con semilla 17) | 300 de 300 con 4/4 e idénticas |

**Qué cubre el RTL y qué no.** Las 24 series largas recorren todas las combinaciones salvo la esquina S ≥ 8129, a la que solo se llega con 255 como primer precio. Esa esquina está entera en el gemelo (15 810 series) y en una muestra de 300 por el RTL; el gemelo está validado ciclo a ciclo contra el RTL (`make cosim`). Correr las 15 810 por el RTL cuesta una compilación de Verilator por serie y no agrega una combinación nueva.

**Dos errores de las herramientas, no del diseño, encontrados al correr el RTL.** (1) El testbench oficial guarda la serie en `int precio [20000]`: con series más largas Verilator pliega los índices y la simulación manda otros precios. La copia que usa `r0.py` cambia también ese arreglo (`int precio [NTICKS]`) y comprueba que no cambia ninguna otra línea. (2) El gemelo, en modo lote, lee cada serie con un búfer de 4 MB por línea y corta las series largas; `r1.py` las corre con `--serie`. Los dos se corrigieron antes de tomar los resultados de esta tabla. Además, la primera versión de la cobertura juntaba los mapas de bits de todas las series en memoria (8 GB en R0, más de 30 GB en R1); ahora se acumulan a medida que llegan.

**Un detalle de la comparación.** En dos de las series (las de precios bajos) el testbench y el gemelo desbordan el patrimonio: lo llevan en enteros de 32 bits, como el testbench oficial, y una serie que compra a 1 y vende a 253 millones de veces llega a más de 2 147 483 647. La referencia en Python no tiene ese límite. Por eso se comparan los bytes de decisión, que es lo que se verifica, y no las columnas de contabilidad. En la competencia no puede pasar: con 63 acciones por orden y 20 000 ticks el patrimonio no sale de unos pocos millones.

**Por qué 12 us.** Es el período más corto con que R0 todavía responde a tiempo con SCLK de 1 MHz (11,34 us, `docs/mediciones/fondo/r1/sclk_minimo.txt`), y deja 62 ciclos de presupuesto contra los 44 a 49 que usa. Así el RTL recorre las 19 millones de decisiones en minutos en vez de horas, y el período no cambia nada de la regla.

## 5. R1

El fondo guarda mucho más estado (cuatro posiciones, tres pesos, tres puntajes y la ventana), y recorrerlo entero no es posible. Lo que sí se cubre:

- **El supervisor corre la misma regla que R0, con la misma S.** Las mismas series aplican cada precio en cada uno de sus estados.
- **Los gestores comparten S y tienen sus propios umbrales.** Se cuenta qué parte de sus combinaciones alcanzables recorren las mismas series.
- **La votación.** Se cuentan las combinaciones de votos y pesos que llegan a la decisión.

`tools/exhaustivo/r1.py` corre todas las series en el gemelo con el hardware de R1 (a 30 us, porque R1 necesita al menos 26,94 us) y las cuatro series largas más cortas por el RTL. Los números están en `docs/mediciones/noche/exhaustivo_r1.txt`.

| Prueba | Resultado |
|--------|-----------|
| Cobertura del supervisor (`max_media`, entra -96, sale 1) | 4 144 770 de 4 144 770 (100 %) |
| Cobertura del gestor 1 (los mismos umbrales) | 4 144 770 de 4 144 770 (100 %) |
| Cobertura del gestor 2 (entra -128, sale 1) | 3 574 305 de 4 144 515 (86,24 %) |
| Cobertura del gestor 3 (entra -64, sale 17) | 4 132 787 de 4 145 025 (99,70 %) |
| Votación | 168 combinaciones de votos por pesos (4 de los 8 juegos de votos, 42 juegos de pesos) |
| Gemelo con el hardware de R1, 30 us | Las 24 largas (19 116 872 ticks) y las 15 810 cortas: todos los bytes iguales a `ref/fondo.py` |
| RTL con Verilator, las 4 series largas más cortas | 963 350 ticks, 4/4 en cada una, peor caso 441 ciclos de 512, bytes iguales a `ref/fondo.py` |

**Por qué el gestor 2 queda en 86 %.** Las series se construyeron para recorrer los estados de la regla de R0. Con entrada a -128 el gestor 2 necesita caídas más profundas para entrar, y las series no se armaron para buscarlas. No es un hueco de la verificación de R0, que es la que compite como respaldo; para R1 es una cobertura alta pero no completa, y así se informa.

**La votación no es exhaustiva.** Los tres gestores comparten la media, así que sus votos están correlacionados: con estas series aparecen 4 de los 8 juegos de votos posibles. La votación con cualquier combinación de votos y pesos se prueba aparte en `make check-fondo` (controles y degradación).

## 6. Cómo se reproduce

```bash
cc -O2 -o build/exhaustivo/r0_cubrir tools/exhaustivo/r0_cubrir.c
build/exhaustivo/r0_cubrir 24 build/exhaustivo/series           # las series (unos 2 minutos)
python3 tools/exhaustivo/r0.py --rtl --rtl-esquina 300 --jobs 6  # cobertura, gemelo y RTL
python3 tools/exhaustivo/r1.py --rtl 4 --jobs 6                  # R1
```

## 7. Preguntas que nos pueden hacer

**¿Exhaustivo de verdad, o una muestra grande?** Exhaustivo para R0: cada uno de los 4 144 770 pares (estado, precio) que pueden ocurrir se le aplicó al programa real, y el conteo lo hizo la referencia, no el generador.

**¿Por qué no forzar los registros del procesador?** Porque así se prueba también el camino real: el SPI, el sondeo y la escritura en `DECISION`. Forzar registros prueba una parte del programa con un estado que el programa quizás nunca alcanza.

**¿Y la contabilidad?** No es parte de la regla: la hace la maestra. Se verificó aparte (`ref/test_ref.py`, el arnés de retorno contra la tarea `ejecutar` del testbench).
