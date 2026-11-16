# Auditoría de los estudios de retorno 3 y 4

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Tramo de factibilidad del Proyecto 4. Esta carpeta no agrega hardware ni cambia el programa de la placa. Es una revisión independiente de cuatro estudios hechos con el arnés de `factibilidad/retorno`: la ejecución que conoce su patrimonio (`../r3_ejecucion`), el fondo de estrategias (`../r4b_fondo`), el aprendizaje en vivo (`../r4c_aprendizaje`) y el cierre, que compara el fondo completo con la mejor estrategia sola (`../r4_final`). La decisión sobre el fondo se apoya en esas cifras, así que la revisión se hizo tratando de refutarlas.

## 1. Resultado

**Las cifras se reproducen y las conclusiones se sostienen. No se encontró ningún error de cálculo, ninguna fuga de información del futuro y ninguna señal de que la semilla reservada se haya usado más de una vez. Se corrigieron cuatro frases que decían más de lo que las tablas sostienen y se agregaron cinco precisiones.** Ninguna cambia la recomendación.

| Punto revisado | Resultado |
|----------------|-----------|
| 1. Información del futuro | Sin fallas: comando `causal` en 110 estrategias registradas y 22 variantes sin alias, y una perturbación propia con 85 008 comparaciones en 56 estrategias. Los 3 controles negativos fallan, como deben |
| 2. Sesgo de selección | Las candidatas quedaron fijadas antes de generar la semilla 3 y la lista final tiene la huella que se anotó antes de la corrida. Un solo registro de corrida con la semilla 3. Son indicios de archivo, no una prueba |
| 3. Reproducción independiente | 15 estrategias reescritas (12 de los estudios y 3 con un límite por orden hipotético), 46 061 series cada una, 0 distintas del arnés. 1 174 cifras del resumen del cierre contra otro evaluador, 0 fuera de tolerancia. Los campos nuevos no cambian ninguna salida anterior |
| 4. Cotas | La cota de ejecución, el oráculo del fondo y la mezcla fija se recalcularon y coinciden. Ninguna se presenta como alcanzable. Tres precisiones (sección 8) |
| 5. Implementabilidad | Aritmética entera, sin productos ni cocientes fuera de los declarados. Las instrucciones por tick son estimaciones y están marcadas así. Dos precisiones (sección 9) |
| 6. Reglas | Ninguna tabla ni constante sale punto a punto de la serie de práctica |
| 7. Coherencia | Cuatro frases corregidas en `../r4_final/README.md` y una en `../r3_ejecucion/README.md` (sección 11) |

Lo que queda vigente está en la sección 12.

## 2. Qué se construyó

| Archivo | Qué es |
|---------|--------|
| `Makefile` | Un objetivo por comprobación. Compila `build/arnes` (el núcleo y los módulos de los cuatro estudios, sin tocar), `build/perturba` y `build/indep34`. |
| `causal.sh` | El comando `causal` del arnés para todo lo registrado y para 22 variantes sin alias. |
| `perturba.c` | Perturbación propia de los precios futuros, repetición entre rondas, serie cortada y prueba de martingala, con tres controles negativos. Programa aparte, enlazado con el núcleo sin su `main.c`. |
| `indep34.c` | Evaluador independiente. No usa ningún fuente del núcleo ni de las carpetas auditadas. Incluye sin modificar el evaluador de la auditoría del arnés (`../auditoria/indep.c`: contabilidad escrita desde el enunciado, 61 rivales, campos y valor esperado exacto del torneo) y agrega, escrito de nuevo a partir de los README: `ejec`, el Kalman de dos estados, la tabla que aprende, el supervisor del fondo, la regla con un límite por orden hipotético, las tres vistas, la semilla 3, los duelos contra `ejec_a` y la robustez del espejo. |
| `equivalencia.py` | Las estrategias reescritas contra las del arnés, serie por serie. |
| `sin_cambios.sh` | Los campos nuevos de `../nucleo/torneo.c` no cambian las salidas anteriores, con una lista de comandos distinta de la del estudio. |
| `veredictos_campos.sh` | El veredicto por campo de las tablas del cierre contra el comando oficial `veredicto`. |
| `aritmetica.py` | Productos, cocientes y tipos anchos en las rutinas de decisión, y frecuencia medida de cada operación cara. |
| `seleccion.sh` | Fechas, huellas, usos de la semilla 3 y cantidad de variantes. |
| `repetir.sh` | Repite objetivos baratos de las cuatro carpetas auditadas y compara sus salidas. |
| `informe.py` | Cifras informadas contra obtenidas, y la tabla principal en Markdown. |
| `mediciones/` | Todas las salidas. |

Fuera de esta carpeta se cambiaron solo los cuatro README auditados (texto, sección 11). No se tocó ningún fuente, ningún script ni ninguna medición de los estudios. `../auditoria/indep.c` se usa tal cual, con `#include`: no hizo falta copiarlo ni modificarlo.

## 3. Cómo se reproduce cada número

Desde esta carpeta, con las series del arnés generadas (`make -C .. series`) y sus resultados guardados (`make -C .. exploracion`). `repetir` necesita además `../build/auditoria/estudio_s0.txt` (`make -C ../auditoria estudio`).

