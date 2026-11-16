/* main.c: comandos del arnés de evaluación del estudio de retorno.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Cualquier binario que se compile con los fuentes del núcleo tiene estos
 * comandos, y además conoce las estrategias que se le hayan agregado:
 *
 *   listar                       estrategias, alias y rivales
 *   correr    --estrategia S --serie CSV [--nticks N] [--perdidos K] [-o decisiones.csv]
 *   mercado                      contabilidad de un flujo de órdenes (entrada estándar)
 *   detalle   --estrategia S --lote ARCHIVO.bin        una línea por serie
 *   resumen   --estrategia S[;S...] --conjunto C --largo N --semilla K
 *   lote-texto ARCHIVO.bin       las series como texto, para el gemelo digital
 *   causal    [--estrategia S]   comprueba que ninguna estrategia mira el futuro
 *   rivales                      la lista de rivales y su peso en cada campo
 *   bordes    --largo N --semilla K     cuánto tocan las series los límites 1 y 255
 *   frontera  --largo N --semilla K [--candidatos a,b,c]
 *   hipotesis --largo N --semilla K [--candidatos a,b,c] [--G 10] [--campo mixto] [--tsv ARCHIVO]
 *   veredicto --candidata S --referencia S [--semilla K] [--largo N] [--G 10] [--campo mixto]
 *   precalcular --largo N --semilla K   deja en build/resultados los rivales y candidatos
 *
 * Opciones comunes: --caja N, --comision N (por defecto 10000 y 5), e
 * --interior en resumen, frontera, hipotesis y veredicto: usa solo las series
 * cuyo precio se queda siempre entre 21 y 249 (ver README.md, límites 1 y
 * 255). El veredicto usa las interiores a 20 000 ticks aunque no se pida.
 * --parada (agregada en la auditoría, ver README.md): usa todas las series,
 * pero cada una solo hasta el primer tick en que el precio sale de 21 a 249.
 * En veredicto agrega filas informativas a 20 000 ticks y no cambia el
 * veredicto. Sin --parada la salida de todos los comandos es la de antes.
 * Un candidato se nombra por su alias corto ("max_media" es "cand:max_media")
 * o por su especificación completa ("param:E=96,X=0", "mia:a=1").
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "nucleo.h"
#include "torneo.h"

#define MAX_C 48

static Reglas g_reglas = {CAJA0_DEF, COMISION_DEF};

static const char *POR_DEFECTO = "base,max_media,guardia,guardia_tope,prudente,kalman,kalman_base,activo,base_guardia,"
                                 "base_tope,base_fuerte,prud_guardia,guardia_tope_r,base_tope_r";

/* ---- Argumentos ------------------------------------------------------------------------------------ */

static int g_argc;
static char **g_argv;

static const char *opcion(const char *nombre, const char *defecto) {
  for (int i = 2; i + 1 < g_argc; i++)
    if (!strcmp(g_argv[i], nombre)) return g_argv[i + 1];
  return defecto;
}

static int opcion_int(const char *nombre, int defecto) {
  const char *v = opcion(nombre, NULL);
  return v ? atoi(v) : defecto;
}

static void morir(const char *a, const char *b) {
  fprintf(stderr, "%s%s%s\n", a, b ? ": " : "", b ? b : "");
  exit(2);
}

/* ---- Listas de candidatos ---------------------------------------------------------------------------- */

typedef struct { int nc; char nombre[MAX_C][96]; char spec[MAX_C][512]; } Lista;

static void resolver(const char *nombre, char *spec, size_t tam) {
  char alias[160];
  snprintf(alias, sizeof alias, "cand:%s", nombre);
  for (int k = 0; k < nucleo_nalias(); k++)
    if (!strcmp(nucleo_alias_nombre(k), alias)) { snprintf(spec, tam, "%s", alias); return; }
  snprintf(spec, tam, "%s", nombre);
}

/* Nombres separados por ';' (o por ',' si ninguno lleva parámetros). */
static void lista_leer(Lista *l, const char *texto) {
  char copia[4096];
  const char *sep = strchr(texto, ';') || strchr(texto, '=') ? ";" : ",";
  snprintf(copia, sizeof copia, "%s", texto);
  l->nc = 0;
  for (char *tok = strtok(copia, sep); tok; tok = strtok(NULL, sep)) {
    if (l->nc == MAX_C) morir("demasiados candidatos", NULL);
    snprintf(l->nombre[l->nc], sizeof l->nombre[0], "%s", tok);
    resolver(tok, l->spec[l->nc], sizeof l->spec[0]);
    char error[256];
    Instancia *i = instancia_crear(l->spec[l->nc], error, sizeof error);
    if (!i) morir(error, NULL);
    instancia_destruir(i);
    l->nc++;
  }
}

static int lista_buscar(const Lista *l, const char *nombre) {
  for (int c = 0; c < l->nc; c++)
    if (!strcmp(l->nombre[c], nombre)) return c;
  return -1;
}

static const char *nombre_semilla(int s) {
  return s == 0 ? "exploracion" : s == 1 ? "reservada del tramo anterior" : s == 2 ? "reservada de este tramo" : "otra";
}

/* ---- Resultados de una lista sobre un conjunto ------------------------------------------------------ */

/* Con --interior solo se usan las series cuyo precio se queda siempre entre
 * 21 y 249: las que no tocan la zona de los límites 1 y 255. */
static int g_interior;
#define INTERIOR_MIN 21
#define INTERIOR_MAX 249

static int es_interior(const Lote *l, int i) {
  const unsigned char *p = l->datos + (size_t)i * l->n;
  for (int j = 0; j < l->n; j++)
    if (p[j] < INTERIOR_MIN || p[j] > INTERIOR_MAX) return 0;
  return 1;
}

/* Con --parada cada serie se corre solo hasta el primer tick en que el precio
 * sale de INTERIOR_MIN..INTERIOR_MAX, incluido ese tick, con un mínimo de
 * PARADA_MIN ticks. Es una regla de parada que no mira el futuro: a diferencia
 * de --interior, no elige las series por lo que pasa después, y a diferencia
 * de usar todas, no deja que el rebote en los límites 1 y 255 infle el
 * resultado. No usa build/resultados: evalúa siempre. */
static int g_parada;
static const double *g_parada_peso;      /* si no es NULL, los rivales con peso 0 no se evalúan */
#define PARADA_MIN 200

static int hilos(void);

static int largo_parada(const Lote *l, int i) {
  const unsigned char *p = l->datos + (size_t)i * l->n;
  int j = 0;
  while (j < l->n && p[j] >= INTERIOR_MIN && p[j] <= INTERIOR_MAX) j++;
  j = j < l->n ? j + 1 : l->n;                     /* el tick en que se ve el precio afuera también se juega */
  if (j < PARADA_MIN) j = PARADA_MIN < l->n ? PARADA_MIN : l->n;
  return j;
}

static Resultado *resultados_parada(const char *spec, const Lote *l) {
  char error[256] = "", resuelta[512];
  Instancia *prueba = instancia_crear(spec, error, sizeof error);
  if (!prueba) { fprintf(stderr, "%s\n", error); return NULL; }
  strcpy(resuelta, instancia_spec(prueba));
  instancia_destruir(prueba);
  Resultado *res = malloc(sizeof(Resultado) * (size_t)l->ns);
#pragma omp parallel num_threads(hilos())
  {
    Instancia *inst = instancia_crear(resuelta, NULL, 0);
#pragma omp for schedule(dynamic, 8)
    for (int i = 0; i < l->ns; i++) {
      int k = 0;
      while (k + 1 < l->partes && i >= l->inicio[k + 1]) k++;
      res[i] = correr_serie(inst, l->datos + (size_t)i * l->n, largo_parada(l, i), &g_reglas,
                            semilla_serie(resuelta, i - l->inicio[k]), 0, NULL);
    }
    instancia_destruir(inst);
  }
  return res;
}

typedef struct {
  Lote *lote;            /* el conjunto completo */
  int ns;                /* series que se usan (todas, o las interiores) */
  int *sel;              /* sel[j]: posición en el lote de la serie j que se usa */
  int partes, inicio[MAX_PARTES + 1];   /* límites de cada familia entre las series que se usan */
  int nc;
  Resultado **res;       /* res[c][j] */
  double **w;            /* w[c][j] */
  double *byh;
} Tabla;

