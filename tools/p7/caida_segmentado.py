#!/usr/bin/env python3
"""caida_segmentado.py: piezas de tools/p7/caida_segmentado.sh.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Subcomandos:
  huella SOC.JSON
      Huella de la netlist de Yosys: tipo, parámetros y conexiones de cada
      celda, sin los atributos (que llevan rutas y números de línea). Dos
      netlists con la misma huella dan la misma colocación en nextpnr.
  orden K ARCHIVO...
      Los archivos en el orden de lectura número K (K = 0 es el orden dado;
      K > 0 es una permutación con semilla K).
  informe DIR SEMILLAS SEMILLAS_ORDEN
      Lee DIR/commits.txt, DIR/corridas.txt y DIR/equiv.txt y escribe el
      cuerpo del informe por la salida estándar.

Solo biblioteca estándar.
"""
import hashlib
import json
import math
import os
import random
import re
import sys


def huella(ruta):
    with open(ruta, encoding="utf-8") as f:
        m = json.load(f)["modules"]["pochoco_soc"]
    celdas = sorted(
        (n, c["type"], json.dumps(c.get("parameters", {}), sort_keys=True),
         json.dumps(c["connections"], sort_keys=True))
        for n, c in m["cells"].items())
    return hashlib.sha256(repr(celdas).encode()).hexdigest()[:12]


# --- estadística -------------------------------------------------------------

