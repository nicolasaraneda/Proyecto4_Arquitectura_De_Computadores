/*
 * ventanas.c: patrimonio de varias estrategias en todas las ventanas de una serie real.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Toma la serie de minutos de una empresa (precios en dólares), corta una ventana de LARGO
 * precios en cada posición de inicio (de PASO en PASO), la normaliza como el profesor
 * (mínimo a 100, máximo a 255, lineal y redondeada: ref/cotas/comun.py, normalizar) y corre
 * cada estrategia con la contabilidad del testbench. Las estrategias y la contabilidad son
 * las de evaluar.c, que se incluye tal cual (validadas contra Python en validar.py).
 *
 * Entrada SERIE: "int32 n" y n valores double.
 * Salida SALIDA: "int32 nv, int32 ne", después nv inicios (int32), nv posiciones del primer
 * 100 y nv del primer 255 dentro de la ventana (int32), y nv filas de ne patrimonios (int32).
 *
 * Uso: ventanas ESTRATEGIAS SERIE LARGO PASO SALIDA [caja comisión]
 * Paraleliza por ventana con OpenMP. ref/cotas/reales.py lo compila y lo usa.
 */
#define EVALUAR_SIN_MAIN
#include "evaluar.c"

static void normalizar(const double *x, int n, double lo, double hi, unsigned char *out) {
  for (int i = 0; i < n; i++)
    out[i] = (hi == lo) ? 178 : (unsigned char)(int)(100 + (x[i] - lo) * 155.0 / (hi - lo) + 0.5);
}

int main(int argc, char **argv) {
  if (argc < 6) { fprintf(stderr, "uso: ventanas ESTRATEGIAS SERIE LARGO PASO SALIDA [caja comision]\n"); return 1; }
  int largo = atoi(argv[3]), paso = atoi(argv[4]);
  long caja0 = argc > 6 ? atol(argv[6]) : 10000, com = argc > 7 ? atol(argv[7]) : 5;
  Estrategia *es;
  int ne = leer_estrategias(argv[1], &es);
  FILE *f = fopen(argv[2], "rb");
  if (!f) { perror(argv[2]); return 1; }
  int n;
  if (fread(&n, 4, 1, f) != 1) return 1;
  double *x = malloc((size_t)n * sizeof *x);
  if (fread(x, sizeof *x, n, f) != (size_t)n) return 1;
  fclose(f);
  if (n < largo) { fprintf(stderr, "serie mas corta que la ventana\n"); return 1; }
  int nv = (n - largo) / paso + 1;

  /* mínimo y máximo de cada ventana de largo fijo, con colas monótonas (O(n)) */
  int nall = n - largo + 1;
  double *lo = malloc(nall * sizeof *lo), *hi = malloc(nall * sizeof *hi);
  int *qmin = malloc(n * sizeof *qmin), *qmax = malloc(n * sizeof *qmax);
  int a0 = 0, a1 = 0, b0 = 0, b1 = 0;
  for (int i = 0; i < n; i++) {
    while (a1 > a0 && x[qmin[a1 - 1]] >= x[i]) a1--;
    qmin[a1++] = i;
    while (b1 > b0 && x[qmax[b1 - 1]] <= x[i]) b1--;
    qmax[b1++] = i;
    int s = i - largo + 1;
    if (s >= 0) {
      while (qmin[a0] < s) a0++;
      while (qmax[b0] < s) b0++;
      lo[s] = x[qmin[a0]];
      hi[s] = x[qmax[b0]];
    }
  }

  int *ini = malloc(nv * sizeof *ini), *pmin = malloc(nv * sizeof *pmin), *pmax = malloc(nv * sizeof *pmax);
  int *w = malloc((size_t)nv * ne * sizeof *w);
#pragma omp parallel
  {
    unsigned char *p = malloc(largo);
#pragma omp for schedule(dynamic, 64)
    for (int v = 0; v < nv; v++) {
      int s = v * paso;
      normalizar(x + s, largo, lo[s], hi[s], p);
      ini[v] = s;
      pmin[v] = pmax[v] = -1;
      for (int t = 0; t < largo; t++) {
        if (pmin[v] < 0 && p[t] == 100) pmin[v] = t;
        if (pmax[v] < 0 && p[t] == 255) pmax[v] = t;
      }
      for (int j = 0; j < ne; j++) {
        int o;
        w[(size_t)v * ne + j] = (int)correr(&es[j], p, largo, caja0, com, &o);
      }
    }
    free(p);
  }
  FILE *g = fopen(argv[5], "wb");
  if (!g) { perror(argv[5]); return 1; }
  fwrite(&nv, 4, 1, g);
  fwrite(&ne, 4, 1, g);
  fwrite(ini, 4, nv, g);
  fwrite(pmin, 4, nv, g);
  fwrite(pmax, 4, nv, g);
  fwrite(w, 4, (size_t)nv * ne, g);
  fclose(g);
  return 0;
}
