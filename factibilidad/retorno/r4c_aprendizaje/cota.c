/* cota.c: cuánto podría ganar, como máximo, una tabla o una banda que se adapta a la serie.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Herramienta de medición, fuera del arnés y fuera del diseño. Lee los lotes
 * de series de factibilidad/retorno/build/series y lleva su propia
 * contabilidad (las reglas del testbench: caja 10 000, comisión 5, compra
 * recortada a (caja - 5) / p, venta recortada a las acciones que hay, orden
 * ejecutada un tick después). La primera línea de cada familia compara su
 * max_media con la cifra del arnés, que se le pasa con --control.
 *
 * Son oráculos: usan información que el programa de la placa no tiene. Sirven
 * para saber cuánto hay para ganar antes de mirar si el aprendizaje lo logra.
 *
 *   O1  banda de la familia. La mejor banda fija (E, X) de una grilla para
 *       todas las series de la familia. Es lo que lograría un aprendizaje que
 *       identifica la familia al instante y sin error.
 *   O2  tabla de la familia. La tabla de retorno futuro por casilla de
 *       desviación (con y sin el signo del último cambio) promediada sobre
 *       todas las series de la familia, fija, con los mejores umbrales de una
 *       grilla. Es el límite al que tiende la tabla que aprende si la ronda
 *       fuera infinita.
 *   O3  mejor banda de cada serie, elegida después de verla completa, entre
 *       las tres bandas candidatas del frente del algoritmo (activo, max_media
 *       y base) y entre toda la grilla. Es una cota floja: elegir después el
 *       máximo de varios resultados con ruido infla la cifra.
 *
 * A 20 000 ticks cada serie se corre hasta el primer tick en que el precio
 * sale de 21 a 249 (la vista de parada del arnés), para que el rebote de las
 * series de prueba en los límites 1 y 255 no infle las cifras.
 *
 * Uso: cota --series DIR --semilla 0 --largo 2000 [--max N]
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NB 32
#define NZ 3

typedef struct {
  int tipo;                    /* 0 banda, 1 tabla */
  int E, X;                    /* banda */
  int ter;                     /* tabla: 0 sin tercer índice, 1 signo del último cambio */
  unsigned char entra[NZ][NB], sale[NZ][NB];
} Politica;

static int largo_parada(const unsigned char *p, int n) {
  int j = 0;
  while (j < n && p[j] >= 21 && p[j] <= 249) j++;
  j = j < n ? j + 1 : n;
  if (j < 200) j = 200 < n ? 200 : n;
  return j;
}

/* Patrimonio final de una política de posición objetivo (comprar 63 o vender 63 en cada tick). */
static int simular(const unsigned char *p, int n, const Politica *q) {
  int caja = 10000, acc = 0, S = p[0] << 5, pos = 0, objetivo = -1, pant = p[0];
  for (int t = 0; t < n; t++) {
    int pr = p[t];
    if (objetivo == 1) {
      int k = (caja - 5) / pr;
      if (k > 63) k = 63;
      if (k > 0) { caja -= k * pr + 5; acc += k; }
    } else if (objetivo == 0) {
      int k = acc > 63 ? 63 : acc;
      if (k > 0 && caja + k * pr >= 5) { caja += k * pr - 5; acc -= k; }
    }
    int d = pr - pant;
    pant = pr;
    int dev = (pr << 5) - S;
    S += dev >> 5;
    int entra, sale;
    if (q->tipo == 0) { entra = dev < -q->E; sale = dev > q->X; }
    else {
      int z = q->ter ? (d < 0 ? 0 : d > 0 ? 2 : 1) : 0;
      int i = ((dev - pos) >> 5) + NB / 2;
      if (i < 0) i = 0;
      if (i > NB - 1) i = NB - 1;
      entra = q->entra[z][i]; sale = q->sale[z][i];
    }
    if (pos) { if (sale) pos = 0; } else if (entra) pos = 1;
    objetivo = pos;
  }
  return caja + acc * p[n - 1];
}

static const unsigned char *g_d;
static int g_ns, g_n, g_parada;
static int *g_len;

/* Corre la política sobre toda la familia y deja el patrimonio de cada serie. */
static void correr(const Politica *q, float *w) {
#pragma omp parallel for schedule(dynamic, 16)
  for (int i = 0; i < g_ns; i++) w[i] = (float)simular(g_d + (size_t)i * g_n, g_len[i], q);
}

