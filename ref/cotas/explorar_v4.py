#!/usr/bin/env python3
"""explorar_v4.py: parte 7 de la sección 14, V4 (candado selectivo con máquina de modos).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Las mismas 12 000 ventanas de las otras acciones, los mismos 200 000 sorteos y los mismos controles
de la parte 3 (explorar_clon.py). Las cinco empresas no se usan. Combinaciones: bases V1, V3 con (b)
y la fase A de V2; motores E0 a E4 (candado_v4.motores); M en {25, 50, 100}; piso L en
{sin piso, 2000, 4000}; ambición sí o no. Comisiones y órdenes de hasta 63 en todo.

Por etapas (pedido de Nicolás del 20/11, después de cortar la corrida completa de 918 combinaciones):
la etapa 1 son 24 combinaciones (bases V1, V3 con (b) y fase A de V2; motores E0, E1, E2 d20 y E3 k5;
M 25, sin piso; ambición sí y no). La simulación va por bloques de ventanas: cada bloque calcula todas
las combinaciones de la etapa sobre sus ventanas (el trabajo común por ventana, clon y trayectorias
de las bases, es el 99 % del costo) y se guarda en su propio archivo apenas termina. Después, cada
combinación se arma, juega sus torneos y se guarda en su propio archivo. Lo que ya existe no se
recalcula. Una línea de avance por bloque y por combinación en build/clon/parte7_etapa<N>.log.

Uso (con export P4_DATOS=~/proyectos/datos_p4):
  python3 ref/cotas/explorar_v4.py --etapa 1  -> docs/mediciones/exploracion/clon_parte7_etapa1.txt
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
import optimo_estrategia as OE  # noqa: E402

MS = (25, 50, 100)
LS = (None, 2000, 4000)
AMB = (False, True)
INF = 10 ** 12
CONTROL_VENTANAS = 120
CONTROL_COMBOS_M = (("E1", None, None), 25, None, False), (("E2", 20, None), 50, 2000, True), \
    (("E3", None, 5), 100, None, False), (("E4", 10, 10), 25, 4000, True), (("E0", None, None), 50, None, True)
V2SPEC = OE.spec("V2", "log", "S2/t")
# Los .pkl que se leen aquí son las cachés locales que escriben estos mismos scripts en build/cotas/.


def bases():
    el = pickle.load(open(os.path.join(XO.CACHE, "elegidas_guardas.pkl"), "rb"))
    return {"V1": OE.spec("V1", "log", "S2/t"), "V3 con (b)": el["V3"], "V2 (fase A)": V2SPEC}


ETAPAS = {
    "1": dict(motores=(("E0", None, None), ("E1", None, None), ("E2", 20, None), ("E3", None, 5)),
              Ms=(25,), Ls=(None,), amb=(False, True)),
    # V4b: fase A libre (candado_v4, fase_a_libre=True). Control obligatorio: E0 igual a la base sola.
    "1b": dict(motores=(("E0", None, None), ("E1", None, None)), Ms=(25, 100), Ls=(None, 2000, 4000), amb=(False,),
               bases=("V1", "V3 con (b)"), v4b=True, candado="copiar", top=2, rivales=("banda 30", "banda 50", "banda 60")),
}
BLOQUE = 250
LOG = [None]


def log(msg):
    linea = f"{time.strftime('%H:%M:%S')} {msg}"
    print(linea, flush=True)
    if LOG[0]:
        with open(LOG[0], "a") as f:
            f.write(linea + "\n")


def combos(nb, et=None):
    import candado_v4 as C4
    if et is None:
        out = [(k, m, M, L, a) for k in range(nb) for m in C4.motores() for M in MS for L in LS for a in AMB]
        control = [(k, ("E0", None, None), INF, None, False) for k in range(nb)]
        control.append((nb - 1, ("E1", None, None), INF, None, True))     # V2 con E1 y sin candado: V2 sola
        return out, control
    else:
        out = [(k, m, M, L, a) for k in range(nb) for m in et["motores"] for M in et["Ms"] for L in et["Ls"]
               for a in et["amb"]]
    control = [(k, ("E0", None, None), INF, None, False) for k in range(nb)]
    control.append((nb - 1, ("E1", None, None), INF, None, True))     # V2 con E1 y sin candado: V2 sola
    return out, control


_G = {}


def _trabajo(ids):
    import candado_v4 as C4
    conj, specs, cmb = _G["conj"], _G["specs"], _G["combos"]
    res = []
    for i in ids:
        o = C4.ventana_v4(conj.ventana(i), specs, V2SPEC, cmb, _G.get("v4b", False), _G.get("candado", "igualar"))
        res.append({c: o[c] for c in cmb} | {"clon": o["clon"]} | {("base", k): o[("base", k)] for k in range(len(specs))})
    return ids, res


def _control(i):
    import candado_v4 as C4
    import ideas
    conj, specs = _G["conj"], _G["specs"]
    w = conj.ventana(i)
    out = []
    lista = _G.get("control_combos") or [(k,) + cm for k in range(len(specs)) for cm in CONTROL_COMBOS_M]
    for k, m, M, L, a in lista:
        s = C4.V4(specs[k], m, M, L, a, _G.get("v4b", False), _G.get("candado", "igualar"))
        W, n, _ = ideas.correr(w, s)
        out.append(((k, m, M, L, a), W, n, s.info()[0], s.info()[1]))
    return i, out


def clave(cx, specs, cmb):
    h = hashlib.sha256(repr((specs, cmb, cx.conj.clave(), E.codigo(), E.CODIGO_EXTRA.get("optima"))).encode())
    for f in ("candado.py", "candado_v4.py"):
        h.update(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f), "rb").read())
    return h.hexdigest()[:16]


def _atomico(obj, ruta):
    tmp = ruta + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(obj, f)
    os.replace(tmp, ruta)


def _bloque(a):
    t = time.perf_counter()
    ids = list(range(a, min(a + BLOQUE, _G["n"])))
    return a, _trabajo(ids)[1], time.perf_counter() - t


def simular_bloques(c, specs, cmb, ctrl, carpeta, procesos):
    """Simula por bloques de BLOQUE ventanas, cada uno a su archivo. Devuelve W, G, O, clon, base y control."""
    import array
    import candado_v4 as C4
    cx = c.cx
    _G["conj"], _G["specs"], _G["combos"], _G["n"] = cx.conj, specs, cmb, c.n
    if cx.conj.ventanas is None:
        cx.conj.cargar_series()
    inicios = list(range(0, c.n, BLOQUE))
    falta = [a for a in inicios if not os.path.exists(os.path.join(carpeta, f"bloque_{a:05d}.pkl"))]
    log(f"simulación: {len(inicios)} bloques de {BLOQUE} ventanas, {len(inicios) - len(falta)} ya guardados, "
        f"{len(cmb)} combinaciones por ventana")
    t0 = time.time()
    if falta:
        with Pool(procesos or os.cpu_count()) as pool:
            for j, (a, res, dt) in enumerate(pool.imap_unordered(_bloque, falta)):
                _atomico(res, os.path.join(carpeta, f"bloque_{a:05d}.pkl"))
                log(f"bloque {a:05d}-{min(a + BLOQUE, c.n) - 1:05d} guardado ({j + 1} de {len(falta)}): "
                    f"{dt:.1f} s de un proceso, {time.time() - t0:.0f} s desde el inicio")
    gi = {g: j for j, g in enumerate(C4.GRUPOS)}
    W = {cm: array.array("i", [0] * c.n) for cm in cmb}
    G = {cm: array.array("b", [0] * c.n) for cm in cmb}
    O = {cm: array.array("h", [0] * c.n) for cm in cmb}
    LW = {cm: array.array("q", [0] * c.n) for cm in cmb}     # patrimonios propio y del clon al cerrar el candado
    LC = {cm: array.array("q", [0] * c.n) for cm in cmb}
    clon = array.array("i", [0] * c.n)
    base = {k: (array.array("i", [0] * c.n), array.array("h", [0] * c.n)) for k in range(len(specs))}
    for a in inicios:
        res = pickle.load(open(os.path.join(carpeta, f"bloque_{a:05d}.pkl"), "rb"))
        for i, o in zip(range(a, a + len(res)), res):
            for cm in cmb:
                Wf, g, n, lk = o[cm]
                W[cm][i], G[cm][i], O[cm][i] = Wf, gi[g], n
                if lk is not None:
                    LW[cm][i], LC[cm][i] = lk
            clon[i] = o["clon"]
            for k in range(len(specs)):
                base[k][0][i], base[k][1][i] = o[("base", k)]
    rc = os.path.join(carpeta, "control.pkl")
    if os.path.exists(rc):
        control = pickle.load(open(rc, "rb"))
        log("control directo: ya guardado")
    else:
        t = time.time()
        _G["control_combos"] = ctrl
        rng = random.Random(f"control-v4-{XC.SEMILLA}")
        with Pool(procesos or os.cpu_count()) as pool:
            control = list(pool.imap_unordered(_control, sorted(rng.sample(list(range(c.n)), CONTROL_VENTANAS))))
        _atomico(control, rc)
        log(f"control directo ({CONTROL_VENTANAS} ventanas, {len(ctrl)} combinaciones, tick a tick): {time.time() - t:.0f} s")
    return dict(W=W, G=G, O=O, LW=LW, LC=LC, clon=clon, base=base, control=control)


def _mano_t(args):
    t = time.perf_counter()
    r = XC._mano(args)
    return r + (time.perf_counter() - t,)


def torneos_por_combinacion(c, cmb, W, b40, carpeta, nombre, procesos):
    """Torneo de cada combinación contra la banda 40, a su archivo apenas termina."""
    met = {}
    tareas = []
    for cm in cmb:
        ruta = os.path.join(carpeta, f"comb_{hashlib.sha256(repr(cm).encode()).hexdigest()[:12]}.pkl")
        if os.path.exists(ruta):
            met[cm] = pickle.load(open(ruta, "rb"))["met"]
            log(f"combinación {nombre(cm)}: ya guardada")
        else:
            tareas.append((cm, [W[cm][i] - b40[i] for i in range(c.n)], "todas"))
    if tareas:
        rutas = {cm: os.path.join(carpeta, f"comb_{hashlib.sha256(repr(cm).encode()).hexdigest()[:12]}.pkl") for cm, _, _ in tareas}
        with Pool(procesos or os.cpu_count()) as pool:
            for cm, m, contrib, dt in pool.imap_unordered(_mano_t, tareas):
                t = time.perf_counter()
                for k in ("g", "p", "d", "m"):
                    m[f"ee_{k}"] = XR.ee_contrib(contrib[k], c.G, True)[0] * (100 if k in ("g", "p") else 1)
                _atomico(dict(combo=cm, nombre=nombre(cm), met=m, W=list(W[cm])), rutas[cm])
                met[cm] = m
                log(f"combinación {nombre(cm)} guardada: torneo {dt:.1f} s, error estándar {time.perf_counter() - t:.1f} s")
    return met


def simular(c, specs, cmb, procesos):
    cx = c.cx
    ruta = os.path.join(XO.CACHE, f"clon_parte7_{clave(cx, specs, cmb)}.pkl")
    if os.path.exists(ruta):
        return pickle.load(open(ruta, "rb"))
    _G["conj"], _G["specs"], _G["combos"] = cx.conj, specs, cmb
    if cx.conj.ventanas is None:
        cx.conj.cargar_series()
    ids = list(range(c.n))
    tr = max(5, c.n // ((procesos or os.cpu_count()) * 8))
    import array
    W = {cm: array.array("i", [0] * c.n) for cm in cmb}
    G = {cm: array.array("b", [0] * c.n) for cm in cmb}
    O = {cm: array.array("h", [0] * c.n) for cm in cmb}
    clon = array.array("i", [0] * c.n)
    base = {k: (array.array("i", [0] * c.n), array.array("h", [0] * c.n)) for k in range(len(specs))}
    import candado_v4 as C4
    gi = {g: j for j, g in enumerate(C4.GRUPOS)}
    with Pool(procesos or os.cpu_count()) as pool:
        for idsr, out in pool.imap_unordered(_trabajo, [ids[a:a + tr] for a in range(0, c.n, tr)]):
            for i, o in zip(idsr, out):
                for cm in cmb:
                    Wf, g, n = o[cm][:3]
                    W[cm][i], G[cm][i], O[cm][i] = Wf, gi[g], n
                clon[i] = o["clon"]
                for k in range(len(specs)):
                    base[k][0][i], base[k][1][i] = o[("base", k)]
        rng = random.Random(f"control-v4-{XC.SEMILLA}")
        control = list(pool.imap_unordered(_control, sorted(rng.sample(ids, CONTROL_VENTANAS))))
    out = dict(W=W, G=G, O=O, clon=clon, base=base, control=control)
    pickle.dump(out, open(ruta, "wb"))
    return out


def fmt(x, d=1):
    return XC.fmt(x, d)


def main():
    import multiprocessing
    multiprocessing.set_start_method("fork", force=True)
    import candado_v4 as C4
    etapa = sys.argv[sys.argv.index("--etapa") + 1] if "--etapa" in sys.argv else None
    et = ETAPAS[etapa] if etapa is not None else None
    suf = f"_etapa{etapa}" if etapa is not None else ""
    procesos = None
    t_ini = time.time()
    c = XC.Ctx(procesos)
    avisos = []
    Rs = XC.rivales(c, avisos)
    Wd = XC.estrategias(c, avisos)
    bd = bases()
    nombres = [k for k in bd if et is None or k in et.get("bases", bd)]
    specs = [bd[k] for k in nombres]
    cmb, control = combos(len(specs), et)
    v4b = bool(et and et.get("v4b"))
    _G["v4b"] = v4b
    _G["candado"] = (et or {}).get("candado", "igualar")
    if v4b:
        control = [cm for cm in control if not (cm[1][0] == "E1")]      # V2 no es base en V4b

    def nombre(cm):
        k, m, M, L, a = cm
        return (f"{nombres[k]}, {C4.nombre_motor(m)}, M {M if M < INF else 'inf'}, L {'sin piso' if L is None else L}"
                f"{', ambición' if a else ''}")

    if etapa is None:
        sim = simular(c, specs, cmb + control, procesos)
        ctrl_n = f"3 bases y {len(CONTROL_COMBOS_M)} combinaciones"
    else:
        carpeta = os.path.join(XO.CACHE, "v4", f"etapa{etapa}_{clave(c.cx, specs, cmb + control + [('v4b', v4b), ('candado', _G['candado'])])}")
        os.makedirs(carpeta, exist_ok=True)
        LOG[0] = os.path.join(E.comun.RAIZ, "build", "clon", f"parte7_etapa{etapa}.log")
        log(f"etapa {etapa}: {len(cmb)} combinaciones más {len(control)} sin candado; carpeta {carpeta}")
        sim = simular_bloques(c, specs, cmb + control, cmb, carpeta, procesos)
        ctrl_n = f"las {len(cmb)} combinaciones de la etapa"
    W, G, O = sim["W"], sim["G"], sim["O"]
    todos = list(range(c.n))
    b40 = Rs["banda 40"]
    caso = c.caso
    iS = [i for i in todos if caso[i] == "S"]
    iB = [i for i in todos if caso[i] == "B"]

    L_ = [f"# V4: candado selectivo con máquina de modos (parte 7{', etapa ' + str(etapa) if etapa else ''})", "",
          f"ref/cotas/explorar_v4.py, commit {XR.commit()}. Otras acciones: {c.n} ventanas; los mismos {XC.SORTEOS} "
          "sorteos de las partes 1 y 3. D = patrimonio propio - patrimonio del clon (banda 40 emulada). Interpretación "
          "y motores en el encabezado de ref/cotas/candado_v4.py.", ""]
    # controles
    L_.append("## Controles\n")
    L_.append(f"- Clon emulado contra la banda 40 de la caché: {sum(1 for i in todos if sim['clon'][i] != b40[i])} "
              f"ventanas distintas de {c.n}.")
    ref = {"V1": Wd["V1"]["W"], "V3 con (b)": Wd["V3 con (b)"]["W"], "V2 (fase A)": Wd["V2"]["W"]}
    for k, nm in enumerate(nombres):
        mal = sum(1 for i in todos if sim["base"][k][0][i] != ref[nm][i])
        L_.append(f"- Base {nm} sola, recorrida con el código actual, contra la caché de la parte 1: {mal} ventanas distintas.")
    for cm in control:
        k = cm[0]
        mal = sum(1 for i in todos if W[cm][i] != ref[nombres[k]][i])
        if nombres[k] == "V2 (fase A)" and cm[1][0] == "E0":
            L_.append(f"- {nombre(cm)} (sin candado) contra V2 sola: {mal} ventanas distintas. No es un control: "
                      "después de la fase A copia al clon, y V2 sola sigue con su política en B, C y D.")
        else:
            L_.append(f"- {nombre(cm)} (sin candado) contra la base sola: {mal} ventanas distintas.")
    mal = 0
    for i, out in sim["control"]:
        for cm, Wr, n, g, *lk in out:
            mal += (Wr != W[cm][i]) or (n != O[cm][i]) or (C4.GRUPOS[G[cm][i]] != g)
            if lk and lk[0] is not None and "LW" in sim:
                mal += tuple(lk[0]) != (sim["LW"][cm][i], sim["LC"][cm][i])
    L_.append(f"- Por eventos contra la referencia directa (`candado_v4.V4` en `ideas.correr`), {CONTROL_VENTANAS} ventanas, "
              f"{ctrl_n}: {mal} diferencias en patrimonio, órdenes o grupo.")
    if v4b:
        # control obligatorio de V4b: con E0, idéntico a la base sola en todas las ventanas
        L_.append("\n### Control obligatorio de V4b: E0 contra la base sola\n")
        L_.append("| Combinación | Ventanas distintas | Distintas por grupo (apuesta / recuperación / sin recuperar / piso / sin desviar) | "
                  "Δ medio en las distintas |")
        L_.append("|---|---|---|---|")
        malos = 0
        for cm in [x for x in cmb if x[1][0] == "E0"] + control:
            k = cm[0]
            dist = [i for i in todos if W[cm][i] != ref[nombres[k]][i]]
            malos += len(dist)
            por = [sum(1 for i in dist if G[cm][i] == gj) for gj in range(len(C4.GRUPOS))]
            dm = (sum(W[cm][i] - ref[nombres[k]][i] for i in dist) / len(dist)) if dist else 0.0
            L_.append(f"| {nombre(cm)} | {len(dist)} | {' / '.join(map(str, por))} | {dm:+.0f} |")
        L_.append("")
        if malos:
            txt = "\n".join(L_) + "\n"
            open(os.path.join(XC.SALIDA, f"clon_parte7{suf}_control.txt"), "w").write(txt)
            log(f"CONTROL DE V4b FALLA: {malos} diferencias (ventana por combinación) con E0; se detiene antes de los torneos")
            print(txt)
            sys.exit(3)
        log("control de V4b: E0 idéntico a la base sola en todas las ventanas")
    L_.append("")

    # torneos contra la banda 40
    XC._T["todas"] = (XC.sorteos(todos, "todas", XC.SORTEOS), c.n)
    if etapa is None:
        tareas = [(("v4",) + cm, [W[cm][i] - b40[i] for i in todos], "todas") for cm in cmb]
    else:
        mv4 = torneos_por_combinacion(c, cmb, W, b40, carpeta, nombre, procesos)
        tareas = []
    ref_V2M25 = _parte3_V2M25(c)
    tareas.append((("ref", "V2 con M 25 (parte 3)"), [ref_V2M25[i] - b40[i] for i in todos], "todas"))
    tareas.append((("ref", "V3 con (b) sin candado"), [Wd["V3 con (b)"]["W"][i] - b40[i] for i in todos], "todas"))
    met = XC.correr_torneos(c, tareas, procesos)
    if etapa is not None:
        met.update({("v4",) + cm: m for cm, m in mv4.items()})

    def d_ee(Wl, idx):
        return XR.delta(c.G, {"W": Wl}, {"W": b40}, idx)

    filas = {}
    for cm in cmb:
        m = met[("v4",) + cm]
        d, ee = d_ee(W[cm], todos)
        filas[cm] = dict(m=m, d=d, ee=ee, o=sum(O[cm]) / c.n)
    elegibles = [cm for cm in cmb if filas[cm]["d"] >= 0]
    orden = sorted(elegibles, key=lambda cm: -(filas[cm]["m"]["g"] - filas[cm]["m"]["p"]))
    top10 = orden[:10]

    def fila_torneo(nm, m, d, ee, o):
        return (f"| {nm} | {XC.fmt_ee(d, ee, 0, True)} | {fmt(m['g'])} | {fmt(m['e'])} | {fmt(m['p'])} | "
                f"{fmt(m['g'] - m['p'])} | {m['d']:.0f} | {m['m']:+.0f} | {m['p5']:+.0f} | {m['peor']:+.0f} | {fmt(o)} |")

    CAB = ("| Combinación | Δ por ronda (ee) | Gana % | Empata % | Pierde % | Gana - pierde | Déficit | Media del torneo | p5 | Peor | Órdenes |\n"
           "|---|---|---|---|---|---|---|---|---|---|---|")
    L_.append(f"## Las 10 primeras por (gana % - pierde %) entre las {len(elegibles)} de {len(cmb)} combinaciones con "
              "diferencia media >= 0, contra la banda 40\n")
    L_.append(CAB)
    for cm in top10:
        f = filas[cm]
        L_.append(fila_torneo(nombre(cm), f["m"], f["d"], f["ee"], f["o"]))
    for nm, Wl, o in (("V2 con M 25, sin tope (parte 3)", ref_V2M25, None), ("V3 con (b) sin candado", Wd["V3 con (b)"]["W"], Wd["V3 con (b)"]["n"])):
        m = met[("ref", "V2 con M 25 (parte 3)" if "V2" in nm else "V3 con (b) sin candado")]
        d, ee = d_ee(Wl, todos)
        oo = (sum(o) / c.n) if o is not None else float("nan")
        L_.append(fila_torneo(f"referencia: {nm}", m, d, ee, oo))

    # por caso y grupos de las 10 primeras
    def grupos_caso(cm, idx):
        celdas = []
        for gj, g in enumerate(C4.GRUPOS):
            sel = [i for i in idx if G[cm][i] == gj]
            if sel:
                celdas.append(f"{fmt(100 * len(sel) / len(idx))} ({sum(W[cm][i] - b40[i] for i in sel) / len(sel):+.0f})")
            else:
                celdas.append("0,0")
        return celdas

    L_.append("\n## Por ronda y por caso, las 10 primeras\n")
    L_.append("Grupos: candado tras apuesta ganada, candado tras recuperación, sin recuperar, piso, sin desviar "
              "(sin apuesta y sin ambición). Porcentaje de las rondas del caso y, entre paréntesis, la D final media del grupo.\n")
    L_.append("| Combinación | Caso | Δ (ee) | Candado tras apuesta | Candado tras recuperación | Sin recuperar | Piso | Sin desviar |")
    L_.append("|---|---|---|---|---|---|---|---|")
    for cm in top10:
        for cs, idx in (("S", iS), ("B", iB)):
            d, ee = d_ee(W[cm], idx)
            L_.append(f"| {nombre(cm)} | {cs} | {XC.fmt_ee(d, ee, 0, True)} | " + " | ".join(grupos_caso(cm, idx)) + " |")

    # top 3 contra otras bandas y memoria
    top3 = orden[:(et or {}).get("top", 3)]
    Rs_top = {rv: Wr for rv, Wr in Rs.items() if et is None or rv in et.get("rivales", Rs)}
    tareas = []
    for cm in top3:
        for rv, Wr in Rs_top.items():
            tareas.append((("r",) + cm + (rv,), [W[cm][i] - Wr[i] for i in todos], "todas"))
            tareas.append((("mem",) + cm + (rv,), ("mem", (W[cm], b40, Wr, cm[2])), "todas"))
    met2 = XC.correr_torneos(c, tareas, procesos)
    L_.append(f"\n## Las {len(top3)} primeras con el rival real en otra banda (el emulado sigue siendo la banda 40)\n")
    L_.append("| Combinación | Rival real | Δ por ronda (ee) | Gana % | Empata % | Pierde % | Gana - pierde | Déficit | p5 | Peor |")
    L_.append("|---|---|---|---|---|---|---|---|---|---|")
    for cm in top3:
        for rv, Wr in Rs_top.items():
            m = met2[("r",) + cm + (rv,)]
            d, ee = XR.delta(c.G, {"W": W[cm]}, {"W": Wr}, todos)
            L_.append(f"| {nombre(cm)} | {rv} | {XC.fmt_ee(d, ee, 0, True)} | {fmt(m['g'])} | {fmt(m['e'])} | {fmt(m['p'])} | "
                      f"{fmt(m['g'] - m['p'])} | {m['d']:.0f} | {m['p5']:+.0f} | {m['peor']:+.0f} |")
    L_.append(f"\n## Dato aparte: memoria entre rondas para las {len(top3)} primeras\n")
    L_.append("En el orden del sorteo: si la D acumulada contra el clon emulado ya es >= M al empezar una ronda, esa ronda "
              "copia al clon entera.\n")
    L_.append("| Combinación | Rival real | Gana % | Empata % | Pierde % | Gana - pierde | Déficit | Media del torneo | p5 | Peor |")
    L_.append("|---|---|---|---|---|---|---|---|---|---|")
    for cm in top3:
        for rv in Rs_top:
            m = met2[("mem",) + cm + (rv,)]
            L_.append(f"| {nombre(cm)} | {rv} | {fmt(m['g'])} | {fmt(m['e'])} | {fmt(m['p'])} | {fmt(m['g'] - m['p'])} | "
                      f"{m['d']:.0f} | {m['m']:+.0f} | {m['p5']:+.0f} | {m['peor']:+.0f} |")

    # todas las combinaciones
    L_.append(f"\n## Todas las combinaciones ({len(cmb)}), contra la banda 40\n")
    L_.append("| Combinación | Δ (ee) | Δ S (ee) | Δ B (ee) | Gana % | Empata % | Pierde % | Déficit | Media | p5 | Peor | Órdenes | "
              "S: apuesta / recuperación / sin recuperar / piso / sin desviar | B: ídem |")
    L_.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cm in cmb:
        f = filas[cm]
        m = f["m"]
        dS, eS = d_ee(W[cm], iS)
        dB, eB = d_ee(W[cm], iB)
        L_.append(f"| {nombre(cm)} | {XC.fmt_ee(f['d'], f['ee'], 0, True)} | {XC.fmt_ee(dS, eS, 0, True)} | "
                  f"{XC.fmt_ee(dB, eB, 0, True)} | {fmt(m['g'])} | {fmt(m['e'])} | {fmt(m['p'])} | {m['d']:.0f} | "
                  f"{m['m']:+.0f} | {m['p5']:+.0f} | {m['peor']:+.0f} | {fmt(f['o'])} | "
                  + " / ".join(grupos_caso(cm, iS)) + " | " + " / ".join(grupos_caso(cm, iB)) + " |")

    if "LW" in sim:
        L_.append(f"\n## Rondas en candado ({len(cmb)} combinaciones)\n")
        L_.append("Candado = grupos apuesta y recuperación. Razón = patrimonio propio / patrimonio del clon emulado, "
                  "al cerrar el candado (al precio de ese tick) y al final de la ronda. D = propio - clon al final.\n")
        L_.append("| Combinación | En candado (% de las rondas) | En S | En B | Razón al cerrar, media (mín) | "
                  "Razón al final, media (mín) | Terminan con D < 0 (% de las en candado) | D final media en candado |")
        L_.append("|---|---|---|---|---|---|---|---|")
        clw = sim["clon"]
        for cm in cmb:
            idx = [i for i in todos if G[cm][i] in (0, 1)]
            if not idx:
                L_.append(f"| {nombre(cm)} | 0 | 0 | 0 | - | - | - | - |")
                continue
            rl = [sim["LW"][cm][i] / sim["LC"][cm][i] for i in idx]
            rf = [W[cm][i] / clw[i] for i in idx]
            neg = sum(1 for i in idx if W[cm][i] < clw[i])
            nS = sum(1 for i in idx if caso[i] == "S")
            L_.append(f"| {nombre(cm)} | {len(idx)} ({fmt(100 * len(idx) / c.n)}) | {nS} | {len(idx) - nS} | "
                      f"{sum(rl) / len(rl):.4f} ({min(rl):.4f}) | {sum(rf) / len(rf):.4f} ({min(rf):.4f}) | "
                      f"{neg} ({fmt(100 * neg / len(idx))}) | {sum(W[cm][i] - clw[i] for i in idx) / len(idx):+.0f} |")

    txt = "\n".join(L_) + "\n"
    open(os.path.join(XC.SALIDA, f"clon_parte7{suf}.txt"), "w").write(txt)
    pickle.dump(dict(top10=top10, top3=top3, filas={cm: (filas[cm]["d"], filas[cm]["m"]) for cm in cmb}),
                open(os.path.join(XO.CACHE, f"clon_parte7{suf}_resumen.pkl"), "wb"))
    print(txt)


def _parte3_V2M25(c):
    """V2 con M 25 y sin tope de la parte 3, desde su caché."""
    specs3 = list(XC.bases_candado().values())
    ruta = os.path.join(XO.CACHE, f"clon_parte3_{XC.clave_parte3(c.cx, specs3)}.pkl")
    if not os.path.exists(ruta):
        raise SystemExit(f"falta la caché de la parte 3 ({os.path.basename(ruta)})")
    res = pickle.load(open(ruta, "rb"))["res"]
    return [res[i][(0, 25, None)][0] for i in range(c.n)]


if __name__ == "__main__":
    main()
