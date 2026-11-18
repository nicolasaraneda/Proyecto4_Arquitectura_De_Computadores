"""planb.py: reglas para el caso en que las rondas no tocan los extremos (docs/cotas.md, sección 6).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Referencias en Python de los tipos "rango", "salto" y "tendencia" de evaluar.c (la misma
aritmética entera); validar.py exige que den los mismos bytes.
"""
import market

C, V, M = market.COMPRAR_63, market.VENDER_63, market.MANTENER


class Rango:
    """Compra si p <= L, vende si p >= H. inicio 1: compra con el primer precio si es <= u."""

    def __init__(self, L, H, inicio=0, u=0):
        self.L, self.H, self.inicio, self.u = L, H, inicio, u
        self.primero, self.q = True, M

    def decidir(self, p):
        if self.primero:
            self.primero = False
            self.q = C if (self.inicio == 1 and p <= self.u) else M
        if p <= self.L:
            self.q = C
        elif p >= self.H:
            self.q = V
        return self.q


class Salto:
    """Al ver un salto de G o más (dir 0 hacia abajo, 1 hacia arriba) compra y vende N precios después."""

    def __init__(self, G, N, dir=0):
        self.G, self.N, self.dir = G, N, dir
        self.primero, self.q, self.prev, self.resta = True, M, 0, 0

    def decidir(self, p):
        if self.primero:
            self.primero, self.prev, self.q = False, p, M
            return self.q
        d = p - self.prev
        self.prev = p
        if (self.dir == 0 and d <= -self.G) or (self.dir == 1 and d >= self.G):
            self.q, self.resta = C, self.N
        elif self.resta > 0:
            self.resta -= 1
            if self.resta == 0:
                self.q = V
        return self.q


class Tendencia:
    """Cruce de medias exponenciales de 2^k1 y 2^k2 precios, en punto fijo de 16 bits."""

    def __init__(self, k1, k2, d):
        self.k1, self.k2, self.d = k1, k2, d
        self.primero, self.q, self.F, self.L = True, M, 0, 0

    def decidir(self, p):
        x = p << 16
        if self.primero:
            self.primero, self.F, self.L, self.q = False, x, x, M
            return self.q
        self.F += (x - self.F) >> self.k1
        self.L += (x - self.L) >> self.k2
        dif, um = self.F - self.L, self.d << 16
        if dif > um:
            self.q = C
        elif dif < -um:
            self.q = V
        return self.q


class UnaVez:
    """Rival de la ronda de Tesla del 18/11 (UnaVez(100, 220) dio 21 467): parte en caja, al ver
    p <= L compra 63 (repetido) y, ya adentro, al ver p >= H vende 63 (repetido) y no vuelve a entrar."""

    def __init__(self, L=100, H=220):
        self.L, self.H = L, H
        self.estado, self.q = 0, M         # 0 esperando, 1 adentro, 2 terminado

    def decidir(self, p):
        if self.estado == 0 and p <= self.L:
            self.estado, self.q = 1, C
        elif self.estado == 1 and p >= self.H:
            self.estado, self.q = 2, V
        return self.q
