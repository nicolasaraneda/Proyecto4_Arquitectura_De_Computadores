#!/usr/bin/env python3
"""informe_recursos.py: arma mediciones/recursos.txt con lo que midió tools/medir.sh.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 informe_recursos.py CARPETA_LINEAS CARPETA_VARIANTES SEMILLAS CARPETA_MEDICIONES variantes.txt [otro.txt ...]

CARPETA_LINEAS tiene un archivo ETIQUETA.txt por variante con la línea de
resumen de tools/medir_variante.sh. CARPETA_VARIANTES es build/variantes de la
raíz, donde ese script deja los logs de nextpnr (fact2_i_ETIQUETA). Los
archivos de variantes dan el orden, los grupos, la referencia de la columna
"agrega" y la descripción de cada una.

Por cada variante informa celdas lógicas, la diferencia contra su referencia,
celdas libres de las 1280, BRAM, LUT4, la frecuencia máxima mínima, mediana y
máxima entre las semillas y cuántas cierran a 25 MHz. Después lista la
frecuencia de cada semilla y, para las variantes que no terminan, el error de
nextpnr. Las variantes que todavía no se midieron se marcan como tales.
"""
import os
import re
import subprocess
import sys

CELDAS, BRAMS = 1280, 16
RE_LINEA = re.compile(r"celdas\s+(\S+) de 1280, BRAM\s+(\S+) de 16, LUT4\s+(\S*), fmax min\s+(\S+) mediana\s+(\S+) max\s+(\S+) MHz, "
                      r"cierran a 25 MHz (\d+) de (\d+)")


def leer_variantes(rutas):
    """Lista de ('grupo', título) y ('var', etiqueta, fuentes, defs, params, ref, desc)."""
    items = []
    for ruta in rutas:
        for linea in open(ruta, encoding="utf-8"):
            linea = linea.rstrip("\n")
            if not linea.strip() or linea.lstrip().startswith("#"):
                continue
            if linea.startswith("="):
                items.append(("grupo", linea[1:].strip()))
                continue
            campos = [c.strip() for c in linea.split("|")]
            if len(campos) != 6:
                sys.exit(f"informe_recursos.py: línea mal formada en {ruta}: {linea}")
            items.append(("var", *campos))
    return items


def medicion(carpeta_lineas, carpeta_var, etq, semillas):
    """Diccionario con lo medido de una variante, o None si no se midió."""
    ruta = os.path.join(carpeta_lineas, etq + ".txt")
    if not os.path.exists(ruta):
        return None
    texto = open(ruta, encoding="utf-8").read()
    m = RE_LINEA.search(texto)
    d = os.path.join(carpeta_var, "fact2_i_" + etq)
    log1 = os.path.join(d, "soc.s1.log")
    r = {"celdas": None, "bram": None, "lut": None, "fmin": 0.0, "fmed": 0.0, "fmax": 0.0, "cierran": 0, "de": semillas,
         "por_semilla": [], "error": "", "warmboot": "", "yosys_bram": None}
    if m:
        ent = lambda s: int(s) if s.isdigit() else None   # noqa: E731
        r["celdas"], r["bram"], r["lut"] = ent(m.group(1)), ent(m.group(2)), ent(m.group(3))
        r["fmin"], r["fmed"], r["fmax"] = float(m.group(4)), float(m.group(5)), float(m.group(6))
        r["cierran"], r["de"] = int(m.group(7)), int(m.group(8))
    fm = os.path.join(d, "fmax.txt")
    if os.path.exists(fm):
        r["por_semilla"] = [x.strip() for x in open(fm) if x.strip()]
    if os.path.exists(log1):
        log = open(log1, encoding="utf-8", errors="replace").read()
        e = re.search(r"^ERROR: (.*)$", log, re.M)
        if e:
            r["error"] = e.group(1).strip()
        w = re.search(r"SB_WARMBOOT:\s*(\d+)/\s*(\d+)", log)
        if w and int(w.group(1)) > 0:
            r["warmboot"] = f"{w.group(1)} de {w.group(2)}"
    # Si nextpnr no llegó a informar la ocupación, se toma de la síntesis
    ylog = os.path.join(d, "yosys.log")
    if os.path.exists(ylog):
        y = open(ylog, encoding="utf-8", errors="replace").read()
        b = re.findall(r"^\s+(\d+)\s+SB_RAM40_4K\w*\s*$", y, re.M)
        if b:
            r["yosys_bram"] = int(b[-1]) if len(b) == 1 else None
            # con varias clases de BRAM (4K y 4KNR) se suman las del último bloque de estadísticas
            ult = y.rfind("Number of cells")
            if ult >= 0:
                r["yosys_bram"] = sum(int(n) for n in re.findall(r"^\s+(\d+)\s+SB_RAM40_4K\w*\s*$", y[ult:], re.M))
    return r


