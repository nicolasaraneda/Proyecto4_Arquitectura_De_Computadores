#!/usr/bin/env python3
"""
controles.py: programas con un error puesto a propósito en sw/fondo.s, para
comprobar que las pruebas de R1 y R2 lo detectan (controles negativos).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Cada control reemplaza un trozo exacto del programa, o cambia un valor de la
tabla de parámetros (los que empiezan con "TABLA:": el programa queda igual y
lo que se carga distinto es la BRAM de la tabla). Si el trozo no aparece
una sola vez el script termina con error, para que un cambio en fondo.s no
deje un control sin efecto sin que nadie lo note.

Desde el 17/11 (decisión T133) el programa es la regla de cotas en el hilo 0.
Los controles se corren con series normalizadas que tocan 100 y 255 ("norm" y
"norm2": series de reversión normalizadas, semillas 1 y 2; "meta": la serie Meta
desde el tick 10 500, normalizada), para que la regla opere y el error se note.
La semilla 2 es la que tiene un precio de exactamente 195 estando adentro con los
dos extremos vistos: la única forma de ver el umbral de venta corrido en uno.

Uso: tools/fondo/controles.py --lista
     tools/fondo/controles.py NOMBRE [-i sw/fondo.s] -o salida.s
"""

import argparse
import sys

# nombre: (descripción, texto original, texto con el error, falla con que se corre, serie)
CONTROLES = {
    "banda_tabla": (
        "la tabla trae otra banda de compra (171 en vez de 161)",
        "TABLA:BANDA_COMPRA=171", "", "", "norm"),
    "venta_tabla": (
        "la tabla vende desde 200 en vez de 195",
        "TABLA:BANDA_VENTA=200", "", "", "norm"),
    "venta_196": (
        "la tabla vende desde 196 en vez de 195 (un solo byte cambia: la serie de reversion de semilla 2)",
        "TABLA:BANDA_VENTA=196", "", "", "norm2"),
    "bajo_desde_101": (
        "compra al ver 101 y no solo 100",
        "    lw   x13, T_LO_MAS_1(x1)\n",
        "    lw   x13, T_LO_MAS_1(x1)\n    addi x13, x13, 1\n", "", "meta"),
    "minimo_olvidado": (
        "la marca de haber visto el minimo no queda puesta",
        "    or   x10, x10, x6          # se vio el mínimo",
        "    mv   x10, x6               # se vio el mínimo", "", "norm"),
    "sin_banda": (
        "con los dos extremos vistos no compra en la banda",
        "    and  x9, x9, x8            # comprar = bajo | (los dos & p <= 160)",
        "    and  x9, x9, x0            # comprar = bajo | (los dos & p <= 160)", "", "norm"),
    "q_no_se_mantiene": (
        "sin cambio el byte no se repite: pasa a comprar 63",
        "    and  x15, x15, x13\n", "", "", "norm"),
    "parte_comprando": (
        "parte con comprar 63 en vez de mantener",
        "    li   x4, 0                 # q = mantener: parte en caja",
        "    li   x4, 0x7F              # q = mantener: parte en caja", "", "meta"),
    "dos_decisiones": (
        "el hilo 0 escribe DECISION dos veces en el tick",
        "    sw   x4, OFF_DECISION(x2)\n", "    sw   x4, OFF_DECISION(x2)\n    sw   x4, OFF_DECISION(x2)\n", "", "meta"),
    "dos_stores_telemetria": (
        "la telemetria hace dos stores en los ticks impares",
        "    sw   x15, PER_LEDS(x14)\n", "    sw   x15, PER_LEDS(x14)\n    sw   x0, PER_DIGITOS(x14)\n", "", "meta"),
    "latido": (
        "el LED de latido usa otro bit del numero de tick",
        ".equ BIT_LATIDO,    0x400", ".equ BIT_LATIDO,    0x200", "", "meta"),
    "digitos": (
        "los 7 segmentos muestran otro numero al estar adentro",
        ".equ DIGITOS_ADENTRO, 0x63", ".equ DIGITOS_ADENTRO, 0x36", "", "meta"),
    "hilo_toca_spi": (
        "el hilo 1 lee el registro de estado del SPI",
        "hilo1:\n#@HILO1\n", "hilo1:\n#@HILO1\n    li   x5, SPI_BASE\n    lw   x6, OFF_STATUS(x5)\n", "", "meta"),
    "hilo_escribe_ram": (
        "el hilo 2 escribe la RAM (el programa sano no la usa)",
        "", "", "escribe:2", "meta"),
}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Controles negativos de sw/fondo.s")
    ap.add_argument("nombre", nargs="?")
    ap.add_argument("--lista", action="store_true", help="nombre|falla|serie|param|descripcion de cada control")
    ap.add_argument("-i", "--entrada", default="sw/fondo.s")
    ap.add_argument("-o", "--salida")
    a = ap.parse_args(argv)
    if a.lista:
        for nombre, (desc, original, _, falla, serie) in CONTROLES.items():
            param = original[6:] if original.startswith("TABLA:") else ""
            print(f"{nombre}|{falla}|{serie}|{param}|{desc}")
        return 0
    desc, original, mutado, _, _ = CONTROLES[a.nombre]
    with open(a.entrada, encoding="utf-8") as f:
        texto = f.read()
    if original.startswith("TABLA:") or original == "":
        original = mutado = ""
    elif texto.count(original) != 1:
        raise SystemExit(f"control {a.nombre}: el texto a reemplazar aparece {texto.count(original)} veces en {a.entrada}")
    texto = texto.replace(original, mutado) if original else texto
    with open(a.salida, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
