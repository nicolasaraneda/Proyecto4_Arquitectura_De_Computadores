#!/usr/bin/env python3
"""xd.py: modelo de referencia de la extensión de la ISA en custom-0.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Es la definición ejecutable de docs/extension_isa.md. Si el texto y este
modelo no coinciden, manda el modelo: contra él se generan los vectores del
testbench de los módulos (tb/xd/tb_xd_mod.sv).

    python3 ref/xd.py              autoprueba
    python3 ref/xd.py --tabla      tabla de codificaciones y ejemplos
    python3 ref/xd.py --vectores N SEMILLA   vectores para tb/xd/tb_xd_mod.sv

Las tres instrucciones son de formato R en el opcode custom-0 (0001011):

    emad rd, rs1, rs2, 5    funct3 100, funct7 0000101   rd = rs2 + (rs1 >>> 5)
    devk rd, rs1, rs2, 5    funct3 101, funct7 0000101   rd = (rs1 << 5) - rs2
    mulstep rd, rs1, rs2    funct3 010, funct7 0000000   rd = (rs1 << 1) + (rs1[31] ? rs2 : 0)

Todo es aritmética de 32 bits que da la vuelta. Los valores se manejan como
enteros sin signo entre 0 y 2^32 - 1.
"""
import random
import sys

M32 = 0xFFFFFFFF
OPCODE_CUSTOM0 = 0x0B
K = 5                                    # el único k que implementa el hardware
F3 = {"emad": 0b100, "devk": 0b101, "mulstep": 0b010}
F7 = {"emad": K, "devk": K, "mulstep": 0}
BIT = {"emad": 0, "devk": 1, "mulstep": 2}   # bit de la máscara Xd del RTL


def con_signo(x):
    x &= M32
    return x - (1 << 32) if x & 0x80000000 else x


def emad(rs1, rs2):
    """rd = rs2 + (rs1 >>> 5): paso de media exponencial desde la desviación."""
    return (rs2 + (con_signo(rs1) >> K)) & M32


def devk(rs1, rs2):
    """rd = (rs1 << 5) - rs2: desviación de una muestra respecto de un estado por 32."""
    return ((rs1 << K) - rs2) & M32


def mulstep(rs1, rs2):
    """rd = (rs1 << 1) + (rs1[31] ? rs2 : 0): un paso de multiplicación."""
    return ((rs1 << 1) + (rs2 if rs1 & 0x80000000 else 0)) & M32


FUNC = {"emad": emad, "devk": devk, "mulstep": mulstep}


def codificar(nombre, rd, rs1, rs2):
    """Palabra de 32 bits de la instrucción."""
    for r in (rd, rs1, rs2):
        if not 0 <= r <= 15:
            raise ValueError("RV32E solo tiene x0 a x15")
    return (F7[nombre] << 25) | (rs2 << 20) | (rs1 << 15) | (F3[nombre] << 12) | (rd << 7) | OPCODE_CUSTOM0


def decodificar(palabra, mascara=7):
    """Nombre de la instrucción, o None si la palabra no es una de las tres
    (el core la trata como ilegal y no hace nada). mascara es el subconjunto
    presente en el hardware: bit 0 emad, bit 1 devk y bit 2 mulstep."""
    if palabra & 0x7F != OPCODE_CUSTOM0:
        return None
    f3, f7 = (palabra >> 12) & 7, (palabra >> 25) & 0x7F
    for nombre in F3:
        if f3 == F3[nombre] and f7 == F7[nombre] and (mascara >> BIT[nombre]) & 1:
            return nombre
    return None


def producto(a, b, pasos=8):
    """a * b con `pasos` instrucciones mulstep: a es el multiplicador (cabe en
    `pasos` bits) y b el multiplicando (menor que 2^(32 - pasos))."""
    x = (a << (32 - pasos)) & M32
    for _ in range(pasos):
        x = mulstep(x, b)
    return x


