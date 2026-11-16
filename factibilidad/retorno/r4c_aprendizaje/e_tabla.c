/* e_tabla.c: tabla de política que parte de la regla max_media y se ajusta en vivo.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Estrategia `tabla` del arnés de retorno (factibilidad/retorno). No es parte
 * del diseño ni del programa de la placa: es el prototipo en C con el que se
 * mide si la idea gana.
 *
 * Estado que indexa la tabla:
 *   - la desviación del precio respecto de la media exponencial (la misma de
 *     la regla base, dev = 32 p - S), cuantizada en casillas de 2^sh / 32
 *     unidades de precio;
 *   - la posición (dentro o fuera): corre la cuantización en 1/32 de precio
 *     para que los dos umbrales de la regla caigan justo en un borde de
 *     casilla, y con filas=2 además elige una fila propia;
 *   - opcional, un tercer índice barato (ter): el signo del último cambio o
 *     un régimen de volatilidad.
 *
 * Contenido (modo):
 *   0  estimación del retorno futuro a h ticks contado desde el tick de
 *      ejecución, R = p[t+1+h] - p[t+1], en precio por 2^10. Se ajusta con
 *      T[s] += (R * 2^10 - T[s]) >> ka cuando el resultado ya se conoce. La
 *      tabla guarda el acumulador A = T * 2^ka y se actualiza como
 *      A += R * 2^10 - (A >> ka), que es la misma recurrencia sin perder los
 *      bits que el desplazamiento bota. La forma directa, con T en la tabla,
 *      redondea siempre hacia abajo y con ka grande eso arrastra la tabla
 *      entera hacia "vender" (se midió: ver README.md, sección de hallazgos).
 *      R se recorta a +-31 para que A quepa en 32 bits con ka hasta 16.
 *   1  preferencia de acción con contador saturado de `bits` bits: sube si
 *      R > g y baja si R < -g.
 *
 * Valor inicial: el que implica la regla (comprar bajo -E, vender sobre X).
 *   modo 0: recta T0 = -c * (centro de la casilla) / 8, con umbral de compra
 *           c * E / 8 y de venta c * X / 8. La recta cruza el umbral justo en el
 *           borde de la regla, así que con ka = 0 la tabla decide igual que
 *           max_media en todos los ticks (make equivalencia lo comprueba).
 *   modo 1: contador en el máximo en las casillas de compra, en cero en las
 *           de venta y en la mitad en las demás.
 *
 * Con banda=1 la tabla no decide casilla por casilla: solo corre los dos
 * bordes de la banda, a lo más `lim` casillas desde la regla, cuando la
 * casilla vecina al borde cruza el umbral con margen `mg`. Es la tabla como
 * ajuste lento de las bandas.
 *
 * Todo es aritmética entera con sumas, restas, comparaciones y
 * desplazamientos por constantes. No hay multiplicaciones en `decidir`: las
 * de `tabla_iniciar` son las constantes del valor inicial, que en la placa
 * irían en el .hex.
 *
 * Con ter=1 o 3, los parámetros ezb, ezi y ezs suben el umbral de compra
 * cuando el último cambio fue una baja, nulo o una subida. Con ka=0 eso ya no
 * es max_media sino otra regla fija (por ejemplo "entra 3 bajo la media, o 4
 * si el precio acaba de bajar"), y sirve para separar lo que aporta el tercer
 * índice de lo que aporta aprender.
 *
 * Con cmp=1 lleva por dentro a max_media y cuenta en aux[3] los ticks en que
 * el byte de decisión es distinto. Sirve para la prueba de equivalencia.
 */
#include <stdio.h>
#include <string.h>

#include "nucleo.h"

#define MAXNB 64                 /* casillas de desviación por fila */
#define MAXNT 3                  /* valores del tercer índice */
#define MAXT (2 * MAXNT * MAXNB)
#define ANILLO 128               /* ticks de historia para conocer el resultado: h <= 126 */
#define FQ 10                    /* la estimación va en precio por 2^10 */
#define RMAX 31                  /* recorte del resultado, en unidades de precio */

