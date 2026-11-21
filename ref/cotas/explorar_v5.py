#!/usr/bin/env python3
"""explorar_v5.py: corridas de V5 (docs/exploracion_ideas.md, sección 15).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Las mismas 12 000 ventanas de las 100 acciones ajenas y los mismos 200 000 sorteos de la sección 14
(explorar_clon.sorteos). Las cinco empresas no se usan. Rivales del pronóstico e índice de competencia
en v5.py (RIVALES, PESOS).

Índice de competencia: promedio ponderado por rival de dos cifras por torneo de 3 rondas mano a mano:
  nd  % de torneos en que no queda debajo (promedio propio - promedio del rival > -10)
  g   % de torneos que gana (diferencia >= 10)
Error estándar: cada cifra es un estadístico U de orden 3; su parte lineal (proyección de Hoeffding)
se estima con los mismos sorteos y se agrupa por fecha y empresa como en la sección 14
(explorar_regimen.ee_contrib, el mayor de bloques de 20 días, de 60 días y dos sentidos). La
diferencia entre dos estrategias usa la diferencia de sus contribuciones (pareada).

Uso (con export P4_DATOS=~/proyectos/datos_p4):
  python3 ref/cotas/explorar_v5.py pre        precálculo por ventana y rivales (una vez)
  python3 ref/cotas/explorar_v5.py <etapa>    ver ETAPAS al final
Cada corrida guarda por bloque de ventanas y deja una línea de avance en build/clon/v5_<etapa>.log.
"""
import hashlib
import os
import pickle
import random
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorar_clon as XC     # noqa: E402
import explorar_ideas as E     # noqa: E402
import explorar_optimo as XO   # noqa: E402
import explorar_regimen as XR  # noqa: E402
import v5 as V                 # noqa: E402

CACHE = os.path.join(E.comun.BUILD, "v5")
SALIDA = E.SALIDA
BLOQUE = 250
LOG = [None]
_G = {}
# Los .pkl que se leen aquí son las cachés locales que escriben estos mismos scripts en build/cotas/.


def log(msg):
    linea = f"{time.strftime('%H:%M:%S')} {msg}"
    print(linea, flush=True)
    if LOG[0]:
        with open(LOG[0], "a") as f:
            f.write(linea + "\n")


def _atomico(obj, ruta):
    tmp = ruta + f".tmp{os.getpid()}"
    with open(tmp, "wb") as f:
        pickle.dump(obj, f)
    os.replace(tmp, ruta)


def codigo():
    h = hashlib.sha256()
    for f in ("v5.py", "ideas.py", "optimo_estrategia.py", "regimen.py"):
        h.update(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f), "rb").read())
    return h.hexdigest()[:12]


class Ctx:
    def __init__(self):
        self.D = XR.cargar("otras")
        self.n = len(self.D.filas)
        self.G = XR.grupos_de(self.D)
        self.anio = [f[2] for f in self.D.filas]
        self.grupo = list(self.D.grupo)
        self.caso = [XC.caso_de(v) for v in self.D.ventanas]
        _G["vent"] = self.D.ventanas
        os.makedirs(CACHE, exist_ok=True)


# --- precálculo ----------------------------------------------------------------------------------

def _pre_bloque(a):
    t = time.perf_counter()
    vent = _G["vent"]
    out = []
    for i in range(a, min(a + BLOQUE, len(vent))):
        w = vent[i]
        pre = V.precalcular(w)
        wr = {}
        for r in V.RIVALES:
            ca, ac, _ = V.rival(w, r)
            wr[r] = ca[-1] + ac[-1] * w[-1]
        out.append((pre, wr))
    return a, out, time.perf_counter() - t


def precalculo(c, procesos=None):
    carpeta = os.path.join(CACHE, "pre")
    os.makedirs(carpeta, exist_ok=True)
    inicios = list(range(0, c.n, BLOQUE))
    falta = [a for a in inicios if not os.path.exists(os.path.join(carpeta, f"b{a:05d}.pkl"))]
    if falta:
        log(f"precálculo: {len(falta)} bloques de {BLOQUE} ventanas por hacer")
        t0 = time.time()
        with Pool(procesos or os.cpu_count()) as pool:
            for j, (a, out, dt) in enumerate(pool.imap_unordered(_pre_bloque, falta)):
                _atomico(out, os.path.join(carpeta, f"b{a:05d}.pkl"))
                log(f"precálculo: bloque {a:05d} ({j + 1} de {len(falta)}), {dt:.0f} s de un proceso, "
                    f"{time.time() - t0:.0f} s desde el inicio")
    pre, WR = [], {r: [] for r in V.RIVALES}
    for a in inicios:
        for p, wr in pickle.load(open(os.path.join(carpeta, f"b{a:05d}.pkl"), "rb")):
            pre.append(p)
            for r in V.RIVALES:
                WR[r].append(wr[r])
    # motor de placa (V2 comprimida, sin fase A): caché aparte
    carpeta2 = os.path.join(CACHE, "pre_v2c")
    os.makedirs(carpeta2, exist_ok=True)
    _G["pre"] = pre
    falta = [a for a in inicios if not os.path.exists(os.path.join(carpeta2, f"b{a:05d}.pkl"))]
    if falta:
        log(f"precálculo del motor de placa: {len(falta)} bloques por hacer")
        t0 = time.time()
        with Pool(procesos or os.cpu_count()) as pool:
            for j, (a, out, dt) in enumerate(pool.imap_unordered(_pre_v2c, falta)):
                _atomico(out, os.path.join(carpeta2, f"b{a:05d}.pkl"))
                if (j + 1) % 8 == 0 or j + 1 == len(falta):
                    log(f"precálculo del motor de placa: bloque {j + 1} de {len(falta)}, {dt:.0f} s de un proceso, "
                        f"{time.time() - t0:.0f} s desde el inicio")
    for a in inicios:
        for k, ev in enumerate(pickle.load(open(os.path.join(carpeta2, f"b{a:05d}.pkl"), "rb"))):
            pre[a + k]["v2c"] = ev
    # el mismo motor con 8 tramos de tiempo (la mitad de bytes) y con el objetivo lineal
    for nombre, tramos, objetivo in (("v2c8", 8, "log"), ("v2clin", 16, "lineal"), ("v2clin8", 8, "lineal")):
        carpeta3 = os.path.join(CACHE, "pre_" + nombre)
        os.makedirs(carpeta3, exist_ok=True)
        falta = [a for a in inicios if not os.path.exists(os.path.join(carpeta3, f"b{a:05d}.pkl"))]
        if falta:
            t0 = time.time()
            with Pool(procesos or os.cpu_count()) as pool:
                for j, (a, out, dt) in enumerate(pool.imap_unordered(_pre_v2cx, [(a, tramos, objetivo) for a in falta])):
                    _atomico(out, os.path.join(carpeta3, f"b{a:05d}.pkl"))
                    if (j + 1) % 8 == 0 or j + 1 == len(falta):
                        log(f"precálculo del motor {nombre}: bloque {j + 1} de {len(falta)}, {time.time() - t0:.0f} s")
        for a in inicios:
            for k, ev in enumerate(pickle.load(open(os.path.join(carpeta3, f"b{a:05d}.pkl"), "rb"))):
                pre[a + k][nombre] = ev
    return pre, WR


def _pre_v2cx(args):
    a, tramos, objetivo = args
    t = time.perf_counter()
    vent, pre = _G["vent"], _G["pre"]
    return a, [V.precalcular_v2c(vent[i], pre[i]["tA"], tramos, objetivo) for i in range(a, min(a + BLOQUE, len(vent)))], time.perf_counter() - t


def _pre_v2c(a):
    t = time.perf_counter()
    vent, pre = _G["vent"], _G["pre"]
    return a, [V.precalcular_v2c(vent[i], pre[i]["tA"]) for i in range(a, min(a + BLOQUE, len(vent)))], time.perf_counter() - t


# --- evaluación de variantes ---------------------------------------------------------------------

def clave_var(var):
    return hashlib.sha256((codigo() + repr(var)).encode()).hexdigest()[:16]


def _eval_bloque(args):
    a, variantes = args
    t = time.perf_counter()
    vent, pre = _G["vent"], _G["pre"]
    out = {k: [] for k in range(len(variantes))}
    extra = _G.get("rivales_extra", ())
    for i in range(a, min(a + BLOQUE, len(vent))):
        w = vent[i]
        pr = pre[i]
        riv = {r: V.rival(w, r) for r in V.clones_de(variantes)}
        for r in extra:
            riv[r] = V.rival(w, r)
        memo_a = {}
        for k, (optA, optP) in enumerate(variantes):
            ka = repr(optA)
            if ka not in memo_a:
                memo_a[ka] = V.fase_a(w, pr, optA) if optA is not None else pr["base"]
            out[k].append(V.post(w, pr, memo_a[ka], riv, optP))
    return a, out, time.perf_counter() - t


