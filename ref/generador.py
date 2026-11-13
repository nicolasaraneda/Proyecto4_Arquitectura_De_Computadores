#!/usr/bin/env python3
"""generador.py: identifica el generador de la serie de práctica y lo valida.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Modelo que se ajusta (docs/algoritmo.md, sección 2):

    precio(t) = redondeo( nivel(t) + transitoria(t) )
    nivel(t)       = nivel(t-1) + ruido de varianza qL          (paseo aleatorio)
    transitoria(t) = phi * transitoria(t-1) + ruido de varianza qT   (AR(1))

con dos regímenes de volatilidad (tranquilo y ruidoso) que multiplican las dos
varianzas, y saltos de nivel poco frecuentes. El redondeo a enteros se trata
como un ruido de observación de varianza 1/12.

Qué hace cada opción:

    python3 ref/generador.py --ajustar    # segmenta los regímenes y ajusta por máxima verosimilitud
    python3 ref/generador.py --validar    # compara series simuladas con la de práctica
    python3 ref/generador.py --redondeo   # cuánta reversión aparente fabrica el redondeo

El ajuste usa el filtro de Kalman para calcular la verosimilitud (cada
evaluación recorre los 20 000 ticks) y Nelder-Mead para maximizarla. Todo con
la biblioteca estándar.

Las constantes ajustadas viven en ref/calibracion.py. --ajustar las vuelve a
calcular y avisa si dejaron de coincidir.
"""
import argparse
import math
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import calibracion as cal     # noqa: E402
import market                 # noqa: E402
import series                 # noqa: E402
import trader                 # noqa: E402


# ---- Estadísticos descriptivos ------------------------------------------------------

def cambios(p):
    return [b - a for a, b in zip(p, p[1:])]


def autocorrelacion(x, k):
    m = st.fmean(x)
    den = sum((v - m) ** 2 for v in x)
    return sum((x[i] - m) * (x[i + k] - m) for i in range(len(x) - k)) / den if den else 0.0


def curtosis(x):
    m, s = st.fmean(x), st.pstdev(x)
    return sum((v - m) ** 4 for v in x) / len(x) / s ** 4


def varianza_a(p, k):
    """Varianza del cambio de precio a k ticks."""
    return st.pvariance([p[i + k] - p[i] for i in range(len(p) - k)])


def razon_latente(p, k, r=cal.R_REDONDEO):
    """Razón de varianza descontando el redondeo.

    El redondeo suma 2r a la varianza del cambio a cualquier horizonte. Si se
    le resta, queda la razón de varianza del proceso antes de redondear.
    """
    return (varianza_a(p, k) - 2 * r) / (k * (varianza_a(p, 1) - 2 * r))


# ---- Regímenes de volatilidad -----------------------------------------------------

def segmentar(p, umbral=cal.UMBRAL_REGIMEN, media_ventana=50, salto=cal.SALTO_MIN_ABS):
    """Etiqueta cada tick: 1 si es ruidoso, 0 si es tranquilo.

    Un tick es ruidoso si la desviación estándar de los cambios en la ventana
    de +-50 ticks, sin contar los saltos, pasa del umbral.
    """
    d = cambios(p)
    n = len(p)
    etiquetas = []
    for t in range(n):
        seg = [v for v in d[max(0, t - media_ventana):min(n - 1, t + media_ventana)] if abs(v) < salto]
        etiquetas.append(1 if st.pstdev(seg) > umbral else 0)
    return etiquetas


def tramos(etiquetas):
    """Lista de (régimen, duración) de los tramos consecutivos."""
    salida, actual, largo = [], etiquetas[0], 0
    for e in etiquetas:
        if e == actual:
            largo += 1
        else:
            salida.append((actual, largo))
            actual, largo = e, 1
    salida.append((actual, largo))
    return salida


# ---- Verosimilitud con el filtro de Kalman ---------------------------------------

