#!/usr/bin/env python3
"""trader.py: referencia oficial del algoritmo que corre en sw/trade.s.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Estrategia oficial: `max_media` (decisión T50). Es la regla base con el
umbral de entrada en 3 unidades en vez de 4 (E = 96 en la notación de
ref/candidatos.py). La regla base se conserva como `ReglaBase` porque es la
referencia contra la que el protocolo compara a los candidatos.

Regla de reversión a la media (la misma aritmética para las dos):

  - Se lleva una media exponencial del precio con alfa = 1/32, guardada
    multiplicada por 32 (S = 32 * media, punto fijo con 5 bits de fracción).
  - Con cada precio p se calcula la desviación dev = 32 p - S.
  - Si dev < -32 * ENTRA se entra: -96 en `max_media` (3 unidades bajo la
    media) y -128 en la regla base (4 unidades).
  - Si dev > 0 (el precio recuperó la media) se sale.
  - Si no pasa ninguna de las dos cosas se mantiene la posición anterior.
  - La orden es siempre por 63 acciones: "comprar 63" si se quiere estar
    adentro y "vender 63" si se quiere estar afuera. La maestra recorta la
    orden a lo que alcanza, así que repetirla no cuesta comisión.
  - Después se actualiza la media: S = S + ((32 p - S) >> 5).

La clase `ReglaBase` hace las cuentas con las mismas operaciones que trade.s,
que no tiene shifter. El desplazamiento aritmético se reescribe así:

    (32 p - S) >> 5  =  p - ceil(S / 32)  =  p - ((S + 31) >> 5)

y el desplazamiento a la derecha de un número no negativo se hace en el
programa multiplicando por 8 (tres sumas) y leyendo el segundo byte de la
palabra desde la memoria. `ref/test_ref.py` comprueba que esta forma da lo
mismo que la fórmula directa de ref/p4_baseline.py.

Uso:

    python3 ref/trader.py tb/practica.csv                    # tabla del punto 3.1
    python3 ref/trader.py tb/practica.csv -o build/ref.csv   # decisiones.csv de referencia
    python3 ref/trader.py tb/practica.csv --nticks 2000 --periodo-ns 100000 -o build/ref.csv

Con --periodo-ns se modelan los precios que el programa no alcanza a ver en el
testbench porque llegan durante el reset de la placa (ver `ticks_perdidos`).
"""
import argparse
import sys

import market

K = 5                    # alfa = 1 / 2^K
ENTRA_BASE = 4           # regla base: entra si el precio está más de 4 unidades bajo la media
ENTRA = 3                # max_media, la que corre en sw/trade.s: 3 unidades
SALE = 0                 # sale si el precio está más de SALE unidades sobre la media


class ReglaBase:
    """Regla base con la aritmética exacta de sw/trade.s.

    Estado: S (media por 2^k, de 13 bits para k = 5) y pos (0 afuera, 1 adentro).
    El primer precio inicializa la media: S = 2^k * p.
    """

    def __init__(self, k=K, entra=ENTRA_BASE, sale=SALE):
        if not 1 <= k <= 8:
            raise ValueError("k debe estar entre 1 y 8 para que el desplazamiento salga de un byte")
        if entra + sale < 0:
            raise ValueError("entra + sale debe ser >= 0: comprar y vender serían simultáneos")
        self.k = k
        self.umbral_compra = -(entra << k)     # compra si dev < umbral_compra
        self.umbral_venta = (sale << k) + 1    # no vende si dev < umbral_venta
        self.S = None
        self.pos = 0

    def decidir(self, p):
        """Recibe el precio p y devuelve el byte que queda en DECISION."""
        k = self.k
        if self.S is None:
            self.S = p << k
        dev = (p << k) - self.S
        compra = 1 if dev < self.umbral_compra else 0
        no_vende = 1 if dev < self.umbral_venta else 0
        self.pos = (self.pos | compra) & no_vende
        # byte: 0xBF (vender 63) o 0x7F (comprar 63)
        decision = (0xBF + ((-self.pos) & ~0x3F)) & 0xFF
        # media: S + ((2^k p - S) >> k), sin desplazar números negativos
        self.S = self.S + p - (((self.S + (1 << k) - 1) << (8 - k)) >> 8)
        return decision


class MaxMedia(ReglaBase):
    """`max_media`: la regla base con entrada a 3 unidades. Es la de sw/trade.s."""

    def __init__(self, k=K, entra=ENTRA, sale=SALE):
        super().__init__(k, entra, sale)


# La estrategia que corre en sw/trade.s y contra la que se compara el RTL
Oficial = MaxMedia


