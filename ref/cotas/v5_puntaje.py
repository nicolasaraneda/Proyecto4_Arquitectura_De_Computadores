#!/usr/bin/env python3
"""v5_puntaje.py: el puntaje de la competencia bajo el pronóstico (sección 15 de docs/exploracion_ideas.md).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El puntaje es lineal entre el peor grupo (0) y el mejor (2), con el promedio de las tres rondas. Aquí el campo
es: nosotros, el mejor rival del pronóstico (v5.PESOS) y un peor grupo con un patrimonio fijo (10 000: no opera;
15 000: opera mal). Por torneo de 3 rondas, con P = promedio propio, R = promedio del rival y w = min(peor, P, R):
  puntaje = 2 si P >= R; si no, 2 (P - w) / (R - w).
Es un supuesto sobre el campo, no una medición de la competencia: sirve para poner nd y el déficit en la misma
unidad que la nota. Mismos sorteos y mismos errores estándar agrupados que explorar_v5.py.

Uso (con export P4_DATOS=~/proyectos/datos_p4): python3 ref/cotas/v5_puntaje.py
Salida: docs/mediciones/exploracion/v5_puntaje.txt.
"""
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorar_regimen as XR  # noqa: E402
import explorar_v5 as X        # noqa: E402
import v5 as V                 # noqa: E402

PEORES = (10000, 15000)
KS = (1, 2, 3, 5, 8)
CAMPOS = {"los seis rivales a la vez": V.RIVALES,
          "sin la banda 40 exacta (ext, f5, b30, b50, b60)": ("ext", "f5", "b30", "b50", "b60"),
          "ext, f5 y la banda 40": ("ext", "f5", "b40")}


def _puntaje(args):
    nombre, W = args
    tr, n_idx = X._G["sorteos"]["todas"]
    WR = X._G["WR"]
    n = len(W)
    out = {}
    for peor in PEORES:
        tot = [0.0] * len(tr)
        por = {}
        for r in V.RIVALES:
            Wr = WR[r]
            pw = V.PESOS[r]
            s = 0.0
            for t, (a, b, c) in enumerate(tr):
                P = (W[a] + W[b] + W[c]) / 3.0
                R = (Wr[a] + Wr[b] + Wr[c]) / 3.0
                if P >= R:
                    x = 2.0
                else:
                    w = peor if peor < P else P
                    x = 2.0 * (P - w) / (R - w)
                tot[t] += pw * x
                s += x
            por[r] = s / len(tr)
        out[peor] = (sum(tot) / len(tot), X._contrib(tot, tr, n, n_idx), por)
    # campo con varios rivales a la vez: el mejor rival de cada torneo es el de mayor promedio
    for clave, campo in CAMPOS.items():
        nd, g, pt = [0.0] * len(tr), [0.0] * len(tr), [0.0] * len(tr)
        for t, (a, b, c) in enumerate(tr):
            P = (W[a] + W[b] + W[c]) / 3.0
            R = max((WR[r][a] + WR[r][b] + WR[r][c]) / 3.0 for r in campo)
            if P > R - X.XC.EMPATE:
                nd[t] = 1.0
                if P >= R + X.XC.EMPATE:
                    g[t] = 1.0
            if P >= R:
                pt[t] = 2.0
            else:
                w = 10000 if 10000 < P else P
                pt[t] = 2.0 * (P - w) / (R - w)
        out[clave] = tuple((sum(v) / len(v), X._contrib(v, tr, n, n_idx)) for v in (nd, g, pt))
    # campo sorteado: K rivales, cada uno de un tipo sorteado con los pesos del pronóstico (los mismos sorteos para todas)
    for K, tipos in X._G["campos_k"].items():
        nd, g, pt = [0.0] * len(tr), [0.0] * len(tr), [0.0] * len(tr)
        for t, (a, b, c) in enumerate(tr):
            P = (W[a] + W[b] + W[c]) / 3.0
            R = max((WR[r][a] + WR[r][b] + WR[r][c]) / 3.0 for r in tipos[t])
            if P > R - X.XC.EMPATE:
                nd[t] = 1.0
                if P >= R + X.XC.EMPATE:
                    g[t] = 1.0
            if P >= R:
                pt[t] = 2.0
            else:
                w = 10000 if 10000 < P else P
                pt[t] = 2.0 * (P - w) / (R - w)
        out[("K", K)] = tuple((sum(v) / len(v), X._contrib(v, tr, n, n_idx)) for v in (nd, g, pt))
    return nombre, out


