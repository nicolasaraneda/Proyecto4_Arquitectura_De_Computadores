#!/usr/bin/env python3
"""Punto de partida del Proyecto 4: mercado exacto del testbench + hallazgos sobre practica.csv.

Uso:  python3 p4_baseline.py tb/practica.csv

Todo en aritmetica entera. `ejecutar` es un porte linea a linea de la tarea
`ejecutar` de tb_proyecto_4.sv. El desfase es el del testbench: el byte que se
ejecuta al precio p[n] fue calculado habiendo visto solo hasta p[n-1].
"""
import statistics as st
import sys

CAJA0, COMISION = 10000, 5
COMPRAR, VENDER = 0x40 | 63, 0x80 | 63   # ordenes idempotentes: "quiero estar adentro" / "quiero estar afuera"


def leer(ruta):
    with open(ruta) as f:
        next(f)
        return [int(l.split(",")[1]) for l in f if l.strip()]


def simular(p, decidir, estado):
    caja, acciones, ordenes, peak, max_dd, dec = CAJA0, 0, 0, CAJA0, 0, 0   # DECISION parte en 0 (mantener)
    w = CAJA0
    for pn in p:
        q, accion = dec & 63, dec >> 6
        if accion == 1:
            q = min(q, (caja - COMISION) // pn)
            if q > 0:
                caja -= q * pn + COMISION; acciones += q; ordenes += 1
        elif accion == 2:
            q = min(q, acciones)
            if q > 0 and caja + q * pn >= COMISION:
                caja += q * pn - COMISION; acciones -= q; ordenes += 1
        w = caja + acciones * pn
        peak = max(peak, w); max_dd = max(max_dd, peak - w)
        dec = decidir(estado, pn)            # se ejecutara al precio siguiente
    return w, ordenes, max_dd


def comprar_y_mantener(p):
    q = (CAJA0 - COMISION) // p[0]
    return CAJA0 - COMISION - q * p[0] + q * p[-1]


def reversion_ema(k=5, entra=4, sale=0):
    """Compra si el precio cae `entra` unidades bajo su media exponencial (alfa = 1/2^k); vende al recuperarla."""
    def decidir(s, pn):
        if "S" not in s:
            s["S"], s["pos"] = pn << k, 0
        dev = (pn << k) - s["S"]             # desviacion escalada por 2^k
        s["S"] += dev >> k
        if dev < -(entra << k): s["pos"] = 1
        elif dev > (sale << k): s["pos"] = 0
        return COMPRAR if s["pos"] else VENDER
    return decidir


def reversion_sma(n=64, entra=4, sale=1):
    """Igual idea sin desplazamientos: suma movil de los ultimos n precios en un buffer circular."""
    def decidir(s, pn):
        if "buf" not in s:
            s["buf"], s["sum"], s["i"], s["pos"] = [pn] * n, pn * n, 0, 0
        dev = n * pn - s["sum"]
        s["sum"] += pn - s["buf"][s["i"]]; s["buf"][s["i"]] = pn; s["i"] = (s["i"] + 1) % n
        if dev < -entra * n: s["pos"] = 1
        elif dev > sale * n: s["pos"] = 0
        return COMPRAR if s["pos"] else VENDER
    return decidir


def tendencia_ema(k=5, entra=4, sale=0):
    """Lo contrario: compra cuando el precio supera a su media (seguir tendencia)."""
    def decidir(s, pn):
        if "S" not in s:
            s["S"], s["pos"] = pn << k, 0
        dev = (pn << k) - s["S"]
        s["S"] += dev >> k
        if dev > (entra << k): s["pos"] = 1
        elif dev < -(sale << k): s["pos"] = 0
        return COMPRAR if s["pos"] else VENDER
    return decidir


def razon_de_varianza(p, k):
    """VR(k) = Var(p[t+k]-p[t]) / (k * Var(p[t+1]-p[t])). 1 = paseo aleatorio, <1 = reversion, >1 = tendencia."""
    d1 = [p[i + 1] - p[i] for i in range(len(p) - 1)]
    dk = [p[i + k] - p[i] for i in range(len(p) - k)]
    return st.pvariance(dk) / (k * st.pvariance(d1))


def main():
    p = leer(sys.argv[1] if len(sys.argv) > 1 else "tb/practica.csv")
    print(f"Serie: {len(p)} ticks, de {p[0]} a {p[-1]}, min {min(p)}, max {max(p)}")
    print("Razon de varianza:", "  ".join(f"VR({k})={razon_de_varianza(p, k):.2f}" for k in (2, 5, 10, 20, 50, 100, 500)))
    bloques = [p[i:i + 2000] for i in range(0, len(p), 2000)]
    bh = [comprar_y_mantener(b) for b in bloques]
    print(f"\n{'estrategia':34s} {'serie completa':>14s} {'ordenes':>8s} {'perdida max':>11s} | bloques de 2000: {'media':>6s} {'peor':>6s} {'>10000':>6s} {'>B&H':>5s}")
    print(f"{'no operar':34s} {CAJA0:14d} {0:8d} {0:11d} | {'':17s} {CAJA0:6d} {CAJA0:6d}")
    print(f"{'comprar y mantener':34s} {comprar_y_mantener(p):14d} {1:8d} {'':11s} | {'':17s} {round(st.mean(bh)):6d} {min(bh):6d} {sum(x > CAJA0 for x in bh):4d}/10")
    for nombre, fab in [("reversion EMA k=5, entra 4, sale 0", lambda: reversion_ema(5, 4, 0)),
                        ("reversion SMA 64, entra 4, sale 1", lambda: reversion_sma(64, 4, 1)),
                        ("tendencia EMA k=5, entra 4, sale 0", lambda: tendencia_ema(5, 4, 0))]:
        w, o, dd = simular(p, fab(), {})
        ws = [simular(b, fab(), {})[0] for b in bloques]
        print(f"{nombre:34s} {w:14d} {o:8d} {dd:11d} | {'':17s} {round(st.mean(ws)):6d} {min(ws):6d} {sum(x > CAJA0 for x in ws):4d}/10 {sum(a > b for a, b in zip(ws, bh)):2d}/10")


if __name__ == "__main__":
    main()
