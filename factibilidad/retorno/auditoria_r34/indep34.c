/* indep34.c: evaluador independiente para auditar los estudios de retorno 3 y 4.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * No usa ningún fuente del núcleo del arnés ni de las carpetas auditadas.
 * Parte del evaluador de la auditoría del arnés (../auditoria/indep.c, que se
 * incluye sin modificar): de ahí salen la contabilidad escrita desde el
 * enunciado, el lazo de ronda, los 61 rivales, los campos y el valor esperado
 * exacto de H3a y H3b. Aquí se agrega, escrito de nuevo a partir de lo que
 * describen los README de los estudios:
 *
 *   - la ejecución que conoce su patrimonio (`ejec:m=8` y la candidata B);
 *   - las señales de los gestores: media exponencial, Kalman de dos estados
 *     en punto fijo y la tabla de política que aprende (`aprendiz`);
 *   - el supervisor del fondo: reparto por pesos fijos con banda de no operar,
 *     voto, pesos aprendidos con el puntaje por acción y la regla de compra
 *     chica (`fondo_rec`, `rec_e`, `completo`, `completo_s`, `fondo_min`,
 *     `min_e`, `completo_min`);
 *   - la regla con un límite por orden hipotético (para la cota de ejecución);
 *   - las tres vistas (2000 ticks, 20 000 interiores y 20 000 con parada),
 *     la semilla 3 y los duelos contra `ejec_a`.
 *
 * Lo que toma del arnés son datos: los archivos de series y la lista de
 * rivales (clase y especificación, de ../mediciones/rivales.txt).
 *
 * Comandos (se corre desde factibilidad/retorno):
 *   indep34 detalle NOMBRE ARCHIVO.bin    patrimonio y órdenes de una estrategia propia, una fila por serie
 *   indep34 tabla --semilla S             todas las cifras de la tabla final, como líneas clave=valor
 *   indep34 cotas --semilla S             cota de ejecución y oráculos del fondo
 *   indep34 lista                         las estrategias propias y su nombre en el arnés
 */
#define main indep_main
#include "../auditoria/indep.c"
#undef main

/* ---- Señales de los gestores ------------------------------------------------------------------ */

enum { S_EMA, S_KALMAN, S_TABLA, S_SIEMPRE };

typedef struct {
  int tipo, E, X, ka, h;
  int ini, pos, n;
  long S, L, T, dev;
  long A[32];                  /* tabla: acumulador de cada casilla */
  int st[128], pr[128];        /* anillo: casilla y precio de los últimos ticks */
} Senal;

static void senal_iniciar(Senal *s, int tipo, int E, int X, int ka, int h) {
  memset(s, 0, sizeof *s);
  s->tipo = tipo; s->E = E; s->X = X; s->ka = ka; s->h = h;
}

/* Recibe el precio que acaba de llegar y devuelve la posición que el gestor quiere: 0 afuera, 1 adentro. */
static int senal_paso(Senal *s, int p) {
  if (s->tipo == S_SIEMPRE) { s->pos = 1; return 1; }
  if (s->tipo == S_KALMAN) {
    /* nivel L y transitoria T con 8 bits de fracción; ganancias como sumas de desplazamientos:
     * la transitoria decae 1/32 + 1/128 por tick, el nivel corrige 1/2 + 1/8 del error y la transitoria 1/8 + 1/16 */
    if (!s->ini) { s->ini = 1; s->L = (long)p << 8; s->T = 0; }
    long Tp = s->T - piso(s->T, 5) - piso(s->T, 7);
    long e = ((long)p << 8) - s->L - Tp;
    s->L += piso(e, 1) + piso(e, 3);
    s->T = Tp + piso(e, 3) + piso(e, 4);
    s->dev = s->T;
    if (s->pos) { if (s->dev > s->X) s->pos = 0; }
    else if (s->dev < -s->E && !(s->dev > s->X)) s->pos = 1;
    return s->pos;
  }
  /* media exponencial con alfa 1/32, en treintaidosavos de precio */
  if (!s->ini) { s->S = (long)p << 5; }
  s->dev = ((long)p << 5) - s->S;
  s->S += piso(s->dev, 5);
  if (s->tipo == S_EMA) {
    s->ini = 1;
    if (s->pos) { if (s->dev > s->X) s->pos = 0; }
    else if (s->dev < -s->E && !(s->dev > s->X)) s->pos = 1;
    return s->pos;
  }
  /* tabla de política: 32 casillas de un punto de precio. La casilla guarda la estimación del
   * retorno a h ticks desde la ejecución, en precio por 2^10, como acumulador (por 2^ka). */
  if (!s->ini) {
    s->ini = 1;
    for (int i = 0; i < 32; i++) {
      long centro = (long)(i - 16) * 32 + 16;        /* centro de la casilla, en 1/32 de precio */
      s->A[i] = (-4 * centro) * (1L << s->ka);       /* la recta que implica la regla: compra bajo -96, vende sobre 0 */
    }
  }
  if (s->ka && s->n >= s->h + 1) {                   /* el resultado de la decisión del tick u ya se conoce */
    int u = s->n - 1 - s->h;
    int casilla = s->st[u & 127];
    long R = p - s->pr[(u + 1) & 127];               /* precio de ahora menos el precio al que se ejecutó */
    if (R > 31) R = 31;
    if (R < -31) R = -31;
    s->A[casilla] += R * 1024 - piso(s->A[casilla], s->ka);
  }
  long idx = piso(s->dev - s->pos, 5) + 16;
  if (idx < 0) idx = 0;
  if (idx > 31) idx = 31;
  long v = piso(s->A[idx], s->ka);
  if (s->pos) { if (v < 0) s->pos = 0; }
  else if (v > 384) s->pos = 1;
  s->st[s->n & 127] = (int)idx;
  s->pr[s->n & 127] = p;
  s->n++;
  return s->pos;
}

