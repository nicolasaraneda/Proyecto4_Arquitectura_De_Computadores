#!/usr/bin/env python3
"""
sclk_minimo.py: SCLK mínimo con que el fondo en un chip responde a tiempo en la
ronda 3, y período mínimo con SCLK de 1 MHz (exploración, con el gemelo).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

La transacción ocupa el período junto con la respuesta. Con SCLK lento la
transacción se alarga y el presupuesto (período menos transacción) se achica.
Este barrido usa la forma de la matriz de estrés (CS_SETUP = max(1500, 3 medio
período), CS_HOLD = 500) y, para cada programa, el peor caso de respuesta con
los 2000 primeros ticks de la práctica. Un caso pasa si los bytes son los de la
referencia, todos los precios tienen respuesta y el peor caso cabe en el
presupuesto.

Uso: python3 tools/fondo/sclk_minimo.py   (o make fondo-sclk-minimo)
Resultado en docs/mediciones/fondo/sclk_minimo.txt.
"""
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, os.path.join(RAIZ, "tools"))

import estres    # noqa: E402
import market    # noqa: E402

PROGRAMAS = [("R0, sw/trade.s en el core base", "sw/trade.hex", "", "trader"),
             ("R1, sw/fondo.s en el barrel", "build/fondo/fondo.hex", "--barrel --xd 3", "fondo")]


def caso(nombre, precios, **kw):
    return estres.base(nombre, precios, **kw)


def main():
    os.chdir(RAIZ)
    if not os.path.exists("build/gemelo") or os.path.getmtime("build/gemelo") < os.path.getmtime("ref/gemelo/gemelo.c"):
        subprocess.run(["cc", "-O2", "-o", "build/gemelo", "ref/gemelo/gemelo.c"], check=True)
    subprocess.run([sys.executable, "tools/pochoasm.py", "sw/fondo.s", "-o", "build/fondo/fondo.hex"],
                   check=True, capture_output=True)
    d = "build/estres/sclk_minimo"
    os.makedirs(d, exist_ok=True)
    p = market.leer_serie("tb/practica.csv")[:2000]
    lineas = ["SCLK minimo a 0,1 ms y periodo minimo a 1 MHz, con el gemelo (exploracion)",
              "Generado por tools/fondo/sclk_minimo.py. No editar a mano.", ""]
    for titulo, hexfile, opts, ref in PROGRAMAS:
        lineas.append(f"{titulo}:")
        # SCLK a 0,1 ms, de 100 kHz a 200 kHz
        primero = None
        for khz in range(100, 205, 5):
            medio = round(500000 / khz)
            c = caso(f"sclk_{khz}k", p, SCLK_MEDIO_NS=medio, CS_SETUP_NS=max(1500, 3 * medio))
            nombre, ok, det, peor, _ = estres.correr((None, d, c, ref, ("gemelo", hexfile, opts)))
            if ok and primero is None:
                primero = (khz, det)
            lineas.append(f"  {'pasa   ' if ok else 'no pasa'} SCLK {khz:3d} kHz (medio periodo {medio} ns): {det}")
        lineas.append(f"  SCLK minimo con que responde a tiempo a 0,1 ms: {primero[0] if primero else 'ninguno'} kHz")
        # Período mínimo a 1 MHz, en pasos de 40 ns (un ciclo de presupuesto)
        minimo = None
        for per in range(9500 + 40 * 20, 100000, 40):
            c = caso(f"periodo_{per}", p, PERIODO_NS=per)
            nombre, ok, det, peor, _ = estres.correr((None, d, c, ref, ("gemelo", hexfile, opts)))
            if ok:
                minimo = (per, det)
                break
        if minimo:
            lineas.append(f"  Periodo minimo con SCLK de 1 MHz: {minimo[0]} ns, {100000 / minimo[0]:.2f} veces mas rapido "
                          f"que la ronda 3: {minimo[1]}")
        lineas.append("")
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    with open("docs/mediciones/fondo/sclk_minimo.txt", "w") as f:
        f.write(texto)


if __name__ == "__main__":
    main()
