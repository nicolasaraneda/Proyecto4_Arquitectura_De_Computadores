#!/usr/bin/env python3
"""explorar_optimo.py: la política óptima del paseo normalizado (docs/exploracion_ideas.md, sección 13).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

G1 (calibración): en cada ventana, en los ticks t = 500, 1000, 2000, 4000 y 8000 en que todavía
no se ha visto ni 100 ni 255 (fase A), el modelo da P(255 antes que 100 | x, r, v^2) = h_A / g_A
(ref/cotas/paseo_optimo.py) con r = 19 999 - t, interpolando en v^2 entre las tablas de la
grilla. Se agrupan las observaciones en deciles de la probabilidad predicha y se compara con la
frecuencia observada. Pasa si la frecuencia observada crece con la predicha (ningún decil cae
respecto del anterior en más de 2 ee) y ningún decil se aleja más de 10 puntos.

Estimadores de v^2 en el tick t (solo con los precios hasta t):
  verdadero  solo en paseos: (155 / R)^2, con R el rango del paseo sin normalizar (paso de varianza 1)
  S2/t       promedio de (p(n) - p(n-1))^2 con la diferencia acotada a 15 (el del diseño)
  2000       lo mismo en los últimos 2000 ticks (antes de 2000, el acumulado)
  10 ticks   promedio de (p(n) - p(n-10))^2 / 10 (diferencia acotada a 50): agregado, informativo;
             el redondeo a niveles enteros agrega ruido a cada diferencia de un tick y no a la
             varianza de largo plazo, que es la que usa el modelo

Uso (con export P4_DATOS=~/proyectos/datos_p4):
  python3 ref/cotas/explorar_optimo.py g1    -> docs/mediciones/exploracion/optimo_g1.txt
"""
import argparse
import os
import pickle
import random
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorar_ideas as E     # noqa: E402
import explorar_regimen as XR  # noqa: E402
import hashlib                 # noqa: E402
import ideas                   # noqa: E402
import optimo_estrategia as OE  # noqa: E402
import paseo_optimo as P       # noqa: E402

E.CODIGO_EXTRA["optima"] = hashlib.sha256(b"".join(
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f), "rb").read()
    for f in ("optimo_estrategia.py", "paseo_optimo.py", "regimen.py"))).hexdigest()[:16]

# Las cachés de conjuntos de explorar_regimen.py se escribieron corriéndolo como programa principal, así que
# guardan la clase como __main__.Datos; se la presta aquí para poder leerlas.
sys.modules["__main__"].Datos = XR.Datos

TS = (500, 1000, 2000, 4000, 8000)
EST = ("S2/t", "2000", "10 ticks")
CACHE = P.CACHE
SALIDA = XR.SALIDA
# Las cachés .pkl de build/cotas/optimo/ las escribe solo este script en la máquina local.


def _rango_paseo(i):
    rng = random.Random(f"paseo-{XR.SEMILLA}-{i}")
    g = rng.gauss
    v = lo = hi = 0.0
    for _ in range(1, XR.LARGO):
        v += g(0.0, 1.0)
        if v < lo:
            lo = v
        elif v > hi:
            hi = v
    return (155.0 / (hi - lo)) ** 2


def estimadores(w, t):
    """v^2 estimado con los precios w[0..t]."""
    s1 = 0
    for j in range(1, t + 1):
        d = w[j] - w[j - 1]
        d = -d if d < 0 else d
        s1 += (15 if d > 15 else d) ** 2
    if t >= 2000:
        s2 = 0
        for j in range(t - 1999, t + 1):
            d = w[j] - w[j - 1]
            d = -d if d < 0 else d
            s2 += (15 if d > 15 else d) ** 2
        e2 = s2 / 2000
    else:
        e2 = s1 / t
    s3 = 0
    for j in range(10, t + 1):
        d = w[j] - w[j - 10]
        d = -d if d < 0 else d
        s3 += (50 if d > 50 else d) ** 2
    return {"S2/t": s1 / t, "2000": e2, "10 ticks": s3 / (10 * (t - 9))}


_G = {}


def _obs(ids):
    T, V, verd = _G["T"], _G["v"], _G.get("verdadero")
    out = []
    for i in ids:
        w = V[i]
        i100, i255 = w.index(100), w.index(255)
        y = 1 if i255 < i100 else 0
        primero = min(i100, i255)
        for t in TS:
            if t >= primero:
                break
            x, r = w[t], P.N - 1 - t
            ests = estimadores(w, t)
            if verd is not None:
                ests["verdadero"] = verd[i]
            pred = {k: P.p255(T, v2, x, r) for k, v2 in ests.items()}
            out.append((i, t, y, pred, ests))
    return ids, out