/* ---- Estrategias propias ---------------------------------------------------------------------- */

enum { M_EJEC, M_SENAL, M_FONDO, M_LIM };

typedef struct {
  const char *nombre, *arnes;  /* nombre aquí y especificación en el arnés (para comparar serie por serie) */
  int tipo;
  int m, m2, e2;               /* ejec */
  int stipo, E, X, ka, h;      /* señal sola */
  int conj, x, w[4], b, em, modo, v, mg, d, pp, vt;   /* fondo */
  long lim;                    /* límite por orden; 0 = sin límite */
  int caja_real, com_real;     /* robustez: reglas reales distintas de las que supone el espejo (0 y -1: las supuestas) */
} Mia;

static const Mia MIAS[] = {
  {"ejec_a", "ejec:m=8", M_EJEC, .m = 8},
  {"ejec_b", "ejec:m=8,m2=24,e2=32", M_EJEC, .m = 8, .m2 = 24, .e2 = 32},
  {"kalman", "cand:kalman", M_SENAL, .stipo = S_KALMAN, .E = 190, .X = -40},
  {"aprendiz", "cand:aprendiz", M_SENAL, .stipo = S_TABLA, .ka = 12, .h = 16},
  {"aprendiz_rapido", "cand:aprendiz_rapido", M_SENAL, .stipo = S_TABLA, .ka = 10, .h = 16},
  {"fondo_rec", "cand:fondo_rec", M_FONDO, .conj = 3, .w = {8, 4, 4, 0}, .b = 4},
  {"rec_e", "cand:rec_e", M_FONDO, .conj = 3, .w = {8, 4, 4, 0}, .b = 4, .em = 8},
  {"completo", "cand:completo", M_FONDO, .conj = 3, .x = 1, .w = {6, 3, 3, 4}, .b = 4, .em = 8},
  {"completo_s", "cand:completo_s", M_FONDO, .conj = 3, .x = 1, .w = {6, 3, 3, 4}, .b = 4},
  {"fondo_min", "cand:fondo_min", M_FONDO, .conj = 5, .w = {6, 5, 5, 0}, .modo = 2, .v = 9, .mg = 5, .d = 4, .pp = 1, .vt = 8},
  {"min_e", "cand:min_e", M_FONDO, .conj = 5, .w = {6, 5, 5, 0}, .modo = 2, .v = 9, .mg = 5, .d = 4, .pp = 1, .vt = 8, .em = 8},
  {"completo_min", "cand:completo_min", M_FONDO, .conj = 5, .x = 1, .w = {4, 4, 4, 4}, .modo = 2, .v = 9, .mg = 5, .d = 4, .pp = 1, .vt = 8, .em = 8},
  /* robustez del espejo: la maestra usa otra caja u otra comisión; el espejo sigue suponiendo 10 000 y 5.
   * Las "mm_" son max_media con esas mismas reglas reales (no lleva espejo): la referencia de cada caso. */
  {"mm_c9000", "-", M_EJEC, .caja_real = 9000}, {"ea_c9000", "-", M_EJEC, .m = 8, .caja_real = 9000},
  {"mm_c12000", "-", M_EJEC, .caja_real = 12000}, {"ea_c12000", "-", M_EJEC, .m = 8, .caja_real = 12000},
  {"mm_c20000", "-", M_EJEC, .caja_real = 20000}, {"ea_c20000", "-", M_EJEC, .m = 8, .caja_real = 20000},
  {"mm_k0", "-", M_EJEC, .com_real = -2}, {"ea_k0", "-", M_EJEC, .m = 8, .com_real = -2},
  {"lim126", "lim:L=126", M_LIM, .lim = 126},
  {"lim252", "lim:L=252", M_LIM, .lim = 252},
  {"lim2m", "lim:L=0", M_LIM, .lim = 1L << 21},      /* el "sin límite" del estudio 3: 2^21 acciones por orden */
  {"limsin", "-", M_LIM, .lim = 0},                   /* sin límite de verdad: no tiene par en el arnés */
};
#define NMIAS ((int)(sizeof MIAS / sizeof MIAS[0]))

