# Estudios de retorno 1 y 2 y arnés común de evaluación

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Tramo de factibilidad del Proyecto 4. Esta carpeta no agrega hardware ni cambia el programa de la placa: es un evaluador de estrategias y dos estudios hechos con él. Nada de lo que hay aquí queda dentro del diseño.

El arnés pasó después por una revisión independiente, con otro evaluador escrito desde cero (sección 17, "Auditoría"). No encontró errores en la contabilidad, el desfase, los puntajes, las series ni los rivales, y las cifras de este documento se reproducen. Sí cambió tres cosas que conviene leer antes de usar los números: cuánto valen las ventajas en rondas de 20 000 ticks (sección 17.4), cuánto depende el nivel de puntos del campo de rivales (sección 17.5) y qué tan blando es el criterio sobre el percentil 5 (sección 17.6).

## 1. Qué es y qué se construyó

| Pieza | Dónde | Qué hace |
|-------|-------|----------|
| Arnés de evaluación | `nucleo/` | Evaluador en C a nivel de tick, con la contabilidad oficial del testbench. Las estrategias son módulos separados con una interfaz mínima. Trae los candidatos del frente del algoritmo, 61 rivales, las hipótesis de puntaje, el torneo simulado y el veredicto del criterio de corte. |
| Series | `generar_series.py`, `build/series/` | Bloques de práctica, remuestreos y familias de `ref/series.py`, a 2000 y a 20 000 ticks, con tres semillas. Quedan guardadas para que otros evaluadores las lean. |
| Validación | `pruebas/validar.py`, `pruebas/validar_torneo.py`, `pruebas/validar_gemelo.py`, `pruebas/validar_series.py` | El arnés contra `ref/market.py`, `ref/motor/motor.c`, `ref/trader.py`, `ref/candidatos.py` y `ref/protocolo.py`, y el binario de la placa contra la regla base del arnés. |
| Estudio 1 | comando `frontera` | La frontera de candidatos con rondas de 2000 y de 20 000 ticks. |
| Estudio 2 | comandos `hipotesis` y `veredicto` | Los mismos candidatos bajo tres hipótesis de puntaje: patrimonio, exceso sobre comprar y mantener, y torneo contra rivales. |
| Ejemplo | `ejemplo/`, `ejemplo/minimo/` | Estrategias de juguete en archivos fuera del núcleo, con su Makefile. Son la plantilla para agregar una estrategia. |
| Auditoría | `auditoria/` | Revisión independiente del arnés: contabilidad contra la tarea del testbench, prueba de que nadie ve el futuro, evaluador propio con el torneo exacto, segunda implementación de los rivales y campos más fuertes (sección 17). |

### Tres evaluadores que no hay que confundir

- **El gemelo digital** (`ref/gemelo/gemelo.c`) simula el SoC ciclo a ciclo y ejecuta un `trade.hex`. Solo puede evaluar lo que existe en assembly.
- **El motor** (`ref/motor/motor.c`) evalúa a nivel de tick la familia paramétrica de `ref/candidatos.py` y nada más.
- **El arnés** de esta carpeta también evalúa a nivel de tick, pero cualquier estrategia escrita en C contra su interfaz. No simula el procesador.

Los dos estudios están hechos con el arnés, porque casi ningún candidato existe en assembly. El gemelo se usó donde aporta: para confirmar que `sw/trade.hex` decide igual que la regla base del arnés en las series nuevas de este tramo (sección 6). El motor se usó como referencia para validar el arnés.

## 2. Cómo se reproduce cada número

Todo se corre desde esta carpeta. Las salidas quedan en `mediciones/` y los productos intermedios en `build/`, que no se versiona.

| Comando | Qué hace | Salida | Tiempo medido |
|---------|----------|--------|---------------|
| `make arnes` | Compila `build/retorno`. | | segundos |
| `make series` | Genera las series que falten en `build/series/`. | `build/series/MANIFIESTO.txt` | unos 2 minutos la primera vez (no se volvió a medir) |
| `make comprobar-series` | Regenera una muestra de cada archivo con `ref/series.py` y la compara. | `mediciones/series_comprobacion.txt` | 8 s |
| `make validar` | Mercado, números conocidos, motor, referencia en Python, rivales, frontera anterior y causalidad. | `mediciones/validacion.txt`, `mediciones/causal.txt` | 5 min 16 s |
| `make gemelo` | `sw/trade.hex` en el gemelo digital contra la regla base del arnés. | `mediciones/gemelo.txt` | 2 min 5 s |
| `make ejemplo` | Compila y prueba la estrategia de ejemplo. | `mediciones/ejemplo.txt` | 3 s |
| `make exploracion` | Estudios 1 y 2 con la semilla 0. | `mediciones/*_s0.*` | 1 min 25 s con los resultados ya guardados en `build/resultados/` |
| `make validar-torneo` | Recalcula H3a y H3b por otro camino, en Python. Necesita `make exploracion`. | `mediciones/validacion_torneo.txt` | 3 s |
| `make final` | Lo mismo con la semilla reservada (2) y la comparación de las dos semillas. | `mediciones/*_s2.*`, `mediciones/semillas_0_y_2.md` | 1 min 57 s, calculando todo |
| `make todo` | Todo lo anterior, en orden. | | 7 min 11 s como un solo comando, con las series ya generadas (medido en la auditoría) |
| `make auditoria` | La auditoría independiente (`auditoria/Makefile`). Necesita `iverilog`, `vvp` y `yosys-config` en el `PATH`. | `mediciones/auditoria_*` | 5 min 57 s |

`HILOS` (por defecto 6) limita los hilos del arnés y `PROCESOS` los de Python.

Archivos de `mediciones/` y de dónde sale cada uno:

| Archivo | Contenido |
|---------|-----------|
| `validacion.txt`, `validacion_torneo.txt`, `causal.txt`, `gemelo.txt`, `ejemplo.txt`, `series_comprobacion.txt` | Validación (sección 6). |
| `series_manifiesto.txt` | Archivos de series con su cantidad, su largo y su huella. |
| `rivales.txt` | Los 61 rivales, su patrimonio en la serie de práctica y su peso en cada campo. |
| `bordes_s*.txt` | Cuánto tocan las series los límites 1 y 255 (sección 4). |
| `frontera_s*.txt` | Estudio 1 completo, con el desglose por familia. |
| `hipotesis_s*.txt` | Estudio 2 completo: cuatro conjuntos, tres vistas, sensibilidad al campo y a G. |
| `veredictos_s*.txt` | Criterio de corte de cada candidato contra la regla base. |
| `duelos_s*.txt` | Criterio de corte de `kalman`, `activo` y `guardia` contra `max_media`. |
| `tablas_s*.md` | Las tablas principales en Markdown. De aquí salen las tablas de este documento. |
| `semillas_0_y_2.md` | Las dos semillas lado a lado. |
| `auditoria_*.txt`, `auditoria_tablas.md` | Salidas de la auditoría (sección 17). |

## 3. Interfaz: cómo se agrega una estrategia y cómo se evalúa

### 3.1 La interfaz

Una estrategia es una variable de tipo `Estrategia` (`nucleo/nucleo.h`):

```c
typedef struct Estrategia {
  const char *nombre;        /* con este nombre se pide: "mia" o "mia:a=1,b=2" */
  const char *descripcion;
  size_t tam_cfg;            /* bytes de la configuración (parámetros) */
  size_t tam_estado;         /* bytes del estado de una ronda */
  int  (*configurar)(void *cfg, const char *parametros, char *error, size_t tam_error);
  void (*iniciar)(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla);
  int  (*decidir)(void *estado, int precio, const Cuenta *propia);
  void (*contadores)(const void *estado, int aux[4]);   /* opcional */
  void (*liberar)(void *cfg);                           /* opcional */
} Estrategia;
```

- `decidir` recibe el precio que acaba de llegar y devuelve el byte de `DECISION`. El arnés lo ejecuta al precio siguiente, igual que la maestra.
- `propia` es una copia de la cuenta (caja, acciones, patrimonio, órdenes y acciones de la última orden) después de ejecutar, a ese mismo precio, la decisión anterior. Es lo que el programa de la placa puede llevar por su cuenta. Una estrategia que no lleva contabilidad la ignora.
- `iniciar` recibe las reglas (caja inicial y comisión) y una semilla distinta para cada serie. Una estrategia con azar debe usar esa semilla y no otra fuente.
- `contadores` entrega hasta 4 números para los informes.

Para llevar varias estrategias en papel dentro de otra (un gestor, un fondo) el núcleo entrega `instancia_crear`, `instancia_iniciar`, `instancia_decidir` y `cuenta_ejecutar`. `ejemplo/mi_estrategia.c` lo muestra con la estrategia `seguidor`.

### 3.2 Por qué una estrategia no puede mirar el futuro

`decidir` recibe un solo precio, por valor, y una copia de la cuenta. Nunca recibe la serie, un puntero a ella, el número de tick ni el largo de la ronda. Además el comando `causal` lo comprueba para cualquier estrategia: cambia la serie desde un tick en adelante, la corta, y repite la ronda después de otra distinta, y exige que las decisiones anteriores sean idénticas.

### 3.3 Ejemplo que compila

`ejemplo/minimo/mia.c` es la estrategia más chica posible y `ejemplo/mi_estrategia.c` muestra la interfaz completa (uso de la cuenta propia y de otras estrategias por dentro). Lo mínimo es esto, en una carpeta propia:

```c
/* mia.c */
#include "nucleo.h"

typedef struct { int k, entra; } Cfg;
typedef struct { const Cfg *c; int ini, S, pos; } Estado;

static int configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  Cfg *c = cfg;
  c->k = 5; c->entra = 3;
  const Campo campos[] = {{"k", &c->k}, {"entra", &c->entra}};
  return leer_campos(parametros, campos, 2, error, tam);
}

static void iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  (void)reglas; (void)semilla;
  ((Estado *)estado)->c = cfg;
}

static int decidir(void *estado, int precio, const Cuenta *propia) {
  Estado *s = estado;
  (void)propia;
  if (!s->ini) { s->ini = 1; s->S = precio << s->c->k; }
  int dev = (precio << s->c->k) - s->S;
  s->S += dev >> s->c->k;
  if (dev < -(s->c->entra << s->c->k)) s->pos = 1; else if (dev > 0) s->pos = 0;
  return s->pos ? COMPRAR_63 : VENDER_63;
}

static const Estrategia mia = {"mia", "ejemplo minimo", sizeof(Cfg), sizeof(Estado),
                               configurar, iniciar, decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(mia)
```

```make
# Makefile de la carpeta propia (por ejemplo factibilidad/otro_estudio/)
include ../retorno/nucleo/nucleo.mk
build/arnes: $(NUCLEO_FUENTES) $(NUCLEO_CABECERAS) mia.c
	@mkdir -p build
	$(NUCLEO_CC) -o $@ $(NUCLEO_FUENTES) mia.c $(NUCLEO_LIBS)
```

El binario que resulta tiene todos los comandos del arnés y conoce la estrategia nueva por su nombre:

```bash
build/arnes listar
build/arnes causal --estrategia mia
build/arnes correr --estrategia "mia:k=5,entra=3" --serie ../../tb/practica.csv
build/arnes resumen --conjunto remuestreo --largo 2000 --semilla 0 --estrategia "base;max_media;mia"
build/arnes hipotesis --largo 2000 --semilla 0 --candidatos "base;max_media;mia"
build/arnes veredicto --candidata mia --referencia base --semilla 0
python3 ../retorno/pruebas/veredictos.py --arnes build/arnes --candidatas "mia;mia:entra=4" --referencia max_media --semilla 0
```

`make ejemplo` compila los dos ejemplos y corre esos mismos pasos (`mediciones/ejemplo.txt`). El ejemplo mínimo es `ejemplo/minimo/mia.c`, el mismo texto de arriba: con `entra=4` reproduce los 27 062 con 388 órdenes de la regla base en la serie de práctica, y sin parámetros da las mismas cifras que `max_media` en los 5000 remuestreos (media, mediana, percentil 5, peor, mejor y órdenes).

### 3.4 El veredicto del criterio de corte

`veredicto --candidata A --referencia B` entrega el criterio que fijó Nicolás para las piezas de algoritmo: se descarta si no mejora los puntos esperados del torneo sin empeorar el percentil 5.

