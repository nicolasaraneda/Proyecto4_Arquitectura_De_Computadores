#!/usr/bin/env python3
"""c1.py: referencia entera de C1 (R3), exacta a nivel de bit con sw/c1.s.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

C1 (docs/exploracion_ideas.md de la rama minutos-reales, sección 15): la banda 40 con un desempate.
  fase A   antes de ver 100 o 255: media posición solo cuando la tabla da probabilidad >= 0,95 de
           que el 255 llegue antes que el 100
  motor    desde el primer extremo: la política óptima V2 comprimida, hasta ganarle M al clon
  candado  cuando el patrimonio propio supera en M (100) al de un clon de la banda 40, copia al clon
           hasta el final de la ronda

Solo usa sumas, restas, comparaciones y lecturas de tabla, en el mismo orden que el programa de los
cuatro hilos (docs/c1_plan.md). Cada bloque dice qué hilo lo calcula. La referencia no modela
ciclos: con los cuatro hilos sanos la decisión no depende de cuánto demora cada uno. Las fallas
(un hilo que no publica a tiempo) se modelan con dos conjuntos de ticks:
  faltas    la política de ese tick no llega nunca (un hilo colgado)
  tardias   llega después del plazo y antes del plazo del tick siguiente (dato viejo)

Uso, desde la raíz:
  python3 ref/c1/c1.py SERIE.csv [--tabla sw/c1_tabla.hex] [--nticks N] [--periodo-ns P] [-o decisiones.csv]
Con --periodo-ns modela los precios que el programa no ve durante el reset del testbench, y -o
escribe el decisiones.csv del testbench oficial (ref/market.py).
"""
import argparse
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import tablas as TB  # noqa: E402

M_, C_, V_ = 0x00, 0x7F, 0xBF            # mantener, comprar 63, vender 63
MODO_A, MODO_REC, MODO_COPIA = 0, 1, 2
OBJ_MAX = 511                            # tope del cociente de la media posición (9 bits)
U32 = 0xFFFFFFFF


def ejecutar(byte, p, caja, acc, com):
    """La contabilidad oficial para un byte, como la hace el hilo 3: una sola rutina voraz con los
    múltiplos p, 2p, ..., 32p. Devuelve (caja, acc, ejecutó).
      compra  q = min(cantidad, floor((caja - com) / p)); caja -= q p + com
      venta   q = min(cantidad, acc); caja += q p - com
    Una orden que queda en cero no se ejecuta ni paga."""
    cant = byte & 63
    if byte & 0x40:
        x = caja - com
        if x < 0:
            return caja, acc, 0
        rq = cant
    elif byte & 0x80:
        rq = cant if cant < acc else acc
        x = ~caja & U32                  # la venta suma: se resta de ~caja, que sin signo siempre alcanza
    else:
        return caja, acc, 0
    total = rq
    for w in (32, 16, 8, 4, 2, 1):       # los múltiplos w p se arman con sumas: p, 2p, 4p, ..., 32p
        m = w * p
        if rq >= w and x >= m:
            x -= m
            rq -= w
    q = total - rq
    if q == 0:
        return caja, acc, 0
    if byte & 0x40:
        return x, acc + q, 1
    caja = (~x & U32)
    if caja & 0x80000000:
        caja -= 1 << 32
    return caja - com, acc - q, 1


def producto(a, p):
    """a por p con los 8 bits de p, por duplicaciones y sumas. Exacto para cualquier a."""
    r = 0
    for bit in (128, 64, 32, 16, 8, 4, 2, 1):
        r = r + r
        if p & bit:
            r = r + a
    return r


def media_posicion(W, p):
    """min(511, floor(W / (2 p))) por división con restas de 9 pasos."""
    d = producto(512, p)                 # 512 p = (2 p) 2^8, por duplicaciones
    if W >= d + d:
        return OBJ_MAX
    q = 0
    for _ in range(9):
        q = q + q
        if W >= d:
            W -= d
            q += 1
        W = W + W
    return q


def hacia(obj, acc):
    """Orden de hasta 63 acciones hacia la posición objetivo."""
    d = obj - acc
    if d > 0:
        return 0x40 | (63 if d > 63 else d)
    if d < 0:
        d = -d
        return 0x80 | (63 if d > 63 else d)
    return M_


