/* pred.h: predictor de patrones al estilo de un predictor de saltos.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Lo comparten las estrategias de e_patron.c y el medidor exactitud.c, para
 * que la exactitud se mida con el mismo código que después opera.
 *
 * Qué predice: el signo de R = p[t+1+h] - p[t+1]. La decisión que se toma con
 * el precio del tick t se ejecuta al precio del tick t+1, así que el primer
 * cambio que se puede aprovechar es el que viene DESPUÉS de la ejecución
 * (h = 1). El cambio inmediato, p[t+1] - p[t], no sirve: ya pasó cuando la
 * orden se ejecuta.
 *
 * Con qué predice: una historia de los últimos H cambios de precio en un
 * registro de desplazamiento (un bit por cambio: sube o no sube; o dos bits:
 * igual, sube, baja) que indexa una tabla de contadores saturados. Variantes:
 *   tipo 0  historia sola
 *   tipo 1  historia combinada por XOR con la desviación cuantizada (gshare)
 *   tipo 2  solo la desviación cuantizada (bimodal), para comparar
 *   tipo 3  torneo: historia contra desviación, con un selector de 2 bits
 *           indexado por la historia
 *
 * Cómo aprende: el resultado de la predicción del tick u se conoce en el tick
 * u+1+h. Ahí el contador sube si R > 0, baja si R < 0 y no cambia si R = 0.
 * Un anillo guarda los índices y precios de los últimos ticks.
 *
 * Todo con sumas, comparaciones, XOR y desplazamientos por constantes.
 */
#ifndef PRED_H
#define PRED_H

#include <string.h>

#define PRED_LOG 12                    /* hasta 4096 contadores por tabla */
#define PRED_ANILLO 128                /* h <= 126 */

typedef struct {
  int H, sim, bits, tipo, h, shd, lgd, apr;
  int lg;                              /* calculado: log2 de las entradas de la tabla de historia */
} PredCfg;

typedef struct {
  int n, pant;
  unsigned hist;
  unsigned char t1[1 << PRED_LOG], t2[1 << PRED_LOG], sel[1 << PRED_LOG];
  unsigned short r1[PRED_ANILLO], r2[PRED_ANILLO];
  unsigned char rp[PRED_ANILLO], rq[PRED_ANILLO];
} Pred;

static inline void pred_defecto(PredCfg *c) {
  c->H = 8; c->sim = 2; c->bits = 2; c->tipo = 0; c->h = 1; c->shd = 5; c->lgd = 4; c->apr = 1;
}

/* Devuelve NULL si la configuración es válida, o el motivo. */
static inline const char *pred_validar(PredCfg *c) {
  if (c->sim != 2 && c->sim != 3) return "sim debe ser 2 o 3";
  if (c->H < 1) return "H debe ser al menos 1";
  c->lg = c->H * (c->sim == 3 ? 2 : 1);
  if (c->lg > PRED_LOG) return "la historia no cabe en 4096 contadores";
  if (c->bits < 1 || c->bits > 8) return "bits debe estar entre 1 y 8";
  if (c->tipo < 0 || c->tipo > 3) return "tipo debe ser 0, 1, 2 o 3";
  if (c->h < 1 || c->h > PRED_ANILLO - 2) return "h debe estar entre 1 y 126";
  if (c->lgd < 1 || c->lgd > PRED_LOG) return "lgd fuera de rango";
  if (c->tipo == 1 && c->lgd > c->lg) return "gshare: lgd no puede ser mayor que los bits de historia";
  if (c->shd < 0 || c->shd > 10) return "shd fuera de rango";
  return NULL;
}

/* Bits de memoria de las tablas del predictor (sin el anillo). */
static inline int pred_bits_tabla(const PredCfg *c) {
  int t1 = (1 << c->lg) * c->bits, t2 = (1 << c->lgd) * c->bits;
  return c->tipo == 2 ? t2 : c->tipo == 3 ? t1 + t2 + (1 << c->lg) * 2 : t1;
}

static inline void pred_subir(unsigned char *v, int arriba, int max) {
  if (arriba) { if (*v < max) (*v)++; } else if (*v > 0) (*v)--;
}

/* Un tick: aprende del resultado que se acaba de conocer y predice. `dev` es
 * la desviación de la regla (32 p - S). Devuelve +2 (sube, saturado), +1
 * (sube), -1 (baja) o -2 (baja, saturado). */
static inline int pred_paso(Pred *s, const PredCfg *c, int pr, int dev) {
  const int max = (1 << c->bits) - 1, mid = 1 << (c->bits - 1), M = PRED_ANILLO - 1;
  const int nd = 1 << c->lgd;
  if (!s->n) {                                        /* valor inicial: sin opinión */
    for (int i = 0; i < (1 << c->lg); i++) { s->t1[i] = (unsigned char)(mid - (i & 1)); s->sel[i] = 1; }
    for (int i = 0; i < nd; i++) s->t2[i] = (unsigned char)(i < nd / 2 ? mid : mid - 1);   /* bajo la media: sube */
    s->pant = pr;
  }
  int d = pr - s->pant;
  s->pant = pr;
  int sym = c->sim == 3 ? (d > 0 ? 1 : d < 0 ? 2 : 0) : d > 0;
  s->hist = ((s->hist << (c->sim == 3 ? 2 : 1)) | (unsigned)sym) & ((1u << c->lg) - 1);

  if (c->apr && s->n >= c->h + 1) {                   /* el resultado del tick u ya se conoce */
    int u = s->n - 1 - c->h;
    int R = pr - s->rp[(u + 1) & M];
    if (R != 0) {
      int arriba = R > 0, i1 = s->r1[u & M], i2 = s->r2[u & M];
      if (c->tipo == 3) {
        int p1 = s->rq[u & M] & 1, p2 = (s->rq[u & M] >> 1) & 1;
        if (p1 != p2) pred_subir(&s->sel[i1], p1 == arriba, 3);
      }
      if (c->tipo != 2) pred_subir(&s->t1[i1], arriba, max);
      if (c->tipo >= 2) pred_subir(&s->t2[i2], arriba, max);
    }
  }

  int q = (dev >> c->shd) + nd / 2;
  if (q < 0) q = 0;
  if (q > nd - 1) q = nd - 1;
  int i1 = (int)s->hist, i2 = q;
  if (c->tipo == 1) i1 ^= q << (c->lg - c->lgd);
  int v1 = s->t1[i1], v2 = s->t2[i2];
  int v = c->tipo == 2 ? v2 : c->tipo == 3 ? (s->sel[i1] >= 2 ? v1 : v2) : v1;

  s->r1[s->n & M] = (unsigned short)i1;
  s->r2[s->n & M] = (unsigned short)i2;
  s->rp[s->n & M] = (unsigned char)pr;
  s->rq[s->n & M] = (unsigned char)((v1 >= mid) | ((v2 >= mid) << 1));
  s->n++;
  if (v >= mid) return v == max ? 2 : 1;
  return v == 0 ? -2 : -1;
}

#endif
