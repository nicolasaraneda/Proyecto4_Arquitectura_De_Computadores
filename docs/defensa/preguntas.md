# Banco de preguntas de la defensa

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Preguntas que el profesor o un ayudante pueden hacer a cualquiera de los tres sobre el informe, el algoritmo, el assembly y el RTL. Cada respuesta está pensada para decirse en voz alta en unos 20 segundos, con el dato y el archivo que la respaldan.

- **[B]** básica: los tres tienen que poder responderla sin mirar nada.
- **[A]** avanzada: la responde con soltura el dueño de la pieza (`docs/defensa/plan_estudio.md`), y los otros dos al menos en una frase.
- **[I]** incómoda: pregunta que puede poner en duda una decisión. La respuesta es honesta y dice lo que se aceptó a sabiendas.
- "Dato" apunta a un `archivo:línea` de la rama de entrega, o a una sección de un documento. Si una cifra de aquí no calza con su fuente, manda la fuente.

Los documentos de estudio que desarrollan cada sección son los de esta carpeta (`docs/defensa/*.md`), y las cifras de memoria están en `docs/defensa/cifras.md`.

---

## 1. El diseño que compite y por qué

**1. [B] ¿Qué compite el 1/12?**
Una escalera de tres bitstreams: R0 (Espino base con `max_media`), R1 (Espino barrel de 4 hilos con `emad`, `devk`, la tabla en BRAM y `sw/fondo.s`) y R2 (R1 con el vigilante y R0 como imagen de respaldo). Compite el peldaño más alto que pase las puertas de simulación, placa y maestra.
Dato: `docs/puertas.md:7` a `:11`, `docs/decisiones.md:326`.

**2. [B] ¿Cómo se elige el peldaño el día de la competencia?**
Con un árbol de una página: R0 si el ayudante dice que el barrel no es Espino, si R1 falla con la maestra, si el SCLK de la ronda 3 es menor que 115 kHz o el período menor que 27 us; R2 si se permite reconfigurar durante una ronda y pasó sus puertas; si no, R1.
Dato: `docs/arbol_decision.md:11` a `:16`.

**3. [I] ¿Por qué compiten con un diseño que, según ustedes mismos, no suma puntos?**
Es la decisión T50, tomada a sabiendas: según la factibilidad el fondo suma +0,007 puntos esperados a 2 000 ticks y -0,005 a 20 000 contra `max_media` sola, y agrega riesgo en vivo. Se elige por lo que representa como co-diseño (procesador rediseñado, extensión usada de verdad, cuatro reglas en paralelo, todo medido). El riesgo está acotado: R0 es el respaldo y el árbol dice cuándo usarlo.
Dato: `docs/decisiones.md:330`.

**4. [I] Entonces, ¿no habría sido más sensato competir con R0 o con el segmentado?**
En puntos esperados, empatan: la diferencia medida es de milésimas. La recomendación de la factibilidad era el segmentado con `emad` y `max_media`; se descartó a favor de T50. Lo que se perdió está escrito: días de trabajo y margen para reaccionar a una falla de placa.
Dato: `docs/decisiones.md:331` y `:332`.

**5. [B] ¿Qué es `max_media`?**
La regla base de reversión a la media con el umbral de entrada en 3 unidades bajo la media en vez de 4. En el código cambia una constante: `UMBRAL_COMPRA` pasa de -128 a -96.
Dato: `sw/trade.s:64`, `docs/decisiones.md:335`.

**6. [B] ¿Qué está probado y qué no?**
R0, R1 y R2 pasaron los ocho criterios de la puerta de simulación. Falta la puerta de placa (autoprueba; la de R0 está lista para grabar) y la de la maestra real del 26/11. Nada se ha probado todavía en la placa.
Dato: `docs/puertas.md:43` y `:90`.

**7. [B] ¿Qué es la puerta de simulación?**
Ocho criterios: testbench oficial 4/4, equivalencia con la referencia, timing en 10 semillas, peor caso barriendo fases bajo la mitad del presupuesto, core contra el base, degradación, estrés y simulación del bitstream ruteado.
Dato: `docs/puertas.md:17` a `:24`.

**8. [A] ¿Qué compila el comando del encabezado del testbench oficial?**
Sin definiciones compila R0. Si compite R1 o R2, `make peldano-fijar` agrega `rtl/00_peldano.v` con las definiciones (va primero en orden alfabético) y `sw/trade.s` pasa a ser `sw/fondo.s`. Está preparado y se ejecuta después del 26/11.
Dato: `docs/peldano.md`, sección "Cómo se hace".

**9. [I] ¿Un Espino de cuatro hilos con instrucciones propias sigue siendo Espino?**
Misma ISA RV32E, mismo decodificador, ALU, LSU y bus, sin modificar; cambia la microarquitectura, y la extensión usa custom-0, que RISC-V reserva para esto. Pero no lo decidimos nosotros: es una pregunta al ayudante, y si dice que no, compite R0 sin discusión.
Dato: `docs/arbol_decision.md:11`, `docs/espino_barrel.md`, sección 9.

**10. [B] ¿El hardware agregado decide?**
No. La decisión la calcula el core con instrucciones: un hilo lee `PRICE` y escribe `DECISION`. `emad` y `devk` son aritmética sin estado, la tabla es memoria de solo lectura y el vigilante solo cuenta precios.
Dato: `sw/fondo.s:192` y `:266`, `rtl/pochoco_tabla.v:6` y `:7`.

---

## 2. Algoritmo

**11. [B] ¿Qué idea hay detrás del algoritmo?**
Reversión a la media: si el precio cae lo suficiente bajo su media reciente, tiende a volver. Se compra cuando el precio está más de 3 unidades bajo la media exponencial y se vende cuando la recupera.
Dato: `ref/trader.py:74`, `docs/trade_s.md`, sección 1.

**12. [I] ¿Por qué reversión y no tendencia?**
La razón de varianza es menor que 1 a 10, 50 y 100 ticks (0,77, 0,62 y 0,53) en los 20 bloques de 1000 ticks, la autocorrelación de los cambios es -0,11, y seguir tendencia termina con mediana 5 566 en 336 configuraciones. Las familias sintéticas confirman el riesgo: sin reversión no se gana y con tendencia se pierde.
Dato: `ref/hallazgos.py:42` y `:55`, resultados en `docs/estado.md`, tramo 1 (tabla de hallazgos).

**13. [A] ¿Qué es la razón de varianza?**
La varianza del cambio a k ticks dividida por k veces la varianza del cambio a 1 tick. En un paseo aleatorio vale 1; menor que 1 indica que los movimientos se deshacen.
Dato: `ref/hallazgos.py:42`.

**14. [A] ¿Cuánta reversión hay de verdad?**
Menos de la que parece: un paseo aleatorio redondeado a enteros da VR(100) = 0,77. La mitad de la caída es redondeo y no se puede explotar porque la orden se ejecuta un tick después. Lo real es una transitoria con vida media de 17,5 ticks.
Dato: `docs/algoritmo.md:71`.

**15. [A] ¿Qué modelo ajustaron?**
Precio = redondeo(nivel + transitoria): nivel como paseo aleatorio, transitoria AR(1) con phi = 0,961, dos regímenes de volatilidad y saltos poco frecuentes. Máxima verosimilitud con filtro de Kalman y Nelder-Mead.
Dato: `ref/generador.py:187`, `docs/algoritmo.md:44`.

