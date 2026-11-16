#!/usr/bin/env python3
"""Pruebas de la referencia del fondo en un chip (ref/fondo.py).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 ref/test_fondo.py        (o make test-fondo)

Qué comprueba:
  - Con los tres gestores sanos, ref/fondo.py da los números que la
    factibilidad midió con su módulo en C para `fondo_min` (patrimonio,
    órdenes, pesos finales y cambios de pesos en cinco corridas).
  - Una segunda escritura del mismo fondo, hecha aparte y con la aritmética de
    la factibilidad (puntaje en dieciseisavos, media con (S + 31) >> 5 y
    margen 2 * ventaja > p), da los mismos bytes y los mismos pesos. Es lo que
    respalda llevar el puntaje en treintaidosavos y la media con emad.
  - Degradación: sin ningún voto los bytes son los de max_media sola
    (ref/trader.py); con un voto ausente no se ajustan los pesos; una falla
    acotada deja de tener efecto en los votos cuando termina.
  - La tabla de parámetros de sw/fondo.s es la de ref/fondo.py, palabra por
    palabra, y el programa no tiene otras constantes del algoritmo.
"""
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(RAIZ, "tools", "fondo"))

import fondo            # noqa: E402
import market           # noqa: E402
import series           # noqa: E402
import simbolos         # noqa: E402
import trader           # noqa: E402

FAMILIAS = ["modelo", "tendencia", "volatil", "reversion", "paseo", "saltos", "plana", "borde_bajo", "borde_alto"]


class FondoFactibilidad:
    """`fondo_min` como lo escribe el programa de la factibilidad, sin compartir código con fondo.py."""

    GESTORES = [(-96, 1), (-128, 1), (-64, 17)]

    def __init__(self):
        self.s = [None] * 3
        self.pos = [0] * 3
        self.ejec = [0] * 3
        self.des = [0] * 3
        self.p16 = 0
        self.w = [6, 5, 5]
        self.wmax = [10, 9, 9]
        self.wmin = [2, 1, 1]
        self.ref = [0] * 3
        self.faltan = 512

    def decidir(self, p):
        primero = self.s[0] is None
        for k, (entra, sale) in enumerate(self.GESTORES):
            if primero:
                self.s[k] = 32 * p
            else:
                if self.ejec[k]:
                    self.des[k] += 16 * p - self.p16
                self.des[k] -= self.ejec[k] ^ self.pos[k]
                self.ejec[k] = self.pos[k]
            dev = 32 * p - self.s[k]
            self.pos[k] = (self.pos[k] | (dev < entra)) & (dev < sale)
            self.s[k] = self.s[k] + p - ((self.s[k] + 31) >> 5)
        self.p16 = 16 * p
        self.faltan -= 1
        if self.faltan == 0:
            self.faltan = 512
            g = [self.des[k] - self.ref[k] for k in range(3)]
            self.ref = list(self.des)
            mejor = max(range(3), key=lambda k: (g[k], -k))      # el primero entre los empatados
            peor = min(range(3), key=lambda k: (g[k], k))
            if 2 * (g[mejor] - g[peor]) > p and self.w[mejor] < self.wmax[mejor] and self.w[peor] > self.wmin[peor]:
                self.w[mejor] += 1
                self.w[peor] -= 1
        f = sum(w for w, x in zip(self.w, self.pos) if x)
        return market.COMPRAR_63 if f >= 8 else market.VENDER_63


