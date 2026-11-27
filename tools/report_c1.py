"""report_c1.py: cifras, tablas y figura de R3 (C1 en los cuatro hilos) para tools/report.py.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Se usa cuando el informe describe R3 (make informe PELDANO_INFORME=r3). Cada cifra sale de su
archivo de medición en docs/mediciones/c1/ o se recalcula con la referencia ref/c1/c1.py, y se
comprueba contra lo que ya estaba escrito: si algo no calza, el script termina con FAIL y no
deja el informe a medias.

Lo único que este módulo mide por su cuenta es el desempeño logrado, el roofline y el Amdahl de
R3, que no estaban medidos. Lo hace sobre el perfil por dirección ya guardado
(docs/mediciones/c1/perfil/gemelo.txt, make p7-c1-perfil) y deja el resultado en
docs/mediciones/c1/ops_roofline.txt. Definiciones (clase 7):

  - Operación útil de R3: cada instrucción aritmética, lógica o de comparación (add, sub, and,
    or, xor, slt y sus variantes con inmediato) que ejecutan los cuatro hilos. No cuentan los
    loads, los stores, los saltos, cargar una constante (li, la), copiar un registro (mv), las
    vueltas de los lazos de espera del precio, la telemetría, ni las vueltas repetidas de los
    lazos en que un hilo espera el dato de otro (cuenta una pasada por tick). La rutina
    `producto` se usa para D y para la telemetría: se reparte en proporción a las llamadas.
  - Kernel: del hilo 0, de leer PRICE a volver al sondeo, igual que en R0, R1 y R2.
  - Desempeño logrado = operaciones útiles x 25 MHz / ciclos del kernel.
  - Roofline: I = operaciones útiles / bytes que mueven los loads y stores de los cuatro hilos
    fuera de los lazos de espera del precio. Ppeak = 25 MOPS (cuatro hilos, una instrucción por
    ciclo en total).
  - Amdahl: f = ciclos por tick de la rutina más cara del hilo que cierra la respuesta, sobre
    la respuesta promedio; S = 1 / ((1 - f) + f / F).

Salidas en informe/generado/: cifras_c1.tex, t31r3.tex, texamen.tex, t32r3.tex, t32r3hilos.tex,
t33r3.tex y roofline_r3.tex.
"""
import csv
import math
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(RAIZ, "informe", "generado")
M = "docs/mediciones"
C = "docs/mediciones/c1"
SERIE = "data/practica_meta.csv"
F_CLK, BS = 25.0, 100.0
PRESUPUESTO = {1: 249762, 2: 24762, 3: 2262}
PERIODO_NS = {1: 10_000_000, 2: 1_000_000, 3: 100_000}

# Lazos de espera del precio (etiqueta: instrucciones) y lazos en que un hilo espera a otro
ESPERA = {"h0_espera": 3, "h1_espera": 2, "h2_espera": 2, "h3_espera": 2}
SINC = {"h0_sondeo": 6, "h2_reg": 4, "h2_fase": 4, "h3_fase": 4, "h3_tab": 4}


def exigir(ok, texto):
    if not ok:
        raise SystemExit(f"FAIL report (R3): {texto}")


def leer(ruta):
    with open(os.path.join(RAIZ, ruta), encoding="utf-8") as f:
        return f.read()


def buscar(patron, texto, tipo=float, grupo=1):
    m = re.search(patron, texto, re.M)
    exigir(m is not None, f"no se encontro /{patron}/")
    return tipo(m.group(grupo))


def tex(s):
    """Texto de un registro (coma decimal, signo ASCII) a LaTeX."""
    return s.strip().replace(",", "{,}").replace("-", "$-$").replace("+", "$+$")


def ancha(tabla, ruta, cabecera, filas, alineacion, nota):
    """Tabla que el informe reescala al ancho de la página (\\tablaancha). La nota va en un archivo
    aparte, <tabla>_nota.tex: dentro del cuadro reescalado quedaría en una sola línea y achicaría la tabla."""
    tabla(ruta, cabecera, filas, alineacion)
    with open(ruta.replace(".tex", "_nota.tex"), "w", encoding="utf-8") as f:
        f.write("% Generado por tools/report_c1.py. No editar a mano.\n")
        f.write(f"{{\\footnotesize {nota}\\par}}\n")


class Macros:
    """Macros \\ctres... con su archivo de origen comentado al lado."""

    def __init__(self):
        self.d = {}

    def poner(self, nombre, valor, origen):
        exigir(re.fullmatch(r"[A-Za-z]+", nombre) is not None, f"nombre de macro invalido: {nombre}")
        exigir(nombre not in self.d, f"macro repetida: {nombre}")
        self.d[nombre] = (valor, origen)

    def escribir(self, ruta):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("% Generado por tools/report_c1.py (make informe PELDANO_INFORME=r3). No editar a mano.\n")
            for k, (v, origen) in sorted(self.d.items()):
                f.write(f"\\newcommand{{\\ctres{k}}}{{{v}}}% {origen}\n")


