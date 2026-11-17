#!/usr/bin/env python3
"""validar.py: la regla zscore del arnés (zscore.c) contra la referencia en Python (ref/zscore.py).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Comprueba, en este orden:

  1. ref/zscore.py contra tools/referencia.py del repositorio de Vicente
     (función agente_zscore), byte por byte de DECISION en la serie de práctica
     y en series sintéticas. El repositorio se busca en VICENTE_REPO (por
     defecto, una carpeta Vicente_Proyecto4 al lado de este repositorio). Si no
     está, la prueba se informa como no corrida.
  2. 40 957 con 578 órdenes en la serie de práctica completa (la cifra que dio Vicente).
  3. zscore.c contra ref/zscore.py: patrimonio y órdenes serie por serie, en
     varios conjuntos y con varios juegos de parámetros.
  4. fondo_z.c sin gestores por nombre contra el fondo de la factibilidad
     (r4b_fondo/fondo.c): fondoz_min y fondo_min dan lo mismo serie por serie.

Uso: python3 ref/zscore/validar.py   (después de make zscore-arnes)
"""
import importlib.util
import os
import struct
import subprocess
import sys
from multiprocessing import Pool

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
import market  # noqa: E402
import trader  # noqa: E402
import series as series_mod  # noqa: E402
from zscore import ZScore  # noqa: E402

ARNES = os.path.join(RAIZ, "build", "zscore", "arnes")
SERIES = os.environ.get("RETORNO_SERIES", os.path.join(RAIZ, "factibilidad", "retorno", "build", "series"))
FONDO_FACT = os.path.join(RAIZ, "factibilidad", "retorno", "r4b_fondo", "build", "arnes")
VICENTE = os.environ.get("VICENTE_REPO", os.path.join(os.path.dirname(RAIZ), "Vicente_Proyecto4"))

fallas = 0


def comprobar(ok, texto):
    global fallas
    print(("PASS " if ok else "FAIL ") + texto)
    if not ok:
        fallas += 1


def leer_lote(ruta, maximo=None):
    with open(ruta, "rb") as f:
        ns, n = struct.unpack("<ii", f.read(8))
        datos = f.read()
    ns = ns if maximo is None else min(ns, maximo)
    return [list(datos[i * n:(i + 1) * n]) for i in range(ns)]


def detalle(spec, ruta, maximo=None):
    out = subprocess.run([ARNES, "detalle", "--estrategia", spec, "--lote", ruta], check=True,
                         capture_output=True, text=True).stdout.split("\n")
    filas = [list(map(int, l.split()[:2])) for l in out if l.strip()]
    return filas if maximo is None else filas[:maximo]


def py_zscore(args):
    precios, kw = args
    m = trader.correr(precios, ZScore(**kw))
    return [m.w, m.ordenes]


def main():
    # 1. Contra la referencia de Vicente
    ruta = os.path.join(VICENTE, "tools", "referencia.py")
    practica = market.leer_serie(os.path.join(RAIZ, "tb", "practica.csv"))
    if os.path.exists(ruta):
        spec = importlib.util.spec_from_file_location("referencia_vicente", ruta)
        ref_v = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ref_v)
        lotes = [practica] + [series_mod.lote(f, 20, 2000, 0)[i] for f in ("modelo", "paseo", "volatil", "borde_bajo")
                              for i in range(20)]
        distintas = 0
        for s in lotes:
            z = ZScore()
            nuestro = [z.decidir(p) for p in s]
            if nuestro != list(ref_v.agente_zscore(s)):
                distintas += 1
        comprobar(distintas == 0, f"ref/zscore.py contra agente_zscore de {ruta}: {len(lotes)} series "
                                  f"(practica y 80 sinteticas), {distintas} con algun byte distinto")
    else:
        print(f"NO CORRIDA: no se encontro {ruta} (VICENTE_REPO)")

    # 2. La cifra de Vicente
    m = trader.correr(practica, ZScore())
    comprobar((m.w, m.ordenes) == (40957, 578), f"practica completa: {m.w} con {m.ordenes} ordenes (se esperaba 40 957 con 578)")

    # 3. zscore.c contra ref/zscore.py
    juegos = [dict(), dict(num=9, den=4), dict(num=7, den=4, km=4), dict(num=3, den=1, kd=7, w=32),
              dict(num=2, den=1, km=6, kd=5, sx2=1)]
    conjuntos = [("bloques_n2000.bin", None), ("practica_n20000.bin", None), ("remuestreo_s0_n2000.bin", 200),
                 ("modelo_s0_n2000.bin", 100), ("tendencia_s0_n2000.bin", 100), ("saltos_s0_n2000.bin", 100),
                 ("borde_bajo_s0_n2000.bin", 50), ("plana_s0_n2000.bin", 20), ("modelo_s0_n20000.bin", 10)]
    total = 0
    with Pool(int(os.environ.get("PROCESOS", "12"))) as pool:
        for kw in juegos:
            spec = "zscore:" + ",".join(f"{k}={v}" for k, v in kw.items()) if kw else "zscore"
            distintas = n = 0
            for archivo, maximo in conjuntos:
                ruta = os.path.join(SERIES, archivo)
                lote = leer_lote(ruta, maximo)
                c = detalle(spec, ruta, maximo)
                p = pool.map(py_zscore, [(s, kw) for s in lote])
                distintas += sum(1 for a, b in zip(c, p) if a != b) + abs(len(c) - len(p))
                n += len(lote)
            total += n
            comprobar(distintas == 0, f"zscore.c contra ref/zscore.py con {spec}: {n} series, {distintas} distintas "
                                      f"(patrimonio y ordenes)")

    # 4. fondo_z.c sin gestores por nombre es el fondo de la factibilidad
    if os.path.exists(FONDO_FACT):
        distintas = n = 0
        for archivo in ("bloques_n2000.bin", "remuestreo_s0_n2000.bin", "modelo_s0_n2000.bin", "practica_n20000.bin"):
            ruta = os.path.join(SERIES, archivo)
            a = detalle("cand:fondoz_min", ruta)
            b = subprocess.run([FONDO_FACT, "detalle", "--estrategia", "cand:fondo_min", "--lote", ruta], check=True,
                               capture_output=True, text=True).stdout.split("\n")
            b = [list(map(int, l.split()[:2])) for l in b if l.strip()]
            distintas += sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
            n += len(a)
        comprobar(distintas == 0, f"fondoz_min (fondo_z.c) contra fondo_min (r4b_fondo/fondo.c): {n} series, {distintas} distintas")
    else:
        print(f"NO CORRIDA: falta {FONDO_FACT} (make -C factibilidad/retorno/r4b_fondo arnes)")

    print("RESULTADO", "PASS" if fallas == 0 else "FAIL", f"({total} series de zscore por los dos caminos)")
    return 0 if fallas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
