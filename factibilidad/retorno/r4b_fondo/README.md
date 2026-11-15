# Estudio de retorno 4, parte B: el fondo de estrategias y el reparto de capital

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Tramo de factibilidad del Proyecto 4. Esta carpeta no agrega hardware ni cambia el programa de la placa. Evalúa, con el arnés de `factibilidad/retorno/`, si un fondo de estrategias (tres gestores que operan en papel, uno por hilo del barrel, y un supervisor que lleva la cuenta real, reparte el capital y escribe `DECISION`) rinde más puntos de torneo que la mejor estrategia sola, `max_media`.

## 1. Respuesta corta

**El fondo no mejora los puntos esperados contra `max_media`. Ninguna de las 88 variantes probadas pasa el criterio de corte, y las cinco configuraciones con nombre dan `NO_PASA` en el veredicto oficial, a 2000 y a 20 000 ticks.** Todo con la semilla 0.

- Las variantes que quedan más cerca son las que casi no se apartan de `max_media`. La menos mala con contabilidad y posiciones parciales reales es `fondo_rec` (gestores `max_media`, `kalman` y `activo`, pesos 8/4/4 de 16, banda de no operar de 4/16): -0,004 ± 0,001 puntos con H3a y +0,006 ± 0,002 con H3b a 2000 ticks, y -0,008 ± 0,001 y +0,006 ± 0,001 a 20 000 ticks sin seleccionar series (vista de parada). Las dos lecturas del torneo tienen signo contrario, y el signo tampoco se repite entre remuestreo (negativo) y plausibles (positivo). No es una mejora.
- El diseño original (`max_media`, `prudente` o `guardia`, y comprar y mantener como ancla) cuesta entre 0,02 y 0,05 puntos esperados a 2000 ticks y entre 0,08 y 0,17 a 20 000. A cambio, a 2000 ticks sube el percentil 5 de la competencia de tres rondas (+0,057 ± 0,010 con H3a) y gana en las series de estrés (+0,028 y +0,053). Es un seguro, no una mejora, y en rondas largas el seguro también pierde el percentil 5.
- Repartir según el desempeño en papel no ayuda, porque el desempeño en papel no persiste: el gestor que va ganando en la primera mitad de la ronda es el mejor de la segunda en el 35 % de las series, lo mismo que al azar. Copiar al líder cuesta entre 0,16 y 0,34 puntos con los conjuntos que incluyen comprar y mantener.
- La causa de fondo es la comisión fija. Una posición parcial paga los mismos 5 pesos que una completa, así que repartir el capital multiplica las órdenes (de 55 a 76 por ronda con pesos 8/4/4) y se come la poca diversificación que había (sección 6).
- Como pieza de exhibición el fondo se puede llevar al barrel casi gratis en puntos: el fondo mínimo `fondo_min` cuesta +0,000 ± 0,000 a 2000 ticks y -0,019 ± 0,002 (H3a) a 20 000 ticks, siempre que el supervisor espere a los gestores en el mismo tick. Si usa lo publicado en el tick anterior, cuesta 0,02 a 0,05 puntos más.

## 2. Qué se construyó

| Archivo | Qué hace |
|---------|----------|
| `fondo.c` | El fondo como estrategia del arnés: gestores en papel con las reglas oficiales (`instancia_*` y `cuenta_*` del núcleo), supervisor con espejo de la cuenta real, reparto por pesos fijos, líder con histéresis o pesos aprendidos, banda de no operar, voto, desfase de 0 o 1 tick y un cuarto gestor por nombre. Trae cinco configuraciones con nombre. |
| `cota.c` | Programa aparte, enlazado con el núcleo sin su `main.c`: correlaciones entre gestores, oráculo de selección, mejor mezcla fija a posteriori y persistencia del líder. |
| `pruebas.sh` | Causalidad, identidad con un solo gestor, desfase de un tick y espejo de la cuenta. |
| `explorar.py` | Lista de variantes, corridas con el comando `hipotesis` del arnés (referencia `max_media`), veredictos oficiales y tablas. Se niega a usar las semillas 2 y 3. |
| `bytes.sh` | Flujo de bytes de `DECISION` de una configuración para una serie, con su huella y una traza del estado interno. |
| `Makefile` | Un objetivo por medición. |
| `mediciones/` | Salidas de todo lo anterior. `mediciones/tablas.md` tiene las tablas completas. |

No se modificó ningún archivo fuera de esta carpeta. El núcleo del arnés se usa tal como está, con `nucleo.mk`.

## 3. Cómo se reproduce cada número

Desde esta carpeta, con las series del arnés ya generadas (`make -C .. series`):

| Comando | Qué hace | Salida | Tiempo medido |
|---------|----------|--------|---------------|
| `make arnes` | Compila `build/arnes` y `build/cota`. | | segundos |
| `make prueba` | Comprobaciones del módulo (sección 4.4). | `mediciones/prueba.txt` | no se midió aparte |
| `make cota` | Cota a posteriori (sección 5). | `mediciones/cota_n2000_evidencia.txt`, `cota_n2000_estres.txt`, `cota_n20000_evidencia_interiores.txt` | 29 s |
| `make exploracion` | Las 88 variantes y las 5 con nombre a 2000 ticks. | `mediciones/exploracion_n2000_t*_parte*.txt`, `finales_n2000_parte1.txt` | 1 min 37 s la primera tanda y 34 s la segunda |
| `make largo` | Lista corta (17 variantes y las 5 con nombre) a 20 000 ticks: interiores, todas y parada. | `mediciones/largo_n20000_*_parte1.txt` | no se midió aparte |
| `make veredictos` | `veredicto --candidata X --referencia max_media --semilla 0 --parada` para las 5 con nombre. | `mediciones/veredicto_*.txt` | no se midió aparte |
| `make bytes` | Flujo de bytes de `fondo_rec` y `fondo_min` sobre `tb/practica.csv`. | `mediciones/bytes_*_practica.txt` | segundos |
| `make tablas` | Tablas en Markdown. | `mediciones/tablas.md` | 1 s |
| `make todo` | Todo lo anterior, en orden. | | 10 min 2 s |

Los archivos `*_parte*.txt` son el resumen, en texto, de lo que entrega el comando `hipotesis` del arnés: una línea por vista, conjunto y candidato, con cada cifra y su error. Todas las diferencias son pareadas contra `max_media`, con el campo mixto y G = 10. `HILOS` vale 5.

## 4. Definición del fondo

### 4.1 Gestores

Cada gestor es una estrategia del arnés con su propia cuenta en papel de 10 000, llevada con las reglas oficiales. Publica dos cosas: su posición (0 afuera, 1 adentro, según la acción de su última decisión) y su desempeño en papel.

| Conjunto (`c`) | Gestores | Para qué |
|----------------|----------|----------|
| 1 | `max_media`, `prudente`, comprar y mantener | El diseño de Nicolás con ancla. |
| 2 | `max_media`, `guardia`, comprar y mantener | El mismo, con la guardia de régimen. |
| 3 | `max_media`, `kalman`, `activo` | Tres reversiones con distinto estimador y distinta banda. |
| 4 | `max_media`, `base`, `prudente` | Tres bandas de la misma regla. |
| 5 | `max_media`, `base`, `activo` | Las tres bandas más baratas y más parecidas: para el fondo mínimo. |

