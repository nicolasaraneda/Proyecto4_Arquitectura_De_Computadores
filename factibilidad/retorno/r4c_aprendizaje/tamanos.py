#!/usr/bin/env python3
"""tamanos.py: memoria que pide cada variante del aprendizaje en vivo, contra las 4 BRAM libres.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 tamanos.py --arnes build/arnes > mediciones/tamanos.txt

Para cada variante del barrido (las listas de barrer.py) y cada alias de
aprendiz.c calcula, a partir de sus parámetros:

  celdas    entradas de la tabla
  bits      bits por entrada que de verdad se usan
  lógicos   celdas por bits
  palabras  lo que ocupa en la RAM de datos de 32 bits (tabla más anillo),
            sin empaquetar: una palabra por estimación y un byte por contador
            (dos si pasa de 8 bits), porque Espino no tiene desplazamientos
            variables para sacar un campo de 2 bits de una palabra
  % BRAM    bits lógicos sobre los 16 384 bits de las 4 BRAM libres
  % RAM     palabras sobre las 512 de la RAM del SoC (el programa actual usa 40)

Una variante con ka = 0 es una regla fija: no necesita tabla ni anillo.

Cómo se cuentan los bits por entrada:
  tabla, modo 0   16 + ka. La estimación va en precio por 2^10 y se recorta a
                  +-31 de precio (16 bits con signo), y el acumulador la lleva
                  multiplicada por 2^ka. En la RAM de datos es una palabra.
  tabla, modo 1   los bits del contador saturado.
  predictor       los bits del contador; el torneo suma la tabla por
                  desviación y un selector de 2 bits por entrada de historia.

El anillo guarda, para los últimos h + 2 ticks, el índice de la casilla
visitada y el precio: cabe en una palabra por tick (9 bits de índice y 8 de
precio; el predictor de 12 bits de historia usa 12 + 4 + 8 + 2).

No mide nada: es aritmética sobre los parámetros, la misma de e_tabla.c y
pred.h. Sirve para que las cifras de memoria del README salgan de un comando.
"""
import argparse
import subprocess
import sys

import barrer

BRAM_LIBRES_BITS = 4 * 4096
RAM_DATOS_PALABRAS = 512
PROGRAMA_PALABRAS = 40           # palabras distintas de cero de sw/trade.hex (regla base)


def campos(spec):
    nombre, _, par = spec.partition(":")
    return nombre, dict(x.split("=") for x in par.split(",") if "=" in x)


def tabla(c):
    nb = int(c.get("nb", 32))
    ter = int(c.get("ter", 0))
    nt = 3 if ter == 1 else 2 if ter else 1
    filas = int(c.get("filas", 1))
    ka = int(c.get("ka", 0))
    modo = int(c.get("modo", 0))
    h = int(c.get("h", 16))
    if not ka:
        return 0, 0, 0, 0, 0
    celdas = nb * nt * filas
    bits = int(c.get("bits", 6)) if modo else 16 + ka
    anillo = h + 2
    palabras = celdas + anillo if not modo else (celdas * (1 if bits <= 8 else 2) + 3) // 4 + anillo
    return celdas, bits, celdas * bits, palabras, anillo


def predictor(c):
    H = int(c.get("H", 8))
    sim = int(c.get("sim", 2))
    bits = int(c.get("bits", 2))
    tipo = int(c.get("tipo", 0))
    lgd = int(c.get("lgd", 4))
    h = int(c.get("h", 1))
    lg = H * (2 if sim == 3 else 1)
    t1, t2 = (1 << lg) * bits, (1 << lgd) * bits
    logicos = t2 if tipo == 2 else t1 + t2 + (1 << lg) * 2 if tipo == 3 else t1
    celdas = (1 << lgd) if tipo == 2 else (1 << lg)
    contadores = (1 << lgd) if tipo == 2 else 2 * (1 << lg) + (1 << lgd) if tipo == 3 else (1 << lg)
    anillo = h + 2
    return celdas, bits, logicos, (contadores + 3) // 4 + anillo, anillo


def fila(spec, real):
    nombre, c = campos(real)
    if nombre == "tabla":
        celdas, bits, logicos, palabras, anillo = tabla(c)
    elif nombre in ("patron", "mm_patron"):
        celdas, bits, logicos, palabras, anillo = predictor(c)
    else:
        return None
    return spec, celdas, bits, logicos, palabras, anillo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arnes", default="build/arnes")
    a = ap.parse_args()
    alias = {}
    for linea in subprocess.run([a.arnes, "listar"], check=True, capture_output=True, text=True).stdout.splitlines():
        p = linea.split()
        if len(p) >= 2 and p[0].startswith("cand:"):
            alias[p[0][5:]] = p[1]
    print("Memoria que pide cada variante. 4 BRAM libres = 16384 bits. RAM de datos del SoC = 512 palabras de 32 bits.")
    print("celdas: entradas de la tabla. bits: por entrada. logicos: celdas por bits. palabras: tabla mas anillo en la RAM de datos,")
    print("sin empaquetar (una palabra por estimacion, un byte por contador). Una fila en cero es una regla fija: no pide tabla.")
    print()
    cab = f"{'variante':<60} {'celdas':>6} {'bits':>4} {'logicos':>8} {'% BRAM':>7} {'anillo':>6} {'palabras':>8} {'% RAM':>6}"

    def imprimir(filas):
        print(cab)
        for spec, celdas, bits, logicos, palabras, anillo in filas:
            print(f"{spec:<60} {celdas:>6} {bits:>4} {logicos:>8} {100 * logicos / BRAM_LIBRES_BITS:>6.1f}% {anillo:>6} {palabras:>8} "
                  f"{100 * palabras / RAM_DATOS_PALABRAS:>5.1f}%")

    print("Alias entregados (aprendiz.c):")
    finales = [fila(n, alias[n]) for n in ("espera", "aprendiz", "aprendiz_rapido", "aprendiz_patron", "aprendiz_puro") if n in alias]
    imprimir([f for f in finales if f])
    print()

    todas = []
    vistas = set()
    for _, specs in barrer.etapas().items():
        for s in specs:
            if s not in vistas:
                vistas.add(s)
                f = fila(s, s)
                if f:
                    todas.append(f)
    for nombre, pref in (("tabla de politica", "tabla"), ("predictor solo", "patron"), ("predictor como filtro", "mm_patron")):
        grupo = [f for f in todas if campos(f[0])[0] == pref and barrer.aprende(f[0])]
        if not grupo:
            continue
        chico = min(grupo, key=lambda f: (f[3], f[0]))
        grande = max(grupo, key=lambda f: (f[3], f[0]))
        print(f"Barrido, {nombre}: {len(grupo)} variantes que aprenden. La mas chica y la mas grande en bits logicos:")
        imprimir([chico, grande])
        pasan = sum(1 for f in grupo if f[3] > BRAM_LIBRES_BITS)
        print(f"  variantes que no caben en las 4 BRAM libres (mas de 16384 bits logicos): {pasan}")
        pal = max(grupo, key=lambda f: (f[4], f[0]))
        print(f"  la que mas palabras pide en la RAM de datos: {pal[0]} ({pal[4]} palabras, {100 * pal[4] / RAM_DATOS_PALABRAS:.1f} % de 512)")
        libres = RAM_DATOS_PALABRAS - PROGRAMA_PALABRAS
        print(f"  variantes que no caben en la RAM de datos (mas de {libres} palabras libres): {sum(1 for f in grupo if f[4] > libres)}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
