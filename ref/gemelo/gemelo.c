/* gemelo.c: gemelo digital del Pochoco SoC, con exactitud de ciclo.
 *
 * Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
 * Arquitectura de Computadores, Universidad de los Andes, 2026-2.
 *
 * Simula lo mismo que el testbench oficial (la maestra SPI, la contabilidad
 * y el SoC con el programa de un .hex), pero sin simular compuertas: por eso
 * corre millones de ticks en segundos. No es la referencia del algoritmo (esa
 * es ref/trader.py): es un modelo del hardware, y ejecuta el mismo trade.hex
 * que va dentro del bitstream.
 *
 * Qué modela, y con qué exactitud:
 *   - Espino base: cada instrucción con su costo en ciclos y con el ciclo
 *     exacto en que accede al bus y en que escribe el banco de registros.
 *       cualquier instrucción ............ 2 ciclos
 *       load ............................. 3 ciclos (acceso al bus en el 2.o)
 *       salto tomado, jal, jalr .......... 3 ciclos (una burbuja)
 *     Decodifica igual que espino_decoder.v, incluidos los casos raros: los
 *     shifts se ejecutan como suma (la ALU los tiene deshabilitados) y una
 *     instrucción desconocida no hace nada.
 *   - pochoco_spi_slave: se ejecuta ciclo a ciclo con la misma lógica del
 *     Verilog (sincronizadores de 3 etapas, contador de bits, registros).
 *     Cuando las líneas están quietas se salta de un evento al siguiente.
 *   - Reset de encendido de pochoco_soc (2^PorBits - 1 ciclos).
 *   - Maestra: el timing en nanosegundos de tb_proyecto_4.sv, parametrizable.
 *   - Contabilidad: la tarea `ejecutar` del testbench, con enteros de 32 bits.
 *
 * Numeración: el ciclo k es el intervalo que termina en el flanco de subida
 * número k del reloj (el flanco 0 ocurre a los 20 ns, y hay uno cada 40 ns).
 * "Durante el ciclo k" es lo que se muestrea en ese flanco. Es la misma
 * convención de tb/tb_cpi.sv, y las trazas de los dos se comparan con cmp.
 *
 * Atajo del sondeo: el programa pasa casi todo el tiempo en el lazo
 *     lw rA, STATUS(rB) ; andi rA, rA, 1 ; beqz rA, lazo
 * Cuando el gemelo reconoce ese lazo y no hay precio nuevo, calcula en qué
 * vuelta va a llegar y se salta las anteriores (8 ciclos y 3 instrucciones
 * por vuelta). El resultado es idéntico al de simular cada vuelta: se
 * comprueba corriendo con y sin --sin-atajo (make cosim).
 *
 * Compilar:  cc -O2 -o build/gemelo ref/gemelo/gemelo.c   (o make gemelo)
 * Uso:       build/gemelo --ayuda
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define T_CLK    40          /* periodo del reloj en ns (25 MHz) */
#define T_POS0   20          /* instante del primer flanco de subida */
#define NWORDS   512         /* palabras de la RAM */
#define MAXQ     64          /* eventos de una transaccion */
#define SIN_EVENTO INT64_MAX

/* ---- Configuracion -------------------------------------------------------- */
static struct {
  const char *hex, *serie, *lote, *csv, *ticks_csv, *traza;
  int      nticks;
  int      por_bits;
  int64_t  inicio_ns, periodo_ns, cs_setup_ns, sclk_medio_ns, cs_hold_ns;
  int      borde;            /* 1: un cambio de pin que coincide con el flanco ya se ve en ese flanco */
  int      caja0, comision;
  int      atajo;
  int      resumen;
} cfg = {
  "sw/trade.hex", "tb/practica.csv", NULL, NULL, NULL, NULL,
  0, 12, 4000, 100000, 1000, 500, 500, 1, 10000, 5, 1, 1
};

enum { EV_CS, EV_SCLK, EV_MOSI, EV_MUESTRA };
typedef struct { int64_t ciclo; int tipo, valor; } Evento;

typedef struct {
  /* memoria y core */
  uint32_t mem[NWORDS];
  uint32_t x[16];
  uint32_t pc, w;            /* w: instruccion ya leida de la memoria para pc */
  int64_t  c;                /* ciclo en que parte la instruccion actual */
  int64_t  ic, n_load, n_store, n_br_t, n_br_nt, n_jump, n_otras, vueltas_saltadas;
  int64_t  load_pend;        /* ciclo en que se completa el load en curso, o -1 */
  /* perifericos */
  uint8_t  digit, led;
  /* esclavo SPI: estado durante el ciclo spi_c */
  int64_t  spi_c;
  uint8_t  sclk_sync, mosi_sync, cs_sync, rx_shift, tx_shift, bit_cnt, tx_hold, price_q, new_price;
  int      pin_sclk, pin_mosi, pin_cs;
  /* maestra */
  const int *precio;
  int      nticks;
  Evento   q[MAXQ];
  int      qh, nq, tx_gen;   /* tx_gen: transacciones ya generadas */
  uint8_t  rx_maestra;
  uint8_t *leido;
  /* contabilidad oficial */
  int      caja, acciones, w_pat, peak, max_dd, ordenes;
  /* medicion oficial (precio -> DECISION) */
  int64_t  t0;
  int      esperando, respuestas, precios_perdidos, peor_caso;
  /* medicion por tick (igual que tb_cpi.sv) */
  int64_t  ic0;
  int      esp_dec, esp_fin, tick_m, precio_m, r_ciclos, r_ic, ticks_medidos;
  int      peor_r_ciclos, peor_r_ic, peor_t_ciclos, peor_t_ic;
  int64_t  suma_r_ciclos, suma_r_ic, suma_t_ciclos, suma_t_ic;
  /* atajo del sondeo */
  int      ff;
  int64_t  ff_c, ff_ic;
  /* limites */
  int64_t  R, c_fin;
  FILE    *f_csv, *f_ticks, *f_traza;
} Sim;

