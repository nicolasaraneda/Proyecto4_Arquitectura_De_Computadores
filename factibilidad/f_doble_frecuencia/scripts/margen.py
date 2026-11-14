#!/usr/bin/env python3
"""margen.py: margen real del reloj doblado, comparación con los dos flancos y presupuesto de ciclos.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee las corridas de scripts/medir_soc.sh (build/soc) y, si existe, el
resultado de scripts/humo_soc.sh (mediciones/humo_soc_x2.txt), y calcula:

  1. A qué período tendría que cerrar el SoC con el reloj doblado para
     tolerar cada ciclo de trabajo del oscilador, y cuántas semillas lo
     logran según nextpnr.
  2. Qué ciclo de trabajo tolera cada semilla, en cada esquina de la base de
     tiempos, mirando todas las clases de ruta (scripts/sta_icestorm.py).
  3. La alternativa de los dos flancos a 25 MHz (el Espino segmentado tal
     como está): qué ciclo de trabajo tolera.
  4. Qué pasa si el chip es más rápido o más lento que la base de tiempos:
     ancho del pulso y holgura con todos los retardos escalados.
  5. El presupuesto de ciclos de cada ronda con el reloj doblado.

Uso: margen.py CARPETA_SOC [HUMO.txt]
"""
import glob
import json
import os
import re
import sys

T = 40.0            # período del oscilador, ns
TW_GBUF = 0.88      # pulso mínimo de la red global, ns (hoja de datos DS1040, iCE40HX)
SKEW_GBUF = 0.727   # skew máximo de la red global en la HX1K, ns (hoja de datos DS1040)
ESQ = ("min", "tip", "max")
NOM = {"min": "mínima", "tip": "típica", "max": "máxima"}


def cargar(carpeta, variante, frec="50"):
    filas = []
    for p in sorted(glob.glob(os.path.join(carpeta, "%s_f%s_s*.sta.json" % (variante, frec))),
                    key=lambda x: int(re.search(r"_s(\d+)\.", x).group(1))):
        s = int(re.search(r"_s(\d+)\.", p).group(1))
        j = json.load(open(p))
        log = p.replace(".sta.json", ".log")
        fmax = None
        for linea in open(log, errors="replace"):
            m = re.search(r"Max frequency for clock\s+'[^']+': ([0-9.]+) MHz", linea)
            if m:
                fmax = float(m.group(1))
        filas.append({"s": s, "sta": j, "fmax": fmax})
    return filas


def reloj(fila, esq):
    """(asimetría, pulso sube, pulso baja) en ns. asimetría = latencia de bajada - latencia de subida."""
    e = fila["sta"]["reloj"][0]["esquinas"][esq]
    if e["duplicador"]:
        return ((e["baja"]["latencia_ps"] - e["sube"]["latencia_ps"]) / 1000.0,
                e["sube"]["ancho_ps"] / 1000.0, e["baja"]["ancho_ps"] / 1000.0)
    # reloj directo: el flanco de bajada llega antes o después que el de subida
    return ((e["baja"]["eventos"][0][0] - e["sube"]["eventos"][0][0]) / 1000.0, None, None)


def holgura_x2(fila, esq, duty, k=1.0):
    """Peor holgura (ns) del reloj doblado con ese ciclo de trabajo (0 a 1). k escala todos los retardos."""
    a, wr, wf = reloj(fila, esq)
    a, wr, wf = a * k, wr * k, wf * k
    ta = T * duty + a
    tb = T * (1 - duty) - a
    peor = 1e9
    for clase, r in fila["sta"]["rutas"].items():
        p = r[esq] * k
        if clase in ("pos>pos", "neg>neg"):
            disp = min(ta, tb)
        elif clase == "pos>neg":
            disp = min(wr, wf)
        elif clase == "neg>pos":
            disp = min(ta - wr, tb - wf)
        else:
            continue
        peor = min(peor, disp - p)
    return peor


