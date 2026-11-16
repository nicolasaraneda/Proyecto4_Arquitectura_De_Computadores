#!/usr/bin/env python3
"""medir_uart.py: mide el tiempo de reconfiguración con la UART de la Go Board.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Cada imagen de la prueba de placa (rtl/wb_demo.v) envía un byte por la UART
4096 ciclos después de arrancar: "A" la imagen 0 y "b" la imagen 1. En los
modos de ping-pong cada imagen espera un tiempo fijo desde que arrancó y
salta a la otra, así que el tiempo entre dos bytes seguidos es

    período = espera + tiempo de reconfiguración

con  espera = (2^20 + 3) / 25 MHz = 41,943 ms   (ping-pong rápido, SW3)
     espera = (2^24 + 2) / 25 MHz = 671,089 ms  (ping-pong lento, SW2)

Los 2 o 3 ciclos de más son lo que demora BOOT en subir después de que el
contador llega a la cuenta (medido en simulación, mediciones/demo_sim_*.txt).

Este script abre el puerto serie, anota la hora de llegada de cada byte
durante unos segundos y calcula el período medio como (hora del último byte
menos hora del primero) / (cantidad de bytes menos 1). El conversor USB
entrega los bytes al computador en grupos (hasta 16 ms de atraso por byte),
pero ese error solo afecta a los dos extremos: con 300 bytes es menor que
0,1 ms por período.

Uso (Linux o WSL con el puerto de la placa visible; solo biblioteca estándar):

    python3 scripts/medir_uart.py /dev/ttyUSB1 --modo rapido --segundos 30

En Windows, si está instalado pyserial, sirve el nombre del puerto COM:

    python scripts\\medir_uart.py COM5 --modo rapido --segundos 30

La Go Board aparece como dos puertos: el primero es el de programación y el
segundo la UART. Si con uno no llega nada, se prueba el otro.

Al final imprime una línea RESULTADO que se puede copiar tal cual.
"""
import argparse
import os
import sys
import time

ESPERA_MS = {
    "rapido": (2 ** 20 + 3) / 25e6 * 1e3,
    "lento": (2 ** 24 + 2) / 25e6 * 1e3,
}


def abrir_posix(puerto):
    import termios
    fd = os.open(puerto, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[0] = 0                                                      # iflag: sin traducciones
    a[1] = 0                                                      # oflag
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL           # 8N1
    a[3] = 0                                                      # lflag: modo crudo
    a[4] = termios.B115200
    a[5] = termios.B115200
    a[6][termios.VMIN] = 0
    a[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, a)
    termios.tcflush(fd, termios.TCIFLUSH)

    def leer():
        try:
            return os.read(fd, 4096)
        except BlockingIOError:
            return b""
    return leer


def abrir_pyserial(puerto):
    import serial                      # pyserial, solo si no hay termios
    s = serial.Serial(puerto, 115200, timeout=0)
    s.reset_input_buffer()
    return lambda: s.read(4096)


def analizar(marcas, modo):
    """marcas: lista de (hora en segundos, byte). Devuelve el texto del informe."""
    lineas = []
    validos = [(t, b) for t, b in marcas if b in (0x41, 0x62)]
    otros = len(marcas) - len(validos)
    lineas.append("bytes recibidos: %d (A: %d, b: %d, otros: %d)" % (
        len(marcas), sum(1 for _, b in validos if b == 0x41), sum(1 for _, b in validos if b == 0x62), otros))
    if len(validos) < 3:
        lineas.append("RESULTADO: no hay suficientes bytes. Revisa el puerto y que el interruptor esté apretado.")
        return lineas
    alternan = sum(1 for i in range(1, len(validos)) if validos[i][1] != validos[i - 1][1])
    lineas.append("cambios de imagen: %d de %d intervalos" % (alternan, len(validos) - 1))
    if alternan != len(validos) - 1:
        lineas.append("AVISO: hay bytes repetidos. Una imagen se recargó a sí misma o se perdió un byte.")
    duracion = validos[-1][0] - validos[0][0]
    periodo = duracion / (len(validos) - 1) * 1e3
    error = 16.0 / (len(validos) - 1)
    lineas.append("período medio: %.3f ms (%d intervalos en %.3f s, error por los extremos menor que %.3f ms)" % (
        periodo, len(validos) - 1, duracion, error))
    for desde, hacia, nombre in ((0x41, 0x62, "de A a b (carga la imagen 1)"), (0x62, 0x41, "de b a A (carga la imagen 0)")):
        d = [validos[i][0] - validos[i - 1][0] for i in range(1, len(validos))
             if validos[i - 1][1] == desde and validos[i][1] == hacia]
        if d:
            lineas.append("  %s: media %.2f ms en %d intervalos (cada intervalo suelto tiene hasta 16 ms de error)" % (
                nombre, sum(d) / len(d) * 1e3, len(d)))
    if modo in ESPERA_MS:
        espera = ESPERA_MS[modo]
        lineas.append("espera conocida del modo %s: %.3f ms" % (modo, espera))
        lineas.append("RESULTADO: tiempo de reconfiguración = %.2f ms (modo %s, %d intervalos, error menor que %.2f ms)" % (
            periodo - espera, modo, len(validos) - 1, error))
    else:
        lineas.append("RESULTADO: período medio = %.3f ms (%d intervalos)" % (periodo, len(validos) - 1))
    return lineas


def autoprueba():
    """Comprueba el cálculo con marcas sintéticas: reconfiguración de 53 ms y atraso al azar de hasta 16 ms."""
    import random
    r = random.Random(1)
    for modo in ("rapido", "lento"):
        t, marcas = 0.0, []
        for i in range(301):
            marcas.append((t + r.uniform(0, 0.016), 0x41 if i % 2 == 0 else 0x62))
            t += (ESPERA_MS[modo] + 53.0) / 1e3
        salida = analizar(marcas, modo)
        print("\n".join(salida))
        valor = float(salida[-1].split("=")[1].split("ms")[0])
        if abs(valor - 53.0) > 0.1:
            sys.exit("autoprueba: FALLA, se esperaba 53 ms")
    print("autoprueba: correcta")


def main():
    ap = argparse.ArgumentParser(description="Mide el tiempo de reconfiguración con la UART de la Go Board.")
    ap.add_argument("puerto", nargs="?", help="/dev/ttyUSB1, COM5, ...")
    ap.add_argument("--modo", choices=["rapido", "lento", "ninguno"], default="rapido",
                    help="qué interruptor se mantiene apretado: rapido (SW3) o lento (SW2)")
    ap.add_argument("--segundos", type=float, default=30.0)
    ap.add_argument("--autoprueba", action="store_true", help="prueba el cálculo sin la placa")
    a = ap.parse_args()

    if a.autoprueba:
        autoprueba()
        return
    if not a.puerto:
        ap.error("falta el puerto")

    try:
        leer = abrir_posix(a.puerto)
    except ImportError:
        leer = abrir_pyserial(a.puerto)

    print("Leyendo %s a 115200 baudios durante %.0f s. Mantén apretado el interruptor del modo %s." % (
        a.puerto, a.segundos, a.modo))
    marcas = []
    fin = time.monotonic() + a.segundos
    while time.monotonic() < fin:
        datos = leer()
        ahora = time.monotonic()
        for b in datos:
            marcas.append((ahora, b))
        if not datos:
            time.sleep(0.0005)
    print("\n".join(analizar(marcas, a.modo)))


if __name__ == "__main__":
    main()
