#!/usr/bin/env python3
# explorar.py: corre las variantes del fondo en el arnés y arma las tablas del estudio.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Estudio de retorno 4, parte B. Todo con la semilla 0 (exploración). Las
# semillas 2 y 3 son reservadas y este script se niega a usarlas.
#
#   --fase exploracion   todas las variantes a 2000 ticks (comando hipotesis, referencia max_media)
#   --fase largo         la lista corta a 20 000 ticks: interiores, todas y parada
#   --fase veredictos    criterio de corte oficial (veredicto --parada) de las candidatas
#   --fase tablas        mediciones/tablas.md a partir de los .tsv guardados
#
# Cada fila de las tablas es la diferencia pareada contra max_media con su
# error estándar, en el campo mixto con G = 10 rivales.
import argparse
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ARNES = os.path.join(AQUI, "build", "arnes")
MED = os.path.join(AQUI, "mediciones")
BUILD = os.path.join(AQUI, "build")
SEMILLA = 0
REF = "max_media"


def f(c, w, extra=""):
    """Especificación de un fondo: conjunto, pesos (tupla) y el resto de los parámetros."""
    pesos = ",".join("w%d=%d" % (k, x) for k, x in enumerate(w))
    return "fondo:c=%d,%s%s" % (c, pesos, "," + extra if extra else "")


# Variantes de la exploración: (grupo, etiqueta, especificación). Lista fijada antes de mirar resultados.
VARIANTES = []


def agrega(grupo, etiqueta, spec):
    VARIANTES.append((grupo, etiqueta, spec))


NOMBRE_CONJ = {1: "mm+prud+byh", 2: "mm+guar+byh", 3: "mm+kal+act", 4: "mm+base+prud", 5: "mm+base+act"}
# (c) pesos fijos, mismo tick, banda 1/16
for c, lista in ((1, [(12, 2, 2), (12, 4, 0), (12, 0, 4), (14, 0, 2), (14, 2, 0), (8, 4, 4), (8, 0, 8)]),
                 (2, [(12, 2, 2), (12, 4, 0), (8, 4, 4), (8, 8, 0)]),
                 (3, [(12, 2, 2), (12, 4, 0), (12, 0, 4), (10, 3, 3), (8, 4, 4), (8, 8, 0), (8, 0, 8), (6, 5, 5), (4, 6, 6),
                      (0, 8, 8)]),
                 (4, [(12, 2, 2), (12, 4, 0), (8, 4, 4)])):
    for w in lista:
        agrega("fijos", "%s %d/%d/%d" % (NOMBRE_CONJ[c], *w), f(c, w))
# banda de no operar
for b in (0, 2, 4):
    agrega("banda", "mm+kal+act 8/4/4 banda %d" % b, f(3, (8, 4, 4), "b=%d" % b))
    agrega("banda", "mm+prud+byh 12/2/2 banda %d" % b, f(1, (12, 2, 2), "b=%d" % b))
# desfase de un tick
agrega("desfase", "max_media sola, tick anterior", f(1, (16, 0, 0), "df=1"))
agrega("desfase", "mm+kal+act 8/4/4, tick anterior", f(3, (8, 4, 4), "df=1"))
agrega("desfase", "mm+kal+act 6/5/5, tick anterior", f(3, (6, 5, 5), "df=1"))
agrega("desfase", "mm+prud+byh 12/2/2, tick anterior", f(1, (12, 2, 2), "df=1"))
# voto: todo o nada
agrega("voto", "mm+kal+act 6/5/5 voto 2 de 3", f(3, (6, 5, 5), "vt=8"))
agrega("voto", "mm+kal+act 8/4/4 voto >= 8", f(3, (8, 4, 4), "vt=8"))
agrega("voto", "mm+base+prud 6/5/5 voto 2 de 3", f(4, (6, 5, 5), "vt=8"))
agrega("voto", "mm+prud+byh 6/5/5 voto 2 de 3", f(1, (6, 5, 5), "vt=8"))
# (a) líder con histéresis
for c in (1, 2, 3, 4):
    agrega("lider", "%s lider acumulado, margen 1/64" % NOMBRE_CONJ[c], f(c, (16, 0, 0), "m=1,v=0,mg=6"))
    agrega("lider", "%s lider ventana 512, margen 1/64" % NOMBRE_CONJ[c], f(c, (16, 0, 0), "m=1,v=9,mg=6"))
