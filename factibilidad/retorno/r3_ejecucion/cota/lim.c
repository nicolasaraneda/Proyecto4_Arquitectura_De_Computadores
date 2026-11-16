/* lim.c: la regla de reversión con un límite por orden hipotético. Solo para la cota.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Es la regla de `max_media` (media exponencial con k = 5, entra con
 * dev < -E, sale con dev > X) y la misma forma de operar de la placa: repite
 * "comprar L" mientras la señal dice adentro y "vender L" mientras dice
 * afuera. Lo único que cambia es L, el máximo de acciones por orden:
 *
 *   L = 63        la maestra real. Debe dar lo mismo que `max_media`.
 *   L = 126, 252  maestras hipotéticas con el doble y el cuádruple.
 *   L = 0         sin límite: la posición completa entra y sale en una orden.
 *
 * Solo tiene sentido compilada contra la copia del núcleo de cota/parche.sh,
 * que acepta cantidades de más de 6 bits. Contra el núcleo real cualquier L
 * se comporta como L mod 64. No es una candidata: no se puede construir.
 */
#include <stdio.h>

#include "nucleo.h"

typedef struct { int k, E, X, L; } Cfg;
typedef struct { const Cfg *c; int ini, S, pos; } Estado;

#define SIN_LIMITE (1 << 21)
/* acción en los bits 7:6, cantidad en los bits 5:0 y, lo que no cabe, desde el bit 8 */
#define ORDEN(accion, q) (((accion) << 6) | ((q) & 63) | (((q) >> 6) << 8))

static int configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  Cfg *c = cfg;
  c->k = 5; c->E = 96; c->X = 0; c->L = 63;
  const Campo campos[] = {{"k", &c->k}, {"E", &c->E}, {"X", &c->X}, {"L", &c->L}};
  if (leer_campos(parametros, campos, 4, error, tam)) return 1;
  if (c->L < 0 || c->L > SIN_LIMITE) { snprintf(error, tam, "lim: L fuera de rango"); return 1; }
  if (c->L == 0) c->L = SIN_LIMITE;
  return 0;
}

static void iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  (void)reglas; (void)semilla;
  ((Estado *)estado)->c = cfg;
}

static int decidir(void *estado, int precio, const Cuenta *propia) {
  Estado *s = estado;
  const Cfg *c = s->c;
  (void)propia;
  if (!s->ini) { s->ini = 1; s->S = precio << c->k; }
  int dev = (precio << c->k) - s->S;
  s->S += dev >> c->k;
  if (s->pos && dev > c->X) s->pos = 0;
  else if (!s->pos && dev < -c->E && !(dev > c->X)) s->pos = 1;
  return s->pos ? ORDEN(1, c->L) : ORDEN(2, c->L);
}

static const Estrategia lim = {
  "lim", "cota: max_media con un limite por orden hipotetico. k, E, X, L (0 = sin limite)",
  sizeof(Cfg), sizeof(Estado), configurar, iniciar, decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(lim)
