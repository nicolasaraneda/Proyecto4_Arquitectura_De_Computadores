#!/usr/bin/env python3
"""explorar_regimen.py: política por régimen filtrado (docs/exploracion_ideas.md, sección 12).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Conjuntos de ventanas de 20 000 minutos normalizadas entre 100 y 255 (receta de reales.py):
  cinco   la muestra de siempre de META, AAPL, NFLX, AMD y TSLA (semilla 18, 3600 ventanas)
  otras   las 100 acciones de tools/datos/otras_acciones.txt (2020 a 2024): 24 ventanas por
          acción y año de inicio, con inicios en múltiplos de PASO (para que los rivales salgan
          de reales.correr en C con ese paso), semilla 18
  paseo   control: 3600 paseos aleatorios gaussianos de 20 000 pasos normalizados igual

Filtros (sección 8 del diseño), en orden:
  F1  clase por v^2 de los ticks 1 a K (K = 1000, 2000, 4000) contra (a) v^2 de la ventana y del
      resto, (b) cruces de la banda 140/215 en la fase D, (c) persistencia
      signo(p(t+h) - p(t)) signo(p(t) - p(t-h)), h = 390 y 1950, por clase, en el resto de la
      ventana; separada por fase (A a C y D) y por caso S y B.
  F2  primer máximo nuevo >= theta en la fase A desde t = 390: probabilidad de ver 255 antes de
      caer d niveles, por clase, contra d / (255 - p0 + d).
  F3  techo del módulo E: banda 40 decidiendo con p(n) completo, y con la orden condicionada a los
      bits del precio que llega, con y sin comisión por cantidad 0.

Errores estándar por grupos de ventanas: bloque de 20 días hábiles de la fecha de inicio (todas
las empresas juntas, porque comparten fechas); además bloques de 60 días y, en las otras
acciones, grupos en dos sentidos (fecha y empresa). Para decidir se usa el mayor.

Uso (con export P4_DATOS=~/proyectos/datos_p4):
  python3 ref/cotas/explorar_regimen.py filtros --conjunto cinco|otras|paseo   -> filtros_<conjunto>.txt
  python3 ref/cotas/explorar_regimen.py f3 --conjunto cinco|otras               -> f3_<conjunto>.txt
"""
import argparse
import bisect
import hashlib
import os
import pickle
import random
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorar_ideas as E  # noqa: E402
import ideas                # noqa: E402
import regimen as RG        # noqa: E402
import reales               # noqa: E402

RAIZ = E.comun.RAIZ
LISTA = os.path.join(RAIZ, "tools", "datos", "otras_acciones.txt")
CACHE = os.path.join(E.comun.BUILD, "regimen")
SALIDA = E.SALIDA
LARGO = E.LARGO
PASO = 97
POR_ESTRATO_OTRAS = 24
ANIOS_OTRAS = (2020, 2021, 2022, 2023, 2024)
N_PASEOS = 3600
SEMILLA = 18
# Las cachés .pkl de build/cotas/regimen/ las escribe solo este script en la máquina local; no se
# cargan archivos de otro origen.
_COD = hashlib.sha256(open(os.path.abspath(RG.__file__), "rb").read()).hexdigest()[:16]
E.CODIGO_EXTRA["regimen_pol"] = _COD


def commit():
    return E.commit()


def fmt(x, d=3):
    return "-" if x is None else f"{x:.{d}f}".replace(".", ",")


# --- conjuntos ---------------------------------------------------------------------------------

def leer_grupos(ruta=LISTA):
    """{ticker: grupo} de las 100 elegidas y lista de suplentes."""
    g, sup = {}, []
    for linea in open(ruta):
        linea = linea.split("#")[0].strip()
        if ":" not in linea:
            continue
        k, v = linea.split(":", 1)
        if k.strip() == "suplentes":
            sup = v.split()
        else:
            for t in v.split():
                g[t] = k.strip()
    return g, sup


