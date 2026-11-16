/* cota.c: cuánto se podía ganar repartiendo capital entre gestores (cota a posteriori).
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Estudio de retorno 4, parte B. Programa aparte, enlazado con el núcleo del
 * arnés (sin su main.c). Para un conjunto de series calcula:
 *
 *   1. La correlación entre los patrimonios finales de los gestores, serie a serie.
 *   2. El oráculo de selección: en cada serie, el mejor gestor del conjunto,
 *      elegido después de verla. Ningún reparto que elija un gestor por ronda
 *      puede superarlo.
 *   3. La mejor mezcla fija a posteriori: los mismos pesos para todas las
 *      series, elegidos mirando el resultado, con el capital repartido una
 *      vez (el patrimonio de la mezcla es la suma ponderada). En una serie
 *      sola la mejor mezcla es el mejor gestor (el patrimonio es lineal en
 *      los pesos), así que la mezcla solo puede ganar en puntos de torneo y
 *      solo por la forma del puntaje.
 *   4. La persistencia: si el gestor que va ganando en papel en la primera
 *      mitad de la ronda sigue ganando en la segunda. Es lo que necesita
 *      cualquier reparto según el desempeño en papel.
 *
 * Los puntos de torneo son los del arnés (torneo(), campo mixto, G = 10) y
 * las diferencias son pareadas contra max_media.
 *
 *   cota --largo 2000|20000 --semilla 0 [--conjunto evidencia] [--interior]
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "nucleo.h"
#include "torneo.h"

#define NG 8
static const char *GESTOR[NG] = {"cand:max_media", "cand:prudente", "cand:guardia", "cand:kalman", "cand:activo",
                                 "cand:base", "byh:q=63,rep=1", "nada"};
static const char *CORTO[NG] = {"max_media", "prudente", "guardia", "kalman", "activo", "base", "byh", "nada"};
static const int CONJ[4][3] = {{0, 1, 6}, {0, 2, 6}, {0, 3, 4}, {0, 5, 1}};
static const char *CONJ_NOMBRE[4] = {"1: max_media, prudente, byh", "2: max_media, guardia, byh", "3: max_media, kalman, activo",
                                     "4: max_media, base, prudente"};

static Reglas g_reglas = {CAJA0_DEF, COMISION_DEF};

static const char *opcion(int argc, char **argv, const char *nombre, const char *defecto) {
  for (int i = 1; i + 1 < argc; i++)
    if (!strcmp(argv[i], nombre)) return argv[i + 1];
  return defecto;
}

static double correlacion(const double *a, const double *b, int n) {
  double ma = 0, mb = 0, saa = 0, sbb = 0, sab = 0;
  for (int i = 0; i < n; i++) { ma += a[i]; mb += b[i]; }
  ma /= n; mb /= n;
  for (int i = 0; i < n; i++) { saa += (a[i] - ma) * (a[i] - ma); sbb += (b[i] - mb) * (b[i] - mb); sab += (a[i] - ma) * (b[i] - mb); }
  return saa > 0 && sbb > 0 ? sab / sqrt(saa * sbb) : 0;
}

static void fila_puntos(const char *nombre, const PuntosTorneo *p, const double *w, const double *wref, int n) {
  double d, e;
  pareada(w, wref, n, &d, &e);
  Resumen r = resumir(w, n);
  printf("%-34s | %8.0f %+7.0f %5.0f %7.0f | %6.3f %+7.3f %5.3f | %6.3f %+7.3f %5.3f | %+7.3f %5.3f | %+7.3f %5.3f\n", nombre, r.media,
         d, e, r.p5, p->a_media, p->da, p->da_ee, p->b_media, p->db, p->db_ee, p->dca_p5, p->dca_p5_ee, p->dcb_p5, p->dcb_p5_ee);
}

int main(int argc, char **argv) {
  int largo = atoi(opcion(argc, argv, "--largo", "2000")), semilla = atoi(opcion(argc, argv, "--semilla", "0"));
  const char *conjunto = opcion(argc, argv, "--conjunto", "evidencia");
  int interior = 0, G = 10;
  for (int i = 1; i < argc; i++) if (!strcmp(argv[i], "--interior")) interior = 1;
  if (semilla == 2 || semilla == 3) { fprintf(stderr, "las semillas 2 y 3 son reservadas\n"); return 2; }

  Lote *l = conjunto_leer(conjunto, largo, semilla);
  if (!l) { fprintf(stderr, "no se pudo leer el conjunto %s\n", conjunto); return 1; }
  int *sel = malloc(sizeof(int) * (size_t)l->ns), ns = 0;
  for (int i = 0; i < l->ns; i++) {
    const unsigned char *p = l->datos + (size_t)i * l->n;
    int ok = 1;
    if (interior) for (int j = 0; j < l->n; j++) if (p[j] < 21 || p[j] > 249) { ok = 0; break; }
    if (ok) sel[ns++] = i;
  }
  printf("=== Cota a posteriori: conjunto %s, %d ticks, semilla %d, %d series%s ===\n", conjunto, largo, semilla, ns,
         interior ? " interiores (precio siempre entre 21 y 249)" : "");

  /* patrimonio final de cada gestor, y a mitad de ronda */
  Lote mitad = *l;
  mitad.n = l->n / 2;
  mitad.datos = malloc((size_t)l->ns * (size_t)mitad.n);
  for (int i = 0; i < l->ns; i++) memcpy(mitad.datos + (size_t)i * mitad.n, l->datos + (size_t)i * l->n, (size_t)mitad.n);
  double *W[NG], *M[NG], *byh = malloc(sizeof(double) * (size_t)ns);
  Resultado *tmp = malloc(sizeof(Resultado) * (size_t)l->ns);
  for (int k = 0; k < NG; k++) {
    W[k] = malloc(sizeof(double) * (size_t)ns); M[k] = malloc(sizeof(double) * (size_t)ns);
    Resultado *res = resultados(GESTOR[k], l, conjunto, largo, semilla, &g_reglas);
    if (!res || evaluar_lote(GESTOR[k], &mitad, &g_reglas, tmp)) { fprintf(stderr, "no se pudo evaluar %s\n", GESTOR[k]); return 1; }
    for (int j = 0; j < ns; j++) { W[k][j] = res[sel[j]].w; M[k][j] = tmp[sel[j]].w; if (k == 0) byh[j] = res[sel[j]].byh; }
    free(res);
  }

  /* rivales */
  Rivales rv;
  if (rivales_preparar(&rv, &g_reglas)) return 1;
  double **R = malloc(sizeof(double *) * (size_t)rv.nr);
  for (int k = 0; k < rv.nr; k++) {
    Resultado *res = resultados(rv.spec[k], l, conjunto, largo, semilla, &g_reglas);
    if (!res) { fprintf(stderr, "no se pudo evaluar el rival %s\n", rv.spec[k]); return 1; }
    R[k] = malloc(sizeof(double) * (size_t)ns);
    for (int j = 0; j < ns; j++) R[k][j] = res[sel[j]].w;
    free(res);
  }
  int campo = campo_indice("mixto");

  /* 1. correlaciones */
  printf("\n--- 1. Correlacion entre los patrimonios finales de los gestores (Pearson, serie a serie) ---\n%-10s", "");
  for (int b = 0; b < NG - 1; b++) printf(" %9s", CORTO[b]);
  printf("\n");
  for (int a = 0; a < NG - 1; a++) {
    printf("%-10s", CORTO[a]);
    for (int b = 0; b < NG - 1; b++) printf(" %9.3f", correlacion(W[a], W[b], ns));
    printf("\n");
  }
  printf("\nCorrelacion del exceso sobre max_media (W_k - W_max_media) con el de los demas, y media del exceso\n%-10s", "");
  for (int b = 1; b < NG - 1; b++) printf(" %9s", CORTO[b]);
  printf(" %9s\n", "media");
  double *ex[NG];
  for (int k = 0; k < NG; k++) { ex[k] = malloc(sizeof(double) * (size_t)ns); for (int j = 0; j < ns; j++) ex[k][j] = W[k][j] - W[0][j]; }
  for (int a = 1; a < NG - 1; a++) {
    printf("%-10s", CORTO[a]);
    for (int b = 1; b < NG - 1; b++) printf(" %9.3f", correlacion(ex[a], ex[b], ns));
    printf(" %+9.0f\n", resumir(ex[a], ns).media);
  }

  /* 2 y 3. oráculo y mezclas fijas, por conjunto de gestores */
  for (int cj = 0; cj < 4; cj++) {
    const int *g = CONJ[cj];
    enum { PASOS = 8, NM = 45 };
    int nc = 3 + 2 + NM, c = 0, pesos[3 + 2 + NM][3];
    double **X = malloc(sizeof(double *) * (size_t)nc);
    char nombres[3 + 2 + NM][48];
    for (int k = 0; k < 3; k++, c++) { X[c] = W[g[k]]; snprintf(nombres[c], 48, "%s", CORTO[g[k]]); }
    int gana[3] = {0, 0, 0};
    X[c] = malloc(sizeof(double) * (size_t)ns); X[c + 1] = malloc(sizeof(double) * (size_t)ns);
    for (int j = 0; j < ns; j++) {
      int m = 0, p = 0;
      for (int k = 1; k < 3; k++) { if (W[g[k]][j] > W[g[m]][j]) m = k; if (W[g[k]][j] < W[g[p]][j]) p = k; }
      gana[m]++;
      X[c][j] = W[g[m]][j]; X[c + 1][j] = W[g[p]][j];
    }
    snprintf(nombres[c], 48, "ORACULO (mejor de los tres)"); snprintf(nombres[c + 1], 48, "peor de los tres");
    c += 2;
    int primera_mezcla = c;
    for (int a = 0; a <= PASOS; a++)
      for (int b = 0; a + b <= PASOS; b++, c++) {
        int d = PASOS - a - b;
        pesos[c][0] = a; pesos[c][1] = b; pesos[c][2] = d;
        X[c] = malloc(sizeof(double) * (size_t)ns);
        for (int j = 0; j < ns; j++) X[c][j] = (a * W[g[0]][j] + b * W[g[1]][j] + d * W[g[2]][j]) / PASOS;
        snprintf(nombres[c], 48, "mezcla %d/8 %d/8 %d/8", a, b, d);
      }
    PuntosTorneo *pt = malloc(sizeof(PuntosTorneo) * (size_t)nc);
    torneo(X, byh, nc, 0, R, rv.peso[campo], rv.nr, ns, G, 0x4b0f0d0ULL + (uint64_t)largo + (uint64_t)cj, pt);
    printf("\n--- Conjunto de gestores %s ---\n", CONJ_NOMBRE[cj]);
    printf("Mejor gestor de la serie: %s %.1f %%, %s %.1f %%, %s %.1f %%\n", CORTO[g[0]], 100.0 * gana[0] / ns, CORTO[g[1]],
           100.0 * gana[1] / ns, CORTO[g[2]], 100.0 * gana[2] / ns);
    printf("%-34s | %8s %7s %5s %7s | %6s %7s %5s | %6s %7s %5s | %7s %5s | %7s %5s\n", "", "H1 media", "dif", "+-ee", "p5", "H3a",
           "dif", "+-ee", "H3b", "dif", "+-ee", "dp5 a", "+-ee", "dp5 b", "+-ee");
    for (int k = 0; k < 5; k++) fila_puntos(nombres[k], &pt[k], X[k], X[0], ns);
    int ma = primera_mezcla, mb = primera_mezcla, mpa = primera_mezcla, mpb = primera_mezcla;
    for (int k = primera_mezcla; k < nc; k++) {
      if (pt[k].a_media > pt[ma].a_media) ma = k;
      if (pt[k].b_media > pt[mb].b_media) mb = k;
      if (pt[k].ca_p5 > pt[mpa].ca_p5) mpa = k;
      if (pt[k].cb_p5 > pt[mpb].cb_p5) mpb = k;
    }
    char t[96];
    snprintf(t, sizeof t, "mejor H3a: %s", nombres[ma] + 7); fila_puntos(t, &pt[ma], X[ma], X[0], ns);
    snprintf(t, sizeof t, "mejor H3b: %s", nombres[mb] + 7); fila_puntos(t, &pt[mb], X[mb], X[0], ns);
    snprintf(t, sizeof t, "mejor p5 H3a: %s", nombres[mpa] + 7); fila_puntos(t, &pt[mpa], X[mpa], X[0], ns);
    snprintf(t, sizeof t, "mejor p5 H3b: %s", nombres[mpb] + 7); fila_puntos(t, &pt[mpb], X[mpb], X[0], ns);
    printf("Mezclas con max_media en 6/8 y 4/8 (para ver la pendiente):\n");
    for (int k = primera_mezcla; k < nc; k++)
      if (pesos[k][0] == 6 || pesos[k][0] == 4) fila_puntos(nombres[k], &pt[k], X[k], X[0], ns);

    /* 4. persistencia: el que va ganando a mitad de ronda, ¿sigue ganando en la segunda mitad? */
    int lider_sigue = 0, tabla[3][3] = {{0}};
    double *seg_lider = malloc(sizeof(double) * (size_t)ns), *seg_ref = malloc(sizeof(double) * (size_t)ns);
    double *w_lider = malloc(sizeof(double) * (size_t)ns), *vent1 = malloc(sizeof(double) * (size_t)ns),
           *vent2 = malloc(sizeof(double) * (size_t)ns);
    for (int j = 0; j < ns; j++) {
      int l1 = 0, l2 = 0;
      double r2[3];
      for (int k = 0; k < 3; k++) r2[k] = W[g[k]][j] / (M[g[k]][j] > 1 ? M[g[k]][j] : 1);
      for (int k = 1; k < 3; k++) { if (M[g[k]][j] > M[g[l1]][j]) l1 = k; if (r2[k] > r2[l2]) l2 = k; }
      tabla[l1][l2]++;
      lider_sigue += l1 == l2;
      seg_lider[j] = r2[l1]; seg_ref[j] = r2[0];
      w_lider[j] = M[g[0]][j] * r2[l1];            /* seguir a max_media media ronda y después al que iba ganando */
      vent1[j] = M[g[1]][j] - M[g[0]][j]; vent2[j] = r2[1] - r2[0];
    }
    double d, e;
    pareada(seg_lider, seg_ref, ns, &d, &e);
    printf("Persistencia (lider a mitad de ronda contra el mejor de la segunda mitad), filas = lider en la primera mitad:\n");
    for (int a = 0; a < 3; a++)
      printf("  %-10s lidera la 1a mitad en %5.1f %%: en la 2a mitad gana %s %4.1f %%, %s %4.1f %%, %s %4.1f %%\n", CORTO[g[a]],
             100.0 * (tabla[a][0] + tabla[a][1] + tabla[a][2]) / ns, CORTO[g[0]],
             100.0 * tabla[a][0] / (tabla[a][0] + tabla[a][1] + tabla[a][2] + 1e-9), CORTO[g[1]],
             100.0 * tabla[a][1] / (tabla[a][0] + tabla[a][1] + tabla[a][2] + 1e-9), CORTO[g[2]],
             100.0 * tabla[a][2] / (tabla[a][0] + tabla[a][1] + tabla[a][2] + 1e-9));
    printf("  el lider de la 1a mitad es el mejor de la 2a en %.1f %% de las series\n", 100.0 * lider_sigue / ns);
    printf("  rendimiento de la 2a mitad: lider de la 1a %.4f, %s %.4f, diferencia %+.4f +- %.4f\n", resumir(seg_lider, ns).media,
           CORTO[g[0]], resumir(seg_ref, ns).media, d, e);
    printf("  correlacion entre la ventaja de %s sobre %s en la 1a mitad y en la 2a: %+.3f\n", CORTO[g[1]], CORTO[g[0]],
           correlacion(vent1, vent2, ns));
    double *Y[2] = {W[g[0]], w_lider};
    PuntosTorneo p2[2];
    torneo(Y, byh, 2, 0, R, rv.peso[campo], rv.nr, ns, G, 0x51d0ULL + (uint64_t)largo + (uint64_t)cj, p2);
    fila_puntos("seguir al lider desde la mitad", &p2[1], w_lider, W[g[0]], ns);
    free(seg_lider); free(seg_ref); free(w_lider); free(vent1); free(vent2); free(pt);
  }
  return 0;
}
