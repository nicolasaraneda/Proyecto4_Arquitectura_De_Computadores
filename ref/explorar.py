#!/usr/bin/env python3
"""explorar.py: barridos de la familia paramétrica, una idea por tabla.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Cada sección cambia una sola pieza de la estrategia y muestra qué pasa en la
evidencia de exploración (semilla 0): los 10 bloques de práctica, 5000
remuestreos, 5000 series del modelo calibrado, 5000 del modelo con parámetros
vecinos y 1000 de cada familia de estrés. Usa el motor en C (ref/motor.py).

    python3 ref/explorar.py                 # todas las secciones
    python3 ref/explorar.py bandas saltos   # solo esas

Secciones: bandas, estimadores, volatilidad, saltos, cortes, guardia, tope,
ordenes, asimetria, potencia.

Columnas: media y peor bloque de práctica; media y percentil 5 de los
remuestreos, del modelo y del vecino; `act` es el porcentaje de remuestreos en
que la guardia o el tope llegaron a actuar; y de las familias de estrés, el
percentil 5 y el peor caso. Estas tablas son de exploración: con ellas se
eligieron los parámetros, así que sus números tienen sesgo de selección. Los
finalistas se evalúan aparte con otra semilla (ref/frontera.py).
"""
import math
import os
import random
import statistics as st
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import calibracion as cal   # noqa: E402
import candidatos           # noqa: E402
import generador            # noqa: E402
import motor                # noqa: E402
import series               # noqa: E402

TAMANOS = (("bloques", None), ("remuestreo", 5000), ("modelo", 5000), ("modelo_vecino", 5000),
           ("paseo", 1000), ("tendencia", 1000), ("cambio_de_caracter", 1000), ("saltos", 1000),
           ("volatil", 1000), ("nivel_bajo", 1000))
BASE = dict(k=5, E=128, X=0)


def conjuntos(semilla=0):
    return {n: motor.conjunto(n, c, semilla=semilla) for n, c in TAMANOS}


def nombre_de(cfg, ocultar=()):
    return " ".join(f"{k}={v}" for k, v in cfg.items() if k not in ocultar) or "(regla base)"


def tabla(titulo, cfgs, cj, pool, ocultar=("k",), nota=None):
    res = {n: motor.evaluar(ruta, cfgs, pool) for n, ruta in cj.items()}
    print(f"\n== {titulo} ==")
    if nota:
        print(nota)
    print(f"{'parametros':40s} | {'bloques':>11s} | {'remuestreo':>16s} | {'modelo':>11s} | {'vecino':>11s} | "
          f"{'paseo':>10s} | {'tendencia':>10s} | {'cambio car.':>11s} | {'saltos':>6s}")
    print(f"{'':40s} | {'media':>5s} {'peor':>5s} | {'media':>5s} {'p5':>5s} {'act':>4s} | {'media':>5s} {'p5':>5s} | "
          f"{'media':>5s} {'p5':>5s} | {'p5':>5s} {'peor':>4s} | {'p5':>5s} {'peor':>4s} | {'p5':>5s} {'peor':>5s} | {'p5':>6s}")
    for i, c in enumerate(cfgs):
        r = lambda n, campo: res[n][i][campo]                     # noqa: E731
        act = 100 * max(r("remuestreo", "con_tope"), r("remuestreo", "con_guardia"))
        print(f"{nombre_de(c, ocultar):40s} | {r('bloques', 'media'):5.0f} {r('bloques', 'peor'):5.0f} | "
              f"{r('remuestreo', 'media'):5.0f} {r('remuestreo', 'p5'):5.0f} {act:3.0f}% | "
              f"{r('modelo', 'media'):5.0f} {r('modelo', 'p5'):5.0f} | {r('modelo_vecino', 'media'):5.0f} {r('modelo_vecino', 'p5'):5.0f} | "
              f"{r('paseo', 'p5'):5.0f} {r('paseo', 'peor'):4.0f} | {r('tendencia', 'p5'):5.0f} {r('tendencia', 'peor'):4.0f} | "
              f"{r('cambio_de_caracter', 'p5'):5.0f} {r('cambio_de_caracter', 'peor'):5.0f} | {r('saltos', 'p5'):6.0f}")
    return res


