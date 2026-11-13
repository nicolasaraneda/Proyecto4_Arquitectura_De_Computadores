#!/usr/bin/env python3
"""costo_mv2x2.py: verifica y mide el costo del producto 2x2 en punto fijo.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Es la parte de diseño y costo del último peldaño de la escalera de co-diseño
(docs/producto_2x2.md). No modifica el SoC: todo se arma en build/mv2x2/.

  1. Testbench: las versiones de coeficientes fijos (factorizada y directa) y
     la de multiplicadores reales contra los vectores de ref/mv2x2.py.
  2. Costo en la FPGA, módulo suelto: LUT4 y celdas de acarreo de synth_ice40
     para varias precisiones de los coeficientes, con y sin saturación, y
     para la versión de multiplicadores.
  3. Costo en la FPGA, integrado: el módulo conectado como instrucción de
     custom-0 en una copia del core base (commit fijo), con place and route.
     Entrega las celdas que agrega al SoC completo y la frecuencia máxima.
     La copia es solo para medir: no se verifica como instrucción.
  4. Costo en ASIC: celdas y área en GF180MCU (liberty típico, síntesis con
     abc) de las dos versiones. Necesita el PDK instalado con ciel. Si no
     está, esta parte se salta.

Uso, desde la raíz del repositorio:
    python3 tools/costo_mv2x2.py            # todo (unos minutos)
    python3 tools/costo_mv2x2.py --solo-tb  # solo el testbench (integración continua)
"""
import argparse
import glob
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, os.path.join(RAIZ, "tools"))
import mv2x2        # noqa: E402
import gen_mv2x2    # noqa: E402

D = "build/mv2x2"
MULT = "rtl/exhibicion/mv2x2_mult.v"
COMMIT_CORE = "16f9cc3"     # core base sobre el que se mide la integración
CELDAS_FPGA = 1280
NVEC = 20000

# Coeficientes del estimador calibrado contra la serie de práctica
# (docs/algoritmo.md, sección 4.1): phi = 1 - 1/32 - 1/128, K1 = 1/2 + 1/8 y
# K2 = 1/8 + 1/16. Con 7 bits de fracción son exactos: 123, 80 y 24.
CALIBRADA = ["--c", "7", "--k1", "0.625", "--k2", "0.1875", "--phi", "0.9609375"]


def correr(cmd, log=None, check=True):
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
    if log:
        with open(os.path.join(RAIZ, log), "w") as f:
            f.write(r.stdout + r.stderr)
    if check and r.returncode != 0:
        sys.stderr.write(r.stdout[-2000:] + r.stderr[-2000:])
        raise SystemExit(f"falló: {' '.join(cmd)[:200]}")
    return r


def generar(nombre, *args):
    """Genera build/mv2x2/NOMBRE.v y devuelve (ruta, matriz entera, s)."""
    ruta = f"{D}/{nombre}.v"
    args = [*args, "--nombre", nombre]
    a = ["python3", "tools/gen_mv2x2.py", *args]
    correr([*a, "-o", ruta])
    g00, g01, g10, g11, s = map(int, correr([*a, "--matriz"]).stdout.split())
    return ruta, [[g00, g01], [g10, g11]], s


