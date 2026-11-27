# Banco de preguntas de la defensa

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Preguntas que el profesor o un ayudante pueden hacer a cualquiera de los tres sobre el informe, el algoritmo, el assembly y el RTL. Cada respuesta está pensada para decirse en voz alta en unos 20 segundos, con el dato y el archivo que la respaldan.

- **[B]** básica: los tres tienen que poder responderla sin mirar nada.
- **[A]** avanzada: la responde con soltura el dueño de la pieza (`docs/defensa/plan_estudio.md`), y los otros dos al menos en una frase.
- **[I]** incómoda: pregunta que puede poner en duda una decisión. La respuesta dice lo que se aceptó a sabiendas.
- "Dato" apunta a un `archivo:línea` de la rama de entrega, o a una sección de un documento. Si una cifra de aquí no calza con su fuente, manda la fuente.

Los documentos de estudio que desarrollan cada sección son los de esta carpeta (`docs/defensa/*.md`), y las cifras de memoria están en `docs/defensa/cifras.md`.

---

## 1. El diseño que compite y por qué

**1. [B] ¿Qué compite el 1/12?**
Una escalera de tres bitstreams: R0 (Espino base con `max_media`), R1 (Espino barrel de 4 hilos con `emad`, `devk`, la tabla en BRAM y `sw/fondo.s`) y R2 (R1 con el vigilante y R0 como imagen de respaldo). Compite el peldaño más alto que pase las puertas de simulación, placa y maestra.
Dato: `docs/puertas.md:7` a `:11`, `docs/decisiones.md:326`.

**2. [B] ¿Cómo se elige el peldaño el día de la competencia?**
Con un árbol de una página: R0 si R1 falla con la maestra, si el SCLK de la ronda 3 es menor que 115 kHz o el período menor que 27 µs; R2 si pasó sus puertas y nadie prohibió reconfigurar durante una ronda; si no, R1. Que el barrel sea Espino ya no es una condición: lo confirmó el profesor el 16/11.
Dato: `docs/arbol_decision.md:11` a `:16`.

**3. [I] ¿Por qué compiten con un diseño que, según ustedes mismos, no suma puntos?**
Es la decisión T50, tomada a sabiendas: según la factibilidad el fondo suma +0,007 puntos esperados a 2 000 ticks y -0,005 a 20 000 contra `max_media` sola, y agrega riesgo en vivo. Se elige por lo que representa como co-diseño (procesador rediseñado, extensión usada realmente, cuatro reglas en paralelo, todo medido). El riesgo está acotado: R0 es el respaldo y el árbol dice cuándo usarlo.
Dato: `docs/decisiones.md:330`.

**4. [I] Entonces, ¿no habría sido más sensato competir con R0 o con el segmentado?**
En puntos esperados, empatan: la diferencia medida es de milésimas. La recomendación de la factibilidad era el segmentado con `emad` y `max_media`; se descartó a favor de T50. Lo que se perdió está escrito: días de trabajo y margen para reaccionar a una falla de placa.
Dato: `docs/decisiones.md:331` y `:332`.

**5. [B] ¿Qué es `max_media`?**
La regla base de reversión a la media con el umbral de entrada en 3 unidades bajo la media en vez de 4. En el código cambia una constante: `UMBRAL_COMPRA` pasa de -128 a -96.
Dato: `sw/trade.s:64`, `docs/decisiones.md:335`.

**6. [B] ¿Qué está probado y qué no?**
R0, R1 y R2 pasaron los ocho criterios de la puerta de simulación. La puerta de placa está incompleta: el 16/11, en la placa, R2 pasó la firma a 0,1 ms y la media hora sin disparo, y el relevo se midió en 35,50 ms por la UART; R0 mostró a los tres períodos la mitad baja de su firma ("3C") y le falta la mitad alta ("A2"); faltan además las tres firmas de R1, la de R2 a 1 ms y 10 ms y ver la imagen testigo después del relevo (`docs/mediciones/placa_16nov.md`). Falta la puerta de la maestra real del miércoles 25/11, por confirmar.
Dato: `docs/puertas.md`, secciones de R0, R1 y R2 y "Puerta de placa"; `docs/mediciones/placa_16nov.md`.

**7. [B] ¿Qué es la puerta de simulación?**
Ocho criterios: testbench oficial 4/4, equivalencia con la referencia, timing en 10 semillas, peor caso barriendo fases bajo la mitad del presupuesto, core contra el base, degradación, estrés y simulación del bitstream ruteado.
Dato: `docs/puertas.md:17` a `:24`.

**8. [A] ¿Qué compila el comando del encabezado del testbench oficial?**
Sin definiciones compila R0. Si compite R1 o R2, `make peldano-fijar` agrega `rtl/00_peldano.v` con las definiciones (va primero en orden alfabético) y `sw/trade.s` pasa a ser `sw/fondo.s`. Está preparado y se ejecuta después del miércoles 25/11, por confirmar.
Dato: `docs/peldano.md`, sección "Cómo se hace".

**9. [I] ¿Un Espino de cuatro hilos con instrucciones propias sigue siendo Espino?**
Sí. El profesor Jorge Gómez nos confirmó en persona el 16/11 que se puede modificar lo que uno quiera y que cualquier decisión de diseño es válida; le describimos el Espino multihilo y dijo que estaba perfecto. Además, técnicamente: misma ISA RV32E, mismo decodificador, ALU, LSU y bus, sin modificar; cambia la microarquitectura, y la extensión usa custom-0, que RISC-V reserva para esto.
Dato: `docs/decisiones.md`, T126; `docs/arbol_decision.md:11`; `docs/espino_barrel.md`, sección 9.

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