def ruta_critica(carpeta_var, etq, por_semilla):
    """Resumen de la ruta crítica (posedge a posedge) de la semilla más lenta."""
    try:
        f = [float(x) for x in por_semilla]
    except ValueError:
        return None
    if not f or min(f) <= 0:
        return None
    peor = f.index(min(f)) + 1
    log = os.path.join(carpeta_var, "fact2_i_" + etq, f"soc.s{peor}.log")
    if not os.path.exists(log):
        return None
    lineas = open(log, encoding="utf-8", errors="replace").read().splitlines()
    inicios = [i for i, l in enumerate(lineas) if "Critical path report for clock" in l and "posedge -> posedge" in l]
    if not inicios:
        return None
    nombres, logica, ruteo, acarreo = [], 0.0, 0.0, 0
    for l in lineas[inicios[-1] + 2:]:
        m = re.match(r"Info: ([\d.]+) ns logic, ([\d.]+) ns routing", l)
        if m:
            logica, ruteo = float(m.group(1)), float(m.group(2))
            break
        m = re.match(r"Info:\s+([\w-]+)\s+([\d.]+)\s+([\d.]+)\s+(Source|Net)\s+(\S+)", l)
        if m:
            nombres.append(m.group(5))
            if "CARRY" in m.group(5) or "carry" in m.group(5):
                acarreo += 1
    if not nombres:
        return None
    corto = lambda s: s if len(s) <= 70 else s[:67] + "..."   # noqa: E731
    return {"semilla": peor, "ns": 1000.0 / min(f), "logica": logica, "ruteo": ruteo, "tramos": len(nombres),
            "acarreo": acarreo, "desde": corto(nombres[0]), "hasta": corto(nombres[-1])}


