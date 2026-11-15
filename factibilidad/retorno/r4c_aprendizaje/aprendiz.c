/* aprendiz.c: nombre estable de la mejor estrategia experimental del estudio de aprendizaje en vivo.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Alias que quedan registrados, con los parámetros fijados (se eligieron solo
 * con la semilla 0; ver README.md):
 *
 *   aprendiz         la tabla de política que aprende, con prior fuerte. En
 *                    rondas de 2000 ticks decide igual que max_media y en
 *                    rondas largas se aparta de ella.
 *   aprendiz_rapido  la misma tabla con una tasa cuatro veces mayor: ya se
 *                    aparta de max_media dentro de una ronda de 2000 ticks.
 *   espera           regla fija, sin aprendizaje: max_media, pero no compra en
 *                    el mismo tick en que el precio baja (salvo que la caída
 *                    sea de 5 o más) y mantiene la compra pendiente si el
 *                    precio rebota una unidad. Es lo que la tabla con el signo
 *                    del último cambio debería descubrir.
 *   aprendiz_patron  max_media con el predictor de patrones (gshare de 12
 *                    bits) como filtro de entradas.
 *   aprendiz_puro    el predictor de patrones operando solo. Pierde mucho:
 *                    está para que quede medido.
 *
 * Uso desde otra estrategia (por ejemplo como gestor en papel de un fondo):
 *     Instancia *g = instancia_crear("cand:aprendiz", error, sizeof error);
 */
#include "nucleo.h"

static void __attribute__((constructor)) alias_aprendiz(void) {
  nucleo_alias("cand:aprendiz", "tabla:ka=12,h=16",
               "r4c: tabla de politica que parte de max_media y aprende con prior fuerte (experimental)");
  nucleo_alias("cand:aprendiz_rapido", "tabla:ka=10,h=16",
               "r4c: la misma tabla con una tasa de aprendizaje cuatro veces mayor (experimental)");
  nucleo_alias("cand:espera", "tabla:ter=1,ezb=64,ezs=-32",
               "r4c: max_media que no compra en el tick en que el precio baja; regla fija, sin aprendizaje");
  nucleo_alias("cand:aprendiz_patron", "mm_patron:tipo=1,H=12,sim=2,bits=2,h=1,fe=2,fs=0,maxp=4",
               "r4c: max_media con el predictor de patrones como filtro de entradas (experimental)");
  nucleo_alias("cand:aprendiz_puro", "patron:tipo=1,H=12,sim=2,bits=3,h=1",
               "r4c: el predictor de patrones operando solo (experimental, pierde)");
}
