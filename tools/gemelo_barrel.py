#!/usr/bin/env python3
"""gemelo_barrel.py: validación del gemelo digital del Espino barrel contra el RTL.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Para cada configuración corre el mismo programa y la misma maestra en dos
lados y exige tres archivos idénticos byte a byte:

  RTL      tb/barrel/tb_gemelo.sv con Verilator (se compila una vez por
           hardware: con y sin la extensión, y con el reset corto)
  gemelo   build/gemelo --barrel (ref/gemelo/gemelo.c)

  traza       cada escritura al banco de registros (con su hilo), cada acceso
              al bus de datos, cada precio recibido y cada byte que sale por
              MISO, con su número de ciclo
  ticks       por tick: ciclo del precio, ciclos e IC del hilo 0 hasta DECISION
              y hasta que vuelve a sondear
  decisiones  el decisiones.csv del testbench oficial

Además:
  - el gemelo con y sin el atajo del sondeo da las mismas decisiones, las
    mismas mediciones por tick y los mismos conteos de instrucciones, en la
    serie de práctica completa a los tres períodos;
  - control negativo: el gemelo con --borde 0 (la coincidencia de SCLK con el
    reloj resuelta al revés) tiene que dar una traza distinta, y el gemelo con
    la máscara de la extensión equivocada también.

Uso, desde la raíz:  python3 tools/gemelo_barrel.py   (o make cosim-barrel)
Opciones: --corta (pocas configuraciones, para la integración continua),
          --jobs N. Resultado en docs/mediciones/gemelo_barrel.txt.
"""
import argparse
import filecmp
import multiprocessing
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
os.environ["PATH"] = os.path.expanduser("~/herramientas/oss-cad-suite/bin") + os.pathsep + os.environ["PATH"]

import market    # noqa: E402
import series    # noqa: E402

B = "build/gemelo_barrel"
GEMELO = "build/gemelo"
FIN_RESET_NS = ((1 << 12) - 1) * 40 + 20 + 3 * 40

# Hardware: definiciones del RTL, máscara de la extensión para el gemelo y
# ancho del reset
# El hardware del fondo es el de R1: la tabla de parámetros en su BRAM
# (rtl/pochoco_tabla.v, que lee sw/fondo_tabla.hex) y el gemelo con --tabla.
TABLA = "sw/fondo_tabla.hex"
HW = {
    "fondo":      ("-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA", 3, 12),
    "fondo_por6": ("-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA", 3, 6),
    "xd7":        ("-DESPINO_BARREL -DESPINO_XD", 7, 12),
    "sin_xd":     ("-DESPINO_BARREL", 0, 12),
}

# plusarg del testbench -> opción del gemelo
OPCION = {
    "NTICKS": "--nticks", "PERIODO_NS": "--periodo-ns", "PERIODO2_NS": "--periodo2-ns",
    "PERIODO3_NS": "--periodo3-ns", "RONDA_TICKS": "--ronda-ticks", "PAUSA_NS": "--pausa-ns",
    "INICIO_NS": "--inicio-ns", "SCLK_MEDIO_NS": "--sclk-medio-ns", "CS_SETUP_NS": "--cs-sclk-ns",
    "CS_HOLD_NS": "--cs-hold-ns",
}


def sh(cmd, log=None):
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
    if log:
        with open(os.path.join(RAIZ, log), "w") as f:
            f.write(r.stdout + r.stderr)
    return r


def compilar_hw(nombre):
    defs, _, por = HW[nombre]
    d = f"{B}/hw_{nombre}"
    sim = f"{d}/obj/sim"
    fuentes = sorted(f"rtl/{f}" for f in os.listdir(os.path.join(RAIZ, "rtl")) if f.endswith(".v") and not f.startswith("00_")) + \
        sorted(f"rtl/espino_core/{f}" for f in os.listdir(os.path.join(RAIZ, "rtl/espino_core")) if f.endswith(".v"))
    cells = subprocess.check_output(["yosys-config", "--datdir"], text=True).strip() + "/ice40/cells_sim.v"
    os.makedirs(os.path.join(RAIZ, d), exist_ok=True)
    r = sh(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", "tb_gemelo",
            "-DNO_ICE40_DEFAULT_ASSIGNMENTS", *defs.split(), f"-GPOR={por}", "-O3", "--Mdir", f"{d}/obj", "-o", "sim",
            cells, *fuentes, "tb/barrel/tb_gemelo.sv"], log=f"{d}/verilator.log")
    if r.returncode != 0:
        raise SystemExit(f"FAIL: Verilator no compila tb_gemelo.sv para {nombre} (ver {d}/verilator.log)")
    return sim


