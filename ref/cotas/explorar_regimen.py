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


MIN_DIAS = 0.98     # una acción falla si la receta de sesión le deja menos del 98 % de los días hábiles


def dias_sesion(carpeta, emp):
    n, ult = 0, None
    with open(os.path.join(carpeta, f"{emp}.csv")) as f:
        next(f)
        for linea in f:
            d = linea[:10]
            if d != ult:
                n += 1
                ult = d
    return n


def empresas_otras(carpeta):
    """Las 100 elegidas, con cada una que falla reemplazada por la primera suplente de su grupo que no
    falla (dos suplentes por grupo, en el orden de los grupos del archivo). Devuelve ({ticker: grupo},
    lista de (falla, días, reemplazo))."""
    grupos, sup = leer_grupos()
    orden_g = []
    for g in grupos.values():
        if g not in orden_g:
            orden_g.append(g)
    sup_g = {g: sup[2 * j:2 * j + 2] for j, g in enumerate(orden_g)}
    dias = {t: dias_sesion(carpeta, t) for t in list(grupos) + sup}
    tope = max(dias.values())
    out, cambios = {}, []
    usados = set()
    for t, g in grupos.items():
        if dias[t] >= MIN_DIAS * tope:
            out[t] = g
            continue
        r = next((x for x in sup_g[g] if x not in usados and dias[x] >= MIN_DIAS * tope), None)
        cambios.append((t, dias[t], r, dias.get(r)))
        if r:
            usados.add(r)
            out[r] = g
    return out, cambios, tope


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
    grupos, cambios, tope = empresas_otras(carpeta)
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
    d.cambios, d.tope = cambios, tope
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
    if getattr(D, "cambios", None):
        L.append(f"Acciones reemplazadas (la receta de sesión les deja menos del {100 * MIN_DIAS:.0f} % de los {D.tope} días): "
                 + "; ".join(f"{t} ({d} días) por {r} ({dr} días)" for t, d, r, dr in D.cambios) + ".")
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


# --- equivalencia con la banda 40 ----------------------------------------------------------------

NEUTRO_D = {"S": (140, 0, 215, 0), "B": (140, 0, 215, 0), "c2": 0, "k": -1}
_EQ = {}


def _eq(ids):
    """Decisiones tick a tick de la banda 40, de la política con los módulos apagados y de la política
    con el módulo D en su punto neutro (140/215 en toda la tabla). Ninguna usa caja ni acciones."""
    conj = _EQ["conj"]
    dif, ticks = [], 0
    for i in ids:
        w = conj.ventana(i)
        da = ideas.Regla(ideas.BandaD(140, 215)).decidir
        db = RG.Politica().decidir
        dc = RG.Politica(D=NEUTRO_D).decidir
        for p in w:
            x = da(p, 0, 0)
            if db(p, 0, 0) != x or dc(p, 0, 0) != x:
                dif.append(i)
                break
        ticks += len(w)
    return dif, ticks


def accion_equivalencia(procesos, cual):
    L = ["# Equivalencia: política con los módulos apagados contra la banda 40", "",
         f"ref/cotas/explorar_regimen.py equivalencia, commit {commit()}. Se comparan las decisiones tick a tick de "
         "ideas.Regla(BandaD(140, 215)), de regimen.Politica() y de regimen.Politica(D con 140/215 en toda la tabla)."]
    pares = []
    if cual == "cinco":
        conj5 = E.completa(reales.carpeta_datos())
        conj5.cargar_series()
        pares.append(("población completa de las cinco empresas", conj5))
    else:
        pares.append(("muestra de las otras acciones", cargar("otras").conj()))
    for nombre, conj in pares:
        _EQ["conj"] = conj
        n = len(conj.filas)
        tr = 200
        dif, ticks = [], 0
        t0 = time.time()
        with Pool(procesos or os.cpu_count()) as pool:
            for d, t in pool.imap_unordered(_eq, [list(range(a, min(n, a + tr))) for a in range(0, n, tr)]):
                dif += d
                ticks += t
        L.append(f"- {nombre}: {n} ventanas, {ticks} decisiones por estrategia, ventanas con alguna diferencia: {len(dif)} "
                 f"({time.time() - t0:.0f} s)" + (f"; primeras: {sorted(dif)[:10]}" if dif else ""))
        print(L[-1], file=sys.stderr)
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, f"regimen_equivalencia_{cual}.txt"), "w").write(txt)
    print(txt)


