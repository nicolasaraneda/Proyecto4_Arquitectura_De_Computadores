#!/usr/bin/env python3
"""tablas.py: tablas del estudio de cierre a partir de las corridas de correr.py.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 tablas.py --semilla 0 --etiqueta exploracion > mediciones/tablas_exploracion_s0.md
    python3 tablas.py --semilla 3 --etiqueta final       > mediciones/tablas_final_s3.md
    python3 tablas.py --semilla 3 --etiqueta duelo_ejec_a --ref ejec_a > mediciones/tablas_duelo_ejec_a_s3.md

No evalúa nada: lee build/tsv/ETIQUETA_sS_VISTA_CAMPO.tsv, que escribe el
comando `hipotesis` del arnés. Todas las diferencias son pareadas contra la
referencia (`max_media`, o la que se indique con --ref), con G = 10 rivales.

El veredicto de cada campo se calcula aquí con la misma regla del comando
`veredicto` del arnés (nucleo/main.c): en el conjunto evidencia, una fila H3a
o H3b pasa si la media de los puntos mejora en más de dos errores y el
percentil 5 de la competencia de tres rondas no baja en más de dos errores; a
2000 ticks con todas las series y a 20 000 con las interiores. Las cifras son
las mismas del comando oficial, porque `hipotesis` y `veredicto` usan el mismo
torneo con el mismo sorteo. Si existe mediciones/veredictos_sS.txt (el comando
oficial, campo mixto), se comprueba que coinciden cifra por cifra.
"""
import argparse
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
TSV = os.path.join(AQUI, "build", "tsv")
M = os.path.join(AQUI, "mediciones")
REF = "max_media"        # se cambia con --ref
VISTAS = (("n2000", "2000 ticks"), ("n20000_int", "20 000 ticks, interiores"), ("n20000_par", "20 000 ticks, parada"))
CORRIDOS = ("mixto", "racional", "reversores", "fijos2", "fijos3")
CAMPOS = ("mixto", "fuerte", "racional", "reversores")          # los de la tabla final
TODOS = ("ingenuo", "mixto", "fuerte", "fijos2", "fijos3", "racional", "reversores")
CONJUNTOS = ("evidencia", "estres")

QUE = {
    "max_media": "`max_media`, la referencia de los estudios anteriores",
    "base": "regla base (E = 128)",
    "kalman": "Kalman de dos estados",
    "ejec_a": "`ejec:m=8`, ejecución A",
    "ejec_b": "`ejec:m=8,m2=24,e2=32`, ejecución B",
    "espera": "regla fija `espera` (r4c)",
    "aprendiz": "tabla que aprende (r4c)",
    "aprendiz_patron": "`max_media` con predictor de patrones (r4c)",
    "espera_e": "`espera` con la ejecución A",
    "fondo_rec": "fondo recomendado (r4b)",
    "fondo_min": "fondo mínimo, voto (r4b)",
    "fondo_ancla": "fondo con ancla (r4b)",
    "rec_e": "`fondo_rec` con la ejecución A",
    "min_e": "`fondo_min` con la ejecución A",
    "completo": "FONDO COMPLETO",
    "completo_s": "completo sin la ejecución A",
    "completo_esp": "completo con `espera` de cuarto gestor",
    "completo_ap": "completo con pesos aprendidos",
    "completo_ancla": "completo con ancla en comprar y mantener",
    "completo_min": "fondo mínimo con `aprendiz` y ejecución A",
}


def leer(etiqueta, semilla, ref=None):
    """Devuelve (datos, candidatas, campos disponibles). Los duelos no traen fijos2 ni fijos3."""
    ref = ref or REF
    datos, orden = {}, []
    for vista, _ in VISTAS:
        for campo in CORRIDOS:
            ruta = os.path.join(TSV, f"{etiqueta}_s{semilla}_{vista}_{campo}.tsv")
            if not os.path.exists(ruta):
                if campo in ("fijos2", "fijos3"):
                    continue
                sys.exit(f"falta {ruta}: correr correr.py --semilla {semilla}")
            d = {}
            with open(ruta) as f:
                next(f)
                for linea in f:
                    _, _, _, conj, cand, clave, valor = linea.rstrip("\n").split("\t")
                    d[(conj, cand, clave)] = float(valor)
                    if cand not in orden:
                        orden.append(cand)
            datos[(vista, campo)] = d
    campos = [c for c in TODOS if c in ("ingenuo", "fuerte") or ("n2000", c) in datos]
    return datos, [c for c in orden if c not in (ref, "nada", "byh")], campos


