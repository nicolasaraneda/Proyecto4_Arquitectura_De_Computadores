#!/usr/bin/env python3
"""degradacion.py: arma los casos de las pruebas de degradación de R3 (criterio 6 de la puerta).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Elige con la referencia (ref/c1/c1.py) los ticks en que una falla importa y escribe, para cada
caso, el programa con la falla (tools/c1/variante.py) y una línea con los argumentos de
tools/c1/caso.py. Lo corre tools/c1/degradacion.sh.

Series (todas reproducibles desde el repositorio):
  mano    la serie hecha a mano de tools/c1/cosim.py: apuesta en la fase A (media posición) y
          llega al candado en el primer extremo
  motor   una ventana de la serie Meta que pasa cientos de ticks en el motor antes del candado
  baja    la serie hecha a mano con una caída a 90 mientras tiene la media posición: precio bajo
          el mínimo válido

Situaciones en que se cuelga cada hilo (1, 2 y 3, de a uno):
  antes     tick 200: la tabla todavía no está activa
  entrada   el tick siguiente al de la entrada a media posición: la política anterior es una
            orden parcial, que no se repite
  media     con la media posición tomada, en la fase A
  motor     en el motor, con una orden completa vigente y distinta de la banda 40
  candado   50 ticks después del candado. Aquí los hilos 1 y 2 ya no hacen falta: el hilo 3 copia al
            clon sin esperarlos, la política sigue llegando y es la banda 40

Dato viejo: los hilos 1 y 2 atrasados un tick (la política llega después del plazo), en el motor
y con la media posición; dos ticks seguidos atrasados; y un atraso más largo que un período (el
hilo se salta un precio y el hilo 0 termina en modo seguro).

Modo seguro sin hilos colgados: precio bajo el mínimo válido, ronda más larga que la supuesta
(el programa generado con N_RONDA 1500) y la política apagada en la tabla.

Uso: python3 tools/c1/degradacion.py CARPETA [--corta]   (imprime una línea por caso)
"""
import argparse
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [os.path.join(RAIZ, "tools", "c1"), os.path.join(RAIZ, "ref"), os.path.join(RAIZ, "ref", "c1"),
                os.path.join(RAIZ, "ref", "cotas")]
import cosim          # noqa: E402
import variante       # noqa: E402
import c1 as R        # noqa: E402
import tablas as TB   # noqa: E402
import comun          # noqa: E402
import market         # noqa: E402
import series         # noqa: E402

NT = 2600


