# Auditoría de hardware: diseño integrado y fondo de cuatro hilos

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz. Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Estudio de factibilidad. Esta carpeta revisa dos piezas que ya tenían su README y sus mediciones: `factibilidad/i_integrado/` (extensión de la ISA, vigilante y memoria de la tabla sobre el barrel, y las configuraciones I1 a I4) y `factibilidad/b_fondo_hilos/` (el fondo mínimo en assembly con cuatro hilos). El objetivo no fue repetir sus pruebas sino intentar refutarlas: medir de nuevo con listas de fuentes propias, poner errores que sus autores no eligieron, buscar carreras con tiempos al azar y contrastar cada frase de los resúmenes con una medición.

Nada de esta carpeta está integrado en `rtl/`, en el `Makefile` de la raíz ni en la integración continua. Todos los números salen de un script de esta carpeta y su salida está en `mediciones/`.

## 1. Resultado en una página

| Qué se revisó | Resultado | Salida |
|---------------|-----------|--------|
| Celdas, BRAM y fmax de I1, I2 e I3 | **Se reproducen exactas.** Con las semillas 1 a 10 dan las mismas cifras del README, celda por celda y centésima por centésima. Con 20 semillas cierran 20 de 20. `icetime`, un segundo analizador, da mínimas entre 45,3 y 50,9 MHz | `mediciones/recursos.txt` |
| I1 con el programa del fondo en la memoria | Mismas 1071 celdas, 13 BRAM y 46,76 MHz de mínima que con la regla base. El programa no cambia la síntesis | `mediciones/recursos.txt` |
| Testbench oficial sin modificar | 4/4 en I1, I2 e I3 con decisiones idénticas a las del Espino base. 4/4 con el fondo en el barrel y **con el fondo en el hardware I1**, que ninguna de las dos piezas había corrido junto: decisiones idénticas a la referencia en C y el vigilante no dispara | `mediciones/oficial.txt` |
| Equivalencia del fondo contra su referencia en C | 34 casos, 646 000 ticks, 645 934 filas de estado por 13 campos, cero diferencias. Incluye las 14 familias sintéticas con dos semillas que la pieza no usó y 4 casos sobre el hardware I1 | `mediciones/equiv.txt` |
| Repetición de los objetivos de las dos piezas | 10 objetivos vueltos a correr (6 del fondo y 4 del diseño integrado): salidas idénticas a las guardadas, sin contar el commit ni los tiempos. Los tres objetivos largos del diseño integrado se habían repetido al cerrar la pieza, también idénticos | `mediciones/repeticion.txt` |
| Mutaciones nuevas (18) | 17 detectadas por las pruebas de las piezas, pero **solo después de corregir un testbench y de agregar una variante**. Antes, dos errores de conexión de la primitiva `SB_WARMBOOT` y un supervisor que no espera al gestor 2 pasaban sin que ninguna prueba de las piezas los notara. La que queda no cambia el comportamiento | `mediciones/mutaciones.txt` |
| Carreras entre hilos | **No se encontró ninguna.** 19 corridas con retardos y fase de llegada al azar, 337 174 decisiones vigiladas con 9 monitores, cero violaciones, y el estado interno igual al modelo en todas, también cuando el fondo pierde precios por ir atrasado. En ninguna decisión el supervisor había cargado un `EST_k` de otro tick | `mediciones/carreras.txt` |
| Un gestor colgado | El supervisor se queda esperando y deja de escribir `DECISION`. En I1 el vigilante dispara con el precio T + N. El README de `i_integrado` decía lo contrario. Con un fondo que pierde el 42 % de los precios por ir atrasado, el vigilante no dispara, pero queda a un precio de hacerlo | `mediciones/cuelgue.txt` |
| Archivos fuera de `factibilidad/` | Ninguno con cambios. El testbench oficial es byte a byte el entregado | `mediciones/integridad.txt` |
| Reglas del enunciado para el fondo en un chip | El hilo 0 lee los 19 998 precios y escribe las 19 998 decisiones con `lw` y `sw`. En 20 000 ticks el programa solo cambia 17 palabras de memoria. Seis módulos agregados no tienen un testbench que los instancie solos | `mediciones/reglas.txt` |

Lo que se refutó y se corrigió:

1. **El testbench del vigilante sobre el barrel no probaba la conexión de la primitiva.** `tb/tb_vig_barrel.sv` de `i_integrado` miraba `dut.g_vig.boot` y `dut.g_vig.sel`, que son los cables que salen del módulo `vigilante`. Con la entrada BOOT de `SB_WARMBOOT` puesta en 0, o con S1 y S0 cruzados, la prueba pasaba igual. En la placa el primero significa que el respaldo no entra nunca y el segundo que la FPGA carga una imagen que no existe. El RTL estaba bien conectado: lo que fallaba era la prueba. Se corrigió el testbench para que mire las entradas de la primitiva y se repitieron `make tabla-vigilante` y `make mutaciones` de la pieza.
2. **El README de `i_integrado` decía que un hilo de estrategia colgado no dispara el vigilante** porque "el supervisor seguiría respondiendo con datos viejos". Con el programa real del fondo pasa lo contrario, y está medido (sección 7). Se corrigieron las secciones 6 y 12 de ese README.
3. **El README de `b_fondo_hilos` tenía seis marcas sin reemplazar** (`@@EQUIV_RESUMEN@@` y otras) en el resumen, en la tabla de equivalencia y en el veredicto. Los números estaban medidos y guardados. Se completó el texto. Su `AVANCE.md` decía que faltaban tres mediciones que ya estaban hechas.
4. **La holgura de I1 frente al calendario estaba contada en el mejor caso.** El texto decía que I1 "llega al 25/11 con 3 días de holgura". La cuenta es correcta solo con las tres personas dedicadas a eso y sin ningún tropiezo en la placa. Se reescribió el párrafo con sus supuestos (sección 10).
5. **Ninguna prueba de la pieza del fondo ejercitaba la espera del gestor 2.** Sin retardos el supervisor solo espera de verdad al gestor 1: en 20 000 ticks encontró `EST_1` atrasado 159 982 veces y `EST_2` y `EST_3` ninguna. La pieza tenía una variante con el gestor 3 atrasado (`atraso_800`) y ninguna con el gestor 2. Un supervisor que no comprueba el número de tick de `EST_2` pasaba sin una diferencia la equivalencia nominal (20 000 ticks, decisiones y estado, que es lo que comparan `make equiv` y `make estado`) y la variante `atraso_800`. Se agregó la variante `atraso_800_g2` a `make variantes` de la pieza: el programa sano la pasa (4/4, decisiones y estado idénticos) y la mutación se detecta desde la fila 58 (sección 5).
6. **El monitor M5 de esta misma auditoría veía solo una parte de las lecturas viejas.** Miraba la memoria en el ciclo en que se escribe `DECISION`, 16 instrucciones después de la carga de `EST_3`. Con el supervisor que no espera al gestor 3, marcaba 24 decisiones. El monitor M9, que mira la carga, marca 224: en las otras 200 el gestor publicó entre la carga y la escritura. La frase "M2, M5 y M6 juntos dicen que el supervisor no decide con datos de dos ticks" decía más de lo que esos monitores podían ver. Con M9 la búsqueda se repitió y el resultado es el mismo: ninguna violación en el programa sin mutar (sección 6.2).