El cuarto gestor experimental entra por nombre con el parámetro `x` y su peso `w3`. Por ejemplo `fondo:c=1,x=cand:kalman,w0=8,w1=2,w2=2,w3=4`. Si la especificación lleva parámetros, se escribe `/` en vez de `,` y `~` en vez de `=`. Se probó que compila, que pasa la causalidad y que con todo el peso en él el fondo decide igual que esa estrategia sola (`mediciones/prueba.txt`). No se evaluó ningún cuarto gestor: lo enchufa el estudio de cierre.

El desempeño en papel tiene dos formas (`pp`):

- `pp=0`: el patrimonio de la cuenta oficial del gestor.
- `pp=1`: un puntaje por acción, sin productos ni divisiones. En cada tick suma 16 veces el cambio de precio si el gestor tenía la acción, y resta 1 cada vez que se ejecuta un cambio de posición (la comisión de 5 pesos repartida en unas 76 acciones, en dieciseisavos de precio).

### 4.2 Supervisor: orden exacto dentro de un tick

Llega el precio `p` del tick n.

1. **Espejo.** El supervisor ejecuta en su copia de la cuenta real, al precio `p`, el byte que escribió en el tick n-1 (compra recortada a `(caja - 5) / p`, venta recortada a las acciones que tiene, orden que queda en cero no paga). Es lo mismo que hace la maestra.
2. **Gestores.** Cada gestor, con ese mismo `p`: ejecuta en su cuenta en papel su decisión anterior, actualiza su puntaje por acción, decide con `p`, y publica posición y desempeño.
3. **Lectura.** Con `df=0` (mismo tick) el supervisor usa lo que los gestores publicaron en este tick: tiene que esperarlos. Con `df=1` (tick anterior) usa lo que tenían publicado antes de este tick: no espera a nadie y la decisión del fondo sale con un tick más de atraso.
4. **Reparto.** Si corresponde, ajusta los pesos (sección 4.3).
5. **Orden.** `F` es la suma de los pesos de los gestores que están adentro, en dieciseisavos (0 a 16).
   - `F = 16`: escribe `0x7F` (comprar 63). `F = 0`: escribe `0xBF` (vender 63). Son las mismas órdenes repetibles de la regla base.
   - Entre medio, con `V = acciones * p` y `W = caja + V`: `D = F * W - 16 * V` es lo que falta invertir, en dieciseisavos de peso. Si `|D| <= b * W` no opera (`0x00`). Si `D > b * W` compra `min(63, (D - 16 * 5) / (16 * p))`. Si `D < -b * W` vende `min(63, -D / (16 * p))`. Una cantidad 0 es mantener.
   - Con voto (`vt`), `F` se lleva antes a 16 si `F >= vt` y a 0 si no, con histéresis opcional (`vs`). El fondo queda todo adentro o todo afuera y no necesita la cuenta real.

Con todo el peso en un gestor y `df=0`, el fondo escribe exactamente los bytes de ese gestor (comprobado en 8 casos, 20 000 ticks cada uno).

### 4.3 Formas de repartir (`m`)

| | Regla | Parámetros |
|-|-------|------------|
| (c) Pesos fijos, `m=0` | Los pesos son el prior y no cambian. | `w0..w3` |
| (a) Líder con histéresis, `m=1` | Todo el peso va al líder. En cada frontera de ventana de `2^v` ticks (o en cada tick, con el desempeño acumulado, si `v=0`) el líder cambia al gestor de mayor ganancia en papel solo si la ventaja supera `2^-mg` del patrimonio en papel del líder. | `v`, `mg` |
| (d) Pesos aprendidos, `m=2` | En cada frontera de ventana pasa `ps` dieciseisavos del gestor que menos ganó al que más ganó, si la ventaja supera el margen y ningún peso se aleja más de `d` de su prior. | `v`, `mg`, `d`, `ps` |
| (e) Ancla | Un gestor con peso fijo, fuera del aprendizaje. | `fj` (máscara) |
| (b) Banda de no operar | En dieciseisavos del patrimonio. Vale para todas las formas con posiciones parciales. | `b` |

El margen se compara como `ventaja * 2^mg > base`, solo con desplazamientos a la izquierda.

### 4.4 Comprobaciones del módulo (`make prueba`)

| Prueba | Resultado |
|--------|-----------|
| Causalidad (comando `causal` del arnés) | 7 variantes, 78 comparaciones cada una, 0 fallas |
| Identidad con un gestor | 8 casos (los gestores de los conjuntos 1 a 4 y el cuarto gestor), 20 000 filas cada uno, idénticas |
| Desfase | Con `df=1` el byte leído en el tick t es el de `max_media` en t-1: 19 998 filas, 0 distintas |
| Espejo de la cuenta real contra la cuenta que lleva el arnés | 3 variantes con posiciones parciales en 5 lotes (8900 series cada una, incluidos los bordes 1 y 255): 0 ticks distintos |

### 4.5 Configuraciones con nombre

| Nombre | Especificación | Qué es |
|--------|----------------|--------|
| `fondo_rec` | `fondo:c=3,w0=8,w1=4,w2=4,b=4` | El fondo recomendado si se quiere uno: el menos malo con contabilidad y posiciones parciales. |
| `fondo_rec_ant` | lo mismo con `df=1` | Para medir el costo de no esperar a los gestores. |
| `fondo_ancla` | `fondo:c=1,w0=12,w1=2,w2=2,b=2` | El diseño original con ancla: el fondo como seguro. |
| `fondo_min` | `fondo:c=5,w0=6,w1=5,w2=5,m=2,v=9,mg=5,d=4,pp=1,vt=8` | Fondo mínimo de demostración (sección 9). |
| `fondo_min_ant` | lo mismo con `df=1` | |

## 5. La cota: cuánto había para ganar

`make cota`. Conjunto evidencia, semilla 0. La mezcla fija es la ideal: el capital se reparte una vez entre cuentas separadas y el patrimonio es la suma ponderada. En una serie sola la mejor mezcla es siempre el mejor gestor (el patrimonio es lineal en los pesos), así que la mezcla fija se busca con los mismos pesos para todas las series, entre las 45 combinaciones en octavos.

Rondas de 2000 ticks (10 000 series). Diferencias contra `max_media`, H3a y H3b:

| Conjunto | Oráculo de selección | Mejor mezcla fija a posteriori | El líder de la 1.ª mitad es el mejor de la 2.ª | Seguir al líder desde la mitad |
|----------|----------------------|--------------------------------|------------------------------------------------|--------------------------------|
| 1: `max_media`, `prudente`, byh | +0,341 ± 0,005, +0,332 ± 0,005 | `max_media` sola (0) | 35,0 % | -0,116 ± 0,005, -0,124 ± 0,005 |
| 2: `max_media`, `guardia`, byh | +0,291 ± 0,005, +0,271 ± 0,004 | `max_media` sola (0) | 38,7 % | -0,103 ± 0,005, -0,115 ± 0,005 |
| 3: `max_media`, `kalman`, `activo` | +0,152 ± 0,002, +0,185 ± 0,003 | 3/8, 3/8, 2/8: +0,005 ± 0,001, +0,019 ± 0,002 | 37,3 % | -0,012 ± 0,002, +0,000 ± 0,003 |
| 4: `max_media`, `base`, `prudente` | +0,167 ± 0,003, +0,202 ± 0,003 | `max_media` sola (0) | 34,9 % | -0,034 ± 0,002, -0,039 ± 0,003 |

