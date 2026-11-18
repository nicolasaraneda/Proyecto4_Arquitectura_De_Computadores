"""comun.py: utilidades de la evaluación de reglas para series normalizadas (docs/cotas.md).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.
"""
import os
import struct
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
BUILD = os.path.join(RAIZ, "build", "cotas")
sys.path.insert(0, os.path.dirname(AQUI))


def evaluador():
    """Compila evaluar.c si hace falta y devuelve la ruta del ejecutable."""
    os.makedirs(BUILD, exist_ok=True)
    exe = os.path.join(BUILD, "evaluar")
    src = os.path.join(AQUI, "evaluar.c")
    if not os.path.exists(exe) or os.path.getmtime(exe) < os.path.getmtime(src):
        subprocess.run(["cc", "-O2", "-o", exe, src], check=True)
    return exe


def normalizar(x):
    """Normalización del profesor: mínimo a 100, máximo a 255, lineal y redondeada."""
    lo, hi = min(x), max(x)
    if hi == lo:
        return [178] * len(x)
    return [int(100 + (v - lo) * 155.0 / (hi - lo) + 0.5) for v in x]


def escribir_ventanas(ruta, ventanas):
    with open(ruta, "wb") as f:
        f.write(struct.pack("<i", len(ventanas)))
        for v in ventanas:
            f.write(struct.pack("<i", len(v)))
            f.write(bytes(v))


def evaluar(estrategias, ventanas, etiqueta="tmp", caja=10000, comision=5, ordenes=False):
    """estrategias: lista de (nombre, tipo, parámetros). Devuelve (nombres, filas de patrimonio[, órdenes])."""
    exe = evaluador()
    pe = os.path.join(BUILD, f"{etiqueta}_estrategias.txt")
    pv = os.path.join(BUILD, f"{etiqueta}_ventanas.bin")
    po = os.path.join(BUILD, f"{etiqueta}_ordenes.csv")
    with open(pe, "w") as f:
        for nombre, tipo, par in estrategias:
            f.write(f"{nombre} {tipo} {' '.join(str(x) for x in par)}\n")
    escribir_ventanas(pv, ventanas)
    args = [exe, pe, pv, str(caja), str(comision)] + ([po] if ordenes else [])
    r = subprocess.run(args, capture_output=True, text=True, check=True)
    lineas = r.stdout.splitlines()
    nombres = lineas[0].split(",")
    filas = [[int(x) for x in l.split(",")] for l in lineas[1:]]
    if not ordenes:
        return nombres, filas
    lo = open(po).read().splitlines()[1:]
    return nombres, filas, [[int(x) for x in l.split(",")] for l in lo]