Lo que se matizó, sin ser un error:

7. **La equivalencia nominal del fondo no puede ver un supervisor que no espera al gestor 2 o al gestor 3.** Con los gestores de tiempo constante, los dos publican antes de que el supervisor llegue a leerlos, así que esas mutaciones pasan los 20 000 ticks con decisiones y estado idénticos. Las detectan las variantes `atraso_800` y `atraso_800_g2` de la pieza y la prueba de carreras de esta carpeta. El argumento "la decisión no depende de los ciclos" se sostiene, pero se apoya en `make variantes` y no en `make equiv`.
8. **El orden "primero `DES_k`, después `EST_k`" no se puede poner a prueba en este programa.** Invertirlo no cambia ninguna decisión ni ningún peso, porque el supervisor tarda al menos tres instrucciones entre leer `EST_k` y leer `DES_k`, y el gestor escribe la segunda una instrucción después de la primera. El orden importaría si el gestor hiciera trabajo entre los dos stores.

Las conclusiones de las dos piezas quedan como estaban: las cuatro configuraciones de hardware caben y cierran, y el fondo de cuatro hilos es factible como programa pero no pasa el criterio de corte de algoritmo.

## 2. Qué hay en esta carpeta

| Archivo | Qué es |
|---------|--------|
| `tools/comun.sh` | Listas de fuentes y definiciones de cada configuración, escritas archivo por archivo. La auditoría no usa las listas de los scripts que revisa |
| `tools/recursos.sh`, `tools/leer_pnr.py` | Síntesis y place and route de I1, I2 e I3 con 20 semillas, lectura directa de los logs de nextpnr e `icetime` |
| `tools/oficial.sh` | Testbench oficial sin modificar, seis corridas con Icarus |
| `tools/equiv.sh` | El fondo contra su referencia con series nuevas, en el barrel y en I1 |
| `tools/mutar_aud.py`, `tools/mutaciones.sh` | 12 mutaciones de RTL y 6 del protocolo, contra las pruebas de las piezas |
| `tb/tb_carreras.sv` | Testbench propio: llegada del precio con fase al azar, interruptores al azar, nueve monitores del protocolo, cuenta de las esperas del supervisor, serie de precios vistos y estado por tick |
| `tools/prog_carreras.py` | Variantes de `sw/fondo.s` para la auditoría: retardos que dependen de los interruptores, mutaciones del protocolo y un gestor colgado. No modifica el original |
| `tools/carreras.sh`, `tools/comparar_vistos.py` | Búsqueda de carreras y comparación con la referencia corrida sobre los precios que el supervisor vio |
| `tools/cuelgue.sh` | Un gestor colgado, en el barrel y en I1, y un fondo atrasado en I1 |
| `tools/integridad.sh` | `git status` y `git diff`, solo lectura |
| `tools/reglas.sh` | Reglas del enunciado para el hardware I1 con el programa del fondo |
| `tools/repeticion.sh` | Vuelve a correr los objetivos de las dos piezas y compara con sus salidas guardadas |
| `mediciones/` | La salida de cada script |
| `AVANCE.md` | Bitácora de trabajo |

No se copió ni se modificó ningún fuente fuera de esta carpeta y de las dos piezas auditadas. De las piezas se usan en su lugar los testbenches (`tb_xd_barrel.sv`, `tb_vig_barrel.sv`, `tb_fondo.sv`), el generador `gen_prog_hilos.py`, `simbolos.py`, `variante.py` y `comparar_estado.py`: son justamente lo que se quería poner a prueba. Las mutaciones se hacen sobre copias dentro de `build/`.

Lo que sí cambió en las piezas auditadas, que desde este tramo se mantienen junto con esta carpeta:

| Archivo | Cambio |
|---------|--------|
| `factibilidad/i_integrado/tb/tb_vig_barrel.sv` | Mira BOOT, S1 y S0 en las entradas de la primitiva `SB_WARMBOOT` |
| `factibilidad/i_integrado/README.md` | Secciones 5, 6, 10, 12 y 13 corregidas, y sección 16 nueva |
| `factibilidad/i_integrado/mediciones/tabla_vigilante.txt` y `mutaciones.txt` | Vueltos a generar con el testbench corregido |
| `factibilidad/b_fondo_hilos/README.md` | Marcas sin reemplazar completadas, variante `atraso_800_g2` en las secciones 1, 4.3, 4.4 y 6.3, y sección 15 nueva |
| `factibilidad/b_fondo_hilos/tools/variantes.sh` | Variante `atraso_800_g2` (el gestor 2 atrasado 800 ciclos). Ahora son diez corridas |
| `factibilidad/b_fondo_hilos/mediciones/` | `variantes.txt` vuelto a generar con la corrida nueva: las otras nueve dan lo mismo que antes. `tamano.txt`, `ticks.txt`, `estado.txt` y `oficial.txt` vueltos a generar por `make repeticion`, sin cambios de contenido |
| `AVANCE.md` de las dos piezas | Puestos al día |

## 3. Cómo se reproduce cada número

Desde la raíz del repositorio. Hace falta OSS CAD Suite en el `PATH` y gcc. Cada script usa a lo más 5 procesos.

| Comando | Qué mide | Salida | Tiempo |
|---------|----------|--------|--------|
| `make -C factibilidad/auditoria_hw recursos` | Celdas, BRAM y fmax de I1a, I1b, I2, I3a, I3b e I1 con el fondo, 20 semillas | `mediciones/recursos.txt` | 2 min |
| `make -C factibilidad/auditoria_hw oficial` | Testbench oficial sin modificar, 6 corridas | `mediciones/oficial.txt` | 4 min |
| `make -C factibilidad/auditoria_hw equiv` | El fondo contra su referencia, 34 casos | `mediciones/equiv.txt` | 4 min |
| `make -C factibilidad/auditoria_hw mutaciones` | 18 mutaciones | `mediciones/mutaciones.txt` | 6 min |
| `make -C factibilidad/auditoria_hw carreras` | 19 corridas con tiempos al azar | `mediciones/carreras.txt` | 2 min |
| `make -C factibilidad/auditoria_hw cuelgue` | Un gestor colgado y un fondo atrasado, con y sin vigilante | `mediciones/cuelgue.txt` | 1 min |
| `make -C factibilidad/auditoria_hw integridad` | Estado del repositorio | `mediciones/integridad.txt` | 5 s |
| `make -C factibilidad/auditoria_hw reglas` | Reglas del enunciado | `mediciones/reglas.txt` | 40 s |
| `make -C factibilidad/auditoria_hw todo` | Todo lo anterior | | 17 min (estimado: 15 medidos antes de agregar una mutación y una prueba) |
| `make -C factibilidad/auditoria_hw repeticion` | Repite los objetivos de las dos piezas y compara | `mediciones/repeticion.txt` | 8 min (unos 27 con `LARGOS=1`, estimado) |

