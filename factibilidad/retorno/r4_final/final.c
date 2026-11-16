/* final.c: piezas propias del estudio de cierre y nombres de las configuraciones que compara.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Estudio de retorno 4, cierre. No es parte del diseño: son estrategias para
 * el arnés de retorno (../README.md).
 *
 * 1. Estrategia `filtro`: cualquier estrategia que no lleva contabilidad, con
 *    la ejecución recomendada por el estudio 3 puesta a la salida. Si la
 *    estrategia de adentro pide comprar y la caja alcanza para menos de m
 *    acciones al precio actual (caja - comisión < m p), se manda "mantener".
 *    La caja es la de la cuenta propia que entrega el arnés, que es la que
 *    llevaría el espejo del programa. Con x=cand:max_media y m=8 decide byte a
 *    byte igual que `ejec:m=8` (objetivo `prueba`).
 *    Parámetros: x (estrategia de adentro; con parámetros se escribe '/' en
 *    vez de ',' y '~' en vez de '=') y m (por defecto 8).
 *    No sirve para el fondo, que lleva su propio espejo: para eso está el
 *    parámetro em de `fondoc` (fondoc.c).
 *
 * 2. Alias. Todos se fijaron antes de correr nada, a partir de lo que
 *    recomienda cada estudio, y no se ajustaron después:
 *
 *    ejec_a          ejec:m=8                         la ejecución recomendada (estudio 3, candidata A)
 *    ejec_b          ejec:m=8,m2=24,e2=32             la candidata B del estudio 3
 *    espera_e        espera con la ejecución A
 *    rec_e           fondo_rec con la ejecución A en el supervisor
 *    min_e           fondo_min con la ejecución A en el supervisor
 *    completo        EL FONDO COMPLETO: los gestores y el reparto de fondo_rec (max_media, kalman y
 *                    activo, pesos fijos, banda de 4/16), la tabla que aprende (aprendiz) como cuarto
 *                    gestor con pesos 6/3/3/4 y la ejecución A en el supervisor
 *    completo_s      el mismo sin la ejecución A (para separar cuánto aporta cada pieza)
 *    completo_esp    el mismo con `espera` en vez de `aprendiz` como cuarto gestor
 *    completo_ap     el mismo, pero los pesos se aprenden alrededor de 6/3/3/4 según el desempeño en
 *                    papel (ventana de 512 ticks, margen 1/64, a lo más 4/16 de distancia del prior)
 *    completo_ancla  con ancla en comprar y mantener: max_media, prudente, comprar y mantener y
 *                    aprendiz, pesos 10/2/2/2, banda de 2/16 y la ejecución A
 *    completo_min    el fondo mínimo (voto, sin productos) con aprendiz como cuarto gestor, pesos
 *                    aprendidos alrededor de 4/4/4/4 y la ejecución A
 */
#include <stdio.h>
#include <string.h>

#include "nucleo.h"

typedef struct { Instancia *sub; int m; char x[256]; } Cfg;
typedef struct { const Cfg *c; Reglas r; int n_sup; } Estado;

static int configurar(void *cfg, const char *parametros, char *error, size_t tam) {
  Cfg *c = cfg;
  char copia[512], resto[512] = "", *guarda = NULL;
  c->m = 8;
  snprintf(c->x, sizeof c->x, "cand:max_media");
  if (parametros && strlen(parametros) >= sizeof copia) { snprintf(error, tam, "filtro: parametros demasiado largos"); return 1; }
  strcpy(copia, parametros ? parametros : "");
  for (char *tok = strtok_r(copia, ", \t\r\n", &guarda); tok; tok = strtok_r(NULL, ", \t\r\n", &guarda)) {
    if (!strncmp(tok, "x=", 2)) {
      snprintf(c->x, sizeof c->x, "%s", tok + 2);
      for (char *q = c->x; *q; q++) { if (*q == '/') *q = ','; else if (*q == '~') *q = '='; }
    } else {
      if (resto[0]) strcat(resto, ",");
      strcat(resto, tok);
    }
  }
  const Campo campos[] = {{"m", &c->m}};
  if (leer_campos(resto, campos, 1, error, tam)) return 1;
  if (c->m < 0 || c->m > 63) { snprintf(error, tam, "filtro: m debe estar entre 0 y 63"); return 1; }
  return (c->sub = instancia_crear(c->x, error, tam)) ? 0 : 1;
}

