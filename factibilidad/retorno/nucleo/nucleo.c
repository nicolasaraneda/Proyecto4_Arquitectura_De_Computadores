/* nucleo.c: mercado, registro de estrategias, instancias, lotes de series y estadística.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * La contabilidad es la tarea `ejecutar` de tb/tb_proyecto_4.sv, con las
 * mismas operaciones enteras (la división de C trunca hacia cero, igual que
 * la de SystemVerilog). pruebas/validar.py la compara con ref/market.py.
 */
#include "nucleo.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---- Mercado -------------------------------------------------------------------------- */

void cuenta_iniciar(Cuenta *c, const Reglas *r) {
  memset(c, 0, sizeof *c);
  c->caja = r->caja0;
  c->w = r->caja0;
  c->peak = r->caja0;
}

int cuenta_ejecutar(Cuenta *c, const Reglas *r, int decision, int p) {
  int q = decision & 63, accion = (decision >> 6) & 3, hecho = 0;
  if (accion == 1) {                               /* comprar lo que alcance */
    int tope = (c->caja - r->comision) / p;
    if (q > tope) q = tope;
    if (q > 0) { c->caja -= q * p + r->comision; c->acciones += q; c->ordenes++; hecho = q; }
  } else if (accion == 2) {                        /* vender lo que se tenga */
    if (q > c->acciones) q = c->acciones;
    if (q > 0 && c->caja + q * p >= r->comision) { c->caja += q * p - r->comision; c->acciones -= q; c->ordenes++; hecho = -q; }
  }                                                /* 00 y 11: mantener */
  long long w = (long long)c->caja + (long long)c->acciones * p;
  if (w > 0x7fffffffLL || c->caja > 0x7fffffff - 63 * 255) c->desborde = 1;
  c->w = (int)w;
  if (c->w > c->peak) c->peak = c->w;
  if (c->peak - c->w > c->max_dd) c->max_dd = c->peak - c->w;
  c->ultima_q = hecho;
  return hecho;
}

int comprar_y_mantener(const unsigned char *precios, int n, const Reglas *r) {
  int q = (r->caja0 - r->comision) / precios[0];
  return r->caja0 - r->comision - q * precios[0] + q * precios[n - 1];
}

/* ---- Registro --------------------------------------------------------------------------- */

#define MAX_ESTRATEGIAS 64
#define MAX_ALIAS 256
#define MAX_RIVALES 256

static const Estrategia *g_estrategias[MAX_ESTRATEGIAS];
static int g_nestrategias;
typedef struct { const char *nombre, *spec, *descripcion; } Alias;
static Alias g_alias[MAX_ALIAS];
static int g_nalias;
typedef struct { const char *clase, *spec; } Rival;
static Rival g_rivales[MAX_RIVALES];
static int g_nrivales;

void nucleo_registrar(const Estrategia *e) {
  if (g_nestrategias == MAX_ESTRATEGIAS) { fprintf(stderr, "demasiadas estrategias\n"); exit(2); }
  for (int i = 0; i < g_nestrategias; i++)
    if (!strcmp(g_estrategias[i]->nombre, e->nombre)) { fprintf(stderr, "estrategia repetida: %s\n", e->nombre); exit(2); }
  g_estrategias[g_nestrategias++] = e;
}

void nucleo_alias(const char *nombre, const char *spec, const char *descripcion) {
  if (g_nalias == MAX_ALIAS) { fprintf(stderr, "demasiados alias\n"); exit(2); }
  g_alias[g_nalias++] = (Alias){nombre, spec, descripcion};
}

void nucleo_rival(const char *clase, const char *spec) {
  if (g_nrivales == MAX_RIVALES) { fprintf(stderr, "demasiados rivales\n"); exit(2); }
  g_rivales[g_nrivales++] = (Rival){clase, spec};
}

