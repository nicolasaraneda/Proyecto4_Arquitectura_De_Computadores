#!/usr/bin/env python3
"""candado.py: candado contra un clon de la banda 40 (docs/exploracion_ideas.md, sección 14).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Una cuenta sombra emula la banda 40 exacta tick a tick, con la contabilidad oficial (caja 10 000,
comisión 5, compra recortada a (caja - 5) / p, venta recortada a las acciones), y lleva
D = patrimonio propio - patrimonio del clon, valorizado al precio actual. Regla:
  - mientras D < M (y D > -L si hay tope), opera la política base;
  - cuando D >= M ("candado arriba") o D <= -L ("tope"), iguala la cartera del clon y lo copia
    hasta el final de la ronda.
Igualar la cartera es tener las mismas acciones que el clon. Con órdenes de hasta 63 acciones y
comisión 5 cada una, como cualquier otra orden; las compras quedan recortadas por la caja propia
(si D es negativo puede no alcanzar). Una vez iguales, las dos cuentas hacen las mismas
operaciones a los mismos precios y D queda fijo, salvo cuando la compra del clon queda recortada
por su caja: la placa estima la cantidad con el precio que acaba de ver y la ejecución usa el
siguiente, así que puede quedar una diferencia de una acción que se corrige con otra orden.

Tiempo de la decisión, como en ideas.correr: en el tick n se ejecuta la orden pendiente a p(n), se
valoriza y se decide; la decisión se ejecuta a p(n + 1). El candado se revisa con el estado
después de ejecutar en n, y la decisión de ese mismo tick ya es la del seguidor.

Dos implementaciones que deben dar lo mismo:
  Candado            estrategia para ideas.correr (la referencia directa, lenta);
  ventana_combos     corre la base una vez por ventana, guarda su trayectoria y aplica todas las
                     combinaciones (M, L) desde el tick del candado (rápida).
hilo_clon_placa      el hilo que emula al clon y lleva D solo con sumas, restas, comparaciones y
                     tablas (optimo_placa.py), contando operaciones por tick (parte 6).
"""
import bisect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ideas          # noqa: E402
import optimo_placa as OP  # noqa: E402

M_, C_, V_ = ideas.M, ideas.C, ideas.V
CAJA0, COM = ideas.CAJA0, ideas.COMISION
CLON = ("banda", {"w": 40})


def ejecutar(d, p, caja, acc):
    """La contabilidad oficial de ideas.correr para una orden d al precio p. Devuelve (caja, acc, hubo)."""
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


def objetivo_clon(dc, p, caja_c, acc_c):
    """Acciones del clon después de ejecutar su orden dc, estimadas con el precio p que se acaba de ver."""
    a = dc >> 6
    if a == 1:
        t = (caja_c - COM) // p
        q = dc & 63
        return acc_c + (q if q < t else max(t, 0))
    if a == 2:
        q = dc & 63
        return acc_c - (q if q < acc_c else acc_c)
    return acc_c


# --- referencia directa -------------------------------------------------------------------------

class Candado:
    """Estrategia para ideas.correr: base hasta el candado, después copia al clon."""

    def __init__(self, base, M, L=None):
        self.base = ideas.crear(base)
        self.clon = ideas.Cuenta(ideas.crear(CLON))
        self.M, self.L = M, L
        self.estado = 0          # 0 base, 1 candado arriba, 2 tope
        self.tick = -1
        self.t_candado = -1
        self.D = 0

    def decidir(self, p, caja, acc):
        self.tick += 1
        cl = self.clon
        cl.paso(p)               # ejecuta la orden pendiente del clon a p y pide la siguiente
        D = caja + acc * p - cl.W
        self.D = D
        if self.estado == 0:
            d = self.base.decidir(p, caja, acc)
            if D >= self.M:
                self.estado, self.t_candado = 1, self.tick
            elif self.L is not None and D <= -self.L:
                self.estado, self.t_candado = 2, self.tick
            else:
                return d
        return ideas.hacia(objetivo_clon(cl.d, p, cl.caja, cl.acc), acc)

    def info(self):
        return (self.estado, self.t_candado)


# --- camino rápido ------------------------------------------------------------------------------

