#!/usr/bin/env python3
"""
variante.py: arma programas con fallas puestas a propósito a partir de
sw/fondo.s, para las pruebas de degradación (criterio 6 de la puerta) y del
vigilante.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

No cambia ninguna línea del programa: solo inserta instrucciones en las marcas
"#@" (los lazos de los hilos 1 a 3 y el punto del hilo 0 después de leer el
precio).

Desde el 17/11 (decisión T133) los hilos 1 a 3 no participan en la decisión:
están en un lazo de espera. Las fallas de esos hilos muestran que lo que hagan
no cambia los bytes ni el tiempo de respuesta del hilo 0. K es el hilo (1, 2 o
3); se pueden juntar varias con "+":
  ocupado:K          el hilo K hace cuentas sin parar (sumas, xor, comparaciones)
  escribe:K          el hilo K escribe y lee una palabra de la RAM sin parar
                     (el programa sano no usa la RAM; se corre con --permitir-ram)
  programa:K         el hilo K lee sin parar palabras de la memoria del programa
  cuelgue_sup:N      el hilo 0 entra en un lazo infinito al recibir el precio
                     del tick N, antes de decidir: deja de escribir DECISION. Es la
                     falla dura que debe ver el vigilante de R2

Uso: tools/fondo/variante.py FALLAS [-i sw/fondo.s] -o salida.s
     tools/fondo/variante.py FALLAS --ref      # argumentos para revisar.py
"""

import argparse
import sys

RAM_HILO = {1: 0x7C4, 2: 0x7C8, 3: 0x7CC}     # palabra de la RAM que escribe cada hilo


def leer(texto):
    fallas = []
    for parte in texto.split("+"):
        campos = parte.split(":")
        tipo, nums = campos[0], [int(c) for c in campos[1:]]
        if tipo == "cuelgue_sup" and len(nums) == 1 and nums[0] >= 1:
            fallas.append((tipo, nums))
        elif tipo in ("ocupado", "escribe", "programa") and len(nums) == 1 and nums[0] in RAM_HILO:
            fallas.append((tipo, nums))
        else:
            raise SystemExit(f"falla mal escrita: {parte}")
    return fallas


def armar(fuente, fallas):
    marcas = {"#@HILO1": [], "#@HILO2": [], "#@HILO3": [], "#@SUPERVISOR": []}
    for i, (tipo, n) in enumerate(fallas):
        if tipo == "cuelgue_sup":
            # x3 trae el número del tick anterior; x15 está libre en ese punto
            marcas["#@SUPERVISOR"] += [f"    li   x15, {n[0] - 1}", f"    bne  x3, x15, v{i}_sigue",
                                       f"v{i}_cuelgue:", f"    j    v{i}_cuelgue", f"v{i}_sigue:"]
            continue
        k = n[0]
        if tipo == "ocupado":
            marcas[f"#@HILO{k}"] += ["    addi x5, x5, 1", "    xor  x6, x6, x5", "    add  x7, x7, x6",
                                     "    sltu x8, x7, x5", "    or   x9, x9, x8"]
        elif tipo == "escribe":
            marcas[f"#@HILO{k}"] += [f"    li   x5, {RAM_HILO[k]}", "    addi x6, x6, 1", "    sw   x6, 0(x5)",
                                     "    lw   x7, 0(x5)"]
        elif tipo == "programa":
            marcas[f"#@HILO{k}"] += ["    addi x5, x5, 4", "    andi x5, x5, 0xFC", "    lw   x6, 0(x5)"]
    salida, vistas = [], set()
    for linea in fuente.splitlines():
        salida.append(linea)
        m = linea.strip()
        if m in marcas:
            vistas.add(m)
            salida += marcas[m]
    faltan = set(marcas) - vistas
    if faltan:
        raise SystemExit(f"el programa no tiene las marcas {sorted(faltan)}")
    return "\n".join(salida) + "\n"


def para_revisar(fallas):
    """Argumentos para revisar.py: las fallas de los hilos 1 a 3 no cambian los bytes;
    si algún hilo escribe la RAM, esos stores se permiten."""
    return ["--permitir-ram"] if any(t == "escribe" for t, _ in fallas) else []


def main(argv=None):
    ap = argparse.ArgumentParser(description="Variantes de sw/fondo.s con fallas")
    ap.add_argument("fallas")
    ap.add_argument("-i", "--entrada", default="sw/fondo.s")
    ap.add_argument("-o", "--salida")
    ap.add_argument("--ref", action="store_true", help="imprime los argumentos para tools/fondo/revisar.py")
    a = ap.parse_args(argv)
    fallas = leer(a.fallas)
    if a.ref:
        print(" ".join(para_revisar(fallas)))
        return 0
    with open(a.entrada, encoding="utf-8") as f:
        texto = armar(f.read(), fallas)
    if a.salida:
        with open(a.salida, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
    else:
        sys.stdout.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
