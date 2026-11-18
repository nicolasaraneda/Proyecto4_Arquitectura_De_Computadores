#!/usr/bin/env python3
"""Pruebas del mercado y de la referencia del algoritmo.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 ref/test_ref.py        (o make test-ref)

Qué comprueba:
  - market.py da lo mismo que el mercado de ref/p4_baseline.py, que es el
    archivo de partida del proyecto.
  - La aritmética de ReglaBase (la de trade.s, sin shifter) da lo mismo que
    la fórmula directa de la regla base. La actualización de la media se
    revisa de forma exhaustiva: todos los valores de S y todos los precios.
  - El modelo de los precios que se pierden durante el reset.
  - Las series de prueba: rango, largo y reproducibilidad con la semilla.
  - El protocolo: los números conocidos de la regla base.
  - El gemelo digital contra la referencia, en un lote chico de series.
"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gemelo           # noqa: E402
import market           # noqa: E402
import p4_baseline      # noqa: E402
import protocolo        # noqa: E402
import series           # noqa: E402
import trader           # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERIE = os.path.join(RAIZ, "tb", "practica.csv")


class Directa:
    """Regla base con la fórmula directa (la de p4_baseline.reversion_ema)."""

    def __init__(self, k, entra, sale):
        self.f = p4_baseline.reversion_ema(k, entra, sale)
        self.s = {}

    def decidir(self, p):
        return self.f(self.s, p)


class MercadoTests(unittest.TestCase):
    def test_division_trunca_hacia_cero(self):
        self.assertEqual(market.div_sv(7, 2), 3)
        self.assertEqual(market.div_sv(-7, 2), -3)      # Python daría -4
        self.assertEqual(market.div_sv(-2, 10), 0)      # Python daría -1
        self.assertEqual(market.div_sv(0, 5), 0)

    def test_igual_al_mercado_de_partida(self):
        p = market.leer_serie(SERIE)
        for k, entra, sale in [(5, 4, 0), (4, 2, 1), (6, 8, 0)]:
            w, ordenes, dd = p4_baseline.simular(p, p4_baseline.reversion_ema(k, entra, sale), {})
            m = trader.correr(p, trader.ReglaBase(k, entra, sale))
            self.assertEqual((m.w, m.ordenes, m.max_dd), (w, ordenes, dd))

    def test_comprar_y_mantener(self):
        p = market.leer_serie(SERIE)
        self.assertEqual(market.comprar_y_mantener(p), p4_baseline.comprar_y_mantener(p))

    def test_orden_en_cero_no_paga(self):
        m = market.Mercado()
        m.ejecutar(market.VENDER_63, 100)               # no hay acciones: no se ejecuta
        self.assertEqual((m.caja, m.acciones, m.ordenes), (10000, 0, 0))
        m.ejecutar(market.COMPRAR_63, 100)              # compra 63
        m.ejecutar(market.COMPRAR_63, 100)              # compra lo que alcanza: 36
        m.ejecutar(market.COMPRAR_63, 100)              # ya no alcanza: no se ejecuta
        self.assertEqual((m.acciones, m.ordenes, m.caja), (99, 2, 90))
        m.ejecutar(0xC0 | 63, 100)                      # accion 11: mantener
        self.assertEqual((m.acciones, m.ordenes), (99, 2))

    def test_formato_csv(self):
        filas = []
        market.simular([100, 101], [0x00, 0x7F], filas=filas)
        texto = market.formatear_csv(filas)
        self.assertEqual(texto, "tick,precio,decision,caja,acciones,patrimonio\n"
                                "0,100,00,10000,0,10000\n1,101,7f,3632,63,9995\n")


class ReglaBaseTests(unittest.TestCase):
    def test_media_exhaustiva(self):
        """S + p - ((S + 31) * 8 >> 8) == S + ((32 p - S) >> 5) para todo S y todo p."""
        casos = 0
        for S in range(0, 255 * 32 + 1):
            c = ((S + 31) << 3) >> 8
            self.assertLess((S + 31) << 3, 1 << 16)      # el resultado cabe en el segundo byte
            self.assertEqual(c, -((-S) >> 5))            # es ceil(S / 32)
            for p in (0, 1, 2, 127, 128, 254, 255):
                self.assertEqual(S + p - c, S + (((p << 5) - S) >> 5))
                casos += 1
        # la identidad es lineal en p: p - ceil(S/32). Con todos los S queda cubierta.
        self.assertEqual(casos, 8161 * 7)

    def test_media_no_sale_de_rango(self):
        for S in (32, 8160):
            for p in (1, 255):
                r = trader.ReglaBase()
                r.S = S
                r.decidir(p)
                self.assertTrue(32 <= r.S <= 8160)

    def test_decision_exhaustiva(self):
        """Para todo dev posible y las dos posiciones, el byte es el de la fórmula directa."""
        for umbral in (-128, -96):      # regla base y max_media
          for dev in range(-8128, 8129):
            for pos in (0, 1):
                esperado = 1 if dev < umbral else (0 if dev > 0 else pos)
                compra = 1 if dev < umbral else 0
                no_vende = 1 if dev < 1 else 0
                nuevo = (pos | compra) & no_vende
                self.assertEqual(nuevo, esperado)
                byte = (0xBF + ((-nuevo) & ~0x3F)) & 0xFF
                self.assertEqual(byte, market.COMPRAR_63 if esperado else market.VENDER_63)

    def test_igual_a_la_formula_directa(self):
        p = market.leer_serie(SERIE)
        rng = random.Random(4)
        series = [p,
                  [rng.randint(1, 255) for _ in range(5000)],
                  [1] * 50 + [255] * 50 + [1] * 50,
                  [255] * 50 + [1] * 50 + [255] * 50]
        for k in range(1, 9):
            for entra, sale in [(4, 0), (1, 0), (0, 0), (7, 2), (3, 5)]:
                for serie in series:
                    a, b = trader.ReglaBase(k, entra, sale), Directa(k, entra, sale)
                    self.assertEqual([a.decidir(x) for x in serie], [b.decidir(x) for x in serie],
                                     f"k={k} entra={entra} sale={sale}")

    def test_serie_de_practica(self):
        p = market.leer_serie(SERIE)
        m = trader.correr(p, trader.ReglaBase())
        self.assertEqual((m.w, m.ordenes, m.comisiones, m.max_dd), (27062, 388, 1940, 2929))
        m = trader.correr(p, trader.MaxMedia())     # la oficial hasta el 17/11
        self.assertEqual((m.w, m.ordenes, m.comisiones, m.max_dd), (25973, 624, 3120, 6295))

    def test_serie_meta(self):
        """Desde el 17/11 la oficial es cotas, espera con banda 60 (T133): 19 214 con 4 órdenes en la serie Meta."""
        p = market.leer_serie(os.path.join(os.path.dirname(SERIE), "..", "data", "practica_meta.csv"))
        m = trader.correr(p)
        self.assertEqual((m.w, m.ordenes), (19214, 4))
        self.assertEqual(trader.correr(p, trader.MaxMedia()).w, 9722)

    def test_max_media_y_oficial(self):
        """max_media es la regla base con entrada a 3 unidades; la oficial es la de cotas."""
        r = trader.MaxMedia()
        self.assertEqual((r.k, r.umbral_compra, r.umbral_venta), (5, -96, 1))
        o = trader.Oficial()
        self.assertEqual((o.inicio, o.a, o.b, o.banda, o.lo, o.hi), ("espera", 0, 0, 60, 100, 255))
        b = trader.ReglaBase()
        self.assertEqual((b.k, b.umbral_compra, b.umbral_venta), (5, -128, 1))


class ResetTests(unittest.TestCase):
    def test_ticks_perdidos(self):
        self.assertEqual(trader.ticks_perdidos(100000), 2)        # ronda 3
        self.assertEqual(trader.ticks_perdidos(1000000), 1)       # ronda 2
        self.assertEqual(trader.ticks_perdidos(10000000), 1)      # ronda 1
        self.assertEqual(trader.ticks_perdidos(100000, por_bits=4), 0)   # reset del repositorio base

    def test_desfase(self):
        class Eco:
            def decidir(self, p):
                return p
        self.assertEqual(trader.decisiones([10, 20, 30, 40], Eco()), [0, 10, 20, 30])
        self.assertEqual(trader.decisiones([10, 20, 30, 40], Eco(), perdidos=2), [0, 0, 0, 30])


class SeriesTests(unittest.TestCase):
    def test_rango_y_largo(self):
        for nombre in ["remuestreo"] + list(series.FAMILIAS):
            for s in series.lote(nombre, 5, 500, semilla=3):
                self.assertEqual(len(s), 500, nombre)
                self.assertTrue(all(isinstance(p, int) and 1 <= p <= 255 for p in s), nombre)

    def test_reproducible(self):
        for nombre in ["remuestreo", "paseo", "saltos"]:
            self.assertEqual(series.lote(nombre, 3, 300, semilla=7), series.lote(nombre, 3, 300, semilla=7))
            self.assertNotEqual(series.lote(nombre, 1, 300, semilla=7), series.lote(nombre, 1, 300, semilla=8))

    def test_reflejar(self):
        self.assertEqual([series.reflejar(x) for x in (1, 255, 0, -3, 256, 259, 509, 510)],
                         [1, 255, 2, 5, 254, 251, 1, 2])

    def test_bloques(self):
        b = series.bloques(series.practica())
        self.assertEqual((len(b), len(b[0]), len(b[-1])), (10, 2000, 2000))

    def test_remuestreo_usa_incrementos_de_la_practica(self):
        p = series.practica()
        incrementos = {b - a for a, b in zip(p, p[1:])}
        s = series.lote("remuestreo", 1, 2000, semilla=0)[0]
        fuera = [b - a for a, b in zip(s, s[1:]) if b - a not in incrementos]
        self.assertLess(len(fuera), 20)       # solo los rebotes en los bordes pueden salirse


class ProtocoloTests(unittest.TestCase):
    def test_regla_base_en_los_bloques(self):
        b = series.bloques(series.practica())
        r = protocolo.resumen(protocolo.evaluar("base", b), b)
        self.assertEqual((round(r["media"]), r["peor"], r["sobre_byh"]), (11069, 9720, 0.9))

    def test_fabrica_con_parametros(self):
        e = protocolo.fabrica("base:k=4,entra=3,sale=1")()
        self.assertEqual((e.k, e.umbral_compra, e.umbral_venta), (4, -48, 17))

    def test_suma_movil_igual_al_punto_de_partida(self):
        p = series.practica()
        w, ordenes, dd = p4_baseline.simular(p, p4_baseline.reversion_sma(64, 4, 1), {})
        m = trader.correr(p, protocolo.SumaMovil(64, 4, 1))
        self.assertEqual((m.w, m.ordenes, m.max_dd), (w, ordenes, dd))


class GemeloTests(unittest.TestCase):
    """sw/trade.hex en el gemelo digital contra la referencia."""

    def test_lote_igual_a_la_referencia(self):
        lote = [s for nombre in ("remuestreo", "plana", "borde_bajo", "borde_alto", "saltos")
                for s in series.lote(nombre, 4, 600, semilla=5)]
        for periodo in (100000, 1000000):
            res = gemelo.correr_lote(lote, periodo_ns=periodo)
            for s, g in zip(lote, res):
                m = trader.correr(s)
                self.assertEqual((g["patrimonio"], g["ordenes"], g["perdida_max"]), (m.w, m.ordenes, m.max_dd))
                self.assertEqual((g["respuestas"], g["precios_perdidos"]), (len(s), 0))

    def test_reset_del_testbench(self):
        """Con la primera transacción a los 4000 ns se pierden 2 precios a 0,1 ms, como en el RTL."""
        p = series.practica()[:300]
        g = gemelo.correr_lote([p], inicio_ns=4000)[0]
        m = trader.correr(p, perdidos=trader.ticks_perdidos(100000))
        self.assertEqual((g["patrimonio"], g["ordenes"], g["respuestas"]), (m.w, m.ordenes, 298))


if __name__ == "__main__":
    unittest.main()