class C1:
    """Un objeto por ronda. paso(p) recibe el precio del tick y devuelve el byte que el hilo 0
    escribe en DECISION. `faltas` y `tardias`: ticks (desde 1) en que la política no llega dentro
    del plazo; en los de `tardias` llega después (queda como la del tick anterior para el siguiente)."""

    def __init__(self, tabla, faltas=(), programa=None, tardias=()):
        T = tabla
        self.T = T
        par = dict(TB.PROGRAMA)
        if programa:
            par.update(programa)
        self.lo1, self.hi, self.bc, self.bv = T[TB.T_LO_MAS_1], T[TB.T_HI], T[TB.T_BANDA_COMPRA], T[TB.T_BANDA_VENTA]
        self.M, self.n_ronda, self.t_min = par["m"], par["n_ronda"], TB.T_MIN
        self.caja0 = par["caja"]
        self.com, self.hist, self.p_min = par["comision"], TB.HISTERESIS, par["p_min"]
        self.faltas = faltas
        self.tardias = tardias
        # hilo 0: corredor
        self.k = 0
        self.q = M_
        self.vlo = self.vhi = 0
        self.seguro = 1 if T[TB.T_POLITICA] == TB.POLITICA_APAGADA else 0
        self.pol_tick = -1              # tick de la última política recibida (publicada por el hilo 3)
        self.pol_byte = M_
        self.pol_ultimo = None          # el byte que el hilo 3 publicó en el último tick
        self.vencidos = 0               # ticks con el plazo vencido
        # hilo 1: régimen y reloj
        self.prev = -1
        self.a64 = 0                    # 64 S2
        self.B = [0] * 7                # N_j (t - 1)
        self.cv = -1
        self.cnt = 0
        self.tr_a, self.c_a = TB.TRAMOS_A - 1, TB.LARGO_A
        self.tr_m, self.c_m = TB.TRAMOS_M - 1, TB.LARGO_M
        # hilo 2: política (tablas)
        self.sa = 0                     # posición de la fase A según la tabla (0 caja, 1 media)
        self.sm = 0                     # posición del motor (0 caja, 1 invertido)
        # hilo 3: emulador del clon, cuenta propia y máquina de modos
        self.caja, self.acc = self.caja0, 0
        self.cajac, self.accc = self.caja0, 0
        self.ord = M_                   # byte propio pendiente (el que el hilo 0 escribió)
        self.qc = M_                    # byte pendiente del clon
        self.modo = MODO_A
        self.obj = 0
        self.D = 0
        self.W = self.caja0

    # --- hilo 1 ---
    def _regimen(self, p, k):
        if self.prev >= 0:
            d = p - self.prev
            if d < 0:
                d = -d
            if d > TB.D_MAX:
                d = TB.D_MAX
            self.a64 += self.T[TB.T_CUAD64 + d]
        self.prev = p
        if k >= 2:
            for j in range(7):
                self.B[j] += self.T[TB.T_N64 + j]
        activa = 1 if k >= self.t_min else 0
        if activa:
            raw = 0
            while raw < 7 and self.a64 >= self.B[raw]:
                raw += 1
            if self.cv < 0:
                self.cv = raw
            elif raw != self.cv:
                self.cnt += 1
                if self.cnt >= self.hist:
                    self.cv = raw
                    self.cnt = 0
            else:
                self.cnt = 0
        ia = TB.T_FASE_A + self.cv * TB.TRAMOS_A + self.tr_a if activa else 0
        im = TB.T_MOTOR + self.cv * TB.TRAMOS_M + self.tr_m if activa else 0
        # reloj: los tramos del tick siguiente
        self.c_a -= 1
        if self.c_a == 0:
            self.c_a = TB.LARGO_A
            if self.tr_a > 0:
                self.tr_a -= 1
        self.c_m -= 1
        if self.c_m == 0:
            self.c_m = TB.LARGO_M
            if self.tr_m > 0:
                self.tr_m -= 1
        return activa, ia, im

    def paso(self, p):
        self.k += 1
        k = self.k
        T = self.T
        # --- hilo 0: banda 40 (la misma cuenta de sw/fondo.s) y modo seguro ---
        lo = 1 if p < self.lo1 else 0
        hi = 1 if p >= self.hi else 0
        self.vlo |= lo
        self.vhi |= hi
        dos = self.vlo & self.vhi
        compra = lo | (dos & (1 if p < self.bc else 0))
        vende = hi | (dos & (1 if p >= self.bv else 0))
        if compra | vende:
            self.q = V_ if vende else C_
        q = self.q
        if p < self.p_min or k > self.n_ronda:
            self.seguro = 1
        # --- hilo 1: régimen y reloj ---
        activa, ia, im = self._regimen(p, k)
        # --- hilo 2: tablas ---
        en_a = 0 if (self.vlo | self.vhi) else 1
        spa = entra = 0
        if en_a:
            if activa:
                cel = T[ia]
                if self.sa == 0:
                    spa = entra = 1 if p >= (cel & 0xFF) else 0
                else:
                    spa = 1 if p >= (cel >> 8) else 0
                self.sa = spa
            self.sm = 1 if q == C_ else 0
        elif not activa:
            self.sm = 1 if q == C_ else 0
        else:
            cel = T[im + (128 if dos else 0 if self.vlo else 64)]
            self.sm = 1 if p <= ((cel >> 8) if self.sm else (cel & 0xFF)) else 0
        # --- hilo 3: las dos cuentas, D y la máquina de modos ---
        self.caja, self.acc, _ = ejecutar(self.ord, p, self.caja, self.acc, self.com)
        self.cajac, self.accc, _ = ejecutar(self.qc, p, self.cajac, self.accc, self.com)
        r = producto(self.acc - self.accc, p)
        self.D = self.caja - self.cajac + r
        if self.modo == MODO_A and not en_a:
            self.modo = MODO_REC
        if self.modo == MODO_REC and self.D >= self.M:
            self.modo = MODO_COPIA
        if self.modo == MODO_COPIA:
            b = q
        elif self.modo == MODO_REC:
            b = C_ if self.sm else V_
        elif not activa:
            b = M_
        elif not spa:
            b = V_
        else:
            if entra:
                self.obj = media_posicion(self.caja + r, p)     # en la fase A el clon no tiene acciones: r = acc p
            b = hacia(self.obj, self.acc)
        self.qc = q
        self.pol_ultimo = b
        self.W = self.caja + producto(self.acc, p)              # fuera del camino de la respuesta: telemetría
        # --- hilo 0: elige el byte ---
        if self.seguro:
            byte = q
        elif k in self.faltas or k in self.tardias:
            # degradación: el plazo venció sin la política de este tick
            self.vencidos += 1
            if self.pol_tick == k - 1:
                # la del tick anterior: se sostiene si es una orden completa (63); una parcial no se repite
                byte = self.pol_byte if (self.pol_byte & 63) == 63 else M_
            else:
                self.seguro = 1
                byte = q
            if k in self.tardias:
                self.pol_tick, self.pol_byte = k, b             # llegó tarde: sirve de anterior para el tick k + 1
        else:
            self.pol_tick, self.pol_byte = k, b
            byte = b
        self.ord = byte
        return byte

    decidir = paso                      # la interfaz de ref/trader.py


