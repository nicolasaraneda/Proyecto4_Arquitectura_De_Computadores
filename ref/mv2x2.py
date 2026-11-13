#!/usr/bin/env python3
"""mv2x2.py: modelo de referencia del producto 2x2 en punto fijo (instrucción kal2).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El estimador de dos estados separa el precio en un nivel lento m y una
componente transitoria u. Su filtro de Kalman en estado estacionario es

    e  = p - m - phi u                 (innovación)
    m' = m + k1 e
    u' = phi u + k2 e

Con d = p - m, eso es un producto de una matriz 2x2 por un vector:

    [ m' - m ]   [ k1    -k1 phi      ] [ d ]
    [ u'     ] = [ k2    phi (1 - k2) ] [ u ]

Este archivo define esa operación en enteros, que es lo que tiene que calcular
el hardware bit a bit (docs/producto_2x2.md):

    estado  rs1 = {u[15:0], m[15:0]}   m sin signo Q8.8, u con signo Q7.8
    precio  rs2[7:0]
    d       = (p << 8) - m
    dm      = (g00 d + g01 u) >> S     (desplazamiento aritmético: piso)
    un      = (g10 d + g11 u) >> S
    m'      = saturar(m + dm, 0, 65535)
    u'      = saturar(un, -32768, 32767)
    rd      = {u', m'}

Los g son enteros con S bits de fracción. La versión de coeficientes fijos
(rtl/exhibicion/kal2_fijo.v, generada por tools/gen_mv2x2.py) y la versión con
multiplicadores (rtl/exhibicion/mv2x2_mult.v) calculan exactamente esto.

Uso:
    python3 ref/mv2x2.py                    # ganancias y matriz del ejemplo
    python3 ref/mv2x2.py --vectores N -o f  # vectores de prueba para el testbench
    python3 ref/mv2x2.py --g 91 -82 157 89 --s 8 --vectores N -o f
"""
import argparse
import random
import sys

F = 8            # bits de fracción de m y de u
ANCHO = 16       # ancho de cada carril


def ganancia_estacionaria(phi, q_m, q_u, r, iteraciones=5000):
    """Ganancia de Kalman en estado estacionario del modelo de dos estados.

    Estado x = [m, u]. m es un paseo aleatorio con varianza q_m por tick y u un
    AR(1) con coeficiente phi y varianza de innovación q_u. Se observa
    p = m + u + ruido de varianza r (el redondeo a enteros aporta 1/12).
    Devuelve (k1, k2). Itera la ecuación de Riccati con matrices de 2x2 a mano.
    """
    # P es la covarianza de la predicción, simétrica: [[a, b], [b, c]]
    a, b, c = q_m + 1.0, 0.0, q_u + 1.0
    for _ in range(iteraciones):
        s = a + 2 * b + c + r                    # varianza de la innovación
        k1, k2 = (a + b) / s, (b + c) / s
        # covarianza después de medir: (I - K H) P
        a2 = a - k1 * (a + b)
        b2 = b - k1 * (b + c)
        c2 = c - k2 * (b + c)
        # predicción: F P F' + Q, con F = diag(1, phi)
        a, b, c = a2 + q_m, phi * b2, phi * phi * c2 + q_u
    s = a + 2 * b + c + r
    return (a + b) / s, (b + c) / s


def matriz(phi, k1, k2):
    """Matriz G (números reales) que lleva [d, u] a [m' - m, u']."""
    return [[k1, -k1 * phi], [k2, phi * (1 - k2)]]


def cuantizar(g, s):
    """Redondea cada coeficiente a un entero con s bits de fracción."""
    return [[int(round(x * (1 << s))) for x in fila] for fila in g]


def csd(n):
    """Dígitos con signo canónicos de n: lista de (signo, desplazamiento).

    Es la forma con menos términos distintos de cero. Cada término es una suma
    o una resta de la entrada desplazada: 7 = 8 - 1 usa 2 términos y no 3.
    """
    terminos, i, neg = [], 0, n < 0
    n = abs(n)
    while n:
        if n & 1:
            dig = 2 - (n & 3)                    # +1 si termina en 01, -1 si termina en 11
            terminos.append((-dig if neg else dig, i))
            n -= dig
        n >>= 1
        i += 1
    return terminos


