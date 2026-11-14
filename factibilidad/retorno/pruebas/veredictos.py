#!/usr/bin/env python3
"""veredictos.py: el criterio de corte para cada candidato contra la regla base.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 factibilidad/retorno/pruebas/veredictos.py --semilla 0
    python3 factibilidad/retorno/pruebas/veredictos.py --semilla 0 --candidatas "max_media;param:E=80,X=0"
    python3 factibilidad/retorno/pruebas/veredictos.py --semilla 0 --arnes ../mi_carpeta/build/mi_binario --candidatas mia

Corre `retorno veredicto` (ver nucleo/main.c) para cada candidata y resume:

  1. El veredicto con el campo mixto y G = 10 rivales, con la diferencia de
     puntos esperados y del percentil 5 y sus errores.
  2. Cómo cambia el veredicto con la composición del campo de rivales
     (ingenuo, mixto, fuerte) y con G (5, 10, 15).
  3. La salida completa de cada veredicto del punto 1.

Criterio (el que fijó Nicolás para este tramo): una pieza de algoritmo se
descarta si no mejora los puntos esperados del torneo sin empeorar el
percentil 5. Aquí "mejora" es más de dos errores estándar y "empeora" también.
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
ARNES = os.path.join(RETORNO, "build", "retorno")
PROCESOS = int(os.environ.get("PROCESOS", "6"))

POR_DEFECTO = ("max_media;guardia;guardia_tope;prudente;kalman;kalman_base;activo;base_guardia;base_tope;base_fuerte;"
               "prud_guardia;guardia_tope_r;base_tope_r")
CAMPOS = ("ingenuo", "mixto", "fuerte")
GS = (5, 10, 15)


def correr(args):
    arnes, candidata, referencia, semilla, campo, G = args
    entorno = dict(os.environ, HILOS=os.environ.get("HILOS_VEREDICTO", "2"))
    return subprocess.run([arnes, "veredicto", "--candidata", candidata, "--referencia", referencia, "--semilla", str(semilla),
                           "--campo", campo, "--G", str(G)], check=True, capture_output=True, text=True, env=entorno).stdout


def leer(texto):
    """Filas del criterio y veredictos de una salida de `retorno veredicto`."""
    filas, veredictos = {}, {}
    for linea in texto.splitlines():
        if linea.startswith("VEREDICTO"):
            clave, _, valor = linea.partition(":")
            veredictos[clave.replace("VEREDICTO", "").strip() or "global"] = valor.split()[0]
        elif linea.startswith("Veredicto literal"):
            veredictos["literal"] = linea.rsplit(":", 1)[1].strip()
        partes = linea.split("|")
        if len(partes) == 4 and partes[3].strip() in ("pasa", "no pasa"):
            largo, _, _, lectura = partes[0].split()
            media, p5 = partes[1].split(), partes[2].split()
            filas[(int(largo), lectura)] = dict(cand=float(media[0]), ref=float(media[1]), d=float(media[2]), ee=float(media[3]),
                                                p5=float(p5[0]), p5ref=float(p5[1]), dp5=float(p5[2]), ee5=float(p5[3]),
                                                fila=partes[3].strip())
    return filas, veredictos


def main(argv=None):
    ap = argparse.ArgumentParser(description="Criterio de corte para cada candidata contra una referencia")
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--candidatas", default=POR_DEFECTO, help="separadas por ';'")
    ap.add_argument("--referencia", default="base")
    ap.add_argument("--arnes", default=ARNES, help="binario compilado contra el núcleo (para estrategias propias)")
    ap.add_argument("--sin-sensibilidad", action="store_true", help="solo el campo mixto con G = 10")
    a = ap.parse_args(argv)
    candidatas = [c for c in a.candidatas.split(";") if c]
    combos = [("mixto", 10)] if a.sin_sensibilidad else [(c, g) for c in CAMPOS for g in GS]

    trabajos = [(a.arnes, c, a.referencia, a.semilla, campo, G) for c in candidatas for campo, G in combos]
    with ThreadPoolExecutor(PROCESOS) as pool:
        salidas = dict(zip([(t[1], t[4], t[5]) for t in trabajos], pool.map(correr, trabajos)))
    datos = {k: leer(v) for k, v in salidas.items()}

    nombre = {0: "exploracion", 1: "reservada del tramo anterior", 2: "reservada de este tramo"}.get(a.semilla, "otra")
    print(f"Criterio de corte: cada candidata contra {a.referencia}. Semilla {a.semilla} ({nombre}).")
    print("Una pieza de algoritmo se descarta si no mejora los puntos esperados del torneo sin empeorar el percentil 5.")
    print("Puntos de 0 a 2 en el conjunto evidencia (remuestreo y plausibles, mitad y mitad). A 2000 ticks todas las series;")
    print("a 20000 ticks las interiores (precio siempre entre 21 y 249). dif = candidata - referencia, con su error estandar.")
    print("p5: percentil 5 de los puntos de una competencia de tres rondas. PASA exige las cuatro filas (H3a y H3b, dos largos).")

    print("\n1. Campo mixto, G = 10 rivales")
    cab = f"{'dH3a':>7s} {'+-ee':>5s} {'dp5':>7s} {'+-ee':>5s}  {'dH3b':>7s} {'+-ee':>5s} {'dp5':>7s} {'+-ee':>5s} {'':8s}"
    print(f"{'candidata':16s} | {'rondas de 2000 ticks':^62s} | {'rondas de 20000 ticks (interiores)':^62s} | {'global':8s} | literal")
    print(f"{'':16s} | {cab} | {cab} |")
    for c in candidatas:
        filas, ver = datos[(c, "mixto", 10)]
        celdas = []
        for largo in (2000, 20000):
            x, y = filas[(largo, "H3a")], filas[(largo, "H3b")]
            celdas.append(f"{x['d']:+7.3f} {x['ee']:5.3f} {x['dp5']:+7.3f} {x['ee5']:5.3f}  {y['d']:+7.3f} {y['ee']:5.3f} "
                          f"{y['dp5']:+7.3f} {y['ee5']:5.3f} {ver[str(largo)]:8s}")
        print(f"{c:16s} | {celdas[0]} | {celdas[1]} | {ver['global']:8s} | {ver['literal']}")

    if not a.sin_sensibilidad:
        print("\n2. Sensibilidad del veredicto al campo de rivales y a G. Cada celda: veredicto a 2000 ticks / a 20000 ticks")
        print("(P pasa, n no pasa) y la diferencia de puntos esperados H3a a 2000 y a 20000 ticks.")
        print(f"{'candidata':16s} | " + " | ".join(f"{campo + ' G=' + str(G):^19s}" for campo, G in combos) + " | pasa en")
        for c in candidatas:
            celdas, cuenta = [], 0
            for campo, G in combos:
                filas, ver = datos[(c, campo, G)]
                cuenta += ver["global"] == "PASA"
                letras = "/".join("P" if ver[str(largo)] == "PASA" else "n" for largo in (2000, 20000))
                celdas.append(f"{letras} {filas[(2000, 'H3a')]['d']:+6.3f} {filas[(20000, 'H3a')]['d']:+6.3f}")
            print(f"{c:16s} | " + " | ".join(f"{x:19s}" for x in celdas) + f" | {cuenta} de {len(combos)}")
        print("\nLo mismo con H3b (lineal en el puesto): diferencia de puntos esperados a 2000 y a 20000 ticks.")
        print(f"{'candidata':16s} | " + " | ".join(f"{campo + ' G=' + str(G):^15s}" for campo, G in combos))
        for c in candidatas:
            celdas = []
            for campo, G in combos:
                filas, _ = datos[(c, campo, G)]
                celdas.append(f"{filas[(2000, 'H3b')]['d']:+6.3f} {filas[(20000, 'H3b')]['d']:+6.3f}")
            print(f"{c:16s} | " + " | ".join(f"{x:15s}" for x in celdas))

    print("\n3. Salida completa de cada veredicto (campo mixto, G = 10)")
    for c in candidatas:
        print("\n" + "-" * 100)
        print(salidas[(c, "mixto", 10)].rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