Rondas de 20 000 ticks, series interiores (4021 series):

| Conjunto | Oráculo de selección | Mejor mezcla fija a posteriori | Seguir al líder desde la mitad |
|----------|----------------------|--------------------------------|--------------------------------|
| 1 | +0,046 ± 0,002, +0,053 ± 0,003 | `max_media` sola (0) | -0,140 ± 0,005, -0,105 ± 0,005 |
| 2 | +0,036 ± 0,002, +0,047 ± 0,002 | `max_media` sola (0) | -0,119 ± 0,005, -0,101 ± 0,005 |
| 3 | +0,079 ± 0,002, +0,104 ± 0,002 | 3/8, 3/8, 2/8: +0,008 ± 0,001, +0,027 ± 0,002 | -0,010 ± 0,002, +0,010 ± 0,002 |
| 4 | +0,050 ± 0,002, +0,059 ± 0,002 | `max_media` sola (0) | -0,060 ± 0,003, -0,042 ± 0,002 |

Correlación entre los patrimonios finales, serie a serie (2000 ticks, evidencia):

| | `prudente` | `guardia` | `kalman` | `activo` | `base` | byh |
|-|-----------|-----------|----------|----------|--------|-----|
| `max_media` | 0,755 | 0,819 | 0,977 | 0,906 | 0,929 | 0,110 |

Qué dice la cota:

1. **El oráculo vale mucho a 2000 ticks (+0,15 a +0,34 puntos) y poco a 20 000 (+0,04 a +0,10).** En una ronda corta el resultado tiene mucha suerte y elegir después de mirar la aprovecha. En una ronda larga `max_media` es el mejor de los tres en el 75 a 80 % de las series de los conjuntos 1 y 2 (66 % en el 4) y queda poco que elegir.
2. **Ese valor no se puede cobrar, porque el desempeño en papel no persiste.** El líder de la primera mitad es el mejor de la segunda en el 35 a 39 % de las series a 2000 ticks. La tabla de persistencia tiene las tres filas casi iguales: lidere quien lidere la primera mitad, `max_media` gana la segunda el 39 a 41 % de las veces. La correlación entre la ventaja de un gestor sobre `max_media` en una mitad y en la otra va de -0,07 a +0,03.
3. **Los gestores de reversión diversifican poco entre sí**: correlaciones de 0,76 a 0,98 con `max_media`. El único que no está correlacionado es comprar y mantener (0,11), y pierde 1209 de patrimonio medio contra `max_media`.
4. **La mejor mezcla fija es `max_media` sola en tres de los cuatro conjuntos**, en los dos largos. Solo el conjunto 3 deja algo: +0,005 con H3a y +0,019 con H3b. Y esa cifra es ideal: supone que una cuenta con la cuarta parte del capital paga la cuarta parte de la comisión. La sección 6 muestra que con la comisión real desaparece.
5. **En las series de estrés la mezcla sí ayuda** (`mediciones/cota_n2000_estres.txt`): con 4/8, 2/8, 2/8 del conjunto 1, +0,018 ± 0,004 y +0,049 ± 0,004 en puntos y +0,234 ± 0,019 en el percentil 5 de tres rondas. Es el argumento del fondo como seguro.
6. **Notas de la auditoría (sección 17).** El oráculo y la mezcla fija se recalcularon con otro evaluador y coinciden. Dos precisiones. La mezcla 3/8, 3/8, 2/8 es la mejor por H3a; por H3b la mejor es 0/8, 5/8, 3/8, con +0,023 a 2000 ticks y +0,031 a 20 000 con las interiores. Y la tabla de 20 000 ticks es solo de las series interiores: con la vista de parada la mezcla 3/8, 3/8, 2/8 da -0,006 ± 0,001 con H3a y +0,011 ± 0,002 con H3b, la mejor mezcla por H3a pasa a ser `max_media` sola y la mejor por H3b (2/8, 5/8, 1/8) da +0,015. Sin el filtro de interiores hay todavía menos para ganar.

## 6. Exploración a 2000 ticks

`make exploracion`. 88 variantes en dos tandas (64 fijadas antes de mirar resultados y 24 definidas después de ver la primera). Conjunto evidencia (10 000 series). Referencia `max_media`: 10 982 de patrimonio, 1,503 puntos con H3a y 1,473 con H3b, percentil 5 de tres rondas 0,882 y 0,911, 55,2 órdenes por ronda. La tabla completa, con H2 y el estrés, está en `mediciones/tablas.md`.

