/* ejec.c: la regla de reversión con una ejecución que conoce su patrimonio.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * La señal es la de `max_media`: media exponencial con alfa = 1/32, entra
 * con dev < -E y sale con dev > X (E = 96 y X = 0, en treintaidosavos de
 * precio). Lo que cambia es cómo se convierte la señal en órdenes. La regla
 * de la placa repite "comprar 63" o "vender 63" y deja que la maestra recorte.
 * Esta lleva además su propia contabilidad, un espejo de la maestra (caja y
 * acciones), y con eso puede decidir cuántas órdenes manda y cuándo.
 *
 * Sin opciones decide byte a byte lo mismo que `max_media`. Cada opción
 * activa una variante del estudio (README.md, sección 5):
 *
 *   (a) m      no manda una compra si a este precio le alcanza para menos de m acciones
 *       mv     no manda una venta si le quedan menos de mv acciones (se queda con ellas)
 *   (b) K      tope de la posición en órdenes: a lo más 63 K acciones
 *       F      tope en dieciseisavos del patrimonio: no compra si la posición ya vale F/16 o más
 *   (c)(e) eo  entrada escalonada, una orden por escalón de eo:
 *              ea = 1  la última orden entra en E y las anteriores antes (E - eo, E - 2 eo, ...)
 *              ea = 0  la primera orden entra en E y las siguientes más abajo (E + eo, ...):
 *                      el tamaño depende de la profundidad de la desviación
 *              ec = 1  sin escalones: entra completa en E - eo (n - 1), con n las órdenes que necesita
 *   (c)(d) xo  salida escalonada, una orden por escalón de xo:
 *              xa = 1  la última orden sale en X y las anteriores antes (X - xo, ...)
 *              xa = 0  la primera orden sale en X y las siguientes más arriba (X + xo, ...)
 *              xc = 1  sin escalones: sale completa en X - xo (n - 1), con n las órdenes que tiene
 *                      que vender. Es la salida anticipada proporcional a las órdenes que hacen falta
 *       m2,e2  una compra de menos de m2 acciones solo se manda si la desviación pasa de E + e2
 *   (f) nr     no recompra: cuando una compra quedó recortada por la caja (posición completa),
 *              no manda más compras hasta la próxima entrada
 *       nt     sin contabilidad: manda compras solo en los primeros nt ticks de cada entrada
 *
 * El espejo usa las reglas que el programa supone (caja0 y com, por defecto
 * 10000 y 5) y no las reales: así se puede medir qué pasa si la maestra usa
 * otras (opciones --caja y --comision del arnés). El contador aux[0] cuenta
 * los ticks en que el espejo no coincide con la cuenta oficial.
 *
 * Aritmética: enteros, sumas, restas, comparaciones y desplazamientos por
 * constantes. Productos solo de precio (8 bits) por cantidad de acciones, y
 * un cociente de 6 bits (caja / precio, menor que 63) cuando la maestra
 * recorta una compra. aux[1] cuenta los cocientes y aux[2] los productos que
 * no son por 63 (63 p se hace como 64 p - p).
 */
#include <stdio.h>
#include <string.h>

#include "nucleo.h"

#define NMAX 8                 /* órdenes de una posición completa que se distinguen (504 acciones) */

typedef struct {
  int k, E, X;
  int caja0, com;
  int m, mv, K, F;
  int m2, e2;
  int eo, ea, ec;
  int xo, xa, xc;
  int nr, nt;
} Cfg;

typedef struct {
  const Cfg *c;
  int ini, S;
  int caja, acc, dprev;        /* espejo de la maestra y la última decisión mandada */
  int obj, top;                /* objetivo en órdenes (0 afuera, top posición completa) y top anterior */
  int recortada, ticks;        /* la última entrada ya quedó completa; ticks desde que empezó */
  int n_dif, n_div, n_mul, n_sup;
} Estado;

static int configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  Cfg *c = cfg;
  c->k = 5; c->E = 96; c->X = 0; c->caja0 = CAJA0_DEF; c->com = COMISION_DEF; c->ea = 1; c->xa = 1;
#define C(n) {#n, &c->n}
  const Campo campos[] = {C(k), C(E), C(X), C(caja0), C(com), C(m), C(mv), C(K), C(F), C(m2), C(e2), C(eo), C(ea), C(ec),
                          C(xo), C(xa), C(xc), C(nr), C(nt)};
#undef C
  if (leer_campos(parametros, campos, (int)(sizeof campos / sizeof campos[0]), error, tam)) return 1;
  if (c->k < 1 || c->k > 8) { snprintf(error, tam, "ejec: k debe estar entre 1 y 8"); return 1; }
  if (c->K < 0 || c->K > NMAX) { snprintf(error, tam, "ejec: K debe estar entre 0 y %d", NMAX); return 1; }
  return 0;
}

static void iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  Estado *s = estado;
  (void)reglas; (void)semilla;          /* a propósito: el programa no conoce las reglas reales */
  s->c = cfg;
}

