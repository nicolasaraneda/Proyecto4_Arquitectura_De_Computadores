/* futuro.c: prueba independiente de que ninguna estrategia ni rival ve el precio al que se ejecuta su orden.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Se enlaza con el núcleo del arnés (sin su main.c) y con las estrategias de
 * ejemplo, y recorre todo lo registrado: estrategias, alias y rivales. No usa
 * correr_serie para decidir nada: tiene su propio lazo y su propia
 * contabilidad, y compara contra el arnés al final.
 *
 * Pruebas, por estrategia:
 *   A. Lazo propio contra correr_serie: mismo patrimonio, mismas órdenes y los
 *      mismos bytes leídos por la maestra (desfasados un tick, con 0 en el
 *      primero).
 *   B. Futuro perturbado: se cambian todos los precios posteriores al tick T,
 *      o solo el precio T+1 (el de ejecución de la orden emitida en T), y las
 *      órdenes emitidas hasta T inclusive tienen que ser las mismas.
 *   C. Ronda repetida después de otra distinta: mismas órdenes (no queda
 *      estado de una ronda a la siguiente).
 *   D. Martingala: en series que suben o bajan con la misma probabilidad y
 *      sin comisión, ninguna estrategia que no vea el futuro puede ganar en
 *      promedio. Se informa la media del patrimonio y su distancia a 10 000 en
 *      errores estándar.
 *
 * Control negativo: la estrategia `tramposa`, que solo existe en este
 * programa, mira por una fuga puesta a propósito en el lazo propio el precio
 * al que se va a ejecutar su orden y el que viene después. Las pruebas B y D
 * tienen que detectarla.
 *
 *   build/auditoria/futuro          (lo compila y lo corre auditoria/Makefile)
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "nucleo.h"
#include "torneo.h"

/* ---- La fuga del control negativo ------------------------------------------------------ */

static _Thread_local const unsigned char *t_fuga;      /* serie completa, o NULL si no hay fuga */
static _Thread_local int t_fuga_t, t_fuga_n;

static int tramposa_decidir(void *estado, int precio, const Cuenta *propia) {
  (void)estado; (void)propia;
  (void)precio;
  if (!t_fuga || t_fuga_t + 2 >= t_fuga_n) return MANTENER;
  /* Su orden se ejecuta al precio t+1: compra si después de ejecutarse el precio sube. */
  int ejecucion = t_fuga[t_fuga_t + 1], despues = t_fuga[t_fuga_t + 2];
  return despues > ejecucion ? COMPRAR_63 : despues < ejecucion ? VENDER_63 : MANTENER;
}

