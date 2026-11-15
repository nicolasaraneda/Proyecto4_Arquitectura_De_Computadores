#!/usr/bin/env python3
"""informe_recursos.py: arma los informes de tools/barrel/medir_recursos.sh.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Uso: informe_recursos.py CARPETA_DE_TRABAJO build/variantes SEMILLAS CARPETA_DE_MEDICIONES

Lee las líneas de resumen de tools/medir_variante.sh, los logs de nextpnr de
cada semilla y las estadísticas de Yosys, y escribe recursos.txt, desglose.txt
y ruta_critica.txt.
"""
import re
import subprocess
import sys

O, V, SEMILLAS, M = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
LC_TOTAL, RAM_TOTAL = 1280, 16


def ver(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip().splitlines()[0]


def cabecera(titulo):
    return [titulo,
            "Generado por tools/barrel/medir_recursos.sh (make barrel-recursos). No editar a mano.",
            "",
            "Herramientas:",
            "  " + ver(["yosys", "-V"]),
            "  " + ver(["nextpnr-ice40", "--version"]),
            ""]


# --- Líneas de medir_variante.sh ------------------------------------------------
filas = {}
for linea in open(f"{O}/lineas.txt"):
    m = re.match(r"(\S+)\s+celdas\s+(\d+) de 1280, BRAM\s+(\d+) de 16, LUT4\s+(\d+), fmax min\s+([\d.]+) mediana\s+([\d.]+)"
                 r" max\s+([\d.]+) MHz, cierran a 25 MHz (\d+) de (\d+)", linea)
    if m:
        filas[m.group(1)] = dict(lc=int(m.group(2)), ram=int(m.group(3)), lut=int(m.group(4)), fmin=float(m.group(5)),
                                 fmed=float(m.group(6)), fmax=float(m.group(7)), cierran=int(m.group(8)), n=int(m.group(9)))


def semillas(etq):
    return [float(x) for x in open(f"{V}/{etq}/fmax.txt").read().split()]


def recursos_log(etq, s=1):
    t = open(f"{V}/{etq}/soc.s{s}.log").read()
    r = {}
    for k in ("ICESTORM_LC", "ICESTORM_RAM", "SB_IO", "SB_GB"):
        m = re.search(k + r":\s+(\d+)/", t)
        r[k] = int(m.group(1)) if m else 0
    return r


NOMBRES = [
    ("barrel_base", "Espino base (sin definiciones)"),
    ("barrel_seg", "Pipeline de 3 etapas (-DESPINO_SEGMENTADO)"),
    ("barrel", "Barrel de 4 hilos (-DESPINO_BARREL)"),
]
RECORTES = [
    ("barrel_pc32", "contador de programa de 32 bits (en vez de 11)"),
    ("barrel_por4", "contador de reset de 4 bits (en vez de 12)"),
    ("barrel_ramdirecta", "memoria sin emulacion de lectura durante escritura"),
]
RAMDIRECTA = [
    ("barrel_base", "barrel_base_ramdirecta", "Espino base"),
    ("barrel_seg", "barrel_seg_ramdirecta", "Pipeline de 3 etapas"),
    ("barrel", "barrel_ramdirecta", "Barrel de 4 hilos"),
]

out = cabecera("Recursos y frecuencia maxima: Espino base, pipeline de 3 etapas y barrel")
out.append(f"Flujo: tools/medir_variante.sh, nextpnr-ice40 --hx1k --package vq100 --freq 25, goboard.pcf, semillas 1 a {SEMILLAS}.")
out.append("SoC completo: core, memoria, esclavo SPI, perifericos y contador de reset.")
out.append("")
out.append("1. Los tres cores, medidos en la misma corrida")
out.append("")
enc = f"  {'Variante':<46} {'Celdas':>6} {'%':>5} {'Libres':>6} {'LUT4':>5} {'BRAM':>4} {'Fmax min':>9} {'mediana':>8} {'max':>7}  Cierran a 25 MHz"
out.append(enc)


def fila(etq, texto):
    f = filas[etq]
    return (f"  {texto:<46} {f['lc']:>6} {100 * f['lc'] / LC_TOTAL:>4.0f}% {LC_TOTAL - f['lc']:>6} {f['lut']:>5} {f['ram']:>4} "
            f"{f['fmin']:>9.2f} {f['fmed']:>8.2f} {f['fmax']:>7.2f}  {f['cierran']} de {f['n']}")


for etq, texto in NOMBRES:
    out.append(fila(etq, texto))
b, s, x = filas["barrel_base"], filas["barrel_seg"], filas["barrel"]
out.append("")
out.append(f"  Barrel contra el base:       {x['lc'] - b['lc']:+d} celdas, {x['ram'] - b['ram']:+d} BRAM, mediana de fmax {x['fmed'] - b['fmed']:+.2f} MHz")
out.append(f"  Barrel contra el segmentado: {x['lc'] - s['lc']:+d} celdas, {x['ram'] - s['ram']:+d} BRAM, mediana de fmax {x['fmed'] - s['fmed']:+.2f} MHz")
out.append(f"  Libres con el barrel:        {LC_TOTAL - x['lc']} celdas de {LC_TOTAL} y {RAM_TOTAL - x['ram']} BRAM de {RAM_TOTAL}")
out.append(f"  Margen de timing del barrel: periodo minimo {1000 / x['fmin']:.1f} ns de 40 disponibles en la peor semilla")
out.append("")
out.append("  Frecuencia maxima por semilla (MHz):")
out.append(f"  {'semilla':<46} " + " ".join(f"{i:>6}" for i in range(1, SEMILLAS + 1)))
for etq, texto in NOMBRES:
    out.append(f"  {texto:<46} " + " ".join(f"{v:>6.2f}" for v in semillas(etq)))
out.append("")
out.append("2. Cuanto cambia cada recorte o agregado sobre el barrel")
out.append("")
out.append(f"  {'Variante del barrel':<52} {'Celdas':>6} {'Dif.':>5} {'Libres':>6} {'BRAM':>4} {'Fmax min':>9} {'mediana':>8} {'max':>7}  Cierran")
out.append(f"  {'barrel (referencia)':<52} {x['lc']:>6} {'':>5} {LC_TOTAL - x['lc']:>6} {x['ram']:>4} {x['fmin']:>9.2f} {x['fmed']:>8.2f} {x['fmax']:>7.2f}  {x['cierran']} de {x['n']}")
for etq, texto in RECORTES:
    f = filas[etq]
    out.append(f"  {texto:<52} {f['lc']:>6} {f['lc'] - x['lc']:>+5d} {LC_TOTAL - f['lc']:>6} {f['ram']:>4} {f['fmin']:>9.2f} {f['fmed']:>8.2f} {f['fmax']:>7.2f}  {f['cierran']} de {f['n']}")
out.append("")
out.append("  Una diferencia menor que unas 10 celdas esta dentro del ruido de la sintesis (decision T6).")
out.append("")
out.append("3. La memoria sin emulacion de lectura durante escritura, en los tres cores")
out.append("")
out.append("  Yosys agrega a pochoco_ram registros y multiplexores para que, si se lee y se escribe la misma")
out.append("  palabra en el mismo flanco, la lectura entregue el dato viejo, que es lo que dice el Verilog y")
out.append("  que la BRAM del iCE40 no garantiza. Con el atributo (* no_rw_check *) en el arreglo no los agrega.")
out.append("")
out.append(f"  {'Core':<24} {'Celdas':>6} {'sin emulacion':>14} {'Recupera':>9} {'Libres':>7} {'Fmax min':>9} {'mediana':>8} {'max':>7}  Cierran")
for a, d, texto in RAMDIRECTA:
    fa, fd = filas[a], filas[d]
    out.append(f"  {texto:<24} {fa['lc']:>6} {fd['lc']:>14} {fa['lc'] - fd['lc']:>9} {LC_TOTAL - fd['lc']:>7} {fd['fmin']:>9.2f} {fd['fmed']:>8.2f} {fd['fmax']:>7.2f}  {fd['cierran']} de {fd['n']}")
out.append("")
out.append("  No esta aplicado en rtl/. Cambia lo que pasa en la placa en un solo caso: leer y escribir")
out.append("  la misma palabra de la memoria en el mismo flanco. Ver docs/espino_barrel.md.")
out.append("")
r = recursos_log("barrel")
out.append(f"4. Otros recursos del barrel (semilla 1): {r['SB_IO']} pines de 72, {r['SB_GB']} buffers globales de 8")
out.append("")
out.append("5. Celdas que trabajan en el flanco de bajada (del conteo final de Yosys de cada variante)")
out.append("")


def flanco_bajada(etq):
    """Cuenta BRAM con reloj de lectura o de escritura invertido y flip-flops de flanco de bajada."""
    t = open(f"{V}/{etq}/yosys.log").read()
    ult = t[t.rfind("Number of cells"):] if "Number of cells" in t else t[t.rfind("cells"):]
    bram = sum(int(n) for n, c in re.findall(r"^\s+(\d+)\s+(SB_RAM40_4K\w+)\s*$", ult, re.M))
    ffn = sum(int(n) for n, c in re.findall(r"^\s+(\d+)\s+(SB_DFFN\w*)\s*$", ult, re.M))
    return bram, ffn


for etq, texto in NOMBRES:
    bram, ffn = flanco_bajada(etq)
    out.append(f"  {texto:<46} BRAM con reloj invertido: {bram:>2}   flip-flops de flanco de bajada: {ffn:>2}")
out.append("")
out.append("  El barrel y el base usan un solo flanco. El pipeline de 3 etapas lee la memoria de instrucciones")
out.append("  en el flanco de bajada y tiene rutas de medio ciclo (docs/espino_segmentado.md, seccion 8).")
open(f"{M}/recursos.txt", "w").write("\n".join(out) + "\n")

# --- Desglose por módulo ----------------------------------------------------------
TIPOS = ["SB_LUT4", "FF", "SB_CARRY", "SB_RAM40_4K"]


def stat(path):
    """Devuelve {modulo: {tipo: n}} de la salida de 'stat' de Yosys."""
    mods, actual = {}, None
    for linea in open(path):
        m = re.match(r"=== (.+) ===", linea)
        if m:
            actual = m.group(1).split("\\")[-1]
            mods[actual] = {t: 0 for t in TIPOS}
            continue
        m = re.match(r"\s+(\d+)\s+(SB_\w+)\s*$", linea)
        if m and actual:
            n, t = int(m.group(1)), m.group(2)
            if t.startswith("SB_DFF"):
                mods[actual]["FF"] += n
            elif t in mods[actual]:
                mods[actual][t] += n
    return mods


ROL = [("core", ("espino_core", "espino_barrel_core")), ("memoria (pochoco_ram)", ("pochoco_ram",)),
       ("esclavo SPI", ("pochoco_spi_slave",)), ("perifericos", ("pochoco_periph",)),
       ("pochoco_soc: reset, seleccion y multiplexor de lectura", ("pochoco_soc",))]

out = cabecera("Desglose por modulo: donde estan las celdas")
out.append("1. Sintesis con las fronteras del SoC conservadas (keep_hierarchy en u_core, u_ram, u_spi y u_periph)")
out.append("")
out.append("  Dentro de cada modulo todo se aplana y se optimiza. Entre modulos no, asi que el total de LUT4")
out.append("  es algo mayor que el del flujo normal, que aplana todo. Una celda logica del iCE40 tiene una LUT4")
out.append("  y un flip-flop: el numero de celdas despues de empaquetar es menor que LUT4 + FF.")
out.append("")
des = {n: stat(f"{O}/desglose_{n}.txt") for n in ("base", "segmentado", "barrel")}
out.append(f"  {'Modulo':<56} {'Base':^17} {'Segmentado':^17} {'Barrel':^17}")
out.append(f"  {'':<56} " + " ".join(f"{'LUT4':>5} {'FF':>4} {'acarr':>5}" for _ in range(3)))
tot = {n: [0, 0, 0] for n in des}
for texto, claves in ROL:
    celdas = []
    for n in ("base", "segmentado", "barrel"):
        d = next((v for k, v in des[n].items() if k in claves), {t: 0 for t in TIPOS})
        celdas.append(f"{d['SB_LUT4']:>5} {d['FF']:>4} {d['SB_CARRY']:>5}")
        for i, t in enumerate(TIPOS[:3]):
            tot[n][i] += d[t]
    out.append(f"  {texto:<56} " + " ".join(celdas))
out.append(f"  {'total con fronteras':<56} " + " ".join(f"{tot[n][0]:>5} {tot[n][1]:>4} {tot[n][2]:>5}" for n in ("base", "segmentado", "barrel")))
out.append(f"  {'flujo normal (todo aplanado): LUT4':<56} " + " ".join(f"{filas[e]['lut']:>5} {'':>4} {'':>5}" for e in ("barrel_base", "barrel_seg", "barrel")))
out.append(f"  {'flujo normal: celdas logicas despues de nextpnr':<56} " + " ".join(f"{filas[e]['lc']:>5} {'':>4} {'':>5}" for e in ("barrel_base", "barrel_seg", "barrel")))
out.append("")
out.append("  El banco de registros (4 BRAM) esta dentro del core y la memoria usa 8 BRAM en los tres casos.")
out.append("")
out.append("2. Bloques del core barrel sintetizados por separado (sin aplanar nada)")
out.append("")
out.append("  Cada modulo se sintetiza completo, aunque el barrel no use todas sus salidas. Sirve para ver el")
out.append("  tamano de cada bloque reutilizado, no para sumar.")
out.append("")
blo = stat(f"{O}/bloques_barrel.txt")
out.append(f"  {'Modulo':<56} {'LUT4':>5} {'FF':>4} {'acarr':>5}")
for k, texto in (("espino_alu", "espino_alu (reutilizada sin cambios)"),
                 ("espino_decoder", "espino_decoder (reutilizado sin cambios)"),
                 ("espino_load_store_unit", "espino_load_store_unit (cada una de las dos instancias)"),
                 ("espino_barrel_core", "espino_barrel_core: registros de etapa, PC y multiplexores")):
    d = blo.get(k)
    if d:
        out.append(f"  {texto:<56} {d['SB_LUT4']:>5} {d['FF']:>4} {d['SB_CARRY']:>5}")
out.append("")
out.append("3. Lo mismo medido por diferencia en el flujo normal (docs/mediciones/barrel/recursos.txt, seccion 2)")
out.append("")
for etq, texto in RECORTES:
    out.append(f"  {texto:<52} {filas[etq]['lc'] - x['lc']:>+5d} celdas")
open(f"{M}/desglose.txt", "w").write("\n".join(out) + "\n")

# --- Ruta crítica -------------------------------------------------------------------
def ruta(log):
    """Tramos de la última ruta crítica posedge -> posedge del log de nextpnr.

    Devuelve (tramos, logica, ruteo). Cada tramo es (tipo, retardo, acumulado,
    nombre, archivo:linea del RTL donde se define la red, si se conoce).
    """
    lineas = open(log).read().splitlines()
    ini = max(i for i, l in enumerate(lineas) if "Critical path report for clock" in l and "posedge -> posedge" in l)
    tramos, i = [], ini + 2
    while i < len(lineas):
        l = lineas[i]
        m = re.match(r"Info: ([\d.]+) ns logic, ([\d.]+) ns routing", l)
        if m:
            return tramos, float(m.group(1)), float(m.group(2))
        m = re.match(r"Info:\s+([\w-]+)\s+([\d.]+)\s+([\d.]+)\s+(Source|Net)\s+(\S+)", l)
        if m:
            tramos.append([m.group(1), float(m.group(2)), float(m.group(3)), m.group(5), ""])
        else:
            m = re.match(r"Info:\s+(\S+\.s?v):(\d+)", l)
            if m and tramos and not tramos[-1][4] and "oss-cad-suite" not in m.group(1):
                tramos[-1][4] = f"{m.group(1).split('/')[-1]}:{m.group(2)}"
        i += 1
    return tramos, 0.0, 0.0


def corto(nombre):
    nombre = re.sub(r"\$SB_IO_IN|\$glb_clk", "", nombre)
    # Los nombres que Yosys deriva de otra red son muy largos: se deja el comienzo
    return nombre if len(nombre) <= 60 else nombre[:57] + "..."


out = cabecera("Ruta critica de la semilla mas lenta de cada core")
out.append("Tomada del log de nextpnr (build/variantes/barrel*/soc.sN.log). Cada linea es un tramo de logica o de")
out.append("ruteo: retardo en ns, acumulado, nombre de la celda o de la red y, cuando nextpnr lo informa, la linea")
out.append("del RTL donde se define la red. Los tramos seguidos de una cadena de acarreo (el sumador) van en una linea.")
for etq, texto in NOMBRES + [("barrel_ramdirecta", "Barrel con la memoria sin emulacion")]:
    xs = semillas(etq)
    peor = min(range(len(xs)), key=lambda i: xs[i]) + 1
    tramos, logica, ruteo = ruta(f"{V}/{etq}/soc.s{peor}.log")
    out.append("")
    out.append(f"--- {texto}: semilla {peor}, {xs[peor - 1]:.2f} MHz ({1000 / xs[peor - 1]:.2f} ns) ---")
    n_logica = sum(1 for t in tramos if t[0] != "routing")
    k = 0
    while k < len(tramos):
        tipo, d, acum, nombre, donde = tramos[k]
        # Cadena de acarreo: tramos de lógica de 0,13 ns con ruteo de 0 a 0,26 ns entre ellos
        j, suma = k, 0.0
        while j < len(tramos) and ((tramos[j][0] == "logic" and tramos[j][1] <= 0.14 and "COUT" in tramos[j][3]) or
                                   (tramos[j][0] == "routing" and tramos[j][1] <= 0.27 and j > k)):
            suma += tramos[j][1]
            j += 1
        if j - k >= 6:
            out.append(f"  {'acarreo':<9} {suma:>5.2f} {tramos[j - 1][2]:>6.2f}  cadena de acarreo del sumador, {sum(1 for t in tramos[k:j] if t[0] == 'logic')} bits")
            k = j
            continue
        out.append(f"  {tipo:<9} {d:>5.2f} {acum:>6.2f}  {corto(nombre):<60} {donde}")
        k += 1
    out.append(f"  total: {logica:.2f} ns de logica y {ruteo:.2f} ns de ruteo, {n_logica} tramos de logica")
open(f"{M}/ruta_critica.txt", "w").write("\n".join(out) + "\n")
