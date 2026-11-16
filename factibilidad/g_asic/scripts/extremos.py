#!/usr/bin/env python3
"""extremos.py: de dónde a dónde va la ruta crítica de cada corrida.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso, desde la raíz del repositorio:

    python3 factibilidad/g_asic/scripts/extremos.py TAG [TAG ...] [--md salida.md]

El reporte de timing nombra los flip-flops por su instancia (_8906_), que no
dice nada. Este script busca cada instancia en el netlist final de la corrida
y entrega el nombre del net de su salida Q, que sí conserva el nombre del
registro del RTL. Lee la ruta crítica de la esquina lenta que dejó
scripts/recolectar.py en mediciones/TAG/.
"""

import argparse
import os
import re
import sys

G = "factibilidad/g_asic"
ESQUINA = "max_ss_125C_4v50"


def salida_q(netlist, inst):
    m = re.search(r"gf180mcu_fd_sc_mcu7t5v0__dff\w+\s+" + re.escape(inst) + r"\s*\((.*?)\);", netlist, re.S)
    if not m:
        return "?"
    q = re.search(r"\.Q\(\s*\\?(\S+?)\s*\)", m.group(1))
    return q.group(1) if q else "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--md")
    a = ap.parse_args()
    out = ["## Extremos de la ruta crítica, esquina lenta (max_ss_125C_4v50)", "",
           "| corrida | sale del registro | llega al registro | celdas en la ruta | retardo de llegada (ns) | holgura (ns) |",
           "|---|---|---|---|---|---|"]
    for tag in a.tags:
        ruta = os.path.join(G, "mediciones", tag, f"{ESQUINA}_ruta_critica.txt")
        nl = os.path.join(G, "runs", tag, "final", "nl", "asic_top.nl.v")
        if not (os.path.exists(ruta) and os.path.exists(nl)):
            out.append(f"| {tag} | sin datos | | | | |")
            continue
        texto = open(ruta, encoding="utf-8", errors="replace").read()
        netlist = open(nl, encoding="utf-8", errors="replace").read()
        ini = re.search(r"Startpoint: (\S+)", texto).group(1)
        fin = re.search(r"Endpoint: (\S+)", texto).group(1)
        celdas = len(re.findall(r"^\s+[-0-9.]+\s+[-0-9.]+\s+[-0-9.]+\s+[-0-9.]+\s+[-0-9.]+ [v^] \S+/(?:Z|ZN|Q|X|Y) ", texto, re.M))
        llegada = re.search(r"([-0-9.]+)\s+data arrival time", texto).group(1)
        holgura = re.search(r"([-0-9.]+)\s+slack", texto).group(1)
        out.append(f"| {tag} | `{salida_q(netlist, ini)}` | `{salida_q(netlist, fin)}` | {celdas} | {float(llegada):.3f} | {float(holgura):.3f} |")
    out.append("")
    out.append("El nombre es el del net de la salida Q del flip-flop en el netlist final. La cuenta de celdas incluye el flip-flop de partida y los buffers.")
    texto = "\n".join(out) + "\n"
    print(texto)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
