#!/usr/bin/env python3
"""gemelo_lote.py: sw/c1.s en el gemelo digital (tabla de 512 palabras) contra ref/c1/c1.py, en un
lote de series y a los tres períodos.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El gemelo del barrel con la tabla de 512 palabras está validado ciclo a ciclo contra el RTL de
R3 (make c1-cosim), así que aquí se corre todo el lote a 0,1 ms, 1 ms y 10 ms. Para cada serie y
cada período exige: los bytes que lee la maestra idénticos a los de la referencia (con los
precios que se pierden en el reset, como el testbench oficial que parte a los 4 us), ningún
precio sin leer, una respuesta por cada precio visto y peor caso bajo el límite.

Con --banda40 la referencia es además la banda 40 de R2 (ref/fondo.py) y el programa de R2
(sw/fondo.s con sw/fondo_tabla.hex) en el mismo gemelo: los bytes tienen que ser los mismos en
las tres. Es la puerta de la política apagada.

Uso, desde la raíz:
  python3 tools/c1/gemelo_lote.py LISTA.txt [--tabla sw/c1_tabla.hex] [--hex build/c1/c1.hex]
        [--limite 1131] [--banda40] [--jobs 12] [--salida archivo.txt] [--titulo "..."]
LISTA.txt trae una ruta de serie (CSV tick,price) por línea.
"""
import argparse
import multiprocessing
import os
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
import fondo    # noqa: E402  (antes que nada que pueda traer otro fondo.py)
import market   # noqa: E402
import trader   # noqa: E402
sys.path.insert(0, os.path.join(RAIZ, "ref", "c1"))
import c1 as R          # noqa: E402
import tablas as TB     # noqa: E402

PERIODOS = (100000, 1000000, 10000000)
T = None


def esperado(args):
    precios, perdidos = args
    return bytes(trader.decisiones(precios, R.C1(T), perdidos))


def esperado_b40(args):
    precios, perdidos = args
    return bytes(trader.decisiones(precios, fondo.Fondo(), perdidos))


def gemelo(args):
    hexfile, tabla, lote, periodo = args
    r = subprocess.run(["build/gemelo", "--barrel", "--xd", "3", "--tabla", tabla, "--hex", hexfile, "--lote", lote, "--bytes",
                        "--periodo-ns", str(periodo), "--inicio-ns", "4000"], cwd=RAIZ, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("FAIL: el gemelo terminó con error: " + r.stderr[-300:])
    filas = []
    for linea in r.stdout.splitlines():
        c = linea.split()
        filas.append(dict(peor=int(c[3]), respuestas=int(c[4]), sin_leer=int(c[5]), suma=int(c[7]), bytes=bytes.fromhex(c[8])))
    return filas


def main(argv=None):
    global T
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("lista")
    ap.add_argument("--tabla", default="sw/c1_tabla.hex")
    ap.add_argument("--hex", default="build/c1/c1.hex")
    ap.add_argument("--limite", type=int, default=1131)
    ap.add_argument("--banda40", action="store_true")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--salida")
    ap.add_argument("--titulo", default="sw/c1.s en el gemelo digital contra ref/c1/c1.py")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    T = TB.leer_hex(a.tabla)
    rutas = [l.strip() for l in open(a.lista) if l.strip()]
    lote = [market.leer_serie(r) for r in rutas]
    if a.banda40:
        if subprocess.run([sys.executable, "tools/pochoasm.py", "sw/fondo.s", "-o", "build/c1/fondo_r2.hex"],
                          capture_output=True).returncode != 0:
            raise SystemExit("FAIL: sw/fondo.s no ensambla")
    ctx = multiprocessing.get_context("fork")
    lineas = [a.titulo, "Generado por tools/c1/gemelo_lote.py. No editar a mano.",
              f"{len(lote)} series, {sum(map(len, lote))} ticks por periodo. Tabla {a.tabla}. Primera transaccion a los 4 us, "
              f"como el testbench oficial. Limite del peor caso: {a.limite} ciclos.", ""]
    fallas = 0
    total = 0
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp, ctx.Pool(a.jobs) as pool:
        # el lote repartido en a.jobs archivos, para correr el gemelo en paralelo
        partes = [list(range(i, len(lote), a.jobs)) for i in range(min(a.jobs, len(lote)))]
        for j, idx in enumerate(partes):
            with open(os.path.join(tmp, f"lote{j}.txt"), "w") as f:
                for i in idx:
                    f.write(" ".join(map(str, lote[i])) + "\n")
        for per in PERIODOS:
            perd = trader.ticks_perdidos(per)

            def correr(hexfile, tabla):
                res = pool.map(gemelo, [(hexfile, tabla, os.path.join(tmp, f"lote{j}.txt"), per) for j in range(len(partes))])
                filas = [None] * len(lote)
                for idx, r in zip(partes, res):
                    for i, fila in zip(idx, r):
                        filas[i] = fila
                return filas
            filas = correr(a.hex, a.tabla)
            esp = pool.map(esperado, [(p, perd) for p in lote], chunksize=4)
            b40 = r2 = None
            if a.banda40:
                b40 = pool.map(esperado_b40, [(p, perd) for p in lote], chunksize=4)
                r2 = correr("build/c1/fondo_r2.hex", "sw/fondo_tabla.hex")
            n_ok, peor, suma, resp = 0, 0, 0, 0
            for i, (p, fila, e) in enumerate(zip(lote, filas, esp)):
                err = []
                if fila["bytes"] != e:
                    err.append(f"{sum(x != y for x, y in zip(fila['bytes'], e))} bytes distintos a ref/c1/c1.py")
                if b40 is not None and fila["bytes"] != b40[i]:
                    err.append(f"{sum(x != y for x, y in zip(fila['bytes'], b40[i]))} bytes distintos a la banda 40 de ref/fondo.py")
                if r2 is not None and fila["bytes"] != r2[i]["bytes"]:
                    err.append(f"{sum(x != y for x, y in zip(fila['bytes'], r2[i]['bytes']))} bytes distintos al programa de R2")
                if fila["sin_leer"] != 0:
                    err.append(f"{fila['sin_leer']} precios sin leer")
                if fila["respuestas"] != len(p) - perd:
                    err.append(f"{fila['respuestas']} respuestas de {len(p) - perd}")
                if fila["peor"] >= a.limite:
                    err.append(f"peor caso {fila['peor']} ciclos")
                peor = max(peor, fila["peor"]); suma += fila["suma"]; resp += fila["respuestas"]
                total += len(p)
                if err:
                    fallas += 1
                    if fallas <= 12:
                        lineas.append(f"FAIL {rutas[i]} a {per} ns: " + "; ".join(err))
                else:
                    n_ok += 1
            lineas.append(f"{'PASS' if n_ok == len(lote) else 'FAIL'} periodo {per} ns ({perd} precios perdidos en el reset): "
                          f"{n_ok} de {len(lote)} series identicas a la referencia"
                          + (", a la banda 40 de ref/fondo.py y al programa de R2 en el gemelo" if a.banda40 else "")
                          + f"; respuesta promedio {suma / max(resp, 1):.1f} ciclos, peor caso {peor}")
    lineas.append("")
    lineas.append(f"Ticks comparados: {total} ({len(lote)} series por {len(PERIODOS)} periodos). Tiempo: {time.time() - t0:.0f} s.")
    lineas.append(f"{'PASS' if fallas == 0 else 'FAIL'}: {fallas} corridas con diferencias")
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    if a.salida:
        with open(a.salida, "w") as f:
            f.write(texto)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
