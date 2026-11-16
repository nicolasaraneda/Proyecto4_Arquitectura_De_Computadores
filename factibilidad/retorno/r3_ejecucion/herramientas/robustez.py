#!/usr/bin/env python3
"""robustez.py: qué pasa con la contabilidad propia cuando lo que supone no es cierto.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    make finales        (mediciones/finales_robustez.txt)

El espejo de la contabilidad parte de una caja inicial y una comisión que el
programa lleva como constantes (10000 y 5). Nada le avisa si la maestra usa
otras, ni si empieza otra ronda sin reiniciar la placa. Aquí se mide la
diferencia de patrimonio contra `max_media`, que no supone nada, en tres
casos:

  1. La maestra parte con otra caja (opción --caja del arnés).
  2. La maestra cobra otra comisión (opción --comision).
  3. El espejo parte con otra caja (parámetro caja0 de la estrategia) y la
     maestra con 10000: es lo que pasa en una ronda que empieza sin reiniciar
     la placa, con el espejo de la ronda anterior.

Además mide el costo de los caminos caros de la contabilidad: cuántos
cocientes y cuántos productos generales hace por ronda. Semilla 0.
"""
import argparse
import os
import subprocess
import sys


def correr(binario, *args):
    return subprocess.run([binario, *args], check=True, capture_output=True, text=True).stdout


def resumen(binario, estrategias, conjunto, largo, extra=()):
    filas = []
    salida = correr(binario, "resumen", "--conjunto", conjunto, "--largo", str(largo), "--semilla", "0", "--estrategia",
                    ";".join(estrategias), *extra)
    for linea in salida.splitlines():
        if linea.startswith("#"):
            continue
        p = linea.split()
        filas.append(dict(nombre=p[0], n=int(p[1]), media=float(p[2]), dif=float(p[3]), ee=float(p[4]), p5=float(p[6]),
                          ordenes=float(p[10])))
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arnes", required=True)
    ap.add_argument("--series", required=True)
    ap.add_argument("--finales", required=True, help="candidatas separadas por ';'")
    a = ap.parse_args()
    finales = [f for f in a.finales.split(";") if f]
    vistas = [("2000 ticks", "evidencia", 2000, ()), ("20000 ticks, parada", "evidencia", 20000, ("--parada",))]

    print("Robustez de la contabilidad propia. Diferencia pareada de patrimonio contra max_media (+- error estandar), conjunto evidencia, semilla 0.")
    print("La estrategia supone siempre caja 10000 y comision 5, salvo en la tabla 3.")

    print("\n1. La maestra parte con otra caja")
    print(f"{'caja real':>10s} {'vista':20s} | {'max_media':>10s} | " + " | ".join(f"{f:>24s}" for f in finales))
    for caja in (1000, 5000, 9000, 9500, 10000, 10500, 11000, 12000, 15000, 20000, 100000):
        for nombre, conjunto, largo, extra in vistas:
            r = resumen(a.arnes, ["max_media"] + finales, conjunto, largo, ("--caja", str(caja)) + extra)
            print(f"{caja:10d} {nombre:20s} | {r[0]['media']:10.0f} | " + " | ".join(
                f"{x['dif']:+9.1f} +- {x['ee']:5.1f} {100 * x['dif'] / r[0]['media']:+5.2f}%" for x in r[1:]))

    print("\n2. La maestra cobra otra comision")
    print(f"{'comision':>10s} {'vista':20s} | {'max_media':>10s} | " + " | ".join(f"{f:>24s}" for f in finales))
    for com in (0, 2, 5, 10, 20, 50):
        for nombre, conjunto, largo, extra in vistas:
            r = resumen(a.arnes, ["max_media"] + finales, conjunto, largo, ("--comision", str(com)) + extra)
            print(f"{com:10d} {nombre:20s} | {r[0]['media']:10.0f} | " + " | ".join(
                f"{x['dif']:+9.1f} +- {x['ee']:5.1f} {100 * x['dif'] / r[0]['media']:+5.2f}%" for x in r[1:]))

    print("\n3. El espejo parte con otra caja y la maestra con 10000 (ronda sin reiniciar la placa)")
    print(f"{'caja espejo':>11s} {'vista':20s} | {'max_media':>10s} | " + " | ".join(f"{f:>24s}" for f in finales))
    for caja0 in (5000, 7000, 8000, 9000, 9500, 10000, 10500, 11000, 12000, 15000, 20000, 40000):
        for nombre, conjunto, largo, extra in vistas:
            r = resumen(a.arnes, ["max_media"] + [f"{f},caja0={caja0}" for f in finales], conjunto, largo, extra)
            print(f"{caja0:11d} {nombre:20s} | {r[0]['media']:10.0f} | " + " | ".join(
                f"{x['dif']:+9.1f} +- {x['ee']:5.1f} {100 * x['dif'] / r[0]['media']:+5.2f}%" for x in r[1:]))

    print("\n4. Caminos caros de la contabilidad, promedio por ronda (comando detalle: contadores de la estrategia)")
    print("   cocientes: compras que la maestra recorta y ejecutan al menos una accion ((caja - 5) / precio, menor que 63)")
    print("   productos: ventas de un resto de menos de 63 acciones (6 bits por 8 bits). 63 x precio no cuenta: es 64 p - p")
    print("   suprimidas: ticks en que la regla dejo de mandar una compra que habria ejecutado al menos una accion")
    print(f"{'candidata':26s} {'lote':28s} | {'ordenes':>8s} {'cocientes':>10s} {'productos':>10s} {'suprimidas':>11s} | {'ticks con cociente o producto':>30s}")
    for f in ["ejec"] + finales:
        for lote in ("remuestreo_s0_n2000", "modelo_s0_n2000", "remuestreo_s0_n20000", "modelo_s0_n20000"):
            ruta = os.path.join(a.series, lote + ".bin")
            largo = int(lote.rsplit("_n", 1)[1])
            filas = [list(map(int, l.split())) for l in correr(a.arnes, "detalle", "--estrategia", f, "--lote", ruta).splitlines()]
            n = len(filas)
            ordenes = sum(x[1] for x in filas) / n
            div = sum(x[4] for x in filas) / n
            mul = sum(x[5] for x in filas) / n
            sup = sum(x[6] for x in filas) / n
            print(f"{f:26s} {lote:28s} | {ordenes:8.1f} {div:10.2f} {mul:10.2f} {sup:11.1f} | {100 * (div + mul) / largo:29.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
