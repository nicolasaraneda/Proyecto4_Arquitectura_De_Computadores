#!/usr/bin/env python3
"""desfase.py: desfase de un tick, primer tick y último tick, contra el testbench oficial.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Corre tb/tb_proyecto_4.sv sin modificar, con el RTL del repositorio y
sw/trade.hex (Icarus, 2000 ticks, cerca de un minuto y medio), y compara su
decisiones.csv byte a byte con:

  arnes    build/retorno correr --estrategia base --nticks 2000 --perdidos 2
  propia   la regla base escrita aquí desde su descripción (media exponencial
           con alfa 1/32, entra 4 bajo la media, sale al recuperarla), con un
           lazo propio y la contabilidad propia de contabilidad.py.

El testbench se corre desde un directorio espejo (build/auditoria/tb_oficial,
con enlaces a sw/ y tb/) para que su decisiones.csv no caiga en la raíz del
repositorio. El archivo del testbench es el mismo: se le pasa a iverilog por
su ruta.

Además muestra, con el archivo del testbench solo, a qué precio se ejecutó la
primera orden: tiene que ser el del tick siguiente al que produjo la señal.

    python3 auditoria/desfase.py            (desde factibilidad/retorno)
"""
import glob
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
RAIZ = os.path.dirname(os.path.dirname(RETORNO))
BUILD = os.path.join(RETORNO, "build", "auditoria")
ARNES = os.path.join(RETORNO, "build", "retorno")

sys.path.insert(0, AQUI)
from contabilidad import Propia        # noqa: E402

ENCABEZADO = "tick,precio,decision,caja,acciones,patrimonio"
ADENTRO, AFUERA = 0x7F, 0xBF            # comprar 63 y vender 63: posición objetivo


def leer_precios(ruta, n=None):
    with open(ruta) as f:
        next(f)
        p = [int(x.split(",")[1]) for x in f if x.strip()]
    return p if n is None else p[:n]


def regla_base(precios, perdidos=0, k=5, entra=4, sale=0):
    """Bytes que la maestra lee en cada tick, con la regla base.

    La maestra lee en el tick t lo que el programa dejó escrito después de ver
    el precio t-1. En el tick 0 lee el valor de reset de DECISION, que es 0.
    Los primeros `perdidos` precios no los ve el programa (reset de la placa).
    """
    leidos, escrito, media, dentro = [], 0x00, None, False
    for t, p in enumerate(precios):
        leidos.append(escrito)
        if t < perdidos:
            continue
        if media is None:
            media = p << k                       # la media parte en el primer precio visto
        desvio = (p << k) - media                # contra la media de antes de este precio
        media += desvio >> k
        if dentro and desvio > (sale << k):
            dentro = False
        elif not dentro and desvio < -(entra << k):
            dentro = True
        escrito = ADENTRO if dentro else AFUERA
    return leidos


def contabilizar(precios, leidos, caja0=10000, comision=5):
    c, filas = Propia(caja0, comision), []
    for t, (p, b) in enumerate(zip(precios, leidos)):
        caja, acc, w, _, _ = c.tick(b, p)
        filas.append("%d,%d,%02x,%d,%d,%d" % (t, p, b, caja, acc, w))
    return c, ENCABEZADO + "\n" + "\n".join(filas) + "\n"


def comprar_y_mantener(precios, caja0=10000, comision=5):
    q = (caja0 - comision) // precios[0]
    return caja0 - comision - q * precios[0] + q * precios[-1]


def correr_testbench():
    espejo = os.path.join(BUILD, "tb_oficial")
    os.makedirs(espejo, exist_ok=True)
    for d in ("sw", "tb"):
        enlace = os.path.join(espejo, d)
        if not os.path.islink(enlace):
            os.symlink(os.path.join(RAIZ, d), enlace)
    datdir = subprocess.run(["yosys-config", "--datdir"], capture_output=True, text=True, check=True).stdout.strip()
    fuentes = sorted(glob.glob(os.path.join(RAIZ, "rtl", "*.v"))) + sorted(glob.glob(os.path.join(RAIZ, "rtl", "espino_core", "*.v")))
    binario = os.path.join(BUILD, "tb_p4.vvp")
    subprocess.run(["iverilog", "-g2012", "-s", "tb_proyecto_4", "-o", binario, os.path.join(datdir, "ice40", "cells_sim.v")]
                   + fuentes + [os.path.join(RAIZ, "tb", "tb_proyecto_4.sv")], check=True, cwd=RAIZ)
    r = subprocess.run(["vvp", "-n", binario], capture_output=True, text=True, check=True, cwd=espejo)
    return os.path.join(espejo, "decisiones.csv"), r.stdout


