#!/usr/bin/env python3
"""v5_mezclas.py: arista 9 de la sección 15 (cobertura). Mezclas de bandas como subcuentas, aproximadas por el
promedio de los patrimonios de las reglas puras; índice y déficit ponderado.
Salida: docs/mediciones/exploracion/v5_mezclas.txt.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso (con export P4_DATOS=~/proyectos/datos_p4): python3 ref/cotas/v5_mezclas.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorar_v5 as X, v5 as V
c, pre, WR = X.contexto("mezclas")
def mez(*ks):
    return [sum(WR[k][i] for k in ks) / len(ks) for i in range(c.n)]
Ws = {"banda 40": WR["b40"], "banda 30": WR["b30"], "banda 50": WR["b50"],
      "(b30 + b40) / 2": mez("b30", "b40"), "(b40 + b50) / 2": mez("b40", "b50"), "(b30 + b50) / 2": mez("b30", "b50"),
      "(b30 + b40 + b50) / 3": mez("b30", "b40", "b50"), "(b30 + b40 + b50 + b60) / 4": mez("b30", "b40", "b50", "b60"),
      "(b40 + ext) / 2": mez("b40", "ext"), "(b30 + ext) / 2": mez("b30", "ext"), "(b40 + b40 + b30 + b50) / 4": mez("b40", "b40", "b30", "b50"),
      "(b30 + b40 + b50 + b60 + ext) / 5": mez("b30", "b40", "b50", "b60", "ext")}
ind = X.indices(c, Ws)
L = ["# V5, arista 9: cobertura con mezclas de bandas", "",
     "ref/cotas/v5_mezclas.py. Aproximación: el patrimonio de la mezcla es el promedio de las reglas puras (subcuentas iguales, sin "
     "simular sus órdenes ni el redondeo de acciones). Déficit ponderado = suma por rival de peso por déficit del torneo.", "",
     "| Mezcla | nd (ee) | g (ee) | déficit ponderado | " + " | ".join(f"{r}: nd / déficit" for r in V.RIVALES) + " |",
     "|---|---|---|---|" + "---|" * len(V.RIVALES)]
for nm in Ws:
    m = ind[(nm, "todas")][0]
    dp = sum(V.PESOS[r] * m[r]["d"] for r in V.RIVALES)
    L.append(f"| {nm} | {X.fmt(m['nd'])} ({X.fmt(m['ee_nd'])}) | {X.fmt(m['g'])} ({X.fmt(m['ee_g'])}) | {dp:.0f} | "
             + " | ".join(f"{X.fmt(m[r]['nd'])} / {m[r]['d']:.0f}" for r in V.RIVALES) + " |")
txt = "\n".join(L) + "\n"
open(os.path.join(X.SALIDA, "v5_mezclas.txt"), "w").write(txt)
print(txt)
