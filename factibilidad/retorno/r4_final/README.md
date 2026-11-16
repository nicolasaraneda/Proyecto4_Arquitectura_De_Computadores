# Estudio de retorno 4, cierre: el fondo completo contra la mejor estrategia sola

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Tramo de factibilidad del Proyecto 4. Esta carpeta no agrega hardware ni cambia el programa de la placa. Junta en un solo binario las estrategias de los tres estudios anteriores (`../r3_ejecucion`, `../r4b_fondo` y `../r4c_aprendizaje`), arma con ellas el fondo completo y lo compara con la mejor estrategia sola, en los dos largos de ronda, bajo las tres hipótesis de puntaje, con campos de rivales más duros y con una semilla reservada que no se había mirado.

## 1. Respuesta corta

**El fondo completo no le gana a la mejor estrategia sola en puntos de torneo: no pasa el criterio de corte contra ella con ningún campo de rivales. Con los campos mixto, fuerte y de reversores pierde en los dos largos de ronda y en las dos lecturas del puntaje. Con los campos ingenuo y racional, en rondas de 20 000 ticks y solo con la lectura lineal en patrimonio, queda igual o apenas arriba (+0,001 a +0,002 puntos de 2). Sí le gana en patrimonio medio (H1 y H2) en rondas de 20 000 ticks, por cerca de 1 %, pero esa ventaja aparece solo en las familias del modelo y es cero en el remuestreo.** Las dos semillas dan lo mismo.

Este estudio pasó después por una auditoría independiente, con otro evaluador (sección 19). Las cifras se reproducen y la conclusión no cambia. La auditoría corrigió el párrafo anterior y tres frases de las secciones 1, 9 y 12, que decían más de lo que las tablas sostienen: están marcadas donde corresponde.

- La mejor estrategia sola es `max_media` con la ejecución del estudio 3 (`ejec:m=8`, aquí `ejec_a`): pasa el criterio de corte contra `max_media` en los cinco campos, con la semilla 0 y con la reservada. Con el campo mixto vale +0,007 puntos con H3a y +0,027 con H3b a 2000 ticks, y +0,006 a +0,007 y +0,048 a +0,051 a 20 000 ticks.
- El fondo completo (`completo`: los gestores y el reparto de `fondo_rec`, la tabla que aprende como cuarto gestor y la ejecución A en el supervisor) queda contra `ejec_a`, con el campo mixto y la semilla reservada, en -0,007 ± 0,001 (H3a) y -0,016 ± 0,002 (H3b) a 2000 ticks, y en -0,008 ± 0,001 y -0,034 ± 0,001 a 20 000 ticks sin seleccionar series. Con los campos más duros pierde más con H3b (hasta -0,200) y empata con H3a en el mejor de los casos (campo racional, 20 000 ticks: +0,002 ± 0,001). Las cifras a su favor son todas de H3a a 20 000 ticks: con rivales racionales, +0,012 ± 0,002 con las series interiores, que sin el filtro queda en +0,002 ± 0,001; y con el campo ingenuo, +0,006 ± 0,001 con las interiores y +0,002 ± 0,001 con parada. Con H3b pierde en los cinco campos. (Corregido en la auditoría: la versión anterior decía que la del campo racional era la única cifra a favor y no nombraba el campo ingenuo.)
- Contra `max_media` sin contabilidad, el fondo completo queda en +0,000 ± 0,001 (H3a) y +0,011 ± 0,001 (H3b) a 2000 ticks con la semilla reservada. Todo lo positivo lo pone la ejecución A: el mismo fondo sin ella da -0,003 y +0,005 (semilla 0). La estructura del fondo resta entre 0,005 y 0,007 puntos de H3a a lo que la ejecución A consigue sola.
- En patrimonio, a 20 000 ticks el fondo completo saca +249 ± 26 más que `ejec_a` (vista de parada, semilla reservada; +221 ± 25 con la semilla 0), sobre 21 700. Por evidencia: -1 ± 28 en el remuestreo y +500 ± 43 en las plausibles. A 2000 ticks empata: -1 ± 3.
- Lo que el fondo completo sí compra es protección en series de estrés en rondas largas, y la pone la tabla que aprende: +0,021 ± 0,002 (H3a) contra `max_media` en el estrés a 20 000 ticks, contra +0,007 de `ejec_a`.
- El ancla en comprar y mantener cuesta 0,03 puntos a 2000 ticks y 0,14 a 0,16 a 20 000, igual que en el estudio del fondo. A 2000 ticks sube el percentil 5 de la competencia (+0,062 ± 0,011 con H3a).
- La tabla que aprende, sola, es `max_media` a 2000 ticks y pierde 0,014 a 0,028 puntos de H3a a 20 000. La regla fija `espera` pasa a 2000 ticks y no a 20 000, con signo contrario en las dos evidencias. La semilla reservada confirma los dos resultados.
- Las expectativas escritas antes de mirar la semilla reservada se cumplieron todas (sección 8.6). De 528 diferencias de puntos comparadas entre las dos semillas, 509 coinciden dentro de dos errores.

Recomendación: para la edición de competencia, `max_media` con la ejecución A si el ayudante confirma caja inicial, comisión y reset por ronda, y `max_media` sola si no. Para la edición de exhibición, el fondo en su forma mínima con la tabla que aprende y la ejecución A (`completo_min`), que a 2000 ticks rinde lo mismo que `ejec_a` (diferencia de 0,000 ± 0,000 puntos con el campo mixto). El detalle está en la sección 13.

## 2. Qué se construyó

| Archivo | Qué es |
|---------|--------|
| `Makefile` | Un objetivo por medición. Compila `build/arnes` con el núcleo, los módulos de los tres estudios sin tocar y los dos archivos propios. |
| `fondoc.c` | Copia de `../r4b_fondo/fondo.c` con tres cambios: se registra como `fondoc`, agrega el parámetro `em` (el supervisor no manda una compra si su espejo alcanza para menos de `em` acciones) y no registra alias. Con `em=0` decide igual que `fondo`. |
| `final.c` | Estrategia `filtro` (la ejecución A puesta a la salida de cualquier estrategia sin contabilidad) y los 11 alias de las configuraciones del estudio. |
| `salidas_torneo.sh` | Lista fija de comandos del arnés cuyas salidas no deben cambiar al agregar campos. |
| `comparar_campos.py` | Los campos nuevos del arnés contra el evaluador independiente de la auditoría. |
| `pruebas.sh` | Causalidad, identidades, espejo y control negativo de las piezas propias. |
| `correr.py` | Las corridas del estudio con los comandos `hipotesis` y `veredicto` del arnés. Se niega a usar la semilla 2 y a repetir la 3. |
| `lista_final.txt` | Las candidatas y los duelos que se evalúan con la semilla reservada. Se fijó antes de mirarla. |
| `tablas.py`, `resumen.py` | Tablas en Markdown. No evalúan: leen lo que deja `correr.py`. |
| `mediciones/` | Todas las salidas. `mediciones/resumen.md` trae las dos semillas lado a lado y es la fuente de las tablas de este documento. |

Fuera de esta carpeta se cambiaron dos archivos, los dos que el estudio tenía que cambiar:

- `../nucleo/torneo.c`: cuatro campos de rivales más (sección 4). 52 líneas agregadas y 2 cambiadas. No entra en la huella del núcleo, que sigue siendo `76399e005fd4ed8`, así que los resultados guardados en `../build/resultados` siguen valiendo.
- `../generar_series.py`: la semilla 3 (una línea, más el comentario).

Además se cerró `../r4c_aprendizaje`, que había quedado sin informe final: su `make todo` había terminado bien, su README ya traía las cifras de la última etapa y solo faltaba dejarlo anotado en su `AVANCE.md`. No hubo que corregir ninguna cifra.

Los tres módulos ajenos compilan juntos sin modificar nada. La copia `fondoc.c` existe porque la ejecución A dentro del fondo tiene que ir en el supervisor: un filtro por fuera dejaría el espejo del supervisor distinto de la cuenta real.

## 3. Cómo se reproduce cada número

Desde esta carpeta, con las series del arnés generadas (`make -C .. series`, que ahora incluye la semilla 3) y sus resultados guardados (`make -C .. exploracion`). Para `make campos` hace falta además `../build/auditoria/estudio_s0.txt` (`make -C ../auditoria estudio`).

| Comando | Qué hace | Salida en `mediciones/` | Tiempo medido |
|---------|----------|-------------------------|---------------|
| `make` | Compila `build/arnes`. | | segundos |
| `make sin-cambios` | Compila el mismo binario con el `torneo.c` anterior (sacado del repositorio, versión `9b82e81`) y con el actual, corre 10 comandos con los dos y compara byte a byte. Repite `make -C .. validar-torneo`. | `sin_cambios.txt` | 1 min 5 s |
| `make campos` | Campos nuevos contra el evaluador independiente, y sus pesos. | `campos_contra_independiente.txt`, `campos_pesos.txt` | 18 s |
| `make prueba` | Comprobaciones de `fondoc` y `filtro`. | `prueba.txt` | 16 s |
| `make exploracion` | Las 19 configuraciones con la semilla 0: tres vistas y cinco campos. | `hipotesis_exploracion_s0_*.txt`, `tablas_exploracion_s0.md` | 13 min 33 s |
| `make final-0` | La lista final con la semilla 0: veredicto oficial de cada candidata y duelos contra `ejec_a`. | `veredictos_s0.txt`, `hipotesis_duelo_ejec_a_s0_*.txt`, `tablas_final_s0.md`, `tablas_duelo_ejec_a_s0.md` | 6 min 36 s |
| `make reservada` | Lo mismo con la semilla 3. Se corrió una vez. Para reproducir las cifras: `make reservada REPETIR=1`. | `reservada_usada.txt`, `hipotesis_final_s3_*.txt`, `veredictos_s3.txt`, `hipotesis_duelo_ejec_a_s3_*.txt`, `tablas_final_s3.md`, `tablas_duelo_ejec_a_s3.md`, `resumen.md` | 12 min 8 s |
| `make tablas` | Todas las tablas y el resumen, sin evaluar. | `tablas_*.md`, `resumen.md` | segundos |
| `make todo` | Todo menos `reservada` y `tablas`. | | 21 min 31 s como un solo comando |

