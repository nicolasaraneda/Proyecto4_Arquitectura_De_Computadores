#!/usr/bin/env python3
"""modelo_kernel.py: lo que deben publicar los hilos de sw/kernel_media.s y sw/kernel_carriles.s.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 modelo_kernel.py media|carriles VUELTAS PREFIJO

Escribe PREFIJO.h1.esp, PREFIJO.h2.esp y PREFIJO.h3.esp: la suma S que el hilo
publica en cada vuelta, una por línea, de la vuelta 1 a la VUELTAS. Cada
instrucción nueva se calcula con el modelo de referencia de la extensión,
ref/xd.py de factibilidad/d_isa, que se usa sin copiar ni modificar. Los
valores iniciales son los de los archivos .s.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "d_isa", "ref"))
import xd  # noqa: E402

M32 = xd.M32
INICIO = {
    "media":    [(0x13579BDF, 0x2468ACE1), (0x89ABCDEF, 0x0F1E2D3D), (0x7FFFFFF1, 0xDEADBEEF)],
    "carriles": [(0x00000011, 0xC83CA064), (0x000000A7, 0x10462802), (0x0000005C, 0xFF80017F)],
}


def vuelta_media(x1, x2):
    x3 = xd.mulstep(x1, x2)
    x4 = xd.emad(x3, x1, 5)
    x1 = xd.devk(x4, x3, 5)
    return x1, x1


def vuelta_carriles(x1, x2):
    c = xd.CARRILES
    x1 = (x1 + 37) & M32
    x3 = xd.simd8(c["pbcast8"], x1, 0)
    x4 = xd.simd8(c["psubus8"], x2, x3)
    x7 = xd.simd8(c["pcmpltu8"], x3, x2)
    x9 = xd.simd8(c["paddus8"], x4, x7)
    x9 = xd.simd8(c["padd8"], x9, x3)
    x9 = xd.simd8(c["psub8"], x9, x2)
    x1 = xd.emad(x9, x1, 5)
    return x1, x9


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in INICIO:
        sys.exit(__doc__)
    cual, vueltas, prefijo = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    paso = vuelta_media if cual == "media" else vuelta_carriles
    for t, (x1, x2) in enumerate(INICIO[cual], start=1):
        s = 0
        lineas = []
        for _ in range(vueltas):
            x1, suma = paso(x1, x2)
            s = (s + suma) & M32
            lineas.append(f"{s:08x}\n")
        with open(f"{prefijo}.h{t}.esp", "w", newline="\n") as f:
            f.write("".join(lineas))
    print(f"{cual}: {vueltas} vueltas por hilo")


if __name__ == "__main__":
    main()
