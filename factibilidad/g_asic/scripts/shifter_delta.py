#!/usr/bin/env python3
"""shifter_delta.py: cuánto cambia el macro con el shifter completo de la ALU.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso, desde la raíz del repositorio:

    python3 factibilidad/g_asic/scripts/shifter_delta.py [--md salida.md]

Compara las corridas completas de 40 ns sin y con el shifter (base_t40 contra
base_shifter_t40 y seg_t40 contra seg_shifter_t40). Lee las mismas métricas
que scripts/recolectar.py y calcula la diferencia absoluta y la porcentual.
No corre el flujo: necesita que las cuatro corridas existan
(make flujo y make shifter-flujo).
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recolectar as rc  # noqa: E402

FILAS = [
    ("área del dado (um2)", "die", 0),
    ("área del núcleo (um2)", "core", 0),
    ("área de celdas estándar (um2)", "stdcell", 0),
    ("celdas", "celdas", 0),
    ("flip-flops", "ff", 0),
    ("largo de cable (um)", "cable", 0),
    ("holgura de setup, esquina lenta (ns)", f"setup_{rc.LENTA}", 3),
    ("holgura de setup, esquina típica (ns)", f"setup_{rc.TIPICA}", 3),
    ("holgura de hold, peor esquina (ns)", "hold_peor", 3),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md")
    a = ap.parse_args()
    out = ["## Costo del shifter completo en el flujo completo (40 ns)", ""]
    for var, nombre in (("base", "Espino base"), ("seg", "Espino segmentado")):
        sin = rc.recolectar(f"{var}_t40")
        con = rc.recolectar(f"{var}_shifter_t40")
        if sin.get("falta") or con.get("falta") or sin.get("incompleta") or con.get("incompleta"):
            out.append(f"{nombre}: falta alguna de las dos corridas ({var}_t40, {var}_shifter_t40).")
            out.append("")
            continue
        out.append(f"### {nombre}")
        out.append("")
        out.append(f"| | sin shifter ({var}_t40) | con shifter ({var}_shifter_t40) | diferencia | % |")
        out.append("|---|---|---|---|---|")
        for titulo, clave, dec in FILAS:
            x, y = sin[clave], con[clave]
            pct = f"{100.0 * (y - x) / x:+.1f}" if dec == 0 and x else ""
            out.append(f"| {titulo} | {x:.{dec}f} | {y:.{dec}f} | {y - x:+.{dec}f} | {pct} |")
        out.append(f"| cierra timing en las 9 esquinas | {rc.n(sin['cierra_timing'])} | {rc.n(con['cierra_timing'])} | | |")
        out.append(f"| además DRC de Magic, LVS y antenas en cero | {rc.n(sin['cierra_todo'])} | {rc.n(con['cierra_todo'])} | | |")
        out.append("")
    out.append("Una corrida por caso. La holgura de una corrida no predice el período mínimo: el resizer deja de "
               "reparar cuando cumple su margen, así que la diferencia de holgura entre las dos columnas no es el "
               "costo del shifter en frecuencia. Lo que sí se demuestra es que con el shifter completo el macro "
               "cierra a 40 ns (25 MHz). No se hizo barrido de período con el shifter.")
    texto = "\n".join(out) + "\n"
    print(texto)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
