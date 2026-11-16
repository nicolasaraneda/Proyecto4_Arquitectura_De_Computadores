#!/usr/bin/env python3
"""chip_vlog.py: convierte un .asc en un módulo Verilog simulable (chip).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Llama a icebox_vlog y corrige el encabezado del módulo. icebox_vlog declara
los puertos en el encabezado (estilo ANSI) y después los vuelve a declarar
como wire o reg, cosa que iverilog -g2012 rechaza. Aquí el encabezado se pasa
al estilo antiguo (lista de nombres y declaraciones aparte), donde repetir la
declaración sí es válido. Si el diseño tiene la primitiva SB_WARMBOOT, además
le pone nombre de instancia (u_warmboot), porque icebox_vlog la escribe de una
forma que no es Verilog válido. No se cambia nada más.

    python3 tools/chip_vlog.py build/pochoco_soc.asc goboard.pcf -o build/bitstream/chip.v
"""
import argparse
import re
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asc")
    ap.add_argument("pcf")
    ap.add_argument("-o", "--salida", required=True)
    a = ap.parse_args()

    texto = subprocess.run(["icebox_vlog", "-n", "chip", "-p", a.pcf, "-d", "vq100", "-s", "-c", a.asc],
                           check=True, capture_output=True, text=True).stdout
    m = re.search(r"module chip \((.*?)\);", texto, re.S)
    if not m:
        sys.exit("chip_vlog.py: no se encontró el encabezado del módulo chip")
    nombres, declaraciones = [], []
    for puerto in m.group(1).split(","):
        partes = puerto.split()
        nombre = partes[-1]
        nombres.append(nombre + " " if nombre.startswith("\\") else nombre)
        declaraciones.append(" ".join(partes[:-1]) + " " + nombre + " ;")
    encabezado = "module chip (" + ", ".join(nombres) + ");\n" + "\n".join(declaraciones)
    texto = texto[:m.start()] + encabezado + texto[m.end():]
    # icebox_vlog escribe la primitiva de warm boot sin nombre de instancia y
    # con una coma de sobra. Queda como "SB_WARMBOOT u_warmboot (...)", para
    # que un testbench pueda mirar dut.u_warmboot.BOOT, S1 y S0.
    texto, n = re.subn(r"SB_WARMBOOT \(\n(.*?),\n\);",
                       lambda w: "SB_WARMBOOT u_warmboot (\n" + w.group(1) + "\n);", texto, flags=re.S)
    if n > 1:
        sys.exit("chip_vlog.py: hay %d instancias de SB_WARMBOOT" % n)
    with open(a.salida, "w", newline="\n") as f:
        f.write(texto)


if __name__ == "__main__":
    main()
