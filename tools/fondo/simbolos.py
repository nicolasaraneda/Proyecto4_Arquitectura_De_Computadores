#!/usr/bin/env python3
"""
simbolos.py: direcciones de las etiquetas de sw/fondo.s y tamaño por bloque.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Usa el ensamblador del repositorio sin modificarlo: lo ejecuta y se queda con
la tabla de símbolos.

Uso:
  tools/fondo/simbolos.py PROGRAMA.s --plusargs   # argumentos para tb/fondo/tb_fondo.sv
  tools/fondo/simbolos.py PROGRAMA.s --tamano     # palabras por bloque
  tools/fondo/simbolos.py PROGRAMA.s NOMBRE...    # dirección de cada símbolo
"""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "tools", "asm"))

import core  # noqa: E402

# etiqueta del programa -> plusarg del testbench
PLUSARGS = [("s_espera", "A_S_ESPERA"), ("hilo1", "A_HILO1"), ("hilo2", "A_HILO2"), ("hilo3", "A_HILO3")]

# bloques del programa, en orden: (nombre, etiqueta donde empieza)
BLOQUES = [
    ("Tabla de arranque", None),
    ("Hilos 1 a 3: lazo de espera", "hilo1"),
    ("Hilo 0: inicio", "supervisor"),
    ("Hilo 0: sondeo del SPI y lectura del precio", "s_espera"),
    ("Hilo 0: umbrales de la tabla, decision y DECISION", "s_decidir"),
    ("Hilo 0: telemetria", "s_telemetria"),
]


class Ensamblador(core.Assembler):
    """El ensamblador del repositorio, guardando las etiquetas y los .equ."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.simbolos = {}
        self.etiquetas = {}

    def _define_symbol(self, symtab, name, value, lineno, kind):
        super()._define_symbol(symtab, name, value, lineno, kind)
        self.simbolos[name] = value
        if kind == "etiqueta":
            self.etiquetas[name] = value


def ensamblar(ruta):
    e = Ensamblador(xd=True)
    with open(ruta, encoding="utf-8") as f:
        palabras = e.assemble(f.read())
    return e, palabras


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    e, palabras = ensamblar(argv[1])
    if argv[2] == "--plusargs":
        print(" ".join(f"+{arg}={e.simbolos[nombre]}" for nombre, arg in PLUSARGS))
    elif argv[2] == "--tamano":
        fin = max(i for i, w in enumerate(palabras) if w) + 1
        inicio = [0 if et is None else e.etiquetas[et] for _, et in BLOQUES] + [fin * 4]
        for (nombre, _), a, b in zip(BLOQUES, inicio, inicio[1:]):
            print(f"  {nombre:52s} {(b - a) // 4:4d}")
        print(f"  {'Programa':52s} {fin:4d} de 512 palabras ({100.0 * fin / 512:.1f} %)")
        print("  El programa no usa la RAM de datos. La tabla de parametros (4 valores de 16 bits) esta en su BRAM.")
    else:
        for nombre in argv[2:]:
            print(f"{nombre} {e.simbolos[nombre]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
