#!/usr/bin/env python3
"""experimento.py: evaluación de la familia "cotas" sobre la población real (docs/cotas.md, sección 5).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Poblaciones (poblacion.py):
  puente     ventanas de las cinco empresas (diarios reales de 2022 a 2024, días con la forma
             de días reales de Meta), normalizadas entre 100 y 255; largos 2000, 5000 y 20000;
             dos rellenos distintos de los minutos por empresa.
  meta_dias  días de la serie Meta sorteados y encadenados, normalizados.
  meta       la serie del profesor (una sola).
Separación para ajustar y validar:
  por años     ajuste: ventanas que empiezan en 2022 o 2023; validación: enteras en 2024.
  por empresa  ajuste: META, AAPL y NFLX; validación: AMD y TSLA.
Casos:
  a  inicio: espera, compra, compra parcial de k acciones, según el primer precio (umbral u)
  b  después de ver los dos extremos: banda de w unidades
  c  márgenes: compra desde 100 + a, vende desde 255 - b
  d  hipótesis falsa: la ronda es un trozo de una ventana normalizada más larga
  e  torneo contra campos de rivales con y sin reglas de extremos
Salidas en docs/mediciones/cotas/. Uso: python3 ref/cotas/experimento.py (unos minutos).
"""
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402
import cotas  # noqa: E402
import poblacion  # noqa: E402

SALIDA = os.path.join(comun.RAIZ, "docs", "mediciones", "cotas")
LARGOS = (2000, 5000, 20000)
POR_EMPRESA = 120            # ventanas por empresa, largo y relleno
RELLENOS = (0, 1)


def C(nombre, inicio=0, a=0, b=0, banda=0, k=0, u=178):
    return (nombre, "cotas", (inicio, a, b, banda, k, u))


BASE = [("nada", "nada", ()), ("siempre", "siempre", ()), ("max_media", "media", (5, 3, 0)),
        ("regla_base", "media", (5, 4, 0)), ("media_e2", "media", (5, 2, 0)), ("media_e6", "media", (5, 6, 0)),
        ("zscore", "zscore", (5, 6, 5, 2, 64, 0)), ("zscore_z2", "zscore", (5, 6, 2, 1, 64, 0))]


def variantes():
    v = [C("espera"), C("compra", 1)]
    v += [C(f"parte{k}", 2, k=k) for k in (10, 20, 30, 40, 50)]
    v += [C(f"umbral{u}", 3, u=u) for u in (130, 150, 170, 190, 210, 230)]
    for ini, n in ((0, "espera"), (1, "compra")):
        v += [C(f"{n}_banda{w}", ini, banda=w) for w in (10, 20, 30, 40, 50, 60, 65, 70, 73, 76)]
        v += [C(f"{n}_a{a}", ini, a=a) for a in (1, 2, 3, 5, 8, 12)]
        v += [C(f"{n}_b{b}", ini, b=b) for b in (1, 2, 3, 5, 8, 12)]
        v += [C(f"{n}_a{a}_b{a}_banda{w}", ini, a=a, b=a, banda=w) for a in (2, 5) for w in (20, 40, 60)]
    v += [C(f"parte{k}_banda{w}", 2, banda=w, k=k) for k in (10, 20, 30) for w in (40, 60, 70)]
    return v


ESTRATEGIAS = BASE + variantes()
NOMBRES = [e[0] for e in ESTRATEGIAS]
CAMPO_SIN = ["nada", "siempre", "max_media", "regla_base", "media_e2", "media_e6", "zscore", "zscore_z2"]
CAMPO_COTAS = ["espera", "compra", "compra_banda40", "espera_banda40", "umbral170", "compra_a2_b2_banda40"]


def poblacion_puente():
    """Lista de (empresa, largo, fecha_inicio, fecha_fin, ventana)."""
    out = []
    for emp in poblacion.EMPRESAS:
        for r in RELLENOS:
            precios, fechas = poblacion.puente(emp, r)
            rng = random.Random(f"ventanas-{emp}-{r}")
            for largo in LARGOS:
                for _ in range(POR_EMPRESA):
                    i = rng.randrange(0, len(precios) - largo)
                    out.append((emp, largo, fechas[i], fechas[i + largo - 1], comun.normalizar(precios[i:i + largo])))
    return out


def poblacion_trozos():
    """Caso d: ventanas de 20000 normalizadas y cortadas en rondas de 2000 y 5000, sin normalizar de nuevo."""
    out = []
    for emp in poblacion.EMPRESAS:
        precios, fechas = poblacion.puente(emp, 0)
        rng = random.Random(f"trozos-{emp}")
        for _ in range(30):
            i = rng.randrange(0, len(precios) - 20000)
            v = comun.normalizar(precios[i:i + 20000])
            for largo in (2000, 5000):
                for j in range(0, 20000, largo):
                    out.append((emp, largo, fechas[i], fechas[i], v[j:j + largo]))
    return out


