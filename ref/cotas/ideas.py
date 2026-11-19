#!/usr/bin/env python3
"""ideas.py: motor común y estrategias de la exploración de ideas (docs/exploracion_ideas.md).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Motor (correr): la contabilidad oficial de ref/market.py (caja 10 000, comisión 5, compra
recortada a (caja - 5) / p, venta recortada a las acciones), con la regla de tiempo del
testbench: el byte que se ejecuta al precio n es el que la estrategia escribió después de ver
el precio n - 1. La estrategia recibe en cada tick el precio recién ejecutado y su propia caja
y acciones: el programa puede llevar esa cuenta por su lado, porque conoce sus órdenes, los
precios y las reglas de recorte (necesita q por p, que sin multiplicador es un lazo de
desplazamientos y sumas de 7 pasos, y una comparación para el recorte).

Fases (definiciones del pedido del 18/11):
  A  no se ha visto ni 100 ni 255: en caja; al ver 100 compra 63 (repetido), al ver 255 vende.
  B  se vio 100 y falta 255 (el 255 está garantizado): todo invertido.
  C  se vio 255 y falta 100 (el 100 está garantizado): en caja.
  D  se vieron los dos: decide el comportamiento de cada idea.
Regla(BandaD(140, 215)) es la regla de los peldaños con banda 40, idéntica byte a byte a
regla_cotas.Cotas("espera", banda=40) (ref/cotas/explorar_ideas.py validar).

Todas las órdenes son de 63 acciones como máximo; un cambio completo de posición toma 2 o 3
ticks, y el motor lo simula así porque ejecuta cada byte con su recorte.
"""
import collections

M, C, V = 0x00, 0x40 | 63, 0x80 | 63
LO, HI = 100, 255
LARGO = 20000
CAJA0, COMISION = 10000, 5


def correr(w, s, caja0=CAJA0, com=COMISION):
    """Corre la estrategia s sobre la ventana w. Devuelve (patrimonio, órdenes, pérdida máxima
    desde un peak como fracción del peak)."""
    caja = caja0
    acc = 0
    d = M
    nord = 0
    peak = lim = caja0
    mdd = 0.0
    W = caja0
    dec = s.decidir
    for p in w:
        if d:
            a = d >> 6
            if a == 1:
                q = d & 63
                t = (caja - com) // p
                if q > t:
                    q = t
                if q > 0:
                    caja -= q * p + com
                    acc += q
                    nord += 1
            elif a == 2:
                q = d & 63
                if q > acc:
                    q = acc
                if q > 0 and caja + q * p >= com:
                    caja += q * p - com
                    acc -= q
                    nord += 1
        W = caja + acc * p
        if W > peak:
            peak = W
            lim = peak * (1.0 - mdd)
        elif W < lim:
            mdd = 1.0 - W / peak
            lim = W
        d = dec(p, caja, acc)
    return W, nord, mdd


def hacia(obj, acc):
    """Orden de hasta 63 acciones hacia una posición objetivo en acciones."""
    if acc < obj:
        q = obj - acc
        return 0x40 | (63 if q > 63 else q)
    if acc > obj:
        q = acc - obj
        return 0x80 | (63 if q > 63 else q)
    return M


class Cuenta:
    """Cuenta virtual con la contabilidad oficial exacta (ideas 3 y 7). paso(p) ejecuta la orden
    pendiente al precio p y pide la siguiente, igual que el motor."""
    __slots__ = ("s", "caja", "acc", "d", "W")

    def __init__(self, s):
        self.s, self.caja, self.acc, self.d, self.W = s, CAJA0, 0, M, CAJA0

    def paso(self, p):
        d = self.d
        if d:
            a = d >> 6
            if a == 1:
                q = d & 63
                t = (self.caja - COMISION) // p
                if q > t:
                    q = t
                if q > 0:
                    self.caja -= q * p + COMISION
                    self.acc += q
            elif a == 2:
                q = d & 63
                if q > self.acc:
                    q = self.acc
                if q > 0 and self.caja + q * p >= COMISION:
                    self.caja += q * p - COMISION
                    self.acc -= q
        self.W = self.caja + self.acc * p
        self.d = self.s.decidir(p, self.caja, self.acc)


# --------------------------------------------------------------------------------------------
# Regla con fases y comportamientos para la fase D

