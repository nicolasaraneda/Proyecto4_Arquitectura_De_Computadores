#!/usr/bin/env python3
"""resumen_barrel.py: tabla de las corridas de LibreLane del macro ASIC del barrel.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso, desde la raíz: python3 asic/scripts/resumen_barrel.py [--p3 RUTA]
Lee asic/runs/barrel_xd*_t*/final/metrics.json, pasa cada corrida por el verificador
de cierre del Proyecto 3 (asic/verificar_cierre.py del clon en P3) y escribe
asic/mediciones/corridas.md y asic/mediciones/resumen.txt (clave = valor, lo lee
tools/p7/tablas.py). Las corridas en asic/runs/descartadas/ no cuentan.

"Cierra" es el criterio del Proyecto 3, igual que en la edición ASIC del base:
flujo completo, setup y hold con holgura no negativa y TNS 0 en las 9 esquinas,
DRC de Magic, LVS y antenas en cero. La frecuencia con cierre demostrado es la del
período más corto que cierra en el barrido de xd=3.
"""
import glob
import json
import os
import re
import subprocess
import sys

A = "asic"
P3 = os.environ.get("P3", os.path.expanduser("~/proyectos/Proyecto3_Arquitectura_De_Computadores"))


def cierra(run):
    md = os.path.join(A, "build", "post", "cierre_" + os.path.basename(run) + ".md")
    os.makedirs(os.path.dirname(md), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(P3, "asic", "verificar_cierre.py"), run, "--md", md],
                   capture_output=True, text=True)
    txt = open(md, encoding="utf-8").read() if os.path.exists(md) else ""
    return "Resultado: CIERRA" in txt


def main():
    filas = []
    for run in sorted(glob.glob(os.path.join(A, "runs", "barrel_xd*_t*"))):
        f = os.path.join(run, "final", "metrics.json")
        m = re.match(r"barrel_xd(\d)_t([\d.]+)$", os.path.basename(run))
        if not m or not os.path.exists(f):
            continue
        j = json.load(open(f))
        tag = os.path.basename(run)
        drc_k = os.path.join(A, "mediciones", tag, "drc_klayout.md")
        kl = "n/c"
        if os.path.exists(drc_k):
            mk = re.search(r"(\d+) marcadores", open(drc_k, encoding="utf-8").read())
            kl = mk.group(1) if mk else "?"
        filas.append(dict(
            tag=tag, xd=int(m.group(1)), T=float(m.group(2)),
            dado=round(j["design__die__area"]), std=round(j["design__instance__area__stdcell"]),
            celdas=j["design__instance__count__stdcell"], ff=j["design__instance__count__class:sequential_cell"],
            wns=j["timing__setup__ws"], wns_tt=j["timing__setup__ws__corner:nom_tt_025C_5v00"],
            hold=j["timing__hold__ws"], magic=j["magic__drc_error__count"], lvs=j["design__lvs_error__count"],
            ant=j["antenna__violating__nets"], slew=j.get("design__max_slew_violation__count"),
            cap=j.get("design__max_cap_violation__count"), klayout=kl, cierra=cierra(run)))
    L = ["# Corridas de LibreLane del macro ASIC del barrel", "",
         "Generado por `asic/scripts/resumen_barrel.py`. GF180MCU (`gf180mcuD`), LibreLane 3.0.16. Áreas en um2,"
         " holguras en ns. \"Cierra\" con el verificador del Proyecto 3 (setup y hold en 9 esquinas, DRC de Magic,"
         " LVS y antenas). Slew y capacitancia son informativos, como en el Proyecto 3.", "",
         "| corrida | xd | período (ns) | dado | celdas estándar | celdas | flip-flops | setup WNS lenta | setup WNS típica"
         " | hold WNS | DRC Magic | DRC KLayout | LVS | antenas | slew | cap | cierra |",
         "|" + "---|" * 17]
    for r in filas:
        L.append(f"| {r['tag']} | {r['xd']} | {r['T']:g} | {r['dado']} | {r['std']} | {r['celdas']} | {r['ff']} | "
                 f"{r['wns']:.3f} | {r['wns_tt']:.3f} | {r['hold']:.3f} | {r['magic']} | {r['klayout']} | {r['lvs']} | "
                 f"{r['ant']} | {r['slew']} | {r['cap']} | {'sí' if r['cierra'] else 'no'} |")
    xd3 = [r for r in filas if r["xd"] == 3]
    cierran = sorted(r["T"] for r in xd3 if r["cierra"])
    no = sorted(r["T"] for r in xd3 if not r["cierra"])
    L.append("")
    res = {}
    if cierran:
        tmin = cierran[0]
        res["t_min_cierra_ns"] = tmin
        res["fmax_cierre_mhz"] = round(1000.0 / tmin, 1)
        L.append(f"Con xd=3 (el hardware de R1) cierra hasta {tmin:g} ns ({1000.0 / tmin:.1f} MHz)"
                 + (f"; no cierra a {', '.join(f'{t:g}' for t in no)} ns." if no else "; ningún período probado falla."))
    for r in filas:
        if r["T"] == 40:
            k = f"xd{r['xd']}"
            res.update({f"{k}_dado_um2": r["dado"], f"{k}_std_um2": r["std"], f"{k}_celdas": r["celdas"],
                        f"{k}_ff": r["ff"], f"{k}_wns_lenta_ns": round(r["wns"], 3),
                        f"{k}_fmax_holgura_lenta_mhz": round(1000.0 / (40 - r["wns"]), 1)})
    open(os.path.join(A, "mediciones", "corridas.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    open(os.path.join(A, "mediciones", "resumen.txt"), "w", encoding="utf-8").write(
        "".join(f"{k} = {v}\n" for k, v in res.items()))
    print("\n".join(L))
    print("".join(f"{k} = {v}\n" for k, v in res.items()), end="")


if __name__ == "__main__":
    main()