Los logs de nextpnr quedan en `build/variantes/fact2_auditoria_hw_*` de la raíz.

## 4. Cifras repetidas

### 4.1 Recursos y timing

`mediciones/recursos.txt`. Mismo flujo del repositorio (`tools/medir_variante.sh`: `synth_ice40` y `nextpnr-ice40 --hx1k --package vq100 --freq 25`), con las listas de fuentes y las definiciones de `tools/comun.sh` de esta carpeta, que se escribieron leyendo la tabla del README y no los scripts de la pieza.

| Configuración | Celdas | Libres | BRAM | Fmax mínima, mediana y máxima, semillas 1 a 10 (MHz) | Informado en el README | Semillas 11 a 20: mínima | Cierran de 20 | `icetime`, mínima de 20 |
|---------------|--------|--------|------|-------------------------------------------------------|------------------------|--------------------------|---------------|-------------------------|
| I1, tabla de 256 x 16 | 1071 | 209 | 13 | 46,76, 48,62 y 50,48 | lo mismo | 46,95 | 20 | 46,44 |
| I1 con 16 BRAM | 1098 | 182 | 16 | 44,94, 48,07 y 51,83 | lo mismo | 44,68 | 20 | 45,29 |
| I2 | 939 | 341 | 12 | 50,95, 53,59 y 56,09 | lo mismo | 52,24 | 20 | 50,92 |
| I3, `emad` | 1046 | 234 | 12 | 48,02, 52,36 y 53,25 | lo mismo | 48,43 | 20 | 48,58 |
| I3, tres instrucciones | 1142 | 138 | 12 | 46,59, 48,05 y 49,14 | lo mismo | 45,17 | 20 | 45,28 |
| I1 con `sw/fondo.s` en la memoria | 1071 | 209 | 13 | 46,76, 48,62 y 50,48 | no estaba medido | 46,95 | 20 | 46,44 |

Lectura:

- **Las quince cifras de fmax y las diez de recursos coinciden con el README.** nextpnr es determinista con la misma semilla, así que una coincidencia exacta dice que la auditoría sintetizó el mismo circuito a partir de la descripción del README. Ese era el punto: que la tabla describe lo que se midió.
- **Las semillas 11 a 20 no se habían usado para nada.** Cierran todas. La peor es 44,68 MHz en I1 con 16 BRAM, 0,26 MHz bajo la peor de las diez primeras. "10 de 10" no era suerte de las semillas.
- **`icetime` coincide con nextpnr** dentro de 2 MHz en todas las semillas. En I3 `icetime` no entiende las rutas de medio ciclo del segmentado (`docs/espino_segmentado.md`), así que ahí vale solo como referencia.
- **El programa no cambia la síntesis.** I1 con el fondo en la memoria da las mismas celdas y las mismas 20 frecuencias que con la regla base. La configuración "fondo en un chip" completa cabe y cierra.
- **Los bitstreams salen bit a bit iguales.** El `.asc` de la semilla 1 de esta medición, empaquetado con `icepack`, tiene el mismo sha256 que informa la pieza para `i1a.bin`, `i1b.bin`, `i2.bin`, `i3a.bin` e `i3b.bin` (32 220 bytes cada uno). La pieza decía que el sha256 se reproduce y no lo había comprobado nadie fuera de sus scripts. No se repitieron los dos de I4 ni la simulación desde el `.asc`.

### 4.2 Testbench oficial

`mediciones/oficial.txt`. `tb/tb_proyecto_4.sv` sin tocar (sha256 `f83486755fe2b3de...`), con el comando de su encabezado y Icarus Verilog. 2000 ticks a 0,1 ms.

| Corrida | 4/4 | Decisiones | Peor caso (ciclos) | Patrimonio | Vigilante |
|---------|-----|------------|--------------------|------------|-----------|
| Espino base de `rtl/` | sí | referencia | 44 | 9617 | |
| I1 con la regla base en el hilo 0 | sí | idénticas al base | 83 | 9617 | cuenta 1, BOOT 0 |
| I2 con la regla base en el hilo 0 | sí | idénticas al base | 83 | 9617 | cuenta 1, BOOT 0 |
| I3 con `sw/trade.hex` | sí | idénticas al base | 26 | 9617 | cuenta 1, BOOT 0 |
| El fondo en el barrel prototipo | sí | idénticas a `fondo_min` en C | 439 | 9661 | |
| El fondo en el hardware I1 | sí | idénticas a `fondo_min` en C | 439 | 9661 | cuenta 1, BOOT 0 |

La última fila es la configuración que le da nombre al tramo, y no estaba corrida: `i_integrado` midió su hardware con la regla base, y `b_fondo_hilos` corrió su programa sobre el barrel sin extensión ni vigilante. Juntos funcionan igual: mismos 439 ciclos, mismas 74 órdenes, y el vigilante cuenta a lo más un precio sin respuesta.

### 4.3 Equivalencia del fondo

`mediciones/equiv.txt`. Con el testbench de la pieza (`tb/tb_fondo.sv`), que deja además el estado interno. En cada caso se exige 4/4, `decisiones.csv` idéntico al de `fondo_min` en C y los 13 campos del estado iguales en todos los ticks.

| Grupo | Casos | Ticks | Resultado |
|-------|-------|-------|-----------|
| Serie de práctica en el barrel, a 0,1 ms y a 1 ms | 2 | 23 000 | idénticos |
| 14 familias sintéticas, semillas 2 y 3, en el barrel | 28 | 560 000 | idénticos |
| Serie de práctica en el hardware I1, a 0,1 ms y a 1 ms | 2 | 23 000 | idénticos |
| `volatil` semilla 2 y `modelo` semilla 3 en el hardware I1 | 2 | 40 000 | idénticos |
| **Total** | **34** | **646 000** | **645 934 filas de estado, cero diferencias** |

La pieza había usado la semilla 1 y ocho familias. Las 28 series nuevas incluyen las siete familias que no había probado (`modelo_vecino`, `dos_componentes`, `cambio_volatilidad`, `paseo`, `reversion`, `nivel_bajo` y `borde_bajo`) y casos con hasta 10 786 órdenes y patrimonio sobre 700 000, que ejercitan el espejo de la cuenta con cajas grandes. El peor caso de la respuesta es 439 ciclos en todas menos en la serie plana (383).