# --- Punto 3.1: la serie de práctica, el examen y la maestra real -------------------------------
def punto_31(mc, tabla, num):
    sys.path[:0] = [os.path.join(RAIZ, "ref", "c1")]
    import c1 as C1m           # noqa: E402
    import tablas as TB        # noqa: E402
    import market              # noqa: E402
    import trader              # noqa: E402
    from regla_cotas import Cotas   # noqa: E402
    import report              # noqa: E402  (comprar_y_mantener, la misma de R0 a R2)

    precios = market.leer_serie(os.path.join(RAIZ, SERIE))
    T = TB.leer_hex(os.path.join(RAIZ, "sw", "c1_tabla.hex"))
    mc1 = market.simular(precios, trader.decisiones(precios, C1m.C1(T), 0))
    mb = market.simular(precios, trader.decisiones(precios, Cotas("espera", banda=40), 0))
    mcym = report.comprar_y_mantener(precios)
    # Con la política apagada, la referencia de C1 decide la banda 40 byte por byte
    apagada = list(T)
    apagada[TB.T_POLITICA] = TB.POLITICA_APAGADA
    exigir(trader.decisiones(precios, C1m.C1(apagada), 0) == trader.decisiones(precios, Cotas("espera", banda=40), 0),
           "con la politica apagada ref/c1/c1.py no decide la banda 40 en la serie de practica")

    sr = leer(f"{C}/series_reales.txt")
    reales = {}
    for nombre in ("Meta", "Tesla", "AMD"):
        bloque = sr.split(f"\n{nombre} (")[1].split("\n\n")[0]
        reales[nombre] = dict(
            c1=buscar(r"C1: patrimonio (\d+)", bloque, int), c1o=buscar(r"C1: patrimonio \d+, (\d+) órdenes", bloque, int),
            b=buscar(r"Banda 40: patrimonio (\d+)", bloque, int), bo=buscar(r"Banda 40: patrimonio \d+, (\d+) órdenes", bloque, int))
    exigir((mc1.w, mc1.ordenes) == (reales["Meta"]["c1"], reales["Meta"]["c1o"]),
           f"C1 en la practica: {mc1.w} con {mc1.ordenes} ordenes, y series_reales.txt dice otra cosa")
    exigir((mb.w, mb.ordenes) == (reales["Meta"]["b"], reales["Meta"]["bo"]), "la banda 40 en la practica no calza con series_reales.txt")

    filas = [["No operar", num(market.CAJA0), 0, 0, 0],
             ["Comprar al inicio y mantener", num(mcym.w), mcym.ordenes, num(mcym.comisiones), num(mcym.max_dd)],
             ["Banda 40 (base y respaldo)", num(mb.w), mb.ordenes, num(mb.comisiones), num(mb.max_dd)],
             ["C1 (el algoritmo que compite)", num(mc1.w), mc1.ordenes, num(mc1.comisiones), num(mc1.max_dd)]]
    tabla(os.path.join(G, "t31r3.tex"), ["Estrategia", "Patrimonio", "Órdenes", "Comisiones", "Pérdida máx."], filas, "lrrrr",
          "Serie de práctica completa (\\texttt{data/practica\\_meta.csv}, 20\\,000 ticks), con \\texttt{ref/c1/c1.py} y la "
          "contabilidad de \\texttt{ref/market.py}. Pérdida máxima: mayor caída del patrimonio desde un máximo anterior.")
    o = "ref/c1/c1.py sobre data/practica_meta.csv; docs/mediciones/c1/series_reales.txt"
    mc.poner("PracticaW", num(mc1.w), o)
    mc.poner("PracticaOrdenes", mc1.ordenes, o)
    mc.poner("PracticaPerdida", num(mc1.max_dd), o)
    mc.poner("PracticaBandaW", num(mb.w), o)
    mc.poner("PracticaBandaOrdenes", mb.ordenes, o)
    mc.poner("PracticaBandaPerdida", num(mb.max_dd), o)
    mc.poner("PracticaCymW", num(mcym.w), o)
    mc.poner("PracticaCymPerdida", num(mcym.max_dd), o)
    # La apuesta de la fase A en la práctica: primera orden de C1
    m = re.search(r"tick (\d+), precio (\d+), compra (\d+) \(byte 56\), decidida en fase A", sr.split("\nMeta (")[1])
    exigir(m is not None, "series_reales.txt no trae la compra de la fase A de la serie Meta")
    o = "docs/mediciones/c1/series_reales.txt"
    mc.poner("ApuestaTick", num(int(m.group(1))), o)
    mc.poner("ApuestaPrecio", m.group(2), o)
    mc.poner("ApuestaAcciones", m.group(3), o)
    for nombre in ("Tesla", "AMD"):
        r = reales[nombre]
        mc.poner(f"{nombre.capitalize()}W", num(r["c1"]), o)
        mc.poner(f"{nombre.capitalize()}Ordenes", r["c1o"], o)
        mc.poner(f"{nombre.capitalize()}BandaW", num(r["b"]), o)
        mc.poner(f"{nombre.capitalize()}BandaOrdenes", r["bo"], o)

    # La maestra real del 25/11 (docs/puertas.md): tiene que ser lo mismo que la simulación
    pu = leer("docs/puertas.md").split("## Puerta de maestra: el 25/11")[1]
    for nombre in ("Meta", "Tesla"):
        m = re.search(rf"^\| {nombre}[^|]*\| ([\d ]+) con (\d+) órdenes \|", pu, re.M)
        exigir(m is not None, f"docs/puertas.md no trae la ronda de {nombre} del 25/11")
        placa = (int(m.group(1).replace(" ", "")), int(m.group(2)))
        exigir(placa == (reales[nombre]["c1"], reales[nombre]["c1o"]),
               f"maestra real en {nombre}: {placa} no es lo que da la simulacion {reales[nombre]}")

    # El examen (cinco empresas) y las 100 acciones ajenas
    ex = leer(f"{C}/c1_examen.txt")
    o = "docs/mediciones/c1/c1_examen.txt (copia del registro de la rama minutos-reales, commit 17d7284)"
    m = re.search(r"Banda 40 sola: nd ([\d,]+) \(([\d,]+)\), g ([\d,]+) \(([\d,]+)\)\. C1: nd ([\d,]+) \(([\d,]+)\), g ([\d,]+) \(([\d,]+)\)\.", ex)
    exigir(m is not None, "c1_examen.txt: no esta la linea de las cifras ponderadas")
    b_nd, _, b_g, _, c_nd, _, c_g, _ = m.groups()
    d_g = buscar(r"^1\. g de C1.*Diferencia pareada ([+\-][\d,]+ \([\d,]+\))", ex, str)
    d_nd = buscar(r"^2\. nd de C1.*Diferencia pareada ([+\-][\d,]+ \([\d,]+\))", ex, str)
    d_w = buscar(r"^\| C1 \| b40 \| 0,10 \| ([+\-]\d+ \(\d+\)) \|", ex, str)
    s = re.search(r"^\| caso S \| (\d+) \|[^|]*\|[^|]*\|[^|]*\|[^|]*\| ([^|]*) \| ([^|]*) \|", ex, re.M)
    b = re.search(r"^\| caso B \| (\d+) \|[^|]*\|[^|]*\|[^|]*\|[^|]*\| ([^|]*) \| ([^|]*) \|", ex, re.M)
    exigir(s is not None and b is not None, "c1_examen.txt: faltan las filas por caso")
    ronda = {k: re.search(rf"^\| {k} \| \d+ \| [\d,]+ \| \d+ \| \d+ \| ([+\-]\d+ \(\d+\)) \|", ex, re.M).group(1)
             for k in ("caso S", "caso B")}
    mec = re.search(r"^\| S \| 2101 \| [^|]* \| ([\d,]+) \(([+\-]\d+)\) \| ([\d,]+) \(([+\-]\d+)\) \|", ex, re.M)
    exigir(mec is not None, "c1_examen.txt: falta la mecanica del caso S")
    ventanas = buscar(r"^\| todas las ventanas \| (\d+) \|", ex, int)
    clon_nd = buscar(r"^\| C1 \| b40 \| 0,10 \| [^|]* \| ([\d,]+) \(", ex, str)

    fi = leer(f"{C}/v5_finalistas.txt")
    of = "docs/mediciones/c1/v5_finalistas.txt (copia del registro de la rama minutos-reales, commit 17d7284)"
    fb = re.search(r"^\| banda 40 \| ([\d,]+) \([\d,]+\) \| ([\d,]+) \([\d,]+\) \|", fi, re.M)
    fc = re.search(r"^\| C1: pA 0,95[^|]*\| ([\d,]+) \([\d,]+\) \| ([\d,]+) \([\d,]+\) \| ([^|]*) \| ([^|]*) \|", fi, re.M)
    f30 = re.search(r"^\| banda 30 sola \| ([\d,]+) \([\d,]+\) \| [^|]* \| ([^|]*) \|", fi, re.M)
    exigir(fb and fc and f30, "v5_finalistas.txt: faltan filas")
    ajenas = buscar(r"Otras acciones: (\d+) ventanas", fi, int)
    indice = fi.split("## Índice, todas las ventanas")[1].split("\n\n")[1]
    sobre = [f.strip() for f in re.findall(r"^\| ([^|]+)\| [^|]+\| [^|]+\| \+(?!0,0)[\d,]+ \(", indice, re.M)]
    exigir(sobre == ["banda 30 sola"], f"v5_finalistas.txt: superan a la banda 40 en nd {sobre}, y el informe dice que solo la banda 30")

    filas = [[f"Examen, {num(ventanas)} ventanas", "Banda 40", tex(b_g), tex(b_nd)],
             ["", "C1", tex(c_g), tex(c_nd)],
             ["", "Diferencia", tex(d_g), tex(d_nd)],
             [f"\\quad caso S ({num(int(s.group(1)))} ventanas)", "Diferencia", tex(s.group(3)), tex(s.group(2))],
             [f"\\quad caso B ({num(int(b.group(1)))} ventanas)", "Diferencia", tex(b.group(3)), tex(b.group(2))],
             "---",
             [f"Ajuste, {num(ajenas)} ventanas", "Banda 40", tex(fb.group(2)), tex(fb.group(1))],
             ["", "C1", tex(fc.group(2)), tex(fc.group(1))],
             ["", "Diferencia", tex(fc.group(4)), tex(fc.group(3))]]
    tabla(os.path.join(G, "texamen.tex"), ["Conjunto", "", "Gana sola (\\%)", "No queda debajo (\\%)"], filas, "llrr",
          "Examen: cinco empresas; ajuste: 100 acciones ajenas. Torneos de 3 rondas contra un rival sorteado; diferencias "
          "pareadas, con su error estándar entre paréntesis. Caso S: el 100 llega antes que el 255; caso B: al revés. "
          "Fuente: \\texttt{docs/mediciones/c1/c1\\_examen.txt} y \\texttt{v5\\_finalistas.txt}.")
    mc.poner("ExamenVentanas", num(ventanas), o)
    mc.poner("ExamenGanaBanda", tex(b_g), o)
    mc.poner("ExamenGana", tex(c_g), o)
    mc.poner("ExamenNdBanda", tex(b_nd), o)
    mc.poner("ExamenNd", tex(c_nd), o)
    mc.poner("ExamenDifGana", tex(d_g), o)
    mc.poner("ExamenDifNd", tex(d_nd), o)
    mc.poner("ExamenDifRonda", tex(d_w), o)
    mc.poner("ExamenDifNdCasoS", tex(s.group(2)), o)
    mc.poner("ExamenDifNdCasoB", tex(b.group(2)), o)
    mc.poner("ExamenRondaCasoS", tex(ronda["caso S"]), o)
    mc.poner("ExamenRondaCasoB", tex(ronda["caso B"]), o)
    mc.poner("ExamenCandadoCasoS", tex(mec.group(1)), o)
    mc.poner("ExamenSinRecuperarCasoS", tex(mec.group(3)), o)
    mc.poner("ExamenSinRecuperarD", tex(mec.group(4).lstrip("-")), o)
    mc.poner("ExamenDebajoClon", num(100 - float(clon_nd.replace(",", ".")), 1), o)
    mc.poner("AjenasVentanas", num(ajenas), of)
    mc.poner("AjenasGana", tex(fc.group(2)), of)
    mc.poner("AjenasNd", tex(fc.group(1)), of)
    mc.poner("AjenasNdBanda", tex(fb.group(1)), of)
    mc.poner("AjenasGanaBanda", tex(fb.group(2)), of)
    mc.poner("AjenasDifNdBandaTreinta", tex(f30.group(2)), of)
    mc.poner("AjenasNdBandaTreinta", tex(f30.group(1)), of)