def poblacion_meta_dias():
    out = []
    rng = random.Random("meta-dias")
    for largo in LARGOS:
        for _ in range(200):
            out.append(("META*", largo, None, None, comun.normalizar(poblacion.meta_dias(rng, largo))))
    return out


def resumen(filas, j, jref):
    w = sorted(f[j] for f in filas)
    n = len(w)
    return dict(n=n, media=st.mean(w), p5=w[int(0.05 * (n - 1))], peor=w[0],
                gana_nada=sum(1 for f in filas if f[j] > 10000) / n,
                gana_ref={k: sum(1 for f in filas if f[j] > f[r]) / n for k, r in jref.items()})


def puntos(filas, jnos, frac, rng):
    """Puntos por ronda (lineal entre el peor y el mejor del campo) y fracción de rondas ganadas.
    Cada uno de los 9 rivales usa una regla de extremos con probabilidad `frac`."""
    pts, primero = [], 0
    for f in filas:
        riv = [f[NOMBRES.index(rng.choice(CAMPO_COTAS if rng.random() < frac else CAMPO_SIN))] for _ in range(9)]
        todos = riv + [f[jnos]]
        lo, hi = min(todos), max(todos)
        pts.append(0.5 if hi == lo else (f[jnos] - lo) / (hi - lo))
        primero += f[jnos] >= hi
    return st.mean(pts), primero / len(filas)


def linea(nombre, r):
    g = r["gana_ref"]
    return (f"{nombre:28s} {r['media']:9.0f} {r['p5']:7d} {r['peor']:7d} {100 * r['gana_nada']:6.1f} "
            f"{100 * g['siempre']:6.1f} {100 * g['max_media']:6.1f}")


CAB = f"{'estrategia':28s} {'media':>9s} {'p5':>7s} {'peor':>7s} {'>nada':>6s} {'>c y m':>6s} {'>max_m':>6s}"


def tabla(titulo, filas, nombres):
    jref = {"siempre": NOMBRES.index("siempre"), "max_media": NOMBRES.index("max_media")}
    L = ["", f"== {titulo} ({len(filas)} ventanas)", CAB]
    for n in nombres:
        L.append(linea(n, resumen(filas, NOMBRES.index(n), jref)))
    return L


