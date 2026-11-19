#!/usr/bin/env python3
"""ideas_reloj.py: ideas 13 y 14 de docs/exploracion_ideas.md (pedido del 19/11).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Idea 13 (la 11 del pedido): niveles de la banda según el orden de los extremos. Caso S: el 100
llegó antes que el 255 (la fase D empieza al ver el 255). Caso B: el 255 llegó antes que el 100
(la fase D empieza al ver el 100). Un par (compra, venta) para cada caso.

Idea 14 (la 12 del pedido): reloj de día de mercado. Detectores de la fase del día que un hilo
puede correr solo con la serie recibida (sin multiplicar, dividir ni desplazar), y la regla que
compra para pasar el salto de cierre a apertura.

Este archivo no cambia ideas.py: registra sus comportamientos en ideas.COMPS al importarse, así
que las cachés de la primera tanda siguen valiendo.
"""
import ideas
from ideas import Comp, BandaD, C, V, M, HI, LARGO

DIA = 390


class OrdenD(Comp):
    """Idea 13. S y B son pares (compra, venta): compra 63 con p <= compra, vende 63 con p >= venta."""

    def __init__(self, S=(140, 215), B=(140, 215)):
        self.S, self.Bp = tuple(S), tuple(B)
        self.caso = 0          # 1 = S, 2 = B
        self.banda = None
        self.nivel_venta = 215

    def entra(self, r, p, caja, acc):
        # el tick que completa los dos extremos es el del segundo: 255 en el caso S, 100 en el B
        self.caso = 1 if p >= HI else 2
        c, v = self.S if self.caso == 1 else self.Bp
        self.banda = BandaD(c, v)
        self.nivel_venta = v
        return self.banda.d(r, p, caja, acc)

    def d(self, r, p, caja, acc):
        return self.banda.d(r, p, caja, acc)

    def info(self):
        return (self.caso,)


# --------------------------------------------------------------------------------------------
# Idea 14: detectores de la fase del día. Cada uno recibe los precios de a uno y responde, antes
# de ver el precio del tick n, si predice que el tick n es el salto de cierre a apertura. Solo
# usan sumas, restas, comparaciones y un contador que da la vuelta en 390.

class DetectorHistograma:
    """Suma |p(n) - p(n-1)| en el casillero c = n mod 390 (contador con vuelta) y lleva el
    casillero con más suma, actualizado en cada tick (una comparación). Memoria: 390 contadores."""

    def __init__(self):
        self.H = [0] * DIA
        self.c = 0
        self.mejor = -1
        self.prev = None

    def predice(self):
        """¿El tick que viene cae en el casillero elegido?"""
        return self.mejor >= 0 and self.c == self.mejor

    def paso(self, p):
        if self.prev is not None:
            d = p - self.prev
            if d < 0:
                d = -d
            h = self.H[self.c] + d
            self.H[self.c] = h
            if self.mejor < 0 or h > self.H[self.mejor]:
                self.mejor = self.c
        self.prev = p
        self.c += 1
        if self.c == DIA:
            self.c = 0


class DetectorBloque:
    """Cada 390 ticks guarda el casillero del mayor |p(n) - p(n-1)| del bloque. Fija la fase
    cuando dos bloques seguidos dan el mismo casillero; la suelta si un bloque da otro. Memoria:
    cuatro palabras. Si un día viene corto, vuelve a fijar en dos días."""

    def __init__(self):
        self.c = 0
        self.max_b = -1
        self.pos_b = -1
        self.ultimo = -2
        self.fase = -1
        self.prev = None

    def predice(self):
        return self.fase >= 0 and self.c == self.fase

    def paso(self, p):
        if self.prev is not None:
            d = p - self.prev
            if d < 0:
                d = -d
            if d > self.max_b:
                self.max_b, self.pos_b = d, self.c
        self.prev = p
        self.c += 1
        if self.c == DIA:
            self.c = 0
            if self.pos_b == self.ultimo:
                self.fase = self.pos_b
            elif self.fase >= 0 and self.pos_b != self.fase:
                self.fase = -1
            self.ultimo = self.pos_b
            self.max_b, self.pos_b = -1, -1