# --- Verificación y hardware: de los registros de las puertas ------------------------------------
def verificacion(mc, num):
    t = leer(f"{C}/contabilidad.txt")
    filas = re.findall(r"^.*?: (\d+) series; (\d+) con apuesta de la fase A, (\d+) órdenes parciales, \d+ órdenes de la maestra; "
                       r"ticks con diferencia entre la cuenta emulada y la maestra: (\d+)", t, re.M)
    exigir(len(filas) == 5 and "PASS: 0 comprobaciones falladas" in t, "contabilidad.txt no tiene las cinco familias en PASS")
    o = "docs/mediciones/c1/contabilidad.txt"
    mc.poner("ContSeries", num(sum(int(f[0]) for f in filas)), o)
    mc.poner("ContParciales", num(sum(int(f[2]) for f in filas)), o)
    mc.poner("ContDiferencias", sum(int(f[3]) for f in filas), o)

    t = leer(f"{C}/contabilidad_rtl.txt")
    m = re.search(r"^PASS: (\d+) de (\d+) corridas", t, re.M)
    exigir(m is not None and m.group(1) == m.group(2), "contabilidad_rtl.txt no termina en PASS")
    mc.poner("ContRtl", f"{m.group(1)} de {m.group(2)}", "docs/mediciones/c1/contabilidad_rtl.txt")

    t = leer(f"{C}/puerta_b.txt")
    o = "docs/mediciones/c1/puerta_b.txt"
    exigir("PASS: 0 corridas con diferencias" in t, "puerta_b.txt no termina en PASS")
    m = re.search(r"^PASS: (\d+) de \d+ ventanas identicas.*?(\d+) ticks, (\d+) ordenes, (\d+) terminan en candado, peor caso (\d+)", t, re.M)
    completas = len(re.findall(r"^PASS (?:tesla|amd|meta)_\d+: 20000 bytes", t, re.M))
    mc.poner("PuertaBVentanas", m.group(1), o)
    mc.poner("PuertaBTicks", num((int(m.group(2)) + completas * 20000) / 1e6, 2), o)
    mc.poner("PeorPuertas", m.group(5), o)
    for nombre in ("tesla", "amd", "meta"):
        exigir(re.search(rf"^PASS {nombre}_100000:.*peor caso 783 de", t, re.M) is not None,
               f"puerta_b.txt: el peor caso de {nombre} a 0,1 ms no es 783")
    m = re.search(r"^PASS periodo 100000 ns.*?(\d+) de \d+ series identicas", t, re.M)
    mc.poner("GemeloReales", m.group(1), o)

    t = leer(f"{C}/puerta_a.txt")
    m = re.search(r"^PASS: (\d+) de \d+ corridas .*?(\d+) ticks: R3 con la politica apagada escribe los mismos bytes que R2\. "
                  r"Peor caso de R3 apagado: (\d+) ciclos", t, re.M)
    exigir(m is not None and "PASS: 0 corridas con diferencias" in t, "puerta_a.txt no termina en PASS")
    o = "docs/mediciones/c1/puerta_a.txt"
    mc.poner("ApagadaCorridas", m.group(1), o)
    mc.poner("ApagadaTicks", num(int(m.group(2))), o)

    t = leer(f"{C}/series.txt")
    m = re.search(r"^PASS periodo 100000 ns.*?(\d+) de (\d+) series identicas.*peor caso (\d+)", t, re.M)
    exigir(m is not None and m.group(1) == m.group(2), "series.txt: el lote sintetico no pasa")
    mc.poner("SinteticasGemelo", num(int(m.group(1))), "docs/mediciones/c1/series.txt")
    n = re.search(r"^PASS: (\d+) de (\d+) series identicas a la referencia \(bytes, estado y protocolo\)", t, re.M)
    exigir(n is not None and n.group(1) == n.group(2), "series.txt: las series por el RTL no pasan")
    mc.poner("SinteticasRtl", num(int(n.group(1))), "docs/mediciones/c1/series.txt")
    exigir(m.group(3) == mc.d["PeorPuertas"][0], "el peor caso de las series sinteticas no es el de la puerta b")

    t = leer(f"{C}/degradacion.txt")
    m = re.search(r"^PASS: (\d+) de (\d+) casos con la decision esperada y a tiempo\. Peor caso (\d+) ciclos", t, re.M)
    exigir(m is not None and m.group(1) == m.group(2), "degradacion.txt no termina en PASS")
    mc.poner("Degradacion", f"{m.group(1)} de {m.group(2)}", "docs/mediciones/c1/degradacion.txt")

    t = leer(f"{C}/fases.txt")
    o = "docs/mediciones/c1/fases.txt"
    mc.poner("PeorFases", buscar(r"^Peor caso con el programa sano: (\d+) ciclos", t, int), o)
    mc.poner("PeorColgado", buscar(r"^Peor caso con el hilo 3 colgado: (\d+) ciclos", t, int), o)

    t = leer(f"{M}/ci_local_c1.txt")
    m = re.search(r"^RESULTADO: (\d+) de (\d+) pasos en PASS", t, re.M)
    exigir(m is not None and m.group(1) == m.group(2), "ci_local_c1.txt no tiene todos los pasos en PASS")
    mc.poner("IntegracionLocal", f"{m.group(1)} de {m.group(2)}", "docs/mediciones/ci_local_c1.txt")

    t = leer(f"{C}/oficial.txt")
    m = re.search(r"Peor caso precio->decision: (\d+) ciclos \(disponibles: 2262\)\n\s*Testbenchs aprobados: 4/4", t)
    exigir(m is not None, "oficial.txt: el testbench oficial no da 4/4")
    mc.poner("OficialPeor", m.group(1), "docs/mediciones/c1/oficial.txt")

    t = leer(f"{C}/timing.txt")
    m = re.search(r"celdas (\d+) de 1280, BRAM (\d+) de 16, LUT4\s+(\d+), fmax min\s+([\d.]+) mediana\s+([\d.]+) max\s+([\d.]+) MHz, "
                  r"cierran a 25 MHz (\d+) de (\d+)", t)
    exigir(m is not None and m.group(7) == m.group(8), "timing.txt: R3 no cierra en todas las semillas")
    o = "docs/mediciones/c1/timing.txt"
    hw = dict(celdas=int(m.group(1)), bram=int(m.group(2)), lut4=int(m.group(3)), fmin=float(m.group(4)))
    mc.poner("Celdas", num(hw["celdas"]), o)
    mc.poner("Bram", hw["bram"], o)
    mc.poner("Fmin", num(hw["fmin"], 2), o)
    mc.poner("Semillas", f"{m.group(7)} de {m.group(8)}", o)
    r2 = re.search(r"celdas (\d+) de 1280", leer(f"{M}/fondo/r2/timing.txt"))
    mc.poner("CeldasRdosMismaSintesis", num(int(r2.group(1))), "docs/mediciones/fondo/r2/timing.txt")
    mc.poner("CeldasSobreRdos", hw["celdas"] - int(r2.group(1)), "docs/mediciones/c1/timing.txt y fondo/r2/timing.txt")

    t = leer(f"{C}/tamano.txt")
    m = re.search(r"Codigo: (\d+) palabras\. Datos: (\d+) palabras\. Total (\d+) de 512", t)
    exigir(m is not None, "tamano.txt: falta el total")
    o = "docs/mediciones/c1/tamano.txt"
    mc.poner("Palabras", m.group(3), o)
    mc.poner("PalabrasCodigo", m.group(1), o)
    sys.path[:0] = [os.path.join(RAIZ, "ref", "c1")]
    import tablas as TB        # noqa: E402
    mc.poner("TablaUsadas", TB.USADAS, "ref/c1/tablas.py (USADAS)")
    mc.poner("TablaCeldas", TB.CLASES * TB.TRAMOS_A + len(TB.FASES_M) * TB.CLASES * TB.TRAMOS_M, "ref/c1/tablas.py")

    t = leer(f"{M}/autoprueba_r3.txt")
    exigir(all(re.search(rf"^PASS RTL con SW{n} .*firma=984c esperada=984c", t, re.M) for n in (1, 2, 3)),
           "autoprueba_r3.txt: la firma no pasa a los tres ritmos")
    return hw


