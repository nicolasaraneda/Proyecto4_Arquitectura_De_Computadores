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
PLUSARGS = [
    ("s_espera", "A_S_ESPERA"), ("s_primero", "A_S_PRIMERO"), ("s_votos", "A_S_VOTOS"),
    ("s_plazo", "A_PLAZO"), ("frontera", "A_FRONTERA"), ("g_espera", "A_G_ESPERA"),
    ("g_primero", "A_G_PRIMERO"), ("PUB", "PUB"), ("W1", "W1"), ("REF1", "REF1"), ("G1", "G1"),
]

# bloques del programa, en orden: (nombre, etiqueta donde empieza)
BLOQUES = [
    ("Tabla de arranque", None),
    ("Supervisor: inicio y primer precio", "supervisor"),
    ("Supervisor: sondeo del SPI y publicación", "s_espera"),
    ("Supervisor: max_media propia", None),
    ("Supervisor: lectura de votos con plazo", "s_votos"),
    ("Supervisor: degradación (plazo vencido)", "s_plazo"),
    ("Supervisor: voto y DECISION", "s_todos"),
    ("Supervisor: telemetría", None),
    ("Supervisor: frontera de ventana (pesos)", "frontera"),
    ("Entradas de los tres gestores", "hilo1"),
    ("Rutina común de los gestores", "gestor"),
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
        tabla = e.simbolos["TABLA"] // 4
        fin = max(i for i, w in enumerate(palabras[:tabla]) if w) + 1
        marcas = {"Supervisor: max_media propia": e.etiquetas["s_publica"] + 12,
                  "Supervisor: telemetría": e.etiquetas["s_voto"] + 14 * 4}
        inicio = [0 if et is None and n == "Tabla de arranque" else marcas[n] if et is None else e.etiquetas[et]
                  for n, et in BLOQUES]
        inicio.append(fin * 4)
        for (nombre, _), a, b in zip(BLOQUES, inicio, inicio[1:]):
            print(f"  {nombre:45s} {(b - a) // 4:4d}")
        datos = sum(1 for w in palabras[tabla:] if w is not None and tabla * 4 < e.simbolos["PUB"])
        n_tabla = (e.simbolos["PUB"] - e.simbolos["TABLA"]) // 4
        n_estado = (e.simbolos["G3"] + 8 - e.simbolos["PUB"]) // 4
        print(f"  {'Programa':45s} {fin:4d}")
        print(f"  {'Tabla de parámetros (solo lectura)':45s} {n_tabla:4d}")
        print(f"  {'Estado compartido (parte en cero)':45s} {n_estado:4d}")
        print(f"  {'Total':45s} {fin + n_tabla + n_estado:4d} de {len(palabras)} palabras "
              f"({100.0 * (fin + n_tabla + n_estado) / len(palabras):.1f} %)")
        print(f"  {'Libres entre el programa y la tabla':45s} {tabla - fin:4d}")
    else:
        for nombre in argv[2:]:
            print(f"{nombre} {e.simbolos[nombre]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
