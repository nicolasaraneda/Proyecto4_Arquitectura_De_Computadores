#!/usr/bin/env python3
"""v5_diag.py: diagnóstico de la sección 15. Con el motor de placa desde D = 0 y sin fase A, fracción de rondas que
cierran candado según el caso, la clase de v^2 al primer extremo y los ticks restantes.
Salida: docs/mediciones/exploracion/v5_diag.txt.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso (con export P4_DATOS=~/proyectos/datos_p4): python3 ref/cotas/v5_diag.py
"""
import sys, os, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorar_v5 as X, v5 as V
c, pre, WR = X.contexto("diag")
SAL = ["# V5: cuándo cierra candado el motor desde D = 0", "", "ref/cotas/v5_diag.py. Sin fase A, motor de placa de 16 tramos, M 100.", ""]


def di(x):
    print(x)
    SAL.append(x)

res = X.evaluar(c, {"x": (X.SIN_A, dict(motor="v2c", M=100, amb=True))}, "diag")["x"]
def cl(i):
    ev = pre[i]["cv"]
    return ev[-1][1] if ev else -1
def tr(i):
    r = 19999 - pre[i]["tA"]
    return "0-5000" if r < 5000 else "5000-10000" if r < 10000 else "10000-15000" if r < 15000 else "15000-20000"
for nombre, f in (("clase de v^2 al primer extremo", cl), ("ticks restantes al primer extremo", tr)):
    di(f"\n## Por {nombre}\n\n| Caso | Valor | Rondas | Cierra candado % | D media si cierra | D media si no |\n|---|---|---|---|---|---|")
    for cs in ("S", "B"):
        g = collections.defaultdict(list)
        for i in range(c.n):
            if c.caso[i] == cs:
                g[f(i)].append(i)
        for k in sorted(g, key=str):
            idx = g[k]
            ok = [i for i in idx if res["g"][i] == "recuperacion"]
            no = [i for i in idx if res["g"][i] != "recuperacion"]
            di(f"| {cs} | {k} | {len(idx)} | {100 * len(ok) / len(idx):.1f} | "
               f"{(sum(res['D'][i] for i in ok) / len(ok)) if ok else 0:+.0f} | {(sum(res['D'][i] for i in no) / len(no)) if no else 0:+.0f} |")

open(os.path.join(X.SALIDA, "v5_diag.txt"), "w").write("\n".join(SAL) + "\n")