# --- Punto 3.2: mediciones por tick ------------------------------------------------------------------
def gemelo(periodo_ns):
    """Respuesta de R3 en la serie de práctica completa, con el gemelo digital."""
    os.makedirs(os.path.join(RAIZ, "build", "report"), exist_ok=True)
    subprocess.run([sys.executable, "tools/pochoasm.py", "sw/c1.s", "-o", "build/report/c1.hex"], cwd=RAIZ, check=True,
                   capture_output=True)
    r = subprocess.run(["build/gemelo", "--barrel", "--xd", "3", "--tabla", "sw/c1_tabla.hex", "--hex", "build/report/c1.hex",
                        "--serie", SERIE, "--periodo-ns", str(periodo_ns), "--nticks", "20000"], cwd=RAIZ, check=True,
                       capture_output=True, text=True).stdout
    exigir("aprobados: 4/4" in r, f"el gemelo no da 4/4 con R3 a {periodo_ns} ns")
    m = re.search(r"Respuesta: ([\d.]+) ciclos e IC ([\d.]+) en promedio, peor caso (\d+) ciclos e IC (\d+)", r)
    return dict(prom=float(m[1]), ic=float(m[2]), peor=int(m[3]), ic_peor=int(m[4]),
                w=int(re.search(r"Patrimonio final:\s+(\d+)", r).group(1)))