/* La decisión anterior ejecutada al precio p, igual que la maestra. */
static void espejo(Estado *s, int p) {
  const Cfg *c = s->c;
  int q = s->dprev & 63, accion = (s->dprev >> 6) & 3;
  if (accion == 1) {
    if (q != 63) s->n_mul++;            /* q x p; con q = 63 es 64 p - p y no cuenta como producto */
    if (q * p + c->com > s->caja) {     /* no alcanza para las q: la maestra recorta */
      if (s->caja - c->com >= p) {      /* el único cociente: (caja - com) / p, menor que 63 */
        q = (s->caja - c->com) / p;     /* el resto de esa división es la caja que queda */
        s->n_div++;
      } else q = 0;                     /* no alcanza ni para una: se sabe con una comparación */
      s->recortada = 1;
    }
    if (q > 0) { s->caja -= q * p + c->com; s->acc += q; }
  } else if (accion == 2) {
    if (q > s->acc) q = s->acc;
    if (q > 0 && q != 63) s->n_mul++;   /* venta de un resto: producto de 6 bits por 8 bits */
    if (q > 0 && s->caja + q * p >= c->com) { s->caja += q * p - c->com; s->acc -= q; }
  }
}

static int decidir(void *estado, int p, const Cuenta *propia) {
  Estado *s = estado;
  const Cfg *c = s->c;
  if (!s->ini) { s->ini = 1; s->S = p << c->k; s->caja = c->caja0; s->acc = 0; s->dprev = MANTENER; s->top = 1; }
  espejo(s, p);
  if (propia->caja != s->caja || propia->acciones != s->acc) s->n_dif++;

  int dev = (p << c->k) - s->S;
  s->S += dev >> c->k;

  /* n: órdenes de 63 que hacen falta para una posición completa con el patrimonio actual */
  int escalones = c->eo || c->xo || c->K;
  int n = 1, todo = 1;
  if (escalones) {
    int W = s->caja + s->acc * p;       /* producto de precio por acciones */
    s->n_mul++;
    for (int j = 1; j < NMAX; j++)
      if (W - c->com >= (63 * j + 1) * p) n++;
  }
  int top = n;
  if (c->K && c->K < n) { top = c->K; todo = 0; }
  if (s->obj >= s->top) { if (s->obj > 0) s->obj = top; }     /* si estaba completa, sigue completa */
  else if (s->obj > top) s->obj = top;
  s->top = top;

  /* escalera de entrada: cuántas órdenes permite esta desviación */
  int sube = 0, baja = top;
  for (int j = 1; j <= top; j++) {
    int umbral = c->ec ? c->E - c->eo * (top - 1) : c->ea ? c->E - c->eo * (top - j) : c->E + c->eo * (j - 1);
    if (umbral < 16) umbral = 16;                              /* nunca entra a menos de medio punto bajo la media */
    if (dev < -umbral) sube++;
  }
  /* escalera de salida: cuántas órdenes deja mantener */
  int tengo = 0;                        /* órdenes que hacen falta para vender lo que hay */
  for (int j = 0; j < NMAX; j++) tengo += s->acc > 63 * j;
  for (int j = 1; j <= top; j++) {
    int umbral = c->xc ? c->X - c->xo * ((tengo > 1 ? tengo : 1) - 1) : c->xa ? c->X - c->xo * (top - j) : c->X + c->xo * (j - 1);
    if (umbral < 32 - c->E) umbral = 32 - c->E;                /* nunca sale a menos de un punto sobre la entrada */
    if (dev > umbral) baja--;
  }
  int antes = s->obj;
  if (sube > s->obj) s->obj = sube;
  if (baja < s->obj) s->obj = baja;
  if (antes == 0 && s->obj > 0) { s->ticks = 0; s->recortada = 0; }
  if (s->obj > antes && antes > 0) s->recortada = 0;          /* un escalón nuevo vuelve a permitir compras */
  s->ticks++;

  int d;
  if (s->obj == 0) {
    d = (c->mv && s->acc < c->mv) ? MANTENER : VENDER_63;
  } else {
    int comprar = 0, q = 63;
    if (s->obj == top && todo) comprar = 1;                    /* todo lo que alcance */
    else {
      int objetivo = 63 * s->obj;
      if (s->acc < objetivo) { comprar = 1; q = objetivo - s->acc; if (q > 63) q = 63; }
      else if (s->acc > objetivo) { comprar = -1; q = s->acc - objetivo; if (q > 63) q = 63; }
    }
    if (comprar > 0) {
      int suprime = 0;
      if (c->m && s->caja - c->com < c->m * p) suprime = 1;                  /* compraría menos de m acciones */
      if (c->m2 && s->caja - c->com < c->m2 * p && dev >= -(c->E + c->e2)) suprime = 1;   /* resto mediano: solo más abajo */
      if (c->F) { s->n_mul++; if (16 * s->acc * p >= c->F * (s->caja + s->acc * p)) suprime = 1; }
      if (c->nr && s->recortada) suprime = 1;
      if (c->nt && s->ticks > c->nt) suprime = 1;
      if (suprime) { if (s->caja - c->com >= p) s->n_sup++; d = MANTENER; }
      else d = COMPRAR(q);
    } else if (comprar < 0) d = VENDER(q);
    else d = MANTENER;
  }
  s->dprev = d;
  return d;
}

/* aux: ticks en que el espejo no coincide con la cuenta oficial, cocientes, productos generales y compras suprimidas */
static void contadores(const void *estado, int aux[4]) {
  const Estado *s = estado;
  aux[0] = s->n_dif; aux[1] = s->n_div; aux[2] = s->n_mul; aux[3] = s->n_sup;
}

static const Estrategia ejec = {
  "ejec", "max_media con contabilidad propia: m, mv, K, F, eo/ea/ec, xo/xa/xc, nr, nt (ver ejec.c)",
  sizeof(Cfg), sizeof(Estado), configurar, iniciar, decidir, contadores, NULL};
REGISTRAR_ESTRATEGIA(ejec)
