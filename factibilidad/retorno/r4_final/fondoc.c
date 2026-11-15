/* fondoc.c: el fondo de estrategias con la ejecución del estudio 3 en el supervisor.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Estudio de retorno 4, cierre. Es una copia de ../r4b_fondo/fondo.c con tres
 * cambios, y nada más:
 *   1. La estrategia se registra como `fondoc` (el original sigue siendo
 *      `fondo` y se compila sin tocar en el mismo binario).
 *   2. Parámetro nuevo `em`: el supervisor no manda una compra si la caja de
 *      su espejo alcanza para menos de `em` acciones al precio actual. Es la
 *      regla de `ejec:m=8` del estudio de ejecución, puesta donde tiene que
 *      ir: en el supervisor, que es quien lleva el espejo de la cuenta real.
 *      Un filtro por fuera desincronizaría ese espejo. Con em=0 (por defecto)
 *      el fondo decide byte a byte igual que `fondo` (objetivo `prueba`).
 *   3. No registra alias: los de este estudio están en final.c.
 * El resto del texto es el del original.
 *
 * Estudio de retorno 4, parte B. Tres (o cuatro) gestores operan en papel y
 * un supervisor lleva la cuenta real, reparte el capital entre ellos y emite
 * UNA orden por tick. No es parte del diseño: es el modelo de referencia
 * contra el que se compara, byte a byte, el programa en assembly del barrel.
 *
 * Orden exacto de las operaciones dentro de un tick (llega el precio p):
 *
 *   1. Supervisor: ejecuta en su espejo de la cuenta real, al precio p, el
 *      byte que dejó en DECISION en el tick anterior (reglas oficiales).
 *   2. Cada gestor k, con el mismo precio p:
 *        a. ejecuta en su cuenta en papel, al precio p, su decisión anterior;
 *        b. actualiza su puntaje por acción (papel simplificado);
 *        c. decide con p y publica su posición (0 afuera, 1 adentro) y su
 *           desempeño en papel.
 *   3. Supervisor: toma lo publicado por los gestores. Con df=0 usa lo que
 *      publicaron en este mismo tick (espera a que terminen). Con df=1 usa
 *      lo que habían publicado en el tick anterior (no espera a nadie).
 *   4. Supervisor: si corresponde (frontera de ventana), ajusta los pesos.
 *   5. Supervisor: F = suma de peso por posición (en dieciseisavos). Con
 *      F = 16 escribe "comprar 63", con F = 0 "vender 63", y entre medio
 *      calcula la orden que acerca la parte invertida a F/16 del patrimonio,
 *      salvo que la diferencia quede dentro de la banda de no operar.
 *
 * Toda la aritmética del supervisor es entera: sumas, restas, comparaciones,
 * desplazamientos por constantes, productos de precio (8 bits) por cantidad
 * y una división de cociente acotado a 63 (6 pasos de resta condicionada).
 *
 * Parámetros (todos enteros salvo x):
 *   c    conjunto de gestores: 1 max_media, prudente, comprar y mantener
 *                              2 max_media, guardia, comprar y mantener
 *                              3 max_media, kalman, activo
 *                              4 max_media, base, prudente (tres bandas de la misma regla)
 *                              5 max_media, base, activo (tres bandas cercanas, las más baratas)
 *   x    cuarto gestor, experimental, por nombre (alias o estrategia). Para
 *        pasar parámetros se escribe '/' en vez de ',' y '~' en vez de '='.
 *   w0..w3  pesos iniciales (el prior), en dieciseisavos. Deben sumar 16.
 *   m    reparto: 0 pesos fijos, 1 líder con histéresis, 2 pesos aprendidos
 *   v    ventana de evaluación, 2^v ticks. Con m=1 y v=0 el desempeño es el acumulado
 *   mg   margen relativo 2^-mg: solo se cambia si la ventaja lo supera
 *   d    cuánto se puede alejar cada peso de su prior (m=2), en dieciseisavos
 *   ps   paso de cada ajuste (m=2), en dieciseisavos
 *   fj   máscara de gestores con peso fijo, que no entran al aprendizaje (ancla)
 *   b    banda de no operar para posiciones parciales, en dieciseisavos del patrimonio
 *   df   desfase: 0 mismo tick, 1 tick anterior
 *   pp   papel: 0 cuenta oficial de cada gestor, 1 puntaje por acción (sin productos)
 *   vt   voto: si no es 0, F se lleva a 16 cuando F >= vt y a 0 si no (todo o nada)
 *   vs   voto con histéresis: si se da, con F >= vt se entra, con F <= vs se sale y entre
 *        medio se conserva lo anterior. Sin vs, se sale con F < vt
 *   em   (solo fondoc) no manda una compra si la caja alcanza para menos de em acciones
 *
 * Contadores: cambios de líder o de pesos, peso final del gestor 0, ticks en
 * que el espejo no coincide con la cuenta real (debe ser 0) y ticks con
 * objetivo parcial.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "nucleo.h"

#define MAXG 4
#define NP 16                    /* los pesos son dieciseisavos */