**14. [A] ¿Cuánta reversión hay realmente?**
Menos de la que parece: un paseo aleatorio redondeado a enteros da VR(100) = 0,77. La mitad de la caída es redondeo y no se puede explotar porque la orden se ejecuta un tick después. Lo real es una transitoria con vida media de 17,5 ticks.
Dato: `docs/algoritmo.md:71`.

**15. [A] ¿Qué modelo ajustaron?**
Precio = redondeo(nivel + transitoria): nivel como paseo aleatorio, transitoria AR(1) con phi = 0,961, dos regímenes de volatilidad y saltos poco frecuentes. Máxima verosimilitud con filtro de Kalman y Nelder-Mead.
Dato: `ref/generador.py:187`, `docs/algoritmo.md:44`.

**16. [B] ¿Cómo decide la cantidad?**
No la decide: siempre 63. La maestra recorta la compra a lo que alcanza con la caja y la venta a lo que se tiene, y una orden que queda en cero no paga comisión. El programa expresa una posición objetivo: todo comprado o todo en caja.
Dato: `tb/tb_proyecto_4.sv:73` y `:78`, `docs/trade_s.md:27`.

**17. [B] ¿Por qué no lleva contabilidad?**
Porque "comprar 63" y "vender 63" son idempotentes: repetirlos con la caja gastada o sin acciones no hace nada. Y una contabilidad propia podría desincronizarse de la oficial.
Dato: `docs/trade_s.md:27`.

**18. [I] ¿Por qué la tabla del punto 3.1 muestra menos con `max_media` (25 973) que con la regla base (27 062)?**
Porque el 27 062 está sesgado: los parámetros de la regla base se eligieron mirando esa misma serie. Fuera de muestra `max_media` gana 0,7 % en remuestreos y 1,4 % en familias plausibles, con 7 y 10 errores estándar. En los bloques de práctica queda 26 abajo con un error de 238: no se distinguen.
Dato: `docs/mediciones/tabla_3_1.txt:6` y `:7`, `docs/decisiones.md:339`.

**19. [A] ¿Por qué alfa 1/32?**
Con alfa más grande la media sigue al precio y no queda desviación que operar; con una menor mejora el modelo y empeora el remuestreo. 1/32 es el mejor compromiso, y además en la extensión el desplazamiento fijo (k = 5) se implementa solo con cableado.
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
Respuesta: IC 19,5 en promedio y 21 en el peor caso, 41 y 44 ciclos, CPI 2,10. Tick completo: IC 28,5 y 30, 63 y 66 ciclos. En la ronda 3, 44 de los 2262 ciclos del presupuesto: 1,95 % (1,76 % del período completo de 2500 ciclos).
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
Las BRAM del iCE40 no entregan datos válidos hasta un tiempo después de configurar la FPGA: con el reset original de 15 ciclos el core arrancaba leyendo ceros (medido en el Proyecto 2). Son 4095 ciclos, 164 µs.
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
No cambió el diseño, cambió la síntesis. La equivalencia formal entre el SoC de P1 y el actual pasa; desde el commit `c293cf4`, que agregó la tabla y el vigilante detrás de definiciones que el segmentado no usa, Yosys entrega otra netlist equivalente que nextpnr rutea peor. Con el mismo RTL leído en otro orden la mediana va de 47,88 a 53,59 MHz. Por eso no atribuimos al diseño diferencias de pocos MHz, y en 40 semillas cierra 40 de 40 a 25 MHz.
Dato: `docs/mediciones/p7/caida_segmentado.txt`, secciones 3 y 4; `docs/decisiones.md`, T127.

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

**78. [A] ¿Por qué el barrel es el core más pequeño?**
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
Un desplazamiento por una constante se implementa solo con cableado. `espino_xd_dec` reconoce la palabra en la etapa R, `espino_xd_opa` entrega el operando A desplazado en X, y el resultado sale del sumador de la ALU como un `add`. Sin sumador nuevo ni estado.
Dato: `rtl/espino_core/espino_xd.v:92` y `:98`, `rtl/espino_core/espino_barrel_core.v:198`.

**88. [I] ¿Por qué k fijo en 5?**
Con un solo k el desplazamiento se implementa solo con cableado. Con k de 0 a 31 hace falta un desplazador de unas 160 celdas, y la frecuencia mínima bajaba de 51,6 a 39,2 MHz en la factibilidad. El alfa de las cuatro reglas es 1/32.
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
Se construyeron y verificaron las tres antes de escribir `sw/fondo.s`. El fondo no lleva contabilidad, así que no la usa, y por decisión del grupo (ninguna pieza sin uso en el chip que compite, T58) R1 se compila sin ella.
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
Suma los pesos (en dieciseisavos, iniciales 6/5/5) de los gestores que votan comprar; con 8/16 o más escribe comprar 63 y si no vender 63.
Dato: `sw/fondo.s:252` a `:266`.