def main():
    os.makedirs(SALIDA, exist_ok=True)
    print("generando poblaciones...", file=sys.stderr)
    pp = poblacion_puente()
    pm = poblacion_meta_dias()
    pt = poblacion_trozos()
    meta = cotas.leer(os.path.join(comun.RAIZ, "data", "practica_meta.csv"))
    todas = pp + pm + pt + [("META", 20000, None, None, meta)]
    print(f"evaluando {len(ESTRATEGIAS)} estrategias en {len(todas)} ventanas...", file=sys.stderr)
    _, filas = comun.evaluar(ESTRATEGIAS, [v[4] for v in todas], "experimento")
    fp, fm, ft, fmeta = filas[:len(pp)], filas[len(pp):len(pp) + len(pm)], filas[len(pp) + len(pm):-1], filas[-1]

    def sub(lista, filas_, cond):
        return [f for v, f in zip(lista, filas_) if cond(v)]

    clave = ["nada", "siempre", "max_media", "zscore", "espera", "compra", "parte20", "parte40", "umbral170",
             "umbral190", "espera_banda20", "espera_banda40", "espera_banda60", "espera_banda70", "espera_banda76",
             "compra_banda20", "compra_banda40", "compra_banda60", "compra_banda70", "parte20_banda60", "parte20_banda70",
             "espera_a2", "espera_b2", "espera_a5", "compra_a2", "compra_b2", "compra_a5", "espera_a2_b2_banda60",
             "compra_a2_b2_banda40"]
    # --- variantes por población y largo
    L = ["Familia cotas en la poblacion real (ref/cotas/experimento.py)",
         "Patrimonio final desde 10 000 (comision 5). '>nada', '>c y m' y '>max_m': porcentaje de ventanas en que la",
         "estrategia termina sobre no operar, sobre comprar 63 siempre (comprar y mantener) y sobre max_media.",
         "", "Serie Meta del profesor: " + ", ".join(f"{n} {fmeta[NOMBRES.index(n)]}" for n in clave)]
    for largo in LARGOS:
        L += tabla(f"puente, cinco empresas, largo {largo}", sub(pp, fp, lambda v: v[1] == largo), clave)
    for largo in LARGOS:
        L += tabla(f"dias de Meta sorteados, largo {largo}", sub(pm, fm, lambda v: v[1] == largo), clave)
    open(os.path.join(SALIDA, "variantes.txt"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))

    # --- ajuste y validación: la mejor variante de cotas por patrimonio medio en el ajuste
    candidatas = [n for n in NOMBRES if n not in dict((b[0], 1) for b in BASE)]
    S = ["Seleccion con separacion de ajuste y validacion (ref/cotas/experimento.py)",
         "Se elige la variante de cotas con mayor patrimonio medio en el ajuste y se informa en la validacion,",
         "junto con sus vecinas (meseta) y las de referencia."]
    for nombre_sep, aj, va in (
            ("por anos (ajuste 2022-2023, validacion 2024)",
             lambda v: v[2].year in (2022, 2023), lambda v: v[2].year == 2024 and v[3].year == 2024),
            ("por empresa (ajuste META AAPL NFLX, validacion AMD TSLA)",
             lambda v: v[0] in ("META", "AAPL", "NFLX"), lambda v: v[0] in ("AMD", "TSLA"))):
        for largo in LARGOS:
            fa = sub(pp, fp, lambda v: aj(v) and v[1] == largo)
            fv = sub(pp, fp, lambda v: va(v) and v[1] == largo)
            medias = sorted(((st.mean(f[NOMBRES.index(n)] for f in fa), n) for n in candidatas), reverse=True)
            mejor = medias[0][1]
            S += ["", f"== {nombre_sep}, largo {largo}: ajuste {len(fa)} ventanas, validacion {len(fv)}",
                  "   cinco mejores en el ajuste: " + ", ".join(f"{n} {m:.0f}" for m, n in medias[:5])]
            S += [f"   en la validacion:", "   " + CAB]
            jref = {"siempre": NOMBRES.index("siempre"), "max_media": NOMBRES.index("max_media")}
            vecinas = [x for x in ("espera_banda40", "espera_banda60", "espera_banda70", "espera_banda76", "parte20_banda70",
                                   "compra", "espera", "compra_banda40", "max_media", "siempre", "nada") if x != mejor]
            for n in [mejor] + vecinas:
                S.append("   " + linea(n, resumen(fv, NOMBRES.index(n), jref)))
    open(os.path.join(SALIDA, "seleccion.txt"), "w").write("\n".join(S) + "\n")
    print("\n".join(S))

    # --- caso d: hipótesis falsa
    D = ["Caso d: la ronda es un trozo de una ventana de 20 000 normalizada (no se vuelve a normalizar)",
         "Generado por ref/cotas/experimento.py. Cinco empresas, 30 ventanas de 20 000 cada una, cortadas en rondas."]
    for largo in (2000, 5000):
        f_ = sub(pt, ft, lambda v: v[1] == largo)
        toca = sum(1 for v in pt if v[1] == largo and (min(v[4]) == 100 or max(v[4]) == 255)) / len(f_)
        D += tabla(f"trozos de {largo} (tocan algun extremo: {100 * toca:.0f} %)", f_, clave)
    open(os.path.join(SALIDA, "hipotesis_falsa.txt"), "w").write("\n".join(D) + "\n")
    print("\n".join(D))

    # --- caso e: torneo
    T = ["Caso e: torneo. En cada ronda, 9 rivales sorteados del campo; puntos lineales entre el peor y el mejor",
         "de la ronda (0 a 1) y porcentaje de rondas en primer lugar. Poblacion puente, cinco empresas.",
         "Campos: 'sin extremos' (" + ", ".join(CAMPO_SIN) + "), 'un tercio con extremos' y 'dos tercios con extremos'",
         "(los de extremos sorteados de: " + ", ".join(CAMPO_COTAS) + ")."]
    campos = {"sin extremos": 0.0, "un tercio con extremos": 1 / 3, "dos tercios con extremos": 2 / 3}
    for largo in LARGOS:
        f_ = sub(pp, fp, lambda v: v[1] == largo)
        T += ["", f"== largo {largo} ({len(f_)} rondas)", f"{'estrategia':28s}" + "".join(f"{c:>30s}" for c in campos)]
        for n in clave:
            celdas = []
            for c, campo in campos.items():
                pts, pri = puntos(f_, NOMBRES.index(n), campo, random.Random(f"torneo-{c}-{largo}"))
                celdas.append(f"{pts:8.3f} pts {100 * pri:5.1f} % 1o")
            T.append(f"{n:28s}" + "".join(f"{c:>30s}" for c in celdas))
    open(os.path.join(SALIDA, "torneo.txt"), "w").write("\n".join(T) + "\n")
    print("\n".join(T))


if __name__ == "__main__":
    main()
