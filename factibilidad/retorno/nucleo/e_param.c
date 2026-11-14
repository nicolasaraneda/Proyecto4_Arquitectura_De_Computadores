/* e_param.c: la familia paramétrica de estrategias del frente del algoritmo, como módulo del arnés.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Es la misma estrategia de ref/candidatos.py (clase Trader) y de
 * ref/motor/motor.c, con los mismos parámetros y las mismas operaciones
 * enteras. Con los parámetros por defecto es la regla base de ref/trader.py.
 * pruebas/validar.py exige que coincida con las tres, serie por serie.
 *
 * Los alias "cand:..." son los candidatos de ref/candidatos.py y los extras
 * de ref/frontera.py. Los que terminan en "_r" son variantes para rondas
 * largas que se agregan en este estudio (ver README.md).
 */
#include "nucleo.h"

#include <string.h>

typedef struct {
  int est, k, ka, kb, k1a, k1b, k2a, k2b;
  int E, X;
  int kv, ev, xv, sv;
  int J;
  int tmax, stop, lock;
  int kg, g, gsal, nfal, gapag;
  int cap, capsh, capsh2, capoff, capini;
  int modo, p2, q1, E2;
} Cfg;

typedef struct {
  const Cfg *c;
  int ini, S, L, T, V, G, pant;
  int pos, etapa, t_dentro, p_entrada, bloqueo, espera;
  int perdida, apagado, compro, fallas, pausa;
  int buf[256], bi, suma;
  int n_veto, n_cortes, n_topes, n_pausas;         /* contadores para los informes */
} Estado;

static int configurar(void *cfg, const char *parametros, char *error, size_t tam_error) {
  Cfg *c = cfg;
  c->k = 5; c->E = 128; c->X = 0;
  c->ka = 5; c->kb = 7; c->k1a = 1; c->k1b = 3; c->k2a = 3; c->k2b = 4;
#define C(n) {#n, &c->n}
  const Campo campos[] = {C(est), C(k), C(ka), C(kb), C(k1a), C(k1b), C(k2a), C(k2b), C(E), C(X), C(kv), C(ev), C(xv),
                          C(sv), C(J), C(tmax), C(stop), C(lock), C(kg), C(g), C(gsal), C(nfal), C(gapag), C(cap),
                          C(capsh), C(capsh2), C(capoff), C(capini), C(modo), C(p2), C(q1), C(E2)};
#undef C
  if (leer_campos(parametros, campos, (int)(sizeof campos / sizeof campos[0]), error, tam_error)) return 1;
  if (c->k < 0 || c->k > 8) { strncpy(error, "k debe estar entre 0 y 8", tam_error); return 1; }
  return 0;
}

static void iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  (void)reglas; (void)semilla;
  ((Estado *)estado)->c = cfg;
}

#define ASR(x, s) ((x) >> (s))          /* desplazamiento aritmético (redondea hacia abajo) */
#define FK 8                            /* bits de fracción del Kalman */

static int decidir(void *estado, int pr, const Cuenta *propia) {
  Estado *s = estado;
  const Cfg *c = s->c;
  int dev, d;
  (void)propia;
  if (!s->ini) {
    s->ini = 1; s->pant = pr;
    s->S = pr << c->k; s->L = pr << FK; s->T = 0;
    if (c->est == 2) { for (int i = 0; i < (1 << c->k); i++) s->buf[i] = pr; s->suma = pr << c->k; }
  }
  d = pr - s->pant; s->pant = pr;
  int ad = d < 0 ? -d : d;
  if (c->J && ad >= c->J) {             /* salto: el nivel se corre con el precio */
    s->S += d << c->k; s->L += d << FK;
    if (c->est == 2) { for (int i = 0; i < (1 << c->k); i++) s->buf[i] += d; s->suma += d << c->k; }
    ad = 0;
  }
  if (c->est == 0) {
    dev = (pr << c->k) - s->S;
    s->S = s->S + ASR(dev, c->k);
  } else if (c->est == 2) {
    dev = (pr << c->k) - s->suma;
    s->suma += pr - s->buf[s->bi]; s->buf[s->bi] = pr; s->bi = (s->bi + 1) & ((1 << c->k) - 1);
  } else {
    int Tp = s->T - ASR(s->T, c->ka) - (c->kb ? ASR(s->T, c->kb) : 0);
    int e = (pr << FK) - s->L - Tp;
    s->L = s->L + ASR(e, c->k1a) + (c->k1b ? ASR(e, c->k1b) : 0);
    s->T = Tp + ASR(e, c->k2a) + (c->k2b ? ASR(e, c->k2b) : 0);
    dev = s->T;
  }
  int Eef = c->E, Xef = c->X;
  if (c->kv) {
    Eef += ASR(c->ev * s->V, c->sv);
    Xef += ASR(c->xv * s->V, c->sv);
    s->V = s->V + ad - ASR(s->V + (1 << c->kv) - 1, c->kv);
  }
  int guardia = 0;
  if (c->kg) {
    guardia = s->G < -c->g;
    s->G = s->G + ASR(dev - s->G, c->kg);
  }
  if (s->apagado > 0) { s->apagado--; if (s->apagado == 0) s->perdida = 0; }
  if (s->pausa > 0) s->pausa--;
  int veto = guardia || s->apagado != 0 || s->pausa != 0;
  if (s->bloqueo > 0) s->bloqueo--;

  int entra = dev < -Eef;
  int sale = dev > Xef;
  if (s->espera && sale) s->espera = 0;     /* después de un corte espera a que el precio recupere la media */
  int corte = 0, tope = 0;
  if (s->pos) {
    s->t_dentro++;
    if (c->tmax && s->t_dentro > c->tmax) corte = 1;
    if (c->stop && pr <= s->p_entrada - c->stop) corte = 1;
    if (guardia && c->gsal) corte = 1;
    /* tope de pérdida: caída acumulada desde el mejor momento, contando la posición abierta */
    if ((c->cap || c->capsh) && s->perdida + (pr - s->p_entrada) <
        -(c->cap + (c->capsh ? (pr >> c->capsh) : 0) + (c->capsh2 ? (pr >> c->capsh2) : 0))) tope = 1;
  }
  if (s->pos && (sale || corte || tope)) {
    s->pos = 0; s->etapa = 0;
    s->perdida += pr - s->p_entrada;
    if (s->perdida > 0 && !c->capini) s->perdida = 0;   /* desde el mejor momento: una ganancia la deja en cero */
    if (corte && !sale) {
      s->n_cortes++;
      if (c->lock) s->bloqueo = c->lock; else s->espera = 1;
      s->fallas++;
      if (c->nfal && s->fallas >= c->nfal) { s->pausa = c->gapag; s->fallas = 0; s->n_pausas++; }
    } else if (!tope) s->fallas = 0;
    if (tope) { s->apagado = c->capoff ? c->capoff : 0x7fffffff; s->n_topes++; }
  } else if (!s->pos && entra && !sale && !veto && !s->bloqueo && !s->espera) {
    s->pos = 1; s->etapa = 1; s->t_dentro = 0; s->p_entrada = pr; s->compro = 0;
  }
  if (s->pos && c->q1 && s->etapa == 1 && dev < -c->E2) s->etapa = 2;
  s->n_veto += veto;

  int decision;
  if (!s->pos) decision = VENDER_63;
  else if (c->q1 && s->etapa == 1) { decision = s->compro ? MANTENER : COMPRAR(c->q1); s->compro = 1; }
  else if (c->modo == 1) { decision = s->compro ? MANTENER : COMPRAR_63; s->compro = 1; }
  else if (c->modo == 2) { decision = (s->compro && pr > c->p2) ? MANTENER : COMPRAR_63; s->compro = 1; }
  else decision = COMPRAR_63;
  return decision;
}

