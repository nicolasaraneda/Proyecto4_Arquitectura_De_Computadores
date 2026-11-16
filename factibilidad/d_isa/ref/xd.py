#!/usr/bin/env python3
"""xd.py: modelo de referencia de la extensión de la ISA en custom-0 (pieza D).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Es la definición ejecutable de cada instrucción propuesta. El RTL de
factibilidad/d_isa/rtl/ se compara contra estas funciones (tb/ y formal/), y
la especificación escrita está en ESPECIFICACION.md. Todos los valores son
enteros de Python entre 0 y 2^32 - 1 (el contenido de un registro).

Instrucciones, todas de un ciclo, sin estado y con formato R en custom-0
(opcode 0001011):

  funct3 = 000   ema       rd = rs2 + ((rs1 - rs2) >>> k), con k en funct7[4:0]
                           (rs1 es la muestra y rs2 el estado)
  funct3 = 001   carriles  cuatro carriles de 8 bits, operación en funct7[3:0]
  funct3 = 010   producto  mulstep, divstep y mulc, según funct7[1:0]
  funct3 = 011   srak      rd = rs1 >>> k, con k en funct7[4:0]
  funct3 = 100   emad      rd = rs2 + (rs1 >>> k): el paso de la media a partir
                           de la desviación (rs1 = muestra - estado)
  funct3 = 101   devk      rd = (rs1 << k) - rs2: la desviación de una muestra
                           sin escalar
  funct3 = 110   reservado para kal2 (docs/producto_2x2.md)

    python3 factibilidad/d_isa/ref/xd.py            # autoprueba del modelo
    python3 factibilidad/d_isa/ref/xd.py --tabla    # tabla de codificaciones
"""
import random
import sys

M32 = 0xFFFFFFFF
OPCODE_CUSTOM0 = 0b0001011

F3_EMA = 0b000
F3_CARRILES = 0b001
F3_PRODUCTO = 0b010
F3_SRAK = 0b011
F3_EMAD = 0b100
F3_DEVK = 0b101
F3_KAL2 = 0b110          # reservado, no es de esta pieza
CON_K = {"ema": F3_EMA, "srak": F3_SRAK, "emad": F3_EMAD, "devk": F3_DEVK}

# funct7[3:0] del grupo de carriles
CARRILES = {
    "padd8": 0,      # suma con vuelta (módulo 256)
    "psub8": 1,      # resta con vuelta
    "pcmpltu8": 2,   # a < b sin signo: 0xFF o 0x00 por carril
    "pcmplt8": 3,    # a < b con signo
    "pminu8": 4,     # mínimo sin signo
    "pmaxu8": 5,     # máximo sin signo
    "paddus8": 6,    # suma saturada sin signo (tope 255)
    "psubus8": 7,    # resta saturada sin signo (piso 0)
    "pbcast8": 8,    # copia el byte bajo de rs1 a los cuatro carriles
    "pmovmsk8": 9,   # un bit por carril: el bit 7 de cada carril de rs1
}
# funct7[1:0] del grupo de producto
PRODUCTO = {
    "mulstep": 0,    # un paso de multiplicación, bit más significativo primero
    "divstep": 1,    # un paso de división con restauración, cociente de 8 bits
    "mulc": 2,       # producto combinacional angosto: rs1[15:0] por rs2[7:0]
}
UN_OPERANDO = {"pbcast8", "pmovmsk8"}


def s32(x):
    """El valor con signo de un registro de 32 bits."""
    x &= M32
    return x - (1 << 32) if x >> 31 else x


