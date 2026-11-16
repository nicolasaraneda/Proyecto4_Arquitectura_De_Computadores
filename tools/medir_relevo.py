#!/usr/bin/env python3
"""medir_relevo.py: mide en la placa cuánto dura el relevo por warm boot, por la
UART de la Go Board, y lo traduce a ticks perdidos en cada ronda.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Se usa con bitstreams/relevo_r2_multi.bin (docs/autoprueba.md, sección 8).
Las dos imágenes de ese archivo conectan el pin de recepción de la UART con el
de transmisión (eco, sin lógica de por medio). Durante la reconfiguración la
FPGA suelta todos sus pines y el eco se corta. El computador manda bytes sin
pausa y recibe el eco; los bytes que no vuelven son el tiempo que duró la
reconfiguración. A 115 200 baudios cada byte dura 86,8 us (10 bits), así que
la resolución es de unos 0,1 ms, sin depender de cuándo el conversor USB
entrega los bytes al computador: lo que se cuenta es cuáles faltan, no cuándo
llegaron.

Los bytes enviados son una secuencia pseudoaleatoria fija. Cada ventana de 8
bytes aparece una sola vez, así que cualquier tramo recibido se ubica en la
secuencia aunque falten cientos de bytes en medio.

Uso:
  python3 tools/medir_relevo.py /dev/ttyUSB1 [--segundos 20] [--baudios 115200]
      Durante esos segundos hay que apretar SW3 (o SW1 o SW2) una vez. El
      relevo ocurre unos 10 ms después (a 0,1 ms). Al final imprime el hueco
      y la línea RESULTADO.
  python3 tools/medir_relevo.py --traducir 53.0
      Traduce un tiempo de reconfiguración (en ms, medido de cualquier forma:
      cámara, analizador lógico o este script) a ticks perdidos por ronda.
  python3 tools/medir_relevo.py --esperado
      El tiempo esperado según la hoja de datos y lo que significa en ticks.
  python3 tools/medir_relevo.py --prueba
      Prueba el análisis sin placa: huecos conocidos, bytes basura al volver
      el eco y la traducción a ticks con los 53 ms de la hoja de datos (tiene
      que dar los 536, 58 y 10 ticks de docs/mediciones/vigilante/relevo.txt).

Solo usa la biblioteca estándar (termios, select, threading).
"""
import argparse
import os
import random
import select
import sys
import termios
import threading
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, os.path.join(RAIZ, "tools", "vigilante"))

VENTANA = 8                  # bytes para ubicar un tramo recibido en la secuencia
SEMILLA = 2026
BITS_POR_BYTE = 10           # 8N1: inicio, 8 datos y parada
T_CONFIG_MS = 53.0           # hoja de datos DS1040, tCONFIG típico de la HX1K, oscilador en frecuencia baja
POR_CICLOS = 4095            # reset de encendido de pochoco_soc
PERIODOS_NS = {"ronda 1 (10 ms)": 10_000_000, "ronda 2 (1 ms)": 1_000_000, "ronda 3 (0,1 ms)": 100_000}
VELOCIDADES = {9600: termios.B9600, 19200: termios.B19200, 38400: termios.B38400, 57600: termios.B57600,
               115200: termios.B115200, 230400: termios.B230400}


def secuencia(n):
    return random.Random(SEMILLA).randbytes(n)


# --- Análisis ---------------------------------------------------------------------------
def tramos(enviado, recibido):
    """Ubica lo recibido en lo enviado. Devuelve una lista de (inicio_enviado,
    inicio_recibido, largo) de tramos que coinciden byte a byte, en orden."""
    indice, repetidas = {}, set()
    for j in range(len(enviado) - VENTANA + 1):
        w = enviado[j:j + VENTANA]
        if w in indice:
            repetidas.add(w)
        else:
            indice[w] = j
    salida = []
    i = 0
    while i <= len(recibido) - VENTANA:
        w = recibido[i:i + VENTANA]
        j = indice.get(w) if w not in repetidas else None
        if j is None:
            i += 1
            continue
        largo = VENTANA
        while i + largo < len(recibido) and j + largo < len(enviado) and recibido[i + largo] == enviado[j + largo]:
            largo += 1
        if not salida or j >= salida[-1][0] + salida[-1][2]:
            salida.append((j, i, largo))
        i += largo
    return salida


