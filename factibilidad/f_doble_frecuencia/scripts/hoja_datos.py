#!/usr/bin/env python3
"""hoja_datos.py: saca de la hoja de datos de la iCE40 los tres datos que usa la pieza F.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

La hoja de datos (DS1040, "iCE40 LP/HX Family Data Sheet") no está en el
repositorio. Se baja a mano y se pasa como argumento. El script descomprime
los flujos de texto del PDF con la biblioteca estándar (no hay lector de PDF
instalado) y muestra:
  - la versión del documento;
  - las filas de la tabla de relojes de los iCE40HX: frecuencia máxima,
    ancho mínimo del pulso (tW_GBUF) y skew (tSKEW_GBUF) de la red global;
  - el párrafo "Derating Logic Timing";
  - todas las líneas del documento que hablan de un ancho de pulso, para
    ver si hay algún otro mínimo que afecte al reloj (por ejemplo el de las
    memorias).

Uso: scripts/hoja_datos.py HOJA.pdf
"""
import hashlib
import os
import re
import sys
import zlib


def flujos(datos):
    """Texto de cada flujo comprimido del PDF, una línea por operador Tj o TJ."""
    for m in re.finditer(rb"stream\r?\n", datos):
        fin = datos.find(b"endstream", m.end())
        try:
            t = zlib.decompress(datos[m.end():fin])
        except zlib.error:
            continue
        lineas = []
        for tj, simple in re.findall(rb"\[(.*?)\]\s*TJ|\(((?:[^()\\]|\\.)*)\)\s*Tj", t, re.S):
            if tj:
                lineas.append(b"".join(re.findall(rb"\(((?:[^()\\]|\\.)*)\)", tj)))
            else:
                lineas.append(simple)
        if lineas:
            yield [l.decode("latin-1") for l in lineas]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    datos = open(sys.argv[1], "rb").read()
    version = None
    reloj = None
    derating = None
    pulsos = []
    for lineas in flujos(datos):
        for i, l in enumerate(lineas):
            if version is None and re.search(r"DS1040 Version", l):
                version = l.strip()
            if reloj is None and "Clock networkAll iCE40HX devices" in l:
                j = i
                while j < len(lineas) and "Pin-LUT-Pin" not in lineas[j]:
                    j += 1
                # El carácter 0x97 marca una columna vacía (mínimo o máximo sin dato)
                reloj = [x.replace("\x97", " [sin dato] ").strip() for x in lineas[i - 2:j]]
            if derating is None and l.strip() == "Derating Logic Timing":
                derating = [x.strip() for x in lineas[i:i + 4]]
            if re.search(r"pulse\s*width", l, re.I):
                limpio = l.replace("\x97", " [sin dato] ").strip()
                if limpio not in pulsos:
                    pulsos.append(limpio)
    print("Hoja de datos: %s" % (version or "versión no encontrada"))
    print()
    print("Tabla de relojes de los iCE40HX (External Switching Characteristics, HX Devices):")
    # El PDF parte los símbolos con subíndice en dos líneas y pega las
    # columnas (parámetro, dispositivo, mínimo, máximo y unidad): se muestra
    # cada fila tal como viene, una por parámetro.
    fila = ""
    for l in reloj or ["no encontrada"]:
        if l in ("f", "t") and fila:
            print("  " + fila)
            fila = ""
        fila = (fila + " " + l).strip()
    print("  " + fila)
    print()
    print("Párrafo sobre los tiempos de las herramientas:")
    print("  " + " ".join(derating or ["no encontrado"]))
    print()
    print("Todas las líneas del documento que mencionan un ancho de pulso (pulse width):")
    for l in pulsos or ["ninguna"]:
        print("  " + l)
    print()
    print("Columnas de la tabla de relojes: parámetro, dispositivo, mínimo, máximo y unidad.")
    print("tW_GBUF es un mínimo y tSKEW_GBUF un máximo.")
    print()
    print("Archivo leído: %s, %d bytes, SHA-256 %s" %
          (os.path.basename(sys.argv[1]), len(datos), hashlib.sha256(datos).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
