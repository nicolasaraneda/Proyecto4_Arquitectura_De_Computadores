#!/usr/bin/env python3
"""frontera.py: los candidatos a algoritmo final, sobre la frontera entre media y percentil 5.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Evalúa los candidatos de ref/candidatos.py con muestras grandes y con dos
semillas:

  semilla 0   la de exploración: con ella se eligieron bandas y protecciones.
  semilla 1   reservada. Ninguna decisión se tomó mirándola. Es la que vale.

Conjuntos: los 10 bloques de práctica, 5000 remuestreos, las familias
plausibles (2500 series de cada una) y las de estrés (1000 de cada una). Por
cada candidato: media, diferencia pareada contra la regla base con su error
estándar, percentil 5, peor caso y fracción de series en que supera a comprar
y mantener. `act` es el porcentaje de series en que la guardia o el tope
llegaron a actuar.

    python3 ref/frontera.py                 # las dos semillas
    python3 ref/frontera.py --semilla 1
    python3 ref/frontera.py --detalle       # además, una tabla por familia

Usa el motor en C, que ref/test_candidatos.py valida contra la referencia.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import candidatos       # noqa: E402
import market           # noqa: E402
import motor            # noqa: E402
import series           # noqa: E402

N_REM, N_PLAUSIBLE, N_ESTRES = 5000, 2500, 1000
DEGENERADAS = ("plana", "borde_bajo", "borde_alto")      # solo prueban la aritmética
EXTRA = {
    "activo": (dict(E=64, X=16), "entra 2 bajo la media, sale medio punto sobre ella"),
    "base_guardia": (dict(E=128, X=0, **candidatos.SALTOS, **candidatos.GUARDIA), "regla base con saltos y guardia"),
    "base_tope": (dict(E=128, X=0, **candidatos.PROTECCION), "regla base con saltos, guardia y tope"),
    "base_fuerte": (dict(E=128, X=0, **candidatos.PROTECCION_FUERTE), "regla base con guardia sensible y tope de 25 %"),
    "prud_guardia": (dict(E=192, X=-32, **candidatos.SALTOS, **candidatos.GUARDIA), "prudente con saltos y guardia"),
    "kalman_base": (dict(est=1, E=250, X=-40), "Kalman de dos estados con bandas equivalentes a la regla base"),
}


def estadisticos(filas, base, byh):
    ws = [f["w"] for f in filas]
    n = len(ws)
    dif = [a - b["w"] for a, b in zip(ws, base)]
    m = sum(dif) / n
    ee = (sum((v - m) ** 2 for v in dif) / max(1, n - 1) / n) ** 0.5
    orden = sorted(ws)
    return dict(n=n, media=sum(ws) / n, dif=m, ee=ee, p5=orden[min(n - 1, int(0.05 * n))], peor=orden[0],
                sobre_byh=sum(w > b for w, b in zip(ws, byh)) / n,
                act=sum(f["topes"] > 0 or f["guardia"] > 0 for f in filas) / n)


def texto(e, con_dif=True):
    dif = f"{e['dif']:+6.0f} {e['ee']:4.0f}" if con_dif else " " * 11
    return f"{e['media']:6.0f} {dif} {e['p5']:5d} {e['peor']:5d} {100 * e['sobre_byh']:3.0f}%"


def evaluar(semilla, nombres, detalle=False):
    grupos = [("bloques", [("bloques", None)]),
              ("remuestreo", [("remuestreo", N_REM)]),
              ("plausibles", [(f, N_PLAUSIBLE) for f in series.PLAUSIBLES]),
              ("estres", [(f, N_ESTRES) for f in series.ESTRES if f not in DEGENERADAS])]
    rutas = {f: motor.conjunto(f, c, semilla=semilla) for _, lista in grupos for f, c in lista}
    byh = {}
    for f, ruta in rutas.items():
        byh[f] = [market.comprar_y_mantener(s) for s in motor.leer(ruta)]
    todos = dict(candidatos.CANDIDATOS)
    for k, (par, desc) in EXTRA.items():
        todos[k] = (par, None, desc)
    res = {n: {f: motor.detalle(ruta, todos[n][0]) for f, ruta in rutas.items()} for n in nombres}
    base = res["base"]

    print(f"\n=== Semilla {semilla} ({'exploracion' if semilla == 0 else 'reservada'}) ===")
    cab = f"{'media':>6s} {'dif':>6s} {'+-ee':>4s} {'p5':>5s} {'peor':>5s} {'>B&H':>4s}"
    print(f"{'candidato':15s} | {'bloques: media, peor':>20s} | {'remuestreo (' + str(N_REM) + ')':^35s} | "
          f"{'plausibles (' + str(4 * N_PLAUSIBLE) + ')':^35s} | {'estres (' + str(7 * N_ESTRES) + ')':^35s} | act rem, pla")
    print(f"{'':15s} | {'':20s} | {cab} | {cab} | {cab} |")
    tabla = {}
    for n in nombres:
        fila = {}
        for g, lista in grupos:
            filas = [x for f, _ in lista for x in res[n][f]]
            fb = [x for f, _ in lista for x in base[f]]
            fila[g] = estadisticos(filas, fb, [b for f, _ in lista for b in byh[f]])
        tabla[n] = fila
        b = fila["bloques"]
        print(f"{n:15s} | {b['media']:8.0f} {b['dif']:+5.0f} {b['peor']:6d} | {texto(fila['remuestreo'])} | "
              f"{texto(fila['plausibles'])} | {texto(fila['estres'])} | {100 * fila['remuestreo']['act']:3.0f}% "
              f"{100 * fila['plausibles']['act']:3.0f}%")

    print(f"\nFamilias de estres, semilla {semilla}: media, percentil 5 y peor caso")
    estres = [f for f in series.ESTRES if f not in DEGENERADAS]
    print(f"{'candidato':15s} | " + " | ".join(f"{f[:18]:^18s}" for f in estres))
    for n in nombres:
        celdas = []
        for f in estres:
            e = estadisticos(res[n][f], base[f], byh[f])
            celdas.append(f"{e['media']:6.0f} {e['p5']:5d} {e['peor']:5d}")
        print(f"{n:15s} | " + " | ".join(celdas))
    if detalle:
        print(f"\nFamilias plausibles, semilla {semilla}: media, diferencia con la base, error, percentil 5, peor, >B&H")
        print(f"{'candidato':15s} | " + " | ".join(f"{f:^35s}" for f in series.PLAUSIBLES))
        for n in nombres:
            print(f"{n:15s} | " + " | ".join(texto(estadisticos(res[n][f], base[f], byh[f])) for f in series.PLAUSIBLES))
    return tabla


def main(argv=None):
    ap = argparse.ArgumentParser(description="Candidatos sobre la frontera entre media y percentil 5")
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--detalle", action="store_true")
    ap.add_argument("--candidatos", default="base,max_media,guardia,guardia_tope,prudente,kalman,kalman_base,"
                                             "activo,base_guardia,base_tope,base_fuerte,prud_guardia")
    a = ap.parse_args(argv)
    nombres = a.candidatos.split(",")
    if "base" not in nombres:
        nombres.insert(0, "base")
    print("Candidatos (parametros distintos de la regla base):")
    for n in nombres:
        par, desc = (candidatos.CANDIDATOS[n][0], candidatos.CANDIDATOS[n][2]) if n in candidatos.CANDIDATOS else EXTRA[n]
        print(f"  {n:15s} {' '.join(f'{k}={v}' for k, v in par.items()):58s} {desc}")
    for semilla in ([a.semilla] if a.semilla is not None else [0, 1]):
        evaluar(semilla, nombres, a.detalle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