class TestFondo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.practica = series.practica()

    def correr(self, precios, perdidos=2, **k):
        return fondo.correr(precios, perdidos, **k)

    def test_numeros_de_la_factibilidad(self):
        casos = [
            (self.practica, 2, 26070, 630, [7, 6, 3], 20),
            (self.practica[:3000], 1, 9904, 92, [6, 6, 4], 3),
            (series.lote("modelo", 1, 20000, 1)[0], 2, 11208, 325, [3, 4, 9], 15),
            (series.lote("tendencia", 1, 20000, 1)[0], 2, 13079, 185, [6, 2, 8], 6),
            (series.lote("volatil", 1, 20000, 1)[0], 2, 374864, 6521, [8, 5, 3], 31),
        ]
        for precios, perdidos, w, ordenes, pesos, cambios in casos:
            m, f = self.correr(precios, perdidos)
            self.assertEqual((m.w, m.ordenes, f.w, f.cambios), (w, ordenes, pesos, cambios))
            self.assertEqual(f.degradados, 0)

    def test_igual_a_la_aritmetica_de_la_factibilidad(self):
        lotes = [self.practica] + [s for fam in FAMILIAS for s in series.lote(fam, 2, 6000, 3)]
        for precios in lotes:
            a = fondo.Fondo()
            b = FondoFactibilidad()
            self.assertEqual(trader.decisiones(precios, a, 2), trader.decisiones(precios, b, 2))
            self.assertEqual(a.w, b.w)
            self.assertEqual([g.puntaje for g in a.gestores], [2 * d for d in b.des])
            self.assertEqual([g.s for g in a.gestores], b.s)

    def test_sin_votos_es_max_media(self):
        fallas = [fondo.Falla(k) for k in (1, 2, 3)]
        for precios in [self.practica] + [series.lote(fam, 1, 6000, 5)[0] for fam in FAMILIAS]:
            f = fondo.Fondo(fallas=fallas)
            self.assertEqual(trader.decisiones(precios, f, 2), trader.decisiones(precios, trader.Oficial(), 2))
            self.assertEqual(f.cambios, 0)

    def test_sin_un_voto_no_se_ajustan_los_pesos(self):
        precios = series.lote("reversion", 1, 6000, 1)[0]
        _, sano = self.correr(precios)
        self.assertGreater(sano.cambios, 0)
        for k in (1, 2, 3):
            _, f = self.correr(precios, fallas=[fondo.Falla(k)])
            self.assertEqual((f.cambios, f.w, f.degradados), (0, [6, 5, 5], len(precios) - 2))

    def test_falla_acotada(self):
        precios = series.lote("reversion", 1, 6000, 1)[0]
        traza = []
        _, f = self.correr(precios, fallas=[fondo.Falla(2, 1024, 1024)], traza=traza)
        self.assertEqual(f.degradados, 1)
        campos = fondo.Fondo.CAMPOS
        fila = dict(zip(campos, traza[1023]))
        self.assertEqual((fila["tick"], fila["llego2"], fila["v2"]), (1024, 0, fila["pos0"]))
        # el tick 1024 es de frontera: sin los tres votos no hay ajuste ahí
        self.assertEqual(traza[1022][campos.index("w1"):campos.index("w3") + 1],
                         traza[1023][campos.index("w1"):campos.index("w3") + 1])
        self.assertTrue(all(dict(zip(campos, t))["llego2"] for t in traza[1024:]))

    def test_falla_leer(self):
        a = fondo.Falla.leer("3:100:")
        self.assertEqual((a.gestor, a.desde, a.hasta), (3, 100, None))
        b = fondo.Falla.leer("2:50:60")
        self.assertTrue(b.afecta(2, 50) and b.afecta(2, 60) and not b.afecta(2, 61) and not b.afecta(1, 55))
        self.assertTrue(fondo.Falla.leer("1").afecta(1, 1))
        with self.assertRaises(ValueError):
            fondo.Falla.leer("4")

    def test_tabla_del_programa(self):
        e, palabras = simbolos.ensamblar(os.path.join(RAIZ, "sw", "fondo.s"))
        base = e.simbolos["TABLA"] // 4
        n = len(fondo.PARAMETROS)
        self.assertEqual([w & 0xFFFFFFFF for w in palabras[base:base + n]], fondo.palabras_tabla())
        self.assertEqual(e.simbolos["PUB"], e.simbolos["TABLA"] + 4 * n)
        self.assertTrue(all(w == 0 for w in palabras[base + n:]))


if __name__ == "__main__":
    unittest.main()