`HILOS` vale 5. Las corridas van una tras otra.

Las cifras de este documento salen de `mediciones/resumen.md` (las dos semillas lado a lado), de `mediciones/tablas_exploracion_s0.md` (las 19 configuraciones) y de `mediciones/tablas_final_s3.md` (todo el detalle de la semilla reservada: H1, H2, H3a y H3b, media, percentil 5 y diferencia con su error, en evidencia y en estrés, con los campos mixto, fuerte, racional y reversores, y la competencia de tres rondas).

## 4. Campos de rivales más duros

La auditoría del arnés había mostrado que el campo mixto es optimista (la mitad de sus rivales pierde en la serie de práctica) y definió cuatro campos más, que solo existían en su evaluador independiente (`../auditoria/indep.c`). Este estudio los agregó a `../nucleo/torneo.c`, para que cualquier estrategia de afuera se evalúe contra ellos con los comandos de siempre:

| Campo | Cómo se arma |
|-------|--------------|
| `racional` | Cualquier rival que no pierde en la serie de práctica completa y que no opera al azar: 22 reversiones de distinta calidad y no operar, 23 rivales con la misma probabilidad. |
| `reversores` | Los diez rivales traen una de las tres mejores reversiones (la regla base, `max_media` y la suma móvil de 64). |
| `fijos2` | El campo mixto, pero dos de los diez rivales son siempre la regla base y `max_media`. |
| `fijos3` | Lo mismo con tres: además la suma móvil de 64. |

Se piden con `--campo racional` en `hipotesis` y `veredicto`, o con la variable `RETORNO_CAMPO` en cualquier comando (por ejemplo `RETORNO_CAMPO=racional build/arnes rivales` muestra sus pesos). `torneo.h` y `main.c` no se tocaron: la tabla de pesos sigue teniendo tres filas, y el campo pedido ocupa en esa corrida la fila del mixto. Por eso la tabla de sensibilidad de `hipotesis` muestra entonces ingenuo, el campo pedido y fuerte. Un aviso de uso: `main.c` sigue diciendo "campo desconocido (ingenuo, mixto o fuerte)" si el nombre está mal escrito.

Comprobaciones:

- **Nada de lo anterior cambia** (`make sin-cambios`, `mediciones/sin_cambios.txt`). Diez salidas (`rivales`, dos `hipotesis` con sus `.tsv`, cuatro `veredicto` con estrategias del núcleo y de afuera en los tres campos originales, y un `hipotesis` con estrategias de afuera) son idénticas byte a byte con el `torneo.c` anterior y con el actual. `make -C .. validar-torneo` deja `../mediciones/validacion_torneo.txt` idéntico al versionado y termina en PASS.
- **Los campos nuevos dan lo mismo que el evaluador independiente** (`make campos`, `mediciones/campos_contra_independiente.txt`). Para `base` y `max_media`, con la semilla 0, G = 10, a 2000 ticks y a 20 000 con las interiores: 80 cifras comparadas (puntos esperados de cada una, su diferencia pareada y el percentil 5 de tres rondas), ninguna fuera de tolerancia. En las 48 de puntos esperados la diferencia mediana es 0,0006 y la máxima 0,0019. El evaluador independiente calcula el valor esperado exacto y el arnés sortea 6 campos por serie, así que no pueden coincidir al último decimal.

Cuánto cambia el nivel: `max_media` saca 1,50 puntos con H3a a 2000 ticks en el campo mixto, 1,42 en el fuerte, 1,20 en el racional y 1,07 con todos los rivales reversores (semilla reservada).

## 5. La semilla 3

`../generar_series.py` genera ahora la semilla 3 a los dos largos: 30 archivos más, con las mismas cantidades que las otras semillas. Los 77 archivos anteriores no cambiaron: sus líneas en `../build/series/MANIFIESTO.txt` (tamaño y huella) son las mismas de antes. La semilla 2 ya se había usado para los candidatos del núcleo, así que la reservada de este estudio es la 3.

Se usó una sola vez, el 14/11 a las 21:38 (`mediciones/reservada_usada.txt`), con la lista de `lista_final.txt`, que se había fijado a las 21:31 con los resultados de la semilla 0. Antes de correrla se escribió qué se esperaba ver (`AVANCE.md`). Después de mirarla no se cambió ninguna candidata ni ningún parámetro, y no se eligió nada con ella. Lo único que se tocó después en `lista_final.txt` fue el texto de una línea de comentario, y quedó anotado en el mismo archivo de la marca.

## 6. Las configuraciones

Todas se fijaron antes de correr nada, a partir de lo que recomienda cada estudio. No hubo barrido.

| Nombre | Especificación | Qué es |
|--------|----------------|--------|
| `ejec_a` | `ejec:m=8` | La ejecución recomendada por el estudio 3: `max_media` con contabilidad propia, que no manda una compra de menos de 8 acciones. |
| `ejec_b` | `ejec:m=8,m2=24,e2=32` | La candidata B del estudio 3: además, el resto de menos de 24 acciones solo un punto más abajo. |
| `espera`, `aprendiz`, `aprendiz_patron` | (estudio de aprendizaje) | La regla fija de espera, la tabla que aprende y el predictor de patrones como filtro. |
| `fondo_rec`, `fondo_min`, `fondo_ancla` | (estudio del fondo) | El fondo recomendado, el mínimo y el de ancla. |
| `espera_e` | `filtro:x=cand:espera,m=8` | `espera` con la ejecución A. |
| `rec_e` | `fondoc:c=3,w0=8,w1=4,w2=4,b=4,em=8` | `fondo_rec` con la ejecución A en el supervisor. Es el fondo completo sin el gestor experimental. |
| `min_e` | `fondoc:c=5,w0=6,w1=5,w2=5,m=2,v=9,mg=5,d=4,pp=1,vt=8,em=8` | `fondo_min` con la ejecución A. |
| **`completo`** | `fondoc:c=3,x=cand:aprendiz,w0=6,w1=3,w2=3,w3=4,b=4,em=8` | **El fondo completo**: gestores `max_media`, `kalman` y `activo` con pesos fijos y banda de no operar de 4/16 (lo que recomienda el estudio del fondo), la tabla que aprende como cuarto gestor en papel con pesos 6/3/3/4 (los que fijó el estudio de aprendizaje) y la ejecución A en el supervisor. |
| `completo_s` | lo mismo sin `em` | Para separar lo que pone la ejecución. |
| `completo_esp` | lo mismo con `x=cand:espera` | Con la regla `espera` de cuarto gestor. |
| `completo_ap` | `completo` con `m=2,v=9,mg=6,d=4` | Los pesos se aprenden alrededor de 6/3/3/4 según el desempeño en papel: ventana de 512 ticks, margen 1/64, a lo más 4/16 de distancia del prior. Es la versión literal de "reparto según desempeño en papel con prior fuerte". |
| `completo_ancla` | `fondoc:c=1,x=cand:aprendiz,w0=10,w1=2,w2=2,w3=2,b=2,em=8` | Con ancla en comprar y mantener: `max_media`, `prudente`, comprar y mantener y `aprendiz`. |
| `completo_min` | `fondoc:c=5,x=cand:aprendiz,w0=4,w1=4,w2=4,w3=4,m=2,v=9,mg=5,d=4,pp=1,vt=8,em=8` | El fondo mínimo (voto, puntaje por acción, pesos aprendidos) con `aprendiz` de cuarto gestor y la ejecución A. |

Como cuarto gestor del fondo completo se puso `aprendiz` y no `espera` porque es la pieza que de verdad aprende en vivo, que es lo que se quería evaluar. `espera` es una regla fija. La variante con `espera` se midió igual (`completo_esp`) y es peor.

Comprobaciones de las piezas propias (`make prueba`, `mediciones/prueba.txt`, todo en PASS):

| Prueba | Resultado |
|--------|-----------|
| Causalidad (comando `causal`) de las 10 configuraciones nuevas | 78 comparaciones cada una, 0 fallas |
| `fondoc` con `em=0` contra `fondo`: 5 configuraciones, 10 lotes de la semilla 0 de los dos largos y la serie de práctica | 14 800 series cada una, 0 distintas, y la práctica idéntica byte a byte |
| `filtro` sobre `max_media` con m = 8, y `fondoc` con todo el peso en `max_media` y `em=8` (con y sin voto), contra `ejec:m=8` | 14 800 series cada una, 0 distintas, práctica idéntica byte a byte |
| Espejo del supervisor contra la cuenta real cuando el supervisor suprime compras, 5 configuraciones | 0 ticks distintos en 14 800 series |
| Control negativo: `rec_e` contra `fondo_rec` y `completo` contra `completo_s` | 10 709 y 11 037 series distintas de 14 800 |

## 7. Exploración con la semilla 0

`make exploracion`, `mediciones/tablas_exploracion_s0.md`. Diferencias pareadas contra `max_media`, conjunto evidencia, campo mixto, G = 10. `max_media` saca 10 982 de patrimonio y 1,503 (H3a) y 1,473 (H3b) puntos a 2000 ticks, 1,855 y 1,821 a 20 000 con las interiores y 1,721 y 1,708 con parada. La última columna dice en cuántos de los 7 campos (ingenuo, mixto, fuerte, fijos2, fijos3, racional y reversores) la candidata pasa el criterio de corte y además la vista de parada confirma el signo.

