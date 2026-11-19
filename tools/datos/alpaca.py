#!/usr/bin/env python3
"""alpaca.py: descarga barras de 1 minuto de Alpaca para evaluar reglas (no entran al diseño).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Necesita una cuenta gratuita de Alpaca (solo papel, sin depositar dinero) y su clave de
API (docs/pendientes_nicolas.md, acción 3b). La clave se toma de las variables de entorno
APCA_API_KEY_ID y APCA_API_SECRET_KEY y, si no están, del archivo ~/.alpaca.env (líneas
"APCA_API_KEY_ID=..." y "APCA_API_SECRET_KEY=...", con o sin "export" y comillas), o del
archivo que se pase con --claves. La clave nunca se imprime ni se escribe en ningún archivo.
El plan gratuito entrega el histórico consolidado (feed SIP) mientras no se pidan los
últimos 15 minutos.

Escribe, en la carpeta de salida:
  crudo/TICKER.csv  todas las barras que entrega Alpaca, también fuera de la sesión
                    regular: "t,o,h,l,c,v" con t en hora de Nueva York (ISO con desfase).
  TICKER.csv        una fila por minuto de la sesión regular (9:30 a 15:59, Nueva York):
                    "fecha,minuto,precio", con el cierre del minuto (ajustado por splits);
                    los minutos sin operaciones repiten el último precio.

La carpeta de salida es la variable de entorno P4_DATOS (más /minuto) o, si no está,
data/externos/minuto, que está fuera del repositorio (.gitignore). Los datos solo se
usan para evaluar reglas: no entran al diseño ni al repositorio.

Con --gzip las barras crudas quedan en crudo/TICKER.csv.gz. Con --procesos N baja N empresas a
la vez, con un tope común de llamadas por minuto (--tope, 190 por omisión, bajo el límite de
200 de la cuenta). Una empresa con TICKER.csv ya escrito se salta (para retomar una descarga
cortada), salvo con --rehacer. Al terminar cada empresa avisa los saltos entre días mayores
que --salto (25 % por omisión), que pueden ser una escisión o un error del dato.

Uso:
    python3 tools/datos/alpaca.py                       # META AAPL NFLX AMD TSLA, 2022 a 2024
    python3 tools/datos/alpaca.py --lista tools/datos/otras_acciones.txt --desde 2020-01-01 \
        --hasta 2024-12-31 --salida $P4_DATOS/otras --procesos 4 --gzip
    python3 tools/datos/alpaca.py --tickers AAPL --desde 2023-01-01 --hasta 2023-03-31
    python3 tools/datos/alpaca.py --solo-sesion         # rehace TICKER.csv desde crudo/, sin red
Solo usa la biblioteca estándar.
"""
import argparse
import datetime as dt
import gzip
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
URL = "https://data.alpaca.markets/v2/stocks/bars"
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOMBRES = ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY")


def leer_claves(ruta):
    """Clave y secreto desde el entorno o desde un archivo KEY=VALUE. No imprime nada de ellos."""
    vals = {k: os.environ.get(k) for k in NOMBRES}
    if all(vals.values()):
        return vals[NOMBRES[0]], vals[NOMBRES[1]]
    ruta = os.path.expanduser(ruta)
    if not os.path.exists(ruta):
        raise SystemExit(f"faltan {NOMBRES[0]} y {NOMBRES[1]}: ni en el entorno ni en {ruta}")
    with open(ruta) as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            if linea.startswith("export "):
                linea = linea[len("export "):].strip()
            k, v = linea.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k in NOMBRES and v and not vals.get(k):
                vals[k] = v
    if not all(vals.values()):
        falta = [k for k in NOMBRES if not vals.get(k)]
        raise SystemExit(f"{ruta} no trae {', '.join(falta)}")
    return vals[NOMBRES[0]], vals[NOMBRES[1]]