/* aux: ticks sin poder entrar (guardia, pausa o tope), cortes de posición, topes de pérdida, pausas de la guardia */
static void contadores(const void *estado, int aux[4]) {
  const Estado *s = estado;
  aux[0] = s->n_veto; aux[1] = s->n_cortes; aux[2] = s->n_topes; aux[3] = s->n_pausas;
}

static const Estrategia param = {
  "param", "familia parametrica del frente del algoritmo (ref/candidatos.py). Sin parametros es la regla base",
  sizeof(Cfg), sizeof(Estado), configurar, iniciar, decidir, contadores, NULL};
REGISTRAR_ESTRATEGIA(param)

#define SALTOS "J=8"
#define GUARDIA "tmax=48,nfal=3,gapag=1000"

static void __attribute__((constructor)) alias_param(void) {
  /* candidatos de ref/candidatos.py */
  nucleo_alias("cand:base", "param:E=128,X=0", "regla base: entra 4 bajo la media, sale al recuperarla");
  nucleo_alias("cand:max_media", "param:E=96,X=0", "entra 3 bajo la media, sale al recuperarla, sin proteccion");
  nucleo_alias("cand:guardia", "param:E=96,X=0," SALTOS "," GUARDIA, "max_media con manejo de saltos y guardia de regimen");
  nucleo_alias("cand:guardia_tope", "param:E=96,X=0," SALTOS "," GUARDIA ",capsh=1", "max_media con saltos, guardia y tope de perdida");
  nucleo_alias("cand:prudente", "param:E=192,X=-32", "entra 6 bajo la media, sale 1 antes de recuperarla");
  nucleo_alias("cand:kalman", "param:est=1,E=190,X=-40", "Kalman de dos estados con bandas equivalentes a max_media");
  /* extras de ref/frontera.py */
  nucleo_alias("cand:kalman_base", "param:est=1,E=250,X=-40", "Kalman de dos estados con bandas equivalentes a la regla base");
  nucleo_alias("cand:activo", "param:E=64,X=16", "entra 2 bajo la media, sale medio punto sobre ella");
  nucleo_alias("cand:base_guardia", "param:E=128,X=0," SALTOS "," GUARDIA, "regla base con saltos y guardia");
  nucleo_alias("cand:base_tope", "param:E=128,X=0," SALTOS "," GUARDIA ",capsh=1", "regla base con saltos, guardia y tope");
  nucleo_alias("cand:base_fuerte", "param:E=128,X=0,J=8,tmax=48,nfal=2,gapag=1000,capsh=2", "regla base con guardia sensible y tope de 25 %");
  nucleo_alias("cand:prud_guardia", "param:E=192,X=-32," SALTOS "," GUARDIA, "prudente con saltos y guardia");
  /* variantes para rondas largas, definidas antes de mirar ningún resultado: el tope se rearma */
  nucleo_alias("cand:guardia_tope_r", "param:E=96,X=0," SALTOS "," GUARDIA ",capsh=1,capoff=2000",
               "guardia_tope con el tope rearmado a los 2000 ticks");
  nucleo_alias("cand:base_tope_r", "param:E=128,X=0," SALTOS "," GUARDIA ",capsh=1,capoff=2000",
               "base_tope con el tope rearmado a los 2000 ticks");
}
