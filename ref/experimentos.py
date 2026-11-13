#!/usr/bin/env python3
"""experimentos.py: ideas que aprenden en vivo, rehechas con control de rotación.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Los primeros intentos del grupo (perceptrón en línea y población de traders)
perdieron contra la regla base porque operaban demasiado y las comisiones se
los comían. Aquí se rehacen con histéresis y con un punto de partida fuerte
(los parámetros ya validados), para ver si adaptarse a la serie en curso
agrega algo.

  Poblacion    Varios traders virtuales con bandas distintas comparten la misma
               media. Cada uno lleva la cuenta de lo que habría ganado. Se
               sigue al líder, y el líder solo cambia si otro lo supera por un
               margen y no hay posición abierta.
  Adaptacion   Lo mismo con tres traders vecinos a la regla base y un margen
               grande: es la adaptación en vivo con prior fuerte.
  Perceptron   Predice el cambio de precio a 16 ticks con una combinación
               lineal de tres entradas, corrige los pesos con el error
               (regla LMS) y opera con histéresis sobre la predicción.

    python3 ref/experimentos.py      # tabla contra la regla base, con error estándar

Se evalúan con la referencia en Python sobre los 10 bloques, 400 remuestreos y
400 series del modelo calibrado, comparando serie por serie con la regla base.
"""
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import market           # noqa: E402
import series           # noqa: E402
import trader           # noqa: E402

K = 5


class Poblacion:
    """Sigue al mejor de varios traders virtuales, con margen para cambiar de líder."""

    def __init__(self, entradas=(64, 96, 128, 160, 192), salidas=(-32, 0, 32), margen=24, costo=1, olvido=10, inicial=None):
        self.bandas = [(e, x) for e in entradas for x in salidas]
        self.margen, self.costo, self.olvido = margen, costo, olvido
        self.lider = self.bandas.index(inicial if inicial else (128, 0))
        self.pos = [0] * len(self.bandas)
        self.entrada = [0] * len(self.bandas)
        self.puntaje = [0] * len(self.bandas)       # ganancia virtual, en cuartos de unidad de precio
        self.S = None
        self.cambios = 0

    def decidir(self, p):
        if self.S is None:
            self.S = p << K
        dev = (p << K) - self.S
        self.S += dev >> K
        for i, (e, x) in enumerate(self.bandas):
            if self.pos[i] and dev > x:
                self.pos[i] = 0
                self.puntaje[i] += 4 * (p - self.entrada[i]) - self.costo
            elif not self.pos[i] and dev < -e and not dev > x:
                self.pos[i], self.entrada[i] = 1, p
            self.puntaje[i] -= self.puntaje[i] >> self.olvido      # las ganancias viejas pesan menos
        mejor = max(range(len(self.bandas)), key=lambda i: self.puntaje[i])
        if (mejor != self.lider and not self.pos[self.lider] and not self.pos[mejor]
                and self.puntaje[mejor] > self.puntaje[self.lider] + self.margen):
            self.lider = mejor
            self.cambios += 1
        return market.COMPRAR_63 if self.pos[self.lider] else market.VENDER_63


class Adaptacion(Poblacion):
    """Tres traders vecinos a la regla base y un margen grande para dejarla."""

    def __init__(self):
        super().__init__(entradas=(96, 128, 160), salidas=(0,), margen=48)


class Perceptron:
    """Predicción lineal del cambio a `h` ticks, con corrección LMS e histéresis."""

    def __init__(self, h=16, paso=14, entra=24, sale=0, espera=8):
        self.h, self.paso, self.entra, self.sale, self.espera = h, paso, entra, sale, espera
        # pesos en punto fijo (por 2^12). Parten en la regla base: solo pesa la desviación lenta, con signo negativo
        self.w = [-(1 << 12) // 16, 0, 0]
        self.S5 = self.S3 = None
        self.pant = None
        self.cola = []                    # (entradas, precio de ejecución) a la espera de su resultado
        self.pos, self.quieto = 0, 0

    def decidir(self, p):
        if self.S5 is None:
            self.S5, self.S3, self.pant = p << 5, p << 3, p
        x = [(p << 5) - self.S5, ((p << 3) - self.S3) << 2, (p - self.pant) << 5]     # todas por 32
        self.S5 += x[0] >> 5
        self.S3 += ((p << 3) - self.S3) >> 3
        self.pant = p
        # aprende con el caso de hace h + 1 ticks: ya se conoce cuánto cambió el precio desde su ejecución
        self.cola.append([x, None])
        if len(self.cola) >= 2 and self.cola[-2][1] is None:
            self.cola[-2][1] = p          # precio al que se habría ejecutado la decisión anterior
        if len(self.cola) > self.h + 1:
            xv, pe = self.cola.pop(0)
            error = ((p - pe) << 5) - (sum(w * v for w, v in zip(self.w, xv)) >> 12)
            for i in range(3):
                self.w[i] += (error * xv[i]) >> self.paso
        y = sum(w * v for w, v in zip(self.w, x)) >> 12            # cambio predicho, por 32
        if self.quieto:
            self.quieto -= 1
        elif not self.pos and y > self.entra:
            self.pos, self.quieto = 1, self.espera
        elif self.pos and y < self.sale:
            self.pos, self.quieto = 0, self.espera
        return market.COMPRAR_63 if self.pos else market.VENDER_63


ESTRATEGIAS = {"poblacion (15 traders)": Poblacion, "adaptacion con prior fuerte": Adaptacion, "perceptron": Perceptron}


def _evaluar(args):
    nombre, precios = args
    m = trader.correr(precios, ESTRATEGIAS[nombre]() if nombre else trader.ReglaBase())
    return m.w, m.ordenes


def main():
    conjuntos = (("practica, 10 bloques", series.bloques(series.practica(), 2000)),
                 ("remuestreo (400)", series.lote("remuestreo", 400, 2000, 0)),
                 ("modelo (400)", series.lote("modelo", 400, 2000, 0)),
                 ("paseo (200)", series.lote("paseo", 200, 2000, 0)))
    print("Ideas que aprenden en vivo, contra la regla base. Diferencia pareada de patrimonio y su error estandar.")
    print(f"{'estrategia':28s} {'conjunto':22s} {'media':>7s} {'base':>7s} {'dif':>6s} {'+-ee':>5s} {'p5':>6s} {'p5 base':>7s} {'ordenes':>8s} {'base':>6s}")
    with Pool(12) as pool:
        base = {c: pool.map(_evaluar, [(None, s) for s in lista], chunksize=8) for c, lista in conjuntos}
        for nombre in ESTRATEGIAS:
            for c, lista in conjuntos:
                r = pool.map(_evaluar, [(nombre, s) for s in lista], chunksize=8)
                b = base[c]
                n = len(r)
                dif = [x[0] - y[0] for x, y in zip(r, b)]
                m = sum(dif) / n
                ee = (sum((v - m) ** 2 for v in dif) / (n - 1) / n) ** 0.5
                ws, wb = sorted(x[0] for x in r), sorted(y[0] for y in b)
                print(f"{nombre:28s} {c:22s} {sum(ws) / n:7.0f} {sum(wb) / n:7.0f} {m:+6.0f} {ee:5.0f} "
                      f"{ws[int(0.05 * n)]:6d} {wb[int(0.05 * n)]:7d} {sum(x[1] for x in r) / n:8.1f} {sum(y[1] for y in b) / n:6.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
