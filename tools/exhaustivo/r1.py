#!/usr/bin/env python3
"""r1.py: cobertura de la regla de decisión de R1 (sw/fondo.s) con las series exhaustivas de R0.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El fondo tiene demasiado estado para recorrerlo entero (cuatro posiciones, tres pesos,
tres puntajes y la ventana). Lo que sí se puede cubrir entero es lo que decide cada hilo:
los cuatro llevan la misma media S (la misma cuenta desde el mismo primer precio) y cada
uno su posición con sus umbrales. Las series de tools/exhaustivo/r0_cubrir.c aplican cada
precio en cada estado alcanzable (S, pos) del supervisor, que corre la regla de R0. Este
script:

  1. Cuenta, con ref/fondo.py, cuántas combinaciones (S, pos, p) recorre cada hilo, contra
     las alcanzables con sus propios umbrales, y cuántas combinaciones de votos (los tres
     gestores) y pesos llegan a la decisión.
  2. Corre todas las series en el gemelo con el hardware de R1 y compara los bytes de
     decisión con ref/fondo.py.
  3. Con --rtl N, corre por el RTL (Verilator, copia del testbench oficial) las N series
     largas más cortas.

El período es 30 us: R1 necesita al menos 26,94 us con SCLK de 1 MHz.
Uso: python3 tools/exhaustivo/r1.py [--rtl 4] [--jobs 6]
Salida: docs/mediciones/noche/exhaustivo_r1.txt
"""
import argparse
import os
import re
import subprocess
import sys
import time
from multiprocessing import Pool

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
import fondo  # noqa: E402
import market  # noqa: E402
import trader  # noqa: E402

R1_DEFS = "-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA"
GEMELO = ["build/gemelo", "--barrel", "--xd", "3", "--tabla", "sw/fondo_tabla.hex", "--hex", "build/fondo/fondo.hex"]


def alcanzables(entra, sale):
    """Estados (S, pos) alcanzables con la regla de umbrales (entra, sale), como Regla.paso."""
    alc = set(2 * 32 * p0 for p0 in range(1, 256))
    cola = list(alc)
    while cola:
        nueva = []
        for i in cola:
            S, pos = i >> 1, i & 1
            for p in range(1, 256):
                dev = 32 * p - S
                np_ = (pos | (dev < entra)) & (dev < sale)
                j = 2 * (S + (dev >> 5)) + np_
                if j not in alc:
                    alc.add(j)
                    nueva.append(j)
        cola = nueva
    return alc


def cobertura(args):
    precios, perdidos = args
    f = fondo.Fondo()
    hilos = [f.sup] + f.gestores
    vistos = [bytearray(8161 * 2 * 32) for _ in hilos]
    votos = set()
    for t, p in enumerate(precios):
        if t < perdidos:
            continue
        if f.sup.s is not None:
            for h, v in zip(hilos, vistos):
                clave = ((h.s * 2 + h.pos) << 8) | p
                v[clave >> 3] |= 1 << (clave & 7)
        f.decidir(p)
        votos.add((f.gestores[0].pos, f.gestores[1].pos, f.gestores[2].pos, tuple(f.w)))
    return [bytes(v) for v in vistos], votos


def gemelo_lote(args):
    ruta, per = args
    r = subprocess.run(GEMELO + ["--lote", ruta, "--bytes", "--periodo-ns", str(per)], cwd=RAIZ, capture_output=True,
                       text=True, check=True)
    return [bytes.fromhex(l.split()[8]) for l in r.stdout.splitlines()]


def esperado(args):
    precios, perd = args
    return bytes(trader.decisiones(precios, fondo.Fondo(), perd))