def mediana(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def cuantil(v, q):
    """Cuantil por interpolación lineal (el tipo 7 de R y de numpy)."""
    v = sorted(v)
    h = (len(v) - 1) * q
    i = int(math.floor(h))
    return v[i] if i + 1 >= len(v) else v[i] + (h - i) * (v[i + 1] - v[i])


def desv(v):
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def mann_whitney(a, b):
    """U de a sobre b (cuántos pares a > b, los empates valen 1/2), z con la
    aproximación normal corregida por empates y p de dos colas."""
    n1, n2 = len(a), len(b)
    u = sum((x > y) + 0.5 * (x == y) for x in a for y in b)
    todos = sorted(a + b)
    empates = {}
    for x in todos:
        empates[x] = empates.get(x, 0) + 1
    n = n1 + n2
    corr = sum(t ** 3 - t for t in empates.values()) / (n * (n - 1))
    sigma = math.sqrt(n1 * n2 / 12 * ((n + 1) - corr))
    z = (u - n1 * n2 / 2) / sigma
    p = math.erfc(abs(z) / math.sqrt(2))
    return u, z, p


# --- logs de nextpnr ---------------------------------------------------------

def leer_fmax(ruta):
    with open(ruta) as f:
        return [float(x) for x in f.read().split()]


def ruta_critica(log):
    """Resumen de la última ruta crítica reloj a reloj del log de nextpnr."""
    with open(log, errors="replace") as f:
        lineas = f.read().splitlines()
    ini = [i for i, l in enumerate(lineas) if "Critical path report for clock" in l]
    if not ini:
        return None
    pasos, fuentes_rtl = [], []
    origen = destino = None
    for l in lineas[ini[-1] + 1:]:
        t = l[len("Info:"):] if l.startswith("Info:") else l
        if "Critical path report" in t or "Max frequency" in t or not l.startswith("Info:"):
            break
        m = re.match(r"\s+(clk-to-q|logic|routing|setup)\s+([0-9.]+)\s+([0-9.]+)\s+(Source|Net|Sink)?\s*(\S+)?", t)
        if m:
            pasos.append((m.group(1), float(m.group(2)), float(m.group(3))))
            if m.group(4) == "Source" and origen is None:
                origen = m.group(5)
            continue
        m = re.match(r"\s+Sink\s+(\S+)", t)
        if m:
            destino = m.group(1)
            continue
        m = re.match(r"\s+(rtl/\S+?\.v)", t)
        if m:
            arch = os.path.basename(m.group(1))
            if arch not in fuentes_rtl:
                fuentes_rtl.append(arch)
    logica = sum(c for tipo, c, _ in pasos if tipo == "logic")
    ruteo = sum(c for tipo, c, _ in pasos if tipo == "routing")
    otros = sum(c for tipo, c, _ in pasos if tipo in ("clk-to-q", "setup"))
    return {
        "niveles": sum(1 for tipo, _, _ in pasos if tipo == "logic"),
        "logica": logica, "ruteo": ruteo, "otros": otros,
        "total": pasos[-1][2] if pasos else 0.0,
        "origen": origen, "destino": destino, "rtl": fuentes_rtl,
    }


def corto(nombre, n=60):
    if nombre is None:
        return "?"
    return nombre if len(nombre) <= n else nombre[:n - 3] + "..."


# --- informe -----------------------------------------------------------------

def informe(d, semillas, semillas_orden):
    commits = []   # (etiqueta, sha, fecha, asunto, huella, lut, carry, dff, ram, hex)
    with open(os.path.join(d, "commits.txt"), encoding="utf-8") as f:
        for l in f:
            if l.strip():
                commits.append(l.rstrip("\n").split("|"))
    corridas = []  # (etiqueta, descripcion, dir_variante, sha)
    with open(os.path.join(d, "corridas.txt"), encoding="utf-8") as f:
        for l in f:
            if l.strip():
                corridas.append(l.rstrip("\n").split("|"))

    p = print
    p("1. Netlist del segmentado en cada commit que cambio rtl/, sw/trade.hex, goboard.pcf")
    p("   o tools/medir_variante.sh desde la medicion de P1 (sintesis sola, sin nextpnr)")
    p()
    p("  commit   fecha        LUT4 CARRY  FF  BRAM  huella netlist  huella trade.hex  asunto")
    for c in commits:
        etq, sha, fecha, asunto, hu, lut, carry, dff, ram, hx = c
        p(f"  {sha:8} {fecha:11} {lut:>5} {carry:>5} {dff:>3} {ram:>5}  {hu:14}  {hx:16}  {corto(asunto, 48)}")
    p()
    p("  La huella de la netlist es el sha256 de tipo, parametros y conexiones de cada celda,")
    p("  sin atributos. Commits con la misma huella dan la misma frecuencia en cada semilla.")
    p()

    datos = {}
    for etq, desc, dv, sha in corridas:
        f = leer_fmax(os.path.join(dv, "fmax.txt"))
        with open(os.path.join(dv, "linea.txt")) as g:
            linea = g.read()
        lc = re.search(r"celdas +([0-9?]+)", linea).group(1)
        lut = re.search(r"LUT4 +([0-9?]+)", linea).group(1)
        cierran = re.search(r"cierran a 25 MHz (\d+) de", linea).group(1)
        datos[etq] = dict(desc=desc, dv=dv, sha=sha, f=f, lc=lc, lut=lut, cierran=cierran,
                          hu=huella(os.path.join(dv, "soc.json")))

    principales = [c for c in corridas if not c[0].startswith("orden")]
    ordenes = [c for c in corridas if c[0].startswith("orden")]

    p(f"2. Frecuencia maxima (MHz) del segmentado, semillas 1 a 10 y 1 a {semillas}")
    p()
    p(f"  {'corrida':8} {'commit':8} {'celdas':>6} {'LUT4':>5} | {'1 a 10: min':>11} {'mediana':>7} {'max':>6} |"
      f" {'1 a ' + str(semillas) + ': min':>11} {'p10':>6} {'mediana':>7} {'media':>6} {'desv':>5} {'max':>6}  cierran")
    for etq, desc, dv, sha in principales:
        x = datos[etq]
        f10, f = x["f"][:10], x["f"]
        p(f"  {etq:8} {sha:8} {x['lc']:>6} {x['lut']:>5} | {min(f10):11.2f} {mediana(f10):7.2f} {max(f10):6.2f} |"
          f" {min(f):11.2f} {cuantil(f, 0.1):6.2f} {mediana(f):7.2f} {sum(f) / len(f):6.2f} {desv(f):5.2f} {max(f):6.2f}"
          f"  {x['cierran']} de {len(f)}")
    p()
    for etq, desc, dv, sha in principales:
        p(f"  {etq:8} huella {datos[etq]['hu']}  {desc}")
    p()

    p("3. Solapamiento de las distribuciones")
    p()
    pares = [(a[0], b[0]) for a, b in zip(principales, principales[1:])]
    if len(principales) > 2:
        pares.append((principales[0][0], principales[-1][0]))
    for a, b in pares:
        fa, fb = datos[a]["f"], datos[b]["f"]
        if datos[a]["hu"] == datos[b]["hu"]:
            p(f"  {a} contra {b}: misma netlist (huella {datos[a]['hu']}), mismas frecuencias semilla a semilla:"
              f" {'si' if fa == fb else 'NO'}")
            continue
        u, z, pv = mann_whitney(fa, fb)
        sobre = sum(1 for y in fb if y >= min(fa))
        bajo = sum(1 for x in fa if x <= max(fb))
        p(f"  {a} contra {b}: diferencia de medianas {mediana(fa) - mediana(fb):+.2f} MHz;"
          f" U = {u:.0f} de {len(fa) * len(fb)}, z = {z:.2f}, p = {pv:.1e} (Mann-Whitney, dos colas)")
        p(f"    semillas de {b} sobre la minima de {a}: {sobre} de {len(fb)};"
          f" semillas de {a} bajo la maxima de {b}: {bajo} de {len(fa)}")
    p()

    if ordenes:
        p(f"4. Mismas fuentes, distinto orden de lectura (rtl/ del commit actual, {semillas_orden} semillas)")
        p()
        p("  Cada orden lee los mismos archivos de rtl/ en otra secuencia (orden 0 es el de")
        p("  tools/medir_variante.sh). La logica es la misma; cambia la numeracion interna de Yosys")
        p("  y con ella la netlist que entrega la sintesis.")
        p()
        p(f"  {'orden':8} {'huella':12} {'celdas':>6} {'LUT4':>5} {'min':>7} {'p10':>6} {'mediana':>7} {'max':>6}")
        meds = []
        for etq, desc, dv, sha in ordenes:
            x = datos[etq]
            f = x["f"]
            meds.append(mediana(f))
            p(f"  {etq:8} {x['hu']:12} {x['lc']:>6} {x['lut']:>5} {min(f):7.2f} {cuantil(f, 0.1):6.2f} {mediana(f):7.2f} {max(f):6.2f}")
        p()
        mins = [min(datos[c[0]]["f"]) for c in ordenes]
        p(f"  Entre ordenes: medianas de {min(meds):.2f} a {max(meds):.2f} MHz, minimas de {min(mins):.2f} a {max(mins):.2f} MHz.")
        p()

    p("5. Ruta critica de la semilla mas lenta de cada corrida")
    p()
    for etq, desc, dv, sha in principales + ordenes:
        f = datos[etq]["f"]
        s = f.index(min(f)) + 1
        r = ruta_critica(os.path.join(dv, f"soc.s{s}.log"))
        if r is None:
            p(f"  {etq}: sin informe de ruta critica")
            continue
        p(f"  {etq} (semilla {s}, {min(f):.2f} MHz): {r['total']:.2f} ns = logica {r['logica']:.2f}"
          f" + ruteo {r['ruteo']:.2f} + registro {r['otros']:.2f}; {r['niveles']} pasos de logica (LUT y acarreo)")
        p(f"    desde {corto(r['origen'], 70)}")
        p(f"    hasta {corto(r['destino'], 70)}")
        p(f"    RTL: {' -> '.join(r['rtl'])}")
    p()

    p("   Promedio sobre todas las semillas (la ruta critica de cada una):")
    for etq, desc, dv, sha in principales:
        rs = [ruta_critica(os.path.join(dv, f"soc.s{s}.log")) for s in range(1, len(datos[etq]["f"]) + 1)]
        rs = [r for r in rs if r]
        n = len(rs)
        p(f"  {etq:8} pasos de logica {sum(r['niveles'] for r in rs) / n:5.2f}, logica {sum(r['logica'] for r in rs) / n:5.2f} ns,"
          f" ruteo {sum(r['ruteo'] for r in rs) / n:5.2f} ns, total {sum(r['total'] for r in rs) / n:5.2f} ns ({n} semillas)")
    p()

    ruta_eq = os.path.join(d, "equiv.txt")
    if os.path.exists(ruta_eq):
        p("6. Equivalencia formal del SoC segmentado antes y despues del salto")
        p()
        with open(ruta_eq) as f:
            for l in f:
                p("  " + l.rstrip())
        p()

    p("7. Frecuencia maxima por semilla (MHz)")
    for etq, desc, dv, sha in principales + ordenes:
        f = datos[etq]["f"]
        p(f"  {etq}:")
        for i in range(0, len(f), 10):
            p("    " + " ".join(f"{x:6.2f}" for x in f[i:i + 10]))


def main():
    a = sys.argv[1:]
    if a[0] == "huella":
        print(huella(a[1]))
    elif a[0] == "orden":
        k, archivos = int(a[1]), a[2:]
        if k > 0:
            random.Random(k).shuffle(archivos)
        print("\n".join(archivos))
    elif a[0] == "informe":
        informe(a[1], int(a[2]), int(a[3]))
    else:
        sys.exit("uso: caida_segmentado.py huella|orden|informe ...")


if __name__ == "__main__":
    main()
