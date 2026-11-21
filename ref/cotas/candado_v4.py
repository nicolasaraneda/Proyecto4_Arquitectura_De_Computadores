#!/usr/bin/env python3
"""candado_v4.py: V4, candado selectivo con máquina de modos (docs/exploracion_ideas.md, sección 14, parte 7).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

D = patrimonio propio - patrimonio del clon (banda 40 emulada, candado.py), al precio actual.
Máquina de modos por ronda:
  APUESTA       fase A: decide la política base (V1, V3 con (b) o la fase A de V2). La apuesta está
                abierta mientras haya acciones; sin candado mientras esté abierta, sea cual sea D.
                Se cierra cuando la base vuelve a caja o cuando se toca un extremo.
  CANDADO       sin apuesta abierta y D >= M: igualar las acciones del clon y copiarlo hasta el final
                (el seguidor de candado.py: órdenes de hasta 63, comisión 5 cada una).
  RECUPERACIÓN  sin apuesta abierta y D < M, después de la fase A: corre el motor hasta que D >= M
                (pasa a CANDADO) o termina la ronda. Con piso L: si D < -L, deja de desviarse y copia
                al clon hasta el final.
Interpretación fijada aquí (sección 14):
  - Una apuesta cerrada en la fase A con D < M no termina la fase A: la base sigue decidiendo y
    puede volver a apostar; la recuperación empieza al tocar el primer extremo. En la fase A solo se
    revisa el candado (acciones en 0 y D >= M), no el piso.
  - "Copiar al clon" fuera del candado es mandar el mismo byte que el clon ("comprar 63",
    "vender 63"), con la caja propia. Así E0 sin candado (M infinito) da la base sin candado:
    después de la fase A, V1 y V3 hacen lo mismo que el clon.
  - Sin haber apostado, D es 0 al tocar el primer extremo. Sin ambición, la ronda copia al clon
    ("sin desviar"); con ambición, el motor corre desde ahí.
Motores (actúan en las fases B, C y D; donde no actúan, copian el byte del clon):
  E0  ninguno.
  E1  la política V2 en B, C y D (sus bytes son los de V2 sola: con dos posiciones no dependen de la
      cuenta; su estado de posición interno es el de su propia corrida).
  E2  en D, banda propia: compra con p <= 140 + d, vende con p >= 215 - d (se arrastra como la regla:
      fuera de los dos niveles repite su último byte, que al entrar a D es el del clon).
  E3  en C, compra con p <= 100 + k y se queda comprado; en B, vende con p >= 255 - k y se queda en
      caja. Se deshace por el candado (D >= M) o queda igual al clon cuando llega el extremo.
  E4  E2 + E3.

V4b (corrección de Nicolás del 20/11, fase_a_libre=True): durante toda la fase A manda solo la
política base, que abre y cierra apuestas las veces que quiera; CANDADO y RECUPERACIÓN recién pueden
activarse al tocar el primer extremo. El resto igual que V4.
CANDADO "copiar" (pedido de Nicolás del 20/11, el que usa V4b; candado="copiar"): al cerrarse, la
cartera propia va al mismo estado que el clon (si el clon está comprado, "comprar 63" hasta que la
caja propia no alcance para una acción más; si está en caja, "vender 63" hasta quedar sin acciones);
desde ahí, los mismos bytes que el clon con la cuenta propia hasta el final. Estado del clon: comprado
si su byte es de compra, en caja si es de venta; con "mantener", comprado si tiene acciones. Desde el
primer extremo el byte del clon siempre es "comprar 63" o "vender 63" (la banda ya tocó 140 o 215), así
que en el camino por eventos ese candado es copiar el byte del clon desde el tick del candado; se
comprueba con assert y contra la referencia directa. CANDADO "igualar" (V4 original): igualar el
número de acciones del clon y seguirlo (candado.py).

Dos implementaciones que deben dar lo mismo: V4 (estrategia para ideas.correr, tick a tick) y
ventana_v4 (por eventos: entre dos eventos nada se ejecuta ni cambia ninguna decisión).
Grupos de cada ronda: "apuesta" (candado al cerrar una apuesta ganada), "recuperacion" (candado
durante la recuperación), "sin_recuperar", "piso" y "sin_desviar".
"""
import bisect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import candado as CD  # noqa: E402
import ideas          # noqa: E402