static void liberar(void *cfg) { instancia_destruir(((Cfg *)cfg)->sub); }

static void iniciar(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla) {
  Estado *s = estado;
  s->c = cfg;
  s->r = *reglas;
  instancia_iniciar(s->c->sub, reglas, semilla + 1);
}

static int decidir(void *estado, int p, const Cuenta *propia) {
  Estado *s = estado;
  int d = instancia_decidir(s->c->sub, p, propia);
  if (s->c->m && ((d >> 6) & 3) == 1 && propia->caja - s->r.comision < s->c->m * p) {
    if (propia->caja - s->r.comision >= p) s->n_sup++;
    d = MANTENER;
  }
  return d;
}

static void contadores(const void *estado, int aux[4]) {
  aux[0] = aux[1] = aux[2] = 0;
  aux[3] = ((const Estado *)estado)->n_sup;
}

static const Estrategia filtro = {
  "filtro", "cualquier estrategia sin contabilidad con la ejecucion del estudio 3: no manda compras de menos de m acciones. x, m",
  sizeof(Cfg), sizeof(Estado), configurar, iniciar, decidir, contadores, liberar};
REGISTRAR_ESTRATEGIA(filtro)

static void __attribute__((constructor)) alias_final(void) {
  nucleo_alias("cand:ejec_a", "ejec:m=8", "r3: max_media sin las compras de menos de 8 acciones (candidata A)");
  nucleo_alias("cand:ejec_b", "ejec:m=8,m2=24,e2=32", "r3: ademas, el resto de menos de 24 acciones solo un punto mas abajo (candidata B)");
  nucleo_alias("cand:espera_e", "filtro:x=cand:espera,m=8", "cierre: espera con la ejecucion A");
  nucleo_alias("cand:rec_e", "fondoc:c=3,w0=8,w1=4,w2=4,b=4,em=8", "cierre: fondo_rec con la ejecucion A en el supervisor");
  nucleo_alias("cand:min_e", "fondoc:c=5,w0=6,w1=5,w2=5,m=2,v=9,mg=5,d=4,pp=1,vt=8,em=8", "cierre: fondo_min con la ejecucion A en el supervisor");
  nucleo_alias("cand:completo", "fondoc:c=3,x=cand:aprendiz,w0=6,w1=3,w2=3,w3=4,b=4,em=8",
               "cierre: el fondo completo (fondo_rec, aprendiz como cuarto gestor y ejecucion A)");
  nucleo_alias("cand:completo_s", "fondoc:c=3,x=cand:aprendiz,w0=6,w1=3,w2=3,w3=4,b=4", "cierre: el fondo completo sin la ejecucion A");
  nucleo_alias("cand:completo_esp", "fondoc:c=3,x=cand:espera,w0=6,w1=3,w2=3,w3=4,b=4,em=8",
               "cierre: el fondo completo con espera como cuarto gestor");
  nucleo_alias("cand:completo_ap", "fondoc:c=3,x=cand:aprendiz,w0=6,w1=3,w2=3,w3=4,b=4,m=2,v=9,mg=6,d=4,em=8",
               "cierre: el fondo completo con los pesos aprendidos alrededor de 6/3/3/4");
  nucleo_alias("cand:completo_ancla", "fondoc:c=1,x=cand:aprendiz,w0=10,w1=2,w2=2,w3=2,b=2,em=8",
               "cierre: fondo con ancla en comprar y mantener, aprendiz como cuarto gestor y ejecucion A");
  nucleo_alias("cand:completo_min", "fondoc:c=5,x=cand:aprendiz,w0=4,w1=4,w2=4,w3=4,m=2,v=9,mg=5,d=4,pp=1,vt=8,em=8",
               "cierre: fondo minimo (voto) con aprendiz como cuarto gestor y ejecucion A");
}
