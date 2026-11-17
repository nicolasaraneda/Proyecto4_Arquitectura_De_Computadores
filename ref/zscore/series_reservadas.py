#!/usr/bin/env python3
"""series_reservadas.py: series de la semilla 4, la reservada para la evaluación de zscore.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Usa el mismo generador del estudio de retorno (factibilidad/retorno/generar_series.py)
con una semilla (por defecto 4, la reservada de T128; la tarea B usa la 5, que nadie había usado), en los dos largos y con
las mismas cantidades. Deja los archivos en build/zscore/series/ junto con enlaces
a las series ya generadas de las semillas 0 a 3, para que el arnés las encuentre
todas con RETORNO_SERIES=build/zscore/series.

Uso: python3 ref/zscore/series_reservadas.py
"""
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RETORNO = os.path.join(RAIZ, "factibilidad", "retorno")
sys.path.insert(0, RETORNO)
import generar_series as g  # noqa: E402

DESTINO = os.path.join(RAIZ, "build", "zscore", "series")


def main():
    os.makedirs(DESTINO, exist_ok=True)
    origen = g.DESTINO
    for nombre in sorted(os.listdir(origen)):
        if nombre.endswith(".bin"):
            enlace = os.path.join(DESTINO, nombre)
            if not os.path.lexists(enlace):
                os.symlink(os.path.join(origen, nombre), enlace)
    g.DESTINO = DESTINO
    s = int(os.environ.get("SEMILLA", "4"))
    g.SEMILLAS = {2000: (s,), 20000: (s,)}
    g.PROCESOS = int(os.environ.get("PROCESOS", "16"))
    return g.main([])


if __name__ == "__main__":
    sys.exit(main())