**16. [B] ¿Cómo decide la cantidad?**
No la decide: siempre 63. La maestra recorta la compra a lo que alcanza con la caja y la venta a lo que se tiene, y una orden que queda en cero no paga comisión. El programa expresa una posición objetivo, todo adentro o todo afuera.
Dato: `tb/tb_proyecto_4.sv:73` y `:78`, `docs/trade_s.md:27`.

**17. [B] ¿Por qué no lleva contabilidad?**
Porque "comprar 63" y "vender 63" son idempotentes: repetirlos con la caja gastada o sin acciones no hace nada. Y una contabilidad propia podría desincronizarse de la oficial.
Dato: `docs/trade_s.md:27`.

**18. [I] ¿Por qué la tabla del punto 3.1 muestra menos con `max_media` (25 973) que con la regla base (27 062)?**
Porque el 27 062 está sesgado: los parámetros de la regla base se eligieron mirando esa misma serie. Fuera de muestra `max_media` gana 0,7 % en remuestreos y 1,4 % en familias plausibles, con 7 y 10 errores estándar. En los bloques de práctica queda 26 abajo con un error de 238: no se distinguen.
Dato: `docs/mediciones/tabla_3_1.txt:6` y `:7`, `docs/decisiones.md:339`.

**19. [A] ¿Por qué alfa 1/32?**
Con alfa más grande la media sigue al precio y no queda desviación que operar; con más chica mejora el modelo y empeora el remuestreo. 1/32 es el mejor compromiso, y además son cables en la extensión (k = 5).
Dato: `docs/algoritmo.md:248`.

**20. [A] ¿Por qué entrar a 3 unidades?**
Bandas más angostas suben la media en el modelo y bajan el percentil 5. El remuestreo tiene su máximo con E entre 96 y 128 y el modelo con E = 48. Donde coinciden las dos evidencias es E = 96.
Dato: `docs/algoritmo.md:234`.

**21. [B] ¿Cómo evaluaron el algoritmo?**
Con un protocolo fijado antes de probar ideas: 10 bloques de práctica, 1000 remuestreos por bloques de 100 ticks de los incrementos y 14 familias sintéticas calibradas (4 plausibles y 10 de estrés), con una semilla reservada para los finalistas.
Dato: `ref/series.py:56`, `:75`, `:267` y `:270`, `docs/decisiones.md:160`.

**22. [A] ¿Cuál es el criterio de aceptación?**
Una candidata reemplaza a la base si sube media y peor bloque en la práctica, media y percentil 5 en los remuestreos, y en ninguna familia baja más de 1 %. Además se informa la diferencia pareada con su error estándar.
Dato: `ref/protocolo.py:36` a `:40`.

**23. [I] `max_media` no cumple ese criterio. ¿Por qué la eligieron?**
Es cierto y está escrito: falla por 26 puntos en la media de los bloques (dentro del error de 238) y por familias de estrés. Se eligió por el perfil de riesgo del grupo (maximizar el patrimonio esperado): es el único candidato que sube la media en las dos evidencias independientes, sin agregar instrucciones.
Dato: `docs/decisiones.md:339`, `docs/algoritmo.md:454`.

**24. [I] ¿Cómo saben que no es sobreajuste?**
Tres cosas: los finalistas se evaluaron con una semilla que no se usó para elegir nada (las dos semillas coinciden dentro de 1 %); los parámetros están en una meseta (E entre 80 y 128 da medias dentro de 60 puntos); y el modelo, que no usa los cambios de la práctica uno por uno, coincide en el signo de la mejora.
Dato: `docs/algoritmo.md:471`.

**25. [I] ¿Cuánto del resultado es suerte?**
En una ronda, la mayor parte: con la misma regla los remuestreos terminan entre 6 520 y 15 637. `max_media` supera a comprar y mantener en el 71 % de los remuestreos: una ronda de cada tres puede terminar bajo esa referencia. En tres rondas pesa menos, pero sigue pesando.
Dato: `docs/protocolo.md:194`, `docs/algoritmo.md:481`.

**26. [I] ¿Qué pasa si la serie oculta es distinta?**
Está medido en las familias de estrés: sin reversión (paseo) no se gana, con tendencia a la baja se pierde (percentil 5 de 4 631), con más volatilidad o precios bajos se gana más. La serie oculta puede salir de otro generador; es una pregunta al ayudante.
Dato: `docs/algoritmo.md:477`.

**27. [A] ¿Por qué no usaron el filtro de Kalman si es el estimador óptimo del modelo?**
Porque el problema está mal condicionado: después de filtrar, la incertidumbre de la transitoria baja de 1,19 a 1,11. Empata con la media exponencial y cuesta unas 140 instrucciones contra 27.
Dato: `docs/algoritmo.md:475`.

**28. [A] ¿Por qué no usar la política óptima del modelo?**
Es óptima para el modelo gaussiano, no para la serie: gana 4 puntos en el modelo y pierde 7 en el remuestreo. Se usa como cota (8,4 % por ronda) y como guía de la forma: la política óptima también es de bandas.
Dato: `docs/algoritmo.md:473`, `docs/mediciones/politica_optima.txt`.

**29. [A] ¿Probaron cortar pérdidas?**
Sí: tope de tiempo, tope de precio, guardia de régimen y tope de pérdida. Todos suben el peor caso en tendencia y cuestan media cuando la serie revierte, porque vender después de una caída es vender en el peor momento. Quedaron fuera de la competencia con sus números.
Dato: `docs/algoritmo.md:299` y `:340`.

**30. [A] ¿Por qué la guardia no es un test estadístico?**
No tiene potencia: con 2000 ticks la razón de varianza de una serie que revierte y la de un paseo aleatorio se traslapan casi enteras. La guardia que se construyó mide si las últimas entradas volvieron.
Dato: `docs/algoritmo.md:479`, `docs/decisiones.md:226`.

**31. [A] ¿Por qué no aprender en vivo (perceptrón, población de traders)?**
Hay una unidad de log-verosimilitud de evidencia por ronda: adaptarse es ajustar con casi nada de información. Los tres intentos pierden en el remuestreo (-199, -57 y -16).
Dato: `docs/algoritmo.md:324`, `docs/mediciones/experimentos.txt`.

**32. [B] ¿Cuáles son las referencias del punto 3.1?**
No operar: 10 000. Comprar y mantener: 6 497. `max_media`: 25 973 con 624 órdenes, 3 120 de comisiones y pérdida máxima de 6 295, en la serie completa viendo todos los precios.
Dato: `docs/mediciones/tabla_3_1.txt:3` a `:7`.

**33. [A] ¿Por qué el patrimonio en el testbench no es el mismo que en la tabla?**
Por el reset de encendido largo (4095 ciclos): en el testbench el programa no ve los 2 primeros precios a 0,1 ms y el primero a 1 y 10 ms, y la media parte en otro precio. La referencia lo modela. En la competencia la placa está encendida antes.
Dato: `ref/trader.py:101`, `docs/trade_s.md:146`.