static Tabla tabla_cargar(const Lista *l, const char *conjunto, int largo, int semilla) {
  Tabla t;
  t.lote = conjunto_leer(conjunto, largo, semilla);
  if (!t.lote) morir("no se pudo leer el conjunto", conjunto);
  t.sel = malloc(sizeof(int) * (size_t)t.lote->ns);
  t.ns = 0;
  t.partes = t.lote->partes;
  for (int k = 0; k < t.partes; k++) {
    t.inicio[k] = t.ns;
    for (int i = t.lote->inicio[k]; i < t.lote->inicio[k + 1]; i++)
      if (!g_interior || es_interior(t.lote, i)) t.sel[t.ns++] = i;
  }
  t.inicio[t.partes] = t.ns;
  if (t.ns < 1) morir("no queda ninguna serie en el conjunto", conjunto);
  t.nc = l->nc;
  t.res = malloc(sizeof(Resultado *) * (size_t)l->nc);
  t.w = malloc(sizeof(double *) * (size_t)l->nc);
  t.byh = malloc(sizeof(double) * (size_t)t.ns);
  for (int c = 0; c < l->nc; c++) {
    Resultado *todos = g_parada ? resultados_parada(l->spec[c], t.lote)
                                : resultados(l->spec[c], t.lote, conjunto, largo, semilla, &g_reglas);
    if (!todos) morir("no se pudo evaluar", l->spec[c]);
    t.res[c] = malloc(sizeof(Resultado) * (size_t)t.ns);
    t.w[c] = malloc(sizeof(double) * (size_t)t.ns);
    for (int j = 0; j < t.ns; j++) {
      t.res[c][j] = todos[t.sel[j]];
      t.w[c][j] = t.res[c][j].w;
      if (t.res[c][j].desborde) fprintf(stderr, "AVISO: %s desborda 32 bits en la serie %d de %s\n", l->nombre[c], t.sel[j], conjunto);
    }
    free(todos);
  }
  for (int j = 0; j < t.ns; j++) t.byh[j] = t.res[0][j].byh;
  return t;
}

static void tabla_liberar(Tabla *t) {
  for (int c = 0; c < t->nc; c++) { free(t->res[c]); free(t->w[c]); }
  free(t->res); free(t->w); free(t->byh); free(t->sel);
  lote_liberar(t->lote);
}

static const char *nota_interior(void) {
  if (g_parada) return " Cada serie solo hasta el primer precio fuera de 21 a 249 (parada).";
  return g_interior ? " Solo series interiores (precio siempre entre 21 y 249)." : "";
}

typedef struct { Resumen r; double dif, ee, sobre_byh, act, pausa, tope, veto, ordenes; } Fila;

/* Estadísticos del candidato c sobre las series i0..i1-1, con la diferencia pareada contra `ref`. */
static Fila fila(const Tabla *t, int c, int ref, int i0, int i1) {
  Fila f;
  int n = i1 - i0;
  f.r = resumir(t->w[c] + i0, n);
  pareada(t->w[c] + i0, t->w[ref] + i0, n, &f.dif, &f.ee);
  f.sobre_byh = f.act = f.pausa = f.tope = f.veto = f.ordenes = 0;
  for (int i = i0; i < i1; i++) {
    const Resultado *x = &t->res[c][i];
    f.sobre_byh += x->w > x->byh;
    f.act += x->aux[0] > 0 || x->aux[2] > 0;
    f.pausa += x->aux[3] > 0;
    f.tope += x->aux[2] > 0;
    f.veto += x->aux[0];
    f.ordenes += x->ordenes;
  }
  f.sobre_byh /= n; f.act /= n; f.pausa /= n; f.tope /= n; f.ordenes /= n;
  f.veto /= (double)n * t->lote->n;
  return f;
}

static double media_geometrica(const double *w, int n) {
  double slog = 0;
  for (int i = 0; i < n; i++) slog += log(w[i] < 1 ? 1 : w[i]);
  return exp(slog / n);
}

/* ---- listar, rivales ------------------------------------------------------------------------------------ */

static int cmd_listar(void) {
  printf("Estrategias (se piden como nombre o nombre:parametro=valor,...):\n");
  for (int k = 0; k < nucleo_nestrategias(); k++)
    printf("  %-12s %s\n", nucleo_estrategia(k)->nombre, nucleo_estrategia(k)->descripcion);
  printf("\nAlias:\n");
  for (int k = 0; k < nucleo_nalias(); k++)
    printf("  %-22s %-62s %s\n", nucleo_alias_nombre(k), nucleo_alias_spec(k), nucleo_alias_desc(k));
  printf("\nRivales del torneo: %d (ver el comando rivales)\n", nucleo_nrivales());
  return 0;
}

static int cmd_rivales(void) {
  Rivales rv;
  if (rivales_preparar(&rv, &g_reglas)) return 1;
  printf("Rivales del torneo simulado: %d. Patrimonio en la serie de practica completa (20 000 ticks)\n", rv.nr);
  printf("y probabilidad de que un grupo rival sea ese, en cada composicion del campo.\n\n");
  printf("%-20s %-40s %9s | %8s %8s %8s\n", "clase", "rival", "practica", CAMPOS[0], CAMPOS[1], CAMPOS[2]);
  for (int k = 0; k < rv.nr; k++)
    printf("%-20s %-40s %9.0f | %7.2f%% %7.2f%% %7.2f%%\n", rv.clase[k], rv.spec[k], rv.practica[k],
           100 * rv.peso[0][k], 100 * rv.peso[1][k], 100 * rv.peso[2][k]);
  return 0;
}

/* ---- correr: una serie en CSV, con el decisiones.csv del testbench --------------------------------- */

static int leer_csv(const char *ruta, unsigned char **precios) {
  FILE *f = fopen(ruta, "r");
  if (!f) morir("no se pudo abrir", ruta);
  char linea[256];
  int n = 0, cap = 1 << 16;
  *precios = malloc((size_t)cap);
  if (!fgets(linea, sizeof linea, f)) morir("serie vacia", ruta);
  while (fgets(linea, sizeof linea, f)) {
    char *coma = strchr(linea, ',');
    if (!coma) continue;
    int p = atoi(coma + 1);
    if (p < 1 || p > 255) morir("precio fuera de 1..255 en", ruta);
    if (n == cap) { cap *= 2; *precios = realloc(*precios, (size_t)cap); }
    (*precios)[n++] = (unsigned char)p;
  }
  fclose(f);
  return n;
}

static int cmd_correr(void) {
  const char *spec0 = opcion("--estrategia", "base"), *serie = opcion("--serie", "tb/practica.csv");
  const char *salida = opcion("-o", NULL);
  char spec[512], error[256];
  unsigned char *precios;
  int n = leer_csv(serie, &precios), nticks = opcion_int("--nticks", 0), perdidos = opcion_int("--perdidos", 0);
  if (nticks > 0 && nticks < n) n = nticks;
  resolver(spec0, spec, sizeof spec);
  Instancia *inst = instancia_crear(spec, error, sizeof error);
  if (!inst) morir(error, NULL);
  unsigned char *leidos = malloc((size_t)n);
  Resultado r = correr_serie(inst, precios, n, &g_reglas, semilla_serie(instancia_spec(inst), 0), perdidos, leidos);
  if (salida) {
    FILE *f = fopen(salida, "w");
    if (!f) morir("no se pudo crear", salida);
    Cuenta c;
    cuenta_iniciar(&c, &g_reglas);
    fprintf(f, "tick,precio,decision,caja,acciones,patrimonio\n");
    for (int t = 0; t < n; t++) {
      cuenta_ejecutar(&c, &g_reglas, leidos[t], precios[t]);
      fprintf(f, "%d,%d,%02x,%d,%d,%d\n", t, precios[t], leidos[t], c.caja, c.acciones, c.w);
    }
    fclose(f);
  }
  printf("estrategia %s (%s), serie %s, %d ticks, precios iniciales sin ver %d\n", spec0, instancia_spec(inst), serie, n, perdidos);
  printf("patrimonio %d ordenes %d comisiones %d perdida_maxima %d comprar_y_mantener %d\n", r.w, r.ordenes,
         r.ordenes * g_reglas.comision, r.max_dd, r.byh);
  instancia_destruir(inst);
  return 0;
}

