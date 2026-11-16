#!/usr/bin/env python3
"""comparar_vistos.py: estado del fondo en el barrel contra la referencia en C, sobre los precios vistos.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

tb/tb_carreras.sv escribe una fila por tick del supervisor (cuando publica el
precio siguiente): precio, espejo de la caja y de las acciones, posición y
puntaje de cada gestor, pesos y byte de DECISION. La traza de referencia sale
de fondo.c (FONDO_TRAZA) corrido sobre la serie de precios que el supervisor
publicó. Se comparan 13 campos por fila.

Uso: comparar_vistos.py ESTADO.csv TRAZA.csv [anterior]
Con "anterior" (la variante que decide con lo del tick anterior) las
posiciones, los puntajes y los pesos de la fila i se comparan con la fila
i + 1 de la traza. La traza anota en cada tick lo que el supervisor vio, que
es lo que los gestores publicaron en el tick previo, y en esa variante el
ajuste de pesos del tick i + 1 se hace antes de publicar, que es cuando el
testbench toma la fila i.
Escribe una línea "PASS modelo: ..." o "FAIL modelo: ..." y sale con 0 o 1.
"""
import csv
import sys

PARES = [("precio", "precio"), ("caja", "caja"), ("acciones", "acciones"),
         ("pos1", "pos0"), ("pos2", "pos1"), ("pos3", "pos2"),
         ("des1", "des0"), ("des2", "des1"), ("des3", "des2"),
         ("w1", "w0"), ("w2", "w1"), ("w3", "w2"), ("decision", "decision")]


def main():
    with open(sys.argv[1], encoding="ascii") as f:
        est = list(csv.DictReader(f))
    with open(sys.argv[2], encoding="ascii") as f:
        ref = list(csv.DictReader(f))
    pares = PARES
    corridos = ()
    if len(sys.argv) > 3 and sys.argv[3] == "anterior":
        corridos = ("pos", "des", "w")
    if not est or len(est) != len(ref):
        print(f"FAIL modelo: {len(est)} filas del barrel y {len(ref)} de la referencia")
        return 1
    malas, por_campo, primera = 0, {}, None
    for i, (a, b) in enumerate(zip(est, ref)):
        dif = []
        for x, y in pares:
            base = 16 if x == "decision" else 10
            if x.startswith(corridos) and corridos:
                if i + 1 >= len(ref):
                    continue
                b = ref[i + 1]
            else:
                b = ref[i]
            if int(a[x], base) != int(b[y], base):
                dif.append(f"{x} {a[x]} y {b[y]}")
                por_campo[x] = por_campo.get(x, 0) + 1
        if dif:
            malas += 1
            if primera is None:
                primera = f"fila {i}: " + ", ".join(dif[:4])
    cambios_pos = sum(1 for i in range(1, len(est)) for c in ("pos1", "pos2", "pos3") if est[i][c] != est[i - 1][c])
    cambios_dec = sum(1 for i in range(1, len(est)) if est[i]["decision"] != est[i - 1]["decision"])
    if malas:
        print(f"FAIL modelo: {malas} de {len(est)} filas distintas ({', '.join(f'{k} {v}' for k, v in por_campo.items())}); primera en la {primera}")
        return 1
    print(f"PASS modelo: {len(est)} filas por {len(pares)} campos identicas a la referencia sobre los precios vistos "
          f"({cambios_pos} cambios de posicion de los gestores, {cambios_dec} cambios del byte)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
