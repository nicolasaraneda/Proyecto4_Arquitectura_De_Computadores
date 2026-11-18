#!/usr/bin/env python3
"""tablas.py: tablas, figuras y macros del co-diseño (punto 3.3) desde las
mediciones guardadas. No sintetiza ni simula nada.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee (todo en docs/mediciones/):
  p7/recursos.txt        celdas, LUT4, BRAM y fmax de cada variante (tools/p7/recursos.sh)
  p7/gemelo.txt          ciclos por tick a los tres períodos (tools/p7/medir.py)
  p7/perfil/*.txt        instrucciones y ciclos por dirección (tools/p7/medir.py)
  p7/rtl.txt             confirmación con el RTL (tools/p7/rtl.sh)
  p7/pll.txt             PLL en el VQ100 y en un TQ144 hipotético (tools/p7/pll.sh)
  p7/doble_frecuencia/   duplicador de reloj (tools/p7/doble_frecuencia.sh)
  asic/                  potencia y corridas de LibreLane de la factibilidad
y escribe en docs/mediciones/p7/:
  variantes.txt/.csv     la tabla de variantes del punto 3.3
  perfil.txt/.csv        en qué fase del tick se van los ciclos
  amdahl.txt/.csv        speedup predicho con Amdahl generalizado contra el medido
  escalera.txt/.csv      la escalera de la clase 7 aplicada a nuestro kernel
  roofline.csv/.svg/.tex el roofline (la .tex es una figura TikZ para el informe)
  asic.txt/.csv          área, frecuencia, potencia, Ops/s, Ops/W y energía por decisión
  negativos.txt          PLL y doble frecuencia, con el presupuesto que habrían dado
  cifras.tex             una macro \\newcommand por cada cifra que cita el informe

Definiciones (clase 7, Métricas de Desempeño), las mismas de docs/codiseno.md:
  - Operación útil del kernel max_media: las operaciones de la regla escrita en
    su forma matemática (ref/trader.py, ReglaBase.decidir). Actualizar la media:
    32 p, dev = 32 p - S, dev >>> 5 y S + (dev >>> 5), 4 operaciones. Decidir:
    dev < umbral de entrada, dev < umbral de salida, pos | entrar y
    (...) & no_salir, 4 operaciones. Son 8 por tick. Armar el byte (0x7F o
    0xBF) es codificación de la salida y no cuenta, como no cuentan los loads,
    stores, saltos ni el sondeo. emad y devk hacen 2 operaciones cada una.
  - Operaciones útiles del fondo (sw/fondo.s, ref/fondo.py) por tick común:
    4 reglas de 8 (supervisor y tres gestores), 3 puntajes de 6 (32 (p - p
    anterior), por la posición ejecutada, suma, xor de posiciones, por 2 y
    resta) y la combinación (3 productos peso por voto, 2 sumas y la
    comparación con el umbral, 6). Son 56. El ajuste de pesos cada 512 ticks
    no se cuenta.
  - Ciclos del kernel: los de las instrucciones que van desde la lectura de
    PRICE hasta el salto de vuelta al sondeo, medidos con el perfil. No
    incluyen la espera del precio. En el fondo son los del supervisor, que
    espera los votos: su camino es el camino crítico del tick.
  - Desempeño logrado = operaciones útiles x 25 MHz / ciclos del kernel.
  - Ppeak = f x instrucciones por ciclo x operaciones por instrucción x núcleos.
  - Roofline: P = min(Ppeak, I x Bs), Bs = 4 B por ciclo x 25 MHz = 100 MB/s,
    I = operaciones útiles / bytes que el kernel mueve por el bus (loads y
    stores fuera del sondeo de STATUS; cada dirección cuenta a lo más una vez
    por tick, así un lazo que espera un dato cuenta solo la lectura que lo trae).
  - Amdahl generalizado: S = 1 / sum(f_i / F_i), con una fracción por fase.

Uso: python3 tools/p7/tablas.py   (o make p7-rapido)
"""
import csv
import math
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tools", "p7"))
import fuentes  # noqa: E402

