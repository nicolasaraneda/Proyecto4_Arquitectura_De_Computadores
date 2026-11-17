#!/usr/bin/env python3
"""trozos.py: zscore contra max_media según el largo de trozo del remuestreo, y con ajuste en una
mitad de la práctica y evaluación en la otra.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Parte 1. El remuestreo del protocolo (ref/series.py, remuestreo) arma series de 2000
ticks con trozos de 100 incrementos de la práctica elegidos al azar. Aquí se repite la
comparación de zscore (z = 2,5, memorias 32 y 64) contra max_media con trozos de 10, 50,
100, 250, 1000 y 2000 incrementos, 1000 series por largo, y con todas las ventanas reales
contiguas de 2000 ticks de la práctica (cada 100 ticks).

Parte 2. Con trozos largos el remuestreo se parece cada vez más a la serie con que se
eligieron los parámetros, así que no distingue estructura de sobreajuste. Para separarlos:
se eligen los parámetros de las dos reglas en una mitad de la práctica (la mejor media en
sus 5 bloques de 2000, como se hizo con la serie completa) y se evalúan en la otra mitad,
con sus bloques y con remuestreos de trozos de 50, 250 y 1000 tomados solo de esa mitad.

Parte 3. Lo mismo de la parte 1 con series del modelo calibrado como base (6 series de
20 000 ticks de `modelo` y de `cambio_volatilidad`, semilla 9), para ver si el efecto del
largo del trozo es del método o de la serie de práctica. Y las razones de varianza a
horizontes largos, de la práctica y del modelo.

Parte 4 (con --puntos): los puntos del torneo con trozos de 50, 250 y 1000 (5000 series
de cada uno, campo mixto, G = 10), con build/zscore/arnes. Necesita make -C ref/zscore y
las series de la semilla 0 en build/zscore/series.

Uso: python3 ref/zscore/trozos.py [--puntos]   (unos 3 minutos con 12 procesos)
Salida: docs/mediciones/zscore/trozos.txt
"""
import math
import os
import random
import statistics
import struct
import subprocess
import sys
from multiprocessing import Pool

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
import market  # noqa: E402
import series  # noqa: E402
import trader  # noqa: E402
import zscore  # noqa: E402

N = 2000
REMUESTREOS = 1000


def crear(regla):
    tipo, kw = regla
    return zscore.ZScore(**kw) if tipo == "z" else trader.ReglaBase(**kw)


def w(args):
    precios, regla = args
    return trader.correr(precios, crear(regla)).w


def pareado(pool, lista, a, b):
    wa = pool.map(w, [(s, a) for s in lista], chunksize=8)
    wb = pool.map(w, [(s, b) for s in lista], chunksize=8)
    d = [x - y for x, y in zip(wa, wb)]
    n = len(d)
    m = sum(d) / n
    ee = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1) / n) if n > 1 else float("nan")
    gana = sum(x > 0 for x in d) / n
    return sum(wa) / n, sum(wb) / n, m, ee, gana


VICENTE = ("z", dict(km=5, kd=6, num=5, den=2))
MAX_MEDIA = ("r", dict(k=5, entra=3, sale=0))


def lote(base, largo, cuantos, semilla):
    rng = random.Random(semilla)
    return [series.remuestreo(base, N, rng, bloque=largo) for _ in range(cuantos)]


