#!/usr/bin/env python3
"""contabilidad_rtl.py: R3 por el RTL contra el testbench oficial, con la cuenta que emula el programa
comparada con la de la maestra en cada tick.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Para cada serie de 20 000 ticks y cada ritmo:
  1. Una copia parametrizada de tb/tb_proyecto_4.sv (cambian PROGRAMA, PERIODO_NS, NTICKS y SERIE; el
     método de tools/c1/oficial.sh) instanciada dentro de tb/c1/tb_mon.sv, que no la toca y compara, en
     cada tick, D_CAJA, D_ACC y D_W del programa (memoria de datos del RTL de R3) con la caja, las
     acciones y el patrimonio de la maestra.
  2. Exige: el testbench oficial en 4/4; su decisiones.csv (bytes, caja, acciones y patrimonio por tick)
     idéntico, byte a byte, al de ref/c1/c1.py; el monitor con 0 diferencias en los 20 000 ticks; y el
     patrimonio final, las órdenes y la pérdida máxima que imprime el testbench iguales a los que se
     recalculan con ref/market.py desde los bytes del CSV.
Más dos controles negativos en Meta, que tienen que dar diferencias (si no, el monitor no ve nada): la dirección
de D_CAJA corrida a la de D_ACC, y el programa del tick n comparado con la maestra del tick n-1, que es como se vería
una orden ejecutada un tick tarde.

Series: Meta de práctica (data/practica_meta.csv, apuesta una vez en la fase A) y las 12 de
tools/c1/contabilidad_series.py (otras acciones, de $P4_DATOS). Ritmos: 0,1 y 1 ms; --ritmos agrega o
quita (el de 10 ms tarda unos 22 minutos por serie y no entra en la contabilidad).

Cada corrida deja una línea de INICIO y otra de FIN en docs/mediciones/c1/contabilidad_rtl_avance.txt, con
sus archivos en build/c1/contabilidad_rtl/. Si se repite, no rehace las que ya pasaron (--rehacer las
fuerza). Resumen en docs/mediciones/c1/contabilidad_rtl.txt.

Uso: python3 tools/c1/contabilidad_rtl.py [--ritmos 100000,1000000] [--jobs 22] [--rehacer]
"""
import argparse
import concurrent.futures as cf
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, os.path.join(RAIZ, "tools", "fondo"))
import market  # noqa: E402
import simbolos  # noqa: E402

B = os.path.join(RAIZ, "build", "c1", "contabilidad_rtl")
AVANCE = os.path.join(RAIZ, "docs", "mediciones", "c1", "contabilidad_rtl_avance.txt")
RESUMEN = os.path.join(RAIZ, "docs", "mediciones", "c1", "contabilidad_rtl.txt")
NTICKS = 20000
NOMBRE_RITMO = {100000: "0,1 ms", 1000000: "1 ms", 10000000: "10 ms"}


