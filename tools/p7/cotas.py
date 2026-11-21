#!/usr/bin/env python3
"""cotas.py: el punto 3.3 (co-diseño) medido sobre la regla de cotas con banda 40.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El paquete P7 (tools/p7/medir.py y tablas.py) midió el co-diseño sobre la regla
anterior, max_media, y sigue valiendo para la extensión emad y devk. Este script
mide el mismo conjunto de variantes con el programa que corre hoy:

  r0      Espino base, sw/trade.s (la regla de cotas, un hilo)
  seg     Espino segmentado, sw/trade.s
  barrel  Espino barrel con sw/trade.s en un hilo (tools/barrel/tabla.py)
  r2      R1 y R2 (barrel, tabla en BRAM y la extensión, que la regla no usa),
          sw/fondo.s: el hilo 0 decide, los otros tres esperan

con el gemelo digital (validado contra el RTL) a los tres períodos y con el perfil
por dirección a 0,1 ms. Los recursos (celdas, LUT4, BRAM, fmax) son los de
docs/mediciones/p7/recursos.txt: el hardware no cambió con el programa.

Definiciones (clase 7, las mismas de docs/codiseno.md):
  - Operación útil de la regla, 11 por tick (decisión de Nicolás, 21/11): 4
    comparaciones (p <= 100, p >= 255, p <= 140, p >= 215), 2 "or" que recuerdan
    el mínimo y el máximo vistos, 1 "and" de los dos extremos, y 2 + 2 para
    comprar = bajo | (ambos & p <= 140) y vender = alto | (ambos & p >= 215).
    Armar el byte, los loads, los stores, los saltos, el sondeo y la telemetría
    no cuentan.
  - Kernel: de leer PRICE a volver al sondeo, sin la espera. Respuesta: de
    byte_done a la escritura de DECISION.
  - Desempeño logrado = operaciones útiles x 25 MHz / ciclos del kernel.
  - Ppeak = f x instrucciones por ciclo x operaciones por instrucción x núcleos.
    Base 12,5 MOPS, segmentado 25, barrel con un hilo útil 6,25 y R2 25 (cuatro
    hilos, una instrucción por ciclo agregada, una operación por instrucción: la
    regla no usa la extensión, que es lo que duplicaba el techo en max_media).
  - Roofline: I = operaciones útiles / bytes que el kernel mueve por el bus (loads
    y stores fuera del sondeo), Bs = 100 MB/s.
  - Amdahl generalizado: S = 1 / sum(f_i / F_i), una fracción por fase, con el
    modelo de costo de la variante nueva aplicado a las instrucciones del perfil.

Deja en docs/mediciones/p7/cotas/: gemelo.txt, perfil/<v>.txt, variantes.csv y
.txt, perfil.csv y .txt, amdahl.csv y .txt, roofline.csv y .tex, cifras.tex.

Uso: python3 tools/p7/cotas.py   (o make p7-cotas). Unos 20 segundos.
"""
import csv
import hashlib
import math
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tools", "p7"))
import fuentes  # noqa: E402

B = "build/p7/cotas"
M = "docs/mediciones/p7/cotas"
GEMELO = "build/gemelo"
SERIE = "data/practica_meta.csv"
F_CLK, BS, SPI_NS = 25.0, 100.0, 9500
OPS = 11
RONDAS = [("r1", 10_000_000, 2000), ("r2", 1_000_000, 20000), ("r3", 100_000, 20000)]
PRESUPUESTO = {r: (p - SPI_NS) // 40 for r, p, _ in RONDAS}
TABLA = "sw/fondo_tabla.hex"

# etiqueta: (nombre, opciones del gemelo, programa, ppeak, clave de recursos, nombre corto)
VAR = {
    "r0": ("Espino base, sw/trade.s", [], "trade", 12.5, "r0", "R0 base"),
    "seg": ("Segmentado, sw/trade.s", ["--pipeline"], "trade", 25.0, "seg", "Segmentado"),
    "barrel": ("Barrel, sw/trade.s en un hilo", ["--barrel"], "trade_h0", 6.25, "barrel", "Barrel 1 hilo"),
    "r2": ("R1 y R2: barrel, tabla y vigilante, sw/fondo.s", ["--barrel", "--xd", "3", "--tabla", TABLA], "fondo", 25.0,
           "r2", "R2 (4 hilos)"),
}
ORDEN = ["r0", "seg", "barrel", "r2"]
MODELOS = {
    "base": dict(alu=2, load=3, store=2, salto=3),
    "seg_clase": dict(alu=1, load=2, store=1, salto=3),
    "seg": dict(alu=1, load=2, store=1, salto=2),
    "barrel": dict(alu=4, load=4, store=4, salto=4),
}
FASES_RESP = ["leer", "comparar", "decidir", "escribir"]
NOMBRE_FASE = {"deteccion": "Detectar el precio (sondeo)", "leer": "Leer PRICE", "comparar": "Comparar con los umbrales",
               "decidir": "Decidir y armar el byte", "escribir": "Escribir DECISION", "telemetria": "Telemetría",
               "volver": "Volver al sondeo"}


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw).stdout


