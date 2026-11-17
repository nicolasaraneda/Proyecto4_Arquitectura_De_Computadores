# Pruebas de práctica para la defensa

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Tres pruebas de 15 preguntas tomadas del banco (`docs/defensa/preguntas.md`, 156 preguntas), sin repetir entre ellas. Cada una tiene 7 básicas [B], 5 avanzadas [A] y 3 incómodas [I], repartidas por todas las secciones del banco. Las genera `python3 tools/defensa/pruebas.py`; si el banco cambia, se generan de nuevo.

**Cómo se usan.** Uno lee las preguntas en voz alta, sin mostrar la pauta. El que responde tiene unos 20 segundos por pregunta y no mira nada. Puntaje por pregunta: 2 si da la idea y el dato (la cifra o el archivo), 1 si da la idea sin el dato, 0 si no. Una prueba vale 30 puntos. Las [B] que fallen se repiten en el repaso siguiente; las [A] se le pasan al dueño de la pieza (`docs/defensa/plan_estudio.md`, sección 2).

Sugerencia de uso con el plan de estudio: la prueba 1 en el repaso del 21/11, la 2 en el del 24/11 y la 3 en el ensayo del 30/11, cada vez a alguien que no es dueño de la mayoría de las preguntas.

## Prueba 1

1. [A] ¿Cuál es el criterio de aceptación? *(pregunta 22, sección 2)*
2. [I] `max_media` no cumple ese criterio. ¿Por qué la eligieron? *(pregunta 23, sección 2)*
3. [B] ¿Cómo multiplican por 32 sin shifter? *(pregunta 39, sección 3)*
4. [B] ¿Por qué el Espino base tiene CPI 2? *(pregunta 50, sección 4)*
5. [A] ¿Por qué el salto tomado cuesta 2 y la clase estimó 3? *(pregunta 65, sección 5)*
6. [B] ¿Qué es un procesador barrel? *(pregunta 70, sección 6)*
7. [A] ¿Por qué la latencia no da patrimonio? *(pregunta 77, sección 6)*
8. [A] ¿Qué pasa si alguien escribe `emad` con k = 4? *(pregunta 89, sección 7)*
9. [B] ¿La extensión cambia el resultado de la competencia? *(pregunta 96, sección 7)*
10. [B] ¿Cuánto demora el fondo en responder? *(pregunta 108, sección 8)*
11. [B] ¿Qué es la tabla de parámetros? *(pregunta 115, sección 9)*
12. [B] ¿Qué alternativas de hardware construyeron y midieron? *(pregunta 140, sección 11)*
13. [I] La pregunta del enunciado: ¿eligieron la que más gana, la más rápida o la que mejor balancea? *(pregunta 145, sección 11)*
14. [A] ¿Cómo sabrán el SCLK real? *(pregunta 148, sección 12)*
15. [I] ¿Por qué no usaron la regla que da 40 957 en la práctica? *(pregunta 156, sección 13)*

## Prueba 2

1. [B] ¿Qué está probado y qué no? *(pregunta 6, sección 1)*
2. [I] ¿Un Espino de cuatro hilos con instrucciones propias sigue siendo Espino? *(pregunta 9, sección 1)*
3. [A] ¿Qué modelo ajustaron? *(pregunta 15, sección 2)*
4. [B] ¿Por qué no lleva contabilidad? *(pregunta 17, sección 2)*
5. [I] ¿Por qué la tabla del punto 3.1 muestra menos con `max_media` (25 973) que con la regla base (27 062)? *(pregunta 18, sección 2)*
6. [A] ¿Por qué hay peor caso si el programa no tiene saltos que dependan del precio? *(pregunta 47, sección 3)*
7. [B] ¿Qué memoria usa el programa? *(pregunta 49, sección 3)*
8. [B] ¿Qué es la ley de hierro y qué factor ataca cada pieza? *(pregunta 53, sección 4)*
9. [B] ¿Qué es el segmentado y compite? *(pregunta 62, sección 5)*
10. [A] ¿Puede un hilo leer o escribir un registro de otro? *(pregunta 75, sección 6)*
11. [A] ¿Cuál es el error más fácil de cometer con una extensión en un barrel? *(pregunta 94, sección 7)*
12. [B] ¿Cómo combina los votos el supervisor? *(pregunta 98, sección 8)*
13. [I] ¿Qué pasa si un hilo se cuelga? *(pregunta 103, sección 8)*
14. [A] ¿Qué es un molde y por qué hace falta? *(pregunta 118, sección 9)*
15. [B] ¿Cuál es el Ppeak de cada core? *(pregunta 143, sección 11)*