/* Contabilidad con órdenes de cualquier tamaño (solo para la cota: esa maestra no existe). */
static void operar_grande(Cta *c, int compra, long q, int p) {
  if (compra) {
    long alcanza = c->caja < COMISION ? 0 : (c->caja - COMISION) / p;
    if (q > alcanza) q = alcanza;
    if (q >= 1) { c->caja -= q * p + COMISION; c->acc += q; c->ord++; }
  } else {
    if (q > c->acc) q = c->acc;
    if (q >= 1 && c->caja + q * p - COMISION >= 0) { c->caja += q * p - COMISION; c->acc -= q; c->ord++; }
  }
  c->w = c->caja + c->acc * p;
}

/* La maestra con otra caja inicial u otra comisión (solo para la robustez del espejo). */
static void operar_real(Cta *c, int byte, int p, int com) {
  int accion = byte >> 6;
  long q = byte & 63;
  if (accion == 1) {
    long alcanza = c->caja < com ? 0 : (c->caja - com) / p;
    if (q > alcanza) q = alcanza;
    if (q >= 1) { c->caja -= q * p + com; c->acc += q; c->ord++; }
  } else if (accion == 2) {
    if (q > c->acc) q = c->acc;
    if (q >= 1 && c->caja + q * p - com >= 0) { c->caja += q * p - com; c->acc -= q; c->ord++; }
  }
  c->w = c->caja + c->acc * p;
}

/* Mayor patrimonio visto durante la última ronda con límite hipotético (por hilo): el arnés lleva la
 * cuenta en 32 bits y esas series, si pasan de 2^31, no se pueden comparar. */
static __thread long g_wmax;