# --- ajuste en las otras acciones --------------------------------------------------------------

def rivales_otras(D, carpeta):
    import array
    import reales_experimento as rx
    ruta = os.path.join(CACHE, f"rivales_{D.clave()}.pkl")
    if os.path.exists(ruta):
        return pickle.load(open(ruta, "rb"))
    out = {nm: array.array("i") for nm in E.COLUMNAS_C}
    orden, emps = {}, []
    for i, f in enumerate(D.filas):
        if f[0] not in orden:
            orden[f[0]] = []
            emps.append(f[0])
        orden[f[0]].append(i)
    vistos = []
    for emp in emps:
        r = reales.correr(rx.ESTR, carpeta, emp, paso=PASO)
        ne = r["ne"]
        for i in orden[emp]:
            s = D.filas[i][1]
            k = s // PASO
            assert r["ini"][k] == s
            for nm in E.COLUMNAS_C:
                out[nm].append(r["w"][k * ne + rx.J[nm]])
            vistos.append(i)
    assert vistos == list(range(len(D.filas)))
    pickle.dump(out, open(ruta, "wb"))
    return out


SEP_OTRAS = {
    "anios": (lambda f, g: f[2] <= 2022, lambda f, g: f[2] >= 2023),
    "grupos": (lambda f, g: g in ("fin", "sal", "ind"), lambda f, g: g in ("tec", "con")),
}


class CtxO:
    """Muestra de las otras acciones con rivales (C, paso PASO), subconjuntos y torneos."""

    def __init__(self, procesos=None):
        self.carpeta = os.path.join(os.path.expanduser(os.environ.get("P4_DATOS", "~/proyectos/datos_p4")), "otras")
        self.D = cargar("otras")
        self.conj = self.D.conj(self.carpeta)
        self.procesos = procesos
        self.R = rivales_otras(self.D, self.carpeta)
        self.G = grupos_de(self.D)
        todos = list(range(len(self.D.filas)))
        self.idx = {"todas": todos}
        for sep, (aj, va) in SEP_OTRAS.items():
            self.idx[f"{sep}-ajuste"] = [i for i in todos if aj(self.D.filas[i], self.D.grupo[i])]
            self.idx[f"{sep}-validacion"] = [i for i in todos if va(self.D.filas[i], self.D.grupo[i])]
        self.T = {k: E.Torneo(ix, self.R, f"otras-{k}", SEMILLA) for k, ix in self.idx.items()}
        self.Tx = {k: E.Torneo(ix, self.R, f"otras-{k}-sin-copia", SEMILLA, excluir=("espera_banda40",))
                   for k, ix in self.idx.items()}

    def ev(self, specs, info=True):
        return E.evaluar(self.conj, specs, self.procesos, verbose=False, info=info)


def delta(G, rA, rB, idx, dos=True):
    x = [0.0] * len(rA["W"])
    for i in idx:
        x[i] = rA["W"][i] - rB["W"][i]
    m = sum(x[i] for i in idx) / len(idx)
    c = [0.0] * len(x)
    for i in idx:
        c[i] = (x[i] - m) / len(idx)
    return m, ee_contrib(c, G, dos)[0]