static void pareada(const float *a, const float *b, int n, double *m, double *ee) {
  double s = 0, s2 = 0;
  for (int i = 0; i < n; i++) { double x = (double)a[i] - b[i]; s += x; s2 += x * x; }
  *m = s / n;
  double v = (s2 - n * *m * *m) / (n - 1);
  *ee = v > 0 ? sqrt(v / n) : 0;
}

static double media(const float *a, int n) {
  double s = 0;
  for (int i = 0; i < n; i++) s += a[i];
  return s / n;
}

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

/* Retorno medio a h ticks después de la ejecución, por casilla de desviación y signo del último cambio. */
static void tabla_familia(int h, int ter, double mu[NZ][NB], double cuenta[NZ][NB]) {
  double s[NZ][NB], c[NZ][NB];
  memset(s, 0, sizeof s); memset(c, 0, sizeof c);
  for (int i = 0; i < g_ns; i++) {
    const unsigned char *p = g_d + (size_t)i * g_n;
    int n = g_len[i], S = p[0] << 5, pant = p[0];
    for (int t = 0; t < n; t++) {
      int d = p[t] - pant;
      pant = p[t];
      int dev = (p[t] << 5) - S;
      S += dev >> 5;
      if (t + 1 + h >= n) continue;
      int z = ter ? (d < 0 ? 0 : d > 0 ? 2 : 1) : 0;
      int k = (dev >> 5) + NB / 2;
      if (k < 0) k = 0;
      if (k > NB - 1) k = NB - 1;
      s[z][k] += p[t + 1 + h] - p[t + 1];
      c[z][k] += 1;
    }
  }
  for (int z = 0; z < NZ; z++)
    for (int k = 0; k < NB; k++) { mu[z][k] = c[z][k] > 0 ? s[z][k] / c[z][k] : 0; cuenta[z][k] = c[z][k]; }
}

static const char *opcion(int argc, char **argv, const char *nombre, const char *defecto) {
  for (int i = 1; i + 1 < argc; i++)
    if (!strcmp(argv[i], nombre)) return argv[i + 1];
  return defecto;
}