M = "docs/mediciones/p7"
A = "docs/mediciones/asic"
F_CLK = 25.0            # MHz
BS = 100.0              # MB/s
SPI_NS = 9500
PERIODOS = {"r1": 10_000_000, "r2": 1_000_000, "r3": 100_000}
PRESUPUESTO = {r: (p - SPI_NS) // 40 for r, p in PERIODOS.items()}
OPS_TRADE = 8
OPS_FONDO = 4 * 8 + 3 * 6 + 6

# Variantes de la tabla. fuente: programa en assembly para mapear el perfil.
VAR = {
    "r0": dict(nombre="Espino base, max_media (R0 hasta el 17/11, solo software)", corto="R0 base", fuente="sw/historico/trade_max_media.s",
               ops=OPS_TRADE, ppeak=12.5, ppeak_hw=12.5, hilos=1, macro="Rcero"),
    "seg": dict(nombre="Pipeline de 3 etapas, max_media", corto="Segmentado", fuente="sw/historico/trade_max_media.s",
                ops=OPS_TRADE, ppeak=25.0, ppeak_hw=25.0, hilos=1, macro="Seg"),
    "barrel": dict(nombre="Barrel, max_media en un hilo", corto="Barrel 1 hilo", fuente="build/p7/sw/trade_h0.s",
                   ops=OPS_TRADE, ppeak=6.25, ppeak_hw=25.0, hilos=1, macro="Barrel"),
    "barrel_xd": dict(nombre="Barrel con emad y devk, sw/xd/trade_xd.s en un hilo", corto="Barrel 1 hilo + ext.",
                      fuente="build/p7/sw/trade_xd_h0.s", ops=OPS_TRADE, ppeak=12.5, ppeak_hw=50.0, hilos=1,
                      macro="BarrelXd"),
    "r1": dict(nombre="R1: barrel, extensión y tabla, sw/fondo.s (4 hilos)", corto="R1 fondo", fuente="sw/fondo.s",
               ops=OPS_FONDO, ppeak=50.0, ppeak_hw=50.0, hilos=4, macro="Runo"),
    "r2": dict(nombre="R2: R1 con el vigilante, sw/fondo.s (4 hilos)", corto="R2 fondo + vigilante",
               fuente="sw/fondo.s", ops=OPS_FONDO, ppeak=50.0, ppeak_hw=50.0, hilos=4, macro="Rdos"),
}
ORDEN = ["r0", "seg", "barrel", "barrel_xd", "r1", "r2"]

# Modelos de costo en ciclos por instrucción, por clase
MODELOS = {
    "base": dict(alu=2, load=3, store=2, salto=3, nombre="Espino base, medido (make cpi)"),
    "seg_clase": dict(alu=1, load=2, store=1, salto=3, nombre="pipeline de 3 etapas, estimado en la clase 7"),
    "seg": dict(alu=1, load=2, store=1, salto=2, nombre="pipeline de 3 etapas, medido (make cpi-seg)"),
    "barrel": dict(alu=4, load=4, store=4, salto=4, nombre="barrel, 4 ciclos por instrucción de un hilo"),
}


def lazo(modelo):
    """Ciclos de una vuelta del sondeo: lw, andi y beqz tomado."""
    m = MODELOS[modelo]
    return m["load"] + m["alu"] + m["salto"]


# ---------------------------------------------------------------------------- lectura
def leer_recursos():
    r = {}
    txt = open(f"{M}/recursos.txt", encoding="utf-8").read()
    pat = (r"^p7_(\w+) +celdas +(\d+) de 1280, BRAM +(\d+) de 16, LUT4 +(\d+), fmax min +([\d.]+) "
           r"mediana +([\d.]+) max +([\d.]+) MHz, cierran a 25 MHz (\d+) de (\d+)")
    for mm in re.finditer(pat, txt, re.M):
        r[mm.group(1)] = dict(celdas=int(mm.group(2)), bram=int(mm.group(3)), lut=int(mm.group(4)),
                              fmin=float(mm.group(5)), fmed=float(mm.group(6)), fmax=float(mm.group(7)),
                              cierran=int(mm.group(8)), semillas=int(mm.group(9)))
    commit = re.search(r"Commit de partida: (\w+)", txt).group(1)
    return r, commit


def leer_gemelo():
    g = {}
    txt = open(f"{M}/gemelo.txt", encoding="utf-8").read()
    for mm in re.finditer(r"^(\w+) (r\d) \| Peor caso precio->decision: (\d+) ciclos \(disponibles: (\d+)\)", txt, re.M):
        g.setdefault(mm.group(1), {}).setdefault(mm.group(2), {})["peor_oficial"] = int(mm.group(3))
    for mm in re.finditer(r"^(\w+) (r\d) \| Patrimonio final: +(\d+)", txt, re.M):
        g[mm.group(1)][mm.group(2)]["patrimonio"] = int(mm.group(3))
    pat = (r"^(\w+) (r\d) \| Gemelo: (\d+) ticks medidos\. Respuesta: ([\d.]+) ciclos e IC ([\d.]+) en promedio, "
           r"peor caso (\d+) ciclos e IC (\d+)\. Tick completo: ([\d.]+) ciclos e IC ([\d.]+) en promedio, "
           r"peor caso (\d+) ciclos e IC (\d+)")
    for mm in re.finditer(pat, txt, re.M):
        d = g[mm.group(1)][mm.group(2)]
        d.update(ticks=int(mm.group(3)), r_c=float(mm.group(4)), r_ic=float(mm.group(5)), r_cp=int(mm.group(6)),
                 r_icp=int(mm.group(7)), t_c=float(mm.group(8)), t_ic=float(mm.group(9)), t_cp=int(mm.group(10)),
                 t_icp=int(mm.group(11)))
    commit = re.search(r"Commit de partida: (\w+)", txt).group(1)
    return g, commit


def leer_perfil(etq):
    filas = []
    for linea in open(f"{M}/perfil/{etq}.txt", encoding="utf-8"):
        if linea.startswith("#"):
            continue
        h, d, w, n, c = linea.split()
        filas.append((int(h), int(d, 16), int(w, 16), int(n), int(c)))
    return filas


# ---------------------------------------------------------------------------- perfil por fase
def analizar(etq):
    """Ciclos, instrucciones y bytes por tick de cada fase, con el perfil a 0,1 ms."""
    v = VAR["r1" if etq == "r2" else etq]
    filas = leer_perfil("r1" if etq == "r2" else etq)
    fondo = v["fuente"] == "sw/fondo.s"
    fase, mapa = fuentes.fases_fondo(v["fuente"]) if fondo else fuentes.fases_trade(v["fuente"])
    esc = [d for d in fase if fase[d] == "escribir"]
    nref = sum(n for h, d, w, n, c in filas if h == 0 and d in esc)
    por = {}            # (hilo, fase) -> dict
    for h, d, w, n, c in filas:
        f = fase.get(d, "fuera")
        x = por.setdefault((h, f), dict(c=0.0, ic=0.0, alu=0.0, load=0.0, store=0.0, salto=0.0, bytes=0.0))
        x["c"] += c / nref
        x["ic"] += n / nref
        x[fuentes.clase(w)] += n / nref
        if f not in ("arranque",) and not (h == 0 and f == "esperar"):
            x["bytes"] += fuentes.tamano_acceso(w) * min(n, nref) / nref
    return dict(por=por, nref=nref, fondo=fondo)


FASES_RESP_TRADE = ["leer", "media_dev", "decidir", "escribir"]
FASES_KERNEL_TRADE = ["leer", "media_dev", "decidir", "escribir", "media_s", "volver"]
FASES_RESP_FONDO = ["leer", "publicar", "regla", "votos", "pesos", "voto", "escribir"]
FASES_KERNEL_FONDO = FASES_RESP_FONDO + ["telemetria"]


def resumen(etq, gem):
    a = analizar(etq)
    por = a["por"]
    g = gem["r1" if etq == "r2" else etq]["r3"]
    fr, fk = (FASES_RESP_FONDO, FASES_KERNEL_FONDO) if a["fondo"] else (FASES_RESP_TRADE, FASES_KERNEL_TRADE)
    cero = dict(c=0.0, ic=0.0, alu=0.0, load=0.0, store=0.0, salto=0.0, bytes=0.0)
    fase0 = {f: por.get((0, f), cero) for f in set(fr) | set(fk) | {"esperar"}}
    resp_fases = sum(fase0[f]["c"] for f in fr)
    det = g["r_c"] - resp_fases
    k_c = sum(fase0[f]["c"] for f in fk)
    k_ic = sum(fase0[f]["ic"] for f in fk)
    byts = sum(fase0[f]["bytes"] for f in fk)
    ic_hilos = k_ic
    if a["fondo"]:
        for h in (1, 2, 3):
            for (hh, f), x in por.items():
                if hh == h and f not in ("arranque", "esperar"):
                    ic_hilos += x["ic"]
                if hh == h and f != "arranque":
                    byts += x["bytes"]
    ops = VAR[etq]["ops"]
    return dict(a=a, fase0=fase0, det=det, k_c=k_c, k_ic=k_ic, ic_hilos=ic_hilos, bytes=byts,
                cpi_k=k_c / k_ic, mops=ops * F_CLK / k_c, intens=ops / byts, ops=ops, g=g, fr=fr, fk=fk)


# ---------------------------------------------------------------------------- formato
def f2(x, d=2):
    return f"{x:.{d}f}"


def tex(x, d=2):
    if isinstance(x, str):
        return x
    s = f"{x:,.{d}f}" if abs(x) >= 10000 else f"{x:.{d}f}"
    return s.replace(",", "\\,").replace(".", "{,}")


def escribir_csv(ruta, cab, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cab)
        w.writerows(filas)


MACROS = []


def macro(nombre, valor, d=2):
    assert re.fullmatch(r"[A-Za-z]+", nombre), nombre
    MACROS.append((nombre, tex(valor, d) if not isinstance(valor, int) else (f"{valor:,}".replace(",", "\\,") if valor >= 10000 else str(valor))))


# ---------------------------------------------------------------------------- tablas
def tabla_variantes(rec, gem, R):
    cab = ["variante", "descripcion", "celdas", "lut4", "bram", "fmax_min_mhz", "fmax_mediana_mhz", "cierran_25mhz",
           "resp_prom_ciclos", "resp_peor_ciclos", "tick_prom_ciclos", "tick_peor_ciclos", "ic_resp_prom",
           "ic_tick_prom", "cpi_resp", "ciclos_kernel", "ic_kernel_hilo0", "ic_kernel_todos", "cpi_kernel",
           "ops_utiles_tick", "mops_logrado", "ppeak_mops", "speedup_resp", "speedup_mops",
           "uso_r1_pct", "uso_r2_pct", "uso_r3_pct", "patrimonio_r3"]
    filas, txt = [], []
    base = R["r0"]
    for etq in ORDEN:
        v, r, s = VAR[etq], rec[etq], R[etq]
        g = gem["r1" if etq == "r2" else etq]
        uso = {k: 100.0 * g[k]["peor_oficial"] / PRESUPUESTO[k] for k in PERIODOS}
        sp_r = base["g"]["r_c"] / s["g"]["r_c"]
        sp_m = s["mops"] / base["mops"]
        filas.append([etq, v["nombre"], r["celdas"], r["lut"], r["bram"], r["fmin"], r["fmed"], f"{r['cierran']}/{r['semillas']}",
                      f2(s["g"]["r_c"]), s["g"]["r_cp"], f2(s["g"]["t_c"]), s["g"]["t_cp"], f2(s["g"]["r_ic"]),
                      f2(s["g"]["t_ic"]), f2(s["g"]["r_c"] / s["g"]["r_ic"], 3), f2(s["k_c"]), f2(s["k_ic"]),
                      f2(s["ic_hilos"]), f2(s["cpi_k"], 3), s["ops"], f2(s["mops"], 3), v["ppeak"], f2(sp_r, 3),
                      f2(sp_m, 3), f2(uso["r1"], 3), f2(uso["r2"], 3), f2(uso["r3"], 3), g["r3"]["patrimonio"]])
        m = v["macro"]
        macro(f"pSieteCeldas{m}", r["celdas"])
        macro(f"pSieteLut{m}", r["lut"])
        macro(f"pSieteBram{m}", r["bram"])
        macro(f"pSieteFmaxMin{m}", r["fmin"])
        macro(f"pSieteFmaxMed{m}", r["fmed"])
        macro(f"pSieteRespProm{m}", s["g"]["r_c"])
        macro(f"pSieteRespPeor{m}", s["g"]["r_cp"])
        macro(f"pSieteTickProm{m}", s["g"]["t_c"])
        macro(f"pSieteTickPeor{m}", s["g"]["t_cp"])
        macro(f"pSieteIcResp{m}", s["g"]["r_ic"])
        macro(f"pSieteCpiResp{m}", s["g"]["r_c"] / s["g"]["r_ic"], 3)
        macro(f"pSieteKernelCiclos{m}", s["k_c"])
        macro(f"pSieteKernelIc{m}", s["k_ic"])
        macro(f"pSieteKernelIcHilos{m}", s["ic_hilos"])
        macro(f"pSieteCpiKernel{m}", s["cpi_k"], 3)
        macro(f"pSieteOps{m}", s["ops"])
        macro(f"pSieteMops{m}", s["mops"])
        macro(f"pSietePpeak{m}", v["ppeak"])
        macro(f"pSieteSpeedupResp{m}", sp_r)
        macro(f"pSieteSpeedupMops{m}", sp_m)
        macro(f"pSieteUsoRuno{m}", uso["r1"], 3)
        macro(f"pSieteUsoRdos{m}", uso["r2"], 3)
        macro(f"pSieteUsoRtres{m}", uso["r3"], 2)
        macro(f"pSieteIntensidad{m}", s["intens"], 3)
        macro(f"pSieteBytes{m}", s["bytes"])
    escribir_csv(f"{M}/variantes.csv", cab, filas)

    w = txt.append
    w("Tabla de variantes de co-diseno (punto 3.3 del enunciado)")
    w("Generado por tools/p7/tablas.py (make p7-rapido) desde las mediciones de docs/mediciones/p7/. No editar a mano.")
    w("")
    w("Celdas, LUT4, BRAM y fmax: recursos.txt (nextpnr, 10 semillas). Ciclos: gemelo.txt (gemelo validado contra el")
    w("RTL; rtl.txt confirma R0 y el segmentado tick por tick, y R1 y R2 contra la medicion del RTL de P5). Serie de")
    w("practica completa a 0,1 ms. R2 tiene los ciclos de R1: el vigilante solo observa (rtl.txt). Reloj de 25 MHz.")
    w(f"Operacion util: {OPS_TRADE} por tick en max_media, {OPS_FONDO} en el fondo (definicion en docs/codiseno.md, seccion 3).")
    w("")
    w(f"{'':<4}{'Variante':<24}{'Celdas':>7}{'LUT4':>6}{'BRAM':>5}{'Fmax min':>9}{'med.':>7}{'Cierran':>10}")
    for etq in ORDEN:
        r = rec[etq]
        w(f"{'':<4}{VAR[etq]['corto']:<24}{r['celdas']:>7}{r['lut']:>6}{r['bram']:>5}{r['fmin']:>9.2f}{r['fmed']:>7.2f}"
          f"{str(r['cierran']) + ' de ' + str(r['semillas']):>10}")
    w("")
    w("    Ciclos por tick a 0,1 ms (respuesta: de byte_done a DECISION; tick completo: hasta volver a sondear)")
    w(f"{'':<4}{'Variante':<24}{'Resp. prom':>11}{'peor':>6}{'Tick prom':>10}{'peor':>6}{'IC resp':>8}{'CPI resp':>9}")
    for etq in ORDEN:
        g = R[etq]["g"]
        w(f"{'':<4}{VAR[etq]['corto']:<24}{g['r_c']:>11.2f}{g['r_cp']:>6}{g['t_c']:>10.2f}{g['t_cp']:>6}"
          f"{g['r_ic']:>8.2f}{g['r_c'] / g['r_ic']:>9.3f}")
    w("")
    w("    Kernel (de leer PRICE a volver al sondeo, sin la espera), desempeño y speedup contra R0")
    w(f"{'':<4}{'Variante':<24}{'Ciclos':>7}{'IC h0':>7}{'IC 4h':>7}{'CPI':>7}{'Ops':>5}{'MOPS':>8}{'Ppeak':>7}"
      f"{'S resp':>8}{'S MOPS':>8}")
    for etq in ORDEN:
        s = R[etq]
        w(f"{'':<4}{VAR[etq]['corto']:<24}{s['k_c']:>7.2f}{s['k_ic']:>7.2f}{s['ic_hilos']:>7.2f}{s['cpi_k']:>7.3f}"
          f"{s['ops']:>5}{s['mops']:>8.3f}{VAR[etq]['ppeak']:>7.2f}{base['g']['r_c'] / s['g']['r_c']:>8.3f}"
          f"{s['mops'] / base['mops']:>8.3f}")
    w("")
    w("    Peor caso de la respuesta contra el presupuesto de cada ronda")
    w(f"{'':<4}{'Variante':<24}" + "".join(f"{'ronda ' + k[1] + ' (' + str(PRESUPUESTO[k]) + ')':>22}" for k in ("r1", "r2", "r3")))
    for etq in ORDEN:
        g = gem["r1" if etq == "r2" else etq]
        w(f"{'':<4}{VAR[etq]['corto']:<24}" + "".join(
            f"{str(g[k]['peor_oficial']) + ' ciclos, ' + f2(100.0 * g[k]['peor_oficial'] / PRESUPUESTO[k], 3) + ' %':>22}"
            for k in ("r1", "r2", "r3")))
    w("")
    w("    Variantes que no existen en el RTL")
    w("    Espino base con la extension y segmentado con la extension: emad y devk estan solo en el core barrel")
    w("    (rtl/espino_core/espino_xd.v se conecta en espino_barrel_core.v). Construirlas obliga a tocar el RTL")
    w("    compartido de R0, que paso la puerta: quedan como prediccion con Amdahl en amdahl.txt (decision T101).")
    w("")
    w("    Lectura")
    w(f"    - Por hilo, la variante mas rapida es el segmentado: responde en {f2(R['seg']['g']['r_c'])} ciclos, "
      f"{f2(base['g']['r_c'] / R['seg']['g']['r_c'])} veces mas rapido que R0.")
    w(f"    - R1, el que compite, responde en {f2(R['r1']['g']['r_c'])} ciclos en promedio y {R['r1']['g']['r_cp']} en el peor caso:"
      f" {f2(R['r1']['g']['r_c'] / base['g']['r_c'])} veces mas lento que R0.")
    w(f"      Pero hace {OPS_FONDO} operaciones utiles por tick y no {OPS_TRADE}: su desempeño logrado es "
      f"{f2(R['r1']['mops'], 3)} MOPS contra {f2(base['mops'], 3)} de R0 ({f2(R['r1']['mops'] / base['mops'])} veces).")
    w(f"    - Todas usan menos del {math.ceil(max(100.0 * gem['r1' if e == 'r2' else e]['r3']['peor_oficial'] / PRESUPUESTO['r3'] for e in ORDEN))} % del presupuesto de la ronda 3.")
    open(f"{M}/variantes.txt", "w", encoding="utf-8").write("\n".join(txt) + "\n")


NOMBRES_FASE = dict(fuentes.NOMBRE_FASE)
NOMBRES_FASE.update(fuentes.NOMBRE_FASE_FONDO)
NOMBRES_FASE["deteccion"] = "esperar el precio: deteccion por el sondeo"


def tabla_perfil(R):
    filas, txt = [], []
    w = txt.append
    w("Perfil del tick: en que fase se van los ciclos (punto 3.3, perfilado)")
    w("Generado por tools/p7/tablas.py (make p7-rapido) desde docs/mediciones/p7/perfil/. No editar a mano.")
    w("")
    w("El gemelo (build/gemelo --perfil) cuenta, por hilo y por direccion, las instrucciones ejecutadas y sus ciclos")
    w("en la serie de practica completa a 0,1 ms. tools/p7/fuentes.py asigna cada direccion a una fase leyendo el")
    w("programa. Ciclos por tick = ciclos de la fase / ticks. La deteccion (cuanto demora el sondeo en ver el")
    w("precio) es la respuesta medida menos las fases que van antes de la escritura: no se estima.")
    w("")
    for etq in ["r0", "seg", "barrel", "barrel_xd", "r1"]:
        s = R[etq]
        w(f"== {VAR[etq]['nombre']}")
        w(f"   {'fase':<46}{'ciclos/tick':>12}{'instr./tick':>12}{'% resp.':>9}{'% kernel':>9}")
        fases = ["deteccion"] + s["fk"]
        for f in fases:
            c = s["det"] if f == "deteccion" else s["fase0"][f]["c"]
            ic = float("nan") if f == "deteccion" else s["fase0"][f]["ic"]
            pr = 100.0 * c / s["g"]["r_c"] if (f == "deteccion" or f in s["fr"]) else float("nan")
            pk = float("nan") if f == "deteccion" else 100.0 * c / s["k_c"]
            w(f"   {NOMBRES_FASE.get(f, f):<46}{c:>12.2f}{ic:>12.2f}{pr:>9.1f}{pk:>9.1f}".replace("nan", "  -"))
            filas.append([etq, f, f2(c), "" if f == "deteccion" else f2(ic), "" if pr != pr else f2(pr, 1),
                          "" if pk != pk else f2(pk, 1)])
        w(f"   {'respuesta medida (gemelo)':<46}{s['g']['r_c']:>12.2f}")
        w(f"   {'kernel (suma de las fases sin la deteccion)':<46}{s['k_c']:>12.2f}{s['k_ic']:>12.2f}")
        espera = s["fase0"]["esperar"]["c"]
        w(f"   {'sondeo en todo el tick (de 2500 ciclos)':<46}{espera:>12.2f}{s['fase0']['esperar']['ic']:>12.2f}"
          f"{100.0 * espera / 2500:>9.1f} % del periodo")
        if etq == "r1":
            w("   Gestores (hilos 1 a 3), instrucciones por tick fuera del lazo de espera:")
            por = s["a"]["por"]
            for h in (1, 2, 3):
                partes = [f"{NOMBRES_FASE.get(f, f)} {x['ic']:.2f}" for (hh, f), x in sorted(por.items()) if hh == h
                          and f not in ("arranque", "esperar")]
                w(f"     hilo {h}: " + ", ".join(partes))
        mayor = max(s["fr"], key=lambda f: s["fase0"][f]["c"])
        mayor_k = max(s["fk"], key=lambda f: s["fase0"][f]["c"])
        w(f"   Fase mas larga de la respuesta: {NOMBRES_FASE.get(mayor, mayor)} ({s['fase0'][mayor]['c']:.2f} ciclos);"
          f" del kernel: {NOMBRES_FASE.get(mayor_k, mayor_k)} ({s['fase0'][mayor_k]['c']:.2f}).")
        if etq in ("r0", "seg", "barrel"):
            media = s["fase0"]["media_dev"]["c"] + s["fase0"]["media_s"]["c"]
            w(f"   Actualizar la media (dev y S) suma {media:.2f} ciclos: {100.0 * media / s['k_c']:.1f} % del kernel.")
            macro(f"pSieteMediaPct{VAR[etq]['macro']}", 100.0 * media / s["k_c"], 1)
            macro(f"pSieteMediaCiclos{VAR[etq]['macro']}", media)
        macro(f"pSieteDeteccion{VAR[etq]['macro']}", s["det"])
        w("")
    escribir_csv(f"{M}/perfil.csv", ["variante", "fase", "ciclos_tick", "instrucciones_tick", "pct_respuesta", "pct_kernel"], filas)
    open(f"{M}/perfil.txt", "w", encoding="utf-8").write("\n".join(txt) + "\n")


def predecir(R, programa, modelo, ventana):
    """Ciclos predichos por fase de `programa` (perfil medido) con `modelo`. ventana: 'resp' o 'kernel'."""
    s = R[programa]
    m = MODELOS[modelo]
    fases = s["fr"] if ventana == "resp" else s["fk"]
    out = {f: sum(s["fase0"][f][k] * m[k] for k in ("alu", "load", "store", "salto")) for f in fases}
    if ventana == "resp":
        out["deteccion"] = R["r0"]["det"] * lazo(modelo) / lazo("base")
    return out


def medido(R, etq, ventana):
    s = R[etq]
    fases = s["fr"] if ventana == "resp" else s["fk"]
    out = {f: s["fase0"][f]["c"] for f in fases}
    if ventana == "resp":
        out["deteccion"] = s["det"]
    return out


def tabla_amdahl(R):
    txt, filas = [], []
    w = txt.append
    w("Amdahl generalizado: speedup predicho contra medido (punto 3.3)")
    w("Generado por tools/p7/tablas.py (make p7-rapido). No editar a mano.")
    w("")
    w("S = 1 / sum(f_i / F_i). La fraccion f_i de cada fase sale del perfil medido de la variante de partida.")
    w("El factor F_i predicho sale de aplicar el modelo de costo de la variante nueva a las instrucciones de la")
    w("fase (contadas en el perfil, por clase: ALU, load, store y salto). La deteccion del sondeo se predice")
    w("escalando la de R0 por la duracion de una vuelta del lazo (lw, andi, beqz tomado) en cada modelo.")
    w("El F_i medido es el cociente de los ciclos medidos de la fase en las dos variantes.")
    w("")
    for nom, m in MODELOS.items():
        w(f"  modelo {nom:<10} ALU {m['alu']}, load {m['load']}, store {m['store']}, salto tomado {m['salto']}"
          f"  ({m['nombre']}); vuelta del sondeo {lazo(nom)} ciclos")
    w("")
    casos = [
        # (etiqueta, desde, programa nuevo, modelo, variante medida o None, descripcion)
        ("seg_clase", "r0", "r0", "seg_clase", "seg", "R0 -> segmentado, con el CPI que estimó la clase 7"),
        ("seg", "r0", "r0", "seg", "seg", "R0 -> segmentado, con el modelo de costo medido"),
        ("barrel", "r0", "r0", "barrel", "barrel", "R0 -> barrel, sw/trade.s en un hilo"),
        ("xd_barrel", "barrel", "barrel_xd", "barrel", "barrel_xd", "barrel -> barrel con emad y devk (la extensión sola)"),
        ("barrel_xd", "r0", "barrel_xd", "barrel", "barrel_xd", "R0 -> barrel con la extensión"),
        ("base_xd", "r0", "barrel_xd", "base", None, "R0 -> Espino base con la extensión (no existe en el RTL)"),
        ("seg_xd", "r0", "barrel_xd", "seg", None, "R0 -> segmentado con la extensión (no existe en el RTL)"),
    ]
    for ventana, titulo in (("resp", "respuesta (de byte_done a DECISION)"), ("kernel", "kernel (de leer PRICE a volver al sondeo)")):
        w(f"=== Ventana: {titulo}")
        for etq, desde, prog, modelo, med, desc in casos:
            if etq == "xd_barrel":
                # la extension sola: el mismo core, la deteccion no cambia
                base_f = medido(R, "barrel", ventana)
                pred = predecir(R, "barrel_xd", "barrel", ventana)
                if ventana == "resp":
                    pred["deteccion"] = R["barrel"]["det"]
            else:
                base_f = medido(R, desde, ventana)
                pred = predecir(R, prog, modelo, ventana)
            tot0 = sum(base_f.values())
            tot0_med = R[desde]["g"]["r_c"] if ventana == "resp" else R[desde]["k_c"]
            s_pred = tot0 / sum(pred.values())
            w(f"--- {desc}")
            w(f"    {'fase':<44}{'ciclos antes':>13}{'f':>8}{'F predicho':>11}{'F medido':>10}")
            medf = medido(R, med, ventana) if med else None
            for f in base_f:
                fi = base_f[f] / tot0
                Fp = base_f[f] / pred[f] if pred[f] else float("inf")
                Fm = (base_f[f] / medf[f] if medf and medf.get(f) else float("nan"))
                w(f"    {NOMBRES_FASE.get(f, f):<44}{base_f[f]:>13.2f}{fi:>8.3f}{Fp:>11.3f}" + (f"{Fm:>10.3f}" if medf else f"{'-':>10}"))
            s_med = (tot0_med / (R[med]["g"]["r_c"] if ventana == "resp" else R[med]["k_c"])) if med else None
            linea = f"    S predicho {s_pred:.3f} ({tot0 / s_pred:.2f} ciclos)"
            if med:
                nuevo = R[med]["g"]["r_c"] if ventana == "resp" else R[med]["k_c"]
                linea += f", S medido {s_med:.3f} ({nuevo:.2f} ciclos), diferencia {100.0 * (s_pred - s_med) / s_med:+.1f} %"
            else:
                linea += ", sin medicion: la variante no existe en el RTL"
            w(linea)
            filas.append([ventana, etq, desde, desc, f2(s_pred, 3), "" if s_med is None else f2(s_med, 3),
                          f2(tot0 / s_pred), "" if not med else f2(R[med]["g"]["r_c"] if ventana == "resp" else R[med]["k_c"])])
            mk = {"seg_clase": "SegClase", "seg": "Seg", "barrel": "Barrel", "xd_barrel": "XdSobreBarrel",
                  "barrel_xd": "BarrelXd", "base_xd": "BaseXd", "seg_xd": "SegXd"}[etq]
            vk = "Resp" if ventana == "resp" else "Kernel"
            macro(f"pSieteAmdahlPred{vk}{mk}", s_pred, 3)
            macro(f"pSieteAmdahlCiclosPred{vk}{mk}", tot0 / s_pred)
            if med:
                macro(f"pSieteAmdahlMed{vk}{mk}", s_med, 3)
        w("")
    # Amdahl clasico sobre la fase mas pesada: la media
    s = R["r0"]
    media = s["fase0"]["media_dev"]["c"] + s["fase0"]["media_s"]["c"]
    f = media / s["k_c"]
    w("=== Amdahl clasico sobre la fase que mas pesa en el kernel de R0: actualizar la media")
    w(f"    f = {media:.2f} / {s['k_c']:.2f} = {f:.3f}. Con emad y devk las 14 instrucciones de la media pasan a 2.")
    pxd = predecir(R, "barrel_xd", "base", "kernel")
    Fm = media / (pxd["media_dev"] + pxd["media_s"])
    w(f"    En el Espino base eso es F = {Fm:.2f} y S = 1 / ((1 - f) + f / F) = {1 / ((1 - f) + f / Fm):.3f}."
      f" Limite con F infinito: {1 / (1 - f):.3f}.")
    macro("pSieteAmdahlFmedia", f, 3)
    macro("pSieteAmdahlFfactor", Fm)
    macro("pSieteAmdahlLimite", 1 / (1 - f), 3)
    w("")
    w("=== El fondo (R1) no es un speedup del mismo kernel")
    r1 = R["r1"]
    w(f"    R1 hace {OPS_FONDO} operaciones utiles por tick en 4 hilos; R0 hace {OPS_TRADE} en uno. La respuesta de R1")
    w(f"    ({r1['g']['r_c']:.2f} ciclos) la domina la espera de los votos: {r1['fase0']['votos']['c']:.2f} ciclos del supervisor"
      f" ({100.0 * r1['fase0']['votos']['c'] / r1['g']['r_c']:.1f} %).")
    w(f"    Un gestor ejecuta {sum(x['ic'] for (h, ff), x in r1['a']['por'].items() if h == 1 and ff not in ('arranque', 'esperar')):.2f}"
      " instrucciones por tick a 4 ciclos cada una: es el piso de esa espera.")
    macro("pSieteVotosCiclosRuno", r1["fase0"]["votos"]["c"])
    macro("pSieteVotosPctRuno", 100.0 * r1["fase0"]["votos"]["c"] / r1["g"]["r_c"], 1)
    escribir_csv(f"{M}/amdahl.csv", ["ventana", "caso", "desde", "descripcion", "s_predicho", "s_medido",
                                     "ciclos_predichos", "ciclos_medidos"], filas)
    open(f"{M}/amdahl.txt", "w", encoding="utf-8").write("\n".join(txt) + "\n")


def tabla_escalera(R, rec):
    """La escalera de la clase 7 aplicada al kernel de max_media."""
    b = R["r0"]
    xd = R["barrel_xd"]
    ic_xd = xd["k_ic"]

    def ciclos_modelo(prog, modelo):
        return sum(predecir(R, prog, modelo, "kernel").values())

    pasos = [
        # paso, descripcion, estado, ops, ic, ciclos, cpi_clase, costo
        ("0", "Espino base, solo software (R0)", "medido", OPS_TRADE, b["k_ic"], b["k_c"], 2.35, rec["r0"]["celdas"]),
        ("1", "+ extensión de la ISA (devk, emad) en el Espino base", "estimado: modelo de costo medido del base",
         OPS_TRADE, ic_xd, ciclos_modelo("barrel_xd", "base"), 2.35, None),
        ("2", "pipeline de 3 etapas, solo software", "medido", OPS_TRADE, R["seg"]["k_ic"], R["seg"]["k_c"], 1.5,
         rec["seg"]["celdas"]),
        ("1+2", "pipeline de 3 etapas + extensión", "estimado: modelo de costo medido del segmentado", OPS_TRADE, ic_xd,
         ciclos_modelo("barrel_xd", "seg"), 1.5, None),
        ("2b", "barrel, un hilo, solo software", "medido", OPS_TRADE, R["barrel"]["k_ic"], R["barrel"]["k_c"], None,
         rec["barrel"]["celdas"]),
        ("1+2b", "barrel, un hilo + extensión", "medido", OPS_TRADE, ic_xd, xd["k_c"], None, rec["barrel_xd"]["celdas"]),
        ("2c", "barrel, 4 hilos + extensión: el fondo (R1)", "medido", OPS_FONDO, R["r1"]["ic_hilos"], R["r1"]["k_c"],
         None, rec["r1"]["celdas"]),
        # Estimaciones con CPI ideal 1, como hizo la clase
        ("3", "instrucciones a medida (mmpos y mmbyte) sobre el pipeline", "estimado: CPI ideal 1", OPS_TRADE, 7, 7, 1.0, None),
        ("4", "SIMD de 2 carriles de 16 bits: las 4 reglas y el voto", "estimado: CPI ideal 1", 38, 10, 10, 1.0, None),
    ]
    txt, filas = [], []
    w = txt.append
    w("La escalera de co-diseno de la clase 7, aplicada al kernel de max_media (actualizar la media y decidir)")
    w("Generado por tools/p7/tablas.py (make p7-rapido). No editar a mano.")
    w("")
    w("Formato de la clase: instrucciones por operacion, ciclos por operacion, MOPS (operaciones utiles x 25 MHz")
    w("/ ciclos), speedup contra el paso 0 y costo. La columna 'clase' es la estimacion con el metodo de la clase:")
    w("IC x 2,35 en el Espino base (CPI del mix), IC x 1,5 en el pipeline (CPI estimado) y CPI ideal 1 en los")
    w("pasos 3 y 4. Lo 'medido' sale del perfil del gemelo; lo 'estimado' no esta construido.")
    w("")
    w(f"  {'paso':<6}{'descripcion':<56}{'ops':>4}{'IC':>7}{'IC/op':>7}{'ciclos':>8}{'cic/op':>8}{'MOPS':>8}{'S':>7}"
      f"{'clase':>8}{'celdas':>8}  estado")
    for paso, desc, est, ops, ic, cic, cpi_c, costo in pasos:
        mops = ops * F_CLK / cic
        s = mops / b["mops"]
        clase = f"{ic * cpi_c / ops:.2f}" if cpi_c else "-"
        w(f"  {paso:<6}{desc:<56}{ops:>4}{ic:>7.2f}{ic / ops:>7.3f}{cic:>8.2f}{cic / ops:>8.3f}{mops:>8.3f}{s:>7.2f}"
          f"{clase:>8}{(str(costo) if costo else '-'):>8}  {est}")
        filas.append([paso, desc, est, ops, f2(ic), f2(ic / ops, 3), f2(cic), f2(cic / ops, 3), f2(mops, 3), f2(s, 3),
                      clase, costo or ""])
        mk = {"0": "Cero", "1": "Uno", "2": "Dos", "1+2": "UnoDos", "2b": "DosB", "1+2b": "UnoDosB", "2c": "DosC",
              "3": "Tres", "4": "Cuatro"}[paso]
        macro(f"pSieteEscMops{mk}", mops, 3)
        macro(f"pSieteEscCicOp{mk}", cic / ops, 3)
        macro(f"pSieteEscIcOp{mk}", ic / ops, 3)
        macro(f"pSieteEscSpeedup{mk}", s)
    w("")
    w("  Paso 3 (estimado): dos instrucciones a medida, como las de Xpulp que fusionan operaciones que siempre van")
    w("  juntas. mmpos rd, rs1: pos = (pos | dev < E) & (dev < X) con los dos umbrales fijos (4 operaciones);")
    w("  mmbyte: de pos al byte 0x7F o 0xBF. El kernel queda en lw, devk, mmpos, mmbyte, sw, emad y j: 7.")
    w("  Paso 4 (estimado): las cuatro reglas del fondo con el mismo precio, empaquetadas de a dos en carriles de")
    w("  16 bits (S necesita 13 bits y dev 14 con signo: no caben 4 carriles de 8). lw, 2 devk.v, 2 mmpos.v, 2")
    w("  emad.v, una instruccion de voto ponderado (6 operaciones), sw y j: 10 instrucciones, 4 x 8 + 6 = 38 ops.")
    w("")
    w("  Comparacion con lo que estimo la clase")
    for paso, desc, est, ops, ic, cic, cpi_c, costo in pasos:
        if est == "medido" and cpi_c:
            w(f"  - paso {paso}: medido {cic:.2f} ciclos, metodo de la clase {ic * cpi_c:.2f}"
              f" ({100.0 * (ic * cpi_c - cic) / cic:+.1f} %).")
    w("    El pipeline medido supera la estimacion de la clase porque el salto tomado cuesta 2 ciclos y no 3")
    w("    (docs/espino_segmentado.md). En el Espino base el kernel tiene menos loads y saltos que el mix de la")
    w(f"    clase: su CPI es {b['cpi_k']:.3f} y no 2,35.")
    escribir_csv(f"{M}/escalera.csv", ["paso", "descripcion", "estado", "ops_utiles", "ic", "ic_por_op", "ciclos",
                                       "ciclos_por_op", "mops", "speedup", "ciclos_por_op_clase", "celdas"], filas)
    open(f"{M}/escalera.txt", "w", encoding="utf-8").write("\n".join(txt) + "\n")
    return pasos


# ---------------------------------------------------------------------------- roofline
COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]


