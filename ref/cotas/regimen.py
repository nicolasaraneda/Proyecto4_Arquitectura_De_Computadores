#!/usr/bin/env python3
"""regimen.py: política por régimen filtrado (docs/exploracion_ideas.md, sección 12; pedido del 19/11).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Variables de estado (sección 3 del diseño), todas enteras y sin multiplicar en el camino de
decisión:
  t        ticks recibidos
  S2       suma de (p(n) - p(n-1))^2 con la diferencia acotada a 15 (tabla de 16 cuadrados)
  clase    0 si 4 S2 < t (v^2 < 1/4), 1 si 2 S2 < t, 2 si S2 < t, 3 si no; válida desde t = 390,
           cambia solo si el valor nuevo se mantiene 64 ticks seguidos (histéresis)
  tramo    0, 1, 2 o 3 según t contra 5 000, 10 000 y 15 000
  fase     A, B, C, D como en ideas.Regla; caso S (100 antes que 255) o B, fijado al entrar a D
  pmáx     máximo visto antes del precio actual; entrada: precio con que se decidió la compra del módulo A

Política (sección 4): la banda 40 más dos módulos. Con los dos apagados decide, byte a byte,
lo mismo que ideas.Regla(ideas.BandaD(140, 215)) (explorar_regimen.py equivalencia).
  Módulo D (fase D): par (compra, venta) = T[caso][clase][tramo], con
      compra = c0 + c1 clase - c2 tramo,  venta = v0 - v1 clase,  y compra = 0 si clase <= k
  (c0, c1, v0, v1 por caso; c2 y k compartidos: decisión de Nicolás del 19/11, 10 parámetros).
  Al entrar a D se vende en el caso S (se vio el 255) y se compra en el B (se vio el 100), como
  la banda 40: son certezas que ningún módulo toca. Sin clase válida se usa 140/215.
  Módulo A (fase A): compra N una sola vez si t >= 390, clase <= kA, p >= pmáx y p >= theta.
  Vende todo al ver 255 (y sigue la fase C) o con p <= entrada - d (y el módulo se apaga).

Medidas por ventana para los filtros F1 y F2 (medir) y motor de F3 (correr_e: la banda 40
decidiendo con el precio completo, o con la orden condicionada a los bits del precio que llega).
"""
import ideas
from ideas import M, C, V, LO, HI

CUAD = tuple(d * d for d in range(16))
T_CLASE = 390
HISTERESIS = 64
B40 = (140, 215)


def clase_cruda(S2, t):
    """Clase por v^2 = S2 / t, comparando con sumas (sin multiplicar ni desplazar)."""
    s2x2 = S2 + S2
    if s2x2 + s2x2 < t:
        return 0
    if s2x2 < t:
        return 1
    if S2 < t:
        return 2
    return 3


def tramo(t):
    return 0 if t < 5000 else 1 if t < 10000 else 2 if t < 15000 else 3


def tabla_d(D):
    """T[caso][clase][tramo] -> (compra, venta); caso 1 = S, 2 = B (índice 0 sin uso)."""
    T = [None, [], []]
    for caso, k in ((1, "S"), (2, "B")):
        c0, c1, v0, v1 = D[k]
        for cl in range(4):
            fila = []
            for tr in range(4):
                compra = c0 + c1 * cl - D["c2"] * tr
                if cl <= D["k"]:
                    compra = 0
                fila.append((compra, v0 - v1 * cl))
            T[caso].append(fila)
    return T


class Politica:
    """D: dict(S=(c0, c1, v0, v1), B=(c0, c1, v0, v1), c2=, k=) o None (módulo apagado).
    A: dict(kA=, theta=, d=, N=) o None."""

    def __init__(self, D=None, A=None):
        self.T = tabla_d(D) if D else None
        self.A = A
        # régimen
        self.t = 0
        self.prev = -1
        self.S2 = 0
        self.clase = -1
        self.cuenta = 0
        # fases (mismas reglas que ideas.Regla)
        self.vlo = self.vhi = False
        self.q = M
        self.n = -1
        self.tD = -1
        self.caso = 0
        self.pmax = -1
        # módulo A: 0 disponible, 1 con la compra hecha, 2 usado o apagado
        self.a_est = 0
        self.entrada = 0
        self.a_veces = 0
        self.a_tope = 0

    def _regimen(self, p):
        t = self.t + 1
        self.t = t
        if self.prev >= 0:
            d = p - self.prev
            if d < 0:
                d = -d
            if d > 15:
                d = 15
            self.S2 += CUAD[d]
        self.prev = p
        if t >= T_CLASE:
            raw = clase_cruda(self.S2, t)
            c = self.clase
            if c < 0:
                self.clase = raw
            elif raw != c:
                self.cuenta += 1
                if self.cuenta >= HISTERESIS:
                    self.clase = raw
                    self.cuenta = 0
            else:
                self.cuenta = 0

    def decidir(self, p, caja, acc):
        self.n += 1
        self._regimen(p)
        pm = self.pmax
        if p > pm:
            self.pmax = p
        if self.tD >= 0:
            return self._d(p)
        if p <= LO:
            self.vlo = True
            self.q = C
        elif p >= HI:
            self.vhi = True
            self.q = V
        else:
            if self.A is not None and not self.vlo and not self.vhi:
                return self._a(p, pm)
            return self.q
        if self.a_est == 1:          # sale de la fase A con la compra del módulo: manda la fase nueva
            self.a_est = 2
        if self.vlo and self.vhi:
            self.tD = self.n
            self.caso = 1 if p >= HI else 2
            self.q = V if self.caso == 1 else C
        return self.q

    def _a(self, p, pm):
        A = self.A
        if self.a_est == 0:
            if 0 <= self.clase <= A["kA"] and p >= pm and p >= A["theta"]:
                self.a_est = 1
                self.a_veces += 1
                self.entrada = p
                return 0x40 | A["N"]
            return self.q
        if self.a_est == 1:
            if p <= self.entrada - A["d"]:
                self.a_est = 2
                self.a_tope += 1
                self.q = V
                return V
            return M
        return self.q

    def _d(self, p):
        if self.T is None or self.clase < 0:
            c, v = B40
        else:
            c, v = self.T[self.caso][self.clase][tramo(self.t)]
        if p <= c:
            self.q = C
        elif p >= v:
            self.q = V
        return self.q

    def info(self):
        return (self.tD, self.caso, self.a_veces, self.a_tope)


