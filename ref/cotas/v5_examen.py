#!/usr/bin/env python3
"""v5_examen.py: examen de C1 contra la banda 40 sola en las cinco empresas (docs/exploracion_ideas.md, 15.14).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Usa el código congelado de V5 sin cambiarlo (v5.py y explorar_v5.py): el mismo precálculo, la misma
simulación tick a tick, el mismo índice y los mismos errores estándar. Lo propio de este guion es el
conjunto de ventanas, los subconjuntos y el informe. No ajusta ni elige nada.

Conjunto: la muestra estratificada vigente de las cinco empresas (explorar_regimen.cargar("cinco"):
240 ventanas por empresa y año de inicio, 2022 a 2024, semilla 18, 3600 ventanas). Caché aparte
(build/cotas/v5_cinco), porque la clave de las variantes de explorar_v5 no incluye el conjunto.

Estrategias: C1 (explorar_v5.FINALISTAS) y la banda 40 sola. Rivales y pesos: v5.RIVALES y v5.PESOS.
Sorteos: explorar_clon.sorteos, 200 000 torneos de 3 rondas en todas las ventanas y 60 000 dentro de
cada subconjunto (caso S, caso B, año de inicio y empresa).

Criterio fijado antes de correr, sobre las cifras ponderadas de todas las ventanas:
  1. g de C1 >= g de la banda 40 + 20 puntos
  2. nd de C1 >= nd de la banda 40 - 8 puntos

Uso (con export P4_DATOS=~/proyectos/datos_p4, desde la raíz de la rama):
  python3 ref/cotas/v5_examen.py --ensayo   el mismo guion sobre las otras acciones: debe repetir
                                            v5_finalistas.txt; escribe en build/clon/ y no en docs/
  python3 ref/cotas/v5_examen.py            el examen (una sola vez): docs/mediciones/exploracion/c1_examen.txt
"""
import argparse
import multiprocessing
import os
import pickle
import random
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorar_clon as XC     # noqa: E402
import explorar_ideas as E     # noqa: E402
import explorar_regimen as XR  # noqa: E402
import explorar_v5 as X        # noqa: E402
import v5 as V                 # noqa: E402

C1 = list(X.FINALISTAS)[0]
B40 = "banda 40 sola"
APAGADO = "todo apagado"
VARIANTES = {C1: X.FINALISTAS[C1], APAGADO: (X.SIN_A, dict(motor="E0", M=100))}
N_SUB = 60000
N_CONTROL = 120
UMBRAL_G, UMBRAL_ND = 20.0, 8.0
POND = "ponderado"
# Los .pkl que se leen aquí son las cachés locales que escriben estos mismos scripts en build/cotas/.


class Ctx:
    """Lo que usan explorar_v5.precalculo, evaluar, indices y dif, sobre el conjunto pedido."""

    def __init__(self, nombre):
        self.nombre = nombre
        self.D = XR.cargar(nombre)
        self.n = len(self.D.filas)
        self.G = XR.grupos_de(self.D)
        self.anio = [f[2] for f in self.D.filas]
        self.emp = [f[0] for f in self.D.filas]
        self.grupo = list(self.D.grupo)
        self.caso = [XC.caso_de(v) for v in self.D.ventanas]
        X._G["vent"] = self.D.ventanas
        os.makedirs(X.CACHE, exist_ok=True)


def subconjuntos(c):
    """[(clave, título, índices, sorteos)]. Las claves 'todas', año y grupo son las de explorar_v5."""
    todos = list(range(c.n))
    subs = [("todas", "todas las ventanas", todos, XC.SORTEOS)]
    for cs in ("S", "B"):
        subs.append((f"caso {cs}", f"caso {cs}", [i for i in todos if c.caso[i] == cs], N_SUB))
    for a in sorted(set(c.anio)):
        subs.append((str(a), f"inicio en {a}", [i for i in todos if c.anio[i] == a], N_SUB))
    if c.nombre == "cinco":
        for e in E.EMPRESAS:
            subs.append((e, e, [i for i in todos if c.emp[i] == e], N_SUB))
    else:
        for g in ("tec", "fin", "sal", "con", "ind"):
            subs.append((g, f"grupo {g}", [i for i in todos if c.grupo[i] == g], N_SUB))
    X._G["sorteos"] = {k: (XC.sorteos(idx, k, n), len(idx)) for k, _, idx, n in subs}
    return subs