def roofline(R, pasos):
    puntos = []   # etiqueta, I, P, Ppeak, medido
    for i, etq in enumerate(["r0", "seg", "barrel", "barrel_xd", "r1"]):
        s = R[etq]
        etiqueta = VAR[etq]["corto"] + (" y R2" if etq == "r1" else "")
        puntos.append((etiqueta, s["intens"], s["mops"], VAR[etq]["ppeak"], True, COLORES[i]))
    # estimados: con los bytes del programa con extension (8 por tick) y del fondo para el paso 4
    # Los pasos estimados mueven lo mismo que sw/xd/trade_xd.s: el precio y la decision (8 bytes por tick).
    by_xd = R["barrel_xd"]["bytes"]
    for paso, desc, est, ops, ic, cic, cpi_c, costo in pasos:
        if paso in ("1", "1+2", "3", "4"):
            puntos.append((f"paso {paso} (estimado)", ops / by_xd, ops * F_CLK / cic, None, False, "#6b6b6b"))
    techos = [(6.25, "6,25: barrel, 1 hilo"), (12.5, "12,5: Espino base; barrel 1 hilo con extensión"),
              (25.0, "25: segmentado; barrel 4 hilos"), (50.0, "50: barrel 4 hilos con extensión (R1, R2)")]
    filas = [[p[0], f2(p[1], 4), f2(p[2], 4), "" if p[3] is None else p[3], "medido" if p[4] else "estimado"] for p in puntos]
    filas += [[f"techo {t[1]}", "", "", t[0], "Ppeak"] for t in techos]
    filas.append(["quiebre del Espino base", f2(12.5 / BS, 4), "12.5", "12.5", "Ppeak / Bs"])
    escribir_csv(f"{M}/roofline.csv", ["serie", "intensidad_op_por_byte", "mops", "ppeak_mops", "tipo"], filas)

    # Geometría común: x de 0,01 a 100 Op/B, y de 0,1 a 1000 MOPS
    X0, X1, Y0, Y1 = -2, 2, -1, 3
    W, H, ML, MR, MT, MB = 720, 560, 70, 250, 20, 55

    def px(i):
        return ML + (math.log10(i) - X0) / (X1 - X0) * (W - ML - MR)

    def py(p):
        return MT + (Y1 - math.log10(p)) / (Y1 - Y0) * (H - MT - MB)

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         'font-family="Helvetica, Arial, sans-serif" font-size="12">',
         '<title>Roofline de las variantes de Espino</title>',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    for e in range(X0, X1 + 1):
        x = px(10 ** e)
        s.append(f'<line x1="{x:.1f}" y1="{MT}" x2="{x:.1f}" y2="{H - MB}" stroke="#e6e6e6"/>')
        s.append(f'<text x="{x:.1f}" y="{H - MB + 16}" text-anchor="middle" fill="#555">{10 ** e:g}</text>')
    for e in range(Y0, Y1 + 1):
        y = py(10 ** e)
        s.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{W - MR}" y2="{y:.1f}" stroke="#e6e6e6"/>')
        s.append(f'<text x="{ML - 6}" y="{y + 4:.1f}" text-anchor="end" fill="#555">{10 ** e:g}</text>')
    s.append(f'<rect x="{ML}" y="{MT}" width="{W - ML - MR}" height="{H - MT - MB}" fill="none" stroke="#999"/>')
    s.append(f'<text x="{(ML + W - MR) / 2:.0f}" y="{H - 12}" text-anchor="middle" fill="#222">'
             'Intensidad operacional I (operaciones útiles por byte)</text>')
    s.append(f'<text transform="translate(18 {(MT + H - MB) / 2:.0f}) rotate(-90)" text-anchor="middle" fill="#222">'
             'Desempeño (MOPS)</text>')
    # techo de memoria y techos de cómputo
    imin = 10 ** X0
    for pk, lab in techos:
        xq = pk / BS
        s.append(f'<line x1="{px(xq):.1f}" y1="{py(pk):.1f}" x2="{W - MR}" y2="{py(pk):.1f}" stroke="#888" '
                 'stroke-width="1.5" stroke-dasharray="5 3"/>')
        s.append(f'<text x="{W - MR + 6}" y="{py(pk) + 4:.1f}" fill="#444" font-size="11">{lab}</text>')
    s.append(f'<line x1="{px(imin):.1f}" y1="{py(imin * BS):.1f}" x2="{px(50.0 / BS):.1f}" y2="{py(50.0):.1f}" '
             'stroke="#444" stroke-width="2"/>')
    s.append(f'<text x="{px(0.02):.1f}" y="{py(0.02 * BS) - 8:.1f}" fill="#444" font-size="11" '
             f'transform="rotate(-38 {px(0.02):.1f} {py(0.02 * BS) - 8:.1f})">Bs = 100 MB/s</text>')
    s.append(f'<line x1="{px(0.125):.1f}" y1="{py(12.5):.1f}" x2="{px(0.125):.1f}" y2="{H - MB}" stroke="#bbb" '
             'stroke-dasharray="2 3"/>')
    s.append(f'<text x="{px(0.125) + 4:.1f}" y="{H - MB - 6}" fill="#666" font-size="11">0,125 Op/B</text>')
    # puntos y leyenda
    ly = py(6.25) + 32
    for k, (lab, i, p, pk, med, col) in enumerate(puntos):
        x, y = px(i), py(p)
        if med:
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{col}" stroke="#fff" stroke-width="2"/>')
        else:
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="none" stroke="{col}" stroke-width="2"/>')
        s.append(f'<title>{lab}: I = {i:.3f} Op/B, {p:.2f} MOPS</title>')
        yy = ly + 18 * k
        if med:
            s.append(f'<circle cx="{W - MR + 12}" cy="{yy - 4}" r="5" fill="{col}"/>')
        else:
            s.append(f'<circle cx="{W - MR + 12}" cy="{yy - 4}" r="5" fill="none" stroke="{col}" stroke-width="2"/>')
        s.append(f'<text x="{W - MR + 24}" y="{yy}" fill="#222" font-size="11">{lab}: {p:.2f} MOPS</text>')
    s.append("</svg>")
    open(f"{M}/roofline.svg", "w", encoding="utf-8").write("\n".join(s) + "\n")

    # Figura TikZ equivalente, en coordenadas log10 (sin pgfplots)
    t = ["% roofline.tex: generado por tools/p7/tablas.py (make p7-rapido). No editar a mano.",
         "% Uso: \\input{roofline.tex} dentro de una figura. Ejes en log10: x de 0,01 a 100 Op/B, y de 0,1 a 1000 MOPS.",
         "\\begin{tikzpicture}[x=2.2cm,y=1.6cm,font=\\small]"]
    t.append(f"  \\draw[gray!25] ({X0},{Y0}) grid ({X1},{Y1});")
    t.append(f"  \\draw[gray] ({X0},{Y0}) rectangle ({X1},{Y1});")
    for e in range(X0, X1 + 1):
        t.append(f"  \\node[below] at ({e},{Y0}) {{${tex(10.0 ** e, max(0, -e))}$}};")
    for e in range(Y0, Y1 + 1):
        t.append(f"  \\node[left] at ({X0},{e}) {{${tex(10.0 ** e, max(0, -e))}$}};")
    t.append(f"  \\node[below=5mm] at ({(X0 + X1) / 2},{Y0}) {{Intensidad operacional $I$ (Op/B)}};")
    t.append(f"  \\node[rotate=90,above=8mm] at ({X0},{(Y0 + Y1) / 2}) {{Desempeño (MOPS)}};")
    lg = math.log10
    for pk, lab in techos:
        t.append(f"  \\draw[gray,dashed,thick] ({lg(pk / BS):.4f},{lg(pk):.4f}) -- ({X1},{lg(pk):.4f}) "
                 f"node[right,black,font=\\scriptsize] {{{lab.replace(',', '{,}')}}};")
    t.append(f"  \\draw[black,thick] ({X0},{lg(imin * BS):.4f}) -- ({lg(50.0 / BS):.4f},{lg(50.0):.4f});")
    t.append(f"  \\draw[gray,dotted] ({lg(0.125):.4f},{Y0}) -- ({lg(0.125):.4f},{lg(12.5):.4f});")
    for lab, i, p, pk, med, col in puntos:
        estilo = f"fill={{rgb,255:red,{int(col[1:3], 16)};green,{int(col[3:5], 16)};blue,{int(col[5:7], 16)}}}" if med \
            else "draw=gray,thick,fill=white"
        lado = "left" if lab in ("R0 base", "Segmentado", "Barrel 1 hilo") else "right"
        t.append(f"  \\filldraw[{estilo}] ({lg(i):.4f},{lg(p):.4f}) circle (2.2pt) "
                 f"node[{lado},font=\\scriptsize,black] {{{lab}}};")
    t.append("\\end{tikzpicture}")
    open(f"{M}/roofline.tex", "w", encoding="utf-8").write("\n".join(t) + "\n")
    return puntos


