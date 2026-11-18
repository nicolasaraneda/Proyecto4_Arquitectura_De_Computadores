#!/usr/bin/env python3
"""report.py: cifras y tablas del informe (make report).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El informe (informe/informe.tex) no escribe ningún número a mano: todos entran
desde informe/generado/, que este script rehace a partir de las referencias
del algoritmo y de las mediciones guardadas en docs/mediciones/. Lo que cambia
según el peldaño que compite (el algoritmo, el programa, las mediciones por
tick) se elige con el mismo criterio que el comando oficial del testbench:

  - si existe rtl/00_peldano.v (make peldano-fijar), el peldaño es el suyo;
  - si no, el de la variable PELDANO (r0, r1 o r2), y sin ella r0, que es lo
    que hoy da el comando oficial.

Así, al fijar el peldaño que compite, make report regenera el informe solo.

Salidas en informe/generado/:
  cifras.tex      macros con cada cifra que cita el texto (\\cifra...)
  peldano.tex     \\peldano, y el condicional \\ifpeldanofondo
  t31*.tex        tablas del punto 3.1
  t32*.tex        tablas del punto 3.2
  t33*.tex        tablas del punto 3.3 (desde docs/mediciones/p7/)
  roofline.csv y techos.csv  datos de la figura del roofline

Uso: python3 tools/report.py [--peldano r0|r1|r2]
"""
import argparse
import csv
import os
import re
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Serie de práctica del curso desde el 17/11 (antes tb/practica.csv, que sigue siendo la que lee el
# testbench oficial; docs/obsoleto_serie_meta.md).
SERIE_PRACTICA = "data/practica_meta.csv"
sys.path.insert(0, os.path.join(RAIZ, "ref"))

import fondo     # noqa: E402
import market    # noqa: E402
import series    # noqa: E402
import trader    # noqa: E402

G = "informe/generado"
M = "docs/mediciones"


def num(x, dec=0):
    """Número con coma decimal y espacio fino de miles, para LaTeX."""
    if isinstance(x, str):
        return x
    s = f"{x:,.{dec}f}".replace(",", "X").replace(".", "{,}").replace("X", "\\,")
    return s


def leer(ruta):
    with open(os.path.join(RAIZ, ruta), encoding="utf-8") as f:
        return f.read()


def buscar(patron, texto, grupo=1, tipo=float):
    m = re.search(patron, texto, re.M)
    if not m:
        raise SystemExit(f"FAIL report: no se encontro /{patron}/")
    return tipo(m.group(grupo))


class Cifras:
    def __init__(self):
        self.d = {}

    def __setitem__(self, k, v):
        if not re.fullmatch(r"[A-Za-z]+", k):
            raise ValueError(f"nombre de macro invalido: {k}")
        self.d[k] = v

    def escribir(self, ruta):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("% Generado por tools/report.py (make report). No editar a mano.\n")
            for k, v in sorted(self.d.items()):
                f.write(f"\\newcommand{{\\cifra{k}}}{{{v}}}\n")


def tabla(ruta, cabecera, filas, alineacion, nota=None):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("% Generado por tools/report.py (make report). No editar a mano.\n")
        f.write(f"\\begin{{tabular}}{{{alineacion}}}\n\\toprule\n")
        f.write(" & ".join(cabecera) + " \\\\\n\\midrule\n")
        for fila in filas:
            if fila == "---":
                f.write("\\midrule\n")
            else:
                f.write(" & ".join(str(c) for c in fila) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
        if nota:
            f.write(f"\\par\\smallskip{{\\footnotesize {nota}}}\n")


def comprar_y_mantener(precios):
    """Comprar y mantener con la contabilidad de ref/market.py. Compra en el tick 0 todo lo
    que alcanza la caja, como la referencia del testbench (pueden ser más de 63 acciones, así
    que no se expresa con bytes de decisión), y después solo mantiene. El patrimonio final es
    el de market.comprar_y_mantener; la pérdida máxima tiene la misma definición que en las
    otras filas (Mercado.max_dd: mayor caída del patrimonio desde un máximo anterior, que
    parte en la caja inicial)."""
    m = market.Mercado()
    q = market.div_sv(m.caja - m.comision, precios[0])
    m.caja -= q * precios[0] + m.comision
    m.acciones = q
    m.ordenes = 1
    for p in precios:
        m.ejecutar(market.MANTENER, p)
    assert m.w == market.comprar_y_mantener(precios)
    return m


def estrategia(peldano):
    return (lambda: trader.Oficial()) if peldano == "r0" else (lambda: fondo.Fondo())


# --- Punto 3.1 -----------------------------------------------------------------------
def punto_31(c, peldano):
    practica = market.leer_serie(os.path.join(RAIZ, SERIE_PRACTICA))
    nuevo = estrategia(peldano)
    nombre = "\\texttt{max\\_media}" if peldano == "r0" else "fondo en un chip"
    filas = []
    for etiqueta, n, per in (("20\\,000 ticks", 20000, None), ("2\\,000 ticks, testbench", 2000, 100000)):
        p = practica[:n]
        perd = trader.ticks_perdidos(per) if per else 0
        mc = comprar_y_mantener(p)
        cym = mc.w
        candidatos = [("No operar", None), ("Comprar y mantener", "cym"),
                      ("Regla base del grupo (hasta el 15/11)", lambda: trader.ReglaBase()),
                      (f"Nuestro algoritmo ({nombre})", nuevo)]
        for nom, est in candidatos:
            if est is None:
                fila = [nom, num(market.CAJA0), 0, 0, 0]
            elif est == "cym":
                fila = [nom, num(cym), mc.ordenes, num(mc.comisiones), num(mc.max_dd)]
                c[f"CymPerdidaMax{'Veinte' if n == 20000 else 'Dos'}"] = num(mc.max_dd)
            else:
                m = market.simular(p, trader.decisiones(p, est(), perd))
                fila = [nom, num(m.w), num(m.ordenes), num(m.comisiones), num(m.max_dd)]
                if nom.startswith("Nuestro"):
                    sufijo = "Veinte" if n == 20000 else "Dos"
                    c[f"Patrimonio{sufijo}"] = num(m.w)
                    c[f"Ordenes{sufijo}"] = num(m.ordenes)
                    c[f"Comisiones{sufijo}"] = num(m.comisiones)
                    c[f"PerdidaMax{sufijo}"] = num(m.max_dd)
                    c[f"Cym{sufijo}"] = num(cym)
            filas.append(fila)
        filas.append("---")
        c["PerdidosTb"] = trader.ticks_perdidos(100000)
    filas = filas[:-1]
    # inserta el subtítulo de cada serie
    filas.insert(0, ["\\multicolumn{5}{l}{\\textit{Serie de práctica completa, 20\\,000 ticks}}", "", "", "", ""][:1])
    filas.insert(6, ["\\multicolumn{5}{l}{\\textit{Primeros 2\\,000 ticks, como el testbench (pierde " +
                     f"{trader.ticks_perdidos(100000)} precios en el reset)}}}}"])
    tabla(os.path.join(RAIZ, G, "t31.tex"), ["Estrategia", "Patrimonio", "Órdenes", "Comisiones", "Pérdida máx."],
          filas, "lrrrr")

    # Bloques de 2 000 ticks y familias plausibles
    filas = []
    for nom, est in (("Comprar y mantener", "cym"), ("Regla base del grupo", lambda: trader.ReglaBase()),
                     (f"Nuestro algoritmo", nuevo)):
        ws = []
        for b in series.bloques(practica, 2000):
            ws.append(market.comprar_y_mantener(b) if est == "cym" else market.simular(b, trader.decisiones(b, est())).w)
        cyms = [market.comprar_y_mantener(b) for b in series.bloques(practica, 2000)]
        gana = sum(w > y for w, y in zip(ws, cyms))
        filas.append([nom, num(sum(ws) / len(ws)), num(min(ws)), num(max(ws)),
                      "n/a" if est == "cym" else f"{gana} de {len(ws)}"])
        if nom.startswith("Nuestro"):
            c["BloquesMedia"] = num(sum(ws) / len(ws))
            c["BloquesPeor"] = num(min(ws))
            c["BloquesGana"] = gana
    tabla(os.path.join(RAIZ, G, "t31bloques.tex"),
          ["Estrategia", "Media", "Peor bloque", "Mejor bloque", "Supera a comprar y mantener"], filas, "lrrrr")


# --- Punto 3.2 -----------------------------------------------------------------------
def punto_32(c, peldano):
    filas = []
    if peldano == "r0":
        t = leer(f"{M}/ticks_software.txt")
        for ronda, nombre in ((1, "10 ms"), (2, "1 ms"), (3, "0,1 ms")):
            bloque = t.split(f"== Ronda {ronda} ==")[1].split("== Ronda")[0]
            presu = buscar(r"presupuesto (\d+) ciclos", bloque, tipo=int)
            for caso in ("promedio", "peor caso"):
                ic, cic, cpi, us, pct = [float(x) for x in re.search(
                    rf"respuesta, {caso}\s+IC\s+([\d.]+)\s+ciclos\s+([\d.]+)\s+CPI\s+([\d.]+)\s+tiempo\s+([\d.]+) us\s+\(\s*([\d.]+) %",
                    bloque).groups()]
                filas.append([f"{ronda} ({nombre})" if caso == "promedio" else "", caso.capitalize(), num(ic, 1),
                              num(cic, 0), num(cpi, 3), num(us, 2), num(pct, 3), num(presu) if caso == "promedio" else ""])
        c["CPIPrograma"] = num(buscar(r"CPI medido:\s+([\d.]+)", t.split("== Ronda 3 ==")[1]), 3)
        r3 = t.split("== Ronda 3 ==")[1]
        c["RespPeor"] = num(buscar(r"respuesta, peor caso\s+IC\s+[\d.]+\s+ciclos\s+([\d.]+)", r3), 0)
        c["RespProm"] = num(buscar(r"respuesta, promedio\s+IC\s+[\d.]+\s+ciclos\s+([\d.]+)", r3), 1)
        c["UsoRondaTres"] = num(buscar(r"respuesta, peor caso.*\(\s*([\d.]+) % de T\)", r3), 2)
        # El mismo peor caso contra el presupuesto (período menos la transacción SPI), no contra el período
        c["UsoPresuRondaTres"] = num(100.0 * buscar(r"respuesta, peor caso\s+IC\s+[\d.]+\s+ciclos\s+([\d.]+)", r3)
                                     / buscar(r"presupuesto (\d+) ciclos", r3, tipo=int), 2)
        tabla(os.path.join(RAIZ, G, "t32.tex"),
              ["Ronda", "Caso", "IC", "Ciclos", "CPI", "Tiempo ($\\mu$s)", "\\% de $T$", "Presupuesto"],
              filas, "llrrrrrr", "Respuesta: desde que el esclavo SPI entrega el precio (\\texttt{byte\\_done}) "
              "hasta la escritura en \\texttt{DECISION}. Fuente: \\texttt{docs/mediciones/ticks\\_software.txt}.")
        with open(os.path.join(RAIZ, G, "t32hilos.tex"), "w") as f:
            f.write("% Sin hilos en R0\n")
    else:
        t = leer(f"{M}/fondo/{peldano}/ticks.txt")
        r3 = t.split("=== Ronda 3")[1].split("=== Ronda")[0]
        hilos = []
        for nombre, patron in (("0, supervisor", r"0, supervisor"), ("1, gestor \\texttt{max\\_media}", r"1, gestor max_media"),
                               ("2, gestor base", r"2, gestor base"), ("3, gestor activo", r"3, gestor activo"),
                               ("Los cuatro (agregado)", r"los cuatro \(agregado\)")):
            mi, pr, ma, cp, cm, cpi = re.search(patron + r"\s+(\d+)\s+([\d.]+)\s+(\d+)\s+([\d.]+)\s+(\d+)\s+([\d.]+)", r3).groups()
            hilos.append([nombre, mi, num(float(pr), 2), ma, num(float(cp), 2), cm, num(float(cpi), 3)])
        tabla(os.path.join(RAIZ, G, "t32hilos.tex"),
              ["Hilo", "IC mín.", "IC prom.", "IC máx.", "Ciclos prom.", "Ciclos máx.", "CPI"], hilos, "lrrrrrr",
              f"Ronda 3, 20\\,000 ticks de la práctica. Fuente: \\texttt{{docs/mediciones/fondo/{peldano}/ticks.txt}}.")
        for ronda, nombre, presu in ((1, "10 ms", 249762), (2, "1 ms", 24762), (3, "0,1 ms", 2262)):
            T = {1: 10e6, 2: 1e6, 3: 1e5}[ronda]
            if f"=== Ronda {ronda}" in t:
                rr = t.split(f"=== Ronda {ronda}")[1].split("=== Ronda")[0]
                fila = re.search(r"DECISION \(respuesta\), todos los ticks\s+(\d+)\s+([\d.]+)\s+(\d+)", rr)
                prom, peor = float(fila.group(2)), int(fila.group(3))
                fuente = ""
            else:
                # La ronda 1 no se midió por el RTL (10 ms por tick son 35 minutos de Verilator):
                # sale del gemelo, validado contra el RTL en make cosim-barrel
                prom, peor = gemelo_respuesta(T)
                rr = r3
                fuente = "$^*$"
            ic = re.search(r"los cuatro \(agregado\)\s+(\d+)\s+([\d.]+)\s+(\d+)", rr)
            sup = re.search(r"0, supervisor\s+(\d+)\s+([\d.]+)\s+(\d+)", rr)
            filas.append([f"{ronda} ({nombre}){fuente}", "Promedio", num(float(sup.group(2)), 2), num(float(ic.group(2)), 2),
                          num(prom, 1), "4 / 1", num(prom * 0.04, 2), num(prom * 40 / T * 100, 3), num(presu)])
            filas.append(["", "Peor caso", sup.group(3), ic.group(3), num(peor), "4 / 1", num(peor * 0.04, 2),
                          num(peor * 40 / T * 100, 3), ""])
            if ronda == 3:
                c["RespPeor"] = num(peor)
                c["RespProm"] = num(prom, 1)
                c["UsoRondaTres"] = num(peor * 40 / T * 100, 2)
                c["UsoPresuRondaTres"] = num(100.0 * peor / presu, 2)
        tabla(os.path.join(RAIZ, G, "t32.tex"),
              ["Ronda", "Caso", "IC supervisor", "IC 4 hilos", "Ciclos", "CPI hilo / agregado", "Tiempo ($\\mu$s)",
               "\\% de $T$", "Presupuesto"], filas, "llrrrrrrr",
              "Ciclos: desde \\texttt{byte\\_done} hasta la escritura en \\texttt{DECISION}. IC: instrucciones de "
              f"trabajo del tick. Fuente: \\texttt{{docs/mediciones/fondo/{peldano}/ticks.txt}}, por el RTL. "
              "$^*$La ronda 1 no se midió por el RTL: los ciclos salen del gemelo digital (2\\,000 ticks) y las "
              "instrucciones son las de la ronda 3, porque el trabajo por tick no depende del período (las rondas 2 y 3 "
              "coinciden en las dos primeras decimales).")
        c["CPIPrograma"] = "4 por hilo y 1 agregado"


def _esperado(arg):
    peldano, precios, perd = arg
    est = trader.Oficial() if peldano == "r0" else fondo.Fondo()
    return bytes(trader.decisiones(precios, est, perd))


def equivalencia(c, peldano):
    """Gemelo digital contra la referencia: la práctica a los tres períodos y un
    lote de series sintéticas a 0,1 ms. Bytes leídos por la maestra, tick a tick."""
    import multiprocessing
    subprocess.run(["make", "-s", "build/gemelo", "fondo-hex"], cwd=RAIZ, check=True, stdout=subprocess.DEVNULL)
    opts = [] if peldano == "r0" else ["--barrel", "--xd", "3", "--tabla", "sw/fondo_tabla.hex"]
    hexf = "sw/trade.hex" if peldano == "r0" else "build/fondo/fondo.hex"
    practica = market.leer_serie(os.path.join(RAIZ, SERIE_PRACTICA))
    lote = []
    for nombre in series.FAMILIAS:
        lote += series.lote(nombre, 50, n=2000, semilla=21)
    trabajos = [(practica, per) for per in (100000, 1000000, 10000000)] + [(p, 100000) for p in lote]
    ruta = os.path.join(RAIZ, "build", "report_lote.txt")
    malas, ticks = 0, 0
    for per in (100000, 1000000, 10000000):
        grupo = [t for t in trabajos if t[1] == per]
        with open(ruta, "w") as f:
            for precios, _ in grupo:
                f.write(" ".join(map(str, precios)) + "\n")
        out = subprocess.run(["build/gemelo", *opts, "--hex", hexf, "--lote", ruta, "--bytes", "--periodo-ns", str(per)],
                             cwd=RAIZ, capture_output=True, text=True, check=True).stdout.splitlines()
        perd = trader.ticks_perdidos(per)
        with multiprocessing.Pool(min(20, os.cpu_count())) as pool:
            esperados = pool.map(_esperado, [(peldano, precios, perd) for precios, _ in grupo], chunksize=4)
        for (precios, _), linea, esp in zip(grupo, out, esperados):
            leidos = bytes.fromhex(linea.split()[8])
            malas += leidos != esp
            ticks += len(precios)
    c["EqSeries"] = num(len(lote))
    c["EqTicks"] = num(ticks)
    c["EqDistintas"] = malas
    if malas:
        raise SystemExit(f"FAIL report: {malas} corridas del gemelo distintas a la referencia")


def gemelo_respuesta(periodo_ns, nticks=2000):
    """Ciclos de respuesta promedio y peor caso del fondo en el gemelo."""
    subprocess.run(["make", "-s", "build/gemelo", "fondo-hex"], cwd=RAIZ, check=True, stdout=subprocess.DEVNULL)
    ruta = os.path.join(RAIZ, "build", "report_ticks.csv")
    subprocess.run(["build/gemelo", "--barrel", "--xd", "3", "--tabla", "sw/fondo_tabla.hex", "--hex",
                    "build/fondo/fondo.hex", "--periodo-ns", str(int(periodo_ns)), "--nticks", str(nticks),
                    "--ticks", ruta, "--callado"], cwd=RAIZ, check=True)
    r = [int(f["ciclos_respuesta"]) for f in csv.DictReader(open(ruta)) if int(f["ciclos_respuesta"]) >= 0]
    return sum(r) / len(r), max(r)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--peldano", default=os.environ.get("PELDANO") or None)
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    pv = "rtl/00_peldano.v"
    if os.path.exists(pv):
        peldano = re.search(r"Peldaño: (r\d)", leer(pv)).group(1)
        origen = "rtl/00_peldano.v"
    else:
        peldano = a.peldano or "r0"
        origen = "PELDANO" if a.peldano else "por defecto (sin rtl/00_peldano.v)"
    if peldano not in ("r0", "r1", "r2"):
        raise SystemExit(f"peldano desconocido: {peldano}")
    os.makedirs(G, exist_ok=True)
    c = Cifras()
    c["Peldano"] = peldano.upper()
    with open(os.path.join(G, "peldano.tex"), "w") as f:
        f.write("% Generado por tools/report.py (make report). No editar a mano.\n")
        f.write(f"\\newif\\ifpeldanofondo\\peldanofondo{'true' if peldano != 'r0' else 'false'}\n")
        f.write(f"\\newif\\ifpeldanodos\\peldanodos{'true' if peldano == 'r2' else 'false'}\n")
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        f.write(f"\\newcommand{{\\commitinforme}}{{{commit}}}\n")
    punto_31(c, peldano)
    punto_32(c, peldano)
    equivalencia(c, peldano)
    # Hechos de la serie de práctica que justifican la reversión a la media
    practica = market.leer_serie(os.path.join(RAIZ, SERIE_PRACTICA))
    for k, nombre in ((10, "Diez"), (50, "Cincuenta"), (100, "Cien")):
        c[f"VR{nombre}"] = num(series.razon_de_varianza(practica, k), 2)
    d = [b - a for a, b in zip(practica, practica[1:])]
    m = sum(d) / len(d)
    ac = sum((x - m) * (y - m) for x, y in zip(d, d[1:])) / sum((x - m) ** 2 for x in d)
    c["AutocorrUno"] = num(ac, 2)
    c["PrecioMin"], c["PrecioMax"] = min(practica), max(practica)
    # Palabras de programa (sin el relleno de ceros) y series comparadas por el RTL
    fuente = "sw/trade.s" if peldano == "r0" else "sw/fondo.s"
    subprocess.run([sys.executable, "tools/pochoasm.py", fuente, "-o", "build/report_prog.hex"], cwd=RAIZ,
                   check=True, capture_output=True)
    pal = [l.strip() for l in open(os.path.join(RAIZ, "build/report_prog.hex")) if l.strip() and not l.startswith(("//", "@"))]
    while pal and int(pal[-1], 16) == 0:
        pal.pop()
    c["PalabrasPrograma"] = len(pal)
    if peldano != "r0":
        c["SeriesRTL"] = num(buscar(r"PASS: (\d+) de \d+ series identicas", leer(f"{M}/fondo/{peldano}/series.txt"), tipo=int))
    import report_33   # noqa: E402  (tools/report_33.py: tablas y figura del punto 3.3)
    report_33.punto_33(c, peldano, tabla, num, leer)
    c.escribir(os.path.join(G, "cifras.tex"))
    print(f"report: peldano {peldano.upper()} ({origen}); {len(c.d)} cifras y tablas en {G}/")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