## Prueba 3

1. [B] ¿Qué idea hay detrás del algoritmo? *(pregunta 11, sección 2)*
2. [A] ¿Cuánta reversión hay realmente? *(pregunta 14, sección 2)*
3. [B] ¿Qué hace el bloque `primero`? *(pregunta 44, sección 3)*
4. [B] ¿Por qué no tiene riesgos de datos ni de control? *(pregunta 72, sección 6)*
5. [I] ¿Por qué un barrel si cada hilo responde más lento? *(pregunta 76, sección 6)*
6. [B] ¿Por qué custom-0? *(pregunta 86, sección 7)*
7. [A] ¿Cuánto cuestan? *(pregunta 91, sección 7)*
8. [I] ¿Qué aportan los otros tres hilos si deciden casi igual que `max_media`? *(pregunta 104, sección 8)*
9. [A] ¿Por qué el fondo responde más lento si usa cuatro hilos? *(pregunta 109, sección 8)*
10. [B] ¿Cuándo dispara el vigilante? *(pregunta 119, sección 9)*
11. [I] ¿Está permitido reconfigurar la FPGA durante una ronda? *(pregunta 125, sección 9)*
12. [B] ¿Cuáles son los tres modelos y cómo se comparan? *(pregunta 126, sección 10)*
13. [A] ¿Qué es la autoprueba en placa? *(pregunta 136, sección 10)*
14. [B] ¿Qué desempeño logra cada variante? *(pregunta 144, sección 11)*
15. [A] ¿Qué se prueba el 26/11 con la maestra? *(pregunta 153, sección 12)*

## Pauta de la prueba 1

**1. [A] ¿Cuál es el criterio de aceptación?** (pregunta 22)
Una candidata reemplaza a la base si sube media y peor bloque en la práctica, media y percentil 5 en los remuestreos, y en ninguna familia baja más de 1 %. Además se informa la diferencia pareada con su error estándar.
Dato: `ref/protocolo.py:36` a `:40`.

**2. [I] `max_media` no cumple ese criterio. ¿Por qué la eligieron?** (pregunta 23)
Es cierto y está escrito: falla por 26 puntos en la media de los bloques (dentro del error de 238) y por familias de estrés. Se eligió por el perfil de riesgo del grupo (maximizar el patrimonio esperado): es el único candidato que sube la media en las dos evidencias independientes, sin agregar instrucciones.
Dato: `docs/decisiones.md:339`, `docs/algoritmo.md:454`.

**3. [B] ¿Cómo multiplican por 32 sin shifter?** (pregunta 39)
Cinco sumas: `x6 = p + p` y después cuatro veces `x6 = x6 + x6`.
Dato: `sw/trade.s:100` a `:104`.

**4. [B] ¿Por qué el Espino base tiene CPI 2?** (pregunta 50)
Porque el banco de registros es BRAM con lectura registrada: cada instrucción espera un ciclo a sus operandos (`ops_valid_q`) y otro para ejecutar.
Dato: `rtl/espino_core/espino_id_stage.v:209` a `:213`.

**5. [A] ¿Por qué el salto tomado cuesta 2 y la clase estimó 3?** (pregunta 65)
La clase supone una etapa de fetch de un ciclo completo con dos instrucciones detrás del salto. Aquí IF e ID son medio ciclo cada una y solo se anula una.
Dato: `docs/mediciones/espino_segmentado.txt:52` a `:56`.

**6. [B] ¿Qué es un procesador barrel?** (pregunta 70)
Un core con varios hilos por hardware que reparte el pipeline por turnos fijos: un hilo por ciclo, sin prioridades. Aquí 4 hilos por un pipeline de 4 etapas.
Dato: `rtl/espino_core/espino_barrel_core.v:6` a `:8`.

**7. [A] ¿Por qué la latencia no da patrimonio?** (pregunta 77)
El byte que la maestra lee en el tick n se ejecuta al precio n, sea que el programa respondió en 22 ciclos o en 443. R0, el segmentado y el barrel dan con `max_media` los mismos 20 000 bytes.
Dato: `docs/codiseno.md:353`.