# ---------------------------------------------------------------------------- ASIC
def barrel_asic(R, w, filas):
    """Edicion ASIC del barrel con xd=3 y sw/fondo.s (asic/mediciones/, asic/README.md)."""
    res_p = "asic/mediciones/resumen.txt"
    pot_p = "asic/mediciones/potencia/barrel_xd3_t40/tabla.md"
    if not (os.path.exists(res_p) and os.path.exists(pot_p)):
        w("== Espino barrel con la extension (R1): sin mediciones en asic/mediciones/")
        w("")
        return
    res = {}
    for linea in open(res_p, encoding="utf-8"):
        if " = " in linea:
            k, v = linea.strip().split(" = ")
            res[k] = float(v)
    txt = open(pot_p, encoding="utf-8").read()
    m = re.search(r"^\| típica \(.*?\) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", txt, re.M)
    sondeo, ronda3, calc = float(m.group(2)), float(m.group(3)), float(m.group(4))
    m = re.search(r"^\| típica \(.*?\) \| [\d.]+ \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", txt, re.M)
    e3, e2, e1, marg = (float(m.group(i)) for i in range(1, 5))
    fmax = res["fmax_cierre_mhz"]
    kc = R["r1"]["k_c"]
    mops = OPS_FONDO * F_CLK / kc
    mops_f = OPS_FONDO * fmax / kc
    pp = VAR["r1"]["ppeak"]
    opw = mops / (calc / 1000.0)
    ppw = pp / (calc / 1000.0)
    dado, std = res["xd3_dado_um2"], res["xd3_std_um2"]
    w("== Espino barrel con emad y devk, sw/fondo.s: el hardware de R1 (corrida barrel_xd3_t40)")
    w(f"   dado {dado:.0f} um2 ({dado / 1e6:.3f} mm2), celdas estandar {std:.0f} um2, {res['xd3_celdas']:.0f} celdas,"
      f" {res['xd3_ff']:.0f} flip-flops (el banco de registros de cuatro contextos son 2048)")
    w(f"   frecuencia: cierra en la esquina lenta hasta T = {res['t_min_cierra_ns']:g} ns ({fmax:.1f} MHz)"
      f" (asic/mediciones/corridas.md)")
    w(f"   potencia, esquina tipica: sondeo {sondeo:.3f} mW, calculo {calc:.3f} mW, ronda 3 {ronda3:.3f} mW")
    w(f"   kernel: {kc:.2f} ciclos, {OPS_FONDO} ops: {mops:.3f} MOPS a 25 MHz, {mops_f:.3f} MOPS a {fmax:.1f} MHz;"
      f" Ppeak {pp} MOPS")
    w(f"   Ops/W: kernel {opw:.1f} MOPS/W, Ppeak {ppw:.1f} MOPS/W")
    w(f"   energia por decision: ronda 3 {e3 / 1000:.3f} uJ (flujo), ronda 2 {e2 / 1000:.2f} uJ y ronda 1"
      f" {e1 / 1000:.1f} uJ (estimadas: mas sondeo)")
    w(f"   costo marginal de decidir sobre el de esperar: {marg:.2f} nJ, {marg / OPS_FONDO:.3f} nJ por operacion util")
    w("   (los cuatro hilos ejecutan una instruccion por ciclo tambien mientras sondean: esperar ya cuesta casi")
    w("   lo mismo que calcular)")
    w("")
    filas.append(["barrel_r1", round(dado), round(std), int(res["xd3_celdas"]), int(res["xd3_ff"]), f2(fmax, 1),
                  sondeo, f2(calc, 3), ronda3, f2(kc), f2(mops, 3), f2(mops_f, 3), pp, f2(opw, 1), f2(ppw, 1),
                  f2(e3 / 1000, 3), f2(e2 / 1000, 2), f2(e1 / 1000, 1), f2(marg, 3), f2(marg / OPS_FONDO, 3)])
    mk = "Barrel"
    macro(f"pSieteAsicDado{mk}", dado / 1e6, 3)
    macro(f"pSieteAsicStd{mk}", round(std))
    macro(f"pSieteAsicFmax{mk}", fmax, 1)
    macro(f"pSieteAsicPsondeo{mk}", sondeo, 1)
    macro(f"pSieteAsicPcalculo{mk}", calc, 1)
    macro(f"pSieteAsicMops{mk}", mops, 2)
    macro(f"pSieteAsicMopsFmax{mk}", mops_f, 2)
    macro(f"pSieteAsicMopsW{mk}", opw, 0)
    macro(f"pSieteAsicPpeakW{mk}", ppw, 0)
    macro(f"pSieteAsicErtres{mk}", e3 / 1000, 2)
    macro(f"pSieteAsicErdos{mk}", e2 / 1000, 1)
    macro(f"pSieteAsicEruno{mk}", e1 / 1000, 0)
    macro(f"pSieteAsicMarginal{mk}", marg, 2)
    macro(f"pSieteAsicMarginalOp{mk}", marg / OPS_FONDO, 3)


