/* mia.c: la estrategia más chica que se puede agregar al arnés.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Es el ejemplo del README de factibilidad/retorno, tal cual. No es una
 * candidata: con k=5 y entra=3 es la misma regla de max_media, y la prueba
 * de este directorio lo comprueba.
 *
 * Compilar y probar: make -C factibilidad/retorno/ejemplo/minimo probar
 */
#include "nucleo.h"

typedef struct { int k, entra; } Cfg;
typedef struct { const Cfg *c; int ini, S, pos; } Estado;

static int configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  Cfg *c = cfg;
  c->k = 5; c->entra = 3;
  const Campo campos[] = {{"k", &c->k}, {"entra", &c->entra}};
  return leer_campos(parametros, campos, 2, error, tam);
}

static void iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  (void)reglas; (void)semilla;
  ((Estado *)estado)->c = cfg;
}

static int decidir(void *estado, int precio, const Cuenta *propia) {
  Estado *s = estado;
  (void)propia;
  if (!s->ini) { s->ini = 1; s->S = precio << s->c->k; }
  int dev = (precio << s->c->k) - s->S;
  s->S += dev >> s->c->k;
  if (dev < -(s->c->entra << s->c->k)) s->pos = 1; else if (dev > 0) s->pos = 0;
  return s->pos ? COMPRAR_63 : VENDER_63;
}

static const Estrategia mia = {"mia", "ejemplo minimo", sizeof(Cfg), sizeof(Estado),
                               configurar, iniciar, decidir, NULL, NULL};
REGISTRAR_ESTRATEGIA(mia)
