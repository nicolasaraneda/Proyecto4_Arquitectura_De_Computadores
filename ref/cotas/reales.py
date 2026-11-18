#!/usr/bin/env python3
"""reales.py: población real de minutos (Alpaca, 2022 a 2024) y su comprobación.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Los minutos los baja tools/datos/alpaca.py a una carpeta fuera del repositorio
($P4_DATOS/minuto, o data/externos/minuto, que no se versiona). Cada empresa queda como
una serie de un precio por minuto de la sesión regular (9:30 a 15:59 de Nueva York).
La población es el conjunto de todas las ventanas de LARGO minutos seguidos de cada
empresa, normalizadas con el mínimo y el máximo de la ventana (comun.normalizar).

Comprobaciones (python3 ref/cotas/reales.py comprobar [--captura CSV ...]):
  1. La ventana de Meta que empieza el 23/2/2022 a las 15:20 da data/practica_meta.csv
     byte a byte.
  2. Cada serie capturada de la maestra se busca en las cinco empresas: inicio, fin y
     cuántos precios difieren en la mejor ventana.
Las estrategias sobre todas las ventanas las corre ventanas.c (en C, con OpenMP);
python3 ref/cotas/reales.py validar lo compara con las referencias en Python.
"""
import argparse
import array
import collections
import datetime as dt
import hashlib
import os
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

EMPRESAS = ("META", "AAPL", "NFLX", "AMD", "TSLA")
LARGO = 20000
CACHE = os.path.join(comun.BUILD, "reales")


def carpeta_datos(arg=None):
    if arg:
        return os.path.expanduser(arg)
    if os.environ.get("P4_DATOS"):
        return os.path.join(os.path.expanduser(os.environ["P4_DATOS"]), "minuto")
    return os.path.join(comun.RAIZ, "data", "externos", "minuto")


def leer_sesion(carpeta, emp):
    """(fechas, minutos, precios) de la sesión regular de una empresa."""
    fechas, minutos, precios = [], [], []
    with open(os.path.join(carpeta, f"{emp}.csv")) as f:
        next(f)
        for linea in f:
            d, m, p = linea.rstrip("\n").split(",")
            fechas.append(d)
            minutos.append(int(m))
            precios.append(float(p))
    return fechas, minutos, precios


def hora(minuto):
    return f"{9 + (30 + minuto) // 60:02d}:{(30 + minuto) % 60:02d}"


def extremos_deslizantes(x, largo):
    """Mínimo y máximo de cada ventana de largo fijo (colas monótonas)."""
    lo, hi = [0.0] * (len(x) - largo + 1), [0.0] * (len(x) - largo + 1)
    qa, qb = collections.deque(), collections.deque()
    for i, v in enumerate(x):
        while qa and x[qa[-1]] >= v:
            qa.pop()
        qa.append(i)
        while qb and x[qb[-1]] <= v:
            qb.pop()
        qb.append(i)
        s = i - largo + 1
        if s >= 0:
            while qa[0] < s:
                qa.popleft()
            while qb[0] < s:
                qb.popleft()
            lo[s], hi[s] = x[qa[0]], x[qb[0]]
    return lo, hi


def buscar(objetivo, carpeta, empresas=EMPRESAS, prefijo=64):
    """Mejores ventanas de las empresas para una serie normalizada: [(distintos, emp, inicio)]."""
    n = len(objetivo)
    out = []
    for emp in empresas:
        fechas, minutos, x = leer_sesion(carpeta, emp)
        if len(x) < n:
            continue
        lo, hi = extremos_deslizantes(x, n)
        for s in range(len(lo)):
            a, b = lo[s], hi[s]
            if b == a:
                continue
            # filtro barato: los primeros precios normalizados
            if any(int(100 + (x[s + t] - a) * 155.0 / (b - a) + 0.5) != objetivo[t] for t in range(prefijo)):
                continue
            w = comun.normalizar(x[s:s + n])
            out.append((sum(1 for u, v in zip(w, objetivo) if u != v), emp, s, fechas, minutos))
    out.sort(key=lambda r: r[0])
    return out


def describir(r, n):
    d, emp, s, fechas, minutos = r
    return (f"{emp} desde {fechas[s]} {hora(minutos[s])} hasta {fechas[s + n - 1]} {hora(minutos[s + n - 1])} "
            f"(hora de Nueva York): {n - d} de {n} precios iguales")


def comprobar(carpeta, capturas):
    L = ["Comprobacion de la poblacion real (ref/cotas/reales.py comprobar)", ""]
    meta = [int(l.split(",")[1]) for l in open(os.path.join(comun.RAIZ, "data", "practica_meta.csv")).read().splitlines()[1:]]
    fechas, minutos, x = leer_sesion(carpeta, "META")
    s = next(i for i in range(len(fechas)) if fechas[i] == "2022-02-23" and minutos[i] == 350)
    w = comun.normalizar(x[s:s + len(meta)])
    dif = sum(1 for u, v in zip(w, meta) if u != v)
    L += [f"1. data/practica_meta.csv contra la ventana de Meta que empieza el 2022-02-23 a las 15:20:",
          f"   {len(meta) - dif} de {len(meta)} precios iguales; extremos {min(x[s:s + len(meta)]):.4f} y "
          f"{max(x[s:s + len(meta)]):.4f} USD; fin {fechas[s + len(meta) - 1]} {hora(minutos[s + len(meta) - 1])}.",
          "   " + ("PASS" if dif == 0 else "FAIL")]
    r = buscar(meta, carpeta)
    L.append("   Busqueda en las cinco empresas: " + (describir(r[0], len(meta)) if r else "sin coincidencias")
             + f"; otras ventanas exactas: {sum(1 for q in r[1:] if q[0] == 0)}")
    for i, cap in enumerate(capturas, 2):
        obj = [int(l.split(",")[1]) for l in open(cap).read().splitlines()[1:]]
        r = buscar(obj, carpeta)
        L += ["", f"{i}. Captura {os.path.basename(cap)} ({len(obj)} precios, minimo {min(obj)}, maximo {max(obj)}):"]
        L.append("   " + (describir(r[0], len(obj)) if r else "no aparece en ninguna empresa"))
        if r:
            L.append("   " + ("PASS" if r[0][0] == 0 else "FAIL") + f"; otras ventanas exactas: {sum(1 for q in r[1:] if q[0] == 0)}")
    return L