class Regla:
    """Fases A, B y C de la regla de los peldaños; la fase D la decide el comportamiento B.
    obs(regla, p), si existe, se llama en cada tick en todas las fases (indicadores en vivo)."""

    def __init__(self, B, obs=None):
        self.B = B
        self.obs = obs if obs is not None else getattr(B, "obs", None)
        self.vlo = self.vhi = False
        self.q = M
        self.n = -1
        self.tD = -1

    def resta(self):
        """Ticks que quedan por ejecutar después de esta decisión."""
        return LARGO - 1 - self.n

    def decidir(self, p, caja, acc):
        self.n += 1
        if self.obs is not None:
            self.obs(self, p)
        if self.tD >= 0:
            return self.B.d(self, p, caja, acc)
        if p <= LO:
            self.vlo = True
            self.q = C
        elif p >= HI:
            self.vhi = True
            self.q = V
        else:
            return self.q
        if self.vlo and self.vhi:
            self.tD = self.n
            return self.B.entra(self, p, caja, acc)
        return self.q

    def info(self):
        i = getattr(self.B, "info", None)
        return (self.tD,) + (i() if i else ())


class Comp:
    """Comportamiento de la fase D. entra() se llama en el tick que completa los dos extremos."""

    def entra(self, r, p, caja, acc):
        return self.d(r, p, caja, acc)

    def d(self, r, p, caja, acc):
        return r.q


class BandaD(Comp):
    """Compra 63 con p <= c, vende 63 con p >= v (banda w: c = 100 + w, v = 255 - w)."""

    def __init__(self, c, v):
        self.c, self.v = c, v
        self.nivel_venta = v

    def d(self, r, p, caja, acc):
        if p <= self.c:
            r.q = C
        elif p >= self.v:
            r.q = V
        return r.q


def banda(w):
    return BandaD(LO + w, HI - w)


class NoVuelveD(Comp):
    """Vende con p >= H y no vuelve a entrar (el rival de Tesla en la fase D)."""

    def __init__(self, H=220):
        self.H = H
        self.fin = False
        self.nivel_venta = H

    def d(self, r, p, caja, acc):
        if self.fin:
            return V
        if p >= self.H or (acc == 0 and r.q != C):
            self.fin = True
            r.q = V
        return r.q


class TresBandasD(Comp):
    """Tres bandas por hilo: cada una lleva un tercio del patrimonio, con histéresis propia."""

    def __init__(self, niveles=((120, 155), (150, 185), (180, 215))):
        self.niv = niveles
        self.est = [False] * len(niveles)
        self.obj = None
        self.nivel_venta = max(v for _, v in niveles)

    def _obj(self, p, caja, acc):
        k, n = sum(self.est), len(self.est)
        self.obj = C if k == n else V if k == 0 else (k * (caja + acc * p)) // (n * p)

    def entra(self, r, p, caja, acc):
        self.est = [p <= c for c, _ in self.niv]
        self._obj(p, caja, acc)
        return self.d(r, p, caja, acc)

    def d(self, r, p, caja, acc):
        est, cambio = self.est, False
        for i, (c, v) in enumerate(self.niv):
            if not est[i]:
                if p <= c:
                    est[i] = cambio = True
            elif p >= v:
                est[i] = False
                cambio = True
        if cambio:
            self._obj(p, caja, acc)
        o = self.obj
        return o if o == C or o == V else hacia(o, acc)


