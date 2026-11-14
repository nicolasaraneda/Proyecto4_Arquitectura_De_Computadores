#!/usr/bin/env python3
"""memoria.py: RAM de datos en flip-flops contra las macros SRAM del PDK.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso, desde la raíz del repositorio (lo llama scripts/memoria.sh):

    python3 factibilidad/g_asic/scripts/memoria.py base_dw4 base_dw64 ... [--md salida.md]

Para cada corrida de síntesis jerárquica base_dwN lee el área del módulo
pochoco_mem_asic y del módulo pochoco_rom (reports/stat.json) y calcula el
área de la RAM de datos como la diferencia. Es área de celdas recién
sintetizadas: no incluye buffers, árbol de reloj ni el espacio que agrega el
place and route (la utilización de las corridas completas es cercana a 55 %).

Las macros SRAM se leen del PDK instalado (libs.ref/gf180mcu_fd_ip_sram): el
tamaño sale de la línea SIZE de cada LEF. Son de 8 bits de ancho y un solo
puerto, así que una palabra de 32 bits necesita 4 macros.
"""

import argparse
import glob
import json
import os
import re
import sys

G = "factibilidad/g_asic"
PDK = os.path.expanduser(os.environ.get(
    "PDK_ROOT", "~/.ciel/ciel/gf180mcu/versions/54435919abffb937387ec956209f9cf5fd2dfbee"))
SRAM = os.path.join(PDK, "gf180mcuD", "libs.ref", "gf180mcu_fd_ip_sram")


def nombre(m):
    m = m.lstrip("\\")
    r = re.match(r"\$paramod\$[0-9a-f]+\\(\w+)", m) or re.match(r"\$paramod\\(\w+)\\", m)
    return r.group(1) if r else m


def sintesis(tag):
    run = os.path.join(G, "runs", tag)
    paso = sorted(glob.glob(os.path.join(run, "*-yosys-synthesis")))[-1]
    s = json.load(open(os.path.join(paso, "reports", "stat.json")))
    params = json.load(open(os.path.join(run, "resolved.json")))["SYNTH_PARAMETERS"]
    palabras = int([p for p in params if p.startswith("DataWords=")][0].split("=")[1])
    area = {nombre(m): v for m, v in s["modules"].items()}
    mem = area["pochoco_mem_asic"]
    rom = area["pochoco_rom"]
    ff = sum(v for c, v in mem.get("num_cells_by_type", {}).items() if "__dff" in c)
    return {"tag": tag, "palabras": palabras, "total": s["design"]["area"],
            "ram": mem["area"] - rom["area"], "ff": ff, "celdas": mem["num_cells"]}


def macros():
    out = []
    for lef in sorted(glob.glob(os.path.join(SRAM, "lef", "*.lef"))):
        m = re.search(r"sram(\d+)x(\d+)", os.path.basename(lef))
        texto = open(lef, encoding="utf-8", errors="replace").read()
        t = re.search(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)", texto)
        if m and t:
            out.append({"nombre": os.path.basename(lef)[:-4], "palabras": int(m.group(1)), "bits": int(m.group(2)),
                        "x": float(t.group(1)), "y": float(t.group(2))})
    return sorted(out, key=lambda d: d["palabras"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="*")
    ap.add_argument("--md")
    a = ap.parse_args()
    filas = sorted((sintesis(t) for t in a.tags), key=lambda f: f["palabras"])
    out = ["## Memoria de datos: flip-flops contra macros SRAM", "",
           "RAM de datos en flip-flops, medida con síntesis jerárquica del macro (Espino base, 40 ns). "
           "El área de la RAM es la del módulo `pochoco_mem_asic` menos la de `pochoco_rom`; incluye el "
           "registro de lectura y, en el Espino base, el registro de instrucción (32 flip-flops).", "",
           "| corrida | palabras de 32 bits | flip-flops del módulo | área de la RAM (um2) | um2 por palabra | área total del macro (um2) |",
           "|---|---|---|---|---|---|"]
    for f in filas:
        out.append(f"| {f['tag']} | {f['palabras']} | {f['ff']} | {f['ram']:.0f} | {f['ram'] / f['palabras']:.0f} | {f['total']:.0f} |")
    out += ["", f"Macros SRAM del PDK instalado (`{os.path.relpath(SRAM, os.path.expanduser('~'))}`, tamaño de la línea SIZE del LEF). "
            "Son de 8 bits y un solo puerto, con lectura sincrónica: una memoria de 32 bits usa 4.", "",
            "| macro | palabras | ancho (bits) | tamaño (um) | área de una (um2) | área de 4, para 32 bits (um2) | um2 por palabra de 32 bits |",
            "|---|---|---|---|---|---|---|"]
    ms = macros()
    for m in ms:
        a1 = m["x"] * m["y"]
        out.append(f"| {m['nombre']} | {m['palabras']} | {m['bits']} | {m['x']:.2f} x {m['y']:.2f} | {a1:.0f} | {4 * a1:.0f} | {4 * a1 / m['palabras']:.0f} |")
    if not ms:
        out.append("| no se encontraron macros en el PDK | | | | | | |")
    out.append("")
    if filas and ms:
        out += ["Comparación con el mismo número de palabras (flip-flops medidos contra 4 macros):", "",
                "| palabras | flip-flops (um2) | 4 macros SRAM (um2) | más chico |", "|---|---|---|---|"]
        por_pal = {m["palabras"]: 4 * m["x"] * m["y"] for m in ms}
        for f in filas:
            if f["palabras"] in por_pal:
                s = por_pal[f["palabras"]]
                out.append(f"| {f['palabras']} | {f['ram']:.0f} | {s:.0f} | {'flip-flops' if f['ram'] < s else 'macros SRAM'} |")
        out.append("")
    texto = "\n".join(out)
    print(texto)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as fh:
            fh.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
