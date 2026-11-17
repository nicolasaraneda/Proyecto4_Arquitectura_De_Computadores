#!/usr/bin/env python3
"""tabla_potencia_barrel.py: tabla de potencia y energía por decisión del macro ASIC del barrel.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso, desde la raíz: python3 asic/scripts/tabla_potencia_barrel.py TAG [TAG ...]
Lee los reportes de OpenSTA que deja asic/scripts/potencia_barrel.sh en
asic/mediciones/potencia/TAG/ y escribe asic/mediciones/potencia/TAG/tabla.md.

Mismo método que factibilidad/g_asic/scripts/tabla_potencia.py (la edición ASIC del
base), con las ventanas del fondo:
  - sondeo: 60 us del tick 20 después de decidir (los cuatro hilos sondean).
  - ronda 3: los ticks 20 a 23 completos, 0,1 ms cada uno.
  - cálculo: 450 ciclos desde el octavo flanco de SCLK del tick 20.
Energía por decisión:
  - ronda 3: potencia de la ventana ronda 3 por 100 us (calculada por el flujo).
  - rondas 2 y 1: la de la ronda 3 más la potencia de sondeo por 0,9 ms y 9,9 ms
    (estimadas por composición: el tiempo extra es sondeo).
  - marginal: (cálculo menos sondeo) por los 18 us de la ventana de cálculo.
Las operaciones útiles, los MOPS y los Ops/W los calcula tools/p7/tablas.py con la
definición de P7; aquí solo potencia y energía.
"""
import os
import re
import sys

A = "asic"
ESQUINAS = ["nom_tt_025C_5v00", "max_ss_125C_4v50", "min_ff_n40C_5v50"]
NOMBRE = {"nom_tt_025C_5v00": "típica (tt, 25 C, 5,0 V)", "max_ss_125C_4v50": "lenta (ss, 125 C, 4,5 V)",
          "min_ff_n40C_5v50": "rápida (ff, -40 C, 5,5 V)"}
MODOS = ["defecto", "sondeo", "ronda3", "calculo"]
TITULO = {"defecto": "flujo, sin actividad anotada", "sondeo": "sondeo", "ronda3": "ronda 3 (4 ticks)",
          "calculo": "cálculo (450 ciclos)"}
VENTANA_CALCULO_S = 450 * 40e-9


def leer(tag, modo, esquina):
    p = os.path.join(A, "mediciones", "potencia", tag, f"{modo}_{esquina}.txt")
    if not os.path.exists(p):
        return None
    out = {"sin_anotar": None, "anotados": None}
    for linea in open(p, encoding="utf-8", errors="replace"):
        c = linea.split()
        if len(c) >= 5 and c[0] in ("Sequential", "Combinational", "Clock", "Total"):
            try:
                out[c[0]] = float(c[4])
            except ValueError:
                pass
        m = re.match(r"Annotated (\d+) pin activities", linea)
        if m:
            out["anotados"] = int(m.group(1))
        m = re.match(r"\s*unannotated\s+(\d+)", linea)
        if m and out["sin_anotar"] is None:
            out["sin_anotar"] = int(m.group(1))
    return out if "Total" in out else None


def mw(x):
    return "n/d" if x is None else f"{x * 1e3:.3f}"


def tabla(tag):
    d = {(m, e): leer(tag, m, e) for m in MODOS for e in ESQUINAS}
    if d[("ronda3", ESQUINAS[0])] is None:
        return None
    o = [f"## Potencia de la corrida {tag} (Espino barrel, sw/fondo.s)", ""]
    o.append("Reloj de 40 ns (25 MHz). Cálculo de OpenSTA con el netlist final, los parásitos extraídos y el liberty de "
             "cada esquina. La actividad sale de la simulación del netlist final ejecutando sw/fondo.s con la maestra a "
             "0,1 ms por tick (asic/scripts/potencia_barrel.sh), salvo en la primera columna. Valores en mW.")
    o.append("")
    o.append("| esquina | " + " | ".join(TITULO[m] for m in MODOS) + " |")
    o.append("|" + "---|" * (len(MODOS) + 1))
    for e in ESQUINAS:
        o.append(f"| {NOMBRE[e]} | " + " | ".join(mw((d[(m, e)] or {}).get("Total")) for m in MODOS) + " |")
    o.append("")
    o.append("Desglose en la esquina típica, en mW:")
    o.append("")
    o.append("| grupo | " + " | ".join(TITULO[m] for m in MODOS) + " |")
    o.append("|" + "---|" * (len(MODOS) + 1))
    for g, nom in (("Sequential", "secuencial"), ("Combinational", "combinacional"), ("Clock", "reloj"), ("Total", "total")):
        o.append(f"| {nom} | " + " | ".join(mw((d[(m, ESQUINAS[0])] or {}).get(g)) for m in MODOS) + " |")
    o.append("")
    sin = [f"{m}_{e}: {d[(m, e)]['sin_anotar']}" for m in MODOS[1:] for e in ESQUINAS
           if d[(m, e)] and d[(m, e)]["sin_anotar"] not in (0, None)]
    o.append("Pines sin actividad anotada en las ventanas con VCD: " + (", ".join(sin) if sin else "0 en todas") + ".")
    o.append("")
    o.append("Energía por decisión:")
    o.append("")
    o.append("| esquina | potencia de sondeo (mW) | energía por decisión, ronda 3 (nJ) | ronda 2 (nJ) | ronda 1 (nJ) | marginal del cálculo (nJ) |")
    o.append("|---|---|---|---|---|---|")
    for e in ESQUINAS:
        ps, p3, pc = (d[(m, e)]["Total"] for m in ("sondeo", "ronda3", "calculo"))
        e3 = p3 * 100e-6 * 1e9
        e2 = e3 + ps * 0.9e-3 * 1e9
        e1 = e3 + ps * 9.9e-3 * 1e9
        marg = (pc - ps) * VENTANA_CALCULO_S * 1e9
        o.append(f"| {NOMBRE[e]} | {ps * 1e3:.3f} | {e3:.1f} | {e2:.1f} | {e1:.1f} | {marg:.4f} |")
    o.append("")
    o.append("La energía de la ronda 3 es la de la ventana ronda 3 por 100 us. Las de las rondas 2 y 1 son estimadas: "
             "la de la ronda 3 más la potencia de sondeo por 0,9 ms y 9,9 ms. El marginal del cálculo es la potencia "
             "de la ventana de cálculo menos la de sondeo, por los 18 us de la ventana. En el barrel los cuatro hilos "
             "ejecutan una instrucción por ciclo también mientras sondean, así que calcular cuesta casi lo mismo que "
             "esperar.")
    return "\n".join(o) + "\n"


def main():
    for tag in sys.argv[1:]:
        t = tabla(tag)
        if t is None:
            print(f"{tag}: sin reportes de potencia")
            continue
        p = os.path.join(A, "mediciones", "potencia", tag, "tabla.md")
        open(p, "w", encoding="utf-8").write(t)
        print(f"escrito {p}")


if __name__ == "__main__":
    main()
