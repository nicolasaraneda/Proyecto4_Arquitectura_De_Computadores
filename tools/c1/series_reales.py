#!/usr/bin/env python3
"""series_reales.py: C1 y la banda 40 y 60 en la serie de práctica Meta y en las de la clase del 18/11.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Parte del script de comparación que Nicolás armó el 21/11 (tres reglas por serie, con la fase en que cae
cada orden). Cambios: el rival "unavez 100 220" de la ronda de Tesla (el que hizo 21 467 en la clase) ahora
está bien escrito (el original no compraba nunca y daba 10 000), y el script comprueba lo que
docs/c1_dia_de_prueba.md (sección 10) pide ver en la maestra con la serie de práctica Meta a 10 ms.

Series: data/practica_meta.csv (en el repositorio) y build/reales/tesla.csv y amd.csv (las de la clase del
18/11; las arma tools/reales.sh desde $P4_DATOS; si faltan, se saltan). Una orden se cuenta en el tick n
cuando la maestra la ejecuta al precio n; la fase es la que tenía la regla después de ver el precio n-1,
que es la que decidió esa orden.

Comprobaciones (si alguna falla, el programa sale con código 1):
  - las cifras de la referencia que ya estaban escritas: banda 60 en Tesla 18 779 y en AMD 21 895 (lo que
    mostró la maestra el 18/11), banda 40 en Meta 21 392, Tesla 20 795 y AMD 26 470, y el rival de Tesla 21 467;
  - C1 en Meta (lo que se mira en la maestra, docs/c1_dia_de_prueba.md): la primera orden es una compra de
    22 acciones en la fase A en el tick 8234 al precio 222; la segunda, en el tick 10966; el patrimonio final
    22 682 con 6 órdenes.

Uso, desde la raíz: python3 tools/c1/series_reales.py [-o salida.txt]   (make c1-series-reales)
"""
import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.dont_write_bytecode = True
sys.path[:0] = [os.path.join(RAIZ, "ref"), os.path.join(RAIZ, "ref", "c1")]
import market  # noqa: E402
import trader  # noqa: E402
from regla_cotas import Cotas  # noqa: E402
import c1 as C1m  # noqa: E402
import tablas as TB  # noqa: E402

SERIES = (("Meta", "data/practica_meta.csv"), ("Tesla", "build/reales/tesla.csv"), ("AMD", "build/reales/amd.csv"))
FASE_C1 = {0: "fase A", 1: "motor", 2: "candado"}


class UnaVez:
    """Rival de la ronda de Tesla del 18/11 (unavez 100 220, 21 467): parte en caja, al ver p <= 100 compra 63
    (repetido) y, ya adentro, al ver p >= 220 vende 63 (repetido) y no vuelve a entrar."""

    def __init__(self, lo=100, hi=220):
        self.lo, self.hi, self.estado, self.q = lo, hi, 0, market.MANTENER

    def decidir(self, p):
        if self.estado == 0 and p <= self.lo:
            self.estado, self.q = 1, market.COMPRAR_63
        elif self.estado == 1 and p >= self.hi:
            self.estado, self.q = 2, market.VENDER_63
        return self.q

    def fase(self):
        return ("espera", "adentro", "salio")[self.estado]


class ConFase:
    """Envuelve una estrategia y guarda la fase en que quedó después de cada precio."""

    def __init__(self, est, fase):
        self.est, self.fase, self.hist = est, fase, []

    def decidir(self, p):
        b = self.est.decidir(p)
        self.hist.append(self.fase(self.est))
        return b


def correr(precios, estrategia, fase):
    """Devuelve (patrimonio, órdenes, lista de (tick, precio, byte, fase que decidió la orden))."""
    w = ConFase(estrategia, fase)
    decisiones = trader.decisiones(precios, w, 0)
    m = market.Mercado()
    ordenes = []
    for n, (p, d) in enumerate(zip(precios, decisiones)):
        antes = m.ordenes
        m.ejecutar(d, p)
        if m.ordenes > antes:
            ordenes.append((n, p, d, w.hist[n - 1] if n > 0 else "-"))
    return m.w, m.ordenes, ordenes


