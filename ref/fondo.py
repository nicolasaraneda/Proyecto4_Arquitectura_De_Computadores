#!/usr/bin/env python3
"""
fondo.py: referencia exacta de sw/fondo.s, el fondo de cuatro hilos que corre
en el Espino barrel (docs/fondo.md).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Es la configuración `fondo_min` de la factibilidad (tres gestores de la regla
de reversión, pesos 6/5/5 que se ajustan cada 512 ticks y voto con mayoría de
8/16), más la degradación que pide el diseño de competencia: el supervisor
calcula `max_media` por su cuenta y la usa en el lugar de cada voto que no
llegó. Con los tres gestores sanos el flujo de bytes es el de `fondo_min`.

Por cada precio p que el programa ve (tick t = 1, 2, 3...):

  Gestor k (hilos 1, 2 y 3), con sus umbrales entra_k y sale_k:
    1. Puntaje en papel, en treintaidosavos de unidad de precio:
         puntaje += 32 (p - p anterior)   si tenía la acción
         puntaje -= 2                     si la orden del tick anterior cambió su posición
    2. dev = 32 p - S, con S la media exponencial por 32 (alfa 1/32).
       pos = (pos | dev < entra_k) & (dev < sale_k)
    3. Publica el puntaje y después su voto: el tick t y pos.
    4. S = S + (dev >>> 5).
    En su primer precio S parte en 32 p y no hay puntaje que sumar.

  Supervisor (hilo 0):
    1. Calcula `max_media` propia con el mismo paso 2 y 4 (pos0).
    2. Voto de cada gestor: su pos si llegó con el tick t; si no, pos0.
    3. Cada VENTANA ticks, y solo si llegaron los tres votos: g_k es lo que
       ganó el gestor k en la ventana. Si la ventaja del mejor sobre el peor
       supera 1/32 del precio y los topes lo permiten, pasa 1/16 de peso del
       peor al mejor.
    4. F = suma de los pesos de los votos adentro. Byte: comprar 63 si
       F >= UMBRAL, vender 63 si no.

El puntaje se lleva en treintaidosavos y no en dieciseisavos como en la
factibilidad porque así sale de `devk` sin más instrucciones. Es el doble
exacto, y la comparación con el margen se escala igual, así que ninguna
decisión cambia (lo comprueba `ref/test_fondo.py` contra los números medidos
en la factibilidad).

Las fallas se describen con `Falla`: desde qué tick y hasta cuál el voto de un
gestor no llega. Un gestor que no publica sigue llevando su estado en este
modelo: sirve para un gestor colgado (no vuelve) y para uno atrasado menos de
un tick (sus votos llegan siempre tarde, pero no se salta precios).

Uso:
  python3 ref/fondo.py                         # tabla contra max_media
  python3 ref/fondo.py SERIE --periodo-ns 100000 -o ref.csv
  python3 ref/fondo.py --falla 3:100: -o ref.csv    # gestor 3 sin voto desde el tick 100
  python3 ref/fondo.py --traza traza.csv       # estado interno por tick
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import market
import trader

K = 5                    # alfa = 1/32. El hardware solo tiene k = 5

# Tabla de parámetros, en el orden en que está en la memoria (sw/fondo.s,
# etiqueta TABLA). Los umbrales van en unidades de dev (precio por 32).
PARAMETROS = [
    ("S_ENTRA", -96),    # supervisor, max_media: entra si dev < -3 * 32
    ("S_SALE", 1),       #                         sale si dev > 0
    ("G1_ENTRA", -96),   # gestor 1, max_media
    ("G1_SALE", 1),
    ("G2_ENTRA", -128),  # gestor 2, base: entra 4 bajo la media
    ("G2_SALE", 1),
    ("G3_ENTRA", -64),   # gestor 3, activo: entra 2 bajo la media
    ("G3_SALE", 17),     #                    sale medio punto sobre la media
    ("W1_INI", 6),       # pesos iniciales (el prior), en dieciseisavos
    ("W2_INI", 5),
    ("W3_INI", 5),
    ("W1_MAX", 10),      # prior + 4
    ("W2_MAX", 9),
    ("W3_MAX", 9),
    ("W1_MIN", 2),       # prior - 4
    ("W2_MIN", 1),
    ("W3_MIN", 1),
    ("VENTANA", 512),    # ticks entre ajustes de los pesos
    ("UMBRAL", 8),       # compra si los pesos adentro suman 8/16 o más
    ("PLAZO", 8),        # vueltas del lazo de espera antes de decidir sin los que falten
]
POR_DEFECTO = dict(PARAMETROS)

M32 = 0xFFFFFFFF


def s32(x):
    """Interpreta x como entero de 32 bits con signo."""
    x &= M32
    return x - (1 << 32) if x & 0x80000000 else x


class Regla:
    """La regla de reversión de sw/trade.s con umbrales libres (un gestor o el supervisor)."""

    def __init__(self, entra, sale):
        self.entra = entra
        self.sale = sale
        self.s = None
        self.pos = 0

    def paso(self, p):
        if self.s is None:
            self.s = 32 * p
        dev = s32(32 * p - self.s)
        entrar = 1 if dev < self.entra else 0
        no_salir = 1 if dev < self.sale else 0
        self.pos = (self.pos | entrar) & no_salir
        self.s = s32(self.s + (dev >> K))
        return self.pos


class Gestor(Regla):
    """Un gestor en papel: la regla más su puntaje por acción."""

    def __init__(self, entra, sale):
        super().__init__(entra, sale)
        self.ejecutada = 0       # posición ya ejecutada en papel
        self.puntaje = 0         # en treintaidosavos de unidad de precio
        self.p32 = None          # 32 p del tick anterior

    def paso(self, p):
        if self.p32 is not None:
            if self.ejecutada:
                self.puntaje = s32(self.puntaje + 32 * p - self.p32)
            self.puntaje = s32(self.puntaje - 2 * (self.ejecutada ^ self.pos))
            self.ejecutada = self.pos
        self.p32 = 32 * p
        return super().paso(p)


class Falla:
    """El voto del gestor `gestor` (1, 2 o 3) no llega entre los ticks `desde` y `hasta`."""

    def __init__(self, gestor, desde=1, hasta=None):
        self.gestor = gestor
        self.desde = desde
        self.hasta = hasta

    def afecta(self, gestor, tick):
        return gestor == self.gestor and tick >= self.desde and (self.hasta is None or tick <= self.hasta)

    @classmethod
    def leer(cls, texto):
        """ "3:100:" gestor 3 desde el tick 100; "2:50:60" gestor 2 entre el 50 y el 60; "1" siempre."""
        partes = texto.split(":")
        gestor = int(partes[0])
        desde = int(partes[1]) if len(partes) > 1 and partes[1] else 1
        hasta = int(partes[2]) if len(partes) > 2 and partes[2] else None
        if gestor not in (1, 2, 3):
            raise ValueError("el gestor de una falla es 1, 2 o 3")
        return cls(gestor, desde, hasta)


class Fondo:
    """El fondo completo. `decidir(p)` devuelve el byte que queda en DECISION."""

    CAMPOS = ("tick", "precio", "byte", "pos0", "v1", "v2", "v3", "llego1", "llego2", "llego3",
              "w1", "w2", "w3", "des1", "des2", "des3", "s0", "s1", "s2", "s3")

    def __init__(self, parametros=None, fallas=()):
        q = dict(POR_DEFECTO)
        if parametros:
            q.update(parametros)
        self.q = q
        self.sup = Regla(q["S_ENTRA"], q["S_SALE"])
        self.gestores = [Gestor(q[f"G{k}_ENTRA"], q[f"G{k}_SALE"]) for k in (1, 2, 3)]
        self.w = [q["W1_INI"], q["W2_INI"], q["W3_INI"]]
        self.wmax = [q["W1_MAX"], q["W2_MAX"], q["W3_MAX"]]
        self.wmin = [q["W1_MIN"], q["W2_MIN"], q["W3_MIN"]]
        self.ref = [0, 0, 0]             # puntaje de cada gestor al empezar la ventana
        self.faltan = q["VENTANA"]       # ticks que faltan para la frontera
        self.fallas = list(fallas)
        self.tick = 0
        self.cambios = 0                 # ajustes de pesos hechos
        self.degradados = 0              # ticks decididos sin algún voto
        self.traza = None                # lista de tuplas si se pide

    def decidir(self, p):
        self.tick += 1
        t = self.tick
        pos0 = self.sup.paso(p)
        self.faltan -= 1
        posiciones = [g.paso(p) for g in self.gestores]
        llego = [not any(f.afecta(k + 1, t) for f in self.fallas) for k in range(3)]
        votos = [posiciones[k] if llego[k] else pos0 for k in range(3)]
        if all(llego):
            if self.faltan == 0:
                self._frontera(p)
        else:
            self.degradados += 1
            if self.faltan == 0:         # sin los tres votos no se tocan los pesos
                self.faltan = self.q["VENTANA"]
        f = sum(w for w, v in zip(self.w, votos) if v)
        byte = market.COMPRAR_63 if f >= self.q["UMBRAL"] else market.VENDER_63
        if self.traza is not None:
            self.traza.append((t, p, byte, pos0, *votos, *(int(x) for x in llego), *self.w,
                               *(g.puntaje for g in self.gestores), self.sup.s, *(g.s for g in self.gestores)))
        return byte

    def _frontera(self, p):
        """Ajuste de pesos. Mismo orden de comparaciones que sw/fondo.s."""
        g = []
        for k in range(3):
            des = self.gestores[k].puntaje
            g.append(s32(des - self.ref[k]))
            self.ref[k] = des
        mejor = peor = 0
        for k in (1, 2):
            if g[k] > g[mejor]:
                mejor = k
            if g[k] < g[peor]:
                peor = k
        self.faltan = self.q["VENTANA"]
        if p >= g[mejor] - g[peor]:              # la ventaja no supera 1/32 del precio
            return
        if self.w[mejor] >= self.wmax[mejor] or self.wmin[peor] >= self.w[peor]:
            return
        self.w[mejor] += 1
        self.w[peor] -= 1
        self.cambios += 1


def correr(precios, perdidos=0, parametros=None, fallas=(), filas=None, traza=None):
    """Corre el fondo sobre la serie. Devuelve (Mercado final, Fondo)."""
    fondo = Fondo(parametros, fallas)
    fondo.traza = traza
    m = market.simular(precios, trader.decisiones(precios, fondo, perdidos), filas=filas)
    return m, fondo


def palabras_tabla(parametros=None):
    """Las palabras de la tabla de parámetros, en el orden de la memoria."""
    q = dict(POR_DEFECTO)
    if parametros:
        q.update(parametros)
    return [q[nombre] & M32 for nombre, _ in PARAMETROS]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Referencia de sw/fondo.s")
    ap.add_argument("serie", nargs="?", default="tb/practica.csv")
    ap.add_argument("--nticks", type=int, default=None, help="usar solo los primeros N ticks")
    ap.add_argument("--periodo-ns", type=int, default=None,
                    help="período del testbench: modela los precios que se pierden durante el reset")
    ap.add_argument("--perdidos", type=int, default=None, help="fijar a mano cuántos precios iniciales no se ven")
    ap.add_argument("--falla", action="append", default=[], metavar="G[:DESDE[:HASTA]]",
                    help="el voto del gestor G no llega entre esos ticks (se puede repetir)")
    ap.add_argument("--param", action="append", default=[], metavar="NOMBRE=VALOR",
                    help="cambia un parámetro de la tabla (se puede repetir)")
    ap.add_argument("-o", "--salida", help="escribir el decisiones.csv de referencia")
    ap.add_argument("--traza", help="escribir el estado interno por tick")
    ap.add_argument("--tabla", action="store_true", help="mostrar la tabla de parámetros y salir")
    a = ap.parse_args(argv)

    parametros = {}
    for texto in a.param:
        nombre, valor = texto.split("=")
        if nombre not in POR_DEFECTO:
            ap.error(f"parametro desconocido: {nombre}")
        parametros[nombre] = int(valor, 0)
    if a.tabla:
        for (nombre, _), palabra in zip(PARAMETROS, palabras_tabla(parametros)):
            print(f"{nombre:10s} {s32(palabra):6d}  0x{palabra:08x}")
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
    print(f"fondo: patrimonio final {m.w}, {m.ordenes} ordenes, perdida maxima {m.max_dd}, "
          f"pesos finales {fondo.w[0]}/{fondo.w[1]}/{fondo.w[2]} con {fondo.cambios} cambios, "
          f"{fondo.degradados} ticks sin algun voto")
    if a.salida:
        market.escribir_csv(a.salida, filas)
    if a.traza:
        with open(a.traza, "w", newline="\n") as f:
            f.write(",".join(Fondo.CAMPOS) + "\n")
            for fila in traza:
                f.write(",".join(str(x) for x in fila) + "\n")
    if not a.salida and not a.traza:
        mm = trader.correr(precios, perdidos=perdidos)
        print(f"max_media sola: patrimonio final {mm.w}, {mm.ordenes} ordenes, perdida maxima {mm.max_dd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
