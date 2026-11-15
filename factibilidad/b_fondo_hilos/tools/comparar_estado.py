#!/usr/bin/env python3
"""comparar_estado.py: estado interno del fondo en el barrel contra la traza del módulo en C.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

tb/tb_fondo.sv anota, al cerrar cada tick, lo que quedó en la memoria del SoC:
espejo de la caja y de las acciones, posición y desempeño en papel de cada
gestor, pesos y byte de DECISION. factibilidad/retorno/r4b_fondo/fondo.c
escribe lo mismo por tick con FONDO_TRAZA. Este script compara las dos tablas
fila por fila y campo por campo. Con los bytes de DECISION solos, un error en
el espejo o en un puntaje podría pasar inadvertido hasta la frontera de
ventana siguiente, o para siempre.

Uso:
    python3 tools/comparar_estado.py TICKS.csv TRAZA.csv
Sale con 0 si todas las filas coinciden.
"""
import csv
import sys

# campo del testbench -> campo de la traza en C
PARES = [
    ("precio", "precio"), ("caja", "caja"), ("acciones", "acciones"),
    ("pos1", "pos0"), ("pos2", "pos1"), ("pos3", "pos2"),
    ("des1", "des0"), ("des2", "des1"), ("des3", "des2"),
    ("w1", "w0"), ("w2", "w1"), ("w3", "w2"), ("decision", "decision"),
]


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    with open(sys.argv[1], encoding="ascii") as f:
        ticks = list(csv.DictReader(f))
    with open(sys.argv[2], encoding="ascii") as f:
        traza = list(csv.DictReader(f))
    filas = min(len(ticks), len(traza))
    distintas = 0
    por_campo = {a: 0 for a, _ in PARES}
    primera = None
    for i in range(filas):
        mal = []
        for a, b in PARES:
            x, y = ticks[i][a], traza[i][b]
            igual = (int(x, 16) == int(y, 16)) if a == "decision" else (int(x) == int(y))
            if not igual:
                mal.append(f"{a}: barrel {x}, referencia {y}")
                por_campo[a] += 1
        if mal:
            distintas += 1
            if primera is None:
                primera = (i, ticks[i]["tick"], mal)
    cambios_peso = sum(1 for i in range(1, filas) if any(ticks[i][c] != ticks[i - 1][c] for c in ("w1", "w2", "w3")))
    ordenes = sum(1 for i in range(1, filas) if ticks[i]["acciones"] != ticks[i - 1]["acciones"])
    print(f"  filas del testbench {len(ticks)}, filas de la traza {len(traza)}, comparadas {filas}")
    print(f"  campos por fila: {len(PARES)} ({', '.join(a for a, _ in PARES)})")
    print(f"  en esas filas: {ordenes} ticks en que el espejo cambia de acciones, {cambios_peso} cambios de pesos, "
          f"pesos finales {ticks[filas - 1]['w1']}/{ticks[filas - 1]['w2']}/{ticks[filas - 1]['w3']}, "
          f"espejo final caja {ticks[filas - 1]['caja']} y acciones {ticks[filas - 1]['acciones']}")
    if len(ticks) != len(traza):
        print(f"FAIL las dos tablas no tienen el mismo largo")
        return 1
    if distintas:
        i, tick, mal = primera
        print(f"FAIL {distintas} filas distintas. Por campo: " + ", ".join(f"{k} {v}" for k, v in por_campo.items() if v))
        print(f"  primera diferencia en la fila {i} (tick {tick} de la serie): " + "; ".join(mal))
        return 1
    print(f"PASS {filas} filas por {len(PARES)} campos idénticas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
