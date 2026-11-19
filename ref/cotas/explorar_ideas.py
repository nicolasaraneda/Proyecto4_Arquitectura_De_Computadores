#!/usr/bin/env python3
"""explorar_ideas.py: evaluación de las ideas del 18/11 sobre la población real (docs/exploracion_ideas.md).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Población: las ventanas de 20 000 minutos de META, AAPL, NFLX, AMD y TSLA (2022 a 2024),
normalizadas con su mínimo y su máximo (ref/cotas/reales.py, decisión T134).
  muestra   estratificada por empresa y año de inicio: POR_ESTRATO ventanas de cada una de las
            15 combinaciones, sorteadas con la semilla (por omisión 18).
  completa  todas las ventanas (1 368 253), solo para las finalistas.
Separación de ajuste y validación, la misma de reales_experimento.py:
  años      ajuste: empiezan en 2022 o 2023; validación: enteras en 2024.
  empresas  ajuste: META, AAPL y NFLX; validación: AMD y TSLA.
Torneo de 3 rondas: tres ventanas sorteadas y 9 rivales que corren las tres (el mismo programa
en las tres rondas, como en la competencia); uno es siempre el rival de Tesla (unavez 100 220) y
los otros 8 se sortean del campo, dos tercios de las reglas con extremos y un tercio de las
otras (los campos de reales_experimento.py). Puntos lineales sobre la suma de las tres rondas:
0 al peor y 2 al mejor de los 10; 'primera sola' es terminar sobre todos los rivales, sin empate.
El patrimonio de los rivales sale de la caché en C de la población (reales.correr).

Los resultados se guardan en build/cotas/exploracion/ con una clave que incluye el código de
ideas.py, ideas_dp.py y este archivo, la estrategia y el conjunto de ventanas: si el código no
cambió, no se vuelve a correr. Cada salida anota el commit con que se generó.

Uso:
  python3 ref/cotas/explorar_ideas.py validar        motor contra Cotas y contra la caché en C
  python3 ref/cotas/explorar_ideas.py filtros        tabla de filtros (tabla 1)
  python3 ref/cotas/explorar_ideas.py idea N         barrido de la idea N (1 a 10) o combinaciones (11)
  python3 ref/cotas/explorar_ideas.py tabla          todas las ideas, ordenadas (tabla 2)
  python3 ref/cotas/explorar_ideas.py completa       finalistas en la población completa
  python3 ref/cotas/explorar_ideas.py tesla          idea 8 en la ronda de Tesla del 18/11
Opciones: --semilla S, --datos CARPETA, --procesos P.
"""
import argparse
import array
import hashlib
import json
import os
import pickle
import random
import subprocess
import sys
import time
import types
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402
import ideas  # noqa: E402
import reales  # noqa: E402

LARGO = reales.LARGO
EMPRESAS = reales.EMPRESAS
ANIOS = (2022, 2023, 2024)
POR_ESTRATO = 240
SEMILLA = 18
TORNEOS = 20000
CACHE = os.path.join(comun.BUILD, "exploracion")
SALIDA = os.path.join(comun.RAIZ, "docs", "mediciones", "exploracion")
RIVAL_TESLA = "unavez100_220"
CAMPO_SIN = ["nada", "siempre", "max_media", "regla_base", "media_e2", "media_e6", "zscore", "zscore_z2"]
CAMPO_COTAS = ["espera", "compra", "compra_banda40", "espera_banda40", "umbral170", "compra_a2_b2_banda40",
               RIVAL_TESLA]
COLUMNAS_C = sorted(set(CAMPO_SIN + CAMPO_COTAS + ["espera_banda60"]))
SEPARACIONES = {
    "anios": (lambda v: v[2] in (2022, 2023), lambda v: v[2] == 2024 and v[3] == 2024),
    "empresas": (lambda v: v[0] in ("META", "AAPL", "NFLX"), lambda v: v[0] in ("AMD", "TSLA")),
}


MOTOR = "motor-1"   # se cambia a mano si cambia la forma de evaluar en este archivo (normalización, motor)


def codigo():
    """Clave del código que decide: ideas.py, ideas_dp.py y la versión del motor de este archivo."""
    h = hashlib.sha256(MOTOR.encode())
    for f in ("ideas.py", "ideas_dp.py"):
        ruta = os.path.join(comun.AQUI, f)
        if os.path.exists(ruta):
            h.update(open(ruta, "rb").read())
    return h.hexdigest()[:16]


# Tipos de especificación definidos fuera de ideas.py (ideas_reloj.py, segunda tanda): su clave de caché
# agrega el código de su módulo. Para los tipos de ideas.py la clave queda igual que antes.
CODIGO_EXTRA = {}


def commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=comun.AQUI, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return "?"


# --- conjuntos de ventanas -------------------------------------------------------------------

class Conjunto:
    """Ventanas (empresa, inicio, año de inicio, año de fin). Si `bytes_` está, son las ventanas
    normalizadas; si no, se normalizan al vuelo desde las series."""

    def __init__(self, nombre, filas, carpeta):
        self.nombre, self.filas, self.carpeta = nombre, filas, carpeta
        self.series = {}
        self.ventanas = None

    def cargar_series(self):
        for emp in EMPRESAS:
            if emp not in self.series:
                fechas, _, x = reales.leer_sesion(self.carpeta, emp)
                lo, hi = reales.extremos_deslizantes(x, LARGO)
                self.series[emp] = (x, lo, hi)

    def ventana(self, i):
        if self.ventanas is not None:
            return self.ventanas[i]
        emp, s = self.filas[i][0], self.filas[i][1]
        x, lo, hi = self.series[emp]
        a, d = lo[s], hi[s] - lo[s]
        return bytes([int(100 + (v - a) * 155.0 / d + 0.5) for v in x[s:s + LARGO]])

    def normalizar_todas(self):
        self.cargar_series()
        self.ventanas = [self.ventana(i) for i in range(len(self.filas))]

    def clave(self):
        h = hashlib.sha256(self.nombre.encode())
        h.update(repr(self.filas[:50]).encode())
        h.update(str(len(self.filas)).encode())
        return h.hexdigest()[:12]


def muestra(carpeta, semilla=SEMILLA, por_estrato=POR_ESTRATO):
    filas = []
    for emp in EMPRESAS:
        fechas, _, x = reales.leer_sesion(carpeta, emp)
        n = len(x) - LARGO + 1
        for anio in ANIOS:
            cand = [s for s in range(n) if int(fechas[s][:4]) == anio]
            rng = random.Random(f"muestra-{semilla}-{emp}-{anio}")
            for s in sorted(rng.sample(cand, min(por_estrato, len(cand)))):
                filas.append((emp, s, anio, int(fechas[s + LARGO - 1][:4])))
    c = Conjunto(f"muestra-{semilla}-{por_estrato}", filas, carpeta)
    return c


def completa(carpeta, paso=1):
    filas = []
    for emp in EMPRESAS:
        fechas, _, x = reales.leer_sesion(carpeta, emp)
        for s in range(0, len(x) - LARGO + 1, paso):
            filas.append((emp, s, int(fechas[s][:4]), int(fechas[s + LARGO - 1][:4])))
    return Conjunto(f"completa-{paso}", filas, carpeta)


def rivales(conj):
    """Patrimonio de los rivales (y de las bandas 40 y 60 en C) en cada ventana del conjunto."""
    ruta = os.path.join(CACHE, f"rivales_{conj.clave()}.pkl")
    if os.path.exists(ruta):
        return pickle.load(open(ruta, "rb"))
    import reales_experimento as rx
    out = {n: array.array("i") for n in COLUMNAS_C}
    por_emp = {}
    for i, f in enumerate(conj.filas):
        por_emp.setdefault(f[0], []).append(i)
    orden = []
    for emp in EMPRESAS:
        if emp not in por_emp:
            continue
        r = reales.correr(rx.ESTR, conj.carpeta, emp)
        mv, ne = memoryview(r["w"]), r["ne"]
        assert r["ini"][0] == 0 and r["ini"][1] == 1
        for i in por_emp[emp]:
            s = conj.filas[i][1]
            for n in COLUMNAS_C:
                out[n].append(mv[s * ne + rx.J[n]])
            orden.append(i)
        del r, mv
    assert orden == list(range(len(conj.filas))), "las filas del conjunto deben venir ordenadas por empresa"
    os.makedirs(CACHE, exist_ok=True)
    pickle.dump(out, open(ruta, "wb"))
    return out


