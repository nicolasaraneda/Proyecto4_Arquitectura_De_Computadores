/* torneo_b.c: copia de factibilidad/retorno/nucleo/torneo.c con un campo más, "variados"
 * (tarea B del 17/11, docs/generador_b.md): todos los rivales son reversiones, cada una
 * de las 25 parametrizaciones de la clase con la misma probabilidad. Sin pedirlo, la
 * salida es la del original.
 *
 * Texto original:
 *
 * torneo.c: puntajes, torneo simulado contra rivales y caché de resultados.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Ver torneo.h para las hipótesis. Detalles de la simulación:
 *
 *   Una ronda.   Para cada serie se sortean FIELDS campos de G rivales y se
 *                calculan los puntos de cada candidato. La media usa el
 *                promedio por serie, y su error estándar se calcula entre
 *                series (los campos sorteados sobre una misma serie no son
 *                muestras independientes).
 *   Competencia. Las series se reparten al azar en tríos sin repetir; cada
 *                trío es una competencia con un mismo campo en sus tres
 *                rondas. Se repite REPS veces con otro reparto y otros campos.
 *                El percentil 5 es el promedio de los REPS percentiles. Su
 *                error se estima por remuestreo de las competencias dentro de
 *                cada repetición y se promedia: es conservador, porque no
 *                descuenta lo que gana el promedio entre repeticiones.
 *
 * Todos los candidatos se enfrentan a los mismos campos y a las mismas
 * series, así que las diferencias entre dos candidatos son pareadas.
 */
#include "torneo.h"

#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define FIELDS 6          /* campos sorteados por serie para el puntaje de una ronda */
#define REPS 6            /* repartos en tríos para el puntaje de una competencia */
#define BOOT 100          /* remuestreos para el error del percentil 5 */

const char *CAMPOS[N_CAMPOS] = {"ingenuo", "mixto", "fuerte"};

/* Campos más duros, agregados en el estudio de cierre (r4_final). Son los
 * cuatro de la auditoría (auditoria/indep.c):
 *   racional    cualquier rival que no pierde en la serie de práctica completa
 *               y que no opera al azar, todos con la misma probabilidad;
 *   reversores  todos los rivales traen una de las tres mejores reversiones;
 *   fijos2      el campo mixto, pero dos de los G rivales son siempre la regla
 *               base y max_media;
 *   fijos3      lo mismo con tres: además la suma móvil de 64.
 * La tabla de pesos sigue teniendo N_CAMPOS filas. Un campo de estos se pide
 * por nombre (--campo racional, o la variable RETORNO_CAMPO) y en esa corrida
 * ocupa el lugar del mixto: campo_indice devuelve 1, CAMPOS[1] pasa a llamarse
 * como el campo pedido y rivales_preparar llena esa fila con sus pesos. Sin
 * pedirlos, nada cambia: las salidas con ingenuo, mixto y fuerte son las de
 * antes, byte a byte. */
#define N_EXTRAS 5
static const char *EXTRAS[N_EXTRAS] = {"racional", "reversores", "fijos2", "fijos3", "variados"};
static const char *FIJOS[3] = {"reversion:k=5,a=4,b=0", "reversion:k=5,a=3,b=0", "reversion:tipo=1,n=64,a=4,b=1"};
static int extra_pedido;                  /* 0 ninguno; 1 + índice en EXTRAS */
static const double *extra_peso;          /* la fila de pesos que ocupa el campo pedido */
static int extra_nfijos, extra_fijo[3];   /* rivales que están siempre en el campo (fijos2 y fijos3) */

int campo_indice(const char *nombre) {
  for (int k = 0; k < N_CAMPOS; k++)
    if (!strcmp(CAMPOS[k], nombre)) return k;
  for (int e = 0; e < N_EXTRAS; e++)
    if (!strcmp(EXTRAS[e], nombre)) { extra_pedido = 1 + e; CAMPOS[1] = EXTRAS[e]; return 1; }
  return -1;
}

