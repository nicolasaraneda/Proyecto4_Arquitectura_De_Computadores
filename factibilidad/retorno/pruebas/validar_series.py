#!/usr/bin/env python3
"""validar_series.py: las series guardadas son las que entrega ref/series.py.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 factibilidad/retorno/pruebas/validar_series.py      (o make comprobar-series)

Para cada archivo de build/series vuelve a generar sus primeras series con
series.lote(familia, cantidad, largo, semilla) y exige que sean idénticas a
las guardadas. También compara los bloques y la serie de práctica completa
con tb/practica.csv, y revisa que todos los precios estén entre 1 y 255.

Solo mira precios: no evalúa ninguna estrategia, así que puede leer también
los archivos de la semilla reservada.
"""
import os
import struct
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
RAIZ = os.path.dirname(os.path.dirname(RETORNO))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, RETORNO)

import series               # noqa: E402
import generar_series       # noqa: E402

SERIES = os.path.join(RETORNO, "build", "series")
MUESTRA = {2000: 3, 20000: 1}       # series que se regeneran por archivo


def leer(nombre, cuantas=None):
    with open(os.path.join(SERIES, nombre), "rb") as f:
        datos = f.read()
    ns, n = struct.unpack("<ii", datos[:8])
    cuerpo = datos[8:]
    fuera = sum(1 for b in cuerpo if b < 1)                 # un byte no pasa de 255
    k = ns if cuantas is None else min(ns, cuantas)
    return ns, n, len(cuerpo), fuera, [list(cuerpo[i * n:(i + 1) * n]) for i in range(k)]


def main():
    archivos = comparadas = distintas = mal_tamano = fuera_total = 0
    for archivo, familia, cantidad, n, s in generar_series.plan():
        ns, nn, largo, fuera, guardadas = leer(archivo, MUESTRA[n])
        archivos += 1
        mal_tamano += ns != cantidad or nn != n or largo != ns * nn
        fuera_total += fuera
        for a, b in zip(guardadas, series.lote(familia, len(guardadas), n, s)):
            comparadas += 1
            distintas += a != list(b)
    p = series.practica()
    ns, nn, largo, fuera, guardadas = leer("practica_n20000.bin")
    archivos += 1
    fuera_total += fuera
    comparadas += 1
    distintas += guardadas[0] != list(p)
    ns, nn, largo, fuera, guardadas = leer("bloques_n2000.bin")
    archivos += 1
    fuera_total += fuera
    for a, b in zip(guardadas, series.bloques(p, 2000)):
        comparadas += 1
        distintas += a != list(b)
    ok = distintas == 0 and mal_tamano == 0 and fuera_total == 0
    print(f"serie de practica: {len(p)} ticks, precio minimo {min(p)}, precio maximo {max(p)}")
    print(f"{'PASS' if ok else 'FAIL'}  series guardadas contra ref/series.py: {archivos} archivos, {comparadas} series regeneradas, "
          f"{distintas} distintas, {mal_tamano} archivos con tamano inesperado, {fuera_total} precios fuera de 1..255")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
