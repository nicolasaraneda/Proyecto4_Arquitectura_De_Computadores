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
  3. Familias sintéticas (`FAMILIAS`), calibradas contra la serie de práctica
     con los parámetros de ref/calibracion.py y separadas en dos grupos:
       - `PLAUSIBLES`: el modelo ajustado a la serie de práctica y sus
         vecinos. Es a lo que debería parecerse la serie oculta si sale del
         mismo generador.
       - `ESTRES`: paseo aleatorio, tendencia, saltos frecuentes, cambio de
         carácter, otra volatilidad, otro nivel, serie plana y bordes 1 y
         255. Sirven para ver cuánto se pierde si la serie oculta es distinta.

Estas series son datos de prueba. Nada de esto queda dentro del diseño.

Uso como programa, para generar un CSV que el testbench puede leer:

    python3 ref/series.py listar
    python3 ref/series.py reversion --n 2000 --semilla 3 -o build/series/reversion_3.csv
    python3 ref/series.py remuestreo --n 2000 --semilla 1 -o build/series/remuestreo_1.csv
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import calibracion as cal   # noqa: E402
import market               # noqa: E402

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


# ---- Modelo calibrado del generador ---------------------------------------------------

def modelo(n, rng, q_nivel=cal.Q_NIVEL, q_trans=cal.Q_TRANS, phi=cal.PHI, razon=cal.RAZON_RUIDOSO,
           dur_tranquilo=cal.DUR_TRANQUILO, dur_ruidoso=cal.DUR_RUIDOSO, p_salto=cal.P_SALTO,
           salto_tam=cal.SALTO_TAM, p0=None, deriva=0.0, redondear=True):
    """Modelo ajustado a la serie de práctica (ref/generador.py, ref/calibracion.py).

    Nivel lento (paseo aleatorio) más componente transitoria AR(1), dos
    regímenes de volatilidad que se alternan, saltos de nivel poco frecuentes
    y redondeo a enteros. `deriva` suma una tendencia al nivel.
    """
    nivel = rng.uniform(*cal.NIVEL_INICIAL) if p0 is None else p0
    ruidoso = rng.random() < dur_ruidoso / (dur_tranquilo + dur_ruidoso)
    escala = math.sqrt(razon) if ruidoso else 1.0
    s_nivel, s_trans = math.sqrt(q_nivel), math.sqrt(q_trans)
    trans = rng.gauss(0, escala * s_trans / math.sqrt(1 - phi * phi))
    salida = []
    for _ in range(n):
        salida.append(nivel + trans)
        if rng.random() < 1.0 / (dur_ruidoso if ruidoso else dur_tranquilo):
            ruidoso = not ruidoso
            escala = math.sqrt(razon) if ruidoso else 1.0
        nivel = reflejar(nivel + deriva + rng.gauss(0, escala * s_nivel))
        if rng.random() < p_salto:
            nivel = reflejar(nivel + rng.choice([-1, 1]) * rng.uniform(*salto_tam))
        trans = phi * trans + rng.gauss(0, escala * s_trans)
    return a_precios(salida) if redondear else salida


def _log_uniforme(rng, amplitud):
    """Factor al azar entre exp(-amplitud) y exp(amplitud)."""
    return math.exp(rng.uniform(-amplitud, amplitud))


def modelo_vecino(n, rng):
    """El modelo calibrado con cada parámetro movido al azar, hasta la mitad o el doble.

    Cubre el error de la calibración y la posibilidad de que la serie oculta
    salga del mismo generador con otros parámetros: más o menos volatilidad,
    reversión más rápida o más lenta, más o menos tiempo en el régimen ruidoso.
    """
    vida_media = math.log(0.5) / math.log(cal.PHI) * _log_uniforme(rng, 0.7)
    volatilidad = _log_uniforme(rng, 0.7)
    return modelo(n, rng,
                  q_nivel=cal.Q_NIVEL * volatilidad,
                  q_trans=cal.Q_TRANS * volatilidad * _log_uniforme(rng, 0.7),
                  phi=0.5 ** (1.0 / vida_media),
                  razon=cal.RAZON_RUIDOSO * _log_uniforme(rng, 0.5),
                  dur_tranquilo=cal.DUR_TRANQUILO * _log_uniforme(rng, 0.7),
                  dur_ruidoso=cal.DUR_RUIDOSO * _log_uniforme(rng, 0.7),
                  p_salto=cal.P_SALTO * _log_uniforme(rng, 1.0),
                  p0=rng.uniform(60, 200))


# Varianza del cambio de un tick antes de redondear, en el régimen tranquilo: es
# lo que usan las familias sin componente transitoria para tener la misma
# volatilidad que la serie de práctica.
Q_TOTAL = cal.Q_NIVEL + 2 * cal.Q_TRANS / (1 + cal.PHI)
# Mezcla de los dos regímenes en un solo número (86 % tranquilo, 14 % ruidoso)
FRAC_RUIDOSO = cal.DUR_RUIDOSO / (cal.DUR_TRANQUILO + cal.DUR_RUIDOSO)
MEZCLA = 1 - FRAC_RUIDOSO + FRAC_RUIDOSO * cal.RAZON_RUIDOSO


