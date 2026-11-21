#!/usr/bin/env python3
"""v5.py: banco de pruebas de V5 (docs/exploracion_ideas.md, sección 15).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Tres piezas, todas tick a tick (sin saltos por eventos) y con la contabilidad oficial de ideas.correr:

  rivales        trayectoria densa (caja, acciones, byte) de cada rival del pronóstico:
                 ext  extremos puros: compra 63 repetido desde el primer 100, vende al ver 255 ya comprado
                      y no vuelve (unavez 100 255);
                 f5   Fila 5, el rival de Tesla: lo mismo con venta en 220 o más (unavez 100 220);
                 b30, b40, b50, b60  la regla de los peldaños con banda 30, 40, 50 y 60.
  fase_a         la fase A de V3 con (b) reescrita con opciones (umbral de probabilidad, tamaño, clase,
                 tiempo). Con las opciones por omisión da el mismo estado que optimo_estrategia.Optima.
  post           desde el primer extremo: máquina de modos de V4b (recuperación, candado "copiar") con
                 opciones nuevas (motores, freno por rendimiento del clon, M según el tiempo, audacia al
                 final, niveles propios en la fase D, varios rivales emulados).

Tiempo de la decisión, como en ideas.correr: en el tick n se ejecuta la orden pendiente a p(n), se
valoriza y se decide con lo visto hasta p(n); la decisión se ejecuta a p(n + 1). Nada de lo que decide
en n usa precios posteriores a n (explorar_v5.py causal lo comprueba cambiando el futuro).
"""
import array
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ideas                    # noqa: E402
import optimo_estrategia as OE  # noqa: E402
import paseo_optimo as P        # noqa: E402

M_, C_, V_ = ideas.M, ideas.C, ideas.V
LO, HI = ideas.LO, ideas.HI
N = ideas.LARGO
CAJA0, COM = ideas.CAJA0, ideas.COMISION
INF = 10 ** 12

RIVALES = ("ext", "f5", "b30", "b50", "b60", "b40")
# Pronóstico de Nicolás (20/11): 60 % extremos o Fila 5 (repartido aquí en mitades), 30 % una banda
# parecida (30, 50 o 60, parejo) y 10 % la banda 40 exacta.
PESOS = {"ext": 0.30, "f5": 0.30, "b30": 0.10, "b50": 0.10, "b60": 0.10, "b40": 0.10}
BANDAS = {"b30": 30, "b40": 40, "b50": 50, "b60": 60}
V3B = ("optima", {"variante": "V3", "objetivo": "log", "estimador": "S2/t", "comprimida": True, "placa": True,
                  "guarda": (0, True, False)})
V2SPEC = OE.spec("V2", "log", "S2/t")


# --- rivales -------------------------------------------------------------------------------------

def _cuenta(w, dec):
    """Corre una regla dec(p) -> byte con la contabilidad oficial. Devuelve listas densas (caja, acc, d)
    con el estado después de ejecutar en cada tick y la decisión de ese tick."""
    n = len(w)
    ca, ac, dl = [0] * n, [0] * n, [0] * n
    caja, acc, d = CAJA0, 0, M_
    for i, p in enumerate(w):
        if d:
            if d == C_:
                q = (caja - COM) // p
                if q > 63:
                    q = 63
                if q > 0:
                    caja -= q * p + COM
                    acc += q
            elif acc > 0:
                q = acc if acc < 63 else 63
                caja += q * p - COM
                acc -= q
        d = dec(p)
        ca[i], ac[i], dl[i] = caja, acc, d
    return ca, ac, dl


def _dec_banda(c, v):
    """La regla de los peldaños (fases A a C de ideas.Regla) con banda de compra c y venta v en D."""
    st = [False, False, M_]

    def dec(p):
        if st[0] and st[1]:
            if p <= c:
                st[2] = C_
            elif p >= v:
                st[2] = V_
        elif p <= LO:
            st[0] = True
            st[2] = C_
        elif p >= HI:
            st[1] = True
            st[2] = V_
        return st[2]
    return dec