def observaciones(D, verdadero=None, procesos=None):
    ruta = os.path.join(CACHE, f"g1obs_{D.clave()}.pkl")
    if os.path.exists(ruta):
        return pickle.load(open(ruta, "rb"))
    _G["T"] = P.tablas_pA()
    _G["v"] = D.ventanas
    _G["verdadero"] = verdadero
    n = len(D.ventanas)
    tr = max(5, n // ((procesos or os.cpu_count()) * 6))
    obs = []
    with Pool(procesos or os.cpu_count()) as pool:
        for _, o in pool.imap_unordered(_obs, [list(range(a, min(n, a + tr))) for a in range(0, n, tr)]):
            obs += o
    obs.sort(key=lambda o: (o[0], o[1]))
    pickle.dump(obs, open(ruta, "wb"))
    return obs


def tabla_g1(D, obs, est, L, titulo):
    G = XR.grupos_de(D)
    dos = D.filas[0][0] != "paseo" and len({f[0] for f in D.filas}) > 5
    ob = [o for o in obs if o[3][est] == o[3][est]]          # sin NaN
    ob.sort(key=lambda o: o[3][est])
    n = len(ob)
    L.append(f"\n### {titulo}: estimador {est} ({n} observaciones en {len({o[0] for o in ob})} ventanas)\n")
    L.append("| decil | observaciones | P predicha media | frecuencia observada (ee) | diferencia (puntos) |")
    L.append("|---|---|---|---|---|")
    filas = []
    for d in range(10):
        part = ob[d * n // 10:(d + 1) * n // 10]
        m = len(part)
        pm = sum(o[3][est] for o in part) / m
        fo = sum(o[2] for o in part) / m
        c = [0.0] * len(D.filas)
        for o in part:
            c[o[0]] += (o[2] - fo) / m
        ee = XR.ee_contrib(c, G, dos)[0]
        filas.append((pm, fo, ee))
        L.append(f"| {d + 1} | {m} | {pm:.3f} | {fo:.3f} ({ee:.3f}) | {100 * (fo - pm):+.1f} |".replace(".", ","))
    crece = all(filas[d + 1][1] >= filas[d][1] - 2 * (filas[d][2] ** 2 + filas[d + 1][2] ** 2) ** 0.5 for d in range(9))
    lejos = max(abs(fo - pm) for pm, fo, _ in filas)
    pasa = crece and lejos <= 0.10
    L.append(f"\nCrece con la predicha: {'sí' if crece else 'no'}; mayor distancia {fmt(100 * lejos, 1)} puntos; "
             f"G1 {'PASA' if pasa else 'no pasa'}.")
    # por tick de observación
    partes = []
    for t in TS:
        o_t = [o for o in ob if o[1] == t]
        if o_t:
            partes.append(f"t = {t}: {len(o_t)} obs., predicha {fmt(sum(o[3][est] for o in o_t) / len(o_t))}, "
                          f"observada {fmt(sum(o[2] for o in o_t) / len(o_t))}")
    L.append("Por tick: " + "; ".join(partes) + ".")
    return pasa, lejos, crece


def fmt(x, d=3):
    return f"{x:.{d}f}".replace(".", ",")


def accion_g1(procesos):
    t0 = time.time()
    P.tablas_pA()
    print(f"  tablas del modelo listas ({time.time() - t0:.0f} s)", file=sys.stderr)
    L = ["# G1: calibración del modelo del paseo normalizado", "",
         f"ref/cotas/explorar_optimo.py g1, commit {XR.commit()}. P(255 antes que 100) del modelo (h_A / g_A, "
         "ref/cotas/paseo_optimo.py) en los ticks t = 500, 1000, 2000, 4000 y 8000 de cada ventana que siguen en la fase A, "
         "con r = 19 999 - t e interpolación lineal en v^2 entre las tablas de v^2 = 1/8, 1/4, 3/8, 1/2, 3/4, 1, 3/2 y 2 "
         "(fuera de ese rango, la del borde). Deciles de la probabilidad predicha. Error estándar por grupos: ventana en los "
         "paseos; bloques de 20 y 60 días de inicio (y fecha y empresa en las otras acciones) en los datos reales, el mayor.",
         "Pasa si ningún decil cae respecto del anterior en más de 2 ee y ningún decil se aleja más de 10 puntos de lo predicho."]
    resumen = []
    with Pool(procesos or os.cpu_count()) as pool:
        verdadero = pool.map(_rango_paseo, range(XR.N_PASEOS), chunksize=20)
    conjuntos = [("paseo", "Paseos normalizados", verdadero), ("otras", "Otras acciones", None), ("cinco", "Cinco empresas", None)]
    dist = []
    for nombre, titulo, verd in conjuntos:
        D = XR.cargar(nombre, procesos)
        obs = observaciones(D, verd, procesos)
        ests = (("verdadero",) if verd is not None else ()) + EST
        for est in ests:
            pasa, lejos, crece = tabla_g1(D, obs, est, L, titulo)
            resumen.append((titulo, est, pasa, lejos, crece))
        # distribución de los estimadores
        for est in ests:
            v = sorted(o[4][est] for o in obs)
            q = [v[int(f * (len(v) - 1))] for f in (0.1, 0.5, 0.9)]
            dist.append(f"| {titulo} | {est} | {fmt(q[0])} | {fmt(q[1])} | {fmt(q[2])} |")
    L.append("\n## Resumen\n")
    L.append("| conjunto | estimador | crece | mayor distancia (puntos) | G1 |")
    L.append("|---|---|---|---|---|")
    for titulo, est, pasa, lejos, crece in resumen:
        L.append(f"| {titulo} | {est} | {'sí' if crece else 'no'} | {fmt(100 * lejos, 1)} | {'pasa' if pasa else 'no pasa'} |")
    L.append("\n## v^2 estimado en los puntos de observación (percentiles 10, 50 y 90)\n")
    L.append("| conjunto | estimador | p10 | p50 | p90 |")
    L.append("|---|---|---|---|---|")
    L += dist
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "optimo_g1.txt"), "w").write(txt)
    print(txt)


