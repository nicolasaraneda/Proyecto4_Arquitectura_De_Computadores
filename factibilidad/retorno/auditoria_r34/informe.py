#!/usr/bin/env python3
"""informe.py: cifras informadas por el estudio de cierre contra las del evaluador independiente.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee ../r4_final/mediciones/resumen.md (las tablas del estudio, con las
semillas 0 y 3 lado a lado) y mediciones/independiente_s0.txt y _s3.txt (lo
que entrega `indep34 tabla`). Para cada celda que el evaluador independiente
calcula, compara lo informado con lo obtenido.

Tolerancias:
  - patrimonio (H1): las series y la contabilidad son deterministas, así que
    tiene que coincidir al redondeo con que se informa (medio peso);
  - razón W/B&H: al redondeo (0,0005);
  - puntos de torneo: el arnés sortea 6 campos de rivales por serie y el
    evaluador independiente calcula el valor esperado exacto. No pueden
    coincidir al último decimal. La diferencia entre los dos es ruido del
    sorteo de campos, que es parte del error estándar que el estudio informa
    (ese error junta el ruido entre series y el del sorteo). Se acepta el
    redondeo (0,0005) más tres veces el error informado, al que se le suma su
    propio redondeo (0,0005). Para los niveles, que el resumen trae sin
    error, se usa 0,006, que es el error que el arnés da para un nivel.

    python3 informe.py            (desde factibilidad/retorno/auditoria_r34)
"""
import os
import re
import statistics
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RESUMEN = os.path.join(os.path.dirname(AQUI), "r4_final", "mediciones", "resumen.md")
MIAS = {"max_media", "base", "ejec_a", "ejec_b", "aprendiz", "fondo_rec", "rec_e", "completo", "completo_s", "fondo_min", "min_e",
        "completo_min"}
VISTAS = {"2000": "n2000", "20 000 int.": "n20000int", "20 000 parada": "n20000par", "parada": "n20000par"}


def num(texto):
    return float(texto.replace(" ", "").replace(" ", "").replace(",", ".").replace("+", ""))


def celda(texto):
    """'a ± e / b ± e' o 'a / b' -> [(valor, error), (valor, error)] para las semillas 0 y 3."""
    partes = [p.strip() for p in texto.split(" / ")]
    if len(partes) != 2:
        return None
    salida = []
    try:
        for p in partes:
            if "±" in p:
                v, e = p.split("±")
                salida.append((num(v), num(e)))
            else:
                salida.append((num(p), 0.0))
    except ValueError:
        return None
    return salida


def leer_independiente():
    d = {}
    for s in (0, 3):
        with open(os.path.join(AQUI, "mediciones", f"independiente_s{s}.txt")) as f:
            for linea in f:
                k, v = linea.rstrip("\n").rsplit("=", 1)
                d[k] = float(v)
    return d


def filas_tabla(lineas, i):
    """Devuelve (cabecera, filas) de la tabla Markdown que empieza en la línea i."""
    cab = [c.strip() for c in lineas[i].strip().strip("|").split("|")]
    filas = []
    j = i + 2
    while j < len(lineas) and lineas[j].startswith("|"):
        filas.append([c.strip() for c in lineas[j].strip().strip("|").split("|")])
        j += 1
    return cab, filas


