#!/usr/bin/env python3
"""tablas.py: tablas principales del estudio de retorno, en Markdown.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 factibilidad/retorno/pruebas/tablas.py --semilla 0 > mediciones/tablas_s0.md

No calcula nada por su cuenta: pide los números al arnés (`retorno resumen`)
y lee los archivos que deja `retorno hipotesis --tsv` en build/tsv. Sirve
para que las tablas del README salgan de un comando y no de copiar a mano.
`make exploracion` y `make final` lo corren después de generar esos archivos.
"""
import argparse
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
ARNES = os.path.join(RETORNO, "build", "retorno")
TSV = os.path.join(RETORNO, "build", "tsv")

CANDIDATOS = ["base", "max_media", "guardia", "guardia_tope", "prudente", "kalman", "kalman_base", "activo", "base_guardia",
              "base_tope", "base_fuerte", "prud_guardia", "guardia_tope_r", "base_tope_r"]
PRINCIPALES = ["base", "max_media", "guardia", "guardia_tope", "prudente", "kalman", "activo"]
CAMPOS = ("ingenuo", "mixto", "fuerte")
GS = (5, 10, 15)
VISTAS = [(2000, "todas", "2000 ticks"), (20000, "interiores", "20 000 ticks, interiores"), (20000, "todas", "20 000 ticks, todas")]


def ent(x):
    """Entero con separador de miles: 10 868."""
    return f"{round(x):,}".replace(",", " ")


def sig(x):
    return ("+" if x >= 0 else "-") + ent(abs(x))


def dec(x, d=3, signo=False):
    t = f"{x:+.{d}f}" if signo else f"{x:.{d}f}"
    return t.replace(".", ",")


def pm(x, e):
    return f"{sig(x)} ± {ent(e)}"


def pmd(x, e, d=3):
    return f"{dec(x, d, True)} ± {dec(e, d)}"


def resumen(conjunto, largo, semilla, interior=False, candidatos=CANDIDATOS):
    """{candidato: {columna: valor}} del comando `resumen` del arnés."""
    cmd = [ARNES, "resumen", "--conjunto", conjunto, "--largo", str(largo), "--semilla", str(semilla), "--estrategia",
           ",".join(candidatos)] + (["--interior"] if interior else [])
    lineas = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.splitlines()
    columnas = lineas[0].split("candidato", 1)[1].split()
    salida = {}
    for linea in lineas[1:]:
        c = linea.split()
        salida[c[0]] = dict(zip(columnas, map(float, c[1:])))
    return salida


def leer_tsv(largo, series, semilla):
    """{(conjunto, candidato): {clave: valor}} de un archivo de `hipotesis --tsv`."""
    ruta = os.path.join(TSV, f"hipotesis_n{largo}_{series}_s{semilla}.tsv")
    datos = {}
    with open(ruta) as f:
        next(f)
        for linea in f:
            _, _, _, conjunto, candidato, clave, valor = linea.rstrip("\n").split("\t")
            datos.setdefault((conjunto, candidato), {})[clave] = float(valor)
    return datos


def tabla(cabecera, filas):
    print("| " + " | ".join(cabecera) + " |")
    print("|" + "|".join("---" for _ in cabecera) + "|")
    for f in filas:
        print("| " + " | ".join(str(x) for x in f) + " |")
    print()


