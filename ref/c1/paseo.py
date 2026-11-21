#!/usr/bin/env python3
"""paseo.py: el modelo del paseo normalizado y su programación dinámica, para las tablas de C1.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Es el cálculo de ref/cotas/paseo_optimo.py de la rama minutos-reales (commit 17d7284,
docs/exploracion_ideas.md, sección 13), copiado sin cambiar ninguna operación: nucleo, la
recurrencia de las probabilidades y la programación dinámica. Lo único distinto es que dp() no
guarda la tabla completa en disco: devuelve las filas (ticks restantes r) que se le piden, que son
las que usa la tabla comprimida de la placa (ref/c1/tablas.py).

Modelo: el precio normalizado es un paseo en los enteros 100..255 con pasos de una gaussiana
discretizada de varianza v^2 por tick, condicionado a que su mínimo sea 100 y su máximo 255 en la
ronda de 20 000 ticks. No usa ningún precio guardado: todo sale de v^2, del largo de la ronda, de
la comisión relativa (COSTO) y de los niveles 100 y 255.
"""
import array
import math
from operator import mul

LO, HI = 100, 255
L = HI - LO + 1          # 156 niveles
N = 20000
V2S = (0.125, 0.25, 0.375, 0.5, 0.75, 1.0, 1.5, 2.0)


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


# --- programación dinámica ---------------------------------------------------------------------

LOGL = [math.log(LO + i) for i in range(L)]
COSTO = 10 / 15000      # un cambio completo de posición: dos órdenes de 5 sobre un patrimonio de 15 000
VARIANTES = {"V1": ("A",), "V2": ("A", "B", "C", "D"), "V3": ("A",), "B40": ()}
POS = {"V1": (0.0, 1.0), "V2": (0.0, 1.0), "V3": (0.0, 0.5, 1.0), "B40": (0.0, 1.0)}
FASES = "ABCD"
RANGO = {"A": (1, L - 1), "B": (0, L - 1), "C": (1, L), "D": (0, L)}


def fija(F, i, s, nS):
    """Política fija fuera de las fases optimizadas: B invertido, C en caja, D banda 40, A mantener."""
    if F == "B":
        return nS - 1
    if F == "C":
        return 0
    if F == "D":
        x = LO + i
        return nS - 1 if x <= 140 else 0 if x >= 215 else s
    return s