# --- controles -----------------------------------------------------------------------------------

def _ref_c1(i):
    import ideas
    W, n, _ = ideas.correr(X._G["vent"][i], V.V5Ref(**X.REF_ARGS["C1"]))
    return i, (W, n)


def controles(c, res, WR):
    """Devuelve (líneas, cantidad de diferencias). Los mismos controles de explorar_v5.etapa_finalistas."""
    L = []
    mal = sum(1 for i in range(c.n) if res[APAGADO]["W"][i] != WR["b40"][i])
    L.append(f"- Todo apagado (sin fase A, sin motor): patrimonio distinto al de la banda 40 en {mal} ventanas de {c.n}.")
    rng = random.Random("v5-control")
    ids = sorted(rng.sample(range(c.n), N_CONTROL))
    with Pool(os.cpu_count()) as pool:
        byt = sum(pool.imap_unordered(X._apagado, ids))
        refs = dict(pool.imap_unordered(_ref_c1, ids))
    L.append(f"- Todo apagado, byte a byte contra la banda 40 desde el primer extremo en {N_CONTROL} ventanas: {byt} bytes distintos.")
    malr = sum(1 for i in ids if refs[i] != (res[C1]["W"][i], res[C1]["n"][i]))
    L.append(f"- C1: v5.fase_a + v5.post contra la segunda implementación (`v5.V5Ref` en `ideas.correr`, tick a tick) en "
             f"{N_CONTROL} ventanas: {malr} diferencias en patrimonio u órdenes.")
    total = mal + byt + malr
    if c.nombre == "cinco":      # dato de respaldo: los rivales en Python contra la caché en C de la misma muestra
        conj = c.D.conj(XR.reales.carpeta_datos())
        ruta = os.path.join(E.CACHE, f"rivales_{conj.clave()}.pkl")
        if os.path.exists(ruta):
            R = pickle.load(open(ruta, "rb"))
            for r, col in (("b40", "espera_banda40"), ("b60", "espera_banda60"), ("f5", E.RIVAL_TESLA)):
                if col in R:
                    d = sum(1 for i in range(c.n) if WR[r][i] != R[col][i])
                    total += d
                    L.append(f"- Rival {r} en Python (`v5.rival`) contra `{col}` de la caché en C de la misma muestra: "
                             f"{d} ventanas distintas de {c.n}.")
        else:
            L.append("- La caché en C de los rivales de esta muestra no está: no se comparó `v5.rival` contra C.")
    return L, total


# --- cifras que el índice de explorar_v5 no entrega ----------------------------------------------

def _extra(args):
    """Por rival: déficit con su contribución por ventana (para el ee). Ponderado: p5 y peor torneo de la
    mezcla de rivales (cada torneo contra el rival r pesa PESOS[r])."""
    nombre, W, sub = args
    tr, n_idx = X._G["sorteos"][sub]
    WR = X._G["WR"]
    NT, n = len(tr), len(W)
    out, pares = {}, []
    for r in V.RIVALES:
        Wr = WR[r]
        x = [W[i] - Wr[i] for i in range(n)]
        S = [x[a] + x[b] + x[c_] for a, b, c_ in tr]
        dfc = [-s / 3.0 if s < 0 else 0.0 for s in S]
        out[r] = dict(d=sum(dfc) / NT, c_d=X._contrib(dfc, tr, n, n_idx))
        pw = V.PESOS[r]
        pares.extend((s, pw, r) for s in S)
    pares.sort(key=lambda t: t[0])
    acum, p5 = 0.0, pares[-1][0]
    for s, pw, _ in pares:
        acum += pw
        if acum >= 0.05 * NT:
            p5 = s
            break
    out[POND] = dict(p5=p5 / 3.0, peor=pares[0][0] / 3.0, peor_rival=pares[0][2])
    return nombre, sub, out


def extras(Ws, claves):
    tareas = [(nm, W, sub) for nm, W in Ws.items() for sub in claves]
    out = {}
    with Pool(os.cpu_count()) as pool:
        for nm, sub, o in pool.imap_unordered(_extra, tareas):
            out[(nm, sub)] = o
    return out


# --- informe -------------------------------------------------------------------------------------

def z(d, e, dec=1):
    return f"{d:+.{dec}f} ({e:.{dec}f})".replace(".", ",")


