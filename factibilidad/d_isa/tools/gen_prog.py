#!/usr/bin/env python3
"""gen_prog.py: programas de prueba de las instrucciones nuevas dentro del core.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Genera un programa al azar para tb/tb_xd_core.sv y la lista de escrituras al
banco de registros que debe producir, calculada con el modelo ref/xd.py. El
programa carga operandos con lui y addi, ejecuta instrucciones de custom-0
con registros al azar (incluye x0, rd igual a un operando y el uso inmediato
del resultado en la instrucción siguiente, que ejercita el adelantamiento del
pipeline) y, si está el periférico, hace productos por MMIO.

    python3 tools/gen_prog.py --defs="-DXD_EMA=0 -DXD_SIMD=28" --semilla 3 \\
        --hex build/core/p.hex --esperado build/core/p.esp

--defs recibe las mismas definiciones que se le pasan al RTL, para generar
solo las instrucciones presentes y con la codificación de esa variante.
Imprime el número de escrituras esperadas.
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ref"))
import xd  # noqa: E402

M32 = xd.M32
PALABRAS = 512
CONJUNTO_K = {0: [5], 2: [4, 5, 6, 7], 3: list(range(8)), 5: list(range(32))}
ESQUINAS = [0, 1, 31, 32, 0x7F, 0x80, 0xFF, 0x100, 0xFFFF, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF,
            0x01010101, 0x80808080, 0xFF00FF00, 0x00FFFFFF, 0x01000000]
MUL_BASE = 0x80020000


def leer_defs(texto):
    d = {}
    for tok in texto.replace("-D", " ").split():
        nombre, _, valor = tok.partition("=")
        d[nombre] = int(valor) if valor else 1
    return d


class Programa:
    def __init__(self, defs, rng):
        self.defs = defs
        self.rng = rng
        self.palabras = []
        self.reg = [0] * 16
        self.esperado = []                 # (registro, valor) de cada escritura con rd != 0
        self.conteo = {}

    def escribir(self, rd, valor):
        if rd:
            self.reg[rd] = valor & M32
            self.esperado.append((rd, valor & M32))

    # --- instrucciones base ---
    def lui(self, rd, imm20):
        self.palabras.append((imm20 << 12) | (rd << 7) | 0x37)
        self.escribir(rd, imm20 << 12)

    def addi(self, rd, rs1, imm):
        self.palabras.append(((imm & 0xFFF) << 20) | (rs1 << 15) | (rd << 7) | 0x13)
        self.escribir(rd, self.reg[rs1] + imm)

    def add(self, rd, rs1, rs2):
        self.palabras.append((rs2 << 20) | (rs1 << 15) | (rd << 7) | 0x33)
        self.escribir(rd, self.reg[rs1] + self.reg[rs2])

    def sub(self, rd, rs1, rs2):
        self.palabras.append((0x20 << 25) | (rs2 << 20) | (rs1 << 15) | (rd << 7) | 0x33)
        self.escribir(rd, self.reg[rs1] - self.reg[rs2])

    def li(self, rd, valor):
        bajo = valor & 0xFFF
        if bajo >= 0x800:
            bajo -= 0x1000
        self.lui(rd, ((valor - bajo) >> 12) & 0xFFFFF)
        self.addi(rd, rd, bajo)

    def sw(self, rs2, rs1, imm):
        self.palabras.append(((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (2 << 12) | ((imm & 31) << 7) | 0x23)

    def lw(self, rd, rs1, imm, valor):
        self.palabras.append((imm << 20) | (rs1 << 15) | (2 << 12) | (rd << 7) | 0x03)
        self.escribir(rd, valor)

    # --- instrucciones nuevas ---
    def xd(self, nombre, rd, rs1, rs2, k=None):
        d = self.defs
        a, b = self.reg[rs1], self.reg[rs2]
        if nombre == "ema":
            valor = xd.ema(a, b, k)
        elif nombre == "emad":
            valor = xd.emad(a, b, k)
        elif nombre == "devk":
            valor = xd.devk(a, b, k)
        elif nombre == "srak":
            valor = xd.srak(a, k)
        elif nombre in xd.CARRILES:
            modelo = xd.simd8_bit if d.get("XD_SIMD", 0) & 32 else xd.simd8
            valor = modelo(xd.CARRILES[nombre], a, b)
        elif nombre == "mulstep":
            valor = xd.mulstep(a, b)
        elif nombre == "divstep":
            valor = xd.divstep(a, b)
        else:
            valor = xd.mulc(a, b, d["XD_MULC"])
        self.palabras.append(xd.codificar(nombre, rd, rs1, rs2, k=k))
        self.escribir(rd, valor)
        self.conteo[nombre] = self.conteo.get(nombre, 0) + 1

    def disponibles(self):
        d = self.defs
        lista = []
        if "XD_EMA" in d:
            lista.append("ema")
        if "XD_SRAK" in d:
            lista.append("srak")
        if "XD_EMAD" in d:
            lista.append("emad")
        if "XD_DEVK" in d:
            lista.append("devk")
        if "XD_SIMDALU" in d:                    # carriles en el sumador de la ALU
            m = d["XD_SIMDALU"]
            lista += ["padd8", "psub8", "pcmpltu8"]
            lista += ["paddus8", "psubus8"] if m & 4 else []
            lista += ["pbcast8"] if m & 8 else []
        if "XD_SIMD" in d:
            m = d["XD_SIMD"]
            lista += ["padd8", "psub8", "pcmpltu8"]
            lista += ["pcmplt8"] if m & 1 else []
            lista += ["pminu8", "pmaxu8"] if m & 2 else []
            lista += ["paddus8", "psubus8"] if m & 4 else []
            lista += ["pbcast8"] if m & 8 else []
            lista += ["pmovmsk8"] if m & 16 else []
        if "XD_MULSTEP" in d or "XD_MULSTEPALU" in d:
            lista.append("mulstep")
        if "XD_DIVSTEP" in d:
            lista.append("divstep")
        if "XD_MULC" in d:
            lista.append("mulc")
        return lista

    def elegir_k(self, nombre):
        """k al azar dentro del conjunto que implementa la variante."""
        if nombre not in xd.CON_K:
            return None
        return self.rng.choice(CONJUNTO_K[self.defs["XD_" + nombre.upper()]])

    def valor(self):
        r = self.rng
        modo = r.randrange(5)
        if modo == 0:
            return r.choice(ESQUINAS)
        if modo == 1:
            return r.randrange(32, 8161)                     # el rango de la media de trade.s
        if modo == 2:
            return (r.getrandbits(8) << 24) | r.getrandbits(6)
        return r.getrandbits(32)

    def generar(self):
        r = self.rng
        lista = self.disponibles()
        libres = lambda: PALABRAS - 2 - len(self.palabras)   # noqa: E731
        base_mul = 15
        if "XD_MULMMIO" in self.defs:
            self.li(base_mul, MUL_BASE)
        regs = list(range(1, 15 if "XD_MULMMIO" in self.defs else 16))
        for x in regs:
            self.li(x, self.valor())
        while libres() > 24:
            if "XD_MULMMIO" in self.defs and (not lista or r.randrange(8) == 0):
                # producto por el periférico: 9 instrucciones de espera antes de leer
                ra, rb, rd = r.choice(regs), r.choice(regs), r.choice(regs)
                self.sw(ra, base_mul, 0)
                self.sw(rb, base_mul, 4)
                for _ in range(9):
                    self.addi(0, 0, 0)
                self.lw(rd, base_mul, 8, (self.reg[ra] & 0xFFFFFF) * (self.reg[rb] & 0xFF))
                self.lw(r.choice(regs), base_mul, 12, 0)
                self.conteo["mmio"] = self.conteo.get("mmio", 0) + 1
                continue
            if not lista:
                break
            nombre = r.choice(lista)
            rd = r.choice(regs + [0])
            rs1 = r.choice(regs + [0])
            rs2 = r.choice(regs + [0, rs1])
            if r.randrange(3) == 0 and rs1:
                self.li(rs1, self.valor())
            if r.randrange(3) == 0 and rs2:
                self.li(rs2, self.valor())
            k = self.elegir_k(nombre)
            if nombre in xd.UN_OPERANDO or nombre == "srak":
                rs2 = 0
            self.xd(nombre, rd, rs1, rs2, k)
            modo = r.randrange(4)
            if modo == 0 and rd:                             # uso inmediato del resultado
                self.add(r.choice(regs), rd, r.choice(regs))
            elif modo == 1 and rd:                           # dos instrucciones nuevas seguidas
                otro = r.choice(lista)
                k2 = self.elegir_k(otro)
                self.xd(otro, r.choice(regs), rd, 0 if otro in xd.UN_OPERANDO or otro == "srak" else r.choice(regs + [rd]), k2)
            elif modo == 2:
                self.sub(r.choice(regs), r.choice(regs), r.choice(regs))
        self.palabras.append(0x0000006F)                     # jal x0, 0: se queda aquí
        self.palabras += [0] * (PALABRAS - len(self.palabras))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Programa de prueba de la extensión en custom-0")
    ap.add_argument("--defs", default="")
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--hex", required=True)
    ap.add_argument("--esperado", required=True)
    a = ap.parse_args(argv)
    p = Programa(leer_defs(a.defs), random.Random(a.semilla))
    p.generar()
    for ruta in (a.hex, a.esperado):
        os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    with open(a.hex, "w", newline="\n") as f:
        f.write("".join(f"{w:08x}\n" for w in p.palabras))
    with open(a.esperado, "w", newline="\n") as f:
        f.write("".join(f"{rd:x}{v:08x}\n" for rd, v in p.esperado))
    print(len(p.esperado), " ".join(f"{k}={v}" for k, v in sorted(p.conteo.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
