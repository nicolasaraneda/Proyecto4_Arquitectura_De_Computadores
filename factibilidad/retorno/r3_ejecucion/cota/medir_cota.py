#!/usr/bin/env python3
"""medir_cota.py: cuánto se ganaría como máximo arreglando la ejecución.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    make cota

Corre la regla de `max_media` con un límite por orden hipotético (estrategia
`lim` de cota/lim.c, sobre la copia del núcleo de cota/parche.sh) y la compara
con `max_media` con el límite real de 63:

    lim:L=63    el límite real (debe dar diferencia cero)
    lim:L=126   el doble
    lim:L=252   el cuádruple
    lim:L=0     sin límite: la posición completa entra y sale en una orden

Los rivales del torneo siguen con el límite real. La diferencia de `lim:L=0`
contra `max_media` es la cota: lo más que puede ganar cualquier forma de
ejecutar la misma señal, porque ninguna maestra real acepta esas órdenes.
Semilla 0.
"""
import argparse
import subprocess
import sys

LIMITES = [("63", "lim:L=63"), ("126", "lim:L=126"), ("252", "lim:L=252"), ("sin limite", "lim:L=0")]


def correr(binario, *args):
    return subprocess.run([binario, *args], check=True, capture_output=True, text=True).stdout


def resumen(binario, conjunto, largo, vista):
    args = ["resumen", "--conjunto", conjunto, "--largo", str(largo), "--semilla", "0", "--estrategia",
            "max_media;" + ";".join(s for _, s in LIMITES)]
    if vista:
        args.append("--" + vista)
    filas = {}
    for linea in correr(binario, *args).splitlines():
        if linea.startswith("#"):
            continue
        p = linea.split()
        filas[p[0]] = dict(n=int(p[1]), media=float(p[2]), dif=float(p[3]), ee=float(p[4]), mediana=float(p[5]), p5=float(p[6]),
                           ordenes=float(p[10]), geom=float(p[12]))
    return filas


def veredicto(binario, spec):
    texto = correr(binario, "veredicto", "--candidata", spec, "--referencia", "max_media", "--semilla", "0", "--parada")
    filas = {}
    for linea in texto.splitlines():
        partes = linea.split("|")
        if len(partes) == 4 and partes[0].split() and partes[0].split()[0] in ("2000", "20000"):
            largo, series, conjunto, lectura = partes[0].split()
            m, q = partes[1].split(), partes[2].split()
            if lectura == "H1":
                filas[(largo, series, conjunto, lectura)] = (float(m[2]), float(m[3]), float(q[2]), 0.0)
            else:
                filas[(largo, series, conjunto, lectura)] = (float(m[2]), float(m[3]), float(q[2]), float(q[3]))
    return texto, filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cota", required=True)
    a = ap.parse_args()

    print("Cota de la ejecucion: max_media con un limite por orden hipotetico, contra max_media con el limite real (63).")
    print("Semilla 0. Diferencias pareadas con su error estandar. Los rivales del torneo siguen con el limite real.")

    print("\n1. Patrimonio (H1) y ordenes por ronda")
    print("Vistas: todas las series; interior, solo las series con el precio siempre entre 21 y 249; parada, cada serie hasta el primer")
    print("precio fuera de 21 a 249. Sin limite y con todas las series la media no sirve: en las pocas series que bajan a precios de 1 a 5")
    print("una orden sin limite compra miles de acciones, el patrimonio se multiplica por miles y llega a desbordar los 32 bits (p5 negativo).")
    print("Para la cota valen la vista interior, la mediana, la media geometrica y los puntos del torneo.")
    print(f"{'largo':>6s} {'vista':10s} {'conjunto':11s} {'limite':10s} | {'series':>6s} {'media':>9s} {'dif':>8s} {'+-ee':>6s} {'dif %':>7s} "
          f"{'mediana':>8s} {'p5':>7s} {'dif p5':>7s} | {'ordenes':>8s} {'geom':>9s} {'dif geom %':>10s}")
    for largo, vistas in ((2000, ["", "interior"]), (20000, ["interior", "parada", ""])):
        for vista in vistas:
            for conjunto in ("evidencia", "remuestreo", "plausibles", "estres"):
                try:
                    f = resumen(a.cota, conjunto, largo, vista)
                except subprocess.CalledProcessError:
                    continue
                ref = f["max_media"]
                print(f"{largo:6d} {vista or 'todas':10s} {conjunto:11s} {'max_media':10s} | {ref['n']:6d} {ref['media']:9.0f} {'':8s} {'':6s} {'':7s} "
                      f"{ref['mediana']:8.0f} {ref['p5']:7.0f} {'':7s} | {ref['ordenes']:8.1f} {ref['geom']:9.0f}")
                for nombre, spec in LIMITES:
                    x = f[spec]
                    print(f"{largo:6d} {vista or 'todas':10s} {conjunto:11s} {nombre:10s} | {x['n']:6d} {x['media']:9.0f} {x['dif']:+8.1f} {x['ee']:6.1f} "
                          f"{100 * x['dif'] / ref['media']:+6.2f}% {x['mediana']:8.0f} {x['p5']:7.0f} {x['p5'] - ref['p5']:+7.0f} | "
                          f"{x['ordenes']:8.1f} {x['geom']:9.0f} {100 * (x['geom'] / ref['geom'] - 1):+9.2f}%")
            print()

    print("2. Puntos del torneo (campo mixto, G = 10): diferencia contra max_media, media y percentil 5 de tres rondas")
    print(f"{'limite':10s} {'largo':>6s} {'series':10s} {'conjunto':10s} | {'dH3a':>7s} {'+-ee':>6s} {'dp5':>7s} {'+-ee':>6s} | "
          f"{'dH3b':>7s} {'+-ee':>6s} {'dp5':>7s} {'+-ee':>6s} | {'dH1':>7s} {'+-ee':>5s}")
    textos = []
    for nombre, spec in LIMITES:
        texto, f = veredicto(a.cota, spec)
        textos.append((nombre, texto))
        for clave in sorted({k[:3] for k in f}, key=lambda k: (int(k[0]), k[1] != "todas", k[1], k[2] != "evidencia", k[2])):
            xa, xb, h1 = f.get(clave + ("H3a",)), f.get(clave + ("H3b",)), f.get(clave + ("H1",))
            if not xa:
                continue
            print(f"{nombre:10s} {clave[0]:>6s} {clave[1]:10s} {clave[2]:10s} | {xa[0]:+7.3f} {xa[1]:6.3f} {xa[2]:+7.3f} {xa[3]:6.3f} | "
                  f"{xb[0]:+7.3f} {xb[1]:6.3f} {xb[2]:+7.3f} {xb[3]:6.3f} | {h1[0]:+7.0f} {h1[1]:5.0f}")
        print()

    print("3. Salida completa de cada veredicto")
    for nombre, texto in textos:
        print(f"\n--- limite {nombre} ---")
        print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
