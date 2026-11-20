#!/usr/bin/env python3
"""optimo_estrategia.py: la política óptima del paseo normalizado como estrategia (sección 13).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Misma regla de fases que regimen.Politica (y que la banda 40). En las fases que la variante
optimiza (V1 y V3: A; V2: A, B, C y D) decide con la tabla de la programación dinámica
(paseo_optimo.dp): s' = tabla[fase][clase de v^2][(r * 156 + x - 100) * nS + s], con r los ticks
restantes, x el precio y s la posición objetivo actual (0 caja, 1 invertido; en V3 también 1/2).
Fuera de esas fases, lo de siempre: B invertido, C en caja, D banda 40.

v^2 en vivo: 'S2/t' (S2 de regimen.Politica, diferencias acotadas a 15, dividido por las
diferencias vistas) o '2000' (lo mismo en las últimas 2000). La clase es la v^2 de la grilla más
cercana en escala logarítmica. Antes de t = 390 no se usa la tabla (como la clase de regimen.py).
Las órdenes: invertido es "comprar 63", caja es "vender 63"; media posición fija, al pasar a ella,
el objetivo en acciones del patrimonio / (2 p) y va hacia él con órdenes de hasta 63.

Con pol = None (la política apagada) decide byte a byte lo mismo que la banda 40.
Comprimida (G3): en vez de la tabla completa, umbrales por celda (clase, tramo de r):
ver comprimir().
"""
import math

import ideas
import paseo_optimo as P
import regimen as RG
from ideas import M, C, V, LO, HI, hacia

T_MIN = 390
CORTES = [math.sqrt(P.V2S[k] * P.V2S[k + 1]) for k in range(len(P.V2S) - 1)]
# Versión de placa (pedido del 19/11, noche): cortes en sesenta y cuatroavos, comparados con sumas
# (64 S2 >= N_j (t - 1), con 64 S2 y N_j (t - 1) llevados como sumas corridas), e histéresis de 64
# ticks como la clase de regimen.py. Los cortes son las medias geométricas de la grilla redondeadas
# a 1/64: 0,172, 0,313, 0,438, 0,609, 0,859, 1,219 y 1,734.
N64 = (11, 20, 28, 39, 55, 78, 111)
HIST = 64
TABLAS = {}


def clase_v(v2):
    j = 0
    while j < len(CORTES) and v2 >= CORTES[j]:
        j += 1
    return j


def tablas(variante, objetivo):
    k = (variante, objetivo)
    if k not in TABLAS:
        TABLAS[k] = P.cargar_pol(variante, objetivo)
    return TABLAS[k]


def clase_placa(S2, nd):
    a = S2 + S2
    a = a + a
    a = a + a
    a = a + a
    a = a + a
    a = a + a          # 64 S2 con sumas
    j = 0
    while j < 7 and a >= N64[j] * nd:
        j += 1
    return j


