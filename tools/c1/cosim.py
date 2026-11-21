#!/usr/bin/env python3
"""cosim.py: el gemelo digital con la tabla de 512 palabras y sw/c1.s, contra el RTL de R3.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Es tools/gemelo_barrel.py (make cosim-barrel) con el hardware y el programa de R3: el mismo
testbench de traza (tb/barrel/tb_gemelo.sv, sin tocar) compilado con -DESPINO_TABLA_512, y el
gemelo con --tabla sw/c1_tabla.hex (512 valores). Para cada configuración exige tres archivos
idénticos byte a byte entre el RTL y el gemelo:

  traza       cada escritura al banco de registros (con su hilo), cada acceso al bus de datos
              (también las lecturas de la tabla con lw y con lbu), cada precio y cada byte de MISO,
              con su número de ciclo
  ticks       por tick: ciclo del precio, ciclos e IC del hilo 0 hasta DECISION
  decisiones  el decisiones.csv del testbench oficial

Las configuraciones cubren lo que el programa de R2 no ejercita: los cuatro hilos trabajando,
las lecturas de byte en la tabla, la entrada a media posición, el primer extremo, el candado,
un hilo colgado (plazo vencido y modo seguro), un dato que llega tarde, el reset a mitad de una
transacción, tiempos de SPI distintos, rondas seguidas a los tres períodos y precios pegados.

Además: el gemelo con y sin el atajo del sondeo da las mismas decisiones, mediciones por tick y
conteos en la serie Meta completa a los tres períodos; y dos controles negativos (el gemelo con
--borde 0 y el gemelo con la tabla de R2) tienen que dar una traza distinta.

El vigilante no existe en el gemelo: el hardware de la comparación es el de R3 sin
-DESPINO_VIGILANTE, que mientras no dispare no cambia nada (lo vigilan las demás pruebas).

Uso, desde la raíz:  python3 tools/c1/cosim.py [--corta] [--jobs N]   (make c1-cosim)
Resultado en docs/mediciones/c1/cosim.txt.
"""
import argparse
import filecmp
import multiprocessing
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "tools"))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, os.path.join(RAIZ, "ref", "c1"))
sys.path.insert(0, os.path.join(RAIZ, "ref", "cotas"))

import gemelo_barrel as G   # noqa: E402
import c1 as R              # noqa: E402
import tablas as TB         # noqa: E402
import comun                # noqa: E402
import market               # noqa: E402
import series               # noqa: E402

B = "build/c1/cosim"
TABLA = "sw/c1_tabla.hex"
DEFS = "-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA -DESPINO_TABLA_512"
G.B = B
G.TABLA = TABLA
G.HW = {"c1": (DEFS, 3, 12), "c1_por6": (DEFS, 3, 6)}


def variante(fallas, nombre):
    G.sh([sys.executable, "tools/c1/variante.py", fallas, "-o", f"{B}/prog/{nombre}.s"])
    G.ensamblar(f"{B}/prog/{nombre}.s", f"{B}/prog/{nombre}.hex")
    return f"{B}/prog/{nombre}.hex"


def ventana_con(precios, condicion, largo, margen=150):
    """Primera ventana de `largo` ticks de la serie, normalizada de nuevo, en que la referencia
    cumple `condicion` (una función del objeto C1) antes del tick largo - margen."""
    T = TB.leer_hex(os.path.join(RAIZ, TABLA))
    for ini in range(0, len(precios) - largo, 250):
        w = comun.normalizar(precios[ini:ini + largo])
        c = R.C1(T)
        for k, p in enumerate(w):
            c.paso(p)
            if condicion(c):
                break
        if condicion(c) and 400 < k < largo - margen:
            return w, ini, k + 1
    raise SystemExit("no hay una ventana con esa condición")