M_, C_, V_ = ideas.M, ideas.C, ideas.V
LO, HI = ideas.LO, ideas.HI
INF = 10 ** 12
GRUPOS = ("apuesta", "recuperacion", "sin_recuperar", "piso", "sin_desviar")


def motores():
    out = [("E0", None, None), ("E1", None, None)]
    out += [("E2", d, None) for d in (10, 20, 30)]
    out += [("E3", None, k) for k in (3, 5, 10)]
    out += [("E4", d, k) for d in (10, 20, 30) for k in (3, 5, 10)]
    return out


def nombre_motor(m):
    e, d, k = m
    return e + (f" d{d}" if d is not None else "") + (f" k{k}" if k is not None else "")


class Motor:
    """Estado del motor en la recuperación (E2: byte arrastrado en D; E3: disparos en B y C)."""
    __slots__ = ("e", "d", "k", "q2", "trigB", "trigC")

    def __init__(self, m):
        self.e, self.d, self.k = m
        self.q2 = None
        self.trigB = self.trigC = False

    def byte(self, F, p, dcl, dv2):
        e = self.e
        if F == "D" and self.q2 is None:
            self.q2 = dcl                 # al entrar a D, el byte del clon (C con 100, V con 255)
        if e == "E0":
            return dcl
        if e == "E1":
            return dv2
        if F == "D":
            if e in ("E2", "E4"):
                if p <= 140 + self.d:
                    self.q2 = C_
                elif p >= 215 - self.d:
                    self.q2 = V_
                return self.q2
            return dcl
        if e in ("E3", "E4"):
            if F == "B":
                if not self.trigB and p >= 255 - self.k:
                    self.trigB = True
                return V_ if self.trigB else dcl
            if F == "C":
                if not self.trigC and p <= 100 + self.k:
                    self.trigC = True
                return C_ if self.trigC else dcl
        return dcl


# --- referencia directa -------------------------------------------------------------------------

class V4:
    def __init__(self, base, motor, M, L=None, ambicion=False, fase_a_libre=False, candado="igualar"):
        self.libre = fase_a_libre
        self.cmodo = candado
        self.lock = None
        self.base = ideas.crear(base)
        self.v2 = ideas.crear(("optima", {"variante": "V2", "objetivo": "log", "estimador": "S2/t"})) if motor[0] == "E1" else None
        self.clon = ideas.Cuenta(ideas.crear(CD.CLON))
        self.mot = Motor(motor)
        self.M, self.L, self.amb = M, L, ambicion
        self.vlo = self.vhi = False
        self.modo = "A"
        self.aposto = False
        self.grupo = None
        self.tick = -1

    def decidir(self, p, caja, acc):
        self.tick += 1
        cl = self.clon
        cl.paso(p)
        dcl = cl.d
        D = caja + acc * p - cl.W
        db = self.base.decidir(p, caja, acc)
        dv2 = self.v2.decidir(p, caja, acc) if self.v2 is not None else M_
        if p <= LO:
            self.vlo = True
        elif p >= HI:
            self.vhi = True
        F = "D" if (self.vlo and self.vhi) else ("B" if self.vlo else ("C" if self.vhi else "A"))
        if self.modo == "candado":
            if self.cmodo == "copiar":
                return self._copiar(dcl, p, caja, acc)
            return ideas.hacia(CD.objetivo_clon(dcl, p, cl.caja, cl.acc), acc)
        if self.modo == "A":
            if acc > 0:
                self.aposto = True
            if F == "A":
                if not self.libre and acc == 0 and self.aposto and D >= self.M:
                    return self._candado("apuesta", dcl, p, acc, caja)
                return db
            # primer extremo: la apuesta se cierra
            if self.aposto and D >= self.M:
                return self._candado("apuesta", dcl, p, acc, caja)
            if self.aposto or (self.amb and -10 <= D < self.M):
                self.modo = "rec"
            else:
                self.modo, self.grupo = "copia", "sin_desviar"
        if self.modo == "rec":
            if D >= self.M:
                return self._candado("recuperacion", dcl, p, acc, caja)
            if self.L is not None and D < -self.L:
                self.modo, self.grupo = "copia", "piso"
        b = self.mot.byte(F, p, dcl, dv2)       # mantiene el estado del motor también en copia
        if self.modo == "copia":
            return dcl
        return b

    def _candado(self, g, dcl, p, acc, caja):
        self.modo, self.grupo = "candado", g
        cl = self.clon
        self.lock = (caja + acc * p, cl.W)
        if self.cmodo == "copiar":
            self.obj = C_ if _comprado(dcl, cl.acc) else V_
            self.igualando = True
            return self._copiar(dcl, p, caja, acc)
        return ideas.hacia(CD.objetivo_clon(dcl, p, cl.caja, cl.acc), acc)

    def _copiar(self, dcl, p, caja, acc):
        if self.igualando:
            if _comprado(dcl, self.clon.acc) != (self.obj == C_):
                self.igualando = False          # el clon cambió de estado: desde aquí, su byte
            elif (self.obj == C_ and caja - CD.COM >= p) or (self.obj == V_ and acc > 0):
                return self.obj
            else:
                self.igualando = False
        return dcl

    def info(self):
        return (self.grupo or ("sin_recuperar" if self.modo == "rec" else "sin_desviar"), self.lock)