def ticks_perdidos(periodo_ns, por_bits=12, inicio_ns=4000):
    """Cuántos precios iniciales no ve el programa en el testbench.

    El power-on reset de pochoco_soc dura 2^por_bits - 1 ciclos de 40 ns. El
    testbench manda la primera transacción a los 4000 ns, sin esperar. Una
    transacción cuyo primer flanco de SCLK (1500 ns después de bajar CS_n)
    llega antes de que termine el reset no se recibe: el esclavo SPI está en
    reset, no levanta byte_done y responde 0 por MISO.

    Con el reset de 4095 ciclos (163,8 us): 2 precios a 0,1 ms y 1 precio a
    1 ms y a 10 ms. En la placa no se pierde ninguno, porque está encendida
    desde mucho antes del primer precio.
    """
    fin_reset_ns = ((1 << por_bits) - 1) * 40 + 20 + 3 * 40    # más la sincronización de CS_n
    n = 0
    while inicio_ns + n * periodo_ns + 1500 < fin_reset_ns:
        n += 1
    return n


def decisiones(precios, estrategia, perdidos=0):
    """Byte que la maestra lee en cada tick.

    En el tick n la maestra lee lo que el programa escribió después de ver el
    precio n-1. DECISION parte en 0 (mantener) y no cambia mientras el programa
    no haya visto ningún precio. Los primeros `perdidos` precios no se ven.
    """
    salida = []
    actual = market.MANTENER
    for n, p in enumerate(precios):
        salida.append(actual)
        if n >= perdidos:
            actual = estrategia.decidir(p)
    return salida


def correr(precios, estrategia=None, perdidos=0, caja0=market.CAJA0, comision=market.COMISION, filas=None):
    """Corre la estrategia sobre la serie. Devuelve el Mercado final."""
    if estrategia is None:
        estrategia = Oficial()
    return market.simular(precios, decisiones(precios, estrategia, perdidos), caja0, comision, filas)


def tabla_3_1(precios, perdidos=0):
    """Tabla del punto 3.1: el algoritmo contra no operar y comprar y mantener."""
    base = correr(precios, ReglaBase(), perdidos=perdidos)
    m = correr(precios, perdidos=perdidos)
    byh = market.simular(precios, [market.MANTENER] + [market.COMPRAR_63] * (len(precios) - 1))
    filas = [
        ("no operar", market.CAJA0, 0, 0, 0),
        ("comprar y mantener (testbench)", market.comprar_y_mantener(precios), 1, market.COMISION, None),
        ("comprar 63 siempre (trade.s del tramo 1)", byh.w, byh.ordenes, byh.comisiones, byh.max_dd),
        ("regla base (trade.s hasta el 15/11)", base.w, base.ordenes, base.comisiones, base.max_dd),
        ("max_media (trade.s)", m.w, m.ordenes, m.comisiones, m.max_dd),
    ]
    print(f"{'estrategia':42s} {'patrimonio':>10s} {'ordenes':>8s} {'comisiones':>10s} {'perdida max':>11s}")
    for nombre, w, ordenes, comisiones, dd in filas:
        print(f"{nombre:42s} {w:10d} {ordenes:8d} {comisiones:10d} {'' if dd is None else dd:>11}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Referencia del algoritmo de sw/trade.s")
    ap.add_argument("serie", nargs="?", default="tb/practica.csv")
    ap.add_argument("--nticks", type=int, default=None, help="usar solo los primeros N ticks")
    ap.add_argument("--periodo-ns", type=int, default=None,
                    help="período del testbench: modela los precios que se pierden durante el reset")
    ap.add_argument("--perdidos", type=int, default=None, help="fijar a mano cuántos precios iniciales no se ven")
    ap.add_argument("--por-bits", type=int, default=12, help="ancho del contador de reset de pochoco_soc")
    ap.add_argument("-o", "--salida", help="escribir el decisiones.csv de referencia")
    a = ap.parse_args(argv)

    precios = market.leer_serie(a.serie, a.nticks)
    if a.perdidos is not None:
        perdidos = a.perdidos
    elif a.periodo_ns is not None:
        perdidos = ticks_perdidos(a.periodo_ns, a.por_bits)
    else:
        perdidos = 0

    print(f"Serie {a.serie}: {len(precios)} ticks, precios iniciales que el programa no ve: {perdidos}")
    if a.salida:
        filas = []
        m = correr(precios, perdidos=perdidos, filas=filas)
        market.escribir_csv(a.salida, filas)
        print(f"{a.salida}: patrimonio final {m.w}, {m.ordenes} ordenes, perdida maxima {m.max_dd}")
    else:
        tabla_3_1(precios, perdidos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
