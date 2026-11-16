#!/usr/bin/env python3
"""
variante.py: arma programas con fallas puestas a propósito a partir de
sw/fondo.s, para las pruebas de degradación (criterio 6 de la puerta).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

No cambia ninguna línea del programa: solo inserta instrucciones en las marcas
"#@" de la rutina de los gestores. El supervisor queda intacto, que es lo que
se quiere probar.

Fallas (K es el gestor: 1, 2 o 3; los ticks se cuentan como el programa, desde
1 en el primer precio que ve). Se pueden juntar varias con "+":

  cuelgue:K:N        el gestor K entra en un lazo infinito al procesar el tick
                     N y no vuelve (N = 1: nunca llega a votar)
  sin_voto:K:N:M     el gestor K calcula pero no publica su voto en los ticks
                     N a M
  atraso:K:C         el gestor K demora C ciclos más antes de publicar, en
                     todos los ticks
  atraso:K:C:N:M     lo mismo, solo en los ticks N a M
  cuelgue_sup:N      el supervisor entra en un lazo infinito al recibir el
                     precio del tick N, antes de publicarlo: deja de escribir
                     DECISION. Es la falla dura que debe ver el vigilante

Uso: tools/fondo/variante.py FALLAS [-i sw/fondo.s] -o salida.s
     tools/fondo/variante.py FALLAS --ref      # las --falla para ref/fondo.py
"""

import argparse
import sys

CICLOS_POR_VUELTA = 8        # addi y bnez, 4 ciclos cada una en el barrel
BLOQUE = {1: "G1", 2: "G2", 3: "G3"}


def leer(texto):
    fallas = []
    for parte in texto.split("+"):
        campos = parte.split(":")
        tipo, nums = campos[0], [int(c) for c in campos[1:]]
        if tipo == "cuelgue_sup" and len(nums) == 1:
            fallas.append((tipo, nums))
            continue
        if tipo == "cuelgue" and len(nums) == 2:
            pass
        elif tipo == "sin_voto" and len(nums) == 3:
            pass
        elif tipo == "atraso" and len(nums) in (2, 4):
            pass
        else:
            raise SystemExit(f"falla mal escrita: {parte}")
        if nums[0] not in BLOQUE:
            raise SystemExit(f"el gestor de una falla es 1, 2 o 3: {parte}")
        fallas.append((tipo, nums))
    return fallas


def en_rango(i, n, m, sale):
    """Salta a `sale` si el tick en curso (x5 - x8 = tick * 256) no está entre n y m."""
    return [f"    sub  x7, x5, x8",
            f"    li   x1, {n * 256}",
            f"    bltu x7, x1, {sale}",
            f"    li   x1, {m * 256}",
            f"    bltu x1, x7, {sale}"]


def armar(fuente, fallas):
    antes, voto, despues, sup = [], [], [], []
    for i, (tipo, n) in enumerate(fallas):
        if tipo == "cuelgue_sup":
            # x3 todavía trae el tick anterior por 256; x9 está libre
            sup += [f"    li   x9, {(n[0] - 1) * 256}", f"    bne  x3, x9, v{i}_sigue",
                    f"v{i}_cuelgue:", f"    j    v{i}_cuelgue", f"v{i}_sigue:"]
            continue
        k = n[0]
        sigue = f"v{i}_sigue"
        if tipo == "cuelgue":
            antes += [f"    li   x1, {BLOQUE[k]}", f"    bne  x2, x1, {sigue}",
                      "    sub  x7, x5, x8", f"    li   x1, {n[1] * 256}", f"    bltu x7, x1, {sigue}",
                      f"v{i}_cuelgue:", f"    j    v{i}_cuelgue", f"{sigue}:"]
        elif tipo == "atraso":
            vueltas = max(1, n[1] // CICLOS_POR_VUELTA)
            antes += [f"    li   x1, {BLOQUE[k]}", f"    bne  x2, x1, {sigue}"]
            if len(n) == 4:
                antes += en_rango(i, n[2], n[3], sigue)
            antes += [f"    li   x1, {vueltas}", f"v{i}_lazo:", "    addi x1, x1, -1",
                      f"    bnez x1, v{i}_lazo", f"{sigue}:"]
        elif tipo == "sin_voto":
            # x7 trae el voto ya armado: se usa x9 y x15 para no pisarlo
            voto += [f"    li   x1, {BLOQUE[k]}", f"    bne  x2, x1, {sigue}",
                     "    sub  x9, x5, x8",
                     f"    li   x1, {n[1] * 256}", f"    bltu x9, x1, {sigue}",
                     f"    li   x1, {n[2] * 256}", f"    bltu x1, x9, {sigue}",
                     "    j    v_sin_voto", f"{sigue}:"]
    if any(t == "sin_voto" for t, _ in fallas):
        despues = ["v_sin_voto:"]
    marcas = {"#@ANTES_DE_PUBLICAR": antes, "#@VOTO": voto, "#@DESPUES_DEL_VOTO": despues, "#@SUPERVISOR": sup}
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


def para_ref(fallas, plazo_ciclos):
    """Las fallas como las entiende ref/fondo.py: desde y hasta qué tick no llega el voto."""
    args = []
    for tipo, n in fallas:
        if tipo == "cuelgue_sup":
            continue
        if tipo == "cuelgue":
            args.append(f"{n[0]}:{n[1]}:")
        elif tipo == "sin_voto":
            args.append(f"{n[0]}:{n[1]}:{n[2]}")
        elif tipo == "atraso" and n[1] > plazo_ciclos:
            args.append(f"{n[0]}:{n[2]}:{n[3]}" if len(n) == 4 else f"{n[0]}:1:")
    return args


def main(argv=None):
    ap = argparse.ArgumentParser(description="Variantes de sw/fondo.s con fallas")
    ap.add_argument("fallas")
    ap.add_argument("-i", "--entrada", default="sw/fondo.s")
    ap.add_argument("-o", "--salida")
    ap.add_argument("--ref", action="store_true", help="imprime las --falla equivalentes para ref/fondo.py")
    ap.add_argument("--plazo-ciclos", type=int, default=600,
                    help="un atraso mayor que esto se cuenta como voto que no llega (por defecto 600)")
    a = ap.parse_args(argv)
    fallas = leer(a.fallas)
    if a.ref:
        print(" ".join(f"--falla {x}" for x in para_ref(fallas, a.plazo_ciclos)))
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
