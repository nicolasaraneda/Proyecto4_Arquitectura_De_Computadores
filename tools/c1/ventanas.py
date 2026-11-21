#!/usr/bin/env python3
"""ventanas.py: escribe ventanas reales de 20 000 minutos, normalizadas como las de la competencia.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee los minutos de $P4_DATOS/minuto/EMPRESA.csv (no están en el repositorio: son datos de mercado
de una cuenta) y escribe CSV "tick,price" con la normalización del profesor (ref/cotas/comun.py:
mínimo 100, máximo 255). Los inicios se sortean con una semilla fija, parejo entre las cinco
empresas. Imprime la ruta de cada archivo.

Uso: python3 tools/c1/ventanas.py CARPETA --n 200 [--semilla 21] [--largo 20000]
"""
import argparse
import os
import random
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref", "cotas"))
import comun  # noqa: E402

EMPRESAS = ("META", "AAPL", "NFLX", "AMD", "TSLA")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("carpeta")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--semilla", type=int, default=21)
    ap.add_argument("--largo", type=int, default=20000)
    a = ap.parse_args()
    datos = os.path.expanduser(os.environ.get("P4_DATOS", "~/proyectos/datos_p4"))
    os.makedirs(a.carpeta, exist_ok=True)
    rng = random.Random(a.semilla)
    series = {}
    for e in EMPRESAS:
        with open(os.path.join(datos, "minuto", e + ".csv")) as f:
            series[e] = [float(l.split(",")[2]) for l in f.read().splitlines()[1:]]
    for k in range(a.n):
        e = EMPRESAS[k % len(EMPRESAS)]
        i = rng.randrange(len(series[e]) - a.largo)
        p = comun.normalizar(series[e][i:i + a.largo])
        ruta = os.path.join(a.carpeta, f"{e.lower()}_{i}.csv")
        with open(ruta, "w", newline="\n") as f:
            f.write("tick,price\n" + "".join(f"{t},{x}\n" for t, x in enumerate(p)))
        print(ruta)


if __name__ == "__main__":
    main()
