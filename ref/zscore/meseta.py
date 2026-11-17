#!/usr/bin/env python3
"""meseta.py: sensibilidad de zscore al umbral y a las memorias, en puntos del torneo.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Corre el comando hipotesis del arnés (build/zscore/arnes) para una grilla de
zscore: umbral z de 1,0 a 3,0 cada 0,25 (num/4), memoria de la media km de 4
a 6 y de la desviación kd de 5 a 7, con w = 64. Todas contra max_media, sobre
el conjunto evidencia (remuestreos y plausibles), campo mixto con 10 rivales.

Uso:
    python3 ref/zscore/meseta.py --largo 2000 --semilla 0
    python3 ref/zscore/meseta.py --largo 20000 --semilla 0 --interior
    python3 ref/zscore/meseta.py --largo 20000 --semilla 0 --parada

Por cada (km, kd, z) informa: patrimonio medio en la evidencia y su diferencia
con max_media (+-ee), lo mismo en remuestreos, plausibles y estrés, puntos
esperados H3a y H3b contra max_media (+-ee), y el percentil 5 de H3a de la
competencia de tres rondas contra el de max_media. La salida queda en
docs/mediciones/zscore/meseta_n<largo>_s<semilla>[_interior|_parada].txt.
"""
import argparse
import collections
import os
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARNES = os.path.join(RAIZ, "build", "zscore", "arnes")
SALIDA = os.path.join(RAIZ, "docs", "mediciones", "zscore")
ZS = list(range(4, 13))          # z = num / 4: 1,00 a 3,00


def spec(km, kd, num):
    return f"zscore:km={km},kd={kd},num={num},den=4"


def correr(candidatos, largo, semilla, extra, tsv):
    cmd = [ARNES, "hipotesis", "--largo", str(largo), "--semilla", str(semilla),
           "--candidatos", ";".join(["max_media"] + candidatos), "--tsv", tsv] + extra
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = collections.defaultdict(dict)
    with open(tsv) as f:
        next(f)
        for linea in f:
            _, _, _, conjunto, cand, clave, valor = linea.rstrip("\n").split("\t")
            d[(conjunto, cand)][clave] = float(valor)
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--largo", type=int, default=2000)
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--interior", action="store_true")
    ap.add_argument("--parada", action="store_true")
    a = ap.parse_args(argv)
    if a.semilla not in (0,):
        print("AVISO: la meseta es exploracion y se corre con la semilla 0 (T128)", file=sys.stderr)
    extra = (["--interior"] if a.interior else []) + (["--parada"] if a.parada else [])
    sufijo = "_interior" if a.interior else "_parada" if a.parada else ""
    os.makedirs(SALIDA, exist_ok=True)
    os.makedirs(os.path.join(RAIZ, "build", "zscore"), exist_ok=True)
    filas = []
    for km in (4, 5, 6):
        cands = [spec(km, kd, num) for kd in (5, 6, 7) for num in ZS]
        tsv = os.path.join(RAIZ, "build", "zscore", f"meseta_km{km}_n{a.largo}_s{a.semilla}{sufijo}.tsv")
        d = correr(cands, a.largo, a.semilla, extra, tsv)
        for kd in (5, 6, 7):
            for num in ZS:
                c = spec(km, kd, num)
                ev = d[("evidencia", c)]
                filas.append((km, kd, num, ev, d[("remuestreo", c)], d[("plausibles", c)], d[("estres", c)]))
        ref = d[("evidencia", "max_media")]
    vista = "interiores" if a.interior else "parada" if a.parada else "todas las series"
    lineas = [f"Meseta de zscore contra max_media: rondas de {a.largo} ticks, semilla {a.semilla}, {vista}.",
              f"Generado por ref/zscore/meseta.py {' '.join(argv if argv is not None else sys.argv[1:])}.",
              "Conjunto evidencia (remuestreos y plausibles), campo mixto, G = 10. Diferencias contra max_media, pareadas.",
              f"max_media: patrimonio medio {ref['h1_media']:.0f}, H3a {ref['h3a_media']:.3f}, H3b {ref['h3b_media']:.3f}, "
              f"p5 de H3a en tres rondas {ref['h3a_c_p5']:.3f}.",
              "",
              f"{'km':>2s} {'kd':>2s} {'z':>5s} | {'W evid':>7s} {'dif':>6s} {'+-ee':>4s} | {'dW rem':>6s} {'dW pla':>6s} {'dW est':>7s} | "
              f"{'dH3a':>7s} {'+-ee':>5s} {'dH3b':>7s} {'+-ee':>5s} | {'dp5 H3a':>7s} {'+-ee':>5s} | {'ordenes':>7s}"]
    mejor = None
    for km, kd, num, ev, rem, pla, est in filas:
        z = num / 4
        lineas.append(f"{km:2d} {kd:2d} {z:5.2f} | {ev['h1_media']:7.0f} {ev['h1_dif']:+6.0f} {ev['h1_dif_ee']:4.0f} | "
                      f"{rem['h1_dif']:+6.0f} {pla['h1_dif']:+6.0f} {est['h1_dif']:+7.0f} | "
                      f"{ev['d_h3a']:+7.3f} {ev['d_h3a_ee']:5.3f} {ev['d_h3b']:+7.3f} {ev['d_h3b_ee']:5.3f} | "
                      f"{ev['d_h3a_c_p5']:+7.3f} {ev['d_h3a_c_p5_ee']:5.3f} | {ev['ordenes']:7.1f}")
        if mejor is None or ev["d_h3a"] > mejor[3]["d_h3a"]:
            mejor = (km, kd, num, ev)
        if num == ZS[-1]:
            lineas.append("")
    km, kd, num, ev = mejor
    lineas.append(f"Mejor dH3a de la grilla: km={km}, kd={kd}, z={num / 4:.2f}: {ev['d_h3a']:+.3f} +- {ev['d_h3a_ee']:.3f} "
                  f"(H3b {ev['d_h3b']:+.3f} +- {ev['d_h3b_ee']:.3f}).")
    texto = "\n".join(lineas) + "\n"
    ruta = os.path.join(SALIDA, f"meseta_n{a.largo}_s{a.semilla}{sufijo}.txt")
    with open(ruta, "w", newline="\n") as f:
        f.write(texto)
    print(texto, end="")
    print(f"(guardado en {os.path.relpath(ruta, RAIZ)})")


if __name__ == "__main__":
    main()