def _dec_unavez(L, H):
    st = [0, M_]

    def dec(p):
        if st[0] == 0:
            if p <= L:
                st[0], st[1] = 1, C_
        elif st[0] == 1 and p >= H:
            st[0], st[1] = 2, V_
        return st[1]
    return dec


def rival(w, nombre):
    if nombre in BANDAS:
        return _cuenta(w, _dec_banda(LO + BANDAS[nombre], HI - BANDAS[nombre]))
    if nombre == "ext":
        return _cuenta(w, _dec_unavez(LO, HI))
    if nombre == "f5":
        return _cuenta(w, _dec_unavez(LO, 220))
    if nombre.startswith("banda:"):
        _, c, v = nombre.split(":")
        return _cuenta(w, _dec_banda(int(c), int(v)))
    raise ValueError(nombre)


# --- precálculo por ventana ----------------------------------------------------------------------

def precalcular(w):
    """Lo que comparten todas las variantes de una ventana: ticks de los extremos, clase de v^2 de placa
    por tick en la fase A (como eventos), estado de la base V3 con (b) al primer extremo (control), y los
    bytes de V2 desde el primer extremo (como eventos)."""
    t100, t255 = w.find(bytes([LO])), w.find(bytes([HI]))
    tA = min(t100, t255)
    # base V3 con (b) hasta el primer extremo, con optimo_estrategia.Optima (la referencia)
    s = ideas.crear(V3B)
    caja, acc, d, nord = CAJA0, 0, M_, 0
    aposto = False
    cv_ev = []
    cv = -2
    dec = s.decidir
    for i in range(tA + 1):
        p = w[i]
        caja, acc, h = _ejec(d, p, caja, acc)
        nord += h
        if acc > 0:
            aposto = True
        d = dec(p, caja, acc)
        if s.cv != cv:
            cv = s.cv
            cv_ev.append((i, cv))
    base = (caja, acc, nord, aposto)
    # V2 completa: sus bytes no dependen de la cuenta (dos posiciones)
    s2 = ideas.crear(V2SPEC)
    dec2 = s2.decidir
    v2ev = []
    prev = None
    for i, p in enumerate(w):
        b = dec2(p, CAJA0, 0)
        if i >= tA and b != prev:
            v2ev.append((i, b))
            prev = b
    return dict(t100=t100, t255=t255, tA=tA, base=base, cv=cv_ev, v2=v2ev)


V2C = OE.spec("V2", "log", "S2/t", comprimida=True, placa=True)


_COMP_T = {}


