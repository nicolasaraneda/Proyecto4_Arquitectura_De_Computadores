#!/usr/bin/env python3
"""equivalencia.py: las estrategias reescritas en la auditoría contra las del arnés, serie por serie.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El evaluador independiente (indep34.c) trae su propia versión de la ejecución
con espejo, del Kalman, de la tabla que aprende y del supervisor del fondo,
escrita a partir de lo que describen los README. Aquí se compara, para cada
una y para cada archivo de series, el patrimonio final y la cantidad de
órdenes de cada serie con lo que entrega el comando `detalle` del arnés
(build/arnes: el núcleo y los módulos de los estudios, sin tocar). Tienen que
ser iguales en todas las series.

Las reglas con un límite por orden hipotético (lim126, lim252 y lim2m) se
comparan con el binario de la cota del estudio 3 (../r3_ejecucion/build/cota/arnes),
si existe. El "sin límite" de ese estudio es en realidad un límite de 2^21
acciones por orden (lim2m). La regla sin límite de verdad (limsin) no tiene
par en el arnés. El arnés lleva la cuenta en 32 bits y el evaluador independiente en
64: las series en que el patrimonio pasa de 2^31, al final o en algún tick, se
cuentan aparte.

    python3 equivalencia.py            (desde factibilidad/retorno/auditoria_r34)
"""
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
ARNES = os.path.join(AQUI, "build", "arnes")
INDEP = os.path.join(AQUI, "build", "indep34")
COTA = os.path.join(RETORNO, "r3_ejecucion", "build", "cota", "arnes")
SERIES = os.path.join(RETORNO, "build", "series")

FAMILIAS = ["remuestreo", "modelo", "modelo_vecino", "dos_componentes", "cambio_volatilidad", "paseo", "tendencia",
            "reversion", "saltos", "cambio_de_caracter", "volatil", "nivel_bajo", "plana", "borde_bajo", "borde_alto"]


def archivos():
    lista = ["bloques_n2000", "practica_n20000"]
    lista += [f"{f}_s0_n2000" for f in FAMILIAS]
    lista += [f"{f}_s0_n20000" for f in FAMILIAS]
    lista += ["remuestreo_s3_n2000", "modelo_s3_n2000", "remuestreo_s3_n20000", "dos_componentes_s3_n20000"]
    return lista


def correr(cmd):
    env = dict(os.environ)
    env.setdefault("HILOS", "5")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=RETORNO, env=env)
    if r.returncode != 0:
        raise RuntimeError(" ".join(cmd) + ": " + r.stderr.strip())
    return [tuple(int(x) for x in linea.split()[:3]) for linea in r.stdout.splitlines() if linea.strip()]


def main():
    lista = subprocess.run([INDEP, "lista"], capture_output=True, text=True, check=True).stdout.split("\n")
    pares = [l.split() for l in lista if l.strip()]
    archs = archivos()
    print("Estrategias reescritas en la auditoria contra las del arnes: patrimonio final y ordenes de cada serie")
    print(f"{len(archs)} archivos de series (semilla 0 a los dos largos, parte de la semilla 3, bloques y practica)")
    print(f"{'propia':16s} {'en el arnes':64s} {'series':>8s} {'distintas':>9s} {'sobre 2^31':>10s}")
    mal = 0
    total_series = 0
    comparadas = 0
    for nombre, spec in pares:
        if spec == "-":
            print(f"{nombre:16s} {'(sin par en el arnes: no se compara)':64s}")
            continue
        es_lim = nombre.startswith("lim")
        binario = COTA if es_lim else ARNES
        if es_lim and not os.path.exists(COTA):
            print(f"{nombre:16s} {spec:64s} no se comparo: falta {os.path.relpath(COTA, RETORNO)}")
            continue
        series = distintas = grandes = 0
        primera = None
        for a in archs:
            ruta = os.path.join(SERIES, a + ".bin")
            suyo = correr([binario, "detalle", "--estrategia", spec, "--lote", ruta])
            mio = correr([INDEP, "detalle", nombre, a])
            if len(suyo) != len(mio):
                raise RuntimeError(f"{nombre} {a}: {len(suyo)} filas contra {len(mio)}")
            for i, (x, y) in enumerate(zip(suyo, mio)):
                series += 1
                if y[0] >= 2 ** 31 or (len(y) > 2 and y[2]):
                    grandes += 1          # el patrimonio pasa de 32 bits al final o en algún tick: el arnés desborda
                    continue
                x, y = x[:2], y[:2]
                if x != y:
                    distintas += 1
                    if primera is None:
                        primera = f"{a} serie {i}: arnes {x}, propia {y}"
        total_series += series
        comparadas += 1
        print(f"{nombre:16s} {spec:64s} {series:8d} {distintas:9d} {grandes:10d}" + (f"   primera: {primera}" if primera else ""))
        sys.stdout.flush()
        mal += distintas
    print()
    print(f"{'PASS' if mal == 0 else 'FAIL'}: {comparadas} estrategias con par en el arnes, {total_series} corridas de series comparadas, {mal} distintas")
    return 1 if mal else 0


if __name__ == "__main__":
    sys.exit(main())