/* ---- mercado: contabilidad de flujos de órdenes, para comparar con ref/market.py ------------------ */
/* Entrada: "R caja comision" empieza un flujo; después "precio decision" (decimal) por tick.
 * Salida: por cada tick "caja acciones patrimonio ordenes perdida_maxima". */

static int cmd_mercado(void) {
  char linea[128];
  Reglas r = g_reglas;
  Cuenta c;
  cuenta_iniciar(&c, &r);
  while (fgets(linea, sizeof linea, stdin)) {
    if (linea[0] == 'R') {
      sscanf(linea + 1, "%d %d", &r.caja0, &r.comision);
      cuenta_iniciar(&c, &r);
      continue;
    }
    int p, d;
    if (sscanf(linea, "%d %d", &p, &d) != 2) continue;
    cuenta_ejecutar(&c, &r, d, p);
    printf("%d %d %d %d %d\n", c.caja, c.acciones, c.w, c.ordenes, c.max_dd);
  }
  return 0;
}

/* ---- detalle, resumen, lote-texto ---------------------------------------------------------------------- */

static int cmd_detalle(void) {
  const char *ruta = opcion("--lote", NULL);
  char spec[512];
  if (!ruta) morir("falta --lote ARCHIVO.bin", NULL);
  resolver(opcion("--estrategia", "base"), spec, sizeof spec);
  Lote *l = lote_leer(ruta);
  if (!l) morir("no se pudo leer", ruta);
  Resultado *res = malloc(sizeof(Resultado) * (size_t)l->ns);
  if (evaluar_lote(spec, l, &g_reglas, res)) return 1;
  for (int i = 0; i < l->ns; i++)            /* patrimonio ordenes perdida_maxima aux0..aux3 comprar_y_mantener */
    printf("%d %d %d %d %d %d %d %d\n", res[i].w, res[i].ordenes, res[i].max_dd, res[i].aux[0], res[i].aux[1],
           res[i].aux[2], res[i].aux[3], res[i].byh);
  return 0;
}

static int cmd_resumen(void) {
  Lista l;
  const char *conjunto = opcion("--conjunto", "remuestreo");
  int largo = opcion_int("--largo", 2000), semilla = opcion_int("--semilla", 0);
  lista_leer(&l, opcion("--estrategia", POR_DEFECTO));
  Tabla t = tabla_cargar(&l, conjunto, largo, semilla);
  printf("# %s: %d series.%s candidato n media dif ee mediana p5 peor mejor sobre_byh ordenes act geom pausa tope vetado\n",
         t.lote->nombre, t.ns, nota_interior());
  for (int c = 0; c < l.nc; c++) {
    Fila f = fila(&t, c, 0, 0, t.ns);
    printf("%s %d %.6f %.6f %.6f %.0f %.0f %.0f %.0f %.6f %.4f %.6f %.4f %.6f %.6f %.6f\n", l.nombre[c], f.r.n, f.r.media, f.dif,
           f.ee, f.r.mediana, f.r.p5, f.r.peor, f.r.mejor, f.sobre_byh, f.ordenes, f.act, media_geometrica(t.w[c], t.ns),
           f.pausa, f.tope, f.veto);
  }
  tabla_liberar(&t);
  return 0;
}

static int cmd_lote_texto(void) {
  if (g_argc < 3) morir("uso: lote-texto ARCHIVO.bin [--max N]", NULL);
  Lote *l = lote_leer(g_argv[2]);
  if (!l) morir("no se pudo leer", g_argv[2]);
  int max = opcion_int("--max", l->ns);
  for (int i = 0; i < l->ns && i < max; i++) {
    const unsigned char *p = l->datos + (size_t)i * l->n;
    for (int t = 0; t < l->n; t++) printf(t ? " %d" : "%d", p[t]);
    putchar('\n');
  }
  return 0;
}

/* ---- causal: ninguna estrategia puede depender de precios que todavía no llegan ------------------- */
/* Para cada estrategia y cada serie de prueba:
 *   - se corre dos veces y debe decidir lo mismo (no guarda nada entre rondas);
 *   - se cambia la serie desde el tick T en adelante y las decisiones leídas
 *     hasta el tick T (las que se tomaron viendo solo precios anteriores a T)
 *     deben ser idénticas;
 *   - se corta la serie en T y deben ser idénticas (no conoce el largo). */

static void serie_de_prueba(unsigned char *p, int n, Azar *a) {
  double x = 40 + 170 * azar_u01(a), m = x;
  for (int t = 0; t < n; t++) {
    x += 0.05 * (m - x) + 3.0 * (azar_u01(a) + azar_u01(a) + azar_u01(a) - 1.5);
    if (azar_entero(a, 400) == 0) m += 40 * (azar_u01(a) - 0.5);
    if (x < 1) x = 1;
    if (x > 255) x = 255;
    p[t] = (unsigned char)(x + 0.5);
  }
}

static int causal_una(const char *spec, int *pruebas) {
  enum { N = 3000, SERIES = 6 };
  static const int CORTES[] = {1, 2, 17, 400, 1500, 2999};
  char error[256];
  Instancia *inst = instancia_crear(spec, error, sizeof error);
  if (!inst) { printf("  %-60s ERROR %s\n", spec, error); return 1; }
  unsigned char p[N], q[N], d0[N], d1[N];
  Azar a;
  int fallas = 0;
  azar_sembrar(&a, 12345);
  for (int s = 0; s < SERIES; s++) {
    uint64_t sem = semilla_serie(instancia_spec(inst), s);
    serie_de_prueba(p, N, &a);
    correr_serie(inst, p, N, &g_reglas, sem, 0, d0);
    serie_de_prueba(q, N, &a);
    correr_serie(inst, q, N, &g_reglas, sem + 1, 0, d1);          /* otra ronda entre medio */
    correr_serie(inst, p, N, &g_reglas, sem, 0, d1);
    fallas += memcmp(d0, d1, N) != 0; (*pruebas)++;
    for (size_t k = 0; k < sizeof CORTES / sizeof CORTES[0]; k++) {
      int T = CORTES[k];
      memcpy(q, p, N);
      for (int t = T; t < N; t++) q[t] = (unsigned char)(1 + azar_entero(&a, 255));
      correr_serie(inst, q, N, &g_reglas, sem, 0, d1);
      fallas += memcmp(d0, d1, (size_t)T + 1 > N ? N : (size_t)T + 1) != 0; (*pruebas)++;
      correr_serie(inst, p, T, &g_reglas, sem, 0, d1);
      fallas += memcmp(d0, d1, (size_t)T) != 0; (*pruebas)++;
    }
  }
  instancia_destruir(inst);
  printf("  %-60s %s\n", spec, fallas ? "FALLA: depende del futuro o guarda estado entre rondas" : "ok");
  return fallas;
}

static int cmd_causal(void) {
  const char *una = opcion("--estrategia", NULL);
  int fallas = 0, pruebas = 0, n = 0;
  printf("Prueba de causalidad: decisiones identicas al cambiar o cortar el futuro, y al repetir la ronda\n");
  if (una) {
    char spec[512];
    resolver(una, spec, sizeof spec);
    fallas += causal_una(spec, &pruebas); n++;
  } else {
    for (int k = 0; k < nucleo_nestrategias(); k++, n++) fallas += causal_una(nucleo_estrategia(k)->nombre, &pruebas);
    for (int k = 0; k < nucleo_nalias(); k++, n++) fallas += causal_una(nucleo_alias_nombre(k), &pruebas);
    for (int k = 0; k < nucleo_nrivales(); k++, n++) fallas += causal_una(nucleo_rival_spec(k), &pruebas);
  }
  printf("%s: %d estrategias, %d comparaciones, %d fallas\n", fallas ? "FAIL" : "PASS", n, pruebas, fallas);
  return fallas ? 1 : 0;
}

/* ---- bordes: qué pasa con los límites 1 y 255 --------------------------------------------------------- */

