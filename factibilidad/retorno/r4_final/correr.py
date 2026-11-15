#!/usr/bin/env python3
"""correr.py: corridas del estudio de cierre con los comandos del arnés.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 correr.py --semilla 0 --lista exploracion     todas las configuraciones (semilla de exploración)
    python3 correr.py --semilla 0 --lista final           veredictos oficiales y duelos de la lista final
    python3 correr.py --semilla 3 --lista final           la semilla reservada: UNA vez

Qué corre, siempre con `max_media` como referencia y G = 10:

  hipotesis   Una corrida por vista (2000 ticks; 20 000 interiores; 20 000 con
              parada) y por campo. La corrida con el campo mixto trae además
              el ingenuo y el fuerte en su tabla de sensibilidad. Las cifras
              quedan en build/tsv/ y la salida completa del campo mixto en
              mediciones/. La exploración usa los campos mixto, racional,
              reversores, fijos2 y fijos3; la lista final, los tres primeros.
              Con la semilla 0 las cifras de la lista final no se vuelven a
              calcular: son las de la exploración (el torneo no depende de
              qué otras candidatas van en la misma corrida) y se copian de
              sus tsv, filtrando. Los veredictos oficiales lo comprueban.
  veredicto   El criterio de corte oficial (`veredicto --parada`, campo mixto)
              de cada candidata de la lista final contra max_media.
  duelos      `hipotesis` otra vez, con otra referencia (las líneas "A contra
              B" de lista_final.txt), para saber si el fondo le gana a la mejor
              estrategia sola y cuánto aporta cada pieza. Campos mixto (con el
              fuerte), racional y reversores.

La semilla 2 no se usa. La semilla 3 solo se acepta con la lista final y deja
una marca en mediciones/reservada_usada.txt: si la marca existe, el programa
se niega a correr de nuevo salvo con --repetir, que sirve para reproducir las
cifras y no para elegir nada.
"""
import argparse
import datetime
import os
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
ARNES = os.path.join(AQUI, "build", "arnes")
M = os.path.join(AQUI, "mediciones")
TSV = os.path.join(AQUI, "build", "tsv")

REFERENCIA = "max_media"
VISTAS = (("n2000", 2000, []), ("n20000_int", 20000, ["--interior"]), ("n20000_par", 20000, ["--parada"]))
CAMPOS = ("mixto", "racional", "reversores", "fijos2", "fijos3")
CAMPOS_FINAL = ("mixto", "racional", "reversores")

# Todas las configuraciones del estudio. Se fijaron antes de correr (final.c).
EXPLORACION = ["base", "kalman", "ejec_a", "ejec_b", "espera", "aprendiz", "aprendiz_patron", "espera_e",
               "fondo_rec", "fondo_min", "fondo_ancla", "rec_e", "min_e",
               "completo", "completo_s", "completo_esp", "completo_ap", "completo_ancla", "completo_min"]


def leer_lista_final():
    """lista_final.txt: una candidata por línea; las líneas `A contra B` son duelos."""
    candidatas, duelos = [], []
    with open(os.path.join(AQUI, "lista_final.txt"), encoding="utf-8") as f:
        for linea in f:
            linea = linea.split("#")[0].strip()
            if not linea:
                continue
            if " contra " in linea:
                a, b = [x.strip() for x in linea.split(" contra ")]
                duelos.append((a, b))
            else:
                candidatas.append(linea)
    return candidatas, duelos


def entorno(semilla):
    e = dict(os.environ, HILOS=os.environ.get("HILOS", "5"))
    if semilla != 0:
        # Los resultados de la semilla reservada se guardan en la carpeta de este estudio.
        e["RETORNO_RESULTADOS"] = os.path.join(AQUI, "build", "resultados")
        e["RETORNO_GUARDAR"] = "1"
        os.makedirs(e["RETORNO_RESULTADOS"], exist_ok=True)
    return e


def correr(args, env):
    return subprocess.run([ARNES] + args, check=True, capture_output=True, text=True, env=env).stdout


def hipotesis(semilla, lista, etiqueta, env, ref=REFERENCIA, campos=CAMPOS):
    os.makedirs(TSV, exist_ok=True)
    candidatos = ";".join([ref] + lista)
    for vista, largo, extra in VISTAS:
        for campo in campos:
            t0 = time.time()
            tsv = os.path.join(TSV, f"{etiqueta}_s{semilla}_{vista}_{campo}.tsv")
            salida = correr(["hipotesis", "--largo", str(largo), "--semilla", str(semilla), "--candidatos", candidatos,
                             "--ref", ref, "--campo", campo, "--G", "10", "--tsv", tsv] + extra, env)
            if campo == "mixto":
                with open(os.path.join(M, f"hipotesis_{etiqueta}_s{semilla}_{vista}.txt"), "w", newline="\n") as f:
                    f.write(salida)
            print(f"hipotesis {etiqueta} s{semilla} {vista} {campo}: {time.time() - t0:.0f} s", flush=True)


