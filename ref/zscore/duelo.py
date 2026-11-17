#!/usr/bin/env python3
"""duelo.py: probabilidad de ganarle cabeza a cabeza a una referencia, por ronda y por competencia.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Para cada candidata y cada conjunto de series corre el comando detalle del arnés
(build/zscore/arnes) para la candidata y la referencia sobre las mismas series y cuenta:

  ronda        fracción de series en que la candidata termina con más patrimonio
               que la referencia (los empates se informan aparte)
  competencia  fracción de tríos de series (consecutivas, sin repetir) en que la
               suma de los tres patrimonios de la candidata es mayor
  2 de 3       fracción de tríos en que la candidata gana al menos dos de las tres rondas

con su error estándar binomial. A 20 000 ticks se informan todas las series y las
interiores (precio siempre entre 21 y 249).

Uso:
    python3 ref/zscore/duelo.py --largo 2000 --semilla 0 --candidatas "zscore;zscore:km=5,kd=7,num=6,den=4"
    python3 ref/zscore/duelo.py --largo 20000 --semilla 4 --referencia max_media --candidatas zscore
"""
import argparse
import math
import os
import struct
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARNES = os.path.join(RAIZ, "build", "zscore", "arnes")
SERIES = os.environ.get("RETORNO_SERIES", os.path.join(RAIZ, "build", "zscore", "series"))
PLAUSIBLES = ["modelo", "modelo_vecino", "dos_componentes", "cambio_volatilidad"]
ESTRES = ["paseo", "tendencia", "reversion", "saltos", "cambio_de_caracter", "volatil", "nivel_bajo"]


def patrimonios(spec, ruta):
    out = subprocess.run([ARNES, "detalle", "--estrategia", spec, "--lote", ruta], check=True,
                         capture_output=True, text=True).stdout.split("\n")
    return [int(l.split()[0]) for l in out if l.strip()]


def interiores(ruta):
    with open(ruta, "rb") as f:
        ns, n = struct.unpack("<ii", f.read(8))
        datos = f.read()
    return [min(datos[i * n:(i + 1) * n]) >= 21 and max(datos[i * n:(i + 1) * n]) <= 249 for i in range(ns)]


def frac(k, n):
    p = k / n if n else float("nan")
    return p, math.sqrt(p * (1 - p) / n) if n else float("nan")


def duelo(wc, wr):
    n = len(wc)
    gana = sum(a > b for a, b in zip(wc, wr))
    empata = sum(a == b for a, b in zip(wc, wr))
    t = n // 3
    comp = sum(sum(wc[3 * i:3 * i + 3]) > sum(wr[3 * i:3 * i + 3]) for i in range(t))
    dos = sum(sum(a > b for a, b in zip(wc[3 * i:3 * i + 3], wr[3 * i:3 * i + 3])) >= 2 for i in range(t))
    return n, frac(gana, n), empata / n if n else 0, t, frac(comp, t), frac(dos, t)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--largo", type=int, default=2000)
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--referencia", default="max_media")
    ap.add_argument("--candidatas", required=True, help="separadas por ';'")
    ap.add_argument("--salida")
    a = ap.parse_args(argv)
    cands = a.candidatas.split(";")
    conjuntos = [("remuestreo", ["remuestreo"]), ("plausibles", PLAUSIBLES), ("estres", ESTRES)]
    if a.largo == 2000:
        conjuntos.insert(0, ("bloques de practica", None))
    lineas = [f"Duelo cabeza a cabeza contra {a.referencia}: rondas de {a.largo} ticks, semilla {a.semilla}.",
              f"Generado por ref/zscore/duelo.py {' '.join(argv if argv is not None else sys.argv[1:])}.",
              "ronda: P(candidata > referencia) en una serie. competencia: P(suma de tres rondas mayor). "
              "2 de 3: P(gana al menos dos rondas). +-: error estandar binomial.", ""]
    vistas = ["todas"] + (["interiores"] if a.largo == 20000 else [])
    for nombre, familias in conjuntos:
        rutas = [os.path.join(SERIES, "bloques_n2000.bin")] if familias is None else \
            [os.path.join(SERIES, f"{f}_s{a.semilla}_n{a.largo}.bin") for f in familias]
        ref, cand, dentro = [], {c: [] for c in cands}, []
        for r in rutas:
            ref += patrimonios(a.referencia, r)
            for c in cands:
                cand[c] += patrimonios(c, r)
            dentro += interiores(r)
        for vista in vistas:
            idx = [i for i in range(len(ref)) if vista == "todas" or dentro[i]]
            lineas.append(f"--- {nombre}, {vista}: {len(idx)} series ---")
            lineas.append(f"{'candidata':40s} {'ronda':>6s} {'+-':>5s} {'empate':>6s} | {'tríos':>5s} {'compet.':>7s} {'+-':>5s} "
                          f"{'2 de 3':>6s} {'+-':>5s} | {'W media':>8s} {'W ref':>8s}")
            for c in cands:
                wc = [cand[c][i] for i in idx]
                wr = [ref[i] for i in idx]
                n, (pr, er), emp, t, (pc, ec), (p2, e2) = duelo(wc, wr)
                lineas.append(f"{c:40s} {100 * pr:5.1f}% {100 * er:4.1f} {100 * emp:5.1f}% | {t:5d} {100 * pc:6.1f}% {100 * ec:4.1f} "
                              f"{100 * p2:5.1f}% {100 * e2:4.1f} | {sum(wc) / n:8.0f} {sum(wr) / n:8.0f}")
            lineas.append("")
    texto = "\n".join(lineas)
    print(texto)
    if a.salida:
        os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
        with open(a.salida, "w", newline="\n") as f:
            f.write(texto + "\n")


if __name__ == "__main__":
    main()