typedef struct {
  int k, E, X;                   /* la regla de partida */
  int sh, nb, ter, filas;        /* forma de la tabla */
  int h, ka, modo;               /* horizonte, tasa de aprendizaje (0 = apagado), contenido */
  int c, ui, uo;                 /* modo 0: pendiente del valor inicial (precio/256 por unidad de precio de desviación) y
                                    corrimiento de los umbrales (precio/1024) */
  int bits, g;                   /* modo 1: bits del contador y zona muerta del resultado */
  int banda, lim, mg;            /* ajuste de bordes */
  int kv, uv;                    /* régimen de volatilidad */
  int ezb, ezi, ezs;             /* con ter=1 o 3: umbral de compra más exigente (en 1/32 de precio) según el último cambio */
  int cmp;
  int dir;                       /* 1: forma directa T += (R - T) >> ka, con su sesgo de redondeo (solo para medirlo) */
  int nt, ks;                    /* calculados: valores del tercer índice y bits de más del acumulador */
  Instancia *ref;                /* max_media, solo con cmp=1 */
} Cfg;

typedef struct {
  const Cfg *c;
  Reglas reglas;
  int ini, n, S, pant, pos, V;
  int T[MAXT];
  int eb[MAXNT], xb[MAXNT];      /* bordes de la banda (banda=1): entra si casilla < eb, sale si casilla >= xb */
  short st[ANILLO];
  unsigned char pr[ANILLO];
  int n_dif, n_ent, n_cmp;
} Estado;

static int configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  Cfg *c = cfg;
  c->k = 5; c->E = 96; c->X = 0;
  c->sh = 5; c->nb = 32; c->ter = 0; c->filas = 1;
  c->h = 16; c->ka = 0; c->modo = 0;
  c->c = 32; c->ui = 0; c->uo = 0;
  c->bits = 6; c->g = 0;
  c->banda = 0; c->lim = 1; c->mg = 0;
  c->kv = 5; c->uv = 384;
#define C(n) {#n, &c->n}
  const Campo campos[] = {C(k), C(E), C(X), C(sh), C(nb), C(ter), C(filas), C(h), C(ka), C(modo), C(c), C(ui), C(uo),
                          C(bits), C(g), C(banda), C(lim), C(mg), C(kv), C(uv), C(ezb), C(ezi), C(ezs), C(cmp), C(dir)};
#undef C
  if (leer_campos(parametros, campos, (int)(sizeof campos / sizeof campos[0]), error, tam)) return 1;
  c->nt = c->ter == 1 ? 3 : c->ter ? 2 : 1;
  c->ks = c->dir || c->modo ? 0 : c->ka;
  const char *mal = NULL;
  if (c->k < 1 || c->k > 8) mal = "k debe estar entre 1 y 8";
  else if (c->sh < 1 || c->sh > c->k + 3) mal = "sh fuera de rango";
  else if (c->nb != 8 && c->nb != 16 && c->nb != 32 && c->nb != 64) mal = "nb debe ser 8, 16, 32 o 64";
  else if (c->ter < 0 || c->ter > 3) mal = "ter debe ser 0, 1, 2 o 3";
  else if (c->filas != 1 && c->filas != 2) mal = "filas debe ser 1 o 2";
  else if (c->h < 1 || c->h > ANILLO - 2) mal = "h debe estar entre 1 y 126";
  else if (c->ka < 0 || c->ka > 16) mal = "ka debe estar entre 0 y 16";
  else if (c->c < 1 || c->c > 255 || (c->c << (c->sh - 1)) % 8 || (c->c * c->E) % 8 || (c->c * c->X) % 8)
    mal = "c fuera de rango o el valor inicial no queda entero (c * 2^(sh-1), c * E y c * X deben ser multiplos de 8)";
  else if (c->modo != 0 && c->modo != 1) mal = "modo debe ser 0 o 1";
  else if (c->bits < 2 || c->bits > 12) mal = "bits debe estar entre 2 y 12";
  else if (c->E % (1 << c->sh) || c->X % (1 << c->sh)) mal = "E y X deben ser multiplos de 2^sh";
  else if (c->E >= (c->nb / 2) << c->sh || c->X >= (c->nb / 2) << c->sh || c->X <= -((c->nb / 2) << c->sh))
    mal = "los umbrales de la regla quedan fuera de la tabla";
  else if (c->banda && c->modo) mal = "banda=1 solo con modo=0";
  else if (c->banda && c->filas != 1) mal = "banda=1 solo con filas=1";
  else if ((c->ezb || c->ezi || c->ezs) && (c->modo || c->banda || (c->ter != 1 && c->ter != 3)))
    mal = "ezb, ezi y ezs solo con modo=0, banda=0 y ter=1 o 3";
  else if (c->ezb % (1 << c->sh) || c->ezi % (1 << c->sh) || c->ezs % (1 << c->sh)) mal = "ezb, ezi y ezs deben ser multiplos de 2^sh";
  if (mal) { snprintf(error, tam, "tabla: %s", mal); return 1; }
  if (c->cmp && !(c->ref = instancia_crear("cand:max_media", error, tam))) return 1;
  return 0;
}