**34. [I] ¿Y si cambian la comisión o la caja el mismo día?**
El programa no las conoce: no llegan por SPI. `tools/retune.py` busca umbrales con el mismo protocolo y solo cambia si la media sube más de 0,2 % sin bajar el percentil 5 ni el peor bloque. Con las reglas publicadas devuelve los actuales; cambia con comisión de 20 o más, y esos juegos ya están construidos.
Dato: `tools/retune.py:195`, `docs/arbol_decision.md:33` a `:35`.

**35. [A] ¿Por qué no se ajusta solo a la comisión, en el chip?**
Porque el programa no recibe la comisión ni ve el patrimonio. Inferirla exigiría llevar la contabilidad, que el diseño evita a propósito.
Dato: `docs/contingencia.md:81`.

---

## 3. Assembly: `sw/trade.s`

**36. [B] ¿Cuál es la estructura del ciclo principal?**
Esperar (sondeo de `STATUS`), leer `PRICE`, calcular `dev = 32 p - S`, decidir sin saltos, un solo store a `DECISION`, y después actualizar la media y volver.
Dato: `sw/trade.s:91` a `:129`.

**37. [B] ¿Por qué la media se actualiza después de escribir `DECISION`?**
Para que la respuesta salga lo antes posible: la decisión usa la media anterior al precio nuevo, igual que la referencia, y lo que viene después no cuenta en el tiempo de respuesta.
Dato: `sw/trade.s:118` y `:121`.

**38. [B] ¿Qué representación de punto fijo usan?**
La media se guarda multiplicada por 32 (5 bits de fracción): `S` va de 32 a 8160, 13 bits. `dev` queda entre -8128 y 8128.
Dato: `sw/trade.s:47` a `:50`, `docs/trade_s.md`, sección 2.

**39. [B] ¿Cómo multiplican por 32 sin shifter?**
Cinco sumas: `x6 = p + p` y después cuatro veces `x6 = x6 + x6`.
Dato: `sw/trade.s:100` a `:104`.

**40. [A] ¿Cómo desplazan a la derecha un número con signo?**
Con una identidad: como `32 p` es múltiplo de 32, `(32 p - S) >> 5 = p - ((S + 31) >> 5)`, y `S + 31` nunca es negativo.
Dato: `docs/trade_s.md:68`, `sw/trade.s:36`.

**41. [A] ¿Y cómo desplazan un positivo 5 bits a la derecha?**
Multiplican por 8 con tres sumas, guardan la palabra y leen su segundo byte con `lbu`: `x >> 5 = (8 x) >> 8`. Cabe porque `(8160 + 31) × 8 < 65 536`. Se revisó para todos los S entre 0 y 8160.
Dato: `sw/trade.s:121` a `:126`.

**42. [B] ¿Por qué no hay saltos que dependan del precio?**
Las comparaciones se hacen con `slti` (0 o 1) y la posición con `or` y `and`. El byte se arma con aritmética. El único salto condicional es el del sondeo. Así el tiempo no depende de los datos.
Dato: `sw/trade.s:109` a `:115`, `docs/decisiones.md:102`.

**43. [A] ¿Cómo arman el byte sin saltos?**
`0 - pos` da 0 o 0xFFFFFFFF; `andi` con -64 deja 0 o -64; sumar 0xBF da 0xBF (vender 63) o 0x7F (comprar 63). El esclavo SPI toma los 8 bits bajos.
Dato: `sw/trade.s:113` a `:115`.

**44. [B] ¿Qué hace el bloque `primero`?**
Con el primer precio deja `S = 32 p`, así `dev = 0` y no se opera. La media parte en el primer precio que el programa ve, cualquiera sea.
Dato: `sw/trade.s:77` a `:88`.

**45. [B] ¿Cómo muestran que `trade.s` decide exactamente igual que la referencia?**
`make equiv` compara el `decisiones.csv` del testbench con el de `ref/trader.py` con `cmp`, en los 20 000 ticks a los tres períodos, y el gemelo lo repite en 3810 series a los tres períodos. Cero diferencias.
Dato: `tools/equiv.sh:69`, `docs/puertas.md:35`.

**46. [B] ¿Cuáles son las mediciones por tick?**
Respuesta: IC 19,5 en promedio y 21 en el peor caso, 41 y 44 ciclos, CPI 2,10. Tick completo: IC 28,5 y 30, 63 y 66 ciclos. En la ronda 3, 44 de 2262 ciclos: 1,9 %.
Dato: `docs/mediciones/ticks_software.txt`, `docs/trade_s.md`, sección 6.

**47. [A] ¿Por qué hay peor caso si el programa no tiene saltos que dependan del precio?**
Lo que varía es en qué punto de la vuelta de sondeo (8 ciclos) llega el precio. El testbench tiene un período de 2500 ciclos, no múltiplo de 8, y recorre 4 fases: 38, 40, 42 y 44.
Dato: `docs/trade_s.md:191`.

**48. [A] ¿Por qué ustedes dicen 49 y el testbench 44?**
Barriendo las 8 fases, el primer precio pasa por `primero` (5 ciclos más) y llega a 49. El testbench cae en una fase favorable.
Dato: `docs/gemelo.md:134`, `docs/puertas.md:37`.

**49. [B] ¿Qué memoria usa el programa?**
40 palabras de programa y una sola palabra de datos, `TMP`, la última de la RAM, para el desplazamiento. El `.org 0x800` rellena el `.hex` a 512 palabras.
Dato: `sw/trade.s:69` y `:132`.

---

## 4. Espino base y cómo se mide

**50. [B] ¿Por qué el Espino base tiene CPI 2?**
Porque el banco de registros es BRAM con lectura registrada: cada instrucción espera un ciclo a sus operandos (`ops_valid_q`) y otro para ejecutar.
Dato: `rtl/espino_core/espino_id_stage.v:209` a `:213`.

**51. [B] ¿Por qué el load cuesta 3 y el salto tomado 3?**
El load espera además el dato de la memoria de datos, también registrada (`busy_o`). El salto tomado descarta la instrucción que ya se buscó detrás (`valid_d = ~pc_set_i`).
Dato: `rtl/espino_core/espino_load_store_unit.v:53`, `rtl/espino_core/espino_if_stage.v:50`.

**52. [B] ¿Cómo midieron el CPI?**
`tb/tb_cpi.sv` cuenta IC, ciclos, loads y saltos tomados, y comprueba `ciclos = 2 IC + loads + tomados` con diferencia 0 en todos los programas. Con el mix de la clase da 2,350.
Dato: `docs/mediciones/base.txt:51`, `docs/mediciones/espino_segmentado.txt:46`.

**53. [B] ¿Qué es la ley de hierro y qué factor ataca cada pieza?**
Tiempo = IC × CPI × Tclk. El segmentado y el barrel atacan el CPI; la extensión ataca el IC; el PLL atacaría Tclk, pero no existe en este encapsulado.
Dato: `docs/codiseno.md:48`.

**54. [B] ¿Por qué no habilitaron el shifter?**
El completo no cabe: 1491 celdas de 1280, nextpnr no lo puede ubicar.
Dato: `docs/mediciones/base.txt:27` y `:31`, `rtl/espino_core/espino_alu.v:72`.

