#!/usr/bin/env python3
"""resumen_timing.py: tabla de costo de la extensión a partir de las líneas de
tools/medir_variante.sh.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 resumen_timing.py lineas.txt

La primera línea (xd_ref) es el barrel sin la extensión. Para cada variante
informa cuántas celdas agrega y cuántas quedan libres de las 1280 de la FPGA.
"""
import re
import sys

PAT = re.compile(r"^(\S+)\s+celdas\s+(\d+) de 1280, BRAM\s+(\d+) de 16, LUT4\s+(\d+), "
                 r"fmax min\s+([\d.]+) mediana\s+([\d.]+) max\s+([\d.]+) MHz, cierran a 25 MHz (\d+) de (\d+)")


def main():
    filas = []
    for linea in open(sys.argv[1], encoding="utf-8"):
        m = PAT.match(linea)
        if m:
            filas.append(m.groups())
    if not filas:
        print("sin mediciones")
        return 1
    ref = int(filas[0][1])
    print("Variante   Celdas  Agrega  Libres  BRAM  Fmax minima  Mediana  Maxima  Cierran")
    for n, lc, ram, _lut, fmin, fmed, fmax, c, s in filas:
        agrega = "" if n == filas[0][0] else f"{int(lc) - ref:+d}"
        print(f"{n:<10} {int(lc):>6}  {agrega:>6}  {1280 - int(lc):>6}  {ram:>4}  {fmin:>11}  {fmed:>7}  {fmax:>6}  {c} de {s}")
    print()
    print("El conteo de celdas de un mismo circuito se mueve unas 10 celdas entre sintesis")
    print("(decision T6): una diferencia menor que eso no se puede atribuir a un cambio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