def rtl(args):
    ruta, per, nticks, etiqueta = args
    d = os.path.join(RAIZ, "build", "exhaustivo", "rtl_r1", etiqueta)
    os.makedirs(d, exist_ok=True)
    tb = open(os.path.join(RAIZ, "tb/tb_proyecto_4.sv")).read()
    c = re.sub(r'PROGRAMA   = "[^"]*";', 'PROGRAMA   = "build/fondo/fondo.hex";', tb)
    c = re.sub(r'SERIE      = "[^"]*";', f'SERIE      = "{ruta}";', c)
    c = re.sub(r"PERIODO_NS = [0-9]*;", f"PERIODO_NS = {per};", c)
    c = re.sub(r"NTICKS     = [0-9]*;", f"NTICKS     = {nticks};", c).replace('"decisiones.csv"', f'"{d}/tb.csv"')
    # el arreglo de la serie del oficial tiene 20 000 precios fijos (tb/tb_proyecto_4.sv:37)
    c = c.replace("int precio [20000];", "int precio [NTICKS];")
    open(f"{d}/tb_p4.sv", "w").write(c)
    fuentes = [f"rtl/{f}" for f in sorted(os.listdir(os.path.join(RAIZ, "rtl"))) if f.endswith(".v") and not f.startswith("00_")] + \
        [f"rtl/espino_core/{f}" for f in sorted(os.listdir(os.path.join(RAIZ, "rtl/espino_core"))) if f.endswith(".v")]
    celdas = subprocess.run(["yosys-config", "--datdir"], capture_output=True, text=True).stdout.strip() + "/ice40/cells_sim.v"
    if subprocess.run(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", "tb_proyecto_4",
                       "-DNO_ICE40_DEFAULT_ASSIGNMENTS", *R1_DEFS.split(), "-O3", "--Mdir", f"{d}/obj", "-o", "sim", celdas,
                       *fuentes, f"{d}/tb_p4.sv"], cwd=RAIZ, capture_output=True).returncode:
        return etiqueta, nticks, False, "no compila"
    sal = subprocess.run([f"{d}/obj/sim"], cwd=RAIZ, capture_output=True, text=True).stdout
    precios = market.leer_serie(os.path.join(RAIZ, ruta))
    esp = bytes(trader.decisiones(precios, fondo.Fondo(), trader.ticks_perdidos(per)))
    filas = open(f"{d}/tb.csv").read().splitlines()[1:]
    leido = bytes(int(l.split(",")[2], 16) for l in filas)
    m = re.search(r"Testbenchs aprobados: (\d+)/(\d+)", sal)
    pc = re.search(r"Peor caso precio->decision: (\d+) ciclos \(disponibles: (\d+)\)", sal)
    ok = bool(m) and m.group(1) == m.group(2) == "4" and leido == esp
    return etiqueta, nticks, ok, f"{m.group(0) if m else '?'}, peor caso {pc.group(1) if pc else '?'} de {pc.group(2) if pc else '?'}, " \
        f"bytes de decision {'identicos' if leido == esp else 'DISTINTOS'} a ref/fondo.py"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default="build/exhaustivo/series")
    ap.add_argument("--periodo-ns", type=int, default=30000)
    ap.add_argument("--rtl", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--salida", default="docs/mediciones/noche/exhaustivo_r1.txt")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    t0 = time.time()
    subprocess.run(["cc", "-O2", "-o", "build/gemelo", "ref/gemelo/gemelo.c"], check=True)
    os.makedirs("build/fondo", exist_ok=True)
    subprocess.run([sys.executable, "tools/pochoasm.py", "sw/fondo.s", "-o", "build/fondo/fondo.hex"], check=True, capture_output=True)
    per = a.periodo_ns
    perd = trader.ticks_perdidos(per)
    largas = sorted(os.path.join(a.dir, f) for f in os.listdir(a.dir) if f.startswith("serie_") and f.endswith(".csv"))
    esquina = [list(map(int, l.split())) for l in open(os.path.join(a.dir, "esquina.txt")) if l.strip()]
    datos = [market.leer_serie(r) for r in largas] + esquina
    lineas = ["Cobertura de la regla de decision de R1 (sw/fondo.s) con las series exhaustivas de R0",
              f"Generado por tools/exhaustivo/r1.py {' '.join(argv if argv is not None else sys.argv[1:])}.",
              f"{len(largas)} series largas y {len(esquina)} cortas de tools/exhaustivo/r0_cubrir.c, {sum(map(len, datos))} ticks. "
              f"Periodo {per} ns: se pierden {perd} precios en el reset.", ""]
    with Pool(a.jobs * 2) as pool:
        res = pool.map(cobertura, [(d, perd) for d in datos], chunksize=1)
    q = fondo.Fondo().q
    reglas = [("supervisor (max_media)", q["S_ENTRA"], q["S_SALE"]), ("gestor 1", q["G1_ENTRA"], q["G1_SALE"]),
              ("gestor 2", q["G2_ENTRA"], q["G2_SALE"]), ("gestor 3", q["G3_ENTRA"], q["G3_SALE"])]
    votos = set()
    for _, v in res:
        votos |= v
    lineas.append("1. Cobertura contada con ref/fondo.py (combinaciones (S, pos, p) de cada hilo contra las alcanzables con sus umbrales):")
    for h, (nombre, e, s) in enumerate(reglas):
        total = bytearray(len(res[0][0][h]))
        for v, _ in res:
            for i, b in enumerate(v[h]):
                if b:
                    total[i] |= b
        alc = alcanzables(e, s)
        cub = sum(1 for i in range(len(total) * 8) if (total[i >> 3] >> (i & 7)) & 1 and (i >> 8) in alc)
        lineas.append(f"   {nombre:24s} entra {e:5d}, sale {s:3d}: {cub} de {len(alc) * 255} ({100 * cub / (len(alc) * 255):.2f} %)")
    pesos = {v[3] for v in votos}
    lineas.append(f"   Votos de los tres gestores por pesos que llegaron a la decision: {len(votos)} combinaciones distintas "
                  f"({len({v[:3] for v in votos})} de 8 votos, {len(pesos)} juegos de pesos).")
    # 2. gemelo
    os.makedirs("build/exhaustivo/r1", exist_ok=True)
    lotes = []
    for i in range(0, len(datos), 400):
        ruta = f"build/exhaustivo/r1/lote_{i:05d}.txt"
        with open(ruta, "w") as f:
            for s in datos[i:i + 400]:
                f.write(" ".join(map(str, s)) + "\n")
        lotes.append(ruta)
    with Pool(a.jobs) as pool:
        leidos = [b for parte in pool.map(gemelo_lote, [(r, per) for r in lotes], chunksize=1) for b in parte]
        esperados = pool.map(esperado, [(d, perd) for d in datos], chunksize=4)
    malas = sum(1 for x, y in zip(leidos, esperados) if x != y) + abs(len(leidos) - len(datos))
    lineas.append(f"2. Gemelo con el hardware de R1: {len(datos)} series; con algun byte de decision distinto a ref/fondo.py: {malas}")
    lineas.append(f"   {'PASS' if malas == 0 else 'FAIL'} gemelo")
    # 3. RTL
    if a.rtl:
        cortas = sorted(largas, key=lambda r: len(market.leer_serie(r)))[:a.rtl]
        with Pool(min(a.jobs, a.rtl)) as pool:
            rr = pool.map(rtl, [(r, per, len(market.leer_serie(r)), os.path.basename(r)[:-4]) for r in cortas], chunksize=1)
        for e, n, ok, txt in rr:
            lineas.append(f"   {'PASS' if ok else 'FAIL'} RTL {e} ({n} ticks): {txt}")
        lineas.append(f"3. RTL: {sum(x[2] for x in rr)} de {len(rr)} series ({sum(x[1] for x in rr)} ticks) con 4/4 y bytes identicos")
    lineas += ["", f"Tiempo: {time.time() - t0:.0f} s."]
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    with open(a.salida, "w", newline="\n") as f:
        f.write(texto)


if __name__ == "__main__":
    main()