static int cmd_bordes(void) {
  int largo = opcion_int("--largo", 2000), semilla = opcion_int("--semilla", 0);
  static const char *conjuntos[] = {"remuestreo", "plausibles", "estres"};
  Lista l;
  g_interior = 0; g_parada = 0;                    /* esta tabla siempre mira el conjunto completo */
  lista_leer(&l, "base");
  printf("=== Limites 1 y 255: series de %d ticks, semilla %d (%s) ===\n", largo, semilla, nombre_semilla(semilla));
  printf("Porcentaje de series que tocan cada zona, y la regla base segun el precio minimo de la serie.\n\n");
  printf("%-20s %6s | %7s %7s %7s %7s %7s | %24s | %24s\n", "familia", "n", "toca 1", "min<=5", "min<=20", "max>=250",
         "toca 255", "base si min > 20: media, mediana", "base si min <= 20: media, mediana");
  for (int g = 0; g < 3; g++) {
    Tabla t = tabla_cargar(&l, conjuntos[g], largo, semilla);
    for (int k = 0; k <= t.lote->partes; k++) {
      int i0 = k < t.lote->partes ? t.lote->inicio[k] : 0, i1 = k < t.lote->partes ? t.lote->inicio[k + 1] : t.lote->ns;
      if (k == t.lote->partes && t.lote->partes == 1) break;
      int n = i1 - i0, c1 = 0, c5 = 0, c20 = 0, c250 = 0, c255 = 0, na = 0, nb = 0;
      double *alto = malloc(sizeof(double) * (size_t)n), *bajo = malloc(sizeof(double) * (size_t)n);
      for (int i = i0; i < i1; i++) {
        const unsigned char *p = t.lote->datos + (size_t)i * t.lote->n;
        int mn = 255, mx = 1;
        for (int j = 0; j < t.lote->n; j++) { if (p[j] < mn) mn = p[j]; if (p[j] > mx) mx = p[j]; }
        c1 += mn <= 1; c5 += mn <= 5; c20 += mn <= 20; c250 += mx >= 250; c255 += mx >= 255;
        if (mn > 20) alto[na++] = t.w[0][i]; else bajo[nb++] = t.w[0][i];
      }
      Resumen ra = resumir(alto, na), rb = resumir(bajo, nb);
      printf("%-20s %6d | %6.1f%% %6.1f%% %6.1f%% %6.1f%% %6.1f%% | %12.0f %11.0f | %12.0f %11.0f\n",
             k < t.lote->partes ? t.lote->parte[k] : conjuntos[g], n, 100.0 * c1 / n, 100.0 * c5 / n, 100.0 * c20 / n,
             100.0 * c250 / n, 100.0 * c255 / n, ra.media, ra.mediana, rb.media, rb.mediana);
      free(alto); free(bajo);
    }
    tabla_liberar(&t);
  }
  return 0;
}

/* ---- frontera ------------------------------------------------------------------------------------------- */

static void celda(const Fila *f) {
  printf(" %7.0f %+6.0f %4.0f %7.0f %6.0f %6.0f %3.0f%% |", f->r.media, f->dif, f->ee, f->r.mediana, f->r.p5, f->r.peor,
         100 * f->sobre_byh);
}

static int cmd_frontera(void) {
  int largo = opcion_int("--largo", 2000), semilla = opcion_int("--semilla", 0);
  Lista l;
  lista_leer(&l, opcion("--candidatos", POR_DEFECTO));
  const char *primero = largo == 2000 ? "bloques" : "practica";
  Tabla tb = tabla_cargar(&l, primero, largo, semilla), tr = tabla_cargar(&l, "remuestreo", largo, semilla);
  Tabla tp = tabla_cargar(&l, "plausibles", largo, semilla), te = tabla_cargar(&l, "estres", largo, semilla);
  const Tabla *ts[3] = {&tr, &tp, &te};

  printf("\n=== Frontera: rondas de %d ticks, semilla %d (%s) ===%s\n", largo, semilla, nombre_semilla(semilla), nota_interior());
  printf("Candidatos (especificacion):\n");
  for (int c = 0; c < l.nc; c++) {
    Instancia *i = instancia_crear(l.spec[c], NULL, 0);
    printf("  %-16s %s\n", l.nombre[c], instancia_spec(i));
    instancia_destruir(i);
  }
  printf("\nPor conjunto: media, diferencia pareada contra %s, su error estandar, mediana, percentil 5, peor caso\n", l.nombre[0]);
  printf("y porcentaje de series en que supera a comprar y mantener.\n");
  char cab[3][64];
  snprintf(cab[0], sizeof cab[0], "remuestreo (%d)", tr.ns);
  snprintf(cab[1], sizeof cab[1], "plausibles (%d)", tp.ns);
  snprintf(cab[2], sizeof cab[2], "estres (%d)", te.ns);
  if (largo == 2000) printf("%-16s | %-20s |", "candidato", "bloques: media, dif, peor");
  else printf("%-16s | %-20s |", "candidato", "practica completa: patrimonio, ordenes");
  for (int g = 0; g < 3; g++) printf(" %-47s |", cab[g]);
  printf("\n%-16s | %-*s |", "", largo == 2000 ? 25 : 38, "");
  for (int g = 0; g < 3; g++) printf(" %7s %6s %4s %7s %6s %6s %4s |", "media", "dif", "+-ee", "mediana", "p5", "peor", ">B&H");
  printf("\n");
  for (int c = 0; c < l.nc; c++) {
    Fila fb = fila(&tb, c, 0, 0, tb.ns);
    if (largo == 2000) printf("%-16s | %9.0f %+6.0f %8.0f |", l.nombre[c], fb.r.media, fb.dif, fb.r.peor);
    else printf("%-16s | %20.0f %17.0f |", l.nombre[c], fb.r.media, fb.ordenes);
    for (int g = 0; g < 3; g++) { Fila f = fila(ts[g], c, 0, 0, ts[g]->ns); celda(&f); }
    printf("\n");
  }

  printf("\nGuardia y tope: %% de series en que la guardia pauso, %% en que salto el tope, %% de ticks sin poder entrar y ordenes promedio\n");
  printf("%-16s |", "candidato");
  for (int g = 0; g < 3; g++) printf(" %-34s |", cab[g]);
  printf("\n%-16s |", "");
  for (int g = 0; g < 3; g++) printf(" %7s %7s %8s %8s |", "pausa", "tope", "vetado", "ordenes");
  printf("\n");
  for (int c = 0; c < l.nc; c++) {
    printf("%-16s |", l.nombre[c]);
    for (int g = 0; g < 3; g++) {
      Fila f = fila(ts[g], c, 0, 0, ts[g]->ns);
      printf(" %6.1f%% %6.1f%% %7.1f%% %8.1f |", 100 * f.pausa, 100 * f.tope, 100 * f.veto, f.ordenes);
    }
    printf("\n");
  }

  for (int g = 2; g >= 1; g--) {
    const Tabla *t = ts[g];
    printf("\nFamilias %s: media, diferencia con %s, error, mediana, percentil 5, peor, >B&H\n",
           g == 2 ? "de estres" : "plausibles", l.nombre[0]);
    printf("%-16s |", "candidato");
    for (int k = 0; k < t->partes; k++) printf(" %-47s |", t->lote->parte[k]);
    printf("\n");
    for (int c = 0; c < l.nc; c++) {
      printf("%-16s |", l.nombre[c]);
      for (int k = 0; k < t->partes; k++) { Fila f = fila(t, c, 0, t->inicio[k], t->inicio[k + 1]); celda(&f); }
      printf("\n");
    }
  }
  tabla_liberar(&tb); tabla_liberar(&tr); tabla_liberar(&tp); tabla_liberar(&te);
  return 0;
}

/* ---- hipotesis --------------------------------------------------------------------------------------------- */

static uint64_t semilla_torneo(const char *conjunto, int largo, int semilla, int G, int campo) {
  char texto[160];
  snprintf(texto, sizeof texto, "torneo %s %d %d %d %d", conjunto, largo, semilla, G, campo);
  return semilla_serie(texto, 0);
}

typedef struct { int nr; double **w; } TablaRivales;

