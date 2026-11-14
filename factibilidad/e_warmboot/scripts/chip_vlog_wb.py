#!/usr/bin/env python3
"""chip_vlog_wb.py: convierte un .asc con SB_WARMBOOT en un módulo Verilog simulable.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Llama a tools/chip_vlog.py (que a su vez llama a icebox_vlog y corrige el
encabezado del módulo) y arregla una cosa más: icebox_vlog escribe la
primitiva de warm boot sin nombre de instancia y con una coma de sobra,

    SB_WARMBOOT (
      .BOOT(n78),
      .S0(...),
      .S1(...),
    );

que no es Verilog válido. Aquí queda como "SB_WARMBOOT u_warmboot (...)", sin
la coma final. Así el testbench puede mirar dut.u_warmboot.BOOT, S1 y S0.

Se corre desde la raíz del repositorio:

    python3 factibilidad/e_warmboot/scripts/chip_vlog_wb.py ASC goboard.pcf -o SALIDA.v
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

    subprocess.run([sys.executable, "tools/chip_vlog.py", a.asc, a.pcf, "-o", a.salida], check=True)
    with open(a.salida, encoding="utf-8") as f:
        texto = f.read()
    patron = re.compile(r"SB_WARMBOOT \(\n(.*?),\n\);", re.S)
    nuevo, n = patron.subn(lambda m: "SB_WARMBOOT u_warmboot (\n" + m.group(1) + "\n);", texto)
    if n != 1:
        sys.exit("chip_vlog_wb.py: se esperaba una instancia de SB_WARMBOOT y hay %d" % n)
    with open(a.salida, "w", newline="\n", encoding="utf-8") as f:
        f.write(nuevo)


if __name__ == "__main__":
    main()
