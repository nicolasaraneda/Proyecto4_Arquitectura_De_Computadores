#!/usr/bin/env python3
"""grilla.py: qué umbrales elige tools/retune.py para cada comisión y caja, y qué juego de
bitstreams/contingencia/ corresponde a cada caso.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Corre retune (sin simular) para 14 comisiones y 7 cajas y escribe la tabla del árbol de
decisión (docs/arbol_decision.md, sección 2). Un poco más de un minuto.

Uso: python3 tools/p8/grilla.py   (o make contingencia-grilla)
Salida: docs/mediciones/p8/retune_grilla.txt
"""
import os
import re
import subprocess
import sys
from multiprocessing import Pool

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMISIONES = (0, 2, 5, 8, 10, 12, 15, 20, 25, 30, 40, 50, 75, 100)
CAJAS = (1000, 2000, 5000, 10000, 20000, 50000, 100000)


def umbrales(args):
    c, k = args
    r = subprocess.run([sys.executable, "tools/retune.py", "--comision", str(c), "--caja", str(k)], cwd=RAIZ,
                       capture_output=True, text=True)
    m = re.search(r"Umbrales elegidos: entra (-?\d+), sale (-?\d+)", r.stdout)
    return c, k, (int(m.group(1)), int(m.group(2))) if m else None


def main():
    with Pool(4) as pool:
        res = pool.map(umbrales, [(c, k) for c in COMISIONES for k in CAJAS])
    d = {(c, k): u for c, k, u in res}
    carpetas = {d_: f"e{d_[0]}_s{d_[1]}" for d_ in set(d.values()) if d_}
    hay = set(os.listdir(os.path.join(RAIZ, "bitstreams", "contingencia")))
    L = ["Umbrales que elige tools/retune.py (entra, sale) para cada comision y caja, y el juego de bitstreams/contingencia/",
         "Generado por tools/p8/grilla.py. 'actuales' = (3, 0), los de bitstreams/ (no hay que cambiar nada).", "",
         "| Comision | " + " | ".join(f"Caja {k:,}".replace(",", " ") for k in CAJAS) + " |",
         "|---|" + "---|" * len(CAJAS)]
    for c in COMISIONES:
        celdas = []
        for k in CAJAS:
            u = d[(c, k)]
            if u is None:
                celdas.append("error")
            elif u == (3, 0):
                celdas.append("actuales")
            else:
                n = carpetas[u]
                celdas.append(f"`{n}`" + ("" if n in hay else " (no construido)"))
        L.append(f"| {c} | " + " | ".join(celdas) + " |")
    faltan = sorted(n for u, n in carpetas.items() if u != (3, 0) and n not in hay)
    L += ["", "Juegos que aparecen y no estan construidos: " + (", ".join(faltan) if faltan else "ninguno")]
    texto = "\n".join(L) + "\n"
    print(texto, end="")
    os.makedirs(os.path.join(RAIZ, "docs", "mediciones", "p8"), exist_ok=True)
    with open(os.path.join(RAIZ, "docs", "mediciones", "p8", "retune_grilla.txt"), "w", newline="\n") as f:
        f.write(texto)


if __name__ == "__main__":
    main()
