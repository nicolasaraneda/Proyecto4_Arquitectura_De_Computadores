#!/usr/bin/env python3
"""matriz.py: matriz de estrés de R0, R1 y R2 en las dimensiones que faltaban
(paquete P8, frente E del plan).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

La puerta de simulación ya cubre, por el RTL, SCLK de 100 kHz a 1 MHz, tiempos
de CS_n, reset con la maestra transmitiendo, rondas seguidas y series pegadas
(docs/mediciones/estres_base.txt para R0 y docs/mediciones/fondo/r1|r2/
estres.txt). Este script agrega, con el gemelo digital (validado contra el RTL
de R0 en make cosim y de R1 en make cosim-barrel) y las referencias:

  A. Período desde 10 ms hasta el mínimo que soporta cada peldaño.
  B. SCLK de 100 kHz a 1 MHz en cada uno de los tres períodos.
  C. Rondas de 500 a 200 000 ticks.
  D. Comisión de 0 a 50 y caja inicial de 1 000 a 100 000: patrimonio contra
     comprar y mantener y contra no operar, en los 10 bloques de la práctica y
     en las 14 familias sintéticas. Las decisiones no dependen de la caja ni
     de la comisión (el programa no lleva contabilidad), así que esta parte es
     del algoritmo: se calcula con las referencias.

Cada celda de A, B y C exige lo mismo que la matriz de la puerta: los bytes
que lee la maestra iguales a los de la referencia, ningún precio sin leer ni
sin respuesta, y el peor caso dentro del presupuesto. R2 es R1 más el
vigilante, que el gemelo no modela: el vigilante solo se dispara si llegan 5
precios sin ninguna escritura en DECISION, y en toda celda donde R1 responde
a cada precio (columna "sin respuesta" en 0) no puede dispararse. Por eso la
columna de R2 se deduce de la de R1, y la matriz de la puerta lo confirma por
el RTL en sus 56 casos.

Uso: python3 tools/p8/matriz.py [--rapida]   (make p8-matriz)
Resultado en docs/mediciones/p8/matriz.txt y docs/mediciones/p8/matriz.csv.
"""
import argparse
import multiprocessing
import os
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, os.path.join(RAIZ, "tools"))

import estres    # noqa: E402
import fondo     # noqa: E402
import market    # noqa: E402
import series    # noqa: E402
import trader    # noqa: E402

PELDANOS = [
    # nombre, programa, opciones del gemelo, referencia
    ("R0", "sw/trade.hex", "", "trader"),
    ("R1", "build/fondo/fondo.hex", "--barrel --xd 3 --tabla sw/fondo_tabla.hex", "fondo"),
]
D = "build/p8/matriz"


def correr(arg):
    peldano, caso = arg
    nombre, hexfile, opts, ref = next(p for p in PELDANOS if p[0] == peldano)
    os.makedirs(os.path.join(RAIZ, D, peldano), exist_ok=True)
    n, ok, det, peor, _ = estres.correr((None, os.path.join(D, peldano), caso, ref, ("gemelo", hexfile, opts)))
    return peldano, caso["grupo"], caso["nombre"], ok, det, peor


def caso(grupo, nombre, precios, **kw):
    c = estres.base(nombre, precios, **kw)
    c["grupo"] = grupo
    return c


def casos_tiempo(rapida):
    p = market.leer_serie("tb/practica.csv")
    c = []
    # A. Período: de 10 ms al mínimo (con SCLK de 1 MHz)
    for per in (10_000_000, 1_000_000, 100_000, 50_000, 30_000, 27_000, 20_000, 15_000, 11_500):
        nt = 300 if per >= 1_000_000 and rapida else 2000
        c.append(caso("A_periodo", f"periodo_{per}ns", p[:nt], PERIODO_NS=per))
    # B. SCLK por período
    for khz in (100, 115, 200, 500, 1000):
        medio = round(500000 / khz)
        for per in (100_000, 1_000_000, 10_000_000):
            nt = 300 if per >= 1_000_000 and rapida else 2000
            c.append(caso("B_sclk", f"sclk_{khz}k_periodo_{per // 1000}us", p[:nt], PERIODO_NS=per,
                          SCLK_MEDIO_NS=medio, CS_SETUP_NS=max(1500, 3 * medio)))
    # C. Largo de la ronda, a 0,1 ms, con series del modelo ajustado a la práctica
    for largo in ((500, 2000, 20000) if rapida else (500, 2000, 20000, 200000)):
        precios = series.lote("modelo", 1, n=largo, semilla=8)[0]
        c.append(caso("C_largo", f"ronda_{largo}_ticks", precios))
    return c


