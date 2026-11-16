#!/usr/bin/env python3
"""resumir.py: resumen por etapa de las tablas del barrido (mediciones/barrido_*.txt).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 resumir.py --mediciones mediciones > mediciones/barrido_resumen.txt

No evalúa nada: lee las tablas que dejó barrer.py y, para cada etapa y vista,
separa las variantes que aprenden de las fijas (reglas sin aprendizaje y
controles con el aprendizaje apagado) e informa:

  - cuántas son y cuántas tienen cada juicio;
  - el rango de la diferencia contra max_media en patrimonio (H1), H3a y H3b,
    en el conjunto evidencia;
  - la mejor variante por H3a y por H3b, con su error, y su signo en el
    remuestreo y en las plausibles por separado;
  - cuántas mejoran en más de dos errores H3a y H3b a la vez en evidencia, y
    de esas cuántas tienen además el mismo signo en remuestreo y plausibles.

Es de donde salen los rangos y los conteos que cita el README.
"""
import argparse
import glob
import os
import sys

import barrer


def leer(ruta):
    filas = []
    with open(ruta, encoding="utf-8") as f:
        lineas = f.read().splitlines()
    for linea in lineas[6:]:
        p = [x.split() for x in linea.split("|")]
        if len(p) != 8:
            continue
        v = {"spec": p[0][0], "ord": float(p[0][1]),
             "h1": float(p[1][0]), "h1_ee": float(p[1][1]), "h1_rem": float(p[1][2]), "h1_pla": float(p[1][4]),
             "h1_est": float(p[1][6]),
             "h3a": float(p[3][0]), "h3a_ee": float(p[3][1]), "h3b": float(p[3][2]), "h3b_ee": float(p[3][3]),
             "h3a_rem": float(p[5][0]), "h3a_pla": float(p[5][1]), "h3b_rem": float(p[5][2]), "h3b_pla": float(p[5][3]),
             "h3a_est": float(p[6][0]), "h3a_est_ee": float(p[6][1]), "h3b_est": float(p[6][2]), "h3b_est_ee": float(p[6][3]),
             "juicio": " ".join(p[7])}
        filas.append(v)
    return filas


def bloque(nombre, filas):
    if not filas:
        return
    n = {k: sum(1 for f in filas if f["juicio"] == k) for k in ("PASA", "p5 baja", "igual", "empeora")}
    print(f"  {nombre}: {len(filas)} variantes. PASA {n['PASA']}, mejora y baja el p5 {n['p5 baja']}, igual {n['igual']}, empeora {n['empeora']}")
    for clave, titulo in (("h1", "H1 "), ("h3a", "H3a"), ("h3b", "H3b")):
        lo = min(filas, key=lambda f: f[clave])
        hi = max(filas, key=lambda f: f[clave])
        fmt = "{:+.0f}" if clave == "h1" else "{:+.3f}"
        print(f"    {titulo} evidencia: de {fmt.format(lo[clave])} a {fmt.format(hi[clave])}   (peor: {lo['spec']}; mejor: {hi['spec']})")
    for clave in ("h3a", "h3b"):
        m = max(filas, key=lambda f: f[clave])
        print(f"    mejor por {clave.upper()}: {m['spec']}: {m[clave]:+.3f} +- {m[clave + '_ee']:.3f} "
              f"(remuestreo {m[clave + '_rem']:+.3f}, plausibles {m[clave + '_pla']:+.3f}, estres {m[clave + '_est']:+.3f})")
    ambas = [f for f in filas if f["h3a"] > 2 * f["h3a_ee"] and f["h3b"] > 2 * f["h3b_ee"]]
    firmes = [f for f in ambas if min(f["h3a_rem"], f["h3a_pla"], f["h3b_rem"], f["h3b_pla"]) > 0]
    print(f"    mejoran H3a y H3b en mas de dos errores en evidencia: {len(ambas)}; con el mismo signo en remuestreo y plausibles: {len(firmes)}")
    for f in ambas:
        print(f"      {f['spec']}: H3a {f['h3a']:+.3f} (rem {f['h3a_rem']:+.3f}, pla {f['h3a_pla']:+.3f}), "
              f"H3b {f['h3b']:+.3f} (rem {f['h3b_rem']:+.3f}, pla {f['h3b_pla']:+.3f}), juicio {f['juicio']}")
    protege = [f for f in filas if f["h3a_est"] > 2 * f["h3a_est_ee"] and f["h3b_est"] > 2 * f["h3b_est_ee"]]
    print(f"    mejoran H3a y H3b en mas de dos errores en estres: {len(protege)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mediciones", default="mediciones")
    a = ap.parse_args()
    print("Resumen del barrido por etapa (semilla 0). Diferencias pareadas contra max_media, campo mixto, G = 10.")
    print("Sale de leer mediciones/barrido_*.txt: no evalua nada.")
    total = {}
    for ruta in sorted(glob.glob(os.path.join(a.mediciones, "barrido_*_n*.txt"))):
        base = os.path.basename(ruta)[len("barrido_"):-len(".txt")]
        filas = [f for f in leer(ruta) if not f["spec"].startswith("param:")]
        if not filas:
            continue
        print(f"\n{base}")
        bloque("que aprenden", [f for f in filas if barrer.aprende(f["spec"])])
        bloque("fijas o con el aprendizaje apagado", [f for f in filas if not barrer.aprende(f["spec"])])
        vista = base.split("_n", 1)[1]
        for f in filas:
            total.setdefault(vista, {})[f["spec"]] = f
    print("\nTodas las etapas juntas, variantes distintas de este estudio:")
    for vista in sorted(total, key=lambda v: (len(v), v)):
        print(f"\nn{vista}")
        filas = list(total[vista].values())
        bloque("que aprenden", [f for f in filas if barrer.aprende(f["spec"])])
        bloque("fijas o con el aprendizaje apagado", [f for f in filas if not barrer.aprende(f["spec"])])
    return 0


if __name__ == "__main__":
    sys.exit(main())