def mano(G, W, Wr, idx, nombre, dos=True, sorteos=20000):
    n = len(idx)
    g = sum(1 for i in idx if W[i] > Wr[i])
    e = sum(1 for i in idx if W[i] == Wr[i])
    d, ee = delta(G, {"W": W}, {"W": Wr}, idx, dos)
    rng = random.Random(f"mano3-{SEMILLA}-{nombre}")
    g3 = e3 = 0
    for _ in range(sorteos):
        a, b, c = idx[rng.randrange(n)], idx[rng.randrange(n)], idx[rng.randrange(n)]
        x = W[a] + W[b] + W[c] - Wr[a] - Wr[b] - Wr[c]
        g3 += x > 0
        e3 += x == 0
    return dict(g=100 * g / n, e=100 * e / n, p=100 * (n - g - e) / n, d=d, ee=ee,
                g3=100 * g3 / sorteos, e3=100 * e3 / sorteos, p3=100 * (sorteos - g3 - e3) / sorteos)


def fila_metricas(cx, r, k, rb, nombre, idx=None, T=None, Tx=None):
    idx = cx.idx[k] if idx is None else idx
    T = cx.T[k] if T is None else T
    Tx = cx.Tx[k] if Tx is None else Tx
    m = E.metricas(r, idx, cx.R, T)
    p, q = Tx.puntos(r["W"])
    d, ee = delta(cx.G, r, rb, idx)
    mm = mano(cx.G, r["W"], cx.R[E.RIVAL_TESLA], idx, k)   # mismos sorteos para todas las estrategias
    inf = [x for x in (r["info"][i] for i in idx) if x]
    disp = 100 * sum(1 for x in inf if len(x) > 2 and x[2]) / len(idx) if inf else 0.0
    tope = 100 * sum(1 for x in inf if len(x) > 3 and x[3]) / len(idx) if inf else 0.0
    return (f"| {nombre} | {m['n']} | {fmt(p)} | {100 * q:.1f} | {m['media']:.0f} | {m['p5']} | {m['peor']} | {m['ordenes']:.1f} | "
            f"{d:+.0f} ({ee:.0f}) | {disp:.1f} / {tope:.1f} | {mm['g']:.1f} / {mm['e']:.1f} / {mm['p']:.1f} | "
            f"{mm['d']:+.0f} ({mm['ee']:.0f}) | {mm['g3']:.1f} / {mm['p3']:.1f} |"), dict(pts=p, pri=q, media=m["media"], d=d, ee=ee, p3=mm["p3"])


CAB_M = ("| estrategia | ventanas | pts sin copia | 1.ª sola % | media | p5 | peor | órdenes | Δ con banda 40 (ee) | "
         "módulo A: dispara / tope % | contra el rival: gana / empata / pierde % | Δ con el rival (ee) | 3 rondas: gana / pierde % |")
SEP_M = "|---|---|---|---|---|---|---|---|---|---|---|---|---|"

GRILLA_A = [{"kA": kA, "theta": th, "d": d, "N": N} for kA in (0, 1) for th in RG.THETAS for d in RG.DS for N in (33, 63)]
GRILLA_D = {"c0": (110, 120, 130, 140, 150, 160, 170), "c1": (-10, -5, 0, 5, 10),
            "v0": (185, 195, 205, 215, 225, 235, 245, 256), "v1": (-10, -5, 0, 5, 10),
            "c2": (-5, 0, 5, 10), "k": (-1, 0, 1, 2)}


def nombre_a(A):
    return "ninguno" if A is None else f"A(kA {A['kA']}, theta {A['theta']}, d {A['d']}, N {A['N']})"


def nombre_d(D):
    if D is None:
        return "ninguno"
    return (f"D(S {D['S'][0]}+{D['S'][1]}c/{D['S'][2]}-{D['S'][3]}c, B {D['B'][0]}+{D['B'][1]}c/{D['B'][2]}-{D['B'][3]}c, "
            f"c2 {D['c2']}, k {D['k']})")


def puntos(cx, r, k):
    return cx.T[k].puntos(r["W"])[0]