- Se evalúa en el conjunto `evidencia` (remuestreo y series plausibles, mitad y mitad), con el campo mixto y G = 10 rivales, en las dos lecturas del puntaje (H3a y H3b) y en los dos largos de ronda. A 20 000 ticks cuentan las series interiores (sección 4).
- Una fila pasa si la media de los puntos mejora en más de dos errores estándar y el percentil 5 de la competencia de tres rondas no baja en más de dos errores. El veredicto es `PASA` solo si pasan las cuatro filas.
- La salida trae cada diferencia con su error, el juicio de cada fila, las filas informativas (remuestreo, plausibles, estrés, H1, H3s y H3r) y además el veredicto literal, que mira solo el signo.
- `pruebas/veredictos.py` lo repite para varias candidatas y para las 9 combinaciones de campo y G. Con `--arnes` usa un binario propio y con `--sin-sensibilidad` corre solo el campo mixto con G = 10.
- La semilla 2 es la reservada. El comando avisa cuando se usa. La regla es la misma del tramo anterior: una vez por candidata final, sin ajustar nada después de mirarla.
- Con `--parada` (agregada en la auditoría) el comando suma filas informativas a 20 000 ticks con todas las series de la evidencia, cada una corrida solo hasta el primer tick en que el precio sale de 21 a 249. No cambia el veredicto ni el resto de la salida. **Conviene pedirla siempre que el resultado a 20 000 ticks importe**: si la fila de parada no confirma el signo de la fila de interiores, la mejora a 20 000 ticks viene del filtro y no de la estrategia (sección 17.4). `resumen`, `frontera` e `hipotesis` también la aceptan.

### 3.5 Detalles que conviene saber

- Los resultados de las estrategias del núcleo se guardan en `build/resultados/`, con la huella de los fuentes y de las series. Un binario compilado con el mismo núcleo los lee y no recalcula los rivales. Las estrategias de afuera se evalúan siempre.
- Variables de entorno: `HILOS`, `RETORNO_SERIES` (otra carpeta de series), `RETORNO_RESULTADOS` (otra carpeta de resultados), `RETORNO_SIN_CACHE=1` (recalcular todo) y `RETORNO_GUARDAR=1` (escribir resultados; solo lo usa el Makefile de esta carpeta).
- `--caja` y `--comision` cambian las reglas en cualquier comando.
- Los candidatos del núcleo se nombran por su alias corto (`max_media`) y cualquier punto de la familia paramétrica por su especificación (`param:E=80,X=0`).
- `resumen`, `frontera`, `hipotesis` y `veredicto` aceptan `--interior`.

## 4. Series guardadas

`build/series/`, 77 archivos, 548 MB. No se versionan: se regeneran con `make series`. `make comprobar-series` verifica que son las de `ref/series.py`.

Formato de cada archivo, el mismo de `ref/motor.py`:

```
int32 ns        número de series del lote (little endian)
int32 n         ticks por serie
ns * n bytes    un byte por precio (1 a 255), serie tras serie
```

| Archivo | Series | Qué es |
|---------|--------|--------|
| `bloques_n2000.bin` | 10 de 2000 | Los 10 bloques de la serie de práctica. |
| `practica_n20000.bin` | 1 de 20 000 | La serie de práctica completa. |
| `remuestreo_s<S>_n2000.bin` | 5000 | Remuestreo por bloques de 100 incrementos. |
| `<plausible>_s<S>_n2000.bin` | 2500 cada una | `modelo`, `modelo_vecino`, `dos_componentes`, `cambio_volatilidad`. |
| `<estrés>_s<S>_n2000.bin` | 1000 cada una | `paseo`, `tendencia`, `reversion`, `saltos`, `cambio_de_caracter`, `volatil`, `nivel_bajo`. |
| `<degenerada>_s<S>_n2000.bin` | 200 cada una | `plana`, `borde_bajo`, `borde_alto`. Solo prueban la aritmética. |
| `remuestreo_s<S>_n20000.bin` | 4000 | |
| `<plausible>_s<S>_n20000.bin` | 1000 cada una | |
| `<estrés>_s<S>_n20000.bin` | 400 cada una | |
| `<degenerada>_s<S>_n20000.bin` | 50 cada una | |

Son exactamente las series de `series.lote(familia, cantidad, largo, semilla)`: mismo generador y misma semilla por serie.

Semillas:

| Semilla | Uso | Largos |
|---------|-----|--------|
| 0 | Exploración. | 2000 y 20 000 |
| 1 | La reservada del tramo anterior. Aquí solo se usa para reproducir `docs/mediciones/frontera.txt`. | 2000 |
| 2 | La reservada de este tramo. No se miró hasta tener escritas las conclusiones de la semilla 0 (`AVANCE.md`). | 2000 y 20 000 |

Conjuntos con nombre que entiende el arnés: `bloques`, `practica`, `remuestreo`, `plausibles`, `estres`, `degeneradas`, cualquier familia, y `evidencia`, que junta todos los remuestreos con la misma cantidad de series plausibles repartida entre las cuatro familias (10 000 series a 2000 ticks y 8000 a 20 000).

**A 20 000 ticks los bloques de práctica son una sola serie**, la serie completa. Se informa su patrimonio, pero no hay media, percentil ni error: no es una muestra.

**El remuestreo a 20 000 ticks no es evidencia nueva.** Cada remuestreo de 20 000 ticks se arma con 200 tramos de 100 incrementos sacados, con reposición, de los mismos 19 999 incrementos de la serie de práctica. Mide qué pasa al reordenar el mismo material, no qué pasaría con otra serie. La evidencia independiente a ese largo son las familias plausibles.

### Límites 1 y 255 en las series largas

`ref/series.py` hace rebotar el nivel cuando toca 1 o 255. A 2000 ticks casi no ocurre. A 20 000 ticks el nivel pasea lo suficiente para que ocurra seguido (`mediciones/bordes_s0.txt`, semilla 0):

| Conjunto | 2000 ticks: tocan 1, mínimo de 20 o menos, tocan 255 | 20 000 ticks: tocan 1, mínimo de 20 o menos, tocan 255 |
|----------|------------------------------------------------------|---------------------------------------------------------|
| Remuestreo | 0,1 %, 0,7 %, 0,0 % | 31,4 %, 41,1 %, 8,8 % |
| Plausibles | 0,5 %, 1,3 %, 0,6 % | 20,3 %, 26,8 %, 20,7 % |
| Estrés | 7,6 %, 17,7 %, 3,6 % | 47,7 %, 56,5 %, 37,4 % |

Con el precio cerca de 1, un cambio de una unidad es un cambio de 50 o 100 %, y el rebote garantiza que el precio vuelve a subir. La regla de reversión multiplica el patrimonio varias veces en esas series: a 20 000 ticks la regla base promedia 22 898 en los remuestreos cuyo mínimo es mayor que 20 y 61 217 en los demás. Eso es un efecto del rebote del generador de pruebas y no una propiedad de la serie de práctica, cuyo precio se mueve entre 72 y 190 (`mediciones/series_comprobacion.txt`).

Por eso cada tabla a 20 000 ticks sale dos veces:

- **Interiores**: solo las series cuyo precio se queda siempre entre 21 y 249. Es la vista principal y la que usa el criterio de corte.
- **Todas**: sin filtrar. Se informa siempre al lado.

La auditoría agregó una tercera vista, que es la que no tiene ninguno de los dos defectos:

- **Parada**: todas las series, pero cada una se corre solo hasta el primer tick en que el precio sale de 21 a 249 (incluido ese tick, con un mínimo de 200). La ronda termina cuando la serie entra a la zona de los límites, así que el rebote no infla nada, y la regla de corte no mira el futuro, así que no selecciona. El costo es que las rondas quedan más cortas: 15 270 ticks de media, con mediana de 20 000. Se pide con `--parada`.

El filtro tiene un costo que hay que tener presente: selecciona por la trayectoria, así que deja fuera las series con caídas largas. La auditoría lo midió con los primeros 2000 ticks de las series de 20 000: en las que el filtro deja, comprar y mantener termina ese primer tramo en 10 059 y el percentil 5 de la regla base es 9 127; en las que el filtro saca, 9 529 y 8 541 (semilla 0, `mediciones/auditoria_tablas.md`). El filtro mira la serie completa y eso ya se nota en el primer décimo de la ronda: las series interiores son más favorables que las que saldrían de verdad. En las familias de estrés deja muy pocas series (602 de 2800 con la semilla 0, de las cuales 400 son de `reversion` y ninguna de `tendencia` ni de `cambio_de_caracter`, que en la salida aparecen con `-nan`). **Para el estrés a 20 000 ticks hay que mirar la tabla con todas las series.** Los umbrales 21 y 249 se fijaron con la semilla 0.

## 5. Rivales e hipótesis de puntaje

### 5.1 Rivales

61 parametrizaciones en 6 clases (`nucleo/e_rivales.c`, `mediciones/rivales.txt`), fijadas antes de mirar ningún resultado del torneo:

| Clase | Cantidad | Parametrizaciones |
|-------|----------|-------------------|
| Cruce de medias | 14 | Medias exponenciales y ventanas, con y sin banda. |
| Momentum | 11 | Horizonte de 1 a 50 ticks y umbral de 1 a 4. |
| Comprar y mantener | 4 | Hecho por el programa, con 63, 20 o 10 acciones por orden. |
| No operar | 1 | |
| Reversión simple | 25 | Media exponencial o suma móvil, entrada de 2 a 6, salida 0 o 1, y momentum invertido. Incluye la regla base (`k=5,a=4,b=0`) y `max_media` (`k=5,a=3,b=0`). |
| Azar | 6 | Probabilidad de operar de 1 %, 10 % o 100 % por tick. |

Las clases que siguen una señal traen tres formas ingenuas de dimensionar la orden: repetir "63" en cada tick (posición objetivo), una sola orden de 63 al cambiar la señal, y 10 acciones por tick mientras dure la señal.

Composición del campo. En cada ronda se sortean G grupos rivales:

| Campo | Cómo se sortea cada grupo |
|-------|---------------------------|
| `ingenuo` | Una de las seis clases con la misma probabilidad y cualquier parametrización de la clase. |
| `mixto` | La clase igual, pero dentro de la clase una de las tres parametrizaciones que más ganan en la serie de práctica completa: lo que haría un grupo que ajusta con ella. |
| `fuerte` | Como el mixto, pero el 60 % de los grupos llega a una reversión ajustada. |

### 5.2 Hipótesis

| | Qué se puntúa |
|-|---------------|
| H1 | Patrimonio final. |
| H2 | Exceso sobre comprar y mantener, como diferencia `W - B&H` y como razón `W / B&H`. |
| H3a | Torneo, lineal en patrimonio: `2 * (W - peor) / (mejor - peor)` entre los G rivales y nosotros. |
| H3b | Torneo, lineal en el puesto: `2 * (rivales bajo nosotros) / G`. Los empates valen medio puesto. |
| H3s, H3r | Como H3a, pero sobre la suma del patrimonio de las tres rondas (H3s) o sobre la suma de `W / B&H` (H3r). Son la lectura del enunciado en que el puntaje se calcula una vez para toda la competencia. |

El enunciado dice que el puntaje "depende del patrimonio final respecto a la referencia comprar y mantener y de la posición relativa entre los grupos" y que se reparte "de forma lineal según su posición relativa". H3a y H3b son las dos lecturas de "lineal". H3r es la que toma además el "respecto a comprar y mantener".

Una competencia son tres rondas con series independientes y los mismos rivales en las tres. Para cada hipótesis se informa media, percentil 5, peor caso y error estándar, por ronda y por competencia. Las comparaciones entre dos estrategias son pareadas: las dos enfrentan las mismas series y los mismos campos.

- El error de la media se calcula entre series.
- El percentil 5 de una competencia se estima repartiendo las series en tríos sin repetir, 6 veces. Su error sale de 100 remuestreos de las competencias dentro de cada reparto y es conservador.
- "Mejora" y "empeora" significan más de dos errores estándar.

## 6. Validación del arnés

Todo con cero diferencias. Las salidas se volvieron a generar con los fuentes actuales el 14/11.

| Prueba | Contra qué | Resultado |
|--------|------------|-----------|
| Mercado | `ref/market.py`, flujos de órdenes al azar con todas las acciones (incluida la 11), cantidades de 0 a 63, precios de 1 a 255 y distintas cajas y comisiones | 400 flujos, 334 250 ticks, 113 673 órdenes ejecutadas, 0 filas distintas |
| Números conocidos | Los del tramo anterior | Regla base 27 062 con 388 órdenes y comprar y mantener 6 497 en la serie completa. Media 11 068,7 (11 069) y peor 9 720 en los 10 bloques. 26 795 con los dos precios que se pierden en el testbench. 24 143 con la suma móvil de 64 |
| `decisiones.csv` | `ref/trader.py` | 20 000 filas con 0, 1 y 2 precios perdidos: idénticos byte a byte |
| Familia paramétrica | `ref/motor/motor.c`, serie por serie | 74 configuraciones (14 candidatos y 60 al azar), 32 lotes, 33 561 series, 2 483 514 corridas, 0 distintas |
| Candidatos | `ref/candidatos.py` y `ref/trader.py`, serie por serie | 14 candidatos, 431 series de 32 lotes a los dos largos, 6 465 corridas, 0 distintas |
| Rival de reversión con k=5, a=4, b=0 | La regla base | 11 210 series, 0 distintas |
| Rivales de suma móvil, comprar 63 y no operar | `ref/protocolo.py` | 273 corridas, 0 distintas |
| Frontera del tramo anterior | `docs/mediciones/frontera.txt`, semillas 0 y 1 | 552 cifras, 0 distintas |
| Causalidad | Cambiar el futuro, cortar la serie y repetir la ronda | 82 estrategias, 6 396 comparaciones, 0 fallas |
| Puntajes del torneo | Cálculo independiente en Python sobre los 5000 remuestreos de 2000 ticks: pesos de los rivales rehechos desde la regla, valor esperado exacto de H3b y un sorteo propio para H3a | Pesos de los 61 rivales iguales en los tres campos. H3b: 36 cifras, ninguna fuera de 4 errores del sorteo (peor caso 2,0). H3a: 8 cifras, ninguna fuera de 4 errores (peor caso 1,7) |
| Series guardadas | `ref/series.py` | 77 archivos, 176 series regeneradas, 0 distintas, 0 precios fuera de 1 a 255 |
| Binario de la placa | `sw/trade.hex` en el gemelo digital contra la regla base del arnés | Período de 0,1 ms: las 33 561 series de la semilla 0 a los dos largos, 264 240 000 ticks, 0 distintas y ningún precio sin respuesta. Períodos de 1 ms y 10 ms y core segmentado: 1811 series y 9 040 000 ticks cada uno, 0 distintas. Peor caso de respuesta 48 ciclos (26 con el core segmentado) |
| Estrategias de afuera | `ejemplo/` y `ejemplo/minimo/` | Compilan contra el núcleo, pasan la causalidad y entregan su veredicto. La mínima, escrita solo con la interfaz, reproduce los 27 062 con 388 órdenes de la regla base |

