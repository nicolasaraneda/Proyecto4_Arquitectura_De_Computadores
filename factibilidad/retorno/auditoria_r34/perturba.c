/* perturba.c: prueba propia de que las estrategias de los estudios 3 y 4 no usan precios futuros.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Auditoría de los estudios de retorno 3 y 4. No es parte del diseño. Es un
 * programa aparte, enlazado con el núcleo del arnés (sin su main.c) y con los
 * módulos de r3_ejecucion, r4b_fondo, r4c_aprendizaje y r4_final sin tocar.
 *
 * Para cada estrategia de la lista:
 *   1. Repetición: una ronda, otra ronda con otra serie, y la primera de
 *      nuevo. Las decisiones deben ser idénticas (no queda nada entre rondas:
 *      ni tablas aprendidas, ni pesos, ni cuentas en papel).
 *   2. Futuro cambiado: para muchos ticks de corte T, incluidos los bordes de
 *      las ventanas de 512 ticks del fondo y los del anillo de la tabla, se
 *      cambia la serie desde T en adelante y se exige que los bytes que la
 *      maestra lee hasta el tick T (los que se decidieron con precios
 *      anteriores a T) no cambien. Tres formas de cambiarla: precios al azar
 *      entre 1 y 255, la misma serie con un paseo lento sumado (la serie
 *      sigue pareciéndose a sí misma) y solo el precio del tick T (el de
 *      ejecución de la última decisión que se compara).
 *   3. Serie cortada en T: las decisiones hasta T no cambian (no conoce el largo).
 *   4. Martingala: series sin sesgo (paseo simétrico con barreras absorbentes)
 *      y sin comisión. El patrimonio de una estrategia que no ve el futuro es
 *      una martingala, así que la media del patrimonio final tiene que ser
 *      10 000 dentro del error. Esta prueba no depende de comparar decisiones.
 *
 * Controles negativos, para saber que la prueba detecta lo que busca:
 *   tramposa        compra si el precio sube después de la ejecución: compara p[t+2] con p[t+1],
 *                   que lee por una fuga puesta a propósito.
 *   tramposa_lenta  la regla max_media, pero con un umbral que se ajusta con un acumulador
 *                   de tasa 2^-12 alimentado con el retorno FUTURO a 16 ticks: la misma forma
 *                   de la tabla que aprende, con la fuga en el ajuste y no en la decisión.
 *   memoriosa       no reinicia un contador entre rondas.
 * Las tres deben fallar.
 *
 * Uso: perturba [--series N] [--mart N]      (se corre desde factibilidad/retorno/auditoria_r34)
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "nucleo.h"

/* ---- Controles negativos ------------------------------------------------------------------- */

static const unsigned char *g_fuga;      /* la serie completa: solo la miran las tramposas */
static int g_fuga_n;