def ajuste_a(cx, L):
    specs = [RG.spec_politica(None, A) for A in GRILLA_A]
    res = cx.ev(specs)
    elegido = {}
    for k in ("anios-ajuste", "grupos-ajuste", "todas"):
        orden = sorted(range(len(specs)), key=lambda j: (-puntos(cx, res[j], k), -E.metricas(res[j], cx.idx[k], cx.R, cx.T[k])["media"]))
        elegido[k] = GRILLA_A[orden[0]]
        L.append(f"\nMódulo A, ajuste en {k} ({len(cx.idx[k])} ventanas): las 5 mejores de {len(specs)} por puntos de torneo")
        for j in orden[:5]:
            L.append(f"- {nombre_a(GRILLA_A[j])}: pts {fmt(puntos(cx, res[j], k))}, media "
                     f"{E.metricas(res[j], cx.idx[k], cx.R, cx.T[k])['media']:.0f}")
    return elegido


def descenso_d(cx, k, L, A=None, pasadas=3):
    par = {"S": [140, 0, 215, 0], "B": [140, 0, 215, 0], "c2": 0, "k": -1}

    def congelar(q):
        return {"S": tuple(q["S"]), "B": tuple(q["B"]), "c2": q["c2"], "k": q["k"]}

    coords = [(c, j, nm) for c in ("S", "B") for j, nm in enumerate(("c0", "c1", "v0", "v1"))] + [("c2", None, "c2"), ("k", None, "k")]
    actual = congelar(par)
    mejor = puntos(cx, cx.ev([RG.spec_politica(actual, A)])[0], k)
    L.append(f"\nMódulo D, ajuste en {k}: desde la banda 40 (pts {fmt(mejor)}), una coordenada a la vez")
    for pasada in range(pasadas):
        cambio = False
        for c, j, nm in coords:
            cands = []
            for v in GRILLA_D[nm]:
                q = {"S": list(actual["S"]), "B": list(actual["B"]), "c2": actual["c2"], "k": actual["k"]}
                if j is None:
                    if q[c] == v:
                        continue
                    q[c] = v
                else:
                    if q[c][j] == v:
                        continue
                    q[c][j] = v
                cands.append(congelar(q))
            res = cx.ev([RG.spec_politica(q, A) for q in cands])
            for q, r in zip(cands, res):
                pt = puntos(cx, r, k)
                if pt > mejor + 1e-9:
                    mejor, actual, cambio = pt, q, True
            L.append(f"  pasada {pasada + 1}, {c if j is None else c + ' ' + nm}: {nombre_d(actual)} pts {fmt(mejor)}")
        if not cambio:
            break
    return actual


def accion_ajuste(procesos, con_d):
    cx = CtxO(procesos)
    b40 = cx.ev([E.B40], info=False)[0]
    neutro = cx.ev([RG.spec_politica(None, None)])[0]
    igual = sum(1 for i in range(len(b40["W"])) if b40["W"][i] != neutro["W"][i])
    c40 = sum(1 for i in range(len(b40["W"])) if b40["W"][i] != cx.R["espera_banda40"][i])
    L = ["# Ajuste de los módulos en las otras acciones", "",
         f"ref/cotas/explorar_regimen.py ajuste, commit {commit()}. Muestra {cx.D.nombre}: {len(cx.D.filas)} ventanas. "
         "Se elige por puntos de torneo de 3 rondas en la parte de ajuste (rival de Tesla fijo más 8 del campo, 20 000 "
         "sorteos). Validación por años: ajuste con inicio en 2020 a 2022, validación con inicio en 2023 o 2024. Por "
         "grupos: ajuste con fin, sal e ind; validación con tec y con.",
         f"Comprobaciones: política sin módulos contra banda 40 (Python), ventanas distintas: {igual}; banda 40 en Python "
         f"contra espera_banda40 en C: {c40}."]
    elegidoA = ajuste_a(cx, L)
    elegidoD = {}
    if con_d:
        for k in ("anios-ajuste", "grupos-ajuste", "todas"):
            elegidoD[k] = descenso_d(cx, k, L)
    L.append("\n## Validación interna\n")
    for sep in ("anios", "grupos"):
        ka, kv = f"{sep}-ajuste", f"{sep}-validacion"
        filas = [("banda 40", b40)]
        filas.append((f"módulo A: {nombre_a(elegidoA[ka])}", cx.ev([RG.spec_politica(None, elegidoA[ka])])[0]))
        if con_d:
            filas.append((f"módulo D: {nombre_d(elegidoD[ka])}", cx.ev([RG.spec_politica(elegidoD[ka], None)])[0]))
            filas.append(("A y D", cx.ev([RG.spec_politica(elegidoD[ka], elegidoA[ka])])[0]))
        for parte in (ka, kv):
            L.append(f"\n### {parte} ({len(cx.idx[parte])} ventanas)\n")
            L.append(CAB_M)
            L.append(SEP_M)
            for nm, r in filas:
                L.append(fila_metricas(cx, r, parte, b40, nm)[0])
    L.append("\n## Parámetros finales (ajuste con todas las otras acciones)\n")
    L.append(f"- módulo A: {nombre_a(elegidoA['todas'])}")
    if con_d:
        L.append(f"- módulo D: {nombre_d(elegidoD['todas'])}")
    finales = {"A": elegidoA["todas"], "D": elegidoD.get("todas")}
    pickle.dump(finales, open(os.path.join(CACHE, "finales.pkl"), "wb"))
    L.append(f"\nGuardados en build/cotas/regimen/finales.pkl: {finales!r}")
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "regimen_ajuste.txt"), "w").write(txt)
    print(txt)