def ensamblar(fuente, hexfile, *opciones):
    r = sh([sys.executable, "tools/pochoasm.py", *opciones, fuente, "-o", hexfile])
    if r.returncode != 0:
        raise SystemExit(f"FAIL: no ensambla {fuente}: {r.stdout}{r.stderr}")


def preparar():
    """Programas y series de las configuraciones. Devuelve la lista de casos."""
    p = f"{B}/prog"
    s = f"{B}/series"
    os.makedirs(os.path.join(RAIZ, p), exist_ok=True)
    os.makedirs(os.path.join(RAIZ, s), exist_ok=True)
    ensamblar("sw/fondo.s", f"{p}/fondo.hex")
    tabla = sh([sys.executable, "tools/barrel/tabla.py", "0", "sw/trade.s"]).stdout
    with open(os.path.join(RAIZ, f"{p}/trade_barrel.s"), "w") as f:
        f.write(tabla)
    ensamblar(f"{p}/trade_barrel.s", f"{p}/trade_barrel.hex")
    for fallas, nombre in (("cuelgue:2:5", "cuelgue"), ("atraso:1:300", "atraso"), ("sin_voto:3:3:40", "sin_voto")):
        sh([sys.executable, "tools/fondo/variante.py", fallas, "-o", f"{p}/fondo_{nombre}.s"])
        ensamblar(f"{p}/fondo_{nombre}.s", f"{p}/fondo_{nombre}.hex")
    for sem, modo, xd in ((1, "separado", 3), (2, "separado", 3), (3, "compartido", 3), (4, "spi1", 3),
                          (5, "separado", 7), (6, "compartido", 7), (7, "trade", 7), (8, "separado", 7)):
        sh([sys.executable, "tools/barrel/prog_hilos.py", str(sem), "--modo", modo, "--xd", str(xd), "-o", f"{p}/al{sem}.s"])
        ensamblar(f"{p}/al{sem}.s", f"{p}/al{sem}.hex", "--allow-shifts", "--xd")

    practica = market.leer_serie("tb/practica.csv")
    series.escribir_csv(f"{s}/pegada_1.csv", [1] * 200)
    series.escribir_csv(f"{s}/pegada_255.csv", [255] * 200)
    series.escribir_csv(f"{s}/reversion.csv", series.lote("reversion", 1, 600, semilla=3)[0])
    series.escribir_csv(f"{s}/saltos.csv", series.lote("saltos", 1, 600, semilla=4)[0])
    series.escribir_csv(f"{s}/rondas.csv", practica[2000:2040] + practica[6000:6040] + practica[12000:12040])

    pr = "tb/practica.csv"
    fondo = f"{p}/fondo.hex"
    casos = [
        # nombre, hardware, programa, serie, plusargs
        ("A_fondo_oficial", "fondo", fondo, pr, dict(NTICKS=300)),
        ("B1_fondo_fases_sclk500k", "fondo", fondo, pr,
         dict(NTICKS=300, PERIODO_NS=100010, INICIO_NS=3999, SCLK_MEDIO_NS=1000, CS_SETUP_NS=2500, CS_HOLD_NS=700)),
        ("B2_fondo_sclk100k_reset63", "fondo_por6", fondo, pr,
         dict(NTICKS=60, PERIODO_NS=400000, INICIO_NS=2000, SCLK_MEDIO_NS=5000, CS_SETUP_NS=15000, CS_HOLD_NS=5000)),
        ("B3_fondo_tiempos_raros", "fondo", fondo, pr,
         dict(NTICKS=300, PERIODO_NS=30010, INICIO_NS=4013, SCLK_MEDIO_NS=530, CS_SETUP_NS=1130, CS_HOLD_NS=470)),
        ("C1_aleatorio_separado_xd3", "fondo", f"{p}/al1.hex", pr, dict(NTICKS=150, PERIODO_NS=30000)),
        ("C2_aleatorio_separado_xd3", "fondo", f"{p}/al2.hex", pr, dict(NTICKS=150, PERIODO_NS=30000)),
        ("C3_aleatorio_compartido_xd3", "fondo", f"{p}/al3.hex", pr, dict(NTICKS=150, PERIODO_NS=30000)),
        ("C4_aleatorio_spi1_xd3", "fondo", f"{p}/al4.hex", pr, dict(NTICKS=150, PERIODO_NS=30000)),
        ("C5_aleatorio_separado_xd7", "xd7", f"{p}/al5.hex", pr, dict(NTICKS=150, PERIODO_NS=30000)),
        ("C6_aleatorio_compartido_xd7", "xd7", f"{p}/al6.hex", pr, dict(NTICKS=150, PERIODO_NS=30000)),
        ("C7_aleatorio_trade_xd7", "xd7", f"{p}/al7.hex", pr, dict(NTICKS=150, PERIODO_NS=30000)),
        ("C8_aleatorio_xd7_en_core_sin_extension", "sin_xd", f"{p}/al8.hex", pr, dict(NTICKS=150, PERIODO_NS=30000)),
        ("D_trade_un_hilo", "sin_xd", f"{p}/trade_barrel.hex", pr, dict(NTICKS=300)),
        ("E1_fondo_gestor_colgado", "fondo", f"{p}/fondo_cuelgue.hex", f"{s}/reversion.csv", dict(NTICKS=300)),
        ("E2_fondo_voto_atrasado", "fondo", f"{p}/fondo_atraso.hex", f"{s}/reversion.csv", dict(NTICKS=300)),
        ("E3_fondo_voto_ausente", "fondo", f"{p}/fondo_sin_voto.hex", f"{s}/saltos.csv", dict(NTICKS=300)),
        ("F_fondo_rondas_10ms_1ms_01ms", "fondo", fondo, f"{s}/rondas.csv",
         dict(NTICKS=120, RONDA_TICKS=40, PAUSA_NS=2000000, PERIODO_NS=10000000, PERIODO2_NS=1000000, PERIODO3_NS=100000)),
        ("G1_fondo_reset_desde_0", "fondo", fondo, pr, dict(NTICKS=150, INICIO_NS=0)),
        ("G2_fondo_reset_a_mitad", "fondo", fondo, pr, dict(NTICKS=150, INICIO_NS=FIN_RESET_NS - 1500 - 4000 + 300)),
        ("H1_fondo_pegada_1", "fondo", fondo, f"{s}/pegada_1.csv", dict(NTICKS=200)),
        ("H2_fondo_pegada_255", "fondo", fondo, f"{s}/pegada_255.csv", dict(NTICKS=200)),
    ]
    return casos