/* Acceso de solo lectura al registro (lo usan main.c y torneo.c). */
int nucleo_nestrategias(void) { return g_nestrategias; }
const Estrategia *nucleo_estrategia(int i) { return g_estrategias[i]; }
int nucleo_nalias(void) { return g_nalias; }
const char *nucleo_alias_nombre(int i) { return g_alias[i].nombre; }
const char *nucleo_alias_spec(int i) { return g_alias[i].spec; }
const char *nucleo_alias_desc(int i) { return g_alias[i].descripcion; }
int nucleo_nrivales(void) { return g_nrivales; }
const char *nucleo_rival_clase(int i) { return g_rivales[i].clase; }
const char *nucleo_rival_spec(int i) { return g_rivales[i].spec; }

int leer_campos(const char *texto, const Campo *campos, int n, char *error, size_t tam_error) {
  char copia[1024];
  if (!texto) return 0;
  if (strlen(texto) >= sizeof copia) { snprintf(error, tam_error, "parametros demasiado largos"); return 1; }
  strcpy(copia, texto);
  char *guarda = NULL;
  for (char *tok = strtok_r(copia, ", \t\r\n", &guarda); tok; tok = strtok_r(NULL, ", \t\r\n", &guarda)) {
    char *eq = strchr(tok, '=');
    if (!eq) { snprintf(error, tam_error, "parametro sin valor: %s", tok); return 1; }
    *eq = 0;
    int k;
    for (k = 0; k < n; k++)
      if (!strcmp(campos[k].nombre, tok)) { *campos[k].destino = (int)strtol(eq + 1, NULL, 0); break; }
    if (k == n) { snprintf(error, tam_error, "parametro desconocido: %s", tok); return 1; }
  }
  return 0;
}

/* ---- Instancias --------------------------------------------------------------------------- */

struct Instancia {
  const Estrategia *e;
  void *cfg, *estado;
  char spec[512];
};

Instancia *instancia_crear(const char *spec, char *error, size_t tam_error) {
  char nulo[8];
  if (!error) { error = nulo; tam_error = sizeof nulo; }
  for (int vuelta = 0; vuelta < 4; vuelta++) {      /* un alias puede apuntar a otro alias */
    int k;
    for (k = 0; k < g_nalias; k++)
      if (!strcmp(g_alias[k].nombre, spec)) { spec = g_alias[k].spec; break; }
    if (k == g_nalias) break;
  }
  if (strlen(spec) >= sizeof ((Instancia *)0)->spec) { snprintf(error, tam_error, "especificacion demasiado larga"); return NULL; }
  const char *dp = strchr(spec, ':');
  size_t largo = dp ? (size_t)(dp - spec) : strlen(spec);
  const Estrategia *e = NULL;
  for (int k = 0; k < g_nestrategias; k++)
    if (strlen(g_estrategias[k]->nombre) == largo && !strncmp(g_estrategias[k]->nombre, spec, largo)) e = g_estrategias[k];
  if (!e) { snprintf(error, tam_error, "estrategia desconocida: %s (ver el comando listar)", spec); return NULL; }
  Instancia *i = calloc(1, sizeof *i);
  i->e = e;
  strcpy(i->spec, spec);
  i->cfg = calloc(1, e->tam_cfg ? e->tam_cfg : 1);
  i->estado = calloc(1, e->tam_estado ? e->tam_estado : 1);
  if (e->configurar && e->configurar(i->cfg, dp ? dp + 1 : "", error, tam_error)) { instancia_destruir(i); return NULL; }
  return i;
}

void instancia_destruir(Instancia *i) {
  if (!i) return;
  if (i->e->liberar) i->e->liberar(i->cfg);
  free(i->cfg); free(i->estado); free(i);
}

void instancia_iniciar(Instancia *i, const Reglas *r, uint64_t semilla) {
  memset(i->estado, 0, i->e->tam_estado);
  if (i->e->iniciar) i->e->iniciar(i->estado, i->cfg, r, semilla);
}

int instancia_decidir(Instancia *i, int precio, const Cuenta *propia) {
  return i->e->decidir(i->estado, precio, propia) & 0xFF;
}