agrega("lider", "mm+prud+byh lider acumulado, margen 1/16", f(1, (16, 0, 0), "m=1,v=0,mg=4"))
agrega("lider", "mm+prud+byh lider ventana 256, margen 1/64", f(1, (16, 0, 0), "m=1,v=8,mg=6"))
agrega("lider", "mm+kal+act lider ventana 512, margen 1/256", f(3, (16, 0, 0), "m=1,v=9,mg=8"))
agrega("lider", "mm+kal+act lider acumulado, margen 1/16", f(3, (16, 0, 0), "m=1,v=0,mg=4"))
agrega("lider", "mm+base+prud lider acumulado 1/32, papel por accion", f(4, (16, 0, 0), "m=1,v=0,mg=5,pp=1"))
agrega("lider", "mm+base+prud lider acumulado 1/32, papel por accion, tick anterior", f(4, (16, 0, 0), "m=1,v=0,mg=5,pp=1,df=1"))
agrega("lider", "mm+kal+act lider ventana 512 1/64, papel por accion", f(3, (16, 0, 0), "m=1,v=9,mg=6,pp=1"))
agrega("lider", "mm+prud+byh lider acumulado 1/32, papel por accion", f(1, (16, 0, 0), "m=1,v=0,mg=5,pp=1"))
# (d) pesos aprendidos con prior fuerte
agrega("aprende", "mm+prud+byh 12/2/2 aprende v=512 1/64 d=4", f(1, (12, 2, 2), "m=2,v=9,mg=6,d=4"))
agrega("aprende", "mm+prud+byh 12/2/2 aprende v=256 1/64 d=4", f(1, (12, 2, 2), "m=2,v=8,mg=6,d=4"))
agrega("aprende", "mm+prud+byh 12/2/2 aprende v=512 1/64 d=2", f(1, (12, 2, 2), "m=2,v=9,mg=6,d=2"))
agrega("aprende", "mm+prud+byh 12/2/2 aprende v=512 1/256 d=4", f(1, (12, 2, 2), "m=2,v=9,mg=8,d=4"))
agrega("aprende", "mm+guar+byh 12/2/2 aprende v=512 1/64 d=4", f(2, (12, 2, 2), "m=2,v=9,mg=6,d=4"))
agrega("aprende", "mm+kal+act 8/4/4 aprende v=512 1/64 d=4", f(3, (8, 4, 4), "m=2,v=9,mg=6,d=4"))
agrega("aprende", "mm+kal+act 8/4/4 aprende v=256 1/128 d=4 paso 2", f(3, (8, 4, 4), "m=2,v=8,mg=7,d=4,ps=2"))
agrega("aprende", "mm+kal+act 6/5/5 aprende v=512 1/64 d=5", f(3, (6, 5, 5), "m=2,v=9,mg=6,d=5"))
# (e) ancla fija en comprar y mantener, el resto aprende
agrega("ancla", "mm+prud+byh 10/2/4 ancla 4/16, aprende el resto", f(1, (10, 2, 4), "m=2,v=9,mg=6,d=2,fj=4"))
agrega("ancla", "mm+guar+byh 10/2/4 ancla 4/16, aprende el resto", f(2, (10, 2, 4), "m=2,v=9,mg=6,d=2,fj=4"))

# --- Segunda tanda, definida después de mirar la primera (semilla 0): la comisión fija castiga las órdenes
# parciales, así que se prueban las formas de no pagarlas (bandas anchas, voto con histéresis) y los
# gestores más baratos para el fondo mínimo (conjunto 5).
TANDA2 = len(VARIANTES)
for w, b in (((8, 4, 4), 3), ((8, 4, 4), 6), ((6, 5, 5), 4), ((6, 5, 5), 5), ((8, 8, 0), 4), ((10, 3, 3), 3), ((12, 2, 2), 2)):
    agrega("banda2", "mm+kal+act %d/%d/%d banda %d" % (*w, b), f(3, w, "b=%d" % b))
