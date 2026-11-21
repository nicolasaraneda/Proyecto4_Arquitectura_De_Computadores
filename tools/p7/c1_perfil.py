#!/usr/bin/env python3
"""c1_perfil.py: IC, ciclos, CPI y perfil por hilo de R3 (sw/c1.s) con el gemelo digital.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Mide la serie Meta a 0,1 ms (20 000 ticks) con el gemelo (--barrel --xd 3 y la tabla de
512 palabras) y el perfil por dirección. Agrupa cada dirección por la rutina a la que
pertenece (la etiqueta anterior de sw/c1.s) y por hilo. Las mediciones por tick del RTL
(docs/mediciones/c1/ticks.txt) son las que van en la sección 3.2; esto las acompaña con el
perfil. Amdahl y roofline de R3 quedan para la pasada de R3, después del 26/11 (T155).

Deja docs/mediciones/c1/perfil_hilos.txt y c1/perfil/gemelo.txt.
Uso: python3 tools/p7/c1_perfil.py   (o make p7-c1-perfil). Segundos.
"""
import hashlib
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tools", "p7"))
import fuentes  # noqa: E402

B, M = "build/p7/c1", "docs/mediciones/c1"


def sh(cmd):
    return subprocess.run(cmd, check=True, text=True, capture_output=True).stdout


def sha(ruta):
    return hashlib.sha256(open(ruta, "rb").read()).hexdigest()[:16]


def grupo(etiqueta):
    if etiqueta.startswith(("pr_", "producto")):
        return "producto"
    if etiqueta.startswith(("ej_", "ejecutar")):
        return "ejecutar"
    return etiqueta


def main():
    os.makedirs(B, exist_ok=True)
    sh(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", "build/gemelo", "ref/gemelo/gemelo.c"])
    sh([sys.executable, "tools/pochoasm.py", "sw/c1.s", "-o", f"{B}/c1.hex"])
    perfil = f"{B}/perfil.txt"
    r = sh(["build/gemelo", "--barrel", "--xd", "3", "--tabla", "sw/c1_tabla.hex", "--hex", f"{B}/c1.hex",
            "--serie", "data/practica_meta.csv", "--periodo-ns", "100000", "--nticks", "20000", "--perfil", perfil])
    resumen = [l for l in r.splitlines() if l.startswith(("Patrimonio", "Peor caso", "Testbenchs", "Gemelo: 1999"))]
    m, sim = fuentes.mapa("sw/c1.s")
    etiquetas = sorted((d, n) for n, d in sim.items() if isinstance(d, int) and d in m and not n.isupper())
    def etiqueta_de(d):
        previa = [n for a, n in etiquetas if a <= d]
        return previa[-1] if previa else "arranque"
    esc = [d for d, (_, nom, ops, _) in m.items() if nom == "sw" and len(ops) > 1 and "off_decision" in ops[1]]
    filas = []
    for linea in open(perfil, encoding="utf-8"):
        if not linea.startswith("#"):
            h, d, w, n, c = linea.split()
            filas.append((int(h), int(d, 16), int(n), int(c)))
    nref = sum(n for h, d, n, c in filas if h == 0 and d in esc)
    por_hilo, por_grupo = {}, {}
    for h, d, n, c in filas:
        x = por_hilo.setdefault(h, [0, 0])
        x[0] += n
        x[1] += c
        g = por_grupo.setdefault((h, grupo(etiqueta_de(d))), [0, 0])
        g[0] += n
        g[1] += c
    out = ["Perfil por hilo de R3 (sw/c1.s) con el gemelo digital",
           "Generado por tools/p7/c1_perfil.py (make p7-c1-perfil). No editar a mano.", "",
           f"Programa sw/c1.s (sha256 {sha('sw/c1.s')}...), tabla sw/c1_tabla.hex (sha256 {sha('sw/c1_tabla.hex')}...)",
           f"Serie data/practica_meta.csv, 20000 ticks a 0,1 ms; {nref} ticks con escritura de DECISION.", ""]
    out += resumen
    out += ["", "Por hilo, por tick (incluye las vueltas de los lazos de espera): el barrel ejecuta una instruccion de cada",
            "hilo cada 4 ciclos, asi que CPI 4 por hilo y 1 agregado por construccion.",
            f"{'hilo':>5}{'IC por tick':>13}{'ciclos por tick':>17}{'CPI':>7}"]
    for h in sorted(por_hilo):
        n, c = por_hilo[h]
        out.append(f"{h:>5}{n / nref:>13.2f}{c / nref:>17.2f}{c / n:>7.3f}")
    out += ["", "Por rutina (la etiqueta anterior de sw/c1.s); las que terminan en _espera son los lazos de espera.",
            f"{'hilo':>5} {'rutina':<14}{'IC por tick':>12}{'ciclos por tick':>16}"]
    for (h, g), (n, c) in sorted(por_grupo.items(), key=lambda kv: (kv[0][0], -kv[1][1])):
        if n / nref >= 0.5:
            out.append(f"{h:>5} {g:<14}{n / nref:>12.2f}{c / nref:>16.2f}")
    os.makedirs(f"{M}/perfil", exist_ok=True)
    open(f"{M}/perfil_hilos.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
    os.replace(perfil, f"{M}/perfil/gemelo.txt")
    print("\n".join(out))


if __name__ == "__main__":
    main()