**99. [A] ¿Cómo se ajustan los pesos?**
Cada 512 ticks se pasa 1/16 de peso del gestor que menos ganó en su puntaje simulado al que más ganó, si la ventaja supera 1/32 del precio, sin salir del tope y el piso de cada peso.
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

**104. [I] ¿Qué aportan los otros tres hilos si deciden casi igual que `max_media`?**
En la serie de práctica, poco o nada en los bytes: en el testbench a 0,1 ms escribe los mismos 20 000 bytes que `max_media` (los dos terminan con 26 070); a 1 ms y 10 ms no: el fondo termina con 25 031 y `max_media` con 26 070 (`docs/mediciones/fondo/r1/equiv.txt`, `docs/mediciones/p7/gemelo.txt`). Viendo todos los precios, `ref/fondo.py` da 26 388 y `ref/trader.py` 25 973. Con pesos 6/5/5 la banda del medio define la mayoría; lo que los separa es el ajuste de pesos. En otras series difieren: 1816 bytes en una de reversión. Lo que aportan es co-diseño: 56 operaciones útiles por tick en vez de 8.
Dato: `docs/fondo.md:377` y `:336`, `docs/mediciones/fondo/r1/equiv.txt`.

**105. [A] ¿Por qué el supervisor calcula `max_media` si el gestor 1 ya la calcula?**
La del gestor 1 llega por memoria y puede no llegar. La del supervisor está en sus registros: es la única que no depende de otro hilo.
Dato: `sw/fondo.s:202` a `:209`.

**106. [A] ¿Cómo probaron la degradación?**
Con fallas puestas en el programa (un gestor en lazo infinito, un voto que nunca llega, un voto atrasado), no forzando señales: un gestor realmente colgado sigue ocupando su turno. 30 corridas de 20 000 ticks sobre dos series.
Dato: `docs/decisiones.md:453`, `docs/mediciones/fondo/r1/degradacion.txt`.

**107. [A] ¿Por qué corren la degradación sobre dos series?**
Las pruebas de degradación corren a 0,1 ms, y ahí, en la práctica, el fondo sano, el fondo con fallas y `max_media` escriben los mismos bytes (`docs/mediciones/fondo/r1/degradacion.txt`): la prueba solo distinguiría por el estado interno. En una serie de reversión sí difieren.
Dato: `docs/fondo.md:336`.

**108. [B] ¿Cuánto demora el fondo en responder?**
223,01 ciclos en promedio (8,92 µs), 443 en el peor caso del testbench y 444 barriendo fases: 19,6 % de la ronda 3. Con el plazo agotado, 568.
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
Sí: atrasos de un gestor entre 200 y 600 ciclos, donde el voto llega justo al vencer el plazo y la decisión depende del ciclo exacto; y la vuelta del contador de ticks (16,7 millones de ticks), donde un gestor que nunca votó contaría como en caja durante un tick.
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
El mismo diseño sintetizado con las memorias llenas de un patrón al azar. `icebram` ubica una memoria por su contenido, y la tabla definitiva (236 ceros) no es distinguible. Se comprueba que el molde con `icebram` da el bitstream directo byte por byte.
Dato: `docs/tabla_vigilante.md:53`, `docs/decisiones.md:467`.

**119. [B] ¿Cuándo dispara el vigilante?**
Al quinto precio seguido sin escritura en `DECISION` (K = 4), y espera a que `CS_n` suba. Entonces activa `SB_WARMBOOT` con `S1 S0 = 01` y la FPGA carga la imagen 1, que es R0.
Dato: `rtl/vigilante.v:65` y `:81`, `rtl/pochoco_soc.v:295`.

**120. [A] ¿Por qué K = 4?**
En todas las corridas sanas de R2, incluida la matriz de estrés, la cuenta nunca pasó de 1. Cualquier K de 2 o más cumple; 4 da margen y gasta solo 5 ticks de los 361 del relevo (con el tiempo medido en la placa).
Dato: `docs/tabla_vigilante.md:101`, `docs/decisiones.md:473`.

**121. [A] ¿Puede el vigilante disparar por una condición del algoritmo?**
No: solo cuenta precios y escrituras en `DECISION`. No mira precios, votos ni el plazo. Un gestor colgado no lo dispara porque el supervisor sigue decidiendo.
Dato: `rtl/vigilante.v:12` a `:16`.

**122. [I] ¿Cuánto cuesta un relevo?**
361 ticks sin decisión nueva a 0,1 ms (40 a 1 ms, 8 a 10 ms), con los 35,50 ms de reconfiguración medidos en la placa el 16/11; con los 53 ms de la hoja de datos eran 536. Y probablemente la posición: R0 parte de cero y su primera decisión suele ser vender.
Dato: `docs/tabla_vigilante.md:132` y `:144`.

**123. [A] ¿Qué lee la maestra durante la reconfiguración?**
MISO queda con pull-up: lee `0xFF`, acción 11, que se trata como mantener. Después `0x00` mientras R0 está en su reset. Está en la simulación; el nivel real del pin se ve en la placa.
Dato: `docs/tabla_vigilante.md:126`.

**124. [A] ¿Por qué la imagen de respaldo no tiene vigilante?**
Para que no pueda haber un ciclo de reinicios, y porque es R0 tal cual, el mismo archivo que pasó su puerta.
Dato: `docs/decisiones.md:480`.

