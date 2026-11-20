#!/usr/bin/env python3
"""explorar_clon.py: la vara de medir contra un clon de la banda 40 (docs/exploracion_ideas.md, sección 14).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El rival de referencia pasa a ser un grupo que corre la banda 40 o una banda parecida. Con el
puntaje lineal (2 al mejor, 0 al peor), ganarle a un clon no suma y quedar debajo resta. Las
métricas son de torneos de 3 rondas mano a mano contra un rival R, comparando el promedio de las
tres rondas:
  gana     promedio propio - promedio de R >= 10
  empata   |diferencia| < 10
  pierde   diferencia <= -10
  déficit  media de max(0, promedio de R - promedio propio)
  p5 y peor caso de la diferencia
Rivales: banda 40 exacta y bandas 30, 50 y 60. Solo las 100 acciones ajenas (las "otras" de la
sección 12, 12 000 ventanas), en total y por año de inicio. Las cinco empresas no se usan.

Errores estándar. Un torneo es una función de tres ventanas sorteadas, así que cada métrica es
un estadístico U de orden 3. Su parte lineal es (3 / n) suma h1(i), con h1(i) la media de
(f - m) en los torneos que usan la ventana i; h1 se estima con los mismos sorteos (unas 50 a 125
apariciones por ventana, lo que agranda un poco el error: queda del lado conservador). Esas
contribuciones se agrupan como en la sección 12 (explorar_regimen.ee_contrib): bloques de 20 y
60 días de la fecha de inicio y dos sentidos, fecha y empresa; se informa el mayor.

Uso (con export P4_DATOS=~/proyectos/datos_p4):
  python3 ref/cotas/explorar_clon.py simular   las estrategias que faltan en la caché (idea 1 y
                                               bandas 30, 50 y 60 en Python), una vez
  python3 ref/cotas/explorar_clon.py parte1    métricas desde la caché -> clon_parte1.txt
"""
import argparse
import hashlib
import os
import pickle
import random
import subprocess
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorar_optimo as XO   # noqa: E402  (fija la clave de caché de "optima" y presta Datos)
import explorar_ideas as E     # noqa: E402
import explorar_regimen as XR  # noqa: E402
import optimo_estrategia as OE  # noqa: E402
import regimen as RG           # noqa: E402

SALIDA = E.SALIDA
SEMILLA = 18
SORTEOS = 200000        # torneos de 3 rondas en todas las ventanas
SORTEOS_ANIO = 100000   # por año de inicio
EMPATE = 10             # |diferencia de promedio| < 10 es empate
ANIOS = XR.ANIOS_OTRAS

B30, B50, B60P = ("banda", {"w": 30}), ("banda", {"w": 50}), ("banda", {"w": 60})
IDEA1 = ("dp", {"objetivo": "log_exacto", "version": "placa", "modo": "cambios"})   # el representante de la sección 3

# V1, V2 y V3 completas (G2, sección 13.4) se evaluaron con el código de optimo_estrategia.py,
# paseo_optimo.py y regimen.py del commit 1360cef; después esos archivos cambiaron (clase de placa,
# guardas) y la clave de caché con el código actual ya no las encuentra. Se leen con la clave de
# ese commit. Si el archivo no está, se evalúan con el código actual y se avisa.
COMMIT_G2 = "1360cef"
# Los .pkl que se leen aquí son las cachés locales que escriben estos mismos scripts en build/cotas/;
# no se cargan archivos de otro origen.


def _git_show(commit, archivo):
    return subprocess.run(["git", "show", f"{commit}:ref/cotas/{archivo}"], capture_output=True, check=True,
                          cwd=E.comun.RAIZ).stdout


def ruta_cache(conj, sp, extra=None):
    extra = E.CODIGO_EXTRA.get(sp[0], "") if extra is None else extra
    h = hashlib.sha256((E.codigo() + extra + repr(sp)).encode()).hexdigest()[:20]
    return os.path.join(E.CACHE, f"{conj.clave()}_{h}.pkl")


def cargar_historica(cx, sp, commit, avisos):
    extra = hashlib.sha256(b"".join(_git_show(commit, f) for f in
                                    ("optimo_estrategia.py", "paseo_optimo.py", "regimen.py"))).hexdigest()[:16]
    ruta = ruta_cache(cx.conj, sp, extra)
    if os.path.exists(ruta):
        avisos.append(f"{XO.nombre_spec(sp)}: caché del código de {commit} ({os.path.basename(ruta)})")
        return pickle.load(open(ruta, "rb"))
    avisos.append(f"AVISO: {XO.nombre_spec(sp)} no está en la caché de {commit}; se evaluó con el código actual")
    return cx.ev([sp])[0]