**55. [I] ¿Por qué no subieron la frecuencia con el PLL?**
El VQ100 no tiene PLL: nextpnr falla con "PLL 'u_pll' couldn't be placed anywhere, no suitable BEL found". En un TQ144 hipotético R1 cerraría a 50 MHz, pero el patrimonio no cambiaría: el peor caso ya usa menos del 20 % del presupuesto.
Dato: `docs/mediciones/base.txt:35`, `docs/codiseno.md:311`.

**56. [A] ¿Y un duplicador de reloj por lógica?**
Se midió: el reloj doblado alterna períodos según el ciclo de trabajo del oscilador, y el segmentado cierra en 1 de 10 semillas en la esquina lenta; el base en ninguna. No es confiable.
Dato: `docs/codiseno.md:313`.

**57. [B] ¿Qué es `byte_done` y por qué importa?**
El pulso del esclavo SPI cuando llegó un precio completo (octavo flanco de subida de SCLK). El testbench oficial mide los ciclos de respuesta desde ahí hasta la escritura en `DECISION`.
Dato: `rtl/pochoco_spi_slave.v:74`, `tb/tb_proyecto_4.sv:93`.

**58. [A] ¿Por qué el byte que lee la maestra en el tick n responde al precio n-1?**
Escribir `DECISION` solo deja el byte en `tx_hold`; pasa al registro de desplazamiento cuando baja `CS_n` de la transacción siguiente.
Dato: `rtl/pochoco_spi_slave.v:81` a `:82` y `:113`.

**59. [A] ¿Para qué sirve el reset de encendido largo?**
Las BRAM del iCE40 no entregan datos válidos hasta un tiempo después de configurar la FPGA: con el reset original de 15 ciclos el core arrancaba leyendo ceros (medido en el Proyecto 2). Son 4095 ciclos, 164 us.
Dato: `rtl/pochoco_soc.v:114` a `:124`, `docs/decisiones.md:41`.

**60. [A] ¿Cambiaron el Espino base?**
No en su lógica: `make formal-base` prueba con los pases `equiv_*` de Yosys que sus etapas IF e ID son equivalentes a las del curso (1376 puntos).
Dato: `formal/base_sin_cambios/equiv.sh`, `docs/espino_segmentado.md:218`.

**61. [A] ¿Por qué el conteo de celdas de R0 aparece como 1083 en un lugar y 1091 en otro?**
Es el mismo RTL. El conteo tiene un ruido de unas 10 celdas entre síntesis según qué archivos lee Yosys; diferencias menores no se atribuyen a un cambio (decisión T6).
Dato: `docs/decisiones.md:64`, `docs/puertas.md:36`, `docs/mediciones/p7/variantes.txt:10`.

---

## 5. Espino segmentado

**62. [B] ¿Qué es el segmentado y compite?**
El Espino con pipeline de 3 etapas: CPI 1 en ALU, 2 en load y salto tomado. No compite; es una variante medida del punto 3.3 y la más rápida por hilo (22 ciclos de respuesta, 1,86 veces R0).
Dato: `docs/mediciones/p7/variantes.txt:20`.

**63. [A] ¿Cómo leen la instrucción a tiempo si la BRAM es registrada?**
La memoria de instrucciones lee en el flanco de bajada, desde una copia propia. Su salida está lista en la segunda mitad del ciclo y el banco lee con esas direcciones en el flanco de subida.
Dato: `rtl/pochoco_ram.v:69` a `:71`.

**64. [A] ¿Qué riesgo de datos aparece y cómo se resuelve?**
La instrucción i+1 lee el banco en el mismo flanco en que i escribe, y la BRAM entrega el valor viejo. Un adelantamiento de un nivel guarda el dato escrito y un bit de coincidencia por puerto.
Dato: `rtl/espino_core/espino_register_file.v:99` a `:113`.

**65. [A] ¿Por qué el salto tomado cuesta 2 y la clase estimó 3?**
La clase supone una etapa de fetch de un ciclo completo con dos instrucciones detrás del salto. Aquí IF e ID son medio ciclo cada una y solo se anula una.
Dato: `docs/mediciones/espino_segmentado.txt:52` a `:56`.

**66. [A] ¿Cuánto midieron contra lo que estimó la clase?**
CPI con el mix 1,350 contra 1,5; 18,52 MIPS contra 16,7; speedup 1,74 contra 1,57.
Dato: `docs/mediciones/espino_segmentado.txt:46` a `:49`.

**67. [A] ¿Qué riesgos tiene el pipeline en la placa?**
Las rutas de medio ciclo: nextpnr las analiza con un reloj de ciclo de trabajo de 50 %. Ninguna pasa de 9,8 ns de 20; tolera un ciclo de trabajo entre 25 y 75 %.
Dato: `docs/decisiones.md:261`, `docs/espino_segmentado.md:206`.

**68. [I] ¿Por qué la frecuencia del segmentado bajó de 51 a 45 MHz?**
Sin cambios en su core, al cambiar `pochoco_soc.v` en P2 y P5. Sigue cerrando 10 de 10 con holgura. Está anotado como no investigado.
Dato: `docs/mediciones/espino_segmentado.txt:15`, `docs/mediciones/p7/variantes.txt:11`.

**69. [B] ¿Cómo verificaron el segmentado?**
Formal del base sin cambios, ejecución en paralelo contra el base (1,6 millones de instrucciones por configuración, 39 % distintas), programas de riesgos del Proyecto 3, cosimulación con el gemelo y 5 de 5 mutaciones.
Dato: `docs/mediciones/paralelo_largo.txt:1`, `rtl/espino_core/espino_if_stage.v:45`.

---

## 6. Espino barrel

**70. [B] ¿Qué es un procesador barrel?**
Un core con varios hilos por hardware que reparte el pipeline por turnos fijos: un hilo por ciclo, sin prioridades. Aquí 4 hilos por un pipeline de 4 etapas.
Dato: `rtl/espino_core/espino_barrel_core.v:6` a `:8`.

**71. [B] ¿Cuál es su CPI?**
1,000 agregado y 4,000 por hilo, exactos, para cualquier mezcla de instrucciones.
Dato: `docs/mediciones/barrel/cpi.txt:15` y `:20`.

**72. [B] ¿Por qué no tiene riesgos de datos ni de control?**
Entre dos instrucciones del mismo hilo pasan 4 ciclos: cuando la siguiente lee el banco, la anterior ya escribió; cuando se busca, el salto anterior ya se resolvió. No hay adelantamiento, burbujas ni anulaciones.
Dato: `rtl/espino_core/espino_barrel_core.v:22` a `:25`.

**73. [A] ¿Cómo sabe el core de qué hilo es cada instrucción?**
Un contador de 2 bits dice qué hilo está en F; las otras etapas son ese valor menos 1, 2 y 3. El número de hilo no viaja con la instrucción.
Dato: `rtl/espino_core/espino_barrel_core.v:107` a `:110`.

**74. [A] ¿Dónde guardan los registros de cuatro hilos?**
En las mismas BRAM del banco, con dirección `{hilo, registro}` de 6 bits: 64 de 256 palabras. No cuesta ninguna BRAM adicional.
Dato: `rtl/espino_core/espino_barrel_regfile.v:55` a `:59`, `rtl/espino_core/espino_barrel_core.v:216` y `:225`.