def evaluar(c, variantes, etiqueta="", procesos=None):
    """variantes: {nombre: (optA, optPost)}. Devuelve {nombre: dict(W, n, g, D)} (listas por ventana).
    Caché por variante (clave: código de v5.py y opciones)."""
    res, falta = {}, []
    carpeta = os.path.join(CACHE, "var")
    os.makedirs(carpeta, exist_ok=True)
    for nm, var in variantes.items():
        ruta = os.path.join(carpeta, clave_var(var) + ".pkl")
        if os.path.exists(ruta):
            res[nm] = pickle.load(open(ruta, "rb"))
        else:
            falta.append(nm)
    if falta:
        lista = [variantes[nm] for nm in falta]
        inicios = list(range(0, c.n, BLOQUE))
        acum = {k: {} for k in range(len(lista))}
        t0 = time.time()
        log(f"{etiqueta}: {len(falta)} variantes por simular ({len(variantes) - len(falta)} en caché), "
            f"{len(inicios)} bloques de {BLOQUE} ventanas")
        with Pool(procesos or os.cpu_count()) as pool:
            for j, (a, out, dt) in enumerate(pool.imap_unordered(_eval_bloque, [(a, lista) for a in inicios])):
                for k in out:
                    acum[k][a] = out[k]
                if (j + 1) % 8 == 0 or j + 1 == len(inicios):
                    log(f"{etiqueta}: bloque {j + 1} de {len(inicios)}, {dt:.0f} s de un proceso, "
                        f"{time.time() - t0:.0f} s desde el inicio")
        for k, nm in enumerate(falta):
            filas = [x for a in inicios for x in acum[k][a]]
            r = dict(W=[x[0] for x in filas], n=[x[1] for x in filas], g=[x[2] for x in filas], D=[x[3] for x in filas])
            _atomico(r, os.path.join(carpeta, clave_var(variantes[nm]) + ".pkl"))
            res[nm] = r
    return res


# --- índice --------------------------------------------------------------------------------------

LIM = 3 * XC.EMPATE


def _indice(args):
    """Métricas de una estrategia contra todos los rivales sobre sorteos fijos, con las contribuciones
    por ventana (Hoeffding) del índice (nd y g) y, si se pide, de cada rival."""
    nombre, W, sub, detalle = args
    tr, n_idx = _G["sorteos"][sub]
    WR = _G["WR"]
    NT = len(tr)
    n = len(W) if not isinstance(W, tuple) else len(W[1])
    Ind = [0.0] * NT
    Ig = [0.0] * NT
    Idp = [0.0] * NT            # déficit ponderado del torneo: suma por rival de peso por max(0, -diferencia de promedio)
    met = {}
    contrib = {}
    mem = None
    if isinstance(W, tuple):        # ("mem", W, W del clon emulado, M): memoria entre rondas (dato aparte)
        _, W, Wcl, Mm = W
        mem = []
        for t in tr:
            cum = own = 0
            for i in t:
                if cum >= Mm:
                    own += Wcl[i]
                else:
                    own += W[i]
                    cum += W[i] - Wcl[i]
            mem.append(own)
        n = len(W)
    for r in V.RIVALES:
        Wr = WR[r]
        x = [W[i] - Wr[i] for i in range(n)]
        if mem is None:
            S = [x[a] + x[b] + x[c] for a, b, c in tr]
        else:
            S = [o - Wr[a] - Wr[b] - Wr[c] for o, (a, b, c) in zip(mem, tr)]
        pw = V.PESOS[r]
        g = p = 0
        dfc = 0.0
        for t, s in enumerate(S):
            if s > -LIM:
                Ind[t] += pw
                if s >= LIM:
                    Ig[t] += pw
                    g += 1
                if s < 0:
                    dfc -= s
                    Idp[t] -= pw * s / 3.0
            else:
                p += 1
                dfc -= s
                Idp[t] -= pw * s / 3.0
        Ss = sorted(S)
        met[r] = dict(g=100 * g / NT, p=100 * p / NT, nd=100 * (NT - p) / NT, d=dfc / (3.0 * NT),
                      m=sum(S) / (3.0 * NT), p5=Ss[int(0.05 * (NT - 1))] / 3.0, peor=Ss[0] / 3.0,
                      m1=sum(x) / n if sub == "todas" else None)
        if detalle:
            contrib[r] = (_contrib([1.0 if s > -LIM else 0.0 for s in S], tr, n, n_idx),
                          _contrib([1.0 if s >= LIM else 0.0 for s in S], tr, n, n_idx),
                          _contrib([s / 3.0 for s in S], tr, n, n_idx))
    met["nd"] = 100 * sum(Ind) / NT
    met["g"] = 100 * sum(Ig) / NT
    met["dp"] = sum(Idp) / NT
    contrib["nd"] = _contrib(Ind, tr, n, n_idx)
    contrib["g"] = _contrib(Ig, tr, n, n_idx)
    contrib["dp"] = _contrib(Idp, tr, n, n_idx)
    return nombre, sub, met, contrib


def _contrib(f, tr, n, n_idx):
    m = sum(f) / len(f)
    acc = [0.0] * n
    cnt = [0] * n
    for (a, b, c), v in zip(tr, f):
        v -= m
        acc[a] += v
        acc[b] += v
        acc[c] += v
        cnt[a] += 1
        cnt[b] += 1
        cnt[c] += 1
    return [3.0 * acc[i] / cnt[i] / n_idx if cnt[i] else 0.0 for i in range(n)]


def preparar_sorteos(c, subs=None):
    todos = list(range(c.n))
    S = {"todas": (XC.sorteos(todos, "todas", XC.SORTEOS), c.n)}
    for a in XR.ANIOS_OTRAS:
        idx = [i for i in todos if c.anio[i] == a]
        S[str(a)] = (XC.sorteos(idx, str(a), 60000), len(idx))
    for g in ("tec", "fin", "sal", "con", "ind"):
        idx = [i for i in todos if c.grupo[i] == g]
        S[g] = (XC.sorteos(idx, g, 60000), len(idx))
    _G["sorteos"] = S
    return S


def indices(c, Ws, subs=("todas",), detalle=False, procesos=None):
    """Ws: {nombre: W}. Devuelve {(nombre, sub): (met, contrib)} con ee del índice en met."""
    tareas = [(nm, W, sub, detalle) for nm, W in Ws.items() for sub in subs]
    out = {}
    with Pool(procesos or os.cpu_count()) as pool:
        for nm, sub, met, contrib in pool.imap_unordered(_indice, tareas):
            met["ee_nd"] = 100 * XR.ee_contrib(contrib["nd"], c.G, True)[0]
            met["ee_g"] = 100 * XR.ee_contrib(contrib["g"], c.G, True)[0]
            met["ee_dp"] = XR.ee_contrib(contrib["dp"], c.G, True)[0]
            if detalle:
                for r in V.RIVALES:
                    met[r]["ee_nd"] = 100 * XR.ee_contrib(contrib[r][0], c.G, True)[0]
                    met[r]["ee_g"] = 100 * XR.ee_contrib(contrib[r][1], c.G, True)[0]
                    met[r]["ee_m"] = XR.ee_contrib(contrib[r][2], c.G, True)[0]
            out[(nm, sub)] = (met, contrib)
    return out


def dif(c, ind, a, b, sub="todas"):
    """Diferencia pareada del índice entre las estrategias a y b: (d nd, ee, d g, ee)."""
    ma, ca = ind[(a, sub)]
    mb, cb = ind[(b, sub)]
    out = []
    for k in ("nd", "g"):
        e = 100 * XR.ee_contrib([x - y for x, y in zip(ca[k], cb[k])], c.G, True)[0]
        out += [ma[k] - mb[k], e]
    return out


