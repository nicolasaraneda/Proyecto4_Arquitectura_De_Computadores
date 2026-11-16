#!/usr/bin/env python3
"""tabla_potencia.py: tablas de potencia, energía por decisión y Ops/W.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso, desde la raíz del repositorio:

    python3 factibilidad/g_asic/scripts/tabla_potencia.py TAG [TAG ...]

Lee los reportes de OpenSTA que dejó scripts/potencia.sh en
factibilidad/g_asic/mediciones/potencia/TAG/ y los ciclos por tick medidos del
repositorio (docs/mediciones/ticks_software.txt y ticks_segmentado.txt), y
escribe factibilidad/g_asic/mediciones/potencia/TAG/tabla.md.

Definiciones (clase 7, Métricas de Desempeño):
  - Ppeak = f x instrucciones por ciclo x operaciones por instrucción. A
    25 MHz: 12,5 MOPS el Espino base (2 ciclos por instrucción de ALU) y
    25 MOPS el segmentado (1 ciclo).
  - Desempeño logrado por el kernel = operaciones útiles x f / ciclos del
    kernel. El kernel es el tick completo de trade.s. Las operaciones útiles
    del tick se cuentan así (definición nuestra, pendiente de fijar en el
    frente C): 32 p (1), dev = 32 p - S (1), dos comparaciones (2) y
    S + (dev >> 5) (2). Son 6.
  - Ops/W = MOPS / potencia.
Energía por decisión:
  - ronda 3 (0,1 ms): potencia de la ventana ronda3 por 100 us. Medida.
  - rondas 2 y 1 (1 ms y 10 ms): la de la ronda 3 más la potencia de sondeo
    por el tiempo que sobra. Estimada por composición: se supone que el tiempo
    extra es sondeo con el bus SPI quieto.
  - marginal del cálculo: (potencia de la ventana calculo menos la de sondeo)
    por la duración de la ventana. Es lo que cuesta decidir por sobre esperar.
"""

import os
import re
import sys

G = "factibilidad/g_asic"
ESQUINAS = ["nom_tt_025C_5v00", "max_ss_125C_4v50", "min_ff_n40C_5v50"]
NOMBRE = {"nom_tt_025C_5v00": "típica (tt, 25 C, 5,0 V)", "max_ss_125C_4v50": "lenta (ss, 125 C, 4,5 V)",
          "min_ff_n40C_5v50": "rápida (ff, -40 C, 5,5 V)"}
MODOS = ["defecto", "cero", "sondeo", "ronda3", "calculo", "calculo_b"]
TITULO = {"defecto": "flujo, sin actividad anotada", "cero": "solo reloj", "sondeo": "sondeo",
          "ronda3": "ronda 3 (4 ticks)", "calculo": "cálculo, tick 20", "calculo_b": "cálculo, tick 23"}
OPS_UTILES = 6
F_HZ = 25e6
T_CICLO = 40e-9
VENTANA_CALCULO_S = 3200e-9


def leer(tag, modo, esquina):
    p = os.path.join(G, "mediciones", "potencia", tag, f"{modo}_{esquina}.txt")
    if not os.path.exists(p):
        return None
    out = {"anotados": None, "sin_anotar": None}
    for linea in open(p, encoding="utf-8", errors="replace"):
        c = linea.split()
        if len(c) >= 5 and c[0] in ("Sequential", "Combinational", "Clock", "Total"):
            try:
                out[c[0]] = float(c[4])
            except ValueError:
                pass
        m = re.match(r"\s*vcd\s+(\d+)", linea)
        if m and out["anotados"] is None:
            out["anotados"] = int(m.group(1))
        m = re.match(r"\s*unannotated\s+(\d+)", linea)
        if m and out["sin_anotar"] is None:
            out["sin_anotar"] = int(m.group(1))
        m = re.match(r"clock clk: periodo ([0-9.]+)", linea)
        if m:
            out["periodo"] = float(m.group(1))
    return out if "Total" in out else None


def ciclos_tick(variante):
    """Ciclos promedio y peor caso del tick completo y de la respuesta."""
    archivo = "docs/mediciones/ticks_segmentado.txt" if variante == "seg" else "docs/mediciones/ticks_software.txt"
    out = {}
    en_r3 = False
    for linea in open(archivo, encoding="utf-8"):
        if linea.startswith("== Ronda 3"):
            en_r3 = True
        if not en_r3:
            continue
        m = re.match(r"\s*(respuesta|tick completo), (promedio|peor caso)\s+IC\s+([0-9.]+)\s+ciclos\s+([0-9.]+)", linea)
        if m:
            out[(m.group(1), m.group(2))] = (float(m.group(3)), float(m.group(4)))
    return out, archivo


def mw(x):
    return "n/d" if x is None else f"{x * 1e3:.3f}"