Al cerrar los estudios quedaban sin referencia independiente los rivales de cruce de medias, momentum y azar, y el percentil 5 de la competencia de tres rondas. La auditoría los cubrió: escribió las seis clases de rivales por segunda vez y coinciden serie por serie con las del arnés (1 033 149 corridas, 0 distintas; los de azar, que usan otro generador, coinciden en distribución), y rehízo el percentil 5 con otro sorteo. Además comparó la contabilidad con la tarea `ejecutar` copiada textual del testbench y simulada con Icarus, y el desfase con el testbench oficial sin modificar. El detalle está en la sección 17.

## 7. Estudio 1: la frontera en los dos horizontes

Las tablas de esta sección y de la siguiente son las de la semilla reservada (`mediciones/tablas_s2.md`). Las de la semilla 0 están en `mediciones/tablas_s0.md` y la comparación en `mediciones/semillas_0_y_2.md`. Las diferencias son pareadas contra la regla base, con su error estándar.

Candidatos: `base` (E=128, X=0), `max_media` (E=96), `kalman` (dos estados, bandas equivalentes a `max_media`), `kalman_base` (bandas equivalentes a la base), `activo` (E=64, X=16), `guardia` (`max_media` con saltos y guardia), `guardia_tope` (además tope de pérdida), `prudente` (E=192, X=-32). Los extras de `ref/frontera.py` (`base_guardia`, `base_tope`, `base_fuerte`, `prud_guardia`) y dos variantes nuevas para rondas largas (`guardia_tope_r` y `base_tope_r`, con el tope rearmado a los 2000 ticks) están en los archivos de mediciones.

### 7.1 Rondas de 2000 ticks

10 bloques de práctica, 5000 remuestreos, 10 000 series plausibles y 7000 de estrés.

| Candidato | Bloques: media, peor | Remuestreo: media, dif., p5 | Plausibles: media, dif., p5 | Estrés: p5, peor |
|-----------|----------------------|-----------------------------|------------------------------|------------------|
| `base` | 11 069, 9 720 | 10 766, 8 966 | 10 914, 8 648 | 5 637, 256 |
| `max_media` | 11 043, 9 620 | 10 832, +66 ± 11, 8 778 | 11 066, +152 ± 12, 8 552 | 5 202, 172 |
| `kalman` | 11 002, 9 678 | 10 874, +108 ± 11, 8 802 | 11 057, +143 ± 14, 8 523 | 5 219, 156 |
| `kalman_base` | 11 102, 10 000 | 10 795, +29 ± 5, 9 015 | 10 893, -21 ± 6, 8 636 | 5 651, 256 |
| `activo` | 10 826, 8 728 | 10 720, -46 ± 17, 8 438 | 11 244, +330 ± 19, 8 296 | 4 590, 116 |
| `guardia` | 11 018, 9 024 | 10 727, -40 ± 13, 8 811 | 10 863, -50 ± 16, 8 339 | 6 733, 355 |
| `guardia_tope` | 11 018, 9 024 | 10 705, -61 ± 14, 8 738 | 10 713, -200 ± 24, 7 980 | 6 726, 1 753 |
| `prudente` | 10 712, 10 000 | 10 649, -118 ± 14, 9 281 | 10 616, -297 ± 17, 9 021 | 6 800, 219 |

Es la misma frontera del tramo anterior, ahora con una tercera semilla: `max_media` gana 66 y 152 (79 y 150 con la semilla 1), la guardia cuesta 40 y 50, y `prudente` cambia 118 y 297 de media por 315 y 373 de percentil 5. A este largo hay un intercambio real entre media y percentil 5.

### 7.2 Rondas de 20 000 ticks

Series interiores: 1994 remuestreos y 2010 series plausibles. La columna de práctica es la serie completa, una sola serie.

| Candidato | Práctica completa | Remuestreo: media, mediana, dif., p5 | Plausibles: media, mediana, dif., p5 |
|-----------|-------------------|--------------------------------------|---------------------------------------|
| `base` | 27 062 | 23 862, 20 955, 12 315 | 22 314, 17 046, 9 899 |
| `max_media` | 25 973 | 26 533, 22 861, +2 671 ± 149, 12 916 | 25 642, 19 549, +3 329 ± 183, 10 213 |
| `kalman` | 26 450 | 27 300, 23 618, +3 438 ± 153, 13 074 | 25 591, 19 258, +3 277 ± 187, 10 396 |
| `kalman_base` | 26 575 | 24 392, 21 342, +530 ± 58, 12 484 | 22 162, 16 963, -152 ± 68, 9 962 |
| `activo` | 19 234 | 25 709, 21 884, +1 847 ± 231, 11 468 | 30 989, 23 260, +8 676 ± 419, 10 840 |
| `guardia` | 23 399 | 23 632, 20 450, -230 ± 169, 11 602 | 21 635, 17 189, -678 ± 212, 9 653 |
| `guardia_tope` | 23 399 | 21 754, 19 185, -2 108 ± 214, 9 124 | 18 156, 15 468, -4 158 ± 375, 7 666 |
| `guardia_tope_r` | 23 399 | 22 546, 19 787, -1 316 ± 185, 11 160 | 19 665, 16 344, -2 649 ± 293, 8 814 |
| `prudente` | 19 790 | 18 994, 17 412, -4 869 ± 177, 11 452 | 16 148, 12 808, -6 165 ± 258, 9 220 |

Estas cifras son las de las series interiores, que la auditoría mostró más favorables que la realidad (sección 4). La vista de parada, sin selección, deja la ventaja de `max_media` sobre la base en +1 899 ± 74 y +1 757 ± 71 de patrimonio (semillas 0 y 2, conjunto evidencia) contra +3 278 ± 124 y +3 001 ± 118 con las interiores. El signo de todas las comparaciones de esta sección se mantiene, salvo el de `activo` en puntos de torneo (sección 17.4).

Todas las series (4000 remuestreos, 4000 plausibles y 2800 de estrés). Aquí las medias están infladas por las series que rebotan cerca del precio 1: hay que mirar la mediana y el percentil 5.

| Candidato | Remuestreo: media, mediana, p5 | Plausibles: media, mediana, p5 | Estrés: mediana, p5 |
|-----------|--------------------------------|--------------------------------|---------------------|
| `base` | 37 984, 24 238, 11 878 | 46 934, 19 970, 9 987 | 22 988, 2 697 |
| `max_media` | 45 492, 27 201, 12 697 | 57 749, 22 740, 10 515 | 31 747, 2 840 |
| `kalman` | 46 024, 28 123, 12 798 | 57 257, 22 751, 10 505 | 32 415, 2 821 |
| `activo` | 55 922, 26 210, 11 512 | 79 951, 27 787, 11 260 | 62 196, 2 760 |
| `guardia` | 38 563, 23 914, 11 586 | 44 264, 19 525, 9 378 | 27 005, 4 587 |
| `guardia_tope` | 18 620, 16 299, 7 245 | 17 135, 14 169, 6 927 | 10 405, 6 170 |
| `guardia_tope_r` | 20 940, 18 201, 6 129 | 19 844, 15 971, 5 455 | 13 372, 2 823 |
| `prudente` | 26 770, 19 399, 11 045 | 29 087, 14 274, 8 888 | 17 369, 3 970 |

### 7.3 Qué cambia al alargar la ronda y por qué

Conjunto evidencia. El crecimiento es la media geométrica del patrimonio final llevada a 2000 ticks.

| Candidato | Crecimiento por cada 2000 ticks: ronda de 2000, de 20 000 (interiores), de 20 000 (todas) | Órdenes por cada 2000 ticks | Ronda de 2000: pausa, tope, ticks vetados | Ronda de 20 000 (interiores): pausa, tope, ticks vetados |
|-----------|------------|------------|------------|------------|
| `base` | +7,06 %, +7,32 %, +10,62 % | 34,6, 42,1, 82,3 | | |
| `max_media` | +7,83 %, +8,47 %, +12,19 % | 54,6, 71,1, 130,7 | | |
| `kalman` | +7,98 %, +8,59 %, +12,27 % | 55,0, 72,6, 131,5 | | |
| `activo` | +7,83 %, +9,01 %, +13,65 % | 75,1, 102,4, 193,7 | | |
| `guardia` | +6,50 %, +7,14 %, +10,32 % | 53,4, 65,2, 117,2 | 2,5 %, 0,0 %, 0,8 % | 26,1 %, 0,0 %, 1,5 % |
| `guardia_tope` | +5,93 %, +5,88 %, +4,48 % | 51,2, 56,1, 50,2 | 2,3 %, 3,5 %, 2,1 % | 24,0 %, 17,8 %, 9,4 % |
| `guardia_tope_r` | +5,93 %, +6,53 %, +5,38 % | 51,2, 61,2, 66,2 | 2,3 %, 3,5 %, 2,1 % | 25,3 %, 17,8 %, 3,4 % |
| `prudente` | +5,43 %, +4,87 %, +7,39 % | 17,0, 17,1, 35,0 | | |
| `base_fuerte` | +4,43 %, +3,25 %, +2,54 % | 28,3, 21,7, 19,0 | 12,4 %, 9,9 %, 9,1 % | 65,7 %, 46,7 %, 30,9 % |

1. **La regla no cambia, el resultado se compone.** Sin guardia ni tope, el crecimiento por cada 2000 ticks es casi el mismo en los dos largos (7,1 y 7,3 % la base, 7,8 y 8,5 % `max_media`). Una ronda de 20 000 ticks son diez rondas de 2000 encadenadas, y una ventaja cercana a 1 punto de crecimiento por tramo pasa a ser 11 a 15 % de patrimonio: de +66 y +152 a +2 671 y +3 329.
2. **La frontera se cierra.** A 2000 ticks ser prudente compra percentil 5 con media. A 20 000 ticks no compra nada: `prudente` queda bajo la base en la media (-4 869 y -6 165) y también en el percentil 5 (11 452 contra 12 315 en el remuestreo, 9 220 contra 9 899 en las plausibles). Con diez veces más posiciones el resultado de la ronda depende de la tasa de crecimiento y no de la suerte de unas pocas entradas, y el que crece más queda arriba en casi toda la distribución. `max_media` y `kalman` superan a la base en media y en percentil 5 a la vez. **Corrección de la auditoría: esto no se sostiene sin el filtro.** Vale para las series interiores y para todas, que son las dos vistas que favorecen a quien aguanta una caída (una porque saca las series con caídas largas y la otra porque el rebote en el precio 1 las rescata). En la vista de parada el percentil 5 del patrimonio de `prudente` queda sobre el de la base (7 888 contra 7 056 con la semilla 0 y 7 650 contra 6 844 con la 2) y el de `max_media` por debajo (6 689 y 6 397). El intercambio entre media y percentil 5 del patrimonio sigue existiendo en rondas largas. En puntos de torneo la conclusión no cambia: `prudente` pierde 0,21 con H3a y 0,08 con H3b también en esa vista (sección 17.4).
3. **La guardia llega a pausar en una de cada cuatro series.** Tres posiciones seguidas cortadas por tiempo es un evento raro en 2000 ticks (2,5 % de las series) y frecuente en 20 000 (26,1 %). Cada pausa son 1000 ticks, así que los ticks vetados suben poco (de 0,8 a 1,5 %). Frente a `max_media`, que es la misma regla sin guardia, cuesta 1,3 puntos de crecimiento por tramo en los dos largos. Frente a la base queda en -230 ± 169 en el remuestreo, que no se distingue de cero, y -678 ± 212 en las plausibles.
4. **El tope sin rearmar es lo que más pierde.** Salta en el 3,5 % de las series a 2000 ticks y en el 17,8 % a 20 000, y como apaga hasta el final deja el 9,4 % de los ticks sin operar. Cuesta 2 108 y 4 158 frente a la base. Rearmarlo a los 2000 ticks (`guardia_tope_r`) baja los ticks vetados a 3,4 % y recupera algo más de un tercio de lo perdido (-1 316 y -2 649), pero sigue por debajo de la guardia sola. Lo que el tramo anterior dejó anotado se confirma: en rondas largas el tope hay que rearmarlo, y aun así no paga.
5. **Con todas las series el tope pierde mucho más** (18 620 contra 37 984 en el remuestreo), porque las series que bajan hasta precios chicos son a la vez las que disparan el tope y las que más ganan después con el rebote. Esa parte es un efecto de las series de prueba (sección 4) y no se debe leer como una pérdida esperada.
6. **Las órdenes por tramo suben con el patrimonio.** La base pasa de 34,6 a 42,1 órdenes por cada 2000 ticks. Las señales no dependen de la cuenta, así que lo que cambia es que con más patrimonio una entrada ya no cabe en una orden de 63 acciones. En la misma serie de práctica son 299 órdenes en los 10 bloques por separado y 388 en la serie completa. No se midió cuánto cuesta entrar en varios ticks: queda para el estudio de la ejecución que conoce su patrimonio.
7. **En la serie de práctica completa la base sigue siendo la mejor** (27 062 contra 25 973 de `max_media`). Es una sola serie y es la misma con que se eligieron los parámetros de la base. En los remuestreos de ese mismo material `max_media` gana 2 671 ± 149.
8. **El estrés a 20 000 ticks dice poco.** Con todas las series la guardia y el tope suben el percentil 5 (4 587 y 6 170 contra 2 697 de la base y 2 840 de `max_media`), pero las medias y medianas están dominadas por el rebote en el precio 1. Con las interiores casi no quedan series de estrés.