def fmt(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def fila_indice(nm, met):
    partes = [f"{fmt(met['nd'])} ({fmt(met['ee_nd'])})", f"{fmt(met['g'])} ({fmt(met['ee_g'])})"]
    for r in V.RIVALES:
        m = met[r]
        partes.append(f"{fmt(m['nd'])} / {fmt(m['g'])}")
    return f"| {nm} | " + " | ".join(partes) + " |"


CAB_IND = ("| Estrategia | Índice nd (ee) | Índice g (ee) | " + " | ".join(f"{r}: nd / g" for r in V.RIVALES) + " |\n|---|---|---|"
           + "---|" * len(V.RIVALES))


def contexto(etapa):
    import multiprocessing
    multiprocessing.set_start_method("fork", force=True)
    LOG[0] = os.path.join(E.comun.RAIZ, "build", "clon", f"v5_{etapa}.log")
    c = Ctx()
    pre, WR = precalculo(c)
    _G["WR"] = WR
    for j in range(8):
        V.tabla_pA(j)           # antes del fork: los procesos comparten las tablas
    preparar_sorteos(c)
    return c, pre, WR


def v4b_cache(c):
    """W de V4b (V3 con (b), E1, M 100, sin piso) desde la caché de la etapa 1b de la sección 14."""
    base = os.path.join(XO.CACHE, "v4")
    for carpeta in sorted(os.listdir(base)):
        if not carpeta.startswith("etapa1b_"):
            continue
        for f in os.listdir(os.path.join(base, carpeta)):
            if f.startswith("comb_"):
                x = pickle.load(open(os.path.join(base, carpeta, f), "rb"))
                if x["nombre"] == "V3 con (b), E1, M 100, L sin piso":
                    return x["W"]
    return None


# --- etapas --------------------------------------------------------------------------------------

V4B = (None, dict(motor="E1", M=100))
BASE_SOLA = (None, dict(motor="E0", M=V.INF))


def tabla_rivales(L, nombres, ind, sub="todas"):
    """Tabla larga: cada estrategia contra cada rival."""
    L.append("| Estrategia | Rival | Δ por ronda (ee) | No debajo % (ee) | Gana % (ee) | Pierde % | Déficit | p5 | Peor |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for nm in nombres:
        met = ind[(nm, sub)][0]
        for r in V.RIVALES:
            m = met[r]
            L.append(f"| {nm} | {r} | {m['m']:+.0f} ({m.get('ee_m', 0):.0f}) | {fmt(m['nd'])} ({fmt(m.get('ee_nd', 0))}) | "
                     f"{fmt(m['g'])} ({fmt(m.get('ee_g', 0))}) | {fmt(m['p'])} | {m['d']:.0f} | {m['p5']:+.0f} | {m['peor']:+.0f} |")


def etapa_varas():
    c, pre, WR = contexto("varas")
    L = ["# V5: las dos varas (banda 40 sola y V4b) con el índice de competencia", "",
         f"ref/cotas/explorar_v5.py varas, commit {XR.commit()}. Otras acciones: {c.n} ventanas; los mismos {XC.SORTEOS} "
         "sorteos de la sección 14. Rivales: ext (extremos puros: compra desde el primer 100, vende al ver 255 y no "
         "vuelve), f5 (Fila 5: lo mismo con venta en 220 o más), b30, b50, b60 y b40 (bandas). Pesos del índice: "
         + ", ".join(f"{r} {V.PESOS[r]:.2f}" for r in V.RIVALES) + ". nd = % de torneos de 3 rondas en que no queda "
         "debajo (diferencia de promedio > -10); g = % que gana (diferencia >= 10).", ""]
    # controles
    R = XR.rivales_otras(c.D, None)
    avisos = []
    Rs = XC.rivales(XC.Ctx(), avisos)
    L.append("## Controles\n")
    for r, ref in (("f5", R["unavez100_220"]), ("b40", R["espera_banda40"]), ("b60", R["espera_banda60"]),
                   ("b30", Rs["banda 30"]), ("b50", Rs["banda 50"])):
        L.append(f"- Rival {r} de v5.py contra la caché: {sum(1 for i in range(c.n) if WR[r][i] != ref[i])} ventanas distintas de {c.n}.")
    iS = [i for i in range(c.n) if c.caso[i] == "S"]
    L.append(f"- Dato (no es un control): ext vende una sola vez; `espera` de la caché en C vuelve a comprar si el 100 "
             f"aparece otra vez después del 255. En el caso S difieren en {sum(1 for i in iS if WR['ext'][i] != R['espera'][i])} "
             f"ventanas de {len(iS)}.")
    res = evaluar(c, {"V4b": V4B, "base sola": BASE_SOLA, "todo apagado": (None, dict(motor="E0", M=V.INF, amb=False)),
                      "fase A reescrita": ({}, dict(motor="E1", M=100))}, "varas")
    Wv4b = v4b_cache(c)
    el = pickle.load(open(os.path.join(XO.CACHE, "elegidas_guardas.pkl"), "rb"))
    Wv3b = XC.solo_cache(XC.Ctx().cx, el["V3"], "V3 con (b)", avisos)["W"]
    L.append(f"- V4b de v5.py (tick a tick) contra la caché de la etapa 1b (por eventos): "
             f"{sum(1 for i in range(c.n) if res['V4b']['W'][i] != Wv4b[i])} ventanas distintas de {c.n}.")
    L.append(f"- Motor apagado (E0, sin candado) contra la base V3 con (b) de la caché: "
             f"{sum(1 for i in range(c.n) if res['base sola']['W'][i] != Wv3b[i])} ventanas distintas de {c.n}.")
    L.append(f"- Fase A reescrita (v5.fase_a con las opciones por omisión) contra optimo_estrategia.Optima: "
             f"{sum(1 for i in range(c.n) if res['fase A reescrita']['W'][i] != res['V4b']['W'][i])} ventanas distintas de {c.n}.")
    mal = sum(1 for x in L if x.startswith("- ") and "Dato" not in x and not x.split(": ")[-1].startswith("0 "))
    if mal:
        print("\n".join(L))
        raise SystemExit("CONTROL DISTINTO DE CERO: se detiene")
    Ws = {"banda 40": WR["b40"], "V4b": res["V4b"]["W"], "V3 con (b) sola": res["base sola"]["W"]}
    subs = ["todas"] + [str(a) for a in XR.ANIOS_OTRAS] + ["tec", "fin", "sal", "con", "ind"]
    ind = indices(c, Ws, subs, detalle=True)
    L.append("\n## Índice, todas las ventanas\n")
    L.append(CAB_IND)
    for nm in Ws:
        L.append(fila_indice(nm, ind[(nm, "todas")][0]))
    d = dif(c, ind, "V4b", "banda 40")
    L.append(f"\nV4b menos banda 40 (pareada): nd {d[0]:+.1f} (ee {d[1]:.1f}), g {d[2]:+.1f} (ee {d[3]:.1f}).\n".replace(".", ","))
    L.append("## Contra cada rival, todas las ventanas\n")
    tabla_rivales(L, list(Ws), ind)
    L.append("\n## Índice por año de inicio y por grupo de empresas (nd / g)\n")
    L.append("| Estrategia | " + " | ".join(subs[1:]) + " |")
    L.append("|---|" + "---|" * (len(subs) - 1))
    for nm in Ws:
        L.append(f"| {nm} | " + " | ".join(f"{fmt(ind[(nm, s)][0]['nd'])} / {fmt(ind[(nm, s)][0]['g'])}" for s in subs[1:]) + " |")
    L.append("\n## Cada rival del pronóstico como estrategia propia (matriz del campo)\n")
    L.append("Fila: la regla que jugaríamos; columnas: su nd / g contra cada rival y el índice.\n")
    indr = indices(c, {r: WR[r] for r in V.RIVALES})
    L.append(CAB_IND)
    for r in V.RIVALES:
        d = dif(c, indr | ind, r, "banda 40")
        L.append(fila_indice(f"{r} (Δnd con banda 40 {d[0]:+.1f}, ee {d[1]:.1f})".replace(".", ","), indr[(r, "todas")][0]))
    L.append("\n## Una ronda: banda 40 contra ext y f5, por caso\n")
    L.append("| Rival | Caso | Rondas | Gana % | Empata % | Pierde % | Δ media |")
    L.append("|---|---|---|---|---|---|---|")
    for r in ("ext", "f5"):
        for cs in ("S", "B"):
            idx = [i for i in range(c.n) if c.caso[i] == cs]
            x = [WR["b40"][i] - WR[r][i] for i in idx]
            L.append(f"| {r} | {cs} | {len(idx)} | {fmt(100 * sum(1 for v in x if v > 0) / len(x))} | "
                     f"{fmt(100 * sum(1 for v in x if v == 0) / len(x))} | {fmt(100 * sum(1 for v in x if v < 0) / len(x))} | "
                     f"{sum(x) / len(x):+.0f} |")
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "v5_varas.txt"), "w").write(txt)
    print(txt)


