#!/usr/bin/env python3
"""registrador.py: guarda como CSV los precios que registra bitstreams/registrador.bin.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El bitstream (rtl/registrador/registrador.v, docs/registrador.md) escucha el SPI de la
maestra y manda por la UART de la Go Board, a 1 Mbaud, un registro de 5 bytes por
transacción:

    b0 = {1, sec[6:0]}     b1 = {0, precio[7:1]}     b2 = {0, miso[7:1]}
    b3 = {0, precio[0], miso[0], err, dt[10:7]}       b4 = {0, dt[6:0]}

Este programa lee el puerto, arma los registros, detecta los perdidos por el salto en
la secuencia y escribe dos archivos:

    PREFIJO_serie.csv     "tick,price", el formato de tb/practica.csv: sirve tal cual para
                          el testbench, el gemelo (build/gemelo --serie) y ref/trader.py
    PREFIJO_detalle.csv   registro, sec, precio, decision leida por la maestra (MISO),
                          err, periodo en us desde la transacción anterior (medido por la
                          FPGA, hasta 10 480 us) y hora de llegada al computador en s
                          (resolución de USB, para períodos largos)
    PREFIJO_crudo.bin     los bytes tal como llegaron, escritos a medida que llegan

y un resumen en la salida: registros, perdidos, transacciones con error, bytes fuera de
un registro, y período mínimo, medio y máximo entre precios.

Uso:
    python3 tools/registrador.py /dev/ttyUSB1 -o build/maestra/ronda3            # hasta Ctrl+C
    python3 tools/registrador.py /dev/ttyUSB1 -o build/maestra/ronda3 --segundos 30
    python3 tools/registrador.py --archivo bytes.bin -o salida      # bytes ya guardados
    python3 tools/registrador.py --prueba                           # sin placa

Solo usa la biblioteca estándar (termios, select). Si dice "Permission denied", el usuario
no tiene permiso sobre el puerto (grupo dialout). Si el puerto no acepta 1 Mbaud, el
bitstream se puede construir para 921 600 baudios (docs/registrador.md) y aquí se usa
--baudios 921600.
"""
import argparse
import os
import pty
import select
import sys
import termios
import threading
import time

VELOCIDADES = {115200: termios.B115200, 921600: termios.B921600, 1000000: termios.B1000000}
UNIDAD_US = 128 * 0.04        # dt en unidades de 128 ciclos de 40 ns


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


def leer_puerto(fd, segundos=None, avisar=True, crudo=None, marcas=None):
    """Lee hasta Ctrl+C o hasta `segundos` sin pausa. Devuelve los bytes.
    Con `crudo` (un archivo abierto) escribe cada trozo apenas llega, para no perder la
    ronda si el programa o el computador se caen a la mitad. Con `marcas` (una lista)
    anota (posición del trozo, segundos desde el comienzo) de cada trozo recibido."""
    datos = bytearray()
    t0 = time.time()
    ultimo_aviso = t0
    try:
        while segundos is None or time.time() - t0 < segundos:
            r, _, _ = select.select([fd], [], [], 0.2)
            if r:
                trozo = os.read(fd, 65536)
                if marcas is not None and trozo:
                    marcas.append((len(datos), time.time() - t0))
                datos += trozo
                if crudo is not None and trozo:
                    crudo.write(trozo)
                    crudo.flush()
            if avisar and time.time() - ultimo_aviso > 2:
                ultimo_aviso = time.time()
                print(f"  {len(datos) // 5} registros recibidos", file=sys.stderr, flush=True)
    except KeyboardInterrupt:
        pass
    return bytes(datos)