### 4.4 Repetición de los objetivos de las piezas

`mediciones/repeticion.txt`. Se guardó una copia de `mediciones/` de cada pieza, se corrieron sus objetivos y se comparó archivo por archivo, sin contar las líneas del commit y de los tiempos.

| Pieza | Objetivo | Archivo | Resultado |
|-------|----------|---------|-----------|
| `b_fondo_hilos` | `make programa` | `tamano.txt` | idéntico |
| | `make ticks` | `ticks.txt` | idéntico |
| | `make variantes` | `variantes.txt` | idéntico. Desde la segunda pasada tiene diez corridas: las nueve anteriores dan lo mismo que antes |
| | `make estado` | `estado.txt` | idéntico |
| | `make oficial` | `oficial.txt` | idéntico |
| | `make equiv` | `equiv.txt` | los 10 casos repetidos dan las mismas filas. La fila de 10 ms no se repitió |
| `i_integrado` | `make verif` | `verif_rv32e.txt` | idéntico |
| | `make tabla-vigilante` | `tabla_vigilante.txt` | idéntico (con el testbench ya corregido) |
| | `make mutaciones` | `mutaciones.txt` | idéntico (con el testbench ya corregido) |
| | `make formal` | `formal.txt` | idéntico |
| | `make recursos`, `make tb-xd` y `make oficial` | `recursos.txt`, `tb_xd.txt` y `oficial.txt` | repetidos una vez al cerrar la pieza: idénticos a la copia anterior |

Los 13 archivos se reproducen. En `b_fondo_hilos` la repetición cubre las cifras que faltaba confirmar al cerrar la pieza: palabras de programa y de datos (227 y 24, 251 de 512), instrucciones por tick de cada hilo (41,99 en promedio y 84 como máximo el supervisor, 35 cada gestor), ciclos de respuesta (227,36 en promedio y 439 en el peor caso del testbench, 440 barriendo la fase, de 2262) y las variantes (un gestor atrasado a propósito y el supervisor que usa lo del tick anterior).

Dos cosas que conviene saber sobre esos archivos:

- **`mediciones/equiv.txt` del fondo lo dejó `make equiv-ronda1`**, que agrega la práctica a 10 ms (34 minutos). `make equiv` y `make todo` lo vuelven a escribir con 10 casos. La repetición no lo pisa: corre los 10 casos con otro nombre de archivo y compara fila por fila.
- **Al corregir `tb/tb_vig_barrel.sv`, `tabla_vigilante.txt` y `mutaciones.txt` de `i_integrado` no cambiaron** más que en la línea del commit: el RTL sin mutar pasa igual con el testbench que mira la primitiva.

## 5. Mutaciones

`mediciones/mutaciones.txt`. Las dos piezas traen sus propios controles negativos (18 en `i_integrado`, y las variantes que deben fallar en `b_fondo_hilos`). Aquí se pusieron 18 errores distintos, elegidos pensando en qué se puede conectar mal y no en qué miran las pruebas.

| Mutación | Área | La detectan las pruebas de la pieza | Comentario |
|----------|------|-------------------------------------|------------|
| `opa_con_rs2`: el operando desplazado sale de rs2 | Extensión | Sí, en las tres configuraciones | |
| `emad_sin_decodificar`: el decodificador se instancia sin `emad` | Extensión | Sí, en las tres | |
| `anula_b_siempre`: el operando B se anula en `emad` y `devk` | Extensión | Sí, en las tres | |
| `mulstep_bit_30`: `mulstep` mira rs1[30] | Extensión | Sí, en las tres | Error dentro de `xd_opa`, visto desde la integración |
| `carriles_pegados`: el corte de acarreos no se suelta | Extensión | Sí, en la configuración con carriles | En I1 no hay carriles: no aplica |
| `k_de_otro_hilo`: `xd_opa` recibe el funct7 de otro hilo | Extensión | Sí, en la configuración con todos los k | En I1 el k está cableado en 5 y el funct7 no se usa: ahí es un mutante equivalente |
| `vig_cuenta_cs`: cuenta ciclos con CS_n en bajo | Vigilante | Sí | |
| `vig_un_precio_tarde`: dispara con N + 2 | Vigilante | Sí, y la prueba formal | |
| `vig_boot_sin_enganche`: BOOT vuelve a bajar | Vigilante | Sí, y la prueba formal | |
| `vig_mismo_ciclo`: pierde el precio que llega junto con una escritura | Vigilante | **Solo la prueba formal** de `e_warmboot` | La simulación no produce esa coincidencia |
| `warmboot_pines`: S1 y S0 cruzados en la primitiva | Vigilante | **Antes no. Ahora sí** | Ver abajo |
| `warmboot_sin_boot`: BOOT de la primitiva en 0 | Vigilante | **Antes no. Ahora sí** | Ver abajo |
| `pub_dos_stores`: tick y precio en dos escrituras | Protocolo | Sí, desde la fila 6 | |
| `g1_sin_sello`: no mira el número de tick de `EST_1` | Protocolo | Sí, desde la fila 58 | |
| `est_tick_viejo`: el gestor sella con el tick anterior | Protocolo | Sí: el supervisor se queda esperando | 2/4 |
| `sin_esperar_g3`: no espera al gestor 3 | Protocolo | **La equivalencia nominal no.** La variante `atraso_800` sí | Ver abajo |
| `sin_esperar_g2`: no espera al gestor 2 | Protocolo | **Antes no: ni la equivalencia ni `atraso_800`. Ahora sí**, con la variante `atraso_800_g2` | Ver abajo |
| `des_despues`: `EST_k` antes que `DES_k` | Protocolo | No | Mutante equivalente en este programa. Ver abajo |

**Las dos mutaciones de la primitiva.** El script corre además el testbench del vigilante como estaba antes de la auditoría (`VIG4-antes`, reconstruido deshaciendo las dos líneas que se cambiaron). Con ese testbench `warmboot_pines` y `warmboot_sin_boot` pasan. Lo que salvaba a la pieza es que su RTL estaba bien: la simulación de los bitstreams informa `S1S0=01` leído de la primitiva en el netlist reconstruido desde el `.asc`. Pero esa simulación solo corre el caso sano, y un BOOT desconectado también lo pasa. Con el testbench corregido las dos se detectan ("destino S1 S0 = 10 en la primitiva" y "BOOT no subió").

**`vig_mismo_ciclo`.** El vigilante trata aparte el caso en que un precio llega en el mismo ciclo en que el core escribe `DECISION`. Las simulaciones del barrel no producen esa coincidencia, así que no pueden notar si esa rama está mal. La prueba por inducción de `e_warmboot` sí la cubre. No hace falta cambiar nada, pero conviene saber que ese caso descansa en la prueba formal.