# ---- Familias sintéticas -----------------------------------------------------------
# Todas están calibradas contra la serie de práctica: la volatilidad, los
# regímenes, la escala de la reversión y el tamaño de los saltos salen de
# ref/calibracion.py. Lo que cambia de una familia a otra es qué pieza del
# modelo se quita, se exagera o se reemplaza.

def paseo(n, rng, p0=None):
    """Paseo aleatorio con la volatilidad y los regímenes de la práctica, sin reversión."""
    return modelo(n, rng, q_nivel=Q_TOTAL, q_trans=1e-12, p_salto=0.0, p0=p0)


def tendencia(n, rng, deriva=None):
    """Paseo aleatorio con deriva: entre 40 y 120 unidades en 2000 ticks, hacia arriba o hacia abajo.

    El tramo de tendencia más fuerte de la práctica baja 45 unidades en 800
    ticks (0,056 por tick). Aquí la deriva va de 0,02 a 0,06 por tick y dura
    toda la serie.
    """
    if deriva is None:
        deriva = rng.choice([-1, 1]) * rng.uniform(0.02, 0.06)
    p0 = min(230.0, max(25.0, rng.uniform(100, 150) - deriva * n / 2))
    return modelo(n, rng, q_nivel=Q_TOTAL, q_trans=1e-12, p_salto=0.0, p0=p0, deriva=deriva)


def reversion(n, rng, mu=None):
    """Reversión a una media fija: la transitoria de la práctica sin el paseo del nivel."""
    mu = rng.uniform(60, 200) if mu is None else mu
    return modelo(n, rng, q_nivel=1e-12, q_trans=Q_TOTAL * (1 + cal.PHI) / 2, p_salto=0.0, p0=mu)


def dos_componentes(n, rng, p0=None):
    """Nivel lento más transitoria con los parámetros calibrados, en un solo régimen de volatilidad."""
    return modelo(n, rng, q_nivel=cal.Q_NIVEL * MEZCLA, q_trans=cal.Q_TRANS * MEZCLA, razon=1.0, p_salto=0.0, p0=p0)


def saltos(n, rng):
    """El modelo con saltos 20 veces más frecuentes (uno cada 200 ticks) y de hasta 30 unidades."""
    return modelo(n, rng, p_salto=20 * cal.P_SALTO, salto_tam=(cal.SALTO_TAM[0], 30))


def cambio_volatilidad(n, rng):
    """El modelo con los regímenes alternando rápido: tramos de 200 a 800 ticks, mitad del tiempo en cada uno."""
    return modelo(n, rng, dur_tranquilo=500, dur_ruidoso=500, p_salto=0.0)


def volatil(n, rng):
    """El modelo siempre en el régimen ruidoso y con el doble de varianza."""
    return modelo(n, rng, q_nivel=2 * cal.Q_NIVEL * cal.RAZON_RUIDOSO, q_trans=2 * cal.Q_TRANS * cal.RAZON_RUIDOSO,
                  razon=1.0)


def nivel_bajo(n, rng):
    """El modelo con precios entre 15 y 40: los mismos movimientos pesan mucho más en porcentaje."""
    return modelo(n, rng, p0=rng.uniform(15, 40))


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
    """Primera mitad como la práctica, segunda mitad con tendencia, sin salto de nivel entre las dos."""
    a = modelo(n // 2, rng)
    b = tendencia(n - n // 2, rng, deriva=rng.choice([-1, 1]) * rng.uniform(0.04, 0.10))
    corrimiento = a[-1] - b[0]
    return a + [reflejar(v + corrimiento) for v in b]


FAMILIAS = {
    "modelo": modelo,
    "modelo_vecino": modelo_vecino,
    "dos_componentes": dos_componentes,
    "cambio_volatilidad": cambio_volatilidad,
    "paseo": paseo,
    "tendencia": tendencia,
    "reversion": reversion,
    "saltos": saltos,
    "cambio_de_caracter": cambio_de_caracter,
    "volatil": volatil,
    "nivel_bajo": nivel_bajo,
    "plana": plana,
    "borde_bajo": borde_bajo,
    "borde_alto": borde_alto,
}

# Plausibles: se parecen a la serie de práctica. Si la serie oculta sale del
# mismo generador, debería parecerse a una de estas.
PLAUSIBLES = ["modelo", "modelo_vecino", "dos_componentes", "cambio_volatilidad"]
# De estrés: algo importante es distinto. Sirven para ver cuánto se pierde si
# la serie oculta no se parece a la de práctica.
ESTRES = ["paseo", "tendencia", "reversion", "saltos", "cambio_de_caracter", "volatil", "nivel_bajo",
          "plana", "borde_bajo", "borde_alto"]


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
            grupo = "plausible" if nombre in PLAUSIBLES or nombre == "remuestreo" else "estres"
            print(f"{nombre:20s} {min(s):4d} {max(s):4d} {razon_de_varianza(s, 10):7.2f} {razon_de_varianza(s, 50):7.2f}  [{grupo}] {doc}")
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