| Variante | H1: patrimonio | H3a | H3b | H3a: p5 de 3 rondas | Órdenes | Estrés: H3a, H3b |
|----------|----------------|-----|-----|---------------------|---------|------------------|
| **Pesos fijos, banda 1/16** | | | | | | |
| mm, prud, byh 12/2/2 | -206 ± 9 | -0,046 ± 0,002 | -0,035 ± 0,002 | +0,048 ± 0,010 | 46,2 | +0,022, +0,047 |
| mm, prud, byh 14/0/2 | -157 ± 8 | -0,031 ± 0,002 | -0,027 ± 0,002 | +0,045 ± 0,010 | 47,8 | +0,021, +0,039 |
| mm, prud, byh 8/0/8 | -602 ± 35 | -0,181 ± 0,006 | -0,140 ± 0,005 | -0,055 ± 0,018 | 30,8 | +0,034, +0,058 |
| mm, guardia, byh 12/2/2 | -183 ± 9 | -0,042 ± 0,002 | -0,036 ± 0,002 | +0,038 ± 0,010 | 49,3 | +0,024, +0,046 |
| mm, kalman, activo 8/4/4 | -66 ± 5 | -0,038 ± 0,001 | -0,034 ± 0,002 | -0,029 ± 0,010 | 76,3 | -0,014, -0,003 |
| mm, kalman, activo 8/8/0 | +7 ± 2 | -0,002 ± 0,001 | +0,002 ± 0,002 | +0,009 ± 0,009 | 56,4 | -0,005, -0,003 |
| mm, base, prud 12/2/2 | -81 ± 3 | -0,026 ± 0,001 | -0,028 ± 0,002 | -0,007 ± 0,009 | 54,4 | -0,003, -0,003 |
| **Banda de no operar** | | | | | | |
| mm, kalman, activo 8/4/4, banda 0 | -76 ± 5 | -0,041 ± 0,001 | -0,038 ± 0,002 | -0,031 ± 0,010 | 78,3 | -0,021, -0,010 |
| mm, kalman, activo 8/4/4, banda 3 | -62 ± 5 | -0,036 ± 0,001 | -0,032 ± 0,002 | -0,027 ± 0,010 | 75,2 | -0,014, -0,002 |
| mm, kalman, activo 8/4/4, banda 4 (`fondo_rec`) | +6 ± 4 | -0,004 ± 0,001 | +0,006 ± 0,002 | +0,005 ± 0,009 | 55,2 | -0,000, +0,010 |
| mm, kalman, activo 8/4/4, banda 6 | +6 ± 4 | -0,004 ± 0,001 | +0,007 ± 0,002 | +0,004 ± 0,008 | 54,3 | +0,001, +0,012 |
| mm, kalman, activo 6/5/5, banda 5 | +6 ± 5 | -0,005 ± 0,001 | +0,007 ± 0,002 | +0,007 ± 0,009 | 54,9 | -0,000, +0,011 |
| mm, prud, byh 12/2/2, banda 0 | -275 ± 9 | -0,075 ± 0,002 | -0,065 ± 0,002 | +0,010 ± 0,010 | 62,0 | -0,044, -0,020 |
| mm, prud, byh 12/2/2, banda 2 (`fondo_ancla`) | -165 ± 13 | -0,031 ± 0,002 | -0,020 ± 0,002 | +0,057 ± 0,010 | 40,1 | +0,028, +0,053 |
| mm, prud, byh 12/2/2, banda 4 | -180 ± 20 | -0,034 ± 0,002 | -0,018 ± 0,003 | +0,061 ± 0,012 | 35,3 | +0,038, +0,064 |
| **Voto (todo o nada)** | | | | | | |
| mm, kalman, activo 6/5/5, 2 de 3 | +10 ± 3 | -0,003 ± 0,001 | +0,002 ± 0,002 | +0,001 ± 0,009 | 56,0 | -0,003, +0,006 |
| mm, kalman, activo, entra con 2 y sale con 0 | +18 ± 7 | -0,012 ± 0,002 | +0,009 ± 0,003 | -0,008 ± 0,013 | 51,5 | -0,005, +0,014 |
| mm, base, prud 6/5/5, 2 de 3 | -103 ± 10 | -0,038 ± 0,003 | -0,036 ± 0,004 | -0,047 ± 0,015 | 35,1 | -0,018, -0,029 |
| **Líder con histéresis** | | | | | | |
| mm, prud, byh, acumulado, margen 1/64 | -694 ± 17 | -0,335 ± 0,007 | -0,328 ± 0,007 | -0,363 ± 0,021 | 39,3 | +0,017, -0,036 |
| mm, prud, byh, ventana 512, margen 1/64 | -364 ± 15 | -0,180 ± 0,006 | -0,176 ± 0,006 | -0,219 ± 0,018 | 37,4 | +0,087, +0,063 |
| mm, guardia, byh, ventana 512, margen 1/64 | -316 ± 13 | -0,162 ± 0,006 | -0,163 ± 0,006 | -0,204 ± 0,019 | 43,6 | +0,062, +0,031 |
| mm, kalman, activo, ventana 512, margen 1/64 | +13 ± 11 | -0,015 ± 0,002 | -0,003 ± 0,003 | -0,013 ± 0,013 | 61,4 | -0,001, +0,015 |
| mm, base, prud, ventana 512, margen 1/64 | -104 ± 11 | -0,044 ± 0,003 | -0,043 ± 0,003 | -0,039 ± 0,013 | 45,1 | +0,027, +0,020 |
| **Pesos aprendidos con prior fuerte** | | | | | | |
| mm, prud, byh 12/2/2, ventana 512, margen 1/64, d = 4 | -184 ± 5 | -0,052 ± 0,002 | -0,052 ± 0,002 | +0,025 ± 0,010 | 48,1 | +0,024, +0,037 |
| lo mismo con d = 2 | -182 ± 7 | -0,052 ± 0,002 | -0,051 ± 0,002 | +0,025 ± 0,010 | 48,1 | +0,023, +0,037 |
| lo mismo con ventana 256 | -180 ± 5 | -0,060 ± 0,002 | -0,062 ± 0,002 | +0,012 ± 0,011 | 49,6 | +0,032, +0,041 |
| mm, kalman, activo 8/4/4, ventana 512, d = 4 | -65 ± 5 | -0,038 ± 0,001 | -0,037 ± 0,002 | -0,030 ± 0,010 | 76,3 | -0,013, -0,004 |
| **Ancla fija y el resto aprende** | | | | | | |
| mm, prud, byh 10/2/4, ancla 4/16 | -343 ± 19 | -0,089 ± 0,003 | -0,063 ± 0,003 | +0,059 ± 0,013 | 40,5 | +0,037, +0,062 |
| mm, guardia, byh 10/2/4, ancla 4/16 | -319 ± 18 | -0,079 ± 0,003 | -0,057 ± 0,003 | +0,051 ± 0,013 | 42,1 | +0,038, +0,060 |
| **Desfase** | | | | | | |
| `max_media` sola, tick anterior | -31 ± 6 | -0,021 ± 0,002 | -0,011 ± 0,003 | -0,016 ± 0,011 | 55,0 | -0,021, -0,015 |

Qué se ve:

1. **Ninguna variante mejora H3a.** La mejor es el empate exacto (`fondo_min` y los votos que por construcción deciden igual que `max_media`). Las que mejoran H3b (+0,006 a +0,009) empeoran H3a (-0,004 a -0,012).
2. **La comisión fija castiga las órdenes parciales.** Con pesos 8/4/4 de `max_media`, `kalman` y `activo`, la mezcla ideal de la sección 5 ganaba +0,005 y +0,017. La mezcla real, con una sola cuenta, pierde 0,038 y 0,034: pasa de 55 a 76 órdenes por ronda, y 21 órdenes de 5 pesos son los 105 pesos que explican la baja de 66 de patrimonio. Con una banda de 4/16 o más las órdenes vuelven a 55 y el resultado vuelve a cero. La meseta existe (bandas 4 a 6, pesos 8/4/4 y 6/5/5 dan lo mismo), pero es la meseta de "casi `max_media`".
3. **El ancla en comprar y mantener cambia puntos esperados por piso.** Con 2/16 a 4/16 de ancla se pierden 0,03 a 0,09 puntos esperados y el percentil 5 de la competencia de tres rondas sube 0,04 a 0,06 con H3a (con H3b, +0,02 a +0,06, dentro de dos errores salvo con banda ancha). En el estrés gana en media (+0,02 a +0,06) y en percentil 5 (+0,10 a +0,19). Con 8/16 de ancla ya pierde las dos cosas.
4. **Copiar al líder es lo peor.** -0,16 a -0,34 puntos con comprar y mantener entre los gestores: el fondo se cambia a comprar y mantener justo después de que subió. Es lo que predecía la falta de persistencia.
5. **Aprender los pesos no mejora al prior fijo**: -0,052 contra -0,046 con 12/2/2. Cambiar d, la ventana o el margen no mueve nada.
6. **La guardia como gestor no aporta sobre `prudente`** (-0,042 contra -0,046).
7. **Por evidencia y por campo** (`mediciones/tablas.md`): `fondo_rec` pierde en el remuestreo (-0,010 ± 0,001 y -0,003 ± 0,002) y gana en las plausibles (+0,003 ± 0,001 y +0,013 ± 0,002). Es la firma de `activo`, que el estudio 2 ya había descartado por lo mismo. `fondo_ancla` pierde en las dos evidencias y pierde más con el campo fuerte (-0,058 y -0,097).

## 7. Rondas de 20 000 ticks

`make largo`. Evidencia, semilla 0. Referencia `max_media`: 1,855 y 1,821 puntos en las interiores (4021 series) y 1,721 y 1,708 en la vista de parada (8000 series).