**125. [I] ¿Está permitido reconfigurar la FPGA durante una ronda?**
No lo preguntamos en particular. El profesor nos dijo el 16/11 que cualquier decisión de diseño es válida, y lo tomamos como cubierto por esa respuesta general, sin confirmación específica; está escrito así en T126. Si el ayudante lo prohibiera de forma explícita, R2 no compite y el titular es R1: el supervisor colgado queda sin defensa en vivo y entre rondas se graba R0.
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
El SoC del peldaño con una maestra SPI dentro de la FPGA que manda 2000 precios de un paseo aleatorio a los tres períodos y muestra una firma CRC-16 de las decisiones. La firma esperada de R0 es `a23c`, igual en gemelo, referencia, RTL y bitstream.
Dato: `tools/autoprueba.py:61`, `docs/decisiones.md:532`.

**137. [I] ¿Qué no está probado?**
La puerta de placa está incompleta. El 16/11, en la placa, R2 pasó la firma a 0,1 ms y la media hora sin disparo, y el relevo se midió en 35,50 ms por la UART; R0 mostró a los tres períodos la mitad baja de su firma ("3C") y le falta la mitad alta ("A2"); faltan además las tres firmas de R1, la de R2 a 1 ms y 10 ms y ver la imagen testigo después del relevo (`docs/mediciones/placa_16nov.md`). El tiempo de reconfiguración tiene una sola medición de tres pedidas. Falta la maestra real el miércoles 25/11, por confirmar.
Dato: `docs/puertas.md`, sección "Puerta de placa"; `docs/mediciones/placa_16nov.md`.

---

## 11. Co-diseño (punto 3.3)

**138. [B] ¿Qué parte del algoritmo consume más ciclos?**
En el kernel de R0 (de leer `PRICE` a volver al sondeo, 51 ciclos), la fase más larga es actualizar la media, `S = S + (dev >>> 5)`: 17 ciclos (33,3 %), por el desplazamiento hecho con `sw` y `lbu`. Con la desviación a la media (12 ciclos), el estimador completo suma 29 de 51 ciclos (56,9 %), que es la fracción que usa Amdahl. En la respuesta, la fase más larga es decidir y armar el byte (14 de 41 ciclos). En el tick completo a 0,1 ms, esperar el precio: 98 %.
Dato: `docs/mediciones/p7/perfil.txt`; `docs/codiseno.md`, sección 14, pregunta 3.

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
En esperar: decidir cuesta 2,6 nJ sobre 2,8 µJ por tick a 0,1 ms. Ningún peldaño de la escalera cambia eso; detener el reloj entre precios sí.
Dato: `docs/codiseno.md:343`.

---

## 12. Operación del día y contingencia

**147. [I] ¿Qué pasa si la maestra usa otro SCLK?**
Hasta 4 MHz todos los diseños responden igual. Hacia abajo, R1 responde a tiempo en la ronda 3 desde 110 kHz: con 100 kHz quedan 237 ciclos y necesita hasta 444. El árbol usa 115 kHz para dejar margen; bajo eso compite R0, que responde en 44 ciclos.
Dato: `docs/mediciones/fondo/r1/sclk_minimo.txt:51`, `docs/decisiones.md:613`.

**148. [A] ¿Cómo sabrán el SCLK real?**
Con el medidor del SPI: un bitstream aparte que escucha a la maestra y muestra en los 7 segmentos el período de SCLK, el período entre precios y los tiempos de `CS_n`. Se graba el miércoles 25/11, por confirmar antes que los peldaños.
Dato: `rtl/medidor/medidor_spi.v:15`, `docs/decisiones.md:589`.

**149. [A] ¿Cuál es el período mínimo que soporta cada peldaño?**
Con SCLK de 1 MHz: R0 11,34 µs (8,82 veces más rápido que la ronda 3), R1 26,94 µs (3,71 veces).
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

**153. [A] ¿Qué se prueba el miércoles 25/11, por confirmar con la maestra?**
Medir el SPI con el medidor, después los peldaños del más seguro al más arriesgado, el relevo de R2 con la falla inyectada si se permite, y las preguntas al ayudante.
Dato: `docs/checklist_26nov.md:40`, `:64` y `:85`.

**154. [I] ¿Qué preguntas pendientes pueden cambiar todo?**
Ya ninguna sobre el diseño: el profesor confirmó el 16/11 que el Espino multihilo es válido, y la reconfiguración durante una ronda quedó cubierta por esa respuesta general, sin confirmación específica (T126). Quedan las de la competencia: qué SCLK y cuántos precios usa la maestra, si las series ocultas salen del mismo generador y cómo se calcula el puntaje.
Dato: `docs/decisiones.md`, T126; `docs/checklist_26nov.md:98` a `:109`.

**155. [A] ¿Cómo se sabe que un bitstream hecho con `icebram` es correcto?**
Por el control: con los parámetros de siempre, `icebram` sobre el molde da los bitstreams guardados byte por byte. Y cada juego nuevo se simula por los pines antes de guardarse (unos 40 minutos).
Dato: `docs/contingencia.md:82`, `docs/decisiones.md:595`.

## 13. La regla de Vicente