def huecos(enviado, recibido):
    """Huecos entre tramos: lista de (bytes enviados que no volvieron, bytes
    recibidos que no calzan, posición en lo enviado, posición en lo recibido)."""
    t = tramos(enviado, recibido)
    salida = []
    for (j0, i0, n0), (j1, i1, _n1) in zip(t, t[1:]):
        perdidos = j1 - (j0 + n0)
        basura = i1 - (i0 + n0)
        if perdidos > 0 or basura > 0:
            salida.append((perdidos, basura, j0 + n0, i0 + n0))
    return t, salida


# --- Traducción a ticks ---------------------------------------------------------------------
def ticks_perdidos(t_reconf_ms, periodo_ns, falla=100):
    """Ticks sin decisión nueva en un relevo, con el modelo de tools/vigilante/relevo_ref.py
    (la maestra del testbench oficial, la serie de práctica y la falla en el tick 100).
    Devuelve (ticks sin decisión nueva, ticks leyendo 0xFF)."""
    import market
    import relevo_ref
    precios = market.leer_serie(os.path.join(RAIZ, "tb/practica.csv"))
    n = min(len(precios), falla + 10 + int(3 * (t_reconf_ms * 1e6 + 1e6) / periodo_ns))
    e = relevo_ref.Esperado(precios[:n], periodo_ns, 4000, falla, 4, int(round(t_reconf_ms * 1e6)))
    return e.n1 - e.nf, e.clase.count("suelto")


def traducir(t_ms, salida=print):
    salida(f"Tiempo de reconfiguracion: {t_ms:.2f} ms. Se le suman el reset de la imagen 1 "
           f"({POR_CICLOS} ciclos = {POR_CICLOS * 40 / 1e6:.3f} ms) y los 5 precios que cuenta el vigilante.")
    for nombre, per in PERIODOS_NS.items():
        sin, ff = ticks_perdidos(t_ms, per)
        salida(f"  {nombre}: {sin} ticks sin decision nueva desde el precio colgado "
               f"({ff} leyendo 0xFF, que es mantener)")


def esperado():
    bits = 32220 * 8
    print("Tiempo esperado del relevo por warm boot (Go Board, iCE40 HX1K). Generado por "
          "tools/medir_relevo.py --esperado (make relevo-placa).")
    print()
    print(f"- Hoja de datos DS1040, tCONFIG de la HX1K desde la flash: {T_CONFIG_MS:.0f} ms tipico con el oscilador de")
    print("  configuracion en frecuencia baja, que es lo que escribe icepack (tools/ver_multi.py lo lee en los")
    print("  vectores de arranque). No da maximo. Se supone que un warm boot demora lo mismo.")
    print(f"- Cota inferior: leer el bitstream ({bits} bits) a 7,5 MHz toma {bits / 7.5e3:.1f} ms, mas 0,8 ms de")
    print("  borrado de la memoria de configuracion.")
    print(f"- Despues, la imagen R0 pasa {POR_CICLOS} ciclos en reset: {POR_CICLOS * 40 / 1e6:.3f} ms.")
    print("- Antes, el vigilante espera el quinto precio sin respuesta y el fin de esa transaccion.")
    print()
    print("Lo que miden la camara (7 segmentos apagados), el eco de la UART y el pin de MISO del PMOD es")
    print("el tiempo en que los pines quedan sueltos: desde que BOOT sube hasta que la imagen 1 arranca. Es el")
    print("T_RECONF de tools/vigilante/relevo.sh. El reset de R0 y los 5 precios se suman al traducir.")
    print()
    for t in (bits / 7.5e3 + 0.8, T_CONFIG_MS, 2 * T_CONFIG_MS):
        traducir(round(t, 2))
        print()
    print("En bitstreams/relevo_r2_multi.bin el supervisor se cuelga con el precio 100 y BOOT sube al")
    print("terminar la transaccion 103 (la placa no pierde precios): 10,3 ms despues de apretar SW3,")
    print("103 ms con SW2 y 1,03 s con SW1 (docs/mediciones/autoprueba_r2.txt).")
    print()
    return 0