def solo_cache(cx, sp, nombre, avisos):
    ruta = ruta_cache(cx.conj, sp)
    if not os.path.exists(ruta):
        raise SystemExit(f"{nombre} no está en la caché ({os.path.basename(ruta)}): corre primero 'simular'")
    avisos.append(f"{nombre}: caché {os.path.basename(ruta)}")
    return pickle.load(open(ruta, "rb"))


class Ctx:
    def __init__(self, procesos=None):
        self.cx = XR.CtxO(procesos)
        self.D, self.R, self.G = self.cx.D, self.cx.R, self.cx.G
        self.n = len(self.D.filas)
        self.anio = [f[2] for f in self.D.filas]
        self.caso = [caso_de(v) for v in self.D.ventanas]


def caso_de(v):
    """S si el 100 llega antes que el 255, B si el 255 llega primero."""
    i100, i255 = v.find(bytes([100])), v.find(bytes([255]))
    return "S" if i100 < i255 else "B"


def estrategias(c, avisos):
    """Las siete de la parte 1, desde la caché. Devuelve {nombre: dict W, n}."""
    cx = c.cx
    el = pickle.load(open(os.path.join(XO.CACHE, "elegidas_guardas.pkl"), "rb"))
    fin = pickle.load(open(os.path.join(XR.CACHE, "finales.pkl"), "rb"))
    out = {}
    b60 = solo_cache(cx, B60P, "banda 60 (Python)", avisos)
    distintas = sum(1 for i in range(c.n) if b60["W"][i] != c.R["espera_banda60"][i])
    avisos.append(f"control: banda 60 en Python contra espera_banda60 en C: {distintas} ventanas distintas de {c.n}")
    out["banda 60"] = b60
    for v in ("V1", "V2", "V3"):
        out[v] = cargar_historica(cx, OE.spec(v, "log", "S2/t"), COMMIT_G2, avisos)
    out["V3 sin guarda (placa)"] = solo_cache(cx, XO.spec_g("V3", None), "V3 sin guarda, placa", avisos)
    out["V3 con (b)"] = solo_cache(cx, el["V3"], "V3 con (b)", avisos)
    out["módulo A"] = solo_cache(cx, RG.spec_politica(None, fin["A"]), "módulo A", avisos)
    out["idea 1"] = solo_cache(cx, IDEA1, "idea 1", avisos)
    return out


def rivales(c, avisos):
    cx = c.cx
    b40 = solo_cache(cx, E.B40, "banda 40", avisos)
    distintas = sum(1 for i in range(c.n) if b40["W"][i] != c.R["espera_banda40"][i])
    avisos.append(f"control: banda 40 en Python contra espera_banda40 en C: {distintas} ventanas distintas de {c.n}")
    return {"banda 40": b40["W"], "banda 30": solo_cache(cx, B30, "banda 30", avisos)["W"],
            "banda 50": solo_cache(cx, B50, "banda 50", avisos)["W"], "banda 60": c.R["espera_banda60"]}


# --- torneos mano a mano ------------------------------------------------------------------------

def sorteos(idx, nombre, n):
    rng = random.Random(f"clon3-{SEMILLA}-{nombre}")
    m = len(idx)
    return [(idx[rng.randrange(m)], idx[rng.randrange(m)], idx[rng.randrange(m)]) for _ in range(n)]


_T = {}


def _mano(args):
    """Métricas de un par (estrategia, rival) sobre sorteos fijos. x[i] = W propio - W del rival."""
    clave, x, sub = args
    tr, n_idx = _T[sub]
    N = len(tr)
    lim = 3 * EMPATE
    S = [x[a] + x[b] + x[c] for a, b, c in tr]
    g = sum(1 for s in S if s >= lim)
    p = sum(1 for s in S if s <= -lim)
    dfc = [(-s / 3.0 if s < 0 else 0.0) for s in S]
    mg, mp, md, mm = g / N, p / N, sum(dfc) / N, sum(S) / (3.0 * N)
    # proyección de Hoeffding: h1(i) = media de (f - m) en los torneos con la ventana i
    acc = {k: {} for k in ("g", "p", "d", "m")}
    cnt = {}
    for (a, b, c), s, d in zip(tr, S, dfc):
        fg = (1.0 if s >= lim else 0.0) - mg
        fp = (1.0 if s <= -lim else 0.0) - mp
        fd = d - md
        fm = s / 3.0 - mm
        for i in (a, b, c):
            cnt[i] = cnt.get(i, 0) + 1
            acc["g"][i] = acc["g"].get(i, 0.0) + fg
            acc["p"][i] = acc["p"].get(i, 0.0) + fp
            acc["d"][i] = acc["d"].get(i, 0.0) + fd
            acc["m"][i] = acc["m"].get(i, 0.0) + fm
    contrib = {}
    for k in acc:
        cvec = [0.0] * len(x)
        for i, v in acc[k].items():
            cvec[i] = 3.0 * (v / cnt[i]) / n_idx
        contrib[k] = cvec
    Ss = sorted(S)
    return clave, dict(g=100 * mg, e=100 * (1 - mg - mp), p=100 * mp, d=md, m=mm,
                       p5=Ss[int(0.05 * (N - 1))] / 3.0, peor=Ss[0] / 3.0), contrib