## 8. Estudio 2: las tres hipótesis de puntaje

Conjunto evidencia, campo mixto, G = 10 rivales, semilla reservada. `nada` es no operar y `byh` es comprar 63 siempre.

Rondas de 2000 ticks (10 000 series):

| Candidato | H1: media ± ee, p5 | H2: exceso medio, p5 | H2: W/B&H media, mediana | H3a: media ± ee | H3b: media ± ee | H3s | H3r |
|-----------|--------------------|----------------------|--------------------------|-----------------|-----------------|-----|-----|
| `base` | 10 840 ± 20, 8 811 | +1 061, -2 818 | 1,221, 1,084 | 1,452 ± 0,006 | 1,423 ± 0,005 | 1,675 | 1,694 |
| `max_media` | 10 943 ± 23, 8 683 | +1 164, -2 607 | 1,228, 1,097 | 1,494 ± 0,006 | 1,463 ± 0,005 | 1,724 | 1,729 |
| `kalman` | 10 956 ± 23, 8 646 | +1 176, -2 593 | 1,229, 1,097 | 1,487 ± 0,006 | 1,467 ± 0,005 | 1,716 | 1,721 |
| `activo` | 10 972 ± 24, 8 373 | +1 193, -2 428 | 1,217, 1,099 | 1,457 ± 0,006 | 1,458 ± 0,006 | 1,681 | 1,670 |
| `guardia` | 10 796 ± 21, 8 585 | +1 017, -2 730 | 1,207, 1,086 | 1,429 ± 0,006 | 1,400 ± 0,005 | 1,632 | 1,642 |
| `guardia_tope` | 10 709 ± 16, 8 385 | +929, -2 752 | 1,185, 1,084 | 1,420 ± 0,006 | 1,391 ± 0,005 | 1,611 | 1,620 |
| `prudente` | 10 641 ± 18, 9 194 | +862, -3 119 | 1,207, 1,065 | 1,345 ± 0,006 | 1,352 ± 0,005 | 1,537 | 1,577 |
| `nada` | 10 000 ± 0, 10 000 | +220, -3 681 | 1,129, 1,022 | 1,161 ± 0,006 | 1,146 ± 0,005 | 1,233 | 1,313 |
| `byh` | 9 774 ± 24, 5 876 | -6, -124 | 0,999, 1,000 | 1,090 ± 0,007 | 1,093 ± 0,007 | 1,107 | 0,969 |

Rondas de 20 000 ticks, series interiores (4004 series):

| Candidato | H1: media ± ee, p5 | H2: exceso medio, p5 | H2: W/B&H media, mediana | H3a: media ± ee | H3b: media ± ee | H3s | H3r |
|-----------|--------------------|----------------------|--------------------------|-----------------|-----------------|-----|-----|
| `base` | 23 085 ± 246, 10 495 | +13 047, -2 225 | 2,954, 2,061 | 1,732 ± 0,004 | 1,745 ± 0,003 | 1,803 | 1,812 |
| `max_media` | 26 086 ± 300, 11 231 | +16 048, -1 040 | 3,320, 2,270 | 1,857 ± 0,003 | 1,820 ± 0,003 | 1,935 | 1,934 |
| `kalman` | 26 442 ± 304, 11 154 | +16 404, -1 138 | 3,371, 2,291 | 1,841 ± 0,003 | 1,830 ± 0,003 | 1,926 | 1,925 |
| `activo` | 28 360 ± 396, 11 085 | +18 322, -228 | 3,518, 2,377 | 1,812 ± 0,004 | 1,837 ± 0,003 | 1,915 | 1,900 |
| `guardia` | 22 630 ± 234, 10 355 | +12 592, -2 373 | 2,873, 2,025 | 1,684 ± 0,005 | 1,728 ± 0,004 | 1,756 | 1,754 |
| `guardia_tope` | 19 948 ± 184, 8 137 | +9 910, -3 852 | 2,487, 1,837 | 1,579 ± 0,007 | 1,663 ± 0,005 | 1,619 | 1,612 |
| `prudente` | 17 565 ± 143, 9 750 | +7 527, -4 756 | 2,260, 1,626 | 1,431 ± 0,006 | 1,623 ± 0,004 | 1,452 | 1,475 |
| `nada` | 10 000 ± 0, 10 000 | -38, -8 183 | 1,243, 1,047 | 0,952 ± 0,006 | 1,247 ± 0,004 | 0,884 | 0,914 |
| `byh` | 10 040 ± 70, 3 731 | +2, -120 | 0,999, 1,000 | 0,932 ± 0,008 | 1,227 ± 0,006 | 0,879 | 0,765 |

La tabla con todas las series a 20 000 ticks está en `mediciones/tablas_s2.md`. El orden de los candidatos es el mismo, salvo que `activo` sube.

### 8.1 (a) ¿Cambia el orden de los candidatos según la hipótesis?

Arriba, casi no. Abajo, sí.

| Hipótesis | 2000 ticks: tres primeros, puesto de `base` | 20 000 ticks (interiores): tres primeros, puesto de `base` |
|-----------|---------------------------------------------|-------------------------------------------------------------|
| H1, media (y H2 en diferencia) | `activo`, `kalman`, `max_media`; 5.º | `activo`, `kalman`, `max_media`; 5.º |
| H1, percentil 5 | `prudente`, `prud_guardia`, `kalman_base`; 4.º | `max_media`, `kalman`, `activo`; 5.º |
| H2, razón W/B&H media | `kalman`, `max_media`, `kalman_base`; 4.º | `activo`, `kalman`, `max_media`; 5.º |
| H3a, puntos esperados | `max_media`, `kalman`, `activo`; 4.º | `max_media`, `kalman`, `activo`; 4.º |
| H3b, puntos esperados | `kalman`, `max_media`, `activo`; 5.º | `activo`, `kalman`, `max_media`; 5.º |
| H3s, suma del patrimonio | `max_media`, `kalman`, `activo`; 4.º | `max_media`, `kalman`, `activo`; 4.º |
| H3r, suma de razones | `max_media`, `kalman`, `base`; 3.º | `max_media`, `kalman`, `activo`; 4.º |
| H3a, p5 de tres rondas | `kalman`, `max_media`, `base`; 3.º | `max_media`, `kalman`, `activo`; 4.º |
| H3b, p5 de tres rondas | `max_media`, `base`, `kalman`; 2.º | `kalman`, `max_media`, `activo`; 4.º |

- **Los tres primeros son siempre `max_media`, `kalman` y `activo`**, salvo cuando se ordena por el percentil 5 del patrimonio de una ronda de 2000 ticks, que es el único criterio en que ganan los candidatos prudentes. El orden entre los tres cambia según la hipótesis, pero las diferencias entre `max_media` y `kalman` son de 0,004 a 0,016 puntos (sección 8.4).
- **`activo` es el que más depende de la hipótesis.** Lidera el patrimonio medio porque gana mucho en pocas series, y eso el torneo no lo paga: un patrimonio muy alto vale 2 puntos igual que uno apenas mejor que el segundo. Con H3a a 2000 ticks empata con la base (+0,005 ± 0,005).
- **Ningún candidato con guardia, tope o bandas anchas mejora a la base en puntos**, bajo ninguna lectura del torneo ni en ningún largo.
- **H2 como razón premia estar afuera cuando el precio cae.** No operar saca una razón media de 1,13 a 2000 ticks, sin hacer nada, porque comprar y mantener se hunde en las series que bajan. Por eso se informa también la mediana.
- **Comprar y mantener y no operar sacan entre 1,09 y 1,16 puntos a 2000 ticks y menos de 1 a 20 000** (lineal en patrimonio). Con rondas largas el torneo lo deciden las estrategias de reversión entre sí.

### 8.2 (b) Cuánto vale en puntos pasar de la regla base a cada candidato

Diferencia de puntos esperados y del percentil 5 de una competencia de tres rondas. Cada celda trae la semilla 0 y la semilla 2 (`mediciones/semillas_0_y_2.md`). Los puntos van de 0 a 2, que es lo que pesa la competencia en la nota.

Rondas de 2000 ticks. La regla base saca 1,465 y 1,452 puntos con H3a y 1,437 y 1,423 con H3b. Su percentil 5 de tres rondas es 0,835 y 0,828 con H3a y 0,872 y 0,867 con H3b.

| Candidato | H1: patrimonio | H3a: puntos esperados | H3b: puntos esperados | H3a: p5 de tres rondas | H3b: p5 de tres rondas |
|-----------|----------------|-----------------------|-----------------------|------------------------|------------------------|
| `max_media` | +103 ± 10 / +103 ± 11 | +0,038 ± 0,003 / +0,042 ± 0,004 | +0,036 ± 0,004 / +0,040 ± 0,004 | +0,047 ± 0,015 / +0,042 ± 0,016 | +0,039 ± 0,022 / +0,017 ± 0,021 |
| `kalman` | +123 ± 10 / +116 ± 12 | +0,033 ± 0,003 / +0,034 ± 0,004 | +0,040 ± 0,004 / +0,044 ± 0,004 | +0,052 ± 0,015 / +0,042 ± 0,016 | +0,028 ± 0,026 / +0,000 ± 0,025 |
| `kalman_base` | +13 ± 5 / +1 ± 5 | -0,007 ± 0,002 / -0,009 ± 0,002 | +0,002 ± 0,002 / +0,001 ± 0,002 | +0,005 ± 0,011 / -0,006 ± 0,010 | -0,006 ± 0,017 / -0,006 ± 0,019 |
| `activo` | +127 ± 18 / +132 ± 16 | +0,001 ± 0,005 / +0,005 ± 0,005 | +0,029 ± 0,005 / +0,036 ± 0,005 | +0,005 ± 0,019 / -0,002 ± 0,018 | -0,022 ± 0,028 / -0,033 ± 0,028 |
| `guardia` | -55 ± 16 / -44 ± 12 | -0,027 ± 0,004 / -0,023 ± 0,004 | -0,030 ± 0,005 / -0,023 ± 0,005 | -0,025 ± 0,016 / -0,031 ± 0,017 | -0,072 ± 0,026 / -0,067 ± 0,018 |
| `guardia_tope` | -130 ± 21 / -131 ± 17 | -0,035 ± 0,004 / -0,033 ± 0,004 | -0,037 ± 0,005 / -0,032 ± 0,005 | -0,033 ± 0,016 / -0,047 ± 0,017 | -0,072 ± 0,024 / -0,067 ± 0,022 |
| `prudente` | -232 ± 14 / -199 ± 14 | -0,114 ± 0,004 / -0,107 ± 0,004 | -0,076 ± 0,004 / -0,071 ± 0,005 | -0,108 ± 0,015 / -0,108 ± 0,015 | -0,106 ± 0,026 / -0,100 ± 0,023 |
| `nada` | -879 ± 23 / -840 ± 20 | -0,301 ± 0,006 / -0,291 ± 0,006 | -0,286 ± 0,005 / -0,276 ± 0,005 | -0,299 ± 0,018 / -0,283 ± 0,017 | -0,250 ± 0,022 / -0,250 ± 0,020 |
| `byh` | -1 106 ± 33 / -1 066 ± 30 | -0,383 ± 0,010 / -0,363 ± 0,010 | -0,350 ± 0,010 / -0,329 ± 0,009 | -0,475 ± 0,022 / -0,458 ± 0,022 | -0,472 ± 0,025 / -0,467 ± 0,020 |