def tabla_asic(R):
    def potencias(ruta):
        txt = open(ruta, encoding="utf-8").read()
        filas = {}
        for linea in txt.splitlines():
            m = re.match(r"\| (típica|lenta|rápida) \(.*?\) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", linea)
            if m:
                filas[m.group(1)] = dict(flujo=float(m.group(2)), reloj=float(m.group(3)), sondeo=float(m.group(4)),
                                         ronda3=float(m.group(5)), calc=(float(m.group(6)) + float(m.group(7))) / 2)
            m = re.match(r"\| (típica|lenta|rápida) \(.*?\) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|", linea)
            if m and "e+" not in linea[:0]:
                pass
        en = {}
        for m in re.finditer(r"^\| (típica|lenta|rápida) \(.*?\) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.e+]+) \|",
                             txt, re.M):
            en[m.group(1)] = dict(e3=float(m.group(3)), e2=float(m.group(4)), e1=float(m.group(5)), marg=float(m.group(6)))
        return filas, en

    corr = {}
    for linea in open(f"{A}/corridas.md", encoding="utf-8"):
        c = [x.strip() for x in linea.strip().strip("|").split("|")]
        if len(c) >= 19 and re.match(r"(base|seg)_t", c[0]):
            corr[c[0]] = dict(T=float(c[2]), dado=int(c[3]), std=int(c[5]), celdas=int(c[7]), ff=int(c[8]),
                              cierra_t=c[13], todo=c[18])
    cierre = open(f"{A}/cierre.txt", encoding="utf-8").read()
    txt, filas = [], []
    w = txt.append
    w("Edicion ASIC (GF180MCU, LibreLane): area, frecuencia, potencia, Ops/s, Ops/W y energia por decision")
    w("Generado por tools/p7/tablas.py (make p7-rapido) desde docs/mediciones/asic/. No editar a mano.")
    w("")
    w("Procedencia: docs/mediciones/asic/LEEME.md. Son calculos del flujo (OpenSTA con actividad de la simulacion")
    w("del netlist final ejecutando el programa), no mediciones de silicio. El base y el segmentado vienen de la")
    w("factibilidad (sw/trade.s); el barrel con la extension y el fondo (sw/fondo.s, el hardware de R1) es la")
    w("edicion ASIC del 17/11 (asic/README.md), con sus mediciones en asic/mediciones/.")
    w(f"Ops/s con la definicion de P7: {OPS_TRADE} operaciones utiles por tick y los ciclos del kernel medidos en la FPGA")
    w("(el core del macro son los mismos archivos de rtl/espino_core; el segmentado del macro usa la ROM")
    w("combinacional, con el mismo modelo de costo). Esquina tipica (tt, 25 C, 5,0 V), reloj de 25 MHz.")
    w("")
    cab = ["core", "dado_um2", "celdas_std_um2", "celdas", "flip_flops", "fmax_cierre_mhz", "p_sondeo_mw",
           "p_calculo_mw", "p_ronda3_mw", "ciclos_kernel", "mops_25", "mops_fmax", "ppeak_25", "mops_por_w",
           "ppeak_por_w", "e_decision_r3_uj", "e_decision_r2_uj", "e_decision_r1_uj", "marginal_nj",
           "marginal_por_op_nj"]
    for core, etq, mk in (("base", "r0", "Base"), ("seg", "seg", "Seg")):
        pot, en = potencias(f"{A}/potencia_{core}_t40.md")
        tt, e = pot["típica"], en["típica"]
        c40 = corr[f"{core}_t40"]
        cierran = [corr[k]["T"] for k in corr if k.startswith(core + "_") and f"{k}: Resultado: CIERRA" in cierre]
        tmin = min(cierran)
        fmax = 1000.0 / tmin
        kc = R[etq]["k_c"]
        mops = OPS_TRADE * F_CLK / kc
        mops_f = OPS_TRADE * fmax / kc
        pp = VAR[etq]["ppeak"]
        opw = mops / (tt["calc"] / 1000.0)
        ppw = pp / (tt["calc"] / 1000.0)
        w(f"== Espino {'base' if core == 'base' else 'segmentado'} (corrida {core}_t40)")
        w(f"   dado {c40['dado']} um2 ({c40['dado'] / 1e6:.3f} mm2), celdas estandar {c40['std']} um2, {c40['celdas']} celdas,"
          f" {c40['ff']} flip-flops")
        w(f"   frecuencia: cierra en la esquina lenta hasta T = {tmin} ns ({fmax:.1f} MHz); el periodo siguiente del barrido no cierra")
        w(f"   potencia, esquina tipica: sondeo {tt['sondeo']:.3f} mW, calculo {tt['calc']:.3f} mW, ronda 3 {tt['ronda3']:.3f} mW"
          f" (solo reloj {tt['reloj']:.3f} mW)")
        w(f"   kernel: {kc:.2f} ciclos, {OPS_TRADE} ops: {mops:.3f} MOPS a 25 MHz, {mops_f:.3f} MOPS a {fmax:.1f} MHz;"
          f" Ppeak {pp} MOPS")
        w(f"   Ops/W: kernel {opw:.1f} MOPS/W, Ppeak {ppw:.1f} MOPS/W (la clase supuso 10 mW: {pp / 0.010:.0f} MOPS/W de Ppeak)")
        w(f"   energia por decision: ronda 3 {e['e3'] / 1000:.3f} uJ (flujo), ronda 2 {e['e2'] / 1000:.2f} uJ y ronda 1"
          f" {e['e1'] / 1000:.1f} uJ (estimadas: mas sondeo)")
        w(f"   costo marginal de decidir sobre el de esperar: {e['marg']:.2f} nJ, {e['marg'] / OPS_TRADE:.3f} nJ por operacion util")
        w("")
        filas.append([core, c40["dado"], c40["std"], c40["celdas"], c40["ff"], f2(fmax, 1), tt["sondeo"], f2(tt["calc"], 3),
                      tt["ronda3"], f2(kc), f2(mops, 3), f2(mops_f, 3), pp, f2(opw, 1), f2(ppw, 1), f2(e["e3"] / 1000, 3),
                      f2(e["e2"] / 1000, 2), f2(e["e1"] / 1000, 1), f2(e["marg"], 3), f2(e["marg"] / OPS_TRADE, 3)])
        macro(f"pSieteAsicDado{mk}", c40["dado"] / 1e6, 3)
        macro(f"pSieteAsicStd{mk}", c40["std"])
        macro(f"pSieteAsicFmax{mk}", fmax, 1)
        macro(f"pSieteAsicPsondeo{mk}", tt["sondeo"], 1)
        macro(f"pSieteAsicPcalculo{mk}", tt["calc"], 1)
        macro(f"pSieteAsicMops{mk}", mops, 2)
        macro(f"pSieteAsicMopsFmax{mk}", mops_f, 2)
        macro(f"pSieteAsicMopsW{mk}", opw, 0)
        macro(f"pSieteAsicPpeakW{mk}", ppw, 0)
        macro(f"pSieteAsicErtres{mk}", e["e3"] / 1000, 2)
        macro(f"pSieteAsicErdos{mk}", e["e2"] / 1000, 1)
        macro(f"pSieteAsicEruno{mk}", e["e1"] / 1000, 0)
        macro(f"pSieteAsicMarginal{mk}", e["marg"], 2)
        macro(f"pSieteAsicMarginalOp{mk}", e["marg"] / OPS_TRADE, 3)
    barrel_asic(R, w, filas)
    w("Lectura: la energia por decision la pone la espera, no el calculo. Decidir cuesta unos nJ sobre los")
    w("2,6 a 2,8 uJ que se gastan esperando 0,1 ms con el reloj corriendo. Detener el reloj entre precios es")
    w("la mejora de energia mas grande disponible; ningun peldaño de la escalera la cambia.")
    escribir_csv(f"{M}/asic.csv", cab, filas)
    open(f"{M}/asic.txt", "w", encoding="utf-8").write("\n".join(txt) + "\n")


