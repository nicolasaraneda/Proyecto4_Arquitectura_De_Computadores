#!/usr/bin/env python3
"""optimo_placa.py: aritmética de la política óptima en la placa, solo con sumas, restas y comparaciones.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

La ALU de competencia no desplaza ni multiplica (rtl/espino_core/espino_alu.v). El hilo 3 del
reparto pedido el 19/11 lleva la caja y las acciones propias y calcula la cantidad de la próxima
orden; para eso necesita, sin dividir ni multiplicar:

  producto(q, p, bits)      q * p por Horner con duplicaciones (x + x): un paso por bit de q
  cociente(x, d, bits)      min(2^bits - 1, floor(x / d)) por división con restas: se arman
                            d, 2d, 4d, ... por sumas y se resta de mayor a menor
  maxima_compra(caja, p)    min(63, floor((caja - 5) / p)): el recorte de la maestra
  media(caja, acc, p)       floor((caja + acc * p) / (2 p)): la media posición de la referencia
  clase(S2, nd)             la clase de placa: 64 S2 por seis duplicaciones contra N_j (t - 1)

Cada función cuenta sus operaciones (sumas, restas, comparaciones y saltos tomados como una
instrucción cada una; cargas de constantes aparte), para estimar instrucciones por tick.

Uso: python3 ref/cotas/optimo_placa.py   (pruebas exhaustivas contra la aritmética de Python)
"""
import sys


def producto(q, p, bits):
    """Horner: r = 0; por cada bit de q del más alto al más bajo: r = r + r; si el bit: r = r + p.
    Los bits de q se sacan comparando con potencias de dos guardadas en una tabla (sin desplazar)."""
    pot = [1 << k for k in range(bits)]          # tabla en memoria
    r, resto, ops = 0, q, 0
    for k in range(bits - 1, -1, -1):
        r = r + r
        ops += 1
        ops += 2                                  # carga de la potencia y comparación
        if resto >= pot[k]:
            resto -= pot[k]
            r = r + p
            ops += 2
    return r, ops


def cociente(x, d, bits):
    """División con restas: m_k = d 2^k por sumas sucesivas, después de mayor a menor."""
    m = [d]
    ops = 0
    for _ in range(bits - 1):
        m.append(m[-1] + m[-1])
        ops += 1
    pot = [1 << k for k in range(bits)]
    q, ops = 0, ops
    for k in range(bits - 1, -1, -1):
        ops += 2                                  # comparación y salto
        if x >= m[k]:
            x -= m[k]
            q += pot[k]
            ops += 3                              # resta, carga de la potencia y suma
    return q, ops


def maxima_compra(caja, p):
    x = caja - 5
    if x < 0:
        return 0, 2
    q, ops = cociente(x, p, 6)                    # con 6 bits sale 63 si el cociente es 64 o más
    return q, ops + 2


def media(caja, acc, p):
    ap, o1 = producto(acc, p, 9)                  # acc < 512
    w = caja + ap
    q, o2 = cociente(w, p + p, 9)                 # cociente < 512
    return q, o1 + o2 + 2


N64 = (11, 20, 28, 39, 55, 78, 111)


def clase(S2, nd):
    a = S2
    for _ in range(6):
        a = a + a
    j = 0
    while j < 7 and a >= N64[j] * nd:             # en la placa, N_j (t - 1) es una suma corrida (+N_j por tick)
        j += 1
    return j


def pruebas():
    import optimo_estrategia as OE
    mal, peor = 0, {"producto6": 0, "producto9": 0, "maxima": 0, "media": 0}
    for p in range(100, 256):
        for q in range(64):
            r, o = producto(q, p, 6)
            mal += r != q * p
            peor["producto6"] = max(peor["producto6"], o)
        for a in range(512):
            r, o = producto(a, p, 9)
            mal += r != a * p
            peor["producto9"] = max(peor["producto9"], o)
        for caja in range(0, 40001, 3):
            r, o = maxima_compra(caja, p)
            mal += r != max(0, min(63, (caja - 5) // p))
            peor["maxima"] = max(peor["maxima"], o)
    n = 0
    for p in range(100, 256):
        for caja in range(0, 30001, 97):
            for acc in range(0, 300, 7):
                w = caja + acc * p
                if w // (2 * p) >= 512:
                    continue
                r, o = media(caja, acc, p)
                mal += r != w // (2 * p)
                peor["media"] = max(peor["media"], o)
                n += 1
    for S2 in range(0, 20000, 13):
        for nd in range(389, 20000, 211):
            mal += clase(S2, nd) != OE.clase_placa(S2, nd)
    print(f"diferencias con la aritmética exacta: {mal}; operaciones en el peor caso: {peor}; casos de media: {n}")
    return mal, peor


if __name__ == "__main__":
    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
    pruebas()
