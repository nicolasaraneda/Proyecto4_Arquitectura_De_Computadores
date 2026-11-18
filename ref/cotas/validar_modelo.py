#!/usr/bin/env python3
"""validar_modelo.py: el puente diario contra la serie Meta real en la misma ventana.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.
La serie del profesor son los minutos de Meta del 23/2/2022 a las 15:10 al 9/5/2022.
Se generan 50 réplicas de esa misma ventana con el puente (poblacion.py) y se comparan
estadísticas por minuto y el patrimonio de cada regla. Uso: python3 ref/cotas/validar_modelo.py
"""
import datetime as dt
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402
import cotas  # noqa: E402
import poblacion  # noqa: E402

ESTR = [("espera", "cotas", (0, 0, 0, 0, 0, 178)), ("compra", "cotas", (1, 0, 0, 0, 0, 178)),
        ("compra_banda40", "cotas", (1, 0, 0, 40, 0, 178)), ("max_media", "media", (5, 3, 0)),
        ("zscore", "zscore", (5, 6, 5, 2, 64, 0)), ("siempre", "siempre", ())]


def estadisticas(p):
    d = [b - a for a, b in zip(p, p[1:])]
    ap = [abs(d[i]) for i in range(len(d)) if (i + 1 - 40) % 390 == 0]
    dentro = [abs(d[i]) for i in range(len(d)) if (i + 1 - 40) % 390 != 0]
    m = st.mean(d)
    var = st.pvariance(d)
    ac = sum((d[i] - m) * (d[i + 1] - m) for i in range(len(d) - 1)) / (len(d) - 1) / var if var else 0
    return dict(dentro=st.mean(dentro), apertura=st.mean(ap), ac1=ac, toca100=p.count(100), toca255=p.count(255),
                tmin=p.index(100), tmax=p.index(255))


def main():
    real = cotas.leer(os.path.join(comun.RAIZ, "data", "practica_meta.csv"))
    L = ["Puente diario (ref/cotas/poblacion.py) contra la serie Meta real, misma ventana (23/2/2022 15:10 a 9/5/2022)",
         "Generado por ref/cotas/validar_modelo.py. 50 replicas de cada forma con los diarios de Yahoo.",
         "Con la forma 'molde' los dias son dias reales de la misma serie, sorteados: la comparacion es optimista para",
         "la forma intradiaria; lo que se valida es el camino de varios dias y los extremos."]
    for forma in ("browniano", "molde"):
        L += ["", f"== forma {forma}"]
        L += comparar(real, forma)
    texto = "\n".join(L) + "\n"
    print(texto, end="")
    open(os.path.join(comun.RAIZ, "docs", "mediciones", "cotas", "modelo.txt"), "w").write(texto)


def comparar(real, forma):
    replicas = []
    for s in range(50):
        precios, fechas = poblacion.puente("META", s, forma)
        i = fechas.index(dt.date(2022, 2, 23)) + 350          # 15:10 del 23/2: 40 minutos antes del cierre
        replicas.append(comun.normalizar(precios[i:i + 20000]))
    nombres, filas = comun.evaluar(ESTR, [real] + replicas, "modelo")
    L = []
    er = estadisticas(real)
    es = [estadisticas(r) for r in replicas]
    L.append(f"{'estadistica':40s} {'real':>10s} {'puente: mediana':>16s} {'p10':>8s} {'p90':>8s}")
    for k, nom in (("dentro", "cambio absoluto medio dentro del dia"), ("apertura", "salto absoluto medio en la apertura"),
                   ("ac1", "autocorrelacion de los cambios, rezago 1"), ("toca100", "ticks en 100"), ("toca255", "ticks en 255"),
                   ("tmin", "primer tick en 100"), ("tmax", "primer tick en 255")):
        v = sorted(e[k] for e in es)
        L.append(f"{nom:40s} {er[k]:10.3f} {st.median(v):16.3f} {v[5]:8.3f} {v[44]:8.3f}")
    L += ["", f"{'regla':20s} {'real':>8s} {'puente: mediana':>16s} {'p10':>8s} {'p90':>8s}"]
    for j, n in enumerate(nombres):
        v = sorted(f[j] for f in filas[1:])
        L.append(f"{n:20s} {filas[0][j]:8d} {st.median(v):16.0f} {v[5]:8d} {v[44]:8d}")
    return L


if __name__ == "__main__":
    main()