class Tope:
    """Tope común de llamadas por minuto entre hilos (ventana deslizante de 60 s)."""

    def __init__(self, por_minuto):
        self.n, self.t, self.lock = por_minuto, [], threading.Lock()

    def esperar(self):
        while True:
            with self.lock:
                ahora = time.monotonic()
                self.t = [x for x in self.t if ahora - x < 60.0]
                if len(self.t) < self.n:
                    self.t.append(ahora)
                    return
                espera = 60.0 - (ahora - self.t[0]) + 0.05
            time.sleep(espera)


TOPE = Tope(190)


def pedir(params, clave, secreto):
    TOPE.esperar()
    url = URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"APCA-API-KEY-ID": clave, "APCA-API-SECRET-KEY": secreto,
                                               "Accept": "application/json"})
    for intento in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:    # límite de llamadas por minuto o falla del servidor
                time.sleep(15 * (intento + 1))
                continue
            raise SystemExit(f"Alpaca respondió {e.code}: {e.read()[:300]!r}")
        except urllib.error.URLError:
            time.sleep(15 * (intento + 1))
    raise SystemExit("Alpaca no respondió después de 6 intentos")


def barras(ticker, desde, hasta, clave, secreto):
    """Barras de 1 minuto entre dos fechas (incluidas): lista de (t en Nueva York, o, h, l, c, v)."""
    params = {"symbols": ticker, "timeframe": "1Min", "feed": "sip", "adjustment": "split", "limit": 10000,
              "start": f"{desde}T00:00:00Z", "end": f"{hasta}T23:59:59Z"}
    out = []
    while True:
        j = pedir(params, clave, secreto)
        for b in j.get("bars", {}).get(ticker, []):
            t = dt.datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(NY)
            out.append((t, b["o"], b["h"], b["l"], b["c"], b["v"]))
        tok = j.get("next_page_token")
        if not tok:
            return out
        params["page_token"] = tok
        print(f"  {ticker}: {len(out)} barras hasta {out[-1][0]:%Y-%m-%d}", file=sys.stderr)


def leer_crudo(ruta):
    out = []
    if not os.path.exists(ruta) and os.path.exists(ruta + ".gz"):
        ruta += ".gz"
    with (gzip.open(ruta, "rt") if ruta.endswith(".gz") else open(ruta)) as f:
        next(f)
        for linea in f:
            t, o, h, l, c, v = linea.rstrip("\n").split(",")
            out.append((dt.datetime.fromisoformat(t), float(o), float(h), float(l), float(c), float(v)))
    return out


def a_sesion(bs):
    """Una fila por minuto de la sesión regular de cada día con operaciones."""
    por_dia = {}
    for t, _o, _h, _l, c, _v in bs:
        m = (t.hour - 9) * 60 + t.minute - 30
        if 0 <= m < 390:
            por_dia.setdefault(t.date(), {})[m] = c
    filas = []
    ultimo = None
    for d in sorted(por_dia):
        mins = por_dia[d]
        if len(mins) < 200:                       # día corto (feriado a medias) o casi sin datos
            continue
        for m in range(max(mins) + 1):           # los días de media jornada terminan antes
            if m in mins:
                ultimo = mins[m]
            if ultimo is not None:
                filas.append((d, m, ultimo))
    return filas


def saltos(filas, umbral):
    """Cambios entre el último minuto de un día y el primero del siguiente mayores que umbral."""
    out = []
    for k in range(1, len(filas)):
        if filas[k][0] != filas[k - 1][0]:
            a, b = filas[k - 1][2], filas[k][2]
            if a > 0 and abs(b / a - 1) > umbral:
                out.append(f"{filas[k][0]} {a:.2f}->{b:.2f} ({100 * (b / a - 1):+.0f} %)")
    return out


def leer_lista(ruta):
    """Tickers de un archivo de texto: se ignora lo que sigue a '#' y los rótulos 'grupo:'."""
    out = []
    with open(ruta) as f:
        for linea in f:
            linea = linea.split("#")[0]
            if ":" in linea:
                linea = linea.split(":", 1)[1]
            out.extend(linea.split())
    return out


