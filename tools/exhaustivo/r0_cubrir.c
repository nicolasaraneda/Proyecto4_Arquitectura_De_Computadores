/* r0_cubrir.c: series que recorren todas las combinaciones (estado, precio) de la regla de R0.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * La regla de sw/trade.s (max_media, ref/trader.py) tiene como estado S (32 veces la
 * media, de 32 a 8160) y pos (0 afuera, 1 adentro). Con cada precio p de 1 a 255:
 *     dev = 32 p - S
 *     pos = (pos | dev < -96) & (dev < 1)
 *     S   = S + p - ceil(S / 32)
 * y la decisión es comprar 63 si pos = 1 y vender 63 si no.
 *
 * Este programa calcula qué estados (S, pos) son alcanzables desde algún primer precio
 * (S = 32 p0, pos = 0) y arma K series de precios que, juntas, aplican cada precio de 1 a
 * 255 en cada estado alcanzable al menos una vez. Cada serie parte desde el reset de la
 * placa (los primeros 24 precios iguales, para que el programa vea su primer precio
 * aunque pierda los que llegan durante el reset) y se encarga de una franja de S. Cuando
 * en el estado actual ya no quedan precios por probar de su franja, busca por anchura el
 * estado más cercano que todavía tenga y lo alcanza.
 *
 * El conteo de combinaciones cubiertas no se confía a este programa: lo rehace
 * tools/exhaustivo/r0.py con ref/trader.py sobre las series generadas.
 *
 * Uso: r0_cubrir K CARPETA      (deja CARPETA/serie_00.csv ... y un resumen en la salida)
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SMIN 32
#define SMAX 8160
#define NS ((SMAX + 1) * 2)
#define PAD 24

static inline int idx(int S, int pos) { return S * 2 + pos; }
static inline int ceil32(int S) { return (S + 31) >> 5; }
static inline int sig(int i, int p) {
  int S = i >> 1, pos = i & 1, dev = 32 * p - S;
  int np = (pos | (dev < -96)) & (dev < 1);
  return idx(S + p - ceil32(S), np);
}

static unsigned char alc[NS];
static uint64_t pend[NS][4];       /* bit p-1: falta aplicar el precio p en el estado */
static int npend[NS];
static int cola[NS], padre[NS], ppadre[NS], visto[NS];
static int sello = 0;
static int esquina[NS], nesq = 0;

/* Un paso del controlador que lleva el estado actual hacia (St, pt). Ver el razonamiento en
 * docs/verificacion_exhaustiva.md: para llegar con pos = 0 se llega desde abajo (sale);
 * para llegar con pos = 1 se baja desde 4 o más unidades de S arriba (entra) o se baja
 * conservando pos = 1 (dev < 1 en cada paso). */
static int paso_hacia(int cur, int St, int pt) {
  int S = cur >> 1, pos = cur & 1, m = ceil32(S), d = St - S, p;
  if (pt == 0) {
    if (d > 0) p = m + d;                     /* sube y sale */
    else p = m + d - 1;                       /* baja a St - 1 para después subir */
  } else if (pos == 1 && d < 0) {
    p = m + d;                                /* baja conservando pos = 1 */
  } else if (pos == 0 && S >= 129 && -d >= 4) {
    p = m + d;                                /* baja 4 o más y entra */
  } else {
    int U = St + 4 > 133 ? St + 4 : 133;      /* sube a donde se pueda bajar entrando */
    p = m + (U - S);
  }
  if (p < 1) p = 1;
  if (p > 255) p = 255;
  return p;
}

static int pendiente(int i, int p) { return (pend[i][(p - 1) >> 6] >> ((p - 1) & 63)) & 1; }

