#!/usr/bin/env python3
"""retune.py: kit de contingencia para un cambio de reglas anunciado el día de
la competencia (paquete P8, docs/arbol_decision.md).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Recibe la comisión, la caja inicial y lo que se sepa de la ronda (cuántos
ticks dura), y:

  1. Busca los umbrales de `max_media` (entra y sale, en unidades de precio)
     que mejor rinden con esas reglas, en los bloques de la práctica y en las
     cuatro familias sintéticas plausibles (ref/series.py), y los compara con
     los actuales (entra 3, sale 0) bajo las mismas reglas. Con el principio
     4 del proyecto: elige otros solo si suben la media en más de 0,2 % sin
     bajar el percentil 5 ni el peor bloque de la práctica. Si no, deja los
     actuales. Con las reglas publicadas (comisión 5, caja 10 000) tiene que
     dejar los actuales: es el control de la herramienta.
  2. Con los umbrales elegidos arma, sin sintetizar, los bitstreams de la
     escalera con icebram sobre los moldes guardados (bitstreams/moldes/):
     R0 con sw/trade.s ensamblado con -D UMBRAL_COMPRA y -D UMBRAL_VENTA; R1
     y R2 con otra tabla de parámetros (ref/fondo.py --param), y la imagen
     múltiple de R2 con el R0 nuevo de respaldo.
  3. Corre una equivalencia rápida en el gemelo: la práctica a 0,1 ms y una
     serie de cada familia plausible, contra ref/trader.py y ref/fondo.py con
     los parámetros nuevos.
  4. Con --simular, simula además los .asc nuevos por los pines (2000 ticks,
     unos 40 minutos). Un bitstream cambiado no hereda la puerta de
     simulación: sin este paso no debería grabarse (docs/tabla_vigilante.md).

Las decisiones del programa no dependen de la caja ni de la comisión (no
lleva contabilidad): lo que cambia es cuánto cuesta operar y, con ello, qué
umbral conviene. Los gestores 2 y 3 del fondo se corren con el supervisor:
quedan una unidad más abajo y más arriba, como en la tabla actual.

Uso:
    python3 tools/retune.py --comision 10 --caja 10000
    python3 tools/retune.py --comision 5 --caja 1000 --largo 500 --simular
    python3 tools/retune.py --comision 20 --forzar 5,1       # sin buscar
Resultado en build/retune/c<comision>_k<caja>_n<largo>/ (bitstreams, tabla,
programa y RESUMEN.txt). Unos 2 minutos sin --simular.
"""
import argparse
import hashlib
import multiprocessing
import os
import shutil
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "ref"))

import fondo     # noqa: E402
import market    # noqa: E402
import series    # noqa: E402
import trader    # noqa: E402

ACTUAL = (3, 0)
GRILLA_ENTRA = (1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 24, 63)    # 63: casi no opera
GRILLA_SALE = (-1, 0, 1, 2, 3, 4)
MOLDES = "bitstreams/moldes"


def conjunto(largo):
    practica = market.leer_serie("tb/practica.csv")
    bloques = series.bloques(practica, largo)
    plaus = []
    for nombre in series.PLAUSIBLES:
        plaus += series.lote(nombre, 20, n=largo, semilla=11)
    return bloques + plaus


