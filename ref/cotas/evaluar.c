/*
 * evaluar.c: patrimonio final de varias estrategias en muchas ventanas de precios.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * La contabilidad es la del testbench oficial (ref/market.py): la decisión que se lee
 * en el tick n es la que se escribió después de ver el precio n-1 (en el tick 0,
 * mantener), y se ejecuta al precio n. Comprar se recorta a (caja - comisión) / p,
 * vender a las acciones que se tienen, y una orden que queda en cero no se ejecuta.
 *
 * Estrategias (una por línea en el archivo de estrategias, "nombre tipo parámetros"):
 *   cotas  inicio a b banda k u    ref/cotas.py (inicio: 0 espera, 1 compra, 2 parte, 3 umbral)
 *   media  k entra sale            ref/trader.py (ReglaBase; max_media es 5 3 0)
 *   zscore km kd num den w sx2     ref/zscore.py
 *   nada                           mantener siempre
 *   siempre                        comprar 63 siempre (comprar y mantener desde el tick 1)
 *
 * Ventanas: archivo binario con "int32 n" y después n veces "int32 largo, largo bytes".
 * Salida (stdout): una línea por ventana con el patrimonio de cada estrategia, separados
 * por comas, y las órdenes en un segundo archivo si se pide.
 *
 * Uso: evaluar ESTRATEGIAS VENTANAS [caja comisión]
 * Verificado contra ref/cotas.py, ref/trader.py y ref/zscore.py (ref/cotas/validar.py).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { COTAS, MEDIA, ZSCORE, NADA, SIEMPRE };
#define MANTENER 0x00
#define COMPRAR 0x7F
#define VENDER 0xBF

typedef struct {
  int tipo;
  int par[6];
  char nombre[64];
} Estrategia;

typedef struct {   /* estado de una estrategia en una ventana */
  int primero, q, vio_lo, vio_hi;      /* cotas */
  long S; int pos;                     /* media */
  long M, D; int n, quiere;            /* zscore */
} Estado;

static int decidir(const Estrategia *e, Estado *s, int p) {
  const int *a = e->par;
  switch (e->tipo) {
  case NADA:
    return MANTENER;
  case SIEMPRE:
    return COMPRAR;
  case COTAS: {
    int inicio = a[0], ma = a[1], mb = a[2], banda = a[3], k = a[4], u = a[5];
    int primero = s->primero;
    s->primero = 0;
    if (p <= 100 + ma) {
      if (p <= 100) s->vio_lo = 1;
      s->q = COMPRAR;
      return s->q;
    }
    if (p >= 255 - mb) {
      if (p >= 255) s->vio_hi = 1;
      s->q = VENDER;
      return s->q;
    }
    if (primero) {
      if (inicio == 1 || (inicio == 3 && p <= u)) s->q = COMPRAR;
      else if (inicio == 2 && k > 0) { s->q = MANTENER; return 0x40 | k; }
    }
    if (banda && s->vio_lo && s->vio_hi) {
      if (p <= 100 + banda) s->q = COMPRAR;
      else if (p >= 255 - banda) s->q = VENDER;
    }
    return s->q;
  }
  case MEDIA: {
    int k = a[0], entra = a[1], sale = a[2];
    long uc = -((long)entra << k), uv = ((long)sale << k) + 1;
    if (s->primero) { s->S = (long)p << k; s->primero = 0; }
    long dev = ((long)p << k) - s->S;
    int compra = dev < uc, no_vende = dev < uv;
    s->pos = (s->pos | compra) & no_vende;
    s->S = s->S + p - (((s->S + (1L << k) - 1) << (8 - k)) >> 8);
    return s->pos ? COMPRAR : VENDER;
  }
  case ZSCORE: {
    int km = a[0], kd = a[1], num = a[2], den = a[3], w = a[4], sx2 = a[5];
    if (s->primero) { s->M = (long)p << km; s->primero = 0; return MANTENER; }
    long dev = ((long)p << km) - s->M, mag = dev < 0 ? -dev : dev;
    s->M += p - ((s->M + (1L << (km - 1))) >> km);
    s->D += mag - ((s->D + (1L << (kd - 1))) >> kd);
    if (s->n < w) { s->n++; return MANTENER; }
    if (dev < 0 && ((long)den << kd) * mag > (long)num * s->D) s->quiere = 1;
    else if (dev > 0 && (2L << kd) * dev > (long)sx2 * s->D) s->quiere = 0;
    return s->quiere ? COMPRAR : VENDER;
  }
  }
  return MANTENER;
}

