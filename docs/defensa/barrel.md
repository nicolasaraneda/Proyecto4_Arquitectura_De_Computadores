# Espino barrel: cuatro hilos por un pipeline de cuatro etapas

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio para la defensa. Resume y ordena `docs/espino_barrel.md`, que es la fuente completa. El barrel es el core de R1 y R2, los peldaños del diseño que compite (decisión T50). Cifras de `docs/mediciones/barrel/`, `docs/mediciones/p7/variantes.txt` y `docs/puertas.md`.

## 1. El problema: otra forma de bajar el CPI

El segmentado baja el CPI con adelantamiento, una espera en los loads y anulando la instrucción que sigue a un salto tomado (`docs/defensa/segmentado.md`). Todo eso existe porque dos instrucciones seguidas **del mismo programa** están juntas en el pipeline.

El barrel evita el problema en vez de resolverlo: tiene **cuatro hilos**, cada uno con su contador de programa y sus 16 registros, y en cada ciclo entra al pipeline una instrucción de un hilo distinto, por turnos (0, 1, 2, 3, 0, ...). Dos instrucciones seguidas del mismo hilo nunca están juntas en el pipeline: cuando la i+1 empieza, la i ya terminó. No hay riesgos de datos ni de control.

En términos de la ley de hierro:

| Factor | Qué pasa |
|--------|----------|
| IC | No cambia: es la misma ISA |
| CPI agregado (todo el core) | 1,000 exacto, para cualquier mezcla de instrucciones |
| CPI por hilo | 4,000 exacto: cada hilo avanza una instrucción cada 4 ciclos |
| Tclk | 40 ns en la placa. La frecuencia máxima sube porque no hay multiplexores de adelantamiento |

Ppeak con la definición de la clase: 25 MHz × 0,25 × 1 × 4 hilos = 25 MOPS, el mismo techo del segmentado, pero el barrel lo alcanza con cualquier mezcla (`docs/espino_barrel.md`, sección 2).

## 2. Las cuatro etapas y el diagrama

| Etapa | Qué hace |
|-------|----------|
| F | El contador de programa del hilo direcciona la memoria de instrucciones |
| R | Sale la instrucción de la BRAM, se decodifica y sus `rs1` y `rs2` direccionan el banco con `{hilo, registro}` |
| X | ALU, comparación del salto, próximo contador de programa y petición al bus |
| M | Llega el dato del load, se alinea y se escribe el registro en `{hilo, rd}` |

```
ciclo      1   2   3   4   5   6   7   8
hilo 0     F   R   X   M   F   R   X   M
hilo 1     M   F   R   X   M   F   R   X
hilo 2     X   M   F   R   X   M   F   R
hilo 3     R   X   M   F   R   X   M   F
```

Por columnas: en cada ciclo hay un hilo en cada etapa. Por filas: cada hilo completa una instrucción cada 4 ciclos, sea ALU, load, store o salto.

**Por qué es el core más chico.** Las tres memorias del SoC (instrucciones, datos y banco) son BRAM con lectura registrada. En el base esa lectura cuesta un ciclo de espera; en el segmentado obligó a leer en el flanco de bajada. En el barrel cada BRAM cae justo en una frontera entre etapas, y su registro de salida **es** el registro de pipeline. Todo usa el flanco de subida.

## 3. Por qué no hay riesgos

Para un mismo hilo, la instrucción i ocupa los ciclos 1 a 4 y la i+1 los ciclos 5 a 8.

| Riesgo de un pipeline normal | En el barrel |
|------------------------------|--------------|
| Leer un registro que la anterior no escribió | i escribe al cerrar el ciclo 4; i+1 lee al cerrar el ciclo 6 |
| Load seguido de uso | El dato del load se escribe en ese mismo flanco del ciclo 4 |
| Salto que todavía no se resuelve | El próximo contador se calcula en el ciclo 3 y se usa en el 5: nunca se busca una instrucción especulativa |
| Efectos en el SPI de una instrucción anulada | No hay instrucciones especulativas: un `lw PRICE` o `sw DECISION` que llega a X siempre es de verdad |
| Leer y escribir el banco en el mismo flanco | El hilo que lee (R) y el que escribe (M) difieren en 2: las direcciones `{hilo, registro}` no pueden coincidir |

## 4. Dónde se ve en el RTL

