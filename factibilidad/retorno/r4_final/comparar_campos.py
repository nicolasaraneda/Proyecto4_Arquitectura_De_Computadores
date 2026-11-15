#!/usr/bin/env python3
"""comparar_campos.py: los campos nuevos del arnés contra el evaluador independiente de la auditoría.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 comparar_campos.py --arnes build/arnes > mediciones/campos_contra_independiente.txt

Los campos racional, reversores, fijos2 y fijos3 existían solo en
../auditoria/indep.c, que calcula el valor esperado exacto de H3a y H3b. Este
estudio los agregó a ../nucleo/torneo.c, que sortea 6 campos por serie. Aquí
se corre el arnés con cada campo nuevo para `base` y `max_media` (semilla 0,
G = 10) y se comparan sus puntos con los del evaluador independiente, que ya
están en ../build/auditoria/estudio_s0.txt (los deja `make -C ../auditoria
estudio`).

Se comparan los puntos esperados de cada candidato, la diferencia pareada
entre los dos y el percentil 5 de la competencia de tres rondas. La
tolerancia de los puntos esperados es 4 errores del sorteo del arnés, que se
estiman como la raíz de la diferencia entre la varianza de la media que
informa el arnés (series y sorteo) y la del valor exacto (solo series), con
un piso de 0,002. La del percentil 5 son 3 errores combinados.
"""
import argparse
import math
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
INDEP = os.path.join(RETORNO, "build", "auditoria", "estudio_s0.txt")
CAMPOS = ("racional", "reversores", "fijos2", "fijos3")
CONJUNTOS = ("evidencia", "remuestreo", "plausibles", "estres")
VISTAS = ((2000, [], "n2000.todas", "2000 ticks"), (20000, ["--interior"], "n20000.int", "20 000 ticks, interiores"))


def leer_indep():
    datos = {}
    with open(INDEP) as f:
        for linea in f:
            clave, _, valor = linea.strip().rpartition("=")
            datos[clave] = float(valor)
    return datos


def leer_tsv(ruta):
    datos = {}
    with open(ruta) as f:
        next(f)
        for linea in f:
            _, _, _, conjunto, candidato, clave, valor = linea.rstrip("\n").split("\t")
            datos[(conjunto, candidato, clave)] = float(valor)
    return datos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arnes", default=os.path.join(AQUI, "build", "arnes"))
    a = ap.parse_args()
    if not os.path.exists(INDEP):
        sys.exit(f"falta {INDEP}: correr make -C ../auditoria estudio")
    ind = leer_indep()
    os.makedirs(os.path.join(AQUI, "build", "campos"), exist_ok=True)
    print("Campos nuevos del arnes (nucleo/torneo.c) contra el evaluador independiente (auditoria/indep.c).")
    print("Semilla 0, G = 10, candidatos base y max_media. arnes: sorteo de 6 campos por serie. indep: valor esperado exacto.")
    print("dif = arnes - indep. tol: 4 errores del sorteo (puntos) o 3 errores combinados (p5 de tres rondas).\n")
    print(f"{'vista':26s} {'campo':10s} {'conjunto':10s} {'cifra':22s} {'arnes':>8s} {'indep':>8s} {'dif':>8s} {'tol':>7s}")
    total = fuera = 0
    difs = []
    for largo, extra, pref, titulo in VISTAS:
        for campo in CAMPOS:
            tsv = os.path.join(AQUI, "build", "campos", f"campo_{campo}_n{largo}.tsv")
            subprocess.run([a.arnes, "hipotesis", "--largo", str(largo), "--semilla", "0", "--candidatos", "base;max_media",
                            "--ref", "base", "--campo", campo, "--G", "10", "--tsv", tsv] + extra,
                           check=True, stdout=subprocess.DEVNULL)
            d = leer_tsv(tsv)
            for conj in CONJUNTOS:
                filas = []
                for cand in ("base", "max_media"):
                    for lectura in ("h3a", "h3b"):
                        k = f"s0.{pref}.{conj}.{cand}.{campo}.G10."
                        if k + lectura not in ind:
                            continue
                        arn, ee_arn = d[(conj, cand, lectura + "_media")], d[(conj, cand, lectura + "_ee")]
                        exa, ee_exa = ind[k + lectura], ind[k + lectura + "_ee"]
                        tol = 4 * max(0.002, math.sqrt(abs(ee_arn ** 2 - ee_exa ** 2)))
                        filas.append((f"{cand} {lectura.upper()}", arn, exa, tol, 1))
                        p5a, p5e = d[(conj, cand, lectura + "_c_p5")], d[(conj, cand, lectura + "_c_p5_ee")]
                        q = "p5a3" if lectura == "h3a" else "p5b3"
                        tol5 = 3 * math.hypot(p5e, ind[k + q + "_ee"]) + 0.005
                        filas.append((f"{cand} {lectura.upper()} p5 3r", p5a, ind[k + q], tol5, 0))
                k = f"s0.{pref}.{conj}.max_media.{campo}.G10."
                if k + "dh3a" in ind:
                    for lectura in ("h3a", "h3b"):
                        arn, ee_arn = d[(conj, "max_media", "d_" + lectura)], d[(conj, "max_media", "d_" + lectura + "_ee")]
                        exa, ee_exa = ind[k + "d" + lectura], ind[k + "d" + lectura + "_ee"]
                        tol = 4 * max(0.002, math.sqrt(abs(ee_arn ** 2 - ee_exa ** 2)))
                        filas.append((f"max_media - base {lectura.upper()}", arn, exa, tol, 1))
                for nombre, arn, exa, tol, exacta in filas:
                    dif = arn - exa
                    mal = abs(dif) > tol
                    total += 1
                    fuera += mal
                    if exacta:
                        difs.append(abs(dif))
                    print(f"{titulo:26s} {campo:10s} {conj:10s} {nombre:22s} {arn:8.4f} {exa:8.4f} {dif:+8.4f} {tol:7.4f}"
                          f"{'  FUERA' if mal else ''}")
    difs.sort()
    print(f"\nCifras comparadas: {total}. Fuera de tolerancia: {fuera}.")
    print(f"Puntos esperados y diferencias pareadas ({len(difs)} cifras): diferencia absoluta mediana {difs[len(difs) // 2]:.4f}, "
          f"maxima {difs[-1]:.4f}.")
    print("CAMPOS: OK" if fuera == 0 else "CAMPOS: FALLA")
    return 1 if fuera else 0


if __name__ == "__main__":
    sys.exit(main())
