#!/usr/bin/env python3
"""v5_causal.py: arista 11 de la sección 15 (docs/exploracion_ideas.md). (a) Prueba causal: cambiar el futuro no
cambia las decisiones pasadas; (b) traslape de las ventanas; (c) independencia de los sorteos.
Salida: docs/mediciones/exploracion/v5_causal.txt.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso (con export P4_DATOS=~/proyectos/datos_p4): python3 ref/cotas/v5_causal.py
"""
import sys, time, os, random, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorar_v5 as X, v5 as V, explorar_regimen as XR, explorar_clon as XC, ideas, candado_v4 as C4
c = X.Ctx()
vent = c.D.ventanas
SAL = ["# V5, arista 11: revisión de la medición", "", "ref/cotas/v5_causal.py. Otras acciones: 12 000 ventanas.", ""]


def di(x):
    print(x)
    SAL.append("- " + x)

rng = random.Random(11)
# (a) referencia directa de V4b (candado_v4.V4 en ideas.correr) y v5.post: bytes hasta el corte t con el futuro cambiado
class Graba:
    def __init__(self, s):
        self.s, self.b = s, []
    def decidir(self, p, caja, acc):
        d = self.s.decidir(p, caja, acc)
        self.b.append(d)
        return d
def bytes_v4b(w):
    g = Graba(C4.V4(V.V3B, ("E1", None, None), 100, None, False, True, "copiar"))
    ideas.correr(w, g)
    return g.b
def bytes_v5(w):
    pre = V.precalcular(w)
    tr = []
    V.post(w, pre, V.fase_a(w, pre), {"b40": V.rival(w, "b40")}, None, tr)
    return pre["tA"], tr
mal = casos = 0
malv5 = 0
for k in range(40):
    i, j = rng.randrange(c.n), rng.randrange(c.n)
    w = vent[i]
    t = rng.randrange(500, 19500)
    # futuro distinto: el sufijo de otra ventana (sigue entre 100 y 255); el pasado queda igual
    w2 = w[:t + 1] + vent[j][t + 1:]
    b1, b2 = bytes_v4b(w), bytes_v4b(w2)
    casos += 1
    mal += b1[:t + 1] != b2[:t + 1]
    tA1, t1 = bytes_v5(w)
    try:
        tA2, t2 = bytes_v5(w2)
    except Exception as e:
        continue   # el sufijo cambiado puede dejar la ventana sin un extremo: v5.precalcular lo necesita
    if tA1 <= t and tA2 == tA1:
        a = [x for x in t1 if x[0] <= t]
        b = [x for x in t2 if x[0] <= t]
        malv5 += a != b
di(f"(a) causal: {casos} ventanas con el futuro cambiado después de un tick al azar; referencia directa de V4b con bytes "
      f"distintos hasta el corte: {mal}; v5.post con bytes distintos hasta el corte: {malv5}")
# (b) traslape
por_emp = collections.defaultdict(list)
for f in c.D.filas:
    por_emp[f[0]].append(f[1])
tras = []
for emp, ini in por_emp.items():
    ini.sort()
    for a, b in zip(ini, ini[1:]):
        tras.append(max(0, 20000 - (b - a)) / 20000)
import statistics
cub = []
for emp, ini in por_emp.items():
    marcas = collections.Counter()
    for s in ini:
        for blk in range(s // 1000, (s + 20000) // 1000):
            marcas[blk] += 1
    cub.append(statistics.mean(marcas.values()))
di(f"(b) traslape: {len(por_emp)} empresas, {len(c.D.filas)} ventanas; fracción de traslape con la ventana siguiente de la misma "
      f"empresa: media {statistics.mean(tras):.2f}, mediana {statistics.median(tras):.2f}; cada minuto de una empresa cae en "
      f"{statistics.mean(cub):.1f} ventanas en promedio")
di("grupos para el error estándar: " + ", ".join(f"{k} {len(set(v))}" for k, v in c.G.items()))
# (c) sorteos
tr = XC.sorteos(list(range(c.n)), "todas", XC.SORTEOS)
rep = sum(1 for a, b, d in tr if a == b or b == d or a == d)
misma = sum(1 for a, b, d in tr if c.D.filas[a][0] == c.D.filas[b][0] or c.D.filas[b][0] == c.D.filas[d][0] or c.D.filas[a][0] == c.D.filas[d][0])
def cerca(a, b):
    return abs(c.D.dia[a] - c.D.dia[b]) < 52
fechas = sum(1 for a, b, d in tr if cerca(a, b) or cerca(b, d) or cerca(a, d))
di(f"(c) sorteos: {len(tr)} torneos; con una ventana repetida {100 * rep / len(tr):.3f} %; con dos ventanas de la misma empresa "
      f"{100 * misma / len(tr):.1f} %; con dos ventanas cuyas fechas se traslapan (inicios a menos de 52 días hábiles) {100 * fechas / len(tr):.1f} %")

open(os.path.join(X.SALIDA, "v5_causal.txt"), "w").write("\n".join(SAL) + "\n")
