#!/usr/bin/env python3
"""estres.py: barrido de fases y matriz de estrés del SoC contra ref/trader.py.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Cubre los criterios 4 y 7 de la puerta de simulación (docs/puertas.md):

  fases   el peor caso de respuesta barriendo las 8 fases del lazo de sondeo
          (8 desfases de un ciclo en el inicio, y un período de 2501 ciclos que
          recorre todas las fases dentro de la misma corrida). Exige peor caso
          menor que la mitad del presupuesto de la ronda 3 (1131 ciclos).
  estres  SCLK de 100 kHz a 1 MHz (y más rápido, como exploración), tiempos de
          CS_n distintos, el reset terminando con la maestra a mitad de una
          transacción, rondas seguidas sin reset, series pegadas en 1 y en 255,
          y un período cercano al mínimo.

Cada caso corre tb/tb_estres.sv con Verilator (se compila una vez por variante)
y exige: todos los bytes que lee la maestra iguales a los de ref/trader.py, MISO
sin X, ningún precio sin leer ni sin respuesta, y peor caso dentro del
presupuesto. Los precios que llegan antes de que termine el reset de encendido
se modelan como perdidos, igual que en ref/trader.py.

Uso, desde la raíz:
    python3 tools/estres.py                       # todo, core base
    python3 tools/estres.py --solo fases
    DEFS=-DESPINO_SEGMENTADO python3 tools/estres.py --etiqueta seg

El fondo en un chip (sw/fondo.s sobre el barrel, docs/fondo.md) usa la misma
matriz con su referencia, ref/fondo.py, y con dos motores: el RTL (tb_estres.sv
con Verilator) y el gemelo digital (build/gemelo --barrel, validado ciclo a
ciclo contra el RTL en make cosim-barrel):
    DEFS="-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA" python3 tools/estres.py \
        --ref fondo --hex build/fondo/fondo.hex --etiqueta fondo --solo estres
    python3 tools/estres.py --ref fondo --motor gemelo --gemelo-opts "--barrel --xd 3 --tabla sw/fondo_tabla.hex" \
        --hex build/fondo/fondo.hex --etiqueta fondo_gemelo --solo estres
Con el gemelo no hay valores X que mirar: esa columna queda en 0. Los dos casos
de período cercano al mínimo se eligen según el programa (--periodos-minimos):
con un presupuesto de 50 ciclos el fondo no alcanza a responder.
"""
import argparse
import multiprocessing
import os
import random
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
import fondo     # noqa: E402
import market    # noqa: E402
import series    # noqa: E402
import trader    # noqa: E402

CLK_NS = 40
FIN_RESET_NS = ((1 << 12) - 1) * CLK_NS + 20 + 3 * CLK_NS    # el mismo de trader.ticks_perdidos
PRESUPUESTO_R3 = (100000 - 9500) // CLK_NS                    # 2262


def compilar(d, hexfile, defs):
    os.makedirs(d, exist_ok=True)
    cells = subprocess.check_output(["yosys-config", "--datdir"], text=True).strip() + "/ice40/cells_sim.v"
    src = sorted(f"rtl/{f}" for f in os.listdir("rtl") if f.endswith(".v")) + \
        sorted(f"rtl/espino_core/{f}" for f in os.listdir("rtl/espino_core") if f.endswith(".v"))
    cmd = ["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style",
           "--top-module", "tb_estres", "-DNO_ICE40_DEFAULT_ASSIGNMENTS", *defs.split(),
           f'-GPROGRAMA="{hexfile}"', "-O3", "--Mdir", f"{d}/obj", "-o", "sim",
           cells, *src, "tb/tb_estres.sv"]
    with open(f"{d}/verilator.log", "w") as log:
        subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT)
    return f"{d}/obj/sim"


def perdidos(caso):
    """Precios cuyo primer flanco de SCLK llega antes de que termine el reset."""
    t, n = caso["INICIO_NS"], 0
    while n < caso["NTICKS"] and t + caso["CS_SETUP_NS"] < FIN_RESET_NS:
        t += caso["PERIODO_NS"]
        n += 1
    return n


