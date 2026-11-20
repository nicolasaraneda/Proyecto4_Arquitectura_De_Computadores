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


class Optima(RG.Politica):
    def __init__(self, variante=None, objetivo="log", estimador="S2/t", comprimida=None):
        super().__init__()
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

    def _tabla(self, F, p, caja, acc):
        """Decisión de la tabla, o None si no se usa (antes de t = 390)."""
        if self.t < T_MIN:
            return None
        j = clase_v(self._v2())
        r = P.N - 1 - self.n
        if r < 0:
            r = 0
        self.usos += 1
        if self.comp is not None:
            sp = self.comp.decide(F, j, r, p, self.s)
        else:
            sp = self.pol[F][j][(r * P.L + p - LO) * self.nS + self.s]
        return self._orden(sp, p, caja, acc)

    def _fijo(self):
        self.s = self.top if self.q == C else 0
        self.obj = None
        return self.q

    def decidir(self, p, caja, acc):
        self.n += 1
        prev = self.prev
        self._regimen(p)
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
        return (self.tD, self.caso, self.usos)


# --- compresión (G3) ---------------------------------------------------------------------------

TRAMOS = 16
LARGO_TRAMO = P.N // TRAMOS


class Comprimida:
    """Umbrales por celda (clase de v^2, tramo de r, fase): para cada posición s, el conjunto de x con
    s' = arriba se aproxima por x >= alto[s] o x <= bajo[s] (los dos intervalos que tocan los
    bordes), tomados de la tabla completa en el r del medio del tramo. 0 en alto o 255 en bajo
    marcan 'vacío'. Para V3 hay además el umbral de media posición. Solo variantes de dos
    posiciones."""

    def __init__(self, variante, objetivo):
        pol = tablas(variante, objetivo)
        self.nS = len(P.POS[variante])
        self.cel = {}
        for F, por_v in pol.items():
            i0, i1 = P.RANGO[F]
            for j, t in enumerate(por_v):
                for tr in range(TRAMOS):
                    r = tr * LARGO_TRAMO + LARGO_TRAMO // 2
                    for s in range(self.nS):
                        dec = [t[(r * P.L + i) * self.nS + s] for i in range(i0, i1)]
                        top = self.nS - 1
                        # intervalo alto: desde el borde superior hacia abajo mientras s' = top
                        alto = 256
                        for i in range(i1 - 1, i0 - 1, -1):
                            if dec[i - i0] == top:
                                alto = LO + i
                            else:
                                break
                        bajo = 99
                        for i in range(i0, i1):
                            if dec[i - i0] == top:
                                bajo = LO + i
                            else:
                                break
                        if bajo >= alto:      # todo el rango
                            bajo = 255
                        self.cel[(F, j, tr, s)] = (alto, bajo)

    def decide(self, F, j, r, p, s):
        tr = min(TRAMOS - 1, r // LARGO_TRAMO)
        alto, bajo = self.cel[(F, j, tr, s)]
        return (self.nS - 1) if (p >= alto or p <= bajo) else 0


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


def spec(variante=None, objetivo="log", estimador="S2/t", comprimida=False):
    d = {"variante": variante, "objetivo": objetivo, "estimador": estimador}
    if comprimida:
        d["comprimida"] = True
    return ("optima", d)