def orden(datos, clave, conjunto="evidencia", candidatos=CANDIDATOS):
    return sorted(candidatos, key=lambda c: -datos[(conjunto, c)][clave])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tablas del estudio de retorno en Markdown")
    ap.add_argument("--semilla", type=int, default=0)
    a = ap.parse_args(argv)
    s = a.semilla
    nombre = {0: "exploración", 2: "reservada de este tramo"}.get(s, "otra")
    print(f"# Tablas del estudio de retorno, semilla {s} ({nombre})\n")
    print("Generado por `pruebas/tablas.py` con los números del arnés. Patrimonios con caja inicial 10 000 y comisión 5.")
    print("Las diferencias son pareadas contra la regla base, serie por serie, con su error estándar.")
    print("Interiores: series cuyo precio se queda siempre entre 21 y 249.\n")

    # ---- 1. Frontera -----------------------------------------------------------------------------
    print("## 1. Frontera en los dos horizontes\n")
    blo = resumen("bloques", 2000, s)
    rem, pla, est = (resumen(c, 2000, s) for c in ("remuestreo", "plausibles", "estres"))
    print(f"Rondas de 2000 ticks: 10 bloques de práctica, {ent(rem['base']['n'])} remuestreos, {ent(pla['base']['n'])} series "
          f"plausibles y {ent(est['base']['n'])} de estrés.\n")
    tabla(["Candidato", "Bloques: media, peor", "Remuestreo: media, dif., p5", "Plausibles: media, dif., p5", "Estrés: p5, peor"],
          [[f"`{c}`", f"{ent(blo[c]['media'])}, {ent(blo[c]['peor'])}",
            f"{ent(rem[c]['media'])}, {pm(rem[c]['dif'], rem[c]['ee'])}, {ent(rem[c]['p5'])}",
            f"{ent(pla[c]['media'])}, {pm(pla[c]['dif'], pla[c]['ee'])}, {ent(pla[c]['p5'])}",
            f"{ent(est[c]['p5'])}, {ent(est[c]['peor'])}"] for c in CANDIDATOS])
    pra = resumen("practica", 20000, s)
    for interior, titulo in ((True, "series interiores"), (False, "todas las series")):
        rem, pla, est = (resumen(c, 20000, s, interior) for c in ("remuestreo", "plausibles", "estres"))
        print(f"Rondas de 20 000 ticks, {titulo}: la serie de práctica completa (una sola serie), {ent(rem['base']['n'])} "
              f"remuestreos, {ent(pla['base']['n'])} plausibles y {ent(est['base']['n'])} de estrés.\n")
        tabla(["Candidato", "Práctica completa", "Remuestreo: media, mediana, dif., p5", "Plausibles: media, mediana, dif., p5",
               "Estrés: mediana, p5"],
              [[f"`{c}`", ent(pra[c]["media"]),
                f"{ent(rem[c]['media'])}, {ent(rem[c]['mediana'])}, {pm(rem[c]['dif'], rem[c]['ee'])}, {ent(rem[c]['p5'])}",
                f"{ent(pla[c]['media'])}, {ent(pla[c]['mediana'])}, {pm(pla[c]['dif'], pla[c]['ee'])}, {ent(pla[c]['p5'])}",
                f"{ent(est[c]['mediana'])}, {ent(est[c]['p5'])}"] for c in CANDIDATOS])

    # ---- 2. Qué cambia al alargar la ronda ----------------------------------------------------------
    print("## 2. Qué cambia al alargar la ronda\n")
    print("Conjunto evidencia (remuestreo y plausibles, mitad y mitad). Crecimiento: media geométrica del patrimonio final,")
    print("llevada a 2000 ticks (a 20 000 ticks es la raíz décima). Órdenes: promedio por cada 2000 ticks. Pausa y tope:")
    print("porcentaje de series en que la guardia llegó a pausar y en que saltó el tope de pérdida. Vetado: porcentaje de")
    print("ticks sin poder entrar.\n")
    ev = {(n, ser): resumen("evidencia", n, s, ser == "interiores") for n, ser, _ in VISTAS}
    filas = []
    for c in CANDIDATOS:
        fila = [f"`{c}`"]
        for n, ser, _ in VISTAS:
            x = ev[(n, ser)][c]
            crec = (x["geom"] / 10000) ** (2000 / n)
            fila.append(f"{dec(100 * (crec - 1), 2, True)} %, {dec(x['ordenes'] * 2000 / n, 1)}")
        for n, ser, _ in VISTAS[:2]:
            x = ev[(n, ser)][c]
            fila.append(f"{dec(100 * x['pausa'], 1)} %, {dec(100 * x['tope'], 1)} %, {dec(100 * x['vetado'], 1)} %")
        filas.append(fila)
    tabla(["Candidato"] + [f"{t}: crecimiento, órdenes" for _, _, t in VISTAS] +
          [f"{t}: pausa, tope, vetado" for _, _, t in VISTAS[:2]], filas)

    # ---- 3. Hipótesis --------------------------------------------------------------------------------
    H = {(n, ser): leer_tsv(n, ser, s) for n, ser, _ in VISTAS}
    todos = CANDIDATOS + ["nada", "byh"]
    print("## 3. Las hipótesis de puntaje\n")
    print("Conjunto evidencia, campo mixto, G = 10 rivales. H1: patrimonio. H2: exceso sobre comprar y mantener, como")
    print("diferencia y como razón W/B&H. H3a y H3b: puntos de 0 a 2 en una ronda, lineales en el patrimonio o en el puesto.")
    print("H3s y H3r: puntos sobre la suma del patrimonio y sobre la suma de W/B&H de las tres rondas. `nada` es no operar y")
    print("`byh` es comprar 63 siempre.\n")
    for n, ser, titulo in VISTAS:
        d = H[(n, ser)]
        print(f"Rondas de {titulo} ({ent(d[('evidencia', 'base')]['n'])} series):\n")
        tabla(["Candidato", "H1: media ± ee, p5, peor", "H2: exceso medio, p5", "H2: W/B&H media, mediana, p5",
               "H3a: media ± ee", "H3b: media ± ee", "H3s", "H3r"],
              [[f"`{c}`", f"{ent(x['h1_media'])} ± {ent(x['h1_ee'])}, {ent(x['h1_p5'])}, {ent(x['h1_peor'])}",
                f"{sig(x['h2_media'])}, {sig(x['h2_p5'])}",
                f"{dec(x['h2r_media'])}, {dec(x['h2r_mediana'])}, {dec(x['h2r_p5'])}",
                f"{dec(x['h3a_media'])} ± {dec(x['h3a_ee'])}", f"{dec(x['h3b_media'])} ± {dec(x['h3b_ee'])}",
                dec(x["h3s_media"]), dec(x["h3r_media"])] for c in todos for x in [d[("evidencia", c)]]])

    print("### Orden de los candidatos según la hipótesis\n")
    criterios = [("H1, media", "h1_media"), ("H1, percentil 5", "h1_p5"), ("H2, razón W/B&H media", "h2r_media"),
                 ("H2, razón mediana", "h2r_mediana"), ("H3a, puntos esperados", "h3a_media"),
                 ("H3b, puntos esperados", "h3b_media"), ("H3s, suma de patrimonio", "h3s_media"),
                 ("H3r, suma de razones", "h3r_media"), ("H3a, p5 de tres rondas", "h3a_c_p5"),
                 ("H3b, p5 de tres rondas", "h3b_c_p5")]
    for n, ser, titulo in VISTAS:
        d = H[(n, ser)]
        print(f"Rondas de {titulo}. El orden por exceso medio de H2 es el mismo de la media de H1.\n")
        tabla(["Hipótesis", "1.º", "2.º", "3.º", "4.º", "5.º", "Puesto de `base`"],
              [[t] + [f"`{c}`" for c in orden(d, k)[:5]] + [str(orden(d, k).index("base") + 1)] for t, k in criterios])

    # ---- 4. Puntos contra la regla base ---------------------------------------------------------------
    print("## 4. Cuánto vale en puntos pasar de la regla base a cada candidato\n")
    print("Conjunto evidencia, campo mixto, G = 10. Diferencia de puntos esperados en una ronda (que es también la de la")
    print("competencia) y diferencia del percentil 5 de los puntos de una competencia de tres rondas.\n")
    for n, ser, titulo in VISTAS:
        d = H[(n, ser)]
        b = d[("evidencia", "base")]
        print(f"Rondas de {titulo}. La regla base saca {dec(b['h3a_media'])} puntos con H3a y {dec(b['h3b_media'])} con H3b; "
              f"su percentil 5 de tres rondas es {dec(b['h3a_c_p5'])} y {dec(b['h3b_c_p5'])}.\n")
        tabla(["Candidato", "H3a: puntos esperados", "H3a: p5 de tres rondas", "H3b: puntos esperados", "H3b: p5 de tres rondas",
               "H3s: esperados", "H3r: esperados", "H1: patrimonio"],
              [[f"`{c}`", pmd(x["d_h3a"], x["d_h3a_ee"]), pmd(x["d_h3a_c_p5"], x["d_h3a_c_p5_ee"]),
                pmd(x["d_h3b"], x["d_h3b_ee"]), pmd(x["d_h3b_c_p5"], x["d_h3b_c_p5_ee"]), pmd(x["d_h3s"], x["d_h3s_ee"]),
                pmd(x["d_h3r"], x["d_h3r_ee"]), pm(x["h1_dif"], x["h1_dif_ee"])]
               for c in todos if c != "base" for x in [d[("evidencia", c)]]])

    # ---- 5. Sensibilidad -------------------------------------------------------------------------------
    print("## 5. Sensibilidad al campo de rivales y a G\n")
    print("Conjunto evidencia. Puntos esperados de la regla base y diferencia de cada candidato contra ella.\n")
    for clave, titulo_h in (("h3a", "H3a, lineal en patrimonio"), ("h3b", "H3b, lineal en el puesto")):
        for n, ser, titulo in VISTAS[:2]:
            d = H[(n, ser)]
            print(f"{titulo_h}. Rondas de {titulo}.\n")
            cab = ["Candidato"] + [f"{campo}, G={G}" for campo in CAMPOS for G in GS]
            filas = [["`base` (puntos)"] + [dec(d[("evidencia", "base")][f"sens_{clave}_{campo}_{G}"])
                                            for campo in CAMPOS for G in GS]]
            for c in PRINCIPALES[1:]:
                x = d[("evidencia", c)]
                filas.append([f"`{c}`"] + [dec(x[f"dsens_{clave}_{campo}_{G}"], 3, True) for campo in CAMPOS for G in GS])
            tabla(cab, filas)
    ee = max(H[(n, ser)][("evidencia", c)][f"dsens_{clave}_{campo}_{G}_ee"] for n, ser, _ in VISTAS[:2] for c in PRINCIPALES[1:]
             for clave in ("h3a", "h3b") for campo in CAMPOS for G in GS)
    print(f"El error estándar de cada diferencia de estas tablas es a lo más {dec(ee)}.\n")

    # ---- 6. Por conjunto ---------------------------------------------------------------------------------
    print("## 6. Puntos esperados por conjunto\n")
    print("Campo mixto, G = 10. Puntos H3a y H3b de la regla base y diferencia de los candidatos principales.\n")
    for n, ser, titulo in VISTAS:
        d = H[(n, ser)]
        cab = ["Candidato"] + [f"{conj}: H3a, H3b" for conj in ("remuestreo", "plausibles", "estres")]
        filas = [["`base` (puntos)"] + [f"{dec(d[(conj, 'base')]['h3a_media'])}, {dec(d[(conj, 'base')]['h3b_media'])}"
                                        for conj in ("remuestreo", "plausibles", "estres")]]
        for c in PRINCIPALES[1:]:
            filas.append([f"`{c}`"] + [f"{pmd(d[(conj, c)]['d_h3a'], d[(conj, c)]['d_h3a_ee'])}, "
                                       f"{pmd(d[(conj, c)]['d_h3b'], d[(conj, c)]['d_h3b_ee'])}"
                                       for conj in ("remuestreo", "plausibles", "estres")])
        print(f"Rondas de {titulo}.\n")
        tabla(cab, filas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
