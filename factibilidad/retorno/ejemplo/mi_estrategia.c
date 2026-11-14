/* mi_estrategia.c: ejemplo de cómo agregar estrategias al arnés sin tocar el núcleo.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Trae dos estrategias de juguete. No son candidatas: están para mostrar la
 * interfaz completa y para probar que un archivo de otra carpeta compila
 * contra el núcleo.
 *
 *   ejemplo    reversión como la regla base, pero dimensiona la orden con su
 *              propia cuenta: pide las acciones que le alcanzan y deja de
 *              pedir cuando ya no puede comprar. Muestra parámetros, estado y
 *              el uso de `propia`.
 *   seguidor   corre varias estrategias en papel, cada una con su cuenta, y
 *              copia la decisión de la que lleva más patrimonio. Muestra cómo
 *              usar otras estrategias por dentro (instancias) y cómo llevar
 *              cuentas en papel con cuenta_ejecutar.
 *
 * Compilar y probar: make -C factibilidad/retorno/ejemplo probar
 */
#include <stdio.h>
#include <string.h>

#include "nucleo.h"

/* ---- ejemplo: una estrategia simple que mira su cuenta ---------------------------------- */

typedef struct { int k, entra, sale; } CfgEjemplo;                 /* parámetros */
typedef struct { const CfgEjemplo *c; Reglas reglas; int ini, S, pos; } EstEjemplo;   /* estado de una ronda */

static int ejemplo_configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  CfgEjemplo *c = cfg;
  c->k = 5; c->entra = 4; c->sale = 0;                             /* valores por defecto */
  const Campo campos[] = {{"k", &c->k}, {"entra", &c->entra}, {"sale", &c->sale}};
  if (leer_campos(parametros, campos, 3, error, tam)) return 1;
  if (c->k < 1 || c->k > 8) { snprintf(error, tam, "ejemplo: k debe estar entre 1 y 8"); return 1; }
  return 0;
}

static void ejemplo_iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  EstEjemplo *s = estado;                                          /* llega en cero */
  (void)semilla;                                                   /* no usa azar */
  s->c = cfg;
  s->reglas = *reglas;
}

static int ejemplo_decidir(void *estado, int precio, const Cuenta *propia) {
  EstEjemplo *s = estado;
  const CfgEjemplo *c = s->c;
  if (!s->ini) { s->ini = 1; s->S = precio << c->k; }
  int dev = (precio << c->k) - s->S;                               /* desviación respecto a la media, por 2^k */
  s->S += dev >> c->k;
  if (dev < -(c->entra << c->k)) s->pos = 1;
  else if (dev > (c->sale << c->k)) s->pos = 0;

  if (!s->pos) return propia->acciones > 0 ? VENDER(propia->acciones > 63 ? 63 : propia->acciones) : MANTENER;
  int alcanza = (propia->caja - s->reglas.comision) / precio;      /* lo que podría comprar a este precio */
  if (alcanza <= 0) return MANTENER;
  return COMPRAR(alcanza > 63 ? 63 : alcanza);
}

static const Estrategia ejemplo = {
  "ejemplo", "ejemplo: reversion que dimensiona la orden con su propia cuenta. k, entra, sale",
  sizeof(CfgEjemplo), sizeof(EstEjemplo), ejemplo_configurar, ejemplo_iniciar, ejemplo_decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(ejemplo)

/* ---- seguidor: varias estrategias en papel y se copia a la que va ganando ------------- */

#define SEGUIDAS 3
typedef struct { Instancia *sub[SEGUIDAS]; } CfgSeguidor;
typedef struct {
  const CfgSeguidor *c;
  Reglas reglas;
  Cuenta papel[SEGUIDAS];        /* la cuenta que tendría cada una si operara sola */
  int decision[SEGUIDAS];        /* lo último que decidió cada una */
  int lider, cambios;
} EstSeguidor;

static int seguidor_configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  static const char *seguidas[SEGUIDAS] = {"cand:base", "cand:max_media", "cand:prudente"};
  CfgSeguidor *c = cfg;
  if (parametros && *parametros) { snprintf(error, tam, "seguidor no tiene parametros"); return 1; }
  for (int k = 0; k < SEGUIDAS; k++)
    if (!(c->sub[k] = instancia_crear(seguidas[k], error, tam))) return 1;
  return 0;
}

static void seguidor_liberar(void *cfg) {
  CfgSeguidor *c = cfg;
  for (int k = 0; k < SEGUIDAS; k++) instancia_destruir(c->sub[k]);
}

static void seguidor_iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  EstSeguidor *s = estado;
  s->c = cfg;
  s->reglas = *reglas;
  for (int k = 0; k < SEGUIDAS; k++) {
    instancia_iniciar(s->c->sub[k], reglas, semilla + (uint64_t)k);
    cuenta_iniciar(&s->papel[k], reglas);
    s->decision[k] = MANTENER;
  }
}

static int seguidor_decidir(void *estado, int precio, const Cuenta *propia) {
  EstSeguidor *s = estado;
  (void)propia;
  for (int k = 0; k < SEGUIDAS; k++) {
    cuenta_ejecutar(&s->papel[k], &s->reglas, s->decision[k], precio);     /* su orden anterior, a este precio */
    s->decision[k] = instancia_decidir(s->c->sub[k], precio, &s->papel[k]);
  }
  int mejor = s->lider;
  for (int k = 0; k < SEGUIDAS; k++)
    if (s->papel[k].w > s->papel[mejor].w + 100) mejor = k;                /* margen para no cambiar por nada */
  if (mejor != s->lider) { s->lider = mejor; s->cambios++; }
  return s->decision[s->lider];
}

static void seguidor_contadores(const void *estado, int aux[4]) {
  const EstSeguidor *s = estado;
  aux[0] = s->cambios; aux[1] = s->lider;
}

static const Estrategia seguidor = {
  "seguidor", "ejemplo: tres candidatos en papel, copia al que lleva mas patrimonio",
  sizeof(CfgSeguidor), sizeof(EstSeguidor), seguidor_configurar, seguidor_iniciar, seguidor_decidir,
  seguidor_contadores, seguidor_liberar};
REGISTRAR_ESTRATEGIA(seguidor)