static void ronda_mia(const Mia *m, const unsigned char *p, int n, double *w, int *ord) {
  Cta c = {CAJA0, 0, CAJA0, 0};
  int escrito = 0;

  if (m->tipo == M_SENAL) {
    Senal s;
    senal_iniciar(&s, m->stipo, m->stipo == S_TABLA ? 96 : m->E, m->X, m->ka, m->h);
    for (int t = 0; t < n; t++) {
      operar(&c, escrito, p[t]);
      escrito = (senal_paso(&s, p[t]) ? 0x40 : 0x80) | 63;
    }
  } else if (m->tipo == M_EJEC) {
    /* max_media con espejo de la cuenta. El espejo supone caja 10 000 y comisión 5 y no recibe nada de la
     * maestra. La cuenta real `c` es la de la maestra: si sus reglas son las supuestas, las dos coinciden. */
    Senal s;
    Cta esp = {CAJA0, 0, CAJA0, 0};
    int com = m->com_real == -2 ? 0 : m->com_real > 0 ? m->com_real : COMISION;
    if (m->caja_real) { c.caja = m->caja_real; c.w = m->caja_real; }
    senal_iniciar(&s, S_EMA, 96, 0, 0, 0);
    for (int t = 0; t < n; t++) {
      int pr = p[t];
      operar_real(&c, escrito, pr, com);
      operar(&esp, escrito, pr);
      if (!senal_paso(&s, pr)) escrito = 0x80 | 63;
      else {
        int suprime = 0;
        if (m->m && esp.caja - COMISION < (long)m->m * pr) suprime = 1;               /* alcanzaría para menos de m acciones */
        if (m->m2 && esp.caja - COMISION < (long)m->m2 * pr && s.dev >= -(96 + m->e2)) suprime = 1;   /* resto mediano: solo más abajo */
        escrito = suprime ? 0 : 0x40 | 63;
      }
    }
  } else if (m->tipo == M_LIM) {
    Senal s;
    int pos = 0, hay = 0;
    senal_iniciar(&s, S_EMA, 96, 0, 0, 0);
    for (int t = 0; t < n; t++) {
      if (hay) operar_grande(&c, pos, m->lim ? m->lim : (1L << 40), p[t]);
      else c.w = c.caja + c.acc * p[t];
      if (t == 0 || c.w > g_wmax) g_wmax = c.w;
      pos = senal_paso(&s, p[t]); hay = 1;
    }
  } else {
    /* El fondo: gestores en papel y un supervisor que lleva la cuenta real y escribe una orden por tick. */
    Senal g[4];
    int ng = m->x ? 4 : 3, pos[4] = {0, 0, 0, 0}, ten[4] = {0, 0, 0, 0}, peso[4], voto = 0, ticks = 0, pant = p[0];
    long punt[4] = {0, 0, 0, 0}, ref[4] = {0, 0, 0, 0};
    senal_iniciar(&g[0], S_EMA, 96, 0, 0, 0);                                   /* max_media */
    if (m->conj == 3) { senal_iniciar(&g[1], S_KALMAN, 190, -40, 0, 0); senal_iniciar(&g[2], S_EMA, 64, 16, 0, 0); }   /* kalman y activo */
    else if (m->conj == 5) { senal_iniciar(&g[1], S_EMA, 128, 0, 0, 0); senal_iniciar(&g[2], S_EMA, 64, 16, 0, 0); }   /* base y activo */
    else morir("conjunto de gestores no reescrito", m->nombre);
    if (m->x) senal_iniciar(&g[3], S_TABLA, 96, 0, 12, 16);                     /* la tabla que aprende */
    for (int k = 0; k < 4; k++) peso[k] = m->w[k];
    for (int t = 0; t < n; t++) {
      int pr = p[t], dp = pr - pant;
      pant = pr;
      operar(&c, escrito, pr);                       /* 1. la orden anterior, a este precio */
      for (int k = 0; k < ng; k++) {                 /* 2. gestores */
        if (ten[k]) punt[k] += 16 * dp;              /* tuvo la acción entre el precio anterior y este */
        if (ten[k] != pos[k]) { ten[k] = pos[k]; punt[k] -= 1; }   /* su cambio de posición se ejecuta ahora: comisión */
        pos[k] = senal_paso(&g[k], pr);
      }
      ticks++;
      if (m->modo == 2 && (ticks & ((1 << m->v) - 1)) == 0) {      /* 4. frontera de ventana: un dieciseisavo del peor al mejor */
        int mejor = 0, peor = 0;
        for (int k = 1; k < ng; k++) {
          if (punt[k] - ref[k] > punt[mejor] - ref[mejor]) mejor = k;
          if (punt[k] - ref[k] < punt[peor] - ref[peor]) peor = k;
        }
        if (mejor != peor) {
          long ventaja = (punt[mejor] - ref[mejor]) - (punt[peor] - ref[peor]);
          int piso_peor = m->w[peor] - m->d < 0 ? 0 : m->w[peor] - m->d;
          if (ventaja * (1L << m->mg) > 16L * pr && peso[mejor] + 1 <= m->w[mejor] + m->d && peso[peor] - 1 >= piso_peor) {
            peso[mejor]++; peso[peor]--;
          }
        }
        for (int k = 0; k < ng; k++) ref[k] = punt[k];
      }
      int F = 0, decision;                           /* 5. posición objetivo, en dieciseisavos */
      for (int k = 0; k < ng; k++) if (pos[k]) F += peso[k];
      if (m->vt) { voto = F >= m->vt; F = voto ? 16 : 0; }
      if (F >= 16) decision = 0x40 | 63;
      else if (F <= 0) decision = 0x80 | 63;
      else {
        long V = c.acc * pr, W = c.caja + V, D = F * W - 16 * V, banda = m->b * W, q;
        decision = 0;
        if (D > banda) {
          q = D - 16 * COMISION <= 0 ? 0 : (D - 16 * COMISION) / (16L * pr);
          if (q > 63) q = 63;
          if (q > 0) decision = 0x40 | (int)q;
        } else if (D < -banda) {
          q = (-D) / (16L * pr);
          if (q > 63) q = 63;
          if (q > 0) decision = 0x80 | (int)q;
        }
      }
      if (m->em && (decision >> 6) == 1 && c.caja - COMISION < (long)m->em * pr) decision = 0;   /* compra chica: no se manda */
      escrito = decision;
    }
  }
  *w = (double)c.w; *ord = c.ord;
}

/* ---- Reglas de este estudio dentro de la tabla de reglas del evaluador ------------------------ */

static int G_MIA[NMIAS];             /* índice en REG de cada estrategia propia */
static int G_BASE, G_MM, G_ACT, G_PRU, G_NADA, G_BYH;
static const char *PSEUDO[] = {"orac1", "orac3", "orac4", "mezcla3"};   /* se calculan a partir de otras columnas */
#define NPSEUDO 4
static int G_PSEUDO[NPSEUDO];

static int mia_de(int g) {
  for (int k = 0; k < NMIAS; k++) if (G_MIA[k] == g) return k;
  return -1;
}

/* Estrategias propias sobre un archivo, cada serie hasta corte[i] (o completa). */
static void mias_evaluar(Arch *a, double **w, int **ord, const int *corte) {
#pragma omp parallel for num_threads(hilos()) schedule(dynamic, 16)
  for (int i = 0; i < a->ns; i++) {
    const unsigned char *p = a->d + (size_t)i * a->n;
    int n = corte ? corte[i] : a->n;
    if (n < 1) n = 1;
    for (int k = 0; k < NMIAS; k++) ronda_mia(&MIAS[k], p, n, &w[G_MIA[k]][i], &ord[G_MIA[k]][i]);
  }
}

