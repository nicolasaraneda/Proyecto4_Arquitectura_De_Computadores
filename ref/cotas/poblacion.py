"""poblacion.py: series de un precio por minuto para evaluar reglas (docs/cotas.md, sección 5).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

No hay datos por minuto gratuitos de 2022 a 2024 sin cuenta (docs/pendientes_nicolas.md,
acción 3b). Mientras tanto, dos poblaciones:

1. "puente": los precios diarios reales (apertura, máximo, mínimo, cierre) de META, AAPL,
   NFLX, AMD y TSLA, de diciembre de 2021 a enero de 2025 (Yahoo, data/externos/diarios/,
   fuera del repositorio), con los 390 minutos de cada día rellenados por la forma de un
   día real de la serie Meta del profesor (sorteado; "molde", por defecto) o por un puente
   browniano ("browniano"), llevada de la apertura al cierre y estirada para que llegue a una fracción LAMBDA
   del exceso del máximo y del mínimo sobre la apertura y el cierre. LAMBDA = 0,89 es la
   mediana medida en la serie Meta del profesor contra los diarios de los mismos días
   (los cierres por minuto no llegan a los extremos de las operaciones). Los saltos de
   apertura, la tendencia de varios días y el día en que cae cada extremo son reales;
   la forma dentro del día es del modelo.
2. "meta_dias": días completos de la serie Meta del profesor (en dólares, deshaciendo su
   normalización: precio = (p + 309,57) / 2,3866, ajustado con los cierres diarios),
   sorteados con reposición y encadenados por sus retornos, con su salto de apertura.

Las ventanas se cortan de esas series y se normalizan como las del profesor (mínimo a
100, máximo a 255, comun.normalizar).
"""
import csv
import datetime as dt
import math
import os
import random

import comun

EMPRESAS = ("META", "AAPL", "NFLX", "AMD", "TSLA")
LAMBDA = 0.89
A_META, B_META = 2.3866, -309.57


def diarios(ticker):
    ruta = os.path.join(comun.RAIZ, "data", "externos", "diarios", f"{ticker}.csv")
    out = []
    for r in csv.DictReader(open(ruta)):
        out.append((dt.date.fromisoformat(r["fecha"]), float(r["apertura"]), float(r["maximo"]),
                    float(r["minimo"]), float(r["cierre"])))
    return out


def dia_puente(o, h, l, c, rng, lam=LAMBDA, n=390):
    """390 cierres por minuto de un día: puente de o a c que llega cerca de h y l."""
    w, ws = 0.0, [0.0]
    for _ in range(n - 1):
        w += rng.gauss(0, 1)
        ws.append(w)
    s = (h - l) / math.sqrt(n) if h > l else 0.0
    x = [o + (c - o) * m / (n - 1) + s * (ws[m] - ws[-1] * m / (n - 1)) for m in range(n)]
    top, bot = max(o, c), min(o, c)
    hh, ll = top + lam * (h - top), bot - lam * (bot - l)
    mx, mn = max(x), min(x)
    for m in range(n):
        if x[m] > top and mx > top:
            x[m] = top + (x[m] - top) * (hh - top) / (mx - top)
        elif x[m] < bot and mn < bot:
            x[m] = bot - (bot - x[m]) * (bot - ll) / (bot - mn)
    return x


_MOLDES = None


def moldes():
    """Los 51 días completos de la serie Meta, cada uno relativo a su primer minuto."""
    global _MOLDES
    if _MOLDES is None:
        P = meta_real()
        _MOLDES = [[v / P[40 + 390 * j] for v in P[40 + 390 * j:40 + 390 * (j + 1)]] for j in range(51)]
    return _MOLDES


def dia_molde(o, h, l, c, rng, lam=LAMBDA, n=390):
    """Como dia_puente, pero la forma del día es la de un día real de la serie Meta
    (sorteado), llevada de o a c y estirada hacia h y l."""
    y = rng.choice(moldes())
    x = [o * v for v in y]
    x = [v - (x[-1] - c) * m / (n - 1) for m, v in enumerate(x)]       # termina en c
    top, bot = max(o, c), min(o, c)
    hh, ll = top + lam * (h - top), bot - lam * (bot - l)
    mx, mn = max(x), min(x)
    for m in range(n):
        if x[m] > top and mx > top:
            x[m] = top + (x[m] - top) * (hh - top) / (mx - top)
        elif x[m] < bot and mn < bot:
            x[m] = bot - (bot - x[m]) * (bot - ll) / (bot - mn)
    return x


def puente(ticker, semilla, forma="molde"):
    """Serie por minuto de un ticker: (precios, fecha de cada minuto). forma: "molde"
    (días reales de Meta, por defecto) o "browniano"."""
    rng = random.Random(f"{ticker}-{semilla}")
    f = dia_molde if forma == "molde" else dia_puente
    precios, fechas = [], []
    for fecha, o, h, l, c in diarios(ticker):
        precios += f(o, h, l, c, rng)
        fechas += [fecha] * 390
    return precios, fechas


def meta_real():
    """La serie Meta del profesor en dólares y los índices de sus días completos."""
    import cotas
    p = cotas.leer(os.path.join(comun.RAIZ, "data", "practica_meta.csv"))
    return [(x - B_META) / A_META for x in p]


def meta_dias(rng, largo):
    """Días completos de la serie Meta, sorteados y encadenados por sus retornos."""
    P = meta_real()
    dias = [P[40 + 390 * j - 1:40 + 390 * (j + 1)] for j in range(51)]   # cierre anterior + 390 minutos
    x = [100.0]
    while len(x) < largo:
        d = rng.choice(dias)
        for a, b in zip(d, d[1:]):
            x.append(x[-1] * b / a)
    return x[:largo]


def ventanas(precios, largo, cantidad, rng, fechas=None, filtro=None):
    """Ventanas al azar de `largo` minutos, normalizadas. Con `filtro(fecha_inicio, fecha_fin)`
    solo se aceptan las que cumplen la condición."""
    out, intentos = [], 0
    while len(out) < cantidad and intentos < 100 * cantidad:
        intentos += 1
        i = rng.randrange(0, len(precios) - largo)
        if filtro and fechas and not filtro(fechas[i], fechas[i + largo - 1]):
            continue
        out.append(comun.normalizar(precios[i:i + largo]))
    return out