class GrillaD(Comp):
    """Idea 2. N niveles iguales entre Linf y Lsup: el tramo j se compra con p <= b_j y se vende
    con p >= b_j + paso (histéresis de un escalón); bajo Linf todo invertido, sobre Lsup nada.
    Tamaño del tramo: 'fraccion' (patrimonio / (N p) al comprar) o 'fijas' (acciones fijas,
    patrimonio al entrar a D dividido por la suma de los niveles de compra: todos los tramos
    caben en la caja). Una sola orden neta por tick, de hasta 63."""

    def __init__(self, N=4, Linf=100, Lsup=255, modo="fraccion"):
        paso = (Lsup - Linf) / N
        self.b = [int(round(Lsup - (j + 1) * paso)) for j in range(N)]
        self.s = [int(round(Lsup - j * paso)) for j in range(N)]
        self.N, self.modo = N, modo
        self.held = [0] * N
        self.obj = 0
        self.fijo = 0
        self.vueltas = 0
        self.nivel_venta = self.s[-1]

    def entra(self, r, p, caja, acc):
        if self.modo == "fijas":
            self.fijo = max(1, (caja + acc * p - COMISION * self.N) // sum(self.b))
        return self.d(r, p, caja, acc)

    def d(self, r, p, caja, acc):
        held = self.held
        for j in range(self.N):
            if held[j]:
                if p >= self.s[j]:
                    self.obj -= held[j]
                    held[j] = 0
                    self.vueltas += 1
            elif p <= self.b[j]:
                sh = self.fijo if self.modo == "fijas" else (caja + acc * p) // (self.N * p)
                held[j] = sh if sh > 0 else 1
                self.obj += held[j]
        if self.obj <= 0:
            return V
        return hacia(self.obj, acc)

    def info(self):
        return (self.vueltas,)




# --------------------------------------------------------------------------------------------
# Cuentas virtuales y rivales emulados (ideas 3 y 7)

class Siempre:
    """Comprar y mantener: compra 63 en cada tick hasta gastar la caja (como 'siempre' en C)."""

    def decidir(self, p, caja, acc):
        return C


class UnaVezR:
    """El rival de Tesla (planb.UnaVez) con la interfaz del motor."""

    def __init__(self, L=100, H=220):
        self.L, self.H, self.estado, self.q = L, H, 0, M

    def decidir(self, p, caja, acc):
        if self.estado == 0 and p <= self.L:
            self.estado, self.q = 1, C
        elif self.estado == 1 and p >= self.H:
            self.estado, self.q = 2, V
        return self.q


class RangoR:
    """Banda simple sin fases: compra con p <= L, vende con p >= H, parte en caja."""

    def __init__(self, L=140, H=215):
        self.L, self.H, self.q = L, H, M

    def decidir(self, p, caja, acc):
        if p <= self.L:
            self.q = C
        elif p >= self.H:
            self.q = V
        return self.q


def fraccion_siguiente(c, p):
    """Fracción invertida de la cuenta después de ejecutar su orden pendiente al precio p."""
    acc, caja, d = c.acc, c.caja, c.d
    a = d >> 6
    if a == 1:
        q = min(d & 63, (caja - COMISION) // p)
        if q > 0:
            acc += q
            caja -= q * p + COMISION
    elif a == 2:
        q = min(d & 63, acc)
        if q > 0:
            acc -= q
            caja += q * p - COMISION
    W = caja + acc * p
    return acc * p / W if W > 0 else 0.0


def objetivo_fraccion(f, p, caja, acc):
    """Orden hacia una fracción invertida f del patrimonio propio."""
    if f >= 0.97:
        return C
    if f <= 0.03:
        return V
    return hacia(int(f * (caja + acc * p) / p), acc)


def cuenta_spec(sp):
    """Especificación de una cuenta virtual: ('regla', bspec) | ('siempre',) | ('unavez', L, H) | ('rango', L, H)."""
    if sp[0] == "regla":
        return Regla(comp(sp[1]))
    if sp[0] == "siempre":
        return Siempre()
    if sp[0] == "unavez":
        return UnaVezR(sp[1], sp[2])
    if sp[0] == "rango":
        return RangoR(sp[1], sp[2])
    raise ValueError(sp)


# --------------------------------------------------------------------------------------------
# Idea 1: política por programación dinámica (tablas de ideas_dp.py)

class DPD(Comp):
    """Umbrales a y b por tramo de tiempo restante y clase de volatilidad. La clase sale de q,
    la fracción de ticks con cambio vista hasta ahora (modo 'cambios'), o del cuadrado medio del
    cambio (modo 'varianza'). tabla[clase][tramo] = (a, b); cortes de clase en q."""

    def __init__(self, tabla, cortes, tramos, modo="cambios"):
        self.tabla, self.cortes, self.tramos, self.modo = tabla, cortes, tramos, modo
        self.prev = None
        self.nc = 0
        self.s2 = 0
        self.nivel_venta = 215

    def obs(self, r, p):
        if self.prev is not None and p != self.prev:
            self.nc += 1
            self.s2 += (p - self.prev) * (p - self.prev)
        self.prev = p

    def d(self, r, p, caja, acc):
        n = r.n if r.n > 0 else 1
        x = (self.nc if self.modo == "cambios" else min(self.s2, n)) / n
        cl = 0
        for c in self.cortes:
            if x > c:
                cl += 1
        tr = (r.resta() * self.tramos) // LARGO
        a, b = self.tabla[cl][tr if tr < self.tramos else self.tramos - 1]
        self.nivel_venta = b
        if p <= a:
            r.q = C
        elif p >= b:
            r.q = V
        return r.q


# --------------------------------------------------------------------------------------------
# Idea 3: torneo en sombra

class SombraD(Comp):
    """Cuentas virtuales exactas desde el tick 0. En la fase D, cada R ticks se ordena por
    patrimonio virtual; el capital real copia la posición de la seguida y cambia de seguida solo
    si la líder la supera por un margen Mg. modo 'lider' o 'tercios' (las 3 mejores, un tercio
    cada una). Al entrar a D se sigue a la cuenta inicial (la banda 40)."""

    def __init__(self, cuentas, R=390, Mg=1 / 32, modo="lider", inicial=0):
        self.cuentas = [Cuenta(cuenta_spec(sp)) for sp in cuentas]
        self.R, self.Mg, self.modo, self.inicial = R, Mg, modo, inicial
        self.seg = []
        self.f = None
        self.cambios = 0
        self.ord_cambio = 0
        self.convergiendo = False
        self.nivel_venta = 215

    def obs(self, r, p):
        for c in self.cuentas:
            c.paso(p)

    def _ordenar(self):
        return sorted(range(len(self.cuentas)), key=lambda i: -self.cuentas[i].W)

    def entra(self, r, p, caja, acc):
        if self.modo == "lider":
            self.seg = [self.inicial]
        else:
            self.seg = self._ordenar()[:3]
        return self.d(r, p, caja, acc)

    def d(self, r, p, caja, acc):
        cs = self.cuentas
        if (r.n - r.tD) % self.R == 0 and r.n > r.tD:
            orden = self._ordenar()
            if self.modo == "lider":
                lider, s0 = orden[0], self.seg[0]
                if lider != s0 and cs[lider].W > cs[s0].W * (1 + self.Mg):
                    self.seg = [lider]
                    self.cambios += 1
                    self.convergiendo = True
            else:
                nuevo = list(self.seg)
                for i in orden[:3]:
                    if i in nuevo:
                        continue
                    peor = min(nuevo, key=lambda j: cs[j].W)
                    if cs[i].W > cs[peor].W * (1 + self.Mg):
                        nuevo[nuevo.index(peor)] = i
                        self.cambios += 1
                        self.convergiendo = True
                self.seg = nuevo
        f = sum(fraccion_siguiente(cs[i], p) for i in self.seg) / len(self.seg)
        if self.f is None or abs(f - self.f) > 0.05:
            self.f = f
        o = objetivo_fraccion(self.f, p, caja, acc)
        if self.convergiendo:
            if o == M or (o == C and (caja - COMISION) // p <= 0) or (o == V and acc == 0):
                self.convergiendo = False
            else:
                self.ord_cambio += 1
        return o

    def info(self):
        return (self.cambios, self.ord_cambio)


class SondaSombra:
    """Filtro de la idea 3: patrimonio de cada cuenta virtual a mitad de ventana (tick 9 999), al
    final y, para la variante dentro de D, en el inicio y la mitad de la fase D."""

    def __init__(self, cuentas):
        self.cuentas = [Cuenta(cuenta_spec(sp)) for sp in cuentas]
        self.fases = Regla(Comp())
        self.mitad = None
        self.d0 = None
        self.n = -1

    def decidir(self, p, caja, acc):
        self.n += 1
        self.fases.decidir(p, 0, 0)
        for c in self.cuentas:
            c.paso(p)
        if self.n == LARGO // 2 - 1:
            self.mitad = [c.W for c in self.cuentas]
        if self.fases.tD == self.n:
            self.d0 = [c.W for c in self.cuentas]
        tD = self.fases.tD
        if tD >= 0 and self.n == tD + (LARGO - 1 - tD) // 2:
            self.dm = [c.W for c in self.cuentas]
        return M

    def info(self):
        fin = [c.W for c in self.cuentas]
        return (self.fases.tD, self.mitad, fin, self.d0, getattr(self, "dm", None))


# --------------------------------------------------------------------------------------------
# Idea 4: detector de régimen

class Indicadores:
    """Indicadores en vivo desde el tick 0: sumas de la razón de varianzas para k en (16, 64, 390),
    cruces del nivel 177 y ticks desde el último extremo nuevo (máximo o mínimo corrido).
    solo = índice en IND del único indicador que se necesita (None: todos, para el filtro)."""

    KS = (16, 64, 390)

    def __init__(self, solo=None):
        self.solo = solo
        self.ks = [j for j in range(3) if solo is None or solo == j]
        self.anillos = {j: collections.deque(maxlen=self.KS[j]) for j in self.ks}
        self.cr = solo is None or solo == 3
        self.ex = solo is None or solo == 4
        self.prev = None
        self.s1 = 0
        self.sk = [0, 0, 0]
        self.lado = 0
        self.cruces = 0
        self.mx = self.mn = None
        self.desde = 0
        self.desde_prev = 0

    def paso(self, p):
        if self.prev is not None:
            d = p - self.prev
            self.s1 += d * d
        for j in self.ks:
            a = self.anillos[j]
            if len(a) == self.KS[j]:
                e = p - a[0]
                self.sk[j] += e * e
            a.append(p)
        self.prev = p
        if self.cr:
            lado = 1 if p > 177 else -1 if p < 177 else self.lado
            if self.lado and lado != self.lado:
                self.cruces += 1
            self.lado = lado
        if self.ex:
            if self.mx is None:
                self.mx = self.mn = p
            elif p > self.mx or p < self.mn:
                self.mx, self.mn = max(self.mx, p), min(self.mn, p)
                self.desde_prev, self.desde = self.desde, 0
            else:
                self.desde += 1

    def valores(self, n):
        """vr16, vr64, vr390, cruces por 1000 ticks, ticks desde el extremo anterior."""
        s1 = self.s1 if self.s1 > 0 else 1
        vr = [self.sk[j] / (k * s1) for j, k in enumerate(self.KS)]
        return tuple(vr) + (1000.0 * self.cruces / max(1, n), self.desde_prev)


IND = ("vr16", "vr64", "vr390", "cruces", "desde")


class RegimenD(Comp):
    """Al entrar a D elige por el indicador: oscilador (comportamiento osc), tendencia (vende con
    220 o más y no vuelve) o banda 40. sentido +1: indicador alto = tendencia (razón de varianzas);
    sentido -1: indicador bajo = tendencia (cruces, ticks desde el extremo)."""

    def __init__(self, ind="vr64", u1=0.85, u2=1.15, sentido=1, osc=("banda", {"w": 60}), medio=("banda", {"w": 40})):
        self.ind, self.u1, self.u2, self.sentido = IND.index(ind), u1, u2, sentido
        self.osc_spec, self.medio_spec = osc, medio
        self.I = Indicadores(self.ind)
        self.B = None
        self.modo = None
        self.valor = None
        self.nivel_venta = 215

    def obs(self, r, p):
        if self.B is None:
            self.I.paso(p)
        elif hasattr(self.B, "obs"):
            self.B.obs(r, p)

    def entra(self, r, p, caja, acc):
        x = self.I.valores(r.n)[self.ind] * self.sentido
        self.valor = x
        u1, u2 = (self.u1, self.u2) if self.sentido > 0 else (-self.u2, -self.u1)
        if x < u1:
            self.modo, self.B = 0, comp(self.osc_spec)
        elif x > u2:
            self.modo, self.B = 2, NoVuelveD(220)
        else:
            self.modo, self.B = 1, comp(self.medio_spec)
        self.nivel_venta = getattr(self.B, "nivel_venta", 215)
        return self.B.entra(r, p, caja, acc)

    def d(self, r, p, caja, acc):
        return self.B.d(r, p, caja, acc)

    def info(self):
        return (self.modo,)


class SondaRegimen(Regla):
    """Filtro de la idea 4: banda 40 que además anota los indicadores al entrar a D."""

    def __init__(self):
        super().__init__(banda(40))
        self.I = Indicadores()
        self.val = None
        self.obs = self._obs

    @staticmethod
    def _obs(r, p):
        if r.tD < 0:
            r.I.paso(p)

    def decidir(self, p, caja, acc):
        q = super().decidir(p, caja, acc)
        if self.tD == self.n and self.val is None:
            self.val = self.I.valores(self.n)
        return q

    def info(self):
        return (self.tD, self.val)


# --------------------------------------------------------------------------------------------
# Idea 5: bandas por cuantiles

class CuantilD(Comp):
    """Histograma de 156 contadores con el tiempo en cada nivel; un puntero por cuantil que se
    mueve a lo más un nivel por tick. origen 'inicio' (desde el tick 0), 'D' (desde la entrada a
    D) u 'olvido' (desde el tick 0, todo dividido por 2 cada 4096 ticks). Compra con p <= puntero
    de qc, vende con p >= puntero de qv, separación mínima de 10 niveles. Antes de 'calor' ticks
    de histograma opera la banda 40."""

    def __init__(self, qc=0.25, qv=0.75, origen="inicio", calor=1950, sep=10):
        self.qc, self.qv, self.origen, self.calor, self.sep = qc, qv, origen, calor, sep
        self.h = [0] * 156
        self.T = 0
        self.P = [None, None]
        self.cum = [0, 0]
        self.q = (qc, qv)
        self.n0 = 0
        self.suma_ancho = 0
        self.n_activo = 0
        self.nivel_venta = 215

    def _agregar(self, x):
        h = self.h
        h[x] += 1
        self.T += 1
        P, cum = self.P, self.cum
        for j in (0, 1):
            if P[j] is None:
                P[j] = x
                cum[j] = h[x]
                continue
            if x <= P[j]:
                cum[j] += 1
            f = self.q[j] * self.T
            if cum[j] < f and P[j] < 155:
                P[j] += 1
                cum[j] += h[P[j]]
            elif cum[j] - h[P[j]] >= f and P[j] > 0:
                cum[j] -= h[P[j]]
                P[j] -= 1

    def _olvidar(self):
        h = self.h
        for i in range(156):
            h[i] >>= 1
        self.T = sum(h)
        for j in (0, 1):
            if self.P[j] is not None:
                self.cum[j] = sum(h[:self.P[j] + 1])

    def obs(self, r, p):
        if self.origen == "D" and r.tD < 0:
            return
        self._agregar(p - LO)
        if self.origen == "olvido" and r.n > 0 and r.n % 4096 == 0:
            self._olvidar()

    def entra(self, r, p, caja, acc):
        self.n0 = r.n
        return self.d(r, p, caja, acc)

    def d(self, r, p, caja, acc):
        hechos = r.n - self.n0 if self.origen == "D" else r.n
        if hechos < self.calor:
            c, v = LO + 40, HI - 40
        else:
            c, v = self.P[0] + LO, self.P[1] + LO
            if v - c < self.sep:
                m = (c + v) // 2
                c, v = m - self.sep // 2, m + self.sep - self.sep // 2
            self.suma_ancho += v - c
            self.n_activo += 1
        self.nivel_venta = v
        if p <= c:
            r.q = C
        elif p >= v:
            r.q = V
        return r.q

    def info(self):
        return (self.suma_ancho, self.n_activo)


# --------------------------------------------------------------------------------------------
# Idea 6: predictor de contadores saturados

class ContadoresD(Comp):
    """Símbolo por tick (baja 0, igual 1, sube 2); índice: los últimos h símbolos (2 bits cada uno),
    o eso con XOR de los bits bajos del precio. Tabla de contadores de 2 bits desde el tick 0. El
    contador del índice de hace dos ticks se entrena con el símbolo actual (con información hasta
    n la orden se ejecuta a p(n+1) y se sale recién a p(n+2)). En D: con el contador en 3 se
    mantienen 63 acciones, con el contador en 0 se sale; anota el cambio de precio que siguió a
    cada decisión con contador saturado (filtro)."""

    def __init__(self, h=4, xor=False):
        self.h, self.xor = h, xor
        self.mask = (1 << (2 * h)) - 1
        self.t = [1] * (1 << (2 * h))
        self.hb = 0
        self.prev = None
        self.idx = [None, None]          # índice de n-1 y de n-2
        self.pend = []                   # (tick de la decisión, signo del contador)
        self.suma = [0, 0]
        self.cuenta = [0, 0]
        self.p_hist = []
        self.nivel_venta = 215
        self.obj = 0

    def obs(self, r, p):
        if self.prev is not None:
            s = 0 if p < self.prev else 1 if p == self.prev else 2
            i2 = self.idx[1]
            if i2 is not None:
                c = self.t[i2]
                if s == 2 and c < 3:
                    self.t[i2] = c + 1
                elif s == 0 and c > 0:
                    self.t[i2] = c - 1
            self.hb = ((self.hb << 2) | s) & self.mask
        self.prev = p
        i = self.hb ^ (p & self.mask) if self.xor else self.hb
        self.idx = [i, self.idx[0]]
        if r.tD >= 0:
            ph = self.p_hist
            ph.append(p)
            # la decisión del tick n se ejecuta a p(n+1); el cambio que cuenta es p(n+2) - p(n+1)
            while self.pend and self.pend[0][0] + 2 <= r.n:
                t0, sg = self.pend.pop(0)
                k = len(ph) - 1 - (r.n - (t0 + 2))
                dlt = ph[k] - ph[k - 1]
                self.suma[sg] += dlt
                self.cuenta[sg] += 1

    def d(self, r, p, caja, acc):
        c = self.t[self.idx[0]]
        if c == 3:
            self.obj = 63
            self.pend.append((r.n, 0))
        elif c == 0:
            self.obj = 0
            self.pend.append((r.n, 1))
        return hacia(self.obj, acc) if self.obj or acc else V

    def info(self):
        return (self.suma[0], self.cuenta[0], self.suma[1], self.cuenta[1])


# --------------------------------------------------------------------------------------------
# Idea 7: cobertura contra rivales emulados

class CoberturaD(Comp):
    """Cuentas virtuales exactas del rival de Tesla, de comprar y mantener y de una banda simple
    (140/215 sin fases). En D, si quedan menos de Tc ticks y el patrimonio propio supera al mejor
    rival virtual por un margen m (en %), se copia su posición; si no, el comportamiento base."""

    def __init__(self, base=("banda", {"w": 40}), m=5, Tc=5000,
                 rivales=(("unavez", 100, 220), ("siempre",), ("rango", 140, 215))):
        self.B = comp(base)
        self.m, self.Tc = m, Tc
        self.cuentas = [Cuenta(cuenta_spec(sp)) for sp in rivales]
        self.copias = 0
        self.copiando = False
        self.nivel_venta = getattr(self.B, "nivel_venta", 215)

    def obs(self, r, p):
        for c in self.cuentas:
            c.paso(p)
        if hasattr(self.B, "obs"):
            self.B.obs(r, p)

    def entra(self, r, p, caja, acc):
        o = self.B.entra(r, p, caja, acc)
        return self._cubrir(r, p, caja, acc, o)

    def d(self, r, p, caja, acc):
        return self._cubrir(r, p, caja, acc, self.B.d(r, p, caja, acc))

    def _cubrir(self, r, p, caja, acc, o):
        if r.resta() < self.Tc:
            mejor = max(self.cuentas, key=lambda c: c.W)
            if (caja + acc * p) * 100 >= (100 + self.m) * mejor.W:
                if not self.copiando:
                    self.copias += 1
                    self.copiando = True
                return C if fraccion_siguiente(mejor, p) > 0.5 else V
        self.copiando = False
        return o

    def info(self):
        return (self.copias,)


# --------------------------------------------------------------------------------------------
# Idea 8: final de ronda

class FinalD(Comp):
    """Envoltura del final de ronda sobre cualquier comportamiento de D, en los últimos Tf ticks.
    'a': sin compras nuevas (si no hay posición, no entra; incluye la compra al ver 100 después de
    255, que lleva a D). 'b': el nivel de venta baja en línea recta desde el del comportamiento
    hasta el precio de entrada. 'c': vende apenas el precio está sobre el de entrada y no vuelve a
    comprar."""

    def __init__(self, base=("banda", {"w": 40}), var="a", Tf=1000):
        self.B = comp(base)
        self.var, self.Tf = var, Tf
        self.e = None
        self.acc_prev = 0
        self.cerrado = False
        self.nivel_venta = getattr(self.B, "nivel_venta", 215)

    @property
    def obs(self):
        return getattr(self.B, "obs", None)

    def entra(self, r, p, caja, acc):
        return self._final(r, p, caja, acc, self.B.entra(r, p, caja, acc))

    def d(self, r, p, caja, acc):
        return self._final(r, p, caja, acc, self.B.d(r, p, caja, acc))

    def _final(self, r, p, caja, acc, o):
        if acc > 0 and self.acc_prev == 0:
            self.e = p
        self.acc_prev = acc
        resta = r.resta()
        if resta > self.Tf:
            return o
        compra = (o >> 6) == 1
        if self.var == "a":
            if compra and acc == 0:
                return V
            return o
        if self.var == "b":
            if acc > 0 and self.e is not None:
                v0 = getattr(self.B, "nivel_venta", 215)
                nivel = self.e + ((v0 - self.e) * resta) // self.Tf
                if p >= nivel:
                    r.q = V
                    return V
            return o
        # 'c'
        if self.cerrado:
            return V
        if acc > 0 and self.e is not None and p > self.e:
            self.cerrado = True
            r.q = V
            return V
        if compra and acc == 0:
            return V
        return o


# --------------------------------------------------------------------------------------------
# Idea 9: decisión según el precio inicial

class InicioRegla(Regla):
    """En la fase A: si el primer precio es >= u (o, con T > 0, si p(T) - p(0) >= u en el tick T),
    compra una fracción f del patrimonio; después la regla de siempre (vende al ver 255 y espera el
    100; si llega primero el 100, completa la compra y espera el 255). Fase D: banda w."""

    def __init__(self, u=200, f=1.0, T=0, w=40):
        super().__init__(banda(w))
        self.u, self.f, self.T = u, f, T
        self.p0 = None
        self.obj = None

    def decidir(self, p, caja, acc):
        if self.p0 is None:
            self.p0 = p
        if self.tD < 0 and not self.vlo and not self.vhi and LO < p < HI:
            self.n += 1
            if self.obj is None and self.n == self.T:
                x = p if self.T == 0 else p - self.p0
                if x >= self.u:
                    self.obj = C if self.f >= 1 else int(self.f * (caja + acc * p)) // p
                else:
                    self.obj = 0
            if self.obj:
                return C if self.obj == C else hacia(self.obj, acc)
            return self.q
        return super().decidir(p, caja, acc)


# --------------------------------------------------------------------------------------------
# Idea 10: salida por caída desde el máximo

class CaidaD(Comp):
    """Sobre la banda w: tras comprar se guarda el máximo desde la entrada; se vende si el precio
    cae d niveles desde ese máximo, siempre que el máximo esté al menos g sobre la entrada.
    Reentrada 'banda' (el nivel de compra de la banda) o 'rebote' (subida de d desde el mínimo
    posterior a la venta, o el nivel de la banda, lo que llegue primero)."""

    def __init__(self, w=40, dd=15, g=40, reentrada="banda"):
        self.c, self.v = LO + w, HI - w
        self.dd, self.g, self.re = dd, g, reentrada
        self.e = None
        self.mx = 0
        self.acc_prev = 0
        self.parado = False
        self.mn = 0
        self.paradas = 0
        self.nivel_venta = self.v

    def d(self, r, p, caja, acc):
        if acc > 0 and self.acc_prev == 0:
            self.e, self.mx = p, p
        self.acc_prev = acc
        if self.parado:
            if p < self.mn:
                self.mn = p
            if p <= self.c or (self.re == "rebote" and p >= self.mn + self.dd):
                self.parado = False
                r.q = C
            return r.q
        if acc > 0 and self.e is not None:
            if p > self.mx:
                self.mx = p
            if self.mx >= self.e + self.g and p <= self.mx - self.dd and r.q == C:
                self.parado = True
                self.paradas += 1
                self.mn = p
                r.q = V
                return V
        if p <= self.c:
            r.q = C
        elif p >= self.v:
            r.q = V
        return r.q

    def info(self):
        return (self.paradas,)


# --------------------------------------------------------------------------------------------
# Catálogo: especificación (tipo, parámetros) -> comportamiento o estrategia nueva

def comp(spec):
    tipo, kw = spec
    return COMPS[tipo](**kw)


def _banda_ancho(ancho, centro):
    return BandaD(centro - ancho // 2, centro + ancho - ancho // 2)


def _dp(**kw):
    import ideas_dp
    return ideas_dp.comportamiento(**kw)


COMPS = {
    "banda": lambda w: banda(w),
    "bandac": _banda_ancho,
    "tres": lambda niveles=((120, 155), (150, 185), (180, 215)): TresBandasD(niveles),
    "grilla": lambda N, Linf, Lsup, modo="fraccion": GrillaD(N, Linf, Lsup, modo),
    "novuelve": lambda H=220: NoVuelveD(H),
    "dp": _dp,
    "sombra": lambda **kw: SombraD(**kw),
    "regimen": lambda **kw: RegimenD(**kw),
    "cuantil": lambda **kw: CuantilD(**kw),
    "contadores": lambda **kw: ContadoresD(**kw),
    "cobertura": lambda **kw: CoberturaD(**kw),
    "final": lambda **kw: FinalD(**kw),
    "caida": lambda **kw: CaidaD(**kw),
}


def crear(spec):
    """('regla', bspec) -> Regla(comp(bspec)); ('inicio', kw) -> InicioRegla; ('sonda_sombra', kw);
    ('sonda_regimen', {}); y por comodidad cualquier bspec suelto se envuelve en una Regla."""
    tipo, kw = spec
    if tipo == "regla":
        return Regla(comp(kw))
    if tipo == "inicio":
        return InicioRegla(**kw)
    if tipo == "sonda_sombra":
        return SondaSombra(**kw)
    if tipo == "sonda_regimen":
        return SondaRegimen()
    return Regla(comp(spec))