def correr(caso):
    nombre, hw, hexfile, serie, plus = caso
    defs, xd, por = HW[hw]
    d = f"{B}/casos/{nombre}"
    os.makedirs(os.path.join(RAIZ, d), exist_ok=True)
    sim = f"{B}/hw_{hw}/obj/sim"
    r = sh([sim, f"+PROGRAMA={hexfile}", f"+SERIE={serie}", f"+TRAZA={d}/rtl.traza", f"+TICKS={d}/rtl.ticks",
            f"+SALIDA={d}/rtl.csv", *[f"+{k}={v}" for k, v in plus.items()]], log=f"{d}/rtl.log")
    gem = [GEMELO, "--barrel", "--xd", str(xd), "--por-bits", str(por), "--hex", hexfile, "--serie", serie]
    if "-DESPINO_TABLA" in defs:
        gem += ["--tabla", TABLA]
    for k, v in plus.items():
        gem += [OPCION[k], str(v)]
    sh(gem + ["--traza", f"{d}/gem.traza", "--ticks", f"{d}/gem.ticks", "--csv", f"{d}/gem.csv"], log=f"{d}/gem.log")
    res = []
    for ext in ("traza", "ticks", "csv"):
        a, b = os.path.join(RAIZ, f"{d}/rtl.{ext}"), os.path.join(RAIZ, f"{d}/gem.{ext}")
        if not os.path.exists(a) or not os.path.exists(b):
            res.append((ext, False, 0))
            continue
        n = sum(1 for _ in open(a))
        res.append((ext, filecmp.cmp(a, b, shallow=False), n))
    # control negativo en el caso A: --borde 0 y la máscara equivocada deben notarse
    neg = []
    if nombre == "A_fondo_oficial":
        sh(gem + ["--borde", "0", "--traza", f"{d}/neg_borde.traza"])
        sh([g if g != str(xd) else "1" for g in gem] + ["--traza", f"{d}/neg_xd.traza"])
        for t in ("neg_borde", "neg_xd"):
            neg.append((t, not filecmp.cmp(os.path.join(RAIZ, f"{d}/rtl.traza"), os.path.join(RAIZ, f"{d}/{t}.traza"),
                                           shallow=False)))
    eventos = {}
    if os.path.exists(os.path.join(RAIZ, f"{d}/rtl.traza")):
        for linea in open(os.path.join(RAIZ, f"{d}/rtl.traza")):
            c = linea.split()[1]
            eventos[c] = eventos.get(c, 0) + 1
    return nombre, hw, res, neg, eventos