# --- 1. Testbench --------------------------------------------------------------
def testbench():
    f_fact, g, s = generar("kal2_fact")
    f_dir, gd, sd = generar("kal2_dir", "--forma", "directa")
    for nombre, gi, si in (("fact", g, s), ("dir", gd, sd)):
        with open(os.path.join(RAIZ, f"{D}/vectores_{nombre}.hex"), "w", newline="\n") as f:
            for e, p, y in mv2x2.vectores(NVEC, gi, si):
                f.write(f"{e:08x}{p:02x}{y:08x}\n")
    lit = lambda x: f"-16'sd{-x}" if x < 0 else f"16'sd{x}"      # noqa: E731
    defs = [f"-DNVEC={NVEC}", f"-DS={s}", f"-DSD={sd}"]
    for pref, gi in (("G", g), ("GD", gd)):
        defs += [f"-D{pref}{i}{j}={lit(gi[i][j])}" for i in (0, 1) for j in (0, 1)]
    correr(["iverilog", "-g2012", "-s", "tb_mv2x2", *defs, "-o", f"{D}/tb", f_fact, f_dir, MULT, "tb/tb_mv2x2.sv"])
    salida = correr(["vvp", "-n", f"{D}/tb"]).stdout
    print(next(l for l in salida.splitlines() if "tb_mv2x2" in l))
    print(f"     matriz factorizada G x 2^{s} = {g}, matriz directa G x 2^{sd} = {gd}")
    return "PASS tb_mv2x2" in salida


# --- 2. FPGA, módulo suelto ------------------------------------------------------
def ice40(top, fuentes, chparam=""):
    """LUT4 y celdas de acarreo de synth_ice40 para un módulo suelto."""
    r = correr(["yosys", "-p", f"read_verilog {' '.join(fuentes)}; {chparam} synth_ice40 -top {top}; stat"],
               log=f"{D}/{top}_ice40.log")
    cuenta = lambda celda: int((re.findall(rf"^\s*(\d+)\s+{celda}\s*$", r.stdout, re.M)       # noqa: E731
                                or re.findall(rf"{celda}\s+(\d+)", r.stdout) or ["0"])[-1])
    return cuenta("SB_LUT4"), cuenta("SB_CARRY")


def fpga_suelto():
    print("\n== Costo en la FPGA, módulo suelto (synth_ice40) ==")
    print("La FPGA tiene 1280 celdas y el SoC base deja libres unas 200.")
    print(f"{'versión':<34} {'matriz entera':<34} {'términos':>8} {'LUT4':>6} {'acarreo':>8}")
    casos = [(f"fija, factorizada, C = {c}", f"fact_c{c}", ["--c", str(c)]) for c in (3, 4, 5, 6, 8)]
    casos += [(f"fija, directa, S = {s}", f"dir_s{s}", ["--forma", "directa", "--s", str(s)]) for s in (6, 8, 12)]
    casos += [("fija, factorizada, C = 6, sin saturar", "fact_c6_nosat", ["--c", "6", "--sin-saturar"]),
              ("fija, k1 = 1/32, k2 = 1/2, phi = 7/8", "fact_barata", ["--c", "5", "--k1", "0.03125", "--k2", "0.5", "--phi", "0.875"]),
              ("fija, calibrada (docs/algoritmo.md)", "fact_cal", CALIBRADA)]
    filas = {}

    def uno(caso):
        etiqueta, nombre, args = caso
        ruta, gi, s = generar(nombre, *args)
        ints = None
        if "directa" not in args:
            c = int(args[args.index("--c") + 1])
            ints = [gi[0][0] >> c, 0, gi[1][0] >> c]          # k1 y k2; phi sale de g01
            ints[1] = -gi[0][1] // ints[0] if ints[0] else 0
            terminos = sum(len(mv2x2.csd(x)) for x in ints)
        else:
            terminos = mv2x2.terminos_csd(gi)
        luts, acarreos = ice40(nombre, [ruta])
        return etiqueta, nombre, f"{gi[0]} {gi[1]} / 2^{s}", terminos, luts, acarreos

    with ThreadPoolExecutor(6) as pool:
        for etiqueta, nombre, mat, terminos, luts, acarreos in pool.map(uno, casos):
            filas[nombre] = luts
            print(f"{etiqueta:<34} {mat:<34} {terminos:>8} {luts:>6} {acarreos:>8}")
    for cw, s in ((8, 6), (14, 12)):
        luts, acarreos = ice40("mv2x2_mult", [MULT], f"chparam -set CW {cw} -set S {s} mv2x2_mult;")
        filas[f"mult{cw}"] = luts
        print(f"{f'multiplicadores, coeficientes de {cw} bits':<34} {'entradas (programable)':<34} {'':>8} {luts:>6} {acarreos:>8}")
    return filas