def copiar_de_exploracion(lista):
    """Los tsv de la lista final con la semilla 0, sacados de los de la exploración."""
    quedan = set([REFERENCIA, "nada", "byh"] + lista)
    for vista, _, _ in VISTAS:
        for campo in CAMPOS_FINAL:
            origen = os.path.join(TSV, f"exploracion_s0_{vista}_{campo}.tsv")
            if not os.path.exists(origen):
                sys.exit(f"falta {origen}: correr antes --semilla 0 --lista exploracion")
            with open(origen) as f, open(os.path.join(TSV, f"final_s0_{vista}_{campo}.tsv"), "w", newline="\n") as g:
                g.write(next(f))
                vistos = set()
                for linea in f:
                    cand = linea.split("\t")[4]
                    if cand in quedan:
                        g.write(linea)
                        vistos.add(cand)
            faltan = quedan - vistos
            if faltan:
                sys.exit(f"la exploracion no trae a {sorted(faltan)}")
    print("lista final con la semilla 0: cifras copiadas de la exploracion", flush=True)


def veredictos(semilla, pares, nombre, env):
    with open(os.path.join(M, f"{nombre}_s{semilla}.txt"), "w", newline="\n") as f:
        for cand, ref in pares:
            t0 = time.time()
            salida = correr(["veredicto", "--candidata", cand, "--referencia", ref, "--semilla", str(semilla), "--parada"], env)
            f.write(f"===== {cand} contra {ref} =====\n{salida}\n")
            f.flush()
            final = [x for x in salida.splitlines() if x.startswith("VEREDICTO:")][0]
            print(f"{nombre} s{semilla} {cand} contra {ref}: {final} ({time.time() - t0:.0f} s)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semilla", type=int, required=True)
    ap.add_argument("--lista", choices=("exploracion", "final"), required=True)
    ap.add_argument("--repetir", action="store_true", help="volver a correr la semilla reservada para reproducir sus cifras")
    a = ap.parse_args()
    if a.semilla not in (0, 3):
        sys.exit("este estudio solo usa las semillas 0 (exploracion) y 3 (reservada)")
    if a.semilla == 3 and a.lista != "final":
        sys.exit("la semilla 3 es la reservada: solo se corre con la lista final")
    os.makedirs(M, exist_ok=True)
    env = entorno(a.semilla)
    t0 = time.time()
    if a.lista == "exploracion":
        hipotesis(a.semilla, EXPLORACION, "exploracion", env)
    else:
        candidatas, duelos = leer_lista_final()
        marca = os.path.join(M, "reservada_usada.txt")
        if a.semilla == 3:
            if os.path.exists(marca) and not a.repetir:
                sys.exit("la semilla 3 ya se uso (mediciones/reservada_usada.txt). Con --repetir se reproducen las cifras.")
            if not os.path.exists(marca):
                with open(marca, "w", newline="\n") as f:
                    f.write("La semilla 3 se uso una vez, con esta lista, fijada antes de mirarla (lista_final.txt):\n")
                    f.write("candidatas: " + ", ".join(candidatas) + "\n")
                    f.write("duelos: " + ", ".join(f"{x} contra {y}" for x, y in duelos) + "\n")
                    f.write("inicio de la corrida: " + datetime.datetime.now().strftime("%d/%m/%Y %H:%M") + "\n")
                    with open(os.path.join(AQUI, "lista_final.txt"), "rb") as g:
                        import hashlib
                        f.write("md5 de lista_final.txt: " + hashlib.md5(g.read()).hexdigest() + "\n")
        if a.semilla == 0:
            copiar_de_exploracion(candidatas)
        else:
            hipotesis(a.semilla, candidatas, "final", env, campos=CAMPOS_FINAL)
        veredictos(a.semilla, [(c, REFERENCIA) for c in candidatas], "veredictos", env)
        for ref in sorted(set(b for _, b in duelos)):
            hipotesis(a.semilla, [x for x, b in duelos if b == ref], f"duelo_{ref}", env, ref=ref,
                      campos=("mixto", "racional", "reversores"))
    print(f"total: {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