static void liberar(void *cfg) {
  Cfg *c = cfg;
  if (c->ref) instancia_destruir(c->ref);
}

static void iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  Estado *s = estado;
  s->c = cfg;
  s->reglas = *reglas;
  if (s->c->ref) instancia_iniciar(s->c->ref, reglas, semilla);
}

/* Valor inicial de la tabla: lo que implica la regla. */
static void tabla_iniciar(Estado *s) {
  const Cfg *c = s->c;
  int mitad = c->nb / 2;
  int eb0 = mitad - (c->E >> c->sh);                 /* primera casilla que NO compra */
  int xb0 = mitad + (c->X >> c->sh);                 /* primera casilla que vende */
  for (int f = 0; f < c->filas; f++)
    for (int z = 0; z < c->nt; z++)
      for (int i = 0; i < c->nb; i++) {
        int v;
        if (c->modo == 0) {
          int centro = ((i - mitad) << c->sh) + (1 << (c->sh - 1));     /* en 1/32 de precio */
          v = (-c->c * centro / 8) * (1 << c->ks);                      /* acumulador: precio por 2^10 por 2^ka */
        } else {
          v = i < eb0 ? (1 << c->bits) - 1 : i >= xb0 ? 0 : 1 << (c->bits - 1);
        }
        s->T[(f * c->nt + z) * c->nb + i] = v;
      }
  for (int z = 0; z < c->nt; z++) { s->eb[z] = eb0; s->xb[z] = xb0; }
}