def trayectoria_clon(w):
    """Estado del clon después de ejecutar en cada tick, su decisión y sus órdenes acumuladas."""
    s = ideas.crear(CLON)
    n = len(w)
    caja_l, acc_l, d_l, nord_l = [0] * n, [0] * n, [0] * n, [0] * n
    caja, acc, d, nord = CAJA0, 0, M_, 0
    dec = s.decidir
    for i, p in enumerate(w):
        caja, acc, h = ejecutar(d, p, caja, acc)
        nord += h
        d = dec(p, caja, acc)
        caja_l[i], acc_l[i], d_l[i], nord_l[i] = caja, acc, d, nord
    # ticks en que el seguidor no puede saltar: el clon va a ejecutar (estimado o real)
    act = [i for i in range(n - 1) if acc_l[i + 1] != acc_l[i] or objetivo_clon(d_l[i], w[i], caja_l[i], acc_l[i]) != acc_l[i]]
    return dict(caja=caja_l, acc=acc_l, d=d_l, nord=nord_l, act=act, W=caja + acc * w[-1])


def trayectoria_base(w, spec):
    s = ideas.crear(spec)
    n = len(w)
    caja_l, acc_l, nord_l = [0] * n, [0] * n, [0] * n
    caja, acc, d, nord = CAJA0, 0, M_, 0
    dec = s.decidir
    for i, p in enumerate(w):
        caja, acc, h = ejecutar(d, p, caja, acc)
        nord += h
        caja_l[i], acc_l[i], nord_l[i] = caja, acc, nord
        d = dec(p, caja, acc)
    return dict(caja=caja_l, acc=acc_l, nord=nord_l, W=caja + acc * w[-1])


def seguir(w, n0, caja, acc, cl):
    """El seguidor desde el tick n0 (estado propio después de ejecutar en n0). Devuelve
    (patrimonio final, órdenes propias desde n0 + 1)."""
    N = len(w)
    ca, ac, dl, act = cl["caja"], cl["acc"], cl["d"], cl["act"]
    nord = 0
    n = n0
    while n < N - 1:
        p = w[n]
        d = ideas.hacia(objetivo_clon(dl[n], p, ca[n], ac[n]), acc)
        if d == M_ and acc == ac[n]:
            # sincronizado: si el clon no ejecuta en n + 1, salta al próximo tick con actividad del clon;
            # en un tick con actividad se avanza de a uno (la compra del clon puede ocurrir aunque la
            # estimación diga que no, si el precio siguiente baja)
            j = bisect.bisect_left(act, n)
            if j == len(act):
                break
            if act[j] > n:
                n = act[j]
                continue
        caja, acc, h = ejecutar(d, w[n + 1], caja, acc)
        nord += h
        n += 1
    return caja + acc * w[-1], nord


def ventana_combos(w, specs, Ms, Ls):
    """Para cada base de specs y cada (M, L): patrimonio, estado final (0, 1, 2), órdenes propias y
    órdenes del clon en la misma ventana. Devuelve también el patrimonio de la base sola y del clon."""
    cl = trayectoria_clon(w)
    out = {"clon": (cl["W"], cl["nord"][-1])}
    N = len(w)
    for k, spec in enumerate(specs):
        b = trayectoria_base(w, spec)
        out[("base", k)] = (b["W"], b["nord"][-1])
        cb, ab, cc, ac = b["caja"], b["acc"], cl["caja"], cl["acc"]
        # primer tick en que D >= M para cada M y D <= -L para cada L
        Ms_ord = sorted(Ms)
        Ls_ord = sorted(x for x in Ls if x is not None)
        primM, primL = {}, {}
        jm, jl = 0, 0
        for i in range(N):
            if jm == len(Ms_ord) and jl == len(Ls_ord):
                break
            p = w[i]
            D = cb[i] - cc[i] + (ab[i] - ac[i]) * p
            while jm < len(Ms_ord) and D >= Ms_ord[jm]:
                primM[Ms_ord[jm]] = i
                jm += 1
            while jl < len(Ls_ord) and D <= -Ls_ord[jl]:
                primL[Ls_ord[jl]] = i
                jl += 1
        for M in Ms:
            for L in Ls:
                tm = primM.get(M, N)
                tl = primL.get(L, N) if L is not None else N
                if tm == N and tl == N:
                    out[(k, M, L)] = (b["W"], 0, b["nord"][-1], 0, -1)
                    continue
                n0, est = (tm, 1) if tm <= tl else (tl, 2)
                Wf, nf = seguir(w, n0, cb[n0], ab[n0], cl)
                nord = b["nord"][n0] + nf
                extra = nf - (cl["nord"][-1] - cl["nord"][n0])
                out[(k, M, L)] = (Wf, est, nord, extra, n0)
    return out