**75. [A] ¿Puede un hilo leer o escribir un registro de otro?**
No: probado formalmente para cualquier programa (P1, P6, P10 y P11) y comparado en cada instrucción de la campaña.
Dato: `formal/barrel/propiedades.vh:53` y `:91`.

**76. [I] ¿Por qué un barrel si cada hilo responde más lento?**
Porque el diseño que compite corre cuatro reglas a la vez: cada hilo tiene CPI 4, pero el core completa una instrucción por ciclo. La latencia no cambia el patrimonio mientras la decisión llegue antes de la transacción siguiente, y R1 usa el 19,6 % de la ronda 3. Para una sola regla el segmentado es mejor, y está medido.
Dato: `docs/codiseno.md:353`, `docs/mediciones/p7/variantes.txt:41`.

**77. [A] ¿Por qué la latencia no da patrimonio?**
El byte que la maestra lee en el tick n se ejecuta al precio n, sea que el programa respondió en 22 ciclos o en 443. R0, el segmentado y el barrel dan con `max_media` los mismos 20 000 bytes.
Dato: `docs/codiseno.md:353`.

**78. [A] ¿Por qué el barrel es el core más chico?**
Cada BRAM (instrucciones, banco, datos) cae en una frontera entre etapas y su registro de salida es el registro de pipeline. Sin espera, sin adelantamiento y con contador de 11 bits.
Dato: `docs/espino_barrel.md`, sección 3.3; `docs/mediciones/p7/variantes.txt:12`.

**79. [A] ¿Cómo arrancan los hilos?**
El hilo t parte en la dirección 4 t: todo programa empieza con una tabla de cuatro saltos. En hardware son los valores de reset del anillo de contadores.
Dato: `sw/fondo.s:157` a `:160`, `rtl/espino_core/espino_barrel_core.v:400`.

**80. [A] ¿Qué pasa si un programa no tiene la tabla de arranque?**
Los hilos 1 a 3 parten en la segunda, tercera y cuarta instrucción. El testbench oficial da 2/4; en la placa la falla es silenciosa.
Dato: `docs/espino_barrel.md:116`.

**81. [A] ¿Qué pasa si dos hilos escriben la misma palabra?**
Las dos escrituras ocurren en ciclos distintos y en orden fijo: el hardware es determinista. Evitar la carrera es tarea del programa: una palabra, un escritor.
Dato: `docs/espino_barrel.md:118`.

**82. [B] ¿Cómo verificaron el barrel?**
Cada hilo contra un Espino base, instrucción por instrucción: 7,9 millones de instrucciones, 91,96 % distintas, cero diferencias; 21 de 21 mutaciones; 24 afirmaciones formales de estructura; testbench oficial 4/4.
Dato: `docs/puertas.md:54`.

**83. [A] ¿Encontraron errores en el barrel?**
En el core, ninguno. En el método, tres: programas que caían en un punto fijo, un `jalr` que sacaba a un hilo de su código y un hilo que terminaba ejecutando datos compartidos.
Dato: `docs/espino_barrel.md:276`.

---

## 7. Extensión de la ISA

**84. [B] ¿Qué instrucciones agregaron?**
`emad rd, rs1, rs2, 5`: `rd = rs2 + (rs1 >>> 5)`. `devk rd, rs1, rs2, 5`: `rd = (rs1 << 5) - rs2`. Y `mulstep`, que está construida pero no entra a R1.
Dato: `rtl/espino_core/espino_xd.v:12` a `:15`.

**85. [B] ¿Para qué sirven?**
`devk` calcula `dev = 32 p - S` en una instrucción (en `trade.s` son seis) y `emad` actualiza la media (en `trade.s` son ocho, con un paso por la memoria). El estimador pasa de 14 instrucciones a 2.
Dato: `sw/fondo.s:202` y `:209`.

**86. [B] ¿Por qué custom-0?**
Es uno de los opcodes que RISC-V reserva para extensiones propias: ninguna extensión estándar lo va a ocupar.
Dato: `rtl/espino_core/espino_xd.v:44`.

**87. [A] ¿Cómo están construidas?**
Un desplazamiento por una constante son cables. `espino_xd_dec` reconoce la palabra en la etapa R, `espino_xd_opa` entrega el operando A desplazado en X, y el resultado sale del sumador de la ALU como un `add`. Sin sumador nuevo ni estado.
Dato: `rtl/espino_core/espino_xd.v:92` y `:98`, `rtl/espino_core/espino_barrel_core.v:198`.

**88. [I] ¿Por qué k fijo en 5?**
Con un solo k el desplazamiento son cables. Con k de 0 a 31 hace falta un desplazador de unas 160 celdas, y la frecuencia mínima bajaba de 51,6 a 39,2 MHz en la factibilidad. El alfa de las cuatro reglas es 1/32.
Dato: `tools/asm/isa.py:91`, `docs/extension_isa.md`, sección 4.

**89. [A] ¿Qué pasa si alguien escribe `emad` con k = 4?**
El ensamblador lo rechaza. Si la palabra llega igual a la memoria, el core la trata como ilegal: no escribe, no accede al bus y no salta. Probado formalmente (X4) y con la mutación `MUTA_XD_K`.
Dato: `tools/asm/core.py:413`, `rtl/espino_core/espino_xd.v:56`.

**90. [A] ¿Por qué no un `ema` de una sola instrucción?**
Encadena resta, desplazamiento y suma: necesita un segundo sumador (60 a 167 celdas contra 37). Y el programa necesita la desviación de todas formas para decidir.
Dato: `docs/extension_isa.md`, sección 4.

**91. [A] ¿Cuánto cuestan?**
`emad` y `devk`: 52 celdas, 0 BRAM, frecuencia mínima 48,92 MHz. Las tres: 96 celdas. El costo es el multiplexor del operando A.
Dato: `docs/mediciones/xd/timing.txt`, `docs/decisiones.md:383`.

**92. [I] ¿Por qué `mulstep` está en el RTL si no se usa?**
Se construyeron y verificaron las tres antes de escribir `sw/fondo.s`. El fondo no lleva contabilidad, así que no la usa, y por la regla de Nicolás ("no quiero piezas sin uso en el chip que compite") R1 se compila sin ella.
Dato: `docs/decisiones.md:389`.

**93. [A] ¿Cómo verificaron una instrucción que el Espino base no tiene?**
Contra la fórmula, escrita tres veces por separado: en `ref/xd.py`, en el testbench de la campaña y en las propiedades formales. Formal: cada instrucción contra su especificación por inducción, y el resto del core equivalente al de P1 en 1890 puntos.
Dato: `formal/xd/propiedades_xd.vh:78`, `docs/decisiones.md:399`.

**94. [A] ¿Cuál es el error más fácil de cometer con una extensión en un barrel?**
Mirar la instrucción equivocada: mientras una está en X, lo que sale de la memoria es de otro hilo. `espino_xd_opa` usa el `funct3` registrado. Es la mutación `MUTA_XD_HILO`.
Dato: `rtl/espino_core/espino_barrel_core.v:50` a `:53`.

**95. [A] ¿Qué encontró la prueba formal de la extensión?**
Un error en la propiedad, no en el RTL: `rs2 + (rs1s >>> 5)` en una sola expresión se evalúa sin signo en Verilog. Lo delató una mutación que pasaba. Sin el control negativo se habría "arreglado" el RTL.
Dato: `docs/extension_isa.md`, sección 7.1.