| Comando | Qué hace | Salida en `mediciones/` | Tiempo medido |
|---------|----------|-------------------------|---------------|
| `make` | Compila los tres binarios. | | segundos |
| `make causal` | Comando `causal` del arnés. | `causal.txt` | 1 s |
| `make perturba` | Perturbación propia y martingala. | `perturbacion.txt` | 33 s |
| `make sin-cambios` | `torneo.c` anterior contra el actual. | `sin_cambios.txt` | 4 min 10 s |
| `make equivalencia` | Estrategias reescritas contra el arnés. | `equivalencia.txt` | 59 s |
| `make reproducir` | Tabla final con el evaluador independiente, semillas 0 y 3. | `independiente_s0.txt`, `independiente_s3.txt` | 1 min 36 s |
| `make cotas` | Cota de ejecución, oráculos del fondo y robustez del espejo. | `cotas.txt` | 35 s |
| `make aritmetica` | Operaciones de cada candidata. | `aritmetica.txt` | 18 s |
| `make seleccion` | Fechas, huellas y variantes. | `seleccion.txt` | 1 s |
| `make veredictos` | Veredicto por campo contra el comando oficial. | `veredictos_campos.txt` | 5 min 26 s |
| `make repetir` | Objetivos baratos de las carpetas auditadas, repetidos. | `repeticion.txt` | 2 min 39 s |
| `make informe` | Cifras informadas contra obtenidas. | `cifras.txt`, `tabla_principal.md` | 1 s |
| `make todo` | Todo, en orden. | | 16 min 20 s como un solo comando |

`HILOS` vale 5.

## 4. Punto 1: información del futuro

### Por lectura

- **Interfaz.** `decidir` recibe un precio por valor y una copia de la cuenta después de ejecutar, a ese mismo precio, la decisión anterior. Ningún módulo de los cuatro estudios guarda variables globales que cambien, lee archivos ni recibe la serie. Lo único estático es el escritor de la traza del fondo (`FONDO_TRAZA`), que solo escribe.
- **Fondo con cuentas en papel** (`fondo.c`, `fondoc.c`). En cada tick, cada gestor ejecuta primero en su cuenta en papel su decisión anterior al precio que acaba de llegar y después decide. El puntaje por acción suma el cambio de precio del tick solo si el gestor ya tenía la acción ejecutada. El reparto usa el desempeño publicado hasta ese tick.
- **Tabla que aprende** (`e_tabla.c`). En el tick n ajusta la casilla que se usó en el tick n - 1 - h con `R = p[n] - p[n - h]`: el precio que acaba de llegar menos el precio al que se ejecutó esa decisión. Los dos ya se recibieron. El anillo tiene 128 lugares y `h` llega a 126.
- **Predictor de patrones** (`pred.h`). La misma estructura: entrena el contador de la predicción del tick n - 1 - h con el signo de `p[n] - p[n - h]`.

### Por prueba

`mediciones/causal.txt`: el comando `causal` del arnés pasa en las 110 estrategias, alias y rivales registrados (8 580 comparaciones) y en 22 variantes sin alias.

El comando `causal` tiene un límite que conviene conocer: usa series de 3000 ticks y 6 cortes, y la tabla `aprendiz` (prior fuerte) casi no cambia ninguna decisión en ese largo. Una fuga en el ajuste de la tabla no se vería. Por eso la prueba propia (`perturba.c`, `mediciones/perturbacion.txt`) usa series de 8192 ticks, 63 cortes por serie (los bordes de las ventanas de 512 ticks del fondo, los del anillo y 24 al azar) y agrega variantes que aprenden rápido por el mismo código (`tabla:ka=6`, contadores de 4 bits, fondo con ventana de 64 ticks):

| Prueba | Qué exige | Resultado en las 56 estrategias |
|--------|-----------|----------------------------------|
| Repetición | La misma ronda después de otra ronda decide igual | 0 fallas |
| Futuro al azar | Con la serie cambiada desde el tick T, los bytes leídos hasta T no cambian | 0 fallas |
| Futuro parecido | Lo mismo, sumando a la serie un paseo lento desde T | 0 fallas |
| Solo el precio de ejecución | Lo mismo, cambiando solo el precio del tick T | 0 fallas |
| Serie cortada en T | Las decisiones hasta T no cambian | 0 fallas |
| Martingala | En 4000 series sin sesgo y sin comisión la media del patrimonio final es 10 000 | La más lejana queda a 1,34 errores |

Son 85 008 comparaciones de decisiones. Controles negativos: una estrategia que mira los dos precios siguientes falla 794 comparaciones y saca 40 189 de media en la martingala (1095 errores); una que ajusta un umbral con el retorno futuro a 16 ticks y tasa 2^-12, la misma forma de la tabla, falla 14; una que guarda un contador entre rondas falla 1174.

Lo que estas pruebas no pueden ver: una estrategia en C podría leer memoria ajena. No hay nada parecido en el código.

## 5. Punto 2: sesgo de selección

`mediciones/seleccion.txt`.

- **Variantes probadas con la semilla 0**: 61 de ejecución (37 más el control y 24), 88 del fondo y 5 configuraciones con nombre, 249 de aprendizaje (más 17 bandas para la cota, 60 configuraciones del predictor y 8 del cuarto gestor) y 19 configuraciones en el cierre. Son las cifras que dan los README.
- **Las candidatas estaban fijadas antes de que existiera la semilla 3.** Los fuentes que las definen son del 14/11 entre las 12:19 y las 12:50, y las salidas con que cada estudio las recomendó son de las 12:43 (fondo), 17:31 (ejecución) y 17:42 (cuarto gestor). La primera serie de la semilla 3 se generó a las 21:06. `fondoc.c` y `final.c`, que arman las configuraciones del cierre, son de las 21:09 y 21:10.
- **La lista final se fijó antes de la corrida.** `../r4_final/build/lista_final_original.txt` tiene la huella `3a940a49...` que quedó anotada en `reservada_usada.txt` al iniciar la corrida (21:38). La lista actual difiere en una línea de comentario. Las 11 candidatas del registro de la corrida son las de la lista.
- **Una sola corrida.** Hay un registro (`build/final_s3.log`, 728 s), sus salidas son de las 21:38 a las 21:48, no hay resultados guardados de la semilla 3 en `../build/resultados` y ningún script de los estudios 3, 4B y 4C la nombra. `correr.py` se niega a repetirla sin `--repetir` y `explorar.py` se niega a usarla.
- **Después de la corrida** solo cambiaron `tablas.py` (22:13, agrega una columna) y el comentario de la lista. Los veredictos por campo, que calcula `tablas.py`, se comprobaron contra el comando oficial (sección 6).
- **El tamaño del efecto no deja lugar a un falso positivo por selección.** `ejec:m=8` da +0,0074 ± 0,0002 con H3a en la semilla 3, que no participó en elegirla.

