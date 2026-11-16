#!/usr/bin/env python3
"""resumen_cadena.py: tabla del retardo de la cadena del duplicador.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee las corridas que deja scripts/medir_cadena.sh y arma una fila por largo,
modo y ubicación, con el mínimo y el máximo entre semillas de:
  - el ancho del pulso según nextpnr (SDF): ruta por la cadena menos ruta
    directa, hasta la salida del XOR. nextpnr usa un valor por arco: el
    máximo de la base de tiempos, con el pin lógico de la LUT;
  - el ancho del pulso según la base de tiempos de icestorm sobre el diseño
    ruteado (pin físico), para el flanco de subida y el de bajada del reloj
    de entrada, en la esquina máxima, y el del flanco de subida en las
    esquinas típica y mínima.

Uso: resumen_cadena.py CARPETA
"""
import glob
import json
import os
import re
import sys


def retardo_sdf(ruta):
    """Ancho del pulso que ve nextpnr: (por la cadena) - (directo), en ns."""
    inter = {}     # (inst, pin) destino -> [(inst origen, pin, ps)]
    iopath = {}    # inst -> {(pin entrada, pin salida): ps}
    inst = None
    for linea in open(ruta):
        linea = linea.replace("\\", "")
        m = re.search(r"\(INTERCONNECT (\S+)/(\w+) (\S+)/(\w+) \((\d+):", linea)
        if m:
            a, pa, b, pb, d = m.groups()
            inter.setdefault((b, pb), []).append((a, pa, float(d)))
            continue
        m = re.search(r"\(INSTANCE (\S*)\)", linea)
        if m:
            inst = m.group(1)
            continue
        m = re.search(r"\(IOPATH (\w+) (\w+) \((\d+):", linea)
        if m and inst:
            iopath.setdefault(inst, {})[(m.group(1), m.group(2))] = float(m.group(3))

    memo = {}

    def llegada(celda, pin):
        """Llegada más tardía al pin de entrada de una celda, desde el pin del reloj."""
        k = (celda, pin)
        if k in memo:
            return memo[k]
        mejor = None
        for (a, pa, d) in inter.get(k, []):
            if "sb_io" in a:
                t = d
            elif "u_dup" in a:
                t0 = max((llegada(a, pe) + dd for (pe, ps), dd in iopath.get(a, {}).items()
                          if ps == pa and llegada(a, pe) is not None), default=None)
                t = None if t0 is None else t0 + d
            else:
                t = None
            if t is not None and (mejor is None or t > mejor):
                mejor = t
        memo[k] = mejor
        return mejor

    xor = [i for i in iopath if i.endswith("u_dup.u_xor_LC")]
    if not xor:
        return None
    xor = xor[0]
    t0 = llegada(xor, "I0")
    t1 = llegada(xor, "I1")
    if t0 is None or t1 is None:
        return None
    return ((t1 + iopath[xor][("I1", "O")]) - (t0 + iopath[xor][("I0", "O")])) / 1000.0