# --- evaluación en paralelo con caché --------------------------------------------------------

_G = {}
# Las cachés .pkl de build/cotas/exploracion/ las escribe solo este script en la máquina local;
# no se cargan archivos de otro origen.


def _trabajo(args):
    specs, ids = args
    conj = _G["conj"]
    out = [([], [], [], []) for _ in specs]
    antes = _G.get("antes")      # gancho opcional por ventana (explorar_ideas2.py: minutos del día para la idea 14)
    for i in ids:
        w = conj.ventana(i)
        if antes is not None:
            antes(i)
        for k, sp in enumerate(specs):
            s = ideas.crear(sp)
            W, n, dd = ideas.correr(w, s)
            o = out[k]
            o[0].append(W)
            o[1].append(n)
            o[2].append(dd)
            o[3].append(s.info() if _G.get("info", True) and hasattr(s, "info") else ())
    return ids, out


def evaluar(conj, specs, procesos=None, trozo=None, verbose=True, info=True):
    """Devuelve una lista (una por spec) de dict W, n, dd, info, alineadas con conj.filas."""
    cod = codigo()
    os.makedirs(CACHE, exist_ok=True)
    rutas = [os.path.join(CACHE, f"{conj.clave()}_"
                          f"{hashlib.sha256((cod + CODIGO_EXTRA.get(sp[0], '') + repr(sp)).encode()).hexdigest()[:20]}.pkl")
             for sp in specs]
    faltan = [k for k, r in enumerate(rutas) if not os.path.exists(r)]
    if faltan:
        sf = [specs[k] for k in faltan]
        nv = len(conj.filas)
        if conj.ventanas is None:
            conj.cargar_series()
        _G["conj"] = conj
        _G["info"] = info
        trozo = trozo or max(10, nv // ((procesos or os.cpu_count()) * 8))
        tareas = [(sf, list(range(a, min(nv, a + trozo)))) for a in range(0, nv, trozo)]
        res = [None] * len(sf)
        for k in range(len(sf)):
            res[k] = dict(W=array.array("i", [0] * nv), n=array.array("i", [0] * nv),
                          dd=array.array("f", [0.0] * nv), info=[None] * nv)
        t0 = time.time()
        with Pool(procesos or os.cpu_count()) as pool:
            for hechas, (ids, out) in enumerate(pool.imap_unordered(_trabajo, tareas), 1):
                for k, o in enumerate(out):
                    for j, i in enumerate(ids):
                        res[k]["W"][i] = o[0][j]
                        res[k]["n"][i] = o[1][j]
                        res[k]["dd"][i] = o[2][j]
                        res[k]["info"][i] = o[3][j]
                if verbose and hechas % max(1, len(tareas) // 10) == 0:
                    print(f"  {conj.nombre}: {hechas}/{len(tareas)} trozos, {time.time() - t0:.0f} s", file=sys.stderr)
        for k, r in zip(faltan, res):
            pickle.dump(r, open(rutas[k], "wb"))
    return [pickle.load(open(r, "rb")) for r in rutas]


# --- métricas y torneo -----------------------------------------------------------------------

def sub(conj, cond):
    return [i for i, f in enumerate(conj.filas) if cond(f)]


class Torneo:
    """Sorteo fijo de torneos de 3 rondas sobre un subconjunto (números aleatorios comunes a todas
    las estrategias)."""

    def __init__(self, idx, R, nombre, semilla=SEMILLA, n=TORNEOS, excluir=()):
        rng = random.Random(f"torneo3-{semilla}-{nombre}")
        self.v, self.lo, self.hi = [], [], []
        cotas = [c for c in CAMPO_COTAS if c not in excluir]
        sin = [c for c in CAMPO_SIN if c not in excluir]
        for _ in range(n):
            v = [idx[rng.randrange(len(idx))] for _ in range(3)]
            riv = [RIVAL_TESLA] if RIVAL_TESLA not in excluir else []
            while len(riv) < 9:
                riv.append(rng.choice(cotas if rng.random() < 2 / 3 else sin))
            sumas = [R[r][v[0]] + R[r][v[1]] + R[r][v[2]] for r in riv]
            self.v.append(v)
            self.lo.append(min(sumas))
            self.hi.append(max(sumas))

    def puntos(self, W):
        pts = pri = 0.0
        for v, lo_r, hi_r in zip(self.v, self.lo, self.hi):
            S = W[v[0]] + W[v[1]] + W[v[2]]
            lo, hi = min(lo_r, S), max(hi_r, S)
            pts += 1.0 if hi == lo else 2.0 * (S - lo) / (hi - lo)
            pri += S > hi_r
        return pts / len(self.v), pri / len(self.v)


def metricas(r, idx, R, torneo):
    W = sorted(r["W"][i] for i in idx)
    n = len(W)
    bh = sum(R["siempre"][i] for i in idx) / n
    media = sum(W) / n
    pts, pri = torneo.puntos(r["W"])
    nord = sum(r["n"][i] for i in idx) / n
    return dict(n=n, media=media, mediana=W[n // 2], p5=W[int(0.05 * (n - 1))], peor=W[0], bh=media / bh,
                ordenes=nord, comisiones=5 * nord, dd=100 * sum(r["dd"][i] for i in idx) / n, pts=pts, pri=100 * pri)


CAB = (f"{'estrategia':34s} {'pts':>5s} {'1a %':>5s} {'media':>7s} {'mediana':>7s} {'p5':>6s} {'peor':>6s} "
       f"{'/cym':>5s} {'ord':>5s} {'com':>5s} {'dd %':>5s}")


def linea(nombre, m):
    return (f"{nombre:34s} {m['pts']:5.3f} {m['pri']:5.1f} {m['media']:7.0f} {m['mediana']:7d} {m['p5']:6d} "
            f"{m['peor']:6d} {m['bh']:5.2f} {m['ordenes']:5.1f} {m['comisiones']:5.0f} {m['dd']:5.1f}")


# --- validación del motor --------------------------------------------------------------------

def validar(carpeta, procesos=None):
    import market
    import trader
    from regla_cotas import Cotas
    L = [f"Validacion del motor de ideas.py (commit {commit()})", ""]
    tesla = market.leer_serie(os.path.join(os.path.dirname(carpeta), "capturas", "ronda_10ms_clase.csv"))
    for b, esperado in ((60, 18779), (40, None)):
        W = ideas.correr(tesla, ideas.crear(("banda", {"w": b})))[0]
        ref = trader.correr(tesla, Cotas("espera", banda=b)).w
        L.append(f"Tesla 18/11, banda {b}: motor {W}, Cotas {ref}" + (f", maestra {esperado}" if esperado else "")
                 + ("  PASS" if W == ref and (esperado is None or W == esperado) else "  FAIL"))
    W = ideas.correr(tesla, ideas.crear(("novuelve", {"H": 220})))[0]
    L.append(f"Tesla 18/11, fases A-C y 'vende con 220 o mas y no vuelve' en D: {W} (el rival dio 21 467)")
    conj = muestra(carpeta)
    R = rivales(conj)
    res = evaluar(conj, [("banda", {"w": 40}), ("banda", {"w": 60})], procesos)
    malos = sum(1 for k, n in enumerate(("espera_banda40", "espera_banda60"))
                for i in range(len(conj.filas)) if res[k]["W"][i] != R[n][i])
    L.append(f"Muestra ({len(conj.filas)} ventanas): bandas 40 y 60 del motor contra la cache en C: {malos} diferencias"
             + ("  PASS" if malos == 0 else "  FAIL"))
    # Python puro (trader.correr + Cotas) en 40 ventanas
    conj.normalizar_todas()
    malos = 0
    for i in range(0, len(conj.filas), len(conj.filas) // 40):
        w = list(conj.ventanas[i])
        for b in (40, 60):
            malos += ideas.correr(w, ideas.crear(("banda", {"w": b})))[0] != trader.correr(w, Cotas("espera", banda=b)).w
    L.append(f"40 ventanas de la muestra contra trader.correr + Cotas: {malos} diferencias" + ("  PASS" if malos == 0 else "  FAIL"))
    return L


# --- especificaciones -------------------------------------------------------------------------

B40, B60, TRES = ("banda", {"w": 40}), ("banda", {"w": 60}), ("tres", {})
BASES = [("banda 40", B40), ("banda 60", B60), ("tres bandas por hilo", TRES)]
RANGOS = ((100, 255), (110, 245), (120, 215), (130, 200))
GRILLA4 = ("grilla", {"N": 4, "Linf": 100, "Lsup": 255, "modo": "fraccion"})
GRILLA_OSC = ("grilla", {"N": 4, "Linf": 120, "Lsup": 215, "modo": "fraccion"})   # rango que pasa el filtro de la idea 2
# Representante fijo (sin barrido) de las ideas que no pasan su filtro, para la tabla 2
REPRESENTANTE = {1: ("dp", {"objetivo": "log_exacto", "version": "placa", "modo": "cambios"}),
                 5: ("cuantil", {"qc": 0.25, "qv": 0.75, "origen": "inicio", "calor": 1950}),
                 6: ("contadores", {"h": 4, "xor": False})}
CUENTAS_SOMBRA = ([("regla", B40)]
                  + [("regla", ("bandac", {"ancho": a, "centro": c})) for a in (10, 20, 40, 60, 76) for c in (160, 177, 195)]
                  + [("unavez", 100, 220), ("siempre",), ("regla", GRILLA4)])
CUENTAS_TRES = [("regla", B40), ("unavez", 100, 220), ("regla", GRILLA4)]


def nombre(sp):
    t, kw = sp
    if t == "bandac":
        c = kw["centro"] - kw["ancho"] // 2
        return f"banda compra<={c} vende>={c + kw['ancho']}"
    if t in ("banda", "tres", "grilla", "novuelve", "bandac"):
        return t + " " + " ".join(f"{k}={v}" for k, v in kw.items()) if t != "tres" else "tres bandas"
    if t == "regla":
        return nombre(kw)
    if t == "inicio":
        fr = {1 / 3: "1/3", 2 / 3: "2/3", 1.0: "todo"}.get(kw["f"], str(kw["f"]))
        cond = f"p0>={kw['u']}" if kw["T"] == 0 else f"p({kw['T']})-p0>={kw['u']}"
        return f"inicio: si {cond} compra {fr}; banda {kw['w']}"
    if t == "sombra":
        return f"sombra {len(kw['cuentas'])}c R={kw['R']} M=1/{round(1 / kw['Mg'])} {kw['modo']}"
    return t + " " + " ".join(f"{k}={v if not isinstance(v, tuple) else nombre(v)}" for k, v in kw.items()
                              if k not in ("cuentas",))


def idea_specs(n):
    """Barrido de cada idea: lista de especificaciones."""
    if n == 1:
        return [("dp", {"objetivo": o, "version": v, "modo": m}) for o in ("log", "log_exacto", "lineal")
                for v in ("placa", "fino") for m in ("cambios", "varianza")]
    if n == 2:
        return [("grilla", {"N": N, "Linf": a, "Lsup": b, "modo": m}) for N in (2, 3, 4, 6, 8, 12)
                for a, b in RANGOS for m in ("fijas", "fraccion")]
    if n == 3:
        return [("sombra", {"cuentas": CUENTAS_SOMBRA, "R": R, "Mg": Mg, "modo": m}) for R in (100, 390, 1000)
                for Mg in (1 / 64, 1 / 32, 1 / 16) for m in ("lider", "tercios")]
    if n == 4:
        out = []
        umb = {"vr16": (0.70, 0.85, 1.00, 1.15), "vr64": (0.70, 0.85, 1.00, 1.15), "vr390": (0.70, 0.85, 1.00, 1.15),
               "cruces": (0.34, 1.2, 2.7), "desde": (3, 10, 75, 341)}
        for ind, us in umb.items():
            for u1 in us:
                for u2 in us:
                    if u2 >= u1:
                        for sg in (1, -1):
                            for osc in (B60, GRILLA_OSC):
                                out.append(("regimen", {"ind": ind, "u1": u1, "u2": u2, "sentido": sg, "osc": osc}))
        return out
    if n == 5:
        return [("cuantil", {"qc": qc, "qv": qv, "origen": o, "calor": c}) for o in ("inicio", "D", "olvido")
                for qc in (0.125, 0.25, 0.375) for qv in (0.625, 0.75, 0.875) for c in (390, 1950, 3900)]
    if n == 6:
        return [("contadores", {"h": h, "xor": x}) for h in (2, 3, 4, 6) for x in (False, True)]
    if n == 7:
        return [("cobertura", {"base": b, "m": m, "Tc": Tc}) for b in (B40, B60) for m in (2, 5, 10)
                for Tc in (20000, 5000, 2000, 500)]
    if n == 8:
        return ([("final", {"base": b, "var": v, "Tf": Tf}) for b in (B40, B60) for v in ("a", "b", "c")
                 for Tf in (100, 390, 1000, 2000)] + [("final", {"base": b, "var": "c", "Tf": 3}) for b in (B40, B60)])
    if n == 9:
        out = [("inicio", {"u": u, "f": f, "T": 0, "w": 40}) for u in range(150, 241, 10) for f in (1 / 3, 2 / 3, 1.0)]
        out += [("inicio", {"u": u, "f": f, "T": T, "w": 40}) for T in (390, 1950) for u in (-20, -10, 0, 10, 20, 30)
                for f in (1 / 3, 2 / 3, 1.0)]
        return out
    if n == 12:
        return [("bandac", {"ancho": v - c, "centro": c + (v - c) // 2}) for c in (120, 130, 135, 140, 145, 150, 160)
                for v in (195, 205, 210, 215, 220, 225, 230, 235)]
    if n == 10:
        return [("caida", {"w": w, "dd": d, "g": g, "reentrada": r}) for w in (40, 60) for d in (5, 10, 15, 20, 30)
                for g in (20, 40, 60) for r in ("banda", "rebote")]
    raise ValueError(n)


# --- filtros ----------------------------------------------------------------------------------

def spearman(a, b):
    def rangos(x):
        orden = sorted(range(len(x)), key=lambda i: x[i])
        r = [0.0] * len(x)
        i = 0
        while i < len(x):
            j = i
            while j + 1 < len(x) and x[orden[j + 1]] == x[orden[i]]:
                j += 1
            for k in range(i, j + 1):
                r[orden[k]] = (i + j) / 2
            i = j + 1
        return r
    ra, rb = rangos(a), rangos(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    saa = sum((x - ma) ** 2 for x in ra)
    sbb = sum((y - mb) ** 2 for y in rb)
    return sab / (saa * sbb) ** 0.5 if saa > 0 and sbb > 0 else None


class Ctx:
    """Muestra, rivales, torneos y separaciones, para no repetirlos."""

    def __init__(self, carpeta, semilla=SEMILLA, procesos=None):
        self.semilla, self.procesos = semilla, procesos
        self.conj = muestra(carpeta, semilla)
        self.R = rivales(self.conj)
        self.todo = list(range(len(self.conj.filas)))
        self.T = {"muestra": Torneo(self.todo, self.R, "muestra", semilla)}
        self.idx = {"muestra": self.todo}
        for sep, (aj, va) in SEPARACIONES.items():
            for parte, cond in (("ajuste", aj), ("validacion", va)):
                k = f"{sep}-{parte}"
                self.idx[k] = sub(self.conj, cond)
                self.T[k] = Torneo(self.idx[k], self.R, k, semilla)

    def ev(self, specs):
        return evaluar(self.conj, specs, self.procesos, verbose=False)

    def m(self, r, parte="muestra"):
        return metricas(r, self.idx[parte], self.R, self.T[parte])


def filtros(cx):
    F = []           # (idea, filtro, número, pasa)
    D = ["Detalle de los filtros (ref/cotas/explorar_ideas.py filtros), muestra estratificada "
         f"{cx.conj.nombre} ({len(cx.todo)} ventanas), commit {commit()}", ""]
    rb = cx.ev([B40, B60, TRES, ("novuelve", {"H": 220})])
    mb = {n: cx.m(r) for (n, _), r in zip(BASES + [("no vuelve", None)], rb)}
    D += ["== Bases en la muestra", CAB] + [linea(n, m) for n, m in mb.items()]

    # idea 1
    sp = idea_specs(1)
    r1 = cx.ev(sp)
    D += ["", "== Idea 1: umbrales de la programacion dinamica contra la banda 40 (puntos del torneo en la muestra)", CAB]
    for s_, r in zip(sp, r1):
        D.append(linea(nombre(s_), cx.m(r)))
    placa = cx.m(r1[sp.index(("dp", {"objetivo": "log_exacto", "version": "placa", "modo": "cambios"}))])
    mejor = max((cx.m(r)["pts"], nombre(s_)) for s_, r in zip(sp, r1))
    F.append((1, "puntos de la tabla de placa (log exacto) contra banda 40", f"{placa['pts']:.3f} contra {mb['banda 40']['pts']:.3f}"
              f" (mejor variante: {mejor[1]}, {mejor[0]:.3f})", mejor[0] > mb["banda 40"]["pts"]))

    # idea 2
    sp = [("grilla", {"N": 4, "Linf": a, "Lsup": b, "modo": "fraccion"}) for a, b in RANGOS]
    r2 = cx.ev(sp)
    D += ["", "== Idea 2: idas y vueltas completas por ventana en la fase D con N = 4 (tramo comprado y despues vendido)"]
    vals = []
    for s_, r in zip(sp, r2):
        v = [i[1] for i in r["info"] if i[0] >= 0]
        x = sum(v) / len(v)
        vals.append((x, s_[1]["Linf"], s_[1]["Lsup"]))
        dist = [sum(1 for y in v if y == k) for k in range(4)] + [sum(1 for y in v if y >= 4)]
        D.append(f"   ({s_[1]['Linf']}, {s_[1]['Lsup']}): {x:5.2f} por ventana; ventanas con 0, 1, 2, 3, 4+: {dist}")
    F.append((2, "idas y vueltas por ventana en D con N = 4 (minimo 1)",
              ", ".join(f"({a},{b}) {x:.2f}" for x, a, b in vals), max(vals)[0] >= 1))

    # idea 3
    r3 = cx.ev([("sonda_sombra", {"cuentas": CUENTAS_SOMBRA})])[0]
    rho, rhoD = [], []
    for inf in r3["info"]:
        tD, mitad, fin, d0, dm = inf
        seg = [f / m for f, m in zip(fin, mitad)]
        x = spearman(mitad, seg)
        if x is not None:
            rho.append(x)
        if tD >= 0 and dm is not None:
            a_ = [m / z for m, z in zip(dm, d0)]
            b_ = [f / m for f, m in zip(fin, dm)]
            y = spearman(a_, b_)
            if y is not None:
                rhoD.append(y)
    D += ["", "== Idea 3: correlacion de rangos (Spearman) entre el orden de las cuentas a mitad de ventana y su",
          f"   rendimiento en la segunda mitad: media {sum(rho) / len(rho):+.3f} en {len(rho)} ventanas",
          f"   dentro de la fase D (rendimiento en la primera mitad de D contra la segunda): media {sum(rhoD) / len(rhoD):+.3f}"
          f" en {len(rhoD)} ventanas", f"   cuentas: {len(CUENTAS_SOMBRA)}"]
    F.append((3, "Spearman del orden a mitad de ventana contra la segunda mitad (pasa si >= 0,2)",
              f"{sum(rho) / len(rho):+.3f} (dentro de D: {sum(rhoD) / len(rhoD):+.3f})", sum(rho) / len(rho) >= 0.2))

    # idea 4
    r4 = cx.ev([("sonda_regimen", {})])[0]
    w40, wnv = rb[0]["W"], rb[3]["W"]
    D += ["", "== Idea 4: el indicador hasta la entrada a D predice quien gana despues, banda 40 o 'vende con 220 o mas y no vuelve'"]
    filas4 = []
    for i, inf in enumerate(r4["info"]):
        if inf[0] >= 0 and w40[i] != wnv[i]:
            filas4.append((i, inf[1], 1 if wnv[i] > w40[i] else 0))
    gana_nv = sum(f[2] for f in filas4) / len(filas4)
    empates = sum(1 for i, inf in enumerate(r4["info"]) if inf[0] >= 0 and w40[i] == wnv[i])
    D.append(f"   ventanas con D: {len(filas4) + empates}; empates {empates}; sin empate gana 'no vuelve' en {100 * gana_nv:.1f} %")
    aj_set = set(cx.idx["anios-ajuste"])
    va_set = set(cx.idx["anios-validacion"])
    mejor4 = None
    for j, ind in enumerate(ideas.IND):
        xs = sorted(f[1][j] for f in filas4 if f[0] in aj_set)
        umbrales = [xs[int(k * (len(xs) - 1) / 20)] for k in range(1, 20)]
        if ind.startswith("vr"):
            umbrales = sorted(set(umbrales + [0.70, 0.85, 1.00, 1.15]))
        best = None
        for u in umbrales:
            for sg in (1, -1):
                ac = [(1 if (f[1][j] > u) == (sg > 0) else 0) == f[2] for f in filas4 if f[0] in aj_set]
                a = sum(ac) / len(ac)
                if best is None or a > best[0]:
                    best = (a, u, sg)
        a, u, sg = best
        av = [(1 if (f[1][j] > u) == (sg > 0) else 0) == f[2] for f in filas4 if f[0] in va_set]
        acv = sum(av) / len(av)
        mayo_v = sum(f[2] for f in filas4 if f[0] in va_set) / len(av)
        D.append(f"   {ind:7s}: umbral elegido en el ajuste (anios) {u:8.3f}, 'no vuelve' si el indicador esta "
                 f"{'sobre' if sg > 0 else 'bajo'} el umbral; acierto ajuste {100 * a:5.1f} %, validacion {100 * acv:5.1f} % "
                 f"(clase mayoritaria en la validacion: {100 * max(mayo_v, 1 - mayo_v):5.1f} %)")
        if mejor4 is None or a > mejor4[3]:
            mejor4 = (acv, ind, max(mayo_v, 1 - mayo_v), a)
    D.append(f"   indicador con mas acierto en el ajuste: {mejor4[1]}; su acierto en la validacion es el numero del filtro")
    F.append((4, "acierto en la validacion por anios del indicador elegido en el ajuste (pasa si >= 55 %)",
              f"{100 * mejor4[0]:.1f} % con {mejor4[1]} (clase mayoritaria {100 * mejor4[2]:.1f} %)", mejor4[0] >= 0.55))

    # idea 5
    sp = idea_specs(5)
    r5 = cx.ev(sp)
    anchos = []
    for s_, r in zip(sp, r5):
        sa = sum(i[1] for i in r["info"] if i[0] >= 0)
        na = sum(i[2] for i in r["info"] if i[0] >= 0)
        anchos.append(sa / na if na else 155 - 80)
    wfijas = sorted({max(0, min(77, round((155 - a) / 2))) for a in anchos})
    rf = dict(zip(wfijas, cx.ev([("banda", {"w": w}) for w in wfijas])))
    D += ["", "== Idea 5: bandas por cuantiles contra la banda fija del mismo ancho medio (w = (155 - ancho) / 2)",
          f"{'variante':58s} {'ancho':>6s} {'w fija':>6s} {'pts':>6s} {'pts fija':>8s} {'media':>7s} {'media fija':>10s}"]
    ganan = 0
    for s_, r, a in zip(sp, r5, anchos):
        w = max(0, min(77, round((155 - a) / 2)))
        m, mf = cx.m(r), cx.m(rf[w])
        ganan += m["pts"] > mf["pts"]
        D.append(f"{nombre(s_):58s} {a:6.1f} {w:6d} {m['pts']:6.3f} {mf['pts']:8.3f} {m['media']:7.0f} {mf['media']:10.0f}")
    F.append((5, "variantes de cuantiles que superan a la banda fija del mismo ancho medio, en puntos (pasa si > 50 %)",
              f"{ganan} de {len(sp)}", ganan > len(sp) / 2))

    # idea 6
    sp = idea_specs(6)
    r6 = cx.ev(sp)
    D += ["", "== Idea 6: cambio medio de precio que sigue a una decision con el contador saturado (fase D)"]
    mejor6 = None
    for s_, r in zip(sp, r6):
        su = sum(i[1] for i in r["info"] if i[0] >= 0)
        cu = sum(i[2] for i in r["info"] if i[0] >= 0)
        sd = sum(i[3] for i in r["info"] if i[0] >= 0)
        cd = sum(i[4] for i in r["info"] if i[0] >= 0)
        eu, ed = su / max(1, cu), sd / max(1, cd)
        D.append(f"   {nombre(s_):28s} contador en 3: {cu:9d} veces, E[cambio] {eu:+.4f}, 63 x E = {63 * eu:+6.2f};"
                 f" contador en 0: {cd:9d} veces, E[cambio] {ed:+.4f}")
        if mejor6 is None or eu > mejor6[0]:
            mejor6 = (eu, nombre(s_))
    F.append((6, "63 x E[p(n+1) - p(n)] con el contador en 3 (pasa si >= 10)", f"{63 * mejor6[0]:+.2f} (mejor: {mejor6[1]})",
              63 * mejor6[0] >= 10))

    # idea 7 (filtro propio): cuánto se activa la condición de cobertura
    sp = [("cobertura", {"base": B40, "m": m, "Tc": 20000}) for m in (2, 5, 10)]
    r7 = cx.ev(sp)
    D += ["", "== Idea 7 (diagnostico, el pedido no trae filtro): ventanas en que la condicion de copia se activa alguna vez"]
    act = []
    for s_, r in zip(sp, r7):
        x = sum(1 for i in r["info"] if i[0] >= 0 and i[1] > 0) / len(r["info"])
        act.append(x)
        D.append(f"   m = {s_[1]['m']:2d} %: se activa en {100 * x:5.1f} % de las ventanas; copias por ventana "
                 f"{sum(i[1] for i in r['info'] if i[0] >= 0) / len(r['info']):.2f}")
    F.append((7, "sin filtro en el pedido; diagnostico: ventanas en que la copia se activa alguna vez (m = 2 %, Tc = 20 000)",
              f"{100 * act[0]:.1f} %", None))

    # idea 8 (filtro propio): ventanas que terminan invertidas y bajo el precio de entrada
    D += ["", "== Idea 8 (diagnostico): ventanas que terminan con la banda 40 invertida bajo su ultima compra"]
    conj = cx.conj
    if conj.ventanas is None:
        conj.normalizar_todas()
    abajo = 0
    for i in cx.todo:
        w = conj.ventanas[i]
        s_ = ideas.crear(B40)
        e = None
        acc_prev = 0
        caja, acc, d = ideas.CAJA0, 0, ideas.M
        for p in w:
            a = d >> 6
            if a == 1:
                q = min(d & 63, (caja - 5) // p)
                if q > 0:
                    caja -= q * p + 5
                    acc += q
            elif a == 2:
                q = min(d & 63, acc)
                if q > 0:
                    caja += q * p - 5
                    acc -= q
            if acc > 0 and acc_prev == 0:
                e = p
            acc_prev = acc
            d = s_.decidir(p, caja, acc)
        if acc > 0 and s_.tD >= 0 and e is not None and w[-1] < e:
            abajo += 1
    x8 = abajo / len(cx.todo)
    D.append(f"   {100 * x8:.1f} % de las ventanas")
    F.append((8, "sin filtro en el pedido; diagnostico: ventanas que terminan invertidas en D bajo el precio de entrada (banda 40)",
              f"{100 * x8:.1f} %", None))

    # idea 9
    D += ["", "== Idea 9: probabilidad de que el 255 llegue antes que el 100 segun p0, contra el paseo sin memoria (p0-100)/155"]
    tab = {}
    for i in cx.todo:
        w = conj.ventanas[i]
        b = min(15, (w[0] - 100) // 10)
        primero255 = w.index(255) < w.index(100)
        t = tab.setdefault(b, [0, 0])
        t[0] += 1
        t[1] += primero255
    ventaja = []
    for b in sorted(tab):
        n_, k_ = tab[b]
        centro = 100 + 10 * b + 5
        pa = (centro - 100) / 155
        ventaja.append((b, k_ / n_ - pa, n_))
        D.append(f"   p0 en {100 + 10 * b:3d}-{min(255, 109 + 10 * b):3d}: {n_:5d} ventanas, P(255 antes) = {k_ / n_:5.3f};"
                 f" paseo {pa:5.3f}; diferencia {k_ / n_ - pa:+.3f}")
    for T in (390, 1950):
        D.append(f"   pendiente de los primeros {T} ticks (ventanas que siguen en la fase A en el tick {T}):")
        tb = {}
        for i in cx.todo:
            w = conj.ventanas[i]
            i100, i255 = w.index(100), w.index(255)
            if min(i100, i255) <= T:
                continue
            b = max(-4, min(4, (w[T] - w[0]) // 10))
            t = tb.setdefault(b, [0, 0, 0.0])
            t[0] += 1
            t[1] += i255 < i100
            t[2] += (w[T] - 100) / 155
        for b in sorted(tb):
            n_, k_, pa = tb[b]
            D.append(f"     p(T)-p0 en [{10 * b:4d},{10 * b + 9:4d}]: {n_:5d} ventanas, P(255 antes) {k_ / n_:5.3f}, paseo desde p(T) {pa / n_:5.3f}")
    pos = [b for b, d_, n_ in ventaja if d_ > 0.03 and n_ >= 50]
    F.append((9, "rangos de p0 donde P(255 antes) real supera al paseo por mas de 0,03 (con 50 ventanas o mas; pasa si hay alguno)",
              ", ".join(f"{100 + 10 * b}-{109 + 10 * b} ({d_:+.2f})" for b, d_, n_ in ventaja if b in pos) or "ninguno",
              len(pos) > 0))

    # idea 10 (filtro propio)
    D += ["", "== Idea 10 (diagnostico): ventanas en que, en D, tras comprar, el precio sube 20 o mas y vuelve bajo la entrada",
          "   antes de que la banda 40 venda"]
    hay = 0
    for i in cx.todo:
        w = conj.ventanas[i]
        s_ = ideas.crear(("caida", {"w": 40, "dd": 1000, "g": 20, "reentrada": "banda"}))
        caja, acc, d = ideas.CAJA0, 0, ideas.M
        e, mx, acc_prev, visto = None, 0, 0, False
        for p in w:
            a = d >> 6
            if a == 1:
                q = min(d & 63, (caja - 5) // p)
                if q > 0:
                    caja -= q * p + 5
                    acc += q
            elif a == 2:
                q = min(d & 63, acc)
                if q > 0:
                    caja += q * p - 5
                    acc -= q
            if acc > 0 and acc_prev == 0:
                e, mx = p, p
            acc_prev = acc
            if acc > 0 and s_.tD >= 0 and e is not None:
                mx = max(mx, p)
                if mx >= e + 20 and p < e:
                    visto = True
            d = s_.decidir(p, caja, acc)
        hay += visto
    x10 = hay / len(cx.todo)
    D.append(f"   {100 * x10:.1f} % de las ventanas")
    F.append((10, "sin filtro en el pedido; diagnostico: ventanas con una subida de 20 que se devuelve bajo la entrada",
              f"{100 * x10:.1f} %", None))
    return F, D


# --- barridos con ajuste y validación ---------------------------------------------------------

CLASE = {1: "A", 2: "B", 3: "A", 4: "B", 5: "A", 6: "A", 7: "B", 8: "B", 9: "B", 10: "B", 11: "B", 12: "B"}
TITULO = {1: "Política por programación dinámica", 2: "Grilla con compensación", 3: "Torneo en sombra",
          4: "Detector de régimen", 5: "Bandas por cuantiles", 6: "Predictor de contadores saturados",
          7: "Cobertura contra rivales emulados", 8: "Final de ronda", 9: "Decisión según el precio inicial",
          10: "Salida por caída desde el máximo", 11: "Combinaciones",
          12: "Banda asimétrica (agregada: en Tesla decidió el nivel de venta)"}


def cluster(f):
    return (f[0], f[1] // 7800)


def delta_ee(cx, rA, rB, idx):
    """Diferencia media de patrimonio A - B y su error estándar por grupos de ventanas vecinas
    (misma empresa y mismo bloque de 20 días de inicio)."""
    d = [rA["W"][i] - rB["W"][i] for i in idx]
    n = len(d)
    m = sum(d) / n
    g = {}
    for i, x in zip(idx, d):
        k = cluster(cx.conj.filas[i])
        g[k] = g.get(k, 0.0) + (x - m)
    return m, (sum(v * v for v in g.values())) ** 0.5 / n


def barrido(cx, n, specs=None, extra_bases=()):
    sp = specs if specs is not None else idea_specs(n)
    res = cx.ev(sp)
    rb = cx.ev([b for _, b in BASES] + [b for _, b in extra_bases])
    nb = [nm for nm, _ in BASES] + [nm for nm, _ in extra_bases]
    L = [f"Idea {n}: {TITULO[n]} (clase {CLASE[n]}). ref/cotas/explorar_ideas.py idea {n} --semilla {cx.semilla}, "
         f"commit {commit()}", f"Muestra {cx.conj.nombre}: {len(cx.todo)} ventanas; {len(sp)} variantes. Se elige la de mas "
         "puntos de torneo en el ajuste y se informa en la validacion.", ""]
    out = {"n": n, "specs": {}, "bases": {}}
    for sep in SEPARACIONES:
        aj, va = f"{sep}-ajuste", f"{sep}-validacion"
        ma = [cx.m(r, aj) for r in res]
        orden = sorted(range(len(sp)), key=lambda k: -ma[k]["pts"])
        L += [f"== separacion por {sep}: ajuste {len(cx.idx[aj])} ventanas, validacion {len(cx.idx[va])}",
              "   diez mejores en el ajuste:", "   " + CAB]
        L += ["   " + linea(nombre(sp[k])[:34], ma[k]) for k in orden[:10]]
        L += ["   bases en el ajuste:"] + ["   " + linea(nm, cx.m(r, aj)) for nm, r in zip(nb, rb)]
        k0 = orden[0]
        mv = cx.m(res[k0], va)
        d40, ee40 = delta_ee(cx, res[k0], rb[0], cx.idx[va])
        d60, ee60 = delta_ee(cx, res[k0], rb[1], cx.idx[va])
        L += [f"   en la validacion (elegida: {nombre(sp[k0])}):", "   " + CAB, "   " + linea("ELEGIDA", mv)]
        L += ["   " + linea(nombre(sp[k])[:34], cx.m(res[k], va)) for k in orden[1:5]]
        L += ["   " + linea(nm, cx.m(r, va)) for nm, r in zip(nb, rb)]
        L += [f"   diferencia media de patrimonio en la validacion: contra banda 40 {d40:+.0f} (ee {ee40:.0f}), "
              f"contra banda 60 {d60:+.0f} (ee {ee60:.0f})", ""]
        info = [r for r in res[k0]["info"]]
        out["specs"][sep] = dict(spec=sp[k0], nombre=nombre(sp[k0]), ajuste=ma[k0], validacion=mv,
                                 d40=(d40, ee40), d60=(d60, ee60))
        out["bases"][sep] = {nm: dict(ajuste=cx.m(r, aj), validacion=cx.m(r, va)) for nm, r in zip(nb, rb)}
    return L, out


def guardar_idea(n, L, out):
    open(os.path.join(SALIDA, f"idea{n}.txt"), "w").write("\n".join(L) + "\n")
    out["commit"] = commit()
    json.dump(out, open(os.path.join(SALIDA, f"idea{n}.json"), "w"), indent=1, default=list)


def combinaciones(d, sep):
    """Combinaciones con los componentes elegidos en el ajuste de la separación sep (sin mezclar separaciones):
    2+4+8, 5+8, 10+8 y la idea 3 con tres cuentas (banda 40, vende alto y no vuelve, grilla de 4)."""
    el = {n: desjson(d[n]["specs"][sep]["spec"]) for n in d if n <= 10}
    finales = [("a", 1000), ("a", 2000), ("b", 390), ("b", 1000), ("c", 390)]
    out = []
    if 4 in el and 2 in el:
        rg = dict(el[4][1])
        rg["osc"] = el[2]
        for v, Tf in finales:
            out.append(("final", {"base": ("regimen", rg), "var": v, "Tf": Tf}))
    for n in (5, 10):
        if n in el:
            for v, Tf in finales:
                out.append(("final", {"base": el[n], "var": v, "Tf": Tf}))
    out += [("sombra", {"cuentas": CUENTAS_TRES, "R": R, "Mg": Mg, "modo": m}) for R in (100, 390, 1000)
            for Mg in (1 / 64, 1 / 32, 1 / 16) for m in ("lider", "tercios")]
    return out


def barrido_combinaciones(cx):
    d = leer_ideas()
    por_sep = {sep: combinaciones(d, sep) for sep in SEPARACIONES}
    todas = []
    for v in por_sep.values():
        for x in v:
            if x not in todas:
                todas.append(x)
    res = dict(zip(map(repr, todas), cx.ev(todas)))
    rb = cx.ev([b for _, b in BASES])
    L = [f"Idea 11: combinaciones (clase B). ref/cotas/explorar_ideas.py idea 11 --semilla {cx.semilla}, commit {commit()}",
         "Cada separacion arma sus combinaciones con los componentes elegidos en su propio ajuste.", ""]
    out = {"n": 11, "specs": {}, "bases": {}, "familias": {}}
    for sep in SEPARACIONES:
        aj, va = f"{sep}-ajuste", f"{sep}-validacion"
        sp = por_sep[sep]
        ma = [cx.m(res[repr(x)], aj) for x in sp]
        orden = sorted(range(len(sp)), key=lambda k: -ma[k]["pts"])
        L += [f"== separacion por {sep}", "   todas en el ajuste y en la validacion:",
              "   " + CAB.replace("estrategia", "estrategia (ajuste)")]
        for k in orden:
            L.append("   " + linea(nombre(sp[k])[:34], ma[k]))
            L.append("   " + linea("   validacion", cx.m(res[repr(sp[k])], va)))
        k0 = orden[0]
        r0 = res[repr(sp[k0])]
        mv = cx.m(r0, va)
        d40, ee40 = delta_ee(cx, r0, rb[0], cx.idx[va])
        d60, ee60 = delta_ee(cx, r0, rb[1], cx.idx[va])
        L += [f"   elegida: {nombre(sp[k0])}; contra banda 40 {d40:+.0f} (ee {ee40:.0f}), contra banda 60 {d60:+.0f} (ee {ee60:.0f})", ""]
        out["specs"][sep] = dict(spec=sp[k0], nombre=nombre(sp[k0]), ajuste=ma[k0], validacion=mv, d40=(d40, ee40), d60=(d60, ee60))
        out["bases"][sep] = {nm: dict(ajuste=cx.m(r, aj), validacion=cx.m(r, va)) for (nm, _), r in zip(BASES, rb)}
        # mejor de cada familia, para la tabla 2
        fam = {}
        for k in orden:
            x = sp[k]
            f = ("2+4+8" if x[0] == "final" and x[1]["base"][0] == "regimen" else
                 "5+8" if x[0] == "final" and x[1]["base"][0] == "cuantil" else
                 "10+8" if x[0] == "final" and x[1]["base"][0] == "caida" else "3 con tres cuentas")
            if f not in fam:
                r = res[repr(x)]
                fam[f] = dict(spec=x, nombre=nombre(x), ajuste=ma[k], validacion=cx.m(r, va),
                              d40=delta_ee(cx, r, rb[0], cx.idx[va]), d60=delta_ee(cx, r, rb[1], cx.idx[va]))
        out["familias"][sep] = fam
    return L, out


# --- tabla 2 y finalistas ----------------------------------------------------------------------

def leer_ideas():
    out = {}
    for n in range(1, 13):
        ruta = os.path.join(SALIDA, f"idea{n}.json")
        if os.path.exists(ruta):
            out[n] = json.load(open(ruta))
    return out


def fmt(x, d=3):
    return f"{x:.{d}f}".replace(".", ",")


def tabla2(ideas_, d40_bases=None):
    """d40_bases: {(nombre, separación): (Δ, ee)} de las bases contra banda 40 en la validación (si se calcularon)."""
    d40_bases = d40_bases or {}
    filas = []
    for n, d in ideas_.items():
        if n == 11:
            for fam in d["familias"]["anios"]:
                if fam in d["familias"]["empresas"]:
                    filas.append((f"11 ({fam})", f"Combinación {fam}", CLASE[11], d["familias"]["anios"][fam],
                                  d["familias"]["empresas"][fam]))
            continue
        a, e = d["specs"]["anios"], d["specs"]["empresas"]
        t = TITULO[n] + (" (no pasó el filtro; representante fijo)" if d.get("sin_barrido") else "")
        filas.append((n, t, CLASE[n], a, e))
    base = next(iter(ideas_.values()))["bases"]
    for nm in ("banda 40", "banda 60", "tres bandas por hilo"):
        filas.append((0, nm, "base", dict(nombre=nm, ajuste=base["anios"][nm]["ajuste"], validacion=base["anios"][nm]["validacion"],
                                          d40=d40_bases.get((nm, "anios"), (0, 0))),
                      dict(nombre=nm, ajuste=base["empresas"][nm]["ajuste"], validacion=base["empresas"][nm]["validacion"],
                           d40=d40_bases.get((nm, "empresas"), (0, 0)))))
    filas.sort(key=lambda f: -(f[3]["validacion"]["pts"] + f[4]["validacion"]["pts"]))
    T = ["| # | Idea | Clase | Elegida (ajuste por años / por empresas) | Pts validación años / empresas | Pts ajuste años / empresas "
         "| 1.ª sola % (val. años / emp.) | Media | Mediana | p5 | Peor | / c. y m. | Órdenes | Comisiones | Pérdida máx. % "
         "| Δ media vs banda 40 (ee), años / empresas |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, t, c, a, e in filas:
        va, ve = a["validacion"], e["validacion"]
        na, ne = (nombre(desjson(a["spec"])), nombre(desjson(e["spec"]))) if "spec" in a else (a["nombre"], e["nombre"])
        el = na if na == ne else f"{na} / {ne}"
        d40, e40 = a["d40"], e["d40"]
        T.append(f"| {n or '-'} | {t} | {c} | {el} | {fmt(va['pts'])} / {fmt(ve['pts'])} | {fmt(a['ajuste']['pts'])} / "
                 f"{fmt(e['ajuste']['pts'])} | {fmt(va['pri'], 1)} / {fmt(ve['pri'], 1)} | {va['media']:.0f} | {va['mediana']} | "
                 f"{va['p5']} | {va['peor']} | {fmt(va['bh'], 2)} | {fmt(va['ordenes'], 1)} | {va['comisiones']:.0f} | "
                 f"{fmt(va['dd'], 1)} | {d40[0]:+.0f} ({d40[1]:.0f}) / {e40[0]:+.0f} ({e40[1]:.0f}) |")
    T.append("")
    T.append("Media, mediana, p5, peor, razón contra comprar y mantener, órdenes, comisiones y pérdida máxima: validación "
             "por años (ventanas enteras en 2024), con la variante elegida en el ajuste por años. Δ: diferencia de patrimonio "
             "medio contra banda 40 en cada validación, con la variante elegida en su ajuste, y su error estándar por grupos "
             "de ventanas vecinas (empresa y bloque de 20 días de inicio).")
    return T


def completa_finalistas(carpeta, semilla, procesos, k=5):
    """Las k ideas con más puntos de validación (media de las dos separaciones), con sus elegidas, y las bases, en
    todas las ventanas de la población."""
    d = leer_ideas()
    orden = sorted(d, key=lambda n: -(d[n]["specs"]["anios"]["validacion"]["pts"] + d[n]["specs"]["empresas"]["validacion"]["pts"]))
    specs, nombres = [], []
    for nm, b in BASES:
        specs.append(b)
        nombres.append(nm)
    for n in orden[:k] + ([12] if 12 in d and 12 not in orden[:k] else []):
        if n == 11:
            continue
        for sep in SEPARACIONES:
            sp = d[n]["specs"][sep]["spec"]
            sp = json.loads(json.dumps(sp), object_hook=None)
            sp = desjson(sp)
            if sp not in specs:
                specs.append(sp)
                nombres.append(f"idea {n}: {d[n]['specs'][sep]['nombre']}")
    conj = completa(carpeta)
    R = rivales(conj)
    t0 = time.time()
    res = evaluar(conj, specs, procesos, trozo=200, info=False)
    idx = {"todas": list(range(len(conj.filas)))}
    for sep, (aj, va) in SEPARACIONES.items():
        idx[f"{sep}-validacion"] = sub(conj, va)
    L = [f"Finalistas en la poblacion completa ({len(conj.filas)} ventanas de 20 000), ref/cotas/explorar_ideas.py completa "
         f"--semilla {semilla}, commit {commit()}; {time.time() - t0:.0f} s",
         "Torneo de 3 rondas: 20 000 sorteos por subconjunto, rival de Tesla fijo y 8 del campo (dos tercios con extremos).",
         "Ultima columna: diferencia de patrimonio medio contra banda 40 y su error estandar por grupos de ventanas vecinas.", "",
         "Estrategias (nombre completo):"] + [f"   {nm}" for nm in nombres] + [""]
    cxx = types.SimpleNamespace(conj=conj)
    for k_, ix in idx.items():
        T = Torneo(ix, R, f"completa-{k_}", semilla)
        L += [f"== {k_} ({len(ix)} ventanas)", CAB + "   d40   (ee)"]
        for nm, r in zip(nombres, res):
            dm, ee = delta_ee(cxx, r, res[0], ix)
            L.append(linea(nm[:34], metricas(r, ix, R, T)) + f"  {dm:+5.0f} ({ee:3.0f})")
        L.append("")
    return L


def desjson(x):
    """Las especificaciones vuelven del JSON con listas en vez de tuplas."""
    if isinstance(x, list):
        return tuple(desjson(v) for v in x)
    if isinstance(x, dict):
        return {k: desjson(v) for k, v in x.items()}
    return x


def tesla(carpeta):
    """Idea 8 en la ronda de Tesla del 18/11 (y en las otras dos series conocidas, como ilustración)."""
    import market
    tes = market.leer_serie(os.path.join(os.path.dirname(carpeta), "capturas", "ronda_10ms_clase.csv"))
    meta = market.leer_serie(os.path.join(comun.RAIZ, "data", "practica_meta.csv"))
    fechas, minutos, x = reales.leer_sesion(carpeta, "AMD")
    s0 = next(i for i in range(len(fechas)) if fechas[i] == "2022-01-10" and minutos[i] == 50)
    amd = comun.normalizar(x[s0:s0 + LARGO])
    series = (("Tesla 18/11", tes), ("AMD 18/11", amd), ("practica Meta", meta))
    L = [f"Idea 8 en la ronda de Tesla del 18/11 (ref/cotas/explorar_ideas.py tesla), commit {commit()}",
         "La maestra mostro 18 779 para nosotros (banda 60) y 21 467 para el rival. AMD (21 895 con banda 60) y la serie de",
         "practica se muestran como ilustracion: no sirven para elegir (son tres series).", "",
         f"{'variante':44s} " + " ".join(f"{n:>14s}" for n, _ in series) + "   cierra Tesla"]
    specs = [("banda 40", B40), ("banda 60", B60)] + [(nombre(sp), sp) for sp in idea_specs(8)]
    specs += [("no vuelve en D (220)", ("novuelve", {"H": 220}))]
    elegidas = []
    for n, d in sorted(leer_ideas().items()):
        for sep in SEPARACIONES:
            sp = desjson(d["specs"][sep]["spec"])
            if all(sp != x for _, x in specs + elegidas):
                elegidas.append((f"idea {n}: {nombre(sp)}", sp))
    specs += elegidas
    for nm, sp in specs:
        ws = [ideas.correr(w, ideas.crear(sp))[0] for _, w in series]
        L.append(f"{nm[:44]:44s} " + " ".join(f"{w:14d}" for w in ws) + ("   si" if ws[0] >= 21467 else ""))
    tD = ideas.crear(B60)
    ideas.correr(tes, tD)
    i100, i255 = tes.index(100), tes.index(255)
    L += ["", f"En Tesla el primer 100 llega en el tick {i100} y el primer 255 en el {i255}; la fase D empieza en el tick {tD.tD}."]
    # operaciones de la banda 60 y de la banda 40 en Tesla
    for nm, sp in (("banda 60", B60), ("banda 40", B40)):
        s_, filas = ideas.crear(sp), []
        caja, acc, d = ideas.CAJA0, 0, ideas.M
        for n, p in enumerate(tes):
            a0 = acc
            a = d >> 6
            if a == 1:
                q = min(d & 63, (caja - 5) // p)
                if q > 0:
                    caja -= q * p + 5
                    acc += q
            elif a == 2:
                q = min(d & 63, acc)
                if q > 0:
                    caja += q * p - 5
                    acc -= q
            if acc != a0:
                filas.append(f"tick {n} a {p}: {'compra' if acc > a0 else 'vende'} {abs(acc - a0)}")
            d = s_.decidir(p, caja, acc)
        L.append(f"{nm}: " + "; ".join(filas) + f"; termina con {acc} acciones a {tes[-1]} (patrimonio {caja + acc * tes[-1]})")
    return L


def detalle(cx):
    """Lo que el pedido exige además de la tabla: cambios de líder de la idea 3 y su costo, y la idea 7 contra
    rivales que no se emulan."""
    d = leer_ideas()
    L = [f"Detalle de las ideas 3 y 7 (ref/cotas/explorar_ideas.py detalle --semilla {cx.semilla}), commit {commit()}", ""]
    rb40 = cx.ev([B40])[0]
    for n, clave in ((3, None), (11, "3 con tres cuentas")):
        for sep in SEPARACIONES:
            e = d[n]["familias"][sep][clave] if clave else d[n]["specs"][sep]
            r = cx.ev([desjson(e["spec"])])[0]
            va = cx.idx[f"{sep}-validacion"]
            inf = [r["info"][i] for i in va if r["info"][i][0] >= 0]
            cambios = sum(x[1] for x in inf)
            ordenes = sum(x[2] for x in inf)
            dif = sum(r["n"][i] - rb40["n"][i] for i in va)
            dW = sum(r["W"][i] - rb40["W"][i] for i in va) / len(va)
            L.append(f"Idea {'3' if n == 3 else '3 con tres cuentas'}, {e['nombre']}, validacion por {sep}: "
                     f"{cambios / len(va):.2f} cambios de lider por ventana; {ordenes / max(1, cambios):.2f} ordenes por cambio "
                     f"({5 * ordenes / max(1, cambios):.1f} de comision por cambio); {dif / len(va):+.2f} ordenes por ventana "
                     f"contra banda 40; patrimonio medio {dW:+.0f} contra banda 40, es decir {dW / max(0.01, cambios / len(va)):+.0f} "
                     "por cada cambio de lider")
    L.append("")
    emulados = (RIVAL_TESLA, "siempre")
    L.append("Idea 7: efecto de la cobertura en el torneo, con el campo de siempre (rival de Tesla fijo) y con un campo sin los")
    L.append("rivales emulados (sin el rival de Tesla ni comprar y mantener; la banda simple 140/215 no esta en el campo).")
    for sep in SEPARACIONES:
        va = cx.idx[f"{sep}-validacion"]
        Tx = Torneo(va, cx.R, f"{sep}-validacion-sin-emulados", cx.semilla, excluir=emulados)
        e = d[7]["specs"][sep]
        r = cx.ev([desjson(e["spec"])])[0]
        for nm, T in (("campo de siempre", cx.T[f"{sep}-validacion"]), ("sin rivales emulados", Tx)):
            p7, f7 = T.puntos(r["W"])
            p0, f0 = T.puntos(rb40["W"])
            L.append(f"   {sep}, {nm}: {e['nombre']} {p7:.3f} pts y {100 * f7:.1f} % primera sola; banda 40 {p0:.3f} pts y "
                     f"{100 * f0:.1f} % (diferencia {p7 - p0:+.3f} pts, {100 * (f7 - f0):+.1f} puntos porcentuales)")
    L.append("")
    L.append("Primera sola y la regla identica del campo: el campo con extremos incluye espera_banda40, que es la banda 40")
    L.append("misma; cuando sale sorteada (en cerca de la mitad de los torneos), la banda 40 empata y no puede quedar primera sola.")
    rb = cx.ev([b for _, b in BASES])
    for sep in SEPARACIONES:
        va = cx.idx[f"{sep}-validacion"]
        Tx = Torneo(va, cx.R, f"{sep}-validacion-sin-b40", cx.semilla, excluir=("espera_banda40",))
        for (nm, _), r in zip(BASES, rb):
            p1, f1 = cx.T[f"{sep}-validacion"].puntos(r["W"])
            p2, f2 = Tx.puntos(r["W"])
            L.append(f"   {sep}, {nm:22s}: campo de siempre {p1:.3f} pts, {100 * f1:5.1f} % primera sola; campo sin "
                     f"espera_banda40 {p2:.3f} pts, {100 * f2:5.1f} % primera sola")
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("accion")
    ap.add_argument("resto", nargs="*")
    ap.add_argument("--semilla", type=int, default=SEMILLA)
    ap.add_argument("--datos", default=None)
    ap.add_argument("--procesos", type=int, default=None)
    a = ap.parse_args(argv)
    carpeta = reales.carpeta_datos(a.datos)
    os.makedirs(SALIDA, exist_ok=True)
    if a.accion == "validar":
        L = validar(carpeta, a.procesos)
        texto = "\n".join(L) + "\n"
        print(texto, end="")
        open(os.path.join(SALIDA, "validar.txt"), "w").write(texto)
        return 0 if "FAIL" not in texto else 1
    if a.accion == "filtros":
        cx = Ctx(carpeta, a.semilla, a.procesos)
        F, D = filtros(cx)
        T1 = [f"Tabla 1: filtros de las ideas (ref/cotas/explorar_ideas.py filtros --semilla {a.semilla}), commit {commit()}", "",
              "| Idea | Filtro | Numero medido | Pasa |", "|---|---|---|---|"]
        T1 += [f"| {n} | {f} | {x} | {'sin filtro' if p is None else 'si' if p else 'no'} |" for n, f, x, p in F]
        texto = "\n".join(T1) + "\n\n" + "\n".join(D) + "\n"
        open(os.path.join(SALIDA, "filtros.txt"), "w").write(texto)
        print(texto, end="")
        return 0
    if a.accion == "idea":
        cx = Ctx(carpeta, a.semilla, a.procesos)
        for n in [int(x) for x in a.resto]:
            if n == 11:
                L, out = barrido_combinaciones(cx)
            elif n in REPRESENTANTE:
                L, out = barrido(cx, n, [REPRESENTANTE[n]])
                out["sin_barrido"] = True
                L.insert(1, "NO PASO SU FILTRO: sin barrido; se informa un representante fijo, elegido antes de ver resultados.")
            else:
                L, out = barrido(cx, n)
            guardar_idea(n, L, out)
            print("\n".join(L))
        return 0
    if a.accion == "detalle":
        L = detalle(Ctx(carpeta, a.semilla, a.procesos))
        texto = "\n".join(L) + "\n"
        open(os.path.join(SALIDA, "detalle.txt"), "w").write(texto)
        print(texto, end="")
        return 0
    if a.accion == "tesla":
        L = tesla(carpeta)
        texto = "\n".join(L) + "\n"
        open(os.path.join(SALIDA, "tesla.txt"), "w").write(texto)
        print(texto, end="")
        return 0
    if a.accion == "tabla":
        cx = Ctx(carpeta, a.semilla, a.procesos)
        rb = dict(zip([nm for nm, _ in BASES], cx.ev([b for _, b in BASES])))
        d40b = {(nm, sep): delta_ee(cx, rb[nm], rb["banda 40"], cx.idx[f"{sep}-validacion"])
                for nm in rb for sep in SEPARACIONES}
        T = tabla2(leer_ideas(), d40b)
        texto = "\n".join(T) + "\n"
        open(os.path.join(SALIDA, "tabla2.md"), "w").write(texto)
        print(texto, end="")
        return 0
    if a.accion == "completa":
        L = completa_finalistas(carpeta, a.semilla, a.procesos, int(a.resto[0]) if a.resto else 5)
        texto = "\n".join(L) + "\n"
        open(os.path.join(SALIDA, "completa.txt"), "w").write(texto)
        print(texto, end="")
        return 0
    raise SystemExit("accion desconocida: " + a.accion)


if __name__ == "__main__":
    sys.exit(main())