typedef struct {
  int ng;
  Instancia *sub[MAXG];
  int conj, modo, w[MAXG], v, mg, d, ps, fj, b, df, pp, vt, vs, em;
  char x[256];
} Cfg;

typedef struct {
  const Cfg *c;
  Reglas r;
  Cuenta real;                   /* espejo de la cuenta real que lleva el supervisor */
  int dec_ant;                   /* último byte escrito en DECISION */
  Cuenta papel[MAXG];            /* cuenta en papel de cada gestor, reglas oficiales */
  int dec[MAXG];                 /* última decisión de cada gestor */
  int pos[MAXG];                 /* posición que cada gestor publicó: 0 afuera, 1 adentro */
  int ten[MAXG];                 /* posición que el gestor ya tiene ejecutada (papel por acción) */
  int S[MAXG];                   /* puntaje por acción, en 1/16 de unidad de precio */
  int ref[MAXG];                 /* desempeño al comenzar la ventana */
  int w[MAXG];                   /* pesos vigentes */
  int lider, t, p_ant, ini;
  int voto;                      /* estado del voto con histéresis: 0 afuera, 1 adentro */
  int n_cambios, n_parciales, n_espejo;
  int n_suprimidas;              /* compras que el supervisor no mandó por la regla em */
} Estado;

static const char *CONJUNTOS[6][3] = {
  {NULL, NULL, NULL},
  {"cand:max_media", "cand:prudente", "byh:q=63,rep=1"},
  {"cand:max_media", "cand:guardia", "byh:q=63,rep=1"},
  {"cand:max_media", "cand:kalman", "cand:activo"},
  {"cand:max_media", "cand:base", "cand:prudente"},
  {"cand:max_media", "cand:base", "cand:activo"},
};

static int configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  Cfg *c = cfg;
  char copia[1024], *guarda = NULL;
  int hay_w = 0;
  c->conj = 1; c->modo = 0; c->vs = -1; c->v = 9; c->mg = 6; c->d = 4; c->ps = 1; c->b = 1; c->df = 0; c->pp = 0;
  c->w[0] = NP;
  if (parametros && strlen(parametros) >= sizeof copia) { snprintf(error, tam, "fondoc: parametros demasiado largos"); return 1; }
  strcpy(copia, parametros ? parametros : "");
  struct { const char *n; int *d; } campos[] = {
    {"c", &c->conj}, {"m", &c->modo}, {"w0", &c->w[0]}, {"w1", &c->w[1]}, {"w2", &c->w[2]}, {"w3", &c->w[3]},
    {"v", &c->v}, {"mg", &c->mg}, {"d", &c->d}, {"ps", &c->ps}, {"fj", &c->fj}, {"b", &c->b}, {"df", &c->df},
    {"pp", &c->pp}, {"vt", &c->vt}, {"vs", &c->vs}, {"em", &c->em}};
  for (char *tok = strtok_r(copia, ", \t\r\n", &guarda); tok; tok = strtok_r(NULL, ", \t\r\n", &guarda)) {
    char *eq = strchr(tok, '=');
    size_t k, n = sizeof campos / sizeof campos[0];
    if (!eq) { snprintf(error, tam, "fondoc: parametro sin valor: %s", tok); return 1; }
    *eq = 0;
    if (!strcmp(tok, "x")) {
      snprintf(c->x, sizeof c->x, "%s", eq + 1);
      for (char *q = c->x; *q; q++) { if (*q == '/') *q = ','; else if (*q == '~') *q = '='; }
      continue;
    }
    for (k = 0; k < n; k++)
      if (!strcmp(campos[k].n, tok)) { *campos[k].d = (int)strtol(eq + 1, NULL, 0); break; }
    if (k == n) { snprintf(error, tam, "fondoc: parametro desconocido: %s", tok); return 1; }
    if (tok[0] == 'w' && !hay_w) { hay_w = 1; if (strcmp(tok, "w0")) c->w[0] = 0; }
  }
  if (c->conj < 1 || c->conj > 5) { snprintf(error, tam, "fondoc: c debe estar entre 1 y 5"); return 1; }
  c->ng = c->x[0] ? 4 : 3;
  int suma = 0;
  for (int k = 0; k < MAXG; k++) {
    if (c->w[k] < 0 || (k >= c->ng && c->w[k])) { snprintf(error, tam, "fondoc: peso invalido en w%d", k); return 1; }
    suma += c->w[k];
  }
  if (suma != NP) { snprintf(error, tam, "fondoc: los pesos deben sumar %d (suman %d)", NP, suma); return 1; }
  if (c->modo < 0 || c->modo > 2 || c->v < 0 || c->v > 14 || c->mg < 0 || c->mg > 10 || c->b < 0 || c->b > NP ||
      c->ps < 1 || c->d < 0 || (c->modo == 2 && c->v == 0)) {
    snprintf(error, tam, "fondoc: parametro fuera de rango"); return 1;
  }
  for (int k = 0; k < c->ng; k++) {
    const char *spec = k < 3 ? CONJUNTOS[c->conj][k] : c->x;
    if (!(c->sub[k] = instancia_crear(spec, error, tam))) return 1;
  }
  return 0;
}

