#!/usr/bin/env python3
"""busqueda.py: mejor respuesta a un campo de rivales que también operan reversión (tarea B).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Corre el comando hipotesis del arnés con el campo "variados" (ref/torneo_b/torneo_b.c:
todos los rivales son reversiones, de las 25 parametrizaciones de la clase) y con el
mixto, para una grilla de la regla de reversión (memoria de la media, umbral de entrada y
de salida) y de zscore, contra max_media. Es exploración: semilla 0.

Uso: python3 ref/torneo_b/busqueda.py --largo 2000 [--interior | --parada] [--campo variados]
Salida: docs/mediciones/generador_b/busqueda_n<largo>_<campo>[_interior|_parada].txt
"""
import argparse
import collections
import os
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARNES = os.path.join(RAIZ, "build", "torneo_b", "arnes")


def grilla():
    c = []
    for k in (4, 5, 6):
        for e in (2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
            for x in (-1.0, -0.5, 0.0, 0.5):
                c.append((f"reversion k={k} entra {e:g} sale {x:+g}", f"param:k={k},E={int(e * (1 << k))},X={int(x * (1 << k))}"))
    for kd in (6, 7):
        for num in (5, 6, 7):
            c.append((f"zscore z {num / 4:g} (32 y {1 << kd})", f"zscore:km=5,kd={kd},num={num},den=4"))
    return c


def correr(cands, largo, semilla, campo, extra, tsv):
    env = dict(os.environ, RETORNO_CAMPO=campo) if campo not in ("ingenuo", "mixto", "fuerte") else dict(os.environ)
    cmd = [ARNES, "hipotesis", "--largo", str(largo), "--semilla", str(semilla), "--campo", campo,
           "--candidatos", ";".join(["max_media"] + [s for _, s in cands]), "--tsv", tsv] + extra
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, env=env)
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
    ap.add_argument("--campo", default="variados")
    ap.add_argument("--interior", action="store_true")
    ap.add_argument("--parada", action="store_true")
    a = ap.parse_args(argv)
    extra = (["--interior"] if a.interior else []) + (["--parada"] if a.parada else [])
    suf = "_interior" if a.interior else "_parada" if a.parada else ""
    os.makedirs(os.path.join(RAIZ, "build", "torneo_b"), exist_ok=True)
    cands = grilla()
    filas = []
    for i in range(0, len(cands), 40):
        parte = cands[i:i + 40]
        tsv = os.path.join(RAIZ, "build", "torneo_b", f"b_n{a.largo}_s{a.semilla}_{a.campo}{suf}_{i}.tsv")
        d = correr(parte, a.largo, a.semilla, a.campo, extra, tsv)
        ref = d[("evidencia", "max_media")]
        for nombre, spec in parte:
            filas.append((nombre, spec, d[("evidencia", spec[:95])], d[("plausibles", spec[:95])], d[("remuestreo", spec[:95])]))
    vista = "interiores" if a.interior else "parada" if a.parada else "todas las series"
    lineas = [f"Tarea B: la regla de reversion y zscore contra max_media en el campo {a.campo}, G = 10. Rondas de {a.largo} ticks, "
              f"semilla {a.semilla}, {vista}.", f"Generado por ref/torneo_b/busqueda.py {' '.join(argv if argv is not None else sys.argv[1:])}.",
              f"max_media en la evidencia: H3a {ref['h3a_media']:.3f}, H3b {ref['h3b_media']:.3f}. Diferencias pareadas (+-ee).",
              "Umbrales en unidades de precio sobre o bajo la media exponencial (k = memoria 2^k).", "",
              f"{'candidata':34s} | {'dH3a evid':>9s} {'+-':>5s} {'dH3b evid':>9s} {'+-':>5s} | {'dH3a plaus':>10s} {'dH3b plaus':>10s} | "
              f"{'dH3a rem':>8s} | {'dp5 H3a':>7s} | {'ordenes':>7s}"]
    filas.sort(key=lambda f: -(f[2]["d_h3a"] + f[2]["d_h3b"]))
    for nombre, spec, ev, pl, rm in filas:
        lineas.append(f"{nombre:34s} | {ev['d_h3a']:+9.3f} {ev['d_h3a_ee']:5.3f} {ev['d_h3b']:+9.3f} {ev['d_h3b_ee']:5.3f} | "
                      f"{pl['d_h3a']:+10.3f} {pl['d_h3b']:+10.3f} | {rm['d_h3a']:+8.3f} | {ev['d_h3a_c_p5']:+7.3f} | {ev['ordenes']:7.1f}")
    mejoran = [f for f in filas if f[2]["d_h3a"] > 2 * f[2]["d_h3a_ee"] and f[2]["d_h3b"] > 2 * f[2]["d_h3b_ee"]]
    lineas.append("")
    lineas.append(f"Candidatas que mejoran H3a y H3b en mas de dos errores en la evidencia: {len(mejoran)}"
                  + (": " + "; ".join(f[0] for f in mejoran) if mejoran else ""))
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    salida = os.path.join(RAIZ, "docs", "mediciones", "generador_b", f"busqueda_n{a.largo}_{a.campo}{suf}.txt")
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    with open(salida, "w", newline="\n") as f:
        f.write(texto)


if __name__ == "__main__":
    main()