def main():
    practica = market.leer_serie(os.path.join(RAIZ, "tb", "practica.csv"))
    lineas = ["zscore (Vicente: z = 2,5, memorias 32 y 64) contra max_media segun el largo de trozo del remuestreo",
              "Generado por ref/zscore/trozos.py. Series de 2000 ticks. dif = zscore - max_media, pareada, +- error estandar",
              "entre series. Con trozos largos el error subestima la incertidumbre: todas las series salen de la misma",
              "serie de practica, que tiene 20 000 / trozo trozos distintos.", ""]
    with Pool(int(os.environ.get("PROCESOS", "12"))) as pool:
        lineas.append("=== Parte 1: remuestreo de la practica completa, 1000 series por largo (semilla 7) ===")
        lineas.append(f"{'trozo':>6s} {'trozos distintos':>16s} | {'zscore':>7s} {'max_media':>9s} {'dif':>6s} {'+-ee':>5s} {'gana':>6s}")
        for largo in (10, 50, 100, 250, 1000, 2000):
            r = pareado(pool, lote(practica, largo, REMUESTREOS, 7), VICENTE, MAX_MEDIA)
            marca = "  <- el del protocolo" if largo == 100 else ""
            lineas.append(f"{largo:6d} {19999 // largo:16d} | {r[0]:7.0f} {r[1]:9.0f} {r[2]:+6.0f} {r[3]:5.0f} {100 * r[4]:5.1f}%{marca}")
        vent = [practica[i:i + N] for i in range(0, len(practica) - N + 1, 100)]
        r = pareado(pool, vent, VICENTE, MAX_MEDIA)
        lineas.append(f"{'ventanas reales contiguas':>23s} | {r[0]:7.0f} {r[1]:9.0f} {r[2]:+6.0f} {r[3]:5.0f} {100 * r[4]:5.1f}%"
                      f"  ({len(vent)} ventanas cada 100 ticks; se solapan, el error es optimista)")
        bl = series.bloques(practica, N)
        r = pareado(pool, bl, VICENTE, MAX_MEDIA)
        lineas.append(f"{'10 bloques sin solapar':>23s} | {r[0]:7.0f} {r[1]:9.0f} {r[2]:+6.0f} {r[3]:5.0f} {100 * r[4]:5.1f}%")
        lineas.append("")

        # Parte 2: ajuste en una mitad, evaluación en la otra
        grilla_z = [("z", dict(km=5, kd=kd, num=num, den=4)) for kd in (5, 6, 7) for num in range(4, 13)]
        grilla_r = [("r", dict(k=5, entra=e, sale=s)) for e in (2, 3, 4, 5) for s in (0, 1)]
        nombre = lambda r: (f"zscore z {r[1]['num'] / 4:g}, desviacion {1 << r[1]['kd']}" if r[0] == "z"
                            else f"reversion entra {r[1]['entra']}, sale {r[1]['sale']}")
        lineas.append("=== Parte 2: parametros elegidos en una mitad de la practica, evaluados en la otra ===")
        lineas.append("Eleccion: la mejor media en los 5 bloques de 2000 de la mitad de ajuste (zscore: 27 combinaciones de")
        lineas.append("umbral 1 a 3 y desviacion 32 a 128; reversion: entrada 2 a 5 unidades, salida 0 o 1, media de 32).")
        mitades = {"primera": practica[:10000], "segunda": practica[10000:]}
        for ajuste, prueba in (("primera", "segunda"), ("segunda", "primera")):
            bl_aj = series.bloques(mitades[ajuste], N)
            mejores = {}
            for g in (grilla_z, grilla_r):
                medias = [sum(pool.map(w, [(s, r) for s in bl_aj])) / len(bl_aj) for r in g]
                k = max(range(len(g)), key=lambda i: medias[i])
                mejores[g[0][0]] = (g[k], medias[k])
            az, ar = mejores["z"][0], mejores["r"][0]
            lineas.append(f"--- ajuste en la {ajuste} mitad, prueba en la {prueba} ---")
            lineas.append(f"  elegidas: {nombre(az)} (media {mejores['z'][1]:.0f} en el ajuste) y {nombre(ar)} "
                          f"(media {mejores['r'][1]:.0f})")
            bl_pr = series.bloques(mitades[prueba], N)
            for etiqueta, lista in [("5 bloques de la mitad de prueba", bl_pr)] + \
                    [(f"remuestreo de la mitad de prueba, trozo {L}", lote(mitades[prueba], L, 500, 11)) for L in (50, 250, 1000)]:
                r = pareado(pool, lista, az, ar)
                lineas.append(f"  {etiqueta:44s} zscore {r[0]:7.0f}  reversion {r[1]:7.0f}  dif {r[2]:+6.0f} +- {r[3]:4.0f}  "
                              f"gana {100 * r[4]:5.1f}%")
            r = pareado(pool, bl_pr, VICENTE, MAX_MEDIA)
            lineas.append(f"  {'(sin reajustar: Vicente contra max_media)':44s} zscore {r[0]:7.0f}  max_media {r[1]:7.0f}  dif "
                          f"{r[2]:+6.0f} +- {r[3]:4.0f}")
        lineas.append("")
        lineas.append("=== Parte 3: el mismo remuestreo con series del modelo calibrado como base ===")
        for fam in ("modelo", "cambio_volatilidad"):
            bases = series.lote(fam, 6, 20000, 9)
            for L in (50, 250, 1000, 2000):
                rng = random.Random(5)
                lst = [series.remuestreo(b, N, rng, bloque=L) for b in bases for _ in range(150)]
                r = pareado(pool, lst, VICENTE, MAX_MEDIA)
                lineas.append(f"  {fam:20s} trozo {L:5d}: dif {r[2]:+6.0f} +- {r[3]:4.0f}  gana {100 * r[4]:5.1f}%")

        def vr(x, h):
            v1 = statistics.pvariance([b - a for a, b in zip(x, x[1:])])
            return statistics.pvariance([x[i + h] - x[i] for i in range(len(x) - h)]) / (h * v1)
        H = (10, 50, 100, 250, 500, 1000)
        lineas.append("  Razon de varianza a " + ", ".join(map(str, H)) + " ticks:")
        lineas.append("    practica             " + " ".join(f"{vr(practica, h):.2f}" for h in H))
        for fam in ("modelo", "cambio_volatilidad"):
            lst = series.lote(fam, 30, 20000, 0)
            lineas.append(f"    {fam:20s} " + " ".join(f"{statistics.mean(vr(x, h) for x in lst):.2f}" for h in H)
                          + "  (promedio de 30 series)")
    if "--puntos" in sys.argv:
        d = os.path.join(RAIZ, "build", "zscore", "trozos")
        base = os.environ.get("RETORNO_SERIES", os.path.join(RAIZ, "build", "zscore", "series"))
        os.makedirs(d, exist_ok=True)
        for nombre in os.listdir(base):
            if nombre.endswith(".bin") and ("_s0_n2000" in nombre and not nombre.startswith("remuestreo")):
                for sem in (70, 71, 72):
                    dst = os.path.join(d, nombre.replace("_s0_", f"_s{sem}_"))
                    if not os.path.lexists(dst):
                        os.symlink(os.path.join(base, nombre), dst)
        for f in ("bloques_n2000.bin", "practica_n20000.bin"):
            if not os.path.lexists(os.path.join(d, f)):
                os.symlink(os.path.join(base, f), os.path.join(d, f))
        lineas.append("")
        lineas.append("=== Parte 4: puntos del torneo con trozos largos (5000 series, campo mixto, G = 10) ===")
        for sem, L in ((70, 50), (71, 250), (72, 1000)):
            rng = random.Random(7000 + L)
            lst = [series.remuestreo(practica, N, rng, bloque=L) for _ in range(5000)]
            with open(os.path.join(d, f"remuestreo_s{sem}_n2000.bin"), "wb") as f:
                f.write(struct.pack("<ii", len(lst), N))
                f.write(b"".join(bytes(x) for x in lst))
            tsv = os.path.join(d, f"h_{sem}.tsv")
            subprocess.run([os.path.join(RAIZ, "build", "zscore", "arnes"), "hipotesis", "--largo", str(N), "--semilla", str(sem),
                            "--candidatos", "max_media;zscore", "--tsv", tsv], check=True, stdout=subprocess.DEVNULL,
                           env=dict(os.environ, RETORNO_SERIES=d))
            v = {}
            for linea in open(tsv).read().splitlines()[1:]:
                c = linea.split("\t")
                if c[3] == "remuestreo" and c[4] == "zscore":
                    v[c[5]] = float(c[6])
            lineas.append(f"  trozo {L:5d}: dif {v['h1_dif']:+6.0f} +- {v['h1_dif_ee']:3.0f}   dH3a {v['d_h3a']:+.3f} +- {v['d_h3a_ee']:.3f}"
                          f"   dH3b {v['d_h3b']:+.3f} +- {v['d_h3b_ee']:.3f}")
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    salida = os.path.join(RAIZ, "docs", "mediciones", "zscore", "trozos.txt")
    with open(salida, "w", newline="\n") as f:
        f.write(texto)


if __name__ == "__main__":
    main()