def main():
    c, pre, WR = X.contexto("puntaje")
    var = dict(X.FINALISTAS)
    var.update(X.SOBRE30)
    var.update({"V4b": X.V4B, X.SIN_FASE_A: (X.SIN_A, dict(motor="v2c", M=100, amb=True))})
    res = X.evaluar(c, var, "puntaje")
    import random
    pesos = [V.PESOS[r] for r in V.RIVALES]
    X._G["campos_k"] = {}
    for K in KS:
        rng = random.Random(f"campo-{K}-{X.XC.SEMILLA}")
        X._G["campos_k"][K] = [tuple(set(rng.choices(V.RIVALES, pesos, k=K))) for _ in range(X.XC.SORTEOS)]
    Ws = {"banda 40 sola": WR["b40"], "banda 30 sola": WR["b30"], "banda 50 sola": WR["b50"], "extremos puros": WR["ext"]}
    Ws.update({nm: res[nm]["W"] for nm in var})
    with Pool(os.cpu_count()) as pool:
        out = dict(pool.imap_unordered(_puntaje, list(Ws.items())))
    L = ["# V5: puntaje esperado de la competencia bajo el pronóstico", "",
         f"ref/cotas/v5_puntaje.py, commit {XR.commit()}. Campo supuesto: nosotros, el mejor rival del pronóstico y un peor grupo "
         "con patrimonio fijo. Puntaje por torneo de 3 rondas: 2 si nuestro promedio no queda debajo del rival; si no, "
         "2 (P - w) / (R - w), con w el menor entre el peor grupo, P y R. Promedio ponderado por rival con los pesos del índice. "
         "Entre paréntesis, ee agrupado; las diferencias contra la banda 40 sola son pareadas.", ""]
    for peor in PEORES:
        L.append(f"\n## Peor grupo en {peor}\n")
        L.append("| Estrategia | Puntaje esperado (ee) | Diferencia con la banda 40 sola (ee) | " + " | ".join(V.RIVALES) + " |")
        L.append("|---|---|---|" + "---|" * len(V.RIVALES))
        m0, c0, _ = out["banda 40 sola"][peor]
        for nm in Ws:
            m, cv, por = out[nm][peor]
            ee = XR.ee_contrib(cv, c.G, True)[0]
            eed = XR.ee_contrib([x - y for x, y in zip(cv, c0)], c.G, True)[0]
            L.append(f"| {nm} | {m:.4f} ({ee:.4f}) | {m - m0:+.4f} ({eed:.4f}) | " + " | ".join(f"{por[r]:.3f}" for r in V.RIVALES) + " |")
    for clave in CAMPOS:
        L.append(f"\n## Campo con varios rivales a la vez: {clave}\n")
        L.append("El mejor rival de cada torneo es el de mayor promedio entre los del campo. nd = % de torneos en que no quedamos "
                 "debajo de ese mejor (diferencia mayor que -10); g = % en que lo superamos por 10 o más; puntaje con el peor grupo en 10000.\n")
        L.append("| Estrategia | nd % (ee) | g % (ee) | Puntaje (ee) | Δnd con la banda 40 (ee) | Δg con la banda 40 (ee) | Δ puntaje con la banda 40 (ee) |")
        L.append("|---|---|---|---|---|---|---|")
        b = out["banda 40 sola"][clave]
        for nm in Ws:
            o = out[nm][clave]
            cel, dif = [], []
            for k, esc, dec in ((0, 100, 1), (1, 100, 1), (2, 1, 4)):
                m, cv = o[k]
                ee = XR.ee_contrib(cv, c.G, True)[0]
                eed = XR.ee_contrib([x - y for x, y in zip(cv, b[k][1])], c.G, True)[0]
                cel.append(f"{esc * m:.{dec}f} ({esc * ee:.{dec}f})")
                dif.append(f"{esc * (m - b[k][0]):+.{dec}f} ({esc * eed:.{dec}f})")
            L.append(f"| {nm} | " + " | ".join(cel + dif) + " |")
    L.append("\n## Campo sorteado de K rivales\n")
    L.append("En cada torneo el campo tiene K rivales, cada uno de un tipo sorteado con los pesos del pronóstico (pueden repetirse); el "
             "mejor rival es el de mayor promedio. Con K = 1 es el índice. Los mismos campos para todas las estrategias. Celda: "
             "nd % / g % / diferencia de puntaje con la banda 40 sola (ee), con el peor grupo en 10000.\n")
    L.append("| Estrategia | " + " | ".join(f"K = {K}" for K in KS) + " |")
    L.append("|---|" + "---|" * len(KS))
    for nm in Ws:
        cel = []
        for K in KS:
            o, b = out[nm][("K", K)], out["banda 40 sola"][("K", K)]
            eed = XR.ee_contrib([x - y for x, y in zip(o[2][1], b[2][1])], c.G, True)[0]
            cel.append(f"{100 * o[0][0]:.1f} / {100 * o[1][0]:.1f} / {o[2][0] - b[2][0]:+.4f} ({eed:.4f})")
        L.append(f"| {nm} | " + " | ".join(cel) + " |")
    L.append("\nDiferencia de nd con la banda 40 sola (ee) en cada K:\n")
    L.append("| Estrategia | " + " | ".join(f"K = {K}" for K in KS) + " |")
    L.append("|---|" + "---|" * len(KS))
    for nm in Ws:
        cel = []
        for K in KS:
            o, b = out[nm][("K", K)], out["banda 40 sola"][("K", K)]
            eed = XR.ee_contrib([x - y for x, y in zip(o[0][1], b[0][1])], c.G, True)[0]
            cel.append(f"{100 * (o[0][0] - b[0][0]):+.1f} ({100 * eed:.1f})")
        L.append(f"| {nm} | " + " | ".join(cel) + " |")
    import re
    txt = re.sub(r"(\d)\.(\d)", r"\1,\2", "\n".join(L)) + "\n"       # coma decimal solo en los números
    open(os.path.join(X.SALIDA, "v5_puntaje.txt"), "w").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
