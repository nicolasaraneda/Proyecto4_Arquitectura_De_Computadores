#!/usr/bin/env python3
"""r0_cotas.py: verificación exhaustiva de la regla de cotas de R0 (sw/trade.s) en el gemelo.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El estado de la regla es (q, se vio el mínimo, se vio el máximo). Desde el arranque solo
se alcanzan cinco: (mantener, 0, 0), (comprar, 1, 0), (vender, 0, 1), (comprar, 1, 1) y
(vender, 1, 1). Para cada uno y cada precio de 1 a 255 se arma una serie corta que lleva
al estado y aplica el precio, y se exige que el byte que lee la maestra en el gemelo (el
programa ensamblado corriendo en el Espino base) sea el de ref/trader.py (Oficial).
1275 combinaciones, a los tres períodos de las rondas.

Uso: python3 tools/exhaustivo/r0_cotas.py   Resultado: docs/mediciones/exhaustivo_r0_cotas.txt
"""
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
import trader  # noqa: E402

ESTADOS = {"(mantener, 0, 0)": [], "(comprar, 1, 0)": [100], "(vender, 0, 1)": [255],
           "(comprar, 1, 1)": [255, 100], "(vender, 1, 1)": [100, 255]}


def estado_ref(prefijo):
    o = trader.Oficial()
    for p in prefijo:
        o.decidir(p)
    return (o.q, int(o.vio_lo), int(o.vio_hi))


def main():
    subprocess.run(["make", "-s", "build/gemelo"], cwd=RAIZ, check=True, stdout=subprocess.DEVNULL)
    L = ["Verificacion exhaustiva de la regla de cotas de R0 (sw/trade.s) en el gemelo",
         "Generado por tools/exhaustivo/r0_cotas.py. Cada combinacion (estado, precio) en una serie corta: precios",
         "que se pierden en el reset, el prefijo que lleva al estado, el precio y un precio mas para leer el byte."]
    fallas = 0
    for per in (100000, 1000000, 10000000):
        perd = trader.ticks_perdidos(per)
        series, esperados = [], []
        for nombre, pref in ESTADOS.items():
            for p in range(1, 256):
                s = [150] * perd + pref + [p, 150]
                series.append(s)
                esperados.append(bytes(trader.decisiones(s, trader.Oficial(), perd)))
        ruta = os.path.join(RAIZ, "build", "exhaustivo_r0_cotas.txt")
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        open(ruta, "w").write("".join(" ".join(map(str, s)) + "\n" for s in series))
        out = subprocess.run(["build/gemelo", "--hex", "sw/trade.hex", "--lote", ruta, "--bytes", "--periodo-ns", str(per)],
                             cwd=RAIZ, capture_output=True, text=True, check=True).stdout.splitlines()
        malas = sum(1 for linea, e in zip(out, esperados) if bytes.fromhex(linea.split()[8]) != e)
        malas += abs(len(out) - len(series))
        fallas += malas
        L.append(f"periodo {per} ns (precios perdidos en el reset: {perd}): {len(series)} combinaciones, {malas} distintas a ref/trader.py")
    alc = {n: estado_ref(p) for n, p in ESTADOS.items()}
    L.append("Estados alcanzados por cada prefijo en la referencia (q, minimo, maximo): " +
             ", ".join(f"{n} -> ({q:#04x}, {a}, {b})" for n, (q, a, b) in alc.items()))
    L.append("PASS" if fallas == 0 else f"FAIL: {fallas} combinaciones distintas")
    texto = "\n".join(L) + "\n"
    print(texto, end="")
    open(os.path.join(RAIZ, "docs", "mediciones", "exhaustivo_r0_cotas.txt"), "w").write(texto)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
