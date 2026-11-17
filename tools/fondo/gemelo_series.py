#!/usr/bin/env python3
"""
gemelo_series.py: el fondo en un chip en el gemelo digital contra ref/fondo.py,
en un lote grande de series sintéticas y a los tres períodos.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Es la versión con el gemelo de tools/fondo/series.sh (que corre el RTL con
Verilator y por eso se queda en 0,1 ms). El gemelo del barrel está validado
ciclo a ciclo contra el RTL (make cosim-barrel), así que aquí se puede correr
todo el lote a 0,1 ms, 1 ms y 10 ms en segundos.

Para cada serie y cada período exige: los bytes que lee la maestra idénticos a
los de ref/fondo.py (con los precios que se pierden en el reset, como el
testbench oficial que parte a los 4 us), ningún precio sin leer, una respuesta
por cada precio visto y peor caso bajo el presupuesto del período.

Uso, desde la raíz:  python3 tools/fondo/gemelo_series.py   (o make fondo-gemelo-series)
Opciones: --por-familia 70 (1 050 series), --nticks 2000, --semilla 1,
          --practica (agrega la serie de práctica completa a los tres períodos),
          --peldano r0 (sw/trade.s en el Espino base contra ref/trader.py, en
          vez del fondo en R1).
Resultado en docs/mediciones/fondo/r1/gemelo_series.txt.
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

import fondo    # noqa: E402
import market   # noqa: E402
import series   # noqa: E402
import trader   # noqa: E402

PERIODOS = (100000, 1000000, 10000000)
GEMELO = ["build/gemelo", "--barrel", "--xd", "3", "--tabla", "sw/fondo_tabla.hex"]   # hardware de R1


PELDANO = "r1"


def esperado(args):
    precios, perdidos, peldano = args
    estrategia = trader.Oficial() if peldano == "r0" else fondo.Fondo()
    return bytes(trader.decisiones(precios, estrategia, perdidos))


def correr_gemelo(hexfile, lote, periodo, peldano="r1"):
    gemelo = ["build/gemelo"] if peldano == "r0" else GEMELO
    r = subprocess.run(gemelo + ["--hex", hexfile, "--lote", lote, "--bytes", "--periodo-ns", str(periodo),
                                 "--inicio-ns", "4000"], cwd=RAIZ, capture_output=True, text=True, check=True)
    filas = []
    for linea in r.stdout.splitlines():
        c = linea.split()
        filas.append(dict(peor=int(c[3]), respuestas=int(c[4]), sin_leer=int(c[5]), suma=int(c[7]),
                          bytes=bytes.fromhex(c[8])))
    return filas


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--por-familia", type=int, default=70)
    ap.add_argument("--nticks", type=int, default=2000)
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--practica", action="store_true")
    ap.add_argument("--salida", default="docs/mediciones/fondo/r1/gemelo_series.txt")
    ap.add_argument("--peldano", choices=("r0", "r1"), default="r1")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    os.makedirs("build/fondo", exist_ok=True)
    if subprocess.run(["cc", "-O2", "-o", "build/gemelo", "ref/gemelo/gemelo.c"]).returncode != 0:
        raise SystemExit("FAIL: el gemelo no compila")
    fuente = "sw/trade.s" if a.peldano == "r0" else "sw/fondo.s"
    hexfile = "build/fondo/trade_r0.hex" if a.peldano == "r0" else "build/fondo/fondo.hex"
    if subprocess.run([sys.executable, "tools/pochoasm.py", fuente, "-o", hexfile],
                      capture_output=True).returncode != 0:
        raise SystemExit(f"FAIL: {fuente} no ensambla")

    familias = ["remuestreo"] + sorted(series.FAMILIAS)
    lote = []                      # (familia, precios)
    for fam in familias:
        for p in series.lote(fam, a.por_familia, a.nticks, a.semilla):
            lote.append((fam, p))
    if a.practica:
        lote.append(("practica", market.leer_serie("tb/practica.csv")))

    titulo = ("R0: sw/trade.s en el Espino base, en el gemelo digital, contra ref/trader.py" if a.peldano == "r0"
              else "El fondo en un chip en el gemelo digital contra ref/fondo.py")
    lineas = [titulo,
              f"Generado por tools/fondo/gemelo_series.py (make fondo-gemelo-series). No editar a mano.",
              f"{a.por_familia} series por familia de {a.nticks} ticks, semilla {a.semilla}, "
              f"{len(lote)} series en total. Primera transaccion a los 4 us, como el testbench oficial.", ""]
    fallas = 0
    total_ticks = 0
    t_gemelo = 0.0
    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, "lote.txt")
        with open(ruta, "w") as f:
            for _, p in lote:
                f.write(" ".join(map(str, p)) + "\n")
        for per in PERIODOS:
            perd = trader.ticks_perdidos(per)
            t0 = time.time()
            filas = correr_gemelo(hexfile, ruta, per, a.peldano)
            t_gemelo += time.time() - t0
            with multiprocessing.Pool() as pool:
                esperados = pool.map(esperado, [(p, perd, a.peldano) for _, p in lote])
            presupuesto = (per - 9500) // 40
            lineas.append(f"Periodo {per} ns (presupuesto {presupuesto} ciclos, {perd} precios perdidos en el reset):")
            lineas.append(f"  {'familia':20s} {'series':>6s} {'pasan':>6s} {'ticks':>9s} {'prom':>7s} {'peor':>6s}")
            por_fam = {}
            for (fam, p), fila, esp in zip(lote, filas, esperados):
                ok = (fila["bytes"] == esp and fila["sin_leer"] == 0 and fila["respuestas"] == len(p) - perd
                      and fila["peor"] < presupuesto)
                d = por_fam.setdefault(fam, [0, 0, 0, 0, 0])
                d[0] += 1; d[1] += ok; d[2] += len(p); d[3] += fila["suma"]; d[4] = max(d[4], fila["peor"])
                if not ok:
                    fallas += 1
                    if fallas <= 10:
                        distintos = sum(x != y for x, y in zip(fila["bytes"], esp))
                        lineas.append(f"  FAIL {fam}: bytes distintos {distintos}, sin leer {fila['sin_leer']}, "
                                      f"respuestas {fila['respuestas']}, peor {fila['peor']}")
            for fam, (n, ok, tk, suma, peor) in por_fam.items():
                total_ticks += tk
                lineas.append(f"  {fam:20s} {n:6d} {ok:6d} {tk:9d} {suma / max(tk - n * perd, 1):7.1f} {peor:6d}")
            lineas.append("")
    lineas.append(f"Ticks comparados: {total_ticks} ({len(lote)} series por {len(PERIODOS)} periodos). "
                  f"Tiempo del gemelo: {t_gemelo:.1f} s en total.")
    lineas.append(f"{'PASS' if fallas == 0 else 'FAIL'}: {fallas} corridas con diferencias")
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    with open(a.salida, "w") as f:
        f.write(texto)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
