#!/usr/bin/env python3
"""Pruebas de la referencia de R1 y R2 (ref/fondo.py).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 ref/test_fondo.py        (o make test-fondo)

Desde el 17/11 (decisión T133, opción F-a) sw/fondo.s corre en el hilo 0 la regla
de cotas de R0 y deja los hilos 1 a 3 en espera. Qué comprueba:
  - Con la tabla por defecto, ref/fondo.py decide byte por byte igual que
    ref/trader.py (Oficial, la regla de sw/trade.s en R0), en la serie Meta, en
    la de práctica anterior y en series de cada familia, crudas y normalizadas
    entre 100 y 255. En la serie Meta da 21 392 con 4 órdenes (banda 40, desde el
    19/11, T140; con banda 60 daba 19 214).
  - La telemetría: 7 segmentos en los ticks pares, LED en los impares, con el
    latido en el bit 10 del número de tick.
  - Los parámetros de la tabla cambian la decisión como se espera, y una falla
    en un hilo 1 a 3 no cambia nada.
  - sw/fondo_tabla.hex es el que genera ref/fondo.py, los desplazamientos que usa
    sw/fondo.s son los del orden de PARAMETROS y el programa no deja nada en la
    zona de datos de la RAM.
"""

import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, "cotas"))
sys.path.insert(0, os.path.join(RAIZ, "tools", "fondo"))

import comun            # noqa: E402
import fondo            # noqa: E402
import market           # noqa: E402
import series           # noqa: E402
import simbolos         # noqa: E402
import trader           # noqa: E402

FAMILIAS = ["modelo", "tendencia", "volatil", "reversion", "paseo", "saltos", "plana", "borde_bajo", "borde_alto"]
META = os.path.join(RAIZ, "data", "practica_meta.csv")


class TestFondo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.meta = market.leer_serie(META)
        cls.lotes = [cls.meta, series.practica()]
        for fam in FAMILIAS:
            for s in series.lote(fam, 2, 4000, 3):
                cls.lotes += [s, comun.normalizar(s)]

    def test_igual_a_la_regla_de_r0(self):
        operan = 0
        for precios in self.lotes:
            for perdidos in (0, 2):
                f = fondo.Fondo()
                self.assertEqual(trader.decisiones(precios, f, perdidos),
                                 trader.decisiones(precios, trader.Oficial(), perdidos))
            # con perdidos = 2 el programa ve desde el tercer precio hasta el último
            vistos = precios[2:]
            self.assertEqual((f.vio_lo, f.vio_hi), (int(min(vistos) <= 100), int(max(vistos) >= 255)))
            operan += f.vio_lo and f.vio_hi
        self.assertGreaterEqual(operan, len(FAMILIAS))       # las normalizadas ven los dos extremos

    def test_serie_meta(self):
        m, f = fondo.correr(self.meta)
        self.assertEqual((m.w, m.ordenes, f.vio_lo, f.vio_hi), (21392, 4, 1, 1))

    def test_telemetria(self):
        traza = []
        precios = comun.normalizar(series.lote("reversion", 1, 3000, 1)[0])
        fondo.correr(precios, traza=traza)
        c = fondo.Fondo.CAMPOS
        for t in traza:
            fila = dict(zip(c, t))
            adentro = fila["byte"] == market.COMPRAR_63
            if fila["tick"] % 2 == 0:
                self.assertEqual(fila["seg"], 0x63 if adentro else 0)
            else:
                esperado = ((fila["tick"] >> 10) & 1) | (fila["vio_lo"] << 1) | (fila["vio_hi"] << 2) | (adentro << 3)
                self.assertEqual(fila["leds"], esperado)
        latidos = {dict(zip(c, t))["leds"] & 1 for t in traza}
        self.assertEqual(latidos, {0, 1})

    def test_parametros(self):
        precios = comun.normalizar(series.lote("reversion", 1, 4000, 1)[0])
        base = trader.decisiones(precios, fondo.Fondo(), 0)
        otra = trader.decisiones(precios, fondo.Fondo({"BANDA_COMPRA": 171}), 0)
        self.assertNotEqual(base, otra)
        ref = trader.decisiones(precios, trader.Oficial(), 0)
        self.assertEqual(base, ref)
        with self.assertRaises(KeyError):
            fondo.Fondo({"G1_ENTRA": -64})

    def test_fallas_no_cambian_nada(self):
        precios = comun.normalizar(series.lote("tendencia", 1, 4000, 2)[0])
        sano = trader.decisiones(precios, fondo.Fondo(), 2)
        for k in (1, 2, 3):
            f = fondo.Fondo(fallas=[fondo.Falla(k)])
            self.assertEqual(trader.decisiones(precios, f, 2), sano)
            self.assertEqual(f.degradados, 0)

    def test_falla_leer(self):
        a = fondo.Falla.leer("3:100:")
        self.assertEqual((a.gestor, a.desde, a.hasta), (3, 100, None))
        b = fondo.Falla.leer("2:50:60")
        self.assertTrue(b.afecta(2, 50) and b.afecta(2, 60) and not b.afecta(2, 61) and not b.afecta(1, 55))
        with self.assertRaises(ValueError):
            fondo.Falla.leer("4")

    def test_tabla_del_programa(self):
        e, palabras = simbolos.ensamblar(os.path.join(RAIZ, "sw", "fondo.s"))
        with open(os.path.join(RAIZ, "sw", "fondo_tabla.hex")) as f:
            self.assertEqual(f.read(), fondo.tabla_hex())
        nombres = [n for n, _ in fondo.PARAMETROS]
        usados = [n for n in e.simbolos if n.startswith("T_")]
        self.assertEqual(sorted(n[2:] for n in usados), sorted(nombres))
        for nombre in usados:
            self.assertEqual(e.simbolos[nombre], 4 * nombres.index(nombre[2:]), nombre)
        self.assertEqual(e.simbolos["TAB_BASE"] & 0xFFFFFFFF, 0x80020000)
        fin = max(i for i, w in enumerate(palabras) if w) + 1
        self.assertLess(4 * fin, 0x7C0)                     # nada en la zona de datos

    def test_tabla_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            fondo.tabla_hex({"HI": 40000})
        self.assertEqual(fondo.tabla_hex({"BANDA_COMPRA": 171}).splitlines()[2], "00ab")


if __name__ == "__main__":
    unittest.main()
