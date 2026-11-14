#!/usr/bin/env python3
"""gen_vectores.py: vectores de prueba de la extensión de la ISA (pieza D).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Escribe los archivos que leen los testbenches de factibilidad/d_isa/tb/. Los
valores esperados salen del modelo de referencia ref/xd.py. Formato de los
módulos combinacionales, una línea por vector, en hexadecimal:

    <a> <b> <selector> <pasos> <esperado>

`selector` es k (ema, srak) o el número de operación (carriles). `pasos` es
cuántas veces se aplica el módulo realimentando su salida en `a`: 1 para un
paso suelto, 8 o 16 para un producto o un cociente completo.

Para el periférico multiplicador, una línea por ciclo:

    <req> <we> <off> <wdata> <rdata esperado después del flanco>

Uso:
    python3 tools/gen_vectores.py MODULO SALIDA [opciones]
    MODULO: ema, ema_dominio, srak, simd, mulstep, divstep, mulc, mmio, opa, opa_dominio
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ref"))
import xd  # noqa: E402

ESQUINAS = [0, 1, 2, 31, 32, 33, 0x7F, 0x80, 0xFF, 0x100, 0x7FFF, 0x8000, 0xFFFF, 0x10000,
            0x00FFFFFF, 0x01000000, 0x7FFFFFFF, 0x80000000, 0x80000001, 0xFFFFFFFE, 0xFFFFFFFF,
            0x55555555, 0xAAAAAAAA, 0x01010101, 0x80808080, 0x7F7F7F7F, 0xFF00FF00, 0x00FF00FF]


def conjunto_k(kb):
    return {0: [5], 2: [4, 5, 6, 7], 3: list(range(8)), 5: list(range(32))}[kb]


def pares(rng, n):
    """Pares de operandos: todas las esquinas cruzadas y n al azar."""
    for a in ESQUINAS:
        for b in ESQUINAS:
            yield a, b
    for _ in range(n):
        a, b = rng.getrandbits(32), rng.getrandbits(32)
        modo = rng.randrange(4)
        if modo == 1:                      # valores cercanos: diferencias chicas con signo
            b = (a + rng.randrange(-300, 300)) & xd.M32
        elif modo == 2:                    # el rango de trade.s: S y 32 p
            a, b = rng.randrange(32, 8161), 32 * rng.randrange(1, 256)
        yield a, b


def gen_ema(f, a):
    rng = random.Random(a.semilla)
    n = 0
    for k in conjunto_k(a.kb):
        for x, y in pares(rng, a.n):
            f.write(f"{x:08x} {y:08x} {k:02x} 1 {xd.ema(x, y, k):08x}\n")
            n += 1
    return n


def gen_ema_dominio(f, a):
    """Todo el dominio de la regla base: S entre 32 y 8160, precio entre 1 y 255, k = 5."""
    n = 0
    for s in range(32, 8161):
        for p in range(1, 256):
            f.write(f"{32 * p:08x} {s:08x} 05 1 {xd.ema(32 * p, s, 5):08x}\n")
            n += 1
    return n


def gen_opa(f, a):
    """mulstep, emad y devk por el camino de la ALU (xd_opa más un sumador).
    El selector lleva funct3 en los bits 7:5 y k en los bits 4:0."""
    rng = random.Random(a.semilla)
    n = 0
    for x, y in pares(rng, a.n):
        f.write(f"{x:08x} {y:08x} {(2 << 5):02x} 1 {xd.mulstep(x, y):08x}\n")
        n += 1
    for q in range(256):
        for m in [0, 1, 63, 255, 0xFFFF, 0xFFFFFF] + [rng.getrandbits(24) for _ in range(10)]:
            f.write(f"{q << 24:08x} {m:08x} {(2 << 5):02x} 8 {q * m:08x}\n")
            n += 1
    for k in conjunto_k(a.kb):
        for x, y in pares(rng, a.n):
            f.write(f"{x:08x} {y:08x} {(4 << 5) | k:02x} 1 {xd.emad(x, y, k):08x}\n")
            f.write(f"{x:08x} {y:08x} {(5 << 5) | k:02x} 1 {xd.devk(x, y, k):08x}\n")
            n += 2
    return n


def gen_opa_dominio(f, a):
    """Todo el dominio de la regla base con devk y emad, k = 5: para cada
    media S y cada precio p, la desviación 32 p - S y la media nueva."""
    n = 0
    for s in range(32, 8161):
        for p in range(1, 256):
            dev = xd.devk(p, s, 5)
            f.write(f"{p:08x} {s:08x} {(5 << 5) | 5:02x} 1 {dev:08x}\n")
            f.write(f"{dev:08x} {s:08x} {(4 << 5) | 5:02x} 1 {xd.ema(32 * p, s, 5):08x}\n")
            n += 2
    return n


def gen_srak(f, a):
    rng = random.Random(a.semilla)
    n = 0
    for k in conjunto_k(a.kb):
        for x, _ in pares(rng, a.n):
            f.write(f"{x:08x} 00000000 {k:02x} 1 {xd.srak(x, k):08x}\n")
            n += 1
    return n


def gen_simd(f, a):
    """Exhaustivo por carril: cada carril recorre los 65 536 pares (a, b) de
    cada operación, con una permutación distinta en cada carril para que un
    acarreo entre carriles no pase inadvertido."""
    rng = random.Random(a.semilla)
    m = a.mascara
    ops = [0, 1, 2]
    ops += [3] if m & 1 else []
    ops += [4, 5] if m & 2 else []
    ops += [6, 7] if m & 4 else []
    ops += [8] if m & 8 else []
    ops += [9] if m & 16 else []
    modelo = xd.simd8_bit if m & 32 else xd.simd8
    n = 0
    for op in ops:
        for i in range(65536):
            idx = [i, ((i & 0xFF) << 8) | (i >> 8), (i * 40503 + 12345) & 0xFFFF, (i * 25173 + 13849) & 0xFFFF]
            x = xd.empaquetar([j & 0xFF for j in idx])
            y = xd.empaquetar([j >> 8 for j in idx])
            f.write(f"{x:08x} {y:08x} {op:02x} 1 {modelo(op, x, y):08x}\n")
            n += 1
        for x, y in pares(rng, a.n):
            f.write(f"{x:08x} {y:08x} {op:02x} 1 {modelo(op, x, y):08x}\n")
            n += 1
    return n


def gen_mulstep(f, a):
    rng = random.Random(a.semilla)
    n = 0
    for x, y in pares(rng, a.n):
        f.write(f"{x:08x} {y:08x} 00 1 {xd.mulstep(x, y):08x}\n")
        n += 1
    # productos completos: todos los multiplicadores de 8 bits contra multiplicandos de borde y al azar
    for q in range(256):
        for m in [0, 1, 2, 63, 255, 256, 0xFFFF, 0x10000, 0xFFFFFF] + [rng.getrandbits(24) for _ in range(40)]:
            f.write(f"{q << 24:08x} {m:08x} 00 8 {q * m:08x}\n")
            n += 1
    # 8 x 8 exhaustivo (cantidad por precio)
    for q in range(256):
        for m in range(256):
            f.write(f"{q << 24:08x} {m:08x} 00 8 {q * m:08x}\n")
            n += 1
    # multiplicador de 16 bits, 16 pasos
    for _ in range(20000):
        q, m = rng.getrandbits(16), rng.getrandbits(16)
        f.write(f"{q << 16:08x} {m:08x} 00 10 {q * m:08x}\n")
        n += 1
    return n


def gen_divstep(f, a):
    rng = random.Random(a.semilla)
    n = 0
    for x, y in pares(rng, a.n):
        f.write(f"{x:08x} {y:08x} 00 1 {xd.divstep(x, y):08x}\n")
        n += 1
    # cocientes completos al azar, con N < 256 D
    for _ in range(a.n):
        d = rng.randrange(1, 1 << rng.randrange(1, 24))
        num = rng.randrange(0, min(256 * d, 1 << 31))
        f.write(f"{num:08x} {d:08x} 00 8 {((num % d) << 8) | (num // d):08x}\n")
        n += 1
    # el caso de la contabilidad: (caja - 5) / p con cociente menor que 64,
    # para todo precio y todo dividendo cuando p <= 16, y con paso 7 en el resto
    for p in range(1, 256):
        for num in range(0, 64 * p, 1 if p <= 16 else 7):
            f.write(f"{num:08x} {p:08x} 00 8 {((num % p) << 8) | (num // p):08x}\n")
            n += 1
    return n


def gen_mulc(f, a):
    rng = random.Random(a.semilla)
    n = 0
    if a.aw == 8:
        for x in range(256):
            for y in range(256):
                alto = rng.getrandbits(24) << 8
                f.write(f"{alto | x:08x} {alto ^ 0xABCDEF00 | y:08x} 00 1 {xd.mulc(x, y, 8):08x}\n")
                n += 1
    for x, y in pares(rng, a.n):
        f.write(f"{x:08x} {y:08x} 00 1 {xd.mulc(x, y, a.aw):08x}\n")
        n += 1
    return n


def gen_mmio(f, a):
    """Tráfico al azar por el bus, ciclo a ciclo, y productos dirigidos."""
    rng = random.Random(a.semilla)
    m = xd.MulMMIO()
    n = 0

    def ciclo(req=0, we=0, off=0, wdata=0):
        nonlocal n
        r = m.flanco(bool(req), bool(we), off, wdata)
        f.write(f"{req} {we} {off} {wdata:08x} {r:08x}\n")
        n += 1
        return r

    # productos dirigidos: escribir, esperar y leer. Con espera de 8 ciclos el
    # producto está listo; con menos, el modelo dice qué se lee.
    for i in range(3000):
        x, y = rng.getrandbits(24), rng.getrandbits(8)
        if i < 30:
            x, y = [0, 1, 0xFFFFFF][i % 3], [0, 1, 0xFF, 0x80, 63][i % 5]
        ciclo(1, 1, 0, x | (rng.getrandbits(8) << 24))
        ciclo(1, 1, 1, y | (rng.getrandbits(24) << 8))
        for _ in range(8):
            ciclo(1, 0, 3)                             # sondeo de BUSY
        assert ciclo(1, 0, 2) == x * y
        assert ciclo(1, 0, 3) == 0
    # tráfico al azar: incluye reescribir MULB con un producto en curso
    for _ in range(a.n):
        modo = rng.randrange(10)
        if modo < 4:
            ciclo()
        elif modo < 5:
            ciclo(1, 1, 0, rng.getrandbits(32))
        elif modo < 6:
            ciclo(1, 1, 1, rng.getrandbits(32))
        elif modo < 7:
            ciclo(1, 1, rng.randrange(2, 4), rng.getrandbits(32))    # escritura a un registro de solo lectura
        else:
            ciclo(1, 0, rng.randrange(4))
    return n


GENERADORES = dict(ema=gen_ema, ema_dominio=gen_ema_dominio, srak=gen_srak, simd=gen_simd,
                   mulstep=gen_mulstep, divstep=gen_divstep, mulc=gen_mulc, mmio=gen_mmio,
                   opa=gen_opa, opa_dominio=gen_opa_dominio)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Vectores de prueba de la extensión en custom-0")
    ap.add_argument("modulo", choices=sorted(GENERADORES))
    ap.add_argument("salida")
    ap.add_argument("--kb", type=int, default=0, help="ema, srak, emad y devk: 0, 2, 3 o 5")
    ap.add_argument("--mascara", type=int, default=31, help="carriles: opciones de xd_simd8")
    ap.add_argument("--aw", type=int, default=16, help="mulc: bits del multiplicando")
    ap.add_argument("--n", type=int, default=20000, help="vectores al azar")
    ap.add_argument("--semilla", type=int, default=1)
    a = ap.parse_args(argv)
    os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
    with open(a.salida, "w", newline="\n") as f:
        n = GENERADORES[a.modulo](f, a)
    print(f"{a.salida}: {n} vectores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