# --- paso 3: equivalencia con la política apagada ---------------------------------------------

def _eq(ids):
    conj = _G["conj"]
    dif = []
    for i in ids:
        w = conj.ventana(i)
        da = ideas.Regla(ideas.BandaD(140, 215)).decidir
        db = OE.Optima().decidir
        for p in w:
            if da(p, 0, 0) != db(p, 0, 0):
                dif.append(i)
                break
    return dif, len(ids)


def accion_equivalencia(procesos, cual):
    if cual == "cinco":
        conj = E.completa(XR.reales.carpeta_datos())
        conj.cargar_series()
        nombre = "población completa de las cinco empresas"
    else:
        conj = XR.cargar("otras").conj()
        nombre = "muestra de las otras acciones"
    _G["conj"] = conj
    n = len(conj.filas)
    dif, tot = [], 0
    t0 = time.time()
    with Pool(procesos or os.cpu_count()) as pool:
        for d, k in pool.imap_unordered(_eq, [list(range(a, min(n, a + 200))) for a in range(0, n, 200)]):
            dif += d
            tot += k
    txt = (f"# Equivalencia: política óptima apagada contra la banda 40\n\nref/cotas/explorar_optimo.py equivalencia "
           f"--conjunto {cual}, commit {XR.commit()}. Decisiones tick a tick de ideas.Regla(BandaD(140, 215)) y de "
           f"optimo_estrategia.Optima() (sin tabla).\n- {nombre}: {tot} ventanas, {20000 * tot} decisiones por regla, ventanas "
           f"con alguna diferencia: {len(dif)} ({time.time() - t0:.0f} s)\n")
    open(os.path.join(SALIDA, f"optimo_equivalencia_{cual}.txt"), "w").write(txt)
    print(txt)


# --- pasos 3 a 5: variantes, estimador, G2 y G3 en las otras acciones -------------------------------

COMBOS = [(v, o) for v in ("V1", "V2", "V3") for o in ("log", "lineal")]
CAB = ("| estrategia | pts sin copia | 1.ª sola % | media | p5 | peor | órdenes | Δ con banda 40 (ee) | "
       "contra el rival: gana / empata / pierde % | 3 rondas: gana / pierde % |")
SEPC = "|---|---|---|---|---|---|---|---|---|---|"


def fila(cx, r, k, rb, nombre):
    m = E.metricas(r, cx.idx[k], cx.R, cx.T[k])
    p, q = cx.Tx[k].puntos(r["W"])
    d, ee = XR.delta(cx.G, r, rb, cx.idx[k])
    mm = XR.mano(cx.G, r["W"], cx.R[E.RIVAL_TESLA], cx.idx[k], k)
    txt = (f"| {nombre} | {fmt(p)} | {fmt(100 * q, 1)} | {m['media']:.0f} | {m['p5']} | {m['peor']} | {fmt(m['ordenes'], 1)} | "
           f"{d:+.0f} ({ee:.0f}) | {fmt(mm['g'], 1)} / {fmt(mm['e'], 1)} / {fmt(mm['p'], 1)} | {fmt(mm['g3'], 1)} / {fmt(mm['p3'], 1)} |")
    return txt, dict(pts=p, pri=q, media=m["media"], d=d, ee=ee, p3=mm["p3"])


def nombre_spec(sp):
    d = sp[1]
    if d.get("variante") is None:
        return "apagada"
    return f"{d['variante']} {d['objetivo']}, {d['estimador']}" + (", comprimida" if d.get("comprimida") else "")


def valores_modelo(L):
    """Ganancia en el modelo: valor (log) en t = 0 de cada variante menos el de la banda 40, en fase A con s = 0."""
    L.append("\n## Ganancia dentro del modelo (objetivo log, inicio en la fase A en caja, r = 19 999)\n")
    L.append("Diferencia de E[log patrimonio final] con la banda 40 en el mismo modelo, en porcentaje, para x0 = 140, 177 y 215.\n")
    L.append("| v^2 | V1 | V2 | V3 |")
    L.append("|---|---|---|---|")
    for j, v2 in enumerate(P.V2S):
        b = P.valores("B40", "log", j)["A"][0]
        celdas = []
        for var in ("V1", "V2", "V3"):
            a = P.valores(var, "log", j)["A"][0]
            celdas.append(" / ".join(fmt(100 * (a[x - P.LO] - b[x - P.LO]), 2) for x in (140, 177, 215)))
        L.append(f"| {fmt(v2, 3)} | " + " | ".join(celdas) + " |")