**8. [A] ¿Qué pasa si alguien escribe `emad` con k = 4?** (pregunta 89)
El ensamblador lo rechaza. Si la palabra llega igual a la memoria, el core la trata como ilegal: no escribe, no accede al bus y no salta. Probado formalmente (X4) y con la mutación `MUTA_XD_K`.
Dato: `tools/asm/core.py:413`, `rtl/espino_core/espino_xd.v:56`.

**9. [B] ¿La extensión cambia el resultado de la competencia?** (pregunta 96)
No: las decisiones son las mismas bit a bit. Aporta ciclos libres y co-diseño medido: la respuesta de `max_media` en el barrel baja de 83 a 63 ciclos.
Dato: `docs/puertas.md:66`.

**10. [B] ¿Cuánto demora el fondo en responder?** (pregunta 108)
223,01 ciclos en promedio (8,92 µs), 443 en el peor caso del testbench y 444 barriendo fases: 19,6 % de la ronda 3. Con el plazo agotado, 568.
Dato: `docs/fondo.md:318`, `docs/mediciones/p7/variantes.txt:23`.

**11. [B] ¿Qué es la tabla de parámetros?** (pregunta 115)
Una BRAM de 256 valores de 16 bits en `0x8002_0000`, de solo lectura, con las 20 constantes de `sw/fondo.s`. No calcula ni decide.
Dato: `rtl/pochoco_tabla.v:6` a `:19`.

**12. [B] ¿Qué alternativas de hardware construyeron y midieron?** (pregunta 140)
Segmentado, barrel en un hilo, barrel con `emad` y `devk`, R1 y R2. Base y segmentado con la extensión están predichos con Amdahl, porque construirlos toca el RTL de R0.
Dato: `docs/mediciones/p7/variantes.txt:9` a `:15`, `docs/decisiones.md:551`.

**13. [I] La pregunta del enunciado: ¿eligieron la que más gana, la más rápida o la que mejor balancea?** (pregunta 145)
Ninguna de las tres en sentido estricto, y lo decimos: la más rápida por hilo es el segmentado, y en patrimonio empatan. Elegimos R1 por co-diseño (cuatro hilos, extensión usada, 56 operaciones útiles por tick, 80 % de holgura en la ronda 3) aceptando que no suma puntos (T50).
Dato: `docs/codiseno.md:346`.

**14. [A] ¿Cómo sabrán el SCLK real?** (pregunta 148)
Con el medidor del SPI: un bitstream aparte que escucha a la maestra y muestra en los 7 segmentos el período de SCLK, el período entre precios y los tiempos de `CS_n`. Se graba el 26/11 antes que los peldaños.
Dato: `rtl/medidor/medidor_spi.v:15`, `docs/decisiones.md:589`.

**15. [I] ¿Por qué no usaron la regla que da 40 957 en la práctica?** (pregunta 156)
Porque 40 957 es el resultado en la misma serie con que se eligieron sus parámetros, compuesto sobre 20 000 ticks: en los 10 bloques de 2000 la ventaja sobre `max_media` es +346 +- 321 por bloque, un error, y su vecino a 2,75 desviaciones da 22 421 en la misma serie. Con el criterio que fijamos antes de medir (remuestreos de trozos de 100 ticks y el modelo calibrado, con una semilla reservada) pierde 0,09 puntos por ronda. Lo que no ocultamos: con trozos de 250 ticks o más, y eligiendo los parámetros en una mitad de la práctica para probarlos en la otra, `zscore` gana; en series del modelo, no. Depende de si la serie oculta se parece a la práctica en escalas de cientos de ticks, y eso no se sabe. La decisión y su razón están en `docs/decisiones.md` (T129 y siguientes).
Dato: `docs/zscore.md:101` (largo del trozo), `:131` (las dos lecturas) y `:142` (la grilla en la práctica); `docs/mediciones/zscore/trozos.txt`, `reservada_s4.txt`.

## Pauta de la prueba 2

