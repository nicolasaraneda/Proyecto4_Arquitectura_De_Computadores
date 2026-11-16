#!/usr/bin/env python3
"""recolectar.py: junta los resultados de corridas de LibreLane del macro ASIC.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso, desde la raíz del repositorio:

    python3 factibilidad/g_asic/scripts/recolectar.py TAG [TAG ...] [--md salida.md]

Para cada corrida factibilidad/g_asic/runs/TAG:
  1. Copia a factibilidad/g_asic/mediciones/TAG/ los reportes que respaldan
     los números: las métricas (metrics.txt, una línea por métrica), el reporte
     de síntesis, el resumen de timing, la potencia y la ruta crítica de las
     esquinas típica, lenta y rápida, las violaciones de slew, fanout y
     capacitancia de la esquina lenta, y los avisos del flujo. Van como .txt
     porque el repositorio ignora .json, .log y .rpt no es texto versionado.
  2. Imprime (y agrega a --md) una fila con área, celdas, timing por esquina,
     DRC, LVS, antenas y potencia.

Criterio de cierre, el mismo de nuestro Proyecto 3: una corrida cierra timing
si en la peor de las 9 esquinas la holgura de setup y la de hold son mayores o
iguales a cero. Cierra todo si además no tiene errores de DRC (Magic y
KLayout), de LVS ni violaciones de antena.

No interpreta nada: reúne y formatea. Una corrida sin final/metrics.json se
informa como incompleta, con el último paso que alcanzó.
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys

G = "factibilidad/g_asic"
TIPICA = "nom_tt_025C_5v00"
LENTA = "max_ss_125C_4v50"
RAPIDA = "min_ff_n40C_5v50"
ESQUINAS = [TIPICA, LENTA, RAPIDA]


def paso(run, nombre):
    """Carpeta del paso con ese nombre; si hay varias, la de número más alto."""
    cands = glob.glob(os.path.join(run, f"*-{nombre}")) + glob.glob(os.path.join(run, f"*-{nombre}-*"))
    cands = [c for c in cands if os.path.isdir(c)]
    if not cands:
        return None
    return max(cands, key=lambda c: int(os.path.basename(c).split("-", 1)[0]))


def ultimo_paso(run):
    pasos = sorted(d for d in os.listdir(run) if re.match(r"\d\d-", d))
    return pasos[-1] if pasos else "ninguno"


def primera_ruta(path):
    lineas = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for linea in f:
            lineas.append(linea)
            if "slack (" in linea:
                break
    return "".join(lineas)


def violaciones(path):
    """Sección de slew, fanout y capacitancia máximos de checks.rpt, con sus conteos."""
    lineas, dentro = [], False
    with open(path, encoding="utf-8", errors="replace") as f:
        for linea in f:
            if not dentro and re.match(r"max (slew|fanout|capacitance)\s*$", linea):
                dentro = True
            if dentro and not linea.startswith("====="):
                lineas.append(linea)
            if linea.startswith("max cap violation count"):
                break
    return "".join(lineas)


def potencia(path):
    """Fila Total de report_power: interna, conmutación, fuga y total, en W."""
    if not path or not os.path.exists(path):
        return None
    out = {}
    for linea in open(path, encoding="utf-8", errors="replace"):
        p = linea.split()
        if len(p) >= 5 and p[0] in ("Sequential", "Combinational", "Clock", "Macro", "Pad", "Total"):
            try:
                out[p[0]] = [float(x) for x in p[1:5]]
            except ValueError:
                pass
    return out or None


def periodo(run):
    r = json.load(open(os.path.join(run, "resolved.json")))
    return float(r["CLOCK_PERIOD"]), r.get("SYNTH_PARAMETERS"), r.get("FP_CORE_UTIL")


def recolectar(tag):
    run = os.path.join(G, "runs", tag)
    if not os.path.isdir(run):
        return {"tag": tag, "falta": True}
    mp = os.path.join(run, "final", "metrics.json")
    t, params, util = periodo(run)
    if not os.path.exists(mp):
        return {"tag": tag, "incompleta": True, "ultimo": ultimo_paso(run), "T": t, "params": params}
    m = json.load(open(mp))
    dest = os.path.join(G, "mediciones", tag)
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "metrics.txt"), "w", encoding="utf-8") as f:
        for k in sorted(m):
            f.write(f"{k} {m[k]}\n")
    sint = paso(run, "yosys-synthesis")
    if sint and os.path.exists(os.path.join(sint, "reports", "stat.rpt")):
        shutil.copy(os.path.join(sint, "reports", "stat.rpt"), os.path.join(dest, "sintesis_stat.txt"))
    for nombre in ("warning.log", "error.log"):
        if os.path.exists(os.path.join(run, nombre)):
            shutil.copy(os.path.join(run, nombre), os.path.join(dest, nombre.replace(".log", ".txt")))
    sta = paso(run, "openroad-stapostpnr")
    pot = {}
    if sta:
        if os.path.exists(os.path.join(sta, "summary.rpt")):
            shutil.copy(os.path.join(sta, "summary.rpt"), os.path.join(dest, "sta_resumen.txt"))
        for e in ESQUINAS:
            d = os.path.join(sta, e)
            if os.path.exists(os.path.join(d, "power.rpt")):
                shutil.copy(os.path.join(d, "power.rpt"), os.path.join(dest, f"{e}_potencia.txt"))
                pot[e] = potencia(os.path.join(d, "power.rpt"))
            if os.path.exists(os.path.join(d, "max.rpt")):
                with open(os.path.join(dest, f"{e}_ruta_critica.txt"), "w", encoding="utf-8") as f:
                    f.write(primera_ruta(os.path.join(d, "max.rpt")))
        d = os.path.join(sta, LENTA)
        if os.path.exists(os.path.join(d, "checks.rpt")):
            with open(os.path.join(dest, f"{LENTA}_violaciones.txt"), "w", encoding="utf-8") as f:
                f.write(violaciones(os.path.join(d, "checks.rpt")))
    g = m.get

    def esq(metrica, e):
        return g(f"{metrica}__corner:{e}")

    fila = {
        "tag": tag, "T": t, "params": params, "util_pedida": util,
        "die": g("design__die__area"), "core": g("design__core__area"),
        "stdcell": g("design__instance__area__stdcell"),
        "util": g("design__instance__utilization"),
        "celdas": g("design__instance__count__stdcell"),
        "ff": g("design__instance__count__class:sequential_cell"),
        "buf_timing": g("design__instance__count__class:timing_repair_buffer"),
        "buf_reloj": g("design__instance__count__class:clock_buffer"),
        "cable": g("route__wirelength"),
        "setup_peor": g("timing__setup__ws"), "hold_peor": g("timing__hold__ws"),
        "setup_tns": g("timing__setup__tns"), "hold_tns": g("timing__hold__tns"),
        "r2r_peor": g("timing__setup_r2r__ws"),
        "drc_magic": g("magic__drc_error__count"), "drc_klayout": g("klayout__drc_error__count"),
        "lvs": g("design__lvs_error__count"), "xor": g("design__xor_difference__count"),
        "antena": g("antenna__violating__nets"), "antena_ruteo": g("route__antenna_violation__count"),
        "slew": g("design__max_slew_violation__count"), "cap": g("design__max_cap_violation__count"),
        "pot": pot,
    }
    for e in ESQUINAS:
        fila[f"setup_{e}"] = esq("timing__setup__ws", e)
        fila[f"r2r_{e}"] = esq("timing__setup_r2r__ws", e)
        fila[f"hold_{e}"] = esq("timing__hold__ws", e)
    cierra_t = (fila["setup_peor"] is not None and fila["setup_peor"] >= 0 and fila["hold_peor"] >= 0
                and (fila["setup_tns"] or 0) == 0 and (fila["hold_tns"] or 0) == 0)
    limpio = all((fila[k] or 0) == 0 for k in ("drc_magic", "drc_klayout", "lvs", "antena", "antena_ruteo"))
    fila["cierra_timing"] = cierra_t
    fila["cierra_todo"] = cierra_t and limpio
    return fila


def n(x, d=3):
    if x is None:
        return "n/d"
    if isinstance(x, bool):
        return "sí" if x else "no"
    if isinstance(x, int):
        return str(x)
    return f"{x:.{d}f}"


def tabla(filas):
    out = []
    out.append("| corrida | variante | T (ns) | die (um2) | núcleo (um2) | celdas std (um2) | utilización | celdas | flip-flops | "
               "setup tt | setup ss | setup ff | setup r2r ss | hold peor | cierra timing | DRC Magic | DRC KLayout | LVS | antenas | cierra todo |")
    out.append("|" + "---|" * 20)
    for f in filas:
        if f.get("falta"):
            out.append(f"| {f['tag']} | no existe |" + " |" * 18)
            continue
        var = "seg" if f["params"] and "Pipeline=2" in f["params"] else "base"
        if f.get("incompleta"):
            out.append(f"| {f['tag']} | {var} | {n(f['T'], 1)} | incompleta: llegó a {f['ultimo']} |" + " |" * 16)
            continue
        out.append("| " + " | ".join([
            f["tag"], var, n(f["T"], 1), n(f["die"], 0), n(f["core"], 0), n(f["stdcell"], 0), n(f["util"]),
            n(f["celdas"]), n(f["ff"]),
            n(f[f"setup_{TIPICA}"]), n(f[f"setup_{LENTA}"]), n(f[f"setup_{RAPIDA}"]), n(f[f"r2r_{LENTA}"]),
            n(f["hold_peor"]), n(f["cierra_timing"]), n(f["drc_magic"]), n(f["drc_klayout"]), n(f["lvs"]),
            n((f["antena"] or 0) + (f["antena_ruteo"] or 0)), n(f["cierra_todo"])]) + " |")
    out.append("")
    out.append("| corrida | T (ns) | período mínimo estimado ss (ns) | fmax estimada ss (MHz) | fmax estimada tt (MHz) | "
               "potencia tt (mW) | potencia ss (mW) | potencia ff (mW) | buffers de timing | buffers de reloj | cable (um) | slew | cap |")
    out.append("|" + "---|" * 13)
    for f in filas:
        if f.get("falta") or f.get("incompleta"):
            continue
        tmin_ss = f["T"] - f[f"setup_{LENTA}"]
        tmin_tt = f["T"] - f[f"setup_{TIPICA}"]
        p = [f["pot"].get(e, {}) or {} for e in ESQUINAS]
        pt = [n(x["Total"][3] * 1e3) if "Total" in x else "n/d" for x in p]
        out.append("| " + " | ".join([
            f["tag"], n(f["T"], 1), n(tmin_ss), n(1e3 / tmin_ss, 1), n(1e3 / tmin_tt, 1), pt[0], pt[1], pt[2],
            n(f["buf_timing"]), n(f["buf_reloj"]), n(f["cable"], 0), n(f["slew"]), n(f["cap"])]) + " |")
    out.append("")
    out.append("Esquinas: tt = nom_tt_025C_5v00, ss = max_ss_125C_4v50, ff = min_ff_n40C_5v50. Las holguras están en ns y son la peor "
               "ruta de cada esquina, incluidas las de entrada y salida (IO_DELAY_CONSTRAINT = 20 % del período). \"hold peor\" es la peor de las 9 esquinas. "
               "\"setup r2r ss\" es la peor ruta entre registros en la esquina lenta. El período mínimo estimado es T menos la holgura de setup de esa corrida: "
               "es una estimación, no un cierre a ese período. La potencia es la que informa el flujo con la actividad por defecto de OpenSTA, al período de la corrida. "
               "La columna \"antenas\" suma dos métricas del flujo (antenna__violating__nets y route__antenna_violation__count): un 2 es un solo net en violación, contado por las dos.")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--md")
    ap.add_argument("--titulo", default="Corridas")
    a = ap.parse_args()
    filas = [recolectar(t) for t in a.tags]
    texto = f"## {a.titulo}\n\n" + tabla(filas) + "\n"
    print(texto)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