static void preparar(void) {
  rivales_leer();
  G_BASE = regla_agregar("base", "", "ema:k=5,E=128,X=0", 0);
  G_MM = regla_agregar("max_media", "", "ema:k=5,E=96,X=0", 0);
  G_ACT = regla_agregar("activo", "", "ema:k=5,E=64,X=16", 0);
  G_PRU = regla_agregar("prudente", "", "ema:k=5,E=192,X=-32", 0);
  G_NADA = regla_agregar("nada", "", "nada", 0);
  G_BYH = regla_agregar("byh", "", "byh:q=63,rep=1", 0);
  for (int k = 0; k < NMIAS; k++) G_MIA[k] = regla_agregar(MIAS[k].nombre, "", "ext", 0);
  for (int k = 0; k < NPSEUDO; k++) G_PSEUDO[k] = regla_agregar(PSEUDO[k], "", "ext", 0);
  setenv("AUD_EXT", "/no/existe", 1);                /* ninguna columna se lee del arnés: todas se calculan aquí */
  Arch *a = arch_abrir("practica_n20000");
  arch_listo(a);
  mias_evaluar(a, a->w, a->ord, NULL);
  for (int g = 0; g < NREG; g++) REG[g].practica = a->w[g][0];
}

typedef struct { int ns; double **V, *byh, *largo; } Cols;

/* Patrimonio de todas las reglas en las series del conjunto. Con parada, cada serie se corre hasta el primer
 * tick con el precio fuera de 21..249, incluido ese tick y con un mínimo de 200. */
static Cols columnas(const Conj *c, int parada) {
  Cols o;
  o.ns = c->ns;
  o.V = malloc(sizeof(double *) * (size_t)NREG);
  for (int g = 0; g < NREG; g++) o.V[g] = malloc(sizeof(double) * (size_t)(c->ns > 0 ? c->ns : 1));
  o.byh = malloc(sizeof(double) * (size_t)(c->ns > 0 ? c->ns : 1));
  o.largo = malloc(sizeof(double) * (size_t)(c->ns > 0 ? c->ns : 1));
  int hechas = 0;
  while (hechas < c->ns) {
    Arch *a = c->arch[hechas];
    int cuantas = 0;
    while (hechas + cuantas < c->ns && c->arch[hechas + cuantas] == a) cuantas++;
    int *corte = malloc(sizeof(int) * (size_t)a->ns);
    for (int i = 0; i < a->ns; i++) {
      int fin = a->salida[i] < a->n ? a->salida[i] + 1 : a->n;
      corte[i] = parada ? (fin < 200 ? (200 < a->n ? 200 : a->n) : fin) : a->n;
    }
    double *w[MAXR]; int *o2[MAXR];
    if (parada) { arch_evaluar(a, w, o2, corte); mias_evaluar(a, w, o2, corte); }
    else {                                           /* series completas: se calculan una vez por archivo y se guardan */
      if (isnan(a->w[G_MIA[0]][0])) mias_evaluar(a, a->w, a->ord, NULL);
      for (int g = 0; g < NREG; g++) { w[g] = a->w[g]; o2[g] = a->ord[g]; }
    }
    for (int j = 0; j < cuantas; j++) {
      int i = c->idx[hechas + j];
      const unsigned char *p = a->d + (size_t)i * a->n;
      long q = (CAJA0 - COMISION) / p[0];
      for (int g = 0; g < NREG; g++) o.V[g][hechas + j] = w[g][i];
      o.byh[hechas + j] = (double)(CAJA0 - COMISION - q * p[0] + q * p[corte[i] - 1]);
      o.largo[hechas + j] = corte[i];
    }
    if (parada) for (int g = 0; g < NREG; g++) { free(w[g]); free(o2[g]); }
    free(corte);
    hechas += cuantas;
  }
  /* columnas calculadas: oráculo que elige después el mejor gestor de cada serie, y la mezcla fija ideal */
  int ik = G_MIA[2];                                 /* kalman propio */
  for (int j = 0; j < c->ns; j++) {
    double mm = o.V[G_MM][j], pr = o.V[G_PRU][j], bh = o.V[G_BYH][j], ka = o.V[ik][j], ac = o.V[G_ACT][j], ba = o.V[G_BASE][j];
    double m1 = mm > pr ? mm : pr, m3 = mm > ka ? mm : ka, m4 = mm > ba ? mm : ba;
    o.V[G_PSEUDO[0]][j] = m1 > bh ? m1 : bh;         /* conjunto 1: max_media, prudente, comprar y mantener */
    o.V[G_PSEUDO[1]][j] = m3 > ac ? m3 : ac;         /* conjunto 3: max_media, kalman, activo */
    o.V[G_PSEUDO[2]][j] = m4 > pr ? m4 : pr;         /* conjunto 4: max_media, base, prudente */
    o.V[G_PSEUDO[3]][j] = (3 * mm + 3 * ka + 2 * ac) / 8;   /* el conjunto 2 lleva la guardia, que no se reescribió */
  }
  return o;
}

static void cols_liberar(Cols *o) {
  for (int g = 0; g < NREG; g++) free(o->V[g]);
  free(o->V); free(o->byh); free(o->largo);
}

