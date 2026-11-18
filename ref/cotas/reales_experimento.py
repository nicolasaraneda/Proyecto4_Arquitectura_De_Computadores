#!/usr/bin/env python3
"""reales_experimento.py: paso 5 del protocolo (docs/cotas.md, sección 5) con minutos reales.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Población: todas las ventanas de 20 000 minutos seguidos de META, AAPL, NFLX, AMD y TSLA
entre 2022 y 2024 (sesión regular, minutos de Alpaca), cada una normalizada entre 100 y 255
con su mínimo y su máximo, como data/practica_meta.csv (ref/cotas/reales.py comprobar).
Es la misma población del 17/11 con los minutos reales en vez de los minutos modelados;
el largo es 20 000 porque el 18/11 se supo que cada ronda dura 20 000 ticks.

Ventanas vecinas comparten casi todos sus precios: con 20 000 minutos de largo, cada
empresa tiene unas 15 ventanas que no se solapan. Por eso, además de todas las ventanas,
se informa el resultado por empresa y por año, y la separación de ajuste y validación.

Casos (mismas definiciones que experimento.py):
  a, b, c  variantes de inicio, banda después de ver los dos extremos y márgenes
  selección por años (ajuste: empiezan en 2022 o 2023; validación: enteras en 2024) y por
           empresa (ajuste: META, AAPL, NFLX; validación: AMD, TSLA)
  e        torneo contra campos de rivales; el campo con extremos incluye desde el 18/11 al
           rival que ganó la ronda de Tesla en la clase (unavez 100 220: compra al ver 100,
           vende con 220 o más y no vuelve a entrar)
El caso d (la ronda como trozo de una ventana más larga) no se repite: la captura de la
ronda de Tesla del 18/11 toca 100 y 255 en sus 20 000 precios.

Uso: python3 ref/cotas/reales_experimento.py [--datos CARPETA]   (unos 5 minutos con 24 núcleos)
Salidas en docs/mediciones/cotas_reales/.
"""
import argparse
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402
import experimento as ex  # noqa: E402
import reales  # noqa: E402

SALIDA = os.path.join(comun.RAIZ, "docs", "mediciones", "cotas_reales")
LARGO = reales.LARGO
BANDAS = (10, 20, 30, 35, 40, 45, 50, 55, 60, 65, 70, 73, 76)
TECHOS = (200, 210, 215, 220, 225, 230, 240, 250)


def estrategias():
    v = list(ex.BASE) + ex.variantes()
    nombres = {e[0] for e in v}
    for w in BANDAS:
        if f"espera_banda{w}" not in nombres:
            v.append(ex.C(f"espera_banda{w}", 0, banda=w))
    v += [(f"unavez100_{h}", "unavez", (100, h)) for h in TECHOS]
    return v


ESTR = estrategias()
NOM = [e[0] for e in ESTR]
J = {n: j for j, n in enumerate(NOM)}
CAMPO_SIN = list(ex.CAMPO_SIN)
CAMPO_COTAS = list(ex.CAMPO_COTAS) + ["unavez100_220"]
RIVAL_TESLA = "unavez100_220"
CLAVE = ["nada", "siempre", "max_media", "zscore", "espera", "compra", "parte20", "umbral170",
         "espera_banda20", "espera_banda40", "espera_banda50", "espera_banda60", "espera_banda70", "espera_banda76",
         "compra_banda40", "compra_banda60", "parte20_banda70", "espera_a2", "espera_b2", "espera_a2_b2_banda60",
         "unavez100_200", "unavez100_220", "unavez100_240"]


class Pob:
    """Resultados de todas las ventanas de una empresa."""

    def __init__(self, emp, r, fechas):
        self.emp, self.r, self.fechas = emp, r, fechas
        self.nv, self.ne = r["nv"], r["ne"]
        self.mv = memoryview(r["w"])

    def col(self, j, idx=None):
        c = self.mv[j::self.ne]
        return c if idx is None else [c[i] for i in idx]

    def anio_ini(self, v):
        return int(self.fechas[self.r["ini"][v]][:4])

    def anio_fin(self, v):
        return int(self.fechas[self.r["ini"][v] + LARGO - 1][:4])