void instancia_contadores(const Instancia *i, int aux[4]) {
  aux[0] = aux[1] = aux[2] = aux[3] = 0;
  if (i->e->contadores) i->e->contadores(i->estado, aux);
}

const char *instancia_spec(const Instancia *i) { return i->spec; }

/* ---- Correr una serie ------------------------------------------------------------------------ */

Resultado correr_serie(Instancia *i, const unsigned char *precios, int n, const Reglas *r, uint64_t semilla,
                       int perdidos, unsigned char *leidos) {
  Cuenta c;
  Resultado res;
  int decision = MANTENER;                         /* DECISION parte en 0 */
  cuenta_iniciar(&c, r);
  instancia_iniciar(i, r, semilla);
  for (int t = 0; t < n; t++) {
    int p = precios[t];                            /* lo único que sale de la serie hacia la estrategia */
    if (leidos) leidos[t] = (unsigned char)decision;
    cuenta_ejecutar(&c, r, decision, p);           /* la maestra ejecuta la decisión anterior a este precio */
    if (t >= perdidos) {
      Cuenta copia = c;                            /* la estrategia no puede tocar la cuenta oficial */
      decision = instancia_decidir(i, p, &copia);
    }
  }
  res.w = c.w; res.ordenes = c.ordenes; res.max_dd = c.max_dd; res.desborde = c.desborde;
  res.byh = comprar_y_mantener(precios, n, r);
  instancia_contadores(i, res.aux);
  return res;
}

static uint64_t mezclar(uint64_t x) {              /* splitmix64 */
  x += 0x9E3779B97F4A7C15ULL;
  x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
  x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
  return x ^ (x >> 31);
}

uint64_t semilla_serie(const char *spec, int indice) {
  uint64_t h = 0xCBF29CE484222325ULL;              /* FNV-1a del texto */
  for (const char *p = spec; *p; p++) h = (h ^ (unsigned char)*p) * 0x100000001B3ULL;
  return mezclar(h ^ mezclar((uint64_t)indice + 1));
}

/* ---- Lotes ------------------------------------------------------------------------------------- */

#ifndef RETORNO_DIR
#define RETORNO_DIR "factibilidad/retorno"
#endif

const char *directorio_series(void) {
  const char *d = getenv("RETORNO_SERIES");
  return d && *d ? d : RETORNO_DIR "/build/series";
}

/* Huella del contenido de un lote: sirve para saber si un resultado guardado
 * se calculó con las mismas series. No es criptográfica. */
static uint64_t huella_datos(const unsigned char *d, size_t n, int ns, int ticks) {
  uint64_t h = 0x9E3779B97F4A7C15ULL ^ ((uint64_t)ns << 32) ^ (uint64_t)ticks;
  size_t i = 0;
  for (; i + 8 <= n; i += 8) {
    uint64_t w;
    memcpy(&w, d + i, 8);
    h = (h ^ w) * 0x100000001B3ULL;
    h ^= h >> 29;
  }
  for (; i < n; i++) h = (h ^ d[i]) * 0x100000001B3ULL;
  return mezclar(h);
}

Lote *lote_leer(const char *ruta) {
  FILE *f = fopen(ruta, "rb");
  if (!f) return NULL;
  int cab[2];
  if (fread(cab, sizeof(int), 2, f) != 2 || cab[0] <= 0 || cab[1] <= 0) { fclose(f); return NULL; }
  Lote *l = calloc(1, sizeof *l);
  l->ns = cab[0]; l->n = cab[1];
  size_t total = (size_t)l->ns * l->n;
  l->datos = malloc(total);
  if (fread(l->datos, 1, total, f) != total) { fclose(f); lote_liberar(l); return NULL; }
  fclose(f);
  const char *base = strrchr(ruta, '/');
  snprintf(l->nombre, sizeof l->nombre, "%s", base ? base + 1 : ruta);
  l->partes = 1;
  snprintf(l->archivo[0], sizeof l->archivo[0], "%.63s", l->nombre);
  char *punto = strrchr(l->archivo[0], '.');
  if (punto) *punto = 0;
  snprintf(l->parte[0], sizeof l->parte[0], "%.31s", l->archivo[0]);
  l->inicio[0] = 0; l->inicio[1] = l->ns; l->total[0] = l->ns;
  l->huella[0] = huella_datos(l->datos, total, l->ns, l->n);
  return l;
}