def spec_politica(D=None, A=None):
    """Especificación hashable para la caché de explorar_ideas.evaluar."""
    return ("regimen_pol", {"D": D, "A": A})


def _crear_politica(D=None, A=None):
    return Politica(D, A)


# ideas.crear envuelve un tipo de COMPS en una Regla; para la política completa (que reemplaza a la
# Regla) se registra un tipo propio en ideas.crear mediante un envoltorio.
_crear_original = ideas.crear


def _crear(spec):
    if spec[0] == "regimen_pol":
        return Politica(**spec[1])
    return _crear_original(spec)


ideas.crear = _crear


# --------------------------------------------------------------------------------------------
# Medidas por ventana para F1 y F2

KS = (1000, 2000, 4000)
HS = (390, 1950)
PASO_T = 13
THETAS = (180, 200, 220, 235)
DS = (8, 12, 16, 24)
FASES = ("A", "BC", "D")


def _signo(x):
    return (x > 0) - (x < 0)


def medir(w):
    """Medidas de una ventana normalizada (bytes o lista de 20 000 precios entre 100 y 255).

    Devuelve dict con:
      caso, tA (índice del primer extremo), tD (del segundo), v2 (ventana entera)
      K -> dict(clase, v2, v2resto, cruces, pers={(h, fase): (suma, cuenta)})
      f2 -> {theta: (índice, p0, clase, mínimo antes del 255)} con el primer máximo nuevo >= theta
            en la fase A desde t = 390 (clase con histéresis, como la política)
      a  -> {(kA, theta): (índice, p0, mínimo antes del 255)} con el primer evento que dispara el
            módulo A (clase <= kA)
    """
    n = len(w)
    s2 = [0] * (n + 1)          # s2[t]: suma con los t primeros ticks
    acc = 0
    prev = w[0]
    for i in range(1, n):
        p = w[i]
        d = p - prev
        if d < 0:
            d = -d
        if d > 15:
            d = 15
        acc += CUAD[d]
        s2[i + 1] = acc
        prev = p
    i100 = w.index(100)
    i255 = w.index(255)
    tA, tD = min(i100, i255), max(i100, i255)
    out = {"caso": 1 if i100 < i255 else 2, "tA": tA, "tD": tD, "v2": s2[n] / n}
    for K in KS:
        cl = clase_cruda(s2[K], K)
        ini = max(K, tD)
        lado = cnt = 0
        for j in range(ini, n):
            p = w[j]
            if p <= 140:
                if lado == 1:
                    cnt += 1
                lado = -1
            elif p >= 215:
                if lado == -1:
                    cnt += 1
                lado = 1
        out[K] = {"clase": cl, "v2": s2[K] / K, "v2resto": (s2[n] - s2[K]) / (n - K), "cruces": cnt,
                  "D_resto": n - ini, "pers": {}}
    for h in HS:
        acum = {(K, f): [0, 0] for K in KS for f in FASES}
        for t in range(h, n - h, PASO_T):
            s = _signo(w[t + h] - w[t]) * _signo(w[t] - w[t - h])
            f = "A" if t < tA else "BC" if t < tD else "D"
            for K in KS:
                if t - h >= K:
                    a = acum[(K, f)]
                    a[0] += s
                    a[1] += 1
        for (K, f), (sm, ct) in acum.items():
            out[K]["pers"][(h, f)] = (sm, ct)
    # F2 y disparos del módulo A: clase con histéresis, recorrida hasta el primer extremo
    pol = Politica()
    f2 = {}
    disp = {}
    pm = -1
    for i in range(tA):
        p = w[i]
        pol._regimen(p)
        if pol.t >= T_CLASE and p >= pm and p >= THETAS[0]:
            cl = pol.clase
            for th in THETAS:
                if p >= th:
                    if th not in f2:
                        f2[th] = (i, p, cl)
                    for kA in (0, 1):
                        if cl <= kA and (kA, th) not in disp:
                            disp[(kA, th)] = (i, p)
        if p > pm:
            pm = p
    # mínimo entre el evento y el 255 (el 255 todavía no se ha visto en la fase A)
    pref = {}
    for clave, ev in list(f2.items()) + list(disp.items()):
        i = ev[0]
        if i not in pref:
            pref[i] = min(w[i + 1:i255]) if i255 > i + 1 else 256
    out["f2"] = {th: ev + (pref[ev[0]],) for th, ev in f2.items()}
    out["a"] = {k: ev + (pref[ev[0]],) for k, ev in disp.items()}
    return out