CS = (0, 110, 120, 130, 135, 138, 139, 140, 141, 145, 150, 160)
VS = (195, 205, 210, 214, 215, 216, 218, 220, 221, 225, 235, 245, 255)


def _bandas_bloque(a):
    vent = _G["vent"]
    out = []
    for i in range(a, min(a + BLOQUE, len(vent))):
        w = vent[i]
        fila = {}
        for cc in CS:
            for vv in VS:
                ca, ac, _ = V.rival(w, f"banda:{cc}:{vv}")
                fila[(cc, vv)] = ca[-1] + ac[-1] * w[-1]
        out.append(fila)
    return a, out


def bandas_puras(c):
    ruta = os.path.join(CACHE, f"bandas_{hashlib.sha256(repr((CS, VS, codigo())).encode()).hexdigest()[:12]}.pkl")
    if os.path.exists(ruta):
        return pickle.load(open(ruta, "rb"))
    inicios = list(range(0, c.n, BLOQUE))
    acum = {}
    t0 = time.time()
    with Pool(os.cpu_count()) as pool:
        for j, (a, out) in enumerate(pool.imap_unordered(_bandas_bloque, inicios)):
            acum[a] = out
            if (j + 1) % 8 == 0:
                log(f"bandas puras: bloque {j + 1} de {len(inicios)}, {time.time() - t0:.0f} s desde el inicio")
    filas = [x for a in inicios for x in acum[a]]
    W = {k: [f[k] for f in filas] for k in filas[0]}
    _atomico(W, ruta)
    return W


def etapa_faseD():
    """Arista 6: la fase D como banda pura (sin fase A), niveles por caso, bajo el índice."""
    c, pre, WR = contexto("faseD")
    Wb = bandas_puras(c)
    L = ["# V5, arista 6: niveles de la fase D bajo el índice (bandas puras, sin fase A)", "",
         f"ref/cotas/explorar_v5.py faseD, commit {XR.commit()}. Regla de los peldaños con compra c y venta v en la fase D "
         "(c = 0: no vuelve a comprar). Niveles por caso: (cS, vS) si el 100 llegó primero, (cB, vB) si llegó primero el 255. "
         "Barrido por coordenadas desde 140/215 en los dos casos.", ""]
    assert Wb[(140, 215)] == WR["b40"]
    L.append("Control: la banda pura 140/215 coincide con el rival b40 en las 12 000 ventanas.\n")
    S = [i for i in range(c.n) if c.caso[i] == "S"]
    esS = [cs == "S" for cs in c.caso]

    def comp(kS, kB):
        a, b = Wb[kS], Wb[kB]
        return [a[i] if esS[i] else b[i] for i in range(c.n)]

    Ws = {"banda 40": WR["b40"]}
    for k in Wb:
        Ws[("S", k)] = comp(k, (140, 215))
        Ws[("B", k)] = comp((140, 215), k)
    ind = indices(c, Ws)
    base = ind[("banda 40", "todas")][0]
    for caso in ("S", "B"):
        L.append(f"\n## Caso {caso}: niveles ({'cS, vS' if caso == 'S' else 'cB, vB'}) con el otro caso en 140/215. "
                 "Celda: nd / g del índice, y entre paréntesis la diferencia de nd con la banda 40 en ee pareados\n")
        L.append("| c \\\\ v | " + " | ".join(str(v) for v in VS) + " |")
        L.append("|---|" + "---|" * len(VS))
        for cc in CS:
            cel = []
            for vv in VS:
                m = ind[((caso, (cc, vv)), "todas")][0]
                d = dif(c, ind, (caso, (cc, vv)), "banda 40")
                cel.append(f"{fmt(m['nd'])} / {fmt(m['g'])} ({(d[0] / d[1]) if d[1] > 0 else 0:+.1f})")
            L.append(f"| {cc} | " + " | ".join(cel) + " |")
    # mejores por nd y detalle contra cada rival
    orden = sorted([k for k in Ws if k != "banda 40"], key=lambda k: -ind[(k, "todas")][0]["nd"])
    L.append("\n## Las 12 primeras por nd, contra cada rival\n")
    L.append(CAB_IND)
    L.append(fila_indice("banda 40", base))
    for k in orden[:12]:
        d = dif(c, ind, k, "banda 40")
        L.append(fila_indice(f"caso {k[0]}: {k[1][0]}/{k[1][1]} (Δnd {d[0]:+.1f} ee {d[1]:.1f}; Δg {d[2]:+.1f} ee {d[3]:.1f})",
                             ind[(k, "todas")][0]))
    pickle.dump({k: ind[(k, "todas")][0] for k in Ws}, open(os.path.join(CACHE, "faseD_ind.pkl"), "wb"))
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "v5_faseD.txt"), "w").write(txt)
    print(txt)




def barrido(etapa, titulo, variantes, notas=(), top=None, detalle_de=()):
    """Evalúa variantes {nombre: (optA, optPost)}, calcula el índice y escribe la tabla con las diferencias
    pareadas contra las dos varas. Devuelve (c, res, ind)."""
    c, pre, WR = contexto(etapa)
    variantes = dict(variantes)
    variantes.setdefault("V4b", V4B)
    res = evaluar(c, variantes, etapa)
    Ws = {"banda 40": WR["b40"]}
    Ws.update({nm: res[nm]["W"] for nm in variantes})
    ind = indices(c, Ws)
    L = [f"# V5: {titulo}", "", f"ref/cotas/explorar_v5.py {etapa}, commit {XR.commit()}. Otras acciones: {c.n} ventanas, "
         f"{XC.SORTEOS} sorteos. Índice nd / g con ee; Δ contra cada vara en puntos y, entre paréntesis, en ee pareados. "
         "Δ40 = diferencia media por ronda contra la banda 40 (ee); peor = peor torneo contra la banda 40.", ""]
    L += list(notas) + [""]
    L.append("| Variante | nd (ee) | g (ee) | Δnd banda 40 | Δg banda 40 | Δnd V4b | Δg V4b | " +
             " | ".join(f"{r}" for r in V.RIVALES) + " | Δ40 (ee) | déficit b40 | peor b40 | órdenes |")
    L.append("|---|---|---|---|---|---|---|" + "---|" * len(V.RIVALES) + "---|---|---|---|")
    orden = sorted(Ws, key=lambda k: -(ind[(k, "todas")][0]["nd"] + ind[(k, "todas")][0]["g"]))
    b40 = WR["b40"]
    for nm in orden[:top] if top else orden:
        m = ind[(nm, "todas")][0]
        d1 = dif(c, ind, nm, "banda 40")
        d2 = dif(c, ind, nm, "V4b")

        def z(d, e):
            return f"{d:+.1f} ({(d / e) if e > 0 else 0:+.1f})".replace(".", ",")
        dm, ee = XR.delta(c.G, {"W": Ws[nm]}, {"W": b40}, list(range(c.n)))
        no = sum(res[nm]["n"]) / c.n if nm in res else float("nan")
        L.append(f"| {nm} | {fmt(m['nd'])} ({fmt(m['ee_nd'])}) | {fmt(m['g'])} ({fmt(m['ee_g'])}) | {z(d1[0], d1[1])} | "
                 f"{z(d1[2], d1[3])} | {z(d2[0], d2[1])} | {z(d2[2], d2[3])} | "
                 + " | ".join(f"{fmt(m[r]['nd'])} / {fmt(m[r]['g'])}" for r in V.RIVALES)
                 + f" | {dm:+.0f} ({ee:.0f}) | {m['b40']['d']:.0f} | {m['b40']['peor']:+.0f} | {fmt(no)} |")
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, f"v5_{etapa}.txt"), "w").write(txt)
    print(txt)
    return c, res, ind


def P_(**kw):
    return (None, kw)


