"""regla_cotas.py: la regla de cotas, sin dependencias (la usan ref/trader.py y ref/cotas.py).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Descripción y variantes en ref/cotas.py y docs/cotas.md. Desde el 17/11 (decisión T133)
la estrategia de los tres peldaños es Cotas("espera", banda=60) (trader.Oficial).
"""
import market

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