| Configuración | 2000: H1 | 2000: H3a, H3b | 20 000 interiores: H3a, H3b | 20 000 parada: H1 | 20 000 parada: H3a, H3b | Pasa en |
|---------------|----------|----------------|------------------------------|-------------------|--------------------------|---------|
| `base` | -103 ± 10 | -0,038, -0,036 | -0,125, -0,079 | -1 899 ± 74 | -0,074, -0,049 | 0 de 7 |
| `kalman` | +20 ± 6 | -0,005, +0,004 | -0,014, +0,011 | +304 ± 37 | -0,011, +0,009 | 0 de 7 |
| **`ejec_a`** | +15 ± 0 | +0,007, +0,027 | +0,007, +0,050 | +128 ± 2 | +0,007, +0,048 | 7 de 7 |
| **`ejec_b`** | +24 ± 1 | +0,012, +0,031 | +0,010, +0,041 | +220 ± 4 | +0,011, +0,041 | 7 de 7 |
| `espera` | +37 ± 7 | +0,005, +0,017 | -0,021, +0,009 | +380 ± 49 | -0,000, +0,025 | 1 de 7 |
| `aprendiz` | -2 ± 1 | -0,000, +0,000 | -0,028, -0,010 | -135 ± 34 | -0,016, -0,002 | 0 de 7 |
| `aprendiz_patron` | +1 ± 1 | -0,001, -0,001 | -0,008, -0,000 | +40 ± 13 | -0,004, +0,002 | 0 de 7 |
| `espera_e` | +50 ± 7 | +0,012, +0,025 | -0,014, +0,016 | +490 ± 49 | +0,006, +0,032 | 1 de 7 |
| `fondo_rec` | +6 ± 4 | -0,004, +0,006 | -0,000, +0,016 | +284 ± 25 | -0,008, +0,006 | 1 de 7 |
| `fondo_min` | +1 ± 1 | +0,000, +0,000 | -0,018, -0,003 | +296 ± 50 | -0,019, -0,005 | 0 de 7 |
| `fondo_ancla` | -165 ± 13 | -0,031, -0,020 | -0,135, -0,076 | -3 227 ± 63 | -0,157, -0,091 | 0 de 7 |
| `rec_e` | +16 ± 4 | +0,001, +0,013 | +0,006, +0,024 | +388 ± 26 | -0,003, +0,014 | 3 de 7 |
| `min_e` | +16 ± 1 | +0,008, +0,027 | -0,010, +0,019 | +437 ± 50 | -0,011, +0,019 | 2 de 7 |
| **`completo`** | +12 ± 3 | +0,002, +0,013 | +0,003, +0,019 | +349 ± 25 | -0,002, +0,014 | 3 de 7 |
| `completo_s` | +4 ± 3 | -0,003, +0,005 | -0,003, +0,012 | +260 ± 25 | -0,007, +0,007 | 1 de 7 |
| `completo_esp` | +5 ± 4 | -0,004, +0,004 | +0,000, +0,016 | +350 ± 24 | -0,004, +0,009 | 1 de 7 |
| `completo_ap` | +10 ± 3 | -0,000, +0,010 | -0,006, +0,007 | +358 ± 35 | -0,010, +0,001 | 2 de 7 |
| `completo_ancla` | -165 ± 13 | -0,031, -0,020 | -0,141, -0,080 | -3 284 ± 64 | -0,161, -0,093 | 0 de 7 |
| `completo_min` | +14 ± 1 | +0,007, +0,026 | -0,005, +0,019 | +289 ± 38 | -0,002, +0,022 | 3 de 7 |

El error de las diferencias de puntos es 0,000 a 0,001 en `ejec_a` y `ejec_b`, 0,003 a 0,004 en `base` y 0,001 a 0,003 en las demás.

Qué se ve con la semilla 0:

1. **Las únicas que pasan en los 7 campos son las dos de ejecución.** Ningún fondo pasa con el campo mixto, con el fuerte ni con los de rivales fijos.
2. **Lo positivo de los fondos lo pone la ejecución A.** `fondo_rec` pasa de -0,004 y +0,006 a +0,001 y +0,013 al agregarla, `completo_s` de -0,003 y +0,005 a +0,002 y +0,013, y `fondo_min` de 0,000 a +0,008 y +0,027, que es lo que saca `ejec_a` sola.
3. **El cuarto gestor no aporta en evidencia.** `completo` y `rec_e` se diferencian en 0,000 a 0,005 puntos, y donde difieren gana `rec_e`. Con `espera` de cuarto gestor el fondo empeora (-0,004 y +0,004 a 2000 ticks).
4. **Aprender los pesos no ayuda** (`completo_ap`): -0,006 y +0,007 a 20 000 ticks contra +0,003 y +0,019 con los pesos fijos.
5. **El ancla da lo mismo con o sin las piezas nuevas**: `completo_ancla` y `fondo_ancla` coinciden a 0,006 puntos.
6. **Con los campos racional y reversores los fondos sí pasan contra `max_media`** (`completo`: +0,010 y +0,020 a 2000 ticks y +0,017 y +0,027 a 20 000 con parada, campo racional). No es que el fondo mejore: en esos campos casi todos los rivales son reversiones, las diferencias chicas entre reglas parecidas valen más, y `ejec_a` sube igual o más (+0,015 y +0,036, +0,016 y +0,050).

## 8. Resultado con la semilla reservada

`mediciones/resumen.md`. Cada celda trae la semilla 0 y la semilla 3, separadas por una barra. Diferencias pareadas contra `max_media`, conjunto evidencia, G = 10.

### 8.1 Criterio de corte, campo mixto

`max_media` saca 1,503 / 1,499 (H3a) y 1,473 / 1,464 (H3b) a 2000 ticks; 1,855 / 1,864 y 1,821 / 1,826 a 20 000 con las interiores; 1,721 / 1,717 y 1,708 / 1,704 con parada.

| Candidata | 2000: dH3a | 2000: dH3b | 20 000 interiores: dH3a | 20 000 interiores: dH3b | 20 000 parada: dH3a | 20 000 parada: dH3b | Veredicto del arnés (s0 / s3) | Con parada (s0 / s3) |
|-----------|-----------|-----------|-------------------------|-------------------------|---------------------|---------------------|-------------------------------|----------------------|
| `ejec_a` | +0,007 / +0,007 | +0,027 / +0,027 | +0,007 / +0,006 | +0,050 / +0,051 | +0,007 / +0,006 | +0,048 / +0,048 | PASA / PASA | PASA / PASA |
| `ejec_b` | +0,012 / +0,011 | +0,031 / +0,030 | +0,010 / +0,010 | +0,041 / +0,042 | +0,011 / +0,010 | +0,041 / +0,040 | PASA / PASA | PASA / PASA |
| `fondo_rec` | -0,004 / -0,005 | +0,006 / +0,005 | -0,000 / -0,001 | +0,016 / +0,017 | -0,008 / -0,008 | +0,006 / +0,007 | NO_PASA / NO_PASA | no / no |
| `rec_e` | +0,001 / -0,000 | +0,013 / +0,011 | +0,006 / +0,005 | +0,024 / +0,025 | -0,003 / -0,003 | +0,014 / +0,015 | NO_PASA / NO_PASA | no / no |
| **`completo`** | +0,002 / +0,000 | +0,013 / +0,011 | +0,003 / +0,002 | +0,019 / +0,019 | -0,002 / -0,001 | +0,014 / +0,014 | PASA / NO_PASA | no / no |
| `completo_min` | +0,007 / +0,007 | +0,026 / +0,027 | -0,005 / -0,005 | +0,019 / +0,019 | -0,002 / -0,005 | +0,022 / +0,020 | NO_PASA / NO_PASA | no / no |
| `completo_ancla` | -0,031 / -0,031 | -0,020 / -0,018 | -0,141 / -0,144 | -0,080 / -0,081 | -0,161 / -0,164 | -0,093 / -0,094 | NO_PASA / NO_PASA | no / no |
| `fondo_min` | +0,000 / -0,000 | +0,000 / -0,000 | -0,018 / -0,016 | -0,003 / +0,000 | -0,019 / -0,020 | -0,005 / -0,006 | NO_PASA / NO_PASA | no / no |
| `espera` | +0,005 / +0,004 | +0,017 / +0,019 | -0,021 / -0,026 | +0,009 / +0,007 | -0,000 / -0,002 | +0,025 / +0,023 | NO_PASA / NO_PASA | no / no |
| `aprendiz` | -0,000 / -0,000 | +0,000 / -0,000 | -0,028 / -0,028 | -0,010 / -0,013 | -0,016 / -0,014 | -0,002 / -0,002 | NO_PASA / NO_PASA | no / no |
| `base` | -0,038 / -0,042 | -0,036 / -0,036 | -0,125 / -0,128 | -0,079 / -0,084 | -0,074 / -0,078 | -0,049 / -0,053 | NO_PASA / NO_PASA | no / no |

Errores: 0,000 a 0,001 en `ejec_a` y `ejec_b`; 0,001 a 0,002 en los fondos, `espera` y `aprendiz`; 0,003 a 0,004 en `base`.

- "Veredicto del arnés" es el del comando oficial `veredicto --parada` (`mediciones/veredictos_s0.txt` y `veredictos_s3.txt`). "Con parada" exige además que la fila de parada tenga el mismo signo que la de interiores.
- El veredicto literal (solo signos) pasa para `ejec_a`, `ejec_b` y `completo` con las dos semillas, y para `rec_e` con la semilla 0.
- `completo` es el único caso en el borde: el arnés lo da PASA con la semilla 0 (+0,002 ± 0,001 con H3a a 2000 ticks) y NO_PASA con la reservada (+0,000 ± 0,001). Con las dos, la vista de parada tiene H3a negativo, así que la mejora a 20 000 ticks viene del filtro de interiores. No pasa.
- Las cifras de las tablas de este estudio se leen de los `.tsv` del comando `hipotesis`. Se comprobó contra el comando oficial: 264 cifras por semilla, 0 distintas al tercer decimal, y los 11 veredictos iguales.

### 8.2 Veredicto final por campo (semilla 0 / semilla 3)

PASA significa que pasa el criterio de corte con ese campo y que la vista de parada confirma el signo.

| Candidata | ingenuo | mixto | fuerte | racional | reversores |
|-----------|---------|-------|--------|----------|------------|
| `ejec_a` | PASA / PASA | PASA / PASA | PASA / PASA | PASA / PASA | PASA / PASA |
| `ejec_b` | PASA / PASA | PASA / PASA | PASA / PASA | PASA / PASA | PASA / PASA |
| `fondo_rec` | PASA / no | no / no | no / no | no / no | no / no |
| `rec_e` | PASA / PASA | no / no | no / no | PASA / PASA | PASA / no |
| `completo` | PASA / PASA | no / no | no / no | PASA / PASA | PASA / PASA |
| `completo_min` | PASA / PASA | no / no | no / no | PASA / PASA | PASA / no |
| `espera` | no / no | no / no | no / no | PASA / no | no / no |
| `aprendiz`, `fondo_min`, `completo_ancla`, `base` | no / no | no / no | no / no | no / no | no / no |

