#!/usr/bin/env python3
"""protocolo.py: protocolo de evaluación de algoritmos.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Un algoritmo no se juzga por su resultado en la serie de práctica completa,
porque sus parámetros se pueden haber elegido mirándola. Se juzga con tres
conjuntos de series de 2000 ticks (ref/series.py):

  1. Los 10 bloques de 2000 ticks de la serie de práctica.
  2. 1000 remuestreos por bloques de los incrementos de la serie de práctica.
  3. 200 series de cada familia sintética.

Para cada conjunto se informa: media, mediana, percentil 5, peor caso,
probabilidad de superar a comprar y mantener y a no operar, y órdenes
promedio. La mediana importa porque en algunas familias unas pocas series
con precios muy bajos inflan la media. El programa ve
todos los precios (como en la competencia, con la placa ya encendida).

    python3 ref/protocolo.py                      # evalúa la regla base
    python3 ref/protocolo.py --estrategia sma64   # evalúa otra estrategia
    python3 ref/protocolo.py --comparar sma64     # sma64 contra la regla base, serie por serie
    python3 ref/protocolo.py --meseta             # la regla base con parámetros vecinos
    python3 ref/protocolo.py --binario            # corre sw/trade.hex en el gemelo sobre todas
                                                  # las series y exige que coincida con la referencia

Una estrategia es cualquier objeto con un método decidir(precio) que devuelve
el byte de DECISION. Se nombra como "base", "base:k=4,entra=3,sale=1",
"sma64", o "modulo:fabrica" para una clase de otro archivo de ref/.

Criterio de aceptación (--comparar). Una candidata reemplaza a la regla base
solo si se cumplen las tres condiciones:
  a. En los 10 bloques de práctica: media y peor bloque mayores o iguales.
  b. En los remuestreos: media y percentil 5 mayores o iguales.
  c. En ninguna familia sintética la media baja más de 1 %.
"""
import argparse
import importlib
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import market           # noqa: E402
import series           # noqa: E402
import trader           # noqa: E402

LARGO = 2000
TOLERANCIA_FAMILIA = 0.01


# ---- Estrategias de comparación ---------------------------------------------------

class SumaMovil:
    """Reversión con suma móvil de los últimos n precios (sin desplazamientos)."""

    def __init__(self, n=64, entra=4, sale=1):
        self.n, self.entra, self.sale = n, entra, sale
        self.buf = None

    def decidir(self, p):
        if self.buf is None:
            self.buf, self.suma, self.i, self.pos = [p] * self.n, p * self.n, 0, 0
        dev = self.n * p - self.suma
        self.suma += p - self.buf[self.i]
        self.buf[self.i] = p
        self.i = (self.i + 1) % self.n
        if dev < -self.entra * self.n:
            self.pos = 1
        elif dev > self.sale * self.n:
            self.pos = 0
        return market.COMPRAR_63 if self.pos else market.VENDER_63


class Comprar63:
    """Comprar y mantener hecho por el programa: siempre "comprar 63"."""

    def decidir(self, p):
        return market.COMPRAR_63


class NoOperar:
    def decidir(self, p):
        return market.MANTENER


FABRICAS = {"base": trader.ReglaBase, "sma64": SumaMovil, "comprar63": Comprar63, "nada": NoOperar}


def fabrica(nombre):
    """Convierte "base:k=4,entra=3" o "modulo:Clase" en una función que crea la estrategia."""
    cabeza, _, resto = nombre.partition(":")
    if cabeza in FABRICAS:
        kw = {}
        for par in filter(None, resto.split(",")):
            k, v = par.split("=")
            kw[k.strip()] = int(v)
        return lambda: FABRICAS[cabeza](**kw)
    return getattr(importlib.import_module(cabeza), resto)


# ---- Conjuntos de series -----------------------------------------------------------

def conjuntos(remuestreos=1000, por_familia=200, semilla=0):
    """Lista de (nombre, series). El orden es fijo y todo es reproducible."""
    c = [("practica, 10 bloques", series.bloques(series.practica(), LARGO)),
         (f"remuestreo ({remuestreos})", series.lote("remuestreo", remuestreos, LARGO, semilla))]
    for nombre in series.FAMILIAS:
        c.append((nombre, series.lote(nombre, por_familia, LARGO, semilla)))
    return c


# ---- Evaluación --------------------------------------------------------------------

def evaluar_serie(args):
    nombre, precios = args
    m = trader.correr(precios, fabrica(nombre)())
    return m.w, m.ordenes, m.max_dd