static void morir(const char *msg, const char *arg) {
  fprintf(stderr, "gemelo: %s%s%s\n", msg, arg ? ": " : "", arg ? arg : "");
  exit(2);
}

/* ---- Tiempo -> ciclo -------------------------------------------------------- */
/* Ciclo cuyo estado ve la maestra en el instante t: el que termina en el
 * primer flanco que ocurre en t o despues. */
static int64_t ciclo_de(int64_t t) {
  return t <= T_POS0 ? 0 : (t - T_POS0 + T_CLK - 1) / T_CLK;
}
/* Primer flanco que muestrea un cambio de pin ocurrido en t. El testbench
 * oficial sube SCLK justo en un flanco del reloj (5500 ns = 20 + 40 * 137).
 * Icarus y Verilator resuelven esa coincidencia igual: el flanco ya ve el
 * valor nuevo. Eso es borde = 1, el valor por defecto. En la placa la maestra
 * es asincrona y puede darse cualquiera de los dos casos; con --borde 0 se
 * prueba el otro (la respuesta se mueve un ciclo, las decisiones no cambian). */
static int64_t flanco_que_ve(int64_t t) {
  if (cfg.borde) return ciclo_de(t);
  return t < T_POS0 ? 0 : (t - T_POS0) / T_CLK + 1;
}

/* ---- Contabilidad: tarea ejecutar de tb_proyecto_4.sv ----------------------- */
static void ejecutar(Sim *s, uint8_t decision, int p) {
  int q = decision & 63;
  switch (decision >> 6) {
    case 1:
      if (q > (s->caja - cfg.comision) / p) q = (s->caja - cfg.comision) / p;
      if (q > 0) { s->caja -= q * p + cfg.comision; s->acciones += q; s->ordenes++; }
      break;
    case 2:
      if (q > s->acciones) q = s->acciones;
      if (q > 0 && s->caja + q * p >= cfg.comision) { s->caja += q * p - cfg.comision; s->acciones -= q; s->ordenes++; }
      break;
    default: break;
  }
  s->w_pat = s->caja + s->acciones * p;
  if (s->w_pat > s->peak) s->peak = s->w_pat;
  if (s->peak - s->w_pat > s->max_dd) s->max_dd = s->peak - s->w_pat;
}

/* ---- Maestra: eventos de una transaccion ----------------------------------- */
static void encolar(Sim *s, int tipo, int valor, int64_t t) {
  Evento e = { tipo == EV_MUESTRA ? ciclo_de(t) : flanco_que_ve(t), tipo, valor };
  int i = s->nq++;
  while (i > 0 && s->q[i - 1].ciclo > e.ciclo) { s->q[i] = s->q[i - 1]; i--; }   /* orden estable por ciclo */
  s->q[i] = e;
}

static void generar_tx(Sim *s) {
  int n = s->tx_gen++;
  int64_t t = cfg.inicio_ns + (int64_t)n * cfg.periodo_ns;
  int p = s->precio[n];
  s->qh = s->nq = 0;
  encolar(s, EV_CS, 0, t);
  t += cfg.cs_setup_ns;
  for (int b = 7; b >= 0; b--) {
    encolar(s, EV_MOSI, (p >> b) & 1, t);
    t += cfg.sclk_medio_ns;
    encolar(s, EV_MUESTRA, b, t);          /* la maestra lee MISO al subir SCLK */
    encolar(s, EV_SCLK, 1, t);
    t += cfg.sclk_medio_ns;
    encolar(s, EV_SCLK, 0, t);
  }
  encolar(s, EV_CS, 1, t + cfg.cs_hold_ns);
}

static int64_t proximo_evento(Sim *s) {
  if (s->qh == s->nq) {
    if (s->tx_gen >= s->nticks) return SIN_EVENTO;
    generar_tx(s);
  }
  return s->q[s->qh].ciclo;
}

/* ---- Instrucciones completadas hasta el ciclo y (inclusive) ----------------- */
static int64_t ic_hasta(Sim *s, int64_t y) {
  /* un load accede al bus un ciclo antes de completarse: si el esclavo avanza
   * durante ese acceso, la instruccion todavia no esta contada en ic */
  if (!s->ff) return s->ic + (s->load_pend >= 0 && s->load_pend <= y);
  /* dentro del atajo: vueltas del sondeo que parten en ff_c, 8 ciclos cada una,
   * con instrucciones completadas en los ciclos +2, +4 y +6 */
  int64_t d = y - s->ff_c, r = d % 8;
  return s->ff_ic + 3 * (d / 8) + (r >= 2) + (r >= 4) + (r >= 6);
}

