#!/usr/bin/env python3
"""Hallazgos sobre la serie de practica que p4_baseline.py no imprime.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso, desde la raiz del repositorio:

    python3 ref/hallazgos.py tb/practica.csv

Reutiliza el mercado y las estrategias de p4_baseline.py y agrega:

  1. Razon de varianza en cada uno de los 20 bloques de 1000 ticks.
  2. Autocorrelacion de los cambios de precio, rezagos 1 a 10.
  3. Barrido de seguir tendencia: 336 configuraciones de la media exponencial.
  4. La estrategia trivial "comprar 63 siempre" en los primeros 2000 ticks,
     que es lo que hace el trade.s del tramo 1. Sus numeros deben coincidir
     con los que imprime el testbench oficial.
"""
import statistics as st
import sys

from p4_baseline import (COMPRAR, comprar_y_mantener, leer, razon_de_varianza,
                         reversion_ema, simular, tendencia_ema)


def autocorrelacion(x, rezago):
    m = st.fmean(x)
    num = sum((x[i] - m) * (x[i + rezago] - m) for i in range(len(x) - rezago))
    den = sum((v - m) ** 2 for v in x)
    return num / den


def main():
    p = leer(sys.argv[1] if len(sys.argv) > 1 else "tb/practica.csv")

    print("1. Razon de varianza por bloque de 1000 ticks (menor que 1 indica reversion)")
    print(f"   {'bloque':>6s} {'VR(10)':>7s} {'VR(50)':>7s} {'VR(100)':>8s}")
    bloques = [p[i:i + 1000] for i in range(0, len(p), 1000)]
    bajo_1 = {10: 0, 50: 0, 100: 0}
    for i, b in enumerate(bloques):
        vr = {k: razon_de_varianza(b, k) for k in (10, 50, 100)}
        for k in vr:
            bajo_1[k] += vr[k] < 1
        print(f"   {i:6d} {vr[10]:7.2f} {vr[50]:7.2f} {vr[100]:8.2f}")
    print("   Bloques con VR menor que 1: " + ", ".join(f"VR({k}) en {n} de {len(bloques)}" for k, n in bajo_1.items()))

    print("\n2. Autocorrelacion de los cambios de precio")
    d = [p[i + 1] - p[i] for i in range(len(p) - 1)]
    print("   " + "  ".join(f"r({k})={autocorrelacion(d, k):+.3f}" for k in range(1, 11)))
    print(f"   Banda de ruido aproximada (2 / raiz de N): +-{2 / len(d) ** 0.5:.3f}")

    print("\n3. Barrido de seguir tendencia (media exponencial, serie completa)")
    ks, entradas, salidas = (2, 3, 4, 5, 6, 7, 8), (0, 1, 2, 3, 4, 6, 8, 12), (0, 1, 2, 3, 4, 6)
    finales = sorted(simular(p, tendencia_ema(k, e, s), {})[0] for k in ks for e in entradas for s in salidas)
    bh = comprar_y_mantener(p)
    print(f"   Grilla: k en {ks}, entra en {entradas}, sale en {salidas}: {len(finales)} configuraciones")
    print(f"   Patrimonio final: mediana {round(st.median(finales))}, minimo {finales[0]}, maximo {finales[-1]}")
    print(f"   Terminan sobre 10000: {sum(w > 10000 for w in finales)} de {len(finales)}. "
          f"Superan a comprar y mantener ({bh}): {sum(w > bh for w in finales)} de {len(finales)}")
    rev = sorted(simular(p, reversion_ema(k, e, s), {})[0] for k in ks for e in entradas for s in salidas)
    print(f"   Misma grilla con reversion a la media: mediana {round(st.median(rev))}, minimo {rev[0]}, maximo {rev[-1]}")

    print("\n4. Estrategia trivial del tramo 1: comprar 63 siempre, primeros 2000 ticks")
    w, ordenes, dd = simular(p[:2000], lambda s, pn: COMPRAR, {})
    print(f"   Patrimonio final {w}, ordenes {ordenes}, perdida maxima {dd}")
    print(f"   Comprar y mantener en ese tramo: {comprar_y_mantener(p[:2000])}")


if __name__ == "__main__":
    main()