def main():
    os.makedirs(BUILD, exist_ok=True)
    serie = os.path.join(RAIZ, "tb", "practica.csv")
    precios = leer_precios(serie, 2000)
    mal = 0

    print("Desfase, primer tick y ultimo tick contra el testbench oficial sin modificar")
    ruta_tb, salida = correr_testbench()
    for linea in salida.splitlines():
        if any(x in linea for x in ("Patrimonio final", "Ordenes ejecutadas", "Comprar y mantener", "Testbenchs aprobados")):
            print("  testbench: " + " ".join(linea.split()))
    with open(ruta_tb) as f:
        texto_tb = f.read()
    filas_tb = [x.split(",") for x in texto_tb.strip().split("\n")[1:]]

    ruta_arnes = os.path.join(BUILD, "decisiones_arnes.csv")
    subprocess.run([ARNES, "correr", "--estrategia", "base", "--serie", serie, "--nticks", "2000", "--perdidos", "2",
                    "-o", ruta_arnes], check=True, capture_output=True)
    with open(ruta_arnes) as f:
        texto_arnes = f.read()
    cuenta, texto_propio = contabilizar(precios, regla_base(precios, perdidos=2))

    for nombre, texto in (("arnes (correr, 2 precios perdidos)", texto_arnes), ("regla y lazo propios", texto_propio)):
        igual = texto == texto_tb
        print(f"{'PASS' if igual else 'FAIL'}  decisiones.csv del testbench contra {nombre}: {len(filas_tb)} filas, "
              f"{'identicos byte a byte' if igual else 'DISTINTOS'}")
        mal += not igual

    # Primer tick: la maestra lee el valor de reset
    print(f"Primer tick: el testbench lee el byte {filas_tb[0][2]} (reset de DECISION) y no ejecuta nada: caja {filas_tb[0][3]}.")
    mal += filas_tb[0][2] != "00"
    # Primera orden: precio al que se ejecutó, sacado solo del archivo del testbench
    for t in range(1, len(filas_tb)):
        if int(filas_tb[t][4]) > int(filas_tb[t - 1][4]):
            q = int(filas_tb[t][4]) - int(filas_tb[t - 1][4])
            pagado = int(filas_tb[t - 1][3]) - int(filas_tb[t][3]) - 5
            # tick en que la regla propia decide entrar: el primero en que el byte escrito pasa a 7f
            leidos = regla_base(precios, perdidos=2)
            senal = next(i for i in range(len(leidos)) if leidos[i] == ADENTRO) - 1
            print(f"Primera orden del testbench: fila {t}, {q} acciones, pago {pagado} = {q} x {pagado // q} "
                  f"(resto {pagado % q}). Precio del tick {t}: {precios[t]}. "
                  f"La senal salio con el precio del tick {senal} ({precios[senal]}).")
            ok = pagado == q * precios[t] and senal == t - 1 and precios[senal] != precios[t]
            print(f"{'PASS' if ok else 'FAIL'}  la orden se ejecuta al precio del tick siguiente al que la produjo, no al que la produjo")
            mal += not ok
            break
    # Último tick: el patrimonio final usa el precio del último tick, y la decisión tomada con él no se ejecuta
    w_tb = int(filas_tb[-1][5])
    print(f"Ultimo tick: patrimonio final del testbench {w_tb}, propio {cuenta.w}, ordenes propias {cuenta.ordenes}. "
          f"La decision tomada con el ultimo precio no se ejecuta.")
    mal += w_tb != cuenta.w

    # Serie completa viendo todos los precios (así se informa en el estudio)
    todos = leer_precios(serie)
    cuenta, _ = contabilizar(todos, regla_base(todos))
    print(f"Regla y lazo propios, serie completa sin precios perdidos: patrimonio {cuenta.w}, ordenes {cuenta.ordenes}, "
          f"comprar y mantener {comprar_y_mantener(todos)}.")
    print("PASS" if not mal else "FAIL")
    return 1 if mal else 0


if __name__ == "__main__":
    sys.exit(main())