def etapa_motor():
    """Aristas 2 y 3: motores de recuperación, frenos, M según el tiempo y audacia final, con la fase A de V3 con (b)."""
    v = {"E0 (sin motor), M 100": P_(motor="E0", M=100)}
    for M in (1, 25, 400):
        v[f"E1, M {M}"] = P_(motor="E1", M=M)
    for fs in ("D", "BC", "B", "C"):
        v[f"E1 solo en {fs}"] = P_(motor="E1", M=100, fases=fs)
    for c2, v2 in ((150, 205), (160, 195), (145, 210), (170, 185), (140, 220), (130, 215), (135, 220), (130, 225), (140, 205), (150, 215)):
        v[f"E2 {c2}/{v2}"] = P_(motor="E2", M=100, c2=c2, v2=v2)
    for g in (50, 100, 200, 400):
        v[f"E1, freno clon {g} por mil"] = P_(motor="E1", M=100, frenos=(("clon", g),))
    for k in (1, 2):
        v[f"E1, freno {k} ventas del clon"] = P_(motor="E1", M=100, frenos=(("ciclos", k),))
    for x in (500, 1000, 2000):
        v[f"E1, freno motor -{x}"] = P_(motor="E1", M=100, frenos=(("motor", x),))
    for Lp in (1000, 2000, 4000):
        v[f"E1, piso {Lp}"] = P_(motor="E1", M=100, L=Lp)
    for R in (2000, 5000):
        v[f"E1, freno tiempo {R}"] = P_(motor="E1", M=100, frenos=(("tiempo", R),))
        v[f"E1, M 1 con {R} o menos"] = P_(motor="E1", M=100, Mfin=(R, 1))
    for R in (500, 1000, 2000, 4000):
        for tipo in ("contra", "compra", "caja"):
            v[f"E1, audacia {tipo} {R}"] = P_(motor="E1", M=100, audacia=(R, tipo))
    for R in (1000, 2000, 4000):
        v[f"E0, audacia contra {R}"] = P_(motor="E0", M=100, audacia=(R, "contra"))
    for r_ in (2000, 5000, 10000):
        v[f"E1 solo con más de {r_} restantes"] = P_(motor="E1", M=100, rmot=r_)
    barrido("motor", "motores de recuperación, frenos y audacia (aristas 2 y 3)", v,
            ["Todas con la fase A de V3 con (b) y candado copiar. V4b = E1, M 100, sin piso."])



POSTS = {"E1": dict(motor="E1", M=100), "E1 en B": dict(motor="E1", M=100, fases="B"), "E0": dict(motor="E0", M=100)}


def etapa_faseA():
    """Arista 1: umbral de probabilidad, tamaño, clase de v^2 y tiempo restante en la fase A."""
    A = {}
    for pin in (0.55, 0.65, 0.75, 0.85, 0.9, 0.95):
        A[f"tabla, pA >= {pin}"] = dict(pin=pin)
    for pout in (0.5, 0.7):
        A[f"tabla, pA >= 0.85, sale con pA < {pout}"] = dict(pin=0.85, pout=pout)
    for f in ((1, 8), (1, 4), (1, 1)):
        A[f"tabla, tamaño {f[0]}/{f[1]}"] = dict(f1=f, f2=f)
    A["tabla, tamaño 1/4 y 1/2 según la tabla"] = dict(f1=(1, 4), f2=(1, 2))
    A["tabla, tamaño 1/2 y 1 según la tabla (V3 sin guarda)"] = dict(f1=(1, 2), f2=(1, 1))
    for k in (1, 2, 3, 4):
        A[f"tabla, clases 0 a {k}"] = dict(clases=tuple(range(k + 1)))
    A["tabla, clases 3 a 7"] = dict(clases=(3, 4, 5, 6, 7))
    for r_ in (5000, 10000, 15000):
        A[f"tabla, solo con {r_} o más restantes"] = dict(rmin=r_)
    for th in (0.8, 0.85, 0.9, 0.95):
        for dp in (0.1, 0.2):
            A[f"prob, entra {th}, sale {th - dp:.2f}, 1/2"] = dict(modo="prob", escala=((th, (1, 2)),), pout=round(th - dp, 2))
    for f in ((1, 4), (1, 1)):
        A[f"prob, entra 0.9, sale 0.7, {f[0]}/{f[1]}"] = dict(modo="prob", escala=((0.9, f),), pout=0.7)
    A["prob, 1/4 con 0.7, 1/2 con 0.8, todo con 0.9, sale 0.6"] = dict(
        modo="prob", escala=((0.7, (1, 4)), (0.8, (1, 2)), (0.9, (1, 1))), pout=0.6)
    v = {}
    for na, oa in A.items():
        for npost, op in POSTS.items():
            v[f"{na}; {npost}"] = (oa, op)
    v["V3 con (b); E1 en B"] = (None, POSTS["E1 en B"])
    v["V3 con (b); E1, freno 1 venta del clon"] = (None, dict(motor="E1", M=100, frenos=(("ciclos", 1),)))
    v["V3 con (b); E0"] = (None, POSTS["E0"])
    # ambición: sin apuesta en la fase A, el motor corre igual
    for fs in ("B", "BC", "BCD"):
        v[f"V3 con (b); E1 en {fs} con ambición"] = (None, dict(motor="E1", M=100, fases=fs, amb=True))
        v[f"sin fase A; E1 en {fs} con ambición"] = (dict(pin=2.0), dict(motor="E1", M=100, fases=fs, amb=True))
    barrido("faseA", "fase A: umbral de probabilidad, tamaño, clase y tiempo (arista 1), y ambición", v,
            ["pA = P(255 antes que 100 | precio, ticks restantes, clase de v^2) del modelo de la sección 13. 'tabla': decide "
             "la tabla comprimida de V3 y además se exige pA para entrar; 'prob': entra y sale solo por pA. Después del primer "
             "extremo: E1 (V4b), E1 solo en la fase B, o E0 (sin motor). Candado copiar con M 100."])


def etapa_compuestas():
    """Arista 6, segunda parte: bandas puras con niveles distintos en los dos casos a la vez."""
    c, pre, WR = contexto("compuestas")
    Wb = bandas_puras(c)
    esS = [cs == "S" for cs in c.caso]
    niv = [(cc, vv) for cc in (120, 130, 135, 140) for vv in (215, 220, 225, 235)]
    Ws = {"banda 40": WR["b40"], "V4b": evaluar(c, {"V4b": V4B}, "compuestas")["V4b"]["W"]}
    for kS in niv:
        for kB in niv:
            a, b = Wb[kS], Wb[kB]
            Ws[f"S {kS[0]}/{kS[1]}, B {kB[0]}/{kB[1]}"] = [a[i] if esS[i] else b[i] for i in range(c.n)]
    ind = indices(c, Ws)
    orden = sorted(Ws, key=lambda k: -ind[(k, "todas")][0]["nd"])
    L = ["# V5, arista 6: bandas puras con niveles por caso en los dos casos a la vez", "",
         f"ref/cotas/explorar_v5.py compuestas, commit {XR.commit()}. Las 20 primeras por nd de {len(niv) ** 2} combinaciones "
         "(compra 120 a 140, venta 215 a 235 en cada caso), más las dos varas.", "", CAB_IND]
    for k in orden[:20] + ["banda 40", "V4b"]:
        d = dif(c, ind, k, "banda 40")
        L.append(fila_indice(f"{k} (Δnd {d[0]:+.1f} ee {d[1]:.1f}; Δg {d[2]:+.1f} ee {d[3]:.1f})", ind[(k, "todas")][0]))
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "v5_compuestas.txt"), "w").write(txt)
    print(txt)



SIN_A = dict(pin=2.0)       # la tabla nunca entra: sin apuesta en la fase A


