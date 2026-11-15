#!/usr/bin/env python3
"""resumen.py: la lista final con la semilla de exploración y con la reservada, lado a lado.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 resumen.py > mediciones/resumen.md

No evalúa nada: lee build/tsv/final_s0_*, final_s3_*, duelo_*_s0_* y
duelo_*_s3_* (correr.py) con las funciones de tablas.py. Cada celda trae la
semilla 0 y la semilla 3, separadas por una barra. De aquí salen las tablas
del README.
"""
import glob
import math
import os
import sys

import tablas as tb

AQUI = os.path.dirname(os.path.abspath(__file__))
VISTAS = tb.VISTAS
SEMILLAS = (0, 3)


def par(T, f, dec=3):
    """Una celda con las dos semillas: f(T[semilla]) devuelve (d, ee)."""
    return " / ".join(tb.pm(*f(T[s]), dec) for s in SEMILLAS)


def dif(vista, campo, conj, cand, lec):
    return lambda t: (t.t(vista, campo, conj, cand, lec, "d"), t.t(vista, campo, conj, cand, lec, "d_ee"))


def veredicto_texto(T, campo, cand):
    partes = []
    for s in SEMILLAS:
        p2, p20, _, conf, _ = T[s].veredicto(campo, cand)
        partes.append("PASA" if p2 and p20 and conf else "no")
    return " / ".join(partes)


def bloque(o, T, cands, ref, campos, titulo):
    o.append(f"### {titulo}: criterio de corte contra `{ref}`, conjunto evidencia\n")
    for campo in campos:
        nivel = "; ".join(f"{t}: " + " y ".join(
            " / ".join(tb.n(T[s].t(v, campo, "evidencia", ref, lec, "media")) for s in SEMILLAS) for lec in ("h3a", "h3b"))
            for v, t in VISTAS)
        o.append(f"**Campo {campo}.** Puntos de `{ref}` (H3a y H3b, semilla 0 / semilla 3): {nivel}.\n")
        o.append(tb.cabecera(["Candidata", "2000: dH3a", "2000: dH3b", "20 000 int.: dH3a", "20 000 int.: dH3b", "20 000 parada: dH3a",
                              "20 000 parada: dH3b", "Final (s0 / s3)"]))
        for c in cands:
            celdas = [f"`{c}`"]
            for v, _ in VISTAS:
                for lec in ("h3a", "h3b"):
                    celdas.append(par(T, dif(v, campo, "evidencia", c, lec)))
            celdas.append(veredicto_texto(T, campo, c))
            o.append(tb.fila(celdas))
        o.append("")


def concordancia(o, T, cands, campos, nombre):
    total = dentro = mismo = 0
    peores = []
    for campo in campos:
        for v, _ in VISTAS:
            for conj in ("evidencia", "estres"):
                for c in cands:
                    for lec in ("h3a", "h3b"):
                        d0, e0 = dif(v, campo, conj, c, lec)(T[0])
                        d3, e3 = dif(v, campo, conj, c, lec)(T[3])
                        if any(math.isnan(x) for x in (d0, e0, d3, e3)):
                            continue
                        total += 1
                        comb = math.hypot(e0, e3)
                        z = abs(d0 - d3) / comb if comb > 0 else (0.0 if d0 == d3 else float("inf"))
                        dentro += z <= 2
                        j = lambda d, e: 1 if d > 2 * e else -1 if d < -2 * e else 0
                        mismo += j(d0, e0) == j(d3, e3)
                        peores.append((z, f"`{c}`, {lec.upper()}, campo {campo}, {v}, {conj}: {tb.pm(d0, e0)} y {tb.pm(d3, e3)}"))
    peores.sort(reverse=True)
    o.append(f"- {nombre}: {total} diferencias de puntos comparadas entre las dos semillas (candidatas, tres vistas, evidencia y estrés, "
             f"H3a y H3b, campos {', '.join(campos)}). {dentro} coinciden dentro de dos errores combinados y {mismo} tienen el mismo juicio "
             f"(mejora, igual o empeora).")
    for z, texto in peores[:3]:
        if z > 2:
            o.append(f"  - La más distinta ({tb.n(z, 1)} errores): {texto}.")
    return total, dentro, mismo