De 55 veredictos (11 candidatas y 5 campos), 4 cambian entre las dos semillas, todos de candidatas que estaban en el borde: pasaban con la semilla 0 y no con la reservada.

### 8.3 Campos más duros

Diferencia contra `max_media` de las tres candidatas principales. H3a y H3b, semilla 0 / semilla 3.

| Campo | Candidata | 2000 ticks | 20 000 interiores | 20 000 parada |
|-------|-----------|------------|-------------------|---------------|
| fuerte | `ejec_a` | +0,010 / +0,010 y +0,081 / +0,081 | +0,011 / +0,011 y +0,174 / +0,177 | +0,010 / +0,010 y +0,163 / +0,162 |
| fuerte | `fondo_rec` | -0,006 / -0,008 y +0,015 / +0,013 | +0,002 / +0,001 y +0,053 / +0,059 | -0,011 / -0,010 y +0,024 / +0,025 |
| fuerte | `completo` | +0,001 / -0,001 y +0,030 / +0,027 | +0,006 / +0,006 y +0,062 / +0,069 | -0,001 / -0,000 y +0,043 / +0,043 |
| racional | `ejec_a` | +0,015 / +0,015 y +0,036 / +0,034 | +0,018 / +0,017 y +0,054 / +0,054 | +0,016 / +0,015 y +0,050 / +0,049 |
| racional | `fondo_rec` | +0,002 / +0,001 y +0,009 / +0,008 | +0,023 / +0,024 y +0,031 / +0,034 | +0,006 / +0,007 y +0,014 / +0,013 |
| racional | `completo` | +0,010 / +0,009 y +0,020 / +0,018 | +0,028 / +0,030 y +0,036 / +0,041 | +0,017 / +0,018 y +0,027 / +0,025 |
| reversores | `ejec_a` | +0,034 / +0,033 y +0,131 / +0,129 | +0,049 / +0,048 y +0,291 / +0,293 | +0,043 / +0,042 y +0,270 / +0,269 |
| reversores | `fondo_rec` | -0,001 / +0,001 y +0,024 / +0,021 | +0,029 / +0,029 y +0,086 / +0,094 | -0,001 / -0,005 y +0,042 / +0,042 |
| reversores | `completo` | +0,018 / +0,017 y +0,046 / +0,041 | +0,044 / +0,042 y +0,101 / +0,112 | +0,023 / +0,020 y +0,071 / +0,069 |

Los H3b grandes de `ejec_a` con los campos fuerte y reversores (hasta +0,29) son, en buena parte, desempate: en esos campos `max_media` es uno de los rivales con peso de 20 % y 33 %, y una candidata que es `max_media` más unos pocos pesos le gana casi siempre el medio puesto del empate. El estudio 3 lo midió. La cifra para decidir es la de H3a.

### 8.4 H1 y H2: patrimonio y exceso sobre comprar y mantener

La diferencia de H2 en pesos es la misma de H1, porque comprar y mantener es igual para todos en cada serie. Se informa además la razón W/B&H. `max_media` saca 10 982 / 10 926 de patrimonio medio a 2000 ticks, con percentil 5 de 8 754 / 8 732.

| Candidata | 2000: dH1 | 2000: razón | 20 000 interiores: dH1 | 20 000 parada: dH1 | 20 000 parada: razón | p5 de H1 a 2000 |
|-----------|-----------|-------------|------------------------|--------------------|-----------------------|-----------------|
| `ejec_a` | +15 ± 0 / +14 ± 0 | +0,002 / +0,002 | +176 ± 3 / +176 ± 3 | +128 ± 2 / +127 ± 2 | +0,028 / +0,029 | 8 781 / 8 742 |
| `ejec_b` | +24 ± 1 / +22 ± 1 | +0,003 / +0,003 | +290 ± 7 / +296 ± 8 | +220 ± 4 / +218 ± 4 | +0,055 / +0,056 | 8 815 / 8 782 |
| `fondo_rec` | +6 ± 4 / +7 ± 3 | -0,001 / +0,003 | +520 ± 43 / +588 ± 48 | +284 ± 25 / +305 ± 28 | +0,033 / +0,028 | 8 756 / 8 722 |
| `rec_e` | +16 ± 4 / +15 ± 3 | +0,001 / +0,004 | +662 ± 44 / +736 ± 49 | +388 ± 26 / +408 ± 28 | +0,057 / +0,052 | 8 769 / 8 742 |
| **`completo`** | +12 ± 3 / +13 ± 3 | +0,000 / +0,004 | +550 ± 43 / +628 ± 46 | +349 ± 25 / +376 ± 26 | +0,060 / +0,058 | 8 772 / 8 753 |
| `completo_min` | +14 ± 1 / +16 ± 2 | +0,002 / +0,004 | +478 ± 69 / +476 ± 69 | +289 ± 38 / +258 ± 37 | +0,017 / +0,006 | 8 781 / 8 741 |
| `completo_ancla` | -165 ± 13 / -181 ± 6 | -0,030 / -0,029 | -3 841 ± 103 / -3 909 ± 99 | -3 284 ± 64 / -3 343 ± 64 | -1,079 / -1,126 | 8 700 / 8 679 |
| `fondo_min` | +1 ± 1 / +1 ± 1 | +0,000 / -0,000 | +602 ± 86 / +575 ± 91 | +296 ± 50 / +222 ± 49 | -0,010 / -0,040 | 8 752 / 8 730 |
| `espera` | +37 ± 7 / +46 ± 7 | +0,008 / +0,010 | +215 ± 82 / +134 ± 82 | +380 ± 49 / +330 ± 48 | +0,237 / +0,215 | 8 836 / 8 844 |
| `aprendiz` | -2 ± 1 / +3 ± 2 | +0,001 / +0,003 | -298 ± 57 / -332 ± 58 | -135 ± 34 / -126 ± 34 | -0,029 / -0,026 | 8 749 / 8 733 |
| `base` | -103 ± 10 / -97 ± 9 | -0,002 / -0,005 | -3 278 ± 124 / -3 297 ± 115 | -1 899 ± 74 / -1 898 ± 72 | -0,226 / -0,267 | 8 875 / 8 842 |

- **Bajo H1 y H2, a 20 000 ticks, los fondos con `kalman` y `activo` tienen más patrimonio medio que las candidatas de ejecución**: `completo` +349 / +376 y `rec_e` +388 / +408 contra +128 / +127 de `ejec_a` y +220 / +218 de `ejec_b` (parada). A 2000 ticks no: +12 / +13 contra +15 / +14 y +24 / +22.
- El percentil 5 del patrimonio a 2000 ticks casi no se mueve: entre 8 722 y 8 782 para las candidatas de ejecución y los fondos sin ancla, contra 8 732 de `max_media` (semilla reservada). `espera` lo sube a 8 844 y el ancla lo baja a 8 679, porque comprar y mantener pierde en las series que caen.

### 8.5 Estrés y competencia de tres rondas

Conjunto de estrés, diferencia de puntos contra `max_media`, campo mixto, H3a y H3b (semilla 0 / semilla 3). A 20 000 ticks se usa la vista de parada, porque las interiores casi no dejan series de estrés.

| Candidata | 2000 ticks | 20 000 ticks, parada |
|-----------|------------|----------------------|
| `ejec_a` | +0,006 / +0,006 y +0,025 / +0,024 | +0,006 / +0,007 y +0,033 / +0,033 |
| `ejec_b` | +0,010 / +0,009 y +0,026 / +0,024 | +0,009 / +0,009 y +0,028 / +0,026 |
| `fondo_rec` | -0,000 / +0,002 y +0,010 / +0,013 | -0,001 / -0,002 y +0,005 / +0,002 |
| `rec_e` | +0,004 / +0,006 y +0,018 / +0,019 | +0,004 / +0,004 y +0,014 / +0,012 |
| `completo` | +0,006 / +0,006 y +0,021 / +0,022 | +0,018 / +0,021 y +0,026 / +0,027 |
| `completo_min` | +0,007 / +0,007 y +0,025 / +0,024 | +0,036 / +0,044 y +0,047 / +0,054 |
| `completo_ancla` | +0,029 / +0,030 y +0,054 / +0,052 | -0,047 / -0,047 y +0,000 / +0,007 |
| `aprendiz` | +0,003 / +0,003 y +0,003 / +0,004 | +0,039 / +0,048 y +0,042 / +0,049 |
| `espera` | -0,020 / -0,018 y -0,014 / -0,009 | -0,027 / -0,025 y -0,005 / -0,005 |

Competencia de tres rondas, campo mixto: media de los puntos y percentil 5 del promedio de las tres rondas (niveles; semilla 0 / semilla 3). La media de la competencia es la de una ronda.

| Candidata | 2000, H3a: media, p5 | 2000, H3b: media, p5 | 20 000 parada, H3a: media, p5 | 20 000 parada, H3b: media, p5 |
|-----------|----------------------|----------------------|-------------------------------|-------------------------------|
| `max_media` | 1,503, 0,882 / 1,499, 0,871 | 1,473, 0,911 / 1,464, 0,894 | 1,721, 1,232 / 1,717, 1,209 | 1,708, 1,283 / 1,704, 1,267 |
| `ejec_a` | 1,511, 0,891 / 1,506, 0,882 | 1,500, 0,933 / 1,491, 0,933 | 1,728, 1,245 / 1,723, 1,220 | 1,756, 1,333 / 1,751, 1,333 |
| `ejec_b` | 1,515, 0,901 / 1,510, 0,891 | 1,504, 0,933 / 1,494, 0,933 | 1,732, 1,253 / 1,727, 1,224 | 1,750, 1,333 / 1,744, 1,333 |
| `fondo_rec` | 1,500, 0,887 / 1,494, 0,873 | 1,479, 0,922 / 1,469, 0,878 | 1,713, 1,238 / 1,709, 1,209 | 1,714, 1,267 / 1,710, 1,267 |
| `completo` | 1,505, 0,892 / 1,499, 0,881 | 1,487, 0,933 / 1,475, 0,911 | 1,720, 1,248 / 1,716, 1,218 | 1,722, 1,289 / 1,718, 1,267 |
| `completo_min` | 1,511, 0,892 / 1,506, 0,883 | 1,500, 0,933 / 1,491, 0,933 | 1,719, 1,244 / 1,713, 1,214 | 1,731, 1,322 / 1,724, 1,278 |
| `completo_ancla` | 1,472, 0,941 / 1,468, 0,933 | 1,453, 0,967 / 1,446, 0,933 | 1,560, 1,115 / 1,553, 1,094 | 1,615, 1,200 / 1,609, 1,167 |
| `espera` | 1,509, 0,901 / 1,503, 0,886 | 1,490, 0,906 / 1,483, 0,917 | 1,721, 1,252 / 1,715, 1,225 | 1,734, 1,311 / 1,726, 1,278 |
| `base` | 1,465, 0,835 / 1,457, 0,817 | 1,437, 0,872 / 1,428, 0,856 | 1,647, 1,141 / 1,639, 1,119 | 1,659, 1,217 / 1,651, 1,200 |

