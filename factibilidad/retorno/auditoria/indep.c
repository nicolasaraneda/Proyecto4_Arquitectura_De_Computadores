/* indep.c: evaluador independiente para auditar el arnés de retorno.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * No usa ningún fuente del núcleo del arnés. Tiene su propia contabilidad
 * (escrita desde las reglas de mercado del enunciado), su propio lazo de
 * ronda, su propia versión de la regla de reversión y de las seis clases de
 * rivales, y calcula los puntajes del torneo por otro camino: el valor
 * esperado de H3a y H3b se obtiene exacto, sumando sobre la distribución del
 * peor y del mejor rival del campo, en vez de sortear campos.
 *
 * Las señales se calculan con la historia rellena: antes del primer precio la
 * serie vale el primer precio. Las sumas móviles salen de sumas acumuladas.
 *
 * Lo único que toma del arnés son datos: los archivos de series de
 * build/series, la lista de rivales (clase y especificación, de
 * mediciones/rivales.txt) y, para los candidatos que aquí no se reescriben
 * (kalman, guardia, guardia_tope), el patrimonio por serie que entrega el
 * comando `detalle` del arnés. Esos candidatos van marcados como "ext".
 *
 * Comandos (se corre desde factibilidad/retorno):
 *   indep detalle-todos ARCHIVO.bin        patrimonio y órdenes de cada rival, una fila por serie
 *   indep estudio --semilla S              todas las cifras, como líneas clave=valor
 *
 * Variables: HILOS (por defecto 6), AUD_SERIES (build/series), AUD_EXT
 * (build/auditoria/ext), AUD_RIVALES (mediciones/rivales.txt).
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CAJA0 10000
#define COMISION 5
#define PAD 256                      /* historia rellena con el primer precio */
#define MAXR 96                      /* reglas: rivales y candidatos */
#define MAXARCH 64

static int hilos(void) { const char *h = getenv("HILOS"); return h && atoi(h) > 0 ? atoi(h) : 6; }
static const char *dir_series(void) { const char *d = getenv("AUD_SERIES"); return d && *d ? d : "build/series"; }
static const char *dir_ext(void) { const char *d = getenv("AUD_EXT"); return d && *d ? d : "build/auditoria/ext"; }
static const char *arch_rivales(void) { const char *d = getenv("AUD_RIVALES"); return d && *d ? d : "mediciones/rivales.txt"; }

static void morir(const char *a, const char *b) { fprintf(stderr, "indep: %s %s\n", a, b ? b : ""); exit(2); }

/* ---- Azar propio (splitmix64) ---------------------------------------------------------------- */

static uint64_t sm64(uint64_t *x) {
  uint64_t z = (*x += 0x9E3779B97F4A7C15ULL);
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
  z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
  return z ^ (z >> 31);
}
static double u01(uint64_t *x) { return (double)(sm64(x) >> 11) / 9007199254740992.0; }
static int entero(uint64_t *x, int n) { return (int)(u01(x) * n); }

/* ---- Contabilidad propia (enunciado, sección 2.4) --------------------------------------------- */

typedef struct { long caja, acc, w; int ord; } Cta;

static inline void operar(Cta *c, int byte, int p) {
  int accion = byte >> 6, q = byte & 63;
  if (accion == 1) {                               /* comprar: lo que alcance, sin deuda */
    long alcanza = c->caja < COMISION ? 0 : (c->caja - COMISION) / p;
    if (q > alcanza) q = (int)alcanza;
    if (q >= 1) { c->caja -= (long)q * p + COMISION; c->acc += q; c->ord++; }
  } else if (accion == 2) {                        /* vender: no más de lo que se tiene */
    if (q > c->acc) q = (int)c->acc;
    if (q >= 1 && c->caja + (long)q * p - COMISION >= 0) { c->caja += (long)q * p - COMISION; c->acc -= q; c->ord++; }
  }
  c->w = c->caja + c->acc * p;
}

/* ---- Reglas ------------------------------------------------------------------------------------ */

enum { T_EMA, T_SMA, T_CRUCE_EMA, T_CRUCE_SMA, T_MOM, T_BYH, T_NADA, T_AZAR, T_EXT };

typedef struct {
  char spec[96], clase[24], nombre[64];
  int tipo, es_rival;
  int k, E, X;                 /* reversión con media exponencial: umbrales en unidades de 1/2^k */
  int n, a, b;                 /* reversión con suma móvil */
  int r, l, kr, kl, h;         /* cruce de medias */
  int hm, u, inv;              /* momentum */
  int pm;                      /* azar: probabilidad por mil */
  int q, rep;                  /* tamaño de la orden y si se repite en cada tick */
  double practica;
} Regla;

static Regla REG[MAXR];
static int NREG;

static int param(const char *spec, const char *nombre, int defecto) {
  const char *p = strchr(spec, ':');
  size_t ln = strlen(nombre);
  while (p) {
    p++;
    if (!strncmp(p, nombre, ln) && p[ln] == '=') return atoi(p + ln + 1);
    p = strchr(p, ',');
  }
  return defecto;
}

static void regla_leer(const char *spec, Regla *g) {
  memset(g, 0, sizeof *g);
  snprintf(g->spec, sizeof g->spec, "%s", spec);
  g->q = param(spec, "q", 63);
  g->rep = param(spec, "rep", 1);
  if (!strncmp(spec, "ema", 3)) {                  /* sintaxis propia para los candidatos */
    g->tipo = T_EMA; g->k = param(spec, "k", 5); g->E = param(spec, "E", 128); g->X = param(spec, "X", 0);
  } else if (!strncmp(spec, "reversion", 9)) {
    int k = param(spec, "k", 5), a = param(spec, "a", 4), b = param(spec, "b", 0);
    if (param(spec, "tipo", 0) == 0) { g->tipo = T_EMA; g->k = k; g->E = a << k; g->X = b * (1 << k); }
    else { g->tipo = T_SMA; g->n = param(spec, "n", 64); g->a = a; g->b = b; }
  } else if (!strncmp(spec, "cruce", 5)) {
    g->tipo = param(spec, "tipo", 0) ? T_CRUCE_EMA : T_CRUCE_SMA;
    g->r = param(spec, "r", 5); g->l = param(spec, "l", 20); g->kr = param(spec, "kr", 2); g->kl = param(spec, "kl", 5);
    g->h = param(spec, "h", 0);
  } else if (!strncmp(spec, "momentum", 8)) {
    g->tipo = T_MOM; g->hm = param(spec, "h", 10); g->u = param(spec, "u", 2); g->inv = param(spec, "inv", 0);
  } else if (!strncmp(spec, "byh", 3)) g->tipo = T_BYH;
  else if (!strncmp(spec, "nada", 4)) g->tipo = T_NADA;
  else if (!strncmp(spec, "azar", 4)) { g->tipo = T_AZAR; g->pm = param(spec, "pm", 100); }
  else if (!strncmp(spec, "ext", 3)) g->tipo = T_EXT;
  else morir("regla desconocida:", spec);
}

static int regla_agregar(const char *nombre, const char *clase, const char *spec, int es_rival) {
  if (NREG == MAXR) morir("demasiadas reglas", NULL);
  regla_leer(spec, &REG[NREG]);
  snprintf(REG[NREG].nombre, sizeof REG[NREG].nombre, "%s", nombre);
  snprintf(REG[NREG].clase, sizeof REG[NREG].clase, "%s", clase);
  REG[NREG].es_rival = es_rival;
  return NREG++;
}