class Tablas:
    def __init__(self, datos):
        self.d = datos

    def h(self, vista, conj, cand, clave):
        """Cifras que no dependen del campo (H1 y H2)."""
        return self.d[(vista, "mixto")][(conj, cand, clave)]

    def t(self, vista, campo, conj, cand, lectura, que):
        """Cifras del torneo. lectura: h3a o h3b. que: media, d, d_ee, p5c, dp5c, dp5c_ee."""
        if campo in ("ingenuo", "fuerte"):
            tabla, suf = self.d[(vista, "mixto")], f"_{campo}_10"
            clave = {"media": f"sens_{lectura}{suf}", "d": f"dsens_{lectura}{suf}", "d_ee": f"dsens_{lectura}{suf}_ee",
                     "p5c": f"sens_{lectura}_c_p5{suf}", "dp5c": f"dsens_{lectura}_c_p5{suf}",
                     "dp5c_ee": f"dsens_{lectura}_c_p5{suf}_ee"}[que]
        else:
            tabla = self.d[(vista, campo)]
            clave = {"media": f"{lectura}_media", "d": f"d_{lectura}", "d_ee": f"d_{lectura}_ee", "p5c": f"{lectura}_c_p5",
                     "dp5c": f"d_{lectura}_c_p5", "dp5c_ee": f"d_{lectura}_c_p5_ee", "p5": f"{lectura}_p5"}[que]
        return tabla[(conj, cand, clave)]

    def veredicto(self, campo, cand):
        """El criterio de corte con este campo: (pasa 2000, pasa 20000, literal, parada confirma, motivo)."""
        pasa, literal, motivo = {}, True, []
        for vista in ("n2000", "n20000_int"):
            ok_vista = True
            for lectura in ("h3a", "h3b"):
                d, ee = self.t(vista, campo, "evidencia", cand, lectura, "d"), self.t(vista, campo, "evidencia", cand, lectura, "d_ee")
                dp, ep = self.t(vista, campo, "evidencia", cand, lectura, "dp5c"), self.t(vista, campo, "evidencia", cand, lectura, "dp5c_ee")
                mejora, empeora5 = d > 2 * ee, dp < -2 * ep
                if not (mejora and not empeora5):
                    ok_vista = False
                    motivo.append(f"{vista[1:].split('_')[0]} {lectura.upper()}: " +
                                  ("p5 baja" if mejora else "empeora" if d < -2 * ee else "no mejora"))
                if not (d > 0 and dp >= 0):
                    literal = False
            pasa[vista] = ok_vista
        confirma = True
        for lectura in ("h3a", "h3b"):
            di = self.t("n20000_int", campo, "evidencia", cand, lectura, "d")
            dq = self.t("n20000_par", campo, "evidencia", cand, lectura, "d")
            if (di > 0) != (dq > 0) and not (di == 0 and dq == 0):
                confirma = False
        return pasa["n2000"], pasa["n20000_int"], literal, confirma, "; ".join(motivo)


def n(x, dec=3, signo=False):
    s = f"{x:+.{dec}f}" if signo else f"{x:.{dec}f}"
    if dec == 0 and abs(x) >= 1000:
        s = f"{x:+,.0f}" if signo else f"{x:,.0f}"
        s = s.replace(",", " ")
    return s.replace(".", ",")


def pm(d, ee, dec=3):
    return f"{n(d, dec, True)} ± {n(ee, dec)}"


def fila(celdas):
    return "| " + " | ".join(celdas) + " |"


def cabecera(celdas):
    return fila(celdas) + "\n|" + "|".join("---" for _ in celdas) + "|"


