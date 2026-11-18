#!/usr/bin/env python3
"""validar.py: el evaluador en C (evaluar.c) contra las referencias en Python.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.
Patrimonio y órdenes idénticos en la serie Meta, en sus ventanas y en paseos al azar
normalizados, para cada familia de estrategias. Uso: python3 ref/cotas/validar.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402
import cotas  # noqa: E402
import trader  # noqa: E402
import zscore  # noqa: E402
import planb  # noqa: E402

ESTR = [
    ("espera", "cotas", (0, 0, 0, 0, 0, 178), lambda: cotas.Cotas("espera")),
    ("compra", "cotas", (1, 0, 0, 0, 0, 178), lambda: cotas.Cotas("compra")),
    ("compra_b40", "cotas", (1, 0, 0, 40, 0, 178), lambda: cotas.Cotas("compra", banda=40)),
    ("parte20_a3_b2", "cotas", (2, 3, 2, 0, 20, 178), lambda: cotas.Cotas("parte", a=3, b=2, k=20)),
    ("umbral150_b25", "cotas", (3, 1, 1, 25, 0, 150), lambda: cotas.Cotas("umbral", a=1, b=1, banda=25, u=150)),
    ("max_media", "media", (5, 3, 0), lambda: trader.MaxMedia()),
    ("regla_base", "media", (5, 4, 0), lambda: trader.ReglaBase()),
    ("zscore", "zscore", (5, 6, 5, 2, 64, 0), lambda: zscore.ZScore()),
    ("rango140_215", "rango", (140, 215, 0, 0), lambda: planb.Rango(140, 215)),
    ("rango130_200_i170", "rango", (130, 200, 1, 170), lambda: planb.Rango(130, 200, 1, 170)),
    ("salto3_60_baja", "salto", (3, 60, 0), lambda: planb.Salto(3, 60, 0)),
    ("salto5_200_sube", "salto", (5, 200, 1), lambda: planb.Salto(5, 200, 1)),
    ("tendencia4_8_1", "tendencia", (4, 8, 1), lambda: planb.Tendencia(4, 8, 1)),
    ("nada", "nada", (), None),
    ("siempre", "siempre", (), None),
]


def python(fab, p):
    import market
    if fab is None:
        return None
    m = trader.correr(p, fab())
    return m.w, m.ordenes


def main():
    rnd = random.Random(11)
    meta = cotas.leer(os.path.join(comun.RAIZ, "data", "practica_meta.csv"))
    ventanas = [meta]
    for _ in range(40):
        n = rnd.choice((300, 2000, 5000))
        i = rnd.randrange(0, len(meta) - n)
        ventanas.append(comun.normalizar(meta[i:i + n]))
    for _ in range(40):
        x, v = 0.0, []
        for _ in range(rnd.choice((500, 2000))):
            x += rnd.gauss(0, 1)
            v.append(x)
        ventanas.append(comun.normalizar(v))
    nombres, filas, ords = comun.evaluar([(n, t, p) for n, t, p, _ in ESTR], ventanas, "validar", ordenes=True)
    fallas = 0
    for j, (n, t, p, fab) in enumerate(ESTR):
        if fab is None:
            continue
        malos = sum(1 for v, f, o in zip(ventanas, filas, ords) if python(fab, v) != (f[j], o[j]))
        fallas += malos
        print(("PASS" if malos == 0 else "FAIL") + f" {n}: {len(ventanas) - malos} de {len(ventanas)} ventanas con patrimonio y ordenes identicos")
    print(f"serie Meta completa: " + ", ".join(f"{n} {w}" for n, w in zip(nombres, filas[0])))
    print("RESULTADO", "PASS" if fallas == 0 else "FAIL")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