# --- parte 6: el hilo del clon en la placa ------------------------------------------------------

def hilo_clon_placa(w, ops_propia=True):
    """Emula al clon y lleva D solo con sumas, restas, comparaciones y tablas. Cuenta operaciones por
    tick (cada suma, resta, comparación, salto tomado, carga y store, una). Devuelve
    (lista de D por tick, peor caso de operaciones, media, detalle del peor tick).
    Lleva también la cuenta propia de la estrategia (si ops_propia), porque D la necesita; se
    alimenta con la estrategia base banda 60 solo para tener una cuenta propia distinta del clon."""
    clon = ideas.crear(CLON)
    prop = ideas.crear(("banda", {"w": 60}))
    caja_c, acc_c, dc = CAJA0, 0, M_
    caja, acc, d = CAJA0, 0, M_
    Ds, peor, tot, det_peor = [], 0, 0, None
    for p in w:
        ops = 2                                   # carga del precio publicado y de su tick
        det = {}
        # 1. el clon ejecuta su orden pendiente a p (contabilidad oficial)
        o = 2                                     # decodifica acción (comparaciones con 0x40 y 0x80)
        a = dc >> 6
        if a == 1:
            q, oq = OP.maxima_compra(caja_c, p)   # min(63, (caja - 5) / p) por restas
            o += oq
            if q > 0:
                qp, op_ = OP.producto(q, p, 6)
                o += op_ + 4                      # caja -= qp + 5, acc += q, store de las dos
                caja_c -= qp + COM
                acc_c += q
        elif a == 2:
            q = acc_c if acc_c < 63 else 63
            o += 2
            if q > 0:
                qp, op_ = OP.producto(q, p, 6)
                o += op_ + 4
                caja_c += qp - COM
                acc_c -= q
        det["clon ejecuta"] = o
        ops += o
        # 2. la regla del clon (fases y banda 40): unas comparaciones
        o = 8
        dc = clon.decidir(p, caja_c, acc_c)
        det["clon decide"] = o
        ops += o
        # 3. la cuenta propia ejecuta su orden (igual que el clon)
        if ops_propia:
            o = 2
            a = d >> 6
            if a == 1:
                q, oq = OP.maxima_compra(caja, p)
                o += oq
                if q > 0:
                    qp, op_ = OP.producto(q, p, 6)
                    o += op_ + 4
                    caja -= qp + COM
                    acc += q
            elif a == 2:
                q = acc if acc < 63 else 63
                o += 2
                if q > 0:
                    qp, op_ = OP.producto(q, p, 6)
                    o += op_ + 4
                    caja += qp - COM
                    acc -= q
            det["cuenta propia"] = o
            ops += o
            d = prop.decidir(p, caja, acc)
        # 4. D = (caja - caja_c) + (acc - acc_c) p, con el signo de la diferencia de acciones
        o = 3                                     # resta de cajas, resta de acciones, comparación con 0
        dacc = acc - acc_c
        mag = dacc if dacc >= 0 else -dacc
        if dacc < 0:
            o += 1                                # negar
        prod, op_ = OP.producto(mag, p, 9)        # acciones < 512
        o += op_
        D = caja - caja_c + (prod if dacc >= 0 else -prod)
        o += 2                                    # suma o resta y store
        det["D"] = o
        ops += o
        # 5. compara con M y -L y publica el estado (y el objetivo del seguidor: otra estimación del recorte)
        o = 4
        if dc >> 6 == 1:
            _, oq = OP.maxima_compra(caja_c, p)
            o += oq + 2
        else:
            o += 3
        o += 2                                    # publica objetivo y tick
        det["candado y objetivo"] = o
        ops += o
        ops += 4                                  # lazo: espera del tick siguiente, saltos
        Ds.append(D)
        tot += ops
        if ops > peor:
            peor, det_peor = ops, det
    return Ds, peor, tot / len(w), det_peor