Rondas de 20 000 ticks, series interiores. La regla base saca 1,730 y 1,732 puntos con H3a y 1,742 y 1,745 con H3b. Su percentil 5 de tres rondas es 1,314 y 1,322 con H3a y 1,389 con H3b en las dos semillas.

| Candidato | H1: patrimonio | H3a: puntos esperados | H3b: puntos esperados | H3a: p5 de tres rondas | H3b: p5 de tres rondas |
|-----------|----------------|-----------------------|-----------------------|------------------------|------------------------|
| `max_media` | +3 278 ± 124 / +3 001 ± 118 | +0,125 ± 0,004 / +0,125 ± 0,004 | +0,079 ± 0,003 / +0,075 ± 0,003 | +0,188 ± 0,019 / +0,192 ± 0,018 | +0,133 ± 0,021 / +0,117 ± 0,024 |
| `kalman` | +3 720 ± 136 / +3 357 ± 121 | +0,111 ± 0,004 / +0,109 ± 0,004 | +0,090 ± 0,003 / +0,085 ± 0,003 | +0,186 ± 0,017 / +0,189 ± 0,018 | +0,122 ± 0,026 / +0,122 ± 0,030 |
| `kalman_base` | +272 ± 46 / +188 ± 45 | -0,006 ± 0,002 / -0,009 ± 0,002 | +0,011 ± 0,002 / +0,006 ± 0,002 | -0,001 ± 0,012 / -0,002 ± 0,012 | +0,011 ± 0,023 / -0,011 ± 0,025 |
| `activo` | +5 407 ± 236 / +5 275 ± 246 | +0,080 ± 0,006 / +0,080 ± 0,006 | +0,097 ± 0,004 / +0,092 ± 0,004 | +0,109 ± 0,020 / +0,127 ± 0,022 | +0,122 ± 0,032 / +0,111 ± 0,032 |
| `guardia` | -315 ± 146 / -455 ± 136 | -0,044 ± 0,005 / -0,048 ± 0,005 | -0,015 ± 0,004 / -0,017 ± 0,004 | -0,056 ± 0,020 / -0,042 ± 0,021 | -0,056 ± 0,030 / -0,056 ± 0,025 |
| `guardia_tope` | -2 932 ± 220 / -3 137 ± 217 | -0,149 ± 0,007 / -0,153 ± 0,007 | -0,083 ± 0,005 / -0,082 ± 0,005 | -0,286 ± 0,025 / -0,283 ± 0,027 | -0,189 ± 0,027 / -0,189 ± 0,031 |
| `guardia_tope_r` | -1 878 ± 185 / -1 985 ± 174 | -0,097 ± 0,006 / -0,102 ± 0,006 | -0,037 ± 0,004 / -0,041 ± 0,004 | -0,172 ± 0,021 / -0,160 ± 0,021 | -0,111 ± 0,030 / -0,089 ± 0,028 |
| `prudente` | -5 393 ± 154 / -5 520 ± 157 | -0,294 ± 0,005 / -0,302 ± 0,005 | -0,112 ± 0,004 / -0,122 ± 0,004 | -0,378 ± 0,016 / -0,384 ± 0,018 | -0,200 ± 0,030 / -0,189 ± 0,029 |

- **Pasar de la base a `max_media` vale 0,04 puntos esperados con rondas de 2000 ticks y entre 0,08 y 0,13 con rondas de 20 000**, en las dos lecturas del torneo y con las dos semillas. El percentil 5 de la competencia no baja: sube 0,02 a 0,05 a 2000 ticks (dentro de dos errores en H3b) y 0,12 a 0,19 a 20 000. Corrección de la auditoría: la cifra de 20 000 ticks es la de las series interiores. Sin seleccionar series (vista de parada) vale 0,07 con H3a y 0,05 con H3b, y el percentil 5 de la competencia sube 0,09 a 0,10 y 0,07 (sección 17.4).
- **`kalman` vale lo mismo que `max_media`.**
- **La guardia cuesta 0,02 a 0,03 puntos esperados a 2000 ticks y 0,02 a 0,05 a 20 000, y además baja el percentil 5 de los puntos** (hasta -0,07 con H3b). En el torneo proteger el patrimonio no protege el puntaje: los rivales pierden en las mismas series.
- **`prudente` cuesta 0,07 a 0,11 puntos a 2000 ticks y 0,11 a 0,30 a 20 000**, con el percentil 5 de los puntos también abajo. Es el mejor en percentil 5 del patrimonio de una ronda corta y el peor de los principales en percentil 5 de los puntos.
- **Tener una regla de reversión ya vale mucho más que afinarla**: la base saca 0,29 puntos más que no operar y 0,36 más que comprar y mantener a 2000 ticks, y 0,78 y 0,80 más a 20 000.
- **Una ronda sola es casi una lotería.** El percentil 5 de los puntos de la base en una ronda de 2000 ticks es 0,16 con H3a y 0,30 con H3b. En la competencia de tres rondas sube a 0,83 y 0,87.

Las dos semillas dan lo mismo: de 225 cifras comparadas, 222 coinciden dentro de dos errores combinados y 223 tienen el mismo juicio. Las dos que cambian están en el borde de los dos errores (`kalman_base` en patrimonio a 2000 ticks, +13 ± 5 y +1 ± 5, y el percentil 5 de `guardia` con H3b a 20 000, -0,056 en las dos semillas con errores de 0,030 y 0,025).

### 8.3 (c) Sensibilidad al campo de rivales y a G

Diferencia de puntos esperados contra la regla base, conjunto evidencia, semilla reservada. El error de cada cifra es a lo más 0,010.

H3a, lineal en patrimonio, rondas de 2000 ticks:

| Candidato | ingenuo, G=5 | ingenuo, G=10 | ingenuo, G=15 | mixto, G=5 | mixto, G=10 | mixto, G=15 | fuerte, G=5 | fuerte, G=10 | fuerte, G=15 |
|---|---|---|---|---|---|---|---|---|---|
| `base` (puntos) | 1,652 | 1,671 | 1,685 | 1,480 | 1,452 | 1,437 | 1,309 | 1,349 | 1,367 |
| `max_media` | +0,022 | +0,020 | +0,019 | +0,039 | +0,042 | +0,042 | +0,086 | +0,066 | +0,058 |
| `kalman` | +0,023 | +0,020 | +0,019 | +0,031 | +0,034 | +0,034 | +0,070 | +0,053 | +0,047 |
| `activo` | +0,006 | +0,008 | +0,009 | +0,004 | +0,005 | +0,006 | +0,036 | +0,022 | +0,018 |
| `guardia` | -0,016 | -0,014 | -0,013 | -0,026 | -0,023 | -0,023 | -0,023 | -0,023 | -0,023 |
| `guardia_tope` | -0,024 | -0,021 | -0,020 | -0,035 | -0,033 | -0,033 | -0,033 | -0,033 | -0,033 |
| `prudente` | -0,054 | -0,049 | -0,048 | -0,107 | -0,107 | -0,106 | -0,165 | -0,141 | -0,127 |

H3a, lineal en patrimonio, rondas de 20 000 ticks (interiores):

| Candidato | ingenuo, G=5 | ingenuo, G=10 | ingenuo, G=15 | mixto, G=5 | mixto, G=10 | mixto, G=15 | fuerte, G=5 | fuerte, G=10 | fuerte, G=15 |
|---|---|---|---|---|---|---|---|---|---|
| `base` (puntos) | 1,875 | 1,815 | 1,762 | 1,813 | 1,732 | 1,684 | 1,509 | 1,550 | 1,556 |
| `max_media` | +0,049 | +0,071 | +0,089 | +0,087 | +0,125 | +0,144 | +0,225 | +0,199 | +0,190 |
| `kalman` | +0,049 | +0,071 | +0,090 | +0,075 | +0,109 | +0,127 | +0,202 | +0,179 | +0,173 |
| `activo` | +0,048 | +0,073 | +0,095 | +0,050 | +0,080 | +0,098 | +0,174 | +0,153 | +0,149 |
| `guardia` | -0,014 | -0,023 | -0,026 | -0,044 | -0,048 | -0,048 | -0,051 | -0,043 | -0,041 |
| `guardia_tope` | -0,088 | -0,113 | -0,123 | -0,136 | -0,153 | -0,158 | -0,172 | -0,159 | -0,153 |
| `prudente` | -0,139 | -0,194 | -0,228 | -0,244 | -0,302 | -0,324 | -0,399 | -0,365 | -0,348 |

H3b, lineal en el puesto. No depende de G (los tres valores de G dan lo mismo dentro de 0,005), así que se muestra G = 10:

| Candidato | 2000 ticks: ingenuo, mixto, fuerte | 20 000 ticks (interiores): ingenuo, mixto, fuerte |
|-----------|------------------------------------|----------------------------------------------------|
| `base` (puntos) | 1,542, 1,423, 1,158 | 1,844, 1,745, 1,256 |
| `max_media` | +0,027, +0,040, +0,085 | +0,046, +0,075, +0,224 |
| `kalman` | +0,032, +0,044, +0,086 | +0,051, +0,085, +0,257 |
| `activo` | +0,019, +0,036, +0,098 | +0,056, +0,092, +0,275 |
| `guardia` | -0,020, -0,023, -0,040 | -0,010, -0,017, -0,050 |
| `guardia_tope` | -0,028, -0,032, -0,048 | -0,074, -0,082, -0,123 |
| `prudente` | -0,068, -0,071, -0,124 | -0,111, -0,122, -0,287 |

- **El signo no cambia en ninguna de las 9 combinaciones** para ningún candidato principal. `activo` con H3a a 2000 ticks es positivo, pero con los campos ingenuo y mixto no siempre se distingue de cero. La conclusión cualitativa no depende del campo ni de G.
- **El tamaño sí depende del campo, por un factor de 3 a 5.** Con rivales ingenuos `max_media` vale 0,02 puntos a 2000 ticks. Con el campo fuerte vale 0,06 a 0,09. Mientras mejores sean los rivales, más importa la diferencia entre dos reglas de reversión parecidas, porque los puestos de arriba se deciden entre ellas.
- **El nivel de puntos de la base baja de 1,67 a 1,35 al pasar del campo ingenuo al fuerte** (H3a, G = 10, 2000 ticks), y de 1,54 a 1,16 con H3b. Es la sensibilidad más grande del estudio: lo que más mueve nuestro puntaje no es qué candidato elegimos sino cuántos grupos llegan a una reversión bien ajustada.
- **G mueve poco.** Con H3b nada. Con H3a a 2000 ticks cambia el nivel en unas centésimas y la diferencia entre candidatos en menos de 0,04. A 20 000 ticks la ventaja de `max_media` crece con G: de 0,09 a 0,14 con el campo mixto.
- **Por conjunto**, `max_media` y `kalman` ganan en el remuestreo, en las plausibles y en el estrés. `activo` pierde en el remuestreo (-0,053 ± 0,007 con H3a a 2000 ticks) y gana en las plausibles (+0,066 ± 0,005): su resultado depende de cuál de las dos evidencias se crea. La guardia pierde en remuestreo y plausibles y gana en el estrés (+0,034 ± 0,006 contra la base a 2000 ticks).

### 8.4 (d) Qué conviene bajo cada hipótesis, maximizando el esperado

Duelos contra `max_media` con el mismo criterio de corte (`mediciones/duelos_s2.txt`, campo mixto, G = 10, semilla reservada; la semilla 0 da lo mismo):

| Candidata contra `max_media` | H1 a 2000 ticks: evidencia, remuestreo, plausibles | H3a: 2000, 20 000 | H3b: 2000, 20 000 | Veredicto en las 9 combinaciones |
|------------------------------|-----------------------------------------------------|-------------------|-------------------|----------------------------------|
| `kalman` | +13 ± 6, +42 ± 5, -9 ± 7 | -0,008 ± 0,002, -0,016 ± 0,002 | +0,004 ± 0,002, +0,010 ± 0,002 | no pasa en ninguna |
| `activo` | +29 ± 13, -112 ± 13, +178 ± 15 | -0,037 ± 0,004, -0,045 ± 0,004 | -0,005 ± 0,004, +0,017 ± 0,003 | no pasa en ninguna |
| `guardia` | -147 ± 10, -106 ± 8, -202 ± 14 | -0,065 ± 0,003, -0,173 ± 0,003 | -0,063 ± 0,003, -0,092 ± 0,003 | no pasa en ninguna |