def tabla(tag):
    variante = "seg" if tag.startswith("seg") else "base"
    d = {(m, e): leer(tag, m, e) for m in MODOS for e in ESQUINAS}
    if d[("defecto", ESQUINAS[0])] is None:
        return f"## {tag}\n\nSin reportes de potencia.\n"
    periodo = d[("defecto", ESQUINAS[0])].get("periodo")
    ct, archivo = ciclos_tick(variante)
    out = [f"## Potencia de la corrida {tag} ({'Espino segmentado' if variante == 'seg' else 'Espino base'})", ""]
    out.append(f"Reloj de {periodo} ns ({1e3 / periodo:.1f} MHz), el de la SDC de la corrida. Cálculo de OpenSTA con el netlist final, "
               "los parásitos extraídos y el liberty de cada esquina. La actividad sale de la simulación del netlist "
               "ejecutando trade.s con la maestra a 0,1 ms por tick, salvo en las dos primeras columnas. Valores en mW.")
    out.append("")
    out.append("| esquina | " + " | ".join(TITULO[m] for m in MODOS) + " |")
    out.append("|" + "---|" * (len(MODOS) + 1))
    for e in ESQUINAS:
        out.append(f"| {NOMBRE[e]} | " + " | ".join(mw(d[(m, e)]["Total"]) if d[(m, e)] else "n/d" for m in MODOS) + " |")
    out.append("")
    e = ESQUINAS[0]
    out.append("Desglose en la esquina típica, en mW:")
    out.append("")
    out.append("| grupo | " + " | ".join(TITULO[m] for m in MODOS) + " |")
    out.append("|" + "---|" * (len(MODOS) + 1))
    for grupo, nombre in (("Sequential", "secuencial"), ("Combinational", "combinacional"), ("Clock", "reloj"), ("Total", "total")):
        out.append(f"| {nombre} | " + " | ".join(mw(d[(m, e)].get(grupo)) if d[(m, e)] else "n/d" for m in MODOS) + " |")
    out.append("")
    an = d[("ronda3", e)]
    if an:
        out.append(f"Actividad anotada desde el VCD en la ventana ronda3: {an['anotados']} pines, {an['sin_anotar']} sin anotar.")
        out.append("")

    out.append("Energía por decisión y Ops/W:")
    out.append("")
    out.append("| esquina | potencia de sondeo (mW) | energía por decisión, ronda 3 (nJ) | ronda 2 (nJ) | ronda 1 (nJ) | "
               "marginal del cálculo (nJ) | decisiones por joule, ronda 3 | Ppeak (MOPS) | Ppeak por watt (MOPS/W) | "
               "kernel (MOPS) | kernel por watt (MOPS/W) |")
    out.append("|" + "---|" * 11)
    ppeak = 25.0 if variante == "seg" else 12.5
    ciclos_prom = ct[("tick completo", "promedio")][1]
    kernel = OPS_UTILES * F_HZ / ciclos_prom / 1e6
    for e in ESQUINAS:
        s, r3, c, cb = (d[(m, e)] for m in ("sondeo", "ronda3", "calculo", "calculo_b"))
        if not (s and r3 and c):
            out.append(f"| {NOMBRE[e]} | n/d |" + " |" * 9)
            continue
        e3 = r3["Total"] * 100e-6
        e2 = e3 + s["Total"] * 900e-6
        e1 = e3 + s["Total"] * 9900e-6
        pc = c["Total"] if not cb else (c["Total"] + cb["Total"]) / 2
        marg = (pc - s["Total"]) * VENTANA_CALCULO_S
        out.append(f"| {NOMBRE[e]} | {mw(s['Total'])} | {e3 * 1e9:.1f} | {e2 * 1e9:.1f} | {e1 * 1e9:.1f} | {marg * 1e9:.4f} | "
                   f"{1 / e3:.3e} | {ppeak:.1f} | {ppeak / pc:.0f} | {kernel:.2f} | {kernel / pc:.0f} |")
    out.append("")
    out.append(f"Ciclos del tick completo: {ciclos_prom:.0f} en promedio y {ct[('tick completo', 'peor caso')][1]:.0f} en el peor caso "
               f"({archivo}, ronda 3). Operaciones útiles por tick: {OPS_UTILES} (definición nuestra, ver el encabezado de este script). "
               "Ppeak por watt y kernel por watt usan la potencia de la ventana de cálculo (promedio de los ticks 20 y 23). "
               "La energía de la ronda 3 es medida con la ventana ronda3. Las de las rondas 2 y 1 son estimadas: la de la ronda 3 más "
               "la potencia de sondeo por 0,9 ms y 9,9 ms. El marginal del cálculo es la potencia de la ventana de cálculo menos la de "
               "sondeo, por los 3,2 us de la ventana.")
    out.append("")
    return "\n".join(out)


def main():
    for tag in sys.argv[1:]:
        texto = tabla(tag)
        destino = os.path.join(G, "mediciones", "potencia", tag, "tabla.md")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "w", encoding="utf-8") as f:
            f.write(texto)
        print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