int main(int argc, char **argv) {
  static const char *FAM[] = {"remuestreo", "modelo", "modelo_vecino", "dos_componentes", "cambio_volatilidad", "paseo",
                              "tendencia", "reversion", "saltos", "cambio_de_caracter", "volatil", "nivel_bajo"};
  static const double PESO[] = {0.5, 0.125, 0.125, 0.125, 0.125, 0, 0, 0, 0, 0, 0, 0};     /* conjunto evidencia */
  static const int ES[] = {32, 48, 64, 80, 96, 112, 128, 160}, XS[] = {-32, -16, 0, 16, 32, 48};
  enum { NF = 12, NE = 8, NX = 6, NBANDAS = NE * NX };
  const char *dir = opcion(argc, argv, "--series", "../build/series");
  int semilla = atoi(opcion(argc, argv, "--semilla", "0")), largo = atoi(opcion(argc, argv, "--largo", "2000"));
  int max = atoi(opcion(argc, argv, "--max", "0"));
  if (semilla != 0) { fprintf(stderr, "este estudio solo usa la semilla 0\n"); return 2; }
  g_parada = largo > 2000;

  printf("Cotas del aprendizaje en vivo. Semilla %d, series de %d ticks%s.\n", semilla, largo,
         g_parada ? ", cada una hasta el primer precio fuera de 21 a 249 (vista de parada)" : "");
  printf("Patrimonio final, diferencia pareada contra max_media (E=96, X=0) con su error estandar entre series.\n");
  printf("O1: mejor banda fija de la familia entre %d (E de 32 a 160, X de -32 a 48). O2: tabla de retorno a h ticks de la\n", NBANDAS);
  printf("familia, fija, con los mejores umbrales (z: con el signo del ultimo cambio). O3: mejor banda de cada serie, elegida\n");
  printf("despues de verla (3: entre activo, max_media y base; todas: entre las %d). O1 y O2 se eligen con las mismas series\n", NBANDAS);
  printf("en que se miden.\n\n");

  double ev_o1 = 0, ev_o2 = 0, ev_o2z = 0, ev_o3 = 0, ev_o3t = 0, ev_mm = 0;
  double ev_o1_v = 0, ev_o2_v = 0, ev_o2z_v = 0, ev_o3_v = 0, ev_o3t_v = 0;
  for (int f = 0; f < NF; f++) {
    char ruta[1024];
    snprintf(ruta, sizeof ruta, "%s/%s_s%d_n%d.bin", dir, FAM[f], semilla, largo);
    unsigned char *d = leer_lote(ruta, &g_ns, &g_n);
    if (!d) { fprintf(stderr, "no se pudo leer %s\n", ruta); return 1; }
    if (max > 0 && g_ns > max) g_ns = max;
    g_d = d;
    g_len = malloc(sizeof(int) * (size_t)g_ns);
    double ticks = 0;
    for (int i = 0; i < g_ns; i++) { g_len[i] = g_parada ? largo_parada(d + (size_t)i * g_n, g_n) : g_n; ticks += g_len[i]; }

    float **W = malloc(sizeof(float *) * NBANDAS);
    Politica q;
    memset(&q, 0, sizeof q);
    int ref = -1, act = -1, bas = -1;
    for (int a = 0; a < NE; a++)
      for (int b = 0; b < NX; b++) {
        int k = a * NX + b;
        W[k] = malloc(sizeof(float) * (size_t)g_ns);
        q.tipo = 0; q.E = ES[a]; q.X = XS[b];
        correr(&q, W[k]);
        if (ES[a] == 96 && XS[b] == 0) ref = k;
        if (ES[a] == 64 && XS[b] == 16) act = k;
        if (ES[a] == 128 && XS[b] == 0) bas = k;
      }
    double mm = media(W[ref], g_ns);
    printf("--- Familia %s: %d series, %.0f ticks de media ---\n", FAM[f], g_ns, ticks / g_ns);
    printf("max_media: media %.1f (control contra el arnes: `resumen --conjunto %s`)\n", mm, FAM[f]);

    /* O1: mejor banda de la familia */
    int mejor = ref;
    for (int k = 0; k < NBANDAS; k++)
      if (media(W[k], g_ns) > media(W[mejor], g_ns)) mejor = k;
    double o1, o1e;
    pareada(W[mejor], W[ref], g_ns, &o1, &o1e);
    printf("O1 banda de la familia: E=%d X=%d, %+.1f +- %.1f\n", ES[mejor / NX], XS[mejor % NX], o1, o1e);
    {
      double m, e;
      pareada(W[act], W[ref], g_ns, &m, &e);
      printf("   activo (E=64, X=16): %+.1f +- %.1f", m, e);
      pareada(W[bas], W[ref], g_ns, &m, &e);
      printf("    base (E=128, X=0): %+.1f +- %.1f\n", m, e);
    }

    /* O3: mejor banda de cada serie, sabida después */
    float *o3 = malloc(sizeof(float) * (size_t)g_ns), *o3t = malloc(sizeof(float) * (size_t)g_ns);
    for (int i = 0; i < g_ns; i++) {
      float a = W[ref][i];
      if (W[act][i] > a) a = W[act][i];
      if (W[bas][i] > a) a = W[bas][i];
      o3[i] = a;
      float t = W[0][i];
      for (int k = 1; k < NBANDAS; k++) if (W[k][i] > t) t = W[k][i];
      o3t[i] = t;
    }
    double m3, e3, m3t, e3t;
    pareada(o3, W[ref], g_ns, &m3, &e3);
    pareada(o3t, W[ref], g_ns, &m3t, &e3t);
    printf("O3 mejor banda de cada serie: entre 3, %+.1f +- %.1f; entre las %d, %+.1f +- %.1f\n", m3, e3, NBANDAS, m3t, e3t);

    /* O2: tabla de la familia */
    static const int HS[] = {8, 16, 32};
    static const double TIN[] = {0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.65, 0.80};
    static const double TOUT[] = {-0.30, -0.20, -0.10, -0.05, 0.0, 0.05, 0.10};
    float *wt = malloc(sizeof(float) * (size_t)g_ns), *wmejor[2];
    double o2[2] = {0, 0}, o2e[2] = {0, 0};
    for (int ter = 0; ter < 2; ter++) {
      double mmejor = -1e30;
      int bh = 0;
      double bti = 0, bto = 0;
      wmejor[ter] = malloc(sizeof(float) * (size_t)g_ns);
      for (int a = 0; a < 3; a++) {
        double mu[NZ][NB], cu[NZ][NB];
        tabla_familia(HS[a], ter, mu, cu);
        for (int i = 0; i < 10; i++)
          for (int j = 0; j < 7; j++) {
            double ti = TIN[i] * sqrt(HS[a] / 16.0), to = TOUT[j] * sqrt(HS[a] / 16.0);
            q.tipo = 1; q.ter = ter;
            for (int z = 0; z < NZ; z++)
              for (int k = 0; k < NB; k++) {
                int hay = cu[ter ? z : 0][k] >= 200;                       /* casillas casi sin datos: no actuar */
                double v = mu[ter ? z : 0][k];
                q.entra[z][k] = (unsigned char)(hay && v > ti);
                q.sale[z][k] = (unsigned char)(hay && v < to);
              }
            correr(&q, wt);
            double m = media(wt, g_ns);
            if (m > mmejor) { mmejor = m; bh = HS[a]; bti = ti; bto = to; memcpy(wmejor[ter], wt, sizeof(float) * (size_t)g_ns); }
          }
      }
      pareada(wmejor[ter], W[ref], g_ns, &o2[ter], &o2e[ter]);
      printf("O2 tabla de la familia%s: h=%d, compra si R > %.2f, vende si R < %.2f, %+.1f +- %.1f\n",
             ter ? " con el signo del ultimo cambio (z)" : "", bh, bti, bto, o2[ter], o2e[ter]);
    }
    {
      double mu[NZ][NB], cu[NZ][NB];
      tabla_familia(16, 0, mu, cu);
      printf("   retorno medio a 16 ticks por casilla de desviacion (unidades de precio), casillas -8 a +7:\n   ");
      for (int k = NB / 2 - 8; k < NB / 2 + 8; k++) printf(" %+.2f", mu[0][k]);
      printf("\n   parte de los ticks en cada casilla (%%):\n   ");
      double tot = 0;
      for (int k = 0; k < NB; k++) tot += cu[0][k];
      for (int k = NB / 2 - 8; k < NB / 2 + 8; k++) printf(" %5.1f", 100 * cu[0][k] / tot);
      printf("\n");
    }
    printf("\n");

    ev_mm += PESO[f] * mm;
    ev_o1 += PESO[f] * o1; ev_o1_v += PESO[f] * PESO[f] * o1e * o1e;
    ev_o2 += PESO[f] * o2[0]; ev_o2_v += PESO[f] * PESO[f] * o2e[0] * o2e[0];
    ev_o2z += PESO[f] * o2[1]; ev_o2z_v += PESO[f] * PESO[f] * o2e[1] * o2e[1];
    ev_o3 += PESO[f] * m3; ev_o3_v += PESO[f] * PESO[f] * e3 * e3;
    ev_o3t += PESO[f] * m3t; ev_o3t_v += PESO[f] * PESO[f] * e3t * e3t;

    for (int k = 0; k < NBANDAS; k++) free(W[k]);
    free(W); free(o3); free(o3t); free(wt); free(wmejor[0]); free(wmejor[1]); free(g_len); free(d);
  }
  printf("=== Conjunto evidencia (remuestreo la mitad, cada familia plausible un octavo) ===\n");
  printf("max_media: media %.1f\n", ev_mm);
  printf("O1 banda de cada familia:              %+.1f +- %.1f\n", ev_o1, sqrt(ev_o1_v));
  printf("O2 tabla de cada familia:              %+.1f +- %.1f\n", ev_o2, sqrt(ev_o2_v));
  printf("O2 tabla de cada familia, con signo:   %+.1f +- %.1f\n", ev_o2z, sqrt(ev_o2z_v));
  printf("O3 mejor de 3 bandas por serie:        %+.1f +- %.1f\n", ev_o3, sqrt(ev_o3_v));
  printf("O3 mejor de %d bandas por serie:       %+.1f +- %.1f\n", NBANDAS, ev_o3t, sqrt(ev_o3t_v));
  return 0;
}
