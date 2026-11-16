#!/usr/bin/env python3
"""contabilidad.py: la contabilidad propia hecha con mulstep y divstep.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Un hilo supervisor que quiera saber su caja, sus acciones y su patrimonio
tiene que repetir la contabilidad de la maestra (tarea `ejecutar` de
tb/tb_proyecto_4.sv, portada en ref/market.py). Este script:

  1. Calcula los anchos que necesita cada cantidad para una caja inicial de
     1 000 a 100 000 y precios de 1 a 255.
  2. Lleva esa contabilidad usando solo lo que tendría el programa: sumas,
     restas, comparaciones, 8 pasos de mulstep para cada producto y 8 pasos de
     divstep para la compra recortada (modelo ref/xd.py), y la compara tick a
     tick con ref/market.py en la serie de práctica y en series al azar.
  3. Cuenta cuántos productos y cocientes hacen falta por tick y entrega el
     costo en instrucciones de cada forma de multiplicar y de dividir.

    python3 tools/contabilidad.py > mediciones/contabilidad.txt
"""
import os
import random
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(AQUI, "..", "..", "..")
sys.path.insert(0, os.path.join(AQUI, "..", "ref"))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
import xd  # noqa: E402
import market  # noqa: E402
import trader  # noqa: E402


class Sombra:
    """Contabilidad propia con las operaciones de la extensión.

    Cada producto es multiplicar(precio, x): el precio (8 bits) va de
    multiplicador en los 8 bits altos y x de multiplicando, que debe caber en
    24 bits. Cada cociente es dividir(n, precio), que exige n < 256 * precio.
    """

    def __init__(self, caja0, comision):
        self.caja, self.acciones, self.comision = caja0, 0, comision
        self.w = caja0
        self.productos = self.cocientes = 0
        self.max_prod_tick = self.max_coc_tick = 0
        self.max_caja, self.max_acc, self.max_w = caja0, 0, caja0

    def producto(self, p, x):
        assert 0 <= x < (1 << 24) and 1 <= p <= 255, (p, x)
        self.productos += 1
        self._p += 1
        r = xd.multiplicar(p, x, n=8)
        assert r == p * x
        return r

    def cociente(self, n, p):
        assert 0 <= n < 256 * p, (n, p)
        self.cocientes += 1
        self._c += 1
        return xd.dividir(n, p)

    def ejecutar(self, decision, p):
        self._p = self._c = 0
        q = decision & 63
        accion = (decision >> 6) & 3
        if accion == 1 and q:
            r = self.caja - self.comision
            if r >= p:                                  # alcanza para una acción al menos
                costo = self.producto(p, q)             # q * p, a lo más 63 * 255
                if r >= costo:                          # sin recorte
                    self.caja = r - costo
                else:                                   # recorte: q = r div p, y la caja que queda es r mod p
                    q, resto = self.cociente(r, p)
                    self.caja = resto
                self.acciones += q
        elif accion == 2 and q:
            q = min(q, self.acciones)
            if q:
                ingreso = self.producto(p, q)
                if self.caja + ingreso >= self.comision:
                    self.caja += ingreso - self.comision
                    self.acciones -= q
        self.w = self.caja + self.producto(p, self.acciones)     # patrimonio
        self.max_prod_tick = max(self.max_prod_tick, self._p)
        self.max_coc_tick = max(self.max_coc_tick, self._c)
        self.max_caja = max(self.max_caja, self.caja)
        self.max_acc = max(self.max_acc, self.acciones)
        self.max_w = max(self.max_w, self.w)


def comparar(precios, decisiones, caja0, comision):
    """Corre las dos contabilidades y exige que coincidan en cada tick."""
    m = market.Mercado(caja0, comision)
    s = Sombra(caja0, comision)
    for n, (p, d) in enumerate(zip(precios, decisiones)):
        m.ejecutar(d, p)
        s.ejecutar(d, p)
        assert (m.caja, m.acciones, m.w) == (s.caja, s.acciones, s.w), (n, p, d, m.caja, s.caja)
    return m, s


def bits(x):
    return max(1, int(x).bit_length())