def dp(args):
    """Programación dinámica sobre el paseo condicionado para un v^2 de la grilla. La posición s
    (fracción invertida) es la que viaja de x al precio siguiente y; la elegida s' se ejecuta en y.
      log:    V_F(x, r, s) = max_s' { log(1 - s + s y/x) en esperanza + costo(s, s') + E[V_F'(y, r-1, s')] }
      lineal: V_F(x, r, s) = max_s' { (1 - costo) E[(1 - s + s y/x) V_F'(y, r-1, s')] }
    con la esperanza bajo P(x -> y | condición) = K(y - x) g_F'(y, r - 1) / g_F(x, r). Guarda, para
    las fases optimizadas, s' por (r, x, s), y el valor en r = N - 1.
    args = (variante, objetivo, j, filas): devuelve {fase: {r: bytes de s' por (x, s)}} solo para los r de filas."""
    variante, objetivo, j, filas = args
    K = nucleo(V2S[j])
    m = max(abs(k) for k, _ in K)
    ps = [p for _, p in K]
    w = len(ps)
    pos = POS[variante]
    nS = len(pos)
    opt = VARIANTES[variante]
    log = objetivo == "log"
    V0 = 0.0 if log else 1.0
    cst = [[(math.log(1 - abs(a - b) * COSTO) if log else 1 - abs(a - b) * COSTO) for b in pos] for a in pos]
    pad = [0.0] * m
    LOGP = pad + LOGL + pad
    YP = pad + [float(LO + i) for i in range(L)] + pad
    H = {si: [[math.log(1 - sv + sv * (LO + i + k) / (LO + i)) for k in range(-m, m + 1)] for i in range(L)]
         for si, sv in enumerate(pos) if 0 < sv < 1}
    gD, gB, gC, gA = [1.0] * L, [0.0] * L, [0.0] * L, [0.0] * L
    V = {F: [[V0] * L for _ in pos] for F in FASES}
    tab = {F: bytearray(N * L * nS) for F in opt}

    def ext(F, rowF, B0, C155, D0, D155):
        if F == "D":
            return pad + rowF + pad
        if F == "B":
            return pad + rowF[:L - 1] + [D155] + pad
        if F == "C":
            return pad + [D0] + rowF[1:] + pad
        return pad + [B0] + rowF[1:L - 1] + [C155] + pad

    for r in range(1, N):
        g = {"A": gA, "B": gB, "C": gC, "D": gD}
        e = {F: ext(F, g[F], gB[0], gC[L - 1], gD[0], gD[L - 1]) for F in FASES}
        ev = {F: [ext(F, V[F][sp], V["B"][sp][0], V["C"][sp][L - 1], V["D"][sp][0], V["D"][sp][L - 1])
                  for sp in range(nS)] for F in FASES}
        nuevo_g, nuevo_V = {}, {}
        for F in FASES:
            eF = e[F]
            pV = [[a * b for a, b in zip(eF, ev[F][sp])] for sp in range(nS)]
            if log:
                pL = [a * b for a, b in zip(eF, LOGP)]
            else:
                pY = [[a * b for a, b in zip(pV[sp], YP)] for sp in range(nS)]
            i0, i1 = RANGO[F]
            gF = [0.0] * L
            VF = [[V0] * L for _ in range(nS)]
            optF = F in opt
            tF = tab.get(F)
            for i in range(i0, i1):
                gi = sum(map(mul, ps, eF[i:i + w]))
                gF[i] = gi
                if gi <= 0.0:
                    for s in range(nS):
                        sp = fija(F, i, s, nS)
                        VF[s][i] = V[F][s][i]
                        if optF:
                            tF[(r * L + i) * nS + s] = sp
                    continue
                E2 = [sum(map(mul, ps, pV[sp][i:i + w])) / gi for sp in range(nS)]
                if log:
                    r1 = sum(map(mul, ps, pL[i:i + w])) / gi - LOGL[i]
                    E1 = []
                    for s, sv in enumerate(pos):
                        if sv == 0.0:
                            E1.append(0.0)
                        elif sv == 1.0:
                            E1.append(r1)
                        else:
                            E1.append(sum(map(mul, map(mul, ps, eF[i:i + w]), H[s][i])) / gi)
                else:
                    Bq = [sum(map(mul, ps, pY[sp][i:i + w])) / gi / (LO + i) for sp in range(nS)]
                for s in range(nS):
                    if optF:
                        mejor, msp = None, s
                        for sp in range(nS):
                            if log:
                                val = E1[s] + cst[s][sp] + E2[sp]
                            else:
                                val = cst[s][sp] * ((1 - pos[s]) * E2[sp] + pos[s] * Bq[sp])
                            if mejor is None or val > mejor + 1e-15:
                                mejor, msp = val, sp
                        tF[(r * L + i) * nS + s] = msp
                        VF[s][i] = mejor
                    else:
                        sp = fija(F, i, s, nS)
                        if log:
                            VF[s][i] = E1[s] + cst[s][sp] + E2[sp]
                        else:
                            VF[s][i] = cst[s][sp] * ((1 - pos[s]) * E2[sp] + pos[s] * Bq[sp])
            nuevo_g[F], nuevo_V[F] = gF, VF
        gA, gB, gC, gD = nuevo_g["A"], nuevo_g["B"], nuevo_g["C"], nuevo_g["D"]
        V = nuevo_V
    return {F: {r: bytes(tab[F][r * L * nS:(r + 1) * L * nS]) for r in filas} for F in opt}