/* ---- Rivales y composición del campo ------------------------------------------------------ */
/* ingenuo: cada grupo elige una de las seis clases con la misma probabilidad
 *          y cualquier parametrización de la clase.
 * mixto:   la clase se elige igual, pero dentro de la clase cada grupo se
 *          queda con una de las tres parametrizaciones que más ganan en la
 *          serie de práctica completa (es lo que haría al ajustar con ella).
 * fuerte:  como mixto, pero el 60 % de los grupos llega a una reversión
 *          ajustada: reversión 0,60, comprar y mantener 0,12, cruce 0,08,
 *          momentum 0,08, no operar 0,06 y azar 0,06. */

static const struct { const char *clase; double fuerte; } CLASES[] = {
  {"cruce", 0.08}, {"momentum", 0.08}, {"comprar_y_mantener", 0.12}, {"no_operar", 0.06}, {"reversion", 0.60}, {"azar", 0.06}};
#define N_CLASES ((int)(sizeof CLASES / sizeof CLASES[0]))

int rivales_preparar(Rivales *rv, const Reglas *r) {
  memset(rv, 0, sizeof *rv);
  rv->nr = nucleo_nrivales();
  Lote *practica = conjunto_leer("practica", 20000, 0);
  if (!practica) return 1;
  for (int k = 0; k < rv->nr; k++) {
    Resultado res;
    rv->spec[k] = nucleo_rival_spec(k);
    rv->clase[k] = nucleo_rival_clase(k);
    if (evaluar_lote(rv->spec[k], practica, r, &res)) { lote_liberar(practica); return 1; }
    rv->practica[k] = res.w;
  }
  lote_liberar(practica);
  for (int c = 0; c < N_CLASES; c++) {
    int miembros[MAX_R], n = 0;
    for (int k = 0; k < rv->nr; k++)
      if (!strcmp(rv->clase[k], CLASES[c].clase)) miembros[n++] = k;
    if (n == 0) { fprintf(stderr, "clase de rivales vacia: %s\n", CLASES[c].clase); return 1; }
    for (int a = 0; a < n; a++)                    /* de mayor a menor patrimonio en la práctica */
      for (int b = a + 1; b < n; b++)
        if (rv->practica[miembros[b]] > rv->practica[miembros[a]]) { int t = miembros[a]; miembros[a] = miembros[b]; miembros[b] = t; }
    int mejores = n < 3 ? n : 3;
    for (int a = 0; a < n; a++) {
      rv->peso[0][miembros[a]] = 1.0 / N_CLASES / n;
      rv->peso[1][miembros[a]] = a < mejores ? 1.0 / N_CLASES / mejores : 0.0;
      rv->peso[2][miembros[a]] = a < mejores ? CLASES[c].fuerte / mejores : 0.0;
    }
  }
  /* campo pedido por nombre (ver campo_indice): reemplaza la fila del mixto */
  const char *pedido = getenv("RETORNO_CAMPO");
  if (!extra_pedido && pedido && *pedido && campo_indice(pedido) < 0) {
    fprintf(stderr, "RETORNO_CAMPO: campo desconocido: %s\n", pedido); return 1;
  }
  extra_peso = NULL; extra_nfijos = 0;
  if (extra_pedido) {
    double suma = 0;
    extra_peso = rv->peso[1];
    for (int k = 0; k < rv->nr; k++) {
      double mixto = rv->peso[1][k], p = mixto;                        /* fijos2 y fijos3 sortean el resto como el mixto */
      if (extra_pedido == 1) p = rv->practica[k] >= r->caja0 && strcmp(rv->clase[k], "azar") ? 1.0 : 0.0;
      if (extra_pedido == 2) p = mixto > 0 && !strcmp(rv->clase[k], "reversion") ? 1.0 : 0.0;
      if (extra_pedido == 5) p = !strcmp(rv->clase[k], "reversion") ? 1.0 : 0.0;   /* variados */
      rv->peso[1][k] = p; suma += p;
    }
    if (suma <= 0) { fprintf(stderr, "campo %s: no queda ningun rival\n", CAMPOS[1]); return 1; }
    for (int k = 0; k < rv->nr; k++) rv->peso[1][k] /= suma;
    for (int f = 0; f < (extra_pedido == 3 ? 2 : extra_pedido == 4 ? 3 : 0); f++) {
      int k = 0;
      while (k < rv->nr && strcmp(rv->spec[k], FIJOS[f])) k++;
      if (k == rv->nr) { fprintf(stderr, "campo %s: falta el rival %s\n", CAMPOS[1], FIJOS[f]); return 1; }
      extra_fijo[extra_nfijos++] = k;
    }
  }
  return 0;
}