int main(int argc, char **argv) {
  if (argc < 3) { fprintf(stderr, "uso: r0_cubrir K CARPETA\n"); return 2; }
  setvbuf(stdout, NULL, _IOLBF, 0);
  int K = atoi(argv[1]);
  const char *dir = argv[2];
  /* 1. alcanzables */
  int n = 0, h = 0;
  for (int p0 = 1; p0 <= 255; p0++) { int i = idx(32 * p0, 0); if (!alc[i]) { alc[i] = 1; cola[n++] = i; } }
  while (h < n) {
    int i = cola[h++];
    for (int p = 1; p <= 255; p++) { int j = sig(i, p); if (!alc[j]) { alc[j] = 1; cola[n++] = j; } }
  }
  long casos = 0; int est0 = 0, est1 = 0;
  for (int i = 0; i < NS; i++) if (alc[i]) {
    npend[i] = 255; casos += 255; if (i & 1) est1++; else est0++;
    for (int p = 1; p <= 255; p++) pend[i][(p - 1) >> 6] |= 1ULL << ((p - 1) & 63);
  }
  printf("Estados alcanzables: %d (%d con pos = 0 y %d con pos = 1). Combinaciones (estado, precio): %ld\n",
         est0 + est1, est0, est1, casos);
  /* 2. franjas de S con la misma cantidad de casos */
  int corte[256]; corte[0] = SMIN; { long acum = 0; int k = 1;
    for (int S = SMIN; S <= SMAX && k < K; S++) {
      acum += (alc[idx(S, 0)] + alc[idx(S, 1)]) * 255L;
      if (acum >= casos * k / K) corte[k++] = S + 1;
    } }
  /* 3. un recorrido por franja */
  long total_ticks = 0, total_bfs = 0;
  int *buf = malloc(sizeof(int) * 60000000);
  for (int k = 0; k < K; k++) {
    int lo = corte[k], hi = k + 1 < K ? corte[k + 1] - 1 : SMAX;
    int p0 = ((lo + hi) / 2 + 16) / 32; if (p0 < 1) p0 = 1; if (p0 > 255) p0 = 255;
    int len = 0, cur = idx(32 * p0, 0);
    for (int t = 0; t < PAD; t++) buf[len++] = p0;
    /* estados de la franja que no se alcanzan desde su primer precio: quedan para la esquina */
    sello++;
    { int a = 0, b = 0; cola[b++] = cur; visto[cur] = sello;
      while (a < b) { int i = cola[a++];
        for (int p = 1; p <= 255; p++) { int j = sig(i, p); if (visto[j] != sello) { visto[j] = sello; cola[b++] = j; } } } }
    for (int S = lo; S <= hi; S++) for (int q = 0; q < 2; q++) {
      int i = idx(S, q);
      if (alc[i] && visto[i] != sello && npend[i]) esquina[nesq++] = i;
    }
    int sello_franja = sello;
    long faltan = 0;
    for (int S = lo; S <= hi; S++) for (int q = 0; q < 2; q++)
      if (visto[idx(S, q)] == sello) faltan += npend[idx(S, q)];
    int nbfs = 0;
    while (faltan > 0) {
      int S = cur >> 1;
      if (S >= lo && S <= hi && npend[cur] && visto[cur] == sello_franja) {
        int elegido = -1;
        for (int p = 1; p <= 255; p++) {
          if (!pendiente(cur, p)) continue;
          if (elegido < 0) elegido = p;
          int j = sig(cur, p), Sj = j >> 1;
          if (Sj >= lo && Sj <= hi && visto[j] == sello_franja && npend[j] > (j == cur)) { elegido = p; break; }
        }
        int p = elegido;
        pend[cur][(p - 1) >> 6] &= ~(1ULL << ((p - 1) & 63)); npend[cur]--; faltan--;
        buf[len++] = p; cur = sig(cur, p);
        continue;
      }
      /* el estado pendiente de la franja más cercano en S */
      int obj = -1;
      for (int dS = 0; dS <= SMAX && obj < 0; dS++) {
        int c[4] = {idx(S - dS, cur & 1), idx(S - dS, !(cur & 1)), idx(S + dS, cur & 1), idx(S + dS, !(cur & 1))};
        for (int q = 0; q < 4 && obj < 0; q++) {
          int Sc = c[q] >> 1;
          if (Sc >= lo && Sc <= hi && npend[c[q]] && visto[c[q]] == sello_franja) obj = c[q];
        }
      }
      if (obj < 0) { fprintf(stderr, "franja %d: no quedan estados pendientes pero faltan %ld\n", k, faltan); return 1; }
      /* controlador directo; si no llega en 4000 pasos, búsqueda por anchura */
      int pasos = 0, inicio = len, guardado = cur;
      while (cur != obj && pasos < 4000) {
        int p = paso_hacia(cur, obj >> 1, obj & 1);
        buf[len++] = p; cur = sig(cur, p); pasos++;
      }
      if (cur != obj) {
        len = inicio; cur = guardado; nbfs++;
        static int marca[NS]; static int sm = 0; sm++;
        int a = 0, b = 0, hallado = -1;
        cola[b++] = cur; marca[cur] = sm; padre[cur] = -1;
        while (a < b && hallado < 0) {
          int i = cola[a++];
          for (int p = 1; p <= 255; p++) {
            int j = sig(i, p);
            if (marca[j] == sm) continue;
            marca[j] = sm; padre[j] = i; ppadre[j] = p; cola[b++] = j;
            if (j == obj) { hallado = j; break; }
          }
        }
        if (hallado < 0) { fprintf(stderr, "franja %d: el estado S=%d pos=%d no se alcanza\n", k, obj >> 1, obj & 1); return 1; }
        int camino[20000], m = 0;
        for (int j = hallado; padre[j] >= 0; j = padre[j]) camino[m++] = ppadre[j];
        while (m > 0) buf[len++] = camino[--m];
        cur = hallado;
      }
    }
    char ruta[512];
    snprintf(ruta, sizeof ruta, "%s/serie_%02d.csv", dir, k);
    FILE *f = fopen(ruta, "w");
    if (!f) { perror(ruta); return 1; }
    fprintf(f, "tick,price\n");
    for (int t = 0; t < len; t++) fprintf(f, "%d,%d\n", t, buf[t]);
    fclose(f);
    printf("franja %2d: S de %4d a %4d, p0 = %3d, %8d ticks, %6d busquedas por anchura\n", k, lo, hi, p0, len, nbfs);
    total_ticks += len; total_bfs += nbfs;
  }
  printf("Total: %ld ticks en %d series, %.2f ticks por combinacion, %ld busquedas por anchura\n",
         total_ticks, K, (double)total_ticks / casos, total_bfs);
  /* 4. la esquina: estados que solo se alcanzan desde ciertos primeros precios. Una serie
   * corta por combinación pendiente, que parte del reset con el primer precio p0 que la
   * alcanza, llega por el camino más corto y aplica el precio. Van en un solo archivo de
   * lote (una serie por línea, los precios separados por espacios). */
  char ruta[512];
  snprintf(ruta, sizeof ruta, "%s/esquina.txt", dir);
  FILE *f = fopen(ruta, "w");
  long nser = 0, ntk = 0; int sinlugar = 0;
  static int marca2[NS], ini2[NS]; int sm2 = 0;
  for (int e = 0; e < nesq; e++) {
    int obj = esquina[e];
    /* camino más corto desde algún primer precio (búsqueda por anchura desde los 255 inicios) */
    sm2++; int a = 0, b = 0;
    for (int p0 = 1; p0 <= 255; p0++) { int i = idx(32 * p0, 0); if (marca2[i] != sm2) { marca2[i] = sm2; padre[i] = -1; ini2[i] = p0; cola[b++] = i; } }
    int hallado = (marca2[obj] == sm2) ? obj : -1;
    while (a < b && hallado < 0) { int i = cola[a++];
      for (int p = 1; p <= 255 && hallado < 0; p++) { int j = sig(i, p);
        if (marca2[j] == sm2) continue; marca2[j] = sm2; padre[j] = i; ppadre[j] = p; ini2[j] = ini2[i]; cola[b++] = j;
        if (j == obj) hallado = j; } }
    if (hallado < 0) { sinlugar++; continue; }
    int camino[20000], m = 0;
    for (int j = hallado; padre[j] >= 0; j = padre[j]) camino[m++] = ppadre[j];
    for (int p = 1; p <= 255; p++) {
      if (!pendiente(obj, p)) continue;
      for (int t = 0; t < PAD; t++) fprintf(f, "%d ", ini2[hallado]);
      for (int q = m - 1; q >= 0; q--) fprintf(f, "%d ", camino[q]);
      fprintf(f, "%d\n", p);
      nser++; ntk += PAD + m + 1;
      pend[obj][(p - 1) >> 6] &= ~(1ULL << ((p - 1) & 63)); npend[obj]--;
    }
  }
  fclose(f);
  long quedan = 0; for (int i = 0; i < NS; i++) if (alc[i]) quedan += npend[i];
  printf("Esquina: %d estados que no se alcanzan desde el primer precio de su franja, %ld series cortas, %ld ticks"
         " (%d sin camino). Combinaciones sin cubrir al final: %ld\n", nesq, nser, ntk, sinlugar, quedan);
  return 0;
}