void lote_liberar(Lote *l) {
  if (!l) return;
  free(l->datos); free(l);
}

static const char *PLAUSIBLES[] = {"modelo", "modelo_vecino", "dos_componentes", "cambio_volatilidad", NULL};
static const char *ESTRES[] = {"paseo", "tendencia", "reversion", "saltos", "cambio_de_caracter", "volatil", "nivel_bajo", NULL};
static const char *DEGENERADAS[] = {"plana", "borde_bajo", "borde_alto", NULL};

/* Agrega al lote `l` las primeras `tomar` series del archivo de la familia (todas si tomar <= 0). */
static int agregar(Lote *l, const char *familia, int largo, int semilla, int tomar) {
  char ruta[1024];
  if (!strcmp(familia, "bloques") || !strcmp(familia, "practica"))
    snprintf(ruta, sizeof ruta, "%s/%s_n%d.bin", directorio_series(), familia, largo);
  else
    snprintf(ruta, sizeof ruta, "%s/%s_s%d_n%d.bin", directorio_series(), familia, semilla, largo);
  Lote *p = lote_leer(ruta);
  if (!p) { fprintf(stderr, "no se pudo leer %s (falta correr generar_series.py?)\n", ruta); return 1; }
  if (p->n != largo) { fprintf(stderr, "%s: tiene %d ticks y se pidieron %d\n", ruta, p->n, largo); lote_liberar(p); return 1; }
  if (tomar <= 0 || tomar > p->ns) tomar = p->ns;
  l->n = largo;
  l->datos = realloc(l->datos, (size_t)(l->ns + tomar) * largo);
  memcpy(l->datos + (size_t)l->ns * largo, p->datos, (size_t)tomar * largo);
  snprintf(l->parte[l->partes], sizeof l->parte[0], "%s", familia);
  snprintf(l->archivo[l->partes], sizeof l->archivo[0], "%s", p->archivo[0]);
  l->total[l->partes] = p->ns;
  l->huella[l->partes] = p->huella[0];
  l->inicio[l->partes] = l->ns;
  l->ns += tomar;
  l->inicio[++l->partes] = l->ns;
  lote_liberar(p);
  return 0;
}

Lote *conjunto_leer(const char *conjunto, int largo, int semilla) {
  Lote *l = calloc(1, sizeof *l);
  int mal = 0;
  snprintf(l->nombre, sizeof l->nombre, "%s, semilla %d, %d ticks", conjunto, semilla, largo);
  if (!strcmp(conjunto, "plausibles")) {
    for (const char **f = PLAUSIBLES; *f && !mal; f++) mal = agregar(l, *f, largo, semilla, 0);
  } else if (!strcmp(conjunto, "estres")) {
    for (const char **f = ESTRES; *f && !mal; f++) mal = agregar(l, *f, largo, semilla, 0);
  } else if (!strcmp(conjunto, "degeneradas")) {
    for (const char **f = DEGENERADAS; *f && !mal; f++) mal = agregar(l, *f, largo, semilla, 0);
  } else if (!strcmp(conjunto, "evidencia")) {
    /* Las dos evidencias con el mismo peso: todos los remuestreos y la misma
     * cantidad de series plausibles, repartida entre las cuatro familias. */
    mal = agregar(l, "remuestreo", largo, semilla, 0);
    int cuarto = l->ns / 4;
    for (const char **f = PLAUSIBLES; *f && !mal; f++) mal = agregar(l, *f, largo, semilla, cuarto);
  } else {
    if (!strcmp(conjunto, "bloques") || !strcmp(conjunto, "practica"))
      snprintf(l->nombre, sizeof l->nombre, "%s, %d ticks", conjunto, largo);
    mal = agregar(l, conjunto, largo, semilla, 0);
  }
  if (mal) { lote_liberar(l); return NULL; }
  return l;
}

