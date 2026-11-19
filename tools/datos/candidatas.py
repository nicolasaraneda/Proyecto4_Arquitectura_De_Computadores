#!/usr/bin/env python3
"""candidatas.py: liquidez y cobertura de las candidatas a otras_acciones.txt (pedido del 19/11).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Pide barras diarias de enero de 2020 y de diciembre de 2024 (cuatro llamadas) para 198 acciones
grandes que cotizaron todo 2020 a 2024 sin cambio de símbolo, fusión ni escisión conocida, y las
ordena por monto transado mediano diario en enero de 2020 (precio de cierre por volumen, en
millones de dólares). otras_acciones.txt toma las 20 primeras de cada grupo (PYPL pasa a fin y
UBER a ind, como en GICS desde 2023) y las dos siguientes como suplentes. La clave se lee como en
alpaca.py y no se imprime.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alpaca
SECT = {
 "tec": "MSFT GOOGL NVDA INTC CSCO ORCL ADBE CRM QCOM TXN AVGO MU AMAT LRCX KLAC ADI NXPI MRVL ADSK INTU NOW PYPL CMCSA DIS VZ CHTR EA TTWO SNAP TWLO SHOP UBER ZM ROKU DOCU OKTA CRWD DDOG PINS SPOT WDAY PANW FTNT SNPS CDNS HPQ WDC STX ON SWKS MCHP ANET",
 "fin": "JPM BAC WFC C GS MS SCHW BLK AXP USB PNC COF MET AIG PRU BK TFC CME ICE SPGI MCO MA V ALL TRV MMC AFL PGR CB BX",
 "sal": "JNJ ABBV LLY UNH ABT TMO BMY AMGN GILD CVS MDT ISRG VRTX REGN BIIB MRNA ZTS CI HUM BSX SYK DXCM IQV HCA MCK",
 "con": "AMZN WMT COST HD LOW TGT MCD SBUX NKE KO PEP PG PM MO CL MDLZ KHC GM F BKNG MAR EBAY ETSY LULU TJX ROST DG DLTR YUM CMG KR EL CCL RCL NCLH DAL UAL AAL LVS WYNN MGM EXPE",
 "ind": "BA CAT DE HON UNP UPS FDX LMT NOC GD CSX NSC EMR ETN ITW WM LUV XOM CVX COP OXY SLB EOG HAL MPC PSX VLO DVN KMI WMB FCX NEM LIN APD SHW NUE DOW NEE DUK SO D AEP AMT PLD EQIX SPG O CCI PSA",
}
tick = [t for s in SECT.values() for t in s.split()]
assert len(tick) == len(set(tick)), [t for t in tick if tick.count(t) > 1]
clave, secreto = alpaca.leer_claves("~/.alpaca.env")
H = {"APCA-API-KEY-ID": clave, "APCA-API-SECRET-KEY": secreto, "Accept": "application/json"}
def pedir(params):
    url = alpaca.URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60) as r:
        hdr = {k: v for k, v in r.headers.items() if k.lower().startswith("x-ratelimit")}
        return json.loads(r.read()), hdr
out = {}
for etiqueta, a, b in (("ini", "2020-01-02", "2020-01-31"), ("fin", "2024-12-02", "2024-12-31")):
    datos = {}
    for i in range(0, len(tick), 60):
        params = {"symbols": ",".join(tick[i:i+60]), "timeframe": "1Day", "feed": "sip", "adjustment": "split",
                  "limit": 10000, "start": a + "T00:00:00Z", "end": b + "T23:59:59Z"}
        while True:
            j, hdr = pedir(params)
            for s, bs in j.get("bars", {}).items():
                datos.setdefault(s, []).extend(bs)
            if not j.get("next_page_token"):
                break
            params["page_token"] = j["next_page_token"]
    out[etiqueta] = datos
print("límite de llamadas por minuto:", hdr.get("X-Ratelimit-Limit"))
sec = {t: s for s, v in SECT.items() for t in v.split()}
filas = []
for t in tick:
    ini, fin = out["ini"].get(t, []), out["fin"].get(t, [])
    dv = sorted(b["c"] * b["v"] for b in ini)
    med = dv[len(dv)//2] / 1e6 if dv else 0
    filas.append((med, t, sec[t], len(ini), len(fin), ini[0]["t"][:10] if ini else "-", ini[0]["c"] if ini else 0))
filas.sort(reverse=True)
for f in filas:
    print(f"{f[1]:6s} {f[2]} dias_ini={f[3]:2d} dias_fin={f[4]:2d} primer={f[5]} c0={f[6]:9.2f} mediana_USD_M={f[0]:8.1f}")
print(len(tick), "candidatos")