/* Lista de rivales: clase y especificación, de mediciones/rivales.txt (se ignoran las cifras). */
static void rivales_leer(void) {
  FILE *f = fopen(arch_rivales(), "r");
  char linea[512], clase[64], spec[128];
  if (!f) morir("no se pudo abrir", arch_rivales());
  while (fgets(linea, sizeof linea, f)) {
    if (sscanf(linea, "%63s %127s", clase, spec) != 2) continue;
    if (strcmp(clase, "cruce") && strcmp(clase, "momentum") && strcmp(clase, "comprar_y_mantener") && strcmp(clase, "no_operar") &&
        strcmp(clase, "reversion") && strcmp(clase, "azar")) continue;
    regla_agregar(spec, clase, spec, 1);
  }
  fclose(f);
}

static inline long piso(long x, int k) { return x >= 0 ? x >> k : -((-x + (1L << k) - 1) >> k); }

/* Una ronda. pre[] son las sumas acumuladas de la serie con la historia rellena:
 * pre[i] = suma de los primeros i valores de (PAD veces p[0], p[0], p[1], ...). */
static void ronda(const Regla *g, const unsigned char *p, int n, const int *pre, uint64_t semilla, double *w, int *ord) {
  Cta c = {CAJA0, 0, CAJA0, 0};
  int escrito = 0, quiere = 0, pedido = 0;
  long S = 0, F = 0;
  uint64_t x = semilla;
  for (int t = 0; t < n; t++) {
    int pr = p[t];
    operar(&c, escrito, pr);                       /* la orden escrita con el precio anterior, a este precio */
    switch (g->tipo) {
      case T_NADA: escrito = 0; continue;
      case T_AZAR:
        if (entero(&x, 1000) < g->pm) escrito = (entero(&x, 2) ? 0x40 : 0x80) | g->q; else escrito = 0;
        continue;
      case T_BYH: quiere = 1; break;
      case T_EMA: {
        if (t == 0) S = (long)pr << g->k;
        long dev = ((long)pr << g->k) - S;         /* contra la media anterior a este precio */
        S += piso(dev, g->k);
        if (quiere) { if (dev > g->X) quiere = 0; }
        else if (dev < -g->E && !(dev > g->X)) quiere = 1;
      } break;
      case T_SMA: {
        long dev = (long)g->n * pr - (pre[PAD + t] - pre[PAD + t - g->n]);    /* contra los n precios anteriores */
        if (quiere) { if (dev > (long)g->b * g->n) quiere = 0; }
        else if (dev < -(long)g->a * g->n && !(dev > (long)g->b * g->n)) quiere = 1;
      } break;
      case T_CRUCE_SMA: {
        long rap = pre[PAD + t + 1] - pre[PAD + t + 1 - g->r], len = pre[PAD + t + 1] - pre[PAD + t + 1 - g->l];
        long banda = (long)g->h * g->r * g->l;
        if (rap * g->l > len * g->r + banda) quiere = 1;
        else if (rap * g->l < len * g->r - banda) quiere = 0;
      } break;
      case T_CRUCE_EMA: {
        if (t == 0) { F = (long)pr << g->kr; S = (long)pr << g->kl; }
        F += piso(((long)pr << g->kr) - F, g->kr);
        S += piso(((long)pr << g->kl) - S, g->kl);
        long rap = F << (g->kl - g->kr), banda = (long)g->h << g->kl;
        if (rap > S + banda) quiere = 1;
        else if (rap < S - banda) quiere = 0;
      } break;
      case T_MOM: {
        int d = pr - (pre[PAD + t - g->hm + 1] - pre[PAD + t - g->hm]);       /* precio de hace hm ticks */
        if (g->inv) d = -d;
        if (d >= g->u) quiere = 1;
        else if (d <= -g->u) quiere = 0;
      } break;
      default: break;
    }
    if (g->rep) escrito = (quiere ? 0x40 : 0x80) | g->q;
    else if (quiere != pedido) { pedido = quiere; escrito = (quiere ? 0x40 : 0x80) | g->q; }
    else escrito = 0;
  }
  *w = (double)c.w; *ord = c.ord;
}

static void acumular(const unsigned char *p, int n, int *pre) {
  pre[0] = 0;
  for (int i = 0; i < PAD + n; i++) pre[i + 1] = pre[i] + (i < PAD ? p[0] : p[i - PAD]);
}

/* ---- Archivos de series y resultados por archivo ---------------------------------------------- */

typedef struct {
  char nombre[64];
  int ns, n;
  unsigned char *d;
  double *w[MAXR];             /* patrimonio de cada regla en cada serie (NULL si no se ha calculado) */
  int *ord[MAXR];
  double *byh;                 /* comprar y mantener del testbench */
  unsigned char *interior;     /* 1 si el precio se queda siempre entre 21 y 249 */
  int *salida;                 /* primer tick con el precio fuera de 21..249, o n si no sale */
} Arch;

static Arch ARCH[MAXARCH];
static int NARCH;

static Arch *arch_abrir(const char *nombre) {
  for (int i = 0; i < NARCH; i++)
    if (!strcmp(ARCH[i].nombre, nombre)) return &ARCH[i];
  if (NARCH == MAXARCH) morir("demasiados archivos", NULL);
  Arch *a = &ARCH[NARCH++];
  char ruta[1024];
  int cab[2];
  memset(a, 0, sizeof *a);
  snprintf(a->nombre, sizeof a->nombre, "%s", nombre);
  if (strchr(nombre, '/')) snprintf(ruta, sizeof ruta, "%s", nombre);
  else snprintf(ruta, sizeof ruta, "%s/%s.bin", dir_series(), nombre);
  FILE *f = fopen(ruta, "rb");
  if (!f || fread(cab, sizeof(int), 2, f) != 2) morir("no se pudo leer", ruta);
  a->ns = cab[0]; a->n = cab[1];
  a->d = malloc((size_t)a->ns * a->n);
  if (fread(a->d, 1, (size_t)a->ns * a->n, f) != (size_t)a->ns * a->n) morir("archivo corto:", ruta);
  fclose(f);
  a->byh = malloc(sizeof(double) * (size_t)a->ns);
  a->interior = malloc((size_t)a->ns);
  a->salida = malloc(sizeof(int) * (size_t)a->ns);
  for (int i = 0; i < a->ns; i++) {
    const unsigned char *p = a->d + (size_t)i * a->n;
    long q = (CAJA0 - COMISION) / p[0];
    a->byh[i] = (double)(CAJA0 - COMISION - q * p[0] + q * p[a->n - 1]);
    a->salida[i] = a->n;
    for (int t = 0; t < a->n; t++)
      if (p[t] < 21 || p[t] > 249) { a->salida[i] = t; break; }
    a->interior[i] = a->salida[i] == a->n;
  }
  return a;
}

