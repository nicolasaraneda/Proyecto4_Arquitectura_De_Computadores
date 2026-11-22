#!/usr/bin/env python3
"""contabilidad_series.py: las 12 ventanas de otras acciones para la corrida de R3 contra la maestra.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Escanea 600 ventanas de 20 000 minutos (60 de las acciones de $P4_DATOS/otras, 10 ventanas cada una,
semilla 11), normalizadas entre 100 y 255 como las rondas, y corre ref/c1/c1.py en cada una para ver
si la fase A apuesta (entra a media posición). Elige 12: 4 con dos o tres entradas, 2 con una entrada y
candado al final, 2 con una entrada y recuperación al final, 2 con una entrada que pasa por recuperación
y candado, y 2 sin apuesta (control), una acción distinta en cada una. Escribe sus CSV (tick,price).

Las otras acciones se usaron para ajustar las constantes 0,95 y 100 de C1 (docs/defensa/c1.md): sirven
para comparar cuentas, no para medir ganancia. No son las cinco empresas del examen.

Uso: python3 tools/c1/contabilidad_series.py CARPETA   (escribe CARPETA/ACCION_INICIO.csv y CARPETA/lista.txt)
"""
import importlib.util
import multiprocessing as mp
import os
import random
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, os.path.join(RAIZ, "ref", "cotas"))
sys.path.insert(0, os.path.join(RAIZ, "ref", "c1"))
import market  # noqa: E402
import comun  # noqa: E402
import tablas as TB  # noqa: E402

_spec = importlib.util.spec_from_file_location("c1ref", os.path.join(RAIZ, "ref", "c1", "c1.py"))
c1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c1)

SEMILLA, N_ACCIONES, N_VENTANAS, LARGO = 11, 60, 10, 20000
DATOS = os.path.expanduser(os.environ.get("P4_DATOS", "~/proyectos/datos_p4"))


def analizar(precios, T):
    """Corre C1 y cuenta la apuesta de la fase A (entradas a media posición), sus órdenes parciales y los modos."""
    c = c1.C1(T)
    m = market.Mercado()
    actual, previo = 0, 0
    entradas = ticks_media = parciales = 0
    modos = set()
    for p in precios:
        m.ejecutar(actual, p)
        actual = c.paso(p)
        if c.modo == 0 and c.sa == 1:
            ticks_media += 1
            if previo == 0:
                entradas += 1
        previo = c.sa if c.modo == 0 else 0
        parciales += 1 if 0 < (actual & 63) < 63 else 0
        modos.add(c.modo)
    return dict(W=m.w, ordenes=m.ordenes, entradas=entradas, ticks_media=ticks_media, parciales=parciales,
                modos=sorted(modos))


def por_accion(args):
    e, semilla, T = args
    with open(os.path.join(DATOS, "otras", e + ".csv")) as f:
        x = [float(l.split(",")[2]) for l in f.read().splitlines()[1:]]
    rng = random.Random(semilla)
    out = []
    for _ in range(N_VENTANAS):
        i = rng.randrange(len(x) - LARGO)
        pr = comun.normalizar(x[i:i + LARGO])
        r = analizar(pr, T)
        r.update(accion=e, inicio=i, precios=pr)
        out.append(r)
    return out


def escanear():
    T = TB.leer_hex(os.path.join(RAIZ, "sw", "c1_tabla.hex"))
    acciones = sorted(f[:-4] for f in os.listdir(os.path.join(DATOS, "otras")) if f.endswith(".csv"))
    sel = random.Random(SEMILLA).sample(acciones, N_ACCIONES)
    with mp.get_context("fork").Pool(min(22, os.cpu_count() or 1)) as pool:
        return [r for lote in pool.map(por_accion, [(e, SEMILLA * 1000 + k, T) for k, e in enumerate(sel)]) for r in lote]


def elegir(res):
    usadas = set()

    def tomar(cands, n):
        out = []
        for r in cands:
            if r["accion"] in usadas:
                continue
            usadas.add(r["accion"])
            out.append(r)
            if len(out) == n:
                break
        return out

    orden = sorted(res, key=lambda r: (r["accion"], r["inicio"]))
    uno = [r for r in orden if r["entradas"] == 1]
    return [
        ("2 o 3 entradas", tomar([r for r in sorted(orden, key=lambda r: -r["entradas"]) if r["entradas"] >= 2], 4)),
        ("1 entrada, termina en candado", tomar([r for r in uno if r["modos"] == [0, 2]], 2)),
        ("1 entrada, termina en recuperacion", tomar([r for r in uno if r["modos"] == [0, 1]], 2)),
        ("1 entrada, recuperacion y candado", tomar([r for r in uno if r["modos"] == [0, 1, 2]], 2)),
        ("sin apuesta (control)", tomar([r for r in orden if r["entradas"] == 0], 2)),
    ]


def main():
    carpeta = sys.argv[1]
    os.makedirs(carpeta, exist_ok=True)
    res = escanear()
    con = sum(1 for r in res if r["entradas"] > 0)
    lineas = [f"Escaneo: {len(res)} ventanas de {N_ACCIONES} acciones (semilla {SEMILLA}); {con} con apuesta de la fase A ({100 * con / len(res):.0f} %)",
              f"{'grupo':36s} {'accion':6s} {'inicio':>7s} {'entradas':>8s} {'ticks media':>11s} {'parciales':>9s} {'W ref':>7s} {'ordenes':>7s}"]
    for grupo, lst in elegir(res):
        for r in lst:
            ruta = os.path.join(carpeta, f"{r['accion']}_{r['inicio']}.csv")
            with open(ruta, "w", newline="\n") as f:
                f.write("tick,price\n" + "".join(f"{t},{x}\n" for t, x in enumerate(r["precios"])))
            lineas.append(f"{grupo:36s} {r['accion']:6s} {r['inicio']:7d} {r['entradas']:8d} {r['ticks_media']:11d} "
                          f"{r['parciales']:9d} {r['W']:7d} {r['ordenes']:7d}")
    with open(os.path.join(carpeta, "lista.txt"), "w") as f:
        f.write("\n".join(lineas) + "\n")
    print("\n".join(lineas))


if __name__ == "__main__":
    main()
