#!/usr/bin/env python3
"""generar_series.py: series de prueba del estudio de retorno, a 2000 y a 20 000 ticks.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Genera los lotes de series con ref/series.py (sin modificarlo) y los deja en
factibilidad/retorno/build/series/, para que cualquier evaluador los lea sin
regenerarlos. Las series son exactamente las de series.lote(nombre, cantidad,
n, semilla): mismo generador y misma semilla por serie.

Formato de cada archivo (el mismo de ref/motor.py):
    int32 ns        número de series del lote (little endian)
    int32 n         ticks por serie
    ns * n bytes    un byte por precio (1 a 255), serie tras serie

Nombres:
    bloques_n2000.bin                 los 10 bloques de la serie de práctica
    practica_n20000.bin               la serie de práctica completa (una sola serie)
    <familia>_s<semilla>_n<largo>.bin remuestreo o una familia de ref/series.py

Semillas: 0 exploración, 1 la reservada del tramo anterior (solo a 2000 ticks,
para reproducir docs/mediciones/frontera.txt), 2 la reservada de este tramo y
3 la reservada del estudio de cierre (r4_final), que la usa una sola vez.

    python3 factibilidad/retorno/generar_series.py              # todo lo que falte
    python3 factibilidad/retorno/generar_series.py --largo 2000 --semilla 0
    python3 factibilidad/retorno/generar_series.py --listar     # qué hay y cuánto falta

Son datos de prueba: nada de esto queda dentro del diseño.
"""
import argparse
import hashlib
import os
import random
import struct
import sys
from multiprocessing import Pool

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, os.path.join(RAIZ, "ref"))

import series           # noqa: E402

DESTINO = os.path.join(AQUI, "build", "series")
PROCESOS = int(os.environ.get("PROCESOS", "6"))

DEGENERADAS = ["plana", "borde_bajo", "borde_alto"]              # solo prueban la aritmética
ESTRES = [f for f in series.ESTRES if f not in DEGENERADAS]

# Cantidad de series por lote, según el largo: (remuestreo, cada plausible, cada estrés, cada degenerada)
CANTIDADES = {2000: (5000, 2500, 1000, 200), 20000: (4000, 1000, 400, 50)}
# Semillas que se generan para cada largo
SEMILLAS = {2000: (0, 1, 2, 3), 20000: (0, 2, 3)}


def plan(largos=None, semillas=None):
    """Lista de (archivo, familia, cantidad, largo, semilla) de todo el estudio."""
    salida = []
    for n in (largos or sorted(CANTIDADES)):
        rem, pla, est, deg = CANTIDADES[n]
        for s in SEMILLAS[n]:
            if semillas is not None and s not in semillas:
                continue
            lotes = [("remuestreo", rem)] + [(f, pla) for f in series.PLAUSIBLES] + [(f, est) for f in ESTRES] \
                + [(f, deg) for f in DEGENERADAS]
            for familia, cantidad in lotes:
                salida.append((f"{familia}_s{s}_n{n}.bin", familia, cantidad, n, s))
    return salida


def _generar(args):
    familia, n, semilla, i0, i1 = args
    base = series.practica() if familia == "remuestreo" else None
    partes = []
    for i in range(i0, i1):
        rng = random.Random(series.semilla_de(familia, semilla, i))
        s = series.remuestreo(base, n, rng) if familia == "remuestreo" else series.FAMILIAS[familia](n, rng)
        partes.append(bytes(s))
    return b"".join(partes)


def escribir(ruta, ns, n, datos):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta + ".tmp", "wb") as f:
        f.write(struct.pack("<ii", ns, n))
        f.write(datos)
    os.replace(ruta + ".tmp", ruta)


def al_dia(ruta, ns, n):
    if not os.path.exists(ruta) or os.path.getsize(ruta) != 8 + ns * n:
        return False
    fuentes = [os.path.join(RAIZ, "ref", f) for f in ("series.py", "calibracion.py")] + [series.PRACTICA]
    return all(os.path.getmtime(ruta) >= os.path.getmtime(f) for f in fuentes)


def fijos():
    """Los lotes que no dependen de la semilla: bloques de práctica y la serie completa."""
    p = series.practica()
    b = series.bloques(p, 2000)
    escribir(os.path.join(DESTINO, "bloques_n2000.bin"), len(b), 2000, b"".join(bytes(x) for x in b))
    escribir(os.path.join(DESTINO, "practica_n20000.bin"), 1, len(p), bytes(p))


def manifiesto():
    """Lista de archivos con su tamaño y su huella, para saber que dos copias son la misma."""
    lineas = ["# archivo  series  ticks  sha256 (primeros 16)"]
    for nombre in sorted(os.listdir(DESTINO)):
        if not nombre.endswith(".bin"):
            continue
        ruta = os.path.join(DESTINO, nombre)
        with open(ruta, "rb") as f:
            datos = f.read()
        ns, n = struct.unpack("<ii", datos[:8])
        lineas.append(f"{nombre:44s} {ns:6d} {n:6d}  {hashlib.sha256(datos).hexdigest()[:16]}")
    with open(os.path.join(DESTINO, "MANIFIESTO.txt"), "w", newline="\n") as f:
        f.write("\n".join(lineas) + "\n")
    return lineas


def main(argv=None):
    ap = argparse.ArgumentParser(description="Genera las series del estudio de retorno")
    ap.add_argument("--largo", type=int, action="append", choices=sorted(CANTIDADES))
    ap.add_argument("--semilla", type=int, action="append")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--forzar", action="store_true", help="regenerar aunque el archivo exista")
    a = ap.parse_args(argv)

    trabajos = plan(a.largo, a.semilla)
    if a.listar:
        for archivo, _, cantidad, n, _ in trabajos:
            estado = "ok" if al_dia(os.path.join(DESTINO, archivo), cantidad, n) else "falta"
            print(f"{archivo:44s} {cantidad:6d} x {n:6d}  {estado}")
        return 0

    os.makedirs(DESTINO, exist_ok=True)
    fijos()
    with Pool(PROCESOS) as pool:
        for archivo, familia, cantidad, n, s in trabajos:
            ruta = os.path.join(DESTINO, archivo)
            if al_dia(ruta, cantidad, n) and not a.forzar:
                continue
            paso = max(1, cantidad // (8 * PROCESOS))
            partes = pool.map(_generar, [(familia, n, s, i, min(cantidad, i + paso)) for i in range(0, cantidad, paso)])
            escribir(ruta, cantidad, n, b"".join(partes))
            print(f"{archivo}: {cantidad} series de {n} ticks", flush=True)
    lineas = manifiesto()
    print(f"{DESTINO}/MANIFIESTO.txt: {len(lineas) - 1} archivos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
