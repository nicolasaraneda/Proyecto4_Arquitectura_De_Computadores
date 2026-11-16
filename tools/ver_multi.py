#!/usr/bin/env python3
"""ver_multi.py: revisa un archivo de varias imágenes hecho con icemulti.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El archivo que escribe icemulti parte con cinco vectores de 32 bytes: el de
encendido y los cuatro que elige SB_WARMBOOT con S1 S0. Cada vector lleva la
palabra de sincronía, el modo de arranque, la dirección de 24 bits de la
imagen y la orden de reiniciar la configuración desde ahí:

    7E AA 99 7E  92 00 mm  44 03 a2 a1 a0  82 00 00  01 08  00 ...

Este script decodifica los vectores, comprueba que en cada dirección haya un
bitstream (FF 00 ... 00 FF 7E AA 99 7E) y, si se le pasan los .bin originales,
que estén copiados sin ningún cambio. También informa el tamaño contra la
capacidad de la flash.

    python3 tools/ver_multi.py MULTI.bin [IMAGEN0.bin IMAGEN1.bin ...]
    python3 tools/ver_multi.py --flash 131072 MULTI.bin ...

Termina con error si algo no calza.
"""
import argparse
import hashlib
import sys

SYNC = bytes([0x7E, 0xAA, 0x99, 0x7E])
NOMBRES = ["encendido", "S1 S0 = 00", "S1 S0 = 01", "S1 S0 = 10", "S1 S0 = 11"]
FRECUENCIA = {0: "baja", 1: "media", 2: "alta"}


def vector(datos, i):
    v = datos[32 * i:32 * i + 32]
    if v[0:4] != SYNC or v[4] != 0x92 or v[7:9] != bytes([0x44, 0x03]):
        raise ValueError("el vector %d no tiene el formato de icemulti" % i)
    if v[12:17] != bytes([0x82, 0x00, 0x00, 0x01, 0x08]):
        raise ValueError("el vector %d no termina con la orden de reinicio" % i)
    return (v[9] << 16) | (v[10] << 8) | v[11], v[6]


def cabecera_bitstream(datos, dir_):
    """Devuelve (frecuencia, warmboot) leyendo el comienzo del bitstream en dir_."""
    p = datos.find(SYNC, dir_, dir_ + 512)
    if datos[dir_:dir_ + 2] != bytes([0xFF, 0x00]) or p < 0:
        raise ValueError("en 0x%06X no hay un bitstream" % dir_)
    frec = warm = None
    q = p + 4
    # Comandos de la cabecera: 51 xx (frecuencia del oscilador), 01 05 (reinicia
    # el CRC), 92 00 xx (bit 5: warm boot habilitado).
    for _ in range(4):
        if datos[q] == 0x51:
            frec = datos[q + 1]; q += 2
        elif datos[q:q + 2] == bytes([0x01, 0x05]):
            q += 2
        elif datos[q] == 0x92:
            warm = bool(datos[q + 2] & 0x20); q += 3
        else:
            break
    return frec, warm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("multi")
    ap.add_argument("imagenes", nargs="*")
    ap.add_argument("--flash", type=int, default=131072, help="capacidad de la flash en bytes")
    a = ap.parse_args()

    with open(a.multi, "rb") as f:
        datos = f.read()
    ok = True
    print("archivo: %s" % a.multi)
    print("tamaño: %d bytes de %d (%.1f %%), sobran %d" %
          (len(datos), a.flash, 100.0 * len(datos) / a.flash, a.flash - len(datos)))
    if len(datos) > a.flash:
        print("NO CABE en la flash")
        ok = False
    print("sha256: %s" % hashlib.sha256(datos).hexdigest())

    dirs = []
    for i in range(5):
        d, modo = vector(datos, i)
        dirs.append(d)
        frec, warm = cabecera_bitstream(datos, d)
        print("vector %d (%-10s) -> 0x%06X   modo 0x%02X, oscilador de configuración en frecuencia %s, warm boot %s" %
              (i, NOMBRES[i], d, modo, FRECUENCIA.get(frec, "?"), "habilitado" if warm else "deshabilitado"))

    unicas = sorted(set(dirs))
    print("imágenes distintas: %d, en %s" % (len(unicas), ", ".join("0x%06X" % d for d in unicas)))

    if a.imagenes:
        if len(a.imagenes) != len(unicas):
            print("FALLA: se pasaron %d imágenes y el archivo tiene %d" % (len(a.imagenes), len(unicas)))
            ok = False
        for n, (ruta, d) in enumerate(zip(a.imagenes, unicas)):
            with open(ruta, "rb") as f:
                img = f.read()
            igual = datos[d:d + len(img)] == img
            print("imagen %d: %s, %d bytes, sha256 %s, copia %s" %
                  (n, ruta, len(img), hashlib.sha256(img).hexdigest(), "idéntica" if igual else "DISTINTA"))
            ok = ok and igual
            # Las direcciones que usa SB_WARMBOOT: vector 1 + n
            if dirs[1 + n] != d:
                print("FALLA: S1 S0 = %s no apunta a la imagen %d" % (format(n, "02b"), n))
                ok = False
    print("RESULTADO: %s" % ("correcto" if ok else "con fallas"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