**`sin_esperar_g3`.** Es la mutación que más enseña. El supervisor lee `EST_1`, `EST_2` y `EST_3` uno tras otro, tres instrucciones por gestor, y los gestores publican con un ciclo de diferencia. Si el supervisor deja de comprobar el número de tick de `EST_3`, en el programa sin retardos nunca se nota, porque para cuando llega a leerlo el gestor 3 ya publicó. Las 20 000 filas de decisiones y de estado salen idénticas. La variante `atraso_800` de la pieza la detecta (decisiones distintas desde la fila 419), y la prueba de carreras de esta carpeta también: el monitor M9 marca 224 decisiones tomadas con un `EST_3` cargado del tick anterior. El monitor M5, que mira la memoria al escribir `DECISION`, veía solo 24 de esas 224. En ninguna de las 224 cambió un byte ni un campo del estado, porque la posición vieja coincidía con la nueva o no alcanzaba a cambiar el voto. Por eso los monitores miran las cargas y las escrituras y no solo el resultado.

**`sin_esperar_g2`.** Se agregó en la segunda pasada, después de ver en los contadores de la prueba de carreras que sin retardos el supervisor tampoco espera nunca al gestor 2. La predicción era que esta mutación pasaría todas las pruebas de la pieza, incluida `atraso_800`, que solo atrasa al gestor 3. Se cumplió: `EQUIV` y `ATRASO` dan 4/4 con decisiones y estado idénticos. De las pruebas que había, solo la de carreras la detectaba (M9 marca 300 decisiones con un `EST_2` cargado del tick anterior, y M5 solo 7). La corrección fue agregar a `make variantes` de la pieza la variante `atraso_800_g2`, que atrasa 800 ciclos al gestor 2: el programa sano la pasa y la mutación da decisiones distintas desde la fila 58 (`ATRASO2`). No hace falta una tercera variante para el gestor 1: sin retardos el supervisor ya lo espera unas 8 vueltas por tick, y la mutación equivalente (`g1_sin_sello`) la detectan todas las pruebas.

**`des_despues`.** El argumento de la sección 4.3 del README del fondo dice que el supervisor lee el puntaje del tick correcto porque el gestor escribe `DES_k` antes que `EST_k`. Invertir ese orden no cambia ni una decisión ni un peso en ninguna corrida, con retardos o sin ellos. La razón es de tiempos: el gestor escribe las dos palabras en instrucciones seguidas (4 ciclos) y el supervisor necesita al menos tres instrucciones (12 ciclos) entre leer `EST_k` y leer `DES_k`. Lo marca solo el monitor M4, que vigila el orden por definición. No es un defecto del programa. Sí es una propiedad que hoy nadie ejercita: si un gestor futuro hiciera trabajo entre los dos stores, el orden pasaría a importar y ninguna prueba de equivalencia lo avisaría.

## 6. Carreras entre hilos

### 6.1 Por lectura

Se leyó `sw/fondo.s` completo junto con `espino_barrel_core.v` y `rtl/pochoco_ram.v`.

- **Un solo acceso al bus de datos por ciclo.** El core tiene una sola instrucción en la etapa X y el store escribe en el flanco que cierra ese ciclo. Un load de otro hilo está en X en otro ciclo, así que ve la palabra vieja completa o la nueva completa. El puerto de instrucciones lee en el mismo flanco, pero eso solo importaría si un hilo ejecutara una palabra que otro está escribiendo, y el programa no escribe sobre su código.
- **`PUB` se escribe con un store.** Tick y precio viajan juntos. El precio ocupa 8 bits y no puede acarrear al número de tick.
- **La espera del supervisor compara el número de tick de cada `EST_k`** antes de aceptar la posición. `EST_k - tick * 256` vale 0 o 1 si es de este tick. Si es del anterior vale -256 o -255, que sin signo es mayor que 2. La cuenta sigue valiendo cuando el contador da la vuelta.
- **La frontera de ventana pisa los registros de las posiciones y vuelve a `s_g1`** a leerlas de nuevo. Es correcto, porque ningún gestor vuelve a escribir `EST_k` hasta que cambie `PUB`, y `PUB` lo cambia el propio supervisor.
- **x14 (la constante 2 de la espera) se usa como cociente dentro del espejo.** Se repone en todos los caminos: la única salida anterior a `li x14, 0` no lo ha tocado.
- **Las secuencias de leer, modificar y guardar** (caja, acciones, pesos, puntajes de referencia) son todas del supervisor. Cada gestor tiene su palabra `TMP_k`.
- **Solo el hilo 0 toca el esclavo SPI.**

No se encontró ninguna carrera por lectura. Lo que sí se encontró es lo de la sección 5: dos propiedades que el programa cumple gracias a los tiempos y que las pruebas nominales no distinguen.

### 6.2 Con una prueba

`mediciones/carreras.txt`, `tb/tb_carreras.sv`. La pieza había probado 24 fases de llegada con los gestores de tiempo constante y un solo gestor atrasado una cantidad fija. Aquí todo se mueve a la vez:

- **Fase de llegada.** El período de cada tick es el nominal más un valor al azar entre 0 y J nanosegundos, así que `byte_done` cae en cualquier ciclo de la rotación de hilos y en cualquier punto de los lazos de espera, también dentro de un ciclo.
- **Retardo de cada hilo.** El programa es `sw/fondo.s` con tres lazos agregados que leen los interruptores de la placa, que el testbench cambia al azar: cada gestor demora entre 6 y 37 instrucciones más antes de publicar (24 a 148 ciclos), hasta 240 vueltas de dos instrucciones después de publicar, y el supervisor entre 6 y 37 instrucciones entre publicar y empezar a esperar. Unas veces el supervisor llega a leer `EST_k` antes que el gestor publique y otras después. Los lazos solo usan registros libres y no cambian ningún valor.
- **Períodos más cortos que el de la ronda 3** (0,06 y 0,04 ms), en que un gestor sigue ocupado cuando llega el precio siguiente y el fondo pierde precios, y un retardo de hasta 960 vueltas con el que la vuelta del gestor no cabe en el tick.

Cada corrida se revisa de dos formas que no dependen una de la otra:

| Monitor | Qué vigila |
|---------|------------|
| M1 | Solo el hilo 0 accede al esclavo SPI |
| M2 | `PUB` avanza de a un tick, y cuando se publica el tick n + 1 los tres `EST_k` son del tick n |
| M3 | Cada `EST_k` se escribe con el número de tick que tiene `PUB`, una sola vez por tick y por su hilo |
| M4 | `DES_k` se escribe antes que el `EST_k` del mismo tick |
| M5 | Cuando se escribe `DECISION`, los tres `EST_k` son del tick de `PUB` |
| M6 | El byte escrito es el voto de las posiciones y los pesos que hay en la memoria en ese ciclo |
| M7 | Una sola escritura en `DECISION` por precio publicado |
| M8 | Todo acceso al SPI es un load o un store del programa |
| M9 | Lo último que el supervisor cargó de cada `EST_k` antes de escribir `DECISION` lleva el número de tick de `PUB` (el del tick anterior en la variante `anterior`) |