# --- Puerto serie ---------------------------------------------------------------------------
def abrir(puerto, baudios):
    fd = os.open(puerto, os.O_RDWR | os.O_NOCTTY)
    a = termios.tcgetattr(fd)
    a[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK | termios.ISTRIP | termios.INLCR |
              termios.IGNCR | termios.ICRNL | termios.IXON | termios.IXOFF | termios.IXANY)
    a[1] &= ~termios.OPOST
    a[2] &= ~(termios.CSIZE | termios.PARENB | termios.CSTOPB | getattr(termios, "CRTSCTS", 0))
    a[2] |= termios.CS8 | termios.CREAD | termios.CLOCAL
    a[3] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON | termios.ISIG | termios.IEXTEN)
    a[4] = a[5] = VELOCIDADES[baudios]
    a[6][termios.VMIN] = 0
    a[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, a)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


def medir(puerto, baudios, segundos):
    n = baudios // BITS_POR_BYTE * segundos
    enviado = secuencia(n)
    fd = abrir(puerto, baudios)
    recibido = bytearray()
    llegadas = []                 # (hora, cuántos bytes había recibido hasta ahí)
    tiempos = {}
    fin = threading.Event()

    def escribir():
        tiempos["inicio"] = time.monotonic()
        k = 0
        while k < n:
            k += os.write(fd, enviado[k:k + 256])
        termios.tcdrain(fd)
        tiempos["fin"] = time.monotonic()
        fin.set()

    hilo = threading.Thread(target=escribir, daemon=True)
    print(f"Mandando {n} bytes a {baudios} baudios durante unos {segundos} s. Apriete SW3 una vez ahora.",
          flush=True)
    hilo.start()
    ultimo = time.monotonic()
    while True:
        r, _, _ = select.select([fd], [], [], 0.05)
        ahora = time.monotonic()
        if r:
            datos = os.read(fd, 4096)
            if datos:
                recibido += datos
                llegadas.append((ahora, len(recibido)))
                ultimo = ahora
        if fin.is_set() and ahora - ultimo > 0.5:
            break
    os.close(fd)
    return enviado, bytes(recibido), llegadas, tiempos


def informar(enviado, recibido, baudios, llegadas=None, tiempos=None, salida=print):
    t_byte_ms = BITS_POR_BYTE * 1000 / baudios
    t, hs = huecos(enviado, recibido)
    salida(f"Enviados {len(enviado)} bytes, recibidos {len(recibido)}, en {len(t)} tramos que calzan.")
    if tiempos:
        dur = tiempos["fin"] - tiempos["inicio"]
        nominal = len(enviado) * t_byte_ms / 1000
        salida(f"Envio: {dur:.3f} s contra {nominal:.3f} s sin pausas ({100 * nominal / dur:.1f} %). "
               "Bajo 99 % el conversor dejo pausas y el hueco medido seria un minimo.")
    if not t:
        salida("RESULTADO: no volvio ningun eco. Revise el puerto (el segundo de la Go Board) y que la placa "
               "tenga programado relevo_r2_multi.bin")
        return None
    if t[0][0] > 0:
        salida(f"Los primeros {t[0][0]} bytes enviados no volvieron (normal si la placa partio despues).")
    grandes = [h for h in hs if h[0] > 3]
    for perdidos, basura, pos, _ in hs:
        salida(f"  hueco despues del byte {pos}: {perdidos} bytes sin eco ({perdidos * t_byte_ms:.2f} ms), "
               f"{basura} bytes recibidos que no calzan")
    if len(grandes) != 1:
        salida(f"RESULTADO: se esperaba un hueco grande y hay {len(grandes)}. Repita la medicion apretando el "
               "boton una sola vez, o revise el cable.")
        return None
    perdidos, basura, pos, pos_rx = grandes[0]
    # Un byte cortado por el comienzo o por el final de la reconfiguración se
    # pierde entero: el tiempo sin eco está entre (perdidos - 2) y perdidos bytes.
    lo, hi = max(0, perdidos - 2) * t_byte_ms, perdidos * t_byte_ms
    if llegadas:
        # Primer bloque que trae el último byte antes del hueco y primero que
        # trae un byte posterior al hueco
        antes = next(h for h, cuenta in llegadas if cuenta >= pos_rx)
        despues = next(h for h, cuenta in llegadas if cuenta > pos_rx + basura)
        salida(f"Con la hora de llegada al computador (gruesa, por el conversor USB): "
               f"{1000 * (despues - antes):.1f} ms entre el ultimo eco antes del hueco y el primero despues")
    salida(f"RESULTADO: tiempo de reconfiguracion = {(lo + hi) / 2:.2f} ms (entre {lo:.2f} y {hi:.2f} ms)")
    traducir((lo + hi) / 2, salida)
    return (lo + hi) / 2