def evaluar(nombre, lista, pool=None):
    """Patrimonio, órdenes y pérdida máxima de la estrategia en cada serie."""
    trabajos = [(nombre, s) for s in lista]
    if pool is not None and len(lista) >= 64:
        return pool.map(evaluar_serie, trabajos, chunksize=max(1, len(lista) // 48))
    return [evaluar_serie(t) for t in trabajos]


def percentil(valores, q):
    orden = sorted(valores)
    return orden[min(len(orden) - 1, int(q * len(orden)))]


def resumen(res, lista):
    ws = [r[0] for r in res]
    byh = [market.comprar_y_mantener(s) for s in lista]
    n = len(ws)
    return {
        "n": n,
        "media": sum(ws) / n,
        "mediana": percentil(ws, 0.5),
        "p5": percentil(ws, 0.05),
        "peor": min(ws),
        "mejor": max(ws),
        "sobre_byh": sum(w > b for w, b in zip(ws, byh)) / n,
        "sobre_caja": sum(w > market.CAJA0 for w in ws) / n,
        "ordenes": sum(r[1] for r in res) / n,
        "byh_media": sum(byh) / n,
    }


ENCABEZADO = (f"{'conjunto':24s} {'n':>5s} {'media':>8s} {'mediana':>8s} {'p5':>7s} {'peor':>7s} {'mejor':>7s} "
              f"{'>B&H':>6s} {'>10000':>7s} {'ordenes':>8s} {'B&H media':>10s}")


def linea(nombre, r):
    return (f"{nombre:24s} {r['n']:5d} {r['media']:8.0f} {r['mediana']:8d} {r['p5']:7d} {r['peor']:7d} {r['mejor']:7d} "
            f"{100 * r['sobre_byh']:5.0f}% {100 * r['sobre_caja']:6.0f}% {r['ordenes']:8.1f} {r['byh_media']:10.0f}")


def informe(nombre, cjs, pool):
    print(f"Estrategia: {nombre}")
    print(ENCABEZADO)
    tabla = {}
    for cj, lista in cjs:
        res = evaluar(nombre, lista, pool)
        tabla[cj] = (res, resumen(res, lista))
        print(linea(cj, tabla[cj][1]))
    res, _ = tabla[cjs[0][0]]
    print("\nBloques de practica, uno por uno (patrimonio, ordenes, perdida maxima, comprar y mantener):")
    for i, (r, s) in enumerate(zip(res, cjs[0][1])):
        print(f"  bloque {i}: {r[0]:6d} {r[1]:4d} {r[2]:6d}   B&H {market.comprar_y_mantener(s):6d}")
    return tabla


def comparar(candidata, base, cjs, pool):
    """Candidata contra base, serie por serie, con el criterio de aceptación."""
    print(f"Candidata: {candidata}   Base: {base}")
    print(f"{'conjunto':24s} {'n':>5s} {'media cand':>10s} {'media base':>10s} {'dif':>7s} {'gana en':>8s} "
          f"{'p5 cand':>8s} {'p5 base':>8s} {'peor cand':>9s} {'peor base':>9s}")
    ok = {"a": True, "b": True, "c": True}
    for idx, (cj, lista) in enumerate(cjs):
        rc, rb = evaluar(candidata, lista, pool), evaluar(base, lista, pool)
        sc, sb = resumen(rc, lista), resumen(rb, lista)
        gana = sum(a[0] > b[0] for a, b in zip(rc, rb)) / len(lista)
        print(f"{cj:24s} {sc['n']:5d} {sc['media']:10.0f} {sb['media']:10.0f} {sc['media'] - sb['media']:+7.0f} "
              f"{100 * gana:7.0f}% {sc['p5']:8d} {sb['p5']:8d} {sc['peor']:9d} {sb['peor']:9d}")
        if idx == 0:
            ok["a"] = sc["media"] >= sb["media"] and sc["peor"] >= sb["peor"]
        elif idx == 1:
            ok["b"] = sc["media"] >= sb["media"] and sc["p5"] >= sb["p5"]
        elif sc["media"] < sb["media"] * (1 - TOLERANCIA_FAMILIA):
            ok["c"] = False
    print(f"\nCriterio a (bloques: media y peor bloque):      {'cumple' if ok['a'] else 'no cumple'}")
    print(f"Criterio b (remuestreos: media y percentil 5):  {'cumple' if ok['b'] else 'no cumple'}")
    print(f"Criterio c (ninguna familia baja mas de {100 * TOLERANCIA_FAMILIA:.0f} %):   {'cumple' if ok['c'] else 'no cumple'}")
    aceptada = all(ok.values())
    print(f"Veredicto: la candidata {'REEMPLAZA' if aceptada else 'NO reemplaza'} a la base")
    return aceptada


def meseta(cjs, pool):
    """La regla base con parámetros vecinos: no debe ser un máximo aislado."""
    bloques, remu = cjs[0][1], cjs[1][1][:300]
    print("Regla base con parametros vecinos. Bloques de practica (10) y remuestreos (300).")
    print(f"{'k':>2s} {'entra':>5s} {'sale':>4s} | {'bloques media':>13s} {'peor':>6s} | {'remuestreo media':>16s} {'p5':>6s}")
    tabla = {}
    for k in (4, 5, 6):
        for entra in (2, 3, 4, 5, 6):
            for sale in (0, 1, 2):
                nombre = f"base:k={k},entra={entra},sale={sale}"
                b = resumen(evaluar(nombre, bloques, pool), bloques)
                r = resumen(evaluar(nombre, remu, pool), remu)
                tabla[(k, entra, sale)] = (b, r)
                marca = "  <- regla base" if (k, entra, sale) == (trader.K, trader.ENTRA, trader.SALE) else ""
                print(f"{k:2d} {entra:5d} {sale:4d} | {b['media']:13.0f} {b['peor']:6d} | {r['media']:16.0f} {r['p5']:6d}{marca}")
    centro = (trader.K, trader.ENTRA, trader.SALE)
    vecinos = [c for c in tabla if sum(abs(a - b) for a, b in zip(c, centro)) == 1]
    cb, cr = tabla[centro]
    print(f"\nCentro {centro}: bloques {cb['media']:.0f}, remuestreo {cr['media']:.0f}")
    print(f"Vecinos a distancia 1 ({len(vecinos)}): bloques entre {min(tabla[v][0]['media'] for v in vecinos):.0f} y "
          f"{max(tabla[v][0]['media'] for v in vecinos):.0f}, remuestreo entre "
          f"{min(tabla[v][1]['media'] for v in vecinos):.0f} y {max(tabla[v][1]['media'] for v in vecinos):.0f}")
    mejores = sorted(tabla, key=lambda c: -tabla[c][1]["media"])[:3]
    print("Mejores tres por media de remuestreo: " + ", ".join(f"{c} {tabla[c][1]['media']:.0f}" for c in mejores))


def verificar_binario(cjs):
    """sw/trade.hex en el gemelo contra ref/trader.py, en todas las series del protocolo."""
    import gemelo
    todas = [s for _, lista in cjs for s in lista]
    ref = [evaluar_serie(("base", s)) for s in todas]
    fallas = 0
    for periodo, nombre in ((100000, "0,1 ms"), (1000000, "1 ms"), (10000000, "10 ms")):
        res = gemelo.correr_lote(todas, periodo_ns=periodo)
        distintas = sum((g["patrimonio"], g["ordenes"], g["perdida_max"]) != r for g, r in zip(res, ref))
        sin_respuesta = sum(g["respuestas"] != len(s) or g["precios_perdidos"] != 0 for g, s in zip(res, todas))
        peor = max(g["peor_caso"] for g in res)
        fallas += distintas + sin_respuesta
        print(f"periodo {nombre}: {len(todas)} series, {sum(map(len, todas))} ticks. Distintas a la referencia: {distintas}. "
              f"Series con algun precio sin respuesta: {sin_respuesta}. Peor caso de respuesta: {peor} ciclos")
    print("PASS el binario coincide con la referencia en todas las series" if fallas == 0 else "FAIL")
    return fallas == 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Protocolo de evaluación de algoritmos")
    ap.add_argument("--estrategia", default="base")
    ap.add_argument("--comparar", metavar="CANDIDATA", help="comparar la candidata contra --estrategia")
    ap.add_argument("--meseta", action="store_true")
    ap.add_argument("--binario", action="store_true")
    ap.add_argument("--remuestreos", type=int, default=1000)
    ap.add_argument("--por-familia", type=int, default=200)
    ap.add_argument("--semilla", type=int, default=0)
    a = ap.parse_args(argv)

    cjs = conjuntos(a.remuestreos, a.por_familia, a.semilla)
    print(f"Protocolo: series de {LARGO} ticks, {a.remuestreos} remuestreos, {a.por_familia} series por familia, semilla {a.semilla}\n")
    if a.binario:
        return 0 if verificar_binario(cjs) else 1
    with Pool() as pool:
        if a.meseta:
            meseta(cjs, pool)
        elif a.comparar:
            comparar(a.comparar, a.estrategia, cjs, pool)
        else:
            informe(a.estrategia, cjs, pool)
    return 0


if __name__ == "__main__":
    sys.exit(main())
