#!/usr/bin/env python3
"""tabla.py: tabla de arranque del Espino barrel para un programa de un solo hilo.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

En el Espino barrel el hilo t parte en la dirección 4 t, así que todo programa
empieza con cuatro saltos. Este script escribe esa tabla para correr, sin
tocarlo, un programa escrito para el Espino de un hilo (sw/trade.s,
sw/mix_clase7.s, sw/hazard_test.s): el hilo elegido salta a la etiqueta
_start del programa y los otros tres quedan en un lazo vacío.

Uso: tabla.py HILO programa.s > programa_con_tabla.s

El programa original se copia a continuación de la tabla, sin cambios.
"""
import sys


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in "0123":
        sys.exit(__doc__)
    hilo = int(sys.argv[1])
    print("# Tabla de arranque del Espino barrel (generada por tools/barrel/tabla.py).")
    print(f"# El hilo {hilo} corre el programa. Los otros tres quedan en un lazo vacio.")
    for t in range(4):
        if t == hilo:
            print("    j    _start")
        else:
            print(f"ocioso{t}:")
            print(f"    j    ocioso{t}")
    print()
    sys.stdout.write(open(sys.argv[2], encoding="utf-8").read())


if __name__ == "__main__":
    main()