# --- ema ------------------------------------------------------------------------
def ema(rs1, rs2, k):
    """rd = rs2 + ((rs1 - rs2) >>> k), con rs1 = muestra y rs2 = estado.

    Es la fórmula del paso de media exponencial, estado + ((muestra - estado)
    >>> k). El estado va en rs2 para que la resta sea rs1 - rs2, que es la que
    la ALU del core ya hace. La resta y la suma dan la vuelta en 32 bits y el
    desplazamiento es aritmético: es lo mismo que
    `sub t, rs1, rs2; srai t, t, k; add rd, rs2, t`.
    Con rs2 = x0 es un desplazamiento aritmético a la derecha de rs1.
    """
    d = s32(rs1 - rs2)
    return (rs2 + (d >> k)) & M32


def emad(rs1, rs2, k):
    """rd = rs2 + (rs1 >>> k): el paso de la media cuando la desviación
    (muestra - estado) ya está en un registro. Con rs2 = x0 es srak."""
    return (rs2 + (s32(rs1) >> k)) & M32


def devk(rs1, rs2, k):
    """rd = (rs1 << k) - rs2: la desviación de una muestra sin escalar respecto
    a un estado con k bits de fracción. Con rs2 = x0 es un desplazamiento a la
    izquierda."""
    return ((rs1 << k) - rs2) & M32


def srak(rs1, k):
    """rd = rs1 >>> k: desplazamiento aritmético a la derecha por una constante."""
    return (s32(rs1) >> k) & M32


def ema_secuencia(rs1, rs2, k):
    """La misma instrucción escrita como las tres de RV32I que reemplaza."""
    t = (rs1 - rs2) & M32
    t = (s32(t) >> k) & M32
    return (rs2 + t) & M32


# --- carriles de 4 x 8 bits -----------------------------------------------------
def carriles(x):
    """Los cuatro carriles de un registro, del menos al más significativo."""
    return [(x >> (8 * i)) & 0xFF for i in range(4)]


def empaquetar(v):
    return sum((b & 0xFF) << (8 * i) for i, b in enumerate(v))


def s8(x):
    return x - 256 if x & 0x80 else x


def carril(op, a, b):
    """Resultado de un carril (0 a 255) para la operación `op` (número)."""
    if op == 0:
        return (a + b) & 0xFF
    if op == 1:
        return (a - b) & 0xFF
    if op == 2:
        return 0xFF if a < b else 0x00
    if op == 3:
        return 0xFF if s8(a) < s8(b) else 0x00
    if op == 4:
        return min(a, b)
    if op == 5:
        return max(a, b)
    if op == 6:
        return min(a + b, 255)
    if op == 7:
        return max(a - b, 0)
    raise ValueError(f"operación de carril desconocida: {op}")


def simd8(op, rs1, rs2):
    """Grupo de carriles completo. `op` es el número de funct7[3:0]."""
    if op == 8:                                   # pbcast8
        return empaquetar([rs1 & 0xFF] * 4)
    if op == 9:                                   # pmovmsk8
        return sum(((rs1 >> (8 * i + 7)) & 1) << i for i in range(4))
    return empaquetar([carril(op, a, b) for a, b in zip(carriles(rs1), carriles(rs2))])


def simd8_bit(op, rs1, rs2):
    """Variante evaluada y no elegida: las comparaciones entregan un bit por
    carril en los bits 3:0 en vez de una máscara. El resto no cambia."""
    r = simd8(op, rs1, rs2)
    if op in (2, 3):
        return sum(((r >> (8 * i)) & 1) << i for i in range(4))
    return r


# --- producto y cociente por pasos ----------------------------------------------
def mulstep(rs1, rs2):
    """Un paso de multiplicación: rd = (rs1 << 1) + (rs1[31] ? rs2 : 0).

    El multiplicador va en los n bits altos de rs1 y el acumulador parte en
    cero en los bits bajos. Después de n pasos, rd = multiplicador * rs2,
    siempre que rs2 < 2^(32 - n).
    """
    return ((rs1 << 1) + (rs2 if rs1 >> 31 else 0)) & M32


def multiplicar(q, m, n=8):
    """q (n bits) por m usando n veces mulstep, como lo haría el programa."""
    x = (q << (32 - n)) & M32
    for _ in range(n):
        x = mulstep(x, m)
    return x


