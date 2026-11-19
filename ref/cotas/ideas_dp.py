#!/usr/bin/env python3
"""ideas_dp.py: idea 1, política por programación dinámica (docs/exploracion_ideas.md).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Modelo (sin datos de Alpaca): en la fase D el precio es un paseo en 100..255 con pasos -1, 0 y
+1; en cada tick se mueve con probabilidad q, y queda condicionado a no salir del rango en lo que
queda de ronda (los dos extremos ya se vieron, así que el resto de la ventana está dentro).
Con h(x, k) = probabilidad de seguir dentro tras k movimientos,
  h(x, k) = (h(x-1, k-1) + h(x+1, k-1)) / 2,  h = 0 fuera del rango,  h(x, 0) = 1,
la probabilidad de subir desde x es u(x, k) = h(x+1, k-1) / (2 h(x, k)). Con las filas
normalizadas queda u = h(x+1, k-1) / (h(x-1, k-1) + h(x+1, k-1)). Los movimientos restantes
son k = q por ticks restantes.

Programación dinámica por tick, con posición en caja (0) o invertida (1). La orden decidida al
ver x se ejecuta al precio siguiente x' (el cambio x -> x' lo lleva la posición anterior) y un
cambio de posición cuesta c (dos órdenes de 5 sobre un patrimonio de 15 000).
  log:    V_r(x, s) = max_s' { -c [s' != s] + s E[L(x') - L(x)] + E[V_{r-1}(x', s')] },
          con la tabla entera L[x] = round(1024 log2 x).
  lineal: V_r(x, s) = max_s' { (1 - c [s' != s]) E[(x'/x)^s V_{r-1}(x', s')] }.
'log' usa la tabla entera L; 'log_exacto', log2 en punto flotante. Con la tabla entera, el
redondeo de L (medio punto en diferencias de 8 a 9 por nivel) pesa más que la ganancia esperada
por tick en el centro del rango y los conjuntos de compra y venta salen salpicados; por eso los
umbrales se toman como el intervalo contiguo de compra desde 100 y el de venta desde 255, y se
cuenta en cuántos ticks restantes la política no tiene esa forma.
Salida: umbral de compra a(r) (compra si x <= a) y de venta b(r) (vende si x >= b) para cada
número de ticks restantes r, en cuatro clases de volatilidad elegidas sin mirar datos: q de
1/8, 3/8, 5/8 y 7/8, con cortes en 1/4, 1/2 y 3/4 (en la placa, 4 nc contra n, con
desplazamientos). Versión de placa: 16 tramos de tiempo restante por las 4 clases.

Uso: python3 ref/cotas/ideas_dp.py   (unos 2 minutos; guarda las tablas en build/cotas/exploracion/
y escribe docs/mediciones/exploracion/dp_tablas.txt)
"""
import array
import json
import math
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

N = 156
LARGO = 20000
CLASES = (0.125, 0.375, 0.625, 0.875)
CORTES = (0.25, 0.5, 0.75)
TRAMOS = 16
W_REF = 15000
CACHE = os.path.join(comun.BUILD, "exploracion")
L = [0] + [round(1024 * math.log2(x)) for x in range(1, 256)]
LF = [0.0] + [1024 * math.log2(x) for x in range(1, 256)]
OBJETIVOS = ("log", "log_exacto", "lineal")


def subidas(kmax):
    """U[k][x] = probabilidad de subir desde 100 + x con k movimientos por delante (k >= 1)."""
    hh = [1.0] * N
    U = [None] * (kmax + 1)
    for k in range(1, kmax + 1):
        u = array.array("d", [0.0] * N)
        for x in range(N):
            a = hh[x - 1] if x > 0 else 0.0
            b = hh[x + 1] if x < N - 1 else 0.0
            u[x] = b / (a + b) if a + b > 0 else 0.5
        U[k] = u
        g = [((hh[x - 1] if x > 0 else 0.0) + (hh[x + 1] if x < N - 1 else 0.0)) * 0.5 for x in range(N)]
        m = max(g)
        hh = [v / m for v in g]
    return U