Dos avisos. Las fechas de archivo se pueden cambiar: esto es un indicio. Y las semillas 0 y 3 no son evidencia independiente de la serie de práctica: los remuestreos de las dos salen de la misma serie y las familias plausibles del mismo modelo ajustado. La semilla reservada confirma que el resultado no es suerte del sorteo, no que valga para otra serie.

**Esta auditoría volvió a usar la semilla 3**: `make reproducir` evalúa con ella las mismas candidatas en otro evaluador, y `make equivalencia` compara cuatro de sus archivos serie por serie. No se eligió ni se ajustó nada. Para estas candidatas ya no es una semilla sin mirar.

## 6. Punto 3: reproducción independiente

### Estrategias reescritas

`indep34.c` trae su propia versión de cada pieza, escrita a partir de la descripción de los README (sección 4.2 del estudio del fondo para el supervisor). `make equivalencia` compara el patrimonio final y las órdenes de cada serie con el comando `detalle` del arnés, en 36 archivos: las 15 familias de la semilla 0 a los dos largos (incluidas las de estrés y las de borde), cuatro archivos de la semilla 3, los bloques y la serie de práctica.

| Estrategia | Series | Distintas |
|------------|--------|-----------|
| `ejec:m=8`, `ejec:m=8,m2=24,e2=32` | 46 061 cada una | 0 |
| `kalman`, `aprendiz`, `aprendiz_rapido` | 46 061 cada una | 0 |
| `fondo_rec`, `rec_e`, `completo`, `completo_s` | 46 061 cada una | 0 |
| `fondo_min`, `min_e`, `completo_min` | 46 061 cada una | 0 |
| Límite hipotético de 126, 252 y 2^21 acciones por orden (contra el binario de la cota del estudio 3) | 46 061 cada una | 0, sin contar las series en que el patrimonio pasa de 2^31 |

En la serie de práctica completa: `ejec:m=8` 26 567 con 606 órdenes, `completo` 25 547 con 584 y `completo_min` 27 756 con 630, iguales en los dos evaluadores.

Qué tan independiente es: el supervisor, el espejo, la contabilidad, el lazo, los rivales, los campos y el torneo no comparten código con el arnés. El Kalman y la tabla se reescribieron después de leer su código, así que la coincidencia prueba que hacen lo que el README dice, no que la idea esté bien. `espera`, `completo_ancla`, `completo_esp`, `completo_ap`, `fondo_ancla` y `aprendiz_patron` no se reescribieron.

### La tabla final

`make reproducir` y `make informe` (`mediciones/cifras.txt`). El arnés sortea 6 campos de rivales por serie y el evaluador independiente calcula el valor esperado exacto, así que los puntos no pueden coincidir al último decimal.

| Clase de cifra | Cifras | Diferencia mediana | Diferencia máxima | Fuera de tolerancia |
|----------------|--------|--------------------|-------------------|---------------------|
| Patrimonio (H1) y su percentil 5 | 214 | 0,14 | 0,50 (el redondeo) | 0 |
| Razón W/B&H | 60 | 0,0002 | 0,0005 | 0 |
| Puntos de torneo: niveles y diferencias pareadas, cinco campos, tres vistas, evidencia, remuestreo, plausibles y estrés | 900 | 0,0004 | 0,0028 | 0 |

Son 1 174 cifras de `../r4_final/mediciones/resumen.md`, con las dos semillas. Otras 144 celdas del resumen no se compararon: son de `espera` y `completo_ancla`, y las columnas del campo racional en el estrés.

Tabla principal (`mediciones/tabla_principal.md`): `max_media`, la mejor estrategia sola y el fondo completo. Semilla 0 / semilla 3. Lo obtenido lleva su error estándar.