def main():
    if len(sys.argv) < 6:
        sys.exit(__doc__)
    carpeta_lineas, carpeta_var, semillas, carpeta_med = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    items = leer_variantes(sys.argv[5:])
    med = {it[1]: medicion(carpeta_lineas, carpeta_var, it[1], semillas) for it in items if it[0] == "var"}

    def version(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True).stdout.strip() or \
                   subprocess.run(cmd, capture_output=True, text=True).stderr.strip()
        except OSError:
            return "?"

    out = []
    out.append("Recursos y frecuencia máxima del diseño integrado")
    out.append("Generado por factibilidad/i_integrado/tools/medir.sh (make recursos). No editar a mano.")
    out.append("")
    out.append(f"Herramientas: {version(['yosys', '-V'])}")
    out.append(f"              {version(['nextpnr-ice40', '--version']).splitlines()[0] if version(['nextpnr-ice40', '--version']) else '?'}")
    out.append(f"Flujo: tools/medir_variante.sh del repositorio, nextpnr-ice40 --hx1k --package vq100 --freq 25, goboard.pcf, semillas 1 a {semillas}.")
    out.append("SoC completo: core, memoria, esclavo SPI, periféricos y contador de reset. La FPGA tiene 1280 celdas lógicas y 16 BRAM.")
    out.append("Programa: la regla base (sw/trade.s) en el hilo 0 en las variantes del barrel, y sw/trade.hex en las demás.")
    out.append("'agrega' es la diferencia de celdas contra la variante de la columna 'contra'. fmin, fmed y fmax son la frecuencia")
    out.append("máxima mínima, mediana y máxima entre las semillas, en MHz. 'cierran' cuenta las semillas que cumplen los 25 MHz.")
    out.append("El conteo de celdas de un mismo circuito se mueve unas 10 celdas entre síntesis (decisión T6).")
    out.append("")
    cab = f"{'variante':<15} {'celdas':>6} {'agrega':>6} {'contra':<10} {'libres':>6} {'BRAM':>4} {'LUT4':>5} {'fmin':>7} {'fmed':>7} {'fmax':>7} {'cierran':>8}  qué es"
    for it in items:
        if it[0] == "grupo":
            out.append("")
            out.append("-- " + it[1])
            out.append(cab)
            continue
        _, etq, fuentes, defs, params, ref, desc = it
        r = med[etq]
        if r is None:
            out.append(f"{etq:<15} {'(sin medir)':>6}  {desc}")
            continue
        celdas = r["celdas"]
        bram = r["bram"] if r["bram"] is not None else r["yosys_bram"]
        agrega = ""
        if ref and med.get(ref) and med[ref]["celdas"] is not None and celdas is not None:
            agrega = f"{celdas - med[ref]['celdas']:+d}"
        libres = f"{CELDAS - celdas:d}" if celdas is not None else "?"
        nota = ""
        if celdas is not None and celdas > CELDAS:
            nota = "NO CABE (celdas). "
        if bram is not None and bram > BRAMS:
            nota += "NO CABE (BRAM). "
        if r["cierran"] != r["de"] and not nota:
            nota = "NO CIERRA en todas las semillas. "
        out.append(f"{etq:<15} {celdas if celdas is not None else '?':>6} {agrega:>6} {ref:<10} {libres:>6} "
                   f"{bram if bram is not None else '?':>4} {r['lut'] if r['lut'] is not None else '?':>5} "
                   f"{r['fmin']:>7.2f} {r['fmed']:>7.2f} {r['fmax']:>7.2f} {str(r['cierran']) + ' de ' + str(r['de']):>8}  {nota}{desc}")

    out.append("")
    out.append("Definiciones y parámetros de cada variante")
    for it in items:
        if it[0] != "var":
            continue
        _, etq, fuentes, defs, params, ref, desc = it
        out.append(f"  {etq:<15} fuentes {fuentes:<10} {defs if defs else '(sin definiciones)'}{'   parámetros: ' + params if params else ''}")

    out.append("")
    out.append(f"Frecuencia máxima por semilla (MHz), semillas 1 a {semillas}. Un 0 es una semilla en que nextpnr no terminó.")
    for it in items:
        if it[0] != "var" or med[it[1]] is None:
            continue
        r = med[it[1]]
        out.append(f"  {it[1]:<15} {' '.join(r['por_semilla'])}")

    out.append("")
    out.append("Primitiva SB_WARMBOOT ubicada por nextpnr (semilla 1), en las variantes con vigilante")
    for it in items:
        if it[0] != "var" or med[it[1]] is None or not med[it[1]]["warmboot"]:
            continue
        out.append(f"  {it[1]:<15} SB_WARMBOOT: {med[it[1]]['warmboot']}")

    out.append("")
    out.append("Ruta crítica de la semilla más lenta (de flanco de subida a flanco de subida), del log de nextpnr")
    out.append(f"  {'variante':<15} {'semilla':>7} {'ns':>6} {'lógica':>7} {'ruteo':>6} {'tramos':>6} {'acarreo':>7}  desde -> hasta")
    for it in items:
        if it[0] != "var" or med[it[1]] is None:
            continue
        rc = ruta_critica(carpeta_var, it[1], med[it[1]]["por_semilla"])
        if rc:
            out.append(f"  {it[1]:<15} {rc['semilla']:>7} {rc['ns']:>6.2f} {rc['logica']:>7.2f} {rc['ruteo']:>6.2f} {rc['tramos']:>6} {rc['acarreo']:>7}  "
                       f"{rc['desde']} -> {rc['hasta']}")
    out.append("  'acarreo' cuenta los tramos de la ruta que son de la cadena de acarreo de un sumador.")

    errores = [(it[1], med[it[1]]["error"]) for it in items if it[0] == "var" and med[it[1]] and med[it[1]]["error"]]
    if errores:
        out.append("")
        out.append("Variantes que nextpnr no terminó (semilla 1)")
        for etq, e in errores:
            out.append(f"  {etq:<15} {e}")

    os.makedirs(carpeta_med, exist_ok=True)
    with open(os.path.join(carpeta_med, "recursos.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