class Datos:
    """Ventanas normalizadas (bytes), filas (empresa, inicio, año inicio, año fin), día hábil de
    inicio (para los grupos) y grupo de sector de cada ventana."""

    def __init__(self, nombre, filas, ventanas, dia, grupo):
        self.nombre, self.filas, self.ventanas, self.dia, self.grupo = nombre, filas, ventanas, dia, grupo

    def conj(self, carpeta=None):
        c = E.Conjunto(self.nombre, self.filas, carpeta)
        c.ventanas = self.ventanas
        return c

    def clave(self):
        h = hashlib.sha256(self.nombre.encode())
        h.update(repr(self.filas[:50]).encode())
        h.update(str(len(self.filas)).encode())
        return h.hexdigest()[:12]


def _calendario(fechas_por_emp):
    dias = sorted({d for f in fechas_por_emp.values() for d in f})
    return {d: i for i, d in enumerate(dias)}


def datos_cinco(carpeta):
    ruta = os.path.join(CACHE, f"cinco_{SEMILLA}.pkl")
    if os.path.exists(ruta):
        return pickle.load(open(ruta, "rb"))
    c = E.muestra(carpeta, SEMILLA)
    c.normalizar_todas()
    fechas = {emp: reales.leer_sesion(carpeta, emp)[0] for emp in E.EMPRESAS}
    cal = _calendario(fechas)
    dia = [cal[fechas[f[0]][f[1]]] for f in c.filas]
    grupo = {"META": "tec", "NFLX": "tec", "AAPL": "tec", "AMD": "tec", "TSLA": "con"}
    d = Datos(c.nombre, c.filas, c.ventanas, dia, [grupo[f[0]] for f in c.filas])
    os.makedirs(CACHE, exist_ok=True)
    pickle.dump(d, open(ruta, "wb"))
    return d


def datos_otras(carpeta):
    grupos, _ = leer_grupos()
    empresas = list(grupos)
    h = hashlib.sha256(repr((empresas, PASO, POR_ESTRATO_OTRAS, SEMILLA, LARGO)).encode())
    for emp in empresas:
        st = os.stat(os.path.join(carpeta, f"{emp}.csv"))
        h.update(f"{emp} {st.st_size}".encode())
    ruta = os.path.join(CACHE, f"otras_{h.hexdigest()[:12]}.pkl")
    if os.path.exists(ruta):
        return pickle.load(open(ruta, "rb"))
    filas, ventanas, fechas_ini, todas_fechas = [], [], [], {}
    for emp in empresas:
        fechas, _, x = reales.leer_sesion(carpeta, emp)
        todas_fechas[emp] = sorted(set(fechas))
        n = len(x) - LARGO + 1
        por_anio = {}
        for s in range(0, n, PASO):
            por_anio.setdefault(int(fechas[s][:4]), []).append(s)
        for anio in ANIOS_OTRAS:
            cand = por_anio.get(anio, [])
            rng = random.Random(f"otras-{SEMILLA}-{emp}-{anio}")
            for s in sorted(rng.sample(cand, min(POR_ESTRATO_OTRAS, len(cand)))):
                seg = x[s:s + LARGO]
                lo, hi = min(seg), max(seg)
                ventanas.append(bytes(int(100 + (v - lo) * 155.0 / (hi - lo) + 0.5) for v in seg))
                filas.append((emp, s, anio, int(fechas[s + LARGO - 1][:4])))
                fechas_ini.append(fechas[s])
        print(f"  otras: {emp} listo ({len(filas)} ventanas)", file=sys.stderr)
    cal = _calendario(todas_fechas)
    d = Datos(f"otras-{SEMILLA}-{POR_ESTRATO_OTRAS}-{PASO}", filas, ventanas, [cal[f] for f in fechas_ini],
              [grupos[f[0]] for f in filas])
    os.makedirs(CACHE, exist_ok=True)
    pickle.dump(d, open(ruta, "wb"))
    return d