| Variante | Interiores: H1, H3a, H3b | Parada: H1, H3a, H3b | Parada: p5 de 3 rondas, H3a y H3b |
|----------|--------------------------|----------------------|-----------------------------------|
| `fondo_rec` | +520 ± 43, -0,000 ± 0,001, +0,016 ± 0,002 | +284 ± 25, -0,008 ± 0,001, +0,006 ± 0,001 | +0,006 ± 0,008, -0,017 ± 0,019 |
| `fondo_rec_ant` | +87 ± 67, -0,021 ± 0,002, +0,002 ± 0,002 | -87 ± 40, -0,028 ± 0,002, -0,008 ± 0,002 | -0,014 ± 0,011, -0,017 ± 0,019 |
| `fondo_ancla` | -3746 ± 101, -0,135 ± 0,002, -0,076 ± 0,002 | -3227 ± 63, -0,157 ± 0,002, -0,091 ± 0,002 | -0,118 ± 0,012, -0,083 ± 0,020 |
| `fondo_min` | +602 ± 86, -0,018 ± 0,002, -0,003 ± 0,002 | +296 ± 50, -0,019 ± 0,002, -0,005 ± 0,002 | -0,015 ± 0,011, -0,017 ± 0,015 |
| `fondo_min_ant` | -38 ± 94, -0,043 ± 0,003, -0,013 ± 0,003 | -210 ± 55, -0,046 ± 0,002, -0,019 ± 0,002 | -0,033 ± 0,012, -0,039 ± 0,025 |
| `max_media` sola, tick anterior | -568 ± 59, -0,040 ± 0,002, -0,018 ± 0,002 | -458 ± 35, -0,036 ± 0,002, -0,018 ± 0,002 | -0,020 ± 0,011, -0,017 ± 0,023 |
| mm, kalman, activo 8/4/4, banda 1 | -115 ± 62, -0,050 ± 0,002, -0,031 ± 0,002 | -299 ± 35, -0,061 ± 0,001, -0,043 ± 0,002 | -0,061 ± 0,011, -0,083 ± 0,020 |
| mm, kalman, activo 6/5/5, voto 2 de 3 | +359 ± 40, -0,006 ± 0,001, +0,012 ± 0,002 | +179 ± 24, -0,010 ± 0,001, +0,005 ± 0,001 | +0,000 ± 0,009, -0,017 ± 0,018 |
| mm, prud, byh 12/2/2 | -4034 ± 96, -0,154 ± 0,002, -0,088 ± 0,002 | -3336 ± 60, -0,167 ± 0,002, -0,100 ± 0,002 | -0,124 ± 0,012, -0,094 ± 0,024 |
| mm, guardia, byh 12/2/2 | -3387 ± 86, -0,129 ± 0,002, -0,079 ± 0,002 | -2982 ± 54, -0,155 ± 0,002, -0,093 ± 0,002 | -0,120 ± 0,012, -0,094 ± 0,024 |
| mm, prud, byh 12/2/2, pesos aprendidos | -2344 ± 47, -0,109 ± 0,002, -0,086 ± 0,002 | -1638 ± 30, -0,081 ± 0,002, -0,062 ± 0,002 | -0,040 ± 0,011, -0,072 ± 0,029 |
| mm, prud, byh 10/2/4, ancla 4/16 | -6073 ± 145, -0,247 ± 0,004, -0,113 ± 0,002 | -5254 ± 91, -0,298 ± 0,004, -0,154 ± 0,003 | -0,275 ± 0,015, -0,206 ± 0,029 |
| mm, prud, byh, líder con ventana 512 | -8502 ± 193, -0,498 ± 0,007, -0,276 ± 0,006 | -5960 ± 118, -0,388 ± 0,006, -0,214 ± 0,005 | -0,466 ± 0,019, -0,328 ± 0,027 |
| mm, kalman, activo, líder con ventana 512 | +1220 ± 127, -0,028 ± 0,003, +0,014 ± 0,003 | +460 ± 72, -0,045 ± 0,002, -0,005 ± 0,002 | -0,042 ± 0,014, -0,017 ± 0,019 |

- **En rondas largas el ancla sale muy cara** y deja de dar piso: -0,13 a -0,17 puntos con H3a y el percentil 5 de tres rondas también baja (-0,12). Lo que no se invierte en la reversión deja de componer.
- **`fondo_rec` repite el patrón de 2000 ticks**: cero o negativo con H3a, positivo con H3b. Con todas las series sale +0,015 y +0,027, pero esa es la vista inflada por el rebote en el precio 1 (sección 4 del README del arnés). La fila de parada no confirma el signo de H3a.
- **Aprender los pesos sí ayuda contra su propio prior en rondas largas** (-0,109 contra -0,154 con 12/2/2), porque lleva peso hacia `max_media`. Sigue lejos de `max_media` sola.
- **En el estrés a 20 000 ticks** el ancla gana con todas las series (+0,110 ± 0,007 y +0,138 ± 0,005) y pierde o empata en la vista de parada (-0,049 ± 0,004 y -0,001 ± 0,005). No se puede concluir.

## 8. Las cuatro hipótesis y el desfase

Configuraciones con nombre, evidencia, 2000 ticks (`mediciones/finales_n2000_parte1.txt`). H2 en diferencia es H1 (comprar y mantener es el mismo en cada serie). H3s y H3r son el torneo sobre la suma de las tres rondas, en patrimonio y en razón W/B&H.

| | H1: patrimonio, p5 | H2: p5 del exceso, por ronda y en 3 rondas | H2: razón W/B&H | H3a | H3b | H3s | H3r |
|-|--------------------|---------------------------------------------|-----------------|-----|-----|-----|-----|
| `max_media` (nivel) | 10 982, 8 754 | -2 710, -1 200 | 1,241 | 1,503 | 1,473 | | |
| `fondo_rec` | +6 ± 4, 8 756 | -2 699, -1 168 | -0,001 ± 0,002 | -0,004 ± 0,001 | +0,006 ± 0,002 | -0,005 ± 0,001 | -0,006 ± 0,001 |
| `fondo_rec_ant` | -16 ± 6, 8 704 | -2 681, -1 170 | -0,007 ± 0,002 | -0,015 ± 0,002 | -0,002 ± 0,003 | -0,020 ± 0,003 | -0,023 ± 0,003 |
| `fondo_ancla` | -165 ± 13, 8 692 | -2 367, -1 054 | -0,030 ± 0,004 | -0,031 ± 0,002 | -0,020 ± 0,002 | -0,061 ± 0,003 | -0,077 ± 0,003 |
| `fondo_min` | +1 ± 1, 8 752 | -2 710, -1 195 | +0,000 ± 0,000 | +0,000 ± 0,000 | +0,000 ± 0,000 | -0,000 ± 0,000 | -0,000 ± 0,000 |
| `fondo_min_ant` | -30 ± 6, 8 712 | -2 726, -1 221 | -0,007 ± 0,002 | -0,021 ± 0,002 | -0,011 ± 0,003 | -0,027 ± 0,003 | -0,028 ± 0,003 |