def _comprado(dcl, acc_clon):
    a = dcl >> 6
    return a == 1 or (a != 2 and acc_clon > 0)


# --- búsqueda del próximo tick con p >= x o p <= x ----------------------------------------------

class Busca:
    B = 32
    S = 32

    def __init__(self, w):
        B, S = self.B, self.S
        self.w = w
        self.n = n = len(w)
        self.bmax = [max(w[i:i + B]) for i in range(0, n, B)]
        self.bmin = [min(w[i:i + B]) for i in range(0, n, B)]
        nb = len(self.bmax)
        self.smax = [max(self.bmax[j:j + S]) for j in range(0, nb, S)]
        self.smin = [min(self.bmin[j:j + S]) for j in range(0, nb, S)]

    def ge(self, i, x):
        """Primer j >= i con w[j] >= x (n si no hay)."""
        w, n, B, S = self.w, self.n, self.B, self.S
        if x <= LO:
            return i if i < n else n
        if i >= n or x > HI:
            return n
        fin = min(n, (i // B + 1) * B)
        for j in range(i, fin):
            if w[j] >= x:
                return j
        if fin >= n:
            return n
        b = fin // B
        bm, nb = self.bmax, len(self.bmax)
        while b < nb and b % S:
            if bm[b] >= x:
                return self._en(b, x, True)
            b += 1
        if b >= nb:
            return n            # sin esto, el superbloque parcial del final devolvía un tick anterior a i
        s = b // S
        sm = self.smax
        while s < len(sm) and sm[s] < x:
            s += 1
        if s >= len(sm):
            return n
        b = s * S
        while bm[b] < x:
            b += 1
        return self._en(b, x, True)

    def le(self, i, x):
        """Primer j >= i con w[j] <= x (n si no hay)."""
        w, n, B, S = self.w, self.n, self.B, self.S
        if x >= HI:
            return i if i < n else n
        if i >= n or x < LO:
            return n
        fin = min(n, (i // B + 1) * B)
        for j in range(i, fin):
            if w[j] <= x:
                return j
        if fin >= n:
            return n
        b = fin // B
        bm, nb = self.bmin, len(self.bmin)
        while b < nb and b % S:
            if bm[b] <= x:
                return self._en(b, x, False)
            b += 1
        if b >= nb:
            return n            # sin esto, el superbloque parcial del final devolvía un tick anterior a i
        s = b // S
        sm = self.smin
        while s < len(sm) and sm[s] > x:
            s += 1
        if s >= len(sm):
            return n
        b = s * S
        while bm[b] > x:
            b += 1
        return self._en(b, x, False)

    def _en(self, b, x, mayor):
        w = self.w
        for j in range(b * self.B, min(self.n, (b + 1) * self.B)):
            if (w[j] >= x) if mayor else (w[j] <= x):
                return j
        raise AssertionError("bloque sin el valor")


def _techo(a, b):
    return -((-a) // b)


# --- por eventos --------------------------------------------------------------------------------

def preparar(w, cl, v2d):
    """Lo que comparten todas las combinaciones de una ventana."""
    N = len(w)
    t100 = next(i for i, p in enumerate(w) if p <= LO)
    t255 = next(i for i, p in enumerate(w) if p >= HI)
    ca, ac, dc = cl["caja"], cl["acc"], cl["d"]
    evc = [j for j in range(1, N) if ac[j] != ac[j - 1] or ca[j] != ca[j - 1] or dc[j] != dc[j - 1]]
    evv = [j for j in range(1, N) if v2d[j] != v2d[j - 1]] if v2d is not None else []
    return dict(N=N, t100=t100, t255=t255, tA=min(t100, t255), tD=max(t100, t255), evc=evc, evv=evv,
                bus=Busca(w), v2d=v2d)


def _fase(n, P):
    lo, hi = n >= P["t100"], n >= P["t255"]
    return "D" if (lo and hi) else ("B" if lo else ("C" if hi else "A"))


def _sig(lst, n):
    j = bisect.bisect_right(lst, n)
    return lst[j] if j < len(lst) else INF


def recorrer(w, P, cl, n0, caja, acc, nord, modo, mot, M, L, copiar=False, grupo=None):
    """Desde la decisión del tick n0 (estado propio después de ejecutar en n0), en modo "rec" o
    "copia". Devuelve (patrimonio, órdenes, grupo, tick del candado o -1, (patrimonio propio,
    patrimonio del clon) al cerrar el candado o None). Con copiar, el candado es copiar el byte del clon."""
    lock = None
    nl = -1
    N, bus, v2d = P["N"], P["bus"], P["v2d"]
    ca, ac, dc = cl["caja"], cl["acc"], cl["d"]
    evc, evv = P["evc"], P["evv"]
    if grupo is None:
        grupo = "sin_recuperar" if modo == "rec" else "sin_desviar"
    n = n0
    while True:
        p = w[n]
        F = _fase(n, P)
        if modo == "rec":
            dC = caja - ca[n]
            dA = acc - ac[n]
            D = dC + dA * p
            if D >= M:
                lock = (caja + acc * p, ca[n] + ac[n] * p)
                if not copiar:
                    Wf, nf = CD.seguir(w, n, caja, acc, cl)
                    return Wf, nord + nf, "recuperacion", n, lock
                assert dc[n] in (C_, V_), "candado copiar: byte del clon sin estado"
                modo, grupo, nl = "copia", "recuperacion", n
            elif L is not None and D < -L:
                modo, grupo = "copia", "piso"
        b = mot.byte(F, p, dc[n], v2d[n] if v2d is not None else M_)
        d = dc[n] if modo == "copia" else b
        # próximo evento
        e = INF
        for t in (P["t100"], P["t255"]):
            if n < t < e:
                e = t
        x = _sig(evc, n)
        if x < e:
            e = x
        if modo == "rec":
            if mot.e == "E1" and F != "A":
                x = _sig(evv, n)
                if x < e:
                    e = x
            if mot.e in ("E3", "E4"):
                if F == "B" and not mot.trigB:
                    x = bus.ge(n + 1, 255 - mot.k)
                    if x < e:
                        e = x
                elif F == "C" and not mot.trigC:
                    x = bus.le(n + 1, 100 + mot.k)
                    if x < e:
                        e = x
            if F == "D" and mot.e in ("E2", "E4"):
                x = bus.ge(n + 1, 215 - mot.d) if mot.q2 == C_ else bus.le(n + 1, 140 + mot.d)
                if x < e:
                    e = x
            if dA > 0:
                x = bus.ge(n + 1, _techo(M - dC, dA))
                if x < e:
                    e = x
                if L is not None:
                    x = bus.le(n + 1, (-L - 1 - dC) // dA)
                    if x < e:
                        e = x
            elif dA < 0:
                a = -dA
                x = bus.le(n + 1, (dC - M) // a)
                if x < e:
                    e = x
                if L is not None:
                    x = bus.ge(n + 1, _techo(dC + L + 1, a))
                    if x < e:
                        e = x
        elif F == "D" and mot.e in ("E2", "E4") and mot.q2 is not None:
            # en copia el motor no decide, pero su byte arrastrado no importa: no hace falta seguirlo
            pass
        a6 = d >> 6
        if a6 == 1:
            x = bus.le(n + 1, caja - 5)
            if x < e:
                e = x
        elif a6 == 2 and acc > 0:
            if n + 1 < e:
                e = n + 1
        if e >= N:
            return caja + acc * w[-1], nord, grupo, nl, lock
        caja, acc, h = CD.ejecutar(d, w[e], caja, acc)
        nord += h
        n = e


def ventana_v4(w, specs, v2spec, combos, fase_a_libre=False, candado="igualar"):
    """combos: lista de (k base, motor, M, L, ambición). Devuelve {combo: (W, grupo, órdenes)} más
    los patrimonios del clon y de cada base sola."""
    cl = CD.trayectoria_clon(w)
    tray = [_tray(w, sp) for sp in specs]
    v2d = None
    for sp, t in zip(specs, tray):
        if sp == v2spec:
            v2d = t["d"]
    if v2d is None:
        v2d = _tray(w, v2spec)["d"]
    P = preparar(w, cl, v2d)
    tA = P["tA"]
    out = {"clon": cl["W"]}
    for k, t in enumerate(tray):
        out[("base", k)] = (t["W"], t["nord"][-1])
    memo = {}
    # por base: primer tick con acciones en la fase A (la apuesta) y, por M, el tick del candado
    pre = {}
    for k, t in enumerate(tray):
        cb, ab = t["caja"], t["acc"]
        apuesta = next((j for j in range(tA + 1) if ab[j] > 0), None)
        DtA = cb[tA] + ab[tA] * w[tA] - (cl["caja"][tA] + cl["acc"][tA] * w[tA])
        cerradas = [] if (apuesta is None or fase_a_libre) else [(j, cb[j] - CD.CAJA0) for j in range(apuesta + 1, tA) if ab[j] == 0]
        pre[k] = (apuesta, DtA, cerradas, {})
    for combo in combos:
        k, mot, M, L, amb = combo
        t = tray[k]
        cb, ab, nb = t["caja"], t["acc"], t["nord"]
        apuesta, DtA, cerradas, porM = pre[k]
        clave = None
        if apuesta is not None:
            # candado al cerrar una apuesta ganada en la fase A, o al tocar el primer extremo
            if M not in porM:
                jl = next((j for j, D in cerradas if D >= M), None)
                if jl is None and DtA >= M:
                    jl = tA
                porM[M] = jl
            jl = porM[M]
            if jl is not None:
                clave = ("lock", k, jl)
                if clave not in memo:
                    lock = (cb[jl] + ab[jl] * w[jl], cl["caja"][jl] + cl["acc"][jl] * w[jl])
                    if candado == "copiar":
                        assert cl["d"][jl] in (C_, V_), "candado copiar: byte del clon sin estado"
                        Wf, nf, _, _, _ = recorrer(w, P, cl, jl, cb[jl], ab[jl], nb[jl], "copia",
                                                   Motor(("E0", None, None)), M, L, True, "apuesta")
                        memo[clave] = (Wf, "apuesta", nf, lock)
                    else:
                        Wf, nf = CD.seguir(w, jl, cb[jl], ab[jl], cl)
                        memo[clave] = (Wf, "apuesta", nb[jl] + nf, lock)
                out[combo] = memo[clave]
                continue
            clave = ("rec", k, mot, M, L)
            modo = "rec"
        else:
            if amb:
                clave = ("rec", k, mot, M, L)
                modo = "rec"
            else:
                clave = ("copia", k)
                modo = "copia"
        if clave not in memo:
            Wf, nf, g, _, lock = recorrer(w, P, cl, tA, cb[tA], ab[tA], nb[tA], modo, Motor(mot), M, L,
                                          candado == "copiar")
            memo[clave] = (Wf, g, nf, lock)
        out[combo] = memo[clave]
    return out


def _tray(w, spec):
    s = ideas.crear(spec)
    n = len(w)
    caja_l, acc_l, nord_l, d_l = [0] * n, [0] * n, [0] * n, [0] * n
    caja, acc, d, nord = CD.CAJA0, 0, M_, 0
    dec = s.decidir
    for i, p in enumerate(w):
        caja, acc, h = CD.ejecutar(d, p, caja, acc)
        nord += h
        caja_l[i], acc_l[i], nord_l[i] = caja, acc, nord
        d = dec(p, caja, acc)
        d_l[i] = d
    return dict(caja=caja_l, acc=acc_l, nord=nord_l, d=d_l, W=caja + acc * w[-1])
