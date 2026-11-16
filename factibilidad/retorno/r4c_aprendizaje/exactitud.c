/* exactitud.c: exactitud del predictor de patrones de pred.h, por familia de series.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Herramienta de medición. No usa el arnés: lee los lotes de series de
 * factibilidad/retorno/build/series y corre el predictor en línea, igual que
 * lo haría la estrategia, serie por serie y partiendo de cero en cada una.
 *
 * Qué mide. En cada tick t el predictor ve el precio p[t] y predice el signo
 * de R = p[t+1+h] - p[t+1], el cambio que viene después del tick de
 * ejecución. Se cuenta sobre los ticks con R distinto de cero:
 *   base       la mayor de las dos frecuencias (sube o baja): lo que acierta
 *              quien predice siempre lo mismo;
 *   rev        referencia sin aprendizaje: "sube si el precio está bajo la
 *              media exponencial", que es lo que supone la regla de reversión;
 *   pred       el predictor;
 *   fuerte     el predictor solo cuando su contador está saturado;
 *   R medio    cambio medio de precio después de una predicción saturada de
 *              subida y de baja, contando también los R = 0. Es lo que se
 *              ganaría por acción; una ida y vuelta de unas 78 acciones paga
 *              10 de comisión, 0,13 de precio por acción.
 * El error estándar se calcula entre series (cada serie es una observación).
 *
 * Uso: exactitud --series DIR --semilla 0 --largo 2000 [--max 1000]
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pred.h"

typedef struct { const char *nombre; PredCfg c; } Variante;

#define MAXV 96
static Variante g_v[MAXV];
static int g_nv;

static void agregar(const char *nombre, int tipo, int sim, int H, int bits, int lgd, int shd, int h) {
  static char nombres[MAXV][48];
  PredCfg c;
  pred_defecto(&c);
  c.tipo = tipo; c.sim = sim; c.H = H; c.bits = bits; c.lgd = lgd; c.shd = shd; c.h = h;
  const char *mal = pred_validar(&c);
  if (mal) { fprintf(stderr, "%s: %s\n", nombre, mal); exit(2); }
  snprintf(nombres[g_nv], sizeof nombres[0], "%s", nombre);
  g_v[g_nv].nombre = nombres[g_nv]; g_v[g_nv].c = c; g_nv++;
}

static void variantes(void) {
  static const int HS[] = {1, 4, 16};
  for (int a = 0; a < 3; a++) {
    int h = HS[a];
    agregar("historia H=4 2b", 0, 2, 4, 2, 4, 5, h);
    agregar("historia H=8 2b", 0, 2, 8, 2, 4, 5, h);
    agregar("historia H=12 2b", 0, 2, 12, 2, 4, 5, h);
    agregar("historia H=8 3b", 0, 2, 8, 3, 4, 5, h);
    agregar("historia H=8 6b", 0, 2, 8, 6, 4, 5, h);
    agregar("ternaria H=3 2b", 0, 3, 3, 2, 4, 5, h);
    agregar("ternaria H=6 2b", 0, 3, 6, 2, 4, 5, h);
    agregar("gshare H=8 2b", 1, 2, 8, 2, 4, 5, h);
    agregar("gshare H=12 2b", 1, 2, 12, 2, 4, 5, h);
    agregar("gshare H=12 3b", 1, 2, 12, 3, 4, 5, h);
    agregar("gshare H=8 6b", 1, 2, 8, 6, 4, 5, h);
    agregar("gshare tern H=6 2b", 1, 3, 6, 2, 4, 5, h);
    agregar("desviacion 16 2b", 2, 2, 4, 2, 4, 5, h);
    agregar("desviacion 16 3b", 2, 2, 4, 3, 4, 5, h);
    agregar("desviacion 16 6b", 2, 2, 4, 6, 4, 5, h);
    agregar("desviacion 32 2b", 2, 2, 4, 2, 5, 4, h);
    agregar("torneo H=8 2b", 3, 2, 8, 2, 4, 5, h);
    agregar("torneo H=12 2b", 3, 2, 12, 2, 4, 5, h);
    agregar("torneo H=8 3b", 3, 2, 8, 3, 4, 5, h);
    agregar("torneo tern H=6 2b", 3, 3, 6, 2, 4, 5, h);
  }
}

typedef struct {
  double nz, up, ok, okrev, nf, okf, nfu, sru, nfd, srd, nz2, ok2, okrev2;   /* sumas del lote */
  double nrc, src, nrv, srv;                                                  /* zonas de compra y de venta de la regla */
  double s_acc, s_acc2, s_vrev, s_vrev2, s_vbase, s_vbase2;                   /* por serie, para el error */
  int ns;
} Acum;