def punto_32(mc, tabla, num):
    t = leer(f"{C}/ticks.txt")
    r3 = t.split("=== Ronda 3")[1].split("=== Ronda 2")[0]
    o = "docs/mediciones/c1/ticks.txt (por el RTL)"
    hilos = {}
    for h, mi, pr, ma, cp, cm, cpi in re.findall(r"^\s+([0-3])\s+(\d+)\s+([\d.]+)\s+(\d+)\s+([\d.]+)\s+(\d+)\s+([\d.]+)$", r3, re.M):
        hilos[int(h)] = dict(mi=int(mi), pr=float(pr), ma=int(ma), cpi=float(cpi))
    exigir(len(hilos) == 4 and all(h["cpi"] == 4.0 for h in hilos.values()), "ticks.txt: faltan hilos o el CPI por hilo no es 4")
    hitos = {}
    for clave, patron in (("pub", r"D_PUB\)"), ("reg", r"D_REG\)"), ("tab", r"D_TAB\)"), ("pol", r"D_POL\)"),
                          ("dec", r"DECISION \(respuesta\)"), ("vuelve", r"vuelve a sondear")):
        m = re.search(patron + r"\s+(\d+)\s+([\d.]+)\s+(\d+)", r3)
        exigir(m is not None, f"ticks.txt: falta el hito {clave}")
        hitos[clave] = (int(m[1]), float(m[2]), int(m[3]))
    rol = {0: ("corredor", "\\texttt{D\\_PUB}", "pub"), 1: ("régimen", "\\texttt{D\\_REG}", "reg"),
           2: ("política", "\\texttt{D\\_TAB}", "tab"), 3: ("emulador", "\\texttt{D\\_POL}", "pol")}
    filas = []
    for h in range(4):
        nombre, palabra, k = rol[h]
        filas.append([f"{h}, {nombre}", hilos[h]["mi"], num(hilos[h]["pr"], 1), hilos[h]["ma"], palabra,
                      num(hitos[k][1], 1), hitos[k][2]])
    filas.append(["0, corredor", "", "", "", "\\texttt{DECISION}", num(hitos["dec"][1], 1), hitos["dec"][2]])
    tabla(os.path.join(G, "t32r3hilos.tex"),
          ["Hilo", "IC mín.", "IC prom.", "IC máx.", "Publica", "Ciclo prom.", "Ciclo máx."], filas, "lrrrlrr",
          "Ronda 3, serie de práctica, por el RTL. IC: instrucciones del hilo por tick fuera de su lazo de espera del precio "
          "(CPI 4 por hilo). Ciclo: ciclos desde \\texttt{byte\\_done} hasta que el hilo publica. "
          "Fuente: \\texttt{docs/mediciones/c1/ticks.txt}.")
    mc.poner("IcSumaProm", num(sum(h["pr"] for h in hilos.values()), 0), o)
    mc.poner("IcHiloTresMax", hilos[3]["ma"], o)
    mc.poner("HitoPub", hitos["pub"][2], o)
    mc.poner("HitoRegProm", num(hitos["reg"][1], 0), o)
    mc.poner("HitoTabProm", num(hitos["tab"][1], 0), o)
    mc.poner("HitoPolProm", num(hitos["pol"][1], 0), o)
    mc.poner("HitoDecProm", num(hitos["dec"][1], 0), o)

    # Las tres rondas con el gemelo (20 000 ticks), comprobadas contra el RTL donde se midió
    of = leer(f"{C}/oficial.txt")
    filas = []
    g = {}
    for ronda, nombre in ((1, "10 ms"), (2, "1 ms"), (3, "0,1 ms")):
        d = g[ronda] = gemelo(PERIODO_NS[ronda])
        peor_rtl = buscar(rf"data/practica_meta\.csv, periodo {PERIODO_NS[ronda]} ns, 20000 ticks, Peor caso precio->decision: (\d+)", of, int)
        exigir(d["peor"] == peor_rtl, f"ronda {ronda}: el gemelo da {d['peor']} ciclos de peor caso y el RTL {peor_rtl}")
        T = PERIODO_NS[ronda] / 40
        for caso, cic, ic in (("Promedio", d["prom"], num(d["ic"], 1)), ("Peor caso", d["peor"], d["ic_peor"])):
            filas.append([f"{ronda} ({nombre})" if caso == "Promedio" else "", caso, ic,
                          num(cic, 1) if caso == "Promedio" else num(cic), "4 / 1", num(cic * 0.04, 2),
                          num(100.0 * cic / T, 2), num(100.0 * cic / PRESUPUESTO[ronda], 2),
                          num(PRESUPUESTO[ronda]) if caso == "Promedio" else ""])
    exigir(abs(g[3]["prom"] - hitos["dec"][1]) < 0.05 and g[3]["peor"] == hitos["dec"][2],
           f"ronda 3: el gemelo ({g[3]['prom']}, {g[3]['peor']}) no calza con el RTL {hitos['dec']}")
    exigir(abs(g[3]["ic"] - hilos[0]["pr"]) < 0.05, "ronda 3: el IC del hilo 0 del gemelo no calza con el RTL")
    ancha(tabla, os.path.join(G, "t32r3.tex"),
          ["Ronda", "Caso", "IC del hilo 0", "Ciclos", "CPI hilo / total", "Tiempo ($\\mu$s)", "\\% de $T$", "\\% del presupuesto",
           "Presupuesto"], filas, "llrrrrrrr",
          "Respuesta: de \\texttt{byte\\_done} a la escritura en \\texttt{DECISION}, serie de práctica completa a cada período, "
          "con el gemelo digital. El RTL da los mismos ciclos donde se midió: promedio y peor caso de la ronda 3 "
          "(\\texttt{docs/mediciones/c1/ticks.txt}) y peor caso de las rondas 1 y 2 (\\texttt{oficial.txt}). "
          "Presupuesto: ciclos del período menos la transacción SPI.")
    og = "gemelo digital, serie de practica a 0,1 ms; igual al RTL de docs/mediciones/c1/ticks.txt"
    mc.poner("RespProm", num(g[3]["prom"], 1), og)
    mc.poner("RespPeor", g[3]["peor"], og)
    mc.poner("RespMin", hitos["dec"][0], o)
    mc.poner("RespPromUs", num(g[3]["prom"] * 0.04, 1), og)
    mc.poner("RespPeorUs", num(g[3]["peor"] * 0.04, 1), og)
    mc.poner("UsoPresupuesto", num(100.0 * g[3]["peor"] / PRESUPUESTO[3], 1), og)
    mc.poner("UsoPresupuestoProm", num(100.0 * g[3]["prom"] / PRESUPUESTO[3], 1), og)
    exigir(all(g[r]["w"] == g[3]["w"] for r in g), "el patrimonio del gemelo cambia con el periodo")
    return g[3]


# --- Punto 3.3: operaciones útiles, roofline y Amdahl de R3, desde el perfil guardado ------------
def clase(w):
    """Clase de una instrucción RV32E por su palabra: 'alu', 'const', 'load', 'store', 'salto' u 'otra'.
    Para loads y stores devuelve además los bytes que mueve."""
    op, f3, rs1, imm = w & 0x7F, (w >> 12) & 7, (w >> 15) & 31, w >> 20
    if op == 0x03:
        return "load", {0: 1, 1: 2, 2: 4, 4: 1, 5: 2}[f3]
    if op == 0x23:
        return "store", {0: 1, 1: 2, 2: 4}[f3]
    if op in (0x63, 0x6F, 0x67):
        return "salto", 0
    if op == 0x33:
        return "alu", 0
    if op == 0x13:
        if f3 == 0 and (rs1 == 0 or imm == 0):      # li, la y mv: cargar una constante o copiar
            return "const", 0
        return "alu", 0
    if op in (0x37, 0x17):
        return "const", 0
    return "otra", 0