| Cifra | Informado | Obtenido | Coincide |
|---|---|---|---|
| `max_media`: percentil 5 del patrimonio, 2000 ticks | 8 754 / 8 732 | 8 754,0 / 8 732,0 | sí |
| `max_media`: H3a, campo mixto, 2000 ticks (nivel) | 1,503 / 1,499 | 1,5028 / 1,4980 | sí |
| `max_media`: H3b, campo mixto, 2000 ticks (nivel) | 1,473 / 1,464 | 1,4728 / 1,4645 | sí |
| `max_media`: H3a, campo mixto, 20 000 con parada (nivel) | 1,721 / 1,717 | 1,7229 / 1,7166 | sí |
| `max_media`: H3b, campo mixto, 20 000 con parada (nivel) | 1,708 / 1,704 | 1,7086 / 1,7036 | sí |
| `max_media`: H3a, campo fuerte, 2000 ticks (nivel) | 1,423 / 1,417 | 1,4226 / 1,4185 | sí |
| `max_media`: H3a, campo racional, 20 000 interiores (nivel) | 1,500 / 1,520 | 1,5010 / 1,5172 | sí |
| `max_media`: H3a, campo reversores, 20 000 con parada (nivel) | 1,212 / 1,225 | 1,2110 / 1,2254 | sí |
| `ejec_a` menos `max_media`: patrimonio, 2000 ticks | +15 / +14 | +14,8 ± 0,3 / +14,2 ± 0,3 | sí |
| `ejec_a` menos `max_media`: H3a, mixto, 2000 ticks | +0,007 / +0,007 | +0,0075 ± 0,0002 / +0,0074 ± 0,0002 | sí |
| `ejec_a` menos `max_media`: H3b, mixto, 2000 ticks | +0,027 / +0,027 | +0,0269 ± 0,0006 / +0,0272 ± 0,0006 | sí |
| `ejec_a` menos `max_media`: H3a, mixto, 20 000 con parada | +0,007 / +0,006 | +0,0066 ± 0,0001 / +0,0064 ± 0,0001 | sí |
| `ejec_a` menos `max_media`: H3a, reversores, 2000 ticks | +0,034 / +0,033 | +0,0338 ± 0,0013 / +0,0326 ± 0,0012 | sí |
| `completo` menos `max_media`: patrimonio, 2000 ticks | +12 / +13 | +12,3 ± 3,3 / +13,1 ± 2,8 | sí |
| `completo` menos `max_media`: patrimonio, 20 000 con parada | +349 / +376 | +348,7 ± 24,7 / +376,0 ± 26,0 | sí |
| `completo` menos `max_media`: H3a, mixto, 2000 ticks | +0,002 / +0,000 | +0,0019 ± 0,0008 / +0,0005 ± 0,0008 | sí |
| `completo` menos `max_media`: H3b, mixto, 2000 ticks | +0,013 / +0,011 | +0,0133 ± 0,0014 / +0,0120 ± 0,0014 | sí |
| `completo` menos `max_media`: H3a, mixto, 20 000 interiores | +0,003 / +0,002 | +0,0023 ± 0,0010 / +0,0030 ± 0,0010 | sí |
| `completo` menos `max_media`: H3a, mixto, 20 000 con parada | -0,002 / -0,001 | -0,0018 ± 0,0008 / -0,0012 ± 0,0008 | sí |
| `completo` menos `max_media`: H3b, mixto, 20 000 con parada | +0,014 / +0,014 | +0,0132 ± 0,0012 / +0,0138 ± 0,0012 | sí |
| `completo` menos `max_media`: H3a, fuerte, 2000 ticks | +0,001 / -0,001 | +0,0012 ± 0,0011 / -0,0005 ± 0,0011 | sí |
| `completo` menos `max_media`: H3a, racional, 20 000 con parada | +0,017 / +0,018 | +0,0165 ± 0,0015 / +0,0176 ± 0,0014 | sí |
| `completo` menos `ejec_a`: patrimonio, 2000 ticks | -2 / -1 | -2,5 ± 3,3 / -1,1 ± 2,8 | sí |
| `completo` menos `ejec_a`: patrimonio, 20 000 con parada | +221 / +249 | +220,7 ± 24,5 / +249,4 ± 25,9 | sí |
| `completo` menos `ejec_a`: patrimonio, parada, solo remuestreo | -12 / -1 | -12,4 ± 26,6 / -0,6 ± 27,8 | sí |
| `completo` menos `ejec_a`: patrimonio, parada, solo plausibles | +454 / +500 | +453,8 ± 40,9 / +499,5 ± 43,4 | sí |
| `completo` menos `ejec_a`: H3a, mixto, 2000 ticks | -0,006 / -0,007 | -0,0055 ± 0,0008 / -0,0069 ± 0,0008 | sí |
| `completo` menos `ejec_a`: H3b, mixto, 2000 ticks | -0,013 / -0,016 | -0,0136 ± 0,0014 / -0,0152 ± 0,0014 | sí |
| `completo` menos `ejec_a`: H3a, mixto, 20 000 con parada | -0,008 / -0,008 | -0,0085 ± 0,0008 / -0,0076 ± 0,0008 | sí |
| `completo` menos `ejec_a`: H3b, mixto, 20 000 con parada | -0,034 / -0,034 | -0,0344 ± 0,0013 / -0,0340 ± 0,0013 | sí |
| `completo` menos `ejec_a`: H3a, fuerte, 2000 ticks | -0,009 / -0,011 | -0,0092 ± 0,0011 / -0,0106 ± 0,0011 | sí |
| `completo` menos `ejec_a`: H3a, racional, 20 000 interiores | +0,010 / +0,012 | +0,0099 ± 0,0020 / +0,0127 ± 0,0020 | sí |
| `completo` menos `ejec_a`: H3a, racional, 20 000 con parada | +0,001 / +0,002 | +0,0009 ± 0,0015 / +0,0023 ± 0,0014 | sí |
| `completo` menos `ejec_a`: H3b, reversores, 20 000 con parada | -0,199 / -0,200 | -0,1976 ± 0,0059 / -0,1998 ± 0,0058 | sí |
| `completo_min` menos `ejec_a`: H3a, mixto, 2000 ticks | -0,000 / +0,000 | -0,0000 ± 0,0001 / +0,0002 ± 0,0001 | sí |
| `completo_min` menos `ejec_a`: H3a, mixto, 20 000 con parada | -0,009 / -0,011 | -0,0091 ± 0,0012 / -0,0109 ± 0,0011 | sí |

Son 36 cifras, cada una con las dos semillas, y coinciden las 36. Hay 16 de la vista de parada y 10 con los campos fuerte, racional y de reversores.

### Veredictos y campos nuevos

- `make veredictos` (`mediciones/veredictos_campos.txt`): el estudio corrió el comando oficial `veredicto` solo con el campo mixto y calculó los demás en `tablas.py`. Con el comando oficial, la semilla 0 y los campos ingenuo, fuerte, racional y de reversores, los 20 veredictos de `ejec_a`, `completo`, `completo_min`, `rec_e` y `fondo_rec` son los de la tabla.
- `make sin-cambios` (`mediciones/sin_cambios.txt`): el mismo binario compilado con el `torneo.c` del repositorio (`9b82e81`) y con el actual da 11 salidas idénticas byte a byte, con comandos que el estudio no usó (campo ingenuo con G = 15, campo fuerte con la semilla 1, vista de parada, estrategias de los tres estudios, un duelo contra `ejec:m=8`). `../mediciones/hipotesis_s0.txt` y `rivales.txt`, generados de nuevo sin reescribirlos, son idénticos a los versionados. `torneo.c` tiene 52 líneas agregadas y 2 cambiadas; los otros seis archivos del núcleo no cambiaron y la huella sigue siendo `76399e005fd4ed8`.
- `make repetir` (`mediciones/repeticion.txt`): se volvieron a correr con el Makefile de cada carpeta `validar`, `cota`, `descomposicion` y `practica` del estudio 3, `prueba`, `cota`, `tablas` y `bytes` del 4B, `causal`, `equivalencia` y `tamanos` del 4C y `prueba`, `campos` y `tablas` del cierre. Los 99 archivos de sus `mediciones/` quedaron idénticos. Sus binarios se recompilaron contra el núcleo actual, así que esto también muestra que los campos nuevos no mueven esas salidas.