static int decidir(void *estado, int pr, const Cuenta *propia) {
  Estado *s = estado;
  const Cfg *c = s->c;
  if (!s->ini) { s->ini = 1; s->pant = pr; s->S = pr << c->k; tabla_iniciar(s); }
  int d = pr - s->pant;
  s->pant = pr;
  int dev = (pr << c->k) - s->S;                     /* la misma desviación de la regla base */
  s->S += dev >> c->k;

  int z = 0;                                         /* tercer índice */
  if (c->ter == 1) z = d < 0 ? 0 : d > 0 ? 2 : 1;
  else if (c->ter == 2) {
    int ad = d < 0 ? -d : d;
    s->V += ((ad << 8) - s->V) >> c->kv;
    z = s->V > c->uv;
  } else if (c->ter == 3) z = d < 0;

  int mitad = c->nb / 2;
  int th_in = c->c * c->E / 8 + c->ui, th_out = c->c * c->X / 8 + c->uo;           /* modo 0, precio por 2^10 */
  int alto = (1 << (c->bits - 1)) + (1 << (c->bits - 2)), bajo = (1 << (c->bits - 1)) - (1 << (c->bits - 2));

  /* Aprendizaje: la decisión del tick u se ejecutó al precio u+1; h ticks después se conoce su resultado. */
  if (c->ka && s->n >= c->h + 1) {
    int u = s->n - 1 - c->h;
    int su = s->st[u & (ANILLO - 1)];
    int R = pr - s->pr[(u + 1) & (ANILLO - 1)];
    if (c->modo == 0) {
      if (R > RMAX) R = RMAX;
      if (R < -RMAX) R = -RMAX;
      if (c->dir) s->T[su] += ((R << FQ) - s->T[su]) >> c->ka;      /* forma directa: redondea hacia abajo */
      else s->T[su] += (R << FQ) - (s->T[su] >> c->ka);
    }
    else if (R > c->g) { if (s->T[su] < (1 << c->bits) - 1) s->T[su]++; }
    else if (R < -c->g) { if (s->T[su] > 0) s->T[su]--; }
    if (c->banda) {                                  /* la casilla recién ajustada puede correr un borde */
      int zu = su / c->nb;
      int *eb = &s->eb[zu], *xb = &s->xb[zu];
      int eb0 = mitad - (c->E >> c->sh), xb0 = mitad + (c->X >> c->sh);
      const int *T = &s->T[zu * c->nb];
      if (*eb < eb0 + c->lim && *eb < c->nb - 1 && (T[*eb] >> c->ks) > th_in + c->mg) (*eb)++;
      else if (*eb > eb0 - c->lim && *eb > 1 && (T[*eb - 1] >> c->ks) < th_in - c->mg) (*eb)--;
      if (*xb > xb0 - c->lim && *xb > 1 && (T[*xb - 1] >> c->ks) < th_out - c->mg) (*xb)--;
      else if (*xb < xb0 + c->lim && *xb < c->nb - 1 && (T[*xb] >> c->ks) > th_out + c->mg) (*xb)++;
    }
  }

  int idx = ((dev - s->pos) >> c->sh) + mitad;
  if (idx < 0) idx = 0;
  if (idx > c->nb - 1) idx = c->nb - 1;
  int fila = c->filas == 2 ? s->pos : 0;
  int st = (fila * c->nt + z) * c->nb + idx;
  int v = s->T[st] >> c->ks;

  /* Umbral de compra según el último cambio: es una regla fija distinta de max_media, no aprendizaje. */
  int ez = c->ter == 3 ? (z ? c->ezb : c->ezi) : c->ter == 1 ? (z == 0 ? c->ezb : z == 1 ? c->ezi : c->ezs) : 0;
  int entra, sale;
  if (c->banda) { entra = idx < s->eb[z]; sale = idx >= s->xb[z]; }
  else if (c->modo == 0) { entra = v > th_in + c->c * ez / 8; sale = v < th_out; }
  else { entra = v >= alto; sale = v <= bajo; }
  int entra_regla = dev < -(c->E + ez), sale_regla = dev > c->X;
  if (s->pos) {
    if (sale != sale_regla) s->n_dif++;
    if (sale) s->pos = 0;
  } else {
    if (entra != entra_regla) s->n_dif++;
    if (entra) { s->pos = 1; s->n_ent++; }
  }

  s->st[s->n & (ANILLO - 1)] = (short)st;
  s->pr[s->n & (ANILLO - 1)] = (unsigned char)pr;
  s->n++;
  int decision = s->pos ? COMPRAR_63 : VENDER_63;
  if (c->ref && instancia_decidir(c->ref, pr, propia) != decision) s->n_cmp++;
  return decision;
}

/* aux: ticks en que la tabla decide distinto que la regla desde la misma posición, entradas,
 * corrimiento final del borde de compra (banda=1, z=0) y ticks distintos de max_media (cmp=1). */
static void contadores(const void *estado, int aux[4]) {
  const Estado *s = estado;
  const Cfg *c = s->c;
  aux[0] = s->n_dif; aux[1] = s->n_ent;
  aux[2] = c->banda && s->ini ? s->eb[0] - (c->nb / 2 - (c->E >> c->sh)) : 0;
  aux[3] = s->n_cmp;
}

static const Estrategia tabla = {
  "tabla", "tabla de politica que parte de max_media y se ajusta en vivo (r4c). Con ka=0 es max_media",
  sizeof(Cfg), sizeof(Estado), configurar, iniciar, decidir, contadores, liberar};
REGISTRAR_ESTRATEGIA(tabla)
