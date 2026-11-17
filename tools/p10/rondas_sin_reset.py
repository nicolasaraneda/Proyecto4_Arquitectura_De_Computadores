#!/usr/bin/env python3
"""
rondas_sin_reset.py: cuánto cambia el patrimonio de una ronda si la placa no
se reinicia después de la anterior (revisión P10, docs/revision_p10.md,
observación 2).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Entre rondas el programa sigue con su estado (medias, posición, pesos) y
DECISION conserva la última orden. Si la maestra reinicia la caja al empezar
una ronda pero la placa no se reinicia, la ronda nueva parte con la primera
transacción ejecutando la última orden de la anterior y con la media de la
otra serie. Este script compara, con las referencias exactas (ref/fondo.py
para R1 y R2, ref/trader.py para R0), el patrimonio de la ronda B:

  fresca     la placa parte de cero en la ronda B
  seguida    la placa viene de correr la ronda A sin reinicio

Las rondas son series de 2000 ticks. Se usan pares de series de la familia
"modelo" con semillas distintas (plausibles) y pares en que la ronda B tiene
otro nivel de precios ("nivel_bajo" y "saltos"). No modela precios perdidos
en el reset (la diferencia es la misma en los dos casos).

Uso: python3 tools/p10/rondas_sin_reset.py [--pares 40]
"""

import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))

import fondo     # noqa: E402
import market    # noqa: E402
import series    # noqa: E402
import trader    # noqa: E402

N = 2000


def serie(familia, semilla):
    return series.lote(familia, 1, N, semilla)[0]


def ronda_b(a, b, estrategia):
    """Patrimonio de la ronda b fresca y seguida de a."""
    fresca = market.simular(b, trader.decisiones(b, estrategia()))
    seguidas = trader.decisiones(a + b, estrategia())
    seguida = market.simular(b, seguidas[len(a):])
    return fresca.w, seguida.w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pares", type=int, default=40)
    a = ap.parse_args()
    grupos = [("modelo seguida de modelo", "modelo", "modelo"),
              ("modelo seguida de nivel_bajo", "modelo", "nivel_bajo"),
              ("nivel_bajo seguida de modelo", "nivel_bajo", "modelo"),
              ("modelo seguida de saltos", "modelo", "saltos")]
    print("Ronda B fresca contra ronda B seguida de la ronda A sin reiniciar la placa (caja reiniciada)")
    print("Generado por tools/p10/rondas_sin_reset.py. Series de 2000 ticks, %d pares por grupo." % a.pares)
    print()
    print(f"{'grupo':32s} {'programa':10s} {'media fresca':>12s} {'media seguida':>13s} {'dif. media':>10s} {'peor dif.':>9s} {'mejor dif.':>10s} {'pares peor':>10s}")
    for nombre, fa, fb in grupos:
        for prog, est in (("R1 y R2", fondo.Fondo), ("R0", trader.Oficial)):
            fres, segs = [], []
            for k in range(a.pares):
                sa = serie(fa, 1000 + k)
                sb = serie(fb, 5000 + k)
                f, s = ronda_b(sa, sb, est)
                fres.append(f)
                segs.append(s)
            difs = [s - f for f, s in zip(fres, segs)]
            peor = sum(1 for d in difs if d < 0)
            print(f"{nombre:32s} {prog:10s} {sum(fres) / len(fres):12.1f} {sum(segs) / len(segs):13.1f} "
                  f"{sum(difs) / len(difs):10.1f} {min(difs):9d} {max(difs):10d} {peor:6d}/{len(difs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
