#!/usr/bin/env python3
"""pochoasm: ensamblador del Espino Core (RV32E) para el Pochoco SoC.

Traduce un archivo .s a un .hex con el formato que lee $readmemh:

    python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex

Es el ensamblador que el grupo escribio para el Proyecto 2 y amplio en el
Proyecto 3 (antes assembler/asm.py), con el nombre y la interfaz que espera el
testbench del Proyecto 4. Opcionalmente escribe el programa como include de
Verilog (--vh) o como ROM combinacional (--rom). No invoca ninguna herramienta externa. Ver docs/ensamblador.md.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "asm"))

from core import IDENT_RE, assemble_file, format_verilog_image, format_verilog_rom, parse_number  # noqa: E402
from errors import AssemblerError  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Assembler propio para el Espino Core (RV32E) del Pochoco SoC."
    )
    parser.add_argument("input", help="archivo .s de entrada")
    parser.add_argument(
        "-o",
        "--output",
        help="archivo .hex de salida (por defecto: la entrada con extensión .hex)",
    )
    parser.add_argument(
        "--allow-shifts",
        action="store_true",
        help="permite sll/srl/sra/slli/srli/srai (la ALU los ejecuta como ADD en este core; usar bajo tu propio riesgo)",
    )
    parser.add_argument(
        "--vh",
        metavar="SALIDA.vh",
        help="escribe además la imagen del programa como include de Verilog (PROG_WORDS y prog_word)",
    )
    parser.add_argument(
        "--rom",
        metavar="SALIDA.v",
        help="escribe además el módulo pochoco_rom: una ROM combinacional con el programa",
    )
    parser.add_argument(
        "-D",
        "--define",
        action="append",
        default=[],
        metavar="NOMBRE=VALOR",
        help="fija una constante desde la línea de comandos y pisa el .equ del archivo con ese nombre (repetible)",
    )
    args = parser.parse_args(argv)

    defines = {}
    for item in args.define:
        name, sep, val = item.partition("=")
        if not sep or not IDENT_RE.match(name):
            print(f"error: -D '{item}': se esperaba NOMBRE=VALOR", file=sys.stderr)
            return 1
        try:
            defines[name] = parse_number(val)
        except ValueError:
            print(f"error: -D '{item}': valor no numérico '{val}'", file=sys.stderr)
            return 1

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".hex")

    try:
        words = assemble_file(input_path, output_path, allow_shifts=args.allow_shifts, defines=defines)
    except AssemblerError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"{input_path} -> {output_path} ({len(words)} palabras, {len(words) * 4} bytes)")

    for ruta, formato, nombre in ((args.vh, format_verilog_image, "imagen Verilog"),
                                  (args.rom, format_verilog_rom, "ROM combinacional")):
        if not ruta:
            continue
        destino = Path(ruta)
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            with open(destino, "w", encoding="utf-8", newline="\n") as f:
                f.write(formato(words, input_path.as_posix(), allow_shifts=args.allow_shifts))
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"{input_path} -> {destino} ({nombre}, {len(words)} palabras)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