def accion_g2(procesos):
    for v, o in COMBOS:
        OE.tablas(v, o)
    for v, o in COMBOS:
        if v != "V3":
            OE.comprimida(v, o)
    cx = XR.CtxO(procesos)
    b40 = cx.ev([E.B40], info=False)[0]
    specs = [OE.spec(v, o, "S2/t") for v, o in COMBOS] + [OE.spec(v, o, "2000") for v, o in COMBOS]
    specs_c = [OE.spec(v, o, "S2/t", comprimida=True) for v, o in COMBOS if v != "V3"] + \
              [OE.spec(v, o, "2000", comprimida=True) for v, o in COMBOS if v != "V3"]
    res = dict(zip(map(repr, specs + specs_c), cx.ev(specs + specs_c)))
    apag = cx.ev([OE.spec(None)])[0]
    L = ["# Política óptima del paseo normalizado: variantes, estimador, G2 y G3 en las otras acciones", "",
         f"ref/cotas/explorar_optimo.py g2, commit {XR.commit()}. Muestra {cx.D.nombre}: {len(cx.D.filas)} ventanas. Tablas "
         "de la programación dinámica de ref/cotas/paseo_optimo.py (costo de un cambio de posición: 10 / 15 000). Error "
         "estándar por grupos (bloques de 20 y 60 días de inicio, y fecha y empresa), el mayor.",
         f"Comprobación: política apagada contra la banda 40, ventanas con patrimonio distinto: "
         f"{sum(1 for i in range(len(b40['W'])) if b40['W'][i] != apag['W'][i])}."]
    valores_modelo(L)
    L.append(f"\n## Todas las otras acciones ({len(cx.idx['todas'])} ventanas)\n")
    L.append(CAB)
    L.append(SEPC)
    met = {}
    L.append(fila(cx, b40, "todas", b40, "banda 40")[0])
    for sp in specs + specs_c:
        t, m = fila(cx, res[repr(sp)], "todas", b40, nombre_spec(sp))
        L.append(t)
        met[repr(sp)] = m
    # elección: variante y objetivo por puntos con S2/t; después S2/t contra 2000
    base = [OE.spec(v, o, "S2/t") for v, o in COMBOS]
    elegido = max(base, key=lambda sp: (met[repr(sp)]["pts"], met[repr(sp)]["media"]))
    v, o = elegido[1]["variante"], elegido[1]["objetivo"]
    alt = OE.spec(v, o, "2000")
    d_alt, ee_alt = XR.delta(cx.G, res[repr(alt)], res[repr(elegido)], cx.idx["todas"])
    usa2000 = met[repr(alt)]["pts"] > met[repr(elegido)]["pts"] and d_alt > ee_alt
    final = alt if usa2000 else elegido
    L.append("\n## Elección (reglas fijadas antes de correr)\n")
    L.append(f"- Variante y objetivo, por puntos de torneo con S2/t: **{v} {o}** ({fmt(met[repr(elegido)]['pts'])} puntos).")
    L.append(f"- Ventana de 2000 contra S2/t en {v} {o}: {fmt(met[repr(alt)]['pts'])} contra {fmt(met[repr(elegido)]['pts'])} "
             f"puntos, diferencia de patrimonio {d_alt:+.0f} (ee {ee_alt:.0f}). Se cambia a 2000 solo si tiene más puntos y "
             f"gana por más de 1 ee: {'sí' if usa2000 else 'no'}. Estimador: **{final[1]['estimador']}**.")
    mf = met[repr(final)]
    g2 = mf["d"] > 2 * mf["ee"]
    L.append(f"\n## G2: política completa contra la banda 40\n\n{nombre_spec(final)}: {mf['d']:+.0f} (ee {mf['ee']:.0f}). "
             f"Pasa si gana por más de 2 ee: **{'PASA' if g2 else 'no pasa'}**.")
    if v != "V3":
        comp = OE.spec(v, o, final[1]["estimador"], comprimida=True)
        mc = met[repr(comp)]
        frac = mc["d"] / mf["d"] if mf["d"] > 0 else float("nan")
        g3 = mf["d"] > 0 and frac >= 0.8
        L.append(f"\n## G3: compresión\n\nComprimida ({nombre_spec(comp)}): {mc['d']:+.0f} (ee {mc['ee']:.0f}), "
                 f"{fmt(100 * frac, 1)} % de la ganancia completa. Pasa si conserva al menos 80 %: **{'PASA' if g3 else 'no pasa'}**.")
    L.append("\n## Validación interna de la elegida (no se ajusta nada; informativo)\n")
    for k in ("anios-ajuste", "anios-validacion", "grupos-ajuste", "grupos-validacion"):
        L.append(f"\n### {k} ({len(cx.idx[k])} ventanas)\n")
        L.append(CAB)
        L.append(SEPC)
        L.append(fila(cx, b40, k, b40, "banda 40")[0])
        L.append(fila(cx, res[repr(final)], k, b40, nombre_spec(final))[0])
    import pickle as _pk
    _pk.dump({"final": final}, open(os.path.join(CACHE, "elegida.pkl"), "wb"))
    if v == "V3":
        L.append("\n## G3\n\nLa variante elegida tiene tres posiciones; su compresión se evalúa con `explorar_optimo.py g3` "
                 "(optimo_g3.txt).")
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "optimo_g2.txt"), "w").write(txt)
    print(txt)