Estrés, 2000 ticks (7000 series): `fondo_rec` -0,000 ± 0,001 y +0,010 ± 0,002; `fondo_ancla` +0,028 ± 0,002 y +0,053 ± 0,003, con el percentil 5 de tres rondas en +0,118 ± 0,015 y +0,133 ± 0,026; `fondo_min` +0,001 ± 0,000 y +0,002 ± 0,001.

- **H2, que era donde el ancla podía ayudar.** A 2000 ticks el ancla sí reduce el riesgo relativo: el percentil 5 del exceso sobre comprar y mantener sube de -2 710 a -2 367 por ronda y de -1 200 a -1 054 en tres rondas. Lo paga con 165 de exceso medio (de 1 203) y, llevado a puntos, pierde: -0,077 ± 0,003 en el torneo sobre la razón (H3r). A 20 000 ticks ni siquiera reduce el riesgo en tres rondas: el percentil 5 del exceso baja de +3 941 a +3 314 en las interiores y de +1 363 a +980 en la vista de parada.
- **El percentil 5 de los puntos de la competencia.** `fondo_ancla` es la única familia que lo sube de forma clara a 2000 ticks (+0,057 ± 0,010 con H3a y +0,056 ± 0,025 con H3b). A 20 000 ticks lo baja (-0,118 ± 0,012 y -0,083 ± 0,020 en parada).
- **Mismo tick contra tick anterior.** Usar lo publicado en el tick anterior cuesta lo mismo que atrasar un tick a `max_media`: -0,021 ± 0,002 y -0,011 ± 0,003 a 2000 ticks, y -0,036 ± 0,002 y -0,018 ± 0,002 a 20 000 (parada). En `fondo_rec` cuesta -0,011 y -0,008 a 2000 ticks y -0,020 y -0,014 a 20 000 (resta de las filas `fondo_rec_ant` y `fondo_rec`). **El supervisor tiene que esperar a los gestores en el mismo tick.**

Veredicto oficial (`mediciones/veredicto_*.txt`, `veredicto --parada`, semilla 0):

| Candidata | 2000 ticks | 20 000 ticks | Literal | Motivo |
|-----------|------------|--------------|---------|--------|
| `fondo_rec` | NO_PASA | NO_PASA | no pasa | H3a empeora a 2000 ticks (-0,004 ± 0,001) y no mejora a 20 000. H3b sí pasa en los dos largos |
| `fondo_rec_ant` | NO_PASA | NO_PASA | no pasa | |
| `fondo_ancla` | NO_PASA | NO_PASA | no pasa | Los puntos esperados bajan en las cuatro filas. El percentil 5 sube a 2000 ticks y baja a 20 000 |
| `fondo_min` | NO_PASA | NO_PASA | no pasa | Igual a `max_media` a 2000 ticks. A 20 000 empeora H3a (-0,018 ± 0,002) |
| `fondo_min_ant` | NO_PASA | NO_PASA | no pasa | |

## 9. Fondo mínimo de demostración: `fondo_min`

`fondo:c=5,w0=6,w1=5,w2=5,m=2,v=9,mg=5,d=4,pp=1,vt=8`.

- **Tres gestores en papel**, uno por hilo: `max_media` (entra 3 bajo la media, sale en 0), `base` (entra 4) y `activo` (entra 2, sale medio punto arriba). Son la misma rutina con otras dos constantes, así que el código se comparte entre los tres hilos.
- **Contabilidad en papel sin productos**: cada gestor lleva su puntaje por acción (sección 4.1) y lo publica junto con su posición.
- **Reparto**: pesos 6/5/5 de 16 como prior. Cada 512 ticks el supervisor pasa 1/16 del gestor que menos ganó al que más ganó, si la ventaja supera 1/32 del precio y ningún peso se aleja más de 4/16 del prior.
- **Decisión**: voto ponderado. Si los pesos de los gestores que están adentro suman 8/16 o más, "comprar 63"; si no, "vender 63". No hay posiciones parciales, ni división, ni espejo de la cuenta real (el supervisor puede llevarlo para la telemetría, pero la decisión no lo usa).

Con el prior 6/5/5 dos gestores cualesquiera hacen mayoría, y como las tres bandas están anidadas el voto decide exactamente como `max_media` (la variante sin aprendizaje da 0 ± 0 en las 10 000 series). El fondo solo se aparta cuando el aprendizaje lleva un peso a 8 o más.

| | 2000 ticks, evidencia | 20 000 ticks, interiores | 20 000 ticks, parada |
|-|-----------------------|--------------------------|----------------------|
| `fondo_min`: H1 | +1 ± 1 | +602 ± 86 | +296 ± 50 |
| `fondo_min`: H3a, H3b | +0,000 ± 0,000, +0,000 ± 0,000 | -0,018 ± 0,002, -0,003 ± 0,002 | -0,019 ± 0,002, -0,005 ± 0,002 |
| `fondo_min_ant` (tick anterior): H3a, H3b | -0,021 ± 0,002, -0,011 ± 0,003 | -0,043 ± 0,003, -0,013 ± 0,003 | -0,046 ± 0,002, -0,019 ± 0,002 |

En la serie de práctica completa termina en 26 388 con 614 órdenes (`max_media`: 25 973 con 624).

Otras formas mínimas que se midieron y son peores (2000 ticks): líder con histéresis sobre el puntaje por acción con los mismos gestores, -0,035 y -0,026; pesos fijos 8/4/4 con banda 4 y cuenta real, -0,010 y -0,005; aprendizaje más rápido (ventana 256, paso 2), -0,012 y -0,010.

## 10. Costo e implementabilidad

No se escribió assembly. Las cifras de esta sección son **estimadas**, contando las operaciones del módulo en C con la ISA del Espino base: sin desplazador (un desplazamiento a la izquierda de n bits son n sumas, y uno a la derecha se hace con la memoria, decisión T11) y sin multiplicador.

### 10.1 Aritmética que necesita el supervisor

- Sumas, restas y comparaciones de 32 bits.
- Productos de precio (8 bits) por cantidad: uno para ejecutar la orden anterior en el espejo (cantidad de 6 bits, 6 pasos) y uno para el valor invertido `acciones * p` (8 pasos sobre los bits del precio). Solo en `fondo_rec` y `fondo_ancla`.
- Una división de cociente acotado a 63 (6 pasos de resta condicionada contra `16 p * 2^i`), solo cuando el objetivo es parcial. El tope de la compra `(caja - 5) / p` del espejo se resuelve con la misma búsqueda de 6 pasos, sin división aparte.
- `F * W` con F igual a 4, 8 o 12 (pesos 8/4/4): dos o tres sumas. No hay ningún desplazamiento a la derecha: todo se compara en dieciseisavos de peso.
- `fondo_min` no necesita productos ni divisiones.

En C las cuentas de `D` y del margen se hacen en 64 bits. En la placa caben en 32 bits mientras el patrimonio sea menor que 2^27 (134 millones), que se cumple en todas las series interiores. No se comprobó qué pasa más allá.

### 10.2 Instrucciones por tick y memoria (estimado)