## 7. Percentil 5

El criterio de corte pide además que el percentil 5 de la competencia de tres rondas no baje. El arnés lo estima con un error unas 2,8 veces mayor que el real, lo que vuelve blanda esa condición. Se rehízo con el sorteo propio del evaluador independiente y error por lotes (`independiente_s*.txt`, claves `dp5a3_mm` y `dp5b3_mm`, campo mixto). `ejec_a` contra `max_media`: +0,011 ± 0,001 / +0,011 ± 0,001 con H3a y +0,050 ± 0,002 / +0,025 ± 0,002 con H3b a 2000 ticks, y positivo también a 20 000 con interiores y con parada. Su veredicto no depende de esa blandura. Los fondos fallan por la media, no por el percentil 5.

## 8. Punto 4: las cotas

`make cotas` (`mediciones/cotas.txt`). Semilla 0, diferencias contra `max_media`, campo mixto.

| Cota | Informado | Obtenido |
|------|-----------|----------|
| Límite de 126 por orden: patrimonio en el remuestreo, H3a y H3b en evidencia, 2000 ticks | +103 ± 5, +0,033 y +0,069 | +103,1 ± 5,0, +0,0330 y +0,0698 |
| Límite de 252 | +117 ± 6, +0,035 y +0,072 | +116,5 ± 6,1, +0,0354 y +0,0727 |
| Sin límite | +120 ± 8, +0,036 y +0,073 | +120,1 ± 8,1, +0,0357 y +0,0730 |
| Sin límite, 20 000 ticks: interiores y parada, H3a y H3b | +0,048 y +0,086; +0,042 y +0,081 | +0,0467 y +0,0866; +0,0409 y +0,0801 |
| Oráculo que elige el mejor gestor de cada serie, conjunto 1 (`max_media`, `prudente`, comprar y mantener), 2000 ticks | +0,341 ± 0,005 y +0,332 ± 0,005 | +0,3417 ± 0,0050 y +0,3315 ± 0,0045 |
| Oráculo, conjunto 3 (`max_media`, `kalman`, `activo`): 2000 ticks; 20 000 interiores | +0,152 y +0,185; +0,079 y +0,104 | +0,1523 y +0,1855; +0,0793 y +0,1049 |
| Oráculo, conjunto 4 (`max_media`, `base`, `prudente`), 2000 ticks | +0,167 y +0,202 | +0,1676 y +0,2013 |
| Mezcla fija 3/8, 3/8, 2/8 del conjunto 3: 2000 ticks; 20 000 interiores | +0,005 y +0,019; +0,008 y +0,027 | +0,0049 y +0,0191; +0,0078 y +0,0271 |

El oráculo del conjunto 2 no se recalculó (lleva la guardia, que no se reescribió). El oráculo del estudio de aprendizaje (+0,038 y +0,064) es el promedio de dos cifras del arnés, (0,046 + 0,030) / 2 y (0,068 + 0,059) / 2: la cuenta está bien y las dos cifras de entrada no se recalcularon.

Ninguna cota se presenta como alcanzable: la de ejecución dice que evalúa "una maestra que no existe", el oráculo de selección dice "no se puede cobrar" y la mezcla fija dice que es ideal. Tres precisiones:

1. **"Sin límite" es un límite de 2^21 acciones por orden** (`../r3_ejecucion/cota/lim.c`). Con la regla sin ningún límite, reescrita aquí, las cifras de la tabla son las mismas (remuestreo, interiores, parada y puntos). Solo cambia la media de patrimonio con todas las series (13 millones contra 153 mil a 2000 ticks), que el estudio ya había descartado.
2. **La cota de ejecución no es un máximo.** Es lo que daría la misma forma de operar sin el límite. En puntos no crece siempre con el límite: a 20 000 ticks con parada el límite de 252 da +0,0447 ± 0,0014 y quitarlo da +0,0409 ± 0,0016. El título del paso 1 ("cuánto se gana como máximo") dice más que eso.
3. **La mezcla fija a 20 000 ticks vale solo con las series interiores.** Con parada, 3/8, 3/8, 2/8 da -0,0057 ± 0,0012 con H3a y +0,0112 ± 0,0015 con H3b, y la mejor mezcla por H3a entre las 45 es `max_media` sola. Además la mezcla 3/8, 3/8, 2/8 es la mejor por H3a; por H3b la mejor es 0/8, 5/8, 3/8, con +0,0228 a 2000 ticks. Las dos cosas van a favor de la conclusión del estudio: hay todavía menos para ganar con un fondo.

### Robustez del espejo

La recomendación del estudio depende de cuánto pierde `ejec:m=8` si la maestra usa otra caja u otra comisión. Se recalculó con un espejo propio, separado de la cuenta real (`cotas.txt`, claves `robustez`). Diferencia de patrimonio contra `max_media` con las mismas reglas reales, conjunto evidencia:

| Caso | Informado: 2000 ticks; 20 000 con parada | Obtenido |
|------|-------------------------------------------|----------|
| Caja real 9 000 | +0,7; +6 | +0,7; +6,3 |
| Caja real 12 000 | -21; -640 | -20,6; -640,1 |
| Caja real 20 000 | -657; -7 723 | -657,4; -7 722,7 |
| Comisión real 0 | -13; -986 | -12,8; -986,1 |

## 9. Punto 5: implementabilidad

`make aritmetica` (`mediciones/aritmetica.txt`) lista las 42 líneas de las rutinas de decisión con un producto, un cociente o un tipo de 64 bits. Clasificadas a mano:

- **`ejec:m=8`**: `63 p` (64 p - p) y `8 p` (tres sumas) en todos los ticks; un cociente `(caja - 5) / p` menor que 63 cuando la maestra recorta la compra; un producto de un resto de menos de 63 acciones por el precio al venderlo. Las demás líneas con producto son de opciones que la candidata no usa (`K`, `F`, escalones). Nada más.
- **Gestores `max_media`, `base`, `activo` y `kalman`**: solo sumas y desplazamientos por constantes. Los dos productos de `e_param.c` son de las bandas escaladas con la volatilidad, que ninguna candidata final usa.
- **`aprendiz`**: los productos y cocientes de `decidir` son entre constantes de la configuración (umbral 384, 32 casillas). Lo que opera con datos son desplazamientos por constantes (5, 10 y 12) y una lectura y una escritura de la tabla. Los productos de `tabla_iniciar` son las 32 constantes del valor inicial.
- **Supervisor del fondo**: con voto (`completo_min`) no hay productos fuera del espejo. Con posiciones parciales (`completo`): `acciones * p`, `F * W` con F de 0 a 16, `4 W`, y un cociente acotado a 63. Están declarados en los README. Los `long long` hacen falta solo si el patrimonio llega a 2^27: el mayor patrimonio final de la evidencia de 20 000 ticks con todas las series es 1 676 705.
- No hay punto flotante en ninguna.

Frecuencias medidas en el conjunto evidencia, semilla 0:

| Operación | Rondas de 2000 ticks | Rondas de 20 000 ticks |
|-----------|----------------------|------------------------|
| `ejec:m=8`: cocientes por ronda | 11,07 (0,55 % de los ticks) | 99,1 (0,50 %) |
| `ejec:m=8`: productos de un resto por ronda | 10,87 (0,54 %) | 97,3 (0,49 %) |
| `completo`: ticks con objetivo parcial | 225,8 (11,3 %) | 2 385 (11,9 %) |
| `completo_min`: ticks con objetivo parcial | 0 | 0 |
| `completo_min`: cambios de pesos por ronda | 1,88 | 23,3 |
| Ticks con el espejo distinto de la cuenta real, todas | 0 | 0 |

Las instrucciones por tick de los README son conteos a mano, sin assembly, y están marcadas como estimadas. Las sumas están bien hechas: 38 + 38 + 38 + 95 + 140 = 349 para `completo_min` y 38 + 160 + 38 + 95 + 208 = 539 para `completo`. Dos precisiones, las dos **estimadas** aquí:

1. **La versión sin saltos de `ejec:m=8` no cuesta 90 instrucciones.** Con saltos, el cociente y el producto nunca caen en el mismo tick y el peor camino son unas 90. Sin saltos que dependan de los datos, que es como está escrito hoy `trade.s`, hay que calcular los dos en todos los ticks: entre 145 y 190 instrucciones, unos 320 a 420 ciclos de los 2 262 de la ronda más rápida. Cabe igual.
2. **El camino caro del fondo con posiciones parciales no es raro**: corre en el 11 % de los ticks. El README del fondo cuenta 25 bytes con cantidad parcial en la serie de práctica; el objetivo parcial se calcula en 2 300 de sus 20 000 ticks. El presupuesto se mide en el peor tick, así que no cambia si cabe.

Que `completo` no cabe en las 512 palabras sale de una estimación de unas 620. Con un error del 20 % en esa cuenta el resultado cambia. No se pudo comprobar sin escribir el programa.

## 10. Punto 6: reglas

- Ningún fuente de estrategia trae arreglos de datos ni lee archivos (`grep` en los nueve fuentes: ningún arreglo de 6 o más constantes, y el único `fopen` es la traza de salida del fondo).
- La tabla de `aprendiz` parte de una recta que sale de E = 96, X = 0 y una pendiente: 32 valores calculados con la regla, no con la serie.
- `m = 8`, los pesos, la banda, la ventana y el margen son constantes sueltas elegidas con la semilla 0. `m = 8` sale de un promedio (10 de comisión contra 0,97 de ganancia por acción).
- `espera` usa dos constantes que salieron de mirar el remuestreo de la serie de práctica. El README de aprendizaje lo dice. No es una tabla punto a punto y está descartada.
- Las tablas de los oráculos (`cota.c` de los estudios 4B y 4C) sí salen de las series: son herramientas de medición y no están en ninguna candidata.
- El espejo usa caja 10 000 y comisión 5, que son reglas del enunciado.

## 11. Punto 7: coherencia y correcciones

Lo que se cambió en los README auditados. Cada cambio quedó marcado en el lugar y resumido en la sección "Auditoría" de cada documento.

| Dónde | Decía | Qué sostienen las tablas | Qué se hizo |
|-------|-------|--------------------------|-------------|
| `../r4_final/README.md`, sección 1 | El fondo completo no le gana a la mejor estrategia sola "con ningún campo de rivales" | No pasa el criterio en ningún campo y pierde con H3b en los cinco. Pero con H3a a 20 000 ticks queda apenas arriba con el campo ingenuo (+0,001 ± 0,001 / +0,002 ± 0,001 con parada; +0,0010 ± 0,0005 / +0,0017 ± 0,0005 con el valor exacto) y empata con el racional | Párrafo reescrito |
| `../r4_final/README.md`, secciones 1 y 9.1 | La "única cifra a su favor" es H3a con rivales racionales e interiores | También el campo ingenuo: +0,005 / +0,006 con interiores y +0,001 / +0,002 con parada. Las cifras estaban en `tablas_duelo_ejec_a_s*.md` y no en el README | Frases corregidas y dos filas del campo ingenuo agregadas a la tabla 9.1 |
| `../r4_final/README.md`, sección 9.3 | H3a a 20 000 ticks: gana `ejec_a`; con rivales racionales, empate | Falta el campo ingenuo | Celda completada |
| `../r4_final/README.md`, sección 12 | Mezcla fija: +0,008 y +0,027 a 20 000 | Es con las interiores. Con parada, -0,006 y +0,011 | Fila completada |
| `../r3_ejecucion/README.md`, sección 8.6 | Sin saltos se paga "siempre el peor caso (unas 90 instrucciones)" | Sin saltos hay que hacer el cociente y el producto en el mismo tick: 145 a 190 (estimado) | Nota agregada |