def menos_log_verosimilitud(p, etiquetas, q_nivel, q_trans, phi, razon, q_nivel2=None, q_trans2=None, phi2=None,
                            r=cal.R_REDONDEO, salto=cal.SALTO_MIN_ABS):
    """Menos el logaritmo de la verosimilitud gaussiana de la serie.

    Estado [nivel, transitoria], observación precio = nivel + transitoria +
    redondeo. En el régimen ruidoso las varianzas son razon * (q_nivel,
    q_trans), salvo que se entreguen q_nivel2, q_trans2 y phi2 propios. En un
    tick con salto se suma una varianza grande al nivel, para que el salto no
    contamine el ajuste.
    """
    if min(q_nivel, q_trans, razon) <= 0 or not 0 < phi < 0.9999:
        return 1e18
    if q_nivel2 is None:
        q_nivel2, q_trans2, phi2 = razon * q_nivel, razon * q_trans, phi
    elif min(q_nivel2, q_trans2) <= 0 or not 0 < phi2 < 0.9999:
        return 1e18
    nivel, trans = float(p[0]), 0.0
    p11, p12, p22 = 1.0, 0.0, q_trans / (1 - phi * phi)
    total = 0.0
    for t in range(1, len(p)):
        if etiquetas[t]:
            ql, qt, f = q_nivel2, q_trans2, phi2
        else:
            ql, qt, f = q_nivel, q_trans, phi
        if abs(p[t] - p[t - 1]) >= salto:
            ql += 100.0
        trans = f * trans                                  # predicción
        p11, p12, p22 = p11 + ql, f * p12, f * f * p22 + qt
        s = p11 + 2 * p12 + p22 + r                         # varianza de la innovación
        e = p[t] - nivel - trans
        k1, k2 = (p11 + p12) / s, (p12 + p22) / s           # ganancias
        nivel += k1 * e
        trans += k2 * e
        p11, p12, p22 = p11 - k1 * (p11 + p12), p12 - k1 * (p12 + p22), p22 - k2 * (p12 + p22)
        total += math.log(s) + e * e / s
    return 0.5 * total


