#!/usr/bin/env python3
"""
lote.py: escribe un lote de series sintéticas de ref/series.py, una por archivo.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso: tools/fondo/lote.py CARPETA CANTIDAD_POR_FAMILIA N_TICKS SEMILLA
Imprime la ruta de cada serie. Las familias son todas las de ref/series.py más
el remuestreo por bloques de la serie de práctica. Con NORMALIZAR=1 escribe además
cada serie normalizada como las de la competencia (mínimo 100, máximo 255;
ref/cotas/comun.py), con la familia "FAMILIA-norm": la regla de R1 y R2 solo
opera cuando la serie toca esos extremos.
"""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))

import series  # noqa: E402


def main(argv):
    carpeta, cantidad, n, semilla = argv[1], int(argv[2]), int(argv[3]), int(argv[4])
    os.makedirs(carpeta, exist_ok=True)
    for familia in ["remuestreo"] + sorted(series.FAMILIAS):
        for i, precios in enumerate(series.lote(familia, cantidad, n, semilla)):
            ruta = os.path.join(carpeta, f"{familia}_{i:03d}.csv")
            series.escribir_csv(ruta, precios)
            print(ruta)
            if os.environ.get("NORMALIZAR") == "1":
                ruta = os.path.join(carpeta, f"{familia}-norm_{i:03d}.csv")
                series.escribir_csv(ruta, comun.normalizar(precios))
                print(ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