# --- Prueba sin placa --------------------------------------------------------------------------
def prueba():
    fallas = 0

    def comprobar(ok, texto):
        nonlocal fallas
        fallas += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + texto)

    baudios = 115200
    t_byte = BITS_POR_BYTE * 1000 / baudios
    enviado = secuencia(baudios // BITS_POR_BYTE * 5)
    rnd = random.Random(7)
    for perdidos, basura, corte in [(611, 0, 20000), (611, 3, 31000), (150, 5, 100), (1500, 2, 40000), (288, 1, 57000)]:
        recibido = enviado[:corte] + rnd.randbytes(basura) + enviado[corte + perdidos:]
        _, hs = huecos(enviado, recibido)
        grandes = [h for h in hs if h[0] > 3]
        comprobar(len(grandes) == 1 and grandes[0][0] >= perdidos and grandes[0][0] <= perdidos + basura
                  and grandes[0][2] <= corte,
                  f"hueco de {perdidos} bytes ({perdidos * t_byte:.2f} ms) con {basura} bytes basura al volver: "
                  f"el analisis encuentra {grandes[0][0] if grandes else '-'} bytes")
    # El eco empieza tarde y hay un byte basura suelto antes del hueco
    recibido = enviado[300:20000] + b"\x00" + enviado[20001:20500] + enviado[21100:]
    _, hs = huecos(enviado, recibido)
    grandes = [h for h in hs if h[0] > 3]
    comprobar(len(grandes) == 1 and grandes[0][0] == 600, "comienzo tardio y un byte cambiado: un solo hueco de 600 bytes")
    lineas = []
    t = informar(enviado, enviado[:30000] + enviado[30611:], baudios, salida=lineas.append)
    comprobar(t is not None and abs(t - 610 * t_byte) < 0.01,
              f"informe con un hueco de 611 bytes: {t:.2f} ms (611 bytes son {611 * t_byte:.2f} ms)")
    # Traducción con los 53 ms de la hoja de datos: lo mismo que la simulación
    # del relevo (docs/mediciones/vigilante/relevo.txt)
    esperado = {"ronda 1 (10 ms)": 10, "ronda 2 (1 ms)": 58, "ronda 3 (0,1 ms)": 536}
    for nombre, per in PERIODOS_NS.items():
        sin, ff = ticks_perdidos(53.0, per)
        comprobar(sin == esperado[nombre], f"53 ms en la {nombre}: {sin} ticks sin decision nueva, {ff} con 0xFF "
                                           f"(la simulacion del relevo da {esperado[nombre]})")
    print("RESULTADO prueba", "PASS" if fallas == 0 else "FAIL")
    return 0 if fallas == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tiempo del relevo por warm boot, medido por el eco de la UART")
    ap.add_argument("puerto", nargs="?", help="puerto serie de la Go Board, por ejemplo /dev/ttyUSB1")
    ap.add_argument("--baudios", type=int, default=115200, choices=sorted(VELOCIDADES))
    ap.add_argument("--segundos", type=int, default=20)
    ap.add_argument("--traducir", type=float, metavar="MS", help="solo traducir un tiempo de reconfiguracion a ticks")
    ap.add_argument("--prueba", action="store_true", help="probar el analisis sin placa")
    ap.add_argument("--esperado", action="store_true", help="tiempo esperado segun la hoja de datos")
    a = ap.parse_args(argv)
    if a.prueba:
        return prueba()
    if a.esperado:
        return esperado()
    if a.traducir is not None:
        traducir(a.traducir)
        return 0
    if not a.puerto:
        ap.error("falta el puerto (o --prueba, o --traducir)")
    enviado, recibido, llegadas, tiempos = medir(a.puerto, a.baudios, a.segundos)
    return 0 if informar(enviado, recibido, a.baudios, llegadas, tiempos) is not None else 1


if __name__ == "__main__":
    sys.exit(main())