**96. [B] ¿La extensión cambia el resultado de la competencia?**
No: las decisiones son las mismas bit a bit. Aporta ciclos libres y co-diseño medido: la respuesta de `max_media` en el barrel baja de 83 a 63 ciclos.
Dato: `docs/puertas.md:66`.

---

## 8. El fondo en un chip

**97. [B] ¿Qué hace cada hilo en `sw/fondo.s`?**
El hilo 0, supervisor, lee el precio, lo publica, calcula su propia `max_media`, recoge los votos, combina y escribe `DECISION`. Los hilos 1 a 3, gestores, corren la regla de reversión con umbrales de 3, 4 y 2 unidades y votan por memoria compartida.
Dato: `sw/fondo.s:165` y `:385`.

**98. [B] ¿Cómo combina los votos el supervisor?**
Suma los pesos (en dieciseisavos, iniciales 6/5/5) de los gestores que votan adentro; con 8/16 o más escribe comprar 63 y si no vender 63.
Dato: `sw/fondo.s:252` a `:266`.

**99. [A] ¿Cómo se ajustan los pesos?**
Cada 512 ticks se pasa 1/16 de peso del gestor que menos ganó en papel al que más ganó, si la ventaja supera 1/32 del precio, sin salir del tope y el piso de cada peso.
Dato: `sw/fondo.s:308`, `ref/fondo.py:212`.

**100. [A] ¿Cómo se publica el precio sin que un gestor vea un precio con el tick de otro?**
Precio y número de tick van en la misma palabra (`PUB = tick × 256 + precio`) y se escriben con un solo store, que es atómico.
Dato: `sw/fondo.s:197` a `:199`.

**101. [A] ¿Cómo sabe el supervisor que un voto es viejo, sin un bit de "listo"?**
El voto lleva el tick que el gestor procesó. El supervisor le resta su tick por 256: 0 o 1 si es fresco, 2 o más (sin signo) si es viejo. Un bit de listo habría que borrarlo, y serían dos hilos escribiendo la misma palabra.
Dato: `sw/fondo.s:217` y `:225`.

**102. [A] ¿Por qué no hay carreras?**
Cada palabra tiene un solo escritor, un store es atómico, y el barrel hace un acceso a memoria por ciclo en orden fijo. El gestor escribe el puntaje antes que el voto, y el supervisor lee el puntaje solo después de ver los tres votos frescos.
Dato: `sw/fondo.s:430` y `:434`, `docs/fondo.md:138`.

**103. [I] ¿Qué pasa si un hilo se cuelga?**
Si es un gestor: su voto queda viejo, el supervisor espera a lo más 8 vueltas y usa su propia `max_media` en ese lugar; la decisión sale siempre (30 de 30 corridas, peor caso 679 ciclos). Si es el supervisor, nadie escribe `DECISION`: en R1 la maestra repite el último byte; en R2 el vigilante reconfigura con R0 al quinto precio.
Dato: `sw/fondo.s:230` a `:241`, `rtl/vigilante.v:81`.

**104. [I] ¿Qué aportan los otros tres hilos si deciden igual que `max_media`?**
En la serie de práctica, nada en los bytes: escriben los mismos 20 000. Con pesos 6/5/5 la banda del medio define la mayoría; lo que los separa es el ajuste de pesos. En otras series difieren: 1816 bytes en una de reversión. Lo que aportan es co-diseño: 56 operaciones útiles por tick en vez de 8.
Dato: `docs/fondo.md:377` y `:336`.

**105. [A] ¿Por qué el supervisor calcula `max_media` si el gestor 1 ya la calcula?**
La del gestor 1 llega por memoria y puede no llegar. La del supervisor está en sus registros: es la única que no depende de otro hilo.
Dato: `sw/fondo.s:202` a `:209`.

**106. [A] ¿Cómo probaron la degradación?**
Con fallas puestas en el programa (un gestor en lazo infinito, un voto que nunca llega, un voto atrasado), no forzando señales: un gestor colgado de verdad sigue ocupando su turno. 30 corridas de 20 000 ticks sobre dos series.
Dato: `docs/decisiones.md:453`, `docs/mediciones/fondo/r1/degradacion.txt`.

**107. [A] ¿Por qué corren la degradación sobre dos series?**
En la práctica el fondo sano, el fondo con fallas y `max_media` escriben los mismos bytes: la prueba solo distinguiría por el estado interno. En una serie de reversión sí difieren.
Dato: `docs/fondo.md:336`.

**108. [B] ¿Cuánto demora el fondo en responder?**
223,01 ciclos en promedio (8,92 us), 443 en el peor caso del testbench y 444 barriendo fases: 19,6 % de la ronda 3. Con el plazo agotado, 568.
Dato: `docs/fondo.md:318`, `docs/mediciones/p7/variantes.txt:23`.

**109. [A] ¿Por qué el fondo responde más lento si usa cuatro hilos?**
Cada hilo avanza una instrucción cada 4 ciclos y el supervisor espera los votos. El barrel reparte el trabajo; no lo acelera para un hilo. Además el lazo de votos con plazo y la tabla cuestan ciclos.
Dato: `docs/fondo.md:302`.

**110. [A] ¿Mediciones por tick del fondo, por hilo?**
Supervisor: IC 68,59 en promedio y 116 como máximo, CPI 4. Cada gestor: 25 instrucciones siempre, CPI 4. Los cuatro: 143,59 instrucciones por tick, CPI agregado 1.
Dato: `docs/mediciones/fondo/r1/ticks.txt`, `docs/fondo.md`, sección 8.1.

**111. [A] ¿Cuántas vueltas da el lazo de votos?**
Con los gestores sanos, nunca más de 3 de las 8 del plazo, en 1 122 corridas sanas. El plazo no venció nunca.
Dato: `docs/fondo.md:322`.

**112. [A] ¿Por qué el puntaje está en treintaidosavos?**
`devk` entrega 32 p, y la diferencia de dos de esos valores ya es 32 veces el cambio de precio. Es el doble exacto del puntaje de la factibilidad y no cambia ninguna decisión.
Dato: `docs/decisiones.md:420`.

**113. [A] ¿Qué muestra la telemetría?**
Un store por tick, después de `DECISION`: en ticks pares los 7 segmentos muestran 63 o 00 (la posición objetivo), en impares los LED muestran el latido (bit 10 del tick) y los tres votos.
Dato: `sw/fondo.s:268` a `:297`, `docs/decisiones.md:441`.

**114. [A] ¿Hay algún borde no probado en el fondo?**
Sí: atrasos de un gestor entre 200 y 600 ciclos, donde el voto llega justo al vencer el plazo y la decisión depende del ciclo exacto; y la vuelta del contador de ticks (16,7 millones de ticks), donde un gestor que nunca votó contaría como afuera durante un tick.
Dato: `docs/fondo.md:105`, `docs/decisiones.md:453`.

---

## 9. Tabla, vigilante, warm boot e imagen múltiple

**115. [B] ¿Qué es la tabla de parámetros?**
Una BRAM de 256 valores de 16 bits en `0x8002_0000`, de solo lectura, con las 20 constantes de `sw/fondo.s`. No calcula ni decide.
Dato: `rtl/pochoco_tabla.v:6` a `:19`.