def main():
    ind = leer_independiente()
    lineas = open(RESUMEN).read().split("\n")
    comparadas = []          # (clase, descripcion, informado, obtenido, tolerancia)
    saltadas = 0
    seccion = ""
    ref = "mm"
    campo = None
    for i, linea in enumerate(lineas):
        if linea.startswith("## "):
            ref = "ea" if "Duelos" in linea else "mm"
        if linea.startswith("### "):
            seccion = linea
            campo = None
        m = re.match(r"\*\*Campo (\w+)\.\*\* Puntos de `(\w+)`.*?: (.*)", linea)
        if m:
            campo = m.group(1)
            quien = m.group(2)
            for trozo in m.group(3).split(";"):
                mm = re.match(r"\s*(2000 ticks|20 000 ticks, interiores|20 000 ticks, parada): ([\d,]+) / ([\d,]+) y ([\d,]+) / ([\d,]+)", trozo)
                if not mm:
                    continue
                vista = {"2000 ticks": "n2000", "20 000 ticks, interiores": "n20000int", "20 000 ticks, parada": "n20000par"}[mm.group(1)]
                for lectura, (a, b) in (("h3a", (mm.group(2), mm.group(3))), ("h3b", (mm.group(4), mm.group(5)))):
                    for s, v in ((0, a), (3, b)):
                        clave = f"s{s}.{vista}.evidencia.{campo}.{quien}.{lectura}"
                        if clave in ind:
                            comparadas.append(("torneo", f"{quien} {lectura} {vista} {campo} s{s} (nivel)", num(v), ind[clave], 0.0005 + 3 * 0.0065))
        if not (linea.startswith("| Candidata |") and i + 1 < len(lineas) and lineas[i + 1].startswith("|---")):
            continue
        cab, filas = filas_tabla(lineas, i)
        previa = next((lineas[j] for j in range(i - 1, max(i - 4, 0), -1) if lineas[j].strip()), "")
        es_p5 = previa.startswith("Percentil 5 del patrimonio")
        for fila in filas:
            cand = fila[0].strip("`")
            for col, texto in zip(cab[1:], fila[1:]):
                par = celda(texto) if ("/" in texto and "PASA" not in texto and "no" not in texto.split("/")[0]) else None
                if par is None:
                    continue
                claves = []          # una por semilla
                clase = None
                if "H3a y H3b: criterio de corte" in seccion and campo:
                    mm = re.match(r"(2000|20 000 int\.|20 000 parada): dH3([ab])", col)
                    if mm:
                        clase = "torneo"
                        claves = [f"s{s}.{VISTAS[mm.group(1)]}.evidencia.{campo}.{cand}.dh3{mm.group(2)}_{ref}" for s in (0, 3)]
                elif "H1 y H2: patrimonio" in seccion:
                    mm = re.match(r"(2000|20 000 int\.|20 000 parada): (dH1|razón)", col)
                    if mm:
                        clase = "patrimonio" if mm.group(2) == "dH1" else "razon"
                        claves = [f"s{s}.{VISTAS[mm.group(1)]}.evidencia.{cand}.{'dh1_mm' if mm.group(2) == 'dH1' else 'draz_mm'}" for s in (0, 3)]
                    elif col.startswith("p5 de H1 a 2000"):
                        clase = "patrimonio"
                        claves = [f"s{s}.n2000.evidencia.{cand}.h1_p5" for s in (0, 3)]
                elif "Conjunto de estrés" in seccion:
                    mm = re.match(r"(2000|parada), mixto: dH3([ab])", col)
                    if col == "2000: dH1":
                        clase = "patrimonio"
                        claves = [f"s{s}.n2000.estres.{cand}.dh1_mm" for s in (0, 3)]
                    elif mm:
                        clase = "torneo"
                        claves = [f"s{s}.{VISTAS[mm.group(1)]}.estres.mixto.{cand}.dh3{mm.group(2)}_mm" for s in (0, 3)]
                elif "H1: diferencia de patrimonio contra `ejec_a`" in seccion and es_p5:
                    if col in ("2000", "20 000 int.", "20 000 parada"):
                        clase = "patrimonio"
                        claves = [f"s{s}.{VISTAS[col]}.evidencia.{cand}.h1_p5" for s in (0, 3)]
                elif "H1: diferencia de patrimonio contra `ejec_a`" in seccion:
                    mapa = {"2000": ("n2000", "evidencia"), "2000: remuestreo": ("n2000", "remuestreo"), "2000: plausibles": ("n2000", "plausibles"),
                            "20 000 int.": ("n20000int", "evidencia"), "20 000 parada": ("n20000par", "evidencia"),
                            "parada: remuestreo": ("n20000par", "remuestreo"), "parada: plausibles": ("n20000par", "plausibles"),
                            "parada: estrés": ("n20000par", "estres")}
                    if col in mapa:
                        clase = "patrimonio"
                        claves = [f"s{s}.{mapa[col][0]}.{mapa[col][1]}.{cand}.dh1_ea" for s in (0, 3)]
                elif "Por evidencia" in seccion:
                    mm = re.match(r"(2000|parada), H3([ab]): (remuestreo|plausibles)", col)
                    if mm:
                        clase = "torneo"
                        claves = [f"s{s}.{VISTAS[mm.group(1)]}.{mm.group(3)}.mixto.{cand}.dh3{mm.group(2)}_ea" for s in (0, 3)]
                if not claves:
                    continue
                for s, clave, (v, e) in zip((0, 3), claves, par):
                    if cand not in MIAS or clave not in ind:
                        saltadas += 1
                        continue
                    tol = {"patrimonio": 0.5001, "razon": 0.00051, "torneo": 0.0005 + 3 * (e + 0.0005)}[clase]
                    comparadas.append((clase, clave, v, ind[clave], tol))

    print("Cifras informadas por el estudio de cierre (r4_final/mediciones/resumen.md) contra el evaluador independiente")
    print("Informado: arnes, 6 campos sorteados por serie. Obtenido: indep34, valor esperado exacto. Semillas 0 y 3.")
    print()
    fuera = [c for c in comparadas if abs(c[2] - c[3]) > c[4]]
    for clase in ("patrimonio", "razon", "torneo"):
        sub = [c for c in comparadas if c[0] == clase]
        if not sub:
            continue
        difs = [abs(c[2] - c[3]) for c in sub]
        nf = sum(1 for c in sub if abs(c[2] - c[3]) > c[4])
        print(f"{clase:10s}: {len(sub):4d} cifras, diferencia mediana {statistics.median(difs):.4f}, maxima {max(difs):.4f}, fuera de tolerancia {nf}")
    print(f"total     : {len(comparadas):4d} cifras comparadas, {len(fuera)} fuera de tolerancia; {saltadas} celdas del resumen no se compararon")
    print("            (candidatas que la auditoria no reescribio: espera, completo_ancla; y columnas del campo racional en el estres)")
    print()
    if fuera:
        print("Fuera de tolerancia:")
        for c in sorted(fuera, key=lambda c: -abs(c[2] - c[3]) / c[4]):
            print(f"  {c[1]:64s} informado {c[2]:+10.4f}  obtenido {c[3]:+10.4f}  diferencia {c[2] - c[3]:+8.4f}  tolerancia {c[4]:.4f}")
        print()

    # Tabla principal: max_media y el fondo completo, con parada y campos duros
    print("Tabla principal: celdas de max_media y del fondo completo (informado / obtenido), semilla 0 y semilla 3")
    print(f"{'cifra':66s} {'informado':>10s} {'obtenido':>10s} {'ee indep.':>10s}  coincide")
    principales = []
    for s in (0, 3):
        for vista in ("n2000", "n20000int", "n20000par"):
            for campo in ("mixto", "fuerte", "racional", "reversores"):
                for lectura in ("h3a", "h3b"):
                    principales.append(f"s{s}.{vista}.evidencia.{campo}.max_media.{lectura}")
                    principales.append(f"s{s}.{vista}.evidencia.{campo}.completo.d{lectura}_mm")
                    principales.append(f"s{s}.{vista}.evidencia.{campo}.completo.d{lectura}_ea")
                    principales.append(f"s{s}.{vista}.evidencia.{campo}.ejec_a.d{lectura}_mm")
            principales.append(f"s{s}.{vista}.evidencia.completo.dh1_mm")
            principales.append(f"s{s}.{vista}.evidencia.completo.dh1_ea")
            principales.append(f"s{s}.{vista}.evidencia.ejec_a.dh1_mm")
    por_clave = {}
    for c in comparadas:
        clave = c[1]
        m = re.match(r"(\w+) (h3[ab]) (\w+) (\w+) s(\d) \(nivel\)", clave)
        if m:
            clave = f"s{m.group(5)}.{m.group(3)}.evidencia.{m.group(4)}.{m.group(1)}.{m.group(2)}"
        por_clave[clave] = c
    n = ok = 0
    for clave in principales:
        if clave not in por_clave:
            continue
        c = por_clave[clave]
        ee = ind.get(clave + "_ee", float("nan"))
        bien = abs(c[2] - c[3]) <= c[4]
        n += 1
        ok += bien
        fmt = "+10.0f" if c[0] == "patrimonio" else "+10.3f"
        print(f"{clave:66s} {c[2]:{fmt}} {c[3]:{'+10.1f' if c[0] == 'patrimonio' else '+10.4f'}} {ee:10.4f}  {'si' if bien else 'NO'}")
    print()
    print(f"Tabla principal: {n} celdas, {ok} coinciden")

    # Tabla corta en Markdown para el README: informado (arnés) y obtenido (independiente), semilla 0 / semilla 3
    filas = [
        ("`max_media`: percentil 5 del patrimonio, 2000 ticks", "{s}.n2000.evidencia.max_media.h1_p5", "p"),
        ("`max_media`: H3a, campo mixto, 2000 ticks (nivel)", "{s}.n2000.evidencia.mixto.max_media.h3a", "t"),
        ("`max_media`: H3b, campo mixto, 2000 ticks (nivel)", "{s}.n2000.evidencia.mixto.max_media.h3b", "t"),
        ("`max_media`: H3a, campo mixto, 20 000 con parada (nivel)", "{s}.n20000par.evidencia.mixto.max_media.h3a", "t"),
        ("`max_media`: H3b, campo mixto, 20 000 con parada (nivel)", "{s}.n20000par.evidencia.mixto.max_media.h3b", "t"),
        ("`max_media`: H3a, campo fuerte, 2000 ticks (nivel)", "{s}.n2000.evidencia.fuerte.max_media.h3a", "t"),
        ("`max_media`: H3a, campo racional, 20 000 interiores (nivel)", "{s}.n20000int.evidencia.racional.max_media.h3a", "t"),
        ("`max_media`: H3a, campo reversores, 20 000 con parada (nivel)", "{s}.n20000par.evidencia.reversores.max_media.h3a", "t"),
        ("`ejec_a` menos `max_media`: patrimonio, 2000 ticks", "{s}.n2000.evidencia.ejec_a.dh1_mm", "p"),
        ("`ejec_a` menos `max_media`: H3a, mixto, 2000 ticks", "{s}.n2000.evidencia.mixto.ejec_a.dh3a_mm", "t"),
        ("`ejec_a` menos `max_media`: H3b, mixto, 2000 ticks", "{s}.n2000.evidencia.mixto.ejec_a.dh3b_mm", "t"),
        ("`ejec_a` menos `max_media`: H3a, mixto, 20 000 con parada", "{s}.n20000par.evidencia.mixto.ejec_a.dh3a_mm", "t"),
        ("`ejec_a` menos `max_media`: H3a, reversores, 2000 ticks", "{s}.n2000.evidencia.reversores.ejec_a.dh3a_mm", "t"),
        ("`completo` menos `max_media`: patrimonio, 2000 ticks", "{s}.n2000.evidencia.completo.dh1_mm", "p"),
        ("`completo` menos `max_media`: patrimonio, 20 000 con parada", "{s}.n20000par.evidencia.completo.dh1_mm", "p"),
        ("`completo` menos `max_media`: H3a, mixto, 2000 ticks", "{s}.n2000.evidencia.mixto.completo.dh3a_mm", "t"),
        ("`completo` menos `max_media`: H3b, mixto, 2000 ticks", "{s}.n2000.evidencia.mixto.completo.dh3b_mm", "t"),
        ("`completo` menos `max_media`: H3a, mixto, 20 000 interiores", "{s}.n20000int.evidencia.mixto.completo.dh3a_mm", "t"),
        ("`completo` menos `max_media`: H3a, mixto, 20 000 con parada", "{s}.n20000par.evidencia.mixto.completo.dh3a_mm", "t"),
        ("`completo` menos `max_media`: H3b, mixto, 20 000 con parada", "{s}.n20000par.evidencia.mixto.completo.dh3b_mm", "t"),
        ("`completo` menos `max_media`: H3a, fuerte, 2000 ticks", "{s}.n2000.evidencia.fuerte.completo.dh3a_mm", "t"),
        ("`completo` menos `max_media`: H3a, racional, 20 000 con parada", "{s}.n20000par.evidencia.racional.completo.dh3a_mm", "t"),
        ("`completo` menos `ejec_a`: patrimonio, 2000 ticks", "{s}.n2000.evidencia.completo.dh1_ea", "p"),
        ("`completo` menos `ejec_a`: patrimonio, 20 000 con parada", "{s}.n20000par.evidencia.completo.dh1_ea", "p"),
        ("`completo` menos `ejec_a`: patrimonio, parada, solo remuestreo", "{s}.n20000par.remuestreo.completo.dh1_ea", "p"),
        ("`completo` menos `ejec_a`: patrimonio, parada, solo plausibles", "{s}.n20000par.plausibles.completo.dh1_ea", "p"),
        ("`completo` menos `ejec_a`: H3a, mixto, 2000 ticks", "{s}.n2000.evidencia.mixto.completo.dh3a_ea", "t"),
        ("`completo` menos `ejec_a`: H3b, mixto, 2000 ticks", "{s}.n2000.evidencia.mixto.completo.dh3b_ea", "t"),
        ("`completo` menos `ejec_a`: H3a, mixto, 20 000 con parada", "{s}.n20000par.evidencia.mixto.completo.dh3a_ea", "t"),
        ("`completo` menos `ejec_a`: H3b, mixto, 20 000 con parada", "{s}.n20000par.evidencia.mixto.completo.dh3b_ea", "t"),
        ("`completo` menos `ejec_a`: H3a, fuerte, 2000 ticks", "{s}.n2000.evidencia.fuerte.completo.dh3a_ea", "t"),
        ("`completo` menos `ejec_a`: H3a, racional, 20 000 interiores", "{s}.n20000int.evidencia.racional.completo.dh3a_ea", "t"),
        ("`completo` menos `ejec_a`: H3a, racional, 20 000 con parada", "{s}.n20000par.evidencia.racional.completo.dh3a_ea", "t"),
        ("`completo` menos `ejec_a`: H3b, reversores, 20 000 con parada", "{s}.n20000par.evidencia.reversores.completo.dh3b_ea", "t"),
        ("`completo_min` menos `ejec_a`: H3a, mixto, 2000 ticks", "{s}.n2000.evidencia.mixto.completo_min.dh3a_ea", "t"),
        ("`completo_min` menos `ejec_a`: H3a, mixto, 20 000 con parada", "{s}.n20000par.evidencia.mixto.completo_min.dh3a_ea", "t"),
    ]

    def es(x, clase):
        t = f"{x:+,.0f}".replace(",", " ") if clase == "p" else f"{x:+.3f}".replace(".", ",")
        return t

    with open(os.path.join(AQUI, "mediciones", "tabla_principal.md"), "w") as md:
        md.write("Generado por `informe.py`. Informado: tablas del estudio de cierre (arnés, 6 campos sorteados por serie). Obtenido: evaluador independiente (valor esperado exacto), con su error estándar. Semilla 0 / semilla 3.\n\n")
        md.write("| Cifra | Informado | Obtenido | Coincide |\n|---|---|---|---|\n")
        nf = nok = 0
        for texto, patron, clase in filas:
            inf, obt, bien = [], [], True
            for sem in ("s0", "s3"):
                clave = patron.format(s=sem)
                c = por_clave.get(clave)
                if c is None:
                    inf.append("(no está en el resumen)")
                    bien = False
                else:
                    inf.append(es(c[2], clase))
                    bien = bien and abs(c[2] - c[3]) <= c[4]
                v = ind[clave]
                ee = ind.get(clave + "_ee")
                if clase == "p":
                    obt.append(f"{v:+,.1f}".replace(",", " ").replace(".", ",") + (f" ± {ee:.1f}".replace(".", ",") if ee is not None and "dh1" in clave else ""))
                else:
                    obt.append(f"{v:+.4f}".replace(".", ",") + (f" ± {ee:.4f}".replace(".", ",") if ee is not None else ""))
            nf += 1
            nok += bien
            md.write(f"| {texto} | {' / '.join(inf)} | {' / '.join(obt)} | {'sí' if bien else 'NO'} |\n")
        md.write(f"\n{nf} cifras (cada una con las dos semillas), {nok} coinciden.\n")
    print(f"mediciones/tabla_principal.md: {nf} filas, {nok} coinciden")
    print(f"{'PASS' if not fuera else 'REVISAR'}: {len(comparadas)} cifras comparadas, {len(fuera)} fuera de tolerancia")
    return 0


if __name__ == "__main__":
    sys.exit(main())