static TablaRivales rivales_cargar(const Rivales *rv, const Tabla *t, const char *conjunto, int largo, int semilla) {
  TablaRivales tr;
  tr.nr = rv->nr;
  tr.w = malloc(sizeof(double *) * (size_t)rv->nr);
  for (int k = 0; k < rv->nr; k++) {
    Resultado *res;
    if (g_parada && g_parada_peso && g_parada_peso[k] == 0) res = calloc((size_t)t->lote->ns, sizeof(Resultado));
    else if (g_parada) res = resultados_parada(rv->spec[k], t->lote);
    else res = resultados(rv->spec[k], t->lote, conjunto, largo, semilla, &g_reglas);
    if (!res) morir("no se pudo evaluar el rival", rv->spec[k]);
    tr.w[k] = malloc(sizeof(double) * (size_t)t->ns);
    for (int j = 0; j < t->ns; j++) tr.w[k][j] = res[t->sel[j]].w;
    free(res);
  }
  return tr;
}

static void rivales_liberar(TablaRivales *tr) {
  for (int k = 0; k < tr->nr; k++) free(tr->w[k]);
  free(tr->w);
}

static void orden_por(const Lista *l, const double *valor, const char *titulo) {
  int idx[MAX_C];
  for (int c = 0; c < l->nc; c++) idx[c] = c;
  for (int a = 0; a < l->nc; a++)
    for (int b = a + 1; b < l->nc; b++)
      if (valor[idx[b]] > valor[idx[a]]) { int t = idx[a]; idx[a] = idx[b]; idx[b] = t; }
  printf("  %-28s", titulo);
  for (int a = 0; a < l->nc; a++) printf("%s%s", a ? " > " : "", l->nombre[idx[a]]);
  printf("\n");
}

/* Salida para otros programas (--tsv): una fila por dato, en formato largo. */
static FILE *g_tsv;
static int g_tsv_largo, g_tsv_semilla;
static const char *g_tsv_conjunto;

static void tsv(const char *candidato, const char *clave, double valor) {
  if (g_tsv)
    fprintf(g_tsv, "%d\t%d\t%s\t%s\t%s\t%s\t%.6f\n", g_tsv_largo, g_tsv_semilla, g_interior ? "interiores" : "todas",
            g_tsv_conjunto, candidato, clave, valor);
}

static void tsv2(const char *candidato, const char *clave, const char *sufijo, double valor) {
  char k[160];
  snprintf(k, sizeof k, "%s%s", clave, sufijo);
  tsv(candidato, k, valor);
}

static int hilos(void) {
  const char *h = getenv("HILOS");
  return h && atoi(h) > 0 ? atoi(h) : 6;
}