def etapa_ambicion():
    """Alrededor del hallazgo de la etapa faseA: sin apuesta en la fase A (o con apuestas muy selectivas) y el
    motor corriendo desde D = 0 hasta el candado."""
    v = {"sin fase A; E1": (SIN_A, dict(motor="E1", M=100, amb=True))}
    for M in (10, 30, 50, 200, 400):
        v[f"sin fase A; E1, M {M}"] = (SIN_A, dict(motor="E1", M=M, amb=True))
    for k in (1, 2):
        v[f"sin fase A; E1, freno {k} ventas del clon"] = (SIN_A, dict(motor="E1", M=100, amb=True, frenos=(("ciclos", k),)))
    for x in (500, 1000, 2000):
        v[f"sin fase A; E1, freno motor -{x}"] = (SIN_A, dict(motor="E1", M=100, amb=True, frenos=(("motor", x),)))
    for R in (2000, 5000):
        v[f"sin fase A; E1, freno tiempo {R}"] = (SIN_A, dict(motor="E1", M=100, amb=True, frenos=(("tiempo", R),)))
    v["sin fase A; E1, M 30 con 5000 o menos"] = (SIN_A, dict(motor="E1", M=100, amb=True, Mfin=(5000, 30)))
    for fs in ("BD", "CD", "D", "BC", "B", "C"):
        v[f"sin fase A; E1 en {fs}"] = (SIN_A, dict(motor="E1", M=100, amb=True, fases=fs))
    for r_ in (2000, 5000):
        v[f"sin fase A; E1 solo con más de {r_} restantes"] = (SIN_A, dict(motor="E1", M=100, amb=True, rmot=r_))
    # motor de placa
    for M in (30, 50, 100, 200):
        v[f"sin fase A; E1c (placa), M {M}"] = (SIN_A, dict(motor="v2c", M=M, amb=True))
    for fs in ("BD", "CD", "D", "BC"):
        v[f"sin fase A; E1c (placa) en {fs}"] = (SIN_A, dict(motor="v2c", M=100, amb=True, fases=fs))
    v["sin fase A; E1c (placa), freno 1 ventas del clon"] = (SIN_A, dict(motor="v2c", M=100, amb=True, frenos=(("ciclos", 1),)))
    # motores sin tablas: banda propia en D
    for c2, v2 in ((150, 205), (160, 195), (145, 210), (170, 185), (165, 190), (155, 200), (142, 213), (140, 205), (150, 215),
                   (135, 220), (130, 225), (138, 217)):
        v[f"sin fase A; E2 {c2}/{v2}"] = (SIN_A, dict(motor="E2", M=100, amb=True, c2=c2, v2=v2))
    # apuestas selectivas en la fase A más ambición
    sel = {"tabla, pA >= 0.95": dict(pin=0.95), "tabla, pA >= 0.9": dict(pin=0.9), "tabla, pA >= 0.85": dict(pin=0.85),
           "tabla, clases 0 a 1": dict(clases=(0, 1)), "tabla, clases 0 a 2": dict(clases=(0, 1, 2)),
           "prob 0.95 / 0.75, 1/2": dict(modo="prob", escala=((0.95, (1, 2)),), pout=0.75),
           "tabla, tamaño 1/8": dict(f1=(1, 8), f2=(1, 8)), "tabla, tamaño 1/4": dict(f1=(1, 4), f2=(1, 4)),
           "tabla, pA >= 0.95, tamaño 1/4": dict(pin=0.95, f1=(1, 4), f2=(1, 4)),
           "V3 con (b)": None}
    for na, oa in sel.items():
        v[f"{na}; E1 con ambición"] = (oa, dict(motor="E1", M=100, amb=True))
        v[f"{na}; E1c (placa) con ambición"] = (oa, dict(motor="v2c", M=100, amb=True))
    barrido("ambicion", "sin apuesta en la fase A y motor desde D = 0 (ambición); motor de placa; apuestas selectivas", v,
            ["'sin fase A': nunca apuesta en la fase A; al primer extremo D = 0 y corre el motor hasta D >= M (candado copiar). "
             "Todas con ambición (el motor corre aunque no haya habido apuesta). E1: V2 con la tabla completa, clase exacta y su "
             "propia fase A interna (no cabe en la placa). E1c (placa): V2 comprimida (4 bytes por celda), clase de placa con "
             "histéresis y sin fase A interna. E2: banda propia en la fase D, sin tablas."])



A95 = dict(pin=0.95)
A95P = dict(pin=0.95, sin_bajo=True, pa_tramo=True)      # la misma en forma de placa: 2 bytes por celda


def etapa_fino():
    """Alrededor del mejor punto (apuesta solo con pA >= 0,95 y motor de placa con ambición): forma de placa de la
    fase A, tramos del motor, margen por deslizamiento, M, frenos, y el motor E3 (arista 7)."""
    v = {"pA 0.95; placa 16": (A95, dict(motor="v2c", M=100, amb=True)),
         "sin fase A; placa 16": (SIN_A, dict(motor="v2c", M=100, amb=True)),
         "pA 0.95 de placa (2 bytes); placa 16": (A95P, dict(motor="v2c", M=100, amb=True)),
         "pA 0.95 de placa (2 bytes); placa 8": (A95P, dict(motor="v2c8", M=100, amb=True)),
         "pA 0.95; placa 8": (A95, dict(motor="v2c8", M=100, amb=True)),
         "sin fase A; placa 8": (SIN_A, dict(motor="v2c8", M=100, amb=True)),
         "pA 0.95 sin bloques bajos; placa 16": (dict(pin=0.95, sin_bajo=True), dict(motor="v2c", M=100, amb=True)),
         "pA 0.95 por tramo; placa 16": (dict(pin=0.95, pa_tramo=True), dict(motor="v2c", M=100, amb=True))}
    for pin in (0.97, 0.99):
        v[f"pA {pin}; placa 16"] = (dict(pin=pin), dict(motor="v2c", M=100, amb=True))
    for M in (150, 200, 300):
        v[f"pA 0.95; placa 16, M {M}"] = (A95, dict(motor="v2c", M=M, amb=True))
        v[f"sin fase A; placa 16, M {M}"] = (SIN_A, dict(motor="v2c", M=M, amb=True))
    for sl in (1, 2, 4):
        v[f"pA 0.95; placa 16, margen {sl} por acción"] = (A95, dict(motor="v2c", M=100, amb=True, Mslip=sl))
        v[f"sin fase A; placa 16, margen {sl} por acción"] = (SIN_A, dict(motor="v2c", M=100, amb=True, Mslip=sl))
    v["pA 0.95; placa 16, M 30 y margen 2 por acción"] = (A95, dict(motor="v2c", M=30, amb=True, Mslip=2))
    v["pA 0.95; placa 16, freno 1 venta del clon"] = (A95, dict(motor="v2c", M=100, amb=True, frenos=(("ciclos", 1),)))
    v["pA 0.95; placa 16, freno motor -2000"] = (A95, dict(motor="v2c", M=100, amb=True, frenos=(("motor", 2000),)))
    v["pA 0.95; placa 16, piso 4000"] = (A95, dict(motor="v2c", M=100, amb=True, L=4000))
    for k in (3, 5, 10):
        v[f"sin fase A; E3 k {k}"] = (SIN_A, dict(motor="E3", M=100, amb=True, k3=k))
    v["sin fase A; sin motor (todo apagado)"] = (SIN_A, dict(motor="E0", M=100))
    c, res, ind = barrido("fino", "alrededor del mejor punto: forma de placa, tramos, deslizamiento, M, frenos y E3", v,
                          ["'pA 0.95': fase A de V3 con (b) que solo entra con pA >= 0,95. 'de placa (2 bytes)': sin los bloques bajos "
                           "de la tabla y con pA evaluada en el medio de cada tramo de 1250 ticks (entrada y salida por celda de "
                           "clase y tramo: 2 bytes, 256 en total). 'placa 16' y 'placa 8': motor V2 comprimido con 16 u 8 tramos de "
                           "tiempo (1536 o 768 bytes para las fases B, C y D). Todas con ambición y candado copiar."])
    mal = sum(1 for i in range(c.n) if res["sin fase A; sin motor (todo apagado)"]["W"][i] != _G["WR"]["b40"][i])
    print(f"CONTROL todo apagado contra la banda 40: {mal} ventanas distintas de {c.n}")
    with open(os.path.join(SALIDA, "v5_fino.txt"), "a") as f:
        f.write(f"\nControl: con todo apagado (sin fase A y sin motor), patrimonio distinto al de la banda 40 en {mal} ventanas de {c.n}.\n")



FINALISTAS = {
    "C1: pA 0,95, motor de placa, ambición siempre": (A95P, dict(motor="v2c8", M=100, amb=True)),
    "C2: pA 0,95, motor de placa, ambición solo con clase >= 5": (A95P, dict(motor="v2c8", M=100, amb=True, amb_si=((5, 6, 7), 0))),
    "C3: pA 0,95, motor de placa solo tras una apuesta": (A95P, dict(motor="v2c8", M=100)),
}
SIN_FASE_A = "sin fase A, motor de placa de 16 tramos, ambición siempre"
SOBRE30 = {"C1 sobre la banda 30": (A95P, dict(motor="v2c8", M=100, amb=True, clon="b30")),
           "C3 sobre la banda 30": (A95P, dict(motor="v2c8", M=100, clon="b30"))}
REF_ARGS = {"C1": dict(pin=0.95, placa2=True, tramos=8, M=100, amb=True),
            "C2": dict(pin=0.95, placa2=True, tramos=8, M=100, amb=True, amb_clases=(5, 6, 7)),
            "C3": dict(pin=0.95, placa2=True, tramos=8, M=100, amb=False),
            "sin fase A": dict(pin=2.0, placa2=False, tramos=16, M=100, amb=True),
            "C1 sobre la banda 30": dict(pin=0.95, placa2=True, tramos=8, M=100, amb=True, banda=30),
            "C3 sobre la banda 30": dict(pin=0.95, placa2=True, tramos=8, M=100, amb=False, banda=30),
            "C1 con margen 2": dict(pin=0.95, placa2=True, tramos=8, M=100, amb=True, Mslip=2)}


