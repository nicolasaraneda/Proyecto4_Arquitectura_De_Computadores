#!/usr/bin/env python3
"""explorar_ideas2.py: segunda tanda de docs/exploracion_ideas.md (pedido del 19/11, sección 9).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Mismo protocolo que explorar_ideas.py (muestra estratificada con semilla 18, ajuste y validación
por años y por empresas, torneo de 3 rondas) y la misma caché.

  idea 13 (la 11 del pedido): niveles de la banda según el orden de los extremos.
  idea 14 (la 12 del pedido): reloj de día de mercado.

Uso (con export P4_DATOS=~/proyectos/datos_p4):
  python3 ref/cotas/explorar_ideas2.py filtro13 --semilla 18   -> filtro13.txt
  python3 ref/cotas/explorar_ideas2.py idea13 --semilla 18     -> idea13.txt, idea13.json (si pasa el filtro)
  python3 ref/cotas/explorar_ideas2.py filtro14 --semilla 18   -> filtro14.txt
  python3 ref/cotas/explorar_ideas2.py idea14 --semilla 18     -> idea14.txt, idea14.json (si pasa el filtro)
  python3 ref/cotas/explorar_ideas2.py primera --semilla 18    -> primera.txt
"""
import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorar_ideas as E  # noqa: E402
import ideas_reloj as IR    # noqa: E402
import reales               # noqa: E402

_cod = hashlib.sha256(open(os.path.abspath(IR.__file__), "rb").read()).hexdigest()[:16]
for _t in ("orden", "reloj"):
    E.CODIGO_EXTRA[_t] = _cod

COMPRAS = (120, 130, 140, 150, 160)
VENTAS = (175, 185, 195, 205, 215, 225)
PARES = [(c, v) for c in COMPRAS for v in VENTAS]
B40P = (140, 215)
DIA = 390
BLOQUE = 7800        # 20 días de 390 minutos: grupos del error estándar en la idea 14 (por la fecha del tick)
VERSION14 = "v2"     # se cambia a mano si cambia _f14