def torneos(c, Ws, Rs, subconjuntos, procesos=None):
    """Ws: {estrategia: W}, Rs: {rival: W}, subconjuntos: {nombre: (idx, sorteos)}.
    Devuelve {(sub, estrategia, rival): métricas con ee}."""
    for sub, (idx, n) in subconjuntos.items():
        _T[sub] = (sorteos(idx, sub, n), len(idx))
    tareas = []
    for sub in subconjuntos:
        for s, W in Ws.items():
            for r, Wr in Rs.items():
                tareas.append(((sub, s, r), [W[i] - Wr[i] for i in range(c.n)], sub))
    out = {}
    with Pool(procesos or os.cpu_count()) as pool:
        for clave, met, contrib in pool.imap_unordered(_mano, tareas):
            for k in ("g", "p", "d", "m"):
                met[f"ee_{k}"] = XR.ee_contrib(contrib[k], c.G, True)[0] * (100 if k in ("g", "p") else 1)
            out[clave] = met
    return out


def fmt(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def fmt_ee(x, ee, d=1, signo=False):
    s = f"{x:+.{d}f}" if signo else f"{x:.{d}f}"
    return f"{s.replace('.', ',')} ({fmt(ee, d)})"


# --- parte 1 ------------------------------------------------------------------------------------

def parte1(procesos):
    c = Ctx(procesos)
    avisos = []
    Wd = estrategias(c, avisos)
    Rs = rivales(c, avisos)
    Ws = {"banda 40": Rs["banda 40"]}
    Ws.update({k: v["W"] for k, v in Wd.items()})
    ords = {"banda 40": None}
    ords.update({k: v["n"] for k, v in Wd.items()})
    todos = list(range(c.n))
    subs = {"todas": (todos, SORTEOS)}
    for a in ANIOS:
        subs[str(a)] = ([i for i in todos if c.anio[i] == a], SORTEOS_ANIO)
    res = torneos(c, Ws, Rs, subs, procesos)

    L = ["# Métricas contra el clon: parte 1, desde la caché", "",
         f"ref/cotas/explorar_clon.py parte1, commit {XR.commit()}. Otras acciones: {c.n} ventanas (24 por acción y año "
         f"de inicio, 2020 a 2024). Torneos de 3 rondas mano a mano: {SORTEOS} sorteos en todas y {SORTEOS_ANIO} por año, "
         "los mismos para todas las estrategias y rivales. Gana si el promedio propio supera al del rival por 10 o más; "
         "empata si la diferencia es menor que 10; déficit = media de max(0, promedio del rival - promedio propio). "
         "Entre paréntesis, error estándar agrupado (bloques de 20 y 60 días, y fecha y empresa; el mayor).", ""]
    L += ["Origen de cada columna:", ""] + [f"- {a}" for a in avisos] + [""]

    nS = sum(1 for i in todos if c.caso[i] == "S")
    L.append(f"Casos: S (el 100 antes que el 255) {nS} ventanas ({fmt(100 * nS / c.n)} %), B {c.n - nS}.\n")

    for r in Rs:
        L.append(f"\n## Rival: {r}, todas las ventanas\n")
        L.append("| Estrategia | Media | Órdenes | Δ por ronda (ee) | Gana % (ee) | Empata % | Pierde % (ee) | Déficit (ee) | p5 de la diferencia | Peor |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for s in Ws:
            m = res[("todas", s, r)]
            med = sum(Ws[s]) / c.n
            o = fmt(_ordenes_b40(c)) if ords[s] is None else fmt(sum(ords[s]) / c.n)
            L.append(f"| {s} | {med:.0f} | {o} | {fmt_ee(m['m'], m['ee_m'], 0, True)} | {fmt_ee(m['g'], m['ee_g'])} | "
                     f"{fmt(m['e'])} | {fmt_ee(m['p'], m['ee_p'])} | {fmt_ee(m['d'], m['ee_d'], 0)} | {m['p5']:+.0f} | {m['peor']:+.0f} |")

    for r in Rs:
        L.append(f"\n## Rival: {r}, por año de inicio (gana / empata / pierde %, déficit)\n")
        L.append("| Estrategia | " + " | ".join(str(a) for a in ANIOS) + " |")
        L.append("|---|" + "---|" * len(ANIOS))
        for s in Ws:
            celdas = []
            for a in ANIOS:
                m = res[(str(a), s, r)]
                celdas.append(f"{fmt(m['g'])} / {fmt(m['e'])} / {fmt(m['p'])}, {m['d']:.0f} ({m['ee_d']:.0f})")
            L.append(f"| {s} | " + " | ".join(celdas) + " |")

    for r in Rs:
        L.append(f"\n## Rival: {r}, por año de inicio (p5 / peor de la diferencia de promedio)\n")
        L.append("| Estrategia | " + " | ".join(str(a) for a in ANIOS) + " |")
        L.append("|---|" + "---|" * len(ANIOS))
        for s in Ws:
            L.append(f"| {s} | " + " | ".join(f"{res[(str(a), s, r)]['p5']:+.0f} / {res[(str(a), s, r)]['peor']:+.0f}"
                                              for a in ANIOS) + " |")

    # Por caso, contra la banda 40 exacta: de dónde sale cada número
    L.append("\n## Por caso, contra la banda 40 (una ronda)\n")
    L.append("| Estrategia | Δ caso S (ee) | Δ caso B (ee) | Δ total (ee) | Rondas S perdidas % | Rondas B ganadas / perdidas % | Órdenes S / B |")
    L.append("|---|---|---|---|---|---|---|")
    b40 = Rs["banda 40"]
    for s in Ws:
        W = Ws[s]
        fila = [s]
        for cs in ("S", "B", None):
            idx = [i for i in todos if cs is None or c.caso[i] == cs]
            d, ee = XR.delta(c.G, {"W": W}, {"W": b40}, idx)
            fila.append(fmt_ee(d, ee, 0, True))
        iS = [i for i in todos if c.caso[i] == "S"]
        iB = [i for i in todos if c.caso[i] == "B"]
        pS = 100 * sum(1 for i in iS if W[i] < b40[i]) / len(iS)
        gB = 100 * sum(1 for i in iB if W[i] > b40[i]) / len(iB)
        pB = 100 * sum(1 for i in iB if W[i] < b40[i]) / len(iB)
        on = ords[s] if ords[s] is not None else _n_b40(c)
        oS = sum(on[i] for i in iS) / len(iS)
        oB = sum(on[i] for i in iB) / len(iB)
        fila += [fmt(pS), f"{fmt(gB)} / {fmt(pB)}", f"{fmt(oS)} / {fmt(oB)}"]
        L.append("| " + " | ".join(fila) + " |")

    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "clon_parte1.txt"), "w").write(txt)
    pickle.dump(res, open(os.path.join(XO.CACHE, "clon_parte1.pkl"), "wb"))
    print(txt)


_B40N = {}


def _n_b40(c):
    if "n" not in _B40N:
        _B40N["n"] = solo_cache(c.cx, E.B40, "banda 40", [])["n"]
    return _B40N["n"]


def _ordenes_b40(c):
    n = _n_b40(c)
    return sum(n) / len(n)


def simular(procesos):
    cx = XR.CtxO(procesos)
    faltan = [sp for sp in (B30, B50, B60P, IDEA1) if not os.path.exists(ruta_cache(cx.conj, sp))]
    print(f"faltan en la caché: {faltan}", file=sys.stderr)
    if faltan:
        cx.ev(faltan)
    print("listo")


def main():
    # explorar_ideas.evaluar pasa el conjunto a los procesos por una variable global (_G), que solo
    # heredan si se crean con fork; desde Python 3.14 el método por omisión en Linux es forkserver.
    import multiprocessing
    multiprocessing.set_start_method("fork", force=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=("simular", "parte1"))
    ap.add_argument("--procesos", type=int, default=None)
    a = ap.parse_args()
    if a.accion == "simular":
        simular(a.procesos)
    else:
        parte1(a.procesos)


if __name__ == "__main__":
    main()