def mejores(titulo, cfgs, cj, pool, cuantos=6, ocultar=("k",), nota=None, fijos=()):
    """Barre muchas configuraciones y muestra las mejores por media (remuestreo, modelo y vecino) y las fijas."""
    res = {n: motor.evaluar(cj[n], cfgs, pool) for n in ("remuestreo", "modelo", "modelo_vecino")}
    media = lambda i: sum(res[n][i]["media"] for n in res) / 3      # noqa: E731
    orden = sorted(range(len(cfgs)), key=lambda i: -media(i))
    elegidas = [cfgs[i] for i in orden[:cuantos]]
    por_rem = sorted(range(len(cfgs)), key=lambda i: -res["remuestreo"][i]["media"])[:2]
    elegidas += [cfgs[i] for i in por_rem if cfgs[i] not in elegidas]
    elegidas = [c for c in fijos if c not in elegidas] + elegidas
    medias = [media(i) for i in range(len(cfgs))]
    nota = (nota + "\n" if nota else "") + (
        f"{len(cfgs)} combinaciones. Promedio de las tres medias: mejor {max(medias):.0f}, mediana "
        f"{sorted(medias)[len(medias) // 2]:.0f}, peor {min(medias):.0f}. Se muestran las fijas de referencia, "
        f"las {cuantos} mejores por ese promedio y las 2 mejores por remuestreo.")
    return tabla(titulo, elegidas, cj, pool, ocultar, nota)


# ---- Secciones ---------------------------------------------------------------------

def bandas(cj, pool):
    cfgs = [dict(k=5, E=e, X=x) for e in (32, 48, 64, 80, 96, 112, 128, 144, 160, 192, 224)
            for x in (-64, -32, -16, 0, 16, 32, 64)]
    mejores("Bandas con media exponencial (k = 5): E de 1 a 7 unidades, X de -2 a +2", cfgs, cj, pool,
            fijos=[BASE, dict(k=5, E=192, X=-32), dict(k=5, E=96, X=0), dict(k=5, E=64, X=16), dict(k=5, E=48, X=32)],
            nota="E y X en unidades de 1/32 de precio: E=128 es entrar 4 unidades bajo la media.")
    fila = [dict(k=5, E=e, X=0) for e in (48, 64, 80, 96, 112, 128, 144, 160, 192, 224)]
    tabla("Meseta: umbral de entrada con salida en la media (X = 0)", fila, cj, pool)
    fila = [dict(k=5, E=96, X=x) for x in (-64, -32, -16, 0, 16, 32, 64)]
    tabla("Meseta: umbral de salida con entrada en 3 unidades (E = 96)", fila, cj, pool)


def estimadores(cj, pool):
    ema = [dict(k=k, E=e << k, X=0) for k in (3, 4, 5, 6, 7) for e in (2, 3, 4)]
    tabla("Media exponencial: constante de tiempo (E en unidades de precio por 2^k)", ema, cj, pool, ocultar=())
    sma = [dict(est=2, k=k, E=e << k, X=x << k) for k in (5, 6) for e in (3, 4) for x in (0, 1)]
    tabla("Suma movil de 2^k precios", sma, cj, pool, ocultar=())
    kal = [dict(est=1, E=e, X=x) for e in (100, 140, 190, 250) for x in (-40, 0, 40, 80)]
    tabla("Kalman de dos estados con los coeficientes calibrados (phi 0,961, K1 0,625, K2 0,1875)", kal, cj, pool,
          nota="E y X en unidades de 1/256 de precio, sobre la transitoria estimada.")
    todos = [dict(est=1, ka=ka, kb=kb, k1a=a1, k1b=b1, k2a=a2, k2b=b2, E=e, X=x)
             for ka, kb in ((5, 7), (5, 0), (4, 0), (6, 0)) for a1, b1 in ((1, 3), (1, 0), (2, 0))
             for a2, b2 in ((3, 4), (3, 0), (2, 0), (4, 0)) for e in (70, 100, 140, 190, 250) for x in (-40, 0, 40, 80, 120)]
    mejores("Kalman de dos estados: barrido de coeficientes y bandas", todos, cj, pool, ocultar=("est",),
            fijos=[BASE, dict(k=5, E=96, X=0), dict(k=5, E=48, X=32), dict(est=1, E=190, X=-40), dict(est=1, E=100, X=120)],
            nota="La fila est=1 E=100 X=120 son las bandas de la politica optima del modelo.")


