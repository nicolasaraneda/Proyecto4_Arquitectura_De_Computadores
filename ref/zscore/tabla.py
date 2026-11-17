#!/usr/bin/env python3
"""tabla.py: candidatas con nombre corto contra max_media, en puntos del torneo y patrimonio.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Corre el comando hipotesis del arnés (build/zscore/arnes) con una lista fija de
candidatas (zscore solo, fondos de tres gestores zscore y el fondo de max_media)
y escribe una tabla compacta por conjunto: patrimonio medio y su diferencia
pareada con max_media, puntos H3a y H3b contra max_media y percentil 5 de H3a
en la competencia de tres rondas. Con --campo cambia el campo de rivales.

Uso:
    python3 ref/zscore/tabla.py --largo 2000 --semilla 0
    python3 ref/zscore/tabla.py --largo 20000 --semilla 0 --interior
    python3 ref/zscore/tabla.py --largo 2000 --semilla 0 --campo reversores
"""
import argparse
import collections
import os
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARNES = os.path.join(RAIZ, "build", "zscore", "arnes")

F = "fondoz:c=5,w0=6,w1=5,w2=5"
APRENDE = "m=2,v=9,mg=5,d=4,pp=1,vt=8"


def g(km, kd, num):
    return f"zscore:km~{km}/kd~{kd}/den~4/num~{num}"


CANDIDATAS = [
    ("max_media", "max_media"),
    ("zscore de Vicente (z 2,5; 32 y 64)", "zscore"),
    ("zscore z 2,0 (32 y 64)", "zscore:km=5,kd=6,num=8,den=4"),
    ("zscore z 1,75 (32 y 64)", "zscore:km=5,kd=6,num=7,den=4"),
    ("zscore z 1,5 (32 y 128), centro de la meseta", "zscore:km=5,kd=7,num=6,den=4"),
    ("fondo zscore 2,0/2,25/2,5, mayoria", f"{F},vt=8,g0={g(5, 6, 9)},g1={g(5, 6, 8)},g2={g(5, 6, 10)}"),
    ("fondo zscore 2,0/2,25/2,5, pesos aprendidos", f"{F},{APRENDE},g0={g(5, 6, 9)},g1={g(5, 6, 8)},g2={g(5, 6, 10)}"),
    ("fondo zscore 1,25/1,5/1,75, mayoria", f"{F},vt=8,g0={g(5, 7, 6)},g1={g(5, 7, 5)},g2={g(5, 7, 7)}"),
    ("fondo zscore 1,25/1,5/1,75, aprendidos", f"{F},{APRENDE},g0={g(5, 7, 6)},g1={g(5, 7, 5)},g2={g(5, 7, 7)}"),
    ("fondo max_media + zscore 2,0 + zscore 1,5", f"{F},vt=8,g0=cand:max_media,g1={g(5, 6, 8)},g2={g(5, 7, 6)}"),
    ("fondo de R1 (fondo_min, gestores de reversion)", "cand:fondoz_min"),
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--largo", type=int, default=2000)
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--interior", action="store_true")
    ap.add_argument("--parada", action="store_true")
    ap.add_argument("--campo", default="mixto")
    ap.add_argument("--salida")
    a = ap.parse_args(argv)
    extra = (["--interior"] if a.interior else []) + (["--parada"] if a.parada else [])
    tsv = os.path.join(RAIZ, "build", "zscore", f"tabla_n{a.largo}_s{a.semilla}_{a.campo}{'_i' if a.interior else ''}{'_p' if a.parada else ''}.tsv")
    os.makedirs(os.path.dirname(tsv), exist_ok=True)
    cmd = [ARNES, "hipotesis", "--largo", str(a.largo), "--semilla", str(a.semilla), "--campo", a.campo,
           "--candidatos", ";".join(s for _, s in CANDIDATAS), "--tsv", tsv] + extra
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    d = collections.defaultdict(dict)
    with open(tsv) as f:
        next(f)
        for linea in f:
            _, _, _, conjunto, cand, clave, valor = linea.rstrip("\n").split("\t")
            d[(conjunto, cand)][clave] = float(valor)
    vista = "interiores" if a.interior else "parada" if a.parada else "todas las series"
    lineas = [f"zscore y fondos de gestores zscore contra max_media: rondas de {a.largo} ticks, semilla {a.semilla}, {vista}, "
              f"campo {a.campo}, G = 10.",
              f"Generado por ref/zscore/tabla.py {' '.join(argv if argv is not None else sys.argv[1:])}.", ""]
    for conjunto in ("evidencia", "remuestreo", "plausibles", "estres"):
        ref = d[(conjunto, "max_media")]
        if not ref:
            continue
        lineas.append(f"--- {conjunto}: {int(ref['n'])} series. max_media: W {ref['h1_media']:.0f}, H3a {ref['h3a_media']:.3f}, "
                      f"H3b {ref['h3b_media']:.3f}, p5 de H3a en tres rondas {ref['h3a_c_p5']:.3f} ---")
        lineas.append(f"{'candidata':48s} {'W':>6s} {'dif':>6s} {'+-ee':>4s} | {'dH3a':>7s} {'+-ee':>5s} {'dH3b':>7s} {'+-ee':>5s} | "
                      f"{'dp5 H3a':>7s} {'+-ee':>5s} | {'ordenes':>7s}")
        for nombre, spec in CANDIDATAS[1:]:
            r = d[(conjunto, spec[:95])]  # el arnés guarda el nombre con 95 caracteres a lo más
            lineas.append(f"{nombre:48s} {r['h1_media']:6.0f} {r['h1_dif']:+6.0f} {r['h1_dif_ee']:4.0f} | {r['d_h3a']:+7.3f} "
                          f"{r['d_h3a_ee']:5.3f} {r['d_h3b']:+7.3f} {r['d_h3b_ee']:5.3f} | {r['d_h3a_c_p5']:+7.3f} "
                          f"{r['d_h3a_c_p5_ee']:5.3f} | {r['ordenes']:7.1f}")
        lineas.append("")
    lineas.append("Especificaciones:")
    lineas += [f"  {n}: {s}" for n, s in CANDIDATAS]
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    if a.salida:
        with open(a.salida, "w", newline="\n") as f:
            f.write(texto)


if __name__ == "__main__":
    main()