/* Calcula todas las reglas propias sobre el archivo. Si `corte` no es NULL, cada serie se corre hasta corte[i]. */
static void arch_evaluar(Arch *a, double **w, int **ord, const int *corte) {
  for (int g = 0; g < NREG; g++) {
    w[g] = malloc(sizeof(double) * (size_t)a->ns);
    ord[g] = malloc(sizeof(int) * (size_t)a->ns);
  }
#pragma omp parallel num_threads(hilos())
  {
    int *pre = malloc(sizeof(int) * (size_t)(PAD + a->n + 1));
#pragma omp for schedule(dynamic, 16)
    for (int i = 0; i < a->ns; i++) {
      const unsigned char *p = a->d + (size_t)i * a->n;
      int n = corte ? corte[i] : a->n;
      if (n < 1) n = 1;
      acumular(p, n, pre);
      for (int g = 0; g < NREG; g++) {
        if (REG[g].tipo == T_EXT) { w[g][i] = NAN; ord[g][i] = 0; continue; }
        uint64_t sem = 0xA0D17ULL * (uint64_t)(g + 1) + 0x9E37ULL * (uint64_t)(i + 1);
        ronda(&REG[g], p, n, pre, sem, &w[g][i], &ord[g][i]);
      }
    }
    free(pre);
  }
}

/* Candidatos externos: primera y segunda columna de `retorno detalle`, por archivo. */
static void arch_externos(Arch *a) {
  for (int g = 0; g < NREG; g++) {
    if (REG[g].tipo != T_EXT) continue;
    char ruta[1024];
    snprintf(ruta, sizeof ruta, "%s/%s__%s.txt", dir_ext(), REG[g].nombre, a->nombre);
    FILE *f = fopen(ruta, "r");
    if (!f) { for (int i = 0; i < a->ns; i++) a->w[g][i] = NAN; continue; }
    char linea[256];
    for (int i = 0; i < a->ns; i++) {
      int w, o;
      if (!fgets(linea, sizeof linea, f) || sscanf(linea, "%d %d", &w, &o) != 2) morir("archivo externo corto:", ruta);
      a->w[g][i] = w; a->ord[g][i] = o;
    }
    fclose(f);
  }
}

static void arch_listo(Arch *a) {
  if (a->w[0]) return;
  arch_evaluar(a, a->w, a->ord, NULL);
  arch_externos(a);
}

/* ---- Conjuntos ----------------------------------------------------------------------------------- */

static const char *PLAUS[] = {"modelo", "modelo_vecino", "dos_componentes", "cambio_volatilidad"};
static const char *ESTRES[] = {"paseo", "tendencia", "reversion", "saltos", "cambio_de_caracter", "volatil", "nivel_bajo"};

typedef struct {
  int ns, n;
  Arch **arch;                 /* archivo de cada serie */
  int *idx;                    /* posición dentro del archivo */
} Conj;

static void conj_agregar(Conj *c, const char *archivo, int tomar, int interior) {
  Arch *a = arch_abrir(archivo);
  arch_listo(a);
  if (tomar <= 0 || tomar > a->ns) tomar = a->ns;
  c->arch = realloc(c->arch, sizeof(Arch *) * (size_t)(c->ns + tomar));
  c->idx = realloc(c->idx, sizeof(int) * (size_t)(c->ns + tomar));
  c->n = a->n;
  for (int i = 0; i < tomar; i++)
    if (!interior || a->interior[i]) { c->arch[c->ns] = a; c->idx[c->ns] = i; c->ns++; }
}

static Conj conjunto(const char *nombre, int largo, int semilla, int interior) {
  Conj c = {0, 0, NULL, NULL};
  char arch[128];
  if (!strcmp(nombre, "bloques") || !strcmp(nombre, "practica")) {
    snprintf(arch, sizeof arch, "%s_n%d", nombre, largo);
    conj_agregar(&c, arch, 0, interior);
  } else if (!strcmp(nombre, "plausibles") || !strcmp(nombre, "estres")) {
    const char **fam = !strcmp(nombre, "plausibles") ? PLAUS : ESTRES;
    int nf = !strcmp(nombre, "plausibles") ? 4 : 7;
    for (int k = 0; k < nf; k++) { snprintf(arch, sizeof arch, "%s_s%d_n%d", fam[k], semilla, largo); conj_agregar(&c, arch, 0, interior); }
  } else if (!strcmp(nombre, "evidencia")) {       /* todos los remuestreos y la misma cantidad de plausibles */
    snprintf(arch, sizeof arch, "remuestreo_s%d_n%d", semilla, largo);
    Arch *r = arch_abrir(arch);
    conj_agregar(&c, arch, 0, interior);
    for (int k = 0; k < 4; k++) { snprintf(arch, sizeof arch, "%s_s%d_n%d", PLAUS[k], semilla, largo); conj_agregar(&c, arch, r->ns / 4, interior); }
  } else {
    snprintf(arch, sizeof arch, "%s_s%d_n%d", nombre, semilla, largo);
    conj_agregar(&c, arch, 0, interior);
  }
  return c;
}

static double *col(const Conj *c, int g) {         /* patrimonio de la regla g en las series del conjunto */
  double *x = malloc(sizeof(double) * (size_t)(c->ns > 0 ? c->ns : 1));
  for (int j = 0; j < c->ns; j++) x[j] = c->arch[j]->w[g][c->idx[j]];
  return x;
}
static double *col_ord(const Conj *c, int g) {
  double *x = malloc(sizeof(double) * (size_t)(c->ns > 0 ? c->ns : 1));
  for (int j = 0; j < c->ns; j++) x[j] = c->arch[j]->ord[g][c->idx[j]];
  return x;
}
static double *col_byh(const Conj *c) {
  double *x = malloc(sizeof(double) * (size_t)(c->ns > 0 ? c->ns : 1));
  for (int j = 0; j < c->ns; j++) x[j] = c->arch[j]->byh[c->idx[j]];
  return x;
}

/* ---- Estadística ------------------------------------------------------------------------------------ */

static int cmpd(const void *a, const void *b) { double x = *(const double *)a, y = *(const double *)b; return (x > y) - (x < y); }

typedef struct { double media, ee, mediana, p5, peor; int n; } Est;

static double cuantil(const double *x, int n, double q) {      /* orden[min(n-1, int(q n))] */
  double *o = malloc(sizeof(double) * (size_t)n);
  memcpy(o, x, sizeof(double) * (size_t)n);
  qsort(o, (size_t)n, sizeof(double), cmpd);
  int k = (int)(q * n);
  double v = o[k > n - 1 ? n - 1 : k];
  free(o);
  return v;
}

static Est est(const double *x, int n) {
  Est e = {0, 0, 0, 0, 0, n};
  if (n < 1) return e;
  double s = 0, s2 = 0;
  for (int i = 0; i < n; i++) s += x[i];
  e.media = s / n;
  for (int i = 0; i < n; i++) s2 += (x[i] - e.media) * (x[i] - e.media);
  e.ee = n > 1 ? sqrt(s2 / (n - 1) / n) : 0;
  e.mediana = cuantil(x, n, 0.5); e.p5 = cuantil(x, n, 0.05); e.peor = cuantil(x, n, 0.0);
  return e;
}

static Est est_dif(const double *a, const double *b, int n) {
  double *d = malloc(sizeof(double) * (size_t)(n > 0 ? n : 1));
  for (int i = 0; i < n; i++) d[i] = a[i] - b[i];
  Est e = est(d, n);
  free(d);
  return e;
}