def serie_fase_a(n=1000):
    """Serie hecha a mano para que la fase A apueste: sube de 150 a 255 en 640 ticks con poco ruido
    (un paso de más o de menos en 2 de cada 10 ticks, de un generador congruencial fijo) y después
    baja. Con sw/c1_tabla.hex entra a media posición cerca del tick 549 y llega al candado en el
    primer extremo, cerca del 638. Pasado el tick 1000 oscila entre 105 y 255."""
    x, out = 12345, []
    for t in range(n):
        if t < 640:
            obj = 150 + t * 105 // 640
        elif t < 1000:
            obj = 255 - (t - 640) * 100 // 360
        else:                              # después: sube y baja entre 105 y 255 cada 800 ticks
            u = (t - 1000) % 800
            obj = 155 + u * 100 // 250 if u < 250 else 255 - (u - 250) * 150 // 300 if u < 550 else 105 + (u - 550) * 50 // 250
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        r = (x >> 16) % 10
        out.append(max(100, min(255, obj + (1 if r == 0 else -1 if r == 1 else 0))))
    return out


def preparar():
    for d in ("prog", "series"):
        os.makedirs(os.path.join(RAIZ, B, d), exist_ok=True)
    G.ensamblar("sw/c1.s", f"{B}/prog/c1.hex")
    c1 = f"{B}/prog/c1.hex"
    meta = market.leer_serie(os.path.join(RAIZ, "data/practica_meta.csv"))
    s = f"{B}/series"
    notas = []
    # ventanas en que pasa algo dentro de pocos ticks: media posición en la fase A, motor, candado
    w = serie_fase_a()
    c = R.C1(TB.leer_hex(os.path.join(RAIZ, TABLA)))
    k_a = k_c = None
    for k, p in enumerate(w):
        c.paso(p)
        if k_a is None and c.acc > 0 and c.modo == R.MODO_A:
            k_a = k + 1
        if k_c is None and c.modo == R.MODO_COPIA:
            k_c = k + 1
    if k_a is None or k_c is None:
        raise SystemExit("la serie hecha a mano ya no apuesta en la fase A con esta tabla")
    series.escribir_csv(f"{s}/fase_a.csv", w)
    notas.append(f"fase_a: serie hecha a mano, media posición en el tick {k_a} y candado en el {k_c}")
    w, ini, k = ventana_con(meta, lambda c: c.modo == R.MODO_REC, 1200)
    series.escribir_csv(f"{s}/motor.csv", w)
    notas.append(f"motor: serie Meta desde {ini}, primer extremo en el tick {k}")
    k_motor = k
    w, ini, k = ventana_con(meta, lambda c: c.modo == R.MODO_COPIA, 2500)
    series.escribir_csv(f"{s}/candado.csv", w)
    notas.append(f"candado: serie Meta desde {ini}, candado en el tick {k}")
    series.escribir_csv(f"{s}/pegada_100.csv", [100] * 500)
    series.escribir_csv(f"{s}/pegada_255.csv", [255] * 500)
    series.escribir_csv(f"{s}/pegada_1.csv", [1] * 200)
    series.escribir_csv(f"{s}/rondas.csv", comun.normalizar(meta[2775:2775 + 120]))
    cruda = market.leer_serie(os.path.join(RAIZ, "tb/practica.csv"))
    series.escribir_csv(f"{s}/cruda.csv", cruda[:600])
    fin_reset = G.FIN_RESET_NS
    casos = [
        # nombre, hardware, programa, serie, plusargs
        ("A_oficial_fase_a", "c1", c1, f"{s}/fase_a.csv", dict(NTICKS=1000)),
        ("B_motor", "c1", c1, f"{s}/motor.csv", dict(NTICKS=1200)),
        ("C_candado", "c1", c1, f"{s}/candado.csv", dict(NTICKS=2500)),
        ("D1_fases_sclk500k", "c1", c1, f"{s}/motor.csv",
         dict(NTICKS=700, PERIODO_NS=100010, INICIO_NS=3999, SCLK_MEDIO_NS=1000, CS_SETUP_NS=2500, CS_HOLD_NS=700)),
        ("D2_sclk100k_reset63", "c1_por6", c1, f"{s}/motor.csv",
         dict(NTICKS=450, PERIODO_NS=400000, INICIO_NS=2000, SCLK_MEDIO_NS=5000, CS_SETUP_NS=15000, CS_HOLD_NS=5000)),
        ("D3_tiempos_raros", "c1", c1, f"{s}/fase_a.csv",
         dict(NTICKS=700, PERIODO_NS=60010, INICIO_NS=4013, SCLK_MEDIO_NS=530, CS_SETUP_NS=1130, CS_HOLD_NS=470)),
        ("E1_hilo1_colgado", "c1", variante(f"cuelga:1:{k_motor + 20}", "cuelga1"), f"{s}/motor.csv", dict(NTICKS=k_motor + 150)),
        ("E2_hilo2_colgado", "c1", variante(f"cuelga:2:{k_a + 10}", "cuelga2"), f"{s}/fase_a.csv", dict(NTICKS=k_a + 150)),
        ("E3_hilo3_colgado", "c1", variante(f"cuelga:3:{k_motor + 20}", "cuelga3"), f"{s}/motor.csv", dict(NTICKS=k_motor + 150)),
        ("E4_dato_tardio", "c1", variante(f"atraso:2:{k_motor + 20}:150+atraso:1:{k_motor + 40}:150", "atraso"),
         f"{s}/motor.csv", dict(NTICKS=k_motor + 150)),
        ("F_rondas_10ms_1ms_01ms", "c1", c1, f"{s}/rondas.csv",
         dict(NTICKS=120, RONDA_TICKS=40, PAUSA_NS=2000000, PERIODO_NS=10000000, PERIODO2_NS=1000000, PERIODO3_NS=100000)),
        ("G1_reset_desde_0", "c1", c1, f"{s}/fase_a.csv", dict(NTICKS=500, INICIO_NS=0)),
        ("G2_reset_a_mitad", "c1", c1, f"{s}/fase_a.csv", dict(NTICKS=500, INICIO_NS=fin_reset - 1500 - 4000 + 300)),
        ("H1_pegada_100", "c1", c1, f"{s}/pegada_100.csv", dict(NTICKS=500)),
        ("H2_pegada_255", "c1", c1, f"{s}/pegada_255.csv", dict(NTICKS=500)),
        ("H3_pegada_1_modo_seguro", "c1", c1, f"{s}/pegada_1.csv", dict(NTICKS=200)),
        ("H4_serie_sin_normalizar", "c1", c1, f"{s}/cruda.csv", dict(NTICKS=600)),
    ]
    return casos, notas