def comprimida_tramos(tramos, objetivo="log"):
    """V2 comprimida con otro número de tramos de tiempo (16 es la de optimo_estrategia)."""
    if (tramos, objetivo) not in _COMP_T:
        t0, l0 = OE.TRAMOS, OE.LARGO_TRAMO
        OE.TRAMOS, OE.LARGO_TRAMO = tramos, P.N // tramos
        try:
            c = OE.Comprimida("V2", objetivo)
        finally:
            OE.TRAMOS, OE.LARGO_TRAMO = t0, l0
        cel, lt = c.cel, P.N // tramos

        def decide(F, j, r, p, s):
            alto, bajo, salida, bajo1 = cel[(F, j, min(tramos - 1, r // lt))]
            if s == 0:
                return 1 if (p >= alto or p <= bajo) else 0
            return 1 if (p >= salida or p <= bajo1) else 0
        c.decide = decide
        _COMP_T[(tramos, objetivo)] = c
    return _COMP_T[(tramos, objetivo)]


def precalcular_v2c(w, tA, tramos=16, objetivo="log"):
    """Bytes del motor de placa desde el primer extremo (eventos): V2 comprimida (4 bytes por celda de
    clase y tramo en cada fase), clase de v^2 de placa con histéresis, y sin fase A: hasta el primer
    extremo no decide nada y su posición interna es 0, que es lo que puede hacer un programa que no
    apuesta en la fase A."""
    if tramos == 16 and objetivo == "log":
        s = ideas.crear(V2C)
    else:
        s = OE.Optima(variante="V2", objetivo=objetivo, estimador="S2/t", comprimida=comprimida_tramos(tramos, objetivo), placa=True)
    s.opt = ("B", "C", "D")
    dec = s.decidir
    ev = []
    prev = None
    for i, p in enumerate(w):
        b = dec(p, CAJA0, 0)
        if i >= tA and b != prev:
            ev.append((i, b))
            prev = b
    return ev


def _ejec(d, p, caja, acc):
    """Contabilidad oficial para un byte d cualquiera (cantidad de 0 a 63)."""
    if d:
        a = d >> 6
        if a == 1:
            q = d & 63
            t = (caja - COM) // p
            if q > t:
                q = t
            if q > 0:
                return caja - q * p - COM, acc + q, 1
        elif a == 2:
            q = d & 63
            if q > acc:
                q = acc
            if q > 0 and caja + q * p >= COM:
                return caja + q * p - COM, acc - q, 1
    return caja, acc, 0


def denso(ev, n0, n):
    """Lista densa de largo n desde eventos (tick, valor); antes de n0 queda None."""
    out = [None] * n
    for k, (i, v) in enumerate(ev):
        j = ev[k + 1][0] if k + 1 < len(ev) else n
        out[i:j] = [v] * (j - i)
    return out


# --- fase A --------------------------------------------------------------------------------------

_PA = {}


def tabla_pA(j):
    """P(255 antes que 100 | x, r, clase j) del modelo (paseo_optimo, float32, (r, x))."""
    if j not in _PA:
        a = array.array("f")
        with open(P.ruta_pA(j), "rb") as f:
            a.frombytes(f.read())
        _PA[j] = a
    return _PA[j]


A_BASE = dict(modo="tabla",      # "tabla": decide la tabla comprimida de V3; "prob": umbrales de pA
              f1=(1, 2), f2=(1, 2),   # fracción del patrimonio con s' = 1/2 y con s' = 1 de la tabla
              pin=None, pout=None,    # modo tabla: además exige pA >= pin para entrar; sale con pA < pout
              clases=None,            # conjunto de clases de v^2 permitidas para entrar (None: todas)
              rmin=0,                 # no entra con menos de rmin ticks restantes
              escala=None,            # modo prob: [(p, (num, den))] fracción según pA (escalones)
              sin_bajo=False,         # modo tabla: ignora los bloques bajos de la tabla (entrada solo por arriba)
              pa_tramo=False)         # pA evaluada en el medio del tramo de 1250 ticks (como la tabla comprimida)


def fase_a(w, pre, opt=None):
    """Fase A con opciones. Devuelve (caja, acc, órdenes, apostó) después de ejecutar en el primer
    extremo. Con opt = None es V3 con (b) (control contra pre["base"])."""
    o = dict(A_BASE)
    if opt:
        o.update(opt)
    tA = pre["tA"]
    comp = OE.comprimida("V3", "log")
    cel = comp.cel
    LT = OE.LARGO_TRAMO
    cvd = denso(pre["cv"], 0, tA + 1)
    modo, f1, f2 = o["modo"], o["f1"], o["f2"]
    pin, pout, clases, rmin, escala = o["pin"], o["pout"], o["clases"], o["rmin"], o["escala"]
    usa_p = pin is not None or pout is not None or modo == "prob"
    sin_bajo, pa_tramo = o["sin_bajo"], o["pa_tramo"]
    tope = f1 == f2                 # como la guarda (b): la posición interna nunca pasa de media
    caja, acc, d, nord = CAJA0, 0, M_, 0
    aposto = False
    s = 0           # posición objetivo actual: 0, 1 (media de la tabla) o 2 (completa de la tabla)
    obj = None
    fr = None
    L = P.L
    for i in range(tA + 1):
        p = w[i]
        if d:
            caja, acc, h = _ejec(d, p, caja, acc)
            nord += h
        if acc > 0:
            aposto = True
        if i == tA:
            break
        if i + 1 < OE.T_MIN:
            d = M_
            continue
        j = cvd[i]
        r = N - 1 - i
        if modo == "tabla":
            a1, a2, b1, b2 = cel[("A", j, min(OE.TRAMOS - 1, r // LT))][s]
            if sin_bajo:
                sp = 2 if p >= a2 else 1 if p >= a1 else 0
            else:
                sp = 2 if (p >= a2 or p <= b2) else 1 if (p >= a1 or p <= b1) else 0
            if tope and sp > 1:
                sp = 1
            nf = f2 if sp == 2 else f1 if sp == 1 else None
        else:
            sp, nf = s, fr
        if usa_p:
            rp = (min(OE.TRAMOS - 1, r // LT) * LT + LT // 2) if pa_tramo else r
            pa = tabla_pA(j)[rp * L + p - LO]
            if modo == "prob":
                nf = None
                for pu, fx in escala:
                    if pa >= pu:
                        nf = fx
                # histéresis: mantiene la fracción actual mientras pA >= pout
                if nf is None and fr is not None and pout is not None and pa >= pout:
                    nf = fr
                elif nf is not None and fr is not None and pout is not None and nf[0] * fr[1] < fr[0] * nf[1] and pa >= pout:
                    nf = fr
                sp = 0 if nf is None else 1
            else:
                if s == 0 and sp > 0 and pin is not None and not pa >= pin:
                    sp, nf = 0, None
                elif s > 0 and sp > 0 and pout is not None and not pa >= pout:
                    sp, nf = 0, None
        if sp > 0 and s == 0:
            if (clases is not None and j not in clases) or r < rmin:
                sp, nf = 0, None
        if sp == 0:
            d = V_
            obj = None
            fr = None
        else:
            if nf[0] == nf[1]:
                d = C_
                obj = None
            else:
                if obj is None or nf != fr:
                    obj = ((caja + acc * p) * nf[0]) // (nf[1] * p)
                d = ideas.hacia(obj, acc)
            fr = nf
        s = sp
    return caja, acc, nord, aposto


# --- desde el primer extremo ---------------------------------------------------------------------

POST_BASE = dict(
    motor="E1",        # E0 copia al clon; E1 bytes de V2; E2 banda propia en D (c2, v2); EB banda propia (cS, vS, cB, vB)
    M=100,             # candado: D contra el clon >= M
    Mfin=None,         # (R, M2): con R o menos ticks restantes el candado cierra con D >= M2
    L=None,            # piso fijo: D < -L deja de desviarse
    frenos=(),         # reglas de freno (arista 2); ver _freno
    fases="BCD",       # fases en que actúa el motor en recuperación (en las otras copia al clon)
    rmot=0,            # el motor actúa solo con más de rmot ticks restantes
    audacia=None,      # (R, tipo): con R o menos ticks restantes y D < 0, jugada audaz (ver post)
    amb=False,         # sin apuesta en la fase A, corre el motor igual (ambición)
    banda=None,        # niveles propios en D en modo copia: (cS, vS, cB, vB); None copia al clon
    c2=None, v2=None,  # niveles del motor E2 en D
    k3=None,           # motor E3: en C compra con p <= 100 + k3; en B vende con p >= 255 - k3
    Mslip=0,           # el candado exige D >= M + Mslip * |acciones propias - acciones del clon|
    amb_si=None,       # (clases, rmin): la ambición solo vale si la clase de v^2 al primer extremo está en clases
                       # y quedan rmin ticks o más (None: siempre)
    clon="b40",        # el rival emulado al que se copia y contra el que se lleva D
)


def _amb_ok(cond, pre, tA):
    if cond is None:
        return True
    clases, rmin = cond
    cl = pre["cv"][-1][1] if pre["cv"] else -1
    return (clases is None or cl in clases) and N - 1 - tA >= rmin


def post(w, pre, ini, riv, opt=None, traza=None):
    """Desde el primer extremo. ini = (caja, acc, órdenes, apostó) después de ejecutar en tA.
    riv = {"b40": (caja, acc, d)} densas (más los rivales que se quieran valorizar).
    Devuelve (patrimonio, órdenes, grupo, D final contra el clon)."""
    o = dict(POST_BASE)
    if opt:
        o.update(opt)
    tA, t100, t255 = pre["tA"], pre["t100"], pre["t255"]
    tD = max(t100, t255)
    caso_s = t100 < t255
    cc, ac, dc = riv[o["clon"]]
    motor, M, L = o["motor"], o["M"], o["L"]
    Mfin, frenos, fases, rmot, aud, banda = o["Mfin"], o["frenos"], o["fases"], o["rmot"], o["audacia"], o["banda"]
    v2d = denso(pre["v2"], tA, N) if motor == "E1" else denso(pre[motor], tA, N) if motor.startswith("v2c") else None
    k3, Mslip = o["k3"], o["Mslip"]
    trig3 = False
    caja, acc, nord, aposto = ini
    n = tA
    p = w[n]
    D = caja + acc * p - cc[n] - ac[n] * p
    if aposto and D >= M:
        modo, grupo = 0, "apuesta"
    elif aposto or (o["amb"] and _amb_ok(o["amb_si"], pre, tA)):
        modo, grupo = 1, "sin_recuperar"
    else:
        modo, grupo = 0, "sin_desviar"
    # estado de los frenos
    D0 = D
    Wc0 = cc[n] + ac[n] * p
    Dmin = D
    ventas_clon = 0
    q2 = None                       # byte arrastrado del motor de banda propia
    qb = None                       # byte arrastrado de la banda propia en modo copia
    aud_on = False
    d = M_
    Rf, M2 = Mfin if Mfin else (-1, M)
    Ra, atipo = aud if aud else (-1, None)
    c2, v2 = o["c2"], o["v2"]
    while True:
        r = N - 1 - n
        if modo == 1:
            Mef = M2 if r <= Rf else M
            if Mslip:
                da = acc - ac[n]
                Mef += Mslip * (da if da >= 0 else -da)
            if D >= Mef and not aud_on:
                modo, grupo = 0, "recuperacion"
            elif L is not None and D < -L:
                modo, grupo = 0, "piso"
            elif frenos:
                if D < Dmin:
                    Dmin = D
                for fr in frenos:
                    k = fr[0]
                    if k == "clon":          # el clon ganó g por mil desde tA y seguimos abajo
                        if D < 0 and (cc[n] + ac[n] * p) * 1000 >= Wc0 * (1000 + fr[1]):
                            modo, grupo = 0, "freno"
                    elif k == "ciclos":      # el clon completó k ventas en D desde tA y seguimos abajo
                        if D < 0 and ventas_clon >= fr[1]:
                            modo, grupo = 0, "freno"
                    elif k == "motor":       # el motor perdió x desde que empezó la recuperación
                        if D <= D0 - fr[1]:
                            modo, grupo = 0, "freno"
                    elif k == "tiempo":      # quedan R o menos ticks y seguimos abajo
                        if r <= fr[1] and D < 0:
                            modo, grupo = 0, "freno"
        if n > tA and dc[n] == V_ and dc[n - 1] == C_ and n > tD:
            ventas_clon += 1
        b = dc[n]
        if modo == 1:
            F = "D" if n >= tD else ("B" if caso_s else "C")
            if F in fases and r > rmot:
                if v2d is not None:
                    b = v2d[n]
                elif motor == "E3":
                    if F == "B":
                        if p >= HI - k3:
                            trig3 = True
                        if trig3:
                            b = V_
                    elif F == "C":
                        if p <= LO + k3:
                            trig3 = True
                        if trig3:
                            b = C_
                elif motor == "E2":
                    if F == "D":
                        if q2 is None:
                            q2 = dc[n]
                        if p <= c2:
                            q2 = C_
                        elif p >= v2:
                            q2 = V_
                        b = q2
            if r <= Ra and D < 0:
                aud_on = True
                if atipo == "contra":        # lo contrario del clon
                    b = V_ if dc[n] == C_ else C_
                elif atipo == "compra":
                    b = C_
                elif atipo == "caja":
                    b = V_
            elif aud_on:                     # ya arriba: vuelve al clon y cierra
                aud_on = False
                if D >= Mef:
                    modo, grupo = 0, "recuperacion"
                    b = dc[n]
        elif banda is not None and n >= tD:
            cS, vS, cB, vB = banda
            if qb is None:
                qb = dc[n]
            if caso_s:
                if p <= cS:
                    qb = C_
                elif p >= vS:
                    qb = V_
            else:
                if p <= cB:
                    qb = C_
                elif p >= vB:
                    qb = V_
            b = qb
        d = b
        if traza is not None:
            traza.append((n, d))
        n += 1
        if n >= N:
            break
        p = w[n]
        if d == C_:
            q = (caja - COM) // p
            if q > 63:
                q = 63
            if q > 0:
                caja -= q * p + COM
                acc += q
                nord += 1
        elif d == V_ and acc > 0:
            q = acc if acc < 63 else 63
            caja += q * p - COM
            acc -= q
            nord += 1
        D = caja + acc * p - cc[n] - ac[n] * p
    p = w[N - 1]
    return caja + acc * p, nord, grupo, caja + acc * p - cc[N - 1] - ac[N - 1] * p


def clones_de(variantes):
    """Los rivales emulados que necesitan las variantes."""
    return sorted({(optP or {}).get("clon", "b40") for _, optP in variantes})


# --- segunda implementación, para el control tick a tick ------------------------------------------

class _FaseA(OE.Optima):
    """V3 con (b) con compuerta de pA en la entrada, armada sobre optimo_estrategia.Optima."""

    def __init__(self, pin=None, placa2=False):
        super().__init__(variante="V3", objetivo="log", estimador="S2/t", comprimida=OE.comprimida("V3", "log"),
                         placa=True, guarda=(0, True, False))
        self.pin, self.placa2 = pin, placa2

    def _guardas(self, F, j, p, sp):
        if F != "A":
            return sp
        r = max(0, P.N - 1 - self.n)
        tr = min(OE.TRAMOS - 1, r // OE.LARGO_TRAMO)
        if self.placa2:
            a1, a2, _, _ = self.comp.cel[("A", j, tr)][self.s]
            sp = 2 if p >= a2 else 1 if p >= a1 else 0
        sp = super()._guardas(F, j, p, sp)
        if self.pin is not None and self.s == 0 and sp > 0:
            rp = tr * OE.LARGO_TRAMO + OE.LARGO_TRAMO // 2 if self.placa2 else r
            if not tabla_pA(j)[rp * P.L + p - LO] >= self.pin:
                sp = 0
        return sp


class V5Ref:
    """V5 como estrategia de ideas.correr, escrita aparte de fase_a y post: fase A con _FaseA, clon con
    ideas.Cuenta, motor con Optima (V2 comprimida, sin fase A interna) y la máquina de modos."""

    def __init__(self, pin=None, placa2=False, tramos=16, M=100, amb=True, amb_clases=None, Mslip=0, banda=40):
        self.amb_clases, self.Mslip = amb_clases, Mslip
        self.a = _FaseA(pin, placa2)
        self.clon = ideas.Cuenta(ideas.crear(("banda", {"w": banda})))
        if tramos == 16:
            self.mot = ideas.crear(V2C)
        else:
            self.mot = OE.Optima(variante="V2", objetivo="log", estimador="S2/t", comprimida=comprimida_tramos(tramos), placa=True)
        self.mot.opt = ("B", "C", "D")
        self.M, self.amb = M, amb
        self.modo, self.aposto = "A", False

    def decidir(self, p, caja, acc):
        cl = self.clon
        cl.paso(p)
        D = caja + acc * p - cl.W
        da = self.a.decidir(p, caja, acc)
        dm = self.mot.decidir(p, CAJA0, 0)
        if self.modo == "A":
            if acc > 0:
                self.aposto = True
            if not (self.a.vlo or self.a.vhi):
                return da
            if self.aposto and D >= self.M:
                self.modo = "copia"
            elif self.aposto or (self.amb and (self.amb_clases is None or self.a.cv in self.amb_clases)):
                self.modo = "rec"
            else:
                self.modo = "copia"
        if self.modo == "rec":
            if D >= self.M + self.Mslip * abs(acc - cl.acc):
                self.modo = "copia"
            else:
                return dm
        return cl.d