Precisiones agregadas sin cambiar el texto original: el "sin límite" de 2^21 y la cota que no es un máximo (`r3_ejecucion`, sección 5), la frecuencia del cociente y del producto en el conjunto evidencia (sección 8.6), la mezcla fija con parada y por H3b (`r4b_fondo`, sección 5), el objetivo parcial en el 11 % de los ticks (sección 10.4) y que la semilla reservada ya se usó para las candidatas de cada estudio (los tres).

Una observación que no es un error. Para elegir entre las candidatas A y B de ejecución, el cierre usa la pérdida de B con H3b a 20 000 ticks. Esa pérdida sale del mismo desempate contra el rival idéntico que el estudio 3 pide descontar al comparar A con `max_media`: B se aparta más de `max_media` y a veces termina bajo ese rival, y A casi nunca. Con H3a sola, B queda sobre A en los cinco campos, las dos semillas y las tres vistas, entre +0,003 y +0,030 puntos, con +8 de patrimonio por ronda de 2000 ticks y +92 por ronda de 20 000. Quedarse con A es una decisión de prudencia (un parámetro, ninguna celda negativa). Quedó anotado en la sección 13 del cierre.

Lo demás del resumen del cierre coincide con sus tablas: las cifras de `ejec_a` y `ejec_b`, las del fondo contra `max_media`, que lo positivo lo pone la ejecución A (`completo_s`: -0,003 y +0,005), el patrimonio a 20 000 ticks con signo distinto en las dos evidencias, el estrés (+0,0117 ± 0,0020 / +0,0131 ± 0,0020 contra `ejec_a`), los 4 veredictos que cambian entre semillas y las cuentas de equilibrio del riesgo del espejo.

## 12. Conclusiones y tabla principal vigentes

1. **La mejor estrategia sola es `max_media` con la ejecución A (`ejec:m=8`).** Pasa el criterio de corte contra `max_media` con los cinco campos de rivales, las dos semillas y los dos largos, y la vista de parada confirma. Vale +0,007 puntos de 2 con H3a con el campo mixto (+0,004 con el ingenuo, +0,015 con el racional, +0,033 a +0,043 con reversores) y +15 de patrimonio por ronda de 2000 ticks. Con H3b vale +0,027 a +0,05, casi todo por desempatar con un rival idéntico.
2. **Su riesgo es el que se informó.** Si la caja real es 12 000 pierde 21 por ronda de 2000 ticks y 640 por ronda larga; si es 20 000, 657 y 7 723 (3 % y 19 %); con comisión 0, 13 y 986. La condición de la recomendación (caja 10 000, comisión 5 y reset por ronda confirmados; si no, `max_media` sola) se mantiene.
3. **El fondo completo no le gana a `ejec:m=8`.** No pasa el criterio con ningún campo. Con H3b pierde siempre (-0,013 a -0,034 con el campo mixto, hasta -0,200 con reversores). Con H3a pierde con los campos mixto, fuerte y de reversores (-0,004 a -0,008 con el mixto) y a 2000 ticks con el racional; a 20 000 ticks empata con el racional y queda +0,001 a +0,002 arriba con el ingenuo.
4. **Contra `max_media` sin contabilidad el fondo completo no se distingue de cero con H3a** (+0,002 ± 0,001 / +0,000 ± 0,001 a 2000 ticks, -0,002 / -0,001 con parada) y gana +0,011 a +0,019 con H3b. Lo positivo lo pone la ejecución A.
5. **En patrimonio empata a 2000 ticks y gana cerca de 1 % a 20 000** (+221 ± 25 / +249 ± 26 con parada), todo en las familias del modelo (+454 / +500) y nada en el remuestreo (-12 / -1).
6. **`completo_min` es igual a `ejec:m=8` a 2000 ticks** (0,000 ± 0,000) y cuesta 0,009 a 0,012 puntos de H3a a 20 000. En el estrés largo gana +0,036 / +0,044 contra `max_media`.
7. **Las cotas no se alcanzan y la del fondo es más baja de lo informado en rondas largas**: sin el filtro de interiores la mejor mezcla fija por H3a es `max_media` sola.
8. **Los costos son estimaciones.** Nada de esto existe en assembly.
9. **Entre A y B, A es la elección prudente, no la que el torneo impone.**

Criterio de corte contra `max_media`, campo mixto, conjunto evidencia, G = 10 (dH3a; dH3b), semilla 0 / semilla 3. Cifras del arnés, reproducidas:

