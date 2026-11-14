/* nucleo.h: interfaz del arnés de evaluación del estudio de retorno.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * El arnés evalúa estrategias a nivel de tick: una estrategia recibe el precio
 * que acaba de llegar y devuelve el byte que dejaría en DECISION. No simula el
 * SoC (eso lo hace el gemelo digital, ref/gemelo/gemelo.c) y no es parte del
 * diseño ni del programa de la placa.
 *
 * Cómo se agrega una estrategia desde otra carpeta, sin tocar el núcleo:
 *
 *   1. Se escribe un archivo .c con una variable `Estrategia` y la línea
 *      REGISTRAR_ESTRATEGIA(variable). Ver ejemplo/mi_estrategia.c.
 *   2. Se compila junto con los fuentes del núcleo (nucleo.mk lo hace):
 *        include factibilidad/retorno/nucleo/nucleo.mk
 *        mi_binario: $(NUCLEO_FUENTES) mi_estrategia.c
 *        	$(NUCLEO_CC) -o $@ $^ $(NUCLEO_LIBS)
 *   3. El binario resultante tiene todos los comandos del arnés (listar,
 *      correr, frontera, hipotesis, veredicto, causal...) y conoce la
 *      estrategia nueva por su nombre.
 *
 * Por qué una estrategia no puede mirar el futuro: `decidir` recibe un solo
 * precio, por valor, y una copia de la cuenta. Nunca recibe la serie, ni un
 * puntero a ella, ni el número de tick, ni el largo de la ronda. El comando
 * `causal` además lo comprueba: cambia el futuro de la serie y exige que las
 * decisiones anteriores no cambien.
 */
#ifndef NUCLEO_H
#define NUCLEO_H

#include <stddef.h>
#include <stdint.h>

/* ---- Mercado: contabilidad oficial (tarea `ejecutar` de tb/tb_proyecto_4.sv) ---- */

#define CAJA0_DEF 10000
#define COMISION_DEF 5

#define MANTENER 0x00
#define COMPRAR(q) (0x40 | ((q) & 63))
#define VENDER(q) (0x80 | ((q) & 63))
#define COMPRAR_63 0x7F
#define VENDER_63 0xBF

typedef struct {
  int caja0;      /* caja con que parte la ronda */
  int comision;   /* comisión fija por orden ejecutada */
} Reglas;

typedef struct {
  int caja;       /* dinero disponible */
  int acciones;   /* acciones que se tienen */
  int w;          /* patrimonio al último precio: caja + acciones * precio */
  int peak;       /* mayor patrimonio visto */
  int max_dd;     /* mayor caída desde el máximo */
  int ordenes;    /* órdenes ejecutadas (cada una pagó comisión) */
  int ultima_q;   /* acciones de la última orden: positivo compra, negativo venta, 0 no se ejecutó */
  int desborde;   /* 1 si algún valor no cupo en 32 bits (el testbench usa int) */
} Cuenta;

void cuenta_iniciar(Cuenta *c, const Reglas *r);
/* Ejecuta `decision` al precio `p`. Devuelve las acciones transadas (con signo). */
int cuenta_ejecutar(Cuenta *c, const Reglas *r, int decision, int p);
/* Referencia del testbench: compra todo al primer precio y no vende. */
int comprar_y_mantener(const unsigned char *precios, int n, const Reglas *r);

/* ---- Estrategias ------------------------------------------------------------------ */

typedef struct Estrategia {
  const char *nombre;        /* con este nombre se pide: "param", "cruce", "mia" */
  const char *descripcion;   /* una línea, para `listar` */
  size_t tam_cfg;            /* bytes de la configuración (parámetros de la estrategia) */
  size_t tam_estado;         /* bytes del estado de una ronda */

  /* Lee los parámetros ("E=96,X=0") y llena la configuración. La memoria llega
   * en cero. Devuelve 0 si está bien; si no, deja el motivo en `error`. */
  int (*configurar)(void *cfg, const char *parametros, char *error, size_t tam_error);

  /* Deja el estado de comienzo de ronda. La memoria llega en cero. `semilla`
   * es distinta para cada serie: las estrategias con azar deben usarla y no
   * otra fuente, para que todo sea reproducible. */
  void (*iniciar)(void *estado, const void *cfg, const Reglas *reglas, uint64_t semilla);

  /* Recibe el precio que acaba de llegar y devuelve el byte de DECISION, que
   * se ejecutará al precio siguiente. `propia` es una copia de la cuenta
   * después de ejecutar, a este mismo precio, la decisión anterior: es lo que
   * el programa de la placa puede llevar por su cuenta, porque depende solo
   * de los precios ya recibidos y de sus propias decisiones. Una estrategia
   * que no lleva contabilidad la ignora. */
  int (*decidir)(void *estado, int precio, const Cuenta *propia);

  /* Opcional (puede ser NULL): hasta 4 contadores para los informes. */
  void (*contadores)(const void *estado, int aux[4]);

  /* Opcional (puede ser NULL): libera lo que `configurar` haya pedido, por
   * ejemplo las instancias de otras estrategias que esta usa por dentro. */
  void (*liberar)(void *cfg);
} Estrategia;

