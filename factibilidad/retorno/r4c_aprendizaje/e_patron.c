/* e_patron.c: estrategias que usan el predictor de patrones de pred.h.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Dos estrategias del arnés de retorno. No son parte del diseño ni del
 * programa de la placa.
 *
 *   patron     opera solo con el predictor: compra cuando predice una subida
 *              con el contador saturado y vende cuando predice una baja
 *              saturada. Es la estrategia experimental pura.
 *   mm_patron  es max_media con el predictor como filtro: posterga una
 *              entrada mientras el predictor anuncia otra baja después de la
 *              ejecución (fe) y posterga una salida mientras anuncia otra
 *              subida (fs), a lo más `maxp` ticks. Con el aprendizaje apagado
 *              (apr=0) y fe, fs en 0 o 2 los contadores nunca se saturan y la
 *              estrategia es max_media tick a tick.
 *
 * Parámetros del predictor (los dos): H, sim, bits, tipo, h, shd, lgd, apr.
 * Ver pred.h.
 */
#include <stdio.h>
#include <string.h>

#include "nucleo.h"
#include "pred.h"

/* ---- patron: el predictor solo ---------------------------------------------------------- */

typedef struct {
  PredCfg p;
  int k, ne, ns, tmin;
} CfgPatron;

typedef struct {
  const CfgPatron *c;
  int ini, S, pos, t_pos, n_ent, n_fuerte;
  Pred pred;
} EstPatron;

#define CAMPOS_PRED(c) {"H", &(c)->p.H}, {"sim", &(c)->p.sim}, {"bits", &(c)->p.bits}, {"tipo", &(c)->p.tipo}, \
                       {"h", &(c)->p.h}, {"shd", &(c)->p.shd}, {"lgd", &(c)->p.lgd}, {"apr", &(c)->p.apr}

static int patron_configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  CfgPatron *c = cfg;
  pred_defecto(&c->p);
  c->k = 5; c->ne = 2; c->ns = 2; c->tmin = 0;
  const Campo campos[] = {CAMPOS_PRED(c), {"k", &c->k}, {"ne", &c->ne}, {"ns", &c->ns}, {"tmin", &c->tmin}};
  if (leer_campos(parametros, campos, (int)(sizeof campos / sizeof campos[0]), error, tam)) return 1;
  const char *mal = pred_validar(&c->p);
  if (!mal && (c->ne < 1 || c->ne > 2 || c->ns < 1 || c->ns > 2)) mal = "ne y ns deben ser 1 o 2";
  if (!mal && (c->k < 1 || c->k > 8)) mal = "k debe estar entre 1 y 8";
  if (mal) { snprintf(error, tam, "patron: %s", mal); return 1; }
  return 0;
}

static void patron_iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  (void)reglas; (void)semilla;
  ((EstPatron *)estado)->c = cfg;
}

static int patron_decidir(void *estado, int pr, const Cuenta *propia) {
  EstPatron *s = estado;
  const CfgPatron *c = s->c;
  (void)propia;
  if (!s->ini) { s->ini = 1; s->S = pr << c->k; }
  int dev = (pr << c->k) - s->S;
  s->S += dev >> c->k;
  int pd = pred_paso(&s->pred, &c->p, pr, dev);
  if (pd == 2 || pd == -2) s->n_fuerte++;
  s->t_pos++;
  if (!s->pos && pd >= c->ne && s->t_pos > c->tmin) { s->pos = 1; s->t_pos = 0; s->n_ent++; }
  else if (s->pos && pd <= -c->ns && s->t_pos > c->tmin) { s->pos = 0; s->t_pos = 0; }
  return s->pos ? COMPRAR_63 : VENDER_63;
}

static void patron_contadores(const void *estado, int aux[4]) {
  const EstPatron *s = estado;
  aux[0] = s->n_fuerte; aux[1] = s->n_ent; aux[2] = 0; aux[3] = 0;
}