**156. [I] ¿Por qué no usaron la regla que da 40 957 en la práctica?**
Porque 40 957 es el resultado en la misma serie con que se eligieron sus parámetros, compuesto sobre 20 000 ticks: en los 10 bloques de 2000 la ventaja sobre `max_media` es +346 +- 321 por bloque, un error, y su vecino a 2,75 desviaciones da 22 421 en la misma serie. Con el criterio que fijamos antes de medir (remuestreos de trozos de 100 ticks y el modelo calibrado, con una semilla reservada) pierde 0,09 puntos por ronda. Lo que no ocultamos: con trozos de 250 ticks o más, y eligiendo los parámetros en una mitad de la práctica para probarlos en la otra, `zscore` gana; en series del modelo, no. Depende de si la serie oculta se parece a la práctica en escalas de cientos de ticks, y eso no se sabe. La decisión y su razón están en `docs/decisiones.md` (T129 y siguientes).
Dato: `docs/zscore.md:101` (largo del trozo), `:131` (las dos lecturas) y `:142` (la grilla en la práctica); `docs/mediciones/zscore/trozos.txt`, `reservada_s4.txt`.

## 14. R3: C1 en los cuatro hilos

Se agregó el 21/11. Las preguntas salen de `docs/defensa/c1.md` (documento de estudio de la pieza) y de `docs/puertas.md`, sección "R3". Los números de línea son los de `sw/c1.s` del bitstream congelado.

**157. [B] ¿Qué es R3 y en qué se diferencia de R2?**
Es el cuarto peldaño de la escalera. Mismo hardware que R2 (barrel con `emad` y `devk`, vigilante) más una tabla de 512 palabras en vez de 256, y otro programa: `sw/c1.s` en lugar de `sw/fondo.s`. La imagen de respaldo sigue siendo R0 con la banda 40. Cuesta 1038 celdas y 14 bloques de memoria contra 1015 y 13 de R2.
Dato: `docs/puertas.md`, sección "R3" (tabla de recursos); `rtl/pochoco_tabla512.v`.

**158. [B] ¿Qué agrega C1 a la banda 40?**
Tres piezas. Una apuesta de media posición en la fase A (antes de ver los dos extremos), un motor que decide con una política calculada por programación dinámica, y un candado que copia a la banda 40 cuando la ventaja sobre un clon de la banda 40 llega a 100. Es un desempate: la banda 40 más intentos de quedar un poco arriba, y volver a copiarla cuando se logra.
Dato: `docs/defensa/c1.md`, secciones 1 y 2.

**159. [I] ¿Por qué complicar la banda 40 si C1 no sube la nota?**
No la sube: en la exploración la nota esperada con C1 fue entre 0,003 y 0,006 menor que con la banda 40 sola. Lo que cambia es con qué frecuencia se gana un mano a mano: 81,8 % de los torneos contra 45,7 %, porque rompe los empates que la banda 40 deja contra rivales que corren lo mismo. Se paga con más derrotas (nd baja de 90,4 a 83,3). Se aceptó a sabiendas, como en la pregunta 3.
Dato: `docs/defensa/c1.md`, secciones 1 y 8.1.

**160. [B] ¿Qué hace cada hilo de `sw/c1.s`?**
El hilo 0 lee el precio, calcula la banda 40, espera la política con plazo y escribe `DECISION` una vez por tick: es el único que toca el SPI. El hilo 1 mide la volatilidad y el reloj de los tramos. El hilo 2 lee la celda de la tabla y la compara con el precio. El hilo 3 ejecuta las órdenes propia y del clon, calcula la ventaja D, lleva los modos y arma el byte de la política.
Dato: `sw/c1.s:87` a `:179` (hilo 0), `:191` a `:314` (1), `:322` a `:382` (2), `:390` a `:529` (3).

**161. [A] ¿Cómo se pasan los datos entre hilos y cómo se detecta un dato viejo?**
Por memoria compartida, con una sola escritora por palabra (`D_PUB`, `D_REG`, `D_TAB`, `D_POL`, `D_ORD`). Todo lo publicado lleva el número de tick en los bits 31:8, y quien espera relee hasta ver el tick actual. Una escritura de palabra es atómica, así que no hacen falta candados. El testbench vigila las dos reglas en todas las corridas y no hubo violaciones.
Dato: `docs/defensa/c1.md`, sección 3; `sw/c1.s:668` en adelante (palabras compartidas).

**162. [A] ¿Cómo es la máquina de modos?**
Tres modos sin vuelta atrás: fase A, motor (desde el primer extremo, el 100 o el 255) y candado (cuando D llega a 100). Si la apuesta de la fase A ya ganó 100 al llegar al primer extremo, pasa directo al candado. En el candado el byte de la política es el que publicó el hilo 0 con la banda 40.
Dato: `sw/c1.s:430` a `:447`, `docs/defensa/c1.md`, sección 4.

**163. [A] ¿Cómo saben cuánto tiene el rival?**
No lo saben. El hilo 3 lleva dos cuentas con la contabilidad oficial (caja 10 000, comisión 5): la propia, con el byte que realmente escribió el hilo 0, y la de un clon que opera la banda 40 pura. D es el patrimonio propio menos el del clon, y el candado se decide con ese D. Si el rival real hace otra cosa, el candado se decide igual contra el clon.
Dato: `sw/c1.s:390` a `:447`, `docs/defensa/c1.md`, sección 4.