# ---------------------------------------------------------------------------- negativos
def tabla_negativos(R, gem):
    pll = open(f"{M}/pll.txt", encoding="utf-8").read()
    marg = open(f"{M}/doble_frecuencia/margen.txt", encoding="utf-8").read()
    soc = open(f"{M}/doble_frecuencia/soc_x2.txt", encoding="utf-8").read()
    rep = open(f"{M}/doble_frecuencia/reproduccion.txt", encoding="utf-8").read()
    txt = []
    w = txt.append
    w("Resultados negativos: PLL y doble frecuencia, con el presupuesto que habria dado cada uno")
    w("Generado por tools/p7/tablas.py (make p7-rapido). No editar a mano.")
    w("")
    w("1. PLL (tools/p7/pll.sh, make p7-pll; log en pll_vq100_r1.log)")
    for linea in pll.splitlines():
        if linea.startswith(("  R0", "  R1", "    ERROR", "  r0:", "  r1:")):
            w("  " + linea.strip())
    m = re.search(r"r1: cierran a 50 MHz (\d+) de (\d+) semillas, fmax minima ([\d.]+)", pll)
    macro("pSietePllCierranRuno", int(m.group(1)))
    macro("pSietePllFminRuno", float(m.group(3)))
    m0 = re.search(r"r0: cierran a 50 MHz (\d+) de (\d+) semillas, fmax minima ([\d.]+)", pll)
    macro("pSietePllCierranRcero", int(m0.group(1)))
    w("")
    w("2. Duplicador de reloj por logica (tools/p7/doble_frecuencia.sh, make p7-doble)")
    for linea in rep.splitlines():
        if linea.startswith(("IGUAL", "DISTINTO")):
            w("  " + linea)
    for linea in marg.splitlines():
        if re.match(r"\s+(base_x2|seg_x2)\s+(máxima|típica)", linea) or "45 a 55 %" in linea[:30]:
            w("  " + linea.strip())
    # Semillas que cierran con un oscilador de 45 a 55 % en la esquina máxima (primera columna)
    m = re.search(r"seg_x2\s+máxima\s+\|\s+(\d+) de (\d+)", marg)
    macro("pSieteDobleSemillas", int(m.group(1)))
    macro("pSieteDobleSemillasTotal", int(m.group(2)))
    m = re.search(r"base_x2\s+máxima\s+\|\s+(\d+) de (\d+)", marg)
    macro("pSieteDobleSemillasBase", int(m.group(1)))
    w("")
    w("3. Presupuesto que habria dado cada uno (los dos duplican la frecuencia: 50 MHz, ciclo de 20 ns)")
    w(f"  {'ronda':<8}{'presupuesto a 25 MHz':>22}{'a 50 MHz':>10}")
    for k in ("r1", "r2", "r3"):
        w(f"  {k:<8}{PRESUPUESTO[k]:>22}{(PERIODOS[k] - SPI_NS) // 20:>10}")
    w("")
    w(f"  {'variante':<24}{'peor caso':>10}{'uso r3 a 25 MHz':>17}{'uso r3 a 50 MHz':>17}{'cierra a 50 MHz':>32}")
    rec, _ = leer_recursos()
    for etq in ORDEN:
        pc = gem["r1" if etq == "r2" else etq]["r3"]["peor_oficial"]
        r = rec[etq]
        cz = f"{'si' if r['fmin'] >= 50 else ('nunca' if r['fmax'] < 50 else 'no siempre')} (fmax {r['fmin']:.1f} a {r['fmax']:.1f})"
        w(f"  {VAR[etq]['corto']:<24}{pc:>10}{100.0 * pc / PRESUPUESTO['r3']:>16.2f}%{100.0 * pc / ((PERIODOS['r3'] - SPI_NS) // 20):>16.2f}%{cz:>32}")
    w("")
    w("  Con el reloj al doble el programa haria el mismo trabajo en la mitad del tiempo, pero todas las variantes")
    w("  ya usan menos del 20 % del presupuesto mas corto: el patrimonio no cambia. El PLL no existe en el VQ100")
    w("  y el duplicador por logica no tiene margen real (1 de 10 semillas con un ciclo de trabajo de 45 a 55 %).")
    open(f"{M}/negativos.txt", "w", encoding="utf-8").write("\n".join(txt) + "\n")


