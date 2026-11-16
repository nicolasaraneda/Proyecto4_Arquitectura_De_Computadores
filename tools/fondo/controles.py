#!/usr/bin/env python3
"""
controles.py: programas con un error puesto a propósito en sw/fondo.s, para
comprobar que las pruebas del fondo lo detectan (controles negativos).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Cada control reemplaza un trozo exacto del programa, o cambia un valor de la
tabla de parámetros (los que empiezan con "TABLA:": el programa queda igual y
lo que se carga distinto es la BRAM de la tabla). Si el trozo no aparece
una sola vez el script termina con error, para que un cambio en fondo.s no
deje un control sin efecto sin que nadie lo note.

Uso: tools/fondo/controles.py --lista
     tools/fondo/controles.py NOMBRE [-i sw/fondo.s] -o salida.s
"""

import argparse
import sys

# nombre: (descripción, texto original, texto con el error, falla con que se corre, serie)
CONTROLES = {
    "umbral_gestor3": (
        "la tabla trae otro umbral de entrada para el gestor 3",
        "TABLA:G3_ENTRA=-96", "", "", "reversion"),
    "comision_papel": (
        "el puntaje en papel descuenta la mitad de la comision",
        "    add  x7, x7, x7\n    sub  x13, x13, x7          # la comisión",
        "    sub  x13, x13, x7          # la comisión", "", "reversion"),
    "margen_frontera": (
        "la frontera ajusta los pesos sin exigir el margen",
        "    bge  x8, x9, f_fin         # ventaja <= p: no supera el margen",
        "    bge  x0, x9, f_fin         # ventaja <= p: no supera el margen", "", "practica"),
    "tope_pesos": (
        "la frontera no respeta el tope del peso del mejor",
        "    bge  x5, x6, f_fin         # ya está en su tope\n", "", "", "reversion"),
    "umbral_voto": (
        "el voto exige un dieciseisavo mas para comprar",
        "    slt  x9, x9, x1            # 1 si no hay mayoría",
        "    addi x1, x1, 1\n    slt  x9, x9, x1            # 1 si no hay mayoría", "", "reversion"),
    "plazo_corto": (
        "el plazo de la tabla es de una sola vuelta: vence con los gestores sanos",
        "TABLA:PLAZO=1", "", "", "practica"),
    "sin_reemplazo": (
        "vencido el plazo, el voto viejo del gestor 3 no se reemplaza",
        "    bnez x9, d_4\n    mv   x7, x15\n", "    bnez x9, d_4\n", "cuelgue:3:1", "reversion"),
    "reemplazo_fijo": (
        "vencido el plazo, el voto viejo del gestor 2 se cuenta como afuera en vez de usar max_media",
        "    bnez x9, d_3\n    mv   x6, x15\n", "    bnez x9, d_3\n    mv   x6, x0\n", "cuelgue:2:1", "reversion"),
    "sin_media_propia": (
        "el supervisor no actualiza la media de su max_media",
        "    emad x4, x9, x4, K         # S0 = S0 + (dev >>> 5)\n", "",
        "cuelgue:1:1+cuelgue:2:1+cuelgue:3:1", "practica"),
    "frontera_degradada": (
        "con un voto ausente en la frontera igual se ajustan los pesos",
        "d_4:\n    bnez x13, s_voto\n", "d_4:\n    beqz x13, frontera\n    j    s_voto\n",
        "sin_voto:2:1024:1024", "reversion"),
    "voto_sin_tick": (
        "el supervisor acepta un voto sin mirar de que tick es",
        "    lw   x7, EST3(x0)\n    sub  x7, x7, x3\n",
        "    lw   x7, EST3(x0)\n    andi x7, x7, 1\n", "atraso:3:1000", "reversion"),
    "dos_stores_telemetria": (
        "la telemetria hace dos stores en los ticks impares",
        "    li   x1, PER_BASE\n    sw   x5, PER_LEDS(x1)\n",
        "    li   x1, PER_BASE\n    sw   x5, PER_LEDS(x1)\n    sw   x0, PER_DIGITOS(x1)\n", "", "practica"),
    "latido": (
        "el LED de latido usa otro bit del numero de tick",
        ".equ BIT_LATIDO,    0x40000", ".equ BIT_LATIDO,    0x20000", "", "practica"),
    "gestor_escribe_pub": (
        "un gestor escribe en la palabra PUB, que es del supervisor",
        "    sw   x13, OFF_DES(x2)\n", "    sw   x13, OFF_DES(x2)\n    sw   x5, PUB(x0)\n", "", "practica"),
    "dos_decisiones": (
        "el supervisor escribe DECISION dos veces en el tick",
        "    sw   x1, OFF_DECISION(x2)\n", "    sw   x1, OFF_DECISION(x2)\n    sw   x1, OFF_DECISION(x2)\n",
        "", "practica"),
}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Controles negativos de sw/fondo.s")
    ap.add_argument("nombre", nargs="?")
    ap.add_argument("--lista", action="store_true", help="nombre|falla|serie|descripcion de cada control")
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
    if original.startswith("TABLA:"):
        original = mutado = ""
    elif texto.count(original) != 1:
        raise SystemExit(f"control {a.nombre}: el texto a reemplazar aparece {texto.count(original)} veces en {a.entrada}")
    texto = texto.replace(original, mutado)
    with open(a.salida, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
