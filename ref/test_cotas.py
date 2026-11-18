#!/usr/bin/env python3
"""test_cotas.py: la regla de cotas reproduce las cifras de Nicolás en la serie Meta.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.
Uso: python3 ref/test_cotas.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cotas  # noqa: E402
import market  # noqa: E402
import trader  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    p = cotas.leer(os.path.join(RAIZ, "data", "practica_meta.csv"))
    casos = [
        ("espera", dict(inicio="espera"), 15894, 2),
        ("compra", dict(inicio="compra"), 23906, 5),
        ("compra con banda 40", dict(inicio="compra", banda=40), 32149, None),
    ]
    fallas = 0
    for nombre, kw, w, o in casos:
        m = trader.correr(p, cotas.Cotas(**kw))
        ok = m.w == w and (o is None or m.ordenes == o)
        fallas += not ok
        print(("PASS" if ok else "FAIL") + f" {nombre}: {m.w} con {m.ordenes} ordenes (esperado {w}" + (f" con {o})" if o else ")"))
    # Una serie que no toca los extremos: nunca opera (espera) o compra y mantiene (compra)
    plana = [150] * 100
    ok = trader.correr(plana, cotas.Cotas("espera")).ordenes == 0
    fallas += not ok
    print(("PASS" if ok else "FAIL") + " sin extremos, espera no opera")
    # parte: compra k acciones una sola vez
    m = trader.correr([150] * 50, cotas.Cotas("parte", k=20))
    ok = m.acciones == 20 and m.ordenes == 1
    fallas += not ok
    print(("PASS" if ok else "FAIL") + f" parte con k=20: {m.acciones} acciones en {m.ordenes} orden")
    print("RESULTADO", "PASS" if fallas == 0 else "FAIL")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
