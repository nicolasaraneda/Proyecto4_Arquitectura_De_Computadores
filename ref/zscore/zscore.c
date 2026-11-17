/* zscore.c: la regla "zscore" de Vicente Calderón como estrategia del arnés de retorno.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Es la misma regla de ref/zscore.py, con los mismos nombres de parámetros, para
 * correrla en el torneo de factibilidad/retorno (puntos esperados contra campos de
 * rivales, a 2000 y 20 000 ticks). La equivalencia con la referencia en Python se
 * comprueba serie por serie (ref/zscore/validar.py).
 *
 * Parámetros (enteros):
 *   km, kd    memorias de la media y de la desviación absoluta media, 2^km y 2^kd ticks (5 y 6)
 *   num, den  umbral de entrada z = num/den desviaciones (5/2)
 *   w         precios de calentamiento después del primero, en que solo actualiza (64)
 *   sx2       salida: sale si dev > (sx2/2) d (0: sale al cruzar la media)
 *
 * Regla, con M = 2^km media y D = 2^kd desviación (en las unidades de M):
 *   primer precio: M = 2^km p, D = 0, mantener
 *   dev = 2^km p - M; mag = |dev|
 *   M += p - ((M + 2^(km-1)) >> km); D += mag - ((D + 2^(kd-1)) >> kd)
 *   calentamiento: mantener
 *   entra si dev < 0 y den 2^kd mag > num D; sale si dev > 0 y 2 2^kd dev > sx2 D
 *   comprar 63 si quiere estar adentro, vender 63 si no
 */
#include <stdio.h>

#include "nucleo.h"

typedef struct { int km, kd, num, den, w, sx2; } Cfg;
typedef struct { const Cfg *c; int ini, n, quiere; long long M, D; int entradas; } Estado;

static int configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  Cfg *c = cfg;
  c->km = 5; c->kd = 6; c->num = 5; c->den = 2; c->w = 64; c->sx2 = 0;
  const Campo campos[] = {{"km", &c->km}, {"kd", &c->kd}, {"num", &c->num}, {"den", &c->den}, {"w", &c->w}, {"sx2", &c->sx2}};
  if (leer_campos(parametros, campos, 6, error, tam)) return 1;
  if (c->km < 1 || c->km > 12 || c->kd < 1 || c->kd > 12 || c->den < 1 || c->num < 0 || c->w < 0 || c->sx2 < 0) {
    snprintf(error, tam, "zscore: parametro fuera de rango"); return 1;
  }
  return 0;
}

static void iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  (void)reglas; (void)semilla;
  ((Estado *)estado)->c = cfg;
}

static int decidir(void *estado, int p, const Cuenta *propia) {
  Estado *s = estado;
  const Cfg *c = s->c;
  (void)propia;
  if (!s->ini) { s->ini = 1; s->M = (long long)p << c->km; s->D = 0; return MANTENER; }
  long long dev = ((long long)p << c->km) - s->M;
  long long mag = dev < 0 ? -dev : dev;
  s->M += p - ((s->M + (1LL << (c->km - 1))) >> c->km);
  s->D += mag - ((s->D + (1LL << (c->kd - 1))) >> c->kd);
  if (s->n < c->w) { s->n++; return MANTENER; }
  if (dev < 0 && ((long long)c->den << c->kd) * mag > (long long)c->num * s->D) {
    if (!s->quiere) s->entradas++;
    s->quiere = 1;
  } else if (dev > 0 && (2LL << c->kd) * dev > (long long)c->sx2 * s->D) s->quiere = 0;
  return s->quiere ? COMPRAR_63 : VENDER_63;
}

static void contadores(const void *estado, int aux[4]) {
  const Estado *s = estado;
  aux[0] = s->entradas; aux[1] = (int)s->D; aux[2] = 0; aux[3] = 0;
}

static const Estrategia zscore = {"zscore", "regla zscore de Vicente: km, kd, num, den, w, sx2", sizeof(Cfg), sizeof(Estado),
                                  configurar, iniciar, decidir, contadores, NULL};
REGISTRAR_ESTRATEGIA(zscore)

/* Con nombre: la regla tal como la entregó Vicente. */
static void __attribute__((constructor)) alias_zscore(void) {
  nucleo_alias("cand:zscore", "zscore:km=5,kd=6,num=5,den=2,w=64", "regla zscore de Vicente: z = 2,5, memorias 32 y 64");
}