/* ---- Torneo: valor esperado exacto ------------------------------------------------------------------ */
/* Campo: `nf` rivales fijos y G - nf rivales sorteados con probabilidades pi[] (independientes, con
 * reposición). Nosotros somos un grupo más.
 *   H3a = 2 (w - peor) / (mejor - peor) entre nosotros y los G rivales; 1 si todos empatan.
 *   H3b = 2 (rivales bajo nosotros + medio punto por cada empate) / G. */

typedef struct { int nr; int id[MAXR]; double pi[MAXR]; int nf; int fijo[8]; char nombre[24]; } Campo;

static double potencia(double x, int g) { double r = 1; for (int i = 0; i < g; i++) r *= x; return r; }

/* Para una serie: v[k] patrimonio de la regla k. Deja en a[c] y b[c] los puntos esperados de cada candidato. */
static void exacto(const Campo *cp, int G, const double *v, const int *cand, int nc, double *a, double *b) {
  double u[MAXR], pr[MAXR], cum[MAXR + 1];
  int K = 0, Gr = G - cp->nf;
  /* valores distintos de los rivales sorteables, ordenados, con su probabilidad */
  int ord[MAXR], m = 0;
  for (int k = 0; k < cp->nr; k++) if (cp->pi[k] > 0) ord[m++] = k;
  for (int i = 1; i < m; i++) {
    int t = ord[i], j = i;
    while (j > 0 && v[cp->id[ord[j - 1]]] > v[cp->id[t]]) { ord[j] = ord[j - 1]; j--; }
    ord[j] = t;
  }
  for (int i = 0; i < m; i++) {
    double x = v[cp->id[ord[i]]];
    if (K > 0 && u[K - 1] == x) pr[K - 1] += cp->pi[ord[i]];
    else { u[K] = x; pr[K] = cp->pi[ord[i]]; K++; }
  }
  cum[0] = 0;
  for (int i = 0; i < K; i++) cum[i + 1] = cum[i] + pr[i];
  double fmin = INFINITY, fmax = -INFINITY;
  for (int f = 0; f < cp->nf; f++) { double x = v[cp->fijo[f]]; if (x < fmin) fmin = x; if (x > fmax) fmax = x; }

  for (int c = 0; c < nc; c++) {
    double w = v[cand[c]], sb = 0, pb = 0;
    for (int f = 0; f < cp->nf; f++) { double x = v[cp->fijo[f]]; sb += x < w ? 1 : x == w ? 0.5 : 0; }
    for (int i = 0; i < K; i++) pb += pr[i] * (u[i] < w ? 1 : u[i] == w ? 0.5 : 0);
    b[c] = 2.0 * (sb + Gr * pb) / G;
    a[c] = 0;
    if (Gr == 0) {
      double lo = w < fmin ? w : fmin, hi = w > fmax ? w : fmax;
      a[c] = hi > lo ? 2.0 * (w - lo) / (hi - lo) : 1.0;
    }
  }
  if (Gr == 0) return;
  for (int i = 0; i < K; i++)
    for (int j = i; j < K; j++) {
      /* probabilidad de que el menor sorteado sea u[i] y el mayor u[j] */
      double p = potencia(cum[j + 1] - cum[i], Gr);
      if (j > i) {
        p -= potencia(cum[j + 1] - cum[i + 1], Gr) + potencia(cum[j] - cum[i], Gr);
        if (j > i + 1) p += potencia(cum[j] - cum[i + 1], Gr);
      }
      if (p <= 0) continue;
      double lo0 = u[i] < fmin ? u[i] : fmin, hi0 = u[j] > fmax ? u[j] : fmax;
      for (int c = 0; c < nc; c++) {
        double w = v[cand[c]], lo = w < lo0 ? w : lo0, hi = w > hi0 ? w : hi0;
        a[c] += p * (hi > lo ? 2.0 * (w - lo) / (hi - lo) : 1.0);
      }
    }
}

/* ---- Torneo: competencia de tres rondas, por sorteo propio -------------------------------------- */

static double h3a(double w, const double *x, int G) {
  double lo = w, hi = w;
  for (int g = 0; g < G; g++) { if (x[g] < lo) lo = x[g]; if (x[g] > hi) hi = x[g]; }
  return hi > lo ? 2.0 * (w - lo) / (hi - lo) : 1.0;
}
static double h3b(double w, const double *x, int G) {
  double s = 0;
  for (int g = 0; g < G; g++) s += x[g] < w ? 1 : x[g] == w ? 0.5 : 0;
  return 2.0 * s / G;
}

static int sortear(const Campo *cp, const double *acum, uint64_t *x) {
  double u = u01(x);
  for (int k = 0; k < cp->nr; k++) if (u < acum[k]) return cp->id[k];
  return cp->id[cp->nr - 1];
}

typedef struct { double p5a, p5b, p5a_ee, p5b_ee, h3s, h3r, p5a1, p5b1; double dp5a, dp5b, dp5a_ee, dp5b_ee; } Comp;