**164. [I] ¿Qué pasa si la comisión no es 5 o la caja inicial no es 10 000?**
Las dos cuentas quedan mal y el candado puede cerrar donde no debe: es la dependencia más delicada de C1. La banda 40 no la tiene. Por eso el miércoles 25/11, por confirmar se compara la cuenta emulada, que se lee en los 7 segmentos, con la pantalla de la maestra, y la regla de Nicolás dice que si no calza compite la banda 40.
Dato: `docs/c1_dia_de_prueba.md`, secciones 3 y 4.

**165. [A] ¿Cómo ejecutan una orden si no hay multiplicador ni desplazador completo?**
Con los múltiplos p, 2p, 4p, 8p, 16p y 32p (cinco sumas por tick). Se resta del saldo de mayor a menor mientras quede cantidad y alcance, y lo que queda es la caja nueva. No hace falta dividir. El producto de D (acciones por precio) se hace duplicando y sumando sobre los 8 bits del precio.
Dato: `sw/c1.s:541` (`ejecutar`) y `:620` (`producto`).

**166. [A] ¿Cómo dividen para la media posición?**
Es la única división del programa: el objetivo floor(patrimonio / 2p) se calcula con 9 pasos de resta y comparación, una vez al entrar. El hilo 3 la adelanta en cada tick de la fase A sin posición, antes de esperar al hilo 2, porque si no, al coincidir con un tick lento del hilo 1 el byte llegaba pasado el plazo y se usaba el respaldo (se vio en 3 de 40 ventanas).
Dato: `sw/c1.s:449` a `:472`, `docs/bitacora/c1.md` (tiempos, vuelta 3).

**167. [A] ¿Qué es la clase de volatilidad y para qué tiene histéresis?**
Es S2 / t, la suma de diferencias al cuadrado sobre los ticks transcurridos, clasificada en ocho valores (de 1/8 a 2) para elegir la fila de la tabla. Se calcula sin dividir: se compara 64 S2 contra siete sumas que crecen una constante por tick. La histéresis de 64 ticks evita que la clase salte entre dos valores vecinos. Se usa desde el tick 390.
Dato: `sw/c1.s:257`, `docs/defensa/c1.md`, secciones 5 y 6.

**168. [I] ¿Guardan precios o series dentro de la tabla? ¿Eso cumple la regla del enunciado?**
No hay ningún precio de ninguna serie. Los umbrales los calcula un script (`ref/c1/tablas.py`) desde un modelo matemático: paseo aleatorio condicionado a mínimo 100 y máximo 255 en 20 000 ticks. Entran la varianza, el largo, los extremos y el costo de la comisión. `make c1-generar` los recalcula desde cero y comprueba que son los de la placa. La memoria es de solo lectura y no decide: decide el procesador.
Dato: `docs/defensa/c1.md`, sección 6; `ref/c1/paseo.py`, `ref/c1/tablas.py`.

**169. [A] ¿De dónde salen los umbrales?**
Para cada tiempo restante y precio se calcula por recurrencia hacia atrás la probabilidad de que el 255 llegue antes que el 100. Con programación dinámica se saca la política que maximiza el patrimonio esperado en logaritmo pagando comisión, y se comprime a un umbral por celda: 8 clases por 16 tramos de 1250 ticks en la fase A, y 3 fases por 8 clases por 8 tramos de 2500 en el motor. Son 320 celdas de 2 bytes, 640 bytes. Recalculadas desde cero dieron 0 celdas distintas de las de la exploración.
Dato: `docs/defensa/c1.md`, sección 6; `docs/bitacora/c1.md` (Tablas).

**170. [B] ¿La tabla decide? ¿Cómo se apaga la política?**
No decide: es una memoria de solo lectura y el procesador compara y decide. Con la palabra `POLITICA` de la tabla en 0 el hilo 0 parte en modo seguro y decide la banda 40 exacta. Con la política apagada R3 dio los mismos bytes que R2 en 46 corridas por el RTL y en 203 series del gemelo.
Dato: `sw/c1.s:94` y `:95`, `docs/puertas.md`, sección "R3", puerta a.

**171. [A] ¿Qué pasa si se cuelga el hilo 1, 2 o 3?**
El hilo 0 espera la política con un plazo de 28 vueltas. Pasado el plazo, si el byte es del tick anterior sostiene la orden si era completa (comprar 63 o vender 63) y mantiene si era parcial. Si es más viejo, entra a modo seguro: banda 40 sin política hasta el final de la ronda, con LED1 encendido. Se probó en 26 casos con la decisión siempre a tiempo, el peor en 907 ciclos de 1131.
Dato: `sw/c1.s:151` a `:173`, `docs/mediciones/c1/degradacion.txt`.

**172. [A] ¿Y si se cuelga el hilo 0?**
Deja de escribir `DECISION` y el vigilante de R2 cuenta cinco precios sin respuesta. Entonces la placa se reconfigura con R0 y la banda 40, y MISO queda con pull-up (0xFF, mantener) durante la reconfiguración, unos 35,50 ms medidos. Se comprobó dentro del bitstream de R3: con el hilo 0 colgado en el tick 100, BOOT pide la imagen 01 al terminar la transacción 105.
Dato: `docs/puertas.md`, criterio 8 de la puerta c de R3; `docs/c1_dia_de_prueba.md`, sección 7.

