#!/usr/bin/env python3
"""medir.py: ciclos por tick y perfil de cada variante con el gemelo digital.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Para cada variante corre build/gemelo con la serie de práctica a los tres
períodos (2 000 ticks a 10 ms, 20 000 a 1 ms y 20 000 a 0,1 ms, como
tools/medir_ticks.sh) y una vez más a 0,1 ms con --perfil, que cuenta las
instrucciones y los ciclos de cada dirección del programa en cada hilo.

El gemelo está validado contra el RTL en cada una de estas variantes: el base
y el segmentado con make cosim y make cosim-seg, el barrel, la extensión y el
fondo con make cosim-barrel (21 configuraciones). R2 es R1 más el vigilante,
que el gemelo no modela: el vigilante solo observa, y sus ciclos son los de
R1 (lo confirma tools/p7/rtl.sh con la medición del RTL).

Deja en docs/mediciones/p7/:
  gemelo.txt         resumen del gemelo por variante y ronda, con la huella de
                     los programas
  perfil/<v>.txt     perfil a 0,1 ms: hilo, dirección, palabra, ejecuciones y
                     ciclos

Uso: python3 tools/p7/medir.py   (o make p7-medir). Unos 10 segundos.
"""
import hashlib
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(RAIZ)
B = "build/p7"
M = "docs/mediciones/p7"
GEMELO = "build/gemelo"

# etiqueta, opciones del gemelo, programa
VARIANTES = [
    ("r0", [], f"{B}/sw/trade_max_media.hex"),
    ("seg", ["--pipeline"], f"{B}/sw/trade_max_media.hex"),
    ("barrel", ["--barrel"], f"{B}/sw/trade_h0.hex"),
    ("barrel_xd", ["--barrel", "--xd", "3"], f"{B}/sw/trade_xd_h0.hex"),
    ("r1", ["--barrel", "--xd", "3", "--tabla", "sw/fondo_tabla.hex"], f"{B}/sw/fondo.hex"),
]
RONDAS = [("r1", 10000000, 2000), ("r2", 1000000, 20000), ("r3", 100000, 20000)]


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw).stdout


def sha(ruta):
    return hashlib.sha256(open(ruta, "rb").read()).hexdigest()[:16]


def main():
    sh(["bash", "-c", "source tools/p7/comun.sh && programas"])
    sh(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", GEMELO, "ref/gemelo/gemelo.c"])
    os.makedirs(f"{M}/perfil", exist_ok=True)
    commit = sh(["git", "rev-parse", "--short", "HEAD"]).strip()
    rama = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()
    cc = sh(["cc", "--version"]).splitlines()[0]
    out = [
        "Ciclos por tick de las variantes de co-diseno, con el gemelo digital",
        "Generado por tools/p7/medir.py (make p7-medir). No editar a mano.",
        "",
        "Herramientas:",
        f"  {cc}",
        f"  gemelo ref/gemelo/gemelo.c (sha256 {sha('ref/gemelo/gemelo.c')}...)",
        f"Commit de partida: {commit} (rama {rama})",
        f"Serie tb/practica.csv (sha256 {sha('tb/practica.csv')}...), tabla sw/fondo_tabla.hex (sha256 {sha('sw/fondo_tabla.hex')}...)",
        "",
    ]
    for etq, opts, hexf in VARIANTES:
        out.append(f"== variante {etq}: build/gemelo {' '.join(opts)} --hex {hexf} (sha256 {sha(hexf)}...)")
        for ronda, periodo, nticks in RONDAS:
            r = sh([GEMELO, *opts, "--hex", hexf, "--periodo-ns", str(periodo), "--nticks", str(nticks)])
            for linea in r.splitlines():
                if linea.startswith(("Patrimonio", "Peor caso", "Testbenchs", "Gemelo:")):
                    out.append(f"{etq} {ronda} | {linea}")
        perfil = f"{M}/perfil/{etq}.txt"
        sh([GEMELO, *opts, "--hex", hexf, "--periodo-ns", "100000", "--nticks", "20000", "--perfil", perfil, "--callado"])
        out.append(f"{etq} perfil | {perfil}, 20000 ticks a 0,1 ms sin atajo")
        out.append("")
    open(f"{M}/gemelo.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    if any("FAIL" in x or "aprobados: 4/4" not in x for x in out if "Testbenchs" in x):
        sys.exit("FAIL: alguna variante no obtuvo 4/4 en el gemelo")


if __name__ == "__main__":
    main()
