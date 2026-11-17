#!/usr/bin/env python3
"""
gen_ro_custom0.py: programa de prueba dirigida para el hardware de R1
(revisión P10, docs/revision_p10.md, hallazgos sobre la tabla y custom-0).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Arma un programa de un solo hilo (los hilos 1 a 3 quedan en un lazo vacío) que
comprueba, sobre el SoC de R1 (barrel con emad y devk y la tabla), tres
afirmaciones de la documentación:

  1. La tabla de parámetros es de solo lectura: sw, sh y sb a 0x8002_xxxx y a
     0x8003_xxxx no cambian su contenido, ni escriben DECISION, los LED o los
     7 segmentos, aunque el desplazamiento coincida con el de esos registros.
  2. Toda palabra de custom-0 que no sea emad o devk con k = 5 (incluida la
     codificación de mulstep, que R1 no tiene) no hace nada: no escribe rd, no
     toca la memoria y no salta. Lo mismo para custom-1, custom-2 y custom-3.
  3. emad y devk en los bordes: signo, redondeo hacia menos infinito,
     desborde, rd igual a rs1 o rs2, y rd = x0.

Los resultados quedan en la memoria de datos desde 0x600; el archivo de
valores esperados se calcula aquí con la fórmula de la especificación
(docs/extension_isa.md), independiente del RTL.

Uso: tools/p10/gen_ro_custom0.py PROGRAMA.s ESPERADO.txt
"""

import sys

M = 0xFFFFFFFF


def s32(x):
    x &= M
    return x - (1 << 32) if x & 0x80000000 else x


def emad(rs1, rs2):
    return (rs2 + (s32(rs1) >> 5)) & M


def devk(rs1, rs2):
    return ((rs1 << 5) - rs2) & M


def custom(opcode, funct3, funct7, rd, rs1, rs2):
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


# Tabla de parámetros: sw/fondo_tabla.hex, extendida con signo
TABLA = [int(l, 16) for l in open("sw/fondo_tabla.hex") if l.strip()]


def tabla(i):
    v = TABLA[i]
    return (v - 0x10000 if v & 0x8000 else v) & M


