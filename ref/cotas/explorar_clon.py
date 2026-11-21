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
  python3 ref/cotas/explorar_clon.py parte3    candado (partes 3, 4 y 6) -> clon_parte3.txt
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
    """Métricas de un par (estrategia, rival) sobre sorteos fijos. x[i] = W propio - W del rival.
    Con ("mem", (Wc, Wcl, Wr)) en lugar de x: memoria entre rondas (parte 4); en el orden del
    sorteo, si la suma de D = Wc - Wcl (contra el clon emulado) ya es positiva al terminar una
    ronda, las siguientes copian al clon desde el inicio (patrimonio Wcl)."""
    clave, x, sub = args
    tr, n_idx = _T[sub]
    N = len(tr)
    if isinstance(x, tuple) and x[0] == "mem":
        Wc, Wcl, Wr = x[1][:3]
        umbral = x[1][3] if len(x[1]) > 3 else None   # parte 7: copia si la D acumulada ya es >= M
        S = []
        for t in tr:
            cum, own, copia = 0, 0, False
            for i in t:
                if copia:
                    own += Wcl[i]
                else:
                    own += Wc[i]
                    cum += Wc[i] - Wcl[i]
                    copia = cum > 0 if umbral is None else cum >= umbral
            S.append(own - Wr[t[0]] - Wr[t[1]] - Wr[t[2]])
        x = Wc
    else:
        S = [x[a] + x[b] + x[c] for a, b, c in tr]
    lim = 3 * EMPATE
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
    return correr_torneos(c, tareas, procesos)


def correr_torneos(c, tareas, procesos=None):
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


# --- partes 3, 4 y 6: candado -------------------------------------------------------------------

MS = (25, 50, 100, 200, 400, 800)
LS = (None, 500, 1000, 2000, 4000)
CONTROL_VENTANAS = 120          # ventanas de la referencia directa (Candado en ideas.correr)
CONTROL_COMBOS = ((25, None), (100, 1000), (800, 500), (400, 4000))
PLACA_VENTANAS = 240            # ventanas del conteo del hilo del clon (parte 6)


def bases_candado():
    el = pickle.load(open(os.path.join(XO.CACHE, "elegidas_guardas.pkl"), "rb"))
    fin = pickle.load(open(os.path.join(XR.CACHE, "finales.pkl"), "rb"))
    return {"V2": OE.spec("V2", "log", "S2/t"), "V3 con (b)": el["V3"], "módulo A": RG.spec_politica(None, fin["A"])}


def _combos(ids):
    import candado as CD
    conj, specs = _G3["conj"], _G3["specs"]
    return ids, [CD.ventana_combos(conj.ventana(i), specs, MS, LS) for i in ids]


def _control(i):
    import candado as CD
    import ideas
    conj, specs = _G3["conj"], _G3["specs"]
    w = conj.ventana(i)
    out = []
    for k, sp in enumerate(specs):
        for M, L in CONTROL_COMBOS:
            s = CD.Candado(sp, M, L)
            W, n, _ = ideas.correr(w, s)
            out.append(((k, M, L), W, n, s.estado))
    return i, out


def _placa(i):
    import candado as CD
    import ideas
    w = _G3["conj"].ventana(i)
    Ds, peor, media, det = CD.hilo_clon_placa(w)
    # D exacto con las dos cuentas de ideas.Cuenta
    cl, pr = ideas.Cuenta(ideas.crear(CD.CLON)), ideas.Cuenta(ideas.crear(("banda", {"w": 60})))
    mal = 0
    for p, D in zip(w, Ds):
        cl.paso(p)
        pr.paso(p)
        mal += (pr.W - cl.W) != D
    return i, peor, media, det, mal


_G3 = {}


def clave_parte3(cx, specs):
    h = hashlib.sha256(repr((specs, MS, LS, cx.conj.clave(), E.codigo(), E.CODIGO_EXTRA.get("optima"),
                             E.CODIGO_EXTRA.get("regimen_pol"))).encode())
    h.update(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "candado.py"), "rb").read())
    return h.hexdigest()[:16]