def autoprueba():
    rng = random.Random(2026)
    n = 0
    esquinas = [0, 1, 2, 31, 32, 33, 0x7FFFFFFF, 0x80000000, 0x80000001, 0xFFFFFFFF, 0xFFFFFFE0, 0xFFFFFFDF,
                0x04000000, 0x03FFFFFF, 0x55555555, 0xAAAAAAAA]
    valores = esquinas + [rng.getrandbits(32) for _ in range(400)]
    for a in valores:
        for b in valores:
            # Las mismas fórmulas escritas de otra manera
            sa = con_signo(a)
            assert emad(a, b) == (b + (sa // 32)) % (1 << 32)
            assert devk(a, b) == (a * 32 - b) % (1 << 32)
            assert mulstep(a, b) == (2 * a + (b if a >> 31 else 0)) % (1 << 32)
            n += 3
    # La regla de sw/trade.s: dev = 32 p - S y S = S + (dev >>> 5), con S por 32
    for _ in range(20000):
        p, s = rng.randint(1, 255), rng.randint(32, 8160)
        dev = devk(p, s)
        assert con_signo(dev) == 32 * p - s
        s2 = emad(dev, s)
        assert s2 == s + ((32 * p - s) >> 5)
        n += 2
    # Ocho pasos de mulstep: exhaustivo con multiplicando de 8 bits y al azar con 24
    for a in range(256):
        for b in range(256):
            assert producto(a, b) == a * b
            n += 1
    for _ in range(50000):
        a, b = rng.getrandbits(8), rng.getrandbits(24)
        assert producto(a, b) == a * b
        n += 1
    for _ in range(20000):
        a, b = rng.getrandbits(6), rng.getrandbits(26)
        assert producto(a, b, 6) == a * b
        n += 1
    # Codificación: las palabras de la especificación y la ida y vuelta
    assert codificar("emad", 3, 6, 3) == 0x0A33418B
    assert codificar("devk", 6, 5, 3) == 0x0A32D30B
    assert codificar("mulstep", 7, 7, 8) == 0x0083A38B
    for nombre in F3:
        for rd in range(16):
            for rs1 in range(16):
                for rs2 in range(16):
                    w = codificar(nombre, rd, rs1, rs2)
                    assert decodificar(w) == nombre
                    assert decodificar(w, 7 & ~(1 << BIT[nombre])) is None
                    n += 2
    # Ninguna otra palabra de custom-0 es una instrucción
    validas = {(F3[x], F7[x]) for x in F3}
    for f3 in range(8):
        for f7 in range(128):
            w = (f7 << 25) | (f3 << 12) | OPCODE_CUSTOM0
            assert (decodificar(w) is not None) == ((f3, f7) in validas)
            n += 1
    print(f"PASS ref/xd.py: {n} comprobaciones")


def tabla():
    print("Extension de la ISA en custom-0: codificacion y ejemplos")
    print("Generado por ref/xd.py --tabla (make xd-tabla). No editar a mano.")
    print()
    print("Formato R, opcode custom-0 = 0001011 (0x0B):")
    print("  bits 31:25 funct7 | 24:20 rs2 | 19:15 rs1 | 14:12 funct3 | 11:7 rd | 6:0 opcode")
    print()
    print("Instruccion            funct3  funct7   Resultado")
    print("emad rd, rs1, rs2, 5   100     0000101  rd = rs2 + (rs1 >>> 5)")
    print("devk rd, rs1, rs2, 5   101     0000101  rd = (rs1 << 5) - rs2")
    print("mulstep rd, rs1, rs2   010     0000000  rd = (rs1 << 1) + (rs1[31] ? rs2 : 0)")
    print()
    print("Ejemplos:")
    ej = [("emad", 3, 6, 3, 0xFFFFFFC0, 3264, "emad x3, x6, x3, 5"),
          ("emad", 3, 6, 3, 100, 3264, "emad x3, x6, x3, 5"),
          ("devk", 6, 5, 3, 100, 3264, "devk x6, x5, x3, 5"),
          ("devk", 6, 5, 3, 105, 3264, "devk x6, x5, x3, 5"),
          ("mulstep", 7, 7, 8, 0xC0000000, 1000, "mulstep x7, x7, x8"),
          ("mulstep", 7, 7, 8, 0x40000000, 1000, "mulstep x7, x7, x8")]
    for nombre, rd, rs1, rs2, a, b, texto in ej:
        r = FUNC[nombre](a, b)
        print(f"  {texto:<20} .word 0x{codificar(nombre, rd, rs1, rs2):08x}   rs1 = 0x{a:08x} ({con_signo(a)}), "
              f"rs2 = 0x{b:08x} ({con_signo(b)})  ->  rd = 0x{r:08x} ({con_signo(r)})")
    print()
    print("Ocho pasos de mulstep con rs1 = 63 << 24 y rs2 = 255:")
    x = 63 << 24
    for i in range(8):
        x = mulstep(x, 255)
        print(f"  paso {i + 1}: 0x{x:08x}")
    print(f"  resultado: {x} = 63 * 255")


def vectores(n, semilla):
    """Líneas "nombre_en_bits rs1 rs2 resultado" en hexadecimal, para $readmemh:
    cada vector son cuatro palabras (instrucción 0 emad, 1 devk, 2 mulstep)."""
    rng = random.Random(semilla)
    esquinas = [0, 1, 31, 32, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFFE0, 0x04000000, 0x03FFFFFF]
    val = lambda: rng.choice([rng.getrandbits(32), rng.getrandbits(32), rng.choice(esquinas),
                              rng.randint(0, 8160), (-rng.randint(1, 8160)) & M32])
    for i in range(n):
        nombre = ("emad", "devk", "mulstep")[i % 3]
        a, b = val(), val()
        print(f"{BIT[nombre]:08x} {a:08x} {b:08x} {FUNC[nombre](a, b):08x}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--tabla":
        tabla()
    elif len(sys.argv) > 1 and sys.argv[1] == "--vectores":
        vectores(int(sys.argv[2]), int(sys.argv[3]))
    else:
        autoprueba()
