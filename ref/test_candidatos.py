#!/usr/bin/env python3
"""Pruebas de la familia paramétrica, del motor en C y del modelo del generador.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 ref/test_candidatos.py        (o make test-candidatos)

Qué comprueba:
  - Trader con los parámetros por defecto decide igual que la regla base.
  - El motor en C y la referencia en Python dan lo mismo, serie por serie, para
    los candidatos y para combinaciones de parámetros al azar.
  - Los candidatos no pierden la posición ni escriben bytes inválidos.
  - Las familias calibradas son reproducibles y los grupos cubren todas.
  - El filtro de Kalman en punto fijo sigue al de punto flotante.
"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import calibracion as cal   # noqa: E402
import candidatos           # noqa: E402
import market               # noqa: E402
import motor                # noqa: E402
import politica_optima      # noqa: E402
import series               # noqa: E402
import trader               # noqa: E402


def muestra():
    """Lote chico con series de todo tipo."""
    lista = series.bloques(series.practica(), 2000)[:3]
    for nombre, cantidad in (("remuestreo", 6), ("modelo", 6), ("modelo_vecino", 4), ("tendencia", 4), ("saltos", 4),
                             ("cambio_de_caracter", 4), ("volatil", 3), ("nivel_bajo", 3), ("borde_bajo", 2),
                             ("borde_alto", 2), ("plana", 1)):
        lista += series.lote(nombre, cantidad, 2000, 5)
    return lista


def correr_python(parametros, precios):
    t = candidatos.Trader(**parametros)
    m = trader.correr(precios, t)
    return m.w, m.ordenes, m.max_dd, t.ticks_veto, t.cortes, t.topes


def configuracion_al_azar(rng):
    c = {"k": rng.choice([3, 4, 5, 6]), "X": rng.choice([-32, -16, 0, 16, 32])}
    c["E"] = rng.choice([1, 2, 3, 4, 6]) << c["k"]
    c["est"] = rng.choice([0, 0, 0, 1, 2])
    if c["est"] == 1:
        c.update(E=rng.choice([70, 100, 140, 190, 250]), X=rng.choice([-40, 0, 40, 80]),
                 ka=rng.choice([4, 5, 6]), kb=rng.choice([0, 6, 7]), k1a=rng.choice([1, 2]), k1b=rng.choice([0, 2, 3]),
                 k2a=rng.choice([2, 3, 4]), k2b=rng.choice([0, 4]))
    if rng.random() < 0.3:
        c.update(kv=rng.choice([4, 5, 6]), ev=rng.choice([2, 4, 8]), xv=rng.choice([0, 2]), sv=2)
    if rng.random() < 0.5:
        c["J"] = rng.choice([4, 6, 8])
    if rng.random() < 0.5:
        c.update(tmax=rng.choice([24, 48, 96]), lock=rng.choice([0, 0, 64]))
    if rng.random() < 0.3:
        c.update(stop=rng.choice([4, 8, 12]))
    if rng.random() < 0.3:
        c.update(kg=rng.choice([6, 7]), g=rng.choice([32, 96, 160]), gsal=rng.choice([0, 1]))
    if rng.random() < 0.4:
        c.update(nfal=rng.choice([1, 2, 3]), gapag=rng.choice([100, 500, 1000]))
    if rng.random() < 0.5:
        c.update(cap=rng.choice([0, 0, 8, 16]), capsh=rng.choice([1, 2, 3]), capsh2=rng.choice([0, 0, 3, 4]),
                 capoff=rng.choice([0, 0, 300]), capini=rng.choice([0, 1]))
    r = rng.random()
    if r < 0.15:
        c["modo"] = 1
    elif r < 0.3:
        c.update(modo=2, p2=rng.choice([90, 120]))
    elif r < 0.45:
        c.update(q1=rng.choice([20, 32, 40]), E2=c["E"] + (2 << c["k"]))
    return c


class TraderTests(unittest.TestCase):
    def test_por_defecto_es_la_regla_base(self):
        for precios in muestra():
            a, b = candidatos.Trader(), trader.ReglaBase()
            self.assertEqual([a.decidir(p) for p in precios], [b.decidir(p) for p in precios])

    def test_max_media_es_la_oficial(self):
        """El candidato max_media y la estrategia de sw/trade.s deciden igual."""
        for precios in muestra():
            a, b = candidatos.crear("max_media")(), trader.Oficial()
            self.assertEqual([a.decidir(p) for p in precios], [b.decidir(p) for p in precios])

    def test_base_con_otros_parametros(self):
        precios = series.practica()[:4000]
        for k, entra, sale in ((4, 3, 1), (6, 2, 0), (5, 6, 2)):
            a, b = candidatos.Trader(k=k, E=entra << k, X=sale << k), trader.ReglaBase(k, entra, sale)
            self.assertEqual([a.decidir(p) for p in precios], [b.decidir(p) for p in precios])

    def test_bytes_validos(self):
        for nombre in candidatos.CANDIDATOS:
            t = candidatos.crear(nombre)()
            for p in series.lote("saltos", 1, 2000, 3)[0]:
                self.assertIn(t.decidir(p) >> 6, (0, 1, 2))

    def test_parametro_desconocido(self):
        with self.assertRaises(ValueError):
            candidatos.Trader(umbral=3)

    def test_tope_deja_de_operar(self):
        # una caída sostenida con rebotes: el tope tiene que saltar y dejar la estrategia afuera
        precios = [200 - i // 8 + (3 if i % 40 < 6 else 0) for i in range(1500)]
        t = candidatos.Trader(E=96, X=0, capsh=3)
        m = trader.correr(precios, t)
        self.assertGreaterEqual(t.topes, 1)
        self.assertEqual(m.acciones, 0)
        sin = trader.correr(precios, candidatos.Trader(E=96, X=0))
        self.assertGreater(m.w, sin.w)


class MotorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lista = muestra()
        cls.ruta = os.path.join(motor.CACHE, "prueba_candidatos.bin")
        motor.escribir(cls.ruta, cls.lista)

    def comparar(self, parametros):
        filas = motor.detalle(self.ruta, parametros)
        for i, (precios, f) in enumerate(zip(self.lista, filas)):
            esperado = correr_python(parametros, precios)
            obtenido = (f["w"], f["ordenes"], f["max_dd"], f["guardia"], f["cortes"], f["topes"])
            self.assertEqual(obtenido, esperado, f"serie {i}, parametros {parametros}")

    def test_candidatos(self):
        for nombre, (parametros, _, _) in candidatos.CANDIDATOS.items():
            self.comparar(parametros)

    def test_configuraciones_al_azar(self):
        rng = random.Random(2026)
        for _ in range(60):
            self.comparar(configuracion_al_azar(rng))

    def test_resumen(self):
        r = motor.evaluar(self.ruta, [{}, {"E": 96}])
        ws = sorted(correr_python({}, s)[0] for s in self.lista)
        self.assertEqual(int(r[0]["peor"]), ws[0])
        self.assertAlmostEqual(r[0]["media"], sum(ws) / len(ws), places=1)
        self.assertEqual(len(r), 2)

    def test_conjunto_igual_a_series(self):
        ruta = motor.conjunto("modelo", 8, semilla=3)
        self.assertEqual(motor.leer(ruta), series.lote("modelo", 8, 2000, 3))


class SeriesTests(unittest.TestCase):
    def test_grupos(self):
        self.assertEqual(sorted(series.PLAUSIBLES + series.ESTRES), sorted(series.FAMILIAS))

    def test_reproducibles_y_en_rango(self):
        for nombre in series.FAMILIAS:
            a, b = series.lote(nombre, 2, 500, 9), series.lote(nombre, 2, 500, 9)
            self.assertEqual(a, b)
            self.assertTrue(all(1 <= p <= 255 for s in a for p in s), nombre)

    def test_volatilidad_del_modelo(self):
        # la varianza del cambio de un tick del modelo debe parecerse a la de la práctica (0,75)
        s = series.modelo(60000, random.Random(1))
        d = [b - a for a, b in zip(s, s[1:])]
        var = sum(v * v for v in d) / len(d)
        self.assertTrue(0.45 < var < 1.1, var)


class KalmanTests(unittest.TestCase):
    def test_ganancias(self):
        k1, k2, s, _ = politica_optima.kalman(cal.Q_NIVEL, cal.Q_TRANS, cal.PHI)
        self.assertAlmostEqual(k1, 0.614, places=2)
        self.assertAlmostEqual(k2, 0.184, places=2)

    def test_punto_fijo_sigue_al_flotante(self):
        precios = series.lote("modelo", 1, 2000, 4)[0]
        t = candidatos.Trader(est=1)
        nivel, trans = float(precios[0]), 0.0
        phi, k1, k2 = politica_optima.PHI_FIJO, politica_optima.K1_FIJO, politica_optima.K2_FIJO
        peor = 0.0
        for p in precios:
            t.decidir(p)
            tp = phi * trans
            e = p - nivel - tp
            nivel, trans = nivel + k1 * e, tp + k2 * e
            peor = max(peor, abs(t.T / 256 - trans), abs(t.L / 256 - nivel))
        self.assertLess(peor, 0.25)


if __name__ == "__main__":
    unittest.main()
