#!/usr/bin/env python3
"""gemelo.py: envoltorio en Python del gemelo digital (ref/gemelo/gemelo.c).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Compila el gemelo si hace falta y lo corre sobre un lote de series. Devuelve,
por serie, lo mismo que informa el testbench oficial: patrimonio final,
órdenes, pérdida máxima, peor caso de respuesta en ciclos, cuántos precios
tuvieron respuesta y cuántos se perdieron.

    import gemelo
    resultados = gemelo.correr_lote(series, hex="sw/trade.hex", periodo_ns=100000)

Por defecto la primera transacción llega a los 200 us, después del reset de la
placa (164 us), que es la situación de la competencia: no se pierde ningún
precio. Para reproducir el testbench oficial hay que pasar inicio_ns=4000.
"""
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE = os.path.join(RAIZ, "ref", "gemelo", "gemelo.c")
BINARIO = os.path.join(RAIZ, "build", "gemelo")

CAMPOS = ("patrimonio", "ordenes", "perdida_max", "peor_caso", "respuestas", "precios_perdidos", "comprar_y_mantener")


def compilar():
    """Compila build/gemelo si no existe o si el fuente es más nuevo."""
    if os.path.exists(BINARIO) and os.path.getmtime(BINARIO) >= os.path.getmtime(FUENTE):
        return BINARIO
    os.makedirs(os.path.dirname(BINARIO), exist_ok=True)
    subprocess.run([os.environ.get("CC", "cc"), "-O2", "-o", BINARIO, FUENTE], check=True)
    return BINARIO


def correr_lote(series, hex=None, periodo_ns=100000, inicio_ns=200000, extra=()):
    """Corre el programa `hex` sobre cada serie. Devuelve una lista de diccionarios."""
    binario = compilar()
    hex = hex or os.path.join(RAIZ, "sw", "trade.hex")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for s in series:
            f.write(" ".join(map(str, s)) + "\n")
        ruta = f.name
    try:
        salida = subprocess.run([binario, "--hex", hex, "--lote", ruta, "--periodo-ns", str(periodo_ns),
                                 "--inicio-ns", str(inicio_ns), *map(str, extra)],
                                check=True, capture_output=True, text=True).stdout
    finally:
        os.unlink(ruta)
    filas = [dict(zip(CAMPOS, map(int, linea.split()))) for linea in salida.splitlines() if linea.strip()]
    if len(filas) != len(series):
        raise RuntimeError(f"el gemelo devolvió {len(filas)} resultados para {len(series)} series")
    return filas


if __name__ == "__main__":
    print(compilar())
    sys.exit(0)