agrega("banda2", "mm+prud+byh 12/0/4 banda 4", f(1, (12, 0, 4), "b=4"))
agrega("banda2", "mm+prud+byh 14/0/2 banda 2", f(1, (14, 0, 2), "b=2"))
agrega("voto2", "mm+kal+act 6/5/5 entra con 1, sale con 0", f(3, (6, 5, 5), "vt=5,vs=0"))
agrega("voto2", "mm+kal+act 6/5/5 entra con 2, sale con 0", f(3, (6, 5, 5), "vt=10,vs=0"))
agrega("voto2", "mm+kal+act 6/5/5 entra con 3, sale con 1", f(3, (6, 5, 5), "vt=16,vs=6"))
agrega("voto2", "mm+kal+act 6/5/5 entra con 3, sale con 2", f(3, (6, 5, 5), "vt=16,vs=11"))
agrega("minimo", "mm+base+act 6/5/5 voto 2 de 3", f(5, (6, 5, 5), "vt=8"))
agrega("minimo", "mm+base+act 6/5/5 voto 2 de 3, tick anterior", f(5, (6, 5, 5), "vt=8,df=1"))
agrega("minimo", "mm+base+act 6/5/5 voto con pesos aprendidos, papel por accion", f(5, (6, 5, 5), "m=2,v=9,mg=5,d=4,pp=1,vt=8"))
agrega("minimo", "mm+base+act 6/5/5 voto con pesos aprendidos, papel por accion, tick anterior",
       f(5, (6, 5, 5), "m=2,v=9,mg=5,d=4,pp=1,vt=8,df=1"))
agrega("minimo", "mm+base+act 6/5/5 voto con pesos aprendidos v=256 1/64 paso 2", f(5, (6, 5, 5), "m=2,v=8,mg=6,d=4,ps=2,pp=1,vt=8"))
agrega("minimo", "mm+base+prud 6/5/5 voto con pesos aprendidos, papel por accion", f(4, (6, 5, 5), "m=2,v=9,mg=5,d=4,pp=1,vt=8"))
agrega("minimo", "mm+base+act lider acumulado 1/32, papel por accion", f(5, (16, 0, 0), "m=1,v=0,mg=5,pp=1"))
agrega("minimo", "mm+base+act lider acumulado 1/32, papel por accion, tick anterior", f(5, (16, 0, 0), "m=1,v=0,mg=5,pp=1,df=1"))
agrega("minimo", "mm+base+act 8/4/4 banda 1", f(5, (8, 4, 4)))
agrega("minimo", "mm+base+act 8/4/4 banda 4", f(5, (8, 4, 4), "b=4"))
agrega("minimo", "mm+base+act 8/4/4 banda 4, tick anterior", f(5, (8, 4, 4), "b=4,df=1"))

# Lista corta para 20 000 ticks y candidatas finales: se llena después de mirar la exploración (semilla 0).
CORTA = [
    "mm+kal+act 8/4/4", "mm+kal+act 8/4/4 banda 6", "mm+kal+act 6/5/5 banda 5", "mm+kal+act 8/8/0", "mm+kal+act 6/5/5 voto 2 de 3",
    "mm+kal+act 6/5/5 entra con 2, sale con 0", "max_media sola, tick anterior", "mm+prud+byh 12/2/2", "mm+prud+byh 14/0/2 banda 2",
    "mm+guar+byh 12/2/2", "mm+base+prud 12/2/2", "mm+prud+byh lider ventana 512, margen 1/64",
    "mm+kal+act lider ventana 512, margen 1/64", "mm+prud+byh 12/2/2 aprende v=512 1/64 d=4",
    "mm+prud+byh 10/2/4 ancla 4/16, aprende el resto", "mm+base+act lider acumulado 1/32, papel por accion",
    "mm+base+act 8/4/4 banda 4",
]
# Candidatas con nombre (alias registrados en fondo.c).
FINALES = ["fondo_rec", "fondo_rec_ant", "fondo_ancla", "fondo_min", "fondo_min_ant"]

VISTAS = {"interiores": ["--interior"], "todas": [], "parada": ["--parada"]}


def correr(args, salida):
    with open(salida, "w") as g:
        r = subprocess.run([ARNES] + args, stdout=g, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr)
        sys.exit("fallo: %s" % " ".join(args))