/* ---- Tabla final --------------------------------------------------------------------------------- */

static void kv2(const char *pref, const char *clave, double v) { printf("%s.%s=%.6f\n", pref, clave, v); }

/* Imprime, para cada candidata: H1, razón W/B&H, y por campo H3a y H3b, con la diferencia pareada contra
 * max_media (mm) y contra ejec_a (ea). */
static void bloque(const char *pref, const Cols *o, const int *cand, const char **nombres, int nc, const char **campos, int ncampos,
                   int con_p5, uint64_t semilla) {
  int ns = o->ns, imm = -1, iea = -1;
  char p[512];
  if (ns < 30) return;
  for (int k = 0; k < nc; k++) { if (cand[k] == G_MM) imm = k; if (cand[k] == G_MIA[0]) iea = k; }
  snprintf(p, sizeof p, "%s", pref);
  kv2(p, "n", ns);
  { Est el = est(o->largo, ns); kv2(p, "largo_medio", el.media); }
  double *raz_mm = malloc(sizeof(double) * (size_t)ns), *raz_ea = malloc(sizeof(double) * (size_t)ns), *raz = malloc(sizeof(double) * (size_t)ns);
  for (int j = 0; j < ns; j++) { raz_mm[j] = o->V[G_MM][j] / o->byh[j]; raz_ea[j] = o->V[G_MIA[0]][j] / o->byh[j]; }
  for (int k = 0; k < nc; k++) {
    const double *w = o->V[cand[k]];
    Est e = est(w, ns), dm = est_dif(w, o->V[G_MM], ns), de = est_dif(w, o->V[G_MIA[0]], ns);
    for (int j = 0; j < ns; j++) raz[j] = w[j] / o->byh[j];
    Est er = est(raz, ns), drm = est_dif(raz, raz_mm, ns), dre = est_dif(raz, raz_ea, ns);
    snprintf(p, sizeof p, "%s.%s", pref, nombres[k]);
    kv2(p, "h1", e.media); kv2(p, "h1_ee", e.ee); kv2(p, "h1_p5", e.p5);
    kv2(p, "dh1_mm", dm.media); kv2(p, "dh1_mm_ee", dm.ee); kv2(p, "dh1_ea", de.media); kv2(p, "dh1_ea_ee", de.ee);
    kv2(p, "raz", er.media); kv2(p, "draz_mm", drm.media); kv2(p, "draz_mm_ee", drm.ee); kv2(p, "draz_ea", dre.media); kv2(p, "draz_ea_ee", dre.ee);
  }
  free(raz_mm); free(raz_ea); free(raz);
  double **A = malloc(sizeof(double *) * (size_t)nc), **B = malloc(sizeof(double *) * (size_t)nc);
  for (int k = 0; k < nc; k++) { A[k] = malloc(sizeof(double) * (size_t)ns); B[k] = malloc(sizeof(double) * (size_t)ns); }
  for (int f = 0; f < ncampos; f++) {
    Campo cp = campo(campos[f]);
#pragma omp parallel for num_threads(hilos()) schedule(static)
    for (int j = 0; j < ns; j++) {
      double v[MAXR], a[64], b[64];
      for (int g = 0; g < NREG; g++) v[g] = o->V[g][j];
      exacto(&cp, 10, v, cand, nc, a, b);
      for (int k = 0; k < nc; k++) { A[k][j] = a[k]; B[k][j] = b[k]; }
    }
    Comp comp[64];
    if (con_p5 && f == 0) competencia(&cp, 10, o->V, o->byh, ns, cand, nc, imm, semilla, comp);
    for (int k = 0; k < nc; k++) {
      snprintf(p, sizeof p, "%s.%s.%s", pref, campos[f], nombres[k]);
      Est ea = est(A[k], ns), eb = est(B[k], ns);
      Est ma = est_dif(A[k], A[imm], ns), mb = est_dif(B[k], B[imm], ns), xa = est_dif(A[k], A[iea], ns), xb = est_dif(B[k], B[iea], ns);
      kv2(p, "h3a", ea.media); kv2(p, "h3b", eb.media);
      kv2(p, "dh3a_mm", ma.media); kv2(p, "dh3a_mm_ee", ma.ee); kv2(p, "dh3b_mm", mb.media); kv2(p, "dh3b_mm_ee", mb.ee);
      kv2(p, "dh3a_ea", xa.media); kv2(p, "dh3a_ea_ee", xa.ee); kv2(p, "dh3b_ea", xb.media); kv2(p, "dh3b_ea_ee", xb.ee);
      if (con_p5 && f == 0) {
        kv2(p, "p5a3", comp[k].p5a); kv2(p, "p5b3", comp[k].p5b);
        kv2(p, "dp5a3_mm", comp[k].dp5a); kv2(p, "dp5a3_mm_ee", comp[k].dp5a_ee); kv2(p, "dp5b3_mm", comp[k].dp5b); kv2(p, "dp5b3_mm_ee", comp[k].dp5b_ee);
      }
    }
  }
  for (int k = 0; k < nc; k++) { free(A[k]); free(B[k]); }
  free(A); free(B);
}