static void liberar(void *cfg) {
  Cfg *c = cfg;
  for (int k = 0; k < MAXG; k++) instancia_destruir(c->sub[k]);
}

static void iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  Estado *s = estado;                              /* llega en cero */
  const Cfg *c = cfg;
  s->c = c;
  s->r = *reglas;
  cuenta_iniciar(&s->real, reglas);
  s->dec_ant = MANTENER;
  for (int k = 0; k < c->ng; k++) {
    instancia_iniciar(c->sub[k], reglas, semilla + (uint64_t)k + 1);
    cuenta_iniciar(&s->papel[k], reglas);
    s->dec[k] = MANTENER;
    s->w[k] = c->w[k];
    s->ref[k] = c->pp ? 0 : reglas->caja0;
    if (c->w[k] > c->w[s->lider]) s->lider = k;    /* el líder inicial es el de mayor peso en el prior */
  }
}

/* Desempeño en papel del gestor k: patrimonio de su cuenta oficial o puntaje por acción. */
static int desempeno(const Estado *s, int k) { return s->c->pp ? s->S[k] : s->papel[k].w; }

/* La ventaja supera el margen relativo 2^-mg: ventaja * 2^mg > base (solo desplazamientos a la izquierda). */
static int supera(long long ventaja, long long base, int mg) { return ventaja * (1LL << mg) > base; }