def correr(precios, tabla, faltas=(), programa=None, tardias=()):
    c = C1(tabla, faltas, programa, tardias)
    return [c.paso(p) for p in precios], c


def patrimonio(precios, bytes_, caja0=10000, com=5):
    """Contabilidad oficial del testbench (ref/market.py): el byte del tick n se ejecuta al precio n + 1."""
    caja, acc, d, nord = caja0, 0, 0, 0
    for p, b in zip(precios, bytes_):
        a, q = d >> 6, d & 63
        if a == 1:
            t = (caja - com) // p if p else 0
            q = min(q, t)
            if q > 0:
                caja -= q * p + com
                acc += q
                nord += 1
        elif a == 2:
            q = min(q, acc)
            if q > 0:
                caja += q * p - com
                acc -= q
                nord += 1
        d = b
    return caja + acc * precios[-1], nord


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("serie")
    ap.add_argument("--tabla", default=os.path.join(os.path.dirname(os.path.dirname(AQUI)), "sw", "c1_tabla.hex"))
    ap.add_argument("--nticks", type=int)
    ap.add_argument("--periodo-ns", type=int, help="período del testbench: modela los precios que se pierden en el reset")
    ap.add_argument("--perdidos", type=int, help="fijar a mano cuántos precios iniciales no se ven")
    ap.add_argument("-o", "--salida", help="escribir el decisiones.csv de referencia (formato del testbench oficial)")
    ap.add_argument("--faltas", default="", help="ticks en que la política no llega nunca: a-b,c (un hilo colgado)")
    ap.add_argument("--tardias", default="", help="ticks en que la política llega después del plazo: a,b")
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(AQUI))
    import market
    import trader
    precios = market.leer_serie(a.serie, a.nticks)
    perdidos = a.perdidos if a.perdidos is not None else trader.ticks_perdidos(a.periodo_ns) if a.periodo_ns else 0

    def ticks(texto):
        out = set()
        for parte in filter(None, texto.split(",")):
            lo, _, hi = parte.partition("-")
            out.update(range(int(lo), int(hi or lo) + 1))
        return out
    c = C1(TB.leer_hex(a.tabla), ticks(a.faltas), None, ticks(a.tardias))
    filas = [] if a.salida else None
    m = market.simular(precios, trader.decisiones(precios, c, perdidos), c.caja0, c.com, filas)
    if a.salida:
        market.escribir_csv(a.salida, filas)
    print(f"Serie {a.serie}: {len(precios)} ticks, precios iniciales que el programa no ve: {perdidos}")
    print(f"R3 (sw/c1.s): patrimonio final {m.w}, {m.ordenes} ordenes, modo final {c.modo}, cuenta emulada {c.W}, "
          f"D {c.D}, modo seguro {c.seguro}")


if __name__ == "__main__":
    main()