/* ---- Esclavo SPI: un flanco de reloj ---------------------------------------- */
/* Pasa del estado "durante spi_c" al estado "durante spi_c + 1". El acceso del
 * core (lectura de PRICE o escritura de DECISION) es el del ciclo spi_c. */
static void spi_paso(Sim *s, int price_read, int wr_dec, uint8_t wdata) {
  /* eventos de la maestra que corresponden a este ciclo */
  while (proximo_evento(s) <= s->spi_c) {
    Evento *e = &s->q[s->qh++];
    switch (e->tipo) {
      case EV_CS:   s->pin_cs = e->valor;   break;
      case EV_SCLK: s->pin_sclk = e->valor; break;
      case EV_MOSI: s->pin_mosi = e->valor; break;
      default: {                            /* la maestra muestrea MISO */
        int cs_active = !((s->cs_sync >> 1) & 1);
        int miso = cs_active ? (s->tx_shift >> 7) & 1 : 0;
        if (e->valor == 7) s->rx_maestra = 0;
        s->rx_maestra |= (uint8_t)(miso << e->valor);
        if (e->valor == 0) {                /* byte completo: se ejecuta la orden */
          int n = s->tx_gen - 1;
          s->leido[n] = s->rx_maestra;
          ejecutar(s, s->rx_maestra, s->precio[n]);
          if (s->f_csv)
            fprintf(s->f_csv, "%d,%d,%02x,%d,%d,%d\n", n, s->precio[n], s->rx_maestra, s->caja, s->acciones, s->w_pat);
        }
      }
    }
  }

  if (s->spi_c >= s->R) {                   /* fuera de reset */
    int s1 = (s->sclk_sync >> 1) & 1, s2 = (s->sclk_sync >> 2) & 1;
    int sclk_r = s1 && !s2, sclk_f = !s1 && s2;
    int mosi = (s->mosi_sync >> 1) & 1;
    int cs_active = !((s->cs_sync >> 1) & 1);
    int cs_assert = cs_active & ((s->cs_sync >> 2) & 1);
    int byte_done = sclk_r && s->bit_cnt == 7;
    uint8_t rx_n = s->rx_shift, tx_n = s->tx_shift, bc_n = s->bit_cnt;

    if (cs_assert) {
      tx_n = s->tx_hold; bc_n = 0;
    } else if (cs_active) {
      if (sclk_r) { rx_n = (uint8_t)((s->rx_shift << 1) | mosi); bc_n = (s->bit_cnt + 1) & 15; }
      if (sclk_f) tx_n = (uint8_t)(s->tx_shift << 1);
    }
    if (byte_done) { s->price_q = (uint8_t)((s->rx_shift << 1) | mosi); s->new_price = 1; }
    else if (price_read) s->new_price = 0;
    if (wr_dec) s->tx_hold = wdata;
    s->rx_shift = rx_n; s->tx_shift = tx_n; s->bit_cnt = bc_n;
    s->sclk_sync = ((s->sclk_sync << 1) | s->pin_sclk) & 7;
    s->mosi_sync = ((s->mosi_sync << 1) | s->pin_mosi) & 7;
    s->cs_sync   = ((s->cs_sync   << 1) | s->pin_cs)   & 7;
  }
  s->spi_c++;

  /* lo que el testbench ve durante el ciclo nuevo */
  if (s->spi_c > s->c_fin) return;
  int cs_active = !((s->cs_sync >> 1) & 1);
  if (cs_active & ((s->cs_sync >> 2) & 1)) {
    if (s->f_traza) fprintf(s->f_traza, "%lld C %02x\n", (long long)s->spi_c, s->tx_hold);
  }
  if (((s->sclk_sync >> 1) & 1) && !((s->sclk_sync >> 2) & 1) && s->bit_cnt == 7) {   /* byte_done */
    int precio = ((s->rx_shift << 1) | ((s->mosi_sync >> 1) & 1)) & 0xff;
    if (s->f_traza) fprintf(s->f_traza, "%lld B %02x\n", (long long)s->spi_c, precio);
    if (s->new_price) s->precios_perdidos++;         /* el precio anterior no se leyo */
    s->t0 = s->spi_c; s->esperando = 1;
    s->ic0 = ic_hasta(s, s->spi_c); s->esp_dec = 1; s->esp_fin = 0;
    s->tick_m = (int)((T_POS0 + T_CLK * s->spi_c - cfg.inicio_ns) / cfg.periodo_ns);
    s->precio_m = precio;
  }
}

static int spi_quieto(const Sim *s) {
  return s->sclk_sync == (s->pin_sclk ? 7 : 0) && s->mosi_sync == (s->pin_mosi ? 7 : 0) &&
         s->cs_sync == (s->pin_cs ? 7 : 0);
}