def accion_g3(procesos):
    import pickle as _pk
    final = _pk.load(open(os.path.join(CACHE, "elegida.pkl"), "rb"))["final"]
    v, o, est = final[1]["variante"], final[1]["objetivo"], final[1]["estimador"]
    OE.tablas(v, o)
    OE.comprimida(v, o)
    cx = XR.CtxO(procesos)
    b40 = cx.ev([E.B40], info=False)[0]
    comp = OE.spec(v, o, est, comprimida=True)
    rf, rc = cx.ev([final, comp])
    L = ["# G3: compresión de la variante elegida", "",
         f"ref/cotas/explorar_optimo.py g3, commit {XR.commit()}. Variante elegida en optimo_g2.txt: {nombre_spec(final)}. "
         + ("Compresión de tres posiciones: por celda (clase de v^2, tramo de 1250 ticks) y por cada s, los umbrales a1, a2 "
            "(arriba: media posición desde a1, completa desde a2) y b1, b2 (abajo), del r del medio del tramo; 12 bytes por "
            "celda, 1536 en la fase A." if v == "V3" else "Cuatro bytes por celda, 512 en la fase A."), "", CAB, SEPC]
    tb, _ = fila(cx, b40, "todas", b40, "banda 40")
    tf, mf = fila(cx, rf, "todas", b40, nombre_spec(final))
    tc, mc = fila(cx, rc, "todas", b40, nombre_spec(comp))
    L += [tb, tf, tc]
    frac = mc["d"] / mf["d"] if mf["d"] > 0 else float("nan")
    g3 = mf["d"] > 0 and frac >= 0.8
    L.append(f"\nLa comprimida conserva {fmt(100 * frac, 1)} % de la ganancia de la completa ({mc['d']:+.0f} contra "
             f"{mf['d']:+.0f}). G3 pide al menos 80 %: **{'PASA' if g3 else 'no pasa'}**.")
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "optimo_g3.txt"), "w").write(txt)
    print(txt)


# --- guardas, diagnóstico y elección (pedido del 19/11, noche) ---------------------------------------

def guardas_v3():
    out = [None]
    for d in (16, 24, 32):
        out.append((d, False, False))
    out += [(0, True, False), (0, False, True)]
    for d in (16, 24, 32):
        out.append((d, True, False))
    for d in (16, 24, 32):
        out.append((d, False, True))
    out.append((0, True, True))
    for d in (16, 24, 32):
        out.append((d, True, True))
    return out


def guardas_v1():
    return [g for g in guardas_v3() if g is None or not g[1]]


def nombre_guarda(g):
    if g is None:
        return "sin guarda"
    d, media, alta = g
    partes = ([f"a{d}"] if d else []) + (["b"] if media else []) + (["c"] if alta else [])
    return "+".join(partes)


def spec_g(variante, g):
    return OE.spec(variante, "log", "S2/t", comprimida=True, placa=True, guarda=g)


FASE_N = "ABCD"


def _diag(ids):
    V = _G["v"]
    out = []
    for i in ids:
        w = V[i]
        S = [ideas.crear(spec_g("V3", None)), ideas.UnaVezR(100, 220), ideas.Regla(ideas.BandaD(140, 215))]
        caja, acc, d, Wp = [10000] * 3, [0] * 3, [ideas.M] * 3, [10000] * 3
        acum = {}
        lab = None
        vlo = vhi = False
        for p in w:
            dW = [0] * 3
            for k in range(3):
                b = d[k]
                if b:
                    a = b >> 6
                    q = b & 63
                    if a == 1:
                        t = (caja[k] - 5) // p
                        if q > t:
                            q = t
                        if q > 0:
                            caja[k] -= q * p + 5
                            acc[k] += q
                    elif a == 2:
                        if q > acc[k]:
                            q = acc[k]
                        if q > 0 and caja[k] + q * p >= 5:
                            caja[k] += q * p - 5
                            acc[k] -= q
                W = caja[k] + acc[k] * p
                dW[k] = W - Wp[k]
                Wp[k] = W
            if lab is not None and (dW[0] or dW[1] or dW[2]):
                a = acum.setdefault(lab, [0, 0, 0])
                a[0] += dW[0] - dW[1]
                a[1] += dW[0] - dW[2]
                a[2] += dW[0]
            for k in range(3):
                d[k] = S[k].decidir(p, caja[k], acc[k])
            if p <= 100:
                vlo = True
            elif p >= 255:
                vhi = True
            fase = "D" if (vlo and vhi) else "B" if vlo else "C" if vhi else "A"
            lab = (fase, S[0].cv)
        out.append((i, Wp, acum))
    return ids, out