| Hipótesis | Qué conviene | Por qué |
|-----------|--------------|---------|
| H1, patrimonio | `max_media` | `activo` tiene 29 ± 13 más de media en la evidencia, pero pierde 112 ± 13 en el remuestreo y solo gana en el modelo. `kalman` tiene 13 ± 6 más y es el mismo resultado con cinco veces más instrucciones. `max_media` es el único que gana en las dos evidencias sin agregar nada. |
| H2, exceso sobre comprar y mantener | `max_media` | En diferencia es H1. En razón el orden es el mismo con la mediana. |
| H3a, lineal en patrimonio | `max_media` | Primero en puntos esperados en los dos largos y en las 9 combinaciones de campo y G contra la base. |
| H3b, lineal en el puesto | `max_media` o `kalman` | `kalman` saca 0,004 a 0,010 puntos más. Es una diferencia real y sin valor práctico. |
| H3s y H3r, sobre la competencia completa | `max_media` | Primero en las dos. |

Con el perfil de riesgo de Nicolás (maximizar el esperado) la respuesta es la misma bajo las tres hipótesis: **`max_media`**. La hipótesis de puntaje no cambia la elección. Lo que cambia es cuánto vale: 103 de patrimonio por ronda de 2000 ticks, o 0,04 puntos de torneo, o hasta 0,2 puntos si las rondas son largas y los rivales buenos.

La alternativa que el tramo anterior dejó abierta, `guardia`, queda descartada con este criterio. En puntos de torneo la guardia solo le gana a `max_media` en el conjunto de estrés a 2000 ticks, y por poco: +0,015 ± 0,005 con la semilla 2 y +0,004 ± 0,005 con la 0, contra -0,065 en la evidencia. Para que convenga en puntos esperados la serie oculta tendría que ser de estrés con una probabilidad mayor que 80 % (estimado con esas dos cifras). A 20 000 ticks pierde también en el estrés.

## 9. Veredicto del criterio de corte por candidato

Cada candidata contra la regla base, campo mixto, G = 10 (`mediciones/veredictos_s0.txt`, `veredictos_s2.txt`). Entre paréntesis, en cuántas de las 9 combinaciones de campo y G pasa.

| Candidata | Semilla 0: 2000, 20 000, global | Semilla 2: 2000, 20 000, global |
|-----------|----------------------------------|----------------------------------|
| `max_media` | PASA, PASA, **PASA** (9 de 9) | PASA, PASA, **PASA** (9 de 9) |
| `kalman` | PASA, PASA, **PASA** (9 de 9) | PASA, PASA, **PASA** (9 de 9) |
| `activo` | NO_PASA, PASA, **NO_PASA** (1 de 9) | NO_PASA, PASA, **NO_PASA** (4 de 9) |
| `kalman_base` | NO_PASA, NO_PASA, **NO_PASA** (0 de 9) | NO_PASA, NO_PASA, **NO_PASA** (0 de 9) |
| `guardia` | NO_PASA, NO_PASA, **NO_PASA** (0 de 9) | NO_PASA, NO_PASA, **NO_PASA** (0 de 9) |
| `guardia_tope`, `guardia_tope_r` | NO_PASA, NO_PASA, **NO_PASA** (0 de 9) | NO_PASA, NO_PASA, **NO_PASA** (0 de 9) |
| `prudente`, `prud_guardia` | NO_PASA, NO_PASA, **NO_PASA** (0 de 9) | NO_PASA, NO_PASA, **NO_PASA** (0 de 9) |
| `base_guardia`, `base_tope`, `base_tope_r`, `base_fuerte` | NO_PASA, NO_PASA, **NO_PASA** (0 de 9) | NO_PASA, NO_PASA, **NO_PASA** (0 de 9) |

Ningún veredicto global cambia entre las dos semillas.

Corrección de la auditoría: el `PASA` de `activo` a 20 000 ticks no se sostiene. Con la vista de parada su diferencia contra la base con H3a es -0,017 ± 0,005 (semilla 0) y -0,004 ± 0,005 (semilla 2): no mejora. Venía del filtro de interiores. Su veredicto global ya era `NO_PASA` y no cambia. Los de `max_media`, `kalman`, `guardia`, `guardia_tope`, `guardia_tope_r` y `prudente` tienen el mismo juicio en las tres vistas (`mediciones/auditoria_parada.txt`); los demás candidatos no se pasaron por la vista de parada.

Contra `max_media` como referencia no pasa ninguna de las tres candidatas probadas (`kalman`, `activo`, `guardia`), en ninguna de las 9 combinaciones con la semilla reservada. **La referencia que tienen que superar los estudios siguientes es `max_media`, no la regla base.**

Como dato para esos estudios, la estrategia de juguete `seguidor` del ejemplo (tres candidatos en papel y se copia al que va ganando) no pasa contra la base a 2000 ticks: -0,061 ± 0,004 con H3a y -0,069 ± 0,004 con H3b (`mediciones/ejemplo.txt`, semilla 0). No es un estudio del fondo de estrategias, solo la prueba de que la interfaz lo soporta.

## 10. Hallazgos

1. **La hipótesis de puntaje no cambia la elección.** Bajo patrimonio, exceso sobre comprar y mantener y torneo en sus dos lecturas, lo que conviene con el perfil de máximo esperado es `max_media`. `kalman` empata con él y cuesta cinco veces más instrucciones.
2. **`max_media` pasa el criterio de corte contra la base** en los dos largos, las dos lecturas, las 9 combinaciones de campo y G y las dos semillas: +0,04 puntos esperados a 2000 ticks y +0,08 a +0,13 a 20 000, sin bajar el percentil 5. La auditoría lo confirmó con otro evaluador, en cuatro campos más fuertes (+0,06 a +0,20 a 2000 ticks) y sin el filtro de interiores (+0,05 a +0,07 a 20 000).
3. **Lo que protege el patrimonio no protege el puntaje.** Guardia, tope y bandas anchas bajan los puntos esperados y también el percentil 5 de los puntos, porque en las series malas los rivales también pierden. Ninguna pasa.
4. **Al alargar la ronda la frontera se cierra.** A 20 000 ticks el candidato que crece más también tiene mejor percentil 5. La prudencia cuesta en los dos ejes. Corregido por la auditoría: en patrimonio esto depende de la vista. Sin el filtro de interiores y sin el rebote (vista de parada) `prudente` conserva el mejor percentil 5 del patrimonio y `max_media` queda bajo la base. En puntos de torneo sí se cumple en las tres vistas: la prudencia baja la media y el percentil 5 de los puntos.
5. **El tope de pérdida sin rearmar es lo peor que se puede llevar a una ronda larga.** Rearmado mejora y aun así no paga.
6. **La composición del campo rival mueve más nuestro puntaje que la elección del candidato**: 0,3 puntos entre el campo ingenuo y el fuerte, contra 0,04 entre la base y `max_media`. La auditoría fue más lejos: si ningún rival entrega algo que pierde en la serie de práctica, la base baja a 1,10 puntos, y si todos traen una reversión bien ajustada, a 0,87, bajo la mitad (sección 17.5). Los 1,45 puntos del campo mixto son un nivel optimista.
7. **Una ronda sola es casi una lotería** (percentil 5 de 0,16 a 0,30 puntos). Las tres rondas son las que dan piso.
8. **A 20 000 ticks las series de prueba chocan con los límites 1 y 255** en el 20 a 40 % de los casos y las medias se inflan. Las conclusiones se sacaron de las series interiores y se comprobó que con todas las series el signo es el mismo. La auditoría midió que las interiores también inflan, por selección, y agregó la vista de parada: con ella las ventajas a 20 000 ticks son cerca de un 40 % más chicas y `activo` deja de mejorar con H3a.
9. **Con más patrimonio una posición ya no cabe en una orden de 63.** Las órdenes por tramo suben entre 20 y 30 % en rondas largas. El costo de esa demora no se midió.

## 11. Qué habría que sacrificar para que quepa

No aplica: esta pieza no agrega hardware. `max_media` es la regla base con otra constante, así que usa las mismas celdas, los mismos BRAM y los mismos ciclos por tick. `kalman` costaría unas 140 instrucciones por tick contra 27 (estimación del tramo anterior, `docs/algoritmo.md`), y su hardware de apoyo no cabe en la FPGA (`docs/producto_2x2.md`).

## 12. Días de trabajo que faltan

Para llevar `max_media` a calidad de competencia (estimado):

| Tarea | Días |
|-------|------|
| Cambiar `UMBRAL_COMPRA` de -128 a -96 en `sw/trade.s` y `ENTRA` de 4 a 3 en `ref/trader.py`, y regenerar `sw/trade.hex` | 0,1 |
| Equivalencia: `make equiv`, gemelo a los tres períodos, testbench oficial con 4/4, core segmentado | 0,2 |
| Bitstream nuevo con su hash y simulación del bitstream | 0,1 |
| Documentación: `docs/algoritmo.md`, `docs/trade_s.md`, decisión, tabla del punto 3.1 | 0,3 |
| Total | 0,7 |

El hardware no cambia, pero el programa va dentro del bitstream: tiene que estar en el que se pruebe con la maestra real el 26/11.

Para dejar el arnés como parte de la entrega y no solo de este tramo (estimado):

| Tarea | Días |
|-------|------|
| Moverlo a `ref/` o `tools/`, con objetivos en el Makefile raíz y una validación corta en la integración continua | 0,5 |
| Documento de estudio en `docs/` y preguntas de defensa sobre las hipótesis de puntaje | 0,5 |
| Total | 1,0 |

## 13. Reglas del enunciado y preguntas para el ayudante

- "La decisión se debe calcular en el Espino Core": se cumple. Nada de esta carpeta corre en la placa. `max_media` es el mismo programa con otra constante.
- "No se puede usar información externa a la serie recibida por SPI ni almacenar series de precios en el diseño": se cumple. Las series de `build/series/` son datos de prueba en el computador y no entran al diseño. El umbral de entrada es un parámetro elegido con la serie de práctica, igual que el de la regla base.
- "Todo hardware agregado debe estar en el repositorio con su testbench": no se agrega hardware.
- "Deben usar el mismo programa para todas las series de tiempo": se cumple.

Preguntas, en orden de cuánto cambian los números de este estudio:

1. **Cómo se calcula el puntaje**: lineal en el patrimonio o en el puesto, por ronda o sobre las tres juntas, y qué papel juega comprar y mantener. No cambia la elección, sí el valor.
2. **Cuántos ticks dura cada ronda.** Con rondas largas la ventaja de `max_media` se triplica y el tope de pérdida pasa de caro a muy caro.
3. **Cuántos grupos compiten.** Mueve poco.
4. **Si las series ocultas salen del mismo generador que la de práctica.** Es el supuesto de todo el conjunto evidencia.

## 14. Riesgos y límites del estudio

- **Los rivales son un supuesto.** Nadie sabe qué van a programar los otros grupos. Por eso se barren tres campos, y el signo de las conclusiones no depende de cuál se elija. El tamaño sí.
- **Toda la evidencia sale de una sola serie de práctica**, remuestreada o a través del modelo ajustado a ella. Si la serie oculta es de otro tipo, vale el conjunto de estrés, donde `max_media` también supera a la base en puntos (+0,019 ± 0,004 con H3a a 2000 ticks) pero con peor percentil 5 de patrimonio (5 202 contra 5 637).
- **En los 10 bloques reales no se distinguen**: `max_media` queda 26 abajo de la base con un error de 238, y en la serie completa pierde 1 089. Son los datos con que se eligió la base.
- **A 20 000 ticks las series de prueba son menos confiables** (sección 4): el remuestreo reordena el mismo material, los límites 1 y 255 pesan y el filtro de interiores selecciona por trayectoria. Las cifras de 20 000 ticks se deben leer como orden de magnitud.
- **El criterio de corte usa dos errores estándar.** Con 10 000 series resuelve diferencias de 0,01 puntos. Una mejora real más chica que eso sale como `NO_PASA`. La salida trae además el veredicto literal por signo.
- **El error del percentil 5 es conservador** y el percentil 5 de H3b se mueve en escalones (con G = 10 los puntos de una ronda son múltiplos de 0,1). La auditoría lo midió con lotes disjuntos de series: el error informado es en promedio 2,8 veces el real. Para afirmar una mejora eso es prudente, pero para la condición "no empeora el percentil 5" es al revés: deja pasar caídas reales. Con el error bien medido `activo` pasa contra la base en 0 y 1 de las 9 combinaciones (semillas 0 y 2) en vez de 1 y 4, y ningún veredicto global cambia (sección 17.6).
- **Las tres rondas se suponen independientes** y con los mismos rivales.
- **La semilla 2 ya se usó.** Los estudios siguientes que comparen contra `max_media` con ella deben hacerlo una vez, o reservar otra.

## 15. Veredicto