def main():
    carpeta = sys.argv[1]
    filas = {}
    for sta in sorted(glob.glob(os.path.join(carpeta, "m*_n*_s*.sta.json"))):
        m = re.match(r"m(\d+)_n(\d+)_(.+)_s(\d+)\.sta\.json", os.path.basename(sta))
        modo, n, ubic, sem = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
        j = json.load(open(sta))
        if not j["reloj"]:
            continue
        e = j["reloj"][0]["esquinas"]
        if not all(e[c]["duplicador"] for c in e):
            fila = filas.setdefault((modo, n, ubic), {"malas": 0})
            fila["malas"] = fila.get("malas", 0) + 1
            continue
        d_np = retardo_sdf(sta.replace(".sta.json", ".sdf"))
        fila = filas.setdefault((modo, n, ubic), {"malas": 0})
        fila.setdefault("np", []).append(d_np)
        fila.setdefault("max_s", []).append(e["max"]["sube"]["ancho_ps"] / 1000)
        fila.setdefault("max_b", []).append(e["max"]["baja"]["ancho_ps"] / 1000)
        fila.setdefault("tip_s", []).append(e["tip"]["sube"]["ancho_ps"] / 1000)
        fila.setdefault("min_s", []).append(e["min"]["sube"]["ancho_ps"] / 1000)
        fila.setdefault("min_b", []).append(e["min"]["baja"]["ancho_ps"] / 1000)
        fila.setdefault("asim", []).append((e["max"]["baja"]["latencia_ps"] - e["max"]["sube"]["latencia_ps"]) / 1000)

    for nr in glob.glob(os.path.join(carpeta, "m*_n*_s*.nortea")):
        m = re.match(r"m(\d+)_n(\d+)_(.+)_s(\d+)\.nortea", os.path.basename(nr))
        fila = filas.setdefault((int(m.group(1)), int(m.group(2)), m.group(3)), {"malas": 0})
        fila["nortea"] = fila.get("nortea", 0) + 1

    def rango(v):
        v = [x for x in v if x is not None]
        if not v:
            return "      -      "
        return "%5.2f a %5.2f" % (min(v), max(v))

    print("Ancho del pulso del reloj doblado (ns): mínimo y máximo entre semillas.")
    print("Modo 0: buffer por una entrada de la LUT. Modo 1: AND y OR de 4 entradas, alternados.")
    print("nextpnr: SDF de nextpnr. icestorm: base de tiempos de icestorm sobre el ruteo, con el pin físico.")
    print("sube y baja: pulso que nace del flanco de subida y del de bajada del reloj de entrada.")
    print()
    print("%-4s %-3s %-10s %3s | %-13s | %-13s %-13s | %-13s | %-13s %-13s | %s" %
          ("modo", "N", "ubicación", "sem", "nextpnr", "icestorm max", "", "icestorm típ.", "icestorm mín.", "", "celdas"))
    print("%-4s %-3s %-10s %3s | %-13s | %-13s %-13s | %-13s | %-13s %-13s |" %
          ("", "", "", "", "", "sube", "baja", "sube", "sube", "baja"))
    for (modo, n, ubic) in sorted(filas, key=lambda k: (k[0], k[2] != "libre", k[2], k[1])):
        f = filas[(modo, n, ubic)]
        if "np" not in f:
            print("%-4d %-3d %-10s %3d | sin corridas útiles (%d no se comportan como duplicador, %d sin rutear)" %
                  (modo, n, ubic, 0, f["malas"], f.get("nortea", 0)))
            continue
        print("%-4d %-3d %-10s %3d | %s | %s %s | %s | %s %s | %d" %
              (modo, n, ubic, len(f["np"]), rango(f["np"]), rango(f["max_s"]), rango(f["max_b"]),
               rango(f["tip_s"]), rango(f["min_s"]), rango(f["min_b"]), n + 1))
        if f["malas"]:
            print("     (%d corridas más no se comportan como duplicador)" % f["malas"])
        if f.get("nortea"):
            print("     (%d corridas más: nextpnr no terminó de rutear en el tiempo límite)" % f["nortea"])

    # Retardo por etapa y variación entre semillas, por modo y ubicación
    print()
    print("Retardo por LUT (ns, esquina máxima, pulso de subida) y dispersión entre semillas del pulso completo:")
    print("%-4s %-10s | %-28s | %s" % ("modo", "ubicación", "ns por LUT (ajuste entre N)", "mayor diferencia entre semillas con el mismo N"))
    for modo in sorted({k[0] for k in filas}):
        for ubic in sorted({k[2] for k in filas}, key=lambda u: (u != "libre", u)):
            pts = [(n, sum(f["max_s"]) / len(f["max_s"])) for (mo, n, u), f in filas.items()
                   if mo == modo and u == ubic and "max_s" in f]
            if len(pts) < 2:
                continue
            pts.sort()
            (n0, d0), (n1, d1) = pts[0], pts[-1]
            pend = (d1 - d0) / (n1 - n0)
            disp = max((max(f["max_s"]) - min(f["max_s"]), n) for (mo, n, u), f in filas.items()
                       if mo == modo and u == ubic and "max_s" in f)
            dnp = max((max(f["np"]) - min(f["np"]), n) for (mo, n, u), f in filas.items()
                      if mo == modo and u == ubic and "np" in f)
            print("%-4d %-10s | %5.3f                        | icestorm %.2f ns (N = %d), nextpnr %.2f ns (N = %d)" %
                  (modo, ubic, pend, disp[0], disp[1], dnp[0], dnp[1]))

    # Largo utilizable: el pulso y el hueco entre pulsos deben superar el mínimo de la red global
    TW = 0.88          # tW_GBUF de la hoja de datos (DS1040, iCE40HX), ns
    CORTO = 0.45 * 40  # semiperíodo más corto con ciclo de trabajo de 45 %, ns
    print()
    print("Largo utilizable de la cadena (modo 0, todas las ubicaciones y semillas). El pulso más angosto es el del")
    print("flanco de bajada en la esquina mínima; el más ancho, el del flanco de subida en la esquina máxima. Tienen")
    print("que quedar sobre %.2f ns (pulso mínimo de la red global) y bajo %.2f ns (semiperíodo de %.0f ns con ciclo" %
          (TW, CORTO - 0.3 - TW, CORTO))
    print("de trabajo de 45 %, menos 0,3 ns de diferencia entre flancos, menos el mismo mínimo para el hueco).")
    print("%-3s | %-18s %-28s | %-16s | %s" %
          ("N", "pulso más angosto", "si el chip es 2x más rápido", "pulso más ancho", "utilizable"))
    for n in sorted({k[1] for k in filas if k[0] == 0}):
        mn = [x for (mo, nn, u), f in filas.items() if mo == 0 and nn == n for x in f.get("min_b", [])]
        mx = [x for (mo, nn, u), f in filas.items() if mo == 0 and nn == n for x in f.get("max_s", [])]
        if not mn:
            continue
        a, b = min(mn), max(mx)
        if a < TW:
            v = "no: pulso bajo el mínimo"
        elif b > CORTO - 0.3 - TW:
            v = "no: no deja hueco con 45 %"
        elif a / 2 < TW:
            v = "sí, pero sin margen si el chip es más rápido que la base"
        else:
            v = "sí"
        print("%-3d | %-18s %-28s | %-16s | %s" % (n, "%.2f ns" % a, "%.2f ns" % (a / 2), "%.2f ns" % b, v))

    # Retardo de cada entrada de la LUT según la base de tiempos
    base = os.path.join(os.environ.get("OSS_CAD_SUITE", "/usr/local"), "share/icebox/timings_hx1k.txt")
    if os.path.exists(base):
        print()
        print("Retardo de una LUT según la entrada que use (base de tiempos de icestorm, de la entrada a lcout, en ns).")
        print("nextpnr elige la entrada física al rutear: de ahí sale la dispersión entre semillas con la cadena fija.")
        print("%-8s | %-22s | %-22s" % ("entrada", "subida: mín, típ, máx", "bajada: mín, típ, máx"))
        en_lc = False
        for linea in open(base):
            p = linea.split()
            if p[:1] == ["CELL"]:
                en_lc = p[1] == "LogicCell40"
            elif en_lc and p[:1] == ["IOPATH"] and p[1].startswith("in") and p[2] == "lcout":
                s_, b_ = [[float(x) / 1000 for x in t.split(":")] for t in (p[3], p[4])]
                print("%-8s | %-22s | %-22s" % (p[1], "%.3f, %.3f, %.3f" % tuple(s_), "%.3f, %.3f, %.3f" % tuple(b_)))
        # ¿Qué relación hay entre las tres esquinas en toda la base?
        cuenta = {}
        for linea in open(base):
            for t in re.findall(r"(-?[\d.]+):(-?[\d.]+):(-?[\d.]+)", linea):
                mn, tp, mx = (float(x) for x in t)
                if mx != 0:
                    k = (round(mn / mx, 3), round(tp / mx, 3))
                    cuenta[k] = cuenta.get(k, 0) + 1
        total = sum(cuenta.values())
        (rmn, rtp), veces = max(cuenta.items(), key=lambda kv: kv[1])
        print("Razón entre esquinas en toda la base: %d de %d valores no nulos cumplen mínima = %.3f x máxima y" %
              (veces, total, rmn))
        print("típica = %.3f x máxima. Los otros %d tienen las tres esquinas iguales. Es un factor de escala fijo." %
              (rtp, total - veces))

    asim = [x for f in filas.values() for x in f.get("asim", [])]
    if asim:
        print()
        print("Diferencia de latencia entre el flanco de bajada y el de subida de la entrada (esquina máxima):")
        print("  de %.3f a %.3f ns. Se suma con su signo al semiperíodo alto y se resta del bajo:" % (min(asim), max(asim)))
        print("  con el signo negativo, el período que nace del flanco de subida de la entrada queda más corto.")


if __name__ == "__main__":
    main()
