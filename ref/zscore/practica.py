#!/usr/bin/env python3
"""practica.py: la grilla de zscore en la serie de práctica completa y en sus 10 bloques.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Muestra dónde queda la regla de Vicente (z = 2,5, memorias 32 y 64) dentro de su
vecindario en la serie con la que se eligió: patrimonio en los 20 000 ticks y media
y peor de los 10 bloques de 2000. Una cima aislada en la serie de elección, que
no se repite fuera de ella, es la firma del sobreajuste (docs/protocolo.md).

Uso: python3 ref/zscore/practica.py
"""
import os
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARNES = os.path.join(RAIZ, "build", "zscore", "arnes")
SERIES = os.environ.get("RETORNO_SERIES", os.path.join(RAIZ, "build", "zscore", "series"))


def detalle(spec, archivo):
    out = subprocess.run([ARNES, "detalle", "--estrategia", spec, "--lote", os.path.join(SERIES, archivo)],
                         check=True, capture_output=True, text=True).stdout.split("\n")
    return [list(map(int, l.split()[:2])) for l in out if l.strip()]


def main():
    lineas = ["La grilla de zscore en la serie de practica (la serie con que se eligieron sus parametros).",
              "Generado por ref/zscore/practica.py. W 20k: patrimonio en los 20 000 ticks. Bloques: 10 tramos de 2000.", ""]
    mm = detalle("max_media", "practica_n20000.bin")[0]
    mb = [w for w, _ in detalle("max_media", "bloques_n2000.bin")]
    lineas.append(f"max_media: W 20k {mm[0]} ({mm[1]} ordenes); bloques: media {sum(mb) / 10:.0f}, peor {min(mb)}")
    lineas.append("")
    zs = list(range(4, 13))
    for km in (4, 5, 6):
        for kd in (5, 6, 7):
            fila20, filab = [], []
            for num in zs:
                spec = f"zscore:km={km},kd={kd},num={num},den=4"
                fila20.append(detalle(spec, "practica_n20000.bin")[0][0])
                b = [w for w, _ in detalle(spec, "bloques_n2000.bin")]
                filab.append((sum(b) / 10, min(b)))
            if km == 4 and kd == 5:
                lineas.append(f"{'':10s} " + " ".join(f"{'z ' + format(n / 4, '.2f'):>13s}" for n in zs))
            lineas.append(f"km={km} kd={kd} W 20k   " + " ".join(f"{w:13d}" for w in fila20))
            lineas.append(f"{'':9s} bloques " + " ".join(f"{m:7.0f}/{p:5d}" for m, p in filab))
        lineas.append("")
    lineas.append("Bloques: media/peor. La regla de Vicente es km=5 kd=6 z 2,50.")
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    os.makedirs(os.path.join(RAIZ, "docs", "mediciones", "zscore"), exist_ok=True)
    with open(os.path.join(RAIZ, "docs", "mediciones", "zscore", "practica.txt"), "w", newline="\n") as f:
        f.write(texto)


if __name__ == "__main__":
    sys.exit(main())