**173. [I] ¿Por qué el candado es para siempre? ¿No pierden ganancias?**
Copiando al clon las dos cuentas hacen las mismas órdenes y D casi no cambia (solo por lo que alcanza a comprar cada una). Volver a arriesgar la ventaja es lo que la exploración midió que no conviene. El costo está en el otro lado: en las rondas en que el 100 llega antes que el 255, el motor cierra el candado en la mitad y en la otra mitad queda unos 316 pesos abajo.
Dato: `docs/defensa/c1.md`, secciones 4 y 8.1.

**174. [I] ¿Cuánto del resultado de C1 es suerte?**
La medida se fijó antes de mirar y se corrió una sola vez en 3600 ventanas de cinco empresas. g subió 36,1 puntos con error estándar de 2,4, así que no es ruido. nd bajó 7,1 con error estándar de 2,5 y el criterio era a lo más 8: se cumple por 0,9 puntos, menos que su error estándar, y hay que decirlo así. La nota esperada no cambia. Lo que no mide: el pronóstico de rivales es un supuesto.
Dato: `docs/defensa/c1.md`, sección 8.1.

**175. [I] ¿Las constantes 0,95 y 100 no son sobreajuste?**
Son los dos parámetros que se eligieron mirando datos, y se eligieron con otras 100 acciones, no con las cinco empresas del examen ni con las series de práctica. Son parámetros como el 140 y el 215 de la banda. El tick 390 sale del diseño de la exploración (los minutos de un día de mercado) y las tablas salen del modelo, sin datos. Con eso no se descarta del todo el riesgo: la serie oculta puede no parecerse.
Dato: `docs/defensa/c1.md`, sección 6.

**176. [A] ¿Por qué cuatro hilos y no uno?**
En un solo hilo del barrel el trabajo de los cuatro iría en serie: 369 instrucciones por tick en promedio sin contar esperas, a 4 ciclos cada una, unos 1477 ciclos en promedio. La ronda 3 da 2262 y la puerta pide la mitad (1131). Es una estimación: ese programa no se escribió y su peor caso no se midió, así que no se afirma que no quepa, sino que en promedio pasaría el límite de la puerta. Con cuatro hilos las dos cuentas, la volatilidad y la tabla avanzan en paralelo: la respuesta promedio es de 529,9 ciclos y el peor tick queda en 807. Las 470 instrucciones en promedio y 700 en el peor tick que se citaban antes cuentan las vueltas en que un hilo espera a otro, y no son trabajo que un solo hilo tendría que hacer.
Dato: `docs/defensa/c1.md`, sección 10, pregunta 9; `docs/mediciones/c1/ops_roofline.txt`; `docs/puertas.md`, tabla de recursos de R3.

**177. [I] ¿No están muy justos? Memoria al 94 % y el plazo en 81 % del límite.**
Sí, y está dicho. El programa ocupa 482 de 512 palabras (quedan 30) y con un hilo colgado responde en 916 ciclos de 1131, el margen más chico del diseño. El sano responde en 779 a 807. Hay recortes de reserva documentados y no aplicados, porque cada cambio de `sw/c1.s` obliga a repetir todas las puertas. El período mínimo que soporta con holgura sube a unos 50 µs (R2: 13,5 µs).
Dato: `docs/c1_plan.md`, sección 10; `docs/puertas.md`, tabla de recursos de R3.

**178. [A] ¿Qué pasa con rondas seguidas sin reiniciar la placa?**
C1 supone una ronda de 20 000 ticks contada desde el reset: el reloj de tramos, el modo (el candado no tiene vuelta) y las dos cuentas parten de cero solo ahí. Pasado el tick 20 000 R3 entra a modo seguro y decide la banda 40; no falla, pero ya no es C1. Por eso entre rondas se desconecta y se conecta el USB (decisión de Nicolás del 21/11).
Dato: `sw/c1.s:94` (carga de `D_N_RONDA`) y `:672`; `docs/c1_dia_de_prueba.md`, sección 2.

**179. [A] ¿Cómo saben que el programa hace lo que midieron en Python?**
Por capas. La referencia entera da los mismos bytes que el C1 de la exploración en 2400 ventanas (48 millones de bytes). El programa da los mismos bytes y el mismo estado que la referencia en 4,14 millones de ticks por el RTL y en 12,18 millones en el gemelo a los tres períodos. Además: 4/4 en el testbench oficial, 27 mutaciones detectadas en el core, 26 de 26 de degradación, 25 de 25 controles negativos y el bitstream ruteado simulado por los pines.
Dato: `docs/puertas.md`, sección "R3"; `docs/bitacora/c1.md`.

**180. [A] ¿Qué prueba la autoprueba de R3 en la placa y qué no?**
Un bitstream aparte con el mismo SoC y el mismo programa más una maestra interna que manda 2000 precios y acumula una firma de las decisiones. La esperada es `984c` ("4C" en los 7 segmentos y "98" con SW4); si la placa decidiera la banda 40 daría `a639`. No ejercita la apuesta de la fase A (la caminata se mueve en todos los ticks y la tabla nunca apuesta) ni los cables con la maestra externa. Costó 1208 celdas.
Dato: `docs/c1_dia_de_prueba.md`, sección 9; `tools/autoprueba.py`.