# --- 3. FPGA, integrado en el core base ------------------------------------------
PARCHE_DECODER = [
    ("  output reg         lsu_sign_o\n);", "  output reg         lsu_sign_o,\n  output reg         is_kal2_o\n);"),
    ("    lsu_sign_o     = 1'b1;\n", "    lsu_sign_o     = 1'b1;\n    is_kal2_o      = 1'b0;\n"),
    ("      default: illegal_insn_o = 1'b1;\n    endcase\n  end\n",
     "      7'h0b: begin                       // custom-0: kal2 rd, rs1, rs2\n"
     "        if (funct3 == 3'b110 && funct7 == 7'b0) begin\n"
     "          rf_we_o   = 1'b1;\n          is_kal2_o = 1'b1;\n"
     "        end else illegal_insn_o = 1'b1;\n      end\n\n"
     "      default: illegal_insn_o = 1'b1;\n    endcase\n  end\n"),
]
PARCHE_ID = [
    ("    .lsu_sign_o     (lsu_sign_dec)\n  );", "    .lsu_sign_o     (lsu_sign_dec),\n    .is_kal2_o      (is_kal2)\n  );"),
    ("  // Decode\n", "  // Decode\n  wire        is_kal2;\n  wire [31:0] kal2_result;\n"
                      "  kal2_fijo u_kal2 (.estado_i(rf_rdata_a_i), .precio_i(rf_rdata_b_i[7:0]), .estado_o(kal2_result));\n"),
    ("      default: rf_wdata_o = alu_result;", "      default: rf_wdata_o = is_kal2 ? kal2_result : alu_result;"),
]


def parchar(texto, cambios, archivo):
    for viejo, nuevo in cambios:
        if texto.count(viejo) != 1:
            raise SystemExit(f"el parche de {archivo} no calza con el commit {COMMIT_CORE}")
        texto = texto.replace(viejo, nuevo)
    return texto


def pnr(etiqueta, fuentes, semillas):
    """Sintetiza el SoC y corre nextpnr con varias semillas. Devuelve (celdas, [fmax])."""
    js = f"{D}/{etiqueta}.json"
    correr(["yosys", "-q", "-p", f"read_verilog {' '.join(fuentes)}; chparam -set MemFile \"sw/trade.hex\" pochoco_soc; "
            f"synth_ice40 -top pochoco_soc -json {js}"], log=f"{D}/{etiqueta}_yosys.log")

    def una(semilla):
        log = f"{D}/{etiqueta}_s{semilla}.log"
        correr(["nextpnr-ice40", "--hx1k", "--package", "vq100", "--freq", "25", "--seed", str(semilla),
                "--json", js, "--pcf", "goboard.pcf", "-l", log, "-q"], check=False)
        t = open(os.path.join(RAIZ, log)).read()
        lc = re.findall(r"ICESTORM_LC:\s+(\d+)/", t)
        fm = re.findall(r"Max frequency for clock[^:]*: ([\d.]+) MHz", t)
        return (int(lc[-1]) if lc else None), (float(fm[-1]) if fm else None)

    with ThreadPoolExecutor(len(semillas)) as pool:
        res = list(pool.map(una, semillas))
    celdas = next((lc for lc, _ in res if lc), None)
    return celdas, sorted(f for _, f in res if f)