static long correr(const Estrategia *e, const unsigned char *p, int n, long caja0, long com, int *ordenes) {
  Estado s;
  memset(&s, 0, sizeof s);
  s.primero = 1;
  long caja = caja0, acc = 0;
  int actual = MANTENER, ord = 0;
  for (int t = 0; t < n; t++) {
    int d = actual, q = d & 63, accion = (d >> 6) & 3;
    long pr = p[t];
    if (accion == 1) {
      long tope = (caja - com) / pr;     /* caja - com >= 0 siempre que haya caja: trunca como SV */
      if (caja - com < 0) tope = -((com - caja) / pr);
      if (q > tope) q = (int)tope;
      if (q > 0) { caja -= q * pr + com; acc += q; ord++; }
    } else if (accion == 2) {
      if (q > acc) q = (int)acc;
      if (q > 0 && caja + q * pr >= com) { caja += q * pr - com; acc -= q; ord++; }
    }
    actual = decidir(e, &s, p[t]);
  }
  *ordenes = ord;
  return caja + acc * p[n - 1];
}

static int leer_estrategias(const char *ruta, Estrategia **out) {
  FILE *f = fopen(ruta, "r");
  if (!f) { perror(ruta); exit(1); }
  int cap = 64, n = 0;
  Estrategia *v = malloc(cap * sizeof *v);
  char linea[256], tipo[32];
  while (fgets(linea, sizeof linea, f)) {
    if (linea[0] == '#' || linea[0] == '\n') continue;
    if (n == cap) v = realloc(v, (cap *= 2) * sizeof *v);
    Estrategia *e = &v[n];
    memset(e, 0, sizeof *e);
    int c = sscanf(linea, "%63s %31s %d %d %d %d %d %d", e->nombre, tipo, &e->par[0], &e->par[1], &e->par[2],
                   &e->par[3], &e->par[4], &e->par[5]);
    if (c < 2) continue;
    if (!strcmp(tipo, "cotas")) e->tipo = COTAS;
    else if (!strcmp(tipo, "media")) e->tipo = MEDIA;
    else if (!strcmp(tipo, "zscore")) e->tipo = ZSCORE;
    else if (!strcmp(tipo, "nada")) e->tipo = NADA;
    else if (!strcmp(tipo, "siempre")) e->tipo = SIEMPRE;
    else { fprintf(stderr, "tipo desconocido: %s\n", tipo); exit(1); }
    n++;
  }
  fclose(f);
  *out = v;
  return n;
}

int main(int argc, char **argv) {
  if (argc < 3) { fprintf(stderr, "uso: evaluar ESTRATEGIAS VENTANAS [caja comision] [ORDENES]\n"); return 1; }
  long caja0 = argc > 3 ? atol(argv[3]) : 10000, com = argc > 4 ? atol(argv[4]) : 5;
  FILE *fo = argc > 5 ? fopen(argv[5], "w") : NULL;
  Estrategia *es;
  int ne = leer_estrategias(argv[1], &es);
  FILE *f = fopen(argv[2], "rb");
  if (!f) { perror(argv[2]); return 1; }
  int nv;
  if (fread(&nv, 4, 1, f) != 1) return 1;
  for (int i = 0; i < ne; i++) printf("%s%s", i ? "," : "", es[i].nombre);
  printf("\n");
  if (fo) {
    for (int i = 0; i < ne; i++) fprintf(fo, "%s%s", i ? "," : "", es[i].nombre);
    fprintf(fo, "\n");
  }
  unsigned char *p = NULL;
  int cap = 0;
  for (int v = 0; v < nv; v++) {
    int n;
    if (fread(&n, 4, 1, f) != 1) return 1;
    if (n > cap) { cap = n; p = realloc(p, cap); }
    if (fread(p, 1, n, f) != (size_t)n) return 1;
    for (int i = 0; i < ne; i++) {
      int o;
      long w = correr(&es[i], p, n, caja0, com, &o);
      printf("%s%ld", i ? "," : "", w);
      if (fo) fprintf(fo, "%s%d", i ? "," : "", o);
    }
    printf("\n");
    if (fo) fprintf(fo, "\n");
  }
  if (fo) fclose(fo);
  return 0;
}
