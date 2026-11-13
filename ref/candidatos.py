#!/usr/bin/env python3
"""candidatos.py: familia paramétrica de estrategias y candidatos a algoritmo final.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

`Trader` es la referencia en Python de la familia de estrategias que explora
el frente del algoritmo (docs/algoritmo.md). Con los parámetros por defecto es
exactamente la regla base de ref/trader.py. Cada pieza se enciende con un
parámetro entero:

  estimador   est, k, ka, kb, k1a, k1b, k2a, k2b   media exponencial, Kalman de dos estados o suma móvil
  bandas      E, X                                 entra si dev < -E, sale si dev > X
  volatilidad kv, ev, xv, sv                       bandas que se ensanchan con la volatilidad medida
  saltos      J                                    un cambio de J o más corre el nivel y no se opera
  cortes      tmax, stop, lock                     tope de tiempo y de precio de una posición
  guardia     nfal, gapag  (o kg, g, gsal)         deja de operar si la serie no está revirtiendo
  tope        cap, capsh, capsh2, capoff, capini   tope de pérdida acumulada
  órdenes     modo, p2, q1, E2                     tamaño y escalonado de las órdenes

Todas las operaciones son sumas, restas, comparaciones y desplazamientos por
una constante, sobre enteros: lo mismo que puede hacer sw/trade.s. Un
desplazamiento a la derecha de Python (`>>`) redondea hacia abajo también con
negativos, igual que un desplazamiento aritmético.

El mismo algoritmo está escrito en C en ref/motor/motor.c, para barrer miles
de combinaciones. ref/test_candidatos.py exige que los dos coincidan.

    python3 ref/candidatos.py                   # lista los candidatos y su costo estimado
    python3 ref/protocolo.py --estrategia cand:intermedio
    python3 ref/protocolo.py --estrategia trader:E=96,X=0,J=8

Ninguno de estos candidatos está en la placa todavía: sw/trade.s sigue siendo
la regla base hasta que se elija uno.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import market           # noqa: E402

FK = 8                  # bits de fracción del filtro de Kalman
SIN_FIN = 0x7FFFFFFF

POR_DEFECTO = dict(
    est=0, k=5, ka=5, kb=7, k1a=1, k1b=3, k2a=3, k2b=4,
    E=128, X=0,
    kv=0, ev=0, xv=0, sv=0,
    J=0,
    tmax=0, stop=0, lock=0,
    kg=0, g=0, gsal=0, nfal=0, gapag=0,
    cap=0, capsh=0, capsh2=0, capoff=0, capini=0,
    modo=0, p2=0, q1=0, E2=0,
)


class Trader:
    """Estrategia paramétrica. `decidir(p)` devuelve el byte de DECISION."""

    def __init__(self, **parametros):
        desconocidos = set(parametros) - set(POR_DEFECTO)
        if desconocidos:
            raise ValueError(f"parámetros desconocidos: {sorted(desconocidos)}")
        self.c = dict(POR_DEFECTO, **parametros)
        self.ini = False
        self.S = self.L = self.T = self.V = self.G = self.pant = 0
        self.pos = self.etapa = self.t_dentro = self.p_entrada = 0
        self.bloqueo = self.espera = self.perdida = self.apagado = 0
        self.compro = self.fallas = self.pausa = 0
        self.buf, self.bi, self.suma = [], 0, 0
        # contadores para los informes (no influyen en las decisiones)
        self.ticks_veto = self.cortes = self.topes = self.pausas = 0

    def decidir(self, p):
        c = self.c
        k = c["k"]
        if not self.ini:
            self.ini = True
            self.pant = p
            self.S, self.L, self.T = p << k, p << FK, 0
            if c["est"] == 2:
                self.buf, self.suma = [p] * (1 << k), p << k
        d = p - self.pant
        self.pant = p
        ad = -d if d < 0 else d
        if c["J"] and ad >= c["J"]:              # salto: el nivel se corre con el precio
            self.S += d << k
            self.L += d << FK
            if c["est"] == 2:
                self.buf = [v + d for v in self.buf]
                self.suma += d << k
            ad = 0

        # --- estimador: desviación del precio respecto al nivel -----------------
        if c["est"] == 0:                         # media exponencial
            dev = (p << k) - self.S
            self.S += dev >> k
        elif c["est"] == 2:                       # suma móvil de 2^k precios
            dev = (p << k) - self.suma
            self.suma += p - self.buf[self.bi]
            self.buf[self.bi] = p
            self.bi = (self.bi + 1) & ((1 << k) - 1)
        else:                                     # Kalman de dos estados: nivel L y transitoria T
            T = self.T
            Tp = T - (T >> c["ka"]) - ((T >> c["kb"]) if c["kb"] else 0)      # phi * T
            e = (p << FK) - self.L - Tp                                        # innovación
            self.L += (e >> c["k1a"]) + ((e >> c["k1b"]) if c["k1b"] else 0)  # K1 * e
            self.T = Tp + (e >> c["k2a"]) + ((e >> c["k2b"]) if c["k2b"] else 0)  # K2 * e
            dev = self.T

        # --- bandas ---------------------------------------------------------------
        E, X = c["E"], c["X"]
        if c["kv"]:
            E += (c["ev"] * self.V) >> c["sv"]
            X += (c["xv"] * self.V) >> c["sv"]
            self.V += ad - ((self.V + (1 << c["kv"]) - 1) >> c["kv"])

        # --- guardia y tope: cuándo no se puede entrar ---------------------------
        guardia = False
        if c["kg"]:
            guardia = self.G < -c["g"]
            self.G += (dev - self.G) >> c["kg"]
        if self.apagado > 0:
            self.apagado -= 1
            if self.apagado == 0:
                self.perdida = 0
        if self.pausa > 0:
            self.pausa -= 1
        veto = guardia or self.apagado != 0 or self.pausa != 0
        if self.bloqueo > 0:
            self.bloqueo -= 1

        entra = dev < -E
        sale = dev > X
        if self.espera and sale:                  # después de un corte espera a que el precio recupere la media
            self.espera = 0
        corte = tope = False
        if self.pos:
            self.t_dentro += 1
            if c["tmax"] and self.t_dentro > c["tmax"]:
                corte = True
            if c["stop"] and p <= self.p_entrada - c["stop"]:
                corte = True
            if guardia and c["gsal"]:
                corte = True
            if c["cap"] or c["capsh"]:
                limite = c["cap"] + ((p >> c["capsh"]) if c["capsh"] else 0) + ((p >> c["capsh2"]) if c["capsh2"] else 0)
                if self.perdida + (p - self.p_entrada) < -limite:
                    tope = True

        if self.pos and (sale or corte or tope):
            self.pos = self.etapa = 0
            self.perdida += p - self.p_entrada
            if self.perdida > 0 and not c["capini"]:
                self.perdida = 0                  # se mide desde el mejor momento
            if corte and not sale:
                self.cortes += 1
                if c["lock"]:
                    self.bloqueo = c["lock"]
                else:
                    self.espera = 1
                self.fallas += 1
                if c["nfal"] and self.fallas >= c["nfal"]:
                    self.pausa = c["gapag"]
                    self.fallas = 0
                    self.pausas += 1
            elif not tope:
                self.fallas = 0
            if tope:
                self.apagado = c["capoff"] if c["capoff"] else SIN_FIN
                self.topes += 1
        elif not self.pos and entra and not sale and not veto and not self.bloqueo and not self.espera:
            self.pos = self.etapa = 1
            self.t_dentro = 0
            self.p_entrada = p
            self.compro = 0
        if self.pos and c["q1"] and self.etapa == 1 and dev < -c["E2"]:
            self.etapa = 2
        self.ticks_veto += veto

        # --- byte de decisión -------------------------------------------------------
        if not self.pos:
            return market.VENDER_63
        if c["q1"] and self.etapa == 1:
            decision = market.MANTENER if self.compro else (0x40 | c["q1"])
        elif c["modo"] == 1:
            decision = market.MANTENER if self.compro else market.COMPRAR_63
        elif c["modo"] == 2:
            decision = market.MANTENER if (self.compro and p > c["p2"]) else market.COMPRAR_63
        else:
            return market.COMPRAR_63
        self.compro = 1
        return decision


# ---- Piezas de protección -----------------------------------------------------------
# Se suman a cualquier juego de bandas. Ver docs/algoritmo.md, sección 6.
SALTOS = dict(J=8)                                               # manejo de saltos de nivel
GUARDIA = dict(tmax=48, nfal=3, gapag=1000)                      # guardia de régimen por cortes seguidos
TOPE = dict(capsh=1)                                             # tope de pérdida: 50 % del precio
PROTECCION = dict(**SALTOS, **GUARDIA, **TOPE)
PROTECCION_FUERTE = dict(J=8, tmax=48, nfal=2, gapag=1000, capsh=2)   # guardia más sensible y tope de 25 %

# ---- Candidatos ----------------------------------------------------------------------
# (parámetros, instrucciones por tick estimadas, descripción). El costo se
# estima con el modelo de docs/trade_s.md: la regla base mide 27 instrucciones
# y 58 ciclos sin contar la espera. Los cuatro primeros después de la base son
# los que se presentan sobre la frontera entre media y percentil 5.
CANDIDATOS = {
    "base": (dict(E=128, X=0), 27, "regla base: entra 4 bajo la media, sale al recuperarla"),
    "max_media": (dict(E=96, X=0), 27, "entra 3 bajo la media, sale al recuperarla, sin protección"),
    "guardia": (dict(E=96, X=0, **SALTOS, **GUARDIA), 70, "max_media con manejo de saltos y guardia de régimen"),
    "guardia_tope": (dict(E=96, X=0, **PROTECCION), 85, "max_media con saltos, guardia y tope de pérdida"),
    "prudente": (dict(E=192, X=-32), 27, "entra 6 bajo la media, sale 1 antes de recuperarla, sin protección"),
    "kalman": (dict(est=1, E=190, X=-40), 140, "Kalman de dos estados con bandas equivalentes a max_media"),
}


def crear(nombre):
    """Función que construye el candidato `nombre`."""
    parametros = CANDIDATOS[nombre][0]
    return lambda: Trader(**parametros)


def main():
    print(f"{'candidato':16s} {'instr':>5s} {'ciclos':>6s}  parametros distintos de la regla base")
    for nombre, (par, instr, descripcion) in CANDIDATOS.items():
        ciclos = round(instr * 58 / 27)
        print(f"{nombre:16s} {instr:5d} {ciclos:6d}  {' '.join(f'{k}={v}' for k, v in par.items())}")
        print(f"{'':30s}{descripcion}")
    print("\nPresupuesto de la ronda 3: 2262 ciclos por tick. El costo es una estimación hasta que el candidato esté en trade.s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