/* Lleva el esclavo hasta el estado "durante el ciclo x" */
static void spi_avanzar(Sim *s, int64_t x) {
  while (s->spi_c < x) {
    if (s->spi_c < s->R || spi_quieto(s)) {
      int64_t destino = proximo_evento(s);
      if (destino > x) destino = x;
      if (s->spi_c < s->R && destino > s->R) destino = s->R;
      if (destino > s->spi_c) { s->spi_c = destino; continue; }
    }
    spi_paso(s, 0, 0, 0);
  }
}

/* ---- Mediciones por tick ---------------------------------------------------- */
static void lectura_status(Sim *s, int64_t x) {      /* el programa volvio a sondear */
  if (!s->esp_fin || x == s->t0) return;
  int t_ciclos = (int)(x - s->t0), t_ic = (int)(s->ic - s->ic0);
  s->ticks_medidos++;
  s->suma_r_ciclos += s->r_ciclos; s->suma_r_ic += s->r_ic;
  s->suma_t_ciclos += t_ciclos;    s->suma_t_ic += t_ic;
  if (s->r_ciclos > s->peor_r_ciclos) s->peor_r_ciclos = s->r_ciclos;
  if (s->r_ic > s->peor_r_ic)         s->peor_r_ic = s->r_ic;
  if (t_ciclos > s->peor_t_ciclos)    s->peor_t_ciclos = t_ciclos;
  if (t_ic > s->peor_t_ic)            s->peor_t_ic = t_ic;
  if (s->f_ticks)
    fprintf(s->f_ticks, "%d,%d,%02x,%lld,%d,%d,%d,%d\n", s->tick_m, s->precio_m, s->leido[s->tick_m],
            (long long)s->t0, s->r_ciclos, s->r_ic, t_ciclos, t_ic);
  s->esp_fin = 0;
}

static void escritura_decision(Sim *s, int64_t x) {
  if (x == s->t0) return;                  /* mismo ciclo que byte_done: el testbench no la cuenta */
  if (s->esperando) {
    int ciclos = (int)(x - s->t0);
    if (ciclos > s->peor_caso) s->peor_caso = ciclos;
    s->respuestas++;
    s->esperando = 0;
  }
  if (s->esp_dec) {
    s->r_ciclos = (int)(x - s->t0); s->r_ic = (int)(s->ic - s->ic0);
    s->esp_dec = 0; s->esp_fin = 1;
  }
}

/* ---- Bus de datos ----------------------------------------------------------- */
static uint32_t bus_leer(Sim *s, int64_t x, uint32_t addr) {
  uint32_t dato;
  if (s->f_traza || (addr & 0x80000000u)) spi_avanzar(s, x);
  if (s->f_traza) fprintf(s->f_traza, "%lld L %08x\n", (long long)x, addr & ~3u);
  if (!(addr & 0x80000000u)) return s->mem[(addr >> 2) & (NWORDS - 1)];
  int off = (addr >> 2) & 63;
  if (!(addr & 0x10000u)) return 0;        /* perifericos: los botones valen 0 en el testbench */
  int price_read = 0;
  switch (off) {
    case 0:  dato = (uint32_t)((!((s->cs_sync >> 1) & 1)) << 1) | s->new_price; lectura_status(s, x); break;
    case 1:  dato = s->price_q; price_read = 1; break;
    default: dato = 0; break;
  }
  spi_paso(s, price_read, 0, 0);
  return dato;
}

static void bus_escribir(Sim *s, int64_t x, uint32_t addr, int be, uint32_t wdata) {
  if (s->f_traza || (addr & 0x80000000u)) spi_avanzar(s, x);
  if (s->f_traza) fprintf(s->f_traza, "%lld W %08x %x %08x\n", (long long)x, addr & ~3u, be, wdata);
  if (!(addr & 0x80000000u)) {
    uint32_t mask = (be & 1 ? 0xffu : 0) | (be & 2 ? 0xff00u : 0) | (be & 4 ? 0xff0000u : 0) | (be & 8 ? 0xff000000u : 0);
    uint32_t *m = &s->mem[(addr >> 2) & (NWORDS - 1)];
    *m = (*m & ~mask) | (wdata & mask);
    return;
  }
  int off = (addr >> 2) & 63;
  if (!(addr & 0x10000u)) {                /* display y LEDs */
    if (off == 0) s->digit = (uint8_t)wdata;
    if (off == 1) s->led = wdata & 15;
    return;
  }
  if (off == 2) escritura_decision(s, x);
  spi_paso(s, 0, off == 2, (uint8_t)wdata);
}

/* ---- Core --------------------------------------------------------------------- */
/* Instruccion completada en el ciclo x. rd = 0: no escribe el banco. */
static void completar(Sim *s, int64_t x, int rd, uint32_t valor) {
  if (x > s->c_fin) return;
  if (s->spi_c < x - 1) spi_avanzar(s, x - 1);   /* un byte_done anterior debe ver el IC de antes */
  s->ic++;
  if (rd) {
    s->x[rd] = valor;
    if (s->f_traza) { spi_avanzar(s, x); fprintf(s->f_traza, "%lld R %d %08x\n", (long long)x, rd, valor); }
  }
}