static int cmd_hipotesis(void) {
  int largo = opcion_int("--largo", 2000), semilla = opcion_int("--semilla", 0), G0 = opcion_int("--G", 10);
  int campo0 = campo_indice(opcion("--campo", "mixto"));
  static const char *conjuntos[] = {"evidencia", "remuestreo", "plausibles", "estres"};
  static const int GS[] = {5, 10, 15};
  const char *ruta_tsv = opcion("--tsv", NULL);
  char texto[4096];
  Lista l;
  Rivales rv;
  if (campo0 < 0) morir("campo desconocido (ingenuo, mixto o fuerte)", NULL);
  const char *pedidos = opcion("--candidatos", POR_DEFECTO);
  const char *sep = strchr(pedidos, ';') || strchr(pedidos, '=') ? ";" : ",";
  snprintf(texto, sizeof texto, "%s%snada%sbyh", pedidos, sep, sep);
  lista_leer(&l, texto);
  int ref = lista_buscar(&l, opcion("--ref", l.nombre[0]));
  if (ref < 0) morir("--ref no esta entre los candidatos", NULL);
  if (rivales_preparar(&rv, &g_reglas)) return 1;
  if (ruta_tsv) {
    if (!(g_tsv = fopen(ruta_tsv, "w"))) morir("no se pudo crear", ruta_tsv);
    fprintf(g_tsv, "largo\tsemilla\tseries\tconjunto\tcandidato\tclave\tvalor\n");
    g_tsv_largo = largo; g_tsv_semilla = semilla;
  }

  printf("\n=== Hipotesis de puntaje: rondas de %d ticks, semilla %d (%s) ===%s\n", largo, semilla, nombre_semilla(semilla), nota_interior());
  printf("Referencia de las diferencias: %s. Las filas nada y byh son no operar y \"comprar 63 siempre\".\n", l.nombre[ref]);
  printf("Torneo: %d rivales posibles, campo de G grupos sorteado segun la composicion (comando rivales).\n", rv.nr);

  for (int g = 0; g < 4; g++) {
    Tabla t = tabla_cargar(&l, conjuntos[g], largo, semilla);
    TablaRivales tr = rivales_cargar(&rv, &t, conjuntos[g], largo, semilla);
    int ns = t.ns;
    double *exc = malloc(sizeof(double) * (size_t)ns);
    double *raz = malloc(sizeof(double) * (size_t)ns), *razref = malloc(sizeof(double) * (size_t)ns);
    double h1[MAX_C], h1p5[MAX_C], h2r[MAX_C], h3a[MAX_C], h3b[MAX_C], h3s[MAX_C], h3r[MAX_C], h3ap5[MAX_C], h3bp5[MAX_C];
    TresRondas *t3 = malloc(sizeof(TresRondas) * (size_t)l.nc);
    PuntosTorneo *pt = malloc(sizeof(PuntosTorneo) * (size_t)l.nc);
    g_tsv_conjunto = conjuntos[g];

    printf("\n--- Conjunto %s: %d series de %d ticks ---\n", conjuntos[g], ns, largo);
    printf("\nH1 (patrimonio) y H2 (exceso sobre comprar y mantener: diferencia W - B&H y razon W/B&H), por serie\n");
    printf("%-16s | %8s %5s %8s %8s %7s %7s %7s %5s | %8s %5s %7s %8s | %7s %6s %7s %6s %7s %6s | %5s\n", "candidato", "H1 media",
           "+-ee", "mediana", "m. geom", "p5", "peor", "dif", "+-ee", "H2 media", "+-ee", "p5", "peor", "W/B&H", "+-ee", "mediana",
           "p5", "dif", "+-ee", ">B&H");
    for (int i = 0; i < ns; i++) razref[i] = t.w[ref][i] / t.byh[i];
    for (int c = 0; c < l.nc; c++) {
      Fila f = fila(&t, c, ref, 0, ns);
      double geom = media_geometrica(t.w[c], ns), dr, dr_ee;
      for (int i = 0; i < ns; i++) { exc[i] = t.w[c][i] - t.byh[i]; raz[i] = t.w[c][i] / t.byh[i]; }
      Resumen re = resumir(exc, ns), rr = resumir(raz, ns);
      pareada(raz, razref, ns, &dr, &dr_ee);
      h1[c] = f.r.media; h1p5[c] = f.r.p5; h2r[c] = rr.media;
      printf("%-16s | %8.0f %5.0f %8.0f %8.0f %7.0f %7.0f %+7.0f %5.0f | %+8.0f %5.0f %+7.0f %+8.0f | %7.3f %6.3f %7.3f %6.3f %+7.3f %6.3f | %4.0f%%\n",
             l.nombre[c], f.r.media, f.r.ee, f.r.mediana, geom, f.r.p5, f.r.peor, f.dif, f.ee, re.media, re.ee, re.p5, re.peor,
             rr.media, rr.ee, rr.mediana, rr.p5, dr, dr_ee, 100 * f.sobre_byh);
      const char *n = l.nombre[c];
      tsv(n, "n", ns);
      tsv(n, "h1_media", f.r.media); tsv(n, "h1_ee", f.r.ee); tsv(n, "h1_mediana", f.r.mediana); tsv(n, "h1_geom", geom);
      tsv(n, "h1_p5", f.r.p5); tsv(n, "h1_peor", f.r.peor); tsv(n, "h1_dif", f.dif); tsv(n, "h1_dif_ee", f.ee);
      tsv(n, "h2_media", re.media); tsv(n, "h2_ee", re.ee); tsv(n, "h2_p5", re.p5); tsv(n, "h2_peor", re.peor);
      tsv(n, "h2r_media", rr.media); tsv(n, "h2r_ee", rr.ee); tsv(n, "h2r_mediana", rr.mediana); tsv(n, "h2r_p5", rr.p5);
      tsv(n, "h2r_peor", rr.peor); tsv(n, "h2r_dif", dr); tsv(n, "h2r_dif_ee", dr_ee);
      tsv(n, "sobre_byh", f.sobre_byh); tsv(n, "ordenes", f.ordenes);
    }

    tres_rondas(t.w, t.byh, l.nc, ref, ns, semilla_torneo(conjuntos[g], largo, semilla, 0, 0), t3);
    printf("\nH1 y H2 en una competencia de tres rondas (promedio de las tres)\n");
    printf("%-16s | %9s %5s %9s %8s %5s | %9s %5s %9s\n", "candidato", "H1 p5", "+-ee", "peor", "dif p5", "+-ee", "H2 p5",
           "+-ee", "peor");
    for (int c = 0; c < l.nc; c++) {
      printf("%-16s | %9.0f %5.0f %9.0f %+8.0f %5.0f | %+9.0f %5.0f %+9.0f\n", l.nombre[c], t3[c].w3_p5, t3[c].w3_p5_ee,
             t3[c].w3_peor, t3[c].dw3_p5, t3[c].dw3_p5_ee, t3[c].e3_p5, t3[c].e3_p5_ee, t3[c].e3_peor);
      const char *n = l.nombre[c];
      tsv(n, "h1c_p5", t3[c].w3_p5); tsv(n, "h1c_p5_ee", t3[c].w3_p5_ee); tsv(n, "h1c_peor", t3[c].w3_peor);
      tsv(n, "d_h1c_p5", t3[c].dw3_p5); tsv(n, "d_h1c_p5_ee", t3[c].dw3_p5_ee);
      tsv(n, "h2c_p5", t3[c].e3_p5); tsv(n, "h2c_p5_ee", t3[c].e3_p5_ee); tsv(n, "h2c_peor", t3[c].e3_peor);
    }

    torneo(t.w, t.byh, l.nc, ref, tr.w, rv.peso[campo0], rv.nr, ns, G0, semilla_torneo(conjuntos[g], largo, semilla, G0, campo0), pt);
    printf("\nH3, torneo con G = %d rivales y campo %s. Puntos de 0 a 2.\n", G0, CAMPOS[campo0]);
    printf("H3a: lineal en patrimonio entre el peor y el mejor del campo. H3b: lineal en el puesto.\n");
    printf("%-16s | %-41s | %-41s | %-55s\n", "", "una ronda: media, +-ee, p5", "tres rondas (promedio): p5, +-ee, peor",
           "diferencia contra la referencia");
    printf("%-16s | %6s %6s %5s  %6s %6s %5s | %6s %6s %5s  %6s %6s %5s | %7s %6s  %7s %6s  %7s %6s  %7s %6s\n",
           "candidato", "H3a", "+-ee", "p5", "H3b", "+-ee", "p5", "H3a p5", "+-ee", "peor", "H3b p5", "+-ee", "peor",
           "dH3a", "+-ee", "dH3b", "+-ee", "dp5 a", "+-ee", "dp5 b", "+-ee");
    for (int c = 0; c < l.nc; c++) {
      const PuntosTorneo *p = &pt[c];
      h3a[c] = p->a_media; h3b[c] = p->b_media; h3s[c] = p->cs_media; h3r[c] = p->cr_media; h3ap5[c] = p->ca_p5; h3bp5[c] = p->cb_p5;
      printf("%-16s | %6.3f %6.3f %5.2f  %6.3f %6.3f %5.2f | %6.3f %6.3f %5.2f  %6.3f %6.3f %5.2f | %+7.3f %6.3f  %+7.3f %6.3f  %+7.3f %6.3f  %+7.3f %6.3f\n",
             l.nombre[c], p->a_media, p->a_ee, p->a_p5, p->b_media, p->b_ee, p->b_p5, p->ca_p5, p->ca_p5_ee, p->ca_peor,
             p->cb_p5, p->cb_p5_ee, p->cb_peor, p->da, p->da_ee, p->db, p->db_ee, p->dca_p5, p->dca_p5_ee, p->dcb_p5, p->dcb_p5_ee);
      const char *n = l.nombre[c];
      tsv(n, "h3a_media", p->a_media); tsv(n, "h3a_ee", p->a_ee); tsv(n, "h3a_p5", p->a_p5);
      tsv(n, "h3b_media", p->b_media); tsv(n, "h3b_ee", p->b_ee); tsv(n, "h3b_p5", p->b_p5);
      tsv(n, "h3a_c_p5", p->ca_p5); tsv(n, "h3a_c_p5_ee", p->ca_p5_ee); tsv(n, "h3a_c_peor", p->ca_peor);
      tsv(n, "h3b_c_p5", p->cb_p5); tsv(n, "h3b_c_p5_ee", p->cb_p5_ee); tsv(n, "h3b_c_peor", p->cb_peor);
      tsv(n, "d_h3a", p->da); tsv(n, "d_h3a_ee", p->da_ee); tsv(n, "d_h3b", p->db); tsv(n, "d_h3b_ee", p->db_ee);
      tsv(n, "d_h3a_c_p5", p->dca_p5); tsv(n, "d_h3a_c_p5_ee", p->dca_p5_ee);
      tsv(n, "d_h3b_c_p5", p->dcb_p5); tsv(n, "d_h3b_c_p5_ee", p->dcb_p5_ee);
      tsv(n, "h3s_media", p->cs_media); tsv(n, "h3s_ee", p->cs_ee); tsv(n, "h3s_p5", p->cs_p5); tsv(n, "h3s_p5_ee", p->cs_p5_ee);
      tsv(n, "d_h3s", p->ds); tsv(n, "d_h3s_ee", p->ds_ee); tsv(n, "d_h3s_p5", p->dcs_p5); tsv(n, "d_h3s_p5_ee", p->dcs_p5_ee);
      tsv(n, "h3r_media", p->cr_media); tsv(n, "h3r_ee", p->cr_ee); tsv(n, "h3r_p5", p->cr_p5); tsv(n, "h3r_p5_ee", p->cr_p5_ee);
      tsv(n, "d_h3r", p->dr); tsv(n, "d_h3r_ee", p->dr_ee); tsv(n, "d_h3r_p5", p->dcr_p5); tsv(n, "d_h3r_p5_ee", p->dcr_p5_ee);
    }
    printf("\nH3 sobre la competencia completa: lineal entre el peor y el mejor segun la suma de las tres rondas.\n");
    printf("Suma: patrimonio sumado. Razon: suma de W / comprar y mantener. Diferencias contra la referencia.\n");
    printf("%-16s | %6s %6s %6s %6s  %7s %6s  %7s %6s | %6s %6s %6s %6s  %7s %6s  %7s %6s\n", "candidato", "suma", "+-ee", "p5",
           "+-ee", "dif", "+-ee", "dif p5", "+-ee", "razon", "+-ee", "p5", "+-ee", "dif", "+-ee", "dif p5", "+-ee");
    for (int c = 0; c < l.nc; c++) {
      const PuntosTorneo *p = &pt[c];
      printf("%-16s | %6.3f %6.3f %6.3f %6.3f  %+7.3f %6.3f  %+7.3f %6.3f | %6.3f %6.3f %6.3f %6.3f  %+7.3f %6.3f  %+7.3f %6.3f\n",
             l.nombre[c], p->cs_media, p->cs_ee, p->cs_p5, p->cs_p5_ee, p->ds, p->ds_ee, p->dcs_p5, p->dcs_p5_ee, p->cr_media,
             p->cr_ee, p->cr_p5, p->cr_p5_ee, p->dr, p->dr_ee, p->dcr_p5, p->dcr_p5_ee);
    }

    printf("\nOrden de los candidatos segun cada hipotesis (de mayor a menor)\n");
    orden_por(&l, h1, "H1, media del patrimonio:");
    orden_por(&l, h1p5, "H1, percentil 5:");
    orden_por(&l, h2r, "H2, media de W/B&H:");
    orden_por(&l, h3a, "H3a, puntos esperados:");
    orden_por(&l, h3b, "H3b, puntos esperados:");
    orden_por(&l, h3s, "H3 sobre la suma:");
    orden_por(&l, h3r, "H3 sobre la razon:");
    orden_por(&l, h3ap5, "H3a, p5 de tres rondas:");
    orden_por(&l, h3bp5, "H3b, p5 de tres rondas:");
    printf("  (el orden por H2 en diferencia es el mismo de H1: comprar y mantener es igual para todos en cada serie)\n");

    /* Sensibilidad: las 9 combinaciones de campo y G, una sola vez y en paralelo. */
    PuntosTorneo *ps[9];
    for (int q = 0; q < 9; q++) ps[q] = malloc(sizeof(PuntosTorneo) * (size_t)l.nc);
#pragma omp parallel for num_threads(hilos()) schedule(dynamic, 1)
    for (int q = 0; q < 9; q++)
      torneo(t.w, t.byh, l.nc, ref, tr.w, rv.peso[q / 3], rv.nr, ns, GS[q % 3],
             semilla_torneo(conjuntos[g], largo, semilla, GS[q % 3], q / 3), ps[q]);
    printf("\nSensibilidad al campo y a G: puntos de la referencia y diferencia de cada candidato contra ella (+-ee)\n");
    static const char *titulos[4] = {"H3a (lineal en patrimonio), puntos esperados", "H3b (lineal en el puesto), puntos esperados",
                                     "H3a, percentil 5 de la competencia de tres rondas", "H3b, percentil 5 de la competencia de tres rondas"};
    static const char *claves[4] = {"h3a", "h3b", "h3a_c_p5", "h3b_c_p5"};
    for (int lectura = 0; lectura < 4; lectura++) {
      printf("%s\n%-16s |", titulos[lectura], "candidato");
      for (int q = 0; q < 9; q++) { char e[32]; snprintf(e, sizeof e, "%s G=%d", CAMPOS[q / 3], GS[q % 3]); printf(" %-14s |", e); }
      printf("\n%-16s |", l.nombre[ref]);
      for (int q = 0; q < 9; q++) {
        const PuntosTorneo *p = &ps[q][ref];
        printf(" %6.3f puntos  |", lectura == 0 ? p->a_media : lectura == 1 ? p->b_media : lectura == 2 ? p->ca_p5 : p->cb_p5);
      }
      printf("\n");
      for (int c = 0; c < l.nc; c++) {
        if (c != ref) printf("%-16s |", l.nombre[c]);
        for (int q = 0; q < 9; q++) {
          const PuntosTorneo *p = &ps[q][c];
          double v = lectura == 0 ? p->a_media : lectura == 1 ? p->b_media : lectura == 2 ? p->ca_p5 : p->cb_p5;
          double d = lectura == 0 ? p->da : lectura == 1 ? p->db : lectura == 2 ? p->dca_p5 : p->dcb_p5;
          double e = lectura == 0 ? p->da_ee : lectura == 1 ? p->db_ee : lectura == 2 ? p->dca_p5_ee : p->dcb_p5_ee;
          char suf[48];
          if (c != ref) printf(" %+7.3f %6.3f |", d, e);
          snprintf(suf, sizeof suf, "_%s_%d", CAMPOS[q / 3], GS[q % 3]);
          char k[64];
          snprintf(k, sizeof k, "sens_%s", claves[lectura]); tsv2(l.nombre[c], k, suf, v);
          snprintf(k, sizeof k, "dsens_%s", claves[lectura]); tsv2(l.nombre[c], k, suf, d);
          snprintf(suf, sizeof suf, "_%s_%d_ee", CAMPOS[q / 3], GS[q % 3]);
          tsv2(l.nombre[c], k, suf, e);
        }
        if (c != ref) printf("\n");
      }
    }
    for (int q = 0; q < 9; q++) free(ps[q]);
    free(exc); free(raz); free(razref); free(t3); free(pt);
    rivales_liberar(&tr);
    tabla_liberar(&t);
  }
  if (g_tsv) { fclose(g_tsv); g_tsv = NULL; }
  return 0;
}

