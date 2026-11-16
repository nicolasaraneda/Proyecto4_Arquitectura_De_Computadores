#!/usr/bin/env python3
"""autoprueba.py: firma esperada, simulación y bitstream de la autoprueba en placa.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

La autoprueba (rtl/autoprueba/autoprueba_top.v, docs/autoprueba.md) es el SoC
que compite con una maestra SPI interna: manda una caminata aleatoria de
NTICKS precios generada con un LFSR y acumula los bytes que lee en una firma
CRC-16. Este script:

  firma       Calcula la firma esperada de un peldaño de dos formas
              independientes y exige que coincidan: con el gemelo digital
              corriendo el mismo .hex con los tiempos de la maestra interna, a
              los tres períodos, y con la referencia del algoritmo
              (ref/trader.py o ref/fondo.py).
  simular     Simula autoprueba_top (RTL, Verilator) apretando cada botón y
              compara la firma de los 7 segmentos con la esperada.
  control     Control negativo: el mismo programa con una constante cambiada
              tiene que terminar con LED4 (firma distinta).
  bitstream   Sintetiza, rutea y empaqueta la autoprueba del peldaño, con la
              firma esperada adentro. Informa celdas, BRAM y frecuencia máxima.
  chip        Simula el bitstream ya ruteado (icebox_vlog) con el mismo
              testbench, por los pines.

Peldaños (sección 16.3 del plan): r0 es el core base con sw/trade.s
(max_media). r1 y r2 se agregan cuando P5 deje sus definiciones.

Uso, desde la raíz:
    python3 tools/autoprueba.py firma r0
    python3 tools/autoprueba.py simular r0 [--botones 3,2,1]
    python3 tools/autoprueba.py bitstream r0
    python3 tools/autoprueba.py chip r0
    python3 tools/autoprueba.py todo r0        # las cuatro, en orden
Los productos quedan en build/autoprueba/<peldaño>/ y el informe en
docs/mediciones/autoprueba_<peldaño>.txt.
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
os.environ["PATH"] = os.path.expanduser("~/herramientas/oss-cad-suite/bin") + os.pathsep + os.environ["PATH"]

import fondo     # noqa: E402
import market    # noqa: E402
import trader    # noqa: E402

NTICKS = 2000
PERIODOS = {1: 250000, 2: 25000, 3: 2500}           # ciclos de 40 ns por botón
NOMBRE_PERIODO = {1: "10 ms", 2: "1 ms", 3: "0,1 ms"}
# Tiempos de la maestra interna en el gemelo (ver el encabezado de autoprueba_top.v)
GEMELO_SPI = ["--cs-setup-ns", "1280", "--sclk-medio-ns", "640", "--cs-hold-ns", "640"]
INICIO_NS = 1_000_021        # cualquier instante después del reset; el pin cambia 1 ns después de un flanco

PELDANOS = {
    # nombre: (definiciones del RTL, programa .s, opciones del ensamblador, opciones del gemelo, referencia)
    "r0": ("", "sw/trade.s", [], [], "trader"),
}
# Control negativo: el mismo programa con una constante cambiada, que la
# autoprueba tiene que rechazar (LED4). Para R0, el umbral de la regla base.
CONTROL = {
    "r0": ["-D", "UMBRAL_COMPRA=-128"],
}


def sh(cmd, log=None, **kw):
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, **kw)
    if log:
        with open(os.path.join(RAIZ, log), "w") as f:
            f.write(r.stdout + r.stderr)
    return r


# --- La secuencia y la firma, igual que autoprueba_maestra --------------------------------
def precios(n=NTICKS):
    """Caminata aleatoria: 128 y después pasos de +1 o -1 según el bit nuevo del LFSR."""
    lfsr, p, salida = 0xACE1, 128, [128]
    for _ in range(n - 1):
        nuevo = ((lfsr >> 15) ^ (lfsr >> 13) ^ (lfsr >> 12) ^ (lfsr >> 10)) & 1
        lfsr = ((lfsr << 1) & 0xFFFF) | nuevo
        p = min(255, p + 1) if nuevo else max(1, p - 1)
        salida.append(p)
    return salida


def crc16(datos, crc=0xFFFF):
    """CRC-16/CCITT: polinomio 0x1021, valor inicial 0xFFFF, bit más significativo primero.
    Byte a byte da lo mismo que el cálculo bit a bit de la maestra."""
    for b in datos:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def carpeta(peldano):
    d = f"build/autoprueba/{peldano}"
    os.makedirs(os.path.join(RAIZ, d), exist_ok=True)
    return d


def preparar(peldano):
    """Ensambla el programa del peldaño y escribe la serie. Devuelve (hex, serie)."""
    _, fuente, asm_opts, _, _ = PELDANOS[peldano]
    d = carpeta(peldano)
    hexfile = f"{d}/programa.hex"
    r = sh([sys.executable, "tools/pochoasm.py", *asm_opts, fuente, "-o", hexfile])
    if r.returncode != 0:
        raise SystemExit(f"FAIL: no ensambla {fuente}\n{r.stdout}{r.stderr}")
    serie = f"{d}/serie.csv"
    market_rows = "tick,price\n" + "".join(f"{i},{p}\n" for i, p in enumerate(precios()))
    with open(os.path.join(RAIZ, serie), "w", newline="\n") as f:
        f.write(market_rows)
    return hexfile, serie


def firma(peldano, informe):
    hexfile, serie = preparar(peldano)
    _, _, _, gem_opts, ref = PELDANOS[peldano]
    d = carpeta(peldano)
    r = sh(["cc", "-O2", "-o", "build/gemelo", "ref/gemelo/gemelo.c"])
    if r.returncode != 0:
        raise SystemExit("FAIL: el gemelo no compila")
    firmas = {}
    for boton, ciclos in PERIODOS.items():
        csv = f"{d}/gemelo_{boton}.csv"
        r = sh(["build/gemelo", *gem_opts, "--hex", hexfile, "--serie", serie, "--periodo-ns", str(40 * ciclos),
                "--inicio-ns", str(INICIO_NS), *GEMELO_SPI, "--csv", csv], log=f"{d}/gemelo_{boton}.log")
        if "Testbenchs aprobados: 4/4" not in r.stdout:
            raise SystemExit(f"FAIL: el gemelo no entrega 4/4 a {NOMBRE_PERIODO[boton]} (ver {d}/gemelo_{boton}.log)")
        leidos = [int(l.split(",")[2], 16) for l in open(os.path.join(RAIZ, csv)).read().splitlines()[1:]]
        peor = re.search(r"Peor caso precio->decision: (\d+) ciclos \(disponibles: (\d+)\)", r.stdout)
        firmas[boton] = (crc16(leidos), leidos, peor.group(1), peor.group(2))
    p = precios()
    estrategia = fondo.Fondo() if ref == "fondo" else trader.Oficial()
    esperados = trader.decisiones(p, estrategia, 0)
    f_ref = crc16(esperados)
    m = market.simular(p, esperados)
    informe.append(f"Serie: caminata aleatoria del LFSR, {NTICKS} precios, entre {min(p)} y {max(p)}, "
                   f"sha256 {hashlib.sha256(bytes(p)).hexdigest()[:16]}...")
    informe.append(f"Referencia ref/{ref}.py: firma {f_ref:04x}, {sum(a != b for a, b in zip(esperados, esperados[1:]))} "
                   f"cambios de byte, patrimonio {m.w} con {m.ordenes} ordenes")
    ok = True
    for boton, (f, leidos, peor, disp) in firmas.items():
        igual = leidos == esperados
        ok &= igual and f == f_ref
        informe.append(f"{'PASS' if igual and f == f_ref else 'FAIL'} gemelo con SW{boton} ({NOMBRE_PERIODO[boton]}): "
                       f"firma {f:04x}, bytes {'identicos' if igual else 'DISTINTOS'} a la referencia, "
                       f"peor caso {peor} de {disp} ciclos")
    if not ok:
        raise SystemExit("\n".join(informe) + "\nFAIL: la firma no es la misma en las dos formas de calcularla")
    with open(os.path.join(RAIZ, f"{d}/firma.txt"), "w") as fh:
        fh.write(f"{f_ref:04x}\n")
    return f_ref


def fuentes_soc():
    rtl = sorted(f"rtl/{f}" for f in os.listdir(os.path.join(RAIZ, "rtl")) if f.endswith(".v"))
    core = sorted(f"rtl/espino_core/{f}" for f in os.listdir(os.path.join(RAIZ, "rtl/espino_core")) if f.endswith(".v"))
    return rtl + core + ["rtl/autoprueba/autoprueba_top.v"]


def simular(peldano, informe, botones):
    defs = PELDANOS[peldano][0]
    d = carpeta(peldano)
    hexfile = f"{d}/programa.hex"
    esperada = int(open(os.path.join(RAIZ, f"{d}/firma.txt")).read(), 16)
    cells = subprocess.check_output(["yosys-config", "--datdir"], text=True).strip() + "/ice40/cells_sim.v"
    r = sh(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", "tb_autoprueba",
            "-DNO_ICE40_DEFAULT_ASSIGNMENTS", *defs.split(), f'-GPROGRAMA="{hexfile}"', f"-GFIRMA_P=16'h{esperada:04x}", "-O3", "--Mdir", f"{d}/obj",
            "-o", "sim", cells, *fuentes_soc(), "tb/autoprueba/tb_autoprueba.sv"], log=f"{d}/verilator.log")
    if r.returncode != 0:
        raise SystemExit(f"FAIL: Verilator no compila la autoprueba (ver {d}/verilator.log)")
    ok = True
    for b in botones:
        r = sh([f"{d}/obj/sim", f"+BOTON={b}", f"+FIRMA={esperada:04x}"], log=f"{d}/sim_{b}.log")
        linea = [l for l in r.stdout.splitlines() if l.startswith("RESULTADO")]
        res = linea[0] if linea else "RESULTADO sin salida: " + r.stdout[-200:]
        ok &= res.endswith("PASS")
        informe.append(f"{'PASS' if res.endswith('PASS') else 'FAIL'} RTL con SW{b} ({NOMBRE_PERIODO[b]}): {res}")
    return ok


def control(peldano, informe):
    """La autoprueba con un programa alterado debe terminar en LED4, no en LED3."""
    defs, fuente, asm_opts, gem_opts, _ = PELDANOS[peldano]
    d = carpeta(peldano)
    esperada = int(open(os.path.join(RAIZ, f"{d}/firma.txt")).read(), 16)
    hexfile = f"{d}/control.hex"
    r = sh([sys.executable, "tools/pochoasm.py", *asm_opts, *CONTROL[peldano], fuente, "-o", hexfile])
    if r.returncode != 0:
        raise SystemExit(f"FAIL: no ensambla el control\n{r.stdout}{r.stderr}")
    r = sh(["build/gemelo", *gem_opts, "--hex", hexfile, "--serie", f"{d}/serie.csv", "--periodo-ns", "100000",
            "--inicio-ns", str(INICIO_NS), *GEMELO_SPI, "--csv", f"{d}/control.csv"])
    leidos = [int(l.split(",")[2], 16) for l in open(os.path.join(RAIZ, f"{d}/control.csv")).read().splitlines()[1:]]
    f_control = crc16(leidos)
    cells = subprocess.check_output(["yosys-config", "--datdir"], text=True).strip() + "/ice40/cells_sim.v"
    r = sh(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", "tb_autoprueba",
            "-DNO_ICE40_DEFAULT_ASSIGNMENTS", *defs.split(), f'-GPROGRAMA="{hexfile}"', f"-GFIRMA_P=16'h{esperada:04x}",
            "-O3", "--Mdir", f"{d}/obj_control", "-o", "sim", cells, *fuentes_soc(), "tb/autoprueba/tb_autoprueba.sv"],
           log=f"{d}/verilator_control.log")
    if r.returncode != 0:
        raise SystemExit(f"FAIL: Verilator no compila el control (ver {d}/verilator_control.log)")
    r = sh([f"{d}/obj_control/sim", "+BOTON=3", f"+FIRMA={esperada:04x}"], log=f"{d}/control_3.log")
    linea = [l for l in r.stdout.splitlines() if l.startswith("RESULTADO")]
    res = linea[0] if linea else "sin salida"
    ok = res.endswith("FAIL") and "LED=1010" in res and f"firma={f_control:04x}" in res and f_control != esperada
    informe.append(f"{'PASS' if ok else 'FAIL'} control negativo ({' '.join(CONTROL[peldano][1:])}): el gemelo da "
                   f"{f_control:04x} y la autoprueba lo rechaza con LED4: {res}")
    return ok


def bitstream(peldano, informe):
    defs = PELDANOS[peldano][0]
    d = carpeta(peldano)
    hexfile = f"{d}/programa.hex"
    esperada = int(open(os.path.join(RAIZ, f"{d}/firma.txt")).read(), 16)
    lectura = f"read_verilog {defs} {' '.join(fuentes_soc())}"
    r = sh(["yosys", "-q", "-l", f"{d}/yosys.log", "-p",
            f'{lectura}; chparam -set MemFile "{hexfile}" -set FIRMA_ESPERADA {esperada} autoprueba_top; '
            f"synth_ice40 -top autoprueba_top -json {d}/autoprueba.json"])
    if r.returncode != 0:
        raise SystemExit(f"FAIL: yosys (ver {d}/yosys.log)")
    r = sh(["nextpnr-ice40", "--hx1k", "--package", "vq100", "--freq", "25", "--json", f"{d}/autoprueba.json",
            "--pcf", "goboard.pcf", "--asc", f"{d}/autoprueba.asc", "-l", f"{d}/nextpnr.log", "-q"])
    log = open(os.path.join(RAIZ, f"{d}/nextpnr.log")).read()
    if r.returncode != 0:
        informe.append("FAIL nextpnr: " + (re.findall(r"ERROR:.*", log) or ["ver el log"])[0])
        return False
    lc = re.findall(r"ICESTORM_LC:\s+(\d+)/\s*(\d+)", log)[-1]
    ram = re.findall(r"ICESTORM_RAM:\s+(\d+)/\s*(\d+)", log)[-1]
    fmax = re.findall(r"Max frequency for clock '[^']*': ([\d.]+) MHz", log)[-1]
    sh(["icepack", f"{d}/autoprueba.asc", f"{d}/autoprueba_{peldano}.bin"])
    h = hashlib.sha256(open(os.path.join(RAIZ, f"{d}/autoprueba_{peldano}.bin"), "rb").read()).hexdigest()
    ok = float(fmax) >= 25.0
    informe.append(f"{'PASS' if ok else 'FAIL'} bitstream {d}/autoprueba_{peldano}.bin: {lc[0]} de {lc[1]} celdas, "
                   f"{ram[0]} de {ram[1]} BRAM, frecuencia maxima {fmax} MHz, firma esperada {esperada:04x} adentro")
    informe.append(f"     sha256 {h}")
    return ok


def chip(peldano, informe, botones):
    d = carpeta(peldano)
    esperada = int(open(os.path.join(RAIZ, f"{d}/firma.txt")).read(), 16)
    sh([sys.executable, "tools/chip_vlog.py", f"{d}/autoprueba.asc", "goboard.pcf", "-o", f"{d}/chip.v"])
    cells = subprocess.check_output(["yosys-config", "--datdir"], text=True).strip() + "/ice40/cells_sim.v"
    r = sh(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", "tb_autoprueba",
            "-DCHIP", "-DNO_ICE40_DEFAULT_ASSIGNMENTS", "-O3", "--Mdir", f"{d}/obj_chip", "-o", "sim",
            cells, f"{d}/chip.v", "tb/autoprueba/tb_autoprueba.sv"], log=f"{d}/verilator_chip.log")
    if r.returncode != 0:
        informe.append(f"FAIL Verilator no compila el bitstream ruteado (ver {d}/verilator_chip.log)")
        return False
    ok = True
    for b in botones:
        r = sh([f"{d}/obj_chip/sim", f"+BOTON={b}", f"+FIRMA={esperada:04x}"], log=f"{d}/chip_{b}.log")
        linea = [l for l in r.stdout.splitlines() if l.startswith("RESULTADO")]
        res = linea[0] if linea else "RESULTADO sin salida: " + r.stdout[-200:]
        ok &= res.endswith("PASS")
        informe.append(f"{'PASS' if res.endswith('PASS') else 'FAIL'} bitstream ruteado con SW{b} ({NOMBRE_PERIODO[b]}): {res}")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("accion", choices=("firma", "simular", "control", "bitstream", "chip", "todo"))
    ap.add_argument("peldano", choices=sorted(PELDANOS))
    ap.add_argument("--botones", default="3,2,1", help="botones a simular (3 es el período más corto)")
    ap.add_argument("--botones-chip", default="3", help="botones a simular con el bitstream ruteado")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    botones = [int(x) for x in a.botones.split(",")]
    informe = []
    ok = True
    if a.accion in ("firma", "todo"):
        firma(a.peldano, informe)
    if a.accion in ("bitstream", "todo"):
        ok &= bitstream(a.peldano, informe)
    if a.accion in ("simular", "todo"):
        ok &= simular(a.peldano, informe, botones)
    if a.accion in ("control", "todo"):
        ok &= control(a.peldano, informe)
    if a.accion in ("chip", "todo"):
        ok &= chip(a.peldano, informe, [int(x) for x in a.botones_chip.split(",")])
    commit = sh(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    texto = "\n".join([f"Autoprueba del peldano {a.peldano} ({a.accion}), commit {commit}",
                       f"Generado por tools/autoprueba.py {a.accion} {a.peldano}. No editar a mano.", ""] + informe +
                      ["", "PASS" if ok else "FAIL"]) + "\n"
    print(texto, end="")
    if a.accion == "todo":
        with open(os.path.join(RAIZ, f"docs/mediciones/autoprueba_{a.peldano}.txt"), "w") as f:
            f.write(texto)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