static uint32_t alu(int op, uint32_t a, uint32_t b) {
  switch (op) {
    case 1: return a - b;
    case 2: return a ^ b;
    case 3: return a | b;
    case 4: return a & b;
    case 8: return (int32_t)a < (int32_t)b;
    case 9: return a < b;
    default: return a + b;                 /* ADD, y tambien SLL, SRL y SRA: shifts deshabilitados */
  }
}

/* operador de la ALU segun funct3 (y funct7[5] en OP), como espino_decoder.v */
static int alu_op(int f3, int f7b5, int es_op) {
  switch (f3) {
    case 0: return (es_op && f7b5) ? 1 : 0;
    case 1: return 5;
    case 2: return 8;
    case 3: return 9;
    case 4: return 2;
    case 5: return f7b5 ? 7 : 6;
    case 6: return 3;
    default: return 4;
  }
}

/* Si pc esta en el lazo de sondeo y no hay precio nuevo, salta las vueltas que no cambian nada */
static void atajo_sondeo(Sim *s) {
  uint32_t w = s->w;
  if ((w & 0x707f) != 0x2003) return;                      /* lw */
  int ra = (w >> 7) & 15, rb = (w >> 15) & 15;
  uint32_t addr = s->x[rb] + (uint32_t)((int32_t)w >> 20);
  if (ra == 0 || ra == rb || (addr & 0x800100fcu) != 0x80010000u) return;   /* STATUS del esclavo SPI */
  uint32_t w2 = s->mem[((s->pc + 4) >> 2) & (NWORDS - 1)], w3 = s->mem[((s->pc + 8) >> 2) & (NWORDS - 1)];
  if (w2 != (0x00107013u | (uint32_t)(ra << 7) | (uint32_t)(ra << 15))) return;   /* andi ra, ra, 1 */
  if (w3 != (0xfe000ce3u | (uint32_t)(ra << 15))) return;                         /* beq ra, x0, -8 */

  int64_t c = s->c;
  spi_avanzar(s, c + 1);                   /* la primera lectura de STATUS se hace de verdad */
  lectura_status(s, c + 1);
  if (s->new_price) return;

  s->ff = 1; s->ff_c = c; s->ff_ic = s->ic;
  int fin = 0;                             /* 1: no llegan mas precios antes del final */
  while (!s->new_price) {
    if (s->spi_c > s->c_fin) { fin = 1; break; }
    if (s->spi_c < s->R || spi_quieto(s)) {
      int64_t destino = proximo_evento(s);
      if (destino == SIN_EVENTO) { fin = 1; break; }
      if (s->spi_c < s->R && destino > s->R) destino = s->R;
      if (destino > s->spi_c) { s->spi_c = destino; continue; }
    }
    spi_paso(s, 0, 0, 0);
  }
  s->ff = 0;
  /* primera vuelta cuya lectura (en c + 1 + 8 i) ve el precio nuevo. Si no hay
   * mas precios se salta hasta cerca del final y las ultimas vueltas se simulan. */
  int64_t i = fin ? (s->c_fin - c) / 8 - 1 : (s->spi_c - (c + 1) + 7) / 8;
  if (i <= 0) return;
  s->c += 8 * i; s->ic += 3 * i;
  s->n_load += i; s->n_otras += i; s->n_br_t += i; s->vueltas_saltadas += i;
  s->x[ra] = 0;
}