def volatilidad(cj, pool):
    cfgs = [dict(k=5, E=e0, X=x0, kv=kv, ev=ev, xv=xv, sv=2 + kv - 5)
            for kv in (4, 6) for e0 in (0, 32, 64, 96) for ev in (0, 2, 4, 6, 8, 12, 16, 20) for x0 in (0, 32)
            for xv in (0, 2, 4) if ev or xv]
    mejores("Bandas escaladas con la volatilidad: E = E0 + ev * V / 4, X = X0 + xv * V / 4", cfgs, cj, pool,
            fijos=[BASE, dict(k=5, E=96, X=0), dict(k=5, E=48, X=32)],
            nota="V es la media exponencial de |cambio| (0,40 en el regimen tranquilo y 1,21 en el ruidoso, por 32).")


def saltos(cj, pool):
    cfgs = [BASE] + [dict(BASE, J=j) for j in (4, 5, 6, 8, 10)] + [dict(k=5, E=96, X=0)] + \
           [dict(k=5, E=96, X=0, J=j) for j in (6, 8)]
    tabla("Manejo de saltos: un cambio de J o mas corre el nivel con el precio", cfgs, cj, pool)


def cortes(cj, pool):
    cfgs = [BASE] + [dict(BASE, tmax=t, lock=b) for t in (24, 32, 48, 64, 96, 128) for b in (0, 200)]
    tabla("Tope de tiempo: sale si lleva mas de tmax ticks adentro", cfgs, cj, pool,
          nota="lock=0: no vuelve a entrar hasta que el precio recupere la media. lock=200: espera 200 ticks.")
    cfgs = [BASE] + [dict(BASE, stop=s) for s in (3, 4, 6, 8, 10, 12, 16)]
    tabla("Tope de precio: sale si el precio baja `stop` unidades desde la entrada", cfgs, cj, pool)


def guardia(cj, pool):
    j = dict(BASE, J=8)
    cfgs = [j] + [dict(j, kg=kg, g=g, gsal=s) for kg in (6, 7) for g in (64, 96, 128, 160, 192) for s in (0, 1)]
    tabla("Guardia por tendencia: G = media exponencial de la desviacion, activa si G < -g", cfgs, cj, pool,
          nota="Todas con J=8. gsal=1: con la guardia activa ademas sale de la posicion.")
    cfgs = [j] + [dict(j, tmax=t) for t in (48, 64)] + \
           [dict(j, tmax=t, nfal=n, gapag=a) for t in (48, 64) for n in (2, 3) for a in (250, 500, 1000)]
    tabla("Guardia por cortes seguidos: tras nfal topes de tiempo seguidos deja de operar gapag ticks", cfgs, cj, pool,
          nota="Todas con J=8.")


def tope(cj, pool):
    j = dict(BASE, J=8)
    cfgs = [j] + [dict(j, cap=c) for c in (12, 16, 24, 32)] + \
           [dict(j, capsh=a, capsh2=b) for a, b in ((1, 0), (2, 3), (2, 0), (3, 4), (3, 0))] + \
           [dict(j, capsh=a, capini=1) for a in (1, 2, 3)] + [dict(j, capsh=a, capoff=1000) for a in (1, 2)] + \
           [dict(j, **candidatos.GUARDIA, **candidatos.TOPE), dict(candidatos.PROTECCION_FUERTE, **BASE)]
    tabla("Tope de perdida: deja de operar si la caida acumulada pasa de cap + (p >> capsh) + (p >> capsh2)", cfgs,
          cj, pool, nota="Todas con J=8. capsh=1 es 50 % del precio, capsh=2 es 25 %, capsh=3 es 12,5 %. "
          "capini=1 mide desde el inicio de la ronda y no desde el mejor momento. Las dos ultimas filas son los "
          "paquetes de proteccion normal y fuerte.")


def ordenes(cj, pool):
    cfgs = [BASE, dict(BASE, modo=1)] + [dict(BASE, modo=2, p2=p) for p in (90, 110, 140)] + \
           [dict(BASE, q1=q, E2=e) for q in (20, 40) for e in (160, 192, 256)]
    tabla("Tamano de las ordenes", cfgs, cj, pool,
          nota="modo=1: una sola orden de compra por entrada. modo=2: segunda orden solo si el precio es <= p2. "
          "q1 y E2: entrada escalonada, q1 acciones en E y el resto bajo E2.")