def diagnostico(cx, procesos, L):
    ruta = os.path.join(CACHE, f"diag_{cx.D.clave()}_{E.CODIGO_EXTRA['optima']}.pkl")
    if os.path.exists(ruta):
        res = pickle.load(open(ruta, "rb"))
    else:
        _G["v"] = cx.D.ventanas
        n = len(cx.D.ventanas)
        res = [None] * n
        with Pool(procesos or os.cpu_count()) as pool:
            for _, o in pool.imap_unordered(_diag, [list(range(a, min(n, a + 100))) for a in range(0, n, 100)]):
                for i, Wp, ac in o:
                    res[i] = (Wp, ac)
        pickle.dump(res, open(ruta, "wb"))
    Wv = [r[0][0] for r in res]
    Wr = [r[0][1] for r in res]
    ok_r = sum(1 for i in range(len(res)) if Wr[i] == cx.R[E.RIVAL_TESLA][i])
    L.append(f"\nComprobación: el rival en Python coincide con el de C en {ok_r} de {len(res)} ventanas.")
    idx = cx.idx["todas"]
    n = len(idx)
    rng = random.Random(f"mano3-{XR.SEMILLA}-todas")
    perdidas = []
    for _ in range(20000):
        a, b, c = idx[rng.randrange(n)], idx[rng.randrange(n)], idx[rng.randrange(n)]
        if Wv[a] + Wv[b] + Wv[c] - Wr[a] - Wr[b] - Wr[c] < 0:
            perdidas.append((a, b, c))
    peores = sorted(idx, key=lambda i: Wv[i])[:len(idx) // 100]

    def tabla(ventanas, medida, titulo):
        tot = {}
        for i in ventanas:
            for lab, v in res[i][1].items():
                tot[lab] = tot.get(lab, 0) + v[medida]
        neto = sum(tot.values())
        L.append(f"\n{titulo}: total {neto:+.0f} ({neto / len(ventanas):+.0f} por ventana).\n")
        L.append("| fase | " + " | ".join(["antes de 390"] + [f"v² {fmt(P.V2S[j], 3)}" for j in range(8)]) + " | total fase |")
        L.append("|---|" + "---|" * 10)
        for F in FASE_N:
            celdas = [tot.get((F, j), 0) for j in range(-1, 8)]
            L.append(f"| {F} | " + " | ".join(f"{100 * c / abs(neto):+.0f} %" if neto else "0" for c in celdas)
                     + f" | {100 * sum(celdas) / abs(neto):+.0f} % |")
        col = [sum(tot.get((F, j), 0) for F in FASE_N) for j in range(-1, 8)]
        L.append("| total clase | " + " | ".join(f"{100 * c / abs(neto):+.0f} %" for c in col) + " | 100 % |")

    L.append(f"\n### Torneos de 3 rondas que V3 pierde contra el rival de Tesla ({len(perdidas)} de 20 000)\n")
    L.append("Se reparte la diferencia de patrimonio V3 menos rival de las tres ventanas de cada torneo perdido según la fase y "
             "la clase de v² del tick en que ocurrió cada cambio (la clase de placa de V3 en ese momento). Porcentajes del total "
             "neto perdido (un negativo es pérdida).")
    tabla([i for t in perdidas for i in t], 0, "Diferencia con el rival en los torneos perdidos")
    L.append(f"\n### El 1 % de peores ventanas de V3 ({len(peores)} ventanas, patrimonio de {Wv[peores[0]]} a {Wv[peores[-1]]})\n")
    tabla(peores, 2, "Resultado propio (patrimonio final menos 10 000)")
    tabla(peores, 1, "Diferencia con la banda 40")


def eleccion(cands, met, b40pts):
    """Regla de Nicolás: más puntos entre las que pierden a lo más 5 % de los torneos de 3 rondas contra el
    rival; si ninguna, la que menos pierde entre las que superan en puntos a la banda 40."""
    elig = [c for c in cands if met[c]["p3"] <= 5.0]
    if elig:
        return max(elig, key=lambda c: (met[c]["pts"], met[c]["media"])), "regla 1 (pierde a lo más 5 %)"
    sup = [c for c in cands if met[c]["pts"] > b40pts]
    if sup:
        return min(sup, key=lambda c: (met[c]["p3"], -met[c]["pts"])), "regla 2 (ninguna pierde a lo más 5 %)"
    return None, "ninguna supera a la banda 40 en puntos"


def accion_guardas(procesos):
    for v in ("V3", "V1"):
        OE.tablas(v, "log")
        OE.comprimida(v, "log")
    cx = XR.CtxO(procesos)
    b40 = cx.ev([E.B40], info=False)[0]
    L = ["# Política óptima: diagnóstico de pérdidas, guardas de la fase A y elección", "",
         f"ref/cotas/explorar_optimo.py guardas, commit {XR.commit()}. Otras acciones ({len(cx.D.filas)} ventanas). Todo con la "
         "tabla comprimida y la clase de placa (cortes en 1/64 comparados con sumas, histéresis de 64 ticks), que es lo que "
         "iría a la placa. Torneos contra el rival con los mismos 20 000 sorteos para todas las variantes.",
         "Guardas sobre las compras de la fase A: (a) tope de d niveles bajo la entrada, sin volver a entrar en la fase A de esa "
         "ronda; (b) nunca más de media posición en la fase A (solo V3); (c) no aumentar la posición en la fase A con v² en las "
         "dos clases más altas (3/2 y 2)."]
    L.append("\n## Diagnóstico de V3 sin guarda\n")
    diagnostico(cx, procesos, L)
    tb, mb = fila(cx, b40, "todas", b40, "banda 40")
    elegidas = {}
    for v, gs in (("V3", guardas_v3()), ("V1", guardas_v1())):
        specs = [spec_g(v, g) for g in gs]
        res = cx.ev(specs)
        met, filas = {}, []
        for g, sp, r in zip(gs, specs, res):
            t, m = fila(cx, r, "todas", b40, f"{v} log, {nombre_guarda(g)}")
            met[repr(sp)] = m
            filas.append(t)
        L.append(f"\n## {v} log con guardas ({len(cx.idx['todas'])} ventanas)\n")
        L += [CAB, SEPC, tb] + filas
        el, como = eleccion([repr(sp) for sp in specs], met, mb["pts"])
        if el is None:
            L.append(f"\nElegida: ninguna ({como}).")
            continue
        sp_el = specs[[repr(x) for x in specs].index(el)]
        elegidas[v] = sp_el
        m = met[el]
        L.append(f"\nElegida por la {como}: **{v} log, {nombre_guarda(sp_el[1].get('guarda'))}**: {fmt(m['pts'])} puntos, "
                 f"pierde {fmt(m['p3'], 1)} % de los torneos contra el rival, {m['d']:+.0f} (ee {m['ee']:.0f}) contra la banda 40.")
        L.append("\nValidación interna de la elegida (informativa):\n")
        L += [CAB, SEPC]
        r_el = cx.ev([sp_el])[0]
        for k in ("anios-validacion", "grupos-validacion"):
            L.append(fila(cx, b40, k, b40, f"banda 40 ({k})")[0])
            L.append(fila(cx, r_el, k, b40, f"{v} log, {nombre_guarda(sp_el[1].get('guarda'))} ({k})")[0])
    pickle.dump(elegidas, open(os.path.join(CACHE, "elegidas_guardas.pkl"), "wb"))
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "optimo_guardas.txt"), "w").write(txt)
    print(txt)