static void correr_core(Sim *s) {
  while (s->c < s->c_fin) {
    if (cfg.atajo && !s->f_traza) { atajo_sondeo(s); if (s->c >= s->c_fin) break; }
    uint32_t w = s->w, pc = s->pc;
    int64_t  c = s->c;
    int opcode = w & 0x7f, rd = (w >> 7) & 15, f3 = (w >> 12) & 7, rs1 = (w >> 15) & 15, rs2 = (w >> 20) & 15;
    int f7b5 = (w >> 30) & 1;
    uint32_t a = s->x[rs1], b = s->x[rs2];
    uint32_t imm_i = (uint32_t)((int32_t)w >> 20);
    uint32_t npc = pc + 4;
    int ciclos = 2;
    int ya_leida = 0;

    switch (opcode) {
      case 0x37: completar(s, c + 1, rd, w & 0xfffff000u); s->n_otras++; break;             /* lui */
      case 0x17: completar(s, c + 1, rd, pc + (w & 0xfffff000u)); s->n_otras++; break;      /* auipc */
      case 0x13: completar(s, c + 1, rd, alu(alu_op(f3, f7b5, 0), a, imm_i)); s->n_otras++; break;
      case 0x33: completar(s, c + 1, rd, alu(alu_op(f3, f7b5, 1), a, b)); s->n_otras++; break;
      case 0x03: {                                                                           /* loads */
        uint32_t addr = a + imm_i, dato = 0, r;
        s->load_pend = c + 2;
        if (c + 1 <= s->c_fin) dato = bus_leer(s, c + 1, addr);
        s->load_pend = -1;
        uint32_t half = (addr & 2) ? dato >> 16 : dato & 0xffff;
        uint32_t byte = (addr & 1) ? (half >> 8) & 0xff : half & 0xff;
        switch (f3) {
          case 0:  r = (uint32_t)(int32_t)(int8_t)byte; break;      /* lb */
          case 1:  r = (uint32_t)(int32_t)(int16_t)half; break;     /* lh */
          case 4:  r = byte; break;                                 /* lbu */
          case 5:  r = half; break;                                 /* lhu */
          default: r = dato; break;                                 /* lw (y funct3 invalido) */
        }
        completar(s, c + 2, rd, r);
        s->n_load++; ciclos = 3;
        break;
      }
      case 0x23: {                                                                           /* stores */
        uint32_t addr = a + (((uint32_t)((int32_t)w >> 25) << 5) | ((w >> 7) & 31));
        uint32_t wdata; int be;
        switch (f3) {
          case 0:  wdata = (b & 0xff) * 0x01010101u; be = 1 << (addr & 3); break;
          case 1:  wdata = (b & 0xffff) * 0x00010001u; be = (addr & 2) ? 12 : 3; break;
          default: wdata = b; be = 15; break;
        }
        s->w = s->mem[(npc >> 2) & (NWORDS - 1)];    /* la siguiente instruccion se lee antes de escribir */
        ya_leida = 1;
        completar(s, c + 1, 0, 0);
        if (c + 1 <= s->c_fin) bus_escribir(s, c + 1, addr, be, wdata);
        s->n_store++;
        break;
      }
      case 0x63: {                                                                           /* branches */
        int tomado;
        switch (f3) {
          case 0:  tomado = a == b; break;
          case 1:  tomado = a != b; break;
          case 4:  tomado = (int32_t)a < (int32_t)b; break;
          case 5:  tomado = (int32_t)a >= (int32_t)b; break;
          case 6:  tomado = a < b; break;
          case 7:  tomado = a >= b; break;
          default: tomado = 0; break;
        }
        completar(s, c + 1, 0, 0);
        if (tomado) {
          uint32_t imm_b = ((uint32_t)((int32_t)w >> 31) << 12) | ((w << 4) & 0x800) | ((w >> 20) & 0x7e0) | ((w >> 7) & 0x1e);
          npc = pc + imm_b; ciclos = 3; s->n_br_t++;
        } else s->n_br_nt++;
        break;
      }
      case 0x6f: {                                                                           /* jal */
        uint32_t imm_j = ((uint32_t)((int32_t)w >> 31) << 20) | (w & 0xff000) | ((w >> 9) & 0x800) | ((w >> 20) & 0x7fe);
        completar(s, c + 1, rd, pc + 4);
        npc = pc + imm_j; ciclos = 3; s->n_jump++;
        break;
      }
      case 0x67:                                                                             /* jalr */
        completar(s, c + 1, rd, pc + 4);
        npc = (a + imm_i) & ~1u; ciclos = 3; s->n_jump++;
        break;
      default: completar(s, c + 1, 0, 0); s->n_otras++; break;      /* no hace nada */
    }
    s->pc = npc;
    if (!ya_leida) s->w = s->mem[(npc >> 2) & (NWORDS - 1)];
    s->c = c + ciclos;
  }
  spi_avanzar(s, s->c_fin);
  /* eventos de la maestra que quedan en el ultimo ciclo */
  while (s->spi_c <= s->c_fin && proximo_evento(s) <= s->c_fin) spi_paso(s, 0, 0, 0);
}

/* ---- Una simulacion completa ------------------------------------------------- */
static void simular(Sim *s, const uint32_t *programa, const int *precio, int nticks, uint8_t *leido) {
  FILE *f_csv = s->f_csv, *f_ticks = s->f_ticks, *f_traza = s->f_traza;
  memset(s, 0, sizeof *s);
  s->f_csv = f_csv; s->f_ticks = f_ticks; s->f_traza = f_traza;
  memcpy(s->mem, programa, sizeof s->mem);
  s->precio = precio; s->nticks = nticks; s->leido = leido;
  s->cs_sync = 7; s->pin_cs = 1;
  s->caja = s->w_pat = s->peak = cfg.caja0;
  s->R = ((int64_t)1 << cfg.por_bits) - 1;
  /* el testbench termina en inicio + nticks * periodo: ultimo flanco antes de ese instante */
  s->c_fin = (cfg.inicio_ns + (int64_t)nticks * cfg.periodo_ns - T_POS0 - 1) / T_CLK;
  s->t0 = -1;
  s->load_pend = -1;
  s->spi_c = 0;
  s->pc = 0; s->w = s->mem[0];
  s->c = s->R + 1;                         /* primera instruccion: el ciclo siguiente al fin del reset */
  correr_core(s);
}

/* ---- Entrada ------------------------------------------------------------------- */
static void leer_hex(const char *ruta, uint32_t *mem) {
  FILE *f = fopen(ruta, "r");
  if (!f) morir("no se pudo abrir el programa", ruta);
  int n = 0; unsigned v;
  memset(mem, 0, NWORDS * sizeof *mem);
  while (n < NWORDS && fscanf(f, "%x", &v) == 1) mem[n++] = v;
  fclose(f);
  if (n < NWORDS)
    fprintf(stderr, "gemelo: aviso: %s tiene %d palabras; el resto se toma como 0 (en el RTL simulado seria X)\n", ruta, n);
}

