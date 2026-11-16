#!/usr/bin/env python3
"""barrido.py: el criterio de corte para una lista de variantes, en una tabla compacta.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 herramientas/barrido.py --arnes build/arnes --lista herramientas/variantes.txt
    python3 herramientas/barrido.py --arnes build/arnes --variantes "ejec:m=8;ejec:K=1" --completo

Corre `veredicto --candidata V --referencia max_media --semilla 0 --parada`
para cada variante (hasta 5 a la vez, un hilo cada una) y resume, por
variante: la diferencia pareada de patrimonio y de puntos contra `max_media`
en los dos largos, el percentil 5 de la competencia de tres rondas, el
veredicto del criterio y el veredicto literal. Con --completo agrega la
salida entera de cada veredicto.

El archivo de la lista tiene una variante por línea. Las líneas que empiezan
con "#" son títulos de familia y se copian a la salida. Solo semilla 0.
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

PROCESOS = min(5, int(os.environ.get("PROCESOS", "5")))


def correr(args):
    arnes, variante, referencia, extra = args
    entorno = dict(os.environ, HILOS="1")
    return subprocess.run([arnes, "veredicto", "--candidata", variante, "--referencia", referencia, "--semilla", "0", "--parada",
                           *extra], check=True, capture_output=True, text=True, env=entorno).stdout


def leer(texto):
    filas, ver = {}, {}
    for linea in texto.splitlines():
        if linea.startswith("VEREDICTO"):
            clave, _, valor = linea.partition(":")
            ver[clave.replace("VEREDICTO", "").strip() or "global"] = valor.split()[0]
        elif linea.startswith("Veredicto literal"):
            ver["literal"] = linea.rsplit(":", 1)[1].strip()
        partes = linea.split("|")
        if len(partes) == 4 and partes[0].split() and partes[0].split()[0] in ("2000", "20000"):
            largo, series, conjunto, lectura = partes[0].split()
            m, q = partes[1].split(), partes[2].split()
            if lectura == "H1":
                filas[(largo, series, conjunto, lectura)] = dict(cand=float(m[0]), ref=float(m[1]), d=float(m[2]), ee=float(m[3]),
                                                                 p5=float(q[0]), p5ref=float(q[1]), dp5=float(q[2]), ee5=0.0)
            else:
                filas[(largo, series, conjunto, lectura)] = dict(cand=float(m[0]), ref=float(m[1]), d=float(m[2]), ee=float(m[3]),
                                                                 p5=float(q[0]), p5ref=float(q[1]), dp5=float(q[2]), ee5=float(q[3]))
    return filas, ver


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arnes", required=True)
    ap.add_argument("--lista")
    ap.add_argument("--variantes", help="separadas por ';'")
    ap.add_argument("--referencia", default="max_media")
    ap.add_argument("--campo", default="mixto")
    ap.add_argument("--G", default="10")
    ap.add_argument("--caja")
    ap.add_argument("--comision")
    ap.add_argument("--completo", action="store_true")
    a = ap.parse_args()
    extra = ["--campo", a.campo, "--G", a.G]
    if a.caja:
        extra += ["--caja", a.caja]
    if a.comision:
        extra += ["--comision", a.comision]

    entradas = []                      # ("titulo", texto) o ("variante", spec)
    if a.lista:
        for linea in open(a.lista, encoding="utf-8"):
            linea = linea.strip()
            if not linea:
                continue
            entradas.append(("titulo", linea[1:].strip()) if linea.startswith("#") else ("variante", linea))
    if a.variantes:
        entradas += [("variante", v) for v in a.variantes.split(";") if v]
    variantes = [v for t, v in entradas if t == "variante"]
    with ThreadPoolExecutor(PROCESOS) as pool:
        salidas = dict(zip(variantes, pool.map(correr, [(a.arnes, v, a.referencia, extra) for v in variantes])))

    print(f"Criterio de corte de cada variante contra {a.referencia}. Semilla 0, campo {a.campo}, G = {a.G}"
          + (f", caja {a.caja}" if a.caja else "") + (f", comision {a.comision}" if a.comision else "") + ".")
    print("dW: diferencia pareada de patrimonio (H1). dH3a, dH3b: diferencia de puntos esperados (0 a 2). p5: diferencia del")
    print("percentil 5 de la competencia de tres rondas. Cada cifra con su error estandar entre parentesis (en milesimas para los puntos).")
    print("Conjunto evidencia salvo donde dice rem (remuestreo), pla (plausibles) o est (estres). 20000 ticks: int = interiores, par = parada.")
    print("V: veredicto a 2000 / a 20000 ticks (P pasa, n no pasa). lit: veredicto literal por signo.\n")
    cab = (f"{'variante':30s} | {'dW 2000':>12s} {'rem':>6s} {'pla':>6s} {'est':>7s} | {'dH3a 2000':>11s} {'p5':>11s} {'dH3b 2000':>11s} {'p5':>11s} |"
           f" {'dW int':>11s} {'dH3a int':>11s} {'p5':>11s} {'dH3b int':>11s} {'p5':>11s} | {'dW par':>10s} {'dH3a par':>11s} {'dH3b par':>11s} |"
           f" {'V':3s} {'lit':7s}")
    print(cab)

    def pt(f, clave):
        x = f.get(clave)
        return f"{x['d']:+.3f}({1000 * x['ee']:3.0f})" if x else "     -     "

    def p5(f, clave):
        x = f.get(clave)
        return f"{x['dp5']:+.3f}({1000 * x['ee5']:3.0f})" if x else "     -     "

    def w(f, clave, ancho=12):
        x = f.get(clave)
        return f"{x['d']:+.0f}({x['ee']:.0f})".rjust(ancho) if x else "-".rjust(ancho)

    for tipo, v in entradas:
        if tipo == "titulo":
            print(f"--- {v}")
            continue
        f, ver = leer(salidas[v])
        e2, ei, ep = ("2000", "todas", "evidencia"), ("20000", "interiores", "evidencia"), ("20000", "parada", "evidencia")
        letras = "/".join("P" if ver.get(k) == "PASA" else "n" for k in ("2000", "20000"))
        print(f"{v:30s} | {w(f, e2 + ('H1',))} {w(f, ('2000', 'todas', 'remuestreo', 'H1'), 6)} {w(f, ('2000', 'todas', 'plausibles', 'H1'), 6)} "
              f"{w(f, ('2000', 'todas', 'estres', 'H1'), 7)} | {pt(f, e2 + ('H3a',))} {p5(f, e2 + ('H3a',))} {pt(f, e2 + ('H3b',))} {p5(f, e2 + ('H3b',))} |"
              f" {w(f, ei + ('H1',), 11)} {pt(f, ei + ('H3a',))} {p5(f, ei + ('H3a',))} {pt(f, ei + ('H3b',))} {p5(f, ei + ('H3b',))} |"
              f" {w(f, ep + ('H1',), 10)} {pt(f, ep + ('H3a',))} {pt(f, ep + ('H3b',))} | {letras:3s} {ver.get('literal', '')}")

    if a.completo:
        for v in variantes:
            print(f"\n=== {v} ===")
            print(salidas[v])
    return 0


if __name__ == "__main__":
    sys.exit(main())