- **A 2000 ticks ninguna candidata baja el percentil 5 de la competencia en más de dos errores**, salvo `base`. El ancla es la que más lo sube (+0,058 ± 0,010 / +0,062 ± 0,011 con H3a) y es también la que más media pierde.
- A 20 000 ticks el ancla baja las dos cosas: -0,117 / -0,115 de percentil 5 con H3a en parada.
- Las mismas tablas con el campo racional, las diferencias de percentil 5 con su error y el detalle por candidata están en `mediciones/resumen.md` y `mediciones/tablas_final_s3.md`.

### 8.6 Lo que se esperaba y lo que salió

La expectativa se escribió en `AVANCE.md` antes de correr la semilla 3, candidata por candidata. Resultado:

| Se esperaba | Salió con la semilla 3 |
|-------------|------------------------|
| `ejec_a` y `ejec_b` pasan en todos los campos, con las cifras de la semilla 0 | Sí. Todas sus cifras del campo mixto quedan a 0,001 de las de la semilla 0 |
| `ejec_b` contra `ejec_a`: más H3a y más patrimonio; menos H3b a 20 000 ticks (unos 0,008) | Sí: +0,004 y +0,003 con H3a, +8 y +92 de patrimonio, -0,009 y -0,008 con H3b a 20 000 |
| `espera` pasa a 2000 y no a 20 000, con signo contrario en remuestreo y plausibles | Sí: +0,039 y -0,031 con H3a a 2000 ticks |
| `aprendiz` igual a `max_media` a 2000, peor a 20 000, mejor solo en el estrés largo | Sí: 0,000; -0,028; +0,048 en el estrés |
| `fondo_rec` no pasa: H3a cero o negativo y H3b positivo | Sí: -0,005 y +0,005 |
| `rec_e` no pasa en el mixto y pasa con racional y reversores | En el mixto y el racional, sí. Con reversores pasó con la semilla 0 y no con la 3 |
| `completo` en el borde con H3a positivo a 2000 e interiores y negativo en parada; no pasa en el mixto; pasa con racional y reversores | Sí. A 2000 ticks quedó en +0,000 ± 0,001 |
| `completo_ancla` no pasa en nada, sube el percentil 5 a 2000 ticks y gana en el estrés a 2000 | Sí |
| `fondo_min` igual a 2000 y peor en H3a a 20 000; `completo_min` como `ejec_a` a 2000 y H3a negativo a 20 000 | Sí |
| El fondo completo no le gana a `ejec_a` en puntos y sí en patrimonio medio a 20 000 ticks, con signo contrario entre remuestreo y plausibles | Sí (sección 9) |

Concordancia entre las dos semillas (`mediciones/resumen.md`, sección 3): de 528 diferencias de puntos contra `max_media` (11 candidatas, tres vistas, evidencia y estrés, H3a y H3b, cuatro campos), 509 coinciden dentro de dos errores combinados y 514 tienen el mismo juicio. La más distinta está a 2,9 errores (`ejec_b` con H3b, campo reversores, 2000 ticks: +0,128 y +0,113). En los duelos contra `ejec_a`, 231 de 240 y 220 con el mismo juicio.

## 9. El fondo completo contra la mejor estrategia sola

La mejor estrategia sola es `ejec_a`. Los duelos repiten la evaluación con `ejec_a` como referencia, pareada (`mediciones/tablas_duelo_ejec_a_s0.md`, `tablas_duelo_ejec_a_s3.md` y la sección 2 de `resumen.md`). Semilla 0 / semilla 3.

### 9.1 En puntos de torneo

Diferencia contra `ejec_a`, conjunto evidencia, H3a y H3b.

| Campo | Candidata | 2000 ticks | 20 000 interiores | 20 000 parada |
|-------|-----------|------------|-------------------|---------------|
| ingenuo | `completo` | -0,000 / -0,001 y -0,002 / -0,003 | +0,005 / +0,006 y -0,002 / -0,002 | +0,001 / +0,002 y -0,005 / -0,004 |
| ingenuo | `rec_e` | -0,000 / -0,001 y -0,002 / -0,003 | +0,007 / +0,008 y -0,000 / +0,001 | +0,001 / +0,001 y -0,005 / -0,005 |
| mixto | `completo` | -0,006 / -0,007 y -0,013 / -0,016 | -0,004 / -0,004 y -0,031 / -0,032 | -0,008 / -0,008 y -0,034 / -0,034 |
| mixto | `rec_e` | -0,006 / -0,008 y -0,014 / -0,016 | -0,001 / -0,001 y -0,026 / -0,026 | -0,009 / -0,009 y -0,034 / -0,033 |
| mixto | `completo_min` | -0,000 / +0,000 y -0,000 / -0,000 | -0,011 / -0,012 y -0,031 / -0,032 | -0,009 / -0,011 y -0,025 / -0,028 |
| mixto | `fondo_rec` | -0,011 / -0,012 y -0,021 / -0,022 | -0,007 / -0,007 y -0,034 / -0,035 | -0,015 / -0,015 y -0,042 / -0,041 |
| fuerte | `completo` | -0,009 / -0,011 y -0,051 / -0,054 | -0,005 / -0,005 y -0,113 / -0,108 | -0,011 / -0,010 y -0,119 / -0,120 |
| racional | `completo` | -0,004 / -0,006 y -0,015 / -0,015 | +0,010 / +0,012 y -0,018 / -0,013 | +0,001 / +0,002 y -0,024 / -0,024 |
| racional | `rec_e` | -0,004 / -0,005 y -0,017 / -0,015 | +0,018 / +0,020 y -0,008 / -0,004 | +0,002 / +0,003 y -0,022 / -0,023 |
| reversores | `completo` | -0,016 / -0,016 y -0,085 / -0,088 | -0,005 / -0,006 y -0,190 / -0,181 | -0,019 / -0,021 y -0,199 / -0,200 |
| reversores | `rec_e` | -0,018 / -0,014 y -0,087 / -0,088 | +0,014 / +0,014 y -0,166 / -0,163 | -0,015 / -0,018 y -0,194 / -0,194 |

Errores: 0,000 a 0,001 con el campo ingenuo, 0,001 a 0,002 en los campos mixto, fuerte y racional con H3a, 0,002 a 0,005 con H3b, y 0,004 a 0,008 con reversores. Las dos filas del campo ingenuo las agregó la auditoría: las cifras ya estaban en `mediciones/tablas_duelo_ejec_a_s0.md` y `tablas_duelo_ejec_a_s3.md`.

- **Ningún fondo pasa el criterio contra `ejec_a` en ningún campo, con ninguna de las dos semillas.**
- **A 2000 ticks el fondo completo pierde con H3a y con H3b con los campos mixto, fuerte, racional y de reversores.** Con el ingenuo empata en H3a (-0,000 / -0,001) y pierde en H3b.
- **A 20 000 ticks lo único positivo es H3a, y casi todo con las series interiores**: con el campo racional (+0,010 / +0,012 para `completo` y +0,018 / +0,020 para `rec_e`), con el ingenuo (+0,005 / +0,006 y +0,007 / +0,008) y, solo para `rec_e`, con el de reversores (+0,014 / +0,014). La vista de parada deja el campo racional en +0,001 / +0,002 y +0,002 / +0,003 (dentro de dos errores), el ingenuo en +0,001 / +0,002 y +0,001 / +0,001 (el evaluador de la auditoría da +0,0010 ± 0,0005 y +0,0017 ± 0,0005 para `completo`: 1,9 y 3,1 errores) y el de reversores en -0,015 / -0,018. Lo grande viene del filtro de interiores; lo que queda sin el filtro son uno o dos milésimos de punto con rivales ingenuos. H3b es negativo en todas las celdas menos una, `rec_e` con el campo ingenuo en las interiores, que es cero dentro del error (-0,000 / +0,001 ± 0,001). (Corregido en la auditoría: la versión anterior no nombraba el campo ingenuo.)
- Por evidencia, campo mixto, H3a a 2000 ticks: `completo` queda en -0,011 / -0,012 en el remuestreo y -0,001 / -0,002 en las plausibles. Pierde en las dos.
- `completo_min` a 2000 ticks es `ejec_a`: la diferencia es 0,000 ± 0,000 con los campos mixto y racional y no pasa de 0,002 con el fuerte y el de reversores. A 20 000 ticks pierde 0,009 a 0,012 con H3a (campo mixto).

### 9.2 En patrimonio (H1 y H2)

Diferencia de patrimonio contra `ejec_a`, conjunto evidencia.

| Candidata | 2000 | 2000: remuestreo | 2000: plausibles | 20 000 interiores | 20 000 parada | Parada: remuestreo | Parada: plausibles |
|-----------|------|------------------|------------------|-------------------|---------------|--------------------|--------------------|
| `completo` | -2 ± 3 / -1 ± 3 | -21 ± 3 / -16 ± 4 | +18 ± 4 / +19 ± 4 | +374 ± 43 / +452 ± 46 | +221 ± 25 / +249 ± 26 | -12 ± 27 / -1 ± 28 | +454 ± 41 / +500 ± 43 |
| `rec_e` | +1 ± 4 / +1 ± 3 | -21 ± 3 / -16 ± 4 | +24 ± 5 / +25 ± 4 | +486 ± 43 / +560 ± 49 | +260 ± 26 / +281 ± 28 | +8 ± 30 / +23 ± 30 | +512 ± 42 / +539 ± 47 |
| `completo_min` | -1 ± 1 / +2 ± 2 | +0 ± 0 / +1 ± 1 | -1 ± 1 / +1 ± 2 | +301 ± 69 / +301 ± 69 | +161 ± 38 / +131 ± 37 | -169 ± 33 / -238 ± 34 | +490 ± 67 / +500 ± 65 |
| `fondo_rec` | -9 ± 4 / -8 ± 3 | -28 ± 3 / -22 ± 4 | +12 ± 5 / +13 ± 4 | +343 ± 43 / +412 ± 48 | +156 ± 25 / +178 ± 28 | -74 ± 29 / -63 ± 30 | +386 ± 41 / +420 ± 47 |
| `ejec_b` | +9 ± 1 / +8 ± 1 | +10 ± 1 / +7 ± 1 | +9 ± 1 / +7 ± 1 | +113 ± 7 / +121 ± 7 | +92 ± 4 / +92 ± 4 | +102 ± 5 / +98 ± 5 | +82 ± 6 / +85 ± 6 |