def main():
    print("Contabilidad propia con mulstep y divstep")
    print("Generado por factibilidad/d_isa/tools/contabilidad.py (make contabilidad). No editar a mano.")

    print("\n== 1. Anchos ==")
    print("Contabilidad oficial (tb/tb_proyecto_4.sv): compra recortada a (caja - comisión) / p, venta recortada a las")
    print("acciones, a lo más 63 acciones por orden. Precio p de 1 a 255 (8 bits).\n")
    print(f"{'cantidad':<56} {'máximo':>11} {'bits':>5}")
    filas = [("precio p", 255), ("acciones por orden q", 63), ("costo de una orden q * p", 63 * 255),
             ("caja inicial", 100000), ("acciones con caja inicial y p = 1", 100000 - 5),
             ("acciones si el patrimonio se multiplica por 100 y p = 1", 100 * 100000),
             ("multiplicando que acepta mulstep con 8 pasos", (1 << 24) - 1),
             ("producto que cabe en un registro", (1 << 32) - 1)]
    for nombre, v in filas:
        print(f"{nombre:<56} {v:>11} {bits(v):>5}")
    print("\nEl multiplicador siempre es el precio (8 bits, 8 pasos). El multiplicando es q (6 bits) o las acciones.")
    print("Con 8 pasos de mulstep el multiplicando puede tener 24 bits: 16,7 millones de acciones, 167 veces la")
    print("caja inicial más grande aun con el precio en 1. El producto acciones * p cabe en 32 bits.")
    print("El cociente de la compra recortada es menor que 63 (6 bits), así que los 8 bits de divstep sobran, y su")
    print("condición N < 256 D se cumple siempre que hay recorte, porque ahí caja - comisión < 63 p.")

    print("\n== 2. Comprobación contra ref/market.py ==")
    rng = random.Random(7)
    practica = market.leer_serie(os.path.join(RAIZ, "tb", "practica.csv"))
    ticks = casos = 0
    peor = dict(prod=0, coc=0, caja=0, acc=0, w=0)
    tot_prod = tot_coc = 0

    def acumular(s, n):
        nonlocal ticks, casos, tot_prod, tot_coc
        ticks += n
        casos += 1
        tot_prod += s.productos
        tot_coc += s.cocientes
        peor.update(prod=max(peor["prod"], s.max_prod_tick), coc=max(peor["coc"], s.max_coc_tick),
                    caja=max(peor["caja"], s.max_caja), acc=max(peor["acc"], s.max_acc), w=max(peor["w"], s.max_w))

    print(f"{'serie y órdenes':<52} {'caja0':>7} {'com.':>5} {'ticks':>7} {'patrimonio':>11} {'prod.':>7} {'coc.':>6}")
    for caja0 in (1000, 10000, 100000):
        for comision in (0, 5, 50):
            dec = trader.decisiones(practica, trader.ReglaBase())
            m, s = comparar(practica, dec, caja0, comision)
            acumular(s, len(practica))
            print(f"{'práctica, regla base (comprar 63 y vender 63)':<52} {caja0:>7} {comision:>5} {len(practica):>7} {m.w:>11} {s.productos:>7} {s.cocientes:>6}")
    # Series al azar con órdenes al azar: todas las cantidades y los precios de borde
    for caso in range(300):
        caja0 = rng.choice([1000, 10000, 100000, rng.randrange(1000, 100001)])
        comision = rng.choice([0, 5, 50, rng.randrange(0, 51)])
        n = 2000
        modo = caso % 3
        p = rng.randrange(1, 256)
        precios = []
        for _ in range(n):
            if modo == 0:
                p = min(255, max(1, p + rng.randrange(-3, 4)))
            elif modo == 1:
                p = rng.choice([1, 2, 254, 255, rng.randrange(1, 256)])
            else:
                p = rng.randrange(1, 256)
            precios.append(p)
        dec = [rng.choice([0, 0x40, 0x80, 0xC0]) | rng.choice([0, 1, 2, 62, 63, rng.randrange(64)]) for _ in range(n)]
        m, s = comparar(precios, dec, caja0, comision)
        acumular(s, n)
    print(f"{'300 series al azar de 2000 ticks, órdenes al azar':<52} {'varias':>7} {'0-50':>5} {300 * 2000:>7}")
    print(f"\nPASS: caja, acciones y patrimonio idénticos a ref/market.py en {ticks} ticks de {casos} corridas.")
    print(f"Productos hechos: {tot_prod}. Cocientes hechos: {tot_coc}. Por tick, peor caso: {peor['prod']} productos y {peor['coc']} cociente.")
    print(f"Máximos vistos: caja {peor['caja']} ({bits(peor['caja'])} bits), acciones {peor['acc']} ({bits(peor['acc'])} bits), "
          f"patrimonio {peor['w']} ({bits(peor['w'])} bits).")
    print("El cociente solo aparece en la compra recortada. La venta se recorta con una comparación.")
    print("La caja que queda después de una compra recortada es el resto de esa misma división.")

    print("\n== 3. Costo de cada forma de multiplicar y de dividir (ESTIMADO, no hay programa) ==")
    print("Instrucciones por operación, contadas a mano sobre la secuencia que usaría el programa. En el barrel cada")
    print("instrucción de un hilo son 4 ciclos de reloj; en el segmentado, 1 ciclo (2 un load). El periférico exige")
    print("pedir la lectura 9 ciclos o más después de escribir MULB: en el segmentado son 8 ciclos de espera.\n")
    print(f"{'forma':<52} {'instr.':>6}  notas")
    opciones = [
        ("Producto 8 x 24, solo RV32E (sumar y duplicar)", "48", "8 bits del precio x 6 instrucciones, sin saltos"),
        ("Producto con mulstep", "10", "sb y lw para dejar el precio en los 8 bits altos (no hay shift), y 8 pasos"),
        ("Producto con el periférico MMIO", "3 + 2", "sw, sw, dos instrucciones cualesquiera y lw (barrel: el lw va 12 ciclos después); tiene estado: un solo hilo"),
        ("Producto con mulc (combinacional)", "1", "8 x 8 cabe; 16 x 8 no cabe; acciones de más de 8 bits no caben"),
        ("Cociente de 6 bits, solo RV32E (6 restas de prueba)", "35", "5 sumas para 2p a 32p y 6 x 5 de comparar y restar"),
        ("Cociente y resto con divstep", "11", "8 pasos, andi para el cociente, y sw y lbu para el resto (es menor que p: un byte)"),
        ("Cociente buscando con el multiplicador", "60", "6 pasos de búsqueda binaria x (producto y comparación)"),
    ]
    for forma, n, nota in opciones:
        print(f"{forma:<52} {n:>6}  {nota}")
    print("\nContabilidad completa de un tick, peor caso (una compra recortada): 2 productos y 1 cociente más unas")
    print("12 instrucciones de comparar, sumar y elegir (estimado). Con mulstep y divstep: 2 x 10 + 11 + 12 = 43")
    print("instrucciones. Solo con RV32E: 2 x 48 + 35 + 12 = 143. Con mulstep y sin divstep: 2 x 10 + 35 + 12 = 67.")
    print("En el barrel, a 4 ciclos por instrucción del hilo: 172, 572 y 268 ciclos. El presupuesto de la ronda más")
    print("rápida son 2262 ciclos, así que las tres caben; lo que cambia es cuánto queda para el resto del tick.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