static const Estrategia patron = {
  "patron", "opera solo con el predictor de patrones (r4c): compra con subida saturada, vende con baja saturada",
  sizeof(CfgPatron), sizeof(EstPatron), patron_configurar, patron_iniciar, patron_decidir, patron_contadores, NULL};
REGISTRAR_ESTRATEGIA(patron)

/* ---- mm_patron: max_media con el predictor como filtro --------------------------------- */

typedef struct {
  PredCfg p;
  int k, E, X, fe, fs, maxp, cmp;
  Instancia *ref;
} CfgFiltro;

typedef struct {
  const CfgFiltro *c;
  int ini, S, regla, pos, espera, n_post, n_ent, n_cmp;
  Pred pred;
} EstFiltro;

static int filtro_configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  CfgFiltro *c = cfg;
  pred_defecto(&c->p);
  c->k = 5; c->E = 96; c->X = 0; c->fe = 2; c->fs = 0; c->maxp = 4;
  const Campo campos[] = {CAMPOS_PRED(c), {"k", &c->k}, {"E", &c->E}, {"X", &c->X}, {"fe", &c->fe}, {"fs", &c->fs},
                          {"maxp", &c->maxp}, {"cmp", &c->cmp}};
  if (leer_campos(parametros, campos, (int)(sizeof campos / sizeof campos[0]), error, tam)) return 1;
  const char *mal = pred_validar(&c->p);
  if (!mal && (c->fe < 0 || c->fe > 2 || c->fs < 0 || c->fs > 2)) mal = "fe y fs deben ser 0, 1 o 2";
  if (!mal && (c->k < 1 || c->k > 8)) mal = "k debe estar entre 1 y 8";
  if (mal) { snprintf(error, tam, "mm_patron: %s", mal); return 1; }
  if (c->cmp && !(c->ref = instancia_crear("cand:max_media", error, tam))) return 1;
  return 0;
}

static void filtro_liberar(void *cfg) {
  CfgFiltro *c = cfg;
  if (c->ref) instancia_destruir(c->ref);
}

static void filtro_iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  EstFiltro *s = estado;
  s->c = cfg;
  if (s->c->ref) instancia_iniciar(s->c->ref, reglas, semilla);
}

static int filtro_decidir(void *estado, int pr, const Cuenta *propia) {
  EstFiltro *s = estado;
  const CfgFiltro *c = s->c;
  if (!s->ini) { s->ini = 1; s->S = pr << c->k; }
  int dev = (pr << c->k) - s->S;
  s->S += dev >> c->k;
  if (s->regla) { if (dev > c->X) s->regla = 0; }          /* la posición que quiere max_media */
  else if (dev < -c->E) s->regla = 1;
  int pd = pred_paso(&s->pred, &c->p, pr, dev);
  if (s->pos == s->regla) s->espera = 0;
  else {
    int objeta = s->regla ? (c->fe && pd <= -c->fe) : (c->fs && pd >= c->fs);
    if (objeta && (!c->maxp || s->espera < c->maxp)) { s->espera++; s->n_post++; }
    else { s->pos = s->regla; s->espera = 0; s->n_ent += s->pos; }
  }
  int decision = s->pos ? COMPRAR_63 : VENDER_63;
  if (c->ref && instancia_decidir(c->ref, pr, propia) != decision) s->n_cmp++;
  return decision;
}

/* aux: ticks postergados, entradas, 0 y ticks distintos de max_media (cmp=1). */
static void filtro_contadores(const void *estado, int aux[4]) {
  const EstFiltro *s = estado;
  aux[0] = s->n_post; aux[1] = s->n_ent; aux[2] = 0; aux[3] = s->n_cmp;
}

static const Estrategia mm_patron = {
  "mm_patron", "max_media con el predictor de patrones como filtro de entradas y salidas (r4c). Con apr=0 es max_media",
  sizeof(CfgFiltro), sizeof(EstFiltro), filtro_configurar, filtro_iniciar, filtro_decidir, filtro_contadores,
  filtro_liberar};
REGISTRAR_ESTRATEGIA(mm_patron)