class Optima(RG.Politica):
    def __init__(self, variante=None, objetivo="log", estimador="S2/t", comprimida=None, placa=False, guarda=None):
        super().__init__()
        self.placa = placa
        self.cv = -1
        self.cv_cuenta = 0
        self.guarda = guarda            # (d, media, alta) o None
        self.a_off = False
        self.entrada = 0
        self.topes = 0
        self.var = variante
        self.est = estimador
        self.pol = tablas(variante, objetivo) if (variante and comprimida is None) else None
        self.comp = comprimida              # dict de umbrales (G3) o None
        self.apagada = variante is None
        self.opt = P.VARIANTES[variante] if variante else ()
        self.nS = len(P.POS[variante]) if variante else 2
        self.top = self.nS - 1
        self.s = 0
        self.obj = None
        self.ring = [0] * 2000
        self.k = 0
        self.sw = 0
        self.usos = 0

    def _v2(self):
        nd = self.t - 1
        if self.est == "2000" and nd >= 2000:
            return self.sw / 2000
        return self.S2 / nd

    def _orden(self, sp, p, caja, acc):
        if sp == self.top:
            self.q = C
            o = C
        elif sp == 0:
            self.q = V
            o = V
        else:
            if self.s != sp or self.obj is None:
                self.obj = (caja + acc * p) // (2 * p)
            o = hacia(self.obj, acc)
        if sp != self.nS // 2 or self.nS == 2:
            self.obj = None
        self.s = sp
        return o

    def _clase(self):
        """Clase de v^2 de placa con histéresis, actualizada en cada tick desde t = 390."""
        if self.t < T_MIN:
            return
        raw = clase_placa(self.S2, self.t - 1)
        if self.cv < 0:
            self.cv = raw
        elif raw != self.cv:
            self.cv_cuenta += 1
            if self.cv_cuenta >= HIST:
                self.cv = raw
                self.cv_cuenta = 0
        else:
            self.cv_cuenta = 0

    def _guardas(self, F, j, p, sp):
        g = self.guarda
        if F != "A" or g is None:
            return sp
        d, media, alta = g
        if self.a_off:
            sp = 0
        elif d and self.s > 0 and p <= self.entrada - d:
            sp = 0
            self.a_off = True
            self.topes += 1
        else:
            if alta and j >= 6 and sp > self.s:
                sp = self.s
            if media and sp > 1:
                sp = 1
        if self.s == 0 and sp > 0:
            self.entrada = p
        return sp

    def _tabla(self, F, p, caja, acc):
        """Decisión de la tabla, o None si no se usa (antes de t = 390)."""
        if self.t < T_MIN:
            return None
        j = self.cv if self.placa else clase_v(self._v2())
        r = P.N - 1 - self.n
        if r < 0:
            r = 0
        self.usos += 1
        if self.comp is not None:
            sp = self.comp.decide(F, j, r, p, self.s)
        else:
            sp = self.pol[F][j][(r * P.L + p - LO) * self.nS + self.s]
        if self.guarda is not None:
            sp = self._guardas(F, j, p, sp)
        return self._orden(sp, p, caja, acc)

    def _fijo(self):
        self.s = self.top if self.q == C else 0
        self.obj = None
        return self.q

    def decidir(self, p, caja, acc):
        self.n += 1
        prev = self.prev
        self._regimen(p)
        if self.placa:
            self._clase()
        if prev >= 0:
            d = p - prev
            if d < 0:
                d = -d
            if d > 15:
                d = 15
            sq = d * d
            self.sw += sq - self.ring[self.k]
            self.ring[self.k] = sq
            self.k += 1
            if self.k == 2000:
                self.k = 0
        if p > self.pmax:
            self.pmax = p
        if self.tD >= 0:
            if "D" in self.opt:
                o = self._tabla("D", p, caja, acc)
                if o is not None:
                    return o
            self._d(p)
            return self._fijo()
        if p <= LO:
            self.vlo = True
            self.q = C
        elif p >= HI:
            self.vhi = True
            self.q = V
        else:
            if not self.apagada:
                F = "A" if not (self.vlo or self.vhi) else ("B" if self.vlo else "C")
                if F in self.opt:
                    o = self._tabla(F, p, caja, acc)
                    if o is not None:
                        return o
                    if F == "A":
                        return self.q
                return self._fijo()
            return self.q
        if self.vlo and self.vhi:
            self.tD = self.n
            self.caso = 1 if p >= HI else 2
            self.q = V if self.caso == 1 else C
            if "D" in self.opt:
                o = self._tabla("D", p, caja, acc)
                if o is not None:
                    return o
            return self._fijo() if not self.apagada else self.q
        if not self.apagada:
            F = "B" if self.vlo else "C"
            if F in self.opt:
                o = self._tabla(F, p, caja, acc)
                if o is not None:
                    return o
            return self._fijo()
        return self.q

    def info(self):
        return (self.tD, self.caso, self.usos, self.topes)


# --- compresión (G3) ---------------------------------------------------------------------------

TRAMOS = 16
LARGO_TRAMO = P.N // TRAMOS