CLAVES = set("""n h1_media h1_p5 h1_dif h1_dif_ee h2_media h2_p5 h2r_media h2r_dif h2r_dif_ee h2r_p5 h3a_media h3b_media
h3a_c_p5 h3b_c_p5 d_h3a d_h3a_ee d_h3b d_h3b_ee d_h3a_c_p5 d_h3a_c_p5_ee d_h3b_c_p5 d_h3b_c_p5_ee d_h3s d_h3s_ee d_h3r d_h3r_ee
ordenes h1c_p5 d_h1c_p5 d_h1c_p5_ee h2c_p5 dsens_h3a_ingenuo_10 dsens_h3a_ingenuo_10_ee dsens_h3b_ingenuo_10
dsens_h3b_ingenuo_10_ee dsens_h3a_fuerte_10 dsens_h3a_fuerte_10_ee dsens_h3b_fuerte_10 dsens_h3b_fuerte_10_ee""".split())
FORZAR = False


def hipotesis(specs, largo, extra, base, vista=None):
    """Corre el comando hipotesis en tandas de a lo más 40 variantes y guarda un resumen por tanda.

    El resumen (mediciones/BASE_parteK.txt) tiene una línea por vista, conjunto y candidato, con las
    cifras que usan las tablas. Si ya existe no se vuelve a correr, salvo con --forzar."""
    rutas = []
    for i in range(0, len(specs), 40):
        tanda = specs[i:i + 40]
        nombre = "%s_parte%d" % (base, i // 40 + 1)
        resumen = os.path.join(MED, nombre + ".txt")
        rutas.append(resumen)
        if os.path.exists(resumen) and not FORZAR:
            continue
        tsv = os.path.join(BUILD, nombre + ".tsv.txt")
        correr(["hipotesis", "--largo", str(largo), "--semilla", str(SEMILLA), "--candidatos", ";".join([REF] + tanda), "--ref",
                REF, "--tsv", tsv] + extra, os.path.join(BUILD, nombre + ".salida.txt"))
        compactar(tsv, resumen, vista)
    return rutas


def compactar(tsv, resumen, vista=None):
    """`vista` corrige la columna de series: el arnés escribe "todas" también cuando se corre con --parada."""
    filas, orden = {}, []
    with open(tsv) as g:
        next(g)
        for linea in g:
            largo, semilla, series, conjunto, cand, clave, valor = linea.rstrip("\n").split("\t")
            if clave not in CLAVES:
                continue
            if vista:
                series = vista
            k = (largo, semilla, series, conjunto, cand)
            if k not in filas:
                filas[k] = []
                orden.append(k)
            filas[k].append("%s=%.6g" % (clave, float(valor)))
    with open(resumen, "w") as g:
        g.write("# comando hipotesis del arnes, referencia max_media: largo, semilla, series, conjunto, candidato, cifras\n")
        for k in orden:
            g.write("\t".join(k) + "\t" + " ".join(filas[k]) + "\n")


def leer_tsv(rutas):
    """datos[(series, conjunto, candidato)][clave] = valor"""
    datos = {}
    for ruta in rutas:
        with open(ruta) as g:
            for linea in g:
                if linea.startswith("#"):
                    continue
                largo, semilla, series, conjunto, cand, cifras = linea.rstrip("\n").split("\t")
                datos[(series, conjunto, cand)] = {c.split("=")[0]: float(c.split("=")[1]) for c in cifras.split(" ")}
    return datos


def pm(d, e, dec=3):
    return ("%+." + str(dec) + "f ± %." + str(dec) + "f") % (d, e)


def juicio(x):
    """Criterio de corte en una vista: H3a y H3b mejoran en más de 2 ee y su p5 de tres rondas no baja más de 2 ee."""
    ok = lit = True
    for h in ("h3a", "h3b"):
        d, e, dp, ep = x["d_" + h], x["d_%s_ee" % h], x["d_%s_c_p5" % h], x["d_%s_c_p5_ee" % h]
        ok = ok and d > 2 * e and dp >= -2 * ep
        lit = lit and d > 0 and dp >= 0
    return ("pasa" if ok else "no pasa") + (", literal pasa" if lit else ", literal no pasa")


def fila_md(etiqueta, x, x_est=None):
    celdas = [etiqueta, pm(x["h1_dif"], x["h1_dif_ee"], 0), "%.0f" % x["h1_p5"], "%+.0f" % x["h2_p5"],
              pm(x["h2r_dif"], x["h2r_dif_ee"]), pm(x["d_h3a"], x["d_h3a_ee"]), pm(x["d_h3b"], x["d_h3b_ee"]),
              pm(x["d_h3a_c_p5"], x["d_h3a_c_p5_ee"]), pm(x["d_h3b_c_p5"], x["d_h3b_c_p5_ee"]), "%.1f" % x["ordenes"], juicio(x)]
    if x_est is not None:
        celdas += [pm(x_est["h1_dif"], x_est["h1_dif_ee"], 0), pm(x_est["d_h3a"], x_est["d_h3a_ee"]),
                   pm(x_est["d_h3b"], x_est["d_h3b_ee"]), pm(x_est["d_h3a_c_p5"], x_est["d_h3a_c_p5_ee"])]
    return "| " + " | ".join(celdas) + " |"


CAB = ("| Variante | H1: patrimonio | H1: p5 | H2: p5 del exceso | H2: razón W/B&H | H3a: puntos | H3b: puntos | "
       "H3a: p5 de 3 rondas | H3b: p5 de 3 rondas | Órdenes | Criterio |")
CAB_EST = " Estrés H1 | Estrés H3a | Estrés H3b | Estrés H3a p5 de 3 rondas |"


def tabla(datos, series, pares, con_estres=True):
    """pares: lista de (etiqueta, nombre de candidato en el tsv)."""
    lineas = [CAB + (CAB_EST if con_estres else ""), "|" + "---|" * (11 + (4 if con_estres else 0))]
    ref = datos.get((series, "evidencia", REF))
    if ref:
        lineas.append("| `max_media` (nivel) | %.0f | %.0f | %+.0f | %.3f | %.3f | %.3f | %.3f | %.3f | %.1f | referencia |%s" % (
            ref["h1_media"], ref["h1_p5"], ref["h2_p5"], ref["h2r_media"], ref["h3a_media"], ref["h3b_media"], ref["h3a_c_p5"],
            ref["h3b_c_p5"], ref["ordenes"], " | | | |" if con_estres else ""))
    for etiqueta, cand in pares:
        x = datos.get((series, "evidencia", cand))
        if not x:
            continue
        lineas.append(fila_md(etiqueta, x, datos.get((series, "estres", cand)) if con_estres else None))
    return "\n".join(lineas)


def tabla_signos(datos, series, pares):
    """Signo por separado en remuestreo y en plausibles, y sensibilidad al campo."""
    lineas = ["| Variante | Remuestreo: H3a, H3b | Plausibles: H3a, H3b | Campo ingenuo: H3a, H3b | Campo fuerte: H3a, H3b |",
              "|---|---|---|---|---|"]
    for etiqueta, cand in pares:
        r, p, e = (datos.get((series, c, cand)) for c in ("remuestreo", "plausibles", "evidencia"))
        if not (r and p and e):
            continue
        lineas.append("| %s | %s, %s | %s, %s | %s, %s | %s, %s |" % (
            etiqueta, pm(r["d_h3a"], r["d_h3a_ee"]), pm(r["d_h3b"], r["d_h3b_ee"]), pm(p["d_h3a"], p["d_h3a_ee"]),
            pm(p["d_h3b"], p["d_h3b_ee"]), pm(e["dsens_h3a_ingenuo_10"], e["dsens_h3a_ingenuo_10_ee"]),
            pm(e["dsens_h3b_ingenuo_10"], e["dsens_h3b_ingenuo_10_ee"]), pm(e["dsens_h3a_fuerte_10"], e["dsens_h3a_fuerte_10_ee"]),
            pm(e["dsens_h3b_fuerte_10"], e["dsens_h3b_fuerte_10_ee"])))
    return "\n".join(lineas)


def archivos(prefijo):
    return sorted(os.path.join(MED, a) for a in os.listdir(MED) if a.startswith(prefijo) and "_parte" in a and a.endswith(".txt"))


def fase_tablas():
    s = ["# Tablas del estudio de retorno 4, parte B (fondo de estrategias)", "",
         "Generado por `explorar.py --fase tablas`. Semilla 0, campo mixto, G = 10. Cada celda es la diferencia pareada "
         "contra `max_media` con su error estándar. Órdenes: promedio por ronda. Criterio: el de corte, aplicado a esa vista "
         "(H3a y H3b mejoran en más de 2 errores y su percentil 5 de tres rondas no baja en más de 2 errores); "
         "`literal` mira solo el signo.", ""]
    d = leer_tsv(archivos("exploracion_n2000"))
    if d:
        s += ["## 1. Exploración a 2000 ticks, conjunto evidencia (10 000 series) y estrés (7000)", ""]
        for grupo in ("fijos", "banda", "banda2", "desfase", "voto", "voto2", "lider", "aprende", "ancla", "minimo"):
            pares = [(e, sp) for g, e, sp in VARIANTES if g == grupo]
            s += ["### Grupo: %s" % grupo, "", tabla(d, "todas", pares), ""]
        s += ["### Signo por evidencia y por campo de rivales (2000 ticks)", "",
              tabla_signos(d, "todas", [(e, sp) for g, e, sp in VARIANTES]), ""]
    for vista in ("interiores", "parada", "todas"):
        d = leer_tsv(archivos("largo_n20000_%s" % vista))
        if d:
            mapa = {e: sp for g, e, sp in VARIANTES}
            pares = [(e, mapa[e]) for e in CORTA if e in mapa] + [(n, n) for n in FINALES]
            s += ["## 20 000 ticks, vista %s" % vista, "", tabla(d, vista, pares, con_estres=(vista != "interiores")), ""]
            if vista != "todas":
                s += ["Signo por evidencia y por campo (20 000 ticks, %s):" % vista, "", tabla_signos(d, vista, pares), ""]
    d = leer_tsv(archivos("finales_n2000"))
    if d:
        pares = [(n, n) for n in FINALES]
        s += ["## Candidatas con nombre a 2000 ticks", "", tabla(d, "todas", pares), "", tabla_signos(d, "todas", pares), ""]
    with open(os.path.join(MED, "tablas.md"), "w") as g:
        g.write("\n".join(s) + "\n")
    print("mediciones/tablas.md: %d lineas, %d variantes probadas en la exploracion" % (len(s), len(VARIANTES)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fase", required=True, choices=["exploracion", "largo", "finales", "veredictos", "tablas", "lista"])
    ap.add_argument("--forzar", action="store_true", help="vuelve a correr aunque el resumen ya exista")
    a = ap.parse_args()
    global FORZAR
    FORZAR = a.forzar
    assert SEMILLA not in (2, 3), "las semillas 2 y 3 son reservadas"
    os.makedirs(MED, exist_ok=True)
    os.makedirs(BUILD, exist_ok=True)
    os.environ.setdefault("HILOS", "5")
    if a.fase == "lista":
        for g, e, sp in VARIANTES:
            print("%-8s %-70s %s" % (g, e, sp))
        print("%d variantes" % len(VARIANTES))
    elif a.fase == "exploracion":
        hipotesis([sp for g, e, sp in VARIANTES[:TANDA2]], 2000, [], "exploracion_n2000_t1")
        hipotesis([sp for g, e, sp in VARIANTES[TANDA2:]], 2000, [], "exploracion_n2000_t2")
        fase_tablas()
    elif a.fase == "largo":
        mapa = {e: sp for g, e, sp in VARIANTES}
        specs = [mapa[e] for e in CORTA] + FINALES
        for vista, extra in VISTAS.items():
            hipotesis(specs, 20000, extra, "largo_n20000_%s" % vista, vista)
        fase_tablas()
    elif a.fase == "finales":
        hipotesis(FINALES, 2000, [], "finales_n2000")
        fase_tablas()
    elif a.fase == "veredictos":
        for n in FINALES:
            correr(["veredicto", "--candidata", n, "--referencia", REF, "--semilla", str(SEMILLA), "--parada"],
                   os.path.join(MED, "veredicto_%s.txt" % n))
            with open(os.path.join(MED, "veredicto_%s.txt" % n)) as g:
                print(n, [l.strip() for l in g if l.startswith("VEREDICTO") or l.startswith("Veredicto literal")])
    else:
        fase_tablas()


if __name__ == "__main__":
    main()
