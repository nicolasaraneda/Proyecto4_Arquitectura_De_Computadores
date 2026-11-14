/* torneo.h: hipótesis de puntaje y torneo simulado contra rivales.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Tres hipótesis sobre cómo se puntúa la competencia:
 *   H1  patrimonio final.
 *   H2  exceso sobre comprar y mantener (diferencia y razón).
 *   H3  torneo: en cada ronda compiten G grupos rivales y el puntaje va de 0
 *       (el peor) a 2 (el mejor). El enunciado admite dos lecturas:
 *         H3a  lineal en el patrimonio entre el peor y el mejor del campo;
 *         H3b  lineal en el puesto (los empates se reparten el puesto).
 *       Además se informan dos lecturas sobre la competencia completa:
 *         suma   H3a sobre el patrimonio sumado de las tres rondas;
 *         razón  H3a sobre la suma de W / comprar y mantener de las tres
 *                rondas (el puntaje "respecto a la referencia comprar y
 *                mantener" del enunciado, llevado al torneo).
 * Una competencia son tres rondas con series independientes y los mismos
 * rivales en las tres (cada grupo usa el mismo programa).
 */
#ifndef TORNEO_H
#define TORNEO_H

#include "nucleo.h"

#define N_CAMPOS 3
#define MAX_R 256
extern const char *CAMPOS[N_CAMPOS];          /* "ingenuo", "mixto", "fuerte" */

/* acceso al registro del núcleo */
int nucleo_nestrategias(void);
const Estrategia *nucleo_estrategia(int i);
int nucleo_nalias(void);
const char *nucleo_alias_nombre(int i);
const char *nucleo_alias_spec(int i);
const char *nucleo_alias_desc(int i);
int nucleo_nrivales(void);
const char *nucleo_rival_clase(int i);
const char *nucleo_rival_spec(int i);

typedef struct {
  int nr;
  const char *spec[MAX_R], *clase[MAX_R];
  double practica[MAX_R];                     /* patrimonio del rival en la serie de práctica completa */
  double peso[N_CAMPOS][MAX_R];               /* probabilidad de cada rival en cada composición del campo */
} Rivales;

/* Llena la lista de rivales y los pesos de las tres composiciones. Devuelve 0 si está bien. */
int rivales_preparar(Rivales *rv, const Reglas *r);
int campo_indice(const char *nombre);         /* -1 si no existe */

/* Puntaje de un grupo con patrimonio w frente a los patrimonios x[0..G-1] de los rivales. */
double puntos_patrimonio(double w, const double *x, int G);    /* H3a */
double puntos_puesto(double w, const double *x, int G);        /* H3b */

typedef struct {
  /* una ronda: media con su error (por serie), percentil 5 */
  double a_media, a_ee, a_p5, b_media, b_ee, b_p5;
  /* una competencia de tres rondas: promedio de los puntos de las tres */
  double ca_p5, ca_p5_ee, ca_peor, cb_p5, cb_p5_ee, cb_peor;
  /* H3a sobre el patrimonio sumado de las tres rondas */
  double cs_media, cs_ee, cs_p5, cs_p5_ee;
  /* H3a sobre la suma de W / comprar y mantener de las tres rondas */
  double cr_media, cr_ee, cr_p5, cr_p5_ee;
  /* diferencia contra la candidata de referencia */
  double da, da_ee, db, db_ee, ds, ds_ee, dr, dr_ee;
  double dca_p5, dca_p5_ee, dcb_p5, dcb_p5_ee, dcs_p5, dcs_p5_ee, dcr_p5, dcr_p5_ee;
} PuntosTorneo;

/* W[c][i]: patrimonio del candidato c en la serie i. R[k][i]: el del rival k.
 * byh[i]: comprar y mantener en la serie i. `ref` es el índice del candidato
 * de referencia para las diferencias. No usa variables globales: se puede
 * llamar desde varios hilos a la vez. */
void torneo(double **W, const double *byh, int nc, int ref, double **R, const double *peso, int nr, int ns, int G,
            uint64_t semilla, PuntosTorneo *salida);

typedef struct {
  double w3_media, w3_p5, w3_p5_ee, w3_peor;    /* promedio del patrimonio en tres rondas */
  double e3_p5, e3_p5_ee, e3_peor;              /* promedio del exceso sobre comprar y mantener */
  double dw3_p5, dw3_p5_ee;                     /* diferencia del percentil 5 contra la referencia */
} TresRondas;

/* Patrimonio y exceso agregados en competencias de tres rondas. */
void tres_rondas(double **W, const double *byh, int nc, int ref, int ns, uint64_t semilla, TresRondas *salida);

/* Resultados de `spec` sobre un conjunto, con caché en build/resultados para
 * las estrategias del núcleo. Devuelve un arreglo de l->ns resultados (lo
 * libera quien llama) o NULL. */
Resultado *resultados(const char *spec, const Lote *l, const char *conjunto, int largo, int semilla, const Reglas *r);

#endif