| Candidata | 2000 ticks | 20 000 interiores | 20 000 parada | Arnés (s0 / s3) | Con parada |
|-----------|------------|-------------------|---------------|-----------------|------------|
| `ejec_a` | +0,007 / +0,007; +0,027 / +0,027 | +0,007 / +0,006; +0,050 / +0,051 | +0,007 / +0,006; +0,048 / +0,048 | PASA / PASA | PASA / PASA |
| `ejec_b` | +0,012 / +0,011; +0,031 / +0,030 | +0,010 / +0,010; +0,041 / +0,042 | +0,011 / +0,010; +0,041 / +0,040 | PASA / PASA | PASA / PASA |
| `fondo_rec` | -0,004 / -0,005; +0,006 / +0,005 | -0,000 / -0,001; +0,016 / +0,017 | -0,008 / -0,008; +0,006 / +0,007 | NO_PASA / NO_PASA | no / no |
| `rec_e` | +0,001 / -0,000; +0,013 / +0,011 | +0,006 / +0,005; +0,024 / +0,025 | -0,003 / -0,003; +0,014 / +0,015 | NO_PASA / NO_PASA | no / no |
| `completo` | +0,002 / +0,000; +0,013 / +0,011 | +0,003 / +0,002; +0,019 / +0,019 | -0,002 / -0,001; +0,014 / +0,014 | PASA / NO_PASA | no / no |
| `completo_min` | +0,007 / +0,007; +0,026 / +0,027 | -0,005 / -0,005; +0,019 / +0,019 | -0,002 / -0,005; +0,022 / +0,020 | NO_PASA / NO_PASA | no / no |
| `fondo_min` | +0,000 / -0,000; +0,000 / -0,000 | -0,018 / -0,016; -0,003 / +0,000 | -0,019 / -0,020; -0,005 / -0,006 | NO_PASA / NO_PASA | no / no |
| `aprendiz` | -0,000 / -0,000; +0,000 / -0,000 | -0,028 / -0,028; -0,010 / -0,013 | -0,016 / -0,014; -0,002 / -0,002 | NO_PASA / NO_PASA | no / no |
| `base` | -0,038 / -0,042; -0,036 / -0,036 | -0,125 / -0,128; -0,079 / -0,084 | -0,074 / -0,078; -0,049 / -0,053 | NO_PASA / NO_PASA | no / no |

Las filas de `completo_ancla` y `espera` del README del cierre no se reprodujeron aquí (no se reescribieron) y quedan como las informó el estudio.

El fondo completo contra la mejor estrategia sola: `completo` menos `ejec_a` (dH3a; dH3b), semilla 0 / semilla 3:

| Campo | 2000 ticks | 20 000 interiores | 20 000 parada |
|-------|------------|-------------------|---------------|
| ingenuo | -0,000 / -0,001; -0,002 / -0,003 | +0,005 / +0,006; -0,002 / -0,002 | +0,001 / +0,002; -0,005 / -0,004 |
| mixto | -0,006 / -0,007; -0,013 / -0,016 | -0,004 / -0,004; -0,031 / -0,032 | -0,008 / -0,008; -0,034 / -0,034 |
| fuerte | -0,009 / -0,011; -0,051 / -0,054 | -0,005 / -0,005; -0,113 / -0,108 | -0,011 / -0,010; -0,119 / -0,120 |
| racional | -0,004 / -0,006; -0,015 / -0,015 | +0,010 / +0,012; -0,018 / -0,013 | +0,001 / +0,002; -0,024 / -0,024 |
| reversores | -0,016 / -0,016; -0,085 / -0,088 | -0,005 / -0,006; -0,190 / -0,181 | -0,019 / -0,021; -0,199 / -0,200 |

## 13. Lo que la auditoría no cubrió

- `espera`, `completo_ancla`, `completo_esp`, `completo_ap`, `fondo_ancla`, `fondo_rec_ant`, `fondo_min_ant` y `aprendiz_patron` no se reescribieron. Pasan las pruebas de causalidad, y sus cifras son las del arnés.
- Los barridos (61 variantes de ejecución, 88 del fondo, 249 de aprendizaje) no se volvieron a correr enteros. Se repitieron los objetivos baratos de cada carpeta (sección 6) y las candidatas finales.
- El percentil 5 de tres rondas se rehízo solo con el campo mixto. Los campos `fijos2` y `fijos3` no se usaron.
- La exactitud del predictor de patrones y los oráculos O1 a O3 del estudio de aprendizaje no se recalcularon.
- Las instrucciones por tick, las palabras de memoria y los días de trabajo siguen siendo estimaciones. No hay assembly.
- No se midió qué pasa con un tick perdido, con rondas seguidas sin reset ni con el espejo del fondo cuando la caja real es otra. Los estudios ya lo declaran.
- El README del arnés (`../README.md`) sigue sin nombrar la semilla 3 ni los cuatro campos nuevos, y dice 77 archivos de series (son 107). Está fuera de las carpetas de esta auditoría y no se tocó.
- Toda la evidencia sale de una serie de práctica. Eso no lo arregla ninguna semilla.

## 14. Días de trabajo, reglas, riesgos y veredicto

- **Días de trabajo para calidad de competencia.** La auditoría no cambia las estimaciones de los estudios: 0,7 días para `max_media`, 3,0 para `ejec:m=8`, 8,5 a 10 para `completo_min` y más de 11,5 para `completo`. Lo único que agrega es que la versión sin saltos de `ejec:m=8` son más instrucciones de las anotadas, sin cambiar los días.
- **Reglas del enunciado.** Esta carpeta no agrega hardware ni programa de placa. La decisión sigue calculándose en Espino en todas las candidatas, ninguna usa información externa a la serie, y no hay tablas derivadas de la serie de práctica (sección 10).
- **Riesgos.** El principal sigue siendo el del espejo: caja, comisión o reset distintos de lo supuesto. El segundo, que la evidencia sale de una sola serie. El tercero, que los rivales son un supuesto: el signo del resultado no cambia entre campos, el tamaño sí.
- **Veredicto según los criterios de corte.**

| Pieza | Veredicto después de la auditoría |
|-------|-----------------------------------|
| `max_media` con la ejecución A (`ejec:m=8`) | Pasa el criterio de algoritmo. Confirmado con otro evaluador. Competencia, con la condición de caja, comisión y reset |
| Ejecución B | Pasa contra `max_media`. Contra A no pasa por H3b, que es desempate. Decisión de prudencia |
| Fondo completo (`completo`) y fondo recomendado (`fondo_rec`, `rec_e`) | Descartados de la competencia. Confirmado |
| `completo_min` | Exhibición. Confirmado: igual a `ejec:m=8` a 2000 ticks |
| Tabla que aprende (`aprendiz`) y predictor | Descartados de la competencia. La tabla no usa información del futuro |
| Campos nuevos del arnés | No cambian ninguna salida anterior |
