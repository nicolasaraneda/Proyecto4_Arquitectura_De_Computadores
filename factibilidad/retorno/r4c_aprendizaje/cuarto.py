#!/usr/bin/env python3
"""cuarto.py: las estrategias de este estudio como cuarto gestor en papel del fondo de estrategias.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 cuarto.py --arnes build/arnes_fondo --semilla 0 --salida mediciones

El estudio del fondo (../r4b_fondo) dejó el cuarto gestor probado solo como
mecanismo (parámetro `x` de la estrategia `fondo`). Aquí se compila su
`fondo.c`, sin modificarlo, junto con las estrategias de esta carpeta
(r4c.mk) y se mide una lista corta, fijada antes de mirar resultados:

  - controles: el fondo recomendado y el voto de ese estudio, sin cuarto
    gestor, y `espera`, `aprendiz` y `aprendiz_rapido` solos;
  - identidad: el fondo con todo el peso en el cuarto gestor tiene que dar
    lo mismo que ese gestor solo (comprueba que el módulo se usa bien desde
    otra carpeta);
  - el fondo recomendado (max_media, kalman y activo, banda 4/16) con cada
    estrategia de este estudio como cuarto gestor, pesos 6/3/3/4;
  - el voto entre cuatro gestores (max_media, base, activo y el cuarto), con
    mayoría de 2 y de 3;
  - el fondo mínimo con pesos aprendidos y `espera` como cuarto gestor.

No es un estudio del reparto de capital: eso es del estudio del fondo. Es la
prueba de que el módulo entregado sirve como cuarto gestor y una primera
cifra de cuánto aporta. Solo usa la semilla 0. Las tablas tienen el mismo
formato que las del barrido (barrer.py).
"""
import argparse
import os
import sys

import barrer

REC = "fondo:c=3,w0=8,w1=4,w2=4,b=4"                          # fondo_rec del estudio del fondo
REC4 = "fondo:c=3,x=cand:{g},w0=6,w1=3,w2=3,w3=4,b=4"
VOTO3 = "fondo:c=5,w0=6,w1=5,w2=5,vt=8"                       # voto 2 de 3: decide como max_media
VOTO4 = "fondo:c=5,x=cand:{g},w0=4,w1=4,w2=4,w3=4,vt={vt}"
MIN4 = "fondo:c=5,x=cand:espera,w0=4,w1=4,w2=4,w3=4,m=2,v=9,mg=5,d=4,pp=1,vt=8"

GESTORES = ("espera", "aprendiz", "aprendiz_rapido")
LISTA = (["espera", "aprendiz", "aprendiz_rapido", REC, VOTO3] +
         ["fondo:c=1,x=cand:espera,w0=0,w3=16", "fondo:c=1,x=cand:aprendiz_rapido,w0=0,w3=16"] +
         [REC4.format(g=g) for g in GESTORES] +
         [VOTO4.format(g=g, vt=vt) for g in ("espera", "aprendiz_rapido") for vt in (8, 12)] +
         [MIN4])
VISTAS = ((2000, "todas"), (20000, "parada"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arnes", default="build/arnes_fondo")
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--salida", default="mediciones")
    a = ap.parse_args()
    if a.semilla != 0:
        sys.exit("este estudio usa solo la semilla 0")
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(a.salida, exist_ok=True)
    for largo, vista in VISTAS:
        datos = barrer.correr(a.arnes, LISTA, largo, a.semilla, vista, tmp)
        sufijo = "" if largo == 2000 else "_" + vista
        ruta = os.path.join(a.salida, f"cuarto_gestor_n{largo}{sufijo}.txt")
        barrer.tabla("Las estrategias del aprendizaje en vivo como cuarto gestor del fondo", LISTA, datos, largo, vista, a.semilla, ruta)
        with open(ruta, "a", encoding="utf-8") as f:
            f.write("\nIdentidad: el fondo con todo el peso en el cuarto gestor contra ese gestor solo (deben coincidir):\n")
            mal = 0
            for g in ("espera", "aprendiz_rapido"):
                solo = datos[g]
                fondo = datos[f"fondo:c=1,x=cand:{g},w0=0,w3=16"]
                iguales = all(solo[c][k] == fondo[c][k] for c in barrer.CONJUNTOS for k in ("h1_dif", "d_h3a", "d_h3b", "ordenes"))
                mal += not iguales
                f.write(f"  {g}: {'identico' if iguales else 'DISTINTO'}\n")
            f.write("IDENTIDAD: " + ("OK" if not mal else "FALLA") + "\n")
        print(f"{ruta}: {len(LISTA)} variantes", flush=True)
        if mal:
            sys.exit("la identidad con el cuarto gestor no se cumple")


if __name__ == "__main__":
    main()
