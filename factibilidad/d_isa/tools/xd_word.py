#!/usr/bin/env python3
"""xd_word.py: las instrucciones nuevas de custom-0 como directivas .word.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El ensamblador del repositorio (tools/pochoasm.py) no conoce la extensión y en
este estudio no se modifica. Este script hace de puente de dos formas:

1. Una instrucción suelta, para copiarla a mano en un programa:

       python3 tools/xd_word.py emad x3, x6, x3, 5
       .word 0x0a33418b            # emad x3, x6, x3, 5

2. Un archivo completo. Lee un programa que usa los mnemónicos nuevos y
   escribe otro en que cada una de esas líneas quedó como .word, con la
   instrucción original de comentario. El resto del archivo no se toca, así
   que el resultado se ensambla con tools/pochoasm.py sin cambios:

       python3 tools/xd_word.py --pre sw/trade_media.s -o build/sw/trade_media.s

Sintaxis de las instrucciones nuevas (registros x0 a x15 o sus nombres ABI):

    ema   rd, rs1, rs2, k      emad  rd, rs1, rs2, k      devk rd, rs1, rs2, k
    srak  rd, rs1, k
    padd8 rd, rs1, rs2         (y psub8, pcmpltu8, pcmplt8, pminu8, pmaxu8,
                                paddus8, psubus8)
    pbcast8 rd, rs1            pmovmsk8 rd, rs1
    mulstep rd, rs1, rs2       divstep rd, rs1, rs2       mulc rd, rs1, rs2

La codificación sale de ref/xd.py (función codificar), que es la misma que
usan los testbenches. `python3 tools/xd_word.py --tabla` imprime la tabla.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ref"))
import xd  # noqa: E402

ABI = {"zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4, "t0": 5, "t1": 6, "t2": 7,
       "s0": 8, "fp": 8, "s1": 9, "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14, "a5": 15}
MNEMONICOS = set(xd.CON_K) | set(xd.CARRILES) | set(xd.PRODUCTO)


def registro(texto):
    t = texto.strip().lower()
    if t in ABI:
        return ABI[t]
    m = re.fullmatch(r"x(\d+)", t)
    if not m or int(m.group(1)) > 15:
        raise ValueError(f"registro no válido en RV32E: {texto.strip()}")
    return int(m.group(1))


def numero(texto, constantes):
    t = texto.strip()
    if t in constantes:
        return constantes[t]
    return int(t, 0)


def palabra(mnemonico, operandos, constantes=None):
    """Codifica una instrucción nueva. `operandos` es la lista de textos."""
    constantes = constantes or {}
    m = mnemonico.lower()
    if m in ("ema", "emad", "devk"):
        if len(operandos) != 4:
            raise ValueError(f"{m} lleva rd, rs1, rs2, k")
        rd, rs1, rs2 = (registro(x) for x in operandos[:3])
        return xd.codificar(m, rd, rs1, rs2, k=numero(operandos[3], constantes))
    if m == "srak":
        if len(operandos) != 3:
            raise ValueError("srak lleva rd, rs1, k")
        return xd.codificar(m, registro(operandos[0]), registro(operandos[1]), 0,
                            k=numero(operandos[2], constantes))
    if m in xd.UN_OPERANDO:
        if len(operandos) != 2:
            raise ValueError(f"{m} lleva rd, rs1")
        return xd.codificar(m, registro(operandos[0]), registro(operandos[1]), 0)
    if m in MNEMONICOS:
        if len(operandos) != 3:
            raise ValueError(f"{m} lleva rd, rs1, rs2")
        return xd.codificar(m, *(registro(x) for x in operandos))
    raise ValueError(f"instrucción desconocida: {mnemonico}")


LINEA = re.compile(r"^(\s*(?:[A-Za-z_.][\w.]*:\s*)?)([A-Za-z][\w]*)\s+([^#]*?)\s*(#.*)?$")
EQU = re.compile(r"^\s*\.equ\s+([A-Za-z_]\w*)\s*,\s*([^#\s]+)")


def preprocesar(texto):
    """Devuelve (texto nuevo, número de instrucciones reemplazadas)."""
    salida, n, constantes = [], 0, {}
    for num, linea in enumerate(texto.splitlines(), 1):
        e = EQU.match(linea)
        if e:
            try:
                constantes[e.group(1)] = numero(e.group(2), constantes)
            except ValueError:
                pass
        m = LINEA.match(linea)
        if m and m.group(2).lower() in MNEMONICOS:
            prefijo, mnem, ops, comentario = m.groups()
            try:
                w = palabra(mnem, [o for o in ops.split(",")], constantes)
            except ValueError as err:
                raise SystemExit(f"línea {num}: {err}")
            original = f"{mnem} {', '.join(o.strip() for o in ops.split(','))}"
            resto = f"  {comentario[1:].strip()}" if comentario else ""
            salida.append(f"{prefijo}.word 0x{w:08x}        # {original}{resto}")
            n += 1
        else:
            salida.append(linea)
    return "\n".join(salida) + "\n", n


def main(argv=None):
    ap = argparse.ArgumentParser(description="Instrucciones de custom-0 como .word")
    ap.add_argument("--pre", metavar="ENTRADA.s", help="preprocesa un archivo completo")
    ap.add_argument("-o", metavar="SALIDA.s", help="salida de --pre (por defecto, la salida estándar)")
    ap.add_argument("--tabla", action="store_true", help="imprime la tabla de codificaciones")
    ap.add_argument("instruccion", nargs="*", help="una instrucción suelta: emad x3, x6, x3, 5")
    a = ap.parse_args(argv)
    if a.tabla:
        xd.tabla()
        return 0
    if a.pre:
        with open(a.pre, encoding="utf-8") as f:
            nuevo, n = preprocesar(f.read())
        if a.o:
            os.makedirs(os.path.dirname(os.path.abspath(a.o)), exist_ok=True)
            with open(a.o, "w", encoding="utf-8", newline="\n") as f:
                f.write(nuevo)
            print(f"{a.o}: {n} instrucciones nuevas escritas como .word")
        else:
            sys.stdout.write(nuevo)
        return 0
    if not a.instruccion:
        ap.error("falta la instrucción, --pre o --tabla")
    texto = " ".join(a.instruccion)
    mnem, _, ops = texto.partition(" ")
    try:
        w = palabra(mnem, ops.split(","))
    except ValueError as err:
        raise SystemExit(str(err))
    print(f".word 0x{w:08x}            # {mnem} {', '.join(o.strip() for o in ops.split(','))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