def sha(ruta):
    return hashlib.sha256(open(ruta, "rb").read()).hexdigest()[:16]


def programas():
    os.makedirs(f"{B}/sw", exist_ok=True)
    sh([sys.executable, "tools/pochoasm.py", "sw/trade.s", "-o", f"{B}/sw/trade.hex"])
    sh(["cmp", f"{B}/sw/trade.hex", "sw/trade.hex"])      # el hex guardado es el de sw/trade.s
    open(f"{B}/sw/trade_h0.s", "w", encoding="utf-8").write(sh([sys.executable, "tools/barrel/tabla.py", "0", "sw/trade.s"]))
    sh([sys.executable, "tools/pochoasm.py", f"{B}/sw/trade_h0.s", "-o", f"{B}/sw/trade_h0.hex"])
    sh([sys.executable, "tools/pochoasm.py", "sw/fondo.s", "-o", f"{B}/sw/fondo.hex"])


def fuente(prog):
    return {"trade": "sw/trade.s", "trade_h0": f"{B}/sw/trade_h0.s", "fondo": "sw/fondo.s"}[prog]


# ---------------------------------------------------------------------------- gemelo
def medir():
    sh(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", GEMELO, "ref/gemelo/gemelo.c"])
    os.makedirs(f"{M}/perfil", exist_ok=True)
    commit = sh(["git", "rev-parse", "--short", "HEAD"]).strip()
    out = ["Ciclos por tick de las variantes con la regla de cotas (banda 40), con el gemelo digital",
           "Generado por tools/p7/cotas.py (make p7-cotas). No editar a mano.", "",
           f"Commit de partida: {commit}",
           f"Serie {SERIE} (sha256 {sha(SERIE)}...), tabla {TABLA} (sha256 {sha(TABLA)}...)", ""]
    g = {}
    for etq in ORDEN:
        nombre, opts, prog, *_ = VAR[etq]
        hexf = f"{B}/sw/{prog}.hex"
        out.append(f"== variante {etq}: build/gemelo {' '.join(opts)} --hex {hexf} (sha256 {sha(hexf)}...)")
        g[etq] = {}
        for ronda, periodo, nticks in RONDAS:
            r = sh([GEMELO, *opts, "--hex", hexf, "--serie", SERIE, "--periodo-ns", str(periodo), "--nticks", str(nticks)])
            for linea in r.splitlines():
                if linea.startswith(("Patrimonio", "Peor caso", "Testbenchs", "Gemelo: " + str(nticks - 2))):
                    out.append(f"{etq} {ronda} | {linea}")
            d = g[etq][ronda] = {}
            d["patrimonio"] = int(re.search(r"Patrimonio final:\s+(\d+)", r).group(1))
            d["peor_oficial"] = int(re.search(r"Peor caso precio->decision: (\d+)", r).group(1))
            m = re.search(r"Respuesta: ([\d.]+) ciclos e IC ([\d.]+) en promedio, peor caso (\d+) ciclos e IC (\d+)\. "
                          r"Tick completo: ([\d.]+) ciclos e IC ([\d.]+) en promedio, peor caso (\d+) ciclos e IC (\d+)", r)
            d.update(r_c=float(m[1]), r_ic=float(m[2]), r_cp=int(m[3]), r_icp=int(m[4]), t_c=float(m[5]), t_ic=float(m[6]),
                     t_cp=int(m[7]), t_icp=int(m[8]))
            if "aprobados: 4/4" not in r:
                sys.exit(f"FAIL: {etq} {ronda} no obtuvo 4/4 en el gemelo")
        perfil = f"{M}/perfil/{etq}.txt"
        sh([GEMELO, *opts, "--hex", hexf, "--serie", SERIE, "--periodo-ns", "100000", "--nticks", "20000", "--perfil", perfil,
            "--callado"])
        out.append(f"{etq} perfil | {perfil}, 20000 ticks a 0,1 ms sin atajo")
        out.append("")
    open(f"{M}/gemelo.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
    return g


# ---------------------------------------------------------------------------- recursos
def recursos():
    r = {}
    txt = open("docs/mediciones/p7/recursos.txt", encoding="utf-8").read()
    pat = (r"^p7_(\w+) +celdas +(\d+) de 1280, BRAM +(\d+) de 16, LUT4 +(\d+), fmax min +([\d.]+) "
           r"mediana +([\d.]+) max +([\d.]+) MHz, cierran a 25 MHz (\d+) de (\d+)")
    for m in re.finditer(pat, txt, re.M):
        r[m[1]] = dict(celdas=int(m[2]), bram=int(m[3]), lut=int(m[4]), fmin=float(m[5]), fmed=float(m[6]),
                       cierran=f"{m[8]}/{m[9]}")
    return r


# ---------------------------------------------------------------------------- perfil por fase
def fases_trade(ruta):
    """Fase de cada dirección de un programa con la forma de sw/trade.s (el hilo que decide)."""
    m, sim = fuentes.mapa(ruta)
    fase = {d: "arranque" for d in m}
    d, estado, sondeo = sim["esperar"], "esperar", 0
    while d in m:
        _, nom, ops, _ = m[d]
        if estado == "esperar":
            fase[d] = "esperar"
            sondeo += 1
            if sondeo == 3:
                estado = "leer"
        elif estado == "leer":
            assert nom == "lw" and "off_price" in ops[1], ruta
            fase[d] = "leer"
            estado = "comparar"
        elif estado == "comparar":
            if nom == "or":                       # primera instrucción de la decisión
                estado = "decidir"
                fase[d] = "decidir"
            else:
                fase[d] = "comparar"
        elif estado == "decidir":
            if nom == "sw" and "off_decision" in ops[1]:
                fase[d] = "escribir"
                estado = "volver"
            else:
                fase[d] = "decidir"
        elif estado == "volver":
            fase[d] = "volver" if nom == "j" else "telemetria"
            if nom == "j":
                return fase, m
            estado = "volver"
        d += 4
    raise ValueError(f"{ruta}: no se encontró el lazo principal")


def fases_fondo(ruta):
    """Fase de cada dirección del hilo 0 de sw/fondo.s, por los comentarios numerados."""
    m, _ = fuentes.mapa(ruta)
    lineas = open(ruta, encoding="utf-8").read().splitlines()
    secciones = [(r"^supervisor:", "arranque"), (r"^# 1\. Esperar", "esperar"), (r"^# 2\. Comparar", "comparar"),
                 (r"^# 3\. Decidir", "decidir"), (r"^# 4\. Telemetr", "telemetria"), (r"^hilo[123]:", "arranque")]
    actual, por_linea = "arranque", {}
    for i, txt in enumerate(lineas, start=1):
        for patron, f in secciones:
            if re.match(patron, txt):
                actual = f
                break
        por_linea[i] = actual
    fase = {}
    for d, (lineno, nom, ops, _) in m.items():
        f = por_linea[lineno]
        if nom == "lw" and len(ops) > 1 and "off_price" in ops[1]:
            f = "leer"
        elif nom == "sw" and len(ops) > 1 and "off_decision" in ops[1]:
            f = "escribir"
        elif f == "telemetria" and nom == "j" and ops[0] == "s_espera":
            f = "volver"
        fase[d] = f
    return fase, m


def leer_perfil(etq):
    filas = []
    for linea in open(f"{M}/perfil/{etq}.txt", encoding="utf-8"):
        if linea.startswith("#"):
            continue
        h, d, w, n, c = linea.split()
        filas.append((int(h), int(d, 16), int(w, 16), int(n), int(c)))
    return filas


def analizar(etq, g):
    prog = VAR[etq][2]
    fase, _ = (fases_fondo if prog == "fondo" else fases_trade)(fuente(prog))
    filas = leer_perfil(etq)
    esc = [d for d in fase if fase[d] == "escribir"]
    nref = sum(n for h, d, w, n, c in filas if h == 0 and d in esc)
    por = {}
    for h, d, w, n, c in filas:
        f = fase.get(d, "fuera")
        x = por.setdefault((h, f), dict(c=0.0, ic=0.0, alu=0.0, load=0.0, store=0.0, salto=0.0, bytes=0.0))
        x["c"] += c / nref
        x["ic"] += n / nref
        x[fuentes.clase(w)] += n / nref
        if h == 0 and f not in ("arranque", "esperar", "fuera"):
            x["bytes"] += fuentes.tamano_acceso(w) * min(n, nref) / nref
    cero = dict(c=0.0, ic=0.0, alu=0.0, load=0.0, store=0.0, salto=0.0, bytes=0.0)
    fk = ["leer", "comparar", "decidir", "escribir"] + (["telemetria"] if prog == "fondo" else []) + ["volver"]
    fase0 = {f: por.get((0, f), cero) for f in set(fk) | {"esperar"}}
    gr = g[etq]["r3"]
    k_c = sum(fase0[f]["c"] for f in fk)
    k_ic = sum(fase0[f]["ic"] for f in fk)
    det = gr["r_c"] - sum(fase0[f]["c"] for f in FASES_RESP)
    byts = sum(fase0[f]["bytes"] for f in fk)
    return dict(por=por, fase0=fase0, fk=fk, k_c=k_c, k_ic=k_ic, det=det, bytes=byts, cpi_k=k_c / k_ic,
                mops=OPS * F_CLK / k_c, intens=OPS / byts, g=gr, nref=nref)


def lazo(modelo):
    m = MODELOS[modelo]
    return m["load"] + m["alu"] + m["salto"]


# ---------------------------------------------------------------------------- salida
def f2(x, d=2):
    return f"{x:.{d}f}"


def tex(x, d=2):
    s = f"{x:,.{d}f}" if abs(x) >= 10000 else f"{x:.{d}f}"
    return s.replace(",", "\\,").replace(".", "{,}")


MACROS = []


def macro(nombre, valor, d=2):
    assert re.fullmatch(r"[A-Za-z]+", nombre), nombre
    MACROS.append((nombre, str(valor) if isinstance(valor, int) else tex(valor, d)))


def escribir_csv(ruta, cab, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cab)
        w.writerows(filas)


SUF = {"r0": "Rcero", "seg": "Seg", "barrel": "Barrel", "r2": "Rdos"}


def tabla_variantes(rec, g, R):
    cab = ["variante", "descripcion", "celdas", "lut4", "bram", "fmax_min_mhz", "fmax_mediana_mhz", "cierran_25mhz",
           "resp_prom_ciclos", "resp_peor_ciclos", "tick_prom_ciclos", "tick_peor_ciclos", "ic_resp_prom", "ciclos_kernel",
           "ic_kernel", "cpi_kernel", "ops_utiles_tick", "mops_logrado", "ppeak_mops", "speedup_resp", "uso_r3_pct",
           "patrimonio_r3"]
    filas, txt = [], []
    base = R["r0"]
    for etq in ORDEN:
        nombre, _, _, ppeak, rk, corto = VAR[etq]
        r, s = rec[rk], R[etq]
        uso = {k: 100.0 * g[etq][k]["peor_oficial"] / PRESUPUESTO[k] for k in PRESUPUESTO}
        sp = base["g"]["r_c"] / s["g"]["r_c"]
        filas.append([etq, nombre, r["celdas"], r["lut"], r["bram"], r["fmin"], r["fmed"], r["cierran"], f2(s["g"]["r_c"]),
                      s["g"]["r_cp"], f2(s["g"]["t_c"]), s["g"]["t_cp"], f2(s["g"]["r_ic"]), f2(s["k_c"]), f2(s["k_ic"]),
                      f2(s["cpi_k"], 3), OPS, f2(s["mops"], 3), ppeak, f2(sp, 3), f2(uso["r3"], 3),
                      g[etq]["r3"]["patrimonio"]])
        m = SUF[etq]
        macro(f"pCotasCeldas{m}", r["celdas"])
        macro(f"pCotasFmaxMin{m}", r["fmin"])
        macro(f"pCotasRespProm{m}", s["g"]["r_c"])
        macro(f"pCotasRespPeor{m}", s["g"]["r_cp"])
        macro(f"pCotasKernelCiclos{m}", s["k_c"])
        macro(f"pCotasKernelIc{m}", s["k_ic"])
        macro(f"pCotasCpiKernel{m}", s["cpi_k"], 3)
        macro(f"pCotasMops{m}", s["mops"])
        macro(f"pCotasSpeedupResp{m}", sp)
        macro(f"pCotasUsoRtres{m}", uso["r3"], 2)
        macro(f"pCotasIntensidad{m}", s["intens"], 3)
        macro(f"pCotasBytes{m}", s["bytes"])
        macro(f"pCotasDeteccion{m}", s["det"])
    macro("pCotasOps", OPS)
    escribir_csv(f"{M}/variantes.csv", cab, filas)
    w = txt.append
    w("Variantes de co-diseno con la regla de cotas, banda 40 (punto 3.3 del enunciado)")
    w("Generado por tools/p7/cotas.py (make p7-cotas) desde docs/mediciones/p7/cotas/ y p7/recursos.txt. No editar a mano.")
    w(f"Operaciones utiles por tick: {OPS} (definicion en el encabezado de tools/p7/cotas.py). Serie de practica a 0,1 ms.")
    w("")
    w(f"{'Variante':<20}{'Celdas':>7}{'LUT4':>6}{'BRAM':>5}{'Fmax min':>9}{'Resp prom':>10}{'peor':>6}{'Tick prom':>10}"
      f"{'peor':>6}{'Kernel':>8}{'IC':>7}{'CPI':>7}{'MOPS':>7}{'Ppeak':>7}{'S resp':>8}{'% r3':>7}")
    for f in filas:
        w(f"{VAR[f[0]][5]:<20}{f[2]:>7}{f[3]:>6}{f[4]:>5}{f[5]:>9.2f}{f[8]:>10}{f[9]:>6}{f[10]:>10}{f[11]:>6}{f[13]:>8}"
          f"{f[14]:>7}{f[15]:>7}{f[17]:>7}{f[18]:>7}{f[19]:>8}{f[20]:>7}")
    open(f"{M}/variantes.txt", "w", encoding="utf-8").write("\n".join(txt) + "\n")


def tabla_perfil(R):
    filas, txt = [], []
    w = txt.append
    w("Perfil del tick con la regla de cotas: en que fase se van los ciclos (punto 3.3, perfilado)")
    w("Generado por tools/p7/cotas.py. La deteccion es la respuesta medida menos las fases que van antes de DECISION.")
    w("")
    for etq in ORDEN:
        s = R[etq]
        w(f"== {VAR[etq][0]}")
        w(f"   {'fase':<34}{'ciclos/tick':>12}{'instr./tick':>12}{'% resp.':>9}{'% kernel':>9}")
        for f in ["deteccion"] + s["fk"]:
            c = s["det"] if f == "deteccion" else s["fase0"][f]["c"]
            ic = None if f == "deteccion" else s["fase0"][f]["ic"]
            pr = 100.0 * c / s["g"]["r_c"] if f in ("deteccion",) + tuple(FASES_RESP) else None
            pk = None if f == "deteccion" else 100.0 * c / s["k_c"]
            w(f"   {NOMBRE_FASE[f]:<34}{c:>12.2f}{'-' if ic is None else f'{ic:.2f}':>12}"
              f"{'-' if pr is None else f'{pr:.1f}':>9}{'-' if pk is None else f'{pk:.1f}':>9}")
            filas.append([etq, f, f2(c), "" if ic is None else f2(ic), "" if pr is None else f2(pr, 1),
                          "" if pk is None else f2(pk, 1)])
        w(f"   {'respuesta medida (gemelo)':<34}{s['g']['r_c']:>12.2f}")
        w(f"   {'kernel (sin la deteccion)':<34}{s['k_c']:>12.2f}{s['k_ic']:>12.2f}")
        w("")
    escribir_csv(f"{M}/perfil.csv", ["variante", "fase", "ciclos_tick", "instrucciones_tick", "pct_respuesta", "pct_kernel"], filas)
    open(f"{M}/perfil.txt", "w", encoding="utf-8").write("\n".join(txt) + "\n")


def fases_de(R, etq, ventana):
    s = R[etq]
    fases = FASES_RESP if ventana == "resp" else s["fk"]
    return fases


def medido(R, etq, ventana):
    s = R[etq]
    out = {f: s["fase0"][f]["c"] for f in fases_de(R, etq, ventana)}
    if ventana == "resp":
        out["deteccion"] = s["det"]
    return out


def predecir(R, etq, modelo, ventana):
    s, m = R[etq], MODELOS[modelo]
    out = {f: sum(s["fase0"][f][k] * m[k] for k in ("alu", "load", "store", "salto")) for f in fases_de(R, etq, ventana)}
    if ventana == "resp":
        out["deteccion"] = R["r0"]["det"] * lazo(modelo) / lazo("base")
    return out


def tabla_amdahl(R):
    txt, filas = [], []
    w = txt.append
    w("Amdahl generalizado con la regla de cotas: speedup predicho contra medido (punto 3.3)")
    w("Generado por tools/p7/cotas.py. S = 1 / sum(f_i / F_i); f_i del perfil de R0; F_i predicho = modelo de costo de la")
    w("variante nueva aplicado a las instrucciones de la fase; F_i medido = cociente de los ciclos medidos de la fase.")
    w("La deteccion del sondeo se predice escalando la de R0 por la duracion de una vuelta del lazo.")
    w("")
    for nom, m in MODELOS.items():
        w(f"  modelo {nom:<10} ALU {m['alu']}, load {m['load']}, store {m['store']}, salto tomado {m['salto']}; "
          f"vuelta del sondeo {lazo(nom)} ciclos")
    w("")
    casos = [("seg_clase", "seg_clase", "seg", "R0 -> segmentado, con el CPI que estimó la clase 7"),
             ("seg", "seg", "seg", "R0 -> segmentado, con el modelo de costo medido"),
             ("barrel", "barrel", "barrel", "R0 -> barrel, sw/trade.s en un hilo")]
    for ventana, titulo in (("resp", "respuesta (de byte_done a DECISION)"), ("kernel", "kernel (de leer PRICE a volver al sondeo)")):
        w(f"=== Ventana: {titulo}")
        for etq, modelo, med, desc in casos:
            base_f = medido(R, "r0", ventana)
            pred = predecir(R, "r0", modelo, ventana)
            tot0 = sum(base_f.values())
            s_pred = tot0 / sum(pred.values())
            nuevo = R[med]["g"]["r_c"] if ventana == "resp" else R[med]["k_c"]
            ant = R["r0"]["g"]["r_c"] if ventana == "resp" else R["r0"]["k_c"]
            s_med = ant / nuevo
            medf = medido(R, med, ventana)
            w(f"--- {desc}")
            w(f"    {'fase':<30}{'ciclos antes':>13}{'f':>8}{'F predicho':>11}{'F medido':>10}")
            for f in base_f:
                Fp = base_f[f] / pred[f] if pred[f] else float("inf")
                Fm = base_f[f] / medf[f] if medf.get(f) else float("nan")
                w(f"    {NOMBRE_FASE[f]:<30}{base_f[f]:>13.2f}{base_f[f] / tot0:>8.3f}{Fp:>11.3f}{Fm:>10.3f}")
            w(f"    S predicho {s_pred:.3f} ({tot0 / s_pred:.2f} ciclos), S medido {s_med:.3f} ({nuevo:.2f} ciclos), "
              f"diferencia {100.0 * (s_pred - s_med) / s_med:+.1f} %")
            filas.append([ventana, etq, desc, f2(s_pred, 3), f2(s_med, 3), f2(tot0 / s_pred), f2(nuevo)])
            mk = {"seg_clase": "SegClase", "seg": "Seg", "barrel": "Barrel"}[etq]
            vk = "Resp" if ventana == "resp" else "Kernel"
            macro(f"pCotasAmdahlPred{vk}{mk}", s_pred, 3)
            macro(f"pCotasAmdahlMed{vk}{mk}", s_med, 3)
            macro(f"pCotasAmdahlErr{vk}{mk}", 100.0 * abs(s_pred - s_med) / s_med, 1)
        w("")
    r0 = R["r0"]
    w("=== R2 no es un speedup del mismo kernel")
    r2 = R["r2"]
    w(f"    El hilo 0 de R2 ejecuta {r2['k_ic']:.2f} instrucciones en el kernel contra {r0['k_ic']:.2f} de R0: agrega los cuatro")
    w("    loads de la tabla en BRAM y la telemetria. Cada instruccion cuesta 4 ciclos, y la prediccion por modelo de costo")
    w("    del barrel es exacta por construccion. Los otros tres hilos solo dan vueltas a un salto.")
    escribir_csv(f"{M}/amdahl.csv", ["ventana", "caso", "descripcion", "s_predicho", "s_medido", "ciclos_predichos",
                                     "ciclos_medidos"], filas)
    open(f"{M}/amdahl.txt", "w", encoding="utf-8").write("\n".join(txt) + "\n")


def roofline(R):
    puntos = [(VAR[e][5], R[e]["intens"], R[e]["mops"], VAR[e][3]) for e in ORDEN]
    techos = [(6.25, "6,25: barrel, 1 hilo"), (12.5, "12,5: Espino base"), (25.0, "25: segmentado; barrel, 4 hilos")]
    filas = [[p[0], f2(p[1], 4), f2(p[2], 4), p[3], "medido"] for p in puntos]
    filas += [[f"techo {t[1]}", "", "", t[0], "Ppeak"] for t in techos]
    filas.append(["quiebre del Espino base", f2(12.5 / BS, 4), "12.5", "12.5", "Ppeak / Bs"])
    escribir_csv(f"{M}/roofline.csv", ["serie", "intensidad_op_por_byte", "mops", "ppeak_mops", "tipo"], filas)
    X0, X1, Y0, Y1 = -2, 2, -1, 2
    lg = math.log10
    t = ["% roofline.tex: generado por tools/p7/cotas.py (make p7-cotas). No editar a mano.",
         f"% Ejes en log10: x de 0,01 a 100 Op/B, y de 0,1 a 100 MOPS.",
         "\\begin{tikzpicture}[x=2.2cm,y=1.6cm,font=\\small]",
         f"  \\draw[gray!25] ({X0},{Y0}) grid ({X1},{Y1});", f"  \\draw[gray] ({X0},{Y0}) rectangle ({X1},{Y1});"]
    for e in range(X0, X1 + 1):
        t.append(f"  \\node[below] at ({e},{Y0}) {{${tex(10.0 ** e, max(0, -e))}$}};")
    for e in range(Y0, Y1 + 1):
        t.append(f"  \\node[left] at ({X0},{e}) {{${tex(10.0 ** e, max(0, -e))}$}};")
    t.append(f"  \\node[below=5mm] at ({(X0 + X1) / 2},{Y0}) {{Intensidad operacional $I$ (Op/B)}};")
    t.append(f"  \\node[rotate=90,above=8mm] at ({X0},{(Y0 + Y1) / 2}) {{Desempeño (MOPS)}};")
    for pk, lab in techos:
        t.append(f"  \\draw[gray,dashed,thick] ({lg(pk / BS):.4f},{lg(pk):.4f}) -- ({X1},{lg(pk):.4f}) "
                 f"node[right,black,font=\\scriptsize] {{{lab.replace(',', '{,}')}}};")
    t.append(f"  \\draw[black,thick] ({X0},{lg(10 ** X0 * BS):.4f}) -- ({lg(25.0 / BS):.4f},{lg(25.0):.4f});")
    t.append(f"  \\draw[gray,dotted] ({lg(0.125):.4f},{Y0}) -- ({lg(0.125):.4f},{lg(12.5):.4f});")
    lado = {"R0 base": "left", "Segmentado": "left", "Barrel 1 hilo": "below", "R2 (4 hilos)": "right"}
    for lab, i, p, pk in puntos:
        t.append(f"  \\filldraw[blue!60!black] ({lg(i):.4f},{lg(p):.4f}) circle (2.2pt) "
                 f"node[{lado[lab]},font=\\scriptsize,black] {{{lab}}};")
    t.append("\\end{tikzpicture}")
    open(f"{M}/roofline.tex", "w", encoding="utf-8").write("\n".join(t) + "\n")


def main():
    programas()
    g = medir()
    rec = recursos()
    R = {e: analizar(e, g) for e in ORDEN}
    tabla_variantes(rec, g, R)
    tabla_perfil(R)
    tabla_amdahl(R)
    roofline(R)
    with open(f"{M}/cifras.tex", "w", encoding="utf-8") as f:
        f.write("% Generado por tools/p7/cotas.py (make p7-cotas). No editar a mano.\n")
        for k, v in MACROS:
            f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    print(open(f"{M}/variantes.txt", encoding="utf-8").read())
    print(open(f"{M}/perfil.txt", encoding="utf-8").read())
    print(open(f"{M}/amdahl.txt", encoding="utf-8").read())


if __name__ == "__main__":
    main()