def simular_parte3(c, specs, procesos):
    """Todas las combinaciones en las 12 000 ventanas (caché por código), más los controles."""
    cx = c.cx
    ruta = os.path.join(XO.CACHE, f"clon_parte3_{clave_parte3(cx, specs)}.pkl")
    if os.path.exists(ruta):
        return pickle.load(open(ruta, "rb"))
    _G3["conj"], _G3["specs"] = cx.conj, specs
    if cx.conj.ventanas is None:
        cx.conj.cargar_series()
    ids = list(range(c.n))
    tr = max(10, c.n // ((procesos or os.cpu_count()) * 8))
    res = [None] * c.n
    with Pool(procesos or os.cpu_count()) as pool:
        for idsr, out in pool.imap_unordered(_combos, [ids[a:a + tr] for a in range(0, c.n, tr)]):
            for i, o in zip(idsr, out):
                res[i] = o
        rng = random.Random(f"control-candado-{SEMILLA}")
        ctl_ids = sorted(rng.sample(ids, CONTROL_VENTANAS))
        control = list(pool.imap_unordered(_control, ctl_ids))
        pl_ids = sorted(rng.sample(ids, PLACA_VENTANAS))
        placa = list(pool.imap_unordered(_placa, pl_ids))
    out = dict(res=res, control=control, placa=placa)
    pickle.dump(out, open(ruta, "wb"))
    return out


def parte3(procesos):
    c = Ctx(procesos)
    avisos = []
    Rs = rivales(c, avisos)
    Wd = estrategias(c, avisos)
    specs_d = bases_candado()
    nombres = list(specs_d)
    specs = [specs_d[k] for k in nombres]
    sim = simular_parte3(c, specs, procesos)
    res = sim["res"]
    todos = list(range(c.n))
    b40 = Rs["banda 40"]

    L = ["# Candado contra el clon de la banda 40: partes 3, 4 y 6", "",
         f"ref/cotas/explorar_clon.py parte3, commit {XR.commit()}. Otras acciones: {c.n} ventanas. Torneos: los mismos "
         f"{SORTEOS} sorteos de la parte 1. El clon emulado es la banda 40 exacta; D = patrimonio propio - patrimonio del "
         "clon al precio actual. Con D >= M (candado arriba) o D <= -L (tope) se igualan las acciones del clon, con "
         "órdenes de hasta 63 y comisión 5, y se lo copia hasta el final de la ronda.", ""]

    # controles
    L.append("## Controles\n")
    cl_mal = sum(1 for i in todos if res[i]["clon"][0] != b40[i])
    L.append(f"- Clon emulado contra la banda 40 de la caché: {cl_mal} ventanas distintas de {c.n}.")
    ref = {"V2": Wd["V2"]["W"], "V3 con (b)": Wd["V3 con (b)"]["W"], "módulo A": Wd["módulo A"]["W"]}
    for k, nm in enumerate(nombres):
        mal = sum(1 for i in todos if res[i][("base", k)][0] != ref[nm][i])
        L.append(f"- Base {nm} recorrida con el código actual contra la caché de la parte 1: {mal} ventanas distintas de {c.n}.")
    mal = 0
    for i, out in sim["control"]:
        for (k, M, Lt), W, n, est in out:
            Wf, e, nord, _, _ = res[i][(k, M, Lt)]
            mal += (W != Wf) or (n != nord) or (est != e)
    L.append(f"- Camino rápido contra la referencia directa (`candado.Candado` en `ideas.correr`), {CONTROL_VENTANAS} "
             f"ventanas, 3 bases y {len(CONTROL_COMBOS)} combinaciones: {mal} diferencias en patrimonio, órdenes o estado.")
    L.append("")

    # métricas por combinación
    Ws, filas = {}, {}
    for k, nm in enumerate(nombres):
        Ws[(nm, "base")] = [res[i][("base", k)][0] for i in todos]
        for M in MS:
            for Lt in LS:
                Ws[(nm, M, Lt)] = [res[i][(k, M, Lt)][0] for i in todos]
    tareas = [((("todas",) + (key if isinstance(key, tuple) else (key,))), [W[i] - b40[i] for i in todos], "todas")
              for key, W in Ws.items()]
    _T["todas"] = (sorteos(todos, "todas", SORTEOS), c.n)
    met = correr_torneos(c, tareas, procesos)

    def nombre_combo(nm, M, Lt):
        return f"{nm}, M {M}, L {'sin tope' if Lt is None else Lt}"

    L.append("## Parte 3: todas las combinaciones contra la banda 40 (rival real = clon emulado)\n")
    L.append("Por ronda: porcentaje de rondas que terminan con candado arriba, en el tope y sin tocar ninguno, con la "
             "diferencia media con el clon de cada grupo; órdenes por ronda y órdenes extra (las del seguidor menos las "
             "del clon después del candado). Por torneo de 3 rondas, las métricas de la parte 1.\n")
    L.append("| Base | M | L | Arriba % (Δ) | Tope % (Δ) | Ninguno % (Δ) | Órdenes | Extra | Δ por ronda (ee) | Gana % | Empata % | Pierde % (ee) | Déficit (ee) | p5 | Peor |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    ranking = []
    for k, nm in enumerate(nombres):
        mb = met[("todas", nm, "base")]
        ob = sum(res[i][("base", k)][1] for i in todos) / c.n
        L.append(f"| {nm} | sin candado | | | | 100,0 ({mb['m']:+.0f}) | {fmt(ob)} | | {fmt_ee(mb['m'], mb['ee_m'], 0, True)} | "
                 f"{fmt(mb['g'])} | {fmt(mb['e'])} | {fmt_ee(mb['p'], mb['ee_p'])} | {fmt_ee(mb['d'], mb['ee_d'], 0)} | "
                 f"{mb['p5']:+.0f} | {mb['peor']:+.0f} |")
        for M in MS:
            for Lt in LS:
                r = [res[i][(k, M, Lt)] for i in todos]
                grupos = {}
                for i, x in zip(todos, r):
                    grupos.setdefault(x[1], []).append(x[0] - b40[i])
                cel = []
                for e in (1, 2, 0):
                    g = grupos.get(e, [])
                    cel.append(f"{fmt(100 * len(g) / c.n)} ({(sum(g) / len(g)) if g else 0:+.0f})")
                o = sum(x[2] for x in r) / c.n
                ex = [x[3] for x in r if x[1]]
                exm = sum(ex) / len(ex) if ex else 0.0
                m = met[("todas", nm, M, Lt)]
                L.append(f"| {nm} | {M} | {'sin tope' if Lt is None else Lt} | {cel[0]} | {cel[1]} | {cel[2]} | {fmt(o)} | "
                         f"{fmt(exm)} | {fmt_ee(m['m'], m['ee_m'], 0, True)} | {fmt(m['g'])} | {fmt(m['e'])} | "
                         f"{fmt_ee(m['p'], m['ee_p'])} | {fmt_ee(m['d'], m['ee_d'], 0)} | {m['p5']:+.0f} | {m['peor']:+.0f} |")
                ranking.append(((m["d"], m["p"], -m["m"]), (nm, M, Lt)))
    ranking.sort(key=lambda x: x[0])
    top = [x[1] for x in ranking[:3]]
    L.append("\nCriterio para elegir las 3 que se repiten (el objetivo del pedido: quedar debajo del clon resta y ganarle "
             "no suma): menor déficit esperado contra la banda 40; a igual déficit, menor porcentaje de torneos "
             "perdidos, y después mayor diferencia media. Las 3: " + "; ".join(nombre_combo(*t) for t in top) + ".")
    L.append("\nLas 10 primeras por ese criterio: " + "; ".join(
        f"{nombre_combo(*t)} (déficit {d:.0f}, pierde {fmt(p)} %, Δ {-mm:+.0f})" for (d, p, mm), t in ranking[:10]) + ".\n")

    # las 3 primeras salen casi iguales (módulo A con M 25 casi nunca llega al tope): se repite además la
    # mejor de cada base con el mismo criterio
    por_base = []
    for nm in nombres:
        t = next(t for _, t in ranking if t[0] == nm)
        if t not in top:
            por_base.append(t)
    L.append("La mejor de cada base por el mismo criterio (se repiten también): " +
             "; ".join(nombre_combo(*t) for t in por_base) + ".\n")
    top = top + por_base

    # repetición con otros rivales y parte 4
    tareas = []
    for t in top:
        W = Ws[t]
        for rv, Wr in Rs.items():
            tareas.append((("r",) + t + (rv,), [W[i] - Wr[i] for i in todos], "todas"))
            tareas.append((("mem",) + t + (rv,), ("mem", (W, b40, Wr)), "todas"))
    for k, nm in enumerate(nombres):
        for rv, Wr in Rs.items():
            tareas.append((("r", nm, "base", None, rv), [Ws[(nm, "base")][i] - Wr[i] for i in todos], "todas"))
    met2 = correr_torneos(c, tareas, procesos)

    L.append("## Las 3 mejores con el rival real en otra banda (el emulado sigue siendo la banda 40)\n")
    L.append("Degradación: cambio del déficit y del porcentaje perdido respecto del mismo candado contra la banda 40.\n")
    L.append("| Combinación | Rival real | Δ por ronda (ee) | Gana % | Empata % | Pierde % (ee) | Déficit (ee) | p5 | Peor | Degradación: déficit / pierde |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for t in top:
        m40 = met2[("r",) + t + ("banda 40",)]
        for rv in Rs:
            m = met2[("r",) + t + (rv,)]
            L.append(f"| {nombre_combo(*t)} | {rv} | {fmt_ee(m['m'], m['ee_m'], 0, True)} | {fmt(m['g'])} | {fmt(m['e'])} | "
                     f"{fmt_ee(m['p'], m['ee_p'])} | {fmt_ee(m['d'], m['ee_d'], 0)} | {m['p5']:+.0f} | {m['peor']:+.0f} | "
                     f"{m['d'] - m40['d']:+.0f} / {m['p'] - m40['p']:+.1f} |".replace(".", ","))
    L.append("\nLas bases sin candado contra los mismos rivales (referencia):\n")
    L.append("| Base | Rival real | Δ por ronda (ee) | Gana % | Empata % | Pierde % (ee) | Déficit (ee) | p5 | Peor |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for nm in nombres:
        for rv in Rs:
            m = met2[("r", nm, "base", None, rv)]
            L.append(f"| {nm} | {rv} | {fmt_ee(m['m'], m['ee_m'], 0, True)} | {fmt(m['g'])} | {fmt(m['e'])} | "
                     f"{fmt_ee(m['p'], m['ee_p'])} | {fmt_ee(m['d'], m['ee_d'], 0)} | {m['p5']:+.0f} | {m['peor']:+.0f} |")

    L.append("\n## Parte 4 (solo como dato): memoria entre rondas\n")
    L.append("En el orden del sorteo: si la suma de D contra el clon emulado ya es positiva al terminar una ronda, las "
             "rondas siguientes copian al clon desde el inicio. Mismos sorteos.\n")
    L.append("| Combinación | Rival real | Δ por ronda (ee) | Gana % | Empata % | Pierde % (ee) | Déficit (ee) | p5 | Peor | Cambio contra sin memoria: déficit / pierde |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for t in top:
        for rv in Rs:
            m = met2[("mem",) + t + (rv,)]
            m0 = met2[("r",) + t + (rv,)]
            L.append(f"| {nombre_combo(*t)} | {rv} | {fmt_ee(m['m'], m['ee_m'], 0, True)} | {fmt(m['g'])} | {fmt(m['e'])} | "
                     f"{fmt_ee(m['p'], m['ee_p'])} | {fmt_ee(m['d'], m['ee_d'], 0)} | {m['p5']:+.0f} | {m['peor']:+.0f} | "
                     f"{m['d'] - m0['d']:+.0f} / {m['p'] - m0['p']:+.1f} |".replace(".", ","))

    # parte 6
    pl = sim["placa"]
    peor = max(x[1] for x in pl)
    media = sum(x[2] for x in pl) / len(pl)
    det = max(pl, key=lambda x: x[1])[3]
    mal = sum(x[4] for x in pl)
    L.append("\n## Parte 6: instrucciones por tick del hilo que emula al clon y lleva D\n")
    L.append(f"`candado.hilo_clon_placa`, en {PLACA_VENTANAS} ventanas completas ({PLACA_VENTANAS * 20000} ticks), con la "
             "aritmética de `optimo_placa.py` (sumas, restas, comparaciones y tablas; el producto por duplicaciones y el "
             f"recorte por restas). D de la placa contra D exacto: {mal} ticks distintos.\n")
    L.append(f"- Peor caso: {peor} operaciones en un tick; media {fmt(media)}.")
    L.append("- Reparto del peor tick: " + ", ".join(f"{k} {v}" for k, v in det.items()) + ", más 6 de lectura y lazo.")
    L.append(f"- Tope por hilo a 0,1 ms: unas 565 instrucciones. {'Cabe' if peor <= 565 else 'No cabe'}.")

    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "clon_parte3.txt"), "w").write(txt)
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
    ap.add_argument("accion", choices=("simular", "parte1", "parte3"))
    ap.add_argument("--procesos", type=int, default=None)
    a = ap.parse_args()
    if a.accion == "simular":
        simular(a.procesos)
    elif a.accion == "parte1":
        parte1(a.procesos)
    else:
        parte3(a.procesos)


if __name__ == "__main__":
    main()
