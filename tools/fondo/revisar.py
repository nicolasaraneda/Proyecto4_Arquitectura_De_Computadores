#!/usr/bin/env python3
"""
revisar.py: compara una corrida de tb/fondo/tb_fondo.sv con ref/fondo.py.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Recibe la carpeta de una corrida (salida.csv, estado.csv y tb.log) y la
descripción del caso, y comprueba:

  1. Bytes: cada byte que leyó la maestra es el de la referencia.
  2. Estado en el momento de decidir, tick a tick: byte escrito, palabra PUB,
     pesos, y de cada gestor cuyo voto llega, el voto y el puntaje. Que el
     supervisor decidió por plazo vencido exactamente en los ticks en que la
     referencia dice que faltó algún voto.
  3. Telemetría: a lo más un store al periférico por tick, y los LED y los
     7 segmentos valen lo que corresponde al cerrar cada tick.
  4. Conteos del testbench: llegaron todos los precios, cada uno tuvo una sola
     escritura en DECISION, MISO sin X, ninguna violación del protocolo y peor
     caso bajo el límite.

Imprime una línea PASS o FAIL con los números del caso. Con --medir agrega las
tablas de instrucciones y ciclos por tick.
"""

import argparse
import csv
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))

import fondo as ref_fondo  # noqa: E402
import market  # noqa: E402
import trader  # noqa: E402

SEG_00 = (64, 64)        # los 7 segmentos son activos en bajo
SEG_63 = (2, 48)
LAZO = {0: 3, 1: 2, 2: 2, 3: 2}      # instrucciones de una vuelta del lazo de sondeo