def evaluar(arg):
    """Media, percentil 5, peor bloque de la práctica y órdenes por serie."""
    entra, sale, comision, caja, lista, nbloques = arg
    ws = []
    ordenes = 0
    for precios in lista:
        m = market.simular(precios, trader.decisiones(precios, trader.MaxMedia(entra=entra, sale=sale)), caja, comision)
        ws.append(m.w / caja)
        ordenes += m.ordenes
    peor_bloque = min(ws[:nbloques])
    ws.sort()
    return entra, sale, sum(ws) / len(ws), ws[len(ws) // 20], peor_bloque, ordenes / len(ws)


def params_fondo(entra, sale):
    """La tabla del fondo con el supervisor y el gestor 1 en (entra, sale), y los
    gestores 2 y 3 una unidad más abajo y más arriba, como la tabla actual."""
    return dict(S_ENTRA=-32 * entra, S_SALE=32 * sale + 1, G1_ENTRA=-32 * entra, G1_SALE=32 * sale + 1,
                G2_ENTRA=-32 * (entra + 1), G2_SALE=32 * sale + 1, G3_ENTRA=-32 * (entra - 1), G3_SALE=32 * sale + 17)


def sh(cmd, **kw):
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise SystemExit(f"FAIL: {' '.join(cmd) if isinstance(cmd, list) else cmd}\n{r.stdout}{r.stderr}")
    return r.stdout


def completar(origen, destino):
    pal = [l.strip() for l in open(os.path.join(RAIZ, origen)) if l.strip() and not l.startswith(("//", "@"))]
    pal += ["00000000"] * (512 - len(pal))
    with open(os.path.join(RAIZ, destino), "w", newline="\n") as f:
        f.write("\n".join(pal) + "\n")


def sha(ruta):
    return hashlib.sha256(open(os.path.join(RAIZ, ruta), "rb").read()).hexdigest()


def equivalencia(d, entra, sale):
    """Gemelo contra las referencias con los parámetros nuevos."""
    p = market.leer_serie("tb/practica.csv")[:2000]
    lista = [("practica", p)] + [(n, series.lote(n, 1, n=2000, semilla=12)[0]) for n in series.PLAUSIBLES]
    lote = os.path.join(d, "lote.txt")
    with open(os.path.join(RAIZ, lote), "w") as f:
        for _, precios in lista:
            f.write(" ".join(map(str, precios)) + "\n")
    perd = trader.ticks_perdidos(100000)
    lineas, ok = [], True
    for nombre, hexfile, opts, est in (
            ("R0", f"{d}/trade.hex", [], lambda: trader.MaxMedia(entra=entra, sale=sale)),
            ("R1", "build/fondo/fondo.hex", ["--barrel", "--xd", "3", "--tabla", f"{d}/tabla.hex"],
             lambda: fondo.Fondo(params_fondo(entra, sale)))):
        out = sh(["build/gemelo", *opts, "--hex", hexfile, "--lote", lote, "--bytes", "--periodo-ns", "100000"])
        for (serie, precios), fila in zip(lista, out.splitlines()):
            c = fila.split()
            leidos = bytes.fromhex(c[8])
            esperado = bytes(trader.decisiones(precios, est(), perd))
            bien = leidos == esperado and int(c[4]) == len(precios) - perd and int(c[3]) < 2262
            ok &= bien
            lineas.append(f"  {'PASS' if bien else 'FAIL'} {nombre} {serie}: bytes {'iguales' if leidos == esperado else 'DISTINTOS'}, "
                          f"respuestas {c[4]}, peor caso {c[3]} ciclos de 2262")
    return ok, lineas


def simular_asc(d, nombre, asc, est, nticks=2000):
    """El .asc por los pines con tb/tb_bitstream.sv, contra la referencia."""
    s = os.path.join(d, f"sim_{nombre}")
    os.makedirs(os.path.join(RAIZ, s), exist_ok=True)
    cells = subprocess.check_output(["yosys-config", "--datdir"], text=True).strip() + "/ice40/cells_sim.v"
    sh([sys.executable, "tools/chip_vlog.py", asc, "goboard.pcf", "-o", f"{s}/chip.v"])
    sh(["iverilog", "-g2012", "-s", "tb_bitstream", f"-DNTICKS={nticks}", "-DPERIODO_NS=100000",
        '-DSERIE="tb/practica.csv"', f'-DSALIDA="{s}/bytes.csv"', "-o", f"{s}/sim", cells, f"{s}/chip.v",
        "tb/tb_bitstream.sv"])
    log = sh(["vvp", "-n", f"{s}/sim"])
    leidos = [int(l.split(",")[2], 16) for l in open(os.path.join(RAIZ, s, "bytes.csv")).read().split("\n")[1:] if l]
    precios = market.leer_serie("tb/practica.csv")[:nticks]
    esperado = trader.decisiones(precios, est, trader.ticks_perdidos(100000))
    return leidos == esperado and "Bits de MISO con X: 0" in log


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--comision", type=int, default=market.COMISION)
    ap.add_argument("--caja", type=int, default=market.CAJA0)
    ap.add_argument("--largo", type=int, default=2000, help="ticks por ronda, si se sabe (2000)")
    ap.add_argument("--forzar", help="usar estos umbrales sin buscar: ENTRA,SALE")
    ap.add_argument("--simular", action="store_true", help="simular los .asc nuevos por los pines (40 minutos)")
    ap.add_argument("--control", action="store_true",
                    help="exigir que los umbrales queden iguales y los .bin sean los de bitstreams/ (con las reglas publicadas)")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    t0 = time.time()
    d = f"build/retune/c{a.comision}_k{a.caja}_n{a.largo}"
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    viejo = lambda obj, *fuentes: (not os.path.exists(obj) or  # noqa: E731
                                   any(os.path.getmtime(f) > os.path.getmtime(obj) for f in fuentes))
    if viejo("build/gemelo", "ref/gemelo/gemelo.c") or viejo("build/fondo/fondo.hex", "sw/fondo.s"):
        sh(["make", "-s", "build/gemelo", "fondo-hex"])
    res = []
    lin = [f"retune: comision {a.comision}, caja {a.caja}, rondas de {a.largo} ticks",
           "Generado por tools/retune.py. Patrimonio final dividido por la caja inicial.", ""]

    # --- 1. Umbrales ---------------------------------------------------------------
    lista = conjunto(a.largo)
    nb = len(lista) - 80                                              # bloques de la práctica
    if a.forzar:
        elegido = tuple(int(x) for x in a.forzar.split(","))
        trabajos = [(*elegido, a.comision, a.caja, lista, nb), (*ACTUAL, a.comision, a.caja, lista, nb)]
    else:
        trabajos = [(e, s, a.comision, a.caja, lista, nb) for e in GRILLA_ENTRA for s in GRILLA_SALE if e + s >= 1]
    with multiprocessing.Pool(min(20, os.cpu_count())) as pool:
        res = pool.map(evaluar, trabajos)
    actual = next(r for r in res if (r[0], r[1]) == ACTUAL)
    candidatos = [r for r in res if r[3] >= actual[3] - 1e-9 and r[4] >= actual[4] - 1e-9]
    mejor = max(candidatos, key=lambda r: r[2])
    if a.forzar:
        mejor = next(r for r in res if (r[0], r[1]) == elegido)
    elif mejor[2] < actual[2] + 0.002:                                # menos de 0,2 % no justifica cambiar
        mejor = actual
    entra, sale = mejor[0], mejor[1]
    lin += [f"Series: {len(lista)} ({len(lista) - 80} bloques de la practica y 80 de las familias plausibles)",
            f"{'entra':>5s} {'sale':>5s} {'media':>7s} {'p5':>7s} {'peor bloque':>11s} {'ordenes':>8s}"]
    vista = sorted(res, key=lambda r: -r[2])[:8]
    for r in (actual, mejor):
        if r not in vista:
            vista.append(r)
    for r in vista:
        marca = " <- actual" if (r[0], r[1]) == ACTUAL else ""
        marca += " <- elegido" if (r[0], r[1]) == (entra, sale) else ""
        lin.append(f"{r[0]:5d} {r[1]:5d} {r[2]:7.4f} {r[3]:7.4f} {r[4]:11.4f} {r[5]:8.1f}{marca}")
    cambia = (entra, sale) != ACTUAL
    lin += ["", f"Umbrales elegidos: entra {entra}, sale {sale}" +
            ("" if cambia else " (los actuales: no conviene cambiar nada)"),
            f"  UMBRAL_COMPRA = {-32 * entra}, UMBRAL_VENTA = {32 * sale + 1}", ""]

    # --- 2. Bitstreams con icebram sobre los moldes --------------------------------
    sh([sys.executable, "tools/pochoasm.py", "sw/trade.s", "-D", f"UMBRAL_COMPRA={-32 * entra}",
        "-D", f"UMBRAL_VENTA={32 * sale + 1}", "-o", f"{d}/trade_asm.hex"])
    completar(f"{d}/trade_asm.hex", f"{d}/trade.hex")
    pf = params_fondo(entra, sale)
    sh([sys.executable, "ref/fondo.py", *sum((["--param", f"{k}={v}"] for k, v in pf.items()), []),
        "--tabla-hex", f"{d}/tabla.hex"])
    completar("build/fondo/fondo.hex", f"{d}/fondo512.hex")
    for f in ("r0_molde.asc.gz", "r1_molde.asc.gz", "r2_molde.asc.gz", "molde_prog_r0.hex", "molde_prog.hex",
              "molde_tabla.hex"):
        if not os.path.exists(os.path.join(MOLDES, f)):
            raise SystemExit(f"FAIL: falta {MOLDES}/{f} (make r0-molde o make fondo-bitstreams)")
    t1 = time.time()
    for r in ("r0", "r1", "r2"):
        sh(f"gunzip -c {MOLDES}/{r}_molde.asc.gz > {d}/{r}_molde.asc", shell=True)
    sh(f"icebram {MOLDES}/molde_prog_r0.hex {d}/trade.hex < {d}/r0_molde.asc > {d}/r0.asc", shell=True)
    for r in ("r1", "r2"):
        sh(f"icebram {MOLDES}/molde_prog.hex {d}/fondo512.hex < {d}/{r}_molde.asc | "
           f"icebram {MOLDES}/molde_tabla.hex {d}/tabla.hex > {d}/{r}.asc", shell=True)
    for r in ("r0", "r1", "r2"):
        sh(["icepack", f"{d}/{r}.asc", f"{d}/{r}.bin"])
    sh(["icemulti", "-p0", "-o", f"{d}/r2_multi.bin", f"{d}/r2.bin", f"{d}/r0.bin"])
    lin.append(f"Bitstreams con icebram sobre los moldes: {time.time() - t1:.2f} s")
    if not cambia:
        iguales = all(sha(f"{d}/{r}.bin") == sha(f"bitstreams/{n}") for r, n in
                      (("r0", "r0_base_max_media.bin"), ("r1", "r1_fondo.bin"), ("r2", "r2_fondo_vigilante.bin"),
                       ("r2_multi", "r2_multi.bin")))
        lin.append(f"  Con los umbrales actuales los .bin {'son' if iguales else 'NO son'} los de bitstreams/, byte por byte")
    else:
        iguales = False
    control_ok = (not a.control) or (not cambia and iguales)
    if a.control:
        lin.append(f"  {'PASS' if control_ok else 'FAIL'} control: con las reglas publicadas no cambia nada")

    # --- 3. Equivalencia rápida -------------------------------------------------------
    ok, eq = equivalencia(d, entra, sale)
    lin += ["", "Equivalencia rapida en el gemelo (0,1 ms):"] + eq
    if a.simular:
        lin.append("Simulacion de los .asc por los pines (practica, 2000 ticks, 0,1 ms):")
        with multiprocessing.Pool(3) as pool:
            sims = pool.starmap(simular_asc, [(d, "r0", f"{d}/r0.asc", trader.MaxMedia(entra=entra, sale=sale)),
                                              (d, "r1", f"{d}/r1.asc", fondo.Fondo(pf)),
                                              (d, "r2", f"{d}/r2.asc", fondo.Fondo(pf))])
        for r, bien in zip(("r0", "r1", "r2"), sims):
            ok &= bien
            lin.append(f"  {'PASS' if bien else 'FAIL'} {r}.asc")
    else:
        lin.append("Los .asc NO se simularon por los pines: correr de nuevo con --simular antes de grabar.")

    lin += ["", "Archivos (sha256):"]
    for r in ("r0", "r1", "r2", "r2_multi"):
        lin.append(f"  {d}/{r}.bin  {sha(f'{d}/{r}.bin')}")
    lin += ["", "Para grabar el peldano elegido (lo hace Nicolas):",
            f"  iceprog {d}/r1.bin          # R1",
            f"  iceprog {d}/r2_multi.bin    # R2 con R0 de respaldo",
            f"  iceprog {d}/r0.bin          # R0",
            "", f"Tiempo total: {time.time() - t0:.0f} s", f"{'PASS' if ok and control_ok else 'FAIL'}"]
    texto = "\n".join(lin) + "\n"
    print(texto, end="")
    with open(os.path.join(d, "RESUMEN.txt"), "w") as f:
        f.write(texto)
    return 0 if ok and control_ok else 1


if __name__ == "__main__":
    sys.exit(main())
