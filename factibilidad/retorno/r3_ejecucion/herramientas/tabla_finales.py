#!/usr/bin/env python3
"""tabla_finales.py: las candidatas finales bajo las cuatro hipótesis de puntaje, en Markdown.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    make finales        (mediciones/finales_tablas.md)

Lee los archivos que deja `hipotesis --tsv` (uno por vista: 2000 ticks, y
20 000 ticks con las series interiores, con la vista de parada y con todas) y
arma, para cada candidata y cada conjunto, la diferencia pareada contra
`max_media` con su error:

    H1   patrimonio final
    H2   exceso sobre comprar y mantener: en diferencia es la misma cifra de
         H1 (comprar y mantener es igual para las dos); se informa además la
         diferencia de la razón W / B&H
    H3a  puntos del torneo, lineal en patrimonio
    H3b  puntos del torneo, lineal en el puesto
    y el percentil 5 de los puntos de una competencia de tres rondas.
"""
import argparse
import sys


def leer(ruta):
    datos = {}
    with open(ruta, encoding="utf-8") as f:
        next(f)
        for linea in f:
            largo, semilla, series, conjunto, candidato, clave, valor = linea.rstrip("\n").split("\t")
            datos[(conjunto, candidato, clave)] = float(valor)
    return datos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vista", action="append", required=True, help="TITULO=archivo.tsv (se puede repetir)")
    ap.add_argument("--finales", required=True)
    ap.add_argument("--referencia", default="max_media")
    a = ap.parse_args()
    finales = [f for f in a.finales.split(";") if f]

    print("# Candidatas finales bajo las cuatro hipótesis de puntaje\n")
    print(f"Semilla 0, campo mixto, G = 10. Diferencias pareadas contra `{a.referencia}`, con su error estándar. "
          "Generado por `herramientas/tabla_finales.py` a partir de `hipotesis --tsv`.\n")
    for vista in a.vista:
        titulo, ruta = vista.split("=", 1)
        d = leer(ruta)
        print(f"## {titulo}\n")
        print("| Conjunto | Candidata | Series | H1: patrimonio, dif. | H1: p5, dif. | H2: razón W/B&H, dif. | H3a: puntos, dif. | "
              "H3a: p5 de tres rondas, dif. | H3b: puntos, dif. | H3b: p5 de tres rondas, dif. | Órdenes |")
        print("|---|---|---|---|---|---|---|---|---|---|---|")
        for conjunto in ("evidencia", "remuestreo", "plausibles", "estres"):
            def v(c, k):
                return d.get((conjunto, c, k), float("nan"))
            ref = a.referencia
            print(f"| {conjunto} | `{ref}` (nivel) | {v(ref, 'n'):.0f} | {v(ref, 'h1_media'):.0f} | {v(ref, 'h1_p5'):.0f} | "
                  f"{v(ref, 'h2r_media'):.3f} | {v(ref, 'h3a_media'):.3f} | {v(ref, 'h3a_c_p5'):.3f} | {v(ref, 'h3b_media'):.3f} | "
                  f"{v(ref, 'h3b_c_p5'):.3f} | {v(ref, 'ordenes'):.1f} |")
            for c in finales:
                print(f"| {conjunto} | `{c}` | {v(c, 'n'):.0f} | {v(c, 'h1_dif'):+.1f} ± {v(c, 'h1_dif_ee'):.1f} | "
                      f"{v(c, 'h1_p5') - v(ref, 'h1_p5'):+.0f} | {v(c, 'h2r_dif'):+.4f} ± {v(c, 'h2r_dif_ee'):.4f} | "
                      f"{v(c, 'd_h3a'):+.4f} ± {v(c, 'd_h3a_ee'):.4f} | {v(c, 'd_h3a_c_p5'):+.3f} ± {v(c, 'd_h3a_c_p5_ee'):.3f} | "
                      f"{v(c, 'd_h3b'):+.4f} ± {v(c, 'd_h3b_ee'):.4f} | {v(c, 'd_h3b_c_p5'):+.3f} ± {v(c, 'd_h3b_c_p5_ee'):.3f} | "
                      f"{v(c, 'ordenes'):.1f} |")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