def comprobar_oficial(T, semilla, cands, salida):
    """Las cifras del comando veredicto (campo mixto) contra las que se leen de los tsv."""
    ruta = os.path.join(M, f"veredictos_s{semilla}.txt")
    if not os.path.exists(ruta):
        return {}
    texto = open(ruta, encoding="utf-8").read()
    oficiales, cifras, malas = {}, 0, 0
    for bloque in texto.split("===== ")[1:]:
        cand = bloque.split(" contra ")[0].strip()
        ver = {}
        for linea in bloque.splitlines():
            m = re.match(r"VEREDICTO( \d+)?: (\S+)", linea)
            if m:
                ver[(m.group(1) or " global").strip()] = m.group(2)
            if linea.startswith("Veredicto literal"):
                ver["literal"] = linea.rsplit(":", 1)[1].strip()
            partes = linea.split("|")
            if len(partes) == 4 and partes[0].split()[2:3] == ["evidencia"] and partes[0].split()[3] in ("H3a", "H3b"):
                largo, series, _, lectura = partes[0].split()
                vista = "n2000" if largo == "2000" else {"interiores": "n20000_int", "parada": "n20000_par"}.get(series)
                if vista is None or cand not in cands:
                    continue
                d_of, ee_of = float(partes[1].split()[2]), float(partes[1].split()[3])
                dp_of, ep_of = float(partes[2].split()[2]), float(partes[2].split()[3])
                lec = lectura.lower()
                for of, mio in ((d_of, T.t(vista, "mixto", "evidencia", cand, lec, "d")), (ee_of, T.t(vista, "mixto", "evidencia", cand, lec, "d_ee")),
                                (dp_of, T.t(vista, "mixto", "evidencia", cand, lec, "dp5c")), (ep_of, T.t(vista, "mixto", "evidencia", cand, lec, "dp5c_ee"))):
                    cifras += 1
                    malas += abs(of - mio) > 0.00051
        oficiales[cand] = ver
    veredictos_distintos = 0
    for cand, ver in oficiales.items():
        if cand not in cands:
            continue
        p2, p20, lit, _, _ = T.veredicto("mixto", cand)
        mio = ("PASA" if p2 else "NO_PASA", "PASA" if p20 else "NO_PASA", "pasa" if lit else "no pasa")
        if mio != (ver.get("2000"), ver.get("20000"), ver.get("literal")):
            veredictos_distintos += 1
    salida.append(f"Comprobación contra el comando oficial `veredicto --parada` (campo mixto, `mediciones/veredictos_s{semilla}.txt`): "
                  f"{cifras} cifras comparadas, {malas} distintas al tercer decimal; {len([c for c in oficiales if c in cands])} veredictos, "
                  f"{veredictos_distintos} distintos.")
    return oficiales