def pe(x, e, dec=1):
    return f"{x:.{dec}f} ({e:.{dec}f})".replace(".", ",")


def ee(c, contrib):
    return XR.ee_contrib(contrib, c.G, True)[0]


def cifras(c, ind, ext, nm, sub):
    """{rival o 'ponderado': dict(m, ee_m, nd, ee_nd, g, ee_g, d, ee_d, p5, peor)} de una estrategia."""
    met, con = ind[(nm, sub)]
    ex = ext[(nm, sub)]
    out = {}
    for r in V.RIVALES:
        m = met[r]
        assert abs(m["d"] - ex[r]["d"]) < 1e-6, (nm, sub, r, m["d"], ex[r]["d"])
        out[r] = dict(m=m["m"], ee_m=m["ee_m"], nd=m["nd"], ee_nd=m["ee_nd"], g=m["g"], ee_g=m["ee_g"],
                      d=m["d"], ee_d=ee(c, ex[r]["c_d"]), p5=m["p5"], peor=m["peor"])
    n = len(con["nd"])
    cm = [sum(V.PESOS[r] * con[r][2][i] for r in V.RIVALES) for i in range(n)]
    out[POND] = dict(m=sum(V.PESOS[r] * met[r]["m"] for r in V.RIVALES), ee_m=ee(c, cm), nd=met["nd"], ee_nd=met["ee_nd"],
                     g=met["g"], ee_g=met["ee_g"], d=met["dp"], ee_d=met["ee_dp"], p5=ex[POND]["p5"], peor=ex[POND]["peor"],
                     peor_rival=ex[POND]["peor_rival"])
    return out


def pareadas(c, ind, ext, sub):
    """C1 menos la banda 40 sola, pareada: {rival o 'ponderado': dict(nd, ee_nd, g, ee_g, d, ee_d)} y (Δ media, ee)."""
    ma, ca = ind[("C1", sub)]
    mb, cb = ind[(B40, sub)]
    xa, xb = ext[("C1", sub)], ext[(B40, sub)]
    out = {}
    for r in V.RIVALES:
        out[r] = dict(nd=ma[r]["nd"] - mb[r]["nd"], ee_nd=100 * ee(c, [x - y for x, y in zip(ca[r][0], cb[r][0])]),
                      g=ma[r]["g"] - mb[r]["g"], ee_g=100 * ee(c, [x - y for x, y in zip(ca[r][1], cb[r][1])]),
                      d=ma[r]["d"] - mb[r]["d"], ee_d=ee(c, [x - y for x, y in zip(xa[r]["c_d"], xb[r]["c_d"])]))
    dn, en, dg, eg = X.dif(c, ind, "C1", B40, sub)
    out[POND] = dict(nd=dn, ee_nd=en, g=dg, ee_g=eg, d=ma["dp"] - mb["dp"], ee_d=ee(c, [x - y for x, y in zip(ca["dp"], cb["dp"])]))
    r0 = V.RIVALES[0]       # la diferencia media entre las dos estrategias no depende del rival
    dm = (ma[r0]["m"] - mb[r0]["m"], ee(c, [x - y for x, y in zip(ca[r0][2], cb[r0][2])]))
    return out, dm