def armar(datos, inicios=None):
    """Registros (sec, precio, miso, err, dt) y bytes que no forman parte de un registro.
    Con `inicios` (una lista) anota la posición del primer byte de cada registro."""
    regs, basura, i = [], 0, 0
    while i + 5 <= len(datos):
        b = datos[i:i + 5]
        if not (b[0] & 0x80) or any(x & 0x80 for x in b[1:]):
            basura += 1
            i += 1
            continue
        regs.append((b[0] & 0x7F, ((b[1] & 0x7F) << 1) | ((b[3] >> 6) & 1), ((b[2] & 0x7F) << 1) | ((b[3] >> 5) & 1),
                     (b[3] >> 4) & 1, ((b[3] & 0x0F) << 7) | (b[4] & 0x7F)))
        if inicios is not None:
            inicios.append(i)
        i += 5
    return regs, basura + len(datos) - i


def analizar(regs):
    """Registros perdidos según la secuencia. Un salto a 0 después de otro valor se toma
    como un borrado con SW3 (comienza una ronda nueva) y se informa aparte."""
    perdidos, rondas, saltos = 0, 1, []
    for k in range(1, len(regs)):
        esperado = (regs[k - 1][0] + 1) & 0x7F
        if regs[k][0] != esperado:
            if regs[k][0] == 0 and regs[k][4] == 2047:
                rondas += 1                 # SW3: la secuencia y el período vuelven a cero
            else:
                n = (regs[k][0] - esperado) & 0x7F
                perdidos += n
                saltos.append((k, n))
    return perdidos, rondas, saltos


def tiempos_pc(inicios, marcas):
    """Segundos desde el comienzo de la lectura en que llegó al computador el trozo que
    trae el primer byte de cada registro. La resolución es la de USB (unos ms): sirve
    cuando el período supera los 10,48 ms que mide la FPGA, no para medir 0,1 ms."""
    out, k = [], 0
    for ini in inicios:
        while k + 1 < len(marcas) and marcas[k + 1][0] <= ini:
            k += 1
        out.append(marcas[k][1] if marcas else None)
    return out


def escribir(regs, prefijo, t_pc=None):
    os.makedirs(os.path.dirname(os.path.abspath(prefijo)), exist_ok=True)
    with open(prefijo + "_serie.csv", "w", newline="\n") as f:
        f.write("tick,price\n")
        for t, r in enumerate(regs):
            f.write(f"{t},{r[1]}\n")
    with open(prefijo + "_detalle.csv", "w", newline="\n") as f:
        f.write("registro,sec,precio,decision,err,periodo_us,t_pc_s\n")
        for t, (sec, pre, mis, err, dt) in enumerate(regs):
            per = "" if dt == 2047 else f"{dt * UNIDAD_US:.2f}"
            tp = "" if not t_pc or t_pc[t] is None else f"{t_pc[t]:.3f}"
            f.write(f"{t},{sec},{pre},{mis:02x},{err},{per},{tp}\n")


def resumen(regs, basura, salida=print):
    perdidos, rondas, saltos = analizar(regs)
    errores = sum(r[3] for r in regs)
    dts = [r[4] * UNIDAD_US for r in regs if r[4] != 2047]
    salida(f"Registros: {len(regs)}. Perdidos (saltos de la secuencia): {perdidos}. Rondas (borrados con SW3): {rondas}. "
           f"Transacciones con error: {errores}. Bytes fuera de un registro: {basura}.")
    if dts:
        salida(f"Periodo entre precios: minimo {min(dts):.1f} us, medio {sum(dts) / len(dts):.1f} us, maximo {max(dts):.1f} us "
               f"(cada valor esta redondeado hacia abajo a un multiplo de {UNIDAD_US:.2f} us: el periodo real esta entre ese "
               f"valor y {UNIDAD_US:.2f} us mas; 10 480 us o mas se informa como 10 480).")
    if regs:
        p = [r[1] for r in regs]
        salida(f"Precios: primero {p[0]}, ultimo {p[-1]}, minimo {min(p)}, maximo {max(p)}. "
               f"Decisiones leidas por la maestra distintas de 0x00: {sum(1 for r in regs if r[2] != 0)}.")
    for k, n in saltos[:10]:
        salida(f"  salto en el registro {k}: faltan {n}")
    return perdidos, errores


# --- Prueba sin placa ---------------------------------------------------------------------

