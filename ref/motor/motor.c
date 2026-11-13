/* motor.c: evaluador rápido de la familia paramétrica de estrategias.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Es la herramienta de exploración del frente del algoritmo: corre una
 * estrategia descrita por parámetros enteros sobre un lote de series y
 * entrega el patrimonio final de cada una. La contabilidad es la del
 * testbench oficial (la misma de ref/market.py). La estrategia es la misma
 * de ref/candidatos.py (clase Trader), con las mismas operaciones enteras:
 * ref/test_candidatos.py exige que los dos den lo mismo, serie por serie.
 *
 * No es parte del diseño ni del programa de la placa: solo sirve para barrer
 * miles de combinaciones de parámetros en segundos. Python puro demora unas
 * cien veces más.
 *
 * Uso:
 *   motor SERIES.bin [--detalle] < configuraciones.txt
 *
 * SERIES.bin: dos enteros de 32 bits (número de series y ticks por serie) y
 * después un byte por precio. Lo escribe ref/motor.py.
 * Cada línea de la entrada es una configuración: pares nombre=valor separados
 * por espacios (ver la tabla de parámetros más abajo). Por cada línea sale
 * una línea con el resumen del lote, o con --detalle una línea por serie:
 * patrimonio, órdenes, pérdida máxima, ticks con la guardia o el tope activos,
 * cortes de posición y veces que saltó el tope de pérdida.
 *
 * Todos los parámetros son enteros y todas las operaciones de la estrategia
 * son sumas, restas, comparaciones y desplazamientos por una constante: nada
 * que Espino no pueda hacer (ver docs/algoritmo.md).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CAJA0_DEF 10000
#define COMISION_DEF 5

typedef struct {
  /* estimador */
  int est;      /* 0: media exponencial. 1: Kalman de dos estados. 2: suma móvil de 2^k precios */
  int k;        /* media exponencial: alfa = 1/2^k. La desviación queda en unidades de 1/2^k */
  int ka, kb;   /* Kalman: phi = 1 - 2^-ka - 2^-kb (kb = 0: sin el segundo término) */
  int k1a, k1b; /* Kalman: K1 = 2^-k1a + 2^-k1b */
  int k2a, k2b; /* Kalman: K2 = 2^-k2a + 2^-k2b */
  /* bandas, en unidades de la desviación */
  int E;        /* entra si dev < -(E + ev*V/2^sv) */
  int X;        /* sale si dev > X + xv*V/2^sv */
  /* volatilidad: V = media exponencial de |p - p_anterior| por 2^kv */
  int kv, ev, xv, sv;
  /* saltos: si |p - p_anterior| >= J el nivel se corre con el salto (0: apagado) */
  int J;
  /* tope de tiempo y de precio de una posición */
  int tmax;     /* sale si lleva más de tmax ticks adentro (0: apagado) */
  int stop;     /* sale si p <= precio de entrada - stop (0: apagado) */
  int lock;     /* después de un corte no entra por `lock` ticks. 0: hasta que dev > X */
  /* guardia de régimen: G = media exponencial de la desviación, alfa = 1/2^kg */
  int kg;       /* 0: apagada */
  int g;        /* guardia activa si G < -g (unidades de dev) */
  int gsal;     /* 1: con la guardia activa además sale */
  int nfal;     /* guardia por cortes: después de nfal cortes seguidos deja de operar gapag ticks (0: apagada) */
  int gapag;
  /* tope de pérdida acumulada, en unidades de precio */
  int cap;      /* deja de operar si la caída acumulada (salida - entrada, más la posición abierta) pasa de */
  int capsh;    /*   cap + (precio >> capsh) + (precio >> capsh2). Todo en 0: apagado */
  int capsh2;
  int capoff;   /* por cuántos ticks deja de operar (0: hasta el final) */
  int capini;   /* 1: la pérdida se mide desde el inicio de la ronda. 0: desde el mejor momento */
  /* tamaño de las órdenes */
  int modo;     /* 0: siempre 63. 1: una sola orden de compra por entrada. 2: segunda orden solo si p <= p2 */
  int p2;
  int q1, E2;   /* entrada escalonada: q1 acciones en E y el resto (63) si dev < -E2. q1 = 0: apagada */
  /* mercado */
  int caja0, comision;
} Cfg;

static void cfg_def(Cfg *c) {
  memset(c, 0, sizeof *c);
  c->k = 5; c->E = 128; c->X = 0;
  c->ka = 5; c->kb = 7; c->k1a = 1; c->k1b = 3; c->k2a = 3; c->k2b = 4;
  c->caja0 = CAJA0_DEF; c->comision = COMISION_DEF;
}