| Pieza | Veredicto | Razón |
|-------|-----------|-------|
| Arnés de evaluación | Herramienta del tramo. No es hardware y no entra al diseño | Validado con cero diferencias contra el mercado, el motor, las referencias en Python y el binario de la placa. Es la base de los estudios 3 y 4 |
| `max_media` | **Competencia** | Pasa el criterio de corte contra la regla base en todas las combinaciones y con la semilla reservada. Cuesta una constante |
| `kalman` | Exhibición | Pasa contra la base pero no contra `max_media`, y cuesta cinco veces más instrucciones. Coincide con la decisión T30 |
| `activo` | Descartada | No pasa a 2000 ticks y pierde en el remuestreo |
| `guardia`, `guardia_tope`, `prudente` y sus variantes | Descartadas para la competencia, documentadas | Bajan los puntos esperados y el percentil 5 de los puntos |
| Tope de pérdida rearmado | Descartada | Mejora al tope sin rearmar en rondas largas y sigue sin pagar |

Elegir el candidato y cambiar `sw/trade.s` es decisión de Nicolás. Este tramo no tocó `ref/trader.py`, `sw/trade.s` ni ningún archivo versionado.

## 16. Lo que no se hizo o no se verificó

- No se midió el costo de entrar y salir en varias órdenes cuando el patrimonio crece.
- No hay tablas de H3 por familia de estrés: el torneo se informa para el conjunto de estrés completo.
- Los rivales de cruce, momentum y azar no tenían una segunda implementación, ni el percentil 5 de la competencia de tres rondas, ni las lecturas H3s y H3r. La auditoría lo cubrió (sección 17).
- No se probaron otros largos de ronda (500, 200 000) ni otras cajas y comisiones en los estudios, aunque el arnés los acepta.
- El tiempo de `make series` desde cero no se volvió a medir.
- La comparación con el gemelo digital usa las series de la semilla 0, los bloques y la serie completa. Las de la semilla 2 no se pasaron por el gemelo.
- La cifra de 140 instrucciones de `kalman` y los días de trabajo son estimaciones.

## 17. Auditoría

Revisión independiente del arnés, hecha el 14/11 después de cerrar los estudios 1 y 2 y sin reutilizar su evaluador. Todo está en `auditoria/` y se corre con `make auditoria` (5 min 57 s). Las salidas quedan en `mediciones/auditoria_*`.

### 17.1 Qué se revisó, cómo y qué dio

| Punto | Cómo | Comando (`make -C auditoria ...`) | Resultado |
|-------|------|-----------------------------------|-----------|
| Contabilidad | Cuatro contabilidades con los mismos flujos de órdenes: una escrita desde las reglas del enunciado, `ref/market.py`, el comando `mercado` del arnés y la tarea `ejecutar` copiada textual de `tb/tb_proyecto_4.sv` (líneas 69 a 85) a un banco mínimo y simulada con Icarus. 44 casos de borde (caja justa, un peso de más y de menos, precio 1 y 255, cantidad 0, acción 11, venta sin acciones, caja menor que la comisión, venta que no cubre la comisión, un solo tick, los 256 bytes) y 600 flujos al azar con cajas de 0 a 100 000 y comisiones de 0 a 50 | `contabilidad` | 354 635 ticks, 106 693 órdenes ejecutadas, 0 filas distintas entre las cuatro |
| Desfase, primer y último tick | El testbench oficial sin modificar, con el RTL y `sw/trade.hex`, corrido desde un directorio espejo. Su `decisiones.csv` contra el del arnés (`correr --perdidos 2`) y contra una regla base y un lazo escritos aparte | `desfase` | 4/4, patrimonio 9 617 y 52 órdenes. 2000 filas idénticas byte a byte en los dos casos. El primer tick lee `00`. La primera orden sale con el precio del tick 6 (143) y se ejecuta en el tick 7 a 144. La regla propia da 27 062 con 388 órdenes y 6 497 de comprar y mantener en la serie completa |
| Información del futuro | Programa aparte enlazado con el núcleo, con lazo y contabilidad propios. Para cada estrategia, alias y rival: el lazo propio contra `correr_serie`; todo el futuro cambiado después de un tick; solo el precio de ejecución cambiado; ronda repetida después de otra; y una prueba de martingala (series sin sesgo y sin comisión, donde nadie que no vea el futuro puede ganar en promedio). Control negativo: una estrategia tramposa que mira el precio de ejecución por una fuga puesta a propósito | `futuro` | 85 estrategias (10, 14 alias y 61 rivales), 167 280 comparaciones, 0 fallas. Martingala: la media más lejana de 10 000 queda a 2,36 errores. La tramposa falla 773 y 753 comparaciones y saca 58 203 de media (638 errores sobre 10 000) |
| Puntajes | Lectura de las fórmulas y evaluador independiente (`auditoria/indep.c`): no usa ningún fuente del núcleo, calcula el valor esperado exacto de H3a y H3b sumando sobre la distribución del peor y del mejor rival, y sortea por su cuenta la competencia de tres rondas | `estudio`, `informe` | 264 cifras de torneo: diferencia mediana 0,0009 puntos y máxima 0,008. 82 cifras de percentil 5, H3s y H3r, todas dentro de 2 errores del estudio (mediana 0,004) |
| Series | Cabeceras, tamaños, huellas, bloques contra `tb/practica.csv`, tres series de cada archivo regeneradas con `ref/series.py` (índices distintos de los de `make comprobar-series`), series repetidas y fechas de la semilla reservada | `series` | 77 archivos, 89 711 series, 225 regeneradas y 0 distintas. Ninguna serie repetida dentro de un archivo ni entre semillas. El primer resultado de la semilla 2 (14/11 02:34) es posterior a la última modificación de los fuentes que fijan candidatos, rivales, campos, umbrales y criterio (01:20). Es un indicio, no una prueba |
| Cifras | Cada cifra de las tablas de este documento contra la que obtiene el evaluador independiente | `informe` | 729 cifras: 383 exactas (iguales al redondeo), 264 de torneo y 82 de percentil 5. Coinciden todas, incluidas 27 062, 6 497, 11 069 y 9 720 |
| Rivales | Segunda implementación de las seis clases y de la forma de dimensionar la orden, comparada serie por serie con `detalle` en 14 archivos. Campos de rivales más fuertes | `rivales`, `estudio` | 1 033 149 corridas de reglas deterministas, 0 distintas. Azar (otro generador): la mayor diferencia entre medias es 1,43 errores. Campos: sección 17.5 |
| Interfaz | `ejemplo/minimo/mia.c` copiado a una carpeta fuera del repositorio, con el Makefile de la sección 3.3 | `interfaz` | Compila y corre. Con `entra=4` da 27 062 con 388 órdenes, sin parámetros da la fila de `max_media`, y la huella de `nucleo/` es la misma antes y después |

Además se corrió `make todo` del estudio como un solo comando, que no se había hecho: 7 min 11 s, sin errores, y 20 de las 21 salidas de `mediciones/` idénticas byte a byte a las guardadas. La que cambió es la primera corrección de la lista que sigue.

### 17.2 Fórmulas de puntaje

- H1 es el patrimonio final y H2 el exceso sobre comprar y mantener del testbench (compra `(caja - 5) / precio[0]` acciones al primer precio, sin el límite de 63). Reproducidos exactos.
- H3a es `2 (W - peor) / (mejor - peor)` entre nosotros y los G rivales. Si todos terminan igual vale 1. H3b es `2 (rivales bajo nosotros + medio punto por empate) / G`. Si todos empatan también vale 1. El enunciado no define ese caso y no afecta a ninguna comparación.
- El campo se sortea con reposición según los pesos, es el mismo para todos los candidatos (por eso las diferencias son pareadas) y en una competencia es el mismo en las tres rondas.
- El valor esperado de H3b no depende de G: es lineal en el número de rivales que quedan abajo. Por eso el estudio lo vio igual con G de 5, 10 y 15.
- Las diferencias pareadas y sus errores estándar están bien calculados: se reproducen exactos en todas las celdas de patrimonio. Hay que leerlos con dos avisos. El error mide la variación entre series de prueba, y los remuestreos salen todos de la misma serie de práctica, así que no dice nada de cuánto se parece la serie oculta. Y el error del percentil 5 es mucho mayor que el real (sección 17.6).

### 17.3 Correcciones hechas

1. **`mediciones/ejemplo.txt` no traía resultados.** El archivo guardado tenía solo las 17 líneas de los comandos, sin lo que imprimen. Las cifras que el documento cita de ahí (el `seguidor` con -0,061 ± 0,004 y -0,069 ± 0,004, y el ejemplo mínimo con 27 062) no tenían respaldo guardado. Se regeneró y las cifras son esas.
2. **Objetivo `ejemplo` del Makefile.** Ahora compila en silencio antes de probar, para que la salida guardada traiga los comandos y sus resultados y no la ruta local de la carpeta.
3. **Opción `--parada`** en `nucleo/main.c` (secciones 3.4 y 4). `main.c` no entra en la huella del núcleo, que sigue siendo `76399e005fd4ed8`: los resultados guardados en `build/resultados/` siguen valiendo y quien compiló contra el núcleo solo tiene que volver a correr `make`. Sin la opción, la salida de todos los comandos es la misma de antes: después del cambio se regeneraron las salidas de las dos semillas y son idénticas byte a byte. La opción se comprobó contra el evaluador independiente (`mediciones/auditoria_parada.txt`): patrimonio igual y puntos a menos de 0,002.
4. **Objetivo `make auditoria`** y carpeta `auditoria/`.
5. **Texto de este documento**: secciones 3.4, 4, 6, 7.2, 7.3, 8.2, 9, 10, 14 y 16, donde dice "auditoría".

No se tocaron `nucleo.h`, `nucleo.c`, `e_param.c`, `e_rivales.c`, `torneo.c`, `torneo.h`, las series ni los scripts de `pruebas/`. Ninguna cifra de las tablas de las secciones 7 a 9 cambió.

### 17.4 Rondas de 20 000 ticks: tres vistas

Diferencia de puntos esperados contra la referencia, H3a y H3b, conjunto evidencia, campo mixto, G = 10, con el arnés (`veredicto --parada`, `mediciones/auditoria_parada.txt`). Cada celda trae la semilla 0 y la semilla 2. El error de cada cifra es 0,001 a 0,007.

| Candidata contra referencia | Interiores (criterio del estudio) | Todas | Parada (sin selección ni rebote) |
|-----------------------------|-----------------------------------|-------|----------------------------------|
| `max_media` contra `base` | +0,125 y +0,125, +0,079 y +0,075 | +0,148 y +0,144, +0,084 y +0,081 | +0,074 y +0,074, +0,049 y +0,050 |
| `kalman` contra `base` | +0,111 y +0,109, +0,090 y +0,085 | +0,130 y +0,123, +0,091 y +0,086 | +0,063 y +0,064, +0,058 y +0,060 |
| `activo` contra `base` | +0,080 y +0,080, +0,097 y +0,092 | +0,145 y +0,138, +0,124 y +0,119 | -0,017 y -0,004, +0,024 y +0,035 |
| `guardia` contra `base` | -0,044 y -0,048, -0,015 y -0,017 | -0,047 y -0,052, -0,009 y -0,012 | -0,054 y -0,057, -0,021 y -0,021 |
| `guardia_tope` contra `base` | -0,149 y -0,153, -0,083 y -0,082 | -0,382 y -0,381, -0,160 y -0,164 | -0,115 y -0,116, -0,056 y -0,054 |
| `guardia_tope_r` contra `base` | -0,097 y -0,102, -0,037 y -0,041 | -0,316 y -0,323, -0,106 y -0,117 | -0,089 y -0,092, -0,032 y -0,034 |
| `prudente` contra `base` | -0,294 y -0,302, -0,112 y -0,122 | -0,331 y -0,331, -0,108 y -0,113 | -0,212 y -0,212, -0,077 y -0,082 |
| `kalman` contra `max_media` | -0,014 y -0,016, +0,011 y +0,010 | -0,019 y -0,021, +0,007 y +0,005 | -0,011 y -0,010, +0,009 y +0,010 |
| `activo` contra `max_media` | -0,044 y -0,045, +0,018 y +0,017 | -0,004 y -0,006, +0,039 y +0,038 | -0,091 y -0,077, -0,025 y -0,015 |
| `guardia` contra `max_media` | -0,169 y -0,173, -0,094 y -0,092 | -0,195 y -0,196, -0,093 y -0,093 | -0,128 y -0,130, -0,070 y -0,071 |

Patrimonio de una ronda (H1), misma tabla: diferencia de la media contra la base, y percentil 5 de la candidata y de la base. Semilla 2; la semilla 0 está en el archivo.

| Candidata | Interiores | Todas | Parada |
|-----------|------------|-------|--------|
| `max_media` | +3 001 ± 118; 11 231 y 10 495 | +9 162 ± 265; 11 247 y 10 576 | +1 757 ± 71; 6 397 y 6 844 |
| `kalman` | +3 357 ± 121; 11 154 y 10 495 | +9 182 ± 266; 11 251 y 10 576 | +2 035 ± 72; 6 530 y 6 844 |
| `activo` | +5 275 ± 246; 11 085 y 10 495 | +25 478 ± 729; 11 387 y 10 576 | +2 621 ± 141; 5 420 y 6 844 |
| `guardia` | -455 ± 136; 10 355 y 10 495 | -1 046 ± 297; 10 171 y 10 576 | -544 ± 81; 6 659 y 6 844 |
| `guardia_tope` | -3 137 ± 217; 8 137 y 10 495 | -24 581 ± 702; 7 080 y 10 576 | -2 392 ± 131; 7 119 y 6 844 |
| `prudente` | -5 520 ± 157; 9 750 y 10 495 | -14 531 ± 386; 9 537 y 10 576 | -3 404 ± 96; 7 650 y 6 844 |