static const Estrategia tramposa = {"tramposa", "control negativo de la auditoria: mira los dos precios siguientes",
                                    0, 0, NULL, NULL, tramposa_decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(tramposa)

/* ---- Contabilidad y lazo propios -------------------------------------------------------- */

typedef struct { long caja, acc, w, maximo, caida; int ordenes, ultima; } Mia;

static void mia_tick(Mia *c, int byte, int p, int com) {
  int accion = byte >> 6, q = byte & 63;
  c->ultima = 0;
  if (accion == 1) {
    long alcanza = c->caja < com ? 0 : (c->caja - com) / p;
    if (q > alcanza) q = (int)alcanza;
    if (q >= 1) { c->caja -= (long)q * p + com; c->acc += q; c->ordenes++; c->ultima = q; }
  } else if (accion == 2) {
    if (q > c->acc) q = (int)c->acc;
    if (q >= 1 && c->caja + (long)q * p - com >= 0) { c->caja += (long)q * p - com; c->acc -= q; c->ordenes++; c->ultima = -q; }
  }
  c->w = c->caja + c->acc * p;
  if (c->w > c->maximo) c->maximo = c->w;
  if (c->maximo - c->w > c->caida) c->caida = c->maximo - c->w;
}

/* Corre la instancia con el lazo propio. emitidas[t] es el byte que la
 * estrategia entrega después de ver p[t]; la maestra lo ejecuta en p[t+1]. */
static Mia mi_ronda(Instancia *inst, const unsigned char *p, int n, const Reglas *r, uint64_t semilla,
                    unsigned char *emitidas, int con_fuga) {
  Mia c = {r->caja0, 0, r->caja0, r->caja0, 0, 0, 0};
  int escrito = 0;                                   /* DECISION después del reset */
  instancia_iniciar(inst, r, semilla);
  for (int t = 0; t < n; t++) {
    mia_tick(&c, escrito, p[t], r->comision);        /* se ejecuta lo decidido con el precio anterior */
    Cuenta copia = {(int)c.caja, (int)c.acc, (int)c.w, (int)c.maximo, (int)c.caida, c.ordenes, c.ultima, 0};
    t_fuga = con_fuga ? p : NULL; t_fuga_t = t; t_fuga_n = n;
    escrito = instancia_decidir(inst, p[t], &copia);
    if (emitidas) emitidas[t] = (unsigned char)escrito;
  }
  t_fuga = NULL;
  return c;
}

/* ---- Series de prueba ---------------------------------------------------------------------- */

enum { N = 2500, SERIES = 24, CORTES = 40, NM = 2000, MART = 4000 };

static void serie(unsigned char *p, int n, int forma, Azar *a) {
  double x = 30 + 190 * azar_u01(a), m = x;
  for (int t = 0; t < n; t++) {
    switch (forma % 4) {
      case 0: x += 0.06 * (m - x) + 4.0 * (azar_u01(a) - 0.5); if (azar_entero(a, 300) == 0) m += 50 * (azar_u01(a) - 0.5); break;
      case 1: x += 3.0 * (azar_u01(a) - 0.5) + (forma & 4 ? 0.03 : -0.03); break;      /* paseo con deriva */
      case 2: x = 1 + 254 * azar_u01(a); break;                                         /* precios sin relación */
      default: x += 0.3 * ((forma & 4 ? 4.0 : 250.0) - x) + 5.0 * (azar_u01(a) - 0.5); break;   /* pegada a un borde */
    }
    if (x < 1) x = 1;
    if (x > 255) x = 255;
    p[t] = (unsigned char)(x + 0.5);
  }
}

/* Paseo sin sesgo: sube 1, baja 1 o se queda (1/4, 1/4, 1/2). Si toca un borde se queda ahí. */
static void martingala(unsigned char *p, int n, Azar *a) {
  int x = 128, parado = 0;
  for (int t = 0; t < n; t++) {
    p[t] = (unsigned char)x;
    if (parado) continue;
    int u = azar_entero(a, 4);
    x += u == 0 ? 1 : u == 1 ? -1 : 0;
    if (x <= 1 || x >= 255) parado = 1;
  }
}

/* ---- Pruebas -------------------------------------------------------------------------------- */

typedef struct { int lazo, futuro, uno, repetir, pruebas; double media, ee; int error; } Informe;

static Informe probar(const char *spec, int con_fuga) {
  Informe inf = {0, 0, 0, 0, 0, 0, 0, 0};
  const Reglas r = {CAJA0_DEF, COMISION_DEF}, sin_comision = {CAJA0_DEF, 0};
  Instancia *inst = instancia_crear(spec, NULL, 0);
  if (!inst) { inf.error = 1; return inf; }
  unsigned char *p = malloc(N), *q = malloc(N), *d0 = malloc(N), *d1 = malloc(N), *leidos = malloc(N);
  Azar a;
  azar_sembrar(&a, 987654321);
  for (int s = 0; s < SERIES; s++) {
    uint64_t sem = semilla_serie(instancia_spec(inst), s);
    serie(p, N, s, &a);
    Mia mia = mi_ronda(inst, p, N, &r, sem, d0, con_fuga);
    /* A: el arnés con la misma serie */
    Resultado res = correr_serie(inst, p, N, &r, sem, 0, leidos);
    int igual = !con_fuga ? (res.w == mia.w && res.ordenes == mia.ordenes && res.max_dd == mia.caida && leidos[0] == 0 &&
                             !memcmp(leidos + 1, d0, N - 1)) : 1;
    inf.lazo += !igual; inf.pruebas++;
    /* C: otra ronda entre medio y se repite */
    serie(q, N, s + 1, &a);
    mi_ronda(inst, q, N, &r, sem + 7, d1, con_fuga);
    mi_ronda(inst, p, N, &r, sem, d1, con_fuga);
    inf.repetir += memcmp(d0, d1, N) != 0; inf.pruebas++;
    /* B: futuro perturbado */
    for (int k = 0; k < CORTES; k++) {
      int T = k == 0 ? 0 : k == 1 ? 1 : k == 2 ? N - 2 : azar_entero(&a, N - 1);
      memcpy(q, p, N);
      for (int t = T + 1; t < N; t++) q[t] = (unsigned char)(1 + azar_entero(&a, 255));
      mi_ronda(inst, q, N, &r, sem, d1, con_fuga);
      inf.futuro += memcmp(d0, d1, (size_t)T + 1) != 0; inf.pruebas++;
      memcpy(q, p, N);                               /* solo el precio de ejecución de la orden emitida en T */
      q[T + 1] = (unsigned char)(p[T + 1] > 128 ? p[T + 1] - 100 : p[T + 1] + 100);
      mi_ronda(inst, q, N, &r, sem, d1, con_fuga);
      inf.uno += d0[T] != d1[T] || memcmp(d0, d1, (size_t)T + 1) != 0; inf.pruebas++;
    }
  }
  /* D: martingala sin comisión */
  double s1 = 0, s2 = 0;
  azar_sembrar(&a, 13579);
  for (int s = 0; s < MART; s++) {
    martingala(p, NM, &a);
    Mia mia = mi_ronda(inst, p, NM, &sin_comision, semilla_serie(instancia_spec(inst), 1000 + s), NULL, con_fuga);
    s1 += (double)mia.w; s2 += (double)mia.w * (double)mia.w;
  }
  inf.media = s1 / MART;
  double var = s2 / MART - inf.media * inf.media;
  inf.ee = sqrt((var > 0 ? var : 0) / (MART - 1));
  free(p); free(q); free(d0); free(d1); free(leidos);
  instancia_destruir(inst);
  return inf;
}

int main(void) {
  enum { MAXS = 400 };
  static const char *spec[MAXS];
  static Informe inf[MAXS];
  int n = 0;
  for (int k = 0; k < nucleo_nestrategias(); k++)
    if (strcmp(nucleo_estrategia(k)->nombre, "tramposa")) spec[n++] = nucleo_estrategia(k)->nombre;
  int n_estrategias = n;
  for (int k = 0; k < nucleo_nalias(); k++) spec[n++] = nucleo_alias_nombre(k);
  int n_alias = n - n_estrategias;
  for (int k = 0; k < nucleo_nrivales(); k++) spec[n++] = nucleo_rival_spec(k);
  int n_rivales = n - n_estrategias - n_alias;

#pragma omp parallel for num_threads(6) schedule(dynamic, 1)
  for (int k = 0; k < n; k++) inf[k] = probar(spec[k], 0);
  Informe control = probar("tramposa", 1), sin_fuga = probar("tramposa", 0);

  printf("Prueba independiente de informacion del futuro (lazo y contabilidad propios)\n");
  printf("%d estrategias (con parametros por defecto), %d alias y %d rivales. Por cada una: %d series de %d ticks,\n",
         n_estrategias, n_alias, n_rivales, SERIES, N);
  printf("%d cortes por serie con todo el futuro cambiado y %d con solo el precio de ejecucion cambiado.\n", CORTES, CORTES);
  printf("Martingala: %d series de %d ticks sin comision; z = (media - 10000) / error estandar.\n\n", MART, NM);
  printf("%-44s %6s %7s %7s %8s | %9s %6s %6s\n", "estrategia", "lazo", "futuro", "precio", "repetir", "martingala", "ee", "z");
  int fallas = 0, pruebas = 0, peor = -1;
  double zmax = 0;
  for (int k = 0; k < n; k++) {
    double z = inf[k].ee > 0 ? (inf[k].media - 10000) / inf[k].ee : 0;
    int f = inf[k].error + inf[k].lazo + inf[k].futuro + inf[k].uno + inf[k].repetir;
    printf("%-44s %6d %7d %7d %8d | %9.1f %6.1f %+6.2f%s\n", spec[k], inf[k].lazo, inf[k].futuro, inf[k].uno, inf[k].repetir,
           inf[k].media, inf[k].ee, z, inf[k].error ? "  ERROR al crearla" : "");
    fallas += f; pruebas += inf[k].pruebas;
    if (fabs(z) > zmax) { zmax = fabs(z); peor = k; }
  }
  printf("\nColumnas: comparaciones que fallan en cada prueba (lazo propio contra correr_serie, futuro cambiado,\n");
  printf("precio de ejecucion cambiado, ronda repetida).\n");
  printf("%s  %d estrategias, %d comparaciones, %d fallas\n", fallas ? "FAIL" : "PASS", n, pruebas, fallas);
  int mart_ok = zmax < 4.0;
  printf("%s  martingala: la mayor distancia a 10 000 es %.2f errores estandar (%s); limite 4\n", mart_ok ? "PASS" : "FAIL",
         zmax, peor >= 0 ? spec[peor] : "");

  double zc = control.ee > 0 ? (control.media - 10000) / control.ee : 0;
  int detectada = control.futuro > 0 && control.uno > 0 && zc > 4.0;
  printf("\nControl negativo: estrategia tramposa, que mira el precio de ejecucion y el siguiente por una fuga puesta a proposito\n");
  printf("  con la fuga:  futuro %d fallas, precio de ejecucion %d fallas, martingala %.0f (z = %+.0f)\n", control.futuro,
         control.uno, control.media, zc);
  printf("  sin la fuga:  futuro %d fallas, precio de ejecucion %d fallas, martingala %.0f (no opera)\n", sin_fuga.futuro,
         sin_fuga.uno, sin_fuga.media);
  printf("%s  las pruebas detectan a la tramposa\n", detectada ? "PASS" : "FAIL");
  return fallas || !mart_ok || !detectada;
}
