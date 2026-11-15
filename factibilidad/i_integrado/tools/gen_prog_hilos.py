#!/usr/bin/env python3
"""gen_prog_hilos.py: programas de prueba de las instrucciones nuevas en los cuatro hilos del barrel.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Es el método de factibilidad/d_isa/tools/gen_prog.py llevado al barrel. Ese
script, que se usa sin copiar ni modificar, genera para un core de un hilo un
programa al azar con instrucciones de custom-0 y la lista de escrituras al
banco de registros que predice el modelo ref/xd.py. Aquí se generan cuatro,
uno por hilo y cada uno con su semilla, y se arma la imagen de la memoria:

    palabras 0 a 3              tabla de arranque: el hilo t salta a su tramo
    palabras 4 + 127 t ...      tramo del hilo t (127 palabras), que termina
                                en un salto a sí mismo

Cada hilo tiene sus propios registros, así que la lista de escrituras de un
hilo no depende de lo que hagan los otros tres. Si el barrel mezclara los
campos de la instrucción de un hilo con los operandos de otro, las listas no
calzarían.

    python3 gen_prog_hilos.py --defs="-DXD_EMAD=0 -DXD_DEVK=0" --semilla 3 \\
        --hex build/xd/p.hex --esperado build/xd/p [--solo T]

Escribe p.hex y p.h0.esp a p.h3.esp (una línea por escritura: un dígito con el
registro y ocho con el valor). Con --solo T solo el hilo T tiene programa y
los otros tres quedan en un lazo vacío. Imprime, por hilo, las escrituras
esperadas y las instrucciones nuevas.
"""
import argparse
import os
import random
import sys

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
D_ISA = os.path.join(AQUI, "..", "..", "d_isa")
sys.path.insert(0, os.path.join(D_ISA, "tools"))
sys.path.insert(0, os.path.join(D_ISA, "ref"))
import gen_prog  # noqa: E402

TRAMO = 127                      # palabras por hilo: 4 + 4 x 127 = 512
PALABRAS = 512


def jal(desde, hasta):
    """jal x0, hasta - desde (direcciones en bytes)."""
    d = (hasta - desde) & 0x1FFFFF
    return (((d >> 20) & 1) << 31) | (((d >> 1) & 0x3FF) << 21) | (((d >> 11) & 1) << 20) | (((d >> 12) & 0xFF) << 12) | 0x6F


def main(argv=None):
    ap = argparse.ArgumentParser(description="Programa de prueba de custom-0 en los cuatro hilos del barrel")
    ap.add_argument("--defs", default="")
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--hex", required=True)
    ap.add_argument("--esperado", required=True, help="prefijo de los cuatro archivos .hT.esp")
    ap.add_argument("--solo", type=int, default=-1, choices=[-1, 0, 1, 2, 3])
    a = ap.parse_args(argv)
    defs = gen_prog.leer_defs(a.defs)
    if "XD_MULMMIO" in defs:
        sys.exit("gen_prog_hilos.py: el periférico multiplicador no está en el SoC del barrel")

    gen_prog.PALABRAS = TRAMO
    imagen = [0] * PALABRAS
    resumen = []
    for t in range(4):
        inicio = 4 + TRAMO * t
        imagen[t] = jal(4 * t, 4 * inicio)
        p = gen_prog.Programa(defs, random.Random(1000 * a.semilla + t))
        if a.solo in (-1, t):
            p.generar()
        else:
            p.palabras = [0x0000006F] + [0] * (TRAMO - 1)      # lazo vacío
        assert len(p.palabras) == TRAMO
        imagen[inicio:inicio + TRAMO] = p.palabras
        ruta = f"{a.esperado}.h{t}.esp"
        os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
        with open(ruta, "w", newline="\n") as f:
            f.write("".join(f"{rd:x}{v:08x}\n" for rd, v in p.esperado))
        resumen.append(f"h{t}={len(p.esperado)}:{sum(p.conteo.values())}")
    with open(a.hex, "w", newline="\n") as f:
        f.write("".join(f"{w:08x}\n" for w in imagen))
    print(" ".join(resumen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
