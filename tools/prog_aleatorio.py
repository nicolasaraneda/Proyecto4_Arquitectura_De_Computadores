#!/usr/bin/env python3
"""prog_aleatorio.py: genera un programa aleatorio para comparar dos modelos del SoC.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 tools/prog_aleatorio.py SEMILLA -o build/cosim/prog.s [-n 300]

El programa es un cuerpo de instrucciones al azar que se repite para siempre.
Como los registros y la memoria conservan su valor entre una vuelta y la
siguiente, cada vuelta toma caminos distintos. Se usa para comparar la traza
del RTL con la del gemelo digital (make cosim), y sirve igual para comparar
el Espino original con el segmentado.

Qué incluye:
  - toda la ISA base: aritmética y lógica con registro y con inmediato,
    lui, auipc, loads y stores de los tres tamaños con cualquier
    desplazamiento, los seis branches, jal y jalr;
  - los shifts, que en este core se ejecutan como una suma;
  - accesos a los registros del esclavo SPI y de los periféricos;
  - palabras que el decodificador no reconoce (custom-0, misc-mem, system) y
    codificaciones con funct3 inválido.

Los saltos van siempre hacia adelante, dentro del cuerpo, así que el programa
no se puede salir del código. x13, x14 y x15 guardan las direcciones base y
nunca se escriben. Los stores solo tocan la zona de datos.
"""
import argparse
import random

ALU_R = ["add", "sub", "xor", "or", "and", "slt", "sltu"]
ALU_I = ["addi", "slti", "sltiu", "xori", "ori", "andi"]
SHIFT_R = ["sll", "srl", "sra"]
SHIFT_I = ["slli", "srli", "srai"]
LOADS = ["lw", "lh", "lhu", "lb", "lbu"]
STORES = ["sw", "sh", "sb"]
BRANCHES = ["beq", "bne", "blt", "bge", "bltu", "bgeu"]

DATOS = 0x600            # zona de datos: 64 palabras
NDATOS = 64


def generar(semilla, n):
    rng = random.Random(semilla)
    rd = lambda: f"x{rng.choice([0] + list(range(1, 13)) * 4)}"
    rs = lambda: f"x{rng.randint(0, 15)}"
    imm = lambda: rng.choice([rng.randint(-2048, 2047), rng.randint(-8, 8), 0, 1, -1, 2047, -2048])

    out = [f"# Programa aleatorio, semilla {semilla}. Generado por tools/prog_aleatorio.py.",
           "_start:",
           f"    li   x15, {DATOS}",
           "    li   x14, 0x80010000",
           "    li   x13, 0x80000000"]
    for r in range(1, 13):
        out.append(f"    li   x{r}, {rng.choice([rng.getrandbits(32), rng.randint(-300, 300), rng.randint(0, 255)])}")
    out.append("cuerpo:")

    i = 0
    cuerpo = []          # (etiqueta implícita L<i>, texto)
    while i < n:
        tipo = rng.choices(
            ["alu_r", "alu_i", "shift", "lui", "load", "store", "spi", "periph", "branch", "jal", "jalr", "rara"],
            [22, 22, 5, 5, 10, 9, 7, 2, 10, 2, 2, 4])[0]
        adelante = lambda desde: min(n, desde + 1 + rng.randint(0, 4))
        if tipo == "alu_r":
            cuerpo.append(f"{rng.choice(ALU_R)} {rd()}, {rs()}, {rs()}")
        elif tipo == "alu_i":
            cuerpo.append(f"{rng.choice(ALU_I)} {rd()}, {rs()}, {imm()}")
        elif tipo == "shift":
            if rng.random() < 0.5:
                cuerpo.append(f"{rng.choice(SHIFT_R)} {rd()}, {rs()}, {rs()}")
            else:
                cuerpo.append(f"{rng.choice(SHIFT_I)} {rd()}, {rs()}, {rng.randint(0, 31)}")
        elif tipo == "lui":
            cuerpo.append(f"{rng.choice(['lui', 'auipc'])} {rd()}, {rng.getrandbits(20)}")
        elif tipo == "load":
            cuerpo.append(f"{rng.choice(LOADS)} {rd()}, {rng.randint(0, 4 * NDATOS - 1)}(x15)")
        elif tipo == "store":
            cuerpo.append(f"{rng.choice(STORES)} {rs()}, {rng.randint(0, 4 * NDATOS - 1)}(x15)")
        elif tipo == "spi":
            if rng.random() < 0.6:
                cuerpo.append(f"{rng.choice(['lw', 'lw', 'lbu', 'lh'])} {rd()}, {rng.choice([0, 4, 4, 8, 12, 5])}(x14)")
            else:
                cuerpo.append(f"{rng.choice(STORES)} {rs()}, {rng.choice([8, 8, 8, 0, 4, 12, 9])}(x14)")
        elif tipo == "periph":
            if rng.random() < 0.5:
                cuerpo.append(f"lw {rd()}, {rng.choice([0, 4, 8])}(x13)")
            else:
                cuerpo.append(f"sw {rs()}, {rng.choice([0, 4, 8])}(x13)")
        elif tipo == "branch":
            cuerpo.append(f"{rng.choice(BRANCHES)} {rs()}, {rs()}, L{adelante(len(cuerpo))}")
        elif tipo == "jal":
            cuerpo.append(f"jal {rd()}, L{adelante(len(cuerpo))}")
        elif tipo == "jalr":
            if len(cuerpo) + 2 > n:
                continue
            t = rng.randint(1, 12)
            salto = min(n - len(cuerpo), 2 + rng.randint(0, 3))          # en instrucciones, desde el auipc
            cuerpo.append(f"auipc x{t}, 0")
            cuerpo.append(f"jalr {rd()}, {4 * salto + rng.choice([0, 0, 1])}(x{t})")   # el bit 0 se descarta
        else:
            r_d, r_s = rng.choice(range(1, 13)), rng.randint(0, 15)
            alto = rng.getrandbits(25) << 7
            cuerpo.append(rng.choice([
                f".word {alto | 0x0B}",                                   # custom-0: no hace nada
                f".word {(alto & ~0x7000) | 0x0F}",                       # misc-mem
                f".word {0x00000073 | (rng.getrandbits(1) << 20)}",       # ecall, ebreak
                f".word {(rng.randint(0, 255) << 20) | (15 << 15) | (rng.choice([3, 6, 7]) << 12) | (r_d << 7) | 0x03}",  # load con funct3 inválido
                f".word {(r_s << 20) | (rng.randint(1, 12) << 15) | (rng.choice([2, 3]) << 12) | (8 << 7) | 0x63}",        # branch con funct3 inválido
            ]))
        i = len(cuerpo)

    for k, texto in enumerate(cuerpo):
        out.append(f"L{k}:")
        out.append(f"    {texto}")
    out.append(f"L{len(cuerpo)}:")
    out.append("    j    cuerpo")
    out.append(f".org {DATOS}")
    for _ in range(NDATOS // 4):
        out.append("    .word " + ", ".join(str(rng.getrandbits(32)) for _ in range(4)))
    out.append(".org 0x800")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("semilla", type=int)
    ap.add_argument("-o", "--salida", required=True)
    ap.add_argument("-n", type=int, default=300, help="instrucciones del cuerpo (máximo 350)")
    a = ap.parse_args()
    if not 1 <= a.n <= 350:
        ap.error("-n debe estar entre 1 y 350")
    with open(a.salida, "w", newline="\n") as f:
        f.write(generar(a.semilla, a.n))


if __name__ == "__main__":
    main()