def main():
    global REF, TODOS
    ap = argparse.ArgumentParser()
    ap.add_argument("--semilla", type=int, required=True)
    ap.add_argument("--etiqueta", required=True, help="exploracion, final o duelo_REFERENCIA")
    ap.add_argument("--ref", default=REF)
    a = ap.parse_args()
    REF = a.ref
    datos, cands, TODOS = leer(a.etiqueta, a.semilla)
    T = Tablas(datos)
    o = []
    nombre = "exploración" if a.semilla == 0 else "reservada"
    o.append(f"# Estudio de cierre: tablas de la lista `{a.etiqueta}`, semilla {a.semilla} ({nombre})\n")
    o.append("Generado por `tablas.py` a partir de las corridas de `correr.py`. Diferencias pareadas contra `@REF@`, G = 10 rivales. "
             "Puntos de 0 a 2. \"p5 de 3 rondas\" es el percentil 5 del promedio de puntos de una competencia de tres rondas.\n")
    o.append("Vistas: 2000 ticks con todas las series; 20 000 ticks con las series interiores (precio siempre entre 21 y 249), que es la del "
             "criterio de corte; y 20 000 ticks con parada (todas las series, cada una hasta el primer precio fuera de 21 a 249), que no selecciona.\n")
    ns = {v: {c: int(T.h(v, c, REF, "n")) for c in CONJUNTOS} for v, _ in VISTAS}
    o.append("Series: " + "; ".join(f"{t}: {ns[v]['evidencia']} de evidencia y {ns[v]['estres']} de estrés" for v, t in VISTAS) + ".\n")
    o.append("| Nombre | Qué es |\n|---|---|")
    for c in cands:
        o.append(f"| `{c}` | {QUE.get(c, '')} |")
    o.append("")

    # ---- 1. criterio de corte por campo ----
    o.append("## 1. Criterio de corte contra `@REF@`, por campo de rivales\n")
    comprobar = []
    oficiales = comprobar_oficial(T, a.semilla, cands, comprobar) if a.etiqueta == "final" else {}
    o.extend(comprobar)
    o.append("\nConjunto evidencia. Cada celda: diferencia de puntos esperados ± error. \"dp5\" es la diferencia del percentil 5 de tres rondas, "
             "H3a y H3b. Veredicto: 2000 / 20 000 / global con la regla del arnés, veredicto literal (solo signos) y si la fila de parada "
             "tiene el mismo signo que la de interiores. **Final** es PASA solo si el veredicto global pasa y la parada confirma.\n")
    resumen = {}
    for campo in TODOS:
        o.append(f"### Campo {campo}\n")
        o.append(f"Nivel de `@REF@`: " + "; ".join(
            f"{t}: {n(T.t(v, campo, 'evidencia', REF, 'h3a', 'media'))} (H3a) y {n(T.t(v, campo, 'evidencia', REF, 'h3b', 'media'))} (H3b), "
            f"p5 de 3 rondas {n(T.t(v, campo, 'evidencia', REF, 'h3a', 'p5c'))} y {n(T.t(v, campo, 'evidencia', REF, 'h3b', 'p5c'))}"
            for v, t in VISTAS) + ".\n")
        o.append(cabecera(["Candidata", "2000: dH3a", "2000: dH3b", "2000: dp5", "20 000 int.: dH3a", "20 000 int.: dH3b", "20 000 int.: dp5",
                           "parada: dH3a", "parada: dH3b", "2000 / 20 000 / global", "Literal", "Parada", "Final"]))
        for c in cands:
            p2, p20, lit, conf, _ = T.veredicto(campo, c)
            g = p2 and p20
            final = g and conf
            resumen[(campo, c)] = (p2, p20, g, lit, conf, final)
            celdas = [f"`{c}`"]
            for v in ("n2000", "n20000_int"):
                for lec in ("h3a", "h3b"):
                    celdas.append(pm(T.t(v, campo, "evidencia", c, lec, "d"), T.t(v, campo, "evidencia", c, lec, "d_ee")))
                celdas.append(", ".join(pm(T.t(v, campo, "evidencia", c, lec, "dp5c"), T.t(v, campo, "evidencia", c, lec, "dp5c_ee"))
                                        for lec in ("h3a", "h3b")))
            for lec in ("h3a", "h3b"):
                celdas.append(pm(T.t("n20000_par", campo, "evidencia", c, lec, "d"), T.t("n20000_par", campo, "evidencia", c, lec, "d_ee")))
            celdas += [" / ".join("PASA" if x else "NO_PASA" for x in (p2, p20, g)), "pasa" if lit else "no pasa",
                       "confirma" if conf else "no confirma", "**PASA**" if final else "NO_PASA"]
            o.append(fila(celdas))
        o.append("")
    o.append("### Resumen del veredicto final por campo\n")
    o.append(cabecera(["Candidata"] + list(TODOS) + ["Pasa en"]))
    for c in cands:
        cuenta = sum(resumen[(campo, c)][5] for campo in TODOS)
        o.append(fila([f"`{c}`"] + [("PASA" if resumen[(campo, c)][5] else "no") for campo in TODOS] + [f"{cuenta} de {len(TODOS)}"]))
    o.append("")
    if oficiales:
        o.append("Veredicto del comando oficial (campo mixto): " + "; ".join(
            f"`{c}` {v.get('2000')} / {v.get('20000')} / {v.get('global')}, literal {v.get('literal')}" for c, v in oficiales.items() if c in cands) + ".\n")

    # ---- 2. H1 y H2 ----
    o.append("## 2. H1 (patrimonio) y H2 (exceso sobre comprar y mantener)\n")
    o.append("La diferencia de H2 en pesos es la misma de H1, porque comprar y mantener es igual para todos en cada serie. Por eso se informa además "
             "la razón W/B&H. \"p5 de 3 rondas\" es el percentil 5 del promedio de tres rondas.\n")
    for conj in CONJUNTOS:
        for v, t in VISTAS:
            o.append(f"### {t}, conjunto {conj} ({ns[v][conj]} series)\n")
            o.append(cabecera(["Candidata", "H1: media", "H1: p5", "H1: dif. contra `@REF@`", "H1: p5 de 3 rondas (dif.)", "H2: exceso medio",
                               "H2: p5 del exceso", "H2: p5 de 3 rondas", "H2: W/B&H media", "H2: W/B&H dif.", "Órdenes"]))
            for c in [REF] + cands:
                o.append(fila([f"`{c}`", n(T.h(v, conj, c, "h1_media"), 0), n(T.h(v, conj, c, "h1_p5"), 0),
                               pm(T.h(v, conj, c, "h1_dif"), T.h(v, conj, c, "h1_dif_ee"), 0),
                               f"{n(T.h(v, conj, c, 'h1c_p5'), 0)} ({pm(T.h(v, conj, c, 'd_h1c_p5'), T.h(v, conj, c, 'd_h1c_p5_ee'), 0)})",
                               n(T.h(v, conj, c, "h2_media"), 0, True), n(T.h(v, conj, c, "h2_p5"), 0, True), n(T.h(v, conj, c, "h2c_p5"), 0, True),
                               n(T.h(v, conj, c, "h2r_media")), pm(T.h(v, conj, c, "h2r_dif"), T.h(v, conj, c, "h2r_dif_ee")),
                               n(T.h(v, conj, c, "ordenes"), 1)]))
            o.append("")

    # ---- 3. H3a y H3b por campo ----
    o.append("## 3. H3a y H3b (torneo): puntos esperados por campo\n")
    o.append("Cada celda: media de los puntos, percentil 5 de una ronda (diferencia de la media contra `@REF@` ± error). El campo fuerte "
             "sale de la tabla de sensibilidad del arnés, que no trae el percentil 5 de una ronda. El de la competencia de tres rondas "
             "está en la sección 4 para los cuatro campos.\n")
    for conj in CONJUNTOS:
        for v, t in VISTAS:
            for lec, tl in (("h3a", "H3a, lineal en patrimonio"), ("h3b", "H3b, lineal en el puesto")):
                o.append(f"### {tl}. {t}, conjunto {conj}\n")
                o.append(cabecera(["Candidata"] + list(CAMPOS)))
                for c in [REF] + cands:
                    o.append(fila([f"`{c}`"] + [
                        f"{n(T.t(v, campo, conj, c, lec, 'media'))}"
                        + ("" if campo == "fuerte" else f", p5 {n(T.t(v, campo, conj, c, lec, 'p5'), 2)}")
                        + f" ({pm(T.t(v, campo, conj, c, lec, 'd'), T.t(v, campo, conj, c, lec, 'd_ee'))})"
                        for campo in CAMPOS]))
                o.append("")

    # ---- 4. competencia de tres rondas ----
    o.append("## 4. Competencia de tres rondas: media y percentil 5 de los puntos\n")
    o.append("La media de los puntos de la competencia es la media de una ronda (sección 3). Cada celda: percentil 5 del promedio de las tres rondas "
             "(diferencia contra `@REF@` ± error). El error que da el arnés para el percentil 5 es unas 2,8 veces el real.\n")
    for conj in CONJUNTOS:
        for v, t in VISTAS:
            o.append(f"### {t}, conjunto {conj}\n")
            o.append(cabecera(["Candidata"] + [f"{campo}: {lec}" for campo in CAMPOS for lec in ("H3a", "H3b")]))
            for c in [REF] + cands:
                o.append(fila([f"`{c}`"] + [
                    f"{n(T.t(v, campo, conj, c, lec, 'p5c'))} ({pm(T.t(v, campo, conj, c, lec, 'dp5c'), T.t(v, campo, conj, c, lec, 'dp5c_ee'))})"
                    for campo in CAMPOS for lec in ("h3a", "h3b")]))
            o.append("")

    # ---- 5. signo por evidencia ----
    o.append("## 5. El signo en cada evidencia por separado (campo mixto)\n")
    o.append("Diferencia de puntos esperados contra `@REF@` en el remuestreo y en las familias plausibles. Una mejora vale como evidencia "
             "si el signo se repite en las dos.\n")
    for v, t in VISTAS:
        o.append(f"### {t}\n")
        o.append(cabecera(["Candidata", "H1: remuestreo", "H1: plausibles", "H3a: remuestreo", "H3a: plausibles", "H3b: remuestreo", "H3b: plausibles",
                           "Mismo signo en H3a y H3b"]))
        for c in cands:
            celdas, igual = [f"`{c}`"], True
            for conj in ("remuestreo", "plausibles"):
                celdas.append(pm(T.h(v, conj, c, "h1_dif"), T.h(v, conj, c, "h1_dif_ee"), 0))
            for lec in ("h3a", "h3b"):
                x = [T.t(v, "mixto", conj, c, lec, "d") for conj in ("remuestreo", "plausibles")]
                e = [T.t(v, "mixto", conj, c, lec, "d_ee") for conj in ("remuestreo", "plausibles")]
                celdas += [pm(x[0], e[0]), pm(x[1], e[1])]
                if (x[0] > 0) != (x[1] > 0) and not (x[0] == 0 and x[1] == 0):
                    igual = False
            celdas.append("sí" if igual else "no")
            o.append(fila(celdas))
        o.append("")
    print("\n".join(o).replace("@REF@", REF))
    return 0


if __name__ == "__main__":
    sys.exit(main())