/* ---- veredicto: el criterio de corte para una pieza de algoritmo ------------------------------------- */
/* "Una pieza de algoritmo se descarta si no mejora los puntos esperados del
 * torneo sin empeorar el percentil 5." Se evalúa en el conjunto evidencia
 * (remuestreo y plausibles, mitad y mitad), en los dos largos de ronda y en
 * las dos lecturas del puntaje (H3a y H3b). A 2000 ticks se usan todas las
 * series. A 20 000 ticks el criterio usa las series interiores (precio
 * siempre entre 21 y 249) y el resultado con todas se muestra como
 * información: ver README.md, límites 1 y 255.
 *
 * Una fila pasa si la media de los puntos mejora en más de dos errores
 * estándar y el percentil 5 de la competencia de tres rondas no baja en más
 * de dos errores. El veredicto de un largo es PASA si pasan sus dos filas, y
 * el veredicto global es PASA solo si pasan los dos largos. */

static const char *juicio(double d, double ee) {
  return d > 2 * ee ? "mejora" : d < -2 * ee ? "empeora" : "igual";
}

static int cmd_veredicto(void) {
  const char *cand = opcion("--candidata", NULL), *refn = opcion("--referencia", "base");
  int semilla = opcion_int("--semilla", 0), G = opcion_int("--G", 10), campo = campo_indice(opcion("--campo", "mixto"));
  int un_largo = opcion_int("--largo", 0), pedir_interior = g_interior, pedir_parada = g_parada;
  static const char *conjuntos[] = {"evidencia", "remuestreo", "plausibles", "estres"};
  struct { int largo, interior, criterio, parada; } pasadas[4] = {{2000, pedir_interior, 1, 0}, {20000, 1, 1, 0}, {20000, 0, 0, 0},
                                                                  {20000, 0, 0, 1}};
  g_parada = 0;
  char texto[1200];
  Lista l;
  Rivales rv;
  if (!cand) morir("uso: veredicto --candidata SPEC [--referencia SPEC] [--semilla K] [--largo N] [--G 10] [--campo mixto]", NULL);
  if (campo < 0) morir("campo desconocido (ingenuo, mixto o fuerte)", NULL);
  snprintf(texto, sizeof texto, "%s;%s", refn, cand);
  lista_leer(&l, texto);
  if (l.nc != 2) morir("hacen falta una candidata y una referencia", NULL);
  if (rivales_preparar(&rv, &g_reglas)) return 1;

  printf("Veredicto del criterio de corte: %s contra %s\n", l.nombre[1], l.nombre[0]);
  printf("Semilla %d (%s), campo %s, G = %d rivales, caja %d, comision %d.\n", semilla, nombre_semilla(semilla),
         CAMPOS[campo], G, g_reglas.caja0, g_reglas.comision);
  if (semilla == 2) printf("AVISO: la semilla 2 es la reservada. Se usa una sola vez por candidata final, sin ajustar nada despues de mirarla.\n");
  printf("Puntos de 0 a 2. dif = candidata - referencia, pareada. Juicio con dos errores estandar.\n");
  printf("Series: todas, o interiores (precio siempre entre %d y %d). H3s y H3r: lineal sobre la suma del patrimonio y sobre\n",
         INTERIOR_MIN, INTERIOR_MAX);
  printf("la suma de W/B&H de las tres rondas; su p5 es el de esos mismos puntos.\n\n");
  printf("%-6s %-10s %-10s %-4s | %7s %7s %8s %6s %-8s | %7s %7s %8s %6s %-8s | %s\n", "largo", "series", "conjunto", "", "cand",
         "ref", "dif", "+-ee", "media", "p5 cand", "p5 ref", "dif", "+-ee", "p5 (3r)", "fila");
  int pasa[2] = {1, 1}, hay[2] = {0, 0}, literal = 1, filas = 0;
  char motivos[4096] = "";
  for (int ip = 0; ip < 4; ip++) {
    int largo = pasadas[ip].largo, li = largo == 2000 ? 0 : 1;
    if (un_largo && un_largo != largo) continue;
    if (ip == 2 && pedir_interior) continue;
    if (pasadas[ip].parada && !pedir_parada) continue;
    g_interior = pasadas[ip].interior;
    g_parada = pasadas[ip].parada;
    g_parada_peso = g_parada ? rv.peso[campo] : NULL;
    const char *series = g_parada ? "parada" : g_interior ? "interiores" : "todas";
    for (int g = 0; g < (g_parada ? 1 : 4); g++) {
      Tabla t = tabla_cargar(&l, conjuntos[g], largo, semilla);
      TablaRivales tr = rivales_cargar(&rv, &t, conjuntos[g], largo, semilla);
      PuntosTorneo pt[2];
      int criterio = g == 0 && pasadas[ip].criterio;
      torneo(t.w, t.byh, 2, 0, tr.w, rv.peso[campo], rv.nr, t.ns, G, semilla_torneo(conjuntos[g], largo, semilla, G, campo), pt);
      for (int lectura = 0; lectura < (g == 0 ? 4 : 2); lectura++) {
        static const char *nombres[4] = {"H3a", "H3b", "H3s", "H3r"};
        double mc, mr, d, e, pc, pr, dp, ep;
        switch (lectura) {
          case 0: mc = pt[1].a_media; mr = pt[0].a_media; d = pt[1].da; e = pt[1].da_ee;
                  pc = pt[1].ca_p5; pr = pt[0].ca_p5; dp = pt[1].dca_p5; ep = pt[1].dca_p5_ee; break;
          case 1: mc = pt[1].b_media; mr = pt[0].b_media; d = pt[1].db; e = pt[1].db_ee;
                  pc = pt[1].cb_p5; pr = pt[0].cb_p5; dp = pt[1].dcb_p5; ep = pt[1].dcb_p5_ee; break;
          case 2: mc = pt[1].cs_media; mr = pt[0].cs_media; d = pt[1].ds; e = pt[1].ds_ee;
                  pc = pt[1].cs_p5; pr = pt[0].cs_p5; dp = pt[1].dcs_p5; ep = pt[1].dcs_p5_ee; break;
          default: mc = pt[1].cr_media; mr = pt[0].cr_media; d = pt[1].dr; e = pt[1].dr_ee;
                  pc = pt[1].cr_p5; pr = pt[0].cr_p5; dp = pt[1].dcr_p5; ep = pt[1].dcr_p5_ee; break;
        }
        const char *jm = juicio(d, e), *jp = juicio(dp, ep);
        int ok = !strcmp(jm, "mejora") && strcmp(jp, "empeora"), cuenta = criterio && lectura < 2;
        printf("%-6d %-10s %-10s %-4s | %7.3f %7.3f %+8.3f %6.3f %-8s | %7.3f %7.3f %+8.3f %6.3f %-8s | %s\n", largo, series,
               conjuntos[g], nombres[lectura], mc, mr, d, e, jm, pc, pr, dp, ep, jp,
               cuenta ? (ok ? "pasa" : "no pasa") : "(informativa)");
        if (cuenta) {
          filas++; hay[li] = 1;
          if (!ok) {
            pasa[li] = 0;
            snprintf(motivos + strlen(motivos), sizeof motivos - strlen(motivos), "  %d ticks, %s: %s\n", largo, nombres[lectura],
                     strcmp(jm, "mejora") ? (strcmp(jm, "igual") ? "empeora los puntos esperados"
                     : "no mejora los puntos esperados (la diferencia no se distingue del ruido)") : "empeora el percentil 5");
          }
          if (!(d > 0 && dp >= 0)) literal = 0;
        }
      }
      /* H1, informativa */
      Fila f = fila(&t, 1, 0, 0, t.ns), f0 = fila(&t, 0, 0, 0, t.ns);
      printf("%-6d %-10s %-10s %-4s | %7.0f %7.0f %+8.0f %6.0f %-8s | %7.0f %7.0f %+8.0f %6s %-8s | (informativa: patrimonio, n = %d)\n",
             largo, series, conjuntos[g], "H1", f.r.media, f0.r.media, f.dif, f.ee, juicio(f.dif, f.ee), f.r.p5, f0.r.p5,
             f.r.p5 - f0.r.p5, "", "", t.ns);
      rivales_liberar(&tr);
      tabla_liberar(&t);
    }
    printf("\n");
  }
  g_interior = pedir_interior;
  g_parada = 0; g_parada_peso = NULL;
  printf("Criterio: en evidencia, una fila H3a o H3b pasa si la media de los puntos mejora en mas de 2 ee y el p5 de la\n");
  printf("competencia de tres rondas no baja en mas de 2 ee. A 20000 ticks cuentan las series interiores.\n");
  if (pedir_parada) {
    printf("Parada: todas las series de la evidencia, cada una solo hasta el primer precio fuera de %d a %d (minimo %d ticks).\n",
           INTERIOR_MIN, INTERIOR_MAX, PARADA_MIN);
    printf("No selecciona por la trayectoria futura. Es informativa: si no confirma el signo de las interiores, el resultado\n");
    printf("a 20000 ticks depende del filtro y no se debe dar por bueno.\n");
  }
  if (motivos[0]) printf("Filas que no pasan:\n%s", motivos);
  printf("Veredicto literal (solo el signo de las estimaciones, sin error): %s\n", literal ? "pasa" : "no pasa");
  if (hay[0]) printf("VEREDICTO 2000: %s\n", pasa[0] ? "PASA" : "NO_PASA");
  if (hay[1]) printf("VEREDICTO 20000: %s\n", pasa[1] ? "PASA" : "NO_PASA");
  printf("VEREDICTO: %s (%d filas de evidencia)\n", (!hay[0] || pasa[0]) && (!hay[1] || pasa[1]) ? "PASA" : "NO_PASA", filas);
  return 0;
}