typedef struct { int t; } EstT;
static void t_iniciar(void *e, const void *c, const Reglas *r, uint64_t s) { (void)e; (void)c; (void)r; (void)s; }
static int t_decidir(void *estado, int p, const Cuenta *propia) {
  EstT *s = estado;
  (void)propia;
  int ejec = g_fuga && s->t + 1 < g_fuga_n ? g_fuga[s->t + 1] : p;
  int sig = g_fuga && s->t + 2 < g_fuga_n ? g_fuga[s->t + 2] : ejec;
  s->t++;
  return sig > ejec ? COMPRAR_63 : VENDER_63;
}
static const Estrategia tramposa = {"tramposa", "control negativo: mira los dos precios siguientes", 1, sizeof(EstT), NULL, t_iniciar, t_decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(tramposa)

typedef struct { int t, ini, S, A, pos; } EstL;
static int l_decidir(void *estado, int p, const Cuenta *propia) {
  EstL *s = estado;
  (void)propia;
  if (!s->ini) { s->ini = 1; s->S = p << 5; }
  int dev = (p << 5) - s->S;
  s->S += dev >> 5;
  /* ajuste con el retorno futuro a 16 ticks desde la ejecución: p[t+17] - p[t+1] */
  if (g_fuga && s->t + 17 < g_fuga_n) s->A += ((g_fuga[s->t + 17] - g_fuga[s->t + 1]) << 10) - (s->A >> 12);
  int E = 96 - (s->A >> 17);             /* el umbral se corre de a poco */
  if (E < 32) E = 32;
  if (E > 160) E = 160;
  if (s->pos) { if (dev > 0) s->pos = 0; } else if (dev < -E) s->pos = 1;
  s->t++;
  return s->pos ? COMPRAR_63 : VENDER_63;
}
static const Estrategia tramposa_lenta = {"tramposa_lenta", "control negativo: aprende con retornos futuros", 1, sizeof(EstL), NULL, t_iniciar, l_decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(tramposa_lenta)

static int g_memoria;                    /* no se reinicia entre rondas */
typedef struct { int ini, S, pos; } EstM;
static int m_decidir(void *estado, int p, const Cuenta *propia) {
  EstM *s = estado;
  (void)propia;
  if (!s->ini) { s->ini = 1; s->S = p << 5; }
  int dev = (p << 5) - s->S;
  s->S += dev >> 5;
  g_memoria++;
  int E = 96 + ((g_memoria / 1000) % 4) * 32;
  if (s->pos) { if (dev > 0) s->pos = 0; } else if (dev < -E) s->pos = 1;
  return s->pos ? COMPRAR_63 : VENDER_63;
}
static const Estrategia memoriosa = {"memoriosa", "control negativo: guarda estado entre rondas", 1, sizeof(EstM), NULL, t_iniciar, m_decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(memoriosa)

/* ---- Lista de estrategias -------------------------------------------------------------------- */

static const char *SPECS[] = {
  /* referencia y candidatas finales del estudio 3 */
  "cand:max_media", "ejec:m=8", "ejec:m=8,m2=24,e2=32",
  /* otras familias del estudio 3 con contabilidad */
  "ejec:K=2", "ejec:F=12", "ejec:eo=16", "ejec:ec=1,eo=16", "ejec:xc=1,xo=16", "ejec:nr=1", "ejec:nt=3", "ejec:mv=8",
  /* fondo: configuraciones con nombre y las formas de repartir */
  "cand:fondo_rec", "cand:fondo_rec_ant", "cand:fondo_ancla", "cand:fondo_min", "cand:fondo_min_ant",
  "fondo:c=1,m=1,v=0,mg=6", "fondo:c=3,m=1,v=9,mg=6", "fondo:c=2,m=1,v=6,mg=8", "fondo:c=5,m=1,v=6,mg=6,pp=1",
  "fondo:c=3,w0=6,w1=5,w2=5,m=2,v=6,mg=8,d=6,ps=2", "fondo:c=1,w0=10,w1=2,w2=4,m=2,v=9,mg=6,d=4,fj=4,b=1",
  "fondo:c=3,w0=6,w1=5,w2=5,vt=11,vs=0", "fondo:c=3,w0=8,w1=4,w2=4,b=0",
  /* aprendizaje: alias y variantes que aprenden rápido (ejercitan el ajuste dentro de la serie) */
  "cand:aprendiz", "cand:aprendiz_rapido", "cand:espera", "cand:aprendiz_patron", "cand:aprendiz_puro",
  "tabla:ka=6,h=16", "tabla:ka=8,h=4", "tabla:ka=6,h=32", "tabla:ka=8,h=126", "tabla:modo=1,bits=4,h=16",
  "tabla:banda=1,ka=8,h=16,lim=2", "tabla:ter=1,ka=8,h=8", "tabla:ter=2,ka=8,h=16", "tabla:filas=2,ka=8,h=16",
  "tabla:ka=6,h=16,dir=1", "patron:tipo=0,H=8,sim=2,bits=2,h=1", "patron:tipo=3,H=12,sim=2,bits=2,h=16",
  "mm_patron:tipo=0,H=6,sim=3,bits=2,h=4,fe=1,fs=1,maxp=4",
  /* cierre: las 11 configuraciones propias y dos con aprendizaje rápido dentro del fondo */
  "cand:ejec_a", "cand:ejec_b", "cand:espera_e", "cand:rec_e", "cand:min_e", "cand:completo", "cand:completo_s",
  "cand:completo_esp", "cand:completo_ap", "cand:completo_ancla", "cand:completo_min",
  "fondoc:c=5,x=cand:aprendiz_rapido,w0=4,w1=4,w2=4,w3=4,m=2,v=6,mg=7,d=4,pp=1,vt=8,em=8",
  "fondoc:c=3,x=tabla:ka~6/h~16,w0=4,w1=4,w2=4,w3=4,m=1,v=6,mg=8,b=1,em=8",
  "filtro:x=tabla:ka~6/h~16,m=8",
  /* controles negativos: deben fallar */
  "tramposa", "tramposa_lenta", "memoriosa",
};
#define NSPECS ((int)(sizeof SPECS / sizeof SPECS[0]))

/* ---- Series de prueba --------------------------------------------------------------------------- */

#define N 8192

static void serie_reversion(unsigned char *p, int n, Azar *a) {
  double nivel = 60 + 130 * azar_u01(a), tr = 0;
  for (int t = 0; t < n; t++) {
    nivel += 0.4 * (azar_u01(a) + azar_u01(a) + azar_u01(a) - 1.5) * 2;
    tr = 0.96 * tr + 1.6 * (azar_u01(a) + azar_u01(a) + azar_u01(a) - 1.5);
    if (azar_entero(a, 3000) == 0) nivel += 30 * (azar_u01(a) - 0.5);
    if (nivel < 25) nivel = 25;
    if (nivel > 230) nivel = 230;
    double x = nivel + tr;
    if (x < 1) x = 1;
    if (x > 255) x = 255;
    p[t] = (unsigned char)(x + 0.5);
  }
}

static const Reglas REGLAS = {CAJA0_DEF, COMISION_DEF};

static int g_cortes[96], g_ncortes;

static void armar_cortes(Azar *a) {
  static const int FIJOS[] = {1, 2, 3, 16, 17, 18, 19, 33, 34, 63, 64, 65, 127, 128, 129, 130, 255, 256, 257, 511, 512, 513, 514,
                              529, 530, 1023, 1024, 1025, 1535, 1536, 1537, 2047, 2048, 2049, 4095, 4096, 4097, 8190, 8191};
  g_ncortes = 0;
  for (size_t k = 0; k < sizeof FIJOS / sizeof FIJOS[0]; k++) g_cortes[g_ncortes++] = FIJOS[k];
  for (int k = 0; k < 24; k++) g_cortes[g_ncortes++] = 20 + azar_entero(a, N - 40);
}

typedef struct { int repeticion, azar, lento, ejecucion, corte, pruebas; } Fallas;

static Fallas perturbar(const char *spec, int nseries) {
  Fallas f = {0, 0, 0, 0, 0, 0};
  char error[256];
  Instancia *inst = instancia_crear(spec, error, sizeof error);
  if (!inst) { fprintf(stderr, "%s: %s\n", spec, error); exit(2); }
  static unsigned char p[N], q[N], d0[N], d1[N];
  Azar a;
  azar_sembrar(&a, 20261115);
  for (int s = 0; s < nseries; s++) {
    uint64_t sem = semilla_serie(instancia_spec(inst), s);
    serie_reversion(p, N, &a);
    g_fuga = p; g_fuga_n = N;
    correr_serie(inst, p, N, &REGLAS, sem, 0, d0);
    /* 1. repetición después de otra ronda */
    serie_reversion(q, N, &a);
    g_fuga = q;
    correr_serie(inst, q, N, &REGLAS, sem + 1, 0, d1);
    g_fuga = p;
    correr_serie(inst, p, N, &REGLAS, sem, 0, d1);
    f.repeticion += memcmp(d0, d1, N) != 0; f.pruebas++;
    for (int k = 0; k < g_ncortes; k++) {
      int T = g_cortes[k];
      size_t cmp = (size_t)T + 1 > N ? N : (size_t)T + 1;
      /* 2a. futuro al azar */
      memcpy(q, p, N);
      for (int t = T; t < N; t++) q[t] = (unsigned char)(1 + azar_entero(&a, 255));
      g_fuga = q;
      correr_serie(inst, q, N, &REGLAS, sem, 0, d1);
      f.azar += memcmp(d0, d1, cmp) != 0; f.pruebas++;
      /* 2b. futuro parecido: la misma serie con un paseo lento sumado */
      memcpy(q, p, N);
      int corr = azar_entero(&a, 2) ? 1 : -1;
      for (int t = T; t < N; t++) {
        if (azar_entero(&a, 40) == 0) corr += azar_entero(&a, 3) - 1;
        int x = p[t] + corr;
        q[t] = (unsigned char)(x < 1 ? 1 : x > 255 ? 255 : x);
      }
      g_fuga = q;
      correr_serie(inst, q, N, &REGLAS, sem, 0, d1);
      f.lento += memcmp(d0, d1, cmp) != 0; f.pruebas++;
      /* 2c. solo el precio de ejecución */
      memcpy(q, p, N);
      { int x = p[T < N ? T : N - 1] + (azar_entero(&a, 2) ? 3 : -3); q[T < N ? T : N - 1] = (unsigned char)(x < 1 ? 1 : x > 255 ? 255 : x); }
      g_fuga = q;
      correr_serie(inst, q, N, &REGLAS, sem, 0, d1);
      f.ejecucion += memcmp(d0, d1, cmp) != 0; f.pruebas++;
      /* 3. serie cortada */
      g_fuga = p; g_fuga_n = T;
      correr_serie(inst, p, T, &REGLAS, sem, 0, d1);
      g_fuga_n = N;
      f.corte += memcmp(d0, d1, (size_t)T) != 0; f.pruebas++;
    }
  }
  g_fuga = NULL;
  instancia_destruir(inst);
  return f;
}

/* ---- Martingala ------------------------------------------------------------------------------------ */

#define NM 2000

static void martingala(const char *spec, int nseries, double *media, double *ee) {
  char error[256];
  Instancia *inst = instancia_crear(spec, error, sizeof error);
  if (!inst) { fprintf(stderr, "%s: %s\n", spec, error); exit(2); }
  const Reglas sin = {CAJA0_DEF, 0};
  static unsigned char p[NM];
  Azar a;
  double s1 = 0, s2 = 0;
  azar_sembrar(&a, 777);                 /* las mismas series para todas las estrategias */
  for (int s = 0; s < nseries; s++) {
    int x = 128;
    for (int t = 0; t < NM; t++) {
      if (x > 1 && x < 255) { int u = azar_entero(&a, 4); x += u == 0 ? -1 : u == 1 ? 1 : 0; }   /* barreras absorbentes */
      p[t] = (unsigned char)x;
    }
    g_fuga = p; g_fuga_n = NM;
    Resultado r = correr_serie(inst, p, NM, &sin, semilla_serie(instancia_spec(inst), s), 0, NULL);
    double d = r.w - CAJA0_DEF;
    s1 += d; s2 += d * d;
  }
  g_fuga = NULL;
  instancia_destruir(inst);
  *media = s1 / nseries;
  *ee = sqrt((s2 / nseries - *media * *media) / (nseries - 1));
}

int main(int argc, char **argv) {
  int nseries = 6, nmart = 4000;
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--series") && i + 1 < argc) nseries = atoi(argv[++i]);
    if (!strcmp(argv[i], "--mart") && i + 1 < argc) nmart = atoi(argv[++i]);
  }
  Azar a;
  azar_sembrar(&a, 4242);
  armar_cortes(&a);
  printf("Perturbacion propia de los precios futuros: %d estrategias, %d series de %d ticks, %d cortes por serie\n", NSPECS, nseries, N, g_ncortes);
  printf("Fallas por prueba: repeticion tras otra ronda, futuro al azar, futuro parecido, solo precio de ejecucion, serie cortada.\n");
  printf("Martingala: %d series de %d ticks sin sesgo y sin comision; media del patrimonio final menos 10000 y su error.\n\n", nmart, NM);
  printf("%-88s %5s %5s %5s %5s %5s %7s  %10s %8s %7s  %s\n", "estrategia", "rep", "azar", "lento", "ejec", "corte", "pruebas", "mart", "ee", "z", "juicio");
  int mal = 0, controles = 0, total = 0;
  double zmax = 0;
  for (int k = 0; k < NSPECS; k++) {
    int control = !strncmp(SPECS[k], "tramposa", 8) || !strcmp(SPECS[k], "memoriosa");
    Fallas f = perturbar(SPECS[k], nseries);
    double m, e;
    martingala(SPECS[k], nmart, &m, &e);
    double z = e > 0 ? m / e : 0;
    int fallas = f.repeticion + f.azar + f.lento + f.ejecucion + f.corte;
    int falla_mart = fabs(z) > 4.0;
    const char *juicio;
    if (control) { juicio = fallas || falla_mart ? "falla (control: correcto)" : "NO DETECTADA"; controles += fallas || falla_mart; if (!(fallas || falla_mart)) mal++; }
    else { juicio = fallas || falla_mart ? "FALLA" : "ok"; mal += fallas || falla_mart; total += f.pruebas; if (fabs(z) > zmax) zmax = fabs(z); }
    printf("%-88s %5d %5d %5d %5d %5d %7d  %+10.2f %8.2f %+7.2f  %s\n", SPECS[k], f.repeticion, f.azar, f.lento, f.ejecucion, f.corte, f.pruebas, m, e, z, juicio);
    fflush(stdout);
  }
  printf("\n%s: %d estrategias auditadas, %d comparaciones de decisiones, mayor |z| de martingala %.2f, %d de 3 controles negativos detectados\n",
         mal ? "FAIL" : "PASS", NSPECS - 3, total, zmax, controles);
  return mal ? 1 : 0;
}