def politica(q, objetivo="log", T=LARGO, U=None):
    """Umbrales (a[r], b[r]) para r = 0..T-1 ticks restantes. a = -1 si nunca compra; b = 256 si nunca vende.
    Devuelve también cuántos r no tienen forma de umbral (conjunto de compra no es un intervalo bajo)."""
    kmax = max(1, int(round(q * T)))
    if U is None:
        U = subidas(kmax)
    c_log = 1024 * math.log2(1 + 10 / W_REF)
    c_lin = 10 / W_REF
    Lt = L if objetivo == "log" else LF
    V0 = [0.0] * N if objetivo != "lineal" else [1.0] * N
    V1 = list(V0)
    a_r, b_r = [-1] * T, [256] * T
    raros = 0
    p = [100 + x for x in range(N)]
    for r in range(1, T):
        k = max(1, int(round(q * r)))
        u = U[min(k, kmax)]
        nV0, nV1 = [0.0] * N, [0.0] * N
        compra, venta = [], []
        for x in range(N):
            ux = u[x]
            xa = x + 1 if x < N - 1 else x
            xb = x - 1 if x > 0 else x
            pu, pd = q * ux, q * (1 - ux)
            ps = 1 - pu - pd
            if objetivo != "lineal":
                e0 = ps * V0[x] + pu * V0[xa] + pd * V0[xb]
                e1 = ps * V1[x] + pu * V1[xa] + pd * V1[xb]
                g = pu * (Lt[p[xa]] - Lt[p[x]]) + pd * (Lt[p[xb]] - Lt[p[x]])
                # desde caja: quedarse (e0) o comprar (e1 - c); desde adentro: g + e1 o vender g + e0 - c
                nV0[x] = max(e0, e1 - c_log)
                nV1[x] = max(g + e1, g + e0 - c_log)
                compra.append(e1 - c_log > e0)
                venta.append(e0 - c_log > e1)
            else:
                e0 = ps * V0[x] + pu * V0[xa] + pd * V0[xb]
                e1 = ps * V1[x] + pu * V1[xa] + pd * V1[xb]
                f0 = (ps * V0[x] * p[x] + pu * V0[xa] * p[xa] + pd * V0[xb] * p[xb]) / p[x]
                f1 = (ps * V1[x] * p[x] + pu * V1[xa] * p[xa] + pd * V1[xb] * p[xb]) / p[x]
                nV0[x] = max(e0, (1 - c_lin) * e1)
                nV1[x] = max(f1, (1 - c_lin) * f0)
                compra.append((1 - c_lin) * e1 > e0)
                venta.append((1 - c_lin) * f0 > f1)
        V0, V1 = nV0, nV1
        # umbrales: el intervalo contiguo de compra desde 100 y el de venta desde 255
        a = -1
        while a + 1 < N and compra[a + 1]:
            a += 1
        b = N
        while b - 1 >= 0 and venta[b - 1]:
            b -= 1
        if sum(compra) != a + 1 or sum(venta) != N - b:
            raros += 1
        a_r[r] = a + 100 if a >= 0 else -1
        b_r[r] = b + 100 if b < N else 256
    a_r[0], b_r[0] = a_r[1], b_r[1]
    return a_r, b_r, raros


def _una(args):
    q, objetivo = args
    a, b, raros = politica(q, objetivo, U=_U)
    return q, objetivo, a, b, raros


_U = None


def tablas(forzar=False):
    """{objetivo: {'fino': [[(a,b) por r] por clase], 'placa': [[(a,b) por tramo] por clase], 'raros': [...]}}."""
    global _U
    ruta = os.path.join(CACHE, "dp_tablas.json")
    fuente = open(os.path.abspath(__file__), "rb").read()
    import hashlib
    clave = hashlib.sha256(fuente).hexdigest()[:16]
    if os.path.exists(ruta) and not forzar:
        d = json.load(open(ruta))
        if d.get("clave") == clave:
            return d
    _U = subidas(int(round(max(CLASES) * LARGO)))
    trabajos = [(q, o) for o in OBJETIVOS for q in CLASES]
    with Pool(len(trabajos)) as pool:
        res = pool.map(_una, trabajos)
    d = {"clave": clave}
    for o in OBJETIVOS:
        fino, placa, raros = [], [], []
        for q in CLASES:
            _, _, a, b, rr = next(x for x in res if x[0] == q and x[1] == o)
            fino.append([(a[r], b[r]) for r in range(LARGO)])
            ancho = LARGO // TRAMOS
            placa.append([(a[j * ancho + ancho // 2], b[j * ancho + ancho // 2]) for j in range(TRAMOS)])
            raros.append(rr)
        d[o] = {"fino": fino, "placa": placa, "raros": raros}
    os.makedirs(CACHE, exist_ok=True)
    json.dump(d, open(ruta, "w"))
    return d


_MEMO = {}


def comportamiento(objetivo="log", version="placa", modo="cambios"):
    import ideas
    k = (objetivo, version)
    if k not in _MEMO:
        _MEMO[k] = tablas()[objetivo][version]
    t = _MEMO[k]
    return ideas.DPD(t, CORTES, TRAMOS if version == "placa" else LARGO, modo)


def main():
    d = tablas()
    sal = os.path.join(comun.RAIZ, "docs", "mediciones", "exploracion")
    os.makedirs(sal, exist_ok=True)
    Lin = ["Idea 1: umbrales de la programacion dinamica (ref/cotas/ideas_dp.py). Modelo sin datos: paseo de -1, 0, +1",
           "en 100..255 condicionado a no salir del rango; q = probabilidad de moverse por tick. Compra si p <= a, vende si",
           "p >= b. Tabla de placa: 16 tramos de ticks restantes (tramo 15 = principio de la ronda) por 4 clases de q.", ""]
    for o in OBJETIVOS:
        Lin.append(f"== objetivo {o}; ticks restantes sin forma de umbral, por clase: {d[o]['raros']}")
        Lin.append("tramo (ticks restantes)   " + "  ".join(f"q={q:5.3f} a/b" for q in CLASES))
        for j in range(TRAMOS - 1, -1, -1):
            Lin.append(f"{j:2d} ({j * 1250:5d}-{(j + 1) * 1250 - 1:5d})       "
                       + "  ".join(f"{d[o]['placa'][c][j][0]:5d}/{d[o]['placa'][c][j][1]:<5d}" for c in range(4)))
        Lin.append("")
    texto = "\n".join(Lin) + "\n"
    open(os.path.join(sal, "dp_tablas.txt"), "w").write(texto)
    print(texto, end="")


if __name__ == "__main__":
    main()