**1. [B] ¿Qué está probado y qué no?** (pregunta 6)
R0, R1 y R2 pasaron los ocho criterios de la puerta de simulación. La puerta de placa está incompleta: el 16/11, en la placa, R2 pasó la firma a 0,1 ms y la media hora sin disparo, y el relevo se midió en 35,50 ms por la UART; R0 mostró a los tres períodos la mitad baja de su firma ("3C") y le falta la mitad alta ("A2"); faltan además las tres firmas de R1, la de R2 a 1 ms y 10 ms y ver la imagen testigo después del relevo (`docs/mediciones/placa_16nov.md`). Falta la puerta de la maestra real del 26/11.
Dato: `docs/puertas.md`, secciones de R0, R1 y R2 y "Puerta de placa"; `docs/mediciones/placa_16nov.md`.

**2. [I] ¿Un Espino de cuatro hilos con instrucciones propias sigue siendo Espino?** (pregunta 9)
Sí. El profesor Jorge Gómez nos confirmó en persona el 16/11 que se puede modificar lo que uno quiera y que cualquier decisión de diseño es válida; le describimos el Espino multihilo y dijo que estaba perfecto. Además, técnicamente: misma ISA RV32E, mismo decodificador, ALU, LSU y bus, sin modificar; cambia la microarquitectura, y la extensión usa custom-0, que RISC-V reserva para esto.
Dato: `docs/decisiones.md`, T126; `docs/arbol_decision.md:11`; `docs/espino_barrel.md`, sección 9.

**3. [A] ¿Qué modelo ajustaron?** (pregunta 15)
Precio = redondeo(nivel + transitoria): nivel como paseo aleatorio, transitoria AR(1) con phi = 0,961, dos regímenes de volatilidad y saltos poco frecuentes. Máxima verosimilitud con filtro de Kalman y Nelder-Mead.
Dato: `ref/generador.py:187`, `docs/algoritmo.md:44`.

**4. [B] ¿Por qué no lleva contabilidad?** (pregunta 17)
Porque "comprar 63" y "vender 63" son idempotentes: repetirlos con la caja gastada o sin acciones no hace nada. Y una contabilidad propia podría desincronizarse de la oficial.
Dato: `docs/trade_s.md:27`.

**5. [I] ¿Por qué la tabla del punto 3.1 muestra menos con `max_media` (25 973) que con la regla base (27 062)?** (pregunta 18)
Porque el 27 062 está sesgado: los parámetros de la regla base se eligieron mirando esa misma serie. Fuera de muestra `max_media` gana 0,7 % en remuestreos y 1,4 % en familias plausibles, con 7 y 10 errores estándar. En los bloques de práctica queda 26 abajo con un error de 238: no se distinguen.
Dato: `docs/mediciones/tabla_3_1.txt:6` y `:7`, `docs/decisiones.md:339`.

**6. [A] ¿Por qué hay peor caso si el programa no tiene saltos que dependan del precio?** (pregunta 47)
Lo que varía es en qué punto de la vuelta de sondeo (8 ciclos) llega el precio. El testbench tiene un período de 2500 ciclos, no múltiplo de 8, y recorre 4 fases: 38, 40, 42 y 44.
Dato: `docs/trade_s.md:191`.

**7. [B] ¿Qué memoria usa el programa?** (pregunta 49)
40 palabras de programa y una sola palabra de datos, `TMP`, la última de la RAM, para el desplazamiento. El `.org 0x800` rellena el `.hex` a 512 palabras.
Dato: `sw/trade.s:69` y `:132`.

**8. [B] ¿Qué es la ley de hierro y qué factor ataca cada pieza?** (pregunta 53)
Tiempo = IC × CPI × Tclk. El segmentado y el barrel atacan el CPI; la extensión ataca el IC; el PLL atacaría Tclk, pero no existe en este encapsulado.
Dato: `docs/codiseno.md:48`.

**9. [B] ¿Qué es el segmentado y compite?** (pregunta 62)
El Espino con pipeline de 3 etapas: CPI 1 en ALU, 2 en load y salto tomado. No compite; es una variante medida del punto 3.3 y la más rápida por hilo (22 ciclos de respuesta, 1,86 veces R0).
Dato: `docs/mediciones/p7/variantes.txt:20`.

**10. [A] ¿Puede un hilo leer o escribir un registro de otro?** (pregunta 75)
No: probado formalmente para cualquier programa (P1, P6, P10 y P11) y comparado en cada instrucción de la campaña.
Dato: `formal/barrel/propiedades.vh:53` y `:91`.

