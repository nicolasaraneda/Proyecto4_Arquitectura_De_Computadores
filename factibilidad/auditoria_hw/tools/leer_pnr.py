#!/usr/bin/env python3
"""leer_pnr.py: lee los logs de nextpnr y de icetime de las configuraciones auditadas.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Recibe por la entrada estándar las líneas de configuración de
tools/recursos.sh (etiqueta | fuentes | definiciones | programa | qué es |
valores del README) y como argumento la cantidad de semillas. Lee
build/variantes/fact2_auditoria_hw_ETIQUETA/soc.sN.log y soc.sN.asc.icetime.txt
y escribe la comparación contra los valores que informa el README de
factibilidad/i_integrado.

Criterio de coincidencia: las celdas y las BRAM tienen que ser iguales, y la
frecuencia de cada una de las semillas 1 a 10 no se compara una por una (el
README informa mínima, mediana y máxima): se comparan esas tres cifras con
una tolerancia de 0,01 MHz.
"""
import re
import statistics
import sys
from pathlib import Path

RE_FMAX = re.compile(r"Max frequency for clock.*?: ([0-9.]+) MHz \((PASS|FAIL) at")
RE_LC = re.compile(r"ICESTORM_LC:\s*(\d+)/\s*(\d+)")
RE_RAM = re.compile(r"ICESTORM_RAM:\s*(\d+)/\s*(\d+)")
RE_WB = re.compile(r"SB_WARMBOOT:\s*(\d+)/\s*(\d+)")
RE_ICETIME = re.compile(r"Total path delay: ([0-9.]+) ns \(([0-9.]+) MHz\)")


def leer(etq, semillas):
    d = Path("build/variantes") / f"fact2_auditoria_hw_{etq}"
    filas = []
    for s in range(1, semillas + 1):
        log = (d / f"soc.s{s}.log")
        texto = log.read_text(errors="replace") if log.exists() else ""
        f = RE_FMAX.findall(texto)
        lc, ram, wb = RE_LC.search(texto), RE_RAM.search(texto), RE_WB.search(texto)
        it = d / f"soc.s{s}.asc.icetime.txt"
        m = RE_ICETIME.search(it.read_text(errors="replace")) if it.exists() else None
        filas.append({
            "semilla": s,
            "fmax": float(f[-1][0]) if f else 0.0,
            "pasa": bool(f) and f[-1][1] == "PASS",
            "lc": int(lc.group(1)) if lc else None,
            "ram": int(ram.group(1)) if ram else None,
            "wb": int(wb.group(1)) if wb else 0,
            "icetime": float(m.group(2)) if m else None,
        })
    return filas


def tres(v):
    return min(v), statistics.median(v), max(v)


def main():
    semillas = int(sys.argv[1])
    fallas = 0
    resumen = []
    for linea in sys.stdin.read().splitlines():
        if not linea.strip():
            continue
        etq, _rtl, defs, hex_, desc, readme = [x.strip() for x in linea.split("|")]
        r_lc, r_ram, r_min, r_med, r_max = readme.split()
        filas = leer(etq, semillas)
        diez = filas[:10]
        resto = filas[10:]
        lc = {f["lc"] for f in filas}
        ram = {f["ram"] for f in filas}
        a, b, c = tres([f["fmax"] for f in diez])
        print(f"-- {etq}: {desc}")
        print(f"   definiciones: {defs}   programa: {hex_}")
        print(f"   celdas {sorted(lc, key=str)} de 1280 (README {r_lc}), BRAM {sorted(ram, key=str)} de 16 (README {r_ram}), "
              f"SB_WARMBOOT ubicada en {sum(f['wb'] for f in filas)} de {semillas} semillas")
        print("   fmax por semilla, nextpnr (MHz): " + " ".join(f"{f['fmax']:.2f}" for f in filas))
        print("   fmax por semilla, icetime (MHz): " + " ".join("  -  " if f["icetime"] is None else f"{f['icetime']:.2f}" for f in filas))
        print(f"   semillas 1 a 10:  mínima {a:.2f}, mediana {b:.2f}, máxima {c:.2f}; cierran {sum(f['pasa'] for f in diez)} de 10   "
              f"(README: {r_min}, {r_med} y {r_max}, 10 de 10)")
        ok = (lc == {int(r_lc)} and ram == {int(r_ram)} and abs(a - float(r_min)) < 0.011
              and abs(b - float(r_med)) < 0.011 and abs(c - float(r_max)) < 0.011 and all(f["pasa"] for f in diez))
        if resto:
            a2, b2, c2 = tres([f["fmax"] for f in resto])
            print(f"   semillas 11 a {semillas}: mínima {a2:.2f}, mediana {b2:.2f}, máxima {c2:.2f}; cierran {sum(f['pasa'] for f in resto)} de {len(resto)}   (muestra nueva)")
        it = [f["icetime"] for f in filas if f["icetime"] is not None]
        if it:
            print(f"   icetime, {len(it)} semillas: mínima {min(it):.2f}, mediana {statistics.median(it):.2f}, máxima {max(it):.2f}; "
                  f"sobre 25 MHz {sum(x >= 25.0 for x in it)} de {len(it)}")
        todas = all(f["pasa"] for f in filas)
        print(f"{'PASS' if ok else 'FAIL'} {etq}: las cifras del README {'se reproducen' if ok else 'NO se reproducen'} con las semillas 1 a 10")
        print(f"{'PASS' if todas else 'FAIL'} {etq}: cierra a 25 MHz en {sum(f['pasa'] for f in filas)} de {semillas} semillas")
        print()
        fallas += (not ok) + (not todas)
        peor = min(filas, key=lambda f: f["fmax"])
        resumen.append((etq, sorted(lc, key=str)[0], sorted(ram, key=str)[0], a, b, c, sum(f["pasa"] for f in diez),
                        min(f["fmax"] for f in filas), sum(f["pasa"] for f in filas), min(it) if it else 0.0, peor["semilla"]))
    print("Resumen")
    print("  config     celdas  libres  BRAM   fmin   fmed   fmax  cierran  | 20 semillas: fmin  cierran  peor semilla | icetime mínima")
    for etq, lc, ram, a, b, c, n10, mn, n20, itm, ps in resumen:
        print(f"  {etq:<9} {lc:>6} {1280 - lc:>7} {ram:>5}  {a:5.2f}  {b:5.2f}  {c:5.2f}  {n10:>2} de 10 |             {mn:5.2f}  {n20:>2} de {semillas}  {ps:>6}       | {itm:5.2f}")
    print()
    print("RESULTADO: " + ("PASS" if fallas == 0 else f"FAIL ({fallas} problemas)"))


if __name__ == "__main__":
    main()
