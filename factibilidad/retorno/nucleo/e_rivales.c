/* e_rivales.c: rivales plausibles para el torneo simulado.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Son las estrategias que el enunciado sugiere y las que se le ocurren primero
 * a un grupo del curso: cruce de medias, momentum, comprar y mantener, no
 * operar, reversión simple y azar. Cada una tiene varias parametrizaciones y
 * tres formas ingenuas de dimensionar la orden:
 *
 *   q=63 rep=1   repite "comprar 63" o "vender 63" en cada tick: es una
 *                posición objetivo, la maestra recorta y no cobra de más.
 *   q=63 rep=0   una sola orden de 63 acciones al cambiar la señal: queda
 *                invertido cerca del 80 % de la caja.
 *   q=10 rep=1   10 acciones por tick mientras dure la señal: entra y sale en
 *                varias órdenes y paga comisión en cada una.
 *
 * La lista de rivales (al final del archivo) se fijó antes de mirar ningún
 * resultado del torneo. `reversion:k=5,a=4,b=0` con q=63 y rep=1 es
 * exactamente nuestra regla base: un grupo que ajuste una reversión con la
 * serie de práctica llega a ella o a un vecino.
 */
#include "nucleo.h"

#include <string.h>

#define VENTANA 256

/* ---- Tamaño de la orden, común a todos ------------------------------------------------- */

typedef struct { int q, rep; } Orden;

/* `quiere` es 1 (adentro) o 0 (afuera). `pos` guarda lo último que se pidió. */
static int ordenar(const Orden *o, int *pos, int quiere) {
  if (o->rep) { *pos = quiere; return quiere ? COMPRAR(o->q) : VENDER(o->q); }
  if (quiere == *pos) return MANTENER;
  *pos = quiere;
  return quiere ? COMPRAR(o->q) : VENDER(o->q);
}

static int revisar_orden(const Orden *o, char *error, size_t tam) {
  if (o->q < 1 || o->q > 63) { strncpy(error, "q debe estar entre 1 y 63", tam); return 1; }
  return 0;
}

/* ---- Cruce de medias: adentro si la media rápida está sobre la lenta ------------------- */

typedef struct { int tipo, r, l, kr, kl, h; Orden o; } CfgCruce;   /* tipo 0: ventanas r y l. tipo 1: alfa 1/2^kr y 1/2^kl */
typedef struct { const CfgCruce *c; int ini, pos, quiere, bi, sr, sl, F, S; unsigned char buf[VENTANA]; } EstCruce;

static int cruce_cfg(void *cfg, const char *par, char *error, size_t tam) {
  CfgCruce *c = cfg;
  c->r = 5; c->l = 20; c->kr = 2; c->kl = 5; c->o.q = 63; c->o.rep = 1;
  const Campo campos[] = {{"tipo", &c->tipo}, {"r", &c->r}, {"l", &c->l}, {"kr", &c->kr}, {"kl", &c->kl}, {"h", &c->h},
                          {"q", &c->o.q}, {"rep", &c->o.rep}};
  if (leer_campos(par, campos, 8, error, tam)) return 1;
  if (c->r < 1 || c->l <= c->r || c->l > VENTANA || c->kr < 0 || c->kl <= c->kr || c->kl > 10) {
    strncpy(error, "cruce: hace falta 1 <= r < l <= 256 y 0 <= kr < kl <= 10", tam); return 1;
  }
  return revisar_orden(&c->o, error, tam);
}

static void cruce_ini(void *estado, const void *cfg, const Reglas *r, uint64_t semilla) {
  (void)r; (void)semilla;
  ((EstCruce *)estado)->c = cfg;
}

static int cruce_decidir(void *estado, int p, const Cuenta *propia) {
  EstCruce *s = estado;
  const CfgCruce *c = s->c;
  long long rapida, lenta, banda;
  (void)propia;
  if (c->tipo == 0) {
    if (!s->ini) { s->ini = 1; memset(s->buf, p, sizeof s->buf); s->sr = p * c->r; s->sl = p * c->l; }
    s->sr += p - s->buf[(s->bi - c->r) & (VENTANA - 1)];
    s->sl += p - s->buf[(s->bi - c->l) & (VENTANA - 1)];
    s->buf[s->bi] = (unsigned char)p; s->bi = (s->bi + 1) & (VENTANA - 1);
    rapida = (long long)s->sr * c->l; lenta = (long long)s->sl * c->r; banda = (long long)c->h * c->r * c->l;
  } else {
    if (!s->ini) { s->ini = 1; s->F = p << c->kr; s->S = p << c->kl; }
    s->F += ((p << c->kr) - s->F) >> c->kr;
    s->S += ((p << c->kl) - s->S) >> c->kl;
    rapida = (long long)s->F << (c->kl - c->kr); lenta = s->S; banda = (long long)c->h << c->kl;
  }
  if (rapida > lenta + banda) s->quiere = 1;
  else if (rapida < lenta - banda) s->quiere = 0;
  return ordenar(&c->o, &s->pos, s->quiere);
}