| Hilo | `fondo_rec` | `fondo_min` |
|------|-------------|-------------|
| Gestor de media exponencial (`max_media`, `base`, `activo`): sondeo 4, regla 19, puntaje por acción 11, publicar 4 | 38 | 38 |
| Gestor `kalman`: 140 de la regla (estimación de `docs/algoritmo.md`) más lo mismo | 160 | no lo usa |
| Supervisor, tick común | 55 (afuera, sin orden que ejecutar) | 35 |
| Supervisor, peor caso | 200 (compra en el espejo 59, objetivo parcial 93, cadena `p * 2^i` 19, resto 29) | 80 (frontera de ventana, cada 512 ticks) |
| Productos de precio por cantidad en el peor tick | 2, más una división de 6 pasos | 0 |
| Tiempo de respuesta en la ronda 3 (presupuesto de 2262 ciclos, 4 ciclos por instrucción y por hilo) | unas 300 instrucciones del supervisor contando la espera por `kalman`: 1200 ciclos, 53 % | unas 80: 320 ciclos, 14 % |
| Palabras de datos | 31 (7 compartidas, 15 del supervisor, 9 de los gestores) | 20 |
| Palabras de programa, con la rutina de la media compartida | unas 445 | unas 165 |
| Total contra las 512 palabras de la memoria | unas 476: cabe con 36 de holgura | unas 185 |

El presupuesto de unas 540 instrucciones por hilo alcanza en los dos casos. Lo justo en `fondo_rec` es la memoria, no el tiempo.

### 10.3 Sincronización entre hilos

Cada palabra compartida tiene un solo hilo escritor (regla de la pieza A). El supervisor publica el precio y después el número de tick. Cada gestor espera el número de tick nuevo, calcula, publica su desempeño y su posición y al final su número de tick. Con `df=0` el supervisor espera a ver su propio número de tick en las tres palabras antes de leer las posiciones: así la decisión no depende de cuántas instrucciones demora cada gestor y el modelo en C no necesita modelar ciclos. Con `df=1` el supervisor lee sin esperar, y el modelo en C solo coincide si los gestores no alcanzan a publicar antes de esa lectura, cosa que habría que forzar leyendo las posiciones antes de publicar el precio.

### 10.4 Flujo de bytes de referencia

```bash
make bytes                 # fondo_rec y fondo_min sobre tb/practica.csv
sh bytes.sh build/arnes fondo_rec ../../../tb/practica.csv mediciones/bytes_fondo_rec_practica.txt
```

Deja en `build/` el archivo `decisiones_NOMBRE.csv` (mismo formato que el `decisiones.csv` del testbench), `bytes_NOMBRE.hex` (un byte por tick: el que la maestra lee en ese tick) y `traza_NOMBRE.csv` (cuenta real, posición y desempeño de cada gestor, pesos, F y decisión, tick a tick). En `mediciones/bytes_*_practica.txt` quedan el resultado, las huellas md5 y los primeros bytes.

| Configuración | Patrimonio en la serie de práctica | Órdenes | md5 de `bytes_NOMBRE.hex` |
|---------------|-------------------------------------|---------|---------------------------|
| `fondo_rec` | 25 141 | 594 | `beb4a4fe480edddc8a2b781c945a1ca1` |
| `fondo_min` | 26 388 | 614 | `4ce5af5bf2106e7820a14164199158e5` |

En `fondo_rec` el 99,9 % de los bytes son `bf`, `7f` o `00`: de 20 000 ticks, 14 753, 3 036 y 2 186. Las órdenes parciales son 25 bytes. Eso cuenta los bytes con una cantidad parcial, no las veces que hay que calcularla: el supervisor tiene un objetivo parcial, con sus productos y su comparación contra la banda, en 2 300 de los 20 000 ticks de la serie de práctica, y en el 11 % de los ticks en el conjunto evidencia (225 por ronda de 2000 ticks, medido en la auditoría). El camino caro de la sección 10.2 no es un caso raro. El `correr` del arnés acepta `--perdidos 2` para modelar los dos precios que se pierden en el reset del testbench oficial.

## 11. Cuántas variantes se probaron

- 88 variantes en la exploración a 2000 ticks: 64 de una lista fijada antes de mirar resultados y 24 definidas después, para probar la explicación de la comisión (bandas anchas, voto con histéresis) y para el fondo mínimo. Más 2 configuraciones con nombre que no estaban en la lista (las dos con desfase). Son 90.
- 22 de ellas a 20 000 ticks.
- Hiperparámetros tocados: conjunto de gestores (5), pesos, banda (0 a 6), forma de reparto (3), ventana (256, 512 y acumulado), margen (1/16 a 1/256), desviación máxima (2 a 5), paso, desfase, papel oficial o por acción, y umbrales del voto.
- Con 90 variantes y un criterio de dos errores, se esperan dos o tres falsos positivos por fila (estimado: 2,5 % de 90). No apareció ninguno que pase las dos lecturas a la vez. El resultado negativo no depende de qué variante se elija.

## 12. Qué falta y qué no se verificó

- **No se usó ninguna semilla reservada.** Todo es de la semilla 0. Como nada pasa con la semilla de exploración, la semilla reservada solo confirmaría un negativo. Así fue: el estudio de cierre (`../r4_final`) evaluó `fondo_rec` y `fondo_min` una vez con la semilla reservada 3 y ninguno pasa (sección 17).
- **Las instrucciones, la memoria y el tiempo de respuesta son estimaciones.** No hay assembly ni simulación en el barrel.
- **El veredicto oficial se corrió con el campo mixto y G = 10.** La sensibilidad al campo sale del comando `hipotesis` (ingenuo y fuerte con G = 10, en `mediciones/tablas.md`), no de las 9 combinaciones de `pruebas/veredictos.py`.
- **El cuarto gestor experimental** solo se probó como mecanismo.
- **No se probaron otras cajas ni comisiones.** La explicación por la comisión fija predice que con comisión 0 la mezcla 8/4/4 se acercaría a la ideal (+0,005 y +0,017). No se midió.
- **El estrés a 20 000 ticks** da signos distintos según la vista.
- **El error del percentil 5** que informa el arnés es unas 2,8 veces el real (auditoría del arnés). Las mejoras de percentil 5 de `fondo_ancla` a 2000 ticks con H3a superan cinco errores de todos modos.
- `make todo` se corrió como un solo comando al cerrar el estudio: 10 min 2 s, y las 19 salidas de `mediciones/` quedaron idénticas byte a byte a las que ya estaban (comparadas con `md5sum`). Eso sí está verificado.

## 13. Días de trabajo para llevarlo a calidad de competencia (estimado)

| Tarea | `fondo_min` | `fondo_rec` |
|-------|-------------|-------------|
| Assembly de los gestores y del supervisor sobre el barrel | 1,0 | 3,5 (incluye `kalman`, el espejo, el producto y la división) |
| Equivalencia byte a byte contra `bytes.sh` en simulación del barrel, 20 000 ticks y lotes | 1,0 | 1,5 |
| Testbench oficial 4/4, tiempos por tick medidos, bitstream | 0,5 | 0,5 |
| Documento de estudio y preguntas de defensa | 0,5 | 1,0 |
| Total | 3,0 | 6,5 |

Además depende de que el barrel (pieza A) sea el core de la edición que se pruebe con la maestra real el 26/11.

## 14. Reglas del enunciado