def fpga_integrado(semillas):
    print(f"\n== Costo en la FPGA, integrado como instrucción en el core base ({COMMIT_CORE}) ==")
    base = f"{D}/core_{COMMIT_CORE}"
    archivos = correr(["git", "ls-tree", "-r", "--name-only", COMMIT_CORE, "rtl/"]).stdout.split()
    archivos = [a for a in archivos if a.endswith(".v") and "/exhibicion/" not in a]
    for a in archivos:
        destino = os.path.join(RAIZ, base, a)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "w", newline="\n") as f:
            f.write(correr(["git", "show", f"{COMMIT_CORE}:{a}"]).stdout)
    fuentes_base = [f"{base}/{a}" for a in archivos]

    con = f"{D}/core_kal2"
    fuentes_kal2 = []
    for a in archivos:
        texto = open(os.path.join(RAIZ, base, a)).read()
        if a.endswith("espino_decoder.v"):
            texto = parchar(texto, PARCHE_DECODER, a)
        if a.endswith("espino_id_stage.v"):
            texto = parchar(texto, PARCHE_ID, a)
        destino = os.path.join(RAIZ, con, a)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "w", newline="\n") as f:
            f.write(texto)
        fuentes_kal2.append(f"{con}/{a}")

    variantes = [("SoC base, sin la instrucción", "soc_base", fuentes_base, None),
                 ("con kal2, k1 = 1/32, k2 = 1/2, phi = 7/8", "soc_barata", fuentes_kal2,
                  ["--c", "5", "--k1", "0.03125", "--k2", "0.5", "--phi", "0.875"]),
                 ("con kal2, calibrada", "soc_cal", fuentes_kal2, CALIBRADA),
                 ("con kal2, factorizada, C = 4", "soc_c4", fuentes_kal2, ["--c", "4"]),
                 ("con kal2, factorizada, C = 6", "soc_c6", fuentes_kal2, ["--c", "6"])]
    print(f"{'variante':<42} {'celdas':>7} {'de 1280':>8} {'agrega':>7}   frecuencia máxima en {len(semillas)} semillas (MHz)")
    ref = None
    resultados = {}
    for etiqueta, nombre, fuentes, args in variantes:
        if args is not None:
            ruta, _, _ = generar(f"kal2_{nombre}", *args)
            texto = open(os.path.join(RAIZ, ruta)).read().replace(f"module kal2_{nombre}", "module kal2_fijo")
            ruta_fijo = f"{D}/kal2_fijo_{nombre}.v"
            open(os.path.join(RAIZ, ruta_fijo), "w", newline="\n").write(texto)
            fuentes = [*fuentes, ruta_fijo]
        celdas, fmax = pnr(nombre, fuentes, semillas)
        if celdas is None:                                  # no pasó el empaquetado: contar con Yosys
            t = open(os.path.join(RAIZ, f"{D}/{nombre}_s{semillas[0]}.log")).read()
            falla = (re.findall(r"ERROR: (.*)", t) or ["nextpnr falló"])[0]
            print(f"{etiqueta:<42} {'':>7} {'':>8} {'':>7}   no cabe: {falla[:70]}")
            continue
        ref = ref if ref is not None else celdas
        resultados[nombre] = (celdas, fmax)
        ftxt = (f"mín {fmax[0]:.1f}, mediana {fmax[len(fmax) // 2]:.1f}, máx {fmax[-1]:.1f}, "
                f"cierran a 25 MHz {sum(f >= 25 for f in fmax)} de {len(semillas)}") if fmax else "no cabe: falla el place and route"
        print(f"{etiqueta:<42} {celdas:>7} {100 * celdas / CELDAS_FPGA:>7.0f}% {celdas - ref:>+7}   {ftxt}")
    return resultados


# --- 4. ASIC, GF180MCU -------------------------------------------------------------
ENVOLTORIO = """
// Banco de coeficientes para la versión programable: cuatro registros que el
// programa escribe una vez (o cuando quiera cambiar las ganancias).
module mv2x2_prog #(parameter CW = 14, parameter S = 12) (
  input  wire clk_i,
  input  wire [3:0] we_i,
  input  wire [CW-1:0] wdata_i,
  input  wire [31:0] estado_i,
  input  wire [7:0] precio_i,
  output wire [31:0] estado_o
);
  reg signed [CW-1:0] g00, g01, g10, g11;
  always @(posedge clk_i) begin
    if (we_i[0]) g00 <= wdata_i;
    if (we_i[1]) g01 <= wdata_i;
    if (we_i[2]) g10 <= wdata_i;
    if (we_i[3]) g11 <= wdata_i;
  end
  mv2x2_mult #(.CW(CW), .S(S)) u (.estado_i(estado_i), .precio_i(precio_i),
    .g00_i(g00), .g01_i(g01), .g10_i(g10), .g11_i(g11), .estado_o(estado_o));
endmodule
"""


