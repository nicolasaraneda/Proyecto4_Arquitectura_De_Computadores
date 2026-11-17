#!/usr/bin/env python3
"""ensayo.py: ensayo general de la competencia. Las tres rondas para cada peldaño con
una serie nueva, mostrando lo que vería la maestra.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Para cada ronda se genera una serie nueva (ref/series.py, familia `modelo`, la que imita
la serie de práctica, con una semilla que nadie usó para elegir nada), y para cada
peldaño (R0, R1 y R2) se corre una copia del testbench oficial por el RTL con Verilator,
con el período de la ronda. La copia solo cambia el programa, la serie, el período, el
largo y el nombre de decisiones.csv, igual que tools/equiv.sh. De cada corrida se muestra
lo que imprime el testbench (lo que vería la maestra: patrimonio final, órdenes, pérdida
máxima, comprar y mantener, peor caso contra el presupuesto y los 4 chequeos) y se exige
que decisiones.csv sea idéntico al de la referencia del peldaño (ref/trader.py para R0,
ref/fondo.py para R1 y R2).

Las rondas se corren con reset entre una y otra (cada una es una simulación aparte). Las
rondas seguidas sin reset ya están en la matriz de estrés (make fondo-estres).

Uso: python3 tools/ensayo.py [--nticks 2000] [--semilla 20261130] [--jobs 6]
     (o make ensayo). Unos 15 minutos con 2000 ticks por ronda.
Salida: docs/mediciones/ensayo.txt y las series en build/ensayo/.
"""
import argparse
import os
import re
import subprocess
import sys
import time
from multiprocessing import Pool

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
import market  # noqa: E402
import series  # noqa: E402

R1_DEFS = "-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA"
PELDANOS = {"R0": ("", "sw/trade.hex", "trader"),
            "R1": (R1_DEFS, "build/ensayo/fondo.hex", "fondo"),
            "R2": (R1_DEFS + " -DESPINO_VIGILANTE", "build/ensayo/fondo.hex", "fondo")}
RONDAS = [("Ronda 1", 10000000), ("Ronda 2", 1000000), ("Ronda 3", 100000)]


def fuentes():
    return [f"rtl/{f}" for f in sorted(os.listdir(os.path.join(RAIZ, "rtl"))) if f.endswith(".v") and not f.startswith("00_")] + \
        [f"rtl/espino_core/{f}" for f in sorted(os.listdir(os.path.join(RAIZ, "rtl", "espino_core"))) if f.endswith(".v")]


def correr(args):
    peldano, ronda, periodo, nticks, serie = args
    defs, hexfile, ref = PELDANOS[peldano]
    d = os.path.join("build", "ensayo", f"{peldano}_{ronda.split()[-1]}")
    os.makedirs(d, exist_ok=True)
    tb = open("tb/tb_proyecto_4.sv").read()
    copia = re.sub(r'PROGRAMA   = "[^"]*";', f'PROGRAMA   = "{hexfile}";', tb)
    copia = re.sub(r'SERIE      = "[^"]*";', f'SERIE      = "{serie}";', copia)
    copia = re.sub(r"PERIODO_NS = [0-9]*;", f"PERIODO_NS = {periodo};", copia)
    copia = re.sub(r"NTICKS     = [0-9]*;", f"NTICKS     = {nticks};", copia)
    copia = copia.replace('"decisiones.csv"', f'"{d}/tb.csv"')
    distintas = sum(1 for a, b in zip(tb.splitlines(), copia.splitlines()) if a != b)
    with open(os.path.join(d, "tb_p4.sv"), "w") as f:
        f.write(copia)
    celdas = subprocess.run(["yosys-config", "--datdir"], capture_output=True, text=True).stdout.strip() + "/ice40/cells_sim.v"
    comp = subprocess.run(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module",
                           "tb_proyecto_4", "-DNO_ICE40_DEFAULT_ASSIGNMENTS", *defs.split(), "-O3", "--Mdir", f"{d}/obj",
                           "-o", "sim", celdas, *fuentes(), f"{d}/tb_p4.sv"], capture_output=True, text=True)
    if comp.returncode != 0:
        return peldano, ronda, None, "FAIL: Verilator no compila", distintas
    t0 = time.time()
    sal = subprocess.run([f"{d}/obj/sim"], capture_output=True, text=True).stdout
    if ref == "trader":
        r = subprocess.run([sys.executable, "ref/trader.py", serie, "--nticks", str(nticks), "--periodo-ns", str(periodo),
                            "-o", f"{d}/ref.csv"], capture_output=True, text=True)
    else:
        r = subprocess.run([sys.executable, "ref/fondo.py", serie, "--nticks", str(nticks), "--periodo-ns", str(periodo),
                            "-o", f"{d}/ref.csv"], capture_output=True, text=True)
    igual = r.returncode == 0 and os.path.exists(f"{d}/tb.csv") and open(f"{d}/tb.csv", "rb").read() == open(f"{d}/ref.csv", "rb").read()
    return peldano, ronda, sal, ("PASS" if igual else "FAIL") + f": decisiones.csv {'identico' if igual else 'distinto'} a ref/{ref}.py", \
        distintas, time.time() - t0


