#!/usr/bin/env python3
"""series.py: series de precios para evaluar algoritmos fuera de la serie de práctica.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Tres fuentes de series, todas de enteros entre 1 y 255 y todas reproducibles
con una semilla:

  1. Bloques de la serie de práctica (`bloques`): 10 tramos de 2000 ticks.
  2. Remuestreo por bloques de los incrementos (`remuestreo`): se cortan los
     cambios de precio de la serie de práctica en bloques de ticks seguidos,
     se eligen bloques al azar con reposición y se vuelven a sumar. Dentro de
     cada bloque se conserva la dependencia entre ticks vecinos (que es de
     donde gana la reversión). Entre bloques se pierde, así que el nivel de
     largo plazo de la serie remuestreada es un paseo aleatorio. Para una
     regla de reversión es una prueba más dura que la serie original.
  3. Familias sintéticas (`FAMILIAS`): paseo aleatorio, tendencia, reversión,
     saltos, cambios de volatilidad, serie plana, bordes 1 y 255, y un modelo
     de dos componentes (nivel lento más componente transitoria). Sirven para
     ver qué pasa si la serie oculta no se parece a la de práctica.

Estas series son datos de prueba. Nada de esto queda dentro del diseño.

Uso como programa, para generar un CSV que el testbench puede leer:

    python3 ref/series.py listar
    python3 ref/series.py reversion --n 2000 --semilla 3 -o build/series/reversion_3.csv
    python3 ref/series.py remuestreo --n 2000 --semilla 1 -o build/series/remuestreo_1.csv
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import market           # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRACTICA = os.path.join(RAIZ, "tb", "practica.csv")

P_MIN, P_MAX = 1, 255


def practica():
    return market.leer_serie(PRACTICA)


def bloques(precios, largo=2000):
    """Tramos consecutivos de `largo` ticks, sin traslape."""
    return [precios[i:i + largo] for i in range(0, len(precios) - largo + 1, largo)]


def reflejar(x):
    """Lleva x al rango [1, 255] rebotando en los bordes."""
    ancho = P_MAX - P_MIN
    y = (x - P_MIN) % (2 * ancho)
    return P_MIN + (y if y <= ancho else 2 * ancho - y)


def a_precios(valores):
    """Redondea y lleva al rango una lista de números reales."""
    return [int(round(reflejar(v))) for v in valores]


# ---- Remuestreo por bloques de los incrementos ----------------------------------

def remuestreo(precios, n, rng, bloque=100):
    """Serie de n ticks armada con bloques de incrementos de `precios`.

    Parte de un precio tomado de la serie original y va sumando los
    incrementos de bloques elegidos al azar. Si el nivel toca 1 o 255 rebota.
    """
    d = [b - a for a, b in zip(precios, precios[1:])]
    nivel = precios[rng.randrange(len(precios))]
    salida = [nivel]
    while len(salida) < n:
        i = rng.randrange(len(d) - bloque + 1)
        for inc in d[i:i + bloque]:
            nivel = reflejar(nivel + inc)
            salida.append(nivel)
            if len(salida) == n:
                break
    return salida


# ---- Familias sintéticas -----------------------------------------------------------

def paseo(n, rng, sigma=1.0, p0=None):
    """Paseo aleatorio: cada cambio es independiente del anterior. No hay nada que predecir."""
    x = rng.uniform(90, 170) if p0 is None else p0
    salida = []
    for _ in range(n):
        salida.append(x)
        x = reflejar(x + rng.gauss(0, sigma))
    return a_precios(salida)


def tendencia(n, rng, sigma=1.0, recorrido=80.0):
    """Paseo aleatorio con deriva: sube o baja `recorrido` unidades a lo largo de la serie."""
    signo = rng.choice([-1, 1])
    x = rng.uniform(100, 150) - signo * recorrido / 2
    deriva = signo * recorrido / n
    salida = []
    for _ in range(n):
        salida.append(x)
        x = reflejar(x + deriva + rng.gauss(0, sigma))
    return a_precios(salida)


def reversion(n, rng, theta=0.05, sigma=2.0, mu=None):
    """Reversión a una media fija (proceso de Ornstein-Uhlenbeck discreto)."""
    mu = rng.uniform(60, 200) if mu is None else mu
    x = mu
    salida = []
    for _ in range(n):
        salida.append(x)
        x = x + theta * (mu - x) + rng.gauss(0, sigma)
    return a_precios(salida)


def dos_componentes(n, rng, sigma_nivel=0.6, phi=0.9, sigma_trans=1.5, p0=None):
    """Nivel lento (paseo aleatorio) más componente transitoria AR(1), y redondeo.

    Es la forma del modelo que el frente del algoritmo debe ajustar a la serie
    de práctica. Los valores por defecto no están calibrados.
    """
    nivel = rng.uniform(80, 180) if p0 is None else p0
    trans = 0.0
    salida = []
    for _ in range(n):
        salida.append(nivel + trans)
        nivel = reflejar(nivel + rng.gauss(0, sigma_nivel))
        trans = phi * trans + rng.gauss(0, sigma_trans)
    return a_precios(salida)


def saltos(n, rng, prob=0.004, tam=(10, 30)):
    """Reversión a una media que cada cierto tiempo salta de golpe a otro nivel."""
    mu = rng.uniform(80, 180)
    x = mu
    salida = []
    for _ in range(n):
        salida.append(x)
        if rng.random() < prob:
            mu = reflejar(mu + rng.choice([-1, 1]) * rng.uniform(*tam))
            x = mu + (x - mu) * 0.2            # el precio salta con el nivel
        x = x + 0.05 * (mu - x) + rng.gauss(0, 2.0)
    return a_precios(salida)


def cambio_volatilidad(n, rng, sigmas=(0.7, 4.0), tramo=(200, 800)):
    """Dos componentes con tramos de volatilidad baja y alta que se alternan."""
    nivel = rng.uniform(80, 180)
    trans = 0.0
    salida = []
    alta = rng.random() < 0.5
    quedan = rng.randint(*tramo)
    for _ in range(n):
        salida.append(nivel + trans)
        if quedan == 0:
            alta = not alta
            quedan = rng.randint(*tramo)
        quedan -= 1
        s = sigmas[1] if alta else sigmas[0]
        nivel = reflejar(nivel + rng.gauss(0, 0.3 * s))
        trans = 0.9 * trans + rng.gauss(0, s)
    return a_precios(salida)


def plana(n, rng, p0=None):
    """Precio constante. Cualquier orden que se ejecute solo paga comisión."""
    p = rng.randint(P_MIN, P_MAX) if p0 is None else p0
    return [p] * n


def borde_bajo(n, rng):
    """Serie pegada al precio mínimo (1): prueba la aritmética en el borde."""
    return [max(P_MIN, min(P_MAX, int(round(v)))) for v in
            _ou_libre(n, rng, mu=3.0, theta=0.1, sigma=1.5)]


def borde_alto(n, rng):
    """Serie pegada al precio máximo (255)."""
    return [max(P_MIN, min(P_MAX, int(round(v)))) for v in
            _ou_libre(n, rng, mu=253.0, theta=0.1, sigma=1.5)]


def _ou_libre(n, rng, mu, theta, sigma):
    x = mu
    salida = []
    for _ in range(n):
        salida.append(x)
        x = x + theta * (mu - x) + rng.gauss(0, sigma)
    return salida


def cambio_de_caracter(n, rng):
    """Primera mitad con reversión, segunda mitad con tendencia, sin salto de nivel entre las dos."""
    a = dos_componentes(n // 2, rng)
    b = tendencia(n - n // 2, rng)
    corrimiento = a[-1] - b[0]
    return a + [reflejar(v + corrimiento) for v in b]


FAMILIAS = {
    "paseo": paseo,
    "tendencia": tendencia,
    "reversion": reversion,
    "dos_componentes": dos_componentes,
    "saltos": saltos,
    "cambio_volatilidad": cambio_volatilidad,
    "cambio_de_caracter": cambio_de_caracter,
    "plana": plana,
    "borde_bajo": borde_bajo,
    "borde_alto": borde_alto,
}


def semilla_de(nombre, semilla, i=0):
    """Semilla entera reproducible (no depende del hash de Python, que cambia entre corridas)."""
    return sum(ord(c) * 131 ** k for k, c in enumerate(nombre)) % 1000003 + 1000003 * semilla + 7919 * i


def lote(nombre, cantidad, n=2000, semilla=0):
    """`cantidad` series de la familia `nombre` (o "remuestreo"), reproducibles."""
    series = []
    base = practica() if nombre == "remuestreo" else None
    for i in range(cantidad):
        rng = random.Random(semilla_de(nombre, semilla, i))
        if nombre == "remuestreo":
            series.append(remuestreo(base, n, rng))
        else:
            series.append(FAMILIAS[nombre](n, rng))
    return series


def escribir_csv(ruta, precios):
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    with open(ruta, "w", newline="\n") as f:
        f.write("tick,price\n")
        for i, p in enumerate(precios):
            f.write(f"{i},{p}\n")


def razon_de_varianza(p, k):
    """VR(k): 1 en un paseo aleatorio, menor que 1 si hay reversión, mayor que 1 si hay tendencia."""
    d1 = [b - a for a, b in zip(p, p[1:])]
    dk = [p[i + k] - p[i] for i in range(len(p) - k)]
    m1, mk = sum(d1) / len(d1), sum(dk) / len(dk)
    v1 = sum((x - m1) ** 2 for x in d1) / len(d1)
    vk = sum((x - mk) ** 2 for x in dk) / len(dk)
    return vk / (k * v1) if v1 > 0 else float("nan")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Genera series de prueba (CSV tick,price)")
    ap.add_argument("familia", help="listar, remuestreo o el nombre de una familia")
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("-o", "--salida")
    a = ap.parse_args(argv)

    if a.familia == "listar":
        print(f"{'familia':20s} {'min':>4s} {'max':>4s} {'VR(10)':>7s} {'VR(50)':>7s}  descripcion (una serie de 2000 ticks, semilla 0)")
        p = practica()
        print(f"{'practica (20000)':20s} {min(p):4d} {max(p):4d} {razon_de_varianza(p, 10):7.2f} {razon_de_varianza(p, 50):7.2f}  serie de practica completa")
        for nombre in ["remuestreo"] + list(FAMILIAS):
            s = lote(nombre, 1, 2000, 0)[0]
            doc = "bloques de incrementos de la serie de practica" if nombre == "remuestreo" else FAMILIAS[nombre].__doc__.split("\n")[0]
            print(f"{nombre:20s} {min(s):4d} {max(s):4d} {razon_de_varianza(s, 10):7.2f} {razon_de_varianza(s, 50):7.2f}  {doc}")
        return 0
    if a.familia != "remuestreo" and a.familia not in FAMILIAS:
        ap.error(f"familia desconocida: {a.familia} (ver: python3 ref/series.py listar)")
    serie = lote(a.familia, 1, a.n, a.semilla)[0]
    if a.salida:
        escribir_csv(a.salida, serie)
        print(f"{a.salida}: {len(serie)} ticks, de {min(serie)} a {max(serie)}")
    else:
        print("tick,price")
        for i, p in enumerate(serie):
            print(f"{i},{p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