def divstep(rs1, rs2):
    """Un paso de división con restauración.

    rs1 = {R (24 bits), Q (8 bits)}, divisor D = rs2[23:0]. Desplaza {R, Q} un
    bit a la izquierda y, si el R nuevo (25 bits) es mayor o igual que D, le
    resta D y pone un 1 en el bit bajo. Después de 8 pasos partiendo de
    rs1 = N, con N < 256 * D: Q = N div D y R = N mod D.
    """
    d = rs2 & 0xFFFFFF
    r = (rs1 >> 7) & 0x1FFFFFF                    # R desplazado: 25 bits
    q = (rs1 << 1) & 0xFF
    if r >= d:
        r -= d
        q |= 1
    return ((r << 8) | q) & M32


def dividir(n, d):
    """(cociente, resto) de n / d con 8 pasos de divstep. Exige n < 256 * d."""
    x = n & M32
    for _ in range(8):
        x = divstep(x, d)
    return x & 0xFF, x >> 8


def mulc(rs1, rs2, aw=16, bw=8):
    """Producto combinacional angosto, sin signo: rs1[aw-1:0] * rs2[bw-1:0]."""
    return ((rs1 & ((1 << aw) - 1)) * (rs2 & ((1 << bw) - 1))) & M32


class MulMMIO:
    """Periférico multiplicador serial, con exactitud de ciclo.

    Registros (desplazamiento respecto a la base del periférico):
      0x0 MULA  escritura: multiplicando, 24 bits
      0x4 MULB  escritura: multiplicador, 8 bits. Parte el producto.
      0x8 MULP  lectura: producto de 32 bits (válido cuando BUSY = 0)
      0xC MULS  lectura: bit 0 = BUSY
    Cada ciclo hace un paso de mulstep. El producto queda listo 8 flancos
    después del flanco en que se escribe MULB.
    """

    def __init__(self):
        self.a = 0
        self.x = 0
        self.cnt = 0
        self.rdata = 0

    def flanco(self, req=False, we=False, off=0, wdata=0):
        """Un flanco de reloj. `off` es el número de palabra (0 a 3).

        Devuelve rdata después del flanco. La lectura es registrada: captura
        el valor que el registro tenía antes del flanco.
        """
        a_antes = self.a                 # el paso de este flanco usa el MULA anterior
        if req and not we:
            self.rdata = self.busy if off & 1 else self.x
        if req and we and off == 0:
            self.a = wdata & 0xFFFFFF
        if req and we and off == 1:
            self.x = (wdata & 0xFF) << 24
            self.cnt = 8
        elif self.cnt:
            self.x = mulstep(self.x, a_antes)
            self.cnt -= 1
        return self.rdata

    @property
    def busy(self):
        return int(self.cnt != 0)


# --- contabilidad: lo que ejecuta la maestra ------------------------------------
def compra_recortada(caja, p, q=63, comision=5):
    """Acciones que ejecuta la maestra para "comprar q" (tb/tb_proyecto_4.sv)."""
    tope = (caja - comision) // p if caja >= comision else 0
    return min(q, max(tope, 0))


def compra_por_restas(caja, p, comision=5):
    """Lo mismo para q = 63, sin dividir: 6 restas de prueba con 32p ... p.

    Devuelve (acciones, caja nueva). Como la orden nunca pasa de 63 acciones,
    el cociente tiene 6 bits y el resto final es la caja que queda.
    """
    r = caja - comision
    if r < p:
        return 0, caja                            # no alcanza para una acción: no se ejecuta
    if r >= 64 * p:
        return 63, r - 63 * p                     # sin recorte
    q = 0
    for i in range(5, -1, -1):
        if r >= (p << i):
            r -= p << i
            q |= 1 << i
    return q, r