static unsigned char *leer_lote(const char *ruta, int *ns, int *n) {
  FILE *f = fopen(ruta, "rb");
  if (!f) return NULL;
  int cab[2];
  if (fread(cab, sizeof(int), 2, f) != 2) { fclose(f); return NULL; }
  unsigned char *d = malloc((size_t)cab[0] * (size_t)cab[1]);
  if (fread(d, 1, (size_t)cab[0] * (size_t)cab[1], f) != (size_t)cab[0] * (size_t)cab[1]) { fclose(f); free(d); return NULL; }
  fclose(f);
  *ns = cab[0]; *n = cab[1];
  return d;
}

static void medir(const unsigned char *datos, int ns, int n, const PredCfg *c, Acum *a) {
  memset(a, 0, sizeof *a);
  double nz = 0, up = 0, ok = 0, okrev = 0, nf = 0, okf = 0, nfu = 0, sru = 0, nfd = 0, srd = 0, nz2 = 0, ok2 = 0, okrev2 = 0;
  double nrc = 0, src = 0, nrv = 0, srv = 0;
  double s_acc = 0, s_acc2 = 0, s_vrev = 0, s_vrev2 = 0, s_vbase = 0, s_vbase2 = 0;
  int usadas = 0;
#pragma omp parallel reduction(+ : nz, up, ok, okrev, nf, okf, nfu, sru, nfd, srd, nz2, ok2, okrev2, nrc, src, nrv, srv, s_acc, s_acc2, s_vrev, s_vrev2, s_vbase, s_vbase2, usadas)
  {
    Pred *s = malloc(sizeof *s);
#pragma omp for schedule(dynamic, 16)
    for (int i = 0; i < ns; i++) {
      const unsigned char *p = datos + (size_t)i * (size_t)n;
      memset(s, 0, sizeof *s);
      int S = p[0] << 5;
      double l_nz = 0, l_up = 0, l_ok = 0, l_rev = 0;
      for (int t = 0; t < n; t++) {
        int dev = (p[t] << 5) - S;
        S += dev >> 5;
        int pd = pred_paso(s, c, p[t], dev);
        if (t + 1 + c->h >= n) continue;
        int R = p[t + 1 + c->h] - p[t + 1];
        if (pd == 2) { nfu++; sru += R; }
        if (pd == -2) { nfd++; srd += R; }
        if (dev < -96) { nrc++; src += R; }
        if (dev > 0) { nrv++; srv += R; }
        if (R == 0) continue;
        int arriba = R > 0, acierta = (pd > 0) == arriba, rev = (dev <= 0) == arriba;
        l_nz++; l_up += arriba; l_ok += acierta; l_rev += rev;
        if (pd == 2 || pd == -2) { nf++; okf += acierta; }
        if (t >= n / 2) { nz2++; ok2 += acierta; okrev2 += rev; }
      }
      nz += l_nz; up += l_up; ok += l_ok; okrev += l_rev;
      if (l_nz > 0) {
        double acc = l_ok / l_nz, vrev = (l_ok - l_rev) / l_nz;
        double base = l_up > l_nz - l_up ? l_up / l_nz : 1 - l_up / l_nz;      /* la mejor constante, sabida después */
        s_acc += acc; s_acc2 += acc * acc; s_vrev += vrev; s_vrev2 += vrev * vrev;
        s_vbase += acc - base; s_vbase2 += (acc - base) * (acc - base);
        usadas++;
      }
    }
    free(s);
  }
  a->nz = nz; a->up = up; a->ok = ok; a->okrev = okrev; a->nf = nf; a->okf = okf; a->nfu = nfu; a->sru = sru;
  a->nfd = nfd; a->srd = srd; a->nz2 = nz2; a->ok2 = ok2; a->okrev2 = okrev2;
  a->nrc = nrc; a->src = src; a->nrv = nrv; a->srv = srv;
  a->s_acc = s_acc; a->s_acc2 = s_acc2; a->s_vrev = s_vrev; a->s_vrev2 = s_vrev2; a->s_vbase = s_vbase; a->s_vbase2 = s_vbase2;
  a->ns = usadas;
}

