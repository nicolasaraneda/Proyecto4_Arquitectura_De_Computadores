#!/usr/bin/env python3
"""comparar_semillas.py: la semilla de exploración (0) contra la reservada (2), lado a lado.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 factibilidad/retorno/pruebas/comparar_semillas.py > mediciones/semillas_0_y_2.md

No calcula nada: lee los archivos que dejan `make exploracion` y `make final`
(build/tsv/hipotesis_*.tsv y mediciones/veredictos_s*.txt) y pone las cifras
de las dos semillas una al lado de la otra. Sirve para responder con un
comando si lo que se concluyó con la semilla 0 se sostiene con series que no
se miraron para decidir nada.

Una cifra "coincide" si la diferencia entre las dos semillas es menor que dos
veces el error combinado (raíz de la suma de los cuadrados de los dos errores).
"""
import math
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
TSV = os.path.join(RETORNO, "build", "tsv")
MED = os.path.join(RETORNO, "mediciones")

CANDIDATOS = ["max_media", "guardia", "guardia_tope", "prudente", "kalman", "kalman_base", "activo", "base_guardia",
              "base_tope", "base_fuerte", "prud_guardia", "guardia_tope_r", "base_tope_r", "nada", "byh"]
VISTAS = [(2000, "todas", "2000 ticks"), (20000, "interiores", "20 000 ticks, interiores"), (20000, "todas", "20 000 ticks, todas")]
SEMILLAS = (0, 2)


def leer_tsv(largo, series, semilla):
    ruta = os.path.join(TSV, f"hipotesis_n{largo}_{series}_s{semilla}.tsv")
    datos = {}
    with open(ruta) as f:
        next(f)
        for linea in f:
            _, _, _, conjunto, candidato, clave, valor = linea.rstrip("\n").split("\t")
            datos.setdefault((conjunto, candidato), {})[clave] = float(valor)
    return datos


def leer_veredictos(semilla):
    """{candidata: (veredicto 2000, veredicto 20000, global, literal)} de la sección 1 de veredictos_s*.txt."""
    salida = {}
    with open(os.path.join(MED, f"veredictos_s{semilla}.txt")) as f:
        dentro = False
        for linea in f:
            if linea.startswith("1. Campo mixto"):
                dentro = True
                continue
            if dentro and linea.startswith("2. "):
                break
            partes = [p.strip() for p in linea.split("|")]
            if dentro and len(partes) == 5 and partes[3] in ("PASA", "NO_PASA"):
                v = re.findall(r"(NO_PASA|PASA)", partes[1] + " " + partes[2])
                salida[partes[0]] = (v[0], v[1], partes[3], partes[4])
    return salida


def dec(x, d=3):
    return f"{x:+.{d}f}".replace(".", ",")


def ent(x):
    return ("+" if x >= 0 else "-") + f"{abs(round(x)):,}".replace(",", " ")


def celda(a, ea, b, eb, entero=False):
    f = ent if entero else dec
    e = (lambda v: f"{round(v):,}".replace(",", " ")) if entero else (lambda v: f"{v:.3f}".replace(".", ","))
    coincide = abs(a - b) <= 2 * math.hypot(ea, eb)
    mismo_signo = (a > 2 * ea and b > 2 * eb) or (a < -2 * ea and b < -2 * eb) or (abs(a) <= 2 * ea and abs(b) <= 2 * eb)
    return f"{f(a)} ± {e(ea)} / {f(b)} ± {e(eb)}", coincide, mismo_signo


def tabla(cabecera, filas):
    print("| " + " | ".join(cabecera) + " |")
    print("|" + "|".join("---" for _ in cabecera) + "|")
    for f in filas:
        print("| " + " | ".join(str(x) for x in f) + " |")
    print()


def main():
    H = {(n, ser, s): leer_tsv(n, ser, s) for n, ser, _ in VISTAS for s in SEMILLAS}
    print("# Semilla de exploración (0) contra semilla reservada (2)\n")
    print("Generado por `pruebas/comparar_semillas.py`. Conjunto evidencia, campo mixto, G = 10. Cada celda trae la cifra de la")
    print("semilla 0 y la de la semilla 2, con su error estándar. Las diferencias son contra la regla base, pareadas.\n")

    total = coinciden = juicios = 0
    distintas = []
    for n, ser, titulo in VISTAS:
        a, b = H[(n, ser, 0)], H[(n, ser, 2)]
        ba, bb = a[("evidencia", "base")], b[("evidencia", "base")]
        print(f"## Rondas de {titulo}\n")
        p = lambda v: f"{v:.3f}".replace(".", ",")
        print(f"Series: {round(ba['n'])} con la semilla 0 y {round(bb['n'])} con la semilla 2. Regla base: patrimonio medio "
              f"{round(ba['h1_media'])} ± {round(ba['h1_ee'])} y {round(bb['h1_media'])} ± {round(bb['h1_ee'])}; H3a "
              f"{p(ba['h3a_media'])} y {p(bb['h3a_media'])}; H3b {p(ba['h3b_media'])} y {p(bb['h3b_media'])}.\n")
        filas = []
        for c in CANDIDATOS:
            x, y = a[("evidencia", c)], b[("evidencia", c)]
            fila = [f"`{c}`"]
            for clave, eclave, entero in (("h1_dif", "h1_dif_ee", True), ("d_h3a", "d_h3a_ee", False), ("d_h3b", "d_h3b_ee", False),
                                          ("d_h3a_c_p5", "d_h3a_c_p5_ee", False), ("d_h3b_c_p5", "d_h3b_c_p5_ee", False)):
                texto, coincide, mismo = celda(x[clave], x[eclave], y[clave], y[eclave], entero)
                total += 1
                coinciden += coincide
                juicios += mismo
                if not mismo:
                    distintas.append(f"{titulo}, `{c}`, {clave}: {texto}")
                fila.append(texto + ("" if mismo else " (*)"))
            filas.append(fila)
        tabla(["Candidato", "H1: patrimonio", "H3a: puntos esperados", "H3b: puntos esperados", "H3a: p5 de tres rondas",
               "H3b: p5 de tres rondas"], filas)

    print("## Resumen\n")
    print(f"- Cifras comparadas: {total}. Coinciden dentro de dos errores combinados: {coinciden}.")
    print(f"- Mismo juicio en las dos semillas (mejora, igual o empeora, con dos errores estándar): {juicios} de {total}.")
    if distintas:
        print("- Cifras con juicio distinto, marcadas con (*):")
        for d in distintas:
            print(f"  - {d}")
    print()

    va, vb = leer_veredictos(0), leer_veredictos(2)
    print("## Veredicto del criterio de corte contra la regla base\n")
    print("Campo mixto, G = 10. Veredicto a 2000 ticks, a 20 000 ticks (interiores) y global.\n")
    filas, cambios = [], 0
    for c in CANDIDATOS:
        if c not in va or c not in vb:
            continue
        cambios += va[c][2] != vb[c][2]
        filas.append([f"`{c}`", f"{va[c][0]}, {va[c][1]}, **{va[c][2]}**", f"{vb[c][0]}, {vb[c][1]}, **{vb[c][2]}**",
                      "igual" if va[c][2] == vb[c][2] else "CAMBIA"])
    tabla(["Candidata", "Semilla 0", "Semilla 2", "Veredicto global"], filas)
    print(f"Veredictos globales que cambian entre las dos semillas: {cambios} de {len(filas)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