def hitos(w, T):
    """Ticks (desde 1) de cada situación en la serie w, o None."""
    c = R.C1(T)
    h = dict(entrada=None, media=None, motor=None, candado=None)
    for k, p in enumerate(w, 1):
        b = c.paso(p)
        if h["entrada"] is None and c.modo == R.MODO_A and c.acc == 0 and (b & 0x40) and (b & 63) != 63:
            h["entrada"] = k + 1                # el tick siguiente al de la orden parcial de entrada
        if h["media"] is None and c.modo == R.MODO_A and c.acc > 0 and b == R.M_:
            h["media"] = k + 10
        if h["motor"] is None and c.modo == R.MODO_REC and b != c.q and k > 450:
            h["motor"] = k + 5
        if h["candado"] is None and c.modo == R.MODO_COPIA:
            h["candado"] = k + 50
    return h


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("carpeta")
    ap.add_argument("--corta", action="store_true")
    a = ap.parse_args()
    os.chdir(RAIZ)
    d = a.carpeta
    os.makedirs(d, exist_ok=True)
    T = TB.leer_hex("sw/c1_tabla.hex")
    meta = market.leer_serie("data/practica_meta.csv")
    mano = cosim.serie_fase_a(NT)
    s = {"mano": mano}
    hm = hitos(mano, T)
    # una ventana de la serie Meta con el motor activo un buen rato antes del candado
    motor = hmot = None
    for ini in range(0, len(meta) - NT, 250):
        w = comun.normalizar(meta[ini:ini + NT])
        h = hitos(w, T)
        if h["motor"] and h["candado"] and h["motor"] + 200 < h["candado"] - 50 and h["candado"] < NT - 200:
            motor, hmot = w, h
            break
    if motor is None or None in (hm["entrada"], hm["media"], hm["candado"]):
        raise SystemExit("FAIL: no se encontraron las situaciones en las series")
    s["motor"] = motor
    baja = list(mano)
    for t in range(hm["media"] + 20, hm["media"] + 26):
        baja[t - 1] = 90
    s["baja"] = baja
    for nombre, w in s.items():
        series.escribir_csv(f"{d}/{nombre}.csv", w)

    casos = []      # etiqueta, fallas, serie, argumentos extra de caso.py, descripción

    def cuelga(k, sit, serie, tick):
        casos.append((f"cuelga{k}_{sit}", f"cuelga:{k}:{tick}", serie, ["--banda40-desde", str(tick + 1)],
                      f"hilo {k} colgado en el tick {tick} ({sit}, serie {serie})"))
    for k in (1, 2, 3):
        cuelga(k, "antes", "mano", 200)
        cuelga(k, "entrada", "mano", hm["entrada"])
        cuelga(k, "media", "mano", hm["media"])
        cuelga(k, "motor", "motor", hmot["motor"])
        if k == 3:
            cuelga(k, "candado", "motor", hmot["candado"])
        else:
            # en el candado el hilo 3 copia al clon con lo que publica el hilo 0 y ya no espera a los hilos 1 y 2:
            # la política sigue llegando a tiempo y es la banda 40. No hay plazo vencido ni modo seguro
            tc = hmot["candado"]
            casos.append((f"cuelga{k}_candado", f"cuelga:{k}:{tc}", "motor", ["--banda40-desde", str(tc + 1), "--congelado-desde", str(tc)],
                          f"hilo {k} colgado en el tick {tc} (candado): el hilo 3 ya no lo necesita, la política sigue llegando y es la banda 40"))
    tm, ta = hmot["motor"], hm["media"]
    casos.append(("tarde1_motor", f"atraso:1:{tm}:150", "motor", [], f"hilo 1 atrasado 1200 ciclos en el tick {tm} (motor): dato viejo, se sostiene la orden completa"))
    casos.append(("tarde2_motor", f"atraso:2:{tm}:150", "motor", [], f"hilo 2 atrasado 1200 ciclos en el tick {tm} (motor)"))
    casos.append(("tarde2_media", f"atraso:2:{ta}:150", "mano", [], f"hilo 2 atrasado en el tick {ta} (media posición): mantiene un tick"))
    casos.append(("tarde2_entrada", f"atraso:2:{hm['entrada']}:150", "mano", [],
                  f"hilo 2 atrasado en el tick {hm['entrada']}: la orden parcial anterior no se repite"))
    casos.append(("tarde_dos_seguidos", f"atraso:1:{tm}:150+atraso:2:{tm + 1}:150", "motor", [],
                  f"dos ticks seguidos con el dato atrasado ({tm} y {tm + 1}): se sostiene la política que llegó tarde"))
    casos.append(("salta1_motor", f"atraso:1:{tm}:700", "motor", ["--banda40-desde", str(tm + 1)],
                  f"hilo 1 atrasado 5600 ciclos en el tick {tm}: se salta precios y queda el modo seguro"))
    casos.append(("salta2_media", f"atraso:2:{ta}:700", "mano", ["--banda40-desde", str(ta + 1)],
                  f"hilo 2 atrasado 5600 ciclos en el tick {ta}: modo seguro"))
    # modo seguro sin fallas de hilos
    casos.append(("seguro_precio_bajo", "", "baja", ["--banda40-desde", str(hm["media"] + 20)],
                  f"precio 90 en el tick {hm['media'] + 20}, con la media posición tomada: modo seguro"))
    casos.append(("seguro_ronda_larga", "n_ronda", "motor", ["--programa", "n_ronda=1500", "--banda40-desde", "1501"],
                  "programa generado con N_RONDA 1500 y ronda de 2600 ticks: modo seguro desde el tick 1501"))
    casos.append(("seguro_apagada", "apagada", "motor", ["--banda40-desde", "1"],
                  "política apagada en la tabla: banda 40 desde el primer tick"))
    casos.append(("cuelga3_motor_1ms", f"cuelga:3:{tm}", "motor", ["--banda40-desde", str(tm + 1), "--periodo-ns", "1000000"],
                  f"hilo 3 colgado en el tick {tm}, período de 1 ms"))
    if a.corta:
        casos = [c for c in casos if c[0] in ("cuelga1_motor", "cuelga2_media", "cuelga3_entrada", "cuelga3_candado", "tarde2_motor",
                                              "tarde_dos_seguidos", "salta1_motor", "seguro_precio_bajo", "seguro_apagada")]

    subprocess.run([sys.executable, "tools/c1/generar.py", "--n-ronda", "1500", "-o", f"{d}/n_ronda"], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, "tools/c1/generar.py", "--apagada", "-o", f"{d}/apagada"], check=True, stdout=subprocess.DEVNULL)
    fuente = open("sw/c1.s", encoding="utf-8").read()
    for etq, fallas, serie, extra, desc in casos:
        per = int(extra[extra.index("--periodo-ns") + 1]) if "--periodo-ns" in extra else 100000
        # la primera transacción va después del reset: el programa ve todos los precios y el tick k es el precio k
        args = ["--serie", f"{d}/{serie}.csv", "--nticks", str(NT), "--inicio-ns", "200000"] + extra
        if fallas == "n_ronda":
            args += ["--asm", f"{d}/n_ronda/c1.s"]
        elif fallas == "apagada":
            args += ["--tabla", f"{d}/apagada/c1_tabla.hex"]
        elif fallas:
            f = variante.leer(fallas)
            with open(f"{d}/{etq}.s", "w", encoding="utf-8", newline="\n") as fd:
                fd.write(variante.armar(fuente, f))
            args += ["--asm", f"{d}/{etq}.s"] + ([] if "--congelado-desde" in extra else variante.faltas(f, NT, per))
        print(f"{etq}|{' '.join(args)}|{desc}")


if __name__ == "__main__":
    main()