/* V[k][j]: patrimonio de la regla k en la serie j. byh[j]. cand[]: reglas candidatas; ref: índice en cand. */
static void competencia(const Campo *cp, int G, double **V, const double *byh, int ns, const int *cand, int nc, int ref,
                        uint64_t semilla, Comp *out) {
  enum { REP = 8, LOTES = 10, CAMPOS1 = 12 };
  double acum[MAXR], s = 0;
  uint64_t x = semilla;
  for (int k = 0; k < cp->nr; k++) { s += cp->pi[k]; acum[k] = s; }
  for (int k = 0; k < cp->nr; k++) acum[k] /= s;
  memset(out, 0, sizeof(Comp) * (size_t)nc);
  int *perm = malloc(sizeof(int) * (size_t)ns), campo[64];
  double xs[64];

  /* una ronda: percentil 5 de los puntos sobre series y campos */
  double **ta = malloc(sizeof(double *) * (size_t)nc), **tb = malloc(sizeof(double *) * (size_t)nc);
  for (int c = 0; c < nc; c++) { ta[c] = malloc(sizeof(double) * (size_t)ns * CAMPOS1); tb[c] = malloc(sizeof(double) * (size_t)ns * CAMPOS1); }
  for (int j = 0; j < ns; j++)
    for (int m = 0; m < CAMPOS1; m++) {
      for (int g = 0; g < G; g++) xs[g] = V[g < cp->nf ? cp->fijo[g] : sortear(cp, acum, &x)][j];
      for (int c = 0; c < nc; c++) { ta[c][j * CAMPOS1 + m] = h3a(V[cand[c]][j], xs, G); tb[c][j * CAMPOS1 + m] = h3b(V[cand[c]][j], xs, G); }
    }
  for (int c = 0; c < nc; c++) {
    out[c].p5a1 = cuantil(ta[c], ns * CAMPOS1, 0.05); out[c].p5b1 = cuantil(tb[c], ns * CAMPOS1, 0.05);
    free(ta[c]); free(tb[c]);
  }
  free(ta); free(tb);

  /* tres rondas. pasada 0: toda la muestra. pasadas 1..LOTES: un décimo de las series cada una, para el error */
  int nk_tot = ns / 3;
  if (nk_tot < 30) { free(perm); return; }
  double **ca = malloc(sizeof(double *) * (size_t)nc), **cb = malloc(sizeof(double *) * (size_t)nc);
  for (int c = 0; c < nc; c++) { ca[c] = malloc(sizeof(double) * (size_t)nk_tot); cb[c] = malloc(sizeof(double) * (size_t)nk_tot); }
  int *base = malloc(sizeof(int) * (size_t)ns);
  for (int i = 0; i < ns; i++) base[i] = i;
  for (int i = ns - 1; i > 0; i--) { int j = entero(&x, i + 1), t = base[i]; base[i] = base[j]; base[j] = t; }
  double (*lote)[4] = calloc((size_t)nc * LOTES, sizeof *lote);        /* p5a, p5b, dp5a, dp5b por lote */
  int tam = ns / LOTES;
  for (int pasada = 0; pasada <= LOTES; pasada++) {
    const int *sub = pasada == 0 ? base : base + (pasada - 1) * tam;
    int m = pasada == 0 ? ns : tam, nk = m / 3;
    if (nk < 20) continue;
    double acc[64][6];
    memset(acc, 0, sizeof acc);
    for (int rep = 0; rep < REP; rep++) {
      for (int i = 0; i < m; i++) perm[i] = sub[i];
      for (int i = m - 1; i > 0; i--) { int j = entero(&x, i + 1), t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
      double ss[64], sr[64];
      for (int c = 0; c < nc; c++) ss[c] = sr[c] = 0;
      for (int k = 0; k < nk; k++) {
        const int *tr = perm + 3 * k;
        double xsum[64], xraz[64];
        for (int g = 0; g < G; g++) {
          campo[g] = g < cp->nf ? cp->fijo[g] : sortear(cp, acum, &x);
          xsum[g] = V[campo[g]][tr[0]] + V[campo[g]][tr[1]] + V[campo[g]][tr[2]];
          xraz[g] = V[campo[g]][tr[0]] / byh[tr[0]] + V[campo[g]][tr[1]] / byh[tr[1]] + V[campo[g]][tr[2]] / byh[tr[2]];
        }
        for (int c = 0; c < nc; c++) ca[c][k] = cb[c][k] = 0;
        for (int r = 0; r < 3; r++) {
          for (int g = 0; g < G; g++) xs[g] = V[campo[g]][tr[r]];
          for (int c = 0; c < nc; c++) { ca[c][k] += h3a(V[cand[c]][tr[r]], xs, G) / 3; cb[c][k] += h3b(V[cand[c]][tr[r]], xs, G) / 3; }
        }
        for (int c = 0; c < nc; c++) {
          const double *w = V[cand[c]];
          ss[c] += h3a(w[tr[0]] + w[tr[1]] + w[tr[2]], xsum, G) / nk;
          sr[c] += h3a(w[tr[0]] / byh[tr[0]] + w[tr[1]] / byh[tr[1]] + w[tr[2]] / byh[tr[2]], xraz, G) / nk;
        }
      }
      double ra = cuantil(ca[ref], nk, 0.05), rb = cuantil(cb[ref], nk, 0.05);
      for (int c = 0; c < nc; c++) {
        double pa = cuantil(ca[c], nk, 0.05), pb = cuantil(cb[c], nk, 0.05);
        acc[c][0] += pa / REP; acc[c][1] += pb / REP; acc[c][2] += (pa - ra) / REP; acc[c][3] += (pb - rb) / REP;
        acc[c][4] += ss[c] / REP; acc[c][5] += sr[c] / REP;
      }
    }
    for (int c = 0; c < nc; c++) {
      if (pasada == 0) {
        out[c].p5a = acc[c][0]; out[c].p5b = acc[c][1]; out[c].dp5a = acc[c][2]; out[c].dp5b = acc[c][3];
        out[c].h3s = acc[c][4]; out[c].h3r = acc[c][5];
      } else for (int q = 0; q < 4; q++) lote[c * LOTES + pasada - 1][q] = acc[c][q];
    }
  }
  for (int c = 0; c < nc; c++) {                    /* error: desviación entre lotes / raíz del número de lotes */
    double ee[4];
    for (int q = 0; q < 4; q++) {
      double m1 = 0, m2 = 0;
      for (int l = 0; l < LOTES; l++) m1 += lote[c * LOTES + l][q] / LOTES;
      for (int l = 0; l < LOTES; l++) m2 += (lote[c * LOTES + l][q] - m1) * (lote[c * LOTES + l][q] - m1);
      ee[q] = sqrt(m2 / (LOTES - 1) / LOTES);
    }
    out[c].p5a_ee = ee[0]; out[c].p5b_ee = ee[1]; out[c].dp5a_ee = ee[2]; out[c].dp5b_ee = ee[3];
  }
  for (int c = 0; c < nc; c++) { free(ca[c]); free(cb[c]); }
  free(ca); free(cb); free(perm); free(base); free(lote);
}

/* ---- Campos ---------------------------------------------------------------------------------------- */

static const struct { const char *clase; double fuerte; } CLASES[6] = {
  {"cruce", 0.08}, {"momentum", 0.08}, {"comprar_y_mantener", 0.12}, {"no_operar", 0.06}, {"reversion", 0.60}, {"azar", 0.06}};

static int buscar(const char *nombre) {
  for (int g = 0; g < NREG; g++)
    if (!strcmp(REG[g].nombre, nombre)) return g;
  morir("no existe la regla", nombre);
  return -1;
}

/* Los tres mejores de cada clase en la serie de práctica completa (calculado aquí). */
static int es_mejor3(int g) {
  int mejores = 0;
  for (int h = 0; h < NREG; h++)
    if (REG[h].es_rival && h != g && !strcmp(REG[h].clase, REG[g].clase) &&
        (REG[h].practica > REG[g].practica || (REG[h].practica == REG[g].practica && h < g))) mejores++;
  return mejores < 3;
}

static Campo campo(const char *nombre) {
  Campo c;
  memset(&c, 0, sizeof c);
  snprintf(c.nombre, sizeof c.nombre, "%s", nombre);
  int base = !strcmp(nombre, "fijos2") || !strcmp(nombre, "fijos3") ? 1 : !strcmp(nombre, "ingenuo") ? 0 : !strcmp(nombre, "mixto") ? 1 :
             !strcmp(nombre, "fuerte") ? 2 : !strcmp(nombre, "reversores") ? 3 : !strcmp(nombre, "racional") ? 4 : -1;
  if (base < 0) morir("campo desconocido", nombre);
  for (int g = 0; g < NREG; g++) {
    if (!REG[g].es_rival) continue;
    int nclase = 0, ntop = 0, k = 0;
    for (int h = 0; h < NREG; h++)
      if (REG[h].es_rival && !strcmp(REG[h].clase, REG[g].clase)) { nclase++; ntop += es_mejor3(h); }
    while (strcmp(CLASES[k].clase, REG[g].clase)) k++;
    double p = 0;
    if (base == 0) p = 1.0 / 6 / nclase;
    else if (base == 1) p = es_mejor3(g) ? 1.0 / 6 / ntop : 0;
    else if (base == 2) p = es_mejor3(g) ? CLASES[k].fuerte / ntop : 0;
    else if (base == 3) p = !strcmp(REG[g].clase, "reversion") && es_mejor3(g) ? 1.0 / ntop : 0;
    else p = REG[g].practica >= CAJA0 && strcmp(REG[g].clase, "azar") ? 1.0 : 0;   /* racional: nadie entrega algo que pierde en la práctica */
    c.id[c.nr] = g; c.pi[c.nr] = p; c.nr++;
  }
  double s = 0;
  for (int k = 0; k < c.nr; k++) s += c.pi[k];
  for (int k = 0; k < c.nr; k++) c.pi[k] /= s;
  if (!strcmp(nombre, "fijos2") || !strcmp(nombre, "fijos3")) {
    c.fijo[c.nf++] = buscar("reversion:k=5,a=4,b=0");          /* la regla base */
    c.fijo[c.nf++] = buscar("reversion:k=5,a=3,b=0");          /* max_media */
    if (!strcmp(nombre, "fijos3")) c.fijo[c.nf++] = buscar("reversion:tipo=1,n=64,a=4,b=1");
  }
  return c;
}

/* ---- Estudio ------------------------------------------------------------------------------------------ */

static void kv(const char *pref, const char *clave, double v) { printf("%s.%s=%.6f\n", pref, clave, v); }

static const char *CANDS[] = {"base", "max_media", "activo", "prudente", "nada", "byh", "kalman", "guardia", "guardia_tope", "kalman_base"};
#define NCAND ((int)(sizeof CANDS / sizeof CANDS[0]))

/* Frontera y H1/H2 de un conjunto. */
static void bloque_frontera(const char *pref, const Conj *c) {
  double *wb = col(c, buscar("base")), *wm = col(c, buscar("max_media")), *byh = col_byh(c);
  char p[512];
  snprintf(p, sizeof p, "%s", pref);
  kv(p, "n", c->ns);
  for (int k = 0; k < NCAND; k++) {
    int g = buscar(CANDS[k]);
    double *w = col(c, g), *o = col_ord(c, g);
    if (c->ns < 1 || isnan(w[0])) { free(w); free(o); continue; }
    Est e = est(w, c->ns), d = est_dif(w, wb, c->ns), dm = est_dif(w, wm, c->ns), eo = est(o, c->ns);
    double *exc = malloc(sizeof(double) * (size_t)c->ns), *raz = malloc(sizeof(double) * (size_t)c->ns), slog = 0;
    for (int j = 0; j < c->ns; j++) { exc[j] = w[j] - byh[j]; raz[j] = w[j] / byh[j]; slog += log(w[j] < 1 ? 1 : w[j]); }
    Est ee = est(exc, c->ns), er = est(raz, c->ns);
    snprintf(p, sizeof p, "%s.%s", pref, CANDS[k]);
    kv(p, "media", e.media); kv(p, "ee", e.ee); kv(p, "mediana", e.mediana); kv(p, "p5", e.p5); kv(p, "peor", e.peor);
    kv(p, "dif", d.media); kv(p, "dif_ee", d.ee); kv(p, "mm_dif", dm.media); kv(p, "mm_dif_ee", dm.ee); kv(p, "ordenes", eo.media); kv(p, "geom", exp(slog / c->ns));
    kv(p, "exc_media", ee.media); kv(p, "exc_p5", ee.p5); kv(p, "raz_media", er.media); kv(p, "raz_mediana", er.mediana);
    free(w); free(o); free(exc); free(raz);
  }
  free(wb); free(wm); free(byh);
}

/* Torneo de un conjunto: exacto para todos los campos pedidos y sorteo de tres rondas. */
static void bloque_torneo(const char *pref, const Conj *c, const char **campos, int ncampos, const int *Gs, int nG, int con_sorteo,
                          uint64_t semilla) {
  if (c->ns < 30) return;
  int cand[NCAND], nc = 0, ibase = -1, imm = -1;
  char nombres[NCAND][32];
  double **V = malloc(sizeof(double *) * (size_t)NREG), *byh = col_byh(c);
  for (int g = 0; g < NREG; g++) V[g] = col(c, g);
  for (int k = 0; k < NCAND; k++) {
    int g = buscar(CANDS[k]);
    if (isnan(V[g][0])) continue;
    if (!strcmp(CANDS[k], "base")) ibase = nc;
    if (!strcmp(CANDS[k], "max_media")) imm = nc;
    snprintf(nombres[nc], sizeof nombres[nc], "%s", CANDS[k]);
    cand[nc++] = g;
  }
  double **A = malloc(sizeof(double *) * (size_t)nc), **B = malloc(sizeof(double *) * (size_t)nc);
  for (int k = 0; k < nc; k++) { A[k] = malloc(sizeof(double) * (size_t)c->ns); B[k] = malloc(sizeof(double) * (size_t)c->ns); }
  for (int f = 0; f < ncampos; f++) {
    Campo cp = campo(campos[f]);
    for (int ig = 0; ig < nG; ig++) {
      int G = Gs[ig];
#pragma omp parallel for num_threads(hilos()) schedule(static)
      for (int j = 0; j < c->ns; j++) {
        double v[MAXR], a[NCAND], b[NCAND];
        for (int g = 0; g < NREG; g++) v[g] = V[g][j];
        exacto(&cp, G, v, cand, nc, a, b);
        for (int k = 0; k < nc; k++) { A[k][j] = a[k]; B[k][j] = b[k]; }
      }
      Comp comp[NCAND], comp_mm[NCAND];
      if (con_sorteo) {
        competencia(&cp, G, V, byh, c->ns, cand, nc, ibase, semilla + 1000 * (uint64_t)f + (uint64_t)G, comp);
        competencia(&cp, G, V, byh, c->ns, cand, nc, imm, semilla + 77 + 1000 * (uint64_t)f + (uint64_t)G, comp_mm);
      }
      for (int k = 0; k < nc; k++) {
        char p[512];
        snprintf(p, sizeof p, "%s.%s.%s.G%d", pref, nombres[k], cp.nombre, G);
        Est ea = est(A[k], c->ns), eb = est(B[k], c->ns);
        Est da = est_dif(A[k], A[ibase], c->ns), db = est_dif(B[k], B[ibase], c->ns);
        Est ma = est_dif(A[k], A[imm], c->ns), mb = est_dif(B[k], B[imm], c->ns);
        kv(p, "h3a", ea.media); kv(p, "h3a_ee", ea.ee); kv(p, "h3b", eb.media); kv(p, "h3b_ee", eb.ee);
        kv(p, "dh3a", da.media); kv(p, "dh3a_ee", da.ee); kv(p, "dh3b", db.media); kv(p, "dh3b_ee", db.ee);
        kv(p, "mm_dh3a", ma.media); kv(p, "mm_dh3a_ee", ma.ee); kv(p, "mm_dh3b", mb.media); kv(p, "mm_dh3b_ee", mb.ee);
        if (con_sorteo) {
          kv(p, "p5a3", comp[k].p5a); kv(p, "p5a3_ee", comp[k].p5a_ee); kv(p, "p5b3", comp[k].p5b); kv(p, "p5b3_ee", comp[k].p5b_ee);
          kv(p, "dp5a3", comp[k].dp5a); kv(p, "dp5a3_ee", comp[k].dp5a_ee); kv(p, "dp5b3", comp[k].dp5b); kv(p, "dp5b3_ee", comp[k].dp5b_ee);
          kv(p, "mm_dp5a3", comp_mm[k].dp5a); kv(p, "mm_dp5a3_ee", comp_mm[k].dp5a_ee);
          kv(p, "mm_dp5b3", comp_mm[k].dp5b); kv(p, "mm_dp5b3_ee", comp_mm[k].dp5b_ee);
          kv(p, "h3s", comp[k].h3s); kv(p, "h3r", comp[k].h3r); kv(p, "p5a1", comp[k].p5a1); kv(p, "p5b1", comp[k].p5b1);
        }
      }
    }
  }
  for (int k = 0; k < nc; k++) { free(A[k]); free(B[k]); }
  for (int g = 0; g < NREG; g++) free(V[g]);
  free(A); free(B); free(V); free(byh);
}

/* Límites 1 y 255: cuánto tocan las series cada zona y cuánto tiempo pasan pegadas. */
static void bloque_bordes(const char *pref, const Conj *c) {
  int toca1 = 0, min20 = 0, toca255 = 0, pegada = 0;
  double ticks5 = 0, ticks20 = 0, ticks250 = 0, racha = 0;
  for (int j = 0; j < c->ns; j++) {
    const unsigned char *p = c->arch[j]->d + (size_t)c->idx[j] * c->n;
    int mn = 255, mx = 1, n5 = 0, n20 = 0, n250 = 0, run = 0, maxrun = 0;
    for (int t = 0; t < c->n; t++) {
      if (p[t] < mn) mn = p[t];
      if (p[t] > mx) mx = p[t];
      n5 += p[t] <= 5; n20 += p[t] <= 20; n250 += p[t] >= 250;
      run = p[t] <= 5 || p[t] >= 251 ? run + 1 : 0;
      if (run > maxrun) maxrun = run;
    }
    toca1 += mn <= 1; min20 += mn <= 20; toca255 += mx >= 255;
    ticks5 += n5; ticks20 += n20; ticks250 += n250; racha += maxrun;
    pegada += n20 + n250 > c->n / 10;              /* más del 10 % de la ronda en la zona de los límites */
  }
  double tot = (double)c->ns * c->n;
  kv(pref, "n", c->ns);
  kv(pref, "toca1_pct", 100.0 * toca1 / c->ns); kv(pref, "min20_pct", 100.0 * min20 / c->ns); kv(pref, "toca255_pct", 100.0 * toca255 / c->ns);
  kv(pref, "ticks_hasta5_pct", 100.0 * ticks5 / tot); kv(pref, "ticks_hasta20_pct", 100.0 * ticks20 / tot);
  kv(pref, "ticks_desde250_pct", 100.0 * ticks250 / tot); kv(pref, "racha_media_borde", racha / c->ns);
  kv(pref, "series_pegadas_pct", 100.0 * pegada / c->ns);
}

/* Sesgo del filtro de interiores: los primeros 2000 ticks de las series de 20 000, separadas según si
 * la serie completa queda dentro (interior) o no. El filtro mira toda la trayectoria, así que si
 * selecciona, se nota ya en el primer tramo. También la versión sin selección: cada serie se corre
 * hasta el primer tick en que el precio sale de 21..249, incluido ese tick y con un mínimo de 200
 * (una regla de parada que no mira el futuro). */
static void bloque_sesgo(const char *pref, int semilla) {
  Conj c = conjunto("evidencia", 20000, semilla, 0);
  int nrev = 0;
  for (int k = 0; k < 2; k++) {                    /* 0: prefijo de 2000 ticks; 1: hasta la primera salida */
    double **V = malloc(sizeof(double *) * (size_t)NREG);
    for (int g = 0; g < NREG; g++) V[g] = malloc(sizeof(double) * (size_t)c.ns);
    double *byh = malloc(sizeof(double) * (size_t)c.ns), *largo = malloc(sizeof(double) * (size_t)c.ns);
    unsigned char *dentro = malloc((size_t)c.ns);
    int hechas = 0;
    while (hechas < c.ns) {                        /* por archivo */
      Arch *a = c.arch[hechas];
      int cuantas = 0;
      while (hechas + cuantas < c.ns && c.arch[hechas + cuantas] == a) cuantas++;
      int *corte = malloc(sizeof(int) * (size_t)a->ns);
      for (int i = 0; i < a->ns; i++) {              /* el tick en que se ve el precio afuera también se juega */
        int fin = a->salida[i] < a->n ? a->salida[i] + 1 : a->n;
        corte[i] = k == 0 ? 2000 : (fin < 200 ? 200 : fin);
      }
      double *w[MAXR]; int *o[MAXR];
      arch_evaluar(a, w, o, corte);
      for (int j = 0; j < cuantas; j++) {
        int i = c.idx[hechas + j];
        const unsigned char *p = a->d + (size_t)i * a->n;
        long q = (CAJA0 - COMISION) / p[0];
        for (int g = 0; g < NREG; g++) V[g][hechas + j] = w[g][i];
        byh[hechas + j] = (double)(CAJA0 - COMISION - q * p[0] + q * p[corte[i] - 1]);
        largo[hechas + j] = corte[i];
        dentro[hechas + j] = a->interior[i];
      }
      for (int g = 0; g < NREG; g++) { free(w[g]); free(o[g]); }
      free(corte);
      hechas += cuantas;
    }
    int ib = buscar("base"), im = buscar("max_media"), ip = buscar("prudente"), ia = buscar("activo");
    char p[512];
    if (k == 0) {
      for (int lado = 0; lado < 2; lado++) {       /* 0: interiores, 1: las que el filtro deja fuera */
        double *wb = malloc(sizeof(double) * (size_t)c.ns), *wm = malloc(sizeof(double) * (size_t)c.ns), *bh = malloc(sizeof(double) * (size_t)c.ns);
        int n = 0;
        for (int j = 0; j < c.ns; j++)
          if ((dentro[j] != 0) == (lado == 0)) { wb[n] = V[ib][j]; wm[n] = V[im][j]; bh[n] = byh[j]; n++; }
        Est eb = est(wb, n), ebh = est(bh, n), d = est_dif(wm, wb, n);
        snprintf(p, sizeof p, "%s.prefijo2000.%s", pref, lado == 0 ? "interiores" : "excluidas");
        kv(p, "n", n); kv(p, "base_media", eb.media); kv(p, "base_ee", eb.ee); kv(p, "base_p5", eb.p5);
        kv(p, "byh_media", ebh.media); kv(p, "byh_ee", ebh.ee); kv(p, "mm_dif", d.media); kv(p, "mm_dif_ee", d.ee);
        free(wb); free(wm); free(bh);
      }
    } else {
      /* torneo exacto sobre las rondas cortadas en la primera salida: campo mixto y fuerte, G = 10 */
      int cand[4] = {ib, im, ip, ia};
      const char *nom[4] = {"base", "max_media", "prudente", "activo"};
      Est el = est(largo, c.ns);
      snprintf(p, sizeof p, "%s.parada", pref);
      kv(p, "n", c.ns); kv(p, "largo_medio", el.media); kv(p, "largo_mediana", el.mediana);
      for (int f = 0; f < 2; f++) {
        Campo cp = campo(f == 0 ? "mixto" : "fuerte");
        double *A[4], *B[4];
        for (int q = 0; q < 4; q++) { A[q] = malloc(sizeof(double) * (size_t)c.ns); B[q] = malloc(sizeof(double) * (size_t)c.ns); }
#pragma omp parallel for num_threads(hilos()) schedule(static)
        for (int j = 0; j < c.ns; j++) {
          double v[MAXR], a[4], b[4];
          for (int g = 0; g < NREG; g++) v[g] = V[g][j];
          exacto(&cp, 10, v, cand, 4, a, b);
          for (int q = 0; q < 4; q++) { A[q][j] = a[q]; B[q][j] = b[q]; }
        }
        for (int q = 0; q < 4; q++) {
          Est ea = est(A[q], c.ns), eb = est(B[q], c.ns), da = est_dif(A[q], A[0], c.ns), db = est_dif(B[q], B[0], c.ns);
          Est dw = est_dif(V[cand[q]], V[ib], c.ns);
          snprintf(p, sizeof p, "%s.parada.%s.%s.G10", pref, nom[q], cp.nombre);
          kv(p, "h3a", ea.media); kv(p, "h3b", eb.media); kv(p, "dh3a", da.media); kv(p, "dh3a_ee", da.ee);
          kv(p, "dh3b", db.media); kv(p, "dh3b_ee", db.ee); kv(p, "dh1", dw.media); kv(p, "dh1_ee", dw.ee);
        }
        for (int q = 0; q < 4; q++) { free(A[q]); free(B[q]); }
      }
    }
    for (int g = 0; g < NREG; g++) free(V[g]);
    free(V); free(byh); free(largo); free(dentro);
    nrev++;
  }
  (void)nrev;
}

static void preparar_reglas(void) {
  rivales_leer();
  regla_agregar("base", "", "ema:k=5,E=128,X=0", 0);
  regla_agregar("max_media", "", "ema:k=5,E=96,X=0", 0);
  regla_agregar("activo", "", "ema:k=5,E=64,X=16", 0);
  regla_agregar("prudente", "", "ema:k=5,E=192,X=-32", 0);
  regla_agregar("nada", "", "nada", 0);
  regla_agregar("byh", "", "byh:q=63,rep=1", 0);
  regla_agregar("kalman", "", "ext", 0);
  regla_agregar("guardia", "", "ext", 0);
  regla_agregar("guardia_tope", "", "ext", 0);
  regla_agregar("kalman_base", "", "ext", 0);
  /* patrimonio de cada regla en la serie de práctica completa: define los campos mixto y fuerte */
  Arch *a = arch_abrir("practica_n20000");
  arch_listo(a);
  for (int g = 0; g < NREG; g++) REG[g].practica = a->w[g][0];
}

static int cmd_detalle_todos(const char *archivo) {
  rivales_leer();
  /* los candidatos propios, con el nombre que tienen en el arnés */
  regla_agregar("cand:base", "", "ema:k=5,E=128,X=0", 0);
  regla_agregar("cand:max_media", "", "ema:k=5,E=96,X=0", 0);
  regla_agregar("cand:activo", "", "ema:k=5,E=64,X=16", 0);
  regla_agregar("cand:prudente", "", "ema:k=5,E=192,X=-32", 0);
  Arch *a = arch_abrir(archivo);
  arch_listo(a);
  for (int g = 0; g < NREG; g++) {
    printf("# %s\n", REG[g].nombre);
    for (int i = 0; i < a->ns; i++) printf("%.0f %d\n", a->w[g][i], a->ord[g][i]);
  }
  return 0;
}

static int cmd_estudio(int semilla, int rapido) {
  static const char *campos3[] = {"ingenuo", "mixto", "fuerte"};
  static const char *campos_todos[] = {"ingenuo", "mixto", "fuerte", "reversores", "fijos2", "fijos3", "racional"};
  static const char *mixto[] = {"mixto"};
  static const int G3[] = {5, 10, 15}, G10[] = {10};
  char pref[256];
  preparar_reglas();

  /* rivales: patrimonio en la práctica y peso en cada campo */
  static const char *nombres_campo[] = {"ingenuo", "mixto", "fuerte", "reversores", "racional"};
  for (int f = 0; f < 5; f++) {
    Campo cp = campo(nombres_campo[f]);
    for (int k = 0; k < cp.nr; k++) {
      snprintf(pref, sizeof pref, "rival.%s", REG[cp.id[k]].spec);
      if (f == 0) kv(pref, "practica", REG[cp.id[k]].practica);
      snprintf(pref, sizeof pref, "rival.%s.peso", REG[cp.id[k]].spec);
      kv(pref, nombres_campo[f], 100 * cp.pi[k]);
    }
  }
  for (int k = 0; k < NCAND; k++) { snprintf(pref, sizeof pref, "practica.%s", CANDS[k]); kv(pref, "w", REG[buscar(CANDS[k])].practica); }
  { Arch *a = arch_abrir("practica_n20000"); kv("practica.byh_testbench", "w", a->byh[0]);
    kv("practica.base", "ordenes", a->ord[buscar("base")][0]); }

  for (int il = 0; il < 2; il++) {
    int largo = il == 0 ? 2000 : 20000;
    for (int interior = 0; interior <= (largo == 20000); interior++) {
      const char *vista = interior ? "int" : "todas";
      static const char *conjs[] = {"evidencia", "remuestreo", "plausibles", "estres"};
      if (largo == 2000 && !interior) {
        Conj b = conjunto("bloques", 2000, 0, 0);
        snprintf(pref, sizeof pref, "s%d.n2000.todas.bloques", semilla);
        bloque_frontera(pref, &b);
      }
      for (int ic = 0; ic < 4; ic++) {
        Conj c = conjunto(conjs[ic], largo, semilla, interior);
        snprintf(pref, sizeof pref, "s%d.n%d.%s.%s", semilla, largo, vista, conjs[ic]);
        bloque_frontera(pref, &c);
        if (!interior) {
          snprintf(pref, sizeof pref, "s%d.n%d.bordes.%s", semilla, largo, conjs[ic]);
          bloque_bordes(pref, &c);
        }
        if (rapido) continue;
        snprintf(pref, sizeof pref, "s%d.n%d.%s.%s", semilla, largo, vista, conjs[ic]);
        uint64_t sem = 0xC0FFEEULL + 131 * (uint64_t)semilla + 17 * (uint64_t)largo + (uint64_t)ic + 7 * (uint64_t)interior;
        int principal = ic == 0 && (largo == 2000 || interior);
        if (principal) {
          bloque_torneo(pref, &c, campos3, 3, G3, 3, 1, sem);
          bloque_torneo(pref, &c, campos_todos + 3, 4, G10, 1, 1, sem + 5);
        } else if (ic == 0) bloque_torneo(pref, &c, campos3, 3, G10, 1, 1, sem);
        else bloque_torneo(pref, &c, mixto, 1, G10, 1, 0, sem);
      }
    }
  }
  if (!rapido) {
    snprintf(pref, sizeof pref, "s%d.n20000.sesgo", semilla);
    bloque_sesgo(pref, semilla);
  }
  return 0;
}

int main(int argc, char **argv) {
  if (argc >= 3 && !strcmp(argv[1], "detalle-todos")) return cmd_detalle_todos(argv[2]);
  if (argc >= 2 && !strcmp(argv[1], "estudio")) {
    int semilla = 0, rapido = 0;
    for (int i = 2; i < argc; i++) {
      if (!strcmp(argv[i], "--semilla") && i + 1 < argc) semilla = atoi(argv[++i]);
      if (!strcmp(argv[i], "--rapido")) rapido = 1;
    }
    return cmd_estudio(semilla, rapido);
  }
  fprintf(stderr, "uso: indep detalle-todos ARCHIVO.bin | indep estudio --semilla S [--rapido]\n");
  return 2;
}