def reglas(tabla):
    def fase_c1(e):
        return FASE_C1[e.modo] + (" (extremo visto)" if (e.vlo | e.vhi) else "")

    def fase_banda(e):
        return "banda" if (e.vio_lo and e.vio_hi) else "extremo"
    return (("C1", lambda: (C1m.C1(tabla), fase_c1)), ("Banda 40", lambda: (Cotas("espera", banda=40), fase_banda)),
            ("Banda 60", lambda: (Cotas("espera", banda=60), fase_banda)), ("UnaVez 100 220", lambda: (UnaVez(), UnaVez.fase)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-o", "--salida")
    a = ap.parse_args()
    tabla = TB.leer_hex(os.path.join(RAIZ, "sw", "c1_tabla.hex"))
    lineas = []

    def salida(t=""):
        print(t)
        lineas.append(t)

    salida("C1, banda 40, banda 60 y el rival de Tesla en la serie de práctica Meta y en las series de la clase del 18/11")
    salida("Generado por tools/c1/series_reales.py (make c1-series-reales). No editar a mano.")
    res = {}
    for nombre, ruta in SERIES:
        ruta = os.path.join(RAIZ, ruta)
        if not os.path.exists(ruta):
            salida(f"\n{nombre}: sin {os.path.relpath(ruta, RAIZ)} (lo arma tools/reales.sh desde $P4_DATOS): se salta")
            continue
        precios = market.leer_serie(ruta)
        salida(f"\n{nombre} ({len(precios)} ticks, {os.path.relpath(ruta, RAIZ)})")
        for regla, fabrica in reglas(tabla):
            est, fase = fabrica()
            w, n, ordenes = correr(precios, est, fase)
            res[(regla, nombre)] = (w, n, ordenes)
            salida(f"  {regla}: patrimonio {w}, {n} órdenes")
            if regla == "C1":
                for t, p, d, f in ordenes:
                    salida(f"    tick {t}, precio {p}, {'compra' if d >> 6 == 1 else 'venta'} {d & 63} (byte {d:02X}), decidida en {f}")
    fallas = 0
    salida("\nComprobaciones")

    def chequear(ok, texto):
        nonlocal fallas
        salida(("PASS " if ok else "FAIL ") + texto)
        fallas += 0 if ok else 1

    for (regla, serie), esperado, origen in ((("Banda 60", "Tesla"), 18779, "lo que mostró la maestra el 18/11"),
                                             (("Banda 60", "AMD"), 21895, "lo que mostró la maestra el 18/11"),
                                             (("Banda 40", "Meta"), 21392, "docs/decisiones.md, T140"),
                                             (("Banda 40", "Tesla"), 20795, "docs/decisiones.md, T140"),
                                             (("Banda 40", "AMD"), 26470, "docs/decisiones.md, T140"),
                                             (("UnaVez 100 220", "Tesla"), 21467, "el rival de la ronda de Tesla")):
        if (regla, serie) in res:
            chequear(res[(regla, serie)][0] == esperado, f"{regla} en {serie}: {res[(regla, serie)][0]} (esperado {esperado}, {origen})")
    if ("C1", "Meta") in res:
        w, n, o = res[("C1", "Meta")]
        chequear(len(o) >= 2 and o[0][:3] == (8234, 222, 0x56) and o[0][3] == "fase A",
                 f"C1 en Meta: la primera orden es {o[0][:3] if o else None} en {o[0][3] if o else None} (esperado: tick 8234, precio 222, compra de 22 en la fase A)")
        chequear(len(o) >= 2 and o[1][0] == 10966, f"C1 en Meta: la segunda orden va en el tick {o[1][0] if len(o) > 1 else None} (esperado 10966)")
        chequear(w == 22682 and n == 6, f"C1 en Meta: patrimonio final {w} con {n} órdenes (esperado 22682 con 6)")
    salida(f"\n{'PASS' if fallas == 0 else 'FAIL'}: {fallas} comprobaciones falladas")
    if a.salida:
        os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
        with open(a.salida, "w", newline="\n") as f:
            f.write("\n".join(lineas) + "\n")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