void nucleo_registrar(const Estrategia *e);
#define REGISTRAR_ESTRATEGIA(e) \
  static void __attribute__((constructor)) nucleo_registrar_##e(void) { nucleo_registrar(&e); }

/* Un alias da nombre a una especificación completa: "cand:max_media" es "param:E=96,X=0". */
void nucleo_alias(const char *nombre, const char *spec, const char *descripcion);
/* Un rival es una especificación con la clase a la que pertenece (cruce, momentum...). */
void nucleo_rival(const char *clase, const char *spec);

/* Lectura de parámetros "a=1,b=2" (también separados por espacios). */
typedef struct { const char *nombre; int *destino; } Campo;
int leer_campos(const char *texto, const Campo *campos, int n, char *error, size_t tam_error);

/* ---- Instancias: una estrategia con su configuración y su estado -------------------- */
/* Sirven para correr una estrategia y también para que una estrategia use a
 * otras por dentro (por ejemplo un gestor que sigue a varias en papel). */

typedef struct Instancia Instancia;
/* `spec` es "nombre", "nombre:a=1,b=2" o un alias. Devuelve NULL si hay error. */
Instancia *instancia_crear(const char *spec, char *error, size_t tam_error);
void instancia_destruir(Instancia *i);
void instancia_iniciar(Instancia *i, const Reglas *r, uint64_t semilla);
int instancia_decidir(Instancia *i, int precio, const Cuenta *propia);
void instancia_contadores(const Instancia *i, int aux[4]);
const char *instancia_spec(const Instancia *i);     /* especificación ya resuelta (sin alias) */

/* ---- Correr una serie ----------------------------------------------------------------- */

typedef struct {
  int w;          /* patrimonio final */
  int ordenes;
  int max_dd;
  int byh;        /* comprar y mantener sobre la misma serie */
  int aux[4];     /* contadores de la estrategia */
  int desborde;
} Resultado;

/* Corre la instancia sobre `n` precios. La decisión que la estrategia entrega
 * después de ver precios[t] se ejecuta al precio precios[t+1]; DECISION parte
 * en 0 (mantener). Los primeros `perdidos` precios no se le muestran (reset
 * del testbench; en la competencia es 0). Si `leidos` no es NULL recibe el
 * byte que la maestra lee en cada tick. */
Resultado correr_serie(Instancia *i, const unsigned char *precios, int n, const Reglas *r, uint64_t semilla,
                       int perdidos, unsigned char *leidos);

/* Semilla de la serie `indice` para la estrategia `spec`: no depende del orden ni de los hilos. */
uint64_t semilla_serie(const char *spec, int indice);

/* ---- Lotes de series (formato de generar_series.py) ------------------------------------ */

#define MAX_PARTES 16
typedef struct {
  int ns, n;                 /* series y ticks por serie */
  unsigned char *datos;      /* ns * n bytes */
  char nombre[96];
  int partes;                /* familias que componen el lote (1 si es un solo archivo) */
  char parte[MAX_PARTES][32];   /* nombre de la familia */
  char archivo[MAX_PARTES][64]; /* archivo de origen, sin la extensión */
  int inicio[MAX_PARTES + 1];   /* la familia k ocupa las series inicio[k] .. inicio[k+1]-1 */
  int total[MAX_PARTES];        /* series que tiene el archivo de origen (se puede haber tomado un prefijo) */
  uint64_t huella[MAX_PARTES];  /* huella del contenido del archivo de origen completo */
} Lote;

Lote *lote_leer(const char *ruta);                    /* NULL si no se puede leer */
void lote_liberar(Lote *l);
/* Conjunto con nombre: "bloques", "practica", "remuestreo", "plausibles",
 * "estres", "degeneradas", "evidencia" (remuestreo más plausibles, mitad y
 * mitad) o una familia. Junta los archivos que hagan falta en un solo lote. */
Lote *conjunto_leer(const char *conjunto, int largo, int semilla);
const char *directorio_series(void);                  /* build/series o $RETORNO_SERIES */

/* Corre `spec` sobre todo el lote, en paralelo. `res` tiene lugar para l->ns
 * resultados. La semilla de cada serie depende de su posición dentro de su
 * archivo de origen, no del conjunto en que venga. Devuelve 0 si está bien. */
int evaluar_lote(const char *spec, const Lote *l, const Reglas *r, Resultado *res);

/* ---- Estadística ------------------------------------------------------------------------- */

typedef struct { uint64_t s[4]; } Azar;
void azar_sembrar(Azar *a, uint64_t semilla);
uint64_t azar_u64(Azar *a);
double azar_u01(Azar *a);                              /* uniforme en [0, 1) */
int azar_entero(Azar *a, int n);                       /* uniforme en 0..n-1 */

typedef struct { double media, ee, p5, mediana, peor, mejor; int n; } Resumen;
Resumen resumir(const double *x, int n);
/* Percentil con la convención de ref/protocolo.py: orden[min(n-1, int(q*n))]. Ordena una copia. */
double percentil(const double *x, int n, double q);
/* Diferencia pareada a - b: media y error estándar. */
void pareada(const double *a, const double *b, int n, double *media, double *ee);

#endif
