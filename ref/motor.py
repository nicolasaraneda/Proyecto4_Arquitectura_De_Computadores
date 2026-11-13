#!/usr/bin/env python3
"""motor.py: envoltorio en Python del evaluador rápido (ref/motor/motor.c).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El motor corre la familia paramétrica de estrategias (la misma de
ref/candidatos.py) sobre lotes de series, unas cien veces más rápido que
Python. Se usa para explorar: barridos de parámetros y mesetas. Los números
finales de cada candidata se confirman con la referencia en Python a través
de ref/protocolo.py, y ref/test_candidatos.py exige que el motor y la
referencia coincidan serie por serie.

    import motor
    c = motor.conjunto("remuestreo", 1000, semilla=0)      # se genera una vez y queda en build/
    r = motor.evaluar(c, [{"k": 5, "E": 128, "X": 0}])     # un resumen por configuración
    d = motor.detalle(c, {"k": 5, "E": 128, "X": 0})       # una fila por serie

Una configuración es un diccionario de parámetros enteros (ver la tabla en
ref/motor/motor.c o en docs/algoritmo.md). Lo que no se nombra queda en su
valor por defecto, que es la regla base.
"""
import os
import struct
import subprocess
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import series           # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE = os.path.join(RAIZ, "ref", "motor", "motor.c")
BINARIO = os.path.join(RAIZ, "build", "motor")
CACHE = os.path.join(RAIZ, "build", "series_bin")

RESUMEN = ("media", "mediana", "p5", "peor", "mejor", "sobre_byh", "sobre_caja", "ordenes", "guardia", "cortes",
           "con_tope", "con_guardia")
DETALLE = ("w", "ordenes", "max_dd", "guardia", "cortes", "topes")
PROCESOS = int(os.environ.get("PROCESOS", "12"))


def compilar():
    """Compila build/motor si no existe o si el fuente es más nuevo."""
    if os.path.exists(BINARIO) and os.path.getmtime(BINARIO) >= os.path.getmtime(FUENTE):
        return BINARIO
    os.makedirs(os.path.dirname(BINARIO), exist_ok=True)
    subprocess.run([os.environ.get("CC", "cc"), "-O2", "-Wall", "-Wextra", "-o", BINARIO, FUENTE], check=True)
    return BINARIO


def escribir(ruta, lista):
    """Guarda un lote de series del mismo largo en el formato del motor."""
    n = len(lista[0])
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta + ".tmp", "wb") as f:
        f.write(struct.pack("ii", len(lista), n))
        for s in lista:
            if len(s) != n:
                raise ValueError("todas las series del lote deben tener el mismo largo")
            f.write(bytes(s))
    os.replace(ruta + ".tmp", ruta)


def leer(ruta):
    with open(ruta, "rb") as f:
        ns, n = struct.unpack("ii", f.read(8))
        datos = f.read()
    return [list(datos[i * n:(i + 1) * n]) for i in range(ns)]


def _generar(args):
    nombre, n, semilla, i0, i1 = args
    import random
    base = series.practica() if nombre == "remuestreo" else None
    salida = []
    for i in range(i0, i1):
        rng = random.Random(series.semilla_de(nombre, semilla, i))
        salida.append(series.remuestreo(base, n, rng) if nombre == "remuestreo" else series.FAMILIAS[nombre](n, rng))
    return salida


def conjunto(nombre, cantidad=None, n=2000, semilla=0):
    """Ruta del archivo con el lote. Lo genera si no existe.

    `nombre` es "bloques", "remuestreo" o una familia de ref/series.py. Las
    series son las mismas que entrega series.lote con la misma semilla.
    """
    if nombre == "bloques":
        ruta = os.path.join(CACHE, f"bloques_{n}.bin")
        if not os.path.exists(ruta):
            escribir(ruta, series.bloques(series.practica(), n))
        return ruta
    ruta = os.path.join(CACHE, f"{nombre}_{semilla}_{cantidad}_{n}.bin")
    fuentes = [os.path.join(RAIZ, "ref", f) for f in ("series.py", "calibracion.py")]
    if os.path.exists(ruta) and all(os.path.getmtime(ruta) >= os.path.getmtime(f) for f in fuentes):
        return ruta
    paso = max(1, cantidad // (4 * PROCESOS))
    trabajos = [(nombre, n, semilla, i, min(cantidad, i + paso)) for i in range(0, cantidad, paso)]
    if cantidad >= 200:
        with Pool(PROCESOS) as pool:
            partes = pool.map(_generar, trabajos)
    else:
        partes = [_generar(t) for t in trabajos]
    escribir(ruta, [s for parte in partes for s in parte])
    return ruta


def _linea(cfg):
    return " ".join(f"{k}={int(v)}" for k, v in cfg.items()) or "k=5"


def _correr(args):
    ruta, lineas, det = args
    cmd = [compilar(), ruta] + (["--detalle"] if det else [])
    return subprocess.run(cmd, input="\n".join(lineas) + "\n", check=True, capture_output=True, text=True).stdout


def evaluar(ruta, configuraciones, pool=None):
    """Resumen del lote para cada configuración: lista de diccionarios con las claves de RESUMEN."""
    compilar()
    lineas = [_linea(c) for c in configuraciones]
    if pool is not None and len(lineas) >= 2 * PROCESOS:
        paso = (len(lineas) + PROCESOS - 1) // PROCESOS
        salidas = pool.map(_correr, [(ruta, lineas[i:i + paso], False) for i in range(0, len(lineas), paso)])
        texto = "".join(salidas)
    else:
        texto = _correr((ruta, lineas, False))
    filas = [dict(zip(RESUMEN, map(float, l.split()))) for l in texto.splitlines() if l.strip()]
    if len(filas) != len(configuraciones):
        raise RuntimeError("el motor devolvió un número distinto de resultados")
    return filas


def detalle(ruta, cfg):
    """Una fila por serie: diccionarios con las claves de DETALLE."""
    texto = _correr((ruta, [_linea(cfg)], True))
    return [dict(zip(DETALLE, map(int, l.split()))) for l in texto.splitlines() if l.strip()]


def pareada(ruta, cfg, base=None):
    """Diferencia pareada de patrimonio entre cfg y base, serie por serie.

    Devuelve (media de la diferencia, error estándar, fracción de series en que cfg gana).
    """
    a = [r["w"] for r in detalle(ruta, cfg)]
    b = [r["w"] for r in detalle(ruta, base or {})]
    dif = [x - y for x, y in zip(a, b)]
    n = len(dif)
    m = sum(dif) / n
    var = sum((v - m) ** 2 for v in dif) / (n - 1) if n > 1 else 0.0
    return m, (var / n) ** 0.5, sum(v > 0 for v in dif) / n


if __name__ == "__main__":
    print(compilar())
