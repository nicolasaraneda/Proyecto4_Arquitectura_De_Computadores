"""report_33.py: tablas y figura del punto 3.3 para tools/report.py.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee lo que deja el paquete P7 en docs/mediciones/p7/ (make p7-rapido): los CSV
de variantes, perfil, Amdahl, escalera y ASIC, las macros de cifras.tex y la
figura del roofline en TikZ. No mide nada.
"""
import csv
import os
import re
import shutil

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P7 = os.path.join(RAIZ, "docs", "mediciones", "p7")
G = os.path.join(RAIZ, "informe", "generado")

NOMBRES = {"r0": "R0: base, \\texttt{trade.s}", "seg": "Segmentado, \\texttt{trade.s}",
           "barrel": "Barrel, 1 hilo", "barrel_xd": "Barrel + extensión, 1 hilo",
           "r1": "R1: barrel + ext. + tabla, fondo", "r2": "R2: R1 + vigilante"}
FASES = {"deteccion": "Detectar el precio", "leer": "Leer \\texttt{PRICE}", "media_dev": "Desviación a la media",
         "decidir": "Decidir", "escribir": "Escribir \\texttt{DECISION}", "media_s": "Actualizar la media",
         "volver": "Volver al sondeo", "publicar": "Publicar precio y tick", "regla": "Regla propia (\\texttt{max\\_media})",
         "votos": "Esperar y leer votos", "pesos": "Ajuste de pesos", "voto": "Combinar votos",
         "telemetria": "Telemetría"}
SUFIJO = {"r0": "Rcero", "seg": "Seg", "barrel": "Barrel", "barrel_xd": "BarrelXd", "r1": "Runo", "r2": "Rdos"}
PASO = {"0": "Cero", "1": "Uno", "2": "Dos", "1+2": "UnoDos", "2b": "DosB", "1+2b": "UnoDosB", "2c": "DosC",
        "3": "Tres", "4": "Cuatro"}
NA = "n/a"   # celda sin dato: no aplica o no se midió


