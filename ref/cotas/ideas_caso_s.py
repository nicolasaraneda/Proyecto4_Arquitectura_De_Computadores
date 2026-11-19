#!/usr/bin/env python3
"""ideas_caso_s.py: variante del caso S (docs/exploracion_ideas.md, sección 10; pedido del 19/11).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Caso S: el 100 llega antes que el 255. La regla de los peldaños compra en el 100, vende al ver el
255 (ahí empieza la fase D) y desde entonces sigue su comportamiento de D, que puede volver a
comprar (banda 40: con 140 o menos; tres bandas: cada tercio en su nivel). Modos, solo en el caso S:
  'nunca'  no vuelve a comprar después de vender en el 255;
  'tercio' vuelve a comprar, pero la posición total queda en un tercio del patrimonio, fijado al
           momento de la recompra (no se reajusta tick a tick);
  'todo'   lo actual (igual al comportamiento base).
En el caso B (el 255 antes que el 100) la regla no cambia.

No toca ideas.py: registra el tipo 'casoS' en ideas.COMPS al importarse.
"""
import ideas
from ideas import Comp, C, V, HI, hacia


class CasoSD(Comp):
    def __init__(self, base=("banda", {"w": 40}), modo="todo"):
        self.B = ideas.comp(base)
        self.modo = modo
        self.caso = 0           # 1 = S, 2 = B
        self.obj = None
        self.k_prev = 0
        self.recompras = 0      # veces que el comportamiento base pasa de caja a comprado en el caso S
        self.nivel_venta = getattr(self.B, "nivel_venta", 215)

    @property
    def obs(self):
        return getattr(self.B, "obs", None)

    def _k(self, r):
        """Tercios (o fracción) que el comportamiento base querría tener comprados."""
        est = getattr(self.B, "est", None)
        if est is not None:
            return sum(est)
        return 1 if r.q == C else 0

    def entra(self, r, p, caja, acc):
        self.caso = 1 if p >= HI else 2
        return self._f(r, p, caja, acc, self.B.entra(r, p, caja, acc))

    def d(self, r, p, caja, acc):
        return self._f(r, p, caja, acc, self.B.d(r, p, caja, acc))

    def _f(self, r, p, caja, acc, o):
        if self.caso != 1:
            return o
        k = self._k(r)
        if k > 0 and self.k_prev == 0:
            self.recompras += 1
        self.k_prev = k
        if self.modo == "todo":
            return o
        if self.modo == "nunca" or k == 0:
            self.obj = None
            return V
        if self.obj is None:
            self.obj = (caja + acc * p) // (3 * p)
        return hacia(self.obj, acc)

    def info(self):
        return (self.caso, self.recompras)


ideas.COMPS["casoS"] = lambda base=("banda", {"w": 40}), modo="todo": CasoSD(base, modo)