**116. [B] ¿Para qué sirve tenerla en una BRAM aparte?**
Para cambiar umbrales, pesos o plazo con `icebram` sin volver a sintetizar (una síntesis nueva ya no es el hardware probado), y para que el programa no pueda escribirla ni por error.
Dato: `docs/decisiones.md:459`.

**117. [A] ¿Qué error encontró la simulación del bitstream en la tabla?**
La primera versión llenaba la memoria con ceros en un lazo antes del `$readmemh`. Yosys se quedó con los ceros: la BRAM salía vacía en el bitstream, aunque el RTL funcionaba en simulación.
Dato: `rtl/pochoco_tabla.v:36` a `:41`.

**118. [A] ¿Qué es un molde y por qué hace falta?**
El mismo diseño sintetizado con las memorias llenas de un patrón al azar. `icebram` ubica una memoria por su contenido, y la tabla de verdad (236 ceros) no es distinguible. Se comprueba que el molde con `icebram` da el bitstream directo byte por byte.
Dato: `docs/tabla_vigilante.md:53`, `docs/decisiones.md:467`.

**119. [B] ¿Cuándo dispara el vigilante?**
Al quinto precio seguido sin escritura en `DECISION` (K = 4), y espera a que `CS_n` suba. Entonces activa `SB_WARMBOOT` con `S1 S0 = 01` y la FPGA carga la imagen 1, que es R0.
Dato: `rtl/vigilante.v:65` y `:81`, `rtl/pochoco_soc.v:295`.

**120. [A] ¿Por qué K = 4?**
En todas las corridas sanas de R2, incluida la matriz de estrés, la cuenta nunca pasó de 1. Cualquier K de 2 o más cumple; 4 da margen y gasta solo 5 ticks de los 536 del relevo.
Dato: `docs/tabla_vigilante.md:101`, `docs/decisiones.md:473`.

**121. [A] ¿Puede el vigilante disparar por una condición del algoritmo?**
No: solo cuenta precios y escrituras en `DECISION`. No mira precios, votos ni el plazo. Un gestor colgado no lo dispara porque el supervisor sigue decidiendo.
Dato: `rtl/vigilante.v:12` a `:16`.

**122. [I] ¿Cuánto cuesta un relevo?**
536 ticks sin decisión nueva a 0,1 ms (58 a 1 ms, 10 a 10 ms), con los 53 ms de reconfiguración de la hoja de datos, sin medir en la placa. Y probablemente la posición: R0 parte de cero y su primera decisión suele ser vender.
Dato: `docs/tabla_vigilante.md:132` y `:141`.

**123. [A] ¿Qué lee la maestra durante la reconfiguración?**
MISO queda con pull-up: lee `0xFF`, acción 11, que se trata como mantener. Después `0x00` mientras R0 está en su reset. Está en la simulación; el nivel real del pin se ve en la placa.
Dato: `docs/tabla_vigilante.md:126`.

**124. [A] ¿Por qué la imagen de respaldo no tiene vigilante?**
Para que no pueda haber un ciclo de reinicios, y porque es R0 tal cual, el mismo archivo que pasó su puerta.
Dato: `docs/decisiones.md:480`.

**125. [I] ¿Y si el ayudante no permite reconfigurar durante una ronda?**
R2 no compite y el titular es R1. El supervisor colgado queda sin defensa en vivo; entre rondas se graba R0.
Dato: `docs/arbol_decision.md:15` y `:16`.

---

## 10. Verificación

**126. [B] ¿Cuáles son los tres modelos y cómo se comparan?**
La referencia en Python (valores), el RTL (lo que se sintetiza) y el gemelo en C (ciclos). Referencia contra RTL por `decisiones.csv` byte a byte; gemelo contra RTL por trazas idénticas ciclo a ciclo.
Dato: `docs/defensa/verificacion.md`, sección 1.

**127. [B] ¿Qué es el gemelo digital?**
Un simulador del SoC completo en C, exacto al ciclo, que corre el mismo `.hex` del bitstream. Los 20 000 ticks a 10 ms toman 0,02 s, contra 22 minutos en Verilator.
Dato: `docs/gemelo.md:23`.

**128. [A] ¿Por qué confiar en el gemelo?**
Porque su traza es idéntica a la del RTL, evento por evento con su número de ciclo: 8 configuraciones del base y 21 del barrel (18,3 millones de eventos). Con `--borde 0` la traza difiere, como debe.
Dato: `docs/gemelo.md:105`.

**129. [A] ¿Qué encontró tener dos modelos escritos por separado?**
Que tres testbenches nunca cambiaban de período en las rondas seguidas: una variable declarada con valor inicial dentro de un `initial` es estática en SystemVerilog. El error estaba en los testbenches, no en el gemelo.
Dato: `docs/decisiones.md:507`, `docs/gemelo.md:224`.

**130. [B] ¿Qué es una mutación?**
Un error puesto a propósito, bajo `ifdef`, que la prueba tiene que detectar. Si no lo detecta, la prueba no sirve. Barrel 21/21, extensión 9/9, segmentado 5/5, fondo 15/15, vigilante 4/4.
Dato: `rtl/espino_core/espino_if_stage.v:45`, `docs/defensa/verificacion.md`, sección 7.

**131. [A] ¿Qué significa "instrucciones distintas" en el criterio 5?**
Una instrucción comparada cuenta si no hay otra en toda la campaña con el mismo hilo, contador de programa, instrucción, valor escrito, acceso al bus y palabra de memoria. Se hizo más exigente en vez de más fácil.
Dato: `docs/decisiones.md:374`.

**132. [I] ¿Por qué el 13/11 decían 1,3 millones de instrucciones comparadas y después corrigieron?**
Porque solo el 0,4 % eran distintas: el generador caía en un punto fijo. Se corrigió el generador y se repitió con la cobertura medida.
Dato: `docs/decisiones.md:342`.

**133. [B] ¿Por qué simulan el bitstream ruteado si ya simularon el RTL?**
Porque lo que se graba puede no ser lo que se simuló: la tabla de R1 salió en cero en el bitstream con el RTL funcionando. `make sim-bitstream` reconstruye el diseño desde el `.asc`.
Dato: `docs/decisiones.md:124`, `docs/tabla_vigilante.md:43`.

**134. [A] ¿Qué probaron formalmente?**
Que el base no cambió (equivalencia con Yosys), la estructura del barrel y el aislamiento de hilos (SymbiYosys), cada instrucción de la extensión contra su especificación, y el vigilante. No: el cálculo de cada instrucción RV32E en el barrel, ni riscv-formal.
Dato: `formal/barrel/propiedades.vh:53`, `formal/xd/propiedades_xd.vh:78`, `docs/decisiones.md:309`.

**135. [B] ¿Qué es la matriz de estrés?**
Una maestra configurable (`tb/tb_estres.sv`) que recorre SCLK de 100 kHz a 1 MHz, tiempos de `CS_n`, reset a mitad de una transacción, rondas seguidas sin reset y series pegadas en 1 y 255, comparando cada byte con la referencia. R0 60 de 60, R1 y R2 56 de 56.
Dato: `docs/decisiones.md:349`, `docs/puertas.md:85`.

