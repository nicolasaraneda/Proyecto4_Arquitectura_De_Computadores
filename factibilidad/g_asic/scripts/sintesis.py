#!/usr/bin/env python3
"""sintesis.py: área por módulo de la síntesis jerárquica del macro ASIC.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso, desde la raíz del repositorio:

    python3 factibilidad/g_asic/scripts/sintesis.py TAG [TAG ...] [--md salida.md]

TAG es una corrida hecha con SYNTH_HIERARCHY_MODE=keep hasta Yosys.Synthesis
(make sintesis). Lee reports/stat.json del paso de síntesis y escribe, por
módulo, las celdas y los flip-flops propios (sin submódulos) y el área
acumulada con sus submódulos. El área es la de las celdas estándar recién sintetizadas, antes del place and
route: no incluye buffers de timing, árbol de reloj ni relleno. Copia el
reporte de Yosys a mediciones/TAG/sintesis_jerarquica.txt.
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys

G = "factibilidad/g_asic"


def nombre(m):
    m = m.lstrip("\\")
    r = re.match(r"\$paramod\$[0-9a-f]+\\(\w+)", m) or re.match(r"\$paramod\\(\w+)\\", m)
    return r.group(1) if r else m


def flip_flops(mod):
    """Flip-flops entre las celdas propias del módulo."""
    return sum(v for celda, v in mod.get("num_cells_by_type", {}).items()
               if celda.startswith("gf180mcu") and ("__dff" in celda or "__lat" in celda))


def tabla(tag):
    run = os.path.join(G, "runs", tag)
    paso = sorted(glob.glob(os.path.join(run, "*-yosys-synthesis")))[-1]
    s = json.load(open(os.path.join(paso, "reports", "stat.json")))
    dest = os.path.join(G, "mediciones", tag)
    os.makedirs(dest, exist_ok=True)
    shutil.copy(os.path.join(paso, "reports", "stat.rpt"), os.path.join(dest, "sintesis_jerarquica.txt"))
    params = json.load(open(os.path.join(run, "resolved.json")))["SYNTH_PARAMETERS"]
    total = s["design"]["area"]
    out = [f"### {tag} ({', '.join(params)})", "",
           "| módulo | celdas propias | flip-flops propios | área con submódulos (um2) | de eso, flip-flops (um2) | % del total |",
           "|---|---|---|---|---|---|"]
    filas = []
    for m, v in s["modules"].items():
        filas.append((v.get("area", 0.0), nombre(m), v.get("num_cells", 0), flip_flops(v), v.get("sequential_area", 0.0)))
    for acum, nom, celdas, ff, seq in sorted(filas, reverse=True):
        out.append(f"| {nom} | {celdas} | {ff} | {acum:.0f} | {seq:.0f} | {100 * acum / total:.1f} |")
    out.append("")
    n_ff = sum(f[3] for f in filas)
    out.append(f"Total: {s['design']['num_cells']} celdas, {n_ff} flip-flops, {total:.0f} um2, de los cuales "
               f"{s['design']['sequential_area']:.0f} um2 ({100 * s['design']['sequential_area'] / total:.1f} %) son flip-flops.")
    out.append("")
    return "\n".join(out)


def resumen(tags, modulo):
    """Una fila por corrida: área del módulo pedido y del macro completo."""
    out = [f"## Síntesis jerárquica: módulo {modulo} y total", "",
           f"| corrida | celdas de {modulo} | área de {modulo} (um2) | celdas del macro | flip-flops del macro | área del macro (um2) |",
           "|---|---|---|---|---|---|"]
    for tag in tags:
        paso = sorted(glob.glob(os.path.join(G, "runs", tag, "*-yosys-synthesis")))[-1]
        s = json.load(open(os.path.join(paso, "reports", "stat.json")))
        mods = {nombre(m): v for m, v in s["modules"].items()}
        n_ff = sum(flip_flops(v) for v in s["modules"].values())
        out.append(f"| {tag} | {mods[modulo].get('num_cells', 0)} | {mods[modulo].get('area', 0.0):.0f} | "
                   f"{s['design']['num_cells']} | {n_ff} | {s['design']['area']:.0f} |")
    out += ["", "Área de celdas estándar recién sintetizadas, con la jerarquía conservada (antes del place and route).", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--md")
    ap.add_argument("--resumen", metavar="MODULO", help="tabla compacta con el área de ese módulo en cada corrida")
    a = ap.parse_args()
    if a.resumen:
        texto = resumen(a.tags, a.resumen)
    else:
        texto = "## Síntesis jerárquica: área por módulo\n\n" + "\n".join(tabla(t) for t in a.tags)
    print(texto)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