# --- codificación ---------------------------------------------------------------
def codificar(nombre, rd, rs1, rs2=0, k=None):
    """Palabra de 32 bits de la instrucción. Registros entre 0 y 15 (RV32E)."""
    for r in (rd, rs1, rs2):
        if not 0 <= r <= 15:
            raise ValueError(f"registro fuera de RV32E: x{r}")
    if nombre in CON_K:
        if k is None or not 0 <= k <= 31:
            raise ValueError(f"{nombre} necesita k entre 0 y 31")
        funct3, funct7 = CON_K[nombre], k
    elif nombre in CARRILES:
        funct3, funct7 = F3_CARRILES, CARRILES[nombre]
    elif nombre in PRODUCTO:
        funct3, funct7 = F3_PRODUCTO, PRODUCTO[nombre]
    else:
        raise ValueError(f"instrucción desconocida: {nombre}")
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | OPCODE_CUSTOM0


def ejecutar(palabra, rs1, rs2, ema_k=None):
    """Resultado de una palabra de custom-0 con los operandos dados."""
    funct3 = (palabra >> 12) & 7
    funct7 = palabra >> 25
    if funct3 == F3_EMA:
        return ema(rs1, rs2, funct7 & 31 if ema_k is None else ema_k)
    if funct3 == F3_CARRILES:
        return simd8(funct7 & 15, rs1, rs2)
    if funct3 == F3_PRODUCTO:
        return (mulstep, divstep, mulc)[funct7 & 3](rs1, rs2)
    if funct3 == F3_SRAK:
        return srak(rs1, funct7 & 31 if ema_k is None else ema_k)
    if funct3 == F3_EMAD:
        return emad(rs1, rs2, funct7 & 31 if ema_k is None else ema_k)
    if funct3 == F3_DEVK:
        return devk(rs1, rs2, funct7 & 31 if ema_k is None else ema_k)
    raise ValueError("codificación reservada")


def tabla():
    print(f"{'instrucción':<26} {'funct7':>8} {'funct3':>6}  ejemplo                      palabra")
    filas = [("ema", "ema x3, x6, x3, 5", codificar("ema", 3, 6, 3, k=5), "00kkkkk"),
             ("emad", "emad x3, x6, x3, 5", codificar("emad", 3, 6, 3, k=5), "00kkkkk"),
             ("devk", "devk x6, x5, x3, 5", codificar("devk", 6, 5, 3, k=5), "00kkkkk"),
             ("srak", "srak x7, x6, 5", codificar("srak", 7, 6, 0, k=5), "00kkkkk")]
    filas += [(n, f"{n} x7, x8, x9" if n not in UN_OPERANDO else f"{n} x7, x8",
               codificar(n, 7, 8, 0 if n in UN_OPERANDO else 9), f"{v:07b}") for n, v in CARRILES.items()]
    filas += [(n, f"{n} x7, x7, x8", codificar(n, 7, 7, 8), f"{v:07b}") for n, v in PRODUCTO.items()]
    for nombre, ejemplo, palabra, f7 in filas:
        f3 = format((palabra >> 12) & 7, "03b")
        print(f"{nombre:<26} {f7:>8} {f3:>6}  {ejemplo:<28} 0x{palabra:08x}")


