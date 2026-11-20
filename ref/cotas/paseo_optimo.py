#!/usr/bin/env python3
"""paseo_optimo.py: el paseo normalizado como modelo exacto del juego (docs/exploracion_ideas.md, sección 13).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Modelo (diseño de Nicolás del 19/11, "la política óptima del paseo normalizado"): el precio
normalizado es un paseo en los enteros 100..255 con pasos de una gaussiana discretizada de
varianza v^2 por tick, condicionado a que su mínimo sea 100 y su máximo 255 en la ventana. En cada
tick basta con el precio x, la fase y los ticks restantes r:

  g_D(x, r)  no salir de [100, 255] en los r pasos que quedan
  g_B(x, r)  tocar 255 sin salir (el 100 ya se vio)
  g_C(x, r)  tocar 100 sin salir (el 255 ya se vio)
  g_A(x, r)  tocar 100 y 255 sin salir
  h_A(x, r)  lo mismo que g_A, con el 255 antes que el 100

Recurrencia hacia atrás en r: g_F(x, r) = suma_y K(y - x) g_F'(y, r - 1), donde F' es la fase a la
que lleva y (tocar 100 desde A lleva a B, tocar 255 a C, y desde B o C se pasa a D), y fuera de
[100, 255] vale 0. g_F(x, 0) = 1 solo en D. La probabilidad del siguiente paso dado todo lo que
se sabe es K(y - x) g_F'(y, r - 1) / g_F(x, r), y la de que el 255 llegue primero estando en A es
h_A / g_A.

Núcleo: P(k) proporcional a exp(-k^2 / (2 s^2)) en los enteros, con s elegido para que la varianza
de la distribución discreta sea exactamente v^2 (con v chico, discretizar con s = v da mucha menos
varianza: con v^2 = 1/8 daría 0,035).
v^2 en {1/8, 1/4, 3/8, 1/2, 3/4, 1, 3/2, 2}: es la varianza de largo plazo por tick, la que manda
en cuándo se tocan los extremos.

Uso: python3 ref/cotas/paseo_optimo.py prueba   (compara g con paseos de la red simulados)
"""
import array
import math
import os
import random
import sys
from multiprocessing import Pool
from operator import mul

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

LO, HI = 100, 255
L = HI - LO + 1          # 156 niveles
N = 20000
V2S = (0.125, 0.25, 0.375, 0.5, 0.75, 1.0, 1.5, 2.0)
CACHE = os.path.join(comun.BUILD, "optimo")
# Las tablas .bin de build/cotas/optimo/ las escribe solo este módulo en la máquina local.


def nucleo(v2, corte=1e-13):
    """Lista de (k, P(k)) simétrica, varianza exacta v2."""
    def tabla(s):
        K = int(10 * s) + 3
        w = [math.exp(-k * k / (2 * s * s)) for k in range(-K, K + 1)]
        Z = sum(w)
        return [(k, x / Z) for k, x in zip(range(-K, K + 1), w)]

    def var(s):
        return sum(k * k * p for k, p in tabla(s))

    a, b = 0.05, 10.0
    for _ in range(200):
        m = (a + b) / 2
        if var(m) < v2:
            a = m
        else:
            b = m
    t = [(k, p) for k, p in tabla((a + b) / 2) if p > corte]
    Z = sum(p for _, p in t)
    t = [(k, p / Z) for k, p in t]
    # ajuste fino de la varianza tras el corte: se mezcla con la masa en 0
    return t


def _fila(ps, e, i0, i1, m):
    """Convolución de la fila extendida e (con margen m a cada lado) para los índices i0..i1-1."""
    w = len(ps)
    return [sum(map(mul, ps, e[i:i + w])) for i in range(i0, i1)]


def recurrencia(v2, guardar=("pA",), rmax=N - 1, cada_r=None):
    """Recorre r = 0..rmax. Si cada_r no es None, se llama cada_r(r, gD, gB, gC, gA, hA) en cada r
    (filas de 156 valores; índice i = nivel - 100). Devuelve dict con las tablas pedidas:
    'pA' = h_A / g_A (float32, (rmax + 1) x 156, NaN donde g_A = 0 o fuera de la fase A)."""
    K = nucleo(v2)
    m = max(abs(k) for k, _ in K)
    ps = [p for _, p in K]
    pad = [0.0] * m
    gD = [1.0] * L
    gB = [0.0] * L
    gC = [0.0] * L
    gA = [0.0] * L
    hA = [0.0] * L
    out = {k: array.array("f") for k in guardar}
    nan = float("nan")

    def guarda():
        if "pA" in out:
            out["pA"].extend([nan] + [(hA[i] / gA[i]) if gA[i] > 0 else nan for i in range(1, L - 1)] + [nan])
        if "gA" in out:
            out["gA"].extend(gA)

    if cada_r:
        cada_r(0, gD, gB, gC, gA, hA)
    guarda()
    for r in range(1, rmax + 1):
        eD = pad + gD + pad
        eB = pad + gB[:L - 1] + [gD[L - 1]] + pad
        eC = pad + [gD[0]] + gC[1:] + pad
        eA = pad + [gB[0]] + gA[1:L - 1] + [gC[L - 1]] + pad
        eH = pad + [0.0] + hA[1:L - 1] + [gC[L - 1]] + pad
        gD = _fila(ps, eD, 0, L, m)
        gB = _fila(ps, eB, 0, L - 1, m) + [0.0]
        gC = [0.0] + _fila(ps, eC, 1, L, m)
        gA = [0.0] + _fila(ps, eA, 1, L - 1, m) + [0.0]
        hA = [0.0] + _fila(ps, eH, 1, L - 1, m) + [0.0]
        if cada_r:
            cada_r(r, gD, gB, gC, gA, hA)
        guarda()
    return out