- **A 2000 ticks el fondo completo empata con `ejec_a` en patrimonio** (-2 ± 3 / -1 ± 3), con signo contrario en las dos evidencias.
- **A 20 000 ticks le gana por +221 / +249 (parada) o +374 / +452 (interiores)**: cerca de 1,0 a 1,2 % del patrimonio medio. En la razón W/B&H, +0,032 ± 0,007 / +0,029 ± 0,008 en parada.
- **Toda esa ventaja está en las familias del modelo** (+454 / +500) **y es cero en el remuestreo** (-12 / -1). Es la firma del gestor `activo`, que los estudios 1 y 2 ya habían descartado por lo mismo: gana si la serie oculta se parece al modelo ajustado y no si se parece al material de la serie de práctica. Con el criterio del protocolo (el signo se tiene que repetir en las dos evidencias) no es una mejora.
- El percentil 5 del patrimonio de una ronda a 20 000 ticks queda un poco más abajo con el fondo: 6 649 / 6 465 contra 6 756 / 6 488 de `ejec_a` (parada).
- En el estrés a 20 000 ticks el fondo completo saca mucho más patrimonio medio que `ejec_a` (+2 990 ± 240 / +2 914 ± 218 en parada). Esa media está dominada por pocas series y por eso el estrés se lee mejor en puntos (sección 8.5).

### 9.3 Respuesta por hipótesis y por largo

| Hipótesis | 2000 ticks | 20 000 ticks |
|-----------|------------|--------------|
| H1, patrimonio | Empate: -1 ± 3 | Gana el fondo completo: +249 ± 26 (parada), pero solo en las plausibles. En el remuestreo, -1 ± 28 |
| H2, exceso sobre comprar y mantener | Igual que H1 en pesos | Igual que H1 en pesos. En razón W/B&H, +0,029 ± 0,008 (parada) |
| H3a, lineal en patrimonio | Gana `ejec_a`: el fondo queda en -0,007 ± 0,001 | Gana `ejec_a`: -0,004 (interiores) y -0,008 (parada). Con rivales racionales, empate (+0,002 ± 0,001 en parada). Con rivales ingenuos el fondo queda apenas arriba (+0,002 ± 0,001 en parada) |
| H3b, lineal en el puesto | Gana `ejec_a`: -0,016 ± 0,002 | Gana `ejec_a`: -0,032 a -0,034. Con rivales reversores, hasta -0,200 |

(Cifras de la semilla reservada, campo mixto salvo donde se indica.)

**Cuánto cuesta o cuánto rinde elegir el fondo completo:**

- En vez de `ejec_a`: cuesta 0,004 a 0,008 puntos esperados con H3a y 0,016 a 0,034 con H3b con el campo mixto, y hasta 0,02 y 0,20 si todos los rivales son reversores. Rinde 1 % más de patrimonio medio en rondas de 20 000 ticks si la serie oculta se parece a las familias del modelo, y +0,011 ± 0,002 / +0,014 ± 0,002 puntos de H3a en series de estrés a 20 000 ticks (pareado contra `ejec_a`, parada, campo mixto).
- En vez de `max_media` sin contabilidad: rinde +0,000 a +0,002 puntos con H3a (no se distingue de cero y es negativo sin el filtro de interiores) y +0,011 a +0,019 con H3b. Lo pone la ejecución A.
- En trabajo: más de 11 días contra 3 de `ejec_a` y menos de 1 de `max_media` (estimado, sección 14), y no cabe en la memoria actual (estimado, sección 11).

## 10. Qué pone cada pieza

Diferencia contra `max_media`, conjunto evidencia, campo mixto, H3a y H3b. Semilla 0, porque `completo_s` no fue a la reservada; las demás filas se confirmaron con ella.

| Paso | 2000 ticks | 20 000 parada |
|------|------------|---------------|
| Gestores y reparto recomendados (`fondo_rec`) | -0,004 y +0,006 | -0,008 y +0,006 |
| Más la tabla que aprende como cuarto gestor (`completo_s`) | -0,003 y +0,005 | -0,007 y +0,007 |
| Más la ejecución A en el supervisor (`completo`) | +0,002 y +0,013 | -0,002 y +0,014 |
| La ejecución A sola (`ejec_a`) | +0,007 y +0,027 | +0,007 y +0,048 |

- **El reparto entre gestores resta.** El supervisor con posiciones parciales manda órdenes en ticks en que `max_media` no las mandaría, y cada una paga los 5 de comisión. Es lo que encontró el estudio del fondo.
- **El cuarto gestor no mueve la evidencia** y da la protección en estrés largo: `completo` saca +0,018 / +0,021 con H3a en el estrés a 20 000 ticks y `rec_e`, que no lo tiene, +0,004 / +0,004.
- **La ejecución A suma lo mismo en todas partes**: +0,005 a +0,008 con H3a al fondo, a `fondo_min` y a `max_media`.

## 11. Costo

No se escribió assembly. **Las instrucciones y la memoria de esta sección son estimaciones**: se suman las que entregó cada estudio para su pieza (conteos a mano sobre el código en C, con la ISA del Espino base, sin desplazador ni multiplicador). La regla base mide 27 instrucciones por tick. El presupuesto de la ronda más rápida es de 2262 ciclos, unas 540 instrucciones por hilo en el barrel.

| Candidata | Instrucciones por tick (estimado) | Productos y cocientes | Memoria (estimado) | Hardware que pide |
|-----------|-----------------------------------|-----------------------|--------------------|-------------------|
| `max_media` | 27 (medido para la regla base, que es el mismo programa con otra constante) | 0 | 40 palabras de 512 | Ninguno |
| `ejec_a` | 38 en el tick común, unas 90 en el peor | Un producto de 6 por 8 bits y un cociente de 6 pasos, en el 1 % de los ticks | 2 palabras de estado y 60 a 75 de programa más | Ninguno |
| `ejec_b` | 5 más que `ejec_a` | Lo mismo | Lo mismo | Ninguno |
| `espera` | 34 | 0 | 1 palabra más | Ninguno |
| `aprendiz` | 70 a 80 | 0 | 50 palabras de datos (32 de tabla y 18 de anillo) y unas 90 de programa (esta última cifra se estimó aquí, a partir de sus instrucciones por tick) | Ninguno |
| `fondo_rec` | Gestores 38, 160 (`kalman`) y 38. Supervisor 55 en el tick común y 200 en el peor | Dos productos de precio por cantidad y una división de 6 pasos en el peor tick | Unas 476 palabras | Ninguno. El barrel si se quiere un gestor por hilo |
| **`completo`** | Lo de `fondo_rec`, más unas 95 del cuarto gestor (la tabla y su cuenta en papel) y unas 8 de la regla de compra chica en el supervisor. En un solo hilo, unas 540 en el peor tick | Los de `fondo_rec` | **Unas 620 palabras: no cabe en las 512 actuales** | Ampliar la memoria con las BRAM libres. No se diseñó ni se midió |
| `completo_min` | Gestores 38 cada uno, cuarto gestor 95, supervisor unas 46 en el tick común y 140 en el peor (el voto más el espejo). En un solo hilo, unas 350 en el peor tick | Los del espejo: un producto y un cociente en el 1 % de los ticks | Unas 395 palabras | Ninguno. El barrel si se quiere un gestor por hilo |

- El barrel tiene cuatro hilos: el supervisor y tres gestores. **El cuarto gestor no tiene hilo propio**: tendría que compartirlo con un gestor de media exponencial (38 más 95 instrucciones, lejos de las 540 del presupuesto).
- Ninguna candidata necesita hardware nuevo. En tiempo todas caben: `completo` corrido en un solo hilo del core base serían unos 1200 ciclos de 2262 (estimado con el CPI de 2,2 medido en `trade.s`).
- Lo que limita a `completo` es la memoria de programa, no el tiempo.

## 12. Cotas

Este estudio no calculó una cota nueva. Las de los tres estudios, todas con la semilla 0 y contra `max_media`:

| Cota | Valor | Cómo se calculó | Lo que se alcanzó |
|------|-------|-----------------|-------------------|
| Ejecución sin el límite de 63 acciones por orden (`../r3_ejecucion`) | +0,036 (H3a) y +0,073 (H3b) a 2000 ticks | Copia del núcleo que acepta órdenes más grandes. No es un máximo: es lo que daría la misma regla con una maestra que no existe (auditoría, sección 19) | `ejec_a`: +0,007 y +0,027. `ejec_b`: +0,012 y +0,031 |
| Mejor mezcla fija de `max_media`, `kalman` y `activo`, elegida después (`../r4b_fondo`) | +0,005 y +0,019 a 2000 ticks; +0,008 y +0,027 a 20 000 con las interiores. Con parada (calculado en la auditoría) esa mezcla da -0,006 y +0,011, y la mejor mezcla por H3a es `max_media` sola | Cuentas separadas, con la comisión repartida en proporción | `fondo_rec`: -0,004 y +0,006 |
| Oráculo que elige el mejor gestor de cada serie (`../r4b_fondo`) | +0,15 a +0,34 a 2000 ticks; +0,04 a +0,10 a 20 000 | Después de ver la ronda | No se puede cobrar: el desempeño en papel no persiste dentro de la ronda |
| Oráculo que sabe si la serie es del remuestreo o del modelo y juega la mejor regla fija de cada grupo (`../r4c_aprendizaje`) | +0,038 y +0,064 a 2000 ticks | Las reglas se eligen con las mismas series | `aprendiz`: 0,000 |