int evaluar_lote(const char *spec, const Lote *l, const Reglas *r, Resultado *res) {
  int mal = 0;
  char error[256] = "";
  Instancia *prueba = instancia_crear(spec, error, sizeof error);
  if (!prueba) { fprintf(stderr, "%s\n", error); return 1; }
  char resuelta[512];
  strcpy(resuelta, instancia_spec(prueba));
  instancia_destruir(prueba);
  const char *h = getenv("HILOS");
  int hilos = h && atoi(h) > 0 ? atoi(h) : 6;
#pragma omp parallel num_threads(hilos)
  {
    Instancia *inst = instancia_crear(resuelta, NULL, 0);
#pragma omp for schedule(dynamic, 8)
    for (int i = 0; i < l->ns; i++) {
      if (!inst) { mal = 1; continue; }
      int k = 0;
      while (k + 1 < l->partes && i >= l->inicio[k + 1]) k++;
      res[i] = correr_serie(inst, l->datos + (size_t)i * l->n, l->n, r, semilla_serie(resuelta, i - l->inicio[k]), 0, NULL);
    }
    instancia_destruir(inst);
  }
  return mal;
}

/* ---- Estadística ----------------------------------------------------------------------------------- */

void azar_sembrar(Azar *a, uint64_t semilla) {
  for (int k = 0; k < 4; k++) { semilla = mezclar(semilla + k); a->s[k] = semilla; }
}

static uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }

uint64_t azar_u64(Azar *a) {                        /* xoshiro256** */
  uint64_t *s = a->s, res = rotl(s[1] * 5, 7) * 9, t = s[1] << 17;
  s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
  return res;
}

double azar_u01(Azar *a) { return (double)(azar_u64(a) >> 11) * (1.0 / 9007199254740992.0); }

int azar_entero(Azar *a, int n) { return (int)(azar_u01(a) * n); }

static int cmp_double(const void *a, const void *b) {
  double x = *(const double *)a, y = *(const double *)b;
  return (x > y) - (x < y);
}

double percentil(const double *x, int n, double q) {
  double *o = malloc(sizeof(double) * (size_t)n);
  memcpy(o, x, sizeof(double) * (size_t)n);
  qsort(o, (size_t)n, sizeof(double), cmp_double);
  int k = (int)(q * n);
  if (k > n - 1) k = n - 1;
  double v = o[k];
  free(o);
  return v;
}

Resumen resumir(const double *x, int n) {
  Resumen r = {0, 0, 0, 0, 0, 0, n};
  if (n <= 0) return r;
  double *o = malloc(sizeof(double) * (size_t)n), s = 0, s2 = 0;
  memcpy(o, x, sizeof(double) * (size_t)n);
  qsort(o, (size_t)n, sizeof(double), cmp_double);
  for (int i = 0; i < n; i++) s += o[i];
  r.media = s / n;
  for (int i = 0; i < n; i++) s2 += (o[i] - r.media) * (o[i] - r.media);
  r.ee = n > 1 ? sqrt(s2 / (n - 1) / n) : 0;
  int k5 = (int)(0.05 * n), k50 = (int)(0.5 * n);
  r.p5 = o[k5 > n - 1 ? n - 1 : k5];
  r.mediana = o[k50 > n - 1 ? n - 1 : k50];
  r.peor = o[0]; r.mejor = o[n - 1];
  free(o);
  return r;
}

void pareada(const double *a, const double *b, int n, double *media, double *ee) {
  double s = 0, s2 = 0;
  for (int i = 0; i < n; i++) s += a[i] - b[i];
  *media = s / n;
  for (int i = 0; i < n; i++) { double d = a[i] - b[i] - *media; s2 += d * d; }
  *ee = n > 1 ? sqrt(s2 / (n - 1) / n) : 0;
}
