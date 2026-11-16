#!/usr/bin/env python3
"""simbolos.py: direcciones de las etiquetas de un programa y su tamaño por bloque.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Ensambla el programa con tools/pochoasm.py (sin modificarlo: se usa su módulo
tools/asm/core.py y se anota cada etiqueta que define) y entrega:

  --vh ARCHIVO     un include de Verilog con `define PC_<ETIQUETA> 32'h...
                   por etiqueta, para que tb/tb_fondo.sv sepa qué instrucción
                   es de sondeo y cuál es trabajo
  --tamano         cuántas palabras ocupa cada bloque del programa y los datos

Uso:
    python3 factibilidad/b_fondo_hilos/tools/simbolos.py PROGRAMA.s --vh build/simbolos.vh
    python3 factibilidad/b_fondo_hilos/tools/simbolos.py PROGRAMA.s --tamano
"""
import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(RAIZ, "tools", "asm"))

import core  # noqa: E402

RAM_PALABRAS = 512


def ensamblar(ruta, defines=None):
    """Devuelve (palabras, etiquetas, constantes)."""
    etiquetas, constantes = {}, {}
    original = core.Assembler._define_symbol

    def espia(self, symtab, nombre, valor, lineno, que):
        original(self, symtab, nombre, valor, lineno, que)
        (etiquetas if que == "etiqueta" else constantes)[nombre] = valor

    core.Assembler._define_symbol = espia
    try:
        with open(ruta, encoding="utf-8") as f:
            palabras = core.assemble_text(f.read(), defines=defines)
    finally:
        core.Assembler._define_symbol = original
    return palabras, etiquetas, constantes


def tamano(ruta, palabras, etiquetas, constantes):
    def pal(a, b):
        return (etiquetas[b] - etiquetas[a]) // 4

    datos_ini = constantes["PUB"]
    codigo = max(i for i in range(datos_ini // 4) if palabras[i] != 0) + 1
    bloques = [
        ("Tabla de arranque", 4),
        ("Supervisor: inicio, sondeo del SPI y publicación", pal("supervisor", "s_g1")),
        ("Supervisor: espera a los tres gestores", (etiquetas["s_g3"] + 12 - etiquetas["s_g1"]) // 4),
        ("Supervisor: voto y DECISION", (etiquetas["espejo"] - etiquetas["s_g3"] - 12) // 4),
        ("Supervisor: espejo de la cuenta real", pal("espejo", "e_fin")),
        ("Supervisor: vuelta al sondeo", pal("e_fin", "frontera")),
        ("Supervisor: frontera de ventana (pesos)", pal("frontera", "hilo1")),
        ("Entradas de los tres gestores", pal("hilo1", "gestor")),
        ("Rutina común de los gestores", codigo - etiquetas["gestor"] // 4),
    ]
    total_codigo = sum(n for _, n in bloques)
    datos = RAM_PALABRAS - datos_ini // 4
    print(f"Programa: {ruta}")
    print(f"{'Bloque':<52} {'palabras':>8}")
    for nombre, n in bloques:
        print(f"  {nombre:<50} {n:>8}")
    print(f"  {'Total de programa':<50} {total_codigo:>8}")
    sup = sum(n for nombre, n in bloques if nombre.startswith("Supervisor"))
    ges = sum(n for nombre, n in bloques if "gestor" in nombre and not nombre.startswith("Supervisor"))
    print(f"    del supervisor {sup}, de los gestores {ges} (los tres comparten la rutina), tabla 4")
    print(f"  {'Datos (desde 0x%03X hasta el final de la RAM)' % datos_ini:<50} {datos:>8}")
    escritor = {"supervisor": 1 + 2 + 3 + 3, "gestores": 9, "constantes (topes y pisos de los pesos)": 6}
    for k, v in escritor.items():
        print(f"    {k}: {v}")
    usado = total_codigo + datos
    print(f"  {'Total usado':<50} {usado:>8}  de {RAM_PALABRAS} ({100.0 * usado / RAM_PALABRAS:.1f} %)")
    print(f"  {'Palabras libres':<50} {RAM_PALABRAS - usado:>8}")
    if codigo != total_codigo:
        print(f"FAIL la suma de los bloques ({total_codigo}) no coincide con la última palabra de código ({codigo})")
        return 1
    if codigo * 4 > datos_ini:
        print("FAIL el código pisa los datos")
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("programa")
    ap.add_argument("--vh")
    ap.add_argument("--tamano", action="store_true")
    ap.add_argument("-D", "--define", action="append", default=[])
    args = ap.parse_args()
    defines = {}
    for item in args.define:
        nombre, _, valor = item.partition("=")
        defines[nombre] = core.parse_number(valor)
    palabras, etiquetas, constantes = ensamblar(args.programa, defines)
    if args.vh:
        with open(args.vh, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"// Generado por tools/simbolos.py a partir de {os.path.basename(args.programa)}. No editar.\n")
            for nombre, valor in sorted(etiquetas.items(), key=lambda kv: kv[1]):
                f.write(f"`define PC_{nombre.upper()} 32'h{valor:08x}\n")
            for nombre in ("PUB", "CAJA", "ACC", "W1", "W2", "W3", "DES1", "EST1", "DES2", "EST2", "DES3", "EST3"):
                f.write(f"`define PAL_{nombre} {constantes[nombre] // 4}\n")
    if args.tamano:
        return tamano(args.programa, palabras, etiquetas, constantes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