**136. [A] ¿Qué es la autoprueba en placa?**
El SoC del peldaño con una maestra SPI dentro de la FPGA que manda 2000 precios de una caminata aleatoria a los tres períodos y muestra una firma CRC-16 de las decisiones. La firma esperada de R0 es `a23c`, igual en gemelo, referencia, RTL y bitstream.
Dato: `tools/autoprueba.py:61`, `docs/decisiones.md:532`.

**137. [I] ¿Qué no está probado?**
Nada se ha probado en la placa todavía. Falta la puerta de placa de los tres peldaños (la autoprueba de R0 está lista; la de R1 y R2 pendiente), el relevo de R2 en la placa, el tiempo real de reconfiguración, y la maestra real el 26/11.
Dato: `docs/puertas.md:43` y `:90`, `docs/autoprueba.md:126` y `:127`.

---

## 11. Co-diseño (punto 3.3)

**138. [B] ¿Qué parte del algoritmo consume más ciclos?**
En R0, actualizar la media (29 de 51 ciclos del kernel), por el desplazamiento con la memoria. En la respuesta, decidir. En el tick completo a 0,1 ms, esperar el precio: 98 %.
Dato: `docs/codiseno.md`, sección 14, pregunta 3.

**139. [B] ¿Qué cuenta como operación útil?**
Las 8 operaciones de la regla en su forma matemática: 4 para la media (32 p, la resta, el desplazamiento y la suma) y 4 para decidir. En el fondo, 56. `emad` y `devk` valen 2 cada una, como el MAC de la clase.
Dato: `docs/codiseno.md:97`, `docs/decisiones.md:544`.

**140. [B] ¿Qué alternativas de hardware construyeron y midieron?**
Segmentado, barrel en un hilo, barrel con `emad` y `devk`, R1 y R2. Base y segmentado con la extensión están predichos con Amdahl, porque construirlos toca el RTL de R0.
Dato: `docs/mediciones/p7/variantes.txt:9` a `:15`, `docs/decisiones.md:551`.

**141. [A] ¿Cómo aplicaron Amdahl y cuánto acertó?**
Por fase del tick, con el modelo de costo de cada variante. En el barrel y la extensión acierta al ciclo. En el segmentado predice 1,843 y se mide 1,864; con la estimación de la clase (salto tomado de 3) da 1,745.
Dato: `docs/codiseno.md:30`, `docs/decisiones.md:575`.

**142. [A] ¿Dónde queda el kernel en el roofline?**
Mueve 8 a 13 bytes por tick y hace 8 operaciones: 0,6 a 1 Op/B, a la derecha del quiebre de 0,125 Op/B. Está limitado por el cómputo, no por la memoria.
Dato: `docs/codiseno.md:31`.

**143. [B] ¿Cuál es el Ppeak de cada core?**
Base 12,5 MOPS (25 MHz × 0,5), segmentado 25, barrel 25 con cuatro hilos y 6,25 con uno.
Dato: `docs/mediciones/barrel/cpi.txt:37`, `docs/mediciones/espino_segmentado.txt:48`.

**144. [B] ¿Qué desempeño logra cada variante?**
R0 3,92 MOPS, segmentado 7,41, barrel un hilo 2,08, barrel con extensión 4,17, R1 5,34 (56 operaciones por tick).
Dato: `docs/mediciones/p7/variantes.txt:28` a `:33`.

**145. [I] La pregunta del enunciado: ¿eligieron la que más gana, la más rápida o la que mejor balancea?**
Ninguna de las tres en sentido estricto, y lo decimos: la más rápida por hilo es el segmentado, y en patrimonio empatan. Elegimos R1 por co-diseño (cuatro hilos, extensión usada, 56 operaciones útiles por tick, 80 % de holgura en la ronda 3) aceptando que no suma puntos (T50).
Dato: `docs/codiseno.md:346`.

**146. [A] ¿Dónde se va la energía en el ASIC?**
En esperar: decidir cuesta 2,6 nJ sobre 2,8 uJ por tick a 0,1 ms. Ningún peldaño de la escalera cambia eso; detener el reloj entre precios sí.
Dato: `docs/codiseno.md:343`.

---

## 12. Operación del día y contingencia

**147. [I] ¿Qué pasa si la maestra usa otro SCLK?**
Hasta 4 MHz todos los diseños responden igual. Hacia abajo, R1 responde a tiempo en la ronda 3 desde 110 kHz: con 100 kHz quedan 237 ciclos y necesita hasta 444. El árbol usa 115 kHz para dejar margen; bajo eso compite R0, que responde en 44 ciclos.
Dato: `docs/mediciones/fondo/r1/sclk_minimo.txt:51`, `docs/decisiones.md:613`.

**148. [A] ¿Cómo sabrán el SCLK real?**
Con el medidor del SPI: un bitstream aparte que escucha a la maestra y muestra en los 7 segmentos el período de SCLK, el período entre precios y los tiempos de `CS_n`. Se graba el 26/11 antes que los peldaños.
Dato: `rtl/medidor/medidor_spi.v:15`, `docs/decisiones.md:589`.

**149. [A] ¿Cuál es el período mínimo que soporta cada peldaño?**
Con SCLK de 1 MHz: R0 11,34 us (8,82 veces más rápido que la ronda 3), R1 26,94 us (3,71 veces).
Dato: `docs/mediciones/fondo/r1/sclk_minimo.txt:27` y `:52`.

**150. [A] ¿Qué pasa con rondas seguidas sin reset?**
Los tres peldaños pasan tres rondas seguidas con períodos distintos en la matriz de estrés. El programa no se reinicia: medias, puntajes y pesos siguen. Si la maestra reinicia su cuenta entre rondas es una pregunta al ayudante.
Dato: `docs/fondo.md:381`, `docs/checklist_1dic.md:63`.

**151. [A] ¿Qué pasa con rondas mucho más largas?**
La matriz de P8 corre una ronda de 200 000 ticks en el gemelo: pasan los tres peldaños.
Dato: `docs/contingencia.md`, sección 2.

**152. [B] ¿Qué se lleva grabado el 1/12?**
El peldaño que dé el árbol, el inmediatamente inferior como respaldo 1 y R0 como respaldo 2; los juegos de contingencia solo si anuncian otra comisión.
Dato: `docs/checklist_1dic.md:50`.

**153. [A] ¿Qué se prueba el 26/11 con la maestra?**
Medir el SPI con el medidor, después los peldaños del más seguro al más arriesgado, el relevo de R2 con la falla inyectada si se permite, y las preguntas al ayudante.
Dato: `docs/checklist_26nov.md:40`, `:64` y `:85`.

**154. [I] ¿Qué preguntas pendientes pueden cambiar todo?**
Si un Espino multihilo con custom-0 sigue siendo Espino (si no, R0), si se puede reconfigurar durante una ronda (si no, R1), y si las series ocultas salen del mismo generador.
Dato: `docs/checklist_26nov.md:95`.

**155. [A] ¿Cómo se sabe que un bitstream hecho con `icebram` es correcto?**
Por el control: con los parámetros de siempre, `icebram` sobre el molde da los bitstreams guardados byte por byte. Y cada juego nuevo se simula por los pines antes de guardarse (unos 40 minutos).
Dato: `docs/contingencia.md:82`, `docs/decisiones.md:595`.
