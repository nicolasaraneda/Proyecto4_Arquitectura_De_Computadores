#!/usr/bin/env python3
"""kernel_bandas.py: modelo del kernel de cuatro bandas de sw/bandas_*.s.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Calcula el resultado de cada vuelta del lazo de dos formas, la definición
escalar y la secuencia de instrucciones de carriles con el modelo ref/xd.py,
comprueba que coinciden y compara con el archivo que deja tb/tb_xd_kernel.sv.

    python3 tools/kernel_bandas.py                     # autoprueba
    python3 tools/kernel_bandas.py --comparar ARCHIVO  # PASS o FAIL
    python3 tools/kernel_bandas.py --comparar ARCHIVO --vacio   # lazo sin kernel
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ref"))
import xd  # noqa: E402

N = 256
MEDIAS = [100, 160, 60, 200]
BANDAS = [2, 40, 70, 16]         # la de 70 es mayor que su media: el umbral satura en 0


def precios():
    p = 0
    for _ in range(N):
        p = (p + 37) & 255
        yield p


def escalar():
    """La definición: cuatro veces la regla de sw/trade.s."""
    pos = [0, 0, 0, 0]
    salida = []
    for p in precios():
        for i in range(4):
            entrar = p < MEDIAS[i] - BANDAS[i]
            salir = p > MEDIAS[i]
            pos[i] = int((pos[i] or entrar) and not salir)
        salida.append(sum(b << i for i, b in enumerate(pos)))
    return salida


def con_carriles():
    """La misma secuencia de instrucciones de sw/bandas_carriles.s."""
    op = xd.CARRILES
    m, b, pos = xd.empaquetar(MEDIAS), xd.empaquetar(BANDAS), 0
    salida = []
    for p in precios():
        pp = xd.simd8(op["pbcast8"], p, 0)
        u = xd.simd8(op["psubus8"], m, b)
        e = xd.simd8(op["pcmpltu8"], pp, u)
        s = xd.simd8(op["pcmpltu8"], m, pp)
        pos = (pos | e) & (s ^ xd.M32)
        salida.append(xd.simd8(op["pmovmsk8"], pos, 0))
    return salida


def main(argv):
    esperado = escalar()
    assert esperado == con_carriles(), "la versión con carriles no coincide con la escalar"
    # El recorrido tiene que ejercitar las bandas: las estrategias 0, 1 y 3
    # entran y salen, y la 2 (banda mayor que la media) no entra nunca
    assert len(set(esperado)) >= 4, "el recorrido de precios no ejercita las bandas"
    assert all(any(r >> i & 1 for r in esperado) for i in (0, 1, 3))
    assert not any(r >> 2 & 1 for r in esperado)
    if "--comparar" not in argv:
        print(f"PASS kernel_bandas.py: {N} vueltas, escalar y carriles coinciden, "
              f"{len(set(esperado))} resultados distintos")
        return 0
    ruta = argv[argv.index("--comparar") + 1]
    if "--vacio" in argv:
        esperado = list(precios())
    with open(ruta) as f:
        obtenido = [int(x, 16) for x in f.read().split()]
    if obtenido == esperado:
        print(f"PASS {len(obtenido)} resultados iguales al modelo")
        return 0
    print(f"FAIL {ruta}: {len(obtenido)} resultados, esperados {len(esperado)}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