/* ---- Puntajes --------------------------------------------------------------------------------- */

double puntos_patrimonio(double w, const double *x, int G) {
  double lo = w, hi = w;
  for (int g = 0; g < G; g++) { if (x[g] < lo) lo = x[g]; if (x[g] > hi) hi = x[g]; }
  return hi > lo ? 2.0 * (w - lo) / (hi - lo) : 1.0;
}

double puntos_puesto(double w, const double *x, int G) {
  int abajo = 0, igual = 0;
  for (int g = 0; g < G; g++) { abajo += x[g] < w; igual += x[g] == w; }
  return 2.0 * (abajo + 0.5 * igual) / G;
}

/* ---- Utilidades ---------------------------------------------------------------------------------- */

static double seleccionar(double *v, int n, int k) {      /* k-ésimo menor; desordena v */
  int lo = 0, hi = n - 1;
  while (lo < hi) {
    double piv = v[(lo + hi) / 2];
    int i = lo, j = hi;
    while (i <= j) {
      while (v[i] < piv) i++;
      while (v[j] > piv) j--;
      if (i <= j) { double t = v[i]; v[i] = v[j]; v[j] = t; i++; j--; }
    }
    if (k <= j) hi = j; else if (k >= i) lo = i; else return v[k];
  }
  return v[k];
}

static double p5_de(const double *x, int n, double *tmp) {
  int k = (int)(0.05 * n);
  memcpy(tmp, x, sizeof(double) * (size_t)n);
  return seleccionar(tmp, n, k > n - 1 ? n - 1 : k);
}

static double p5_indices(const double *x, const int *idx, int n, double *tmp) {
  int k = (int)(0.05 * n);
  for (int i = 0; i < n; i++) tmp[i] = x[idx[i]];
  return seleccionar(tmp, n, k > n - 1 ? n - 1 : k);
}

static void acumulada(const double *peso, int nr, double *acum) {
  double s = 0;
  for (int k = 0; k < nr; k++) { s += peso[k]; acum[k] = s; }
  for (int k = 0; k < nr; k++) acum[k] /= s;
}

static int sortear(const double *acum, int nr, Azar *a) {
  double u = azar_u01(a);
  int lo = 0, hi = nr - 1;
  while (lo < hi) { int m = (lo + hi) / 2; if (acum[m] > u) hi = m; else lo = m + 1; }
  return lo;
}

