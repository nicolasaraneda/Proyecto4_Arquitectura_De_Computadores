/* descomp.c: de qué está hecho el costo de la ejecución de una estrategia.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 *   build/descomp --estrategia max_media --conjunto evidencia --largo 2000 --semilla 0 [--interior | --parada]
 *
 * Corre la estrategia con el mismo lazo y la misma contabilidad del arnés
 * (enlaza nucleo.c: cuenta_ejecutar e instancias) y anota cada orden que la
 * maestra ejecuta. No cambia nada del resultado: comprueba que el patrimonio
 * de cada serie es el de correr_serie.
 *
 * Clases de orden:
 *   primera        la primera compra desde que no hay acciones, o la primera venta después de una compra
 *   continuación   la orden anterior, en el tick anterior, ejecutó exactamente 63 acciones: esta orden
 *                  existe porque la posición no cabía en una orden. Es el costo del límite de 63
 *   recompra       compra con la posición ya completa: el precio bajó y la caja que sobraba alcanza
 *                  para alguna acción más. No depende del límite
 *
 * Posición: desde la primera compra hasta que no quedan acciones. La ganancia
 * bruta de una compra es cantidad x (precio medio de venta de la posición -
 * precio de la compra), sin comisiones. Si la ronda termina con la posición
 * abierta, lo que queda se valora al último precio.
 *
 * Precio de las continuaciones: diferencia entre el precio de cada
 * continuación y el de la primera orden de su racha (ticks seguidos con orden
 * ejecutada). Entrada: cantidad x (precio de la continuación - precio de la
 * primera compra). Salida: cantidad x (precio de la primera venta - precio de
 * la continuación). Positivo es peor precio. OJO: no es el costo de la
 * demora. Una continuación solo existe si la señal no cambió antes, o sea si
 * el precio no se devolvió, así que la muestra está sesgada hacia los casos
 * en que esperar salió bien, y además pesa por acciones (dominan las series
 * con mucho patrimonio o precio bajo). El dato limpio es el camino del precio
 * después de la primera orden, que no condiciona a nada, y la cota de
 * cota/medir_cota.py, que compara la ronda completa con y sin límite.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "nucleo.h"

#define INTERIOR_MIN 21        /* los mismos valores de nucleo/main.c */
#define INTERIOR_MAX 249
#define PARADA_MIN 200

#define CAMINO 8
enum { PRIMERA, CONTINUACION, RECOMPRA, NCLASES };
static const char *CLASES[NCLASES] = {"primera", "continuacion", "recompra"};
#define NTAM 7
static const int TAM_MIN[NTAM] = {1, 2, 4, 8, 16, 32, 63};
static const char *TAM_NOMBRE[NTAM] = {"1", "2-3", "4-7", "8-15", "16-31", "32-62", "63"};

typedef struct {
  double n, acciones, bruta;   /* órdenes, acciones y ganancia bruta atribuida (solo compras) */
} Celda;

typedef struct {
  Celda compra[NCLASES][NTAM], venta[NCLASES][NTAM];
  double series, ticks, posiciones, acciones_pos, ordenes;
  double demora_entrada, acc_demora_entrada, demora_salida, acc_demora_salida;
  double bruta_total, acciones_compradas, comisiones, w, ordenes_entrada, ordenes_salida;
  double distintas;
  double pos_ordenes[9];       /* posiciones según las órdenes de compra de su entrada (1..8) */
  /* camino del precio después de la primera compra y de la primera venta, sin condicionar a lo que pase después */
  double camino_e[CAMINO + 1], camino_e2[CAMINO + 1], n_camino_e[CAMINO + 1];
  double camino_s[CAMINO + 1], camino_s2[CAMINO + 1], n_camino_s[CAMINO + 1];
  double senal_e, senal_e2, n_senal_e, senal_s, senal_s2, n_senal_s;   /* precio de ejecución menos precio de la señal */
} Total;