M9 se agregó en la segunda pasada de la auditoría (sección 13). M5 y M6 miran la memoria en el ciclo en que se escribe `DECISION`, y entre la carga de `EST_3` y esa escritura pasan 16 instrucciones (64 ciclos), más entre las de `EST_1` y `EST_2`: si en ese rato un gestor atrasado publica, M5 ya no ve que el supervisor cargó un dato viejo. M9 mira la carga misma (cada load del hilo 0 sobre `EST_k`), así que no depende de ese margen. El testbench cuenta además cuántas veces el supervisor cargó un `EST_k` que todavía era de otro tick y tuvo que volver a leer: es la medida de cuánto se ejercitó cada espera.

M2, M6 y M9 juntos dicen que el supervisor no decide con datos de dos ticks. La segunda revisión es contra el modelo: el testbench anota la serie de precios que el supervisor publicó y el estado de la memoria al terminar cada tick, y la referencia en C se corre sobre esa serie. Así la comparación de los 13 campos sirve aunque se pierdan precios.

| Corridas | Programa | Período | Precios perdidos | Peor respuesta (ciclos) | Esperas del supervisor a `EST_1`, `EST_2` y `EST_3` por corrida | Monitores | Modelo |
|----------|----------|---------|------------------|-------------------------|------------------------------------------------------------------|-----------|--------|
| 1 | sin retardos, solo fase al azar | 0,1 ms | 0 | 440 | 159 982, **0 y 0** | sin violaciones | idéntico |
| 8 | con retardos; práctica, `volatil` y `saltos` | 0,1 ms | 0 | 573 a 596 | unas 163 000, 11 a 8982 y 28 a 4128 | sin violaciones | idéntico |
| 2 | con retardos | 0,06 ms | 14 y 17 | 1593 | unas 530 000, 78 000 y 56 000 | sin violaciones | idéntico |
| 2 | con retardos | 0,04 ms | 4418 y 4371 | 1048 | unas 890 000, 218 000 y 140 000 | sin violaciones | idéntico |
| 1 | con retardos | 1 ms | 0 | 509 | 24 590, 180 y 106 | sin violaciones | idéntico |
| 2 | retardo de hasta 960 vueltas | 0,1 ms | 8474 y 8504 | 2596 | unos 2 490 000, 780 000 y 560 000 | sin violaciones | idéntico |
| 3 | variante que decide con el tick anterior, con retardos | 0,1 y 0,06 ms | 0, 0 y 1 | 1571 | 0, 0 y 0 a 0,1 ms; 19 832, 8258 y 5684 a 0,06 ms | sin violaciones | idéntico |
| **19** | | | | | **9 318 735, 2 179 175 y 1 532 216** | **337 174 decisiones, 0 violaciones** | **19 de 19** |

"Esperas" son las cargas en que el supervisor encontró el `EST_k` de otro tick y volvió a leer. Las cifras por corrida están en `mediciones/carreras.txt`.

Lectura:

- **No se encontró ningún caso en que el supervisor decida con datos mezclados de dos ticks.** Tampoco cuando el fondo va tan atrasado que pierde el 42 % de los precios: decide menos veces, pero cada decisión es la del modelo para los precios que vio. Con M9 la afirmación es exacta y no solo sobre el resultado: en las 337 174 decisiones, los tres `EST_k` que el supervisor cargó por última vez eran del tick que correspondía.
- **Sin retardos, el supervisor nunca espera a los gestores 2 y 3.** En los 20 000 ticks de la primera fila encontró `EST_1` atrasado 159 982 veces (unas 8 vueltas de espera por tick) y `EST_2` y `EST_3` ninguna: cuando termina de esperar al gestor 1, los otros dos ya publicaron, porque lo hacen 1 y 2 ciclos después y el supervisor tarda 12 en llegar a leerlos. Las pruebas nominales de la pieza solo ejercitan una de las tres esperas. Con los retardos de esta prueba las tres se ejercitan entre cientos y cientos de miles de veces por corrida.
- **La variante `anterior` a 0,1 ms tampoco espera nunca** (0, 0 y 0 en dos corridas): los gestores siempre terminaron el tick anterior cuando llega el precio. Su comprobación solo trabaja en la corrida a 0,06 ms.
- **La corrida sin retardos confirma el peor caso de la pieza**: 440 ciclos con la fase al azar en 20 000 ticks, el mismo que su barrido de 24 fases.
- **Que la prueba tiene dientes** lo dice la sección 5: las cinco mutaciones del protocolo la hacen fallar, incluida la que la equivalencia nominal deja pasar.
- **En la variante `anterior`** el monitor M5 no aplica, porque el supervisor toma las posiciones antes de publicar. M6 se evalúa contra el voto de la memoria en el ciclo en que publica. La comparación con el modelo va corrida una fila en las posiciones, los puntajes y los pesos, que es como los anota la traza de `fondo_min_ant`. La primera versión de la comparación no hacía ese corrimiento y marcó 21 a 32 filas distintas en los pesos: era un error de la comparación y no del programa.

## 7. Un gestor colgado

`mediciones/cuelgue.txt`. El programa es `sw/fondo.s` con el gestor del hilo 3 en un lazo sin fin desde el tick 100. 300 ticks a 0,1 ms.

| Hardware | Última decisión | BOOT en la primitiva |
|----------|-----------------|----------------------|
| Barrel prototipo, sin vigilante | con el precio 99 | |
| I1, vigilante con N = 4 | con el precio 99 | sube con el precio 104 = T + N |
| I1 con el programa sano (control) | con el precio 298 de 298 | no sube |
| I1 con el programa sano y retardos largos al azar, 20 000 ticks | decide 11 524 veces y pierde 8474 precios | no sube: la cuenta del vigilante llega a 4 de las 5 que hacen falta |

El protocolo no tiene plazo: el supervisor publica el tick 100, espera al gestor 3 y no vuelve a escribir `DECISION`. La maestra sigue leyendo el último byte. Sin vigilante eso dura hasta el final de la ronda. Con el vigilante de I1 la cuenta de precios sin respuesta llega a N + 1 y la FPGA pide el relevo, cinco precios después del cuelgue.

Esto corrige una frase del README de `i_integrado` y cambia la lectura de un riesgo: en el fondo en un chip, el vigilante cubre también a los tres hilos de estrategia, a través del supervisor.