# plusarg de tb_estres.sv -> opción del gemelo
OPCION_GEMELO = {"PERIODO_NS": "--periodo-ns", "PERIODO2_NS": "--periodo2-ns", "PERIODO3_NS": "--periodo3-ns",
                 "RONDA_TICKS": "--ronda-ticks", "PAUSA_NS": "--pausa-ns", "INICIO_NS": "--inicio-ns",
                 "SCLK_MEDIO_NS": "--sclk-medio-ns", "CS_SETUP_NS": "--cs-sclk-ns", "CS_HOLD_NS": "--cs-hold-ns"}


def correr_gemelo(d, caso, hexfile, opciones):
    """El caso en el gemelo. Devuelve el RESUMEN de tb_estres.sv y los bytes leídos."""
    nombre = caso["nombre"]
    lote = f"{d}/{nombre}.lote"
    with open(lote, "w") as f:
        f.write(" ".join(map(str, caso["precios"])) + "\n")
    args = ["build/gemelo", *opciones.split(), "--hex", hexfile, "--lote", lote, "--bytes"]
    for k, v in caso.items():
        if k in OPCION_GEMELO:
            args += [OPCION_GEMELO[k], str(v)]
    out = subprocess.run(args, capture_output=True, text=True)
    campos = out.stdout.split()
    if out.returncode != 0 or len(campos) != 9:
        return None, None
    _, _, _, peor, respuestas, sin_leer, _, suma, hexbytes = campos
    per = [caso["PERIODO_NS"], caso.get("PERIODO2_NS", caso["PERIODO_NS"])]
    per.append(caso.get("PERIODO3_NS", per[1]))
    rondas = 1 if not caso.get("RONDA_TICKS") else min(3, -(-caso["NTICKS"] // caso["RONDA_TICKS"]))
    dur = caso["CS_SETUP_NS"] + 15 * caso["SCLK_MEDIO_NS"] + caso["CS_HOLD_NS"]
    r = dict(bits_x=0, precios_perdidos=int(sin_leer), respuestas=int(respuestas), peor_caso=int(peor),
             presupuesto=min((p - dur) // CLK_NS for p in per[:rondas]))
    r["sin_respuesta"] = 0
    r["suma_ciclos"] = int(suma)
    return r, list(bytes.fromhex(hexbytes))


def correr(arg):
    sim, d, caso, ref, motor = arg
    nombre = caso["nombre"]
    explora = caso.get("explora", False)
    if motor[0] == "gemelo":
        r, leidos = correr_gemelo(d, caso, motor[1], motor[2])
        if r is None:
            return nombre, False, "el gemelo no corrio", 0, explora
    else:
        csv = f"{d}/{nombre}.csv"
        series.escribir_csv(csv, caso["precios"])
        args = [sim, f"+SERIE={csv}", f"+SALIDA={d}/{nombre}.out.csv"] + \
            [f"+{k}={v}" for k, v in caso.items() if k.isupper()]
        out = subprocess.run(args, capture_output=True, text=True).stdout
        linea = [l for l in out.splitlines() if l.startswith("RESUMEN")]
        if not linea:
            return nombre, False, "sin RESUMEN: " + out[-300:], 0, explora
        r = dict(kv.split("=") for kv in linea[0].split()[1:])
        r = {k: int(v) for k, v in r.items()}
        leidos = [int(l.split(",")[2], 16) for l in open(f"{d}/{nombre}.out.csv").read().split("\n")[1:] if l]
    perd = perdidos(caso)
    estrategia = fondo.Fondo() if ref == "fondo" else trader.Oficial()
    esperado = trader.decisiones(caso["precios"], estrategia, perd)
    distintos = sum(a != b for a, b in zip(leidos, esperado)) + abs(len(leidos) - len(esperado))
    ok = (distintos == 0 and r["bits_x"] == 0 and r["precios_perdidos"] == 0 and r["sin_respuesta"] == 0
          and r["respuestas"] == caso["NTICKS"] - perd and r["peor_caso"] < r["presupuesto"])
    prom = r["suma_ciclos"] / max(r["respuestas"], 1)
    det = (f"perdidos en reset {perd}, respuestas {r['respuestas']}, bytes distintos {distintos}, "
           f"X {r['bits_x']}, sin leer {r['precios_perdidos']}, sin respuesta {r['sin_respuesta']}, "
           f"ciclos prom {prom:.1f} peor {r['peor_caso']} de {r['presupuesto']}")
    return nombre, ok, det, r["peor_caso"], explora


def base(nombre, precios, **kw):
    c = dict(nombre=nombre, precios=precios, NTICKS=len(precios), PERIODO_NS=100000, INICIO_NS=4000,
             SCLK_MEDIO_NS=500, CS_SETUP_NS=1500, CS_HOLD_NS=500)
    c.update(kw)
    return c


def casos_fases(practica):
    p = practica[:2000]
    c = [base(f"fase_{i}", p, INICIO_NS=4000 + 40 * i) for i in range(8)]
    c += [base(f"fase_{i}_mas13ns", p, INICIO_NS=4013 + 40 * i) for i in range(8)]
    c.append(base("fase_todas_periodo_2501_ciclos", p, PERIODO_NS=100040))
    return c


def casos_estres(practica, minimos=(11500, 13500)):
    p = practica[:2000]
    rng = random.Random(7)
    c = []
    # SCLK: de 100 kHz a 1 MHz es lo pedido; 2, 4 y 5 MHz son exploración. A 5 MHz
    # el medio período (100 ns) es menor que la latencia de MISO: SCLK pasa por
    # dos flip-flops de sincronización y el registro de desplazamiento cambia un
    # ciclo después, unos 120 ns tras el flanco de bajada.
    for medio, et in ((5000, "100k"), (2500, "200k"), (1000, "500k"), (500, "1M"),
                      (250, "2M"), (125, "4M"), (100, "5M")):
        c.append(base(f"sclk_{et}", p, SCLK_MEDIO_NS=medio, CS_SETUP_NS=max(1500, 3 * medio),
                      explora=medio < 500))
    # CS_n: setup (bajada de CS a primer flanco) y hold (último flanco a subida de CS)
    for setup in (500, 600, 1000, 5000, 20000):
        for hold in (40, 100, 500, 5000):
            c.append(base(f"cs_setup{setup}_hold{hold}", p[:1000], CS_SETUP_NS=setup, CS_HOLD_NS=hold))
    # Reset terminando a mitad de una transacción: el primer flanco cae j us antes
    # del fin del reset (0 a 8 flancos alcanzan a llegar), y transacciones desde t = 0
    for j in range(0, 9):
        inicio = FIN_RESET_NS - 1500 - j * 1000 + 300
        c.append(base(f"reset_flanco_{j}", p[:500], INICIO_NS=inicio))
    for inicio in (0, 1, 20, 100000, 163000, FIN_RESET_NS - 1500, FIN_RESET_NS - 1499, FIN_RESET_NS - 1460):
        c.append(base(f"reset_inicio_{inicio}", p[:500], INICIO_NS=inicio))
    # Series pegadas y en los bordes
    c.append(base("pegada_1", [1] * 1000))
    c.append(base("pegada_255", [255] * 1000))
    c.append(base("alterna_1_255", [1, 255] * 500))
    c.append(base("pegada_1_luego_255", [1] * 500 + [255] * 500))
    c.append(base("al_azar_1_255", [rng.randint(1, 255) for _ in range(2000)]))
    for fam in ("plana", "borde_bajo", "borde_alto", "saltos", "tendencia", "paseo"):
        c.append(base(f"familia_{fam}", series.lote(fam, 1, 2000, semilla=11)[0]))
    # Rondas seguidas sin reset de la placa: tres series distintas, pausa entre
    # rondas, y el período de cada ronda distinto (10 ms, 1 ms, 0,1 ms y al revés)
    r1, r2, r3 = practica[2000:2200], practica[6000:6200], practica[12000:12200]
    c.append(base("rondas_10ms_1ms_01ms", r1 + r2 + r3, RONDA_TICKS=200, PAUSA_NS=5000000,
                  PERIODO_NS=10000000, PERIODO2_NS=1000000, PERIODO3_NS=100000))
    c.append(base("rondas_01ms_1ms_10ms", r3 + r2 + r1, RONDA_TICKS=200, PAUSA_NS=5000000,
                  PERIODO_NS=100000, PERIODO2_NS=1000000, PERIODO3_NS=10000000))
    c.append(base("rondas_3x2000_01ms", practica[:6000], RONDA_TICKS=2000, PAUSA_NS=20000000))
    # Período cercano al mínimo: con sw/trade.hex, presupuesto de 50 y de 100
    # ciclos. Para otro programa se eligen con --periodos-minimos.
    for per in minimos:
        c.append(base(f"periodo_{per}ns", p, PERIODO_NS=per))
    return c


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", choices=("fases", "estres"))
    ap.add_argument("--etiqueta", default="base")
    ap.add_argument("--hex", default="sw/trade.hex")
    ap.add_argument("--ref", choices=("trader", "fondo"), default="trader",
                    help="referencia: ref/trader.py (max_media) o ref/fondo.py")
    ap.add_argument("--motor", choices=("rtl", "gemelo"), default="rtl")
    ap.add_argument("--gemelo-opts", default="", help="opciones del gemelo para el hardware (p. ej. --barrel --xd 3)")
    ap.add_argument("--periodos-minimos", default="11500,13500",
                    help="periodos en ns de los casos cercanos al minimo")
    ap.add_argument("--presupuesto-minimo", type=int, default=0,
                    help="ciclos entre transacciones bajo los cuales un caso es exploracion y no cuenta "
                         "(600 para el fondo, como tools/fondo/estres.py; 0 para R0)")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    defs = os.environ.get("DEFS", "")
    d = f"build/estres/{a.etiqueta}"
    os.makedirs(d, exist_ok=True)
    if a.motor == "gemelo":
        r = subprocess.run(["cc", "-O2", "-o", "build/gemelo", "ref/gemelo/gemelo.c"])
        if r.returncode != 0:
            raise SystemExit("el gemelo no compila")
        sim, motor, defs = None, ("gemelo", a.hex, a.gemelo_opts), f"gemelo {a.gemelo_opts}".strip()
    else:
        sim, motor = compilar(d, a.hex, defs), ("rtl",)
    minimos = tuple(int(x) for x in a.periodos_minimos.split(","))
    practica = market.leer_serie("tb/practica.csv")
    grupos = []
    if a.solo in (None, "fases"):
        grupos.append(("fases", casos_fases(practica)))
    if a.solo in (None, "estres"):
        ce = casos_estres(practica, minimos)
        for caso in ce:
            dur = caso["CS_SETUP_NS"] + 15 * caso["SCLK_MEDIO_NS"] + caso["CS_HOLD_NS"]
            per = min(caso.get(k, caso["PERIODO_NS"]) for k in ("PERIODO_NS", "PERIODO2_NS", "PERIODO3_NS"))
            if (per - dur) // CLK_NS < a.presupuesto_minimo:
                caso["explora"] = True
        grupos.append(("estres", ce))
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    extra = f", referencia ref/{a.ref}.py, motor {a.motor}" if (a.ref, a.motor) != ("trader", "rtl") else ""
    print(f"Variante {a.etiqueta} (DEFS='{defs}'), programa {a.hex}, commit {commit}{extra}")
    fallas = 0
    with multiprocessing.Pool(min(16, os.cpu_count())) as pool:
        for nombre_g, casos in grupos:
            res = pool.map(correr, [(sim, d, c, a.ref, motor) for c in casos])
            print(f"\n== {nombre_g}: {len(casos)} casos")
            for nombre, ok, det, _, explora in res:
                if explora:
                    print(f"{'pasa' if ok else 'no pasa'} (exploracion, fuera del rango pedido) {nombre}: {det}")
                else:
                    print(f"{'PASS' if ok else 'FAIL'} {nombre}: {det}")
                    fallas += not ok
            if nombre_g == "fases":
                peor = max(r[3] for r in res)
                ok = peor < PRESUPUESTO_R3 // 2
                fallas += not ok
                print(f"{'PASS' if ok else 'FAIL'} peor caso en todas las fases: {peor} ciclos, "
                      f"limite con 50 % de holgura {PRESUPUESTO_R3 // 2} (presupuesto ronda 3: {PRESUPUESTO_R3})")
    print(f"\n{'PASS' if fallas == 0 else 'FAIL'}: {fallas} casos fallidos")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