static int cmd_tabla(int semilla) {
  static const char *campos5[] = {"mixto", "ingenuo", "fuerte", "racional", "reversores"};
  static const char *conjs[] = {"evidencia", "remuestreo", "plausibles", "estres"};
  static const char *noms[] = {"max_media", "base", "ejec_a", "ejec_b", "aprendiz", "fondo_rec", "rec_e", "completo", "completo_s",
                               "fondo_min", "min_e", "completo_min"};
  enum { NC = 12 };
  int cand[NC];
  preparar();
  for (int k = 0; k < NC; k++) cand[k] = buscar(noms[k]);
  for (int k = 0; k < NC; k++) { char p[128]; snprintf(p, sizeof p, "practica.%s", noms[k]); kv2(p, "w", REG[cand[k]].practica); }
  for (int vista = 0; vista < 3; vista++) {          /* 0: 2000 ticks; 1: 20 000 interiores; 2: 20 000 con parada */
    int largo = vista == 0 ? 2000 : 20000;
    const char *nv = vista == 0 ? "n2000" : vista == 1 ? "n20000int" : "n20000par";
    for (int ic = 0; ic < 4; ic++) {
      if (vista == 1 && ic == 3) continue;           /* el estrés a 20 000 ticks se mira con parada */
      Conj c = conjunto(conjs[ic], largo, semilla, vista == 1);
      Cols o = columnas(&c, vista == 2);
      char pref[256];
      snprintf(pref, sizeof pref, "s%d.%s.%s", semilla, nv, conjs[ic]);
      bloque(pref, &o, cand, noms, NC, campos5, ic == 0 ? 5 : 1, ic == 0, 0xA34ULL + 131 * (uint64_t)semilla + 7 * (uint64_t)vista);
      cols_liberar(&o);
      free(c.arch); free(c.idx);
      fflush(stdout);
    }
  }
  return 0;
}

/* ---- Cotas ------------------------------------------------------------------------------------------ */

static int cmd_cotas(int semilla) {
  static const char *mixto[] = {"mixto"};
  static const char *noms[] = {"max_media", "ejec_a", "ejec_b", "lim126", "lim252", "lim2m", "limsin", "orac1", "orac3", "orac4", "mezcla3",
                               "fondo_rec", "kalman", "activo", "prudente", "byh", "base"};
  enum { NC = 17 };
  int cand[NC];
  preparar();
  for (int k = 0; k < NC; k++) cand[k] = buscar(noms[k]);
  for (int vista = 0; vista < 3; vista++) {
    int largo = vista == 0 ? 2000 : 20000;
    const char *nv = vista == 0 ? "n2000" : vista == 1 ? "n20000int" : "n20000par";
    static const char *conjs[] = {"evidencia", "remuestreo"};
    for (int ic = 0; ic < 2; ic++) {
      Conj c = conjunto(conjs[ic], largo, semilla, vista == 1);
      Cols o = columnas(&c, vista == 2);
      char pref[256];
      snprintf(pref, sizeof pref, "s%d.%s.%s", semilla, nv, conjs[ic]);
      bloque(pref, &o, cand, noms, NC, mixto, 1, 0, 0);
      if (ic == 0 && vista != 1) {
        /* robustez del espejo: ejec_a menos max_media cuando la maestra usa otra caja u otra comisión */
        static const char *casos[] = {"c9000", "c12000", "c20000", "k0"};
        for (int q = 0; q < 4; q++) {
          char a[32], b[32], pp[300];
          snprintf(a, sizeof a, "ea_%s", casos[q]); snprintf(b, sizeof b, "mm_%s", casos[q]);
          Est e = est_dif(o.V[buscar(a)], o.V[buscar(b)], o.ns), em = est(o.V[buscar(b)], o.ns);
          snprintf(pp, sizeof pp, "%s.robustez.%s", pref, casos[q]);
          kv2(pp, "dh1", e.media); kv2(pp, "dh1_ee", e.ee); kv2(pp, "mm_h1", em.media);
        }
      }
      if (ic == 0) {
        /* órdenes por ronda con cada límite, y en cuántas series el mejor gestor del conjunto 3 es max_media */
        const char *lims[] = {"max_media", "lim126", "lim252", "limsin"};
        (void)lims;
        int gana = 0;
        for (int j = 0; j < o.ns; j++) gana += o.V[G_MM][j] >= o.V[G_MIA[2]][j] && o.V[G_MM][j] >= o.V[G_ACT][j];
        kv2(pref, "conj3_gana_max_media", 100.0 * gana / o.ns);
        /* la mejor mezcla fija en octavos del conjunto 3, por H3a y por H3b, buscada aquí entre las 45 */
        Campo cp = campo("mixto");
        double mejor_a = -1e9, mejor_b = -1e9; int wa[3] = {8, 0, 0}, wb[3] = {8, 0, 0};
        double *A = malloc(sizeof(double) * (size_t)o.ns), *B = malloc(sizeof(double) * (size_t)o.ns);
        double *Am = malloc(sizeof(double) * (size_t)o.ns), *Bm = malloc(sizeof(double) * (size_t)o.ns);
        int gp = G_PSEUDO[3];
        double *guardada = malloc(sizeof(double) * (size_t)o.ns);
        memcpy(guardada, o.V[gp], sizeof(double) * (size_t)o.ns);
        for (int a8 = 0; a8 <= 8; a8++)
          for (int b8 = 0; a8 + b8 <= 8; b8++) {
            int c8 = 8 - a8 - b8;
            for (int j = 0; j < o.ns; j++) o.V[gp][j] = (a8 * o.V[G_MM][j] + b8 * o.V[G_MIA[2]][j] + c8 * o.V[G_ACT][j]) / 8;
            int cc[2] = {G_MM, gp};
#pragma omp parallel for num_threads(hilos()) schedule(static)
            for (int j = 0; j < o.ns; j++) {
              double v[MAXR], a[2], b[2];
              for (int g = 0; g < NREG; g++) v[g] = o.V[g][j];
              exacto(&cp, 10, v, cc, 2, a, b);
              A[j] = a[1]; B[j] = b[1]; Am[j] = a[0]; Bm[j] = b[0];
            }
            Est da = est_dif(A, Am, o.ns), db = est_dif(B, Bm, o.ns);
            if (da.media > mejor_a) { mejor_a = da.media; wa[0] = a8; wa[1] = b8; wa[2] = c8; }
            if (db.media > mejor_b) { mejor_b = db.media; wb[0] = a8; wb[1] = b8; wb[2] = c8; }
          }
        memcpy(o.V[gp], guardada, sizeof(double) * (size_t)o.ns);
        kv2(pref, "mezcla3_mejor_h3a", mejor_a); kv2(pref, "mezcla3_mejor_h3a_pesos", wa[0] * 100 + wa[1] * 10 + wa[2]);
        kv2(pref, "mezcla3_mejor_h3b", mejor_b); kv2(pref, "mezcla3_mejor_h3b_pesos", wb[0] * 100 + wb[1] * 10 + wb[2]);
        free(A); free(B); free(Am); free(Bm); free(guardada);
      }
      cols_liberar(&o);
      free(c.arch); free(c.idx);
      fflush(stdout);
    }
  }
  return 0;
}