def perfil_r3(mc, num, resp):
    sys.path.insert(0, os.path.join(RAIZ, "tools", "p7"))
    import fuentes             # noqa: E402
    mapa, sim = fuentes.mapa(os.path.join(RAIZ, "sw", "c1.s"))
    hexw = [int(x, 16) for x in open(os.path.join(RAIZ, "build", "report", "c1.hex")).read().split() if not x.startswith(("@", "/"))]
    texto = leer(f"{C}/perfil/gemelo.txt")
    nticks = buscar(r"^# ticks_medidos (\d+)", texto, int)
    filas = []
    for linea in texto.splitlines():
        if linea and not linea.startswith("#"):
            h, d, w, n, c = linea.split()
            h, d, w, n, c = int(h), int(d, 16), int(w, 16), int(n), int(c)
            exigir(hexw[d // 4] == w, f"el perfil guardado no es de este sw/c1.s (direccion {d:03x}): repetir make p7-c1-perfil")
            filas.append((h, d, w, n, c))
    # Que el perfil guardado es el de la medición por tick: misma respuesta promedio
    ph = leer(f"{C}/perfil_hilos.txt")
    exigir(abs(buscar(r"Respuesta: ([\d.]+) ciclos", ph) - resp["prom"]) < 0.005, "perfil_hilos.txt no es de este programa")

    def rango(etiqueta, n):
        ini = sim[etiqueta]
        fin = ini + 4 * (n - 1)
        _, nom, ops, _ = mapa[fin]
        exigir(nom.startswith("b") and ops[-1] == etiqueta, f"el lazo {etiqueta} no termina en un salto a su etiqueta")
        return range(ini, fin + 4, 4)

    espera = {d for e, n in ESPERA.items() for d in rango(e, n)}
    sinc = {d for e, n in SINC.items() for d in rango(e, n)}
    dirs = sorted(mapa)

    def donde(pred):
        r = [d for d in dirs if pred(mapa[d])]
        exigir(len(r) == 1, "no se encontro una instruccion unica del programa")
        return r[0]

    # Telemetría: en el hilo 0, la escritura de los LED; en el hilo 3, lo que va después de publicar D_QC
    d_qc = donde(lambda x: x[1] == "sw" and x[2][-1] == "d_qc(x0)")
    j_h3 = donde(lambda x: x[1] == "j" and x[2] == ["h3_espera"])
    tele = set(range(d_qc + 4, j_h3, 4))
    d_leds = donde(lambda x: x[1] == "sw" and "per_leds" in x[2][-1])
    tele |= {d_leds - 4, d_leds}
    exigir(mapa[d_leds - 4][1] == "li", "la telemetria del hilo 0 no es li y sw")
    prod = range(sim["producto"], max(d for d in dirs if mapa[d][1] == "jr") + 4, 4)
    ejec = range(sim["ejecutar"], sim["producto"], 4)
    llamadas = {d: n for h, d, w, n, c in filas if mapa[d][1] == "jal" and mapa[d][2][-1] == "producto"}
    exigir(len(llamadas) == 2, "se esperaban dos llamadas a producto")
    n_tel = sum(n for d, n in llamadas.items() if d in tele)
    n_d = sum(n for d, n in llamadas.items() if d not in tele)
    parte_d = n_d / (n_d + n_tel)
    # Kernel del hilo 0: de leer PRICE a volver al sondeo
    k_ini = sim["h0_espera"] + 4 * ESPERA["h0_espera"]
    k_fin = donde(lambda x: x[1] == "j" and x[2] == ["h0_espera"])
    exigir(mapa[k_ini][1] == "lw" and "off_price" in mapa[k_ini][2][-1], "el kernel del hilo 0 no parte en la lectura de PRICE")

    ops = [0.0] * 4
    trabajo = [0.0] * 4
    vueltas = [0.0] * 4
    octetos = [0.0] * 4
    k_ic = k_cic = c_ejec = ic_ejec = 0.0
    for h, d, w, n, c in filas:
        if d < sim["h0_espera"] and n == 1:
            continue                                  # arranque: una vez por ronda
        cl, nb = clase(w)
        exigir(cl != "otra", f"instruccion sin clase en {d:03x}")
        if h == 0 and k_ini <= d <= k_fin:
            k_ic += n
            k_cic += c
        if d in ejec:
            c_ejec += c
            ic_ejec += n
        if d in espera:
            continue
        octetos[h] += n * nb
        una = min(n, nticks) if d in sinc else n      # en los lazos entre hilos cuenta una pasada por tick
        vueltas[h] += n - una
        trabajo[h] += una
        if cl == "alu" and d not in tele:
            ops[h] += una * (parte_d if d in prod else 1.0)
    ops_t = sum(ops) / nticks
    oct_t = sum(octetos) / nticks
    k_cic /= nticks
    k_ic /= nticks
    c_ejec /= nticks
    ic_ejec /= nticks
    mops = ops_t * F_CLK / k_cic
    # El mismo conteo por clase aplicado a la banda 40 de R0 y de R2, para comparar con R3 en la misma escala
    # (la tabla de R0 a R2 usa las 11 operaciones contadas a mano, decisión del 21/11)
    with open(os.path.join(RAIZ, M, "p7", "cotas", "perfil.csv"), encoding="utf-8") as fh:
        per = {(r["variante"], r["fase"]): r for r in csv.DictReader(fh)}
    with open(os.path.join(RAIZ, M, "p7", "cotas", "variantes.csv"), encoding="utf-8") as fh:
        var = {v["variante"]: v for v in csv.DictReader(fh)}
    banda = 0.0
    for linea in leer(f"{M}/p7/cotas/perfil/r0.txt").splitlines():
        if linea and not linea.startswith("#"):
            _, _, w, n, _ = linea.split()
            if int(n) == nticks and clase(int(w, 16))[0] == "alu":      # una vez por tick: fuera del arranque y del sondeo
                banda += 1
    exigir(banda == float(per[("r0", "comparar")]["instrucciones_tick"]) + float(per[("r0", "decidir")]["instrucciones_tick"]),
           "el conteo por clase de la banda 40 en R0 no es comparar mas decidir")
    exigir(banda == float(per[("r2", "comparar")]["instrucciones_tick"]) - 4 + float(per[("r2", "decidir")]["instrucciones_tick"]),
           "el conteo por clase de la banda 40 en R2 no es el de R0")
    mops_r0 = banda * F_CLK / float(var["r0"]["ciclos_kernel"])
    mops_r2 = banda * F_CLK / float(var["r2"]["ciclos_kernel"])
    inten = ops_t / oct_t
    f = c_ejec / resp["prom"]
    smax = 1.0 / (1.0 - f)
    serie = sum(trabajo) / nticks

    out = ["Desempeno logrado, roofline y Amdahl de R3 (sw/c1.s), sobre el perfil por direccion del gemelo",
           "Generado por tools/report_c1.py (make informe PELDANO_INFORME=r3). No editar a mano.", "",
           f"Perfil: docs/mediciones/c1/perfil/gemelo.txt (make p7-c1-perfil), serie {SERIE}, 20000 ticks a 0,1 ms,",
           f"{nticks} ticks medidos. Las palabras del perfil son las de sw/c1.s ensamblado hoy.", "",
           "Definiciones (encabezado de tools/report_c1.py): operacion util = instruccion aritmetica, logica o de",
           "comparacion fuera de las esperas y de la telemetria; no cuentan loads, stores, saltos, li, la ni mv.",
           "Kernel = hilo 0, de leer PRICE a volver al sondeo. Bytes = loads y stores de los cuatro hilos fuera de",
           "los lazos de espera del precio. Trabajo = instrucciones fuera de la espera del precio, con una sola",
           "pasada por tick de los lazos en que un hilo espera el dato de otro; vueltas = las pasadas repetidas.", "",
           f"{'hilo':>5}{'trabajo':>10}{'vueltas':>10}{'ops utiles':>12}{'bytes':>9}   (por tick, promedio)"]
    for h in range(4):
        out.append(f"{h:>5}{trabajo[h] / nticks:>10.2f}{vueltas[h] / nticks:>10.2f}{ops[h] / nticks:>12.2f}{octetos[h] / nticks:>9.2f}")
    out += [f"{'suma':>5}{serie:>10.2f}{sum(vueltas) / nticks:>10.2f}{ops_t:>12.2f}{oct_t:>9.2f}", "",
            f"Llamadas a producto: {n_d} para D y {n_tel} para la telemetria; a D se le asigna el {100 * parte_d:.2f} % de la rutina.",
            f"Kernel del hilo 0: {k_ic:.2f} instrucciones y {k_cic:.2f} ciclos por tick (CPI {k_cic / k_ic:.3f}).",
            f"Desempeno logrado: {ops_t:.2f} x 25 MHz / {k_cic:.2f} = {mops:.3f} MOPS. Ppeak 25 MOPS (cuatro hilos).",
            f"Intensidad operacional: {ops_t:.2f} / {oct_t:.2f} = {inten:.4f} Op/B (quiebre de R3 en Ppeak / Bs = {F_CLK / BS:.2f} Op/B).",
            f"Con el mismo conteo por clase, la banda 40 tiene {banda:.0f} operaciones por tick y no las 11 contadas a mano de la",
            f"tabla de R0 a R2: en esa escala R0 logra {mops_r0:.2f} MOPS y R2 {mops_r2:.2f}, contra {mops:.2f} de R3.", "",
            "Amdahl. El hilo 3 es el ultimo en publicar (D_POL) y el hilo 0 escribe DECISION apenas lo ve.",
            f"Su rutina mas cara es `ejecutar` (las dos cuentas): {ic_ejec:.2f} instrucciones y {c_ejec:.2f} ciclos por tick,",
            f"f = {c_ejec:.2f} / {resp['prom']:.2f} = {f:.4f} de la respuesta promedio.",
            f"S = 1 / ((1 - f) + f / F): con F = 2, {1 / ((1 - f) + f / 2):.3f}; con F infinito, {smax:.3f} "
            f"(la respuesta bajaria de {resp['prom']:.2f} a {resp['prom'] - c_ejec:.2f} ciclos).",
            "Es una prediccion: no se construyo una variante de R3 con la contabilidad acelerada.", "",
            f"Trabajo de los cuatro hilos en serie: {serie:.2f} instrucciones por tick; a 4 ciclos por instruccion en un solo hilo",
            f"del barrel serian {4 * serie:.1f} ciclos en promedio (estimado: el programa de un hilo no se escribio)."]
    with open(os.path.join(RAIZ, C, "ops_roofline.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    o = "docs/mediciones/c1/ops_roofline.txt"
    mc.poner("Ops", num(ops_t, 1), o)
    mc.poner("Mops", num(mops, 2), o)
    mc.poner("Intensidad", num(inten, 2), o)
    mc.poner("OpsBandaPorClase", num(banda), o)
    mc.poner("MopsRceroPorClase", num(mops_r0, 2), o)
    mc.poner("MopsRdosPorClase", num(mops_r2, 2), o)
    mc.poner("MopsSobreRdos", num(mops / mops_r2, 1), o)
    mc.poner("KernelCiclos", num(k_cic, 1), o)
    mc.poner("EjecutarCiclos", num(c_ejec, 1), o)
    mc.poner("EjecutarIc", num(ic_ejec, 1), o)
    mc.poner("AmdahlF", num(100 * f, 1), o)
    mc.poner("AmdahlSmax", num(smax, 2), o)
    mc.poner("AmdahlRespMin", num(resp["prom"] - c_ejec, 0), o)
    mc.poner("TrabajoSerie", num(serie, 0), o)
    mc.poner("TrabajoSerieCiclos", num(4 * serie, 0), o)
    mc.poner("EsperaHiloCero", num(vueltas[0] * 4 / nticks, 0), o)
    return dict(ops=ops_t, mops=mops, inten=inten, k_cic=k_cic, k_ic=k_ic)


def punto_33(mc, tabla, num, hw, resp, p):
    """La escalera R0 a R3 en una tabla, y el roofline con el punto de R3."""
    d = os.path.join(RAIZ, M, "p7", "cotas")
    with open(os.path.join(d, "variantes.csv"), encoding="utf-8") as fh:
        var = {v["variante"]: v for v in csv.DictReader(fh)}
    f = lambda x, k=2: num(float(x), k)   # noqa: E731
    nombres = (("r0", "R0: Espino base"), ("seg", "Segmentado"), ("barrel", "Barrel, 1 hilo"),
               ("r2", "R1 y R2: barrel y tabla"))
    filas = []
    for k, nombre in nombres:
        v = var[k]
        filas.append([nombre, f"{num(int(v['celdas']))} / {v['lut4']} / {v['bram']}", f(v["fmax_min_mhz"]),
                      f"{f(v['resp_prom_ciclos'], 1)} / {v['resp_peor_ciclos']}", f(v["cpi_kernel"], 2), v["ops_utiles_tick"],
                      f(v["mops_logrado"]), f(v["ppeak_mops"], 2).replace("{,}00", "").replace("{,}50", "{,}5"), f(v["uso_r3_pct"], 1)])
    filas.append("---")
    filas.append(["R3: tabla de 512 palabras", f"{num(hw['celdas'])} / {hw['lut4']} / {hw['bram']}", num(hw["fmin"], 2),
                  f"{num(resp['prom'], 1)} / {resp['peor']}", "4{,}00", num(p["ops"], 1), num(p["mops"], 2), "25",
                  num(100.0 * resp["peor"] / PRESUPUESTO[3], 1)])
    ancha(tabla, os.path.join(G, "t33r3.tex"),
          ["Peldaño", "Celdas / LUT4 / BRAM", "$f_{\\max}$ (MHz)", "Resp. prom. / peor", "CPI",
           "Ops/tick", "MOPS", "$P_{peak}$", "\\% presup."], filas, "lrrrrrrrr",
          "R0 a R2 corren la banda 40 y R3 corre C1. Recursos: 10 semillas de nextpnr a 25 MHz, todas cierran; $f_{\\max}$ es la "
          "mínima. Respuesta en ciclos, serie de práctica a 0,1 ms; \\% presup.: peor caso sobre los 2\\,262 ciclos de la ronda 3. "
          "CPI del kernel (4 por hilo en el barrel). MOPS = operaciones útiles $\\times$ 25 MHz / ciclos del kernel. Fuentes: "
          "\\texttt{docs/mediciones/p7/cotas/variantes.txt}, \\texttt{docs/mediciones/c1/timing.txt} y \\texttt{ops\\_roofline.txt}.")
    o = "docs/mediciones/p7/cotas/variantes.csv"
    mc.poner("RceroRespProm", f(var["r0"]["resp_prom_ciclos"], 1), o)
    mc.poner("RceroRespPeor", var["r0"]["resp_peor_ciclos"], o)
    mc.poner("RceroMops", f(var["r0"]["mops_logrado"]), o)
    mc.poner("RdosMops", f(var["r2"]["mops_logrado"]), o)
    mc.poner("RdosRespPeor", var["r2"]["resp_peor_ciclos"], o)
    mc.poner("RdosCeldas", num(int(var["r2"]["celdas"])), o)
    mc.poner("SegRespPeor", var["seg"]["resp_peor_ciclos"], o)
    mc.poner("SegMops", f(var["seg"]["mops_logrado"]), o)
    r2 = leer(f"{M}/fondo/r2/ticks.txt").split("=== Ronda 3")[1].split("=== Ronda")[0]
    m = re.search(r"DECISION \(respuesta\)\s+(\d+)\s+([\d.]+)\s+(\d+)", r2)
    exigir(m is not None and m.group(3) == var["r2"]["resp_peor_ciclos"], "la respuesta de R2 del RTL no calza con el gemelo")
    mc.poner("RdosRespMin", m.group(1), "docs/mediciones/fondo/r2/ticks.txt")
    with open(os.path.join(d, "amdahl.csv"), encoding="utf-8") as fh:
        amd = list(csv.DictReader(fh))
    cambio = {"seg_clase": "R0 $\\to$ segmentado, CPI de la clase 7", "seg": "R0 $\\to$ segmentado, costo medido",
              "barrel": "R0 $\\to$ barrel, un hilo"}
    exigir(len(amd) == 6 and all(a["caso"] in cambio for a in amd), "amdahl.csv no tiene las seis filas esperadas")
    tabla(os.path.join(G, "t33r3amdahl.tex"), ["Ventana", "Cambio", "$S$ predicho", "$S$ medido", "Ciclos pred. / med."],
          [["Respuesta" if a["ventana"] == "resp" else "Kernel", cambio[a["caso"]], f(a["s_predicho"], 3), f(a["s_medido"], 3),
            f"{f(a['ciclos_predichos'])} / {f(a['ciclos_medidos'])}"] for a in amd], "llrrr",
          "Amdahl generalizado, $S = 1 / \\sum_i (f_i / F_i)$, con las fracciones del perfil de R0. "
          "Fuente: \\texttt{docs/mediciones/p7/cotas/amdahl.txt}.")
    am = leer(f"{M}/p7/cotas/amdahl.txt").split("=== Ventana: kernel")[1].split("--- R0 -> barrel")[1]
    m = re.search(r"S predicho ([\d.]+) \([\d.]+ ciclos\), S medido ([\d.]+)", am)
    mc.poner("AmdahlBarrelPred", num(float(m.group(1)), 3), "docs/mediciones/p7/cotas/amdahl.txt")
    mc.poner("AmdahlBarrelMed", num(float(m.group(2)), 3), "docs/mediciones/p7/cotas/amdahl.txt")

    # Roofline: la figura de la regla de cotas más el punto de R3
    lineas = leer(f"{M}/p7/cotas/roofline.tex").splitlines()
    exigir(lineas[-1].strip() == "\\end{tikzpicture}", "roofline.tex no termina como se esperaba")
    lineas[0] = "% roofline_r3.tex: generado por tools/report_c1.py desde docs/mediciones/p7/cotas/roofline.tex y c1/ops_roofline.txt."
    for etiqueta in ("R0 base", "Segmentado"):
        viejo = "node[left,font=\\scriptsize,black] {" + etiqueta + "}"
        exigir(sum(viejo in l for l in lineas) == 1, f"roofline.tex: no esta la etiqueta de {etiqueta}")
        lineas = [l.replace(viejo, "node[below right,font=\\scriptsize,black] {" + etiqueta + "}") for l in lineas]
    viejo = "node[below,font=\\scriptsize,black] {Barrel 1 hilo}"
    exigir(sum(viejo in l for l in lineas) == 1, "roofline.tex: no esta la etiqueta del barrel")
    lineas = [l.replace(viejo, "node[below right,font=\\scriptsize,black] {Barrel, 1 hilo}") for l in lineas]
    viejo = "node[right,font=\\scriptsize,black] {R2 (4 hilos)}"
    exigir(sum(viejo in l for l in lineas) == 1, "roofline.tex: no esta la etiqueta de R2")
    lineas = [l.replace(viejo, "node[left,font=\\scriptsize,black] {R2}") for l in lineas]
    punto = (f"  \\filldraw[red!70!black] ({math.log10(p['inten']):.4f},{math.log10(p['mops']):.4f}) circle (2.6pt) "
             "node[below left,font=\\scriptsize,black] {R3 (C1)};")
    with open(os.path.join(G, "roofline_r3.tex"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas[:-1] + [punto, lineas[-1]]) + "\n")


def constantes(mc, num):
    """Lo que informe_r3.tex escribe como texto (parámetros del diseño, criterio del examen, números de
    línea) se comprueba aquí contra su archivo de origen: si alguno cambia, el informe no se genera."""
    sys.path[:0] = [os.path.join(RAIZ, "ref", "c1")]
    import c1 as C1m           # noqa: E402
    import tablas as TB        # noqa: E402
    exigir((TB.CLASES, TB.HISTERESIS, TB.T_MIN, TB.P_MIN, TB.LARGO_A, TB.LARGO_M, TB.N) == (8, 64, 390, 0.95, 1250, 2500, 20000),
           "ref/c1/tablas.py: cambio un parametro que el informe cita (clases, histeresis, tick 390, 0,95, tramos)")
    exigir((TB.PROGRAMA["m"], TB.PROGRAMA["plazo"], TB.PROGRAMA["caja"], TB.PROGRAMA["comision"], C1m.OBJ_MAX) == (100, 28, 10000, 5, 511),
           "ref/c1/tablas.py: cambio un parametro del programa que el informe cita (M, plazo, caja, comision, tope)")
    exigir(TB.PARAMETROS[TB.T_BANDA_COMPRA] == 141 and TB.PARAMETROS[TB.T_BANDA_VENTA] == 215, "cambio la banda 40")
    ex = leer(f"{C}/c1_examen.txt")
    exigir("Rivales y pesos: ext 0,30, f5 0,30, b30 0,10, b50 0,10, b60 0,10, b40 0,10" in ex, "c1_examen.txt: cambiaron los pesos de los rivales")
    exigir("banda 40 + 20 puntos" in ex and "banda 40 - 8 puntos" in ex, "c1_examen.txt: cambio el criterio")
    exigir("diferencia de 10 o más" in ex and "mayor que -10" in ex, "c1_examen.txt: cambio la definicion de ganar y de no quedar debajo")
    exigir("Es la tercera mirada a las cinco empresas" in ex, "c1_examen.txt: falta la nota de la tercera mirada")
    exigir("de 664 a 1 240 por ronda" in leer("README.md"), "README.md: no esta la cifra del candado que igualaba acciones")
    exigir("La meseta va de w = 40 a w = 76 (todas a menos del 2 %" in leer("docs/cotas.md"), "docs/cotas.md: no esta la meseta de la banda")
    exigir("(1131 ciclos)" in leer("docs/puertas.md"), "docs/puertas.md: no esta el limite de 1131 ciclos")
    exigir("No hay ningún dato de la maestra real con órdenes parciales" in leer("docs/bitacora/c1.md"),
           "docs/bitacora/c1.md: falta el registro de que no habia ordenes parciales con la maestra real")
    p7 = leer(f"{M}/p7/cifras.tex")
    exigir("\\newcommand{\\pSieteDobleSemillasBase}{0}" in p7, "p7/cifras.tex: el duplicador ya no falla en todas las semillas con el Espino base")
    exigir(PRESUPUESTO[3] == (PERIODO_NS[3] - 9500) // 40, "presupuesto de la ronda 3")
    mc.poner("Presupuesto", num(PRESUPUESTO[3]), "tb/tb_proyecto_4.sv: (100000 ns - 9500 ns) / 40 ns")
    mc.poner("LimiteGrupo", num(PRESUPUESTO[3] // 2), "docs/puertas.md, criterio 4: la mitad del presupuesto de la ronda 3")
    datos = buscar(r"Datos: (\d+) palabras", leer(f"{C}/tamano.txt"), int)
    mc.poner("PalabrasDatos", datos, "docs/mediciones/c1/tamano.txt")
    # Los números de línea de sw/c1.s y de ref/c1/c1.py que cita el informe
    asm = leer("sw/c1.s").splitlines()
    for linea, texto in ((31, "# Memoria compartida"), (37, "D_POL"), (87, "hilo0:"), (179, "j    h0_espera"), (191, "hilo1:"),
                         (314, "j    h1_espera"), (322, "hilo2:"), (382, "j    h2_espera"), (390, "hilo3:"), (529, "j    h3_espera"),
                         (257, "h1_suma:"), (449, "h3_fase_a:"), (472, "addi x13, x13, -512"), (511, "or   x8, x8, x9"),
                         (541, "ejecutar:"), (620, "producto:"), (666, ".org 0x768")):
        exigir(texto in asm[linea - 1], f"sw/c1.s: la linea {linea} ya no es '{texto}' (el informe la cita)")
    py = leer("ref/c1/c1.py").splitlines()
    exigir(py[83].startswith("def media_posicion") and py[106].strip() == "return M_", "ref/c1/c1.py: cambiaron las lineas 84 a 107")
    pa = leer(f"{C}/puerta_a.txt")
    mc.poner("ApagadaPeor", buscar(r"Peor caso de R3 apagado: (\d+) ciclos", pa, int), "docs/mediciones/c1/puerta_a.txt")


def punto_c1(tabla, num):
    """Todo lo de R3. `tabla` y `num` son los de tools/report.py."""
    mc = Macros()
    constantes(mc, num)
    punto_31(mc, tabla, num)
    hw = verificacion(mc, num)
    resp = punto_32(mc, tabla, num)
    p = perfil_r3(mc, num, resp)
    punto_33(mc, tabla, num, hw, resp, p)
    mc.escribir(os.path.join(G, "cifras_c1.tex"))
    return len(mc.d)