def accion_examen(procesos):
    import regimen as RG
    elegidas = pickle.load(open(os.path.join(CACHE, "elegidas_guardas.pkl"), "rb"))
    sp = elegidas["V3"]
    OE.tablas("V3", "log")
    OE.comprimida("V3", "log")
    finales_A = pickle.load(open(os.path.join(XR.CACHE, "finales.pkl"), "rb"))
    carpeta = XR.reales.carpeta_datos()
    conj = E.completa(carpeta)
    R = E.rivales(conj)
    b40 = E.evaluar(conj, [E.B40], procesos, trozo=200, info=False)[0]
    rA = E.evaluar(conj, [RG.spec_politica(None, finales_A["A"])], procesos, trozo=200, info=True)[0]
    rV = E.evaluar(conj, [sp], procesos, trozo=200, info=True)[0]
    caso = [x[1] for x in rA["info"]]
    filas = [("banda 40", b40), ("banda 40 + módulo A", rA), (f"V3 log, {nombre_guarda(sp[1].get('guarda'))}", rV)]
    L = ["# Examen de la política óptima del paseo en las cinco empresas (una sola vez)", "",
         f"ref/cotas/explorar_optimo.py examen, commit {XR.commit()}. Población completa ({len(conj.filas)} ventanas). Variante "
         f"elegida en las otras acciones (optimo_guardas.txt): {nombre_spec(sp)}, {nombre_guarda(sp[1].get('guarda'))}, tabla "
         "comprimida y clase de placa. Es la segunda mirada a las cinco empresas (la primera fue el examen del módulo A). Error "
         "estándar por grupos de ventanas vecinas (empresa y bloque de 20 días de inicio), como en las secciones 10 a 12. "
         "Torneos contra el rival con los mismos sorteos de la sección 10. En la columna del módulo A, para V3: ventanas en que "
         "usó la tabla / en que cortó por la guarda (a)."]
    subs = {"todas": list(range(len(conj.filas)))}
    for sep, (aj, va) in E.SEPARACIONES.items():
        subs[f"{sep}-validacion"] = E.sub(conj, va)
    resumen = {}
    for k, ix in subs.items():
        for cn, cs in (("todas", None), ("S", 1), ("B", 2)):
            sel = ix if cs is None else [i for i in ix if caso[i] == cs]
            T = E.Torneo(sel, R, f"examen-{k}-{cn}", XR.SEMILLA)
            Tx = E.Torneo(sel, R, f"examen-{k}-{cn}-sin-copia", XR.SEMILLA, excluir=("espera_banda40",))
            L.append(f"\n### {k}, caso {cn} ({len(sel)} ventanas)\n")
            L.append(XR.CAB_M)
            L.append(XR.SEP_M)
            for nm, r in filas:
                txt, m = XR.fila_examen(conj, R, r, b40, sel, T, Tx, f"{k}-{cn}")
                L.append(f"| {nm} " + txt)
                resumen[(k, cn, nm)] = m
    L.append("\n## Criterio (sección 7 del diseño, con el punto 3 cambiado por Nicolás antes del examen)\n")
    for nm, _ in filas[1:]:
        c1 = all(resumen[(k, "todas", nm)]["pts"] > resumen[(k, "todas", "banda 40")]["pts"] for k in ("anios-validacion", "empresas-validacion"))
        c2 = all(resumen[(k, "todas", nm)]["d"] > resumen[(k, "todas", nm)]["ee"] for k in ("anios-validacion", "empresas-validacion"))
        c3 = resumen[("todas", "todas", nm)]["p3"] <= 10.0
        L.append(f"- {nm}: 1. más puntos sin la copia que la banda 40 en las dos validaciones: {'sí' if c1 else 'no'} "
                 f"(años {fmt(resumen[('anios-validacion', 'todas', nm)]['pts'])} contra "
                 f"{fmt(resumen[('anios-validacion', 'todas', 'banda 40')]['pts'])}; empresas "
                 f"{fmt(resumen[('empresas-validacion', 'todas', nm)]['pts'])} contra "
                 f"{fmt(resumen[('empresas-validacion', 'todas', 'banda 40')]['pts'])}); 2. Δ con la banda 40 mayor que 1 ee en "
                 f"las dos: {'sí' if c2 else 'no'} (años {resumen[('anios-validacion', 'todas', nm)]['d']:+.0f} con ee "
                 f"{resumen[('anios-validacion', 'todas', nm)]['ee']:.0f}; empresas {resumen[('empresas-validacion', 'todas', nm)]['d']:+.0f} "
                 f"con ee {resumen[('empresas-validacion', 'todas', nm)]['ee']:.0f}); 3. pierde a lo más 10 % de los torneos de 3 "
                 f"rondas contra el rival en la población: {'sí' if c3 else 'no'} ({fmt(resumen[('todas', 'todas', nm)]['p3'], 1)} %)")
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "optimo_examen.txt"), "w").write(txt)
    print(txt)