**11. [A] ¿Cuál es el error más fácil de cometer con una extensión en un barrel?** (pregunta 94)
Mirar la instrucción equivocada: mientras una está en X, lo que sale de la memoria es de otro hilo. `espino_xd_opa` usa el `funct3` registrado. Es la mutación `MUTA_XD_HILO`.
Dato: `rtl/espino_core/espino_barrel_core.v:50` a `:53`.

**12. [B] ¿Cómo combina los votos el supervisor?** (pregunta 98)
Suma los pesos (en dieciseisavos, iniciales 6/5/5) de los gestores que votan comprar; con 8/16 o más escribe comprar 63 y si no vender 63.
Dato: `sw/fondo.s:252` a `:266`.

**13. [I] ¿Qué pasa si un hilo se cuelga?** (pregunta 103)
Si es un gestor: su voto queda viejo, el supervisor espera a lo más 8 vueltas y usa su propia `max_media` en ese lugar; la decisión sale siempre (30 de 30 corridas, peor caso 679 ciclos). Si es el supervisor, nadie escribe `DECISION`: en R1 la maestra repite el último byte; en R2 el vigilante reconfigura con R0 al quinto precio.
Dato: `sw/fondo.s:230` a `:241`, `rtl/vigilante.v:81`.

**14. [A] ¿Qué es un molde y por qué hace falta?** (pregunta 118)
El mismo diseño sintetizado con las memorias llenas de un patrón al azar. `icebram` ubica una memoria por su contenido, y la tabla definitiva (236 ceros) no es distinguible. Se comprueba que el molde con `icebram` da el bitstream directo byte por byte.
Dato: `docs/tabla_vigilante.md:53`, `docs/decisiones.md:467`.

**15. [B] ¿Cuál es el Ppeak de cada core?** (pregunta 143)
Base 12,5 MOPS (25 MHz × 0,5), segmentado 25, barrel 25 con cuatro hilos y 6,25 con uno.
Dato: `docs/mediciones/barrel/cpi.txt:37`, `docs/mediciones/espino_segmentado.txt:48`.

## Pauta de la prueba 3

**1. [B] ¿Qué idea hay detrás del algoritmo?** (pregunta 11)
Reversión a la media: si el precio cae lo suficiente bajo su media reciente, tiende a volver. Se compra cuando el precio está más de 3 unidades bajo la media exponencial y se vende cuando la recupera.
Dato: `ref/trader.py:74`, `docs/trade_s.md`, sección 1.

**2. [A] ¿Cuánta reversión hay realmente?** (pregunta 14)
Menos de la que parece: un paseo aleatorio redondeado a enteros da VR(100) = 0,77. La mitad de la caída es redondeo y no se puede explotar porque la orden se ejecuta un tick después. Lo real es una transitoria con vida media de 17,5 ticks.
Dato: `docs/algoritmo.md:71`.

**3. [B] ¿Qué hace el bloque `primero`?** (pregunta 44)
Con el primer precio deja `S = 32 p`, así `dev = 0` y no se opera. La media parte en el primer precio que el programa ve, cualquiera sea.
Dato: `sw/trade.s:77` a `:88`.

**4. [B] ¿Por qué no tiene riesgos de datos ni de control?** (pregunta 72)
Entre dos instrucciones del mismo hilo pasan 4 ciclos: cuando la siguiente lee el banco, la anterior ya escribió; cuando se busca, el salto anterior ya se resolvió. No hay adelantamiento, burbujas ni anulaciones.
Dato: `rtl/espino_core/espino_barrel_core.v:22` a `:25`.

**5. [I] ¿Por qué un barrel si cada hilo responde más lento?** (pregunta 76)
Porque el diseño que compite corre cuatro reglas a la vez: cada hilo tiene CPI 4, pero el core completa una instrucción por ciclo. La latencia no cambia el patrimonio mientras la decisión llegue antes de la transacción siguiente, y R1 usa el 19,6 % de la ronda 3. Para una sola regla el segmentado es mejor, y está medido.
Dato: `docs/codiseno.md:353`, `docs/mediciones/p7/variantes.txt:41`.

**6. [B] ¿Por qué custom-0?** (pregunta 86)
Es uno de los opcodes que RISC-V reserva para extensiones propias: ninguna extensión estándar lo va a ocupar.
Dato: `rtl/espino_core/espino_xd.v:44`.