def ruta_pA(j):
    return os.path.join(CACHE, f"pA_{j}.bin")


def _calcular_pA(j):
    ruta = ruta_pA(j)
    if not os.path.exists(ruta):
        os.makedirs(CACHE, exist_ok=True)
        t = recurrencia(V2S[j])["pA"]
        with open(ruta + ".tmp", "wb") as f:
            t.tofile(f)
        os.replace(ruta + ".tmp", ruta)
    return j


def tablas_pA(procesos=8):
    """P(255 antes que 100 | fase A, x, r) para cada v^2 de la grilla: lista de array('f') (r * 156 + i)."""
    falta = [j for j in range(len(V2S)) if not os.path.exists(ruta_pA(j))]
    if falta:
        with Pool(min(procesos, len(falta))) as pool:
            pool.map(_calcular_pA, falta)
    T = []
    for j in range(len(V2S)):
        a = array.array("f")
        with open(ruta_pA(j), "rb") as f:
            a.fromfile(f, N * L)
        T.append(a)
    return T


def p255(T, v2, x, r):
    """Interpolación lineal en v^2 entre las dos tablas vecinas (fuera de la grilla, la del borde)."""
    if v2 <= V2S[0]:
        return T[0][r * L + x - LO]
    if v2 >= V2S[-1]:
        return T[-1][r * L + x - LO]
    j = 0
    while V2S[j + 1] < v2:
        j += 1
    a, b = T[j][r * L + x - LO], T[j + 1][r * L + x - LO]
    f = (v2 - V2S[j]) / (V2S[j + 1] - V2S[j])
    return a + f * (b - a)


# --- prueba del cálculo: paseos de la red simulados -------------------------------------------------

def _mc(args):
    v2, x0, r, n, semilla = args
    K = nucleo(v2)
    ks = [k for k, _ in K]
    cum = []
    c = 0.0
    for _, p in K:
        c += p
        cum.append(c)
    rng = random.Random(semilla)
    import bisect
    cuenta = {"A": 0, "H": 0, "D": 0}
    for _ in range(n):
        x, v100, v255, primero, fuera = x0, False, False, None, False
        for _ in range(r):
            x += ks[bisect.bisect_left(cum, rng.random())]
            if x < LO or x > HI:
                fuera = True
                break
            if x == LO and not v100:
                v100 = True
                primero = primero or "100"
            if x == HI and not v255:
                v255 = True
                primero = primero or "255"
        if not fuera:
            cuenta["D"] += 1
            if v100 and v255:
                cuenta["A"] += 1
                cuenta["H"] += primero == "255"
    return cuenta


def prueba(procesos=None):
    """g_A, h_A y g_D contra paseos de la red sin condicionar, para algunos (v^2, x, r) cortos."""
    casos = [(2.0, 150, 400), (1.0, 120, 800), (2.0, 177, 6000), (1.0, 130, 8000), (0.5, 200, 12000)]
    n, partes = 24000, 24
    out = []
    for v2, x0, r in casos:
        res = {}

        def cb(rr, gD, gB, gC, gA, hA):
            if rr == r:
                res.update(D=gD[x0 - LO], A=gA[x0 - LO], H=hA[x0 - LO])
        recurrencia(v2, guardar=(), rmax=r, cada_r=cb)
        with Pool(procesos or os.cpu_count()) as pool:
            cs = pool.map(_mc, [(v2, x0, r, n // partes, f"mc-{v2}-{x0}-{r}-{k}") for k in range(partes)])
        tot = {k: sum(c[k] for c in cs) for k in ("A", "H", "D")}
        lin = (f"v2 {v2}, x {x0}, r {r}: g_D {res['D']:.4f} contra {tot['D'] / n:.4f}; g_A {res['A']:.4f} contra "
               f"{tot['A'] / n:.4f}; h_A {res['H']:.4f} contra {tot['H'] / n:.4f} ({n} paseos)")
        print(lin)
        out.append(lin)
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "prueba":
        prueba()