#define CAMPO(n) if (!strcmp(nombre, #n)) { c->n = v; return 1; }
static int cfg_set(Cfg *c, const char *nombre, int v) {
  CAMPO(est) CAMPO(k) CAMPO(ka) CAMPO(kb) CAMPO(k1a) CAMPO(k1b) CAMPO(k2a) CAMPO(k2b)
  CAMPO(E) CAMPO(X) CAMPO(kv) CAMPO(ev) CAMPO(xv) CAMPO(sv) CAMPO(J)
  CAMPO(tmax) CAMPO(stop) CAMPO(lock) CAMPO(kg) CAMPO(g) CAMPO(gsal) CAMPO(nfal) CAMPO(gapag)
  CAMPO(cap) CAMPO(capsh) CAMPO(capsh2) CAMPO(capoff) CAMPO(capini) CAMPO(modo) CAMPO(p2) CAMPO(q1) CAMPO(E2)
  CAMPO(caja0) CAMPO(comision)
  return 0;
}

typedef struct { int w, ordenes, max_dd, guardia, cortes, topes, pausas; } Res;

#define ASR(x, s) ((x) >> (s))          /* desplazamiento aritmético (redondea hacia abajo) */
#define FK 8                            /* bits de fracción del Kalman */

static Res correr(const unsigned char *p, int n, const Cfg *c) {
  /* mercado */
  int caja = c->caja0, acciones = 0, w = c->caja0, peak = c->caja0, max_dd = 0, ordenes = 0;
  int decision = 0;                     /* DECISION parte en 0: mantener */
  /* estado de la estrategia */
  int ini = 0, S = 0, L = 0, T = 0, V = 0, G = 0, pant = 0;
  int pos = 0, etapa = 0, t_dentro = 0, p_entrada = 0, bloqueo = 0, espera = 0;
  int perdida = 0, apagado = 0, compro = 0, fallas = 0, pausa = 0;
  int buf[256], bi = 0, suma = 0;
  Res r = {0, 0, 0, 0, 0, 0, 0};

  for (int t = 0; t < n; t++) {
    int pr = p[t];
    /* --- la maestra ejecuta al precio de este tick la decisión anterior --- */
    {
      int q = decision & 63, accion = (decision >> 6) & 3;
      if (accion == 1) {
        int tope = (caja - c->comision) / pr;
        if (q > tope) q = tope;
        if (q > 0) { caja -= q * pr + c->comision; acciones += q; ordenes++; }
      } else if (accion == 2) {
        if (q > acciones) q = acciones;
        if (q > 0 && caja + q * pr >= c->comision) { caja += q * pr - c->comision; acciones -= q; ordenes++; }
      }
      w = caja + acciones * pr;
      if (w > peak) peak = w;
      if (peak - w > max_dd) max_dd = peak - w;
    }
    /* --- el programa ve el precio y decide ---------------------------------- */
    int dev, d;
    if (!ini) {
      ini = 1; pant = pr;
      S = pr << c->k; L = pr << FK; T = 0;
      if (c->est == 2) { for (int i = 0; i < (1 << c->k); i++) buf[i] = pr; suma = pr << c->k; }
    }
    d = pr - pant; pant = pr;
    int ad = d < 0 ? -d : d;
    if (c->J && ad >= c->J) {           /* salto: el nivel se corre con el precio */
      S += d << c->k; L += d << FK;
      if (c->est == 2) { for (int i = 0; i < (1 << c->k); i++) buf[i] += d; suma += d << c->k; }
      ad = 0;
    }
    if (c->est == 0) {
      dev = (pr << c->k) - S;
      S = S + ASR(dev, c->k);
    } else if (c->est == 2) {
      dev = (pr << c->k) - suma;
      suma += pr - buf[bi]; buf[bi] = pr; bi = (bi + 1) & ((1 << c->k) - 1);
    } else {
      int Tp = T - ASR(T, c->ka) - (c->kb ? ASR(T, c->kb) : 0);
      int e = (pr << FK) - L - Tp;
      L = L + ASR(e, c->k1a) + (c->k1b ? ASR(e, c->k1b) : 0);
      T = Tp + ASR(e, c->k2a) + (c->k2b ? ASR(e, c->k2b) : 0);
      dev = T;
    }
    int Eef = c->E, Xef = c->X;
    if (c->kv) {
      Eef += ASR(c->ev * V, c->sv);
      Xef += ASR(c->xv * V, c->sv);
      V = V + ad - ASR(V + (1 << c->kv) - 1, c->kv);
    }
    int guardia = 0;
    if (c->kg) {
      guardia = G < -c->g;
      G = G + ASR(dev - G, c->kg);
    }
    if (apagado > 0) { apagado--; if (apagado == 0) perdida = 0; }
    if (pausa > 0) pausa--;
    int veto = guardia || apagado != 0 || pausa != 0;
    if (bloqueo > 0) bloqueo--;

    int entra = dev < -Eef;
    int sale = dev > Xef;
    if (espera && sale) espera = 0;     /* después de un corte espera a que el precio recupere la media */
    int corte = 0, tope = 0;
    if (pos) {
      t_dentro++;
      if (c->tmax && t_dentro > c->tmax) corte = 1;
      if (c->stop && pr <= p_entrada - c->stop) corte = 1;
      if (guardia && c->gsal) corte = 1;
      /* tope de pérdida: caída acumulada desde el mejor momento, contando la posición abierta */
      if ((c->cap || c->capsh) && perdida + (pr - p_entrada) < -(c->cap + (c->capsh ? (pr >> c->capsh) : 0) + (c->capsh2 ? (pr >> c->capsh2) : 0))) tope = 1;
    }
    if (pos && (sale || corte || tope)) {
      pos = 0; etapa = 0;
      perdida += pr - p_entrada;
      if (perdida > 0 && !c->capini) perdida = 0;   /* desde el mejor momento: una ganancia la deja en cero */
      if (corte && !sale) {
        r.cortes++;
        if (c->lock) bloqueo = c->lock; else espera = 1;
        fallas++;
        if (c->nfal && fallas >= c->nfal) { pausa = c->gapag; fallas = 0; r.pausas++; }
      } else if (!tope) fallas = 0;
      if (tope) { apagado = c->capoff ? c->capoff : 0x7fffffff; r.topes++; }
    } else if (!pos && entra && !sale && !veto && !bloqueo && !espera) {
      pos = 1; etapa = 1; t_dentro = 0; p_entrada = pr; compro = 0;
    }
    if (pos && c->q1 && etapa == 1 && dev < -c->E2) etapa = 2;
    r.guardia += veto;

    if (!pos) decision = 0xBF;
    else if (c->q1 && etapa == 1) { decision = compro ? 0x00 : (0x40 | c->q1); compro = 1; }
    else if (c->modo == 1) { decision = compro ? 0x00 : 0x7F; compro = 1; }
    else if (c->modo == 2) { decision = (compro && pr > c->p2) ? 0x00 : 0x7F; compro = 1; }
    else decision = 0x7F;
  }
  r.w = w; r.ordenes = ordenes; r.max_dd = max_dd;
  return r;
}