def filas_csv(nombre):
    with open(os.path.join(P7, nombre), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def macros_p7():
    """Valores de las macros de docs/mediciones/p7/cifras.tex. Los CSV guardan cifras ya
    redondeadas a 3 decimales, y volver a redondearlas a 2 puede diferir en una centésima
    del texto (0,745 da 0,74 y no 0,75). Las columnas de speedup se toman de aquí para que
    la tabla y el texto muestren el mismo número."""
    with open(os.path.join(P7, "cifras.tex"), encoding="utf-8") as fh:
        return dict(re.findall(r"^\\newcommand\{\\(\w+)\}\{(.*)\}\s*$", fh.read(), re.M))


def punto_33(c, peldano, tabla, num, leer):
    os.makedirs(G, exist_ok=True)
    f = lambda x, d=2: num(float(x), d)   # noqa: E731
    mp = macros_p7()

    # Variantes
    var = filas_csv("variantes.csv")
    filas = []
    for v in var:
        filas.append([NOMBRES[v["variante"]], f"{v['celdas']} / {v['lut4']} / {v['bram']}",
                      f"{f(v['fmax_min_mhz'])} / {f(v['fmax_mediana_mhz'])}",
                      f"{f(v['resp_prom_ciclos'], 1)} / {v['resp_peor_ciclos']}",
                      f"{f(v['tick_prom_ciclos'], 1)} / {v['tick_peor_ciclos']}",
                      f(v["ciclos_kernel"], 1), f(v["cpi_kernel"], 3), v["ops_utiles_tick"], f(v["mops_logrado"]),
                      f(v["ppeak_mops"]), mp[f"pSieteSpeedupResp{SUFIJO[v['variante']]}"], f(v["uso_r3_pct"])])
    tabla(os.path.join(G, "t33variantes.tex"),
          ["Variante", "Celdas / LUT4 / BRAM", "$f_{\\max}$ mín. / med. (MHz)", "Resp. prom. / peor",
           "Tick prom. / peor", "Ciclos kernel", "CPI kernel", "Ops/tick", "MOPS", "$P_{peak}$", "Speedup resp.",
           "\\% ronda 3"], filas, "lrrrrrrrrrrr",
          "Recursos: 10 semillas de nextpnr a 25 MHz (todas cierran). Ciclos: práctica a 0,1 ms, en ciclos de 40 ns. "
          "Kernel: de leer \\texttt{PRICE} a volver al sondeo. Operación útil: las 8 operaciones de \\texttt{max\\_media} "
          "por tick (56 en el fondo). MOPS = operaciones útiles $\\times$ 25 MHz / ciclos del kernel. Fuente: "
          "\\texttt{docs/mediciones/p7/variantes.txt} (\\texttt{make p7-variantes}).")
    for v in var:
        sufijo = SUFIJO[v["variante"]]
        c[f"Celdas{sufijo}"] = v["celdas"]
        c[f"Fmin{sufijo}"] = f(v["fmax_min_mhz"])
        c[f"Mops{sufijo}"] = f(v["mops_logrado"])
        c[f"RespPeor{sufijo}"] = v["resp_peor_ciclos"]

    # Variación de la síntesis: el mismo RTL del segmentado leído en otro orden
    # (tools/p7/caida_segmentado.sh, make p7-caida-seg)
    with open(os.path.join(P7, "caida_segmentado.txt"), encoding="utf-8") as fc:
        texto = fc.read()
    m = re.search(r"Entre ordenes: medianas de ([0-9.]+) a ([0-9.]+) MHz, minimas de ([0-9.]+) a ([0-9.]+) MHz", texto)
    c["SintMedMin"], c["SintMedMax"] = f(m.group(1)), f(m.group(2))
    c["SintMinMin"], c["SintMinMax"] = f(m.group(3)), f(m.group(4))
    m = re.search(r"^  p1 +e118269 +\d+ +\d+ \| +([0-9.]+)", texto, re.M)
    c["FminSegPuno"] = f(m.group(1))

    # Perfil del tick
    perfil = filas_csv("perfil.csv")
    clave = "r0" if peldano == "r0" else "r1"
    filas = [[FASES.get(p["fase"], p["fase"]), f(p["ciclos_tick"], 2),
              f(p["instrucciones_tick"], 2) if p["instrucciones_tick"] else NA,
              f(p["pct_respuesta"], 1) if p["pct_respuesta"] else NA,
              f(p["pct_kernel"], 1) if p["pct_kernel"] else NA] for p in perfil if p["variante"] == clave]
    tabla(os.path.join(G, "t33perfil.tex"), ["Fase", "Ciclos por tick", "Instrucciones", "\\% de la respuesta",
                                              "\\% del kernel"], filas, "lrrrr",
          f"Perfil medido con el gemelo digital (\\texttt{{--perfil}}), {'R0' if clave == 'r0' else 'R1, hilo supervisor'}. "
          "Fuente: \\texttt{docs/mediciones/p7/perfil.txt}.")
    if clave == "r0":
        filas = [[FASES.get(p["fase"], p["fase"]), f(p["ciclos_tick"], 2), f(p["instrucciones_tick"], 2)
                  if p["instrucciones_tick"] else NA] for p in perfil if p["variante"] == "r1"]
    else:
        filas = [[FASES.get(p["fase"], p["fase"]), f(p["ciclos_tick"], 2), f(p["instrucciones_tick"], 2)
                  if p["instrucciones_tick"] else NA] for p in perfil if p["variante"] == "r0"]
    tabla(os.path.join(G, "t33perfilotro.tex"), ["Fase", "Ciclos por tick", "Instrucciones"], filas, "lrr")

    # Amdahl
    am = filas_csv("amdahl.csv")
    filas = []
    for a in am:
        filas.append(["Respuesta" if a["ventana"] == "resp" else "Kernel", a["descripcion"].replace("->", "$\\to$"),
                      f(a["s_predicho"], 3), f(a["s_medido"], 3) if a["s_medido"] else "no construida",
                      f"{f(a['ciclos_predichos'], 2)} / {f(a['ciclos_medidos'], 2) if a['ciclos_medidos'] else 'sin medir'}"])
    tabla(os.path.join(G, "t33amdahl.tex"), ["Ventana", "Cambio", "$S$ predicho", "$S$ medido", "Ciclos pred. / med."],
          filas, "llrrr", "Amdahl generalizado, $S = 1 / \\sum_i (f_i / F_i)$, con las fracciones del perfil medido de "
          "la variante de partida. Fuente: \\texttt{docs/mediciones/p7/amdahl.txt} (\\texttt{make p7-amdahl}).")

    for a in am:
        if a["ventana"] == "resp" and a["caso"] in ("seg_clase", "seg"):
            err = (float(a["s_medido"]) - float(a["s_predicho"])) / float(a["s_medido"]) * 100
            c["AmdahlErrClase" if a["caso"] == "seg_clase" else "AmdahlErrModelo"] = num(err, 0)
    ints = [float(r["intensidad_op_por_byte"]) for r in filas_csv("roofline.csv") if r["tipo"] == "medido"]
    c["IntMin"], c["IntMax"] = num(min(ints), 2), num(max(ints), 2)

    # Escalera
    es = filas_csv("escalera.csv")
    filas = [[e["paso"], e["descripcion"], e["estado"].split(":")[0], f(e["ic_por_op"], 3), f(e["ciclos_por_op"], 3),
              e["ciclos_por_op_clase"].replace(".", "{,}") if e["ciclos_por_op_clase"] not in ("", "-") else NA,
              f(e["mops"]), mp[f"pSieteEscSpeedup{PASO[e['paso']]}"], e["celdas"] or NA] for e in es]
    tabla(os.path.join(G, "t33escalera.tex"), ["Paso", "Descripción", "Estado", "Instr./op", "Ciclos/op",
                                                "Ciclos/op (clase)", "MOPS", "Speedup", "Celdas"], filas,
          "llp{1.5cm}rrrrrr", "Escalera de la clase 7 aplicada a nuestro kernel. Los pasos medidos salen del gemelo y "
          "del RTL; los estimados, del modelo de costo o con CPI ideal 1, como hizo la clase. Fuente: "
          "\\texttt{docs/mediciones/p7/escalera.txt}.")

    # ASIC
    asic = filas_csv("asic.csv")
    filas = []
    for etiqueta, k, d in (("Área del dado (mm$^2$)", "dado_um2", None), ("$f_{\\max}$ con cierre (MHz)", "fmax_cierre_mhz", 1),
                           ("Potencia calculando (mW)", "p_calculo_mw", 1), ("Potencia en la ronda 3 (mW)", "p_ronda3_mw", 1),
                           ("Kernel a 25 MHz (MOPS)", "mops_25", 2), ("Ops/W del kernel (MOPS/W)", "mops_por_w", 0),
                           ("$P_{peak}$/W (MOPS/W)", "ppeak_por_w", 0), ("Energía por decisión, ronda 3 ($\\mu$J)", "e_decision_r3_uj", 2),
                           ("Costo marginal de decidir (nJ)", "marginal_nj", 1)):
        fila = [etiqueta]
        for a in asic:
            fila.append(num(float(a[k]) / 1e6, 3) if k == "dado_um2" else f(a[k], d))
        filas.append(fila)
    tabla(os.path.join(G, "t33asic.tex"), ["", "Espino base", "Segmentado"], filas, "lrr",
          "Flujo LibreLane en GF180MCU, esquina típica, 25 MHz. Fuente: \\texttt{docs/mediciones/p7/asic.txt} y "
          "\\texttt{docs/mediciones/asic/}.")

    # Figura y macros de P7
    shutil.copyfile(os.path.join(P7, "roofline.tex"), os.path.join(G, "roofline.tex"))
    shutil.copyfile(os.path.join(P7, "cifras.tex"), os.path.join(G, "cifras_p7.tex"))