def par_spec(c, v):
    """La misma especificación que la idea 12, para reusar su caché."""
    return ("bandac", {"ancho": v - c, "centro": c + (v - c) // 2})


def fmt(x, d=3):
    return f"{x:.{d}f}".replace(".", ",")


# --- idea 13 ------------------------------------------------------------------------------------

def casos(cx):
    """caso (1 = S: 100 antes que 255; 2 = B), tD y toques de 215 y de 140 después de tD, por ventana."""
    if cx.conj.ventanas is None:
        cx.conj.normalizar_todas()
    out = []
    for w in cx.conj.ventanas:
        i100, i255 = w.index(100), w.index(255)
        tD = max(i100, i255)
        t215 = sum(1 for j in range(tD + 1, len(w)) if w[j] >= 215 and w[j - 1] < 215)
        t140 = sum(1 for j in range(tD + 1, len(w)) if w[j] <= 140 and w[j - 1] > 140)
        out.append((1 if i100 < i255 else 2, tD, t215, t140))
    return out


def componer(res_pares, caso, kS, kB):
    """Resultado de la regla combinada: ventana por ventana, el par del caso."""
    rS, rB = res_pares[kS], res_pares[kB]
    out = {}
    for campo in ("W", "n", "dd"):
        a, b = rS[campo], rB[campo]
        out[campo] = [a[i] if caso[i] == 1 else b[i] for i in range(len(caso))]
    return out


def filtro13(cx):
    cs = casos(cx)
    caso = [c[0] for c in cs]
    specs = [par_spec(c, v) for c, v in PARES]
    res = cx.ev(specs)
    k40 = PARES.index(B40P)
    L = [f"Idea 13 (la 11 del pedido del 19/11): niveles segun el orden de los extremos. Filtro "
         f"(ref/cotas/explorar_ideas2.py filtro13 --semilla {cx.semilla}), commit {E.commit()}",
         f"Muestra {cx.conj.nombre}: {len(caso)} ventanas. Caso S: el 100 llega antes que el 255; caso B: al reves.",
         "Toques: veces que el precio cruza hacia 215 o mas (o hacia 140 o menos) despues del tick que abre la fase D.", ""]
    pasa = []
    for k, nom in ((1, "S"), (2, "B")):
        idx = [i for i in range(len(caso)) if caso[i] == k]
        n = len(idx)
        W40 = sum(res[k40]["W"][i] for i in idx) / n
        con215 = sum(1 for i in idx if cs[i][2] > 0)
        t215 = sum(cs[i][2] for i in idx) / n
        con140 = sum(1 for i in idx if cs[i][3] > 0)
        tD = sorted(cs[i][1] for i in idx)[n // 2]
        medias = [(sum(res[j]["W"][i] for i in idx) / n, j) for j in range(len(PARES))]
        medias.sort(reverse=True)
        jm = medias[0][1]
        d, ee = E.delta_ee(cx, res[jm], res[k40], idx)
        _, ee60 = delta_ee_bloque(cx, res[jm], res[k40], idx, 23400)
        L += [f"== caso {nom}: {n} ventanas ({100 * n / len(caso):.1f} %), tick mediano de entrada a D {tD}",
              f"   banda 40 (140/215): patrimonio medio {W40:.0f}",
              f"   215 despues de entrar a D: lo tocan {con215} ventanas ({100 * con215 / n:.1f} %), {t215:.2f} toques por ventana",
              f"   140 despues de entrar a D: lo tocan {con140} ventanas ({100 * con140 / n:.1f} %)",
              f"   mejor par por patrimonio medio: {PARES[jm][0]}/{PARES[jm][1]}, {medias[0][0]:.0f}; "
              f"diferencia contra 140/215 {d:+.0f} (ee {ee:.0f}); {'mas' if abs(d) >= ee else 'menos'} de un error estandar; "
              f"con grupos de 60 dias, ee {ee60:.0f}",
              "   los cinco mejores pares: " + "; ".join(f"{PARES[j][0]}/{PARES[j][1]} {m:.0f}" for m, j in medias[:5]),
              "   patrimonio medio por par (filas: compra; columnas: venta " + " ".join(str(v) for v in VENTAS) + ")"]
        for c in COMPRAS:
            L.append(f"      {c}: " + " ".join(f"{sum(res[PARES.index((c, v))]['W'][i] for i in idx) / n:6.0f}" for v in VENTAS))
        L.append("")
        pasa.append(abs(d) >= ee)
    veredicto = any(pasa)
    L.append(f"Criterio del pedido: si en los dos casos el mejor par queda a menos de un error estandar de 140/215, se "
             f"descarta. Resultado: {'PASA' if veredicto else 'NO PASA'} "
             f"(S: {'mas' if pasa[0] else 'menos'} de un ee; B: {'mas' if pasa[1] else 'menos'} de un ee).")
    return L, veredicto


def idea13(cx):
    cs = casos(cx)
    caso = [c[0] for c in cs]
    specs = [par_spec(c, v) for c, v in PARES]
    res = cx.ev(specs)
    r40 = cx.ev([E.B40])[0]
    k40 = PARES.index(B40P)
    L = [f"Idea 13: niveles segun el orden de los extremos (clase B). ref/cotas/explorar_ideas2.py idea13 --semilla "
         f"{cx.semilla}, commit {E.commit()}",
         f"Muestra {cx.conj.nombre}: {len(caso)} ventanas; {len(PARES)} x {len(PARES)} combinaciones (par S, par B). Se elige "
         "la de mas puntos de torneo en el ajuste y se informa en la validacion.", ""]
    out = {"n": 13, "specs": {}}
    elegidas = {}
    for sep in E.SEPARACIONES:
        aj, va = f"{sep}-ajuste", f"{sep}-validacion"
        T = cx.T[aj]
        tabla = []
        for kS in range(len(PARES)):
            for kB in range(len(PARES)):
                r = componer(res, caso, kS, kB)
                tabla.append((T.puntos(r["W"])[0], kS, kB))
        tabla.sort(reverse=True)
        pts, kS, kB = tabla[0]
        elegidas[sep] = (kS, kB)
        r = componer(res, caso, kS, kB)
        nombre = f"S {PARES[kS][0]}/{PARES[kS][1]}, B {PARES[kB][0]}/{PARES[kB][1]}"
        ma, mv = cx.m(r, aj), cx.m(r, va)
        d, ee = E.delta_ee(cx, r, r40, cx.idx[va])
        _, ee60 = delta_ee_bloque(cx, r, r40, cx.idx[va], 23400)
        pos40 = next(k for k, t in enumerate(tabla) if t[1] == k40 and t[2] == k40)
        L += [f"== separacion por {sep}: ajuste {len(cx.idx[aj])} ventanas, validacion {len(cx.idx[va])}",
              "   cinco mejores en el ajuste: " + "; ".join(f"S {PARES[a][0]}/{PARES[a][1]} B {PARES[b][0]}/{PARES[b][1]} "
                                                          f"{p:.3f}" for p, a, b in tabla[:5]),
              f"   140/215 en los dos casos (banda 40) queda en el lugar {pos40 + 1} de {len(tabla)} en el ajuste",
              "   " + E.CAB,
              "   " + E.linea(("elegida " + nombre)[:34], ma) + "   (ajuste)",
              "   " + E.linea(("elegida " + nombre)[:34], mv) + "   (validacion)",
              "   " + E.linea("banda 40", cx.m(r40, aj)) + "   (ajuste)",
              "   " + E.linea("banda 40", cx.m(r40, va)) + "   (validacion)",
              f"   diferencia de patrimonio medio en la validacion contra banda 40: {d:+.0f} (ee {ee:.0f}; con grupos de "
              f"60 dias, ee {ee60:.0f})", ""]
        out["specs"][sep] = {"spec": ["orden", {"S": list(PARES[kS]), "B": list(PARES[kB])}], "nombre": nombre,
                             "ajuste": ma, "validacion": mv, "d40": [d, ee], "ee60": ee60}
    # comprobación: la composición es igual a la simulación directa de la regla
    directas = [("orden", {"S": PARES[a], "B": PARES[b]}) for a, b in set(elegidas.values())]
    rd = cx.ev(directas)
    malos = 0
    for sp, r in zip(directas, rd):
        a, b = PARES.index(sp[1]["S"]), PARES.index(sp[1]["B"])
        rc = componer(res, caso, a, b)
        malos += sum(1 for i in range(len(caso)) if rc["W"][i] != r["W"][i] or rc["n"][i] != r["n"][i])
    L.append(f"Comprobacion: la regla simulada directamente (OrdenD, ideas_reloj.py) contra la composicion por caso, "
             f"{len(directas)} reglas x {len(caso)} ventanas: {malos} diferencias" + ("  PASS" if malos == 0 else "  FAIL"))
    return L, out


# --- idea 14 ------------------------------------------------------------------------------------

_G = {}


def _f14(ids):
    conj, mins = _G["conj"], _G["min"]
    out = []
    for i in ids:
        emp, s = conj.filas[i][0], conj.filas[i][1]
        w = conj.ventana(i)
        mi = mins[emp]
        bloques = {}   # bloque de 20 días del tick (s + j) // 7800 -> (sumas, cuentas) por minuto del día
        saltos = []
        for j in range(1, len(w)):
            m = mi[s + j]
            b = (s + j) // BLOQUE
            if b not in bloques:
                bloques[b] = ([0] * DIA, [0] * DIA)
            sm, cn = bloques[b]
            sm[m] += w[j] - w[j - 1]
            cn[m] += 1
            if m == 0:
                saltos.append(j)
        cont = []      # (J, F1, F30, bloque): salto, minuto siguiente, 30 minutos siguientes
        for j in saltos:
            if j + 30 < len(w):
                cont.append((w[j] - w[j - 1], w[j + 1] - w[j], w[j + 30] - w[j], (s + j) // BLOQUE))
        det = {}
        for nombre, clase in IR.DETECTORES.items():
            d = clase()
            primer = -1
            pred = acierto = 0
            js = set(saltos)
            for n in range(len(w)):
                if d.predice():
                    pred += 1
                    if n in js:
                        acierto += 1
                        if primer < 0:
                            primer = n
                d.paso(w[n])
            # saltos después del primer acierto que el detector predijo
            tras = [j for j in saltos if primer >= 0 and j > primer]
            det[nombre] = (primer, pred, acierto, len(tras))
        out.append(([(b, sm, cn) for b, (sm, cn) in sorted(bloques.items())], cont, det, len(saltos)))
    return ids, out


def medir14(cx, procesos=None):
    ruta = os.path.join(E.CACHE, f"f14_{VERSION14}_{cx.conj.clave()}_{_cod}_{E.MOTOR}.json")
    if os.path.exists(ruta):
        return json.load(open(ruta))
    cx.conj.cargar_series()
    mins = {}
    for emp in E.EMPRESAS:
        _, m, _ = reales.leer_sesion(cx.conj.carpeta, emp)
        mins[emp] = m
    _G["conj"], _G["min"] = cx.conj, mins
    nv = len(cx.conj.filas)
    tareas = [list(range(a, min(nv, a + 40))) for a in range(0, nv, 40)]
    res = [None] * nv
    with Pool(procesos or os.cpu_count()) as pool:
        for ids, out in pool.imap_unordered(_f14, tareas):
            for i, o in zip(ids, out):
                res[i] = o
    json.dump(res, open(ruta, "w"))
    return res


def media_ee_tick(cx, idx, R, f):
    """Media de un efecto por tick con error estándar por grupos de ticks: (empresa, bloque de 20 días del
    tick mismo, no de la ventana). Un mismo tick aparece en muchas ventanas de la muestra, que caen en el mismo
    grupo. f(R[i]) entrega (bloque, suma, cuenta) de la ventana i."""
    g = {}
    for i in idx:
        emp = cx.conj.filas[i][0]
        for b, v, n in f(R[i]):
            a = g.setdefault((emp, b), [0.0, 0])
            a[0] += v
            a[1] += n
    N = sum(a[1] for a in g.values())
    if N == 0:
        return 0.0, 0.0, 0
    m = sum(a[0] for a in g.values()) / N
    return m, (sum((a[0] - m * a[1]) ** 2 for a in g.values())) ** 0.5 / N, N


def delta_ee_bloque(cx, rA, rB, idx, bloque):
    """Como E.delta_ee, con grupos de ventanas por empresa y bloque de `bloque` minutos de inicio. Con 23 400
    (60 días, más que el largo de una ventana) es la versión conservadora: con bloques de 20 días, las ventanas
    de bloques vecinos comparten la mayor parte de sus precios y el error estándar sale más chico."""
    d = [rA["W"][i] - rB["W"][i] for i in idx]
    n = len(d)
    m = sum(d) / n
    g = {}
    for i, x in zip(idx, d):
        f = cx.conj.filas[i]
        k = (f[0], f[1] // bloque)
        g[k] = g.get(k, 0.0) + (x - m)
    return m, (sum(v * v for v in g.values())) ** 0.5 / n


def filtro14(cx, procesos=None):
    t0 = time.time()
    R = medir14(cx, procesos)
    filas = cx.conj.filas
    todo = list(range(len(filas)))
    L = [f"Idea 14 (la 12 del pedido del 19/11): reloj de dia de mercado. Filtro (ref/cotas/explorar_ideas2.py filtro14 "
         f"--semilla {cx.semilla}), commit {E.commit()}",
         f"Muestra {cx.conj.nombre}: {len(filas)} ventanas normalizadas de 20 000 minutos. Unidades: niveles de precio "
         "normalizado (100 a 255) por tick. Error estandar por grupos de ticks: empresa y bloque de 20 dias de la fecha del "
         "tick (el mismo tick aparece en muchas ventanas; agrupar por el inicio de la ventana subestima el error).",
         "Minuto 0 = el tick del salto de cierre a apertura (primer minuto del dia: p(apertura) - p(cierre anterior)).", ""]

    def efecto(idx, m):
        return media_ee_tick(cx, idx, R, lambda r: ((b, sm[m], cn[m]) for b, sm, cn in r[0]))

    def por_salto(idx, f, cond=lambda a: True):
        return media_ee_tick(cx, idx, R, lambda r: ((b, f(a, b1, c), 1) for a, b1, c, b in r[1] if cond(a)))

    def ef_salto1(idx):     # lo que gana por accion quien pasa el salto: J + primer minuto
        return por_salto(idx, lambda a, b1, c: a + b1)

    def ef_cont(idx):       # signo del salto por los 30 minutos siguientes (+ continúa, - revierte)
        return por_salto(idx, lambda a, b1, c: (1 if a > 0 else -1) * c, lambda a: a != 0)

    def ef_absj(idx):
        return por_salto(idx, lambda a, b1, c: abs(a))

    # 1. salto por empresa y año de inicio
    L += ["== 1. Salto de cierre a apertura (minuto 0): media (ee) y t, por empresa y por anio de inicio de la ventana"]
    L.append(f"   {'empresa':8s} " + " ".join(f"{a:>22d}" for a in E.ANIOS) + f" {'todas':>22s}")
    for emp in tuple(E.EMPRESAS) + ("todas",):
        cel = []
        for a in tuple(E.ANIOS) + ("todas",):
            idx = [i for i in todo if (emp == "todas" or filas[i][0] == emp) and (a == "todas" or filas[i][2] == a)]
            m, ee, N = efecto(idx, 0)
            cel.append(f"{m:+7.3f} ({ee:5.3f}) t{m / ee if ee else 0:+5.1f}")
        L.append(f"   {emp:8s} " + " ".join(f"{c:>22s}" for c in cel))
    m, ee, N = ef_absj(todo)
    L += [f"   tamano del salto: |J| medio {m:.2f} niveles (ee {ee:.2f}), en {N} saltos de la muestra", ""]

    # 2. ajuste y validación por separación: salto, salto + primer minuto, continuación, y los 389 minutos
    L.append("== 2. Efectos en el ajuste y en la validacion de cada separacion: media (ee) y t")
    subconj = {k: cx.idx[k] for k in ("anios-ajuste", "anios-validacion", "empresas-ajuste", "empresas-validacion")}
    efectos = [("salto (minuto 0)", lambda idx: efecto(idx, 0)),
               ("salto + primer minuto (lo que gana quien pasa el salto)", ef_salto1),
               ("signo del salto x 30 minutos siguientes (+ sigue, - revierte)", ef_cont)]
    tabla_t = {}
    for nom, f in efectos:
        cel = []
        for k, idx in subconj.items():
            m, ee, N = f(idx)
            tabla_t[(nom, k)] = (m, ee)
            cel.append(f"{k}: {m:+.3f} ({ee:.3f}) t{m / ee if ee else 0:+.1f}")
        L.append(f"   {nom}")
        L.append("      " + "; ".join(cel))
    # condicional: media de F30 con salto positivo y con salto negativo, en toda la muestra
    for signo, nom in ((1, "salto positivo"), (-1, "salto negativo")):
        m, ee, N = por_salto(todo, lambda a, b1, c: c, lambda a: a * signo > 0)
        L.append(f"   30 minutos despues de un {nom}: {m:+.3f} (ee {ee:.3f}), {N} saltos")
    L.append("")

    # minutos 1 a 389
    sig = {}
    for k, idx in subconj.items():
        sig[k] = {}
        for mnt in range(DIA):
            m, ee, N = efecto(idx, mnt)
            sig[k][mnt] = (m, ee)
    L.append("== 3. Los 390 minutos del dia: cuantos superan 2 ee (se esperan unos 20 por azar en cada subconjunto)")
    for k in subconj:
        n2 = sum(1 for mnt in range(DIA) if sig[k][mnt][1] and abs(sig[k][mnt][0]) > 2 * sig[k][mnt][1])
        L.append(f"   {k}: {n2} de 390")

    def mantiene(sep, mnt=None, nom=None):
        a, v = f"{sep}-ajuste", f"{sep}-validacion"
        ma, ea = sig[a][mnt] if nom is None else tabla_t[(nom, a)]
        mv, ev = sig[v][mnt] if nom is None else tabla_t[(nom, v)]
        return ea > 0 and ev > 0 and abs(ma) > 2 * ea and abs(mv) > 2 * ev and (ma > 0) == (mv > 0)

    L.append("   minutos que superan 2 ee en el ajuste y se mantienen en la validacion (mismo signo y mas de 2 ee):")
    pasan = {}
    for sep in E.SEPARACIONES:
        pasan[sep] = [mnt for mnt in range(DIA) if mantiene(sep, mnt)]
        L.append(f"      {sep}: " + (", ".join(f"{mnt} ({reales.hora(mnt)}): ajuste {sig[f'{sep}-ajuste'][mnt][0]:+.3f}, "
                                               f"validacion {sig[f'{sep}-validacion'][mnt][0]:+.3f}" for mnt in pasan[sep])
                                     or "ninguno"))
    ambos = sorted(set(pasan["anios"]) & set(pasan["empresas"]))
    L.append("      en las dos separaciones: " + (", ".join(f"{mnt} ({reales.hora(mnt)})" for mnt in ambos) or "ninguno"))
    otros = [nom for nom, _ in efectos if all(mantiene(sep, nom=nom) for sep in E.SEPARACIONES)]
    L.append("   salto, salto + primer minuto y continuacion que se mantienen en las dos separaciones: "
             + (", ".join(otros) or "ninguno"))
    pasa = bool(ambos) or bool(otros)
    L.append("")

    # 4. tamaño económico
    L.append("== 4. Tamano necesario: comprar q acciones para pasar el salto y venderlas paga 2 comisiones (10). Con q = 63,")
    L.append("   el salto + primer minuto tendria que valer mas de 10 / 63 = 0,16 niveles por salto en promedio.")
    L.append("")

    # 5. detectores
    L.append("== 5. Deteccion de la fase del dia con la serie recibida (ideas_reloj.py; contador que da la vuelta en 390)")
    for nombre in IR.DETECTORES:
        primeros = sorted(R[i][2][nombre][0] for i in todo if R[i][2][nombre][0] >= 0)
        nunca = sum(1 for i in todo if R[i][2][nombre][0] < 0)
        pred = sum(R[i][2][nombre][1] for i in todo)
        aci = sum(R[i][2][nombre][2] for i in todo)
        tras = sum(R[i][2][nombre][3] for i in todo)
        # aciertos después del primero / saltos después del primero
        aci_tras = aci - (len(todo) - nunca)
        n = len(primeros)
        L.append(f"   {nombre}: primer salto predicho en el tick (mediana / p90 / max) "
                 f"{primeros[n // 2]} / {primeros[int(0.9 * (n - 1))]} / {primeros[-1]}; nunca en {nunca} de {len(todo)} ventanas")
        L.append(f"      despues del primer acierto predice {100 * aci_tras / max(1, tras):.1f} % de los saltos; "
                 f"de todas sus predicciones, {100 * aci / max(1, pred):.1f} % son saltos")
    L.append("")
    L.append(f"Criterio del pedido: algun efecto supera 2 ee y se mantiene en la validacion por anios y por empresas. "
             f"Resultado: {'PASA' if pasa else 'NO PASA'}. ({time.time() - t0:.0f} s)")
    return L, pasa


# --- idea 14: la regla ---------------------------------------------------------------------------

SPECS14 = [("reloj", {"detector": d, "h": h}) for d in ("oraculo", "histograma", "bloque") for h in (1, 5, 30)]
_MINS = {}


def _antes14(i):
    f = _G["conj14"].filas[i]
    IR.MINUTOS_VENTANA = _MINS[f[0]][f[1]:f[1] + E.LARGO]


def _cond14(ids):
    """Salto + primer minuto (p(j+1) - p(j-1)) en la fase D de la banda 40, según si la banda estaba en caja o
    invertida al cierre (acciones después de ejecutar en j-1)."""
    import ideas
    conj = _G["conj14"]
    out = []
    for i in ids:
        emp, s = conj.filas[i][0], conj.filas[i][1]
        w = conj.ventana(i)
        mi = _MINS[emp]
        st = ideas.crear(E.B40)
        caja, acc, d = ideas.CAJA0, 0, ideas.M
        accs = []
        for p in w:
            if d:
                a, q = d >> 6, d & 63
                if a == 1:
                    q = min(q, (caja - ideas.COMISION) // p)
                    if q > 0:
                        caja -= q * p + ideas.COMISION
                        acc += q
                elif a == 2:
                    q = min(q, acc)
                    if q > 0:
                        caja += q * p - ideas.COMISION
                        acc -= q
            accs.append(acc)
            d = st.decidir(p, caja, acc)
        tD = st.tD
        r = []
        for j in range(max(2, tD + 2), len(w) - 1):
            if mi[s + j] == 0:
                r.append((1 if accs[j - 1] > 0 else 0, w[j + 1] - w[j - 1], (s + j) // BLOQUE))
        out.append(r)
    return ids, out


def salto_condicional(cx, procesos=None):
    cx.conj.cargar_series()
    nv = len(cx.conj.filas)
    tareas = [list(range(a, min(nv, a + 40))) for a in range(0, nv, 40)]
    res = [None] * nv
    with Pool(procesos or os.cpu_count()) as pool:
        for ids, out in pool.imap_unordered(_cond14, tareas):
            for i, o in zip(ids, out):
                res[i] = o
    L = ["== Diagnostico: salto + primer minuto, p(j+1) - p(j-1), en la fase D de la banda 40, segun su posicion al cierre",
         "   (lo que gana por accion quien pasa el salto; grupos por empresa y bloque de 20 dias del tick)"]
    for k in ("muestra", "anios-validacion", "empresas-validacion"):
        cel = []
        for est, nom in ((0, "en caja"), (1, "invertida")):
            m, ee, N = media_ee_tick(cx, cx.idx[k], res, lambda r, est=est: ((b, v, 1) for e, v, b in r if e == est))
            cel.append(f"{nom}: {m:+.3f} (ee {ee:.3f}), {N} saltos")
        L.append(f"   {k}: " + "; ".join(cel))
    return L


def nombre14(sp):
    kw = sp[1]
    return f"reloj {kw['detector']} h={kw['h']}"


def idea14(cx):
    for emp in E.EMPRESAS:
        _, m, _ = reales.leer_sesion(cx.conj.carpeta, emp)
        _MINS[emp] = m
    _G["conj14"] = cx.conj
    E._G["antes"] = _antes14
    res = cx.ev(SPECS14)
    E._G.pop("antes", None)
    r40 = cx.ev([E.B40])[0]
    L = [f"Idea 14: reloj de dia de mercado, la regla (clase B). ref/cotas/explorar_ideas2.py idea14 --semilla {cx.semilla}, "
         f"commit {E.commit()}",
         f"Muestra {cx.conj.nombre}: {len(cx.todo)} ventanas; {len(SPECS14)} variantes. En la fase D, con la banda 40 en caja, "
         "compra 63 para pasar el salto de cierre a apertura y vende h ticks despues del salto. Detector: 'oraculo' usa el "
         "minuto verdadero del dia (cota superior, la placa no lo tiene); 'histograma' y 'bloque' son los de ideas_reloj.py.",
         "Se elige la de mas puntos de torneo en el ajuste y se informa en la validacion.", ""]
    out = {"n": 14, "specs": {}}
    L += salto_condicional(cx) + [""]
    for sep in E.SEPARACIONES:
        aj, va = f"{sep}-ajuste", f"{sep}-validacion"
        ma = [cx.m(r, aj) for r in res]
        mv = [cx.m(r, va) for r in res]
        orden = sorted(range(len(SPECS14)), key=lambda k: -ma[k]["pts"])
        L += [f"== separacion por {sep}: ajuste {len(cx.idx[aj])} ventanas, validacion {len(cx.idx[va])}",
              f"   {'variante':24s} {'pts ajuste':>10s} {'pts val.':>9s} {'vueltas/v':>10s} {'d40 val. (ee; ee 60 d)':>26s} "
              f"{'d40 por vuelta':>15s}"]
        for k in orden:
            r = res[k]
            vu = sum(r["info"][i][1] for i in cx.idx[va] if len(r["info"][i]) > 1) / len(cx.idx[va])
            d, ee = E.delta_ee(cx, r, r40, cx.idx[va])
            _, ee60 = delta_ee_bloque(cx, r, r40, cx.idx[va], 23400)
            L.append(f"   {nombre14(SPECS14[k]):24s} {ma[k]['pts']:10.3f} {mv[k]['pts']:9.3f} {vu:10.2f} "
                     f"{d:+8.0f} ({ee:4.0f}; {ee60:4.0f})     {d / vu if vu else 0:+10.1f}")
        k0 = orden[0]
        r = res[k0]
        d, ee = E.delta_ee(cx, r, r40, cx.idx[va])
        _, ee60 = delta_ee_bloque(cx, r, r40, cx.idx[va], 23400)
        L += ["   " + E.CAB,
              "   " + E.linea(("elegida " + nombre14(SPECS14[k0]))[:34], mv[k0]) + "   (validacion)",
              "   " + E.linea("banda 40", cx.m(r40, va)) + "   (validacion)", ""]
        out["specs"][sep] = {"spec": SPECS14[k0], "nombre": nombre14(SPECS14[k0]), "ajuste": ma[k0], "validacion": mv[k0],
                             "d40": [d, ee], "ee60": ee60}
    return L, out


# --- primera sola sin la copia ------------------------------------------------------------------

def primera(cx, carpeta, semilla, procesos):
    L = [f"Primera sola sin la copia espera_banda40 en el campo (ref/cotas/explorar_ideas2.py primera --semilla {semilla}), "
         f"commit {E.commit()}",
         "Mismo sorteo de torneos que la tabla 2, con espera_banda40 fuera del campo (el resto igual).", "",
         f"{'subconjunto':22s} {'estrategia':22s} {'pts':>6s} {'1a %':>6s} {'pts sin':>8s} {'1a % sin':>9s}"]
    rb = cx.ev([b for _, b in E.BASES])
    for k in ("anios-validacion", "empresas-validacion", "muestra"):
        Tx = E.Torneo(cx.idx[k], cx.R, k + "-sin-copia", semilla, excluir=("espera_banda40",))
        for (nm, _), r in zip(E.BASES, rb):
            m = cx.m(r, k)
            p, q = Tx.puntos(r["W"])
            L.append(f"{k:22s} {nm:22s} {m['pts']:6.3f} {m['pri']:6.1f} {p:8.3f} {100 * q:9.1f}")
    conj = E.completa(carpeta)
    R = E.rivales(conj)
    res = E.evaluar(conj, [b for _, b in E.BASES], procesos, info=False)
    idx = {"completa-todas": list(range(len(conj.filas)))}
    for sep, (aj, va) in E.SEPARACIONES.items():
        idx[f"completa-{sep}-validacion"] = E.sub(conj, va)
    for k, ix in idx.items():
        T = E.Torneo(ix, R, k, semilla)
        Tx = E.Torneo(ix, R, k + "-sin-copia", semilla, excluir=("espera_banda40",))
        for (nm, _), r in zip(E.BASES, res):
            p0, q0 = T.puntos(r["W"])
            p, q = Tx.puntos(r["W"])
            L.append(f"{k:22s} {nm:22s} {p0:6.3f} {100 * q0:6.1f} {p:8.3f} {100 * q:9.1f}")
    return L


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=("filtro13", "idea13", "filtro14", "idea14", "primera"))
    ap.add_argument("--semilla", type=int, default=E.SEMILLA)
    ap.add_argument("--datos", default=None)
    ap.add_argument("--procesos", type=int, default=None)
    a = ap.parse_args()
    carpeta = reales.carpeta_datos(a.datos)
    os.makedirs(E.SALIDA, exist_ok=True)
    cx = E.Ctx(carpeta, a.semilla, a.procesos)
    if a.accion == "filtro13":
        L, _ = filtro13(cx)
        nombre = "filtro13.txt"
    elif a.accion == "idea13":
        L, out = idea13(cx)
        json.dump(out, open(os.path.join(E.SALIDA, "idea13.json"), "w"), indent=1)
        nombre = "idea13.txt"
    elif a.accion == "filtro14":
        L, _ = filtro14(cx, a.procesos)
        nombre = "filtro14.txt"
    elif a.accion == "idea14":
        L, out = idea14(cx)
        json.dump(out, open(os.path.join(E.SALIDA, "idea14.json"), "w"), indent=1)
        nombre = "idea14.txt"
    else:
        L = primera(cx, carpeta, a.semilla, a.procesos)
        nombre = "primera.txt"
    texto = "\n".join(L) + "\n"
    open(os.path.join(E.SALIDA, nombre), "w").write(texto)
    print(texto, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
