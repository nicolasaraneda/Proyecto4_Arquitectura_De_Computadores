#!/usr/bin/env python3
"""sin_custom0.py: quita de un programa aleatorio las palabras con el opcode custom-0.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 sin_custom0.py programa.s > programa_sin_custom0.s

Los generadores de programas aleatorios (tools/prog_aleatorio.py del
repositorio y tools/prog_hilos.py del estudio del barrel) incluyen, entre las
codificaciones que el Espino no reconoce, palabras con el opcode custom-0
(0001011). En el Espino base no hacen nada. En el barrel con la extensión son
instrucciones de verdad, así que esas palabras dejan de servir para comparar
un core contra el otro: la comparación de tools/verif_rv32e.sh es de las
instrucciones de RV32E.

Este filtro reemplaza cada palabra de código con ese opcode por un nop (addi
x0, x0, 0), que ocupa lo mismo, y en las palabras de datos al azar cambia el
opcode por el de misc-mem (0001111), que tampoco hace nada en ninguno de los
dos cores, por si un salto cae ahí. Informa cuántas cambió por la salida de
error. Las instrucciones nuevas se prueban aparte contra su modelo
(tools/tb_xd.sh).
"""
import re
import sys


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    codigo = datos = 0
    out = []
    for linea in open(sys.argv[1], encoding="utf-8"):
        m = re.match(r"^(\s*)\.word\s+(.*?)\s*(#.*)?$", linea.rstrip("\n"))
        if not m:
            out.append(linea)
            continue
        valores = [v.strip() for v in m.group(2).split(",")]
        try:
            nums = [int(v, 0) for v in valores]
        except ValueError:
            out.append(linea)
            continue
        if len(nums) == 1:
            if nums[0] & 0x7F == 0x0B:
                codigo += 1
                out.append(f"{m.group(1)}.word 0x00000013      # era una palabra de custom-0\n")
            else:
                out.append(linea)
            continue
        nuevos = []
        for n in nums:
            if n & 0x7F == 0x0B:
                datos += 1
                n ^= 0x04
            nuevos.append(str(n))
        out.append(f"{m.group(1)}.word {', '.join(nuevos)}\n")
    sys.stdout.write("".join(out))
    print(f"{codigo} palabras de codigo y {datos} de datos con opcode custom-0 reemplazadas", file=sys.stderr)


if __name__ == "__main__":
    main()
