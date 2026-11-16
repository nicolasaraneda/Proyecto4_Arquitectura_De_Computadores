#!/usr/bin/env python3
"""validar_torneo.py: comprobación independiente de los puntajes del torneo (H3a y H3b).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 factibilidad/retorno/pruebas/validar_torneo.py      (o make validar-torneo, después de make exploracion)

El torneo del arnés (nucleo/torneo.c) sortea campos de rivales. Aquí se
recalculan los mismos puntajes por otro camino, en Python, a partir de los
patrimonios por serie que entrega `retorno detalle`:

  1. Pesos de los rivales en los tres campos, rehechos desde la regla escrita
     (clases con la misma probabilidad; en el mixto y el fuerte, las tres
     mejores parametrizaciones de cada clase en la serie de práctica).
  2. H3b (lineal en el puesto): su valor esperado tiene fórmula exacta y no
     depende de G. Se compara con lo que el arnés estimó por sorteo.
  3. H3a (lineal en patrimonio): no tiene fórmula simple. Se estima con un
     sorteo propio, con otro generador de azar y otros campos, y se compara.

Conjunto: los 5000 remuestreos de 2000 ticks de la semilla 0. Tolerancia:
cuatro errores del sorteo (el del arnés y el de aquí, combinados). No usa la
semilla reservada.
"""
import math
import os
import random
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
ARNES = os.path.join(RETORNO, "build", "retorno")
LOTE = os.path.join(RETORNO, "build", "series", "remuestreo_s0_n2000.bin")
TSV = os.path.join(RETORNO, "build", "tsv", "hipotesis_n2000_todas_s0.tsv")

CANDIDATOS = ["base", "max_media", "guardia", "prudente"]
CAMPOS = ("ingenuo", "mixto", "fuerte")
GS = (5, 10, 15)
FUERTE = {"cruce": 0.08, "momentum": 0.08, "comprar_y_mantener": 0.12, "no_operar": 0.06, "reversion": 0.60, "azar": 0.06}
CAMPOS_ARNES = 6          # campos por serie que sortea el arnés (FIELDS en torneo.c)
CAMPOS_AQUI = 12          # campos por serie del sorteo de este script


def arnes(*args):
    return subprocess.run([ARNES, *map(str, args)], check=True, capture_output=True, text=True).stdout


def patrimonios(spec):
    return [int(l.split()[0]) for l in arnes("detalle", "--lote", LOTE, "--estrategia", spec).splitlines()]


def leer_rivales():
    """[(clase, spec, patrimonio en la practica, pesos impresos)] del comando `rivales`."""
    filas = []
    for linea in arnes("rivales").splitlines():
        if "|" not in linea or linea.startswith("clase"):
            continue
        izq, der = linea.split("|")
        clase, spec, practica = izq.split()
        filas.append((clase, spec, float(practica), [float(x.rstrip("%")) / 100 for x in der.split()]))
    return filas


def pesos(rivales):
    """Pesos de cada rival en los tres campos, rehechos desde la regla."""
    clases = {}
    for k, (clase, _, practica, _) in enumerate(rivales):
        clases.setdefault(clase, []).append((practica, k))
    w = {c: [0.0] * len(rivales) for c in CAMPOS}
    for clase, miembros in clases.items():
        orden = sorted(miembros, key=lambda m: -m[0])           # de mayor a menor patrimonio en la práctica
        mejores = orden[:3]
        for _, k in miembros:
            w["ingenuo"][k] = 1 / len(clases) / len(miembros)
        for _, k in mejores:
            w["mixto"][k] = 1 / len(clases) / len(mejores)
            w["fuerte"][k] = FUERTE[clase] / len(mejores)
    return w


def leer_tsv():
    datos = {}
    with open(TSV) as f:
        next(f)
        for linea in f:
            _, _, _, conjunto, candidato, clave, valor = linea.rstrip("\n").split("\t")
            if conjunto == "remuestreo":
                datos[(candidato, clave)] = float(valor)
    return datos