def accion_casos(procesos):
    """Diferencia de la elegida (V3 con guarda) con la banda 40 por caso S y B en las otras acciones, desde la caché.
    Sirve para leer el examen: en qué proporción de casos S la ventaja se anula."""
    cx = XR.CtxO(procesos)
    b40 = cx.ev([E.B40], info=False)[0]
    sp = pickle.load(open(os.path.join(CACHE, "elegidas_guardas.pkl"), "rb"))["V3"]
    r = cx.ev([sp])[0]
    caso = [x[1] for x in r["info"]]
    L = ["# Elegida contra la banda 40 por caso S y B en las otras acciones", "",
         f"ref/cotas/explorar_optimo.py casos, commit {XR.commit()}. {nombre_spec(sp)}, {nombre_guarda(sp[1].get('guarda'))}, "
         "tabla comprimida y clase de placa. Caso S: el 100 llega antes que el 255; caso B: al revés. Error estándar como en "
         "optimo_guardas.txt. Proporción de equilibrio: la fracción de casos S con la que la diferencia media sería cero, "
         "d_B / (d_B - d_S).", "",
         "| subconjunto | ventanas | caso S: ventanas (%) | Δ caso S (ee) | caso B: ventanas (%) | Δ caso B (ee) | equilibrio en S |",
         "|---|---|---|---|---|---|---|"]
    for k in ("todas", "anios-validacion", "grupos-validacion"):
        ix = cx.idx[k]
        c = []
        for cs in (1, 2):
            sel = [i for i in ix if caso[i] == cs]
            d, ee = XR.delta(cx.G, r, b40, sel)
            c.append((len(sel), d, ee))
        (nS, dS, eS), (nB, dB, eB) = c
        L.append(f"| {k} | {len(ix)} | {nS} ({fmt(100 * nS / len(ix), 1)}) | {dS:+.0f} ({eS:.0f}) | {nB} ({fmt(100 * nB / len(ix), 1)}) "
                 f"| {dB:+.0f} ({eB:.0f}) | {fmt(100 * dB / (dB - dS), 1)} % |")
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "optimo_casos_otras.txt"), "w").write(txt)
    print(txt)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("accion", choices=["g1", "g2", "g3", "equivalencia", "guardas", "examen", "casos"])
    ap.add_argument("--conjunto", default="otras")
    ap.add_argument("--procesos", type=int, default=None)
    a = ap.parse_args()
    if a.accion == "g1":
        accion_g1(a.procesos)
    elif a.accion == "g2":
        accion_g2(a.procesos)
    elif a.accion == "g3":
        accion_g3(a.procesos)
    elif a.accion == "guardas":
        accion_guardas(a.procesos)
    elif a.accion == "examen":
        accion_examen(a.procesos)
    elif a.accion == "casos":
        accion_casos(a.procesos)
    elif a.accion == "equivalencia":
        accion_equivalencia(a.procesos, a.conjunto)


if __name__ == "__main__":
    main()