# --- todas las ventanas con ventanas.c --------------------------------------------------------

def ejecutable():
    os.makedirs(comun.BUILD, exist_ok=True)
    exe = os.path.join(comun.BUILD, "ventanas")
    srcs = [os.path.join(comun.AQUI, f) for f in ("ventanas.c", "evaluar.c")]
    if not os.path.exists(exe) or os.path.getmtime(exe) < max(os.path.getmtime(f) for f in srcs):
        subprocess.run(["cc", "-O2", "-fopenmp", "-o", exe, srcs[0]], check=True)
    return exe


def correr(estrategias, carpeta, emp, largo=LARGO, paso=1, caja=10000, comision=5):
    """Patrimonio de cada estrategia en cada ventana. Devuelve dict con ini, pmin, pmax, w (array plano), ne.
    Guarda el resultado en build/cotas/reales/ con una clave de la serie, las estrategias y los parámetros."""
    os.makedirs(CACHE, exist_ok=True)
    texto = "".join(f"{n} {t} {' '.join(str(v) for v in p)}\n" for n, t, p in estrategias)
    ruta_serie = os.path.join(carpeta, f"{emp}.csv")
    h = hashlib.sha256()
    h.update(texto.encode())
    h.update(open(ruta_serie, "rb").read())
    for f in ("ventanas.c", "evaluar.c"):
        h.update(open(os.path.join(comun.AQUI, f), "rb").read())
    h.update(f"{largo} {paso} {caja} {comision}".encode())
    clave = h.hexdigest()[:16]
    salida = os.path.join(CACHE, f"{emp}_{largo}_{paso}_{clave}.bin")
    if not os.path.exists(salida):
        pe = os.path.join(CACHE, f"{emp}_{clave}_estrategias.txt")
        ps = os.path.join(CACHE, f"{emp}_serie.bin")
        open(pe, "w").write(texto)
        _, _, x = leer_sesion(carpeta, emp)
        with open(ps, "wb") as f:
            f.write(struct.pack("<i", len(x)))
            array.array("d", x).tofile(f)
        subprocess.run([ejecutable(), pe, ps, str(largo), str(paso), salida + ".tmp", str(caja), str(comision)],
                       check=True)
        os.replace(salida + ".tmp", salida)
    with open(salida, "rb") as f:
        nv, ne = struct.unpack("<ii", f.read(8))
        ini, pmin, pmax, w = array.array("i"), array.array("i"), array.array("i"), array.array("i")
        ini.fromfile(f, nv)
        pmin.fromfile(f, nv)
        pmax.fromfile(f, nv)
        w.fromfile(f, nv * ne)
    assert ne == len(estrategias)
    return dict(ini=ini, pmin=pmin, pmax=pmax, w=w, ne=ne, nv=nv)


def validar(carpeta, emp="META", paso=4999):
    """ventanas.c contra la normalización y las referencias en Python, en una ventana de cada `paso`."""
    import planb
    import trader
    from regla_cotas import Cotas
    ESTR = [("espera_banda60", "cotas", (0, 0, 0, 60, 0, 178), lambda: Cotas("espera", banda=60)),
            ("compra", "cotas", (1, 0, 0, 0, 0, 178), lambda: Cotas("compra")),
            ("max_media", "media", (5, 3, 0), lambda: trader.MaxMedia()),
            ("unavez100_220", "unavez", (100, 220), lambda: planb.UnaVez(100, 220))]
    r = correr([e[:3] for e in ESTR], carpeta, emp, paso=paso)
    _, _, x = leer_sesion(carpeta, emp)
    malos = 0
    for v in range(r["nv"]):
        s = r["ini"][v]
        w = comun.normalizar(x[s:s + LARGO])
        if r["pmin"][v] != w.index(100) or r["pmax"][v] != w.index(255):
            malos += 1
        for j, e in enumerate(ESTR):
            if trader.correr(w, e[3]()).w != r["w"][v * r["ne"] + j]:
                malos += 1
    L = [f"ventanas.c contra Python: {r['nv']} ventanas de {emp} (una cada {paso}), {len(ESTR)} estrategias, "
         f"extremos y patrimonio: {malos} diferencias", "PASS" if malos == 0 else "FAIL"]
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("accion", choices=["comprobar", "validar"])
    ap.add_argument("--datos", default=None, help="carpeta de los minutos (por omisión $P4_DATOS/minuto)")
    ap.add_argument("--captura", nargs="*", default=[], help="CSV de series capturadas de la maestra")
    ap.add_argument("-o", "--salida", default=None)
    a = ap.parse_args(argv)
    L = comprobar(carpeta_datos(a.datos), a.captura) if a.accion == "comprobar" else validar(carpeta_datos(a.datos))
    texto = "\n".join(L) + "\n"
    print(texto, end="")
    if a.salida:
        open(a.salida, "w").write(texto)
    return 0 if "FAIL" not in texto else 1


if __name__ == "__main__":
    sys.exit(main())
