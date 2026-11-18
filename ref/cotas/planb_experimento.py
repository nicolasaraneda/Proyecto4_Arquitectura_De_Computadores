#!/usr/bin/env python3
"""planb_experimento.py: la mejor regla si las rondas son trozos de una serie normalizada más larga.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Caso: la serie de cada ronda es un trozo de una ventana más larga normalizada entre 100 y
255 (como el testbench oficial, que corre los primeros 2000 ticks de la serie de 20 000), y
no se vuelve a normalizar: la ronda casi nunca toca 100 ni 255.

Población (poblacion.py): ventanas "madre" de 20 000 minutos de las cinco empresas (diarios
reales, días con la forma de días reales de Meta), dos rellenos; las rondas son el primer
trozo (lo más probable con el testbench) o cualquier trozo, de 2000 y de 5000 ticks.
Familias:
  rango      posición en el rango [100, 255] aunque no se toquen: compra bajo L, vende sobre H,
             y opcionalmente compra al inicio si el primer precio es bajo
  salto      saltos de apertura (390 ticks por día): a favor o en contra
  tendencia  cruce de medias
  media      max_media y otros umbrales de reversión; zscore
  referencias: no operar, comprar y mantener, la regla de cotas oficial
Protocolo: se elige en el ajuste (2022-2023, o META AAPL NFLX) y se informa en la
validación (2024, o AMD TSLA), con las vecinas de la elegida (meseta). Salidas en
docs/mediciones/cotas/planb_*.txt. Uso: python3 ref/cotas/planb_experimento.py
"""
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402
import poblacion  # noqa: E402

SALIDA = os.path.join(comun.RAIZ, "docs", "mediciones", "cotas")
MADRES = 60                # ventanas madre por empresa y relleno
LARGO_MADRE = int(os.environ.get("LARGO_MADRE", "20000"))


def estrategias():
    e = [("nada", "nada", ()), ("siempre", "siempre", ()), ("max_media", "media", (5, 3, 0)),
         ("zscore", "zscore", (5, 6, 5, 2, 64, 0)), ("cotas_espera_b60", "cotas", (0, 0, 0, 60, 0, 178))]
    e += [(f"media_e{x}_s{y}", "media", (5, x, y)) for x in (2, 4, 6, 8) for y in (0, 2)]
    for L in range(110, 181, 10):
        for H in range(L + 20, 251, 10):
            e.append((f"rango{L}_{H}", "rango", (L, H, 0, 0)))
    for u in (130, 150, 170, 190):
        e.append((f"inicio{u}", "rango", (0, 256, 1, u)))
        for L, H in ((120, 200), (130, 220), (140, 230), (150, 240)):
            e.append((f"inicio{u}_rango{L}_{H}", "rango", (L, H, 1, u)))
    for a in (5, 10, 15, 20, 30):
        for w in (0, 60):
            e.append((f"cotas_espera_a{a}_b{a}_banda{w}", "cotas", (0, a, a, w, 0, 178)))
    for G in (3, 5, 8):
        for N in (30, 60, 120, 390):
            for d in (0, 1):
                e.append((f"salto{G}_{N}_{'baja' if d == 0 else 'sube'}", "salto", (G, N, d)))
    for k1, k2 in ((3, 6), (4, 8), (5, 9), (6, 10)):
        for d in (0, 1, 2):
            e.append((f"tendencia{k1}_{k2}_{d}", "tendencia", (k1, k2, d)))
    return e


ESTR = estrategias()
NOMBRES = [x[0] for x in ESTR]
REFS = ("nada", "siempre", "max_media", "cotas_espera_b60")


def poblacion_trozos():
    """(empresa, largo, fecha, primero, ventana): trozos de ventanas madre normalizadas."""
    out = []
    for emp in poblacion.EMPRESAS:
        for r in (0, 1):
            precios, fechas = poblacion.puente(emp, r)
            rng = random.Random(f"planb-{emp}-{r}")
            for _ in range(MADRES):
                i = rng.randrange(0, len(precios) - LARGO_MADRE)
                v = comun.normalizar(precios[i:i + LARGO_MADRE])
                for largo in (2000, 5000):
                    for j in range(0, LARGO_MADRE, largo):
                        out.append((emp, largo, fechas[i + j], j == 0, v[j:j + largo]))
    return out