def _respuesta(p, k=5, horizontes=(5, 20, 50)):
    """Cambio medio del precio después de la ejecución, según la desviación al decidir."""
    s = p[0] << k
    devs = []
    for x in p:
        devs.append(((x << k) - s) / (1 << k))
        s += ((x << k) - s) >> k
    cortes_ = [(-99, -6), (-6, -4), (-4, -3), (-3, -2), (-2, -1), (-1, 0), (0, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 99)]
    salida = []
    for lo, hi in cortes_:
        idx = [t for t in range(50, len(p) - max(horizontes) - 2) if lo <= devs[t] < hi]
        salida.append(((lo, hi), len(idx), [st.fmean(p[t + 1 + h] - p[t + 1] for t in idx) for h in horizontes]
                       if len(idx) >= 20 else None))
    return salida


def asimetria(cj, pool):
    print("\n== Asimetria entre caidas y subidas ==")
    print("Cambio medio del precio entre el tick de ejecucion y 5, 20 y 50 ticks despues, segun la desviacion\n"
          "del precio respecto a la media exponencial (k = 5) al decidir. Practica contra el modelo (400 000 ticks).")
    real, sim = _respuesta(series.practica()), _respuesta(series.modelo(400000, random.Random(3)))
    print(f"{'desviacion':>12s} | {'practica':^31s} | {'modelo':^32s}")
    print(f"{'':>12s} | {'n':>5s} {'h=5':>7s} {'h=20':>7s} {'h=50':>7s} | {'n':>6s} {'h=5':>7s} {'h=20':>7s} {'h=50':>7s}")
    for (rango, n, r), (_, m, s) in zip(real, sim):
        f = lambda v: "   --      --      --  " if v is None else " ".join(f"{x:+7.2f}" for x in v)   # noqa: E731
        print(f"{str(rango):>12s} | {n:5d} {f(r)} | {m:6d} {f(s)}")


def potencia(cj, pool):
    """¿Se puede saber dentro de una ronda si la serie revierte?"""
    print("\n== Potencia de una guardia estadistica dentro de una ronda ==")
    print("Razon de varianza a 50 ticks medida en una sola serie de 2000 ticks: como se reparte en el modelo\n"
          "calibrado (que revierte) y en el paseo aleatorio con la misma volatilidad (que no revierte).")
    filas = {}
    for nombre in ("modelo", "paseo", "tendencia"):
        vr = sorted(series.razon_de_varianza(s, 50) for s in series.lote(nombre, 400, 2000, 0))
        filas[nombre] = vr
        print(f"   {nombre:10s}: percentil 5 {vr[20]:.2f}, mediana {vr[200]:.2f}, percentil 95 {vr[380]:.2f}")
    corte = filas["modelo"][380]
    detecta = sum(v > corte for v in filas["paseo"]) / len(filas["paseo"])
    print(f"   Si la guardia saltara cuando la razon pasa del percentil 95 del modelo ({corte:.2f}), se activaria en\n"
          f"   el 5 % de las series que si revierten y solo en el {100 * detecta:.0f} % de los paseos aleatorios.")
    p = series.practica()
    et = generador.segmentar(p)
    ll_modelo = generador.menos_log_verosimilitud(p, et, cal.Q_NIVEL, cal.Q_TRANS, cal.PHI, cal.RAZON_RUIDOSO)
    x, ll_paseo = generador.nelder_mead(
        lambda v: generador.menos_log_verosimilitud(p, et, v[0], 1e-9, 0.5, v[1]), [0.25, 9.0], [0.05, 2.0])
    print(f"   Verosimilitud en los 20 000 ticks de practica: el modelo con reversion supera al paseo aleatorio en\n"
          f"   {ll_paseo - ll_modelo:.1f} unidades de log-verosimilitud, es decir {(ll_paseo - ll_modelo) / 10:.1f} por ronda "
          f"de 2000 ticks. Con 1 unidad de evidencia\n   por ronda no se puede decidir en vivo si la serie revierte.")


SECCIONES = dict(bandas=bandas, estimadores=estimadores, volatilidad=volatilidad, saltos=saltos, cortes=cortes,
                 guardia=guardia, tope=tope, ordenes=ordenes, asimetria=asimetria, potencia=potencia)


def main(argv=None):
    pedidas = (argv if argv is not None else sys.argv[1:]) or list(SECCIONES)
    for s in pedidas:
        if s not in SECCIONES:
            print(f"seccion desconocida: {s}. Disponibles: {', '.join(SECCIONES)}")
            return 2
    print("Exploracion de la familia parametrica (semilla 0). Patrimonio final en series de 2000 ticks.")
    cj = conjuntos()
    with Pool(motor.PROCESOS) as pool:
        for s in pedidas:
            SECCIONES[s](cj, pool)
    return 0


if __name__ == "__main__":
    sys.exit(main())