def terminos_csd(gi):
    """Cantidad total de términos de la matriz entera gi."""
    return sum(len(csd(x)) for fila in gi for x in fila)


def _signo16(x):
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


def paso(estado, precio, gi, s):
    """Un paso del estimador. `estado` y el resultado son palabras de 32 bits."""
    m = estado & 0xFFFF
    u = _signo16(estado >> 16)
    d = ((precio & 0xFF) << F) - m
    dm = (gi[0][0] * d + gi[0][1] * u) >> s      # >> de Python: piso, igual que >>>
    un = (gi[1][0] * d + gi[1][1] * u) >> s
    m2 = min(max(m + dm, 0), 0xFFFF)
    u2 = min(max(un, -0x8000), 0x7FFF)
    return ((u2 & 0xFFFF) << 16) | m2


def desempaquetar(estado):
    """Devuelve (m, u) como números reales."""
    return (estado & 0xFFFF) / (1 << F), _signo16(estado >> 16) / (1 << F)


def vectores(n, gi, s, semilla=1):
    """Vectores de prueba: esquinas, estados al azar y una trayectoria."""
    rng = random.Random(semilla)
    esquinas_m = [0, 1, 0x00FF, 0x0100, 0x7FFF, 0x8000, 0xFF00, 0xFFFF]
    esquinas_u = [0, 1, 0xFFFF, 0x7FFF, 0x8000, 0x8001, 0x0100, 0xFF00]
    casos = [((u << 16) | m, p) for m in esquinas_m for u in esquinas_u for p in (0, 1, 127, 128, 254, 255)]
    while len(casos) < n // 2:
        casos.append((rng.getrandbits(32), rng.getrandbits(8)))
    estado, p = 100 << F, 100                    # trayectoria: el estado realimentado
    while len(casos) < n:
        p = min(255, max(1, p + rng.choice((-3, -1, -1, 0, 0, 1, 1, 3))))
        casos.append((estado, p))
        estado = paso(estado, p, gi, s)
    return [(e, p, paso(e, p, gi, s)) for e, p in casos]


# Parámetros de ejemplo: los de la familia dos_componentes de ref/series.py,
# que están puestos a mano. Los definitivos salen de la calibración del frente A.
EJEMPLO = dict(phi=0.9, q_m=0.6 ** 2, q_u=1.5 ** 2, r=1.0 / 12)
S_EJEMPLO = 8


def main(argv=None):
    ap = argparse.ArgumentParser(description="Modelo del producto 2x2 en punto fijo")
    ap.add_argument("--phi", type=float, default=EJEMPLO["phi"])
    ap.add_argument("--q-m", type=float, default=EJEMPLO["q_m"])
    ap.add_argument("--q-u", type=float, default=EJEMPLO["q_u"])
    ap.add_argument("--r", type=float, default=EJEMPLO["r"])
    ap.add_argument("--s", type=int, default=S_EJEMPLO, help="bits de fracción de los coeficientes")
    ap.add_argument("--g", type=int, nargs=4, metavar=("G00", "G01", "G10", "G11"),
                    help="matriz entera a mano (con --s), en vez de calcularla del modelo")
    ap.add_argument("--vectores", type=int, default=0, help="escribir N vectores de prueba")
    ap.add_argument("-o", "--salida")
    a = ap.parse_args(argv)

    k1, k2 = ganancia_estacionaria(a.phi, a.q_m, a.q_u, a.r)
    g = matriz(a.phi, k1, k2)
    gi = [a.g[:2], a.g[2:]] if a.g else cuantizar(g, a.s)
    if a.vectores:
        with open(a.salida, "w", newline="\n") as f:
            for e, p, y in vectores(a.vectores, gi, a.s):
                f.write(f"{e:08x}{p:02x}{y:08x}\n")
        return 0
    print(f"phi = {a.phi}, q_m = {a.q_m:.4f}, q_u = {a.q_u:.4f}, r = {a.r:.4f}")
    print(f"Ganancias en estado estacionario: k1 = {k1:.5f}, k2 = {k2:.5f}")
    print("Matriz G (real):   " + "  ".join(f"[{x:+.5f} {y:+.5f}]" for x, y in g))
    print(f"Matriz G x 2^{a.s}:    " + "  ".join(f"[{x:+d} {y:+d}]" for x, y in gi))
    print(f"Términos en dígitos con signo canónicos: {terminos_csd(gi)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
