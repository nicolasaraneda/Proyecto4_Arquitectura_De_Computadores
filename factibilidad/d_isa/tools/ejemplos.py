#!/usr/bin/env python3
"""ejemplos.py: un ejemplo numérico de cada instrucción de la extensión.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Imprime, para cada instrucción de custom-0, la palabra codificada y el
resultado que entrega el modelo ref/xd.py con operandos de ejemplo. Son los
ejemplos que cita ESPECIFICACION.md. Antes de imprimir comprueba que la
palabra, pasada por xd.ejecutar, entrega el mismo resultado.

    python3 tools/ejemplos.py > mediciones/ejemplos.txt      (make ejemplos)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ref"))
import xd  # noqa: E402

M32 = xd.M32
A, B = 0x10FF8001, 0x20017F02          # operandos de los carriles


def h(x):
    return f"0x{x & M32:08x}"


def fila(texto, palabra, rs1, rs2, esperado, nota):
    obtenido = xd.ejecutar(palabra, rs1 & M32, rs2 & M32)
    assert obtenido == esperado & M32, (texto, h(obtenido), h(esperado))
    print(f"{texto:<24} {h(palabra)}  rs1 = {h(rs1)}  rs2 = {h(rs2)}  rd = {h(esperado)}  {nota}")


def main():
    print("Un ejemplo de cada instrucción de la extensión en custom-0")
    print("Generado por factibilidad/d_isa/tools/ejemplos.py (make ejemplos). No editar a mano.")
    print()
    print("Media exponencial: precio p = 100 y media 102, o sea S = 32 * 102 = 3264 (k = 5)")
    p, s = 100, 3264
    dev = (32 * p - s) & M32
    fila("ema x3, x10, x3, 5", xd.codificar("ema", 3, 10, 3, k=5), 32 * p, s, xd.ema(32 * p, s, 5),
         f"S nueva = {xd.ema(32 * p, s, 5)}")
    fila("devk x6, x5, x3, 5", xd.codificar("devk", 6, 5, 3, k=5), p, s, dev,
         f"dev = {xd.s32(dev)}")
    fila("emad x3, x6, x3, 5", xd.codificar("emad", 3, 6, 3, k=5), dev, s, xd.emad(dev, s, 5),
         f"S nueva = {xd.emad(dev, s, 5)}")
    fila("srak x7, x6, 5", xd.codificar("srak", 7, 6, 0, k=5), dev, 0, xd.srak(dev, 5),
         f"{xd.s32(dev)} >>> 5 = {xd.s32(xd.srak(dev, 5))}")
    assert xd.ema(32 * p, s, 5) == xd.emad(dev, s, 5) == 3262

    print()
    print("Carriles de 4 x 8 bits")
    for nombre, op in xd.CARRILES.items():
        if nombre == "pbcast8":
            fila("pbcast8 x7, x8", xd.codificar(nombre, 7, 8), 0x12345664, 0, 0x64646464,
                 "el precio 100 en los cuatro carriles")
        elif nombre == "pmovmsk8":
            fila("pmovmsk8 x7, x8", xd.codificar(nombre, 7, 8), 0xFF0000FF, 0, 0b1001,
                 "un bit por carril: 1001")
        else:
            fila(f"{nombre} x7, x8, x9", xd.codificar(nombre, 7, 8, 9), A, B, xd.simd8(op, A, B), "")

    print()
    print("Producto y cociente")
    fila("mulstep x7, x7, x8", xd.codificar("mulstep", 7, 7, 8), 0xC0000000, 1000,
         xd.mulstep(0xC0000000, 1000), "un paso: sale un 1 del multiplicador y se suma rs2")
    x = 63 << 24
    for _ in range(8):
        x = xd.mulstep(x, 255)
    assert x == 63 * 255
    print(f"{'8 veces mulstep':<24} {'':10}  rs1 = {h(63 << 24)}  rs2 = {h(255)}  rd = {h(x)}  "
          f"63 acciones a 255: {x}")
    n, d = 10000 - 5, 180
    fila("divstep x7, x7, x8", xd.codificar("divstep", 7, 7, 8), n, d, xd.divstep(n, d),
         "un paso con N = 9995 y D = 180")
    y = n
    for _ in range(8):
        y = xd.divstep(y, d)
    assert (y & 0xFF, y >> 8) == (n // d, n % d)
    print(f"{'8 veces divstep':<24} {'':10}  rs1 = {h(n)}  rs2 = {h(d)}  rd = {h(y)}  "
          f"(10000 - 5) / 180: cociente {y & 0xFF} y resto {y >> 8}")
    fila("mulc x7, x7, x8", xd.codificar("mulc", 7, 7, 8), 63, 255, xd.mulc(63, 255),
         f"63 * 255 = {xd.mulc(63, 255)}")

    print()
    print("Periférico multiplicador serial (MMIO, base 0x8002_0000)")
    m = xd.MulMMIO()
    m.flanco(req=True, we=True, off=0, wdata=1000)
    m.flanco(req=True, we=True, off=1, wdata=255)
    for i in range(7):
        m.flanco()
    temprana = m.flanco(req=True, off=2)
    lista = m.flanco(req=True, off=2)
    assert lista == 255000 and temprana != lista
    print(f"MULA = 1000, MULB = 255: MULP leído 8 ciclos después de escribir MULB = {temprana} (falta un paso), "
          f"9 ciclos después = {lista}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