static int decidir(void *estado, int p, const Cuenta *propia) {
  Estado *s = estado;
  const Cfg *c = s->c;
  int vis_pos[MAXG], vis_des[MAXG];

  /* 1. espejo de la cuenta real: la orden anterior se ejecuta al precio que acaba de llegar */
  cuenta_ejecutar(&s->real, &s->r, s->dec_ant, p);
  if (s->real.caja != propia->caja || s->real.acciones != propia->acciones) s->n_espejo++;
  if (!s->ini) { s->ini = 1; s->p_ant = p; }
  int dp = p - s->p_ant;
  s->p_ant = p;

  /* 2. gestores en papel */
  for (int k = 0; k < c->ng; k++) {
    vis_pos[k] = s->pos[k];                        /* lo que el gestor tenía publicado del tick anterior */
    vis_des[k] = desempeno(s, k);
    cuenta_ejecutar(&s->papel[k], &s->r, s->dec[k], p);
    if (s->ten[k]) s->S[k] += dp * 16;             /* tuvo la acción entre el precio anterior y este */
    if (s->ten[k] != s->pos[k]) { s->ten[k] = s->pos[k]; s->S[k] -= 1; }   /* su orden se ejecuta ahora: comisión */
    s->dec[k] = instancia_decidir(c->sub[k], p, &s->papel[k]);
    int accion = (s->dec[k] >> 6) & 3;
    if (accion == 1) s->pos[k] = 1; else if (accion == 2) s->pos[k] = 0;
    if (!c->df) { vis_pos[k] = s->pos[k]; vis_des[k] = desempeno(s, k); }
  }

  /* 3 y 4. reparto: pesos fijos, líder con histéresis o pesos aprendidos alrededor del prior */
  s->t++;
  int frontera = c->v ? (s->t & ((1 << c->v) - 1)) == 0 : 1;
  if (c->modo == 1 && frontera) {
    int mejor = s->lider;
    for (int k = 0; k < c->ng; k++)
      if (vis_des[k] - s->ref[k] > vis_des[mejor] - s->ref[mejor]) mejor = k;
    long long ventaja = (long long)(vis_des[mejor] - s->ref[mejor]) - (vis_des[s->lider] - s->ref[s->lider]);
    long long base = c->pp ? 16LL * p : vis_des[s->lider];
    if (mejor != s->lider && supera(ventaja, base, c->mg)) { s->lider = mejor; s->n_cambios++; }
    if (c->v) for (int k = 0; k < c->ng; k++) s->ref[k] = vis_des[k];
  }
  if (c->modo == 1)
    for (int k = 0; k < c->ng; k++) s->w[k] = k == s->lider ? NP : 0;
  if (c->modo == 2 && frontera) {
    int mejor = -1, peor = -1;
    for (int k = 0; k < c->ng; k++) {
      if ((c->fj >> k) & 1) continue;
      int g = vis_des[k] - s->ref[k];
      if (mejor < 0 || g > vis_des[mejor] - s->ref[mejor]) mejor = k;
      if (peor < 0 || g < vis_des[peor] - s->ref[peor]) peor = k;
    }
    if (mejor >= 0 && mejor != peor) {
      long long ventaja = (long long)(vis_des[mejor] - s->ref[mejor]) - (vis_des[peor] - s->ref[peor]);
      long long base = c->pp ? 16LL * p : vis_des[peor];
      int piso = c->w[peor] - c->d < 0 ? 0 : c->w[peor] - c->d;
      if (supera(ventaja, base, c->mg) && s->w[mejor] + c->ps <= c->w[mejor] + c->d && s->w[peor] - c->ps >= piso) {
        s->w[mejor] += c->ps; s->w[peor] -= c->ps; s->n_cambios++;
      }
    }
    for (int k = 0; k < c->ng; k++) s->ref[k] = vis_des[k];
  }

  /* 5. posición objetivo y orden */
  int F = 0, decision;
  for (int k = 0; k < c->ng; k++) F += vis_pos[k] ? s->w[k] : 0;
  if (c->vt) {
    if (F >= c->vt) s->voto = 1;
    else if (c->vs < 0 || F <= c->vs) s->voto = 0;
    F = s->voto ? NP : 0;
  }
  if (F >= NP) decision = COMPRAR_63;
  else if (F <= 0) decision = VENDER_63;
  else {
    long long V = (long long)s->real.acciones * p;        /* parte invertida: acciones por precio */
    long long W = s->real.caja + V;                       /* patrimonio real */
    long long D = F * W - NP * V;                         /* falta (o sobra) para el objetivo, en 1/16 de peso */
    long long banda = c->b * W, q;
    s->n_parciales++;
    if (D > banda) {
      q = (D - NP * (long long)s->r.comision) / (NP * (long long)p);     /* cociente acotado: 6 pasos de resta */
      if (q > 63) q = 63;
      decision = q > 0 ? COMPRAR((int)q) : MANTENER;
    } else if (D < -banda) {
      q = (-D) / (NP * (long long)p);
      if (q > 63) q = 63;
      decision = q > 0 ? VENDER((int)q) : MANTENER;
    } else decision = MANTENER;
  }
  /* ejecución del estudio 3: una compra que alcanzaría para menos de em acciones no se manda */
  if (c->em && ((decision >> 6) & 3) == 1 && s->real.caja - s->r.comision < c->em * p) {
    if (s->real.caja - s->r.comision >= p) s->n_suprimidas++;
    decision = MANTENER;
  }
  s->dec_ant = decision;

  /* traza para llevar el fondo a assembly: FONDO_TRAZA=archivo con el comando correr (un solo hilo) */
  static FILE *traza;
  static int traza_vista;
  if (!traza_vista) {
    traza_vista = 1;
    const char *ruta = getenv("FONDO_TRAZA");
    if (ruta && *ruta && (traza = fopen(ruta, "w")))
      fprintf(traza, "tick,precio,caja,acciones,pos0,pos1,pos2,des0,des1,des2,w0,w1,w2,F,decision\n");
  }
  if (traza)
    fprintf(traza, "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%02x\n", s->t - 1, p, s->real.caja, s->real.acciones,
            vis_pos[0], vis_pos[1], vis_pos[2], vis_des[0], vis_des[1], vis_des[2], s->w[0], s->w[1], s->w[2], F, decision);
  return decision;
}

static void contadores(const void *estado, int aux[4]) {
  const Estado *s = estado;
  aux[0] = s->n_cambios; aux[1] = s->w[0]; aux[2] = s->n_espejo; aux[3] = s->n_parciales;
}

static const Estrategia fondoc = {
  "fondoc", "el fondo de r4b con la ejecucion del estudio 3 en el supervisor (em). Con em=0 es `fondo`. c, x, w0..w3, m, v, mg, d, ps, fj, b, df, pp, vt, vs, em",
  sizeof(Cfg), sizeof(Estado), configurar, iniciar, decidir, contadores, liberar};
REGISTRAR_ESTRATEGIA(fondoc)