Cuánto selecciona el filtro de interiores (`mediciones/auditoria_tablas.md`, sección 5): los primeros 2000 ticks de las series de 20 000, según si la serie completa queda dentro de 21 a 249.

| Semilla | Series | `base` en esos 2000 ticks: media, p5 | Comprar y mantener | `max_media` menos `base` |
|---------|--------|--------------------------------------|--------------------|--------------------------|
| 0 | interiores, 4021 | 10 735 ± 21, 9 127 | 10 059 ± 32 | +102 ± 11 |
| 0 | excluidas, 3979 | 11 031 ± 50, 8 541 | 9 529 ± 44 | +103 ± 18 |
| 2 | interiores, 4004 | 10 758 ± 24, 9 188 | 10 049 ± 31 | +129 ± 11 |
| 2 | excluidas, 3996 | 10 915 ± 36, 8 511 | 9 544 ± 43 | +87 ± 20 |

Qué se saca de aquí:

- **Las series de 20 000 ticks sí quedan pegadas a los límites de forma poco realista.** En la evidencia el 25,9 % toca el precio 1 y el 21,8 % pasa más de un décimo de la ronda con el precio bajo 21 o sobre 249; en el estrés, el 39,0 %. La serie de práctica nunca baja de 72. Con todas las series no se puede concluir nada sobre magnitudes.
- **El filtro de interiores arregla eso y agrega otro sesgo.** Deja las series en que el precio no se alejó nunca: comprar y mantener rinde 5 % más y el percentil 5 de la regla base queda 590 a 680 más arriba ya en el primer décimo de la ronda.
- **Las ventajas a 20 000 ticks son cerca de un 40 % más chicas sin esos dos efectos.** `max_media` vale +0,074 con H3a y +0,050 con H3b, no +0,125 y +0,075. El signo se mantiene con más de 15 errores. Parte de la baja es que las rondas cortadas duran 15 270 ticks de media.
- **`activo` no mejora con H3a a 20 000 ticks.** Su `PASA` a ese largo venía del filtro.
- **La frontera entre media y percentil 5 del patrimonio no se cierra.** Con la vista de parada `prudente` y el tope de pérdida tienen mejor percentil 5 de patrimonio que la base, y `max_media`, `kalman` y `activo` peor. Lo que sí es igual en las tres vistas es el resultado en puntos de torneo, que es el del criterio de corte.
- **Para los estudios que siguen:** un resultado a 20 000 ticks vale si la fila de parada tiene el mismo signo que la de interiores. El veredicto a 2000 ticks no tiene este problema: menos del 0,4 % de las series de la evidencia toca el precio 1.

### 17.5 Campos de rivales más fuertes

El campo mixto sortea la clase del rival con la misma probabilidad para las seis. Dos de esas clases siguen la tendencia y otra opera al azar, y en la serie de práctica todas pierden: los tres mejores cruces terminan en 3 438, 3 413 y 1 841 de 10 000, los tres mejores momentum en 4 870, 2 431 y 1 922 (`mediciones/rivales.txt`). Un grupo que prueba su programa con la serie de práctica no entrega eso. Así que la mitad del campo mixto son rivales que un grupo real descartaría, y eso sube nuestro nivel de puntos. Los rivales en sí hacen lo que dicen y sus parámetros son los que usaría un alumno del ramo.

Se agregaron cuatro campos (`auditoria/indep.c`, G = 10):

- **racional**: cualquier rival que no pierda en la serie de práctica completa (22 reversiones de distinta calidad y no operar), con la misma probabilidad.
- **fijos2** y **fijos3**: el campo mixto, pero dos o tres de los diez rivales son siempre reversiones bien hechas (la regla base, `max_media` y, con tres, la suma móvil de 64).
- **reversores**: los diez rivales traen una de esas tres reversiones.

Rondas de 2000 ticks, conjunto evidencia, semilla 2 (la semilla 0 y las rondas de 20 000 ticks están en `mediciones/auditoria_tablas.md`). Primera columna: puntos esperados de la regla base, H3a y H3b. Las demás: diferencia contra la base, H3a y H3b, con su error.

| Campo | `base` | `max_media` | `kalman` | `activo` | `guardia` | `prudente` |
|-------|--------|-------------|----------|----------|-----------|------------|
| ingenuo | 1,671, 1,542 | +0,019 ± 0,002, +0,028 ± 0,003 | +0,020 ± 0,002, +0,033 ± 0,003 | +0,007 ± 0,003, +0,019 ± 0,004 | -0,014 ± 0,002, -0,019 ± 0,004 | -0,050 ± 0,002, -0,069 ± 0,004 |
| mixto | 1,453, 1,425 | +0,042 ± 0,003, +0,039 ± 0,004 | +0,034 ± 0,003, +0,042 ± 0,004 | +0,006 ± 0,005, +0,035 ± 0,005 | -0,023 ± 0,004, -0,026 ± 0,005 | -0,107 ± 0,004, -0,071 ± 0,004 |
| fuerte | 1,349, 1,158 | +0,066 ± 0,005, +0,084 ± 0,006 | +0,053 ± 0,005, +0,085 ± 0,006 | +0,023 ± 0,006, +0,098 ± 0,008 | -0,023 ± 0,006, -0,040 ± 0,007 | -0,141 ± 0,005, -0,124 ± 0,006 |
| fijos2 | 1,416, 1,327 | +0,057 ± 0,004, +0,057 ± 0,005 | +0,041 ± 0,004, +0,060 ± 0,005 | +0,001 ± 0,006, +0,057 ± 0,006 | -0,025 ± 0,005, -0,039 ± 0,006 | -0,134 ± 0,005, -0,096 ± 0,005 |
| fijos3 | 1,371, 1,274 | +0,057 ± 0,004, +0,064 ± 0,005 | +0,046 ± 0,004, +0,066 ± 0,005 | +0,018 ± 0,006, +0,069 ± 0,007 | -0,022 ± 0,005, -0,035 ± 0,006 | -0,127 ± 0,005, -0,101 ± 0,005 |
| racional | 1,100, 1,157 | +0,100 ± 0,006, +0,082 ± 0,006 | +0,100 ± 0,006, +0,092 ± 0,006 | +0,099 ± 0,009, +0,074 ± 0,008 | -0,006 ± 0,007, -0,029 ± 0,007 | -0,188 ± 0,007, -0,205 ± 0,007 |
| reversores | 0,872, 0,922 | +0,200 ± 0,013, +0,123 ± 0,009 | +0,186 ± 0,012, +0,123 ± 0,009 | +0,192 ± 0,013, +0,150 ± 0,010 | +0,030 ± 0,012, -0,057 ± 0,009 | -0,144 ± 0,009, -0,171 ± 0,008 |

Los tres primeros campos son los del estudio, rehechos con el valor esperado exacto: coinciden con la sección 8.3.

- **El campo mixto está sesgado a nuestro favor en el nivel y en contra en el tamaño de las diferencias.** Con rivales que no pierden en la práctica la base baja de 1,45 a 1,10 puntos, y a 0,87 si todos traen una reversión ajustada: bajo la mitad de los 2 puntos. Los rivales que pierden mucho dejan el peor del campo muy abajo y comprimen las diferencias entre las reglas buenas.
- **La conclusión no cambia con ningún campo y se refuerza con los más fuertes.** `max_media` supera a la base en los siete, con las dos lecturas y las dos semillas: de +0,02 a +0,20 puntos. El percentil 5 de la competencia también sube en los siete. Pasa el criterio de corte en los cuatro campos nuevos.
- **`guardia` y `prudente` siguen sin pasar en ninguno.** La guardia solo sale positiva con H3a cuando todos los rivales son reversores (+0,030 ± 0,012 y +0,015 ± 0,012), y ahí mismo pierde 0,17 contra `max_media`.
- **Con rivales fuertes `max_media`, `kalman` y `activo` no se distinguen entre sí.** Contra `max_media` y con la semilla 2, en los cuatro campos nuevos `kalman` queda entre -0,016 y +0,001 con H3a y entre +0,000 y +0,010 con H3b, y `activo` entre -0,056 y -0,001 y entre -0,007 y +0,027. Ninguno pasa el criterio contra `max_media` en los campos nuevos. `max_media` sigue siendo la referencia que hay que superar y es la más barata.
- **Tener una reversión sigue valiendo más que afinarla**, pero la distancia se acorta: la base saca 0,29 puntos más que no operar en el campo mixto y 0,51 en el racional, y afinarla vale 0,04 y 0,10.

### 17.6 Error del percentil 5

El estudio estima el error del percentil 5 de la competencia de tres rondas remuestreando dentro de cada reparto en tríos, y avisa que es conservador. La auditoría lo estimó con 10 lotes disjuntos de series: el error del estudio es en promedio 2,8 veces mayor (`mediciones/auditoria_tablas.md`, sección 7). Por ejemplo, para `max_media` contra la base a 2000 ticks el estudio da +0,042 ± 0,016 y +0,017 ± 0,021 (semilla 2) y la auditoría +0,049 ± 0,008 y +0,033 ± 0,008.

Para afirmar que el percentil 5 mejora, eso es prudente. Para la segunda condición del criterio de corte, "no empeora", funciona al revés: una caída real de hasta 0,04 o 0,05 puntos se juzga "igual". Con el error bien medido:

| Candidata | Combinaciones de campo y G en que pasa a 2000 ticks, semillas 0 y 2: estudio | Auditoría |
|-----------|-------------------------------------------------------------------------------|-----------|
| `max_media` contra `base` | 9 y 9 | 9 y 9 |
| `kalman` contra `base` | 9 y 9 | 9 y 9 |
| `activo` contra `base` | 1 y 4 (veredicto global) | 0 y 1 |
| `guardia` y `prudente` contra `base` | 0 y 0 | 0 y 0 |
| `kalman` contra `max_media` | 0 y 0 (veredicto global) | 3 y 0 a 2000 ticks, 0 y 0 a 20 000 |
| `activo` y `guardia` contra `max_media` | 0 y 0 | 0 y 0 |

Ningún veredicto global cambia. No se cambió el cálculo del arnés para no mover las cifras ya publicadas. Quien use `veredicto` en los estudios que siguen debe saber que la columna del percentil 5 solo detecta caídas grandes, y mirar también el veredicto literal por signo que imprime el comando.

### 17.7 Qué cambia para la decisión

- **No cambia la elección.** `max_media` pasa el criterio contra la base con otro evaluador, con campos más fuertes y sin el filtro de interiores. Ninguna candidata lo supera.
- **Cambia cuánto vale.** A 2000 ticks, 0,04 puntos con el campo mixto y hasta 0,20 si todos los rivales son buenos. A 20 000 ticks, 0,05 a 0,07 y no 0,08 a 0,13.
- **Cambia el nivel esperado.** Los 1,45 puntos de la base suponen que la mitad de los rivales entrega algo que pierde en la práctica. Con rivales razonables el nivel está entre 0,9 y 1,1: cerca de la mitad de la tabla.
- **Cambia una afirmación sobre el riesgo.** En rondas largas las protecciones siguen cuidando el percentil 5 del patrimonio. Lo que no cuidan es el puntaje.

### 17.8 Lo que la auditoría no cubrió

- `kalman`, `kalman_base`, la guardia y el tope de pérdida no se reescribieron. Su patrimonio por serie se tomó del arnés (van como "externos" en `mediciones/auditoria_cifras.txt`) y lo que se rehízo con ellos es la estadística y el torneo. Su única referencia sigue siendo `make validar` (contra `ref/candidatos.py` y `ref/motor/motor.c`), que se volvió a correr y pasa.
- Los contadores de la guardia y del tope (porcentaje de series con pausa, ticks vetados) no se comprobaron.
- La comparación con el gemelo digital (`make gemelo`) se volvió a correr y pasa, pero no se auditó el gemelo.
- El desfase contra el testbench oficial se comprobó con 2000 ticks a 0,1 ms, que es lo que el testbench trae sin modificar.
- La semilla 2 se volvió a usar aquí para los mismos candidatos y para los campos nuevos. No se eligió nada con ella, pero ya no es una semilla sin mirar para los candidatos del núcleo.
- La vista de parada no se calculó para `kalman_base`, `base_guardia`, `base_tope`, `base_tope_r`, `base_fuerte` ni `prud_guardia`.
- No se probaron otras cajas ni comisiones en los estudios. La contabilidad sí se comprobó con cajas de 0 a 100 000 y comisiones de 0 a 50.
- Una estrategia escrita con mala intención podría leer la memoria del arnés: C no lo impide. La interfaz no le entrega nada del futuro, y eso es lo que se probó.