El fondo completo junta las tres piezas y queda en +0,002 y +0,013 a 2000 ticks: no alcanza ninguna de las tres cotas, y lo que saca es menos de la mitad de lo que consigue la ejecución sola.

## 13. Recomendación

**Edición de competencia: `max_media` con la ejecución A (`ejec:m=8`), si el ayudante confirma que la caja inicial es 10 000, que la comisión es 5 y que la placa parte de reset en cada ronda. Si alguna de las tres no se puede confirmar, `max_media` sola.**

- `ejec_a` es la única pieza de los tres estudios que pasa el criterio de corte, y lo pasa en todo lo que se probó: cinco campos, dos semillas, dos largos, y la vista de parada confirma. Vale +0,006 a +0,007 puntos de 2 con H3a con el campo mixto y +0,015 con rivales racionales. Con H3b vale +0,027 a +0,05, pero la mayor parte es desempate contra un rival idéntico.
- El riesgo lo midió el estudio 3 y no cambia: si el espejo supone menos caja que la real, deja de comprar y pierde 3 % en una ronda de 2000 ticks y 19 % en una de 20 000. Es mucho más que lo que gana. Por eso la condición.
- **Entre A y B, queda A.** La semilla reservada confirma que B tiene más H3a (+0,004 ± 0,000 a los dos largos) y más patrimonio (+8 ± 1 por ronda de 2000 ticks y +92 ± 4 por ronda de 20 000), y también que tiene menos H3b a 20 000 ticks (-0,009 ± 0,001 con el campo mixto, -0,037 con el fuerte y -0,066 con reversores). Contra A no pasa el criterio con los campos mixto, fuerte ni reversores con ninguna de las dos semillas, y con el racional pasa con la semilla 0 y no con la reservada. El estudio 3 había dejado dicho que si la reservada no confirmaba la ventaja de B quedaba A, y además A tiene un parámetro en vez de tres. Si el puntaje fuera lineal en patrimonio y ningún grupo llegara a la misma regla, B valdría 0,004 puntos más. Nota de la auditoría: la pérdida de B con H3b sale del mismo desempate contra el rival idéntico que la sección 8.3 pide descontar cuando se compara A con `max_media`. Con H3a sola, B queda sobre A en los cinco campos, con las dos semillas y en las tres vistas, entre +0,003 y +0,030 puntos. Quedarse con A es una decisión de prudencia (un parámetro, ninguna celda negativa), no algo que el torneo decida por sí solo.
- Ningún fondo va a la competencia.

**Edición de exhibición: el fondo mínimo con la tabla que aprende y la ejecución A (`completo_min`).**

- Muestra las tres ideas a la vez: un gestor por hilo con contabilidad en papel, reparto que se ajusta según el desempeño en papel alrededor de un prior, y una tabla de política que parte de la regla validada y aprende en vivo.
- A 2000 ticks decide igual que `ejec_a` en puntos (diferencia 0,000 ± 0,000 en los cuatro campos). A 20 000 ticks cuesta 0,009 a 0,012 puntos de H3a contra `ejec_a` y gana en el estrés (+0,044 ± 0,003 contra `max_media`).
- Cabe en la memoria actual (unas 395 palabras, estimado) y no necesita productos fuera del espejo.
- `completo`, el fondo con `kalman`, posiciones parciales y la tabla, no rinde más puntos que `completo_min` (a 2000 ticks rinde menos: +0,000 y +0,011 contra +0,007 y +0,027), no cabe en la memoria y cuesta el doble de trabajo. Su único argumento es el patrimonio medio en rondas largas si la serie oculta se parece al modelo.
- Si no alcanza el tiempo, el escalón anterior es `fondo_min` (el que recomendó el estudio del fondo, 3 días): igual a `max_media` a 2000 ticks.

Elegir es decisión de Nicolás. Este estudio no tocó `ref/trader.py`, `sw/trade.s` ni ningún archivo versionado fuera de los dos de la sección 2.

## 14. Días de trabajo para calidad de competencia (estimado)

Sumas de lo que estimó cada estudio para su pieza. No se volvió a estimar.

| Candidata | Tareas | Días |
|-----------|--------|------|
| `max_media` | Una constante en `sw/trade.s`, equivalencia, bitstream y documentación | 0,7 |
| `ejec_a` | Espejo, cociente de 6 restas y producto de 6 por 8 bits en `sw/trade.s`, referencia en `ref/trader.py`, equivalencia, matriz de estrés de caja, comisión y reset, documento | 3,0 |
| `completo_min` | `fondo_min` sobre el barrel (3,0), el espejo y la regla de compra chica en el supervisor (1,5 si `ejec_a` ya existe, 3,0 si no) y la tabla que aprende con su anillo y su acumulador (4,0) | 8,5 a 10 |
| `completo` | `fondo_rec` sobre el barrel (6,5), la tabla (4,0), la regla en el supervisor (1,0) y ampliar la memoria (sin estimar) | más de 11,5 |

Todo lo que compita tiene que estar en el bitstream que se pruebe con la maestra real el 26/11. Los fondos dependen además de que el barrel sea el core de esa edición.

## 15. Cumplimiento de las reglas del enunciado

- **"La decisión se debe calcular en el Espino Core".** Se cumple. Todas las candidatas son software: los gestores y el supervisor son hilos del mismo core (o rutinas de un solo hilo), y el supervisor lee el precio y escribe `DECISION`. Queda la pregunta de la pieza A para el ayudante: si un Espino con cuatro hilos sigue siendo Espino.
- **"No se puede usar información externa a la serie recibida por SPI ni almacenar series de precios en el diseño".** Se cumple. El espejo, las cuentas en papel y la tabla dependen solo de los precios recibidos y de las decisiones propias. La tabla parte de la regla, no de la serie de práctica, y aprende en vivo. La caja inicial y la comisión son reglas del enunciado. Los umbrales, pesos y tasas son hiperparámetros elegidos con la semilla 0 por los estudios anteriores. Este estudio no agregó ninguno: armó las configuraciones con los valores que ya estaban.
- **"Todo hardware agregado debe estar en el repositorio con su testbench".** No se agrega hardware.
- **"Deben usar el mismo programa para todas las series de tiempo".** Se cumple.
- **Regla propia del proyecto** (nada de tablas ni constantes derivadas punto a punto de la serie de práctica): se cumple. Las series de `../build/series` son datos de prueba del computador.
- Aritmética: enteros, sumas, restas, comparaciones y desplazamientos por constantes. Productos solo de precio por cantidad, contados en la sección 11. Sin punto flotante en ninguna estrategia.

## 16. Variantes probadas, sobreajuste y lo que no se verificó

- **19 configuraciones con la semilla 0**: 8 de los estudios anteriores con sus parámetros y 11 armadas aquí, todas fijadas antes de correr (`final.c`). No hubo barrido ni se ajustó ningún parámetro. **11 de ellas fueron a la semilla reservada**, con 5 duelos, en una lista fijada antes de mirarla.
- No se eligió nada con la semilla 3. La recomendación de la sección 13 es la que ya daba la semilla 0.
- La auditoría volvió a evaluar con la semilla 3 las mismas candidatas, con otro evaluador y sin elegir nada (sección 19). Para estas candidatas la semilla 3 ya no es una semilla sin mirar.
- Los estudios anteriores probaron 61 variantes de ejecución, 90 del fondo y 249 de aprendizaje. La candidata A salió de una familia con meseta y la B se armó después de mirar la semilla 0. Para las dos, el resultado que hay que creer es el de la semilla reservada, y coincide con el de la semilla 0 a 0,001.

Lo que no se hizo o no se verificó:

- `make todo` se corrió como un solo comando al cerrar el estudio: 21 min 31 s, sin errores, y las 24 salidas de `mediciones/` que le corresponden o que no toca quedaron idénticas byte a byte a las de las corridas por separado (comparadas con `md5sum`; la única que cambió fue `reservada_usada.txt`, por la nota que se le agregó a mano). Después de eso se agregó a `tablas.py` el percentil 5 de una ronda en las tablas de puntos y se regeneraron con `make tablas`. `make reservada REPETIR=1` no se corrió: la semilla 3 se evaluó una sola vez, así que sus cifras no tienen una segunda corrida que las confirme.
- **El README del arnés no se actualizó** (está fuera de esta carpeta): su tabla de semillas no nombra la 3, su sección de rivales no nombra los cuatro campos nuevos y sigue diciendo que hay 77 archivos de series (ahora son 107). Además, cuando se vuelvan a correr `make comprobar-series`, `make exploracion` o `make auditoria` del arnés, sus salidas versionadas `series_comprobacion.txt`, `series_manifiesto.txt` y `auditoria_series.txt` van a contar también los archivos de la semilla 3. No se volvieron a correr.
- No hay assembly de ninguna candidata y nada se corrió en el gemelo digital ni en el RTL. Las instrucciones, la memoria y los días son estimaciones heredadas.
- **La robustez del espejo no se midió para los fondos.** El modelo del fondo recibe del arnés la caja y la comisión reales, así que no se puede ver con él qué pasa si el programa supone otras. El riesgo que el estudio 3 midió para `ejec_a` vale igual o más para un fondo con posiciones parciales, que usa el patrimonio del espejo en cada orden.
- No se probaron otras cajas ni comisiones, rondas seguidas sin reset ni un tick perdido.
- El veredicto oficial se corrió con el campo mixto. Con los demás campos el veredicto se calcula en `tablas.py` con la misma regla y las mismas cifras, y se comprobó contra el oficial solo en el mixto.
- Los campos nuevos se compararon con el evaluador independiente para `base` y `max_media`, que es lo que ese evaluador calcula. `fijos2` y `fijos3` se usaron en la exploración y no en la lista final.
- El campo `reversores` no tiene rivales débiles: el peor del campo es otra reversión, y H3a se vuelve muy sensible (los errores son 4 veces mayores).
- No se evaluó un fondo con el predictor de patrones como gestor. `aprendiz_patron` solo quedó igual a `max_media` (-0,001 a 2000 ticks) y pediría 2 BRAM.
- El duelo entre `completo` y `rec_e` (cuánto pone el cuarto gestor) no se corrió pareado: sale de restar filas.
- El error del percentil 5 que informa el arnés es unas 2,8 veces el real. Ningún veredicto de este estudio depende de la condición del percentil 5: las candidatas que no pasan fallan por la media.