DETECTORES = {"histograma": DetectorHistograma, "bloque": DetectorBloque}

# Minuto del día de cada tick de la ventana en curso, solo para el detector "oraculo" (cota superior); lo fija
# el corredor antes de crear la estrategia de cada ventana. La placa no lo tiene.
MINUTOS_VENTANA = None


class RelojD(Comp):
    """Idea 14, la regla del pedido: en la fase D, si la banda está en caja, compra para pasar el
    salto (signo +1) y vende después; con signo -1 no hay nada que hacer en caja (ya está fuera
    del salto), así que solo actúa con signo +1. 'oraculo' usa el minuto verdadero del día (cota
    superior); si no, el detector. La orden decidida tras ver p(n-1) se ejecuta a p(n): para estar
    adentro en el salto (tick j) la compra se decide tras ver p(j-2) y se ejecuta a p(j-1); se
    vende h ticks después del salto. q: acciones por orden (una sola orden de compra y una de venta)."""

    def __init__(self, base=("banda", {"w": 40}), detector="histograma", minutos=None, h=1, q=63):
        self.B = ideas.comp(base)
        self.det = DETECTORES[detector]() if detector != "oraculo" else None
        # para el oráculo: minuto del día de cada tick de la ventana
        self.minutos = (minutos if minutos is not None else MINUTOS_VENTANA) if detector == "oraculo" else None
        self.h, self.qmax = h, q
        self.estado = 0             # 0 nada, 1 comprado por el salto
        self.vender_en = -1
        self.vueltas = 0
        self.obs_base = getattr(self.B, "obs", None)

    def obs(self, r, p):
        if self.det is not None:
            self.det.paso(p)
        if self.obs_base is not None:
            self.obs_base(r, p)

    def _salto_en(self, r, k):
        """¿El tick n + k es un salto? (n = tick actual, ya visto)."""
        if self.minutos is not None:
            t = r.n + k
            return t < LARGO and self.minutos[t] == 0
        # el detector ya avanzó con p(n): su contador apunta al tick n + 1
        if k == 1:
            return self.det.predice()
        return False

    def entra(self, r, p, caja, acc):
        return self._decide(r, p, caja, acc, self.B.entra(r, p, caja, acc))

    def d(self, r, p, caja, acc):
        return self._decide(r, p, caja, acc, self.B.d(r, p, caja, acc))

    def _decide(self, r, p, caja, acc, o):
        if self.estado == 1:
            if r.n >= self.vender_en:
                if acc == 0:
                    self.estado = 0
                    return o
                return 0x80 | min(63, acc) if (o >> 6) != 1 else o
            return M
        # la banda en caja: o es vender (o mantener con la posición vendida) y no hay acciones
        if acc == 0 and (o >> 6) != 1 and self._salto_previsto(r):
            self.estado = 1
            self.vueltas += 1
            self.vender_en = r.n + 1 + self.h
            return 0x40 | self.qmax
        return o

    def _salto_previsto(self, r):
        """Compra decidida ahora (tras p(n)) se ejecuta en n + 1; el salto debe ser n + 2."""
        if self.minutos is not None:
            return self._salto_en(r, 2)
        # el detector predice el tick n + 1; para el n + 2 se mira un casillero más adelante
        d = self.det
        if isinstance(d, DetectorHistograma):
            sig = d.c + 1 if d.c + 1 < DIA else 0
            return d.mejor >= 0 and sig == d.mejor
        sig = d.c + 1 if d.c + 1 < DIA else 0
        return d.fase >= 0 and sig == d.fase

    def info(self):
        return (self.vueltas,)


ideas.COMPS["orden"] = lambda S=(140, 215), B=(140, 215): OrdenD(S, B)
ideas.COMPS["reloj"] = lambda **kw: RelojD(**kw)