# --- autoprueba -----------------------------------------------------------------
def autoprueba():
    rng = random.Random(4)
    casos = 0
    # ema: igual a las tres instrucciones que reemplaza, y a la identidad de trade.s
    for _ in range(200000):
        a, b, k = rng.getrandbits(32), rng.getrandbits(32), rng.randrange(32)
        assert ema(a, b, k) == ema_secuencia(a, b, k)
        assert ema(a, b, k) == (b + srak((a - b) & M32, k)) & M32    # srak y add hacen lo mismo
        assert ema(a, b, k) == emad((a - b) & M32, b, k)             # sub y emad hacen lo mismo
        assert ema(a, 0, k) == srak(a, k) == emad(a, 0, k)
        assert devk(a, 0, k) == (a << k) & M32
        casos += 1
    for s in range(32, 8161):
        c = (s + 31) >> 5
        for p in (1, 2, 127, 128, 254, 255, 1 + s % 255):
            assert ema(32 * p, s, 5) == s + p - c          # lo que hace sw/trade.s
            assert devk(p, s, 5) == (32 * p - s) & M32     # la desviación de sw/trade.s
            assert emad(devk(p, s, 5), s, 5) == s + p - c  # devk y emad: el tick completo
            casos += 1
        assert ema(s, 0, 5) == s >> 5                       # con rs2 = x0 es un srai
    # carriles: cada operación contra su definición escalar, exhaustivo por carril
    for op in range(8):
        for a in range(256):
            for b in range(0, 256, 5):
                r = simd8(op, a * 0x01010101, b * 0x01010101)
                assert carriles(r) == [carril(op, a, b)] * 4
                casos += 1
    assert simd8(8, 0x123456AB, 0) == 0xABABABAB
    assert simd8(9, 0x80007F80, 0) == 0b1001
    for a in range(256):
        for b in range(256):
            assert carril(7, a, b) == carril(5, a, b) - b   # psubus = pmaxu - b
    # mulstep: 8 pasos dan el producto, para todo multiplicador de 8 bits
    for q in range(256):
        for m in (0, 1, 255, 63, 0xFFFF, 0xFFFFFF, rng.getrandbits(24)):
            assert multiplicar(q, m) == q * m
            casos += 1
    assert multiplicar(0xFFFF, 0xFFFF, n=16) == 0xFFFF * 0xFFFF
    # divstep: 8 pasos dan cociente y resto cuando el cociente cabe en 8 bits
    for _ in range(200000):
        d = rng.randrange(1, 1 << rng.randrange(1, 24))
        n = rng.randrange(0, min(256 * d, 1 << 31))
        assert dividir(n, d) == (n // d, n % d)
        casos += 1
    # compra recortada: 6 restas de prueba dan lo mismo que la división de la maestra
    for p in range(1, 256):
        for caja in list(range(0, 64 * p + 70)) + [rng.randrange(100000) for _ in range(200)]:
            q, caja2 = compra_por_restas(caja, p)
            assert q == compra_recortada(caja, p), (caja, p, q)
            assert caja2 == (caja - q * p - 5 if q else caja)
            if q < 63 and caja >= 5 and (caja - 5) < 256 * p:
                assert dividir(caja - 5, p)[0] == (caja - 5) // p
            casos += 1
    # periférico: el producto se lee 9 ciclos después de escribir MULB, no antes
    tempranas_malas = 0
    for _ in range(2000):
        a, b = rng.getrandbits(24), rng.getrandbits(8)
        m = MulMMIO()
        m.flanco(req=True, we=True, off=0, wdata=a)
        m.flanco(req=True, we=True, off=1, wdata=b)
        for _ in range(7):
            m.flanco()
        temprano = m.flanco(req=True, off=2)          # pedida 8 ciclos después: falta un paso
        assert m.busy == 0
        assert m.flanco(req=True, off=2) == a * b     # pedida 9 ciclos después
        tempranas_malas += temprano != a * b
        casos += 1
    assert tempranas_malas > 1900                     # la lectura temprana casi nunca sirve
    # codificación de ida y vuelta
    assert codificar("ema", 3, 6, 3, k=5) == 0x0A33018B
    assert codificar("emad", 3, 6, 3, k=5) == 0x0A33418B
    assert codificar("devk", 6, 5, 3, k=5) == 0x0A32D30B
    assert ejecutar(codificar("psubus8", 1, 2, 3), 0x05000A01, 0x06000902) == 0x00000100
    print(f"PASS modelo xd.py: {casos} casos")


if __name__ == "__main__":
    if "--tabla" in sys.argv:
        tabla()
    else:
        autoprueba()