# --- examen final en las cinco empresas --------------------------------------------------------------

def accion_examen(procesos):
    finales = pickle.load(open(os.path.join(CACHE, "finales.pkl"), "rb"))
    carpeta = reales.carpeta_datos()
    conj = E.completa(carpeta)
    R = E.rivales(conj)
    specs = [("módulo A", RG.spec_politica(None, finales["A"]))]
    if finales.get("D"):
        specs += [("módulo D", RG.spec_politica(finales["D"], None)), ("A y D", RG.spec_politica(finales["D"], finales["A"]))]
    b40 = E.evaluar(conj, [E.B40], procesos, trozo=200, info=False)[0]
    res = E.evaluar(conj, [sp for _, sp in specs], procesos, trozo=200, info=True)
    caso = [x[1] for x in res[0]["info"]]
    filas = [("banda 40", b40)] + [(nm, r) for (nm, _), r in zip(specs, res)]
    L = ["# Examen final en las cinco empresas (una sola vez, parámetros fijos)", "",
         f"ref/cotas/explorar_regimen.py examen, commit {commit()}. Población completa ({len(conj.filas)} ventanas). "
         f"Parámetros del ajuste con todas las otras acciones: A = {nombre_a(finales['A'])}"
         + (f", D = {nombre_d(finales['D'])}" if finales.get("D") else "") + ". Error estándar por grupos de ventanas "
         "vecinas (empresa y bloque de 20 días de inicio), como en las secciones 10 y 11."]
    subs = {"todas": list(range(len(conj.filas)))}
    for sep, (aj, va) in E.SEPARACIONES.items():
        subs[f"{sep}-validacion"] = E.sub(conj, va)
    resumen = {}
    for k, ix in subs.items():
        for cn, cs in (("todas", None), ("S", 1), ("B", 2)):
            sel = ix if cs is None else [i for i in ix if caso[i] == cs]
            T = E.Torneo(sel, R, f"examen-{k}-{cn}", SEMILLA)
            Tx = E.Torneo(sel, R, f"examen-{k}-{cn}-sin-copia", SEMILLA, excluir=("espera_banda40",))
            L.append(f"\n### {k}, caso {cn} ({len(sel)} ventanas)\n")
            L.append(CAB_M)
            L.append(SEP_M)
            for nm, r in filas:
                txt, m = fila_examen(conj, R, r, b40, sel, T, Tx, f"{k}-{cn}")   # mismos sorteos que la sección 10
                L.append(f"| {nm} " + txt)
                resumen[(k, cn, nm)] = m
    L.append("\n## Criterio de la sección 9\n")
    for nm, _ in specs:
        c1 = all(resumen[(k, "todas", nm)]["pts"] > resumen[(k, "todas", "banda 40")]["pts"] for k in ("anios-validacion", "empresas-validacion"))
        c2 = all(resumen[(k, "todas", nm)]["d"] > resumen[(k, "todas", nm)]["ee"] for k in ("anios-validacion", "empresas-validacion"))
        c3 = resumen[("todas", "todas", nm)]["p3"] <= resumen[("todas", "todas", "banda 40")]["p3"]
        L.append(f"- {nm}: 1. más puntos sin la copia en las dos validaciones: {'sí' if c1 else 'no'}; 2. Δ con la banda 40 "
                 f"mayor que 1 ee en las dos validaciones: {'sí' if c2 else 'no'}; 3. no pierde más torneos de 3 rondas "
                 f"contra el rival que la banda 40 en la población: {'sí' if c3 else 'no'} "
                 f"({resumen[('todas', 'todas', nm)]['p3']:.1f} % contra {resumen[('todas', 'todas', 'banda 40')]['p3']:.1f} %)")
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "regimen_examen.txt"), "w").write(txt)
    print(txt)