def resumen(fs, j):
    w = sorted(f[j] for f in fs)
    n = len(w)
    return dict(media=st.mean(w), p5=w[int(0.05 * (n - 1))], peor=w[0], gana=sum(1 for x in w if x > 10000) / n,
                pierde=sum(1 for x in w if x < 10000) / n)


def linea(n, r):
    return (f"{n:28s} {r['media']:8.0f} {r['p5']:7d} {r['peor']:7d} {100 * r['gana']:6.1f} {100 * r['pierde']:6.1f}")


CAB = f"{'estrategia':28s} {'media':>8s} {'p5':>7s} {'peor':>7s} {'>nada':>6s} {'<nada':>6s}"


def vecinas(nombre):
    """Las variantes de la misma familia más parecidas (para ver la meseta)."""
    import re
    m = re.match(r"rango(\d+)_(\d+)$", nombre)
    if m:
        L, H = int(m.group(1)), int(m.group(2))
        return [f"rango{L + a}_{H + b}" for a in (-10, 0, 10) for b in (-10, 0, 10) if (a, b) != (0, 0)]
    return []


def main():
    os.makedirs(SALIDA, exist_ok=True)
    print("generando...", file=sys.stderr)
    pob = poblacion_trozos()
    print(f"evaluando {len(ESTR)} estrategias en {len(pob)} rondas...", file=sys.stderr)
    _, filas = comun.evaluar(ESTR, [v[4] for v in pob], "planb")
    L = [f"Plan B: rondas que son trozos de una ventana de {LARGO_MADRE} normalizada (ref/cotas/planb_experimento.py)",
         f"Cinco empresas, dos rellenos, {MADRES} ventanas madre por empresa y relleno. Patrimonio final desde 10 000.",
         "'>nada' y '<nada': porcentaje de rondas que terminan sobre y bajo no operar."]
    for primero, nom in ((True, "primer trozo de cada ventana (lo que corre el testbench oficial)"),
                         (False, "cualquier trozo")):
        for largo in (2000, 5000):
            fs = [f for v, f in zip(pob, filas) if v[1] == largo and (v[3] or not primero)]
            toca = sum(1 for v in pob if v[1] == largo and (v[3] or not primero) and (min(v[4]) == 100 or max(v[4]) == 255))
            L += ["", f"== {nom}, largo {largo}: {len(fs)} rondas, {100 * toca / len(fs):.0f} % tocan algun extremo"]
            medias = sorted(((st.mean(f[j] for f in fs), n) for j, n in enumerate(NOMBRES)), reverse=True)
            L.append("   diez mejores por media: " + ", ".join(f"{n} {m:.0f}" for m, n in medias[:10]))
            L.append("   " + CAB)
            for n in list(REFS) + [n for _, n in medias[:6] if n not in REFS]:
                L.append("   " + linea(n, resumen(fs, NOMBRES.index(n))))
    # Ajuste y validación sobre el primer trozo
    for sep, aj, va in (("por anos (ajuste 2022-2023, validacion 2024)", lambda v: v[2].year in (2022, 2023),
                         lambda v: v[2].year == 2024),
                        ("por empresa (ajuste META AAPL NFLX, validacion AMD TSLA)",
                         lambda v: v[0] in ("META", "AAPL", "NFLX"), lambda v: v[0] in ("AMD", "TSLA"))):
        for largo in (2000, 5000):
            fa = [f for v, f in zip(pob, filas) if v[1] == largo and v[3] and aj(v)]
            fv = [f for v, f in zip(pob, filas) if v[1] == largo and v[3] and va(v)]
            medias = sorted(((st.mean(f[j] for f in fa), n) for j, n in enumerate(NOMBRES)), reverse=True)
            mejor = medias[0][1]
            L += ["", f"== seleccion {sep}, primer trozo, largo {largo}: ajuste {len(fa)}, validacion {len(fv)}",
                  "   cinco mejores en el ajuste: " + ", ".join(f"{n} {m:.0f}" for m, n in medias[:5]),
                  "   en la validacion:", "   " + CAB]
            for n in [mejor] + [x for x in vecinas(mejor) if x in NOMBRES] + list(REFS):
                L.append("   " + linea(n, resumen(fv, NOMBRES.index(n))))
    texto = "\n".join(L) + "\n"
    print(texto)
    sufijo = "" if LARGO_MADRE == 20000 else f"_madre{LARGO_MADRE}"
    open(os.path.join(SALIDA, f"planb{sufijo}.txt"), "w").write(texto)


if __name__ == "__main__":
    main()