def campo(sal, texto):
    m = re.search(re.escape(texto) + r"\s*(-?\d+)", sal or "")
    return int(m.group(1)) if m else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nticks", type=int, default=2000)
    ap.add_argument("--semilla", type=int, default=20261130)
    ap.add_argument("--familia", default="modelo")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--salida", default="docs/mediciones/ensayo.txt")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    os.makedirs("build/ensayo", exist_ok=True)
    if subprocess.run([sys.executable, "tools/pochoasm.py", "sw/fondo.s", "-o", "build/ensayo/fondo.hex"],
                      capture_output=True).returncode != 0:
        raise SystemExit("FAIL: sw/fondo.s no ensambla")
    t0 = time.time()
    trabajos = []
    rutas = {}
    lote = series.lote(a.familia, 3, a.nticks, a.semilla)
    for (ronda, periodo), precios in zip(RONDAS, lote):
        ruta = f"build/ensayo/serie_{ronda.split()[-1]}.csv"
        with open(ruta, "w") as f:
            f.write("tick,price\n" + "".join(f"{t},{p}\n" for t, p in enumerate(precios)))
        rutas[ronda] = (ruta, precios)
        for peldano in PELDANOS:
            trabajos.append((peldano, ronda, periodo, a.nticks, ruta))
    trabajos.sort(key=lambda x: -x[2])          # primero las rondas lentas
    with Pool(a.jobs) as pool:
        res = pool.map(correr, trabajos, chunksize=1)
    por = {(r[0], r[1]): r for r in res}
    lineas = ["Ensayo general: las tres rondas para cada peldano, con series nuevas, por el RTL (Verilator)",
              f"Generado por tools/ensayo.py {' '.join(argv if argv is not None else sys.argv[1:])} (make ensayo).",
              f"Series: familia `{a.familia}` de ref/series.py, semilla {a.semilla} (no se uso para elegir nada), "
              f"{a.nticks} ticks por ronda, una serie distinta por ronda; quedan en build/ensayo/.",
              "Cada corrida es una copia del testbench oficial que solo cambia el programa, la serie, el periodo, el largo y",
              "el nombre de decisiones.csv. Lo que se muestra es lo que imprime el testbench: lo que veria la maestra.", ""]
    fallas = 0
    for ronda, periodo in RONDAS:
        ruta, precios = rutas[ronda]
        lineas.append(f"--- {ronda}: periodo {periodo / 1e6:g} ms, serie {ruta} (precio inicial {precios[0]}, final {precios[-1]}, "
                      f"minimo {min(precios)}, maximo {max(precios)}) ---")
        lineas.append(f"{'peldano':8s} {'patrimonio':>10s} {'ordenes':>8s} {'perdida max':>11s} {'comprar y mant.':>15s} "
                      f"{'peor caso':>10s} {'presupuesto':>11s} {'chequeos':>8s}  referencia")
        for peldano in PELDANOS:
            r = por[(peldano, ronda)]
            sal = r[2]
            m = re.search(r"Testbenchs aprobados: (\d+)/(\d+)", sal or "")
            ok4 = bool(m) and m.group(1) == m.group(2) == "4"
            pc = re.search(r"Peor caso precio->decision: (\d+) ciclos \(disponibles: (\d+)\)", sal or "")
            lineas.append(f"{peldano:8s} {campo(sal, 'Patrimonio final:') or 0:10d} {campo(sal, 'Ordenes ejecutadas:') or 0:8d} "
                          f"{campo(sal, 'Perdida maxima:') or 0:11d} {campo(sal, 'Comprar y mantener:') or 0:15d} "
                          f"{(pc.group(1) if pc else '?'):>10s} {(pc.group(2) if pc else '?'):>11s} "
                          f"{(m.group(1) + '/' + m.group(2)) if m else '?':>8s}  {r[3]}")
            fallas += (not ok4) + (not r[3].startswith("PASS")) + (r[4] > 5)
        lineas.append("")
    lineas.append("Patrimonio de las tres rondas por peldano (suma) y diferencia con R0:")
    sumas = {p: sum(campo(por[(p, rd)][2], "Patrimonio final:") or 0 for rd, _ in RONDAS) for p in PELDANOS}
    for p in PELDANOS:
        lineas.append(f"  {p}: {sumas[p]} ({sumas[p] - sumas['R0']:+d})")
    lineas.append("")
    lineas.append(f"Tiempo: {time.time() - t0:.0f} s.")
    lineas.append(f"{'PASS' if fallas == 0 else 'FAIL'}: {9 - fallas if fallas <= 9 else 0} de 9 corridas con 4/4 y decisiones iguales a su referencia"
                  if fallas == 0 else f"FAIL: {fallas} comprobaciones fallaron")
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    with open(a.salida, "w", newline="\n") as f:
        f.write(texto)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