def main():
    rivales = leer_rivales()
    W = {c: patrimonios("cand:" + c) for c in CANDIDATOS}
    R = [patrimonios(spec) for _, spec, _, _ in rivales]
    ns, nr = len(W["base"]), len(rivales)
    w = pesos(rivales)
    tsv = leer_tsv()
    fallas = 0

    # 1. pesos
    peor = max(abs(w[campo][k] - rivales[k][3][i]) for i, campo in enumerate(CAMPOS) for k in range(nr))
    sumas = [sum(w[campo]) for campo in CAMPOS]
    ok = peor < 0.00006 and all(abs(s - 1) < 1e-9 for s in sumas)       # el arnés imprime con dos decimales de porcentaje
    fallas += not ok
    print(f"{'PASS' if ok else 'FAIL'}  pesos de los {nr} rivales en los 3 campos: diferencia maxima con lo que imprime el arnes "
          f"{100 * peor:.4f} puntos porcentuales (se imprime con 2 decimales), sumas {sumas[0]:.6f} {sumas[1]:.6f} {sumas[2]:.6f}")

    # 2. H3b exacto
    comparadas = fuera = 0
    peor_z = 0.0
    lineas = []
    for campo in CAMPOS:
        activos = [(k, w[campo][k]) for k in range(nr) if w[campo][k] > 0]
        for c in CANDIDATOS:
            total = var = 0.0
            for i in range(ns):
                x = W[c][i]
                m1 = m2 = 0.0
                for k, p in activos:
                    v = 2.0 if R[k][i] < x else 1.0 if R[k][i] == x else 0.0      # puntos que aporta un rival
                    m1 += p * v
                    m2 += p * v * v
                total += m1
                var += m2 - m1 * m1
            exacto = total / ns
            for G in GS:
                estimado = tsv[(c, f"sens_h3b_{campo}_{G}")]
                ee = math.sqrt(var / (G * CAMPOS_ARNES)) / ns                    # error del sorteo del arnés
                z = abs(estimado - exacto) / ee
                comparadas += 1
                fuera += z > 4
                peor_z = max(peor_z, z)
            lineas.append(f"      {campo:8s} {c:10s} exacto {exacto:.4f}   arnes G=5,10,15: "
                          + " ".join(f"{tsv[(c, f'sens_h3b_{campo}_{G}')]:.3f}" for G in GS))
    ok = fuera == 0
    fallas += not ok
    print(f"{'PASS' if ok else 'FAIL'}  H3b contra su valor esperado exacto: {comparadas} cifras, {fuera} fuera de 4 errores del sorteo, "
          f"peor caso {peor_z:.2f} errores")
    print("\n".join(lineas))

    # 3. H3a por un sorteo independiente (campo mixto y fuerte, G = 10)
    rng = random.Random(20261114)
    comparadas = fuera = 0
    peor_z = 0.0
    lineas = []
    G = 10
    for campo in ("mixto", "fuerte"):
        ks = [k for k in range(nr) if w[campo][k] > 0]
        ps = [w[campo][k] for k in ks]
        suma = {c: 0.0 for c in CANDIDATOS}
        var = {c: 0.0 for c in CANDIDATOS}
        for i in range(ns):
            acum = {c: [0.0, 0.0] for c in CANDIDATOS}
            for _ in range(CAMPOS_AQUI):
                x = [R[k][i] for k in rng.choices(ks, ps, k=G)]
                lo_r, hi_r = min(x), max(x)
                for c in CANDIDATOS:
                    v = W[c][i]
                    lo, hi = min(lo_r, v), max(hi_r, v)
                    pts = 2.0 * (v - lo) / (hi - lo) if hi > lo else 1.0
                    acum[c][0] += pts
                    acum[c][1] += pts * pts
            for c in CANDIDATOS:
                m = acum[c][0] / CAMPOS_AQUI
                suma[c] += m
                var[c] += max(0.0, acum[c][1] / CAMPOS_AQUI - m * m) * CAMPOS_AQUI / (CAMPOS_AQUI - 1)
        for c in CANDIDATOS:
            aqui = suma[c] / ns
            estimado = tsv[(c, f"sens_h3a_{campo}_{G}")]
            ee = math.sqrt(var[c] / CAMPOS_AQUI + var[c] / CAMPOS_ARNES) / ns     # los dos sorteos, combinados
            z = abs(estimado - aqui) / ee
            comparadas += 1
            fuera += z > 4
            peor_z = max(peor_z, z)
            lineas.append(f"      {campo:8s} {c:10s} sorteo propio {aqui:.4f}   arnes {estimado:.3f}   diferencia {estimado - aqui:+.4f} "
                          f"(error combinado {ee:.4f})")
    ok = fuera == 0
    fallas += not ok
    print(f"{'PASS' if ok else 'FAIL'}  H3a contra un sorteo independiente (G = 10, {CAMPOS_AQUI} campos por serie): {comparadas} cifras, "
          f"{fuera} fuera de 4 errores, peor caso {peor_z:.2f} errores")
    print("\n".join(lineas))

    print("PASS: los puntajes del torneo coinciden con el calculo independiente" if fallas == 0
          else f"FAIL: {fallas} pruebas con diferencias")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