def resumen(cols, cols_ref):
    """cols: lista de columnas (una por empresa) de una estrategia; cols_ref: dict nombre -> columnas."""
    w = sorted(x for c in cols for x in c)
    n = len(w)
    out = dict(n=n, media=sum(w) / n, p5=w[int(0.05 * (n - 1))], peor=w[0], mediana=w[n // 2],
               gana_nada=sum(1 for x in w if x > 10000) / n)
    for k, cr in cols_ref.items():
        out[k] = sum(1 for c, r in zip(cols, cr) for a, b in zip(c, r) if a > b) / n
    return out


CAB = (f"{'estrategia':24s} {'media':>8s} {'mediana':>8s} {'p5':>7s} {'peor':>7s} {'>nada':>6s} "
       f"{'>c y m':>6s} {'>max_m':>6s}")


def linea(n, r):
    return (f"{n:24s} {r['media']:8.0f} {r['mediana']:8d} {r['p5']:7d} {r['peor']:7d} {100 * r['gana_nada']:6.1f} "
            f"{100 * r['siempre']:6.1f} {100 * r['max_media']:6.1f}")


def tabla(titulo, pobs, idxs, nombres):
    """idxs: lista (una por empresa) de índices de ventana, o None para todas."""
    def cols(n):
        return [p.col(J[n], i) for p, i in zip(pobs, idxs)]
    ref = {"siempre": cols("siempre"), "max_media": cols("max_media")}
    total = sum(p.nv if i is None else len(i) for p, i in zip(pobs, idxs))
    L = ["", f"== {titulo} ({total} ventanas)", CAB]
    for n in nombres:
        L.append(linea(n, resumen(cols(n), ref)))
    return L


def medias(pobs, idxs, nombres):
    out = {}
    for n in nombres:
        s = c = 0
        for p, i in zip(pobs, idxs):
            col = p.col(J[n], i)
            s += sum(col)
            c += len(col)
        out[n] = s / c
    return out


def meseta(m, nombres):
    mejor = max(nombres, key=lambda n: m[n])
    dentro = [n for n in nombres if m[n] >= 0.98 * m[mejor]]
    return mejor, dentro


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--datos", default=None)
    a = ap.parse_args(argv)
    carpeta = reales.carpeta_datos(a.datos)
    os.makedirs(SALIDA, exist_ok=True)
    pobs = []
    for emp in reales.EMPRESAS:
        print(f"{emp}: {len(ESTR)} estrategias en todas las ventanas de {LARGO}...", file=sys.stderr)
        fechas, _, _ = reales.leer_sesion(carpeta, emp)
        pobs.append(Pob(emp, reales.correr(ESTR, carpeta, emp), fechas))
    todas = [None] * len(pobs)
    sin_solapar = [list(range(0, p.nv, LARGO)) for p in pobs]

    # --- a, b, c: variantes
    L = ["Paso 5 con minutos reales: todas las ventanas de 20 000 minutos de las cinco empresas, 2022 a 2024",
         "(ref/cotas/reales_experimento.py). Patrimonio final desde 10 000, comision 5. '>nada', '>c y m' y '>max_m':",
         "porcentaje de ventanas en que la estrategia termina sobre no operar, sobre comprar 63 siempre y sobre max_media.",
         "Ventanas por empresa: " + ", ".join(f"{p.emp} {p.nv}" for p in pobs) + ".",
         "Ventanas vecinas comparten casi todos sus precios: 'sin solapar' toma una de cada 20 000 desde el inicio."]
    L += tabla("todas las ventanas, cinco empresas", pobs, todas, CLAVE)
    L += tabla("sin solapar, cinco empresas", pobs, sin_solapar, CLAVE)
    for p in pobs:
        L += tabla(f"{p.emp}, todas sus ventanas", [p], [None], CLAVE)
    for anio in (2022, 2023, 2024):
        idx = [[v for v in range(p.nv) if p.anio_ini(v) == anio] for p in pobs]
        L += tabla(f"ventanas que empiezan en {anio}", pobs, idx, CLAVE)
    open(os.path.join(SALIDA, "variantes.txt"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))

    # --- banda: meseta de w después de ver los dos extremos
    esp = [f"espera_banda{w}" for w in BANDAS]
    com = [f"compra_banda{w}" for w in (10, 20, 30, 40, 50, 60, 65, 70, 73, 76)]
    B = ["Banda despues de ver los dos extremos (compra con p <= 100 + w, vende con p >= 255 - w), minutos reales.",
         "Patrimonio medio por w; 'meseta': las w a menos del 2 % de la mejor. Todas las ventanas de 20 000.", ""]
    cortes = [("cinco empresas", pobs, todas)]
    cortes += [(p.emp, [p], [None]) for p in pobs]
    cortes += [(f"empiezan en {y}", pobs, [[v for v in range(p.nv) if p.anio_ini(v) == y] for p in pobs])
               for y in (2022, 2023, 2024)]
    B.append(f"{'corte':18s} " + " ".join(f"{w:>6d}" for w in BANDAS) + "   mejor  meseta")
    for nombre, ps, ix in cortes:
        m = medias(ps, ix, esp + ["espera"])
        mejor, dentro = meseta(m, esp)
        ws = [int(n[len('espera_banda'):]) for n in dentro]
        B.append(f"{nombre:18s} " + " ".join(f"{m[n]:6.0f}" for n in esp)
                 + f"   w={mejor[len('espera_banda'):]:>3s}  {min(ws)} a {max(ws)}  (sin banda {m['espera']:.0f})")
    B += ["", "Con inicio 'compra':", f"{'corte':18s} " + " ".join(f"{n[len('compra_banda'):]:>6s}" for n in com)]
    for nombre, ps, ix in cortes[:1]:
        m = medias(ps, ix, com)
        B.append(f"{nombre:18s} " + " ".join(f"{m[n]:6.0f}" for n in com))
    open(os.path.join(SALIDA, "banda.txt"), "w").write("\n".join(B) + "\n")
    print("\n".join(B))

    # --- selección con ajuste y validación
    base = {b[0] for b in ex.BASE}
    candidatas = [n for n in NOM if n not in base and not n.startswith("unavez")]
    S = ["Seleccion con separacion de ajuste y validacion, minutos reales, ventanas de 20 000",
         "(ref/cotas/reales_experimento.py). Se elige la variante de cotas con mayor patrimonio medio en el ajuste",
         "y se informa en la validacion junto con sus vecinas y las de referencia. La familia del rival (unavez)",
         "no es candidata: se informa aparte."]
    seps = (("por anos (ajuste: empiezan en 2022-2023; validacion: enteras en 2024)",
             lambda p, v: p.anio_ini(v) in (2022, 2023), lambda p, v: p.anio_ini(v) == 2024 and p.anio_fin(v) == 2024),
            ("por empresa (ajuste META AAPL NFLX, validacion AMD TSLA)",
             lambda p, v: p.emp in ("META", "AAPL", "NFLX"), lambda p, v: p.emp in ("AMD", "TSLA")))
    for nombre_sep, aj, va in seps:
        ia = [[v for v in range(p.nv) if aj(p, v)] for p in pobs]
        iv = [[v for v in range(p.nv) if va(p, v)] for p in pobs]
        m = medias(pobs, ia, candidatas)
        orden = sorted(candidatas, key=lambda n: -m[n])
        mejor = orden[0]
        mb, dentro = meseta(m, [f"espera_banda{w}" for w in BANDAS])
        S += ["", f"== {nombre_sep}: ajuste {sum(map(len, ia))} ventanas, validacion {sum(map(len, iv))}",
              "   cinco mejores en el ajuste: " + ", ".join(f"{n} {m[n]:.0f}" for n in orden[:5]),
              f"   mejor banda con 'espera' en el ajuste: {mb}; meseta (2 %): "
              + ", ".join(n[len('espera_banda'):] for n in dentro)]
        vecinas = [x for x in ("espera_banda40", "espera_banda50", "espera_banda60", "espera_banda70", "espera_banda76",
                               "parte20_banda70", "compra", "espera", "compra_banda40", "unavez100_220", "max_media",
                               "siempre", "nada") if x != mejor]
        S += ["   en la validacion:"]
        S += ["   " + x for x in tabla("validacion", pobs, iv, [mejor] + vecinas)[1:]]
    open(os.path.join(SALIDA, "seleccion.txt"), "w").write("\n".join(S) + "\n")
    print("\n".join(S))

    # --- torneo (una ventana de cada 39 minutos: 10 por día)
    filas = []
    for p in pobs:
        for v in range(0, p.nv, 39):
            filas.append([p.mv[v * p.ne + j] for j in range(p.ne)])
    campos = {"sin extremos": (0.0, False), "un tercio con extremos": (1 / 3, False),
              "dos tercios con extremos": (2 / 3, False), "rival de Tesla y dos tercios": (2 / 3, True)}
    T = ["Caso e: torneo con minutos reales. En cada ronda, 9 rivales sorteados del campo; puntos lineales entre",
         "el peor y el mejor de la ronda (0 a 1) y porcentaje de rondas en primer lugar.",
         f"{len(filas)} rondas: una ventana de 20 000 cada 39 minutos de cada empresa.",
         "Campos: 'sin extremos' (" + ", ".join(CAMPO_SIN) + "); con extremos, sorteados de: " + ", ".join(CAMPO_COTAS) + ".",
         "'rival de Tesla y dos tercios': uno de los 9 es siempre unavez100_220 (el rival que gano la ronda de Tesla",
         "del 18/11) y los otros 8 se sortean del campo con dos tercios con extremos.", "",
         f"{'estrategia':24s}" + "".join(f"{c:>32s}" for c in campos)]
    for n in CLAVE:
        celdas = []
        for c, (frac, fijo) in campos.items():
            rng = random.Random(f"torneo-reales-{c}")
            pts, pri = [], 0
            for f in filas:
                riv = [f[J[RIVAL_TESLA]]] if fijo else []
                while len(riv) < 9:
                    riv.append(f[J[rng.choice(CAMPO_COTAS if rng.random() < frac else CAMPO_SIN)]])
                todos = riv + [f[J[n]]]
                lo, hi = min(todos), max(todos)
                pts.append(0.5 if hi == lo else (f[J[n]] - lo) / (hi - lo))
                pri += f[J[n]] >= hi
            celdas.append(f"{st.mean(pts):8.3f} pts {100 * pri / len(filas):5.1f} % 1o")
        T.append(f"{n:24s}" + "".join(f"{c:>32s}" for c in celdas))
    open(os.path.join(SALIDA, "torneo.txt"), "w").write("\n".join(T) + "\n")
    print("\n".join(T))

    # --- cara a cara: la regla de los peldaños contra el rival de Tesla y las alternativas
    pares = [("espera_banda60", RIVAL_TESLA), ("espera_banda60", "espera"), ("espera_banda60", "parte20_banda70"),
             ("espera_banda60", "espera_banda70"), ("espera_banda60", "espera_banda40")]
    K = ["Cara a cara en todas las ventanas de 20 000: porcentaje de ventanas en que A termina sobre B, empates",
         "y diferencia media A - B (ref/cotas/reales_experimento.py).", ""]
    for a_, b_ in pares:
        K.append(f"== {a_} contra {b_}")
        for nombre, ps in [("cinco empresas", pobs)] + [(p.emp, [p]) for p in pobs]:
            gana = emp_ = n = 0
            dif = 0
            for p in ps:
                ca, cb = p.col(J[a_]), p.col(J[b_])
                for x, y in zip(ca, cb):
                    gana += x > y
                    emp_ += x == y
                    dif += x - y
                n += p.nv
            K.append(f"   {nombre:15s} A gana {100 * gana / n:5.1f} %  empata {100 * emp_ / n:5.1f} %  "
                     f"pierde {100 * (n - gana - emp_) / n:5.1f} %  diferencia media {dif / n:+8.0f}")
    open(os.path.join(SALIDA, "cara_a_cara.txt"), "w").write("\n".join(K) + "\n")
    print("\n".join(K))

    # --- orden de los extremos: cuántas ventanas ven primero el 100
    O = ["Orden de los extremos en las ventanas de 20 000 (primer 100 y primer 255 de cada ventana)", ""]
    for p in pobs:
        antes = sum(1 for v in range(p.nv) if p.r["pmin"][v] < p.r["pmax"][v])
        O.append(f"{p.emp:5s} el 100 aparece antes que el 255 en {100 * antes / p.nv:5.1f} % de {p.nv} ventanas")
    open(os.path.join(SALIDA, "extremos.txt"), "w").write("\n".join(O) + "\n")
    print("\n".join(O))


if __name__ == "__main__":
    main()