def liberty():
    patron = os.path.expanduser("~/.ciel/ciel/gf180mcu/versions/*/gf180mcuD/libs.ref/"
                                "gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__tt_025C_5v00.lib")
    rutas = sorted(glob.glob(patron))
    return rutas[-1] if rutas else None


def gf180(top, fuentes, lib, chparam=""):
    r = correr(["yosys", "-p", f"read_verilog {' '.join(fuentes)}; {chparam} synth -top {top} -flatten; "
                f"dfflibmap -liberty {lib}; abc -liberty {lib}; opt_clean; stat -liberty {lib}"], log=f"{D}/{top}_gf180.log")
    celdas = int((re.findall(r"^\s*(\d+)\s+[\d.E+]*\s*cells\s*$", r.stdout, re.M)
                  or re.findall(r"Number of cells:\s+(\d+)", r.stdout))[-1])
    area = float(re.findall(r"Chip area for (?:top )?module.*?:\s+([\d.]+)", r.stdout)[-1])
    return celdas, area


def asic():
    print("\n== Costo en ASIC, GF180MCU 7 pistas, liberty típico (síntesis con abc, sin place and route) ==")
    lib = liberty()
    if not lib:
        print("No se encontró el PDK (ciel, gf180mcuD): esta parte no se midió.")
        return {}
    env = f"{D}/mv2x2_prog.v"
    open(os.path.join(RAIZ, env), "w", newline="\n").write(ENVOLTORIO)
    casos = [("fija, k1 = 1/32, k2 = 1/2, phi = 7/8", "fact_barata", [f"{D}/fact_barata.v"], ""),
             ("fija, calibrada", "fact_cal", [f"{D}/fact_cal.v"], ""),
             ("fija, factorizada, C = 6", "fact_c6", [f"{D}/fact_c6.v"], ""),
             ("fija, directa, S = 12", "dir_s12", [f"{D}/dir_s12.v"], ""),
             ("multiplicadores de 17 x 8", "mv2x2_mult", [MULT], "chparam -set CW 8 -set S 6 mv2x2_mult;"),
             ("multiplicadores de 17 x 14", "mv2x2_mult", [MULT], "chparam -set CW 14 -set S 12 mv2x2_mult;"),
             ("multiplicadores de 17 x 14 y 4 registros", "mv2x2_prog", [MULT, env], "")]
    print(f"{'versión':<42} {'celdas':>7} {'área (um2)':>11}")
    res = {}
    for etiqueta, top, fuentes, chp in casos:
        celdas, area = gf180(top, fuentes, lib, chp)
        res[etiqueta] = (celdas, area)
        print(f"{etiqueta:<42} {celdas:>7} {area:>11.0f}")
    print("Referencia de escala: el SoC completo del Proyecto 3 ocupó 208 439 um2 de celdas en este mismo proceso.")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verificación y costo del producto 2x2")
    ap.add_argument("--solo-tb", action="store_true")
    ap.add_argument("--semillas", type=int, default=5)
    a = ap.parse_args(argv)
    os.makedirs(os.path.join(RAIZ, D), exist_ok=True)
    print("== Testbench: tres implementaciones contra ref/mv2x2.py ==")
    if not testbench():
        return 1
    if a.solo_tb:
        return 0
    fpga_suelto()
    fpga_integrado(list(range(1, a.semillas + 1)))
    asic()
    return 0


if __name__ == "__main__":
    sys.exit(main())
