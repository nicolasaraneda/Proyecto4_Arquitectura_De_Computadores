#!/usr/bin/env python3
"""r0.py: verificación exhaustiva de la regla de decisión de R0 (sw/trade.s), por el gemelo y por el RTL.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

La regla de R0 tiene como estado S (32 veces la media) y pos, y recibe un precio de 1
a 255. tools/exhaustivo/r0_cubrir.c arma series que aplican cada precio en cada estado
alcanzable. Este script:

  1. Cuenta de nuevo, con ref/trader.py y sin confiar en el generador, qué combinaciones
     (S, pos, p) recorre la referencia sobre esas series, con los precios que el programa
     pierde durante el reset al período elegido.
  2. Corre cada serie en el gemelo digital (build/gemelo) y compara decisiones.csv con
     el de ref/trader.py, byte por byte.
  3. Con --rtl, corre las series largas por el RTL con Verilator (copia parametrizada
     del testbench oficial, tools/equiv.sh): 4/4 y decisiones.csv idéntico a la referencia.
     Con --rtl-esquina N, además N series cortas de la esquina por el RTL.

Uso: python3 tools/exhaustivo/r0.py [--periodo-ns 12000] [--rtl] [--rtl-esquina 200] [--jobs 6]
Salida: docs/mediciones/noche/exhaustivo_r0.txt
"""
import argparse
import os
import random
import re
import subprocess
import sys
import time
from multiprocessing import Pool

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
import market  # noqa: E402
import trader  # noqa: E402

SMAX = 8160


def leer_csv(ruta):
    return market.leer_serie(ruta)


def cobertura(args):
    precios, perdidos = args
    vistos = bytearray((SMAX + 1) * 2 * 32)          # un bit por (S, pos, p)
    r = trader.MaxMedia()
    n = 0
    for t, p in enumerate(precios):
        if t < perdidos:
            continue
        if r.S is not None:
            clave = ((r.S * 2 + r.pos) << 8) | p
            vistos[clave >> 3] |= 1 << (clave & 7)
            n += 1
        r.decidir(p)
    return bytes(vistos), n


def columnas_decision(ruta):
    """Las columnas tick, precio y decision de un decisiones.csv. Las de caja, acciones y
    patrimonio no se comparan: el testbench y el gemelo las llevan en enteros de 32 bits y
    en estas series artificiales (comprar a 1 y vender a 253 millones de veces) se
    desbordan, mientras que ref/trader.py usa enteros sin límite."""
    with open(ruta) as f:
        return [",".join(l.split(",")[:3]) for l in f]


def gemelo_serie(args):
    ruta, periodo, nticks, d = args
    base = os.path.join(d, os.path.basename(ruta)[:-4])
    g = subprocess.run(["build/gemelo", "--hex", "sw/trade.hex", "--serie", ruta, "--periodo-ns", str(periodo),
                        "--nticks", str(nticks), "--csv", base + "_gemelo.csv", "--callado"], cwd=RAIZ,
                       capture_output=True, text=True)
    r = subprocess.run([sys.executable, "ref/trader.py", ruta, "--nticks", str(nticks), "--periodo-ns", str(periodo),
                        "-o", base + "_ref.csv"], cwd=RAIZ, capture_output=True, text=True)
    igual = g.returncode == 0 and r.returncode == 0 and columnas_decision(base + "_gemelo.csv") == columnas_decision(base + "_ref.csv")
    completo = igual and open(base + "_gemelo.csv", "rb").read() == open(base + "_ref.csv", "rb").read()
    return ruta, nticks, igual, completo