# ---------------------------------------------------------------------------- principal
def main():
    subprocess.run(["bash", "-c", "source tools/p7/comun.sh && programas"], check=True)
    rec, commit_rec = leer_recursos()
    gem, commit_gem = leer_gemelo()
    R = {etq: resumen(etq, gem) for etq in ORDEN}
    tabla_variantes(rec, gem, R)
    tabla_perfil(R)
    tabla_amdahl(R)
    pasos = tabla_escalera(R, rec)
    roofline(R, pasos)
    tabla_asic(R)
    tabla_negativos(R, gem)
    macro("pSieteOpsTrade", OPS_TRADE)
    macro("pSieteOpsFondo", OPS_FONDO)
    macro("pSieteBs", BS, 0)
    macro("pSieteQuiebre", 12.5 / BS, 3)
    for k, mk in (("r1", "Runo"), ("r2", "Rdos"), ("r3", "Rtres")):
        macro(f"pSietePresupuesto{mk}", PRESUPUESTO[k])
        macro(f"pSietePresupuestoDoble{mk}", (PERIODOS[k] - SPI_NS) // 20)
    nombres = [n for n, _ in MACROS]
    assert len(nombres) == len(set(nombres)), "macro repetida"
    with open(f"{M}/cifras.tex", "w", encoding="utf-8") as fh:
        fh.write("% cifras.tex: cifras del co-diseño (P7) para el informe.\n")
        fh.write("% Generado por tools/p7/tablas.py (make p7-rapido). No editar a mano.\n")
        fh.write(f"% Recursos del commit {commit_rec}, ciclos del commit {commit_gem}. Decimales con coma.\n")
        for n, v in MACROS:
            fh.write(f"\\newcommand{{\\{n}}}{{{v}}}\n")
    for f in ("variantes", "perfil", "amdahl", "escalera", "asic", "negativos"):
        print(open(f"{M}/{f}.txt", encoding="utf-8").read())
    print(f"{len(MACROS)} macros en {M}/cifras.tex")


if __name__ == "__main__":
    main()
