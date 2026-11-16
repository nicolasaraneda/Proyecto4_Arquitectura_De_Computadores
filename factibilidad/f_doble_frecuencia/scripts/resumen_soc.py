#!/usr/bin/env python3
"""resumen_soc.py: tabla del SoC con el reloj doblado, por variante, objetivo y semilla.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee las corridas que deja scripts/medir_soc.sh. Para cada variante y cada
frecuencia objetivo informa, sobre las semillas:
  - celdas y BRAM;
  - frecuencia máxima según nextpnr y cuántas semillas cierran al objetivo;
  - frecuencia máxima según icetime;
  - peor ruta de cada clase según scripts/sta_icestorm.py (esquina máxima);
  - ancho del pulso del duplicador;
  - cuántas semillas tienen holgura no negativa en todas las clases de ruta
    con el oscilador de 25 MHz, para ciclo de trabajo de 50 % y para el
    rango de 45 a 55 %, en cada esquina de la base de tiempos;
  - la frecuencia de oscilador más alta que toleraría cada semilla con ciclo
    de trabajo entre 45 y 55 % (esquina máxima).

Uso: resumen_soc.py CARPETA
"""
import glob
import json
import os
import re
import sys


def mmm(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return "     -      -      -"
    n = len(v)
    med = v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
    return "%6.2f %6.2f %6.2f" % (v[0], med, v[-1])


def leer_checksum(ruta):
    """Último checksum que imprime nextpnr: identifica el diseño ya ubicado y ruteado."""
    c = None
    for linea in open(ruta, errors="replace"):
        m = re.search(r"Checksum: (0x[0-9a-f]+)", linea)
        if m:
            c = m.group(1)
    return c


def leer_log(ruta):
    fmax, paso, lc, ram = None, False, None, None
    for linea in open(ruta, errors="replace"):
        m = re.search(r"Max frequency for clock\s+'[^']+': ([0-9.]+) MHz \((PASS|FAIL) at ([0-9.]+) MHz", linea)
        if m:
            fmax, paso = float(m.group(1)), m.group(2) == "PASS"
        m = re.search(r"ICESTORM_LC:\s+(\d+)/", linea)
        if m:
            lc = int(m.group(1))
        m = re.search(r"ICESTORM_RAM:\s+(\d+)/", linea)
        if m:
            ram = int(m.group(1))
    return fmax, paso, lc, ram


def leer_icetime(ruta):
    if not os.path.exists(ruta):
        return None
    for linea in open(ruta, errors="replace"):
        m = re.search(r"Total path delay: ([0-9.]+) ns \(([0-9.]+) MHz\)", linea)
        if m:
            return float(m.group(2))
    return None


def osc_max(sta, duty_min=0.45):
    """Frecuencia de oscilador más alta (MHz) con holgura >= 0 para duty en [45, 55] %, esquina máxima."""
    e = sta["reloj"][0]["esquinas"]["max"]
    lr, lf = e["sube"]["latencia_ps"] / 1000, e["baja"]["latencia_ps"] / 1000
    wr, wf = e["sube"]["ancho_ps"] / 1000, e["baja"]["ancho_ps"] / 1000
    a = lf - lr
    t = 0.0
    for clase, r in sta["rutas"].items():
        p = r["max"]
        if clase in ("pos>pos", "neg>neg"):
            t = max(t, (p + abs(a)) / duty_min)
        elif clase == "neg>pos":
            t = max(t, (p + wr - a) / duty_min, (p + wf + a) / duty_min)
        elif clase == "pos>neg":
            if p > min(wr, wf):
                return 0.0
    return 1000.0 / t if t else None


def main():
    carpeta = sys.argv[1]
    grupos = {}
    for log in sorted(glob.glob(os.path.join(carpeta, "*_f*_s*.log"))):
        m = re.match(r"(.+)_f([0-9.]+)_s(\d+)\.log", os.path.basename(log))
        if not m or log.endswith("yosys.log"):
            continue
        v, f, s = m.group(1), m.group(2), int(m.group(3))
        base = log[:-4]
        fmax, paso, lc, ram = leer_log(log)
        sta = json.load(open(base + ".sta.json")) if os.path.exists(base + ".sta.json") else None
        grupos.setdefault((v, f), []).append(
            {"s": s, "fmax": fmax, "paso": paso, "lc": lc, "ram": ram, "chk": leer_checksum(log),
             "icetime": leer_icetime(base + ".icetime.txt"), "sta": sta})

    orden = sorted(grupos, key=lambda k: (k[0].split("_")[0], k[0], float(k[1])))
    print("SoC con el reloj doblado. nextpnr --hx1k --package vq100. Oscilador de 25 MHz (40 ns).")
    print("x2: reloj interno doblado por lógica. x1: el mismo SoC sin duplicador, con el mismo objetivo (control).")
    print()
    print("1. Recursos y frecuencia máxima (MHz: mínima, mediana y máxima entre semillas)")
    print("%-8s %8s %3s | %6s %4s | %-20s %-9s | %-20s" %
          ("variante", "objetivo", "sem", "celdas", "BRAM", "nextpnr", "cierran", "icetime"))
    for k in orden:
        g = grupos[k]
        n = len(g)
        lcs = sorted({x["lc"] for x in g})
        print("%-8s %8s %3d | %6s %4s | %-20s %-9s | %-20s" %
              (k[0], k[1] + " MHz", n, "/".join(str(x) for x in lcs), g[0]["ram"],
               mmm([x["fmax"] for x in g]), "%d de %d" % (sum(x["paso"] for x in g), n),
               mmm([x["icetime"] for x in g])))

    print()
    print("2. Peor ruta por clase, esquina máxima de la base de tiempos (ns: mínima, mediana y máxima entre semillas)")
    print("   pos>pos: de flanco de subida a flanco de subida (un período). pos>neg y neg>pos: rutas de medio ciclo del segmentado.")
    print("%-8s %8s | %-20s | %-20s | %-20s" % ("variante", "objetivo", "pos>pos", "pos>neg", "neg>pos"))
    for k in orden:
        g = [x for x in grupos[k] if x["sta"]]
        fila = []
        for c in ("pos>pos", "pos>neg", "neg>pos"):
            fila.append(mmm([x["sta"]["rutas"][c]["max"] for x in g if c in x["sta"]["rutas"]]))
        print("%-8s %8s | %s | %s | %s" % (k[0], k[1] + " MHz", fila[0], fila[1], fila[2]))

    print()
    print("3. Pulso del duplicador con la cadena fija en X1/Y8 (ns: mínimo y máximo entre semillas)")
    print("%-8s %8s | %-27s | %-27s | %s" %
          ("variante", "objetivo", "esquina máxima: sube, baja", "esquina mínima: sube, baja", "bajada menos subida (latencia, máx.)"))
    for k in orden:
        g = [x for x in grupos[k] if x["sta"] and x["sta"]["reloj"] and
             all(x["sta"]["reloj"][0]["esquinas"][c]["duplicador"] for c in ("min", "tip", "max"))]
        if not g:
            continue

        def r(c, fl):
            v = [x["sta"]["reloj"][0]["esquinas"][c][fl]["ancho_ps"] / 1000 for x in g]
            return "%.2f a %.2f" % (min(v), max(v))
        a = [(x["sta"]["reloj"][0]["esquinas"]["max"]["baja"]["latencia_ps"] -
              x["sta"]["reloj"][0]["esquinas"]["max"]["sube"]["latencia_ps"]) / 1000 for x in g]
        print("%-8s %8s | %-27s | %-27s | %.2f a %.2f" %
              (k[0], k[1] + " MHz", r("max", "sube") + ", " + r("max", "baja"),
               r("min", "sube") + ", " + r("min", "baja"), min(a), max(a)))

    print()
    print("4. Margen real con el oscilador de 25 MHz: semillas con holgura no negativa en todas las clases de ruta")
    print("   Los períodos del reloj doblado alternan entre duty x 40 ns y (1 - duty) x 40 ns, corregidos por la")
    print("   diferencia de latencia entre flancos. La ruta de un período tiene que caber en el más corto.")
    print("%-8s %8s | %-26s | %-26s | %-22s | %s" %
          ("variante", "objetivo", "duty 50 %: máx, típ, mín", "duty 45 a 55 %: máx, típ, mín",
           "peor holgura (ns)", "oscilador máximo tolerable (MHz)"))
    for k in orden:
        g = [x for x in grupos[k] if x["sta"] and x["sta"].get("holguras")]
        if not g:
            continue
        n = len(g)

        def cuenta(duties, esq):
            c = 0
            for x in g:
                h = [y["holgura"] for y in x["sta"]["holguras"] if y["duty"] in duties and y["esquina"] == esq]
                c += min(h) >= 0
            return c
        d50 = ", ".join("%d" % cuenta((50.0,), e) for e in ("max", "tip", "min"))
        d45 = ", ".join("%d" % cuenta((45.0, 50.0, 55.0), e) for e in ("max", "tip", "min"))
        peor = [min(y["holgura"] for y in x["sta"]["holguras"] if y["esquina"] == "max") for x in g]
        peor50 = [min(y["holgura"] for y in x["sta"]["holguras"] if y["esquina"] == "max" and y["duty"] == 50.0) for x in g]
        om = [osc_max(x["sta"]) for x in g]
        print("%-8s %8s | %-26s | %-26s | %-22s | %s" %
              (k[0], k[1] + " MHz", d50 + " de %d" % n, d45 + " de %d" % n,
               "%.2f (50 %%: %.2f)" % (min(peor), min(peor50)),
               "%.1f a %.1f" % (min(om), max(om))))

    # ¿Cambia algo en nextpnr al pedir más frecuencia?
    print()
    print("5. ¿Cambia el resultado de nextpnr con la frecuencia objetivo?")
    print("   Semillas en que el diseño ruteado es el mismo (igual checksum final) con todos los objetivos:")
    for v in sorted({k[0] for k in grupos}):
        frecs = sorted((k[1] for k in grupos if k[0] == v), key=float)
        por_sem = {}
        for f in frecs:
            for x in grupos[(v, f)]:
                por_sem.setdefault(x["s"], set()).add(x["chk"])
        iguales = sum(1 for c in por_sem.values() if len(c) == 1 and None not in c)
        print("   %-8s objetivos %s MHz: %d de %d" % (v, " y ".join(frecs), iguales, len(por_sem)))
    print("   El objetivo solo mueve el umbral de PASS o FAIL: nextpnr no ubica ni rutea distinto por pedirle más.")

    # Detalle por semilla de la mejor combinación de cada variante x2
    print()
    print("6. Detalle por semilla, esquina máxima (ns). Holgura con duty 50 % y con el peor entre 45 y 55 %")
    print("%-8s %8s %3s | %7s %7s | %7s %7s %7s | %7s %7s | %9s %9s" %
          ("variante", "objetivo", "sem", "nextpnr", "icetime", "pos>pos", "pos>neg", "neg>pos",
           "pulso s", "pulso b", "holg. 50", "holg. 45-55"))
    for k in orden:
        if not k[0].endswith("x2"):
            continue
        for x in sorted(grupos[k], key=lambda y: y["s"]):
            st = x["sta"]
            if not st or not st.get("holguras"):
                continue
            ru = st["rutas"]
            e = st["reloj"][0]["esquinas"]["max"]
            h50 = min(y["holgura"] for y in st["holguras"] if y["esquina"] == "max" and y["duty"] == 50.0)
            h45 = min(y["holgura"] for y in st["holguras"] if y["esquina"] == "max")

            def p(c):
                return "%7.2f" % ru[c]["max"] if c in ru else "      -"
            print("%-8s %8s %3d | %7.2f %7s | %s %s %s | %7.2f %7.2f | %9.2f %9.2f" %
                  (k[0], k[1] + " MHz", x["s"], x["fmax"] or 0,
                   "%.2f" % x["icetime"] if x["icetime"] else "-",
                   p("pos>pos"), p("pos>neg"), p("neg>pos"),
                   e["sube"]["ancho_ps"] / 1000, e["baja"]["ancho_ps"] / 1000, h50, h45))


if __name__ == "__main__":
    main()