def _paseo(i):
    rng = random.Random(f"paseo-{SEMILLA}-{i}")
    g = rng.gauss
    x, v = [0.0] * LARGO, 0.0
    for j in range(1, LARGO):
        v += g(0.0, 1.0)
        x[j] = v
    lo, hi = min(x), max(x)
    return bytes(int(100 + (u - lo) * 155.0 / (hi - lo) + 0.5) for u in x)


def datos_paseo(procesos=None):
    ruta = os.path.join(CACHE, f"paseo_{SEMILLA}_{N_PASEOS}.pkl")
    if os.path.exists(ruta):
        return pickle.load(open(ruta, "rb"))
    with Pool(procesos or os.cpu_count()) as pool:
        ventanas = pool.map(_paseo, range(N_PASEOS), chunksize=20)
    d = Datos(f"paseo-{SEMILLA}-{N_PASEOS}", [("paseo", i, 0, 0) for i in range(N_PASEOS)], ventanas,
              list(range(N_PASEOS)), ["paseo"] * N_PASEOS)
    os.makedirs(CACHE, exist_ok=True)
    pickle.dump(d, open(ruta, "wb"))
    return d


def cargar(nombre, procesos=None):
    if nombre == "cinco":
        return datos_cinco(reales.carpeta_datos())
    if nombre == "otras":
        return datos_otras(os.path.join(os.path.expanduser(os.environ.get("P4_DATOS", "~/proyectos/datos_p4")),
                                        "otras"))
    if nombre == "paseo":
        return datos_paseo(procesos)
    raise SystemExit(f"conjunto desconocido: {nombre}")


# --- errores estándar por grupos -----------------------------------------------------------------