static const Estrategia cruce = {"cruce", "rival: cruce de medias (sigue la tendencia). tipo, r, l, kr, kl, h, q, rep",
                                 sizeof(CfgCruce), sizeof(EstCruce), cruce_cfg, cruce_ini, cruce_decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(cruce)

/* ---- Momentum: adentro si el precio subió u o más en los últimos h ticks --------------- */
/* Con inv=1 la señal se invierte: compra lo que cayó (una reversión ingenua). */

typedef struct { int h, u, inv; Orden o; } CfgMom;
typedef struct { const CfgMom *c; int ini, pos, quiere, bi; unsigned char buf[VENTANA]; } EstMom;

static int mom_cfg(void *cfg, const char *par, char *error, size_t tam) {
  CfgMom *c = cfg;
  c->h = 10; c->u = 2; c->o.q = 63; c->o.rep = 1;
  const Campo campos[] = {{"h", &c->h}, {"u", &c->u}, {"inv", &c->inv}, {"q", &c->o.q}, {"rep", &c->o.rep}};
  if (leer_campos(par, campos, 5, error, tam)) return 1;
  if (c->h < 1 || c->h >= VENTANA || c->u < 1) { strncpy(error, "momentum: hace falta 1 <= h < 256 y u >= 1", tam); return 1; }
  return revisar_orden(&c->o, error, tam);
}

static void mom_ini(void *estado, const void *cfg, const Reglas *r, uint64_t semilla) {
  (void)r; (void)semilla;
  ((EstMom *)estado)->c = cfg;
}

static int mom_decidir(void *estado, int p, const Cuenta *propia) {
  EstMom *s = estado;
  const CfgMom *c = s->c;
  (void)propia;
  if (!s->ini) { s->ini = 1; memset(s->buf, p, sizeof s->buf); }
  int d = p - s->buf[(s->bi - c->h) & (VENTANA - 1)];
  s->buf[s->bi] = (unsigned char)p; s->bi = (s->bi + 1) & (VENTANA - 1);
  if (c->inv) d = -d;
  if (d >= c->u) s->quiere = 1;
  else if (d <= -c->u) s->quiere = 0;
  return ordenar(&c->o, &s->pos, s->quiere);
}

static const Estrategia momentum = {"momentum", "rival: momentum de h ticks con umbral u (inv=1: al reves). h, u, inv, q, rep",
                                    sizeof(CfgMom), sizeof(EstMom), mom_cfg, mom_ini, mom_decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(momentum)

/* ---- Comprar y mantener ------------------------------------------------------------------ */

typedef struct { Orden o; } CfgByh;
typedef struct { const CfgByh *c; int pos; } EstByh;

static int byh_cfg(void *cfg, const char *par, char *error, size_t tam) {
  CfgByh *c = cfg;
  c->o.q = 63; c->o.rep = 1;
  const Campo campos[] = {{"q", &c->o.q}, {"rep", &c->o.rep}};
  if (leer_campos(par, campos, 2, error, tam)) return 1;
  return revisar_orden(&c->o, error, tam);
}

static void byh_ini(void *estado, const void *cfg, const Reglas *r, uint64_t semilla) {
  (void)r; (void)semilla;
  ((EstByh *)estado)->c = cfg;
}

static int byh_decidir(void *estado, int p, const Cuenta *propia) {
  EstByh *s = estado;
  (void)p; (void)propia;
  return ordenar(&s->c->o, &s->pos, 1);
}

static const Estrategia byh = {"byh", "rival: comprar y mantener hecho por el programa. q, rep",
                               sizeof(CfgByh), sizeof(EstByh), byh_cfg, byh_ini, byh_decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(byh)

/* ---- No operar ----------------------------------------------------------------------------- */

static int nada_decidir(void *estado, int p, const Cuenta *propia) {
  (void)estado; (void)p; (void)propia;
  return MANTENER;
}

static const Estrategia nada = {"nada", "rival: no operar", 0, 0, NULL, NULL, nada_decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(nada)

/* ---- Reversión simple: compra bajo la media, vende sobre ella ---------------------------- */
/* tipo 0: media exponencial con alfa 1/2^k. tipo 1: suma móvil de n precios.
 * Entra si el precio está más de `a` bajo la media y sale si está más de `b`
 * sobre ella. Con tipo=0, q=63 y rep=1 es la familia de la regla base. */

typedef struct { int tipo, k, n, a, b; Orden o; } CfgRev;
typedef struct { const CfgRev *c; int ini, pos, quiere, bi, S, suma; unsigned char buf[VENTANA]; } EstRev;

static int rev_cfg(void *cfg, const char *par, char *error, size_t tam) {
  CfgRev *c = cfg;
  c->k = 5; c->n = 64; c->a = 4; c->b = 0; c->o.q = 63; c->o.rep = 1;
  const Campo campos[] = {{"tipo", &c->tipo}, {"k", &c->k}, {"n", &c->n}, {"a", &c->a}, {"b", &c->b},
                          {"q", &c->o.q}, {"rep", &c->o.rep}};
  if (leer_campos(par, campos, 7, error, tam)) return 1;
  if (c->k < 1 || c->k > 10 || c->n < 2 || c->n > VENTANA || c->a + c->b < 0) {
    strncpy(error, "reversion: hace falta 1 <= k <= 10, 2 <= n <= 256 y a + b >= 0", tam); return 1;
  }
  return revisar_orden(&c->o, error, tam);
}

static void rev_ini(void *estado, const void *cfg, const Reglas *r, uint64_t semilla) {
  (void)r; (void)semilla;
  ((EstRev *)estado)->c = cfg;
}

static int rev_decidir(void *estado, int p, const Cuenta *propia) {
  EstRev *s = estado;
  const CfgRev *c = s->c;
  int dev, escala;
  (void)propia;
  if (c->tipo == 0) {
    if (!s->ini) { s->ini = 1; s->S = p << c->k; }
    dev = (p << c->k) - s->S; escala = 1 << c->k;
    s->S += dev >> c->k;
  } else {
    if (!s->ini) { s->ini = 1; memset(s->buf, p, sizeof s->buf); s->suma = p * c->n; }
    dev = c->n * p - s->suma; escala = c->n;
    s->suma += p - s->buf[(s->bi - c->n) & (VENTANA - 1)];
    s->buf[s->bi] = (unsigned char)p; s->bi = (s->bi + 1) & (VENTANA - 1);
  }
  int entra = dev < -c->a * escala, sale = dev > c->b * escala;
  if (s->quiere && sale) s->quiere = 0;
  else if (!s->quiere && entra && !sale) s->quiere = 1;
  return ordenar(&c->o, &s->pos, s->quiere);
}

static const Estrategia reversion = {"reversion", "rival: reversion simple a la media. tipo, k, n, a, b, q, rep",
                                     sizeof(CfgRev), sizeof(EstRev), rev_cfg, rev_ini, rev_decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(reversion)

/* ---- Azar: con probabilidad pm/1000 por tick manda una orden de compra o de venta ------- */

typedef struct { int pm, q; } CfgAzar;
typedef struct { const CfgAzar *c; Azar rng; } EstAzar;

static int azar_cfg(void *cfg, const char *par, char *error, size_t tam) {
  CfgAzar *c = cfg;
  c->pm = 100; c->q = 63;
  const Campo campos[] = {{"pm", &c->pm}, {"q", &c->q}};
  if (leer_campos(par, campos, 2, error, tam)) return 1;
  if (c->pm < 0 || c->pm > 1000 || c->q < 1 || c->q > 63) { strncpy(error, "azar: 0 <= pm <= 1000 y 1 <= q <= 63", tam); return 1; }
  return 0;
}

static void azar_ini(void *estado, const void *cfg, const Reglas *r, uint64_t semilla) {
  EstAzar *s = estado;
  (void)r;
  s->c = cfg;
  azar_sembrar(&s->rng, semilla);
}

static int azar_decidir(void *estado, int p, const Cuenta *propia) {
  EstAzar *s = estado;
  (void)p; (void)propia;
  if (azar_entero(&s->rng, 1000) >= s->c->pm) return MANTENER;
  return azar_entero(&s->rng, 2) ? COMPRAR(s->c->q) : VENDER(s->c->q);
}

static const Estrategia azar = {"azar", "rival: ordenes al azar. pm (probabilidad por mil de operar en un tick), q",
                                sizeof(CfgAzar), sizeof(EstAzar), azar_cfg, azar_ini, azar_decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(azar)

/* ---- La lista de rivales -------------------------------------------------------------------- */

static void __attribute__((constructor)) lista_de_rivales(void) {
  static const char *cruces[] = {
    "cruce:tipo=1,kr=1,kl=3", "cruce:tipo=1,kr=2,kl=4", "cruce:tipo=1,kr=2,kl=5", "cruce:tipo=1,kr=3,kl=5",
    "cruce:tipo=1,kr=3,kl=6", "cruce:tipo=1,kr=4,kl=6",
    "cruce:tipo=1,kr=2,kl=5,q=63,rep=0", "cruce:tipo=1,kr=2,kl=5,q=10,rep=1",
    "cruce:tipo=1,kr=3,kl=6,q=63,rep=0", "cruce:tipo=1,kr=3,kl=6,q=10,rep=1",
    "cruce:tipo=0,r=5,l=20", "cruce:tipo=0,r=10,l=50", "cruce:tipo=0,r=20,l=100", "cruce:tipo=0,r=5,l=20,h=1", NULL};
  static const char *momentums[] = {
    "momentum:h=1,u=1", "momentum:h=1,u=2", "momentum:h=5,u=2", "momentum:h=10,u=2", "momentum:h=10,u=3",
    "momentum:h=20,u=3", "momentum:h=50,u=4",
    "momentum:h=5,u=2,q=63,rep=0", "momentum:h=5,u=2,q=10,rep=1",
    "momentum:h=10,u=3,q=63,rep=0", "momentum:h=10,u=3,q=10,rep=1", NULL};
  static const char *byhs[] = {"byh:q=63,rep=1", "byh:q=63,rep=0", "byh:q=10,rep=1", "byh:q=20,rep=0", NULL};
  static const char *nadas[] = {"nada", NULL};
  static const char *reversiones[] = {
    "reversion:k=3,a=2,b=0", "reversion:k=4,a=2,b=0", "reversion:k=4,a=3,b=0", "reversion:k=4,a=4,b=1",
    "reversion:k=5,a=2,b=0", "reversion:k=5,a=3,b=0", "reversion:k=5,a=4,b=0", "reversion:k=5,a=4,b=1",
    "reversion:k=5,a=6,b=0", "reversion:k=5,a=3,b=1", "reversion:k=6,a=3,b=0", "reversion:k=6,a=4,b=0",
    "reversion:k=6,a=6,b=1",
    "reversion:k=5,a=4,b=0,q=63,rep=0", "reversion:k=5,a=4,b=0,q=10,rep=1",
    "reversion:k=5,a=3,b=0,q=63,rep=0", "reversion:k=5,a=3,b=0,q=10,rep=1",
    "reversion:k=4,a=3,b=0,q=63,rep=0", "reversion:k=4,a=3,b=0,q=10,rep=1",
    "reversion:tipo=1,n=20,a=3,b=0", "reversion:tipo=1,n=50,a=4,b=0", "reversion:tipo=1,n=64,a=4,b=1",
    "momentum:inv=1,h=1,u=2", "momentum:inv=1,h=5,u=3", "momentum:inv=1,h=10,u=4", NULL};
  static const char *azares[] = {"azar:pm=1000,q=63", "azar:pm=1000,q=10", "azar:pm=100,q=63", "azar:pm=100,q=10",
                                 "azar:pm=10,q=63", "azar:pm=10,q=10", NULL};
  static const struct { const char *clase; const char **lista; } clases[] = {
    {"cruce", cruces}, {"momentum", momentums}, {"comprar_y_mantener", byhs}, {"no_operar", nadas},
    {"reversion", reversiones}, {"azar", azares}};
  for (size_t k = 0; k < sizeof clases / sizeof clases[0]; k++)
    for (const char **s = clases[k].lista; *s; s++) nucleo_rival(clases[k].clase, *s);
}