def types_ns(**kw):
    import types
    return types.SimpleNamespace(**kw)


def fila_examen(conj, R, r, rb, sel, T, Tx, nombre):
    m = E.metricas(r, sel, R, T)
    p, q = Tx.puntos(r["W"])
    P = types_ns(conj=conj)
    d, ee = E.delta_ee(P, r, rb, sel)
    Wr = R[E.RIVAL_TESLA]
    W = r["W"]
    n = len(sel)
    g = sum(1 for i in sel if W[i] > Wr[i])
    e = sum(1 for i in sel if W[i] == Wr[i])
    dr, eer = E.delta_ee(P, r, {"W": Wr}, sel)
    rng = random.Random(f"mano3-{SEMILLA}-{nombre}")
    g3 = p3 = 0
    for _ in range(20000):
        a, b, c = sel[rng.randrange(n)], sel[rng.randrange(n)], sel[rng.randrange(n)]
        x = W[a] + W[b] + W[c] - Wr[a] - Wr[b] - Wr[c]
        g3 += x > 0
        p3 += x < 0
    inf = r.get("info")
    disp = tope = 0.0
    if inf and inf[0] and len(inf[0]) > 3:
        disp = 100 * sum(1 for i in sel if inf[i][2]) / n
        tope = 100 * sum(1 for i in sel if inf[i][3]) / n
    txt = (f"| {n} | {fmt(p)} | {100 * q:.1f} | {m['media']:.0f} | {m['p5']} | {m['peor']} | {m['ordenes']:.1f} | "
           f"{d:+.0f} ({ee:.0f}) | {disp:.1f} / {tope:.1f} | {100 * g / n:.1f} / {100 * e / n:.1f} / {100 * (n - g - e) / n:.1f} | "
           f"{dr:+.0f} ({eer:.0f}) | {100 * g3 / 20000:.1f} / {100 * p3 / 20000:.1f} |")
    return txt, dict(pts=p, d=d, ee=ee, p3=100 * p3 / 20000)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("accion", choices=["filtros", "f3", "equivalencia", "ajuste", "examen"])
    ap.add_argument("--sin-d", action="store_true", help="ajuste solo del módulo A (el D descartado por F1)")
    ap.add_argument("--conjunto", default="cinco")
    ap.add_argument("--procesos", type=int, default=None)
    a = ap.parse_args()
    if a.accion == "filtros":
        accion_filtros(a.conjunto, a.procesos)
    elif a.accion == "f3":
        accion_f3(a.conjunto, a.procesos)
    elif a.accion == "equivalencia":
        accion_equivalencia(a.procesos, a.conjunto)
    elif a.accion == "ajuste":
        accion_ajuste(a.procesos, not a.sin_d)
    elif a.accion == "examen":
        accion_examen(a.procesos)


if __name__ == "__main__":
    main()
