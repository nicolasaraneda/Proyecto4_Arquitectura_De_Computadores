#!/usr/bin/env python3
"""validar_gemelo.py: el binario de la placa contra la regla base del arnés, en las series nuevas.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 factibilidad/retorno/pruebas/validar_gemelo.py [--semilla 0]     (o make gemelo)

El arnés evalúa estrategias a nivel de tick. El gemelo digital
(ref/gemelo/gemelo.c) simula el SoC ciclo a ciclo y ejecuta sw/trade.hex, el
mismo programa del bitstream. Aquí se usa el gemelo para lo único que aporta
en este estudio: confirmar que el programa actual decide igual que la regla
base del arnés también en las series de este tramo, que son nuevas (rondas de
20 000 ticks, y series que tocan los límites 1 y 255).

Se compara patrimonio, órdenes y pérdida máxima, serie por serie:
  - todas las series de la semilla pedida, a 2000 y a 20 000 ticks, con el
    período de la ronda 3 (0,1 ms);
  - las primeras series de cada lote con los períodos de las rondas 2 y 1
    (1 ms y 10 ms);
  - una muestra con el core segmentado (--pipeline).
Además se exige que ningún precio quede sin respuesta.

La primera transacción llega a los 200 us, después del reset de la placa: el
programa ve todos los precios, como en la competencia.
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
RAIZ = os.path.dirname(os.path.dirname(RETORNO))
sys.path.insert(0, RETORNO)

import generar_series       # noqa: E402

ARNES = os.path.join(RETORNO, "build", "retorno")
GEMELO = os.path.join(RETORNO, "build", "gemelo")
SERIES = os.path.join(RETORNO, "build", "series")
HEX = os.path.join(RAIZ, "sw", "trade.hex")
PROCESOS = int(os.environ.get("PROCESOS", "6"))
MUESTRA = {2000: 100, 20000: 20}        # series por lote para los períodos largos y el core segmentado


def correr(args):
    """Corre el gemelo y el arnés sobre las primeras `cuantas` series de un lote. Devuelve los conteos."""
    archivo, cuantas, periodo, extra = args
    ruta = os.path.join(SERIES, archivo)
    # las series pasan del arnés al gemelo por una tubería, como texto (una serie por línea)
    texto = subprocess.Popen([ARNES, "lote-texto", ruta, "--max", str(cuantas)], stdout=subprocess.PIPE)
    g = subprocess.run([GEMELO, "--hex", HEX, "--lote", "/dev/stdin", "--periodo-ns", str(periodo), "--inicio-ns", "200000",
                        *extra], stdin=texto.stdout, check=True, capture_output=True, text=True).stdout.splitlines()
    texto.stdout.close()
    if texto.wait() != 0:
        raise RuntimeError(f"no se pudo leer {ruta}")
    a = subprocess.run([ARNES, "detalle", "--lote", ruta, "--estrategia", "base"], check=True, capture_output=True,
                       text=True).stdout.splitlines()[:len(g)]
    distintas = sin_respuesta = ticks = 0
    peor = 0
    for lg, la in zip(g, a):
        w, ordenes, dd, peor_caso, respuestas, perdidos, byh = map(int, lg.split())
        x = list(map(int, la.split()))
        distintas += [w, ordenes, dd, byh] != [x[0], x[1], x[2], x[7]]
        ticks += respuestas
        peor = max(peor, peor_caso)
    n = int(archivo.split("_n")[-1].split(".")[0])
    sin_respuesta = sum(int(lg.split()[4]) != n or int(lg.split()[5]) != 0 for lg in g)
    return len(g), ticks, distintas, sin_respuesta, peor


def main(argv=None):
    ap = argparse.ArgumentParser(description="sw/trade.hex en el gemelo contra la regla base del arnés")
    ap.add_argument("--semilla", type=int, default=0)
    a = ap.parse_args(argv)

    lotes = [("bloques_n2000.bin", 10, 2000), ("practica_n20000.bin", 1, 20000)]
    lotes += [(archivo, cantidad, n) for archivo, _, cantidad, n, s in generar_series.plan(semillas=[a.semilla])]
    grupos = [
        ("periodo 0,1 ms (ronda 3), todas las series", [(f, c, 100000, ()) for f, c, _ in lotes]),
        ("periodo 1 ms (ronda 2), muestra", [(f, min(c, MUESTRA[n]), 1000000, ()) for f, c, n in lotes]),
        ("periodo 10 ms (ronda 1), muestra", [(f, min(c, MUESTRA[n]), 10000000, ()) for f, c, n in lotes]),
        ("core segmentado, 0,1 ms, muestra", [(f, min(c, MUESTRA[n]), 100000, ("--pipeline",)) for f, c, n in lotes]),
    ]
    print(f"sw/trade.hex en el gemelo digital contra la regla base del arnes. Semilla {a.semilla}, {len(lotes)} lotes.")
    fallas = 0
    with ThreadPoolExecutor(PROCESOS) as pool:
        for titulo, trabajos in grupos:
            res = list(pool.map(correr, trabajos))
            series_n = sum(r[0] for r in res)
            ticks = sum(r[1] for r in res)
            distintas = sum(r[2] for r in res)
            sin_respuesta = sum(r[3] for r in res)
            peor = max(r[4] for r in res)
            fallas += distintas + sin_respuesta
            print(f"{'PASS' if distintas + sin_respuesta == 0 else 'FAIL'}  {titulo}: {series_n} series, {ticks} ticks. "
                  f"Distintas al arnes: {distintas}. Series con algun precio sin respuesta: {sin_respuesta}. "
                  f"Peor caso de respuesta: {peor} ciclos", flush=True)
    print("PASS: el binario decide igual que la regla base del arnes en todas las series" if fallas == 0
          else f"FAIL: {fallas} series con diferencias")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