static int cmp_int(const void *a, const void *b) { return *(const int *)a - *(const int *)b; }

int main(int argc, char **argv) {
  if (argc < 2) { fprintf(stderr, "uso: motor SERIES.bin [--detalle] < configuraciones\n"); return 2; }
  int detalle = argc > 2 && !strcmp(argv[2], "--detalle");
  FILE *f = fopen(argv[1], "rb");
  if (!f) { perror(argv[1]); return 1; }
  int cab[2];
  if (fread(cab, sizeof(int), 2, f) != 2) { fprintf(stderr, "cabecera\n"); return 1; }
  int ns = cab[0], n = cab[1];
  unsigned char *datos = malloc((size_t)ns * n);
  if (fread(datos, 1, (size_t)ns * n, f) != (size_t)ns * n) { fprintf(stderr, "datos\n"); return 1; }
  fclose(f);
  int *ws = malloc(sizeof(int) * ns);
  char linea[4096];
  while (fgets(linea, sizeof linea, stdin)) {
    Cfg c; cfg_def(&c);
    int vacia = 1;
    for (char *tok = strtok(linea, " \t\r\n"); tok; tok = strtok(NULL, " \t\r\n")) {
      char *eq = strchr(tok, '=');
      if (!eq) { fprintf(stderr, "parametro sin valor: %s\n", tok); return 1; }
      *eq = 0;
      if (!cfg_set(&c, tok, atoi(eq + 1))) { fprintf(stderr, "parametro desconocido: %s\n", tok); return 1; }
      vacia = 0;
    }
    (void)vacia;
    double sw = 0, so = 0, sg = 0, sc = 0, st = 0, sga = 0;
    int sobre_byh = 0, sobre_caja = 0;
    for (int i = 0; i < ns; i++) {
      const unsigned char *p = datos + (size_t)i * n;
      Res r = correr(p, n, &c);
      if (detalle) printf("%d %d %d %d %d %d\n", r.w, r.ordenes, r.max_dd, r.guardia, r.cortes, r.topes);
      ws[i] = r.w; sw += r.w; so += r.ordenes; sg += r.guardia; sc += r.cortes; st += r.topes > 0; sga += (c.nfal ? r.pausas : r.guardia) > 0;
      int q = (c.caja0 - c.comision) / p[0];
      int byh = c.caja0 - c.comision - q * p[0] + q * p[n - 1];
      sobre_byh += r.w > byh; sobre_caja += r.w > c.caja0;
    }
    if (!detalle) {
      qsort(ws, ns, sizeof(int), cmp_int);
      int i5 = (int)(0.05 * ns), i50 = (int)(0.5 * ns);
      if (i5 >= ns) i5 = ns - 1;
      if (i50 >= ns) i50 = ns - 1;
      /* media mediana p5 peor mejor sobre_byh sobre_caja ordenes guardia cortes con_tope con_guardia */
      printf("%.2f %d %d %d %d %.4f %.4f %.2f %.2f %.3f %.4f %.4f\n", sw / ns, ws[i50], ws[i5], ws[0], ws[ns - 1],
             (double)sobre_byh / ns, (double)sobre_caja / ns, so / ns, sg / ns, sc / ns, st / ns, sga / ns);
    }
    fflush(stdout);
  }
  return 0;
}
