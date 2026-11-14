#!/usr/bin/env python3
"""parada.py: la vista de parada del arnés contra el evaluador independiente.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

La auditoría agregó al comando `veredicto` la opción --parada: a 20 000 ticks
evalúa todas las series de la evidencia, cada una solo hasta el primer tick en
que el precio sale de 21 a 249 (incluido ese tick, mínimo 200). No selecciona
por la trayectoria futura, que es el defecto del filtro de interiores, ni deja
que el rebote en los límites infle el resultado, que es el defecto de usar
todas las series.

Aquí se comprueba esa opción contra el evaluador independiente
(auditoria/indep.c, que calcula lo mismo por su cuenta y con el valor esperado
exacto) y se deja la tabla con las tres vistas para los candidatos principales.

    python3 auditoria/parada.py            (desde factibilidad/retorno; necesita make estudio)
"""
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
ARNES = os.path.join(RETORNO, "build", "retorno")
BUILD = os.path.join(RETORNO, "build", "auditoria")


def indep(semilla):
    d = {}
    with open(os.path.join(BUILD, f"estudio_s{semilla}.txt")) as f:
        for linea in f:
            if ".sesgo.parada." in linea:
                k, v = linea.rstrip("\n").rsplit("=", 1)
                d[k] = float(v)
    return d


def veredicto(cand, ref, semilla):
    """{(vista, lectura): (dif, ee, juicio)} de las filas de evidencia a 20 000 ticks."""
    r = subprocess.run([ARNES, "veredicto", "--candidata", cand, "--referencia", ref, "--semilla", str(semilla), "--largo", "20000",
                        "--parada"], capture_output=True, text=True, check=True, cwd=RETORNO)
    filas = {}
    for linea in r.stdout.splitlines():
        c = linea.split()
        if len(c) > 13 and c[0] == "20000" and c[2] == "evidencia":
            # dif, error, juicio, y del percentil 5: candidata, referencia, dif y error (el error solo en las filas H3)
            ee_p5 = float(c[14]) if c[3] != "H1" else 0.0
            filas[(c[1], c[3])] = (float(c[7]), float(c[8]), c[9], float(c[11]), float(c[12]), float(c[13]), ee_p5)
    return filas


def main():
    mal = 0
    print("Vista de parada del arnes (veredicto --parada) contra el evaluador independiente")
    print("Diferencia contra la regla base, evidencia de 20 000 ticks, campo mixto, G = 10.")
    print("El arnes sortea 6 campos por serie; el evaluador independiente calcula el valor esperado exacto.")
    print(f"{'candidata':10s} {'sem':>3s} {'lectura':>7s} {'arnes':>16s} {'independiente':>16s}  coincide")
    todas = {}
    for semilla in (0, 2):
        d = indep(semilla)
        for cand in ("max_media", "activo", "prudente"):
            f = veredicto(cand, "base", semilla)
            todas[(cand, "base", semilla)] = f
            for lect, clave, tol in (("H1", "dh1", 0.51), ("H3a", "dh3a", 0.005), ("H3b", "dh3b", 0.005)):
                k = f"s{semilla}.n20000.sesgo.parada.{cand}.mixto.G10.{clave}"
                suyo, mio = f[("parada", lect)], (d[k], d[k + "_ee"])
                ok = abs(suyo[0] - mio[0]) <= tol
                mal += not ok
                fmt = "%+.0f +- %.0f" if lect == "H1" else "%+.3f +- %.3f"
                print(f"{cand:10s} {semilla:3d} {lect:>7s} {fmt % suyo[:2]:>16s} {fmt % mio:>16s}  {'si' if ok else 'NO'}")
    print("PASS" if not mal else "FAIL")

    print("\nLas tres vistas a 20 000 ticks, con el arnes (veredicto --parada): diferencia de puntos esperados, H3a y H3b")
    print(f"{'candidata contra referencia':30s} {'sem':>3s} | {'interiores':>32s} | {'todas':>32s} | {'parada':>32s}")
    pares = [("max_media", "base"), ("kalman", "base"), ("activo", "base"), ("guardia", "base"), ("guardia_tope", "base"),
             ("guardia_tope_r", "base"), ("prudente", "base"), ("kalman", "max_media"), ("activo", "max_media"), ("guardia", "max_media")]
    for cand, ref in pares:
        for semilla in (0, 2):
            if (cand, ref, semilla) not in todas:
                todas[(cand, ref, semilla)] = veredicto(cand, ref, semilla)
            f = todas[(cand, ref, semilla)]
            celdas = []
            for vista in ("interiores", "todas", "parada"):
                a, b = f[(vista, "H3a")], f[(vista, "H3b")]
                celdas.append(f"{a[0]:+.3f} +- {a[1]:.3f}, {b[0]:+.3f} +- {b[1]:.3f}")
            print(f"{cand + ' contra ' + ref:30s} {semilla:3d} | {celdas[0]:>32s} | {celdas[1]:>32s} | {celdas[2]:>32s}")
    print("\nPercentil 5 de la competencia de tres rondas en la vista de parada: diferencia contra la referencia, H3a y H3b")
    print("(con el error del arnes, que es conservador)")
    for cand, ref in pares:
        celdas = []
        for semilla in (0, 2):
            f = todas.get((cand, ref, semilla)) or veredicto(cand, ref, semilla)
            a, b = f[("parada", "H3a")], f[("parada", "H3b")]
            celdas.append(f"semilla {semilla}: {a[5]:+.3f} +- {a[6]:.3f}, {b[5]:+.3f} +- {b[6]:.3f}")
        print(f"  {cand + ' contra ' + ref:30s} {'; '.join(celdas)}")

    print("\nPatrimonio (H1) de una ronda de 20 000 ticks en cada vista")
    print("(en cada vista: diferencia de la media +- error, y percentil 5 de la candidata y de la referencia)")
    print(f"{'candidata contra referencia':30s} {'sem':>3s} | {'interiores':>38s} | {'todas':>38s} | {'parada':>38s}")
    for cand, ref in pares[:7]:
        for semilla in (0, 2):
            f = todas.get((cand, ref, semilla)) or veredicto(cand, ref, semilla)
            celdas = []
            for vista in ("interiores", "todas", "parada"):
                h = f[(vista, "H1")]
                celdas.append(f"{h[0]:+.0f} +- {h[1]:.0f}, p5 {h[3]:.0f} y {h[4]:.0f}")
            print(f"{cand + ' contra ' + ref:30s} {semilla:3d} | {celdas[0]:>38s} | {celdas[1]:>38s} | {celdas[2]:>38s}")

    print("\nJuicio de la vista de parada (mejora, igual o empeora con dos errores), H3a y H3b:")
    for cand, ref in pares:
        js = []
        for semilla in (0, 2):
            f = todas.get((cand, ref, semilla)) or veredicto(cand, ref, semilla)
            js.append(f"semilla {semilla}: {f[('parada', 'H3a')][2]}, {f[('parada', 'H3b')][2]}")
        print(f"  {cand + ' contra ' + ref:30s} {'; '.join(js)}")
    return 1 if mal else 0


if __name__ == "__main__":
    sys.exit(main())
