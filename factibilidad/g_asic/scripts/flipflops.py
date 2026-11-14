#!/usr/bin/env python3
"""flipflops.py: qué registros del RTL quedan como flip-flops en el netlist.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso, desde la raíz del repositorio:

    python3 factibilidad/g_asic/scripts/flipflops.py TAG [TAG ...] [--md salida.md]

Cuenta los flip-flops del netlist de síntesis de cada corrida, agrupados por
el nombre del net de su salida Q (sin el índice del bit). Sirve para ver qué
eliminó la síntesis aplanada: con el programa en una ROM combinacional, el
sintetizador ve el contenido del programa y quita lo que trade.s no usa. En
el banco de registros informa además cuántos registros de 32 bits quedaron.
"""

import argparse
import collections
import glob
import os
import re
import sys

G = "factibilidad/g_asic"


def contar(tag):
    cands = glob.glob(os.path.join(G, "runs", tag, "*-yosys-synthesis", "asic_top.nl.v"))
    if not cands:
        return None
    texto = open(sorted(cands)[-1], encoding="utf-8", errors="replace").read()
    grupos = collections.Counter()
    regs = set()
    for m in re.finditer(r"gf180mcu_fd_sc_mcu7t5v0__dff\w+\s+\S+\s*\((.*?)\);", texto, re.S):
        q = re.search(r"\.Q\(\s*\\?(\S+?)\s*\)", m.group(1))
        nombre = q.group(1).strip() if q else "?"
        r = re.search(r"(?:^|\.)regs\[(\d+)\]", nombre)
        if r:
            regs.add(int(r.group(1)))
        nombre = re.sub(r"\[\d+\]$", "", nombre)
        nombre = re.sub(r"regs\[\d+\]", "regs[N]", nombre)
        nombre = re.sub(r"ram\[\d+\]", "ram[N]", nombre)
        # En un netlist con jerarquía el nombre es local al módulo: se deja
        # solo el último tramo para poder comparar las dos formas.
        nombre = nombre.split(".")[-1]
        grupos[nombre] += 1
    return grupos, sorted(regs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--md")
    a = ap.parse_args()
    datos = {t: contar(t) for t in a.tags}
    datos = {t: d for t, d in datos.items() if d}
    out = ["## Flip-flops del netlist de síntesis, por registro del RTL", ""]
    out.append("| corrida | flip-flops | del banco de registros | registros del banco que quedaron | registros eliminados |")
    out.append("|---|---|---|---|---|")
    for t, (g, regs) in datos.items():
        falta = [f"x{i}" for i in range(1, 16) if i not in regs]
        out.append(f"| {t} | {sum(g.values())} | {g.get('regs[N]', 0)} | {len(regs)} de 15 | {', '.join(falta) if falta else 'ninguno'} |")
    out.append("")
    nombres = sorted({n for g, _ in datos.values() for n in g}, key=lambda n: (-max(g.get(n, 0) for g, _ in datos.values()), n))
    out.append("| registro (net de la salida Q) | " + " | ".join(datos) + " |")
    out.append("|---|" + "---|" * len(datos))
    for n in nombres:
        out.append(f"| `{n}` | " + " | ".join(str(g.get(n, 0)) for g, _ in datos.values()) + " |")
    out.append("")
    out.append("Las corridas completas se sintetizan aplanadas. Con la jerarquía conservada (corridas *_jer) el banco de registros "
               "mantiene sus 15 registros en las dos variantes (mediciones/sintesis.md).")
    texto = "\n".join(out) + "\n"
    print(texto)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