def registro(sec, pre, mis=0, err=0, dt=19):
    return bytes([0x80 | (sec & 0x7F), pre >> 1, mis >> 1, ((pre & 1) << 6) | ((mis & 1) << 5) | (err << 4) | (dt >> 7),
                  dt & 0x7F])


def prueba():
    fallas = 0

    def comprobar(ok, texto):
        nonlocal fallas
        print(("PASS " if ok else "FAIL ") + texto)
        fallas += not ok

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    practica = [int(l.split(",")[1]) for l in open(os.path.join(raiz, "tb", "practica.csv")).read().splitlines()[1:]]
    # 1. Los bytes que el testbench recibió por la UART del registrador (caso de la ronda 3)
    ruta = os.path.join(raiz, "build", "registrador", "bytes_r3.bin")
    if os.path.exists(ruta):
        regs, basura = armar(open(ruta, "rb").read())
        perdidos, _, _ = analizar(regs)
        comprobar(len(regs) == 2000 and [r[1] for r in regs] == practica[:2000] and perdidos == 0 and basura == 0,
                  f"bytes del testbench (ronda 3): {len(regs)} registros, precios iguales a tb/practica.csv, "
                  f"{perdidos} perdidos, {basura} bytes sueltos")
        comprobar(all(r[4] == 19 for r in regs[1:]) and regs[0][4] == 2047, "bytes del testbench: periodo de 19 unidades (97,3 us)")
    else:
        print(f"NO CORRIDA: falta {ruta} (tools/registrador.sh, paso 1)")
    # 2. Flujos sintéticos: pérdida, basura al comienzo y un byte cambiado
    serie = practica[:300]
    flujo = b"".join(registro(k, p) for k, p in enumerate(serie))
    regs, basura = armar(b"\x13\x55" + flujo)
    comprobar(len(regs) == 300 and basura == 2, "basura al comienzo: se descartan 2 bytes y quedan 300 registros")
    sin_10 = b"".join(registro(k, p) for k, p in enumerate(serie) if k not in range(100, 110))
    regs, _ = armar(sin_10)
    perdidos, _, saltos = analizar(regs)
    comprobar(perdidos == 10 and len(saltos) == 1, "10 registros que no llegaron: la secuencia los cuenta")
    sin_128 = b"".join(registro(k, p) for k, p in enumerate(serie) if k not in range(50, 178))
    regs, _ = armar(sin_128)
    perdidos, _, _ = analizar(regs)
    comprobar(perdidos == 0, "limite conocido: 128 perdidos seguidos no se ven en la secuencia (modulo 128). Para eso "
                             "esta la cuenta de los 7 segmentos: tiene que coincidir con las filas del CSV")
    roto = bytearray(flujo)
    roto[5 * 40 + 2] |= 0x80                  # un byte con el bit 7 en 1 donde no va
    regs, basura = armar(bytes(roto))
    perdidos, _, _ = analizar(regs)
    comprobar(len(regs) == 299 and perdidos == 1, "un byte dañado: se pierde ese registro y la secuencia lo cuenta")
    dos = b"".join(registro(k, p) for k, p in enumerate(serie[:100])) + \
        b"".join(registro(k, p, dt=2047 if k == 0 else 19) for k, p in enumerate(serie[100:]))
    regs, _ = armar(dos)
    perdidos, rondas, _ = analizar(regs)
    comprobar(perdidos == 0 and rondas == 2, "un borrado con SW3 a mitad: dos rondas, ningun perdido")
    # 3. De punta a punta por un pseudoterminal a 1 Mbaud, con los archivos de salida
    maestro, esclavo = pty.openpty()
    nombre = os.ttyname(esclavo)
    fd = abrir(nombre, 1000000)

    def escribir_lento():
        time.sleep(0.2)
        for k in range(0, len(flujo), 500):
            os.write(maestro, flujo[k:k + 500])
            time.sleep(0.01)
    hilo = threading.Thread(target=escribir_lento)
    hilo.start()
    pref = os.path.join(raiz, "build", "registrador", "prueba_pty")
    os.makedirs(os.path.dirname(pref), exist_ok=True)
    marcas, inicios = [], []
    with open(pref + "_crudo.bin", "wb") as crudo:
        datos = leer_puerto(fd, segundos=1.5, avisar=False, crudo=crudo, marcas=marcas)
    hilo.join()
    os.close(fd)
    regs, basura = armar(datos, inicios)
    t_pc = tiempos_pc(inicios, marcas)
    escribir(regs, pref, t_pc)
    leida = [int(l.split(",")[1]) for l in open(pref + "_serie.csv").read().splitlines()[1:]]
    comprobar(leida == serie, f"pseudoterminal a 1 Mbaud: {len(regs)} registros, la serie escrita en {os.path.relpath(pref, raiz)}_serie.csv "
                              f"es igual a la enviada")
    comprobar(open(pref + "_crudo.bin", "rb").read() == datos, "los bytes crudos quedan en disco a medida que llegan")
    tp = [l.split(",")[6] for l in open(pref + "_detalle.csv").read().splitlines()[1:]]
    comprobar(all(tp) and all(float(a) <= float(b) for a, b in zip(tp, tp[1:])) and 0.1 < float(tp[0]) < 1.0,
              f"hora de llegada al computador en cada registro (primero a {tp[0]} s, ultimo a {tp[-1]} s)")
    print("RESULTADO prueba", "PASS" if fallas == 0 else "FAIL")
    return 0 if fallas == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Guarda como CSV los precios del registrador (docs/registrador.md)")
    ap.add_argument("puerto", nargs="?", help="puerto serie de la Go Board, por ejemplo /dev/ttyUSB1")
    ap.add_argument("-o", "--salida", help="prefijo de los archivos de salida")
    ap.add_argument("--baudios", type=int, default=1000000, choices=sorted(VELOCIDADES))
    ap.add_argument("--segundos", type=float, help="leer este tiempo (sin esto, hasta Ctrl+C)")
    ap.add_argument("--archivo", help="leer los bytes de un archivo en vez del puerto")
    ap.add_argument("--crudo", help="archivo para los bytes recibidos (por defecto PREFIJO_crudo.bin)")
    ap.add_argument("--prueba", action="store_true", help="probar el programa sin placa")
    a = ap.parse_args(argv)
    if a.prueba:
        return prueba()
    if not a.salida or not (a.puerto or a.archivo):
        ap.error("hace falta el puerto (o --archivo) y -o PREFIJO")
    marcas, inicios = [], []
    if a.archivo:
        datos = open(a.archivo, "rb").read()
    else:
        fd = abrir(a.puerto, a.baudios)
        os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
        ruta_crudo = a.crudo or a.salida + "_crudo.bin"
        print(f"Leyendo {a.puerto} a {a.baudios} baudios" + (f" durante {a.segundos} s" if a.segundos else " hasta Ctrl+C") +
              f". Los bytes se guardan a medida que llegan en {ruta_crudo} (si algo se cae, se recupera con "
              f"--archivo {ruta_crudo}).", file=sys.stderr)
        with open(ruta_crudo, "wb") as crudo:
            datos = leer_puerto(fd, a.segundos, crudo=crudo, marcas=marcas)
        os.close(fd)
    regs, basura = armar(datos, inicios)
    escribir(regs, a.salida, tiempos_pc(inicios, marcas) if marcas else None)
    perdidos, _ = resumen(regs, basura)
    print(f"Escrito: {a.salida}_serie.csv y {a.salida}_detalle.csv")
    print(f"Comprobar en la placa: los 7 segmentos deben mostrar {len(regs) & 0xFF:02X} y, con SW4, {len(regs) >> 8 & 0xFF:02X} "
          f"(la cuenta de registros desde el ultimo SW3, si no hubo otro SW3 durante la lectura).")
    return 1 if perdidos else 0


if __name__ == "__main__":
    sys.exit(main())