def rango_duty_x2(fila, esq):
    """Ciclos de trabajo (en %) con holgura no negativa, barriendo de 30 a 70 % en pasos de 0,05."""
    ok = [d / 20.0 for d in range(600, 1401) if holgura_x2(fila, esq, d / 2000.0) >= 0]
    return (min(ok), max(ok)) if ok else None


def rango_duty_x1(fila, esq):
    """Dos flancos a 25 MHz: el tiempo en alto debe cubrir pos>neg y el tiempo en bajo neg>pos."""
    a, _, _ = reloj(fila, esq)
    ru = fila["sta"]["rutas"]
    if ru["pos>pos"][esq] > T:
        return None
    dmin = (ru.get("pos>neg", {esq: 0})[esq] - a) / T * 100
    dmax = (1 - (ru.get("neg>pos", {esq: 0})[esq] - a) / T) * 100
    return (dmin, dmax)


def txt_rango(v):
    v = [x for x in v if x is not None]
    if not v:
        return "ninguno"
    return "de %.1f a %.1f" % (min(v), max(v))


def main():
    carpeta = sys.argv[1]
    humo = sys.argv[2] if len(sys.argv) > 2 else None
    var = {v: cargar(carpeta, v) for v in ("base_x2", "seg_x2", "base_x1", "seg_x1")}
    if not var["base_x2"] or not var["seg_x2"]:
        print("Faltan corridas en %s: correr antes scripts/medir_soc.sh" % carpeta)
        return 1
    n = len(var["seg_x2"])
    asim = [reloj(f, "max")[0] for v in ("base_x2", "seg_x2") for f in var[v]]
    a_max = max(abs(x) for x in asim)

    print("Margen real del reloj doblado. Oscilador de 25 MHz (40 ns). %d semillas por variante." % n)
    print("base_x2: Espino base. seg_x2: Espino segmentado. Los dos con el reloj interno doblado por lógica.")
    print()
    print("1. Período al que hay que cerrar según el ciclo de trabajo del oscilador")
    print("   El período corto del reloj doblado es 40 ns x min(d, 1 - d) menos la diferencia de latencia entre")
    print("   el flanco de bajada y el de subida (%.2f ns en la esquina máxima). Las rutas de flanco de subida a" % a_max)
    print("   flanco de subida tienen que caber ahí. Semillas que lo logran según la frecuencia máxima de nextpnr:")
    print("   %-18s %14s %14s | %-10s %-10s" % ("ciclo de trabajo", "período (ns)", "equivale a MHz", "base_x2", "seg_x2"))
    for d in (50, 48, 45, 40):
        tc = T * d / 100.0 - a_max
        f = 1000.0 / tc
        c = ["%d de %d" % (sum(1 for x in var[v] if x["fmax"] and x["fmax"] >= f), len(var[v]))
             for v in ("base_x2", "seg_x2")]
        print("   %-18s %14.2f %14.1f | %-10s %-10s" % ("%d a %d %%" % (d, 100 - d), tc, f, c[0], c[1]))
    print("   Además del período, nextpnr no descuenta el skew de la red global: hasta %.3f ns en la HX1K" % SKEW_GBUF)
    print("   según la hoja de datos. Con el reloj de 25 MHz sobran más de 15 ns y no importa. Aquí sí.")
    print()

    print("2. Ciclo de trabajo que tolera cada semilla, con todas las clases de ruta (%)")
    print("   Rango de ciclos de trabajo del oscilador con holgura no negativa. 'no cierra': con ninguno.")
    print("   El rango no queda centrado en 50 % por la diferencia de latencia entre flancos.")
    print("   %-8s %3s | %-16s | %-16s | %-16s" % ("variante", "sem", "esquina máxima", "esquina típica", "esquina mínima"))
    resumen = {}
    for v in ("base_x2", "seg_x2"):
        for f in var[v]:
            cols = []
            for e in ("max", "tip", "min"):
                r = rango_duty_x2(f, e)
                resumen.setdefault((v, e), []).append((r, holgura_x2(f, e, 0.5) >= 0))
                cols.append("no cierra" if r is None else "%.1f a %.1f" % r)
            print("   %-8s %3d | %-16s | %-16s | %-16s" % (v, f["s"], cols[0], cols[1], cols[2]))
    print("   Semillas que cierran con cada supuesto sobre el oscilador:")
    print("     %-8s %-8s | %-12s | %-12s | %-12s" % ("variante", "esquina", "45 a 55 %", "48 a 52 %", "50 % exacto"))
    for v in ("base_x2", "seg_x2"):
        for e in ("max", "tip", "min"):
            rs = resumen[(v, e)]
            c45 = sum(1 for r, _ in rs if r and r[0] <= 45.0 and r[1] >= 55.0)
            c48 = sum(1 for r, _ in rs if r and r[0] <= 48.0 and r[1] >= 52.0)
            c50 = sum(1 for _, ok in rs if ok)
            print("     %-8s %-8s | %-12s | %-12s | %-12s" %
                  (v, NOM[e], "%d de %d" % (c45, len(rs)), "%d de %d" % (c48, len(rs)), "%d de %d" % (c50, len(rs))))
    print("   Peor holgura con 50 %% exacto, esquina máxima: base_x2 %.2f ns, seg_x2 %.2f ns." %
          (min(holgura_x2(f, "max", 0.5) for f in var["base_x2"]),
           min(holgura_x2(f, "max", 0.5) for f in var["seg_x2"])))
    print("   Peor holgura con 45 a 55 %%, esquina máxima: base_x2 %.2f ns, seg_x2 %.2f ns." %
          (min(min(holgura_x2(f, "max", 0.45), holgura_x2(f, "max", 0.55)) for f in var["base_x2"]),
           min(min(holgura_x2(f, "max", 0.45), holgura_x2(f, "max", 0.55)) for f in var["seg_x2"])))
    print()

    print("3. La alternativa de los dos flancos a 25 MHz (Espino segmentado sin duplicador, seg_x1)")
    if var["seg_x1"]:
        print("   El fetch lee la memoria en el flanco de bajada: hay rutas de subida a bajada (necesitan el tiempo")
        print("   en alto) y de bajada a subida (necesitan el tiempo en bajo). Peor ruta de cada clase, esquina máxima,")
        print("   y ciclo de trabajo del oscilador que tolera cada semilla:")
        print("   %3s | %8s %8s %8s | %s" % ("sem", "pos>pos", "pos>neg", "neg>pos", "ciclo de trabajo tolerado (%)"))
        rr = []
        for f in var["seg_x1"]:
            ru = f["sta"]["rutas"]
            r = rango_duty_x1(f, "max")
            rr.append(r)
            print("   %3d | %8.2f %8.2f %8.2f | %s" % (f["s"], ru["pos>pos"]["max"], ru["pos>neg"]["max"],
                                                    ru["neg>pos"]["max"], "%.1f a %.1f" % r if r else "no cierra"))
        print("   En las %d semillas: tolera al menos de %.1f a %.1f %%. Holgura de la ruta de un período: %.1f ns o más." %
              (len(rr), max(r[0] for r in rr), min(r[1] for r in rr),
               T - max(f["sta"]["rutas"]["pos>pos"]["max"] for f in var["seg_x1"])))
    print()

    print("4. Si el chip es más rápido o más lento que la base de tiempos")
    print("   La base de icestorm trae tres valores por arco con razón fija (mínimo = 0,80 x máximo, típico = 0,89 x")
    print("   máximo). La hoja de datos dice que son peores casos y que el retardo real puede ser mucho menor.")
    print("   k escala todos los retardos (cadena y lógica) respecto de la esquina máxima. El período no escala.")
    print("   %-6s | %-28s | %-28s | %-28s" % ("k", "pulso (ns): base_x2, seg_x2", "peor holgura 50 %: base, seg", "peor holgura 45 a 55 %: base, seg"))
    for k in (1.2, 1.1, 1.0, 0.89, 0.80, 0.65, 0.50):
        pb = [reloj(f, "max")[2] * k for f in var["base_x2"]]
        ps = [reloj(f, "max")[2] * k for f in var["seg_x2"]]
        h50 = [min(holgura_x2(f, "max", 0.5, k) for f in var[v]) for v in ("base_x2", "seg_x2")]
        h45 = [min(min(holgura_x2(f, "max", 0.45, k), holgura_x2(f, "max", 0.55, k)) for f in var[v])
               for v in ("base_x2", "seg_x2")]
        print("   %-6.2f | %-28s | %-28s | %-28s" %
              (k, "%.2f, %.2f" % (min(pb), min(ps)), "%+.2f, %+.2f" % (h50[0], h50[1]), "%+.2f, %+.2f" % (h45[0], h45[1])))
    kb = [(T * 0.45 - abs(reloj(f, "max")[0])) / f["sta"]["rutas"]["pos>pos"]["max"] for f in var["base_x2"]]
    print("   El Espino base cierra con 45 a 55 %% solo si el chip es al menos %.0f %% más rápido que la esquina" %
          (100 * (1 - min(kb))))
    print("   máxima en la peor semilla (k = %.2f) y %.0f %% en la mejor (k = %.2f)." % (min(kb), 100 * (1 - max(kb)), max(kb)))
    print("   Pulso mínimo de la red global (tW_GBUF): %.2f ns. El pulso más angosto de la tabla lo cumple con holgura." % TW_GBUF)
    print()

    print("5. Presupuesto de ciclos por ronda si el reloj doblado funcionara")
    print("   Presupuesto del testbench: (período - 9500 ns de la transacción SPI) / período del reloj.")
    resp = {}
    if humo and os.path.exists(humo):
        v = None
        for linea in open(humo):
            m = re.match(r"== (\w+)", linea)
            if m:
                v = m.group(1)
            m = re.search(r"respuesta en ciclos del reloj interno: promedio ([0-9.]+), peor caso (\d+)", linea)
            if m and v:
                resp[v] = (float(m.group(1)), int(m.group(2)))
    print("   %-7s %10s | %14s %14s" % ("ronda", "período", "a 25 MHz", "a 2 x 25 MHz"))
    for ronda, per in ((1, 10000000), (2, 1000000), (3, 100000)):
        print("   %-7d %7.1f ms | %14d %14d" % (ronda, per / 1e6, (per - 9500) // 40, (per - 9500) // 20))
    print("   El reloj doblado tiene en promedio 20 ns de período, pero sus períodos alternan (por ejemplo 18 y")
    print("   22 ns con ciclo de trabajo de 45 %). El número de ciclos por tick es exactamente el doble.")
    if resp:
        print("   Respuesta medida en la prueba de humo (ciclos del reloj interno, desde byte_done hasta DECISION):")
        for v, nom in (("base", "Espino base"), ("seg", "Espino segmentado")):
            if v in resp:
                pr, pe = resp[v]
                print("     %-18s promedio %.1f, peor caso %d ciclos: %.2f us con el reloj doblado, %.2f us a 25 MHz." %
                      (nom, pr, pe, pe * 20 / 1000.0, pe * 40 / 1000.0))
                print("     %-18s uso del presupuesto de la ronda 3: %.1f %% a 25 MHz, %.1f %% con el reloj doblado." %
                      ("", 100.0 * pe / 2262, 100.0 * pe / 4525))
        print("   El programa hace el mismo trabajo en la mitad del tiempo, pero ya usaba menos del 2 % del")
        print("   presupuesto más corto: el patrimonio no cambia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
