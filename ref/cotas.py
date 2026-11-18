#!/usr/bin/env python3
"""cotas.py: familia de reglas "cotas", para series normalizadas entre 100 y 255.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Desde el 17/11 la serie de práctica es data/practica_meta.csv: precios reales de Meta,
uno por minuto de mercado, normalizados de modo que el mínimo es exactamente 100 y el
máximo exactamente 255. Si cada ronda de la competencia se normaliza igual, el precio
nunca sale de [100, 255] y toca los dos extremos. La regla lo aprovecha:

    al ver p <= LO + a      quiere estar adentro: comprar 63 (repetido, la maestra
                            compra lo que alcance)
    al ver p >= HI - b      quiere estar afuera: vender 63 (repetido)
    entre medio             mantiene la posición

Variantes (parámetros, todos enteros):
    inicio = "espera"       parte en caja (escribe mantener hasta el primer extremo)
             "compra"       parte comprando (comprar 63 desde el primer precio)
             "parte"        compra k acciones con el primer precio y después mantiene
             "umbral"       según el primer precio p0: "compra" si p0 <= u, "espera" si no
    a, b                    márgenes: compra hasta LO + a, vende desde HI - b. La orden se
                            ejecuta al precio siguiente, así que el margen no cambia el
                            precio de ejecución sino cuándo se decide.
    banda = w               después de haber visto los dos extremos: compra si
                            p <= LO + w y vende si p >= HI - w (0: sin banda, mantiene)

Comprobaciones con la serie Meta completa (las cifras de Nicolás, ref/test_cotas.py):
    espera  15 894 con 2 órdenes; compra  23 906 con 5; compra con banda 40  32 149.

Uso:
    python3 ref/cotas.py data/practica_meta.csv
    python3 ref/cotas.py data/practica_meta.csv --inicio compra --banda 40
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import market  # noqa: E402
import trader  # noqa: E402

LO, HI = 100, 255


class Cotas:
    """Regla de cotas. decidir(p) devuelve el byte de DECISION, como las demás estrategias."""

    def __init__(self, inicio="espera", a=0, b=0, banda=0, k=0, u=178, lo=LO, hi=HI):
        if inicio not in ("espera", "compra", "parte", "umbral"):
            raise ValueError("inicio desconocido: " + str(inicio))
        if not (0 <= k <= 63) or a < 0 or b < 0 or banda < 0:
            raise ValueError("parámetros fuera de rango")
        self.inicio, self.a, self.b, self.banda, self.k, self.u = inicio, a, b, banda, k, u
        self.lo, self.hi = lo, hi
        self.primero = True
        self.q = market.MANTENER          # último byte escrito
        self.vio_lo = self.vio_hi = False

    def decidir(self, p):
        primero, self.primero = self.primero, False
        if self._extremo(p):
            return self.q
        if primero:
            if self.inicio == "compra" or (self.inicio == "umbral" and p <= self.u):
                self.q = market.COMPRAR_63
            elif self.inicio == "parte" and self.k > 0:
                self.q = market.MANTENER          # el tick siguiente escribe mantener: compra k una sola vez
                return 0x40 | self.k
        if self.banda and self.vio_lo and self.vio_hi:
            if p <= self.lo + self.banda:
                self.q = market.COMPRAR_63
            elif p >= self.hi - self.banda:
                self.q = market.VENDER_63
        return self.q

    def _extremo(self, p):
        if p <= self.lo + self.a:
            if p <= self.lo:
                self.vio_lo = True
            self.q = market.COMPRAR_63
            return True
        if p >= self.hi - self.b:
            if p >= self.hi:
                self.vio_hi = True
            self.q = market.VENDER_63
            return True
        return False


def leer(ruta):
    return [int(l.split(",")[1]) for l in open(ruta).read().splitlines()[1:]]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Regla de cotas sobre una serie (docs/cotas.md)")
    ap.add_argument("serie", nargs="?", default="data/practica_meta.csv")
    ap.add_argument("--inicio", default=None, choices=["espera", "compra", "parte", "umbral"])
    ap.add_argument("-a", type=int, default=0)
    ap.add_argument("-b", type=int, default=0)
    ap.add_argument("--banda", type=int, default=0)
    ap.add_argument("-k", type=int, default=0)
    ap.add_argument("-u", type=int, default=178)
    ap.add_argument("--perdidos", type=int, default=0)
    a = ap.parse_args(argv)
    precios = leer(a.serie)
    inicios = [a.inicio] if a.inicio else ["espera", "compra"]
    print(f"Serie {a.serie}: {len(precios)} ticks, minimo {min(precios)}, maximo {max(precios)}")
    for ini in inicios:
        m = trader.correr(precios, Cotas(ini, a.a, a.b, a.banda, a.k, a.u), perdidos=a.perdidos)
        print(f"  {ini:7s} a={a.a} b={a.b} banda={a.banda}: patrimonio {m.w}, ordenes {m.ordenes}")


if __name__ == "__main__":
    main()
