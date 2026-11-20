#!/usr/bin/env python3
"""
fondo.py: referencia exacta de sw/fondo.s, el programa de R1 y R2 (Espino barrel).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Desde el 17/11 (decisión T133, opción F-a) el hilo 0 corre la regla de cotas
"espera" (ref/regla_cotas.py, docs/cotas.md), desde el 19/11 con banda 40
(decisión T140; del 17/11 al 19/11 con banda 60), y los hilos 1 a 3
quedan en un lazo de espera. El nombre del archivo se mantiene porque todas las
herramientas de R1 y R2 lo usan; hasta el 17/11 modelaba el fondo de cuatro
hilos que votaba (historial de git).

Por cada precio p que el programa ve (tick t = 1, 2, 3...), con los umbrales
de la tabla de parámetros:
    bajo   = p < LO_MAS_1          (101: p <= 100)
    alto   = no (p < HI)           (255: p >= 255)
    vio_lo |= bajo ; vio_hi |= alto ; los_dos = vio_lo & vio_hi
    comprar = bajo | (los_dos & p < BANDA_COMPRA)       (141: p <= 140)
    vender  = alto | (los_dos & no (p < BANDA_VENTA))   (215: p >= 215)
    si comprar o vender: q = vender 63 si vender, si no comprar 63
    DECISION = q (parte en 0x00, mantener)
Con los umbrales de la tabla por defecto decide byte por byte igual que
ref/trader.py (Oficial), la regla de sw/trade.s en R0 (lo comprueba
ref/test_fondo.py).

Telemetría (un store por tick, después de decidir): en los ticks pares los 7
segmentos muestran 63 si q es comprar 63 y 00 si no; en los impares los LED
son latido (bit 10 del número de tick), vio_lo, vio_hi y adentro.

Fallas: los hilos 1 a 3 no participan en la decisión, así que una falla en
ellos (`Falla`, se mantiene para las herramientas) no cambia ningún byte. Las
pruebas de degradación (tools/fondo/degradacion.sh) lo comprueban por el RTL.

Uso:
  python3 ref/fondo.py SERIE --periodo-ns 100000 -o ref.csv
  python3 ref/fondo.py SERIE --param BANDA_COMPRA=171 -o ref.csv
  python3 ref/fondo.py SERIE --traza traza.csv       # estado por tick
  python3 ref/fondo.py --tabla | --tabla-hex ARCHIVO
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import market
import trader

# Tabla de parámetros, en el orden en que está en la BRAM de la tabla
# (rtl/pochoco_tabla.v, 0x8002_0000; la palabra i está en el desplazamiento
# 4 i). Cada valor tiene que caber en 16 bits con signo: el programa la lee con
# lw y llega con extensión de signo.
PALABRAS_TABLA = 256
PARAMETROS = [
    ("LO_MAS_1", 101),       # bajo si p < 101: el mínimo de la serie es 100
    ("HI", 255),             # alto si p >= 255: el máximo es 255
    ("BANDA_COMPRA", 141),   # con los dos extremos vistos, compra si p < 141 (100 + 40)
    ("BANDA_VENTA", 215),    # y vende si p >= 215 (255 - 40)
]
POR_DEFECTO = dict(PARAMETROS)

M32 = 0xFFFFFFFF
DIGITOS_ADENTRO = 0x63
BIT_LATIDO = 1 << 10


def u32(x):
    """El registro que deja lw: 16 bits con extensión de signo, comparado sin signo (sltu)."""
    return x & M32


class Falla:
    """El hilo `gestor` (1, 2 o 3) falla entre los ticks `desde` y `hasta`. Desde el
    17/11 los hilos 1 a 3 no participan en la decisión: la falla no cambia nada."""

    def __init__(self, gestor, desde=1, hasta=None):
        self.gestor = gestor
        self.desde = desde
        self.hasta = hasta

    def afecta(self, gestor, tick):
        return gestor == self.gestor and tick >= self.desde and (self.hasta is None or tick <= self.hasta)

    @classmethod
    def leer(cls, texto):
        """ "3:100:" hilo 3 desde el tick 100; "2:50:60" hilo 2 entre el 50 y el 60; "1" siempre."""
        partes = texto.split(":")
        gestor = int(partes[0])
        desde = int(partes[1]) if len(partes) > 1 and partes[1] else 1
        hasta = int(partes[2]) if len(partes) > 2 and partes[2] else None
        if gestor not in (1, 2, 3):
            raise ValueError("el hilo de una falla es 1, 2 o 3")
        return cls(gestor, desde, hasta)


def _validar(parametros):
    q = dict(POR_DEFECTO)
    if parametros:
        for nombre in parametros:
            if nombre not in POR_DEFECTO:
                raise KeyError(f"parametro desconocido: {nombre}")
        q.update(parametros)
    return q


class Fondo:
    """El programa de R1 y R2. `decidir(p)` devuelve el byte que queda en DECISION."""

    CAMPOS = ("tick", "precio", "byte", "bajo", "alto", "vio_lo", "vio_hi", "leds", "seg")

    def __init__(self, parametros=None, fallas=()):
        self.q = _validar(parametros)
        self.fallas = list(fallas)       # no afectan la decisión (ver Falla)
        self.byte = market.MANTENER
        self.vio_lo = 0
        self.vio_hi = 0
        self.tick = 0
        self.leds = 0                    # LED al cerrar el tick
        self.seg = 0                     # 0 o 0x63: lo último escrito en los dígitos
        self.degradados = 0              # se mantiene por compatibilidad: siempre 0
        self.traza = None                # lista de tuplas si se pide

    def decidir(self, p):
        q = self.q
        self.tick += 1
        t = self.tick
        bajo = 1 if p < u32(q["LO_MAS_1"]) else 0
        alto = 0 if p < u32(q["HI"]) else 1
        banda_c = 1 if p < u32(q["BANDA_COMPRA"]) else 0
        banda_v = 0 if p < u32(q["BANDA_VENTA"]) else 1
        self.vio_lo |= bajo
        self.vio_hi |= alto
        dos = self.vio_lo & self.vio_hi
        comprar = bajo | (dos & banda_c)
        vender = alto | (dos & banda_v)
        if comprar or vender:
            self.byte = market.VENDER_63 if vender else market.COMPRAR_63
        adentro = 1 if self.byte == market.COMPRAR_63 else 0
        if t % 2 == 0:
            self.seg = DIGITOS_ADENTRO if adentro else 0
        else:
            self.leds = (1 if t & BIT_LATIDO else 0) | (self.vio_lo << 1) | (self.vio_hi << 2) | (adentro << 3)
        if self.traza is not None:
            self.traza.append((t, p, self.byte, bajo, alto, self.vio_lo, self.vio_hi, self.leds, self.seg))
        return self.byte


def correr(precios, perdidos=0, parametros=None, fallas=(), filas=None, traza=None):
    """Corre el programa sobre la serie. Devuelve (Mercado final, Fondo)."""
    fondo = Fondo(parametros, fallas)
    fondo.traza = traza
    m = market.simular(precios, trader.decisiones(precios, fondo, perdidos), filas=filas)
    return m, fondo


def palabras_tabla(parametros=None):
    """Los valores de la tabla de parámetros, en el orden de la memoria."""
    q = _validar(parametros)
    valores = [q[nombre] for nombre, _ in PARAMETROS]
    for (nombre, _), v in zip(PARAMETROS, valores):
        if not -32768 <= v <= 32767:
            raise ValueError(f"{nombre} = {v} no cabe en 16 bits con signo")
    return valores


def tabla_hex(parametros=None):
    """El contenido de la BRAM de la tabla: 256 líneas con un valor de 16 bits."""
    valores = palabras_tabla(parametros)
    valores += [0] * (PALABRAS_TABLA - len(valores))
    return "".join(f"{v & 0xFFFF:04x}\n" for v in valores)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Referencia de sw/fondo.s")
    ap.add_argument("serie", nargs="?", default="data/practica_meta.csv")
    ap.add_argument("--nticks", type=int, default=None, help="usar solo los primeros N ticks")
    ap.add_argument("--periodo-ns", type=int, default=None,
                    help="período del testbench: modela los precios que se pierden durante el reset")
    ap.add_argument("--perdidos", type=int, default=None, help="fijar a mano cuántos precios iniciales no se ven")
    ap.add_argument("--falla", action="append", default=[], metavar="H[:DESDE[:HASTA]]",
                    help="falla en el hilo H (1 a 3) entre esos ticks: no cambia la decisión")
    ap.add_argument("--param", action="append", default=[], metavar="NOMBRE=VALOR",
                    help="cambia un parámetro de la tabla (se puede repetir)")
    ap.add_argument("-o", "--salida", help="escribir el decisiones.csv de referencia")
    ap.add_argument("--traza", help="escribir el estado por tick")
    ap.add_argument("--tabla", action="store_true", help="mostrar la tabla de parámetros y salir")
    ap.add_argument("--tabla-hex", metavar="ARCHIVO",
                    help="escribir el contenido de la BRAM de la tabla (256 valores de 16 bits) y salir")
    a = ap.parse_args(argv)

    parametros = {}
    for texto in a.param:
        nombre, valor = texto.split("=")
        if nombre not in POR_DEFECTO:
            ap.error(f"parametro desconocido: {nombre}")
        parametros[nombre] = int(valor, 0)
    if a.tabla:
        for i, ((nombre, _), v) in enumerate(zip(PARAMETROS, palabras_tabla(parametros))):
            print(f"{i:3d}  0x{4 * i:03x}  {nombre:12s} {v:6d}  0x{v & 0xFFFF:04x}")
        return 0
    if a.tabla_hex:
        with open(a.tabla_hex, "w", newline="\n") as f:
            f.write(tabla_hex(parametros))
        return 0

    precios = market.leer_serie(a.serie, a.nticks)
    if a.perdidos is not None:
        perdidos = a.perdidos
    elif a.periodo_ns is not None:
        perdidos = trader.ticks_perdidos(a.periodo_ns)
    else:
        perdidos = 0
    fallas = [Falla.leer(t) for t in a.falla]

    filas = [] if a.salida else None
    traza = [] if a.traza else None
    m, fondo = correr(precios, perdidos, parametros, fallas, filas, traza)
    print(f"Serie {a.serie}: {len(precios)} ticks, precios iniciales que el programa no ve: {perdidos}")
    print(f"R1 y R2 (sw/fondo.s): patrimonio final {m.w}, {m.ordenes} ordenes, perdida maxima {m.max_dd}, "
          f"vio el minimo {fondo.vio_lo}, vio el maximo {fondo.vio_hi}")
    if a.salida:
        market.escribir_csv(a.salida, filas)
    if a.traza:
        with open(a.traza, "w", newline="\n") as f:
            f.write(",".join(Fondo.CAMPOS) + "\n")
            for fila in traza:
                f.write(",".join(str(x) for x in fila) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
