#!/usr/bin/env python3
"""comparar.py: el macro ASIC contra la FPGA y contra el ASIC del Proyecto 3.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso, desde la raíz del repositorio:

    python3 factibilidad/g_asic/scripts/comparar.py [--md salida.md]

De dónde sale cada número:
  - ASIC del Proyecto 4: corridas de factibilidad/g_asic/runs/ (las mismas
    métricas que usa scripts/recolectar.py) y potencia con actividad real de
    factibilidad/g_asic/mediciones/potencia/TAG/ (scripts/potencia.sh).
  - FPGA: docs/mediciones/espino_segmentado.txt (make medir-espino), que
    tiene las celdas, la frecuencia en 10 semillas y el CPI medido.
  - ASIC del Proyecto 3: final/metrics.json de su corrida final, si el clon
    está en la variable de entorno P3. Su frecuencia
    máxima (46,5 MHz) y sus MIPS (27,9) no se recalculan: son los documentados
    en asic/final.md de ese repositorio y aquí van marcados como documentados.

Frecuencia de cierre del ASIC: el período más corto del barrido en que la
corrida cierra setup y hold en las 9 esquinas. Se informa aparte si esa
corrida además queda limpia de DRC, LVS y antenas.

MIPS = frecuencia / CPI. El CPI es el medido en simulación con el RTL de la
FPGA (el core del macro son los mismos archivos): no se volvió a medir sobre
el macro.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recolectar as rc  # noqa: E402

G = "factibilidad/g_asic"
P3 = os.path.expanduser(os.environ.get("P3", "no-definido"))
TIPICA = "nom_tt_025C_5v00"
PERIODOS = ["40", "30", "25", "23p5", "22"]


def fpga():
    """Celdas, BRAM, Fmax y CPI de docs/mediciones/espino_segmentado.txt."""
    out = {}
    texto = open("docs/mediciones/espino_segmentado.txt", encoding="utf-8").read()
    for clave, patron in (("base", r"Espino base \(el del bitstream de competencia\)"),
                          ("seg", r"Segmentado, fetch en flanco de bajada \(BRAM\)"),
                          ("seg_rom", r"Segmentado, programa en ROM combinacional")):
        m = re.search(patron + r"\s+(\d+)\s+(\d+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+(\d+) de (\d+)", texto)
        out[clave] = {"celdas": int(m.group(1)), "bram": int(m.group(2)), "fmin": float(m.group(3)),
                      "fmed": float(m.group(4)), "fmax": float(m.group(5)), "cierran": f"{m.group(6)} de {m.group(7)}"}
    cpi = {}
    for prog, core, valor in re.findall(r"^\s+(trade|mix_clase7)\s+(base|segmentado)\s+\d+\s+\d+\s+([0-9.]+)", texto, re.M):
        cpi[(prog, "base" if core == "base" else "seg")] = float(valor)
    return out, cpi


def potencia(tag):
    """Total y desglose de la ventana ronda3 en la esquina típica, en W."""
    p = os.path.join(G, "mediciones", "potencia", tag, f"ronda3_{TIPICA}.txt")
    if not os.path.exists(p):
        return None
    out = {}
    for linea in open(p, encoding="utf-8", errors="replace"):
        c = linea.split()
        if len(c) >= 5 and c[0] in ("Sequential", "Combinational", "Clock", "Total"):
            try:
                out[c[0]] = float(c[4])
            except ValueError:
                pass
    return out if "Total" in out else None


def corridas(var):
    filas = []
    for t in PERIODOS:
        tag = f"{var}_t{t}"
        if os.path.exists(os.path.join(G, "runs", tag, "final", "metrics.json")):
            filas.append(rc.recolectar(tag))
    return filas


def p3():
    mp = os.path.join(P3, "asic", "rom", "runs", "final", "final", "metrics.json")
    if not os.path.exists(mp):
        return None
    m = json.load(open(mp))
    r = json.load(open(os.path.join(P3, "asic", "rom", "runs", "final", "resolved.json")))
    return {"T": float(r["CLOCK_PERIOD"]), "die": m["design__die__area"], "core": m["design__core__area"],
            "stdcell": m["design__instance__area__stdcell"], "celdas": m["design__instance__count__stdcell"],
            "ff": m["design__instance__count__class:sequential_cell"], "util": m["design__instance__utilization"]}


def f(x, d=1):
    return "n/d" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md")
    a = ap.parse_args()
    fp, cpi = fpga()
    out = ["## Comparación: macro ASIC del Proyecto 4, FPGA y ASIC del Proyecto 3", ""]

    # 1. Cierre por período
    cierre = {}
    out += ["### Cierre del macro ASIC por período", "",
            "| variante | T (ns) | frecuencia (MHz) | holgura de setup, esquina lenta (ns) | hold peor (ns) | cierra timing | DRC, LVS y antenas limpios |",
            "|---|---|---|---|---|---|---|"]
    for var in ("base", "seg"):
        filas = corridas(var)
        for fila in filas:
            limpio = all((fila[k] or 0) == 0 for k in ("drc_magic", "lvs", "antena", "antena_ruteo"))
            out.append(f"| {var} | {fila['T']:g} | {1e3 / fila['T']:.1f} | {fila['setup_peor']:.3f} | {fila['hold_peor']:.3f} | "
                       f"{'sí' if fila['cierra_timing'] else 'no'} | {'sí' if limpio else 'no'} |")
        ok_t = [x for x in filas if x["cierra_timing"]]
        ok_todo = [x for x in filas if x["cierra_todo"]]
        cierre[var] = {"timing": min(ok_t, key=lambda x: x["T"]) if ok_t else None,
                       "todo": min(ok_todo, key=lambda x: x["T"]) if ok_todo else None,
                       "t40": next((x for x in filas if x["T"] == 40.0), None)}
    out.append("")

    # 2. Tabla principal
    out += ["### Las dos variantes en las tres plataformas", "",
            "| | Espino base | Espino segmentado |", "|---|---|---|"]
    out.append(f"| FPGA iCE40 HX1K: celdas lógicas de 1280 | {fp['base']['celdas']} | {fp['seg']['celdas']} (fetch en BRAM), {fp['seg_rom']['celdas']} (ROM combinacional) |")
    out.append(f"| FPGA: BRAM de 16 | {fp['base']['bram']} | {fp['seg']['bram']} y {fp['seg_rom']['bram']} |")
    out.append(f"| FPGA: Fmax en 10 semillas, mínima y mediana (MHz) | {fp['base']['fmin']:.2f} y {fp['base']['fmed']:.2f} | "
               f"{fp['seg']['fmin']:.2f} y {fp['seg']['fmed']:.2f} (BRAM), {fp['seg_rom']['fmin']:.2f} y {fp['seg_rom']['fmed']:.2f} (ROM) |")
    b, s = cierre["base"], cierre["seg"]

    def celda(c, clave, d=0):
        return "n/d" if c["t40"] is None else f(c["t40"][clave], d)

    out.append(f"| ASIC GF180, corrida de 40 ns: área del dado (um2) | {celda(b, 'die')} | {celda(s, 'die')} |")
    out.append(f"| ASIC: área del núcleo (um2) | {celda(b, 'core')} | {celda(s, 'core')} |")
    out.append(f"| ASIC: área de celdas estándar (um2) | {celda(b, 'stdcell')} | {celda(s, 'stdcell')} |")
    out.append(f"| ASIC: utilización del núcleo | {celda(b, 'util', 3)} | {celda(s, 'util', 3)} |")
    out.append(f"| ASIC: celdas estándar y flip-flops | {celda(b, 'celdas')} y {celda(b, 'ff')} | {celda(s, 'celdas')} y {celda(s, 'ff')} |")

    def frec(c, clave):
        return "ninguna corrida" if c[clave] is None else f"{1e3 / c[clave]['T']:.1f} MHz ({c[clave]['T']:g} ns)"

    out.append(f"| ASIC: frecuencia más alta del barrido que cierra timing en las 9 esquinas | {frec(b, 'timing')} | {frec(s, 'timing')} |")
    out.append(f"| ASIC: lo mismo, además sin errores de DRC, LVS ni antenas | {frec(b, 'todo')} | {frec(s, 'todo')} |")
    for nombre, prog in (("mix de la clase 7", "mix_clase7"), ("trade.s con el sondeo", "trade")):
        fila = [f"| CPI medido, {nombre} |"]
        for var in ("base", "seg"):
            fila.append(f" {cpi[(prog, var)]:.3f} |")
        out.append("".join(fila))
    for nombre, prog in (("mix de la clase 7", "mix_clase7"), ("trade.s", "trade")):
        fila_f = [f"| MIPS en la FPGA a 25 MHz, {nombre} |"]
        fila_a = [f"| MIPS en el ASIC a la frecuencia de cierre de timing, {nombre} |"]
        for var, c in (("base", b), ("seg", s)):
            fila_f.append(f" {25 / cpi[(prog, var)]:.2f} |")
            fila_a.append(" n/d |" if c["timing"] is None else f" {1e3 / c['timing']['T'] / cpi[(prog, var)]:.2f} |")
        out += ["".join(fila_f), "".join(fila_a)]
    pb, ps = potencia("base_t40"), potencia("seg_t40")
    out.append(f"| ASIC: potencia a 25 MHz con la actividad de la ronda 3, esquina típica (mW) | "
               f"{'n/d' if pb is None else f(pb['Total'] * 1e3, 2)} | {'n/d' if ps is None else f(ps['Total'] * 1e3, 2)} |")
    out.append(f"| ASIC: energía por decisión en la ronda 3, potencia por 0,1 ms (uJ) | "
               f"{'n/d' if pb is None else f(pb['Total'] * 100e-6 * 1e6, 2)} | {'n/d' if ps is None else f(ps['Total'] * 100e-6 * 1e6, 2)} |")
    out.append("")

    # 3. Proyecto 3
    out += ["### Contra el ASIC del Proyecto 3", ""]
    q = p3()
    out += ["| | Proyecto 3, corrida final | Proyecto 4, Espino base | Proyecto 4, Espino segmentado |", "|---|---|---|---|"]
    if q:
        out.append(f"| Período de la corrida (ns) | {q['T']:g} | 40 | 40 |")
        out.append(f"| Área del dado (um2) | {q['die']:.0f} | {celda(b, 'die')} | {celda(s, 'die')} |")
        out.append(f"| Área del núcleo (um2) | {q['core']:.0f} | {celda(b, 'core')} | {celda(s, 'core')} |")
        out.append(f"| Área de celdas estándar (um2) | {q['stdcell']:.0f} | {celda(b, 'stdcell')} | {celda(s, 'stdcell')} |")
        out.append(f"| Celdas estándar y flip-flops | {q['celdas']} y {q['ff']} | {celda(b, 'celdas')} y {celda(b, 'ff')} | {celda(s, 'celdas')} y {celda(s, 'ff')} |")
    else:
        out.append(f"| Corrida final del Proyecto 3 | no está el clon en {P3} | | |")
    out.append(f"| Frecuencia máxima de cierre | 46,5 MHz (21,5 ns), documentado en asic/final.md del Proyecto 3 | {frec(b, 'timing')} | {frec(s, 'timing')} |")
    mb = "n/d" if b["timing"] is None else f"{1e3 / b['timing']['T'] / cpi[('trade', 'base')]:.1f}"
    ms = "n/d" if s["timing"] is None else f"{1e3 / s['timing']['T'] / cpi[('trade', 'seg')]:.1f}"
    out.append(f"| MIPS con el CPI de su propio programa | 27,9 (CPI del juego 1,665), documentado | {mb} (CPI de trade.s {cpi[('trade', 'base')]:.3f}) | {ms} (CPI de trade.s {cpi[('trade', 'seg')]:.3f}) |")
    out.append("")
    out.append("El Proyecto 3 lleva el pipeline con lectura anticipada, antirrebote de botones y contador de ciclos; el macro del Proyecto 4 "
               "no tiene esos dos periféricos. La frecuencia del Proyecto 3 salió de un barrido fino (pasos de 0,5 ns) con su modelo de cable "
               "derivado de su propia extracción; aquí el barrido tiene 5 puntos y el modelo de cable es el copiado del Proyecto 3.")
    out.append("")
    texto = "\n".join(out)
    print(texto)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as fh:
            fh.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
