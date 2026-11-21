#!/usr/bin/env python3
"""caso.py: corre sw/c1.s en el RTL (tb/c1/tb_c1.sv con Verilator) y lo compara con ref/c1/c1.py.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Un caso es una serie, un período y un programa. Comprueba:

  1. Bytes: cada byte que leyó la maestra es el de la referencia entera.
  2. Estado tick a tick (salvo --sin-estado): el byte escrito, el byte de la política, el modo,
     D, el patrimonio propio emulado, las dos cuentas (caja y acciones), el objetivo de la media
     posición, la clase de v^2, las sumas y el reloj de tramos del hilo 1, la posición del motor y
     el LED de modo seguro.
  3. Conteos del testbench: llegaron todos los precios, una sola escritura en DECISION por tick,
     MISO sin X, ninguna violación del protocolo, el vigilante sin disparar, y el peor caso de
     la respuesta bajo el límite.

Imprime una línea PASS o FAIL. Con --medir agrega instrucciones por hilo y los hitos del tick.

Uso, desde la raíz (el simulador se compila con tools/c1/comun.sh, función compilar_sim):
  python3 tools/c1/caso.py CARPETA --serie S.csv --nticks N [--periodo-ns P] [--inicio-ns I]
        [--asm sw/c1.s] [--tabla sw/c1_tabla.hex] [--sim build/c1/r3/obj/sim] [--faltas a-b,c]
        [--tardias a,b] [--limite CICLOS] [--plus "+X=1 ..."] [--medir] [--sin-estado]

Con fallas (tools/c1/variante.py): --faltas son los ticks en que la política no llega nunca (un hilo
colgado) y --tardias los ticks en que llega después del plazo. Desde la primera falta el estado de
los hilos 1 a 3 queda congelado y no se compara; el byte, la escritura única en DECISION y el LED
de modo seguro se comparan siempre.
"""
import argparse
import csv
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, os.path.join(RAIZ, "ref", "c1"))
sys.path.insert(0, os.path.join(RAIZ, "tools", "fondo"))

import fondo              # noqa: E402
import c1 as R            # noqa: E402
import tablas as TB       # noqa: E402
import market             # noqa: E402
import trader             # noqa: E402
import simbolos           # noqa: E402

LAZO = {0: ("h0_espera", 3), 1: ("h1_espera", 2), 2: ("h2_espera", 2), 3: ("h3_espera", 2)}
LIMITE_PUERTA = 1131      # la mitad del presupuesto de la ronda 3


def ensamblar(asm, hexa):
    e, palabras = simbolos.ensamblar(asm)
    os.makedirs(os.path.dirname(hexa), exist_ok=True)
    with open(hexa, "w") as f:
        f.write("".join(f"{w:08x}\n" for w in palabras))
    return e.simbolos


def plusargs(sim_b):
    a = [f"+A_ESPERA{h}={sim_b[n]}" for h, (n, _) in LAZO.items()]
    a += [f"+L_ESPERA{h}={4 * l}" for h, (_, l) in LAZO.items()]
    a += [f"+A_PUB={sim_b['D_PUB']}", f"+A_REG={sim_b['D_REG']}", f"+A_TAB={sim_b['D_TAB']}", f"+A_POL={sim_b['D_POL']}",
          f"+A_DATOS={sim_b['D_PUB']}"]
    return a


def leer_resumen(ruta):
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            if linea.startswith("RESUMEN"):
                return {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", linea)}
    return None


def faltas_de(texto):
    out = set()
    for parte in (texto or "").split(","):
        if not parte:
            continue
        if "-" in parte:
            a, b = parte.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(parte))
    return out