def nelder_mead(f, x0, paso, iteraciones=300, tolerancia=1e-4):
    """Minimiza f partiendo de x0. Devuelve (x, f(x))."""
    k = len(x0)
    sim = [list(x0)] + [[x0[j] + (paso[j] if j == i else 0.0) for j in range(k)] for i in range(k)]
    fv = [f(x) for x in sim]
    for _ in range(iteraciones):
        orden = sorted(range(k + 1), key=lambda i: fv[i])
        sim, fv = [sim[i] for i in orden], [fv[i] for i in orden]
        if fv[-1] - fv[0] < tolerancia:
            break
        c = [sum(s[j] for s in sim[:-1]) / k for j in range(k)]
        xr = [2 * c[j] - sim[-1][j] for j in range(k)]
        fr = f(xr)
        if fr < fv[0]:
            xe = [3 * c[j] - 2 * sim[-1][j] for j in range(k)]
            fe = f(xe)
            sim[-1], fv[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < fv[-2]:
            sim[-1], fv[-1] = xr, fr
        else:
            xc = [0.5 * (c[j] + sim[-1][j]) for j in range(k)]
            fc = f(xc)
            if fc < fv[-1]:
                sim[-1], fv[-1] = xc, fc
            else:
                for i in range(1, k + 1):
                    sim[i] = [0.5 * (sim[0][j] + sim[i][j]) for j in range(k)]
                    fv[i] = f(sim[i])
    i = min(range(k + 1), key=lambda j: fv[j])
    return sim[i], fv[i]


# ---- Simulación ----------------------------------------------------------------------

def simular(n, rng, **parametros):
    """Serie de n precios del modelo calibrado (es series.modelo)."""
    return series.modelo(n, rng, **parametros)


# ---- Opciones del programa ------------------------------------------------------------

def ajustar():
    p = series.practica()
    d = cambios(p)
    etiquetas = segmentar(p)
    tr = tramos(etiquetas)
    ruidosos = [largo for e, largo in tr if e]
    tranquilos = [largo for e, largo in tr if not e]
    saltos = [(i, v) for i, v in enumerate(d) if abs(v) >= cal.SALTO_MIN_ABS]
    print("1. Regímenes de volatilidad (desviación estándar de los cambios en +-50 ticks, umbral "
          f"{cal.UMBRAL_REGIMEN})")
    print(f"   Fracción de ticks ruidosos: {sum(etiquetas) / len(p):.3f}")
    print(f"   Tramos tranquilos: {tranquilos}  (media {st.fmean(tranquilos):.0f})")
    print(f"   Tramos ruidosos:   {ruidosos}  (media {st.fmean(ruidosos):.0f})")
    for nombre, valor in (("tranquilo", 0), ("ruidoso", 1)):
        dd = [v for v, e in zip(d, etiquetas) if e == valor and abs(v) < cal.SALTO_MIN_ABS]
        print(f"   Régimen {nombre}: varianza de los cambios {st.pvariance(dd):.3f}, "
              f"media de |cambio| {st.fmean(abs(v) for v in dd):.3f}, mayor |cambio| {max(abs(v) for v in dd)}")
    print(f"\n2. Saltos (|cambio| >= {cal.SALTO_MIN_ABS}): {len(saltos)} en {len(p)} ticks: {saltos}")
    for i, v in saltos:
        antes, despues = st.fmean(p[i - 20:i + 1]), st.fmean(p[i + 21:i + 61])
        print(f"   tick {i}: salto {v:+d}; media de los 20 ticks anteriores {antes:.1f}, de los ticks 20 a 60 "
              f"siguientes {despues:.1f} (se conserva {100 * (despues - antes) / v:.0f} % del salto)")

    print("\n3. Ajuste por máxima verosimilitud (4 parámetros: q_nivel, q_trans, phi, razón entre regímenes)")
    def f4(x):
        return menos_log_verosimilitud(p, etiquetas, *x)
    mejor = None
    for x0 in ([0.15, 0.08, 0.95, 9.0], [0.10, 0.15, 0.80, 9.0], [0.20, 0.03, 0.98, 9.0]):
        x, fx = nelder_mead(f4, x0, [0.05, 0.03, 0.02, 2.0])
        print(f"   desde {x0}: q_nivel {x[0]:.4f}, q_trans {x[1]:.4f}, phi {x[2]:.4f}, razón {x[3]:.3f}, "
              f"-log L {fx:.2f}")
        if mejor is None or fx < mejor[1]:
            mejor = (x, fx)
    (ql, qt, phi, razon), f_mejor = mejor
    sd_t = math.sqrt(qt / (1 - phi * phi))
    print(f"   Resultado: desv. est. del paso del nivel {math.sqrt(ql):.3f}, de la innovación transitoria "
          f"{math.sqrt(qt):.3f}; desv. est. de la transitoria {sd_t:.2f} (tranquilo) y "
          f"{sd_t * math.sqrt(razon):.2f} (ruidoso); vida media {math.log(0.5) / math.log(phi):.1f} ticks")

    print("\n4. Modelos alternativos (misma segmentación)")
    x_rw, f_rw = nelder_mead(lambda x: menos_log_verosimilitud(p, etiquetas, x[0], 1e-9, 0.5, x[1]),
                             [0.25, 9.0], [0.05, 2.0])
    print(f"   Solo paseo aleatorio más redondeo (sin transitoria): -log L {f_rw:.2f}. "
          f"La transitoria mejora en {f_rw - f_mejor:.1f} con 2 parámetros más")
    x6, f6 = nelder_mead(lambda x: menos_log_verosimilitud(p, etiquetas, x[0], x[1], x[2], 1.0, x[3], x[4], x[5]),
                         [ql, qt, phi, razon * ql, razon * qt, phi], [0.03, 0.02, 0.01, 0.3, 0.2, 0.01], iteraciones=500)
    print(f"   Parámetros separados por régimen (6): tranquilo q_nivel {x6[0]:.4f}, q_trans {x6[1]:.4f}, "
          f"phi {x6[2]:.4f}; ruidoso q_nivel {x6[3]:.4f}, q_trans {x6[4]:.4f}, phi {x6[5]:.4f}; -log L {f6:.2f}. "
          f"Mejora en {f_mejor - f6:.1f} con 2 parámetros más")

    print("\n5. Constantes de ref/calibracion.py")
    ok = True
    for nombre, nuevo, guardado, tol in (("Q_NIVEL", ql, cal.Q_NIVEL, 0.01), ("Q_TRANS", qt, cal.Q_TRANS, 0.01),
                                         ("PHI", phi, cal.PHI, 0.003), ("RAZON_RUIDOSO", razon, cal.RAZON_RUIDOSO, 0.3),
                                         ("P_SALTO", len(saltos) / len(p), cal.P_SALTO, 1e-9),
                                         ("DUR_TRANQUILO", st.fmean(tranquilos), cal.DUR_TRANQUILO, 50),
                                         ("DUR_RUIDOSO", st.fmean(ruidosos), cal.DUR_RUIDOSO, 20)):
        coincide = abs(nuevo - guardado) <= tol
        ok = ok and coincide
        print(f"   {nombre:14s} ajustado {nuevo:10.5f}   guardado {guardado:10.5f}   {'coincide' if coincide else 'DISTINTO'}")
    print("PASS las constantes guardadas corresponden al ajuste" if ok else "FAIL hay que actualizar ref/calibracion.py")
    return 0 if ok else 1


def _fila(nombre, p):
    d = cambios(p)
    v1 = st.pvariance(d)
    vr = {k: varianza_a(p, k) / (k * v1) for k in (2, 10, 50, 100, 500)}
    ad = [abs(v) for v in d]
    return (f"{nombre:28s} {v1:6.3f} {vr[2]:6.2f} {vr[10]:6.2f} {vr[50]:6.2f} {vr[100]:6.2f} {vr[500]:6.2f} "
            f"{autocorrelacion(d, 1):7.3f} {curtosis(d):6.1f} {autocorrelacion(ad, 1):6.2f} {autocorrelacion(ad, 100):6.2f} "
            f"{sum(v == 0 for v in d) / len(d):6.2f} {max(ad):4d}")


def _regla_base(lista):
    ws = sorted(trader.correr(s).w for s in lista)
    return st.fmean(ws), ws[len(ws) // 2], ws[int(0.05 * len(ws))], ws[0], ws[-1]


def validar(n_series=5, por_lote=400):
    p = series.practica()
    print("1. Estadísticos de la serie de práctica y de series simuladas del mismo largo (20 000 ticks)")
    print(f"{'serie':28s} {'var d':>6s} {'VR2':>6s} {'VR10':>6s} {'VR50':>6s} {'VR100':>6s} {'VR500':>6s} "
          f"{'acf(1)':>7s} {'curt':>6s} {'|d|:1':>6s} {'|d|:100':>6s} {'d=0':>6s} {'max':>4s}")
    print(_fila("practica", p))
    for i in range(n_series):
        print(_fila(f"modelo, semilla {i}", simular(len(p), random.Random(100 + i))))
    sin_reg = [simular(len(p), random.Random(200 + i), razon=1.0, p_salto=0.0,
                       q_nivel=cal.Q_NIVEL * 2.1, q_trans=cal.Q_TRANS * 2.1) for i in range(2)]
    for i, s in enumerate(sin_reg):
        print(_fila(f"un solo regimen, semilla {i}", s))

    print("\n2. La regla base en series de 2000 ticks (patrimonio final: media, mediana, percentil 5, peor, mejor)")
    conjuntos = (("practica, 10 bloques", series.bloques(p, 2000)),
                 (f"remuestreo ({por_lote})", series.lote("remuestreo", por_lote, 2000, 0)),
                 (f"modelo ({por_lote})", [simular(2000, random.Random(1000 + i)) for i in range(por_lote)]))
    for nombre, lista in conjuntos:
        m, med, p5, peor, mejor = _regla_base(lista)
        byh = st.fmean(market.comprar_y_mantener(s) for s in lista)
        print(f"   {nombre:24s} {m:8.0f} {med:7d} {p5:7d} {peor:7d} {mejor:7d}   comprar y mantener {byh:7.0f}")
    return 0


def redondeo():
    """Cuánta reversión aparente fabrica el redondeo, y cuánta queda al descontarlo."""
    p = series.practica()
    print("Razón de varianza de la serie de práctica, medida y descontando el redondeo (varianza 1/12 por precio)")
    print(f"{'horizonte':>9s} {'medida':>8s} {'sin redondeo':>13s} {'paseo redondeado':>17s}")
    paseo_r = series.a_precios(simular(200000, random.Random(7), q_trans=1e-12, razon=1.0, p_salto=0.0,
                                       q_nivel=varianza_a(p, 1) - 2 * cal.R_REDONDEO, redondear=False))
    v1, w1 = varianza_a(p, 1), varianza_a(paseo_r, 1)
    for k in (2, 5, 10, 20, 50, 100, 200, 500, 1000):
        print(f"{k:9d} {varianza_a(p, k) / (k * v1):8.3f} {razon_latente(p, k):13.3f} {varianza_a(paseo_r, k) / (k * w1):17.3f}")
    print(f"\nVarianza del cambio a 1 tick: {v1:.3f}. De eso, el redondeo aporta {2 * cal.R_REDONDEO:.3f} "
          f"({100 * 2 * cal.R_REDONDEO / v1:.0f} %).")
    print("La columna del paseo redondeado es un paseo aleatorio sin ninguna reversión, con la misma varianza\n"
          "latente, redondeado a enteros: toda su reversión aparente viene del redondeo.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Identificación y validación del generador de la serie de práctica")
    ap.add_argument("--ajustar", action="store_true")
    ap.add_argument("--validar", action="store_true")
    ap.add_argument("--redondeo", action="store_true")
    a = ap.parse_args(argv)
    if a.ajustar:
        return ajustar()
    if a.redondeo:
        return redondeo()
    return validar()


if __name__ == "__main__":
    sys.exit(main())
