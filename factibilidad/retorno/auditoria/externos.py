#!/usr/bin/env python3
"""externos.py: patrimonio por serie de los candidatos que la auditoría no reescribe.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El evaluador independiente (auditoria/indep.c) tiene su propia versión de la
regla de reversión (base, max_media, activo, prudente) y de los rivales. Los
candidatos con estimador de dos estados o con guardia (kalman, kalman_base,
guardia, guardia_tope) no se reescribieron: su patrimonio por serie se pide al
comando `detalle` del arnés y se guarda en build/auditoria/ext/. En las tablas
de la auditoría van marcados como externos.

    python3 auditoria/externos.py            (desde factibilidad/retorno)
"""
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
ARNES = os.path.join(RETORNO, "build", "retorno")
SERIES = os.path.join(RETORNO, "build", "series")
DESTINO = os.path.join(RETORNO, "build", "auditoria", "ext")

CANDIDATOS = ["kalman", "kalman_base", "guardia", "guardia_tope"]
FAMILIAS = ["remuestreo", "modelo", "modelo_vecino", "dos_componentes", "cambio_volatilidad",
            "paseo", "tendencia", "reversion", "saltos", "cambio_de_caracter", "volatil", "nivel_bajo"]


def archivos():
    lista = ["bloques_n2000", "practica_n20000"]
    for semilla in (0, 2):
        for largo in (2000, 20000):
            lista += [f"{f}_s{semilla}_n{largo}" for f in FAMILIAS]
    return lista


def main():
    os.makedirs(DESTINO, exist_ok=True)
    hechos = 0
    for archivo in archivos():
        origen = os.path.join(SERIES, archivo + ".bin")
        for cand in CANDIDATOS:
            destino = os.path.join(DESTINO, f"{cand}__{archivo}.txt")
            if os.path.exists(destino) and os.path.getmtime(destino) >= max(os.path.getmtime(origen), os.path.getmtime(ARNES)):
                continue
            r = subprocess.run([ARNES, "detalle", "--estrategia", "cand:" + cand, "--lote", origen],
                               capture_output=True, text=True, check=True)
            with open(destino + ".tmp", "w") as f:
                f.write(r.stdout)
            os.replace(destino + ".tmp", destino)
            hechos += 1
    print(f"externos: {len(archivos())} archivos de series, {len(CANDIDATOS)} candidatos, {hechos} archivos escritos en {os.path.relpath(DESTINO, RETORNO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