static double ee(double s, double s2, int n) {
  if (n < 2) return 0;
  double m = s / n, v = (s2 - n * m * m) / (n - 1);
  return v > 0 ? sqrt(v / n) : 0;
}

static const char *opcion(int argc, char **argv, const char *nombre, const char *defecto) {
  for (int i = 1; i + 1 < argc; i++)
    if (!strcmp(argv[i], nombre)) return argv[i + 1];
  return defecto;
}

int main(int argc, char **argv) {
  static const char *FAM[] = {"practica", "remuestreo", "modelo", "modelo_vecino", "dos_componentes", "cambio_volatilidad",
                              "paseo", "tendencia", "reversion", "saltos", "cambio_de_caracter", "volatil", "nivel_bajo"};
  static const char *GRUPO[] = {"practica", "remuestreo", "plausibles", "plausibles", "plausibles", "plausibles", "estres",
                                "estres", "estres", "estres", "estres", "estres", "estres"};
  enum { NF = 13 };
  const char *dir = opcion(argc, argv, "--series", "../build/series");
  int semilla = atoi(opcion(argc, argv, "--semilla", "0")), largo = atoi(opcion(argc, argv, "--largo", "2000"));
  int max = atoi(opcion(argc, argv, "--max", "1000"));
  if (semilla != 0) { fprintf(stderr, "este estudio solo usa la semilla 0\n"); return 2; }
  variantes();
  static Acum A[NF][MAXV];
  int ns_f[NF];

  printf("Exactitud del predictor de patrones. Semilla %d, series de %d ticks, hasta %d series por familia.\n", semilla, largo, max);
  printf("Objetivo: signo de R = p[t+1+h] - p[t+1] (el cambio despues del tick de ejecucion). Porcentajes sobre los ticks con R != 0.\n");
  printf("base: la mejor prediccion constante de la familia. rev: sube si el precio esta bajo la media exponencial (sin aprender).\n");
  printf("v.rev y v.base: ventaja del predictor sobre rev y sobre la mejor constante de cada serie (sabida despues), en puntos\n");
  printf("porcentuales, con su error entre series. 2a mitad: exactitud en la segunda mitad de la ronda. fuerte: contador saturado.\n");
  printf("R sube y R baja: cambio medio de precio despues de una prediccion saturada de subida y de baja (umbral util: 0,13).\n\n");

  for (int f = 0; f < NF; f++) {
    char ruta[1024];
    int ns, n;
    if (f == 0) snprintf(ruta, sizeof ruta, "%s/%s", dir, largo == 2000 ? "bloques_n2000.bin" : "practica_n20000.bin");
    else snprintf(ruta, sizeof ruta, "%s/%s_s%d_n%d.bin", dir, FAM[f], semilla, largo);
    unsigned char *d = leer_lote(ruta, &ns, &n);
    if (!d) { fprintf(stderr, "no se pudo leer %s\n", ruta); return 1; }
    if (ns > max) ns = max;
    ns_f[f] = ns;
    for (int v = 0; v < g_nv; v++) medir(d, ns, n, &g_v[v].c, &A[f][v]);
    free(d);
    printf("--- Familia %s (%s): %d series ---\n", FAM[f], GRUPO[f], ns);
    for (int v = 0; v < g_nv; v++)
      if (v == 0 || g_v[v].c.h != g_v[v - 1].c.h) {
        const Acum *a = &A[f][v];
        printf("regla max_media, h = %d: R medio en zona de compra (dev < -96) %+.3f (%.1f%% de los ticks), en zona de venta (dev > 0) %+.3f"
               " (%.1f%%), diferencia %+.3f\n", g_v[v].c.h, a->nrc > 0 ? a->src / a->nrc : 0, 100 * a->nrc / (ns * (double)(n - 1 - g_v[v].c.h)),
               a->nrv > 0 ? a->srv / a->nrv : 0, 100 * a->nrv / (ns * (double)(n - 1 - g_v[v].c.h)),
               (a->nrc > 0 ? a->src / a->nrc : 0) - (a->nrv > 0 ? a->srv / a->nrv : 0));
      }
    printf("%-20s %3s %6s | %6s %6s %6s %6s | %7s %5s %7s %5s | %7s %6s | %6s %6s %7s %7s\n", "predictor", "h", "bits", "base",
           "rev", "pred", "+-ee", "v.rev", "+-ee", "v.base", "+-ee", "2a mitad", "rev 2a", "fuerte", "acierta", "R sube", "R baja");
    for (int v = 0; v < g_nv; v++) {
      const Acum *a = &A[f][v];
      double base = a->up > a->nz - a->up ? a->up / a->nz : 1 - a->up / a->nz;
      printf("%-20s %3d %6d | %6.2f %6.2f %6.2f %6.2f | %+7.2f %5.2f %+7.2f %5.2f | %7.2f %6.2f | %5.1f%% %6.2f %+7.3f %+7.3f\n",
             g_v[v].nombre, g_v[v].c.h, pred_bits_tabla(&g_v[v].c), 100 * base, 100 * a->okrev / a->nz, 100 * a->ok / a->nz,
             100 * ee(a->s_acc, a->s_acc2, a->ns), 100 * a->s_vrev / a->ns, 100 * ee(a->s_vrev, a->s_vrev2, a->ns),
             100 * a->s_vbase / a->ns, 100 * ee(a->s_vbase, a->s_vbase2, a->ns), 100 * a->ok2 / a->nz2, 100 * a->okrev2 / a->nz2,
             100 * a->nf / a->nz, a->nf > 0 ? 100 * a->okf / a->nf : 0, a->nfu > 0 ? a->sru / a->nfu : 0,
             a->nfd > 0 ? a->srd / a->nfd : 0);
    }
    printf("\n");
  }

  /* Resumen por grupo: promedio simple de las familias del grupo. */
  static const char *GR[] = {"practica", "remuestreo", "plausibles", "estres"};
  printf("R medio de la regla max_media (zona de compra menos zona de venta), por grupo y horizonte:\n");
  for (int v = 0; v < g_nv; v++)
    if (v == 0 || g_v[v].c.h != g_v[v - 1].c.h) {
      printf("  h = %2d:", g_v[v].c.h);
      for (int g = 0; g < 4; g++) {
        double x = 0; int k = 0;
        for (int f = 0; f < NF; f++)
          if (!strcmp(GRUPO[f], GR[g])) { const Acum *a = &A[f][v]; x += (a->nrc > 0 ? a->src / a->nrc : 0) - (a->nrv > 0 ? a->srv / a->nrv : 0); k++; }
        printf("  %s %+.3f", GR[g], x / k);
      }
      printf("\n");
    }
  printf("\n");
  printf("=== Resumen por grupo (promedio de las familias de cada grupo) ===\n");
  printf("Para cada grupo: exactitud de la referencia rev, del predictor, ventaja sobre rev con su error, y R medio por accion\n");
  printf("despues de una prediccion saturada de subida menos el de despues de una saturada de baja.\n");
  printf("%-20s %3s %6s", "predictor", "h", "bits");
  for (int g = 0; g < 4; g++) printf(" | %-10s %6s %6s %6s %5s %7s", GR[g], "rev", "pred", "v.rev", "+-ee", "R s-b");
  printf("\n");
  for (int v = 0; v < g_nv; v++) {
    printf("%-20s %3d %6d", g_v[v].nombre, g_v[v].c.h, pred_bits_tabla(&g_v[v].c));
    for (int g = 0; g < 4; g++) {
      double rev = 0, pr = 0, vr = 0, var = 0, rsb = 0;
      int k = 0;
      for (int f = 0; f < NF; f++) {
        if (strcmp(GRUPO[f], GR[g])) continue;
        const Acum *a = &A[f][v];
        double e = ee(a->s_vrev, a->s_vrev2, a->ns);
        rev += a->okrev / a->nz; pr += a->ok / a->nz; vr += a->s_vrev / a->ns; var += e * e;
        rsb += (a->nfu > 0 ? a->sru / a->nfu : 0) - (a->nfd > 0 ? a->srd / a->nfd : 0);
        k++;
      }
      printf(" | %-10s %6.2f %6.2f %+6.2f %5.2f %+7.3f", "", 100 * rev / k, 100 * pr / k, 100 * vr / k, 100 * sqrt(var) / k, rsb / k);
    }
    printf("\n");
  }
  (void)ns_f;
  return 0;
}