/* ---- Detalle de una estrategia propia ---------------------------------------------------------------- */

static int cmd_detalle(const char *nombre, const char *archivo) {
  const Mia *m = NULL;
  for (int k = 0; k < NMIAS; k++) if (!strcmp(MIAS[k].nombre, nombre)) m = &MIAS[k];
  if (!m) morir("no existe la estrategia propia", nombre);
  Arch *a = arch_abrir(archivo);
  double *w = malloc(sizeof(double) * (size_t)a->ns);
  int *o = malloc(sizeof(int) * (size_t)a->ns);
  long *mx = malloc(sizeof(long) * (size_t)a->ns);
#pragma omp parallel for num_threads(hilos()) schedule(dynamic, 16)
  for (int i = 0; i < a->ns; i++) { g_wmax = 0; ronda_mia(m, a->d + (size_t)i * a->n, a->n, &w[i], &o[i]); mx[i] = g_wmax; }
  /* tercera columna: 1 si el patrimonio pasó en algún tick de lo que cabe en 32 bits (solo reglas con límite hipotético) */
  for (int i = 0; i < a->ns; i++) printf("%.0f %d %d\n", w[i], o[i], mx[i] > 0x7fffffffL - 63 * 255);
  return 0;
}

int main(int argc, char **argv) {
  (void)mia_de;
  if (argc >= 2 && !strcmp(argv[1], "lista")) {
    for (int k = 0; k < NMIAS; k++) printf("%s %s\n", MIAS[k].nombre, MIAS[k].arnes);
    return 0;
  }
  if (argc >= 4 && !strcmp(argv[1], "detalle")) return cmd_detalle(argv[2], argv[3]);
  int semilla = 0;
  for (int i = 2; i < argc; i++)
    if (!strcmp(argv[i], "--semilla") && i + 1 < argc) semilla = atoi(argv[++i]);
  if (argc >= 2 && !strcmp(argv[1], "tabla")) return cmd_tabla(semilla);
  if (argc >= 2 && !strcmp(argv[1], "cotas")) return cmd_cotas(semilla);
  fprintf(stderr, "uso: indep34 lista | detalle NOMBRE ARCHIVO.bin | tabla --semilla S | cotas --semilla S\n");
  return 2;
}