**181. [A] ¿Qué muestra la telemetría de R3 y cuál es su límite?**
Los 7 segmentos muestran un byte de las cuentas emuladas, elegido con los cuatro botones: patrimonio, modo, caja, acciones y caja del clon. Sirve para comparar con la pantalla de la maestra. El límite: el programa lee los botones y escribe el display una vez por tick, así que al terminar la ronda queda congelado en el byte que elegían los botones en el último precio. Sin tocar nada se ve el byte bajo del patrimonio. Nicolás decidió dejarlo así para no tocar el bitstream congelado.
Dato: `sw/c1.s:519` a `:529`, `docs/c1_dia_de_prueba.md`, sección 3; `docs/bitacora/c1.md`, cuarta parte.

**182. [I] ¿R3 usa hardware que no pasó por la maestra real? ¿Quién decide si compite?**
Sí: la tabla de 512 palabras es hardware nuevo y no estuvo el 18/11. Solo compite si pasa la prueba del miércoles 25/11, por confirmar y la decisión es de Nicolás. Si la caja o el patrimonio no calzan con la pantalla, o algo falla, compite la banda 40 (R2 o R0). Por eso R3 queda sobre los otros peldaños en la escalera y no en lugar de ellos: R0, R1 y R2 siguen intactos y con sus bitstreams.
Dato: `docs/c1_dia_de_prueba.md`, encabezado y sección 2; `docs/defensa/c1.md`, sección 9.

**183. [I] ¿Qué pasa si el rival corre exactamente la banda 40, o algo distinto?**
Contra un clon exacto de la banda 40, C1 queda debajo en 16,6 % de los torneos: es el costo de arriesgar una apuesta que el rival no hace. Contra otros rivales el candado igual se decide con el clon y no con el rival real, así que la ventaja D es una estimación. El examen sorteó rivales (extremos puros, la regla de Fila 5 y bandas de 30 a 60) y ese pronóstico de quién es el rival es un supuesto que no se puede verificar antes de la competencia.
Dato: `docs/defensa/c1.md`, sección 8.1.

## 15. Por qué compiten con la variante más lenta

Se agregó el 21/11. Son dos versiones de la misma pregunta incómoda, una para R2 y otra para R3. Las cifras de ciclos son de la serie Meta a 0,1 ms; el presupuesto es el que calcula el testbench oficial (`(PERIODO_NS - SPI_NS) / 40`), no el período completo de 2500 ciclos.

**184. [I] ¿Por qué compiten con la variante más lenta? (R2)**
Es cierto y está medido. R2 responde en 123 ciclos de promedio y 127 de peor caso, contra 56,5 y 60 de R0; en trabajo útil por segundo logra 1,64 MOPS contra 5,50, y pasar del base a un hilo del barrel tiene un Amdahl de 0,521 (los 50 ciclos del kernel pasan a 96). No cuesta patrimonio: el byte que lee la maestra en el tick n se ejecuta al precio n, lo respondan en 60 o en 127 ciclos, y 127 son el 5,6 % de los 2262 ciclos de presupuesto de la ronda 3. Lo que se compra con esa lentitud es una tabla en BRAM que se cambia con `icebram` en 0,32 s sin sintetizar ni ensamblar, y un vigilante que reconfigura a R0 si el hilo 0 deja de escribir `DECISION` (relevo de 35,50 ms medidos, 361 ticks a 0,1 ms). Lo que se acepta: los hilos 1 a 3 solo esperan, así que R2 decide la misma regla que R0 y no suma puntos, y un relevo cuesta decisiones. Ver también 3 y 76.
Dato: `docs/mediciones/p7/cotas/variantes.txt:6` y `:9`, `docs/mediciones/p7/cotas/roofline.csv:2` y `:5`, `docs/mediciones/p7/cotas/amdahl.txt:61`, `docs/mediciones/fondo/r2/ticks.txt:14` y `:25` a `:29`, `tb/tb_proyecto_4.sv:133`, `docs/tabla_vigilante.md:17`, `:67` y `:136`, `docs/mediciones/placa_16nov.md:16`.

**185. [I] ¿Por qué compiten con la variante más lenta? (R3)**
R3 es todavía más lenta que R2. Responde en 529,86 ciclos de promedio (132,72 instrucciones) y 783 de peor caso (196 instrucciones), contra 56,5 y 60 de R0: unas 9,4 veces más ciclos de promedio. El peor caso sano usa el 34,6 % de los 2262 ciclos de presupuesto y el tick completo llega a 807. Con un hilo colgado el peor tick medido es de 916 ciclos, el 81 % de los 1131 que pide la puerta (la mitad del presupuesto): es el margen más chico del diseño. La latencia no da patrimonio mientras la decisión llegue antes de la transacción siguiente. Lo que se compra: los cuatro hilos hacen en paralelo las dos cuentas, la volatilidad y la tabla de 512 palabras, que en un solo hilo darían unos 1477 ciclos en promedio, sobre los 1131 de la puerta (pregunta 176), y con eso C1, cuyo examen sube g 36,1 puntos (error estándar 2,4) y baja nd 7,1 (error estándar 2,5). Lo que no está medido: el Amdahl y el roofline de R3 quedan para después del miércoles 25/11, por confirmar, así que no hay MOPS de R3 en el informe. Si algo falla con la maestra compite la banda 40. Ver también 159, 177 y 182.
Dato: `docs/mediciones/c1/perfil_hilos.txt:8` y `:10`, `docs/mediciones/p7/cotas/variantes.txt:6`, `docs/c1_plan.md:159` y `:160`, `docs/defensa/c1.md:161` y `:162`, `docs/decisiones.md:847`.