- **La decisión se calcula en el Espino.** Todo el fondo es software: los gestores y el supervisor son hilos del mismo core, y el hilo supervisor lee el precio y escribe `DECISION`. No hay hardware nuevo en esta pieza. Queda para el ayudante la pregunta de la pieza A: si un Espino con cuatro hilos sigue siendo Espino.
- **Sin información externa ni series guardadas.** Los gestores y las cuentas en papel dependen solo de los precios recibidos. Los pesos iniciales (8/4/4, 6/5/5, 12/2/2), la banda, la ventana y el margen son hiperparámetros elegidos con remuestreos y series sintéticas. No hay ninguna tabla derivada punto a punto de la serie de práctica. Lo que aprende (`fondo_min`) parte del prior y se ajusta en vivo.
- **Hardware con testbench.** No aplica.
- **Mismo programa en las tres rondas.** Sí. Con la espera en el mismo tick el resultado no depende del período.

## 15. Riesgos

- Llevar un fondo con ancla a la competencia cuesta 0,02 a 0,05 puntos esperados si las rondas son de 2000 ticks y 0,08 a 0,17 si son de 20 000.
- Si el supervisor no espera a los gestores, se pierden 0,01 a 0,05 puntos solo por el atraso.
- `fondo_rec` ocupa unas 476 de las 512 palabras (estimado). Cualquier agregado obliga a ampliar la memoria.
- Tres hilos más de software son tres lugares más donde equivocarse, sin ningún punto a cambio.
- Toda la evidencia sale de una serie de práctica, remuestreada o modelada. El único escenario en que el fondo con ancla gana es que la serie oculta sea de otro tipo (estrés) y las rondas cortas.

## 16. Veredicto

| Pieza | Veredicto | Razón |
|-------|-----------|-------|
| Fondo de estrategias como algoritmo de competencia | **Descartado** | Ninguna de las 90 variantes mejora los puntos esperados en las dos lecturas del torneo. Las cinco configuraciones con nombre dan `NO_PASA` |
| Reparto según el desempeño en papel (líder, pesos aprendidos) | **Descartado** | El desempeño en papel no persiste dentro de la ronda. Cuesta de 0,01 a 0,34 puntos |
| Ancla en comprar y mantener (`fondo_ancla`) | **Descartada**, documentada como seguro | Baja los puntos esperados. Sube el percentil 5 y gana en el estrés solo a 2000 ticks |
| `fondo_min` | **Exhibición** | La forma más barata de mostrar "un gestor por hilo" funcionando: +0,000 a 2000 ticks, -0,019 a 20 000, 3 días de trabajo |
| `fondo_rec` | Exhibición, si se quiere mostrar contabilidad y posiciones parciales | -0,004 y +0,006 a 2000 ticks, 6,5 días y la memoria casi llena |

La estrategia de competencia sigue siendo `max_media` sola. Si Nicolás quiere el fondo de todos modos, la recomendación es `fondo_min` en la edición de exhibición, con el supervisor esperando a los gestores en el mismo tick.

## 17. Auditoría

Revisión independiente hecha el 15/11 junto con la de los estudios de ejecución, de aprendizaje y de cierre. Todo está en `../auditoria_r34/` y se corre con `make todo` desde ahí. Aquí va lo que toca a este estudio.

### 17.1 Qué se revisó y qué dio

| Punto | Cómo | Resultado |
|-------|------|-----------|
| Información del futuro | Lectura de `fondo.c` y dos pruebas: el comando `causal` y una perturbación propia de los precios futuros (63 cortes por serie, entre ellos los bordes de las ventanas de 512 ticks) más una prueba de martingala, para las 5 configuraciones con nombre y 8 variantes: líder acumulado, líder con ventana, pesos aprendidos con ventana de 64 ticks, puntaje por acción, ancla, voto con histéresis y banda 0 | 0 fallas. Cada gestor ejecuta en su cuenta en papel su decisión anterior al precio que acaba de llegar y después decide; el puntaje por acción solo suma el cambio de precio si la acción ya estaba ejecutada; nada queda entre rondas |
| Supervisor | Escrito de nuevo a partir de la sección 4.2, con otra contabilidad y sin usar el núcleo: pesos fijos con banda, voto, pesos aprendidos y puntaje por acción | `fondo_rec` y `fondo_min`: 46 061 series de 36 archivos cada uno, 0 distintas. En la práctica completa, 25 141 con 594 órdenes para `fondo_rec` |
| Cifras | Torneo con el valor esperado exacto, semillas 0 y 3 | `fondo_rec` contra `max_media`, campo mixto, semilla 0 / semilla 3: -0,0037 ± 0,0009 / -0,0052 ± 0,0009 con H3a y +0,0055 ± 0,0015 / +0,0052 ± 0,0015 con H3b a 2000 ticks; -0,0086 / -0,0078 y +0,0059 / +0,0066 a 20 000 con parada. `fondo_min`: +0,0002 / -0,0003 a 2000 ticks y -0,0195 / -0,0198 con H3a a 20 000 con parada. Son las cifras de este documento |
| Cotas | Oráculo de selección y mezcla fija recalculados con el Kalman reescrito | Conjunto 1: +0,3417 ± 0,0050 y +0,3315 ± 0,0045. Conjunto 3: +0,1523 y +0,1855 a 2000 ticks, +0,0793 y +0,1049 a 20 000 con interiores. Conjunto 4: +0,1676 y +0,2013. Mezcla 3/8, 3/8, 2/8: +0,0049 ± 0,0014 y +0,0191 ± 0,0020. Coinciden con la sección 5. El conjunto 2 no se recalculó |
| Repetición | `make prueba`, `make cota`, `make tablas` y `make bytes` de esta carpeta, con el binario recompilado contra el núcleo actual | Los 19 archivos de `mediciones/` quedan idénticos |

### 17.2 Precisiones

1. **Sección 5, mezcla fija.** La mezcla 3/8, 3/8, 2/8 es la mejor por H3a. Por H3b la mejor es 0/8, 5/8, 3/8 (+0,023 a 2000 ticks). A 20 000 ticks la tabla es de las series interiores: con parada esa mezcla da -0,006 ± 0,001 con H3a y +0,011 ± 0,002 con H3b, y la mejor por H3a es `max_media` sola. Sin el filtro de interiores hay menos para ganar todavía.
2. **Sección 10.4, órdenes parciales.** Los 25 bytes con cantidad parcial no dicen cada cuánto corre el camino caro. El supervisor calcula un objetivo parcial en el 11 % de los ticks (225 por ronda de 2000 ticks y 2 250 por ronda de 20 000 en el conjunto evidencia).
3. **Sección 12, semilla reservada.** El estudio de cierre evaluó `fondo_rec` y `fondo_min` una vez con la semilla 3. Ninguno pasa.
4. Las cotas no se presentan como alcanzables: el texto dice que el oráculo no se puede cobrar y que la mezcla es ideal. Bien.

Ninguna cifra de las tablas cambió y ninguna medición se volvió a generar.

### 17.3 Lo que no se cubrió

- Las 88 variantes de la exploración no se volvieron a correr. De las configuraciones con nombre se reescribieron `fondo_rec` y `fondo_min`; `fondo_ancla` y las dos con desfase de un tick, no.
- La persistencia del líder y las correlaciones de la sección 5 no se recalcularon.
- Las instrucciones, la memoria y los días siguen siendo estimaciones.