def leer_resumen(ruta):
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            if linea.startswith("RESUMEN"):
                return {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", linea)}
    return None


def estadistica(valores):
    return min(valores), sum(valores) / len(valores), max(valores)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compara una corrida del fondo con su referencia")
    ap.add_argument("carpeta")
    ap.add_argument("--etiqueta", default=None)
    ap.add_argument("--serie", default="tb/practica.csv")
    ap.add_argument("--nticks", type=int, required=True)
    ap.add_argument("--periodo-ns", type=int, default=100000)
    ap.add_argument("--inicio-ns", type=int, default=4000)
    ap.add_argument("--falla", action="append", default=[])
    ap.add_argument("--param", action="append", default=[])
    ap.add_argument("--limite", type=int, default=None,
                    help="peor caso admitido en ciclos (por defecto el presupuesto del testbench)")
    ap.add_argument("--solo-max-media", action="store_true",
                    help="exige además que los bytes sean los de ref/trader.py (max_media sola)")
    ap.add_argument("--sin-estado", action="store_true", help="no comparar el estado interno")
    ap.add_argument("--medir", action="store_true", help="tablas de instrucciones y ciclos por tick")
    a = ap.parse_args(argv)

    etiqueta = a.etiqueta or os.path.basename(a.carpeta.rstrip("/"))
    errores = []
    precios = market.leer_serie(a.serie, a.nticks)
    perdidos = trader.ticks_perdidos(a.periodo_ns, inicio_ns=a.inicio_ns)
    parametros = {t.split("=")[0]: int(t.split("=")[1], 0) for t in a.param}
    fallas = [ref_fondo.Falla.leer(t) for t in a.falla]
    filas, traza = [], []
    m, f = ref_fondo.correr(precios, perdidos, parametros, fallas, filas, traza)

    # 1. Bytes
    with open(os.path.join(a.carpeta, "salida.csv"), encoding="utf-8") as fd:
        tb = list(csv.reader(fd))[1:]
    if len(tb) != len(filas):
        errores.append(f"la maestra leyo {len(tb)} bytes y se esperaban {len(filas)}")
    difs = [n for n, (x, y) in enumerate(zip(tb, filas)) if int(x[2], 16) != y[2] or int(x[1]) != y[1]]
    if difs:
        errores.append(f"{len(difs)} bytes distintos a la referencia, el primero en el tick {difs[0]}")
    if a.solo_max_media:
        solo = trader.decisiones(precios, trader.MaxMedia(), perdidos)   # el supervisor del fondo que vota
        if [int(x[2], 16) for x in tb] != solo:
            errores.append("los bytes no son los de max_media sola")

    # 2 y 3. Estado y telemetría
    est = []
    ruta_estado = os.path.join(a.carpeta, "estado.csv")
    if os.path.exists(ruta_estado):
        with open(ruta_estado, encoding="utf-8") as fd:
            est = list(csv.DictReader(fd))
    n_estado = 0
    if est and not a.sin_estado:
        if len(est) != len(traza):
            errores.append(f"el testbench vio {len(est)} precios y la referencia {len(traza)}")
        seg, leds = SEG_00, 0
        malos = {}
        for fila, t in zip(est, traza):
            (tick, p, byte, pos0, v1, v2, v3, l1, l2, l3, w1, w2, w3, d1, d2, d3) = t[:16]
            votos, llego, des = (v1, v2, v3), (l1, l2, l3), (d1, d2, d3)

            def revisar(campo, obtenido, esperado):
                if obtenido != esperado and campo not in malos:
                    malos[campo] = f"{campo} en el tick {tick}: {obtenido} y se esperaba {esperado}"

            revisar("precio", int(fila["precio"]), p)
            revisar("byte", int(fila["byte"], 16), byte)
            revisar("escrituras en DECISION", int(fila["n_dec"]), 1)
            revisar("PUB", int(fila["pub"]), tick * 256 + p)
            revisar("escrituras en PUB", int(fila["n_pub"]), 1)
            revisar("pesos", (int(fila["w1"]), int(fila["w2"]), int(fila["w3"])), (w1, w2, w3))
            revisar("plazo vencido", int(fila["plazo"]), 0 if all(llego) else 1)
            for k in range(3):
                if llego[k]:
                    revisar(f"voto {k + 1}", int(fila[f"est{k + 1}"]), tick * 256 + votos[k])
                    revisar(f"puntaje {k + 1}", int(fila[f"des{k + 1}"]), des[k])
            if int(fila["n_tel"]) > 1:
                revisar("stores de telemetria", int(fila["n_tel"]), 1)
            if tick % 2 == 0:
                seg = SEG_63 if byte == market.COMPRAR_63 else SEG_00
            else:
                pesos = (w1, w2, w3)
                leds = ((tick >> 10) & 1) | sum((1 << (k + 1)) for k in range(3) if votos[k] and pesos[k])
            revisar("7 segmentos", (int(fila["seg1"]), int(fila["seg2"])), seg)
            revisar("LED", int(fila["leds"]), leds)
            n_estado += 1
        errores += list(malos.values())

    # 4. Conteos del testbench
    r = leer_resumen(os.path.join(a.carpeta, "tb.log"))
    limite = a.limite
    if r is None:
        errores.append("el testbench no termino")
        r = {}
    else:
        if limite is None:
            limite = r["presupuesto"]
        vistos = a.nticks - perdidos
        for campo, esperado in (("recibidos", vistos), ("respuestas", vistos), ("sin_respuesta", 0),
                                ("precios_perdidos", 0), ("bits_x", 0), ("violaciones", 0),
                                ("dec_distinto_de_1", 0), ("tel_mas_de_1", 0), ("ticks_plazo", f.degradados),
                                ("vig_boot", 0)):
            if r[campo] != esperado:
                errores.append(f"{campo} = {r[campo]} y se esperaba {esperado}")
        if r["vig_max"] > 1:
            errores.append(f"el vigilante llego a contar {r['vig_max']} precios sin respuesta")
        if r["peor_caso"] >= limite:
            errores.append(f"peor caso {r['peor_caso']} ciclos, no menor que {limite}")

    extra = ""
    if fallas:
        ref_bytes = [y[2] for y in filas]
        sano = trader.decisiones(precios, ref_fondo.Fondo(parametros), perdidos)
        solo = trader.decisiones(precios, trader.MaxMedia(), perdidos)   # el supervisor del fondo que vota
        extra = (f", bytes esperados distintos a los del fondo sano {sum(x != y for x, y in zip(ref_bytes, sano))}"
                 f" y a los de max_media sola {sum(x != y for x, y in zip(ref_bytes, solo))}")

    estado = "FAIL" if errores else "PASS"
    print(f"{estado} {etiqueta}: {len(tb)} bytes, {n_estado} ticks de estado, patrimonio {m.w}, {m.ordenes} ordenes, "
          f"pesos {f.w[0]}/{f.w[1]}/{f.w[2]} ({f.cambios} cambios), {f.degradados} ticks por plazo, "
          f"peor caso {r.get('peor_caso', '?')} de {limite} ciclos, hasta {r.get('max_vueltas', '?')} vueltas de lectura{extra}"
          + ("" if not errores else ". " + "; ".join(errores)))

    if a.medir and est:
        medir(est, a.periodo_ns)
    return 1 if errores else 0


def medir(est, periodo_ns):
    """Tablas del punto 3.2 del enunciado: IC, ciclos, CPI y tiempo por tick."""
    est = est[1:-1]          # el primer tick inicia las medias y el último queda cortado
    nombres = ["0, supervisor", "1, gestor max_media", "2, gestor base", "3, gestor activo"]
    trabajo = [[int(f[f"ic{h}"]) - int(f[f"son{h}"]) + LAZO[h] for f in est] for h in range(4)]
    resp = [int(f["respuesta"]) for f in est]
    comunes = [int(f["respuesta"]) for f in est if f["frontera"] == "0"]
    front = [int(f["respuesta"]) for f in est if f["frontera"] == "1"]
    fin = [int(f["c_fin"]) for f in est if int(f["c_fin"]) >= 0]
    ult_voto = [max(int(f["c_est1"]), int(f["c_est2"]), int(f["c_est3"])) for f in est]
    pub = [int(f["c_pub"]) for f in est]
    print()
    print(f"  Ticks medidos: {len(est)} ({len(front)} con frontera de ventana). Ciclo de 40 ns.")
    print()
    print("  Instrucciones de trabajo por tick y por hilo (fuera de los lazos de sondeo, mas la vuelta que encuentra el dato)")
    print(f"    {'hilo':24s} {'minimo':>7s} {'promedio':>9s} {'maximo':>7s} {'ciclos prom.':>13s} {'ciclos max.':>12s} {'CPI':>6s}")
    for h in range(4):
        lo, pr, hi = estadistica(trabajo[h])
        print(f"    {nombres[h]:24s} {lo:7d} {pr:9.2f} {hi:7d} {4 * pr:13.2f} {4 * hi:12d} {4.0:6.3f}")
    suma = [sum(t[i] for t in trabajo) for i in range(len(est))]
    lo, pr, hi = estadistica(suma)
    print(f"    {'los cuatro (agregado)':24s} {lo:7d} {pr:9.2f} {hi:7d} {pr:13.2f} {hi:12d} {1.0:6.3f}")
    print("    Cada hilo ejecuta una instruccion cada 4 ciclos: CPI 4 por hilo y 1 agregado, por construccion.")
    print()
    print("  Ciclos desde que llega el precio (byte_done)")
    print(f"    {'hito':44s} {'minimo':>7s} {'promedio':>9s} {'maximo':>7s} {'tiempo prom.':>13s} {'tiempo max.':>12s}")
    for nombre, v in (("el supervisor publica PUB", pub), ("llega el ultimo voto", ult_voto),
                      ("DECISION (respuesta), todos los ticks", resp), ("DECISION, ticks comunes", comunes),
                      ("DECISION, ticks con frontera", front), ("el supervisor vuelve a sondear (tick completo)", fin)):
        if not v:
            continue
        lo, pr, hi = estadistica(v)
        print(f"    {nombre:44s} {lo:7d} {pr:9.2f} {hi:7d} {pr * 0.04:10.2f} us {hi * 0.04:9.2f} us")
    print()
    peor = max(resp)
    print("  Peor caso de la respuesta contra el presupuesto de cada ronda")
    for nombre, per in (("1 (10 ms)", 10000000), ("2 (1 ms)", 1000000), ("3 (0,1 ms)", 100000)):
        pres = (per - 9500) // 40
        print(f"    ronda {nombre:11s} presupuesto {pres:7d} ciclos, uso {100.0 * peor / pres:7.3f} %, holgura {100.0 * (pres - peor) / pres:6.2f} %")
    turnos = periodo_ns // 40
    print()
    print(f"  Ocupacion a este periodo: {pr_ocup(suma):.2f} instrucciones de trabajo de {turnos} turnos por tick ({100.0 * pr_ocup(suma) / turnos:.2f} %)")


def pr_ocup(suma):
    return sum(suma) / len(suma)


if __name__ == "__main__":
    sys.exit(main())