def main():
    prog, esperado = sys.argv[1], sys.argv[2]
    L = [".extension xd", "    j    t0", "    j    ocioso", "    j    ocioso", "    j    ocioso",
         "ocioso:", "    j    ocioso", "t0:"]
    esp = {}
    dir_ = 0x600

    def guardar(reg, valor):
        nonlocal dir_
        L.append(f"    sw   {reg}, {dir_}(x0)")
        esp[dir_] = valor & M
        dir_ += 4

    # --- 1. Tabla de solo lectura ---------------------------------------------
    L += ["    li   x2, 0x80020000", "    lw   x3, 0(x2)", "    lw   x4, 4(x2)", "    lw   x5, 76(x2)",
          "    li   x6, 0x800203FC", "    lw   x7, 0(x6)",
          "    li   x8, 0x12345678",
          "    sw   x8, 0(x2)", "    sh   x8, 4(x2)", "    sb   x8, 76(x2)", "    sw   x8, 0(x6)",
          # mismo desplazamiento que DIGITOS (0), LEDS (4) y DECISION (8), con los bits 17 y 16
          "    sw   x8, 8(x2)",
          "    li   x9, 0x80030000", "    sw   x8, 0(x9)", "    sw   x8, 4(x9)", "    sw   x8, 8(x9)",
          "    li   x9, 0x80070008", "    sw   x8, 0(x9)",
          "    lw   x10, 0(x2)", "    lw   x11, 4(x2)", "    lw   x12, 76(x2)", "    lw   x13, 0(x6)",
          "    lw   x14, 8(x2)"]
    for r, v in (("x3", tabla(0)), ("x10", tabla(0)), ("x4", tabla(1)), ("x11", tabla(1)),
                 ("x5", tabla(19)), ("x12", tabla(19)), ("x7", tabla(255)), ("x13", tabla(255)),
                 ("x14", tabla(2))):
        guardar(r, v)

    # --- 2. Palabras sin efecto ----------------------------------------------
    centinelas = {1: 0x11111111, 14: 0x33333333, 2: 0x22222222}
    rs1v, rs2v = 0x87654321, 0x0F0F0F0F
    L += [f"    li   x1, 0x{centinelas[1]:08x}", f"    li   x14, 0x{centinelas[14]:08x}",
          f"    li   x2, 0x{centinelas[2]:08x}",
          f"    li   x12, 0x{rs1v:08x}", f"    li   x13, 0x{rs2v:08x}", "    li   x15, 0"]
    n_palabras = 0
    funct7s = [0x00, 0x01, 0x04, 0x05, 0x06, 0x15, 0x25, 0x45, 0x65, 0x7F]
    for f3 in range(8):
        for f7 in funct7s:
            if f7 == 0x05 and f3 in (4, 5):
                continue            # son emad y devk de verdad
            for rd in ((1, 14, 2) if f7 in (0x00, 0x05) else (1, 14)):
                L.append(f"    .word 0x{custom(0x0B, f3, f7, rd, 12, 13):08x}")
                n_palabras += 1
        L.append("    addi x15, x15, 1")   # cuenta de bloques: detecta un salto
    for op in (0x2B, 0x5B, 0x7B):           # custom-1, custom-2 y custom-3
        for f3 in (0, 4, 5, 7):
            L.append(f"    .word 0x{custom(op, f3, 0x05, 1, 12, 13):08x}")
            n_palabras += 1
        L.append("    addi x15, x15, 1")
    guardar("x1", centinelas[1])
    guardar("x14", centinelas[14])
    guardar("x2", centinelas[2])
    guardar("x15", 8 + 3)

    # --- 3. emad y devk en los bordes ----------------------------------------
    casos = [
        ("emad", 0x80000000, 0x7FFFFFFF), ("emad", 0xFFFFFFFF, 5), ("emad", s32(-31), 0),
        ("emad", s32(-32), 0), ("emad", s32(-33), 0), ("emad", 31, 100), ("emad", 0x7FFFFFFF, 0x7FFFFFFF),
        ("devk", 0x08000000, 0), ("devk", 0x04000000, 1), ("devk", 0xFFFFFFFF, 0x80000000),
        ("devk", 255, 0), ("devk", 0, 0x80000000), ("devk", 0x07FFFFFF, s32(-1)),
    ]
    for ins, a, b in casos:
        L += [f"    li   x6, 0x{a & M:08x}", f"    li   x7, 0x{b & M:08x}", f"    {ins} x8, x6, x7, 5"]
        guardar("x8", emad(a, b) if ins == "emad" else devk(a, b))
    # rd igual a rs1 y a rs2, y rd = x0
    L += ["    li   x9, 0x00012345", "    emad x9, x9, x9, 5"]
    guardar("x9", emad(0x12345, 0x12345))
    L += ["    li   x9, 0xFFFFF000", "    devk x9, x9, x9, 5"]
    guardar("x9", devk(0xFFFFF000, 0xFFFFF000))
    L += ["    li   x6, 0x7FFFFFFF", "    emad x0, x6, x6, 5", "    devk x0, x6, x6, 5", "    add  x10, x0, x0"]
    guardar("x10", 0)
    guardar("x0", 0)

    # Marca de fin: si algo saltó o se colgó, no llega
    L += ["    li   x11, 0x00C0FFEE"]
    guardar("x11", 0x00C0FFEE)
    L += ["fin:", "    j    fin"]

    with open(prog, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Generado por tools/p10/gen_ro_custom0.py. No editar a mano.\n")
        f.write("\n".join(L) + "\n")
    with open(esperado, "w", encoding="utf-8", newline="\n") as f:
        for d, v in sorted(esp.items()):
            f.write(f"{d:08x} {v:08x}\n")
    print(f"{n_palabras} palabras sin efecto, {len(casos) + 4} casos de emad y devk, {len(esp)} palabras esperadas")


if __name__ == "__main__":
    main()
