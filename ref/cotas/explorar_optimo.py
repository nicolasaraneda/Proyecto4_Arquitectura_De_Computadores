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
    txt = "\n".join(L) + "\n"
    open(os.path.join(SALIDA, "optimo_g2.txt"), "w").write(txt)
    print(txt)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("accion", choices=["g1", "g2", "equivalencia"])
    ap.add_argument("--conjunto", default="otras")
    ap.add_argument("--procesos", type=int, default=None)
    a = ap.parse_args()
    if a.accion == "g1":
        accion_g1(a.procesos)
    elif a.accion == "g2":
        accion_g2(a.procesos)
    elif a.accion == "equivalencia":
        accion_equivalencia(a.procesos, a.conjunto)


if __name__ == "__main__":
    main()