class Comprimida:
    """Umbrales por celda (fase, clase de v^2, tramo de 1250 ticks restantes), tomados de la tabla
    completa en el r del medio del tramo. La forma de la tabla en la fase A (sección 13.4): con s = 0
    compra en un intervalo alto que no llega al borde (deja fuera los últimos niveles bajo 255) y, a
    veces, en un intervalo bajo que parte en 101; con s = 1 mantiene en intervalos parecidos pero más
    anchos (histéresis). Cuatro bytes por celda:
      alto   compra con s = 0 si x >= alto (el bloque alto, sin su corte superior)
      bajo   compra con s = 0 si x <= bajo (el bloque que parte en 101)
      salida con s = 1 mantiene si x >= salida
      bajo1  con s = 1 mantiene si x <= bajo1
    256 en alto o salida y 99 en bajo o bajo1 marcan un intervalo vacío. Con tres posiciones (V3), cuatro
    umbrales por cada s (ver _niveles): 12 bytes por celda, 1536 en la fase A."""

    def __init__(self, variante, objetivo):
        pol = tablas(variante, objetivo)
        self.nS = len(P.POS[variante])
        self.cel = {}
        for F, por_v in pol.items():
            i0, i1 = P.RANGO[F]
            for j, t in enumerate(por_v):
                for tr in range(TRAMOS):
                    r = tr * LARGO_TRAMO + LARGO_TRAMO // 2
                    u = []
                    for s in range(self.nS):
                        dec = [t[(r * P.L + i) * self.nS + s] for i in range(i0, i1)]
                        u.append(self._intervalos(dec, i0))
                    if self.nS == 2:
                        self.cel[(F, j, tr)] = (u[0][0], u[0][1], u[1][0], u[1][1])
                    else:
                        self.cel[(F, j, tr)] = tuple(self._niveles(
                            [t[(r * P.L + i) * 3 + s] for i in range(i0, i1)], i0) for s in range(3))

    @staticmethod
    def _intervalos(dec, i0):
        n = len(dec)
        bajo = 99
        k = 0
        while k < n and dec[k] == 1:
            bajo = LO + i0 + k
            k += 1
        alto = 256
        k = n - 1
        while k >= 0 and dec[k] == 0:          # corte superior (se ignora)
            k -= 1
        if k >= 0 and LO + i0 + k > bajo:
            while k >= 0 and dec[k] == 1 and LO + i0 + k > bajo:
                alto = LO + i0 + k
                k -= 1
        return alto, bajo

    @staticmethod
    def _niveles(dec, i0):
        """V3 (tres posiciones): umbrales (a1, a2, b1, b2): s' >= 1/2 si x >= a1 o x <= b1; s' = 1 si
        x >= a2 o x <= b2. Arriba se ignoran los ceros y la media posición del corte superior."""
        n = len(dec)
        b1 = b2 = 99
        k = 0
        while k < n and dec[k] == 2:
            b2 = b1 = LO + i0 + k
            k += 1
        while k < n and dec[k] >= 1:
            b1 = LO + i0 + k
            k += 1
        a1 = a2 = 256
        k = n - 1
        while k >= 0 and dec[k] == 0:
            k -= 1
        while k >= 0 and dec[k] == 1 and LO + i0 + k > b1:
            k -= 1
        if k >= 0 and dec[k] == 2:
            while k >= 0 and dec[k] == 2 and LO + i0 + k > b1:
                a2 = a1 = LO + i0 + k
                k -= 1
            while k >= 0 and dec[k] >= 1 and LO + i0 + k > b1:
                a1 = LO + i0 + k
                k -= 1
        else:       # sin bloque de posición completa arriba: el bloque de media posición
            k = n - 1
            while k >= 0 and dec[k] == 0:
                k -= 1
            while k >= 0 and dec[k] >= 1 and LO + i0 + k > b1:
                a1 = LO + i0 + k
                k -= 1
        return a1, a2, b1, b2

    def decide(self, F, j, r, p, s):
        tr = min(TRAMOS - 1, r // LARGO_TRAMO)
        if self.nS == 3:
            a1, a2, b1, b2 = self.cel[(F, j, tr)][s]
            return 2 if (p >= a2 or p <= b2) else 1 if (p >= a1 or p <= b1) else 0
        alto, bajo, salida, bajo1 = self.cel[(F, j, tr)]
        if s == 0:
            return 1 if (p >= alto or p <= bajo) else 0
        return 1 if (p >= salida or p <= bajo1) else 0


COMPRIMIDAS = {}


def comprimida(variante, objetivo):
    k = (variante, objetivo)
    if k not in COMPRIMIDAS:
        COMPRIMIDAS[k] = Comprimida(variante, objetivo)
    return COMPRIMIDAS[k]


_crear_previo = ideas.crear


def _crear(spec):
    if spec[0] == "optima":
        kw = dict(spec[1])
        comp = kw.pop("comprimida", False)
        if comp:
            return Optima(comprimida=comprimida(kw["variante"], kw["objetivo"]), **kw)
        return Optima(**kw)
    return _crear_previo(spec)


ideas.crear = _crear


def spec(variante=None, objetivo="log", estimador="S2/t", comprimida=False, placa=False, guarda=None):
    d = {"variante": variante, "objetivo": objetivo, "estimador": estimador}
    if comprimida:
        d["comprimida"] = True
    if placa:
        d["placa"] = True
    if guarda is not None:
        d["guarda"] = tuple(guarda)
    return ("optima", d)