static int tam_indice(int q) {
  int k = 0;
  while (k + 1 < NTAM && q >= TAM_MIN[k + 1]) k++;
  return k;
}

typedef struct { int clase, q, p; } Compra;

static void una_serie(Instancia *inst, const unsigned char *precios, int n, const Reglas *r, uint64_t semilla, Total *T) {
  Cuenta c;
  int decision = MANTENER;
  cuenta_iniciar(&c, r);
  instancia_iniciar(inst, r, semilla);
  static Compra compras[4096];
  int nc = 0;                  /* compras de la posición abierta */
  double venta_valor = 0, venta_acc = 0;
  int q_ant = 0;               /* acciones de la orden ejecutada en el tick anterior (con signo) */
  int p_primera_compra = 0, p_primera_venta = 0, ordenes_entrada = 0, en_entrada = 0;
  int ultimo_fue_compra = 0;
  for (int t = 0; t < n; t++) {
    int p = precios[t];
    int antes = c.acciones;
    int q = cuenta_ejecutar(&c, r, decision, p);
    if (q > 0) {
      int clase;
      if (antes == 0) {
        clase = PRIMERA; p_primera_compra = p; nc = 0; venta_valor = venta_acc = 0; T->posiciones++; ordenes_entrada = 1; en_entrada = 1;
        for (int j = 1; j <= CAMINO && t + j < n; j++) {
          double d = precios[t + j] - p;
          T->camino_e[j] += d; T->camino_e2[j] += d * d; T->n_camino_e[j]++;
        }
        if (t > 0) { double d = p - precios[t - 1]; T->senal_e += d; T->senal_e2 += d * d; T->n_senal_e++; }
      }
      else if (q_ant == 63) {
        clase = CONTINUACION;
        T->demora_entrada += (double)q * (p - p_primera_compra); T->acc_demora_entrada += q;
        if (en_entrada) ordenes_entrada++;
      } else {
        clase = RECOMPRA; p_primera_compra = p;      /* empieza otra racha de compras: la referencia es esta */
        if (en_entrada) { T->pos_ordenes[ordenes_entrada > 8 ? 8 : ordenes_entrada]++; en_entrada = 0; }
      }
      Celda *x = &T->compra[clase][tam_indice(q)];
      x->n++; x->acciones += q;
      if (nc < 4096) compras[nc++] = (Compra){clase, q, p};
      T->acciones_compradas += q;
      T->ordenes_entrada += clase != RECOMPRA;
      ultimo_fue_compra = 1;
    } else if (q < 0) {
      int clase;
      if (ultimo_fue_compra || q_ant != -63) {
        clase = PRIMERA; p_primera_venta = p;
        for (int j = 1; j <= CAMINO && t + j < n; j++) {
          double d = precios[t + j] - p;
          T->camino_s[j] += d; T->camino_s2[j] += d * d; T->n_camino_s[j]++;
        }
        if (t > 0) { double d = p - precios[t - 1]; T->senal_s += d; T->senal_s2 += d * d; T->n_senal_s++; }
      }
      else { clase = CONTINUACION; T->demora_salida += (double)(-q) * (p_primera_venta - p); T->acc_demora_salida += -q; }
      Celda *x = &T->venta[clase][tam_indice(-q)];
      x->n++; x->acciones += -q;
      venta_valor += (double)(-q) * p; venta_acc += -q;
      T->ordenes_salida++;
      ultimo_fue_compra = 0;
      if (en_entrada) { T->pos_ordenes[ordenes_entrada > 8 ? 8 : ordenes_entrada]++; en_entrada = 0; }
    }
    /* la posición se cerró: reparte la ganancia bruta entre sus compras */
    if (q < 0 && c.acciones == 0 && nc > 0) {
      double pm = venta_valor / venta_acc;
      for (int i = 0; i < nc; i++) {
        double g = compras[i].q * (pm - compras[i].p);
        T->compra[compras[i].clase][tam_indice(compras[i].q)].bruta += g;
        T->bruta_total += g;
      }
      T->acciones_pos += venta_acc;
      nc = 0;
    }
    q_ant = q;
    Cuenta copia = c;
    decision = instancia_decidir(inst, p, &copia);
  }
  if (nc > 0) {                /* posición abierta al final: lo que queda, al último precio */
    double valor = venta_valor + (double)c.acciones * precios[n - 1], acc = venta_acc + c.acciones;
    double pm = valor / acc;
    for (int i = 0; i < nc; i++) {
      double g = compras[i].q * (pm - compras[i].p);
      T->compra[compras[i].clase][tam_indice(compras[i].q)].bruta += g;
      T->bruta_total += g;
    }
    T->acciones_pos += acc;
    if (en_entrada) T->pos_ordenes[ordenes_entrada > 8 ? 8 : ordenes_entrada]++;
  }
  T->series++; T->ticks += n; T->ordenes += c.ordenes; T->comisiones += (double)c.ordenes * r->comision; T->w += c.w;
  Resultado ref = correr_serie(inst, precios, n, r, semilla, 0, NULL);
  if (ref.w != c.w || ref.ordenes != c.ordenes) T->distintas++;
}