def avance(texto):
    with open(AVANCE, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {texto}\n")


def bash(cmd, **kw):
    return subprocess.run(["bash", "-c", cmd], cwd=RAIZ, **kw)


def compilar(periodo, hexa, base):
    """Copia parametrizada del testbench oficial y Verilator con el monitor. Devuelve (binario, error)."""
    d = os.path.join(B, f"obj_{periodo}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(RAIZ, "tb", "tb_proyecto_4.sv"), encoding="utf-8") as f:
        t = f.read()
    cambios = [(r'PROGRAMA   = "[^"]*";', f'PROGRAMA   = "{hexa}";'), (r"PERIODO_NS = [0-9]*;", f"PERIODO_NS = {periodo};"),
               (r"NTICKS     = [0-9]*;", f"NTICKS     = {NTICKS};"), (r'SERIE      = "[^"]*";', 'SERIE      = "serie.csv";')]
    copia = t
    for patron, nuevo in cambios:
        copia = re.sub(patron, nuevo, copia, count=1)
    ruta = os.path.join(d, "tb_p4.sv")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(copia)
    nuevas = sum(1 for a, b in zip(t.split("\n"), copia.split("\n")) if a != b)
    if nuevas > 5:
        return None, f"la copia cambió {nuevas} líneas del testbench oficial (se permiten 5)"
    r = bash(f'source tools/c1/comun.sh; verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_mon '
             f'-DNO_ICE40_DEFAULT_ASSIGNMENTS -O3 --Mdir "{d}/obj" -o sim "$CELLS_SIM" $C1_SRC tb/c1/tb_mon.sv "{ruta}"',
             capture_output=True, text=True)
    if r.returncode:
        return None, "Verilator no compila: " + r.stdout[-300:] + r.stderr[-300:]
    return os.path.join(d, "obj", "sim"), None


def correr(tarea):
    """Una serie a un ritmo. Devuelve (veredicto, línea de resumen)."""
    nombre, serie, periodo, sim, dirs, control, rehacer = tarea
    etiqueta = f"{nombre}_{periodo}" + (f"_control_{control}" if control else "")
    d = os.path.join(B, etiqueta)
    res = os.path.join(d, "resultado.txt")
    if os.path.exists(res) and not rehacer:
        previo = open(res).read().strip()
        if previo.startswith("PASS"):
            avance(f"OMITIDA {etiqueta}: {previo}")
            return "PASS", previo
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "sw"))
    shutil.copy(os.path.join(RAIZ, "sw", "c1_tabla.hex"), os.path.join(d, "sw", "c1_tabla.hex"))
    shutil.copy(serie, os.path.join(d, "serie.csv"))
    t0 = time.time()
    avance(f"INICIO {etiqueta}")
    a_caja, a_acc, a_w = dirs["D_CAJA"], dirs["D_ACC"], dirs["D_W"]
    if control == "direccion":
        a_caja = a_acc                      # el monitor mira la dirección equivocada: tiene que ver diferencias
    extra = ["+DESFASE=1"] if control == "desfase" else []   # el programa del tick n contra la maestra del tick n-1
    with open(os.path.join(d, "tb.log"), "w") as log:
        subprocess.run([sim, f"+A_CAJA={a_caja}", f"+A_ACC={a_acc}", f"+A_W={a_w}", "+MON=monitor.csv"] + extra, cwd=d,
                       stdout=log, stderr=subprocess.STDOUT)
    with open(os.path.join(d, "ref.log"), "w") as log:
        subprocess.run([sys.executable, "ref/c1/c1.py", serie, "--nticks", str(NTICKS), "--periodo-ns", str(periodo), "-o",
                        os.path.join(d, "ref.csv")], cwd=RAIZ, stdout=log, stderr=subprocess.STDOUT)
    errores = []
    tb = open(os.path.join(d, "tb.log"), errors="replace").read()
    if "Testbenchs aprobados: 4/4" not in tb:
        errores.append("el testbench oficial no entrega 4/4")
    mon = re.search(r"MONITOR ticks=(\d+) diferencias=(\d+) primera=(-?\d+)", tb)
    if not mon:
        errores.append("el monitor no terminó")
        ticks_mon, difs_mon, primera = 0, -1, -1
    else:
        ticks_mon, difs_mon, primera = map(int, mon.groups())
    if mon and ticks_mon != NTICKS:
        errores.append(f"el monitor comparó {ticks_mon} ticks y se esperaban {NTICKS}")
    csv_tb, csv_ref = os.path.join(d, "decisiones.csv"), os.path.join(d, "ref.csv")
    if not (os.path.exists(csv_tb) and os.path.exists(csv_ref)):
        errores.append("falta decisiones.csv o la referencia")
        w = ordenes = parciales = 0
    else:
        if open(csv_tb, "rb").read() != open(csv_ref, "rb").read():
            errores.append("decisiones.csv distinto al de ref/c1/c1.py")
        filas = market.leer_csv(csv_tb)
        m = market.simular([f[1] for f in filas], [f[2] for f in filas])
        w, ordenes = m.w, m.ordenes
        parciales = sum(1 for a_, b_ in zip(filas, filas[1:]) if b_[2] >> 6 in (1, 2) and 0 < (b_[2] & 63) < 63 and a_[3:5] != b_[3:5])
        for campo, valor in (("Patrimonio final", m.w), ("Ordenes ejecutadas", m.ordenes), ("Perdida maxima", m.max_dd)):
            x = re.search(campo + r":\s+(-?\d+)", tb)
            if not x or int(x.group(1)) != valor:
                errores.append(f"{campo}: el testbench dice {x.group(1) if x else '?'} y market.py {valor}")
    peor = re.search(r"Peor caso precio->decision: (\d+) ciclos \(disponibles: (\d+)\)", tb)
    if control:
        veredicto = "PASS" if difs_mon > 0 else "FAIL"
        que = ("con D_CAJA apuntando a D_ACC" if control == "direccion" else
               "comparando el programa del tick n con la maestra del tick n-1 (una orden ejecutada un tick tarde)")
        linea = (f"{veredicto} control negativo {nombre} a {NOMBRE_RITMO.get(periodo, periodo)}: {que} el monitor ve "
                 f"{difs_mon} ticks con diferencia (primero en el {primera}); el testbench oficial sigue en "
                 f"{'4/4' if 'Testbenchs aprobados: 4/4' in tb else 'FALLA'}" + ("" if veredicto == "PASS" else "; el monitor no ve nada"))
    else:
        veredicto = "FAIL" if errores or difs_mon != 0 else "PASS"
        linea = (f"{veredicto} {nombre} a {NOMBRE_RITMO.get(periodo, periodo)}: 4/4, decisiones.csv idéntico a ref/c1/c1.py "
                 f"({NTICKS} filas con caja, acciones y patrimonio), monitor {ticks_mon} ticks y {difs_mon} diferencias, "
                 f"patrimonio {w}, {ordenes} órdenes ({parciales} parciales), peor caso {peor.group(1) if peor else '?'} de {peor.group(2) if peor else '?'} ciclos")
        if veredicto == "FAIL":
            linea += ". " + "; ".join(errores) + (f"; el monitor ve la primera diferencia en el tick {primera}" if difs_mon > 0 else "")
    with open(res, "w") as f:
        f.write(linea + "\n")
    avance(f"FIN {etiqueta} ({time.time() - t0:.0f} s): {linea}")
    return veredicto, linea


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ritmos", default="100000,1000000", help="períodos en ns, separados por coma")
    ap.add_argument("--jobs", type=int, default=22)
    ap.add_argument("--rehacer", action="store_true")
    a = ap.parse_args()
    ritmos = [int(x) for x in a.ritmos.split(",")]
    os.makedirs(B, exist_ok=True)
    avance(f"== corrida con ritmos {ritmos}, commit {subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=RAIZ, capture_output=True, text=True).stdout.strip()}")

    # el programa y las direcciones de la cuenta emulada
    hexa = os.path.join(B, "c1.hex")
    e, palabras = simbolos.ensamblar(os.path.join(RAIZ, "sw", "c1.s"))
    with open(hexa, "w") as f:
        f.write("".join(f"{w:08x}\n" for w in palabras))
    dirs = {k: e.simbolos[k] for k in ("D_CAJA", "D_ACC", "D_W")}

    # las series
    carpeta = os.path.join(B, "series")
    r = subprocess.run([sys.executable, "tools/c1/contabilidad_series.py", carpeta], cwd=RAIZ, capture_output=True, text=True)
    if r.returncode:
        print("FAIL: no se pudieron armar las series (falta $P4_DATOS/otras):\n" + r.stderr[-400:])
        return 1
    lista = open(os.path.join(carpeta, "lista.txt")).read().rstrip("\n")
    series = [("meta", os.path.join(RAIZ, "data", "practica_meta.csv"))]
    series += [(f[:-4], os.path.join(carpeta, f)) for f in sorted(os.listdir(carpeta)) if f.endswith(".csv")]

    # compilación, una por ritmo
    sims = {}
    for p in ritmos:
        sim, err = compilar(p, hexa, B)
        if err:
            print(f"FAIL: {err}")
            return 1
        sims[p] = sim
    # los de 1 ms o más primero: son los más largos
    tareas = [(n, s, p, sims[p], dirs, False, "rehacer" if a.rehacer else "") for p in sorted(ritmos, reverse=True) for n, s in series]
    for c in ("direccion", "desfase"):
        tareas.append(("meta", series[0][1], ritmos[0], sims[ritmos[0]], dirs, c, "rehacer" if a.rehacer else ""))
    t0 = time.time()
    resultados = []
    with cf.ProcessPoolExecutor(max_workers=a.jobs, mp_context=__import__("multiprocessing").get_context("fork")) as ex:
        for veredicto, linea in ex.map(correr, tareas):
            resultados.append((veredicto, linea))
            print(linea, flush=True)
    fallos = sum(1 for v, _ in resultados if v != "PASS")

    iv = subprocess.run(["verilator", "--version"], capture_output=True, text=True).stdout.strip()
    cab = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
    sha = lambda ruta: hashlib.sha256(open(os.path.join(RAIZ, ruta), "rb").read()).hexdigest()[:16]
    with open(RESUMEN, "w", newline="\n") as f:
        f.write("R3 por el RTL contra el testbench oficial, con la cuenta emulada comparada con la de la maestra\n")
        f.write("Generado por tools/c1/contabilidad_rtl.py. No editar a mano.\n\n")
        f.write(f"Commit de partida: {cab}. {iv}\n")
        for ruta in ("tb/tb_proyecto_4.sv", "tb/c1/tb_mon.sv", "sw/c1.s", "sw/c1_tabla.hex", "ref/c1/c1.py"):
            f.write(f"{ruta} sha256 {sha(ruta)}...\n")
        f.write("Hardware (R3): pochoco_soc con -DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA -DESPINO_VIGILANTE -DESPINO_TABLA_512\n")
        f.write(f"Direcciones de la cuenta emulada: " + ", ".join(f"{k} {v}" for k, v in dirs.items()) + "\n")
        f.write(f"Ritmos: {', '.join(NOMBRE_RITMO.get(p, str(p)) for p in ritmos)}. 20 000 ticks por serie.\n\n")
        f.write(lista + "\n(más Meta, data/practica_meta.csv)\n\n")
        for _, linea in resultados:
            f.write(linea + "\n")
        f.write(f"\n{'PASS' if fallos == 0 else 'FAIL'}: {len(resultados) - fallos} de {len(resultados)} corridas ({time.time() - t0:.0f} s)\n")
    print(f"\n{'PASS' if fallos == 0 else 'FAIL'}: {len(resultados) - fallos} de {len(resultados)} corridas, resumen en {os.path.relpath(RESUMEN, RAIZ)}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