def main():
    T, cands, campos = {}, None, None
    for s in SEMILLAS:
        datos, c, campos_s = tb.leer("final", s, "max_media")
        T[s] = tb.Tablas(datos)
        cands, campos = c, campos_s
    o = ["# Estudio de cierre: la lista final con las semillas 0 (exploración) y 3 (reservada)\n",
         "Generado por `resumen.py`. Cada celda trae la semilla 0 y la semilla 3, separadas por una barra: diferencia pareada ± error. "
         "G = 10 rivales. \"Final\" es PASA solo si pasa el criterio de corte del arnés (2000 ticks y 20 000 interiores, H3a y H3b, media "
         "que mejora en más de dos errores y percentil 5 de tres rondas que no baja en más de dos) y además la fila de parada tiene el "
         "mismo signo que la de interiores.\n"]
    o.append("## 1. Contra `max_media`\n")
    o.append("### H1 y H2: patrimonio y exceso sobre comprar y mantener, conjunto evidencia\n")
    o.append("La diferencia de H2 en pesos es la de H1. La razón es W/B&H.\n")
    o.append(tb.cabecera(["Candidata", "2000: dH1", "2000: razón", "20 000 int.: dH1", "20 000 int.: razón", "20 000 parada: dH1",
                          "20 000 parada: razón", "p5 de H1 a 2000 (s0 / s3)"]))
    for c in ["max_media"] + cands:
        celdas = [f"`{c}`"]
        for v, _ in VISTAS:
            celdas.append(par(T, lambda t, v=v: (t.h(v, "evidencia", c, "h1_dif"), t.h(v, "evidencia", c, "h1_dif_ee")), 0))
            celdas.append(par(T, lambda t, v=v: (t.h(v, "evidencia", c, "h2r_dif"), t.h(v, "evidencia", c, "h2r_dif_ee"))))
        celdas.append(" / ".join(tb.n(T[s].h("n2000", "evidencia", c, "h1_p5"), 0) for s in SEMILLAS))
        o.append(tb.fila(celdas))
    o.append("")
    bloque(o, T, cands, "max_media", ("mixto", "fuerte", "racional", "reversores"), "H3a y H3b")

    o.append("### Veredicto final por campo (semilla 0 / semilla 3)\n")
    o.append(tb.cabecera(["Candidata"] + list(campos)))
    for c in cands:
        o.append(tb.fila([f"`{c}`"] + [veredicto_texto(T, campo, c) for campo in campos]))
    o.append("")

    o.append("### Conjunto de estrés: diferencia de puntos esperados contra `max_media`\n")
    o.append("A 20 000 ticks las interiores casi no dejan series de estrés: se muestra la vista de parada.\n")
    o.append(tb.cabecera(["Candidata", "2000: dH1", "2000, mixto: dH3a", "2000, mixto: dH3b", "2000, racional: dH3a", "2000, racional: dH3b",
                          "parada, mixto: dH3a", "parada, mixto: dH3b", "parada, racional: dH3a", "parada, racional: dH3b"]))
    for c in cands:
        celdas = [f"`{c}`", par(T, lambda t: (t.h("n2000", "estres", c, "h1_dif"), t.h("n2000", "estres", c, "h1_dif_ee")), 0)]
        for v in ("n2000", "n20000_par"):
            for campo in ("mixto", "racional"):
                for lec in ("h3a", "h3b"):
                    celdas.append(par(T, dif(v, campo, "estres", c, lec)))
        o.append(tb.fila(celdas))
    o.append("")

    o.append("### Competencia de tres rondas: media y percentil 5 de los puntos, conjunto evidencia\n")
    o.append("Niveles, no diferencias. Cada celda: media, p5 de tres rondas (semilla 0 / semilla 3).\n")
    for campo in ("mixto", "racional"):
        o.append(f"**Campo {campo}.**\n")
        o.append(tb.cabecera(["Candidata", "2000: H3a", "2000: H3b", "20 000 parada: H3a", "20 000 parada: H3b"]))
        for c in ["max_media"] + cands:
            celdas = [f"`{c}`"]
            for v in ("n2000", "n20000_par"):
                for lec in ("h3a", "h3b"):
                    celdas.append(" / ".join(f"{tb.n(T[s].t(v, campo, 'evidencia', c, lec, 'media'))}, {tb.n(T[s].t(v, campo, 'evidencia', c, lec, 'p5c'))}"
                                             for s in SEMILLAS))
            o.append(tb.fila(celdas))
        o.append("")
    o.append("Diferencia del percentil 5 de tres rondas contra `max_media` (campo mixto):\n")
    o.append(tb.cabecera(["Candidata", "2000: H3a", "2000: H3b", "20 000 int.: H3a", "20 000 int.: H3b", "20 000 parada: H3a", "20 000 parada: H3b"]))
    for c in cands:
        celdas = [f"`{c}`"]
        for v, _ in VISTAS:
            for lec in ("h3a", "h3b"):
                celdas.append(par(T, lambda t, v=v, lec=lec: (t.t(v, "mixto", "evidencia", c, lec, "dp5c"), t.t(v, "mixto", "evidencia", c, lec, "dp5c_ee"))))
        o.append(tb.fila(celdas))
    o.append("")

    # ---- duelos ----
    o.append("## 2. Duelos: contra la mejor estrategia sola\n")
    refs = sorted(set(os.path.basename(r).split("_s0_")[0][len("duelo_"):] for r in glob.glob(os.path.join(tb.TSV, "duelo_*_s0_n2000_mixto.tsv"))))
    todo = []
    for ref in refs:
        D, dc = {}, None
        for s in SEMILLAS:
            datos, dc, _ = tb.leer(f"duelo_{ref}", s, ref)
            D[s] = tb.Tablas(datos)
        o.append(f"### H1: diferencia de patrimonio contra `{ref}`, conjunto evidencia\n")
        o.append(tb.cabecera(["Candidata", "2000", "2000: remuestreo", "2000: plausibles", "20 000 int.", "20 000 parada",
                              "parada: remuestreo", "parada: plausibles", "parada: estrés"]))
        for c in dc:
            o.append(tb.fila([f"`{c}`"] + [par(D, lambda t, v=v, cj=cj: (t.h(v, cj, c, "h1_dif"), t.h(v, cj, c, "h1_dif_ee")), 0)
                                           for v, cj in (("n2000", "evidencia"), ("n2000", "remuestreo"), ("n2000", "plausibles"),
                                                         ("n20000_int", "evidencia"), ("n20000_par", "evidencia"),
                                                         ("n20000_par", "remuestreo"), ("n20000_par", "plausibles"), ("n20000_par", "estres"))]))
        o.append("")
        o.append(f"Percentil 5 del patrimonio de una ronda (nivel, semilla 0 / semilla 3), `{ref}` y cada candidata:\n")
        o.append(tb.cabecera(["Candidata", "2000", "20 000 int.", "20 000 parada", "2000, 3 rondas", "parada, 3 rondas"]))
        for c in [ref] + dc:
            o.append(tb.fila([f"`{c}`"] + [" / ".join(tb.n(D[s].h(v, "evidencia", c, k), 0) for s in SEMILLAS)
                                           for v, k in (("n2000", "h1_p5"), ("n20000_int", "h1_p5"), ("n20000_par", "h1_p5"),
                                                        ("n2000", "h1c_p5"), ("n20000_par", "h1c_p5"))]))
        o.append("")
        bloque(o, D, dc, ref, ("mixto", "fuerte", "racional", "reversores"), "H3a y H3b")
        o.append(f"### Por evidencia: diferencia contra `{ref}` en remuestreo y plausibles por separado (campo mixto)\n")
        o.append(tb.cabecera(["Candidata", "2000, H3a: remuestreo", "2000, H3a: plausibles", "2000, H3b: remuestreo", "2000, H3b: plausibles",
                              "parada, H3a: remuestreo", "parada, H3a: plausibles"]))
        # la vista de parada del arnés solo trae evidencia en `veredicto`; `hipotesis --parada` sí trae los cuatro conjuntos
        for c in dc:
            celdas = [f"`{c}`"]
            for lec in ("h3a", "h3b"):
                for cj in ("remuestreo", "plausibles"):
                    celdas.append(par(D, dif("n2000", "mixto", cj, c, lec)))
            for cj in ("remuestreo", "plausibles"):
                celdas.append(par(D, dif("n20000_par", "mixto", cj, c, "h3a")))
            o.append(tb.fila(celdas))
        o.append("")
        todo.append((ref, D, dc))

    o.append("## 3. Las dos semillas dicen lo mismo\n")
    concordancia(o, T, cands, ("mixto", "fuerte", "racional", "reversores"), "Contra `max_media`")
    for ref, D, dc in todo:
        concordancia(o, D, dc, ("mixto", "fuerte", "racional", "reversores"), f"Duelos contra `{ref}`")
    o.append("")
    cambios = []
    for campo in campos:
        for c in cands:
            v0 = T[0].veredicto(campo, c)
            v3 = T[3].veredicto(campo, c)
            f0, f3 = v0[0] and v0[1] and v0[3], v3[0] and v3[1] and v3[3]
            if f0 != f3:
                cambios.append(f"`{c}` con el campo {campo} ({'PASA' if f0 else 'no'} con la semilla 0 y {'PASA' if f3 else 'no'} con la 3)")
    o.append(f"Veredictos finales que cambian entre las dos semillas, de {len(campos) * len(cands)} (candidata y campo): "
             + (str(len(cambios)) + ": " + "; ".join(cambios) if cambios else "ninguno") + ".")
    print("\n".join(o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