La otra cara es el relevo en falso. La última fila lo mide con los retardos más largos de la prueba de carreras, en que la vuelta de un gestor dura hasta unos 3 ticks. El fondo pierde el 42 % de los precios y sigue decidiendo bien con los que ve, pero la cuenta del vigilante llega a 4, una menos de las que disparan. Un gestor que tardara 4 ticks o más en publicar provocaría el relevo con el programa sano. El fondo medido está muy lejos de eso (35 instrucciones por gestor), pero el margen entre "pierde precios" y "se va al respaldo" es de un tick.

## 8. Integridad del repositorio

`mediciones/integridad.txt`. Solo con `git status`, `git diff`, `git ls-files` y `git show`.

- **Ningún archivo versionado fuera de `factibilidad/` tiene cambios locales.**
- **`tb/tb_proyecto_4.sv` es byte a byte el del commit que lo entregó** (`63e5d19`), y ningún otro commit lo tocó.
- **`rtl/`, `tb/`, `ref/`, `tools/`, `sw/` y el `Makefile` de la raíz son los de `main`.**
- **Todo lo que aparece en `git status` está dentro de `factibilidad/`.**
- Las copias de fuentes del repositorio que usan las piezas siguen iguales al original, y las dos copias modificadas difieren en lo que dicen sus encabezados.

Tres cosas que no son fallas pero hay que saber:

1. **Las dos piezas y esta carpeta todavía no están en ningún commit.** Para que cumplan "todo hardware agregado debe estar en el repositorio" tienen que entrar.
2. **Hay dos archivos versionados con cambios locales dentro de `factibilidad/retorno/`** (`generar_series.py` y `nucleo/torneo.c`), que son de otro estudio en curso. La referencia en C del fondo se compila con ese núcleo. `integridad.txt` compila la referencia dos veces, con los fuentes de HEAD y con los del disco, y compara: entregan el mismo `decisiones.csv` para `fondo_min` y `fondo_min_ant`. `fondo.c` y `nucleo.c` no tienen cambios.
3. **La rama tiene un commit anterior que toca cuatro documentos fuera de `factibilidad/`** (`4bcd4ab`, el cambio de calendario de la decisión T44). No es de estas piezas.

## 9. Reglas del enunciado para el fondo en un chip

`mediciones/reglas.txt`. La configuración es el hardware I1 con `sw/fondo.s`. Serie de práctica completa a 0,1 ms.

| Regla | Qué se midió | Resultado |
|-------|--------------|-----------|
| "El core debe leer el precio y escribir la decisión" | Cada acceso al esclavo SPI: qué hilo lo hace y con qué instrucción | Los 19 998 precios los lee y las 19 998 decisiones las escribe el hilo 0, con `lw` y `sw`. Cero accesos de otros hilos y cero accesos que no sean de una instrucción del programa |
| "El hardware agregado no reemplaza al procesador en el ciclo de decisión" | Por lectura del RTL: qué puede escribir `DECISION` | Solo una escritura del bus de datos del core en el registro 2 del esclavo. El vigilante solo tiene las salidas `boot_o` y `sel_o`, las memorias de la tabla solo `rdata_o`, y `xd_opa` es combinacional dentro de la etapa X |
| "No almacenar series de precios en el diseño" | La memoria al terminar los 20 000 ticks contra la imagen inicial | Cambiaron 17 de 512 palabras, todas del estado del programa (`PUB`, caja, pesos, puntajes de referencia y los tres bloques de los gestores). No hay ningún arreglo que crezca con la serie. La tabla de 256 x 16 sigue en cero |
| Regla propia: nada derivado punto a punto de la serie de práctica | Constantes de la imagen | 10 palabras de datos distintas de cero: la caja inicial, los tres pesos y sus topes y pisos. 52 constantes `.equ`, ninguna tabla |
| "Todo hardware agregado debe estar en el repositorio con su testbench" | Por cada módulo de la lista de fuentes de I1 que no es de `rtl/`, qué testbench lo instancia | 13 módulos tienen testbench propio. **6 no**: el core barrel, sus dos módulos del banco de registros, el decodificador con la extensión, la copia del esclavo SPI y `xd_unit`. Se prueban dentro del SoC |
| "El mismo programa para todas las series" | | Un solo programa. No mide el período |

Sobre la última fila con negrita: el core y el banco de registros tienen además las propiedades formales de `a_barrel` y de `i_integrado`, y el SoC que los contiene tiene tres testbenches en `i_integrado`, más `tb_verif.sv` del barrel y el testbench oficial. Que eso alcance para "con su testbench" es una lectura de la regla. Lo seguro es preguntarle al ayudante o escribir un testbench mínimo por módulo antes de entregar.

Las dudas de fondo son las que ya plantearon las dos piezas y siguen abiertas: si un Espino de cuatro hilos y con instrucciones en custom-0 sigue siendo Espino, y si tres hilos que calculan estrategias y un cuarto que decide cumplen "el core debe leer el precio y escribir la decisión". La medición dice quién toca el SPI. No resuelve la interpretación.

## 10. Coherencia de los resúmenes y días de trabajo

Se contrastó cada cifra de los dos README con el archivo de `mediciones/` que cita.

- **`i_integrado`.** Las tablas de las secciones 1, 4, 6, 7, 8 y 9 coinciden con `recursos.txt` línea por línea. Las cifras de verificación (240 programas por variante, 884 281 instrucciones por configuración, 155 648 vueltas en la prueba mixta, los siete sha256) coinciden con sus archivos. Las comparaciones "sobre el segmentado" coinciden con el README de `d_isa`. No hubo que corregir ningún número. Sí tres frases (sección 1 de este documento, puntos 1, 2 y 4).
- **`b_fondo_hilos`.** Las cifras de tamaño, instrucciones por tick, ciclos de respuesta, variantes y retorno coinciden con sus archivos. Faltaba completar el texto (punto 3). La frase "la decisión no depende de los ciclos" estaba respaldada para el gestor 3 y no para el gestor 2 (punto 5): ahora lo está para los dos.
- **Esta carpeta.** La primera versión decía que M2, M5 y M6 bastaban para afirmar que el supervisor no decide con datos de dos ticks. No bastaban (punto 6). Se agregó M9 y se repitió la búsqueda.

Días de trabajo frente al calendario. El hardware se congela el 25/11 en la noche, la maestra es el 26/11 y hoy es 14/11: quedan 11 días de calendario, 33 días de persona para todo el proyecto.

| Configuración | Días de persona estimados | Qué fracción de los 33 | Juicio |
|---------------|---------------------------|------------------------|--------|
| I1 con el fondo completo | 16 a 18,5 | la mitad | No se sostiene para la competencia: ocupa la mitad del grupo hasta el congelamiento, junta tres piezas que no han pasado por la placa y su único aporte al patrimonio, el fondo, no pasa el criterio de algoritmo |
| I1 con `fondo_min` tal como está | 13,5 a 15,5 | algo menos de la mitad | Lo mismo |
| I2 | 8,5 a 9 | un cuarto | Defendible en plazo. No cambia el patrimonio y responde más lento que el segmentado |
| I3 | 7 a 7,5 | un quinto | Defendible. Es la que menos arriesga |
| I4 | 0,25 | | Es lo que hay |