/* ---- precalcular ---------------------------------------------------------------------------------------------- */

static int cmd_precalcular(void) {
  int largo = opcion_int("--largo", 2000), semilla = opcion_int("--semilla", 0);
  static const char *c2000[] = {"bloques", "remuestreo", "plausibles", "estres", "degeneradas"};
  static const char *c20000[] = {"practica", "remuestreo", "plausibles", "estres", "degeneradas"};
  const char **conjuntos = largo == 2000 ? c2000 : c20000;
  char texto[4096];
  Lista l;
  int n = 0;
  snprintf(texto, sizeof texto, "%s,nada,byh", POR_DEFECTO);
  lista_leer(&l, texto);
  for (int g = 0; g < 5; g++) {
    Lote *lote = conjunto_leer(conjuntos[g], largo, semilla);
    if (!lote) return 1;
    for (int c = 0; c < l.nc; c++, n++) free(resultados(l.spec[c], lote, conjuntos[g], largo, semilla, &g_reglas));
    for (int k = 0; k < nucleo_nrivales(); k++, n++)
      free(resultados(nucleo_rival_spec(k), lote, conjuntos[g], largo, semilla, &g_reglas));
    lote_liberar(lote);
  }
  printf("precalcular: %d ticks, semilla %d: %d evaluaciones de estrategia por conjunto\n", largo, semilla, n);
  return 0;
}

/* ---- principal ---------------------------------------------------------------------------------------------- */

int main(int argc, char **argv) {
  g_argc = argc; g_argv = argv;
  if (argc < 2) {
    fprintf(stderr, "uso: %s COMANDO [opciones]. Comandos: listar correr mercado detalle resumen lote-texto causal rivales\n"
                    "     bordes frontera hipotesis veredicto precalcular (ver el encabezado de nucleo/main.c)\n", argv[0]);
    return 2;
  }
  g_reglas.caja0 = opcion_int("--caja", CAJA0_DEF);
  g_reglas.comision = opcion_int("--comision", COMISION_DEF);
  for (int i = 2; i < argc; i++) {
    if (!strcmp(argv[i], "--interior")) g_interior = 1;
    if (!strcmp(argv[i], "--parada")) g_parada = 1;
  }
  if (g_parada && g_interior) morir("--parada y --interior no se usan juntas", NULL);
  const char *c = argv[1];
  if (!strcmp(c, "listar")) return cmd_listar();
  if (!strcmp(c, "rivales")) return cmd_rivales();
  if (!strcmp(c, "correr")) return cmd_correr();
  if (!strcmp(c, "mercado")) return cmd_mercado();
  if (!strcmp(c, "detalle")) return cmd_detalle();
  if (!strcmp(c, "resumen")) return cmd_resumen();
  if (!strcmp(c, "lote-texto")) return cmd_lote_texto();
  if (!strcmp(c, "causal")) return cmd_causal();
  if (!strcmp(c, "bordes")) return cmd_bordes();
  if (!strcmp(c, "frontera")) return cmd_frontera();
  if (!strcmp(c, "hipotesis")) return cmd_hipotesis();
  if (!strcmp(c, "veredicto")) return cmd_veredicto();
  if (!strcmp(c, "precalcular")) return cmd_precalcular();
  morir("comando desconocido", c);
  return 2;
}