static void permutar(int *perm, int n, Azar *a) {
  for (int i = 0; i < n; i++) perm[i] = i;
  for (int i = n - 1; i > 0; i--) { int j = azar_entero(a, i + 1), t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
}

static double **matriz(int f, int c) {
  double **m = malloc(sizeof(double *) * (size_t)f);
  for (int i = 0; i < f; i++) m[i] = calloc((size_t)c, sizeof(double));
  return m;
}

static void liberar_matriz(double **m, int f) {
  for (int i = 0; i < f; i++) free(m[i]);
  free(m);
}

/* Error estándar del percentil 5 de cada fila de x[nc][n] y de su diferencia
 * con la fila `ref`, por remuestreo de las n columnas. Suma en ee[] y dee[]. */
static void error_p5(double **x, int nc, int ref, int n, Azar *a, double *ee, double *dee) {
  int *idx = malloc(sizeof(int) * (size_t)n);
  double *tmp = malloc(sizeof(double) * (size_t)n);
  double *s = calloc((size_t)nc, sizeof(double)), *s2 = calloc((size_t)nc, sizeof(double));
  double *d = calloc((size_t)nc, sizeof(double)), *d2 = calloc((size_t)nc, sizeof(double));
  for (int b = 0; b < BOOT; b++) {
    for (int i = 0; i < n; i++) idx[i] = azar_entero(a, n);
    double pref = p5_indices(x[ref], idx, n, tmp);
    for (int c = 0; c < nc; c++) {
      double p = c == ref ? pref : p5_indices(x[c], idx, n, tmp);
      s[c] += p; s2[c] += p * p; d[c] += p - pref; d2[c] += (p - pref) * (p - pref);
    }
  }
  for (int c = 0; c < nc; c++) {
    double v = s2[c] / BOOT - (s[c] / BOOT) * (s[c] / BOOT), dv = d2[c] / BOOT - (d[c] / BOOT) * (d[c] / BOOT);
    ee[c] += sqrt(v > 0 ? v : 0);
    dee[c] += sqrt(dv > 0 ? dv : 0);
  }
  free(idx); free(tmp); free(s); free(s2); free(d); free(d2);
}

/* ---- Torneo ---------------------------------------------------------------------------------------- */

void torneo(double **W, const double *byh, int nc, int ref, double **R, const double *peso, int nr, int ns, int G,
            uint64_t semilla, PuntosTorneo *o) {
  Azar az;
  double acum[MAX_R], x[64], xs[64], xr[64];
  int campo[64];
  azar_sembrar(&az, semilla);
  acumulada(peso, nr, acum);
  memset(o, 0, sizeof(PuntosTorneo) * (size_t)nc);
  if (G > 64) G = 64;
  /* con fijos2 y fijos3 los primeros nf rivales del campo no se sortean; en los demás campos nf = 0 */
  int nf = peso == extra_peso ? extra_nfijos : 0;
  if (nf > G) nf = G;

  /* --- una ronda --- */
  double **sa = matriz(nc, ns), **sb = matriz(nc, ns);              /* promedio por serie */
  double **ta = matriz(nc, ns * FIELDS), **tb = matriz(nc, ns * FIELDS);   /* todas las muestras */
  double *tmp = malloc(sizeof(double) * (size_t)ns * FIELDS);
  for (int i = 0; i < ns; i++)
    for (int m = 0; m < FIELDS; m++) {
      for (int g = 0; g < G; g++) x[g] = R[g < nf ? extra_fijo[g] : sortear(acum, nr, &az)][i];
      for (int c = 0; c < nc; c++) {
        double pa = puntos_patrimonio(W[c][i], x, G), pb = puntos_puesto(W[c][i], x, G);
        ta[c][i * FIELDS + m] = pa; tb[c][i * FIELDS + m] = pb;
        sa[c][i] += pa / FIELDS; sb[c][i] += pb / FIELDS;
      }
    }
  for (int c = 0; c < nc; c++) {
    Resumen ra = resumir(sa[c], ns), rb = resumir(sb[c], ns);
    o[c].a_media = ra.media; o[c].a_ee = ra.ee; o[c].b_media = rb.media; o[c].b_ee = rb.ee;
    o[c].a_p5 = p5_de(ta[c], ns * FIELDS, tmp); o[c].b_p5 = p5_de(tb[c], ns * FIELDS, tmp);
    pareada(sa[c], sa[ref], ns, &o[c].da, &o[c].da_ee);
    pareada(sb[c], sb[ref], ns, &o[c].db, &o[c].db_ee);
  }
  liberar_matriz(sa, nc); liberar_matriz(sb, nc); liberar_matriz(ta, nc); liberar_matriz(tb, nc);

  /* --- una competencia de tres rondas --- */
  int nk = ns / 3;
  if (nk >= 20) {
    int *perm = malloc(sizeof(int) * (size_t)ns);
    double **ca = matriz(nc, nk), **cb = matriz(nc, nk), **cs = matriz(nc, nk), **cr = matriz(nc, nk);
    double *ee = calloc((size_t)nc * 4, sizeof(double)), *dee = calloc((size_t)nc * 4, sizeof(double));
    for (int c = 0; c < nc; c++) o[c].ca_peor = o[c].cb_peor = 2.0;
    for (int rep = 0; rep < REPS; rep++) {
      permutar(perm, ns, &az);
      for (int k = 0; k < nk; k++) {
        const int *tr = perm + 3 * k;
        for (int g = 0; g < G; g++) campo[g] = g < nf ? extra_fijo[g] : sortear(acum, nr, &az);
        for (int g = 0; g < G; g++) {
          const double *rg = R[campo[g]];
          xs[g] = rg[tr[0]] + rg[tr[1]] + rg[tr[2]];
          xr[g] = rg[tr[0]] / byh[tr[0]] + rg[tr[1]] / byh[tr[1]] + rg[tr[2]] / byh[tr[2]];
        }
        for (int c = 0; c < nc; c++) { ca[c][k] = cb[c][k] = 0; }
        for (int j = 0; j < 3; j++) {
          for (int g = 0; g < G; g++) x[g] = R[campo[g]][tr[j]];
          for (int c = 0; c < nc; c++) {
            ca[c][k] += puntos_patrimonio(W[c][tr[j]], x, G) / 3;
            cb[c][k] += puntos_puesto(W[c][tr[j]], x, G) / 3;
          }
        }
        for (int c = 0; c < nc; c++) {
          const double *wc = W[c];
          cs[c][k] = puntos_patrimonio(wc[tr[0]] + wc[tr[1]] + wc[tr[2]], xs, G);
          cr[c][k] = puntos_patrimonio(wc[tr[0]] / byh[tr[0]] + wc[tr[1]] / byh[tr[1]] + wc[tr[2]] / byh[tr[2]], xr, G);
        }
      }
      double pra = p5_de(ca[ref], nk, tmp), prb = p5_de(cb[ref], nk, tmp), prs = p5_de(cs[ref], nk, tmp);
      double prr = p5_de(cr[ref], nk, tmp);
      for (int c = 0; c < nc; c++) {
        double pa = p5_de(ca[c], nk, tmp), pb = p5_de(cb[c], nk, tmp), ps = p5_de(cs[c], nk, tmp), m, e;
        double pr = p5_de(cr[c], nk, tmp);
        Resumen rs = resumir(cs[c], nk), rr = resumir(cr[c], nk);
        o[c].ca_p5 += pa / REPS; o[c].cb_p5 += pb / REPS; o[c].cs_p5 += ps / REPS; o[c].cr_p5 += pr / REPS;
        o[c].dca_p5 += (pa - pra) / REPS; o[c].dcb_p5 += (pb - prb) / REPS; o[c].dcs_p5 += (ps - prs) / REPS;
        o[c].dcr_p5 += (pr - prr) / REPS;
        o[c].cs_media += rs.media / REPS; o[c].cs_ee += rs.ee / REPS;
        o[c].cr_media += rr.media / REPS; o[c].cr_ee += rr.ee / REPS;
        pareada(cs[c], cs[ref], nk, &m, &e);
        o[c].ds += m / REPS; o[c].ds_ee += e / REPS;
        pareada(cr[c], cr[ref], nk, &m, &e);
        o[c].dr += m / REPS; o[c].dr_ee += e / REPS;
        for (int k = 0; k < nk; k++) {
          if (ca[c][k] < o[c].ca_peor) o[c].ca_peor = ca[c][k];
          if (cb[c][k] < o[c].cb_peor) o[c].cb_peor = cb[c][k];
        }
      }
      error_p5(ca, nc, ref, nk, &az, ee, dee);
      error_p5(cb, nc, ref, nk, &az, ee + nc, dee + nc);
      error_p5(cs, nc, ref, nk, &az, ee + 2 * nc, dee + 2 * nc);
      error_p5(cr, nc, ref, nk, &az, ee + 3 * nc, dee + 3 * nc);
    }
    for (int c = 0; c < nc; c++) {
      o[c].ca_p5_ee = ee[c] / REPS; o[c].cb_p5_ee = ee[nc + c] / REPS; o[c].cs_p5_ee = ee[2 * nc + c] / REPS;
      o[c].cr_p5_ee = ee[3 * nc + c] / REPS;
      o[c].dca_p5_ee = dee[c] / REPS; o[c].dcb_p5_ee = dee[nc + c] / REPS; o[c].dcs_p5_ee = dee[2 * nc + c] / REPS;
      o[c].dcr_p5_ee = dee[3 * nc + c] / REPS;
    }
    liberar_matriz(ca, nc); liberar_matriz(cb, nc); liberar_matriz(cs, nc); liberar_matriz(cr, nc);
    free(perm); free(ee); free(dee);
  }
  free(tmp);
}

void tres_rondas(double **W, const double *byh, int nc, int ref, int ns, uint64_t semilla, TresRondas *o) {
  Azar az;
  int nk = ns / 3;
  azar_sembrar(&az, semilla);
  memset(o, 0, sizeof(TresRondas) * (size_t)nc);
  if (nk < 20) return;
  int *perm = malloc(sizeof(int) * (size_t)ns);
  double **w3 = matriz(nc, nk), **e3 = matriz(nc, nk), *tmp = malloc(sizeof(double) * (size_t)nk);
  double *ee = calloc((size_t)nc * 2, sizeof(double)), *dee = calloc((size_t)nc * 2, sizeof(double));
  for (int c = 0; c < nc; c++) o[c].w3_peor = o[c].e3_peor = 1e300;
  for (int rep = 0; rep < REPS; rep++) {
    permutar(perm, ns, &az);
    for (int k = 0; k < nk; k++) {
      const int *tr = perm + 3 * k;
      double b = (byh[tr[0]] + byh[tr[1]] + byh[tr[2]]) / 3;
      for (int c = 0; c < nc; c++) {
        w3[c][k] = (W[c][tr[0]] + W[c][tr[1]] + W[c][tr[2]]) / 3;
        e3[c][k] = w3[c][k] - b;
        if (w3[c][k] < o[c].w3_peor) o[c].w3_peor = w3[c][k];
        if (e3[c][k] < o[c].e3_peor) o[c].e3_peor = e3[c][k];
      }
    }
    double pref = p5_de(w3[ref], nk, tmp);
    for (int c = 0; c < nc; c++) {
      double p = p5_de(w3[c], nk, tmp);
      o[c].w3_p5 += p / REPS; o[c].dw3_p5 += (p - pref) / REPS;
      o[c].e3_p5 += p5_de(e3[c], nk, tmp) / REPS;
      o[c].w3_media += resumir(w3[c], nk).media / REPS;
    }
    error_p5(w3, nc, ref, nk, &az, ee, dee);
    error_p5(e3, nc, ref, nk, &az, ee + nc, dee + nc);
  }
  for (int c = 0; c < nc; c++) {
    o[c].w3_p5_ee = ee[c] / REPS; o[c].e3_p5_ee = ee[nc + c] / REPS; o[c].dw3_p5_ee = dee[c] / REPS;
  }
  liberar_matriz(w3, nc); liberar_matriz(e3, nc);
  free(perm); free(tmp); free(ee); free(dee);
}

/* ---- Caché de resultados --------------------------------------------------------------------------- */
/* Un archivo por (archivo de series, estrategia): build/resultados/ARCHIVO/SPEC.res.
 * Solo para las estrategias del núcleo y las reglas por defecto. Lleva la
 * versión de los fuentes del núcleo y la huella del archivo de series: si
 * alguna cambió, no se usa y se recalcula. Se escribe solo con
 * RETORNO_GUARDAR=1 (lo pone el Makefile de este estudio); los demás binarios
 * solo leen. RETORNO_SIN_CACHE=1 obliga a recalcular todo. */

#ifndef RETORNO_DIR
#define RETORNO_DIR "factibilidad/retorno"
#endif
#ifndef NUCLEO_VERSION
#define NUCLEO_VERSION 0ULL
#endif

typedef struct { char magia[4]; int ns; unsigned long long version, huella; int caja0, comision; } Cabecera;

static int del_nucleo(const char *spec) {
  static const char *propias[] = {"param", "cruce", "momentum", "byh", "nada", "reversion", "azar", NULL};
  const char *dp = strchr(spec, ':');
  size_t largo = dp ? (size_t)(dp - spec) : strlen(spec);
  for (const char **p = propias; *p; p++)
    if (strlen(*p) == largo && !strncmp(*p, spec, largo)) return 1;
  return 0;
}

static void ruta_cache(char *ruta, size_t tam, const char *archivo, const char *spec, int con_archivo) {
  char limpio[512];
  size_t k = 0;
  for (const char *p = spec; *p && k + 1 < sizeof limpio; p++)
    limpio[k++] = *p == ':' ? '.' : *p == ',' ? '_' : *p == '=' ? '-' : *p == '/' ? '_' : *p;
  limpio[k] = 0;
  const char *base = getenv("RETORNO_RESULTADOS");
  if (!base || !*base) base = RETORNO_DIR "/build/resultados";
  if (con_archivo) snprintf(ruta, tam, "%s/%s/%s.res", base, archivo, limpio);
  else snprintf(ruta, tam, "%s/%s", base, archivo);
}

Resultado *resultados(const char *spec, const Lote *l, const char *conjunto, int largo, int semilla, const Reglas *r) {
  (void)conjunto; (void)largo; (void)semilla;
  char error[256] = "", resuelta[512];
  Instancia *inst = instancia_crear(spec, error, sizeof error);
  if (!inst) { fprintf(stderr, "%s\n", error); return NULL; }
  strcpy(resuelta, instancia_spec(inst));
  instancia_destruir(inst);

  Resultado *res = malloc(sizeof(Resultado) * (size_t)l->ns);
  int usar = del_nucleo(resuelta) && r->caja0 == CAJA0_DEF && r->comision == COMISION_DEF && !getenv("RETORNO_SIN_CACHE");
  const char *g = getenv("RETORNO_GUARDAR");
  int guardar = usar && g && *g == '1';
  for (int k = 0; k < l->partes; k++) {
    int cuantas = l->inicio[k + 1] - l->inicio[k], listo = 0;
    char ruta[1200];
    ruta_cache(ruta, sizeof ruta, l->archivo[k], resuelta, 1);
    if (usar) {
      FILE *f = fopen(ruta, "rb");
      Cabecera cab;
      if (f) {
        if (fread(&cab, sizeof cab, 1, f) == 1 && !memcmp(cab.magia, "RES2", 4) && cab.version == NUCLEO_VERSION &&
            cab.huella == l->huella[k] && cab.ns >= cuantas && cab.caja0 == r->caja0 && cab.comision == r->comision &&
            fread(res + l->inicio[k], sizeof(Resultado), (size_t)cuantas, f) == (size_t)cuantas) listo = 1;
        fclose(f);
      }
    }
    if (listo) continue;
    Lote sub = *l;                                 /* solo esta parte */
    sub.ns = cuantas; sub.datos = l->datos + (size_t)l->inicio[k] * l->n; sub.partes = 1;
    sub.inicio[0] = 0; sub.inicio[1] = cuantas;
    if (evaluar_lote(resuelta, &sub, r, res + l->inicio[k])) { free(res); return NULL; }
    if (guardar && cuantas == l->total[k]) {
      char dir[1200], tmp[1300];
      ruta_cache(dir, sizeof dir, "", "", 0);
      mkdir(dir, 0777);
      ruta_cache(dir, sizeof dir, l->archivo[k], "", 0);
      if (mkdir(dir, 0777) && errno != EEXIST) continue;
      snprintf(tmp, sizeof tmp, "%s.tmp%d", ruta, (int)(semilla_serie(resuelta, k) & 0xffff));
      FILE *f = fopen(tmp, "wb");
      if (!f) continue;
      Cabecera cab = {{'R', 'E', 'S', '2'}, cuantas, NUCLEO_VERSION, l->huella[k], r->caja0, r->comision};
      fwrite(&cab, sizeof cab, 1, f);
      fwrite(res + l->inicio[k], sizeof(Resultado), (size_t)cuantas, f);
      fclose(f);
      rename(tmp, ruta);
    }
  }
  return res;
}