def atajo():
    """El gemelo con y sin atajo, en la práctica completa a los tres períodos."""
    filas = []
    for per in (100000, 1000000, 10000000):
        d = f"{B}/atajo_{per}"
        os.makedirs(os.path.join(RAIZ, d), exist_ok=True)
        base = [GEMELO, "--barrel", "--xd", "3", "--tabla", TABLA, "--hex", f"{B}/prog/fondo.hex", "--periodo-ns", str(per)]
        ra = sh(base + ["--csv", f"{d}/con.csv", "--ticks", f"{d}/con.ticks"])
        rs = sh(base + ["--sin-atajo", "--csv", f"{d}/sin.csv", "--ticks", f"{d}/sin.ticks"])
        ok = all(filecmp.cmp(os.path.join(RAIZ, f"{d}/con.{e}"), os.path.join(RAIZ, f"{d}/sin.{e}"), shallow=False)
                 for e in ("csv", "ticks"))
        sin_saltos = lambda t: [l for l in t.splitlines() if "saltadas" not in l]   # noqa: E731
        ok = ok and sin_saltos(ra.stdout) == sin_saltos(rs.stdout)
        saltadas = [l for l in ra.stdout.splitlines() if "saltadas" in l][0].split(",")[-1].strip()
        filas.append((per, ok, saltadas))
    return filas


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--corta", action="store_true")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--salida", default="docs/mediciones/gemelo_barrel.txt")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    r = sh(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", GEMELO, "ref/gemelo/gemelo.c"])
    if r.returncode != 0:
        raise SystemExit("FAIL: el gemelo no compila\n" + r.stderr)
    casos = preparar()
    if a.corta:
        casos = [c for c in casos if c[0][:2] in ("A_", "B3", "C1", "C5", "E1", "F_")]
    with multiprocessing.Pool(a.jobs) as pool:
        pool.map(compilar_hw, sorted({c[1] for c in casos}))
        res = pool.map(correr, casos)
    filas_atajo = [] if a.corta else atajo()

    commit = sh(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    sucio = " con cambios sin commit" if sh(["git", "status", "--porcelain", "ref/gemelo", "tb/barrel", "rtl"]).stdout else ""
    lineas = ["Gemelo digital del Espino barrel contra el RTL",
              f"Generado por tools/gemelo_barrel.py{' --corta' if a.corta else ''} (make cosim-barrel). No editar a mano.",
              f"Commit {commit}{sucio}. {sh(['verilator', '--version']).stdout.strip()}", "",
              "Traza, mediciones por tick y decisiones.csv del RTL (tb/barrel/tb_gemelo.sv, Verilator)",
              "contra el gemelo (build/gemelo --barrel), byte a byte.", ""]
    fallas = 0
    total_ev = {}
    for nombre, hw, rs, neg, ev in res:
        ok = all(o for _, o, _ in rs)
        fallas += not ok
        for k, v in ev.items():
            total_ev[k] = total_ev.get(k, 0) + v
        det = ", ".join(f"{e} {'igual' if o else 'DISTINTA'} ({n} lineas)" for e, o, n in rs)
        evs = " ".join(f"{k}={ev.get(k, 0)}" for k in "RLWBC")
        lineas.append(f"{'PASS' if ok else 'FAIL'} {nombre} [{hw}]: {det}; eventos {evs}")
        for t, o in neg:
            fallas += not o
            lineas.append(f"{'PASS' if o else 'FAIL'} control negativo {t}: la traza {'difiere' if o else 'NO difiere'} del RTL")
    lineas.append("")
    lineas.append(f"Configuraciones: {len(res)}. Eventos comparados: " +
                  ", ".join(f"{k} {total_ev.get(k, 0)}" for k in "RLWBC") + f", total {sum(total_ev.values())}")
    if filas_atajo:
        lineas += ["", "Gemelo con y sin el atajo del sondeo, sw/fondo.s, practica completa (20 000 ticks):"]
        for per, ok, saltadas in filas_atajo:
            fallas += not ok
            lineas.append(f"{'PASS' if ok else 'FAIL'} periodo {per} ns: decisiones, ticks y conteos "
                          f"{'identicos' if ok else 'DISTINTOS'} ({saltadas})")
    lineas += ["", f"{'PASS' if fallas == 0 else 'FAIL'}: {fallas} fallas"]
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    with open(os.path.join(RAIZ, a.salida if not a.corta else f"{B}/corta.txt"), "w") as f:
        f.write(texto)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
