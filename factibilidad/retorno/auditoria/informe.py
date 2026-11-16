#!/usr/bin/env python3
"""informe.py: cifras del informe del estudio de retorno contra el evaluador independiente, y tablas de la auditoría.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee las salidas de `indep estudio --semilla 0` y `--semilla 2`
(build/auditoria/estudio_s0.txt y estudio_s2.txt) y escribe:

  mediciones/auditoria_cifras.txt   cada cifra informada por el estudio, la que obtiene el
                                    evaluador independiente y si coinciden;
  mediciones/auditoria_tablas.md    las tablas propias de la auditoría: campos más fuertes,
                                    las tres vistas de las rondas de 20 000 ticks, límites
                                    1 y 255, criterio de corte recalculado y error del
                                    percentil 5.

Cuándo se dice que una cifra coincide:
  exacta   cifras que no dependen de ningún sorteo (patrimonio, órdenes, medias, percentiles,
           diferencias pareadas y sus errores): tienen que ser iguales al redondeo informado;
  torneo   puntos esperados: el estudio los estima sorteando 6 campos por serie y aquí se
           calculan exactos, y los rivales de azar usan otro generador. Se acepta una
           diferencia de hasta 0,006 puntos en un nivel y 0,005 en una diferencia;
  p5       percentil 5 de la competencia de tres rondas y lecturas H3s y H3r: los dos son
           sorteos distintos. Se acepta hasta 2 veces el error que informa el estudio (o
           0,012 si no informa error).

    python3 auditoria/informe.py            (desde factibilidad/retorno)
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
BUILD = os.path.join(RETORNO, "build", "auditoria")
MED = os.path.join(RETORNO, "mediciones")


def cargar(semilla):
    d = {}
    with open(os.path.join(BUILD, f"estudio_s{semilla}.txt")) as f:
        for linea in f:
            if "=" in linea:
                k, v = linea.rstrip("\n").rsplit("=", 1)
                d[k] = float(v)
    return d


D = {0: cargar(0), 2: cargar(2)}

# ---- Cifras informadas ------------------------------------------------------------------
# (tabla, cifra, semilla, clave, informado, tipo, tolerancia)
C = []


def ex(tabla, cifra, s, clave, inf, unidad=1.0):
    C.append((tabla, cifra, s, clave, inf, "exacta", unidad / 2 + 1e-6))


def to(tabla, cifra, s, clave, inf, tol=0.006):
    C.append((tabla, cifra, s, clave, inf, "torneo", tol))


def p5(tabla, cifra, s, clave, inf, ee=None):
    C.append((tabla, cifra, s, clave, inf, "p5", 2 * ee if ee else 0.012))


T = "Numeros conocidos"
ex(T, "regla base, serie completa: patrimonio", 2, "practica.base.w", 27062)
ex(T, "regla base, serie completa: ordenes", 2, "practica.base.ordenes", 388)
ex(T, "comprar y mantener, serie completa", 2, "practica.byh_testbench.w", 6497)
ex(T, "regla base, 10 bloques: media", 2, "s2.n2000.todas.bloques.base.media", 11069)
ex(T, "regla base, 10 bloques: peor", 2, "s2.n2000.todas.bloques.base.peor", 9720)

T = "Frontera, 2000 ticks"
for cand, fila in {
    "base": dict(bm=11069, bp=9720, rm=10766, rp=8966, pm=10914, pp=8648, ep=5637, ew=256),
    "max_media": dict(bm=11043, bp=9620, rm=10832, rd=66, re=11, rp=8778, pm=11066, pd=152, pe=12, pp=8552, ep=5202, ew=172),
    "activo": dict(bm=10826, bp=8728, rm=10720, rd=-46, re=17, rp=8438, pm=11244, pd=330, pe=19, pp=8296, ep=4590, ew=116),
    "prudente": dict(bm=10712, bp=10000, rm=10649, rd=-118, re=14, rp=9281, pm=10616, pd=-297, pe=17, pp=9021, ep=6800, ew=219),
    "kalman": dict(bm=11002, bp=9678, rm=10874, rd=108, re=11, rp=8802, pm=11057, pd=143, pe=14, pp=8523, ep=5219, ew=156),
    "guardia": dict(bm=11018, bp=9024, rm=10727, rd=-40, re=13, rp=8811, pm=10863, pd=-50, pe=16, pp=8339, ep=6733, ew=355),
}.items():
    nombres = {"bm": ("bloques", "media"), "bp": ("bloques", "peor"), "rm": ("remuestreo", "media"), "rd": ("remuestreo", "dif"),
               "re": ("remuestreo", "dif_ee"), "rp": ("remuestreo", "p5"), "pm": ("plausibles", "media"), "pd": ("plausibles", "dif"),
               "pe": ("plausibles", "dif_ee"), "pp": ("plausibles", "p5"), "ep": ("estres", "p5"), "ew": ("estres", "peor")}
    for k, v in fila.items():
        conj, med = nombres[k]
        ex(T, f"{cand}, {conj}: {med}", 2, f"s2.n2000.todas.{conj}.{cand}.{med}", v)

T = "Frontera, 20 000 ticks, interiores"
ex(T, "remuestreos interiores", 2, "s2.n20000.int.remuestreo.n", 1994)
ex(T, "plausibles interiores", 2, "s2.n20000.int.plausibles.n", 2010)
for cand, w in {"max_media": 25973, "activo": 19234, "prudente": 19790, "kalman": 26450, "guardia": 23399}.items():
    ex(T, f"{cand}, practica completa", 2, f"practica.{cand}.w", w)
for cand, fila in {
    "base": dict(rm=23862, rmd=20955, rp=12315, pm=22314, pmd=17046, pp=9899),
    "max_media": dict(rm=26533, rmd=22861, rd=2671, re=149, rp=12916, pm=25642, pmd=19549, pd=3329, pe=183, pp=10213),
    "activo": dict(rm=25709, rmd=21884, rd=1847, re=231, rp=11468, pm=30989, pmd=23260, pd=8676, pe=419, pp=10840),
    "prudente": dict(rm=18994, rmd=17412, rd=-4869, re=177, rp=11452, pm=16148, pmd=12808, pd=-6165, pe=258, pp=9220),
    "kalman": dict(rm=27300, rmd=23618, rd=3438, re=153, rp=13074, pm=25591, pmd=19258, pd=3277, pe=187, pp=10396),
}.items():
    nombres = {"rm": ("remuestreo", "media"), "rmd": ("remuestreo", "mediana"), "rd": ("remuestreo", "dif"), "re": ("remuestreo", "dif_ee"),
               "rp": ("remuestreo", "p5"), "pm": ("plausibles", "media"), "pmd": ("plausibles", "mediana"), "pd": ("plausibles", "dif"),
               "pe": ("plausibles", "dif_ee"), "pp": ("plausibles", "p5")}
    for k, v in fila.items():
        conj, med = nombres[k]
        ex(T, f"{cand}, {conj}: {med}", 2, f"s2.n20000.int.{conj}.{cand}.{med}", v)

T = "Frontera, 20 000 ticks, todas"
for cand, fila in {
    "base": dict(rm=37984, rmd=24238, rp=11878, pm=46934, pmd=19970, pp=9987, emd=22988, ep=2697),
    "max_media": dict(rm=45492, rmd=27201, rp=12697, pm=57749, pmd=22740, pp=10515, emd=31747, ep=2840),
    "activo": dict(rm=55922, rmd=26210, rp=11512, pm=79951, pmd=27787, pp=11260, emd=62196, ep=2760),
    "prudente": dict(rm=26770, rmd=19399, rp=11045, pm=29087, pmd=14274, pp=8888, emd=17369, ep=3970),
    "guardia": dict(rm=38563, rmd=23914, rp=11586, pm=44264, pmd=19525, pp=9378, emd=27005, ep=4587),
}.items():
    nombres = {"rm": ("remuestreo", "media"), "rmd": ("remuestreo", "mediana"), "rp": ("remuestreo", "p5"), "pm": ("plausibles", "media"),
               "pmd": ("plausibles", "mediana"), "pp": ("plausibles", "p5"), "emd": ("estres", "mediana"), "ep": ("estres", "p5")}
    for k, v in fila.items():
        conj, med = nombres[k]
        ex(T, f"{cand}, {conj}: {med}", 2, f"s2.n20000.todas.{conj}.{cand}.{med}", v)

T = "Que cambia al alargar la ronda"
for cand, (c1, c2, c3, o1, o2, o3) in {"base": (7.06, 7.32, 10.62, 34.6, 42.1, 82.3), "max_media": (7.83, 8.47, 12.19, 54.6, 71.1, 130.7),
                                        "activo": (7.83, 9.01, 13.65, 75.1, 102.4, 193.7), "prudente": (5.43, 4.87, 7.39, 17.0, 17.1, 35.0),
                                        "kalman": (7.98, 8.59, 12.27, 55.0, 72.6, 131.5)}.items():
    ex(T, f"{cand}: crecimiento por 2000 ticks, ronda de 2000 (%)", 2, f"crec1:s2.n2000.todas.evidencia.{cand}.geom", c1, 0.01)
    ex(T, f"{cand}: crecimiento, 20 000 interiores (%)", 2, f"crec10:s2.n20000.int.evidencia.{cand}.geom", c2, 0.01)
    ex(T, f"{cand}: crecimiento, 20 000 todas (%)", 2, f"crec10:s2.n20000.todas.evidencia.{cand}.geom", c3, 0.01)
    ex(T, f"{cand}: ordenes por 2000 ticks, ronda de 2000", 2, f"s2.n2000.todas.evidencia.{cand}.ordenes", o1, 0.1)
    ex(T, f"{cand}: ordenes por 2000 ticks, 20 000 interiores", 2, f"div10:s2.n20000.int.evidencia.{cand}.ordenes", o2, 0.1)
    ex(T, f"{cand}: ordenes por 2000 ticks, 20 000 todas", 2, f"div10:s2.n20000.todas.evidencia.{cand}.ordenes", o3, 0.1)

for T, pref, filas in (
    ("Hipotesis, 2000 ticks", "s2.n2000.todas.evidencia", {
        "base": (10840, 20, 8811, 1061, -2818, 1.221, 1.084, 1.452, 1.423, 1.675, 1.694),
        "max_media": (10943, 23, 8683, 1164, -2607, 1.228, 1.097, 1.494, 1.463, 1.724, 1.729),
        "activo": (10972, 24, 8373, 1193, -2428, 1.217, 1.099, 1.457, 1.458, 1.681, 1.670),
        "prudente": (10641, 18, 9194, 862, -3119, 1.207, 1.065, 1.345, 1.352, 1.537, 1.577),
        "kalman": (10956, 23, 8646, 1176, -2593, 1.229, 1.097, 1.487, 1.467, 1.716, 1.721),
        "guardia": (10796, 21, 8585, 1017, -2730, 1.207, 1.086, 1.429, 1.400, 1.632, 1.642),
        "nada": (10000, 0, 10000, 220, -3681, 1.129, 1.022, 1.161, 1.146, 1.233, 1.313),
        "byh": (9774, 24, 5876, -6, -124, 0.999, 1.000, 1.090, 1.093, 1.107, 0.969)}),
    ("Hipotesis, 20 000 ticks, interiores", "s2.n20000.int.evidencia", {
        "base": (23085, 246, 10495, 13047, -2225, 2.954, 2.061, 1.732, 1.745, 1.803, 1.812),
        "max_media": (26086, 300, 11231, 16048, -1040, 3.320, 2.270, 1.857, 1.820, 1.935, 1.934),
        "activo": (28360, 396, 11085, 18322, -228, 3.518, 2.377, 1.812, 1.837, 1.915, 1.900),
        "prudente": (17565, 143, 9750, 7527, -4756, 2.260, 1.626, 1.431, 1.623, 1.452, 1.475),
        "kalman": (26442, 304, 11154, 16404, -1138, 3.371, 2.291, 1.841, 1.830, 1.926, 1.925),
        "nada": (10000, 0, 10000, -38, -8183, 1.243, 1.047, 0.952, 1.247, 0.884, 0.914),
        "byh": (10040, 70, 3731, 2, -120, 0.999, 1.000, 0.932, 1.227, 0.879, 0.765)})):
    for cand, (m, e, q, xm, xp, rm, rmd, a, b, hs, hr) in filas.items():
        ex(T, f"{cand}: H1 media", 2, f"{pref}.{cand}.media", m)
        ex(T, f"{cand}: H1 error", 2, f"{pref}.{cand}.ee", e)
        ex(T, f"{cand}: H1 p5", 2, f"{pref}.{cand}.p5", q)
        ex(T, f"{cand}: H2 exceso medio", 2, f"{pref}.{cand}.exc_media", xm)
        ex(T, f"{cand}: H2 exceso p5", 2, f"{pref}.{cand}.exc_p5", xp)
        ex(T, f"{cand}: W/B&H media", 2, f"{pref}.{cand}.raz_media", rm, 0.001)
        ex(T, f"{cand}: W/B&H mediana", 2, f"{pref}.{cand}.raz_mediana", rmd, 0.001)
        to(T, f"{cand}: H3a", 2, f"{pref}.{cand}.mixto.G10.h3a", a)
        to(T, f"{cand}: H3b", 2, f"{pref}.{cand}.mixto.G10.h3b", b)
        p5(T, f"{cand}: H3s", 2, f"{pref}.{cand}.mixto.G10.h3s", hs)
        p5(T, f"{cand}: H3r", 2, f"{pref}.{cand}.mixto.G10.h3r", hr)
ex("Hipotesis, 20 000 ticks, interiores", "series interiores de la evidencia", 2, "s2.n20000.int.evidencia.n", 4004)

T = "Puntos contra la regla base, 2000 ticks (semilla 0 / semilla 2)"
for s, base, filas in ((0, (1.465, 1.437, 0.835, 0.872), {
        "max_media": (103, 10, 0.038, 0.036, 0.047, 0.015, 0.039, 0.022), "kalman": (123, 10, 0.033, 0.040, 0.052, 0.015, 0.028, 0.026),
        "activo": (127, 18, 0.001, 0.029, 0.005, 0.019, -0.022, 0.028), "guardia": (-55, 16, -0.027, -0.030, -0.025, 0.016, -0.072, 0.026),
        "prudente": (-232, 14, -0.114, -0.076, -0.108, 0.015, -0.106, 0.026), "nada": (-879, 23, -0.301, -0.286, -0.299, 0.018, -0.250, 0.022),
        "byh": (-1106, 33, -0.383, -0.350, -0.475, 0.022, -0.472, 0.025)}),
                       (2, (1.452, 1.423, 0.828, 0.867), {
        "max_media": (103, 11, 0.042, 0.040, 0.042, 0.016, 0.017, 0.021), "kalman": (116, 12, 0.034, 0.044, 0.042, 0.016, 0.000, 0.025),
        "activo": (132, 16, 0.005, 0.036, -0.002, 0.018, -0.033, 0.028), "guardia": (-44, 12, -0.023, -0.023, -0.031, 0.017, -0.067, 0.018),
        "prudente": (-199, 14, -0.107, -0.071, -0.108, 0.015, -0.100, 0.023), "nada": (-840, 20, -0.291, -0.276, -0.283, 0.017, -0.250, 0.020),
        "byh": (-1066, 30, -0.363, -0.329, -0.458, 0.022, -0.467, 0.020)})):
    pref = f"s{s}.n2000.todas.evidencia"
    to(T, "base: H3a", s, f"{pref}.base.mixto.G10.h3a", base[0])
    to(T, "base: H3b", s, f"{pref}.base.mixto.G10.h3b", base[1])
    p5(T, "base: p5 de tres rondas, H3a", s, f"{pref}.base.mixto.G10.p5a3", base[2], 0.012)
    p5(T, "base: p5 de tres rondas, H3b", s, f"{pref}.base.mixto.G10.p5b3", base[3], 0.012)
    for cand, (d, e, a, b, pa, pae, pb, pbe) in filas.items():
        ex(T, f"{cand}: H1 dif", s, f"{pref}.{cand}.dif", d)
        ex(T, f"{cand}: H1 dif error", s, f"{pref}.{cand}.dif_ee", e)
        to(T, f"{cand}: dif H3a", s, f"{pref}.{cand}.mixto.G10.dh3a", a, 0.005)
        to(T, f"{cand}: dif H3b", s, f"{pref}.{cand}.mixto.G10.dh3b", b, 0.005)
        p5(T, f"{cand}: dif p5 tres rondas H3a", s, f"{pref}.{cand}.mixto.G10.dp5a3", pa, pae)
        p5(T, f"{cand}: dif p5 tres rondas H3b", s, f"{pref}.{cand}.mixto.G10.dp5b3", pb, pbe)
to(T, "base: p5 de una ronda, H3a", 2, "s2.n2000.todas.evidencia.base.mixto.G10.p5a1", 0.16, 0.02)
to(T, "base: p5 de una ronda, H3b", 2, "s2.n2000.todas.evidencia.base.mixto.G10.p5b1", 0.30, 0.02)

T = "Puntos contra la regla base, 20 000 ticks interiores (semilla 0 / semilla 2)"
for s, base, filas in ((0, (1.730, 1.742, 1.314, 1.389), {
        "max_media": (3278, 124, 0.125, 0.079, 0.188, 0.019, 0.133, 0.021), "kalman": (3720, 136, 0.111, 0.090, 0.186, 0.017, 0.122, 0.026),
        "activo": (5407, 236, 0.080, 0.097, 0.109, 0.020, 0.122, 0.032), "prudente": (-5393, 154, -0.294, -0.112, -0.378, 0.016, -0.200, 0.030)}),
                       (2, (1.732, 1.745, 1.322, 1.389), {
        "max_media": (3001, 118, 0.125, 0.075, 0.192, 0.018, 0.117, 0.024), "kalman": (3357, 121, 0.109, 0.085, 0.189, 0.018, 0.122, 0.030),
        "activo": (5275, 246, 0.080, 0.092, 0.127, 0.022, 0.111, 0.032), "prudente": (-5520, 157, -0.302, -0.122, -0.384, 0.018, -0.189, 0.029)})):
    pref = f"s{s}.n20000.int.evidencia"
    to(T, "base: H3a", s, f"{pref}.base.mixto.G10.h3a", base[0])
    to(T, "base: H3b", s, f"{pref}.base.mixto.G10.h3b", base[1])
    p5(T, "base: p5 de tres rondas, H3a", s, f"{pref}.base.mixto.G10.p5a3", base[2], 0.015)
    p5(T, "base: p5 de tres rondas, H3b", s, f"{pref}.base.mixto.G10.p5b3", base[3], 0.015)
    for cand, (d, e, a, b, pa, pae, pb, pbe) in filas.items():
        ex(T, f"{cand}: H1 dif", s, f"{pref}.{cand}.dif", d)
        ex(T, f"{cand}: H1 dif error", s, f"{pref}.{cand}.dif_ee", e)
        to(T, f"{cand}: dif H3a", s, f"{pref}.{cand}.mixto.G10.dh3a", a, 0.005)
        to(T, f"{cand}: dif H3b", s, f"{pref}.{cand}.mixto.G10.dh3b", b, 0.005)
        p5(T, f"{cand}: dif p5 tres rondas H3a", s, f"{pref}.{cand}.mixto.G10.dp5a3", pa, pae)
        p5(T, f"{cand}: dif p5 tres rondas H3b", s, f"{pref}.{cand}.mixto.G10.dp5b3", pb, pbe)

COMB = [(c, g) for c in ("ingenuo", "mixto", "fuerte") for g in (5, 10, 15)]
T = "Sensibilidad al campo y a G, H3a"
for largo, vista, filas in ((2000, "todas", {"base": (1.652, 1.671, 1.685, 1.480, 1.452, 1.437, 1.309, 1.349, 1.367),
                                             "max_media": (0.022, 0.020, 0.019, 0.039, 0.042, 0.042, 0.086, 0.066, 0.058),
                                             "kalman": (0.023, 0.020, 0.019, 0.031, 0.034, 0.034, 0.070, 0.053, 0.047),
                                             "activo": (0.006, 0.008, 0.009, 0.004, 0.005, 0.006, 0.036, 0.022, 0.018),
                                             "guardia": (-0.016, -0.014, -0.013, -0.026, -0.023, -0.023, -0.023, -0.023, -0.023),
                                             "prudente": (-0.054, -0.049, -0.048, -0.107, -0.107, -0.106, -0.165, -0.141, -0.127)}),
                            (20000, "int", {"base": (1.875, 1.815, 1.762, 1.813, 1.732, 1.684, 1.509, 1.550, 1.556),
                                            "max_media": (0.049, 0.071, 0.089, 0.087, 0.125, 0.144, 0.225, 0.199, 0.190),
                                            "kalman": (0.049, 0.071, 0.090, 0.075, 0.109, 0.127, 0.202, 0.179, 0.173),
                                            "activo": (0.048, 0.073, 0.095, 0.050, 0.080, 0.098, 0.174, 0.153, 0.149),
                                            "prudente": (-0.139, -0.194, -0.228, -0.244, -0.302, -0.324, -0.399, -0.365, -0.348)})):
    for cand, vals in filas.items():
        for (campo, g), v in zip(COMB, vals):
            med = "h3a" if cand == "base" else "dh3a"
            to(T, f"{largo} ticks, {cand}, {campo} G={g}", 2, f"s2.n{largo}.{vista}.evidencia.{cand}.{campo}.G{g}.{med}", v)

T = "Sensibilidad al campo, H3b (G = 10)"
for largo, vista, filas in ((2000, "todas", {"base": (1.542, 1.423, 1.158), "max_media": (0.027, 0.040, 0.085), "kalman": (0.032, 0.044, 0.086),
                                             "activo": (0.019, 0.036, 0.098), "guardia": (-0.020, -0.023, -0.040),
                                             "prudente": (-0.068, -0.071, -0.124)}),
                            (20000, "int", {"base": (1.844, 1.745, 1.256), "max_media": (0.046, 0.075, 0.224), "kalman": (0.051, 0.085, 0.257),
                                            "activo": (0.056, 0.092, 0.275), "prudente": (-0.111, -0.122, -0.287)})):
    for cand, vals in filas.items():
        for campo, v in zip(("ingenuo", "mixto", "fuerte"), vals):
            med = "h3b" if cand == "base" else "dh3b"
            to(T, f"{largo} ticks, {cand}, {campo}", 2, f"s2.n{largo}.{vista}.evidencia.{cand}.{campo}.G10.{med}", v)

T = "Puntos por conjunto, 2000 ticks"
for cand, vals in {"base": (1.475, 1.453, 1.418, 1.389, 1.146, 1.176), "max_media": (0.033, 0.024, 0.057, 0.057, 0.019, 0.023),
                   "kalman": (0.034, 0.041, 0.041, 0.048, 0.010, 0.020), "activo": (-0.053, -0.027, 0.066, 0.096, 0.011, 0.043),
                   "guardia": (-0.021, -0.026, -0.021, -0.022, 0.034, 0.036), "prudente": (-0.090, -0.046, -0.126, -0.099, -0.004, -0.001)}.items():
    k = 0
    for conj in ("remuestreo", "plausibles", "estres"):
        for lect in ("h3a", "h3b"):
            med = lect if cand == "base" else "d" + lect
            to(T, f"{cand}, {conj}, {lect.upper().replace('H3A', 'H3a').replace('H3B', 'H3b')}", 2,
               f"s2.n2000.todas.{conj}.{cand}.mixto.G10.{med}", vals[k], 0.007)
            k += 1

T = "Duelos contra max_media"
for cand, (e, ee, r, re_, pl, ple, a2, a20, b2, b20) in {"kalman": (13, 6, 42, 5, -9, 7, -0.008, -0.016, 0.004, 0.010),
                                                          "activo": (29, 13, -112, 13, 178, 15, -0.037, -0.045, -0.005, 0.017),
                                                          "guardia": (-147, 10, -106, 8, -202, 14, -0.065, -0.173, -0.063, -0.092)}.items():
    ex(T, f"{cand}: H1 evidencia", 2, f"s2.n2000.todas.evidencia.{cand}.mm_dif", e)
    ex(T, f"{cand}: H1 evidencia, error", 2, f"s2.n2000.todas.evidencia.{cand}.mm_dif_ee", ee)
    ex(T, f"{cand}: H1 remuestreo", 2, f"s2.n2000.todas.remuestreo.{cand}.mm_dif", r)
    ex(T, f"{cand}: H1 remuestreo, error", 2, f"s2.n2000.todas.remuestreo.{cand}.mm_dif_ee", re_)
    ex(T, f"{cand}: H1 plausibles", 2, f"s2.n2000.todas.plausibles.{cand}.mm_dif", pl)
    ex(T, f"{cand}: H1 plausibles, error", 2, f"s2.n2000.todas.plausibles.{cand}.mm_dif_ee", ple)
    to(T, f"{cand}: H3a, 2000", 2, f"s2.n2000.todas.evidencia.{cand}.mixto.G10.mm_dh3a", a2, 0.004)
    if cand != "guardia":
        to(T, f"{cand}: H3a, 20 000 interiores", 2, f"s2.n20000.int.evidencia.{cand}.mixto.G10.mm_dh3a", a20, 0.004)
        to(T, f"{cand}: H3b, 20 000 interiores", 2, f"s2.n20000.int.evidencia.{cand}.mixto.G10.mm_dh3b", b20, 0.004)
    to(T, f"{cand}: H3b, 2000", 2, f"s2.n2000.todas.evidencia.{cand}.mixto.G10.mm_dh3b", b2, 0.004)
to(T, "guardia contra max_media en el estres, H3a, semilla 2", 2, "s2.n2000.todas.estres.guardia.mixto.G10.mm_dh3a", 0.015, 0.006)
to(T, "guardia contra max_media en el estres, H3a, semilla 0", 0, "s0.n2000.todas.estres.guardia.mixto.G10.mm_dh3a", 0.004, 0.006)

T = "Limites 1 y 255 (semilla 0)"
for largo, filas in ((2000, {"remuestreo": (0.1, 0.7, 0.0), "plausibles": (0.5, 1.3, 0.6), "estres": (7.6, 17.7, 3.6)}),
                     (20000, {"remuestreo": (31.4, 41.1, 8.8), "plausibles": (20.3, 26.8, 20.7), "estres": (47.7, 56.5, 37.4)})):
    for conj, (a, b, c) in filas.items():
        ex(T, f"{largo} ticks, {conj}: tocan 1 (%)", 0, f"s0.n{largo}.bordes.{conj}.toca1_pct", a, 0.1)
        ex(T, f"{largo} ticks, {conj}: minimo de 20 o menos (%)", 0, f"s0.n{largo}.bordes.{conj}.min20_pct", b, 0.1)
        ex(T, f"{largo} ticks, {conj}: tocan 255 (%)", 0, f"s0.n{largo}.bordes.{conj}.toca255_pct", c, 0.1)
ex(T, "interiores de la evidencia a 20 000, semilla 0", 0, "s0.n20000.int.evidencia.n", 4021)


def valor(s, clave):
    d = D[s]
    if clave.startswith("crec1:"):
        return (d[clave[6:]] / 10000 - 1) * 100
    if clave.startswith("crec10:"):
        return ((d[clave[7:]] / 10000) ** 0.1 - 1) * 100
    if clave.startswith("div10:"):
        return d[clave[6:]] / 10
    return d[clave]


def fmt(x):
    if abs(x) >= 100:
        return f"{x:.0f}" if abs(x - round(x)) < 0.05 else f"{x:.1f}"
    return f"{x:.2f}" if abs(x) >= 3 else f"{x:.3f}"


def escribir_cifras():
    lineas = ["Cifras del estudio de retorno contra el evaluador independiente (auditoria/indep.c)",
              "Tipos: exacta (sin sorteo, igual al redondeo informado), torneo (valor esperado exacto contra sorteo de 6 campos),",
              "p5 (dos sorteos distintos, hasta 2 errores del estudio). Los candidatos kalman y guardia son externos: su patrimonio",
              "por serie viene del arnes y aqui se rehacen solo la estadistica y el torneo.", ""]
    cuenta = {}
    fallas = []
    actual = None
    difs = {}
    for tabla, cifra, s, clave, inf, tipo, tol in C:
        obt = valor(s, clave)
        ok = abs(obt - inf) <= tol
        difs.setdefault(tipo, []).append(abs(obt - inf))
        c = cuenta.setdefault(tabla, {})
        t = c.setdefault(tipo, [0, 0])
        t[0] += 1
        t[1] += ok
        if tabla != actual:
            lineas.append(f"--- {tabla} ---")
            lineas.append(f"{'cifra':58s} {'sem':>3s} {'informado':>10s} {'obtenido':>10s} {'tipo':>7s}  coincide")
            actual = tabla
        lineas.append(f"{cifra:58s} {s:3d} {fmt(inf):>10s} {fmt(obt):>10s} {tipo:>7s}  {'si' if ok else 'NO'}")
        if not ok:
            fallas.append((tabla, cifra, s, inf, obt, tipo))
    lineas.append("")
    lineas.append("Resumen por tabla (coinciden / comparadas)")
    lineas.append(f"{'tabla':72s} {'exactas':>10s} {'torneo':>10s} {'p5':>10s}")
    tot = {"exacta": [0, 0], "torneo": [0, 0], "p5": [0, 0]}
    for tabla, c in cuenta.items():
        celdas = []
        for tipo in ("exacta", "torneo", "p5"):
            n, ok = c.get(tipo, [0, 0])
            tot[tipo][0] += n
            tot[tipo][1] += ok
            celdas.append(f"{ok}/{n}" if n else "")
        lineas.append(f"{tabla:72s} {celdas[0]:>10s} {celdas[1]:>10s} {celdas[2]:>10s}")
    lineas.append(f"{'TOTAL':72s} " + " ".join(f"{tot[t][1]}/{tot[t][0]:<d}".rjust(10) for t in ("exacta", "torneo", "p5")))
    lineas.append("")
    lineas.append("Tamano de las diferencias entre lo informado y lo obtenido")
    for tipo in ("exacta", "torneo", "p5"):
        v = sorted(difs.get(tipo, [0.0]))
        lineas.append(f"  {tipo:7s} {len(v):4d} cifras: mediana {v[len(v) // 2]:.4f}, percentil 95 {v[int(0.95 * len(v))]:.4f}, maxima {v[-1]:.4f}")
    lineas.append("  (en las exactas la diferencia es el redondeo de la cifra informada: como mucho media unidad del ultimo digito)")
    lineas.append("")
    if fallas:
        lineas.append(f"Cifras que no coinciden: {len(fallas)}")
        for tabla, cifra, s, inf, obt, tipo in fallas:
            lineas.append(f"  [{tabla}] {cifra}, semilla {s}: informado {fmt(inf)}, obtenido {fmt(obt)} ({tipo})")
    else:
        lineas.append("Todas las cifras comparadas coinciden.")
    with open(os.path.join(MED, "auditoria_cifras.txt"), "w", newline="\n") as f:
        f.write("\n".join(lineas) + "\n")
    return tot, fallas


# ---- Tablas de la auditoría -------------------------------------------------------------------

def pm(x, e, dec=3):
    return f"{x:+.{dec}f} ± {e:.{dec}f}".replace(".", ",")


def num(x, dec=3):
    return f"{x:.{dec}f}".replace(".", ",")


def juicio(d, e):
    return "mejora" if d > 2 * e else "empeora" if d < -2 * e else "igual"


CAMPOS = [("ingenuo", "ingenuo"), ("mixto", "mixto"), ("fuerte", "fuerte (60 % reversión ajustada)"),
          ("racional", "racional (nadie entrega algo que pierde en la práctica)"),
          ("fijos2", "mixto con 2 rivales fijos: base y max_media"), ("fijos3", "mixto con 3 fijos: base, max_media y suma móvil"),
          ("reversores", "todos con reversión ajustada")]
CANDS = ["max_media", "kalman", "activo", "guardia", "prudente"]


def tabla_campos(s, largo, vista):
    d = D[s]
    pref = f"s{s}.n{largo}.{vista}.evidencia"
    out = [f"| Campo (G = 10) | `base`: H3a, H3b | " + " | ".join(f"`{c}`" for c in CANDS) + " |", "|---|---|" + "---|" * len(CANDS)]
    for campo, nombre in CAMPOS:
        if f"{pref}.base.{campo}.G10.h3a" not in d:
            continue
        fila = [nombre, f"{num(d[f'{pref}.base.{campo}.G10.h3a'])}, {num(d[f'{pref}.base.{campo}.G10.h3b'])}"]
        for c in CANDS:
            k = f"{pref}.{c}.{campo}.G10"
            if k + ".dh3a" not in d:
                fila.append("")
                continue
            fila.append(f"{pm(d[k + '.dh3a'], d[k + '.dh3a_ee'])}, {pm(d[k + '.dh3b'], d[k + '.dh3b_ee'])}")
        out.append("| " + " | ".join(fila) + " |")
    return out


def tabla_campos_mm(s, largo, vista):
    d = D[s]
    pref = f"s{s}.n{largo}.{vista}.evidencia"
    cands = ["kalman", "activo", "guardia"]
    out = ["| Campo (G = 10) | " + " | ".join(f"`{c}` contra `max_media`: H3a, H3b" for c in cands) + " |", "|---|" + "---|" * len(cands)]
    for campo, nombre in CAMPOS:
        fila = [nombre]
        for c in cands:
            k = f"{pref}.{c}.{campo}.G10"
            fila.append(f"{pm(d[k + '.mm_dh3a'], d[k + '.mm_dh3a_ee'])}, {pm(d[k + '.mm_dh3b'], d[k + '.mm_dh3b_ee'])}" if k + ".mm_dh3a" in d else "")
        out.append("| " + " | ".join(fila) + " |")
    return out


def pasa(d, k, ref=""):
    """Criterio de corte con las cifras de la auditoría: media mejora en más de 2 ee y p5 de tres rondas no baja en más de 2 ee."""
    filas = []
    for lect, p in (("h3a", "p5a3"), ("h3b", "p5b3")):
        jm = juicio(d[f"{k}.{ref}d{lect}"], d[f"{k}.{ref}d{lect}_ee"])
        jp = juicio(d[f"{k}.{ref}d{p}"], d[f"{k}.{ref}d{p}_ee"])
        filas.append(jm == "mejora" and jp != "empeora")
    return all(filas)


def tabla_veredictos():
    out = ["| Candidata | Semilla 0: 2000, 20 000 interiores (de 9) | Semilla 2: 2000, 20 000 interiores (de 9) | Campos más fuertes, 2000 ticks, semillas 0 y 2 (de 4) |",
           "|---|---|---|---|"]
    for ref, nombre_ref in (("", "base"), ("mm_", "max_media")):
        for c in ("max_media", "kalman", "activo", "guardia", "prudente"):
            if ref and c in ("max_media", "prudente"):
                continue
            fila = [f"`{c}` contra `{nombre_ref}`"]
            for s in (0, 2):
                d = D[s]
                n2 = sum(pasa(d, f"s{s}.n2000.todas.evidencia.{c}.{campo}.G{g}", ref) for campo, g in COMB)
                n20 = sum(pasa(d, f"s{s}.n20000.int.evidencia.{c}.{campo}.G{g}", ref) for campo, g in COMB)
                fila.append(f"{n2}, {n20}")
            fuertes = []
            for s in (0, 2):
                fuertes.append(str(sum(pasa(D[s], f"s{s}.n2000.todas.evidencia.{c}.{campo}.G10", ref)
                                       for campo in ("racional", "fijos2", "fijos3", "reversores"))))
            fila.append(" y ".join(fuertes))
            out.append("| " + " | ".join(fila) + " |")
    return out


def tabla_vistas():
    out = ["| Candidato contra `base` | Interiores (la del estudio): H1, H3a, H3b | Todas: H1, H3a, H3b | Parada (sin selección): H1, H3a, H3b |",
           "|---|---|---|---|"]
    for s in (0, 2):
        d = D[s]
        for c in ("max_media", "activo", "prudente"):
            fila = [f"`{c}`, semilla {s}"]
            for vista in ("int", "todas"):
                k = f"s{s}.n20000.{vista}.evidencia.{c}"
                fila.append(f"{d[k + '.dif']:+.0f} ± {d[k + '.dif_ee']:.0f}, {pm(d[k + '.mixto.G10.dh3a'], d[k + '.mixto.G10.dh3a_ee'])}, "
                            f"{pm(d[k + '.mixto.G10.dh3b'], d[k + '.mixto.G10.dh3b_ee'])}")
            k = f"s{s}.n20000.sesgo.parada.{c}.mixto.G10"
            fila.append(f"{d[k + '.dh1']:+.0f} ± {d[k + '.dh1_ee']:.0f}, {pm(d[k + '.dh3a'], d[k + '.dh3a_ee'])}, {pm(d[k + '.dh3b'], d[k + '.dh3b_ee'])}")
            out.append("| " + " | ".join(fila) + " |")
    return out


def tabla_sesgo():
    out = ["| Semilla | Series | `base` en los primeros 2000 ticks: media ± ee, p5 | Comprar y mantener: media ± ee | `max_media` menos `base` |",
           "|---|---|---|---|---|"]
    for s in (0, 2):
        d = D[s]
        for lado, nombre in (("interiores", "interiores (las que deja el filtro)"), ("excluidas", "excluidas por el filtro")):
            k = f"s{s}.n20000.sesgo.prefijo2000.{lado}"
            out.append(f"| {s} | {nombre}, {d[k + '.n']:.0f} | {d[k + '.base_media']:.0f} ± {d[k + '.base_ee']:.0f}, {d[k + '.base_p5']:.0f} | "
                       f"{d[k + '.byh_media']:.0f} ± {d[k + '.byh_ee']:.0f} | {d[k + '.mm_dif']:+.0f} ± {d[k + '.mm_dif_ee']:.0f} |")
    return out


def tabla_bordes():
    out = ["| Conjunto, semilla 0 | Tocan 1 | Mínimo de 20 o menos | Tocan 255 | Ticks con precio de 20 o menos | Ticks con precio de 5 o menos | "
           "Series con más del 10 % de la ronda en la zona de los límites | Racha más larga pegada a un límite (media) |", "|---|---|---|---|---|---|---|---|"]
    d = D[0]
    for largo in (2000, 20000):
        for conj in ("remuestreo", "plausibles", "estres", "evidencia"):
            k = f"s0.n{largo}.bordes.{conj}"
            out.append(f"| {conj}, {largo} ticks | {num(d[k + '.toca1_pct'], 1)} % | {num(d[k + '.min20_pct'], 1)} % | {num(d[k + '.toca255_pct'], 1)} % | "
                       f"{num(d[k + '.ticks_hasta20_pct'], 2)} % | {num(d[k + '.ticks_hasta5_pct'], 2)} % | {num(d[k + '.series_pegadas_pct'], 1)} % | "
                       f"{num(d[k + '.racha_media_borde'], 0)} ticks |")
    return out


def tabla_error_p5():
    informado = {0: {"max_media": (0.015, 0.022), "kalman": (0.015, 0.026), "activo": (0.019, 0.028), "guardia": (0.016, 0.026), "prudente": (0.015, 0.026)},
                 2: {"max_media": (0.016, 0.021), "kalman": (0.016, 0.025), "activo": (0.018, 0.028), "guardia": (0.017, 0.018), "prudente": (0.015, 0.023)}}
    val = {0: {"max_media": (0.047, 0.039), "kalman": (0.052, 0.028), "activo": (0.005, -0.022), "guardia": (-0.025, -0.072), "prudente": (-0.108, -0.106)},
           2: {"max_media": (0.042, 0.017), "kalman": (0.042, 0.000), "activo": (-0.002, -0.033), "guardia": (-0.031, -0.067), "prudente": (-0.108, -0.100)}}
    out = ["| Candidato contra `base` | H3a, estudio: semilla 0, semilla 2 | H3a, auditoría: semilla 0, semilla 2 | H3b, estudio: semilla 0, semilla 2 | "
           "H3b, auditoría: semilla 0, semilla 2 |", "|---|---|---|---|---|"]
    razones = []
    for c in CANDS:
        fila = [f"`{c}`"]
        for q, lect in ((0, "dp5a3"), (1, "dp5b3")):
            fila.append(", ".join(pm(val[s][c][q], informado[s][c][q]) for s in (0, 2)))
            mios = []
            for s in (0, 2):
                k = f"s{s}.n2000.todas.evidencia.{c}.mixto.G10.{lect}"
                mios.append(pm(D[s][k], D[s][k + "_ee"]))
                razones.append(informado[s][c][q] / D[s][k + "_ee"])
            fila.append(", ".join(mios))
        out.append("| " + " | ".join(fila) + " |")
    return out, sum(razones) / len(razones)


def escribir_tablas():
    L = ["# Tablas de la auditoría del arnés de retorno", "",
         "Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.",
         "Arquitectura de Computadores, Universidad de los Andes, 2026-2.", "",
         "Generado por `auditoria/informe.py` con el evaluador independiente (`auditoria/indep.c`). Los puntos esperados son exactos "
         "(no hay sorteo de campos) y su error es el error estándar entre series. `kalman` y `guardia` son externos: su patrimonio por "
         "serie viene del arnés.", ""]
    L += ["## 1. Campos de rivales más fuertes, rondas de 2000 ticks", "",
          "Conjunto evidencia (10 000 series), G = 10. Primera columna: puntos esperados de la regla base. Las demás: diferencia de "
          "puntos esperados contra la base, H3a y H3b, con su error.", ""]
    for s in (2, 0):
        L += [f"Semilla {s}:", ""] + tabla_campos(s, 2000, "todas") + [""]
    L += ["Contra `max_media`, semilla 2:", ""] + tabla_campos_mm(2, 2000, "todas") + [""]
    L += ["Contra `max_media`, semilla 0:", ""] + tabla_campos_mm(0, 2000, "todas") + [""]
    L += ["## 2. Campos más fuertes, rondas de 20 000 ticks (series interiores)", ""]
    for s in (2, 0):
        L += [f"Semilla {s}:", ""] + tabla_campos(s, 20000, "int") + [""]
    L += ["## 3. Criterio de corte recalculado", "",
          "En cuántas combinaciones de campo y G pasa cada candidata, con las cifras de la auditoría: la media de los puntos mejora en "
          "más de dos errores y el percentil 5 de la competencia de tres rondas no baja en más de dos errores, en H3a y en H3b. El error "
          "del percentil 5 es el de la auditoría (10 lotes de series), más chico que el del estudio.", ""]
    L += tabla_veredictos() + [""]
    L += ["## 4. Rondas de 20 000 ticks: tres vistas", "",
          "Diferencia contra la regla base en el conjunto evidencia, campo mixto, G = 10. Interiores: solo las series que nunca salen de "
          "21 a 249 (selecciona por la trayectoria completa). Todas: sin filtrar (incluye las series pegadas al precio 1). Parada: todas "
          "las series, cada una hasta el primer precio fuera de 21 a 249 (mínimo 200 ticks); no mira el futuro y deja rondas de largo "
          f"medio {D[2]['s2.n20000.sesgo.parada.largo_medio']:.0f} ticks.", ""]
    L += tabla_vistas() + [""]
    L += ["## 5. Cuánto selecciona el filtro de interiores", "",
          "Los primeros 2000 ticks de las series de 20 000 ticks de la evidencia, separadas según si la serie completa queda dentro de "
          "21 a 249. Si el filtro no seleccionara, las dos filas de cada semilla serían iguales.", ""]
    L += tabla_sesgo() + [""]
    L += ["## 6. Límites 1 y 255", ""] + tabla_bordes() + [""]
    t, razon = tabla_error_p5()
    L += ["## 7. Error del percentil 5 de la competencia de tres rondas", "",
          "Diferencia del percentil 5 contra la regla base, 2000 ticks, campo mixto, G = 10. El estudio estima el error por remuestreo "
          "dentro de cada reparto en tríos y avisa que es conservador. La auditoría lo estima con 10 lotes disjuntos de series. "
          f"El error del estudio es en promedio {num(razon, 1)} veces el de la auditoría.", ""]
    L += t + [""]
    with open(os.path.join(MED, "auditoria_tablas.md"), "w", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def main():
    tot, fallas = escribir_cifras()
    escribir_tablas()
    n = sum(v[0] for v in tot.values())
    ok = sum(v[1] for v in tot.values())
    print(f"auditoria_cifras.txt: {ok} de {n} cifras coinciden "
          f"(exactas {tot['exacta'][1]}/{tot['exacta'][0]}, torneo {tot['torneo'][1]}/{tot['torneo'][0]}, p5 {tot['p5'][1]}/{tot['p5'][0]})")
    for tabla, cifra, s, inf, obt, tipo in fallas:
        print(f"  NO coincide [{tabla}] {cifra}, semilla {s}: informado {fmt(inf)}, obtenido {fmt(obt)} ({tipo})")
    print("auditoria_tablas.md escrito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