def economia(arg):
    """Patrimonio de un peldaño en un conjunto de series, para cada comisión y caja.

    Las decisiones se calculan una sola vez por serie: no dependen de la caja ni
    de la comisión."""
    peldano, conjunto, lista = arg
    decs = []
    for precios in lista:
        est = trader.Oficial() if peldano == "R0" else fondo.Fondo()
        decs.append(trader.decisiones(precios, est))
    salida = []
    for comision in (0, 5, 10, 20, 50):
        for caja in (1000, 10000, 100000):
            filas = []
            for precios, dec in zip(lista, decs):
                m = market.simular(precios, dec, caja, comision)
                filas.append((m.w, market.comprar_y_mantener(precios, caja, comision), m.ordenes))
            k = len(filas)
            salida.append((peldano, comision, caja, conjunto, sum(f[0] for f in filas) / k / caja,
                           min(f[0] for f in filas) / caja, sum(f[1] for f in filas) / k / caja,
                           sum(f[0] > f[1] for f in filas) / k, sum(f[0] > caja for f in filas) / k,
                           sum(f[2] for f in filas) / k))
    return salida


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapida", action="store_true", help="menos ticks en los períodos largos y sin la ronda de 200 000")
    ap.add_argument("--salida", default="docs/mediciones/p8", help="carpeta de salida (la rápida va a build/p8)")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    t0 = time.time()
    subprocess.run(["make", "-s", "build/gemelo", "fondo-hex"], check=True, stdout=subprocess.DEVNULL)
    os.makedirs(a.salida, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()

    trabajos = [(pel[0], c) for c in casos_tiempo(a.rapida) for pel in PELDANOS]
    practica = market.leer_serie("tb/practica.csv")
    conjuntos = {"practica_10_bloques": series.bloques(practica, 2000)}
    fam = []
    for nombre in series.FAMILIAS:
        fam += series.lote(nombre, 4 if a.rapida else 20, n=2000, semilla=8)
    conjuntos["familias_14"] = fam
    eco = [(pel, nom, lista) for pel in ("R0", "R1") for nom, lista in conjuntos.items()]

    with multiprocessing.Pool(min(20, os.cpu_count())) as pool:
        res = pool.map(correr, trabajos, chunksize=1)
        res_eco = sorted((f for grupo in pool.map(economia, eco, chunksize=1) for f in grupo),
                         key=lambda f: (f[1], f[2], f[3], f[0]))

    lin = ["Matriz de estres de R0, R1 y R2: periodo, SCLK, largo de ronda, comision y caja",
           "Generado por tools/p8/matriz.py (make p8-matriz). No editar a mano.", "",
           f"Commit de partida: {commit}. Motor: gemelo digital (build/gemelo), referencias ref/trader.py y ref/fondo.py.",
           "R2 = R1 en el gemelo; el vigilante no puede dispararse en una celda con 'sin respuesta 0' (ver el encabezado).",
           f"Modo: {'rapido' if a.rapida else 'completo'}", ""]
    csv = ["grupo,celda,peldano,resultado,peor_ciclos,detalle"]
    fallas = 0
    por_celda = {}
    for pel, grupo, nombre, ok, det, peor in res:
        por_celda.setdefault((grupo, nombre), {})[pel] = (ok, det, peor)
    grupo_actual = None
    for (grupo, nombre), v in por_celda.items():
        if grupo != grupo_actual:
            titulo = {"A_periodo": "A. Periodo (SCLK de 1 MHz, practica)",
                      "B_sclk": "B. SCLK por periodo (practica)",
                      "C_largo": "C. Largo de la ronda a 0,1 ms (serie del modelo, semilla 8)"}[grupo]
            lin += ["", f"== {titulo}", f"{'celda':34s} {'R0':8s} {'R1':8s} {'R2':8s}  detalle de R1"]
            grupo_actual = grupo
        r0, r1 = v["R0"], v["R1"]
        r2_ok = r1[0] or ("sin respuesta 0" in r1[1])
        e = lambda ok: "pasa" if ok else "no pasa"   # noqa: E731
        lin.append(f"{nombre:34s} {e(r0[0]):8s} {e(r1[0]):8s} {e(r1[0]):8s}  {r1[1]}")
        if not r2_ok:
            lin.append(f"{'':34s} ATENCION: en R2 el vigilante podria dispararse en esta celda")
        for pel, (ok, det, peor) in (("R0", r0), ("R1", r1), ("R2", r1)):
            csv.append(f"{grupo},{nombre},{pel},{'pasa' if ok else 'no pasa'},{peor},\"{det}\"")

    # Resumen de A: período mínimo que pasa
    lin += ["", "Periodo minimo que pasa en A (SCLK de 1 MHz):"]
    for pel in ("R0", "R1"):
        pasan = [int(n.split("_")[1][:-2]) for (g, n), v in por_celda.items() if g == "A_periodo" and v[pel][0]]
        m = min(pasan) if pasan else None
        lin.append(f"  {pel}: {m} ns ({100000 / m:.2f} veces mas rapido que la ronda 3)" if m else f"  {pel}: ninguno")
    lin.append("  (el minimo exacto, en pasos de 40 ns, esta en docs/mediciones/fondo/r1/sclk_minimo.txt)")

    # Celdas que deben pasar: todo lo que deja 600 ciclos o más (como la matriz de la puerta)
    lin += ["", "Celdas que cuentan (al menos 600 ciclos entre transacciones, como la matriz de la puerta):"]
    for (grupo, nombre), v in por_celda.items():
        for pel in ("R0", "R1"):
            ok, det, peor = v[pel]
            presu = int(det.split(" de ")[-1])
            if presu >= 600 and not ok:
                fallas += 1
                lin.append(f"  FAIL {pel} {nombre}: {det}")
    if fallas == 0:
        lin.append("  todas pasan")

    lin += ["", "== D. Comision y caja inicial (patrimonio final dividido por la caja inicial)",
            "Las decisiones no dependen de la caja ni de la comision; cambia lo que cuestan.",
            f"{'peldano':7s} {'comision':>8s} {'caja':>7s} {'conjunto':20s} {'media':>7s} {'peor':>7s} "
            f"{'cym':>7s} {'>cym':>6s} {'>nada':>6s} {'ordenes':>8s}"]
    csv_eco = ["peldano,comision,caja,conjunto,media,peor,media_cym,frac_supera_cym,frac_supera_no_operar,ordenes"]
    for pel, com, caja, nom, media, peor, cym, g_cym, g_nada, ordenes in res_eco:
        lin.append(f"{pel:7s} {com:8d} {caja:7d} {nom:20s} {media:7.3f} {peor:7.3f} {cym:7.3f} {g_cym:6.2f} "
                   f"{g_nada:6.2f} {ordenes:8.1f}")
        csv_eco.append(f"{pel},{com},{caja},{nom},{media:.4f},{peor:.4f},{cym:.4f},{g_cym:.3f},{g_nada:.3f},{ordenes:.1f}")

    lin += ["", f"Tiempo total: {time.time() - t0:.0f} s",
            f"{'PASS' if fallas == 0 else 'FAIL'}: {fallas} celdas que cuentan no pasan"]
    texto = "\n".join(lin) + "\n"
    print(texto, end="")
    with open(os.path.join(a.salida, "matriz.txt"), "w") as f:
        f.write(texto)
    with open(os.path.join(a.salida, "matriz.csv"), "w") as f:
        f.write("\n".join(csv) + "\n")
    with open(os.path.join(a.salida, "economia.csv"), "w") as f:
        f.write("\n".join(csv_eco) + "\n")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