| Qué | Dónde |
|-----|-------|
| Un contador de 2 bits dice qué hilo está en F; las otras etapas son ese valor menos 1, 2 y 3 | `rtl/espino_core/espino_barrel_core.v:107` a `:110` |
| Anillo de cuatro contadores de programa, uno por etapa | `rtl/espino_core/espino_barrel_core.v:120` |
| Lectura del banco con `{tid_r, rs1}` y `{tid_r, rs2}` | `rtl/espino_core/espino_barrel_core.v:216` y `:218` |
| Escritura del banco con `{tid_m, rd}` | `rtl/espino_core/espino_barrel_core.v:225` |
| x0 nunca se escribe: `rf_we_m` exige destino distinto de 0 | `rtl/espino_core/espino_barrel_core.v:446` |
| Avance del pipeline y valores de reset del anillo (arranque de los hilos) | `rtl/espino_core/espino_barrel_core.v:400` a `:429` |
| Los cuatro contextos en las mismas BRAM del banco, dirección de 6 bits | `rtl/espino_core/espino_barrel_regfile.v:55` a `:59` |
| El SoC instancia el barrel con `-DESPINO_BARREL` | `rtl/pochoco_soc.v:135` a `:140` |

Del Espino se reutilizan sin modificar el decodificador, la ALU y la unidad de carga (dos instancias: una arma la petición en X y otra alinea el dato en M). El banco de 16 registros ya estaba en BRAM de 256 palabras; el barrel usa 64 de ellas para los cuatro contextos y **no cuesta ninguna BRAM adicional**.

**El arranque.** El hilo t parte en la dirección 4 t, así que todo programa para el barrel empieza con una tabla de cuatro saltos (`sw/fondo.s:157` a `:160`). En hardware no cuesta nada: son los valores de reset del anillo. Un programa sin la tabla falla en silencio: con `sw/trade.hex` tal cual el testbench oficial da 2/4 (`make barrel-sin-tabla`).

## 5. Memoria compartida

Los registros no se comparten; la memoria y los periféricos sí.

- Hay un solo bus y una sola instrucción en X por ciclo: cada load y cada store es atómico, y los accesos de los cuatro hilos quedan en un orden fijo.
- No hay instrucciones atómicas de lectura y escritura. La regla de uso es **una palabra, un escritor**.
- El hardware es determinista: el orden entre hilos está fijo ciclo a ciclo. Lo que puede tener carreras es el software, si dos hilos escriben la misma palabra.

Es la base del protocolo del fondo (`docs/defensa/fondo.md`).

## 6. Qué cuesta: la latencia por hilo

| Core, `sw/trade.s` | Respuesta prom. | Peor (testbench) | Peor barriendo la fase |
|--------------------|-----------------|------------------|-------------------------|
| Base | 41,0 | 44 | 49 |
| Segmentado | 22,0 | 26 | 27 |
| Barrel, hilo 0 | 75,1 | 83 | 88 |

Fuente: `docs/mediciones/barrel/ticks.txt`, resumido en `docs/espino_barrel.md`, sección 4. El barrel responde 1,8 veces más lento que el base con el mismo programa. **El tiempo de un hilo no depende de lo que hagan los demás**: esa es la propiedad que usa el fondo, con un hilo atendiendo a la maestra mientras los otros calculan.

Con el fondo completo (R1) la respuesta es 223,01 ciclos en promedio y 443 en el peor caso del testbench, el 19,6 % del presupuesto de la ronda 3 (`docs/mediciones/p7/variantes.txt`).

**Por qué la latencia no cambia el patrimonio.** El byte que la maestra lee en el tick n se ejecuta al precio n, sea que el programa respondió en 22 ciclos o en 443. Mientras la respuesta llegue antes de la transacción siguiente, la misma estrategia da los mismos bytes en cualquier core: R0, el segmentado, el barrel y el barrel con la extensión dan con `max_media` los mismos 20 000 bytes que `ref/trader.py` (`docs/codiseno.md`, sección 11).

## 7. Recursos

| | Celdas | BRAM | Fmax mín. | Fuente |
|-|--------|------|-----------|--------|
| Barrel, un hilo con `sw/trade.s` (P1) | 933 | 12 | 52,62 | `docs/puertas.md` |
| Barrel, un hilo (P7) | 932 | 12 | 53,45 | `docs/mediciones/p7/variantes.txt` |
| R1: barrel con `emad`, `devk` y tabla | 1029 | 13 | 51,59 | `docs/puertas.md` |
| R2: R1 con vigilante | 1045 | 13 | 47,86 | `docs/puertas.md` |

Ruta crítica: salida de la BRAM del banco, multiplexor de operandos, sumador de la ALU, decodificación de la dirección y habilitación del registro de lectura de periféricos. 19,0 ns de 40 en la peor semilla (`docs/mediciones/barrel/ruta_critica.txt`).