El rango de cada fila va de la suma con el descuento de lo que se hace una sola vez a la suma sin él. Las dos piezas estiman bien sus tareas una por una y las dos cuentas son coherentes entre sí: `i_integrado` pone 5 días para el programa del fondo y `b_fondo_hilos` pone 7 para la versión de competencia, de los cuales 2,5 (gemelo y documento) ya están en los 5 del barrel. La diferencia entre las dos es medio día. Lo que no se sostenía era la frase sobre la holgura: 3 días libres antes del 25/11 solo existen si las tres personas no hacen nada más del 15 al 22/11 y si nada falla en la placa. Ninguna de las estimaciones tiene margen para una falla de placa, y el antecedente es que en el Proyecto 2 el reset corto falló justamente ahí.

## 11. Lo que no se verificó

- **Nada en la placa ni con la maestra real.** Igual que las dos piezas.
- **El relevo completo del vigilante sobre el barrel.** Se comprobó que BOOT sube en la entrada de la primitiva en el momento debido. No se simuló la reconfiguración ni el arranque del respaldo, y la simulación desde el `.asc` solo corre el caso sano.
- **Los tres objetivos largos de `i_integrado` dentro de `make repeticion`.** `recursos`, `tb-xd` y `oficial` se repitieron una vez al cerrar la pieza y se compararon con la copia anterior. `make repeticion` los vuelve a correr solo con `LARGOS=1`. `make mixto` y `make bitstreams` no se repitieron: de los bitstreams se comprobó el sha256 de cinco de los siete (sección 4.1), no la simulación desde el `.asc`.
- **La fila de 10 ms de la equivalencia del fondo.** Está en el archivo guardado de la pieza (34 minutos). No se repitió.
- **Mutaciones de la memoria de la tabla.** La pieza tiene siete propias. Aquí no se agregaron.
- **Las demás variantes de `make variantes` con los programas mutados.** Las mutaciones del protocolo se corrieron contra la equivalencia nominal y contra las dos variantes de atraso de 800 ciclos, no contra `espejo_antes`, `anterior`, `vuelta` ni las de 2000 y 2400 ciclos.
- **El supervisor de la variante `anterior` esperando de verdad.** A 0,1 ms nunca espera. Su comprobación solo se ejercitó en una corrida a 0,06 ms (19 832, 8258 y 5684 esperas).
- **Una cota demostrada del peor caso de la respuesta.** Sigue siendo el máximo observado: 440 ciclos en el barrido de 24 fases de la pieza y en 20 000 ticks con la fase al azar.
- **Carreras en un fondo distinto de `fondo_min`.** Los monitores están escritos para este protocolo. Un fondo con posiciones parciales o con un plazo en el supervisor necesita los suyos.
- **Rondas seguidas sin reconfigurar**, que el README del fondo ya deja como pendiente.

## 12. Conclusiones vigentes

- **I1, I2 e I3 caben y cierran.** Confirmado con una medición independiente y con 20 semillas. El criterio de corte de hardware no descarta ninguna.
- **El fondo en un chip completo funciona en simulación**: hardware I1 con `sw/fondo.s`, 4/4 en el testbench oficial, decisiones idénticas a su referencia, vigilante quieto con el programa sano y disparo correcto con un gestor colgado.
- **El protocolo entre hilos no tiene carreras** que esta auditoría haya podido provocar. En 337 174 decisiones con tiempos al azar, el supervisor nunca decidió con un `EST_k` cargado de otro tick.
- **El fondo no pasa el criterio de corte de algoritmo.** Eso lo midió el estudio de retorno 4B y esta auditoría no lo revisó: aquí se comprobó que el programa hace lo que hace su referencia, no que la referencia gane.
- **Para la competencia**, lo defendible frente al calendario es I3 o I2. I1 queda para la edición de exhibición.

## 13. Segunda pasada (15/11)

La auditoría se repitió completa al día siguiente, partiendo de las salidas guardadas, y se agregaron cuatro cosas.

**Repetición.** `make todo` otra vez, 15 minutos: las nueve salidas de `mediciones/` salieron idénticas a las guardadas, sin contar las líneas de fecha y de demora (copia anterior en `build/mediciones_previas_0201/`). Eso incluye las celdas, las BRAM y las 20 frecuencias de cada configuración, las seis corridas del testbench oficial, los 34 casos de equivalencia, las 17 mutaciones y las 19 corridas de carreras. La integridad del repositorio se comprobó además a mano con `git status`, `git diff --stat` y el sha256 del testbench oficial contra el del commit `63e5d19`.

**Sha256 de los bitstreams** (`tools/recursos.sh`, sección 4.1). Los cinco bitstreams de I1, I2 e I3 hechos desde la síntesis de esta carpeta tienen el sha256 que informa la pieza.

**Monitor M9 y cuenta de esperas** (`tb/tb_carreras.sv`, sección 6.2). Al leer el testbench se vio que M5 mira la memoria al escribir `DECISION` y no lo que el supervisor cargó. M9 mira cada load del hilo 0 sobre `EST_k`. Resultado con el programa sin mutar: 0 violaciones en las 19 corridas. Con el supervisor que no espera al gestor 3, M9 marca 224 decisiones y M5 solo 24.

**Mutación `sin_esperar_g2` y variante `atraso_800_g2`** (sección 5). Los contadores de esperas mostraron que sin retardos el supervisor nunca espera a los gestores 2 y 3. La pieza cubría al gestor 3 con `atraso_800` y a nadie más. La mutación nueva pasaba todas las pruebas de la pieza. Se agregó la variante a `factibilidad/b_fondo_hilos/tools/variantes.sh` y ahora se detecta.

Con eso las cuentas quedan en 18 mutaciones, 17 detectadas por las pruebas de las piezas (14 antes de las dos correcciones: el testbench del vigilante, que deja ver dos, y la variante nueva, que deja ver una) y 18 contando las pruebas de esta carpeta.

Se volvieron a correr `make carreras`, `make mutaciones`, `make cuelgue`, `make reglas` e `make integridad` de esta carpeta, `make variantes` de la pieza del fondo y `make repeticion` (466 segundos: los 10 objetivos repetidos de las dos piezas dan salidas idénticas a las guardadas, `variantes.txt` ya con sus diez corridas). `mediciones/cuelgue.txt` y `mediciones/reglas.txt` no cambiaron. `mediciones/oficial.txt` y `equiv.txt` son los de la repetición completa, que no usa nada de lo que se modificó después, y `mediciones/recursos.txt` se volvió a generar al agregar los sha256: lo demás salió igual. No se corrió un `make todo` entero después de los cambios: cada objetivo afectado se corrió por separado.