def grupos_de(D):
    """Llaves de grupo por ventana: bloque de 20 días, de 60 días y empresa."""
    if D.filas[0][0] == "paseo":
        ids = list(range(len(D.filas)))
        return {"b20": ids, "b60": ids, "emp": ids, "emp_b60": ids}
    return {"b20": [d // 20 for d in D.dia], "b60": [d // 60 for d in D.dia], "emp": [f[0] for f in D.filas],
            "emp_b60": [(f[0], d // 60) for f, d in zip(D.filas, D.dia)]}


def _v(contrib, llaves):
    g = {}
    for c, k in zip(contrib, llaves):
        if c:
            g[k] = g.get(k, 0.0) + c
    return sum(x * x for x in g.values())


def ee_contrib(contrib, G, dos_sentidos):
    """Error estándar de un estadístico lineal con contribuciones por ventana. Devuelve (máximo,
    detalle). Dos sentidos (Cameron, Gelbach y Miller): V = V_fecha + V_empresa - V_intersección."""
    v20, v60 = _v(contrib, G["b20"]), _v(contrib, G["b60"])
    det = {"b20": v20 ** 0.5, "b60": v60 ** 0.5}
    if dos_sentidos:
        v2 = v60 + _v(contrib, G["emp"]) - _v(contrib, G["emp_b60"])
        det["2s"] = max(v2, 0.0) ** 0.5
    return max(det.values()), det


def media_ee(x, w, sel, G, dos):
    """Media ponderada de x (pesos w) sobre las ventanas sel, con su error estándar."""
    W = sum(w[i] for i in sel)
    if W == 0:
        return None, None, 0
    m = sum(w[i] * x[i] for i in sel) / W
    c = [0.0] * len(x)
    for i in sel:
        c[i] = w[i] * (x[i] - m) / W
    return m, ee_contrib(c, G, dos)[0], len(sel)


def dif_ee(x, w, selA, selB, G, dos):
    """Diferencia de medias ponderadas A - B (conjuntos disjuntos) y su error estándar."""
    WA, WB = sum(w[i] for i in selA), sum(w[i] for i in selB)
    if WA == 0 or WB == 0:
        return None, None
    mA = sum(w[i] * x[i] for i in selA) / WA
    mB = sum(w[i] * x[i] for i in selB) / WB
    c = [0.0] * len(x)
    for i in selA:
        c[i] = w[i] * (x[i] - mA) / WA
    for i in selB:
        c[i] -= w[i] * (x[i] - mB) / WB
    return mA - mB, ee_contrib(c, G, dos)[0]


# --- medidas en paralelo -----------------------------------------------------------------------

_V = {}


def _medir(ids):
    return ids, [RG.medir(_V["v"][i]) for i in ids]


def medidas(D, procesos=None):
    ruta = os.path.join(CACHE, f"medidas_{D.clave()}_{_COD}.pkl")
    if os.path.exists(ruta):
        return pickle.load(open(ruta, "rb"))
    _V["v"] = D.ventanas
    n = len(D.ventanas)
    tr = max(5, n // ((procesos or os.cpu_count()) * 6))
    out = [None] * n
    t0 = time.time()
    with Pool(procesos or os.cpu_count()) as pool:
        for ids, res in pool.imap_unordered(_medir, [list(range(a, min(n, a + tr))) for a in range(0, n, tr)]):
            for i, r in zip(ids, res):
                out[i] = r
    print(f"  medidas {D.nombre}: {n} ventanas en {time.time() - t0:.0f} s", file=sys.stderr)
    pickle.dump(out, open(ruta, "wb"))
    return out


# --- F1 ----------------------------------------------------------------------------------------

def corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    saa = sum((x - ma) ** 2 for x in a)
    sbb = sum((y - mb) ** 2 for y in b)
    return sab / (saa * sbb) ** 0.5


GRUPOS_FASE = {"todas": ("A", "BC", "D"), "A a C": ("A", "BC"), "D": ("D",), "solo A": ("A",)}


def f1(D, med, L, subconj=None, titulo=""):
    """Agrega a L las tablas de F1 y devuelve {(grupo_fase, K, h): (dif, ee)} y cruces por K."""
    G = grupos_de(D)
    dos = D.filas[0][0] != "paseo" and len({f[0] for f in D.filas}) > 5
    todos = list(range(len(med))) if subconj is None else subconj
    res = {}
    L.append(f"\n### F1 {titulo} ({len(todos)} ventanas)\n")
    for K in RG.KS:
        cl = [m[K]["clase"] for m in med]
        por = {c: [i for i in todos if cl[i] == c] for c in range(4)}
        v2K = [med[i][K]["v2"] for i in todos]
        L.append(f"K = {K}: ventanas por clase " + ", ".join(f"{c}: {len(por[c])} ({100 * len(por[c]) / len(todos):.1f} %)"
                                                           for c in range(4))
                 + f"; v^2 medio {fmt(sum(v2K) / len(v2K))}; (a) correlación de v^2(1..K) con v^2 de la ventana "
                 f"{fmt(corr(v2K, [med[i]['v2'] for i in todos]))} y con v^2 del resto "
                 f"{fmt(corr(v2K, [med[i][K]['v2resto'] for i in todos]))}")
        # (b) cruces en D por clase (por ventana)
        x = [m[K]["cruces"] for m in med]
        uno = [1.0] * len(med)
        fila = []
        for c in range(4):
            mm, ee, nn = media_ee(x, uno, por[c], G, dos)
            fila.append((mm, ee))
        d30 = dif_ee(x, uno, por[3], por[0], G, dos)
        crece = all(fila[c][0] is not None for c in range(4)) and all(fila[c][0] < fila[c + 1][0] for c in range(3))
        L.append("  (b) cruces de 140/215 en D después de K, por clase: "
                 + " | ".join(f"{c}: {fmt(m_, 2)} ({fmt(e_, 2)})" for c, (m_, e_) in enumerate(fila))
                 + f"; clase 3 - clase 0 = {fmt(d30[0], 2)} (ee {fmt(d30[1], 2)}); crece con la clase: {'sí' if crece else 'no'}")
        res[("cruces", K)] = (crece and d30[0] is not None and d30[0] > 2 * d30[1], d30)
        # (c) persistencia por clase y fase
        for h in RG.HS:
            for gf, fases in GRUPOS_FASE.items():
                s = [sum(m[K]["pers"][(h, f)][0] for f in fases) for m in med]
                ct = [sum(m[K]["pers"][(h, f)][1] for f in fases) for m in med]
                xm = [s[i] / ct[i] if ct[i] else 0.0 for i in range(len(med))]
                fila = []
                for c in range(4):
                    mm, ee, nn = media_ee(xm, ct, por[c], G, dos)
                    fila.append((mm, ee))
                d = dif_ee(xm, ct, por[0], por[3], G, dos)
                res[(gf, K, h)] = d
                t = d[0] / d[1] if d[0] is not None and d[1] else None
                L.append(f"  (c) h = {h:4d}, fases {gf:6s}: " + " | ".join(f"{c}: {fmt(m_)} ({fmt(e_)})" for c, (m_, e_) in enumerate(fila))
                         + f"; clase 0 - clase 3 = {fmt(d[0])} (ee {fmt(d[1])}, t {fmt(t, 1)})")
    return res


def veredicto_f1(res):
    """Pasa por grupo de fases si en los tres K y los dos h la persistencia de la clase 0 supera a la
    de la clase 3 por más de 2 ee; en D además deben pasar los cruces (b) en los tres K."""
    out = {}
    for gf in ("todas", "A a C", "D"):
        ok_c = all(res[(gf, K, h)][0] is not None and res[(gf, K, h)][1] and res[(gf, K, h)][0] > 2 * res[(gf, K, h)][1]
                   for K in RG.KS for h in RG.HS)
        ok_b = all(res[("cruces", K)][0] for K in RG.KS)
        out[gf] = (ok_c and ok_b) if gf in ("todas", "D") else ok_c
    return out


# --- F2 ----------------------------------------------------------------------------------------

def f2(D, med, L, subconj=None, titulo=""):
    """Primer máximo nuevo >= theta en la fase A, por clase de ese momento: tasa de ver 255 antes de
    caer d, contra la base d / (255 - p0 + d). Devuelve {(grupo, theta, d): (exceso, ee, n)}."""
    G = grupos_de(D)
    dos = D.filas[0][0] != "paseo" and len({f[0] for f in D.filas}) > 5
    todos = list(range(len(med))) if subconj is None else subconj
    res = {}
    L.append(f"\n### F2 {titulo} ({len(todos)} ventanas)\n")
    L.append("Exceso = tasa de ver 255 antes de caer d - d / (255 - p0 + d), en puntos porcentuales; entre paréntesis ee.")
    grupos_cl = {"clase 0": (0,), "clase 0 y 1": (0, 1), "clase 2": (2,), "clase 3": (3,)}
    for th in RG.THETAS:
        L.append(f"theta = {th}:")
        for gn, cls in grupos_cl.items():
            sel = [i for i in todos if th in med[i]["f2"] and med[i]["f2"][th][2] in cls]
            partes = []
            for d in RG.DS:
                x = [0.0] * len(med)
                for i in sel:
                    _, p0, _, mn = med[i]["f2"][th]
                    x[i] = (1.0 if mn > p0 - d else 0.0) - d / (255 - p0 + d)
                uno = [1.0] * len(med)
                m_, e_, nn = media_ee(x, uno, sel, G, dos)
                res[(gn, th, d)] = (m_, e_, len(sel))
                tasa = sum(1 for i in sel if med[i]["f2"][th][3] > med[i]["f2"][th][1] - d) / len(sel) if sel else None
                partes.append(f"d={d}: {fmt(None if tasa is None else 100 * tasa, 1)} % "
                              f"exceso {fmt(None if m_ is None else 100 * m_, 1)} ({fmt(None if e_ is None else 100 * e_, 1)})")
            L.append(f"  {gn:12s} n = {len(sel):5d}  " + " | ".join(partes))
    return res


def veredicto_f2(res):
    """Pasa si en la celda de referencia (theta 220, d 16) el exceso de la clase 0, o de las clases
    0 y 1 juntas, supera 2 ee. Se informa además cuántas de las 16 celdas pasan 2 ee."""
    ref = [res[(g, 220, 16)] for g in ("clase 0", "clase 0 y 1")]
    pasa = any(m is not None and e and m > 2 * e for m, e, _ in ref)
    cuenta = {g: sum(1 for th in RG.THETAS for d in RG.DS
                     if res[(g, th, d)][0] is not None and res[(g, th, d)][1] and res[(g, th, d)][0] > 2 * res[(g, th, d)][1])
              for g in ("clase 0", "clase 0 y 1")}
    return pasa, cuenta


# --- F3 ----------------------------------------------------------------------------------------

def _f3(ids):
    out = []
    for i in ids:
        w = _V["v"][i]
        fila = [RG.correr_e(w, ideas.Regla(ideas.BandaD(140, 215)), "bits")[0],
                RG.correr_e(w, ideas.Regla(ideas.BandaD(140, 215)), "techo")[0]]
        for armado in (1, 2):
            for cc in (False, True):
                fila.append(RG.correr_e(w, RG.Banda40E(armado), "bits", com_cero=cc)[0])
        out.append(fila)
    return ids, out


F3_COLS = ["banda 40", "techo: decide con p(n)", "bits, armado 1, sin comisión en 0", "bits, armado 1, con comisión en 0",
           "bits, armado 2, sin comisión en 0", "bits, armado 2, con comisión en 0"]


def f3(D, L, procesos=None):
    ruta = os.path.join(CACHE, f"f3_{D.clave()}_{_COD}.pkl")
    if os.path.exists(ruta):
        R = pickle.load(open(ruta, "rb"))
    else:
        _V["v"] = D.ventanas
        n = len(D.ventanas)
        tr = max(5, n // ((procesos or os.cpu_count()) * 6))
        R = [None] * n
        with Pool(procesos or os.cpu_count()) as pool:
            for ids, res in pool.imap_unordered(_f3, [list(range(a, min(n, a + tr))) for a in range(0, n, tr)]):
                for i, r in zip(ids, res):
                    R[i] = r
        pickle.dump(R, open(ruta, "wb"))
    G = grupos_de(D)
    dos = len({f[0] for f in D.filas}) > 5
    n = len(R)
    L.append(f"\n### F3 {D.nombre} ({n} ventanas)\n")
    L.append("| variante | patrimonio medio | diferencia con la banda 40 (ee) |")
    L.append("|---|---|---|")
    for j, nom in enumerate(F3_COLS):
        x = [R[i][j] - R[i][0] for i in range(n)]
        m = sum(x) / n
        ee = ee_contrib([v - m for v in x], G, dos)[0] / n
        media = sum(R[i][j] for i in range(n)) / n
        L.append(f"| {nom} | {media:.0f} | {m:+.1f} ({ee:.1f}) |")
    # pasa si una distancia de armado gana más de 1 ee con y sin comisión por cantidad 0
    ok = []
    for j0 in (2, 4):
        bien = True
        for j in (j0, j0 + 1):
            x = [R[i][j] - R[i][0] for i in range(n)]
            m = sum(x) / n
            ee = ee_contrib([v - m for v in x], G, dos)[0] / n
            bien = bien and m > ee
        ok.append(bien)
    return any(ok)


# --- acciones ----------------------------------------------------------------------------------

def accion_filtros(nombre, procesos):
    D = cargar(nombre, procesos)
    med = medidas(D, procesos)
    L = [f"# Filtros F1 y F2: {nombre}", "",
         f"ref/cotas/explorar_regimen.py filtros --conjunto {nombre}, commit {commit()}. Conjunto {D.nombre}: "
         f"{len(med)} ventanas. Clase por v^2 de los ticks 1 a K (umbrales 1/4, 1/2 y 1). Persistencia con t cada "
         f"{RG.PASO_T} ticks y t - h >= K. Error estándar por grupos (bloques de 20 y 60 días hábiles de la fecha de "
         "inicio" + (", y en dos sentidos fecha y empresa" if nombre == "otras" else "") + "); se informa el mayor."]
    r = f1(D, med, L, titulo="todas las ventanas")
    v = veredicto_f1(r)
    caso = {c: [i for i, m in enumerate(med) if m["caso"] == c] for c in (1, 2)}
    rs = {}
    for c, nm in ((1, "caso S (100 antes que 255)"), (2, "caso B (255 antes que 100)")):
        rs[c] = f1(D, med, L, caso[c], titulo=nm)
    L.append("\n### Veredicto F1 (todas las ventanas)\n")
    for gf, ok in v.items():
        L.append(f"- fases {gf}: {'PASA' if ok else 'no pasa'}")
    for c in (1, 2):
        vc = veredicto_f1(rs[c])
        L.append(f"- caso {'S' if c == 1 else 'B'}: " + ", ".join(f"fases {gf} {'pasa' if ok else 'no pasa'}" for gf, ok in vc.items()))
    r2 = f2(D, med, L, titulo="todas las ventanas")
    p2, cuenta = veredicto_f2(r2)
    if nombre != "paseo":
        anios = sorted({f[2] for f in D.filas})
        for a in anios:
            sel = [i for i, f in enumerate(D.filas) if f[2] == a]
            f2(D, med, L, sel, titulo=f"ventanas que empiezan en {a}")
    L.append("\n### Veredicto F2\n")
    L.append(f"- celda de referencia (theta 220, d 16), clase 0 o clases 0 y 1 sobre 2 ee: {'PASA' if p2 else 'no pasa'}")
    L.append(f"- celdas (de 16) sobre 2 ee: clase 0 {cuenta['clase 0']}, clases 0 y 1 {cuenta['clase 0 y 1']} "
             "(por azar se esperan 0,4)")
    txt = "\n".join(L) + "\n"
    os.makedirs(SALIDA, exist_ok=True)
    open(os.path.join(SALIDA, f"filtros_{nombre}.txt"), "w").write(txt)
    print(txt)


def accion_f3(nombre, procesos):
    D = cargar(nombre, procesos)
    L = [f"# F3: techo del módulo E, {nombre}", "",
         f"ref/cotas/explorar_regimen.py f3 --conjunto {nombre}, commit {commit()}. Banda 40 normal; decidiendo con p(n) "
         "completo (techo); con la orden condicionada a los bits del precio que llega (efectivo), armada cuando el "
         "precio anterior quedó a 1 o 2 niveles del umbral, con y sin comisión por una orden de cantidad 0."]
    ok = f3(D, L, procesos)
    L.append(f"\nVeredicto F3 (una distancia de armado gana más de 1 ee con y sin comisión en 0): {'PASA' if ok else 'no pasa'}")
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, f"f3_{nombre}.txt"), "w").write(txt)
    print(txt)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("accion", choices=["filtros", "f3"])
    ap.add_argument("--conjunto", default="cinco")
    ap.add_argument("--procesos", type=int, default=None)
    a = ap.parse_args()
    if a.accion == "filtros":
        accion_filtros(a.conjunto, a.procesos)
    elif a.accion == "f3":
        accion_f3(a.conjunto, a.procesos)


if __name__ == "__main__":
    main()