def una(t, a, carpeta, clave, secreto):
    try:
        _una(t, a, carpeta, clave, secreto)
    except BaseException as e:            # una empresa que falla no detiene a las demás
        print(f"{t}: FALLA {type(e).__name__}: {e}", flush=True)


def _una(t, a, carpeta, clave, secreto):
    ruta = os.path.join(carpeta, f"{t}.csv")
    if not a.solo_sesion and not a.rehacer and os.path.exists(ruta):
        print(f"{t}: ya estaba, se salta", flush=True)
        return
    ruta_crudo = os.path.join(carpeta, "crudo", f"{t}.csv")
    if a.solo_sesion:
        bs = leer_crudo(ruta_crudo)
    else:
        bs = barras(t, a.desde, a.hasta, clave, secreto)
        if a.gzip:
            ruta_crudo += ".gz"
        tmp = ruta_crudo + ".tmp"
        with (gzip.open(tmp, "wt", newline="\n") if a.gzip else open(tmp, "w", newline="\n")) as f:
            f.write("t,o,h,l,c,v\n")
            for b in bs:
                f.write(f"{b[0].isoformat()},{b[1]:.4f},{b[2]:.4f},{b[3]:.4f},{b[4]:.4f},{b[5]:.0f}\n")
        os.replace(tmp, ruta_crudo)
    filas = a_sesion(bs)
    del bs
    tmp = ruta + ".tmp"
    with open(tmp, "w", newline="\n") as f:
        f.write("fecha,minuto,precio\n")
        for d, m, c in filas:
            f.write(f"{d},{m},{c:.4f}\n")
    os.replace(tmp, ruta)
    dias = len({d for d, _, _ in filas})
    print(f"{t}: {len(filas)} minutos de sesión en {dias} días -> {ruta}", flush=True)
    for x in saltos(filas, a.salto):
        print(f"{t}: SALTO entre días {x}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tickers", nargs="+", default=["META", "AAPL", "NFLX", "AMD", "TSLA"])
    ap.add_argument("--lista", default=None, help="archivo con los tickers (reemplaza a --tickers)")
    ap.add_argument("--procesos", type=int, default=1, help="empresas que se bajan a la vez")
    ap.add_argument("--tope", type=int, default=190, help="llamadas por minuto entre todos los hilos")
    ap.add_argument("--gzip", action="store_true", help="barras crudas comprimidas (crudo/TICKER.csv.gz)")
    ap.add_argument("--rehacer", action="store_true", help="baja aunque TICKER.csv ya exista")
    ap.add_argument("--salto", type=float, default=0.25, help="avisa saltos entre días mayores que esto")
    ap.add_argument("--desde", default="2022-01-01")
    ap.add_argument("--hasta", default="2024-12-31")
    ap.add_argument("--claves", default="~/.alpaca.env", help="archivo con la clave si no está en el entorno")
    ap.add_argument("--salida", default=None, help="carpeta de salida (por omisión $P4_DATOS/minuto)")
    ap.add_argument("--solo-sesion", action="store_true", help="rehace TICKER.csv desde crudo/ sin descargar")
    a = ap.parse_args(argv)
    if a.salida:
        carpeta = os.path.expanduser(a.salida)
    elif os.environ.get("P4_DATOS"):
        carpeta = os.path.join(os.path.expanduser(os.environ["P4_DATOS"]), "minuto")
    else:
        carpeta = os.path.join(RAIZ, "data", "externos", "minuto")
    os.makedirs(os.path.join(carpeta, "crudo"), exist_ok=True)
    clave = secreto = None
    if not a.solo_sesion:
        clave, secreto = leer_claves(a.claves)
    tickers = leer_lista(a.lista) if a.lista else a.tickers
    TOPE.n = a.tope
    if a.procesos <= 1:
        for t in tickers:
            una(t, a, carpeta, clave, secreto)
    else:
        with ThreadPoolExecutor(a.procesos) as ex:
            for f in [ex.submit(una, t, a, carpeta, clave, secreto) for t in tickers]:
                f.result()


if __name__ == "__main__":
    main()