def rtl_serie(args):
    """La serie por el RTL con Verilator, con una copia del testbench oficial.

    La copia cambia las cinco líneas de tools/equiv.sh (programa, serie, período, largo y
    archivo de salida) y una más: el arreglo de la serie, que en el oficial tiene 20 000
    precios fijos (tb/tb_proyecto_4.sv:37). Con series más largas Verilator escribe fuera
    del arreglo y el testbench manda otros precios: así falló la primera corrida.
    """
    ruta, periodo, nticks, etiqueta = args
    d = os.path.join(RAIZ, "build", "exhaustivo", "rtl_r0", etiqueta)
    os.makedirs(d, exist_ok=True)
    tb = open(os.path.join(RAIZ, "tb", "tb_proyecto_4.sv")).read()
    c = re.sub(r'PROGRAMA   = "[^"]*";', 'PROGRAMA   = "sw/trade.hex";', tb)
    c = re.sub(r'SERIE      = "[^"]*";', f'SERIE      = "{ruta}";', c)
    c = re.sub(r"PERIODO_NS = [0-9]*;", f"PERIODO_NS = {periodo};", c)
    c = re.sub(r"NTICKS     = [0-9]*;", f"NTICKS     = {nticks};", c)
    c = c.replace("int precio [20000];", "int precio [NTICKS];").replace('"decisiones.csv"', f'"{d}/tb.csv"')
    cambiadas = sum(1 for a, b in zip(tb.splitlines(), c.splitlines()) if a != b)
    if cambiadas != 6:
        return ruta, nticks, False, f"FAIL {etiqueta}: la copia del testbench cambia {cambiadas} lineas (se esperaban 6)"
    open(f"{d}/tb_p4.sv", "w").write(c)
    fuentes = [f"rtl/{f}" for f in sorted(os.listdir(os.path.join(RAIZ, "rtl"))) if f.endswith(".v") and not f.startswith("00_")] + \
        [f"rtl/espino_core/{f}" for f in sorted(os.listdir(os.path.join(RAIZ, "rtl/espino_core"))) if f.endswith(".v")]
    celdas = subprocess.run(["yosys-config", "--datdir"], capture_output=True, text=True).stdout.strip() + "/ice40/cells_sim.v"
    if subprocess.run(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", "tb_proyecto_4",
                       "-DNO_ICE40_DEFAULT_ASSIGNMENTS", "-O3", "--Mdir", f"{d}/obj", "-o", "sim", celdas, *fuentes, f"{d}/tb_p4.sv"],
                      cwd=RAIZ, capture_output=True).returncode:
        return ruta, nticks, False, f"FAIL {etiqueta}: Verilator no compila"
    sal = subprocess.run([f"{d}/obj/sim"], cwd=RAIZ, capture_output=True, text=True).stdout
    subprocess.run([sys.executable, "ref/trader.py", ruta, "--nticks", str(nticks), "--periodo-ns", str(periodo),
                    "-o", f"{d}/ref.csv"], cwd=RAIZ, capture_output=True)
    m = re.search(r"Testbenchs aprobados: (\d+)/(\d+)", sal)
    pc = re.search(r"Peor caso precio->decision: (\d+) ciclos \(disponibles: (\d+)\)", sal)
    cuatro = bool(m) and m.group(1) == m.group(2) == "4"
    iguales = os.path.exists(f"{d}/tb.csv") and columnas_decision(f"{d}/tb.csv") == columnas_decision(f"{d}/ref.csv")
    completo = iguales and open(f"{d}/tb.csv", "rb").read() == open(f"{d}/ref.csv", "rb").read()
    txt = (f"{'PASS' if cuatro and iguales else 'FAIL'} {etiqueta}: {nticks} ticks a {periodo} ns, {m.group(0) if m else '?'}, "
           f"peor caso {pc.group(1) if pc else '?'} de {pc.group(2) if pc else '?'} ciclos, bytes de decision "
           f"{'identicos' if iguales else 'DISTINTOS'} a ref/trader.py"
           + ("" if completo or not iguales else " (la contabilidad de 32 bits del testbench se desborda en esta serie)"))
    return ruta, nticks, cuatro and iguales, txt

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default="build/exhaustivo/series")
    ap.add_argument("--periodo-ns", type=int, default=12000)
    ap.add_argument("--rtl", action="store_true")
    ap.add_argument("--rtl-esquina", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--salida", default="docs/mediciones/noche/exhaustivo_r0.txt")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    t0 = time.time()
    per = a.periodo_ns
    perd = trader.ticks_perdidos(per)
    largas = sorted(os.path.join(a.dir, f) for f in os.listdir(a.dir) if f.startswith("serie_") and f.endswith(".csv"))
    esquina = [list(map(int, l.split())) for l in open(os.path.join(a.dir, "esquina.txt")) if l.strip()]
    lineas = ["Verificacion exhaustiva de la regla de decision de R0 (sw/trade.s, max_media)",
              f"Generado por tools/exhaustivo/r0.py {' '.join(argv if argv is not None else sys.argv[1:])}.",
              f"Series de tools/exhaustivo/r0_cubrir.c: {len(largas)} largas y {len(esquina)} cortas (la esquina). "
              f"Periodo {per} ns: el programa pierde los primeros {perd} precios durante el reset.", ""]
    subprocess.run(["cc", "-O2", "-o", "build/gemelo", "ref/gemelo/gemelo.c"], check=True)
    subprocess.run([sys.executable, "tools/pochoasm.py", "sw/trade.s", "-o", "build/exhaustivo/trade.hex"], check=True,
                   capture_output=True)
    if open("build/exhaustivo/trade.hex").read() != open("sw/trade.hex").read():
        lineas.append("FAIL sw/trade.hex no corresponde a sw/trade.s")
    # 1. cobertura con la referencia
    datos = [(leer_csv(r), perd) for r in largas] + [(s, perd) for s in esquina]
    with Pool(a.jobs * 2) as pool:
        res = pool.map(cobertura, datos)
    total = bytearray(len(res[0][0]))
    pasos = 0
    for v, n in res:
        pasos += n
        for i, b in enumerate(v):
            if b:
                total[i] |= b
    cubiertas = sum(bin(b).count("1") for b in total)
    # alcanzables: se recalculan aquí por anchura, independiente del generador
    alc = set(2 * 32 * p0 for p0 in range(1, 256))
    cola = list(alc)
    while cola:
        nueva = []
        for i in cola:
            S, pos = i >> 1, i & 1
            for p in range(1, 256):
                dev = 32 * p - S
                np_ = (pos | (dev < -96)) & (dev < 1)
                j = 2 * (S + p - ((S + 31) >> 5)) + np_
                if j not in alc:
                    alc.add(j)
                    nueva.append(j)
        cola = nueva
    esperadas = len(alc) * 255
    fuera = 0
    for i in range(len(total) * 8):
        if (total[i >> 3] >> (i & 7)) & 1 and (i >> 8) not in alc:
            fuera += 1
    lineas.append(f"1. Cobertura, contada con ref/trader.py: {pasos} decisiones en estado conocido, {cubiertas} combinaciones "
                  f"(S, pos, p) distintas de {esperadas} alcanzables ({len(alc)} estados por 255 precios); fuera del "
                  f"conjunto alcanzable: {fuera}.")
    lineas.append(f"   {'PASS' if cubiertas == esperadas and fuera == 0 else 'FAIL'} cobertura completa")
    # 2. gemelo
    d = "build/exhaustivo/gemelo"
    os.makedirs(d, exist_ok=True)
    with Pool(a.jobs * 2) as pool:
        g = pool.map(gemelo_serie, [(r, per, len(leer_csv(r)), d) for r in largas])
    malas = [x for x in g if not x[2]]
    desborde = [os.path.basename(x[0]) for x in g if x[2] and not x[3]]
    lineas.append(f"2. Gemelo, series largas: {len(g)} series, {sum(x[1] for x in g)} ticks; con algun byte de decision distinto "
                  f"a ref/trader.py: {len(malas)}. Con la contabilidad de 32 bits desbordada (decisiones iguales): "
                  f"{', '.join(desborde) if desborde else 'ninguna'}")
    for x in malas[:5]:
        lineas.append(f"   FAIL {x[0]}")
    ruta_lote = os.path.join(a.dir, "esquina.txt")
    gl = subprocess.run(["build/gemelo", "--hex", "sw/trade.hex", "--lote", ruta_lote, "--bytes", "--periodo-ns", str(per)],
                        capture_output=True, text=True, check=True).stdout.splitlines()
    malas_e = 0
    for s, linea in zip(esquina, gl):
        leido = bytes.fromhex(linea.split()[8])
        if leido != bytes(trader.decisiones(s, trader.MaxMedia(), perd)):
            malas_e += 1
    lineas.append(f"   Gemelo, esquina: {len(esquina)} series cortas; distintas a ref/trader.py: {malas_e + abs(len(gl) - len(esquina))}")
    lineas.append(f"   {'PASS' if not malas and malas_e == 0 and len(gl) == len(esquina) else 'FAIL'} gemelo")
    # 3. RTL
    if a.rtl:
        trabajos = [(r, per, len(leer_csv(r)), f"ex_r0_{i:02d}") for i, r in enumerate(largas)]
        trabajos.sort(key=lambda x: -x[2])
        with Pool(a.jobs) as pool:
            rr = pool.map(rtl_serie, trabajos, chunksize=1)
        malas = [x for x in rr if not x[2]]
        lineas.append(f"3. RTL con Verilator, copia del testbench oficial a {per} ns: {len(rr)} series, "
                      f"{sum(x[1] for x in rr)} ticks; con 4/4 y decisiones.csv identico a ref/trader.py: {len(rr) - len(malas)}")
        for x in sorted(rr):
            lineas.append(f"   {x[3]}")
        lineas.append(f"   {'PASS' if not malas else 'FAIL'} RTL, series largas")
    if a.rtl_esquina:
        rng = random.Random(17)
        muestra = rng.sample(range(len(esquina)), min(a.rtl_esquina, len(esquina)))
        os.makedirs("build/exhaustivo/esquina", exist_ok=True)
        trabajos = []
        for i in muestra:
            ruta = f"build/exhaustivo/esquina/e{i:05d}.csv"
            with open(ruta, "w") as f:
                f.write("tick,price\n" + "".join(f"{t},{p}\n" for t, p in enumerate(esquina[i])))
            trabajos.append((ruta, per, len(esquina[i]), f"ex_r0_e{i:05d}"))
        with Pool(a.jobs) as pool:
            rr = pool.map(rtl_serie, trabajos, chunksize=1)
        malas = [x for x in rr if not x[2]]
        lineas.append(f"   RTL, esquina: {len(rr)} series cortas al azar (semilla 17) de {len(esquina)}; con 4/4 e identicas: "
                      f"{len(rr) - len(malas)}")
        for x in malas[:5]:
            lineas.append(f"   {x[3]}")
        lineas.append(f"   {'PASS' if not malas else 'FAIL'} RTL, esquina")
    lineas.append("")
    lineas.append(f"Tiempo: {time.time() - t0:.0f} s.")
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    os.makedirs(os.path.dirname(a.salida), exist_ok=True)
    with open(a.salida, "w", newline="\n") as f:
        f.write(texto)


if __name__ == "__main__":
    main()