static int leer_serie(const char *ruta, int **precio) {
  FILE *f = fopen(ruta, "r");
  if (!f) morir("no se pudo abrir la serie", ruta);
  char linea[256];
  int n = 0, cap = 1 << 15, t, p;
  int *v = malloc(cap * sizeof *v);
  if (!fgets(linea, sizeof linea, f)) morir("serie vacia", ruta);
  while (fgets(linea, sizeof linea, f)) {
    if (sscanf(linea, "%d,%d", &t, &p) != 2) continue;
    if (p < 1 || p > 255) morir("precio fuera de 1..255 en", ruta);
    if (n == cap) { cap *= 2; v = realloc(v, cap * sizeof *v); }
    v[n++] = p;
  }
  fclose(f);
  *precio = v;
  return n;
}

static void ayuda(void) {
  puts("gemelo: gemelo digital del Pochoco SoC (ver el encabezado de ref/gemelo/gemelo.c)\n"
       "\n"
       "  --hex ARCHIVO         programa (por defecto sw/trade.hex)\n"
       "  --serie ARCHIVO       serie CSV \"tick,price\" (por defecto tb/practica.csv)\n"
       "  --lote ARCHIVO        varias series, una por linea, precios separados por espacios.\n"
       "                        Escribe una linea por serie:\n"
       "                        patrimonio ordenes perdida_max peor_caso respuestas precios_perdidos comprar_y_mantener\n"
       "  --nticks N            usar solo los primeros N ticks de la serie\n"
       "  --periodo-ns N        periodo entre precios (100000)\n"
       "  --inicio-ns N         instante de la primera transaccion (4000)\n"
       "  --cs-setup-ns N       de bajar CS_n al primer bit (1000)\n"
       "  --sclk-medio-ns N     medio periodo de SCLK (500, o sea 1 MHz)\n"
       "  --cs-hold-ns N        del ultimo flanco de SCLK a subir CS_n (500)\n"
       "  --por-bits N          ancho del contador de reset de pochoco_soc (12)\n"
       "  --caja N, --comision N   contabilidad (10000 y 5)\n"
       "  --borde 0|1           1: un cambio de pin que coincide con un flanco se ve en ese flanco (1)\n"
       "  --sin-atajo           simular cada vuelta del sondeo\n"
       "  --csv ARCHIVO         escribir decisiones.csv, igual al del testbench oficial\n"
       "  --ticks ARCHIVO       escribir una fila por tick, igual a la de tb/tb_cpi.sv\n"
       "  --traza ARCHIVO       escribir la traza de eventos, igual a la de tb/tb_cpi.sv\n"
       "  --callado             no imprimir el resumen");
}

static int64_t num(const char *txt) { return strtoll(txt, NULL, 0); }

