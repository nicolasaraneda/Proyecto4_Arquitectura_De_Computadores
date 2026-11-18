#!/usr/bin/env python3
"""alpaca.py: descarga barras de 1 minuto de Alpaca para evaluar reglas (no entran al diseño).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Necesita una cuenta gratuita de Alpaca (solo papel, sin depositar dinero) y su clave de
API en las variables de entorno APCA_API_KEY_ID y APCA_API_SECRET_KEY
(docs/pendientes_nicolas.md, acción de los datos por minuto). El plan gratuito entrega
el histórico consolidado (feed SIP) mientras no se pidan los últimos 15 minutos.

Para cada ticker escribe data/externos/minuto/TICKER.csv con una fila por minuto de la
sesión regular (9:30 a 15:59, hora de Nueva York): "fecha,minuto,precio", donde precio es
el cierre del minuto (ajustado por splits) y los minutos sin operaciones repiten el
último precio, como una serie de un precio por minuto de mercado. data/externos/ está
fuera del repositorio (.gitignore): los datos solo se usan para evaluar.

Uso:
    export APCA_API_KEY_ID=...  APCA_API_SECRET_KEY=...
    python3 tools/datos/alpaca.py                       # META AAPL NFLX AMD TSLA, 2022 a 2024
    python3 tools/datos/alpaca.py --tickers AAPL --desde 2023-01-01 --hasta 2023-03-31
Solo usa la biblioteca estándar.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
URL = "https://data.alpaca.markets/v2/stocks/bars"
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pedir(params, clave, secreto):
    url = URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"APCA-API-KEY-ID": clave, "APCA-API-SECRET-KEY": secreto,
                                               "Accept": "application/json"})
    for intento in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:                     # límite de llamadas por minuto
                time.sleep(15 * (intento + 1))
                continue
            raise SystemExit(f"Alpaca respondió {e.code}: {e.read()[:300]!r}")
    raise SystemExit("Alpaca no respondió después de 5 intentos")


def barras(ticker, desde, hasta, clave, secreto):
    """Barras de 1 minuto entre dos fechas (incluidas), en hora de Nueva York."""
    params = {"symbols": ticker, "timeframe": "1Min", "feed": "sip", "adjustment": "split", "limit": 10000,
              "start": f"{desde}T00:00:00Z", "end": f"{hasta}T23:59:59Z"}
    out = []
    while True:
        j = pedir(params, clave, secreto)
        for b in j.get("bars", {}).get(ticker, []):
            t = dt.datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(NY)
            out.append((t, b["c"]))
        tok = j.get("next_page_token")
        if not tok:
            return out
        params["page_token"] = tok
        print(f"  {ticker}: {len(out)} barras hasta {out[-1][0]:%Y-%m-%d}", file=sys.stderr)


def a_sesion(bs):
    """Una fila por minuto de la sesión regular de cada día con operaciones."""
    por_dia = {}
    for t, c in bs:
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tickers", nargs="+", default=["META", "AAPL", "NFLX", "AMD", "TSLA"])
    ap.add_argument("--desde", default="2022-01-01")
    ap.add_argument("--hasta", default="2024-12-31")
    a = ap.parse_args(argv)
    clave, secreto = os.environ.get("APCA_API_KEY_ID"), os.environ.get("APCA_API_SECRET_KEY")
    if not clave or not secreto:
        raise SystemExit("faltan APCA_API_KEY_ID y APCA_API_SECRET_KEY (docs/pendientes_nicolas.md)")
    carpeta = os.path.join(RAIZ, "data", "externos", "minuto")
    os.makedirs(carpeta, exist_ok=True)
    for t in a.tickers:
        filas = a_sesion(barras(t, a.desde, a.hasta, clave, secreto))
        ruta = os.path.join(carpeta, f"{t}.csv")
        with open(ruta, "w", newline="\n") as f:
            f.write("fecha,minuto,precio\n")
            for d, m, c in filas:
                f.write(f"{d},{m},{c:.4f}\n")
        dias = len({d for d, _, _ in filas})
        print(f"{t}: {len(filas)} minutos en {dias} dias -> {os.path.relpath(ruta, RAIZ)}")


if __name__ == "__main__":
    main()