# --------------------------------------------------------------------------------------------
# F3: la orden condicionada a los bits del precio que llega (módulo E)

def efectivo(base, L, mayor_igual, p):
    """Byte que sale por MISO si el periférico condiciona la orden base a p >= L (o p <= L).
    El bit k de salida se envía mientras llega el bit k del precio: solo puede depender de los
    bits 7 a k+1. Mientras la condición no haya fallado sale el bit base; cuando falla, sale 0, y
    si la base es una venta y la condición falló con el primer bit, el bit 6 sale en 1 (acción
    11, mantener)."""
    out = 0
    fallo = decidido = False
    venta = (base >> 7) & 1
    for k in range(7, -1, -1):
        if fallo:
            b = 1 if (k == 6 and venta and fallo_en == 7) else 0
        else:
            b = (base >> k) & 1
        out |= b << k
        if not fallo and not decidido:
            pb, lb = (p >> k) & 1, (L >> k) & 1
            if pb != lb:
                if (pb > lb) == mayor_igual:
                    decidido = True
                else:
                    fallo = True
                    fallo_en = k
    return out


class Banda40E:
    """Banda 40 con la orden condicional: después de ver p(n-1), si la posición ya está en su
    objetivo y el precio quedó a lo más 'armado' niveles del umbral que la daría vuelta, envía
    la orden contraria condicionada al precio n. Al ver p(n) sabe si la orden salió (es función
    de p(n)) y actualiza su objetivo. Umbrales: 100 (comprar) en las fases A y C, 255 (vender) en
    la B, 140 y 215 en la D."""

    def __init__(self, armado=2):
        self.R = ideas.Regla(ideas.BandaD(140, 215))
        self.armado = armado
        self.pend = None
        self.cond = 0

    def decidir(self, p, caja, acc):
        R = self.R
        if self.pend is not None:
            base, L, ge = self.pend
            b = efectivo(base, L, ge, p)
            if (b >> 6) == 1 and (b & 63):
                R.q = C
            elif (b >> 6) == 2 and (b & 63):
                R.q = V
            self.pend = None
        d = R.decidir(p, caja, acc)
        q = R.q
        if R.tD >= 0:
            if q == C:
                base, L, ge = V, 215, True
            else:
                base, L, ge = C, 140, False
        elif R.vlo and not R.vhi:
            base, L, ge = V, HI, True
        else:
            base, L, ge = C, LO, False
        en_objetivo = (acc == 0) if base == C else ((caja - 5) // p == 0)
        if d == q and en_objetivo and abs(p - L) <= self.armado and not (ge and p >= L) and not (not ge and p <= L):
            self.pend = (base, L, ge)
            self.cond += 1
            return self.pend
        return d

    def info(self):
        return (self.cond,)


def correr_e(w, s, modo, com_cero=False, caja0=ideas.CAJA0, com=ideas.COMISION):
    """modo 'techo': la estrategia decide con p(n) y la orden se ejecuta a p(n).
    modo 'bits': la estrategia puede devolver (base, L, mayor_igual); se ejecuta efectivo(...) a p(n).
    com_cero: una orden de compra o venta con cantidad 0 paga la comisión (si la maestra lo hiciera)."""
    caja, acc, nord, d = caja0, 0, 0, M
    dec = s.decidir
    for p in w:
        if modo == "techo":
            d = dec(p, caja, acc)
        b = d
        if isinstance(b, tuple):
            b = efectivo(b[0], b[1], b[2], p)
        a = b >> 6
        if a == 1 or a == 2:
            q = b & 63
            if q == 0:
                if com_cero and caja >= com:
                    caja -= com
                    nord += 1
            elif a == 1:
                t = (caja - com) // p
                if q > t:
                    q = t
                if q > 0:
                    caja -= q * p + com
                    acc += q
                    nord += 1
            else:
                if q > acc:
                    q = acc
                if q > 0 and caja + q * p >= com:
                    caja += q * p - com
                    acc -= q
                    nord += 1
        if modo != "techo":
            d = dec(p, caja, acc)
    return caja + acc * w[-1], nord