int main(int argc, char **argv) {
  for (int i = 1; i < argc; i++) {
    const char *o = argv[i];
    const char *v = i + 1 < argc ? argv[i + 1] : NULL;
#define CON_VALOR(nombre, accion) if (!strcmp(o, nombre)) { if (!v) morir("falta el valor de", o); accion; i++; continue; }
    CON_VALOR("--hex", cfg.hex = v)
    CON_VALOR("--serie", cfg.serie = v)
    CON_VALOR("--lote", cfg.lote = v)
    CON_VALOR("--csv", cfg.csv = v)
    CON_VALOR("--ticks", cfg.ticks_csv = v)
    CON_VALOR("--traza", cfg.traza = v)
    CON_VALOR("--nticks", cfg.nticks = (int)num(v))
    CON_VALOR("--periodo-ns", cfg.periodo_ns = num(v))
    CON_VALOR("--inicio-ns", cfg.inicio_ns = num(v))
    CON_VALOR("--cs-setup-ns", cfg.cs_setup_ns = num(v))
    CON_VALOR("--sclk-medio-ns", cfg.sclk_medio_ns = num(v))
    CON_VALOR("--cs-hold-ns", cfg.cs_hold_ns = num(v))
    CON_VALOR("--por-bits", cfg.por_bits = (int)num(v))
    CON_VALOR("--caja", cfg.caja0 = (int)num(v))
    CON_VALOR("--comision", cfg.comision = (int)num(v))
    CON_VALOR("--borde", cfg.borde = (int)num(v))
    if (!strcmp(o, "--sin-atajo")) { cfg.atajo = 0; continue; }
    if (!strcmp(o, "--callado")) { cfg.resumen = 0; continue; }
    if (!strcmp(o, "--ayuda") || !strcmp(o, "-h") || !strcmp(o, "--help")) { ayuda(); return 0; }
    morir("opcion desconocida", o);
  }
  int64_t spi_ns = cfg.cs_setup_ns + 16 * cfg.sclk_medio_ns + cfg.cs_hold_ns;
  if (cfg.periodo_ns <= spi_ns) morir("el periodo es menor que la transaccion SPI", NULL);
  if (cfg.sclk_medio_ns < 1 || cfg.por_bits < 1 || cfg.por_bits > 30) morir("parametros fuera de rango", NULL);

  static uint32_t programa[NWORDS];
  static Sim s;
  leer_hex(cfg.hex, programa);

  if (cfg.lote) {                          /* una serie por linea */
    FILE *f = fopen(cfg.lote, "r");
    if (!f) morir("no se pudo abrir el lote", cfg.lote);
    size_t cap = 1 << 22;
    char *linea = malloc(cap);
    int *precio = malloc((cap / 2) * sizeof *precio);
    uint8_t *leido = malloc(cap / 2);
    while (fgets(linea, (int)cap, f)) {
      int n = 0;
      for (char *p = linea; *p; ) {
        char *fin;
        long val = strtol(p, &fin, 10);
        if (fin == p) { p++; continue; }
        if (val < 1 || val > 255) morir("precio fuera de 1..255 en el lote", cfg.lote);
        precio[n++] = (int)val; p = fin;
      }
      if (n == 0) continue;
      if (cfg.nticks > 0 && n > cfg.nticks) n = cfg.nticks;
      simular(&s, programa, precio, n, leido);
      int q = (cfg.caja0 - cfg.comision) / precio[0];
      printf("%d %d %d %d %d %d %d\n", s.w_pat, s.ordenes, s.max_dd, s.peor_caso, s.respuestas, s.precios_perdidos,
             cfg.caja0 - cfg.comision - q * precio[0] + q * precio[n - 1]);
    }
    fclose(f);
    return 0;
  }

  int *precio;
  int n = leer_serie(cfg.serie, &precio);
  if (cfg.nticks > 0 && cfg.nticks < n) n = cfg.nticks;
  if (n == 0) morir("la serie no tiene precios", cfg.serie);
  uint8_t *leido = calloc((size_t)n, 1);

  if (cfg.csv) {
    if (!(s.f_csv = fopen(cfg.csv, "w"))) morir("no se pudo crear", cfg.csv);
    fprintf(s.f_csv, "tick,precio,decision,caja,acciones,patrimonio\n");
  }
  if (cfg.ticks_csv) {
    if (!(s.f_ticks = fopen(cfg.ticks_csv, "w"))) morir("no se pudo crear", cfg.ticks_csv);
    fprintf(s.f_ticks, "tick,precio,decision_leida,ciclo_precio,ciclos_respuesta,ic_respuesta,ciclos_tick,ic_tick\n");
  }
  if (cfg.traza && !(s.f_traza = fopen(cfg.traza, "w"))) morir("no se pudo crear", cfg.traza);

  simular(&s, programa, precio, n, leido);

  if (s.f_csv) fclose(s.f_csv);
  if (s.f_ticks) fclose(s.f_ticks);
  if (s.f_traza) fclose(s.f_traza);
  if (!cfg.resumen) return 0;

  /* Mismas lineas que imprime tb_proyecto_4.sv */
  int q = (cfg.caja0 - cfg.comision) / precio[0];
  int presupuesto = (int)((cfg.periodo_ns - spi_ns) / T_CLK);
  int ok[4] = { 1, s.respuestas > 0, s.precios_perdidos == 0, s.peor_caso < presupuesto }, aprobados = 0;
  const char *nombre[4] = { "MISO sin valores X", "el programa escribe DECISION", "el programa lee todos los precios",
                            "la decision llega antes del siguiente tick" };
  printf("Patrimonio final:          %d\n", s.w_pat);
  printf("Ordenes ejecutadas:        %d\n", s.ordenes);
  printf("Perdida maxima:            %d\n", s.max_dd);
  printf("No operar:                 %d\n", cfg.caja0);
  printf("Comprar y mantener:        %d\n", cfg.caja0 - cfg.comision - q * precio[0] + q * precio[n - 1]);
  printf("Peor caso precio->decision: %d ciclos (disponibles: %d)\n", s.peor_caso, presupuesto);
  printf("Detalle por tick en decisiones.csv\n");
  for (int i = 0; i < 4; i++) { printf("%s %s\n", ok[i] ? "PASS" : "FAIL", nombre[i]); aprobados += ok[i]; }
  printf("Testbenchs aprobados: %d/4\n", aprobados);
  /* Lo que el testbench oficial no imprime */
  printf("Gemelo: %lld instrucciones, %lld ciclos desde el reset, %lld vueltas de sondeo saltadas\n",
         (long long)s.ic, (long long)(s.c_fin - s.R), (long long)s.vueltas_saltadas);
  if (s.ticks_medidos > 0) {
    double m = s.ticks_medidos;
    printf("Gemelo: %d ticks medidos. Respuesta: %.2f ciclos e IC %.2f en promedio, peor caso %d ciclos e IC %d. "
           "Tick completo: %.2f ciclos e IC %.2f en promedio, peor caso %d ciclos e IC %d\n",
           s.ticks_medidos, s.suma_r_ciclos / m, s.suma_r_ic / m, s.peor_r_ciclos, s.peor_r_ic,
           s.suma_t_ciclos / m, s.suma_t_ic / m, s.peor_t_ciclos, s.peor_t_ic);
  }
  return aprobados == 4 ? 0 : 1;
}
