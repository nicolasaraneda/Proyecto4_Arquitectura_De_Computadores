#!/usr/bin/env python3
"""zscore.py: referencia de la regla "zscore" de Vicente Calderón, para evaluarla con el protocolo.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Es una candidata, no la estrategia oficial: R0, R1 y R2 siguen con `max_media`
(ref/trader.py y ref/fondo.py). La regla viene de tools/referencia.py del
repositorio de Vicente (función agente_zscore); aquí se reescribe con la
interfaz de las estrategias del protocolo (un método decidir(p) que devuelve el
byte de DECISION) y con sus parámetros abiertos para medir la meseta.

Regla, toda en enteros (valores por defecto, los de Vicente):

  Estado: M = 2^km x media (km = 5), D = 2^kd x desviación absoluta media
  (kd = 6, en las mismas unidades que M), quiere, n.
  Primer precio: M = 2^km p, D = 0, escribe mantener.
  Con cada precio p:
      dev = 2^km p - M ; mag = |dev|          desvío con la media anterior
      M  += p - ((M + 2^(km-1)) >> km)        media exponencial redondeada
      D  += mag - ((D + 2^(kd-1)) >> kd)      desviación absoluta media; el umbral usa la D nueva
      los primeros W = 64 precios después del primero: solo actualiza y escribe mantener
      entra si dev < 0 y den x 2^kd x mag > num x D     (mag > z d, con z = num/den = 5/2)
      sale  si dev > 0
      DECISION = comprar 63 si quiere, vender 63 si no.

Con km = 5, kd = 6 y z = 5/2 la condición de entrada es 128 mag > 5 D, la del
enunciado de la tarea. La salida se puede mover con sx2: sale si
2 x 2^kd x dev > sx2 x D, es decir dev > (sx2 / 2) d. Con sx2 = 0
(por defecto) es dev > 0, la regla de Vicente.

Uso:

    python3 ref/zscore.py tb/practica.csv                 # patrimonio y órdenes en la serie completa
    python3 ref/zscore.py tb/practica.csv --num 9 --den 4  # umbral 2,25
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import market  # noqa: E402
import trader  # noqa: E402


class ZScore:
    """Regla zscore. Parámetros enteros para que el protocolo la pueda pedir por nombre.

    km, kd   memorias de la media y de la desviación (2^km y 2^kd ticks)
    num, den umbral de entrada z = num / den, en desviaciones absolutas medias
    w        precios de calentamiento después del primero (solo actualiza)
    sx2  umbral de salida en medias desviaciones: sale si dev > (sx2 / 2) d
    """

    def __init__(self, km=5, kd=6, num=5, den=2, w=64, sx2=0):
        if km < 1 or kd < 1 or den < 1 or num < 0 or w < 0:
            raise ValueError("parámetros fuera de rango")
        self.km, self.kd, self.num, self.den, self.w, self.sx2 = km, kd, num, den, w, sx2
        self.M = None
        self.D = 0
        self.n = 0
        self.quiere = 0

    def decidir(self, p):
        km, kd = self.km, self.kd
        if self.M is None:
            self.M = p << km
            return market.MANTENER
        dev = (p << km) - self.M
        mag = -dev if dev < 0 else dev
        self.M += p - ((self.M + (1 << (km - 1))) >> km)
        self.D += mag - ((self.D + (1 << (kd - 1))) >> kd)
        if self.n < self.w:
            self.n += 1
            return market.MANTENER
        if dev < 0 and (self.den << kd) * mag > self.num * self.D:
            self.quiere = 1
        elif dev > 0 and (2 << kd) * dev > self.sx2 * self.D:
            self.quiere = 0
        return market.COMPRAR_63 if self.quiere else market.VENDER_63


def main(argv=None):
    ap = argparse.ArgumentParser(description="Regla zscore sobre una serie")
    ap.add_argument("serie")
    for nombre, v in (("km", 5), ("kd", 6), ("num", 5), ("den", 2), ("w", 64), ("sx2", 0)):
        ap.add_argument("--" + nombre.replace("_", "-"), type=int, default=v)
    ap.add_argument("--perdidos", type=int, default=0)
    a = ap.parse_args(argv)
    precios = market.leer_serie(a.serie)
    z = ZScore(a.km, a.kd, a.num, a.den, a.w, a.sx2)
    m = trader.correr(precios, z, perdidos=a.perdidos)
    mm = trader.correr(precios, trader.MaxMedia(), perdidos=a.perdidos)
    print(f"zscore (km={a.km}, kd={a.kd}, z={a.num}/{a.den}, w={a.w}, sx2={a.sx2}): "
          f"patrimonio {m.w}, ordenes {m.ordenes}, perdida max {m.max_dd}")
    print(f"max_media: patrimonio {mm.w}, ordenes {mm.ordenes}, perdida max {mm.max_dd}")


if __name__ == "__main__":
    main()