def correr(caso):
    nombre, hw, hexfile, serie, plus = caso
    r = G.correr(caso)
    d = f"{B}/casos/{nombre}"
    _, xd, por = G.HW[hw]
    gem = [G.GEMELO, "--barrel", "--xd", str(xd), "--por-bits", str(por), "--hex", hexfile, "--serie", serie]
    for k, v in plus.items():
        gem += [G.OPCION[k], str(v)]
    neg = []
    if nombre == "A_oficial_fase_a":
        # controles negativos: la coincidencia de SCLK con el reloj al revés, y la tabla de R2 (256 palabras)
        G.sh(gem + ["--tabla", TABLA, "--borde", "0", "--traza", f"{d}/neg_borde.traza"])
        G.sh(gem + ["--tabla", "sw/fondo_tabla.hex", "--traza", f"{d}/neg_tabla.traza"])
        for t in ("neg_borde", "neg_tabla"):
            neg.append((t, not filecmp.cmp(os.path.join(RAIZ, f"{d}/rtl.traza"), os.path.join(RAIZ, f"{d}/{t}.traza"),
                                           shallow=False)))
    return r[0], r[1], r[2], neg, r[4]


def atajo():
    """El gemelo con y sin el atajo del sondeo: serie Meta completa a los tres períodos."""
    filas = []
    for per in (100000, 1000000, 10000000):
        d = f"{B}/atajo_{per}"
        os.makedirs(os.path.join(RAIZ, d), exist_ok=True)
        base = [G.GEMELO, "--barrel", "--xd", "3", "--tabla", TABLA, "--hex", f"{B}/prog/c1.hex",
                "--serie", "data/practica_meta.csv", "--nticks", "20000", "--periodo-ns", str(per)]
        ra = G.sh(base + ["--csv", f"{d}/con.csv", "--ticks", f"{d}/con.ticks"])
        rs = G.sh(base + ["--sin-atajo", "--csv", f"{d}/sin.csv", "--ticks", f"{d}/sin.ticks"])
        ok = all(filecmp.cmp(os.path.join(RAIZ, f"{d}/con.{e}"), os.path.join(RAIZ, f"{d}/sin.{e}"), shallow=False)
                 for e in ("csv", "ticks"))
        sin_saltos = lambda t: [l for l in t.splitlines() if "saltadas" not in l]   # noqa: E731
        ok = ok and sin_saltos(ra.stdout) == sin_saltos(rs.stdout) and "4/4" in ra.stdout
        saltadas = [l for l in ra.stdout.splitlines() if "saltadas" in l][0].split(",")[-1].strip()
        filas.append((per, ok, saltadas))
    return filas


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--corta", action="store_true")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--salida", default="docs/mediciones/c1/cosim.txt")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    r = G.sh(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", G.GEMELO, "ref/gemelo/gemelo.c"])
    if r.returncode != 0:
        raise SystemExit("FAIL: el gemelo no compila\n" + r.stderr)
    casos, notas = preparar()
    if a.corta:
        casos = [c for c in casos if c[0][:2] in ("A_", "B_", "E3", "E4", "F_")]
    with multiprocessing.get_context("fork").Pool(a.jobs) as pool:
        pool.map(G.compilar_hw, sorted({c[1] for c in casos}))
        res = pool.map(correr, casos)
    filas_atajo = [] if a.corta else atajo()

    commit = G.sh(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    sucio = " con cambios sin commit" if G.sh(["git", "status", "--porcelain", "ref/gemelo", "tb/barrel", "rtl", "sw/c1.s"]).stdout else ""
    lineas = ["Gemelo digital con la tabla de 512 palabras y sw/c1.s contra el RTL de R3",
              f"Generado por tools/c1/cosim.py{' --corta' if a.corta else ''} (make c1-cosim). No editar a mano.",
              f"Commit {commit}{sucio}. {G.sh(['verilator', '--version']).stdout.strip()}",
              f"Hardware: pochoco_soc con {DEFS}", "",
              "Traza, mediciones por tick y decisiones.csv del RTL (tb/barrel/tb_gemelo.sv, Verilator)",
              "contra el gemelo (build/gemelo --barrel --xd 3 --tabla sw/c1_tabla.hex), byte a byte.", ""]
    lineas += ["Series: " + "; ".join(notas), ""]
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
        lineas += ["", "Gemelo con y sin el atajo del sondeo, sw/c1.s, serie Meta completa (20 000 ticks):"]
        for per, ok, saltadas in filas_atajo:
            fallas += not ok
            lineas.append(f"{'PASS' if ok else 'FAIL'} periodo {per} ns: decisiones, ticks y conteos "
                          f"{'identicos' if ok else 'DISTINTOS'}, 4/4 ({saltadas})")
    lineas += ["", f"{'PASS' if fallas == 0 else 'FAIL'}: {fallas} fallas"]
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    with open(os.path.join(RAIZ, a.salida if not a.corta else f"{B}/corta.txt"), "w") as f:
        f.write(texto)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