**7. [A] ¿Cuánto cuestan?** (pregunta 91)
`emad` y `devk`: 52 celdas, 0 BRAM, frecuencia mínima 48,92 MHz. Las tres: 96 celdas. El costo es el multiplexor del operando A.
Dato: `docs/mediciones/xd/timing.txt`, `docs/decisiones.md:383`.

**8. [I] ¿Qué aportan los otros tres hilos si deciden casi igual que `max_media`?** (pregunta 104)
En la serie de práctica, poco o nada en los bytes: en el testbench a 0,1 ms escribe los mismos 20 000 bytes que `max_media` (los dos terminan con 26 070); a 1 ms y 10 ms no: el fondo termina con 25 031 y `max_media` con 26 070 (`docs/mediciones/fondo/r1/equiv.txt`, `docs/mediciones/p7/gemelo.txt`). Viendo todos los precios, `ref/fondo.py` da 26 388 y `ref/trader.py` 25 973. Con pesos 6/5/5 la banda del medio define la mayoría; lo que los separa es el ajuste de pesos. En otras series difieren: 1816 bytes en una de reversión. Lo que aportan es co-diseño: 56 operaciones útiles por tick en vez de 8.
Dato: `docs/fondo.md:377` y `:336`, `docs/mediciones/fondo/r1/equiv.txt`.

**9. [A] ¿Por qué el fondo responde más lento si usa cuatro hilos?** (pregunta 109)
Cada hilo avanza una instrucción cada 4 ciclos y el supervisor espera los votos. El barrel reparte el trabajo; no lo acelera para un hilo. Además el lazo de votos con plazo y la tabla cuestan ciclos.
Dato: `docs/fondo.md:302`.

**10. [B] ¿Cuándo dispara el vigilante?** (pregunta 119)
Al quinto precio seguido sin escritura en `DECISION` (K = 4), y espera a que `CS_n` suba. Entonces activa `SB_WARMBOOT` con `S1 S0 = 01` y la FPGA carga la imagen 1, que es R0.
Dato: `rtl/vigilante.v:65` y `:81`, `rtl/pochoco_soc.v:295`.

**11. [I] ¿Está permitido reconfigurar la FPGA durante una ronda?** (pregunta 125)
No lo preguntamos en particular. El profesor nos dijo el 16/11 que cualquier decisión de diseño es válida, y lo tomamos como cubierto por esa respuesta general, sin confirmación específica; está escrito así en T126. Si el ayudante lo prohibiera de forma explícita, R2 no compite y el titular es R1: el supervisor colgado queda sin defensa en vivo y entre rondas se graba R0.
Dato: `docs/arbol_decision.md:15` y `:16`.

**12. [B] ¿Cuáles son los tres modelos y cómo se comparan?** (pregunta 126)
La referencia en Python (valores), el RTL (lo que se sintetiza) y el gemelo en C (ciclos). Referencia contra RTL por `decisiones.csv` byte a byte; gemelo contra RTL por trazas idénticas ciclo a ciclo.
Dato: `docs/defensa/verificacion.md`, sección 1.

**13. [A] ¿Qué es la autoprueba en placa?** (pregunta 136)
El SoC del peldaño con una maestra SPI dentro de la FPGA que manda 2000 precios de un paseo aleatorio a los tres períodos y muestra una firma CRC-16 de las decisiones. La firma esperada de R0 es `a23c`, igual en gemelo, referencia, RTL y bitstream.
Dato: `tools/autoprueba.py:61`, `docs/decisiones.md:532`.

**14. [B] ¿Qué desempeño logra cada variante?** (pregunta 144)
R0 3,92 MOPS, segmentado 7,41, barrel un hilo 2,08, barrel con extensión 4,17, R1 5,34 (56 operaciones por tick).
Dato: `docs/mediciones/p7/variantes.txt:28` a `:33`.

**15. [A] ¿Qué se prueba el 26/11 con la maestra?** (pregunta 153)
Medir el SPI con el medidor, después los peldaños del más seguro al más arriesgado, el relevo de R2 con la falla inyectada si se permite, y las preguntas al ayudante.
Dato: `docs/checklist_26nov.md:40`, `:64` y `:85`.