## 17. Riesgos

- **Toda la evidencia sale de una serie de práctica**, remuestreada o a través del modelo ajustado a ella. El fondo completo gana patrimonio en una de las dos evidencias y no en la otra. Cuál se parece más a la serie oculta no se sabe.
- **Los rivales son un supuesto.** El signo de la comparación entre el fondo y `ejec_a` no cambia en ninguno de los cinco campos de la lista final. El tamaño sí, por un factor de 5.
- **H3b premia a `ejec_a` por desempatar con un rival idéntico.** Si ningún grupo llega a `max_media`, su ventaja con H3b es la de H3a. La comparación con el fondo se sostiene igual con H3a.
- **La contabilidad propia abre un modo de falla que `max_media` no tiene** (caja, comisión o reset distintos de lo supuesto). Vale para `ejec_a` y para todos los fondos.
- **Cuatro hilos y cuatro gestores son más lugares donde equivocarse**, sin ningún punto de torneo a cambio.
- A 20 000 ticks las series de prueba son menos confiables (límites 1 y 255, filtro de interiores). Por eso cada cifra a ese largo se informa con interiores y con parada, y las conclusiones usan la de parada.

## 18. Veredicto según los criterios de corte

| Pieza | Veredicto | Razón |
|-------|-----------|-------|
| `max_media` con la ejecución A (`ejec_a`) | **Pasa el criterio de algoritmo, confirmado con la semilla reservada.** Competencia, con la condición de caja, comisión y reset | +0,006 a +0,007 puntos (H3a), el percentil 5 no baja, 5 de 5 campos, dos semillas, parada confirma. No agrega hardware |
| Ejecución B (`ejec_b`) | Pasa contra `max_media`. No pasa contra A. Queda A | Más H3a y patrimonio (+0,004, +8), menos H3b en rondas largas (-0,009 a -0,066) |
| **El fondo completo** (`completo`) | **Descartado de la competencia.** Exhibición solo en su forma mínima | No pasa contra `max_media` con el campo mixto ni el fuerte, y no pasa contra `ejec_a` en ningún campo. Cuesta 0,004 a 0,008 puntos de H3a frente a la mejor estrategia sola. No cabe en la memoria (estimado) |
| El fondo sin el gestor experimental (`rec_e`, `fondo_rec`) | Descartado | Lo mismo. `fondo_rec` sin la ejecución queda en -0,005 y +0,005 |
| El fondo con ancla en comprar y mantener (`completo_ancla`) | Descartado, documentado como seguro | -0,031 puntos a 2000 ticks y -0,144 a -0,164 a 20 000. Sube el percentil 5 solo en rondas cortas |
| Fondo mínimo con la tabla y la ejecución A (`completo_min`) | **Exhibición** | Igual a `ejec_a` a 2000 ticks, -0,005 de H3a contra `max_media` a 20 000, protege en el estrés. Cabe (estimado) |
| La tabla que aprende sola (`aprendiz`) | Descartada de la competencia. Exhibición, como gestor del fondo mínimo | Igual a `max_media` a 2000 ticks, -0,014 a -0,028 a 20 000 |
| La regla fija `espera` | Descartada | Pasa a 2000 y no a 20 000, con signo contrario en las dos evidencias |
| Campos racional, reversores, fijos2 y fijos3 en el arnés | Herramienta. Quedan disponibles para cualquier estudio | Sin cambios en las salidas anteriores y de acuerdo con el evaluador independiente |

## 19. Auditoría

Revisión independiente hecha el 15/11, después de cerrar el estudio, con la intención de refutarlo. Todo está en `../auditoria_r34/` y se corre con `make todo` desde ahí. Su README trae el detalle. Aquí va lo que toca a este estudio.

### 19.1 Qué se revisó y qué dio

| Punto | Cómo | Resultado |
|-------|------|-----------|
| Información del futuro | Comando `causal` del arnés para todo lo registrado en el binario del cierre. Perturbación propia de los precios futuros (63 cortes por serie de 8192 ticks, futuro al azar, futuro parecido, solo el precio de ejecución, serie cortada y ronda repetida) y prueba de martingala, para 56 estrategias: las 11 configuraciones de este estudio, las de los tres anteriores y variantes que aprenden rápido | 0 fallas en 85 008 comparaciones. La media de martingala más lejana queda a 1,34 errores. Los 3 controles negativos fallan |
| Semilla reservada | Fechas de los fuentes, de las series y de las salidas, huella de la lista original, registro de la corrida y búsqueda de otros usos | La lista original (`build/lista_final_original.txt`) tiene la huella anotada al iniciar la corrida. Las candidatas se definieron antes de generar la semilla 3. Un solo registro de corrida. Son indicios de archivo |
| `fondoc` y `filtro` | El supervisor del fondo, el espejo, `ejec`, el Kalman y la tabla se escribieron de nuevo a partir de los README, sin usar el núcleo, y se compararon serie por serie con el comando `detalle` | `ejec_a`, `ejec_b`, `fondo_rec`, `rec_e`, `completo`, `completo_s`, `fondo_min`, `min_e`, `completo_min`, `kalman`, `aprendiz` y `aprendiz_rapido`: 46 061 series cada una, 0 distintas |
| Tablas | Torneo con el valor esperado exacto en vez del sorteo de campos, tres vistas, cinco campos, semillas 0 y 3 | 1 174 cifras de `mediciones/resumen.md`: el patrimonio coincide al peso y los puntos a 0,0004 de mediana y 0,0028 como máximo. Ninguna fuera de tolerancia |
| Veredicto por campo | Comando oficial `veredicto --parada` con los campos ingenuo, fuerte, racional y de reversores, semilla 0, para `ejec_a`, `completo`, `completo_min`, `rec_e` y `fondo_rec` | Los 20 veredictos son los que calcula `tablas.py` |
| Campos nuevos de `torneo.c` | El mismo binario con el `torneo.c` del repositorio y con el actual, con 11 comandos distintos de los de `salidas_torneo.sh`. Las salidas versionadas `../mediciones/hipotesis_s0.txt` y `rivales.txt`, generadas de nuevo | Todo idéntico byte a byte. `torneo.c`: 52 líneas agregadas y 2 cambiadas. Los demás archivos del núcleo, sin cambios |
| Repetición | `make prueba`, `make campos` y `make tablas` de esta carpeta | Los 25 archivos de `mediciones/` quedan idénticos |
| Percentil 5 | Rehecho con otro sorteo y error por lotes, campo mixto | `ejec_a` lo sube en las tres vistas con las dos semillas. Ningún veredicto depende de que el error del arnés sea grande |
| Riesgo del espejo | Espejo propio separado de la cuenta real, con caja real 9 000, 12 000 y 20 000 y comisión real 0 | Las cifras del estudio 3 que usa la recomendación se reproducen: -657 y -7 723 con el doble de caja |

### 19.2 Correcciones a este documento

1. **Sección 1, respuesta corta.** Decía que el fondo completo no le gana a la mejor estrategia sola "con ningún campo de rivales". Lo que las tablas sostienen es que no pasa el criterio con ningún campo y que con H3b pierde en los cinco. Con H3a, a 20 000 ticks, queda apenas arriba con el campo ingenuo y empata con el racional. Párrafo reescrito.
2. **Secciones 1 y 9.1, "la única cifra a su favor".** No era la única. Con el campo ingenuo, `completo` menos `ejec_a` da +0,005 ± 0,001 / +0,006 ± 0,001 con H3a en las interiores y +0,001 ± 0,001 / +0,002 ± 0,001 con parada. Con el valor esperado exacto, +0,0010 ± 0,0005 / +0,0017 ± 0,0005 (1,9 y 3,1 errores): la vista de parada conserva el signo. Con el campo racional también lo conserva, pero dentro del error (+0,0009 ± 0,0015 / +0,0023 ± 0,0014). Las cifras estaban en `mediciones/tablas_duelo_ejec_a_s0.md` y `tablas_duelo_ejec_a_s3.md`; la tabla 9.1 no traía el campo ingenuo. Se agregaron sus dos filas y se corrigieron las frases. Son uno o dos milésimos de punto de un máximo de 2, con rivales que no se parecen a los que se esperan, y H3b sigue negativo: no cambia ningún veredicto.
3. **Sección 9.3.** La celda de H3a a 20 000 ticks ahora nombra el campo ingenuo.
4. **Sección 12, mezcla fija.** Los +0,008 y +0,027 a 20 000 ticks son con las series interiores. Con parada esa mezcla da -0,006 ± 0,001 y +0,011 ± 0,002, y la mejor mezcla por H3a es `max_media` sola. La fila lo dice ahora. Va a favor de la conclusión.
5. **Sección 12, cota de ejecución.** No es un máximo: es lo que daría la misma regla sin el límite, y su "sin límite" son 2^21 acciones por orden. Las cifras no cambian.
6. **Sección 13, A o B.** Se agregó una nota: la pérdida de B con H3b es el mismo desempate contra el rival idéntico que se descuenta al comparar A con `max_media`. Con H3a sola B queda sobre A en todo lo evaluado. Quedarse con A es una decisión de prudencia.
7. **Sección 16.** Se anotó que la auditoría volvió a evaluar con la semilla 3.

Ninguna cifra de las tablas cambió y ninguna medición se volvió a generar: lo corregido es texto.

### 19.3 Lo que la auditoría no cubrió de este estudio

- `espera`, `espera_e`, `completo_ancla`, `completo_esp`, `completo_ap`, `fondo_ancla` y `aprendiz_patron` no se reescribieron. Pasan las pruebas de causalidad y sus cifras son las del arnés.
- La exploración de las 19 configuraciones con los campos `fijos2` y `fijos3` no se rehízo.
- La concordancia entre semillas (509 de 528) no se volvió a contar.
- Los costos de la sección 11 y los días de la sección 14 siguen siendo estimaciones. Que `completo` no cabe en 512 palabras depende de una cuenta de unas 620 que no se pudo comprobar sin escribir el programa.
- El README del arnés sigue sin actualizar (sección 16).