static const char *opcion(int argc, char **argv, const char *nombre, const char *defecto) {
  for (int i = 1; i + 1 < argc; i++)
    if (!strcmp(argv[i], nombre)) return argv[i + 1];
  return defecto;
}

static int bandera(int argc, char **argv, const char *nombre) {
  for (int i = 1; i < argc; i++)
    if (!strcmp(argv[i], nombre)) return 1;
  return 0;
}

int main(int argc, char **argv) {
  const char *nombre = opcion(argc, argv, "--estrategia", "max_media"), *conjunto = opcion(argc, argv, "--conjunto", "evidencia");
  int largo = atoi(opcion(argc, argv, "--largo", "2000")), semilla = atoi(opcion(argc, argv, "--semilla", "0"));
  int interior = bandera(argc, argv, "--interior"), parada = bandera(argc, argv, "--parada");
  Reglas r = {atoi(opcion(argc, argv, "--caja", "10000")), atoi(opcion(argc, argv, "--comision", "5"))};
  char spec[600], error[256];
  snprintf(spec, sizeof spec, "cand:%s", nombre);
  Instancia *inst = instancia_crear(spec, error, sizeof error);
  if (!inst) inst = instancia_crear(nombre, error, sizeof error);
  if (!inst) { fprintf(stderr, "%s\n", error); return 2; }
  Lote *l = conjunto_leer(conjunto, largo, semilla);
  if (!l) return 2;

  Total T;
  memset(&T, 0, sizeof T);
  for (int i = 0; i < l->ns; i++) {
    const unsigned char *p = l->datos + (size_t)i * l->n;
    int n = l->n, dentro = 1, j = 0;
    while (j < n && p[j] >= INTERIOR_MIN && p[j] <= INTERIOR_MAX) j++;
    if (j < n) dentro = 0;
    if (interior && !dentro) continue;
    if (parada) { n = j < l->n ? j + 1 : l->n; if (n < PARADA_MIN) n = PARADA_MIN < l->n ? PARADA_MIN : l->n; }
    int k = 0;
    while (k + 1 < l->partes && i >= l->inicio[k + 1]) k++;
    una_serie(inst, p, n, &r, semilla_serie(instancia_spec(inst), i - l->inicio[k]), &T);
  }

  double S = T.series, por2000 = 2000.0 * S / T.ticks;      /* factor para llevar un promedio por serie a 2000 ticks */
  printf("=== Descomposicion de la ejecucion: %s (%s) ===\n", nombre, instancia_spec(inst));
  printf("Conjunto %s, %d ticks, semilla %d%s: %.0f series, %.0f ticks de media. Caja %d, comision %d.\n", conjunto, largo, semilla,
         interior ? ", solo interiores" : parada ? ", vista de parada" : "", S, T.ticks / S, r.caja0, r.comision);
  printf("Comprobacion contra correr_serie: %.0f series con patrimonio u ordenes distintos.\n", T.distintas);
  printf("Promedios por serie. Entre parentesis, llevado a 2000 ticks.\n\n");
  printf("Patrimonio final %.0f. Ordenes %.1f (%.1f). Comisiones %.0f (%.0f).\n", T.w / S, T.ordenes / S, T.ordenes / S * por2000,
         T.comisiones / S, T.comisiones / S * por2000);
  printf("Posiciones (entradas) %.2f (%.2f). Acciones por posicion %.1f. Ganancia bruta por accion comprada %.3f.\n", T.posiciones / S,
         T.posiciones / S * por2000, T.acciones_pos / T.posiciones, T.bruta_total / T.acciones_compradas);
  printf("Ganancia bruta por posicion %.1f. Ordenes de compra por entrada %.2f, de venta por salida %.2f.\n", T.bruta_total / T.posiciones,
         T.ordenes_entrada / T.posiciones, T.ordenes_salida / T.posiciones);
  double tp = 0;
  for (int k = 1; k <= 8; k++) tp += T.pos_ordenes[k];
  printf("Posiciones segun las ordenes de compra de su entrada:");
  for (int k = 1; k <= 8; k++) printf(" %d%s: %.1f%%", k, k == 8 ? "+" : "", 100 * T.pos_ordenes[k] / (tp > 0 ? tp : 1));
  printf("\n\n");

  printf("Ordenes por clase y por acciones ejecutadas (promedio por serie)\n");
  printf("%-7s %-13s %-6s | %8s %9s %9s | %10s %11s %12s\n", "lado", "clase", "tamano", "ordenes", "acciones", "comision", "bruta",
         "bruta/orden", "bruta/accion");
  for (int lado = 0; lado < 2; lado++)
    for (int cl = 0; cl < NCLASES; cl++) {
      Celda tot = {0, 0, 0};
      for (int k = 0; k < NTAM; k++) {
        const Celda *x = lado ? &T.venta[cl][k] : &T.compra[cl][k];
        tot.n += x->n; tot.acciones += x->acciones; tot.bruta += x->bruta;
        if (x->n == 0) continue;
        printf("%-7s %-13s %-6s | %8.3f %9.2f %9.2f |", lado ? "venta" : "compra", CLASES[cl], TAM_NOMBRE[k], x->n / S, x->acciones / S,
               x->n * r.comision / S);
        if (!lado) printf(" %10.2f %11.2f %12.3f", x->bruta / S, x->bruta / x->n, x->bruta / x->acciones);
        printf("\n");
      }
      if (tot.n == 0) continue;
      printf("%-7s %-13s %-6s | %8.3f %9.2f %9.2f |", lado ? "venta" : "compra", CLASES[cl], "total", tot.n / S, tot.acciones / S,
             tot.n * r.comision / S);
      if (!lado) printf(" %10.2f %11.2f %12.3f", tot.bruta / S, tot.bruta / tot.n, tot.bruta / tot.acciones);
      printf("\n");
    }

  double ncc = 0, ncv = 0, nrc = 0;
  for (int k = 0; k < NTAM; k++) { ncc += T.compra[CONTINUACION][k].n; ncv += T.venta[CONTINUACION][k].n; nrc += T.compra[RECOMPRA][k].n; }
  printf("\nOrdenes que existen por el limite de 63 acciones (promedio por serie; entre parentesis por cada 2000 ticks)\n");
  printf("  comisiones de las continuaciones de compra   %8.2f (%.2f)   %.2f ordenes\n", ncc * r.comision / S, ncc * r.comision / S * por2000, ncc / S);
  printf("  comisiones de las continuaciones de venta    %8.2f (%.2f)   %.2f ordenes\n", ncv * r.comision / S, ncv * r.comision / S * por2000, ncv / S);
  printf("  suma de comisiones de las continuaciones     %8.2f (%.2f)   %.2f %% del patrimonio final\n", (ncc + ncv) * r.comision / S,
         (ncc + ncv) * r.comision / S * por2000, 100 * (ncc + ncv) * r.comision / T.w);
  printf("Precio de las continuaciones contra la primera orden de su racha (sesgado: solo existen si la senal no cambio; ver el encabezado)\n");
  printf("  compras: precio de mas                       %8.2f (%.2f)   %+.4f de precio por accion, %.1f acciones\n",
         T.demora_entrada / S, T.demora_entrada / S * por2000, T.acc_demora_entrada > 0 ? T.demora_entrada / T.acc_demora_entrada : 0,
         T.acc_demora_entrada / S);
  printf("  ventas: precio de menos                      %8.2f (%.2f)   %+.4f de precio por accion, %.1f acciones\n",
         T.demora_salida / S, T.demora_salida / S * por2000, T.acc_demora_salida > 0 ? T.demora_salida / T.acc_demora_salida : 0,
         T.acc_demora_salida / S);
  printf("Recompras (no dependen del limite): %.2f ordenes, comision %.2f (%.2f)\n", nrc / S, nrc * r.comision / S,
         nrc * r.comision / S * por2000);

  printf("\nCamino del precio despues de la primera orden (media +- error entre ordenes; no depende de lo que la estrategia haga despues)\n");
  printf("  primera compra menos precio de la senal (tick anterior): %+.4f +- %.4f\n", T.senal_e / T.n_senal_e,
         sqrt((T.senal_e2 / T.n_senal_e - pow(T.senal_e / T.n_senal_e, 2)) / T.n_senal_e));
  printf("  precio j ticks despues de la primera compra, menos el de la primera compra:\n   ");
  for (int j = 1; j <= CAMINO; j++) {
    double m = T.camino_e[j] / T.n_camino_e[j];
    printf(" j=%d %+.3f+-%.3f", j, m, sqrt((T.camino_e2[j] / T.n_camino_e[j] - m * m) / T.n_camino_e[j]));
  }
  printf("\n  primera venta menos precio de la senal (tick anterior): %+.4f +- %.4f\n", T.senal_s / T.n_senal_s,
         sqrt((T.senal_s2 / T.n_senal_s - pow(T.senal_s / T.n_senal_s, 2)) / T.n_senal_s));
  printf("  precio j ticks despues de la primera venta, menos el de la primera venta:\n   ");
  for (int j = 1; j <= CAMINO; j++) {
    double m = T.camino_s[j] / T.n_camino_s[j];
    printf(" j=%d %+.3f+-%.3f", j, m, sqrt((T.camino_s2[j] / T.n_camino_s[j] - m * m) / T.n_camino_s[j]));
  }
  printf("\n");

  printf("\nOrdenes que ejecutan menos de m acciones (compras y ventas, todas las clases), promedio por serie\n");
  printf("%4s | %8s %9s %10s | %s\n", "m", "ordenes", "comision", "% ordenes", "ganancia bruta de las compras de ese tamano, por orden");
  for (int k = 1; k < NTAM; k++) {
    double n = 0, nb = 0, bruta = 0;
    for (int cl = 0; cl < NCLASES; cl++)
      for (int j = 0; j < k; j++) { n += T.compra[cl][j].n + T.venta[cl][j].n; nb += T.compra[cl][j].n; bruta += T.compra[cl][j].bruta; }
    printf("%4d | %8.3f %9.2f %9.2f%% | %.2f\n", TAM_MIN[k], n / S, n * r.comision / S, 100 * n / T.ordenes, nb > 0 ? bruta / nb : 0);
  }
  lote_liberar(l);
  instancia_destruir(inst);
  return 0;
}