def _ref(i):
    import ideas
    w = _G["vent"][i]
    out = {}
    for k, kw in REF_ARGS.items():
        W, n, _ = ideas.correr(w, V.V5Ref(**kw))
        out[k] = (W, n)
    return i, out


def _apagado(i):
    """Bytes con todo apagado contra los de la banda 40, tick a tick."""
    w = _G["vent"][i]
    pre = _G["pre"][i]
    riv = {"b40": V.rival(w, "b40")}
    tr = []
    V.post(w, pre, V.fase_a(w, pre, SIN_A), riv, dict(motor="E0", M=100), tr)
    dc = riv["b40"][2]
    return sum(1 for n, d in tr if d != dc[n])


def etapa_finalistas():
    c, pre, WR = contexto("finalistas")
    var = dict(FINALISTAS)
    var.update(SOBRE30)
    var.update({"V4b": V4B, SIN_FASE_A: (SIN_A, dict(motor="v2c", M=100, amb=True)),
                "C1 con el motor de 16 tramos": (A95P, dict(motor="v2c", M=100, amb=True)),
                "C1 con M 200": (A95P, dict(motor="v2c8", M=200, amb=True)),
                "C1 con margen de 2 por acción": (A95P, dict(motor="v2c8", M=100, amb=True, Mslip=2)),
                "C1 con freno a la primera venta del clon": (A95P, dict(motor="v2c8", M=100, amb=True, frenos=(("ciclos", 1),))),
                "C1 con el motor apagado": (A95P, dict(motor="E0", M=100)),
                "todo apagado": (SIN_A, dict(motor="E0", M=100)),
                "E2 150/205 sin fase A (sin tablas)": (SIN_A, dict(motor="E2", M=100, amb=True, c2=150, v2=205))})
    res = evaluar(c, var, "finalistas")
    nombres = ["banda 40", "V4b"] + list(FINALISTAS) + [SIN_FASE_A, "banda 30 sola"] + list(SOBRE30)
    Ws = {"banda 40": WR["b40"], "banda 30 sola": WR["b30"]}
    Ws.update({nm: res[nm]["W"] for nm in var})
    subs = ["todas"] + [str(a) for a in XR.ANIOS_OTRAS] + ["tec", "fin", "sal", "con", "ind"]
    ind = indices(c, {k: Ws[k] for k in nombres}, subs, detalle=True)
    ind.update(indices(c, {k: Ws[k] for k in Ws if k not in nombres}))
    L = ["# V5: finalistas", "",
         f"ref/cotas/explorar_v5.py finalistas, commit {XR.commit()}. Otras acciones: {c.n} ventanas; {XC.SORTEOS} sorteos "
         "(60 000 por año y por grupo). Índice: nd = % de torneos de 3 rondas en que no queda debajo, g = % que gana; pesos "
         + ", ".join(f"{r} {V.PESOS[r]:.2f}" for r in V.RIVALES) + ". ee agrupado por fecha y empresa; las diferencias son pareadas.", ""]
    # controles
    L.append("## Controles\n")
    mal = sum(1 for i in range(c.n) if res["todo apagado"]["W"][i] != WR["b40"][i])
    L.append(f"- Todo apagado (sin fase A, sin motor): patrimonio distinto al de la banda 40 en {mal} ventanas de {c.n}.")
    rng = random.Random("v5-control")
    ids = sorted(rng.sample(range(c.n), 120))
    with Pool(os.cpu_count()) as pool:
        byt = sum(pool.imap_unordered(_apagado, ids))
        L.append(f"- Todo apagado, byte a byte contra la banda 40 desde el primer extremo en 120 ventanas: {byt} bytes distintos.")
        refs = dict(pool.imap_unordered(_ref, ids))
    malr = 0
    for k, nm in zip(("C1", "C2", "C3", "sin fase A", "C1 sobre la banda 30", "C3 sobre la banda 30", "C1 con margen 2"),
                     list(FINALISTAS) + [SIN_FASE_A] + list(SOBRE30) + ["C1 con margen de 2 por acción"]):
        d = sum(1 for i in ids if refs[i][k] != (res[nm]["W"][i], res[nm]["n"][i]))
        malr += d
        L.append(f"- {k}: v5.fase_a + v5.post contra la segunda implementación (`v5.V5Ref` en `ideas.correr`, tick a tick) en "
                 f"120 ventanas: {d} diferencias en patrimonio u órdenes.")
    base = evaluar(c, {"C1 base sola": (A95P, dict(motor="E0", M=V.INF))}, "control")["C1 base sola"]
    solo = evaluar(c, {"C1 motor apagado sin candado": (A95P, dict(motor="E0", M=V.INF, amb=True))}, "control")["C1 motor apagado sin candado"]
    L.append(f"- C1 con el motor apagado y sin candado, con y sin ambición: {sum(1 for i in range(c.n) if base['W'][i] != solo['W'][i])} "
             f"ventanas distintas de {c.n} (la base: fase A con pA >= 0,95 y después los bytes del clon).")
    if mal or byt or malr:
        print("\n".join(L))
        raise SystemExit("CONTROL DISTINTO DE CERO: se detiene")
    # índice
    L.append("\n## Índice, todas las ventanas\n")
    L.append("| Estrategia | nd (ee) | g (ee) | Δnd contra banda 40 (ee) | Δg contra banda 40 (ee) | Δnd contra V4b (ee) | Δg contra V4b (ee) | "
             "déficit ponderado (ee) | Δ déficit contra banda 40 (ee) | órdenes |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")

    def z(d, e):
        return f"{d:+.1f} ({e:.1f})".replace(".", ",")
    orden = nombres + [k for k in Ws if k not in nombres]
    for nm in orden:
        m = ind[(nm, "todas")][0]
        d1, d2 = dif(c, ind, nm, "banda 40"), dif(c, ind, nm, "V4b")
        no = fmt(sum(res[nm]["n"]) / c.n) if nm in res else "3,8"
        ca, cb = ind[(nm, "todas")][1]["dp"], ind[("banda 40", "todas")][1]["dp"]
        edp = XR.ee_contrib([x - y for x, y in zip(ca, cb)], c.G, True)[0]
        L.append(f"| {nm} | {fmt(m['nd'])} ({fmt(m['ee_nd'])}) | {fmt(m['g'])} ({fmt(m['ee_g'])}) | {z(d1[0], d1[1])} | {z(d1[2], d1[3])} | "
                 f"{z(d2[0], d2[1])} | {z(d2[2], d2[3])} | {m['dp']:.0f} ({m['ee_dp']:.0f}) | "
                 f"{m['dp'] - ind[('banda 40', 'todas')][0]['dp']:+.0f} ({edp:.0f}) | {no} |")
    C1 = list(FINALISTAS)[0]
    L.append("\nSi las dos cifras se promedian en una sola (nd + g) / 2, diferencia pareada contra cada vara:\n")
    L.append("| Estrategia | (nd + g) / 2 | contra banda 40 (ee) | contra V4b (ee) |")
    L.append("|---|---|---|---|")
    for nm in orden:
        m = ind[(nm, "todas")][0]
        cel = []
        for vara in ("banda 40", "V4b"):
            ca, cb = ind[(nm, "todas")][1], ind[(vara, "todas")][1]
            e = 100 * XR.ee_contrib([(a1 + a2 - b1 - b2) / 2 for a1, a2, b1, b2 in zip(ca["nd"], ca["g"], cb["nd"], cb["g"])], c.G, True)[0]
            mv = ind[(vara, "todas")][0]
            cel.append(z((m["nd"] + m["g"] - mv["nd"] - mv["g"]) / 2, e))
        L.append(f"| {nm} | {fmt((m['nd'] + m['g']) / 2)} | {cel[0]} | {cel[1]} |")
    L.append("\nDiferencias pareadas contra C1 (nd, g): " + "; ".join(
        f"{nm}: {z(*dif(c, ind, nm, C1)[:2])}, {z(*dif(c, ind, nm, C1)[2:])}" for nm in orden if nm not in ("banda 40", "V4b", C1)) + ".")
    L.append("\n## Contra cada rival, todas las ventanas\n")
    tabla_rivales(L, nombres, ind)
    # por año y grupo
    L.append("\n## Por año de inicio y por grupo de empresas: índice nd / g\n")
    L.append("| Estrategia | " + " | ".join(subs[1:]) + " |")
    L.append("|---|" + "---|" * (len(subs) - 1))
    for nm in nombres:
        L.append(f"| {nm} | " + " | ".join(f"{fmt(ind[(nm, s_)][0]['nd'])} / {fmt(ind[(nm, s_)][0]['g'])}" for s_ in subs[1:]) + " |")
    for vara in ("V4b", "banda 40"):
        L.append(f"\nDiferencia pareada contra {vara} en cada subconjunto: Δnd (ee) / Δg (ee)\n")
        L.append("| Estrategia | " + " | ".join(subs[1:]) + " |")
        L.append("|---|" + "---|" * (len(subs) - 1))
        for nm in list(FINALISTAS) + [SIN_FASE_A, "banda 30 sola"] + list(SOBRE30):
            cel = []
            for s_ in subs[1:]:
                d = dif(c, ind, nm, vara, s_)
                cel.append(f"{z(d[0], d[1])} / {z(d[2], d[3])}")
            L.append(f"| {nm[:2] if nm in FINALISTAS else nm.split(',')[0]} | " + " | ".join(cel) + " |")
    # por ronda: grupos y mecánica del candado
    L.append("\n## Una ronda: cómo termina (por caso) y mecánica del candado\n")
    L.append("| Estrategia | Caso | Candado tras apuesta % (D media) | Candado tras el motor % (D media) | Sin recuperar % (D media) | "
             "Sin desviar % | Rondas en candado que terminan con D < 0 % | Δ contra su clon (ee) |")
    L.append("|---|---|---|---|---|---|---|---|")
    b40 = WR["b40"]
    for nm in ["V4b"] + list(FINALISTAS) + [SIN_FASE_A, "C1 con margen de 2 por acción"] + list(SOBRE30):
        r = res[nm]
        for cs in ("S", "B"):
            idx = [i for i in range(c.n) if c.caso[i] == cs]
            cel = []
            for g in ("apuesta", "recuperacion", "sin_recuperar"):
                sel = [i for i in idx if r["g"][i] == g]
                cel.append(f"{fmt(100 * len(sel) / len(idx))} ({(sum(r['D'][i] for i in sel) / len(sel)) if sel else 0:+.0f})")
            sd = sum(1 for i in idx if r["g"][i] == "sin_desviar")
            lock = [i for i in idx if r["g"][i] in ("apuesta", "recuperacion")]
            neg = sum(1 for i in lock if r["D"][i] < 0)
            dm, ee = XR.delta(c.G, {"W": r["W"]}, {"W": WR[var[nm][1].get("clon", "b40")]}, idx)
            L.append(f"| {nm[:2] if nm in FINALISTAS else nm.split(',')[0]} | {cs} | " + " | ".join(cel) + f" | {fmt(100 * sd / len(idx))} | "
                     f"{fmt(100 * neg / len(lock)) if lock else '-'} | {dm:+.0f} ({ee:.0f}) |")
    # memoria entre rondas
    L.append("\n## Dato aparte (arista 10): memoria entre rondas\n")
    L.append("En el orden del sorteo: si la D acumulada contra el clon emulado ya es >= 100 al empezar una ronda, esa ronda copia a "
             "la banda 40 entera. No se sabe si está permitido; no entra en ningún candidato.\n")
    mem = indices(c, {nm + " con memoria": ("mem", Ws[nm], b40, 100) for nm in ["V4b"] + list(FINALISTAS)})
    L.append(CAB_IND)
    for nm in ["V4b"] + list(FINALISTAS):
        L.append(fila_indice(nm[:3].rstrip(":") + " sin memoria", ind[(nm, "todas")][0]))
        L.append(fila_indice(nm[:3].rstrip(":") + " con memoria", mem[(nm + " con memoria", "todas")][0]))
    pickle.dump({nm: ind[(nm, "todas")][0] for nm in orden}, open(os.path.join(CACHE, "finalistas_ind.pkl"), "wb"))
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "v5_finalistas.txt"), "w").write(txt)
    print(txt)