def referencia(precios, perdidos, T, faltas=(), programa=None, tardias=()):
    """Bytes que lee la maestra y el estado de la referencia después de cada precio recibido."""
    c = R.C1(T, faltas, programa, tardias)
    salida, estados = [], []
    actual = 0
    for n, p in enumerate(precios):
        salida.append(actual)
        if n >= perdidos:
            actual = c.paso(p)
            estados.append(dict(k=c.k, p=p, byte=actual, pol=c.pol_ultimo, modo=c.modo, D=c.D, W=c.W, caja=c.caja,
                                acc=c.acc, cajac=c.cajac, accc=c.accc, obj=c.obj, cv=c.cv, sm=c.sm, seguro=c.seguro,
                                activa=1 if c.k >= c.t_min else 0, tr_a=c.tr_a, c_a=c.c_a, tr_m=c.tr_m, c_m=c.c_m,
                                B=list(c.B)))
    return salida, estados, c


def s32(x):
    return x - (1 << 32) if x & 0x80000000 else x


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("carpeta")
    ap.add_argument("--etiqueta")
    ap.add_argument("--serie", default="data/practica_meta.csv")
    ap.add_argument("--nticks", type=int, required=True)
    ap.add_argument("--periodo-ns", type=int, default=100000)
    ap.add_argument("--inicio-ns", type=int, default=4000)
    ap.add_argument("--asm", default="sw/c1.s")
    ap.add_argument("--tabla", default="sw/c1_tabla.hex")
    ap.add_argument("--tabla-ref", help="tabla de la referencia, si no es la del simulador (controles negativos)")
    ap.add_argument("--sim", default="build/c1/r3/obj/sim")
    ap.add_argument("--faltas", help="ticks en que la política no llega nunca (a-b,c): los decide la degradación")
    ap.add_argument("--tardias", help="ticks en que la política llega después del plazo (a,b)")
    ap.add_argument("--congelado-desde", type=int, metavar="K",
                    help="desde el precio K no se compara el estado de los hilos 1 a 3 (un hilo colgado que ya no hace falta)")
    ap.add_argument("--banda40-desde", type=int, metavar="K",
                    help="exige además que desde el precio K (contado desde 1) los bytes sean los de la banda 40 de ref/fondo.py")
    ap.add_argument("--programa", action="append", default=[], help="parámetro del programa para la referencia: nombre=valor")
    ap.add_argument("--limite", type=int, default=LIMITE_PUERTA)
    ap.add_argument("--plus", default="")
    ap.add_argument("--vig-esperado", type=int, default=0)
    ap.add_argument("--medir", action="store_true")
    ap.add_argument("--sin-estado", action="store_true")
    ap.add_argument("--sin-correr", action="store_true", help="solo revisa una corrida ya hecha")
    a = ap.parse_args(argv)

    d = a.carpeta
    os.makedirs(d, exist_ok=True)
    etiqueta = a.etiqueta or os.path.basename(d.rstrip("/"))
    sb = ensamblar(a.asm, os.path.join(d, "programa.hex"))
    if not a.sin_correr:
        cmd = [a.sim, f"+PROGRAMA={d}/programa.hex", f"+TABLA={a.tabla}", f"+SERIE={a.serie}", f"+NTICKS={a.nticks}",
               f"+PERIODO_NS={a.periodo_ns}", f"+INICIO_NS={a.inicio_ns}", f"+SALIDA={d}/salida.csv",
               f"+ESTADO={d}/estado.csv"] + plusargs(sb) + a.plus.split()
        with open(os.path.join(d, "tb.log"), "w") as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=RAIZ)

    errores = []
    precios = market.leer_serie(a.serie, a.nticks)
    perdidos = trader.ticks_perdidos(a.periodo_ns, inicio_ns=a.inicio_ns)
    T = TB.leer_hex(a.tabla_ref or a.tabla)
    programa = {t.split("=")[0]: int(t.split("=")[1], 0) for t in a.programa}
    faltas = faltas_de(a.faltas)
    congelado = a.congelado_desde or (min(faltas) if faltas else None)   # desde ese tick los hilos 1 a 3 no publican
    salida, estados, c = referencia(precios, perdidos, T, faltas, programa, faltas_de(a.tardias))

    # 1. Bytes
    with open(os.path.join(d, "salida.csv"), encoding="utf-8") as fd:
        tb = list(csv.reader(fd))[1:]
    if len(tb) != len(salida):
        errores.append(f"la maestra leyó {len(tb)} bytes y se esperaban {len(salida)}")
    difs = [n for n, (x, y) in enumerate(zip(tb, salida)) if int(x[2], 16) != y]
    if difs:
        errores.append(f"{len(difs)} bytes distintos a la referencia, el primero en el tick {difs[0]}")

    if a.banda40_desde:
        b40 = trader.decisiones(precios, fondo.Fondo(), perdidos)
        desde = perdidos + a.banda40_desde          # el byte del precio K lo lee la maestra en el tick siguiente
        malos = [n for n in range(desde, min(len(tb), len(b40))) if int(tb[n][2], 16) != b40[n]]
        if malos:
            errores.append(f"{len(malos)} bytes distintos a la banda 40 desde el precio {a.banda40_desde}, el primero en el tick {malos[0]}")
        if not c.seguro and c.modo != R.MODO_COPIA:
            errores.append("la referencia no termina en modo seguro ni en el candado")

    # 2. Estado
    est = []
    with open(os.path.join(d, "estado.csv"), encoding="utf-8") as fd:
        filas = list(csv.reader(fd))
    cab, filas = filas[0], filas[1:]
    nfijos = cab.index("datos...")
    base = sb["D_PUB"]

    def dato(fila, nombre):
        return int(fila[nfijos + (sb[nombre] - base) // 4], 16)

    n_estado = 0
    if not a.sin_estado:
        if len(filas) != len(estados):
            errores.append(f"el testbench vio {len(filas)} precios y la referencia {len(estados)}")
        malos = {}
        for fila, e in zip(filas, estados):
            def revisar(campo, obtenido, esperado):
                if obtenido != esperado and campo not in malos:
                    malos[campo] = f"{campo} en el tick {e['k']}: {obtenido} y se esperaba {esperado}"
            revisar("precio", int(fila[1]), e["p"])
            revisar("byte", int(fila[4], 16), e["byte"])
            revisar("escrituras en DECISION", int(fila[5]), 1)
            revisar("LED de modo seguro", int(fila[cab.index("leds")]), e["seguro"])
            if congelado is None or e["k"] < congelado:      # los hilos 1 a 3 publicaron en este tick
                revisar("byte de la política", dato(fila, "D_POL"), (e["k"] << 8) | e["pol"])
                revisar("modo", dato(fila, "D_MODO"), e["modo"])
                revisar("D", s32(dato(fila, "D_DIF")), e["D"])
                revisar("patrimonio emulado", dato(fila, "D_W") & 0xFFFFFF, e["W"] & 0xFFFFFF)
                revisar("caja", s32(dato(fila, "D_CAJA")), e["caja"])
                revisar("acciones", dato(fila, "D_ACC"), e["acc"])
                revisar("caja del clon", s32(dato(fila, "D_CAJAC")), e["cajac"])
                revisar("acciones del clon", dato(fila, "D_ACCC"), e["accc"])
                revisar("objetivo", dato(fila, "D_OBJ"), e["obj"])
                if e["activa"]:
                    revisar("clase", dato(fila, "D_CVA"), 64 * e["cv"])
                # el reloj del hilo 1, ya avanzado para el tick siguiente, y sus siete sumas
                revisar("tramo de la fase A", dato(fila, "D_TRA"), 4 * e["tr_a"])
                revisar("cuenta del tramo de la fase A", dato(fila, "D_CA"), e["c_a"])
                revisar("tramo del motor", dato(fila, "D_TRM"), 4 * e["tr_m"])
                revisar("cuenta del tramo del motor", dato(fila, "D_CM"), e["c_m"])
                revisar("sumas N_j (t - 1)", [int(fila[nfijos + (sb["D_B"] - base) // 4 + j], 16) for j in range(7)], e["B"])
                if e["modo"] != R.MODO_COPIA:
                    revisar("posición del motor", (dato(fila, "D_TAB") >> 2) & 1, e["sm"])
            n_estado += 1
        errores += list(malos.values())

    # 3. Conteos
    r = leer_resumen(os.path.join(d, "tb.log"))
    if r is None:
        errores.append("el testbench no terminó")
        r = {}
    else:
        vistos = a.nticks - perdidos
        for campo, esperado in (("recibidos", vistos), ("respuestas", vistos), ("sin_respuesta", 0), ("precios_perdidos", 0),
                                ("bits_x", 0), ("violaciones", 0), ("dec_distinto_de_1", 0), ("tel_mas_de_1", 0),
                                ("vig_boot", a.vig_esperado)):
            if r.get(campo) != esperado:
                errores.append(f"{campo} = {r.get(campo)} y se esperaba {esperado}")
        if r["vig_max"] > 1 and not a.vig_esperado:
            errores.append(f"el vigilante llegó a contar {r['vig_max']} precios sin respuesta")
        if r["peor_caso"] >= a.limite:
            errores.append(f"peor caso {r['peor_caso']} ciclos, no menor que {a.limite}")

    W, nord = R.patrimonio(precios, salida[1:] + [0], c.caja0, c.com) if precios else (0, 0)
    estado = "FAIL" if errores else "PASS"
    print(f"{estado} {etiqueta}: {len(tb)} bytes, {n_estado} ticks de estado, patrimonio {W}, {nord} órdenes, modo final "
          f"{c.modo}, seguro {c.seguro}, plazo vencido en {c.vencidos} ticks, peor caso {r.get('peor_caso', '?')} de {a.limite} ciclos"
          + (f", banda 40 desde el precio {a.banda40_desde}" if a.banda40_desde and not errores else "")
          + ("" if not errores else ". " + "; ".join(errores)))
    if a.medir and filas:
        medir(cab, filas[1:-1], a.periodo_ns)
    return 1 if errores else 0


def medir(cab, filas, periodo_ns):
    def col(nombre):
        i = cab.index(nombre)
        return [int(f[i]) for f in filas]

    def est(v):
        v = [x for x in v if x >= 0]
        return (min(v), sum(v) / len(v), max(v)) if v else (0, 0.0, 0)

    print()
    print(f"  Ticks medidos: {len(filas)}. Ciclo de 40 ns. Trabajo: instrucciones fuera del lazo de espera del hilo.")
    print(f"    {'hilo':10s} {'mínimo':>7s} {'promedio':>9s} {'máximo':>7s} {'ciclos prom.':>13s} {'ciclos máx.':>12s} {'CPI':>6s}")
    for h in range(4):
        ic, son = col(f"ic{h}"), col(f"son{h}")
        lo, pr, hi = est([i - s for i, s in zip(ic, son)])
        print(f"    {h:<10d} {lo:7d} {pr:9.2f} {hi:7d} {4 * pr:13.2f} {4 * hi:12d} {4.0:6.3f}")
    print()
    print("  Ciclos desde que llega el precio (byte_done)")
    print(f"    {'hito':40s} {'mínimo':>7s} {'promedio':>9s} {'máximo':>7s} {'tiempo máx.':>12s}")
    for nombre, campo in (("el hilo 0 publica el precio (D_PUB)", "c_pub"), ("el hilo 1 publica la clase (D_REG)", "c_reg"),
                          ("el hilo 2 publica las posiciones (D_TAB)", "c_tab"), ("el hilo 3 publica la política (D_POL)", "c_pol"),
                          ("DECISION (respuesta)", "respuesta"), ("el hilo 0 vuelve a sondear", "c_fin")):
        lo, pr, hi = est(col(campo))
        print(f"    {nombre:40s} {lo:7d} {pr:9.2f} {hi:7d} {hi * 0.04:9.2f} us")
    peor = max(col("respuesta"))
    print()
    for nombre, per in (("1 (10 ms)", 10000000), ("2 (1 ms)", 1000000), ("3 (0,1 ms)", 100000)):
        pres = (per - 9500) // 40
        print(f"    ronda {nombre:11s} presupuesto {pres:7d} ciclos, uso {100.0 * peor / pres:7.3f} %, holgura {100.0 * (pres - peor) / pres:6.2f} %")


if __name__ == "__main__":
    sys.exit(main())