def tabla_detalle(L, c, ind, ext, sub):
    L.append("| Estrategia | Rival | Peso | Δ media por ronda (ee) | nd % (ee) | g % (ee) | Déficit (ee) | p5 | Peor |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for nm in (B40, "C1"):
        cf = cifras(c, ind, ext, nm, sub)
        for r in list(V.RIVALES) + [POND]:
            m = cf[r]
            peso = f"{V.PESOS[r]:.2f}".replace(".", ",") if r in V.PESOS else "1,00"
            L.append(f"| {nm} | {r} | {peso} | {z(m['m'], m['ee_m'], 0)} | {pe(m['nd'], m['ee_nd'])} | {pe(m['g'], m['ee_g'])} | "
                     f"{pe(m['d'], m['ee_d'], 0)} | {m['p5']:+.0f} | {m['peor']:+.0f} |")
    par, dm = pareadas(c, ind, ext, sub)
    L.append(f"\nC1 menos la banda 40 sola, pareada. Diferencia media por ronda (la misma contra cualquier rival): {z(dm[0], dm[1], 0)}.\n")
    L.append("| Rival | Δnd (ee) | Δg (ee) | Δ déficit (ee) |")
    L.append("|---|---|---|---|")
    for r in list(V.RIVALES) + [POND]:
        m = par[r]
        L.append(f"| {r} | {z(m['nd'], m['ee_nd'])} | {z(m['g'], m['ee_g'])} | {z(m['d'], m['ee_d'], 0)} |")


def tabla_rondas(L, c, res, WR, subs):
    """Por ronda (una ventana), sin torneos: C1 contra la banda 40."""
    L.append("| Subconjunto | Ventanas | Caso S % | Banda 40: media | C1: media | Δ por ronda (ee) | C1 arriba / igual / abajo % | "
             "Banda 40: peor | C1: peor | Órdenes de C1 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    Wc, Wb = res[C1]["W"], WR["b40"]
    for k, tit, idx, _ in subs:
        n = len(idx)
        dm, e = XR.delta(c.G, {"W": Wc}, {"W": Wb}, idx)
        ar = sum(1 for i in idx if Wc[i] > Wb[i])
        ig = sum(1 for i in idx if Wc[i] == Wb[i])
        L.append(f"| {tit} | {n} | {X.fmt(100 * sum(1 for i in idx if c.caso[i] == 'S') / n)} | {sum(Wb[i] for i in idx) / n:.0f} | "
                 f"{sum(Wc[i] for i in idx) / n:.0f} | {z(dm, e, 0)} | {X.fmt(100 * ar / n)} / {X.fmt(100 * ig / n)} / "
                 f"{X.fmt(100 * (n - ar - ig) / n)} | {min(Wb[i] for i in idx)} | {min(Wc[i] for i in idx)} | "
                 f"{X.fmt(sum(res[C1]['n'][i] for i in idx) / n)} |")


def tabla_candado(L, c, res):
    L.append("| Caso | Ventanas | Candado tras apuesta % (D media) | Candado tras el motor % (D media) | Sin recuperar % (D media) | "
             "Sin desviar % | Rondas en candado que terminan con D < 0 % |")
    L.append("|---|---|---|---|---|---|---|")
    r = res[C1]
    for cs in ("S", "B"):
        idx = [i for i in range(c.n) if c.caso[i] == cs]
        cel = []
        for g in ("apuesta", "recuperacion", "sin_recuperar"):
            sel = [i for i in idx if r["g"][i] == g]
            cel.append(f"{X.fmt(100 * len(sel) / len(idx))} ({(sum(r['D'][i] for i in sel) / len(sel)) if sel else 0:+.0f})")
        sd = sum(1 for i in idx if r["g"][i] == "sin_desviar")
        lock = [i for i in idx if r["g"][i] in ("apuesta", "recuperacion")]
        neg = sum(1 for i in lock if r["D"][i] < 0)
        L.append(f"| {cs} | {len(idx)} | " + " | ".join(cel) + f" | {X.fmt(100 * sd / len(idx))} | "
                 f"{X.fmt(100 * neg / len(lock)) if lock else '-'} |")


def criterio(L, c, ind, ext):
    cb, cc = cifras(c, ind, ext, B40, "todas")[POND], cifras(c, ind, ext, "C1", "todas")[POND]
    par = pareadas(c, ind, ext, "todas")[0][POND]
    p1 = cc["g"] >= cb["g"] + UMBRAL_G
    p2 = cc["nd"] >= cb["nd"] - UMBRAL_ND
    L.append("Cifras ponderadas, todas las ventanas. Banda 40 sola: nd "
             f"{pe(cb['nd'], cb['ee_nd'])}, g {pe(cb['g'], cb['ee_g'])}. C1: nd {pe(cc['nd'], cc['ee_nd'])}, g {pe(cc['g'], cc['ee_g'])}.\n")
    m1 = f"{par['g'] - UMBRAL_G:+.1f}".replace(".", ",")
    m2 = f"{par['nd'] + UMBRAL_ND:+.1f}".replace(".", ",")
    L.append(f"1. g de C1 >= g de la banda 40 + 20 puntos: {X.fmt(cc['g'])} contra {X.fmt(cb['g'])} + 20 = {X.fmt(cb['g'] + UMBRAL_G)}. "
             f"Diferencia pareada {z(par['g'], par['ee_g'])}; margen sobre el umbral {m1}. **{'Se cumple' if p1 else 'No se cumple'}.**")
    L.append(f"2. nd de C1 >= nd de la banda 40 - 8 puntos: {X.fmt(cc['nd'])} contra {X.fmt(cb['nd'])} - 8 = {X.fmt(cb['nd'] - UMBRAL_ND)}. "
             f"Diferencia pareada {z(par['nd'], par['ee_nd'])}; margen sobre el umbral {m2}. **{'Se cumple' if p2 else 'No se cumple'}.**")
    L.append("")
    if p1 and p2:
        L.append("**Resultado: C1 cumple los dos puntos del criterio.**")
    else:
        L.append("**Resultado: C1 no cumple el criterio. Según lo fijado, compite la banda 40 sola.**")
    return p1, p2


def informe(c, subs, res, WR, ind, ext, Lc, ensayo):
    conj = ("las otras acciones (ensayo del guion, no es el examen)" if ensayo else
            "las cinco empresas (Meta, Apple, Netflix, AMD y Tesla; ventanas que empiezan en 2022, 2023 y 2024)")
    G = c.G
    L = ["# Examen de C1 contra la banda 40 sola" + (" (ENSAYO en las otras acciones)" if ensayo else " en las cinco empresas"), "",
         f"ref/cotas/v5_examen.py{' --ensayo' if ensayo else ''}, commit {XR.commit()} (código de V5: {X.codigo()}). Conjunto: {conj}; "
         f"{c.n} ventanas de 20 000 ticks" + ("" if ensayo else ", la muestra estratificada vigente (240 por empresa y año de inicio, semilla 18)")
         + ". " + ("" if ensayo else "Una sola corrida, con el código congelado de V5; no se ajustó ni se eligió nada con estos datos. "
                   "**Es la tercera mirada a las cinco empresas** (la primera fue el examen del módulo A, sección 12, y la segunda el de "
                   "la política óptima, sección 13). ")
         + f"Torneos de 3 rondas mano a mano: {XC.SORTEOS} sorteos en todas las ventanas y {N_SUB} dentro de cada subconjunto.", "",
         "Estrategias: **C1** (apuesta en la fase A solo con probabilidad >= 0,95 de que el 255 llegue antes que el 100, motor V2 comprimido "
         "de 8 tramos desde el primer extremo, candado copiar con M 100) y **la banda 40 sola**. Nada más.", "",
         "Rivales y pesos: " + ", ".join(f"{r} {V.PESOS[r]:.2f}".replace(".", ",") for r in V.RIVALES)
         + " (ext: extremos puros; f5: regla de Fila 5; b30, b50, b60 y b40: bandas 30, 50, 60 y 40 exacta).", "",
         "Cifras por torneo: **nd** = % en que no queda debajo (promedio propio menos promedio del rival mayor que -10); **g** = % que gana "
         "sola (diferencia de 10 o más); **Δ media** = diferencia media de patrimonio por ronda; **déficit** = media de max(0, promedio del "
         "rival menos promedio propio); **p5** y **peor** = percentil 5 y mínimo de la diferencia de promedio. Fila `ponderado`: promedio con "
         "los pesos (nd, g, Δ media y déficit); su p5 y su peor son los de la mezcla de rivales (cada torneo contra el rival r pesa su peso).", "",
         "Errores estándar (entre paréntesis): proyección de Hoeffding por ventana con los mismos sorteos, agrupada por fecha y empresa "
         "(`explorar_regimen.ee_contrib`: el mayor entre bloques de 20 días, de 60 días y dos sentidos, fecha y empresa). Las diferencias "
         f"entre C1 y la banda 40 son pareadas. Grupos en este conjunto: {len(set(G['b20']))} bloques de 20 días, {len(set(G['b60']))} de "
         f"60 días y {len(set(G['emp']))} empresas" + ("." if ensayo else ": con tan pocos grupos el ee es aproximado, y dentro de una sola "
                                                        "empresa solo agrupa por fecha."), ""]
    L.append("## Controles (antes de mirar el índice)\n")
    L += Lc
    L.append("\n## Criterio fijado de antemano\n")
    p = criterio(L, c, ind, ext)
    L.append("\n## Contra cada rival y ponderado, todas las ventanas\n")
    tabla_detalle(L, c, ind, ext, "todas")
    L.append("\n## Resumen ponderado por caso, por año de inicio y por " + ("grupo" if ensayo else "empresa") + "\n")
    L.append("Los torneos de cada fila se sortean dentro del subconjunto (las tres rondas del mismo caso, año o empresa).\n")
    L.append("| Subconjunto | Ventanas | Banda 40: nd (ee) | Banda 40: g (ee) | C1: nd (ee) | C1: g (ee) | Δnd (ee) | Δg (ee) | "
             "Banda 40: Δ media / déficit / p5 / peor | C1: Δ media / déficit / p5 / peor | Punto 1 | Punto 2 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k, tit, idx, _ in subs:
        cb, cc = cifras(c, ind, ext, B40, k)[POND], cifras(c, ind, ext, "C1", k)[POND]
        par = pareadas(c, ind, ext, k)[0][POND]

        def cola(m):
            return f"{z(m['m'], m['ee_m'], 0)} / {pe(m['d'], m['ee_d'], 0)} / {m['p5']:+.0f} / {m['peor']:+.0f}"
        L.append(f"| {tit} | {len(idx)} | {pe(cb['nd'], cb['ee_nd'])} | {pe(cb['g'], cb['ee_g'])} | {pe(cc['nd'], cc['ee_nd'])} | "
                 f"{pe(cc['g'], cc['ee_g'])} | {z(par['nd'], par['ee_nd'])} | {z(par['g'], par['ee_g'])} | {cola(cb)} | {cola(cc)} | "
                 f"{'sí' if par['g'] >= UMBRAL_G else 'no'} | {'sí' if par['nd'] >= -UMBRAL_ND else 'no'} |")
    L.append("\nLas columnas Punto 1 y Punto 2 aplican los mismos umbrales a cada subconjunto solo como lectura: el criterio se evalúa en "
             "todas las ventanas.")
    L.append("\n## Por ronda (una ventana, sin torneos): C1 contra la banda 40\n")
    tabla_rondas(L, c, res, WR, subs)
    L.append("\nMecánica de C1 por caso (S: el 100 llega primero; B: el 255):\n")
    tabla_candado(L, c, res)
    for k, tit, idx, _ in subs[1:]:
        L.append(f"\n## Contra cada rival y ponderado: {tit} ({len(idx)} ventanas)\n")
        tabla_detalle(L, c, ind, ext, k)
    return "\n".join(L) + "\n", p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensayo", action="store_true", help="corre el guion sobre las otras acciones (no es el examen)")
    a = ap.parse_args()
    multiprocessing.set_start_method("fork", force=True)
    nombre = "otras" if a.ensayo else "cinco"
    if not a.ensayo:
        X.CACHE = os.path.join(E.comun.BUILD, "v5_cinco")
    X.LOG[0] = os.path.join(E.comun.RAIZ, "build", "clon", f"c1_examen{'_ensayo' if a.ensayo else ''}.log")
    os.makedirs(os.path.dirname(X.LOG[0]), exist_ok=True)
    t0 = time.time()
    c = Ctx(nombre)
    X.log(f"examen de C1: conjunto {nombre}, {c.n} ventanas, código de V5 {X.codigo()}")
    pre, WR = X.precalculo(c)
    X._G["WR"] = WR
    for j in range(8):
        V.tabla_pA(j)           # antes del fork: los procesos comparten las tablas
    subs = subconjuntos(c)
    res = X.evaluar(c, VARIANTES, "examen")
    Lc, total = controles(c, res, WR)
    X.log("controles:\n" + "\n".join(Lc))
    if total:
        raise SystemExit("CONTROL DISTINTO DE CERO: se detiene sin calcular el índice")
    Ws = {B40: WR["b40"], "C1": res[C1]["W"]}
    claves = [k for k, _, _, _ in subs]
    ind = X.indices(c, Ws, claves, detalle=True)
    ext = extras(Ws, claves)
    txt, p = informe(c, subs, res, WR, ind, ext, Lc, a.ensayo)
    ruta = (os.path.join(E.comun.RAIZ, "build", "clon", "c1_examen_ensayo.txt") if a.ensayo else
            os.path.join(E.SALIDA, "c1_examen.txt"))
    open(ruta, "w").write(txt)
    print(txt)
    X.log(f"examen de C1: listo en {time.time() - t0:.0f} s, salida en {ruta}; punto 1 {'sí' if p[0] else 'no'}, punto 2 {'sí' if p[1] else 'no'}")


if __name__ == "__main__":
    main()