def etapa_regimen():
    """Arista 3: la ambición (motor desde D = 0) solo en ciertos regímenes: clase de v^2 y tiempo restante al primer extremo."""
    v = {"C1": FINALISTAS[list(FINALISTAS)[0]], "C3": FINALISTAS[list(FINALISTAS)[2]]}
    v["sin fase A, ambición solo con clase >= 5"] = (SIN_A, dict(motor="v2c8", M=100, amb=True, amb_si=((5, 6, 7), 0)))
    for k in (1, 2, 3, 4, 5, 6):
        v[f"C1, ambición solo con clase >= {k}"] = (A95P, dict(motor="v2c8", M=100, amb=True, amb_si=(tuple(range(k, 8)), 0)))
    for k in (2, 3, 4):
        v[f"C1, ambición solo con clase <= {k}"] = (A95P, dict(motor="v2c8", M=100, amb=True, amb_si=(tuple(range(-1, k + 1)), 0)))
    v["C1, ambición solo con clase >= 4 o sin clase"] = (A95P, dict(motor="v2c8", M=100, amb=True, amb_si=((-1, 4, 5, 6, 7), 0)))
    for r_ in (5000, 10000, 15000):
        v[f"C1, ambición solo con {r_} o más restantes"] = (A95P, dict(motor="v2c8", M=100, amb=True, amb_si=(None, r_)))
    v["C1, ambición con clase >= 4 y 10000 o más"] = (A95P, dict(motor="v2c8", M=100, amb=True, amb_si=((4, 5, 6, 7), 10000)))
    barrido("regimen", "la ambición solo en ciertos regímenes (arista 3)", v,
            ["C1 = fase A con pA >= 0,95 (2 bytes por celda), motor de placa de 8 tramos, candado copiar con M 100 y ambición. "
             "Aquí la ambición (correr el motor sin haber apostado) se condiciona a la clase de v^2 de placa en el tick del primer "
             "extremo (sin clase si el extremo llega antes del tick 390) y a los ticks que quedan."])



def etapa_base30():
    """La máquina de V5 sobre un clon de la banda 30 (se emula y se copia la banda 30 en vez de la 40), el motor con
    objetivo lineal y el margen por deslizamiento."""
    v = {"C1": FINALISTAS[list(FINALISTAS)[0]], "C2": FINALISTAS[list(FINALISTAS)[1]], "C3": FINALISTAS[list(FINALISTAS)[2]]}
    for nm in ("C1", "C2", "C3"):
        oa, op = v[nm]
        v[f"{nm} sobre la banda 30"] = (oa, dict(op, clon="b30"))
        v[f"{nm} con margen 2"] = (oa, dict(op, Mslip=2))
        v[f"{nm} sobre la banda 30 con margen 2"] = (oa, dict(op, clon="b30", Mslip=2))
    v["todo apagado sobre la banda 30"] = (SIN_A, dict(motor="E0", M=100, clon="b30"))
    v["C1 con el motor lineal de 8 tramos"] = (A95P, dict(motor="v2clin8", M=100, amb=True))
    v["sin fase A, motor lineal de 16 tramos"] = (SIN_A, dict(motor="v2clin", M=100, amb=True))
    v["sin fase A, motor log de 16 tramos"] = (SIN_A, dict(motor="v2c", M=100, amb=True))
    v["C3 con el motor lineal de 8 tramos"] = (A95P, dict(motor="v2clin8", M=100))
    for b in ("b50", "b60"):
        v[f"C3 sobre {b}"] = (A95P, dict(motor="v2c8", M=100, clon=b))
    c, res, ind = barrido("base30", "la máquina de V5 sobre un clon de la banda 30, motor lineal y margen por deslizamiento", v,
                          ["'sobre la banda 30': el rival emulado, al que se copia y contra el que se lleva D, es la banda 30 (130/225). "
                           "'margen 2': el candado exige D >= 100 + 2 por cada acción de diferencia con el clon. 'motor lineal': la tabla de "
                           "V2 con objetivo lineal (patrimonio esperado) en vez de logarítmico."])
    mal = sum(1 for i in range(c.n) if res["todo apagado sobre la banda 30"]["W"][i] != _G["WR"]["b30"][i])
    with open(os.path.join(SALIDA, "v5_base30.txt"), "a") as f:
        f.write(f"\nControl: con todo apagado sobre la banda 30, patrimonio distinto al de la banda 30 en {mal} ventanas de {c.n}.\n")
    print(f"CONTROL todo apagado sobre la banda 30: {mal} ventanas distintas")



ETAPAS = {"varas": etapa_varas, "faseD": etapa_faseD, "motor": etapa_motor, "faseA": etapa_faseA, "compuestas": etapa_compuestas, "ambicion": etapa_ambicion, "fino": etapa_fino, "finalistas": etapa_finalistas, "regimen": etapa_regimen, "base30": etapa_base30}

if __name__ == "__main__":
    if sys.argv[1] == "pre":
        contexto("pre")
    else:
        ETAPAS[sys.argv[1]]()