## 8. Verificación

| Prueba | Resultado | Comando |
|--------|-----------|---------|
| Cada hilo contra un Espino base, instrucción por instrucción: contador de programa, instrucción, escritura al banco, acceso al bus, los 16 registros y la memoria | 7 948 558 instrucciones en 20 600 programas lineales, 91,96 % distintas en toda la campaña, cero diferencias; más 8 966 903 en la campaña de lazos | `make barrel-verif` |
| Controles negativos | 21 de 21 mutaciones detectadas, cada una por las 7 comparaciones | `make barrel-mutaciones` |
| Propiedades formales de estructura (SymbiYosys): aislamiento de contextos, x0, burbujas, rotación, contador de cada hilo, arranque | 24 afirmaciones probadas, 9 de 9 mutaciones con contraejemplo | `make barrel-formal` |
| Aislamiento y memoria compartida con cuatro hilos | Cada hilo igual a su corrida solo; cuatro hilos sobre la misma memoria iguales a un modelo por turnos | `make barrel-aislamiento`, `make barrel-compartida` |
| Testbench oficial | 4/4, 83 ciclos de 2262 | `make barrel-oficial` |

Fuentes: `docs/mediciones/barrel/verificacion.txt`, `mutaciones.txt` y `formal.txt`. Para la configuración exacta de R1 y R2 (con `emad`, `devk`, tabla y vigilante) la campaña se repitió: 7 974 963 instrucciones, 92,80 % distintas, cero diferencias (`docs/puertas.md`, criterio 5).

Qué falta: no hay prueba formal de lo que calcula cada instrucción de RV32E (eso se apoya en la comparación contra el base); nada se ha probado en la placa.

## 9. Preguntas típicas

1. **¿Por qué no hay adelantamiento?** Entre dos instrucciones del mismo hilo pasan 4 ciclos: cuando la siguiente lee el banco, la anterior ya escribió (`rtl/espino_core/espino_barrel_core.v:22` a `:25`, comentario del encabezado).
2. **¿Cómo sabe el core de qué hilo es cada instrucción?** No lo guarda con la instrucción: un contador de 2 bits (`tid_f`) dice quién está en F y las otras etapas son ese valor menos 1, 2 y 3 (`rtl/espino_core/espino_barrel_core.v:107`).
3. **¿Dónde están los registros de los cuatro hilos?** En las mismas BRAM del banco, con dirección `{hilo, registro}` (`rtl/espino_core/espino_barrel_regfile.v:55`). Usa 64 de 256 palabras.
4. **¿Puede un hilo leer o escribir un registro de otro?** No: probado formalmente para cualquier programa (propiedades P1, P6, P10 y P11 de `formal/barrel/propiedades.vh`) y comparado en cada instrucción de la campaña.
5. **¿Por qué un barrel si responde más lento?** Porque el diseño que compite corre cuatro estrategias a la vez. Cada hilo tiene CPI 4, pero el core completa una instrucción por ciclo. La latencia no cambia el patrimonio mientras llegue antes del tick: R1 usa el 19,6 % de la ronda 3. Para una sola regla, el segmentado es mejor y está medido.
6. **¿Cuál es el CPI?** 1,000 agregado y 4,000 por hilo, exactos, para cualquier mezcla (`docs/mediciones/barrel/cpi.txt`).
7. **¿Sigue siendo Espino?** Misma ISA, decodificador, ALU, LSU y bus, sin modificar. Cambia la microarquitectura. Y el profesor lo confirmó en persona el 16/11: se puede modificar lo que uno quiera y el Espino multihilo está bien (T126). El barrel puede competir.
8. **¿Qué pasa si dos hilos escriben la misma palabra?** Las dos escrituras ocurren, en ciclos distintos y en orden fijo. Evitar la carrera es tarea del programa: una palabra, un escritor.
9. **¿Encontraron algún error?** En el core, ninguno. En el método, tres: programas aleatorios que caían en un punto fijo, un `jalr` que sacaba a un hilo de su código, y un hilo que terminaba ejecutando datos compartidos (`docs/espino_barrel.md`, sección 8.2).
10. **¿Qué pasa si el programa no tiene la tabla de arranque?** Los hilos 1 a 3 parten en la segunda, tercera y cuarta instrucción del programa y el testbench da 2/4. En la placa falla en silencio. Por eso todo programa del barrel la lleva (`sw/fondo.s:157`).
